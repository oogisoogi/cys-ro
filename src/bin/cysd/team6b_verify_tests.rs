//! (독립 검증 · TICKET=cysr-1116-s6-verify-1119) 조각 6b 반례 시험 — 검증 좌석 작성(VERDICT M1·M2·m3·m5·i7 재현).
//! (고침 · master#c4bc0244) 정식 시험 모듈로 편입 — 결함을 단언하던 V2·V5·V6·V7·V8 은 **고친 동작**을 단언하도록 바꿨다
//!   (각 시험 머리 주석 「바꿈:」 줄). V1·V1b·V3·V3b·V4·V8b 는 원문 그대로(기록된 동작 · 대조). V9·V10 = m4·m6 고침 핀(새로 씀).
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
        let _ = std::fs::remove_dir_all(&self.dir);
    }
}
fn fx(tag: &str) -> Fx {
    let g = crate::governance::PACK_ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    crate::delivery::tests::isolate_state_dir_for_thread(tag);
    static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let n = SEQ.fetch_add(1, Ordering::Relaxed);
    let dir = std::env::temp_dir().join(format!("cys-6bv-{tag}-{}-{n}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(dir.join("acl.json"), r#"{"default":"allow","rules":[]}"#).unwrap();
    std::env::set_var(cys::pack::ENV_PACK_DIR, &dir);
    let daemon = Daemon::new(dir.join("cysd.sock"));
    crate::agent_write::set_test_sync_settle(true);
    Fx { daemon, dir, _g: g }
}
/// role None 허용 · team None = 명시 묶음 없음(생성 폴더 = cwd).
fn pane2(fx: &Fx, role: Option<&str>, team: Option<&str>, cwd: Option<String>, pid: u32) -> Arc<Surface> {
    let s = fx.daemon.create_surface(cwd, Some("sleep 30".into()), None, role.map(str::to_string), 24, 80).expect("create surface");
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
fn tick(_fx: &Fx, s: &Arc<Surface>) -> Option<String> {
    *s.last_queue_delivery_at.lock().unwrap() = None;
    deliver_head_locked(&_fx.daemon, s, false, false, None, None, None, None).map(|d| d.body.clone())
}
const P: u32 = 997_700;

/// V1 — 팀 1개(작업 좌석 기준)여도 「리뷰어 좌석」이 다른 폴더면 팀 2개로 세어 ⑦ 몫(30)이 발효하는가.
#[test]
fn v1_reviewer_seat_in_other_folder_makes_multi() {
    let fx = fx("v1");
    let m = pane2(&fx, Some("master"), None, None, P);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 1);
    let rv = fx.dir.join("reviewdir");
    std::fs::create_dir_all(&rv).unwrap();
    let _r = pane2(&fx, Some("reviewer-codex"), None, Some(rv.to_string_lossy().into_owned()), P + 2);
    let mut first_err = None;
    for i in 0..40 {
        let r = queued(&fx, P + 1, &m, &format!("a {i}"), None);
        if r["ok"] != json!(true) {
            first_err = Some((i, r["error"]["code"].clone()));
            break;
        }
    }
    eprintln!("V1 first_err = {first_err:?} · distinct = {}", crate::team::distinct_teams(&crate::team::snapshot(&fx.daemon)));
    assert_eq!(first_err, Some((30, json!("queue_full_team"))), "리뷰어 좌석 1개로 팀 2개 판정 → 단일 작업팀이 30에서 막힘");
}

/// V1b — 역할 없는 셸 좌석(사람이 연 터미널)도 팀으로 센다.
#[test]
fn v1b_roleless_shell_counts_as_team() {
    let fx = fx("v1b");
    let _m = pane2(&fx, Some("master"), None, None, P + 10);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 11);
    let sh = fx.dir.join("shelldir");
    std::fs::create_dir_all(&sh).unwrap();
    let _s = pane2(&fx, None, None, Some(sh.to_string_lossy().into_owned()), P + 12);
    let d = crate::team::distinct_teams(&crate::team::snapshot(&fx.daemon));
    eprintln!("V1b distinct = {d}");
    assert_eq!(d, 2, "역할 없는 셸 좌석 = 팀 1개로 셈");
}

/// V2 — 【진행】 묶음은 같은 발신자 병합의 글자 상한(queue_digest_max_chars 기본 4000)을 지키는가.
#[test]
fn v2_bundle_respects_digest_char_cap() {
    let fx = fx("v2");
    let m = pane2(&fx, Some("master"), None, None, P + 20);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 21);
    let _b = pane2(&fx, Some("worker-2"), Some("b"), None, P + 22);
    let long = "가".repeat(1500);
    for i in 0..5 {
        assert_eq!(queued(&fx, P + 21, &m, &format!("진행{i} {long}"), Some("progress"))["ok"], json!(true));
    }
    for e in m.pending_queue.lock().unwrap().iter_mut() {
        e.enqueued_at -= crate::team::PROGRESS_BUNDLE_SECS_DEFAULT as f64 + 1.0;
    }
    let body = tick(&fx, &m).expect("묶음 배달");
    let n = body.chars().count();
    eprintln!("V2 bundle chars = {n} · left = {}", texts(&m).len());
    // 대조: 꼬리표 없는 같은 발신자 병합
    let m2 = pane2(&fx, Some("master"), None, None, P + 23);
    // m2 는 두 번째 master 좌석 — 대상 역할 master 이므로 계획은 같다. 꼬리표 없이 5건.
    for i in 0..5 {
        queued(&fx, P + 21, &m2, &format!("보통{i} {long}"), None);
    }
    let body2 = tick(&fx, &m2).expect("병합 배달");
    eprintln!("V2 plain merge chars = {} · left = {}", body2.chars().count(), texts(&m2).len());
    assert!(n <= 4000, "묶음 본문 {n}자 > 4000(병합 상한 우회)");
    // 바꿈(고침 M1): 이월 확인 — 같은 발신자 병합과 같은 2건(3,0xx자)만 싣고 나머지는 자르지 않고 남긴다.
    //   (이 검체의 `sleep` 좌석은 긴 본문 배달을 확정하지 않아 큐가 그대로 남는다 — 이어진 배달은 team.rs 단위 시험이 핀.)
    assert!(body.contains("진행0 ") && body.contains("진행1 "), "머리 + 다음 1건");
    for i in 2..5 {
        assert!(!body.contains(&format!("진행{i} ")), "진행{i} = 다음 배달로 이월");
    }
    assert!(body.starts_with("【진행 묶음】 a 2건"), "묶음 머리 = 실린 건수");
    assert_eq!(texts(&m).len(), 5, "큐에서 잘린 항목 0(유실 0)");
    assert!(texts(&m).iter().all(|t| t.chars().count() == long.chars().count() + 4), "원문 그대로");
}

