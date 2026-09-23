//! D6 정밀 디버깅(TICKET=dbg-D6 · 2026-09-23) — 계기·경보 결함 **검출 시험**.
//!
//! ★제품 코드는 건드리지 않는다. 공개 API(note_rate·alert_rates·alerts::evaluate·local_json)만 쓴다.
//! 결함 검출 시험은 `#[ignore]` 로 둔다 — 현 코드(fd356c06)에서 **적색**이 정상이고, 보고서의
//! 제안 patch 를 적용하면 초록이 된다. 대조군(control)은 ignore 없이 두 코드 모두에서 초록이다.
//!   실행: `cysd-<hash> d6_probe_tests --include-ignored`
//!   보고서: ~/axdev/master/reports/cysr-115-debug-2026-09-23/D6-telemetry.md
use crate::state::Daemon;
use crate::usage::RateWindow;
use std::path::PathBuf;
use std::sync::Arc;

fn tmp(tag: &str) -> PathBuf {
    static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let d = std::env::temp_dir().join(format!(
        "cys-d6-{tag}-{}-{}",
        std::process::id(),
        SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    ));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(&d).unwrap();
    d
}

fn daemon(tag: &str) -> Arc<Daemon> {
    Daemon::new(tmp(&format!("{tag}-sock")).join("cysd.sock"))
}

