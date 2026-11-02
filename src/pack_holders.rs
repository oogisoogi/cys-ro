//! rotate ④ 직전 팩 홀더 정리(TICKET=cysr-1111-r9-fix · master#310d3d5b F1).
//!
//! 윈 r9 rotate 2회차 rc 24: 「① 저장 확인 4/4」 뒤 ④ 가 팩 폴더 rename 재시도(5초)를 넘겼다. Restart Manager 로 본 홀더는
//! **옛 좌석의 훅 bash**(save-state.sh · role-capability-gate.sh …)였다 — ② 에서 데몬이 죽은 뒤에도 남아 팩 파일을 쥐었다.
//! 그래서 ④ 직전에 팩 파일을 쥔 프로세스 중 **② 가 내린 옛 데몬의 자손**만 골라 상한까지 끝나기를 기다리고, 넘으면 그것만 끝낸다.
//! 그 밖의 홀더(사용자 앱 · 백신 · 다른 데몬)는 건드리지 않고 기록만 한다. 자손 판정은 (pid, 시작 시각) 쌍이라 pid 재사용에 걸리지 않고,
//! 끝내기 직전에 시작 시각을 다시 대조한다. 맥·리눅스는 rename 이 열린 파일에 막히지 않아 이 경로를 타지 않는다.
//! ★전제: 사용자·다른 프로세스를 죽이지 않는다 — 판정이 애매하면 남으로 본다(기다리지도 끝내지도 않고 기록만 · 막히면 종전처럼 rc 24).

use std::collections::HashSet;
use std::time::Duration;

/// 프로세스 한 줄 — `start` 는 생성 시각(윈 FILETIME 100ns 단위). pid 만으로는 재사용된 남을 우리 것으로 볼 수 있다.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Proc {
    pub pid: u32,
    pub parent: u32,
    pub start: u64,
}

/// ② 직전에 찍은 옛 데몬 트리 — 데몬이 죽은 뒤에는 부모 고리를 다시 볼 수 없어 미리 찍어 둔다.
#[derive(Clone, Debug, Default)]
pub struct OldTree {
    /// 옛 데몬과 그 자손의 (pid, 시작 시각).
    pub tree: HashSet<(u32, u64)>,
    /// 찍은 순간의 전체 표 — `tree` 를 고른 근거(로그·시험용). 위로 걷기에는 쓰지 않는다([`is_ours`] doc).
    pub snapshot: Vec<Proc>,
}

/// 홀더 대기 상한 — 넘으면 옛 트리 자손만 끝낸다.
pub const HOLDER_WAIT: Duration = Duration::from_secs(10);
/// ④ 재시도 간격(지수 백오프). 시도는 이 길이 + 1회 · 대기 합 14초 · 시도마다 홀더 대기(최대 [`HOLDER_WAIT`]) 와
/// init-pack 자체의 rename 재시도(5초)가 더해진다 — 총 상한 ≈ 14 + 10 + 4×(5 + init-pack 실행) 초.
pub const PACK_RETRY_BACKOFF: [Duration; 3] = [Duration::from_secs(2), Duration::from_secs(4), Duration::from_secs(8)];

/// `root` 와 그 자손(순수) — 자식의 시작 시각이 부모보다 늦을 때만 잇는다(죽은 부모의 pid 를 재사용한 남을 끌어오지 않는다).
pub fn descendants(snapshot: &[Proc], root: u32) -> HashSet<(u32, u64)> {
    let mut out = HashSet::new();
    let Some(r) = snapshot.iter().find(|p| p.pid == root) else {
        return out;
    };
    let mut todo = vec![*r];
    out.insert((r.pid, r.start));
    while let Some(cur) = todo.pop() {
        for c in snapshot {
            if c.parent == cur.pid && c.pid != cur.pid && c.start >= cur.start && out.insert((c.pid, c.start)) {
                todo.push(*c);
            }
        }
    }
    out
}

