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
}

impl Owner {
    pub fn token(&self) -> Token {
        Token { txn_id: self.txn_id.clone(), epoch: self.epoch }
    }
}

/// 잡은 잠금(drop = 해제 · 소유자 기록은 남긴다 — 다음 epoch 계산 재료 · 낡음은 잠금 상태로 판별).
#[derive(Debug)]
pub struct TxnGuard {
    _file: File,
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

fn busy(d: impl Into<String>) -> UpdateErr {
    UpdateErr::new(ErrCode::TxnBusy, "lock", d)
}

fn open_lock(dir: &Path) -> Result<File, UpdateErr> {
    std::fs::create_dir_all(dir).map_err(|e| busy(format!("상태 폴더: {e}")))?;
    OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(dir.join(LOCK_FILE))
        .map_err(|e| busy(format!("잠금 파일: {e}")))
}

pub fn read_owner(dir: &Path) -> Option<Owner> {
    serde_json::from_slice(&std::fs::read(dir.join(OWNER_FILE)).ok()?).ok()
}

/// 잠금이 지금 (누군가에게) 잡혀 있는가 — 비차단 시도가 실패하면 잡혀 있다. 시도가 성공하면 즉시 놓는다.
/// `None` = 판정 불가(열기 실패 등).
pub fn is_held(dir: &Path) -> Option<bool> {
    let f = OpenOptions::new().read(true).write(true).open(dir.join(LOCK_FILE)).ok()?;
    match f.try_lock() {
        Ok(()) => {
            let _ = f.unlock();
            Some(false)
        }
        Err(TryLockError::WouldBlock) => Some(true),
        Err(TryLockError::Error(_)) => None,
    }
}

/// 잠금을 잡는다(비차단 · 잡혀 있으면 `txn_busy`). 새 `txn_id`·`epoch`(+1)를 소유자 기록에 원자 기록한다.
pub fn acquire(dir: &Path, owner: &str) -> Result<TxnGuard, UpdateErr> {
    let f = open_lock(dir)?;
    match f.try_lock() {
        Ok(()) => {}
        Err(TryLockError::WouldBlock) => {
            let who = read_owner(dir).map(|o| format!("{}(pid {})", o.owner, o.pid)).unwrap_or_else(|| "?".into());
            return Err(busy(format!("잠금 소유 중: {who}")));
        }
        Err(TryLockError::Error(e)) => return Err(busy(format!("잠금 시도: {e}"))),
    }
    let epoch = read_owner(dir).map(|o| o.epoch + 1).unwrap_or(1);
    let o = Owner {
        owner: owner.to_string(),
        pid: std::process::id(),
        txn_id: super::buildinfo::random_hex128().map_err(busy)?,
        epoch,
        started_at: super::clock::wall_now(),
        boot_id: super::clock::boot_id(),
    };
    let bytes = serde_json::to_vec_pretty(&o).map_err(|e| busy(e.to_string()))?;
    crate::pack::write_atomic(&dir.join(OWNER_FILE), &bytes).map_err(|e| busy(format!("소유자 기록: {e}")))?;
    Ok(TxnGuard { _file: f, owner: o, dir: dir.to_path_buf() })
}

/// 위임 검증 3조건(①내용 일치 ②잠금 실재 ③조상). `is_ancestor(pid)` 는 호출부가 준다(실 구현 = [`pid_is_ancestor`]).
pub fn verify_delegated(dir: &Path, token: &Token, is_ancestor: impl Fn(u32) -> Option<bool>) -> Result<Owner, UpdateErr> {
    let o = read_owner(dir).ok_or_else(|| busy("① 소유자 기록 없음"))?;
    if o.txn_id != token.txn_id || o.epoch != token.epoch {
        return Err(busy(format!("① 토큰 불일치 (epoch {} vs {})", token.epoch, o.epoch)));
    }
    match is_held(dir) {
        Some(true) => {}
        Some(false) => return Err(busy("② 잠금이 풀려 있음(낡은 토큰)")),
        None => return Err(busy("② 잠금 판정 불가")),
    }
    match is_ancestor(o.pid) {
        Some(true) => Ok(o),
        Some(false) => Err(busy(format!("③ 소유 pid {} 가 조상 아님", o.pid))),
        None => Err(busy("③ 조상 판정 불가")),
    }
}

/// 참가 결과 — 직접 소유 · 위임 받음.
#[derive(Debug)]
pub enum Participation {
    Owner(TxnGuard),
    Delegated(Owner),
}

/// 참가자 입구: 토큰이 있으면 위임 검증(재잠금 0), 없으면 잠금을 잡는다.
pub fn acquire_or_delegate(dir: &Path, owner: &str, token: Option<&str>) -> Result<Participation, UpdateErr> {
    match token {
        Some(t) => {
            let tok = Token::parse(t).ok_or_else(|| busy("토큰 형식"))?;
            verify_delegated(dir, &tok, pid_is_ancestor).map(Participation::Delegated)
        }
        None => acquire(dir, owner).map(Participation::Owner),
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

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cys-u1-lock-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        d
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

    /// §7-1 「위임 토큰 3조건(내용 불일치·잠금 없음·조상 아님 → txn_busy) · 토큰 없는 자식 = 재잠금」.
    #[test]
    fn delegation_three_conditions() {
        let d = tmp("deleg");
        let g = acquire(&d, "runner").unwrap();
        let tok = g.token();
        // 전부 맞음
        assert!(verify_delegated(&d, &tok, |_| Some(true)).is_ok());
        // ① 내용 불일치(옛 epoch · 다른 txn_id)
        let old = Token { epoch: tok.epoch - 1, ..tok.clone() };
        assert!(verify_delegated(&d, &old, |_| Some(true)).unwrap_err().detail.contains('①'));
        let other = Token { txn_id: "f".repeat(32), ..tok.clone() };
        assert!(verify_delegated(&d, &other, |_| Some(true)).unwrap_err().detail.contains('①'));
        // ③ 조상 아님 · 판정 불가
        assert!(verify_delegated(&d, &tok, |_| Some(false)).unwrap_err().detail.contains('③'));
        assert!(verify_delegated(&d, &tok, |_| None).unwrap_err().detail.contains('③'));
        // 토큰 없는 자식 = 재잠금 시도 → 잡혀 있으므로 txn_busy
        assert_eq!(acquire_or_delegate(&d, "rotate", None).unwrap_err().code, ErrCode::TxnBusy);
        // ② 잠금 풀림(소유자 죽음) — 기록은 남아도 낡은 토큰
        drop(g);
        assert!(verify_delegated(&d, &tok, |_| Some(true)).unwrap_err().detail.contains('②'));
        // 토큰 없는 호출은 이제 잡힌다
        assert!(matches!(acquire_or_delegate(&d, "rotate", None).unwrap(), Participation::Owner(_)));
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
