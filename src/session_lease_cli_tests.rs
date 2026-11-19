//! TICKET=cysr-seatkeep-t1 — `cys` 바이너리 안쪽 시험(복원 루프 · 가짜 데몬 · 기록 기동기).
//! `src/bin/cys.rs` 의 `#[cfg(test)] #[path]` 한 줄로 붙는다(기존 시험 모듈 무수정 — 병합 충돌 축소).
#![cfg(unix)]

use super::*;

/// 기동 기록 — (역할 · 갈래 · resume · 세션).
struct LeaseRec {
    calls: Vec<(String, &'static str, bool, Option<String>)>,
    /// in-seat 결과: 쓰기 결과 불명(⑪ 주입).
    in_seat_unknown: bool,
    /// in-seat 결과: 기동 명령을 보낸 뒤 일반 오류(set_meta 등 · codex 6R 주입).
    in_seat_err_after_send: bool,
    /// in-seat 결과 주입(codex 1R C1·C2): (그 좌석의 「기동 글 수락」 기록 = None 이면 기록 없음 · 오류 종류 "journal"|"unknown"|"generic").
    in_seat_err: Option<(Option<bool>, &'static str)>,
    /// fresh 결과 주입: (rc · 만든 좌석 98 의 「기동 글 수락」 기록 · 역할 이름 조회 = 99 = 남의 좌석).
    fresh_rc: Option<(i32, Option<bool>)>,
}

/// 줄 주석을 걷은 본문(핀이 주석 문장에 반응하지 않게 · 이 두 파일엔 문자열 안 `//` 없음).
fn code_only(src: &str) -> String {
    src.lines().map(|l| l.split("//").next().unwrap_or("")).collect::<Vec<_>>().join("\n")
}

/// 시험 주입 오류 문자열 — 운영 분류기(is_journal_refusal · is_write_outcome_unknown)가 읽는 모양 그대로.
fn injected_err(kind: &str) -> String {
    match kind {
        "journal" => format!("{}: writer journal unavailable (시험 주입)", cys::ERR_JOURNAL_UNAVAILABLE),
        "unknown" => format!("{}: barrier budget passed (시험 주입)", cys::ERR_WRITE_OUTCOME_UNKNOWN),
        _ => "surface.set_meta: 시험 주입 일반 오류".into(),
    }
}

impl RestoreLauncher for LeaseRec {
    fn in_seat(&mut self, sid: u64, role: &str, _a: &str, resume: bool, sess: Option<&str>,
               _c: Option<&str>, _cfg: Option<&str>) -> Result<Result<BootVerdict, String>, String> {
        self.calls.push((role.into(), "in-seat", resume, sess.map(String::from)));
        if let Some((note, kind)) = self.in_seat_err {
            if let Some(resumed) = note {
                lease_note_launch(sid, resumed);
            }
            return Ok(Err(injected_err(kind)));
        }
        if self.in_seat_err_after_send {
            lease_note_launch(sid, resume); // boot_agent_on_surface 가 기동 명령 직전에 적는 것과 같다
            return Ok(Err("surface.set_meta: 시험 주입 일반 오류(기동 명령 뒤)".into()));
        }
        if self.in_seat_unknown {
            return Ok(Err(format!("{}: barrier budget passed (시험 주입)", cys::ERR_WRITE_OUTCOME_UNKNOWN)));
        }
        Ok(Ok(BootVerdict::Ready))
    }
    fn fresh(&mut self, role: &str, _a: &str, _c: Option<String>, resume: bool, sess: Option<String>,
             _cfg: Option<String>, _t: Option<String>) -> (i32, Option<u64>) {
        self.calls.push((role.into(), "fresh", resume, sess));
        // 98 = 이 기동이 만든 좌석(run_launch_agent_opts 반환 · 데몬이 이름을 바꿔 띄운 좌석 — 가짜 데몬 resolve_role 은 99 = 남의 좌석)
        let Some((rc, note)) = self.fresh_rc else { return (0, Some(98)) };
        if let Some(resumed) = note {
            lease_note_launch(98, resumed);
        }
        (rc, Some(98))
    }
}

type LeaseCalls = Vec<(String, &'static str, bool, Option<String>)>;

/// 한 회차의 가짜 데몬 답(topology live · surface.list) + in-seat 결과 불명 주입 여부.
#[derive(Default)]
struct LeaseRound {
    live: Value,
    surfaces: Value,
    in_seat_unknown: bool,
    in_seat_err_after_send: bool,
    no_resume: bool,
    in_seat_err: Option<(Option<bool>, &'static str)>,
    fresh_rc: Option<(i32, Option<bool>)>,
    /// 회차 끝에 이 대화의 임대 파일을 읽어 [`LEASE_PEEK`] 에 남긴다(없으면 빈 문자열).
    peek: Option<&'static str>,
}

/// 회차 끝 임대 파일 판독(시험 전용 · `LeaseRound::peek`) — 병렬 시험이 함께 쓰므로 읽을 때는 [`peek_of`] 로 대화 id 를 골라 읽는다.
static LEASE_PEEK: std::sync::Mutex<Vec<String>> = std::sync::Mutex::new(Vec::new());

/// 그 대화의 마지막 회차 끝 판독(없으면 빈 문자열).
fn peek_of(sess: &str) -> String {
    LEASE_PEEK.lock().unwrap_or_else(|e| e.into_inner()).iter().rev().find(|l| l.contains(&format!("\"id\":\"{sess}\""))).cloned().unwrap_or_default()
}

/// 가짜 데몬 위에서 `run_restore_with` 를 회차마다 돈다(회차마다 새 프로세스 내 집합 = 다른 `cys restore` 실행과 같다).
/// HOME·소켓 = 임시 폴더(라이브 무접촉) · **노브는 켬으로 고정**(바깥 환경의 off 가 이 시험을 종전 경로로 바꾸지 않게 · codex 4R minor).
/// 반환 = 회차별 (기동 기록, rc).
fn lease_restore_rounds(saved: Value, rounds: Vec<LeaseRound>) -> Vec<(LeaseCalls, i32)> {
    use std::io::{BufRead, BufReader, Write};
    use std::sync::{Arc, Mutex};
    let _g = tests::ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    lease_forget_launches(); // 「기동 글 수락」 기록은 프로세스 전역 — 앞 시험의 좌석 번호 기록이 새지 않게
    let dir = std::path::PathBuf::from(format!("/tmp/slct-{}-{}", std::process::id(),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos() % 1_000_000_000));
    std::fs::create_dir_all(dir.join("home")).unwrap();
    let socket = dir.join("s.sock");
    let listener = std::os::unix::net::UnixListener::bind(&socket).expect("가짜 소켓 bind");
    let now: Arc<Mutex<(Value, Value)>> = Arc::new(Mutex::new((json!([]), json!([]))));
    let srv_now = now.clone();
    let server = std::thread::spawn(move || {
        for stream in listener.incoming() {
            let Ok(mut stream) = stream else { break };
            let mut line = String::new();
            if BufReader::new(&mut stream).read_line(&mut line).is_err() {
                continue;
            }
            let req: Value = serde_json::from_str(line.trim()).unwrap_or(Value::Null);
            let (live, surfaces) = srv_now.lock().unwrap().clone();
            let result = match req["method"].as_str().unwrap_or("") {
                "__stop" => break,
                "system.topology" => json!({"saved": saved, "tombstones": [], "live": live}),
                "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
                "system.resolve_role" => json!({"surface_id": 99}),
                "surface.list" => json!({"surfaces": surfaces}),
                _ => json!({}),
            };
            let _ = writeln!(stream, "{}", json!({"id": req["id"], "ok": true, "result": result}));
        }
    });
    let keys = ["CYS_SOCKET", "CYS_NO_AUTOSTART", "HOME", cys::session_lease::KNOB];
    let saved_env: Vec<_> = keys.into_iter().map(|k| (k, std::env::var_os(k))).collect();
    std::env::set_var("CYS_SOCKET", &socket);
    std::env::set_var("CYS_NO_AUTOSTART", "1");
    std::env::set_var("HOME", dir.join("home"));
    std::env::remove_var(cys::session_lease::KNOB);
    // run_restore_with 는 디버그 빌드에서 프레임이 크고, 임대 켬이면 관문·argv 훑기 프레임이 더 얹힌다 — 시험 스레드 기본 스택(2MB)을 넘어
    // 병렬 전체 실행에서 「stack overflow」로 시험 바이너리 전체가 죽었다(11-11 18:0x · 단일 스레드 = 주 스레드 8MB 에선 통과).
    // 운영은 주 스레드에서 돈다 → 시험 쪽만 넉넉한 스택의 스레드에서 돌린다.
    let out = std::thread::Builder::new()
        .stack_size(32 * 1024 * 1024)
        .spawn(move || {
            let mut out = Vec::new();
            for r in rounds {
                *now.lock().unwrap() = (r.live, r.surfaces);
                let mut rec = LeaseRec { calls: vec![], in_seat_unknown: r.in_seat_unknown, in_seat_err_after_send: r.in_seat_err_after_send,
                                         in_seat_err: r.in_seat_err, fresh_rc: r.fresh_rc };
                let rc = run_restore_with(None, false, r.no_resume, &mut rec);
                if let Some(sess) = r.peek {
                    let l = lease_store().ok().and_then(|st| std::fs::read_to_string(st.file_of(sess)).ok()).unwrap_or_default();
                    LEASE_PEEK.lock().unwrap_or_else(|e| e.into_inner()).push(l);
                }
                out.push((rec.calls, rc));
            }
            out
        })
        .unwrap()
        .join()
        .unwrap();
    let _ = std::os::unix::net::UnixStream::connect(&socket)
        .and_then(|mut s| writeln!(s, "{}", json!({"id": 0, "method": "__stop"})));
    let _ = server.join();
    for (k, v) in saved_env {
        match v { Some(v) => std::env::set_var(k, v), None => std::env::remove_var(k) }
    }
    let _ = std::fs::remove_dir_all(&dir);
    out
}

/// 종전 모양(회차마다 같은 답) — 결과 불명 뒤 좌석 52 에 에이전트가 보인다(떠 있을 수 있는 그 좌석).
fn lease_restore_runs(saved: Value, live: Value, runs: usize, in_seat_unknown: bool) -> Vec<(LeaseCalls, i32)> {
    let occ = json!([{"surface_id": 52, "pid": 1, "exited": false, "seat": "occupied", "agent_alive": true}]);
    lease_restore_rounds(saved, (0..runs).map(|_| LeaseRound { live: live.clone(), surfaces: occ.clone(), in_seat_unknown, ..Default::default() }).collect())
}

/// 결함 ⑪ — 좌석 내 재연결의 쓰기 결과가 불명이면 그 좌석이 대화를 이미 잇고 있을 수 있다. 같은 대화를 가리키는 두 번째 항목(같은 회차)도,
/// 다음 `cys restore`(다른 회차)도 그 대화를 다시 `--resume` 하면 안 된다.
#[test]
fn unknown_write_outcome_keeps_the_conversation_owned() {
    let saved = json!([
        {"role": "w-unk", "agent": "claude", "session_id": "s-dup", "cwd": "/tmp", "claude_config_dir": "/cfg"},
        {"role": "w-two", "agent": "claude", "session_id": "s-dup", "cwd": "/tmp", "claude_config_dir": "/cfg"},
    ]);
    let live = json!([{"role": "w-unk", "seat": "empty", "surface_id": 52, "env_injected": true, "session_id": null}]); // 데몬 계약: session_id 키 상존(1.1.9~)
    let runs = lease_restore_runs(saved, live, 2, true);
    let resumes: Vec<_> = runs.iter().flat_map(|r| &r.0).filter(|c| c.2 && c.3.as_deref() == Some("s-dup")).collect();
    assert_eq!(resumes.len(), 1, "결과 불명 뒤 같은 대화를 또 이었다: {runs:?}");
    assert_eq!(runs[1].1, EXIT_SESSION_WRITER_LIVE, "둘째 회차 = 좌석에 에이전트 보임 → 92: {runs:?}");
}

/// codex 4R blocking — 결과 불명(⑪) 임대: 좌석이 **비어 보여도**(exited=false · seat=empty · agent_alive=null · live 의 session_id 없음 · argv 증거 없음)
/// 큐의 기동 명령이 아직 닿을 수 있다 → 다시 잇지 않는다(93). 좌석이 사라진 뒤(확정 종료)에야 인수해 잇는다(rc 0).
/// 정상 첫 복원 rc 0 도 함께 고정(정상 조건 거짓 93 = 0).
#[test]
fn unknown_outcome_is_not_released_by_an_empty_looking_seat() {
    let saved = json!([{"role": "w-unk", "agent": "claude", "session_id": "s-unk2", "cwd": "/tmp", "claude_config_dir": "/cfg"}]);
    let seat_live = json!([{"role": "w-unk", "seat": "empty", "surface_id": 52, "env_injected": true, "session_id": null}]);
    let empty52 = json!([{"surface_id": 52, "pid": 1, "exited": false, "seat": "empty", "agent_alive": null}]);
    let runs = lease_restore_rounds(saved.clone(), vec![
        LeaseRound { live: seat_live.clone(), surfaces: empty52.clone(), in_seat_unknown: true, ..Default::default() },  // ① 좌석 재연결 · 쓰기 결과 불명
        LeaseRound { live: seat_live.clone(), surfaces: empty52.clone(), in_seat_unknown: false, ..Default::default() }, // ② 비어 보이는 같은 좌석
        LeaseRound { live: json!([]), surfaces: json!([]), in_seat_unknown: false, ..Default::default() },              // ③ 좌석 소멸(확정 종료)
    ]);
    let resumes = |r: &(LeaseCalls, i32)| r.0.iter().filter(|c| c.2 && c.3.as_deref() == Some("s-unk2")).count();
    assert_eq!(resumes(&runs[0]), 1, "① 시험 전제: 첫 회차가 이었다 {runs:?}");
    assert_eq!((resumes(&runs[1]), runs[1].1), (0, EXIT_SESSION_LIVENESS_UNKNOWN), "② 결과 불명을 빈 좌석 관측으로 풀었다: {runs:?}");
    assert_eq!((resumes(&runs[2]), runs[2].1), (1, 0), "③ 확정 종료 뒤 인수해 잇지 못했다: {runs:?}");
    // 정상 조건: 결과 불명 없는 첫 복원 = rc 0 · 잇는다.
    let ok = lease_restore_rounds(saved, vec![LeaseRound { live: json!([]), surfaces: json!([]), ..Default::default() }]);
    assert_eq!((resumes(&ok[0]), ok[0].1), (1, 0), "정상 첫 복원: {ok:?}");
}

/// 주입 표식(300초)과 임대 — master#2f22d811 조건: ① 임대를 잡은(인수) 회차는 같은 좌석의 신선한 표식을 지나간다
/// ② 임대 없는 겹침 주입은 여전히 막힌다(표식 본래 목적 = 한 좌석에 지침 두 번 방지).
fn with_tmp_state<T>(f: impl FnOnce(&std::path::Path) -> T) -> T {
    let _g = tests::ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let dir = std::path::PathBuf::from(format!("/tmp/slim-{}-{}", std::process::id(),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos() % 1_000_000_000));
    std::fs::create_dir_all(dir.join("home")).unwrap();
    let keys = ["CYS_SOCKET", "HOME", "CYS_NO_AUTOSTART", cys::session_lease::KNOB];
    let saved: Vec<_> = keys.into_iter().map(|k| (k, std::env::var_os(k))).collect();
    std::env::set_var("CYS_SOCKET", dir.join("s.sock"));
    std::env::set_var("HOME", dir.join("home"));
    std::env::set_var("CYS_NO_AUTOSTART", "1");
    std::env::remove_var(cys::session_lease::KNOB);
    let out = f(&dir);
    for (k, v) in saved {
        match v { Some(v) => std::env::set_var(k, v), None => std::env::remove_var(k) }
    }
    let _ = std::fs::remove_dir_all(&dir);
    out
}

#[test]
fn inject_mark_lets_the_lease_winner_through() {
    with_tmp_state(|_| {
        assert!(restore_inject_claim(71), "첫 표식");
        assert!(!restore_inject_claim(71), "표식 시험 전제: 300초 안 두 번째는 막힘");
        // 임대를 잡은 회차(이 프로세스가 가드를 쥠) — 데몬 없는 상자라 증거 조회 대신 leaf 를 가짜 세계로 직접 잡는다.
        struct W;
        impl cys::session_lease::World for W {
            fn holder(&self, _h: &cys::session_lease::Holder) -> cys::session_lease::Liveness { cys::session_lease::Liveness::Dead }
            fn seat(&self, _s: u64, _g: Option<&str>, _strict: bool) -> cys::session_lease::Liveness { cys::session_lease::Liveness::Dead }
            fn evidence(&self, _n: &str) -> cys::session_lease::Evidence { cys::session_lease::Evidence::NoneConfirmed }
            fn now(&self) -> u64 { 1 }
        }
        let store = lease_store().unwrap();
        let cx = cys::session_lease::AcquireCtx { me: cys::session_lease::me().unwrap(), surface_id: Some(71), daemon_gen: None, cfg: None, world: &W };
        let cys::session_lease::Decision::Granted(g) = cys::session_lease::acquire(&store, "sess-71", &cx) else { panic!("임대") };
        assert!(inject_claim_or_lease(71, Some("sess-71")), "임대를 잡은 회차가 신선한 표식에 막혔다");
        drop(g);
        assert!(!inject_claim_or_lease(71, Some("sess-71")), "임대를 놓은 뒤에도 표식을 지나갔다");
    });
}

#[test]
fn inject_mark_still_blocks_overlap_without_a_lease() {
    with_tmp_state(|_| {
        assert!(inject_claim_or_lease(72, Some("sess-72")), "첫 주입");
        assert!(!inject_claim_or_lease(72, Some("sess-72")), "임대 없는 겹침 주입을 막지 않았다");
        assert!(!inject_claim_or_lease(72, None), "대화 없는 겹침 주입을 막지 않았다");
    });
}

/// 응답을 고를 수 있는 가짜 데몬 위에서 `f` — HOME·소켓 = 임시 폴더(라이브 무접촉).
fn with_fake_daemon<T>(answer: impl Fn(&str) -> Value + Send + 'static, f: impl FnOnce(&std::path::Path) -> T) -> T {
    use std::io::{BufRead, BufReader, Write};
    let _g = tests::ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let dir = std::path::PathBuf::from(format!("/tmp/slfd-{}-{}", std::process::id(),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos() % 1_000_000_000));
    std::fs::create_dir_all(dir.join("home")).unwrap();
    let socket = dir.join("s.sock");
    let listener = std::os::unix::net::UnixListener::bind(&socket).expect("가짜 소켓 bind");
    let server = std::thread::spawn(move || {
        for stream in listener.incoming() {
            let Ok(mut stream) = stream else { break };
            let mut line = String::new();
            if BufReader::new(&mut stream).read_line(&mut line).is_err() {
                continue;
            }
            let req: Value = serde_json::from_str(line.trim()).unwrap_or(Value::Null);
            let m = req["method"].as_str().unwrap_or("").to_string();
            if m == "__stop" {
                break;
            }
            let _ = writeln!(stream, "{}", json!({"id": req["id"], "ok": true, "result": answer(&m)}));
        }
    });
    let keys = ["CYS_SOCKET", "CYS_NO_AUTOSTART", "HOME", cys::session_lease::KNOB];
    let saved_env: Vec<_> = keys.into_iter().map(|k| (k, std::env::var_os(k))).collect();
    std::env::set_var("CYS_SOCKET", &socket);
    std::env::set_var("CYS_NO_AUTOSTART", "1");
    std::env::set_var("HOME", dir.join("home"));
    std::env::remove_var(cys::session_lease::KNOB);
    let out = f(&dir);
    let _ = std::os::unix::net::UnixStream::connect(&socket)
        .and_then(|mut s| writeln!(s, "{}", json!({"id": 0, "method": "__stop"})));
    let _ = server.join();
    for (k, v) in saved_env {
        match v { Some(v) => std::env::set_var(k, v), None => std::env::remove_var(k) }
    }
    let _ = std::fs::remove_dir_all(&dir);
    out
}

/// codex 1R B1 — 데몬 응답의 live 가 배열이 아니면 「없음」이 아니라 판정 불가.
#[test]
fn malformed_topology_is_undecided_not_none() {
    use cys::session_lease::{Evidence, World};
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": [], "live": {"oops": 1}}),
            _ => json!({}),
        },
        |_| {
            let e = CliWorld::new().evidence("sess-b1");
            assert_eq!(e, Evidence::Undecided("daemon:malformed-topology".into()));
        },
    );
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": []}),
            _ => json!({}),
        },
        |_| assert!(matches!(CliWorld::new().evidence("sess-b1"), Evidence::Undecided(_)), "live 결측을 없음으로 쳤다"),
    );
}

