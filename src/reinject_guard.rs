//! `cys reinject --check`(지침 각성 확인 핑 → 무응답이면 디렉티브 전문 재주입)의 **폭주 차단**.
//!
//! # 고치는 결함(TICKET=v112-wake ② · 1.0.1 참가자 기기 실기)
//! 5자리 전부에 「지침 각성 확인 핑」과 디렉티브 전문이 약 1분 간격으로 반복 주입돼 자리 3개가
//! CTX 100% 에 닿았다. 핑의 발신자(phoenix `stage_reinject`·`stage_g2_ack`)는 복원이 돌 때마다
//! 부르고, 복원 단계 표식은 데몬 기동 시각에 묶여 데몬이 다시 뜰 때마다 초기화된다. 그런데
//! `run_reinject` 자신에는 **「이미 깨어 있다」 기억도 · 시도 상한도 · 간격도 없었다** — 부르는 쪽이
//! 몇 번을 부르든 그대로 핑을 넣고, 짧은 대기(4~6초)에 ACK 가 안 보이면 전문을 쏟았다.
//!
//! # 보장(위협 모델)
//! · **보장**: 같은 좌석에 대해 ⑴ ACK 를 받은 뒤 `AWAKE_TTL_SECS` 안에는 핑·전문 0회
//!   ⑵ 1시간에 핑 시도 `HOURLY_CAP` 회 이하 ⑶ 연속 시도 사이 지수 간격(120s·240s·…).
//!   기록은 상태 폴더 파일이라 **데몬 재기동을 넘어 유지**된다(1.0.1 폭주의 재료가 바로 재기동이었다).
//! · **보장하지 않음**: 강제 주입(`--check` 없는 reinject · CEO 승격 경로)은 막지 않는다 —
//!   그것은 사람·조건 게이트가 이미 거른 명시 행동이다. 좌석 번호가 바뀐 새 좌석은 기록이 없다(옳다).
//!
//! 판정은 순수 함수다 — 파일 입출력과 시계는 호출부(`cys.rs`)가 한다.

use serde::{Deserialize, Serialize};

/// ACK(디렉티브 생존 확인)를 받은 뒤 다시 확인하지 않는 창(초).
pub const AWAKE_TTL_SECS: u64 = 3600;
/// 1시간 안 핑 시도 상한.
pub const HOURLY_CAP: usize = 3;
/// 첫 재시도 최소 간격(초). n번째 시도 뒤엔 `BACKOFF_BASE_SECS × 2^(n-1)`.
pub const BACKOFF_BASE_SECS: u64 = 120;

/// 좌석 1개의 기록(파일 1개 = JSON 1개).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct SeatRecord {
    /// 마지막 ACK 수신 시각(epoch 초).
    #[serde(default)]
    pub ack_at: Option<u64>,
    /// 최근 핑 시도 시각들(epoch 초 · 1시간 넘은 것은 솎는다).
    #[serde(default)]
    pub attempts: Vec<u64>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Decision {
    /// 핑을 보내도 된다.
    Allow,
    /// 보내지 않는다 — 사유(원장·출력용).
    Skip(&'static str),
}

/// 좌석 기록 파일의 상태 폴더 안 상대 경로.
pub fn record_rel_path(surface_id: u64) -> String {
    format!("reinject-guard/{surface_id}.json")
}

/// 판정 순서가 계약이다: 깨어 있음 → 시간당 상한 → 간격.
/// 시계가 뒤로 간 기록(미래 시각)은 「방금 있었다」로 본다 — 기록이 시계보다 강한 증거다.
pub fn decide(rec: &SeatRecord, now: u64) -> Decision {
    if let Some(ack) = rec.ack_at {
        if ack > now || now - ack < AWAKE_TTL_SECS {
            return Decision::Skip("awake");
        }
    }
    let recent: Vec<u64> = rec
        .attempts
        .iter()
        .copied()
        .filter(|t| *t > now || now - t < 3600)
        .collect();
    if recent.len() >= HOURLY_CAP {
        return Decision::Skip("hourly_cap");
    }
    if let Some(last) = recent.iter().max().copied() {
        let n = recent.len() as u32; // ≥1
        let gap = BACKOFF_BASE_SECS.saturating_mul(1u64 << (n - 1).min(16));
        if last > now || now - last < gap {
            return Decision::Skip("backoff");
        }
    }
    Decision::Allow
}

/// 시도 기록(핑을 보내기 **전에** 쓴다 — 핑 뒤에 죽어도 시도는 센다).
pub fn record_attempt(rec: &mut SeatRecord, now: u64) {
    rec.attempts.retain(|t| *t > now || now - t < 3600);
    rec.attempts.push(now);
}

/// ACK 수신 — 깨어 있음 기록 + 시도 이력 비움(즉시 정지).
pub fn record_ack(rec: &mut SeatRecord, now: u64) {
    rec.ack_at = Some(now);
    rec.attempts.clear();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_record_allows() {
        assert_eq!(decide(&SeatRecord::default(), 10_000), Decision::Allow);
    }

    #[test]
    fn ack_silences_for_the_ttl_then_releases() {
        let mut r = SeatRecord::default();
        record_ack(&mut r, 10_000);
        assert_eq!(decide(&r, 10_060), Decision::Skip("awake"));
        assert_eq!(decide(&r, 10_000 + AWAKE_TTL_SECS - 1), Decision::Skip("awake"));
        assert_eq!(decide(&r, 10_000 + AWAKE_TTL_SECS), Decision::Allow);
    }

    #[test]
    fn one_minute_cadence_is_cut_to_backoff_and_cap() {
        // 1.0.1 폭주 흉내: 부르는 쪽이 60초마다 부른다 — 1시간 동안 허용은 3회 이하여야 한다.
        let mut r = SeatRecord::default();
        let mut allowed = 0;
        for i in 0..60u64 {
            let now = 100_000 + i * 60;
            if decide(&r, now) == Decision::Allow {
                record_attempt(&mut r, now);
                allowed += 1;
            }
        }
        assert!(allowed <= HOURLY_CAP, "1시간 60회 호출 중 허용 {allowed}");
        assert!(allowed >= 2, "간격을 지나면 재시도는 허용돼야 한다(조용한 영구 정지 금지) — {allowed}");
    }

    #[test]
    fn backoff_doubles() {
        let mut r = SeatRecord::default();
        record_attempt(&mut r, 1_000);
        assert_eq!(decide(&r, 1_000 + BACKOFF_BASE_SECS - 1), Decision::Skip("backoff"));
        assert_eq!(decide(&r, 1_000 + BACKOFF_BASE_SECS), Decision::Allow);
        record_attempt(&mut r, 1_120);
        assert_eq!(decide(&r, 1_120 + 2 * BACKOFF_BASE_SECS - 1), Decision::Skip("backoff"));
        assert_eq!(decide(&r, 1_120 + 2 * BACKOFF_BASE_SECS), Decision::Allow);
    }

    #[test]
    fn ack_clears_attempts() {
        let mut r = SeatRecord::default();
        record_attempt(&mut r, 1_000);
        record_attempt(&mut r, 1_200);
        record_ack(&mut r, 1_300);
        assert!(r.attempts.is_empty());
    }
}
