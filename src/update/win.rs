//! 윈 전용 판독 — 스마트 앱 컨트롤(SAC) 상태(설계 AUTO-UPDATE-118 §2-0 O3 · 게이트 N12).
//!
//! 출처: 원작자 cys-terminal `up/v0.14.43` 커밋 `f7f3dbf7`(J2) `src-tauri/src/main.rs` 의 `parse_sac_state`·
//! `smart_app_control_state`(MIT · Copyright (c) 2026 CYSJavis) 를 **동작 그대로** 라이브러리로 옮겼다(📌15 편입 —
//! 앱 쪽 원본은 U4(T4-0) 가 정리할 때까지 그대로 둔다 · 핀 시험이 거기 걸려 있다). 바뀐 것 = 두 가지뿐:
//! ① 공개 함수 ② (2판 · 1R M2) 판독 경로 = `reg.exe` 스폰 대신 `RegGetValueW` 직접 호출 — 「값 없음(ERROR_FILE_NOT_FOUND)」과
//! 「읽기 실패」를 가르기 위해서다. 출력 판정 규칙(`parse_sac_state` · 0/1/2 = off/on/eval)은 원작자 그대로 남겨 대조 시험이 지킨다.
//! **읽기만** 한다 — 끄라는 안내·우회 코드 0(원작자 원칙 「보안 기능을 끄라는 지시를 제품이 하지 않는다」).

/// `reg query` 출력에서 SAC 상태를 읽는다 — `VerifiedAndReputablePolicyState    REG_DWORD    0x1` 꼴의 줄을 찾아
/// `0x0` → "off" · `0x1` → "on" · `0x2` → "eval"(평가 모드) · 그 밖·줄 없음 → None. 값 이름은 대소문자를 가리지 않고
/// 칸 사이 공백은 가변이다. 순수 함수(양쪽 OS 에서 컴파일·시험).
pub fn parse_sac_state(reg_stdout: &str) -> Option<&'static str> {
    for line in reg_stdout.lines() {
        let mut cols = line.split_whitespace();
        let (Some(name), Some(kind), Some(value)) = (cols.next(), cols.next(), cols.next()) else {
            continue;
        };
        if !name.eq_ignore_ascii_case("VerifiedAndReputablePolicyState") || !kind.eq_ignore_ascii_case("REG_DWORD") {
            continue;
        }
        let hex = value.strip_prefix("0x").or_else(|| value.strip_prefix("0X"))?;
        return match u32::from_str_radix(hex, 16).ok()? {
            0 => Some("off"),
            1 => Some("on"),
            2 => Some("eval"),
            _ => None,
        };
    }
    None
}

/// 레지스트리 판독 결과(1R MAJOR M2 — 「값 없음」과 「읽기 실패」를 가른다).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SacRead {
    /// REG_DWORD 값.
    Value(u32),
    /// `ERROR_FILE_NOT_FOUND`(2) — 키·값이 없다(SAC 없는 윈10 등).
    NotFound,
    /// 그 밖의 Win32 오류(접근 거부·형식 다름 등).
    Error(u32),
}

/// N12 사실 분류 — 값 0/1/2 = off/on/eval · 값 없음 = "absent" · 미지 DWORD·읽기 오류 = None(판정 불가 = 보류).
pub fn classify_sac(r: SacRead) -> Option<&'static str> {
    match r {
        SacRead::Value(0) => Some("off"),
        SacRead::Value(1) => Some("on"),
        SacRead::Value(2) => Some("eval"),
        SacRead::Value(_) => None,
        SacRead::NotFound => Some("absent"),
        SacRead::Error(_) if super::mutant("M2") => Some("absent"),
        SacRead::Error(_) => None,
    }
}

/// 윈 레지스트리 직접 판독(`RegGetValueW` · `RRF_RT_REG_DWORD` — 스폰 0 · 읽기만). 원작자 판은 `reg.exe` 출력을 읽었으나
/// 그 길은 「값 없음」과 「실행·권한 실패」를 같은 비 0 종료로 합친다(1R M2) — 그래서 오류 코드를 직접 받는다.
#[cfg(windows)]
pub fn read_sac_registry() -> SacRead {
    use windows_sys::Win32::System::Registry::{RegGetValueW, HKEY_LOCAL_MACHINE, RRF_RT_REG_DWORD};
    let w = |s: &str| s.encode_utf16().chain(std::iter::once(0)).collect::<Vec<u16>>();
    let sub = w(r"SYSTEM\CurrentControlSet\Control\CI\Policy");
    let val = w("VerifiedAndReputablePolicyState");
    let mut data: u32 = 0;
    let mut size: u32 = std::mem::size_of::<u32>() as u32;
    // SAFETY: 널종단 와이드 문자열 · data/size 는 유효한 지역 변수.
    let rc = unsafe {
        RegGetValueW(
            HKEY_LOCAL_MACHINE,
            sub.as_ptr(),
            val.as_ptr(),
            RRF_RT_REG_DWORD,
            std::ptr::null_mut(),
            &mut data as *mut u32 as *mut core::ffi::c_void,
            &mut size,
        )
    };
    match rc {
        0 => SacRead::Value(data),
        2 => SacRead::NotFound,
        e => SacRead::Error(e),
    }
}