/// codex 1R B3 — 세대가 다른 임대의 좌석: 그 데몬이 살아 있으면 판정 불가(93) · 죽음 확인·pid 재사용이면 죽음 · 판독 실패 = 판정 불가.
#[test]
fn other_generation_seat_is_dead_only_when_that_daemon_is() {
    use cys::process_observation::{Failure, Identity};
    use cys::session_lease::Liveness;
    let id = |birth: u64| Identity { pid: 4242, parent: 1, process_group: 4242, birth_seconds: birth, birth_microseconds: 0, pointer_width: 8, executable: vec![] };
    assert_eq!(other_gen_seat("4242-1000.25", 7, |_| Err(Failure::Dead)), Liveness::Dead);
    assert_eq!(other_gen_seat("4242-1000.25", 7, |_| Ok(id(999))), Liveness::Undecided("daemon:other-gen-alive:4242:7".into()));
    assert_eq!(other_gen_seat("4242-1000.25", 7, |_| Ok(id(1000))), Liveness::Undecided("daemon:other-gen-alive:4242:7".into()));
    assert_eq!(other_gen_seat("4242-1000.25", 7, |_| Ok(id(5000))), Liveness::Dead, "pid 재사용을 산 데몬으로 쳤다");
    assert!(matches!(other_gen_seat("4242-1000.25", 7, |_| Err(Failure::Unknown { stage: "x", os_error: Some(1) })), Liveness::Undecided(_)));
    assert!(matches!(other_gen_seat("garbage", 7, |_| Err(Failure::Dead)), Liveness::Undecided(_)), "형식 이상을 죽음으로 쳤다");
    // 다음 행동 줄은 그 데몬을 가리킨다.
    let next = cys::session_lease::next_action("daemon:other-gen-alive:4242:7", "abc", std::path::Path::new("/x/y.lease"));
    assert!(next.contains("pid 4242") && next.contains("surface:7"), "{next}");
}

