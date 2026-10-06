//! `cys self-update --check [--json]` — 피드 검증 + 게이트 판정 **만**(교체 0 · 쓰기 0). 설계 AUTO-UPDATE-118 §3-4 끝줄
//! 「결과는 `cys self-update --check --json` 으로 그대로 보인다」 · §8 U1 행.
//!
//! 사실 모으기 순서 = 게이트 판정 순서와 같은 「싼 것 먼저」이지만, 표시를 위해 끝까지 모은다(전부 읽기 — 파일·OS 조회·
//! 데몬 RPC). 데몬에서 오는 사실(좌석·승인 대기)은 CLI 바이너리 쪽 함수로 받는다([`Hooks`]) — 재주입 3신호 판정
//! (`adapter_ready`)이 CLI 바이너리에 있어 사본을 만들지 않기 위해서다.
//!
//! U1 에서 정직하게 「모름/미구현」인 칸: N14(복구기 등록 = U2) → 늘 보류 · N7(롤백 자산 공간 계산 = U2 스냅샷 실측 뒤) →
//! 판정 불가 보류. 그래서 U1 판의 `--check` 결정은 언제나 `hold` 이다(교체 경로가 없는 판에서 올바른 답).

use super::buildinfo;
use super::clock;
use super::feed::{self, AcceptedFeed, FeedInput, FeedOutcome, Verdict};
use super::gates::{self, Facts, Power, SeatFact};
use super::keys::UpdateKeyring;
use super::net;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::Path;

/// 데몬 쪽 사실 공급자(CLI 바이너리가 채운다 · 데몬 없음 = None = 판정 불가).
pub struct Hooks<'a> {
    pub seats: &'a dyn Fn() -> Option<Vec<SeatFact>>,
    pub pending_approvals: &'a dyn Fn() -> Option<u64>,
}

// ── 상태 폴더 안 작은 기록들(읽기 전용) ─────────────────────────────────────────────────────

/// `<상태>/config.json` — `{auto: bool, channel: "stable"|"next"}` · 부재 = 기본(auto ON · 📌5 · stable).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Config {
    #[serde(default = "default_true")]
    pub auto: bool,
    #[serde(default = "default_channel")]
    pub channel: String,
}

fn default_true() -> bool {
    true
}
fn default_channel() -> String {
    "stable".into()
}

impl Default for Config {
    fn default() -> Self {
        Config { auto: true, channel: default_channel() }
    }
}

/// 부재 = Ok(기본) · 손상 = Err(→ N9 판정 불가).
pub fn read_config(dir: &Path) -> Result<Config, String> {
    match std::fs::read(dir.join("config.json")) {
        Ok(b) => serde_json::from_slice(&b).map_err(|e| format!("config.json 손상: {e}")),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(Config::default()),
        Err(e) => Err(e.to_string()),
    }
}

