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
pub(crate) enum Opened {
    /// 직접 PTY — 열린 PTY 쌍.
    Direct(PtyPair),
    /// seatkeep 경유 — 열기 단계에서 실행 파일·잠금·경로를 확인해 둔 기동 계획(맥).
    #[cfg(target_os = "macos")]
    Seatkeep(SeatkeepPlan),
}

/// 기동된 좌석 — 손잡이의 얼굴들. `take_io` 로 읽기·쓰기를 꺼낸 뒤 `master`·`child` 를 `Surface` 에 넣는다.
pub(crate) struct Spawned {
    pub(crate) master: Box<dyn MasterPty + Send>,
    pub(crate) child: Box<dyn Child + Send + Sync>,
    pub(crate) pid: u32,
    /// seatkeep 경유: 생성 때 만든 읽기·쓰기 얼굴(직접 PTY 는 None — `take_io` 가 master 에서 꺼낸다).
    io: Option<(Box<dyn Read + Send>, Box<dyn Write + Send>)>,
    /// seatkeep 경유: 전경 질의용 연결(직접 PTY 는 None).
    #[cfg(target_os = "macos")]
    link: Option<std::sync::Arc<SeatLink>>,
}

/// 전경 질의 fd 칸의 「seatkeep 연결로 물음」 표식(직접 PTY 의 −1 = 모름과 구별 — 시험이 −1 을 넣어 「모름」을 흉내 내는 경로 유지).
#[cfg(unix)]
pub(crate) const FG_VIA_LINK: i32 = -2;

/// ① PTY 를 연다(옛 `state.rs` `native_pty_system().openpty(..)` 자리). 노브(`CYS_SEATKEEP=1`)가 켜져 있으면 seatkeep 기동 계획을
/// 세운다 — 쓸 수 없으면(실행 파일 없음·실행 불가·잠금 없음·맥 밖 등) 이유와 함께 실패(직접 PTY 로 내려가지 않는다).
pub(crate) fn open(daemon: &crate::state::Daemon, size: PtySize) -> Result<Opened, String> {
    if seatkeep_enabled() {
        #[cfg(target_os = "macos")]
        return SeatkeepPlan::prepare(daemon, size).map(Opened::Seatkeep);
        #[cfg(not(target_os = "macos"))]
        return Err(format!("seatkeep 노브 켜짐({SEATKEEP_KNOB}=1) · 이 운영체제는 아직 지원하지 않음(맥 전용 · 리눅스·윈도우 = T7)"));
    }
    let _ = daemon;
    let pty = native_pty_system();
    let pair = pty
        .openpty(size)
        .map_err(|e| crate::state::map_pty_open_error(e.as_ref()))?;
    Ok(Opened::Direct(pair))
}

impl Opened {
    /// ② 자식을 띄운다(옛 `pair.slave.spawn_command(builder)` · Job 결박 · slave 닫기 자리).
    pub(crate) fn spawn(self, builder: CommandBuilder) -> Result<Spawned, String> {
        let pair = match self {
            Opened::Direct(pair) => pair,
            #[cfg(target_os = "macos")]
            Opened::Seatkeep(plan) => return plan.spawn(builder),
        };
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
        Ok(Spawned {
            master: pair.master,
            child,
            pid,
            io: None,
            #[cfg(target_os = "macos")]
            link: None,
        })
    }
}

impl Spawned {
    /// ③ 출력 읽기 얼굴과 입력 쓰기 얼굴(옛 `try_clone_reader` · `take_writer` 자리 · 오류 문구 그대로).
    pub(crate) fn take_io(&mut self) -> Result<(Box<dyn Read + Send>, Box<dyn Write + Send>), String> {
        if let Some(io) = self.io.take() {
            return Ok(io);
        }
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
        #[cfg(target_os = "macos")]
        if self.link.is_some() {
            return FG_VIA_LINK;
        }
        self.master.as_raw_fd().unwrap_or(-1)
    }

    /// 전경 질의용 seatkeep 연결(직접 PTY = None) — `Surface::seat_link` 에 넣는다.
    #[cfg(target_os = "macos")]
    pub(crate) fn link(&self) -> Option<std::sync::Arc<SeatLink>> {
        self.link.clone()
    }
}

/// 전경 프로세스 그룹(unix · 옛 `Surface::foreground_pgid_now` 본문) — `tcgetpgrp(캐시한 master fd)`. fd 가 없거나(< 0)·
/// 시스템 콜이 실패하면(반환 ≤ 0) `None`. 락 없음 · `master` Mutex 를 잡지 않는다.
/// seatkeep 경유(fd 칸 = [`FG_VIA_LINK`])는 연결로 FOREGROUND 를 묻는다(왕복 상한 200ms · 모르면 `None`).
#[cfg(unix)]
pub(crate) fn foreground_pgid(fd: &AtomicI32, link: Option<&SeatLinkRef>) -> Option<i32> {
    let fd = fd.load(Ordering::Relaxed);
    #[cfg(target_os = "macos")]
    if fd == FG_VIA_LINK {
        return link.and_then(|l| l.foreground());
    }
    let _ = link;
    (fd >= 0).then(|| unsafe { libc::tcgetpgrp(fd) }).filter(|p| *p > 0)
}