/// B3 운영 세계 — 살아 있는 다른 데몬(여기선 이 시험 프로세스 자신을 그 데몬으로 둔다)의 임대 좌석은 지금 데몬에서 「없음」이어도 죽음이 아니다.
#[test]
fn cli_world_seat_does_not_kill_a_live_foreign_daemons_seat() {
    use cys::session_lease::{Liveness, World};
    let me = cys::process_observation::identity(std::process::id()).unwrap();
    let foreign = format!("{}-{}.0", me.pid, me.birth_seconds + 1);
    with_fake_daemon(
        |m| match m {
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            "surface.list" => json!({"surfaces": []}),
            _ => json!({}),
        },
        move |_| {
            let w = CliWorld::new();
            assert!(matches!(w.seat(1, Some(&foreign), false), Liveness::Undecided(r) if r.starts_with("daemon:other-gen-alive")));
            // 같은 세대면 종전대로 이 데몬의 좌석 목록으로 판정(없음 = 죽음).
            assert_eq!(w.seat(1, Some("77-1.5"), false), Liveness::Dead);
        },
    );
}

/// master#388727f0 M3 = B — 옛 판 복원기의 60초 안 claim 동률은 restore 만이 아니라 공통 관문(lease_gate)에서 본다
/// → --resume-saved · node-recover 도 같은 거절(92). 임대를 아는 판의 claim(`L`)·60초 지난 claim 은 임대 판정으로 넘어간다.
#[test]
fn old_version_claim_tie_is_honoured_at_the_shared_gate() {
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": [], "live": []}),
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            _ => json!({}),
        },
        |dir| {
            let claims = dir.join("claims");
            std::fs::create_dir_all(&claims).unwrap();
            let id = "sess-m3-tie";
            let file = claims.join(restore_claim_file_name(id));
            let now = restore_now_secs();
            std::fs::write(&file, format!("123-456-0 {now} 9-1.5\n")).unwrap();
            match lease_gate("w-m3", Some(id), None, None, Some(&claims)) {
                LeaseGate::Refuse { rc, line } => {
                    assert_eq!(rc, EXIT_SESSION_WRITER_LIVE);
                    assert!(line.contains("옛 판 복원기"), "{line}");
                }
                _ => panic!("60초 안 옛 claim 을 공통 관문이 지나갔다"),
            }
            // 임대를 아는 판의 claim = 동률 아님 → 임대 판정(여기선 비어 있음 = 진행).
            std::fs::write(&file, format!("L123-456-0 {now} 9-1.5\n")).unwrap();
            assert!(matches!(lease_gate("w-m3", Some(id), None, None, Some(&claims)), LeaseGate::Proceed(Some(_))), "L claim 을 동률로 쳤다");
            // 60초 지난 옛 claim = 동률 아님.
            std::fs::write(&file, format!("123-456-0 {} 9-1.5\n", now - 61)).unwrap();
            assert!(matches!(lease_gate("w-m3", Some(id), None, None, Some(&claims)), LeaseGate::Proceed(Some(_))), "낡은 claim 을 동률로 쳤다");
        },
    );
}

/// codex 1R M4 → 2R blocking 으로 **고치지 않음**: 다른 대화 임대의 작성자로 적힌 프로세스라도 argv 에 이 대화가 있으면 증거로 남는다
/// (좌석 안 /resume 으로 돌아왔는데 등록이 아직 안 닿은 순간과 가를 수 없음 → 안전 쪽 = 92 거짓 막힘). 실제 자식 프로세스로 잰다.
#[test]
fn stale_argv_stays_evidence_even_if_recorded_as_writing_elsewhere() {
    use cys::session_lease::{self as sl, Evidence, Lease, State, World};
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": [], "live": []}),
            _ => json!({}),
        },
        |_| {
            let mut child = cys::hidden_command("/bin/sh")
                .args(["-c", "sleep 30; true", "sess-m4-a"])
                .spawn()
                .unwrap();
            std::thread::sleep(std::time::Duration::from_millis(200));
            let w = CliWorld::new();
            assert!(matches!(w.evidence("sess-m4-a"), Evidence::Seen(_)), "시험 전제: 자식 argv 가 증거로 보여야 함");
            let id = cys::process_observation::identity(child.id()).unwrap();
            let store = lease_store().unwrap();
            let l = Lease { v: sl::LEASE_VERSION, id: "sess-m4-b".into(), fence: 1, token: "t".into(), state: State::Held,
                writer: Some(sl::holder_of(&id)), restorer: None, surface_id: Some(3), daemon_gen: None, cfg: None, at: 1, launch_sent: false };
            std::fs::write(store.file_of("sess-m4-b"), serde_json::to_string(&l).unwrap()).unwrap();
            assert!(matches!(w.evidence("sess-m4-a"), Evidence::Seen(_)), "다른 대화 작성자 기록으로 argv 증거를 지웠다(작성자 둘의 창)");
            let _ = child.kill();
            let _ = child.wait();
        },
    );
}

/// codex 2R B3 — 세대 기록 없는 임대의 좌석 · 번호 없는 좌석 원소 · 형식이 틀린 live 원소 = 판정 불가(죽음·없음으로 단정 안 함).
#[test]
fn missing_generation_and_malformed_elements_are_undecided() {
    use cys::session_lease::{Evidence, Liveness, World};
    with_fake_daemon(
        |m| match m {
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            "surface.list" => json!({"surfaces": [{"surface_id": 1}, {"oops": true}]}),
            "system.topology" => json!({"saved": [], "live": [{"surface_id": 1, "seat": "occupied", "session_id": 5}]}),
            _ => json!({}),
        },
        |_| {
            let w = CliWorld::new();
            assert_eq!(w.seat(9, None, false), Liveness::Undecided("daemon:gen-unknown:9".into()), "세대 없는 임대를 지금 데몬 목록으로 판정했다");
            assert_eq!(w.seat(9, Some("77-1.5"), false), Liveness::Undecided("daemon:malformed-surface-list".into()), "번호 없는 원소를 무시하고 죽음으로 봤다");
            assert_eq!(w.evidence("x"), Evidence::Undecided("daemon:malformed-topology".into()), "session_id 형식 이상을 없음으로 쳤다");
        },
    );
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": [], "live": ["not-an-object"]}),
            _ => json!({}),
        },
        |_| assert!(matches!(CliWorld::new().evidence("x"), Evidence::Undecided(_))),
    );
}

/// codex 2R M3 — 죽은 보유자의 임대 파일이 있어도 60초 안 옛 claim 은 동률(옛 판은 임대를 모름) · claim 판독 오류(FIFO 포함) = 93 · 멈추지 않음.
#[test]
fn old_claim_tie_holds_over_an_existing_lease_and_claim_errors_are_undecided() {
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": [], "live": []}),
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            _ => json!({}),
        },
        |dir| {
            let claims = dir.join("claims");
            std::fs::create_dir_all(&claims).unwrap();
            let id = "sess-m3-dead";
            // 죽은 작성자의 임대(없는 pid) — 옛 규칙은 「임대 있음 = claim 안 봄」이었다.
            let store = lease_store().unwrap();
            let dead = cys::session_lease::Holder { pid: 0x7fff_fff0, birth_s: 1, birth_us: 0 };
            let l = cys::session_lease::Lease { v: cys::session_lease::LEASE_VERSION, id: id.into(), fence: 3, token: "t".into(),
                state: cys::session_lease::State::Held, writer: Some(dead), restorer: None, surface_id: None, daemon_gen: None, cfg: None, at: 1, launch_sent: false };
            std::fs::write(store.file_of(id), serde_json::to_string(&l).unwrap()).unwrap();
            std::fs::write(claims.join(restore_claim_file_name(id)), format!("123-456-0 {} 9-1.5\n", restore_now_secs())).unwrap();
            assert!(matches!(lease_gate("w", Some(id), None, None, Some(&claims)), LeaseGate::Refuse { rc: EXIT_SESSION_WRITER_LIVE, .. }),
                    "임대 파일이 있다고 옛 판의 신선한 claim 을 건너뛰었다");
            // claim 자리에 FIFO = 판정 불가 · 곧장.
            let f = claims.join(restore_claim_file_name("sess-m3-fifo"));
            let c = std::ffi::CString::new(f.to_str().unwrap()).unwrap();
            assert_eq!(unsafe { libc::mkfifo(c.as_ptr(), 0o600) }, 0);
            let t0 = std::time::Instant::now();
            assert!(matches!(lease_gate("w", Some("sess-m3-fifo"), None, None, Some(&claims)), LeaseGate::Refuse { rc: EXIT_SESSION_LIVENESS_UNKNOWN, .. }));
            assert!(t0.elapsed() < std::time::Duration::from_secs(2), "claim FIFO 에서 멈췄다");
        },
    );
}

