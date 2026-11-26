//! ★(1.1.16 · TICKET=cysr-1116-borrow23-1119 · 차용 ②) OSC 7501 단말 쪽 시험 — 규격 버림 규칙 · 청크 경계 스캐너 · 저장소 ·
//! 덧씌움 · `display_activity` 매핑 · 실제 PTY 좌석에서 질의 응답과 보고 수신.
//!
//! 견본 보고 원문은 11-19 격리 실측(Claude Code 2.1.328)의 실물 바이트다(msg 의 경로만 짧은 가짜로 바꿨다).

use super::*;
use std::time::{Duration, Instant};

fn report(body: &str) -> Report {
    match parse(body.as_bytes(), body.len() + 9) {
        Parsed::Report(r) => r,
        other => panic!("expected report for {body:?}, got {other:?}"),
    }
}

fn discard(body: &str) -> &'static str {
    match parse(body.as_bytes(), body.len() + 9) {
        Parsed::Discard(w) => w,
        other => panic!("expected discard for {body:?}, got {other:?}"),
    }
}

// ---- 파서(규격 버림 규칙) ----

#[test]
fn real_claude_reports_parse() {
    // 실측 원문(11-19 · Claude Code 2.1.328).
    let r = report("state=blocked:app=claude-code:kind=permission:msg=dHJ1c3QgdGhpcyBmb2xkZXI=");
    assert_eq!(r.state, Some(PState::Blocked));
    assert_eq!(r.kind, Some(Kind::Permission));
    assert_eq!(r.app.as_deref(), Some("claude-code"));
    assert_eq!(r.msg.as_deref(), Some("trust this folder"));
    assert_eq!(report("state=idle:app=claude-code").state, Some(PState::Idle));
    assert_eq!(report("state=working:app=claude-code:msg=V3JpdGluZyBwcm9iZS50eHQ=").msg.as_deref(), Some("Writing probe.txt"));
    assert_eq!(report("state=done:app=claude-code").state, Some(PState::Done));
    let c = report("state=clear");
    assert_eq!(c.state, None);
    assert!(c.id.is_empty());
}

#[test]
fn query_is_only_a_bare_question_mark() {
    assert_eq!(parse(b"?", 11), Parsed::Query);
    assert_eq!(parse(b" ?\t", 13), Parsed::Query);
    // `??` · `?:state=idle` 는 질의가 아니다(질의도 보고도 아님 = 상태 없음 버림).
    assert!(matches!(parse(b"??", 12), Parsed::Discard(_)));
    assert!(matches!(parse(b"?:state=idle", 22), Parsed::Report(_) | Parsed::Discard(_)));
    assert_ne!(parse(b"?:state=idle", 22), Parsed::Query);
}

#[test]
fn discard_rules() {
    assert_eq!(discard("app=x"), "no state");
    assert_eq!(discard("state=finished"), "unknown state");
    assert_eq!(discard("state=idle:abcdefghijklmnopq=1"), "key too long"); // 17바이트 키
    assert_eq!(discard("state=idle:id=a//b"), "bad id");
    assert_eq!(discard("state=idle:id=a/b/c/d/e/f/g/h/i"), "bad id"); // 깊이 9
    assert_eq!(discard(&format!("state=idle:id={}", "a".repeat(33))), "bad id");
    assert_eq!(discard(&format!("state=idle:app={}", "a".repeat(33))), "app too long");
    // 허용 밖 바이트(!)가 든 값 = 그 쌍만 무시(보고는 산다) · base64 길이 결함 = 통째 폐기.
    assert_eq!(report("state=idle:msg=!!!").msg, None);
    assert_eq!(discard("state=idle:msg=a"), "bad msg");
    // 정규형이 아닌 base64(버려지는 비트가 0 아님): "aGk=" 정상 · "aGl=" 비정규.
    assert_eq!(report("state=idle:msg=aGk=").msg.as_deref(), Some("hi"));
    assert_eq!(discard("state=idle:msg=aGl="), "bad msg");
    // 해독된 글에 제어 문자(ESC) — 통째 폐기.
    assert_eq!(discard("state=idle:msg=G1sybQ=="), "bad msg"); // "\x1b[2m"
    // title 한도(인코딩 256).
    assert_eq!(discard(&format!("state=idle:title={}", "QUFB".repeat(65))), "bad title");
    // 시퀀스 길이 4096 초과.
    assert!(matches!(parse(b"state=idle", MAX_SEQUENCE + 1), Parsed::Discard("sequence too long")));
}

#[test]
fn ignored_pairs_and_optional_fields() {
    // 키가 대문자 · 값에 허용 밖 바이트 · '=' 없는 쌍 = 그 쌍만 무시.
    let r = report("state=working:Kind=x:app=claude code:junk:progress=42");
    assert_eq!(r.app, None);
    assert_eq!(r.progress, Some(42));
    // kind 는 blocked 에만 · progress 는 working/blocked 에만 · 100 초과 무시.
    assert_eq!(report("state=idle:kind=permission:progress=5").kind, None);
    assert_eq!(report("state=idle:progress=5").progress, None);
    assert_eq!(report("state=working:progress=101").progress, None);
    assert_eq!(report("state=blocked:kind=auth").kind, Some(Kind::Auth));
    assert_eq!(report("state=blocked:kind=other").kind, None);
    // 같은 키 = 뒤의 것이 이긴다.
    assert_eq!(report("state=idle:state=working").state, Some(PState::Working));
    // 앞뒤 공백·탭 허용.
    assert_eq!(report(" state = done ").state, Some(PState::Done));
    // 방향 바꿈 문자는 지운다(U+202E).
    let rlo = "\u{202e}abc";
    let enc = b64(rlo.as_bytes());
    assert_eq!(report(&format!("state=idle:msg={enc}")).msg.as_deref(), Some("abc"));
}

