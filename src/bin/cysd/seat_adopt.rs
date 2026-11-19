//! 좌석 입양(T4 · TICKET=cysr-1116-seatkeep-1119 · 설계 = `docs/seatkeep/T4-DESIGN.md` · holder DESIGN §3-2 ③ · T0 §3).
//!
//! 노브 `CYS_SEATKEEP_ADOPT=1`(+ `CYS_SEATKEEP=1`) 일 때만 일한다 — 끔이면 이 파일의 어떤 함수도 파일·소켓에 닿지 않는다.
//!
//! 하는 일 넷:
//! ① **좌석 기록**: seatkeep 경유 좌석마다 cysd 가 아는 신원·약속(T0 ⓑ)을 seatkeep 상태 폴더의 `<seatkeep id>.cysd.json` 에 원자 쓰기한다.
//!    자식 기동 **전** 임시본(`record_provisional` · seatkeep pid 없음 — 못 쓰면 좌석을 만들지 않는다) → 기동 직후 · `persist_topology` 마다 전체본.
//!    쓰기는 한 잠금 안에서 「스냅샷 → 고유 임시 파일 → rename」(늦은 스냅샷이 새 값을 덮지 않음 · codex T4 1R #5). 좌석 토큰은 쓰지 않는다(비편입 계약 · T5 몫).
//! ② **기동 입양**(`adopt_on_boot`): 시작 잠금 뒤 · watchdog·accept·자동 복원 전(main.rs). 판정(`judge`)은 **pid 생존 + 출생 시각**을 먼저 보고
//!    (기록의 seatkeep 출생 시각에 결박), 등록부가 없거나 읽기 오류여도 산 pid 는 **미결**(지우지 않음 · codex T4 1R #3). 붙기 = 소켓 경로는 id 에서
//!    도출 · 연결 뒤 상대 pid·출생 시각·실행 파일을 다시 확인(`seat_proc::adopt_connect` · codex T4 1R #2). 죽음 확인 = 남은 `.exit` 를 사건으로
//!    발행한 뒤 파일 정리(codex T4 1R #6).
//! ③ **미결 예약(T1 최소 대역 · 이 파일 한 곳)**: 살아 있으나 입양하지 못한 좌석의 역할을 데몬이 사는 동안 예약한다 —
//!    `surface_create_blocked` 가 `surface.create` 입구에서 그 역할의 새 좌석을 거절한다(자동 복원·`cys restore`·phoenix 재시도 모두 그 입구를
//!    지남 · codex T4 1R #1). 예약은 그 seatkeep 이 끝나면(pid 없음·출생 시각 다름) 풀린다. 역할을 모르는 미결(기록·env 모두 못 읽음)이 있으면
//!    역할 있는 좌석 생성을 모두 거절하고 그 기동의 자동 복원을 보류한다(`restore_should_hold`). 입양된 역할은 accept 전에 `roles` 맵에 있어
//!    따로 막지 않는다. ★T1(대화 소유 임대)이 오면 **`surface_create_blocked`·`restore_should_hold` 두 함수만** 갈아끼운다.
//! ④ **좌석 끝**: 좌석이 끝나면 기록을 지운다(`forget_surface` · 읽기 스레드 EOF) — 정상 종료 좌석이 다음 기동에 「없는 사이 끝남」으로 보이지 않게.

use crate::state::{Daemon, Surface};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};

/// 좌석 기록 파일 꼬리(seatkeep 의 `<id>.json` 등록부와 구별 — seatkeep 은 이 이름을 보지 않는다).
pub(crate) const RECORD_SUFFIX: &str = ".cysd.json";
/// 기록 형식 판.
const RECORD_SCHEMA: u32 = 1;
/// 입양 직후 큐 배달을 멈추는 시간 — 꼬리 재생·크기 흔들기로 화면이 다시 그려진 뒤 초안 관문(화면 판정)이 판단하게(T0 §2-4).
pub(crate) const ADOPT_QUEUE_PAUSE: std::time::Duration = std::time::Duration::from_secs(3);
/// 임시본 기록(seatkeep pid 없음)만 있고 등록부도 없을 때 「아직 뜨는 중」으로 볼 상한 — seatkeep 의 첫 조종자 상한(15초)보다 넉넉히.
/// 넘으면 그 seatkeep 은 스스로 끝났거나 뜨지 못했다(죽음 확인).
const PROVISIONAL_MAX_SECS: f64 = 60.0;

