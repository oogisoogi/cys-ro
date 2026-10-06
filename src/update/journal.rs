//! 갱신 저널 — 상태 전이표 · write-ahead · fsync · 사본 2 · 손상 = fail-closed(설계 AUTO-UPDATE-118 §3 · §3-10 · §3-11 ·
//! 2R 신규 BLOCK 2·5 · 3R MINOR 2).
//!
//! - 자리 = `<상태 폴더>/journal.json` · `journal.prev.json` = **A/B 두 슬롯**(2판 · 1R B7). 쓸 때마다 `generation` +1 을
//!   최신본이 **아닌** 슬롯에 원자 쓰기(임시 파일 → fsync → rename → 부모 폴더 fsync) · 읽기 = 온전한 것 중 generation 최대.
//!   한 슬롯이라도 손상이면 `Degraded` — 손상본이 더 새것이었을 수 있으므로(예: S9 를 적고 교체까지 한 뒤 손상) 남은 본을
//!   실행 근거로 쓰지 않고 실물 재대조(재구성)로 간다 · 둘 다 손상 = `Corrupt`(→ 좌석을 열지 않는다 · 재구성은 U2 복구기).
//! - write-ahead: 다음 단계의 부작용 **전에** 그 단계 이름을 먼저 적는다. 상태 이름 = 「그 단계에 들어간다」.
//! - 내용마다 `crc`(본문 sha256)를 실어 디스크 손상(파싱은 되나 값이 바뀐 것)도 손상으로 읽는다.
//! - `(txn_id, epoch)` 펜싱: 다른 토큰의 전이는 거부(옛 소유자의 늦은 쓰기 차단).
//! - 종결 표지: 설계의 정식 종결 `RB_DONE`·`RB_FAILED` 에 더해 「S11 을 마침」 = `DONE`, 「S1~S8b 에서 보류로 정리」 =
//!   `DEFERRED`, 팩 단독 갱신 끝 = `PACK_DONE` 을 둔다(설계는 상태 = 「들어가는 단계」라 끝난 뒤의 이름이 따로 없다 — 복구기가
//!   「비종결」을 가르려면 필요하다).
//!
//! U1 = 모듈 + 시험(전이표·write-ahead 순서·복구 판정표). 상태기계를 실제로 모는 러너·복구기·cysd 부팅 가드는 U2.

use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

pub const JOURNAL_FILE: &str = "journal.json";
pub const JOURNAL_PREV_FILE: &str = "journal.prev.json";

/// 저널 상태(정식 이름 = 설계 표기).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum State {
    #[serde(rename = "S1_LOCKED")]
    Locked,
    #[serde(rename = "S2_FETCHED")]
    Fetched,
    #[serde(rename = "S3_QUIESCED")]
    Quiesced,
    #[serde(rename = "S4_DRAINED")]
    Drained,
    #[serde(rename = "S5_RECHECKED")]
    Rechecked,
    #[serde(rename = "S5b_BASELINED")]
    Baselined,
    #[serde(rename = "S6_CONFIRMED")]
    Confirmed,
    #[serde(rename = "S7_STOPPED")]
    Stopped,
    #[serde(rename = "S8_SNAPSHOTTED")]
    Snapshotted,
    #[serde(rename = "S8b_COMMIT_CHECK")]
    CommitCheck,
    #[serde(rename = "S9_SWAPPED")]
    Swapped,
    #[serde(rename = "S9b_PAYLOAD_OK")]
    PayloadOk,
    #[serde(rename = "S10_STARTED")]
    Started,
    #[serde(rename = "S11_COMMITTED")]
    Committed,
    #[serde(rename = "RB_PREPARED")]
    RbPrepared,
    #[serde(rename = "RB_SWAPPED")]
    RbSwapped,
    #[serde(rename = "RB_RESTORED")]
    RbRestored,
    #[serde(rename = "RB_VERIFIED")]
    RbVerified,
    #[serde(rename = "RB_DONE")]
    RbDone,
    #[serde(rename = "RB_FAILED")]
    RbFailed,
    #[serde(rename = "PACK_APPLY")]
    PackApply,
    #[serde(rename = "PACK_ROLLBACK")]
    PackRollback,
    #[serde(rename = "DONE")]
    Done,
    #[serde(rename = "DEFERRED")]
    Deferred,
    #[serde(rename = "PACK_DONE")]
    PackDone,
}

use State::*;

impl State {
    pub const ALL: [State; 25] = [
        Locked, Fetched, Quiesced, Drained, Rechecked, Baselined, Confirmed, Stopped, Snapshotted, CommitCheck, Swapped,
        PayloadOk, Started, Committed, RbPrepared, RbSwapped, RbRestored, RbVerified, RbDone, RbFailed, PackApply,
        PackRollback, Done, Deferred, PackDone,
    ];

