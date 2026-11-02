//! 재시작이 새 데몬을 띄울 때 그 기동의 콜드부트 자동 복원을 팩 반영 뒤로 미루는 표식(r8-1 · TICKET=cysr-1111-rotate-no-autorestore).
//!
//! 【왜】 새 데몬의 자동 복원은 rotate ④ 와 겹친다. 윈도우는 새 좌석의 훅이 팩 안 스크립트를 여는 동안 팩 폴더 rename 이 거부돼 rc 24 로 끝났다(윈 대조 08:2x).
//! 【왜 미루는가】 건너뛰면 맨 `cys restore` 가 phoenix 를 대신하게 되는데 둘은 같은 일을 하지 않는다 — 홈 좌석 폴더 보정 · 새 대화 강등 · 재시도 · 원장이 빠진다(794 F2·F7).
//! 데몬은 표식이 풀릴 때까지 기다렸다가 평소의 phoenix 를 돈다. 재시작이 죽어도 그 데몬이 스스로 복원한다(F3).
//! 【왜 env 가 아닌가】 작업 스케줄러 · GUI · 훅의 cys 자동 기동은 재시작의 env 를 받지 못하고, 데몬이 받은 env 는 좌석 셸까지 상속된다.
//! 표식은 데몬 상태 폴더에 있어 어떤 길로 뜬 데몬이든 본다.
//! 【fail-open】 건 쪽이 죽었거나 상한이 지나면 없는 것으로 친다 — 표식이 복원을 영영 막으면 안 된다([`crate::factory_reset::reset_in_progress`] 와 같은 형태).

use std::path::{Path, PathBuf};

/// 건 쪽이 살아 있어도 이만큼 지나면 푼다 — 멈춘 재시작이 좌석을 영영 막지 않게 한다. 편성의 `RESTORE_STALE_S` · 초기화 센티널과 같은 값이다.
/// 건 쪽이 죽으면 이 시간과 무관하게 바로 풀린다. 갱신 스레드로 짧은 값을 미는 방식은 재시작이 멈춰도 스레드가 살아 있어 fail-open 을 깬다.
pub const HOLD_MAX_SECS: u64 = 900;

fn hold_path(socket: &Path) -> PathBuf {
    crate::daemon_state_dir(socket).join("autorestore-hold")
}

fn now_unix() -> u64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_or(0, |d| d.as_secs())
}

fn parse(body: &str) -> (u64, u32) {
    let mut it = body.split_whitespace();
    let ts = it.next().and_then(|v| v.parse().ok()).unwrap_or(0);
    let pid = it.next().and_then(|v| v.parse().ok()).unwrap_or(0);
    (ts, pid)
}

/// 살아 있는 동안 데몬의 자동 복원을 미룬다. 놓이면(어느 return 이든) 표식이 지워지고 데몬이 복원을 시작한다.
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
        // 앱과 CLI 가 겹쳐 남이 다시 건 표식은 지우지 않는다.
        if std::fs::read_to_string(&self.0).is_ok_and(|b| parse(&b).1 == std::process::id()) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
}

/// 이 소켓의 데몬이 지금 자동 복원을 미뤄야 하는가.
pub fn held(socket: &Path) -> bool {
    held_with(socket, now_unix(), &|pid| crate::factory_reset::pid_alive(pid) && crate::factory_reset::pid_is_cys_family(pid))
}

/// [`held`] 의 판정자 주입판. 파일 없음 · 형식 불량 · 상한 초과(시계가 되돌아간 미래 시각 포함) · 건 쪽 사망 = false(잔재는 지운다).
fn held_with(socket: &Path, now: u64, owner_alive: &dyn Fn(u32) -> bool) -> bool {
    let p = hold_path(socket);
    let Ok(body) = std::fs::read_to_string(&p) else {
        return false;
    };
    let (ts, pid) = parse(&body);
    if ts > 0 && now.abs_diff(ts) < HOLD_MAX_SECS && owner_alive(pid) {
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
        assert!(!held_with(&b, now_unix(), &|_| true), "다른 데몬은 미루지 않는다");
    }

    #[test]
    fn hold_outlasts_a_slow_pack_step_while_its_owner_lives() {
        let s = sock("slow");
        let _h = RestoreHold::arm(&s).unwrap();
        assert!(held_with(&s, now_unix() + HOLD_MAX_SECS - 1, &|_| true), "④ 가 길어도 풀리지 않는다");
    }

    #[test]
    fn hold_limit_is_pinned() {
        assert_eq!(HOLD_MAX_SECS, 900, "javis_formation.RESTORE_STALE_S 와 같은 값이다");
    }

    #[test]
    fn expired_hold_opens_and_is_removed() {
        let s = sock("ttl");
        let h = RestoreHold::arm(&s).unwrap();
        assert!(!held_with(&s, now_unix() + HOLD_MAX_SECS, &|_| true));
        assert!(!hold_path(&s).exists(), "잔재를 지운다");
        std::mem::forget(h);
    }

    #[test]
    fn hold_from_the_future_opens() {
        let s = sock("future");
        std::fs::write(hold_path(&s), format!("{} 1", now_unix() + HOLD_MAX_SECS)).unwrap();
        assert!(!held_with(&s, now_unix(), &|_| true), "시계가 되돌아간 뒤의 표식");
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

    /// pid 가 재사용돼 무관한 프로세스가 살아 있어도 표식은 무효다 — 이 시험 실행 파일의 이름은 cys 계열이 아니다.
    #[test]
    fn real_judge_refuses_a_live_unrelated_process() {
        let s = sock("other");
        std::fs::write(hold_path(&s), format!("{} {}", now_unix(), std::process::id())).unwrap();
        assert!(!held(&s));
    }

    #[test]
    fn drop_leaves_a_hold_someone_else_armed() {
        let s = sock("other-owner");
        let h = RestoreHold::arm(&s).unwrap();
        std::fs::write(hold_path(&s), format!("{} 1", now_unix())).unwrap();
        drop(h);
        assert!(hold_path(&s).exists(), "남의 표식을 지우지 않는다");
    }
}
