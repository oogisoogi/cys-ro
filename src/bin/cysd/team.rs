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
//   예외 1(검증 m4 · master#c4bc0244): 정지된 팀 **이름 목록만** 상태 폴더 `team-paused.json` 에 적어 두고, 데몬이 다시 켜질 때 그 목록이
//   있으면 사건 `team.pause_lost` 1건(「팀 정지가 풀렸어요」)을 내고 파일을 지운다 — 정지를 되살리지는 않는다(영속 = 1.1.17).
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
/// (검증 m4) 데몬 재시작으로 정지가 풀렸음을 알리는 사건 · 정지 이름 목록 파일(상태 폴더 안).
pub const EV_PAUSE_LOST: &str = "team.pause_lost";
pub const PAUSED_FILE: &str = "team-paused.json";
/// (codex 1R B1) 정지 팀 이름 집합 상한 — 넘는 새 이름의 정지 요청 = `team_pause_limit`(이미 정지된 이름·재개는 늘 받는다).
///   영속 파일(`team-paused.json`)은 이 집합만 적으므로 상한이 같이 걸린다(이름 1~64자 × 64 ≈ 16KiB 이하).
pub const PAUSED_TEAMS_MAX: usize = 64;
pub const TEAM_PAUSE_LIMIT: &str = "team_pause_limit";
/// (codex 1R B1) 재시작 때 읽는 정지 목록 파일 상한(바이트) — 넘으면 이름을 읽지 않고 「목록을 못 읽음」으로 알린다.
pub const PAUSED_FILE_MAX_BYTES: u64 = 64 * 1024;
/// (codex 1R M6) 보고 시각 링의 팀 키 수 상한 — 넘으면 가장 오래 조용한 팀부터 버린다(만료분·빈 키는 읽을 때마다 지운다).
pub const REPORT_TEAMS_MAX: usize = 256;
/// (codex 1R M4) 같은 팀 도우미 생성 문을 기다리는 상한(초) — 앞 생성이 이만큼 안 끝나면 거절(무한 대기 0).
pub const ADMIT_WAIT_SECS: u64 = 60;
pub const TEAM_ADMIT_BUSY: &str = "team_worker_admission_busy";

/// 폴더 경로의 마지막 이름 — `/`·`\` 둘 다 자른다 · 드라이브 뿌리(`C:`) = "" (seatrows.ts folderKey 와 같은 규칙).
pub fn folder_key(cwd: &str) -> String {
    let last = cwd.split(['/', '\\']).filter(|p| !p.is_empty()).last().unwrap_or("");
    let b = last.as_bytes();
    if b.len() == 2 && b[1] == b':' && b[0].is_ascii_alphabetic() {
        return String::new();
    }
    last.to_string()
}

/// master·ceo·cso 계열(고정 좌석) — 팀이 아니다(seatrows.ts fixedRank 와 같은 규칙).
/// (검증 i7) `ceo` = 마스터급 좌석(alert_route.rs CLEAR_SIGNAL_ROLES = ["master","ceo"]) — 팀 정지로 얼지 않는다.
pub fn is_fixed_role(role: Option<&str>) -> bool {
    let r = role.unwrap_or("").trim();
    r == "master" || r.starts_with("master-") || r == "ceo" || r.starts_with("ceo-") || r == "cso" || r.starts_with("cso-")
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

/// 항목 한 칸(항목 id 로 묶음) — `misses` = 어느 큐에도 안 보인 연속 청소 횟수(2번이면 지움 · 옮기는 도중 한 번 안 보이는 것은 살린다).
///   · `tag`  = 마스터 좌석 큐에 팀 좌석이 넣은 꼬리표(⑦ 몫 · ⑨ 보류 · ⑩ 묶음).
///   · `dest` = (codex 1R M5) 정지된 팀 **좌석으로 가는** 항목의 목적지 팀 — 그 좌석이 죽어 항목이 역할 주차·복원 보존소로 옮겨져도
///             팀 정지 크레딧을 이어 주는 재료(정지 중에만 적는다 · ⑦⑩ 판정에는 안 쓴다).
///   · `parked_credit` = (M5) 역할 주차 중에 받은 팀 정지 크레딧(초) — 주차 TTL(항목 `enqueued_at` 기준)에서 뺀다.
#[derive(Clone, Debug, Default)]
struct Slot {
    tag: Option<EntryTag>,
    dest: Option<String>,
    parked_credit: f64,
    misses: u8,
}

/// 시험 이음매(운영 경로 = 늘 비어 있음 · `cfg!(test)` 일 때만 부른다) — 동시성 반례를 장벽 없이 순서로 고정한다.
pub type Seam = std::sync::Arc<dyn Fn() + Send + Sync>;

/// 데몬 하나의 팀 장부.
#[derive(Default)]
pub struct TeamBook {
    paused: Mutex<HashSet<String>>,
    /// (검증 m3) 항목 id → 칸. 항목 id 는 데몬 한 번 켜진 동안 유일하고(`q<시작 시각>.<번호>`) 좌석 승계·주차·rehome 이관에서
    ///   그대로 따라가므로, 좌석 id 가 아니라 항목 id 로 묶는다(옮긴 뒤에도 정지 보류·【진행】 묶음이 이어짐). 청소 = `sweep_tags`.
    tags: Mutex<HashMap<String, Slot>>,
    reports: Mutex<HashMap<String, VecDeque<f64>>>,
    /// (검증 m4) 정지 목록 파일 쓰기 직렬화 — 이 잠금 안에서 **최신** 목록을 다시 읽어 쓴다(늦게 쓴 쪽이 낡은 목록을 덮지 않게).
    persist_gate: Mutex<()>,
    /// (codex 1R M4) 지금 도우미 생성 문을 지나는 팀 — 같은 팀 생성은 셈·생성·좌석 표 삽입까지 한 줄로(다른 팀은 막지 않음).
    admitting: Mutex<HashSet<String>>,
    admit_cv: std::sync::Condvar,
    /// 시험 이음매 — 큐 넣기 잠금을 놓은 직후(M2) · 도우미 수를 센 직후(M4) · 배달 앞 팀 판정 직후(M1).
    pub(crate) enqueue_seam: Mutex<Option<Seam>>,
    pub(crate) admit_seam: Mutex<Option<Seam>>,
    pub(crate) deliver_seam: Mutex<Option<Seam>>,
}

/// (M1 시험 이음매) `deliver_head_locked` 의 잠금 밖 팀 판정 직후 — 운영 경로 = 비용 0(`cfg!(test)` 거짓이면 아무것도 안 함).
pub fn deliver_seam(book: &TeamBook) {
    run_seam(&book.deliver_seam);
}

/// (M4) 팀 도우미 생성 문 — 살아 있는 동안 같은 팀 생성은 기다린다 · 놓으면(생성 성공·실패·거절 모두) 다음이 들어온다.
pub struct AdmitToken<'a> {
    book: &'a TeamBook,
    team: String,
}

