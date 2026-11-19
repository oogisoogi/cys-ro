// (조각 6b · TICKET=cysr-1116-s6-1119) 팀별 기계 장치 — P2-DESIGN §16-2 ⑦~⑩ · PRD FR-L7 · LLM 팀장 0(10-09 정책).
//
// 팀 = 본부 안 좌석 묶음(개정 E1). 데몬 쪽 판정 = 명시 묶음(`cys seat-group` → Surface.group = Some(Some(g))) 우선,
//   아니면 좌석 **생성** 폴더의 마지막 이름(앱 ui/src/seatrows.ts folderKey 와 같은 규칙). master*·cso* 좌석은 팀이 아니다.
//   ⚠앱의 「사람이 옮긴 묶음」 기록(localStorage cys-seat-group)은 데몬이 모른다 — 데몬 재시작 뒤 그 기록만 있는 좌석은
//   폴더 이름으로 셈(=앱이 다시 정하기 전까지 「지금 동작」 쪽으로 물러남 · 설계 §16-2 한계 1줄).
// 장치 넷:
//   ⑦ 팀별 대기열 몫  — 마스터 좌석 큐에 넣을 때 한 팀이 몫(기본 30)을 넘으면 그 팀 요청만 `queue_full_team`.
//   ⑧ 팀별 도우미 상한 — `CYS_MAX_TEAM_WORKERS`(기본 0 = 무제한) · surface.create {role:worker} 거절 `team_worker_limit_exceeded`.
//   ⑨ 팀 정지 스위치  — `surface.group_pause` · 그 팀 좌석으로 가는 큐 배달 동결 + 그 팀이 마스터로 넣은 큐 항목 보류(직접 보내기 통과).
//   ⑩ 【진행】 묶음    — `kind:"progress"` 꼬리표를 단 기계 문안만 팀별 10분 창으로 묶어 1건 배달(원문 순서대로 보존 · 급한 머리표 = 즉시).
// ⑦·⑩ 은 「팀이 2개 이상」일 때만 발효(팀 1개 사용자 = 지금 동작 그대로). 모든 상태는 데몬 메모리 전용(재시작 = 비움 · 안전 쪽).
// 락 규약: TeamBook 의 세 Mutex 는 말단(leaf) — 잡은 채로 다른 락을 잡지 않는다. pending_queue → book 순서는 허용.
use std::collections::{HashMap, HashSet, VecDeque};
use std::sync::Mutex;

/// ⑦ 기본 몫(팀당 마스터 좌석 큐 항목 수 · 설계 목표값). env `CYS_TEAM_QUEUE_SHARE`(0 = 끔).
pub const TEAM_QUEUE_SHARE_DEFAULT: usize = 30;
/// ⑩ 기본 묶음 창(초 · 설계 목표값). env `CYS_PROGRESS_BUNDLE_SECS`(0 = 묶지 않음).
pub const PROGRESS_BUNDLE_SECS_DEFAULT: u64 = 600;
/// team.stats 보고 시각 링 — 팀별 상한 · 창(7일).
pub const REPORT_RING_MAX: usize = 5000;
pub const REPORT_WINDOW_SECS: f64 = 7.0 * 86_400.0;
/// ⑩ 이 머리표가 본문에 있으면 꼬리표가 있어도 묶지 않는다(즉시 원문).
pub const URGENT_MARKS: [&str; 5] = ["【확인요청】", "【질문】", "【결정필요】", "【경고】", "【막힘】"];
/// ⑩ 큐 보내기 파라미터 값(`kind`).
pub const PROGRESS_KIND: &str = "progress";
/// 오류 코드 · 사건 이름.
pub const QUEUE_FULL_TEAM: &str = "queue_full_team";
pub const TEAM_WORKER_LIMIT: &str = "team_worker_limit_exceeded";
pub const EV_PAUSED: &str = "team.paused";
pub const EV_RESUMED: &str = "team.resumed";

