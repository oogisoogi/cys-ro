//! ★v112-wake — 감시 이벤트 → 잠든 master 각성 1줄(위험 4군 ③ 「자가치유 전멸」 수리).
//!
//! ## 왜 있나 (09-21 윈 노트북 실기)
//! ↻ 재시작 뒤 worker 입력줄에 [RESTORE] 가 붙기만 하고 미제출 → 300s 뒤 데몬이 `pane.idle` 을
//! 발행했지만, 그 이벤트는 master 자리의 **배경 구독 stdout** 에 쌓였을 뿐이다. master 턴이 없으니
//! 아무도 읽지 않았고, 박사님이 master 에게 말을 걸고서야(사람 손 1) 풀렸다. 신호는 있는데
//! 잠든 master 를 깨우지 못한다 = 자가치유가 사람 손 없이는 0 이다.
//!
//! ## 무엇을 하나
//! master 가 봐야 하는 감시 사건(① role 좌석 입력줄에 미제출 지시가 멈춘 채 유휴 · ② role 좌석의
//! 에이전트 사망)이 나면 master 의 **pending_queue** 에 1줄을 적재한다. 배달은 기존 큐 배달자
//! (`deliver_queued`)가 맡는다 — 그 경로가 이미 「master 입력줄이 비어 있을 때만 · 프롬프트 경계
//! (턴 중이면 대기) · 사람 타이핑 직후 금지 · 빈 좌석 보류」를 강제한다. 배달 뒤에는 입력창을
//! 3상태로 실측하고(제출/미제출/못 잼) 미제출이면 Return 을 **1회만** 다시 보낸다.
//!
//! ## 폭주 방지(이 항목의 절반 — 1.0.1 1분 주기 재주입이 반례)
//! * 이벤트 키 멱등: 같은 사건 키는 두 번 적재하지 않는다.
//! * 최소 간격: master 좌석당 `CYS_WATCH_WAKEUP_MIN_INTERVAL_SECS`(기본 300s).
//! * 시간당 상한: `CYS_WATCH_WAKEUP_HOURLY_CAP`(기본 6).
//! * 미배달 1건 원칙: master 큐에 이 경로의 줄이 아직 남아 있으면(=턴 중·입력 중) 새로 쌓지 않는다.
//! * 1줄 고정: 개행 제거·길이 상한. 디렉티브·스킬 전문 동반 0.
//! * 억제·실패는 조용히: master 입력줄에 아무것도 쓰지 않고 이벤트 원장(`watch_wakeup.*`)에만 남긴다.
//! * `CYS_WATCH_WAKEUP=0` 이면 전면 비활성(종전 동작 = 이벤트만 발행).

use crate::state::Daemon;
use serde_json::json;
use std::collections::{HashMap, VecDeque};
use std::sync::atomic::Ordering;
use std::sync::{Arc, Mutex, OnceLock};

/// 큐 항목 origin·from — 이 경로의 줄을 큐에서 식별하는 유일한 표지.
pub(crate) const ORIGIN: &str = "governance-watch";
const FROM: &str = "cysd-watch";
/// 1줄 상한(문자). 이벤트 요약 + 확인 명령이 들어가기에 충분하고 전문 덤프는 불가능한 크기.
const MAX_CHARS: usize = 200;
/// 배달 뒤 제출 실측까지 기다리는 시간(초) — Inject 의 cr_delay(400ms)+렌더를 넘기는 값.
const PROBE_AFTER_SECS: f64 = 2.0;

fn env_u64(key: &str, default: u64) -> u64 {
    std::env::var(key)
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(default)
}

pub(crate) fn enabled() -> bool {
    std::env::var("CYS_WATCH_WAKEUP").map(|v| v != "0").unwrap_or(true)
}

/// 속도 제한 설정(env 는 호출부가 1회 읽어 넘긴다 — 판정자는 순수).
#[derive(Debug, Clone, Copy)]
pub(crate) struct Limits {
    pub min_interval_secs: f64,
    pub hourly_cap: usize,
}

impl Limits {
    pub(crate) fn from_env() -> Self {
        Limits {
            min_interval_secs: env_u64("CYS_WATCH_WAKEUP_MIN_INTERVAL_SECS", 300) as f64,
            hourly_cap: env_u64("CYS_WATCH_WAKEUP_HOURLY_CAP", 6) as usize,
        }
    }
}

