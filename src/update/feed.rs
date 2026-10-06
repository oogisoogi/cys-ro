//! 피드 두 겹 서식 + 검증 함수 **하나**(`verify_feed`) — 설계 AUTO-UPDATE-118 §6-1 · §6-2 · §4-2.
//!
//! 두 겹: 안쪽 **릴리스 본문**(U 서명 · 발행 의식 때 1회) · 바깥 **봉투**(F 서명 · CI 주 1회 + 발행 때). 봉투는 본문 원문과
//! 그 서명을 base64 로 실어 나를 뿐 내용을 바꿀 수 없다. 폐기문(R 서명)은 [`super::keys::verify_revocations`].
//!
//! 순서(고정 · §6-2): ⓐ 폐기문(R·`rev` 단조·위임 반영) → ⓑ 봉투 서식 → ⓒ 봉투 키(F 용도·폐기·만료) → ⓓ 봉투 minisign →
//! ⓔ 유효창(N13 시계 의심이면 판정 불가) → ⓕ `feed_rev` 단조 → ⓖ 본문 서식 → ⓗ 본문 키(U 용도) → ⓘ 본문 minisign →
//! ⓙ `revoked_releases` → ⓚ `release_seq` 대 설치본(`uptodate` 갈림 · 설치판 폐기 = `installed_revoked`) →
//! ⓛ `min_from_release_seq`·`requires` 빈 값·파싱 불가 거부 → ⓜ 이 기판 행 존재·URL 허용 목록 → ⓝ `halt`·`rollout`(표시).
//!
//! 오류코드는 고정 사전(§3-12)에서만 고른다 — 사전에 「서식 오류」 낱말이 따로 없으므로 봉투 계층의 서식·키·서명 실패는
//! `feed_sig_bad`, 본문 계층은 `release_sig_bad`, ⓛ·ⓜ 의 계약 위반은 `verify_failed`(URL 은 `url_refused`) 로 싣고 어느
//! 단계인지는 `step` 칸이 말한다.

use super::errors::{ErrCode, UpdateErr};
use super::keys::{verify_revocations, Purpose, Revocations, Severity, UpdateKeyring};
use super::url::{check_url, Hop};
use base64::Engine;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

/// 봉투 서식 표지.
pub const ENVELOPE_KIND: &str = "component-update-feed";
/// 릴리스 본문 서식 표지.
pub const RELEASE_KIND: &str = "component-release";
/// 봉투 유효창 상한(`expires_at − signed_at ≤ 14일`).
pub const MAX_ENVELOPE_WINDOW_SECS: i64 = 14 * 86_400;
/// 알림 1줄 상한(글자).
pub const NOTES_MAX_CHARS: usize = 80;
/// 사용자 문구 금지 어휘(§3-12 「오류·실패·위험·손상·경고」 — 위협·공포 표현 0).
pub const NOTES_FORBIDDEN: [&str; 5] = ["오류", "실패", "위험", "손상", "경고"];

pub const COMPONENTS: [&str; 2] = ["cysr", "agora-client"];
pub const CHANNELS: [&str; 2] = ["stable", "next"];
pub const TARGETS: [&str; 4] = ["macos-arm64", "macos-x64", "windows-x64", "any"];

// ── 서식 ──────────────────────────────────────────────────────────────────────────────

/// 봉투(F 서명).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Envelope {
    pub kind: String,
    pub component: String,
    pub channel: String,
    pub feed_rev: u64,
    pub key_id: String,
    pub signed_at: i64,
    pub expires_at: i64,
    pub rollout_pct: u8,
    pub halt: bool,
    /// U 서명 릴리스 본문 원문(base64).
    pub release: String,
    /// 그 본문의 `.minisig` 원문(base64).
    pub release_sig: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub prev_release: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub prev_release_sig: Option<String>,
}

/// 동봉 팩 신원.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BundledPack {
    pub version: String,
    pub digest: String,
}

/// 기판 행 1개(U 서명 안 — 행마다 `{target, build_id, release_seq}` 를 따로 싣는다 · BLOCK 13).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Asset {
    pub url: String,
    pub size: u64,
    pub sha256: String,
    pub max_unpacked: u64,
    pub target: String,
    #[serde(default)]
    pub build_id: String,
    pub release_seq: u64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub bundled_pack: Option<BundledPack>,
    /// §6-1 공통 필수 칸(빈 배열은 허용 · 칸 부재 = 거부 — 1R MAJOR).
    #[serde(default)]
    pub features: Option<Vec<String>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cdhash: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub dr_pin_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub a2_sig_url: Option<String>,
    /// ★U3 1R #10 · 설계 §3-7 ①·S9b: 윈 설치 페이로드 전수(설치기가 놓는 모든 파일) — cysr 윈 행 **필수**(ⓖ). 검증 반환 JSON 의
    /// `asset` 에 그대로 실린다(U2 S9b 전수 대조 · U3 발행 게이트의 행 전체 대조 재료).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub payload_manifest: Option<Vec<PayloadEntry>>,
}

/// 윈 설치 페이로드 1파일 — 경로 = `/` 구분 상대 경로(U3 `make-release-json.payload_manifest` 생산 규칙과 같은 꼴).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PayloadEntry {
    pub path: String,
    pub size: u64,
    pub sha256: String,
}

/// `payload_manifest` 계약 — 비어 있지 않음 · 경로 = 상대(`/`·`\`·`:`·제어문자·빈/`.`/`..` 성분 거부) · sha256 소문자 64 hex ·
/// 대소문자 무시 경로 중복 거부(윈 파일 시스템).
fn check_payload_manifest(k: &str, pm: Option<&Vec<PayloadEntry>>) -> Result<(), String> {
    let pm = match pm {
        Some(v) if !v.is_empty() => v,
        _ => return Err(format!("행 {k} payload_manifest 부재·빈 목록")),
    };
    let mut seen = std::collections::BTreeSet::new();
    for e in pm {
        let bad_path = e.path.is_empty()
            || e.path.starts_with('/')
            || e.path.contains('\\')
            || e.path.contains(':')
            || e.path.chars().any(|c| c.is_control())
            || e.path.split('/').any(|seg| seg.is_empty() || seg == "." || seg == "..");
        if bad_path {
            return Err(format!("행 {k} payload_manifest 경로 {:?}", e.path));
        }
        if !is_hex(&e.sha256, 64) {
            return Err(format!("행 {k} payload_manifest {} sha256 형식", e.path));
        }
        if !seen.insert(e.path.to_lowercase()) {
            return Err(format!("행 {k} payload_manifest 경로 중복(대소문자 무시) {}", e.path));
        }
    }
    Ok(())
}

/// 릴리스 본문(U 서명).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReleaseBody {
    pub kind: String,
    pub component: String,
    pub release_seq: u64,
    pub version: String,
    pub key_id: String,
    pub signed_at: i64,
    pub min_from_release_seq: u64,
    #[serde(default)]
    pub requires: BTreeMap<String, serde_json::Value>,
    pub state_migration: String,
    pub assets: BTreeMap<String, Asset>,
    pub notes_ko: String,
}

/// 수용 기록(`accepted-<component>-<channel>.json` · §6-3). ★1R B2·MAJOR: 봉투 sha256 을 보존(같은 feed_rev 의 동일성 증명)하고
/// 「피드 본문의 release_seq」와 「설치판 release_seq」를 따로 적는다(호출자 주장을 피드 칸에 섞지 않는다). 모든 칸 필수.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AcceptedFeed {
    pub feed_rev: u64,
    pub envelope_sha256: String,
    pub feed_release_seq: u64,
    pub installed_release_seq: u64,
    pub signed_at: i64,
    pub at: i64,
}

pub fn sha256_hex(b: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    format!("{:x}", Sha256::digest(b))
}

fn is_hex(s: &str, n: usize) -> bool {
    s.len() == n && s.chars().all(|c| c.is_ascii_digit() || ('a'..='f').contains(&c))
}

// ── 판정 ──────────────────────────────────────────────────────────────────────────────

/// 판정(§6-2 `verdict` 칸).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    Apply,
    Uptodate,
    InstalledRevoked,
    Halt,
    NotInRollout,
    /// rc 2 — 거부.
    Reject,
    /// rc 3 — 판정 불가(시계 의심·로컬 기록 손상).
    Undetermined,
}

impl Verdict {
    pub fn as_str(self) -> &'static str {
        match self {
            Verdict::Apply => "apply",
            Verdict::Uptodate => "uptodate",
            Verdict::InstalledRevoked => "installed_revoked",
            Verdict::Halt => "halt",
            Verdict::NotInRollout => "not_in_rollout",
            Verdict::Reject => "reject",
            Verdict::Undetermined => "undetermined",
        }
    }

    /// CLI 종료 코드(§6-2 rc 0 = 판정 성공 · 2 = 거부 · 3 = 판정 불가).
    pub fn rc(self) -> i32 {
        match self {
            Verdict::Reject => 2,
            Verdict::Undetermined => 3,
            _ => 0,
        }
    }
}