/// 게이트 N12 사실 — 윈 아님 = "n/a" · 윈 = [`classify_sac`]`(`[`read_sac_registry`]`)`.
pub fn sac_fact() -> Option<String> {
    #[cfg(windows)]
    {
        return classify_sac(read_sac_registry()).map(str::to_string);
    }
    #[allow(unreachable_code)]
    Some("n/a".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 원작자 시험 사례 그대로(@up/v0.14.43 `src-tauri/src/main.rs` `j2_parse_sac_state_reads_reg_query_output`).
    #[test]
    fn j2_parse_sac_state_reads_reg_query_output() {
        let head = "\r\nHKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\CI\\Policy\r\n";
        let sample = |hex: &str| format!("{head}    VerifiedAndReputablePolicyState    REG_DWORD    {hex}\r\n\r\n");
        assert_eq!(parse_sac_state(&sample("0x0")), Some("off"));
        assert_eq!(parse_sac_state(&sample("0x1")), Some("on"));
        assert_eq!(parse_sac_state(&sample("0x2")), Some("eval"));
        assert_eq!(
            parse_sac_state("HKEY_LOCAL_MACHINE\\X\n    verifiedandreputablepolicystate\treg_dword\t0x1\n"),
            Some("on")
        );
        assert_eq!(parse_sac_state("VERIFIEDANDREPUTABLEPOLICYSTATE REG_DWORD 0x2"), Some("eval"));
        assert_eq!(
            parse_sac_state("\r\nERROR: The system was unable to find the specified registry key or value.\r\n"),
            None
        );
        assert_eq!(parse_sac_state(""), None);
        assert_eq!(parse_sac_state("   \r\n\r\n"), None);
        assert_eq!(parse_sac_state(&sample("0x7")), None);
        assert_eq!(parse_sac_state(&sample("0x")), None);
        assert_eq!(parse_sac_state(&sample("1")), None, "0x 접두 없는 값은 읽지 않는다");
        assert_eq!(parse_sac_state("    VerifiedAndReputablePolicyState    REG_SZ    0x1\r\n"), None);
    }

    #[test]
    fn sac_fact_off_windows_is_na() {
        if !cfg!(windows) {
            assert_eq!(sac_fact().as_deref(), Some("n/a"));
        }
    }

    /// 1R M2 뮤테이션: 값 없음(2)만 absent · 접근 거부(5)·형식 다름(1630 등)·미지 DWORD = None(보류).
    #[test]
    fn m2_only_file_not_found_is_absent() {
        assert_eq!(classify_sac(SacRead::NotFound), Some("absent"));
        assert_eq!(classify_sac(SacRead::Error(5)), None);
        assert_eq!(classify_sac(SacRead::Error(1630)), None);
        assert_eq!(classify_sac(SacRead::Value(7)), None);
        assert_eq!(classify_sac(SacRead::Value(1)), Some("on"));
        assert_eq!(classify_sac(SacRead::Value(0)), Some("off"));
        assert_eq!(classify_sac(SacRead::Value(2)), Some("eval"));
    }

    /// 앱 쪽 원본(src-tauri)과 판독 규칙이 갈라지지 않았는지 — 두 함수 본문의 판정 줄이 같다.
    #[test]
    fn same_rules_as_app_original() {
        let app = include_str!("../../src-tauri/src/main.rs");
        for needle in [
            "if !name.eq_ignore_ascii_case(\"VerifiedAndReputablePolicyState\") || !kind.eq_ignore_ascii_case(\"REG_DWORD\") {",
            "0 => Some(\"off\"),",
            "1 => Some(\"on\"),",
            "2 => Some(\"eval\"),",
        ] {
            assert!(app.contains(needle), "앱 원본에서 사라짐: {needle}");
            assert!(include_str!("win.rs").contains(needle));
        }
    }
}