/// V3 — 팀 1개 · 정지 없음: 배달 본문 = 기존 render_queue_digest 와 바이트 같음 · 병합 수 같음.
#[test]
fn v3_single_team_body_byte_identical() {
    let fx = fx("v3");
    let m = pane2(&fx, Some("master"), None, None, P + 30);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 31);
    let ts = ["첫 보고", "둘째 보고 【진행】", "셋째"];
    for t in ts {
        assert_eq!(queued(&fx, P + 31, &m, t, Some("progress"))["ok"], json!(true));
    }
    let from = m.pending_queue.lock().unwrap().front().unwrap().from.clone();
    let body = tick(&fx, &m).expect("배달");
    let want = cys::paste_fence::sanitize_owned(crate::governance::render_queue_digest(from.as_deref(), &ts.iter().map(|s| s.to_string()).collect::<Vec<_>>()));
    assert_eq!(body.as_bytes(), want.as_bytes(), "팀 1개 = 기존 병합 본문 그대로");
}

/// V4 — 정지된 팀이 보낸 급한 머리표(【막힘】)도 보류되는가(설계 = 그 팀 큐 보류 · 급한 머리표 예외 없음).
#[test]
fn v4_paused_team_urgent_is_held() {
    let fx = fx("v4");
    let me = std::process::id();
    let m = pane2(&fx, Some("master"), None, None, P + 40);
    bind(&fx, me, m.id);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 41);
    let _b = pane2(&fx, Some("worker-2"), Some("b"), None, P + 42);
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": true}));
    queued(&fx, P + 41, &m, "【막힘】 빌드 멈춤", None);
    let r = tick(&fx, &m);
    eprintln!("V4 tick = {r:?} · queue = {:?}", texts(&m));
    assert_eq!(r, None, "정지 팀의 【막힘】도 보류");
}

