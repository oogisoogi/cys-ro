//! 윈 실 프로세스 시험(TICKET=cysr-1111-winchrome · CI windows-health): 데몬처럼 자기 자신을 KILL_ON_JOB_CLOSE Job 에 넣은
//! 부모를 `taskkill /F` 로 죽여, 이탈 스폰 자식만 살아남는지 본다. 좌석 재시작 R5 A 와 같은 모양이다.
#![cfg(windows)]

use cys::job_exit::{job_limits, set_breakaway, spawn_breaking_away};
use cys::SpawnPolicy;
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};
use windows_sys::Win32::Foundation::{CloseHandle, STILL_ACTIVE};
use windows_sys::Win32::System::JobObjects::{
    AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation, SetInformationJobObject,
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JOB_OBJECT_LIMIT_BREAKAWAY_OK, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
};
use windows_sys::Win32::System::Threading::{
    GetCurrentProcess, GetExitCodeProcess, OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION,
};

const ENV_MODE: &str = "CYS_JOBEXIT_TEST_MODE";
const ENV_OUT: &str = "CYS_JOBEXIT_TEST_OUT";
const BASH: &str = r"C:\Program Files\Git\bin\bash.exe";

fn sleeper() -> Command {
    let mut c = Command::new("ping");
    c.args(["-n", "300", "127.0.0.1"]).stdout(Stdio::null()).stderr(Stdio::null());
    c
}

fn alive(pid: u32) -> bool {
    unsafe {
        let h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid);
        if h.is_null() {
            return false;
        }
        let mut code = 0u32;
        let ok = GetExitCodeProcess(h, &mut code) != 0;
        CloseHandle(h);
        ok && code == STILL_ACTIVE as u32
    }
}

fn wait_dead(pid: u32, within: Duration) -> bool {
    let t = Instant::now();
    while t.elapsed() < within {
        if !alive(pid) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    !alive(pid)
}

fn kill(pid: u32) {
    let _ = Command::new("taskkill").args(["/PID", &pid.to_string(), "/F"]).output();
}

fn new_job(limits: u32) -> usize {
    unsafe {
        let h = CreateJobObjectW(std::ptr::null(), std::ptr::null());
        assert!(!h.is_null());
        let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
        info.BasicLimitInformation.LimitFlags = limits;
        assert_ne!(
            SetInformationJobObject(
                h,
                JobObjectExtendedLimitInformation,
                (&info as *const JOBOBJECT_EXTENDED_LIMIT_INFORMATION).cast(),
                std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            ),
            0
        );
        h as usize
    }
}

fn enter(job: usize) {
    unsafe { assert_ne!(AssignProcessToJobObject(job as _, GetCurrentProcess()), 0) };
}

fn publish(out: &Path, body: String) {
    let tmp = out.with_extension("tmp");
    std::fs::write(&tmp, body).unwrap();
    std::fs::rename(&tmp, out).unwrap();
}

/// 부모 역할(자기 자신을 다시 띄운 프로세스에서만 돈다).
#[test]
fn parent_helper() {
    let Ok(mode) = std::env::var(ENV_MODE) else { return };
    let out = PathBuf::from(std::env::var(ENV_OUT).unwrap());
    if mode == "nested" {
        enter(new_job(0));                  // 바깥 Job = 이탈 불허(러너·설치기 꼴)
    }
    if mode.starts_with("msys") {
        // 부모 Job 이 이탈을 허용하면 msys 가 자식에 이탈 flag 를 스스로 붙이는지 재는 모드 — 상시 허용을 버린 근거.
        enter(new_job(job_limits(mode == "msys-open")));
        let body = format!(
            "ping -n 300 127.0.0.1 >/dev/null 2>&1 & sleep 1; cat /proc/$!/winpid > '{}'; wait",
            out.to_string_lossy().replace('\\', "/")
        );
        Command::new(BASH).args(["-c", &body]).spawn().unwrap();
        std::thread::sleep(Duration::from_secs(300));
        return;
    }
    let job = new_job(job_limits(false));
    enter(job);
    let bound = sleeper().spawn().unwrap();
    let mut outside = sleeper();
    outside.spawn_policy(cys::ChildLifetime::Survivor);
    let escaped = spawn_breaking_away(job, &mut outside).unwrap();
    // 허용 구간이 끝났으면 같은 flag 의 스폰은 다시 거부돼야 한다.
    let mut late = sleeper();
    late.spawn_policy(cys::ChildLifetime::Survivor);
    let denied = match late.spawn() {
        Err(e) => e.raw_os_error() == Some(5),
        Ok(c) => {
            kill(c.id());
            false
        }
    };
    publish(&out, format!("{} {} {}", bound.id(), escaped.id(), denied));
    std::thread::sleep(Duration::from_secs(300));
}

/// 단언·시한 실패에도 부모·자식을 남기지 않는다.
struct Reap(Vec<u32>);
impl Drop for Reap {
    fn drop(&mut self) {
        for p in &self.0 {
            kill(*p);
        }
    }
}

fn start_parent(mode: &str, out: &Path) -> std::process::Child {
    Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "parent_helper", "--nocapture", "--test-threads=1"])
        .env(ENV_MODE, mode)
        .env(ENV_OUT, out)
        .creation_flags(0x0800_0000)
        .spawn()
        .unwrap()
}

