//! ★1.1.16(TICKET=cysr-1116-debt-d-1119 ⑤ · [master#c0262f9c]) 설치·판 올림 직후 미리 데우기 — 새로 쓴 cys·cysd·cysr 를 `--version` 으로 1회씩 실행한다.
//!
//! 왜: 새로 쓴 실행 파일의 **첫 실행**은 OS 검사(맥 syspolicyd·윈 SmartScreen/백신 첫 스캔)로 느리다 — flaky 좌석 실측 첫 실행 1.3~3.0s ·
//! 해소기 2s 시한 20회 중 1회 강등(메모 「맥 첫 exec 검사 × 스텁 2s 시한」). 그 첫 실행을 시한 있는 사용자 경로(훅·해소기·자동 기동)가
//! 아니라 설치 단계가 떠안게 한다. 실패해도 설치·갱신은 계속(값 = 로그 1줄뿐).
//!
//! 부르는 곳: 업데이터 교체 직후(`realops::start_new` · 새 데몬 기동 전) · 설치 끝 = `cys daemon prime`(설치기 bootstrap.sh·ps1·NSIS 가 1회).

use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

/// 데우는 실행 파일(이 순서).
pub const PRIME_NAMES: [&str; 3] = ["cys", "cysd", "cysr"];
/// 한 개 상한 — 넘으면 그 자식만 끝내고 다음으로(설치를 멈추지 않는다).
pub const PRIME_CAP: Duration = Duration::from_secs(10);

/// 한 실행 파일의 결과.
#[derive(Debug, Clone, PartialEq)]
pub struct Primed {
    pub name: &'static str,
    /// None = 그 자리에 파일이 없어 건너뜀.
    pub took: Option<Duration>,
    pub ok: bool,
}

/// `dir` 안 실행 파일 경로(윈 = `.exe`).
pub fn prime_path(dir: &Path, name: &str) -> PathBuf {
    dir.join(if cfg!(windows) { format!("{name}.exe") } else { name.to_string() })
}

/// 순수 뼈대 — `run(경로)` = 성공 여부(시간은 여기서 잰다). 없는 파일은 건너뛴다.
pub fn prime_binaries_with(dir: &Path, mut run: impl FnMut(&Path) -> bool) -> Vec<Primed> {
    PRIME_NAMES
        .iter()
        .map(|&name| {
            let p = prime_path(dir, name);
            if !p.is_file() {
                return Primed { name, took: None, ok: false };
            }
            let t = Instant::now();
            let ok = run(&p);
            Primed { name, took: Some(t.elapsed()), ok }
        })
        .collect()
}

/// 실행판 — `<경로> --version` 1회(숨김 헬퍼 · 출력 버림 · [`PRIME_CAP`] 상한).
pub fn prime_binaries(dir: &Path) -> Vec<Primed> {
    prime_binaries_with(dir, |p| run_version_capped(p, PRIME_CAP))
}

fn run_version_capped(p: &Path, cap: Duration) -> bool {
    let mut cmd = crate::hidden_command(p);
    cmd.arg("--version")
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null());
    let Ok(mut child) = cmd.spawn() else { return false };
    let t = Instant::now();
    loop {
        match child.try_wait() {
            Ok(Some(st)) => return st.success(),
            Ok(None) if t.elapsed() < cap => std::thread::sleep(Duration::from_millis(20)),
            // 상한 넘김·판독 오류 = 내가 띄운 그 자식만 끝낸다(이름 일치 종료 아님).
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                return false;
            }
        }
    }
}

