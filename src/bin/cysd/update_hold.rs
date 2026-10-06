//! ★1.1.8 U2 — 데몬 쪽 정비 모드 · 보류 로그 · 재생 · 부팅 가드(설계 AUTO-UPDATE-118 §3-3 · §3-11 · 3R 신규 BLOCK 1).
//!
//! - `update.quiesce{txn, ttl_secs}` = 트랜잭션 잠금 소유자 토큰(`txn_id:epoch`)이 맞을 때만 정비 모드 진입 · 좌석 세대 토큰을 돌려준다.
//!   그 동안 사람이 아닌 입력 배달(`surface.send_text`·`surface.send_key` Return·`--queued`)은 보류 로그에 fsync 뒤 ACK(`held:true`) ·
//!   정기 작업 발화 정지. TTL 이 지나면 데몬이 스스로 푼다(러너가 죽어도 함대가 멈춰 있지 않게).
//! - 재생은 워치독 틱이 한다(정비 모드가 아닐 때 · 대상 좌석이 살아 있을 때) — 규칙·원자성 근거 = lib `update::quiesce` 머리 주석.
//! - 부팅 가드: 비종결 저널 + 잠금 쥔 러너 없음 / 저널 손상 → 좌석·세션을 만들기 전에 「복구 대기」 rc 로 끝.

use crate::state::{Daemon, Surface};
use cys::update::{hold, quiesce};
use serde_json::{json, Value};
use std::sync::atomic::Ordering;
use std::sync::{Arc, Mutex, OnceLock};
use std::time::{Duration, Instant};

struct Q {
    txn_id: String,
    epoch: u64,
    gen: u64,
    until: Instant,
    /// 시험 빌드만: 정비 모드를 건 시험 스레드 — 병렬로 도는 다른 시험의 send 가 보류되지 않게(전역 상태 격리).
    #[cfg(test)]
    owner: std::thread::ThreadId,
}

static QUIESCE: Mutex<Option<Q>> = Mutex::new(None);
static GEN: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
static START: OnceLock<Instant> = OnceLock::new();
/// 재생 원장·보류 로그 쓰기를 한 손으로(정비 RPC·배달 훅·틱).
static IO: Mutex<()> = Mutex::new(());

fn start() -> Instant {
    *START.get_or_init(Instant::now)
}

pub fn update_dir() -> Option<std::path::PathBuf> {
    cys::update::buildinfo::state_dir().ok()
}

/// 부팅 가드 — async_main 의 단일 인스턴스 게이트보다 **앞**(부수효과 0). 막히면 rc 75 로 끝.
pub fn boot_guard_or_exit() {
    let Some(dir) = update_dir() else { return };
    if let Some(why) = cys::update::runner::boot_blocked(&dir) {
        eprintln!("[cysd] 갱신 복구 대기 — {why} · 좌석을 만들지 않고 끝낸다(복구기가 종결한 뒤 다시 뜬다)");
        std::process::exit(cys::update::runner::RC_RECOVER_PENDING);
    }
}

/// 정비 모드 중인가(만료면 여기서 푼다).
pub fn quiesced() -> bool {
    let mut g = QUIESCE.lock().unwrap_or_else(|e| e.into_inner());
    match g.as_ref() {
        #[cfg(test)]
        Some(q) if q.owner != std::thread::current().id() => false,
        Some(q) if Instant::now() < q.until => true,
        Some(_) => {
            *g = None;
            eprintln!("[cysd] 정비 모드 TTL 만료 — 스스로 해제(보류 로그는 다음 틱에 배달)");
            false
        }
        None => false,
    }
}

fn seat_tok(s: &Arc<Surface>) -> quiesce::SeatTok {
    let human = s.last_human_input.lock().unwrap().map(|t| t.saturating_duration_since(start()).as_millis() as u64);
    let working = match s.agent_status.lock().unwrap().as_ref() {
        Some(st) => Some(st.state == "working"),
        None if s.agent_meta.lock().unwrap().is_none() => Some(false),
        None => None,
    };
    quiesce::SeatTok {
        surface_id: s.id,
        role: s.role.lock().unwrap().clone(),
        output_gen: s.output_gen.load(Ordering::SeqCst),
        human_input_mono_ms: human,
        pending_input_bytes: s.pending_input_bytes.load(Ordering::Relaxed),
        queue_len: s.pending_queue.lock().unwrap().len() as u64,
        working,
    }
}