/// cysd 가 좌석마다 남기는 신원·약속(T0 ⓑ 중 입양에 쓰는 것). 모르는 칸은 None/기본값 — 추측으로 채우지 않는다.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub(crate) struct SeatRecord {
    pub schema: u32,
    pub skid: String,
    /// 진단용(입양은 이 값을 쓰지 않고 `<상태 폴더>/<skid>.sock` 을 쓴다 · codex T4 1R #2).
    pub sock: String,
    /// seatkeep pid — 0 = 임시본(자식 기동 전 기록 · 등록부의 pid 를 쓴다).
    pub keeper_pid: u32,
    /// seatkeep 출생 시각(µs) — 기록을 그 seatkeep 한 개에 결박한다(pid 재사용·남의 프로세스 차단). 임시본 = None.
    #[serde(default)]
    pub keeper_start_us: Option<u64>,
    pub surface_id: u64,
    pub display_no: Option<u16>,
    pub title: String,
    pub role: Option<String>,
    pub cmd: String,
    pub cwd: String,
    pub created_at: f64,
    pub env_injected: bool,
    pub rows: u16,
    pub cols: u16,
    pub agent_meta: Option<(String, String)>,
    pub agent_session_id: Option<String>,
    pub claude_config_dir: Option<String>,
    pub config_dir_trusted: bool,
    pub registered_transcript: Option<String>,
    pub repin_anchor: Option<String>,
    pub agent_epoch: u64,
    pub conversation_epoch: u64,
    pub awakened_at: Option<f64>,
    pub directive_verified: Option<bool>,
    pub pack_reinject: Option<crate::state::PackReinject>,
    pub gate_pending: Option<crate::state::GatePending>,
    /// 기록 시각(진단 · 임시본 나이 판정).
    pub at: f64,
}

/// 입양 갈래로 `create_surface_core` 에 넘기는 것 — 기록 + 이미 붙은 손잡이.
pub(crate) struct AdoptSeat {
    pub rec: SeatRecord,
    pub spawned: crate::seat_proc::Spawned,
}

/// 켜짐 판정(노브 둘 다).
pub(crate) fn enabled() -> bool {
    crate::seat_proc::seatkeep_adopt_enabled()
}

// ─────────────────────────────── ① 좌석 기록 ───────────────────────────────

/// 기록 쓰기 잠금(전 좌석 공용) — 스냅샷과 쓰기를 같은 잠금 안에서 해 늦은 스냅샷이 새 값을 덮지 않는다.
static RECORD_LOCK: Mutex<()> = Mutex::new(());

fn record_path_in(dir: &Path, skid: &str) -> PathBuf {
    dir.join(format!("{skid}{RECORD_SUFFIX}"))
}

/// 고유 임시 파일 → fsync → rename(0600). 같은 이름 임시 파일을 두 쓰기가 나눠 쓰지 않는다.
fn write_record_file(path: &Path, rec: &SeatRecord) -> std::io::Result<()> {
    use std::io::Write;
    use std::os::unix::fs::OpenOptionsExt;
    static SEQ: AtomicU64 = AtomicU64::new(0);
    let text = serde_json::to_string(rec).map_err(std::io::Error::other)?;
    let dir = path.parent().ok_or_else(|| std::io::Error::other("기록 경로에 폴더가 없음"))?;
    let tmp = dir.join(format!(".{}.{}.{}.tmp", path.file_name().and_then(|n| n.to_str()).unwrap_or("rec"), std::process::id(), SEQ.fetch_add(1, Ordering::Relaxed)));
    let res = (|| {
        let mut f = std::fs::OpenOptions::new().write(true).create_new(true).mode(0o600).open(&tmp)?;
        f.write_all(text.as_bytes())?;
        f.sync_all()?;
        std::fs::rename(&tmp, path)
    })();
    if res.is_err() {
        let _ = std::fs::remove_file(&tmp);
    }
    res
}

/// 살아 있는 seatkeep 좌석의 지금 신원·약속으로 기록을 만든다(필드마다 짧게 잠근다).
pub(crate) fn snapshot(s: &Surface, link: &crate::seat_proc::SeatLink) -> SeatRecord {
    let (rows, cols) = {
        let p = s.parser.lock().unwrap_or_else(|e| e.into_inner());
        p.screen().size()
    };
    SeatRecord {
        schema: RECORD_SCHEMA,
        skid: link.skid().to_string(),
        sock: link.sock().to_string_lossy().into_owned(),
        keeper_pid: link.keeper_pid(),
        keeper_start_us: link.keeper_start_us(),
        surface_id: s.id,
        display_no: s.display_no,
        title: s.title.lock().unwrap_or_else(|e| e.into_inner()).clone(),
        role: s.role.lock().unwrap_or_else(|e| e.into_inner()).clone(),
        cmd: s.cmd.clone(),
        cwd: s.cwd.clone(),
        created_at: s.created_at,
        env_injected: s.env_injected,
        rows,
        cols,
        agent_meta: s.agent_meta.lock().unwrap_or_else(|e| e.into_inner()).clone(),
        agent_session_id: s.agent_session_id.lock().unwrap_or_else(|e| e.into_inner()).clone(),
        claude_config_dir: s.claude_config_dir.lock().unwrap_or_else(|e| e.into_inner()).clone(),
        config_dir_trusted: s.config_dir_trusted,
        registered_transcript: s.registered_transcript.lock().unwrap_or_else(|e| e.into_inner()).clone(),
        repin_anchor: s.repin_anchor.lock().unwrap_or_else(|e| e.into_inner()).clone(),
        agent_epoch: s.agent_epoch.load(Ordering::SeqCst),
        conversation_epoch: s.conversation_epoch.load(Ordering::SeqCst),
        awakened_at: *s.awakened_at.lock().unwrap_or_else(|e| e.into_inner()),
        directive_verified: *s.directive_verified.lock().unwrap_or_else(|e| e.into_inner()),
        pack_reinject: s.pack_reinject.lock().unwrap_or_else(|e| e.into_inner()).clone(),
        gate_pending: s.gate_pending.lock().unwrap_or_else(|e| e.into_inner()).clone(),
        at: crate::state::now_epoch(),
    }
}