/// `Surface::seat_link` 의 타입(맥 = seatkeep 연결 · 그 밖 유닉스 = 비어 있는 자리).
#[cfg(target_os = "macos")]
pub(crate) type SeatLinkRef = SeatLink;
#[cfg(all(unix, not(target_os = "macos")))]
pub(crate) enum SeatLinkRef {}

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

// ─────────────────────────────── seatkeep 경유(노브 · 맥) ───────────────────────────────
//
// 노브 = 환경변수 `CYS_SEATKEEP=1`(그 밖 = 끔 · 정책 파일에서는 켜지 않는다 — `knobs.rs` 머리 규칙). **데몬 단위**: 처음 읽은 값을
// 프로세스 끝까지 쓴다(좌석마다 갈리지 않음). 켜졌는데 seatkeep 을 쓸 수 없으면 좌석 생성이 **이유와 함께 실패**한다 — 직접 PTY 로
// 조용히 내려가지 않는다(브리프 §1-2 · 「켰는데 안 켜진」 상태를 숨기지 않게).
//
// 프레임 정의는 seatkeep 쪽 파일(`src/bin/cys-seatkeep/proto.rs`)을 그대로 끌어 쓴다 — 두 실행 파일이 같은 정의를 본다.

/// 노브 이름.
pub(crate) const SEATKEEP_KNOB: &str = "CYS_SEATKEEP";

/// 노브 판정(순수) — `"1"`(앞뒤 공백 무시)만 켬.
pub(crate) fn seatkeep_enabled_from(env: Option<&str>) -> bool {
    env.map(|v| v.trim() == "1").unwrap_or(false)
}

/// 노브(데몬 단위 · 첫 읽기 고정).
pub(crate) fn seatkeep_enabled() -> bool {
    static ON: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *ON.get_or_init(|| {
        let on = seatkeep_enabled_from(std::env::var(SEATKEEP_KNOB).ok().as_deref());
        if on {
            eprintln!("[cysd] 좌석 보유 장치(seatkeep) 노브 켜짐({SEATKEEP_KNOB}=1) — 새 좌석은 cys-seatkeep 아래에서 뜬다(입양 없음 · T4 전)");
        }
        on
    })
}

/// 실행 파일 이름(브리프 §1-1 · DESIGN §7-2 ⓐ).
pub(crate) const SEATKEEP_EXE: &str = "cys-seatkeep";

/// seatkeep 실행 파일 = 지금 도는 cysd 실행 파일과 같은 폴더(개발 = `target/<profile>/` · 제품 = 앱 번들 `Contents/MacOS/`).
/// 시험 빌드는 cysd 시험 실행 파일이 `target/<profile>/deps/` 에 있으므로 한 단계 위를 본다.
pub(crate) fn seatkeep_exe_beside(cysd_exe: &std::path::Path) -> Option<std::path::PathBuf> {
    let dir = cysd_exe.parent()?;
    #[cfg(test)]
    let dir = if dir.file_name().map(|n| n == "deps").unwrap_or(false) { dir.parent()? } else { dir };
    Some(dir.join(SEATKEEP_EXE))
}

/// seatkeep 이 감사 토큰으로 이 프로세스를 볼 때의 코드 경로(인계 4 · T2 실측 = 번들 주 실행 파일이면 번들 경로).
/// 규칙: `<X>.app/Contents/MacOS/<이름>` 이고 `<X>.app/Contents/Info.plist` 의 `CFBundleExecutable` 이 `<이름>` 이면 `<X>.app`,
/// 아니면 실행 파일 경로 그대로. Info.plist 를 못 읽거나(이진 plist 포함) 키가 없으면 실행 파일 경로(= 번들 아님으로 본다).
pub(crate) fn audit_code_path(exe: &std::path::Path) -> std::path::PathBuf {
    let name = match exe.file_name().and_then(|n| n.to_str()) {
        Some(n) => n,
        None => return exe.to_path_buf(),
    };
    let macos = match exe.parent() {
        Some(d) if d.file_name().map(|n| n == "MacOS").unwrap_or(false) => d,
        _ => return exe.to_path_buf(),
    };
    let contents = match macos.parent() {
        Some(d) if d.file_name().map(|n| n == "Contents").unwrap_or(false) => d,
        _ => return exe.to_path_buf(),
    };
    let bundle = match contents.parent() {
        Some(d) if d.extension().map(|e| e == "app").unwrap_or(false) => d,
        _ => return exe.to_path_buf(),
    };
    match std::fs::read_to_string(contents.join("Info.plist")) {
        Ok(text) if plist_bundle_executable(&text).as_deref() == Some(name) => bundle.to_path_buf(),
        _ => exe.to_path_buf(),
    }
}

/// XML plist 에서 `CFBundleExecutable` 문자열 값(없으면 None). 이진 plist 는 `read_to_string` 단계에서 걸러진다.
fn plist_bundle_executable(text: &str) -> Option<String> {
    let k = text.find("<key>CFBundleExecutable</key>")?;
    let rest = &text[k + "<key>CFBundleExecutable</key>".len()..];
    let s = rest.find("<string>")?;
    // 키와 값 사이에는 공백만 있어야 한다(다른 키의 값을 집지 않게).
    if !rest[..s].trim().is_empty() {
        return None;
    }
    let v = &rest[s + "<string>".len()..];
    let e = v.find("</string>")?;
    Some(v[..e].trim().to_string())
}