fn token(daemon: &Arc<Daemon>, txn_id: &str, gen: u64) -> quiesce::Token {
    let mut seats: Vec<quiesce::SeatTok> =
        daemon.surfaces.lock().unwrap().values().filter(|s| !s.exited.load(Ordering::Relaxed)).map(seat_tok).collect();
    seats.sort_by_key(|s| s.surface_id);
    let hold_seq = update_dir().and_then(|d| hold::last_seq_readonly(&d)).unwrap_or(0);
    quiesce::Token { txn_id: txn_id.to_string(), gen, hold_seq, seats }
}

/// ★2판(codex 1R C2 · 세대 승계): 지금 잠금 소유자로 검증된 토큰이 옛 세대의 정비 세션을 만나면 세션을 그 세대로 넘겨받는다
/// (복구기 = 죽은 러너의 세션을 `update.release` 로 풀 수 있게 — 최대 TTL 까지 남지 않음). 잠금 소유자는 언제나 하나라 옛 세션의
/// 주인은 이미 죽었다. 세션 파일도 같은 세대로 고친다(gen·from_hold_seq 그대로).
fn adopt_session(dir: &std::path::Path, tok: &cys::update::lock::Token) {
    let mut g = QUIESCE.lock().unwrap_or_else(|e| e.into_inner());
    let Some(q) = g.as_mut() else { return };
    if q.txn_id == tok.txn_id && q.epoch == tok.epoch {
        return;
    }
    q.txn_id = tok.txn_id.clone();
    q.epoch = tok.epoch;
    if let Some(mut s) = quiesce::read_json::<quiesce::Session>(dir, quiesce::SESSION_FILE) {
        s.txn_id = tok.txn_id.clone();
        let _ = quiesce::write_json(dir, quiesce::SESSION_FILE, &s);
    }
}

/// `update.*` RPC. Err = (code, message).
pub fn rpc(daemon: &Arc<Daemon>, method: &str, params: &Value) -> Result<Value, (&'static str, String)> {
    let dir = update_dir().ok_or(("update_state_dir", "갱신 상태 폴더 판독 불가".to_string()))?;
    let txn = params.get("txn").and_then(Value::as_str).unwrap_or_default();
    let tok = quiesce::verify_owner_token(&dir, txn).map_err(|e| ("txn_busy", e))?;
    adopt_session(&dir, &tok);
    match method {
        "update.quiesce" => {
            let ttl = params.get("ttl_secs").and_then(Value::as_u64).unwrap_or(quiesce::DEFAULT_TTL_SECS).clamp(60, 3600);
            let gen = GEN.fetch_add(1, Ordering::SeqCst) + 1;
            let from = hold::last_seq_readonly(&dir).ok_or(("hold_log", "보류 로그 판독 불가".to_string()))?;
            quiesce::write_json(&dir, quiesce::SESSION_FILE, &quiesce::Session { txn_id: tok.txn_id.clone(), gen, from_hold_seq: from })
                .map_err(|e| ("io", e))?;
            *QUIESCE.lock().unwrap_or_else(|e| e.into_inner()) =
                Some(Q {
                    txn_id: tok.txn_id.clone(),
                    epoch: tok.epoch,
                    gen,
                    until: Instant::now() + Duration::from_secs(ttl),
                    #[cfg(test)]
                    owner: std::thread::current().id(),
                });
            daemon.bus.publish("update.quiesced", "update", None, json!({"gen": gen, "ttl_secs": ttl}));
            Ok(serde_json::to_value(token(daemon, &tok.txn_id, gen)).unwrap_or(Value::Null))
        }
        "update.seat_token" => {
            let gen = QUIESCE.lock().unwrap_or_else(|e| e.into_inner()).as_ref().filter(|q| q.txn_id == tok.txn_id).map(|q| q.gen).unwrap_or(0);
            Ok(serde_json::to_value(token(daemon, &tok.txn_id, gen)).unwrap_or(Value::Null))
        }
        "update.release" => {
            let mut g = QUIESCE.lock().unwrap_or_else(|e| e.into_inner());
            let was = g.as_ref().map(|q| q.txn_id == tok.txn_id && q.epoch == tok.epoch).unwrap_or(false);
            if was {
                *g = None;
            }
            drop(g);
            daemon.bus.publish("update.released", "update", None, json!({"released": was}));
            Ok(json!({"released": was}))
        }
        _ => Err(("unknown_method", method.to_string())),
    }
}

