//! 재시작이 새 데몬을 띄울 때 그 기동의 콜드부트 자동 복원만 쉬게 하는 표식(r8-1 · TICKET=cysr-1111-r8-merge).
//!
//! 【왜】 새 데몬의 자동 복원은 rotate ④ 와 겹친다. 윈도우는 새 좌석의 훅이 팩 안 스크립트를 여는 동안 팩 폴더 rename 이 거부돼 rc 24 로 끝났다(윈 대조 08:2x).
//! 재시작은 ⑤ 에서 어차피 복원하므로 자동 복원을 쉬어도 잃는 것이 없다.
//! 【왜 env 가 아닌가】 작업 스케줄러 · GUI · 훅의 cys 자동 기동은 재시작의 env 를 받지 못하고, 데몬이 받은 env 는 좌석 셸까지 상속된다.
//! 표식은 데몬 상태 폴더에 있어 어떤 길로 뜬 데몬이든 보고, 소켓별이라 다른 데몬을 건드리지 않는다.
//! 【fail-open】 재시작이 죽었거나 시간이 지나면 없는 것으로 친다 — 표식이 자동 복원을 영영 막으면 안 된다([`crate::factory_reset::reset_in_progress`] 와 같은 형태).

use std::path::{Path, PathBuf};

/// 데몬은 표식을 건 뒤 몇 초 안에 뜬다. 이 시간은 재시작이 끊겼을 때 자동 복원이 돌아오는 상한이다.
pub const HOLD_TTL_SECS: u64 = 120;

fn hold_path(socket: &Path) -> PathBuf {
    crate::daemon_state_dir(socket).join("autorestore-hold")
}

fn now_unix() -> u64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_or(0, |d| d.as_secs())
}

/// 살아 있는 동안 자동 복원을 쉬게 한다. 놓이면(어느 return 이든) 표식이 지워진다.
#[derive(Debug)]
pub struct RestoreHold(PathBuf);

impl RestoreHold {
    /// 쓰지 못하면 None — 표식 없이 종전대로 간다(겹치면 rc 24 · 복원은 된다).
    pub fn arm(socket: &Path) -> Option<Self> {
        let p = hold_path(socket);
        if let Some(d) = p.parent() {
            let _ = std::fs::create_dir_all(d);
        }
        std::fs::write(&p, format!("{} {}", now_unix(), std::process::id())).ok()?;
        Some(Self(p))
    }
}

impl Drop for RestoreHold {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

/// 이 소켓의 데몬이 지금 자동 복원을 쉬어야 하는가 — 데몬 기동 때 한 번 묻는다.
pub fn held(socket: &Path) -> bool {
    held_with(socket, now_unix(), &|pid| crate::factory_reset::pid_alive(pid) && crate::factory_reset::pid_is_cys_family(pid))
}

/// [`held`] 의 판정자 주입판. 파일 없음 · 형식 불량 · TTL 초과 · 건 쪽 사망 = false(잔재는 지운다).
fn held_with(socket: &Path, now: u64, owner_alive: &dyn Fn(u32) -> bool) -> bool {
    let p = hold_path(socket);
    let Ok(body) = std::fs::read_to_string(&p) else {
        return false;
    };
    let mut it = body.split_whitespace();
    let ts = it.next().and_then(|v| v.parse::<u64>().ok()).unwrap_or(0);
    let pid = it.next().and_then(|v| v.parse::<u32>().ok()).unwrap_or(0);
    if ts > 0 && now.saturating_sub(ts) < HOLD_TTL_SECS && owner_alive(pid) {
        return true;
    }
    let _ = std::fs::remove_file(&p);
    false
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;

    fn sock(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cys-hold-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d.join("cysd.sock")
    }

    #[test]
    fn hold_is_seen_while_armed_and_gone_when_dropped() {
        let s = sock("arm");
        assert!(!held_with(&s, now_unix(), &|_| true), "표식 없음");
        let h = RestoreHold::arm(&s).unwrap();
        assert!(held_with(&s, now_unix(), &|p| p == std::process::id()));
        drop(h);
        assert!(!hold_path(&s).exists(), "놓이면 지워진다");
    }

    #[test]
    fn hold_is_per_socket() {
        let (a, b) = (sock("a"), sock("b"));
        let _h = RestoreHold::arm(&a).unwrap();
        assert!(!held_with(&b, now_unix(), &|_| true), "다른 데몬은 쉬지 않는다");
    }

    #[test]
    fn expired_hold_opens_and_is_removed() {
        let s = sock("ttl");
        let h = RestoreHold::arm(&s).unwrap();
        assert!(!held_with(&s, now_unix() + HOLD_TTL_SECS, &|_| true));
        assert!(!hold_path(&s).exists(), "잔재를 지운다");
        std::mem::forget(h);
    }

    #[test]
    fn hold_of_a_dead_owner_opens_and_is_removed() {
        let s = sock("dead");
        let h = RestoreHold::arm(&s).unwrap();
        assert!(!held_with(&s, now_unix(), &|_| false));
        assert!(!hold_path(&s).exists(), "잔재를 지운다");
        std::mem::forget(h);
    }

    #[test]
    fn malformed_hold_opens() {
        let s = sock("bad");
        for body in ["", "x y", "123", "0 1"] {
            std::fs::write(hold_path(&s), body).unwrap();
            assert!(!held_with(&s, now_unix(), &|_| true), "{body:?}");
        }
    }

    #[test]
    fn real_judge_sees_a_dead_pid() {
        let s = sock("real");
        std::fs::write(hold_path(&s), format!("{} 4000000", now_unix())).unwrap();
        assert!(!held(&s));
    }
}