/// 로그 1줄(순수) — 예: `미리 데우기: cys 1.32s · cysd 0.21s · cysr 실패 0.05s`.
pub fn prime_log_line(v: &[Primed]) -> String {
    let parts: Vec<String> = v
        .iter()
        .map(|p| match p.took {
            None => format!("{} 없음", p.name),
            Some(d) => format!("{}{} {:.2}s", p.name, if p.ok { "" } else { " 실패" }, d.as_secs_f64()),
        })
        .collect();
    format!("미리 데우기: {}", parts.join(" · "))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scratch(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("d3-prime-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    /// 대역 바이너리(호출 기록 스크립트) — 교체 직후 1회씩 · 인자 `--version` · 실패·없음이어도 다음으로 · 로그 1줄.
    #[cfg(unix)]
    #[test]
    fn d3_prime_runs_each_new_binary_once_with_version() {
        use std::os::unix::fs::PermissionsExt;
        let d = scratch("stub");
        let log = d.join("calls.log");
        for (name, rc) in [("cys", 0), ("cysd", 3)] {
            let p = d.join(name);
            std::fs::write(&p, format!("#!/bin/sh\necho \"{name} $*\" >> '{}'\nexit {rc}\n", log.display())).unwrap();
            std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o755)).unwrap();
        }
        let v = prime_binaries(&d);
        assert_eq!(std::fs::read_to_string(&log).unwrap(), "cys --version\ncysd --version\n", "각 1회 · --version");
        assert_eq!(v.iter().map(|p| (p.name, p.ok, p.took.is_some())).collect::<Vec<_>>(), vec![("cys", true, true), ("cysd", false, true), ("cysr", false, false)]);
        let line = prime_log_line(&v);
        assert!(line.starts_with("미리 데우기: cys ") && line.contains("cysd 실패 ") && line.ends_with("cysr 없음"), "{line}");
        assert_eq!(line.lines().count(), 1);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 멈추는 바이너리 = 상한에서 그 자식만 끝내고 실패로 접는다(설치를 멈추지 않는다).
    #[cfg(unix)]
    #[test]
    fn d3_prime_caps_a_hanging_binary() {
        use std::os::unix::fs::PermissionsExt;
        let d = scratch("hang");
        let p = d.join("cys");
        std::fs::write(&p, "#!/bin/sh\nexec sleep 30\n").unwrap();
        std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o755)).unwrap();
        let t = Instant::now();
        assert!(!run_version_capped(&p, Duration::from_millis(300)));
        assert!(t.elapsed() < Duration::from_secs(5), "상한에서 끊는다");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 배선 핀: 업데이터 = 교체(S9·S9b) 뒤 · 새 데몬 기동(rotate) **앞** 1회 · CLI `cys daemon prime` = 데몬 연결 0 · 늘 0.
    #[test]
    fn d3_prime_is_wired_right_after_the_swap_and_as_a_daemon_subverb() {
        let ro = include_str!("realops.rs");
        let body = &ro[ro.find("    fn start_new(&mut self, _j: &Journal) -> Step {").expect("start_new")..];
        let body = &body[..body.find("\n    }\n").unwrap()];
        let prime = body.find("super::prime::prime_binaries(dir)").expect("교체 직후 미리 데우기");
        assert!(prime < body.find("self.rotate(&self.new_cys(), false)").unwrap(), "새 데몬 기동 전");
        assert_eq!(body.matches("prime_binaries(").count(), 1, "1회");
        assert!(body.contains("if let (Os::Mac, Some(dir)) = (self.env.os, self.new_cys().parent()) {"), "윈 = NSIS POSTINSTALL 이 이미 1회(중복 0)");
        let nsh = include_str!("../../src-tauri/nsis-hooks.nsh");
        let post = &nsh[nsh.find("!macro NSIS_HOOK_POSTINSTALL").unwrap()..];
        let post = &post[..post.find("!macroend").unwrap()];
        let alias = post.find("cys_post_alias_ok:").expect("cysr 별칭 뒤(세 바이너리가 다 놓인 자리)");
        let call = post.find("nsExec::ExecToLog '\"$INSTDIR\\cys.exe\" daemon prime'").expect("NSIS 설치 끝 1회");
        assert!(alias < call && post.matches("daemon prime'").count() == 1);
        let cli = include_str!("../bin/cys.rs");
        let head = &cli[cli.find("fn run_daemon_cmd(action: DaemonAction) -> i32 {").unwrap()..];
        let head = &head[..head.find("let result: Result<(), String> = (|| {").unwrap()];
        let at = head.find("if let DaemonAction::Prime = &action {").expect("하위 동사 머리 처리");
        let arm = &head[at..at + head[at..].find("return 0;").expect("늘 0")];
        assert!(arm.contains("cys::update::prime::prime_binaries(&dir)") && !arm.contains("request("), "데몬 연결 0");
        assert!(cli.contains("action: DaemonAction::Status | DaemonAction::ResumeCheck { .. } | DaemonAction::Prime"), "자동 기동 0");
    }

    #[test]
    fn d3_prime_skips_missing_and_names_exe_on_windows() {
        let d = scratch("none");
        let mut n = 0;
        let v = prime_binaries_with(&d, |_| { n += 1; true });
        assert_eq!(n, 0);
        assert!(v.iter().all(|p| p.took.is_none()));
        assert_eq!(prime_path(Path::new("x"), "cysd").file_name().unwrap().to_str().unwrap(), if cfg!(windows) { "cysd.exe" } else { "cysd" });
        let _ = std::fs::remove_dir_all(&d);
    }
}
