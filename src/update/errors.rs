//! 갱신 오류코드 = **고정 사전**(설계 AUTO-UPDATE-118 §3-12 · 4판).
//!
//! 사전에 없는 코드는 만들 수 없다 — 코드는 이 열거형의 변형뿐이고 문자열은 [`ErrCode::as_str`] 한 곳에서만 나온다.
//! 세부값(어느 단계·rc·OS 코드)은 코드에 섞지 않고 [`UpdateErr`] 의 별도 칸(`step`·`detail`)에 담는다(§3-12 「세부값은
//! 별도 칸 `{step, rc, verify, os_code, token}` · 전부 ≤48자」). 아고라 클라이언트(T3)는 같은 사전을 `agora_update.` 접두로
//! 쓴다(§6-3) — 접두만 다르고 낱말은 같다([`ErrCode::with_prefix`]).

use std::fmt;

/// §3-12 고정 사전 — 37개(순서 = 설계 문서 나열 순서 그대로).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ErrCode {
    FeedSigBad,
    FeedExpired,
    FeedReplay,
    ReleaseSigBad,
    Revoked,
    InstalledRevoked,
    UrlRefused,
    DlSizeMismatch,
    DlShaMismatch,
    ArchiveRefused,
    MacDrMismatch,
    MacCdhashMismatch,
    MacCodesignFail,
    MacSwapUnsupported,
    MacAppsNotWritable,
    WinA2SigBad,
    WinLaunchBlocked,
    WinInstallerFailed,
    WinPayloadMismatch,
    WinImageMismatch,
    WinSacOn,
    WinTaskRefused,
    RecoverAgentMissing,
    TxnBusy,
    BuildInfoMismatch,
    NoRollbackAsset,
    DiskLow,
    ClockSuspect,
    RotateFailed,
    VerifyFailed,
    RollbackOk,
    RollbackFailed,
    RollbackBlocked,
    JournalCorrupt,
    RecoverAnomaly,
    PackMinBinaryEmpty,
    Ok,
}

impl ErrCode {
    /// 사전 전체(시험·문서 대조용 — 설계 §3-12 나열 순서).
    pub const ALL: [ErrCode; 37] = [
        ErrCode::FeedSigBad,
        ErrCode::FeedExpired,
        ErrCode::FeedReplay,
        ErrCode::ReleaseSigBad,
        ErrCode::Revoked,
        ErrCode::InstalledRevoked,
        ErrCode::UrlRefused,
        ErrCode::DlSizeMismatch,
        ErrCode::DlShaMismatch,
        ErrCode::ArchiveRefused,
        ErrCode::MacDrMismatch,
        ErrCode::MacCdhashMismatch,
        ErrCode::MacCodesignFail,
        ErrCode::MacSwapUnsupported,
        ErrCode::MacAppsNotWritable,
        ErrCode::WinA2SigBad,
        ErrCode::WinLaunchBlocked,
        ErrCode::WinInstallerFailed,
        ErrCode::WinPayloadMismatch,
        ErrCode::WinImageMismatch,
        ErrCode::WinSacOn,
        ErrCode::WinTaskRefused,
        ErrCode::RecoverAgentMissing,
        ErrCode::TxnBusy,
        ErrCode::BuildInfoMismatch,
        ErrCode::NoRollbackAsset,
        ErrCode::DiskLow,
        ErrCode::ClockSuspect,
        ErrCode::RotateFailed,
        ErrCode::VerifyFailed,
        ErrCode::RollbackOk,
        ErrCode::RollbackFailed,
        ErrCode::RollbackBlocked,
        ErrCode::JournalCorrupt,
        ErrCode::RecoverAnomaly,
        ErrCode::PackMinBinaryEmpty,
        ErrCode::Ok,
    ];