/// 자식 기동 전 임시본 — 생성 함수가 seatkeep 을 띄우기 바로 앞에서 부른다. 실패 = Err(호출자는 좌석을 만들지 않는다: 기록 없는 산 좌석을
/// 만들지 않기 위해 · 노브 켬일 때만 불림).
#[allow(clippy::too_many_arguments)]
pub(crate) fn record_provisional(
    dir: &Path,
    skid: &str,
    surface_id: u64,
    display_no: Option<u16>,
    title: &str,
    role: Option<&str>,
    cmd: &str,
    cwd: &str,
    env_injected: bool,
    rows: u16,
    cols: u16,
    claude_config_dir: Option<&str>,
    config_dir_trusted: bool,
) -> Result<(), String> {
    let now = crate::state::now_epoch();
    let rec = SeatRecord {
        schema: RECORD_SCHEMA,
        skid: skid.into(),
        sock: dir.join(format!("{skid}.sock")).to_string_lossy().into_owned(),
        keeper_pid: 0,
        keeper_start_us: None,
        surface_id,
        display_no,
        title: title.into(),
        role: role.map(str::to_string),
        cmd: cmd.into(),
        cwd: cwd.into(),
        created_at: now,
        env_injected,
        rows,
        cols,
        agent_meta: None,
        agent_session_id: None,
        claude_config_dir: claude_config_dir.map(str::to_string),
        config_dir_trusted,
        registered_transcript: None,
        repin_anchor: None,
        agent_epoch: 0,
        conversation_epoch: 0,
        awakened_at: None,
        directive_verified: None,
        pack_reinject: None,
        gate_pending: None,
        at: now,
    };
    let _g = RECORD_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    std::fs::create_dir_all(dir).map_err(|e| format!("좌석 기록 폴더 {}: {e}", dir.display()))?;
    write_record_file(&record_path_in(dir, skid), &rec).map_err(|e| format!("좌석 기록 임시본 쓰기 실패 {}: {e}", dir.display()))
}

/// 좌석 하나를 기록한다(끝난 좌석 = 기록 삭제). 노브 끔·직접 PTY 좌석 = 아무것도 안 함.
pub(crate) fn record_surface(s: &Surface) {
    if !enabled() {
        return;
    }
    let Some(link) = s.seat_link.as_deref() else { return };
    let Some(dir) = link.sock().parent() else { return };
    let path = record_path_in(dir, link.skid());
    let _g = RECORD_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    if s.exited.load(Ordering::SeqCst) {
        let _ = std::fs::remove_file(&path);
        return;
    }
    let rec = snapshot(s, link);
    if let Err(e) = write_record_file(&path, &rec) {
        eprintln!("[cysd] 좌석 기록 쓰기 실패 surface:{} ({}): {e} — 이 좌석은 직전 기록으로 입양된다", s.id, path.display());
    }
}

/// 좌석이 끝났다(읽기 스레드 EOF) — 기록을 지운다.
pub(crate) fn forget_surface(s: &Surface) {
    if !enabled() {
        return;
    }
    let Some(link) = s.seat_link.as_deref() else { return };
    let Some(dir) = link.sock().parent() else { return };
    let _g = RECORD_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let _ = std::fs::remove_file(record_path_in(dir, link.skid()));
}

/// 전 좌석 기록(`persist_topology` 가 부른다 — 신원·약속이 바뀌는 자리가 모두 그 길을 지난다).
pub(crate) fn record_all(daemon: &Daemon) {
    if !enabled() {
        return;
    }
    let list: Vec<Arc<Surface>> = daemon.surfaces.lock().unwrap_or_else(|e| e.into_inner()).values().cloned().collect();
    for s in list {
        record_surface(&s);
    }
}

// ─────────────────────────────── ② 판정 ───────────────────────────────

/// seatkeep 등록부(`<id>.json`) 읽기 결과 — 「없음」과 「읽기 오류」를 가른다(codex T4 1R #3).
#[derive(Debug)]
pub(crate) enum RegRead {
    Missing,
    Error,
    Unparsable,
    Ok(serde_json::Value),
}

pub(crate) fn read_registry(path: &Path) -> RegRead {
    match std::fs::read_to_string(path) {
        Ok(t) => match serde_json::from_str::<serde_json::Value>(&t) {
            Ok(v) if v.is_object() => RegRead::Ok(v),
            _ => RegRead::Unparsable,
        },
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => RegRead::Missing,
        Err(_) => RegRead::Error,
    }
}

