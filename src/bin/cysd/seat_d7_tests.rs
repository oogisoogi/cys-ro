//! TICKET=cysr-seatkeep-t3 · 브리프 §1-3(D7 남은 손자) — 좌석 리더·손자의 그룹·후손이 **닫기**와 **리더만 끝남**에서
//! 어떻게 되는지를 직접 PTY(지금 동작)에서 시험으로 고정한다. seatkeep 경유(노브 켬)도 같은 시험이 같은 결과를 내야 한다.
//!
//! 좌석 = `sh <script>` 한 개. 스크립트가 띄우는 것(전부 좌석 리더와 같은 프로세스 그룹 · 비대화형 sh 라 작업 제어 없음):
//! - `g0` 리더의 자식 · SIGHUP 기본 처리
//! - `g1` 리더의 자식 · SIGHUP 무시
//! - `o0` 고아(이중 fork — 부모 서브셸이 바로 끝나 launchd 로 넘어감 → 좌석 리더의 후손이 아니다) · SIGHUP 기본
//! - `o1` 고아 · SIGHUP 무시
//! 관측 = 각 pid 생존(`kill(pid, 0)`). 정리 = 시험이 기록한 pid 만 SIGKILL(자기가 띄운 것만).
#![cfg(unix)]

use crate::state::{now_epoch, Daemon};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