/// 적재 이력 — 프로세스 수명 상태(재기동하면 비어 시작 = 최악이 「한 번 더 깨움」이라 안전 방향).
#[derive(Debug, Default)]
pub(crate) struct WakeState {
    /// 이벤트 키 → 적재 시각. 1시간 넘은 키는 솎는다(24/365 누수 차단).
    seen: HashMap<String, f64>,
    /// 최근 1시간 적재 시각들(시간당 상한 판정).
    recent: VecDeque<f64>,
}

/// 적재 판정 결과 — 억제 사유는 원장에 그대로 남는다(침묵 금지).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Verdict {
    Enqueue,
    Suppress(&'static str),
}

/// ★순수 판정자 — 순서가 계약이다: 멱등(같은 사건) → 미배달 줄 존재 → 최소 간격 → 시간당 상한.
/// 멱등을 맨 앞에 두는 이유: 같은 사건의 재발행은 「간격 때문에 못 넣었다」가 아니라 「이미 넣었다」로
/// 기록돼야 원장이 사실을 말한다.
pub(crate) fn verdict(
    st: &WakeState,
    key: &str,
    pending_in_queue: bool,
    now: f64,
    lim: Limits,
) -> Verdict {
    if st.seen.contains_key(key) {
        return Verdict::Suppress("dup_event");
    }
    if pending_in_queue {
        return Verdict::Suppress("pending_undelivered");
    }
    if let Some(last) = st.recent.back() {
        if now - last < lim.min_interval_secs {
            return Verdict::Suppress("min_interval");
        }
    }
    let in_hour = st.recent.iter().filter(|t| now - **t < 3600.0).count();
    if in_hour >= lim.hourly_cap {
        return Verdict::Suppress("hourly_cap");
    }
    Verdict::Enqueue
}

impl WakeState {
    fn record(&mut self, key: &str, now: f64) {
        self.seen.retain(|_, t| now - *t < 3600.0);
        while self.recent.front().is_some_and(|t| now - *t >= 3600.0) {
            self.recent.pop_front();
        }
        self.seen.insert(key.to_string(), now);
        self.recent.push_back(now);
    }
}

/// 1줄 정규화 — 개행·제어문자를 공백으로, 길이 상한. 1줄이 아니면 다줄 제출(부분 제출)이 된다.
pub(crate) fn one_line(text: &str) -> String {
    let flat: String = text
        .chars()
        .map(|c| if c.is_control() { ' ' } else { c })
        .collect();
    let flat = flat.split_whitespace().collect::<Vec<_>>().join(" ");
    flat.chars().take(MAX_CHARS).collect()
}

/// 제출 실측은 공용 판정기(`cys::submit_probe` — cys CLI 와 같은 술어)를 부른다. 긴 줄은 입력창에서
/// 줄바꿈·잘림이 나므로 sentinel 은 앞 40자로 좁힌다(공백 제거 대조라 줄바꿈에는 강건하다).
fn probe_line(screen: &str, line: &str) -> cys::submit_probe::SubmitProbe {
    let head: String = line.chars().take(40).collect();
    cys::submit_probe::submit_probe(screen, &head).0
}

/// 배달 추적 1건 — 적재 → 배달 관측 → 실측(→ 미제출이면 Return 1회 → 재실측) → 종결.
#[derive(Debug, Clone)]
struct Probe {
    master_sid: u64,
    entry_id: String,
    text: String,
    key: String,
    delivered_at: Option<f64>,
    retried: bool,
}

struct Shared {
    state: WakeState,
    probes: Vec<Probe>,
}

fn shared() -> &'static Mutex<Shared> {
    static S: OnceLock<Mutex<Shared>> = OnceLock::new();
    S.get_or_init(|| {
        Mutex::new(Shared {
            state: WakeState::default(),
            probes: Vec::new(),
        })
    })
}