/// 판정 결과.
#[derive(Debug, PartialEq, Eq)]
pub(crate) enum Liveness {
    /// 붙어 볼 만하다(pid 생존 · 출생 시각 = 기록·등록부 · 단계 committed/exited).
    Alive,
    /// 확실히 끝났다(pid 없음 · 출생 시각 다름 = pid 재사용 · 오래된 임시본) — 파일 정리 대상.
    Dead(&'static str),
    /// 판정 불가 또는 산 pid 인데 등록부가 어긋남 — 미결(파일을 지우지 않는다 · 역할 예약).
    Unknown(&'static str),
}

/// 판정 입력(순수 · 시험 대상).
pub(crate) struct JudgeIn<'a> {
    /// 기록이 있으면 그 seatkeep pid(0 = 임시본)·출생 시각·나이(초).
    pub rec: Option<(u32, Option<u64>, f64)>,
    pub reg: &'a RegRead,
    /// 판정 대상 pid 의 지금 관측(생존 · 출생 시각) — 대상 pid = 기록의 pid(0 이 아니면) 아니면 등록부 pid.
    pub alive: bool,
    pub start_now: Option<u64>,
    /// 그 pid 의 지금 실행 파일이 cys-seatkeep 인가(None = 못 읽음) — 「pid 재사용」을 죽음으로 볼 양성 증거(codex T4 2R).
    pub exe_is_seatkeep: Option<bool>,
}

/// 판정 대상 pid(기록 우선 · 임시본이면 등록부).
pub(crate) fn target_pid(rec: Option<(u32, Option<u64>, f64)>, reg: &RegRead) -> Option<u32> {
    match rec {
        Some((p, _, _)) if p != 0 => Some(p),
        _ => match reg {
            RegRead::Ok(r) => r["pid"].as_u64().filter(|p| *p > 0 && *p <= i32::MAX as u64).map(|p| p as u32),
            _ => None,
        },
    }
}

pub(crate) fn judge(j: &JudgeIn) -> Liveness {
    let reg_start = match j.reg {
        RegRead::Ok(r) => r["start_us"].as_u64(),
        _ => None,
    };
    if target_pid(j.rec, j.reg).is_none() {
        // 임시본만 있고 등록부에 pid 도 없다 — 아직 뜨는 중이거나 뜨지 못했다.
        return match j.rec {
            Some((_, _, age)) if age < PROVISIONAL_MAX_SECS => Liveness::Unknown("provisional_starting"),
            Some(_) => Liveness::Dead("never_started"),
            None => Liveness::Unknown("no_pid"),
        };
    }
    if !j.alive {
        return Liveness::Dead("keeper_gone");
    }
    let Some(now) = j.start_now else { return Liveness::Unknown("start_unreadable") };
    let expected = j.rec.and_then(|(_, s, _)| s).or(reg_start);
    match expected {
        // 기록과 다르지만 등록부는 지금 그 프로세스와 같다 = 기록이 낡았거나 손댄 것 — 산 seatkeep 파일을 지우지 않는다(미결).
        Some(e) if e != now && reg_start == Some(now) => return Liveness::Unknown("record_start_mismatch"),
        // pid 가 살아 있는데 출생 시각이 다르다 — 지금 그 pid 가 cys-seatkeep 이 **아니라는** 양성 증거가 있을 때만 죽음(pid 재사용) ·
        // 그 밖(실행 파일 못 읽음 · 다른 seatkeep)은 파일을 지우지 않는다(미결 · codex T4 2R 차단).
        Some(e) if e != now && j.exe_is_seatkeep == Some(false) => return Liveness::Dead("pid_reused"),
        Some(e) if e != now => return Liveness::Unknown("start_mismatch_live"),
        Some(_) => {}
        None => return Liveness::Unknown("start_unknown"),
    }
    match j.reg {
        RegRead::Missing => Liveness::Unknown("registry_missing_live"),
        RegRead::Error => Liveness::Unknown("registry_io"),
        RegRead::Unparsable => Liveness::Unknown("registry_unparsable"),
        RegRead::Ok(r) => {
            let pid = target_pid(j.rec, j.reg).unwrap_or(0) as u64;
            if r["pid"].as_u64() != Some(pid) {
                return Liveness::Unknown("registry_pid_mismatch");
            }
            if reg_start != Some(now) {
                return Liveness::Unknown("registry_start_mismatch");
            }
            match r["phase"].as_str().unwrap_or("") {
                "committed" | "exited" => Liveness::Alive,
                "prepare" => Liveness::Unknown("preparing"),
                _ => Liveness::Unknown("ending"),
            }
        }
    }
}

/// 프로세스 출생 시각(마이크로초 · seatkeep `registry::process_start_us` 와 같은 식 — 같은 값이어야 대조가 선다).
pub(crate) fn process_start_us(pid: u32) -> Option<u64> {
    #[cfg(target_os = "macos")]
    {
        let mut info: libc::proc_bsdinfo = unsafe { std::mem::zeroed() };
        let size = std::mem::size_of::<libc::proc_bsdinfo>() as i32;
        let rc = unsafe { libc::proc_pidinfo(pid as i32, libc::PROC_PIDTBSDINFO, 0, &mut info as *mut _ as *mut libc::c_void, size) };
        if rc != size {
            return None;
        }
        Some(info.pbi_start_tvsec * 1_000_000 + info.pbi_start_tvusec)
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = pid;
        None
    }
}

pub(crate) fn pid_alive(pid: u32) -> bool {
    #[cfg(unix)]
    {
        pid > 0
            && pid <= i32::MAX as u32
            && (unsafe { libc::kill(pid as i32, 0) } == 0 || std::io::Error::last_os_error().raw_os_error() == Some(libc::EPERM))
    }
    #[cfg(not(unix))]
    {
        let _ = pid;
        false
    }
}

/// 같은 사용자 프로세스의 환경 변수 하나(맥 `KERN_PROCARGS2` · seatkeep 은 플랫폼 실행 파일이 아니라 읽힌다). 기록을 못 읽은 미결 좌석의
/// 역할(`CYS_ROLE` — cysd 가 seatkeep 기동 env 에 실은 값)을 알아내 예약을 좁히는 데만 쓴다. 못 읽으면 None.
pub(crate) fn process_env_var(pid: u32, key: &str) -> Option<String> {
    #[cfg(target_os = "macos")]
    {
        let mut argmax: libc::c_int = 0;
        let mut sz = std::mem::size_of::<libc::c_int>();
        let mut mib = [libc::CTL_KERN, libc::KERN_ARGMAX];
        if unsafe { libc::sysctl(mib.as_mut_ptr(), 2, (&mut argmax as *mut libc::c_int).cast(), &mut sz, std::ptr::null_mut(), 0) } != 0 || argmax <= 0 {
            return None;
        }
        let mut buf = vec![0u8; argmax as usize];
        let mut len = buf.len();
        let mut mib = [libc::CTL_KERN, libc::KERN_PROCARGS2, pid as libc::c_int];
        if unsafe { libc::sysctl(mib.as_mut_ptr(), 3, buf.as_mut_ptr().cast(), &mut len, std::ptr::null_mut(), 0) } != 0 || len < 4 {
            return None;
        }
        parse_procargs_env(&buf[..len], key)
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = (pid, key);
        None
    }
}

/// `KERN_PROCARGS2` 버퍼 = [argc i32][실행 경로\0][\0 채움…][argv\0 × argc][env\0 …][\0] — env 에서 `key=` 를 찾는다(순수 · 시험 대상).
pub(crate) fn parse_procargs_env(buf: &[u8], key: &str) -> Option<String> {
    let argc = i32::from_ne_bytes(buf.get(..4)?.try_into().ok()?);
    if argc < 0 {
        return None;
    }
    let mut i = 4;
    while i < buf.len() && buf[i] != 0 {
        i += 1; // 실행 경로
    }
    while i < buf.len() && buf[i] == 0 {
        i += 1; // 채움
    }
    let mut seen = 0;
    while i < buf.len() && seen < argc {
        while i < buf.len() && buf[i] != 0 {
            i += 1;
        }
        i += 1;
        seen += 1;
    }
    let want = format!("{key}=");
    while i < buf.len() {
        let end = buf[i..].iter().position(|b| *b == 0).map(|p| i + p).unwrap_or(buf.len());
        if end == i {
            break; // 빈 문자열 = env 끝
        }
        if let Ok(s) = std::str::from_utf8(&buf[i..end]) {
            if let Some(v) = s.strip_prefix(&want) {
                return Some(v.to_string());
            }
        }
        i = end + 1;
    }
    None
}

// ─────────────────────────────── ③ 미결 예약 ───────────────────────────────

/// 한 좌석의 입양 결과.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub(crate) struct Outcome {
    pub skid: String,
    pub surface_id: Option<u64>,
    /// adopted · dead · unresolved
    pub result: &'static str,
    pub reason: String,
    pub role: Option<String>,
}

