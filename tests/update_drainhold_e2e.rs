//! TICKET=cysr-1111-drainhold 끝-끝 시험 — 살아 있는 좌석이 있는 기기의 자동 갱신이 S3·S4 교착에 걸리지 않고, S10 의 rotate rc 25(복원 일부
//! 보류)가 끝난 갱신을 되돌리지 않는다.
//!
//! 실물: 격리 HOME 의 cysd · `cys drain --verify` · 실 `Runner` · `RealOps` 의 quiesce/drain/recheck/baseline/start_new/post_verify.
//! 대역: 내려받기·정지·스냅샷·교환(이 기기의 앱을 바꾸지 않는다) · 새 번들 = 애드혹 서명한 대본(`rotate` 만 지정 rc · 나머지는 실 `cys` 로 넘김).
#![cfg(target_os = "macos")]

use cys::update::errors::ErrCode;
use cys::update::journal::{self, Journal, Os, State};
use cys::update::realops::{Candidate, Env, RealOps};
use cys::update::runner::{Attempt, Canon, Fail, Kind, Ops, Outcome, Runner, Step};
use serde_json::{json, Value};
use std::io::{Read, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

const CYS: &str = env!("CARGO_BIN_EXE_cys");

fn rpc_on(sock: &Path, method: &str, params: Value) -> Result<Value, String> {
    let mut s = UnixStream::connect(sock).map_err(|e| e.to_string())?;
    s.set_read_timeout(Some(Duration::from_secs(30))).map_err(|e| e.to_string())?;
    let mut line = serde_json::to_vec(&json!({"id": 1, "method": method, "params": params})).unwrap();
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
    match v.get("error").filter(|e| !e.is_null()) {
        Some(e) => Err(e.to_string()),
        None => Ok(v["result"].clone()),
    }
}

/// 이 시험이 띄운 데몬만 끝낸다(격리 소켓이 밝힌 pid · 이름 일치 종료 0).
struct Fixture {
    root: PathBuf,
    upd: PathBuf,
    sock: PathBuf,
    daemon_pid: Option<i32>,
}

impl Drop for Fixture {
    fn drop(&mut self) {
        if let Some(pid) = self.daemon_pid {
            let _ = std::process::Command::new("/bin/kill").args(["-9", &pid.to_string()]).status();
        }
        let _ = std::fs::remove_dir_all(&self.root);
    }
}

const AGENT: &str = r#"
import os, re, subprocess, sys, time, tty
got, cys, trail = sys.argv[1:4]
subprocess.run([cys, "set-status", "--state", "waiting"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try: tty.setraw(0)
except Exception: pass
buf = b""
while True:
    c = os.read(0, 4096)
    if not c: break
    buf += c
    open(got, "ab").write(c)
    t = buf.decode("utf8", "replace")
    m = re.search(r"(/\S*?checkpoint-\S+?\.md)", t)
    if m:
        os.makedirs(os.path.dirname(m.group(1)), exist_ok=True)
        open(m.group(1), "a").write(t + chr(10))
        buf = b""
        for i in range(int(trail)):   # 저장 뒤 턴을 끝내며 나오는 꼬리 출력
            time.sleep(1)
            os.write(1, ("finishing %d\r\n" % i).encode())
"#;

fn fixture(tag: &str) -> Fixture {
    for (k, _) in std::env::vars() {
        if k.starts_with("CYS_") || k.starts_with("CLAUDE") || k.starts_with("AITERM") || k.starts_with("CMUX") {
            std::env::remove_var(k);
        }
    }
    let root = PathBuf::from(format!("/tmp/cysdh-{tag}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    let home = root.join("h");
    let upd = home.join(".cys/update");
    std::fs::create_dir_all(&upd).unwrap();
    let sock = root.join("s.sock");
    std::env::set_var("HOME", &home);
    std::env::set_var("CYS_SOCKET", &sock);
    std::env::set_var("AITERM_SOCKET", &sock);
    std::env::set_var("XDG_STATE_HOME", home.join("st"));
    std::env::set_var("CYS_UPDATE_STATE_DIR", &upd);
    std::env::set_var("PATH", "/usr/bin:/bin");
    let mut f = Fixture { root, upd, sock, daemon_pid: None };
    let start = Instant::now();
    while !std::process::Command::new(CYS).arg("list").stdin(std::process::Stdio::null()).output().map(|o| o.status.success()).unwrap_or(false) {
        assert!(start.elapsed() < Duration::from_secs(60), "격리 데몬이 뜨지 않음");
        std::thread::sleep(Duration::from_secs(1));
    }
    std::thread::sleep(Duration::from_secs(2));
    f.daemon_pid = rpc_on(&f.sock, "system.identify", json!({})).unwrap()["daemon_pid"].as_i64().map(|p| p as i32);
    f
}

fn add_seat(f: &Fixture, role: &str, trail: u32) -> PathBuf {
    let agent = f.root.join("agent.py");
    let got = f.root.join(format!("got-{role}.log"));
    std::fs::write(&agent, AGENT).unwrap();
    let cmd = format!("/usr/bin/python3 -u {} {} {CYS} {trail}", agent.display(), got.display());
    let o = std::process::Command::new(CYS)
        .args(["new-surface", "--role", role, "--agent", "claude", "--cwd"])
        .arg(&f.root)
        .args(["--cmd", &cmd])
        .stdin(std::process::Stdio::null())
        .output()
        .unwrap();
    assert!(o.status.success(), "좌석 생성 실패: {}", String::from_utf8_lossy(&o.stderr));
    let start = Instant::now();
    loop {
        let org = rpc_on(&f.sock, "org.status", json!({})).unwrap();
        let reported = org["surfaces"].as_array().unwrap().iter().any(|s| s["role"] == role && s["status"]["state"].is_string());
        if reported {
            return got;
        }
        assert!(start.elapsed() < Duration::from_secs(20), "좌석 자기신고 없음: {}", org["surfaces"]);
        std::thread::sleep(Duration::from_millis(200));
    }
}

/// 새 번들 = 애드혹 서명한 대본. 반환 = CDHash(`codesign` 이 정식 자리 표지로 읽는 값).
fn fake_bundle(f: &Fixture, rotate_rc: i32) -> (PathBuf, String) {
    let app = f.root.join("fake.app");
    let exe = app.join("Contents/MacOS/cys");
    std::fs::create_dir_all(exe.parent().unwrap()).unwrap();
    std::fs::write(
        app.join("Contents/Info.plist"),
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?><plist version=\"1.0\"><dict><key>CFBundleExecutable</key><string>cys</string><key>CFBundleIdentifier</key><string>test.cysdh</string></dict></plist>",
    )
    .unwrap();
    std::fs::write(
        &exe,
        format!("#!/bin/sh\necho \"$*\" >> '{log}'\ncase \"$1\" in rotate) exit {rotate_rc};; esac\nexec '{CYS}' \"$@\"\n", log = f.root.join("calls.log").display()),
    )
    .unwrap();
    std::fs::set_permissions(&exe, std::fs::Permissions::from_mode(0o755)).unwrap();
    let s = std::process::Command::new("/usr/bin/codesign").args(["--force", "-s", "-"]).arg(&app).output().unwrap();
    assert!(s.status.success(), "애드혹 서명 실패: {}", String::from_utf8_lossy(&s.stderr));
    let d = std::process::Command::new("/usr/bin/codesign").arg("-dvvv").arg(&app).output().unwrap();
    let text = format!("{}{}", String::from_utf8_lossy(&d.stdout), String::from_utf8_lossy(&d.stderr));
    let cd = text.lines().find_map(|l| l.strip_prefix("CDHash=")).expect("CDHash").trim().to_string();
    (app, cd)
}

fn real_ops(f: &Fixture, token: &str, app: PathBuf, cdhash: &str) -> RealOps {
    let bi: Value = serde_json::from_slice(&std::process::Command::new(CYS).args(["build-info", "--json"]).output().unwrap().stdout).unwrap();
    let pack = f.root.join("h/.cys/pack");
    let read = |n: &str| std::fs::read_to_string(pack.join(n)).map(|s| s.trim().to_string()).unwrap_or_default();
    let asset = serde_json::from_value(json!({
        "url": "", "size": 0, "sha256": "", "max_unpacked": 0, "target": bi["target"], "release_seq": bi["release_seq"], "build_id": bi["build_id"],
        "cdhash": cdhash, "bundled_pack": {"version": read("VERSION"), "digest": read(".pack-digest")},
    }))
    .unwrap();
    let cand = Candidate {
        asset,
        version: "9.9.9".into(),
        release_seq: bi["release_seq"].as_u64().unwrap_or(0),
        installed_revoked: false,
        notes_ko: None,
        feed_rev: None,
        envelope_sha256: None,
        envelope_signed_at: None,
        release_b64: None,
        release_sig_b64: None,
    };
    let sock = f.sock.clone();
    let env = Env {
        os: Os::Mac,
        update_dir: f.upd.clone(),
        cys_root: f.root.join("h/.cys"),
        daemon_state_dir: f.root.join("h/st"),
        canonical_app: app,
        install_dir: f.root.join("h/st"),
        channel: "stable".into(),
        old_cys: PathBuf::from(CYS),
        rpc: Box::new(move |m, p| rpc_on(&sock, m, p)),
        settle_secs: 2,
        dry_run: false,
        counsel_dir: Some(f.root.join("counsel")),
    };
    RealOps::new(env, token.to_string(), cand, "1.1.11".into())
}

/// 실행층 혼합 — S3~S5b·S10·S11 = 실물 · 교체 쪽 = 대역(기록만).
struct Hybrid {
    real: RealOps,
    sock: PathBuf,
    token: String,
    log: Vec<String>,
    /// S3 직후 좌석으로 보내는 비사람 입력(정비 모드가 보류해야 한다).
    send_after_quiesce: Option<u64>,
    held_ack: Option<Value>,
    swapped: bool,
}

impl Ops for Hybrid {
    fn os(&self) -> Os {
        Os::Mac
    }
    fn fetch(&mut self, j: &mut Journal) -> Step {
        j.release_seq = 9;
        j.stage_tree_sha256 = "s".repeat(64);
        Ok(())
    }
    fn quiesce(&mut self, j: &Journal) -> Step {
        self.log.push("quiesce".into());
        self.real.quiesce(j)?;
        if let Some(sid) = self.send_after_quiesce {
            self.held_ack = Some(rpc_on(&self.sock, "surface.send_text", json!({"surface_id": sid, "text": "남의 입력"})).unwrap());
        }
        Ok(())
    }
    fn drain(&mut self, j: &Journal) -> Step {
        self.log.push("drain".into());
        self.real.drain(j)
    }
    fn recheck(&mut self, j: &Journal) -> Step {
        self.log.push("recheck".into());
        self.real.recheck(j)
    }
    fn baseline(&mut self, j: &Journal) -> Step {
        self.real.baseline(j)
    }
    fn confirm(&mut self, _: &Journal) -> Step {
        Ok(())
    }
    fn stop(&mut self, _: &Journal) -> Step {
        self.log.push("stop".into());
        Ok(())
    }
    fn snapshot(&mut self, j: &mut Journal) -> Step {
        j.snapshot_dir = "/snap".into();
        j.snapshot_manifest_sha256 = "m".repeat(64);
        Ok(())
    }
    fn commit_check(&mut self, _: &Journal) -> Step {
        Ok(())
    }
    fn canonical(&mut self, _: &Journal) -> Canon {
        if self.swapped {
            Canon::New
        } else {
            Canon::Old
        }
    }
    fn swap(&mut self, _: &mut Journal) -> Step {
        self.log.push("swap".into());
        self.swapped = true;
        Ok(())
    }
    fn payload_ok(&mut self, _: &Journal) -> Step {
        Ok(())
    }
    fn start_new(&mut self, j: &Journal) -> Step {
        self.log.push("start_new".into());
        let r = self.real.start_new(j);
        // 실물은 새 데몬이 뜨며 정비 모드가 사라진다 — 대역 교체라 같은 데몬이므로 여기서 푼다.
        let _ = rpc_on(&self.sock, "update.release", json!({"txn": self.token}));
        r
    }
    fn post_verify(&mut self, j: &Journal, rollback: bool) -> Step {
        self.log.push(format!("post_verify rollback={rollback}"));
        self.real.post_verify(j, rollback)
    }
    fn commit(&mut self, _: &Journal) -> Step {
        self.log.push("commit".into());
        Ok(())
    }
    fn release(&mut self, _: &Journal) {
        self.log.push("release".into());
        let _ = rpc_on(&self.sock, "update.release", json!({"txn": self.token}));
    }
    fn start_old(&mut self, _: &Journal) -> Step {
        self.log.push("start_old".into());
        Ok(())
    }
    fn rb_prepare(&mut self, _: &Journal) -> Step {
        self.log.push("rb_prepare".into());
        Ok(())
    }
    fn rb_swap(&mut self, _: &Journal) -> Step {
        Ok(())
    }
    fn rb_restore(&mut self, _: &Journal) -> Step {
        Ok(())
    }
    fn recover_pack(&mut self, _: &Journal) -> Result<bool, Fail> {
        Ok(false)
    }
    fn reconstruct(&mut self, _: &Attempt) -> Result<bool, Fail> {
        Err(Fail::new(ErrCode::RotateFailed, "test", "대역 밖"))
    }
    fn restart_after_reconstruct(&mut self) -> Step {
        Ok(())
    }
    fn daemon_alive(&mut self) -> bool {
        true
    }
    fn pack_available(&mut self) -> Result<bool, Fail> {
        Ok(false)
    }
    fn pack_prepare(&mut self, _: &mut Journal) -> Step {
        Ok(())
    }
    fn pack_apply(&mut self, _: &Journal) -> Step {
        Ok(())
    }
    fn record(&mut self, j: Option<&Journal>, kind: Kind, fail: Option<&Fail>) {
        self.log.push(format!("record {kind:?}"));
        self.real.record(j, kind, fail);
    }
}

fn seat_count(got: &Path, needle: &str) -> usize {
    std::fs::read_to_string(got).unwrap_or_default().matches(needle).count()
}

fn run_update(f: &Fixture, rotate_rc: i32, send_after_quiesce: Option<u64>) -> (Outcome, Vec<String>, Option<Value>) {
    let (app, cd) = fake_bundle(f, rotate_rc);
    let guard = cys::update::lock::acquire(&f.upd, "runner").expect("잠금");
    let tok = guard.token();
    let mut ops = Hybrid { real: real_ops(f, &tok.render(), app, &cd), sock: f.sock.clone(), token: tok.render(), log: vec![], send_after_quiesce, held_ack: None, swapped: false };
    let o = Runner::new(&f.upd, &tok.txn_id, tok.epoch, &mut ops).run();
    drop(guard);
    (o, ops.log, ops.held_ack)
}

/// ① 좌석 1개 · 저장 뒤 꼬리 출력 3초 · 정비 모드 · drain → 교체 → rotate rc 25 → 롤백 없음 → DONE.
/// ② 같은 판에서 정비 모드 중 남의 입력 = 여전히 보류 + S5 가 보류로 끝(좌석 도달 0 · 교체 0).
#[test]
fn live_seat_update_passes_drain_and_rc25_does_not_roll_back() {
    let f = fixture("e2e");
    let got = add_seat(&f, "worker-a", 3);

    let (o, log, _) = run_update(&f, 25, None);
    assert!(matches!(o, Outcome::Done), "좌석 있는 기기의 갱신이 끝까지 가지 못함: {o:?} · {log:?}");
    assert_eq!(seat_count(&got, "[DRAIN-VERIFY]"), 1, "저장 지시 정확히 1회 도달");
    assert!(!log.iter().any(|l| l.starts_with("rb_") || l.contains("Rollback")), "롤백 0: {log:?}");
    assert_eq!(journal::read(&f.upd).journal().unwrap().state, State::Done);
    let at = |w: &str| log.iter().position(|l| l == w).unwrap_or_else(|| panic!("{w} 없음: {log:?}"));
    assert!(at("drain") < at("swap") && at("quiesce") < at("swap"), "{log:?}");
    assert!(!f.upd.join("hold-queue.jsonl").exists() || std::fs::metadata(f.upd.join("hold-queue.jsonl")).unwrap().len() == 0, "저장 지시가 보류 로그로 새지 않음");
    let state: Value = serde_json::from_slice(&std::fs::read(f.upd.join("state.json")).unwrap()).unwrap();
    assert!(state.to_string().contains("restore_partial"), "rc 25 보류 기록 없음: {state}");

    let org = rpc_on(&f.sock, "org.status", json!({})).unwrap();
    let sid = org["surfaces"].as_array().unwrap().iter().find(|s| s["role"] == "worker-a").unwrap()["surface_id"].as_u64().unwrap();
    let before = seat_count(&got, "남의 입력");
    let (o2, log2, ack) = run_update(&f, 0, Some(sid));
    assert_eq!(ack.as_ref().and_then(|a| a["held"].as_bool()), Some(true), "정비 모드가 남의 입력을 보류하지 않음: {ack:?}");
    assert!(matches!(&o2, Outcome::Deferred(x) if x.detail.contains("보류 로그")), "S5 가 잡아야 함: {o2:?} · {log2:?}");
    assert!(!log2.iter().any(|l| l == "swap"), "교체 0: {log2:?}");
    assert_eq!(seat_count(&got, "남의 입력"), before, "보류 중 좌석 도달 0");
}