    pub fn is_terminal(self) -> bool {
        matches!(self, Done | Deferred | RbDone | RbFailed | PackDone)
    }

    /// cysd 부팅 가드 대상(§3-11 「비종결(S7~S11·RB·PACK_APPLY·PACK_ROLLBACK)이면 좌석을 만들지 않는다」).
    pub fn blocks_daemon_boot(self) -> bool {
        matches!(
            self,
            Stopped | Snapshotted | CommitCheck | Swapped | PayloadOk | Started | Committed | RbPrepared | RbSwapped
                | RbRestored | RbVerified | PackApply | PackRollback
        )
    }

    pub fn name(self) -> String {
        serde_json::to_value(self).ok().and_then(|v| v.as_str().map(str::to_string)).unwrap_or_default()
    }
}

/// 허용 전이(같은 상태로의 재기록 = 허용 · 멱등).
pub fn can_transition(from: Option<State>, to: State) -> bool {
    let Some(from) = from else {
        return to == Locked; // 새 트랜잭션은 S1 부터
    };
    if from == to {
        return !from.is_terminal();
    }
    if from.is_terminal() {
        return to == Locked; // 끝난 저널 위에 새 트랜잭션
    }
    match (from, to) {
        // 앞으로(본체)
        (Locked, Fetched) | (Fetched, Quiesced) | (Quiesced, Drained) | (Drained, Rechecked) | (Rechecked, Baselined)
        | (Baselined, Confirmed) | (Confirmed, Stopped) | (Stopped, Snapshotted) | (Snapshotted, CommitCheck)
        | (CommitCheck, Swapped) | (Swapped, PayloadOk) | (Swapped, Started) | (PayloadOk, Started)
        | (Started, Committed) | (Committed, Done) => true,
        // 팩 단독
        (Locked, PackApply) | (PackApply, PackDone) | (PackApply, PackRollback) | (PackRollback, PackDone) => true,
        // S1~S6 실패 = 보류로 정리 · S7·S8·S8b = 옛 바이너리로 다시 띄운 뒤 보류로 정리(§3-10)
        (Locked | Fetched | Quiesced | Drained | Rechecked | Baselined | Confirmed, Deferred) => true,
        (Stopped | Snapshotted | CommitCheck, Deferred) => true,
        // S8b 어긋남 = S7 되감기(§3 S8b)
        (CommitCheck, Stopped) => true,
        // S9 이후 실패 = RB
        (Swapped | PayloadOk | Started | Committed, RbPrepared) => true,
        (RbPrepared, RbSwapped) | (RbSwapped, RbRestored) | (RbRestored, RbVerified) | (RbVerified, RbDone) => true,
        (RbPrepared | RbSwapped | RbRestored | RbVerified, RbFailed) => true,
        _ => false,
    }
}

/// 맥 교체 직후 옛 번들 기록(3R MAJOR 1).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct PrevBundle {
    pub path: String,
    pub build_id: String,
    pub file_id: String,
    pub renamed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct PrevInstaller {
    pub path: String,
    pub sha256: String,
    pub release_seq: u64,
}

/// 저널 내용(설계 §3 칸 그대로 + `crc`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Journal {
    pub txn_id: String,
    pub epoch: u64,
    /// ★1R B7: 쓸 때마다 +1(두 슬롯 중 최신 판별 · 단조).
    #[serde(default)]
    pub generation: u64,
    pub state: State,
    #[serde(default)]
    pub release_seq: u64,
    #[serde(default)]
    pub from_release_seq: u64,
    #[serde(default)]
    pub target: String,
    #[serde(default)]
    pub stage_path: String,
    #[serde(default)]
    pub stage_tree_sha256: String,
    #[serde(default)]
    pub snapshot_dir: String,
    #[serde(default)]
    pub snapshot_manifest_sha256: String,
    #[serde(default)]
    pub prev_installer: Option<PrevInstaller>,
    #[serde(default)]
    pub prev_bundle: Option<PrevBundle>,
    #[serde(default)]
    pub payload_manifest_sha256: String,
    #[serde(default)]
    pub hold_ingested_upto: u64,
    pub boot_id: u64,
    pub mono_at_write: u64,
    pub wall_at_write: i64,
    #[serde(default)]
    pub attempt: u32,
    /// 위 칸들(`crc` 제외)의 정규 직렬화 sha256.
    #[serde(default)]
    pub crc: String,
}

