//! TICKET=cysr-seatkeep-t3 · 출력 폭주 실측(master#c125bc97 ③) — 합성 좌석이 큰 출력을 최대 속도로 낼 때 노브 끔/켬을 같은 식으로 잰다.
//! 기본 실행에서는 빠진다(`#[ignore]`) — `cargo test --bin cysd seat_flood_tests -- --ignored --nocapture --test-threads=1`
//! (노브 켬 = 같은 명령 앞에 `CYS_SEATKEEP=1`). 줄 수 = `T3_FLOOD_LINES`(기본 2,000,000 줄 × 101바이트 ≈ 202MB · PTY 가 \n → \r\n).
//! 받은 쪽 = 좌석 방송(`out_tx` · cysd 읽기 스레드가 파서에 먹인 그 조각) 구독자. 구독자가 늦어 방송에서 밀린 것(`Lagged`)은 따로 센다 —
//! 그것은 좌석 유실이 아니라 이 측정기의 지연이다.
#![cfg(unix)]

use crate::state::{now_epoch, Daemon};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

fn rss_kb(pid: u32) -> u64 {
    let out = std::process::Command::new("ps").args(["-o", "rss=", "-p", &pid.to_string()]).output();
    out.ok().and_then(|o| String::from_utf8_lossy(&o.stdout).trim().parse().ok()).unwrap_or(0)
}

#[test]
#[ignore]
fn t3_flood_lines_arrive_in_order() {
    let lines: u64 = std::env::var("T3_FLOOD_LINES").ok().and_then(|v| v.parse().ok()).unwrap_or(2_000_000);
    let dir = std::env::temp_dir().join(format!("cys-flood-{}-{}", std::process::id(), now_epoch().to_bits() % 1_000_000));
    std::fs::create_dir_all(&dir).unwrap();
    let daemon: Arc<Daemon> = Daemon::new(dir.join("cysd.sock"));
    // 1초 쉬고(구독 준비) 최대 속도로 쏟은 뒤 표지 · 그다음 오래 잔다(좌석 생존 확인용).
    let cmd = format!(
        "sleep 1; /usr/bin/perl -e 'my $p = \"x\" x 89; for my $i (1..{lines}) {{ printf(\"%010d %s\\n\", $i, $p) }} print \"FLOODDONE\\n\"; sleep 3600'"
    );
    let s = daemon.create_surface(None, Some(cmd), None, None, 24, 200).expect("좌석");
    let mut rx = s.out_tx.subscribe();
    let keeper = {
        #[cfg(target_os = "macos")]
        {
            s.seat_link.as_ref().map(|l| l.keeper_pid())
        }
        #[cfg(not(target_os = "macos"))]
        {
            None::<u32>
        }
    };
    // RSS 표본(200ms) — 이 시험 프로세스(= cysd 자리) · seatkeep.
    let stop = Arc::new(AtomicBool::new(false));
    let (me_peak, sk_peak) = (Arc::new(AtomicU64::new(0)), Arc::new(AtomicU64::new(0)));
    let sampler = {
        let (stop, me_peak, sk_peak) = (Arc::clone(&stop), Arc::clone(&me_peak), Arc::clone(&sk_peak));
        std::thread::spawn(move || {
            while !stop.load(Ordering::Relaxed) {
                me_peak.fetch_max(rss_kb(std::process::id()), Ordering::Relaxed);
                if let Some(k) = keeper {
                    sk_peak.fetch_max(rss_kb(k), Ordering::Relaxed);
                }
                std::thread::sleep(Duration::from_millis(200));
            }
        })
    };
    let (mut next, mut bytes, mut lagged, mut bad) = (1u64, 0u64, 0u64, 0u64);
    let mut first: Option<Instant> = None;
    let mut carry: Vec<u8> = Vec::new();
    let mut done = false;
    let deadline = Instant::now() + Duration::from_secs(600);
    while !done && Instant::now() < deadline {
        match rx.blocking_recv() {
            Ok(chunk) => {
                first.get_or_insert_with(Instant::now);
                bytes += chunk.len() as u64;
                carry.extend_from_slice(&chunk);
                while let Some(nl) = carry.iter().position(|c| *c == b'\n') {
                    let line: Vec<u8> = carry.drain(..=nl).collect();
                    let t = String::from_utf8_lossy(&line);
                    let t = t.trim_end_matches(['\r', '\n']);
                    if t == "FLOODDONE" {
                        done = true;
                        break;
                    }
                    if let Some(n) = t.get(..10).and_then(|d| d.parse::<u64>().ok()) {
                        if n != next {
                            bad += 1;
                        }
                        next = n + 1;
                    }
                }
            }
            Err(tokio::sync::broadcast::error::RecvError::Lagged(n)) => lagged += n,
            Err(_) => break,
        }
    }
    let elapsed = first.map(|t| t.elapsed()).unwrap_or_default();
    std::thread::sleep(Duration::from_millis(500));
    stop.store(true, Ordering::Relaxed);
    let _ = sampler.join();
    let alive = !s.exited.load(Ordering::Acquire) && unsafe { libc::kill(s.pid as i32, 0) } == 0;
    #[cfg(target_os = "macos")]
    let gap = s.seat_link.as_ref().map(|l| l.gap_bytes()).unwrap_or(0);
    #[cfg(not(target_os = "macos"))]
    let gap = 0u64;
    // write_stalled · evict 기록(seatkeep 교체 기록)
    let mut evicts = 0usize;
    let base = std::env::temp_dir().join(format!("cskt-{:x}", std::process::id())).join("seatkeep");
    if let Ok(rd) = std::fs::read_dir(&base) {
        for e in rd.flatten() {
            if e.path().extension().map(|x| x == "log").unwrap_or(false) {
                evicts += std::fs::read_to_string(e.path()).unwrap_or_default().matches("\"evict\"").count();
            }
        }
    }
    let knob = crate::seat_proc::seatkeep_enabled();
    let sent_bytes = lines * 102 + "FLOODDONE\r\n".len() as u64; // 줄 = 10 + 1 + 89 + \r\n
    eprintln!(
        "T3FLOOD knob={} lines={lines} done={done} last_seq={} out_of_order={bad} received_bytes={bytes} sent_bytes≈{sent_bytes} \
         seat_gap_bytes={gap} lagged_msgs={lagged} elapsed_s={:.2} MBps={:.1} cysd_rss_peak_mb={:.1} seatkeep_rss_peak_mb={:.1} evict_lines={evicts} seat_alive={alive}",
        if knob { "on" } else { "off" },
        next - 1,
        elapsed.as_secs_f64(),
        bytes as f64 / 1e6 / elapsed.as_secs_f64().max(1e-9),
        me_peak.load(Ordering::Relaxed) as f64 / 1024.0,
        sk_peak.load(Ordering::Relaxed) as f64 / 1024.0,
    );
    crate::seat_proc::kill_and_reap(&s.child);
    let _ = std::fs::remove_dir_all(&dir);
    assert!(done, "끝 표지를 못 받음");
    assert_eq!(lagged, 0, "측정기(방송 구독자)가 밀림 — 이 회차는 판정 불가");
    assert_eq!((bad, next - 1, gap), (0, lines, 0), "순서 어긋남·유실");
    assert!(alive, "좌석 사망");
}
