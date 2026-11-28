//! ★(1.1.21 · TICKET=cysr-1121-restore D5 · codex·Fable 코드 1R major) 「자동 복원 중 보통 launch-agent 거절(rc 95)」 의 **운영 배선**을
//! 실 `cys` 바이너리로 돈다 — 명령줄 해석 → 갈래 → env 두 키 읽기 → 데몬 RPC 두 번(org.status · system.topology) → 응답 칸 해석 →
//! rc 반환 → 기동 0. 데몬은 가짜(격리 소켓 · 받은 메서드를 전부 적는다)라 우리 맥 실제 데몬·좌석에 닿지 않는다.
//! 살려 두면 안 되는 변이(Fable 코드 1R): 갈래에서 rc 를 버림 · 래퍼가 None · `"1"` 판정 늘 참 · 응답 칸 오타 · 호출 줄 주석 처리 —
//! 다섯 모두 아래 ①이 붉어진다(rc ≠ 95 이거나 기동 RPC 가 온다).
#![cfg(unix)]

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixListener;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

const CYS: &str = env!("CARGO_BIN_EXE_cys");
/// 거절 판정이 읽는 두 메서드 — 그 밖의 메서드가 오면 기동 길로 들어간 것이다.
const PROBES: [&str; 2] = ["org.status", "system.topology"];

struct FakeDaemon {
    base: PathBuf,
    sock: PathBuf,
    seen: Arc<Mutex<Vec<String>>>,
}

