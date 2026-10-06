//! 갱신 러너 상태기계 · 상태별 되감기 · RB 하위 상태 · 복구기(설계 AUTO-UPDATE-118 §3 그림 · §3-10 · §3-11 · §7-1 강제 종료 행렬).
//!
//! - 상태 이름은 「그 단계에 **들어간다**」(write-ahead): 부작용 전에 [`journal::advance`] 로 이름을 먼저 적는다. 그래서 어느 지점에서
//!   죽어도 복구기는 마지막 상태 + 실물(build-info·매니페스트)만 보고 앞으로 마치거나 되돌린다(시각으로 판정하지 않는다).
//! - 부작용(데몬 RPC·rotate·스냅샷·교환·설치기)은 [`Ops`] 가 한다 — 실 맥·윈 실행층과 시험용 가짜가 같은 상태기계를 탄다.
//! - 결함 주입([`Fault`] · `CYS_UPDATE_FAULT` · **디버그 빌드만**): `kill@<상태>:<before|after>` = 그 상태 전이 직전·직후에 러너가
//!   죽는다(실행 바이너리 = 즉시 `abort` · 시험 = [`Outcome::Killed`]) · `verify_v3` = 사후 검증 V3 실패 · `pause@<상태>` = 표지 파일을
//!   만들고 오래 기다린다(W4 전원 차단 창).
//! - ★폭주 방지(치명 위험 4군 ①): 앞으로 가는 교체는 트랜잭션당 1회(윈 S9b 불일치 = 같은 설치기 **1회** 재실행만) · 롤백은 실물 판정이라
//!   다시 돌려도 신판이 돌아오지 않는다 · 실패는 [`super::failures`] 분류대로 기록돼 같은 릴리스 재시도를 막거나 늦춘다.

use super::errors::ErrCode;
use super::journal::{self, Journal, Os, ReadOutcome, Recovery, State};
use std::path::{Path, PathBuf};

/// 실행층 실패.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Fail {
    pub code: ErrCode,
    pub step: String,
    pub detail: String,
}

impl Fail {
    pub fn new(code: ErrCode, step: &str, detail: impl Into<String>) -> Fail {
        Fail { code, step: step.to_string(), detail: detail.into() }
    }
}

pub type Step = Result<(), Fail>;

/// 정식 자리의 판(실물 판정 · build-info 정확 대조).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Canon {
    New,
    Old,
    /// 정식 자리에 번들·설치본이 없거나 판독 불가 — 사람 필요(`update.recover_anomaly`).
    Unknown,
}

/// 결과 종류(§3-12 알림 표 행).
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    Ok,
    Deferred,
    Rollback,
    RollbackFailed,
    PackOk,
    JournalCorrupt,
    SeatsBlocked,
}

/// 실행층. 각 함수는 **멱등**이어야 한다(복구기가 같은 상태를 다시 부른다).
pub trait Ops {
    fn os(&self) -> Os;
    /// S2 — 내려받기·검증·stage(저널 칸 `release_seq`·`target`·`stage_path`·`stage_tree_sha256` 채움).
    fn fetch(&mut self, j: &mut Journal) -> Step;
    /// S3 — 「하지 않는 조건」 재판정 통과 → 정비 모드 진입(세대 토큰).
    fn quiesce(&mut self, j: &Journal) -> Step;
    /// S4 — `drain --verify` all_saved.
    fn drain(&mut self, j: &Journal) -> Step;
    /// S5 — 토큰 이후 사람 입력·새 출력·큐·working·unknown 재검사.
    fn recheck(&mut self, j: &Journal) -> Step;
    /// S5b — 기준선 B0(`attempt.json`).
    fn baseline(&mut self, j: &Journal) -> Step;
    /// S6 — 폐기문·봉투 재읽기(같은 release_seq · halt:false · 폐기 무변화).
    fn confirm(&mut self, j: &Journal) -> Step;
    /// S7 — `rotate --stop-only --txn`.
    fn stop(&mut self, j: &Journal) -> Step;
    /// S8 — 스냅샷(저널 칸 `snapshot_dir`·`snapshot_manifest_sha256` · 윈 롤백 자산 `prev_installer`).
    fn snapshot(&mut self, j: &mut Journal) -> Step;
    /// S8b — 교체 직전 재확인(N3·N4·N5 · 세대 토큰 무변화 · stage 트리 해시).
    fn commit_check(&mut self, j: &Journal) -> Step;
    /// 정식 자리 판(맥 번들 build-info · 윈 S9b 대조 결과).
    fn canonical(&mut self, j: &Journal) -> Canon;
    /// S9 — 교환(맥 RENAME_SWAP · `prev_bundle` 기록) / 설치기 실행(윈).
    fn swap(&mut self, j: &mut Journal) -> Step;
    /// S9b — (윈) 페이로드 전수 · build-info · pack-plan 게이트. 불일치면 실행층이 같은 설치기를 **1회** 재실행 뒤 다시 대조한다.
    fn payload_ok(&mut self, j: &Journal) -> Step;
    /// S10 — 새 바이너리 `rotate --skip-drain --txn` · 정비 모드 해제.
    fn start_new(&mut self, j: &Journal) -> Step;
    /// S11 — V1~V9(`rollback` = 옛 판 기준 재검사).
    fn post_verify(&mut self, j: &Journal, rollback: bool) -> Step;
    /// S11 마무리 — 수용 기록 · 본문·설치기 보존 · 세대 정리(실패해도 교체는 이미 성공 — 기록만).
    fn commit(&mut self, j: &Journal) -> Step;
    /// S1~S6 정리 — 정비 모드 해제(보류 로그 배달) · stage 삭제(best-effort).
    fn release(&mut self, j: &Journal);
    /// S7·S8·S8b 되감기 — 옛 바이너리 `rotate --skip-drain --txn`.
    fn start_old(&mut self, j: &Journal) -> Step;
    /// RB_PREPARED — 새 데몬 drain(best-effort) · 정지 · 백업 재대조(불일치 = `RollbackBlocked`).
    fn rb_prepare(&mut self, j: &Journal) -> Step;
    /// RB_SWAPPED — 정식 자리 실물 판정 뒤 필요할 때만 되교환/옛 설치기 재실행 + 신판 전용 경로 삭제.
    fn rb_swap(&mut self, j: &Journal) -> Step;
    /// RB_RESTORED — 팩·사용자 트리·상태 폴더 파일 단위 복원.
    fn rb_restore(&mut self, j: &Journal) -> Step;
    /// PACK_APPLY·PACK_ROLLBACK 복구 — `pack::recover_pack_journal()` + 사용자 트리 해시 대조.
    fn recover_pack(&mut self, j: &Journal) -> Step;
    /// 저널 손상 — 실물 재구성(§3-11 1~3). Ok = 판 확정 · 팩·사용자 트리 대조 끝.
    fn reconstruct(&mut self) -> Step;
    /// ★3판(Fable 2R M4 · 설계 §3-8): 팩만 새 판인가 — `pack-plan` 게이트 + `pack-update --dry-run`. Ok(false) = 없음·본체 대기(binary-too-old).
    fn pack_available(&mut self) -> Result<bool, Fail>;
    /// PACK_APPLY 전: 사용자 트리 사본·해시를 저널 칸(`snapshot_dir`·`stage_tree_sha256`)에 채운다.
    fn pack_prepare(&mut self, j: &mut Journal) -> Step;
    /// 팩 적용(`pack-update --txn` 위임).
    fn pack_apply(&mut self, j: &Journal) -> Step;
    /// 결과 기록(state.json `last_result` · 실패 분류 · 상담소 신호 · `counsel/updates.jsonl`).
    fn record(&mut self, j: Option<&Journal>, kind: Kind, fail: Option<&Fail>);
}