impl Drop for AdmitToken<'_> {
    fn drop(&mut self) {
        self.book.admitting.lock().unwrap_or_else(|e| e.into_inner()).remove(&self.team);
        self.book.admit_cv.notify_all();
    }
}

fn run_seam(slot: &Mutex<Option<Seam>>) {
    if cfg!(test) {
        let f = slot.lock().unwrap_or_else(|e| e.into_inner()).clone();
        if let Some(f) = f {
            f();
        }
    }
}

impl TeamBook {
    pub fn is_paused(&self, team: &str) -> bool {
        self.paused.lock().unwrap_or_else(|e| e.into_inner()).contains(team)
    }
    pub fn paused_set(&self) -> HashSet<String> {
        self.paused.lock().unwrap_or_else(|e| e.into_inner()).clone()
    }
    /// 바뀌었으면 Ok(true)(같은 값이면 사건 0) · (codex 1R B1) 집합이 상한이면 **새 이름**의 정지만 Err(재개·이미 정지된 이름 = 늘 받음).
    pub fn set_paused(&self, team: &str, paused: bool) -> Result<bool, &'static str> {
        let mut p = self.paused.lock().unwrap_or_else(|e| e.into_inner());
        if paused {
            if !p.contains(team) && p.len() >= PAUSED_TEAMS_MAX {
                return Err("paused team limit reached (resume a team first)");
            }
            Ok(p.insert(team.to_string()))
        } else {
            Ok(p.remove(team))
        }
    }
    pub fn paused_list(&self) -> Vec<String> {
        let mut v: Vec<String> = self.paused_set().into_iter().collect();
        v.sort();
        v
    }
    /// 한 큐의 꼬리표 — `live` = 지금 그 큐에 있는 id(잠금 안에서 넘김) · 꼬리표가 있는 id 만 돌려준다(읽기 전용 · 청소는 `sweep_tags`).
    pub fn tags_for(&self, live: &[&str]) -> HashMap<String, EntryTag> {
        let t = self.tags.lock().unwrap_or_else(|e| e.into_inner());
        if t.is_empty() {
            return HashMap::new();
        }
        live.iter().filter_map(|id| t.get(*id).and_then(|s| s.tag.clone()).map(|tag| (id.to_string(), tag))).collect()
    }
    pub fn tag(&self, entry_id: &str, tag: EntryTag) {
        let mut t = self.tags.lock().unwrap_or_else(|e| e.into_inner());
        let slot = t.entry(entry_id.to_string()).or_default();
        slot.tag = Some(tag);
        slot.misses = 0;
    }
    /// (M5) 정지된 팀 좌석으로 가는 항목의 목적지 팀을 적는다(이미 적힌 것은 그대로).
    pub fn note_dest(&self, ids: &[String], team: &str) {
        if ids.is_empty() {
            return;
        }
        let mut t = self.tags.lock().unwrap_or_else(|e| e.into_inner());
        for id in ids {
            let slot = t.entry(id.clone()).or_default();
            if slot.dest.is_none() {
                slot.dest = Some(team.to_string());
            }
            slot.misses = 0;
        }
    }
    /// (M1·M5) 이 항목이 정지된 팀에 묶였나 — 꼬리표 팀(마스터 좌석 큐) 또는 목적지 팀(정지 팀 좌석 큐에서 옮겨 온 것).
    pub fn entry_team_paused(&self, entry_id: &str, paused: &HashSet<String>) -> bool {
        if paused.is_empty() {
            return false;
        }
        let t = self.tags.lock().unwrap_or_else(|e| e.into_inner());
        t.get(entry_id).is_some_and(|s| {
            s.tag.as_ref().is_some_and(|g| paused.contains(&g.team)) || s.dest.as_ref().is_some_and(|d| paused.contains(d))
        })
    }
    /// (M5) 역할 주차 중 팀 정지 크레딧 — 더하기 · 읽기.
    pub fn add_parked_credit(&self, entry_id: &str, secs: f64) {
        if let Some(s) = self.tags.lock().unwrap_or_else(|e| e.into_inner()).get_mut(entry_id) {
            s.parked_credit += secs;
        }
    }
    /// (codex 2R M5) 주차 크레딧을 **꺼낸다**(0 으로) — 승계 때 항목 `paused_total_secs` 로 옮기는 자리(활성 TTL 이 그 값만 보므로).
    pub fn take_parked_credit(&self, entry_id: &str) -> f64 {
        self.tags.lock().unwrap_or_else(|e| e.into_inner()).get_mut(entry_id).map_or(0.0, |s| std::mem::take(&mut s.parked_credit))
    }
    pub fn parked_credit(&self, entry_id: &str) -> f64 {
        self.tags.lock().unwrap_or_else(|e| e.into_inner()).get(entry_id).map_or(0.0, |s| s.parked_credit)
    }
    pub fn tag_count(&self) -> usize {
        self.tags.lock().unwrap_or_else(|e| e.into_inner()).len()
    }
    /// 꼬리표 청소(큐 틱마다 1회) — `live` = 데몬의 모든 큐(활성·만료·주차·복원)에 있는 id. 연속 2번 안 보인 칸만 지운다.
    pub fn sweep_tags(&self, live: &HashSet<String>) {
        let mut t = self.tags.lock().unwrap_or_else(|e| e.into_inner());
        t.retain(|id, slot| {
            if live.contains(id) {
                slot.misses = 0;
                return true;
            }
            slot.misses = slot.misses.saturating_add(1);
            slot.misses < 2
        });
    }
    /// team.stats 재료 — 그 팀 좌석이 마스터 좌석 큐에 넣은 시각.
    /// (codex 1R M6) 새 팀 키가 상한이면 먼저 모든 팀의 만료분·빈 키를 지우고, 그래도 차 있으면 마지막 보고가 가장 오래된 팀을 버린다.
    pub fn note_report(&self, team: &str, ts: f64) {
        let mut r = self.reports.lock().unwrap_or_else(|e| e.into_inner());
        if !r.contains_key(team) && r.len() >= REPORT_TEAMS_MAX {
            prune_reports(&mut r, ts);
            while r.len() >= REPORT_TEAMS_MAX {
                let Some(oldest) = r
                    .iter()
                    .min_by(|a, b| a.1.back().copied().unwrap_or(f64::MIN).total_cmp(&b.1.back().copied().unwrap_or(f64::MIN)))
                    .map(|(k, _)| k.clone())
                else {
                    break;
                };
                r.remove(&oldest);
            }
        }
        let q = r.entry(team.to_string()).or_default();
        q.push_back(ts);
        while q.front().is_some_and(|&t| ts - t > REPORT_WINDOW_SECS) || q.len() > REPORT_RING_MAX {
            q.pop_front();
        }
    }
    /// (codex 1R M6) 읽을 때 만료분·빈 팀 키를 **실제로** 지운다(사본만 거르던 것을 고침).
    pub fn reports(&self, now: f64) -> HashMap<String, Vec<f64>> {
        let mut r = self.reports.lock().unwrap_or_else(|e| e.into_inner());
        prune_reports(&mut r, now);
        r.iter().map(|(k, q)| (k.clone(), q.iter().copied().collect::<Vec<f64>>())).collect()
    }
    #[allow(dead_code)]
    pub fn report_team_count(&self) -> usize {
        self.reports.lock().unwrap_or_else(|e| e.into_inner()).len()
    }
    /// (codex 1R M4) 같은 팀 도우미 생성 문 — 앞 생성이 끝날 때까지 기다린다(상한 `ADMIT_WAIT_SECS` · 넘으면 None).
    pub fn admit(&self, team: &str, wait: std::time::Duration) -> Option<AdmitToken<'_>> {
        let deadline = std::time::Instant::now() + wait;
        let mut a = self.admitting.lock().unwrap_or_else(|e| e.into_inner());
        while a.contains(team) {
            let left = deadline.saturating_duration_since(std::time::Instant::now());
            if left.is_zero() {
                return None;
            }
            a = self.admit_cv.wait_timeout(a, left).unwrap_or_else(|e| e.into_inner()).0;
        }
        a.insert(team.to_string());
        Some(AdmitToken { book: self, team: team.to_string() })
    }
}

