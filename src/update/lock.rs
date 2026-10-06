//! 전역 트랜잭션 잠금 + 위임 토큰 `(txn_id, epoch)` — 설계 AUTO-UPDATE-118 §3-2 · 1R BLOCK 11 · 2R 신규 BLOCK 1 · 📌13′.
//!
//! - 잠금 = `<상태 폴더>/txn.lock` 의 OS 배타 잠금(std `File::try_lock` = 유닉스 `flock(LOCK_EX|LOCK_NB)` · 윈 `LockFileEx`).
//!   OS 가 프로세스 종료 때 풀어 준다(죽은 소유자 = 자동 해제).
//! - 소유자 기록 = `<상태 폴더>/txn.owner.json` `{owner, pid, txn_id(128비트), epoch, started_at, boot_id}` — **잠금 파일과
//!   따로** 둔다: 윈 `LockFileEx` 는 잠긴 바이트 범위를 다른 핸들이 **읽지도** 못하게 막아서, 위임 받은 자식이 소유자 내용을
//!   읽어야 하는 계약(①)과 충돌한다. 기록은 원자 쓰기라 찢어진 내용이 없고, 낡은 기록(잠금 풀림)은 ② 가 걸러낸다.
//! - `epoch` 는 잠글 때마다 +1 — 옛 토큰(epoch 불일치)의 늦은 쓰기를 거부한다.
//! - 위임: 러너가 자식을 `--txn <txn_id>:<epoch>` + env `CYS_UPDATE_TXN` 으로 부른다. 자식은 잠금을 **다시 잡지 않고**
//!   ① 소유자 기록의 `txn_id`·`epoch` = 토큰 ② 잠금이 실제로 잡혀 있음(비차단 시도 = 실패여야 정상) ③ 소유 pid 가 자기 조상 —
//!   셋 다 맞을 때만 진행한다. 하나라도 어긋나면 `txn_busy`(재시도 0). 토큰 없는 호출은 평소처럼 잠금을 잡는다.
//!
//! U1 = 모듈 + 시험. 참가자 배선(rotate·pack-update·pack-plan·init-pack·데몬 자동 기동·설치 링크·NSIS ⓪-a)은 U2·U3.

use super::errors::{ErrCode, UpdateErr};
use serde::{Deserialize, Serialize};
use std::fs::{File, OpenOptions, TryLockError};
use std::path::{Path, PathBuf};

pub const ENV_TXN: &str = "CYS_UPDATE_TXN";
pub const LOCK_FILE: &str = "txn.lock";
pub const OWNER_FILE: &str = "txn.owner.json";
/// ★2R B6/H⑥: 위임 자식 잠금 — 위임 받은 자식이 작업 끝까지 쥔다(부모가 죽어 `txn.lock` 이 풀려도 새 트랜잭션은 이것이 풀릴 때까지
/// 못 연다). 자식은 한 번에 하나(러너는 자식을 차례로 부른다).
pub const CHILD_LOCK_FILE: &str = "txn.child.lock";

/// ★4판(codex 3R MINOR 승격): 중첩 위임 깊이별 자식 잠금(`txn.child.lock.<깊이>` · 깊이 1..=[`MAX_NEST`]) — 같은 깊이 형제는 서로 막는다.
pub const MAX_NEST: u32 = 4;

pub fn child_lock_name(depth: u32) -> String {
    if depth == 0 {
        CHILD_LOCK_FILE.to_string()
    } else {
        format!("{CHILD_LOCK_FILE}.{depth}")
    }
}
/// ★2판(C1 개정 · 윈 CI T8): 토큰 없는 CLI 참가자(rotate·init-pack·pack-update·pack-plan)의 **공유** 잠금 — 여럿이 함께 쥘 수 있고,
/// 러너·복구기([`acquire`])는 이것이 쥐어져 있으면 트랜잭션을 열지 않는다. 설치기(⓪-a)가 보는 `txn.lock` 은 건드리지 않는다
/// (짧은 팩 명령이 설치기 「갱신 중」 창을 띄우던 회귀 차단).
pub const PART_LOCK_FILE: &str = "txn.part.lock";

/// 위임 토큰.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Token {
    pub txn_id: String,
    pub epoch: u64,
}

impl Token {
    /// `<txn_id 32자 16진>:<epoch>` 파싱.
    pub fn parse(s: &str) -> Option<Token> {
        let (id, ep) = s.trim().split_once(':')?;
        if id.len() != 32 || !id.chars().all(|c| c.is_ascii_hexdigit()) {
            return None;
        }
        Some(Token { txn_id: id.to_ascii_lowercase(), epoch: ep.parse().ok()? })
    }
    pub fn render(&self) -> String {
        format!("{}:{}", self.txn_id, self.epoch)
    }
}

/// 소유자 기록.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Owner {
    pub owner: String,
    pub pid: u32,
    pub txn_id: String,
    pub epoch: u64,
    pub started_at: i64,
    pub boot_id: u64,
    /// ★1R B6: 소유 프로세스 시작 시각(sysinfo · 초) — pid 재사용을 가른다.
    pub start_time: u64,
    /// ★1R B6: 놓을 때 잠금을 풀기 **전에** true 로 기록(묘비) — 「기록은 옛 소유자 · 잠금은 새 소유자」 창을 닫는다.
    #[serde(default)]
    pub released: bool,
}

impl Owner {
    pub fn token(&self) -> Token {
        Token { txn_id: self.txn_id.clone(), epoch: self.epoch }
    }
}