impl Journal {
    pub fn new(txn_id: &str, epoch: u64) -> Journal {
        let s = super::clock::now_stamp();
        Journal {
            txn_id: txn_id.to_string(),
            epoch,
            generation: 0,
            state: Locked,
            release_seq: 0,
            from_release_seq: 0,
            target: String::new(),
            stage_path: String::new(),
            stage_tree_sha256: String::new(),
            snapshot_dir: String::new(),
            snapshot_manifest_sha256: String::new(),
            prev_installer: None,
            prev_bundle: None,
            payload_manifest_sha256: String::new(),
            hold_ingested_upto: 0,
            boot_id: s.boot_id,
            mono_at_write: s.mono_ms,
            wall_at_write: s.wall,
            attempt: 0,
            crc: String::new(),
        }
    }

    fn compute_crc(&self) -> String {
        use sha2::{Digest, Sha256};
        let mut c = self.clone();
        c.crc = String::new();
        let bytes = serde_json::to_vec(&c).unwrap_or_default();
        format!("{:x}", Sha256::digest(&bytes))
    }

    fn sealed(mut self) -> Journal {
        self.crc = self.compute_crc();
        self
    }

    fn check(&self) -> bool {
        !self.crc.is_empty() && self.crc == self.compute_crc()
    }
}

/// 읽기 결과.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReadOutcome {
    /// 저널 없음(첫 갱신 전).
    Absent,
    /// 온전한 최신본(두 슬롯 중 generation 최대 · 다른 슬롯은 온전하거나 아직 없음).
    Ok(Journal),
    /// ★1R B7: 한 슬롯이 **손상**(있으나 못 읽음) — 손상본이 더 새것이었는지 알 수 없다. 남은 본은 참고값일 뿐 그대로 실행하지
    /// 않는다(복구 = 실물 재대조 · [`Recovery::Reconstruct`]) · 이 상태에서 쓰기 거부.
    Degraded(Journal, String),
    /// 둘 다 못 읽음 = 손상(fail-closed).
    Corrupt(String),
}

impl ReadOutcome {
    pub fn journal(&self) -> Option<&Journal> {
        match self {
            ReadOutcome::Ok(j) | ReadOutcome::Degraded(j, _) => Some(j),
            _ => None,
        }
    }
}

fn parse(bytes: &[u8]) -> Result<Journal, String> {
    let j: Journal = serde_json::from_slice(bytes).map_err(|e| format!("파싱: {e}"))?;
    if !j.check() {
        return Err("crc 불일치".into());
    }
    Ok(j)
}

/// 슬롯 1개: None = 파일 없음 · Some(Ok) = 온전 · Some(Err) = 손상.
fn slot(path: &Path) -> Option<Result<Journal, String>> {
    match std::fs::read(path) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => None,
        Err(e) => Some(Err(e.to_string())),
        Ok(b) => Some(parse(&b)),
    }
}

pub fn read(dir: &Path) -> ReadOutcome {
    let a = slot(&dir.join(JOURNAL_FILE));
    let b = slot(&dir.join(JOURNAL_PREV_FILE));
    match (a, b) {
        (None, None) => ReadOutcome::Absent,
        (Some(Ok(x)), Some(Ok(y))) => ReadOutcome::Ok(if x.generation >= y.generation { x } else { y }),
        // ★2R B7/H⑦: 두 슬롯은 generation 2 부터 늘 둘 다 있다(1 = 첫 쓰기만 한 슬롯). generation ≥2 인데 상대 슬롯이 **없으면**
        //   더 새 본이 지워졌을 수 있다 — 낡은 단일 슬롯을 Ok 로 믿지 않는다(재구성).
        (Some(Ok(x)), None) | (None, Some(Ok(x))) if x.generation >= 2 => {
            let g = x.generation;
            ReadOutcome::Degraded(x, format!("상대 슬롯 없음(generation {g} ≥ 2 — 더 새 본 유실 가능)"))
        }
        (Some(Ok(x)), None) | (None, Some(Ok(x))) => ReadOutcome::Ok(x),
        (Some(Ok(x)), Some(Err(e))) | (Some(Err(e)), Some(Ok(x))) => {
            if super::mutant("B7") {
                ReadOutcome::Ok(x) // 수리 전 동작(살아남은 본을 그대로 믿음)
            } else {
                ReadOutcome::Degraded(x, e)
            }
        }
        (Some(Err(e)), None) | (None, Some(Err(e))) => ReadOutcome::Corrupt(e),
        (Some(Err(e1)), Some(Err(e2))) => ReadOutcome::Corrupt(format!("journal.json: {e1} · journal.prev.json: {e2}")),
    }
}

