//! D23 자동 경로 팩 하한 게이트(설계 AUTO-UPDATE-118 §3-8 · 윈 실측 [master#565f27a7]).
//!
//! 자동 경로(러너·T3)에서 팩 매니페스트의 `min_binary_version` 이 비었거나 파싱 불가면 **거부**(`update.pack_min_binary_empty`).
//! 현행 `version_gates`(cys.rs)는 빈 값 = 「제약 없음 = Apply」라 수동 경로는 그대로 두되, 서명 단계의 cutover 는
//! `packsig::MIN_BINARY_REQUIRED_EPOCH` 가 맡는다(옛 서명본 하위 호환). 릴리스 본문의 `requires.min_binary_for_pack` 빈 값은
//! `feed::verify_feed` ⓛ 가 같은 코드로 거부한다.

use super::errors::{ErrCode, UpdateErr};

pub fn pack_min_binary_gate(min_binary_version: &str) -> Result<(u32, u32, u32), UpdateErr> {
    crate::pack::parse_semver(min_binary_version.trim()).ok_or_else(|| {
        UpdateErr::new(ErrCode::PackMinBinaryEmpty, "D23", format!("min_binary_version {min_binary_version:?}"))
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_or_unparsable_rejected() {
        for bad in ["", "   ", "latest", "v"] {
            assert_eq!(pack_min_binary_gate(bad).unwrap_err().code, ErrCode::PackMinBinaryEmpty, "{bad:?}");
        }
        assert_eq!(pack_min_binary_gate("1.1.8").unwrap(), (1, 1, 8));
        assert_eq!(pack_min_binary_gate(" 1.1.8 ").unwrap(), (1, 1, 8));
    }
}