/// 잡은 잠금. drop = ① 소유자 기록에 묘비(`released:true`) 원자 쓰기 ② 그다음 잠금 해제(순서 고정 — B6).
#[derive(Debug)]
pub struct TxnGuard {
    file: Option<File>,
    pub owner: Owner,
    dir: PathBuf,
}

impl TxnGuard {
    pub fn token(&self) -> Token {
        self.owner.token()
    }
    pub fn dir(&self) -> &Path {
        &self.dir
    }
}

impl Drop for TxnGuard {
    fn drop(&mut self) {
        let mut tomb = self.owner.clone();
        tomb.released = true;
        if let Ok(b) = serde_json::to_vec_pretty(&tomb) {
            let _ = super::write_private(&self.dir.join(OWNER_FILE), &b);
        }
        if let Some(f) = self.file.take() {
            let _ = f.unlock();
        }
    }
}

fn busy(d: impl Into<String>) -> UpdateErr {
    UpdateErr::new(ErrCode::TxnBusy, "lock", d)
}

fn open_lock(dir: &Path) -> Result<File, UpdateErr> {
    open_lock_file(dir, LOCK_FILE)
}

/// 잠금 파일 열기(0600 으로 만들고 · ★2R M3: 이미 있던 파일도 소유자 전용인지 재검증 — 아니면 판정 불가).
fn open_lock_file(dir: &Path, name: &str) -> Result<File, UpdateErr> {
    super::ensure_private_dir(dir).map_err(busy)?;
    let mut o = OpenOptions::new();
    o.read(true).write(true).create(true).truncate(false);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        o.mode(0o600);
    }
    let path = dir.join(name);
    let f = o.open(&path).map_err(|e| busy(format!("잠금 파일: {e}")))?;
    super::check_private_file(&path).map_err(busy)?;
    Ok(f)
}

pub fn read_owner(dir: &Path) -> Option<Owner> {
    serde_json::from_slice(&std::fs::read(dir.join(OWNER_FILE)).ok()?).ok()
}

/// 잠금이 지금 (누군가에게) 잡혀 있는가 — 비차단 시도가 실패하면 잡혀 있다. 시도가 성공하면 즉시 놓는다.
/// `None` = 판정 불가(열기 실패 등).
/// ★3판(Fable 2R M1): 탐침 = **공유** 시도(탐침끼리·공유 참가자와 충돌 0 — 배타 탐침의 순간 잠금이 다른 CLI·러너·설치기 ⓪-a 에 거짓
/// 「잡힘」 을 주던 창 축소) · `WouldBlock` 이면 25ms × 4 다시 본 뒤에도 막힐 때만 잡힘.
pub fn is_held(dir: &Path) -> Option<bool> {
    let f = OpenOptions::new().read(true).write(true).open(dir.join(LOCK_FILE)).ok()?;
    for i in 0..5 {
        match f.try_lock_shared() {
            Ok(()) => {
                let _ = f.unlock();
                return Some(false);
            }
            Err(TryLockError::WouldBlock) if i < 4 => std::thread::sleep(std::time::Duration::from_millis(25)),
            Err(TryLockError::WouldBlock) => return Some(true),
            Err(TryLockError::Error(_)) => return None,
        }
    }
    Some(true)
}

/// 잠금을 잡는다(비차단 · 잡혀 있으면 `txn_busy`). 새 `txn_id`·`epoch`(+1)를 소유자 기록에 원자 기록한다.
pub fn acquire(dir: &Path, owner: &str) -> Result<TxnGuard, UpdateErr> {
    let f = open_lock(dir)?;
    // ★3판(Fable 2R M1): 막혔는데 산 소유자 기록이 없으면(없음·묘비 = 남의 순간 탐침일 수 있음) 짧게 다시 본다(25ms × 8).
    let mut tries = 0;
    loop {
        match f.try_lock() {
            Ok(()) => break,
            Err(TryLockError::WouldBlock) => {
                let o = read_owner(dir);
                let live_owner = o.as_ref().map(|o| !o.released).unwrap_or(false);
                if live_owner || tries >= 8 {
                    let who = o.map(|o| format!("{}(pid {})", o.owner, o.pid)).unwrap_or_else(|| "?".into());
                    return Err(busy(format!("잠금 소유 중: {who}")));
                }
                tries += 1;
                std::thread::sleep(std::time::Duration::from_millis(25));
            }
            Err(TryLockError::Error(e)) => return Err(busy(format!("잠금 시도: {e}"))),
        }
    }
    let prev_owner = std::fs::read(dir.join(OWNER_FILE)).ok();
    let epoch = read_owner(dir).map(|o| o.epoch + 1).unwrap_or(1);
    let pid = std::process::id();
    let o = Owner {
        owner: owner.to_string(),
        pid,
        txn_id: super::buildinfo::random_hex128().map_err(busy)?,
        epoch,
        started_at: super::clock::wall_now(),
        boot_id: super::clock::boot_id(),
        start_time: pid_start_time(pid).unwrap_or(0),
        released: false,
    };
    let bytes = serde_json::to_vec_pretty(&o).map_err(|e| busy(e.to_string()))?;
    super::write_private(&dir.join(OWNER_FILE), &bytes).map_err(|e| busy(format!("소유자 기록: {e}")))?;
    // ★2R B6/H⑥: 옛 트랜잭션의 위임 자식이 아직 일하는 중이면(자식 잠금 쥠) 새로 열지 않는다. 순서 = 새 소유자 기록을 **먼저** 쓰고
    //   자식 잠금을 본다 — 그 뒤에 자식 잠금을 잡는 옛 자식은 ① 에서 새 기록(토큰 불일치)을 읽고 물러난다. 거절이면 직전 기록 복원.
    if !super::mutant("B6g") {
        // 거절(자식 잠금 쥐어짐 · ★3R F4: 자식 잠금 파일을 못 엶·권한 불일치 포함) = 직전 소유자 기록 복원 + 잠금 놓음.
        let refuse = |why: String| -> UpdateErr {
            match &prev_owner {
                Some(b) => {
                    let _ = super::write_private(&dir.join(OWNER_FILE), b);
                }
                None => {
                    let _ = std::fs::remove_file(dir.join(OWNER_FILE));
                }
            }
            let _ = f.unlock();
            busy(why)
        };
        // ★4판: 깊이 0 + 중첩 깊이별 자식 잠금 전부(부모 위임 자식이 죽어도 손자가 살아 있으면 새 트랜잭션을 열지 않는다)
        for depth in 0..=MAX_NEST {
            let name = child_lock_name(depth);
            if depth > 0 && !dir.join(&name).exists() {
                continue;
            }
            let child = match open_lock_file(dir, &name) {
                Ok(c) => c,
                Err(e) => return Err(refuse(format!("자식 잠금 파일: {}", e.detail))),
            };
            match child.try_lock() {
                Ok(()) => {
                    let _ = child.unlock();
                }
                Err(TryLockError::WouldBlock) => return Err(refuse(format!("위임 자식이 아직 작업 중(자식 잠금 {name})"))),
                Err(TryLockError::Error(e)) => return Err(refuse(format!("자식 잠금 시도: {e}"))),
            }
        }
        // ★2판 C1: 토큰 없는 CLI 참가자(공유 잠금)가 일하는 중이면 열지 않는다 — 순서 = 소유자 기록·txn.lock 을 **먼저** 쥐고 본다
        //   (그 뒤 공유 잠금을 잡는 참가자는 txn.lock 이 잡힌 것을 보고 물러난다 · 양방향 원자).
        let part = match open_lock_file(dir, PART_LOCK_FILE) {
            Ok(p) => p,
            Err(e) => return Err(refuse(format!("참가자 잠금 파일: {}", e.detail))),
        };
        match part.try_lock() {
            Ok(()) => {
                let _ = part.unlock();
            }
            Err(TryLockError::WouldBlock) => return Err(refuse("CLI 참가자(rotate·팩 명령)가 작업 중(참가자 잠금)".into())),
            Err(TryLockError::Error(e)) => return Err(refuse(format!("참가자 잠금 시도: {e}"))),
        }
    }
    Ok(TxnGuard { file: Some(f), owner: o, dir: dir.to_path_buf() })
}