    /// 접두 없는 낱말(`feed_sig_bad` 등).
    pub fn word(self) -> &'static str {
        match self {
            ErrCode::FeedSigBad => "feed_sig_bad",
            ErrCode::FeedExpired => "feed_expired",
            ErrCode::FeedReplay => "feed_replay",
            ErrCode::ReleaseSigBad => "release_sig_bad",
            ErrCode::Revoked => "revoked",
            ErrCode::InstalledRevoked => "installed_revoked",
            ErrCode::UrlRefused => "url_refused",
            ErrCode::DlSizeMismatch => "dl_size_mismatch",
            ErrCode::DlShaMismatch => "dl_sha_mismatch",
            ErrCode::ArchiveRefused => "archive_refused",
            ErrCode::MacDrMismatch => "mac_dr_mismatch",
            ErrCode::MacCdhashMismatch => "mac_cdhash_mismatch",
            ErrCode::MacCodesignFail => "mac_codesign_fail",
            ErrCode::MacSwapUnsupported => "mac_swap_unsupported",
            ErrCode::MacAppsNotWritable => "mac_apps_not_writable",
            ErrCode::WinA2SigBad => "win_a2_sig_bad",
            ErrCode::WinLaunchBlocked => "win_launch_blocked",
            ErrCode::WinInstallerFailed => "win_installer_failed",
            ErrCode::WinPayloadMismatch => "win_payload_mismatch",
            ErrCode::WinImageMismatch => "win_image_mismatch",
            ErrCode::WinSacOn => "win_sac_on",
            ErrCode::WinTaskRefused => "win_task_refused",
            ErrCode::RecoverAgentMissing => "recover_agent_missing",
            ErrCode::TxnBusy => "txn_busy",
            ErrCode::BuildInfoMismatch => "build_info_mismatch",
            ErrCode::NoRollbackAsset => "no_rollback_asset",
            ErrCode::DiskLow => "disk_low",
            ErrCode::ClockSuspect => "clock_suspect",
            ErrCode::RotateFailed => "rotate_failed",
            ErrCode::VerifyFailed => "verify_failed",
            ErrCode::RollbackOk => "rollback_ok",
            ErrCode::RollbackFailed => "rollback_failed",
            ErrCode::RollbackBlocked => "rollback_blocked",
            ErrCode::JournalCorrupt => "journal_corrupt",
            ErrCode::RecoverAnomaly => "recover_anomaly",
            ErrCode::PackMinBinaryEmpty => "pack_min_binary_empty",
            ErrCode::Ok => "ok",
        }
    }

    /// 데몬 갱신 신호 코드(`update.<낱말>`).
    pub fn as_str(self) -> String {
        self.with_prefix("update")
    }

    /// 부품별 접두(`update` | `agora_update` — §6-3).
    pub fn with_prefix(self, prefix: &str) -> String {
        format!("{prefix}.{}", self.word())
    }

    /// 사전 역조회(`update.` 접두 필수) — 사전 밖 문자열은 None.
    pub fn parse(s: &str) -> Option<ErrCode> {
        let w = s.strip_prefix("update.")?;
        ErrCode::ALL.iter().copied().find(|c| c.word() == w)
    }

    /// 「그날 이미 보냈어도 즉시 1통」 코드(§3-12 예외 4종).
    pub fn is_immediate(self) -> bool {
        matches!(
            self,
            ErrCode::RollbackFailed | ErrCode::RollbackBlocked | ErrCode::JournalCorrupt | ErrCode::InstalledRevoked
        )
    }
}

impl fmt::Display for ErrCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.as_str())
    }
}

/// 세부값 칸의 길이 상한(§3-12 「전부 ≤48자」).
pub const DETAIL_MAX_CHARS: usize = 48;

/// 갱신 오류 — 사전 코드 1개 + 세부 칸(단계 표지 · 짧은 사유). 세부 칸은 48자에서 자른다(신호 서식 상한).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UpdateErr {
    pub code: ErrCode,
    /// 검증 단계 표지(예: `"ⓓ"`·`"N13"`·`"S2"`).
    pub step: String,
    /// 사람이 읽는 짧은 사유(≤48자로 잘림).
    pub detail: String,
}

