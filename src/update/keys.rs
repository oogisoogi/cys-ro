//! 갱신 키 체계 — 용도 분리 키링(R 루트 · U 릴리스 · F 피드 · A2 윈 자산 · P 팩) + R 서명 폐기문(위임·폐기).
//! 설계 AUTO-UPDATE-118 §4-1 · §6-2 ⓐ.
//!
//! - 키링 원천 = `cysjavis-pack/trusted-keys.json`(build.rs 가 바이너리에 내장 — TOFU 0). 각 키의 `purpose` 칸
//!   (`root|release|feed|win-asset|pack` · **부재 = pack** · 하위 호환)으로 용도를 가른다. **용도가 맞는 키만 수용**한다
//!   (F 키로 서명한 릴리스 본문 = 거부 — 교차 사용 차단).
//! - 이 판(U1)에는 R·U·F 실키가 없다(키 생성·기입 = U3 · 비가역 · master 게이트). 내장 키링에 갱신 용도 키가 0 이면
//!   모든 피드 검증은 「알 수 없는 key_id」로 거부된다(fail-closed) — 그것이 자리표시의 뜻이다.
//! - 시험 키링 덮어쓰기(`CYS_UPDATE_TEST_KEYRING`)는 **디버그 빌드에서만** 읽는다(§4-4 · §4-6 「시험 키 혼입」).
//! - 서명 검증은 팩과 **같은 minisign 함수**(`packsig::verify_minisign`)를 쓴다 — 새 암호 코드 0.

use super::errors::{ErrCode, UpdateErr};
use serde::Deserialize;
use std::collections::BTreeSet;

/// 키 용도.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Purpose {
    /// R — 위임·폐기문만 서명(내용 서명 권한 0).
    Root,
    /// U — 릴리스 본문.
    Release,
    /// F — 봉투(만료·단계 배포·정지).
    Feed,
    /// A2 — 윈 설치 파일 `.sig`.
    WinAsset,
    /// P — 팩 매니페스트(종전 키 전부).
    Pack,
}

impl Purpose {
    pub fn as_str(self) -> &'static str {
        match self {
            Purpose::Root => "root",
            Purpose::Release => "release",
            Purpose::Feed => "feed",
            Purpose::WinAsset => "win-asset",
            Purpose::Pack => "pack",
        }
    }

    /// 키링 칸 해석 — 부재 = pack(하위 호환) · 미지 값 = None(그 키 거부).
    pub fn parse(s: Option<&str>) -> Option<Purpose> {
        match s {
            None => Some(Purpose::Pack),
            Some("root") => Some(Purpose::Root),
            Some("release") => Some(Purpose::Release),
            Some("feed") => Some(Purpose::Feed),
            Some("win-asset") => Some(Purpose::WinAsset),
            Some("pack") => Some(Purpose::Pack),
            Some(_) => None,
        }
    }
}

/// 키링 파일의 한 줄(원시 — 용도·만료를 아직 해석하지 않음).
#[derive(Debug, Clone, Deserialize)]
struct RawKey {
    key_id: String,
    pubkey: String,
    #[serde(default)]
    not_after: String,
    #[serde(default)]
    purpose: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
struct RawKeyring {
    #[serde(default)]
    keys: Vec<RawKey>,
    #[serde(default)]
    revoked_key_ids: Vec<String>,
}

/// 해석된 갱신 키 1개.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UpdateKey {
    pub key_id: String,
    pub pubkey: String,
    /// Unix 초. 이 시각 이후(≥) 그 키 거부.
    pub not_after: i64,
    pub purpose: Purpose,
    /// 내장(바이너리) 키인가 · R 위임으로 들어온 키인가.
    pub delegated: bool,
}

/// 갱신 용도 키링(팩 키는 담지 않는다 — 팩 검증은 `packsig` 가 따로 한다).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct UpdateKeyring {
    pub keys: Vec<UpdateKey>,
    pub revoked_key_ids: BTreeSet<String>,
}

impl UpdateKeyring {
    /// 키링 JSON(trusted-keys.json 서식)에서 **팩 외 용도** 키만 뽑는다. 미지 용도·만료 파싱 불가 키는 조용히 빼지 않고
    /// 오류로 올린다(내장 키링 오기 = 빌드·시험이 잡아야 할 일).
    pub fn from_trusted_keys_json(json: &str) -> Result<UpdateKeyring, String> {
        let raw: RawKeyring = serde_json::from_str(json).map_err(|e| format!("키링 파싱 실패: {e}"))?;
        let mut keys = Vec::new();
        for k in raw.keys {
            let purpose = Purpose::parse(k.purpose.as_deref())
                .ok_or_else(|| format!("키 {} 의 purpose {:?} 는 미지 값", k.key_id, k.purpose))?;
            if purpose == Purpose::Pack {
                continue;
            }
            let not_after = crate::packsig::parse_rfc3339(&k.not_after)
                .ok_or_else(|| format!("키 {} not_after 부재/파싱불가", k.key_id))?;
            keys.push(UpdateKey { key_id: k.key_id, pubkey: k.pubkey, not_after, purpose, delegated: false });
        }
        Ok(UpdateKeyring { keys, revoked_key_ids: raw.revoked_key_ids.into_iter().collect() })
    }

