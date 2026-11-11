//! (tabs-sidebar 2d · 설계 §5) `cys seat-group` · `cys open-control-center` — 실 `cys` · 실 `cysd` · 격리 HOME · 격리 소켓.
//! 못박는 것: 좌석 밖(사람 터미널) 호출 = 허용 · master 좌석 안 = 허용 · 워커 좌석 안 = forbidden · 같은 값 = 이벤트 0 ·
//!   `surface.list` 에 group · 빈 값 = 옮김 해제(null) · 잘못된 이름 = invalid_params · ui.open_panel = control-center 만 · 이벤트 1건씩.
#![cfg(unix)]

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::net::UnixStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

const CYS: &str = env!("CARGO_BIN_EXE_cys");

/// 격리 데몬 상자 — spawn 직후부터 Child 를 소유하고 Drop 에서 TERM→KILL→wait(고아 0 · hidden_seat_screen.rs 와 같은 규율).
struct Box_ {
    base: PathBuf,
    sock: PathBuf,
    child: Option<Child>,
}

impl Box_ {
    fn start() -> Self {
        let base = PathBuf::from(format!("/tmp/cys-sg-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        std::fs::create_dir_all(base.join("home")).unwrap();
        let base = base.canonicalize().unwrap();
        std::fs::create_dir_all(base.join("run")).unwrap();
        let sock = base.join("run/cysd.sock");
        let mut b = Self { base, sock, child: None };
        let mut d = Command::new(PathBuf::from(CYS).with_file_name("cysd"));
        d.env_clear()
            .env("PATH", std::env::var("PATH").unwrap_or_default())
            .env("HOME", b.base.join("home"))
            .env("TMPDIR", &b.base)
            .env("CYS_SOCKET", &b.sock)
            .env("CYS_NO_AUTORESTORE", "1")
            .stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null());
        b.child = Some(d.spawn().expect("cysd 기동"));
        let t = Instant::now();
        while UnixStream::connect(&b.sock).is_err() && t.elapsed() < Duration::from_secs(20) {
            std::thread::sleep(Duration::from_millis(100));
        }
        let pid = b.rpc("system.identify", json!({}))["result"]["daemon_pid"].as_u64().map(|p| p as u32);
        assert_eq!(pid, b.child.as_ref().map(|c| c.id()), "소켓의 데몬 = 시험이 띄운 그 자식");
        b
    }
    /// 응답 전체(ok/error 포함)를 돌려준다.
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
        serde_json::from_slice(&got).unwrap()
    }
    fn ok(&self, method: &str, params: Value) -> Value {
        let v = self.rpc(method, params);
        assert!(v.get("error").map_or(true, Value::is_null), "{method}: {v}");
        v["result"].clone()
    }
    /// 좌석 밖(이 시험 프로세스 = 사람 터미널 자리)에서 cys 를 부른다.
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
    fn group_of(&self, sid: u64) -> Value {
        let l = self.ok("surface.list", json!({}));
        l["surfaces"].as_array().unwrap().iter().find(|s| s["surface_id"].as_u64() == Some(sid)).expect("좌석")["group"].clone()
    }
    fn read_until(&self, sid: u64, needle: &str) -> Option<String> {
        let t = Instant::now();
        while t.elapsed() < Duration::from_secs(15) {
            let txt = self.ok("surface.read_text", json!({"surface_id": sid, "lines": 60}))["text"].as_str().unwrap_or("").to_string();
            // 줄머리 일치 — 입력한 명령 줄(「… echo W_RC=$?」)이 아니라 실행 결과 줄만 잡는다
            if let Some(l) = txt.lines().find(|l| l.trim().starts_with(needle)) {
                return Some(l.trim().to_string());
            }
            std::thread::sleep(Duration::from_millis(200));
        }
        None
    }
    fn gone(&mut self) -> bool {
        self.child.as_mut().map_or(true, |c| !matches!(c.try_wait(), Ok(None)))
    }
}