/// 사람이 아닌 입력 배달을 보류 로그로 돌린다. Some(응답 result) = 보류됨(호출자는 그대로 응답) · None = 정비 모드 아님(평소 경로).
/// 보류 로그 쓰기 실패 = Some(Err) — ACK 없이 「보류 안 됨」 오류(보낸 쪽이 다시 보낸다).
pub fn divert(s: &Arc<Surface>, kind: &str, body: &str) -> Option<Result<Value, String>> {
    if !quiesced() {
        return None;
    }
    let dir = match update_dir() {
        Some(d) => d,
        None => return Some(Err("update_quiesced: 갱신 상태 폴더 판독 불가".into())),
    };
    // 재생 대상 = 역할(재기동 뒤 좌석 id 가 바뀐다 · 큐 WAL 의 재타겟 앵커와 같은 규칙) · 역할 없는 좌석 = 같은 데몬 안 id.
    let target = match s.role.lock().unwrap().clone() {
        Some(r) => format!("role:{r}"),
        None => format!("sid:{}", s.id),
    };
    let _io = IO.lock().unwrap_or_else(|e| e.into_inner());
    let r = hold::HoldLog::open(&dir).and_then(|mut h| h.append(&target, kind, body, now_wall()));
    Some(r.map(|ack| json!({"surface_id": s.id, "held": ack.held, "hold_seq": ack.hold_seq, "queued": true})))
}

fn now_wall() -> i64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0)
}

/// 정기 작업 발화 정지 판정(스케줄러 틱·run_now 게이트).
pub fn schedule_frozen() -> bool {
    quiesced()
}

/// 워치독 틱 — 정비 모드가 아니면 보류 로그 재생 ①(로그 → 배송 큐).
pub fn tick(daemon: &Arc<Daemon>) {
    if quiesced() {
        return;
    }
    let Some(dir) = update_dir() else { return };
    if !dir.join(hold::HOLD_FILE).exists() {
        return;
    }
    let _io = IO.lock().unwrap_or_else(|e| e.into_inner());
    let Some(sess) = quiesce::read_json::<quiesce::Session>(&dir, quiesce::SESSION_FILE) else { return };
    let upto: u64 = quiesce::read_cursor(&dir).unwrap_or(sess.from_hold_seq).max(sess.from_hold_seq);
    let Ok(log) = hold::HoldLog::open(&dir) else { return };
    if log.last_seq() <= upto {
        return;
    }
    let Ok(recs) = log.records_after(upto) else { return };
    let Ok(marks) = quiesce::ledger_marks(&dir) else { return };
    let mut in_queue = std::collections::HashSet::new();
    let surfaces: Vec<Arc<Surface>> = daemon.surfaces.lock().unwrap().values().cloned().collect();
    for s in &surfaces {
        for e in s.pending_queue.lock().unwrap().iter() {
            in_queue.insert(e.id.clone());
        }
    }
    let plan = quiesce::plan_replay(&sess.txn_id, &recs, upto, &in_queue, &marks);
    let mut new_upto = upto;
    let mut pushed = 0usize;
    for r in recs.iter() {
        let id = hold::queue_item_id(&sess.txn_id, r.hold_seq);
        let wanted = plan.iter().any(|p| p.hold_seq == r.hold_seq);
        if wanted {
            let live = surfaces.iter().find(|s| {
                !s.exited.load(Ordering::Relaxed)
                    && match r.target_surface_uuid.split_once(':') {
                        Some(("role", role)) => s.role.lock().unwrap().as_deref() == Some(role),
                        Some(("sid", sid)) => sid.parse::<u64>().ok() == Some(s.id),
                        _ => false,
                    }
            });
            let Some(s) = live else {
                break; // 대상 좌석이 아직 안 떴다(복원 중) — 순서 보존: 여기서 멈추고 다음 틱
            };
            let text = if r.kind == "send-key" { String::new() } else { r.body.clone() };
            let mut e = daemon.next_queue_entry(text, Some("update-hold".into()), quiesce::ORIGIN);
            e.id = id.clone();
            s.pending_queue.lock().unwrap().push_back(e);
            pushed += 1;
        }
        new_upto = r.hold_seq;
    }
    if pushed > 0 {
        daemon.persist_queue_state();
        if !daemon.queue_wal_durable() {
            return; // 큐가 디스크에 안 섰다 — 커서를 올리지 않는다(다음 틱 · id 중복 제거가 지킨다)
        }
        // ACK 재독(§3-3 ①): 큐 파일을 **다시 읽어** 넣은 id 가 전부 있는지 확인한 뒤에만 커서 전진.
        let wal = crate::state::state_dir(&daemon.socket_path).join("queue-state.json");
        let on_disk: std::collections::HashSet<String> = std::fs::read(&wal)
            .ok()
            .and_then(|b| serde_json::from_slice::<Vec<Value>>(&b).ok())
            .map(|rows| rows.iter().filter_map(|r| r["id"].as_str().map(str::to_string)).collect())
            .unwrap_or_default();
        let ok = recs
            .iter()
            .filter(|r| r.hold_seq <= new_upto && plan.iter().any(|p| p.hold_seq == r.hold_seq))
            .all(|r| on_disk.contains(&hold::queue_item_id(&sess.txn_id, r.hold_seq)) || !in_queue_now(&surfaces, &hold::queue_item_id(&sess.txn_id, r.hold_seq)));
        if !ok {
            return;
        }
    }
    if new_upto > upto {
        let _ = quiesce::write_cursor(&dir, new_upto);
        daemon.bus.publish("update.hold_replayed", "update", None, json!({"pushed": pushed, "upto": new_upto}));
    }
}

