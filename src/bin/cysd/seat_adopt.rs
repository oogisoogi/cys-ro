//! 좌석 입양(T4 · TICKET=cysr-1116-seatkeep-1119 · 설계 = `docs/seatkeep/T4-DESIGN.md` · holder DESIGN §3-2 ③ · T0 §3).
//!
//! 노브 `CYS_SEATKEEP_ADOPT=1`(+ `CYS_SEATKEEP=1`) 일 때만 일한다 — 끔이면 이 파일의 어떤 함수도 파일·소켓에 닿지 않는다.
//!
//! 하는 일 셋:
//! ① **좌석 기록**(`record_surface`·`record_all`): seatkeep 경유 좌석마다 cysd 가 아는 신원·약속(T0 ⓑ — 번호·역할·명령·폴더·에이전트·
//!    세션·계정 폴더·각성 시각 …)을 seatkeep 상태 폴더의 `<seatkeep id>.cysd.json` 에 원자 쓰기한다. 생성 직후 1회 + `persist_topology`
//!    마다(역할 claim·메타·세션 등록이 모두 그 길을 지난다). 좌석 토큰은 **쓰지 않는다**(비편입 계약 · `governance.rs` P1 · T5 몫).
//! ② **기동 입양**(`adopt_on_boot`): 데몬 시작 잠금을 잡은 뒤 · 소켓 accept 전(main.rs 호출 자리) — 기록마다 seatkeep 등록부를 대조하고
//!    (단계 `committed` · pid 생존 · 출생 시각 일치) 그 소켓에 조종자로 붙어(`seat_proc::adopt_connect`) 같은 번호의 `Surface` 로 다시
//!    등록한다(`Daemon::create_surface_core` 의 입양 갈래 — 생성과 같은 길 · 자식을 띄우지 않음). 결과 = 입양됨 · 죽음 확인(기록 정리) ·
//!    미결(살아 있는데 붙지 못함).
//! ③ **복원 막기(T1 최소 대역 · 이 파일 한 곳)**: 입양된 역할은 accept 전에 `roles` 맵에 들어가므로 phoenix·`cys restore` 가 「가동 중」으로
//!    보고 건너뛴다(별도 장치 없음). 미결이 하나라도 있으면 그 기동의 자동 복원을 통째로 보류한다(`restore_should_hold`) — 살아 있는
//!    좌석의 대화를 새 좌석이 이어 쓰는(작성자 둘) 길을 닫는 보수 처분. ★T1(작성자 하나 · 대화 소유 임대)이 들어오면 **`restore_should_hold`
//!    한 함수만** 그 임대 판정으로 갈아끼운다(부르는 자리 = main.rs `spawn_auto_restore` 1곳).

use crate::state::{Daemon, Surface};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::path::{Path, PathBuf};
use std::sync::atomic::Ordering;
use std::sync::{Arc, Mutex};

/// 좌석 기록 파일 꼬리(seatkeep 의 `<id>.json` 등록부와 구별 — seatkeep 은 이 이름을 보지 않는다).
pub(crate) const RECORD_SUFFIX: &str = ".cysd.json";
/// 기록 형식 판.
const RECORD_SCHEMA: u32 = 1;
/// 입양 직후 큐 배달을 멈추는 시간 — 꼬리 재생·크기 흔들기로 화면이 다시 그려진 뒤 초안 관문(화면 판정)이 판단하게(T0 §2-4).
pub(crate) const ADOPT_QUEUE_PAUSE: std::time::Duration = std::time::Duration::from_secs(3);

/// cysd 가 좌석마다 남기는 신원·약속(T0 ⓑ 중 입양에 쓰는 것). 모르는 칸은 None/기본값 — 추측으로 채우지 않는다.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub(crate) struct SeatRecord {
    pub schema: u32,
    pub skid: String,
    pub sock: String,
    pub keeper_pid: u32,
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
    /// 기록 시각(진단).
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

/// 좌석 하나의 기록 경로(seatkeep 소켓 옆).
fn record_path(link: &crate::seat_proc::SeatLink) -> Option<PathBuf> {
    link.sock().parent().map(|d| d.join(format!("{}{RECORD_SUFFIX}", link.skid())))
}

/// 살아 있는 seatkeep 좌석의 지금 신원·약속으로 기록을 만든다(순수 · 잠금은 필드마다 짧게).
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