/// 폴더 경로의 마지막 이름 — `/`·`\` 둘 다 자른다 · 드라이브 뿌리(`C:`) = "" (seatrows.ts folderKey 와 같은 규칙).
pub fn folder_key(cwd: &str) -> String {
    let last = cwd.split(['/', '\\']).filter(|p| !p.is_empty()).last().unwrap_or("");
    let b = last.as_bytes();
    if b.len() == 2 && b[1] == b':' && b[0].is_ascii_alphabetic() {
        return String::new();
    }
    last.to_string()
}

/// master·cso 계열(고정 좌석) — 팀이 아니다(seatrows.ts fixedRank 와 같은 규칙).
pub fn is_fixed_role(role: Option<&str>) -> bool {
    let r = role.unwrap_or("").trim();
    r == "master" || r.starts_with("master-") || r == "cso" || r.starts_with("cso-")
}

/// 좌석의 팀 — 명시 묶음 > 생성 폴더 이름 · 고정 좌석·빈 이름 = None.
pub fn team_of(role: Option<&str>, group: &Option<Option<String>>, cwd: &str) -> Option<String> {
    if is_fixed_role(role) {
        return None;
    }
    let t = match group {
        Some(Some(g)) => g.clone(),
        _ => folder_key(cwd),
    };
    (!t.is_empty()).then_some(t)
}

fn env_num(name: &str) -> Option<u64> {
    std::env::var(name).ok().and_then(|v| v.trim().parse::<u64>().ok())
}
pub fn team_queue_share() -> usize {
    env_num("CYS_TEAM_QUEUE_SHARE").map(|v| v as usize).unwrap_or(TEAM_QUEUE_SHARE_DEFAULT)
}
pub fn max_team_workers() -> usize {
    if let Some(v) = TEAM_WORKER_LIMIT_FOR_THREAD.with(|c| c.get()) {
        return v; // 시험 훅(이 스레드만 · 프로세스 env 를 건드리지 않아 병렬 시험의 좌석 만들기를 막지 않는다)
    }
    env_num("CYS_MAX_TEAM_WORKERS").map(|v| v as usize).unwrap_or(0)
}
thread_local! {
    /// 시험 전용 덮어쓰기(운영 경로에서는 늘 None) — `set_team_worker_limit_for_thread`.
    static TEAM_WORKER_LIMIT_FOR_THREAD: std::cell::Cell<Option<usize>> = const { std::cell::Cell::new(None) };
}
/// 이 스레드의 팀별 도우미 상한을 덮어쓴다(None = env 로 돌아감) — 시험 하네스용.
#[allow(dead_code)]
pub fn set_team_worker_limit_for_thread(v: Option<usize>) {
    TEAM_WORKER_LIMIT_FOR_THREAD.with(|c| c.set(v));
}
pub fn progress_bundle_secs() -> u64 {
    env_num("CYS_PROGRESS_BUNDLE_SECS").unwrap_or(PROGRESS_BUNDLE_SECS_DEFAULT)
}

pub fn is_urgent(text: &str) -> bool {
    URGENT_MARKS.iter().any(|m| text.contains(m))
}

/// 마스터 좌석 큐 항목의 팀 꼬리표(넣을 때 정함 · 메모리 전용).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EntryTag {
    pub team: String,
    pub progress: bool,
}

/// 데몬 하나의 팀 장부.
#[derive(Default)]
pub struct TeamBook {
    paused: Mutex<HashSet<String>>,
    /// 대상 좌석 → (항목 id → 꼬리표). 대상 큐 잠금 안에서 그 큐에 없는 id 를 지운다(상한 = 큐 상한).
    tags: Mutex<HashMap<u64, HashMap<String, EntryTag>>>,
    reports: Mutex<HashMap<String, VecDeque<f64>>>,
}