/// 이 기동의 입양 요약.
#[derive(Debug, Default, Clone, Serialize)]
pub(crate) struct BootSummary {
    pub ran: bool,
    pub outcomes: Vec<Outcome>,
}

/// 마지막 기동 입양 요약(진단 · 결과마다 `seat.adopted`/`seat.adopt_skipped` 이벤트와 같은 내용).
static SUMMARY: Mutex<Option<BootSummary>> = Mutex::new(None);

/// 미결 좌석 예약 — 그 seatkeep 이 살아 있는 동안(pid · 출생 시각) 유효.
#[derive(Debug, Clone)]
pub(crate) struct Pending {
    pub skid: String,
    /// None = 역할을 모름(기록·env 모두 못 읽음) → 역할 있는 좌석 생성을 모두 막는다.
    pub role: Option<String>,
    pub pid: Option<u32>,
    pub start_us: Option<u64>,
    /// 임시본(pid 없음)일 때 예약이 끝나는 벽시계.
    pub until: Option<f64>,
}

static PENDING: Mutex<Vec<Pending>> = Mutex::new(Vec::new());

/// 예약이 아직 유효한가(관측 함수 주입 — 시험).
pub(crate) fn pending_live(p: &Pending, alive: impl Fn(u32) -> bool, start: impl Fn(u32) -> Option<u64>, now: f64) -> bool {
    match p.pid {
        Some(pid) => alive(pid) && (p.start_us.is_none() || start(pid) == p.start_us),
        None => p.until.map(|u| now < u).unwrap_or(true),
    }
}