fn b64(b: &[u8]) -> String {
    const A: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut s = String::new();
    for c in b.chunks(3) {
        let n = (u32::from(c[0]) << 16) | (u32::from(*c.get(1).unwrap_or(&0)) << 8) | u32::from(*c.get(2).unwrap_or(&0));
        for i in 0..4 {
            if i <= c.len() {
                s.push(A[((n >> (18 - 6 * i)) & 63) as usize] as char);
            } else {
                s.push('=');
            }
        }
    }
    s
}

#[test]
fn strict_b64_round_trip() {
    for t in ["", "a", "ab", "abc", "abcd", "한글 상태", "approve Write: /tmp/x"] {
        assert_eq!(decode_b64_strict(b64(t.as_bytes()).as_bytes()).as_deref(), Some(t.as_bytes()), "{t}");
        let nopad = b64(t.as_bytes()).trim_end_matches('=').to_string();
        assert_eq!(decode_b64_strict(nopad.as_bytes()).as_deref(), Some(t.as_bytes()), "nopad {t}");
    }
    assert_eq!(decode_b64_strict(b"a"), None);
    assert_eq!(decode_b64_strict(b"aGk==="), None);
    assert_eq!(decode_b64_strict(b"aG=k"), None);
}

// ---- 스캐너(청크 경계) ----

#[test]
fn scanner_extracts_across_every_split() {
    let stream: &[u8] = b"x\x1b]0;title\x07\x1b]7501;?\x07y\x1b]7501;state=working:app=claude-code\x1b\\\x1b]133;A\x07\x1bcz";
    let want = vec![
        Event::Osc7501 { body: b"?".to_vec(), seq_len: 9, bel: true },
        Event::Osc7501 { body: b"state=working:app=claude-code".to_vec(), seq_len: 2 + 5 + 29 + 2, bel: false },
        Event::PromptStart,
        Event::Reset,
    ];
    for cut in 0..=stream.len() {
        let mut sc = Scanner::default();
        let mut got = sc.feed(&stream[..cut]);
        got.extend(sc.feed(&stream[cut..]));
        assert_eq!(got, want, "split at {cut}");
    }
    // 1바이트씩.
    let mut sc = Scanner::default();
    let got: Vec<Event> = stream.iter().flat_map(|b| sc.feed(std::slice::from_ref(b))).collect();
    assert_eq!(got, want);
}

#[test]
fn scanner_aborts_and_bounds() {
    let mut sc = Scanner::default();
    // CAN 취소 · ESC 뒤 종결 아님 = 버림(새 이스케이프로 다시 읽는다).
    assert!(sc.feed(b"\x1b]7501;?\x18rest\x07").is_empty());
    assert_eq!(sc.feed(b"\x1b]7501;state=idle\x1b\x1b]7501;?\x07"), vec![Event::Osc7501 { body: b"?".to_vec(), seq_len: 9, bel: true }]);
    // 넘친 시퀀스 = 길이 한도로 버려진다(질의로도 읽지 않는다) · 담는 버퍼는 유계.
    let mut big = b"\x1b]7501;".to_vec();
    big.extend(std::iter::repeat(b'a').take(10_000));
    big.push(0x07);
    let ev = sc.feed(&big);
    assert_eq!(ev.len(), 1);
    let Event::Osc7501 { body, seq_len, .. } = &ev[0] else { panic!() };
    assert!(body.is_empty() && *seq_len > MAX_SEQUENCE);
    assert!(matches!(parse(body, *seq_len), Parsed::Discard(_)));
    assert!(sc.buf.capacity() <= MAX_SEQUENCE * 2);
    // 133;B 등 다른 133 은 프롬프트 시작이 아니다.
    assert!(sc.feed(b"\x1b]133;B\x07\x1b]133;D;0\x07").is_empty());
    assert_eq!(sc.feed(b"\x1b]133;A;cl=m\x07"), vec![Event::PromptStart]);
}

// ---- 저장소 · ingest ----

/// 질의에 이미 답한 생애의 좌석(보고를 받는 조건)으로 먹인다.
fn feed(store: &mut Store, bytes: &[u8], now: Instant) -> Ingest {
    store.life_answered = true;
    feed_raw(store, bytes, now)
}

/// 생애 표식을 건드리지 않고 먹인다(묻지 않은 보고 시험용).
fn feed_raw(store: &mut Store, bytes: &[u8], now: Instant) -> Ingest {
    let mut sc = Scanner::default();
    ingest(store, sc.feed(bytes), now, true)
}

#[test]
fn ingest_answers_query_with_same_terminator() {
    let mut st = Store::default();
    let t = Instant::now();
    assert_eq!(feed(&mut st, b"\x1b]7501;?\x07", t).replies, vec![b"\x1b]7501;?\x07".to_vec()]);
    assert_eq!(feed(&mut st, b"\x1b]7501;?\x1b\\", t).replies, vec![b"\x1b]7501;?\x1b\\".to_vec()]);
    assert_eq!(st.answered, 2);
    // 보고·다른 OSC 에는 아무것도 되쓰지 않는다.
    assert!(feed(&mut st, b"\x1b]7501;state=idle\x07\x1b]0;?\x07", t).replies.is_empty());
}

