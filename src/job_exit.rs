//! 데몬 Job 밖 스폰(TICKET=cysr-1111-winchrome · 설계 = DESIGN-winchrome.md).
//!
//! 데몬은 자기 자신을 KILL_ON_JOB_CLOSE Job 에 넣는다(`cysd/state.rs::winjob`). 그래서 좌석에서 띄운 크롬·재시작 대기는
//! 데몬이 죽을 때 함께 죽는다 — 좌석 재시작이 자기 자신과 사용자의 크롬을 죽이던 원인이다.
//! ★`JOB_OBJECT_LIMIT_BREAKAWAY_OK` 를 **상시로 켜지 않는다**: 동봉 Git Bash(msys-2.0.dll)는 자기 Job 이 이탈을 허용하면
//! 모든 자식에 `CREATE_BREAKAWAY_FROM_JOB` 을 스스로 붙인다(msys2-runtime `winsup/cygwin/spawn.cc`). 상시로 켜면 좌석 셸의
//! 자식 전부가 Job 을 빠져나가 09-10 고아 python3.exe 사고가 되살아난다. 그래서 **데몬이 허용 목록의 스폰 한 번을 하는 동안만**
//! 비트를 켜고 바로 끈다.

/// `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` — 맥에서도 시험하려고 값을 직접 적는다(윈 시험이 windows-sys 상수와 대조한다).
pub const LIMIT_KILL_ON_JOB_CLOSE: u32 = 0x0000_2000;
/// `JOB_OBJECT_LIMIT_BREAKAWAY_OK`.
pub const LIMIT_BREAKAWAY_OK: u32 = 0x0000_0800;

/// 데몬 Job 의 한도 비트. 평소 = 이탈 불가 · 스폰 한 번 동안만 이탈 허용.
/// `JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK` 는 어떤 경우에도 쓰지 않는다(모든 자손이 말없이 빠져나간다).
pub const fn job_limits(allow_breakaway: bool) -> u32 {
    if allow_breakaway {
        LIMIT_KILL_ON_JOB_CLOSE | LIMIT_BREAKAWAY_OK
    } else {
        LIMIT_KILL_ON_JOB_CLOSE
    }
}

/// 자식에게 넘겨도 되는 환경변수. 좌석 신원·토큰은 넣지 않는다 — 재시작 대기는 앱 ↻ 처럼 좌석 밖에서 돈다.
pub const ENV_ALLOW: [&str; 6] =
    ["CYS_BIN", "CYS_PACK_DIR", "CYS_SOCKET", "CLAUDE_CONFIG_DIR", "CYS_ACCOUNT_DIR", "CYS_CC_STATE"];

fn file_name_lower(p: &str) -> String {
    p.rsplit(['/', '\\']).next().unwrap_or("").to_lowercase()
}

/// 이탈 스폰 요청 검사(순수). 이탈은 **이름 붙은 두 스폰만** — 임의 명령을 Job 밖으로 내보내는 통로가 되지 않게 한다.
pub fn validate(kind: &str, argv: &[String], env: &[(String, String)]) -> Result<(), String> {
    match kind {
        "chrome" => {
            if argv.len() != 2 || file_name_lower(&argv[0]) != "chrome.exe" || argv[1] != "--restore-last-session" {
                return Err("chrome: 인자는 <chrome.exe> --restore-last-session 뿐이다".into());
            }
        }
        "seat_restart" => {
            if argv.len() < 3
                || !file_name_lower(&argv[0]).starts_with("python")
                || argv[1].starts_with('-')
                || file_name_lower(&argv[1]) != "javis_computer_control.py"
                || argv[2] != "seat-restart-wait"
            {
                return Err("seat_restart: 인자는 <python> javis_computer_control.py seat-restart-wait … 뿐이다".into());
            }
        }
        _ => return Err(format!("허용되지 않은 종류: {kind}")),
    }
    if let Some((k, _)) = env.iter().find(|(k, _)| !ENV_ALLOW.contains(&k.as_str())) {
        return Err(format!("허용되지 않은 환경변수: {k}"));
    }
    Ok(())
}

#[cfg(windows)]
mod win {
    use super::job_limits;
    use std::sync::Mutex;
    use windows_sys::Win32::Foundation::GetLastError;
    use windows_sys::Win32::System::JobObjects::{
        JobObjectExtendedLimitInformation, SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
    };

    /// 허용 구간은 한 번에 하나 — 겹치면 앞 구간이 끝나며 뒤 구간의 비트를 꺼 버린다.
    static WINDOW: Mutex<()> = Mutex::new(());