/// 지금도 메모리 큐에 있는가(이미 배달돼 빠진 항목은 디스크 대조 대상이 아니다).
fn in_queue_now(surfaces: &[Arc<Surface>], id: &str) -> bool {
    surfaces.iter().any(|s| s.pending_queue.lock().unwrap().iter().any(|e| e.id == id))
}

/// 재생 ② 주입 표지 — 주입 직전에 머리부터 이어진 보류 재생 항목 전부(병합 배달에 함께 실릴 수 있는 것)를 원장 `delivering` 으로 적고,
/// 이 값이 사라질 때 [`HoldMark::delivered`] 가 불리지 않았으면 `aborted`(주입 안 됨 = 다음 틱 재시도 허용)로 적는다.
pub struct HoldMark {
    ids: Vec<String>,
    done: bool,
}

impl HoldMark {
    /// 인계 성공 — 실제로 실린 id 는 `delivered` · 표지만 하고 안 실린 것은 `aborted`.
    pub fn delivered(mut self, merged_ids: &[String]) {
        self.done = true;
        if self.ids.is_empty() {
            return;
        }
        let Some(dir) = update_dir() else { return };
        let _io = IO.lock().unwrap_or_else(|e| e.into_inner());
        for id in &self.ids {
            let m = if merged_ids.contains(id) { quiesce::Mark::Delivered } else { quiesce::Mark::Aborted };
            let _ = quiesce::ledger_append(&dir, id, m);
        }
    }
}

impl Drop for HoldMark {
    fn drop(&mut self) {
        if self.done || self.ids.is_empty() {
            return;
        }
        let Some(dir) = update_dir() else { return };
        let _io = IO.lock().unwrap_or_else(|e| e.into_inner());
        for id in &self.ids {
            let _ = quiesce::ledger_append(&dir, id, quiesce::Mark::Aborted);
        }
    }
}