impl Drop for Box_ {
    fn drop(&mut self) {
        if let Some(pid) = self.child.as_ref().map(|c| c.id() as i32) {
            unsafe { libc::kill(pid, libc::SIGTERM) };
            let t = Instant::now();
            while !self.gone() && t.elapsed() < Duration::from_secs(10) {
                std::thread::sleep(Duration::from_millis(100));
            }
            if !self.gone() {
                unsafe { libc::kill(pid, libc::SIGKILL) };
                let t = Instant::now();
                while !self.gone() && t.elapsed() < Duration::from_secs(5) {
                    std::thread::sleep(Duration::from_millis(100));
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
fn seat_group_caller_gate_events_and_list() {
    let b = Box_::start();
    // 이벤트 구독(시험 내내 · 받은 이름만 모은다)
    let mut ev = UnixStream::connect(&b.sock).unwrap();
    let mut line = serde_json::to_vec(&json!({"id": 7, "method": "events.stream", "params": {"names": ["surface.group.changed", "ui.open_panel"]}})).unwrap();
    line.push(b'\n');
    ev.write_all(&line).unwrap();
    let seen: Arc<Mutex<Vec<Value>>> = Arc::default();
    {
        let seen = Arc::clone(&seen);
        let rd = ev.try_clone().unwrap();
        std::thread::spawn(move || {
            for l in BufReader::new(rd).lines().map_while(Result::ok) {
                if let Ok(v) = serde_json::from_str::<Value>(&l) {
                    if v.get("name").is_some() {
                        seen.lock().unwrap().push(v);
                    }
                }
            }
        });
    }
    std::thread::sleep(Duration::from_millis(500));
    let events = |name: &str| seen.lock().unwrap().iter().filter(|v| v["name"] == name).cloned().collect::<Vec<_>>();

    let cwd = b.base.join("home");
    let mk = |role: Option<&str>| {
        let mut p = json!({"cwd": cwd, "rows": 30, "cols": 140});
        if let Some(r) = role {
            p["role"] = json!(r);
        }
        b.ok("surface.create", p)["surface_id"].as_u64().expect("surface_id")
    };
    let target = mk(None);
    let master = mk(Some("master"));
    let worker = mk(Some("worker"));
    let tref = format!("surface:{target}");

    // ① 좌석 밖(사람 터미널) = 허용 · list 에 group · 이벤트 1건
    let o = b.cys(&["seat-group", "--surface", &tref, "site"]);
    assert!(o.status.success(), "좌석 밖 seat-group: {}", String::from_utf8_lossy(&o.stderr));
    assert_eq!(b.group_of(target), json!("site"));
    // ② 같은 값 = 변화 없음 · 이벤트 0
    let o = b.cys(&["seat-group", "--surface", &tref, " site "]);
    assert!(String::from_utf8_lossy(&o.stdout).contains("변화 없음"), "같은 값: {}", String::from_utf8_lossy(&o.stdout));
    // ③ 잘못된 이름 = invalid_params(65자 · 제어문자)
    let long = "가".repeat(65);
    assert_eq!(b.rpc("surface.set_group", json!({"surface_id": target, "group": long}))["error"]["code"], "invalid_params");
    assert_eq!(b.rpc("surface.set_group", json!({"surface_id": target, "group": "a\u{7}b"}))["error"]["code"], "invalid_params");
    assert_eq!(b.rpc("surface.set_group", json!({"surface_id": target, "group": 3}))["error"]["code"], "invalid_params");
    assert_eq!(b.group_of(target), json!("site"), "거부된 호출은 값을 바꾸지 않는다");

    // ④ 좌석 안: 워커 = forbidden · master = 허용(그 좌석 셸에서 같은 cys 를 실행 — 데몬은 peer pid 로 좌석을 푼다)
    let run_in = |sid: u64, group: &str, tag: &str| {
        let cmd = format!("{CYS} seat-group --surface {tref} {group}; echo {tag}_RC=$?\r");
        b.ok("surface.send_text", json!({"surface_id": sid, "text": cmd}));
        b.read_until(sid, &format!("{tag}_RC="))
    };
    let w = run_in(worker, "lms", "W").expect("워커 좌석 결과 줄");
    assert_eq!(w, "W_RC=1", "워커 좌석 = 거부(exit 1)");
    assert_eq!(b.group_of(target), json!("site"), "워커 좌석 호출은 값을 바꾸지 못한다");
    let m = run_in(master, "lms", "M").expect("master 좌석 결과 줄");
    assert_eq!(m, "M_RC=0", "master 좌석 = 허용");
    assert_eq!(b.group_of(target), json!("lms"));

    // ⑤ 빈 값 = 옮김 해제(null)
    let o = b.cys(&["seat-group", "--surface", &tref, ""]);
    assert!(o.status.success());
    assert_eq!(b.group_of(target), Value::Null);

    // ⑥ ui.open_panel — control-center 만 · 좌석 밖 CLI 허용 · 워커 좌석 거부
    assert_eq!(b.rpc("ui.open_panel", json!({"panel": "feed"}))["error"]["code"], "invalid_params");
    let o = b.cys(&["open-control-center"]);
    assert!(o.status.success(), "open-control-center: {}", String::from_utf8_lossy(&o.stderr));
    b.ok("surface.send_text", json!({"surface_id": worker, "text": format!("{CYS} open-control-center; echo U_RC=$?\r")}));
    let u = b.read_until(worker, "U_RC=").expect("워커 좌석 open-control-center 결과 줄");
    assert_eq!(u, "U_RC=1", "워커 좌석 open-control-center = 거부");

    // 이벤트 수 = 실제로 값이 바뀐 횟수(site · lms · 해제 = 3) · 패널 열기 = 1(거부·같은 값은 0)
    let t = Instant::now();
    while (events("surface.group.changed").len() < 3 || events("ui.open_panel").is_empty()) && t.elapsed() < Duration::from_secs(5) {
        std::thread::sleep(Duration::from_millis(100));
    }
    std::thread::sleep(Duration::from_millis(500));
    let g = events("surface.group.changed");
    let seq: Vec<Value> = g.iter().map(|v| v["payload"]["group"].clone()).collect();
    assert_eq!(seq, vec![json!("site"), json!("lms"), Value::Null], "group 이벤트 = 바뀐 값 3건만: {g:?}");
    assert_eq!(g[1]["payload"]["previous"], json!("site"));
    assert!(g.iter().all(|v| v["surface_id"].as_u64() == Some(target)));
    assert_eq!(events("ui.open_panel").len(), 1, "패널 열기 이벤트 = 허용된 1건");
    drop(ev);
}