fn test_daemon(tag: &str) -> (Arc<Daemon>, PathBuf) {
    static SEQ: AtomicU64 = AtomicU64::new(0);
    let dir = std::env::temp_dir().join(format!(
        "cys-d7-{tag}-{}-{}-{}",
        std::process::id(),
        now_epoch().to_bits() % 1_000_000,
        SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    std::fs::create_dir_all(&dir).unwrap();
    (Daemon::new(dir.join("cysd.sock")), dir)
}

/// 리더 모양: `Default` = 끝에 `exec sleep`(SIGHUP 기본) · `IgnoreHup` = SIGHUP 무시하고 계속 삶 · `ExitNow` = 손자를 띄우고 바로 끝남.
#[derive(Clone, Copy, PartialEq, Debug)]
enum Leader {
    Default,
    IgnoreHup,
    ExitNow,
}

fn write_script(dir: &Path, out: &Path, leader: Leader) -> PathBuf {
    let tail = match leader {
        Leader::Default => "exec sleep 302",
        Leader::IgnoreHup => "trap '' HUP\nwhile :; do sleep 1; done",
        Leader::ExitNow => "exit 0",
    };
    let script = format!(
        "#!/bin/sh\nOUT='{out}'\n\
         sleep 300 & echo \"g0 $!\" >> \"$OUT\"\n\
         ( trap '' HUP; exec sleep 301 ) & echo \"g1 $!\" >> \"$OUT\"\n\
         ( sleep 303 & echo \"o0 $!\" >> \"$OUT\" )\n\
         ( ( trap '' HUP; exec sleep 304 ) & echo \"o1 $!\" >> \"$OUT\" )\n\
         echo \"leader $$\" >> \"$OUT\"\n\
         echo READY >> \"$OUT\"\n{tail}\n",
        out = out.display()
    );
    let p = dir.join("d7.sh");
    std::fs::write(&p, script).unwrap();
    p
}

fn read_pids(out: &Path) -> Option<Vec<(String, i32)>> {
    let text = std::fs::read_to_string(out).ok()?;
    if !text.lines().any(|l| l == "READY") {
        return None;
    }
    Some(
        text.lines()
            .filter_map(|l| {
                let mut it = l.split_whitespace();
                Some((it.next()?.to_string(), it.next()?.parse().ok()?))
            })
            .collect(),
    )
}

/// 살아 있음 = 신호를 받을 수 있고 **좀비가 아님**(회수 전 좀비는 `kill(pid, 0)` 이 0 을 돌려준다 — 끝난 것으로 센다).
fn alive(pid: i32) -> bool {
    if pid <= 0 || unsafe { libc::kill(pid, 0) } != 0 {
        return false;
    }
    let st = std::process::Command::new("ps").args(["-o", "stat=", "-p", &pid.to_string()]).output();
    match st {
        Ok(o) => {
            let t = String::from_utf8_lossy(&o.stdout);
            let t = t.trim();
            !(t.is_empty() || t.starts_with('Z'))
        }
        Err(_) => true,
    }
}

fn wait_for(limit: Duration, mut cond: impl FnMut() -> bool) -> bool {
    let t = Instant::now();
    while t.elapsed() < limit {
        if cond() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(25));
    }
    cond()
}

/// 이름 → 생존 표(정렬). 좀비 회수 시간을 주려고 짧게 기다린 뒤 잰다.
fn census(pids: &[(String, i32)]) -> Vec<(String, bool)> {
    std::thread::sleep(Duration::from_millis(400));
    let mut v: Vec<(String, bool)> = pids.iter().map(|(n, p)| (n.clone(), alive(*p))).collect();
    v.sort();
    v
}

fn cleanup(pids: &[(String, i32)], dir: &Path) {
    for (_, p) in pids {
        if *p > 0 {
            unsafe { libc::kill(*p, libc::SIGKILL) };
        }
    }
    let _ = std::fs::remove_dir_all(dir);
}

fn start_seat(leader: Leader) -> (Arc<Daemon>, Arc<crate::state::Surface>, Vec<(String, i32)>, PathBuf) {
    let (daemon, dir) = test_daemon(&format!("{leader:?}"));
    let out = dir.join("pids.txt");
    let script = write_script(&dir, &out, leader);
    let s = daemon
        .create_surface(None, Some(format!("sh '{}'", script.display())), None, None, 24, 80)
        .expect("좌석 생성");
    let mut pids = None;
    assert!(wait_for(Duration::from_secs(15), || {
        pids = read_pids(&out);
        pids.is_some()
    }), "스크립트 준비 표식이 안 옴");
    (daemon, s, pids.unwrap(), dir)
}

fn expect(got: &[(String, bool)], want: &[(&str, bool)], what: &str) {
    let want: Vec<(String, bool)> = {
        let mut v: Vec<(String, bool)> = want.iter().map(|(n, a)| (n.to_string(), *a)).collect();
        v.sort();
        v
    };
    assert_eq!(got, want.as_slice(), "{what}");
}

/// ⓐ 좌석 닫기(close-surface · 리더 SIGHUP 기본). 지금 동작 = 리더·리더의 자식은 전부 죽고(후손 SIGKILL + 리더 SIGHUP→SIGKILL),
/// 리더의 후손이 아닌 고아는 **SIGHUP 무시면 산다**(o1) · 기본이면 죽는다(o0 — 리더가 끝날 때 커널이 전경 그룹에 SIGHUP).
#[test]
fn d7_close_surface_leader_default() {
    let (daemon, s, pids, dir) = start_seat(Leader::Default);
    crate::governance::close_surface(&daemon, s.id, crate::governance::CloseCause::Reap).expect("닫기");
    let got = census(&pids);
    cleanup(&pids, &dir);
    eprintln!("D7 close/leader_default: {got:?}");
    expect(&got, &[("g0", false), ("g1", false), ("o0", false), ("o1", true), ("leader", false)], "닫기 · 리더 기본");
}

/// ⓐ' 좌석 닫기 · 리더가 SIGHUP 을 무시(유예 뒤 SIGKILL 로 끝남).
#[test]
fn d7_close_surface_leader_ignores_hup() {
    let (daemon, s, pids, dir) = start_seat(Leader::IgnoreHup);
    crate::governance::close_surface(&daemon, s.id, crate::governance::CloseCause::Reap).expect("닫기");
    let got = census(&pids);
    cleanup(&pids, &dir);
    eprintln!("D7 close/leader_ignores_hup: {got:?}");
    expect(&got, &[("g0", false), ("g1", false), ("o0", false), ("o1", true), ("leader", false)], "닫기 · 리더 HUP 무시");
}

/// ⓑ 좌석 리더만 끝남(스스로 exit 0). 지금 동작 = 좌석은 끝남(exited) · SIGHUP 기본 손자는 죽고 무시 손자는 산다 ·
/// 그 뒤 닫기는 리더가 이미 없어 후손 목록이 비므로 남은 손자를 건드리지 않는다.
#[test]
fn d7_leader_exits_alone() {
    let (daemon, s, pids, dir) = start_seat(Leader::ExitNow);
    assert!(wait_for(Duration::from_secs(10), || s.exited.load(Ordering::Acquire)), "리더 종료가 좌석 종료로 안 보임");
    let after_exit = census(&pids);
    crate::governance::close_surface(&daemon, s.id, crate::governance::CloseCause::Reap).expect("닫기");
    let after_close = census(&pids);
    cleanup(&pids, &dir);
    eprintln!("D7 leader_exit: after_exit={after_exit:?} after_close={after_close:?}");
    let want = [("g0", false), ("g1", true), ("o0", false), ("o1", true), ("leader", false)];
    expect(&after_exit, &want, "리더만 끝남 직후");
    expect(&after_close, &want, "리더만 끝난 뒤 닫기");
}