/// 프로필 dir(`<root>/prof`)에 신원을 적고, 그 프로필의 세션 파일 경로를 돌려준다.
fn profile_session(tag: &str, uuid: &str, email: &str) -> String {
    let root = tmp(tag);
    let prof = root.join("prof");
    std::fs::create_dir_all(prof.join("projects/p")).unwrap();
    std::fs::write(
        prof.join(".claude.json"),
        format!(r#"{{"oauthAccount":{{"accountUuid":"{uuid}","emailAddress":"{email}"}}}}"#),
    )
    .unwrap();
    prof.join("projects/p/s.jsonl").to_string_lossy().into_owned()
}

fn w(label: &str, pct: f64, resets_at: f64) -> RateWindow {
    RateWindow { label: label.into(), used_pct: pct, resets_at: Some(resets_at) }
}

fn account_alert_keys(d: &Arc<Daemon>, now: f64) -> Vec<String> {
    let snap = crate::alerts::Snapshot {
        account_rates: crate::accounts::alert_rates(d),
        ..crate::alerts::Snapshot::default()
    };
    let _ = now;
    crate::alerts::evaluate(&snap, &crate::alerts::AlertConfig::default())
        .into_iter()
        .filter(|a| a.kind == "account_rate")
        .map(|a| a.key)
        .collect()
}

// ── D6-1: 계정 경보(alert_rates → control.alerts·alert.account_rate)가 죽은 창을 거른다 ──

/// 대조군: 신선하고 리셋 전인 창 92% → 경보가 난다(현 코드·수리 코드 모두 초록).
#[test]
fn d6_1_control_fresh_window_alerts() {
    let d = daemon("d61c");
    let now = crate::state::now_epoch();
    let sf = profile_session("d61c", "uuid-fresh", "fresh@x");
    crate::accounts::note_rate(&d, "claude", &sf, &[w("5h", 92.0, now + 3600.0)], "statusline", now);
    assert_eq!(account_alert_keys(&d, now), vec!["account_rate:fresh@x:5h".to_string()]);
}

/// 검출: 리셋이 이미 지난 창(값이 죽은 창)은 경보를 내면 안 된다 — usage.accounts JSON 은 같은
/// 창을 `stale:true · resets_at_passed` 로 표시하는데, 경보 경로는 그 판정을 안 본다.
#[test]
#[ignore = "D6-1 결함 검출 — 현 코드 적색 · 제안 patch 적용 시 초록"]
fn d6_1_reset_passed_window_must_not_alert() {
    let d = daemon("d61a");
    let now = crate::state::now_epoch();
    let sf = profile_session("d61a", "uuid-old", "old@x");
    // 2시간 전 관측(24h 미만 · 관측 자체는 신선) · 리셋은 1시간 전에 지났다
    crate::accounts::note_rate(&d, "claude", &sf, &[w("5h", 92.0, now - 3600.0)], "statusline", now - 7200.0);
    // 계기 JSON 은 이미 이 창을 죽었다고 말한다(전제 확인 — 이 단언이 깨지면 시험 전제 붕괴)
    let j = crate::accounts::local_json(&d, now);
    let row = j.as_array().unwrap().iter().find(|r| r["label"] == "old@x").unwrap();
    assert_eq!(row["rate"][0]["stale_reason"], "resets_at_passed", "전제: 계기는 죽은 창으로 판정");
    assert!(
        account_alert_keys(&d, now).is_empty(),
        "죽은 창(resets_at_passed)이 계정 경보를 냈다 — alert_rates 가 stale 판정을 무시"
    );
}

/// 검출: 24시간 넘게 관측이 없는 창(no_observation_24h)도 경보에서 빠져야 한다
/// (라이브 실증 09-23 16:57: 계정2 7d 78% = 38h 무관측 · 서버 진실 17%).
#[test]
#[ignore = "D6-1 결함 검출 — 현 코드 적색 · 제안 patch 적용 시 초록"]
fn d6_1_unobserved_24h_window_must_not_alert() {
    let d = daemon("d61b");
    let now = crate::state::now_epoch();
    let sf = profile_session("d61b", "uuid-quiet", "quiet@x");
    crate::accounts::note_rate(&d, "claude", &sf, &[w("7d", 96.0, now + 86400.0)], "statusline", now - 30.0 * 3600.0);
    let j = crate::accounts::local_json(&d, now);
    let row = j.as_array().unwrap().iter().find(|r| r["label"] == "quiet@x").unwrap();
    assert_eq!(row["rate"][0]["stale_reason"], "no_observation_24h", "전제: 계기는 무관측 창으로 판정");
    assert!(
        account_alert_keys(&d, now).is_empty(),
        "38h 무관측 창이 crit 계정 경보를 냈다 — 서버 진실과 무관한 숫자로 경보"
    );
}

// ── D6-2: claude 파생 에이전트(agents.json 의 claude-fable·claude-sonnet 등) 계정 귀속 ──

/// 대조군: agent="claude" 관측은 계정에 귀속된다.
#[test]
fn d6_2_control_claude_agent_attributed() {
    let d = daemon("d62c");
    let now = crate::state::now_epoch();
    let sf = profile_session("d62c", "uuid-c", "c@x");
    crate::accounts::note_rate(&d, "claude", &sf, &[w("5h", 10.0, now + 3600.0)], "statusline", now);
    let j = crate::accounts::local_json(&d, now);
    assert!(j.as_array().unwrap().iter().any(|r| r["label"] == "c@x" && r["rate"][0]["used_pct"] == 10.0));
}

/// 검출: 같은 claude 바이너리를 `--model` 만 달리 띄운 파생 에이전트(claude-fable)의 statusline
/// rate 도 계정 뷰에 귀속돼야 한다 — 현 코드는 resolve() 가 문자열 "claude" 만 받아 조용히 버린다
/// (살아 있는 증거: ~/.claude/channels/cso-acct2-budget.py 가 계정 뷰를 포기하고 노드 rate 를 읽는다).
#[test]
#[ignore = "D6-2 결함 검출 — 현 코드 적색 · 제안 patch 적용 시 초록"]
fn d6_2_claude_variant_agent_must_be_attributed() {
    let d = daemon("d62a");
    let now = crate::state::now_epoch();
    let sf = profile_session("d62a", "uuid-v", "v@x");
    crate::accounts::note_rate(&d, "claude-fable", &sf, &[w("5h", 10.0, now + 3600.0)], "statusline", now);
    let j = crate::accounts::local_json(&d, now);
    assert!(
        j.as_array().unwrap().iter().any(|r| r["label"] == "v@x" && r["rate"][0]["used_pct"] == 10.0),
        "claude-fable 관측이 계정 뷰에 0건 — 파생 에이전트 계정 눈멂"
    );
}

/// 검출(소스 배선): usage.report 핸들러의 계정 귀속 조건이 파생 에이전트를 통과시키는가.
/// note_rate 만 고치고 핸들러 조건(`agent == "claude"`)을 남기면 실경로는 여전히 눈멀다 —
/// 두 자리 중 하나만 고친 수리를 잡는 배선 단언(주석 제거 후 대조).
#[test]
#[ignore = "D6-2 결함 검출(배선) — 현 코드 적색 · 제안 patch 적용 시 초록"]
fn d6_2_usage_report_gate_accepts_claude_variants() {
    let src = include_str!("handlers.rs");
    let start = src.find("\"usage.report\" => {").expect("usage.report 분기");
    let body = &src[start..start + src[start..].find("\"usage.event\" =>").expect("다음 분기")];
    let code: String = body
        .lines()
        .map(|l| l.split("//").next().unwrap_or(""))
        .collect::<Vec<_>>()
        .join("\n");
    assert!(
        !code.contains("if agent == \"claude\" && !rate.is_empty()"),
        "usage.report 계정 귀속 조건이 여전히 문자열 \"claude\" 완전일치 — claude-fable/sonnet 노드 rate 유실"
    );
}