impl UpdateErr {
    pub fn new(code: ErrCode, step: &str, detail: impl Into<String>) -> Self {
        UpdateErr { code, step: clip(step), detail: clip(&detail.into()) }
    }
}

impl fmt::Display for UpdateErr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} [{}] {}", self.code, self.step, self.detail)
    }
}

impl std::error::Error for UpdateErr {}

/// 문자 단위로 48자에서 자른다(바이트가 아니라 글자 — 한국어 사유가 중간에서 깨지지 않게).
pub fn clip(s: &str) -> String {
    s.chars().take(DETAIL_MAX_CHARS).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 사전 = 설계 §3-12 나열 그대로(37개 · 순서 포함). 설계 문서의 문자열을 여기 그대로 박아 대조한다 —
    /// 코드를 하나 더하거나 이름을 바꾸면 이 시험이 적색이다(「고정 사전」 계약).
    #[test]
    fn dictionary_is_design_3_12_verbatim() {
        let design = "update.feed_sig_bad · update.feed_expired · update.feed_replay · update.release_sig_bad · \
            update.revoked · update.installed_revoked · update.url_refused · update.dl_size_mismatch · \
            update.dl_sha_mismatch · update.archive_refused · update.mac_dr_mismatch · update.mac_cdhash_mismatch · \
            update.mac_codesign_fail · update.mac_swap_unsupported · update.mac_apps_not_writable · \
            update.win_a2_sig_bad · update.win_launch_blocked · update.win_installer_failed · \
            update.win_payload_mismatch · update.win_image_mismatch · update.win_sac_on · update.win_task_refused · \
            update.recover_agent_missing · update.txn_busy · update.build_info_mismatch · update.no_rollback_asset · \
            update.disk_low · update.clock_suspect · update.rotate_failed · update.verify_failed · \
            update.rollback_ok · update.rollback_failed · update.rollback_blocked · update.journal_corrupt · \
            update.recover_anomaly · update.pack_min_binary_empty · update.ok";
        let want: Vec<&str> = design.split('·').map(|s| s.trim()).collect();
        let got: Vec<String> = ErrCode::ALL.iter().map(|c| c.as_str()).collect();
        assert_eq!(got, want);
        // 중복 0
        let set: std::collections::BTreeSet<&String> = got.iter().collect();
        assert_eq!(set.len(), got.len());
    }

    #[test]
    fn codes_fit_48_chars_with_both_prefixes() {
        for c in ErrCode::ALL {
            assert!(c.as_str().chars().count() <= DETAIL_MAX_CHARS, "{c}");
            assert!(c.with_prefix("agora_update").chars().count() <= DETAIL_MAX_CHARS, "{c}");
        }
    }

    #[test]
    fn parse_roundtrip_and_outside_dictionary_is_none() {
        for c in ErrCode::ALL {
            assert_eq!(ErrCode::parse(&c.as_str()), Some(c));
        }
        assert_eq!(ErrCode::parse("update.mac.swap_unsupported"), None); // 점 표기는 사전 밖(§3-6 본문 표기 ≠ 사전)
        assert_eq!(ErrCode::parse("feed_sig_bad"), None);
        assert_eq!(ErrCode::parse("update.whatever"), None);
    }

    #[test]
    fn immediate_set_is_the_four_exceptions() {
        let imm: Vec<ErrCode> = ErrCode::ALL.iter().copied().filter(|c| c.is_immediate()).collect();
        assert_eq!(
            imm,
            vec![ErrCode::InstalledRevoked, ErrCode::RollbackFailed, ErrCode::RollbackBlocked, ErrCode::JournalCorrupt]
        );
    }

    #[test]
    fn detail_is_clipped_by_chars_not_bytes() {
        let e = UpdateErr::new(ErrCode::VerifyFailed, "ⓜ", "가".repeat(60));
        assert_eq!(e.detail.chars().count(), 48);
        assert!(e.detail.chars().all(|c| c == '가'));
    }
}
