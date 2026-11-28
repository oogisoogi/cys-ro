//! (1.1.16 · cysr-1116-s2 · codex 3R blocking) 화면 행 커서 + `surface.attach history_since` 지킴이 시험.
//!
//! 지키는 것:
//! ① 이음매 = 결정론 — 커서 뒤 화면 위로 밀려난 행 + 「받는 xterm 행 수」 만큼의 줄 내림 + 지금 화면 스냅숏을 새 화면(행 수가 달라도)에 먹이면
//!    스크롤백 = 서버가 커서 뒤 밀려낸 행 그대로(빠짐·겹침·빈 줄 끼어듦 0) · 화면 = 서버 화면.
//! ② 10,000행(파서 스크롤백) 밖으로 밀려난 구간 = 「잘림」 · 상한으로 자른 것도 「잘림」(조용한 손실 0).
//! ③ 파서 세대가 바뀌면(파서 교체 · RIS) 또는 커서가 지금보다 앞이면 = 모르는 커서.
//! ④ `history_since` 없는 attach = ack · 바이트가 종전과 같다(구 소비자 무영향).
//! ⑤ 실제 좌석(reader 스레드 · run_attach)에서 같은 성질.

use crate::state::{pack_screen_cursor, unpack_screen_cursor, Daemon};
use serde_json::json;
use std::sync::atomic::Ordering;
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, AsyncReadExt, BufReader};

fn feed(p: &mut vt100::Parser, bytes: &[u8]) {
    p.process(bytes);
}

/// 줄마다 유일 표지 `L<n>.` — 몇 줄은 색 · 몇 줄은 폭을 넘겨 접힘.
fn lines(from: usize, to: usize) -> Vec<u8> {
    let mut out = Vec::new();
    for i in from..to {
        let body = if i % 7 == 0 {
            format!("\x1b[31mL{i}.\x1b[0m red")
        } else if i % 11 == 0 {
            format!("L{i}.{}", "w".repeat(130)) // 80칸에서 두 행으로 접힌다
        } else {
            format!("L{i}. plain")
        };
        out.extend(body.as_bytes());
        out.extend(b"\r\n");
    }
    out
}

/// 바이트에서 표지 번호를 차례로(색 이스케이프는 표지 사이에만 있다).
fn markers(text: &str) -> Vec<usize> {
    let mut out = Vec::new();
    let mut rest = text;
    while let Some(p) = rest.find('L') {
        rest = &rest[p + 1..];
        let digits: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
        if !digits.is_empty() && rest[digits.len()..].starts_with('.') {
            out.push(digits.parse().unwrap());
        }
    }
    out
}

/// 받는 쪽 파서의 스크롤백 전체 + 화면 글자(표지 세기용).
fn client_text(c: &vt100::Parser) -> (Vec<u8>, String) {
    let (ep, _) = c.screen().scroll_cursor();
    let (sb, _, _, _) = c.screen().scrollback_formatted_since(ep, 0, usize::MAX).unwrap();
    (sb, c.screen().contents())
}

fn strip(bytes: &[u8]) -> String {
    String::from_utf8_lossy(&strip_ansi_escapes::strip(bytes)).into_owned()
}

/// 서버가 run_attach 에서 쓰는 순서 그대로 — 밀려난 행 · 줄 내림(받는 쪽 행 수) · 스냅숏.
fn attach_stream(server: &vt100::Parser, epoch: u64, since: u64, client_rows: u16) -> (Vec<u8>, u64, bool) {
    let (hist, _, n, truncated) = server.screen().scrollback_formatted_since(epoch, since, 5_000).unwrap();
    let mut out = hist;
    if n > 0 {
        out.extend(b"\r\n".repeat(client_rows as usize));
    }
    out.extend(server.screen().contents_formatted());
    (out, n, truncated)
}

