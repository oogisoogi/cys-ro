//! r8-1 순서 시험(TICKET=cysr-1111-r8-merge) — 실 `cys` · 실 `cysd` · 격리 HOME · 격리 소켓. rotate 가 띄운 기동만 자동 복원을 쉬고 일반 기동은 그대로 복원한다.
//! 격리 소켓은 launchd 갈래가 아니라 정지 + 자동 기동 갈래(윈도우 rotate 와 같은 길)를 탄다. 윈도우 실기는 r9 가 잰다.
#![cfg(unix)]

use serde_json::{json, Value};
use std::io::{Read, Write};
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::time::{Duration, Instant};

const CYS: &str = env!("CARGO_BIN_EXE_cys");

struct Box_ {
    base: PathBuf,
    sock: PathBuf,
}

impl Box_ {
    fn new() -> Self {
        let base = PathBuf::from(format!("/tmp/cys-rah-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        std::fs::create_dir_all(base.join("home")).unwrap();
        std::fs::create_dir_all(base.join("run")).unwrap();
        let sock = base.join("run/cysd.sock");
        Self { base, sock }
    }

    fn cys(&self, args: &[&str]) -> Output {
        Command::new(CYS)
            .args(args)
            .env_clear()
            .env("PATH", std::env::var("PATH").unwrap_or_default())
            .env("HOME", self.base.join("home"))
            .env("TMPDIR", &self.base)
            .env("CYS_SOCKET", &self.sock)
            .output()
            .unwrap()
    }

    fn rpc(&self, method: &str) -> Result<Value, String> {
        let mut s = UnixStream::connect(&self.sock).map_err(|e| e.to_string())?;
        s.set_read_timeout(Some(Duration::from_secs(10))).map_err(|e| e.to_string())?;
        let mut line = serde_json::to_vec(&json!({"id": 1, "method": method, "params": {}})).unwrap();
        line.push(b'\n');
        s.write_all(&line).map_err(|e| e.to_string())?;
        let mut got = Vec::new();
        let mut buf = [0u8; 65536];
        while !got.ends_with(b"\n") {
            match s.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => got.extend_from_slice(&buf[..n]),
                Err(e) => return Err(e.to_string()),
            }
        }
        let v: Value = serde_json::from_slice(&got).map_err(|e| e.to_string())?;
        Ok(v["result"].clone())
    }

    fn pid(&self) -> u64 {
        self.rpc("system.identify").unwrap()["daemon_pid"].as_u64().unwrap()
    }

    /// `off` = 이 기동이 자동 복원을 쉬었다 · `running`·`done` = 돌렸다.
    fn phase(&self) -> String {
        self.rpc("org.status").unwrap()["daemon"]["auto_restore"].as_str().unwrap_or("").to_string()
    }

    fn up(&self) -> u64 {
        // 디버그 빌드의 첫 부트는 팩 설치 때문에 자동 기동의 4초 상한을 넘긴다 — 데몬은 이미 떠 있으니 소켓을 기다린다.
        let o = self.cys(&["identify"]);
        let t = Instant::now();
        while self.rpc("system.identify").is_err() {
            assert!(t.elapsed() < Duration::from_secs(60), "identify: {}", String::from_utf8_lossy(&o.stderr));
            std::thread::sleep(Duration::from_millis(200));
        }
        self.pid()
    }

    fn down(&self) {
        let Ok(r) = self.rpc("system.identify") else { return };
        let pid = r["daemon_pid"].as_u64().unwrap();
        unsafe { libc::kill(pid as i32, libc::SIGTERM) };
        let t = Instant::now();
        while UnixStream::connect(&self.sock).is_ok() && t.elapsed() < Duration::from_secs(10) {
            std::thread::sleep(Duration::from_millis(100));
        }
    }

    fn hold(&self) -> PathBuf {
        cys::daemon_state_dir(&self.sock).join("autorestore-hold")
    }
}

impl Drop for Box_ {
    fn drop(&mut self) {
        self.down();
        // 소켓이 닫힌 뒤에도 데몬이 잠깐 상태 폴더에 쓴다.
        for _ in 0..30 {
            let _ = std::fs::remove_dir_all(&self.base);
            std::thread::sleep(Duration::from_millis(100));
            if !self.base.exists() {
                break;
            }
        }
    }
}

fn normal_boot_restores(b: &Box_) {
    let p = b.phase();
    assert!(p == "running" || p == "done", "일반 기동은 자동 복원을 돌린다: {p}");
}

#[test]
fn only_the_rotate_boot_skips_auto_restore() {
    let b = Box_::new();
    let first = b.up();
    normal_boot_restores(&b);

    let o = b.cys(&["rotate", "--skip-drain", "--skip-depts"]);
    let rc = o.status.code();
    assert!(matches!(rc, Some(0) | Some(25)), "rotate rc={rc:?}\n{}", String::from_utf8_lossy(&o.stderr));
    assert_ne!(b.pid(), first, "데몬이 바뀌었다");
    assert_eq!(b.phase(), "off", "rotate 가 띄운 기동은 자동 복원을 쉰다");
    assert!(!b.hold().exists(), "표식은 ⑤ 앞에서 풀린다");

    // 다음 일반 기동은 플래그가 남지 않았다.
    b.down();
    b.up();
    normal_boot_restores(&b);
}

#[test]
fn a_hold_left_by_a_dead_rotate_does_not_stop_the_next_boot() {
    let b = Box_::new();
    b.up();
    b.down();
    let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs();
    write_hold(&b.hold(), now, 4_000_000);
    b.up();
    normal_boot_restores(&b);
    assert!(!b.hold().exists(), "잔재를 지운다");
}

fn write_hold(p: &Path, ts: u64, pid: u32) {
    std::fs::create_dir_all(p.parent().unwrap()).unwrap();
    std::fs::write(p, format!("{ts} {pid}")).unwrap();
}
