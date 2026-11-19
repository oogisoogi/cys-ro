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

fn feed(store: &mut Store, bytes: &[u8], now: Instant) -> Ingest {
    let mut sc = Scanner::default();
    ingest(store, sc.feed(bytes), now)
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
    step(&mut st, b"\x1b]133;A\x07\x1b]7501;state=working\x07", None, ms(8), false);
    let v = st.version;
    st.wipe(false, "x", ms(9));
    assert_eq!(st.version, v + 1, "지움도 판을 올린다");
    st.wipe(false, "x", ms(10));
    assert_eq!(st.version, v + 1, "지울 것이 없으면 판 불변");
}
