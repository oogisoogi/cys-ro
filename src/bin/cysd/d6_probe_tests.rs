//! D6 정밀 디버깅(TICKET=dbg-D6 · 2026-09-23) — 계기·경보 결함 **검출 시험**.
//!
//! ★제품 코드는 건드리지 않는다. 공개 API(note_rate·alert_rates·alerts::evaluate·local_json)만 쓴다.
//! (TICKET=v116-usage) D6-1·D6-2 수리가 들어간 판이라 검출 시험 4건의 `#[ignore]` 를 뗐다 — 이제 회귀
//! 가드다(수리 전 base 526325bf 에서 4건 적색 실측). `d6_1_true_alarm_*` 는 수리의 반대쪽 경계다:
//! 죽은 창을 경보에서 빼다가 **살아 있는 창의 참 경보까지 끄지 않는가**를 잡는다.
//!   실행: `cysd-<hash> d6_probe_tests`
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

// ── D6-1 반대쪽 경계: 참 경보는 살아 있어야 한다 (TICKET=v116-usage · 적대 조준 = 「참 경보 침묵」) ──
// alert_rates 는 자기 시계(now_epoch)로 판정하므로 경계 시험은 수 초 여유를 둔다(시계 경합 회피).

/// 같은 계정에서 5h 창만 리셋이 지났고 7d 창은 살아 있으면 — 7d 경보는 그대로 나야 한다
/// (계정 단위 updated_at 을 공유하므로 「계정째로 끄는」 수리를 잡는다).
#[test]
fn d6_1_true_alarm_fresh_sibling_window_still_alerts() {
    let d = daemon("d61t1");
    let now = crate::state::now_epoch();
    let sf = profile_session("d61t1", "uuid-sib", "sib@x");
    crate::accounts::note_rate(
        &d,
        "claude",
        &sf,
        &[w("5h", 92.0, now - 60.0), w("7d", 97.0, now + 86400.0)],
        "statusline",
        now,
    );
    assert_eq!(account_alert_keys(&d, now), vec!["account_rate:sib@x:7d".to_string()]);
}

/// 죽은 계정이 있어도 다른 계정의 살아 있는 경보는 영향이 없다.
#[test]
fn d6_1_true_alarm_other_account_unaffected() {
    let d = daemon("d61t2");
    let now = crate::state::now_epoch();
    let dead = profile_session("d61t2a", "uuid-dead", "dead@x");
    let live = profile_session("d61t2b", "uuid-live", "live@x");
    crate::accounts::note_rate(&d, "claude", &dead, &[w("7d", 96.0, now + 86400.0)], "statusline", now - 30.0 * 3600.0);
    crate::accounts::note_rate(&d, "claude", &live, &[w("5h", 88.0, now + 3600.0)], "statusline", now);
    assert_eq!(account_alert_keys(&d, now), vec!["account_rate:live@x:5h".to_string()]);
}

/// 무관측으로 빠졌던 창도 새 관측이 오면 **바로** 경보가 돌아온다 — 수리는 「못 쟀다」를 뺄 뿐
/// 「쟀는데 높다」를 끄지 않는다(계정을 실제로 쓰는 순간 statusline·oauth 가 창을 되살린다).
#[test]
fn d6_1_true_alarm_rearms_on_fresh_observation() {
    let d = daemon("d61t3");
    let now = crate::state::now_epoch();
    let sf = profile_session("d61t3", "uuid-re", "re@x");
    crate::accounts::note_rate(&d, "claude", &sf, &[w("7d", 96.0, now + 86400.0)], "statusline", now - 30.0 * 3600.0);
    assert!(account_alert_keys(&d, now).is_empty(), "전제: 30h 무관측 창은 빠진다");
    crate::accounts::note_rate(&d, "claude", &sf, &[w("7d", 96.0, now + 86400.0)], "oauth", now);
    assert_eq!(account_alert_keys(&d, now), vec!["account_rate:re@x:7d".to_string()]);
}

/// 경계 안쪽(관측 23시간 전 · 리셋 2분 뒤)은 아직 살아 있는 창이다 — 경보가 나야 한다.
#[test]
fn d6_1_true_alarm_inside_boundaries_still_alerts() {
    let d = daemon("d61t4");
    let now = crate::state::now_epoch();
    let sf = profile_session("d61t4", "uuid-edge", "edge@x");
    crate::accounts::note_rate(&d, "claude", &sf, &[w("5h", 99.0, now + 120.0)], "statusline", now - 23.0 * 3600.0);
    assert_eq!(account_alert_keys(&d, now), vec!["account_rate:edge@x:5h".to_string()]);
}