#[cfg(target_os = "macos")]
#[allow(dead_code)]
#[path = "../cys-seatkeep/proto.rs"]
mod sk_proto;

#[cfg(target_os = "macos")]
pub(crate) use seatkeep_mac::{SeatkeepPlan, SeatLink};

#[cfg(target_os = "macos")]
mod seatkeep_mac {
    use super::sk_proto as proto;
    use portable_pty::{Child, ChildKiller, CommandBuilder, ExitStatus, MasterPty, PtySize};
    use serde_json::{json, Value};
    use std::collections::VecDeque;
    use std::io::{Read, Write};
    use std::os::unix::io::AsRawFd;
    use std::os::unix::net::UnixStream;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::sync::mpsc::{sync_channel, Receiver, SyncSender};
    use std::sync::{Arc, Condvar, Mutex, MutexGuard};
    use std::time::{Duration, Instant};

    /// seatkeep 좌석 번호(좌석당 방식 = 늘 0).
    const SEAT: u32 = 0;
    /// 입력 한 조각 상한 — seatkeep 의 입력 대기 상한(1MiB · `INPUT_QUEUE_BYTES`)을 넘지 않게. 한 번에 한 조각만 확인을 기다린다.
    const INPUT_CHUNK: usize = 256 << 10;
    /// 전경 질의 왕복 상한 — 넘으면 「모름」(None = 전경 판정 불능 → V2 종전 경로).
    const FG_TIMEOUT: Duration = Duration::from_millis(200);
    /// 기동 ~ WELCOME 상한.
    const START_TIMEOUT: Duration = Duration::from_secs(10);
    /// 연결 스레드 → 읽기 얼굴 출력 큐의 조각 수 상한(조각 ≤ 1MiB · seatkeep 재생 조각). 차면 연결 스레드가 기다린다 = 소켓을 안 읽는다
    /// → seatkeep 이 자기 큐(4MiB)를 넘는 출력을 꼬리로 돌린다(「밀림」 · T2 설계). 상한 없는 큐를 두지 않는다(master#c125bc97 ③).
    const OUT_QUEUE_CHUNKS: usize = 64;
    /// 맥 소켓 경로 한도(sun_path 104 · NUL 포함).
    const SUN_PATH_MAX: usize = 104;

    /// 열기 단계에서 정해 둔 seatkeep 기동 계획(생성 2단계의 앞 절반 — 직접 PTY 의 `openpty` 자리에서 실패할 것은 여기서 실패한다).
    pub(crate) struct SeatkeepPlan {
        exe: PathBuf,
        dir: PathBuf,
        id: String,
        controller_exe: PathBuf,
        lock: PathBuf,
        /// 코드서명 요구사항(브리프 §1-4 — 자리만 둔다 · 제품 필수 여부는 T6).
        requirement: Option<String>,
        size: PtySize,
    }

    fn io_err(msg: impl Into<String>) -> std::io::Error {
        std::io::Error::new(std::io::ErrorKind::Other, msg.into())
    }

    impl SeatkeepPlan {
        /// 실행 파일 · 잠금 · 상태 폴더 · 소켓 경로 길이를 미리 본다. 어느 하나라도 안 되면 이유와 함께 실패.
        pub(crate) fn prepare(daemon: &crate::state::Daemon, size: PtySize) -> Result<SeatkeepPlan, String> {
            let me = std::env::current_exe().map_err(|e| format!("seatkeep: cysd 실행 파일 경로를 모름: {e}"))?;
            let exe = super::seatkeep_exe_beside(&me).ok_or_else(|| format!("seatkeep: {} 옆 폴더를 모름", me.display()))?;
            match std::fs::metadata(&exe) {
                Ok(m) if m.is_file() && std::os::unix::fs::PermissionsExt::mode(&m.permissions()) & 0o111 != 0 => {}
                Ok(_) => return Err(format!("seatkeep 노브 켜짐({}=1) · 실행 파일이 실행 가능한 파일이 아니다: {}", super::SEATKEEP_KNOB, exe.display())),
                Err(e) => return Err(format!("seatkeep 노브 켜짐({}=1) · 실행 파일 없음: {} ({e})", super::SEATKEEP_KNOB, exe.display())),
            }
            let lock = controller_lock(daemon)?;
            static SEQ: AtomicU64 = AtomicU64::new(0);
            let id = format!("{:x}-{:x}-{}", std::process::id(), daemon.started_at as u64, SEQ.fetch_add(1, Ordering::Relaxed));
            let dir = seatkeep_base(daemon);
            let sock = dir.join("seatkeep").join(format!("{id}.sock"));
            if sock.as_os_str().len() >= SUN_PATH_MAX {
                return Err(format!("seatkeep: 소켓 경로가 너무 길다({}바이트 ≥ {SUN_PATH_MAX}): {}", sock.as_os_str().len(), sock.display()));
            }
            Ok(SeatkeepPlan { exe, dir, id, controller_exe: super::audit_code_path(&me), lock, requirement: None, size })
        }