impl TeamBook {
    pub fn is_paused(&self, team: &str) -> bool {
        self.paused.lock().unwrap_or_else(|e| e.into_inner()).contains(team)
    }
    pub fn paused_set(&self) -> HashSet<String> {
        self.paused.lock().unwrap_or_else(|e| e.into_inner()).clone()
    }
    /// 바뀌었으면 true(같은 값이면 사건 0).
    pub fn set_paused(&self, team: &str, paused: bool) -> bool {
        let mut p = self.paused.lock().unwrap_or_else(|e| e.into_inner());
        if paused {
            p.insert(team.to_string())
        } else {
            p.remove(team)
        }
    }
    pub fn paused_list(&self) -> Vec<String> {
        let mut v: Vec<String> = self.paused_set().into_iter().collect();
        v.sort();
        v
    }
    /// 대상 좌석 큐의 꼬리표 — `live` = 지금 그 큐에 있는 id(잠금 안에서 넘김) · 없는 id 는 지운다.
    pub fn tags_for(&self, target: u64, live: &[&str]) -> HashMap<String, EntryTag> {
        let mut t = self.tags.lock().unwrap_or_else(|e| e.into_inner());
        let Some(m) = t.get_mut(&target) else { return HashMap::new() };
        let keep: HashSet<&str> = live.iter().copied().collect();
        m.retain(|id, _| keep.contains(id.as_str()));
        m.clone()
    }
    pub fn tag(&self, target: u64, entry_id: &str, tag: EntryTag) {
        self.tags.lock().unwrap_or_else(|e| e.into_inner()).entry(target).or_default().insert(entry_id.to_string(), tag);
    }
    /// team.stats 재료 — 그 팀 좌석이 마스터 좌석 큐에 넣은 시각.
    pub fn note_report(&self, team: &str, ts: f64) {
        let mut r = self.reports.lock().unwrap_or_else(|e| e.into_inner());
        let q = r.entry(team.to_string()).or_default();
        q.push_back(ts);
        while q.front().is_some_and(|&t| ts - t > REPORT_WINDOW_SECS) || q.len() > REPORT_RING_MAX {
            q.pop_front();
        }
    }
    pub fn reports(&self, now: f64) -> HashMap<String, Vec<f64>> {
        let r = self.reports.lock().unwrap_or_else(|e| e.into_inner());
        r.iter()
            .map(|(k, q)| (k.clone(), q.iter().copied().filter(|&t| now - t <= REPORT_WINDOW_SECS).collect::<Vec<f64>>()))
            .filter(|(_, v)| !v.is_empty())
            .collect()
    }
}

/// 좌석 한 장의 팀 재료(스냅숏 · 잠금 밖에서 판정).
#[derive(Clone, Debug)]
pub struct SeatTeam {
    pub sid: u64,
    pub team: Option<String>,
    pub role: Option<String>,
    pub exited: bool,
    pub working: bool,
}

/// 살아 있는 팀 좌석들의 서로 다른 팀 이름 수.
pub fn distinct_teams(seats: &[SeatTeam]) -> usize {
    seats.iter().filter(|s| !s.exited).filter_map(|s| s.team.as_deref()).collect::<HashSet<&str>>().len()
}

/// 데몬 좌석 표 → 팀 재료(surfaces 락 1회 · 좌석별 말단 락만).
pub fn snapshot(daemon: &crate::state::Daemon) -> Vec<SeatTeam> {
    let surfaces = daemon.surfaces.lock().unwrap_or_else(|e| e.into_inner());
    let mut v: Vec<SeatTeam> = surfaces
        .values()
        .map(|s| {
            let role = s.role.lock().unwrap_or_else(|e| e.into_inner()).clone();
            let group = s.group.lock().unwrap_or_else(|e| e.into_inner()).clone();
            let working = s.agent_status.lock().unwrap_or_else(|e| e.into_inner()).as_ref().is_some_and(|a| a.state == "working");
            SeatTeam {
                sid: s.id,
                team: team_of(role.as_deref(), &group, &s.cwd),
                role,
                exited: s.exited.load(std::sync::atomic::Ordering::Relaxed),
                working,
            }
        })
        .collect();
    v.sort_by_key(|s| s.sid);
    v
}

/// 대상 좌석이 마스터인가(⑦·⑩ 은 마스터 좌석 큐에만).
pub fn is_master_target(role: Option<&str>) -> bool {
    role == Some("master")
}

