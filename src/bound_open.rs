//! 뿌리 폴더 **안의** 파일을 링크를 따라 밖으로 새지 않게 연다 — 윈도우 판(TICKET=cysr-1118-ui ①-4).
//!
//! 왜 있나: 대화 화면이 마스터 세션 기록(`<설정 폴더>/projects/<슬러그>/<세션>.jsonl`)을 읽는데, 유닉스 판(`src-tauri/src/viewcore.rs`
//! `open_bound`)은 폴더 핸들에서 `openat + O_NOFOLLOW` 로 한 요소씩 열어 뿌리 밖·다른 파일로 가지 못한다. 윈도우엔 안정 std 에 같은 API 가
//! 없어 지금까지 **읽지 않았다**(`unsupported_platform` → 윈 대화 화면은 「전달됨」·답·진행 줄을 못 그림 · codex 4R major 「경로 재탐색
//! 대조는 바꿔치기를 못 막음」).
//!
//! 이 판의 방법 = 유닉스 판과 **같은 결속**(핸들 기준 상대 열기 · 경로 재해석 0):
//!  ① 뿌리(설정 폴더 · 데몬이 준 값 · 링크여도 따른다 = 유닉스 판과 같음)를 폴더 핸들로 연다 — 이 핸들을 끝까지 쥔다.
//!  ② 상대 요소마다 `NtCreateFile(OBJECT_ATTRIBUTES.RootDirectory = 앞 핸들, ObjectName = 이 요소 하나)` +
//!     `FILE_OPEN_REPARSE_POINT`(링크·접합을 **따르지 않고** 그 자체를 연다) · 중간 = `FILE_DIRECTORY_FILE` · 마지막 = `FILE_NON_DIRECTORY_FILE`.
//!  ③ 연 요소마다 속성을 핸들로 읽어 reparse point 면 `symlinked_path`(= 유닉스 `O_NOFOLLOW` 의 ELOOP).
//!  뿌리 이름을 도중에 바꿔치기해도 이미 쥔 뿌리 핸들 아래에서만 찾으므로 다른 뿌리로 가지 않는다(codex 1R blocking ①).
//!  최종 경로 문자열 비교를 쓰지 않는다 — 대소문자 접기 비교가 대소문자 구분 폴더의 형제 뿌리를 같다고 보는 우회가 있었다(codex 1R blocking ②).
//! 한계(정직): 하드 링크는 유닉스 판과 같이 막지 않는다(같은 볼륨 · 그 파일 쓰기 권한 필요 · 유닉스 판도 O_NOFOLLOW 로 못 막는 같은 축).
//! 도메인 개념(대화 화면·세션)을 모르는 leaf 다 — 거부 사유 코드는 유닉스 판과 같은 낱말(`outside_config_dir` · `bad_component` ·
//! `no_config_dir` · `no_file` · `symlinked_path` · `not_a_file`).

use std::path::{Component, Path};

/// 상대 요소 검사(순수 · 모든 플랫폼) — 보통 이름만 · 비어 있지 않음 · 윈도 특수 글자(`:` 대체 스트림 · `\`·`/` · 끝 점·공백 = 윈도가 지워 다른 이름이 됨) 0.
pub fn rel_parts(root: &Path, expected: &Path) -> Result<Vec<String>, &'static str> {
    let rel = expected.strip_prefix(root).map_err(|_| "outside_config_dir")?;
    let mut out = Vec::new();
    for c in rel.components() {
        let Component::Normal(n) = c else { return Err("bad_component") };
        let s = n.to_str().ok_or("bad_component")?;
        if s.is_empty() || s.contains([':', '\\', '/', '\0']) || s.ends_with('.') || s.ends_with(' ') {
            return Err("bad_component");
        }
        out.push(s.to_owned());
    }
    if out.is_empty() {
        return Err("bad_component");
    }
    Ok(out)
}

