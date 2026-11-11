//! ⓑ 숨은 탭 좌석 = 보이는 좌석과 같은 send/read-screen(TICKET=cysr-tabs-sidebar-impl 조각 2c-2) — 실 `cys` · 실 `cysd` · 격리 HOME · 격리 소켓.
//! ★이 시험이 주장하는 것은 하나뿐이다(codex 1R): **출력 구독(surface.attach) 유무와 무관하게** 같은 입력에 read_text(cys read-screen 의
//! RPC)가 같은 결과 줄을 돌려준다. 「보이는 좌석」 = 구독이 붙은(ack ok 확인) 좌석 · 「숨은 좌석」 = 구독이 없는 좌석으로 본다.
//! 앱의 숨김 자체(DOM 떼어 두기 · main.ts render() 의 rt.el.remove())와 PTY 크기 보존(fitPane 같은 크기 재전송 0)은 이 시험의 몫이 아니다 —
//! 그쪽은 2c-1 실측(c99378c6 · 탭 20회 왕복 resize 131 → 4)과 ui 시험이 맡는다.
#![cfg(unix)]

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::net::UnixStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::time::{Duration, Instant};

const CYS: &str = env!("CARGO_BIN_EXE_cys");

struct Box_ {
    base: PathBuf,
    sock: PathBuf,
    /// 시험이 띄운 격리 데몬 — spawn 직후부터 이 상자가 소유한다(어느 단계에서 실패해도 Drop 이 내리고 거둔다 · 고아 데몬 0).
    child: Option<Child>,
    /// system.identify 로 잰 데몬 pid(child 와 같아야 한다 — 아래 단언). 다르면 둘 다 내린다.
    pid: Option<i32>,
}