/// 재생 ② 주입 직전 훅(deliver_head_locked 머리). None = 이번엔 주입하지 않는다(원장상 이미 주입했거나 애매 → 큐에서 빼고 보낸 쪽
/// 통지 · 최대 한 번) · Some(표지) = 진행.
/// ★2판(codex 1R C4): 여기서는 `delivering` 을 **쓰지 않는다** — 연속 보류 항목 전부를 선기록하면 선기록 직후 죽을 때 아직 고르지도
/// 주입하지도 않은 뒤 항목까지 재기동 후 `unconfirmed` 로 버려진다. 여기선 이미 표지된 항목(앞 생애의 delivering/delivered)만
/// 연속 보류 구간 **전체**에서 걸러 내고, 실제로 실릴 항목(`merged_ids`)이 정해진 뒤 [`HoldMark::mark_delivering`] 이 그것만 기록한다.
pub fn before_inject(daemon: &Arc<Daemon>, s: &Arc<Surface>) -> Option<HoldMark> {
    let heads: Vec<String> = s
        .pending_queue
        .lock()
        .unwrap()
        .iter()
        .take_while(|e| e.origin == quiesce::ORIGIN)
        .map(|e| e.id.clone())
        .collect();
    if heads.is_empty() {
        return Some(HoldMark { ids: vec![], done: false });
    }
    let dir = update_dir()?;
    let _io = IO.lock().unwrap_or_else(|e| e.into_inner());
    let marks = quiesce::ledger_marks(&dir).ok()?; // 원장 판독 불가 = 애매 → 주입 안 함
    let stale: Vec<(String, Option<quiesce::Mark>)> =
        heads.iter().filter(|id| !quiesce::may_inject(marks.get(*id).copied())).map(|id| (id.clone(), marks.get(id).copied())).collect();
    if stale.is_empty() {
        return Some(HoldMark { ids: vec![], done: false });
    }
    // 이미 delivering/delivered — 다시 보내지 않는다(큐에서 빼고 · delivering 이면 unconfirmed + 보낸 쪽 통지)
    s.pending_queue.lock().unwrap().retain(|e| !stale.iter().any(|(id, _)| *id == e.id));
    for (id, mark) in &stale {
        if *mark == Some(quiesce::Mark::Delivering) {
            let _ = quiesce::ledger_append(&dir, id, quiesce::Mark::Unconfirmed);
            daemon.bus.publish(
                "update.hold_unconfirmed",
                "update",
                Some(s.id),
                json!({"queue_entry_id": id, "hint": "갱신 중 보류된 입력 1건의 배달 여부를 확인할 수 없어 다시 보내지 않았습니다 — 필요하면 다시 보내 주세요"}),
            );
        }
    }
    drop(_io);
    daemon.persist_queue_state();
    None
}