/// 결함 주입(디버그 빌드만 — 출시 빌드에서는 [`Fault::from_env`] 가 늘 빈 값).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Fault {
    /// (상태 접두, after?)
    pub kills: Vec<(String, bool)>,
    pub verify_v3: bool,
    pub pauses: Vec<String>,
}

pub const ENV_FAULT: &str = "CYS_UPDATE_FAULT";

impl Fault {
    pub fn parse(s: &str) -> Fault {
        let mut f = Fault::default();
        for t in s.split(',').map(str::trim).filter(|t| !t.is_empty()) {
            if t == "verify_v3" {
                f.verify_v3 = true;
            } else if let Some(r) = t.strip_prefix("kill@") {
                let (st, ph) = r.split_once(':').unwrap_or((r, "before"));
                f.kills.push((st.to_string(), ph == "after"));
            } else if let Some(r) = t.strip_prefix("pause@") {
                f.pauses.push(r.to_string());
            }
        }
        f
    }

    pub fn from_env() -> Fault {
        if !cfg!(debug_assertions) {
            return Fault::default();
        }
        std::env::var(ENV_FAULT).map(|v| Fault::parse(&v)).unwrap_or_default()
    }

    fn matches(spec: &str, st: State) -> bool {
        let n = st.name();
        n == spec || n.starts_with(&format!("{spec}_"))
    }

    pub fn kill(&self, st: State, after: bool) -> bool {
        self.kills.iter().any(|(s, a)| *a == after && Fault::matches(s, st))
    }

    pub fn pause(&self, st: State) -> bool {
        self.pauses.iter().any(|s| Fault::matches(s, st))
    }
}

/// 러너 결과.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Outcome {
    Done,
    Deferred(Fail),
    RolledBack(Fail),
    RollbackFailed(Fail),
    PackDone,
    /// 결함 주입으로 죽음(시험) — 실행 바이너리는 여기 오지 않고 abort.
    Killed(State, bool),
    /// 저널 쓰기 거부(손상·다른 소유자) — 아무것도 하지 않고 끝.
    JournalRefused(String),
    /// 손상 저널 재구성 실패 — 좌석 0 유지(📌18).
    SeatsBlocked(Fail),
    Nothing,
}

pub struct Runner<'a, O: Ops> {
    pub dir: PathBuf,
    pub txn_id: String,
    pub epoch: u64,
    pub ops: &'a mut O,
    pub fault: Fault,
    /// `pause@` 표지 폴더(없으면 상태 폴더).
    pub pause_marker_dir: Option<PathBuf>,
    /// 시험 = true 면 kill 이 abort 대신 [`Outcome::Killed`].
    pub soft_kill: bool,
}

enum Stop {
    Killed(State, bool),
    Journal(String),
}

