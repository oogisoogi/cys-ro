//! 복원 디렉티브 **1좌석 1회 주입** 표식 — 겹치는 복원 경로가 같은 좌석에 거듭 주입하는 것을 막는다.
//!
//! # 고치는 결함(TICKET=v111-restore ②)
//! 복원은 **경로가 둘 이상 겹치도록 설계돼 있다**. 저장소 자신이 그렇게 적어 두었다:
//! `src-tauri/src/main.rs` 의 조직 복원 주석 — 「재기동된 부서 데몬은 콜드부트 auto-restore 로
//! 노드를 되살린다 … **run_restore 멱등이라 콜드부트 복원과 겹쳐도 안전**」.
//! 그 「멱등」이 보장한 것은 **좌석 중복 스폰이 없다**는 것까지였고(이미 살아 있는 역할은
//! `live.contains(role)` 로 건너뛴다), **주입이 중복되지 않는다**는 것까지가 아니었다.
//! 2026-09-21 실기에서 워커 자리 하나가 같은 목적의 깨움 글 3건(RESTORE 2 · RESUME 1)을 받은
//! 자리가 여기다.
//!
//! # 무엇을 보장하고, 무엇을 보장하지 않는가(위협 모델)
//! · **보장**: 같은 좌석(surface_id)에 대해 **TTL 안에서** 복원 디렉티브 주입은 1회다.
//!   먼저 도착한 경로가 이긴다(`create_new` = 커널 원자성 — 두 프로세스가 동시에 와도 하나만 만든다).
//! · **보장하지 않음**: TTL 밖의 재주입은 막지 않는다 — 막으면 안 되기 때문이다. 좌석이 몇 분 뒤
//!   진짜로 다시 죽어 복원되는 것은 **정당한 재주입**이고, 영구 표식은 그 자리를 영원히 말 없는
//!   좌석으로 만든다(조용한 복원 실패 = 지금 고치는 것보다 비싼 병).
//! · **보장하지 않음**: 표식은 좌석 번호로만 센다. 좌석이 새로 태어나면(fresh 기동) 번호가 달라
//!   표식이 없고, 그것이 옳다 — 새 좌석은 아직 아무 글도 받지 않았다.
//!
//! # 판정은 순수 함수다
//! 파일 입출력은 호출부(`cys.rs`)가 하고, 이 모듈은 **언제를 중복으로 볼지**만 정한다 —
//! 시계·파일계를 시험에 끌고 오지 않고 경계값을 직접 때릴 수 있게.

/// 복원 겹침 창(초). 한 번의 앱 기동에서 겹치는 복원 경로들은 이 안에서 전부 도착한다
/// (콜드부트 auto-restore + 업데이트 후 사이드카 restore + 부서 순회).
pub const RESTORE_MARK_TTL_SECS: u64 = 300;

/// 표식 파일이 들어갈 상태 폴더 안의 상대 경로(좌석 1개 = 파일 1개).
pub fn mark_rel_path(surface_id: u64) -> String {
    format!("restore-mark/{surface_id}")
}

/// `existing_at` = 이 좌석에 마지막으로 복원 글을 넣은 시각(초 · 없으면 `None`).
/// 참이면 **지금 주입은 중복**이다(다른 복원 경로가 방금 넣었다).
///
/// 시계가 뒤로 간 경우(`existing_at > now`)도 중복으로 본다 — 표식이 존재한다는 사실이
/// 시계보다 강한 증거이고, 여기서 fail-open 하면 정확히 고치려던 중복이 되살아난다.
pub fn is_duplicate(existing_at: Option<u64>, now: u64, ttl: u64) -> bool {
    match existing_at {
        None => false,
        Some(at) if at > now => true,
        Some(at) => now < at.saturating_add(ttl),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn no_mark_is_not_duplicate() {
        assert!(!is_duplicate(None, 1_000, RESTORE_MARK_TTL_SECS));
    }

    #[test]
    fn fresh_mark_is_duplicate() {
        // 같은 앱 기동에서 두 번째 복원 경로가 10초 뒤 도착 — 주입하지 않는다.
        assert!(is_duplicate(Some(1_000), 1_010, RESTORE_MARK_TTL_SECS));
    }

    #[test]
    fn boundary_exactly_ttl_is_not_duplicate() {
        // ★경계: 창은 반열림 [at, at+ttl) 이다. 정확히 ttl 은 **밖**이다(한 값만 어긋나도
        //   「영구 표식」과 「무표식」 사이를 오간다 — 부등호를 직접 못박는다).
        assert!(!is_duplicate(Some(1_000), 1_000 + RESTORE_MARK_TTL_SECS, RESTORE_MARK_TTL_SECS));
        assert!(is_duplicate(Some(1_000), 1_000 + RESTORE_MARK_TTL_SECS - 1, RESTORE_MARK_TTL_SECS));
    }

    #[test]
    fn stale_mark_allows_reinjection() {
        // 몇 시간 뒤 좌석이 진짜로 죽어 복원됐다 — 그때는 말을 걸어야 한다(조용한 복원 금지).
        assert!(!is_duplicate(Some(1_000), 1_000 + 86_400, RESTORE_MARK_TTL_SECS));
    }

    #[test]
    fn clock_going_backwards_stays_duplicate() {
        assert!(is_duplicate(Some(2_000), 1_000, RESTORE_MARK_TTL_SECS));
    }

    #[test]
    fn overflow_saturates_instead_of_panicking_or_wrapping() {
        // 평범한 `at + ttl` 이면 여기서 debug 빌드는 패닉, release 는 0 근처로 뒤집혀
        // 「중복 아님」이 된다. saturating_add 는 u64::MAX 에서 멈춘다.
        assert!(is_duplicate(Some(u64::MAX - 1), u64::MAX - 1, RESTORE_MARK_TTL_SECS));
        // 그 포화 지점이 창의 끝이다(반열림 [at, MAX) — now==MAX 는 밖).
        assert!(!is_duplicate(Some(u64::MAX - 1), u64::MAX, RESTORE_MARK_TTL_SECS));
    }

    #[test]
    fn path_is_per_seat() {
        assert_eq!(mark_rel_path(886), "restore-mark/886");
        assert_ne!(mark_rel_path(886), mark_rel_path(887));
    }
}
