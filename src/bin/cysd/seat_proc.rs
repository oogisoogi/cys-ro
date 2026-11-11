//! 좌석 프로세스 손잡이(TICKET=cysr-seatkeep-t3 · 설계 = `docs/seatkeep/T3-DESIGN.md` · DESIGN.md §6 T3).
//!
//! cysd 가 좌석의 PTY 마스터·자식 프로세스에 닿는 자리를 **이 모듈 하나**로 모은다 — 생성 · 출력 읽기 · 입력 쓰기 · 크기 ·
//! 신호 · 전경 그룹 질의 · 종료 감지·회수 · 닫기. 손잡이의 얼굴은 portable-pty 의 두 트레이트(`MasterPty` · `Child`)와
//! 읽기·쓰기 스트림이다 — `Surface` 의 `master`·`child` 필드 타입은 그대로라서 그 얼굴을 부르는 곳(시험 구역 포함)은 바뀌지 않는다.
//!
//! 구현은 둘이다: **직접 PTY**(지금 동작 — 아래 코드는 옛 자리에서 논리 변경 없이 옮긴 것) / seatkeep 경유(노브 · 이 파일 뒤쪽).
//! 이 모듈 밖의 운영 코드가 PTY·자식에 직접 닿으면 `seat_proc_gate_tests` 의 grep 게이트가 붉어진다.

use portable_pty::{native_pty_system, Child, CommandBuilder, MasterPty, PtyPair, PtySize};
use std::io::{Read, Write};
use std::sync::atomic::AtomicBool;
#[cfg(unix)]
use std::sync::atomic::{AtomicI32, Ordering};
use std::sync::{Mutex, TryLockError};

/// 열린 좌석 PTY(자식 기동 전). 옛 순서(`openpty` → 명령 조립 → `spawn_command`)를 그대로 지키려고 생성을 두 단계로 나눈다.
pub(crate) struct Opened {
    pair: PtyPair,
}

/// 기동된 좌석 — 손잡이의 얼굴들. `take_io` 로 읽기·쓰기를 꺼낸 뒤 `master`·`child` 를 `Surface` 에 넣는다.
pub(crate) struct Spawned {
    pub(crate) master: Box<dyn MasterPty + Send>,
    pub(crate) child: Box<dyn Child + Send + Sync>,
    pub(crate) pid: u32,
}

/// ① PTY 를 연다(옛 `state.rs` `native_pty_system().openpty(..)` 자리).
pub(crate) fn open(size: PtySize) -> Result<Opened, String> {
    let pty = native_pty_system();
    let pair = pty
        .openpty(size)
        .map_err(|e| crate::state::map_pty_open_error(e.as_ref()))?;
    Ok(Opened { pair })
}

impl Opened {
    /// ② 자식을 띄운다(옛 `pair.slave.spawn_command(builder)` · Job 결박 · slave 닫기 자리).
    pub(crate) fn spawn(self, builder: CommandBuilder) -> Result<Spawned, String> {
        let pair = self.pair;
        let child = pair
            .slave
            .spawn_command(builder)
            .map_err(|e| format!("spawn failed: {e}"))?;
        let pid = child.process_id().unwrap_or(0);
        // ★D3(W5): 자식을 데몬 소유 Job 에 결박 — 데몬 사후 동반사망(Windows P2-9). unix 는 no-op.
        //   ★(1R#4) 자기 편입(bind_self)이 성립한 정상 경로에서는 **상속으로 이미 결박**돼 있어
        //   이 호출은 Ok 로 즉시 끝난다(경쟁 창 0). 강등 모드에서만 실제 편입을 시도하고,
        //   실패는 **조용히 넘어가지 않는다**(종전엔 반환값이 없어 실패가 보이지 않았다).
        #[cfg(windows)]
        if let Err(e) = crate::state::winjob::assign_child(pid) {
            eprintln!("[cysd] ⚠ PTY 자식 pid={pid} Job 결박 실패: {e} — 데몬 사후 고아 가능");
        }
        drop(pair.slave);
        Ok(Spawned { master: pair.master, child, pid })
    }
}

impl Spawned {
    /// ③ 출력 읽기 얼굴과 입력 쓰기 얼굴(옛 `try_clone_reader` · `take_writer` 자리 · 오류 문구 그대로).
    pub(crate) fn take_io(&mut self) -> Result<(Box<dyn Read + Send>, Box<dyn Write + Send>), String> {
        let reader = self
            .master
            .try_clone_reader()
            .map_err(|e| format!("clone reader failed: {e}"))?;
        let writer = self
            .master
            .take_writer()
            .map_err(|e| format!("take writer failed: {e}"))?;
        Ok((reader, writer))
    }

