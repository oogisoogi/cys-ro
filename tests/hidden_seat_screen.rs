//! ⓑ 숨은 탭 좌석 = 보이는 좌석과 같은 send/read-screen(TICKET=cysr-tabs-sidebar-impl 조각 2c-2) — 실 `cys` · 실 `cysd` · 격리 HOME · 격리 소켓.
//! 앱의 묶음 탭은 숨긴 좌석의 화면 요소를 DOM 에서 떼어 둘 뿐이다(main.ts render() 의 rt.el.remove()). 데몬 쪽에서 「보이는 좌석」 = 출력
//! 구독(surface.attach)이 붙은 좌석 · 「숨은 좌석」 = 구독이 없는 좌석으로 보고, 같은 입력을 보내 read_text(cys read-screen 의 RPC)가
//! 같은 줄을 돌려주는지 잰다.
#![cfg(unix)]

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::net::UnixStream;
use std::path::PathBuf;
use std::process::Command;
use std::time::{Duration, Instant};

const CYS: &str = env!("CARGO_BIN_EXE_cys");

struct Box_ {
    base: PathBuf,
    sock: PathBuf,
}

impl Box_ {
    fn new() -> Self {
        let base = PathBuf::from(format!("/tmp/cys-hss-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        std::fs::create_dir_all(base.join("home")).unwrap();
        let base = base.canonicalize().unwrap();
        std::fs::create_dir_all(base.join("run")).unwrap();
        let sock = base.join("run/cysd.sock");
        Self { base, sock }
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

impl Drop for Box_ {
    fn drop(&mut self) {
        if let Ok(v) = UnixStream::connect(&self.sock).map(|_| self.rpc("system.identify", json!({}))) {
            if let Some(pid) = v["daemon_pid"].as_u64() {
                unsafe { libc::kill(pid as i32, libc::SIGTERM) };
            }
        }
        let t = Instant::now();
        while UnixStream::connect(&self.sock).is_ok() && t.elapsed() < Duration::from_secs(10) {
            std::thread::sleep(Duration::from_millis(100));
        }
        let _ = std::fs::remove_dir_all(&self.base);
    }
}

#[test]
fn hidden_seat_reads_like_visible_seat() {
    let b = Box_::new();
    // 격리 데몬을 직접 띄운다(같은 빌드 폴더의 cysd · 격리 HOME·TMPDIR·소켓) — 소켓이 받을 때까지 기다린다.
    let mut d = Command::new(PathBuf::from(CYS).with_file_name("cysd"));
    d.env_clear()
        .env("PATH", std::env::var("PATH").unwrap_or_default())
        .env("HOME", b.base.join("home"))
        .env("TMPDIR", &b.base)
        .env("CYS_SOCKET", &b.sock)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null());
    let _child = d.spawn().expect("cysd 기동");
    let t = Instant::now();
    while UnixStream::connect(&b.sock).is_err() && t.elapsed() < Duration::from_secs(20) {
        std::thread::sleep(Duration::from_millis(100));
    }
    let _ = b.cys(&["identify"]);
    let cwd = b.base.join("home");
    let mk = || b.rpc("surface.create", json!({"cwd": cwd, "rows": 30, "cols": 100}))["surface_id"].as_u64().expect("surface_id");
    let shown = mk();
    let hidden = mk();
    // 「보이는 좌석」 = 출력 구독이 붙어 있다(앱의 화면 칸과 같은 자리) — 구독 연결을 끝까지 살려 두고 흘려 읽는다.
    let mut att = UnixStream::connect(&b.sock).unwrap();
    let mut line = serde_json::to_vec(&json!({"id": 9, "method": "surface.attach", "params": {"surface_id": shown}})).unwrap();
    line.push(b'\n');
    att.write_all(&line).unwrap();
    let rd = att.try_clone().unwrap();
    std::thread::spawn(move || for _ in BufReader::new(rd).lines() {});
    std::thread::sleep(Duration::from_millis(800));
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
    assert!(probe(shown), "보이는(구독 붙은) 좌석의 read_text 에 결과 줄");
    assert!(probe(hidden), "숨은(구독 없는) 좌석의 read_text 에도 같은 결과 줄 — 숨김이 좌석을 멈추거나 화면을 굳히지 않는다");
    drop(att);
}