#[test]
fn seam_replay_has_no_gap_no_overlap_for_any_client_height() {
    for client_rows in [24u16, 35, 60] {
        let mut s = vt100::Parser::new(24, 80, crate::state::SCROLLBACK_LINES);
        feed(&mut s, &lines(0, 100));
        let (epoch, cursor) = s.screen().scroll_cursor();
        assert!(cursor > 0);
        feed(&mut s, &lines(100, 400));
        let (stream, n, truncated) = attach_stream(&s, epoch, cursor, client_rows);
        assert!(!truncated);
        let (_, now) = s.screen().scroll_cursor();
        assert_eq!(n, now - cursor, "커서 뒤 밀려난 행 전부");

        let mut c = vt100::Parser::new(client_rows, 80, crate::state::SCROLLBACK_LINES);
        feed(&mut c, &stream);
        let (sb, screen) = client_text(&c);
        // 스크롤백 = 서버가 커서 뒤 밀려낸 행과 바이트까지 같다(색 포함 · 빈 행 끼어듦 0)
        let (want_sb, _, _, _) = s.screen().scrollback_formatted_since(epoch, cursor, usize::MAX).unwrap();
        assert_eq!(sb, want_sb, "rows={client_rows}: 스크롤백이 서버의 커서 뒤 밀려난 행과 다르다");
        // 화면 = 서버 화면(받는 쪽이 더 크면 위쪽 서버 행 수만큼)
        let srv: Vec<String> = s.screen().contents().lines().map(str::to_string).collect();
        let cli: Vec<String> = screen.lines().map(str::to_string).collect();
        assert_eq!(cli[..srv.len().min(cli.len())], srv[..srv.len().min(cli.len())], "rows={client_rows}: 화면");
        // 표지 = 커서 때 화면 맨 윗줄 표지부터 마지막까지 빠짐·겹침 없이 한 번씩
        let all = markers(&(strip(&sb) + &screen));
        let mut sorted = all.clone();
        sorted.dedup();
        assert_eq!(all, sorted, "rows={client_rows}: 표지 겹침");
        assert_eq!(*all.last().unwrap(), 399);
        assert!(all.windows(2).all(|w| w[1] == w[0] + 1), "rows={client_rows}: 표지 빠짐 {all:?}");
    }
}

#[test]
fn rows_beyond_parser_scrollback_are_reported_truncated() {
    let mut s = vt100::Parser::new(5, 40, 50);
    let (epoch, c0) = s.screen().scroll_cursor();
    assert_eq!(c0, 0);
    feed(&mut s, &lines(0, 200));
    let (_, start, n, truncated) = s.screen().scrollback_formatted_since(epoch, c0, 5_000).unwrap();
    assert!(truncated, "10,000(여기 50)행 밖 = 잘림");
    assert_eq!(n, 50);
    let (_, now) = s.screen().scroll_cursor();
    assert_eq!(start, now - 50);
    // 상한으로 잘라도 잘림 · 최근 쪽을 남긴다
    let (_, start2, n2, t2) = s.screen().scrollback_formatted_since(epoch, now - 30, 10).unwrap();
    assert_eq!((n2, start2, t2), (10, now - 10, true));
    // 커서 = 지금 = 0 행 · 잘림 아님
    let (b, _, n3, t3) = s.screen().scrollback_formatted_since(epoch, now, 10).unwrap();
    assert_eq!((b.len(), n3, t3), (0, 0, false));
}

#[test]
fn new_parser_or_future_cursor_is_unknown() {
    let mut a = vt100::Parser::new(5, 40, 100);
    feed(&mut a, &lines(0, 20));
    let (ea, ra) = a.screen().scroll_cursor();
    let b = vt100::Parser::new(5, 40, 100);
    let (eb, _) = b.screen().scroll_cursor();
    assert_ne!(ea, eb, "새 파서 = 새 세대");
    assert!(b.screen().scrollback_formatted_since(ea, 0, 10).is_none(), "다른 세대 커서 = 모름");
    assert!(a.screen().scrollback_formatted_since(ea, ra + 1, 10).is_none(), "지금보다 앞 커서 = 모름");
    // RIS(ESC c) = 화면을 새로 만든다 → 세대 바뀜
    feed(&mut a, b"\x1bc");
    assert_ne!(a.screen().scroll_cursor().0, ea);
    // 묶은 수 왕복 · JS 정확 범위(2^53) 안
    let c = pack_screen_cursor(ea, ra);
    assert!(c < (1u64 << 53));
    assert_eq!(unpack_screen_cursor(c), Some((ea & 0x1FFF, ra)));
    assert_eq!(unpack_screen_cursor(1u64 << 60), None);
}

