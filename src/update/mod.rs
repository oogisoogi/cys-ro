//! 1.1.8 데몬 자동 갱신 — 공용 모듈(U1 · 피드·검증·판정). 설계 정본 = AUTO-UPDATE-118 4판
//! (`~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md`).
//!
//! U1 범위 = 판정까지(교체·rotate·롤백·앱 UI 0 — U2·U4). 이 모듈의 함수는 대부분 순수 함수이고, 파일을 쓰는 것
//! (수용 기록·잠금·저널·보류 로그·install_id)은 상태 폴더([`state_dir`]) 아래에만 쓴다. 시험은 `CYS_UPDATE_STATE_DIR`
//! 로 격리한다(실 `~/.cys` 쓰기 0).

pub mod buildinfo;
pub mod check;
pub mod cli;
pub mod clock;
pub mod errors;
pub mod failures;
pub mod feed;
pub mod gates;
pub mod hold;
pub mod journal;
pub mod keys;
pub mod lock;
pub mod net;
pub mod packgate;
pub mod sched;
pub mod url;
pub mod win;

/// 원작자 윈 설치기 실행 판정(📌15 편입 · 파일 통째 · `src/update_launch.rs` 그 자리 그대로 — 아래 근거).
///
/// 설계 §5-1 은 `src/update/launch_win.rs` 로 옮긴다고 적었으나, 파일 위치를 옮기면 ① 윈 실기 레인
/// (`windows-health.yml`)의 시험 필터 `update_launch::` 와 ② 앱 핀 시험의 `include_str!("../../src/update_launch.rs")` 가
/// 깨진다(CI 워크플로 변경 = master 게이트). 그래서 파일은 그대로 두고 여기서 같은 모듈을 `launch_win` 이름으로 노출한다
/// — 바이트 동일성(`git hash-object`)은 그대로 유지된다.
pub use crate::update_launch as launch_win;

pub use errors::{ErrCode, UpdateErr};

/// ★2판 수리 증명 스위치(codex 1R 「각 수리 = 뮤테이션 1」) — **시험 빌드에서만** 켜진다(출시·디버그 실행 바이너리 = 늘 false ·
/// `cfg!(test)` 가 거짓이면 컴파일러가 분기째 지운다). `CYS_U1_MUTANT=<번호>` 로 그 수리의 가드 1곳을 끄고 같은 시험이 적색이
/// 되는지 본다(수정 전 적색 · 수정 후 초록의 기계 증명 — 도구 = HANDOFF-U1 「1R 반영표」 의 실행 줄).
#[inline]
pub(crate) fn mutant(id: &str) -> bool {
    cfg!(test) && std::env::var("CYS_U1_MUTANT").map(|v| v == id).unwrap_or(false)
}

/// 윈 갱신 폴더의 보호 DACL(소유자 권한·SYSTEM 만 · 상속 끊음 — cysd 파이프 owner-only SDDL 과 같은 꼴에서 BA 를 뺀 것).
#[cfg(windows)]
const PRIVATE_DIR_SDDL: &str = "D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)";