#[test]
fn real_lifecycle_sequence() {
    // 11-19 실측 C 갈래 순서 그대로(권한 창 → Esc → /exit).
    let mut st = Store::default();
    let t0 = Instant::now();
    let steps: &[(&str, Option<PState>)] = &[
        ("state=blocked:app=claude-code:kind=permission:msg=dHJ1c3QgdGhpcyBmb2xkZXI=", Some(PState::Blocked)),
        ("state=clear", None),
        ("state=idle:app=claude-code", Some(PState::Idle)),
        ("state=working:app=claude-code", Some(PState::Working)),
        ("state=done:app=claude-code", Some(PState::Done)),
        ("state=working:app=claude-code", Some(PState::Working)),
        ("state=blocked:app=claude-code:kind=permission:msg=YXBwcm92ZSBXcml0ZQ==", Some(PState::Blocked)),
        ("state=idle:app=claude-code", Some(PState::Idle)),
        ("state=clear", None),
    ];
    for (i, (body, want)) in steps.iter().enumerate() {
        let seq = format!("\x1b]7501;{body}\x07");
        feed(&mut st, seq.as_bytes(), t0 + Duration::from_millis(i as u64));
        assert_eq!(st.summary().map(|(_, r)| r.state), *want, "step {i} {body}");
    }
    assert_eq!(st.reports, steps.len() as u64);
}

#[test]
fn ids_cap_clear_and_urgency() {
    let mut st = Store::default();
    let t = Instant::now();
    feed(&mut st, b"\x1b]7501;state=done:id=a\x07\x1b]7501;state=working:id=a/b\x07\x1b]7501;state=idle\x07", t);
    assert_eq!(st.len(), 3);
    assert_eq!(st.summary().unwrap().1.state, PState::Working); // 가장 급한 것
    feed(&mut st, b"\x1b]7501;state=blocked:id=z:kind=question\x07", t);
    assert_eq!(st.summary().unwrap().1.state, PState::Blocked);
    // clear id=a = a 와 그 아래(a/b) · z·뿌리는 남는다.
    feed(&mut st, b"\x1b]7501;state=clear:id=a\x07", t);
    assert_eq!(st.len(), 2);
    // 프롬프트 시작 = working·blocked 만 끝 · RIS = 전부.
    feed(&mut st, b"\x1b]7501;state=working:id=w\x07\x1b]133;A\x07", t);
    assert_eq!(st.len(), 1);
    assert_eq!(st.summary().unwrap().1.state, PState::Idle);
    feed(&mut st, b"\x1bc", t);
    assert_eq!(st.len(), 0);
    // 상한 = 가장 오래 갱신되지 않은 것을 버린다.
    for i in 0..(MAX_RECORDS + 5) {
        feed(&mut st, format!("\x1b]7501;state=idle:id=r{i}\x07").as_bytes(), t);
    }
    assert_eq!(st.len(), MAX_RECORDS);
    assert!(st.records.contains_key(&format!("r{}", MAX_RECORDS + 4)));
    assert!(!st.records.contains_key("r0"));
    // 버린 보고 계수.
    feed(&mut st, b"\x1b]7501;state=bogus\x07", t);
    assert_eq!((st.discarded, st.last_discard), (1, Some("unknown state")));
}

#[test]
fn wipe_on_agent_exit_is_total() {
    let mut st = Store::default();
    let t = Instant::now();
    feed(&mut st, b"\x1b]7501;state=done\x07\x1b]7501;state=working:id=x\x07", t);
    st.wipe(true, "agent exited (shell returned)", t);
    assert_eq!(st.len(), 0);
    assert_eq!(st.last_wipe.map(|w| w.0), Some("agent exited (shell returned)"));
}

// ---- 덧씌움(done → 사람 입력 뒤 = 봄) ----

#[test]
fn overlay_seen_only_after_human_input_following_done() {
    let mut st = Store::default();
    let t0 = Instant::now();
    assert!(overlay(&st, None, t0).is_none());
    feed(&mut st, b"\x1b]7501;state=done:app=claude-code\x07", t0 + Duration::from_millis(10));
    let now = t0 + Duration::from_millis(1500);
    assert!(!overlay(&st, None, now).unwrap().seen);
    assert!(!overlay(&st, Some(t0), now).unwrap().seen, "입력이 done 보다 먼저였다 = 아직 안 봄");
    assert!(overlay(&st, Some(t0 + Duration::from_millis(20)), now).unwrap().seen);
    assert!((overlay(&st, None, now).unwrap().age_secs - 1.49).abs() < 0.01);
    // working 은 사람 입력과 무관하게 seen=false.
    feed(&mut st, b"\x1b]7501;state=working\x07", t0 + Duration::from_millis(30));
    assert!(!overlay(&st, Some(now), now).unwrap().seen);
}

#[test]
fn knob_off_only_for_zero() {
    assert!(enabled_from(None));
    assert!(enabled_from(Some("1")));
    assert!(enabled_from(Some("")));
    assert!(!enabled_from(Some("0")));
    assert!(!enabled_from(Some(" 0 ")));
}

// ---- display_activity 매핑 ----

fn ov(state: PState, kind: Option<Kind>, seen: bool) -> Overlay {
    Overlay { state, kind, app: Some("claude-code".into()), msg: None, title: None, progress: None, id: String::new(), age_secs: 0.5, seen, records: 1 }
}

