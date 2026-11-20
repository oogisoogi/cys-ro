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
    /// None = 실행하지 않음(파일 없음 또는 `skipped`).
    pub took: Option<Duration>,
    pub ok: bool,
    /// 실행하지 않은 사유(별칭 게이트) — None 이고 took 도 None 이면 파일 없음.
    pub skipped: Option<&'static str>,
}

/// 별칭(cysr) 게이트 사유.
pub const SKIP_ALIAS_NOT_PLACED: &str = "별칭 배치가 확인되지 않음";
pub const SKIP_ALIAS_NOT_SAME: &str = "별칭이 cys 와 같은 바이트가 아님";

/// `dir` 안 실행 파일 경로(윈 = `.exe`).
pub fn prime_path(dir: &Path, name: &str) -> PathBuf {
    dir.join(if cfg!(windows) { format!("{name}.exe") } else { name.to_string() })
}

/// 순수 뼈대 — `run(경로)` = 성공 여부(시간은 여기서 잰다). 없는 파일은 건너뛴다.
/// ★codex 3R blocking([master#fc79d3e6]): cysr 는 **별칭 배치 성공(`alias_placed`) ∧ `verify(cys, cysr)` 가 같은 바이트를 증명**할 때만 실행한다 —
/// 별칭 갱신이 실패한 자리의 낡은·심어 둔 cysr 를 관리자 토큰(Highest 갱신)으로 실행하던 길 차단. `verify` 가 돌려준 값(윈 = 쓰기·삭제 금지 손잡이)은
/// 실행이 끝날 때까지 쥔다(대조 ~ 실행 사이 바꿔치기 창을 닫는다).
pub fn prime_binaries_with<G>(
    dir: &Path,
    alias_placed: bool,
    mut verify: impl FnMut(&Path, &Path) -> Option<G>,
    mut run: impl FnMut(&Path) -> bool,
) -> Vec<Primed> {
    PRIME_NAMES
        .iter()
        .map(|&name| {
            let p = prime_path(dir, name);
            if !p.is_file() {
                return Primed { name, took: None, ok: false, skipped: None };
            }
            let guard = if name == "cysr" {
                if !alias_placed {
                    return Primed { name, took: None, ok: false, skipped: Some(SKIP_ALIAS_NOT_PLACED) };
                }
                match verify(&prime_path(dir, "cys"), &p) {
                    Some(g) => Some(g),
                    None => return Primed { name, took: None, ok: false, skipped: Some(SKIP_ALIAS_NOT_SAME) },
                }
            } else {
                None
            };
            let t = Instant::now();
            let ok = run(&p);
            drop(guard);
            Primed { name, took: Some(t.elapsed()), ok, skipped: None }
        })
        .collect()
}

/// 실행판 — `<경로> --version` 1회(숨김 헬퍼 · 출력 버림 · [`PRIME_CAP`] 상한) · cysr = 게이트([`prime_binaries_with`]).
pub fn prime_binaries(dir: &Path, alias_placed: bool) -> Vec<Primed> {
    prime_binaries_with(dir, alias_placed, same_bytes_held, |p| run_version_capped(p, PRIME_CAP))
}