    /// 한도 비트 설정. `job` = 프로세스 전역 핸들 값(`winjob` 이 usize 로 보관하는 그 값).
    pub fn set_breakaway(job: usize, allow: bool) -> Result<(), u32> {
        unsafe {
            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
            info.BasicLimitInformation.LimitFlags = job_limits(allow);
            if SetInformationJobObject(
                job as _,
                JobObjectExtendedLimitInformation,
                (&info as *const JOBOBJECT_EXTENDED_LIMIT_INFORMATION).cast(),
                std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            ) == 0
            {
                return Err(GetLastError());
            }
        }
        Ok(())
    }

    struct Close(usize);
    impl Drop for Close {
        fn drop(&mut self) {
            if let Err(e) = set_breakaway(self.0, false).or_else(|_| set_breakaway(self.0, false)) {
                eprintln!("[cysd] ⚠ Job 이탈 허용을 끄지 못했다(GetLastError={e}) — 좌석 셸 자식이 Job 을 빠져나갈 수 있다");
            }
        }
    }

    /// `job` 의 이탈을 스폰 한 번 동안만 허용한다(`cmd` 는 `CREATE_BREAKAWAY_FROM_JOB` 을 단 채로 온다).
    pub fn spawn_breaking_away(job: usize, cmd: &mut std::process::Command) -> Result<std::process::Child, String> {
        let _one = WINDOW.lock().unwrap_or_else(|p| p.into_inner());
        set_breakaway(job, true).map_err(|e| format!("Job 이탈 허용 실패(GetLastError={e})"))?;
        let _close = Close(job);
        cmd.spawn().map_err(|e| format!("스폰 실패: {e}"))
    }
}
#[cfg(windows)]
pub use win::{set_breakaway, spawn_breaking_away};

#[cfg(test)]
mod tests {
    use super::*;

    fn s(v: &[&str]) -> Vec<String> {
        v.iter().map(|x| x.to_string()).collect()
    }

    #[test]
    fn limit_bits() {
        assert_eq!(job_limits(false), 0x2000, "평소 = 이탈 불가");
        assert_eq!(job_limits(true), 0x2800);
        assert_eq!(job_limits(true) & 0x1000, 0, "SILENT_BREAKAWAY_OK 금지");
    }

    #[test]
    fn only_named_spawns_pass() {
        let chrome = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", "--restore-last-session"];
        assert!(validate("chrome", &s(&chrome), &[]).is_ok());
        assert!(validate("chrome", &s(&[r"C:\x\cmd.exe", "--restore-last-session"]), &[]).is_err());
        assert!(validate("chrome", &s(&[chrome[0], "--remote-debugging-port=9222"]), &[]).is_err());
        assert!(validate("chrome", &s(&[chrome[0]]), &[]).is_err());
        let wait = ["python", r"C:\p\bin\javis_computer_control.py", "seat-restart-wait", "--min-delay", "30"];
        assert!(validate("seat_restart", &s(&wait), &[]).is_ok());
        assert!(validate("seat_restart", &s(&["python", "evil.py", "seat-restart-wait"]), &[]).is_err());
        assert!(validate("seat_restart", &s(&["cmd.exe", wait[1], "seat-restart-wait"]), &[]).is_err());
        // 파이썬 `-c` 를 파일명처럼 위장하는 꼴(1760 F5)
        assert!(validate("seat_restart", &s(&["python", "-cprint(1)#/javis_computer_control.py", "seat-restart-wait"]), &[]).is_err());
        assert!(validate("seat_restart", &s(&["python", wait[1], "chrome-enable"]), &[]).is_err());
        assert!(validate("shell", &s(&["cmd.exe"]), &[]).is_err());
    }

    /// 상시 허용 회귀 핀: 비트를 켜는 곳은 이 모듈의 허용 구간뿐이고 데몬 Job 생성은 꺼진 값으로 시작한다.
    #[test]
    fn breakaway_bit_stays_inside_this_module() {
        let state = include_str!("bin/cysd/state.rs");
        assert!(state.contains("job_exit::job_limits(false)"));
        assert!(!state.contains("job_limits(true)") && !state.contains("set_breakaway") && !state.contains("LIMIT_BREAKAWAY_OK"));
    }

    #[test]
    fn seat_identity_env_is_refused() {
        let wait = s(&["python", "javis_computer_control.py", "seat-restart-wait"]);
        assert!(validate("seat_restart", &wait, &[("CYS_BIN".into(), "c".into())]).is_ok());
        for k in ["CYS_SEAT_TOKEN", "CYS_SURFACE_ID", "CYS_ROLE", "PATH"] {
            assert!(validate("seat_restart", &wait, &[(k.into(), "x".into())]).is_err(), "{k}");
        }
    }
}