/// codex 2R major — 기동 전 좌석 기록을 못 하면 Err(`session_lease:` → launch-agent rc 93 · 기동 0). 노브 끔·임대 없음은 할 일 없음.
#[test]
fn seat_note_failure_stops_the_launch() {
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": [], "live": []}),
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            _ => json!({}),
        },
        |_| {
            assert!(lease_note_surface(Some("sess-note-none"), 5).is_ok(), "임대 없는 갈래");
            let LeaseGate::Proceed(Some(g)) = lease_gate("w", Some("sess-note"), None, None, None) else { panic!("임대") };
            assert!(lease_note_surface(Some("sess-note"), 5).is_ok());
            // 그 사이 임대가 넘어감(디스크의 token 이 바뀜) → 좌석 기록 실패 = 기동 중단.
            let store = lease_store().unwrap();
            let f = store.file_of("sess-note");
            let mut v: Value = serde_json::from_str(&std::fs::read_to_string(&f).unwrap()).unwrap();
            v["token"] = json!("someone-else");
            std::fs::write(&f, v.to_string()).unwrap();
            let e = lease_note_surface(Some("sess-note"), 6).unwrap_err();
            assert!(e.starts_with("session_lease:"), "{e}");
            assert!(lease_resume_unheld(Some("sess-note")).is_some(), "넘어간 임대로 --resume 을 허락했다");
            drop(g);
        },
    );
}

/// codex 3R — 판정 필드 계약 위반(빈 객체 · seat 낱말 밖 · session_id 키 없음 · agent_alive 형식 · exited 형식) = 판정 불가 · 정상 응답 = 통과.
#[test]
fn daemon_entry_contract_is_checked_field_by_field() {
    use cys::session_lease::{Evidence, Liveness, World};
    assert!(live_entry_ok(&json!({"role": "r", "surface_id": 1, "seat": "occupied", "session_id": null})));
    assert!(live_entry_ok(&json!({"role": "r", "surface_id": 1, "seat": "empty", "session_id": "abc"})));
    for bad in [json!({}), json!({"surface_id": 1, "seat": "occupied"}), json!({"surface_id": 1, "seat": "busy", "session_id": null}),
                json!({"surface_id": "1", "seat": "occupied", "session_id": null})] {
        assert!(!live_entry_ok(&bad), "{bad}");
    }
    assert!(list_entry_ok(&json!({"surface_id": 1, "exited": false, "seat": "empty", "agent_alive": null})));
    for bad in [json!({"surface_id": 1, "exited": false, "seat": "empty", "agent_alive": "true"}),
                json!({"surface_id": 1, "exited": "no", "seat": "empty", "agent_alive": false}),
                json!({"surface_id": 1, "exited": false, "seat": "empty"})] {
        assert!(!list_entry_ok(&bad), "{bad}");
    }
    with_fake_daemon(
        |m| match m {
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            "surface.list" => json!({"surfaces": [{"surface_id": 4, "exited": false, "seat": "empty", "agent_alive": "true"}]}),
            "system.topology" => json!({"saved": [], "live": [{}]}),
            _ => json!({}),
        },
        |_| {
            let w = CliWorld::new();
            assert_eq!(w.seat(4, Some("77-1.5"), false), Liveness::Undecided("daemon:malformed-surface-list".into()), "손상 원소를 빈 좌석(죽음)으로 쳤다");
            assert_eq!(w.evidence("x"), Evidence::Undecided("daemon:malformed-topology".into()), "빈 객체를 통과시켰다");
        },
    );
}

/// codex 5R(ESCALATE) — 기동 중(launching) 임대의 복원기가 기동 명령을 친 뒤 결과를 적기 전에 급사한 모양:
/// 작성자 없음 · 좌석 적힘 · 복원기 죽음 · 좌석은 빈 셸(에이전트 exec 전) → 넘기지 않는다(93 · 좌석 확인 다음 행동). 좌석 소멸 뒤엔 넘긴다.
#[test]
fn crashed_restorer_launching_lease_is_not_released_by_an_empty_looking_seat() {
    use cys::session_lease::{self as sl, Holder, Lease, State};
    let surfaces = std::sync::Arc::new(std::sync::Mutex::new(json!([{"surface_id": 61, "pid": 1, "exited": false, "seat": "empty", "agent_alive": null}])));
    let s2 = surfaces.clone();
    with_fake_daemon(
        move |m| match m {
            "system.topology" => json!({"saved": [], "live": []}),
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            "surface.list" => json!({"surfaces": s2.lock().unwrap().clone()}),
            _ => json!({}),
        },
        |_| {
            let store = lease_store().unwrap();
            let l = Lease { v: sl::LEASE_VERSION, id: "sess-crash".into(), fence: 1, token: "t".into(), state: State::Launching, writer: None,
                restorer: Some(Holder { pid: 0x7fff_fff0, birth_s: 1, birth_us: 0 }), surface_id: Some(61), daemon_gen: Some("77-1.5".into()), cfg: None, at: 1, launch_sent: false };
            std::fs::write(store.file_of("sess-crash"), serde_json::to_string(&l).unwrap()).unwrap();
            match lease_gate("w", Some("sess-crash"), None, None, None) {
                LeaseGate::Refuse { rc, line } => {
                    assert_eq!(rc, EXIT_SESSION_LIVENESS_UNKNOWN, "{line}");
                    assert!(line.contains("seat-empty-unconfirmed") && line.contains("surface:61"), "{line}");
                }
                _ => panic!("급사한 복원기의 기동 중 임대를 빈 셸 관측으로 넘겼다"),
            }
            *surfaces.lock().unwrap() = json!([]); // 좌석 소멸 = 확정 종료
            assert!(matches!(lease_gate("w", Some("sess-crash"), None, None, None), LeaseGate::Proceed(Some(_))), "좌석 소멸 뒤에도 못 넘겼다");
        },
    );
}

/// master#ae3bad7d 재발 방지 — 시험이 실제 HOME 에서 임대 폴더를 열려 하면 디스크를 건드리기 전에 실패한다(가드 자신의 시험).
/// 실제 홈은 `CYS_TEST_REAL_HOME` 으로 임시 폴더를 흉내 낸다(뮤턴트가 가드를 지워도 실제 홈은 안 건드림).
#[test]
fn lease_tests_refuse_to_run_against_the_real_home() {
    let _g = tests::ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let dir = std::path::PathBuf::from(format!("/tmp/slg-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let keys = ["HOME", "CYS_TEST_REAL_HOME", cys::session_lease::KNOB];
    let saved: Vec<_> = keys.into_iter().map(|k| (k, std::env::var_os(k))).collect();
    std::env::set_var("HOME", &dir);
    std::env::set_var("CYS_TEST_REAL_HOME", &dir);
    std::env::remove_var(cys::session_lease::KNOB);
    let r = std::panic::catch_unwind(|| lease_store().is_ok());
    let created = dir.join(".local/state/cys/session-leases").exists();
    // 다른 HOME 이면 통과.
    std::env::set_var("CYS_TEST_REAL_HOME", "/nonexistent-real-home");
    let other = std::panic::catch_unwind(|| lease_store().is_ok());
    for (k, v) in saved {
        match v { Some(v) => std::env::set_var(k, v), None => std::env::remove_var(k) }
    }
    let _ = std::fs::remove_dir_all(&dir);
    assert!(r.is_err(), "실제 HOME 에서 임대 폴더를 열었다(가드 없음)");
    assert!(!created, "가드가 디스크를 건드린 뒤에 실패했다");
    assert!(matches!(other, Ok(true)), "격리된 HOME 에서 가드가 막았다");
    // 순수 판정: 실제 홈을 모르면 실패(안전 쪽).
    assert!(test_home_guard(std::path::Path::new("/x"), None).is_some());
    assert!(test_home_guard(std::path::Path::new("/x"), Some(std::path::Path::new("/y"))).is_none());
}

/// codex 6R blocking — 기동 명령을 보낸 뒤의 **일반** 오류(set_meta·read_text 등)는 「안 떴다」가 아니다:
/// 좌석 재연결 갈래가 fresh 로 폴백하지 않고(같은 대화 둘째 작성자 차단) 임대를 유지(rc 91) · 다음 복원은 빈 셸이어도 잇지 않는다(93) · 좌석 소멸 뒤 인수.
#[test]
fn generic_error_after_the_launch_command_keeps_the_lease() {
    let saved = json!([{"role": "w-gen", "agent": "claude", "session_id": "s-gen", "cwd": "/tmp", "claude_config_dir": "/cfg"}]);
    let seat_live = json!([{"role": "w-gen", "seat": "empty", "surface_id": 53, "env_injected": true, "session_id": null}]);
    let empty53 = json!([{"surface_id": 53, "pid": 1, "exited": false, "seat": "empty", "agent_alive": null}]);
    let runs = lease_restore_rounds(saved, vec![
        LeaseRound { live: seat_live.clone(), surfaces: empty53.clone(), in_seat_err_after_send: true, ..Default::default() },
        LeaseRound { live: seat_live.clone(), surfaces: empty53.clone(), ..Default::default() },
        LeaseRound { live: json!([]), surfaces: json!([]), ..Default::default() },
    ]);
    let kinds = |r: &(LeaseCalls, i32)| r.0.iter().map(|c| (c.1, c.2)).collect::<Vec<_>>();
    assert_eq!(kinds(&runs[0]), vec![("in-seat", true)], "① 기동 명령 뒤 일반 오류에서 fresh 로 폴백했다: {runs:?}");
    assert_eq!(runs[0].1, EXIT_WRITE_OUTCOME_UNKNOWN, "① 결과 불명 rc: {runs:?}");
    assert!(kinds(&runs[1]).is_empty() && runs[1].1 == EXIT_SESSION_LIVENESS_UNKNOWN, "② 빈 셸 관측으로 다시 이었다: {runs:?}");
    assert_eq!((kinds(&runs[2]), runs[2].1), (vec![("fresh", true)], 0), "③ 좌석 소멸 뒤 인수: {runs:?}");
}

/// codex 6R major — `--no-resume` 복원은 저장 대화의 임대를 잡지 않는다 · 접미 없이(새 대화로) 뜬 기동은 마무리에서 임대를 되돌린다.
#[test]
fn a_launch_that_does_not_resume_never_keeps_the_saved_conversations_lease() {
    let saved = json!([{"role": "w-nr", "agent": "claude", "session_id": "s-nr", "cwd": "/tmp", "claude_config_dir": "/cfg"}]);
    let runs = lease_restore_rounds(saved, vec![
        LeaseRound { live: json!([]), surfaces: json!([]), no_resume: true, ..Default::default() },
        LeaseRound { live: json!([]), surfaces: json!([]), ..Default::default() }, // 그 뒤 정상 복원 = 잇는다(거짓 93 없음)
    ]);
    assert_eq!(runs[0].0.iter().map(|c| c.2).collect::<Vec<_>>(), vec![false], "① --no-resume: {runs:?}");
    assert_eq!(runs[1].0.iter().map(|c| (c.2, c.3.as_deref())).collect::<Vec<_>>(), vec![(true, Some("s-nr"))], "② 뒤 정상 복원: {runs:?}");
    assert_eq!(runs[1].1, 0, "② 거짓 93/92: {runs:?}");
    // 접미 없이 뜬 기동의 마무리 = 되돌림.
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": [], "live": []}),
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            _ => json!({}),
        },
        |_| {
            let LeaseGate::Proceed(Some(g)) = lease_gate("w", Some("sess-nosfx"), None, None, None) else { panic!("임대") };
            let f = lease_store().unwrap().file_of("sess-nosfx");
            assert!(f.exists());
            lease_note_launch(4711, false);
            lease_finish_ready(Some(g), Some(4711), Some("sess-nosfx"));
            assert!(!f.exists(), "새 대화로 뜬 기동이 저장 대화의 임대를 쥐고 남았다");
        },
    );
}