    /// 바이너리 내장 키링(+ 디버그 빌드에서만 시험 키링 덮어쓰기).
    pub fn embedded() -> Result<UpdateKeyring, String> {
        if let Some(path) = test_keyring_override(cfg!(debug_assertions), |k| std::env::var_os(k)) {
            let s = std::fs::read_to_string(&path)
                .map_err(|e| format!("시험 키링 읽기 실패 {}: {e}", path.display()))?;
            return UpdateKeyring::from_trusted_keys_json(&s);
        }
        UpdateKeyring::from_trusted_keys_json(crate::packsig::TRUSTED_KEYS_JSON)
    }

    pub fn key_ids(&self) -> Vec<String> {
        self.keys.iter().map(|k| format!("{}:{}", k.purpose.as_str(), k.key_id)).collect()
    }

    /// ★2판: 그 용도의 키 중 하나라도 서명을 받아들이면 Ok(A2 처럼 서명 쪽에 key_id 칸이 없는 자산용). ⚠[`key_ids`] 는
    /// `용도:key_id` 표시 문자열이라 [`verify`] 의 key_id 로 넘기면 늘 실패한다(1판 S2 A2 검사가 그랬다 — 2판 수리).
    pub fn verify_any(&self, purpose: Purpose, data: &[u8], sig: &[u8], now: i64) -> Result<(), String> {
        let mut last = format!("{} 용도 키 없음", purpose.as_str());
        for k in self.keys.iter().filter(|k| k.purpose == purpose) {
            match self.verify(purpose, &k.key_id, data, sig, now) {
                Ok(()) => return Ok(()),
                Err(e) => last = e,
            }
        }
        Err(last)
    }

    /// 용도·폐기·만료를 따져 키 1개를 고른다.
    pub fn find(&self, key_id: &str, purpose: Purpose, now: i64) -> Result<&UpdateKey, String> {
        if self.revoked_key_ids.contains(key_id) {
            return Err(format!("폐기된 key_id {key_id}"));
        }
        let k = self
            .keys
            .iter()
            .find(|k| k.key_id == key_id)
            .ok_or_else(|| format!("알 수 없는 key_id {key_id}"))?;
        if k.purpose != purpose {
            return Err(format!("용도 불일치 {key_id}: {}≠{}", k.purpose.as_str(), purpose.as_str()));
        }
        if now >= k.not_after {
            return Err(format!("만료된 키 {key_id}"));
        }
        Ok(k)
    }

    /// `key_id` 가 가리키는 `purpose` 키로 `data` 의 minisign 서명을 검증한다.
    pub fn verify(&self, purpose: Purpose, key_id: &str, data: &[u8], sig: &[u8], now: i64) -> Result<(), String> {
        let k = self.find(key_id, purpose, now)?;
        if purpose == Purpose::WinAsset {
            return crate::packsig::verify_minisign(&k.pubkey, data, &win_asset_sig_text(sig));
        }
        crate::packsig::verify_minisign(&k.pubkey, data, sig)
    }

    /// R 서명 폐기문을 반영한 유효 키링 — 위임 키 추가(루트 위임 불가) · `revoked_key_ids` 합집합.
    /// 폐기문은 [`verify_revocations`] 를 통과한 것만 넘긴다.
    pub fn with_revocations(&self, rev: &Revocations) -> UpdateKeyring {
        let mut out = self.clone();
        for d in &rev.delegations {
            if out.keys.iter().any(|k| k.key_id == d.key_id) {
                continue; // 같은 key_id 재위임은 무시(내장 키를 위임으로 바꿔치기 0)
            }
            out.keys.push(UpdateKey {
                key_id: d.key_id.clone(),
                pubkey: d.pubkey.clone(),
                not_after: d.not_after,
                purpose: d.purpose,
                delegated: true,
            });
        }
        out.revoked_key_ids.extend(rev.revoked_key_ids.iter().cloned());
        out
    }
}

/// A2 `.sig` 입력 정규화(cysr-118-a2-sigformat) — tauri 번들러가 내는 `.sig` = minisign 서명 텍스트 전체를 base64(STANDARD)로 한 번 더
/// 감싼 것(실 발행물 `cysr_1.1.8_x64-setup.exe.sig` 412 B). ① 「untrusted comment:」로 시작 = minisign 원문 그대로 ② 아니면 앞뒤 공백·
/// 개행을 걷고 base64 해제 → 「untrusted comment:」로 시작하면 그 텍스트 ③ 둘 다 아님 = 원 바이트 그대로(종전 「서명 디코드 실패」).
fn win_asset_sig_text(sig: &[u8]) -> std::borrow::Cow<'_, [u8]> {
    use base64::Engine;
    const HEAD: &[u8] = b"untrusted comment:";
    if sig.starts_with(HEAD) {
        return std::borrow::Cow::Borrowed(sig);
    }
    match base64::engine::general_purpose::STANDARD.decode(sig.trim_ascii()) {
        Ok(text) if text.starts_with(HEAD) => std::borrow::Cow::Owned(text),
        _ => std::borrow::Cow::Borrowed(sig),
    }
}