/// 원자 쓰기 + **부모 폴더 fsync 필수**(`pack::write_atomic` 은 폴더 fsync 를 최선 노력으로만 한다 — 저널은 필수).
pub fn durable_write(path: &Path, bytes: &[u8]) -> Result<(), String> {
    crate::pack::write_atomic_mode(path, bytes, Some(0o600)).map_err(|e| format!("{}: {e}", path.display()))?;
    sync_dir(path.parent().ok_or("부모 없음")?)
}

/// 폴더 fsync — 유닉스 = 폴더 열고 `fsync` · 윈 = 폴더 핸들(`FILE_FLAG_BACKUP_SEMANTICS`)로 `FlushFileBuffers`.
pub fn sync_dir(dir: &Path) -> Result<(), String> {
    #[cfg(unix)]
    {
        std::fs::File::open(dir).and_then(|d| d.sync_all()).map_err(|e| format!("폴더 fsync {}: {e}", dir.display()))
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        const FILE_FLAG_BACKUP_SEMANTICS: u32 = 0x0200_0000;
        std::fs::OpenOptions::new()
            .write(true)
            .custom_flags(FILE_FLAG_BACKUP_SEMANTICS)
            .open(dir)
            .and_then(|d| d.sync_all())
            .map_err(|e| format!("폴더 FlushFileBuffers {}: {e}", dir.display()))
    }
}

/// 전이 오류.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AdvanceErr {
    /// 저널 손상 — 쓰지 않는다(fail-closed).
    Corrupt(String),
    /// 허용되지 않는 전이.
    Illegal { from: Option<State>, to: State },
    /// 다른 토큰(옛 소유자)의 쓰기.
    Fenced,
    Io(String),
}

/// 다음 상태로 전이(write-ahead). `update` 는 새 내용의 칸을 고친다(상태·토큰은 이 함수가 넣는다).
/// 새 트랜잭션(`to == Locked`)은 지금 저널이 없거나 종결일 때만 · 다른 전이는 같은 `(txn_id, epoch)` 일 때만.
pub fn advance(dir: &Path, txn_id: &str, epoch: u64, to: State, update: impl FnOnce(&mut Journal)) -> Result<Journal, AdvanceErr> {
    let cur = match read(dir) {
        ReadOutcome::Corrupt(e) | ReadOutcome::Degraded(_, e) => return Err(AdvanceErr::Corrupt(e)),
        ReadOutcome::Absent => None,
        ReadOutcome::Ok(j) => Some(j),
    };
    let from = cur.as_ref().map(|j| j.state);
    if !can_transition(from, to) {
        return Err(AdvanceErr::Illegal { from, to });
    }
    let mut next = match (&cur, to) {
        (Some(c), _) if !(to == Locked && c.state.is_terminal()) => {
            if c.txn_id != txn_id || c.epoch != epoch {
                return Err(AdvanceErr::Fenced);
            }
            c.clone()
        }
        _ => Journal::new(txn_id, epoch),
    };
    next.state = to;
    update(&mut next);
    next.txn_id = txn_id.to_string();
    next.epoch = epoch;
    commit_next(dir, cur.as_ref(), next)
}

/// ★2판(codex 1R C2 · 복구 토큰 세대 승계): 복구기가 새로 잡은 잠금의 `(txn_id, epoch)` 로 **비종결 저널의 토큰을 원자 교체**한다(상태·
/// 칸 그대로 · generation +1). 이 뒤 저널 전이·데몬 RPC(`update.release`)·자식 위임이 모두 같은 새 세대를 쓴다 — 옛 소유자의 늦은
/// 쓰기는 txn_id 가 달라 [`advance`] 가 거부한다(Fenced). 잠금은 호출자가 쥐었다. 종결·같은 토큰 = 무변경.
pub fn takeover(dir: &Path, txn_id: &str, epoch: u64) -> Result<Journal, AdvanceErr> {
    let cur = match read(dir) {
        ReadOutcome::Corrupt(e) | ReadOutcome::Degraded(_, e) => return Err(AdvanceErr::Corrupt(e)),
        ReadOutcome::Absent => return Err(AdvanceErr::Illegal { from: None, to: Locked }),
        ReadOutcome::Ok(j) => j,
    };
    if cur.state.is_terminal() || (cur.txn_id == txn_id && cur.epoch == epoch) {
        return Ok(cur);
    }
    let mut next = cur.clone();
    next.txn_id = txn_id.to_string();
    next.epoch = epoch;
    commit_next(dir, Some(&cur), next)
}

