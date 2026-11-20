//! TICKET=cysr-seatkeep-t3 · 입력→화면 왕복 지연(브리프 §5 · master#c125bc97 덧붙임) — `surface.send_text` RPC(입력 관문 포함 ·
//! 전경 질의가 끼면 그 왕복까지)로 넣은 표지가 cysd 화면 사본(vt100 파서)에 보일 때까지. 좌석 = `cat`(단말 반향 + cat 출력).
//! 기본 실행에서 빠진다(`#[ignore]`) — `cargo test --bin cysd seat_latency_tests -- --ignored --nocapture --test-threads=1`
//! (노브 켬 = 앞에 `CYS_SEATKEEP=1`). 횟수 = `T3_LAT_N`(기본 300).
#![cfg(unix)]

use crate::state::{now_epoch, Daemon};
use serde_json::json;
use std::sync::Arc;
use std::time::{Duration, Instant};

#[test]
#[ignore]
fn t3_input_to_screen_roundtrip() {
    let n: usize = std::env::var("T3_LAT_N").ok().and_then(|v| v.parse().ok()).unwrap_or(300);
    let dir = std::env::temp_dir().join(format!("cys-lat-{}-{}", std::process::id(), now_epoch().to_bits() % 1_000_000));
    std::fs::create_dir_all(&dir).unwrap();
    let d: Arc<Daemon> = Daemon::new(dir.join("cysd.sock"));
    let s = d.create_surface(None, Some("exec cat".into()), None, None, 40, 200).expect("좌석");
    std::thread::sleep(Duration::from_millis(800));
    let mut lat: Vec<f64> = Vec::with_capacity(n);
    let mut fails = 0usize;
    for i in 0..n {
        let tok = format!("q{:05}z", i);
        let t0 = Instant::now();
        let req = cys::Request { id: json!(i), method: "surface.send_text".into(), params: json!({"surface_id": s.id, "text": format!("{tok}\r")}) };
        let resp = match crate::handlers::dispatch(&d, req, None) {
            crate::handlers::Reply::Single(v) => v,
            _ => json!({"non_single": true}),
        };
        if i == 0 {
            eprintln!("T3LAT first response: {resp}");
        }
        let deadline = t0 + Duration::from_secs(3);
        let mut seen = false;
        while Instant::now() < deadline {
            let text = s.parser.lock().unwrap_or_else(|e| e.into_inner()).screen().contents();
            if text.matches(&tok).count() >= 2 {
                seen = true;
                break;
            }
            std::thread::sleep(Duration::from_micros(200));
        }
        if seen {
            lat.push(t0.elapsed().as_secs_f64() * 1000.0);
        } else {
            fails += 1;
        }
    }
    #[cfg(target_os = "macos")]
    let fgq = s.seat_link.as_ref().map(|l| l.fg_queries()).unwrap_or(0);
    #[cfg(not(target_os = "macos"))]
    let fgq = 0u64;
    lat.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let pct = |p: f64| lat.get(((lat.len() as f64 - 1.0) * p).round() as usize).copied().unwrap_or(f64::NAN);
    eprintln!(
        "T3LAT knob={} n={n} ok={} fails={fails} seatkeep_fg_queries={fgq} p50_ms={:.3} p90_ms={:.3} p99_ms={:.3} max_ms={:.3}",
        if crate::seat_proc::seatkeep_enabled() { "on" } else { "off" },
        lat.len(),
        pct(0.50),
        pct(0.90),
        pct(0.99),
        lat.last().copied().unwrap_or(f64::NAN)
    );
    crate::seat_proc::kill_and_reap(&s.child);
    let _ = std::fs::remove_dir_all(&dir);
    assert_eq!(fails, 0, "화면에 안 나타난 입력");
}
