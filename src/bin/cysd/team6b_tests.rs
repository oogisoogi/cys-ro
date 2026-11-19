//! (조각 6b · TICKET=cysr-1116-s6-1119) 팀별 기계 장치 — RPC·배달 수준 회귀 핀(P2-DESIGN §16-2 ⑦~⑩ · §11 6b 수용 기준).
//!
//! 수용 기준(설계 §11 6b 행) ↔ 검체:
//!   ① 한 팀 폭주 시 다른 팀 보고 `queue_full` 0         → t7_share_*
//!   ② 상한 넘는 create 거절                              → t8_*
//!   ③ 정지 중 그 팀 큐 배달 0(다른 팀 그대로)            → t9_*
//!   ④ 묶음 = 꼬리표 단 기계 문안만(그 밖 즉시 원문)      → t10_*
//! 좌석 = 실 PTY(`sleep 30`) · 팀 = 명시 묶음(`Surface.group`) · 발신 = caller_cache 로 결속한 synthetic pid(return_absorb_tests 와 같은 꼴).
#![cfg(test)]

use crate::governance::deliver_head_locked;
use crate::handlers::{dispatch, Reply};
use crate::state::{Daemon, Surface};
use cys::Request;
use serde_json::{json, Value};
use std::sync::atomic::Ordering;
use std::sync::{Arc, MutexGuard};

struct Fx {
    daemon: Arc<Daemon>,
    dir: std::path::PathBuf,
    _g: MutexGuard<'static, ()>,
}

impl Drop for Fx {
    fn drop(&mut self) {
        for s in self.daemon.surfaces.lock().unwrap().values() {
            let mut child = s.child.lock().unwrap();
            let _ = child.kill();
            let _ = child.wait();
        }
        std::env::remove_var(cys::pack::ENV_PACK_DIR);
        crate::team::set_team_worker_limit_for_thread(None);
        let _ = std::fs::remove_dir_all(&self.dir);
    }
}