fn commit_next(dir: &Path, cur: Option<&Journal>, mut next: Journal) -> Result<Journal, AdvanceErr> {
    let s = super::clock::now_stamp();
    next.boot_id = s.boot_id;
    next.mono_at_write = s.mono_ms;
    next.wall_at_write = s.wall;
    next.generation = cur.map(|c| c.generation + 1).unwrap_or(1);
    let next = next.sealed();
    super::ensure_private_dir(dir).map_err(AdvanceErr::Io)?;
    // ★1R B7: 최신본 슬롯은 **절대 덮지 않는다** — 새 generation 은 다른 슬롯(더 낡은 쪽·빈 쪽)에 원자 쓰기(+ 폴더 fsync).
    //   끊기면 최신본은 그대로 남고, 새 슬롯은 옛 내용 그대로다(rename 원자).
    let target = match slot(&dir.join(JOURNAL_FILE)) {
        Some(Ok(a)) if Some(a.generation) == cur.map(|c| c.generation) => JOURNAL_PREV_FILE,
        _ => JOURNAL_FILE,
    };
    let b = serde_json::to_vec_pretty(&next).map_err(|e| AdvanceErr::Io(e.to_string()))?;
    durable_write(&dir.join(target), &b).map_err(AdvanceErr::Io)?;
    Ok(next)
}

// ── 복구 판정표(§3-11 · 순수) ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Os {
    Mac,
    Win,
}

/// 복구기가 할 일(실행은 U2).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Recovery {
    /// 저널 없음·종결 — 할 일 없음.
    Nothing,
    /// S1~S6 — 정비 모드 TTL 해제 확인 · 보류 로그 배달 · 보류로 정리.
    ReleaseAndDefer,
    /// S7·S8·S8b — 옛 바이너리로 기동(§3-10) 뒤 보류로 정리.
    StartOldBinary,
    /// 맥 S9 — 정식 자리 번들 build-info: 새 판 = S10 으로 · 옛 판 = S7 행으로.
    MacCheckCanonical,
    /// 윈 S9·S9b — stage 설치기 sha256 재대조 → S9b 전수 대조부터.
    WinRecheckPayload,
    /// S10·S11 — V1~V9 재검사(통과 = 커밋 · 실패 = RB).
    Reverify,
    /// RB_* — 그 하위 상태부터(실물 판정이라 멱등).
    ResumeRollback(State),
    /// PACK_APPLY·PACK_ROLLBACK — `pack::recover_pack_journal()` → 사용자 트리 해시 대조.
    RecoverPack,
    /// 저널 손상 — 좌석 0 · 실물 재구성(📌18).
    Reconstruct,
}

pub fn recovery_for(read: &ReadOutcome, os: Os) -> Recovery {
    let j = match read {
        ReadOutcome::Absent => return Recovery::Nothing,
        ReadOutcome::Corrupt(_) => return Recovery::Reconstruct,
        ReadOutcome::Degraded(..) if !super::mutant("B7") => return Recovery::Reconstruct,
        ReadOutcome::Ok(j) | ReadOutcome::Degraded(j, _) => j,
    };
    match j.state {
        s if s.is_terminal() => Recovery::Nothing,
        Locked | Fetched | Quiesced | Drained | Rechecked | Baselined | Confirmed => Recovery::ReleaseAndDefer,
        Stopped | Snapshotted | CommitCheck => Recovery::StartOldBinary,
        Swapped => match os {
            Os::Mac => Recovery::MacCheckCanonical,
            Os::Win => Recovery::WinRecheckPayload,
        },
        PayloadOk => Recovery::WinRecheckPayload,
        Started | Committed => Recovery::Reverify,
        s @ (RbPrepared | RbSwapped | RbRestored | RbVerified) => Recovery::ResumeRollback(s),
        PackApply | PackRollback => Recovery::RecoverPack,
        _ => Recovery::Reconstruct,
    }
}