impl Box_ {
    fn new() -> Self {
        let base = PathBuf::from(format!("/tmp/cys-hss-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        std::fs::create_dir_all(base.join("home")).unwrap();
        let base = base.canonicalize().unwrap();
        std::fs::create_dir_all(base.join("run")).unwrap();
        let sock = base.join("run/cysd.sock");
        Self { base, sock, child: None, pid: None }
    }
    fn cys(&self, args: &[&str]) -> std::process::Output {
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
    fn rpc(&self, method: &str, params: Value) -> Value {
        let mut s = UnixStream::connect(&self.sock).expect("connect");
        s.set_read_timeout(Some(Duration::from_secs(10))).unwrap();
        let mut line = serde_json::to_vec(&json!({"id": 1, "method": method, "params": params})).unwrap();
        line.push(b'\n');
        s.write_all(&line).unwrap();
        let mut got = Vec::new();
        let mut buf = [0u8; 65536];
        while !got.ends_with(b"\n") {
            match s.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => got.extend_from_slice(&buf[..n]),
                Err(e) => panic!("{method}: {e}"),
            }
        }
        let v: Value = serde_json::from_slice(&got).unwrap();
        assert!(v.get("error").map_or(true, Value::is_null), "{method}: {v}");
        v["result"].clone()
    }
}

impl Box_ {
    /// 프로세스가 사라졌는가 — 직접 자식이면 try_wait 로 거둔다(거두기 전 좀비는 kill(pid,0) 에 살아 있는 것으로 보인다).
    fn gone(&mut self, pid: i32) -> bool {
        if let Some(c) = self.child.as_mut() {
            if c.id() as i32 == pid {
                return !matches!(c.try_wait(), Ok(None));
            }
        }
        (unsafe { libc::kill(pid, 0) }) != 0
    }
    fn wait_gone(&mut self, pid: i32, limit: Duration) -> bool {
        let t = Instant::now();
        while !self.gone(pid) {
            if t.elapsed() >= limit {
                return false;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        true
    }
}

impl Drop for Box_ {
    fn drop(&mut self) {
        // 소켓이 아니라 **프로세스**가 사라질 때까지 기다린다 — 소켓만 보면 내려가는 중인 데몬이 상태 폴더를 다시 써 고아로 남았다(첫 실행 실측).
        // TERM → 10초 → KILL → 5초 안에 사라짐 확인 → 자식 wait(좀비 0).
        let mut pids: Vec<i32> = self.pid.into_iter().collect();
        if let Some(c) = self.child.as_ref() {
            let p = c.id() as i32;
            if !pids.contains(&p) {
                pids.push(p);
            }
        }
        for pid in pids {
            unsafe { libc::kill(pid, libc::SIGTERM) };
            if !self.wait_gone(pid, Duration::from_secs(10)) {
                unsafe { libc::kill(pid, libc::SIGKILL) };
                if !self.wait_gone(pid, Duration::from_secs(5)) {
                    eprintln!("hidden_seat_screen: 격리 데몬 pid {pid} 가 KILL 뒤에도 남음 — 손으로 확인 필요");
                }
            }
        }
        if let Some(mut c) = self.child.take() {
            let _ = c.kill();
            let _ = c.wait();
        }
        let _ = std::fs::remove_dir_all(&self.base);
    }
}

#[test]
fn hidden_seat_reads_like_visible_seat() {
    let mut b = Box_::new();
    // 격리 데몬을 직접 띄운다(같은 빌드 폴더의 cysd · 격리 HOME·TMPDIR·소켓) — 소켓이 받을 때까지 기다린다.
    let mut d = Command::new(PathBuf::from(CYS).with_file_name("cysd"));
    d.env_clear()
        .env("PATH", std::env::var("PATH").unwrap_or_default())
        .env("HOME", b.base.join("home"))
        .env("TMPDIR", &b.base)
        .env("CYS_SOCKET", &b.sock)
        // 콜드부트 자동 복원(phoenix 손자 프로세스)을 끈다 — 데몬을 내린 뒤에도 남는 손자가 첫 실측에 보였다(시험엔 복원이 필요 없다)
        .env("CYS_NO_AUTORESTORE", "1")
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null());
    b.child = Some(d.spawn().expect("cysd 기동")); // 이 줄부터 어떤 실패에도 Drop 이 데몬을 내린다
    let t = Instant::now();
    while UnixStream::connect(&b.sock).is_err() && t.elapsed() < Duration::from_secs(20) {
        std::thread::sleep(Duration::from_millis(100));
    }
    b.pid = b.rpc("system.identify", json!({}))["daemon_pid"].as_u64().map(|p| p as i32);
    assert_eq!(b.pid, b.child.as_ref().map(|c| c.id() as i32), "소켓의 데몬 = 시험이 띄운 그 자식(남의 데몬에 붙지 않았다)");
    let cwd = b.base.join("home");
    let mk = || b.rpc("surface.create", json!({"cwd": cwd, "rows": 30, "cols": 100}))["surface_id"].as_u64().expect("surface_id");
    let shown = mk();
    let hidden = mk();
    // 「보이는 좌석」 = 출력 구독이 붙어 있다(앱의 화면 칸과 같은 자리) — 첫 줄 ack 가 ok 인지 확인한 뒤(구독 실패면 여기서 멈춘다 · codex 1R)
    //   구독 연결을 끝까지 살려 두고 나머지 원시 출력을 흘려 읽는다.
    let mut att = UnixStream::connect(&b.sock).unwrap();
    att.set_read_timeout(Some(Duration::from_secs(10))).unwrap();
    let mut line = serde_json::to_vec(&json!({"id": 9, "method": "surface.attach", "params": {"surface_id": shown}})).unwrap();
    line.push(b'\n');
    att.write_all(&line).unwrap();
    let mut rd = BufReader::new(att.try_clone().unwrap());
    let mut ack = String::new();
    rd.read_line(&mut ack).expect("attach ack");
    let ack_v: Value = serde_json::from_str(ack.trim()).unwrap_or(Value::Null);
    assert_eq!(ack_v["ok"].as_bool(), Some(true), "보이는 좌석 구독(surface.attach) 성공 ack: {}", ack.trim());
    rd.get_ref().set_read_timeout(None).unwrap();
    std::thread::spawn(move || {
        let mut buf = [0u8; 8192];
        while matches!(rd.read(&mut buf), Ok(n) if n > 0) {}
    });
    for sid in [shown, hidden] {
        b.rpc("surface.send_text", json!({"surface_id": sid, "text": "echo HSS_PROBE_$((6*7))\r"}));
    }
    let probe = |sid: u64| -> bool {
        let t = Instant::now();
        while t.elapsed() < Duration::from_secs(10) {
            let txt = b.rpc("surface.read_text", json!({"surface_id": sid, "lines": 40}))["text"].as_str().unwrap_or("").to_string();
            if txt.lines().any(|l| l.trim() == "HSS_PROBE_42") {
                return true;
            }
            std::thread::sleep(Duration::from_millis(200));
        }
        false
    };
    assert!(probe(shown), "구독 붙은 좌석의 read_text 에 결과 줄");
    assert!(probe(hidden), "구독 없는 좌석의 read_text 에도 같은 결과 줄 — 구독 유무가 좌석 진행·read_text 를 바꾸지 않는다");
    drop(att);
}