/// 검증 입력(전부 값 — 파일·네트워크·시계 접근 0 · 순수 함수).
pub struct FeedInput<'a> {
    pub component: &'a str,
    pub channel: &'a str,
    pub envelope: &'a [u8],
    pub envelope_sig: &'a [u8],
    pub revocations: &'a [u8],
    pub revocations_sig: &'a [u8],
    pub now: i64,
    /// N13 결과(호출부가 [`super::clock::clock_suspect`] 로 판정해 넘긴다).
    pub clock_suspect: bool,
    /// 수용 기록 — `Err` = 존재하나 손상(판정 불가).
    pub accepted: Result<Option<AcceptedFeed>, String>,
    /// 수용한 폐기문 `rev`(없으면 신규 기기).
    pub accepted_rev: Option<u64>,
    /// 마지막 신뢰 시각(`trusted.json`) — 폐기문 `signed_at` 미래 거부의 기준(`max(now, 이 값)`).
    pub last_trusted_time: Option<i64>,
    /// 바이너리 내장 키링(R·U·F·A2).
    pub keyring: &'a UpdateKeyring,
    pub installed_release_seq: u64,
    pub target: &'a str,
    /// `hash(install_id) % 100` — None 이면 단계 배포 100% 일 때만 대상.
    pub rollout_bucket: Option<u8>,
}

/// 검증 결과(JSON 직렬화 = `cys update-verify --json`).
#[derive(Debug, Clone)]
pub struct FeedOutcome {
    pub verdict: Verdict,
    /// 사전 코드(성공 판정은 `update.ok` · `installed_revoked` 는 그 코드).
    pub code: ErrCode,
    pub step: String,
    pub detail: String,
    pub asset: Option<Asset>,
    pub release_seq: Option<u64>,
    pub version: Option<String>,
    pub feed_rev: Option<u64>,
    /// 봉투 바이트 sha256(수용 기록 재료).
    pub envelope_sha256: Option<String>,
    pub installed_revoked: bool,
    /// 설치판 폐기 항목이 `stop_seats` 인가.
    pub stop_seats: bool,
    /// 폐기 목록에 미지 severity 가 있었다(신호 1회 대상).
    pub unknown_severity: bool,
    pub state_migration: Option<String>,
    pub min_from_release_seq: Option<u64>,
    pub halt: bool,
    pub rollout_pct: Option<u8>,
    /// 신뢰 시각 후보(수용한 봉투·폐기문 `signed_at` 최댓값) — 호출부가 `last_trusted_time` 를 올릴 때 쓴다.
    pub trusted_signed_at: Option<i64>,
    pub revocations: Option<Revocations>,
    pub envelope_signed_at: Option<i64>,
    pub notes_ko: Option<String>,
}

impl FeedOutcome {
    fn fail(verdict: Verdict, e: UpdateErr) -> FeedOutcome {
        FeedOutcome {
            verdict,
            code: e.code,
            step: e.step,
            detail: e.detail,
            asset: None,
            release_seq: None,
            version: None,
            feed_rev: None,
            envelope_sha256: None,
            installed_revoked: false,
            stop_seats: false,
            unknown_severity: false,
            state_migration: None,
            min_from_release_seq: None,
            halt: false,
            rollout_pct: None,
            trusted_signed_at: None,
            revocations: None,
            envelope_signed_at: None,
            notes_ko: None,
        }
    }

    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "verdict": self.verdict.as_str(),
            "code": self.code.as_str(),
            "step": self.step,
            "detail": self.detail,
            "asset": self.asset,
            "release_seq": self.release_seq,
            "version": self.version,
            "feed_rev": self.feed_rev,
            "envelope_sha256": self.envelope_sha256,
            "installed_revoked": self.installed_revoked,
            "stop_seats": self.stop_seats,
            "unknown_severity": self.unknown_severity,
            "state_migration": self.state_migration,
            "min_from_release_seq": self.min_from_release_seq,
            "halt": self.halt,
            "rollout_pct": self.rollout_pct,
            "revocations_rev": self.revocations.as_ref().map(|r| r.rev),
        })
    }
}

fn b64(s: &str) -> Result<Vec<u8>, String> {
    base64::engine::general_purpose::STANDARD.decode(s.trim()).map_err(|e| format!("base64: {e}"))
}

/// 단계 배포 버킷 = `sha256(install_id)` 앞 8바이트(빅엔디언) % 100.
pub fn rollout_bucket(install_id: &str) -> u8 {
    use sha2::{Digest, Sha256};
    let h = Sha256::digest(install_id.as_bytes());
    let mut b = [0u8; 8];
    b.copy_from_slice(&h[..8]);
    (u64::from_be_bytes(b) % 100) as u8
}

/// 알림 1줄 검사(발행·검증 둘 다 — §3-12 MI2): ≤80자 · 제어문자 0 · 금지 어휘 0 · 비어 있지 않음.
pub fn check_notes_ko(s: &str) -> Result<(), String> {
    if s.trim().is_empty() {
        return Err("notes_ko 비었음".into());
    }
    if s.chars().count() > NOTES_MAX_CHARS {
        return Err("notes_ko 80자 초과".into());
    }
    if s.chars().any(|c| c.is_control()) {
        return Err("notes_ko 제어문자".into());
    }
    if let Some(w) = NOTES_FORBIDDEN.iter().find(|w| s.contains(*w)) {
        return Err(format!("notes_ko 금지 어휘 {w}"));
    }
    Ok(())
}

/// ⓖ 본문 서식 계약(파싱 뒤 의미 검사).
fn check_release_shape(r: &ReleaseBody, component: &str) -> Result<(), String> {
    if r.kind != RELEASE_KIND {
        return Err(format!("본문 kind {}", r.kind));
    }
    if r.component != component {
        return Err(format!("본문 component {}≠{component}", r.component));
    }
    if r.release_seq < 1 {
        return Err("release_seq < 1".into());
    }
    if r.version.trim().is_empty() {
        return Err("version 비었음".into());
    }
    if !matches!(r.state_migration.as_str(), "none" | "additive" | "breaking") {
        return Err(format!("state_migration {}", r.state_migration));
    }
    if r.assets.is_empty() {
        return Err("assets 비었음".into());
    }
    for (k, a) in &r.assets {
        if !TARGETS.contains(&k.as_str()) {
            return Err(format!("미지 기판 {k}"));
        }
        if &a.target != k {
            return Err(format!("행 target {}≠{k}", a.target));
        }
        if a.release_seq != r.release_seq {
            return Err(format!("행 release_seq {}≠{}", a.release_seq, r.release_seq));
        }
        if !is_hex(&a.sha256, 64) {
            return Err(format!("행 {k} sha256 형식(소문자 16진 64자)"));
        }
        if a.size == 0 || a.max_unpacked == 0 {
            return Err(format!("행 {k} size/max_unpacked 0"));
        }
        // ★1R MAJOR(§6-1 공통 필수): build_id·features 칸은 모든 부품 필수 · cysr 은 bundled_pack{version, digest(64 hex)} 필수.
        if !super::mutant("M9") {
            if a.build_id.trim().is_empty() {
                return Err(format!("행 {k} build_id 비었음"));
            }
            if a.features.is_none() {
                return Err(format!("행 {k} features 칸 부재"));
            }
            if component == "cysr" {
                match &a.bundled_pack {
                    Some(bp) if !bp.version.trim().is_empty() && is_hex(&bp.digest, 64) => {}
                    _ => return Err(format!("행 {k} bundled_pack 부재·빈 값·digest 형식")),
                }
            }
        }
        // ★1R B5: 기판별 둘째 닻 필수(§4-3) — 맥 = cdhash(40 hex) + dr_pin_id(인증서 leaf sha1 40 hex) · 윈 = a2_sig_url
        //   (자산 1홉 규칙). U 서명만 있는 자산은 Apply 에 닿지 않는다.
        if component == "cysr" && !super::mutant("B5") {
            if k.starts_with("macos-") {
                if !a.cdhash.as_deref().map(|h| is_hex(h, 40)).unwrap_or(false) {
                    return Err(format!("행 {k} cdhash 부재·형식(40 hex)"));
                }
                if !a.dr_pin_id.as_deref().map(|h| is_hex(h, 40)).unwrap_or(false) {
                    return Err(format!("행 {k} dr_pin_id 부재·형식(40 hex)"));
                }
            }
            if k.starts_with("windows-") {
                match a.a2_sig_url.as_deref() {
                    Some(u) if row_url_check(component, UrlField::A2Sig, u).is_ok() => {}
                    _ => return Err(format!("행 {k} a2_sig_url 부재·허용 목록 밖")),
                }
            }
        }
        // ★U3 1R #10: 윈 페이로드 전수(cysr 윈 행 필수) · 다른 행에 실렸으면 같은 형식 검사.
        if !super::mutant("PM") {
            if component == "cysr" && k.starts_with("windows-") {
                check_payload_manifest(k, a.payload_manifest.as_ref())?;
            } else if a.payload_manifest.is_some() {
                check_payload_manifest(k, a.payload_manifest.as_ref())?;
            }
        }
    }
    check_notes_ko(&r.notes_ko)
}

