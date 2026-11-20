//! 조종자 신원 확인 — T2 시제품(DESIGN.md §3-2 ② · codex 1R 2 · master 판단 11-11).
//!
//! 신뢰 경계 = 「같은 사용자 = 경계 안」(master 판단 11-11 ⓪). 그 안에서 할 수 있는 만큼 좁힌다.
//!
//! ⚠ **감사 토큰은 연결에 묶여 있지 않다**(독립 검증 D3 · 11-11 정정). 맥 커널의 `LOCAL_PEERTOKEN` 은 피어 소켓의
//! `last_pid`(그 소켓을 마지막으로 connect·send·recv·poll·kqueue 한 프로세스)를 그 순간 `proc_find` 로 찾아 **지금
//! 그 pid 를 가진 프로세스**의 토큰을 돌려준다(xnu `bsd/kern/uipc_usrreq.c` LOCAL_PEERTOKEN · `so_update_last_owner_locked`
//! 호출 11곳). 그래서 토큰의 pidversion 은 「처음 연결한 그 프로세스」를 보증하지 않는다 — fd 를 넘겨받은 프로세스가 보내면
//! 그 프로세스로 바뀌고, 아무도 아직 안 보냈으면 EINVAL(→ 여기서는 거절)이다.
//! **실제 방어**(주 방어 순서): ⓐ HELLO 를 받은 **뒤** 이 확인을 한 번 더 하고 처음 확인과 (pid · pidversion · 출생 시각)이
//!   모두 같아야 받는다(main.rs handshake) ⓑ 핸드셰이크 전체 절대 기한 3초 ⓒ 같은 pid 가 그 3초 안에 재사용되기 어렵다는 사정
//!   ⓓ 잠금 파일에 조종자의 (pid, 출생 시각)이 적혀 있으면 그 짝까지 대조한다(아래 4).
//!
//! 확인 항목:
//! 1. 피어 신원: 맥 `LOCAL_PEERTOKEN`(감사 토큰 · SDK sys/un.h:93) — 위 ⚠ 대로 「지금 마지막 사용 프로세스」의 신원이다.
//! 2. **실행 파일 경로**: 감사 토큰으로 Security 프레임워크의 코드 객체를 얻고(`kSecGuestAttributeAudit`) 그 코드의 경로를 읽는다.
//! 3. (선택) **코드서명 요구사항**: `--requirement` 가 주어지면 같은 코드 객체로 `SecCodeCheckValidity`.
//! 4. **데몬 잠금 보유**: 잠금 파일이 실제로 잡혀 있고(flock 시도 실패) 그 파일 첫 칸의 pid = 토큰 pid. 둘째 칸이 있으면
//!    그것을 조종자의 출생 시각(마이크로초 · proc_pidinfo 의 시작 시각)으로 보고 피어의 출생 시각과 같아야 한다 —
//!    (pid, 출생 시각) 짝은 pid 재사용과 구분된다. 둘째 칸이 없으면(옛 형식) pid 만 대조한다.
//! 5. 같은 사용자(토큰 euid = 내 euid).
//! 확인할 수 없는 것은 전부 거절이다(fail-closed). 맥 밖에서는 아직 구현이 없으므로 항상 거절한다.

use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct Peer {
    pub pid: i32,
    pub pidversion: u32,
    pub euid: u32,
    pub exe: Option<PathBuf>,
    /// 확인 시점에 그 pid 를 가진 프로세스의 출생 시각(마이크로초). 못 읽으면 None(→ 짝 대조가 필요한 곳에서 거절).
    pub start_us: Option<u64>,
}

#[derive(Debug, Clone)]
pub struct Policy {
    pub controller_exe: PathBuf,
    pub requirement: Option<String>,
    pub lock: PathBuf,
}

/// 거절 사유 문자열(교체 기록·REJECT 프레임에 그대로 실린다).
pub type Reason = &'static str;

#[cfg(target_os = "macos")]
mod mac {
    use std::ffi::{c_void, CStr, CString};
    use std::os::raw::{c_char, c_long};
    use std::path::PathBuf;