/// 넣기 전 판정 결과 — 마스터 좌석 큐에 팀 좌석이 넣는 경우만 `Some`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EnqueuePlan {
    pub team: String,
    /// 팀 ≥ 2 (⑦·⑩ 발효)
    pub multi: bool,
    pub progress: bool,
}

/// 넣기 전(잠금 밖) 계획: 대상이 마스터 ∧ 발신 좌석에 팀이 있을 때. progress = 꼬리표 ∧ 급한 머리표 없음 ∧ 팀 ≥ 2.
pub fn plan_enqueue(seats: &[SeatTeam], target: u64, from: Option<u64>, kind: Option<&str>, text: &str) -> Option<EnqueuePlan> {
    let t = seats.iter().find(|s| s.sid == target)?;
    if t.exited || !is_master_target(t.role.as_deref()) {
        return None;
    }
    let team = seats.iter().find(|s| Some(s.sid) == from)?.team.clone()?;
    let multi = distinct_teams(seats) >= 2;
    let progress = multi && kind == Some(PROGRESS_KIND) && !is_urgent(text) && !text.is_empty();
    Some(EnqueuePlan { team, multi, progress })
}

/// 넣는 자리의 입구 — 대상 좌석이 마스터일 때만 좌석 표를 훑는다(그 밖 좌석 큐 = 비용 0 · 계획 없음).
pub fn plan_for(daemon: &crate::state::Daemon, target: &crate::state::Surface, from: Option<u64>, kind: Option<&str>, text: &str) -> Option<EnqueuePlan> {
    let role = target.role.lock().unwrap_or_else(|e| e.into_inner()).clone();
    if !is_master_target(role.as_deref()) || from.is_none() {
        return None;
    }
    plan_enqueue(&snapshot(daemon), target.id, from, kind, text)
}

/// 넣은 뒤 기록(대상 큐 잠금 밖·안 무관 · 말단 락만) — 꼬리표 + 보고 시각.
pub fn note_enqueued(book: &TeamBook, target: u64, entry_id: &str, enqueued_at: f64, plan: &EnqueuePlan) {
    book.tag(target, entry_id, EntryTag { team: plan.team.clone(), progress: plan.progress });
    book.note_report(&plan.team, enqueued_at);
}

/// ⑦ 몫 판정(대상 큐 잠금 안에서) — 그 팀 항목 수 ≥ 몫이면 거절. 몫 0 = 끔 · 팀 1개 = 발효 0.
pub fn share_exceeded(plan: &EnqueuePlan, tags: &HashMap<String, EntryTag>, share: usize) -> bool {
    plan.multi && share > 0 && tags.values().filter(|t| t.team == plan.team).count() >= share
}

/// ⑦ 대상 큐(잠금 안 · `q` = 그 가드) 기준 몫 넘침인가 — 꼬리표 정리(큐에 없는 id 지움)도 여기서.
pub fn share_over(book: &TeamBook, target: u64, q: &VecDeque<crate::state::QueueEntry>, plan: &EnqueuePlan) -> bool {
    if !plan.multi {
        return false;
    }
    let live: Vec<&str> = q.iter().map(|e| e.id.as_str()).collect();
    share_exceeded(plan, &book.tags_for(target, &live), team_queue_share())
}

/// ⑦ 거절 응답 + 사건 `team.queue_full`(그 팀 요청만 · 다른 팀·전체 100 무관).
pub fn queue_full_team_response(daemon: &crate::state::Daemon, id: &serde_json::Value, target: u64, plan: &EnqueuePlan) -> serde_json::Value {
    let share = team_queue_share();
    daemon.bus.publish(
        "team.queue_full",
        "queue",
        Some(target),
        serde_json::json!({"surface_ref": cys::surface_ref(target), "team": plan.team, "share": share}),
    );
    cys::err_response(
        id,
        QUEUE_FULL_TEAM,
        &format!("team queue share ({share}) reached for team {:?} on the master seat (other teams still enqueue · CYS_TEAM_QUEUE_SHARE)", plan.team),
    )
}

