//! 틱 · 러너 기동 · 러너 사본 · 복구기 등록(설계 AUTO-UPDATE-118 §3-1 · §3-11 「복구기 등록」 · N14 · MA8).
//!
//! - 잡 본체 `cys self-update --auto --spawn` = 러너를 **설치본 밖 사본**에서 띄우고 즉시 반환(600초 잡 시한 안 · 큰 자산은 러너가 받는다).
//! - 러너의 생사: 맥 = `ChildLifetime::Survivor`(세션 분리 — cysd 정지 중 생존 = VM M1 실측 대상 R1) · 윈 = 작업 스케줄러 일회 작업
//!   ([`super::win_task`] · COM · 명시 SDDL).
//! - 지터: 러너 시작 직후 0~45분(씨앗 = install_id 해시 · 같은 기계는 늘 비슷한 자리) · 부팅 뒤 첫 확인 15분 뒤 — 단조 시계.
//! - 복구기: 맥 LaunchAgent `com.cysjavis.cysr-update-recover`(RunAtLoad · 프로그램 = 러너 사본 `self-update --recover`) · 윈 로그온 작업.
//!   매 틱 정의를 **다시 읽어** 경로·인자·sha256 을 대조한다(어긋나면 N14 보류).

use std::path::{Path, PathBuf};

pub const AGENT_LABEL: &str = "com.cysjavis.cysr-update-recover";
pub const JITTER_MAX_SECS: u64 = 45 * 60;
pub const BOOT_GRACE_SECS: u64 = 15 * 60;
/// 시험 전용 덮어쓰기(디버그 빌드만) — LaunchAgents 폴더(실 `~/Library` 무접촉 · §7-2 격리).
pub const ENV_AGENTS_DIR: &str = "CYS_UPDATE_LAUNCHAGENTS_DIR";

/// 좌석 신원 env(러너·복구기는 좌석이 아니다 — cys.rs `SEAT_IDENTITY_ENV_KEYS` 와 같은 목록 + 갱신 토큰).
pub const SEAT_ENV: &[&str] =
    &["CYS_SEAT_TOKEN", "CYS_OWNER_TOKEN", "CYS_CHANNEL_TOKEN", "CYS_SURFACE_ID", "CYS_SURFACE_REF", "CYS_ROLE", "CYS_BOOT_NONCE", super::lock::ENV_TXN];

pub fn runner_copy_path(update_dir: &Path) -> PathBuf {
    update_dir.join("runner").join(if cfg!(windows) { "cys.exe" } else { "cys" })
}

/// 러너 사본 보장 — 그 판 `cys`(지금 실행 파일)와 sha256 이 같아야 쓴다(다르면 다시 복사 · 원자).
pub fn ensure_runner_copy(update_dir: &Path, current: &Path) -> Result<PathBuf, String> {
    let dst = runner_copy_path(update_dir);
    super::ensure_private_dir(dst.parent().ok_or("부모 없음")?)?;
    let (want, _) = super::snapshot::sha256_file(current)?;
    if super::snapshot::sha256_file(&dst).map(|(s, _)| s == want).unwrap_or(false) {
        return Ok(dst);
    }
    let (got, _) = super::snapshot::durable_copy(current, &dst)?;
    if got != want {
        return Err("러너 사본 sha256 불일치".into());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(&dst, std::fs::Permissions::from_mode(0o700)).map_err(|e| e.to_string())?;
    }
    Ok(dst)
}

/// 지터(순수): install_id 해시 → 0~`max` 초.
pub fn jitter_secs(install_id: &str, max: u64) -> u64 {
    use sha2::{Digest, Sha256};
    let h = Sha256::digest(install_id.as_bytes());
    let n = u64::from_be_bytes([h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]]);
    if max == 0 {
        0
    } else {
        n % (max + 1)
    }
}

/// 첫 확인까지 남은 대기(순수): 부팅 뒤 경과가 `BOOT_GRACE_SECS` 미만이면 그만큼 더 + 지터.
pub fn initial_wait_secs(uptime_secs: u64, jitter: u64) -> u64 {
    BOOT_GRACE_SECS.saturating_sub(uptime_secs) + jitter
}