/// 홀더가 옛 트리 자손인가(순수) — 홀더에서 위로 올라가며 옛 트리의 (pid, 시작 시각)을 만나면 참.
/// 고리는 **지금 표(`now`)에서만** 잇는다 — 부모가 이미 죽었으면 그 pid 를 옛 표에서 찾지 않는다. 옛 표의 같은 pid 주인이 진짜 부모였다는
/// 증거가 없다: ② 에서 옛 좌석이 한꺼번에 죽어 pid 가 풀리면 그 pid 를 받아 곧 끝난 중간 프로세스(identify · 부서 훅 bash)의 자식, 곧 새 cysd·
/// 부서 훅 손자가 옛 트리로 잡힌다(r9 fix D1 · 799 H1·H1b). 잃는 것은 「부모가 죽은 옛 훅의 손자」뿐이고 그것은 남으로 기록만 된다.
/// 지금 표에서 부모는 자식보다 먼저 태어났어야 한다 — 늦게 태어난 같은 pid 주인은 진짜 부모가 죽은 뒤 그 pid 를 받은 남이다.
pub fn is_ours(holder: (u32, u64), now: &[Proc], old: &OldTree) -> bool {
    let mut cur = holder;
    for _ in 0..64 {
        if old.tree.contains(&cur) {
            return true;
        }
        let Some(me) = now.iter().find(|p| p.pid == cur.0 && p.start == cur.1) else {
            return false;
        };
        let Some(p) = now.iter().find(|p| p.pid == me.parent && p.pid != me.pid && p.start <= me.start) else {
            return false;
        };
        cur = (p.pid, p.start);
    }
    false
}

/// 정리 결과 — 로그·시험용.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Sweep {
    /// 상한 안에 스스로 끝난 옛 트리 홀더 수.
    pub exited: usize,
    /// 상한을 넘겨 끝낸 옛 트리 홀더 pid.
    pub killed: Vec<u32>,
    /// 끝내기에 실패해 남은 옛 트리 홀더 pid.
    pub left: Vec<u32>,
}

/// 옛 트리 홀더가 끝나기를 `wait` 까지 기다리고, 넘으면 그것만 끝낸다(순수 · 효과 주입).
/// `ours` = 지금 팩 파일을 쥔 옛 트리 자손 · `kill` = 시작 시각을 다시 대조하고 끝냈는가 · `sleep` = 한 번 쉰다.
pub fn settle(
    mut ours: impl FnMut() -> Vec<(u32, u64)>,
    mut kill: impl FnMut((u32, u64)) -> bool,
    mut sleep: impl FnMut(Duration),
    wait: Duration,
    step: Duration,
) -> Sweep {
    let first = ours();
    if first.is_empty() {
        return Sweep::default();
    }
    let mut waited = Duration::ZERO;
    let mut now = first.clone();
    while !now.is_empty() && waited < wait {
        sleep(step);
        waited += step;
        now = ours();
    }
    let mut sweep = Sweep { exited: first.iter().filter(|h| !now.contains(h)).count(), ..Sweep::default() };
    for h in now {
        if kill(h) {
            sweep.killed.push(h.0);
        } else {
            sweep.left.push(h.0);
        }
    }
    sweep
}

/// ④ 를 지수 백오프로 다시 한다(순수 · 효과 주입). 시도마다 앞서 `before` 로 홀더를 정리한다. 반환 = (성공, 시도 수).
pub fn retry_with_backoff(
    mut before: impl FnMut(usize),
    mut attempt: impl FnMut(usize) -> bool,
    mut sleep: impl FnMut(Duration),
    backoff: &[Duration],
) -> (bool, usize) {
    for n in 0..=backoff.len() {
        before(n);
        if attempt(n) {
            return (true, n + 1);
        }
        if let Some(b) = backoff.get(n) {
            sleep(*b);
        }
    }
    (false, backoff.len() + 1)
}

/// ② 직전 옛 데몬 트리를 찍는다. 윈 밖은 빈 트리(쓰지 않는다).
pub fn capture(daemon_pid: u32) -> OldTree {
    #[cfg(windows)]
    {
        let snapshot = win::snapshot();
        let tree = descendants(&snapshot, daemon_pid);
        OldTree { tree, snapshot }
    }
    #[cfg(not(windows))]
    {
        let _ = daemon_pid;
        OldTree::default()
    }
}