/// ⑧ surface.create {role:worker} 의 팀별 상한 — 넘으면 거절 응답(사건 `team.worker_limit_denied`) · 상한 0 = 통과.
pub fn team_worker_gate(daemon: &crate::state::Daemon, id: &serde_json::Value, params: &serde_json::Value, caller_pid: Option<u32>) -> Option<serde_json::Value> {
    let limit = max_team_workers();
    if limit == 0 {
        return None;
    }
    let group = params.get("group").and_then(|v| v.as_str()).map(str::trim).filter(|g| !g.is_empty()).map(str::to_string);
    let cwd = params
        .get("cwd")
        .and_then(|v| v.as_str())
        .map(str::to_string)
        .or_else(|| dirs::home_dir().map(|p| p.to_string_lossy().into_owned()))
        .unwrap_or_default();
    let team = team_of(Some("worker"), &group.map(Some), &cwd)?;
    let active = snapshot(daemon)
        .iter()
        .filter(|s| !s.exited && s.team.as_deref() == Some(team.as_str()))
        .filter(|s| s.role.as_deref().is_some_and(|r| r == "worker" || r.starts_with("worker-")))
        .count();
    if active < limit {
        return None;
    }
    daemon.bus.publish(
        "team.worker_limit_denied",
        "system",
        None,
        serde_json::json!({"team": team, "limit": limit, "active": active, "path": "surface.create", "caller_pid": caller_pid}),
    );
    Some(cys::err_response(
        id,
        TEAM_WORKER_LIMIT,
        &format!("team worker limit reached for team {team:?}: {active}/{limit} (CYS_MAX_TEAM_WORKERS · 기본은 무제한)"),
    ))
}

/// 배달 판정 재료 — 큐 항목 (id, 넣은 시각) 순서대로.
pub struct HoldView<'a> {
    pub tags: &'a HashMap<String, EntryTag>,
    pub paused: &'a HashSet<String>,
    pub multi: bool,
    pub bundle_secs: u64,
    pub now: f64,
}

impl HoldView<'_> {
    /// 이 팀의 【진행】 항목이 풀렸나 — 그 팀의 가장 오래된 꼬리표 항목이 창을 채웠거나 · 팀이 1개로 줄었거나 · 창 0.
    pub fn progress_released(&self, team: &str, entries: &[(&str, f64)]) -> bool {
        if !self.multi || self.bundle_secs == 0 {
            return true;
        }
        entries
            .iter()
            .filter(|(id, _)| self.tags.get(*id).is_some_and(|t| t.progress && t.team == team))
            .map(|(_, at)| *at)
            .fold(None, |m: Option<f64>, at| Some(m.map_or(at, |x| x.min(at))))
            .is_some_and(|oldest| self.now - oldest >= self.bundle_secs as f64)
    }
    /// 이 항목은 지금 보류인가(정지된 팀 · 아직 안 풀린 【진행】).
    pub fn held(&self, id: &str, entries: &[(&str, f64)]) -> bool {
        let Some(t) = self.tags.get(id) else { return false };
        self.paused.contains(&t.team) || (t.progress && !self.progress_released(&t.team, entries))
    }
}

/// 머리가 보류이고 뒤에 보낼 항목이 있으면 새 순서(보낼 것 먼저 · 각 무리 안 순서 유지) · 아니면 None.
pub fn rotate_order(held: &[bool]) -> Option<Vec<usize>> {
    if !held.first().copied().unwrap_or(false) || held.iter().all(|&h| h) {
        return None;
    }
    let mut order: Vec<usize> = (0..held.len()).filter(|&i| !held[i]).collect();
    order.extend((0..held.len()).filter(|&i| held[i]));
    Some(order)
}