/// 러너 기동(분리 · 즉시 반환).
pub fn spawn_runner(runner: &Path, args: &[&str]) -> Result<(), String> {
    #[cfg(windows)]
    {
        super::win_task::run_once(runner, args)
    }
    #[cfg(not(windows))]
    {
        use crate::SpawnPolicy;
        let mut c = std::process::Command::new(runner);
        c.args(args);
        for k in SEAT_ENV {
            c.env_remove(k);
        }
        c.spawn_policy(crate::ChildLifetime::Survivor);
        c.spawn().map(|_| ()).map_err(|e| format!("러너 기동: {e}"))
    }
}

// ── 복구기(N14) ──────────────────────────────────────────────────────────────

pub fn agents_dir() -> Option<PathBuf> {
    if cfg!(debug_assertions) {
        if let Some(v) = std::env::var_os(ENV_AGENTS_DIR).filter(|v| !v.is_empty()) {
            return Some(PathBuf::from(v));
        }
    }
    let home = std::env::var_os("HOME")?;
    Some(PathBuf::from(home).join("Library").join("LaunchAgents"))
}

fn xml_escape(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;")
}

/// LaunchAgent plist 본문(순수).
pub fn agent_plist(program: &Path) -> String {
    let args = [program.to_string_lossy().to_string(), "self-update".into(), "--recover".into()];
    let items: String = args.iter().map(|a| format!("\t\t<string>{}</string>\n", xml_escape(a))).collect();
    format!(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\">\n<dict>\n\t<key>Label</key>\n\t<string>{AGENT_LABEL}</string>\n\t<key>ProgramArguments</key>\n\t<array>\n{items}\t</array>\n\t<key>RunAtLoad</key>\n\t<true/>\n</dict>\n</plist>\n"
    )
}