/// ④ 직전 정리 — 팩 파일 홀더 중 옛 트리 자손만 기다렸다 끝낸다. 남의 홀더는 (pid, 이름)으로 돌려준다(건드리지 않음).
#[cfg(windows)]
pub fn clear_for_swap(dir: &std::path::Path, old: &OldTree) -> (Sweep, Vec<(u32, String)>) {
    if old.tree.is_empty() {
        return (Sweep::default(), Vec::new());
    }
    let files = win::files_under(dir);
    let others = std::cell::RefCell::new(Vec::new());
    let ours = || {
        let Ok(holders) = win::holders(&files) else {
            return Vec::new();
        };
        let now = win::snapshot();
        let mut mine = Vec::new();
        let mut rest = Vec::new();
        for (pid, start, name) in holders {
            if is_ours((pid, start), &now, old) {
                mine.push((pid, start));
            } else {
                rest.push((pid, name));
            }
        }
        *others.borrow_mut() = rest;
        mine
    };
    let sweep = settle(ours, win::terminate, std::thread::sleep, HOLDER_WAIT, Duration::from_millis(500));
    let others = others.into_inner();
    (sweep, others)
}

#[cfg(windows)]
mod win {
    use super::Proc;
    use std::os::windows::ffi::OsStrExt;
    use std::path::{Path, PathBuf};
    use windows_sys::Win32::Foundation::{CloseHandle, ERROR_MORE_DATA, FILETIME, INVALID_HANDLE_VALUE};
    use windows_sys::Win32::System::Diagnostics::ToolHelp::{
        CreateToolhelp32Snapshot, Process32FirstW, Process32NextW, PROCESSENTRY32W, TH32CS_SNAPPROCESS,
    };
    use windows_sys::Win32::System::RestartManager::{
        RmEndSession, RmGetList, RmRegisterResources, RmStartSession, CCH_RM_SESSION_KEY, RM_PROCESS_INFO,
    };
    use windows_sys::Win32::System::SystemInformation::GetSystemTimeAsFileTime;
    use windows_sys::Win32::System::Threading::{
        GetProcessTimes, OpenProcess, TerminateProcess, WaitForSingleObject, PROCESS_QUERY_LIMITED_INFORMATION,
        PROCESS_SYNCHRONIZE, PROCESS_TERMINATE,
    };

    fn ft(t: FILETIME) -> u64 {
        ((t.dwHighDateTime as u64) << 32) | t.dwLowDateTime as u64
    }

