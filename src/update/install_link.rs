//! 설치 링크(`bootstrap.sh`·`bootstrap.ps1`) 입구 2개 — 설계 AUTO-UPDATE-118 §3-2(복구기 선행) · §3-7 ②(윈 롤백 자산 · N7) · U5.
//!
//! - `cys self-update --journal-state --json` = 저널 판정만(쓰기 0 · 잠금 0). 설치 링크가 잠금을 잡은 **뒤** 부른다 —
//!   `terminal:false`(온전한 저널이 비종결) = 「복구 대기」로 끝 · `journal: degraded|corrupt` = 📌18 재설치 경로라 끝까지 간다.
//! - `cys self-update --preserve-installer --setup <방금 깐 설치기> --json` = `installers/<seq>/` 에 설치판 본문·서명·설치기·A2 서명
//!   4파일을 놓는다(seq = **이 바이너리의** release_seq · 본문은 불변 보관소 `<피드 뿌리>/cysr/releases/<seq>.json(.minisig)` ·
//!   A2 서명은 본문 행의 `a2_sig_url`). 놓기 = 러너 S11 보존(`realops::preserve_release`)과 같은 꼴(임시 폴더 → 재검증 → rename).
//!   호출자(설치 링크)가 `txn.lock` 을 쥔 채 부른다 — 이 입구는 잠금을 잡지 않는다(잡으면 자기 잠금에 막힌다).

use super::realops::{verify_installer_dir_with, REL_BODY, REL_SIG, SETUP, SETUP_SIG};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

/// 저널 판정 JSON(`journal` ∈ none·ok·degraded·corrupt · `state` · `terminal` · `lock_held`).
/// `--journal-state` 본체 = [`journal_state`] + 이 바이너리 판 `seq` · `assets`(= `--assets`)면 롤백 자산 재검증(`n7_installer` = check::installer_assets_ok ·
/// 러너 N7 과 같은 판정). ★3판(Opus 2R N10): 설치 링크는 자산 「있음」을 스스로 보지 않고 이 값을 쓴다. ★4판(Opus 3R m3): 재검증(설치기 전체 읽기 +
/// 서명)은 무거워 저널 판정과 떼었다 — 저널 판정 호출은 `--assets` 없이(느린 디스크·백신 검사가 저널 판정 시한을 먹지 않게).
pub fn link_state(dir: &Path, assets: bool) -> Value {
    let mut v = journal_state(dir);
    let seq = super::buildinfo::release_seq();
    v["seq"] = serde_json::json!(seq);
    if assets {
        v["n7_installer"] = serde_json::json!(super::check::installer_assets_ok(dir, seq));
    }
    v
}

pub fn journal_state(dir: &Path) -> Value {
    use super::journal::ReadOutcome;
    let lock_held = if dir.join(super::lock::LOCK_FILE).exists() { super::lock::is_held(dir) } else { Some(false) };
    let (kind, j, detail) = match super::journal::read(dir) {
        ReadOutcome::Absent => ("none", None, None),
        ReadOutcome::Ok(j) => ("ok", Some(j), None),
        ReadOutcome::Degraded(j, e) => ("degraded", Some(j), Some(e)),
        ReadOutcome::Corrupt(e) => ("corrupt", None, Some(e)),
    };
    let state = j.as_ref().and_then(|j| serde_json::to_value(j.state).ok());
    // none = 종결로 읽는다(트랜잭션 없음) · 손상(degraded·corrupt) = 판정 없음(null — 설치 링크는 📌18 경로로 끝까지 간다)
    let terminal = match kind {
        "none" => Some(true),
        "ok" => j.as_ref().map(|j| j.state.is_terminal()),
        _ => None,
    };
    json!({"journal": kind, "state": state, "terminal": terminal, "lock_held": lock_held, "detail": detail})
}

/// 보존 실패 — rc 2 = 검증 거부(본문·설치기·서명이 맞지 않음) · 4 = 본문·서명을 받지 못함(보관소에 없음·연결 안 됨) · 3 = 쓰기·판정 불가.
#[derive(Debug)]
pub struct PreserveErr {
    pub rc: i32,
    pub reason: &'static str,
    pub detail: String,
}