impl<'a, O: Ops> Runner<'a, O> {
    pub fn new(dir: &Path, txn_id: &str, epoch: u64, ops: &'a mut O) -> Runner<'a, O> {
        Runner { dir: dir.to_path_buf(), txn_id: txn_id.into(), epoch, ops, fault: Fault::from_env(), pause_marker_dir: None, soft_kill: cfg!(test) }
    }

    fn hit(&self, st: State, after: bool) -> Result<(), Stop> {
        if self.fault.kill(st, after) {
            if !self.soft_kill {
                eprintln!("CYS_UPDATE_FAULT kill@{}:{}", st.name(), if after { "after" } else { "before" });
                std::process::abort();
            }
            return Err(Stop::Killed(st, after));
        }
        if !after && self.fault.pause(st) {
            let d = self.pause_marker_dir.clone().unwrap_or_else(|| self.dir.clone());
            let _ = std::fs::write(d.join(format!("fault-pause-{}.marker", st.name())), b"pause");
            if !self.soft_kill {
                std::thread::sleep(std::time::Duration::from_secs(600));
            }
        }
        Ok(())
    }

    /// write-ahead 전이 + 결함 주입 앞뒤.
    fn enter(&mut self, to: State, f: impl FnOnce(&mut Journal)) -> Result<Journal, Stop> {
        self.hit(to, false)?;
        let j = journal::advance(&self.dir, &self.txn_id, self.epoch, to, f).map_err(|e| Stop::Journal(format!("{e:?}")))?;
        self.hit(to, true)?;
        Ok(j)
    }

    fn stop_to_outcome(s: Stop) -> Outcome {
        match s {
            Stop::Killed(st, a) => Outcome::Killed(st, a),
            Stop::Journal(e) => Outcome::JournalRefused(e),
        }
    }

    /// 본체 교체 1회(S1 → S11/DONE · 실패 = §3-10 상태별 되감기). 잠금은 호출자가 이미 쥐었다(`txn_id`·`epoch` = 그 토큰).
    pub fn run(&mut self) -> Outcome {
        match self.run_inner() {
            Ok(o) => o,
            Err(s) => Self::stop_to_outcome(s),
        }
    }

    fn run_inner(&mut self) -> Result<Outcome, Stop> {
        let mut j: Journal;
        self.enter(State::Locked, |_| {})?;
        // S1~S6: 아직 아무것도 안 바꿈 — 실패 = 보류(정비 모드 해제 · stage 삭제)
        type Phase<O> = fn(&mut O, &mut Journal) -> Step;
        let early: [(State, Phase<O>); 6] = [
            (State::Fetched, |o, j| o.fetch(j)),
            (State::Quiesced, |o, j| o.quiesce(j)),
            (State::Drained, |o, j| o.drain(j)),
            (State::Rechecked, |o, j| o.recheck(j)),
            (State::Baselined, |o, j| o.baseline(j)),
            (State::Confirmed, |o, j| o.confirm(j)),
        ];
        for (st, phase) in early {
            j = self.enter(st, |_| {})?;
            let mut work = j.clone();
            if let Err(f) = phase(self.ops, &mut work) {
                return self.defer(&j, f);
            }
            if work != j {
                self.enter(st, |n| copy_fields(n, &work))?;
            }
        }
        // S7·S8·S8b: 데몬만 섬 — 실패 = 옛 바이너리로 다시 띄운 뒤 보류
        j = self.enter(State::Stopped, |_| {})?;
        if let Err(f) = self.ops.stop(&j) {
            return self.restart_old_and_defer(&j, f);
        }
        j = self.enter(State::Snapshotted, |_| {})?;
        let mut work = j.clone();
        if let Err(f) = self.ops.snapshot(&mut work) {
            return self.restart_old_and_defer(&j, f);
        }
        self.enter(State::Snapshotted, |n| copy_fields(n, &work))?;
        j = self.enter(State::CommitCheck, |_| {})?;
        if let Err(f) = self.ops.commit_check(&j) {
            // S8b 어긋남 = S7 되감기(저널을 S7 로 돌려 적고 옛 데몬)
            let j = self.enter(State::Stopped, |_| {})?;
            return self.restart_old_and_defer(&j, f);
        }
        // S9 이후 = 교체됨 → 실패는 RB
        j = self.enter(State::Swapped, |_| {})?;
        self.forward_from_swapped(j)
    }

    /// S9(기록됨)부터 앞으로. 복구기도 이 길을 탄다(멱등 — 교환은 실물 판정 뒤에만).
    fn forward_from_swapped(&mut self, mut j: Journal) -> Result<Outcome, Stop> {
        if self.ops.canonical(&j) != Canon::New {
            let mut work = j.clone();
            if let Err(f) = self.ops.swap(&mut work) {
                return self.rollback(&j, f);
            }
            self.enter(State::Swapped, |n| copy_fields(n, &work))?;
        }
        if self.ops.os() == Os::Win {
            j = self.enter(State::PayloadOk, |_| {})?;
            if let Err(f) = self.ops.payload_ok(&j) {
                return self.rollback(&j, f);
            }
        }
        j = self.enter(State::Started, |_| {})?;
        self.forward_from_started(j)
    }

    fn forward_from_started(&mut self, j: Journal) -> Result<Outcome, Stop> {
        if let Err(f) = self.ops.start_new(&j) {
            return self.rollback(&j, f);
        }
        let j = self.enter(State::Committed, |_| {})?;
        let v = if self.fault.verify_v3 { Err(Fail::new(ErrCode::VerifyFailed, "V3", "결함 주입 verify_v3")) } else { self.ops.post_verify(&j, false) };
        if let Err(f) = v {
            return self.rollback(&j, f);
        }
        // ★2판(codex 1R C11): 수용 기록·롤백 자산 durable commit 성공 = DONE 의 필수 선행(실패 = 롤백 · 조용한 ok 0).
        if let Err(f) = self.ops.commit(&j) {
            return self.rollback(&j, f);
        }
        let j = self.enter(State::Done, |_| {})?;
        self.ops.record(Some(&j), Kind::Ok, None);
        Ok(Outcome::Done)
    }

    fn defer(&mut self, j: &Journal, f: Fail) -> Result<Outcome, Stop> {
        self.ops.release(j);
        let j = self.enter(State::Deferred, |_| {})?;
        self.ops.record(Some(&j), Kind::Deferred, Some(&f));
        Ok(Outcome::Deferred(f))
    }

    fn restart_old_and_defer(&mut self, j: &Journal, f: Fail) -> Result<Outcome, Stop> {
        if let Err(f2) = self.ops.start_old(j) {
            // 옛 데몬도 못 띄움 — 저널은 S7 행에 남긴다(부팅 가드 유지 · 복구기가 다시 시도) · 결과는 사람 필요 쪽으로 기록
            self.ops.record(Some(j), Kind::RollbackFailed, Some(&f2));
            return Ok(Outcome::RollbackFailed(f2));
        }
        self.ops.release(j);
        let j = self.enter(State::Deferred, |_| {})?;
        self.ops.record(Some(&j), Kind::Deferred, Some(&f));
        Ok(Outcome::Deferred(f))
    }

    /// §3-10 RB 하위 상태(들어가기 전에 적고 · 각 단계 멱등).
    fn rollback(&mut self, _j: &Journal, f: Fail) -> Result<Outcome, Stop> {
        // ★3판(Fable 2R m3): 원인이 「되감기 금지」(윈 설치기 종료 확인 불가 = 옛 설치기를 띄우면 동시 쓰기)면 RB 단계를 밟지 않고
        //   RB_FAILED(사람 필요 · 부팅 가드 유지)로 바로 간다.
        if f.code == ErrCode::RollbackBlocked {
            let j = self.enter(State::RbPrepared, |_| {})?;
            let j = self.enter(State::RbFailed, |_| {})?;
            self.ops.record(Some(&j), Kind::RollbackFailed, Some(&f));
            return Ok(Outcome::RollbackFailed(f));
        }
        let j = self.enter(State::RbPrepared, |_| {})?;
        self.rollback_from(j, f)
    }

    fn rollback_from(&mut self, mut j: Journal, cause: Fail) -> Result<Outcome, Stop> {
        let seq = [State::RbPrepared, State::RbSwapped, State::RbRestored, State::RbVerified];
        let start = seq.iter().position(|s| *s == j.state).unwrap_or(0);
        for (i, st) in seq.iter().enumerate().skip(start) {
            if i > start {
                j = self.enter(*st, |_| {})?;
            }
            let r = match st {
                State::RbPrepared => self.ops.rb_prepare(&j),
                State::RbSwapped => self.ops.rb_swap(&j),
                State::RbRestored => self.ops.rb_restore(&j),
                _ => self.ops.start_old(&j).and_then(|_| self.ops.post_verify(&j, true)),
            };
            if let Err(f2) = r {
                let j = self.enter(State::RbFailed, |_| {})?;
                self.ops.record(Some(&j), Kind::RollbackFailed, Some(&f2));
                return Ok(Outcome::RollbackFailed(f2));
            }
        }
        let j = self.enter(State::RbDone, |_| {})?;
        self.ops.record(Some(&j), Kind::Rollback, Some(&cause));
        Ok(Outcome::RolledBack(cause))
    }

    /// ★3판(Fable 2R M4 · 설계 §3-8): 팩 단독 갱신 1회(본체 같음) — 새 팩 없음 = 저널 0 · 있으면 S1 → PACK_APPLY(사용자 트리 사본·해시 고정)
    /// → 적용 → PACK_DONE · 적용 실패 = PACK_ROLLBACK → `recover_pack`(팩 저널 복구 + 사용자 트리 대조·복원) → PACK_DONE. 잠금은 호출자가 쥐었다.
    pub fn run_pack(&mut self) -> Outcome {
        match self.run_pack_inner() {
            Ok(o) => o,
            Err(s) => Self::stop_to_outcome(s),
        }
    }

    fn run_pack_inner(&mut self) -> Result<Outcome, Stop> {
        match self.ops.pack_available() {
            Ok(false) => return Ok(Outcome::Nothing),
            Err(f) => {
                self.ops.record(None, Kind::Deferred, Some(&f));
                return Ok(Outcome::Deferred(f));
            }
            Ok(true) => {}
        }
        let j = self.enter(State::Locked, |_| {})?;
        let mut work = j.clone();
        if let Err(f) = self.ops.pack_prepare(&mut work) {
            let j = self.enter(State::Deferred, |_| {})?;
            self.ops.record(Some(&j), Kind::Deferred, Some(&f));
            return Ok(Outcome::Deferred(f));
        }
        let j = self.enter(State::PackApply, |n| copy_fields(n, &work))?;
        match self.ops.pack_apply(&j) {
            Ok(()) => {
                let j = self.enter(State::PackDone, |_| {})?;
                self.ops.record(Some(&j), Kind::PackOk, None);
                Ok(Outcome::PackDone)
            }
            Err(f) => {
                let j = self.enter(State::PackRollback, |_| {})?;
                if let Err(f2) = self.ops.recover_pack(&j) {
                    // PACK_ROLLBACK 에 남긴다 — 부팅 가드 유지 · 복구기가 다시 시도
                    self.ops.record(Some(&j), Kind::RollbackFailed, Some(&f2));
                    return Ok(Outcome::RollbackFailed(f2));
                }
                let j = self.enter(State::PackDone, |_| {})?;
                self.ops.record(Some(&j), Kind::Deferred, Some(&f));
                Ok(Outcome::Deferred(f))
            }
        }
    }

    /// 복구기(§3-11) — 저널 마지막 상태 + 실물로 앞으로 마치거나 되돌린다. 저널이 없거나 종결이면 [`Outcome::Nothing`].
    /// 잠금은 호출자가 쥐었다. ★2판(codex 1R C2): 인수 규칙 하나 = **새 잠금 세대**. 비종결 저널의 토큰을 호출자 토큰으로
    /// [`journal::takeover`] 한 뒤 진행한다 — 잠금 소유자·저널·데몬 RPC·자식 토큰이 같은 `(txn_id, epoch)` 가 된다(옛 소유자 = Fenced).
    pub fn recover(&mut self) -> Outcome {
        let mut read = journal::read(&self.dir);
        let rec = journal::recovery_for(&read, self.ops.os());
        if matches!(&read, ReadOutcome::Ok(j) if !j.state.is_terminal()) && !super::mutant("U2-TAKEOVER") {
            match journal::takeover(&self.dir, &self.txn_id, self.epoch) {
                Ok(j) => read = ReadOutcome::Ok(j),
                Err(e) => return Outcome::JournalRefused(format!("takeover: {e:?}")),
            }
        } else if let Some(j) = read.journal() {
            self.txn_id = j.txn_id.clone();
            self.epoch = j.epoch;
        }
        let r = match (rec, read) {
            (Recovery::Nothing, _) => return Outcome::Nothing,
            (Recovery::Reconstruct, _) => return self.reconstruct(),
            (rec, ReadOutcome::Ok(j)) => self.recover_from(rec, j),
            (_, other) => return Outcome::JournalRefused(format!("{other:?}")),
        };
        match r {
            Ok(o) => o,
            Err(s) => Self::stop_to_outcome(s),
        }
    }

    fn recover_from(&mut self, rec: Recovery, j: Journal) -> Result<Outcome, Stop> {
        let anomaly = |d: &str| Fail::new(ErrCode::RecoverAnomaly, "recover", d);
        match rec {
            Recovery::ReleaseAndDefer => self.defer(&j, Fail::new(ErrCode::RotateFailed, "recover", "S1~S6 중단 — 보류로 정리")),
            Recovery::StartOldBinary => {
                if j.state == State::CommitCheck {
                    let j = self.enter(State::Stopped, |_| {})?;
                    return self.restart_old_and_defer(&j, Fail::new(ErrCode::RotateFailed, "recover", "S8b 중단"));
                }
                self.restart_old_and_defer(&j, Fail::new(ErrCode::RotateFailed, "recover", "S7·S8 중단"))
            }
            Recovery::MacCheckCanonical => match if super::mutant("U2-CANON") { Canon::New } else { self.ops.canonical(&j) } {
                Canon::New => {
                    let j = self.enter(State::Started, |_| {})?;
                    self.forward_from_started(j)
                }
                // 교환 전에 끊김 — 아무것도 안 바뀌었지만 S9 는 RB 로만 나간다(실물 판정이라 RB_SWAPPED = 무동작 · 복원 = 전부 Keep)
                Canon::Old => self.rollback(&j, Fail::new(ErrCode::RotateFailed, "recover", "S9 교환 전 중단")),
                Canon::Unknown => self.rollback(&j, anomaly("정식 자리 판독 불가")),
            },
            Recovery::WinRecheckPayload => {
                let j = if j.state == State::Swapped { self.enter(State::PayloadOk, |_| {})? } else { j };
                if let Err(f) = self.ops.payload_ok(&j) {
                    return self.rollback(&j, f);
                }
                let j = self.enter(State::Started, |_| {})?;
                self.forward_from_started(j)
            }
            Recovery::Reverify => {
                let j = if j.state == State::Started { self.enter(State::Committed, |_| {})? } else { j };
                // 새 데몬이 떠 있는지 모른다 — start_new 는 멱등(rotate --skip-drain)이라 먼저 한 번
                if let Err(f) = self.ops.start_new(&j).and_then(|_| self.ops.post_verify(&j, false)) {
                    return self.rollback(&j, f);
                }
                if let Err(f) = self.ops.commit(&j) {
                    return self.rollback(&j, f);
                }
                let j = self.enter(State::Done, |_| {})?;
                self.ops.record(Some(&j), Kind::Ok, None);
                Ok(Outcome::Done)
            }
            Recovery::ResumeRollback(_) => self.rollback_from(j, Fail::new(ErrCode::RotateFailed, "recover", "롤백 이어하기")),
            Recovery::RecoverPack => {
                if let Err(f) = self.ops.recover_pack(&j) {
                    return Ok(Outcome::RollbackFailed(f));
                }
                let j = if j.state == State::PackApply { self.enter(State::PackRollback, |_| {})? } else { j };
                let _ = j;
                self.enter(State::PackDone, |_| {})?;
                Ok(Outcome::PackDone)
            }
            Recovery::Nothing | Recovery::Reconstruct => Ok(Outcome::Nothing),
        }
    }

    fn reconstruct(&mut self) -> Outcome {
        let r = if super::mutant("U2-RECON") { Ok(()) } else { self.ops.reconstruct() };
        match r {
            Ok(()) => match journal::write_reconstructed(&self.dir, &self.txn_id_or_new(), self.epoch) {
                Ok(j) => {
                    self.ops.record(Some(&j), Kind::JournalCorrupt, Some(&Fail::new(ErrCode::JournalCorrupt, "reconstruct", "재구성 성공")));
                    Outcome::Nothing
                }
                Err(e) => {
                    let f = Fail::new(ErrCode::JournalCorrupt, "reconstruct", e);
                    self.ops.record(None, Kind::SeatsBlocked, Some(&f));
                    Outcome::SeatsBlocked(f)
                }
            },
            Err(f) => {
                self.ops.record(None, Kind::SeatsBlocked, Some(&f));
                Outcome::SeatsBlocked(f)
            }
        }
    }

    fn txn_id_or_new(&self) -> String {
        if self.txn_id.len() == 32 {
            self.txn_id.clone()
        } else {
            super::buildinfo::random_hex128().unwrap_or_else(|_| "0".repeat(32))
        }
    }
}

/// 실행층이 채운 칸을 저널에 옮긴다(상태·토큰·세대·시각·crc 는 [`journal::advance`] 가 넣는다).
fn copy_fields(n: &mut Journal, w: &Journal) {
    n.release_seq = w.release_seq;
    n.from_release_seq = w.from_release_seq;
    n.target = w.target.clone();
    n.stage_path = w.stage_path.clone();
    n.stage_tree_sha256 = w.stage_tree_sha256.clone();
    n.snapshot_dir = w.snapshot_dir.clone();
    n.snapshot_manifest_sha256 = w.snapshot_manifest_sha256.clone();
    n.prev_installer = w.prev_installer.clone();
    n.prev_bundle = w.prev_bundle.clone();
    n.payload_manifest_sha256 = w.payload_manifest_sha256.clone();
    n.hold_ingested_upto = w.hold_ingested_upto;
    n.attempt = w.attempt;
}

/// cysd 부팅 가드(§3-11) — 비종결(S7~S11·RB·PACK_*)이거나 저널 손상(`Corrupt`·`Degraded`)이면 Some(사유) = 좌석·세션을 만들지 않고
/// 「복구 대기」 rc 로 끝. 저널 없음·종결·S1~S6 = None(정비 모드 TTL 이 지키는 구간).
pub fn boot_guard(dir: &Path) -> Option<String> {
    match journal::read(dir) {
        ReadOutcome::Absent => None,
        ReadOutcome::Corrupt(e) => Some(format!("journal_corrupt: {e}")),
        ReadOutcome::Degraded(_, e) => Some(format!("journal_degraded: {e}")),
        ReadOutcome::Ok(j) if j.state.blocks_daemon_boot() && !super::mutant("U2-BOOT") => Some(format!("recover_pending: {}", j.state.name())),
        ReadOutcome::Ok(_) => None,
    }
}

/// cysd 가 실제로 쓰는 판정: [`boot_guard`] 가 「복구 대기」여도 **트랜잭션 잠금이 지금 잡혀 있으면**(살아 있는 러너·복구기가 이끄는 중 —
/// S10 의 `rotate --skip-drain` 이 바로 그 데몬을 띄운다) 허용한다. 잠금이 풀린 비종결 저널(죽은 러너) = 막는다(복구기가 먼저).
/// 저널 손상은 잠금과 무관하게 막는다(재구성 뒤 [`journal::write_reconstructed`] 가 종결 저널을 쓴 다음에만 열린다).
/// ★2판(codex 1R C3): 「누군가 잠금을 쥠」 만으론 열지 않는다 — 지금 소유자 기록의 `(txn_id, epoch)` = 저널 토큰 · 묘비 아님 · 소유자 =
/// 러너/복구기 계보(`runner`·`recover`) · 그 pid 의 시작 시각 = 기록값(재사용·사망 아님)일 때만. 토큰 없는 수동 rotate 가 S9 뒤 새 잠금을
/// 잡고 cysd 를 띄워도 저널 소유자가 아니라 막힌다.
pub fn boot_blocked(dir: &Path) -> Option<String> {
    let g = boot_guard(dir)?;
    if g.starts_with("recover_pending") && super::lock::is_held(dir) == Some(true) {
        let j = journal::read(dir);
        let o = super::lock::read_owner(dir);
        if let (Some(j), Some(o)) = (j.journal(), o) {
            let lineage = matches!(o.owner.as_str(), "runner" | "recover");
            if !o.released
                && lineage
                && o.txn_id == j.txn_id
                && o.epoch == j.epoch
                && super::lock::pid_start_time(o.pid) == Some(o.start_time)
            {
                return None;
            }
        }
    }
    Some(g)
}

/// ★2판 C12: 설치판 stop_seats 폐기 표지(`seats-stop.json {release_seq, at}`).
pub const SEATS_STOP_FILE: &str = "seats-stop.json";

/// ★3판(Fable 2R M3 · 설계 §3-10 ③): 이 판(같은 release_seq)이 stop_seats 폐기면 Some(seq) — 데몬은 **새 좌석 생성만** 거부한다
/// (부팅·기존 좌석은 막지 않는다 · 새 판으로 바뀌면 자동 해제).
pub fn seats_stopped(dir: &Path) -> Option<u64> {
    seats_stop_seq(dir).filter(|s| *s == super::buildinfo::release_seq())
}

pub fn seats_stop_seq(dir: &Path) -> Option<u64> {
    super::quiesce::read_json::<serde_json::Value>(dir, SEATS_STOP_FILE).and_then(|v| v.get("release_seq").and_then(|x| x.as_u64()))
}

/// 부팅 가드 rc(「복구 대기」) — cysd 가 이 값으로 끝나면 launchd·작업 스케줄러가 다시 띄워도 같은 판정이 반복된다.
pub const RC_RECOVER_PENDING: i32 = 75;

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use std::collections::BTreeMap;