fn fx(tag: &str) -> Fx {
    let g = crate::governance::PACK_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    crate::delivery::tests::isolate_state_dir_for_thread(tag);
    static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let n = SEQ.fetch_add(1, Ordering::Relaxed);
    let dir = std::env::temp_dir().join(format!("cys-6b-{tag}-{}-{n}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(dir.join("acl.json"), r#"{"default":"allow","rules":[]}"#).unwrap();
    std::env::set_var(cys::pack::ENV_PACK_DIR, &dir);
    let daemon = Daemon::new(dir.join("cysd.sock"));
    crate::agent_write::set_test_sync_settle(true);
    Fx { daemon, dir, _g: g }
}

/// 좌석 1개(역할 · 팀 = 명시 묶음) + 그 좌석으로 해석되는 발신 pid.
fn pane(fx: &Fx, role: &str, team: Option<&str>, pid: u32) -> Arc<Surface> {
    let s = fx.daemon.create_surface(None, Some("sleep 30".into()), None, Some(role.into()), 24, 80).expect("create surface");
    crate::governance::test_wait_seat_runs(&s, "sleep", &["30"]);
    fx.daemon.surfaces.lock().unwrap().insert(s.id, s.clone());
    if let Some(t) = team {
        *s.group.lock().unwrap() = Some(Some(t.to_string()));
    }
    bind(fx, pid, s.id);
    s
}

fn bind(fx: &Fx, pid: u32, sid: u64) {
    fx.daemon.caller_cache.lock().unwrap().insert(
        pid,
        crate::state::CallerCacheEntry::new(Some(sid), crate::state::now_epoch(), None, fx.daemon.caller_gen.load(Ordering::Relaxed)),
    );
}

fn rpc(fx: &Fx, pid: Option<u32>, method: &str, params: Value) -> Value {
    let req = Request { id: json!(7), method: method.into(), params };
    let Reply::Single(resp) = dispatch(&fx.daemon, req, pid) else { panic!("expected single reply") };
    resp
}

fn queued(fx: &Fx, pid: u32, to: &Arc<Surface>, text: &str, kind: Option<&str>) -> Value {
    let mut p = json!({"surface_id": to.id, "text": text, "queued": true, "quiet": true});
    if let Some(k) = kind {
        p["kind"] = json!(k);
    }
    rpc(fx, Some(pid), "surface.send_text", p)
}

fn texts(s: &Arc<Surface>) -> Vec<String> {
    s.pending_queue.lock().unwrap().iter().map(|e| e.text.clone()).collect()
}

/// 틱 1회(비강제 · 간격 시계 초기화 — 연속 배달을 한 검체 안에서 재려고).
fn tick(fx: &Fx, s: &Arc<Surface>) -> Option<String> {
    *s.last_queue_delivery_at.lock().unwrap() = None;
    deliver_head_locked(&fx.daemon, s, false, false, None, None, None, None).map(|d| d.body.clone())
}

const P: u32 = 996_600;

// ─────────────────────────── ⑦ 팀별 대기열 몫 ───────────────────────────

/// 한 팀이 마스터 좌석 큐 몫(기본 30)을 채우면 **그 팀만** `queue_full_team` · 다른 팀은 계속 들어간다(수용 ①).
#[test]
fn t7_share_rejects_only_the_flooding_team() {
    let fx = fx("share");
    let m = pane(&fx, "master", None, P);
    let _a = pane(&fx, "worker-1", Some("a"), P + 1);
    let _b = pane(&fx, "worker-2", Some("b"), P + 2);
    let share = crate::team::TEAM_QUEUE_SHARE_DEFAULT;
    for i in 0..share {
        let r = queued(&fx, P + 1, &m, &format!("a 보고 {i}"), None);
        assert_eq!(r["ok"], json!(true), "몫 안({i}): {r}");
    }
    let over = queued(&fx, P + 1, &m, "a 넘침", None);
    assert_eq!(over["error"]["code"], json!("queue_full_team"), "몫을 넘긴 팀 = 거절: {over}");
    let b = queued(&fx, P + 2, &m, "b 보고", None);
    assert_eq!(b["ok"], json!(true), "다른 팀은 막히지 않는다(queue_full 0): {b}");
    assert_eq!(texts(&m).len(), share + 1);
    assert!(fx.daemon.bus.tail(200).iter().any(|e| e["name"] == "team.queue_full" && e["payload"]["team"] == "a"), "사건 1건");
}

/// 팀 1개(다른 팀 좌석 없음)면 몫은 발효하지 않는다 — 지금 동작(전체 100) 그대로(회귀 0).
#[test]
fn t7_share_inert_with_a_single_team() {
    let fx = fx("share1");
    let m = pane(&fx, "master", None, P + 10);
    let _a = pane(&fx, "worker-1", Some("a"), P + 11);
    for i in 0..crate::team::TEAM_QUEUE_SHARE_DEFAULT + 5 {
        let r = queued(&fx, P + 11, &m, &format!("a {i}"), None);
        assert_eq!(r["ok"], json!(true), "팀 1개 = 몫 없음({i}): {r}");
    }
}

/// 워커 좌석으로 가는 큐는 몫과 무관(마스터 좌석 큐에만).
#[test]
fn t7_share_only_on_master_queue() {
    let fx = fx("share2");
    let _m = pane(&fx, "master", None, P + 20);
    let a = pane(&fx, "worker-1", Some("a"), P + 21);
    let _b = pane(&fx, "worker-2", Some("b"), P + 22);
    for i in 0..crate::team::TEAM_QUEUE_SHARE_DEFAULT + 2 {
        let r = queued(&fx, P + 22, &a, &format!("b→a {i}"), None);
        assert_eq!(r["ok"], json!(true), "워커 대상({i}): {r}");
    }
}

// ─────────────────────────── ⑧ 팀별 도우미 수 상한 ───────────────────────────

/// 상한(이 스레드 1)을 넘는 그 팀 worker create = `team_worker_limit_exceeded` · 다른 팀 폴더 = 통과 · 상한 0 = 무제한(수용 ②).
#[test]
fn t8_team_worker_limit_denies_only_that_team() {
    let fx = fx("cap");
    let da = fx.dir.join("teamA");
    let db = fx.dir.join("teamB");
    std::fs::create_dir_all(&da).unwrap();
    std::fs::create_dir_all(&db).unwrap();
    let w = fx.daemon.create_surface(Some(da.to_string_lossy().into_owned()), Some("sleep 30".into()), None, Some("worker".into()), 24, 80).unwrap();
    fx.daemon.surfaces.lock().unwrap().insert(w.id, w.clone());
    let create = |cwd: &std::path::Path| rpc(&fx, Some(992_601), "surface.create", json!({"cmd": "sleep 30", "role": "worker", "cwd": cwd.to_string_lossy()}));
    crate::team::set_team_worker_limit_for_thread(Some(1));
    let r = create(&da);
    assert_eq!(r["error"]["code"], json!("team_worker_limit_exceeded"), "같은 팀 2번째 = 거절: {r}");
    let r = create(&db);
    assert_ne!(r["error"]["code"], json!("team_worker_limit_exceeded"), "다른 팀은 상한 밖: {r}");
    // 명시 group 파라미터가 폴더보다 먼저
    let r = rpc(&fx, Some(992_602), "surface.create", json!({"cmd": "sleep 30", "role": "worker", "cwd": db.to_string_lossy(), "group": "teamA"}));
    assert_eq!(r["error"]["code"], json!("team_worker_limit_exceeded"), "group = teamA: {r}");
    crate::team::set_team_worker_limit_for_thread(Some(0));
    let r = create(&da);
    assert_ne!(r["error"]["code"], json!("team_worker_limit_exceeded"), "상한 0 = 무제한: {r}");
}

// ─────────────────────────── ⑨ 팀 정지 스위치 ───────────────────────────

/// 정지된 팀이 마스터에게 넣은 큐 항목은 보류 · 다른 팀 항목은 그 뒤에서 먼저 배달 · 재개하면 순서대로(수용 ③).
#[test]
fn t9_pause_holds_team_items_without_blocking_others() {
    let fx = fx("pause");
    let me = std::process::id();
    let m = pane(&fx, "master", None, P + 30);
    bind(&fx, me, m.id); // 호출자 = master 좌석(surface.set_group 과 같은 게이트)
    let _a = pane(&fx, "worker-1", Some("a"), P + 31);
    let _b = pane(&fx, "worker-2", Some("b"), P + 32);
    let r = rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": true}));
    assert_eq!(r["result"]["changed"], json!(true), "{r}");
    assert_eq!(queued(&fx, P + 31, &m, "A1", None)["ok"], json!(true));
    assert_eq!(queued(&fx, P + 31, &m, "A2", None)["ok"], json!(true));
    assert_eq!(queued(&fx, P + 32, &m, "B1", None)["ok"], json!(true));
    assert_eq!(tick(&fx, &m), None, "머리 = 정지 팀 → 재배치 틱은 배달 0");
    assert_eq!(texts(&m), vec!["B1", "A1", "A2"], "다른 팀이 앞으로 · 팀 안 순서 유지");
    assert_eq!(tick(&fx, &m).as_deref(), Some("B1"), "다른 팀 배달");
    assert_eq!(tick(&fx, &m), None, "남은 것 = 전부 정지 팀 → 배달 0");
    assert_eq!(texts(&m), vec!["A1", "A2"]);
    let r = rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": false}));
    assert_eq!(r["result"]["changed"], json!(true));
    let body = tick(&fx, &m).expect("재개 뒤 배달");
    assert!(body.contains("A1") && body.contains("A2") && body.find("A1") < body.find("A2"), "재개 = 순서대로: {body}");
    assert!(fx.daemon.bus.tail(200).iter().any(|e| e["name"] == "team.paused"));
    assert!(fx.daemon.bus.tail(200).iter().any(|e| e["name"] == "team.resumed"));
}

/// 정지된 팀 좌석으로 가는 큐 배달 = 동결 · 다른 팀 좌석은 그대로 · 강제 배달(운영자 지목)은 통과.
#[test]
fn t9_pause_freezes_delivery_to_team_seats() {
    let fx = fx("freeze");
    let me = std::process::id();
    let m = pane(&fx, "master", None, P + 40);
    bind(&fx, me, m.id);
    let a = pane(&fx, "worker-1", Some("a"), P + 41);
    let b = pane(&fx, "worker-2", Some("b"), P + 42);
    assert_eq!(queued(&fx, P + 40, &a, "to-a", None)["ok"], json!(true));
    assert_eq!(queued(&fx, P + 40, &b, "to-b", None)["ok"], json!(true));
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": true}));
    assert_eq!(tick(&fx, &a), None, "정지 팀 좌석 = 배달 0");
    assert_eq!(tick(&fx, &b).as_deref(), Some("to-b"), "다른 팀 좌석 = 배달");
    *a.last_queue_delivery_at.lock().unwrap() = None;
    assert!(deliver_head_locked(&fx.daemon, &a, true, false, None, None, None, None).is_some(), "강제 배달 = 통과");
}

/// 호출자 게이트 — 워커 좌석에서는 정지 못 한다 · 빈 이름 = 잘못된 인자.
#[test]
fn t9_pause_caller_gate_and_params() {
    let fx = fx("pausegate");
    let me = std::process::id();
    let w = pane(&fx, "worker-1", Some("a"), P + 50);
    bind(&fx, me, w.id);
    let r = rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": true}));
    assert_eq!(r["error"]["code"], json!("forbidden"), "{r}");
    assert!(!fx.daemon.teams.is_paused("a"));
    let r = rpc(&fx, Some(me), "surface.group_pause", json!({"group": " ", "paused": true}));
    assert_eq!(r["error"]["code"], json!("invalid_params"), "{r}");
}

// ─────────────────────────── ⑩ 【진행】 보고 묶음 ───────────────────────────

/// 꼬리표 단 기계 문안만 10분 창으로 묶여 1건 · 급한 머리표·꼬리표 없음 = 즉시 원문(수용 ④).
#[test]
fn t10_progress_items_bundle_after_the_window() {
    let fx = fx("bundle");
    let m = pane(&fx, "master", None, P + 60);
    let _a = pane(&fx, "worker-1", Some("a"), P + 61);
    let _b = pane(&fx, "worker-2", Some("b"), P + 62);
    assert_eq!(queued(&fx, P + 61, &m, "진행 1", Some("progress"))["ok"], json!(true));
    assert_eq!(queued(&fx, P + 61, &m, "진행 2", Some("progress"))["ok"], json!(true));
    assert_eq!(queued(&fx, P + 62, &m, "B 완료", None)["ok"], json!(true));
    assert_eq!(queued(&fx, P + 61, &m, "【막힘】 빌드가 멈췄어요", Some("progress"))["ok"], json!(true));
    assert_eq!(tick(&fx, &m), None, "머리 = 안 풀린 【진행】 → 재배치");
    assert_eq!(texts(&m), vec!["B 완료", "【막힘】 빌드가 멈췄어요", "진행 1", "진행 2"]);
    assert_eq!(tick(&fx, &m).as_deref(), Some("B 완료"), "꼬리표 없음 = 즉시");
    assert_eq!(tick(&fx, &m).as_deref(), Some("【막힘】 빌드가 멈췄어요"), "급한 머리표 = 꼬리표가 있어도 즉시");
    assert_eq!(tick(&fx, &m), None, "창 전 = 묶음 보류");
    for e in m.pending_queue.lock().unwrap().iter_mut() {
        e.enqueued_at -= crate::team::PROGRESS_BUNDLE_SECS_DEFAULT as f64 + 1.0;
    }
    let body = tick(&fx, &m).expect("창이 차면 1건");
    assert!(body.starts_with("【진행 묶음】 a 2건"), "{body}");
    assert!(body.find("진행 1") < body.find("진행 2"), "원문 순서 보존: {body}");
    assert!(texts(&m).is_empty(), "두 항목이 한 번에 나감");
}

/// 팀 1개면 꼬리표가 있어도 묶지 않는다(즉시) — 지금 동작 그대로.
#[test]
fn t10_progress_not_bundled_with_a_single_team() {
    let fx = fx("bundle1");
    let m = pane(&fx, "master", None, P + 70);
    let _a = pane(&fx, "worker-1", Some("a"), P + 71);
    assert_eq!(queued(&fx, P + 71, &m, "진행 x", Some("progress"))["ok"], json!(true));
    assert_eq!(tick(&fx, &m).as_deref(), Some("진행 x"));
}

// ─────────────────────────── team.stats ───────────────────────────

/// 팀별 계기 — 살아 있는 worker 수 · 일하는 좌석 수 · 마스터 좌석 큐에 넣은 시각 · 정지 목록.
#[test]
fn team_stats_reports_per_team_counters() {
    let fx = fx("stats");
    let me = std::process::id();
    let m = pane(&fx, "master", None, P + 80);
    bind(&fx, me, m.id);
    let a = pane(&fx, "worker-1", Some("a"), P + 81);
    let _b = pane(&fx, "worker-2", Some("b"), P + 82);
    *a.agent_status.lock().unwrap() = Some(crate::state::AgentStatus { state: "working".into(), context_pct: None, task: None, updated_at: crate::state::now_epoch() });
    queued(&fx, P + 81, &m, "a1", None);
    queued(&fx, P + 81, &m, "a2", None);
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "b", "paused": true}));
    let r = rpc(&fx, None, "team.stats", json!({}));
    let teams = r["result"]["teams"].as_array().expect("teams");
    let ta = teams.iter().find(|t| t["team"] == "a").expect("a");
    assert_eq!(ta["live_workers"], json!(1));
    assert_eq!(ta["working"], json!(1));
    assert_eq!(ta["report_ts"].as_array().unwrap().len(), 2);
    let tb = teams.iter().find(|t| t["team"] == "b").expect("b");
    assert_eq!(tb["report_ts"].as_array().unwrap().len(), 0);
    assert_eq!(r["result"]["paused"], json!(["b"]));
    assert_eq!(r["result"]["distinct"], json!(2));
}