#[test]
fn alternate_screen_does_not_move_the_main_cursor() {
    let mut s = vt100::Parser::new(5, 40, 100);
    feed(&mut s, &lines(0, 10));
    let before = s.screen().scroll_cursor();
    feed(&mut s, b"\x1b[?1049h");
    feed(&mut s, &lines(10, 40));
    assert_eq!(s.screen().scroll_cursor(), before, "대체 화면 출력은 주 격자 스크롤백에 안 쌓인다(xterm 과 같음)");
    feed(&mut s, b"\x1b[?1049l");
}

fn iso(tag: &str) -> Arc<Daemon> {
    static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    let dir = std::env::temp_dir().join(format!("cys-ah-{tag}-{}-{seq}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    let _ = std::fs::create_dir_all(&dir);
    Daemon::new(dir.join(format!("ah-{}-{seq}.sock", std::process::id())))
}

fn wait_until(mut f: impl FnMut() -> bool) {
    let t0 = std::time::Instant::now();
    while !f() {
        assert!(t0.elapsed() < std::time::Duration::from_secs(20), "시한 초과");
        std::thread::sleep(std::time::Duration::from_millis(20));
    }
}

/// run_attach 를 메모리 관에 붙여 ack 한 줄 + 그 뒤 `quiet` 동안 온 바이트를 받는다.
async fn attach_once(d: &Arc<Daemon>, sid: u64, history: Option<(u64, u16)>) -> (serde_json::Value, Vec<u8>) {
    let (mut srv, cli) = tokio::io::duplex(1 << 22);
    let ack = cys::ok_response(&json!(1), json!({"attached": sid}));
    let d2 = Arc::clone(d);
    let task = tokio::spawn(async move { crate::run_attach(&d2, &mut srv, ack, sid, history).await });
    let mut r = BufReader::new(cli);
    let mut line = String::new();
    tokio::time::timeout(std::time::Duration::from_secs(10), r.read_line(&mut line)).await.expect("ack 시한").unwrap();
    let mut bytes = Vec::new();
    let mut buf = vec![0u8; 1 << 16];
    loop {
        match tokio::time::timeout(std::time::Duration::from_millis(400), r.read(&mut buf)).await {
            Ok(Ok(n)) if n > 0 => bytes.extend_from_slice(&buf[..n]),
            _ => break,
        }
    }
    task.abort();
    (serde_json::from_str(line.trim()).unwrap(), bytes)
}

fn kill(s: &crate::state::Surface) {
    if let Ok(mut c) = s.child.lock() {
        let _ = c.kill();
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn attach_without_history_is_byte_identical_to_before() {
    let d = iso("plain");
    let s = d.create_surface(None, Some("printf 'A1\\nB2\\n'; sleep 30".into()), None, None, 24, 80).expect("create");
    let s2 = Arc::clone(&s);
    tokio::task::spawn_blocking(move || wait_until(|| s2.line_count.load(Ordering::Relaxed) >= 2)).await.unwrap();
    std::thread::sleep(std::time::Duration::from_millis(200));
    let snap = s.parser.lock().unwrap().screen().contents_formatted();
    let (ack, bytes) = attach_once(&d, s.id, None).await;
    // 프레임 칸(`_flen`·`_pv` = write_line 이 모든 줄에 붙이는 것)을 뺀 본문이 종전 ack 그대로
    let mut body = ack.clone();
    body.as_object_mut().unwrap().retain(|k, _| !k.starts_with('_'));
    assert_eq!(body, json!({"id": 1, "ok": true, "result": {"attached": s.id}}), "ack 에 새 칸이 없다");
    assert_eq!(bytes, snap, "인자 없는 attach = 종전과 같은 첫 바이트(스냅숏만)");
    kill(&s);
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn real_seat_history_since_list_cursor_replays_without_gap() {
    let d = iso("seat");
    let s = d
        .create_surface(None, Some("sleep 0.3; i=0; while [ $i -lt 300 ]; do echo L$i.; i=$((i+1)); done; sleep 30".into()), None, None, 24, 80)
        .expect("create");
    // 「미룰 때」 목록의 커서(생성 직후 = 이 파서 세대 · 0행)
    let cursor = s.screen_cursor.load(Ordering::Relaxed);
    let (ep_now, rows0) = s.parser.lock().unwrap().screen().scroll_cursor();
    assert_eq!(unpack_screen_cursor(cursor), Some((ep_now & 0x1FFF, rows0)), "생성 직후에도 미러가 이 파서 세대");
    let s2 = Arc::clone(&s);
    tokio::task::spawn_blocking(move || wait_until(|| s2.line_count.load(Ordering::Relaxed) >= 300)).await.unwrap();
    std::thread::sleep(std::time::Duration::from_millis(200));
    for client_rows in [24u16, 40] {
        let (ack, bytes) = attach_once(&d, s.id, Some((cursor, client_rows))).await;
        let h = &ack["result"]["history"];
        assert_eq!(h["status"], json!("ok"), "{ack}");
        assert!(h["rows"].as_u64().unwrap() >= 300 - 24, "{ack}");
        let mut c = vt100::Parser::new(client_rows, 80, crate::state::SCROLLBACK_LINES);
        feed(&mut c, &bytes);
        let (sb, screen) = client_text(&c);
        let all = markers(&(strip(&sb) + &screen));
        assert_eq!(all, (0..300).collect::<Vec<_>>(), "rows={client_rows}: 빠짐·겹침 없이 0..300");
    }
    // 모르는 커서(다른 세대) · 잘림 아님 표시
    let bogus = pack_screen_cursor(ep_now.wrapping_add(1), 0);
    let (ack, bytes) = attach_once(&d, s.id, Some((bogus, 24))).await;
    assert_eq!(ack["result"]["history"]["status"], json!("unknown_cursor"), "{ack}");
    assert_eq!(bytes, s.parser.lock().unwrap().screen().contents_formatted(), "모르는 커서 = 기록 없이 스냅숏만");
    kill(&s);
}

#[test]
fn dispatch_parses_history_params_only_when_given() {
    let d = iso("dispatch");
    let s = d.create_surface(None, Some("sleep 30".into()), None, None, 24, 80).expect("create");
    let req = |p: serde_json::Value| cys::Request { id: json!(1), method: "surface.attach".into(), params: p };
    match crate::handlers::dispatch(&d, req(json!({"surface_id": s.id})), None) {
        crate::handlers::Reply::Attach { history, .. } => assert_eq!(history, None),
        _ => panic!("attach 아님"),
    }
    match crate::handlers::dispatch(&d, req(json!({"surface_id": s.id, "history_since": 7, "history_rows": 33})), None) {
        crate::handlers::Reply::Attach { history, .. } => assert_eq!(history, Some((7, 33))),
        _ => panic!("attach 아님"),
    }
    // 목록에 화면 행 커서 1칸(더하기)
    let list = match crate::handlers::dispatch(&d, cys::Request { id: json!(1), method: "surface.list".into(), params: json!({}) }, None) {
        crate::handlers::Reply::Single(v) => v,
        _ => panic!(),
    };
    let row = list["result"]["surfaces"].as_array().unwrap().iter().find(|r| r["surface_id"] == json!(s.id)).cloned().unwrap();
    assert!(row["screen_cursor"].as_u64().is_some(), "{row}");
    kill(&s);
}

/// (master#b4d5c092 조건 ⑤) 락 안 작업 상한 — 밀려난 행이 상한(5,000)보다 많아도 락 안에서 **복사**하는 것은 최근 5,000행뿐(서식은 락 밖)이고 결과는 「잘림」.
/// 걸린 시간은 측정값으로만 찍는다(시간 단언 = 부하성 거짓 붉음 · 근거 = 행 수 상한). 락은 이 좌석 파서 락뿐(다른 좌석 배달과 무관).
#[test]
fn attach_history_under_lock_is_capped_at_max_rows() {
    let mut s = vt100::Parser::new(50, 200, crate::state::SCROLLBACK_LINES);
    let (epoch, c0) = s.screen().scroll_cursor();
    let mut bytes = Vec::new();
    for i in 0..12_000 {
        bytes.extend(format!("\x1b[3{}m{:0>190}\x1b[0m\r\n", i % 8, i).as_bytes());
    }
    feed(&mut s, &bytes);
    let t0 = std::time::Instant::now();
    let snap = crate::attach_history_snapshot(s.screen(), pack_screen_cursor(epoch, c0)); // 락 안 몫 = 행 사본
    let in_lock = t0.elapsed();
    let t1 = std::time::Instant::now();
    let (info, out) = crate::attach_history_format(snap); // 락 밖 몫 = 서식
    let outside = t1.elapsed();
    assert_eq!(info["status"], json!("truncated"), "{info}");
    assert_eq!(info["rows"], json!(crate::ATTACH_HISTORY_MAX_ROWS as u64));
    println!("[measure] 5,000행×200칸(색) — 락 안 사본 {in_lock:?} · 락 밖 서식 {outside:?} · {} 바이트", out.len());
}

// ── codex 4R(master#9af88457) ─────────────────────────────────────────────────────────────

/// ② 높이 줄임으로 글자 있는 아래 행을 버리면 세대가 바뀐다 → 옛 커서 = 모르는 커서(조용한 손실 0) · 빈 행만 버리면 그대로.
#[test]
fn shrink_dropping_content_invalidates_cursor_blank_shrink_keeps_it() {
    let mut s = vt100::Parser::new(10, 40, 100);
    feed(&mut s, b"top\r\n");
    let before = s.screen().scroll_cursor();
    s.set_size(6, 40); // 아래 4행 = 빈 행
    assert_eq!(s.screen().scroll_cursor(), before, "빈 행만 버림 = 커서 유효");
    feed(&mut s, b"\x1b[6;1Hbottom-line");
    let c = s.screen().scroll_cursor();
    s.set_size(4, 40); // 글자 있는 6번째 행을 버림
    let after = s.screen().scroll_cursor();
    assert_ne!(after.0, c.0, "글자 있는 행을 버림 = 새 세대");
    let (info, bytes) = crate::attach_history(s.screen(), pack_screen_cursor(c.0, c.1));
    assert_eq!((info["status"].clone(), bytes.len()), (json!("unknown_cursor"), 0));
}

/// ③ ED 3(스크롤백 지우기) = 데몬 스크롤백도 지운다 — 지운 앞부분은 다시 그리지 않고(살아 있는 터미널과 같음) 잘림도 아니다 · 그 뒤 밀려난 행만.
#[test]
fn ed3_clears_daemon_scrollback_and_replay_matches_live_terminal() {
    let mut s = vt100::Parser::new(5, 40, crate::state::SCROLLBACK_LINES);
    let (epoch, c0) = s.screen().scroll_cursor();
    feed(&mut s, &lines(0, 50));
    feed(&mut s, b"\x1b[3J");
    feed(&mut s, &lines(50, 80));
    let (info, bytes) = crate::attach_history(s.screen(), pack_screen_cursor(epoch, c0));
    assert_eq!(info["status"], json!("ok"), "{info}");
    let all = markers(&strip(&bytes));
    // 지울 때 스크롤백에 있던 0..46 은 되살아나지 않는다 · 그때 화면에 있던 46..50(5행 화면)은 지워지지 않고 뒤에 밀려 올라간다
    assert_eq!(all.first(), Some(&46), "지운 행이 되살아났다: {all:?}");
    // 살아 있는 터미널 대조 — 처음부터 붙어 같은 바이트를 받은 터미널의 스크롤백 = 다시 그린 행
    let mut live = vt100::Parser::new(5, 40, crate::state::SCROLLBACK_LINES);
    feed(&mut live, &lines(0, 50));
    feed(&mut live, b"\x1b[3J");
    feed(&mut live, &lines(50, 80));
    let (lsb, _) = client_text(&live);
    assert_eq!(markers(&strip(&lsb)), all);
}

/// ④ 락 안 상한 = 칸 수 — 폭 1,000칸 좌석은 1,000,000칸 / 1,000 = 1,000행까지만 복사(잘림) · 화면 사본 서식 = 원본 서식과 바이트 같음.
#[test]
fn cell_cap_and_visible_clone_formats_identically() {
    let mut s = vt100::Parser::new(20, 1000, crate::state::SCROLLBACK_LINES);
    let (epoch, c0) = s.screen().scroll_cursor();
    let mut b = Vec::new();
    for i in 0..3000 {
        b.extend(format!("\x1b[3{}mL{i}.\x1b[0m{}\r\n", i % 8, "x".repeat(900)).as_bytes());
    }
    feed(&mut s, &b);
    let (info, _) = crate::attach_history(s.screen(), pack_screen_cursor(epoch, c0));
    assert_eq!((info["status"].clone(), info["rows"].clone()), (json!("truncated"), json!(crate::ATTACH_HISTORY_MAX_CELLS as u64 / 1000)));
    // 화면 사본 = 원본과 같은 바이트(주 화면 · 색 · 커서 숨김 · 대체 화면)
    for extra in [&b"\x1b[?25l"[..], b"\x1b[1;31mred\x1b[0m", b"\x1b[?1049hALT\x1b[2;3Hzz", b"\x1b[?1049l\x1b]0;title\x07"] {
        feed(&mut s, extra);
        assert_eq!(s.screen().visible_clone().unwrap().contents_formatted(), s.screen().contents_formatted());
    }
}

/// ① 기록 연결이 broadcast 큐(256)를 넘기면 놓침 표지를 마지막에 쓰고 닫는다 · 인자 없는 연결은 표지 없음(종전).
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn lagged_history_connection_ends_with_marker_plain_does_not() {
    for with_history in [true, false] {
        let d = iso(if with_history { "lag-h" } else { "lag-p" });
        let s = d
            .create_surface(None, Some("sleep 0.6; i=0; while [ $i -lt 4000 ]; do printf '%0200d\\n' $i; i=$((i+1)); done; sleep 30".into()), None, None, 24, 80)
            .expect("create");
        let cursor = s.screen_cursor.load(Ordering::Relaxed);
        // 작은 관(1 KiB) — 받는 쪽이 읽지 않는 동안 run_attach 가 쓰기에서 막혀 rx 를 못 비운다 → 큐 256 넘침
        let (mut srv, cli) = tokio::io::duplex(1024);
        let ack = cys::ok_response(&json!(1), json!({"attached": s.id}));
        let d2 = Arc::clone(&d);
        let sid = s.id;
        let hist = with_history.then_some((cursor, 24u16));
        let mut task = tokio::spawn(async move { crate::run_attach(&d2, &mut srv, ack, sid, hist).await });
        let s2 = Arc::clone(&s);
        tokio::task::spawn_blocking(move || wait_until(|| s2.line_count.load(Ordering::Relaxed) >= 4000)).await.unwrap();
        let mut r = BufReader::new(cli);
        let mut all = Vec::new();
        let mut buf = vec![0u8; 1 << 16];
        loop {
            match tokio::time::timeout(std::time::Duration::from_millis(1500), r.read(&mut buf)).await {
                Ok(Ok(n)) if n > 0 => all.extend_from_slice(&buf[..n]),
                Ok(_) => break,  // EOF = 데몬이 닫음
                Err(_) => break, // 조용함
            }
        }
        // ★TICKET=debug-cysr-ci-flaky-1126 F3(깜빡이 고침 · 시험만 · 제품·단언 그대로): 종전 `task.is_finished()` 는 관이 닫힌 것(EOF)을 본
        //   **직후** 완료 표식을 읽었다 — tokio 는 미래값이 끝나 `srv` 가 버려진(=EOF 가 보인) **뒤에야** 완료 표식을 세운다
        //   (tokio 1.52.3 harness.rs `poll_future` → `store_output` → `complete`). 그 틈에 작업 스레드가 밀리면 「표지 true · 닫힘 false」로
        //   붉었다(11-25 516 부하 대조 1/40 · 원문 같음). → 완료를 시각이 아니라 **사건**으로 기다린다: 기록 연결은 5초 안에 끝나야 하고
        //   (안 끝나면 닫힘 false = 붉음 그대로), 인자 없는 연결은 종전처럼 기다리지 않는다(단언에 쓰지 않음).
        let ended = with_history && tokio::time::timeout(std::time::Duration::from_secs(5), &mut task).await.is_ok();
        task.abort();
        kill(&s);
        let marker = all.ends_with(crate::ATTACH_LAGGED_MARKER);
        if with_history {
            assert!(marker && ended, "기록 연결: 놓침 표지로 끝나고 닫힘 (표지 {marker} · 닫힘 {ended} · {} 바이트)", all.len());
        } else {
            assert!(!all.windows(crate::ATTACH_LAGGED_MARKER.len()).any(|w| w == crate::ATTACH_LAGGED_MARKER), "인자 없는 연결에 표지");
        }
    }
}