    type CFTypeRef = *const c_void;
    type CFAllocatorRef = *const c_void;
    type CFDictionaryRef = *const c_void;
    type CFDataRef = *const c_void;
    type CFStringRef = *const c_void;
    type CFURLRef = *const c_void;
    type CFIndex = c_long;
    type OSStatus = i32;
    type SecCodeRef = *const c_void;
    type SecStaticCodeRef = *const c_void;
    type SecRequirementRef = *const c_void;

    #[repr(C)]
    struct CFDictionaryKeyCallBacks {
        _p: [usize; 6],
    }
    #[repr(C)]
    struct CFDictionaryValueCallBacks {
        _p: [usize; 5],
    }

    #[link(name = "CoreFoundation", kind = "framework")]
    extern "C" {
        static kCFTypeDictionaryKeyCallBacks: CFDictionaryKeyCallBacks;
        static kCFTypeDictionaryValueCallBacks: CFDictionaryValueCallBacks;
        fn CFDataCreate(alloc: CFAllocatorRef, bytes: *const u8, len: CFIndex) -> CFDataRef;
        fn CFDictionaryCreate(
            alloc: CFAllocatorRef,
            keys: *const *const c_void,
            values: *const *const c_void,
            n: CFIndex,
            kcb: *const CFDictionaryKeyCallBacks,
            vcb: *const CFDictionaryValueCallBacks,
        ) -> CFDictionaryRef;
        fn CFStringCreateWithCString(alloc: CFAllocatorRef, s: *const c_char, enc: u32) -> CFStringRef;
        fn CFURLGetFileSystemRepresentation(url: CFURLRef, resolve: u8, buf: *mut u8, max: CFIndex) -> u8;
        fn CFRelease(cf: CFTypeRef);
    }

    #[link(name = "Security", kind = "framework")]
    extern "C" {
        static kSecGuestAttributeAudit: CFStringRef;
        fn SecCodeCopyGuestWithAttributes(host: SecCodeRef, attrs: CFDictionaryRef, flags: u32, guest: *mut SecCodeRef) -> OSStatus;
        fn SecCodeCopyStaticCode(code: SecCodeRef, flags: u32, out: *mut SecStaticCodeRef) -> OSStatus;
        fn SecCodeCopyPath(code: SecStaticCodeRef, flags: u32, path: *mut CFURLRef) -> OSStatus;
        fn SecRequirementCreateWithString(text: CFStringRef, flags: u32, req: *mut SecRequirementRef) -> OSStatus;
        fn SecCodeCheckValidity(code: SecCodeRef, flags: u32, req: SecRequirementRef) -> OSStatus;
    }

    const K_CF_STRING_ENCODING_UTF8: u32 = 0x0800_0100;

    struct Owned(CFTypeRef);
    impl Drop for Owned {
        fn drop(&mut self) {
            if !self.0.is_null() {
                unsafe { CFRelease(self.0) }
            }
        }
    }

    /// 감사 토큰 → 코드 객체. 토큰의 pidversion 이 지금 프로세스와 다르면 Security 가 거절한다.
    fn guest(token: &[u32; 8]) -> Option<Owned> {
        unsafe {
            let data = Owned(CFDataCreate(std::ptr::null(), token.as_ptr() as *const u8, 32));
            if data.0.is_null() {
                return None;
            }
            let keys = [kSecGuestAttributeAudit as *const c_void];
            let vals = [data.0];
            let attrs = Owned(CFDictionaryCreate(
                std::ptr::null(),
                keys.as_ptr(),
                vals.as_ptr(),
                1,
                &kCFTypeDictionaryKeyCallBacks,
                &kCFTypeDictionaryValueCallBacks,
            ));
            if attrs.0.is_null() {
                return None;
            }
            let mut code: SecCodeRef = std::ptr::null();
            if SecCodeCopyGuestWithAttributes(std::ptr::null(), attrs.0, 0, &mut code) != 0 || code.is_null() {
                return None;
            }
            Some(Owned(code))
        }
    }