/// ★5판(codex 4R M5): 재구성 **트리 단계 뒤 · 데몬 재기동 전** — 손상 슬롯 둘을 `journal.corrupt.<벽시계>.json`·`.prev.json` 으로 옮겨 보존(지우지 않음)하고 새 트랜잭션을
/// `Locked → Stopped(S7)` 로 적는다(비종결 = 부팅 가드 유지 · 잠금 소유자 토큰 = 이 저널 토큰이라 [`super::runner::boot_blocked`] 는 이
/// 복구기가 띄우는 데몬만 통과). 재기동이 확인된 뒤에만 호출자가 `Stopped → Deferred` 로 종결한다 · 그 사이에 죽으면 다음 복구기 =
/// S7 행(옛 바이너리 기동 뒤 보류). 이 함수 밖에서 손상 저널 위 쓰기는 여전히 거부된다([`advance`] 의 `Corrupt`).
/// `Locked → Stopped` 는 일반 전이표에 없다 — 이 함수만 쓴다(재구성 = 실물 판정이 S2~S6 을 대신한다).
pub fn write_reconstructed_pending(dir: &Path, txn_id: &str, epoch: u64) -> Result<Journal, String> {
    let wall = super::clock::now_stamp().wall;
    for (f, tag) in [(JOURNAL_FILE, "json"), (JOURNAL_PREV_FILE, "prev.json")] {
        let p = dir.join(f);
        if p.exists() {
            std::fs::rename(&p, dir.join(format!("journal.corrupt.{wall}.{tag}"))).map_err(|e| format!("{f} 보존: {e}"))?;
        }
    }
    sync_dir(dir)?;
    let cur = advance(dir, txn_id, epoch, Locked, |_| {}).map_err(|e| format!("{e:?}"))?;
    let mut next = cur.clone();
    next.state = Stopped;
    commit_next(dir, Some(&cur), next).map_err(|e| format!("{e:?}"))
}