/// 순수 판정 — 이 역할의 새 좌석을 막아야 하나(예약 목록은 이미 살아 있는 것만).
pub(crate) fn blocked_by(pending: &[Pending], role: Option<&str>) -> Option<String> {
    let role = role?;
    if let Some(p) = pending.iter().find(|p| p.role.as_deref() == Some(role)) {
        return Some(format!(
            "seat_adopt_reserved: 역할 {role} 의 좌석(seatkeep {})이 살아 있으나 입양되지 않았다 — 같은 대화를 새 좌석이 이어 쓰지 않게 \
             그 seatkeep 이 끝날 때까지 이 역할의 새 좌석을 만들지 않는다(T4 · T1 전 대역)",
            p.skid
        ));
    }
    if let Some(p) = pending.iter().find(|p| p.role.is_none()) {
        return Some(format!(
            "seat_adopt_reserved: 역할을 알 수 없는 미입양 좌석(seatkeep {})이 살아 있다 — 그 좌석이 끝날 때까지 역할 있는 새 좌석을 만들지 않는다(T4 · T1 전 대역)",
            p.skid
        ));
    }
    None
}

/// ★T1 최소 대역 ①(갈아끼울 자리): `surface.create` 입구 — 이 역할의 새 좌석을 거절할 까닭(Some). 노브 끔 = 늘 None.
pub(crate) fn surface_create_blocked(role: Option<&str>) -> Option<String> {
    if !enabled() || role.is_none() {
        return None;
    }
    let mut g = PENDING.lock().unwrap_or_else(|e| e.into_inner());
    let now = crate::state::now_epoch();
    g.retain(|p| pending_live(p, pid_alive, process_start_us, now));
    blocked_by(&g, role)
}

/// ★T1 최소 대역 ②(갈아끼울 자리): 기동 자동 복원을 통째로 보류할 까닭 — 역할을 모르는 미결이 있을 때만(역할을 아는 미결은 ① 이 그 역할만 막는다).
pub(crate) fn restore_should_hold() -> Option<String> {
    if !enabled() {
        return None;
    }
    let mut g = PENDING.lock().unwrap_or_else(|e| e.into_inner());
    let now = crate::state::now_epoch();
    g.retain(|p| pending_live(p, pid_alive, process_start_us, now));
    let unknown: Vec<&str> = g.iter().filter(|p| p.role.is_none()).map(|p| p.skid.as_str()).collect();
    if unknown.is_empty() {
        return None;
    }
    Some(format!(
        "seat_adopt_unresolved: 역할을 알 수 없는 미입양 좌석 {}개({}) — 그 대화를 새 좌석이 이어 쓰지 않게 자동 복원을 보류한다(T1 전 대역)",
        unknown.len(),
        unknown.join(",")
    ))
}

#[cfg(test)]
pub(crate) fn test_set_pending(p: Vec<Pending>) {
    *PENDING.lock().unwrap_or_else(|e| e.into_inner()) = p;
}

// ─────────────────────────────── ② 기동 입양 ───────────────────────────────

/// 죽음이 확인된 좌석의 정리 — 남은 종료 기록(`.exit`)을 신원 확인 뒤 사건으로 발행하고(소비 · 표식 `.exit.consumed` 를 남긴 뒤) cysd 기록·
/// 등록부·잠금·소켓·종료 기록을 지운다. 교체 기록(`.log`)은 사후 적발 장치라 남긴다. `.exit` 를 못 읽거나 id 가 다르면 **아무것도 지우지 않는다**
/// (Err = 미결 · 다음 기동이 다시 본다 · codex T4 2R). 발행 뒤 표식 전 재시작 = 다음 기동에 한 번 더 발행될 수 있다(적어도 한 번 · 사건의 `skid` 가 멱등 키).
fn consume_dead(daemon: &Daemon, dir: &Path, skid: &str, rec: Option<&SeatRecord>, why: &str) -> Result<(), &'static str> {
    let exit_path = dir.join(format!("{skid}.exit"));
    let marker = dir.join(format!("{skid}.exit.consumed"));
    match std::fs::read_to_string(&exit_path) {
        Ok(t) => {
            let v: serde_json::Value = serde_json::from_str(&t).map_err(|_| "exit_unparsable")?;
            if v["id"].as_str() != Some(skid) {
                return Err("exit_id_mismatch");
            }
            if !marker.exists() {
                eprintln!("[cysd] 좌석 입양 {skid}: 데몬 없는 사이 끝난 좌석의 종료 기록 소비 — {}", v["seats"]);
                daemon.bus.publish(
                    "seat.exited_while_away",
                    "surface",
                    rec.map(|r| r.surface_id),
                    json!({"skid": skid, "surface_ref": rec.map(|r| cys::surface_ref(r.surface_id)),
                           "role": rec.and_then(|r| r.role.clone()), "exit": v["seats"], "why": why}),
                );
                std::fs::write(&marker, b"1").map_err(|_| "exit_marker_write")?;
            }
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(_) => return Err("exit_unreadable"),
    }
    for ext in [RECORD_SUFFIX, ".json", ".lock", ".sock", ".exit", ".exit.consumed"] {
        let _ = std::fs::remove_file(dir.join(format!("{skid}{ext}")));
    }
    Ok(())
}