    fn start_of(pid: u32) -> Option<u64> {
        unsafe {
            let h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid);
            if h.is_null() {
                return None;
            }
            let (mut c, mut e, mut k, mut u) = (std::mem::zeroed(), std::mem::zeroed(), std::mem::zeroed(), std::mem::zeroed());
            let ok = GetProcessTimes(h, &mut c, &mut e, &mut k, &mut u) != 0;
            CloseHandle(h);
            ok.then(|| ft(c))
        }
    }

    /// 전체 프로세스 표 — 시작 시각을 못 읽는 것(시스템·권한 밖)은 뺀다(우리 자손이 아니다).
    /// 시작 시각은 표를 찍은 뒤 pid 마다 읽는다 — 그 사이 pid 가 죽고 재사용되면 「옛 부모 + 새 시작 시각」이 섞인다(r9 fix D1 · codex F1-2).
    /// 표에 든 프로세스는 표보다 먼저 태어났으니 찍기 전 시각(`t0`) 이후에 태어난 줄은 버린다. `t0` 는 거친 시계라 같은 틱에 태어난 줄도
    /// 버려진다 — 남으로 보는 쪽이라 안전하고, 홀더 표본은 500ms 마다 다시 찍는다.
    pub fn snapshot() -> Vec<Proc> {
        let mut out = Vec::new();
        unsafe {
            let mut t0: FILETIME = std::mem::zeroed();
            GetSystemTimeAsFileTime(&mut t0);
            let t0 = ft(t0);
            let snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
            if snap == INVALID_HANDLE_VALUE {
                return out;
            }
            let mut e: PROCESSENTRY32W = std::mem::zeroed();
            e.dwSize = std::mem::size_of::<PROCESSENTRY32W>() as u32;
            let mut more = Process32FirstW(snap, &mut e) != 0;
            while more {
                if let Some(start) = start_of(e.th32ProcessID).filter(|&s| s < t0) {
                    out.push(Proc { pid: e.th32ProcessID, parent: e.th32ParentProcessID, start });
                }
                more = Process32NextW(snap, &mut e) != 0;
            }
            CloseHandle(snap);
        }
        out
    }

    pub fn files_under(dir: &Path) -> Vec<PathBuf> {
        let mut out = Vec::new();
        let mut todo = vec![dir.to_path_buf()];
        while let Some(d) = todo.pop() {
            let Ok(rd) = std::fs::read_dir(&d) else { continue };
            for e in rd.flatten() {
                match e.file_type() {
                    Ok(t) if t.is_dir() => todo.push(e.path()),
                    Ok(t) if t.is_file() => out.push(e.path()),
                    _ => {}
                }
            }
        }
        out
    }

    /// Restart Manager 로 본 파일 홀더 (pid, 시작 시각, 이름).
    pub fn holders(files: &[PathBuf]) -> Result<Vec<(u32, u64, String)>, u32> {
        let wide: Vec<Vec<u16>> =
            files.iter().map(|p| p.as_os_str().encode_wide().chain(std::iter::once(0)).collect()).collect();
        let ptrs: Vec<*const u16> = wide.iter().map(|w| w.as_ptr()).collect();
        unsafe {
            let mut session = 0u32;
            let mut key = [0u16; CCH_RM_SESSION_KEY as usize + 1];
            let rc = RmStartSession(&mut session, 0, key.as_mut_ptr());
            if rc != 0 {
                return Err(rc);
            }
            let result = (|| {
                for chunk in ptrs.chunks(256) {
                    let rc = RmRegisterResources(session, chunk.len() as u32, chunk.as_ptr(), 0, std::ptr::null(), 0, std::ptr::null());
                    if rc != 0 {
                        return Err(rc);
                    }
                }
                let mut infos: Vec<RM_PROCESS_INFO> = Vec::new();
                for _ in 0..4 {
                    let (mut needed, mut have, mut reasons) = (0u32, infos.len() as u32, 0u32);
                    let rc = RmGetList(session, &mut needed, &mut have, infos.as_mut_ptr(), &mut reasons);
                    if rc == 0 {
                        infos.truncate(have as usize);
                        return Ok(infos
                            .iter()
                            .map(|i| {
                                let n = i.strAppName.iter().position(|&c| c == 0).unwrap_or(i.strAppName.len());
                                (i.Process.dwProcessId, ft(i.Process.ProcessStartTime), String::from_utf16_lossy(&i.strAppName[..n]))
                            })
                            .collect());
                    }
                    if rc != ERROR_MORE_DATA {
                        return Err(rc);
                    }
                    infos = vec![std::mem::zeroed(); needed as usize + 4];
                }
                Err(ERROR_MORE_DATA)
            })();
            RmEndSession(session);
            result
        }
    }

    /// 시작 시각을 다시 대조한 뒤에만 끝낸다(그 사이 pid 가 재사용됐으면 남이다).
    pub fn terminate((pid, start): (u32, u64)) -> bool {
        unsafe {
            let h = OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_SYNCHRONIZE, 0, pid);
            if h.is_null() {
                return start_of(pid) != Some(start); // 이미 끝났으면 끝낸 것과 같다
            }
            let (mut c, mut e, mut k, mut u) = (std::mem::zeroed(), std::mem::zeroed(), std::mem::zeroed(), std::mem::zeroed());
            let same = GetProcessTimes(h, &mut c, &mut e, &mut k, &mut u) != 0 && ft(c) == start;
            let done = same && TerminateProcess(h, 1) != 0 && WaitForSingleObject(h, 3000) == 0;
            CloseHandle(h);
            done
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::{Cell, RefCell};

    fn p(pid: u32, parent: u32, start: u64) -> Proc {
        Proc { pid, parent, start }
    }

    /// 옛 데몬 10 → 좌석 claude 20 → 훅 bash 30 · 남의 프로세스 40(부모 1) · 데몬이 띄운 크롬 50(Job 밖 · 자손이긴 하다).
    fn old() -> OldTree {
        let snap = vec![p(1, 0, 1), p(10, 1, 100), p(20, 10, 200), p(30, 20, 300), p(40, 1, 150), p(50, 10, 250)];
        OldTree { tree: descendants(&snap, 10), snapshot: snap }
    }

    #[test]
    fn descendants_follow_birth_order_and_skip_reused_pids() {
        let snap = vec![p(10, 1, 100), p(20, 10, 200), p(30, 20, 300), p(31, 20, 150), p(40, 1, 50)];
        let t = descendants(&snap, 10);
        assert!(t.contains(&(10, 100)) && t.contains(&(20, 200)) && t.contains(&(30, 300)));
        assert!(!t.contains(&(31, 150)), "부모(20)보다 먼저 태어난 31 = 재사용된 부모 pid 의 남이다");
        assert!(!t.contains(&(40, 50)));
        assert!(descendants(&snap, 99).is_empty());
    }

    #[test]
    fn a_holder_is_ours_only_through_the_old_tree() {
        let o = old();
        // 데몬·좌석이 죽은 뒤: 지금 표에는 훅 30 과 그 자식 60, 남 40 만 있다.
        let now = vec![p(30, 20, 300), p(60, 30, 400), p(40, 1, 150)];
        assert!(is_ours((30, 300), &now, &o), "옛 좌석의 훅 bash");
        assert!(is_ours((60, 400), &now, &o), "데몬이 죽은 뒤 고아 훅이 띄운 자식");
        assert!(!is_ours((40, 150), &now, &o), "옛 트리 밖");
        // 같은 pid 30 을 새로 받은 남(시작 시각 다름).
        let reused = vec![p(30, 1, 900)];
        assert!(!is_ours((30, 900), &reused, &o), "pid 재사용");
        // 모르는 홀더.
        assert!(!is_ours((77, 5), &now, &o));
    }

    /// r9 fix D1(799 H1): ② 뒤 옛 훅 555 가 죽고 그 pid 를 받은 identify 가 새 cysd 900 을 띄우고 끝났다 — 900 의 부모 칸은 555 지만
    /// 옛 표의 555 는 진짜 부모가 아니다. 새 cysd 는 남이다.
    #[test]
    fn a_dead_parent_pid_reused_after_the_snapshot_does_not_pull_the_new_daemon_in() {
        let snap = vec![p(1, 0, 1), p(10, 1, 100), p(20, 10, 200), p(555, 20, 250), p(999, 1, 260)];
        let o = OldTree { tree: descendants(&snap, 10), snapshot: snap };
        let now = vec![p(1, 0, 1), p(999, 1, 260), p(900, 555, 5000)];
        assert!(!is_ours((900, 5000), &now, &o), "새 cysd");
        let child = vec![p(1, 0, 1), p(900, 555, 5000), p(901, 900, 5100)];
        assert!(!is_ours((901, 5100), &child, &o), "새 cysd 의 자손");
    }

    /// r9 fix D1(799 H1b): 부서 좌석 claude 71(옛 트리 밖)이 띄운 중간 bash 가 옛 훅의 pid 556 을 받아 손자 800 을 띄우고 끝났다.
    #[test]
    fn a_dept_hook_grandchild_under_a_reused_pid_is_not_ours() {
        let snap = vec![p(1, 0, 1), p(10, 1, 100), p(20, 10, 200), p(556, 20, 260), p(70, 1, 50), p(71, 70, 60)];
        let o = OldTree { tree: descendants(&snap, 10), snapshot: snap };
        assert!(o.tree.contains(&(556, 260)));
        let now = vec![p(1, 0, 1), p(70, 1, 50), p(71, 70, 60), p(800, 556, 6000)];
        assert!(!is_ours((800, 6000), &now, &o), "부서 훅 손자");
    }

    /// 지금 표의 부모 칸 pid 주인이 홀더보다 늦게 태어났으면 그 주인은 부모가 아니다(진짜 부모가 죽은 뒤 pid 를 받은 남).
    /// 여기서는 그 늦은 주인이 하필 옛 훅 30 이다 — 시작 시각 대조가 없으면 남의 홀더 70 을 끝낸다.
    #[test]
    fn a_parent_born_after_the_holder_is_not_its_parent() {
        let o = old();
        let now = vec![p(30, 20, 300), p(70, 30, 120)];
        assert!(!is_ours((70, 120), &now, &o));
    }

    /// 홀더는 Restart Manager 가 본 (pid, 시작 시각) 그대로 찾는다 — 그 사이 pid 가 재사용돼 지금 표의 같은 pid 가 옛 훅의 자식이어도
    /// 쥐고 있던 프로세스는 그것이 아니다.
    #[test]
    fn a_holder_is_matched_by_its_own_start_time() {
        let o = old();
        let now = vec![p(30, 20, 300), p(60, 30, 400)];
        assert!(!is_ours((60, 10), &now, &o), "pid 60 의 지금 주인은 옛 훅 자식이지만 쥔 것은 시작 시각 10 의 남");
        assert!(is_ours((60, 400), &now, &o));
    }

    #[test]
    fn settle_waits_and_kills_nothing_when_holders_exit_in_time() {
        let left = Cell::new(3u32);
        let killed = RefCell::new(Vec::new());
        let s = settle(
            || {
                left.set(left.get().saturating_sub(1));
                if left.get() > 0 { vec![(30, 300)] } else { vec![] }
            },
            |h| {
                killed.borrow_mut().push(h);
                true
            },
            |_| {},
            Duration::from_secs(10),
            Duration::from_millis(500),
        );
        assert_eq!(s, Sweep { exited: 1, killed: vec![], left: vec![] });
        assert!(killed.borrow().is_empty(), "상한 안에 끝나면 아무것도 끝내지 않는다");
    }

    #[test]
    fn settle_kills_only_the_stuck_holders_after_the_wait() {
        let slept = Cell::new(Duration::ZERO);
        let killed = RefCell::new(Vec::new());
        let s = settle(
            || vec![(30, 300), (60, 400)],
            |h| {
                killed.borrow_mut().push(h);
                h.0 == 30
            },
            |d| slept.set(slept.get() + d),
            Duration::from_secs(10),
            Duration::from_millis(500),
        );
        assert_eq!(slept.get(), Duration::from_secs(10), "상한까지 기다린 뒤에만");
        assert_eq!(*killed.borrow(), vec![(30, 300), (60, 400)]);
        assert_eq!(s, Sweep { exited: 0, killed: vec![30], left: vec![60] });
        // 홀더가 없으면 기다리지도 끝내지도 않는다.
        let calls = Cell::new(0);
        let none = settle(|| vec![], |_| true, |_| calls.set(calls.get() + 1), HOLDER_WAIT, Duration::from_millis(500));
        assert_eq!((none, calls.get()), (Sweep::default(), 0));
    }

    #[test]
    fn retry_backs_off_and_stops_at_the_limit() {
        let slept = RefCell::new(Vec::new());
        let before = RefCell::new(Vec::new());
        let r = retry_with_backoff(|n| before.borrow_mut().push(n), |n| n == 2, |d| slept.borrow_mut().push(d), &PACK_RETRY_BACKOFF);
        assert_eq!(r, (true, 3));
        assert_eq!(*before.borrow(), vec![0, 1, 2], "시도마다 앞서 홀더를 정리한다");
        assert_eq!(*slept.borrow(), vec![Duration::from_secs(2), Duration::from_secs(4)]);
        slept.borrow_mut().clear();
        let r = retry_with_backoff(|_| {}, |_| false, |d| slept.borrow_mut().push(d), &PACK_RETRY_BACKOFF);
        assert_eq!(r, (false, 4));
        assert_eq!(slept.borrow().iter().sum::<Duration>(), Duration::from_secs(14), "대기 합 = 총 상한의 백오프 몫");
    }
}