impl HoldMark {
    /// ★2판 C4: 실제로 실릴 보류 항목(`hold_ids` = 병합이 고른 것 중 보류 출처)만 주입 직전에 durable `delivering` 으로 기록한다.
    /// 거짓 = 이번 주입 안 함(원장 판독·기록 실패 · 그사이 다른 경로가 표지함) — 이미 쓴 표지는 drop 이 `aborted` 로 닫는다.
    pub fn mark_delivering(&mut self, hold_ids: &[String]) -> bool {
        if hold_ids.is_empty() {
            return true;
        }
        let Some(dir) = update_dir() else { return false };
        let _io = IO.lock().unwrap_or_else(|e| e.into_inner());
        let Ok(marks) = quiesce::ledger_marks(&dir) else { return false };
        for id in hold_ids {
            if !quiesce::may_inject(marks.get(id).copied()) || quiesce::ledger_append(&dir, id, quiesce::Mark::Delivering).is_err() {
                return false;
            }
            self.ids.push(id.clone());
        }
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn with_dir<T>(tag: &str, f: impl FnOnce(&std::path::Path) -> T) -> T {
        let d = std::env::temp_dir().join(format!("cysd-u2-hold-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        let _l = crate::governance::PACK_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let _g = crate::governance::ReapEnvGuard::set(&[("CYS_UPDATE_STATE_DIR", d.to_str().unwrap())]);
        f(&d)
    }

    #[test]
    fn quiesce_requires_owner_token_holds_sends_and_replays_after_release() {
        with_dir("q", |dir| {
            let sock = dir.join("d");
            std::fs::create_dir_all(&sock).unwrap();
            let daemon = Daemon::new(sock.join("cysd.sock"));
            let s = daemon.create_surface(None, Some("sleep 30".into()), None, None, 24, 80).expect("surface");
            *s.role.lock().unwrap() = Some("worker-x".into());
            daemon.surfaces.lock().unwrap().insert(s.id, s.clone());
            // 토큰 없음·틀림 = 거부
            assert_eq!(rpc(&daemon, "update.quiesce", &json!({"txn": "zz"})).unwrap_err().0, "txn_busy");
            let g = cys::update::lock::acquire(dir, "runner").unwrap();
            let t = g.token().render();
            let tok = rpc(&daemon, "update.quiesce", &json!({"txn": t, "ttl_secs": 600})).unwrap();
            assert_eq!(tok["seats"].as_array().unwrap().len(), 1);
            assert!(quiesced() && schedule_frozen());
            // 정비 모드 중 = 보류(ACK 뒤 내구)
            let r = divert(&s, "send", "안녕").unwrap().unwrap();
            assert_eq!((r["held"].as_bool(), r["hold_seq"].as_u64()), (Some(true), Some(1)));
            assert_eq!(divert(&s, "send", "둘").unwrap().unwrap()["hold_seq"].as_u64(), Some(2));
            assert!(s.pending_queue.lock().unwrap().is_empty(), "보류 중 배달 0");
            tick(&daemon);
            assert!(s.pending_queue.lock().unwrap().is_empty(), "정비 모드 중 재생 0");
            assert_eq!(rpc(&daemon, "update.release", &json!({"txn": t})).unwrap()["released"], true);
            assert!(divert(&s, "send", "x").is_none(), "해제 뒤 = 평소 경로");
            tick(&daemon);
            tick(&daemon); // 두 번 돌려도 한 번만
            let q: Vec<_> = s.pending_queue.lock().unwrap().iter().map(|e| (e.id.clone(), e.text.clone(), e.origin.clone())).collect();
            assert_eq!(q.len(), 2, "{q:?}");
            assert!(q[0].0.starts_with("hold:") && q[0].1 == "안녕" && q[0].2 == quiesce::ORIGIN);
            // 주입 직전 훅: before_inject 는 아무것도 선기록하지 않는다 → 실제로 실린 항목(병합이 첫 건만 골랐다고 치자)만 delivering
            let mut m = before_inject(&daemon, &s).expect("진행");
            assert!(quiesce::ledger_marks(dir).unwrap().is_empty(), "★2판 C4: 고르기 전 선기록 0");
            assert!(m.mark_delivering(&[q[0].0.clone()]));
            std::mem::forget(m); // 주입 도중 죽음(표지 delivering 만 남음)
            assert!(before_inject(&daemon, &s).is_none(), "delivering 남은 항목 = 다시 안 보냄");
            let left: Vec<String> = s.pending_queue.lock().unwrap().iter().map(|e| e.id.clone()).collect();
            assert_eq!(left, vec![q[1].0.clone()], "★2판 C4: 고르지 않은 둘째 건은 unconfirmed 로 버려지지 않는다");
            let mut m2 = before_inject(&daemon, &s).expect("둘째 건 = 주입 가능");
            assert!(m2.mark_delivering(&[q[1].0.clone()]));
            m2.delivered(&[q[1].0.clone()]);
            drop(g);
            let _ = daemon;
        });
        *QUIESCE.lock().unwrap() = None;
    }

    /// ★2판 C2: 러너(세대 1)가 정비 세션을 연 채 죽음 → 복구기가 새 잠금(세대 2)을 잡고 그 토큰으로 `update.release` = 세션이 풀린다
    /// (최대 TTL 까지 남지 않음) · 세션 파일도 새 세대. 옛 토큰은 소유자가 아니라 거부.
    #[test]
    fn recovery_generation_adopts_and_releases_dead_runner_session() {
        with_dir("adopt", |dir| {
            let sock = dir.join("d");
            std::fs::create_dir_all(&sock).unwrap();
            let daemon = Daemon::new(sock.join("cysd.sock"));
            let g1 = cys::update::lock::acquire(dir, "runner").unwrap();
            let t1 = g1.token().render();
            rpc(&daemon, "update.quiesce", &json!({"txn": t1, "ttl_secs": 600})).unwrap();
            assert!(quiesced());
            drop(g1); // 러너 죽음
            let g2 = cys::update::lock::acquire(dir, "recover").unwrap();
            let t2 = g2.token();
            assert_eq!(rpc(&daemon, "update.release", &json!({"txn": t1})).unwrap_err().0, "txn_busy", "옛 세대 거부");
            assert_eq!(rpc(&daemon, "update.release", &json!({"txn": t2.render()})).unwrap()["released"], true);
            assert!(!quiesced());
            let sess: quiesce::Session = quiesce::read_json(dir, quiesce::SESSION_FILE).unwrap();
            assert_eq!(sess.txn_id, t2.txn_id);
            drop(g2);
            let _ = daemon;
        });
        *QUIESCE.lock().unwrap() = None;
    }
}