impl FakeDaemon {
    /// `phase` = org.status 의 daemon.auto_restore · 저장 목록 = cso·worker·master(모두 대기 · 좌석 없음).
    fn new(tag: &str, phase: &str) -> Self {
        let base = PathBuf::from(format!("/tmp/cys-lrr-{}-{tag}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        // 기동 길이 첫 RPC 까지 가도록 최소 agents.json(실제 CLI 를 띄우지 않는다 — 가짜 데몬이 기동 RPC 를 거절한다).
        std::fs::create_dir_all(base.join("home/.cys/pack")).unwrap();
        std::fs::write(base.join("home/.cys/pack/agents.json"), r#"{"claude": {"cmd": "true"}}"#).unwrap();
        let sock = base.join("d.sock");
        let listener = UnixListener::bind(&sock).expect("가짜 소켓 bind");
        let seen = Arc::new(Mutex::new(Vec::new()));
        let (seen2, phase) = (seen.clone(), phase.to_string());
        std::thread::spawn(move || {
            for stream in listener.incoming() {
                let Ok(mut stream) = stream else { break };
                let mut reader = BufReader::new(stream.try_clone().unwrap());
                // 한 연결에 여러 줄이 올 수 있다 — 줄마다 답한다.
                loop {
                    let mut line = String::new();
                    match reader.read_line(&mut line) {
                        Ok(0) | Err(_) => break,
                        Ok(_) => {}
                    }
                    let req: Value = serde_json::from_str(line.trim()).unwrap_or(Value::Null);
                    let m = req["method"].as_str().unwrap_or("").to_string();
                    seen2.lock().unwrap().push(m.clone());
                    let reply = match m.as_str() {
                        "org.status" => json!({"id": req["id"], "ok": true, "result": {"daemon": {"auto_restore": phase}}}),
                        "system.topology" => json!({"id": req["id"], "ok": true, "result": {
                            "saved": [{"role": "cso", "agent": "claude"}, {"role": "worker", "agent": "claude"}, {"role": "master", "agent": "claude"}],
                            "tombstones": [], "live": []}}),
                        // 기동 길의 RPC = 즉시 실패(시험이 기다리지 않게) — 도착 자체가 「기동하려 했다」 의 증거다.
                        _ => json!({"id": req["id"], "ok": false, "error": "fake-daemon: not served"}),
                    };
                    if writeln!(stream, "{reply}").is_err() {
                        break;
                    }
                }
            }
        });
        Self { base, sock, seen }
    }

    /// 실 cys 를 격리 env 로 돌린다(env_clear · 격리 HOME · 가짜 소켓 · 자동 기동 끔). 20초 상한(넘으면 죽이고 붉음).
    fn launch(&self, role: &str, extra: &[(&str, &str)], resume_saved: bool) -> (Option<i32>, String, String, Vec<String>) {
        self.seen.lock().unwrap().clear();
        let mut c = Command::new(CYS);
        c.args(["launch-agent", "--role", role, "--agent", "claude"]);
        if resume_saved {
            c.arg("--resume-saved");
        }
        c.env_clear()
            .env("PATH", std::env::var("PATH").unwrap_or_default())
            .env("HOME", self.base.join("home"))
            .env("TMPDIR", &self.base)
            .env("CYS_SOCKET", &self.sock)
            .env("CYS_NO_AUTOSTART", "1")
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        for (k, v) in extra {
            c.env(k, v);
        }
        let mut child = c.spawn().unwrap();
        let t = Instant::now();
        let status = loop {
            if let Some(s) = child.try_wait().unwrap() {
                break Some(s);
            }
            if t.elapsed() > Duration::from_secs(20) {
                let _ = child.kill();
                let _ = child.wait();
                break None;
            }
            std::thread::sleep(Duration::from_millis(20));
        };
        let out = child.wait_with_output().unwrap();
        let rc = status.and_then(|s| s.code());
        (rc, String::from_utf8_lossy(&out.stdout).into_owned(), String::from_utf8_lossy(&out.stderr).into_owned(),
         self.seen.lock().unwrap().clone())
    }
}

impl Drop for FakeDaemon {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.base);
    }
}

fn launched(seen: &[String]) -> bool {
    seen.iter().any(|m| !PROBES.contains(&m.as_str()))
}

#[test]
fn real_cys_refuses_plain_launch_while_auto_restore_revives_the_role() {
    let d = FakeDaemon::new("held", "held");
    // ① 복원 중(held) · 저장 cso 대기 → rc 95 · 기동 RPC 0 · 안내 = stderr 만(stdout 0 바이트 = surface ref 없음)
    let (rc, out, err, seen) = d.launch("cso", &[], false);
    assert_eq!(rc, Some(95), "rc · stderr={err} · seen={seen:?}");
    assert!(!launched(&seen), "거절인데 기동 RPC 가 왔다: {seen:?}");
    assert_eq!(seen, PROBES, "판정 RPC 는 org.status → system.topology 두 번");
    assert!(out.is_empty(), "안내가 stdout 에도 나왔다(stderr 한 곳 계약): {out:?}");
    assert!(err.contains("rc 95") && err.contains("auto_restore=held") && err.contains("'cso'"), "안내: {err}");
    assert_eq!(err.matches("[launch-agent] role=cso").count(), 1, "안내 한 번: {err}");
    // worker 요청 = 계열(저장 worker 대기) → 95
    let (rc, _, err, seen) = d.launch("worker", &[], false);
    assert_eq!(rc, Some(95), "worker 계열 · {err} · {seen:?}");
    assert!(!launched(&seen));

    // ② 탈출 손잡이 · ③ phoenix 표지 · master = 판정 RPC 0 · 기동 길로 들어간다(가짜 데몬이 거절해 rc ≠ 95 로 끝남)
    for (role, extra) in [("cso", vec![("CYS_LAUNCH_DURING_RESTORE", "1")]), ("cso", vec![("CYS_AUTO_RESTORE_SELF", "1")]), ("master", vec![])] {
        let (rc, _, err, seen) = d.launch(role, &extra, false);
        assert_ne!(rc, Some(95), "{role} {extra:?} 가 거절됐다: {err}");
        assert!(!seen.iter().any(|m| PROBES.contains(&m.as_str())), "{role} {extra:?} 가 판정 RPC 를 불렀다(값싼 판정 먼저): {seen:?}");
        assert!(launched(&seen), "{role} {extra:?} 가 기동 길로 가지 않았다: rc={rc:?} seen={seen:?} err={err}");
    }
    // 손잡이 값이 "1" 이 아니면 켜지지 않는다
    let (rc, _, _, seen) = d.launch("cso", &[("CYS_LAUNCH_DURING_RESTORE", "yes")], false);
    assert_eq!(rc, Some(95), "{seen:?}");

    // ④ --resume-saved(boot·boot_node 길)는 손대지 않는다 — 거절 판정 없이 기동 길
    let (rc, _, err, seen) = d.launch("cso", &[], true);
    assert_ne!(rc, Some(95), "--resume-saved 가 거절됐다: {err}");
    assert!(launched(&seen), "--resume-saved 가 기동 길로 가지 않았다: {seen:?}");
}

#[test]
fn real_cys_launches_as_before_when_auto_restore_is_not_in_progress() {
    for phase in ["done", "off"] {
        let d = FakeDaemon::new(phase, phase);
        let (rc, _, err, seen) = d.launch("cso", &[], false);
        assert_ne!(rc, Some(95), "{phase}: 거절됐다 · {err}");
        assert_eq!(seen.first().map(String::as_str), Some("org.status"), "{phase}: {seen:?}");
        assert!(!seen.iter().any(|m| m == "system.topology"), "{phase}: 진행 아님인데 topology 를 읽었다: {seen:?}");
        assert!(launched(&seen), "{phase}: 기동 길로 가지 않았다: {seen:?}");
    }
}