#[test]
fn overlay_state_mapping_is_total() {
    use crate::activity::{overlay_state, Effective};
    let m = |o: Overlay| {
        let (e, r, _) = overlay_state(&o);
        (e.as_str(), r.as_str())
    };
    assert_eq!(m(ov(PState::Working, None, false)), ("working", "active"));
    assert_eq!(m(ov(PState::Idle, None, false)), ("waiting", "idle"));
    assert_eq!(m(ov(PState::Blocked, Some(Kind::Permission), false)), ("waiting_for_input", "permission"));
    assert_eq!(m(ov(PState::Blocked, Some(Kind::Question), false)), ("waiting_for_input", "question"));
    assert_eq!(m(ov(PState::Blocked, Some(Kind::Auth), false)), ("waiting_for_input", "auth"));
    assert_eq!(m(ov(PState::Blocked, None, false)), ("waiting_for_input", "blocked"));
    assert_eq!(m(ov(PState::Done, None, false)), ("done", "done"));
    assert_eq!(m(ov(PState::Done, None, true)), ("waiting", "done"));
    assert_eq!(m(ov(PState::Error, None, false)), ("done", "error"));
    assert_eq!(m(ov(PState::Error, None, true)), ("waiting", "error"));
    // 뜻 문구: unknown 은 성공이 아니라고 못 박는다 · done 은 「안 봄」.
    assert!(Effective::Unknown.meaning().contains("성공했다는 뜻이 아님"));
    assert!(Effective::Done.meaning().contains("아직 안 봄"));
}

// ---- 실제 PTY 좌석: 질의 응답 + 보고 수신 + 사람 계수 무접촉 ----

/// raw 모드에서 질의를 보내고 응답을 기다린 뒤 ACK/NOACK 를 찍고 보고 2건(BEL · ST 종결)을 낸다.
const PY_PROBE: &str = r#"import os,tty,time,select
tty.setraw(0)
os.write(1,b'\x1b]7501;?\x07')
buf=b''
end=time.time()+8
while time.time()<end and b'\x1b]7501;?\x07' not in buf:
    r,_,_=select.select([0],[],[],0.2)
    if r: buf+=os.read(0,64)
os.write(1,b'ACK ' if b'\x1b]7501;?\x07' in buf else b'NOACK ')
os.write(1,b'\x1b]7501;state=working:app=probe:msg=aGk=\x07')
time.sleep(0.3)
os.write(1,b'\x1b]7501;state=blocked:app=probe:kind=question\x1b\\')
time.sleep(30)
"#;

