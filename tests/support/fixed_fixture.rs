//! 통합 시험 공용 — 시험용 실행 파일을 **고정 자리에 한 번 만들고 재사용 · 지우지 않는다**(TICKET=cysr-test-gatekeeper-crash-1118).
//!
//! 왜: 시험마다 새 Mach-O 를 만들어(cc 빌드·복사) 실행한 뒤 상자 폴더째 지우면, 맥 보안 검사(syspolicyd)가 처음 실행된 새 파일을
//! 검사하는 도중 파일이 사라질 수 있다 — 11-18 syspolicyd SIGSEGV(`Universal::architecture` null) → tccd·WindowServer 정지 사슬의
//! 원인 후보. 그래서 자리는 `CARGO_TARGET_TMPDIR/cys-test-fixtures/<용도>/`(용도별 고정 이름 · 내용 해시 아님 = 디스크가 쌓이지 않음)이고,
//! 원문(또는 원본 크기·시각)이 바뀐 때만 임시 이름에 만든 뒤 rename 으로 갈아 끼운다(동시 시험 프로세스가 반쪽 파일을 보지 않음).
#![allow(dead_code)]

use std::path::{Path, PathBuf};
use std::sync::Mutex;

static BUILD: Mutex<()> = Mutex::new(());

/// 용도별 고정 폴더(없으면 만든다).
pub fn fixture_dir(purpose: &str) -> PathBuf {
    let d = Path::new(env!("CARGO_TARGET_TMPDIR")).join("cys-test-fixtures").join(purpose);
    std::fs::create_dir_all(&d).unwrap();
    d
}

/// C 원문 `src_text` 를 `/usr/bin/cc` 로 `<용도>/<name>` 에 빌드한다 — 저장된 원문이 같고 실행 파일이 있으면 그대로 돌려준다.
pub fn cc_fixed(purpose: &str, name: &str, src_text: &str) -> PathBuf {
    let _g = BUILD.lock().unwrap_or_else(|e| e.into_inner());
    let dir = fixture_dir(purpose);
    let (exe, src) = (dir.join(name), dir.join(format!("{name}.c")));
    if exe.is_file() && std::fs::read_to_string(&src).ok().as_deref() == Some(src_text) {
        return exe;
    }
    let tag = std::process::id();
    // 임시 원문 이름은 `.c` 로 끝나야 한다 — 아니면 cc 가 확장자를 몰라 링커 입력(오브젝트)으로 넘겨 링크가 실패한다(979d148b 통제 실행 적색).
    let (te, ts) = (dir.join(format!("{name}.part-{tag}")), dir.join(format!("{name}.part-{tag}.c")));
    std::fs::write(&ts, src_text).unwrap();
    assert!(
        std::process::Command::new("/usr/bin/cc").args(["-w", "-o"]).arg(&te).arg(&ts).status().unwrap().success(),
        "고정 자리 시험 실행 파일 빌드 실패: {name}"
    );
    std::fs::rename(&te, &exe).unwrap();
    std::fs::rename(&ts, &src).unwrap();
    exe
}

/// 빌드된 실행 파일 `from` 을 `<용도>/<같은 이름>` 에 둔다 — **내용(바이트 전수 비교)이 같으면 손대지 않는다**(시각·크기 기준 아님).
/// 3ba23763 통제 실행 2회전에서 rah-bin 이 다시 써졌다: 작업 폴더(worktree)에서는 `.git` 이 파일이라 build.rs 의
/// `rerun-if-changed=.git/HEAD` 경로가 없어 cargo 가 매번 빌드 스크립트를 다시 돌리고, 빌드 번호(UTC 분 포함)가 바뀌어 cys·cysd 를
/// 다시 링크한다 → 옛 「크기 + 수정 시각」 기록이 어긋나 복사가 다시 일어났다.
/// 그래서 ① 같은 inode 거나 바이트가 전부 같으면 그대로 돌려준다(쓰기 0) ② 다르면 **복사가 아니라 하드 링크**(cargo 가 이미 만든
/// 같은 파일 · 새 Mach-O 내용 0)를 임시 이름에 걸고 rename 으로 갈아 끼운다. 지우지 않는다.
pub fn copied_fixed(purpose: &str, from: &Path) -> PathBuf {
    use std::os::unix::fs::MetadataExt;
    let _g = BUILD.lock().unwrap_or_else(|e| e.into_inner());
    let dir = fixture_dir(purpose);
    let name = from.file_name().unwrap().to_string_lossy().into_owned();
    let dst = dir.join(&name);
    if let (Ok(a), Ok(b)) = (std::fs::metadata(from), std::fs::metadata(&dst)) {
        if (a.dev(), a.ino()) == (b.dev(), b.ino()) || (a.len() == b.len() && same_bytes(from, &dst)) {
            return dst;
        }
    }
    let tmp = dir.join(format!("{name}.part-{}", std::process::id()));
    let _ = std::fs::remove_file(&tmp); // 이 프로세스가 앞서 남긴 링크 이름뿐(실행된 적 없는 이름)
    std::fs::hard_link(from, &tmp).unwrap();
    std::fs::rename(&tmp, &dst).unwrap();
    dst
}

/// 두 파일의 바이트가 전부 같은가(1 MiB 조각 비교 · 해시보다 강하고 디버그 빌드에서도 빠르다).
fn same_bytes(a: &Path, b: &Path) -> bool {
    use std::io::Read;
    let (Ok(mut fa), Ok(mut fb)) = (std::fs::File::open(a), std::fs::File::open(b)) else { return false };
    let (mut ba, mut bb) = (vec![0u8; 1 << 20], vec![0u8; 1 << 20]);
    loop {
        let (Ok(na), Ok(nb)) = (read_full(&mut fa, &mut ba), read_full(&mut fb, &mut bb)) else { return false };
        if na != nb || ba[..na] != bb[..nb] {
            return false;
        }
        if na == 0 {
            return true;
        }
    }
    fn read_full(f: &mut std::fs::File, buf: &mut [u8]) -> std::io::Result<usize> {
        let mut n = 0;
        while n < buf.len() {
            match f.read(&mut buf[n..])? {
                0 => break,
                k => n += k,
            }
        }
        Ok(n)
    }
}
