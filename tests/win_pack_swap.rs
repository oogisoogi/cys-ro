//! 윈 실제 잠금 시험(TICKET=cysr-1111-atomic-swap-fix · CI windows-health): 공유 삭제 없이 연 파일이 있으면 폴더 rename 이 막힌다.
//! 윈 r7 에서 이 상태가 복사 뒤 원본 삭제로 넘어가 ~/.cys/pack 이 반쯤 지워졌다. 이제는 재시도 뒤 실패하고 아무것도 지우지 않는다.
#![cfg(windows)]

use cys::pack::{atomic_swap, pack_prev_dir, pack_swap_hold_dir};
use std::fs::{self, File, OpenOptions};
use std::os::windows::fs::OpenOptionsExt;
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