/// 독립 검증 F3(M25) — node-recover: 기동 명령을 보낸 뒤 일반 오류 = 임대 유지(결과 불명) · 보내기 전 오류 = 되돌림.
#[test]
fn node_recover_keeps_the_lease_after_a_generic_error_past_the_launch_command() {
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": [], "live": []}),
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            _ => json!({}),
        },
        |_| {
            let store = lease_store().unwrap();
            // ① 기동 명령을 보낸 좌석(88)에서 일반 오류.
            let LeaseGate::Proceed(Some(g)) = lease_gate("w", Some("sess-nr1"), Some(88), None, None) else { panic!("임대") };
            lease_note_launch(88, true);
            lease_settle_boot(&Err("surface.set_meta: boom".into()), Some(88), Some(g), Some("sess-nr1"));
            let l = std::fs::read_to_string(store.file_of("sess-nr1")).expect("기동 명령 뒤 일반 오류에서 임대를 되돌렸다(M25)");
            assert!(l.contains("\"state\":\"unknown\""), "결과 불명으로 남지 않았다: {l}");
            // ② 기동 명령 전(그 좌석에 기록 없음)의 일반 오류 = 되돌림.
            let LeaseGate::Proceed(Some(g)) = lease_gate("w", Some("sess-nr2"), Some(89), None, None) else { panic!("임대") };
            lease_settle_boot(&Err("spec: boom".into()), Some(89), Some(g), Some("sess-nr2"));
            assert!(!store.file_of("sess-nr2").exists(), "기동 전 오류인데 임대가 남았다");
        },
    );
    // 배선 핀: node-recover 가 이 마무리를 부른다(호출 자리를 끄는 변이도 붉게).
    let src = include_str!("bin/cys.rs");
    let nr = &src[src.find("fn run_node_recover").expect("node-recover 본체")..];
    let nr = &nr[..nr.find("\n}\n").unwrap()];
    // 주석 처리된 호출이 통과하지 않게 줄 머리(공백 뒤 곧바로 호출)까지 본다(독립 재검 m4).
    assert!(nr.lines().any(|l| l.trim_start() == "lease_settle_boot(&result, seat.as_ref().map(|s| s.0), lease_g.take(), lease_sess.as_deref());"),
            "node-recover 가 기동 결과 임대 마무리를 거치지 않는다");
    // 기동 명령 글이 받아들여진 뒤에 「보냄」을 적는다(거절 = 0바이트 = 기동 전 · 독립 재검 m10).
    let boot = &src[src.find("fn boot_agent_on_surface(").unwrap()..];
    let paste = boot.find("authoritative_paste_settled(").unwrap();
    let note = boot.lines().position(|l| l.trim_start() == "lease_note_launch(sid, effective_resume);").map(|_| boot.find("    lease_note_launch(sid, effective_resume);").unwrap()).expect("기동 명령 송신 기록 자리");
    assert!(paste < note && note < boot.find("\"key\": \"Return\"").unwrap(), "송신 기록이 기동 글 수락 뒤 · Return 앞이 아니다");
}

/// 독립 검증 F3(M26) — launch-agent: 임대를 쥐고 기동 명령을 보낸 뒤 좌석을 못 닫음 = rc 91(임대 유지) · 그 밖 = 종전(1).
#[test]
fn launch_agent_close_failure_after_the_launch_command_keeps_the_lease() {
    assert_eq!(close_failure_rc(true, true), Some(EXIT_WRITE_OUTCOME_UNKNOWN));
    assert_eq!(close_failure_rc(true, false), None, "좌석을 닫았으면 작성자도 내려감 = 되돌림");
    assert_eq!(close_failure_rc(false, true), None, "임대 없음·기동 전 = 종전");
    let src = include_str!("bin/cys.rs");
    let la = &src[src.find("fn run_launch_agent_opts(").unwrap()..];
    let la = &la[..la.find("\n}\n").unwrap()];
    let arm = &la[la.find("let mut close_failed = false;").expect("닫기 실패 기록 자리")..];
    // close_failed = true 는 surface.close 의 Err 갈래 안에만(Ok 갈래로 옮기는 변이를 붉게 · 독립 재검 m4).
    let err_arm = &arm[arm.find("Err(e) => {").expect("닫기 Err 갈래")..];
    let ok_arm = &arm[..arm.find("Err(e) => {").unwrap()];
    assert!(err_arm[..err_arm.find("\n                    }").unwrap()].contains("close_failed = true;"), "닫기 실패를 Err 갈래에서 기록하지 않는다");
    assert!(!ok_arm.contains("close_failed = true;"), "닫기 성공을 실패로 기록한다");
    let gate = &arm[arm.find("if let Some(rc) = close_failure_rc(lease_sent, close_failed) {").expect("닫기 실패 rc 판정을 거치지 않는다")..];
    let gate = &gate[..gate.find("\n            }\n").unwrap()];
    assert!(gate.lines().any(|l| l.trim_start() == "return (rc, created);"), "닫기 실패 rc 를 돌려주지 않는다(임대 되돌림)");
    assert!(la.contains("let lease_sent = created.is_some_and(lease_launch_sent) && lease_mine(session_id.as_deref());"), "기동 명령 송신·임대 보유 판정");
}