/// 보고 시각 링 청소 — 창 밖 시각과 빈 팀 키를 지운다.
fn prune_reports(r: &mut HashMap<String, VecDeque<f64>>, now: f64) {
    for q in r.values_mut() {
        while q.front().is_some_and(|&t| now - t > REPORT_WINDOW_SECS) {
            q.pop_front();
        }
    }
    r.retain(|_, q| !q.is_empty());
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
    /// (검증 m6) 본문에 급한 머리표가 있다 — ⑦ 몫 밖(전체 100 상한만 받는다).
    pub urgent: bool,
}

/// 넣기 전(잠금 밖) 계획: 대상이 마스터 ∧ 발신 좌석에 팀이 있을 때. progress = 꼬리표 ∧ 급한 머리표 없음 ∧ 팀 ≥ 2.
pub fn plan_enqueue(seats: &[SeatTeam], target: u64, from: Option<u64>, kind: Option<&str>, text: &str) -> Option<EnqueuePlan> {
    let t = seats.iter().find(|s| s.sid == target)?;
    if t.exited || !is_master_target(t.role.as_deref()) {
        return None;
    }
    let team = seats.iter().find(|s| Some(s.sid) == from)?.team.clone()?;
    let multi = distinct_teams(seats) >= 2;
    let urgent = is_urgent(text);
    let progress = multi && kind == Some(PROGRESS_KIND) && !urgent && !text.is_empty();
    Some(EnqueuePlan { team, multi, progress, urgent })
}

