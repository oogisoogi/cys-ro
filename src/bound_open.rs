//! 뿌리 폴더 **안의** 파일을 링크를 따라 밖으로 새지 않게 연다 — 윈도우 판(TICKET=cysr-1118-ui ①-4).
//!
//! 왜 있나: 대화 화면이 마스터 세션 기록(`<설정 폴더>/projects/<슬러그>/<세션>.jsonl`)을 읽는데, 유닉스 판(`src-tauri/src/viewcore.rs`
//! `open_bound`)은 폴더 핸들에서 `openat + O_NOFOLLOW` 로 한 요소씩 열어 뿌리 밖·다른 파일로 가지 못한다. 윈도우엔 같은 안정 API 가
//! 없어 지금까지 **읽지 않았다**(`unsupported_platform` → 윈 대화 화면은 「전달됨」·답·진행 줄을 못 그림 · codex 4R major 「경로 재탐색
//! 대조는 바꿔치기를 못 막음」).
//!
//! 이 판의 방법 = **연 핸들 자체를 대조**한다(경로를 다시 찾지 않음 → 확인·열기 사이 틈 0):
//!  ① 뿌리(설정 폴더 · 데몬이 준 값 · 링크여도 따른다 = 유닉스 판과 같음)의 최종 경로를 얻는다.
//!  ② 대상 파일을 `FILE_FLAG_OPEN_REPARSE_POINT` 로 연다 — 마지막 요소가 심볼릭 링크·접합(reparse point)이면 따르지 않고 그 자체를 연다.
//!  ③ 연 핸들의 속성: reparse point = `symlinked_path` · 폴더 = `not_a_file`.
//!  ④ 연 핸들의 최종 경로(`GetFinalPathNameByHandleW` · 정규화 · DOS 볼륨 이름)가 「뿌리 최종 경로 + 상대 요소」와 같아야 한다
//!     (ASCII 대소문자 무시 — NTFS 기본 · 상대 요소는 슬러그·세션 id·`projects` 라 ASCII). 중간 폴더가 링크·접합이면 최종 경로가 달라져 거부.
//!     바꿔치기가 있어도 대조 대상은 **이미 연 객체**라 다른 파일을 읽을 수 없다.
//! 한계(정직): 하드 링크는 유닉스 판과 같이 막지 않는다(같은 볼륨 · 같은 사용자 권한 필요 · 최종 경로가 다른 이름으로 나오면 거부 = 안전 쪽).
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

/// 최종 경로 대조(순수 · 모든 플랫폼) — `got` 이 `root_final` 아래 정확히 `parts` 인가(구분자 `\` · ASCII 대소문자 무시 · 앞뒤 다른 글자 0).
pub fn final_path_is(got: &str, root_final: &str, parts: &[String]) -> bool {
    let root = root_final.trim_end_matches('\\');
    let want = format!("{root}\\{}", parts.join("\\"));
    got.len() == want.len() && got.eq_ignore_ascii_case(&want)
}

