//! r8-1 순서 시험(TICKET=cysr-1111-rotate-no-autorestore) — 실 `cys` · 실 `cysd` · 실 phoenix · 격리 HOME · 격리 소켓.
//! rotate 가 띄운 기동은 팩 반영이 끝날 때까지 자동 복원을 미루고, 그 뒤 평소의 phoenix 를 돈다. 건너뛰지 않는다(794 F2·F3).
//! 격리 소켓은 launchd 갈래가 아니라 정지 + 자동 기동 갈래(윈도우 rotate 와 같은 길)를 탄다. 윈도우 실기는 r9 가 잰다.
#![cfg(unix)]

use serde_json::{json, Value};
use std::io::{Read, Write};
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Output, Stdio};
use std::time::{Duration, Instant};

const CYS: &str = env!("CARGO_BIN_EXE_cys");
const FAKE_CLAUDE: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/fake_claude.c");

struct Box_ {
    base: PathBuf,
    sock: PathBuf,
    path: String,
}

impl Box_ {
    fn new(tag: &str) -> Self {
        let base = PathBuf::from(format!("/tmp/cys-rah-{}-{tag}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        std::fs::create_dir_all(base.join("home")).unwrap();
        let base = base.canonicalize().unwrap(); // 좌석이 적는 폴더는 실경로다(맥 /tmp → /private/tmp).
        std::fs::create_dir_all(base.join("run")).unwrap();
        let sock = base.join("run/cysd.sock");
        Self { base, sock, path: std::env::var("PATH").unwrap_or_default() }
    }

    fn cmd(&self, args: &[&str]) -> Command {
        let mut c = Command::new(CYS);
        c.args(args)
            .env_clear()
            .env("PATH", &self.path)
            .env("HOME", self.base.join("home"))
            .env("TMPDIR", &self.base)
            .env("CYS_SOCKET", &self.sock);
        c
    }

    fn cys(&self, args: &[&str]) -> Output {
        self.cmd(args).output().unwrap()
    }

    fn rotate(&self) -> Child {
        self.cmd(&["rotate", "--skip-drain", "--skip-depts"]).stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap()
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

    fn pid(&self) -> Option<u64> {
        self.rpc("system.identify").ok()?["daemon_pid"].as_u64()
    }

    fn phase(&self) -> Option<String> {
        self.rpc("org.status").ok()?["daemon"]["auto_restore"].as_str().map(str::to_string)
    }

    fn up(&self) -> u64 {
        // 디버그 빌드의 첫 부트는 팩 설치 때문에 자동 기동의 4초 상한을 넘긴다 — 데몬은 이미 떠 있으니 소켓을 기다린다.
        let o = self.cys(&["identify"]);
        let t = Instant::now();
        loop {
            if let Some(p) = self.pid() {
                return p;
            }
            assert!(t.elapsed() < Duration::from_secs(60), "identify: {}", String::from_utf8_lossy(&o.stderr));
            std::thread::sleep(Duration::from_millis(200));
        }
    }

    fn down(&self) {
        let Some(pid) = self.pid() else { return };
        unsafe { libc::kill(pid as i32, libc::SIGTERM) };
        let t = Instant::now();
        while UnixStream::connect(&self.sock).is_ok() && t.elapsed() < Duration::from_secs(10) {
            std::thread::sleep(Duration::from_millis(100));
        }
    }

    /// 자동 복원이 끝난 단계를 돌려준다.
    fn settled(&self, secs: u64) -> String {
        let t = Instant::now();
        loop {
            let p = self.phase().unwrap_or_default();
            if !matches!(p.as_str(), "" | "held" | "running" | "retry_wait") {
                return p;
            }
            assert!(t.elapsed() < Duration::from_secs(secs), "복원이 끝나지 않았다: {p}");
            std::thread::sleep(Duration::from_millis(200));
        }
    }

    fn hold(&self) -> PathBuf {
        cys::daemon_state_dir(&self.sock).join("autorestore-hold")
    }

    fn pending(&self) -> PathBuf {
        self.base.join("home/.cys/.pending-restore")
    }

    /// 가짜 claude(세션 등록까지 한다 · 앞의 대본이 시작 폴더를 적는다) · 좌석 폴더는 master = proj · worker = 홈(phoenix 만 proj 로 보정한다).
    fn seats(&mut self) -> PathBuf {
        let (bin, real) = (self.base.join("sbin"), self.base.join("real"));
        std::fs::create_dir_all(&bin).unwrap();
        std::fs::create_dir_all(&real).unwrap();
        assert!(Command::new("/usr/bin/cc").args(["-w", "-o"]).arg(real.join("claude")).arg(FAKE_CLAUDE).status().unwrap().success());
        let p = bin.join("claude");
        std::fs::write(&p, format!("#!/bin/sh\necho \"cwd=$PWD\" >> {0}/claude.log\nexec {0}/real/claude \"$@\"\n", self.base.display())).unwrap();
        std::fs::set_permissions(&p, std::os::unix::fs::PermissionsExt::from_mode(0o755)).unwrap();
        self.path = format!("{}:{}:{}", bin.display(), PathBuf::from(CYS).parent().unwrap().display(), self.path);
        self.base.join("proj")
    }

    fn write_topology(&self, proj: &Path) {
        std::fs::create_dir_all(proj).unwrap();
        let e = json!({"entries": [{"role": "master", "agent": "claude", "cwd": proj}, {"role": "worker", "agent": "claude", "cwd": self.base.join("home")}]});
        std::fs::write(self.base.join("run/topology.json"), e.to_string()).unwrap();
    }

    fn claude_log(&self) -> String {
        std::fs::read_to_string(self.base.join("claude.log")).unwrap_or_default()
    }

    /// 산 소유자 — 이름만 맞는 작은 실행 파일.
    fn owner(&self, name: &str) -> Child {
        let src = self.base.join("owner.c");
        std::fs::write(&src, "#include <unistd.h>\nint main(void) { sleep(300); return 0; }\n").unwrap();
        let exe = self.base.join(name);
        assert!(Command::new("/usr/bin/cc").args(["-w", "-o"]).arg(&exe).arg(&src).status().unwrap().success());
        Command::new(&exe).spawn().unwrap()
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

fn rc_ok(o: &Output) {
    assert!(matches!(o.status.code(), Some(0) | Some(25)), "rotate rc={:?}\n{}", o.status.code(), String::from_utf8_lossy(&o.stderr));
}

/// 끝날 때까지 단계를 표본으로 모은다.
fn phases_until_exit(b: &Box_, mut c: Child) -> (Output, Vec<String>) {
    let mut seen = Vec::new();
    while c.try_wait().unwrap().is_none() {
        if let Some(p) = b.phase() {
            if seen.last() != Some(&p) {
                seen.push(p);
            }
        }
        std::thread::sleep(Duration::from_millis(20));
    }
    (c.wait_with_output().unwrap(), seen)
}

#[test]
fn rotate_defers_auto_restore_past_the_pack_step_and_normal_boots_do_not() {
    let b = Box_::new("order");
    let first = b.up();
    assert_ne!(b.phase().as_deref(), Some("held"));
    assert_eq!(b.settled(120), "done", "일반 기동은 자동 복원을 돌린다");

    let (o, seen) = phases_until_exit(&b, b.rotate());
    rc_ok(&o);
    assert_ne!(b.pid(), Some(first), "데몬이 바뀌었다");
    assert!(seen.iter().any(|p| p == "held"), "rotate 기동은 미룬다: {seen:?}");
    assert_eq!(b.settled(120), "done", "건너뛰지 않고 복원했다: {seen:?}");
    assert!(!b.hold().exists(), "표식이 풀렸다");

    // 다음 일반 기동은 미루지 않는다.
    b.down();
    b.up();
    assert_ne!(b.phase().as_deref(), Some("held"));
    assert_eq!(b.settled(120), "done");
}

/// 794 F2 — 같은 topology 에서 rotate 길도 phoenix 가 좌석을 세워 홈 좌석이 master 폴더로 보정되고 원장이 남는다.
#[test]
fn rotate_restores_through_phoenix_so_home_seats_keep_the_project_folder() {
    let mut b = Box_::new("seats");
    let proj = b.seats();
    b.up();
    b.settled(120);
    b.write_topology(&proj);

    let o = b.rotate().wait_with_output().unwrap();
    rc_ok(&o);
    b.settled(180);
    let log = b.claude_log();
    assert!(log.contains(&format!("cwd={}", proj.display())), "좌석이 떴다: {log}");
    assert!(!log.contains(&format!("cwd={}\n", b.base.join("home").display())), "홈에서 뜬 좌석이 없다: {log}");
    assert!(b.base.join("run/phoenix/journal-default.json").is_file(), "phoenix 원장");
}

/// 794 F3 — 새 데몬이 뜬 순간 rotate 가 죽어도 그 데몬이 스스로 복원한다.
#[test]
fn a_rotate_killed_after_the_new_daemon_is_up_does_not_strand_it() {
    let b = Box_::new("kill");
    let first = b.up();
    b.settled(120);
    let mut c = b.rotate();
    let t = Instant::now();
    while b.pid().is_none_or(|p| p == first) {
        assert!(t.elapsed() < Duration::from_secs(30), "새 데몬이 뜨지 않았다");
        std::thread::sleep(Duration::from_millis(20));
    }
    c.kill().unwrap();
    c.wait().unwrap();
    assert_eq!(b.settled(120), "done", "그 데몬이 복원했다");
    assert!(!b.hold().exists(), "잔재를 지웠다");
}

/// 살아 있는 소유자가 있는 동안 기다리고(120초 뒤에도) 죽으면 복원한다 — `cysr` 이름도 소유자다(794 F4).
#[test]
fn a_live_owner_holds_the_restore_until_it_dies() {
    for name in ["cys", "cysr"] {
        let b = Box_::new(&format!("own-{name}"));
        b.up();
        b.settled(120);
        b.down();
        let mut c = b.owner(name);
        let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs();
        // 만료 판정은 소유자 생존 기준이다 — 옛 상한 120초를 넘긴 표식이어도 소유자가 살아 있으면 미룬다.
        write_hold(&b.hold(), now - 200, c.id());
        b.up();
        std::thread::sleep(Duration::from_secs(2));
        assert_eq!(b.phase().as_deref(), Some("held"), "{name}");
        c.kill().unwrap();
        c.wait().unwrap();
        assert_eq!(b.settled(120), "done", "{name}");
        assert!(!b.hold().exists());
    }
}

#[test]
fn a_hold_left_by_a_dead_rotate_does_not_stop_the_next_boot() {
    let b = Box_::new("dead");
    b.up();
    b.settled(120);
    b.down();
    let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs();
    write_hold(&b.hold(), now, 4_000_000);
    b.up();
    assert_ne!(b.phase().as_deref(), Some("held"));
    assert_eq!(b.settled(120), "done");
    assert!(!b.hold().exists(), "잔재를 지운다");
}

/// ④ 실패 — rc 24 · 복귀 표식 유지 · 표식이 풀려 데몬이 좌석을 돌려놓는다.
#[cfg(target_os = "macos")]
#[test]
fn a_failed_pack_step_still_lets_the_daemon_restore() {
    let mut b = Box_::new("fail4");
    let proj = b.seats();
    b.up();
    b.settled(120);
    b.write_topology(&proj);
    let pack = b.base.join("home/.cys/pack");
    let chflags = |f: &str| assert!(Command::new("chflags").arg(f).arg(&pack).status().unwrap().success());
    chflags("uchg");
    let o = b.rotate().wait_with_output().unwrap();
    chflags("nouchg");
    assert_eq!(o.status.code(), Some(24), "{}", String::from_utf8_lossy(&o.stderr));
    assert!(b.pending().exists(), "앱 다음 기동이 재시도한다");
    assert_eq!(b.settled(180), "done");
    assert!(b.claude_log().contains(&format!("cwd={}", proj.display())), "좌석이 돌아왔다: {}", b.claude_log());
}

fn write_hold(p: &Path, ts: u64, pid: u32) {
    std::fs::create_dir_all(p.parent().unwrap()).unwrap();
    std::fs::write(p, format!("{ts} {pid}")).unwrap();
}