/// ⓛ `requires` 계약 — 부품별 필수 키 · 빈 값·파싱 불가 거부.
fn check_requires(r: &ReleaseBody) -> Result<(), UpdateErr> {
    let s = |k: &str| r.requires.get(k).and_then(|v| v.as_str()).map(str::trim).unwrap_or("");
    match r.component.as_str() {
        "cysr" => {
            let v = s("min_binary_for_pack");
            if crate::pack::parse_semver(v).is_none() {
                return Err(UpdateErr::new(ErrCode::PackMinBinaryEmpty, "ⓛ", format!("min_binary_for_pack {v:?}")));
            }
        }
        "agora-client" => {
            if r.requires.get("min_cysr_release_seq").and_then(|v| v.as_u64()).is_none() {
                return Err(UpdateErr::new(ErrCode::VerifyFailed, "ⓛ", "min_cysr_release_seq 부재"));
            }
            if s("python").is_empty() {
                return Err(UpdateErr::new(ErrCode::VerifyFailed, "ⓛ", "requires.python 비었음"));
            }
        }
        _ => {}
    }
    for (k, v) in &r.requires {
        let empty = match v {
            serde_json::Value::Null => true,
            serde_json::Value::String(x) => x.trim().is_empty(),
            _ => false,
        };
        if empty {
            return Err(UpdateErr::new(ErrCode::VerifyFailed, "ⓛ", format!("requires.{k} 빈 값")));
        }
    }
    Ok(())
}

/// 설치판 폐기·폐기문을 결과에 싣는다 — ★1R B3: R 검증 직후 확정한 것을 뒤 단계(봉투·본문)가 어떻게 실패하든 모든 결과에.
/// `installed` = None(출발 seq 열거의 서명 단계 실패)이면 설치판 폐기 칸은 비운다(특정 설치판이 없다).
fn carry(mut o: FeedOutcome, revs: &Revocations, component: &str, installed: Option<u64>) -> FeedOutcome {
    if super::mutant("B3") {
        return o;
    }
    let inst = installed.and_then(|seq| revs.revoked(component, seq));
    o.installed_revoked = inst.is_some();
    o.stop_seats = inst.map(|r| r.severity == Severity::StopSeats).unwrap_or(false);
    o.unknown_severity = revs.revoked_releases.iter().any(|r| r.unknown_severity);
    o.revocations = Some(revs.clone());
    o.trusted_signed_at = Some(o.trusted_signed_at.unwrap_or(i64::MIN).max(revs.signed_at));
    o
}

/// ⓐ~ⓘ 를 통과한 재료(설치판 seq 와 무관한 부분 — 서명·서식·순번).
struct Checked {
    revs: Revocations,
    env: Envelope,
    env_sha: String,
    body: ReleaseBody,
}

/// ⓐ~ⓘ — 실패 = 그 결과(설치판 폐기 칸은 `installed` 로 싣는다).
fn check_signed(inp: &FeedInput, installed: Option<u64>) -> Result<Checked, Box<FeedOutcome>> {
    use Verdict::{Reject, Undetermined};

    // ⓐ 폐기문 — R 서명·rev 단조·signed_at 미래 거부(신뢰 시각 기준). 위임은 유효 키링에 반영한다.
    let revs = match verify_revocations(inp.revocations, inp.revocations_sig, inp.keyring, inp.accepted_rev, inp.now, inp.last_trusted_time) {
        Ok(r) => r,
        Err(e) => return Err(Box::new(FeedOutcome::fail(Reject, e))),
    };
    let keyring = inp.keyring.with_revocations(&revs);
    let fail = |v: Verdict, e: UpdateErr| Box::new(carry(FeedOutcome::fail(v, e), &revs, inp.component, installed));

    // ⓑ 봉투 서식.
    let fsb = |step: &str, d: String| UpdateErr::new(ErrCode::FeedSigBad, step, d);
    let env: Envelope = match serde_json::from_slice(inp.envelope) {
        Ok(e) => e,
        Err(e) => return Err(fail(Reject, fsb("ⓑ", format!("봉투 서식: {e}")))),
    };
    let shape = if env.kind != ENVELOPE_KIND {
        Err(format!("봉투 kind {}", env.kind))
    } else if env.component != inp.component || !COMPONENTS.contains(&env.component.as_str()) {
        Err(format!("봉투 component {}", env.component))
    } else if env.channel != inp.channel || !CHANNELS.contains(&env.channel.as_str()) {
        Err(format!("봉투 channel {}", env.channel))
    } else if env.rollout_pct > 100 {
        Err(format!("rollout_pct {}", env.rollout_pct))
    } else if env.signed_at > env.expires_at || env.expires_at - env.signed_at > MAX_ENVELOPE_WINDOW_SECS {
        Err("유효창 14일 초과·역전".to_string())
    } else {
        Ok(())
    };
    if let Err(d) = shape {
        return Err(fail(Reject, fsb("ⓑ", d)));
    }
    // ⓒ 봉투 키(F 용도·폐기·만료).
    if let Err(d) = keyring.find(&env.key_id, Purpose::Feed, inp.now) {
        return Err(fail(Reject, fsb("ⓒ", d)));
    }
    // ⓓ 봉투 minisign.
    if let Err(d) = keyring.verify(Purpose::Feed, &env.key_id, inp.envelope, inp.envelope_sig, inp.now) {
        return Err(fail(Reject, fsb("ⓓ", d)));
    }
    // ⓔ 유효창 — 시계 의심이면 판정하지 않는다(N13).
    if inp.clock_suspect {
        return Err(fail(Undetermined, UpdateErr::new(ErrCode::ClockSuspect, "ⓔ", "N13 시계 의심")));
    }
    if inp.now < env.signed_at || inp.now > env.expires_at {
        return Err(fail(
            Reject,
            UpdateErr::new(ErrCode::FeedExpired, "ⓔ", format!("now {} ∉ [{}, {}]", inp.now, env.signed_at, env.expires_at)),
        ));
    }
    // ⓕ feed_rev 단조(수용본 미만 = replay · ★1R B2 같은 rev = 봉투 sha256 이 같을 때만 「이미 본 봉투」 · 다르면 replay).
    // 수용 기록 손상 = 판정 불가(손상본이 신규 기기로 강등되는 길 차단).
    let env_sha = sha256_hex(inp.envelope);
    let accepted = match &inp.accepted {
        Ok(a) => a.clone(),
        Err(e) => return Err(fail(Undetermined, UpdateErr::new(ErrCode::VerifyFailed, "ⓕ", format!("수용 기록 손상: {e}")))),
    };
    if let Some(a) = &accepted {
        if env.feed_rev < a.feed_rev {
            return Err(fail(Reject, UpdateErr::new(ErrCode::FeedReplay, "ⓕ", format!("feed_rev {} < 수용 {}", env.feed_rev, a.feed_rev))));
        }
        if env.feed_rev == a.feed_rev && env_sha != a.envelope_sha256 && !super::mutant("B2") {
            return Err(fail(Reject, UpdateErr::new(ErrCode::FeedReplay, "ⓕ", format!("같은 feed_rev {} 다른 봉투", env.feed_rev))));
        }
    }
    // ⓖ 본문 서식(봉투 안 base64 원문).
    let rsb = |step: &str, d: String| UpdateErr::new(ErrCode::ReleaseSigBad, step, d);
    let (body_bytes, body_sig) = match (b64(&env.release), b64(&env.release_sig)) {
        (Ok(b), Ok(s)) => (b, s),
        (Err(e), _) | (_, Err(e)) => return Err(fail(Reject, rsb("ⓖ", e))),
    };
    let body: ReleaseBody = match serde_json::from_slice(&body_bytes) {
        Ok(b) => b,
        Err(e) => return Err(fail(Reject, rsb("ⓖ", format!("본문 서식: {e}")))),
    };
    if let Err(d) = check_release_shape(&body, inp.component) {
        return Err(fail(Reject, rsb("ⓖ", d)));
    }
    // ⓗ 본문 키(U 용도).
    if let Err(d) = keyring.find(&body.key_id, Purpose::Release, inp.now) {
        return Err(fail(Reject, rsb("ⓗ", d)));
    }
    // ⓘ 본문 minisign.
    if let Err(d) = keyring.verify(Purpose::Release, &body.key_id, &body_bytes, &body_sig, inp.now) {
        return Err(fail(Reject, rsb("ⓘ", d)));
    }
    Ok(Checked { revs, env, env_sha, body })
}