/// V5 — 「ceo」 역할 좌석은 고정 좌석으로 빠지지 않아 팀 정지로 그 좌석 큐 배달이 얼 수 있는가.
/// 바꿈(고침 i7): ceo = 마스터급 고정 좌석(팀 아님) → 묶음 이름이 정지돼도 그 좌석 큐는 배달된다.
#[test]
fn v5_ceo_role_seat_is_fixed_not_frozen_by_team_pause() {
    let fx = fx("v5");
    let me = std::process::id();
    let m = pane2(&fx, Some("master"), None, None, P + 50);
    bind(&fx, me, m.id);
    let c = pane2(&fx, Some("ceo"), Some("a"), None, P + 51);
    let _b = pane2(&fx, Some("worker-2"), Some("b"), None, P + 52);
    queued(&fx, P + 52, &c, "to-ceo", None);
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": true}));
    let r = tick(&fx, &c);
    eprintln!("V5 tick = {r:?}");
    assert_eq!(r.as_deref(), Some("to-ceo"), "ceo 좌석 = 고정 좌석 → 팀 정지로 얼지 않음");
}

/// V6 — 묶음이 다른 팀 사이의 들어온 순서를 뒤집는가(p1 · b1 · p2 → p1+p2 먼저 · b1 뒤).
/// 바꿈(고침 m5): 묶음 = 머리에서 이어진 구간만 → 첫 배달 = p1 만 · 둘째 = b1 · 셋째 = p2(b1 을 앞지르지 않음).
#[test]
fn v6_bundle_keeps_other_team_fifo() {
    let fx = fx("v6");
    let m = pane2(&fx, Some("master"), None, None, P + 60);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 61);
    let _b = pane2(&fx, Some("worker-2"), Some("b"), None, P + 62);
    queued(&fx, P + 61, &m, "p1", Some("progress"));
    queued(&fx, P + 62, &m, "b1", None);
    queued(&fx, P + 61, &m, "p2", Some("progress"));
    for e in m.pending_queue.lock().unwrap().iter_mut() {
        e.enqueued_at -= crate::team::PROGRESS_BUNDLE_SECS_DEFAULT as f64 + 1.0;
    }
    let first = tick(&fx, &m).expect("first");
    let second = tick(&fx, &m);
    let third = tick(&fx, &m);
    eprintln!("V6 first = {first:?} · second = {second:?} · third = {third:?}");
    assert!(first.contains("p1") && !first.contains("p2") && !first.contains("b1"), "첫 배달 = 이어진 【진행】 p1 만: {first:?}");
    assert_eq!(second.as_deref(), Some("b1"), "b1 은 앞지름 당하지 않는다");
    assert!(third.as_deref().is_some_and(|t| t.contains("p2")), "셋째 = p2: {third:?}");
    assert!(texts(&m).is_empty());
}

// ───── 이 좌석(계정2 재기동) 추가 반례 ─────