/// ⑩ 머리가 풀린 【진행】 항목이면 함께 실을 같은 팀 【진행】 항목 위치(머리 포함 · 상한 max_items) · 아니면 None.
pub fn bundle_pick(view: &HoldView<'_>, entries: &[(&str, f64)], max_items: usize) -> Option<(String, Vec<usize>)> {
    let (head, _) = entries.first()?;
    let t = view.tags.get(*head)?;
    if !t.progress || !view.multi || view.held(head, entries) {
        return None;
    }
    let team = t.team.clone();
    let picked: Vec<usize> = entries
        .iter()
        .enumerate()
        .filter(|(_, (id, _))| view.tags.get(*id).is_some_and(|x| x.progress && x.team == team))
        .map(|(i, _)| i)
        .take(max_items.max(1))
        .collect();
    Some((team, picked))
}

/// ⑩ 묶음 본문 — 머리 1줄 + 항목마다 발신·원문(순서 그대로 · 원문 보존).
pub fn render_bundle(team: &str, parts: &[(Option<String>, String)]) -> String {
    let mut out = format!("【진행 묶음】 {} {}건\n", team, parts.len());
    for (i, (from, text)) in parts.iter().enumerate() {
        out.push_str(&format!("[{}/{} · {}] {}\n", i + 1, parts.len(), from.as_deref().unwrap_or("unknown"), text));
    }
    out
}