fn read_out(out: &Path) -> String {
    let t = Instant::now();
    while t.elapsed() < Duration::from_secs(30) {
        if let Ok(s) = std::fs::read_to_string(out) {
            if !s.trim().is_empty() {
                return s;
            }
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    panic!("부모가 결과를 쓰지 않았다: {out:?}");
}

fn scratch(name: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!("cys-jobexit-{}-{name}", std::process::id()));
    std::fs::create_dir_all(&d).unwrap();
    d.join("out.txt")
}

fn run_case(mode: &str) {
    let out = scratch(mode);
    let mut parent = start_parent(mode, &out);
    let mut reap = Reap(vec![parent.id()]);
    let s = read_out(&out);
    let v: Vec<&str> = s.split_whitespace().collect();
    let (bound, escaped): (u32, u32) = (v[0].parse().unwrap(), v[1].parse().unwrap());
    reap.0.extend([bound, escaped]);
    assert!(alive(bound) && alive(escaped), "부모를 죽이기 전에는 둘 다 살아 있어야 한다");
    kill(parent.id());
    let _ = parent.wait();
    let bound_died = wait_dead(bound, Duration::from_secs(10));
    let escaped_alive = alive(escaped);
    assert!(bound_died, "[{mode}] 대조군: 이탈하지 않은 자식은 Job 과 함께 죽어야 한다(결박 유지)");
    assert!(escaped_alive, "[{mode}] 이탈 스폰 자식은 부모가 죽어도 살아야 한다(R5 A)");
    assert_eq!(v[2], "true", "[{mode}] 허용 구간 밖의 이탈은 다시 거부돼야 한다");
}

#[test]
fn escaped_child_survives_and_bound_child_dies() {
    run_case("plain");
}

/// 바깥 Job 이 이탈을 불허해도 안쪽(데몬) Job 은 빠져나간다 — MS 「Nested Jobs」: 직속 Job 이 허용하면 불허 Job 을 만날 때까지 올라간다.
#[test]
fn escape_works_under_outer_job_that_refuses_breakaway() {
    run_case("nested");
}

/// 평소 Job 안의 Git Bash 자식은 Job 에 묶여 있어야 한다.
#[test]
fn msys_child_stays_bound_when_breakaway_is_closed() {
    if !Path::new(BASH).exists() {
        eprintln!("[skip] Git Bash 없음");
        return;
    }
    let out = scratch("msys-closed");
    let mut parent = start_parent("msys-closed", &out);
    let mut reap = Reap(vec![parent.id()]);
    let pid: u32 = read_out(&out).trim().parse().unwrap();
    reap.0.push(pid);
    kill(parent.id());
    let _ = parent.wait();
    let died = wait_dead(pid, Duration::from_secs(10));
    assert!(died, "이탈 비트가 꺼져 있으면 msys 자식도 Job 과 함께 죽어야 한다");
}

/// 설계 근거 측정(단언 없음 · CI 로그의 `[measure]` 줄): 비트를 상시로 켜면 msys 자식이 Job 을 빠져나가는가.
#[test]
fn measure_msys_child_with_breakaway_always_open() {
    if !Path::new(BASH).exists() {
        eprintln!("[skip] Git Bash 없음");
        return;
    }
    let out = scratch("msys-open");
    let mut parent = start_parent("msys-open", &out);
    let mut reap = Reap(vec![parent.id()]);
    let pid: u32 = read_out(&out).trim().parse().unwrap();
    reap.0.push(pid);
    kill(parent.id());
    let _ = parent.wait();
    let died = wait_dead(pid, Duration::from_secs(10));
    eprintln!("[measure] BREAKAWAY_OK 상시 + Git Bash 자식: {}", if died { "함께 죽음" } else { "Job 이탈(생존)" });
}

#[test]
fn limit_constants_match_windows_sdk() {
    assert_eq!(job_limits(false), JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE);
    assert_eq!(job_limits(true), JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_BREAKAWAY_OK);
    let job = new_job(job_limits(false));
    set_breakaway(job, true).unwrap();
    set_breakaway(job, false).unwrap();
}