/// 프로세스 판정 공급자(실 구현 = [`ProcProbe::real`] · 시험은 바꿔 끼운다).
pub struct ProcProbe<'a> {
    pub is_ancestor: &'a dyn Fn(u32) -> Option<bool>,
    pub start_time: &'a dyn Fn(u32) -> Option<u64>,
}

impl ProcProbe<'static> {
    pub fn real() -> ProcProbe<'static> {
        ProcProbe { is_ancestor: &pid_is_ancestor, start_time: &pid_start_time }
    }
}

/// 위임 검증(1R B6 · 순서 고정): ⓪ 인자 토큰 = env 토큰 → ① 소유자 기록 읽기(묘비 아님 · txn_id·epoch = 토큰) → ③ 소유 pid 가
/// 조상 → ② 잠금 실재 → ①′ 소유자 기록 **다시 읽기** = 처음과 같음(그 사이 옛 소유자가 묘비를 쓰고 놓았거나 새 소유자가 기록을
/// 바꿨으면 다름 — 기록은 「소유자 → 묘비 → 새 소유자」로만 바뀌므로 두 번 같으면 ② 시점의 잠금 주인 = 그 소유자) → ③′ 소유 pid 의
/// 시작 시각 = 기록(죽은 소유자 pid 재사용 차단 · 윈 「PID + 생성 시각」). 하나라도 어긋나면 `txn_busy`.
/// ★2R B6/H⑥: 위임 받은 자식의 잠금 증표 — 자식 잠금(`txn.child.lock`)을 쥐고 있다. drop(자식 작업 끝) 때 놓는다. 부모가 먼저
/// 죽어 `txn.lock` 이 풀려도 이것이 살아 있는 동안 [`acquire`] 는 `txn_busy` 다(잠금 세대 유지).
#[derive(Debug)]
pub struct DelegatedGuard {
    file: Option<File>,
    pub owner: Owner,
}

impl Drop for DelegatedGuard {
    fn drop(&mut self) {
        if let Some(f) = self.file.take() {
            let _ = f.unlock();
        }
    }
}

/// ★3판(Fable 2R N1): 위임 자식이 다시 위임할 때(rotate → init-pack) 자식에게 넘기는 깊이 표지 — 깊이 ≥1 이면 자식 잠금을 다시 잡지
/// 않는다(같은 트랜잭션 안 중첩 = 부모가 이미 자식 잠금을 쥠 · 재진입). 토큰·소유자 사슬·조상 검증은 그대로 한다.
pub const ENV_TXN_DEPTH: &str = "CYS_UPDATE_TXN_DEPTH";

pub fn verify_delegated(dir: &Path, arg: &Token, env: Option<&Token>, probe: &ProcProbe) -> Result<DelegatedGuard, UpdateErr> {
    verify_delegated_at(dir, arg, env, probe, 0)
}