/// 시험 키링 덮어쓰기 경로 — `debug` 가 거짓(출시 빌드)이면 env 가 있어도 None.
pub fn test_keyring_override(
    debug: bool,
    get: impl Fn(&str) -> Option<std::ffi::OsString>,
) -> Option<std::path::PathBuf> {
    if !debug {
        return None;
    }
    get("CYS_UPDATE_TEST_KEYRING").filter(|v| !v.is_empty()).map(std::path::PathBuf::from)
}

// ── 폐기문(R 서명) ───────────────────────────────────────────────────────────────────

/// 폐기 항목의 심각도(§4-1 · 3R MAJOR 3) — 미지 값은 `Advisory` 로 읽고 `unknown_severity` 로 표시(신호 1회).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Severity {
    Advisory,
    StopSeats,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RevokedRelease {
    pub component: String,
    pub release_seq: u64,
    pub severity: Severity,
    pub unknown_severity: bool,
    pub reason_code: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Delegation {
    pub key_id: String,
    pub purpose: Purpose,
    pub pubkey: String,
    pub not_after: i64,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct DrPins {
    pub add: Vec<String>,
    pub revoke: Vec<String>,
}

/// 검증을 통과한 폐기문.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Revocations {
    pub rev: u64,
    pub signed_at: i64,
    pub key_id: String,
    pub delegations: Vec<Delegation>,
    pub revoked_key_ids: Vec<String>,
    pub revoked_releases: Vec<RevokedRelease>,
    pub dr_pins: DrPins,
}

/// 폐기문 서식 표지(교차 사용 차단 — 봉투·본문·팩 매니페스트와 서로 역직렬화되지 않게).
pub const REVOCATIONS_KIND: &str = "update-revocations";

#[derive(Debug, Deserialize)]
struct RawRevocations {
    kind: String,
    rev: u64,
    key_id: String,
    signed_at: i64,
    #[serde(default)]
    delegations: Vec<RawDelegation>,
    #[serde(default)]
    revoked_key_ids: Vec<String>,
    #[serde(default)]
    revoked_releases: Vec<RawRevokedRelease>,
    #[serde(default)]
    dr_pins: Option<RawDrPins>,
}

#[derive(Debug, Deserialize)]
struct RawDelegation {
    key_id: String,
    purpose: String,
    pubkey: String,
    not_after: i64,
}

#[derive(Debug, Deserialize)]
struct RawRevokedRelease {
    component: String,
    release_seq: u64,
    #[serde(default)]
    severity: Option<String>,
    #[serde(default)]
    reason_code: String,
}

#[derive(Debug, Deserialize)]
struct RawDrPins {
    #[serde(default)]
    add: Vec<String>,
    #[serde(default)]
    revoke: Vec<String>,
}

/// ⓐ 폐기문 검증 — 서식 → R 키(내장만 · 루트는 위임 불가) → minisign → `rev` 단조(`accepted_rev` 미만 = 거부) →
/// `signed_at` 미래 거부(기준 = 신뢰 시각 `max(now, last_trusted)` — 미래 서명 폐기문을 받으면 `last_trusted_time` 가 미래로
/// 밀려 그 시각까지 모든 판정이 「시계 의심」에 갇힌다 · U3 1R).
/// 실패 코드: 서명·서식 = `feed_sig_bad`(폐기문은 피드 계층의 일부) · `rev` 후퇴 = `feed_replay` · 미래 서명 = `feed_expired`.
pub fn verify_revocations(
    bytes: &[u8],
    sig: &[u8],
    embedded: &UpdateKeyring,
    accepted_rev: Option<u64>,
    now: i64,
    last_trusted: Option<i64>,
) -> Result<Revocations, UpdateErr> {
    let bad = |d: String| UpdateErr::new(ErrCode::FeedSigBad, "ⓐ", d);
    let raw: RawRevocations = serde_json::from_slice(bytes).map_err(|e| bad(format!("폐기문 서식: {e}")))?;
    if raw.kind != REVOCATIONS_KIND {
        return Err(bad(format!("폐기문 kind {}", raw.kind)));
    }
    // ★2R N5: 시각 기준 = 신뢰 시각 `max(now, last_trusted)` — 과거로 돌린 시계에서 이미 만료된 R 키가 다시 유효해지지 않게
    //   (키 만료와 아래 signed_at 미래 거부가 같은 기준).
    let trusted_now = if super::mutant("N5") { now } else { last_trusted.map_or(now, |t| t.max(now)) };
    // R 은 내장 키만(위임문이 스스로 루트를 늘리는 순환 차단). 내장 키링의 폐기 목록만 본다.
    embedded.verify(Purpose::Root, &raw.key_id, bytes, sig, trusted_now).map_err(bad)?;
    if let Some(acc) = accepted_rev {
        if raw.rev < acc {
            return Err(UpdateErr::new(ErrCode::FeedReplay, "ⓐ", format!("폐기문 rev {} < 수용 {acc}", raw.rev)));
        }
    }
    if raw.signed_at > trusted_now && !super::mutant("RF") {
        return Err(UpdateErr::new(
            ErrCode::FeedExpired,
            "ⓐ",
            format!("폐기문 signed_at {} > 신뢰 시각 {trusted_now}(미래 서명)", raw.signed_at),
        ));
    }
    let mut delegations = Vec::new();
    for d in raw.delegations {
        let purpose = Purpose::parse(Some(&d.purpose)).ok_or_else(|| bad(format!("위임 용도 {}", d.purpose)))?;
        if purpose == Purpose::Root || purpose == Purpose::Pack {
            return Err(bad(format!("위임 불가 용도 {}", purpose.as_str())));
        }
        if crate::packsig::pubkey_key_id(&d.pubkey).ok().as_deref() != Some(d.key_id.as_str()) {
            return Err(bad(format!("위임 key_id≠공개키 {}", d.key_id)));
        }
        delegations.push(Delegation { key_id: d.key_id, purpose, pubkey: d.pubkey, not_after: d.not_after });
    }
    // ★2R B9: 폐기 항목 component = 부품 목록 안 · dr_pins = 인증서 leaf sha1 소문자 40 hex.
    if let Some(r) = raw.revoked_releases.iter().find(|r| !super::feed::COMPONENTS.contains(&r.component.as_str())) {
        return Err(bad(format!("폐기 항목 component {:?}", r.component)));
    }
    if let Some(p) = raw.dr_pins.iter().flat_map(|d| d.add.iter().chain(&d.revoke)).find(|p| !super::feed::is_hex40(p)) {
        return Err(bad(format!("dr_pins 형식(소문자 40 hex) {p:?}")));
    }
    let revoked_releases = raw
        .revoked_releases
        .into_iter()
        .map(|r| {
            let (severity, unknown) = match r.severity.as_deref() {
                None | Some("advisory") => (Severity::Advisory, false),
                Some("stop_seats") => (Severity::StopSeats, false),
                Some(_) => (Severity::Advisory, true),
            };
            RevokedRelease {
                component: r.component,
                release_seq: r.release_seq,
                severity,
                unknown_severity: unknown,
                reason_code: r.reason_code,
            }
        })
        .collect();
    let dr = raw.dr_pins.unwrap_or(RawDrPins { add: vec![], revoke: vec![] });
    Ok(Revocations {
        rev: raw.rev,
        signed_at: raw.signed_at,
        key_id: raw.key_id,
        delegations,
        revoked_key_ids: raw.revoked_key_ids,
        revoked_releases,
        dr_pins: DrPins { add: dr.add, revoke: dr.revoke },
    })
}

impl Revocations {
    /// `(component, release_seq)` 가 폐기 목록에 있으면 그 항목.
    pub fn revoked(&self, component: &str, release_seq: u64) -> Option<&RevokedRelease> {
        self.revoked_releases.iter().find(|r| r.component == component && r.release_seq == release_seq)
    }
}

// ── 시험 지원(시험 빌드에서만 컴파일 · 실키 0 — 키쌍은 시험 안에서 생성) ──────────────────────────
#[cfg(test)]
pub(crate) mod testkit {
    use super::*;

    /// 시험 키 1개(생성 · 서명 함수).
    pub struct TestKey {
        pub key_id: String,
        pub pubkey: String,
        sk: minisign::SecretKey,
    }

    impl TestKey {
        pub fn new() -> TestKey {
            let kp = minisign::KeyPair::generate_unencrypted_keypair().expect("keypair");
            let pubkey = kp.pk.to_base64();
            let key_id = crate::packsig::pubkey_key_id(&pubkey).expect("key_id");
            TestKey { key_id, pubkey, sk: kp.sk }
        }
        pub fn sign(&self, data: &[u8]) -> Vec<u8> {
            let c = std::io::Cursor::new(data.to_vec());
            minisign::sign(None, &self.sk, c, None, None).expect("sign").into_string().into_bytes()
        }
        pub fn entry(&self, purpose: &str) -> serde_json::Value {
            serde_json::json!({"key_id": self.key_id, "pubkey": self.pubkey,
                "not_after": "2099-01-01T00:00:00Z", "purpose": purpose})
        }
    }

    /// R·U·F·A2 시험 키 4개 + 그것을 담은 키링 JSON.
    pub struct Keys {
        pub r: TestKey,
        pub u: TestKey,
        pub f: TestKey,
        pub a2: TestKey,
    }

    impl Keys {
        pub fn new() -> Keys {
            Keys { r: TestKey::new(), u: TestKey::new(), f: TestKey::new(), a2: TestKey::new() }
        }
        pub fn keyring_json(&self) -> String {
            serde_json::json!({"keys": [self.r.entry("root"), self.u.entry("release"),
                self.f.entry("feed"), self.a2.entry("win-asset")], "revoked_key_ids": []})
            .to_string()
        }
        pub fn keyring(&self) -> UpdateKeyring {
            UpdateKeyring::from_trusted_keys_json(&self.keyring_json()).unwrap()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::testkit::*;
    use super::*;

    const NOW: i64 = 1_790_000_000;

    fn revo(k: &Keys, rev: u64, extra: serde_json::Value) -> (Vec<u8>, Vec<u8>) {
        let mut v = serde_json::json!({"kind": REVOCATIONS_KIND, "rev": rev, "key_id": k.r.key_id, "signed_at": NOW - 10});
        if let (Some(o), Some(e)) = (v.as_object_mut(), extra.as_object()) {
            for (a, b) in e {
                o.insert(a.clone(), b.clone());
            }
        }
        let bytes = v.to_string().into_bytes();
        let sig = k.r.sign(&bytes);
        (bytes, sig)
    }

    #[test]
    fn purpose_absent_is_pack_and_unknown_is_rejected() {
        assert_eq!(Purpose::parse(None), Some(Purpose::Pack));
        assert_eq!(Purpose::parse(Some("win-asset")), Some(Purpose::WinAsset));
        assert_eq!(Purpose::parse(Some("Feed")), None);
        let bad = r#"{"keys":[{"key_id":"AAAAAAAAAAAAAAAA","pubkey":"x","not_after":"2030-01-01T00:00:00Z","purpose":"wat"}]}"#;
        assert!(UpdateKeyring::from_trusted_keys_json(bad).is_err());
    }

    /// 내장 키링(1.1.8 · TICKET=cysr-118-keyring · 2026-10-07 키 의식) = 갱신 용도 키 정확히 4개(R·U·F·A2) — 각자 제 용도로만 찾히고
    /// 팩 키는 갱신 키링에 들어오지 않는다. (U1 판 핀 「갱신 키 0 = 전부 닫힘」 의 후계 — 실키 기입으로 뒤집힌다.)
    #[test]
    fn embedded_keyring_has_exactly_the_four_update_keys() {
        let kr = UpdateKeyring::from_trusted_keys_json(crate::packsig::TRUSTED_KEYS_JSON).unwrap();
        assert_eq!(
            kr.key_ids(),
            vec!["root:E2EDBBF9B1CBDBB9", "release:49E63A352CC87151", "feed:20ADC40AE5764C8A", "win-asset:831CA9172204E93E"]
        );
        for (id, purpose, wrong) in [
            ("E2EDBBF9B1CBDBB9", Purpose::Root, Purpose::Release),
            ("49E63A352CC87151", Purpose::Release, Purpose::Feed),
            ("20ADC40AE5764C8A", Purpose::Feed, Purpose::Release),
            ("831CA9172204E93E", Purpose::WinAsset, Purpose::Release),
        ] {
            assert!(kr.find(id, purpose, NOW).is_ok(), "{id} 가 제 용도로 안 찾힌다");
            assert!(kr.find(id, wrong, NOW).unwrap_err().contains("용도 불일치"), "{id} 가 다른 용도로 찾혔다");
        }
        assert!(kr.find("54FBA04AD0E0F49D", Purpose::Pack, NOW).is_err(), "팩 키는 갱신 키링에 들어오지 않는다");
        assert!(kr.find("C81BCA7B89578FDE", Purpose::Pack, NOW).is_err(), "팩 키는 갱신 키링에 들어오지 않는다");
    }

    #[test]
    fn find_rejects_wrong_purpose_revoked_expired_unknown() {
        let k = Keys::new();
        let kr = k.keyring();
        assert!(kr.find(&k.u.key_id, Purpose::Release, NOW).is_ok());
        assert!(kr.find(&k.u.key_id, Purpose::Feed, NOW).unwrap_err().contains("용도 불일치"));
        assert!(kr.find("0000000000000000", Purpose::Feed, NOW).unwrap_err().contains("알 수 없는"));
        let mut r = kr.clone();
        r.revoked_key_ids.insert(k.f.key_id.clone());
        assert!(r.find(&k.f.key_id, Purpose::Feed, NOW).unwrap_err().contains("폐기"));
        let far = crate::packsig::parse_rfc3339("2099-01-01T00:00:00Z").unwrap();
        assert!(kr.find(&k.f.key_id, Purpose::Feed, far).unwrap_err().contains("만료"));
    }

    /// ★cysr-118-a2-sigformat: A2 `.sig` 실 발행물 꼴 = minisign 서명 텍스트를 base64(STANDARD)로 한 번 더 감싼 것(tauri 번들러 ·
    /// 1.1.8 윈 실기 17:07 「설치기 A2 서명 불일치」) — ⓐ 감싼 꼴(+끝 개행) 통과 ⓒ 원문 텍스트 여전히 통과 ⓓ 다른 바이트 · 깨진 base64 ·
    /// 서명 아닌 텍스트를 감싼 것 · A2 아닌 키(감싼 꼴) = 거부 · 감싼 꼴 수용은 A2 용도 한정(U 는 종전 그대로 「디코드 실패」).
    #[test]
    fn win_asset_accepts_tauri_base64_wrapped_sig() {
        use base64::Engine;
        let b64 = base64::engine::general_purpose::STANDARD;
        let k = Keys::new();
        let kr = k.keyring();
        let setup = b"MZ-setup-wrapped";
        let raw = k.a2.sign(setup);
        let wrapped = b64.encode(&raw).into_bytes();
        assert!(kr.verify_any(Purpose::WinAsset, setup, &wrapped, NOW).is_ok(), "ⓐ tauri 꼴(base64 겉포장)");
        let mut nl = wrapped.clone();
        nl.extend_from_slice(b"\r\n");
        assert!(kr.verify_any(Purpose::WinAsset, setup, &nl, NOW).is_ok(), "ⓐ 끝 개행");
        assert!(kr.verify_any(Purpose::WinAsset, setup, &raw, NOW).is_ok(), "ⓒ 원문 텍스트");
        assert!(kr.verify_any(Purpose::WinAsset, b"MZ-evil", &wrapped, NOW).is_err(), "ⓓ 다른 바이트");
        let mut broken = wrapped.clone();
        broken.truncate(broken.len() - 7);
        broken.push(b'!');
        assert!(kr.verify_any(Purpose::WinAsset, setup, &broken, NOW).is_err(), "ⓓ 깨진 base64");
        assert!(kr.verify_any(Purpose::WinAsset, setup, b64.encode(b"not a signature").as_bytes(), NOW).is_err(), "ⓓ 서명 아닌 텍스트");
        assert!(kr.verify_any(Purpose::WinAsset, setup, b64.encode(k.u.sign(setup)).as_bytes(), NOW).is_err(), "ⓓ A2 아닌 키");
        let sig_u = k.u.sign(setup);
        assert!(kr.verify(Purpose::Release, &k.u.key_id, setup, &sig_u, NOW).is_ok());
        let wrapped_u = b64.encode(&sig_u);
        assert!(
            kr.verify(Purpose::Release, &k.u.key_id, setup, wrapped_u.as_bytes(), NOW).unwrap_err().contains("디코드"),
            "감싼 꼴 수용 = A2 한정(U 경로 동작 불변)"
        );
    }

    /// ⓔ 실물 대조(손 실행 · `--ignored`): 실 발행물 `cysr_1.1.8_x64-setup.exe` + `.sig`(cys-ro v1.1.8 · .sig 412 B)를 **내장 키링** A2
    /// 공개키(831CA9172204E93E)로 검증 · 한 바이트 잘린 설치기 = 거부. `CYS_A2_REAL_SETUP` · `CYS_A2_REAL_SIG` = 받은 파일 경로.
    #[test]
    #[ignore]
    fn real_release_a2_sig_verifies_with_embedded_keyring() {
        let setup = std::fs::read(std::env::var("CYS_A2_REAL_SETUP").expect("CYS_A2_REAL_SETUP")).unwrap();
        let sig = std::fs::read(std::env::var("CYS_A2_REAL_SIG").expect("CYS_A2_REAL_SIG")).unwrap();
        let kr = UpdateKeyring::from_trusted_keys_json(crate::packsig::TRUSTED_KEYS_JSON).unwrap();
        let now = super::super::clock::wall_now();
        kr.verify_any(Purpose::WinAsset, &setup, &sig, now).expect("실 발행물 A2 서명");
        assert!(kr.verify_any(Purpose::WinAsset, &setup[..setup.len() - 1], &sig, now).is_err(), "잘린 설치기 = 거부");
    }

    /// 교차 사용: F 키로 서명한 데이터를 U 용도로 검증 = 거부(키 자체로 막는다).
    #[test]
    fn cross_purpose_signature_rejected() {
        let k = Keys::new();
        let kr = k.keyring();
        let data = b"body";
        let sig_f = k.f.sign(data);
        assert!(kr.verify(Purpose::Feed, &k.f.key_id, data, &sig_f, NOW).is_ok());
        assert!(kr.verify(Purpose::Release, &k.f.key_id, data, &sig_f, NOW).is_err());
        // U key_id 를 주장하지만 F 키로 서명 = minisign 키 번호 불일치로 거부
        assert!(kr.verify(Purpose::Release, &k.u.key_id, data, &sig_f, NOW).is_err());
    }

    #[test]
    fn revocations_roundtrip_delegation_and_severity() {
        let k = Keys::new();
        let embedded = k.keyring();
        let newf = TestKey::new();
        let (b, s) = revo(
            &k,
            3,
            serde_json::json!({
                "delegations": [{"key_id": newf.key_id, "purpose": "feed", "pubkey": newf.pubkey, "not_after": NOW + 1000}],
                "revoked_key_ids": [k.f.key_id],
                "revoked_releases": [
                    {"component": "cysr", "release_seq": 7, "severity": "stop_seats", "reason_code": "x"},
                    {"component": "cysr", "release_seq": 8, "severity": "melt", "reason_code": "y"},
                    {"component": "agora-client", "release_seq": 7}
                ]
            }),
        );
        let r = verify_revocations(&b, &s, &embedded, Some(2), NOW, None).unwrap();
        assert_eq!(r.rev, 3);
        assert_eq!(r.revoked("cysr", 7).unwrap().severity, Severity::StopSeats);
        let unk = r.revoked("cysr", 8).unwrap();
        assert_eq!((unk.severity, unk.unknown_severity), (Severity::Advisory, true));
        assert_eq!(r.revoked("agora-client", 7).unwrap().severity, Severity::Advisory);
        assert!(r.revoked("cysr", 9).is_none());
        let eff = embedded.with_revocations(&r);
        assert!(eff.find(&newf.key_id, Purpose::Feed, NOW).is_ok(), "위임 키 수용");
        assert!(eff.find(&k.f.key_id, Purpose::Feed, NOW).is_err(), "폐기된 옛 F 키 거부");
    }

    #[test]
    fn revocations_rev_rollback_and_bad_sig_and_non_root_signer_rejected() {
        let k = Keys::new();
        let kr = k.keyring();
        let (b, s) = revo(&k, 3, serde_json::json!({}));
        assert_eq!(verify_revocations(&b, &s, &kr, Some(4), NOW, None).unwrap_err().code, ErrCode::FeedReplay);
        assert!(verify_revocations(&b, &s, &kr, Some(3), NOW, None).is_ok(), "같은 rev = 통과(무변화)");
        let mut b2 = b.clone();
        let i = b2.len() - 2;
        b2[i] ^= 1; // 1바이트 변조
        assert_eq!(verify_revocations(&b2, &s, &kr, None, NOW, None).unwrap_err().code, ErrCode::FeedSigBad);
        // U 키로 서명한 폐기문 = R 용도 아님 → 거부
        let v = serde_json::json!({"kind": REVOCATIONS_KIND, "rev": 1, "key_id": k.u.key_id, "signed_at": NOW});
        let bb = v.to_string().into_bytes();
        let ss = k.u.sign(&bb);
        assert_eq!(verify_revocations(&bb, &ss, &kr, None, NOW, None).unwrap_err().code, ErrCode::FeedSigBad);
    }

    /// ★U3 1R 뮤테이션 RF: 폐기문 `signed_at` 미래 = 거부(기준 = `max(now, 신뢰 시각)`) — 받으면 `last_trusted_time` 가 미래로 밀린다.
    #[test]
    fn rf_future_signed_revocations_rejected() {
        let k = Keys::new();
        let kr = k.keyring();
        let (b, s) = revo(&k, 1, serde_json::json!({"signed_at": NOW + 3600}));
        let e = verify_revocations(&b, &s, &kr, None, NOW, None).unwrap_err();
        assert_eq!((e.code, e.step.as_str()), (ErrCode::FeedExpired, "ⓐ"));
        assert!(verify_revocations(&b, &s, &kr, None, NOW, Some(NOW + 60)).is_err(), "신뢰 시각보다도 미래");
        // 벽시계가 신뢰 시각보다 뒤처진 기기: 기준 = 신뢰 시각 → 그 이하 서명은 통과(시계 의심은 ⓔ 가 따로 판정)
        assert!(verify_revocations(&b, &s, &kr, None, NOW, Some(NOW + 3600)).is_ok());
        let (b, s) = revo(&k, 1, serde_json::json!({"signed_at": NOW}));
        assert!(verify_revocations(&b, &s, &kr, None, NOW, None).is_ok(), "지금 서명 = 통과");
    }

    /// ★2R N5 뮤테이션 N5: R 키 만료도 신뢰 시각 기준 — 시계를 과거로 돌려도(now < 만료 ≤ 신뢰 시각) 만료된 R 키는 거부.
    #[test]
    fn n5_r_key_expiry_uses_trusted_time() {
        let k = Keys::new();
        let mut v: serde_json::Value = serde_json::from_str(&k.keyring_json()).unwrap();
        for e in v["keys"].as_array_mut().unwrap() {
            if e["purpose"] == "root" {
                e["not_after"] = "2026-09-01T00:00:00Z".into(); // 1_788_220_800 < NOW
            }
        }
        let kr = UpdateKeyring::from_trusted_keys_json(&v.to_string()).unwrap();
        let rewound = NOW - 40 * 86_400; // 만료 전 시각으로 돌린 시계
        let (b, s) = revo(&k, 1, serde_json::json!({"signed_at": rewound - 10}));
        assert!(verify_revocations(&b, &s, &kr, None, rewound, None).is_ok(), "신뢰 시각 모름 = 벽시계 기준(대조군)");
        let e = verify_revocations(&b, &s, &kr, None, rewound, Some(NOW)).unwrap_err();
        assert_eq!(e.code, ErrCode::FeedSigBad, "{}", e.detail);
    }

    /// ★2R B9: 폐기 항목 component = 부품 목록 · dr_pins = 소문자 40 hex.
    #[test]
    fn b9_revocation_field_domains() {
        let k = Keys::new();
        let kr = k.keyring();
        let (b, s) = revo(&k, 1, serde_json::json!({"revoked_releases": [{"component": "evil", "release_seq": 1}]}));
        assert!(verify_revocations(&b, &s, &kr, None, NOW, None).unwrap_err().detail.contains("component"));
        for bad in ["ABCDEF0123456789ABCDEF0123456789ABCDEF01", "abc", "zz26231e7dc737ee1d74962b346c23d3acacb18d"] {
            let (b, s) = revo(&k, 1, serde_json::json!({"dr_pins": {"add": [bad]}}));
            assert!(verify_revocations(&b, &s, &kr, None, NOW, None).unwrap_err().detail.contains("dr_pins"), "{bad}");
        }
        let (b, s) = revo(&k, 1, serde_json::json!({"dr_pins": {"revoke": ["a426231e7dc737ee1d74962b346c23d3acacb18d"]}}));
        assert!(verify_revocations(&b, &s, &kr, None, NOW, None).is_ok());
    }

    /// ★2R B9: golden 왕복 — HANDOFF §8 schema 문면 그대로 쓴 폐기문(`testdata/golden-revocations.json`)이 서명·검증을 지나 모든 칸이
    /// 그 값으로 읽힌다(자리표시 = 시험 키). U3 발행기가 같은 문면을 내면 같은 결과.
    #[test]
    fn b9_golden_revocations_roundtrip() {
        let k = Keys::new();
        let kr = k.keyring();
        let x = TestKey::new();
        let text = include_str!("testdata/golden-revocations.json")
            .replace("@R_KEY_ID@", &k.r.key_id)
            .replace("@DELEG_KEY_ID@", &x.key_id)
            .replace("@DELEG_PUBKEY@", &x.pubkey);
        let b = text.into_bytes();
        let s = k.r.sign(&b);
        let r = verify_revocations(&b, &s, &kr, Some(7), NOW, Some(NOW)).unwrap();
        assert_eq!((r.rev, r.signed_at, r.key_id.as_str()), (7, 1_789_999_000, k.r.key_id.as_str()));
        assert_eq!(r.delegations, vec![Delegation { key_id: x.key_id.clone(), purpose: Purpose::Feed, pubkey: x.pubkey.clone(), not_after: 1_795_000_000 }]);
        assert_eq!(r.revoked_key_ids, vec!["0123456789ABCDEF".to_string()]);
        let rr: Vec<(&str, u64, Severity, bool, &str)> =
            r.revoked_releases.iter().map(|x| (x.component.as_str(), x.release_seq, x.severity, x.unknown_severity, x.reason_code.as_str())).collect();
        assert_eq!(rr, vec![
            ("cysr", 12, Severity::StopSeats, false, "crash-on-start"),
            ("agora-client", 3, Severity::Advisory, false, ""),
            ("cysr", 11, Severity::Advisory, false, ""),
        ]);
        assert_eq!(r.dr_pins.add, vec!["a426231e7dc737ee1d74962b346c23d3acacb18d".to_string()]);
        assert_eq!(r.dr_pins.revoke.len(), 1);
        assert_eq!(r.revoked("cysr", 12).map(|x| x.severity), Some(Severity::StopSeats));
    }

    #[test]
    fn delegating_root_or_mismatched_key_id_is_rejected() {
        let k = Keys::new();
        let kr = k.keyring();
        let x = TestKey::new();
        let (b, s) = revo(&k, 1, serde_json::json!({"delegations": [{"key_id": x.key_id, "purpose": "root", "pubkey": x.pubkey, "not_after": NOW + 9}]}));
        assert!(verify_revocations(&b, &s, &kr, None, NOW, None).is_err());
        let (b, s) = revo(&k, 1, serde_json::json!({"delegations": [{"key_id": "0000000000000000", "purpose": "feed", "pubkey": x.pubkey, "not_after": NOW + 9}]}));
        assert!(verify_revocations(&b, &s, &kr, None, NOW, None).is_err());
    }

    /// §4-4·§7-1 「출시 빌드에서 시험 키링 env 무시」.
    #[test]
    fn test_keyring_override_only_in_debug() {
        let get = |_: &str| Some(std::ffi::OsString::from("/tmp/x.json"));
        assert!(test_keyring_override(true, get).is_some());
        assert!(test_keyring_override(false, get).is_none());
    }
}