    pub fn exe_of_token(token: &[u32; 8]) -> Option<PathBuf> {
        let code = guest(token)?;
        unsafe {
            let mut st: SecStaticCodeRef = std::ptr::null();
            if SecCodeCopyStaticCode(code.0, 0, &mut st) != 0 || st.is_null() {
                return None;
            }
            let st = Owned(st);
            let mut url: CFURLRef = std::ptr::null();
            if SecCodeCopyPath(st.0, 0, &mut url) != 0 || url.is_null() {
                return None;
            }
            let url = Owned(url);
            let mut buf = [0u8; 4096];
            if CFURLGetFileSystemRepresentation(url.0, 1, buf.as_mut_ptr(), buf.len() as CFIndex) == 0 {
                return None;
            }
            let s = CStr::from_ptr(buf.as_ptr() as *const c_char).to_string_lossy().into_owned();
            Some(PathBuf::from(s))
        }
    }

    pub fn satisfies(token: &[u32; 8], requirement: &str) -> bool {
        let Some(code) = guest(token) else { return false };
        let Ok(text) = CString::new(requirement) else { return false };
        unsafe {
            let s = Owned(CFStringCreateWithCString(std::ptr::null(), text.as_ptr(), K_CF_STRING_ENCODING_UTF8));
            if s.0.is_null() {
                return false;
            }
            let mut req: SecRequirementRef = std::ptr::null();
            if SecRequirementCreateWithString(s.0, 0, &mut req) != 0 || req.is_null() {
                return false;
            }
            let req = Owned(req);
            SecCodeCheckValidity(code.0, 0, req.0) == 0
        }
    }

    /// `getsockopt(SOL_LOCAL, LOCAL_PEERTOKEN)` — 감사 토큰 8칸(0 auid · 1 euid · 2 egid · 3 ruid · 4 rgid · 5 pid · 6 asid · 7 pidversion).
    pub fn peer_token(fd: i32) -> Option<[u32; 8]> {
        const SOL_LOCAL: i32 = 0;
        const LOCAL_PEERTOKEN: i32 = 0x006;
        let mut tok = [0u32; 8];
        let mut len = std::mem::size_of_val(&tok) as libc::socklen_t;
        let rc = unsafe { libc::getsockopt(fd, SOL_LOCAL, LOCAL_PEERTOKEN, tok.as_mut_ptr() as *mut c_void, &mut len) };
        (rc == 0 && len as usize == std::mem::size_of_val(&tok)).then_some(tok)
    }
}

/// 연결 fd 의 피어 신원. 맥 밖 = None(→ 거절).
pub fn identify(fd: i32) -> Option<(Peer, [u32; 8])> {
    #[cfg(target_os = "macos")]
    {
        let tok = mac::peer_token(fd)?;
        let pid = tok[5] as i32;
        let peer = Peer { pid, pidversion: tok[7], euid: tok[1], exe: mac::exe_of_token(&tok),
                          start_us: crate::registry::process_start_us(pid) };
        Some((peer, tok))
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = fd;
        None
    }
}

/// 잠금 파일을 **한 번 열어 그 fd 로** ⓐ 지금 누군가에게 잡혀 있는가 ⓑ 적힌 pid 를 함께 본다 — 같은 inode 의
/// 관측이다(codex 1R #10: 예전엔 잠금 검사 fd 를 닫고 경로를 다시 열어 pid 를 읽었다).
/// ⓐ = flock 비차단 시도가 EWOULDBLOCK 이면 잡혀 있다. 우리가 잡아 버리면 즉시 풀고 「안 잡혀 있음」으로 답한다.
/// 둘째 값 = 첫 칸 pid · 셋째 값 = 둘째 칸(조종자 출생 시각 · 있으면).
/// 못 열거나 판정 불가 = None(→ 거절).
pub fn lock_state(lock: &Path) -> Option<(bool, Option<i32>, Option<u64>)> {
    use std::io::Read;
    use std::os::unix::io::AsRawFd;
    let mut f = std::fs::OpenOptions::new().read(true).open(lock).ok()?;
    let rc = unsafe { libc::flock(f.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) };
    let held = if rc == 0 {
        unsafe { libc::flock(f.as_raw_fd(), libc::LOCK_UN) };
        false
    } else if std::io::Error::last_os_error().raw_os_error() == Some(libc::EWOULDBLOCK) {
        true
    } else {
        return None;
    };
    let mut text = String::new();
    f.read_to_string(&mut text).ok()?;
    let mut it = text.split_whitespace();
    let pid = it.next().and_then(|t| t.parse().ok());
    let start = it.next().map(|t| t.parse::<u64>().unwrap_or(0));
    Some((held, pid, start))
}