/// 감시 사건 1건을 master 각성 줄로 적재한다(또는 조용히 억제). 반환 = 적재했는가.
///
/// * `key` — 사건 멱등 키(같은 사건 = 같은 키).
/// * `detected_sid` — 사건이 난 좌석. master 자신이면 적재하지 않는다(자기 입력줄에 자기 사건 금지).
/// ★v115-restore(B4 · 09-22 윈 실기 06:4x 사진): 좌석의 `role` 칸은 **지금 그 역할을 쥐었다는 뜻이 아니다** —
/// `create_surface` 의 latest-wins 는 새 자리에 역할을 주면서 옛 자리의 `role` 칸을 지우지 않는다(승계·claim
/// 경로만 지운다). 그래서 옛 자리 surface:58 이 여전히 `cso` 로 읽혀 「surface:58(cso) 입력줄에 미제출 지시가
/// 303초째」가 master 를 깨웠다(현 cso = 61). 감시 각성은 역할표(`daemon.roles`)가 그 좌석을 가리킬 때만 역할을 준다.
pub(crate) fn role_held_now(daemon: &Daemon, s: &crate::state::Surface) -> Option<String> {
    let role = s.role.lock().unwrap().clone()?;
    (daemon.roles.lock().unwrap().get(&role).copied() == Some(s.id)).then_some(role)
}

pub(crate) fn wake_master(daemon: &Daemon, key: &str, detected_sid: u64, text: &str) -> bool {
    if !enabled() {
        return false;
    }
    let lim = Limits::from_env();
    let now = crate::state::now_epoch();
    let suppress = |why: &str| {
        daemon.bus.publish(
            "watch_wakeup.suppressed",
            "queue",
            None,
            json!({"key": key, "reason": why, "detected_surface_ref": cys::surface_ref(detected_sid)}),
        );
        false
    };
    let Some(master_sid) = daemon.roles.lock().unwrap().get("master").copied() else {
        return suppress("no_master");
    };
    if master_sid == detected_sid {
        return suppress("self");
    }
    let Some(s) = daemon.get_surface(master_sid) else {
        return suppress("no_master");
    };
    if s.exited.load(Ordering::Relaxed) {
        return suppress("master_exited");
    }
    let line = one_line(text);
    let mut sh = shared().lock().unwrap_or_else(|e| e.into_inner());
    let entry = {
        let mut q = s.pending_queue.lock().unwrap();
        let pending = q.iter().any(|e| e.origin == ORIGIN);
        match verdict(&sh.state, key, pending, now, lim) {
            Verdict::Suppress(why) => {
                drop(q);
                drop(sh);
                return suppress(why);
            }
            Verdict::Enqueue => {}
        }
        if q.len() >= 100 {
            drop(q);
            drop(sh);
            return suppress("queue_full");
        }
        let entry = daemon.next_queue_entry(line.clone(), Some(FROM.to_string()), ORIGIN);
        q.push_back(entry.clone());
        (entry, q.len())
    };
    sh.state.record(key, now);
    sh.probes.push(Probe {
        master_sid,
        entry_id: entry.0.id.clone(),
        text: line,
        key: key.to_string(),
        delivered_at: None,
        retried: false,
    });
    drop(sh);
    daemon.bus.publish(
        "queue.enqueued",
        "queue",
        Some(master_sid),
        crate::state::queue_enqueued_payload(&entry.0, entry.1, json!(FROM), None),
    );
    daemon.bus.publish(
        "watch_wakeup.enqueued",
        "queue",
        Some(master_sid),
        json!({"key": key, "queue_entry_id": entry.0.id,
               "detected_surface_ref": cys::surface_ref(detected_sid)}),
    );
    daemon.persist_queue_state();
    true
}

/// 이 경로가 추적 중인 큐 항목인가(배달자가 note_delivered 를 부를지 가르는 값싼 술어).
///
/// ★락 순서 계약: 이 모듈은 `shared()` → `pending_queue` 순서로만 잡는다. 호출자는 `pending_queue`
/// 락을 쥔 채 이 함수·`note_delivered` 를 부르면 안 된다(역순 = 교착).
pub(crate) fn is_tracked(entry_id: &str) -> bool {
    shared()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .probes
        .iter()
        .any(|p| p.entry_id == entry_id)
}

/// 배달 관측 — 큐 배달자가 이 경로의 항목을 실제로 PTY 에 인계한 순간 호출한다.
pub(crate) fn note_delivered(entry_ids: &[String]) {
    let now = crate::state::now_epoch();
    let mut sh = shared().lock().unwrap_or_else(|e| e.into_inner());
    for p in sh.probes.iter_mut() {
        if p.delivered_at.is_none() && entry_ids.iter().any(|id| *id == p.entry_id) {
            p.delivered_at = Some(now);
        }
    }
}