/// 소유자 전용 폴더(1R MAJOR · 설계 §3-2 「소유자 전용 ACL」): 유닉스 = 만들 때부터 0700 + 재검증(모드 그룹·기타 비트 0 ·
/// 소유 uid = 나) · 윈 = ★2R M3: **만들 때** `SECURITY_ATTRIBUTES` 로 보호 DACL 을 넣고(`CreateDirectoryW` · 사후 적용 금지) 매번
/// DACL 을 다시 읽어 확인(read-back — 보호 표지 + 허용 ACE 가 소유자 권한·SYSTEM 뿐). 어긋나면 Err(fail-closed).
pub fn ensure_private_dir(dir: &std::path::Path) -> Result<(), String> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::{DirBuilderExt, MetadataExt, PermissionsExt};
        if !dir.exists() {
            std::fs::DirBuilder::new().recursive(true).mode(0o700).create(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
        }
        let md = std::fs::metadata(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
        if md.mode() & 0o077 != 0 && !mutant("M3") {
            std::fs::set_permissions(dir, std::fs::Permissions::from_mode(0o700)).map_err(|e| e.to_string())?;
        }
        let md = std::fs::metadata(dir).map_err(|e| e.to_string())?;
        // SAFETY: 인자 없는 조회.
        let me = unsafe { libc::geteuid() };
        if md.uid() != me || md.mode() & 0o077 != 0 {
            return Err(format!("갱신 폴더 권한 불일치 {} (uid {} · mode {:o})", dir.display(), md.uid(), md.mode() & 0o777));
        }
        Ok(())
    }
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        use windows_sys::Win32::Security::Authorization::{ConvertStringSecurityDescriptorToSecurityDescriptorW, SDDL_REVISION_1};
        use windows_sys::Win32::Security::{PSECURITY_DESCRIPTOR, SECURITY_ATTRIBUTES};
        use windows_sys::Win32::Storage::FileSystem::CreateDirectoryW;
        let wide = |p: &std::path::Path| -> Vec<u16> { p.as_os_str().encode_wide().chain(std::iter::once(0)).collect() };
        if !dir.exists() {
            if let Some(parent) = dir.parent() {
                std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
            }
            let sddl: Vec<u16> = PRIVATE_DIR_SDDL.encode_utf16().chain(std::iter::once(0)).collect();
            let mut psd: PSECURITY_DESCRIPTOR = std::ptr::null_mut();
            // SAFETY: 널종단 와이드 문자열 · psd 는 성공 시 LocalAlloc 블록(아래에서 해제).
            let ok = unsafe { ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.as_ptr(), SDDL_REVISION_1, &mut psd, std::ptr::null_mut()) };
            if ok == 0 || psd.is_null() {
                return Err("DACL 조립 실패".into());
            }
            let sa = SECURITY_ATTRIBUTES {
                nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
                lpSecurityDescriptor: psd,
                bInheritHandle: 0,
            };
            let w = wide(dir);
            // SAFETY: 경로 널종단 · sa 는 유효한 지역 구조체(psd 유효).
            let made = unsafe { CreateDirectoryW(w.as_ptr(), &sa) };
            // SAFETY: Convert… 가 LocalAlloc 으로 준 블록.
            unsafe { windows_sys::Win32::Foundation::LocalFree(psd as _) };
            if made == 0 && !dir.exists() {
                return Err(format!("갱신 폴더 만들기 실패 {}", dir.display()));
            }
        }
        check_private_sd(dir, "폴더")
    }
}

/// 폴더·파일의 보안 기술자(소유자 + DACL)를 SDDL 문자열로 다시 읽는다(read-back).
#[cfg(windows)]
fn read_sd_sddl(path: &std::path::Path) -> Result<String, String> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Security::Authorization::{ConvertSecurityDescriptorToStringSecurityDescriptorW, SDDL_REVISION_1};
    use windows_sys::Win32::Security::{GetFileSecurityW, DACL_SECURITY_INFORMATION, OWNER_SECURITY_INFORMATION};
    let info = OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION;
    let w: Vec<u16> = path.as_os_str().encode_wide().chain(std::iter::once(0)).collect();
    let mut need = 0u32;
    // SAFETY: 크기 질의(버퍼 널 · 길이 0) — 필요한 바이트 수를 need 에 받는다.
    unsafe { GetFileSecurityW(w.as_ptr(), info, std::ptr::null_mut(), 0, &mut need) };
    if need == 0 {
        return Err(format!("보안 기술자 크기 조회 실패 {}", path.display()));
    }
    let mut buf = vec![0u8; need as usize];
    // SAFETY: buf 는 need 바이트.
    if unsafe { GetFileSecurityW(w.as_ptr(), info, buf.as_mut_ptr() as _, need, &mut need) } == 0 {
        return Err(format!("보안 기술자 읽기 실패 {}", path.display()));
    }
    let mut out: windows_sys::core::PWSTR = std::ptr::null_mut();
    let mut len = 0u32;
    // SAFETY: buf 는 자기상대 보안 기술자 · out 은 성공 시 LocalAlloc 블록.
    let ok = unsafe { ConvertSecurityDescriptorToStringSecurityDescriptorW(buf.as_ptr() as _, SDDL_REVISION_1, info, &mut out, &mut len) };
    if ok == 0 || out.is_null() {
        return Err("보안 기술자 문자열 변환 실패".into());
    }
    // SAFETY: out 은 LocalAlloc 블록의 널종단 와이드 문자열.
    let s = unsafe { take_local_wstr(out) };
    Ok(s)
}

/// LocalAlloc 으로 받은 널종단 와이드 문자열을 String 으로 옮기고 해제한다.
#[cfg(windows)]
unsafe fn take_local_wstr(p: windows_sys::core::PWSTR) -> String {
    let mut n = 0usize;
    while *p.add(n) != 0 {
        n += 1;
    }
    let s = String::from_utf16_lossy(std::slice::from_raw_parts(p, n));
    windows_sys::Win32::Foundation::LocalFree(p as _);
    s
}