/// `<상태>/holds.json` — `{holds:[{until, reason}]}` · 지금을 덮는 것이 있으면 true(N5 ⓐ).
pub fn holds_active(dir: &Path, now: i64) -> Option<bool> {
    match std::fs::read(dir.join("holds.json")) {
        Ok(b) => {
            let v: Value = serde_json::from_slice(&b).ok()?;
            let arr = v.get("holds")?.as_array()?;
            Some(arr.iter().any(|h| h.get("until").and_then(|u| u.as_i64()).map(|u| u > now).unwrap_or(true)))
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Some(false),
        Err(_) => None,
    }
}

/// `<상태>/state.json` 의 N8 칸 — `{last_success: Stamp?, failures: {"<c>/<ch>/<t>/<seq>": {class, count, next_at}}}`.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct UpdState {
    #[serde(default)]
    pub last_success: Option<clock::Stamp>,
    #[serde(default)]
    pub failures: std::collections::BTreeMap<String, Failure>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Failure {
    /// "permanent" | "transient"
    pub class: String,
    pub count: u32,
    pub next_at: i64,
}

pub fn failure_key(component: &str, channel: &str, target: &str, release_seq: u64) -> String {
    format!("{component}/{channel}/{target}/{release_seq}")
}

pub fn read_state(dir: &Path) -> Result<UpdState, String> {
    match std::fs::read(dir.join("state.json")) {
        Ok(b) => serde_json::from_slice(&b).map_err(|e| format!("state.json 손상: {e}")),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(UpdState::default()),
        Err(e) => Err(e.to_string()),
    }
}

/// 신뢰 앵커(`trusted.json`) — ★1R B3·H⑪: 마지막 수용 폐기문의 rev·원문 sha256·수용 시각(Stamp)과 마지막 신뢰 시각.
/// 원문은 `revocations.accepted.json` + `.minisig` 로 따로 보존한다(피드 미도달 때 30일까지 대신 쓴다 · §4-1).
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct Trusted {
    #[serde(default)]
    pub revocations_rev: Option<u64>,
    #[serde(default)]
    pub revocations_sha256: Option<String>,
    #[serde(default)]
    pub revocations_accepted_at: Option<clock::Stamp>,
    #[serde(default)]
    pub last_trusted_time: Option<i64>,
}

pub const REV_COPY: &str = "revocations.accepted.json";
pub const REV_COPY_SIG: &str = "revocations.accepted.json.minisig";
/// 폐기문 대체본 수명(§4-1 「못 읽으면 마지막 수용본으로 판정하되 그 수용본이 30일 넘었으면 보류」).
pub const REVOCATIONS_MAX_AGE_SECS: u64 = 30 * 86_400;

pub fn read_trusted(dir: &Path) -> Result<Trusted, String> {
    match std::fs::read(dir.join("trusted.json")) {
        Ok(b) => serde_json::from_slice(&b).map_err(|e| format!("trusted.json 손상: {e}")),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(Trusted::default()),
        Err(e) => Err(e.to_string()),
    }
}

fn write_trusted(dir: &Path, t: &Trusted) -> Result<(), String> {
    let b = serde_json::to_vec_pretty(t).map_err(|e| e.to_string())?;
    super::write_private(&dir.join("trusted.json"), &b)
}

/// 신뢰 시각 단조 상향(내려가지 않음).
pub fn bump_trusted(dir: &Path, signed_at: Option<i64>) -> Result<Trusted, String> {
    let mut t = read_trusted(dir)?;
    let next = match (t.last_trusted_time, signed_at) {
        (Some(a), Some(b)) => Some(a.max(b)),
        (a, b) => a.or(b),
    };
    if next != t.last_trusted_time {
        t.last_trusted_time = next;
        write_trusted(dir, &t)?;
    }
    Ok(t)
}

/// ★1R B3: R 검증을 통과한 폐기문을 **그 즉시** 내구 기록(원문·서명·sha256·rev·수용 Stamp) — 뒤 단계(봉투·본문) 실패와 무관.
/// rev 후퇴 = 거부 · 같은 rev 인데 원문이 다름 = 거부(옛 기록 유지 · R 서명자 실수 신호) · 같은 원문 = 수용 시각만 새로.
pub fn record_revocations(dir: &Path, bytes: &[u8], sig: &[u8], rev: u64, signed_at: i64) -> Result<Trusted, String> {
    let mut t = read_trusted(dir)?;
    let sha = super::feed::sha256_hex(bytes);
    if let Some(cur) = t.revocations_rev {
        if rev < cur {
            return Err(format!("폐기문 rev 후퇴 {rev} < {cur}"));
        }
        if rev == cur && t.revocations_sha256.as_deref() != Some(sha.as_str()) {
            return Err(format!("같은 폐기문 rev {rev} 다른 원문 — 기록 거부"));
        }
    }
    super::write_private(&dir.join(REV_COPY), bytes)?;
    super::write_private(&dir.join(REV_COPY_SIG), sig)?;
    t.revocations_rev = Some(rev);
    t.revocations_sha256 = Some(sha);
    t.revocations_accepted_at = Some(clock::now_stamp());
    t.last_trusted_time = Some(t.last_trusted_time.unwrap_or(i64::MIN).max(signed_at));
    write_trusted(dir, &t)?;
    Ok(t)
}

/// 피드 미도달 때의 폐기문 대체본 — 수용 뒤 30일 이내(낡음 타이머 = 시계 의심이면 낡음)·원문 sha256 = 기록일 때만.
pub fn load_accepted_revocations(dir: &Path, now: &clock::Stamp, wall_suspect: bool) -> Result<(Vec<u8>, Vec<u8>), String> {
    let t = read_trusted(dir)?;
    let at = t.revocations_accepted_at.ok_or("수용 폐기문 없음")?;
    let age = clock::elapsed_for_staleness(&at, now, wall_suspect, t.last_trusted_time);
    if age > REVOCATIONS_MAX_AGE_SECS && !super::mutant("B3") {
        return Err(format!("수용 폐기문 30일 넘음({}일) — 보류", age / 86_400));
    }
    let b = std::fs::read(dir.join(REV_COPY)).map_err(|e| e.to_string())?;
    let s = std::fs::read(dir.join(REV_COPY_SIG)).map_err(|e| e.to_string())?;
    if t.revocations_sha256.as_deref() != Some(super::feed::sha256_hex(&b).as_str()) {
        return Err("수용 폐기문 원문 sha256 불일치".into());
    }
    Ok((b, s))
}

pub fn accepted_path(dir: &Path, component: &str, channel: &str) -> std::path::PathBuf {
    dir.join(format!("accepted-{component}-{channel}.json"))
}

// ── OS 사실 ──────────────────────────────────────────────────────────────────────────

/// N6 전원. 맥 = `pmset -g adapter`(★`-g batt`·`-g ps` 는 80% 유지 앱 아래에서 「배터리 사용 중」을 거짓 보고 — 금지)
/// + 배터리 % = `ioreg -rn AppleSmartBattery` 의 CurrentCapacity/MaxCapacity · 윈 = `GetSystemPowerStatus`.
pub fn power() -> Option<Power> {
    #[cfg(target_os = "macos")]
    {
        let out = crate::hidden_command("pmset").args(["-g", "adapter"]).output().ok()?;
        if !out.status.success() {
            return None;
        }
        let adapter = parse_pmset_adapter(&String::from_utf8_lossy(&out.stdout));
        let battery_pct = crate::hidden_command("ioreg")
            .args(["-rn", "AppleSmartBattery"])
            .output()
            .ok()
            .and_then(|o| parse_ioreg_battery_pct(&String::from_utf8_lossy(&o.stdout)));
        return Some(Power { adapter, battery_pct });
    }
    #[cfg(windows)]
    {
        #[repr(C)]
        struct SystemPowerStatus {
            ac_line_status: u8,
            battery_flag: u8,
            battery_life_percent: u8,
            system_status_flag: u8,
            battery_life_time: u32,
            battery_full_life_time: u32,
        }
        #[link(name = "kernel32")]
        extern "system" {
            fn GetSystemPowerStatus(s: *mut SystemPowerStatus) -> i32;
        }
        let mut s = SystemPowerStatus {
            ac_line_status: 255,
            battery_flag: 255,
            battery_life_percent: 255,
            system_status_flag: 0,
            battery_life_time: 0,
            battery_full_life_time: 0,
        };
        // SAFETY: s 는 유효한 지역 구조체(Win32 SYSTEM_POWER_STATUS 와 같은 배치).
        if unsafe { GetSystemPowerStatus(&mut s) } == 0 {
            return None;
        }
        // 128 = 배터리 없음(데스크톱) · 255 = 모름.
        let battery_pct = if s.battery_flag == 128 || s.battery_life_percent > 100 { None } else { Some(s.battery_life_percent) };
        return match s.ac_line_status {
            1 => Some(Power { adapter: true, battery_pct }),
            0 => Some(Power { adapter: false, battery_pct }),
            _ => None,
        };
    }
    #[allow(unreachable_code)]
    None
}

/// `pmset -g adapter` — 연결 = 와트 등 줄이 있음 · `No adapter attached.` = 미연결.
pub fn parse_pmset_adapter(s: &str) -> bool {
    let t = s.trim();
    !t.is_empty() && !t.contains("No adapter attached")
}

/// `ioreg -rn AppleSmartBattery` → 배터리 %(CurrentCapacity × 100 / MaxCapacity). 배터리 없음 = None.
pub fn parse_ioreg_battery_pct(s: &str) -> Option<u8> {
    let num = |key: &str| -> Option<u64> {
        s.lines().find_map(|l| {
            let l = l.trim();
            let rest = l.strip_prefix(&format!("\"{key}\" = "))?;
            rest.trim().parse().ok()
        })
    };
    let cur = num("CurrentCapacity")?;
    let max = num("MaxCapacity").filter(|m| *m > 0)?;
    Some(((cur * 100) / max).min(100) as u8)
}

/// N2 OS 입력 유휴(초). 맥 = `ioreg -c IOHIDSystem` 의 HIDIdleTime(ns) · 윈 = `GetLastInputInfo`.
pub fn os_idle_secs() -> Option<u64> {
    #[cfg(target_os = "macos")]
    {
        let out = crate::hidden_command("ioreg").args(["-c", "IOHIDSystem", "-d", "4"]).output().ok()?;
        return parse_hid_idle_secs(&String::from_utf8_lossy(&out.stdout));
    }
    #[cfg(windows)]
    {
        #[repr(C)]
        struct LastInputInfo {
            cb_size: u32,
            dw_time: u32,
        }
        #[link(name = "user32")]
        extern "system" {
            fn GetLastInputInfo(p: *mut LastInputInfo) -> i32;
        }
        #[link(name = "kernel32")]
        extern "system" {
            fn GetTickCount() -> u32;
        }
        let mut li = LastInputInfo { cb_size: std::mem::size_of::<LastInputInfo>() as u32, dw_time: 0 };
        // SAFETY: li 는 유효한 지역 구조체 · cb_size 채움.
        if unsafe { GetLastInputInfo(&mut li) } == 0 {
            return None;
        }
        let now = unsafe { GetTickCount() };
        return Some((now.wrapping_sub(li.dw_time) / 1000) as u64);
    }
    #[allow(unreachable_code)]
    None
}

pub fn parse_hid_idle_secs(s: &str) -> Option<u64> {
    s.lines().find_map(|l| {
        // 실측 줄 모양(ioreg 트리 접두 포함): `    | |     "HIDIdleTime" = 13552806131833`
        let rest = l.split_once("\"HIDIdleTime\" = ")?.1;
        rest.trim().parse::<u64>().ok().map(|ns| ns / 1_000_000_000)
    })
}

// ── 판정 ─────────────────────────────────────────────────────────────────────────────

/// 피드 받기 + 검증(읽기 전용). Err = 미도달(조용히 끝 · daily 칸). 폐기문만 못 받으면 30일 이내 수용본으로 대신한다(§4-1).
pub fn fetch_and_verify(dir: &Path, channel: &str, now: i64) -> Result<(FeedOutcome, Vec<Option<i64>>), String> {
    let base = net::feed_base(cfg!(debug_assertions), |k| std::env::var(k).ok());
    let get = |rel: &str| net::fetch_feed_file(&base, rel).map_err(|e| format!("{rel}: {e:?}"));
    let env = get(&format!("cysr/{channel}.json"))?;
    let env_sig = get(&format!("cysr/{channel}.json.minisig"))?;
    let trusted = read_trusted(dir);
    let (accepted_rev, last_trusted) = match &trusted {
        Ok(t) => (t.revocations_rev, t.last_trusted_time),
        Err(_) => (None, None),
    };
    let mut dates = vec![env.http_date, env_sig.http_date];
    let (rev_bytes, rev_sig) = match (get("revocations.json"), get("revocations.json.minisig")) {
        (Ok(a), Ok(b)) => {
            dates.push(a.http_date);
            dates.push(b.http_date);
            (a.bytes, b.bytes)
        }
        _ => {
            let suspect = clock::clock_suspect_dates(now, last_trusted, &dates);
            load_accepted_revocations(dir, &clock::now_stamp(), suspect).map_err(|e| format!("폐기문 미도달 · {e}"))?
        }
    };
    let accepted: Result<Option<AcceptedFeed>, String> = match &trusted {
        Err(e) => Err(e.clone()),
        Ok(_) => feed::read_accepted(&accepted_path(dir, "cysr", channel)),
    };
    let keyring = UpdateKeyring::embedded().map_err(|e| format!("내장 키링: {e}"))?;
    let bucket = buildinfo::read_install_id(dir).map(|id| feed::rollout_bucket(&id));
    let inp = FeedInput {
        component: "cysr",
        channel,
        envelope: &env.bytes,
        envelope_sig: &env_sig.bytes,
        revocations: &rev_bytes,
        revocations_sig: &rev_sig,
        now,
        clock_suspect: clock::clock_suspect_dates(now, last_trusted, &dates),
        accepted,
        accepted_rev,
        keyring: &keyring,
        installed_release_seq: buildinfo::release_seq(),
        target: buildinfo::TARGET,
        rollout_bucket: bucket,
    };
    Ok((feed::verify_feed(&inp), dates))
}

/// 게이트 사실 모으기(읽기 전용).
pub fn gather_facts(dir: &Path, pack_dir: &Path, outcome: Option<&FeedOutcome>, http_dates: &[Option<i64>], now: i64, hooks: &Hooks) -> Facts {
    let cfg = read_config(dir);
    let trusted = read_trusted(dir).ok();
    let st = read_state(dir);
    let target = buildinfo::TARGET;
    let channel = cfg.as_ref().map(|c| c.channel.clone()).unwrap_or_else(|_| default_channel());
    let journal_open = match super::journal::read(dir) {
        super::journal::ReadOutcome::Absent => Some(false),
        super::journal::ReadOutcome::Corrupt(_) => None,
        o => o.journal().map(|j| !j.state.is_terminal()),
    };
    let lock_held = if dir.join(super::lock::LOCK_FILE).exists() { super::lock::is_held(dir) } else { Some(false) };
    let pending_restore = pack_dir.parent().map(|p| p.join(".pending-restore").exists());
    let pack_journal = pack_dir
        .parent()
        .map(|p| p.join(".pack-journal"))
        .map(|j| std::fs::read_dir(&j).map(|mut r| r.next().is_some()).unwrap_or(false));
    let other_txn = match (journal_open, lock_held, pending_restore, pack_journal) {
        (Some(a), Some(b), Some(c), Some(d)) => Some(a || b || c || d),
        _ => None,
    };
    let since_last = st.as_ref().ok().map(|s| match &s.last_success {
        None => u64::MAX,
        Some(then) => clock::elapsed_for_wait(
            then,
            &clock::now_stamp(),
            clock::clock_suspect_dates(now, trusted.as_ref().and_then(|t| t.last_trusted_time), http_dates),
            trusted.as_ref().and_then(|t| t.last_trusted_time),
        ),
    });
    let failure_blocks = match (&st, outcome.and_then(|o| o.release_seq)) {
        (Ok(s), Some(seq)) => Some(
            s.failures
                .get(&failure_key("cysr", &channel, target, seq))
                .map(|f| f.class == "permanent" || f.next_at > now)
                .unwrap_or(false),
        ),
        (Ok(_), None) => Some(false),
        (Err(_), _) => None,
    };
    let sched = super::sched::schedule_facts(&super::sched::schedule_files(pack_dir), chrono::Local::now());
    // 보류 로그 미배달 = 마지막 hold_seq − 배달 커서(커서 없음 = 0 = 전부 미배달 · 보수). 읽기 전용(꼬리 자르기 0).
    let hold_undelivered = super::hold::last_seq_readonly(dir).map(|last| {
        let delivered = std::fs::read(dir.join("hold-cursor.json"))
            .ok()
            .and_then(|b| serde_json::from_slice::<Value>(&b).ok())
            .and_then(|v| v.get("delivered_hold_seq").and_then(|x| x.as_u64()))
            .unwrap_or(0);
        last.saturating_sub(delivered)
    });
    Facts {
        auto_enabled: cfg.as_ref().ok().map(|c| c.auto),
        envelope_halt: outcome.map(|o| o.halt).unwrap_or(false),
        other_txn,
        since_last_update_secs: since_last,
        failure_blocks,
        installed_release_seq: Some(buildinfo::release_seq()),
        min_from_release_seq: outcome.and_then(|o| o.min_from_release_seq),
        clock_suspect: Some(clock::clock_suspect_dates(now, trusted.as_ref().and_then(|t| t.last_trusted_time), http_dates)),
        // N14: 복구기(LaunchAgent·로그온 작업) 등록·검증은 U2 — 이 판에는 등록이 없으므로 「미등록」(보류).
        recover_agent_ok: Some(false),
        power: power(),
        sac_state: super::win::sac_fact(),
        holds_active: holds_active(dir, now),
        pending_approvals: (hooks.pending_approvals)(),
        publish_within_48h: sched.map(|s| s.publish_within_48h),
        bulk_within_48h: sched.map(|s| s.bulk_within_48h),
        nonbulk_within_60m: sched.map(|s| s.nonbulk_within_60m),
        hold_log_undelivered: hold_undelivered,
        seats: (hooks.seats)(),
        os_idle_secs: os_idle_secs(),
        // N7: 공간 식(§3-5 MA3)의 「직전 실측 백업량」은 U2 스냅샷 실측 뒤 — 지금은 판정 불가(보류).
        rollback_assets_ok: None,
    }
}

/// `--check` 본체 — JSON 보고와 rc(0 = 판정함 · 2 = 피드 거부 · 3 = 피드 판정 불가·미도달).
pub fn run_check(dir: &Path, pack_dir: &Path, hooks: &Hooks) -> (Value, i32) {
    let now = clock::wall_now();
    let cfg = read_config(dir).unwrap_or_default();
    let (feed_json, outcome, dates, rc) = match fetch_and_verify(dir, &cfg.channel, now) {
        Ok((o, d)) => {
            let rc = o.verdict.rc();
            (o.to_json(), Some(o), d, rc)
        }
        Err(e) => (json!({"verdict": "unreachable", "detail": e}), None, vec![], 3),
    };
    let facts = gather_facts(dir, pack_dir, outcome.as_ref(), &dates, now, hooks);
    let report = gates::evaluate(&facts);
    let decision = match outcome.as_ref().map(|o| o.verdict) {
        Some(Verdict::Apply) if report.pass => "apply",
        Some(Verdict::Apply) => "hold",
        Some(v) => v.as_str(),
        None => "unreachable",
    };
    let out = json!({
        "decision": decision,
        "replace": false, // U1 = 판정만(교체 0)
        "channel": cfg.channel,
        "build": buildinfo::build_info(),
        "feed": feed_json,
        "gates": report,
        "facts": facts,
    });
    (out, rc)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp(tag: &str) -> std::path::PathBuf {
        let d = std::env::temp_dir().join(format!("cys-u1-chk-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn parsers() {
        assert!(parse_pmset_adapter(" - Wattage = 140W\n - Current = 7000mA\n"));
        assert!(!parse_pmset_adapter("No adapter attached.\n"));
        assert!(!parse_pmset_adapter(""));
        let io = "  \"MaxCapacity\" = 100\n  \"CurrentCapacity\" = 80\n";
        assert_eq!(parse_ioreg_battery_pct(io), Some(80));
        assert_eq!(parse_ioreg_battery_pct("  \"MaxCapacity\" = 5000\n  \"CurrentCapacity\" = 2500\n"), Some(50));
        assert_eq!(parse_ioreg_battery_pct(""), None);
        assert_eq!(parse_hid_idle_secs("    | |   \"HIDIdleTime\" = 125000000000\n"), Some(125));
        assert_eq!(parse_hid_idle_secs("    | | |   \"HIDIdleTime\" = 13552831732708\n"), Some(13552));
        assert_eq!(parse_hid_idle_secs("nothing"), None);
    }

    #[test]
    fn local_records_defaults_and_corruption() {
        let d = tmp("rec");
        assert_eq!(read_config(&d).unwrap(), Config::default());
        std::fs::write(d.join("config.json"), br#"{"auto": false}"#).unwrap();
        assert_eq!(read_config(&d).unwrap(), Config { auto: false, channel: "stable".into() });
        std::fs::write(d.join("config.json"), b"{").unwrap();
        assert!(read_config(&d).is_err());
        assert_eq!(holds_active(&d, 100), Some(false));
        std::fs::write(d.join("holds.json"), br#"{"holds":[{"until":50,"reason":"x"}]}"#).unwrap();
        assert_eq!(holds_active(&d, 100), Some(false), "만료된 보류");
        std::fs::write(d.join("holds.json"), br#"{"holds":[{"until":150,"reason":"x"}]}"#).unwrap();
        assert_eq!(holds_active(&d, 100), Some(true));
        std::fs::write(d.join("holds.json"), b"x").unwrap();
        assert_eq!(holds_active(&d, 100), None);
        // 신뢰 시각 단조
        assert_eq!(bump_trusted(&d, Some(1000)).unwrap().last_trusted_time, Some(1000));
        assert_eq!(bump_trusted(&d, Some(900)).unwrap().last_trusted_time, Some(1000), "내려가지 않음");
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★1R B3 뮤테이션: 수용 폐기문 대체본 = 30일 이내 · 원문 sha256 일치일 때만 · 같은 rev 다른 원문 기록 거부 · rev 후퇴 거부.
    #[test]
    fn b3_revocations_copy_freshness_and_integrity() {
        let d = tmp("b3");
        let t = record_revocations(&d, b"rev-v3", b"sig", 3, 1_000).unwrap();
        assert_eq!((t.revocations_rev, t.last_trusted_time), (Some(3), Some(1_000)));
        let now = clock::now_stamp();
        assert_eq!(load_accepted_revocations(&d, &now, false).unwrap().0, b"rev-v3");
        assert!(record_revocations(&d, b"rev-v3-other", b"sig", 3, 1_000).is_err(), "같은 rev 다른 원문");
        assert!(record_revocations(&d, b"rev-v2", b"sig", 2, 1_000).is_err(), "rev 후퇴");
        // 수용 시각을 31일 전(다른 부팅)으로 — 낡음
        let mut tr = read_trusted(&d).unwrap();
        tr.revocations_accepted_at = Some(clock::Stamp { boot_id: now.boot_id + 1, mono_ms: 0, wall: now.wall - 31 * 86_400 });
        std::fs::write(d.join("trusted.json"), serde_json::to_vec(&tr).unwrap()).unwrap();
        assert!(load_accepted_revocations(&d, &now, false).unwrap_err().contains("30일"));
        // 원문 변조 = 거부
        tr.revocations_accepted_at = Some(now);
        std::fs::write(d.join("trusted.json"), serde_json::to_vec(&tr).unwrap()).unwrap();
        std::fs::write(d.join(REV_COPY), b"tampered").unwrap();
        assert!(load_accepted_revocations(&d, &now, false).is_err());
        let _ = std::fs::remove_dir_all(&d);
    }

    /// U1 판의 --check 사실: 복구기 미등록(N14) · N7 판정 불가 → 판정은 늘 보류(교체 경로 없는 판의 올바른 답).
    #[test]
    fn u1_facts_never_pass_gates() {
        let d = tmp("facts");
        let pack = d.join("pack");
        std::fs::create_dir_all(&pack).unwrap();
        let hooks = Hooks { seats: &|| None, pending_approvals: &|| Some(0) };
        let _ = &hooks;
        let f = gather_facts(&d, &pack, None, &[], clock::wall_now(), &hooks);
        assert_eq!(f.recover_agent_ok, Some(false));
        assert_eq!(f.rollback_assets_ok, None);
        assert_eq!(f.other_txn, Some(false));
        assert_eq!(f.hold_log_undelivered, Some(0));
        assert!(!gates::evaluate(&f).pass);
        let _ = std::fs::remove_dir_all(&d);
    }
}