/// team.stats 응답 조립.
pub fn stats_json(seats: &[SeatTeam], book: &TeamBook, now: f64) -> serde_json::Value {
    let reports = book.reports(now);
    let mut names: Vec<String> = seats.iter().filter(|s| !s.exited).filter_map(|s| s.team.clone()).collect();
    names.extend(reports.keys().cloned());
    names.sort();
    names.dedup();
    let teams: Vec<serde_json::Value> = names
        .iter()
        .map(|n| {
            let live: Vec<&SeatTeam> = seats.iter().filter(|s| !s.exited && s.team.as_deref() == Some(n.as_str())).collect();
            let workers = live.iter().filter(|s| s.role.as_deref().is_some_and(|r| r == "worker" || r.starts_with("worker-"))).count();
            let working = live.iter().filter(|s| s.working).count();
            serde_json::json!({
                "team": n,
                "live_seats": live.len(),
                "live_workers": workers,
                "working": working,
                "report_ts": reports.get(n).cloned().unwrap_or_default(),
            })
        })
        .collect();
    serde_json::json!({
        "teams": teams,
        "paused": book.paused_list(),
        "distinct": distinct_teams(seats),
        "window_secs": REPORT_WINDOW_SECS,
        "volatile": true,
        "note": "daemon memory only — a daemon restart empties report_ts (safe direction: fewer asks)",
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn seat(sid: u64, role: &str, team: Option<&str>) -> SeatTeam {
        SeatTeam { sid, team: team.map(str::to_string), role: Some(role.to_string()), exited: false, working: false }
    }

    #[test]
    fn folder_key_matches_app_rule() {
        assert_eq!(folder_key("/Users/a/site"), "site");
        assert_eq!(folder_key("/Users/a/site/"), "site");
        assert_eq!(folder_key("C:\\work\\lms"), "lms");
        assert_eq!(folder_key("C:\\"), "");
        assert_eq!(folder_key(""), "");
    }

    #[test]
    fn team_of_explicit_then_folder_and_fixed_none() {
        assert_eq!(team_of(Some("worker-1"), &Some(Some("홍보".into())), "/x/site"), Some("홍보".into()));
        assert_eq!(team_of(Some("worker-1"), &Some(None), "/x/site"), Some("site".into()));
        assert_eq!(team_of(Some("worker-1"), &None, "/x/site"), Some("site".into()));
        assert_eq!(team_of(Some("master"), &Some(Some("홍보".into())), "/x/site"), None);
        assert_eq!(team_of(Some("cso-2"), &None, "/x/site"), None);
        assert_eq!(team_of(None, &None, "C:\\"), None);
    }

    #[test]
    fn plan_only_for_master_target_and_progress_needs_two_teams() {
        let one = vec![seat(1, "master", None), seat(2, "worker-1", Some("a")), seat(3, "worker-2", Some("a"))];
        let p = plan_enqueue(&one, 1, Some(2), Some("progress"), "진행 1").unwrap();
        assert!(!p.multi && !p.progress, "팀 1개면 발효 0");
        assert!(plan_enqueue(&one, 2, Some(3), Some("progress"), "x").is_none(), "워커 대상 = 없음");
        let two = vec![seat(1, "master", None), seat(2, "worker-1", Some("a")), seat(3, "worker-2", Some("b"))];
        let p = plan_enqueue(&two, 1, Some(2), Some("progress"), "진행").unwrap();
        assert!(p.multi && p.progress);
        assert!(!plan_enqueue(&two, 1, Some(2), Some("progress"), "【막힘】 x").unwrap().progress, "급한 머리표 = 즉시");
        assert!(!plan_enqueue(&two, 1, Some(2), None, "진행").unwrap().progress, "꼬리표 없음 = 즉시");
        assert!(plan_enqueue(&two, 1, None, Some("progress"), "x").is_none(), "검증 발신 없음 = 없음");
    }

    #[test]
    fn share_counts_only_that_team() {
        let mut tags = HashMap::new();
        for i in 0..3 {
            tags.insert(format!("a{i}"), EntryTag { team: "a".into(), progress: false });
        }
        tags.insert("b0".into(), EntryTag { team: "b".into(), progress: false });
        let pa = EnqueuePlan { team: "a".into(), multi: true, progress: false };
        let pb = EnqueuePlan { team: "b".into(), multi: true, progress: false };
        assert!(share_exceeded(&pa, &tags, 3));
        assert!(!share_exceeded(&pb, &tags, 3));
        assert!(!share_exceeded(&pa, &tags, 0), "0 = 끔");
        assert!(!share_exceeded(&EnqueuePlan { multi: false, ..pa.clone() }, &tags, 3), "팀 1개 = 발효 0");
    }

    #[test]
    fn hold_rotate_and_bundle() {
        let mut tags = HashMap::new();
        tags.insert("p1".to_string(), EntryTag { team: "a".into(), progress: true });
        tags.insert("p2".to_string(), EntryTag { team: "a".into(), progress: true });
        tags.insert("n1".to_string(), EntryTag { team: "b".into(), progress: false });
        let paused = HashSet::new();
        let entries = [("p1", 100.0), ("n1", 150.0), ("p2", 200.0)];
        let v = HoldView { tags: &tags, paused: &paused, multi: true, bundle_secs: 600, now: 300.0 };
        let held: Vec<bool> = entries.iter().map(|(id, _)| v.held(id, &entries)).collect();
        assert_eq!(held, vec![true, false, true]);
        assert_eq!(rotate_order(&held), Some(vec![1, 0, 2]));
        assert!(bundle_pick(&v, &entries, 10).is_none(), "창 전 = 묶지 않음");
        let v2 = HoldView { now: 701.0, ..v };
        assert!(!v2.held("p1", &entries));
        assert_eq!(bundle_pick(&v2, &entries, 10), Some(("a".into(), vec![0, 2])));
        // 정지된 팀 — 꼬리표 없는 항목도 보류
        let mut ps = HashSet::new();
        ps.insert("b".to_string());
        let v3 = HoldView { tags: &tags, paused: &ps, multi: true, bundle_secs: 600, now: 701.0 };
        assert!(v3.held("n1", &entries));
        assert_eq!(rotate_order(&[true, true]), None, "전부 보류 = 그대로");
        assert_eq!(rotate_order(&[false, true]), None, "머리가 보낼 것 = 그대로");
    }

    #[test]
    fn report_ring_window() {
        let b = TeamBook::default();
        b.note_report("a", 1.0);
        b.note_report("a", 1.0 + REPORT_WINDOW_SECS + 5.0);
        assert_eq!(b.reports(1.0 + REPORT_WINDOW_SECS + 5.0)["a"].len(), 1, "7일 넘은 시각은 버림");
    }

    #[test]
    fn render_bundle_keeps_every_part_in_order() {
        let s = render_bundle("a", &[(Some("surface:2".into()), "첫째".into()), (None, "둘째".into())]);
        assert!(s.starts_with("【진행 묶음】 a 2건\n"));
        assert!(s.find("첫째").unwrap() < s.find("둘째").unwrap());
    }
}