/// NTSTATUS → 거부 사유(순수 · 유닉스 판 errno 대응과 같은 뜻): 없음 = `no_file` · 중간 요소가 폴더 아님 = `symlinked_path`(유닉스 ENOTDIR) ·
/// 마지막 요소가 폴더 = `not_a_file` · 링크에서 멈춤 = `symlinked_path` · 그 밖 = `no_file`.
pub fn status_reason(status: i32, last: bool) -> &'static str {
    const NOT_FOUND: i32 = 0xC000_0034_u32 as i32; // STATUS_OBJECT_NAME_NOT_FOUND
    const PATH_NOT_FOUND: i32 = 0xC000_003A_u32 as i32; // STATUS_OBJECT_PATH_NOT_FOUND
    const NOT_A_DIRECTORY: i32 = 0xC000_0103_u32 as i32; // STATUS_NOT_A_DIRECTORY
    const FILE_IS_A_DIRECTORY: i32 = 0xC000_00BA_u32 as i32; // STATUS_FILE_IS_A_DIRECTORY
    const STOPPED_ON_SYMLINK: i32 = 0x8000_002D_u32 as i32; // STATUS_STOPPED_ON_SYMLINK
    match status {
        NOT_FOUND | PATH_NOT_FOUND => "no_file",
        NOT_A_DIRECTORY => "symlinked_path",
        FILE_IS_A_DIRECTORY if last => "not_a_file",
        STOPPED_ON_SYMLINK => "symlinked_path",
        _ => "no_file",
    }
}

/// 뿌리 아래 파일 열기(윈도우) — 위 머리 주석 ①~③.
#[cfg(windows)]
pub fn open_file_under(root: &Path, expected: &Path) -> Result<std::fs::File, &'static str> {
    let parts = rel_parts(root, expected)?;
    open_rel(open_root(root)?, &parts)
}

#[cfg(windows)]
const SHARE_ALL: u32 = windows_sys::Win32::Storage::FileSystem::FILE_SHARE_READ
    | windows_sys::Win32::Storage::FileSystem::FILE_SHARE_WRITE
    | windows_sys::Win32::Storage::FileSystem::FILE_SHARE_DELETE; // Claude Code 가 쓰는 중인 파일 — 쓰기·이름 바꾸기를 막지 않는다

/// ① 뿌리 = 폴더 핸들(데몬이 준 값 · 따라감). 이 핸들 아래에서만 찾는다.
#[cfg(windows)]
pub fn open_root(root: &Path) -> Result<std::os::windows::io::OwnedHandle, &'static str> {
    use std::os::windows::fs::{MetadataExt, OpenOptionsExt};
    use windows_sys::Win32::Storage::FileSystem::{FILE_ATTRIBUTE_DIRECTORY, FILE_FLAG_BACKUP_SEMANTICS, FILE_READ_ATTRIBUTES, FILE_TRAVERSE, SYNCHRONIZE};
    let rootf = std::fs::OpenOptions::new()
        .access_mode(FILE_TRAVERSE | FILE_READ_ATTRIBUTES | SYNCHRONIZE)
        .share_mode(SHARE_ALL)
        .custom_flags(FILE_FLAG_BACKUP_SEMANTICS)
        .open(root)
        .map_err(|_| "no_config_dir")?;
    if rootf.metadata().map(|m| m.file_attributes() & FILE_ATTRIBUTE_DIRECTORY == 0).unwrap_or(true) {
        return Err("no_config_dir");
    }
    Ok(rootf.into())
}