/// 기동 입양 — 잠금 획득 뒤 · accept 전에 한 번(main.rs). 노브 끔 = 아무것도 안 함(요약도 `ran=false`).
pub(crate) fn adopt_on_boot(daemon: &Arc<Daemon>) {
    if !enabled() {
        return;
    }
    let mut summary = BootSummary { ran: true, outcomes: Vec::new() };
    #[cfg(target_os = "macos")]
    {
        let dir = crate::seat_proc::seatkeep_dir(daemon);
        // 대상 = 기록(.cysd.json)과 등록부(.json) 이름의 합집합(기록 없는 산 seatkeep 도 본다).
        let mut ids: Vec<String> = match std::fs::read_dir(&dir) {
            Ok(rd) => rd
                .filter_map(|e| e.ok())
                .filter_map(|e| e.file_name().into_string().ok())
                .filter(|n| !n.starts_with('.'))
                .filter_map(|n| n.strip_suffix(RECORD_SUFFIX).map(str::to_string).or_else(|| n.strip_suffix(".json").map(str::to_string)))
                .filter(|id| !id.is_empty() && id.chars().all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_'))
                .collect(),
            Err(_) => Vec::new(),
        };
        ids.sort();
        ids.dedup();
        let mut pending = Vec::new();
        for skid in ids {
            let (out, p) = adopt_one(daemon, &dir, &skid);
            eprintln!("[cysd] 좌석 입양 {skid}: {} ({})", out.result, out.reason);
            daemon.bus.publish(
                if out.result == "adopted" { "seat.adopted" } else { "seat.adopt_skipped" },
                "surface",
                out.surface_id,
                json!({"skid": out.skid, "result": out.result, "reason": out.reason, "role": out.role,
                       "surface_ref": out.surface_id.map(cys::surface_ref)}),
            );
            if let Some(p) = p {
                pending.push(p);
            }
            summary.outcomes.push(out);
        }
        *PENDING.lock().unwrap_or_else(|e| e.into_inner()) = pending;
    }
    *SUMMARY.lock().unwrap_or_else(|e| e.into_inner()) = Some(summary);
}

/// 좌석 하나 — 결과 + (미결이면) 예약.
#[cfg(target_os = "macos")]
fn adopt_one(daemon: &Arc<Daemon>, dir: &Path, skid: &str) -> (Outcome, Option<Pending>) {
    let rec_path = record_path_in(dir, skid);
    // 기록: 없음 / 못 읽음 / 있음.
    let rec: Result<Option<SeatRecord>, ()> = match std::fs::read_to_string(&rec_path) {
        Ok(t) => serde_json::from_str::<SeatRecord>(&t).ok().filter(|r| r.schema == RECORD_SCHEMA && r.skid == skid).map(Some).ok_or(()),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(_) => Err(()),
    };
    let reg = read_registry(&dir.join(format!("{skid}.json")));
    let now = crate::state::now_epoch();
    let rec_in = match &rec {
        Ok(Some(r)) => Some((r.keeper_pid, r.keeper_start_us, now - r.at)),
        _ => None,
    };
    let pid = target_pid(rec_in, &reg);
    let start_now = pid.and_then(process_start_us);
    let alive = pid.map(pid_alive).unwrap_or(false);
    let exe_is_seatkeep = if alive { pid.and_then(crate::seat_proc::seatkeep_exe_matches) } else { None };
    let verdict = judge(&JudgeIn { rec: rec_in, reg: &reg, alive, start_now, exe_is_seatkeep });
    let rec_ref = rec.as_ref().ok().and_then(|r| r.as_ref());
    let surface_id = rec_ref.map(|r| r.surface_id);
    let role_of = |r: Option<&SeatRecord>| -> Option<String> {
        r.and_then(|r| r.role.clone()).or_else(|| pid.and_then(|p| process_env_var(p, cys::ENV_ROLE)))
    };
    let mk = |result: &'static str, reason: String, role: Option<String>| Outcome { skid: skid.to_string(), surface_id, result, reason, role };
    let pend = |role: Option<String>| Pending {
        skid: skid.to_string(),
        role,
        pid,
        start_us: start_now,
        until: if pid.is_none() { Some(now + PROVISIONAL_MAX_SECS) } else { None },
    };
    // 기록을 못 읽음(권한·손상) — 지우지 않는다. 살아 있는 seatkeep 이면 역할(env)로 예약.
    if rec.is_err() {
        if pid.is_none() || matches!(verdict, Liveness::Dead(_)) {
            return (mk("unresolved", "record_unreadable_keeper_dead".into(), None), None);
        }
        let role = role_of(None);
        return (mk("unresolved", "record_unreadable".into(), role.clone()), Some(pend(role)));
    }
    match verdict {
        Liveness::Dead(why) => {
            let role = rec_ref.and_then(|r| r.role.clone());
            return match consume_dead(daemon, dir, skid, rec_ref, why) {
                Ok(()) => (mk("dead", why.into(), role), None),
                // 종료 기록을 못 믿음 — 파일을 남기고 미결(seatkeep 은 이미 없으니 예약은 두지 않는다).
                Err(e) => (mk("unresolved", format!("{why}+{e}"), role), None),
            };
        }
        Liveness::Unknown(why) => {
            let role = role_of(rec_ref);
            return (mk("unresolved", why.into(), role.clone()), Some(pend(role)));
        }
        Liveness::Alive => {}
    }
    let Some(rec) = rec.ok().flatten() else {
        // 기록 없는 산 seatkeep(기록 쓰기 실패 등) — 번호를 몰라 입양 못 한다 · 좌석은 건드리지 않는다.
        let role = role_of(None);
        return (mk("unresolved", "no_record_live_keeper".into(), role.clone()), Some(pend(role)));
    };
    let role = rec.role.clone();
    let (Some(pid), Some(start)) = (pid, start_now) else {
        return (mk("unresolved", "no_pid".into(), role.clone()), Some(pend(role)));
    };
    if daemon.surfaces.lock().unwrap_or_else(|e| e.into_inner()).contains_key(&rec.surface_id) {
        return (mk("unresolved", "surface_id_taken".into(), role.clone()), Some(pend(role)));
    }
    let size = portable_pty::PtySize { rows: rec.rows.max(1), cols: rec.cols.max(1), pixel_width: 0, pixel_height: 0 };
    let sock = dir.join(format!("{skid}.sock"));
    let spawned = match crate::seat_proc::adopt_connect(&sock, pid, start, size, skid) {
        Ok(s) => s,
        Err(e) => return (mk("unresolved", format!("connect: {e}"), role.clone()), Some(pend(role))),
    };
    let link = spawned.link();
    let mut rec = rec;
    rec.keeper_pid = pid;
    rec.keeper_start_us = Some(start);
    match daemon.create_surface_core(
        Some(rec.cwd.clone()),
        Some(rec.cmd.clone()),
        Some(rec.title.clone()),
        rec.role.clone(),
        size.rows,
        size.cols,
        &[],
        rec.claude_config_dir.clone(),
        None,
        Some(AdoptSeat { rec, spawned }),
    ) {
        Ok(_) => (mk("adopted", "ok".into(), role), None),
        // 등록 실패 — 붙었던 연결을 끊는다(seatkeep 은 --adoptable 이라 산다 · 다음 조종자를 받을 수 있게) → 예약.
        Err(e) => {
            if let Some(l) = link {
                l.detach();
            }
            (mk("unresolved", format!("register: {e}"), role.clone()), Some(pend(role)))
        }
    }
}

/// 입양 갈래 마무리(생성 함수가 `surfaces` 맵에 넣기 **전**에 부른다) — 기록의 약속 칸을 새 `Surface` 에 되살린다.
/// 세대 카운터는 기록값 그대로(T0 §2-6 · 올리지 않음) · 큐는 잠깐 멈춤(T0 §2-4 대역).
pub(crate) fn apply_record(s: &Surface, rec: &SeatRecord) {
    *s.agent_meta.lock().unwrap_or_else(|e| e.into_inner()) = rec.agent_meta.clone();
    *s.agent_session_id.lock().unwrap_or_else(|e| e.into_inner()) = rec.agent_session_id.clone();
    *s.claude_config_dir.lock().unwrap_or_else(|e| e.into_inner()) = rec.claude_config_dir.clone();
    *s.registered_transcript.lock().unwrap_or_else(|e| e.into_inner()) = rec.registered_transcript.clone();
    *s.repin_anchor.lock().unwrap_or_else(|e| e.into_inner()) = rec.repin_anchor.clone();
    s.agent_epoch.store(rec.agent_epoch, Ordering::SeqCst);
    s.conversation_epoch.store(rec.conversation_epoch, Ordering::SeqCst);
    *s.awakened_at.lock().unwrap_or_else(|e| e.into_inner()) = rec.awakened_at;
    *s.directive_verified.lock().unwrap_or_else(|e| e.into_inner()) = rec.directive_verified;
    *s.pack_reinject.lock().unwrap_or_else(|e| e.into_inner()) = rec.pack_reinject.clone();
    *s.gate_pending.lock().unwrap_or_else(|e| e.into_inner()) = rec.gate_pending.clone();
    *s.queue_paused_until.lock().unwrap_or_else(|e| e.into_inner()) = Some(std::time::Instant::now() + ADOPT_QUEUE_PAUSE);
}

/// 입양 좌석 화면 다시 그리기 — 읽기 스레드가 첫 재생을 다 먹은 **직후**에 부른다(codex T4 1R #8 · 타이머 아님). 크기를 흔들어(SIGWINCH)
/// 전체 화면 프로그램이 스스로 다시 그리게 한다(DESIGN §3-2 ⑤ 크래시 경로). 읽기 스레드를 막지 않게 따로 스레드.
pub(crate) fn nudge_now(s: Arc<Surface>) {
    let _ = std::thread::Builder::new().name(format!("seat-adopt-nudge-{}", s.id)).spawn(move || {
        if !s.exited.load(Ordering::SeqCst) {
            if let Err(e) = crate::repaint::nudge_resize(&s, std::time::Duration::from_millis(200)) {
                eprintln!("[cysd] 입양 좌석 surface:{} 크기 흔들기 실패: {e}", s.id);
            }
        }
    });
}

#[cfg(test)]
#[path = "seat_adopt_tests.rs"]
mod tests;