/// 좌석 하나를 기록한다(끝난 좌석 = 기록 삭제). 노브 끔·직접 PTY 좌석 = 아무것도 안 함.
pub(crate) fn record_surface(s: &Surface) {
    if !enabled() {
        return;
    }
    let Some(link) = s.seat_link.as_deref() else { return };
    let Some(path) = record_path(link) else { return };
    if s.exited.load(Ordering::SeqCst) {
        let _ = std::fs::remove_file(&path);
        return;
    }
    let rec = snapshot(s, link);
    let Ok(text) = serde_json::to_string(&rec) else { return };
    let (Some(dir), Some(name)) = (path.parent(), path.file_name().and_then(|n| n.to_str())) else { return };
    if let Err(e) = crate::governance::write_json_atomic(dir, name, &text) {
        eprintln!("[cysd] 좌석 기록 쓰기 실패 surface:{} ({}): {e} — 이 좌석은 cysd 가 죽으면 입양되지 못할 수 있다", s.id, path.display());
    }
}

/// 전 좌석 기록(`persist_topology` 가 부른다 — 신원·약속이 바뀌는 모든 자리가 그 길을 지난다).
pub(crate) fn record_all(daemon: &Daemon) {
    if !enabled() {
        return;
    }
    let list: Vec<Arc<Surface>> = daemon.surfaces.lock().unwrap_or_else(|e| e.into_inner()).values().cloned().collect();
    for s in list {
        record_surface(&s);
    }
}

// ─────────────────────────────── 기동 입양 ───────────────────────────────