    /// 실물을 흉내 내는 가짜 실행층 — 「정식 자리 판」·「옛 데몬 기동 여부」 같은 실물 상태를 들고 있고, 교환·복원은 실물 판정으로 멱등.
    #[derive(Debug, Clone)]
    pub struct Sim {
        pub os: Os,
        pub canonical_new: bool,
        pub daemon: Option<&'static str>,
        pub quiesced: bool,
        pub stage: bool,
        pub restored: u32,
        pub swaps: u32,
        pub installer_runs: u32,
        pub fail_at: BTreeMap<&'static str, ErrCode>,
        pub pack_new: bool,
        pub pack_applied: u32,
        pub payload_bad_runs: u32,
        pub records: Vec<Kind>,
        pub reconstruct_ok: bool,
    }

    impl Sim {
        pub fn new(os: Os) -> Sim {
            Sim {
                os,
                canonical_new: false,
                daemon: Some("old"),
                quiesced: false,
                stage: false,
                restored: 0,
                swaps: 0,
                installer_runs: 0,
                pack_new: false,
                pack_applied: 0,
                fail_at: BTreeMap::new(),
                payload_bad_runs: 0,
                records: vec![],
                reconstruct_ok: true,
            }
        }
        fn f(&self, k: &'static str) -> Step {
            match self.fail_at.get(k) {
                Some(c) => Err(Fail::new(*c, k, "주입")),
                None => Ok(()),
            }
        }
    }

