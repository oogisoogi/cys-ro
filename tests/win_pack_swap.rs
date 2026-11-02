//! 윈 실제 잠금 시험(TICKET=cysr-1111-atomic-swap-fix · CI windows-health): 공유 삭제 없이 연 파일이 있으면 폴더 rename 이 막힌다.
//! 윈 r7 에서 이 상태가 복사 뒤 원본 삭제로 넘어가 ~/.cys/pack 이 반쯤 지워졌다. 이제는 재시도 뒤 실패하고 아무것도 지우지 않는다.
#![cfg(windows)]

use cys::pack::{atomic_swap, pack_prev_dir, pack_swap_hold_dir};
use std::fs::{self, File, OpenOptions};
use std::os::windows::fs::OpenOptionsExt;
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::time::Duration;

const FILE_SHARE_READ: u32 = 1;

fn fixture(tag: &str) -> (PathBuf, PathBuf, PathBuf) {
    let base = std::env::temp_dir().join(format!("cys-win-swap-{tag}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&base);
    let dir = base.join("pack");
    let staging = base.join("staging");
    fs::create_dir_all(dir.join("bin")).unwrap();
    for n in ["a.txt", "bin/a.py", "bin/locked.py", "bin/z.py"] {
        fs::write(dir.join(n), "old").unwrap();
    }
    fs::create_dir_all(&staging).unwrap();
    fs::write(staging.join("a.txt"), "new").unwrap();
    let prev = pack_prev_dir(&dir);
    fs::create_dir_all(&prev).unwrap();
    fs::write(prev.join("a.txt"), "older").unwrap();
    (base, dir, staging)
}

fn lock(p: &Path) -> File {
    OpenOptions::new().read(true).share_mode(FILE_SHARE_READ).open(p).unwrap()
}

fn count(d: &Path) -> usize {
    fs::read_dir(d).unwrap().flatten().map(|e| if e.path().is_dir() { count(&e.path()) } else { 1 }).sum()
}

#[test]
fn locked_file_fails_the_swap_and_deletes_nothing() {
    let (base, dir, staging) = fixture("held");
    let h = lock(&dir.join("bin/locked.py"));
    let r = atomic_swap(&dir, &staging);
    println!("[measure] 잠긴 교체 결과 = {r:?}");
    let e = r.unwrap_err();
    assert!(e.contains("교체 안 함"), "{e}");
    assert_eq!(count(&dir), 4, "팩 파일 수 불변");
    assert_eq!(fs::read_to_string(pack_prev_dir(&dir).join("a.txt")).unwrap(), "older");
    assert!(staging.join("a.txt").exists());
    assert!(!pack_swap_hold_dir(&dir).exists());
    drop(h);
    atomic_swap(&dir, &staging).unwrap();
    assert_eq!(fs::read_to_string(dir.join("a.txt")).unwrap(), "new");
    assert_eq!(count(&pack_prev_dir(&dir)), 4, "옛 팩이 직전 세대로");
    let _ = fs::remove_dir_all(&base);
}

#[test]
fn lock_released_during_retry_completes_the_swap() {
    let (base, dir, staging) = fixture("released");
    let h = lock(&dir.join("bin/locked.py"));
    let t = std::thread::spawn(move || {
        std::thread::sleep(Duration::from_secs(1));
        drop(h);
    });
    atomic_swap(&dir, &staging).unwrap();
    t.join().unwrap();
    assert_eq!(fs::read_to_string(dir.join("a.txt")).unwrap(), "new");
    assert_eq!(count(&pack_prev_dir(&dir)), 4);
    let _ = fs::remove_dir_all(&base);
}

/// r9 F1(master#310d3d5b): 옛 데몬 트리의 자손이 팩 파일을 쥐고 있으면 상한까지 기다린 뒤 그것만 끝내고 교체가 선다.
/// 이 시험 프로세스가 「옛 데몬」 이다 — cmd 가 리다이렉트로 파일을 연 채 ping 을 돌린다(공유 삭제 없음 = 폴더 rename 이 막힌다).
#[test]
fn old_tree_holders_are_waited_then_ended_and_the_swap_completes() {
    use cys::pack_holders::{capture, clear_for_swap};
    let (base, dir, staging) = fixture("holders-ours");
    let target = dir.join("bin").join("locked.py");
    // raw_arg — 따옴표를 Rust 가 \" 로 바꾸면 cmd 가 못 읽는다(임시 폴더에는 빈칸이 없다).
    let mut child = std::process::Command::new("cmd")
        .raw_arg(format!("/c ping -n 120 127.0.0.1 >> {}", target.display()))
        .spawn()
        .unwrap();
    std::thread::sleep(Duration::from_secs(2));
    let old = capture(std::process::id());
    assert!(old.tree.contains(&(child.id(), old.snapshot.iter().find(|p| p.pid == child.id()).unwrap().start)));
    let t0 = std::time::Instant::now();
    let (sweep, others) = clear_for_swap(&dir, &old);
    println!("[measure] 정리 = {sweep:?} · 그 밖 = {others:?} · {:?}", t0.elapsed());
    assert!(t0.elapsed() >= cys::pack_holders::HOLDER_WAIT, "상한까지 기다린 뒤에만 끝낸다");
    assert!(sweep.killed.contains(&child.id()), "{sweep:?}");
    assert!(sweep.left.is_empty(), "{sweep:?}");
    assert!(child.wait().is_ok());
    atomic_swap(&dir, &staging).unwrap();
    assert_eq!(fs::read_to_string(dir.join("a.txt")).unwrap(), "new");
    let _ = fs::remove_dir_all(&base);
}

/// r9 F1: 옛 트리 밖 프로세스(사용자 앱 자리)는 팩 파일을 쥐고 있어도 끝내지 않는다 — 교체는 종전처럼 실패하고 팩은 그대로다.
/// 바깥 cmd 가 `start` 로 띄우고 바로 끝나 홀더의 부모 고리가 옛 표에 없다.
#[test]
fn holders_outside_the_old_tree_are_left_alone() {
    use cys::pack_holders::{capture, clear_for_swap};
    let (base, dir, staging) = fixture("holders-other");
    let old = capture(std::process::id());
    let target = dir.join("bin").join("locked.py");
    let status = std::process::Command::new("cmd")
        .raw_arg(format!("/c start \"\" /min cmd /c \"ping -n 120 127.0.0.1 >> {}\"", target.display()))
        .status()
        .unwrap();
    assert!(status.success());
    std::thread::sleep(Duration::from_secs(3));
    let (sweep, others) = clear_for_swap(&dir, &old);
    println!("[measure] 정리 = {sweep:?} · 그 밖 = {others:?}");
    assert_eq!(sweep, cys::pack_holders::Sweep::default(), "옛 트리 밖은 기다리지도 끝내지도 않는다");
    assert!(!others.is_empty(), "홀더는 기록된다");
    let e = atomic_swap(&dir, &staging).unwrap_err();
    assert!(e.contains("교체 안 함"), "{e}");
    assert_eq!(count(&dir), 4, "팩 파일 수 불변");
    for (pid, _) in &others {
        let _ = std::process::Command::new("taskkill").args(["/PID", &pid.to_string(), "/T", "/F"]).status();
    }
    std::thread::sleep(Duration::from_secs(1));
    let _ = fs::remove_dir_all(&base);
}