/// 뿌리 아래 파일 열기(윈도우) — 위 머리 주석 ①~④.
#[cfg(windows)]
pub fn open_file_under(root: &Path, expected: &Path) -> Result<std::fs::File, &'static str> {
    use std::os::windows::fs::{MetadataExt, OpenOptionsExt};
    use std::os::windows::io::AsRawHandle;
    use windows_sys::Win32::Storage::FileSystem::{
        GetFinalPathNameByHandleW, FILE_ATTRIBUTE_DIRECTORY, FILE_ATTRIBUTE_REPARSE_POINT, FILE_FLAG_BACKUP_SEMANTICS,
        FILE_FLAG_OPEN_REPARSE_POINT, FILE_SHARE_DELETE, FILE_SHARE_READ, FILE_SHARE_WRITE,
    };

    fn final_path(f: &std::fs::File) -> Option<String> {
        let h = f.as_raw_handle();
        let mut buf = vec![0u16; 512];
        loop {
            // SAFETY: 살아 있는 핸들 · 버퍼 길이 전달(flags 0 = FILE_NAME_NORMALIZED | VOLUME_NAME_DOS).
            let n = unsafe { GetFinalPathNameByHandleW(h as _, buf.as_mut_ptr(), buf.len() as u32, 0) } as usize;
            if n == 0 {
                return None;
            }
            if n < buf.len() {
                return String::from_utf16(&buf[..n]).ok();
            }
            if n > 32_768 {
                return None;
            }
            buf.resize(n + 1, 0); // n = 필요한 길이(NUL 포함)
        }
    }
    let share = FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE; // Claude Code 가 쓰는 중인 파일 — 쓰기·이름 바꾸기를 막지 않는다
    let parts = rel_parts(root, expected)?;
    // ① 뿌리 = 폴더 핸들(따라감) → 최종 경로
    let rootf = std::fs::OpenOptions::new()
        .read(true)
        .share_mode(share)
        .custom_flags(FILE_FLAG_BACKUP_SEMANTICS)
        .open(root)
        .map_err(|_| "no_config_dir")?;
    if rootf.metadata().map(|m| m.file_attributes() & FILE_ATTRIBUTE_DIRECTORY == 0).unwrap_or(true) {
        return Err("no_config_dir");
    }
    let root_final = final_path(&rootf).ok_or("no_config_dir")?;
    drop(rootf);
    // ② 대상 = 마지막 요소 링크를 따르지 않고 연다
    let f = std::fs::OpenOptions::new()
        .read(true)
        .share_mode(share)
        .custom_flags(FILE_FLAG_OPEN_REPARSE_POINT)
        .open(expected)
        .map_err(|_| "no_file")?;
    // ③ 연 것의 속성
    let attrs = f.metadata().map_err(|_| "no_file")?.file_attributes();
    if attrs & FILE_ATTRIBUTE_REPARSE_POINT != 0 {
        return Err("symlinked_path");
    }
    if attrs & FILE_ATTRIBUTE_DIRECTORY != 0 {
        return Err("not_a_file");
    }
    // ④ 연 객체의 최종 경로 = 뿌리 최종 경로 + 상대 요소
    let got = final_path(&f).ok_or("no_file")?;
    if !final_path_is(&got, &root_final, &parts) {
        return Err("symlinked_path");
    }
    Ok(f)
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
    fn final_path_must_be_exactly_root_plus_parts() {
        let parts: Vec<String> = ["projects", "C--Users-x-p", "abc.jsonl"].iter().map(|s| s.to_string()).collect();
        let root = r"\\?\C:\Users\x\.claude";
        assert!(final_path_is(r"\\?\C:\Users\x\.claude\projects\C--Users-x-p\abc.jsonl", root, &parts));
        assert!(final_path_is(r"\\?\c:\users\X\.CLAUDE\projects\c--users-x-p\ABC.jsonl", root, &parts), "대소문자 무시");
        assert!(final_path_is(r"\\?\C:\Users\x\.claude\projects\C--Users-x-p\abc.jsonl", r"\\?\C:\Users\x\.claude\", &parts), "뿌리 끝 구분자");
        assert!(!final_path_is(r"\\?\D:\elsewhere\abc.jsonl", root, &parts), "접합 중간 폴더 = 다른 곳");
        assert!(!final_path_is(r"\\?\C:\Users\x\.claude\projects\C--Users-x-p\abc.jsonl.bak", root, &parts));
        assert!(!final_path_is(r"\\?\C:\Users\x\.claude\projects\other\abc.jsonl", root, &parts));
        assert!(!final_path_is(r"\\?\C:\Users\x\.claude2\projects\C--Users-x-p\abc.jsonl", root, &parts), "뿌리 접두만 같은 형제 폴더");
    }

    /// 윈도우 실기(windows-health 레인) — 실제 파일·폴더·접합(mklink /J)·파일 심볼릭 링크로 열기 판정.
    #[cfg(windows)]
    mod win_tests {
        use super::super::*;
        use std::io::Read;
        use std::path::PathBuf;

        fn base(tag: &str) -> PathBuf {
            let b = std::env::temp_dir().join(format!("cys-bound-open-{tag}-{}", std::process::id()));
            let _ = std::fs::remove_dir_all(&b);
            std::fs::create_dir_all(&b).unwrap();
            b
        }
        fn junction(link: &Path, target: &Path) -> bool {
            std::process::Command::new("cmd")
                .args(["/C", "mklink", "/J"])
                .arg(link)
                .arg(target)
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false)
        }

        #[test]
        fn exact_file_opens_and_reads() {
            let b = base("ok");
            let cfg = b.join("cfg");
            let dir = cfg.join("projects").join("C--a");
            std::fs::create_dir_all(&dir).unwrap();
            std::fs::write(dir.join("s1.jsonl"), b"{\"type\":\"user\"}\n").unwrap();
            let mut f = open_file_under(&cfg, &dir.join("s1.jsonl")).expect("정상 파일");
            let mut s = String::new();
            f.read_to_string(&mut s).unwrap();
            assert!(s.contains("user"));
            assert_eq!(open_file_under(&cfg, &dir.join("missing.jsonl")).unwrap_err(), "no_file");
            assert_eq!(open_file_under(&cfg, &dir).unwrap_err(), "not_a_file");
            assert_eq!(open_file_under(&b.join("nope"), &b.join("nope").join("x")).unwrap_err(), "no_config_dir");
            assert_eq!(open_file_under(&cfg, &b.join("outside.jsonl")).unwrap_err(), "outside_config_dir");
            // 쓰는 중인 파일(Claude Code 가 붙여 쓰는 꼴)도 열리고, 연 동안 상대의 쓰기를 막지 않는다
            let w = std::fs::OpenOptions::new().append(true).open(dir.join("s1.jsonl")).unwrap();
            let g = open_file_under(&cfg, &dir.join("s1.jsonl")).expect("쓰는 중에도 열림");
            use std::io::Write;
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
            assert!(junction(&cfg.join("projects").join("C--a"), &secret), "mklink /J 실패 — 시험 환경 확인");
            let p = cfg.join("projects").join("C--a").join("s1.jsonl");
            assert!(std::fs::read(&p).is_ok(), "경로로는 접합을 따라 읽힌다(대조군)");
            assert_eq!(open_file_under(&cfg, &p).unwrap_err(), "symlinked_path", "중간 접합 = 뿌리 밖");
            let _ = std::fs::remove_dir_all(&b);
        }

        #[test]
        fn file_symlink_is_refused_when_creatable() {
            let b = base("lnk");
            let cfg = b.join("cfg");
            let dir = cfg.join("projects").join("C--a");
            std::fs::create_dir_all(&dir).unwrap();
            std::fs::write(b.join("secret.jsonl"), b"secret\n").unwrap();
            let link = dir.join("s1.jsonl");
            // 파일 심볼릭 링크는 개발자 모드·권한이 있어야 만들어진다 — 못 만들면 이 갈래는 판정 대상이 없다(접합 시험이 중간 요소를 덮음)
            if std::os::windows::fs::symlink_file(b.join("secret.jsonl"), &link).is_ok() {
                assert!(std::fs::read(&link).is_ok(), "경로로는 링크를 따라 읽힌다(대조군)");
                assert_eq!(open_file_under(&cfg, &link).unwrap_err(), "symlinked_path");
            } else {
                eprintln!("[bound_open] symlink_file 권한 없음 — 파일 링크 갈래 판정 불가(접합 갈래가 중간 요소를 덮음)");
            }
            let _ = std::fs::remove_dir_all(&b);
        }
    }
}