/// 전부 통과하면 Ok(Peer). 순서는 싼 검사부터 — 결과는 같다(하나라도 실패 = 거절).
pub fn authorize(fd: i32, policy: &Policy) -> Result<Peer, (Reason, Option<Peer>)> {
    let Some((peer, tok)) = identify(fd) else { return Err(("peer_identity_unavailable", None)) };
    if peer.euid != unsafe { libc::geteuid() } {
        return Err(("other_user", Some(peer)));
    }
    let want = std::fs::canonicalize(&policy.controller_exe).unwrap_or_else(|_| policy.controller_exe.clone());
    match peer.exe.as_ref().map(|p| std::fs::canonicalize(p).unwrap_or_else(|_| p.clone())) {
        Some(got) if got == want => {}
        Some(_) => return Err(("exe_mismatch", Some(peer))),
        None => return Err(("exe_unknown", Some(peer))),
    }
    #[cfg(target_os = "macos")]
    if let Some(req) = &policy.requirement {
        if !mac::satisfies(&tok, req) {
            return Err(("requirement_unmet", Some(peer)));
        }
    }
    let _ = &tok;
    match lock_state(&policy.lock) {
        Some((true, pid, start)) if pid == Some(peer.pid) => {
            // 둘째 칸(출생 시각)이 있으면 (pid, 출생 시각) 짝까지 같아야 한다 — pid 재사용과 구분.
            if let Some(start) = start {
                if peer.start_us != Some(start) {
                    return Err(("lock_owner_mismatch", Some(peer)));
                }
            }
        }
        Some((true, _, _)) => return Err(("lock_pid_mismatch", Some(peer))),
        Some((false, _, _)) => return Err(("lock_not_held", Some(peer))),
        None => return Err(("lock_unreadable", Some(peer))),
    }
    Ok(peer)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unheld_lock_reads_false_and_stays_free() {
        let p = std::env::temp_dir().join(format!("sk-lock-{}", std::process::id()));
        std::fs::write(&p, "123").unwrap();
        assert_eq!(lock_state(&p), Some((false, Some(123), None)));
        assert_eq!(lock_state(&p), Some((false, Some(123), None)), "검사가 잠금을 붙잡아 두면 안 된다");
        std::fs::write(&p, "123 456789").unwrap();
        assert_eq!(lock_state(&p), Some((false, Some(123), Some(456789))));
        std::fs::write(&p, "123 garbage").unwrap();
        assert_eq!(lock_state(&p), Some((false, Some(123), Some(0))), "읽을 수 없는 둘째 칸 = 0(어떤 출생 시각과도 불일치 → 거절)");
        let _ = std::fs::remove_file(&p);
    }

    #[test]
    fn held_lock_reads_true() {
        use std::os::unix::io::AsRawFd;
        let p = std::env::temp_dir().join(format!("sk-lock2-{}", std::process::id()));
        std::fs::write(&p, "1").unwrap();
        let f = std::fs::File::open(&p).unwrap();
        assert_eq!(unsafe { libc::flock(f.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) }, 0);
        assert_eq!(lock_state(&p), Some((true, Some(1), None)));
        drop(f);
        let _ = std::fs::remove_file(&p);
    }

    #[test]
    fn missing_lock_is_unreadable_not_free() {
        assert_eq!(lock_state(Path::new("/nonexistent/sk-lock")), None);
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn socketpair_peer_is_self() {
        use std::os::unix::io::AsRawFd;
        let (a, _b) = std::os::unix::net::UnixStream::pair().unwrap();
        let (peer, _) = identify(a.as_raw_fd()).expect("감사 토큰");
        assert_eq!(peer.pid, std::process::id() as i32);
        let me = std::fs::canonicalize(std::env::current_exe().unwrap()).unwrap();
        assert_eq!(peer.exe.map(|p| std::fs::canonicalize(p).unwrap()), Some(me));
    }
}