/// 넣는 자리의 입구 — 대상 좌석이 마스터일 때만 좌석 표를 훑는다(그 밖 좌석 큐 = 비용 0 · 계획 없음).
pub fn plan_for(daemon: &crate::state::Daemon, target: &crate::state::Surface, from: Option<u64>, kind: Option<&str>, text: &str) -> Option<EnqueuePlan> {
    let role = target.role.lock().unwrap_or_else(|e| e.into_inner()).clone();
    if !is_master_target(role.as_deref()) || from.is_none() {
        return None;
    }
    plan_enqueue(&snapshot(daemon), target.id, from, kind, text)
}

/// (codex 1R M2) 꼬리표 공개 — **넣은 그 `pending_queue` 잠금 안에서** 부른다(push_back 직후). 잠금을 놓은 뒤에 달면 그 사이
///   배달 틱이 꼬리표 없는 머리(정지·【진행】 보류 무시)를 보고, 동시 넣기가 몫을 덜 세어 몫을 넘긴다(29 + 2 = 31).
///   장부 잠금은 말단이다(pending_queue → book 순서 허용 · 반대 방향 0).
pub fn tag_entry(book: &TeamBook, entry_id: &str, plan: &EnqueuePlan) {
    book.tag(entry_id, EntryTag { team: plan.team.clone(), progress: plan.progress });
}

/// 넣은 뒤 기록(잠금 밖) — 보고 시각(team.stats 재료). 시험 이음매(M2)가 이 앞에서 돈다.
pub fn note_enqueued(book: &TeamBook, enqueued_at: f64, plan: &EnqueuePlan) {
    run_seam(&book.enqueue_seam);
    book.note_report(&plan.team, enqueued_at);
}

/// ⑦ 몫 판정(대상 큐 잠금 안에서) — 그 팀 항목 수 ≥ 몫이면 거절. 몫 0 = 끔 · 팀 1개 = 발효 0 · 급한 머리표 = 몫 밖(검증 m6).
pub fn share_exceeded(plan: &EnqueuePlan, tags: &HashMap<String, EntryTag>, share: usize) -> bool {
    plan.multi && !plan.urgent && share > 0 && tags.values().filter(|t| t.team == plan.team).count() >= share
}