fn perr(rc: i32, reason: &'static str, d: impl Into<String>) -> PreserveErr {
    PreserveErr { rc, reason, detail: d.into() }
}

/// ★U2 후속 3판 ②(받기 공용 1벌 · 설치 링크 = 이 파일 · 러너 = `realops::fill_installer_dir`): 보관소 본문 받기·검증 — `cysr/releases/<seq>.json`
/// (+`.minisig`) → U 서명·서식 → seq 일치 → 이 기판 행. seq 0 = 발행판 아님(거부).
pub(crate) fn fetch_archive_body(
    seq: u64,
    kr: &super::keys::UpdateKeyring,
    fetch_body: &dyn Fn(&str) -> Result<Vec<u8>, String>,
) -> Result<(Vec<u8>, Vec<u8>, super::feed::Asset), PreserveErr> {
    if seq == 0 {
        return Err(perr(3, "seq_zero", "release_seq 0 = 발행판이 아닌 빌드(보관소에 본문 없음)"));
    }
    let rel = format!("cysr/releases/{seq}.json");
    let body = fetch_body(&rel).map_err(|e| perr(4, "body_unreachable", format!("{rel}: {e}")))?;
    let sig = fetch_body(&format!("{rel}.minisig")).map_err(|e| perr(4, "body_unreachable", format!("{rel}.minisig: {e}")))?;
    let rb = super::feed::verify_release_body(&body, &sig, "cysr", kr).map_err(|e| perr(2, "body_rejected", e))?;
    if rb.release_seq != seq {
        return Err(perr(2, "body_rejected", format!("본문 seq {} ≠ 이 판 {seq}", rb.release_seq)));
    }
    let row = rb.assets.values().find(|a| a.target == super::buildinfo::TARGET).cloned().ok_or_else(|| perr(2, "body_rejected", "이 대상 행 없음"))?;
    Ok((body, sig, row))
}

/// ★U2 후속 3판 ②(공용 1벌): 검증된 본문·서명 + 설치기 바이트 + A2 서명 → `installers/<seq>/` 4파일 놓기(멱등 = 이미 재검증 통과 + 본문 바이트
/// 같음 → 그대로 · 아니면 소유자 전용 임시 폴더 → 내구 쓰기 → 재검증 → rename + 폴더 fsync).
pub(crate) fn place_installer_files(
    update_dir: &Path,
    seq: u64,
    body: &[u8],
    sig: &[u8],
    setup: &[u8],
    a2: &[u8],
    kr: &super::keys::UpdateKeyring,
) -> Result<PathBuf, PreserveErr> {
    let dst = update_dir.join("installers").join(seq.to_string());
    if verify_installer_dir_with(&dst, seq, true, body, sig, kr).is_ok() && std::fs::read(dst.join(REL_BODY)).ok().as_deref() == Some(body) {
        return Ok(dst); // 이미 놓여 있고 재검증 통과(멱등)
    }
    let w = |e: String| perr(3, "write_failed", e);
    let parent = dst.parent().ok_or_else(|| w("installers 부모 없음".into()))?;
    super::ensure_private_dir(parent).map_err(w)?;
    let tmp = parent.join(format!(".{seq}.tmp"));
    let _ = std::fs::remove_dir_all(&tmp);
    super::ensure_private_dir(&tmp).map_err(w)?;
    super::journal::durable_write(&tmp.join(REL_BODY), body).map_err(w)?;
    super::journal::durable_write(&tmp.join(REL_SIG), sig).map_err(w)?;
    super::journal::durable_write(&tmp.join(SETUP), setup).map_err(w)?;
    super::journal::durable_write(&tmp.join(SETUP_SIG), a2).map_err(w)?;
    if let Err(e) = verify_installer_dir_with(&tmp, seq, true, body, sig, kr) {
        let _ = std::fs::remove_dir_all(&tmp);
        return Err(perr(2, "setup_mismatch", format!("보존본 재검증: {e}")));
    }
    if dst.exists() {
        std::fs::remove_dir_all(&dst).map_err(|e| w(e.to_string()))?;
    }
    std::fs::rename(&tmp, &dst).map_err(|e| w(e.to_string()))?;
    super::journal::sync_dir(parent).map_err(w)?;
    Ok(dst)
}