        /// 기동 → 붙기 → WELCOME. 실패하면 띄운 seatkeep 을 정리하고 이유를 돌려준다.
        pub(crate) fn spawn(self, builder: CommandBuilder) -> Result<super::Spawned, String> {
            let argv: Vec<String> = builder
                .get_argv()
                .iter()
                .map(|a| a.to_str().map(str::to_string).ok_or_else(|| "seatkeep: 명령 인자가 UTF-8 이 아니다".to_string()))
                .collect::<Result<_, _>>()?;
            if argv.is_empty() {
                return Err("seatkeep: 빈 명령(기본 셸 좌석은 seatkeep 경유에서 지원하지 않음)".into());
            }
            // 작업 폴더 규칙 = portable-pty `as_command`(폴더가 아니면 HOME).
            let home = builder.get_env("HOME").map(PathBuf::from).or_else(dirs::home_dir).unwrap_or_else(|| PathBuf::from("/"));
            let cwd = builder
                .get_cwd()
                .map(PathBuf::from)
                .filter(|d| d.is_dir())
                .unwrap_or(home);
            let mut cmd = std::process::Command::new(&self.exe);
            cmd.arg("--dir").arg(&self.dir)
                .arg("--id").arg(&self.id)
                .arg("--controller-exe").arg(&self.controller_exe)
                .arg("--lock").arg(&self.lock)
                .arg("--rows").arg(self.size.rows.to_string())
                .arg("--cols").arg(self.size.cols.to_string())
                // ★T3 = 조종자 종속 모드(master#77162b13 · 옛 --end-on-controller-loss 를 넓힘) — 좌석이 직접 PTY 와 같다:
                //   cysd(조종자)가 끊기면 seatkeep 이 끝나 커널이 좌석에 SIGHUP(master#c125bc97 ②) · cysd 가 밀리면 seatkeep 이 PTY 읽기를
                //   멈춰 자식이 cysd 속도에 맞춰 멈춤(출력 유실 0) · 멈춘 cysd 를 내보내지 않음(write_stalled 없음).
                //   ⚠T4(입양)가 켜질 때 **이 인자를 뺀다** — 이 한 줄이 「데몬이 죽어도 좌석이 산다」를 막는 자리다(그때 밀림 정책을 다시 정한다).
                .arg("--controller-bound");
            if let Some(req) = &self.requirement {
                cmd.arg("--requirement").arg(req);
            }
            cmd.arg("--").args(&argv)
                .env_clear()
                .envs(builder.iter_full_env_as_str())
                .current_dir(&cwd)
                .stdin(std::process::Stdio::null())
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::inherit());
            let mut keeper = cmd.spawn().map_err(|e| format!("seatkeep 기동 실패({}): {e}", self.exe.display()))?;
            let keeper_pid = keeper.id();
            match self.attach(&mut keeper) {
                Ok((stream, welcome)) => SeatLink::start(stream, welcome, keeper, self.size),
                Err(e) => {
                    // 붙지 못한 seatkeep — 내가 띄운 것만 정리한다(그룹 = seatkeep 이 setsid 로 만든 새 세션의 그룹).
                    unsafe { libc::kill(keeper_pid as i32, libc::SIGTERM) };
                    let t = Instant::now();
                    while t.elapsed() < Duration::from_secs(2) {
                        if matches!(keeper.try_wait(), Ok(Some(_))) {
                            break;
                        }
                        std::thread::sleep(Duration::from_millis(20));
                    }
                    if !matches!(keeper.try_wait(), Ok(Some(_))) {
                        let _ = keeper.kill();
                        let _ = keeper.wait();
                    }
                    Err(e)
                }
            }
        }