/// ⑦ 대상 큐(잠금 안 · `q` = 그 가드) 기준 몫 넘침인가.
pub fn share_over(book: &TeamBook, q: &VecDeque<crate::state::QueueEntry>, plan: &EnqueuePlan) -> bool {
    if !plan.multi || plan.urgent {
        return false;
    }
    let live: Vec<&str> = q.iter().map(|e| e.id.as_str()).collect();
    share_exceeded(plan, &book.tags_for(&live), team_queue_share())
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

/// (codex 1R M3) 새 좌석이 **실제로** 갖게 될 팀 — `create_surface_with_env` 가 저장하는 cwd(파라미터 `cwd` · 없으면 홈 · 홈도 없으면 ".")
///   그대로의 폴더 이름. 파라미터 `group` 은 보지 않는다 — 만든 좌석의 `Surface.group` 은 늘 None 으로 시작하므로(state.rs),
///   판정에 넣으면 판정한 팀과 실제 팀이 갈린다(상한 우회·거짓 거절). 나중에 `surface.set_group` 으로 옮기는 것은 생성 문 밖.
pub fn create_team(params: &serde_json::Value) -> Option<String> {
    let cwd = params
        .get("cwd")
        .and_then(|v| v.as_str())
        .map(str::to_string)
        .unwrap_or_else(|| dirs::home_dir().map(|p| p.to_string_lossy().into_owned()).unwrap_or_else(|| ".".into()));
    team_of(Some("worker"), &None, &cwd)
}

/// ⑧ surface.create {role:worker} 의 팀별 상한 — 상한 0 = Ok(None)(문 없음 · 종전 바이트) · 넘으면 Err(거절 응답 · 사건 `team.worker_limit_denied`).
/// (codex 1R M4) 상한 > 0 이면 그 팀의 **생성 문**(`AdmitToken`)을 잡은 채로 세고 돌려준다 — 호출부는 좌석 표 삽입
///   (`create_surface_with_env` 반환)까지 쥐고 있다가 놓는다(성공·실패·뒤 게이트 거절 모두 drop = 반납). 같은 팀 동시 생성은 줄을 서고
///   다른 팀은 막지 않는다. 앞 생성이 `ADMIT_WAIT_SECS` 안에 안 끝나면 `team_worker_admission_busy`(무한 대기 0).
pub fn team_worker_gate<'a>(
    daemon: &'a crate::state::Daemon,
    id: &serde_json::Value,
    params: &serde_json::Value,
    caller_pid: Option<u32>,
) -> Result<Option<AdmitToken<'a>>, serde_json::Value> {
    let limit = max_team_workers();
    if limit == 0 {
        return Ok(None);
    }
    let Some(team) = create_team(params) else { return Ok(None) };
    let Some(token) = daemon.teams.admit(&team, std::time::Duration::from_secs(ADMIT_WAIT_SECS)) else {
        return Err(cys::err_response(id, TEAM_ADMIT_BUSY, &format!("another worker for team {team:?} is still being created — retry")));
    };
    let active = snapshot(daemon)
        .iter()
        .filter(|s| !s.exited && s.team.as_deref() == Some(team.as_str()))
        .filter(|s| s.role.as_deref().is_some_and(|r| r == "worker" || r.starts_with("worker-")))
        .count();
    run_seam(&daemon.teams.admit_seam);
    if active < limit {
        return Ok(Some(token));
    }
    drop(token);
    daemon.bus.publish(
        "team.worker_limit_denied",
        "system",
        None,
        serde_json::json!({"team": team, "limit": limit, "active": active, "path": "surface.create", "caller_pid": caller_pid}),
    );
    Err(cys::err_response(
        id,
        TEAM_WORKER_LIMIT,
        &format!("team worker limit reached for team {team:?}: {active}/{limit} (CYS_MAX_TEAM_WORKERS · 기본은 무제한)"),
    ))
}

/// (codex 1R M1) 좌석의 팀이 지금 정지 중인가(목적지 축) — 좌석별 말단 락만.
pub fn seat_team(s: &crate::state::Surface) -> Option<String> {
    let role = s.role.lock().unwrap_or_else(|e| e.into_inner()).clone();
    let group = s.group.lock().unwrap_or_else(|e| e.into_inner()).clone();
    team_of(role.as_deref(), &group, &s.cwd)
}

/// (codex 1R M1) 배달 한 건이 팀 정지에 걸리나 — 목적지 좌석 팀 정지 ∨ 실린 항목 중 정지 팀 꼬리표(·목적지 팀) 하나라도.
///   틱 임계영역(인계 직전 재확인)과 writer 안전 탐침(첫 바이트 앞)이 **같은 함수**를 쓴다(판정 분리 금지). 말단 락만.
pub fn delivery_team_paused(book: &TeamBook, dest_team: Option<&str>, ids: &[String]) -> bool {
    let paused = book.paused_set();
    if paused.is_empty() {
        return false;
    }
    dest_team.is_some_and(|t| paused.contains(t)) || ids.iter().any(|id| book.entry_team_paused(id, &paused))
}

/// (codex 1R M1) writer 안전 탐침에 팀 정지 축을 얹는다 — 기존 탐침이 막으면 그대로 막고, 아니면 지금 팀 정지를 본다.
///   writer 스레드에서 돈다: 데몬이 사라졌거나 패닉 = 막는다(기존 탐침과 같은 방향).
///   (codex 2R M1) 목적지 팀은 **첫 바이트 앞 그 순간** 좌석에서 다시 읽는다(인계 때 스냅숏 재사용 금지 — 그 사이 `surface.set_group` 으로
///   이미 정지된 팀에 옮겨지면 옛 팀 기준으로 통과했다). 좌석 role·group 락은 말단이다(쥔 채 큐·입력 락을 잡는 곳 0 — 탐침 락 규약 유지).
pub fn with_team_pause_probe(daemon: &std::sync::Arc<crate::state::Daemon>, s: &std::sync::Arc<crate::state::Surface>, ids: Vec<String>, base: crate::state::SafetyProbe) -> crate::state::SafetyProbe {
    let wd = std::sync::Arc::downgrade(daemon);
    let ws = std::sync::Arc::downgrade(s);
    std::sync::Arc::new(move || {
        if base() {
            return true;
        }
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let (Some(d), Some(s)) = (wd.upgrade(), ws.upgrade()) else { return true };
            delivery_team_paused(&d.teams, seat_team(&s).as_deref(), &ids)
        }))
        .unwrap_or(true)
    })
}