pub fn journal_path(dir: &Path) -> PathBuf {
    dir.join(JOURNAL_FILE)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cys-u1-jr-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        d
    }
    const T: &str = "0123456789abcdef0123456789abcdef";

    #[test]
    fn state_names_are_design_spelling() {
        let names: Vec<String> = State::ALL.iter().map(|s| s.name()).collect();
        for want in ["S1_LOCKED", "S5b_BASELINED", "S8b_COMMIT_CHECK", "S9b_PAYLOAD_OK", "S11_COMMITTED", "RB_PREPARED",
            "RB_FAILED", "PACK_APPLY", "PACK_ROLLBACK"] {
            assert!(names.contains(&want.to_string()), "{want}");
        }
        assert_eq!(names.iter().collect::<std::collections::BTreeSet<_>>().len(), 25);
    }

    /// 전이표: 앞으로 가는 길 · RB 하위 상태 · 팩 · 보류 · 금지 전이.
    #[test]
    fn transition_table() {
        let mac = [Locked, Fetched, Quiesced, Drained, Rechecked, Baselined, Confirmed, Stopped, Snapshotted, CommitCheck, Swapped, Started, Committed, Done];
        let win = [Swapped, PayloadOk, Started];
        for w in mac.windows(2).chain(win.windows(2)) {
            assert!(can_transition(Some(w[0]), w[1]), "{:?}→{:?}", w[0], w[1]);
            assert!(!can_transition(Some(w[1]), w[0]) || (w[1] == Stopped && w[0] == CommitCheck), "역행 금지 {:?}→{:?}", w[1], w[0]);
        }
        assert!(can_transition(None, Locked));
        assert!(!can_transition(None, Fetched));
        assert!(!can_transition(Some(Locked), Swapped), "건너뛰기 금지");
        assert!(!can_transition(Some(Confirmed), RbPrepared), "아무것도 안 바꾼 단계는 RB 아님");
        assert!(can_transition(Some(Confirmed), Deferred));
        assert!(can_transition(Some(CommitCheck), Stopped), "S8b 어긋남 = S7 되감기");
        assert!(!can_transition(Some(Swapped), Deferred), "교체 뒤엔 보류 정리 불가 — RB 로");
        for s in [Swapped, PayloadOk, Started, Committed] {
            assert!(can_transition(Some(s), RbPrepared));
        }
        let rb = [RbPrepared, RbSwapped, RbRestored, RbVerified, RbDone];
        for w in rb.windows(2) {
            assert!(can_transition(Some(w[0]), w[1]));
        }
        assert!(!can_transition(Some(RbPrepared), RbRestored), "RB 건너뛰기 금지");
        assert!(can_transition(Some(RbSwapped), RbFailed));
        assert!(can_transition(Some(Locked), PackApply) && can_transition(Some(PackApply), PackRollback) && can_transition(Some(PackRollback), PackDone));
        for t in [Done, Deferred, RbDone, RbFailed, PackDone] {
            assert!(can_transition(Some(t), Locked), "종결 뒤 새 트랜잭션");
            assert!(!can_transition(Some(t), t), "종결 재기록 0");
            assert!(!can_transition(Some(t), Fetched));
        }
        assert!(can_transition(Some(Swapped), Swapped), "같은 상태 재기록 = 멱등");
    }

    /// A/B 슬롯 · generation 단조 · 최신본을 덮지 않음 · 펜싱.
    #[test]
    fn advance_alternates_slots_with_monotonic_generation_and_fences_old_tokens() {
        let d = tmp("adv");
        assert_eq!(read(&d), ReadOutcome::Absent);
        let j = advance(&d, T, 1, Locked, |_| {}).unwrap();
        assert_eq!((j.state, j.generation), (Locked, 1));
        assert!(!d.join(JOURNAL_PREV_FILE).exists(), "첫 기록 = 한 슬롯");
        let j2 = advance(&d, T, 1, Fetched, |j| j.release_seq = 9).unwrap();
        assert_eq!(j2.generation, 2);
        let a: Journal = serde_json::from_slice(&std::fs::read(d.join(JOURNAL_FILE)).unwrap()).unwrap();
        let b: Journal = serde_json::from_slice(&std::fs::read(d.join(JOURNAL_PREV_FILE)).unwrap()).unwrap();
        assert_eq!((a.generation, a.state, b.generation, b.state), (1, Locked, 2, Fetched), "최신본 슬롯을 덮지 않고 다른 슬롯에");
        advance(&d, T, 1, Quiesced, |_| {}).unwrap();
        let a: Journal = serde_json::from_slice(&std::fs::read(d.join(JOURNAL_FILE)).unwrap()).unwrap();
        assert_eq!((a.generation, a.state), (3, Quiesced), "다시 반대 슬롯");
        match read(&d) {
            ReadOutcome::Ok(j) => assert_eq!((j.state, j.release_seq, j.generation), (Quiesced, 9, 3)),
            o => panic!("{o:?}"),
        }
        // 옛 epoch · 다른 txn = 거부
        assert_eq!(advance(&d, T, 0, Drained, |_| {}).unwrap_err(), AdvanceErr::Fenced);
        assert_eq!(advance(&d, &"f".repeat(32), 1, Drained, |_| {}).unwrap_err(), AdvanceErr::Fenced);
        // 금지 전이
        assert!(matches!(advance(&d, T, 1, Swapped, |_| {}).unwrap_err(), AdvanceErr::Illegal { .. }));
        // 보류 정리 → 새 트랜잭션(다른 토큰 허용 · generation 은 계속 오른다)
        advance(&d, T, 1, Deferred, |_| {}).unwrap();
        let j5 = advance(&d, &"a".repeat(32), 2, Locked, |_| {}).unwrap();
        assert_eq!((j5.epoch, j5.release_seq, j5.generation), (2, 0, 5), "새 트랜잭션 = 새 내용 · generation 단조");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 손상: 둘 다 = Corrupt · 하나 = Degraded(쓰기 거부 · 복구 = 재구성) · crc 로 값 변조 감지.
    #[test]
    fn corruption_degrades_or_fails_closed() {
        let d = tmp("cor");
        advance(&d, T, 1, Locked, |_| {}).unwrap();
        advance(&d, T, 1, Fetched, |_| {}).unwrap(); // prev 슬롯 = gen2
        // 최신 슬롯 값 변조(파싱은 됨) = crc 불일치 = 손상 → Degraded
        let mut v: serde_json::Value = serde_json::from_slice(&std::fs::read(d.join(JOURNAL_PREV_FILE)).unwrap()).unwrap();
        v["release_seq"] = serde_json::json!(999);
        std::fs::write(d.join(JOURNAL_PREV_FILE), v.to_string()).unwrap();
        let r = read(&d);
        assert!(matches!(r, ReadOutcome::Degraded(_, _)), "{r:?}");
        assert_eq!(recovery_for(&r, Os::Mac), Recovery::Reconstruct);
        assert!(matches!(advance(&d, T, 1, Quiesced, |_| {}).unwrap_err(), AdvanceErr::Corrupt(_)), "Degraded 에서 쓰기 거부");
        // 둘 다 손상 = Corrupt
        std::fs::write(d.join(JOURNAL_FILE), b"garbage").unwrap();
        assert!(matches!(read(&d), ReadOutcome::Corrupt(_)));
        // 남은 하나가 손상 · 다른 하나 없음 = Corrupt
        std::fs::remove_file(d.join(JOURNAL_PREV_FILE)).unwrap();
        assert!(matches!(read(&d), ReadOutcome::Corrupt(_)));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★1R B7 뮤테이션: S9(교체)를 적은 슬롯이 손상되고 S8b 슬롯만 남아도 「옛 바이너리로 기동」을 실행하지 않는다(재구성).
    #[test]
    fn b7_post_side_effect_slot_corruption_never_runs_prev() {
        let d = tmp("b7");
        for st in [Locked, Fetched, Quiesced, Drained, Rechecked, Baselined, Confirmed, Stopped, Snapshotted, CommitCheck, Swapped] {
            advance(&d, T, 1, st, |_| {}).unwrap();
        }
        // 최신(S9 Swapped)이 든 슬롯을 찾아 손상
        let latest_slot = [JOURNAL_FILE, JOURNAL_PREV_FILE]
            .into_iter()
            .find(|f| serde_json::from_slice::<Journal>(&std::fs::read(d.join(f)).unwrap()).unwrap().state == Swapped)
            .unwrap();
        std::fs::write(d.join(latest_slot), b"{torn").unwrap();
        let r = read(&d);
        assert_eq!(r.journal().map(|j| j.state), Some(CommitCheck), "남은 본 = S8b");
        assert_eq!(recovery_for(&r, Os::Win), Recovery::Reconstruct, "S8b 를 믿고 옛 바이너리 기동 = 금지");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★2R B7/H⑦(소스 변이 patch `b7-single-slot`): 최신 슬롯이 **지워져**(손상 아님 · 부재) 낡은 단일 슬롯만 남음 = Degraded →
    /// 재구성(낡은 S8b 를 Ok 로 믿고 옛 바이너리 기동 = 금지) · 첫 쓰기(generation 1)의 단일 슬롯은 정상 Ok.
    #[test]
    fn b7_single_slot_with_missing_peer_is_degraded() {
        let d = tmp("b7s");
        advance(&d, T, 1, Locked, |_| {}).unwrap();
        assert!(matches!(read(&d), ReadOutcome::Ok(_)), "generation 1 단일 슬롯 = 정상");
        for st in [Fetched, Quiesced, Drained, Rechecked, Baselined, Confirmed, Stopped, Snapshotted, CommitCheck, Swapped] {
            advance(&d, T, 1, st, |_| {}).unwrap();
        }
        let latest_slot = [JOURNAL_FILE, JOURNAL_PREV_FILE]
            .into_iter()
            .find(|f| serde_json::from_slice::<Journal>(&std::fs::read(d.join(f)).unwrap()).unwrap().state == Swapped)
            .unwrap();
        std::fs::remove_file(d.join(latest_slot)).unwrap();
        let r = read(&d);
        assert!(matches!(r, ReadOutcome::Degraded(..)), "{r:?}");
        assert_eq!(recovery_for(&r, Os::Win), Recovery::Reconstruct);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// 복구 판정표(§3-11) 각 칸.
    #[test]
    fn recovery_table() {
        let j = |s| ReadOutcome::Ok(Journal { state: s, ..Journal::new(T, 1) });
        assert_eq!(recovery_for(&ReadOutcome::Absent, Os::Win), Recovery::Nothing);
        for s in [Locked, Fetched, Quiesced, Drained, Rechecked, Baselined, Confirmed] {
            assert_eq!(recovery_for(&j(s), Os::Mac), Recovery::ReleaseAndDefer, "{s:?}");
        }
        for s in [Stopped, Snapshotted, CommitCheck] {
            assert_eq!(recovery_for(&j(s), Os::Win), Recovery::StartOldBinary);
        }
        assert_eq!(recovery_for(&j(Swapped), Os::Mac), Recovery::MacCheckCanonical);
        assert_eq!(recovery_for(&j(Swapped), Os::Win), Recovery::WinRecheckPayload);
        assert_eq!(recovery_for(&j(PayloadOk), Os::Win), Recovery::WinRecheckPayload);
        for s in [Started, Committed] {
            assert_eq!(recovery_for(&j(s), Os::Mac), Recovery::Reverify);
        }
        for s in [RbPrepared, RbSwapped, RbRestored, RbVerified] {
            assert_eq!(recovery_for(&j(s), Os::Win), Recovery::ResumeRollback(s));
        }
        assert_eq!(recovery_for(&j(PackApply), Os::Mac), Recovery::RecoverPack);
        assert_eq!(recovery_for(&j(PackRollback), Os::Mac), Recovery::RecoverPack);
        for s in [Done, Deferred, RbDone, RbFailed, PackDone] {
            assert_eq!(recovery_for(&j(s), Os::Mac), Recovery::Nothing);
        }
        // 부팅 가드 = S7~S11·RB 진행·PACK
        let blocking: Vec<State> = State::ALL.iter().copied().filter(|s| s.blocks_daemon_boot()).collect();
        assert_eq!(blocking, vec![Stopped, Snapshotted, CommitCheck, Swapped, PayloadOk, Started, Committed, RbPrepared, RbSwapped, RbRestored, RbVerified, PackApply, PackRollback]);
    }
}