/// 등록부 대조 결과(순수 판정 — 시험 대상).
#[derive(Debug, PartialEq, Eq)]
pub(crate) enum Liveness {
    /// 붙어 볼 만하다(단계 committed · pid 생존 · 출생 시각 일치).
    Alive,
    /// 확실히 끝났다(등록부 없음·끝난 단계·pid 없음·출생 시각 다름 = pid 재사용) — 기록 정리 대상.
    Dead(&'static str),
    /// 판정 불가(등록부 읽기·해석 실패 · 출생 시각 판독 불가) — 미결.
    Unknown(&'static str),
}

/// seatkeep 등록부(`<id>.json`) 값 + 지금 관측(그 pid 의 생존·출생 시각)으로 판정.
pub(crate) fn judge(rec: &SeatRecord, registry: Option<&serde_json::Value>, alive: bool, start_us_now: Option<u64>) -> Liveness {
    let Some(r) = registry else { return Liveness::Dead("registry_missing") };
    let phase = r["phase"].as_str().unwrap_or("");
    match phase {
        "committed" => {}
        "prepare" => return Liveness::Dead("never_committed"),
        "" => return Liveness::Unknown("registry_unparsable"),
        _ => return Liveness::Dead("ended"),
    }
    if r["pid"].as_u64() != Some(rec.keeper_pid as u64) {
        return Liveness::Dead("pid_mismatch");
    }
    if !alive {
        return Liveness::Dead("keeper_gone");
    }
    match (r["start_us"].as_u64(), start_us_now) {
        (Some(a), Some(b)) if a == b => Liveness::Alive,
        (Some(_), Some(_)) => Liveness::Dead("pid_reused"),
        _ => Liveness::Unknown("start_unreadable"),
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

fn pid_alive(pid: u32) -> bool {
    #[cfg(unix)]
    {
        pid > 0 && (unsafe { libc::kill(pid as i32, 0) } == 0 || std::io::Error::last_os_error().raw_os_error() == Some(libc::EPERM))
    }
    #[cfg(not(unix))]
    {
        let _ = pid;
        false
    }
}

/// 한 좌석의 입양 결과.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub(crate) struct Outcome {
    pub skid: String,
    pub surface_id: Option<u64>,
    /// adopted · dead · unresolved
    pub result: &'static str,
    pub reason: String,
}

/// 이 기동의 입양 요약(복원 막기 판정 · `system` 조회용).
#[derive(Debug, Default, Clone, Serialize)]
pub(crate) struct BootSummary {
    pub ran: bool,
    pub outcomes: Vec<Outcome>,
}

static SUMMARY: Mutex<Option<BootSummary>> = Mutex::new(None);

/// 마지막 기동 입양 요약.
pub(crate) fn summary() -> BootSummary {
    SUMMARY.lock().unwrap_or_else(|e| e.into_inner()).clone().unwrap_or_default()
}

/// ★T1 최소 대역(갈아끼울 자리 = 이 함수 하나): 이 기동에서 자동 복원을 통째로 보류할 까닭. 미결 좌석이 있으면 Some.
/// 입양된 좌석은 여기서 막지 않는다 — accept 전에 `roles` 에 들어가 phoenix·`cys restore` 의 「가동 중」 판정이 건너뛴다.
pub(crate) fn restore_should_hold() -> Option<String> {
    let s = summary();
    let unresolved: Vec<&Outcome> = s.outcomes.iter().filter(|o| o.result == "unresolved").collect();
    if unresolved.is_empty() {
        return None;
    }
    Some(format!(
        "seat_adopt_unresolved: 살아 있으나 입양하지 못한 좌석 {}개({}) — 그 대화를 새 좌석이 이어 쓰지 않게 자동 복원을 보류한다(T1 전 대역)",
        unresolved.len(),
        unresolved.iter().map(|o| o.skid.as_str()).collect::<Vec<_>>().join(",")
    ))
}

/// 죽음이 확인된 좌석의 파일 정리 — cysd 기록 + seatkeep 등록부·잠금·소켓·종료 기록. 교체 기록(`.log`)은 사후 적발 장치라 남긴다.
fn cleanup_dead(dir: &Path, skid: &str) {
    for ext in [RECORD_SUFFIX, ".json", ".lock", ".sock", ".exit"] {
        let _ = std::fs::remove_file(dir.join(format!("{skid}{ext}")));
    }
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
        let mut names: Vec<String> = match std::fs::read_dir(&dir) {
            Ok(rd) => rd.filter_map(|e| e.ok()).filter_map(|e| e.file_name().into_string().ok()).filter(|n| n.ends_with(RECORD_SUFFIX)).collect(),
            Err(_) => Vec::new(),
        };
        names.sort();
        for name in names {
            let skid = name.trim_end_matches(RECORD_SUFFIX).to_string();
            let out = adopt_one(daemon, &dir, &skid);
            eprintln!("[cysd] 좌석 입양 {skid}: {} ({})", out.result, out.reason);
            daemon.bus.publish(
                if out.result == "adopted" { "seat.adopted" } else { "seat.adopt_skipped" },
                "surface",
                out.surface_id,
                json!({"skid": out.skid, "result": out.result, "reason": out.reason,
                       "surface_ref": out.surface_id.map(cys::surface_ref)}),
            );
            summary.outcomes.push(out);
        }
    }
    *SUMMARY.lock().unwrap_or_else(|e| e.into_inner()) = Some(summary);
}

#[cfg(target_os = "macos")]
fn adopt_one(daemon: &Arc<Daemon>, dir: &Path, skid: &str) -> Outcome {
    let mk = |surface_id: Option<u64>, result: &'static str, reason: String| Outcome { skid: skid.to_string(), surface_id, result, reason };
    let rec_path = dir.join(format!("{skid}{RECORD_SUFFIX}"));
    let rec: SeatRecord = match std::fs::read_to_string(&rec_path).ok().and_then(|t| serde_json::from_str(&t).ok()) {
        Some(r) => r,
        None => return mk(None, "unresolved", "record_unreadable".into()),
    };
    if rec.schema != RECORD_SCHEMA || rec.skid != skid {
        return mk(Some(rec.surface_id), "unresolved", format!("record_schema {} / skid {}", rec.schema, rec.skid));
    }
    let registry: Option<serde_json::Value> = match std::fs::read_to_string(dir.join(format!("{skid}.json"))) {
        Ok(t) => Some(serde_json::from_str(&t).unwrap_or(serde_json::Value::Null)),
        Err(_) => None,
    };
    let verdict = judge(&rec, registry.as_ref(), pid_alive(rec.keeper_pid), process_start_us(rec.keeper_pid));
    match verdict {
        Liveness::Dead(why) => {
            cleanup_dead(dir, skid);
            return mk(Some(rec.surface_id), "dead", why.into());
        }
        Liveness::Unknown(why) => return mk(Some(rec.surface_id), "unresolved", why.into()),
        Liveness::Alive => {}
    }
    if daemon.surfaces.lock().unwrap_or_else(|e| e.into_inner()).contains_key(&rec.surface_id) {
        return mk(Some(rec.surface_id), "unresolved", "surface_id_taken".into());
    }
    let size = portable_pty::PtySize { rows: rec.rows.max(1), cols: rec.cols.max(1), pixel_width: 0, pixel_height: 0 };
    let spawned = match crate::seat_proc::adopt_connect(Path::new(&rec.sock), rec.keeper_pid, size, skid) {
        Ok(s) => s,
        Err(e) => return mk(Some(rec.surface_id), "unresolved", format!("connect: {e}")),
    };
    let id = rec.surface_id;
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
        Ok(s) => mk(Some(s.id), "adopted", "ok".into()),
        Err(e) => mk(Some(id), "unresolved", format!("register: {e}")),
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

/// 입양 직후 화면 다시 그리기 — 꼬리 재생이 끝나면 크기를 흔들어(SIGWINCH) 전체 화면 프로그램이 스스로 다시 그리게 한다(DESIGN §3-2 ⑤ 크래시 경로).
pub(crate) fn nudge_after_replay(s: Arc<Surface>) {
    let _ = std::thread::Builder::new().name(format!("seat-adopt-nudge-{}", s.id)).spawn(move || {
        std::thread::sleep(std::time::Duration::from_millis(300));
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
