//! 윈 전용 판독 — 스마트 앱 컨트롤(SAC) 상태(설계 AUTO-UPDATE-118 §2-0 O3 · 게이트 N12).
//!
//! 출처: 원작자 cys-terminal `up/v0.14.43` 커밋 `f7f3dbf7`(J2) `src-tauri/src/main.rs` 의 `parse_sac_state`·
//! `smart_app_control_state`(MIT · Copyright (c) 2026 CYSJavis) 를 **동작 그대로** 라이브러리로 옮겼다(📌15 편입 —
//! 앱 쪽 원본은 U4(T4-0) 가 정리할 때까지 그대로 둔다 · 핀 시험이 거기 걸려 있다). 바뀐 것 = 두 가지뿐:
//! ① 스폰 = 이 크레이트의 `hidden_command`(콘솔 창 숨김 · 원본의 `no_console` 과 같은 등급) ② 공개 함수.
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

/// 이 PC 의 SAC 상태 — "on" | "off" | "eval" | None(판정 불가·값 없음·윈도우 아님). 읽기 전용 · 최선 노력.
pub fn smart_app_control_state() -> Option<&'static str> {
    #[cfg(windows)]
    {
        let reg = std::env::var_os("SystemRoot")
            .map(|r| std::path::PathBuf::from(r).join("System32").join("reg.exe"))
            .unwrap_or_else(|| std::path::PathBuf::from("reg.exe"));
        let mut cmd = crate::hidden_command(reg);
        cmd.args(["query", r"HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy", "/v", "VerifiedAndReputablePolicyState"]);
        let out = cmd.output().ok()?;
        if !out.status.success() {
            return None;
        }
        return parse_sac_state(&String::from_utf8_lossy(&out.stdout));
    }
    #[allow(unreachable_code)]
    None
}

/// 게이트 N12 사실 — 윈 아님 = "n/a" · 윈에서 값 없음(SAC 없는 윈10 · `reg` 비 0 종료) = "absent"(보류 아님 — SAC 가 없으면
/// 4551 차단도 없다 · 실제로 막히면 설치기 실행 실패 분류 `classify_launch_error` 가 잡는다).
pub fn sac_fact() -> String {
    if cfg!(windows) {
        smart_app_control_state().unwrap_or("absent").to_string()
    } else {
        "n/a".to_string()
    }
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
            assert_eq!(sac_fact(), "n/a");
            assert_eq!(smart_app_control_state(), None);
        }
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