/// (codex 1R M1·M5) 팀 정지 **전환** 순간(정지 쪽) — `system.pause`(`cancel_unsettled_injects`)·건강 정지(`health_pause_queue`)와 같은 꼴:
///   ① 그 팀 좌석 큐 항목에 목적지 팀을 적는다(좌석이 죽어 주차·복원으로 가도 크레딧이 이어지게 · M5).
///   ② 결판 대기 중인 인계 예약이 그 팀에 걸리면(목적지 좌석이 그 팀 · 실린 항목이 그 팀 꼬리표) **취소**한다 — 예약 생성이
///      `pending_queue` 안이므로 같은 락 아래에서 취소해 창이 없다. 이미 writer 가 쓰기로 확정한 것은 못 끊는다 →
///      사건 `queue.inject_uncancellable {reason:"team_pause"}`(건강 정지와 같은 사건 · 그 항목은 나간다).
///   락 순서: surfaces(복사 후 놓음) → 좌석별 role·group(말단) → pending_queue → 장부(말단). 정지 플래그는 이 함수 **앞**에 이미 섰다.
pub fn on_team_paused(daemon: &crate::state::Daemon, team: &str) {
    let surfaces: Vec<std::sync::Arc<crate::state::Surface>> =
        daemon.surfaces.lock().unwrap_or_else(|e| e.into_inner()).values().cloned().collect();
    for s in surfaces {
        pause_seat_for_team(daemon, &s, team, "team_pause");
    }
}

/// (codex 2R M1) 좌석이 `surface.set_group` 으로 **이미 정지된** 팀에 들어왔을 때 — 정지 전환과 같은 좌석 처리(목적지 팀 기록 ·
///   결판 대기 예약 취소 · 확정분 사건). 정지 전환이 다시 돌지 않으므로 여기서 한다. 정지 안 된 팀이면 아무것도 안 함.
pub fn on_seat_regrouped(daemon: &crate::state::Daemon, s: &std::sync::Arc<crate::state::Surface>) {
    if let Some(t) = seat_team(s).filter(|t| daemon.teams.is_paused(t)) {
        pause_seat_for_team(daemon, s, &t, "team_pause_regroup");
    }
}

fn pause_seat_for_team(daemon: &crate::state::Daemon, s: &std::sync::Arc<crate::state::Surface>, team: &str, reason: &str) {
    let one: HashSet<String> = [team.to_string()].into_iter().collect();
    {
        let dest_hit = seat_team(s).as_deref() == Some(team);
        let q = s.pending_queue.lock().unwrap_or_else(|e| e.into_inner());
        if dest_hit {
            let ids: Vec<String> = q.iter().map(|e| e.id.clone()).collect();
            daemon.teams.note_dest(&ids, team);
        }
        let reserved: Vec<String> =
            s.inject_reservation.lock().unwrap_or_else(|e| e.into_inner()).as_ref().map(|r| r.ids.clone()).unwrap_or_default();
        if reserved.is_empty() || !(dest_hit || reserved.iter().any(|id| daemon.teams.entry_team_paused(id, &one))) {
            return;
        }
        let still = s.cancel_inject_reservation();
        drop(q);
        if !still.is_empty() {
            daemon.bus.publish(
                "queue.inject_uncancellable",
                "queue",
                Some(s.id),
                serde_json::json!({"reason": reason, "team": team, "entries": still.len(),
                       "hint": "팀 정지 전이 시점에 writer 가 이미 쓰기로 확정한 배달이 있다 — 그 항목은 나간다(다음 배달부터 정지)"}),
            );
        }
    }
}

/// (codex 1R M5) 큐 틱마다 — 역할 주차 큐의 항목 중 정지 팀에 묶인 것(꼬리표 팀 · 목적지 팀)에 이번 틱 크레딧을 더한다.
///   활성 큐 크레딧과 같은 식(`delta.min(alive_for)` · alive_for = 넣은 뒤 지난 시간). 데몬 정지는 주차 TTL 에 크레딧을 주지 않으므로(원작자
///   규칙 · 항목 enqueued_at 기준) 팀 정지 크레딧만 따로 적는다. 락: parked_queues 1개 → 장부(말단).
pub fn credit_parked(daemon: &crate::state::Daemon, paused: &HashSet<String>, now: f64, delta: f64) {
    if paused.is_empty() || delta <= 0.0 || daemon.teams.tag_count() == 0 {
        return;
    }
    let map = daemon.parked_queues.lock().unwrap_or_else(|e| e.into_inner());
    for pq in map.values() {
        for e in &pq.entries {
            if daemon.teams.entry_team_paused(&e.id, paused) {
                daemon.teams.add_parked_credit(&e.id, delta.min((now - e.enqueued_at).max(0.0)));
            }
        }
    }
}

