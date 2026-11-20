//! (조각 6b · codex 1R REJECT 처분 · TICKET=cysr-1116-s6-1119 · master#010efa14) 반례 시험 — B1·M1~M6 (원문 = master/reports/verify/codex-1120/s6-r1.md).
//! 동시성 반례는 장벽·잠 대신 **시험 이음매**(`TeamBook.{enqueue,admit,deliver}_seam` · `cfg!(test)` 일 때만 불림)로 순서를 고정한다 —
//! 고치기 전 코드에서는 결정론으로 붉고, 고친 코드에서는 결정론으로 초록이다(시간 문턱 0 · M4 만 「둘째가 문에 닿는가」 1.5초 상한).
#![cfg(test)]

use crate::governance::deliver_head_locked;
use crate::handlers::{dispatch, Reply};
use crate::state::{Daemon, Surface};
use cys::Request;
use serde_json::{json, Value};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
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
    let dir = std::env::temp_dir().join(format!("cys-6bc-{tag}-{}-{n}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(dir.join("acl.json"), r#"{"default":"allow","rules":[]}"#).unwrap();
    std::env::set_var(cys::pack::ENV_PACK_DIR, &dir);
    let daemon = Daemon::new(dir.join("cysd.sock"));
    crate::agent_write::set_test_sync_settle(true);
    Fx { daemon, dir, _g: g }
}
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
fn rpc_on(d: &Arc<Daemon>, pid: Option<u32>, method: &str, params: Value) -> Value {
    let req = Request { id: json!(7), method: method.into(), params };
    let Reply::Single(resp) = dispatch(d, req, pid) else { panic!("expected single reply") };
    resp
}
fn rpc(fx: &Fx, pid: Option<u32>, method: &str, params: Value) -> Value {
    rpc_on(&fx.daemon, pid, method, params)
}
fn queued_on(d: &Arc<Daemon>, pid: u32, to: u64, text: &str) -> Value {
    rpc_on(d, Some(pid), "surface.send_text", json!({"surface_id": to, "text": text, "queued": true, "quiet": true}))
}
fn texts(s: &Arc<Surface>) -> Vec<String> {
    s.pending_queue.lock().unwrap().iter().map(|e| e.text.clone()).collect()
}
fn tick_on(d: &Arc<Daemon>, s: &Arc<Surface>) -> Option<String> {
    *s.last_queue_delivery_at.lock().unwrap() = None;
    deliver_head_locked(d, s, false, false, None, None, None, None).map(|x| x.body.clone())
}
fn pause(fx: &Fx, pid: u32, team: &str, on: bool) -> Value {
    rpc(fx, Some(pid), "surface.group_pause", json!({"group": team, "paused": on}))
}
fn events(d: &Arc<Daemon>, name: &str) -> Vec<Value> {
    d.bus.tail(500).into_iter().filter(|e| e["name"] == name).collect()
}
fn pending_guard(s: &Arc<Surface>, ids: &[String], claimed: bool) -> Arc<crate::state::InjectGuard> {
    let g = Arc::new(crate::state::InjectGuard::new(None, s.output_gen.clone(), false, None));
    if claimed {
        assert!(g.claim_for_write(), "전제: writer 가 소유권을 집는다");
    }
    *s.inject_reservation.lock().unwrap() = Some(crate::state::InjectReservation { ids: ids.to_vec(), guard: g.clone() });
    g
}
/// 마스터 좌석을 표에서 내린다(승계 없이 사라진 마스터 · 보존소 행이 다른 좌석으로 rehome 되지 않게).
fn drop_seat(fx: &Fx, s: &Arc<Surface>) {
    {
        let mut c = s.child.lock().unwrap();
        let _ = c.kill();
        let _ = c.wait();
    }
    fx.daemon.surfaces.lock().unwrap().remove(&s.id);
    fx.daemon.roles.lock().unwrap().retain(|_, v| *v != s.id);
}
const P: u32 = 998_800;

// ─────────────────────────── B1 · 정지 권한 · 상한 ───────────────────────────

/// B1 반례 — 워커 좌석이 떼어 낸 자식(부모가 launchd/init 로 바뀐 고아 · setsid·이중 fork 와 같은 꼴)은 정지할 수 없다.
///   고치기 전: 조상을 끝까지 읽었더니 좌석이 없다 = 「좌석 밖 사람」 → 통과(남의 팀을 멈춤). 고친 뒤: 능력값 없으면 거절.
///   대조: 같은 고아가 운영자 능력값(operator_token)을 실으면 통과(이 등급의 정직한 경계 · 일부러 0600 파일을 읽어야 함) ·
///   워커 좌석 자신은 능력값을 실어도 거절 · master 좌석은 능력값 없이 통과.
#[test]
fn cb1_detached_worker_child_cannot_pause_a_team() {
    let fx = fx("cb1");
    let pidf = fx.dir.join("orphan.pid");
    let cmd = format!("(sleep 37 & echo $! > '{}'); exec sleep 30", pidf.display());
    let w = fx.daemon.create_surface(None, Some(cmd), None, Some("worker-1".into()), 24, 80).expect("worker seat");
    fx.daemon.surfaces.lock().unwrap().insert(w.id, w.clone());
    *w.group.lock().unwrap() = Some(Some("a".into()));
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(10);
    let orphan: u32 = loop {
        if let Some(p) = std::fs::read_to_string(&pidf).ok().and_then(|t| t.trim().parse().ok()) {
            break p;
        }
        assert!(std::time::Instant::now() < deadline, "고아 자식 pid 파일이 안 생겼다");
        std::thread::sleep(std::time::Duration::from_millis(50));
    };
    // 고아가 된 것(부모 = 1)을 확인한다 — 좌석 조상 체인 밖.
    let ppid = || {
        std::process::Command::new("ps").args(["-o", "ppid=", "-p", &orphan.to_string()]).output().ok().and_then(|o| String::from_utf8_lossy(&o.stdout).trim().parse::<u32>().ok())
    };
    let until = std::time::Instant::now() + std::time::Duration::from_secs(5);
    while ppid() != Some(1) && std::time::Instant::now() < until {
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
    let kill_orphan = || {
        let _ = std::process::Command::new("kill").arg(orphan.to_string()).status();
    };
    if ppid() != Some(1) {
        kill_orphan();
        panic!("전제: 떼어 낸 자식의 부모가 1 이어야 한다(ppid = {:?})", ppid());
    }
    let r = rpc(&fx, Some(orphan), "surface.group_pause", json!({"group": "b", "paused": true}));
    let tok = fx.daemon.operator_token.clone().expect("시험 데몬 operator.token");
    let r_tok = rpc(&fx, Some(orphan), "surface.group_pause", json!({"group": "b", "paused": true, "operator_token": tok}));
    kill_orphan();
    assert_eq!(r["error"]["code"], json!("forbidden"), "떼어 낸 워커 자식 = 거절: {r}");
    assert_eq!(r_tok["result"]["changed"], json!(true), "좌석 밖 + 운영자 능력값 = 통과(경계 기록): {r_tok}");
    assert!(fx.daemon.teams.is_paused("b"));
    // (codex 2R B1 · 감사 줄) 그 정지가 누구·어떤 자격이었는지 사건에 남는다.
    let ev = events(&fx.daemon, crate::team::EV_PAUSED);
    let last = ev.last().expect("team.paused 사건");
    assert_eq!(last["payload"]["via"], json!("operator_token"), "{last}");
    assert_eq!(last["payload"]["caller_pid"], json!(orphan), "{last}");
    assert_eq!(last["payload"]["caller_surface"], json!(null), "좌석 밖 = 좌석 없음: {last}");
    // 워커 좌석 자신 — 능력값을 실어도 거절.
    bind(&fx, P, w.id);
    let tok = fx.daemon.operator_token.clone().unwrap();
    let r = rpc(&fx, Some(P), "surface.group_pause", json!({"group": "b", "paused": false, "operator_token": tok}));
    assert_eq!(r["error"]["code"], json!("forbidden"), "워커 좌석 + 토큰 = 거절: {r}");
    // 틀린 토큰 · 호출자 불명 = 거절.
    let r = rpc(&fx, Some(orphan + 1_000_000), "surface.group_pause", json!({"group": "b", "paused": false, "operator_token": "00"}));
    assert_eq!(r["error"]["code"], json!("forbidden"), "{r}");
    let r = rpc(&fx, None, "surface.group_pause", json!({"group": "b", "paused": false}));
    assert_eq!(r["error"]["code"], json!("forbidden"), "{r}");
    // master 좌석 = 능력값 없이 통과 · 감사 줄 = master_seat + 그 좌석.
    let m = pane(&fx, "master", None, P + 1);
    let r = rpc(&fx, Some(P + 1), "surface.group_pause", json!({"group": "b", "paused": false}));
    assert_eq!(r["result"]["changed"], json!(true), "{r}");
    let ev = events(&fx.daemon, crate::team::EV_RESUMED);
    let last = ev.last().expect("team.resumed 사건");
    assert_eq!(last["payload"]["via"], json!("master_seat"), "{last}");
    assert_eq!(last["payload"]["caller_surface"], json!(m.id), "{last}");
}

/// B1 — 정지 팀 이름 집합 상한(64) · 넘는 **새** 이름만 `team_pause_limit` · 이미 정지된 이름·재개는 받음 · 영속 파일 = 상한 안.
#[test]
fn cb1_paused_team_set_is_bounded() {
    let fx = fx("cb1cap");
    let _m = pane(&fx, "master", None, P + 10);
    for i in 0..crate::team::PAUSED_TEAMS_MAX {
        let r = pause(&fx, P + 10, &format!("t{i:03}"), true);
        assert_eq!(r["result"]["changed"], json!(true), "{i}: {r}");
    }
    let r = pause(&fx, P + 10, "overflow", true);
    assert_eq!(r["error"]["code"], json!(crate::team::TEAM_PAUSE_LIMIT), "상한 넘는 새 이름 = 거절: {r}");
    assert!(!fx.daemon.teams.is_paused("overflow"));
    let r = pause(&fx, P + 10, "t000", true);
    assert_eq!(r["result"]["changed"], json!(false), "이미 정지된 이름 = 받음(변화 없음): {r}");
    assert_eq!(pause(&fx, P + 10, "t000", false)["result"]["changed"], json!(true), "재개 = 늘 받음");
    assert_eq!(pause(&fx, P + 10, "overflow", true)["result"]["changed"], json!(true), "자리가 나면 새 이름 받음");
    let file: Value = serde_json::from_str(&std::fs::read_to_string(crate::team::paused_file(&fx.daemon)).unwrap()).unwrap();
    assert_eq!(file["paused"].as_array().unwrap().len(), crate::team::PAUSED_TEAMS_MAX, "파일 = 집합 그대로(상한 안)");
}

/// B1 — 재시작 때 읽는 정지 목록 파일 상한: 넘으면 이름을 읽지 않고 「목록을 못 읽음」 사건 1건 + 파일 지움 · 이름 수도 상한까지만.
#[test]
fn cb1_restart_pause_file_read_is_bounded() {
    let fx = fx("cb1file");
    let file = crate::team::paused_file(&fx.daemon);
    std::fs::write(&file, "x".repeat(crate::team::PAUSED_FILE_MAX_BYTES as usize + 1)).unwrap();
    let d2 = Daemon::new(fx.dir.join("cysd.sock"));
    let ev = events(&d2, crate::team::EV_PAUSE_LOST);
    assert_eq!(ev.len(), 1, "{ev:?}");
    assert_eq!(ev[0]["payload"]["list_unreadable"], json!(true));
    assert_eq!(ev[0]["payload"]["teams"], json!([]));
    assert!(!file.exists(), "넘친 파일도 지운다");
    let many: Vec<String> = (0..200).map(|i| format!("n{i}")).collect();
    std::fs::write(&file, json!({"paused": many}).to_string()).unwrap();
    let d3 = Daemon::new(fx.dir.join("cysd.sock"));
    let ev = events(&d3, crate::team::EV_PAUSE_LOST);
    assert_eq!(ev[0]["payload"]["teams"].as_array().unwrap().len(), crate::team::PAUSED_TEAMS_MAX, "이름 = 상한까지만");
}

// ─────────────────────────── M1 · 쓰기 직전 팀 정지 ───────────────────────────

/// M1 반례(목적지) — 잠금 밖 팀 판정(Freeze) 뒤 · 인계 전에 그 팀이 정지되면 배달 0.
///   고치기 전: 임계영역 안에 목적지 팀 재확인이 없어 정지 응답 뒤에 배달이 나갔다.
#[test]
fn cm1_pause_after_pre_check_freezes_destination_seat() {
    let fx = fx("cm1dest");
    let m = pane(&fx, "master", None, P + 20);
    let a = pane(&fx, "worker-1", Some("a"), P + 21);
    let _b = pane(&fx, "worker-2", Some("b"), P + 22);
    assert_eq!(queued_on(&fx.daemon, P + 20, a.id, "to-a")["ok"], json!(true));
    let d = fx.daemon.clone();
    let fired = Arc::new(AtomicBool::new(false));
    let f2 = fired.clone();
    *fx.daemon.teams.deliver_seam.lock().unwrap() = Some(Arc::new(move || {
        if !f2.swap(true, Ordering::SeqCst) {
            let r = rpc_on(&d, Some(P + 20), "surface.group_pause", json!({"group": "a", "paused": true}));
            assert_eq!(r["result"]["changed"], json!(true), "{r}");
        }
    }));
    let got = tick_on(&fx.daemon, &a);
    *fx.daemon.teams.deliver_seam.lock().unwrap() = None;
    assert!(fired.load(Ordering::SeqCst), "전제: 이음매가 돌았다");
    assert_eq!(got, None, "정지가 판정 뒤·인계 전에 섰다 = 배달 0");
    assert_eq!(texts(&a), vec!["to-a"], "항목 보존");
    // 임계영역 재확인이 writer 에 넘기기 **전에** 멈췄다 — 넘긴 뒤 탐침이 막았다면 남는 사건(queue.inject_aborted)이 없다.
    assert!(events(&fx.daemon, "queue.inject_aborted").is_empty(), "인계 0(탐침까지 가지 않음)");
    drop(m);
}

/// M1 — 정지 **전환** 순간 결판 대기 인계 예약 취소(system.pause·건강 정지와 같은 꼴) · 다른 팀 예약은 그대로.
#[test]
fn cm1_pause_transition_cancels_pending_reservations() {
    let fx = fx("cm1cancel");
    let m = pane(&fx, "master", None, P + 30);
    let a = pane(&fx, "worker-1", Some("a"), P + 31);
    let b = pane(&fx, "worker-2", Some("b"), P + 32);
    assert_eq!(queued_on(&fx.daemon, P + 30, a.id, "to-a")["ok"], json!(true));
    assert_eq!(queued_on(&fx.daemon, P + 30, b.id, "to-b")["ok"], json!(true));
    assert_eq!(queued_on(&fx.daemon, P + 31, m.id, "A 보고")["ok"], json!(true));
    let ids = |s: &Arc<Surface>| s.pending_queue.lock().unwrap().iter().map(|e| e.id.clone()).collect::<Vec<_>>();
    let ga = pending_guard(&a, &ids(&a), false);
    let gb = pending_guard(&b, &ids(&b), false);
    let gm = pending_guard(&m, &ids(&m), false);
    assert_eq!(pause(&fx, P + 30, "a", true)["result"]["changed"], json!(true));
    assert!(!ga.claim_for_write(), "정지 팀 좌석으로 가던 인계 = 취소");
    assert!(!gm.claim_for_write(), "정지 팀이 마스터에게 넣은 항목을 실은 인계 = 취소");
    assert!(gb.claim_for_write(), "다른 팀 좌석 인계 = 그대로");
    assert!(events(&fx.daemon, "queue.inject_uncancellable").is_empty(), "취소됨 = 사건 0");
}

/// M1 — 이미 writer 가 쓰기로 확정한 인계는 못 끊는다 → 건강 정지와 같은 사건 `queue.inject_uncancellable {reason:"team_pause"}`.
#[test]
fn cm1_claimed_reservation_is_reported_uncancellable() {
    let fx = fx("cm1claimed");
    let m = pane(&fx, "master", None, P + 40);
    let a = pane(&fx, "worker-1", Some("a"), P + 41);
    let _b = pane(&fx, "worker-2", Some("b"), P + 42);
    assert_eq!(queued_on(&fx.daemon, P + 40, a.id, "to-a")["ok"], json!(true));
    let ids: Vec<String> = a.pending_queue.lock().unwrap().iter().map(|e| e.id.clone()).collect();
    let _g = pending_guard(&a, &ids, true);
    pause(&fx, P + 40, "a", true);
    let ev = events(&fx.daemon, "queue.inject_uncancellable");
    assert_eq!(ev.len(), 1, "{ev:?}");
    assert_eq!(ev[0]["payload"]["reason"], json!("team_pause"));
    assert_eq!(ev[0]["payload"]["team"], json!("a"));
    drop(m);
}

/// M1 — writer 안전 탐침의 팀 정지 축(첫 바이트 앞) — 목적지 좌석 팀 · 실린 항목 꼬리표 · 기존 탐침이 막으면 그대로 막음.
#[test]
fn cm1_writer_probe_sees_team_pause() {
    let fx = fx("cm1probe");
    let m = pane(&fx, "master", None, P + 50);
    let a = pane(&fx, "worker-1", Some("a"), P + 51);
    let _b = pane(&fx, "worker-2", Some("b"), P + 52);
    assert_eq!(queued_on(&fx.daemon, P + 51, m.id, "A 보고")["ok"], json!(true));
    let tagged: Vec<String> = m.pending_queue.lock().unwrap().iter().map(|e| e.id.clone()).collect();
    let open: crate::state::SafetyProbe = Arc::new(|| false);
    let shut: crate::state::SafetyProbe = Arc::new(|| true);
    let p_dest = crate::team::with_team_pause_probe(&fx.daemon, &a, vec![], open.clone());
    let p_tag = crate::team::with_team_pause_probe(&fx.daemon, &m, tagged.clone(), open.clone());
    let p_other = crate::team::with_team_pause_probe(&fx.daemon, &m, vec!["q-none".into()], open.clone());
    assert!(!p_dest() && !p_tag() && !p_other(), "정지 전 = 막지 않음");
    assert!(crate::team::with_team_pause_probe(&fx.daemon, &m, vec![], shut)(), "기존 탐침이 막으면 그대로");
    pause(&fx, P + 50, "a", true);
    assert!(p_dest(), "목적지 좌석 팀 정지 = 막음");
    assert!(p_tag(), "정지 팀 꼬리표 항목 = 막음");
    assert!(!p_other(), "꼬리표 없는 항목 = 그대로");
}

/// (codex 2R M1) 반례 — 배달이 목적지 팀(a)을 스냅숏한 뒤 그 좌석이 `surface.set_group` 으로 **이미 정지된** 팀 b 로 옮겨지면 배달 0.
///   고치기 전: 임계영역 재확인·writer 탐침이 스냅숏(a)을 다시 써서 통과 · 정지 전환도 다시 안 돌아 그대로 배달.
#[test]
fn cm1_regroup_into_paused_team_during_delivery_holds() {
    let fx = fx("cm1regroup");
    let m = pane(&fx, "master", None, P + 110);
    let me = std::process::id();
    bind(&fx, me, m.id); // set_group 게이트 = 살아 있는 호출자 pid(master 좌석)
    let a = pane(&fx, "worker-1", Some("a"), P + 111);
    let _b = pane(&fx, "worker-2", Some("b"), P + 112);
    assert_eq!(pause(&fx, P + 110, "b", true)["result"]["changed"], json!(true));
    assert_eq!(queued_on(&fx.daemon, P + 110, a.id, "to-a")["ok"], json!(true));
    let d = fx.daemon.clone();
    let aid = a.id;
    let fired = Arc::new(AtomicBool::new(false));
    let f2 = fired.clone();
    *fx.daemon.teams.deliver_seam.lock().unwrap() = Some(Arc::new(move || {
        if !f2.swap(true, Ordering::SeqCst) {
            let r = rpc_on(&d, Some(me), "surface.set_group", json!({"surface_id": aid, "group": "b"}));
            assert_eq!(r["result"]["changed"], json!(true), "{r}");
        }
    }));
    let got = tick_on(&fx.daemon, &a);
    *fx.daemon.teams.deliver_seam.lock().unwrap() = None;
    assert!(fired.load(Ordering::SeqCst), "전제: 이음매가 돌았다");
    assert_eq!(got, None, "스냅숏 뒤 정지 팀으로 옮겨짐 = 배달 0");
    assert_eq!(texts(&a), vec!["to-a"], "항목 보존");
    assert!(events(&fx.daemon, "queue.inject_aborted").is_empty(), "임계영역에서 멈춤(writer 까지 안 감)");
}

/// (codex 2R M1) 이미 정지된 팀으로 옮긴 순간 — 그 좌석의 결판 대기 예약 취소 · writer 탐침도 그 순간 팀을 다시 읽어 막음.
#[test]
fn cm1_regroup_into_paused_team_cancels_reservation_and_probe_rereads() {
    let fx = fx("cm1regroup2");
    let m = pane(&fx, "master", None, P + 120);
    let me = std::process::id();
    bind(&fx, me, m.id);
    let a = pane(&fx, "worker-1", Some("a"), P + 121);
    let _b = pane(&fx, "worker-2", Some("b"), P + 122);
    pause(&fx, P + 120, "b", true);
    assert_eq!(queued_on(&fx.daemon, P + 120, a.id, "to-a")["ok"], json!(true));
    let ids: Vec<String> = a.pending_queue.lock().unwrap().iter().map(|e| e.id.clone()).collect();
    let g = pending_guard(&a, &ids, false);
    let open: crate::state::SafetyProbe = Arc::new(|| false);
    let probe = crate::team::with_team_pause_probe(&fx.daemon, &a, ids.clone(), open);
    assert!(!probe(), "옮기기 전(팀 a · 정지 아님) = 막지 않음");
    let r = rpc(&fx, Some(me), "surface.set_group", json!({"surface_id": a.id, "group": "b"}));
    assert_eq!(r["result"]["changed"], json!(true), "{r}");
    assert!(!g.claim_for_write(), "정지 팀으로 옮김 = 대기 예약 취소");
    assert!(probe(), "탐침 = 첫 바이트 앞 그 순간 팀(b · 정지)");
}

// ─────────────────────────── M2 · 꼬리표 공개 = 같은 잠금 ───────────────────────────

/// M2 반례 — 넣기 잠금을 놓은 직후(꼬리표를 달기 전 창)에 배달 틱이 돌아도 정지 팀 항목은 보류.
///   고치기 전: 그 창의 머리는 꼬리표가 없어 정지를 무시하고 배달됐다.
#[test]
fn cm2_tick_in_enqueue_window_sees_the_tag() {
    let fx = fx("cm2tick");
    let m = pane(&fx, "master", None, P + 60);
    let _a = pane(&fx, "worker-1", Some("a"), P + 61);
    let _b = pane(&fx, "worker-2", Some("b"), P + 62);
    pause(&fx, P + 60, "a", true);
    let d = fx.daemon.clone();
    let m2 = m.clone();
    let seen: Arc<std::sync::Mutex<Option<Option<String>>>> = Arc::new(std::sync::Mutex::new(None));
    let s2 = seen.clone();
    *fx.daemon.teams.enqueue_seam.lock().unwrap() = Some(Arc::new(move || {
        *s2.lock().unwrap() = Some(tick_on(&d, &m2));
    }));
    assert_eq!(queued_on(&fx.daemon, P + 61, m.id, "A 정지 중 보고")["ok"], json!(true));
    *fx.daemon.teams.enqueue_seam.lock().unwrap() = None;
    assert_eq!(*seen.lock().unwrap(), Some(None), "창 안의 틱 = 배달 0(꼬리표가 이미 보임)");
    assert_eq!(texts(&m), vec!["A 정지 중 보고"]);
}

/// M2 반례 — 몫 30 에서 29 꼬리표 + 동시 넣기 2건 = 하나만 들어간다(31 금지).
///   첫 넣기가 잠금을 놓은 창에서 둘째 넣기를 끼워 넣는다(이음매 · 결정론). 고치기 전: 둘째가 29 만 세어 31.
#[test]
fn cm2_concurrent_enqueue_cannot_exceed_the_share() {
    let fx = fx("cm2share");
    let m = pane(&fx, "master", None, P + 70);
    let _a = pane(&fx, "worker-1", Some("a"), P + 71);
    let _b = pane(&fx, "worker-2", Some("b"), P + 72);
    let share = crate::team::team_queue_share();
    assert_eq!(share, 30, "전제: 기본 몫");
    for i in 0..share - 1 {
        assert_eq!(queued_on(&fx.daemon, P + 71, m.id, &format!("a{i}"))["ok"], json!(true), "{i}");
    }
    let d = fx.daemon.clone();
    let mid = m.id;
    let nested: Arc<std::sync::Mutex<Option<Value>>> = Arc::new(std::sync::Mutex::new(None));
    let n2 = nested.clone();
    let once = Arc::new(AtomicBool::new(false));
    *fx.daemon.teams.enqueue_seam.lock().unwrap() = Some(Arc::new(move || {
        if !once.swap(true, Ordering::SeqCst) {
            *n2.lock().unwrap() = Some(queued_on(&d, P + 71, mid, "a-race"));
        }
    }));
    let outer = queued_on(&fx.daemon, P + 71, m.id, "a-last");
    *fx.daemon.teams.enqueue_seam.lock().unwrap() = None;
    let nested = nested.lock().unwrap().clone().expect("전제: 끼워 넣기가 돌았다");
    assert_eq!(outer["ok"], json!(true), "{outer}");
    assert_eq!(nested["error"]["code"], json!(crate::team::QUEUE_FULL_TEAM), "끼워 넣은 둘째 = 몫 넘침: {nested}");
    assert_eq!(m.pending_queue.lock().unwrap().len(), share, "큐 = 몫 그대로(31 아님)");
}

// ─────────────────────────── M3·M4 · 도우미 상한 ───────────────────────────

/// M3 반례 — `surface.create` 의 group 파라미터는 판정 팀을 바꾸지 않는다(만든 좌석의 실제 팀 = cwd 폴더).
///   고치기 전: cwd=A·group=B 가 B 로 세어져 꽉 찬 A 에 하나 더 들어가고(상한 우회) · cwd=C·group=B 는 꽉 찬 B 로 거짓 거절.
#[test]
fn cm3_group_param_does_not_change_the_admission_team() {
    let fx = fx("cm3");
    let mk = |n: &str| {
        let d = fx.dir.join(n);
        std::fs::create_dir_all(&d).unwrap();
        d.to_string_lossy().into_owned()
    };
    let (da, db, dc) = (mk("teamA"), mk("teamB"), mk("teamC"));
    for d in [&da, &db] {
        let w = fx.daemon.create_surface(Some(d.clone()), Some("sleep 30".into()), None, Some("worker".into()), 24, 80).unwrap();
        fx.daemon.surfaces.lock().unwrap().insert(w.id, w.clone());
    }
    crate::team::set_team_worker_limit_for_thread(Some(1));
    let r = rpc(&fx, Some(992_701), "surface.create", json!({"cmd": "sleep 30", "role": "worker", "cwd": da, "group": "teamB"}));
    assert_eq!(r["error"]["code"], json!(crate::team::TEAM_WORKER_LIMIT), "cwd=A(꽉 참) + group=B = 거절: {r}");
    let r = rpc(&fx, Some(992_702), "surface.create", json!({"cmd": "sleep 30", "role": "worker", "cwd": dc, "group": "teamB"}));
    assert_eq!(r["ok"], json!(true), "cwd=C(빈 팀) + group=B(꽉 참) = 통과: {r}");
    let sid = r["result"]["surface_id"].as_u64().expect("surface_id");
    let s = fx.daemon.get_surface(sid).expect("새 좌석");
    assert_eq!(crate::team::seat_team(&s).as_deref(), Some("teamC"), "판정한 팀 = 실제 팀");
    assert_eq!(crate::team::create_team(&json!({"cwd": dc, "group": "teamB"})).as_deref(), Some("teamC"));
}

/// M4 반례 — 같은 팀 동시 생성 2건(상한 1 · 산 도우미 0) = 하나만 생긴다.
///   첫 생성이 수를 센 직후(이음매)에 둘째가 그 자리에 닿을 때까지 1.5초 기다린다. 고치기 전: 둘째도 0 을 세어 둘 다 생김.
///   고친 뒤: 둘째는 팀 생성 문에서 기다리다 첫째 삽입 뒤 1 을 세어 거절.
#[test]
fn cm4_concurrent_same_team_creates_respect_the_cap() {
    let fx = fx("cm4");
    let d = fx.dir.join("teamA");
    std::fs::create_dir_all(&d).unwrap();
    let cwd = d.to_string_lossy().into_owned();
    let arrived = Arc::new(AtomicUsize::new(0));
    let a2 = arrived.clone();
    *fx.daemon.teams.admit_seam.lock().unwrap() = Some(Arc::new(move || {
        if a2.fetch_add(1, Ordering::SeqCst) == 0 {
            let until = std::time::Instant::now() + std::time::Duration::from_millis(1500);
            while a2.load(Ordering::SeqCst) < 2 && std::time::Instant::now() < until {
                std::thread::sleep(std::time::Duration::from_millis(10));
            }
        }
    }));
    let spawn = |pid: u32| {
        let d = fx.daemon.clone();
        let cwd = cwd.clone();
        std::thread::spawn(move || {
            crate::team::set_team_worker_limit_for_thread(Some(1));
            rpc_on(&d, Some(pid), "surface.create", json!({"cmd": "sleep 30", "role": "worker", "cwd": cwd}))
        })
    };
    let t1 = spawn(992_801);
    std::thread::sleep(std::time::Duration::from_millis(100));
    let t2 = spawn(992_802);
    let (r1, r2) = (t1.join().unwrap(), t2.join().unwrap());
    *fx.daemon.teams.admit_seam.lock().unwrap() = None;
    let oks = [&r1, &r2].iter().filter(|r| r["ok"] == json!(true)).count();
    let denied = [&r1, &r2].iter().filter(|r| r["error"]["code"] == json!(crate::team::TEAM_WORKER_LIMIT)).count();
    assert_eq!((oks, denied), (1, 1), "하나만 생성 · 하나는 상한 거절: {r1} · {r2}");
    let live = crate::team::snapshot(&fx.daemon).iter().filter(|s| !s.exited && s.team.as_deref() == Some("teamA")).count();
    assert_eq!(live, 1, "팀 A 산 도우미 = 1");
}

// ─────────────────────────── M5 · 보존소·주차 크레딧 ───────────────────────────

/// 보존소 행이 살았나(만료 보존소에 없고 · 활성 보존소나 어느 좌석 큐에 있음).
fn alive_in_daemon(fx: &Fx, id: &str) -> bool {
    let rx = fx.daemon.restored_expired.lock().unwrap().iter().any(|r| r["id"] == json!(id));
    let rq = fx.daemon.restored_queue.lock().unwrap().iter().any(|r| r["id"] == json!(id));
    let live = fx.daemon.surfaces.lock().unwrap().values().any(|s| s.pending_queue.lock().unwrap().iter().any(|e| e.id == id));
    !rx && (rq || live)
}

/// 좌석 큐 머리를 꺼내 7시간 늙혀 보존소 행으로 옮긴다(좌석이 죽어 park 된 것과 같은 꼴).
fn park_head_to_restored(s: &Arc<Surface>, d: &Arc<Daemon>, role: &str, age: f64) -> String {
    let mut e = s.pending_queue.lock().unwrap().pop_front().expect("머리");
    e.enqueued_at -= age;
    let id = e.id.clone();
    d.restored_queue.lock().unwrap().push(crate::state::queue_entry_row(s.id, &Some(role.to_string()), &e));
    id
}

/// M5 반례(꼬리표) — 정지 팀이 마스터에게 넣은 항목이 마스터 부재로 보존소에 옮겨져도 팀 정지 동안 만료되지 않는다.
///   대조: 정지 안 된 팀 항목은 종전대로 만료. 고치기 전: 보존소 크레딧 = 데몬 정지만 → 둘 다 만료.
#[test]
fn cm5_restored_row_tagged_by_paused_team_keeps_ttl_credit() {
    let fx = fx("cm5tag");
    let m = pane(&fx, "master", None, P + 80);
    let _a = pane(&fx, "worker-1", Some("a"), P + 81);
    let _b = pane(&fx, "worker-2", Some("b"), P + 82);
    assert_eq!(queued_on(&fx.daemon, P + 81, m.id, "A 보고")["ok"], json!(true));
    assert_eq!(queued_on(&fx.daemon, P + 82, m.id, "B 보고")["ok"], json!(true));
    pause(&fx, P + 80, "a", true);
    let seven_h = 7.0 * 3600.0;
    let ida = park_head_to_restored(&m, &fx.daemon, "master", seven_h);
    let idb = park_head_to_restored(&m, &fx.daemon, "master", seven_h);
    drop_seat(&fx, &m);
    *fx.daemon.queue_tick_at.lock().unwrap() = Some(crate::state::now_epoch() - seven_h);
    crate::governance::queue_expiry_pass(&fx.daemon);
    assert!(alive_in_daemon(&fx, &ida), "정지 팀 꼬리표 행 = 크레딧으로 생존");
    assert!(!alive_in_daemon(&fx, &idb), "대조: 정지 안 된 팀 행 = 만료");
}

/// M5 반례(목적지) — 정지 팀 **좌석**으로 가던 항목이 그 좌석이 죽어 보존소로 옮겨져도 크레딧이 이어진다(정지 전환이 목적지 팀을 적음).
#[test]
fn cm5_restored_row_from_paused_team_seat_keeps_ttl_credit() {
    let fx = fx("cm5dest");
    let _m = pane(&fx, "master", None, P + 90);
    let a = pane(&fx, "worker-1", Some("a"), P + 91);
    let _b = pane(&fx, "worker-2", Some("b"), P + 92);
    assert_eq!(queued_on(&fx.daemon, P + 90, a.id, "to-a")["ok"], json!(true));
    pause(&fx, P + 90, "a", true);
    let seven_h = 7.0 * 3600.0;
    let id = park_head_to_restored(&a, &fx.daemon, "worker-1", seven_h);
    drop_seat(&fx, &a);
    *fx.daemon.queue_tick_at.lock().unwrap() = Some(crate::state::now_epoch() - seven_h);
    crate::governance::queue_expiry_pass(&fx.daemon);
    assert!(alive_in_daemon(&fx, &id), "정지 팀 좌석 행 = 크레딧으로 생존");
}

/// M5 — 역할 주차 큐: 주차 중 팀 정지 크레딧을 TTL(항목 enqueued_at 기준 600초)에서 뺀다 · 대조 = 정지 안 된 팀 항목은 종전대로 만기.
#[test]
fn cm5_parked_entry_of_paused_team_gets_parking_credit() {
    let fx = fx("cm5park");
    let m = pane(&fx, "master", None, P + 100);
    let _a = pane(&fx, "worker-1", Some("a"), P + 101);
    let _b = pane(&fx, "worker-2", Some("b"), P + 102);
    assert_eq!(queued_on(&fx.daemon, P + 101, m.id, "A 보고")["ok"], json!(true));
    assert_eq!(queued_on(&fx.daemon, P + 102, m.id, "B 보고")["ok"], json!(true));
    pause(&fx, P + 100, "a", true);
    let mut taken: Vec<crate::state::QueueEntry> = m.pending_queue.lock().unwrap().drain(..).collect();
    for e in taken.iter_mut() {
        e.enqueued_at -= 700.0; // 주차 TTL(600) 넘김
    }
    let (ida, idb) = (taken[0].id.clone(), taken[1].id.clone());
    drop_seat(&fx, &m);
    fx.daemon.parked_queues.lock().unwrap().insert(
        "master".into(),
        crate::state::ParkedQueue { entries: taken, parked_at: crate::state::now_epoch() - 300.0, from_surface: m.id },
    );
    // 주차된 뒤 정지가 300초 이어졌다 — 틱 1회(delta 300).
    *fx.daemon.queue_tick_at.lock().unwrap() = Some(crate::state::now_epoch() - 300.0);
    crate::governance::queue_expiry_pass(&fx.daemon);
    assert!(fx.daemon.teams.parked_credit(&ida) >= 299.0, "정지 팀 항목 = 크레딧 적립");
    assert_eq!(fx.daemon.teams.parked_credit(&idb), 0.0, "대조 = 적립 0");
    let now = crate::state::now_epoch();
    let gone = {
        let mut map = fx.daemon.parked_queues.lock().unwrap();
        crate::state::drain_expired_parked_locked(&mut map, now, &fx.daemon.teams)
    };
    let gone_ids: Vec<String> = gone.iter().flat_map(|(_, _, v)| v.iter().map(|e| e.id.clone())).collect();
    assert_eq!(gone_ids, vec![idb.clone()], "정지 안 된 팀 항목만 만기");
    let left: Vec<String> = fx.daemon.parked_queues.lock().unwrap().get("master").map(|p| p.entries.iter().map(|e| e.id.clone()).collect()).unwrap_or_default();
    assert_eq!(left, vec![ida], "정지 팀 항목 = 주차 생존");
}

/// (codex 2R M5) 반례 — 주차 중 팀 정지 크레딧으로 주차를 살아남은 항목이 새 마스터 좌석에 승계되면, 그 크레딧이 항목
///   `paused_total_secs` 로 옮겨져 활성 큐 TTL(6시간)에서도 산다. 고치기 전: 크레딧이 장부에만 남아 승계 직후 다음 틱에 만료.
#[test]
fn cm5_inherited_parked_entry_keeps_its_pause_credit() {
    let fx = fx("cm5inherit");
    let m = pane(&fx, "master", None, P + 130);
    let _a = pane(&fx, "worker-1", Some("a"), P + 131);
    let _b = pane(&fx, "worker-2", Some("b"), P + 132);
    assert_eq!(queued_on(&fx.daemon, P + 131, m.id, "A 보고")["ok"], json!(true));
    pause(&fx, P + 130, "a", true);
    let seven_h = 7.0 * 3600.0;
    let mut taken: Vec<crate::state::QueueEntry> = m.pending_queue.lock().unwrap().drain(..).collect();
    taken[0].enqueued_at -= seven_h;
    let id = taken[0].id.clone();
    drop_seat(&fx, &m);
    fx.daemon.parked_queues.lock().unwrap().insert(
        "master".into(),
        crate::state::ParkedQueue { entries: taken, parked_at: crate::state::now_epoch() - seven_h, from_surface: m.id },
    );
    // 주차된 7시간 내내 팀 a 정지 — 틱 1회(delta 7h)로 주차 크레딧 적립.
    *fx.daemon.queue_tick_at.lock().unwrap() = Some(crate::state::now_epoch() - seven_h);
    crate::governance::queue_expiry_pass(&fx.daemon);
    assert!(fx.daemon.teams.parked_credit(&id) > seven_h - 60.0, "전제: 주차 크레딧 ≈ 7시간");
    // 새 마스터 좌석 — 생성 경로가 주차분을 승계한다.
    let r = rpc(&fx, Some(992_901), "surface.create", json!({"cmd": "sleep 30", "role": "master"}));
    assert_eq!(r["ok"], json!(true), "{r}");
    let nm = fx.daemon.get_surface(r["result"]["surface_id"].as_u64().unwrap()).unwrap();
    let got = nm.pending_queue.lock().unwrap().iter().find(|e| e.id == id).cloned().expect("승계됨(주차 TTL 생존)");
    assert!(got.paused_total_secs > seven_h - 60.0, "크레딧이 항목으로 옮겨짐: {}", got.paused_total_secs);
    assert_eq!(fx.daemon.teams.parked_credit(&id), 0.0, "장부 크레딧은 꺼냄(겹쳐 더하지 않음)");
    crate::governance::queue_expiry_pass(&fx.daemon);
    assert!(nm.pending_queue.lock().unwrap().iter().any(|e| e.id == id), "승계 뒤 활성 TTL 에서도 생존(만료 0)");
    assert!(!nm.expired_queue.lock().unwrap().iter().any(|e| e.id == id));
}

// ─────────────────────────── M6 · 보고 링 ───────────────────────────

/// M6 — 읽을 때 만료분·빈 팀 키를 실제로 지운다 · 팀 키 수 상한(가장 오래 조용한 팀부터 버림).
#[test]
fn cm6_report_ring_prunes_and_bounds_team_keys() {
    let b = crate::team::TeamBook::default();
    for i in 0..10 {
        b.note_report(&format!("old{i}"), 1.0);
    }
    let later = 1.0 + crate::team::REPORT_WINDOW_SECS + 10.0;
    assert!(b.reports(later).is_empty(), "창 밖 = 비어 보임");
    assert_eq!(b.report_team_count(), 0, "빈 팀 키 = 실제로 지움(사본만 거르지 않음)");
    for i in 0..(crate::team::REPORT_TEAMS_MAX + 40) {
        b.note_report(&format!("t{i}"), 100.0 + i as f64);
    }
    assert_eq!(b.report_team_count(), crate::team::REPORT_TEAMS_MAX, "팀 키 = 상한");
    let r = b.reports(200.0 + crate::team::REPORT_TEAMS_MAX as f64);
    assert!(r.contains_key(&format!("t{}", crate::team::REPORT_TEAMS_MAX + 39)), "가장 최근 팀 = 남음");
    assert!(!r.contains_key("t0"), "가장 오래 조용한 팀 = 버림");
}