/// 리셋 시각을 모르는 창(resets_at 없음)은 리셋이 지났다고 **가정하지 않는다** — 관측이 신선하면 경보.
#[test]
fn d6_1_true_alarm_unknown_resets_at_still_alerts() {
    let d = daemon("d61t5");
    let now = crate::state::now_epoch();
    let sf = profile_session("d61t5", "uuid-nor", "nor@x");
    let win = crate::usage::RateWindow { label: "5h".into(), used_pct: 91.0, resets_at: None };
    crate::accounts::note_rate(&d, "claude", &sf, &[win], "statusline", now);
    assert_eq!(account_alert_keys(&d, now), vec!["account_rate:nor@x:5h".to_string()]);
}

/// D6-2 반대쪽 경계: 파생 에이전트 두 번째 이름(claude-sonnet)도 귀속되고, claude 가 아닌 이름은
/// 접두만 비슷해도(claudex) claude 신원 해석으로 들어가지 않는다.
#[test]
fn d6_2_prefix_is_dash_delimited() {
    let d = daemon("d62p");
    let now = crate::state::now_epoch();
    let s1 = profile_session("d62p1", "uuid-s", "s@x");
    let s2 = profile_session("d62p2", "uuid-n", "n@x");
    crate::accounts::note_rate(&d, "claude-sonnet", &s1, &[w("5h", 10.0, now + 3600.0)], "statusline", now);
    crate::accounts::note_rate(&d, "claudex", &s2, &[w("5h", 20.0, now + 3600.0)], "statusline", now);
    let j = crate::accounts::local_json(&d, now);
    let rows = j.as_array().unwrap();
    assert!(rows.iter().any(|r| r["label"] == "s@x" && r["rate"][0]["used_pct"] == 10.0), "claude-sonnet 귀속");
    assert!(!rows.iter().any(|r| r["label"] == "n@x"), "claudex 는 claude 파생이 아니다 — 유령 계정 0");
}

/// opus 적대 1R(low · D6-1 이 새로 연 부작용): idle 좌석의 statusline 이 리셋 지난 캐시 창 묶음을 다시 보고해도
/// 살아 있는 OAuth 묶음을 덮지 않는다 — 덮으면 경보 키가 사라졌다 다음 프로브에 돌아오며 매번 재발화한다.
#[test]
fn d6_1_dead_statusline_vector_does_not_evict_live_oauth() {
    let d = daemon("d61e");
    let now = crate::state::now_epoch();
    let sf = profile_session("d61e", "uuid-evict", "evict@x");
    crate::accounts::note_rate(&d, "claude", &sf, &[w("5h", 88.0, now + 3600.0)], "oauth", now - 10.0);
    assert_eq!(account_alert_keys(&d, now), vec!["account_rate:evict@x:5h".to_string()], "전제: 살아 있는 경보");
    // 더 새 시각의 statusline 보고 — 그러나 창은 리셋이 이미 지난 캐시
    crate::accounts::note_rate(&d, "claude", &sf, &[w("5h", 93.0, now - 60.0)], "statusline", now);
    assert_eq!(
        account_alert_keys(&d, now),
        vec!["account_rate:evict@x:5h".to_string()],
        "죽은 캐시 묶음이 살아 있는 묶음을 덮어 경보 키가 사라졌다(깜빡임 재발화)"
    );
    let j = crate::accounts::local_json(&d, now);
    let row = j.as_array().unwrap().iter().find(|r| r["label"] == "evict@x").unwrap().clone();
    assert_eq!(row["rate"][0]["used_pct"], 88.0, "계기도 살아 있는 값을 보여야 한다");
    assert_eq!(row["source"], "oauth", "전부 기각된 보고가 출처·관측 시각을 바꿨다(죽은 값이 신선한 척)");
    // 대조: 살아 있는 창이 없던 계정은 종전대로 최신 승자(죽은 묶음도 받아 계기가 stale 로 표시)
    let sf2 = profile_session("d61e2", "uuid-evict2", "evict2@x");
    crate::accounts::note_rate(&d, "claude", &sf2, &[w("5h", 70.0, now - 7200.0)], "oauth", now - 10.0);
    crate::accounts::note_rate(&d, "claude", &sf2, &[w("5h", 93.0, now - 60.0)], "statusline", now);
    let j = crate::accounts::local_json(&d, now);
    let row2 = j.as_array().unwrap().iter().find(|r| r["label"] == "evict2@x").unwrap().clone();
    assert_eq!(row2["rate"][0]["used_pct"], 93.0, "살아 있는 창이 없으면 최신 승자 유지");
}

