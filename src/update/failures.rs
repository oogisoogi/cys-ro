//! 실패 분류(영구 격리 / 일시 백오프) — 설계 AUTO-UPDATE-118 §3-10 MA7 · `state.json.failures` · N8.
//!
//! - **영구 격리** = 서명·해시·구조·DR 핀·A2·build-info 불일치·V5/V7 위반·폐기된 릴리스 → 같은 `(component, channel, target,
//!   release_seq)` 재시도 0.
//! - **일시** = 시한 초과·전원·공간·drain 미저장·S5 재검사·S6/S8b 재확인·복원 지연·V2/V4 시한성 실패 → 6h·12h·24h·48h
//!   백오프 4회 · 4회를 넘으면 daily 칸에만 남기고 다음 릴리스를 기다린다(= 이 릴리스는 더 시도하지 않음).
//! - 경과는 §4-5 기다림 규칙(재부팅 = 보수)으로 잰다 — 이 모듈은 「다음 시도 가능 시각」만 계산한다.
//!
//! 오류코드(고정 사전)마다 분류를 한 번 정해 둔다 — 코드가 늘면 이 표의 `match` 가 컴파일 단계에서 빠짐을 알린다(와일드카드 0).

use super::errors::ErrCode;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Class {
    Permanent,
    Transient,
    /// 실패가 아님(결과 코드 · 판정 코드).
    NotAFailure,
}

pub fn classify(code: ErrCode) -> Class {
    use ErrCode::*;
    match code {
        // 서명·해시·구조·DR·A2·빌드 신원·폐기 = 영구
        FeedSigBad | ReleaseSigBad | Revoked | UrlRefused | DlSizeMismatch | DlShaMismatch | ArchiveRefused
        | MacDrMismatch | MacCdhashMismatch | MacCodesignFail | WinA2SigBad | WinImageMismatch | BuildInfoMismatch
        | PackMinBinaryEmpty | WinPayloadMismatch => Class::Permanent,
        // 만료·재생은 봉투가 다시 서명되면 풀린다 = 일시 · 시계·자원·환경 = 일시
        FeedExpired | FeedReplay | ClockSuspect | DiskLow | NoRollbackAsset | TxnBusy | RotateFailed | VerifyFailed
        | WinLaunchBlocked | WinInstallerFailed | WinSacOn | WinTaskRefused | RecoverAgentMissing | MacSwapUnsupported
        | MacAppsNotWritable => Class::Transient,
        // 결과·상태 코드(실패 기록 대상 아님)
        Ok | RollbackOk | RollbackFailed | RollbackBlocked | JournalCorrupt | RecoverAnomaly | InstalledRevoked => {
            Class::NotAFailure
        }
    }
}

/// 일시 실패 백오프 표(초) — 6h·12h·24h·48h.
pub const BACKOFF_SECS: [u64; 4] = [6 * 3600, 12 * 3600, 24 * 3600, 48 * 3600];

/// `count` 번째 일시 실패(1부터) 뒤 기다릴 시간 — 4회를 넘으면 None(이 릴리스 포기 · daily 칸).
pub fn backoff_after(count: u32) -> Option<u64> {
    if count == 0 {
        return Some(0);
    }
    BACKOFF_SECS.get(count as usize - 1).copied()
}

/// 지금 이 릴리스를 시도해도 되는가 — 영구 = 절대 아니오 · 일시 = 마지막 실패 뒤 경과 ≥ 백오프 · 4회 초과 = 아니오.
pub fn may_retry(class: Class, count: u32, elapsed_since_last_failure: u64) -> bool {
    match class {
        Class::Permanent => false,
        Class::NotAFailure => true,
        Class::Transient => match backoff_after(count) {
            Some(b) => elapsed_since_last_failure >= b,
            None => false,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_dictionary_code_has_a_class_and_design_examples_hold() {
        for c in ErrCode::ALL {
            let _ = classify(c); // 와일드카드 없는 match — 새 코드는 컴파일에서 걸린다
        }
        for c in [ErrCode::FeedSigBad, ErrCode::ReleaseSigBad, ErrCode::DlShaMismatch, ErrCode::MacDrMismatch,
            ErrCode::WinA2SigBad, ErrCode::BuildInfoMismatch, ErrCode::Revoked, ErrCode::ArchiveRefused] {
            assert_eq!(classify(c), Class::Permanent, "{c}");
        }
        for c in [ErrCode::DiskLow, ErrCode::ClockSuspect, ErrCode::RotateFailed, ErrCode::TxnBusy, ErrCode::FeedExpired] {
            assert_eq!(classify(c), Class::Transient, "{c}");
        }
        assert_eq!(classify(ErrCode::Ok), Class::NotAFailure);
    }

    #[test]
    fn backoff_four_times_then_give_up() {
        assert_eq!((1..=5).map(backoff_after).collect::<Vec<_>>(), vec![Some(21_600), Some(43_200), Some(86_400), Some(172_800), None]);
        assert!(!may_retry(Class::Transient, 1, 21_599));
        assert!(may_retry(Class::Transient, 1, 21_600));
        assert!(may_retry(Class::Transient, 4, 172_800));
        assert!(!may_retry(Class::Transient, 5, u64::MAX), "4회 초과 = 다음 릴리스");
        assert!(!may_retry(Class::Permanent, 0, u64::MAX), "영구 = 재시도 0");
    }
}