/// ⓙ~ⓝ — 설치판 `installed` 대비 판정(서명 단계를 통과한 재료로).
fn judge(inp: &FeedInput, c: &Checked, installed: u64) -> FeedOutcome {
    use Verdict::Reject;
    let (env, body) = (&c.env, &c.body);
    let base = |mut o: FeedOutcome| -> FeedOutcome {
        o.release_seq = Some(body.release_seq);
        o.version = Some(body.version.clone());
        o.feed_rev = Some(env.feed_rev);
        o.envelope_sha256 = Some(c.env_sha.clone());
        o.state_migration = Some(body.state_migration.clone());
        o.min_from_release_seq = Some(body.min_from_release_seq);
        o.halt = env.halt;
        o.rollout_pct = Some(env.rollout_pct);
        o.envelope_signed_at = Some(env.signed_at);
        o.trusted_signed_at = Some(env.signed_at);
        o.notes_ko = Some(body.notes_ko.clone());
        carry(o, &c.revs, inp.component, Some(installed))
    };

    // ⓙ 후보 릴리스가 폐기됐는가.
    if c.revs.revoked(inp.component, body.release_seq).is_some() {
        return base(FeedOutcome::fail(
            Reject,
            UpdateErr::new(ErrCode::Revoked, "ⓙ", format!("release_seq {} 폐기", body.release_seq)),
        ));
    }
    // ⓚ 설치본 대비 — 같거나 작음 = uptodate(오류 아님 · BLOCK 1·2). 설치판이 폐기됐으면 installed_revoked.
    if body.release_seq <= installed {
        let mut o = base(FeedOutcome::fail(Verdict::Uptodate, UpdateErr::new(ErrCode::Ok, "ⓚ", "")));
        if o.installed_revoked {
            o.verdict = Verdict::InstalledRevoked;
            o.code = ErrCode::InstalledRevoked;
            o.detail = format!("설치판 {installed} 폐기 · 더 새 후보 없음");
        } else {
            o.detail = format!("후보 {} ≤ 설치 {installed}", body.release_seq);
        }
        return o;
    }
    // ⓛ 출발 판 하한 · breaking(자동 대상 아님 — 1R MINOR: 게이트 배열 밖으로) · requires.
    if installed < body.min_from_release_seq {
        return base(FeedOutcome::fail(
            Reject,
            UpdateErr::new(ErrCode::VerifyFailed, "ⓛ", format!("설치 {installed} < min_from {}", body.min_from_release_seq)),
        ));
    }
    if body.state_migration == "breaking" && !super::mutant("SM") {
        return base(FeedOutcome::fail(
            Reject,
            UpdateErr::new(ErrCode::VerifyFailed, "ⓛ", "state_migration=breaking — 링크 재설치 전용"),
        ));
    }
    if let Err(e) = check_requires(body) {
        return base(FeedOutcome::fail(Reject, e));
    }
    // ⓜ 이 기판 행 · URL 허용 목록(서명된 본문의 url 도 부품별 홉 규칙을 통과해야 한다 — 키 유출 피드의 제3자 URL 차단).
    let Some(asset) = body.assets.get(inp.target).or_else(|| body.assets.get("any")).cloned() else {
        return base(FeedOutcome::fail(Reject, UpdateErr::new(ErrCode::VerifyFailed, "ⓜ", format!("기판 행 없음 {}", inp.target))));
    };
    if let Err(e) = row_url_check(inp.component, UrlField::Asset, &asset.url) {
        return base(FeedOutcome::fail(Reject, UpdateErr::new(ErrCode::UrlRefused, "ⓜ", e.detail)));
    }
    if let Some(sig_url) = &asset.a2_sig_url {
        if let Err(e) = row_url_check(inp.component, UrlField::A2Sig, sig_url) {
            return base(FeedOutcome::fail(Reject, UpdateErr::new(ErrCode::UrlRefused, "ⓜ", e.detail)));
        }
    }
    // ⓝ halt · rollout(표시 · 거부 아님).
    let mut out = base(FeedOutcome::fail(Verdict::Apply, UpdateErr::new(ErrCode::Ok, "ⓝ", "")));
    out.asset = Some(asset);
    if env.halt {
        out.verdict = Verdict::Halt;
    } else if env.rollout_pct < 100 && inp.rollout_bucket.map(|b| b >= env.rollout_pct).unwrap_or(true) {
        out.verdict = Verdict::NotInRollout;
    }
    out
}

/// 검증 함수 — **하나뿐**(§6-2). 파이썬(T3)은 이 함수를 `cys update-verify` 로 부르고 JSON 만 읽는다.
pub fn verify_feed(inp: &FeedInput) -> FeedOutcome {
    match check_signed(inp, Some(inp.installed_release_seq)) {
        Ok(c) => judge(inp, &c, inp.installed_release_seq),
        Err(o) => *o,
    }
}

/// 출발 seq 열거 결과 — 서명 단계(ⓐ~ⓘ)는 한 번 · 판정(ⓙ~ⓝ)은 출발 seq 마다.
#[derive(Debug, Clone)]
pub struct Enumerated {
    pub release_seq: u64,
    pub min_from_release_seq: u64,
    /// `(설치판 seq, 그 판정)` — `max(min_from, 1) ..= release_seq`(마지막 = 후보 자신 = uptodate 기대).
    pub results: Vec<(u64, FeedOutcome)>,
}

/// ★U3 1R #11 · 출발 seq 열거 모드(발행 게이트·`refresh-feed` 가 부른다): 「가짜 설치판 0」 하나로 판정하지 않고 본문이 허용하는
/// 출발 seq(`max(min_from, 1)` ~ 후보 직전) **각각**과 후보 자신을 같은 [`verify_feed`] 단계로 판정한다. `inp.installed_release_seq` 는
/// 쓰지 않는다(설치판이 없는 발행 쪽 질문). 서명 단계 실패 = `Err`(그 결과 하나).
pub fn verify_feed_enumerate(inp: &FeedInput) -> Result<Enumerated, FeedOutcome> {
    let c = check_signed(inp, None).map_err(|o| *o)?;
    let lo = c.body.min_from_release_seq.max(1);
    let results = (lo..=c.body.release_seq).map(|i| (i, judge(inp, &c, i))).collect();
    Ok(Enumerated { release_seq: c.body.release_seq, min_from_release_seq: c.body.min_from_release_seq, results })
}

/// 릴리스 행 URL 칸.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UrlField {
    Asset,
    A2Sig,
}

/// 부품별 행 URL 규칙(U3 `update_common.url_ok_for` 와 1:1 · 공통 벡터 = `scripts/update/url-vectors.json`):
/// cysr 자산 = github 1홉만 · agora-client 자산 = 사이트(피드 호스트)만 · `a2_sig_url` = cysr 의 github 1홉만(다른 부품 = 거부).
pub fn row_url_check(component: &str, field: UrlField, url: &str) -> Result<(), UpdateErr> {
    let hops: &[Hop] = match (component, field) {
        ("cysr", _) => &[Hop::AssetFirst],
        ("agora-client", UrlField::Asset) => &[Hop::Feed],
        _ => return Err(UpdateErr::new(ErrCode::UrlRefused, "url", format!("{component} 의 {field:?} URL 칸 없음"))),
    };
    check_url(url, hops).map(|_| ())
}

// ── 수용 기록(파일) ────────────────────────────────────────────────────────────────────

/// 수용 기록 읽기 — 부재 = `Ok(None)` · 존재하나 손상 = `Err`(판정 불가).
pub fn read_accepted(path: &std::path::Path) -> Result<Option<AcceptedFeed>, String> {
    match std::fs::read(path) {
        Ok(b) => serde_json::from_slice(&b).map(Some).map_err(|e| format!("{}: {e}", path.display())),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(format!("{}: {e}", path.display())),
    }
}

/// 수용 기록 원자 쓰기(소유자 전용 0600 · 파일·부모 fsync). ★1R MAJOR: 기존 기록이 **손상**이면 쓰지 않는다(덮어쓰기 = 단조 앵커
/// 소실) · feed_rev 후퇴·같은 rev 다른 봉투·설치 seq 후퇴 = 거부.
pub fn write_accepted(path: &std::path::Path, rec: &AcceptedFeed) -> Result<(), String> {
    match read_accepted(path) {
        Ok(Some(old)) => {
            if rec.feed_rev < old.feed_rev || rec.installed_release_seq < old.installed_release_seq {
                return Err(format!(
                    "수용 기록 후퇴 거부 (feed_rev {}→{} · 설치 seq {}→{})",
                    old.feed_rev, rec.feed_rev, old.installed_release_seq, rec.installed_release_seq
                ));
            }
            if rec.feed_rev == old.feed_rev && rec.envelope_sha256 != old.envelope_sha256 {
                return Err("같은 feed_rev 다른 봉투 — 기록 거부".into());
            }
        }
        Ok(None) => {}
        Err(e) if !super::mutant("M6") => return Err(format!("수용 기록 손상 — 쓰지 않는다: {e}")),
        Err(_) => {}
    }
    let bytes = serde_json::to_vec_pretty(rec).map_err(|e| e.to_string())?;
    super::write_private(path, &bytes)
}

// ── 시험 ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
pub(crate) mod fixture {
    //! 시험 피드 생성기(시험 키로 서명 · 실키 0). `feed` 모듈 밖(gates·cli 시험)에서도 쓴다.
    use super::super::keys::testkit::Keys;
    use super::super::keys::REVOCATIONS_KIND;
    use super::*;

    pub const NOW: i64 = 1_790_000_000;

    pub fn asset(target: &str, seq: u64) -> serde_json::Value {
        let mut v = serde_json::json!({
            "url": format!("https://github.com/oogisoogi/cys-ro/releases/download/v1.1.{seq}/cysr-{target}.zip"),
            "size": 1234, "sha256": "ab".repeat(32), "max_unpacked": 99999, "target": target,
            "build_id": format!("abc{seq}.20261006T0000Z"), "release_seq": seq,
            "bundled_pack": {"version": "1.1.8", "digest": "cd".repeat(32)}, "features": ["usage-panel"]
        });
        // 기판별 둘째 닻(1R B5 — 필수)
        if target.starts_with("macos-") {
            v["cdhash"] = serde_json::json!("ef".repeat(20));
            v["dr_pin_id"] = serde_json::json!("a426231e7dc737ee1d74962b346c23d3acacb18d");
        }
        if target.starts_with("windows-") {
            v["payload_manifest"] = serde_json::json!([
                {"path": "cys.exe", "size": 1000, "sha256": "aa".repeat(32)},
                {"path": "runtime/python312.dll", "size": 234, "sha256": "bb".repeat(32)}
            ]);
            v["a2_sig_url"] = serde_json::json!(format!("https://github.com/oogisoogi/cys-ro/releases/download/v1.1.{seq}/cysr_x64-setup.exe.sig"));
        }
        v
    }