    impl Ops for Sim {
        fn os(&self) -> Os {
            self.os
        }
        fn fetch(&mut self, j: &mut Journal) -> Step {
            self.f("fetch")?;
            self.stage = true;
            j.release_seq = 9;
            j.from_release_seq = 8;
            j.stage_tree_sha256 = "s".repeat(64);
            Ok(())
        }
        fn quiesce(&mut self, _: &Journal) -> Step {
            self.f("quiesce")?;
            self.quiesced = true;
            Ok(())
        }
        fn drain(&mut self, _: &Journal) -> Step {
            self.f("drain")
        }
        fn recheck(&mut self, _: &Journal) -> Step {
            self.f("recheck")
        }
        fn baseline(&mut self, _: &Journal) -> Step {
            self.f("baseline")
        }
        fn confirm(&mut self, _: &Journal) -> Step {
            self.f("confirm")
        }
        fn stop(&mut self, _: &Journal) -> Step {
            self.f("stop")?;
            self.daemon = None;
            Ok(())
        }
        fn snapshot(&mut self, j: &mut Journal) -> Step {
            self.f("snapshot")?;
            j.snapshot_dir = "/snap".into();
            j.snapshot_manifest_sha256 = "m".repeat(64);
            Ok(())
        }
        fn commit_check(&mut self, _: &Journal) -> Step {
            self.f("commit_check")
        }
        fn canonical(&mut self, _: &Journal) -> Canon {
            if self.canonical_new {
                Canon::New
            } else {
                Canon::Old
            }
        }
        fn swap(&mut self, _: &mut Journal) -> Step {
            self.f("swap")?;
            if self.os == Os::Win {
                self.installer_runs += 1;
            }
            self.swaps += 1;
            self.canonical_new = true;
            Ok(())
        }
        fn payload_ok(&mut self, _: &Journal) -> Step {
            if !self.canonical_new {
                // 설치기가 안 돌았거나 덜 깐 상태 = 대조 불일치 → 같은 설치기 1회 재실행
                self.installer_runs += 1;
                self.canonical_new = true;
            }
            if self.payload_bad_runs > 0 {
                self.payload_bad_runs -= 1;
                self.installer_runs += 1; // 같은 설치기 1회 재실행
                if self.payload_bad_runs > 0 {
                    return Err(Fail::new(ErrCode::WinPayloadMismatch, "S9b", "재실행 뒤에도 불일치"));
                }
            }
            self.f("payload")
        }
        fn start_new(&mut self, _: &Journal) -> Step {
            self.f("start_new")?;
            self.daemon = Some("new");
            self.quiesced = false;
            Ok(())
        }
        fn post_verify(&mut self, _: &Journal, rollback: bool) -> Step {
            if rollback {
                return if self.canonical_new || self.daemon != Some("old") { Err(Fail::new(ErrCode::VerifyFailed, "V1", "옛 판 아님")) } else { self.f("rb_verify") };
            }
            self.f("verify")
        }
        fn commit(&mut self, _: &Journal) -> Step {
            if let Some(c) = self.fail_at.get("commit") {
                return Err(Fail::new(*c, "S11", "결함 주입 commit"));
            }
            self.stage = false;
            Ok(())
        }
        fn release(&mut self, _: &Journal) {
            self.quiesced = false;
            self.stage = false;
        }
        fn start_old(&mut self, _: &Journal) -> Step {
            self.f("start_old")?;
            self.daemon = if self.canonical_new { Some("new") } else { Some("old") };
            self.quiesced = false;
            Ok(())
        }
        fn rb_prepare(&mut self, _: &Journal) -> Step {
            self.f("rb_prepare")?;
            self.daemon = None;
            Ok(())
        }
        fn rb_swap(&mut self, _: &Journal) -> Step {
            self.f("rb_swap")?;
            if self.canonical_new {
                self.canonical_new = false; // 실물 판정 뒤에만 되교환
                self.swaps += 1;
            }
            Ok(())
        }
        fn rb_restore(&mut self, _: &Journal) -> Step {
            self.f("rb_restore")?;
            self.restored += 1;
            Ok(())
        }
        fn pack_available(&mut self) -> Result<bool, Fail> {
            self.f("pack_available")?;
            Ok(self.pack_new)
        }
        fn pack_prepare(&mut self, j: &mut Journal) -> Step {
            self.f("pack_prepare")?;
            j.stage_tree_sha256 = "user-digest".into();
            Ok(())
        }
        fn pack_apply(&mut self, _: &Journal) -> Step {
            self.f("pack_apply")?;
            self.pack_applied += 1;
            Ok(())
        }
        fn recover_pack(&mut self, _: &Journal) -> Step {
            self.f("recover_pack")
        }
        fn reconstruct(&mut self) -> Step {
            if self.reconstruct_ok {
                Ok(())
            } else {
                Err(Fail::new(ErrCode::JournalCorrupt, "reconstruct", "후보 0"))
            }
        }
        fn record(&mut self, _: Option<&Journal>, kind: Kind, _: Option<&Fail>) {
            self.records.push(kind);
        }
    }

