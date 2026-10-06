//! 윈 설치기 무인 실행 — `run_installer_wait` · 쥔 핸들 · `CREATE_SUSPENDED` · 이미지 파일 ID 대조 · `Global\cys-installer` 뮤텍스 보유
//! (설계 AUTO-UPDATE-118 §3-7 ③④⑤ · 1R BLOCK 14 · 2R MAJOR 2 · 3R 신규 BLOCK 2 · 📌13′).
//!
//! - 순서(④): stage 설치기를 `CreateFileW(GENERIC_READ, FILE_SHARE_READ)` 로 열어 쥔 채(쓰기·삭제·이름 바꾸기 차단) 그 핸들로 sha256 을
//!   다시 잰다 · 경로 각 성분 reparse point 아님 → 같은 경로로 `CreateProcessW(CREATE_SUSPENDED)` → `QueryFullProcessImageNameW` 경로를
//!   다시 열어 `FileIdInfo`(볼륨 일련번호 + 128비트 파일 ID)가 쥔 핸들과 같고 `GetFinalPathNameByHandleW` 가 같을 때만 `ResumeThread` ·
//!   아니면 `TerminateProcess` + 영구 실패 `update.win_image_mismatch`.
//! - 인자(⑤): `/S /P /UPDATE /CYSTXN=<txn>:<epoch> /D=<설치 폴더>`(`/D` 는 마지막·따옴표 없음 — NSIS 규칙) + env `CYS_UPDATE_TXN`
//!   = 같은 값(NSIS ⓪-a ⑵ 「인자 = env」).
//! - 결과: 시한 15분 · 종료 코드 0 = 설치기 성공(★그래도 S9b 전수 대조가 판정) · 6 = ⓪-a 거부(`txn_busy`) · 3/4/5/그 밖 = 실패.
//!   종료 코드 해석은 순수 함수 [`classify_exit`].

use super::errors::ErrCode;
use super::runner::{Fail, Step};
use std::path::Path;

pub const TIMEOUT_SECS: u64 = 15 * 60;
pub const MUTEX_NAME: &str = "Global\\cys-installer";

/// NSIS 인자 목록(순수 · `/D` 는 마지막 · 따옴표 없음).
pub fn installer_args(token: &str, install_dir: &Path) -> Vec<String> {
    vec!["/S".into(), "/P".into(), "/UPDATE".into(), format!("/CYSTXN={token}"), format!("/D={}", install_dir.display())]
}

/// 윈 명령줄 한 줄(설치기 경로는 따옴표 · 인자는 NSIS 가 받는 그대로 — `/D=` 는 공백이 있어도 따옴표 없이 마지막에).
pub fn command_line(installer: &Path, args: &[String]) -> String {
    let mut s = format!("\"{}\"", installer.display());
    for a in args {
        s.push(' ');
        s.push_str(a);
    }
    s
}

/// 종료 코드 판정(순수).
pub fn classify_exit(code: Option<u32>) -> Step {
    match code {
        Some(0) => Ok(()),
        Some(6) => Err(Fail::new(ErrCode::TxnBusy, "S9", "설치기 ⓪-a 거부(exit 6)")),
        Some(c) => Err(Fail::new(ErrCode::WinInstallerFailed, "S9", format!("설치기 exit {c}"))),
        None => Err(Fail::new(ErrCode::WinInstallerFailed, "S9", format!("시한 {TIMEOUT_SECS}초 초과 — 설치기 종료 확인 뒤"))),
    }
}

/// `cys-install-failure.txt` 토큰(훅 실패 기록 · 있으면 실패 상세로 싣는다).
pub fn failure_token(install_dir: &Path) -> Option<String> {
    std::fs::read_to_string(install_dir.join("cys-install-failure.txt")).ok().map(|s| s.lines().next().unwrap_or("").trim().to_string())
}

/// 설치기 실행·대기(멱등 호출 단위 — 호출자가 재실행 상한을 지킨다).
pub fn run_installer(installer: &Path, install_dir: &Path, token: &str, expect_sha256: &str) -> Step {
    #[cfg(windows)]
    {
        let r = imp::run(installer, install_dir, token, expect_sha256);
        if let Err(f) = &r {
            if let Some(t) = failure_token(install_dir) {
                return Err(Fail::new(f.code, &f.step, format!("{} · {t}", f.detail)));
            }
        }
        r
    }
    #[cfg(not(windows))]
    {
        let _ = (installer, install_dir, token, expect_sha256);
        Err(Fail::new(ErrCode::WinLaunchBlocked, "S9", "윈 전용"))
    }
}