/// codex 1R C1·C2 — 기동 오류 뒤 임대 처분은 그 좌석의 「기동 글 수락」 기록을 따른다(node-recover · launch-agent 90/91 · 복원 fresh 90/91 공용).
/// 거짓 93 쪽: 새 대화 기동(C1) · 기동 글 0바이트 거절(C2) = 되돌림. 작성자 둘 쪽: 잇는 기동 글 수락 뒤 = 유지 · 기록 없는 쓰기 결과 불명 = 유지.
#[test]
fn launch_error_disposal_follows_the_seats_launch_record() {
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": [], "live": []}),
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            _ => json!({}),
        },
        |_| {
            lease_forget_launches();
            let store = lease_store().unwrap();
            let take = |sess: &str, seat: u64| {
                let LeaseGate::Proceed(Some(g)) = lease_gate("w", Some(sess), Some(seat), None, None) else { panic!("임대 {sess}") };
                g
            };
            let kept = |sess: &str| std::fs::read_to_string(store.file_of(sess)).map(|l| l.contains("\"state\":\"unknown\"")).unwrap_or(false);
            let gone = |sess: &str| !store.file_of(sess).exists();
            let (journal, unknown, generic) = (injected_err("journal"), injected_err("unknown"), injected_err("generic"));
            // node-recover 마무리(lease_settle_boot).
            lease_note_launch(301, false);
            lease_settle_boot(&Err(unknown.clone()), Some(301), Some(take("sess-c1a", 301)), Some("sess-c1a"));
            assert!(gone("sess-c1a"), "C1: 새 대화 기동 + 쓰기 결과 불명인데 저장 대화 임대가 남았다(다음 복원 거짓 93)");
            lease_note_launch(302, false);
            lease_settle_boot(&Err(generic.clone()), Some(302), Some(take("sess-c1b", 302)), Some("sess-c1b"));
            assert!(gone("sess-c1b"), "C1: 새 대화 기동 + 일반 오류인데 임대가 남았다");
            assert!(!lease_launch_sent(302), "C1: 새 대화 기동을 「잇는 기동 보냄」으로 셌다(launch-agent 닫기 실패 91 의 입력)");
            lease_settle_boot(&Err(journal.clone()), Some(303), Some(take("sess-c2a", 303)), Some("sess-c2a"));
            assert!(gone("sess-c2a"), "C2: 기동 글 0바이트 거절(기동 전)인데 임대가 남았다");
            lease_note_launch(304, true);
            lease_settle_boot(&Err(journal.clone()), Some(304), Some(take("sess-c2b", 304)), Some("sess-c2b"));
            assert!(kept("sess-c2b"), "잇는 기동 글 수락 뒤 주입 거절 = 에이전트가 대화를 잇는 중 — 임대를 풀었다(작성자 둘)");
            lease_settle_boot(&Err(unknown.clone()), Some(305), Some(take("sess-c2c", 305)), Some("sess-c2c"));
            assert!(kept("sess-c2c"), "기동 글 자체의 쓰기 결과 불명 = 아직 쳐질 수 있다 — 임대를 풀었다(작성자 둘)");
            // rc 로 끝나는 기동(launch-agent · 복원 fresh)의 90·91.
            lease_settle_kept_rc(take("sess-k1", 306), EXIT_DIRECTIVE_REFUSED, Some(306));
            assert!(gone("sess-k1"), "C2: rc 90 · 기동 글 거절(기록 없음)인데 임대가 남았다");
            lease_note_launch(309, true);
            lease_settle_kept_rc(take("sess-k5", 309), EXIT_DIRECTIVE_REFUSED, Some(309));
            assert!(kept("sess-k5"), "rc 90 · 잇는 기동 뒤 지침 거절 = 유지여야 한다");
            lease_settle_kept_rc(take("sess-k2", 310), EXIT_DIRECTIVE_REFUSED, None);
            assert!(kept("sess-k2"), "좌석을 못 찾은 rc 90 = 대조 불가 = 유지(보수)");
            lease_note_launch(307, false);
            lease_settle_kept_rc(take("sess-k3", 307), EXIT_WRITE_OUTCOME_UNKNOWN, Some(307));
            assert!(gone("sess-k3"), "C1: rc 91 · 새 대화 기동인데 임대가 남았다");
            lease_settle_kept_rc(take("sess-k4", 308), EXIT_WRITE_OUTCOME_UNKNOWN, Some(308));
            assert!(kept("sess-k4"), "rc 91 · 기록 없는 쓰기 결과 불명 = 유지여야 한다");
        },
    );
    // 배선 핀: 네 마무리 자리가 이 처분을 거친다(종전 무조건 유지로 되돌리는 변이를 붉게).
    let src = include_str!("bin/cys.rs");
    for pin in [
        "if let Some(g) = lease_g.take() { lease_settle_after_error(g, Some(sid), false) }",
        "if let Some(g) = lease_g.take() { lease_settle_after_error(g, Some(sid), true) }",
        "lease_settle_kept_rc(g, rc, made); // ⑪·codex 1R C1·C2",
        "lease_finish_ready(lease_g.take(), made, sess.as_deref()); // 좌석 = 이 기동이 만든 좌석(codex 2R #2)",
        "lease_finish_by_rc(lease_g, rc, made, &sid); // 좌석 = 이 기동이 만든 좌석(역할 이름 조회 아님 · codex 2R #2)",
    ] {
        assert_eq!(src.matches(pin).count(), 1, "복원 루프 처분 배선: {pin}");
    }
    let cli = include_str!("session_lease_cli.rs");
    let by_rc = &cli[cli.find("pub(crate) fn lease_finish_by_rc(").unwrap()..];
    let by_rc = &by_rc[..by_rc.find("\n}\n").unwrap()];
    assert!(by_rc.lines().any(|l| l.trim_start().starts_with("lease_settle_kept_rc(g, rc, seat);")), "launch-agent 90·91 처분 배선");
    assert!(by_rc.lines().any(|l| l.trim_start() == "lease_finish_ready(Some(g), seat, Some(sess));"), "launch-agent 0·78 마무리 배선");
    // 좌석 = 그 기동이 만든 좌석(역할 이름 조회는 worker → worker-N 이름 바꿈에서 남의 좌석을 가리킨다 · codex 2R #2) — 이름 조회·전역 기록 0.
    assert!(!code_only(by_rc).contains("system.resolve_role"), "launch-agent 임대 마무리가 역할 이름으로 좌석을 찾는다");
    assert!(!code_only(cli).contains("CREATED"), "프로세스 전역 「만든 좌석」 기록이 남았다");
    let la = &src[src.find("fn run_launch_agent_opts(").unwrap()..];
    let la = &la[..la.find("\n}\n").unwrap()];
    assert!(la.trim_end().ends_with("(rc, seat_out)") && la.contains("        _ => created,\n    };"), "run_launch_agent_opts 가 만든 좌석을 돌려주지 않는다");
}

/// codex 1R C1·C2 — 복원 루프 왕복: 좌석 재연결의 「기동 글 0바이트 거절」·「새 대화 기동 + 결과 불명」 뒤 다음 복원은 같은 좌석으로 다시 잇는다(거짓 93 0) ·
/// 「잇는 기동 글 수락 뒤 지침 거절」 뒤 다음 복원은 잇지 않는다(작성자 둘 0) · fresh rc 90 도 같은 두 갈래.
#[test]
fn launch_record_decides_the_next_restore_both_ways() {
    let saved = json!([{"role": "w-c12", "agent": "claude", "session_id": "s-c12", "cwd": "/tmp", "claude_config_dir": "/cfg"}]);
    let seat_live = json!([{"role": "w-c12", "seat": "empty", "surface_id": 61, "env_injected": true, "session_id": null}]);
    let empty61 = json!([{"surface_id": 61, "pid": 1, "exited": false, "seat": "empty", "agent_alive": null}]);
    let two = |first: LeaseRound| lease_restore_rounds(saved.clone(), vec![first, LeaseRound { live: seat_live.clone(), surfaces: empty61.clone(), ..Default::default() }]);
    let kinds = |r: &(LeaseCalls, i32)| r.0.iter().map(|c| (c.1, c.2)).collect::<Vec<_>>();
    // C2: 기동 글 0바이트 거절(기록 없음) → 다음 복원 = 같은 좌석 재연결 · rc 0.
    let r = two(LeaseRound { live: seat_live.clone(), surfaces: empty61.clone(), in_seat_err: Some((None, "journal")), ..Default::default() });
    assert_eq!((kinds(&r[1]), r[1].1), (vec![("in-seat", true)], 0), "C2: 기동 전 거절 뒤 거짓 93: {r:?}");
    // C1: 새 대화 기동 + 쓰기 결과 불명 → 다음 복원 = 다시 잇는다 · rc 0.
    let r = two(LeaseRound { live: seat_live.clone(), surfaces: empty61.clone(), in_seat_err: Some((Some(false), "unknown")), ..Default::default() });
    assert_eq!((kinds(&r[1]), r[1].1), (vec![("in-seat", true)], 0), "C1: 새 대화 기동 뒤 거짓 93: {r:?}");
    // 작성자 둘 0: 잇는 기동 글 수락 뒤 지침 거절 → 다음 복원 = 잇지 않음(빈 셸로 보여도 93).
    let r = two(LeaseRound { live: seat_live.clone(), surfaces: empty61.clone(), in_seat_err: Some((Some(true), "journal")), ..Default::default() });
    assert_eq!((kinds(&r[1]), r[1].1), (vec![], EXIT_SESSION_LIVENESS_UNKNOWN), "잇는 기동 뒤 거절에서 다시 이었다(작성자 둘): {r:?}");
    // fresh rc 90: 기록 없음(기동 글 거절) → 다음 복원 = 좌석 98 재연결 · 잇는 기동 뒤 거절 → 93.
    // 좌석 98 = 그 기동이 만든 좌석 · 가짜 데몬의 역할 이름 조회는 99(이름 바꿈으로 남의 좌석)를 답한다 — 이름으로 찾으면 둘째 칸이 붉다.
    let live99 = json!([{"role": "w-c12", "seat": "empty", "surface_id": 98, "env_injected": true, "session_id": null}]);
    let empty99 = json!([{"surface_id": 98, "pid": 1, "exited": false, "seat": "empty", "agent_alive": null}]);
    let fresh_two = |note: Option<bool>| lease_restore_rounds(saved.clone(), vec![
        LeaseRound { live: json!([]), surfaces: json!([]), fresh_rc: Some((EXIT_DIRECTIVE_REFUSED, note)), ..Default::default() },
        LeaseRound { live: live99.clone(), surfaces: empty99.clone(), ..Default::default() },
    ]);
    let r = fresh_two(None);
    assert_eq!((kinds(&r[1]), r[1].1), (vec![("in-seat", true)], 0), "C2: fresh rc 90(기동 글 거절) 뒤 거짓 93: {r:?}");
    let r = fresh_two(Some(true));
    assert_eq!((kinds(&r[1]), r[1].1), (vec![], EXIT_SESSION_LIVENESS_UNKNOWN), "fresh rc 90(잇는 기동 뒤 지침 거절) 뒤 다시 이었다(작성자 둘): {r:?}");
}

/// codex 2R #2 — 복원 fresh 의 rc 0·78 마무리 좌석 = 그 기동이 만든 좌석(98). 가짜 데몬의 역할 이름 조회는 99(이름 바꿈으로 남의 좌석)를 답한다 —
/// 이름으로 찾으면 임대가 99 를 가리킨다.
#[test]
fn restore_fresh_success_finishes_the_lease_on_the_seat_it_made() {
    let saved = json!([{"role": "w-rn", "agent": "claude", "session_id": "s-rn", "cwd": "/tmp", "claude_config_dir": "/cfg"}]);
    for rc in [0, cys::EXIT_GATE_PENDING] {
        let r = lease_restore_rounds(saved.clone(), vec![
            LeaseRound { live: json!([]), surfaces: json!([]), fresh_rc: Some((rc, Some(true))), peek: Some("s-rn"), ..Default::default() },
        ]);
        assert_eq!(r[0].0.iter().map(|c| (c.1, c.2)).collect::<Vec<_>>(), vec![("fresh", true)], "rc {rc} 전제: {r:?}");
        let l: Value = serde_json::from_str(&peek_of("s-rn")).expect("임대 파일");
        assert_eq!(l["surface_id"].as_u64(), Some(98), "rc {rc}: 임대가 만든 좌석(98)이 아니라 이름으로 찾은 좌석을 가리킨다: {l}");
    }
}