        fn attach(&self, keeper: &mut std::process::Child) -> Result<(UnixStream, Value), String> {
            let sock = self.dir.join("seatkeep").join(format!("{}.sock", self.id));
            let deadline = Instant::now() + START_TIMEOUT;
            let mut stream = loop {
                if let Ok(Some(st)) = keeper.try_wait() {
                    return Err(format!(
                        "seatkeep 이 붙기 전에 끝남(rc {:?} · 2=인자/경로 3=신원·상태폴더·등록부 4=같은 id·미소비 종료 기록 5=PTY·자식 기동 7=작업 폴더가 사라짐 8=띄운 cysd 가 기동 중에 사라짐) — 사유는 cysd 로그의 cys-seatkeep 줄",
                        st.code()
                    ));
                }
                if let Ok(s) = UnixStream::connect(&sock) {
                    break s;
                }
                if Instant::now() >= deadline {
                    return Err(format!("seatkeep 소켓에 {}초 안에 못 붙음: {}", START_TIMEOUT.as_secs(), sock.display()));
                }
                std::thread::sleep(Duration::from_millis(10));
            };
            greet(stream, keeper.id(), deadline)
        }
    }

    /// 붙은 소켓의 확인과 첫 인사(독립 검증 D3 — 시험이 이 함수를 직접 부른다): ⑴ 소켓 상대 pid = 내가 띄운 seatkeep
    /// ⑵ HELLO → WELCOME 의 pid = 같은 seatkeep. 둘 중 하나라도 다르면 이유와 함께 생성 실패.
    pub(super) fn greet(mut stream: UnixStream, keeper_pid: u32, deadline: Instant) -> Result<(UnixStream, Value), String> {
        // 반대 방향 확인(DESIGN §3-2 ②): 이 소켓의 상대 = 내가 띄운 seatkeep 이어야 한다(가짜 소켓이 가짜 화면을 먹이는 것 차단).
        let peer = peer_pid(&stream).ok_or_else(|| "seatkeep 소켓 상대 pid 를 못 읽음".to_string())?;
        if peer != keeper_pid as i32 {
            return Err(format!("seatkeep 소켓 상대 pid {peer} ≠ 띄운 seatkeep {}", keeper_pid));
        }
        let left = deadline.saturating_duration_since(Instant::now()).max(Duration::from_millis(100));
        let _ = stream.set_read_timeout(Some(left));
        proto::write_all(&mut stream, &proto::json_frame(proto::HELLO, SEAT, &json!({"core": proto::CORE_VERSION, "resume": {}})))
            .map_err(|e| format!("seatkeep HELLO 보내기 실패: {e}"))?;
        match proto::read_frame(&mut stream) {
            Ok(Some((proto::WELCOME, _, p))) => {
                let v: Value = serde_json::from_slice(&p).map_err(|e| format!("seatkeep WELCOME 해석 실패: {e}"))?;
                if v["pid"].as_i64() != Some(keeper_pid as i64) {
                    return Err(format!("seatkeep WELCOME pid {} ≠ 띄운 seatkeep {}", v["pid"], keeper_pid));
                }
                let _ = stream.set_read_timeout(None);
                Ok((stream, v))
            }
            Ok(Some((proto::REJECT, _, p))) => Err(format!("seatkeep 이 접속을 거절: {}", String::from_utf8_lossy(&p))),
            Ok(Some((k, _, _))) => Err(format!("seatkeep 첫 프레임이 WELCOME 이 아님(kind {k})")),
            Ok(None) => Err("seatkeep 이 HELLO 뒤 연결을 닫음".into()),
            Err(e) => Err(format!("seatkeep WELCOME 읽기 실패: {e}")),
        }
    }

    /// 맥 `LOCAL_PEERPID`.
    fn peer_pid(s: &UnixStream) -> Option<i32> {
        let mut pid: libc::pid_t = 0;
        let mut len = std::mem::size_of::<libc::pid_t>() as libc::socklen_t;
        let rc = unsafe {
            libc::getsockopt(s.as_raw_fd(), libc::SOL_LOCAL, libc::LOCAL_PEERPID, (&mut pid as *mut libc::pid_t).cast(), &mut len)
        };
        (rc == 0 && pid > 0).then_some(pid)
    }

    /// seatkeep 상태 폴더의 바탕(그 아래 `seatkeep/` 를 seatkeep 이 만든다) = 데몬 상태 폴더.
    /// 시험 빌드: 시험 데몬의 임시 폴더는 길어 맥 소켓 경로 한도(104)를 넘기 쉽다 → 짧은 임시 폴더(프로세스마다 하나).
    fn seatkeep_base(daemon: &crate::state::Daemon) -> PathBuf {
        #[cfg(test)]
        {
            let _ = daemon;
            std::env::temp_dir().join(format!("cskt-{:x}", std::process::id()))
        }
        #[cfg(not(test))]
        {
            crate::state::state_dir(&daemon.socket_path)
        }
    }

    /// 조종자 잠금 = 데몬 시작 잠금(`socket_path.with_extension("lock")` · main 이 쥐고 `pid 출생시각` 을 적는다).
    /// 시험 빌드: 시험 데몬은 시작 잠금을 잡지 않는다 → 이 프로세스가 그 경로를 잡아 데몬이 끝날 때까지 쥔다(같은 형식으로 적음).
    fn controller_lock(daemon: &crate::state::Daemon) -> Result<PathBuf, String> {
        #[cfg(not(test))]
        let lock = daemon.socket_path.with_extension("lock");
        // 시험 빌드: 시험 데몬 폴더는 일부러 쓰기를 막는 시험이 있다 — 시험용 잠금은 짧은 시험 폴더에 데몬마다 하나(같은 형식).
        #[cfg(test)]
        let lock = {
            use std::hash::{Hash, Hasher};
            let mut h = std::collections::hash_map::DefaultHasher::new();
            daemon.socket_path.hash(&mut h);
            let d = seatkeep_base(daemon).join("locks");
            let _ = std::fs::create_dir_all(&d);
            d.join(format!("{:x}.lock", h.finish()))
        };
        #[cfg(test)]
        {
            use std::collections::HashMap;
            static HELD: Mutex<Option<HashMap<PathBuf, std::fs::File>>> = Mutex::new(None);
            let mut g = HELD.lock().unwrap_or_else(|e| e.into_inner());
            let map = g.get_or_insert_with(HashMap::new);
            if !map.contains_key(&lock) {
                let mut f = std::fs::OpenOptions::new().create(true).read(true).write(true).open(&lock)
                    .map_err(|e| format!("seatkeep(시험): 잠금 파일 열기 실패 {}: {e}", lock.display()))?;
                if unsafe { libc::flock(f.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
                    return Err(format!("seatkeep(시험): 잠금을 못 잡음 {}", lock.display()));
                }
                let _ = f.set_len(0);
                let _ = write!(f, "{}", crate::deadman::lock_record(std::process::id(), true));
                let _ = f.flush();
                map.insert(lock.clone(), f);
            }
        }
        if !lock.exists() {
            return Err(format!("seatkeep: 데몬 시작 잠금 파일이 없다: {}", lock.display()));
        }
        Ok(lock)
    }

    #[derive(Default)]
    struct LinkState {
        /// 받은 입력 확인 id.
        acked: std::collections::HashSet<u64>,
        fg_sent: u64,
        fg_recv: u64,
        fg_answers: VecDeque<(u64, Option<i32>)>,
        exit: Option<ExitStatus>,
        closed: bool,
    }

    /// seatkeep 1개와의 연결(조종자 쪽). 손잡이의 얼굴(`MasterPty`·`Child`·읽기·쓰기)이 이것을 함께 쥔다.
    pub(crate) struct SeatLink {
        wr: Mutex<UnixStream>,
        st: Mutex<LinkState>,
        cv: Condvar,
        /// 전경 질의를 한 번에 하나씩(답 번호 대조는 `fg_sent`/`fg_recv`).
        fg_gate: Mutex<()>,
        size: Mutex<PtySize>,
        child_pid: u32,
        keeper_pid: u32,
        next_input: AtomicU64,
        input_base: u64,
        /// 받은 출력에서 건너뛴 바이트 합(seatkeep 꼬리에서 이미 밀려나 못 받은 구간 = 유실).
        gap_bytes: AtomicU64,
    }

    impl std::fmt::Debug for SeatLink {
        fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            write!(f, "SeatLink(seatkeep pid {} · 좌석 pid {})", self.keeper_pid, self.child_pid)
        }
    }

    impl SeatLink {
        fn lock_st(&self) -> MutexGuard<'_, LinkState> {
            self.st.lock().unwrap_or_else(|e| e.into_inner())
        }

        fn start(stream: UnixStream, welcome: Value, keeper: std::process::Child, size: PtySize) -> Result<super::Spawned, String> {
            let seat0 = &welcome["seats"][0];
            let child_pid = seat0["child_pid"].as_i64().filter(|p| *p > 0).ok_or_else(|| format!("seatkeep WELCOME 에 좌석 pid 없음: {welcome}"))? as u32;
            let rd = stream.try_clone().map_err(|e| format!("seatkeep 연결 복제 실패: {e}"))?;
            let link = Arc::new(SeatLink {
                wr: Mutex::new(stream),
                st: Mutex::new(LinkState::default()),
                cv: Condvar::new(),
                fg_gate: Mutex::new(()),
                size: Mutex::new(size),
                child_pid,
                keeper_pid: keeper.id(),
                next_input: AtomicU64::new(1),
                input_base: (crate::state::now_epoch() as u64) << 24,
                gap_bytes: AtomicU64::new(0),
            });
            let (tx, rx) = sync_channel::<Vec<u8>>(OUT_QUEUE_CHUNKS);
            {
                let l = Arc::clone(&link);
                std::thread::Builder::new()
                    .name(format!("seatkeep-link-{child_pid}"))
                    .spawn(move || l.demux(rd, tx, keeper))
                    .map_err(|e| format!("seatkeep 연결 스레드 기동 실패: {e}"))?;
            }
            let spawned = super::Spawned {
                master: Box::new(KeepMaster(Arc::clone(&link))),
                child: Box::new(KeepChild(Arc::clone(&link))),
                pid: child_pid,
                io: Some((Box::new(ChanReader { rx, buf: Vec::new(), pos: 0 }), Box::new(KeepWriter(Arc::clone(&link))))),
                link: Some(Arc::clone(&link)),
            };
            Ok(spawned)
        }

        fn send(&self, kind: u8, payload: &[u8]) -> std::io::Result<()> {
            let mut w = self.wr.lock().unwrap_or_else(|e| e.into_inner());
            proto::write_all(&mut *w, &proto::frame(kind, SEAT, payload))
        }

        /// 연결 스레드 — 프레임을 나눈다. 끝나면(끊김) 종료로 접고 seatkeep 프로세스를 회수한다.
        fn demux(self: Arc<Self>, mut rd: UnixStream, tx: SyncSender<Vec<u8>>, mut keeper: std::process::Child) {
            let mut tx = Some(tx);
            let mut expect: u64 = 0;
            loop {
                let (kind, _seat, payload) = match proto::read_frame(&mut rd) {
                    Ok(Some(f)) => f,
                    _ => break,
                };
                match kind {
                    proto::OUTPUT if payload.len() >= 8 => {
                        let off = u64::from_le_bytes(payload[..8].try_into().unwrap_or([0; 8]));
                        let bytes = &payload[8..];
                        let end = off + bytes.len() as u64;
                        if off > expect {
                            self.gap_bytes.fetch_add(off - expect, Ordering::Relaxed);
                            eprintln!("[cysd] seatkeep 좌석 pid {} 출력 구멍 {}바이트(오프셋 {expect}→{off})", self.child_pid, off - expect);
                        }
                        if end <= expect {
                            continue; // 이미 받은 구간(재생 겹침)
                        }
                        let skip = expect.saturating_sub(off) as usize;
                        expect = end;
                        if let Some(t) = &tx {
                            // 큐가 차면 여기서 기다린다(읽기 얼굴이 비울 때까지) · 읽기 얼굴이 사라졌으면 출력은 버린다(좌석이 닫히는 중).
                            if t.send(bytes[skip..].to_vec()).is_err() {
                                tx = None;
                            }
                        }
                    }
                    proto::INPUT_ACK if payload.len() >= 8 => {
                        let id = u64::from_le_bytes(payload[..8].try_into().unwrap_or([0; 8]));
                        self.lock_st().acked.insert(id);
                        self.cv.notify_all();
                    }
                    proto::FOREGROUND_IS => {
                        let v: Value = serde_json::from_slice(&payload).unwrap_or(Value::Null);
                        let pg = v["pgid"].as_i64().filter(|p| *p > 0).map(|p| p as i32);
                        let mut st = self.lock_st();
                        st.fg_recv += 1;
                        let n = st.fg_recv;
                        st.fg_answers.push_back((n, pg));
                        while st.fg_answers.len() > 16 {
                            st.fg_answers.pop_front();
                        }
                        drop(st);
                        self.cv.notify_all();
                    }
                    proto::EXITED => {
                        let v: Value = serde_json::from_slice(&payload).unwrap_or(Value::Null);
                        let status = match v["signal"].as_str() {
                            Some(sig) => ExitStatus::with_signal(sig),
                            None => ExitStatus::with_exit_code(v["code"].as_u64().unwrap_or(0) as u32),
                        };
                        // 마지막 출력 뒤에 온다(seatkeep 순서 보장) — 읽기 얼굴을 닫아 EOF 로, 종료를 기록, 바로 확인.
                        tx = None;
                        {
                            let mut st = self.lock_st();
                            if st.exit.is_none() {
                                st.exit = Some(status);
                            }
                        }
                        self.cv.notify_all();
                        let _ = self.send(proto::EXIT_ACK, b"");
                    }
                    _ => {}
                }
            }
            drop(tx);
            {
                let mut st = self.lock_st();
                st.closed = true;
                if st.exit.is_none() {
                    // seatkeep 이 사라지면 PTY 마스터의 마지막 사본이 닫혀 자식도 SIGHUP 으로 끝난다(DESIGN §1-2) — 끝난 것으로 접는다.
                    st.exit = Some(ExitStatus::with_signal("seatkeep_disconnected"));
                }
            }
            self.cv.notify_all();
            let _ = keeper.wait();
        }

        /// 입력 한 조각 — INPUT 을 보내고 수신 확인(= PTY 에 다 씀)까지 기다린다. 끊김·종료 = 오류.
        fn write_chunk(&self, bytes: &[u8]) -> std::io::Result<()> {
            let id = self.input_base | self.next_input.fetch_add(1, Ordering::Relaxed);
            let mut p = id.to_le_bytes().to_vec();
            p.extend_from_slice(bytes);
            self.send(proto::INPUT, &p)?;
            let mut st = self.lock_st();
            loop {
                if st.acked.remove(&id) {
                    return Ok(());
                }
                if st.closed || st.exit.is_some() {
                    return Err(std::io::Error::new(std::io::ErrorKind::BrokenPipe, "seatkeep: 좌석이 끝났거나 연결이 끊김"));
                }
                st = self.cv.wait(st).unwrap_or_else(|e| e.into_inner());
            }
        }

        /// 전경 그룹 질의(락 없는 경로에서 부름 · 상한 FG_TIMEOUT · 모르면 None).
        pub(crate) fn foreground(&self) -> Option<i32> {
            let _g = self.fg_gate.lock().unwrap_or_else(|e| e.into_inner());
            let my = {
                let mut st = self.lock_st();
                if st.closed || st.exit.is_some() {
                    return None;
                }
                st.fg_sent += 1;
                st.fg_sent
            };
            if self.send(proto::FOREGROUND, b"").is_err() {
                return None;
            }
            let deadline = Instant::now() + FG_TIMEOUT;
            let mut st = self.lock_st();
            loop {
                if let Some(&(_, pg)) = st.fg_answers.iter().find(|(n, _)| *n == my) {
                    return pg;
                }
                if st.closed {
                    return None;
                }
                let now = Instant::now();
                if now >= deadline {
                    return None;
                }
                st = self.cv.wait_timeout(st, deadline - now).unwrap_or_else(|e| e.into_inner()).0;
            }
        }

        /// seatkeep 프로세스 pid(관측·시험용).
        #[cfg_attr(not(test), allow(dead_code))]
        pub(crate) fn keeper_pid(&self) -> u32 {
            self.keeper_pid
        }

        /// 지금까지 보낸 전경 질의 수(관측·시험용 — 입력마다 소켓 왕복이 끼는지 잰다).
        #[cfg_attr(not(test), allow(dead_code))]
        pub(crate) fn fg_queries(&self) -> u64 {
            self.lock_st().fg_sent
        }

        /// 지금까지의 출력 유실 바이트(관측·시험용).
        #[cfg_attr(not(test), allow(dead_code))]
        pub(crate) fn gap_bytes(&self) -> u64 {
            self.gap_bytes.load(Ordering::Relaxed)
        }

        /// 좌석 **리더 pid 에만** 신호(D7 결정 B · master#fe07cc6a — 직접 PTY `Child::kill` 과 같은 대상). seatkeep 이 회수 표시
        /// 잠금 안에서 보내고, 이미 회수됐으면 보내지 않고 SIGNAL_RESULT 로 답한다(그 답은 연결 스레드가 받아 버린다 — 회수 사실은
        /// 곧 EXITED 로도 온다).
        fn signal_leader(&self, sig: i32) -> std::io::Result<()> {
            self.send(proto::SIGNAL, json!({"sig": sig, "target": "leader"}).to_string().as_bytes())
        }

        fn exit_status(&self) -> Option<ExitStatus> {
            self.lock_st().exit.clone()
        }

        /// 직접 PTY `Child::kill` 과 같은 모양·같은 대상: 리더에 SIGHUP → 회수 확인(즉시 + 50ms × 4) → 리더에 SIGKILL.
        /// (RELEASE 는 그룹 SIGHUP 이라 D7 결정 B 와 어긋나 T3 에서 쓰지 않는다 — 판 내림(T6) 몫.)
        fn kill(&self) -> std::io::Result<()> {
            if self.exit_status().is_some() {
                return Ok(());
            }
            self.signal_leader(libc::SIGHUP)?;
            for attempt in 0..5 {
                if attempt > 0 {
                    std::thread::sleep(Duration::from_millis(50));
                }
                if self.exit_status().is_some() {
                    return Ok(());
                }
            }
            self.signal_leader(libc::SIGKILL)
        }
    }

    // ── 손잡이의 얼굴 ──

    struct KeepMaster(Arc<SeatLink>);
    impl std::fmt::Debug for KeepMaster {
        fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            write!(f, "KeepMaster({:?})", self.0)
        }
    }
    impl MasterPty for KeepMaster {
        fn resize(&self, size: PtySize) -> Result<(), anyhow::Error> {
            self.0
                .send(proto::RESIZE, json!({"rows": size.rows, "cols": size.cols}).to_string().as_bytes())
                .map_err(anyhow::Error::from)?;
            *self.0.size.lock().unwrap_or_else(|e| e.into_inner()) = size;
            Ok(())
        }
        fn get_size(&self) -> Result<PtySize, anyhow::Error> {
            Ok(*self.0.size.lock().unwrap_or_else(|e| e.into_inner()))
        }
        fn try_clone_reader(&self) -> Result<Box<dyn Read + Send>, anyhow::Error> {
            Err(anyhow::Error::from(io_err("seatkeep: 읽기 얼굴은 생성 때 한 번만 꺼낸다")))
        }
        fn take_writer(&self) -> Result<Box<dyn Write + Send>, anyhow::Error> {
            Err(anyhow::Error::from(io_err("seatkeep: 쓰기 얼굴은 생성 때 한 번만 꺼낸다")))
        }
        fn process_group_leader(&self) -> Option<libc::pid_t> {
            self.0.foreground()
        }
        fn as_raw_fd(&self) -> Option<std::os::unix::io::RawFd> {
            None
        }
        fn tty_name(&self) -> Option<PathBuf> {
            None
        }
    }

    #[derive(Debug)]
    struct KeepChild(Arc<SeatLink>);
    impl ChildKiller for KeepChild {
        fn kill(&mut self) -> std::io::Result<()> {
            self.0.kill()
        }
        fn clone_killer(&self) -> Box<dyn ChildKiller + Send + Sync> {
            Box::new(KeepChild(Arc::clone(&self.0)))
        }
    }
    impl Child for KeepChild {
        fn try_wait(&mut self) -> std::io::Result<Option<ExitStatus>> {
            Ok(self.0.exit_status())
        }
        fn wait(&mut self) -> std::io::Result<ExitStatus> {
            let mut st = self.0.lock_st();
            loop {
                if let Some(s) = st.exit.clone() {
                    return Ok(s);
                }
                st = self.0.cv.wait(st).unwrap_or_else(|e| e.into_inner());
            }
        }
        fn process_id(&self) -> Option<u32> {
            Some(self.0.child_pid)
        }
    }

    struct KeepWriter(Arc<SeatLink>);
    impl Write for KeepWriter {
        fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
            if buf.is_empty() {
                return Ok(0);
            }
            let n = buf.len().min(INPUT_CHUNK);
            self.0.write_chunk(&buf[..n])?;
            Ok(n)
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }

    /// 출력 읽기 얼굴 — 연결 스레드가 넣은 조각을 차례로 돌려준다. 보내는 쪽이 닫히면(EXITED·끊김) EOF.
    struct ChanReader {
        rx: Receiver<Vec<u8>>,
        buf: Vec<u8>,
        pos: usize,
    }
    impl Read for ChanReader {
        fn read(&mut self, out: &mut [u8]) -> std::io::Result<usize> {
            if self.pos >= self.buf.len() {
                match self.rx.recv() {
                    Ok(b) => {
                        self.buf = b;
                        self.pos = 0;
                    }
                    Err(_) => return Ok(0),
                }
            }
            let n = out.len().min(self.buf.len() - self.pos);
            out[..n].copy_from_slice(&self.buf[self.pos..self.pos + n]);
            self.pos += n;
            Ok(n)
        }
    }
}

#[cfg(test)]
#[path = "seat_proc_tests.rs"]
mod tests;

#[cfg(test)]
#[path = "seat_proc_gate_tests.rs"]
mod gate_tests;