/// 이 프로세스 사용자 SID 문자열(`S-1-5-21-…`) — 토큰의 TokenUser.
#[cfg(windows)]
fn current_user_sid() -> Result<String, String> {
    use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
    use windows_sys::Win32::Security::Authorization::ConvertSidToStringSidW;
    use windows_sys::Win32::Security::{GetTokenInformation, TokenUser, TOKEN_QUERY, TOKEN_USER};
    use windows_sys::Win32::System::Threading::{GetCurrentProcess, OpenProcessToken};
    let mut tok: HANDLE = std::ptr::null_mut();
    // SAFETY: 의사 핸들 · tok 은 성공 시 닫아야 하는 토큰 핸들.
    if unsafe { OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &mut tok) } == 0 {
        return Err("프로세스 토큰 열기 실패".into());
    }
    let mut need = 0u32;
    // SAFETY: 크기 질의.
    unsafe { GetTokenInformation(tok, TokenUser, std::ptr::null_mut(), 0, &mut need) };
    let mut buf = vec![0u8; need.max(1) as usize];
    // SAFETY: buf 는 need 바이트.
    let ok = unsafe { GetTokenInformation(tok, TokenUser, buf.as_mut_ptr() as _, need, &mut need) };
    // SAFETY: OpenProcessToken 이 준 핸들.
    unsafe { CloseHandle(tok) };
    if ok == 0 {
        return Err("토큰 사용자 조회 실패".into());
    }
    // SAFETY: GetTokenInformation(TokenUser) 성공 = buf 머리가 TOKEN_USER(SID 포인터는 buf 안).
    let sid = unsafe { (*(buf.as_ptr() as *const TOKEN_USER)).User.Sid };
    let mut out: windows_sys::core::PWSTR = std::ptr::null_mut();
    // SAFETY: sid 유효 · out 은 성공 시 LocalAlloc 블록.
    if unsafe { ConvertSidToStringSidW(sid, &mut out) } == 0 || out.is_null() {
        return Err("SID 문자열 변환 실패".into());
    }
    // SAFETY: LocalAlloc 블록의 널종단 와이드 문자열.
    Ok(unsafe { take_local_wstr(out) })
}

#[cfg(windows)]
fn check_private_sd(path: &std::path::Path, what: &str) -> Result<(), String> {
    let got = read_sd_sddl(path)?;
    let me = current_user_sid()?;
    if !mutant("M3") && !sd_is_private(&got, &me) {
        return Err(format!("갱신 {what} DACL 불일치 {} ({got} · 나 = {me})", path.display()));
    }
    Ok(())
}

/// ★5판(윈 러너 실측 — 생성 시 보호 DACL 폴더 안 파일 = `D:(A;;FA;;;OW)(A;;FA;;;SY)` · 상속 표지 없음): 보안 기술자 SDDL 을
/// **의미로** 판정(순수 · 모든 기판에서 시험). 소유자 ∈ {나(`me` SID 문자열), Administrators(BA), SYSTEM(SY)} ∧ DACL 이 있음
/// (NULL DACL = 누구나 = 거부) ∧ 허용(A) ACE 의 주체가 전부 {소유자 권한(OW), SYSTEM, Administrators, 나} 안 ∧ 거부(D) ACE 는 무관
/// ∧ 그 밖 ACE 형(개체 ACE 등) = 거부. 상속·보호 표지는 보지 않는다 — 대신 **물려받은 ACE 도 같은 주체 규칙으로 센다**(무시하면
/// 물려받은 Everyone·Users 가 지나간다).
pub fn sd_is_private(sddl: &str, me: &str) -> bool {
    let me_alias: &str = if me == "S-1-5-18" { "SY" } else { me };
    let (owner, dacl) = match (sddl.find("O:"), sddl.find("D:")) {
        (Some(o), Some(d)) if o < d => {
            let owner_end = sddl[o + 2..].find("G:").map(|g| o + 2 + g).unwrap_or(d).min(d);
            (&sddl[o + 2..owner_end], &sddl[d + 2..])
        }
        _ => return false,
    };
    if !(owner == me || owner == me_alias || owner == "BA" || owner == "SY") {
        return false;
    }
    let dacl = dacl.split("S:").next().unwrap_or(dacl); // SACL 은 판정 밖
    let flags_end = dacl.find('(').unwrap_or(dacl.len());
    if dacl[..flags_end].contains("NO_ACCESS_CONTROL") {
        return false;
    }
    dacl[flags_end..].split(['(', ')']).filter(|x| !x.is_empty()).all(|ace| {
        let f: Vec<&str> = ace.split(';').collect();
        f.len() == 6
            && match f[0] {
                "A" => matches!(f[5], "OW" | "SY" | "BA") || f[5] == me || f[5] == me_alias,
                "D" => true,
                _ => false,
            }
    })
}