    pub fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cys-u2-run-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }
    const T: &str = "0123456789abcdef0123456789abcdef";

    fn run(d: &Path, sim: &mut Sim, fault: Fault) -> Outcome {
        let mut r = Runner::new(d, T, 1, sim);
        r.fault = fault;
        r.soft_kill = true;
        r.run()
    }
    /// 복구기 = 새 잠금 세대(★2판 C2 — 실제 `recover_if_needed` 처럼 죽은 러너와 다른 토큰).
    const T2: &str = "fedcba9876543210fedcba9876543210";
    fn recover(d: &Path, sim: &mut Sim) -> Outcome {
        let mut r = Runner::new(d, T2, 2, sim);
        r.fault = Fault::default();
        r.soft_kill = true;
        r.recover()
    }
    fn state(d: &Path) -> State {
        journal::read(d).journal().unwrap().state
    }

    #[test]
    fn happy_path_mac_and_win_reach_done() {
        for os in [Os::Mac, Os::Win] {
            let d = tmp(&format!("happy-{os:?}"));
            let mut s = Sim::new(os);
            assert_eq!(run(&d, &mut s, Fault::default()), Outcome::Done);
            assert_eq!(state(&d), State::Done);
            assert!(s.canonical_new && s.daemon == Some("new") && !s.quiesced);
            assert_eq!(s.swaps, 1);
            assert_eq!(s.records, vec![Kind::Ok]);
            assert!(boot_guard(&d).is_none());
        }
    }

    #[test]
    fn early_failure_defers_and_s7_failure_restarts_old_daemon() {
        let d = tmp("early");
        let mut s = Sim::new(Os::Mac);
        s.fail_at.insert("recheck", ErrCode::RotateFailed);
        assert!(matches!(run(&d, &mut s, Fault::default()), Outcome::Deferred(_)));
        assert_eq!(state(&d), State::Deferred);
        assert!(!s.quiesced && !s.stage && s.daemon == Some("old"));
        let d = tmp("s8");
        let mut s = Sim::new(Os::Mac);
        s.fail_at.insert("snapshot", ErrCode::DiskLow);
        assert!(matches!(run(&d, &mut s, Fault::default()), Outcome::Deferred(_)));
        assert_eq!(s.daemon, Some("old"), "S8 실패 = 옛 바이너리로 다시 기동");
        let d = tmp("s8b");
        let mut s = Sim::new(Os::Mac);
        s.fail_at.insert("commit_check", ErrCode::Revoked);
        assert!(matches!(run(&d, &mut s, Fault::default()), Outcome::Deferred(_)));
        assert_eq!((s.swaps, s.daemon), (0, Some("old")), "S8b 어긋남 = 교체 0");
    }

    #[test]
    fn verify_failure_rolls_back_and_rb_is_idempotent() {
        let d = tmp("rb");
        let mut s = Sim::new(Os::Mac);
        let o = run(&d, &mut s, Fault::parse("verify_v3"));
        assert!(matches!(o, Outcome::RolledBack(ref f) if f.step == "V3"), "{o:?}");
        assert_eq!(state(&d), State::RbDone);
        assert!(!s.canonical_new && s.daemon == Some("old"));
        assert_eq!(s.records, vec![Kind::Rollback]);
        // RB_SWAPPED 를 두 번 돌려도 옛 판 그대로(§7-1 3판 추가)
        let mut j = journal::read(&d).journal().unwrap().clone();
        j.state = State::RbSwapped;
        s.rb_swap(&j).unwrap();
        s.rb_swap(&j).unwrap();
        assert!(!s.canonical_new);
    }

    #[test]
    fn win_payload_mismatch_reruns_installer_once_then_rolls_back() {
        let d = tmp("s9b-once");
        let mut s = Sim::new(Os::Win);
        s.payload_bad_runs = 1; // 첫 대조 불일치 → 1회 재실행 → 일치
        assert_eq!(run(&d, &mut s, Fault::default()), Outcome::Done);
        assert_eq!(s.installer_runs, 2);
        let d = tmp("s9b-rb");
        let mut s = Sim::new(Os::Win);
        s.payload_bad_runs = 2; // 재실행 뒤에도 불일치 → RB
        assert!(matches!(run(&d, &mut s, Fault::default()), Outcome::RolledBack(ref f) if f.code == ErrCode::WinPayloadMismatch));
        assert_eq!(s.installer_runs, 2, "재실행은 정확히 1회(폭주 방지)");
        assert!(!s.canonical_new);
    }

    #[test]
    fn rollback_step_failure_is_rb_failed_and_needs_human() {
        let d = tmp("rbf");
        let mut s = Sim::new(Os::Mac);
        s.fail_at.insert("verify", ErrCode::VerifyFailed);
        s.fail_at.insert("rb_prepare", ErrCode::RollbackBlocked);
        assert!(matches!(run(&d, &mut s, Fault::default()), Outcome::RollbackFailed(ref f) if f.code == ErrCode::RollbackBlocked));
        assert_eq!(state(&d), State::RbFailed);
        assert_eq!(s.records, vec![Kind::RollbackFailed]);
    }

    /// ★§7-1 강제 종료 행렬(MA9): 모든 상태 × 직전·직후에 러너를 죽이고 복구기를 돌린다 → 「구본 또는 신본 하나 · 정비 모드 풀림 ·
    /// 데몬 하나 떠 있음 · 종결 저널 · 부팅 가드 풀림」. 정상 경로·롤백 경로(verify_v3) 두 갈래 · 맥·윈 두 기판.
    #[test]
    fn kill_matrix_every_state_before_and_after_recovers_to_one_consistent_version() {
        let forward = [
            State::Locked, State::Fetched, State::Quiesced, State::Drained, State::Rechecked, State::Baselined, State::Confirmed,
            State::Stopped, State::Snapshotted, State::CommitCheck, State::Swapped, State::PayloadOk, State::Started,
            State::Committed, State::Done,
        ];
        let rb = [State::RbPrepared, State::RbSwapped, State::RbRestored, State::RbVerified, State::RbDone];
        let mut cells = 0;
        for os in [Os::Mac, Os::Win] {
            for (path, states) in [("fwd", &forward[..]), ("rb", &rb[..])] {
                for st in states {
                    if os == Os::Mac && *st == State::PayloadOk {
                        continue;
                    }
                    for after in [false, true] {
                        let tag = format!("km-{os:?}-{path}-{}-{after}", st.name());
                        let d = tmp(&tag);
                        let mut s = Sim::new(os);
                        if path == "rb" {
                            // 실 V3 실패(복구기의 재검사에서도 다시 실패하는 실물 결함)
                            s.fail_at.insert("verify", ErrCode::VerifyFailed);
                        }
                        let spec = format!("kill@{}:{}", st.name(), if after { "after" } else { "before" });
                        let o = run(&d, &mut s, Fault::parse(&spec));
                        assert_eq!(o, Outcome::Killed(*st, after), "{tag}");
                        // 죽은 뒤 = 정비 모드·데몬 상태 그대로(실물) → 복구기
                        let was_open = journal::read(&d).journal().map(|j| !j.state.is_terminal()).unwrap_or(false);
                        let o2 = recover(&d, &mut s);
                        let fin = journal::read(&d).journal().map(|j| j.state);
                        if was_open {
                            // ★2판 C2: 저널 = 복구기 세대 · 죽은 러너의 옛 토큰 늦은 쓰기 = Fenced
                            let jj = journal::read(&d).journal().cloned().unwrap();
                            assert_eq!((jj.txn_id.as_str(), jj.epoch), (T2, 2), "{tag}: 세대 승계");
                        }
                        assert!(fin.map(|f| f.is_terminal()).unwrap_or(true), "{tag}: 종결 아님 {fin:?} {o2:?}");
                        assert!(boot_guard(&d).is_none(), "{tag}: 부팅 가드 남음");
                        assert!(!s.quiesced, "{tag}: 정비 모드 안 풀림");
                        match s.daemon {
                            Some("new") => assert!(s.canonical_new, "{tag}: 새 데몬 · 옛 번들"),
                            Some("old") => assert!(!s.canonical_new, "{tag}: 옛 데몬 · 새 번들"),
                            other => panic!("{tag}: 데몬 없음 {other:?} {o2:?}"),
                        }
                        if path == "rb" || matches!(o2, Outcome::RolledBack(_)) {
                            assert!(!s.canonical_new, "{tag}: 롤백 뒤 신판");
                        }
                        // 복구기를 한 번 더 돌려도 아무 일 없음(멱등)
                        let before = (s.canonical_new, s.daemon, s.swaps);
                        assert_eq!(recover(&d, &mut s), Outcome::Nothing, "{tag}");
                        assert_eq!(before, (s.canonical_new, s.daemon, s.swaps), "{tag}");
                        cells += 1;
                    }
                }
            }
        }
        assert_eq!(cells, 2 * (15 + 5) * 2 - 2, "행렬 칸 수");
    }

    /// ★3판 M3(설계 §3-10 ③): stop_seats 표지 = 부팅·기존 좌석은 막지 않고(boot_blocked None) 같은 설치판 seq 에서만 새 좌석 거부
    /// 판정(seats_stopped) · 다른 seq(새 판) = 해제.
    #[test]
    fn stop_seats_marker_blocks_new_seats_only_for_revoked_installed_seq() {
        let d = tmp("stopseats");
        let seq = super::super::buildinfo::release_seq();
        super::super::quiesce::write_json(&d, SEATS_STOP_FILE, &serde_json::json!({"release_seq": seq, "at": 1})).unwrap();
        assert!(boot_blocked(&d).is_none(), "부팅은 막지 않는다(기존 좌석 유지)");
        assert_eq!(seats_stopped(&d), Some(seq), "새 좌석 = 거부");
        super::super::quiesce::write_json(&d, SEATS_STOP_FILE, &serde_json::json!({"release_seq": seq + 1, "at": 1})).unwrap();
        assert_eq!(seats_stopped(&d), None, "다른 판 = 해제");
    }

    /// ★3판 M4(설계 §3-8): 팩 단독 갱신 — 새 팩 없음 = 저널 0 · 적용 성공 = PACK_DONE · 적용 실패 = PACK_ROLLBACK → 복구 → PACK_DONE ·
    /// kill 행렬 2칸(PACK_APPLY 직전·직후) → 복구기 = PACK_DONE · 부팅 가드 풀림 · 재복구 멱등.
    #[test]
    fn pack_only_update_journals_pack_states_and_recovers_from_kills() {
        let d = tmp("packonly-none");
        let mut s = Sim::new(Os::Mac);
        let mut r = Runner::new(&d, T, 1, &mut s);
        assert_eq!(r.run_pack(), Outcome::Nothing);
        assert!(matches!(journal::read(&d), ReadOutcome::Absent), "새 팩 없음 = 저널 0");
        let d = tmp("packonly-ok");
        let mut s = Sim::new(Os::Mac);
        s.pack_new = true;
        assert_eq!(Runner::new(&d, T, 1, &mut s).run_pack(), Outcome::PackDone);
        assert_eq!((state(&d), s.pack_applied), (State::PackDone, 1));
        let d = tmp("packonly-fail");
        let mut s = Sim::new(Os::Mac);
        s.pack_new = true;
        s.fail_at.insert("pack_apply", ErrCode::RotateFailed);
        assert!(matches!(Runner::new(&d, T, 1, &mut s).run_pack(), Outcome::Deferred(_)));
        assert_eq!(state(&d), State::PackDone, "실패 = PACK_ROLLBACK → 복구 → PACK_DONE");
        for after in [false, true] {
            let d = tmp(&format!("packonly-kill-{after}"));
            let mut s = Sim::new(Os::Mac);
            s.pack_new = true;
            let mut r = Runner::new(&d, T, 1, &mut s);
            r.fault = Fault::parse(&format!("kill@PACK_APPLY:{}", if after { "after" } else { "before" }));
            r.soft_kill = true;
            assert_eq!(r.run_pack(), Outcome::Killed(State::PackApply, after));
            if after {
                assert!(boot_guard(&d).is_some(), "PACK_APPLY 잔존 = 부팅 가드");
            }
            let _ = recover(&d, &mut s);
            let fin = journal::read(&d).journal().map(|j| j.state);
            assert!(fin.map(|f| f.is_terminal()).unwrap_or(true), "{after}: 종결 아님 {fin:?}");
            assert!(boot_guard(&d).is_none(), "{after}: 부팅 가드 남음");
            assert_eq!(recover(&d, &mut s), Outcome::Nothing, "{after}: 재복구 멱등");
        }
    }

    /// ★3판 m3: 윈 설치기 종료 확인 불가(RollbackBlocked) = RB 단계 0(옛 설치기 재실행 0) · RB_FAILED · 결과 rollback_failed.
    #[test]
    fn installer_stuck_goes_straight_to_rb_failed_without_rerunning_installer() {
        let d = tmp("stuck");
        let mut s = Sim::new(Os::Win);
        s.fail_at.insert("swap", ErrCode::RollbackBlocked);
        let o = run(&d, &mut s, Fault::default());
        assert!(matches!(o, Outcome::RollbackFailed(_)), "{o:?}");
        assert_eq!(state(&d), State::RbFailed);
        assert_eq!(s.installer_runs, 0, "옛 설치기 재실행 0");
    }

    /// ★2판 C11: S11 durable commit(수용 기록·롤백 자산) 실패 = DONE 아님 → 롤백(옛 판) · 결과 = rollback.
    #[test]
    fn commit_failure_is_not_done_and_rolls_back() {
        for os in [Os::Mac, Os::Win] {
            let d = tmp(&format!("commitfail-{os:?}"));
            let mut s = Sim::new(os);
            s.fail_at.insert("commit", ErrCode::RotateFailed);
            let o = run(&d, &mut s, Fault::default());
            assert!(matches!(o, Outcome::RolledBack(_)), "{os:?} {o:?}");
            assert_eq!(state(&d), State::RbDone);
            assert!(!s.canonical_new, "{os:?}: 옛 판");
        }
    }

    /// ★2판 C2: 세대 승계 = 저널 토큰 원자 교체 → 죽은 러너(옛 토큰)의 늦은 전이는 Fenced · 같은 토큰 재승계 = 무변경.
    #[test]
    fn takeover_fences_old_owner_late_write() {
        let d = tmp("takeover");
        let mut s = Sim::new(Os::Mac);
        assert_eq!(run(&d, &mut s, Fault::parse("kill@S9_SWAPPED:after")), Outcome::Killed(State::Swapped, true));
        let g0 = journal::read(&d).journal().unwrap().generation;
        let j = journal::takeover(&d, T2, 2).unwrap();
        assert_eq!((j.state, j.txn_id.as_str(), j.epoch, j.generation), (State::Swapped, T2, 2, g0 + 1));
        assert!(matches!(journal::advance(&d, T, 1, State::PayloadOk, |_| {}), Err(journal::AdvanceErr::Fenced)), "옛 토큰 늦은 쓰기");
        assert_eq!(journal::takeover(&d, T2, 2).unwrap().generation, g0 + 1, "같은 세대 = 무변경");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn corrupt_journal_blocks_boot_then_reconstruct_or_seats_blocked() {
        let d = tmp("corrupt");
        std::fs::write(d.join(journal::JOURNAL_FILE), b"{broken").unwrap();
        std::fs::write(d.join(journal::JOURNAL_PREV_FILE), b"{broken").unwrap();
        assert!(boot_guard(&d).unwrap().starts_with("journal_corrupt"));
        let mut s = Sim::new(Os::Mac);
        s.reconstruct_ok = false;
        assert!(matches!(recover(&d, &mut s), Outcome::SeatsBlocked(_)));
        assert!(boot_guard(&d).is_some(), "재구성 실패 = 좌석 0 유지");
        assert_eq!(s.records, vec![Kind::SeatsBlocked]);
        s.reconstruct_ok = true;
        assert_eq!(recover(&d, &mut s), Outcome::Nothing);
        assert!(boot_guard(&d).is_none(), "재구성 성공 = 부팅 허용");
        assert!(s.records.contains(&Kind::JournalCorrupt));
    }

    #[test]
    fn boot_blocked_allows_only_live_lock_holder_for_non_terminal_journal() {
        let d = tmp("bootlock");
        journal::advance(&d, T, 1, State::Locked, |_| {}).unwrap();
        journal::advance(&d, T, 1, State::Fetched, |_| {}).unwrap();
        assert!(boot_blocked(&d).is_none(), "S2 = 정비 모드 TTL 구간(막지 않음)");
        for st in [State::Quiesced, State::Drained, State::Rechecked, State::Baselined, State::Confirmed, State::Stopped] {
            journal::advance(&d, T, 1, st, |_| {}).unwrap();
        }
        assert!(boot_blocked(&d).unwrap().starts_with("recover_pending"), "잠금 없음(죽은 러너) = 막음");
        // ★2판 C3: 토큰 없는 수동 rotate 가 새 잠금을 잡음 = 저널 소유자 아님 → 막음
        let g = crate::update::lock::acquire(&d, "rotate").unwrap();
        assert!(boot_blocked(&d).is_some(), "저널과 무관한 잠금 = 막음");
        drop(g);
        // 러너 계보지만 저널 토큰과 다른 세대 = 막음
        let g = crate::update::lock::acquire(&d, "runner").unwrap();
        assert!(boot_blocked(&d).is_some(), "토큰 불일치 = 막음");
        // 복구기 승계(같은 세대) = 허용
        let t = g.token();
        journal::takeover(&d, &t.txn_id, t.epoch).unwrap();
        assert!(boot_blocked(&d).is_none(), "살아 있는 러너/복구기가 같은 세대로 이끄는 중 = 허용");
        drop(g);
        assert!(boot_blocked(&d).is_some());
    }

    #[test]
    fn pack_journal_states_recover_via_pack_recovery() {
        let d = tmp("pack");
        journal::advance(&d, T, 1, State::Locked, |_| {}).unwrap();
        journal::advance(&d, T, 1, State::PackApply, |_| {}).unwrap();
        assert!(boot_guard(&d).is_some());
        let mut s = Sim::new(Os::Mac);
        assert_eq!(recover(&d, &mut s), Outcome::PackDone);
        assert_eq!(state(&d), State::PackDone);
    }

    #[test]
    fn fault_spec_parse_and_release_build_ignores_env() {
        let f = Fault::parse("verify_v3, kill@S9:after ,pause@RB_SWAPPED");
        assert!(f.verify_v3 && f.kill(State::Swapped, true) && !f.kill(State::Swapped, false) && f.pause(State::RbSwapped));
        assert!(!f.kill(State::PayloadOk, true), "S9 는 S9b 를 덮지 않는다");
        assert!(Fault::parse("kill@S9b_PAYLOAD_OK").kill(State::PayloadOk, false));
    }
}
