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

/// 소유자 전용 폴더(1R MAJOR · 설계 §3-2 「소유자 전용 ACL」): 유닉스 = 만들 때부터 0700 + 재검증(모드 그룹·기타 비트 0 ·
/// 소유 uid = 나) · 윈 = 보호된 DACL `D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)`(소유자·SYSTEM 만 · 상속 끊음 — cysd 파이프 owner-only
/// SDDL 과 같은 꼴에서 BA 를 뺀 것). 어긋나면 Err(fail-closed).
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
        use windows_sys::Win32::Security::{SetFileSecurityW, DACL_SECURITY_INFORMATION, PROTECTED_DACL_SECURITY_INFORMATION, PSECURITY_DESCRIPTOR};
        std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
        let sddl: Vec<u16> = "D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)".encode_utf16().chain(std::iter::once(0)).collect();
        let mut psd: PSECURITY_DESCRIPTOR = std::ptr::null_mut();
        // SAFETY: 널종단 와이드 문자열 · psd 는 성공 시 LocalAlloc 블록(아래에서 해제).
        let ok = unsafe { ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.as_ptr(), SDDL_REVISION_1, &mut psd, std::ptr::null_mut()) };
        if ok == 0 || psd.is_null() {
            return Err("DACL 조립 실패".into());
        }
        let wpath: Vec<u16> = dir.as_os_str().encode_wide().chain(std::iter::once(0)).collect();
        // SAFETY: 경로·psd 유효.
        let set = unsafe { SetFileSecurityW(wpath.as_ptr(), DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION, psd) };
        // SAFETY: Convert… 가 LocalAlloc 으로 준 블록.
        unsafe { windows_sys::Win32::Foundation::LocalFree(psd as _) };
        if set == 0 {
            return Err(format!("갱신 폴더 DACL 적용 실패 {}", dir.display()));
        }
        Ok(())
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