/// (codex 1R M5) 역할 주차 큐 TTL 판정 — 항목 `enqueued_at` 기준 + 주차 중 받은 팀 정지 크레딧(주차 TTL 은 종전처럼 데몬 정지 크레딧은 안 받는다).
pub fn parked_alive(book: &TeamBook, e: &crate::state::QueueEntry, now: f64) -> bool {
    now - e.enqueued_at - book.parked_credit(&e.id) < crate::state::PARKED_QUEUE_TTL_SECS
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

/// ⑩ 머리가 풀린 【진행】 항목이면 함께 실을 같은 팀 【진행】 항목 위치(머리 포함) · 아니면 None.
/// 같은 발신자 병합(`plan_queue_merge`)과 같은 두 규칙을 따른다:
///   · (검증 m5) **머리에서 이어진 구간만** — 다른 항목(다른 팀 · 꼬리표 없음)을 만나면 멈춘다(건너뛰어 당기면 들어온 순서가 깨진다 · codex R1-blocking-3).
///   · (검증 M1) 상한 = 항목 수 `max_items` + **최종 렌더 글자 수** `max_chars` — 넘을 항목부터 다음 배달로 이월(자르지 않음 · 머리 1건은 늘 배달).
/// `sizes[i]` = i번 항목의 (발신 라벨, 원문 글자 수) — `entries` 와 같은 순서.
pub fn bundle_pick(
    view: &HoldView<'_>,
    entries: &[(&str, f64)],
    sizes: &[(Option<String>, usize)],
    max_items: usize,
    max_chars: usize,
) -> Option<(String, Vec<usize>)> {
    let (head, _) = entries.first()?;
    let t = view.tags.get(*head)?;
    if !t.progress || !view.multi || view.held(head, entries) {
        return None;
    }
    let team = t.team.clone();
    let rendered_len = |idx: &[usize]| {
        let parts: Vec<(Option<String>, String)> = idx
            .iter()
            .map(|&j| sizes.get(j).map(|(f, n)| (f.clone(), "x".repeat(*n))).unwrap_or((None, String::new())))
            .collect();
        render_bundle(&team, &parts).chars().count()
    };
    let mut picked = vec![0usize];
    for (i, (id, _)) in entries.iter().enumerate().skip(1) {
        if picked.len() >= max_items.max(1) {
            break;
        }
        if !view.tags.get(*id).is_some_and(|x| x.progress && x.team == team) {
            break; // 이어진 구간 끝(검증 m5)
        }
        let mut cand = picked.clone();
        cand.push(i);
        if rendered_len(&cand) > max_chars {
            break; // 글자 상한 — 남은 것은 다음 배달(검증 M1)
        }
        picked = cand;
    }
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

/// (검증 m3) 큐 틱마다 1회 — 데몬의 모든 큐(좌석 활성·만료 · 역할 주차 · 복원)에 있는 항목 id 를 모아 꼬리표를 청소한다.
/// 각 잠금을 하나씩만 잡는다(겹쳐 쥐지 않음) · 꼬리표 0 = 비용 0. 옮기는 도중 한 번 빠진 id 는 `sweep_tags` 의 2회 규칙이 살린다.
pub fn sweep_daemon_tags(daemon: &crate::state::Daemon, surfaces: &[std::sync::Arc<crate::state::Surface>]) {
    if daemon.teams.tag_count() == 0 {
        return;
    }
    let mut live: HashSet<String> = HashSet::new();
    for s in surfaces {
        live.extend(s.pending_queue.lock().unwrap_or_else(|e| e.into_inner()).iter().map(|e| e.id.clone()));
        live.extend(s.expired_queue.lock().unwrap_or_else(|e| e.into_inner()).iter().map(|e| e.id.clone()));
    }
    for pq in daemon.parked_queues.lock().unwrap_or_else(|e| e.into_inner()).values() {
        live.extend(pq.entries.iter().map(|e| e.id.clone()));
    }
    for row in daemon.restored_queue.lock().unwrap_or_else(|e| e.into_inner()).iter() {
        if let Some(id) = row.get("id").and_then(|v| v.as_str()) {
            live.insert(id.to_string());
        }
    }
    daemon.teams.sweep_tags(&live);
}

/// (검증 m4) 정지 목록 파일 경로 — 데몬 상태 폴더(소켓과 같은 곳).
pub fn paused_file(daemon: &crate::state::Daemon) -> std::path::PathBuf {
    crate::state::state_dir(&daemon.socket_path).join(PAUSED_FILE)
}

/// (검증 m4) 정지 목록이 바뀐 뒤 이름 목록만 원자 쓰기(빈 목록 = 파일 지움) · 실패 = 로그 1줄(배달 계약과 무관 · 최선 노력).
pub fn persist_paused(daemon: &crate::state::Daemon) {
    let _g = daemon.teams.persist_gate.lock().unwrap_or_else(|e| e.into_inner());
    let path = paused_file(daemon);
    let list = daemon.teams.paused_list();
    let r = if list.is_empty() {
        match std::fs::remove_file(&path) {
            Err(e) if e.kind() != std::io::ErrorKind::NotFound => Err(e),
            _ => Ok(()),
        }
    } else {
        cys::atomic_write_json(&path, &serde_json::json!({"paused": list, "note": "names only — a daemon restart does not restore the pause (team.pause_lost)"}))
    };
    if let Err(e) = r {
        eprintln!("[cysd] team pause list write failed ({}): {e}", path.display());
    }
}

/// (검증 m4) 데몬 시작 때 1회 — 앞 실행이 남긴 정지 목록이 있으면 사건 `team.pause_lost` 1건 + 파일 지움(정지는 되살리지 않는다).
pub fn announce_lost_pauses(daemon: &crate::state::Daemon) {
    let path = paused_file(daemon);
    let Ok(meta) = std::fs::metadata(&path) else { return };
    // (codex 1R B1) 파일 상한 — 넘으면 이름을 읽지 않는다(지우고 「목록을 못 읽음」 사건 1건).
    let oversize = meta.len() > PAUSED_FILE_MAX_BYTES;
    let raw = if oversize { String::new() } else { std::fs::read_to_string(&path).unwrap_or_default() };
    let _ = std::fs::remove_file(&path);
    let teams: Vec<String> = serde_json::from_str::<serde_json::Value>(&raw)
        .ok()
        .and_then(|v| {
            v.get("paused").and_then(|p| p.as_array()).map(|a| {
                a.iter().filter_map(|x| x.as_str()).filter(|t| !t.is_empty() && t.chars().count() <= 64).take(PAUSED_TEAMS_MAX).map(str::to_string).collect()
            })
        })
        .unwrap_or_default();
    if teams.is_empty() && !oversize {
        return;
    }
    daemon.bus.publish(
        EV_PAUSE_LOST,
        "queue",
        None,
        serde_json::json!({"teams": teams, "reason": "daemon_restart", "list_unreadable": oversize, "note": "팀 정지가 풀렸어요 — 데몬이 다시 켜져 정지 기록이 비었습니다. 계속 멈춰 두려면 다시 정지해 주세요."}),
    );
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
        assert_eq!(team_of(Some("ceo"), &Some(Some("홍보".into())), "/x/site"), None, "ceo = 마스터급 고정 좌석(검증 i7)");
        assert_eq!(team_of(Some("ceo-2"), &None, "/x/site"), None);
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
        let pa = EnqueuePlan { team: "a".into(), multi: true, progress: false, urgent: false };
        let pb = EnqueuePlan { team: "b".into(), multi: true, progress: false, urgent: false };
        assert!(share_exceeded(&pa, &tags, 3));
        assert!(!share_exceeded(&pb, &tags, 3));
        assert!(!share_exceeded(&pa, &tags, 0), "0 = 끔");
        assert!(!share_exceeded(&EnqueuePlan { multi: false, ..pa.clone() }, &tags, 3), "팀 1개 = 발효 0");
        assert!(!share_exceeded(&EnqueuePlan { urgent: true, ..pa.clone() }, &tags, 3), "급한 머리표 = 몫 밖(검증 m6)");
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
        let sizes: Vec<(Option<String>, usize)> = vec![(None, 2); 3];
        assert!(bundle_pick(&v, &entries, &sizes, 10, 4000).is_none(), "창 전 = 묶지 않음");
        let v2 = HoldView { now: 701.0, ..v };
        assert!(!v2.held("p1", &entries));
        assert_eq!(bundle_pick(&v2, &entries, &sizes, 10, 4000), Some(("a".into(), vec![0])), "이어진 구간만 — n1(다른 팀)을 건너뛰지 않음(검증 m5)");
        let joined = [("p1", 100.0), ("p2", 200.0), ("n1", 150.0)];
        assert_eq!(bundle_pick(&v2, &joined, &sizes, 10, 4000), Some(("a".into(), vec![0, 1])));
        assert_eq!(bundle_pick(&v2, &joined, &sizes, 10, 20), Some(("a".into(), vec![0])), "글자 상한 = 이월 · 머리는 늘 배달(검증 M1)");
        // 정지된 팀 — 꼬리표 없는 항목도 보류
        let mut ps = HashSet::new();
        ps.insert("b".to_string());
        let v3 = HoldView { tags: &tags, paused: &ps, multi: true, bundle_secs: 600, now: 701.0 };
        assert!(v3.held("n1", &entries));
        assert_eq!(rotate_order(&[true, true]), None, "전부 보류 = 그대로");
        assert_eq!(rotate_order(&[false, true]), None, "머리가 보낼 것 = 그대로");
    }

    #[test]
    fn tags_follow_entry_id_and_sweep_needs_two_misses() {
        let b = TeamBook::default();
        b.tag("q1.1", EntryTag { team: "a".into(), progress: true });
        b.tag("q1.2", EntryTag { team: "b".into(), progress: false });
        assert_eq!(b.tags_for(&["q1.1", "zz"]).len(), 1, "어느 큐에서 읽든 항목 id 로 찾는다(검증 m3)");
        let live: HashSet<String> = ["q1.1".to_string()].into_iter().collect();
        b.sweep_tags(&live);
        assert_eq!(b.tag_count(), 2, "한 번 안 보임 = 살림(옮기는 도중)");
        b.sweep_tags(&HashSet::new());
        assert_eq!(b.tag_count(), 1, "q1.2 = 연속 2번 안 보임 → 지움 · q1.1 = 앞 청소에서 보였으므로 1번째");
        b.sweep_tags(&live);
        b.sweep_tags(&HashSet::new());
        assert_eq!(b.tag_count(), 1, "보이면 횟수 0 으로");
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