/// r4 A(codex 3R ①②③) — 재반환 좌석 판정 진리표 · 멱등 키 · 배선.
#[test]
fn reused_seat_verdict_and_idem_key() {
    let s1 = "abcdef01-0000-4000-8000-000000000001";
    let s2 = "abcdef01-0000-4000-8000-000000000002";
    // 판정(argv 증거 > 등록 대화): 같은 대화 = 잇는 중 · 다른 대화 = Other · 등록 없음·판독 실패 = 판정 불가(「다른 대화」로 단정 0).
    assert_eq!(reused_seat_verdict(Ok(Some(&s1.to_uppercase())), false, s1), ReusedSeat::Continues, "대소문자 정규화");
    assert_eq!(reused_seat_verdict(Ok(Some(s2)), false, s1), ReusedSeat::Other("abcdef01-0000-4000-8000-000000000002".into()), "다른 대화 = 전체 id(skt1 · r5c #3)");
    assert_eq!(reused_seat_verdict(Ok(None), false, s1), ReusedSeat::Unknown("seat-unregistered"), "등록 없음 = 판정 불가(codex 3R ③)");
    assert_eq!(reused_seat_verdict(Err(()), false, s1), ReusedSeat::Unknown("topology-unreadable"), "판독 실패 = 판정 불가(codex 3R ①)");
    // r5(codex r4 #2): argv 는 「잇는 중일 수 있다」의 증거일 뿐(낡을 수 있다) — 등록이 같은 대화거나 등록이 없을 때만 잇는 중으로 올린다.
    //   등록 충돌(등록 = 다른 대화)·판독 실패 + argv = 판정 불가(임대 유지 · 93) · rc 0 성공으로 올리지 않는다.
    assert_eq!(reused_seat_verdict(Ok(None), true, s1), ReusedSeat::Continues, "등록 없음 + argv 이 대화 = 잇는 중(유일한 관측)");
    assert_eq!(reused_seat_verdict(Ok(Some(s1)), true, s1), ReusedSeat::Continues);
    assert_eq!(reused_seat_verdict(Ok(Some(s2)), true, s1), ReusedSeat::Unknown("registered-elsewhere-argv-here"), "낡은 argv 가 등록 충돌을 덮어 성공(codex r4 #2)");
    assert_eq!(reused_seat_verdict(Err(()), true, s1), ReusedSeat::Unknown("topology-unreadable"), "판독 실패 + argv = 판정 불가(codex r4 #2)");
    // 멱등 키: 새 대화 기동 = 종전 키 그대로 · 잇는 기동 = 대화별로 다른 키(대소문자 무관 같은 키).
    let base = launch_idem_key("tw1", "claude", Some("/p"), None);
    assert!(base.starts_with("la-tw1-claude-") && !base.contains("-s"), "{base}");
    assert_eq!(launch_idem_key("tw1", "claude", Some("/p"), Some(s1)), format!("{base}-s{s1}"));
    assert_ne!(launch_idem_key("tw1", "claude", Some("/p"), Some(s1)), launch_idem_key("tw1", "claude", Some("/p"), Some(s2)), "다른 대화 = 다른 키(남의 대화 좌석 재반환 0)");
    assert_eq!(launch_idem_key("tw1", "claude", Some("/p"), Some(&s1.to_uppercase())), launch_idem_key("tw1", "claude", Some("/p"), Some(s1)));
    // 배선: 키는 잇는 기동일 때만 대화를 싣고 · 건너뜀 갈래가 판정을 거치고 · 93 의 좌석 규칙.
    let src = include_str!("bin/cys.rs");
    let la = &src[src.find("fn run_launch_agent_opts(").unwrap()..];
    let la = &la[..la.find("\n}\n").unwrap()];
    let code = code_only(la);
    assert!(code.contains("let idem = launch_idem_key(role, agent, cwd.as_deref(), if resume { session_id.as_deref() } else { None });"), "멱등 키 배선");
    assert!(code.contains("match lease_judge_reused_seat(sid, session_id.as_deref()) {"), "재반환 건너뜀 갈래가 판정을 거치지 않는다");
    let judge = &code[code.find("match lease_judge_reused_seat(").unwrap()..];
    let judge = &judge[..judge.find("\n                }").unwrap()];
    assert!(judge.contains("ReusedSeat::NotLeased | ReusedSeat::Continues => {}")
        && judge.contains("ReusedSeat::Other(t) => return Err(format!(\"{ERR_REUSED_OTHER}:")
        && judge.contains("ReusedSeat::Unknown(why) => return Err(format!(\"{ERR_REUSED_UNKNOWN}:"), "다른 대화·판정 불가가 rc 0(Ready)으로 접힌다: {judge}");
    assert!(code.contains("Err(e) if e.starts_with(ERR_REUSED_OTHER) || e.starts_with(ERR_REUSED_UNKNOWN) => {") , "재반환 비성공 갈래가 rc 93 으로 안 간다");
    assert!(code.contains("Err(e) if e.starts_with(\"session_lease:\") && !e.starts_with(ERR_REUSED_UNKNOWN) => None,"), "93 좌석 규칙");
    let cli = include_str!("session_lease_cli.rs");
    let by_rc = &cli[cli.find("pub(crate) fn lease_finish_by_rc(").unwrap()..];
    let by_rc = code_only(&by_rc[..by_rc.find("\n}\n").unwrap()]);
    assert!(by_rc.contains("} else if rc == EXIT_SESSION_LIVENESS_UNKNOWN && seat.is_some() {\n        lease_keep_unknown(g);"), "launch-agent 93(좌석 남음) = 임대 유지");
}

/// r4 A — rc 93 처분: 좌석이 남은 93(재반환 판정 불가) = 유지 · 좌석 없는 93(기동 전 관문 · 재반환 다른 대화) = 되돌림. 복원 fresh 갈래도 같다(commit 0 · ok 0).
#[test]
fn rc93_keeps_the_lease_only_when_a_seat_may_be_writing() {
    with_fake_daemon(
        |m| match m {
            "system.topology" => json!({"saved": [], "live": []}),
            "system.identify" => json!({"daemon_pid": 77, "started_at": 1.5}),
            _ => json!({}),
        },
        |_| {
            let store = lease_store().unwrap();
            let LeaseGate::Proceed(Some(g)) = lease_gate("w", Some("sess-93a"), None, None, None) else { panic!("임대") };
            lease_finish_by_rc(Some(g), EXIT_SESSION_LIVENESS_UNKNOWN, Some(71), "sess-93a");
            let l = std::fs::read_to_string(store.file_of("sess-93a")).expect("좌석이 남은 93 에서 임대를 되돌렸다(작성자 둘)");
            assert!(l.contains("\"state\":\"unknown\""), "{l}");
            let LeaseGate::Proceed(Some(g)) = lease_gate("w", Some("sess-93b"), None, None, None) else { panic!("임대") };
            lease_finish_by_rc(Some(g), EXIT_SESSION_LIVENESS_UNKNOWN, None, "sess-93b");
            assert!(!store.file_of("sess-93b").exists(), "좌석 없는 93 인데 임대가 남았다(거짓 93)");
        },
    );
    // 복원 fresh: 93 + 만든(재반환) 좌석 = 유지 · commit·ok 0(요약 = 생존 판정 불가 1).
    let saved = json!([{"role": "w-93", "agent": "claude", "session_id": "s-93", "cwd": "/tmp", "claude_config_dir": "/cfg"}]);
    let r = lease_restore_rounds(saved, vec![
        LeaseRound { live: json!([]), surfaces: json!([]), fresh_rc: Some((EXIT_SESSION_LIVENESS_UNKNOWN, None)), peek: Some("s-93"), ..Default::default() },
    ]);
    assert_eq!(r[0].1, EXIT_SESSION_LIVENESS_UNKNOWN, "복원 rc: {r:?}");
    let l = peek_of("s-93");
    assert!(l.contains("\"state\":\"unknown\""), "복원 fresh 93(좌석 남음)에서 임대를 되돌렸다: {l:?}");
}