/// S7~S9b 동안 `Global\cys-installer` 를 쥔다(옛 1.1.7 이하 설치기 ⓪ 가 exit 5 로 막힌다) — 프로세스가 끝나면 OS 가 푼다.
pub fn hold_installer_mutex() -> Result<(), String> {
    #[cfg(windows)]
    {
        imp::hold_mutex()
    }
    #[cfg(not(windows))]
    {
        Ok(())
    }
}

pub fn release_installer_mutex() {
    #[cfg(windows)]
    imp::release_mutex();
}

#[cfg(windows)]
mod imp {
    use super::*;
    use std::os::windows::ffi::OsStrExt;
    use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle};
    use windows_sys::Win32::Foundation::{CloseHandle, GetLastError, HANDLE, WAIT_ABANDONED, WAIT_OBJECT_0};
    use windows_sys::Win32::Storage::FileSystem::{
        CreateFileW, FileIdInfo, GetFileAttributesW, GetFileInformationByHandleEx, GetFinalPathNameByHandleW, FILE_ATTRIBUTE_REPARSE_POINT,
        FILE_ID_INFO, FILE_SHARE_READ, INVALID_FILE_ATTRIBUTES, OPEN_EXISTING,
    };
    use windows_sys::Win32::System::Threading::{
        CreateMutexW, CreateProcessW, GetExitCodeProcess, QueryFullProcessImageNameW, ReleaseMutex, ResumeThread, TerminateProcess,
        WaitForSingleObject, CREATE_NO_WINDOW, CREATE_SUSPENDED, PROCESS_INFORMATION, STARTUPINFOW,
    };

    const GENERIC_READ: u32 = 0x8000_0000;
    static MUTEX: std::sync::Mutex<isize> = std::sync::Mutex::new(0);

    fn wide(s: &std::ffi::OsStr) -> Vec<u16> {
        s.encode_wide().chain(std::iter::once(0)).collect()
    }

    fn fail(code: ErrCode, d: impl Into<String>) -> Fail {
        Fail::new(code, "S9", d)
    }

    pub fn hold_mutex() -> Result<(), String> {
        let mut g = MUTEX.lock().unwrap_or_else(|e| e.into_inner());
        if *g != 0 {
            return Ok(());
        }
        let name = wide(std::ffi::OsStr::new(MUTEX_NAME));
        // ★2판(codex 1R C8): `initial_owner=1` 이어도 이미 있던 뮤텍스(ERROR_ALREADY_EXISTS)면 소유권을 받지 못한다 — 소유하지 않은 채
        //   진행하던 길 차단. 소유 없이 만들고(·열고) 0ms 대기로 **실제 소유**를 얻을 때만 진행(버려진 뮤텍스 = 소유 획득 · 그 밖 = 거부).
        // SAFETY: NUL 종단 이름 · 보안 속성 기본.
        let h = unsafe { CreateMutexW(std::ptr::null(), 0, name.as_ptr()) };
        if h.is_null() {
            return Err(format!("CreateMutexW {}", unsafe { GetLastError() }));
        }
        // SAFETY: 방금 받은 핸들.
        let w = unsafe { WaitForSingleObject(h, 0) };
        if w != WAIT_OBJECT_0 && w != WAIT_ABANDONED {
            // SAFETY: 우리 핸들(소유 아님 — ReleaseMutex 0).
            unsafe { CloseHandle(h) };
            return Err(format!("설치 뮤텍스를 다른 프로세스가 소유 중(wait {w})"));
        }
        *g = h as isize;
        Ok(())
    }

    pub fn release_mutex() {
        let mut g = MUTEX.lock().unwrap_or_else(|e| e.into_inner());
        if *g != 0 {
            // SAFETY: 우리가 만든 핸들.
            unsafe {
                ReleaseMutex(*g as HANDLE);
                CloseHandle(*g as HANDLE);
            }
            *g = 0;
        }
    }

    fn no_reparse_chain(p: &Path) -> Result<(), Fail> {
        let mut cur = std::path::PathBuf::new();
        for c in p.components() {
            cur.push(c);
            if matches!(c, std::path::Component::Prefix(_) | std::path::Component::RootDir) {
                continue;
            }
            let w = wide(cur.as_os_str());
            // SAFETY: NUL 종단 경로.
            let a = unsafe { GetFileAttributesW(w.as_ptr()) };
            if a == INVALID_FILE_ATTRIBUTES || a & FILE_ATTRIBUTE_REPARSE_POINT != 0 {
                return Err(fail(ErrCode::WinImageMismatch, format!("reparse·부재 성분 {}", cur.display())));
            }
        }
        Ok(())
    }

    fn file_id(h: HANDLE) -> Option<(u64, [u8; 16])> {
        let mut info: FILE_ID_INFO = unsafe { std::mem::zeroed() };
        // SAFETY: 유효 핸들 · 출력 구조체 크기 전달.
        let ok = unsafe { GetFileInformationByHandleEx(h, FileIdInfo, &mut info as *mut _ as *mut _, std::mem::size_of::<FILE_ID_INFO>() as u32) };
        (ok != 0).then(|| (info.VolumeSerialNumber, info.FileId.Identifier))
    }

    fn final_path(h: HANDLE) -> Option<String> {
        let mut buf = vec![0u16; 1024];
        // SAFETY: 버퍼 길이 전달.
        let n = unsafe { GetFinalPathNameByHandleW(h, buf.as_mut_ptr(), buf.len() as u32, 0) };
        (n > 0 && (n as usize) < buf.len()).then(|| String::from_utf16_lossy(&buf[..n as usize]).to_lowercase())
    }

    fn open_shared_read(p: &Path) -> Option<OwnedHandle> {
        let w = wide(p.as_os_str());
        // SAFETY: NUL 종단 경로 · 쓰기·삭제 공유 없음(쥔 동안 바꿔치기 차단).
        let h = unsafe { CreateFileW(w.as_ptr(), GENERIC_READ, FILE_SHARE_READ, std::ptr::null(), OPEN_EXISTING, 0, std::ptr::null_mut()) };
        if h.is_null() || h as isize == -1 {
            return None;
        }
        // SAFETY: 방금 연 유효 핸들 — 소유권을 OwnedHandle 로.
        Some(unsafe { OwnedHandle::from_raw_handle(h as _) })
    }

    pub fn run(installer: &Path, install_dir: &Path, token: &str, expect_sha256: &str) -> Step {
        no_reparse_chain(installer)?;
        let held = open_shared_read(installer).ok_or_else(|| fail(ErrCode::WinImageMismatch, "설치기 열기 실패"))?;
        // 쥔 핸들로 sha256(같은 핸들을 File 로 빌려 읽는다 — try_clone 은 같은 파일 객체)
        let f = std::fs::File::from(held.try_clone().map_err(|e| fail(ErrCode::WinImageMismatch, e.to_string()))?);
        let sha = {
            use sha2::{Digest, Sha256};
            use std::io::Read;
            let mut f = f;
            let mut h = Sha256::new();
            let mut buf = vec![0u8; 1 << 16];
            loop {
                let n = f.read(&mut buf).map_err(|e| fail(ErrCode::WinImageMismatch, e.to_string()))?;
                if n == 0 {
                    break;
                }
                h.update(&buf[..n]);
            }
            format!("{:x}", h.finalize())
        };
        if !expect_sha256.is_empty() && sha != expect_sha256 {
            return Err(fail(ErrCode::DlShaMismatch, "쥔 핸들 sha256 불일치"));
        }
        let held_raw = held.as_raw_handle() as HANDLE;
        let want_id = file_id(held_raw).ok_or_else(|| fail(ErrCode::WinImageMismatch, "FileIdInfo"))?;
        let want_path = final_path(held_raw).ok_or_else(|| fail(ErrCode::WinImageMismatch, "최종 경로"))?;
        std::env::set_var(crate::update::lock::ENV_TXN, token); // ⓪-a ⑵ 인자 = env(자식이 물려받는다)
        let app = wide(installer.as_os_str());
        let mut cmd = wide(std::ffi::OsStr::new(&command_line(installer, &installer_args(token, install_dir))));
        let mut si: STARTUPINFOW = unsafe { std::mem::zeroed() };
        si.cb = std::mem::size_of::<STARTUPINFOW>() as u32;
        let mut pi: PROCESS_INFORMATION = unsafe { std::mem::zeroed() };
        // SAFETY: NUL 종단 앱 경로·가변 명령줄 · 주 스레드 멈춘 채 생성.
        let ok = unsafe {
            CreateProcessW(app.as_ptr(), cmd.as_mut_ptr(), std::ptr::null(), std::ptr::null(), 0, CREATE_SUSPENDED | CREATE_NO_WINDOW, std::ptr::null(), std::ptr::null(), &si, &mut pi)
        };
        if ok == 0 {
            return Err(fail(ErrCode::WinLaunchBlocked, format!("CreateProcessW {}", unsafe { GetLastError() })));
        }
        let kill = |why: String| -> Fail {
            // SAFETY: 방금 만든 프로세스 핸들.
            unsafe {
                TerminateProcess(pi.hProcess, 1);
                CloseHandle(pi.hThread);
                CloseHandle(pi.hProcess);
            }
            fail(ErrCode::WinImageMismatch, why)
        };
        // 이미지 대조(멈춘 채)
        let mut buf = vec![0u16; 1024];
        let mut n = buf.len() as u32;
        // SAFETY: 버퍼·길이 전달.
        if unsafe { QueryFullProcessImageNameW(pi.hProcess, 0, buf.as_mut_ptr(), &mut n) } == 0 {
            return Err(kill("QueryFullProcessImageNameW".into()));
        }
        let image = std::path::PathBuf::from(String::from_utf16_lossy(&buf[..n as usize]));
        let Some(img) = open_shared_read(&image) else { return Err(kill("이미지 다시 열기".into())) };
        let img_raw = img.as_raw_handle() as HANDLE;
        if file_id(img_raw) != Some(want_id) || final_path(img_raw).as_deref() != Some(want_path.as_str()) || crate::update::mutant("U2-IMG") {
            return Err(kill(format!("이미지 불일치 {}", image.display())));
        }
        // SAFETY: 멈춘 주 스레드 재개.
        if unsafe { ResumeThread(pi.hThread) } == u32::MAX {
            return Err(kill("ResumeThread".into()));
        }
        // SAFETY: 프로세스 핸들 대기.
        let w = unsafe { WaitForSingleObject(pi.hProcess, (TIMEOUT_SECS * 1000) as u32) };
        if w != WAIT_OBJECT_0 {
            // ★2판(codex 1R C8): 시한 초과 = 설치기를 끝내고 **끝난 것을 확인한 뒤에만** 돌아간다(그 전에 RB 가 옛 설치기를 띄우면 동시
            //   쓰기). 반쯤 된 설치는 S9b·RB 가 실물로 판정한다. 종료 요청이 거부돼도(권한) 설치기가 스스로 끝날 때까지 기다린다.
            // SAFETY: 우리가 만든 프로세스.
            unsafe { TerminateProcess(pi.hProcess, 1) };
            // SAFETY: 프로세스 핸들 무기한 대기(종료 확인).
            unsafe { WaitForSingleObject(pi.hProcess, u32::MAX) };
            // SAFETY: 끝난 프로세스의 핸들 정리.
            unsafe {
                CloseHandle(pi.hThread);
                CloseHandle(pi.hProcess);
            }
            drop(img);
            drop(held);
            return classify_exit(None);
        }
        let code = if w == WAIT_OBJECT_0 {
            let mut c = 0u32;
            // SAFETY: 끝난 프로세스.
            unsafe { GetExitCodeProcess(pi.hProcess, &mut c) };
            Some(c)
        } else {
            None
        };
        // SAFETY: 핸들 정리.
        unsafe {
            CloseHandle(pi.hThread);
            CloseHandle(pi.hProcess);
        }
        drop(img);
        drop(held);
        classify_exit(code)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// §7-1 윈: 종료 코드 0/3/4/5/6/그 밖 · 시한 초과 · `cys-install-failure.txt` 토큰.
    #[test]
    fn exit_codes_timeout_and_failure_token() {
        assert!(classify_exit(Some(0)).is_ok());
        assert_eq!(classify_exit(Some(6)).unwrap_err().code, ErrCode::TxnBusy);
        for c in [3, 4, 5, 1, 2] {
            assert_eq!(classify_exit(Some(c)).unwrap_err().code, ErrCode::WinInstallerFailed, "{c}");
        }
        assert!(classify_exit(None).unwrap_err().detail.contains("초과"));
        let d = std::env::temp_dir().join(format!("cys-u2-wi-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        assert_eq!(failure_token(&d), None);
        std::fs::write(d.join("cys-install-failure.txt"), "L1_SWEEP_FAILED\nmore").unwrap();
        assert_eq!(failure_token(&d).as_deref(), Some("L1_SWEEP_FAILED"));
    }

    #[test]
    fn args_put_d_last_unquoted_and_token_as_cystxn() {
        let a = installer_args("ab:3", Path::new(r"C:\Users\x y\AppData\Local\cys"));
        assert_eq!(a[3], "/CYSTXN=ab:3");
        assert_eq!(a.last().unwrap(), r"/D=C:\Users\x y\AppData\Local\cys");
        let cl = command_line(Path::new(r"C:\s\setup.exe"), &a);
        assert!(cl.starts_with("\"C:\\s\\setup.exe\" /S /P /UPDATE ") && cl.ends_with(r"/D=C:\Users\x y\AppData\Local\cys"));
    }
}