/// V3b — 팀 2개 · 정지 없음 · 꼬리표 없음: 본문 = 기존 render_queue_digest 와 바이트 같음.
#[test]
fn v3b_two_teams_plain_body_byte_identical() {
    let fx = fx("v3b");
    let m = pane2(&fx, Some("master"), None, None, P + 70);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 71);
    let _b = pane2(&fx, Some("worker-2"), Some("b"), None, P + 72);
    let ts = ["하나", "둘 【완료】", "셋"];
    for t in ts {
        assert_eq!(queued(&fx, P + 71, &m, t, None)["ok"], json!(true));
    }
    let from = m.pending_queue.lock().unwrap().front().unwrap().from.clone();
    let body = tick(&fx, &m).expect("배달");
    let want = cys::paste_fence::sanitize_owned(crate::governance::render_queue_digest(from.as_deref(), &ts.iter().map(|s| s.to_string()).collect::<Vec<_>>()));
    assert_eq!(body.as_bytes(), want.as_bytes(), "팀 2개라도 꼬리표 없음 = 기존 병합 본문 그대로");
}

/// V7 — 마스터 좌석 승계(migrate_seat_queue 와 같은 이관: drain_active_except_inflight → 새 좌석 push_back) 뒤
///      정지된 팀의 보류 항목이 새 마스터 좌석에서 그대로 배달되는가(꼬리표는 옛 좌석 id 에 묶여 있다).
/// 바꿈(고침 m3): 꼬리표 = 항목 id 로 묶임 → 승계 뒤에도 정지 팀 항목은 보류 · 재개하면 새 마스터 좌석에 1회 배달.
#[test]
fn v7_master_succession_keeps_team_tags_and_pause() {
    let fx = fx("v7");
    let me = std::process::id();
    let m1 = pane2(&fx, Some("master"), None, None, P + 80);
    bind(&fx, me, m1.id);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 81);
    let _b = pane2(&fx, Some("worker-2"), Some("b"), None, P + 82);
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": true}));
    assert_eq!(queued(&fx, P + 81, &m1, "정지 팀 보고", None)["ok"], json!(true));
    assert_eq!(tick(&fx, &m1), None, "승계 전 = 보류(대조)");
    let m2 = pane2(&fx, None, None, None, P + 83);
    let drained = crate::governance::drain_active_except_inflight(&m1);
    assert_eq!(drained.len(), 1);
    {
        let mut nq = m2.pending_queue.lock().unwrap();
        for e in drained {
            nq.push_back(e);
        }
    }
    *m1.role.lock().unwrap() = None;
    *m2.role.lock().unwrap() = Some("master".into());
    let r = tick(&fx, &m2);
    eprintln!("V7 after succession tick = {r:?} · paused = {:?}", fx.daemon.teams.paused_list());
    assert_eq!(r, None, "승계 뒤에도 정지 팀 항목 = 보류(꼬리표가 항목을 따라감)");
    // 청소 틱이 지나도 꼬리표는 남는다(새 좌석 큐에 살아 있음).
    crate::governance::queue_expiry_pass(&fx.daemon);
    crate::governance::queue_expiry_pass(&fx.daemon);
    assert_eq!(tick(&fx, &m2), None, "청소 2회 뒤에도 보류");
    bind(&fx, me, m2.id); // 정지를 푸는 사람 = 새 마스터 좌석(옛 좌석은 역할을 잃어 호출자 게이트 밖)
    let rr = rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": false}));
    assert_eq!(rr["result"]["changed"], json!(true), "{rr}");
    assert_eq!(tick(&fx, &m2).as_deref(), Some("정지 팀 보고"), "재개 = 새 마스터 좌석에 배달");
}