/// ★2R M3: 이미 있는 갱신 파일이 소유자 전용인가(유닉스 = 소유 uid 나 · 그룹·기타 비트 0 · 일반 파일 · 윈 = DACL read-back).
pub fn check_private_file(path: &std::path::Path) -> Result<(), String> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        let md = std::fs::symlink_metadata(path).map_err(|e| format!("{}: {e}", path.display()))?;
        // SAFETY: 인자 없는 조회.
        let me = unsafe { libc::geteuid() };
        if mutant("M3") {
            return Ok(());
        }
        if !md.file_type().is_file() || md.uid() != me || md.mode() & 0o077 != 0 {
            return Err(format!("갱신 파일 권한 불일치 {} (uid {} · mode {:o})", path.display(), md.uid(), md.mode() & 0o777));
        }
        Ok(())
    }
    #[cfg(windows)]
    {
        check_private_sd(path, "파일")
    }
}

/// 소유자 전용 파일 원자 쓰기(유닉스 0600 · 윈 = 폴더의 보호 DACL 상속).
pub fn write_private(path: &std::path::Path, bytes: &[u8]) -> Result<(), String> {
    if let Some(p) = path.parent() {
        ensure_private_dir(p)?;
    }
    crate::pack::write_atomic_mode(path, bytes, Some(0o600)).map_err(|e| format!("{}: {e}", path.display()))
}

/// 갱신 모듈 시험 중 env(`CYS_UPDATE_*`)를 바꾸는 시험끼리의 직렬화.
#[cfg(test)]
pub(crate) static TEST_ENV_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

#[cfg(test)]
mod tests {
    /// ★2R M3 · 5판: 윈 보안 기술자 read-back 의미 판정(순수 — 맥에서도 돈다). 러너 꼴(보호 폴더 안 파일 · 표지 없음)과 로컬 꼴(보호
    /// 폴더 · 상속 표지 · 사용자 프로필 상속)이 모두 통과 · Everyone·Users·인증 사용자·남의 SID·NULL DACL·남이 소유자 = 거부.
    #[test]
    fn sd_private_rule() {
        use super::sd_is_private as p;
        let me = "S-1-5-21-1-2-3-1001";
        assert!(p("O:S-1-5-21-1-2-3-1001D:(A;;FA;;;OW)(A;;FA;;;SY)", me), "러너 실측 꼴(표지 없음)");
        assert!(p("O:BAD:(A;;FA;;;OW)(A;;FA;;;SY)", me), "관리자 러너 = 소유자 BA");
        assert!(p("O:S-1-5-21-1-2-3-1001G:S-1-5-21-1-2-3-513D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)", me), "보호 폴더(그룹 칸 포함)");
        assert!(p("O:S-1-5-21-1-2-3-1001D:AI(A;ID;FA;;;OW)(A;ID;FA;;;SY)", me), "상속 표지");
        assert!(p("O:S-1-5-21-1-2-3-1001D:AI(A;OICIID;FA;;;SY)(A;OICIID;FA;;;BA)(A;OICIID;FA;;;S-1-5-21-1-2-3-1001)", me), "사용자 프로필 상속");
        assert!(p("O:S-1-5-21-1-2-3-1001D:(D;;FA;;;WD)(A;;FA;;;OW)", me), "거부 ACE 는 무관");
        assert!(p("O:S-1-5-21-1-2-3-1001D:P", me), "빈 DACL = 아무도 못 씀(허용)");
        assert!(!p("O:S-1-5-21-1-2-3-1001D:(A;;FA;;;OW)(A;;FR;;;WD)", me), "Everyone");
        assert!(!p("O:S-1-5-21-1-2-3-1001D:AI(A;OICIID;FA;;;OW)(A;OICIID;0x1200a9;;;BU)", me), "물려받은 Users");
        assert!(!p("O:S-1-5-21-1-2-3-1001D:(A;;FA;;;OW)(A;;FA;;;AU)", me), "인증 사용자");
        assert!(!p("O:S-1-5-21-1-2-3-1001D:(A;;FA;;;OW)(A;;FA;;;S-1-5-21-9-9-9-1002)", me), "남의 SID");
        assert!(!p("O:S-1-5-21-9-9-9-1002D:(A;;FA;;;OW)", me), "남이 소유자");
        assert!(!p("O:S-1-5-21-1-2-3-1001D:NO_ACCESS_CONTROL", me), "NULL DACL");
        assert!(!p("O:S-1-5-21-1-2-3-1001D:(OA;;FA;guid;;OW)", me), "개체 ACE");
        assert!(!p("D:(A;;FA;;;OW)", me), "소유자 칸 없음");
        assert!(!p("", me));
        assert!(p("O:SYD:(A;;FA;;;SY)", "S-1-5-18"), "SYSTEM 으로 도는 서비스");
    }
}