    /// ④ 전경 질의용 master raw fd(unix · 옛 `pair.master.as_raw_fd().unwrap_or(-1)` 자리). 모르면 −1(= 전경 판정 불능 → V2).
    #[cfg(unix)]
    pub(crate) fn foreground_fd(&self) -> i32 {
        self.master.as_raw_fd().unwrap_or(-1)
    }
}

/// 전경 프로세스 그룹(unix · 옛 `Surface::foreground_pgid_now` 본문) — `tcgetpgrp(캐시한 master fd)`. fd 가 없거나(< 0)·
/// 시스템 콜이 실패하면(반환 ≤ 0) `None`. 락 없음 · `master` Mutex 를 잡지 않는다.
#[cfg(unix)]
pub(crate) fn foreground_pgid(fd: &AtomicI32) -> Option<i32> {
    let fd = fd.load(Ordering::Relaxed);
    (fd >= 0).then(|| unsafe { libc::tcgetpgrp(fd) }).filter(|p| *p > 0)
}

/// 읽기 스레드가 EOF 를 본 뒤의 회수(옛 `state.rs` 읽기 스레드 끝 자리).
/// 좀비 회수: 자력 종료(셸 exit)는 close_surface를 거치지 않으므로 여기서 reap.
/// EOF 시점엔 거의 항상 이미 종료 — 즉시 회수, 아니면 1초 후 한 번 더.
pub(crate) fn reap_after_eof(child: &Mutex<Box<dyn Child + Send + Sync>>) {
    let mut child = child.lock().unwrap();
    if child.try_wait().ok().flatten().is_none() {
        std::thread::sleep(std::time::Duration::from_millis(1000));
        let _ = child.try_wait();
    }
}

/// 닫기의 자식 처치(옛 `governance::close_surface` 자리) — kill 후 reap · 좀비 잔존 차단
/// (reader 스레드의 try_wait와는 같은 Mutex로 직렬화).
pub(crate) fn kill_and_reap(child: &Mutex<Box<dyn Child + Send + Sync>>) {
    let mut child = child.lock().unwrap();
    let _ = child.kill();
    let _ = child.wait();
}

/// 크기 변경(옛 `repaint::resize_pty` 본문).
pub(crate) fn resize(master: &Mutex<Box<dyn MasterPty + Send>>, rows: u16, cols: u16) -> Result<(), String> {
    master
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .resize(PtySize { rows, cols, pixel_width: 0, pixel_height: 0 })
        .map_err(|e| format!("PTY 크기 변경 실패({rows}x{cols}): {e}"))
}

/// 닫기 인가 탐침(옛 `close_auth::probe_child` 본문 · 주석은 그 자리에 남김).
pub(crate) fn probe_child(exited: &AtomicBool, child: &Mutex<Box<dyn Child + Send + Sync>>) -> crate::close_auth::ChildProbe {
    use crate::close_auth::ChildProbe;
    if exited.load(std::sync::atomic::Ordering::Relaxed) {
        return ChildProbe::SurfaceExited;
    }
    let mut guard = match child.try_lock() {
        Ok(g) => g,
        Err(TryLockError::WouldBlock) => return ChildProbe::Contended,
        Err(TryLockError::Poisoned(_)) => return ChildProbe::Unreadable,
    };
    let caught = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| guard.try_wait()));
    drop(guard);
    match caught {
        Ok(Ok(None)) => ChildProbe::Running,
        Ok(Ok(Some(_))) => ChildProbe::Ended,
        Ok(Err(_)) | Err(_) => ChildProbe::Unreadable,
    }
}

/// 제출 뿌리 생존(옛 `handlers::owned_submit_root_live` 본문 · 주석은 그 자리에 남김).
pub(crate) fn owned_root_live(surface: &crate::state::Surface) -> bool {
    if surface.exited.load(std::sync::atomic::Ordering::Acquire) { return false; }
    let mut child = match surface.child.try_lock() {
        Ok(child) => child,
        Err(TryLockError::Poisoned(e)) => e.into_inner(),
        Err(TryLockError::WouldBlock) => return false,
    };
    if child.process_id() != Some(surface.pid) { return false; }
    #[cfg(windows)]
    {
        use windows_sys::Win32::Foundation::WAIT_TIMEOUT;
        use windows_sys::Win32::System::Threading::WaitForSingleObject;
        let Some(handle) = child.as_raw_handle() else { return false; };
        // WinChild::try_wait conflates GetExitCodeProcess failure with STILL_ACTIVE.
        // Only a successful unsignalled observation of the retained handle is positive.
        unsafe { WaitForSingleObject(handle as _, 0) == WAIT_TIMEOUT }
    }
    #[cfg(not(windows))]
    { matches!(child.try_wait(), Ok(None)) }
}