/// `depth` = 이 프로세스의 위임 깊이([`ENV_TXN_DEPTH`] · 0 = 러너의 직접 자식).
pub fn verify_delegated_at(dir: &Path, arg: &Token, env: Option<&Token>, probe: &ProcProbe, depth: u32) -> Result<DelegatedGuard, UpdateErr> {
    if env != Some(arg) && !super::mutant("B6") {
        return Err(busy("⓪ --txn 인자 ≠ CYS_UPDATE_TXN"));
    }
    if depth > MAX_NEST {
        return Err(busy(format!("위임 깊이 {depth} > {MAX_NEST}")));
    }
    if depth >= 1 && !super::mutant("U2-NEST") {
        // 부모 위임 자식이 깊이 0 자식 잠금을 쥔 채 우리를 띄웠다 — 그 잠금은 재진입(안 잡음)하되 ★4판(codex 3R): **같은 깊이 형제**는
        //   깊이별 잠금으로 서로 막는다(전엔 잠금 0 = 형제 둘 다 통과). 사슬 검증(소유 pid = 조상 · 토큰 · 잠금 생존 · 시작 시각)은 그대로.
        let file = if super::mutant("U2-NESTSIB") {
            None
        } else {
            let f = open_lock_file(dir, &child_lock_name(depth))?;
            match f.try_lock() {
                Ok(()) => {}
                Err(TryLockError::WouldBlock) => return Err(busy(format!("같은 깊이({depth}) 위임 형제가 작업 중"))),
                Err(TryLockError::Error(e)) => return Err(busy(format!("깊이 {depth} 자식 잠금 시도: {e}"))),
            }
            Some(f)
        };
        let owner = verify_owner_chain(dir, arg, probe)?;
        return Ok(DelegatedGuard { file, owner });
    }
    // 자식 잠금을 먼저 잡고(다른 위임 자식 = busy) 아래 검증을 한다 — 검증 실패면 guard drop 으로 놓인다.
    let child = open_lock_file(dir, CHILD_LOCK_FILE)?;
    match child.try_lock() {
        Ok(()) => {}
        Err(TryLockError::WouldBlock) => return Err(busy("다른 위임 자식이 작업 중(자식 잠금)")),
        Err(TryLockError::Error(e)) => return Err(busy(format!("자식 잠금 시도: {e}"))),
    }
    let owner = verify_owner_chain(dir, arg, probe)?; // 실패 = `child` drop = 자식 잠금 놓음
    Ok(DelegatedGuard { file: Some(child), owner })
}

fn verify_owner_chain(dir: &Path, arg: &Token, probe: &ProcProbe) -> Result<Owner, UpdateErr> {
    let o = read_owner(dir).ok_or_else(|| busy("① 소유자 기록 없음"))?;
    if o.released {
        return Err(busy("① 소유자가 이미 놓음(묘비)"));
    }
    if o.txn_id != arg.txn_id || o.epoch != arg.epoch {
        return Err(busy(format!("① 토큰 불일치 (epoch {} vs {})", arg.epoch, o.epoch)));
    }
    match (probe.is_ancestor)(o.pid) {
        Some(true) => {}
        Some(false) => return Err(busy(format!("③ 소유 pid {} 가 조상 아님", o.pid))),
        None => return Err(busy("③ 조상 판정 불가")),
    }
    match is_held(dir) {
        Some(true) => {}
        Some(false) => return Err(busy("② 잠금이 풀려 있음(낡은 토큰)")),
        None => return Err(busy("② 잠금 판정 불가")),
    }
    if !super::mutant("B6") {
        if read_owner(dir).as_ref() != Some(&o) {
            return Err(busy("①′ 소유자 기록이 검증 중 바뀜(넘겨주기 경합)"));
        }
        if (probe.start_time)(o.pid) != Some(o.start_time) {
            return Err(busy(format!("③′ pid {} 시작 시각 불일치(재사용·사망)", o.pid)));
        }
    }
    Ok(o)
}

/// 참가 결과 — 직접 소유 · 위임 받음.
#[derive(Debug)]
pub enum Participation {
    Owner(TxnGuard),
    Delegated(DelegatedGuard),
    /// ★2판 C1: 토큰 없는 CLI — 참가자 공유 잠금(쥔 동안 러너·복구기가 트랜잭션을 열지 못함).
    Participant(PartGuard),
}

/// 참가자 공유 잠금 보유(drop = 놓음).
#[derive(Debug)]
pub struct PartGuard {
    file: Option<File>,
}

impl Drop for PartGuard {
    fn drop(&mut self) {
        if let Some(f) = self.file.take() {
            let _ = f.unlock();
        }
    }
}

/// 참가자 입구: 토큰(인자 `--txn` · env `CYS_UPDATE_TXN`)이 하나라도 있으면 위임 검증(재잠금 0 · 둘이 같아야 함),
/// 둘 다 없으면 잠금을 잡는다.
pub fn acquire_or_delegate(dir: &Path, owner: &str, arg: Option<&str>, env: Option<&str>) -> Result<Participation, UpdateErr> {
    match (arg, env) {
        (None, None) => acquire(dir, owner).map(Participation::Owner),
        (Some(a), e) => {
            let tok = Token::parse(a).ok_or_else(|| busy("토큰 형식"))?;
            let et = e.and_then(Token::parse);
            let depth = std::env::var(ENV_TXN_DEPTH).ok().and_then(|v| v.parse::<u32>().ok()).unwrap_or(0);
            verify_delegated_at(dir, &tok, et.as_ref(), &ProcProbe::real(), depth).map(Participation::Delegated)
        }
        (None, Some(_)) => Err(busy("⓪ env 토큰만 있고 --txn 인자 없음")),
    }
}