/// 두 파일이 같은 바이트인가 — 같으면 별칭 쪽 손잡이를 돌려준다(윈 = 공유 모드 읽기만 · 쓰기·삭제·이름 바꾸기 금지 → 실행 끝까지 바꿔치기 0).
fn same_bytes_held(cys: &Path, alias: &Path) -> Option<std::fs::File> {
    use std::io::Read;
    let open = |p: &Path| -> Option<std::fs::File> {
        let mut o = std::fs::OpenOptions::new();
        o.read(true);
        #[cfg(windows)]
        {
            use std::os::windows::fs::OpenOptionsExt;
            o.share_mode(1); // FILE_SHARE_READ 만
        }
        o.open(p).ok()
    };
    let (mut a, mut b) = (open(cys)?, open(alias)?);
    if a.metadata().ok()?.len() != b.metadata().ok()?.len() {
        return None;
    }
    let (mut x, mut y) = (vec![0u8; 1 << 16], vec![0u8; 1 << 16]);
    loop {
        let n = a.read(&mut x).ok()?;
        let mut m = 0;
        while m < n {
            let k = b.read(&mut y[m..n]).ok()?;
            if k == 0 {
                return None;
            }
            m += k;
        }
        if n == 0 {
            // 끝 — 별칭 쪽도 끝이어야 한다.
            return (b.read(&mut y[..1]).ok()? == 0).then_some(b);
        }
        if x[..n] != y[..n] {
            return None;
        }
    }
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
        .map(|p| match (p.took, p.skipped) {
            (None, Some(why)) => format!("{} 건너뜀({why})", p.name),
            (None, None) => format!("{} 없음", p.name),
            (Some(d), _) => format!("{}{} {:.2}s", p.name, if p.ok { "" } else { " 실패" }, d.as_secs_f64()),
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
        let v = prime_binaries(&d, true);
        assert_eq!(std::fs::read_to_string(&log).unwrap(), "cys --version\ncysd --version\n", "각 1회 · --version");
        assert_eq!(v.iter().map(|p| (p.name, p.ok, p.took.is_some())).collect::<Vec<_>>(), vec![("cys", true, true), ("cysd", false, true), ("cysr", false, false)]);
        let line = prime_log_line(&v);
        assert!(line.starts_with("미리 데우기: cys ") && line.contains("cysd 실패 ") && line.ends_with("cysr 없음"), "{line}");
        assert_eq!(line.lines().count(), 1);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★codex 3R blocking([master#fc79d3e6]) 별칭 게이트 — 실패 주입: ① 별칭 배치 실패(`--skip-alias`) = 진짜 사본이어도 cysr 실행 0
    /// ② 배치 성공이라 해도 cysr 가 cys 와 다른 바이트(낡은·심어 둔 것) = 실행 0 ③ 같은 바이트 사본 = 실행 1 ④ 맥 꼴(cys 를 가리키는 심링크) = 실행 1.
    #[cfg(unix)]
    #[test]
    fn d3_prime_runs_the_cysr_alias_only_when_placed_and_byte_same() {
        use std::os::unix::fs::PermissionsExt;
        let d = scratch("alias");
        let log = d.join("calls.log");
        let stub = format!("#!/bin/sh\necho \"$(basename \"$0\") $*\" >> '{}'\nexit 0\n", log.display());
        let put = |name: &str, body: &str| {
            let p = d.join(name);
            let _ = std::fs::remove_file(&p);
            std::fs::write(&p, body).unwrap();
            std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o755)).unwrap();
        };
        put("cys", &stub);
        put("cysd", &stub);
        let calls = || std::fs::read_to_string(&log).unwrap_or_default();
        let cysr_runs = || calls().lines().filter(|l| l.starts_with("cysr ")).count();
        // ① 배치 실패 주입 — 같은 바이트 사본이 있어도 실행 0.
        put("cysr", &stub);
        let v = prime_binaries(&d, false);
        assert_eq!(cysr_runs(), 0, "별칭 배치 실패 = cysr 실행 0: {}", calls());
        assert_eq!(v[2].skipped, Some(SKIP_ALIAS_NOT_PLACED));
        assert!(prime_log_line(&v).ends_with("cysr 건너뜀(별칭 배치가 확인되지 않음)"));
        // ② 심어 둔 별칭(다른 바이트) — 배치 성공 신호여도 실행 0 · cys·cysd 는 그대로 돈다.
        let _ = std::fs::remove_file(&log);
        put("cysr", &format!("{stub}# planted\n"));
        let v = prime_binaries(&d, true);
        assert_eq!(cysr_runs(), 0, "다른 바이트 = 실행 0: {}", calls());
        assert_eq!(v[2].skipped, Some(SKIP_ALIAS_NOT_SAME));
        assert_eq!(calls(), "cys --version\ncysd --version\n");
        // 같은 길이 · 다른 바이트도 막는다.
        put("cysr", &stub.replace("exit 0", "exit 1"));
        prime_binaries(&d, true);
        assert_eq!(cysr_runs(), 0);
        // ③ 같은 바이트 사본 = 1회.
        let _ = std::fs::remove_file(&log);
        put("cysr", &stub);
        let v = prime_binaries(&d, true);
        assert_eq!((cysr_runs(), v[2].skipped, v[2].ok), (1, None, true), "{}", calls());
        // ④ 맥 꼴 = cys 를 가리키는 심링크 → 같은 바이트 = 1회 · 다른 파일을 가리키는 심링크 = 0.
        let _ = std::fs::remove_file(&log);
        let _ = std::fs::remove_file(d.join("cysr"));
        std::os::unix::fs::symlink("cys", d.join("cysr")).unwrap();
        prime_binaries(&d, true);
        assert_eq!(calls().lines().count(), 3, "심링크 별칭 = cys 로 실행: {}", calls());
        let _ = std::fs::remove_file(&log);
        let _ = std::fs::remove_file(d.join("cysr"));
        put("other", &format!("{stub}# other\n"));
        std::os::unix::fs::symlink("other", d.join("cysr")).unwrap();
        prime_binaries(&d, true);
        assert_eq!(calls(), "cys --version\ncysd --version\n", "다른 곳을 가리키는 별칭 = 실행 0");
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
        let prime = body.find("super::prime::prime_binaries(dir, true)").expect("교체 직후 미리 데우기");
        assert!(prime < body.find("self.rotate(&self.new_cys(), false)").unwrap(), "새 데몬 기동 전");
        assert_eq!(body.matches("prime_binaries(").count(), 1, "1회");
        assert!(body.contains("if let (Os::Mac, Some(dir)) = (self.env.os, self.new_cys().parent()) {"), "윈 = NSIS POSTINSTALL 이 이미 1회(중복 0)");
        let nsh = include_str!("../../src-tauri/nsis-hooks.nsh");
        let post = &nsh[nsh.find("!macro NSIS_HOOK_POSTINSTALL").unwrap()..];
        let post = &post[..post.find("!macroend").unwrap()];
        // ★codex 3R blocking: 별칭 복사 실패 갈래(IfErrors → 경고) = `--skip-alias` 1회 후 Goto 로 평소 호출을 건너뛴다 · 성공 갈래(cys_post_alias_ok) = 평소 1회.
        let copy = post.find("CopyFiles /SILENT \"$INSTDIR\\cys.exe\" \"$INSTDIR\\cysr.exe\"").expect("별칭 복사");
        let iferr = copy + post[copy..].find("IfErrors 0 cys_post_alias_ok").expect("복사 성패 분기");
        let ok_lbl = post.find("\ncys_post_alias_ok:").expect("성공 갈래");
        let done_lbl = post.find("\ncys_post_prime_done:").expect("합류");
        let fail_arm = &post[iferr..ok_lbl];
        let ok_arm = &post[ok_lbl..done_lbl];
        let skip = fail_arm.find("nsExec::ExecToLog '\"$INSTDIR\\cys.exe\" daemon prime --skip-alias'").expect("실패 갈래 = cysr 뺌");
        assert!(skip < fail_arm.find("Goto cys_post_prime_done").expect("평소 호출로 흘러가지 않음"));
        assert!(!fail_arm.contains("daemon prime'"), "실패 갈래에 평소 호출 없음");
        assert!(ok_arm.contains("nsExec::ExecToLog '\"$INSTDIR\\cys.exe\" daemon prime'") && !ok_arm.contains("--skip-alias"));
        assert_eq!((post.matches("daemon prime'").count(), post.matches("daemon prime --skip-alias'").count()), (1, 1));
        let cli = include_str!("../bin/cys.rs");
        let head = &cli[cli.find("fn run_daemon_cmd(action: DaemonAction) -> i32 {").unwrap()..];
        let head = &head[..head.find("let result: Result<(), String> = (|| {").unwrap()];
        let at = head.find("if let DaemonAction::Prime { skip_alias } = &action {").expect("하위 동사 머리 처리");
        let arm = &head[at..at + head[at..].find("return 0;").expect("늘 0")];
        assert!(arm.contains("cys::update::prime::prime_binaries(&dir, !*skip_alias)") && !arm.contains("request("), "데몬 연결 0 · --skip-alias = 별칭 배치 미확인");
        // (integ-1120) 자동 기동 금지 목록 = borrow23 이 여러 줄 꼴(ExplainState·BootFleet 추가)로 바꿔 한 줄 문면 핀이 깨졌다 — 문면 대신 그 함수의 Daemon 갈래 안에 Prime 이 있는지 본다.
        let nev = &cli[cli.find("fn command_never_autostarts(command: &Command) -> bool {").expect("자동 기동 금지 판정")..];
        let nev = &nev[..nev.find("\n}\n").unwrap()];
        let dmn = &nev[nev.find("| Command::Daemon {").expect("Daemon 갈래")..];
        let dmn = &dmn[..dmn.find("\n            }").unwrap()];
        assert!(dmn.contains("| DaemonAction::Prime { .. }") && dmn.contains("action: DaemonAction::Status"), "자동 기동 0");
    }

    #[test]
    fn d3_prime_skips_missing_and_names_exe_on_windows() {
        let d = scratch("none");
        let mut n = 0;
        let v = prime_binaries_with(&d, true, |_, _| Some(()), |_| { n += 1; true });
        assert_eq!(n, 0);
        assert!(v.iter().all(|p| p.took.is_none()));
        assert_eq!(prime_path(Path::new("x"), "cysd").file_name().unwrap().to_str().unwrap(), if cfg!(windows) { "cysd.exe" } else { "cysd" });
        let _ = std::fs::remove_dir_all(&d);
    }
}