/// `installers/<seq>/` 4파일 놓기(멱등 — 이미 재검증 통과면 그대로). `fetch_body(rel)` = 보관소 상대 경로 → 바이트 ·
/// `fetch_sig(url)` = 본문 행 `a2_sig_url` → A2 서명 바이트(`setup_sig` 를 주면 부르지 않는다). ★U2 후속 3판: 본문 받기·놓기 = 공용 함수.
pub fn preserve_installer(
    update_dir: &Path,
    seq: u64,
    setup: &Path,
    setup_sig: Option<&Path>,
    kr: &super::keys::UpdateKeyring,
    fetch_body: &dyn Fn(&str) -> Result<Vec<u8>, String>,
    fetch_sig: &dyn Fn(&str) -> Result<Vec<u8>, String>,
) -> Result<PathBuf, PreserveErr> {
    let (body, sig, row) = fetch_archive_body(seq, kr, fetch_body)?;
    let setup_bytes = std::fs::read(setup).map_err(|e| perr(3, "setup_unreadable", format!("{}: {e}", setup.display())))?;
    if super::feed::sha256_hex(&setup_bytes) != row.sha256 {
        return Err(perr(2, "setup_mismatch", "설치기 sha256 ≠ 본문 행(방금 깐 설치기가 이 판의 것이 아님)"));
    }
    let sig_bytes = match setup_sig {
        Some(p) => std::fs::read(p).map_err(|e| perr(3, "sig_unreadable", format!("{}: {e}", p.display())))?,
        None => {
            let url = row.a2_sig_url.as_deref().ok_or_else(|| perr(2, "body_rejected", "본문 행에 a2_sig_url 없음"))?;
            fetch_sig(url).map_err(|e| perr(4, "sig_unreachable", format!("{url}: {e}")))?
        }
    };
    place_installer_files(update_dir, seq, &body, &sig, &setup_bytes, &sig_bytes, kr)
}