/// V8 — 팀 정지 중에는 TTL 이 멈추는가(system.pause 는 pause 크레딧을 준다). 7시간 정지 → 기본 TTL 6h.
/// 바꿈(고침 M2): 팀 정지 = system.pause 와 같은 크레딧 → 7시간 정지 뒤에도 만료 0 · 큐에 남음.
#[test]
fn v8_team_pause_gets_ttl_credit() {
    let fx = fx("v8");
    let me = std::process::id();
    let m = pane2(&fx, Some("master"), None, None, P + 90);
    bind(&fx, me, m.id);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 91);
    let _b = pane2(&fx, Some("worker-2"), Some("b"), None, P + 92);
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": true}));
    assert_eq!(queued(&fx, P + 91, &m, "정지 중 보고", None)["ok"], json!(true));
    let now = crate::state::now_epoch();
    let seven_h = 7.0 * 3600.0;
    for e in m.pending_queue.lock().unwrap().iter_mut() {
        e.enqueued_at -= seven_h;
    }
    // 정지가 걸린 시각부터 7시간 뒤 첫 틱이라고 놓는다(첫 틱은 delta 0 이므로 prev 를 7h 전으로).
    *fx.daemon.queue_tick_at.lock().unwrap() = Some(now - seven_h);
    crate::governance::queue_expiry_pass(&fx.daemon);
    let left = texts(&m);
    let expired = m.expired_queue.lock().unwrap().len();
    eprintln!("V8 team-pause: left = {left:?} · expired = {expired}");
    assert_eq!((left.len(), expired), (1, 0), "팀 정지 7h = 크레딧으로 생존(system.pause 와 같음)");
}

/// V8b — 대조: 같은 7시간을 system.pause(데몬 정지)로 보내면 크레딧으로 살아남는다.
#[test]
fn v8b_system_pause_control_keeps_entry() {
    let fx = fx("v8b");
    let m = pane2(&fx, Some("master"), None, None, P + 95);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 96);
    let _b = pane2(&fx, Some("worker-2"), Some("b"), None, P + 97);
    assert_eq!(queued(&fx, P + 96, &m, "데몬 정지 중 보고", None)["ok"], json!(true));
    let now = crate::state::now_epoch();
    let seven_h = 7.0 * 3600.0;
    for e in m.pending_queue.lock().unwrap().iter_mut() {
        e.enqueued_at -= seven_h;
    }
    fx.daemon.paused.store(true, Ordering::Relaxed);
    *fx.daemon.queue_tick_at.lock().unwrap() = Some(now - seven_h);
    crate::governance::queue_expiry_pass(&fx.daemon);
    fx.daemon.paused.store(false, Ordering::Relaxed);
    let left = texts(&m);
    let expired = m.expired_queue.lock().unwrap().len();
    eprintln!("V8b system-pause: left = {left:?} · expired = {expired}");
    assert_eq!((left.len(), expired), (1, 0), "system.pause = 크레딧으로 생존(대조)");
}

// ───── 고침 핀(master#c4bc0244 · 새로 씀) ─────

/// V8c — 팀 정지 크레딧의 범위: 정지된 팀 **좌석으로 가는** 큐(좌석 동결)도 크레딧 · 정지 안 된 팀 항목은 크레딧 0(종전 그대로 만료).
#[test]
fn v8c_team_pause_credit_scope() {
    let fx = fx("v8c");
    let me = std::process::id();
    let m = pane2(&fx, Some("master"), None, None, P + 100);
    bind(&fx, me, m.id);
    let a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 101);
    let _b = pane2(&fx, Some("worker-2"), Some("b"), None, P + 102);
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": true}));
    assert_eq!(queued(&fx, P + 100, &a, "마스터 → 정지 팀 좌석", None)["ok"], json!(true));
    assert_eq!(queued(&fx, P + 102, &m, "정지 안 된 팀 b 보고", None)["ok"], json!(true));
    let now = crate::state::now_epoch();
    let seven_h = 7.0 * 3600.0;
    for s in [&a, &m] {
        for e in s.pending_queue.lock().unwrap().iter_mut() {
            e.enqueued_at -= seven_h;
        }
    }
    *fx.daemon.queue_tick_at.lock().unwrap() = Some(now - seven_h);
    crate::governance::queue_expiry_pass(&fx.daemon);
    assert_eq!((texts(&a).len(), a.expired_queue.lock().unwrap().len()), (1, 0), "정지 팀 좌석 큐 = 크레딧");
    assert_eq!((texts(&m).len(), m.expired_queue.lock().unwrap().len()), (0, 1), "정지 안 된 팀 = 크레딧 0(종전대로 만료)");
}