/// CLI 참가자 입구(★2판 codex 1R C1): 존재 검사 없이 [`acquire_or_delegate`] 로 원자 참가한다. 토큰이 없고 잠금 파일을 **만들 수조차
/// 없을 때**(갱신 폴더 생성·열기 실패 = 갱신이 돌 수 없는 기계)만 `Ok(None)` = 평소대로 진행(설치기·설치 링크 무변경). 잠금이 잡혀
/// 있음·토큰 불일치 = Err(txn_busy).
pub fn participate(dir: &Path, owner: &str, arg: Option<&str>, env: Option<&str>) -> Result<Option<Participation>, UpdateErr> {
    if arg.is_some() || env.is_some() {
        return acquire_or_delegate(dir, owner, arg, env).map(Some);
    }
    let _ = owner; // 공유 참가자는 소유자 기록을 쓰지 않는다(설치기·부팅 가드가 보는 txn.lock·txn.owner.json 무접촉)
    // ★2판 C1(개정): 참가자 공유 잠금을 **먼저** 쥐고 txn.lock 을 본다 — 러너는 txn.lock 을 먼저 쥐고 참가자 잠금을 본다(양방향 원자).
    // ★3판(Fable 2R m1): 평소대로(참가 0) = 갱신 폴더를 만들 수조차 없을 때만 · 권한 불일치 등 그 밖 = Err(조용한 fail-open 0)
    // ★4판(codex 3R m1): 이미 있는 폴더의 소유자·권한(윈 DACL) 불일치 = Err(조용히 참가 없이 진행하지 않는다) · 폴더가 없고 만들 수도 없을 때만 Ok(None)
    let existed = dir.exists();
    if let Err(e) = super::ensure_private_dir(dir) {
        if existed && !super::mutant("U2-PRIVDIR") {
            return Err(busy(format!("갱신 폴더 소유자·권한 불일치: {e}")));
        }
        return Ok(None);
    }
    let part = open_lock_file(dir, PART_LOCK_FILE)?;
    let mut got = false;
    for _ in 0..40 {
        // 러너의 순간 배타 시도(acquire 의 try_lock) 와만 겹친다 — 짧게 다시 본다
        match part.try_lock_shared() {
            Ok(()) => {
                got = true;
                break;
            }
            Err(TryLockError::WouldBlock) => std::thread::sleep(std::time::Duration::from_millis(25)),
            Err(TryLockError::Error(e)) => return Err(busy(format!("참가자 잠금 시도: {e}"))),
        }
    }
    if !got {
        return Err(busy("참가자 잠금을 얻지 못함"));
    }
    let g = PartGuard { file: Some(part) };
    let held = if dir.join(LOCK_FILE).exists() { is_held(dir) } else { Some(false) };
    match held {
        Some(false) => Ok(Some(Participation::Participant(g))),
        Some(true) => {
            let who = read_owner(dir).map(|o| format!("{}(pid {})", o.owner, o.pid)).unwrap_or_else(|| "?".into());
            Err(busy(format!("잠금 소유 중: {who}")))
        }
        None => Err(busy("잠금 판정 불가")),
    }
}

/// `pid` 가 이 프로세스의 조상(부모·조부모 …)인가 — sysinfo 부모 사슬(최대 64단). 판정 불가 = None.
pub fn pid_is_ancestor(pid: u32) -> Option<bool> {
    use sysinfo::{Pid, ProcessRefreshKind, ProcessesToUpdate, System};
    let mut sys = System::new();
    sys.refresh_processes_specifics(ProcessesToUpdate::All, true, ProcessRefreshKind::nothing());
    let mut cur = sys.process(Pid::from_u32(std::process::id()))?.parent();
    for _ in 0..64 {
        let Some(p) = cur else { return Some(false) };
        if p.as_u32() == pid {
            return Some(true);
        }
        cur = sys.process(p).and_then(|x| x.parent());
    }
    Some(false)
}