/// CLI 본체(`--preserve-installer`) — JSON 1줄 + rc(0 놓음·재검증 통과 · 2 거부 · 3 쓰기·판정 불가 · 4 받지 못함).
pub fn run_preserve(setup: &Path, setup_sig: Option<&Path>, seq_override: Option<u64>, json_out: bool) -> i32 {
    let out = |v: Value, rc: i32| -> i32 {
        if json_out {
            println!("{v}");
        } else {
            println!("ok={} {}", rc == 0, v["detail"].as_str().or(v["dir"].as_str()).unwrap_or(""));
        }
        rc
    };
    // seq = 이 바이너리 판(설치 링크가 방금 깐 cys) — 다른 판 지정은 시험 빌드만
    let seq = match seq_override {
        Some(s) if cfg!(debug_assertions) => s,
        Some(_) => return out(json!({"ok": false, "reason": "seq_override", "detail": "--seq 는 시험 빌드 전용"}), 2),
        None => super::buildinfo::release_seq(),
    };
    let dir = match super::buildinfo::state_dir() {
        Ok(d) => d,
        Err(e) => return out(json!({"ok": false, "reason": "state_dir", "detail": e}), 3),
    };
    let kr = match super::keys::UpdateKeyring::embedded() {
        Ok(k) => k,
        Err(e) => return out(json!({"ok": false, "reason": "keyring", "detail": e}), 3),
    };
    let base = super::net::feed_base(cfg!(debug_assertions), |k| std::env::var(k).ok());
    let fetch_body = |rel: &str| -> Result<Vec<u8>, String> {
        super::net::fetch_feed_file(&base, rel).map(|f| f.bytes).map_err(|e| format!("{e:?}"))
    };
    let fetch_sig = |url: &str| -> Result<Vec<u8>, String> {
        super::net::fetch(url, super::url::Hop::AssetFirst, 64 * 1024).map(|f| f.bytes).map_err(|e| format!("{e:?}"))
    };
    match preserve_installer(&dir, seq, setup, setup_sig, &kr, &fetch_body, &fetch_sig) {
        Ok(d) => {
            let n7 = super::check::installer_assets_ok(&dir, seq);
            out(json!({"ok": n7, "seq": seq, "dir": d, "n7_installer": n7}), if n7 { 0 } else { 3 })
        }
        Err(e) => out(json!({"ok": false, "seq": seq, "reason": e.reason, "detail": e.detail}), e.rc),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::update::feed::fixture::body_json;
    use crate::update::keys::testkit::Keys;

    struct Fx {
        d: PathBuf,
        k: Keys,
        setup: Vec<u8>,
        body: Vec<u8>,
        sig: Vec<u8>,
    }

    fn fx(tag: &str, seq: u64) -> Fx {
        let k = Keys::new();
        let d = std::env::temp_dir().join(format!("cys-u5-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(d.join("dl")).unwrap();
        let setup = b"MZ-cysr-setup-u5".to_vec();
        let mut body = body_json(&k, seq);
        for a in body["assets"].as_object_mut().unwrap().values_mut() {
            a["sha256"] = json!(crate::update::feed::sha256_hex(&setup));
            // 대상 행이 기판마다 달라(맥 시험 = macos 행) 모든 행에 A2 서명 자리를 둔다 — 서명 받기 경로(fetch_sig)를 기판 무관하게 태운다
            a["a2_sig_url"] = json!(format!("https://github.com/oogisoogi/cys-ro/releases/download/v1.1.{seq}/cysr_1.1.{seq}_x64-setup.exe.sig"));
        }
        let body = body.to_string().into_bytes();
        let sig = k.u.sign(&body);
        std::fs::write(d.join("dl/setup.exe"), &setup).unwrap();
        std::fs::write(d.join("dl/setup.exe.sig"), k.a2.sign(&setup)).unwrap();
        Fx { d, k, setup, body, sig }
    }

    impl Fx {
        fn upd(&self) -> PathBuf {
            self.d.join("upd")
        }
        fn run(&self, seq: u64, archive: &dyn Fn(&str) -> Result<Vec<u8>, String>) -> Result<PathBuf, PreserveErr> {
            let sigurl = |_: &str| -> Result<Vec<u8>, String> { Ok(std::fs::read(self.d.join("dl/setup.exe.sig")).unwrap()) };
            preserve_installer(&self.upd(), seq, &self.d.join("dl/setup.exe"), None, &self.k.keyring(), archive, &sigurl)
        }
        fn archive(&self) -> impl Fn(&str) -> Result<Vec<u8>, String> + '_ {
            move |rel: &str| {
                if rel.ends_with(".minisig") {
                    Ok(self.sig.clone())
                } else {
                    Ok(self.body.clone())
                }
            }
        }
    }

    impl Drop for Fx {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.d);
        }
    }

    /// U5 ③(§3-7 ② · N7): 신설치 뒤 `installers/<seq>/` 4파일 실재 + `verify_installer_dir_with(.., true)` Ok + N7 설치기 판정 참 ·
    /// 멱등(두 번째 = 그대로) · 뮤테이션: 4파일 중 하나라도 없으면 N7 거짓.
    #[test]
    fn preserve_places_four_files_and_n7_holds() {
        let f = fx("place", 8);
        let dst = f.run(8, &f.archive()).unwrap();
        for n in [REL_BODY, REL_SIG, SETUP, SETUP_SIG] {
            assert!(dst.join(n).is_file(), "{n} 실재");
        }
        assert_eq!(std::fs::read(dst.join(SETUP)).unwrap(), f.setup);
        assert!(verify_installer_dir_with(&dst, 8, true, &f.body, &f.sig, &f.k.keyring()).is_ok());
        assert!(crate::update::check::installer_assets_ok_with(&f.upd(), 8, &f.k.keyring()), "N7 설치기 판정 = 참");
        assert!(!f.upd().join("installers/.8.tmp").exists(), "임시 폴더 0");
        assert_eq!(f.run(8, &f.archive()).unwrap(), dst, "멱등");
        for n in [REL_BODY, REL_SIG, SETUP, SETUP_SIG] {
            let keep = std::fs::read(dst.join(n)).unwrap();
            std::fs::remove_file(dst.join(n)).unwrap();
            assert!(!crate::update::check::installer_assets_ok_with(&f.upd(), 8, &f.k.keyring()), "{n} 없음 = N7 거짓");
            std::fs::write(dst.join(n), keep).unwrap();
        }
        assert!(crate::update::check::installer_assets_ok_with(&f.upd(), 8, &f.k.keyring()));
    }

    /// 보관소에 본문이 없음(404) = rc 4 명시 실패 · 폴더 0(hold 로 조용히 넘어가지 않는다) · 다른 판 설치기·본문 seq 불일치 = rc 2 · seq 0 = rc 3.
    #[test]
    fn preserve_refuses_explicitly() {
        let f = fx("refuse", 8);
        let gone = |rel: &str| -> Result<Vec<u8>, String> { Err(format!("{rel}: HTTP 404")) };
        let e = f.run(8, &gone).unwrap_err();
        assert_eq!((e.rc, e.reason), (4, "body_unreachable"), "{e:?}");
        assert!(!f.upd().join("installers").exists(), "받지 못하면 아무것도 놓지 않는다");
        let e = f.run(9, &f.archive()).unwrap_err();
        assert_eq!((e.rc, e.reason), (2, "body_rejected"), "본문 seq 8 ≠ 이 판 9: {e:?}");
        std::fs::write(f.d.join("dl/setup.exe"), b"MZ-other").unwrap();
        let e = f.run(8, &f.archive()).unwrap_err();
        assert_eq!((e.rc, e.reason), (2, "setup_mismatch"), "{e:?}");
        assert_eq!(f.run(0, &f.archive()).unwrap_err().rc, 3);
        assert!(!f.upd().join("installers/8").exists());
    }

    /// CLI 종단(디버그 빌드 · 격리 상태 폴더 · 시험 키링 · file:// 보관소): rc 0 + 4파일 · 보관소에 그 판 없음 = rc 4 · 시험 빌드 밖 `--seq` 는 없다.
    #[test]
    fn run_preserve_end_to_end_with_file_archive() {
        let _l = crate::update::TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let f = fx("cli", 8);
        std::fs::create_dir_all(f.d.join("site/cysr/releases")).unwrap();
        std::fs::write(f.d.join("site/cysr/releases/8.json"), &f.body).unwrap();
        std::fs::write(f.d.join("site/cysr/releases/8.json.minisig"), &f.sig).unwrap();
        std::fs::write(f.d.join("kr.json"), f.k.keyring_json()).unwrap();
        let _e = (
            crate::pack::EnvGuard::set("CYS_UPDATE_STATE_DIR", f.upd()),
            crate::pack::EnvGuard::set("CYS_UPDATE_TEST_KEYRING", f.d.join("kr.json")),
            crate::pack::EnvGuard::set(crate::update::net::ENV_FEED_URL, format!("file://{}", f.d.join("site").display())),
        );
        let sig = f.d.join("dl/setup.exe.sig");
        assert_eq!(run_preserve(&f.d.join("dl/setup.exe"), Some(&sig), Some(8), true), 0);
        assert!(crate::update::check::installer_assets_ok(&f.upd(), 8), "embedded(시험 키링 env) 판정도 참");
        assert_eq!(run_preserve(&f.d.join("dl/setup.exe"), Some(&sig), Some(9), true), 4, "보관소에 9 없음 = rc 4");
        assert!(!f.upd().join("installers/9").exists());
        // ★브리프 ④: 놓은 뒤 N7(`rollback_assets_ok` 그 함수 · 윈 갈래) = Some(true) · 4파일 중 하나라도 빠지면 Some(false)
        std::fs::write(f.upd().join("state.json"), r#"{"last_backup_bytes": 1}"#).unwrap();
        let o = n7_outcome(&f);
        let n7 = |win: bool| crate::update::check::rollback_assets_ok_at(&f.upd(), &f.d.join("pack"), Some(&o), 8, win);
        assert_eq!(n7(true), Some(true), "신설치 뒤 N7 = Some(true)");
        for n in [REL_BODY, REL_SIG, SETUP, SETUP_SIG] {
            let p = f.upd().join("installers/8").join(n);
            let keep = std::fs::read(&p).unwrap();
            std::fs::remove_file(&p).unwrap();
            assert_eq!(n7(true), Some(false), "{n} 누락 = N7 Some(false)");
            assert_eq!(n7(false), Some(true), "맥 갈래는 설치기 자산을 보지 않는다(§3-6 세대 백업)");
            std::fs::write(&p, keep).unwrap();
        }
        assert_eq!(crate::update::check::rollback_assets_ok_at(&f.upd(), &f.d.join("pack"), Some(&o), 9, true), Some(false), "다른 판 seq = 자산 없음");
    }

    /// N7 판정용 후보(공간 칸만 의미 — 자산 크기 작게).
    fn n7_outcome(f: &Fx) -> crate::update::feed::FeedOutcome {
        let rb: crate::update::feed::ReleaseBody = serde_json::from_slice(&f.body).unwrap();
        let mut a = rb.assets.values().next().unwrap().clone();
        a.size = 1;
        a.max_unpacked = 1;
        crate::update::feed::FeedOutcome {
            verdict: crate::update::feed::Verdict::Apply,
            code: crate::update::errors::ErrCode::Ok,
            step: String::new(),
            detail: String::new(),
            asset: Some(a),
            release_seq: Some(9),
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
            release_b64: None,
            release_sig_b64: None,
        }
    }

    /// 저널 판정: 없음 = 종결 · 온전 비종결 = terminal false · 손상 = corrupt(terminal null → 설치 링크는 📌18 경로로 진행).
    #[test]
    fn journal_state_reports_terminal_and_damage() {
        let d = std::env::temp_dir().join(format!("cys-u5-js-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        let v = journal_state(&d);
        assert_eq!((v["journal"].as_str(), v["terminal"].as_bool()), (Some("none"), Some(true)));
        crate::update::journal::advance(&d, &"ab".repeat(16), 1, crate::update::journal::State::Locked, |_| {}).unwrap();
        let v = journal_state(&d);
        assert_eq!((v["journal"].as_str(), v["terminal"].as_bool()), (Some("ok"), Some(false)), "{v}");
        std::fs::write(d.join(crate::update::journal::JOURNAL_FILE), b"{broken").unwrap();
        let v = journal_state(&d);
        assert_eq!(v["journal"].as_str(), Some("corrupt"), "{v}");
        assert!(v["terminal"].is_null());
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★3판(Opus 2R N10): `--journal-state` = 저널 칸 그대로 + seq·n7_installer(= check::installer_assets_ok) — 자산 없음·가짜 4파일 = false.
    #[test]
    fn link_state_adds_seq_and_n7_from_reverification() {
        let d = std::env::temp_dir().join(format!("cys-u5-ls-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        let v = link_state(&d, false);
        assert_eq!(v["journal"].as_str(), Some("none"));
        assert_eq!(v["seq"].as_u64(), Some(crate::update::buildinfo::release_seq()));
        assert!(v.get("n7_installer").is_none(), "--assets 없으면 재검증 0(4판 m3)");
        let v = link_state(&d, true);
        assert_eq!(v["n7_installer"].as_bool(), Some(false), "자산 없음");
        let s = d.join("installers").join(crate::update::buildinfo::release_seq().to_string());
        std::fs::create_dir_all(&s).unwrap();
        for n in ["release.json", "release.json.minisig", "setup.exe", "setup.exe.sig"] {
            std::fs::write(s.join(n), b"x").unwrap();
        }
        assert_eq!(link_state(&d, true)["n7_installer"].as_bool(), Some(false), "있음만으로는 참이 아니다(재검증)");
        let _ = std::fs::remove_dir_all(&d);
    }
}