/// V9(고침 m4) — 데몬 재시작은 정지를 되살리지 않고, 정지가 있었으면 사건 `team.pause_lost` **1건**을 낸다(다음 재시작엔 0).
#[test]
fn v9_restart_announces_lost_pause_once() {
    let fx = fx("v9");
    let me = std::process::id();
    let m = pane2(&fx, Some("master"), None, None, P + 110);
    bind(&fx, me, m.id);
    let file = crate::team::paused_file(&fx.daemon);
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "b", "paused": true}));
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "b", "paused": false}));
    assert!(!file.exists(), "정지 0 = 파일 없음");
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "a", "paused": true}));
    rpc(&fx, Some(me), "surface.group_pause", json!({"group": "z", "paused": true}));
    assert!(file.exists(), "정지 목록 파일");
    let lost = |d: &Arc<Daemon>| d.bus.tail(500).into_iter().filter(|e| e["name"] == crate::team::EV_PAUSE_LOST).collect::<Vec<_>>();
    assert!(lost(&fx.daemon).is_empty(), "켜져 있는 동안 = 사건 0");
    let d2 = Daemon::new(fx.dir.join("cysd.sock"));
    let ev = lost(&d2);
    assert_eq!(ev.len(), 1, "재시작 = 사건 정확히 1건: {ev:?}");
    assert_eq!(ev[0]["payload"]["teams"], json!(["a", "z"]));
    assert_eq!(ev[0]["payload"]["reason"], json!("daemon_restart"));
    assert!(d2.teams.paused_list().is_empty(), "정지는 되살리지 않음");
    assert!(!file.exists(), "알린 뒤 파일 지움");
    let d3 = Daemon::new(fx.dir.join("cysd.sock"));
    assert!(lost(&d3).is_empty(), "한 번 알린 정지는 다음 재시작에 다시 안 알림");
}

/// V10(고침 m6) — 【진행】 항목이 그 팀 몫(30)을 채워도 급한 머리표 항목은 들어간다 · 급하지 않은 것은 `queue_full_team`.
#[test]
fn v10_urgent_item_exempt_from_team_share() {
    let fx = fx("v10");
    let m = pane2(&fx, Some("master"), None, None, P + 120);
    let _a = pane2(&fx, Some("worker-1"), Some("a"), None, P + 121);
    let _b = pane2(&fx, Some("worker-2"), Some("b"), None, P + 122);
    for i in 0..crate::team::TEAM_QUEUE_SHARE_DEFAULT {
        assert_eq!(queued(&fx, P + 121, &m, &format!("진행 {i}"), Some("progress"))["ok"], json!(true), "몫 안 {i}");
    }
    let plain = queued(&fx, P + 121, &m, "보통 보고", None);
    assert_eq!(plain["error"]["code"], json!("queue_full_team"), "급하지 않음 = 몫에 걸림: {plain}");
    for mark in crate::team::URGENT_MARKS {
        let r = queued(&fx, P + 121, &m, &format!("{mark} 급한 보고"), None);
        assert_eq!(r["ok"], json!(true), "{mark} = 몫 밖: {r}");
    }
    let r = queued(&fx, P + 121, &m, "【막힘】 꼬리표 달아도", Some("progress"));
    assert_eq!(r["ok"], json!(true), "꼬리표 + 급한 머리표 = 몫 밖: {r}");
}