/// ②③ 쥔 뿌리 핸들에서 상대 요소를 하나씩 reparse 를 따르지 않고 연다.
#[cfg(windows)]
pub fn open_rel(root: std::os::windows::io::OwnedHandle, parts: &[String]) -> Result<std::fs::File, &'static str> {
    use std::os::windows::ffi::OsStrExt;
    use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle};
    use windows_sys::Wdk::Foundation::OBJECT_ATTRIBUTES;
    use windows_sys::Wdk::Storage::FileSystem::{
        NtCreateFile, FILE_DIRECTORY_FILE, FILE_NON_DIRECTORY_FILE, FILE_OPEN, FILE_OPEN_REPARSE_POINT, FILE_SYNCHRONOUS_IO_NONALERT,
    };
    use windows_sys::Win32::Foundation::{HANDLE, UNICODE_STRING};
    use windows_sys::Win32::Storage::FileSystem::{
        GetFileInformationByHandle, BY_HANDLE_FILE_INFORMATION, FILE_ATTRIBUTE_DIRECTORY, FILE_ATTRIBUTE_REPARSE_POINT, FILE_GENERIC_READ,
        FILE_READ_ATTRIBUTES, FILE_TRAVERSE, SYNCHRONIZE,
    };
    use windows_sys::Win32::System::IO::IO_STATUS_BLOCK;
    const OBJ_CASE_INSENSITIVE: u32 = 0x40; // Win32 기본과 같은 이름 찾기(찾기는 쥔 폴더 핸들 안에서만 — 뿌리 밖으로 못 감)

    fn attrs_of(h: HANDLE) -> Option<u32> {
        // SAFETY: 살아 있는 핸들 · 구조체는 0 으로 채운 출력 칸.
        let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
        (unsafe { GetFileInformationByHandle(h, &mut info) } != 0).then_some(info.dwFileAttributes)
    }

    let share = SHARE_ALL;
    if parts.is_empty() {
        return Err("bad_component");
    }
    let mut parent: OwnedHandle = root;
    for (i, name) in parts.iter().enumerate() {
        let last = i + 1 == parts.len();
        let wide: Vec<u16> = std::ffi::OsStr::new(name).encode_wide().collect();
        let bytes = u16::try_from(wide.len() * 2).map_err(|_| "bad_component")?;
        let uname = UNICODE_STRING { Length: bytes, MaximumLength: bytes, Buffer: wide.as_ptr() as *mut u16 };
        let oa = OBJECT_ATTRIBUTES {
            Length: std::mem::size_of::<OBJECT_ATTRIBUTES>() as u32,
            RootDirectory: parent.as_raw_handle() as HANDLE,
            ObjectName: &uname,
            Attributes: OBJ_CASE_INSENSITIVE,
            SecurityDescriptor: std::ptr::null(),
            SecurityQualityOfService: std::ptr::null(),
        };
        // SAFETY: 출력 칸은 0 으로 채움 · OBJECT_ATTRIBUTES·UNICODE_STRING 은 이 호출 동안 살아 있는 지역값을 가리킨다.
        let mut iosb: IO_STATUS_BLOCK = unsafe { std::mem::zeroed() };
        let mut h: HANDLE = std::ptr::null_mut();
        let (access, kind) = if last { (FILE_GENERIC_READ, FILE_NON_DIRECTORY_FILE) } else { (FILE_TRAVERSE | FILE_READ_ATTRIBUTES | SYNCHRONIZE, FILE_DIRECTORY_FILE) };
        let st = unsafe {
            NtCreateFile(&mut h, access, &oa, &mut iosb, std::ptr::null(), 0, share, FILE_OPEN, kind | FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT, std::ptr::null(), 0)
        };
        if st < 0 || h.is_null() {
            return Err(status_reason(st, last));
        }
        // SAFETY: 방금 받은 유일한 소유 핸들.
        let owned = unsafe { OwnedHandle::from_raw_handle(h as _) };
        let a = attrs_of(owned.as_raw_handle() as HANDLE).ok_or("no_file")?;
        if a & FILE_ATTRIBUTE_REPARSE_POINT != 0 {
            return Err("symlinked_path");
        }
        if last && a & FILE_ATTRIBUTE_DIRECTORY != 0 {
            return Err("not_a_file");
        }
        parent = owned; // 앞 핸들은 여기서 닫힌다(자식 핸들이 그 객체를 이미 결속)
    }
    Ok(std::fs::File::from(parent))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn rel_parts_accepts_plain_names_only() {
        let root = PathBuf::from("/cfg");
        assert_eq!(rel_parts(&root, &root.join("projects").join("C--a").join("s1.jsonl")).unwrap(), vec!["projects", "C--a", "s1.jsonl"]);
        assert_eq!(rel_parts(&root, Path::new("/other/x.jsonl")).unwrap_err(), "outside_config_dir");
        assert_eq!(rel_parts(&root, &root).unwrap_err(), "bad_component");
        assert_eq!(rel_parts(&root, &root.join("a").join("..").join("b")).unwrap_err(), "bad_component");
        assert_eq!(rel_parts(&root, &root.join("x.jsonl:alt")).unwrap_err(), "bad_component", "대체 데이터 스트림");
        assert_eq!(rel_parts(&root, &root.join("x.jsonl.")).unwrap_err(), "bad_component", "끝 점");
        assert_eq!(rel_parts(&root, &root.join("x.jsonl ")).unwrap_err(), "bad_component", "끝 공백");
    }

    #[test]
    fn status_reasons_match_unix_words() {
        assert_eq!(status_reason(0xC000_0034_u32 as i32, true), "no_file");
        assert_eq!(status_reason(0xC000_003A_u32 as i32, false), "no_file");
        assert_eq!(status_reason(0xC000_0103_u32 as i32, false), "symlinked_path", "중간 요소가 파일 = 유닉스 ENOTDIR");
        assert_eq!(status_reason(0xC000_00BA_u32 as i32, true), "not_a_file");
        assert_eq!(status_reason(0x8000_002D_u32 as i32, true), "symlinked_path");
        assert_eq!(status_reason(0xC000_0022_u32 as i32, true), "no_file", "권한 없음 등 = 없음 취급");
    }

    /// 윈도우 실기(windows-health 레인 · 필터 `bound_open::tests::win_tests::` 따로 셈) — 실제 파일·폴더·접합(mklink /J)·파일 심볼릭 링크·뿌리 바꿔치기.
    #[cfg(windows)]
    mod win_tests {
        use super::super::*;
        use std::io::{Read, Write};
        use std::path::PathBuf;

        fn base(tag: &str) -> PathBuf {
            let b = std::env::temp_dir().join(format!("cys-bound-open-{tag}-{}", std::process::id()));
            let _ = std::fs::remove_dir_all(&b);
            std::fs::create_dir_all(&b).unwrap();
            b
        }
        fn junction(link: &Path, target: &Path) -> bool {
            std::process::Command::new("cmd").args(["/C", "mklink", "/J"]).arg(link).arg(target).output().map(|o| o.status.success()).unwrap_or(false)
        }
        fn layout(b: &Path) -> (PathBuf, PathBuf) {
            let cfg = b.join("cfg");
            let dir = cfg.join("projects").join("C--a");
            std::fs::create_dir_all(&dir).unwrap();
            std::fs::write(dir.join("s1.jsonl"), b"{\"type\":\"user\"}\n").unwrap();
            (cfg, dir)
        }

        #[test]
        fn exact_file_opens_and_reads_and_reasons_match_unix() {
            let b = base("ok");
            let (cfg, dir) = layout(&b);
            let mut f = open_file_under(&cfg, &dir.join("s1.jsonl")).expect("정상 파일");
            let mut s = String::new();
            f.read_to_string(&mut s).unwrap();
            assert!(s.contains("user"));
            assert!(open_file_under(&cfg, &cfg.join("PROJECTS").join("c--A").join("S1.jsonl")).is_ok(), "대소문자 다른 철자도 같은 파일(윈 기본 · 쥔 뿌리 안)");
            assert_eq!(open_file_under(&cfg, &dir.join("missing.jsonl")).unwrap_err(), "no_file");
            assert_eq!(open_file_under(&cfg, &dir).unwrap_err(), "not_a_file", "마지막 요소가 폴더");
            assert_eq!(open_file_under(&cfg, &dir.join("s1.jsonl").join("x")).unwrap_err(), "symlinked_path", "중간 요소가 파일 = 유닉스 ENOTDIR");
            assert_eq!(open_file_under(&b.join("nope"), &b.join("nope").join("x")).unwrap_err(), "no_config_dir");
            assert_eq!(open_file_under(&cfg, &b.join("outside.jsonl")).unwrap_err(), "outside_config_dir");
            // 쓰는 중인 파일(Claude Code 가 붙여 쓰는 꼴)도 열리고, 연 동안 상대의 쓰기를 막지 않는다
            let w = std::fs::OpenOptions::new().append(true).open(dir.join("s1.jsonl")).unwrap();
            let g = open_file_under(&cfg, &dir.join("s1.jsonl")).expect("쓰는 중에도 열림");
            (&w).write_all(b"{}\n").expect("연 동안 쓰기 허용");
            drop((g, w));
            let _ = std::fs::remove_dir_all(&b);
        }

        #[test]
        fn junction_in_the_middle_is_refused() {
            let b = base("junc");
            let cfg = b.join("cfg");
            let secret = b.join("secret");
            std::fs::create_dir_all(cfg.join("projects")).unwrap();
            std::fs::create_dir_all(&secret).unwrap();
            std::fs::write(secret.join("s1.jsonl"), b"secret\n").unwrap();
            assert!(junction(&cfg.join("projects").join("C--a"), &secret), "mklink /J 실패 — 시험 환경 확인(판정 불가 = 적색)");
            let p = cfg.join("projects").join("C--a").join("s1.jsonl");
            assert!(std::fs::read(&p).is_ok(), "경로로는 접합을 따라 읽힌다(대조군)");
            assert_eq!(open_file_under(&cfg, &p).unwrap_err(), "symlinked_path", "중간 접합 = 뿌리 밖");
            let _ = std::fs::remove_dir_all(&b);
        }

        #[test]
        fn file_symlink_is_refused() {
            let b = base("lnk");
            let (cfg, dir) = layout(&b);
            std::fs::write(b.join("secret.jsonl"), b"secret\n").unwrap();
            let link = dir.join("s2.jsonl");
            // GitHub 윈 러너 = 관리자 → 파일 심볼릭 링크 생성 가능. 못 만들면 이 보안 검체는 판정 불가 = 적색(codex 1R major · 조용한 초록 금지).
            std::os::windows::fs::symlink_file(b.join("secret.jsonl"), &link).expect("symlink_file 실패 — 판정 불가(적색)");
            assert!(std::fs::read(&link).is_ok(), "경로로는 링크를 따라 읽힌다(대조군)");
            assert_eq!(open_file_under(&cfg, &link).unwrap_err(), "symlinked_path");
            let _ = std::fs::remove_dir_all(&b);
        }

        /// codex 1R blocking ①: 뿌리 핸들을 쥔 **뒤** 뿌리 이름을 바꾸고 다른 폴더를 그 이름에 두어도, 쥔 핸들로 연 파일은 옛 뿌리의 것이다
        /// (예전 판 = 뿌리 최종 경로만 기억하고 핸들을 닫은 뒤 경로로 다시 열어 새 뿌리의 파일을 열었다).
        #[test]
        fn root_swapped_after_open_still_reads_old_root() {
            let b = base("swap");
            let (cfg, _dir) = layout(&b);
            let evil = b.join("evil");
            std::fs::create_dir_all(evil.join("projects").join("C--a")).unwrap();
            std::fs::write(evil.join("projects").join("C--a").join("s1.jsonl"), b"evil\n").unwrap();
            let held = open_root(&cfg).expect("뿌리");
            std::fs::rename(&cfg, b.join("cfg-old")).expect("쥔 뿌리 이름 바꾸기(지우기 공유) — 실패 = 판정 불가(적색)");
            std::fs::rename(&evil, &cfg).expect("다른 폴더를 그 이름에");
            let parts: Vec<String> = ["projects", "C--a", "s1.jsonl"].iter().map(|x| x.to_string()).collect();
            let mut s = String::new();
            open_rel(held, &parts).expect("쥔 뿌리 아래 파일").read_to_string(&mut s).unwrap();
            assert!(s.contains("user") && !s.contains("evil"), "쥔 뿌리 핸들 기준 = 옛 뿌리 파일: {s:?}");
            let _ = std::fs::remove_dir_all(&b);
        }
    }
}