/// r5(codex r4 #1) → skt1(codex r5c #2·#4 → codex 1R #5) — 같은 역할 좌석의 #1 방어 판정(순수): 원천 = 에이전트별 현재 대화 증거(`current`) 하나 ·
/// 이 대화 = 거절 · 다른 대화 = 통과 · 없음·판독 불가 = 확인 못 함 · topology 핀·등록 문자열은 어느 쪽 신호도 아님 · 다른 에이전트 좌석·기동 중 자기 좌석 = 건너뜀 ·
/// 생존 미상·죽음 = 종전.
#[test]
fn role_seat_verdict_truth_table() {
    const S: &str = "5e55aaaa-0000-4000-8000-000000000001";
    const T: &str = "7e7e0000-0000-4000-8000-00000000000a";
    let row = |sid: u64, role: &str, sess: Option<&str>| json!({"role": role, "surface_id": sid, "seat": "occupied", "session_id": sess});
    let claude = |_: u64| Some("claude".to_string());
    let codex = |_: u64| Some("codex".to_string());
    let cur_none = |_: u64| -> Result<Option<String>, String> { Ok(None) };
    let cur_t = |_: u64| -> Result<Option<String>, String> { Ok(cys::session_lease::norm_id(T)) };
    let cur_s = |_: u64| -> Result<Option<String>, String> { Ok(cys::session_lease::norm_id(S)) };
    let cur_err = |_: u64| -> Result<Option<String>, String> { Err("lease:bound:readdir:13".into()) };
    let on = |_: u64| Some(true);
    let v = |live: &[Value], agent, sa: &dyn Fn(u64) -> Option<String>, cur: &dyn Fn(u64) -> Result<Option<String>, String>| {
        role_seat_verdict(live, "r", agent, S, None, on, sa, cur)
    };
    let w1 = [row(1, "r", None)];
    // claude 좌석: 결속 T = 다른 대화 확인 = 진행(T 좌석 옆 S 새 좌석 = 정상 흐름).
    assert_eq!(v(&w1, "claude", &claude, &cur_t), RoleSeat::Clear);
    // 결속 없음 = 확인 못 함(등록 문자열 T 가 있어도 — r5c #1 · 판정은 등록 문자열을 받지 않는다).
    assert_eq!(v(&w1, "claude", &claude, &cur_none), RoleSeat::Unverified { seat: 1, why: "seat-unbound".into() });
    assert_eq!(v(&w1, "claude", &claude, &cur_s), RoleSeat::ThisConversation { seat: 1, by: "current" });
    // ★codex 1R #5: topology 핀 S(휴리스틱·헬퍼 등록이 만든 것) 가 있어도 실제 결속 T 가 이긴다 — 종전 = 거절(좌석 수명 동안 93/92).
    assert_eq!(v(&[row(1, "r", Some(S))], "claude", &claude, &cur_t), RoleSeat::Clear, "topology 핀 S 가 결속 T 를 이겼다(codex 1R #5)");
    // 휴리스틱 핀 T(topology) 만 · 결속 없음 = 확인 못 함(r5b-2 유지 · 핀으로 풀지 않음).
    assert_eq!(v(&[row(5, "r", Some(T))], "claude", &claude, &cur_none), RoleSeat::Unverified { seat: 5, why: "seat-unbound".into() });
    // 증거 판독 불가 = 확인 못 함(그 사유).
    assert_eq!(v(&w1, "claude", &claude, &cur_err), RoleSeat::Unverified { seat: 1, why: "lease:bound:readdir:13".into() });
    // ★r5c #4: 등록 경로 없는 codex 좌석의 현재 대화(연 rollout) T = 다른 대화 확인 = 진행 · 없음 = 확인 못 함.
    assert_eq!(v(&w1, "codex", &codex, &cur_t), RoleSeat::Clear, "codex 관측 T 좌석을 고착시켰다(r5c #4)");
    assert_eq!(v(&w1, "codex", &codex, &cur_none), RoleSeat::Unverified { seat: 1, why: "seat-unobserved".into() });
    assert_eq!(v(&[row(1, "r", Some(T))], "codex", &codex, &cur_s), RoleSeat::ThisConversation { seat: 1, by: "current" }, "codex topology T 핀이 연 파일 S 를 이겼다(codex 1R #3)");
    // ★r5c #4: 다른 에이전트 좌석(claude 대화 복원 · 같은 역할 codex 좌석) = 이 대화를 쓸 수 없음 = 건너뜀.
    assert_eq!(v(&w1, "claude", &codex, &cur_none), RoleSeat::Clear, "다른 에이전트 좌석을 후보로 막았다");
    // 좌석 에이전트 모름 = 같은 에이전트로 본다(보수).
    assert_eq!(v(&w1, "claude", &|_| None, &cur_none), RoleSeat::Unverified { seat: 1, why: "seat-unobserved".into() });
    // 다른 역할 · 생존 미상 · 죽음 = 넘어감.
    assert_eq!(v(&[row(4, "q", None)], "claude", &claude, &cur_none), RoleSeat::Clear);
    assert_eq!(role_seat_verdict(&w1, "r", "claude", S, None, |_| None, claude, cur_none), RoleSeat::Clear, "생존 미상 = 종전(넓히지 않음)");
    assert_eq!(role_seat_verdict(&w1, "r", "claude", S, None, |_| Some(false), claude, cur_none), RoleSeat::Clear, "죽은 좌석은 작성자가 아니다");
    // 기동 직전 재확인: 지금 기동하는 자기 좌석은 후보가 아니다 · 다른 좌석은 그대로 본다.
    assert_eq!(role_seat_verdict(&w1, "r", "claude", S, Some(1), on, claude, cur_none), RoleSeat::Clear, "기동 중인 자기 좌석을 막았다");
    assert_eq!(role_seat_verdict(&w1, "r", "claude", S, Some(9), on, claude, cur_s), RoleSeat::ThisConversation { seat: 1, by: "current" });
    // 여러 좌석: 앞 좌석이 다른 대화 확인이어도 뒤 좌석이 확인 못 함이면 막는다(상쇄 없음 · r5c 5(c)).
    let two = [row(1, "r", None), row(2, "r", None)];
    let cur_mixed = |sid: u64| -> Result<Option<String>, String> { Ok((sid == 1).then(|| cys::session_lease::norm_id(T)).flatten()) };
    assert_eq!(v(&two, "claude", &claude, &cur_mixed), RoleSeat::Unverified { seat: 2, why: "seat-unbound".into() });
    // 배선: 잇는 기동일 때 좌석을 만들기 전에 · 거절은 ERR_REUSED_UNKNOWN(좌석 = 그 좌석 · rc 93 · 임대 유지).
    let src = include_str!("bin/cys.rs");
    let la = &src[src.find("fn run_launch_agent_opts(").unwrap()..];
    let la = code_only(&la[..la.find("\n}\n").unwrap()]);
    let guard = la.find("match lease_role_seat_verdict(role, agent, session_id.as_deref(), None) {").expect("#1 방어 배선");
    assert!(guard < la.find("\"surface.create\"").unwrap(), "방어가 좌석 생성 뒤에 있다");
    assert!(la.contains("Err(e) if e.starts_with(ERR_REUSED_UNKNOWN) => created.or(unverified),"), "93 좌석 = 그 좌석(임대 유지)");
    // 운영 「현재 대화 증거」 = claude 결속 · 그 밖 = 에이전트가 연 rollout(lsof) — 등록 문자열·topology 핀은 쓰지 않는다(r5c #1 · codex 1R #3·#5).
    let cli = include_str!("session_lease_cli.rs");
    let now = &cli[cli.find("pub(crate) fn seat_conversation_now(").unwrap()..];
    let now = code_only(&now[..now.find("\n}\n").unwrap()]);
    assert!(now.contains("sl::seat_bound_conversation(&store, sid, gen, &sl::probe_holder)") && now.contains("seat_agent_open_rollout(root, bin)"), "현재 대화 증거 원천");
    assert!(!now.contains("system.topology") && !now.contains("registered_session_id"), "현재 대화 증거가 데몬 핀·등록 문자열이다(codex 1R #3)");
    let rv = &cli[cli.find("pub(crate) fn lease_role_seat_verdict(").unwrap()..];
    let rv = code_only(&rv[..rv.find("\n}\n").unwrap()]);
    assert!(!rv.contains("org.status"), "#1 방어가 등록 문자열을 다시 읽는다(codex 1R #5)");
    let cw = &cli[cli.find("    fn seat_conversation(&self, surface_id: u64").unwrap()..];
    let cw = code_only(&cw[..cw.find("\n    }\n").unwrap()]);
    assert!(cw.contains("seat_conversation_now(surface_id,") && !cw.contains("org.status"), "풀림 판독 원천이 등록 문자열이다(r5c #1)");
    // follow(결속을 만드는 유일한 자리)는 좌석 최상위 훅으로 **증명된** 등록만 옮긴다(r5c #1-3 헬퍼·도구 셸 · codex 1R #1 판독 불가 = 옮기지 않음).
    let fo = &cli[cli.find("pub(crate) fn lease_follow_on_register(").unwrap()..];
    let fo = code_only(&fo[..fo.find("\n}\n").unwrap()]);
    let gate = fo.find("if follow_lineage(&chain, row[\"agent_bin\"].as_str().unwrap_or_default()) != sl::Lineage::ProvenTop {").expect("follow 계통 관문 배선");
    assert!(gate < fo.find("sl::follow(&store, &id, &writer,").expect("follow 호출"), "계통 관문이 follow 뒤에 있다");
    // 등록 앞 결속 해제(codex 1R #2B) · 기동 글 직전 확정(codex 1R #2A) 배선.
    let ur = &src[src.find("Command::UsageRegister { transcript, surface, source } =>").unwrap()..];
    let ur = code_only(&ur[..ur.find("Command::UsageReportStdin").unwrap()]);
    assert!(ur.find("lease_transition_before_register(sid, &tp);").expect("등록 앞 결속 해제") < ur.find("request(\"usage.register\", params)").unwrap(), "결속 해제가 등록 뒤에 있다");
    let bo = &src[src.find("\nfn boot_agent_on_surface(").unwrap()..];
    let bo = code_only(&bo[..bo.find("\n}\n").unwrap()]);
    let commit = bo.find("if effective_resume {\n        lease_commit_launch(role, agent, session_id, sid)?;\n    }").expect("기동 글 직전 확정 배선");
    assert!(commit < bo.find("authoritative_paste_settled(").unwrap(), "확정이 기동 글 뒤에 있다");
}

/// r5(codex r4 #3 소비부) — 복원 fresh 안쪽 거절(92·93)도 표준 거절 줄을 낸다(phoenix `_LEASE_REFUSAL_RE` 가 읽는 모양 ·
/// 같은 문자열을 test_phoenix_seatkeep_t1_lease_hold.py R5 축이 phoenix 판독기로 읽는다).
#[test]
fn restore_inner_refusals_print_the_standard_line() {
    let s = "5e55aaaa-0000-4000-8000-000000000001";
    assert_eq!(restore_inner_refusal_line("w1", Some(s), EXIT_SESSION_LIVENESS_UNKNOWN, Some(7)),
        "· w1: 대화 5e55aaaa-0000-4000-8000-000000000001 작성자 생존 판정 불가(seat-unverified) — 띄우지 않음 · 확인: `cys read-screen --surface surface:7` 로 그 좌석이 이 대화를 잇는지 보세요");
    assert_eq!(restore_inner_refusal_line("w2", Some(s), EXIT_SESSION_WRITER_LIVE, None),
        "· w2: 대화 5e55aaaa-0000-4000-8000-000000000001 — 그 대화를 잇는 좌석이 이미 있음 — 띄우지 않음 · 확인: 바로 위 [launch-agent] 줄의 좌석을 `cys read-screen` 으로 보세요");
    let src = include_str!("bin/cys.rs");
    let rr = &src[src.find("fn run_restore_with(").unwrap()..];
    let rr = code_only(&rr[..rr.find("\n}\n").unwrap()]);
    assert!(rr.contains("if rc == EXIT_SESSION_WRITER_LIVE { lease_live += 1 } else { lease_unknown += 1 }\n                println!(\"{}\", restore_inner_refusal_line(role, sess.as_deref(), rc, made));"),
        "복원 fresh 안쪽 거절 갈래가 표준 거절 줄을 내지 않는다");
}