#[test]
fn live_seat_answers_query_and_records_reports() {
    if std::env::var("CYS_PROGRAM_STATUS").as_deref() == Ok("0") {
        return; // 끈 기계에서는 이 시험의 전제가 없다(기본 = 켬)
    }
    let g = crate::governance::PACK_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    crate::delivery::tests::isolate_state_dir_for_thread("ps7501");
    let dir = std::env::temp_dir().join(format!("cys-ps7501-{}", std::process::id()));
    let _ = std::fs::create_dir_all(&dir);
    std::fs::write(dir.join("acl.json"), r#"{"default":"allow","rules":[]}"#).unwrap();
    std::env::set_var(cys::pack::ENV_PACK_DIR, &dir);
    let daemon = crate::state::Daemon::new(dir.join("cysd.sock"));
    daemon.activity.running.store(true, std::sync::atomic::Ordering::SeqCst); // 관측기가 도는 데몬(응답 관문 열림)
    let script = dir.join("probe.py");
    std::fs::write(&script, PY_PROBE).unwrap();
    let cmd = format!("python3 {}", script.display());
    let s = crate::pty_test_support::retry_on_pty_exhaustion("ps7501 seat", || {
        daemon.create_surface(None, Some(cmd.clone()), None, Some("worker".into()), 24, 80)
    })
    .expect("create surface");
    daemon.surfaces.lock().unwrap().insert(s.id, s.clone());
    let deadline = Instant::now() + Duration::from_secs(20);
    let mut last = None;
    while Instant::now() < deadline {
        let st = s.program_status.lock().unwrap();
        last = st.summary().map(|(_, r)| (r.state, r.kind, r.app.clone()));
        if last.as_ref().map(|l| l.0) == Some(PState::Blocked) {
            break;
        }
        drop(st);
        std::thread::sleep(Duration::from_millis(50));
    }
    let screen = s.parser.lock().unwrap().screen().contents();
    let st = s.program_status.lock().unwrap();
    assert!(screen.contains("ACK") && !screen.contains("NOACK"), "질의 응답이 프로그램에 닿아야 한다: {screen:?}");
    assert_eq!(st.answered, 1);
    assert_eq!(st.reports, 2);
    assert_eq!(last, Some((PState::Blocked, Some(Kind::Question), Some("probe".into()))));
    drop(st);
    // 응답 바이트는 사람 입력이 아니다 — 사람 마지막 입력·미제출 계수 무접촉.
    assert!(s.last_human_input.lock().unwrap().is_none(), "7501 응답이 사람 입력으로 잡혔다");
    assert_eq!(s.pending_input_bytes.load(std::sync::atomic::Ordering::Relaxed), 0);
    if let Ok(mut c) = s.child.lock() {
        let _ = c.kill(); // 이 시험이 만든 자식만(자기 pid)
    }
    drop(g);
}

// ---- codex 1R 수리 고정 ----

#[test]
fn duplicate_key_cannot_launder_a_limit_violation() {
    let long = "A".repeat(MAX_MSG_ENCODED + 1);
    assert_eq!(discard(&format!("state=idle:msg={long}:msg=aGk=")), "bad msg");
    assert_eq!(discard("state=idle:msg=G1sybQ==:msg=aGk="), "bad msg");
    assert_eq!(discard(&format!("state=idle:app={}:app=ok", "a".repeat(33))), "app too long");
    assert_eq!(discard("state=idle:id=a//b:id=ok"), "bad id");
    assert_eq!(discard(&format!("state=idle:title={}:title=aGk=", "QUFB".repeat(65))), "bad title");
}

#[test]
fn urgent_child_inherits_app_from_nearest_ancestor() {
    let mut st = Store::default();
    let t = Instant::now();
    feed(&mut st, b"\x1b]7501;state=working:app=deploy\x07\x1b]7501;state=idle:id=eu:app=eu-app\x07\x1b]7501;state=blocked:id=eu/west\x07", t);
    let o = overlay(&st, None, t).unwrap();
    assert_eq!((o.state, o.id.as_str(), o.app.as_deref()), (PState::Blocked, "eu/west", Some("eu-app")));
    feed(&mut st, b"\x1b]7501;state=clear:id=eu\x07\x1b]7501;state=blocked:id=us\x07", t);
    let o = overlay(&st, None, t).unwrap();
    assert_eq!((o.id.as_str(), o.app.as_deref()), ("us", Some("deploy")));
    // 조상에 app 이 없으면 None(지어내지 않는다).
    let mut st2 = Store::default();
    feed(&mut st2, b"\x1b]7501;state=blocked:id=x/y\x07", t);
    assert_eq!(overlay(&st2, None, t).unwrap().app, None);
}

#[test]
fn version_moves_on_every_change_and_output_seq_is_monotonic() {
    use crate::activity::overlay_seq;
    let mut st = Store::default();
    let t0 = Instant::now();
    let mut last = 0u64;
    let mut obs_seq = 5u64; // 관측기 순번이 멈춰 있어도(틱 사이·관측기 정지) 변화마다 순번이 늘어야 한다
    let mut step = |st: &mut Store, bytes: &[u8], human: Option<Instant>, t: Instant, tick: bool| {
        if tick {
            obs_seq += 1;
        }
        if !bytes.is_empty() {
            feed(st, bytes, t);
        }
        let seen = overlay(st, human, t).is_some_and(|o| o.seen);
        let seq = overlay_seq(obs_seq, st.version, seen);
        assert!(seq > last || (seq == last && bytes.is_empty() && !tick), "seq {seq} <= {last}");
        last = seq;
    };
    let ms = |n| t0 + Duration::from_millis(n);
    step(&mut st, b"\x1b]7501;state=working\x07", None, ms(1), false);
    step(&mut st, b"\x1b]7501;state=blocked:kind=permission\x07", None, ms(2), false); // 틱 없이 상태 변화
    step(&mut st, b"\x1b]7501;state=done\x07", None, ms(3), false);
    step(&mut st, b"", Some(ms(4)), ms(5), false); // 사람이 봄 → done→waiting · 순번 +1
    step(&mut st, b"\x1b]7501;state=clear\x07", Some(ms(4)), ms(6), false); // 덧씌움 사라짐(화면 판정으로) · 그래도 순번 증가
    step(&mut st, b"", None, ms(7), true);
    // 셸 프롬프트는 생애를 끝낸다(codex 2R 3번) — 다음 프로그램이 다시 묻고 보고한다.
    step(&mut st, b"\x1b]133;A\x07\x1b]7501;?\x07\x1b]7501;state=working\x07", None, ms(8), false);
    let v = st.version;
    st.wipe(false, "x", ms(9));
    assert_eq!(st.version, v + 1, "지움도 판을 올린다");
    st.wipe(false, "x", ms(10));
    assert_eq!(st.version, v + 1, "지울 것이 없으면 판 불변");
}

#[test]
fn no_answer_when_the_observer_is_not_running() {
    // codex 2R MAJOR: 관측기 스레드가 못 떴거나 죽었으면 답하지 않는다(답하면 Claude 가 제목 표지를 지워 영구 unknown).
    let mut st = Store::default();
    let mut sc = Scanner::default();
    let r = ingest(&mut st, sc.feed(b"\x1b]7501;?\x07"), Instant::now(), false);
    assert!(r.replies.is_empty());
    assert_eq!((st.answered, st.unanswered), (0, 1));
    assert_eq!(diag_wire(&st, Instant::now())["unanswered_queries"], 1);
}

// ---- 독립 검증 V-1·V-2 (master 처분 (가)): 질의에 답한 생애의 보고만 받는다 ----

#[test]
fn codex_unsolicited_reports_are_ignored_byte_for_byte() {
    // 검증 좌석 실측(codex 0.167 · 질의 0 · ST 종결) 바이트 그대로.
    let codex: &[u8] = b"\x1b]0;rp-_0xrijoi\x07\x1b]7501;state=idle:app=codex\x1b\\\x1b]0;\xe2\xa0\x8b rp-_0xrijoi\x07\x1b]7501;state=working:app=codex\x1b\\\x1b]0;rp-_0xrijoi\x07\x1b]7501;state=idle:app=codex\x1b\\\x1b]0;\x07\x1b]7501;state=clear\x1b\\";
    let mut st = Store::default();
    let r = feed_raw(&mut st, codex, Instant::now());
    assert!(r.replies.is_empty());
    assert_eq!((r.applied, st.unsolicited, st.reports, st.len()), (0, 4, 0, 0));
    assert!(overlay(&st, None, Instant::now()).is_none(), "묻지 않은 codex 보고가 덧씌워졌다(1.1.15 화면 판정 회귀)");
    assert_eq!(diag_wire(&st, Instant::now())["unsolicited_reports"], 4);
}

#[test]
fn shell_spoof_without_query_changes_nothing() {
    let mut st = Store::default();
    feed_raw(&mut st, b"\x1b]7501;state=blocked:kind=permission:app=fake\x07", Instant::now());
    assert!(overlay(&st, None, Instant::now()).is_none());
    assert_eq!(st.unsolicited, 1);
}

#[test]
fn answered_life_ends_on_total_wipe() {
    let mut st = Store::default();
    let t = Instant::now();
    feed_raw(&mut st, b"\x1b]7501;?\x07\x1b]7501;state=working\x07", t);
    assert_eq!(st.len(), 1, "같은 흐름에서 질의 응답 뒤의 보고는 받는다");
    st.wipe(true, "agent exited (shell returned)", t);
    feed_raw(&mut st, b"\x1b]7501;state=working:app=codex\x1b\\", t);
    assert_eq!((st.len(), st.unsolicited), (0, 1), "다음 프로그램은 다시 물어야 받는다");
    feed_raw(&mut st, b"\x1b]7501;?\x1b\\\x1b]7501;state=idle\x1b\\", t);
    assert_eq!(st.len(), 1);
    feed_raw(&mut st, b"\x1bc\x1b]7501;state=idle\x07", t); // RIS 도 생애를 끝낸다
    assert_eq!(st.len(), 0);
}

#[test]
fn live_shell_seat_printf_spoof_is_ignored() {
    if std::env::var("CYS_PROGRAM_STATUS").as_deref() == Ok("0") {
        return;
    }
    let g = crate::governance::PACK_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    crate::delivery::tests::isolate_state_dir_for_thread("ps7501spoof");
    let dir = std::env::temp_dir().join(format!("cys-ps7501spoof-{}", std::process::id()));
    let _ = std::fs::create_dir_all(&dir);
    std::fs::write(dir.join("acl.json"), r#"{"default":"allow","rules":[]}"#).unwrap();
    std::env::set_var(cys::pack::ENV_PACK_DIR, &dir);
    let daemon = crate::state::Daemon::new(dir.join("cysd.sock"));
    daemon.activity.running.store(true, std::sync::atomic::Ordering::SeqCst);
    let cmd = r"printf '\033]7501;state=blocked:kind=permission:app=fake\007SPOOFED'; sleep 30".to_string();
    let s = crate::pty_test_support::retry_on_pty_exhaustion("ps7501 spoof seat", || {
        daemon.create_surface(None, Some(cmd.clone()), None, Some("worker".into()), 24, 80)
    })
    .expect("create surface");
    daemon.surfaces.lock().unwrap().insert(s.id, s.clone());
    let deadline = Instant::now() + Duration::from_secs(15);
    while Instant::now() < deadline && !s.parser.lock().unwrap().screen().contents().contains("SPOOFED") {
        std::thread::sleep(Duration::from_millis(50));
    }
    std::thread::sleep(Duration::from_millis(200));
    let st = s.program_status.lock().unwrap();
    assert!(s.parser.lock().unwrap().screen().contents().contains("SPOOFED"), "위조 출력이 나오지 않았다(전제)");
    assert_eq!((st.len(), st.unsolicited, st.answered), (0, 1, 0), "셸 printf 위조가 상태를 바꿨다");
    drop(st);
    if let Ok(mut c) = s.child.lock() {
        let _ = c.kill();
    }
    drop(g);
}

// ---- codex 2R 3번 · master#bd64bac1 B안: 생애 = 셸 프롬프트까지 · PTY 전경 프로세스 그룹에 묶음 · clear 로는 끝내지 않음 ----

/// 11-19 격리 실측 원자료(갈래 B·C)를 그 순서 그대로 재생한다 — Claude 2.1.328 은 신뢰 창을 닫을 때 `state=clear` 를 보내고
/// **다시 묻지 않고** idle·working·done·blocked 를 이어 보낸다. clear 로 생애를 끝내면 그 뒤가 전부 버려진다(퇴보).
#[test]
fn raw_probe_b_c_replay_keeps_reports_after_trust_clear() {
    let raw = include_str!("../../../docs/evidence/borrow23-1119/claude-2.1.328-osc7501-probe.jsonl");
    for run in ["B", "C"] {
        let mut st = Store::default();
        let mut sc = Scanner::default();
        let t = Instant::now();
        let (mut bodies, mut after_trust_clear) = (0u64, None::<PState>);
        let mut saw_clear = false;
        for line in raw.lines() {
            let v: serde_json::Value = serde_json::from_str(line).expect("jsonl");
            if v["run"] != run || v["osc"] != "7501" {
                continue;
            }
            let body = v["body"].as_str().expect("body");
            let bytes = format!("\x1b]7501;{body}\x07");
            // 같은 Claude 프로세스 = 전경 그룹 고정(4242).
            ingest_fg(&mut st, sc.feed(bytes.as_bytes()), t, true, Some(4242));
            if body != "?" {
                bodies += 1;
            }
            if body == "state=clear" && !saw_clear {
                saw_clear = true;
            } else if saw_clear && after_trust_clear.is_none() && body != "state=clear" {
                after_trust_clear = st.summary().map(|(_, r)| r.state);
            }
        }
        assert!(saw_clear, "{run}: 원자료에 신뢰 창 clear 가 없다(전제)");
        assert_eq!(after_trust_clear, Some(PState::Idle), "{run}: 신뢰 창 clear 뒤 첫 보고(idle)가 버려졌다");
        assert_eq!(st.unsolicited, 0, "{run}: 질의에 답한 생애의 보고를 묻지 않은 보고로 셌다");
        assert_eq!(st.answered, 1, "{run}");
        // C 의 권한 창 msg 는 원자료에서 경로를 가렸다(<redacted-path> · 허용 밖 바이트 = 그 쌍만 무시) — 보고 자체는 받는다.
        assert_eq!((st.reports, st.discarded), (bodies, 0), "{run}");
        assert!(st.life_answered, "{run}: clear 보고가 생애를 끝냈다");
    }
}

#[test]
fn foreground_group_change_ends_the_life() {
    let mut st = Store::default();
    let mut sc = Scanner::default();
    let t = Instant::now();
    let mut f = |st: &mut Store, b: &[u8], fg: Option<i32>| ingest_fg(st, sc.feed(b), t, true, fg);
    f(&mut st, b"\x1b]7501;?\x07", Some(100));
    f(&mut st, b"\x1b]7501;state=working:app=claude-code\x07", Some(100));
    assert_eq!((st.len(), st.life_pgid), (1, Some(100)), "같은 전경 그룹의 보고는 받는다");
    // 에이전트가 끝나고(감시 틱 전) 다른 프로그램(codex · 셸 printf)이 전경을 잡았다.
    f(&mut st, b"\x1b]7501;state=blocked:kind=permission:app=codex\x07", Some(200));
    assert_eq!((st.len(), st.unsolicited, st.life_answered), (0, 1, false), "다음 프로그램에 응답 표식이 넘어갔다");
    assert_eq!(st.last_life_end.map(|(w, _)| w), Some("foreground process group changed"));
    // 끝난 생애는 옛 그룹으로 돌아와도 되살아나지 않는다 — 다시 물어야 받는다.
    f(&mut st, b"\x1b]7501;state=idle\x07", Some(100));
    assert_eq!((st.len(), st.unsolicited), (0, 2));
    f(&mut st, b"\x1b]7501;?\x07\x1b]7501;state=idle\x07", Some(200));
    assert_eq!((st.len(), st.life_pgid), (1, Some(200)), "새 질의 응답 = 새 생애");
    // 전경 그룹을 모르면(윈 · 시스템 콜 실패) 그룹 대조를 하지 않는다(종전 동작 · 한계 문서).
    f(&mut st, b"\x1b]7501;state=working\x07", None);
    assert_eq!((st.len(), st.unsolicited), (1, 2));
    let d = diag_wire(&st, t);
    assert_eq!((d["life_answered"].as_bool(), d["last_life_end"].as_str()), (Some(true), Some("foreground process group changed")));
}

#[test]
fn shell_prompt_ends_the_life() {
    let mut st = Store::default();
    let t = Instant::now();
    feed_raw(&mut st, b"\x1b]7501;?\x07\x1b]7501;state=idle:app=claude-code\x07", t);
    assert_eq!((st.len(), st.life_answered), (1, true));
    // 셸 프롬프트 = 그 프로그램은 끝났다 → idle 기록은 남지만(규격: working·blocked 만 지움) 응답 표식은 꺼진다.
    feed_raw(&mut st, b"\x1b]133;A\x07\x1b]7501;state=blocked:kind=permission:app=fake\x07", t);
    assert_eq!((st.len(), st.unsolicited, st.life_answered), (1, 1, false), "셸로 돌아온 뒤 printf 보고를 받았다");
    assert_eq!(st.summary().map(|(_, r)| r.state), Some(PState::Idle));
    assert_eq!(st.last_life_end.map(|(w, _)| w), Some("shell prompt (OSC 133;A)"));
}

/// 실 PTY: 좌석 프로세스가 질의 → 보고(받음) 뒤 자식에게 전경을 넘기고(`tcsetpgrp`) 그 자식이 보고 → 받지 않는다.
/// reader 가 실제로 `foreground_pgid_now` 를 `ingest_fg` 에 넘기는지(배선)를 잰다.
/// ★TICKET=cysr-1118-debug ①(깜빡이 고침 · 시험만 · 제품 판정·단언 그대로): 종전 파이썬은 첫 보고 0.4초 뒤 **제 시계로** 전경을 넘겼고,
///   시험은 FIRST 를 본 뒤 200ms 쉬고 첫 단언을 했다 — 그 사이 시험 프로세스가 밀리면(CI 러너 · 시험 수천 개 동시) 자식 보고가 먼저 읽혀
///   생애가 끝난 뒤 단언해 `(1, 0, false)` 로 붉었다(rc13 macos-rust-pack 원문과 같은 값). 대조군 = 시험 프로세스만 멈췄다 풀기
///   (450ms 멈춤 · 50ms 돌림 · 파이썬 자식은 안 멈춤): 고치기 전 4/10 붉음(전부 `(1, 0, false)`).
///   → 넘기기를 시각이 아니라 **순서**에 묶는다: 시험이 첫 단언을 마친 뒤 `go` 파일을 만들고, 파이썬은 그것을 본 뒤에만 넘긴다
///   (20초 안에 못 보면 넘기지 않고 끝난다 = 둘째 전제 단언이 붉음 · 고아 없음).
/// ★TICKET=debug-cysr-ci-flaky-1126 F4(깜빡이 고침 · 시험만 · 제품 판정·단언 그대로): 종전 파이썬은 그룹 만들기를 부모(`setpgid(pid,pid)`)와
///   자식(`setpgid(0,0)`)이 **동시에** 했다 — macOS 는 둘이 겹치면 한쪽에 EPERM 을 준다(같은 꼴 20,000회 = 부모 44 + 자식 약 58 · 0.5%).
///   그러면 파이썬이 Traceback 으로 죽어 「자식 보고 출력이 나오지 않았다(전제)」로 붉었고(v1.1.20 1,300회 중 3), 부모가 죽은 경우 자식은
///   제 쓰기 끝을 쥔 채 `read` 에서 영영 기다려 고아로 남았다. → 그룹은 **자식만** 만들고 둘째 관으로 「만들었다」를 알린 뒤에야
///   부모가 전경을 넘긴다(순서 고정 · 같은 대조 20,000회 = 0) · 자식은 쓰기 끝을 닫아 부모가 죽으면 EOF 로 끝난다(고아 0).
#[cfg(unix)]
#[test]
fn live_seat_foreground_handoff_ends_the_life() {
    if std::env::var("CYS_PROGRAM_STATUS").as_deref() == Ok("0") {
        return;
    }
    let g = crate::governance::PACK_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    crate::delivery::tests::isolate_state_dir_for_thread("ps7501fg");
    let dir = std::env::temp_dir().join(format!("cys-ps7501fg-{}", std::process::id()));
    let _ = std::fs::create_dir_all(&dir);
    std::fs::write(dir.join("acl.json"), r#"{"default":"allow","rules":[]}"#).unwrap();
    std::env::set_var(cys::pack::ENV_PACK_DIR, &dir);
    let daemon = crate::state::Daemon::new(dir.join("cysd.sock"));
    daemon.activity.running.store(true, std::sync::atomic::Ordering::SeqCst);
    // 자식은 3초 뒤 스스로 끝난다(좌석 kill 이 다른 그룹의 자식을 못 거두어도 고아가 오래 남지 않게).
    // (Rust 의 `\` 줄 이음은 다음 줄 앞 공백을 지운다 → 들여쓰기가 있는 파이썬은 원시 문자열로.)
    let go = dir.join("go");
    let _ = std::fs::remove_file(&go);
    let py = r#"import os,signal,sys,time
w=lambda b: os.write(1,b)
go=sys.argv[1]
w(b'\x1b]7501;?\x07'); time.sleep(0.4)
w(b'\x1b]7501;state=working:app=first\x07FIRST')
end=time.time()+20
while not os.path.exists(go) and time.time()<end: time.sleep(0.02)
if not os.path.exists(go): os._exit(3)
signal.signal(signal.SIGTTOU, signal.SIG_IGN)
r,wp=os.pipe()
r2,w2=os.pipe()
pid=os.fork()
if pid==0:
    os.close(wp); os.setpgid(0,0); os.write(w2,b'x')
    if not os.read(r,1): os._exit(0)
    w(b'\x1b]7501;state=blocked:kind=permission:app=second\x07HANDED'); time.sleep(3); os._exit(0)
os.read(r2,1); os.tcsetpgrp(0,pid); os.write(wp,b'x'); time.sleep(3)
"#;
    let script = dir.join("fg.py");
    std::fs::write(&script, py).unwrap();
    let cmd = format!("python3 {} {}", script.display(), go.display());
    let s = crate::pty_test_support::retry_on_pty_exhaustion("ps7501 fg seat", || {
        daemon.create_surface(None, Some(cmd.clone()), None, Some("worker".into()), 24, 80)
    })
    .expect("create surface");
    daemon.surfaces.lock().unwrap().insert(s.id, s.clone());
    let wait_for = |needle: &str| {
        let deadline = Instant::now() + Duration::from_secs(15);
        while Instant::now() < deadline && !s.parser.lock().unwrap().screen().contents().contains(needle) {
            std::thread::sleep(Duration::from_millis(50));
        }
        std::thread::sleep(Duration::from_millis(200));
        s.parser.lock().unwrap().screen().contents().contains(needle)
    };
    // ★(codex 1R major 반영) reader 는 화면 파서를 먼저 먹이고(state.rs `process_chunk_isolated`) 그 뒤 전경 조회 + 7501 반영을 한다 —
    //   화면에 표식이 보여도 상태 반영 전일 수 있다. 그래서 「보고 n건이 받음이든 안 받음이든 처리됐다」(reports + unsolicited ≥ n)를 기다린 뒤
    //   단언한다(어느 쪽으로 처리됐는지는 단언이 가린다 — 기다림이 정답 쪽만 기다리지 않는다).
    let wait_reports = |n: u64| {
        let deadline = Instant::now() + Duration::from_secs(15);
        loop {
            let done = {
                let st = s.program_status.lock().unwrap();
                st.reports + st.unsolicited >= n
            };
            if done || Instant::now() >= deadline {
                return done;
            }
            std::thread::sleep(Duration::from_millis(20));
        }
    };
    assert!(wait_for("FIRST"), "첫 보고 출력이 나오지 않았다(전제 · python3 필요):\n{}", s.parser.lock().unwrap().screen().contents());
    assert!(wait_reports(1), "첫 보고가 상태에 반영되지 않았다(전제)");
    {
        let st = s.program_status.lock().unwrap();
        assert_eq!((st.answered, st.len(), st.life_pgid.is_some()), (1, 1, true), "같은 전경 그룹의 보고를 받지 않았다");
    }
    std::fs::write(&go, b"1").unwrap(); // 첫 단언 뒤에만 전경을 넘긴다(순서 고정 · 위 문서)
    assert!(wait_for("HANDED"), "자식 보고 출력이 나오지 않았다(전제)");
    assert!(wait_reports(2), "자식 보고가 상태에 반영되지 않았다(전제)");
    let st = s.program_status.lock().unwrap();
    assert_eq!((st.len(), st.unsolicited, st.life_answered), (0, 1, false), "전경을 넘겨받은 다른 그룹의 보고를 받았다");
    assert_eq!(st.last_life_end.map(|(w, _)| w), Some("foreground process group changed"));
    drop(st);
    if let Ok(mut c) = s.child.lock() {
        let _ = c.kill();
    }
    let _ = std::fs::remove_dir_all(&dir);
    drop(g);
}
