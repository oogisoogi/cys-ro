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

/// 빌드된 실행 파일 `from` 의 사본을 `<용도>/<같은 이름>` 에 둔다 — 원본 크기·수정 시각이 기록과 같으면 재사용.
pub fn copied_fixed(purpose: &str, from: &Path) -> PathBuf {
    let _g = BUILD.lock().unwrap_or_else(|e| e.into_inner());
    let dir = fixture_dir(purpose);
    let name = from.file_name().unwrap().to_string_lossy().into_owned();
    let (dst, stamp) = (dir.join(&name), dir.join(format!("{name}.stamp")));
    let m = std::fs::metadata(from).unwrap();
    let want = format!("{} {:?}", m.len(), m.modified().unwrap());
    if dst.is_file() && std::fs::read_to_string(&stamp).ok().as_deref() == Some(want.as_str()) {
        return dst;
    }
    let tmp = dir.join(format!("{name}.part-{}", std::process::id()));
    std::fs::copy(from, &tmp).unwrap();
    std::fs::rename(&tmp, &dst).unwrap();
    std::fs::write(&stamp, want).unwrap();
    dst
}