/// plist 에서 ProgramArguments 를 읽는다(순수 · 우리가 쓴 꼴만 — 다른 꼴 = None = 불일치).
pub fn plist_program_args(text: &str) -> Option<Vec<String>> {
    let a = text.find("<key>ProgramArguments</key>")?;
    let rest = &text[a..];
    let s = rest.find("<array>")? + "<array>".len();
    let e = rest.find("</array>")?;
    let mut out = Vec::new();
    for part in rest[s..e].split("<string>").skip(1) {
        let v = part.split("</string>").next()?;
        out.push(v.replace("&quot;", "\"").replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&"));
    }
    if !text.contains(&format!("<string>{AGENT_LABEL}</string>")) || !text.contains("<key>RunAtLoad</key>\n\t<true/>") {
        return None;
    }
    Some(out)
}

/// 복구기 등록 대조(N14 사실 · 순수에 가까움): 정의를 다시 읽어 인자 배열 = 기대 · 러너 사본 존재 · sha256 = 지금 판.
pub fn recover_agent_ok(update_dir: &Path, current: &Path) -> Option<bool> {
    let runner = runner_copy_path(update_dir);
    let (want, _) = super::snapshot::sha256_file(current).ok()?;
    let copy_ok = super::snapshot::sha256_file(&runner).map(|(s, _)| s == want).unwrap_or(false);
    #[cfg(windows)]
    {
        let reg = super::win_task::recover_task_ok(&runner);
        return Some(copy_ok && reg.unwrap_or(false));
    }
    #[cfg(not(windows))]
    {
        let dir = agents_dir()?;
        let text = std::fs::read_to_string(dir.join(format!("{AGENT_LABEL}.plist"))).ok();
        let want_args = vec![runner.to_string_lossy().to_string(), "self-update".into(), "--recover".into()];
        Some(copy_ok && text.as_deref().and_then(plist_program_args) == Some(want_args))
    }
}

/// 복구기 등록(멱등 · 1.1.8 첫 틱 · 어긋나면 다시 쓴다). 실 `launchctl` 은 시험 덮어쓰기 폴더일 때 부르지 않는다.
pub fn ensure_recover_agent(update_dir: &Path, current: &Path) -> Result<(), String> {
    let runner = ensure_runner_copy(update_dir, current)?;
    if recover_agent_ok(update_dir, current) == Some(true) {
        return Ok(());
    }
    #[cfg(windows)]
    {
        super::win_task::register_recover_task(&runner)
    }
    #[cfg(not(windows))]
    {
        let dir = agents_dir().ok_or("LaunchAgents 폴더 모름")?;
        std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
        let path = dir.join(format!("{AGENT_LABEL}.plist"));
        super::journal::durable_write(&path, agent_plist(&runner).as_bytes())?;
        let isolated = cfg!(debug_assertions) && std::env::var_os(ENV_AGENTS_DIR).is_some();
        if cfg!(target_os = "macos") && !isolated {
            // SAFETY: 인자 없는 조회.
            let uid = unsafe { libc::getuid() };
            let dom = format!("gui/{uid}");
            let _ = std::process::Command::new("/bin/launchctl").args(["bootout", &dom]).arg(&path).output();
            let o = std::process::Command::new("/bin/launchctl").args(["bootstrap", &dom]).arg(&path).output().map_err(|e| e.to_string())?;
            if !o.status.success() {
                return Err(format!("launchctl bootstrap: {}", String::from_utf8_lossy(&o.stderr)));
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn jitter_is_stable_and_bounded() {
        let a = jitter_secs("0123456789abcdef0123456789abcdef", JITTER_MAX_SECS);
        assert_eq!(a, jitter_secs("0123456789abcdef0123456789abcdef", JITTER_MAX_SECS), "같은 기계 = 같은 자리");
        assert!(a <= JITTER_MAX_SECS);
        assert_ne!(a, jitter_secs("ffffffffffffffffffffffffffffffff", JITTER_MAX_SECS));
        assert_eq!(initial_wait_secs(0, 10), BOOT_GRACE_SECS + 10);
        assert_eq!(initial_wait_secs(10_000, 10), 10);
    }

    #[test]
    fn plist_roundtrip_and_tamper_is_detected() {
        let p = agent_plist(Path::new("/U s/&a/.cys/update/runner/cys"));
        assert_eq!(plist_program_args(&p).unwrap(), vec!["/U s/&a/.cys/update/runner/cys", "self-update", "--recover"]);
        assert!(plist_program_args(&p.replace("--recover", "--run")).unwrap()[2] == "--run");
        assert!(plist_program_args(&p.replace("<true/>", "<false/>")).is_none(), "RunAtLoad 꺼짐 = 불일치");
    }

    /// N14 경로(P4 맥판): 등록 → 대조 통과 → 정의 지움 → 불일치(보류) → 다시 등록 → 통과. 격리 폴더 · launchctl 0.
    #[cfg(unix)]
    #[test]
    fn recover_agent_register_verify_delete_reregister() {
        let _l = crate::update::TEST_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let d = std::env::temp_dir().join(format!("cys-u2-agent-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        let cur = d.join("cys-current");
        std::fs::write(&cur, b"binary v1").unwrap();
        std::env::set_var(ENV_AGENTS_DIR, d.join("agents"));
        let upd = d.join("update");
        assert_eq!(recover_agent_ok(&upd, &cur), Some(false));
        ensure_recover_agent(&upd, &cur).unwrap();
        assert_eq!(recover_agent_ok(&upd, &cur), Some(true));
        std::fs::remove_file(d.join("agents").join(format!("{AGENT_LABEL}.plist"))).unwrap();
        assert_eq!(recover_agent_ok(&upd, &cur), Some(false), "정의 지움 = N14 보류");
        ensure_recover_agent(&upd, &cur).unwrap();
        assert_eq!(recover_agent_ok(&upd, &cur), Some(true));
        std::fs::write(&cur, b"binary v2").unwrap(); // 판이 바뀌면 사본 sha 불일치
        assert_eq!(recover_agent_ok(&upd, &cur), Some(false));
        ensure_recover_agent(&upd, &cur).unwrap();
        assert_eq!(recover_agent_ok(&upd, &cur), Some(true), "사본 다시 복사");
        std::env::remove_var(ENV_AGENTS_DIR);
    }
}