    pub fn body_json(k: &Keys, seq: u64) -> serde_json::Value {
        serde_json::json!({
            "kind": RELEASE_KIND, "component": "cysr", "release_seq": seq, "version": format!("1.1.{seq}"),
            "key_id": k.u.key_id, "signed_at": NOW - 100, "min_from_release_seq": 1,
            "requires": {"min_binary_for_pack": "1.1.8"}, "state_migration": "none",
            "assets": {"macos-arm64": asset("macos-arm64", seq), "windows-x64": asset("windows-x64", seq)},
            "notes_ko": "자비스가 새 판으로 바뀌었어요."
        })
    }

    pub fn envelope_json(k: &Keys, body: &serde_json::Value, feed_rev: u64) -> serde_json::Value {
        let bb = body.to_string().into_bytes();
        envelope_json_raw(k, &bb, &k.u.sign(&bb), feed_rev)
    }

    pub fn envelope_json_raw(k: &Keys, body: &[u8], body_sig: &[u8], feed_rev: u64) -> serde_json::Value {
        let e = base64::engine::general_purpose::STANDARD;
        serde_json::json!({
            "kind": ENVELOPE_KIND, "component": "cysr", "channel": "stable", "feed_rev": feed_rev,
            "key_id": k.f.key_id, "signed_at": NOW - 50, "expires_at": NOW + 7 * 86_400,
            "rollout_pct": 100, "halt": false,
            "release": e.encode(body), "release_sig": e.encode(body_sig)
        })
    }

    pub fn revocations_json(k: &Keys, rev: u64, revoked: serde_json::Value) -> serde_json::Value {
        serde_json::json!({"kind": REVOCATIONS_KIND, "rev": rev, "key_id": k.r.key_id, "signed_at": NOW - 200,
            "revoked_releases": revoked})
    }

    /// 서명된 바이트 묶음(봉투·봉투 서명·폐기문·폐기문 서명).
    pub struct Signed {
        pub env: Vec<u8>,
        pub env_sig: Vec<u8>,
        pub rev: Vec<u8>,
        pub rev_sig: Vec<u8>,
    }

    pub fn sign_all(k: &Keys, env: &serde_json::Value, rev: &serde_json::Value) -> Signed {
        let env = env.to_string().into_bytes();
        let rev = rev.to_string().into_bytes();
        Signed { env_sig: k.f.sign(&env), rev_sig: k.r.sign(&rev), env, rev }
    }