/// watchdog 틱마다 — 배달된 줄의 제출을 실측한다. 미제출이면 Return 1회, 그래도면 원장에만.
pub(crate) fn tick_probes(daemon: &Arc<Daemon>) {
    let now = crate::state::now_epoch();
    let mut done: Vec<(Probe, &'static str)> = Vec::new();
    let mut sh = shared().lock().unwrap_or_else(|e| e.into_inner());
    let mut keep = Vec::new();
    for mut p in std::mem::take(&mut sh.probes) {
        let Some(s) = daemon.get_surface(p.master_sid) else {
            done.push((p, "master_gone"));
            continue;
        };
        let Some(at) = p.delivered_at else {
            // 아직 큐에 있으면 기다린다. 큐에서 사라졌는데 배달 관측이 없으면 clear 로 버려진 것.
            let still = s.pending_queue.lock().unwrap().iter().any(|e| e.id == p.entry_id);
            if still {
                keep.push(p);
            } else {
                done.push((p, "dropped_undelivered"));
            }
            continue;
        };
        if now - at < PROBE_AFTER_SECS {
            keep.push(p);
            continue;
        }
        let screen = s
            .parser
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .screen()
            .contents();
        match probe_line(&screen, &p.text) {
            cys::submit_probe::SubmitProbe::Submitted => done.push((p, "submitted")),
            cys::submit_probe::SubmitProbe::Unmeasured => done.push((p, "unmeasured")),
            cys::submit_probe::SubmitProbe::NotSubmitted if !p.retried => {
                // CR 만 보낸다(본문 재주입 금지 — 재주입은 입력줄에 같은 줄을 두 번 붙인다).
                let _ = s.write_tx.try_send(crate::state::WriteReq::Data(b"\r".to_vec()));
                p.retried = true;
                p.delivered_at = Some(now);
                keep.push(p);
            }
            cys::submit_probe::SubmitProbe::NotSubmitted => done.push((p, "not_submitted")),
        }
    }
    sh.probes = keep;
    drop(sh);
    for (p, verdict) in done {
        daemon.bus.publish(
            "watch_wakeup.submit",
            "queue",
            Some(p.master_sid),
            json!({"key": p.key, "queue_entry_id": p.entry_id, "verdict": verdict,
                   "return_resent": p.retried}),
        );
    }
}

#[cfg(test)]
pub(crate) fn reset_for_test() {
    let mut sh = shared().lock().unwrap_or_else(|e| e.into_inner());
    sh.state = WakeState::default();
    sh.probes.clear();
}

#[cfg(test)]
pub(crate) fn delivered_at_for_test(entry_id: &str) -> Option<f64> {
    shared()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .probes
        .iter()
        .find(|p| p.entry_id == entry_id)
        .and_then(|p| p.delivered_at)
}

#[cfg(test)]
pub(crate) static TEST_LOCK: Mutex<()> = Mutex::new(());

#[cfg(test)]
mod tests {
    use super::*;

    const LIM: Limits = Limits {
        min_interval_secs: 300.0,
        hourly_cap: 6,
    };

    #[test]
    fn same_event_key_enqueues_once() {
        let mut st = WakeState::default();
        assert_eq!(verdict(&st, "k1", false, 1000.0, LIM), Verdict::Enqueue);
        st.record("k1", 1000.0);
        // 간격이 한참 지나도 같은 사건은 다시 넣지 않는다(간격이 아니라 멱등으로 막혀야 한다).
        assert_eq!(verdict(&st, "k1", false, 2000.0, LIM), Verdict::Suppress("dup_event"));
    }

    #[test]
    fn min_interval_blocks_a_different_event_too_soon() {
        let mut st = WakeState::default();
        st.record("k1", 1000.0);
        assert_eq!(verdict(&st, "k2", false, 1299.0, LIM), Verdict::Suppress("min_interval"));
        assert_eq!(verdict(&st, "k2", false, 1300.0, LIM), Verdict::Enqueue);
    }

    #[test]
    fn hourly_cap_blocks_the_seventh() {
        let mut st = WakeState::default();
        let lim = Limits { min_interval_secs: 0.0, hourly_cap: 6 };
        for i in 0..6 {
            let k = format!("k{i}");
            assert_eq!(verdict(&st, &k, false, 100.0 + i as f64, lim), Verdict::Enqueue);
            st.record(&k, 100.0 + i as f64);
        }
        assert_eq!(verdict(&st, "k6", false, 200.0, lim), Verdict::Suppress("hourly_cap"));
        // 1시간 뒤엔 풀린다.
        assert_eq!(verdict(&st, "k6", false, 3800.0, lim), Verdict::Enqueue);
    }

    #[test]
    fn undelivered_line_blocks_a_second_one() {
        let st = WakeState::default();
        assert_eq!(
            verdict(&st, "k1", true, 1000.0, LIM),
            Verdict::Suppress("pending_undelivered")
        );
    }

    #[test]
    fn one_line_strips_newlines_and_caps_length() {
        let s = one_line(&format!("a\nb\r\nc\t{}", "가".repeat(500)));
        assert!(!s.contains('\n') && !s.contains('\r'));
        assert!(s.starts_with("a b c "));
        assert_eq!(s.chars().count(), MAX_CHARS);
    }

    #[test]
    fn probe_line_matches_a_wrapped_long_line_by_its_head() {
        use cys::submit_probe::SubmitProbe as P;
        let line = one_line(&format!("[cys-감시] surface:47(worker) 입력줄에 미제출 지시 {}", "가".repeat(80)));
        // 입력창이 줄을 접어 보여 줘도(공백·개행 삽입) 머리 40자로 잡는다.
        let wrapped: String = line.chars().enumerate().flat_map(|(i, c)| {
            if i % 30 == 29 { vec![c, '\n', ' '] } else { vec![c] }
        }).collect();
        let stuck = format!("위\n────\n❯ {wrapped}\n────\n  상태줄\n");
        assert_eq!(probe_line(&stuck, &line), P::NotSubmitted);
        let sent = format!("> {line}\n● 처리\n────\n❯ \n────\n");
        assert_eq!(probe_line(&sent, &line), P::Submitted);
    }

    // ── 통합: 실제 Daemon · 실제 좌석 · 실제 check_idle 경로 ──────────────────────
    fn drill_daemon(tag: &str) -> Arc<Daemon> {
        static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
        let n = SEQ.fetch_add(1, Ordering::Relaxed);
        let dir = std::env::temp_dir().join(format!(
            "cys-watchwake-{tag}-{}-{}-{n}",
            std::process::id(),
            crate::state::now_epoch() as u64
        ));
        let _ = std::fs::create_dir_all(&dir);
        Daemon::new(dir.join("cysd.sock"))
    }

    fn seat(daemon: &Arc<Daemon>, role: &str) -> Arc<crate::state::Surface> {
        // ★v116-flake-pty ⑵: PTY 고갈(ENXIO)만 상한 재시도 · 넘기면 「PTY 고갈(환경)」 문구로 실패.
        let s = crate::pty_test_support::retry_on_pty_exhaustion("seat", || {
            daemon.create_surface(None, Some("sleep 30".into()), None, Some(role.into()), 24, 80)
        })
        .expect("create surface");
        daemon.roles.lock().unwrap().insert(role.into(), s.id);
        daemon.surfaces.lock().unwrap().insert(s.id, s.clone());
        s
    }

    fn watch_lines(s: &crate::state::Surface) -> Vec<String> {
        s.pending_queue
            .lock()
            .unwrap()
            .iter()
            .filter(|e| e.origin == ORIGIN)
            .map(|e| e.text.clone())
            .collect()
    }

    fn make_idle(s: &crate::state::Surface, secs: u64) {
        *s.last_output.lock().unwrap() = std::time::Instant::now() - std::time::Duration::from_secs(secs);
        s.idle_notified.store(false, Ordering::Relaxed);
    }

    #[test]
    fn stuck_worker_input_wakes_master_once_with_one_line() {
        let _g = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        reset_for_test();
        let d = drill_daemon("stuck");
        let master = seat(&d, "master");
        let worker = seat(&d, "worker");
        // [RESTORE] 가 입력줄에 붙기만 하고 미제출 = 데몬이 쓴 미제출 바이트가 남아 있다.
        worker.pending_input_bytes.store(42, Ordering::Relaxed);
        make_idle(&worker, 400);
        crate::governance::check_idle(&d);
        let lines = watch_lines(&master);
        assert_eq!(lines.len(), 1, "미제출 입력줄 유휴 → master 큐에 정확히 1줄: {lines:?}");
        assert!(!lines[0].contains('\n') && lines[0].chars().count() <= MAX_CHARS);
        assert!(lines[0].contains(&cys::surface_ref(worker.id)) && lines[0].contains("확인"));
        // 같은 사건이 다시 발행돼도(에피소드 재무장 흉내) 주입은 1회로 남는다.
        make_idle(&worker, 400);
        crate::governance::check_idle(&d);
        assert_eq!(watch_lines(&master).len(), 1, "같은 이벤트 2회 → 주입 1회");
    }

    /// ★v115-restore(B4): 같은 역할의 새 자리가 latest-wins 로 역할을 가져간 뒤 옛 자리에 미제출 지시가 남아도
    /// master 를 깨우지 않는다(옛 자리 role 칸은 남아 있다 = 결함 조건 재현) · 대조군 = 새 자리는 깨운다.
    #[test]
    fn stale_role_label_on_old_seat_does_not_wake_master() {
        let _g = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        reset_for_test();
        let d = drill_daemon("stale");
        let master = seat(&d, "master");
        let old = seat(&d, "cso");
        let new = seat(&d, "cso"); // 역할표 cso → new (latest-wins) · old.role 칸은 "cso" 그대로
        assert_eq!(old.role.lock().unwrap().as_deref(), Some("cso"), "결함 조건(옛 자리 role 칸 잔존) 미재현");
        assert_eq!(d.roles.lock().unwrap().get("cso").copied(), Some(new.id));
        old.pending_input_bytes.store(42, Ordering::Relaxed);
        make_idle(&old, 400);
        crate::governance::check_idle(&d);
        assert!(watch_lines(&master).is_empty(), "옛 자리로 master 를 깨웠다: {:?}", watch_lines(&master));
        assert_eq!(role_held_now(&d, &old), None);
        new.pending_input_bytes.store(42, Ordering::Relaxed);
        make_idle(&new, 400);
        crate::governance::check_idle(&d);
        let lines = watch_lines(&master);
        assert_eq!(lines.len(), 1, "현 역할 좌석은 깨워야 한다: {lines:?}");
        assert!(lines[0].contains(&cys::surface_ref(new.id)));
        let src = include_str!("governance.rs");
        assert_eq!(src.matches("crate::watch_wake::role_held_now(daemon, &s)").count(), 2, "각성 2곳 배선");
    }

    #[test]
    fn idle_with_empty_input_or_master_itself_does_not_wake() {
        let _g = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        reset_for_test();
        let d = drill_daemon("quiet");
        let master = seat(&d, "master");
        let worker = seat(&d, "worker");
        make_idle(&worker, 400); // 미제출 0 · 마커 모름 = 정상 대기로 본다
        master.pending_input_bytes.store(9, Ordering::Relaxed);
        make_idle(&master, 400); // master 자신의 유휴는 자기에게 알리지 않는다
        crate::governance::check_idle(&d);
        assert!(watch_lines(&master).is_empty(), "{:?}", watch_lines(&master));
    }

    #[test]
    fn second_distinct_event_inside_interval_is_suppressed_quietly() {
        let _g = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        reset_for_test();
        let d = drill_daemon("interval");
        let master = seat(&d, "master");
        let w = seat(&d, "worker");
        assert!(wake_master(&d, "a", w.id, "첫 사건"));
        // 첫 줄이 배달돼 큐에서 빠졌다고 치자 — 그래도 300s 간격 안의 다른 사건은 막힌다.
        master.pending_queue.lock().unwrap().clear();
        assert!(!wake_master(&d, "b", w.id, "둘째 사건"));
        assert!(watch_lines(&master).is_empty());
        let _ = master;
    }


    /// 배달자가 PTY 에 인계한 감시 줄은 추적 기록에 「배달됨」으로 찍혀야 제출 실측이 돈다
    /// (note_delivered 를 큐 락 밖으로 옮긴 뒤에도 — agy 1R H 수리의 회귀 그물).
    #[test]
    fn delivery_is_noted_so_the_submit_probe_runs() {
        let _g = TEST_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        reset_for_test();
        let d = drill_daemon("noted");
        let master = seat(&d, "master");
        let w = seat(&d, "worker");
        assert!(wake_master(&d, "k", w.id, "배달 기록 시험"));
        let id = master.pending_queue.lock().unwrap().front().unwrap().id.clone();
        assert_eq!(delivered_at_for_test(&id), None);
        let got = crate::governance::deliver_head_locked(&d, &master, true, false, None, None);
        assert!(got.is_some(), "강제 배달이 인계하지 못했다");
        assert!(delivered_at_for_test(&id).is_some(), "배달이 기록되지 않았다 — 제출 실측이 영영 안 돈다");
    }

}