/// 프로세스 시작 시각(sysinfo · epoch 초) — 없는 pid = None.
pub fn pid_start_time(pid: u32) -> Option<u64> {
    use sysinfo::{Pid, ProcessRefreshKind, ProcessesToUpdate, System};
    let p = Pid::from_u32(pid);
    // ★2판: 부하 중 단발 조회가 빈손으로 오는 일이 있어(전수 병렬 실행에서 b6g 1회 적색 · 단독 3/3 초록 — 원인 확정 아님) 3회까지.
    for _ in 0..3 {
        let mut sys = System::new();
        sys.refresh_processes_specifics(ProcessesToUpdate::Some(&[p]), true, ProcessRefreshKind::nothing());
        if let Some(t) = sys.process(p).map(|x| x.start_time()) {
            return Some(t);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cys-u1-lock-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        d
    }

    /// ★2판 C1(개정 · 윈 CI T8): 토큰 없는 CLI = 참가자 **공유** 잠금 — 둘이 함께 참가 가능 · 그동안 러너 acquire = 거부 · 러너가 쥔 동안
    /// 참가 = busy · 참가는 txn.lock·소유자 기록을 만들지 않음(설치기 ⓪-a 무영향) · env 만 = ⓪ 거부.
    #[test]
    fn participate_is_atomic_without_exists_shortcut() {
        let d = tmp("participate");
        let a = participate(&d, "pack-plan", None, None).unwrap().expect("참가");
        assert!(matches!(a, Participation::Participant(_)));
        let b = participate(&d, "init-pack", None, None).unwrap().expect("공유 = 함께 참가");
        assert!(!d.join(LOCK_FILE).exists() && !d.join(OWNER_FILE).exists(), "설치기가 보는 txn.lock·소유자 기록 무접촉");
        assert!(acquire(&d, "runner").unwrap_err().detail.contains("참가자"), "참가자 작업 중 = 러너 거부");
        drop((a, b));
        let g = acquire(&d, "runner").unwrap();
        assert!(participate(&d, "init-pack", None, None).is_err(), "러너가 쥔 동안 = txn_busy");
        let tok = g.token().render();
        assert!(participate(&d, "pack-plan", None, Some(&tok)).is_err(), "env 만 = ⓪ 거부");
        drop(g);
        assert!(participate(&d, "init-pack", None, None).unwrap().is_some(), "놓은 뒤 = 다시 참가");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★3판 M1: 탐침이 공유라 공유 보유자(다른 탐침·참가자)와 충돌 0 · 배타 보유(러너)만 잡힘 · 러너 acquire 는 산 소유자 없는
    /// 순간 막힘(남의 공유 탐침)을 기다려 넘는다.
    #[test]
    fn probe_is_shared_and_runner_rides_out_transient_probe() {
        let d = tmp("probe");
        std::fs::create_dir_all(&d).unwrap();
        let f = open_lock(&d).unwrap();
        f.lock_shared().unwrap(); // 남의 탐침(공유) 보유 중
        assert_eq!(is_held(&d), Some(false), "공유끼리 = 안 잡힘(1·2판 배타 탐침이면 거짓 잡힘)");
        let d2 = d.clone();
        let t = std::thread::spawn(move || acquire(&d2, "runner").map(|_| ()));
        std::thread::sleep(std::time::Duration::from_millis(60));
        f.unlock().unwrap(); // 탐침 끝
        assert!(t.join().unwrap().is_ok(), "산 소유자 없는 순간 막힘 = 재시도로 획득");
        let g = acquire(&d, "runner").unwrap();
        assert_eq!(is_held(&d), Some(true), "배타 보유 = 잡힘");
        drop(g);
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn token_parse_render() {
        let t = Token::parse("0123456789ABCDEF0123456789abcdef:7").unwrap();
        assert_eq!(t.epoch, 7);
        assert_eq!(t.render(), "0123456789abcdef0123456789abcdef:7");
        for bad in ["", "x:1", "0123456789abcdef0123456789abcdef", "0123456789abcdef0123456789abcdef:-1", "zz23456789abcdef0123456789abcdef:1"] {
            assert!(Token::parse(bad).is_none(), "{bad}");
        }
    }

    #[test]
    fn second_acquire_is_busy_and_release_on_drop_bumps_epoch() {
        let d = tmp("busy");
        let g = acquire(&d, "runner").unwrap();
        assert_eq!(g.owner.epoch, 1);
        assert_eq!(is_held(&d), Some(true));
        let e = acquire(&d, "rotate").unwrap_err();
        assert_eq!(e.code, ErrCode::TxnBusy);
        drop(g);
        assert_eq!(is_held(&d), Some(false), "drop = 해제");
        let g2 = acquire(&d, "rotate").unwrap();
        assert_eq!(g2.owner.epoch, 2, "epoch +1");
        drop(g2);
        let _ = std::fs::remove_dir_all(&d);
    }

    fn yes() -> ProcProbe<'static> {
        ProcProbe { is_ancestor: &|_| Some(true), start_time: &|p| pid_start_time(p) }
    }

    /// §7-1 「위임 토큰 3조건(내용 불일치·잠금 없음·조상 아님 → txn_busy) · 토큰 없는 자식 = 재잠금」.
    #[test]
    fn delegation_conditions() {
        let d = tmp("deleg");
        let g = acquire(&d, "runner").unwrap();
        let tok = g.token();
        assert!(verify_delegated(&d, &tok, Some(&tok), &yes()).is_ok());
        let old = Token { epoch: tok.epoch - 1, ..tok.clone() };
        assert!(verify_delegated(&d, &old, Some(&old), &yes()).unwrap_err().detail.contains('①'));
        let other = Token { txn_id: "f".repeat(32), ..tok.clone() };
        assert!(verify_delegated(&d, &other, Some(&other), &yes()).unwrap_err().detail.contains('①'));
        let no = ProcProbe { is_ancestor: &|_| Some(false), start_time: &|p| pid_start_time(p) };
        assert!(verify_delegated(&d, &tok, Some(&tok), &no).unwrap_err().detail.contains('③'));
        let unk = ProcProbe { is_ancestor: &|_| None, start_time: &|p| pid_start_time(p) };
        assert!(verify_delegated(&d, &tok, Some(&tok), &unk).unwrap_err().detail.contains('③'));
        assert_eq!(acquire_or_delegate(&d, "rotate", None, None).unwrap_err().code, ErrCode::TxnBusy);
        drop(g);
        assert!(read_owner(&d).unwrap().released, "놓을 때 묘비");
        assert!(verify_delegated(&d, &tok, Some(&tok), &yes()).unwrap_err().detail.contains('①'), "묘비 = 옛 토큰 거부");
        assert!(matches!(acquire_or_delegate(&d, "rotate", None, None).unwrap(), Participation::Owner(_)));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★1R B6 뮤테이션 ⓐ: 인자 토큰 ≠ env 토큰(또는 env 없음) = 거부.
    #[test]
    fn b6_arg_must_equal_env() {
        let d = tmp("b6a");
        let g = acquire(&d, "runner").unwrap();
        let tok = g.token();
        let other = Token { epoch: tok.epoch + 7, ..tok.clone() };
        assert!(verify_delegated(&d, &tok, Some(&other), &yes()).unwrap_err().detail.contains('⓪'));
        assert!(verify_delegated(&d, &tok, None, &yes()).unwrap_err().detail.contains('⓪'));
        drop(g);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★1R B6 뮤테이션 ⓑ: 검증 도중 소유자 기록이 바뀜(넘겨주기 경합) · 소유 pid 시작 시각 불일치(재사용) = 거부.
    #[test]
    fn b6_handover_race_and_pid_reuse_rejected() {
        let d = tmp("b6b");
        let g = acquire(&d, "runner").unwrap();
        let tok = g.token();
        let dd = d.clone();
        // 조상 판정(①과 ② 사이) 중에 새 소유자가 기록을 바꾼 상황
        let swap = move |_| {
            let mut o = read_owner(&dd).unwrap();
            o.txn_id = "b".repeat(32);
            o.epoch += 1;
            std::fs::write(dd.join(OWNER_FILE), serde_json::to_vec(&o).unwrap()).unwrap();
            Some(true)
        };
        let racy = ProcProbe { is_ancestor: &swap, start_time: &|p| pid_start_time(p) };
        assert!(verify_delegated(&d, &tok, Some(&tok), &racy).unwrap_err().detail.contains("①′"));
        drop(g);
        let g = acquire(&d, "runner").unwrap();
        let tok = g.token();
        let reused = ProcProbe { is_ancestor: &|_| Some(true), start_time: &|_| Some(1) };
        assert!(verify_delegated(&d, &tok, Some(&tok), &reused).unwrap_err().detail.contains("③′"));
        drop(g);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★1R MAJOR(M3) 뮤테이션: 갱신 폴더 0700 · 잠금·소유자 파일 0600(유닉스).
    #[cfg(unix)]
    #[test]
    fn m3_private_permissions() {
        use std::os::unix::fs::PermissionsExt;
        let d = tmp("m3");
        std::fs::create_dir_all(&d).unwrap();
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o755)).unwrap();
        let g = acquire(&d, "runner").unwrap();
        let mode = |p: &Path| std::fs::metadata(p).unwrap().permissions().mode() & 0o777;
        assert_eq!(mode(&d), 0o700, "넓은 폴더 권한은 좁힌다");
        assert_eq!(mode(&d.join(LOCK_FILE)), 0o600);
        assert_eq!(mode(&d.join(OWNER_FILE)), 0o600);
        drop(g);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★2R B6/H⑥ 뮤테이션 B6g: 위임 자식의 guard 가 살아 있는 동안 부모가 죽어(잠금 풀림 · 묘비) 새 트랜잭션이 와도 `txn_busy` ·
    /// 거절된 새 시도는 직전 소유자 기록을 되돌린다 · guard drop 뒤에는 연다 · 자식은 한 번에 하나.
    /// ★3판(Fable 2R N1): 같은 트랜잭션 안 중첩 위임(러너 → rotate(자식 잠금 쥠) → init-pack) = 재진입 통과 · 깊이 없는 둘째 형제 = 여전히 busy ·
    /// 중첩이어도 토큰 불일치·조상 아님은 거부.
    #[test]
    fn nested_delegation_reenters_child_lock_but_siblings_still_exclude() {
        let d = tmp("nested");
        let parent = acquire(&d, "runner").unwrap();
        let tok = parent.token();
        let rotate = verify_delegated(&d, &tok, Some(&tok), &yes()).unwrap();
        assert!(verify_delegated(&d, &tok, Some(&tok), &yes()).is_err(), "깊이 0 형제 = 자식 잠금 busy");
        let init_pack = verify_delegated_at(&d, &tok, Some(&tok), &yes(), 1).expect("깊이 1 = 재진입");
        let bad = Token { epoch: tok.epoch + 1, ..tok.clone() };
        assert!(verify_delegated_at(&d, &bad, Some(&bad), &yes(), 2).is_err(), "중첩이어도 토큰 검증");
        let no = ProcProbe { is_ancestor: &|_| Some(false), start_time: &|p| pid_start_time(p) };
        assert!(verify_delegated_at(&d, &tok, Some(&tok), &no, 2).is_err(), "중첩이어도 조상 검증");
        drop((init_pack, rotate, parent));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★4판(codex 3R m1): 참가 fail-open 범위 — 폴더가 없고 만들 수도 없음 = Ok(None)(평소대로) · 이미 있는데 소유자 전용으로 고칠 수 없음
    /// (맥 = 불변 플래그로 chmod 실패를 재현 · 실기기 = 다른 소유자·DACL) = Err(rc 26). 뮤턴트 U2-PRIVDIR.
    #[cfg(target_os = "macos")]
    #[test]
    fn participate_refuses_existing_dir_with_wrong_mode_but_passes_uncreatable() {
        use std::os::unix::fs::PermissionsExt;
        let d = tmp("privdir");
        std::fs::create_dir_all(&d).unwrap();
        std::fs::set_permissions(&d, std::fs::Permissions::from_mode(0o755)).unwrap();
        let c = std::ffi::CString::new(d.to_string_lossy().as_bytes()).unwrap();
        // SAFETY: 널종단 경로 · 플래그만 바꾼다(끝에 되돌림).
        assert_eq!(unsafe { libc::chflags(c.as_ptr(), libc::UF_IMMUTABLE as _) }, 0);
        let r = participate(&d, "pack-plan", None, None);
        assert_eq!(unsafe { libc::chflags(c.as_ptr(), 0) }, 0);
        assert!(r.is_err(), "기존 폴더 권한 고칠 수 없음 = 거부(조용한 fail-open 0)");
        let ro = tmp("privdir-ro");
        std::fs::create_dir_all(&ro).unwrap();
        std::fs::set_permissions(&ro, std::fs::Permissions::from_mode(0o500)).unwrap();
        assert!(matches!(participate(&ro.join("sub"), "pack-plan", None, None), Ok(None)), "만들 수 없음 = 평소대로");
        std::fs::set_permissions(&ro, std::fs::Permissions::from_mode(0o700)).unwrap();
        let _ = std::fs::remove_dir_all(&d);
        let _ = std::fs::remove_dir_all(&ro);
    }

    /// ★4판(codex 3R MINOR 승격): 같은 rotate 자손이 중첩 명령 둘을 동시에 띄우면 — 깊이 1 형제 둘 중 하나는 busy · 놓으면 다음이
    /// 들어온다 · 깊이 2 는 깊이 1 과 별개 · 손자가 깊이 잠금을 쥔 동안 부모 위임 자식이 죽어도 새 러너 acquire = 거부. 뮤턴트 U2-NESTSIB.
    #[test]
    fn nested_siblings_at_same_depth_exclude_each_other() {
        let d = tmp("nestsib");
        let parent = acquire(&d, "runner").unwrap();
        let tok = parent.token();
        let rotate = verify_delegated(&d, &tok, Some(&tok), &yes()).unwrap();
        let a = verify_delegated_at(&d, &tok, Some(&tok), &yes(), 1).expect("깊이 1 첫째");
        let e = verify_delegated_at(&d, &tok, Some(&tok), &yes(), 1).unwrap_err();
        assert!(e.detail.contains("같은 깊이"), "깊이 1 형제 = busy: {}", e.detail);
        let deeper = verify_delegated_at(&d, &tok, Some(&tok), &yes(), 2).expect("깊이 2 = 별개 잠금");
        assert!(verify_delegated_at(&d, &tok, Some(&tok), &yes(), MAX_NEST + 1).is_err(), "깊이 상한");
        drop(deeper);
        drop(a);
        let b = verify_delegated_at(&d, &tok, Some(&tok), &yes(), 1).expect("첫째가 놓으면 형제 진입");
        drop(rotate);
        drop(parent);
        let e = acquire(&d, "other").unwrap_err();
        assert!(e.detail.contains("txn.child.lock.1"), "손자 생존 = 새 트랜잭션 거부: {}", e.detail);
        drop(b);
        assert!(acquire(&d, "other").is_ok());
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn b6g_delegated_guard_holds_generation_after_parent_death() {
        let d = tmp("b6g");
        let parent = acquire(&d, "runner").unwrap();
        let tok = parent.token();
        let child = verify_delegated(&d, &tok, Some(&tok), &yes()).unwrap();
        assert_eq!(child.owner.epoch, tok.epoch);
        assert!(verify_delegated(&d, &tok, Some(&tok), &yes()).unwrap_err().detail.contains("자식 잠금"), "둘째 자식");
        drop(parent); // 부모 사망 = txn.lock 풀림
        assert_eq!(is_held(&d), Some(false));
        let before = std::fs::read(d.join(OWNER_FILE)).unwrap();
        let e = acquire(&d, "other").unwrap_err();
        assert!(e.detail.contains("위임 자식"), "{}", e.detail);
        assert_eq!(std::fs::read(d.join(OWNER_FILE)).unwrap(), before, "거절 = 직전 소유자 기록 복원");
        assert_eq!(is_held(&d), Some(false), "거절 = txn.lock 도 놓음");
        drop(child);
        let g = acquire(&d, "other").unwrap();
        assert_eq!(g.owner.epoch, tok.epoch + 1);
        // 검증 실패한 자식은 자식 잠금을 남기지 않는다
        assert!(verify_delegated(&d, &tok, Some(&tok), &yes()).is_err());
        let tok2 = g.token();
        assert!(verify_delegated(&d, &tok2, Some(&tok2), &yes()).is_ok());
        drop(g);
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★3R F4: 자식 잠금 파일이 넓은 권한(열기 거절)이어도 새 소유자 기록을 남기지 않는다(직전 기록 복원 · 잠금 놓음).
    #[cfg(unix)]
    #[test]
    fn f4_child_lock_open_failure_restores_owner() {
        use std::os::unix::fs::PermissionsExt;
        let d = tmp("f4");
        drop(acquire(&d, "runner").unwrap());
        let before = std::fs::read(d.join(OWNER_FILE)).unwrap();
        std::fs::set_permissions(d.join(CHILD_LOCK_FILE), std::fs::Permissions::from_mode(0o644)).unwrap();
        let e = acquire(&d, "other").unwrap_err();
        assert!(e.detail.contains("자식 잠금 파일"), "{}", e.detail);
        assert_eq!(std::fs::read(d.join(OWNER_FILE)).unwrap(), before, "직전 기록 복원");
        assert_eq!(is_held(&d), Some(false));
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★2R M3: 이미 있던 잠금 파일이 넓은 권한이면 판정 불가(txn_busy) — 열 때 0600 으로 만든 것만이 아니라 기존 파일도 재검증.
    #[cfg(unix)]
    #[test]
    fn m3_existing_wide_lock_file_rejected() {
        use std::os::unix::fs::PermissionsExt;
        let d = tmp("m3b");
        drop(acquire(&d, "runner").unwrap());
        std::fs::set_permissions(d.join(LOCK_FILE), std::fs::Permissions::from_mode(0o644)).unwrap();
        let e = acquire(&d, "runner").unwrap_err();
        assert!(e.detail.contains("권한 불일치"), "{}", e.detail);
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn real_ancestor_check() {
        // 이 시험 프로세스의 부모(cargo 시험 러너 등)는 조상 · 자기 자신·pid 1 이 아닌 무관 pid 는 조상 아님
        let me = std::process::id();
        assert_eq!(pid_is_ancestor(me), Some(false), "자기 자신은 조상 아님");
        #[cfg(unix)]
        {
            let ppid = unsafe { libc::getppid() } as u32;
            assert_eq!(pid_is_ancestor(ppid), Some(true));
        }
    }
}