    pub fn input<'a>(s: &'a Signed, kr: &'a UpdateKeyring, installed: u64) -> FeedInput<'a> {
        FeedInput {
            component: "cysr",
            channel: "stable",
            envelope: &s.env,
            envelope_sig: &s.env_sig,
            revocations: &s.rev,
            revocations_sig: &s.rev_sig,
            now: NOW,
            clock_suspect: false,
            accepted: Ok(None),
            accepted_rev: None,
            last_trusted_time: None,
            keyring: kr,
            installed_release_seq: installed,
            target: "macos-arm64",
            rollout_bucket: Some(42),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::super::keys::testkit::Keys;
    use super::fixture::*;
    use super::*;

    fn std_case(k: &Keys, seq: u64, feed_rev: u64) -> Signed {
        let body = body_json(k, seq);
        sign_all(k, &envelope_json(k, &body, feed_rev), &revocations_json(k, 1, serde_json::json!([])))
    }

    #[test]
    fn happy_path_apply_with_asset_row() {
        let k = Keys::new();
        let kr = k.keyring();
        let s = std_case(&k, 9, 5);
        let o = verify_feed(&input(&s, &kr, 8));
        assert_eq!(o.verdict, Verdict::Apply, "{o:?}");
        assert_eq!(o.code, ErrCode::Ok);
        assert_eq!(o.asset.as_ref().unwrap().target, "macos-arm64");
        assert_eq!((o.release_seq, o.feed_rev), (Some(9), Some(5)));
        assert_eq!(o.verdict.rc(), 0);
        let j = o.to_json();
        assert_eq!(j["verdict"], "apply");
        assert_eq!(j["code"], "update.ok");
    }

    /// BLOCK 1·2 회귀 핀: 같은 release_seq 재서명(봉투만 새로) = uptodate(오류 아님) · 낮은 seq = uptodate ·
    /// 높은 next 내장 바이너리가 낮은 stable 봉투를 영구 회귀로 막지 않음.
    #[test]
    fn same_or_lower_release_seq_is_uptodate_not_error() {
        let k = Keys::new();
        let kr = k.keyring();
        for installed in [9u64, 10, 50] {
            let s = std_case(&k, 9, 5);
            let o = verify_feed(&input(&s, &kr, installed));
            assert_eq!(o.verdict, Verdict::Uptodate, "installed {installed}");
            assert_eq!(o.verdict.rc(), 0);
        }
        // 같은 seq · 더 큰 feed_rev(재서명) 도 uptodate
        let s = std_case(&k, 9, 6);
        let mut i = input(&s, &kr, 9);
        i.accepted = Ok(Some(AcceptedFeed { feed_rev: 5, envelope_sha256: "00".repeat(32), feed_release_seq: 9, installed_release_seq: 9, signed_at: NOW - 900, at: NOW - 900 }));
        assert_eq!(verify_feed(&i).verdict, Verdict::Uptodate);
    }

    /// 판 문자열(`1.1.8.1`·`1.1.9-rc.1`·`1.1.8+canary.1`)은 순서에 영향 0 — release_seq 만 본다(parse_semver 한계 회귀 핀).
    #[test]
    fn version_strings_never_affect_order() {
        let k = Keys::new();
        let kr = k.keyring();
        for (ver, seq, installed, want) in [
            ("1.1.8.1", 10u64, 9u64, Verdict::Apply),
            ("1.1.8+canary.1", 10, 9, Verdict::Apply),
            ("1.1.9-rc.1", 9, 10, Verdict::Uptodate),
            ("9.9.9", 3, 4, Verdict::Uptodate),
        ] {
            let mut body = body_json(&k, seq);
            body["version"] = serde_json::json!(ver);
            let s = sign_all(&k, &envelope_json(&k, &body, 1), &revocations_json(&k, 1, serde_json::json!([])));
            assert_eq!(verify_feed(&input(&s, &kr, installed)).verdict, want, "{ver}");
        }
    }

    #[test]
    fn missing_required_fields_and_kind_cross_rejected() {
        let k = Keys::new();
        let kr = k.keyring();
        let body = body_json(&k, 9);
        // 봉투 필수 칸 부재
        for field in ["feed_rev", "expires_at", "halt", "release", "kind"] {
            let mut env = envelope_json(&k, &body, 1);
            env.as_object_mut().unwrap().remove(field);
            let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([])));
            let o = verify_feed(&input(&s, &kr, 1));
            assert_eq!((o.verdict, o.code), (Verdict::Reject, ErrCode::FeedSigBad), "{field}");
        }
        // 본문 필수 칸 부재
        for field in ["release_seq", "min_from_release_seq", "state_migration", "assets", "notes_ko"] {
            let mut b = body.clone();
            b.as_object_mut().unwrap().remove(field);
            let s = sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])));
            let o = verify_feed(&input(&s, &kr, 1));
            assert_eq!((o.verdict, o.code), (Verdict::Reject, ErrCode::ReleaseSigBad), "{field}");
        }
        // kind 교차: 봉투 자리에 본문 · 본문 자리에 봉투 · 팩 매니페스트
        let bb = body.to_string().into_bytes();
        let s = Signed { env_sig: k.f.sign(&bb), env: bb, rev: revocations_json(&k, 1, serde_json::json!([])).to_string().into_bytes(), rev_sig: vec![] };
        let s = Signed { rev_sig: k.r.sign(&s.rev), ..s };
        assert_eq!(verify_feed(&input(&s, &kr, 1)).code, ErrCode::FeedSigBad);
        let pack = serde_json::json!({"pack_version": "1.1.8", "key_id": k.f.key_id, "signed_at": NOW, "expires_at": NOW + 9});
        let s = sign_all(&k, &pack, &revocations_json(&k, 1, serde_json::json!([])));
        assert_eq!(verify_feed(&input(&s, &kr, 1)).code, ErrCode::FeedSigBad);
        let mut wrongkind = envelope_json(&k, &body, 1);
        wrongkind["kind"] = serde_json::json!(RELEASE_KIND);
        let s = sign_all(&k, &wrongkind, &revocations_json(&k, 1, serde_json::json!([])));
        assert_eq!(verify_feed(&input(&s, &kr, 1)).step, "ⓑ");
    }

    #[test]
    fn unknown_channel_component_mismatch_rejected() {
        let k = Keys::new();
        let kr = k.keyring();
        let body = body_json(&k, 9);
        let mut env = envelope_json(&k, &body, 1);
        env["channel"] = serde_json::json!("beta");
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([])));
        let mut i = input(&s, &kr, 1);
        i.channel = "beta";
        assert_eq!(verify_feed(&i).code, ErrCode::FeedSigBad);
        // 기대 채널과 다른 봉투(next 봉투를 stable 로 들이밂)
        let mut env = envelope_json(&k, &body, 1);
        env["channel"] = serde_json::json!("next");
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([])));
        assert_eq!(verify_feed(&input(&s, &kr, 1)).code, ErrCode::FeedSigBad);
        // 본문 component 가 다름
        let mut b = body.clone();
        b["component"] = serde_json::json!("agora-client");
        let s = sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])));
        assert_eq!(verify_feed(&input(&s, &kr, 1)).code, ErrCode::ReleaseSigBad);
    }

    /// 뮤테이션 축 「서명 깨짐」: 봉투·본문·폐기문 각각 1바이트 변조 = 거부.
    #[test]
    fn one_byte_tamper_each_layer_rejected() {
        let k = Keys::new();
        let kr = k.keyring();
        let s = std_case(&k, 9, 1);
        let flip = |v: &[u8]| {
            let mut x = v.to_vec();
            let i = x.len() / 2;
            x[i] ^= 0x01;
            x
        };
        let t = Signed { env: flip(&s.env), env_sig: s.env_sig.clone(), rev: s.rev.clone(), rev_sig: s.rev_sig.clone() };
        assert_eq!(verify_feed(&input(&t, &kr, 1)).verdict, Verdict::Reject);
        let t = Signed { env: s.env.clone(), env_sig: s.env_sig.clone(), rev: flip(&s.rev), rev_sig: s.rev_sig.clone() };
        let o = verify_feed(&input(&t, &kr, 1));
        assert_eq!((o.verdict, o.step.as_str()), (Verdict::Reject, "ⓐ"));
        // 본문 1바이트 변조(봉투는 F 로 다시 서명 = 봉투는 정상 · 본문 U 서명만 깨짐)
        let body = body_json(&k, 9);
        let bb = body.to_string().into_bytes();
        let sig = k.u.sign(&bb);
        let mut b2 = body.clone();
        b2["notes_ko"] = serde_json::json!("자비스가 새 판으로 바뀌었어요!"); // 서식은 그대로 · 바이트만 1자 다름
        let tampered = b2.to_string().into_bytes();
        let env = envelope_json_raw(&k, &tampered, &sig, 1);
        let t = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([])));
        let o = verify_feed(&input(&t, &kr, 1));
        assert_eq!((o.verdict, o.code, o.step.as_str()), (Verdict::Reject, ErrCode::ReleaseSigBad, "ⓘ"));
    }

    /// 키 용도 교차: F 로 본문 서명 · U 로 봉투 서명 = 거부.
    #[test]
    fn key_purpose_cross_rejected() {
        let k = Keys::new();
        let kr = k.keyring();
        let mut body = body_json(&k, 9);
        body["key_id"] = serde_json::json!(k.f.key_id);
        let bb = body.to_string().into_bytes();
        let env = envelope_json_raw(&k, &bb, &k.f.sign(&bb), 1);
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([])));
        let o = verify_feed(&input(&s, &kr, 1));
        assert_eq!((o.code, o.step.as_str()), (ErrCode::ReleaseSigBad, "ⓗ"));
        let mut env = envelope_json(&k, &body_json(&k, 9), 1);
        env["key_id"] = serde_json::json!(k.u.key_id);
        let eb = env.to_string().into_bytes();
        let rev = revocations_json(&k, 1, serde_json::json!([])).to_string().into_bytes();
        let s = Signed { env_sig: k.u.sign(&eb), env: eb, rev_sig: k.r.sign(&rev), rev };
        assert_eq!(verify_feed(&input(&s, &kr, 1)).step, "ⓒ");
    }

    /// 폐기·만료 키.
    #[test]
    fn revoked_and_expired_keys_rejected() {
        let k = Keys::new();
        let kr = k.keyring();
        let body = body_json(&k, 9);
        let env = envelope_json(&k, &body, 1);
        let mut rev = revocations_json(&k, 1, serde_json::json!([]));
        rev["revoked_key_ids"] = serde_json::json!([k.f.key_id]);
        let s = sign_all(&k, &env, &rev);
        assert_eq!(verify_feed(&input(&s, &kr, 1)).step, "ⓒ");
        let mut rev = revocations_json(&k, 1, serde_json::json!([]));
        rev["revoked_key_ids"] = serde_json::json!([k.u.key_id]);
        let s = sign_all(&k, &env, &rev);
        assert_eq!(verify_feed(&input(&s, &kr, 1)).step, "ⓗ");
        // 만료 키: 키링의 not_after 를 과거로
        let mut kr2 = kr.clone();
        for key in kr2.keys.iter_mut() {
            if key.key_id == k.f.key_id {
                key.not_after = NOW - 1;
            }
        }
        let s = std_case(&k, 9, 1);
        assert_eq!(verify_feed(&input(&s, &kr2, 1)).step, "ⓒ");
    }

    /// 뮤테이션 축 「만료」 + 유효창 밖 + 14일 초과 창.
    #[test]
    fn validity_window() {
        let k = Keys::new();
        let kr = k.keyring();
        let s = std_case(&k, 9, 1);
        let mut i = input(&s, &kr, 1);
        i.now = NOW + 8 * 86_400;
        let o = verify_feed(&i);
        assert_eq!((o.verdict, o.code), (Verdict::Reject, ErrCode::FeedExpired));
        i.now = NOW - 60; // signed_at 이전
        assert_eq!(verify_feed(&i).code, ErrCode::FeedExpired);
        let mut env = envelope_json(&k, &body_json(&k, 9), 1);
        env["expires_at"] = serde_json::json!(NOW - 50 + 14 * 86_400 + 1);
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([])));
        assert_eq!(verify_feed(&input(&s, &kr, 1)).step, "ⓑ");
    }

    /// 뮤테이션 축 「시계 의심」 = 판정 불가(rc 3).
    #[test]
    fn clock_suspect_is_undetermined() {
        let k = Keys::new();
        let kr = k.keyring();
        let s = std_case(&k, 9, 1);
        let mut i = input(&s, &kr, 1);
        i.clock_suspect = true;
        let o = verify_feed(&i);
        assert_eq!((o.verdict, o.code, o.verdict.rc()), (Verdict::Undetermined, ErrCode::ClockSuspect, 3));
    }

    /// 뮤테이션 축 「순번 역행」: feed_rev 작음 = replay · 같음 = 통과 · 수용 기록 손상 = 판정 불가.
    #[test]
    fn feed_rev_monotonic() {
        let k = Keys::new();
        let kr = k.keyring();
        let s = std_case(&k, 9, 4);
        let acc = |rev| Ok(Some(AcceptedFeed { feed_rev: rev, envelope_sha256: sha256_hex(&s.env), feed_release_seq: 9, installed_release_seq: 8, signed_at: NOW - 999, at: NOW - 999 }));
        let mut i = input(&s, &kr, 8);
        i.accepted = acc(5);
        let o = verify_feed(&i);
        assert_eq!((o.verdict, o.code), (Verdict::Reject, ErrCode::FeedReplay));
        i.accepted = acc(4);
        assert_eq!(verify_feed(&i).verdict, Verdict::Apply);
        i.accepted = Err("깨짐".into());
        assert_eq!(verify_feed(&i).verdict, Verdict::Undetermined);
        // 폐기문 rev 후퇴
        let mut i = input(&s, &kr, 8);
        i.accepted_rev = Some(2);
        assert_eq!(verify_feed(&i).code, ErrCode::FeedReplay);
    }

    /// 뮤테이션 축 「폐기 판」 + installed_revoked 3갈래(판정 쪽).
    #[test]
    fn revoked_releases_and_installed_revoked() {
        let k = Keys::new();
        let kr = k.keyring();
        let body = body_json(&k, 9);
        let env = envelope_json(&k, &body, 1);
        // 후보 9 폐기 = 거부
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([{"component": "cysr", "release_seq": 9}])));
        let o = verify_feed(&input(&s, &kr, 8));
        assert_eq!((o.verdict, o.code), (Verdict::Reject, ErrCode::Revoked));
        // 다른 부품의 같은 번호는 무관
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([{"component": "agora-client", "release_seq": 9}])));
        assert_eq!(verify_feed(&input(&s, &kr, 8)).verdict, Verdict::Apply);
        // ① 설치판 8 폐기 + 더 새 후보 9 = apply(우선 후보) · 표시 installed_revoked
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([{"component": "cysr", "release_seq": 8, "severity": "stop_seats"}])));
        let o = verify_feed(&input(&s, &kr, 8));
        assert_eq!((o.verdict, o.installed_revoked, o.stop_seats), (Verdict::Apply, true, true));
        // ②③ 설치판 9 폐기 + 후보 9(같음) = installed_revoked 판정(rc 0)
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([{"component": "cysr", "release_seq": 10}])));
        let o = verify_feed(&input(&s, &kr, 10));
        assert_eq!((o.verdict, o.code, o.verdict.rc()), (Verdict::InstalledRevoked, ErrCode::InstalledRevoked, 0));
        assert!(!o.stop_seats, "severity 부재 = advisory");
        // 미지 severity = advisory + 표시
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([{"component": "cysr", "release_seq": 10, "severity": "nuke"}])));
        let o = verify_feed(&input(&s, &kr, 10));
        assert_eq!((o.stop_seats, o.unknown_severity), (false, true));
    }

    #[test]
    fn requires_and_min_from() {
        let k = Keys::new();
        let kr = k.keyring();
        let mk = |f: &dyn Fn(&mut serde_json::Value)| {
            let mut b = body_json(&k, 9);
            f(&mut b);
            sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])))
        };
        let s = mk(&|b| b["requires"]["min_binary_for_pack"] = serde_json::json!(""));
        assert_eq!(verify_feed(&input(&s, &kr, 8)).code, ErrCode::PackMinBinaryEmpty);
        let s = mk(&|b| b["requires"] = serde_json::json!({}));
        assert_eq!(verify_feed(&input(&s, &kr, 8)).code, ErrCode::PackMinBinaryEmpty);
        let s = mk(&|b| b["requires"]["extra"] = serde_json::json!(null));
        assert_eq!(verify_feed(&input(&s, &kr, 8)).step, "ⓛ");
        let s = mk(&|b| b["min_from_release_seq"] = serde_json::json!(8));
        assert_eq!(verify_feed(&input(&s, &kr, 7)).step, "ⓛ");
        assert_eq!(verify_feed(&input(&s, &kr, 8)).verdict, Verdict::Apply);
    }

    /// ⓜ URL 허용 목록 밖 · 기판 행 없음.
    #[test]
    fn asset_url_and_target_row() {
        let k = Keys::new();
        let kr = k.keyring();
        let mut b = body_json(&k, 9);
        b["assets"]["macos-arm64"]["url"] = serde_json::json!("https://evil.example/x.zip");
        let s = sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])));
        let o = verify_feed(&input(&s, &kr, 8));
        assert_eq!((o.verdict, o.code), (Verdict::Reject, ErrCode::UrlRefused));
        let mut b = body_json(&k, 9);
        b["assets"]["windows-x64"]["a2_sig_url"] = serde_json::json!("https://github.com/idoforgod/cys-terminal/releases/download/v1/x.sig");
        let s = sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])));
        let mut i = input(&s, &kr, 8);
        i.target = "windows-x64";
        // 1R B5 뒤: a2_sig_url 은 ⓖ 본문 서식(기판별 둘째 닻 필수)에서 먼저 걸린다 — 행이 어떤 기판으로 판정되든 같은 본문 거부.
        let o = verify_feed(&i);
        assert_eq!((o.code, o.step.as_str()), (ErrCode::ReleaseSigBad, "ⓖ"));
        let s = std_case(&k, 9, 1);
        let mut i = input(&s, &kr, 8);
        i.target = "macos-x64";
        assert_eq!(verify_feed(&i).step, "ⓜ");
    }

    #[test]
    fn halt_and_rollout_bucket_edges() {
        let k = Keys::new();
        let kr = k.keyring();
        let body = body_json(&k, 9);
        let mut env = envelope_json(&k, &body, 1);
        env["halt"] = serde_json::json!(true);
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([])));
        let o = verify_feed(&input(&s, &kr, 8));
        assert_eq!((o.verdict, o.verdict.rc()), (Verdict::Halt, 0));
        let mut env = envelope_json(&k, &body, 1);
        env["rollout_pct"] = serde_json::json!(42);
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([])));
        let mut i = input(&s, &kr, 8);
        i.rollout_bucket = Some(41);
        assert_eq!(verify_feed(&i).verdict, Verdict::Apply);
        i.rollout_bucket = Some(42); // 경계: bucket < pct 만 대상
        assert_eq!(verify_feed(&i).verdict, Verdict::NotInRollout);
        i.rollout_bucket = None;
        assert_eq!(verify_feed(&i).verdict, Verdict::NotInRollout);
        let mut env = envelope_json(&k, &body, 1);
        env["rollout_pct"] = serde_json::json!(0);
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([])));
        let mut i = input(&s, &kr, 8);
        i.rollout_bucket = Some(0);
        assert_eq!(verify_feed(&i).verdict, Verdict::NotInRollout);
        let mut env = envelope_json(&k, &body, 1);
        env["rollout_pct"] = serde_json::json!(101);
        let s = sign_all(&k, &env, &revocations_json(&k, 1, serde_json::json!([])));
        assert_eq!(verify_feed(&input(&s, &kr, 8)).step, "ⓑ");
        // 버킷 함수: 결정론 · 0..100
        assert_eq!(rollout_bucket("abc"), rollout_bucket("abc"));
        assert!((0..100).contains(&rollout_bucket("x")));
    }

    #[test]
    fn notes_ko_rules() {
        assert!(check_notes_ko("자비스가 새 판으로 바뀌었어요.").is_ok());
        assert!(check_notes_ko("업데이트 실패 시 알려요").is_err());
        assert!(check_notes_ko("줄\n바꿈").is_err());
        assert!(check_notes_ko(&"가".repeat(81)).is_err());
        assert!(check_notes_ko("  ").is_err());
    }

    // ── 1R 반영 뮤테이션(각 시험 = CYS_U1_MUTANT=<번호> 로 그 가드를 끄면 적색) ─────────────────────

    /// B2: 같은 feed_rev · 다른 봉투(halt 뒤집기) = replay 거부 · 같은 봉투 = 통과.
    #[test]
    fn b2_same_feed_rev_different_envelope_is_replay() {
        let k = Keys::new();
        let kr = k.keyring();
        let body = body_json(&k, 9);
        let seen = sign_all(&k, &envelope_json(&k, &body, 5), &revocations_json(&k, 1, serde_json::json!([])));
        let mut env2 = envelope_json(&k, &body, 5);
        env2["halt"] = serde_json::json!(true);
        let other = sign_all(&k, &env2, &revocations_json(&k, 1, serde_json::json!([])));
        let acc = AcceptedFeed { feed_rev: 5, envelope_sha256: sha256_hex(&seen.env), feed_release_seq: 9, installed_release_seq: 8, signed_at: NOW - 60, at: NOW - 60 };
        let mut i = input(&other, &kr, 8);
        i.accepted = Ok(Some(acc.clone()));
        let o = verify_feed(&i);
        assert_eq!((o.verdict, o.code, o.step.as_str()), (Verdict::Reject, ErrCode::FeedReplay, "ⓕ"));
        let mut i = input(&seen, &kr, 8);
        i.accepted = Ok(Some(acc));
        assert_eq!(verify_feed(&i).verdict, Verdict::Apply);
    }

    /// B3: R 검증 뒤 어느 단계가 실패하든 설치판 stop_seats·폐기문이 결과에 남는다(후보 폐기 · 봉투 서명 깨짐).
    #[test]
    fn b3_installed_stop_seats_survives_later_failures() {
        let k = Keys::new();
        let kr = k.keyring();
        let body = body_json(&k, 9);
        let rev = revocations_json(&k, 3, serde_json::json!([
            {"component": "cysr", "release_seq": 8, "severity": "stop_seats"},
            {"component": "cysr", "release_seq": 9}
        ]));
        let s = sign_all(&k, &envelope_json(&k, &body, 1), &rev);
        let o = verify_feed(&input(&s, &kr, 8));
        assert_eq!(o.code, ErrCode::Revoked, "후보도 폐기");
        assert!(o.installed_revoked && o.stop_seats, "설치판 stop_seats 가 사라지면 안 된다");
        let mut broken = sign_all(&k, &envelope_json(&k, &body, 1), &rev);
        let n = broken.env.len() / 2;
        broken.env[n] ^= 1;
        let o = verify_feed(&input(&broken, &kr, 8));
        assert_eq!(o.verdict, Verdict::Reject);
        assert!(o.stop_seats, "봉투가 깨져도 R 서명 폐기 사실은 남는다");
        assert_eq!(o.revocations.as_ref().map(|r| r.rev), Some(3), "R 검증 통과 폐기문 = 내구 기록 재료");
    }

    /// B5: 기판별 둘째 닻 필수(맥 cdhash·dr_pin_id · 윈 a2_sig_url) · 형식.
    #[test]
    fn b5_second_anchor_required_per_target() {
        let k = Keys::new();
        let kr = k.keyring();
        type M = fn(&mut serde_json::Value);
        let cases: Vec<(&str, M)> = vec![
            ("macos-arm64", |b| { b["assets"]["macos-arm64"].as_object_mut().unwrap().remove("cdhash"); }),
            ("macos-arm64", |b| b["assets"]["macos-arm64"]["cdhash"] = serde_json::json!("XYZ")),
            ("macos-arm64", |b| { b["assets"]["macos-arm64"].as_object_mut().unwrap().remove("dr_pin_id"); }),
            ("windows-x64", |b| { b["assets"]["windows-x64"].as_object_mut().unwrap().remove("a2_sig_url"); }),
            ("windows-x64", |b| b["assets"]["windows-x64"]["a2_sig_url"] = serde_json::json!("https://evil.example/x.sig")),
        ];
        for (t, m) in cases {
            let mut b = body_json(&k, 9);
            m(&mut b);
            let s = sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])));
            let mut i = input(&s, &kr, 8);
            i.target = t;
            let o = verify_feed(&i);
            assert_eq!((o.verdict, o.code, o.step.as_str()), (Verdict::Reject, ErrCode::ReleaseSigBad, "ⓖ"), "{t}");
        }
    }

    /// MAJOR(M9): §6-1 공통 필수 칸 — features 칸 부재 · build_id 빈 값 · bundled_pack digest 빈 값 = 거부.
    #[test]
    fn m9_common_required_fields() {
        let k = Keys::new();
        let kr = k.keyring();
        type M = fn(&mut serde_json::Value);
        let cases: Vec<M> = vec![
            |b| { b["assets"]["macos-arm64"].as_object_mut().unwrap().remove("features"); },
            |b| b["assets"]["macos-arm64"]["build_id"] = serde_json::json!(" "),
            |b| b["assets"]["macos-arm64"]["bundled_pack"]["digest"] = serde_json::json!(""),
            |b| b["assets"]["macos-arm64"]["sha256"] = serde_json::json!("AB".repeat(32)),
        ];
        for m in cases {
            let mut b = body_json(&k, 9);
            m(&mut b);
            let s = sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])));
            let o = verify_feed(&input(&s, &kr, 8));
            assert_eq!((o.verdict, o.step.as_str()), (Verdict::Reject, "ⓖ"));
        }
    }

    /// MINOR(SM): breaking 은 게이트가 아니라 피드 판정(ⓛ)에서 자동 대상 밖.
    #[test]
    fn sm_breaking_release_is_feed_reject() {
        let k = Keys::new();
        let kr = k.keyring();
        let mut b = body_json(&k, 9);
        b["state_migration"] = serde_json::json!("breaking");
        let s = sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])));
        let o = verify_feed(&input(&s, &kr, 8));
        assert_eq!((o.verdict, o.step.as_str()), (Verdict::Reject, "ⓛ"));
    }

    #[test]
    fn accepted_record_roundtrip_and_no_regression() {
        let d = std::env::temp_dir().join(format!("cys-u1-acc-{}-{}", std::process::id(), NOW));
        let p = d.join("accepted-cysr-stable.json");
        assert_eq!(read_accepted(&p).unwrap(), None);
        let a = AcceptedFeed { feed_rev: 3, envelope_sha256: "aa".repeat(32), feed_release_seq: 9, installed_release_seq: 9, signed_at: NOW, at: NOW };
        write_accepted(&p, &a).unwrap();
        assert_eq!(read_accepted(&p).unwrap(), Some(a.clone()));
        assert!(write_accepted(&p, &AcceptedFeed { feed_rev: 2, ..a.clone() }).is_err());
        assert!(write_accepted(&p, &AcceptedFeed { installed_release_seq: 8, ..a.clone() }).is_err());
        assert!(write_accepted(&p, &AcceptedFeed { envelope_sha256: "bb".repeat(32), ..a.clone() }).is_err(), "같은 rev 다른 봉투");
        std::fs::write(&p, b"{bad").unwrap();
        assert!(read_accepted(&p).is_err());
        // ★1R MAJOR(M6) 뮤테이션: 손상된 기록은 덮지 않는다(단조 앵커 소실 차단)
        assert!(write_accepted(&p, &AcceptedFeed { feed_rev: 1, ..a.clone() }).is_err());
        assert_eq!(std::fs::read(&p).unwrap(), b"{bad");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★U3 1R #10 뮤테이션 PM: cysr 윈 행 `payload_manifest` 필수(부재·빈 목록·상대 아닌 경로·중복 = ⓖ 거부) · 반환 JSON 에 실림.
    #[test]
    fn pm_payload_manifest_required_on_windows_rows() {
        let k = Keys::new();
        let kr = k.keyring();
        let win = |f: &dyn Fn(&mut serde_json::Value)| {
            let mut b = body_json(&k, 9);
            f(&mut b["assets"]["windows-x64"]);
            let s = sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])));
            let mut i = input(&s, &kr, 8);
            i.target = "windows-x64";
            verify_feed(&i)
        };
        let ok = win(&|_| {});
        assert_eq!(ok.verdict, Verdict::Apply);
        let pm = &ok.to_json()["asset"]["payload_manifest"];
        assert_eq!(pm[1]["path"], "runtime/python312.dll", "검증 반환 JSON 에 페이로드 전수");
        for (why, f) in [
            ("부재", &(|a: &mut serde_json::Value| { a.as_object_mut().unwrap().remove("payload_manifest"); }) as &dyn Fn(&mut serde_json::Value)),
            ("빈 목록", &|a: &mut serde_json::Value| a["payload_manifest"] = serde_json::json!([])),
            ("상위 경로", &|a: &mut serde_json::Value| a["payload_manifest"][0]["path"] = "../cys.exe".into()),
            ("절대 경로", &|a: &mut serde_json::Value| a["payload_manifest"][0]["path"] = "/cys.exe".into()),
            ("역슬래시", &|a: &mut serde_json::Value| a["payload_manifest"][0]["path"] = "runtime\\x.dll".into()),
            ("대소문자 중복", &|a: &mut serde_json::Value| a["payload_manifest"][1]["path"] = "CYS.EXE".into()),
            ("sha256 형식", &|a: &mut serde_json::Value| a["payload_manifest"][0]["sha256"] = "AA".repeat(32).into()),
        ] {
            let o = win(f);
            assert_eq!((o.verdict, o.step.as_str()), (Verdict::Reject, "ⓖ"), "{why}: {}", o.detail);
        }
    }

    /// ★U3 1R #12: 생산자(U3 `update_common.url_ok_for`)와 같은 벡터 파일로 행 URL 규칙을 대조한다 — 같은 바이트 사본.
    /// 정본 = U3 가지 `scripts/update/url-vectors.json`(ca4c7b6a) · U3 머지 때 같은 경로·같은 바이트라 충돌 0 · 갈리면 이 시험이 적색.
    #[test]
    fn url_vectors_shared_with_u3_publisher() {
        let v: serde_json::Value = serde_json::from_str(include_str!("../../scripts/update/url-vectors.json")).unwrap();
        let cases = v["cases"].as_array().unwrap();
        assert!(cases.len() >= 10);
        for c in cases {
            let field = match c["field"].as_str().unwrap() {
                "asset" => UrlField::Asset,
                "a2_sig" => UrlField::A2Sig,
                f => panic!("미지 field {f}"),
            };
            let got = row_url_check(c["component"].as_str().unwrap(), field, c["url"].as_str().unwrap()).is_ok();
            assert_eq!(got, c["ok"].as_bool().unwrap(), "{c}");
        }
        assert!(row_url_check("agora-client", UrlField::A2Sig, "https://github.com/oogisoogi/cys-ro/releases/download/v1/x.sig").is_err());
    }

    /// ★U3 1R #11: 출발 seq 열거 — `max(min_from,1)..=후보` 각각 판정(가짜 설치판 0 없음) · 서명 단계 실패 = Err 하나.
    #[test]
    fn enumerate_judges_each_allowed_start_seq() {
        let k = Keys::new();
        let kr = k.keyring();
        let mut b = body_json(&k, 9);
        b["min_from_release_seq"] = 6.into();
        let s = sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])));
        let mut i = input(&s, &kr, 0);
        i.installed_release_seq = 12345; // 열거 모드는 이 값을 쓰지 않는다
        let en = verify_feed_enumerate(&i).unwrap();
        assert_eq!((en.release_seq, en.min_from_release_seq), (9, 6));
        let got: Vec<(u64, Verdict)> = en.results.iter().map(|(s, o)| (*s, o.verdict)).collect();
        assert_eq!(got, vec![(6, Verdict::Apply), (7, Verdict::Apply), (8, Verdict::Apply), (9, Verdict::Uptodate)]);
        // 단일 판정과 같은 단계(같은 함수) — 출발 7 의 결과 = verify_feed(설치 7)
        let mut one = input(&s, &kr, 7);
        one.installed_release_seq = 7;
        assert_eq!(verify_feed(&one).to_json(), en.results[1].1.to_json());
        // min_from 0 = 출발 1 부터(0 은 판정 대상 아님)
        let mut b = body_json(&k, 3);
        b["min_from_release_seq"] = 0.into();
        let s = sign_all(&k, &envelope_json(&k, &b, 1), &revocations_json(&k, 1, serde_json::json!([])));
        let en = verify_feed_enumerate(&input(&s, &kr, 0)).unwrap();
        assert_eq!(en.results.iter().map(|(s, _)| *s).collect::<Vec<_>>(), vec![1, 2, 3]);
        // 설치판 폐기 표시는 출발 seq 마다(2 만 stop_seats)
        let s = sign_all(&k, &envelope_json(&k, &b, 1),
            &revocations_json(&k, 1, serde_json::json!([{"component": "cysr", "release_seq": 2, "severity": "stop_seats"}])));
        let en = verify_feed_enumerate(&input(&s, &kr, 0)).unwrap();
        assert_eq!(en.results.iter().map(|(_, o)| o.stop_seats).collect::<Vec<_>>(), vec![false, true, false]);
        // 서명 깨짐 = Err
        let mut s = std_case(&k, 9, 1);
        let n = s.env.len() / 2;
        s.env[n] ^= 1;
        assert_eq!(verify_feed_enumerate(&input(&s, &kr, 0)).unwrap_err().verdict, Verdict::Reject);
    }
}
