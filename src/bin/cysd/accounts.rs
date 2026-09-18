//! CC v2 WS-A: 계정 단위 rate limit 집계 — 노드(surface) 관측을 **계정** 차원으로 귀속한다.
//!
//! 핵심 사실(실측 2026-07-16):
//! - 계정 식별자 = 프로필 dir이 아니라 `<dir>/.claude.json`의 `oauthAccount.accountUuid`.
//!   프로필 dir은 계정에 N:1이다(~/.claude·~/.claude-work·~/.cys/claude* 가 같은 계정인 식).
//! - claude rate의 유일한 생산자는 statusline(usage.report)이다 — usage.rs claude transcript
//!   분기는 rate를 **이월**하며 updated_at을 현재로 갱신하므로, 여기(note_rate)에는
//!   **신선 생산된 rate만** 넘긴다(이월분 수용 시 stale이 최신으로 둔갑).
//! - 병합 = 창 벡터 통째 최신 승자(같은 계정 풀은 최신 관측이 진실).
//!
//! 잠금 순서 불변식: accounts → (해제) → analytics. 역순 금지(교착).

use crate::state::{Daemon, HideConsole};
use crate::usage::RateWindow;
use serde_json::{json, Value};
use std::collections::{BTreeSet, HashMap};
use std::path::{Path, PathBuf};
use std::sync::Arc;

/// 스냅샷 영속 스로틀 — 같은 (계정,창)에서 pct 변화가 이 미만이면 INSERT 생략.
const SNAPSHOT_MIN_DELTA_PCT: f64 = 1.0;
/// 스냅샷 보존 창(초) — 초과분은 prune. 30일.
const SNAPSHOT_RETAIN_SECS: f64 = 30.0 * 86400.0;
/// prune 주기(초) — note 경로에서 저빈도 수행. 6시간.
const PRUNE_INTERVAL_SECS: f64 = 6.0 * 3600.0;
/// 부트 복원 창(초) — 이 안의 마지막 스냅샷으로 계정 뷰를 예열(stale 표시). 7일.
const BOOT_RESTORE_SECS: f64 = 7.0 * 86400.0;
/// rate 창 무관측 만료(초) — 계정 관측이 이보다 오래되면 창을 stale로 표기한다. 24시간.
/// ★읽기 시점 판정이다(상태 파괴 없음): used_pct는 그대로 내보내고 `stale`·`stale_reason`만 덧붙인다.
const RATE_STALE_NO_OBS_SECS: f64 = 24.0 * 3600.0;

#[derive(Clone, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct AccountKey {
    pub provider: String,   // "claude" | "codex" | (accounts.json 선언 provider)
    pub account_id: String, // claude: accountUuid · 그 외 단일 홈: "default"
}

/// 모델 스코프 주간 게이지 — OAuth usage API `limits[].kind=="weekly_scoped"` 유래.
///
/// ★왜 `rate`와 **다른 슬롯**인가(설계의 핵심): `rate`의 병합 규율은 「창 벡터 통째 최신 승자」다
/// (모듈 헤더). 그 규율은 **모든 생산자가 같은 창 집합을 낸다**는 전제 위에서만 옳다. statusline은
/// {5h,7d}만 내고 OAuth 프로브는 {5h,7d,모델 스코프}를 낸다 — 이 둘을 한 벡터에서 겨루게 하면
/// statusline이 이길 때마다 모델 게이지가 **사라졌다 나타났다** 한다(2~5분 주기 × 페인 턴마다).
/// ⇒ 겹치지 않는 축은 겨루게 하지 않는다. 5h·7d는 종전대로 `rate`에서 신선도 경쟁하고(OAuth도
/// 같은 자격으로 합류), 모델 스코프 게이지만 이 슬롯에서 **자기 시각을 들고** 산다.
#[derive(Clone, Debug)]
pub struct ScopedGauge {
    /// API가 준 표시 이름(`scope.model.display_name` — 예: "Fable"). ★우리가 짓지 않는다:
    /// 스코프가 걸린 모델이 바뀌면 라벨도 따라 바뀌어야 하는데, 상수로 박으면 남의 게이지에
    /// 옛 이름이 붙는다.
    pub model: String,
    pub used_pct: f64,
    pub resets_at: Option<f64>,
    /// 이 게이지 자체의 관측 시각 — `AccountView.updated_at`(rate 슬롯의 시각)과 별개다.
    pub updated_at: f64,
    pub source: String, // "oauth"
}

#[derive(Clone, Debug)]
pub struct AccountView {
    pub key: AccountKey,
    pub label: String,        // claude: 이메일 · codex: "OpenAI Codex"
    pub plan: Option<String>, // oauthAccount rate limit tier — 값이 있을 때만 UI 표시
    pub profiles: BTreeSet<String>, // 이 계정으로 관측된 프로필 dir들(홈 상대 표기)
    pub rate: Vec<RateWindow>,
    pub updated_at: f64, // 0.0 = 관측 전(발견만)
    pub source: String,  // "statusline" | "rollout" | "adapter:<p>" | "oauth" | "snapshot"(부트 복원)
    pub adapter: bool,   // false = 관측 어댑터 없음(accounts.json adapter:"none" 선언 계정)
    /// 모델 스코프 주간 게이지(위 주석) — rate 슬롯과 독립. 빈 벡터 = 관측 없음(그리지 않는다).
    pub scoped: Vec<ScopedGauge>,
}

struct IdentEntry {
    mtime: f64,
    ident: Option<(String, String, Option<String>)>, // (accountUuid, email, plan)
}

#[derive(Default)]
pub struct AccountsState {
    views: HashMap<AccountKey, AccountView>,
    ident_cache: HashMap<PathBuf, IdentEntry>,
    last_persisted: HashMap<(AccountKey, String), f64>, // (key, 창 라벨) → 마지막 기록 pct
    last_prune: f64,
}

/// 세션 파일 경로 → 프로필 dir (`…/<profile>/projects/<munged>/<sess>.jsonl`의 profile 부분).
/// `/projects/` 마커 앞이 프로필 dir — 홈 `~/.claude*`와 `~/.cys/claude*` 모두 커버.
pub fn profile_dir_from_session(path: &str) -> Option<PathBuf> {
    let norm = path.replace('\\', "/");
    let idx = norm.find("/projects/")?;
    if idx == 0 {
        return None;
    }
    Some(PathBuf::from(&norm[..idx]))
}

/// 프로필 dir의 홈 상대 표기 (라벨·중복 제거용 — 계정 식별에는 쓰지 않는다)
fn profile_short(dir: &Path) -> String {
    if let Some(home) = dirs::home_dir() {
        if let Ok(rel) = dir.strip_prefix(&home) {
            return rel.to_string_lossy().into_owned();
        }
    }
    dir.to_string_lossy().into_owned()
}

/// `<dir>/.claude.json` → oauthAccount 신원. 잡동사니 dir(.claude-worktrees·백업 등)은
/// 파일 부재/uuid 부재로 None → 관측 미귀속(유령 계정 0). 자격증명(.credentials.json)은 읽지 않는다.
fn claude_identity(
    state: &mut AccountsState,
    dir: &Path,
) -> Option<(String, String, Option<String>)> {
    let f = dir.join(".claude.json");
    let mtime = std::fs::metadata(&f)
        .and_then(|m| m.modified())
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_secs_f64())?;
    if let Some(e) = state.ident_cache.get(dir) {
        if e.mtime == mtime {
            return e.ident.clone();
        }
    }
    let ident = std::fs::read_to_string(&f)
        .ok()
        .and_then(|s| serde_json::from_str::<Value>(&s).ok())
        .and_then(|v| {
            let oa = v.get("oauthAccount")?;
            let uuid = oa.get("accountUuid")?.as_str()?.to_string();
            let email = oa
                .get("emailAddress")
                .and_then(|x| x.as_str())
                .unwrap_or(&uuid)
                .to_string();
            let plan = oa
                .get("userRateLimitTier")
                .or_else(|| oa.get("organizationRateLimitTier"))
                .and_then(|x| x.as_str())
                .map(|s| s.to_string());
            Some((uuid, email, plan))
        });
    state
        .ident_cache
        .insert(dir.to_path_buf(), IdentEntry { mtime, ident: ident.clone() });
    ident
}

/// agent + 세션 파일 → (키, 라벨, plan, 프로필 표기). claude는 신원 해석 실패 시 None(스킵).
fn resolve(
    state: &mut AccountsState,
    agent: &str,
    session_file: &str,
) -> Option<(AccountKey, String, Option<String>, Option<String>)> {
    match agent {
        "claude" => {
            let dir = profile_dir_from_session(session_file)?;
            let (uuid, email, plan) = claude_identity(state, &dir)?;
            Some((
                AccountKey { provider: "claude".into(), account_id: uuid },
                email,
                plan,
                Some(profile_short(&dir)),
            ))
        }
        "codex" => Some((
            AccountKey { provider: "codex".into(), account_id: "default".into() },
            "OpenAI Codex".into(),
            None,
            Some(".codex".into()),
        )),
        // usage-noagy(2026-09-19 박사님 결정): agy(gemini)는 계정 사용량 표에서 뺀다 — 의미 없음.
        // note_rate가 이 분기로 오면 None → 호출부(usage.rs update_agy_usage)의 note_rate 호출은
        // 그대로 남아 있어도 무조건 no-op이다(HANDOFF-usage-noagy.md 결정 기록).
        _ => None,
    }
}

/// 신선 생산된 rate 관측을 계정에 귀속·병합하고 스냅샷을 영속한다(스로틀·prune 포함).
/// **호출 계약: rate는 이번 관측이 실제 생산한 값만** — 이월(carryover) 금지(모듈 헤더 참조).
pub fn note_rate(
    daemon: &Arc<Daemon>,
    agent: &str,
    session_file: &str,
    rate: &[RateWindow],
    source: &str,
    now: f64,
) {
    if rate.is_empty() {
        return;
    }
    // 1) accounts 락 안에서 병합 + 영속 대상 수집 (analytics 락은 여기서 잡지 않는다 — 잠금 순서)
    let mut to_persist: Vec<(AccountKey, String, String, f64, Option<f64>)> = Vec::new();
    let mut do_prune = false;
    {
        let mut st = daemon.accounts.lock().unwrap();
        let Some((key, label, plan, profile)) = resolve(&mut st, agent, session_file) else {
            return; // 미귀속(신원 불명) — 유령 계정을 만들지 않는다
        };
        let view = st.views.entry(key.clone()).or_insert_with(|| AccountView {
            key: key.clone(),
            label: label.clone(),
            plan: plan.clone(),
            profiles: BTreeSet::new(),
            rate: Vec::new(),
            updated_at: 0.0,
            source: String::new(),
            adapter: true,
            scoped: Vec::new(),
        });
        view.label = label;
        if plan.is_some() {
            view.plan = plan;
        }
        if let Some(p) = profile {
            view.profiles.insert(p);
        }
        // 최신 승자 — note는 신선 생산분만 받으므로 timestamp 비교로 충분
        if now >= view.updated_at {
            view.rate = rate.to_vec();
            view.updated_at = now;
            view.source = source.into();
        }
        for w in rate {
            let pk = (key.clone(), w.label.clone());
            let prev = st.last_persisted.get(&pk).copied();
            if prev.map_or(true, |p| (w.used_pct - p).abs() >= SNAPSHOT_MIN_DELTA_PCT) {
                st.last_persisted.insert(pk, w.used_pct);
                to_persist.push((
                    key.clone(),
                    st.views[&key].label.clone(),
                    w.label.clone(),
                    w.used_pct,
                    w.resets_at,
                ));
            }
        }
        if now - st.last_prune > PRUNE_INTERVAL_SECS {
            st.last_prune = now;
            do_prune = true;
        }
    }
    // 2) analytics 영속 (accounts 락 해제 후)
    if to_persist.is_empty() && !do_prune {
        return;
    }
    let guard = daemon.analytics.lock().unwrap();
    if let Some(conn) = guard.as_ref() {
        for (key, label, win, pct, resets) in &to_persist {
            crate::analytics::record_rate_snapshot(
                conn, now, &key.provider, &key.account_id, label, win, *pct, *resets,
            );
        }
        if do_prune {
            crate::analytics::prune_rate_snapshots(conn, now - SNAPSHOT_RETAIN_SECS);
        }
    }
}

/// 부트 시드 — ① 알려진 프로필 dir 스캔으로 계정 **발견**(관측 전에도 3계정이 다 보이게),
/// ② analytics 마지막 스냅샷(7d)으로 rate 예열(source:"snapshot"·stale 표시),
/// ③ ~/.cys/accounts.json 선언 계정 등록(미래 provider — adapter:"none"은 '관측 없음' 상주).
pub fn seed_known(daemon: &Arc<Daemon>) {
    if let Some(home) = dirs::home_dir() {
        // ★(U-17) 프로필 dir 열거 규칙은 **lib 정본 하나**다(`cys::profile_gate`). 종전엔 이
        //   함수 안에만 있었고, 인증 판정기가 같은 규칙을 재구현하면 두 벌이 갈린다(한쪽만
        //   새 부서 접두를 배우는 식) — 같은 목록을 두 소비처가 보게 한다.
        //   ★판정은 바뀌지 않는다: 정본 함수는 종전 두 루프와 **같은 이름 규칙·같은 순서**이며
        //   `is_dir()` 검사도 더하지 않는다(동작 동일성 유지 — 완화도 강화도 아니다).
        let dirs_to_check: Vec<PathBuf> = cys::profile_gate::enumerate_profile_dirs(&home);
        {
            let mut st = daemon.accounts.lock().unwrap();
            for dir in dirs_to_check {
                if let Some((uuid, email, plan)) = claude_identity(&mut st, &dir) {
                    let key = AccountKey { provider: "claude".into(), account_id: uuid };
                    let short = profile_short(&dir);
                    let v = st.views.entry(key.clone()).or_insert_with(|| AccountView {
                        key,
                        label: email.clone(),
                        plan: plan.clone(),
                        profiles: BTreeSet::new(),
                        rate: Vec::new(),
                        updated_at: 0.0,
                        source: String::new(),
                        adapter: true,
                        scoped: Vec::new(),
                    });
                    v.profiles.insert(short);
                }
            }
            if home.join(".codex").is_dir() {
                st.views
                    .entry(AccountKey { provider: "codex".into(), account_id: "default".into() })
                    .or_insert_with(|| AccountView {
                        key: AccountKey { provider: "codex".into(), account_id: "default".into() },
                        label: "OpenAI Codex".into(),
                        plan: None,
                        profiles: BTreeSet::from([".codex".to_string()]),
                        rate: Vec::new(),
                        updated_at: 0.0,
                        source: String::new(),
                        adapter: true,
                        scoped: Vec::new(),
                    });
            }
            // usage-noagy(2026-09-19): antigravity(agy) 자동 시딩 제거 — 박사님 결정("의미가 없다").
        }
        // 선언 계정(~/.cys/accounts.json — pack 밖: pack 스윕/치유 사정권 회피)
        let decl = home.join(".cys/accounts.json");
        if let Ok(s) = std::fs::read_to_string(&decl) {
            if let Ok(v) = serde_json::from_str::<Value>(&s) {
                let mut st = daemon.accounts.lock().unwrap();
                for a in v.get("accounts").and_then(|x| x.as_array()).into_iter().flatten() {
                    let Some(provider) = a.get("provider").and_then(|x| x.as_str()) else {
                        continue;
                    };
                    let label = a
                        .get("label")
                        .and_then(|x| x.as_str())
                        .unwrap_or(provider)
                        .to_string();
                    let adapter =
                        a.get("adapter").and_then(|x| x.as_str()).unwrap_or("none") != "none";
                    let key =
                        AccountKey { provider: provider.into(), account_id: "default".into() };
                    st.views.entry(key.clone()).or_insert_with(|| AccountView {
                        key,
                        label,
                        plan: None,
                        profiles: BTreeSet::new(),
                        rate: Vec::new(),
                        updated_at: 0.0,
                        source: String::new(),
                        adapter,
                        scoped: Vec::new(),
                    });
                }
            }
        }
    }
    // 마지막 스냅샷으로 예열 — updated_at은 스냅샷 시각 그대로(신선한 척 금지)
    let rows = {
        let guard = daemon.analytics.lock().unwrap();
        guard.as_ref().map(|conn| {
            crate::analytics::last_rate_snapshots(
                conn,
                crate::state::now_epoch() - BOOT_RESTORE_SECS,
            )
        })
    };
    if let Some(rows) = rows {
        let mut st = daemon.accounts.lock().unwrap();
        for (ts, provider, account, label, win, pct, resets) in rows {
            // usage-noagy(2026-09-19): 옛 analytics.db에 antigravity 스냅샷 행이 남아 있어도
            // 부트 복원에서 버린다 — 코드에서 시딩을 지워도 과거 기록으로 되살아나면 의미가 없다.
            if provider == "antigravity" {
                continue;
            }
            let key = AccountKey { provider, account_id: account };
            let v = st.views.entry(key.clone()).or_insert_with(|| AccountView {
                key,
                label: label.clone(),
                plan: None,
                profiles: BTreeSet::new(),
                rate: Vec::new(),
                updated_at: 0.0,
                source: String::new(),
                adapter: true,
                scoped: Vec::new(),
            });
            // 라이브 관측 전(발견만·또는 스냅샷 예열 중)에만 덮는다 — 신선 관측 우선.
            let seeded = v.source.is_empty() || v.source == "snapshot";
            if seeded {
                if let Some(w) = v.rate.iter_mut().find(|w| w.label == win) {
                    w.used_pct = pct;
                    w.resets_at = resets;
                } else {
                    v.rate.push(RateWindow { label: win, used_pct: pct, resets_at: resets });
                }
                v.source = "snapshot".into();
                if ts > v.updated_at {
                    v.updated_at = ts;
                }
            }
        }
    }
}

/// accounts.json의 adapter:"cmd" 계정 — 주기 실행해 rate JSON을 흡수하는 범용 풀 어댑터.
/// 출력 계약: `[{"label":"5h","used_pct":12.3,"resets_at":1234.0}, …]`. grok/GLM CLI 합류 지점.
pub fn spawn_custom_adapters(daemon: Arc<Daemon>) {
    let Some(home) = dirs::home_dir() else { return };
    let decl = home.join(".cys/accounts.json");
    let Ok(s) = std::fs::read_to_string(&decl) else { return };
    let Ok(v) = serde_json::from_str::<Value>(&s) else { return };
    for a in v.get("accounts").and_then(|x| x.as_array()).into_iter().flatten() {
        let (Some(provider), Some(cmd)) = (
            a.get("provider").and_then(|x| x.as_str()).map(|s| s.to_string()),
            a.get("cmd").and_then(|x| x.as_str()).map(|s| s.to_string()),
        ) else {
            continue;
        };
        if a.get("adapter").and_then(|x| x.as_str()) != Some("cmd") {
            continue;
        }
        let interval = a
            .get("interval_secs")
            .and_then(|x| x.as_u64())
            .unwrap_or(300)
            .max(60);
        let d = daemon.clone();
        tokio::spawn(async move {
            loop {
                // 플랫폼별 셸 위임 — Windows는 sh 부재(cmd /C). 실패는 무해(다음 주기 재시도).
                let fut = if cfg!(windows) {
                    // ★콘솔 없는 cysd 가 콘솔 자식(cmd)을 숨김 없이 낳으면 주기마다 새 콘솔 창이 뜬다
                    // (TICKET=cysr-brand-version — 이 줄만 스폰 규약에서 빠져 있었다).
                    tokio::process::Command::new("cmd").args(["/C", &cmd]).hide_console().output()
                } else {
                    tokio::process::Command::new("sh").args(["-c", &cmd]).output()
                };
                if let Ok(Ok(out)) =
                    tokio::time::timeout(std::time::Duration::from_secs(10), fut).await
                {
                    if out.status.success() {
                        if let Ok(arr) = serde_json::from_slice::<Value>(&out.stdout) {
                            let rate: Vec<RateWindow> = arr
                                .as_array()
                                .into_iter()
                                .flatten()
                                .filter_map(|w| {
                                    Some(RateWindow {
                                        label: w.get("label")?.as_str()?.to_string(),
                                        used_pct: w.get("used_pct")?.as_f64()?,
                                        resets_at: w.get("resets_at").and_then(|x| x.as_f64()),
                                    })
                                })
                                .collect();
                            if !rate.is_empty() {
                                let now = crate::state::now_epoch();
                                let src = format!("adapter:{provider}");
                                note_custom(&d, &provider, &rate, &src, now);
                            }
                        }
                    }
                }
                tokio::time::sleep(std::time::Duration::from_secs(interval)).await;
            }
        });
    }
}

/// 선언 provider(비 내장) 계정에 rate 반영 — note_rate의 resolve를 우회하는 직접 키 경로.
fn note_custom(daemon: &Arc<Daemon>, provider: &str, rate: &[RateWindow], source: &str, now: f64) {
    let mut st = daemon.accounts.lock().unwrap();
    let key = AccountKey { provider: provider.into(), account_id: "default".into() };
    let label = st.views.get(&key).map(|v| v.label.clone()).unwrap_or_else(|| provider.into());
    let v = st.views.entry(key.clone()).or_insert_with(|| AccountView {
        key,
        label,
        plan: None,
        profiles: BTreeSet::new(),
        rate: Vec::new(),
        updated_at: 0.0,
        source: String::new(),
        adapter: true,
        scoped: Vec::new(),
    });
    if now >= v.updated_at {
        v.rate = rate.to_vec();
        v.updated_at = now;
        v.source = source.into();
        v.adapter = true;
    }
}

// ── Claude OAuth usage API 프로브 (오너 승인 2026-08-07 티켓⑤)
//
// 무엇을 푸는가: 5h·7d는 statusline이 주지만 **Claude 페인이 턴을 돌 때만** 온다. 모델 스코프
// 주간 게이지(Fable)는 statusline JSON에 **아예 없다**(실측 — five_hour·seven_day 둘뿐).
// ⇒ Claude Code의 /usage가 쓰는 서버 API를 우리도 직접 조회해 계정 저장소에 넣는다.
//
// 실측(2026-08-07 02:1x · 재검증 완료): `GET https://api.anthropic.com/api/oauth/usage`
//   헤더 `Authorization: Bearer <accessToken>` + `anthropic-beta: oauth-2025-04-20` → 200
//   `limits[]` = {kind: session|weekly_all|weekly_scoped, percent, resets_at(RFC3339), scope, …}
//   weekly_scoped.scope.model.display_name = "Fable" · 값이 오너 /usage 화면과 일치.
//
// ★신선도 실측 단서: 창이 굴러가는 순간(5h 리셋) API가 **약 1~2분간 직전 창을 계속 보고**한다
//   (02:11:35 조회 = 61%/리셋 02:10(과거) · 02:12:07 조회 = 0%/리셋 07:10). 그러므로 이 값을
//   statusline보다 무조건 우선시키지 않는다 — `rate`에서 신선도로 겨루게 두면 자연히 해소된다.
//
// ⛔토큰 규율: 토큰은 **프로세스 메모리와 파이프에만** 존재한다. 디스크·로그·환경변수·argv 어디에도
//   남기지 않는다. curl에 `-H "Authorization: …"`을 쓰면 argv에 실려 `ps`로 온 시스템에 보이므로,
//   헤더는 `--config -`(stdin)로 넣는다. 실패 로그에도 응답 본문을 찍지 않는다(토큰은 아니지만
//   계정 정보가 섞일 수 있고, 로그는 우리가 지우지 않는 곳이다).

/// 프로브 주기(초) — master 지정 2~5분의 중앙. 계정 한도는 분 단위로 움직이므로 이보다 촘촘할 이유가 없다.
const OAUTH_PROBE_INTERVAL_SECS: u64 = 180;
/// 연속 실패 시 주기 배수 상한 — 180s × 2^3 = 24분. 「재시도 폭주 금지」(master 규율).
const OAUTH_PROBE_MAX_BACKOFF_SHIFT: u32 = 3;
/// 외부 명령 1회 타임아웃(초) — 키체인·네트워크 모두. 매달리지 않는다.
const OAUTH_PROBE_CMD_TIMEOUT_SECS: u64 = 10;

/// OAuth usage 응답 → (rate 창들, 모델 스코프 게이지들). **응답 형태를 아는 유일한 자리**다.
///
/// ★순수 함수로 뽑아 둔 이유: 결함이 나는 곳은 늘 「필드 경로를 아는 지식」인데, 그 지식이
/// 네트워크·프로세스와 뒤엉킨 자리에 있으면 테스트가 닿지 못한다. (같은 이유로 뽑혀 나왔던
/// UI 쪽 짝 `wsusage.fableFromAnalytics`는 티켓⑥에서 그 줄과 함께 삭제됐다 — 교훈만 남는다.)
/// 아래 테스트는 **실물 응답 형태 그대로**를 픽스처로 쓴다.
///
/// 형태가 바뀌면 rate가 비고, 호출자는 그것을 「원천 소실」로 다룬다(경보가 아니라 조용한 강등).
pub fn parse_oauth_usage(v: &Value, now: f64) -> (Vec<RateWindow>, Vec<ScopedGauge>) {
    let iso = |x: &Value| -> Option<f64> {
        chrono::DateTime::parse_from_rfc3339(x.as_str()?).ok().map(|d| d.timestamp() as f64)
    };
    let mut rate = Vec::new();
    let mut scoped = Vec::new();
    for l in v.get("limits").and_then(|x| x.as_array()).into_iter().flatten() {
        let Some(pct) = l.get("percent").and_then(|x| x.as_f64()) else { continue };
        let resets_at = l.get("resets_at").and_then(iso);
        match l.get("kind").and_then(|x| x.as_str()) {
            // 라벨은 statusline·codex·agy와 **같은 어휘**를 쓴다 — 한 표 안에서 같은 창이 다른
            // 이름으로 두 줄 나오면 사용자는 그것을 두 한도로 읽는다.
            Some("session") => rate.push(RateWindow { label: "5h".into(), used_pct: pct, resets_at }),
            Some("weekly_all") => rate.push(RateWindow { label: "7d".into(), used_pct: pct, resets_at }),
            Some("weekly_scoped") => {
                // ★모델 이름이 없으면 게이지를 만들지 않는다. 이름 없는 게이지는 「무엇의 5%인지」를
                //   말할 수 없고, 우리가 이름을 지어 넣으면 없는 사실을 만드는 것이다.
                let Some(model) = l
                    .pointer("/scope/model/display_name")
                    .and_then(|x| x.as_str())
                    .filter(|s| !s.is_empty())
                else {
                    continue;
                };
                scoped.push(ScopedGauge {
                    model: model.to_string(),
                    used_pct: pct,
                    resets_at,
                    updated_at: now,
                    source: "oauth".into(),
                });
            }
            _ => {}
        }
    }
    // limits[]가 없는 옛/새 형태를 위한 보조 경로 — 최상위 five_hour·seven_day.
    // ★보조 경로에는 모델 스코프가 없다(실측: 최상위 seven_day_* 필드들은 전부 null). 즉 이 경로로
    //   떨어지면 Fable 줄은 조용히 사라진다 — 그것이 정직한 표현이다(없는 값을 지어내지 않는다).
    if rate.is_empty() {
        for (k, label) in [("five_hour", "5h"), ("seven_day", "7d")] {
            let Some(o) = v.get(k).filter(|x| x.is_object()) else { continue };
            let Some(pct) = o.get("utilization").and_then(|x| x.as_f64()) else { continue };
            rate.push(RateWindow { label: label.into(), used_pct: pct, resets_at: o.get("resets_at").and_then(iso) });
        }
    }
    rate.sort_by_key(|r| u8::from(r.label != "5h")); // 5h 먼저 (배지·사이드바 순서 안정)
    scoped.sort_by(|a, b| a.model.cmp(&b.model));
    (rate, scoped)
}

/// OAuth 프로브 관측을 claude 계정에 반영 — `rate`는 종전 규율대로 겨루고, `scoped`는 자기 슬롯에 산다.
///
/// ★`scoped`를 무조건 덮는 이유: 이 슬롯의 생산자는 프로브 하나뿐이다. 경쟁자가 없으므로 최신이
/// 곧 진실이고, 시각도 게이지 자신이 들고 있어 UI가 따로 나이를 잰다.
fn note_oauth(
    daemon: &Arc<Daemon>,
    account_id: &str,
    label: &str,
    rate: &[RateWindow],
    scoped: &[ScopedGauge],
    now: f64,
) {
    let key = AccountKey { provider: "claude".into(), account_id: account_id.into() };
    let mut to_persist: Vec<(AccountKey, String, String, f64, Option<f64>)> = Vec::new();
    {
        let mut st = daemon.accounts.lock().unwrap();
        let v = st.views.entry(key.clone()).or_insert_with(|| AccountView {
            key: key.clone(),
            label: label.into(),
            plan: None,
            profiles: BTreeSet::new(),
            rate: Vec::new(),
            updated_at: 0.0,
            source: String::new(),
            adapter: true,
            scoped: Vec::new(),
        });
        // scoped는 rate 승패와 무관하게 갱신한다(위 주석) — statusline이 이겨도 살아남는 축.
        // ★(usage-two-accounts) 비어 있어도 **덮는다**: 이 함수는 응답을 받은 프로브에서만 불리므로
        //   빈 scoped = 「이 계정의 서버 응답에 모델 스코프 창이 없다」는 관측이다. 옛 게이지를 남기면
        //   없는 창이 나이만 먹으며 「죽은 창」으로 그려진다 — 없다를 죽었다로 보이게 하는 것이다.
        v.scoped = scoped.to_vec();
        if !rate.is_empty() && now >= v.updated_at {
            v.rate = rate.to_vec();
            v.updated_at = now;
            v.source = "oauth".into();
        }
        // 스냅샷 영속은 statusline 경로와 **같은 스로틀**을 쓴다(원천이 둘이어도 시계열은 하나다).
        for w in rate {
            let pk = (key.clone(), w.label.clone());
            let prev = st.last_persisted.get(&pk).copied();
            if prev.map_or(true, |p| (w.used_pct - p).abs() >= SNAPSHOT_MIN_DELTA_PCT) {
                st.last_persisted.insert(pk, w.used_pct);
                let lbl = st.views[&key].label.clone();
                to_persist.push((key.clone(), lbl, w.label.clone(), w.used_pct, w.resets_at));
            }
        }
    }
    if to_persist.is_empty() {
        return;
    }
    let guard = daemon.analytics.lock().unwrap(); // 잠금 순서: accounts 해제 후 analytics
    if let Some(conn) = guard.as_ref() {
        for (key, label, win, pct, resets) in &to_persist {
            crate::analytics::record_rate_snapshot(
                conn, now, &key.provider, &key.account_id, label, win, *pct, *resets,
            );
        }
    }
}

/// 외부 명령 1회 실행 — 표준입력을 주고 stdout을 받는다. 실패는 사유 문자열로.
async fn run_capture(program: &str, args: &[&str], stdin_data: Option<&str>) -> Result<Vec<u8>, String> {
    use tokio::io::AsyncWriteExt;
    // ★콘솔 없는 cysd 의 주기 프로브(curl) — 숨김 조립점 경유(TICKET=cysr-console-flicker-r2).
    let mut cmd = cys::hidden_tokio_command(program);
    cmd.args(args)
        .stdin(if stdin_data.is_some() { std::process::Stdio::piped() } else { std::process::Stdio::null() })
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped());
    let mut child = cmd.spawn().map_err(|e| format!("{program} spawn: {e}"))?;
    if let Some(data) = stdin_data {
        let mut si = child.stdin.take().ok_or_else(|| format!("{program}: stdin 없음"))?;
        si.write_all(data.as_bytes()).await.map_err(|e| format!("{program} stdin: {e}"))?;
        drop(si); // EOF — 안 닫으면 curl이 설정 끝을 못 보고 매달린다
    }
    let out = tokio::time::timeout(
        std::time::Duration::from_secs(OAUTH_PROBE_CMD_TIMEOUT_SECS),
        child.wait_with_output(),
    )
    .await
    .map_err(|_| format!("{program}: 타임아웃"))?
    .map_err(|e| format!("{program}: {e}"))?;
    if !out.status.success() {
        // ⛔stderr 본문을 로그로 흘리지 않는다 — 종료코드만 말한다.
        return Err(format!("{program}: 종료코드 {:?}", out.status.code()));
    }
    Ok(out.stdout)
}

/// 기본 설정 dir(`~/.claude`)의 키체인 서비스명 — 접미 없음.
const KEYCHAIN_SERVICE_BASE: &str = "Claude Code-credentials";

/// 프로필 dir → 그 dir의 자격증명이 사는 키체인 서비스명. (TICKET=usage-two-accounts)
///
/// ★산식(실측 2026-09-19 · 이 기계의 키체인 항목 4개 전부 일치):
///   - `~/.claude`(`CLAUDE_CONFIG_DIR` 미설정의 기본 dir) → `Claude Code-credentials`(접미 없음)
///   - 그 밖의 dir(`CLAUDE_CONFIG_DIR=<dir>`로 띄운 프로필) → `Claude Code-credentials-<h8>`,
///     `h8` = **sha256(dir 절대경로 문자열)** 16진 앞 8자리. 끝 슬래시 없는 경로 그대로다
///     (`/…/.cys/claude` → a5d624bb · `/…/.cys/claude/` 는 ce6f8805로 다른 이름 — 그래서 dir을
///     열거 결과 그대로 쓰고 손으로 이어 붙이지 않는다).
///   근거: `security dump-keychain`의 서비스명 접미 4종(0bb9bba4·42f72ae1·8e8febd2·a5d624bb)이
///   `~/.cys/claude-default-dept-1`·`~/.cys/claude-axdev`·`~/.claude-acct2`·`~/.cys/claude`의
///   sha256 앞 8자리와 하나씩 정확히 맞는다. 시험 `keychain_service_names_match_measured_formula`가
///   산식을 고정한다(실물 네 쌍은 개인 경로라 HANDOFF 표에 둔다)(Claude Code가 산식을 바꾸면 그 시험이 아니라 운영에서 「원천 소실」로 드러난다
///   — 산식은 우리 것이 아니므로 시험은 실측을 고정할 뿐이다).
pub fn keychain_service_for(home: &Path, dir: &Path) -> String {
    use sha2::{Digest, Sha256};
    if dir == home.join(".claude") {
        return KEYCHAIN_SERVICE_BASE.to_string();
    }
    let digest = Sha256::digest(dir.to_string_lossy().as_bytes());
    let h8: String = digest.iter().take(4).map(|b| format!("{b:02x}")).collect();
    format!("{KEYCHAIN_SERVICE_BASE}-{h8}")
}

/// 프로브 대상 1건 = claude 계정 1개. 같은 계정을 쓰는 프로필이 여럿이면 후보가 여럿이다.
#[derive(Clone, Debug, PartialEq)]
pub struct ProbeTarget {
    pub account_id: String,
    pub label: String,
    /// (프로필 홈 상대 표기, 키체인 서비스명) — 앞에서부터 시도한다. 기본 dir이 늘 맨 앞이다.
    pub candidates: Vec<(String, String)>,
}

/// 프로필 dir들 → 계정별 프로브 대상. **토큰을 꺼낼 dir과 신원을 읽는 dir이 언제나 같다**(짝 유지):
/// 후보는 `.claude.json`에 accountUuid가 있는 dir만이고, 그 dir의 키체인 항목을 쓴다.
///
/// ★왜 계정마다 후보를 여럿 두는가(실측): 프로필마다 키체인 항목이 따로 있고, 안 쓰는 프로필의
/// 항목은 갱신되지 않아 토큰이 낡는다(`~/.cys/claude-axdev` 항목 = 07-06 이후 무갱신). 한 dir만
/// 고르면 그 dir이 낡은 쪽일 때 계정 전체가 소실된다 — 앞에서부터 시도해 처음 성공한 값을 쓴다.
pub fn probe_targets(
    state: &mut AccountsState,
    home: &Path,
    dirs: &[PathBuf],
) -> Vec<ProbeTarget> {
    let default_dir = home.join(".claude");
    let mut ordered: Vec<&PathBuf> = dirs.iter().collect();
    // 기본 dir 먼저, 나머지는 경로순(열거 순서는 read_dir 순서라 안정적이지 않다).
    ordered.sort_by(|a, b| (**a != default_dir).cmp(&(**b != default_dir)).then(a.cmp(b)));
    let mut out: Vec<ProbeTarget> = Vec::new();
    for dir in ordered {
        let Some((uuid, email, _plan)) = claude_identity(state, dir) else { continue };
        // 표기는 넘겨받은 `home` 기준(profile_short는 실제 홈을 다시 묻는다 — 대상과 표기의 홈이 갈린다).
        let short = dir.strip_prefix(home).map(|r| r.to_string_lossy().into_owned())
            .unwrap_or_else(|_| dir.to_string_lossy().into_owned());
        let cand = (short, keychain_service_for(home, dir));
        match out.iter_mut().find(|t| t.account_id == uuid) {
            Some(t) => t.candidates.push(cand),
            None => out.push(ProbeTarget { account_id: uuid, label: email, candidates: vec![cand] }),
        }
    }
    out.sort_by(|a, b| a.account_id.cmp(&b.account_id));
    out
}

/// 계정 1개 프로브 — 후보 프로필을 앞에서부터 시도해 처음 성공한 응답을 그 계정에 반영한다.
///
/// `fetch` = 키체인 서비스명 → 응답(JSON). 운영에서는 [`live_fetch`], 시험에서는 가짜를 넣는다
/// (키체인·네트워크 없이 「어느 계정이 불렸는가」와 「실패가 번지는가」를 재기 위해서다).
/// 실패 사유에는 프로필 표기만 싣는다(토큰·응답 본문은 싣지 않는다).
async fn probe_account<F, Fut>(daemon: &Arc<Daemon>, t: &ProbeTarget, fetch: &F) -> Result<(), String>
where
    F: Fn(String) -> Fut,
    Fut: std::future::Future<Output = Result<Value, String>>,
{
    let mut errs: Vec<String> = Vec::new();
    for (profile, service) in &t.candidates {
        match fetch(service.clone()).await {
            Ok(v) => {
                let now = crate::state::now_epoch();
                let (rate, scoped) = parse_oauth_usage(&v, now);
                if rate.is_empty() && scoped.is_empty() {
                    errs.push(format!("{profile}: 응답에 한도 정보가 없다(형태 변경?)"));
                    continue;
                }
                note_oauth(daemon, &t.account_id, &t.label, &rate, &scoped, now);
                return Ok(());
            }
            Err(e) => errs.push(format!("{profile}: {e}")),
        }
    }
    Err(errs.join(" · "))
}

/// 계정별 백오프 상태 — (연속 실패 수, 다음 시도 가능 시각). 계정끼리 공유하지 않는다.
type ProbeBackoff = HashMap<String, (u32, f64)>;

/// 프로브 한 바퀴 — 대상 계정 각각을 **따로** 조회한다. 한 계정의 실패는 그 계정의 백오프만 늘린다.
///
/// ★로그는 계정의 상태가 **바뀔 때만** 찍는다(종전 규율 그대로) — 계정을 알아보는 꼬리표는 앞 8자
/// uuid다(이메일은 로그에 남기지 않는다: 로그는 우리가 지우지 않는 곳이다).
async fn probe_round<F, Fut>(
    daemon: &Arc<Daemon>,
    targets: &[ProbeTarget],
    backoff: &mut ProbeBackoff,
    now: f64,
    fetch: &F,
) where
    F: Fn(String) -> Fut,
    Fut: std::future::Future<Output = Result<Value, String>>,
{
    // 사라진 계정의 백오프는 버린다(현재 대상 집합 기준 — 다음에 돌아오면 새로 시작).
    backoff.retain(|k, _| targets.iter().any(|t| &t.account_id == k));
    for t in targets {
        let (fails, due) = backoff.get(&t.account_id).copied().unwrap_or((0, 0.0));
        if due > now {
            continue;
        }
        let tag: String = t.account_id.chars().take(8).collect();
        match probe_account(daemon, t, fetch).await {
            Ok(()) => {
                if fails > 0 {
                    eprintln!("[cysd] oauth-usage: 원천 복구 [{tag}] (연속 실패 {fails}회 후)");
                }
                backoff.insert(t.account_id.clone(), (0, 0.0));
            }
            Err(e) => {
                if fails == 0 {
                    eprintln!("{}", oauth_lost_line(&format!("[{tag}] {e}")));
                }
                let fails = fails.saturating_add(1);
                let shift = fails.min(OAUTH_PROBE_MAX_BACKOFF_SHIFT);
                // 대기 = 주기 × 2^shift. 틱은 「주기 + 조회 소요」마다 오므로 반 주기를 빼 둔다 —
                // 안 빼면 소요만큼 늦은 틱이 기한을 넘기지 못해 한 틱을 더 건너뛴다(2배가 3배가 된다).
                let iv = OAUTH_PROBE_INTERVAL_SECS as f64;
                let wait = iv * (1u64 << shift) as f64 - iv / 2.0;
                backoff.insert(t.account_id.clone(), (fails, now + wait));
            }
        }
    }
}

/// 운영 대상 — 지금 디스크의 프로필 열거(seed_known과 같은 정본 `enumerate_profile_dirs`).
fn current_targets(daemon: &Arc<Daemon>) -> Result<Vec<ProbeTarget>, String> {
    let home = dirs::home_dir().ok_or_else(|| "홈 dir 불명".to_string())?;
    let dirs = cys::profile_gate::enumerate_profile_dirs(&home);
    let mut st = daemon.accounts.lock().unwrap();
    Ok(probe_targets(&mut st, &home, &dirs))
}

/// 키체인에서 Claude Code OAuth 액세스 토큰. **반환값을 로그에 찍지 마라.**
/// 서비스명은 [`keychain_service_for`]가 정한다(프로필마다 항목이 따로 있다).
async fn keychain_token(service: &str) -> Result<String, String> {
    let raw = run_capture("security", &["find-generic-password", "-s", service, "-w"], None).await?;
    let v: Value = serde_json::from_slice(&raw).map_err(|_| "키체인 항목이 JSON이 아니다".to_string())?;
    v.pointer("/claudeAiOauth/accessToken")
        .and_then(|x| x.as_str())
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .ok_or_else(|| "키체인 항목에 accessToken이 없다".to_string())
}

/// 운영 fetch — 키체인 항목 → 토큰 → usage API. 토큰은 이 함수 밖으로 나가지 않는다.
async fn live_fetch(service: String) -> Result<Value, String> {
    let token = keychain_token(&service).await?;
    let v = fetch_oauth_usage(&token).await;
    drop(token); // 필요 이상으로 들고 있지 않는다
    v
}

/// usage API 1회 조회. 토큰은 argv가 아니라 **stdin(curl --config -)** 으로만 건넨다.
async fn fetch_oauth_usage(token: &str) -> Result<Value, String> {
    // curl 설정 파일 문법: `key = "value"`. 값 안의 큰따옴표만 이스케이프하면 된다.
    // 토큰은 `sk-ant-…` 형태라 따옴표가 없지만, 형태를 믿지 않고 escape한다.
    let esc = token.replace('\\', "\\\\").replace('"', "\\\"");
    let cfg = format!(
        concat!(
            "url = \"https://api.anthropic.com/api/oauth/usage\"\n",
            "header = \"Authorization: Bearer {}\"\n",
            "header = \"anthropic-beta: oauth-2025-04-20\"\n",
            "silent\n",
            "show-error\n",
            "max-time = {}\n",
            "write-out = \"\\n%{{http_code}}\"\n",
        ),
        esc, OAUTH_PROBE_CMD_TIMEOUT_SECS
    );
    let out = run_capture("curl", &["--config", "-"], Some(&cfg)).await?;
    let text = String::from_utf8_lossy(&out);
    let (body, code) = text.rsplit_once('\n').ok_or_else(|| "응답 형태 불명".to_string())?;
    if code.trim() != "200" {
        // ★본문은 찍지 않는다. 401은 토큰 만료(Claude Code가 갱신하면 다음 주기에 저절로 낫는다).
        return Err(format!("HTTP {}", code.trim()));
    }
    serde_json::from_str(body).map_err(|_| "응답이 JSON이 아니다".to_string())
}

/// 실패 1줄의 정본 문구 — 상주 프로브와 강제발화가 **같은 문장**을 쓴다.
/// (두 곳이 따로 문장을 지으면, 강제발화로 확인한 실패 표현이 운영 로그의 표현과 달라져
///  「내가 본 것」과 「로그에 남는 것」이 어긋난다.)
fn oauth_lost_line(e: &str) -> String {
    format!("[cysd] oauth-usage: 원천 소실 — {e}")
}

/// 강제발화 — `cysd --oauth-usage-probe`. 데몬을 띄우지 않고 프로브 1회만 돌고 끝난다.
///
/// ★왜 필요한가: 이 경로에서 깨질 수 있는 두 가지(키체인 접근·외부 HTTPS)는 **실행 컨텍스트에
/// 좌우된다** — 사람이 로그인한 셸에서 된다는 것은 launchd 아래 cysd에서 된다는 증거가 아니다.
/// 데몬 본체를 띄우지 않고 **같은 코드**로 그 컨텍스트를 찍어 볼 수 있어야 검증이 성립한다.
/// (usage-two-accounts) 계정마다 한 덩어리로 찍는다 — 꼬리표 = uuid 앞 8자 + 성공한 프로필.
/// ⛔출력에는 값(%·리셋 시각)만 싣는다. 토큰은 어떤 경로로도 나가지 않는다.
/// 반환 = 프로세스 종료코드(0 = 모든 계정 정상 · 1 = 한 계정이라도 원천 소실 또는 대상 0).
pub async fn oauth_probe_report() -> i32 {
    let now = crate::state::now_epoch();
    let targets = match dirs::home_dir() {
        Some(home) => {
            let dirs = cys::profile_gate::enumerate_profile_dirs(&home);
            probe_targets(&mut AccountsState::default(), &home, &dirs)
        }
        None => Vec::new(),
    };
    if targets.is_empty() {
        eprintln!("{}", oauth_lost_line("신원 있는 claude 프로필이 없다"));
        return 1;
    }
    let mut rc = 0;
    for t in &targets {
        let tag: String = t.account_id.chars().take(8).collect();
        let mut errs: Vec<String> = Vec::new();
        let mut done = false;
        for (profile, service) in &t.candidates {
            match live_fetch(service.clone()).await {
                Ok(v) => {
                    let (rate, scoped) = parse_oauth_usage(&v, now);
                    if rate.is_empty() && scoped.is_empty() {
                        errs.push(format!("{profile}: 응답에 한도 정보가 없다(형태 변경?)"));
                        continue;
                    }
                    for w in &rate {
                        println!(
                            "[cysd] oauth-usage: [{tag} {profile}] {} {:.0}% resets_at={:?}",
                            w.label, w.used_pct, w.resets_at
                        );
                    }
                    for g in &scoped {
                        println!(
                            "[cysd] oauth-usage: [{tag} {profile}] 7d·{} {:.0}% resets_at={:?}",
                            g.model, g.used_pct, g.resets_at
                        );
                    }
                    done = true;
                    break;
                }
                Err(e) => errs.push(format!("{profile}: {e}")),
            }
        }
        if !done {
            eprintln!("{}", oauth_lost_line(&format!("[{tag}] {}", errs.join(" · "))));
            rc = 1;
        }
    }
    rc
}

/// claude 계정 OAuth usage 프로브 상주 — 계정마다 주기 조회·계정마다 따로 백오프.
///
/// 실패는 **경보가 아니라 「원천 소실」 1줄**이다(master 규율): 이 값이 없어도 statusline 원천이
/// 그대로 살아 있고, 프로브 유래 행은 나이가 자라 자연히 stale로 강등된다. 시끄럽게 굴 이유가 없다.
/// ★대상은 매 바퀴 다시 연다 — 부트 뒤 새 프로필이 생기거나 로그인이 바뀌어도 따라간다.
pub fn spawn_claude_oauth_probe(daemon: Arc<Daemon>) {
    tokio::spawn(async move {
        let mut backoff: ProbeBackoff = HashMap::new();
        let mut lost_targets = false;
        loop {
            match current_targets(&daemon) {
                Ok(targets) if !targets.is_empty() => {
                    lost_targets = false;
                    let now = crate::state::now_epoch();
                    probe_round(&daemon, &targets, &mut backoff, now, &live_fetch).await;
                }
                Ok(_) | Err(_) => {
                    if !lost_targets {
                        eprintln!("{}", oauth_lost_line("신원 있는 claude 프로필이 없다"));
                    }
                    lost_targets = true;
                }
            }
            tokio::time::sleep(std::time::Duration::from_secs(OAUTH_PROBE_INTERVAL_SECS)).await;
        }
    });
}

/// 소진 예측 최소 표본 수·스팬(초) — 미달 시 예측 미표시(표본 2개 기울기의 황당 예측 차단).
const PREDICT_MIN_POINTS: usize = 3;
const PREDICT_MIN_SPAN_SECS: f64 = 600.0;
/// 예측 대상 신선도(초) — stale 관측으로 예측하지 않는다.
const PREDICT_FRESH_SECS: f64 = 600.0;

/// 로컬 계정 뷰 → JSON 배열 (usage.accounts RPC·control.dashboard "accounts" 공용).
/// stale_secs는 읽기 시점 계산 — updated_at==0.0은 null(관측 전)로 정직 표기.
/// 5h 창에는 소진 예측(exhaust_at)을 붙인다 — 최근 60분 선형 기울기, 표본 미달·기울기≤0·
/// 리셋 후 소진이면 생략(정직한 공백). 잠금 순서: accounts → 해제 → analytics.
pub fn local_json(daemon: &Arc<Daemon>, now: f64) -> Value {
    let mut rows: Vec<Value> = {
        let st = daemon.accounts.lock().unwrap();
        let mut views: Vec<&AccountView> = st.views.values().collect();
        views.sort_by(|a, b| a.key.cmp(&b.key));
        views
            .into_iter()
            .map(|v| {
                json!({
                    "provider": v.key.provider,
                    "account_id": v.key.account_id,
                    "label": v.label,
                    "plan": v.plan,
                    "profiles": v.profiles.iter().collect::<Vec<_>>(),
                    // ★창마다 stale·stale_reason을 덧붙인다(읽기 시점 판정 · 상태 파괴 없음). used_pct·resets_at은
                    //   **그대로** 숫자로 나간다 — 소비자(usage-gate·sentinel·statusline)가 숫자 계약에 묶여 있다.
                    //   관측 시각 = 계정 updated_at(rate 슬롯의 시각).
                    "rate": v.rate.iter().map(|w| rate_window_json(w, v.updated_at, now)).collect::<Vec<_>>(),
                    "updated_at": if v.updated_at > 0.0 { json!(v.updated_at) } else { Value::Null },
                    "stale_secs": if v.updated_at > 0.0 { json!((now - v.updated_at).max(0.0)) } else { Value::Null },
                    "source": v.source,
                    "adapter": v.adapter,
                    // 모델 스코프 게이지 — ★자기 updated_at을 들고 나간다. 계정의 updated_at(rate 슬롯)을
                    // 물려 쓰면 statusline이 rate를 갱신할 때마다 이 게이지가 「방금 관측」으로 둔갑한다.
                    "scoped": v.scoped.iter().map(|g| json!({
                        "model": g.model,
                        "used_pct": g.used_pct,
                        "resets_at": g.resets_at,
                        "updated_at": g.updated_at,
                        "source": g.source,
                        // 스코프 게이지는 자기 관측 시각(g.updated_at)으로 잰다 — 위 주석과 같은 이유.
                        "stale": rate_window_stale_reason(g.resets_at, g.updated_at, now).is_some(),
                        "stale_reason": rate_window_stale_reason(g.resets_at, g.updated_at, now),
                    })).collect::<Vec<_>>(),
                })
            })
            .collect()
    };
    // 소진 예측 — 신선(≤10분) 계정의 5h 창만. accounts 락 해제 후 analytics 조회(잠금 순서).
    let guard = daemon.analytics.lock().unwrap();
    if let Some(conn) = guard.as_ref() {
        for row in rows.iter_mut() {
            let fresh = row["stale_secs"].as_f64().map(|s| s <= PREDICT_FRESH_SECS).unwrap_or(false);
            if !fresh {
                continue;
            }
            let (provider, account) = (
                row["provider"].as_str().unwrap_or("").to_string(),
                row["account_id"].as_str().unwrap_or("").to_string(),
            );
            let resets_at = row["rate"]
                .as_array()
                .into_iter()
                .flatten()
                .find(|w| w["label"] == "5h")
                .and_then(|w| w["resets_at"].as_f64());
            let series = crate::analytics::rate_series(conn, &provider, &account, "5h", now - 3600.0);
            if let Some(t) = predict_exhaust(&series, now, resets_at) {
                row["exhaust_at"] = json!(t);
            }
        }
    }
    Value::Array(rows)
}

/// rate 창 stale 사유(순수 — 테스트 핀). None = 신선. (TICKET=cys-usage-stale-rate)
///
/// 왜: `~/.antigravity` 폴더만 있어도 계정이 등록되고(seed_known), 마지막 관측값(agy-rpc 09-12)이
/// 프로세스 0인 채로 71시간 뒤에도 살아 있는 숫자처럼 나갔다 — 계정 rate 창에는 만료 규칙이 없었다
/// (usage.rs idle_stale_transition은 세션 매핑 전용).
/// ① `resets_at < now` → `resets_at_passed`: 그 %는 이미 리셋된 창의 값이다. ★먼저 본다 —
///    관측이 신선해도 리셋이 지났으면 값은 죽었다.
/// ② `now - observed_at > 24h` → `no_observation_24h`. observed_at<=0(관측 전)도 여기로 떨어진다.
/// 경계는 둘 다 엄격 부등호: 리셋 시각 그 순간·정확히 24h 경과는 아직 신선.
pub fn rate_window_stale_reason(resets_at: Option<f64>, observed_at: f64, now: f64) -> Option<&'static str> {
    if matches!(resets_at, Some(r) if r < now) {
        return Some("resets_at_passed");
    }
    if observed_at <= 0.0 || now - observed_at > RATE_STALE_NO_OBS_SECS {
        return Some("no_observation_24h");
    }
    None
}

/// rate 창 1개 → JSON. 종전 직렬화(`label`·`used_pct`·`resets_at`)를 그대로 두고 두 필드만 더한다.
fn rate_window_json(w: &RateWindow, observed_at: f64, now: f64) -> Value {
    let why = rate_window_stale_reason(w.resets_at, observed_at, now);
    json!({
        "label": w.label,
        "used_pct": w.used_pct,
        "resets_at": w.resets_at,
        "stale": why.is_some(),
        "stale_reason": why,
    })
}

/// 선형 소진 예측(순수 — 테스트 핀): 시계열 최소자승 기울기로 100% 도달 시각.
/// None = 표본 미달·스팬 미달·기울기≤0·이미 100%·예측이 리셋 이후(리셋이 먼저면 무의미).
pub fn predict_exhaust(series: &[(f64, f64)], now: f64, resets_at: Option<f64>) -> Option<f64> {
    if series.len() < PREDICT_MIN_POINTS {
        return None;
    }
    let span = series.last()?.0 - series.first()?.0;
    if span < PREDICT_MIN_SPAN_SECS {
        return None;
    }
    let n = series.len() as f64;
    let (sx, sy): (f64, f64) = series.iter().fold((0.0, 0.0), |a, p| (a.0 + p.0, a.1 + p.1));
    let (mx, my) = (sx / n, sy / n);
    let (mut num, mut den) = (0.0, 0.0);
    for (x, y) in series {
        num += (x - mx) * (y - my);
        den += (x - mx) * (x - mx);
    }
    if den <= 0.0 {
        return None;
    }
    let slope = num / den; // %/초
    let last = series.last()?;
    if slope <= 0.0 || last.1 >= 100.0 {
        return None;
    }
    let t = last.0 + (100.0 - last.1) / slope;
    if t <= now {
        return None;
    }
    match resets_at {
        Some(r) if t >= r => None, // 리셋이 먼저 — 소진 경고 무의미
        _ => Some(t),
    }
}

/// alerts용 스냅샷: (라벨, 창, pct) — 관측된 계정만.
pub fn alert_rates(daemon: &Arc<Daemon>) -> Vec<(String, String, f64)> {
    let st = daemon.accounts.lock().unwrap();
    let mut out = Vec::new();
    for v in st.views.values() {
        if v.updated_at == 0.0 {
            continue;
        }
        for w in &v.rate {
            out.push((v.label.clone(), w.label.clone(), w.used_pct));
        }
    }
    out.sort_by(|a, b| (&a.0, &a.1).cmp(&(&b.0, &b.1)));
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    /// ★콘솔 창 깜빡임 회귀 핀(TICKET=cysr-brand-version): 주기 cmd 어댑터가 Windows `cmd /C` 를
    /// 창 숨김 없이 낳으면 콘솔 없는 cysd 아래에서 주기마다 새 콘솔 창이 뜬다. 그 스폰 문장에
    /// `.hide_console()` 이 붙어 있는지 **프로덕션 구간 소스**로 못박는다(Windows 동작 자체는 못 잰다).
    #[test]
    fn periodic_cmd_adapter_spawn_hides_console() {
        let src = include_str!("accounts.rs");
        let prod = &src[..src.find("#[cfg(test)]").expect("테스트 모듈 앵커 소실")];
        let spawns: Vec<&str> = prod
            .lines()
            .filter(|l| l.contains("Command::new(\"cmd\")"))
            .collect();
        assert_eq!(spawns.len(), 1, "cmd 스폰 문장 수가 바뀌었다 — 이 핀의 대상을 다시 확인하라: {spawns:?}");
        assert!(
            spawns[0].contains(".hide_console()"),
            "cmd /C 스폰에 hide_console 이 없다 — 윈도우에서 주기마다 콘솔 창이 뜬다: {}",
            spawns[0].trim()
        );
    }

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cys-acct-{}-{}", std::process::id(), tag));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn profile_dir_extraction() {
        assert_eq!(
            profile_dir_from_session("/Users/x/.claude-work/projects/-a/s.jsonl"),
            Some(PathBuf::from("/Users/x/.claude-work"))
        );
        assert_eq!(
            profile_dir_from_session("/Users/x/.cys/claude-default-dept-2/projects/-a/s.jsonl"),
            Some(PathBuf::from("/Users/x/.cys/claude-default-dept-2"))
        );
        assert_eq!(profile_dir_from_session("no-projects-marker.jsonl"), None);
        // Windows 역슬래시 경로 내성
        assert_eq!(
            profile_dir_from_session("C:\\Users\\x\\.claude\\projects\\-a\\s.jsonl"),
            Some(PathBuf::from("C:/Users/x/.claude"))
        );
    }

    #[test]
    fn identity_parse_and_junk_dir_skip() {
        let dir = tmp("ident");
        // 정상 프로필
        std::fs::write(
            dir.join(".claude.json"),
            r#"{"oauthAccount":{"accountUuid":"u-1","emailAddress":"a@b.c","userRateLimitTier":"max_5x"}}"#,
        )
        .unwrap();
        let mut st = AccountsState::default();
        let got = claude_identity(&mut st, &dir).unwrap();
        assert_eq!(got, ("u-1".into(), "a@b.c".into(), Some("max_5x".into())));
        // 캐시 적중(mtime 동일 → 재파싱 없이 동일 결과)
        assert_eq!(claude_identity(&mut st, &dir).unwrap().0, "u-1");
        // 잡동사니 dir(.claude.json 없음) → None
        let junk = tmp("junk");
        assert!(claude_identity(&mut st, &junk).is_none());
        // uuid 없는 파손 파일 → None (유령 계정 0)
        let broken = tmp("broken");
        std::fs::write(broken.join(".claude.json"), r#"{"oauthAccount":{}}"#).unwrap();
        assert!(claude_identity(&mut st, &broken).is_none());
    }

    #[test]
    fn predict_exhaust_pins() {
        // 표본 미달(2개) → None
        assert!(predict_exhaust(&[(0.0, 10.0), (600.0, 20.0)], 700.0, None).is_none());
        // 스팬 미달(<600s) → None
        assert!(
            predict_exhaust(&[(0.0, 10.0), (100.0, 20.0), (200.0, 30.0)], 300.0, None).is_none()
        );
        // 정상: 0→60%가 3600초 — 100% 도달 ≈ 6000초
        let s = [(0.0, 0.0), (1800.0, 30.0), (3600.0, 60.0)];
        let t = predict_exhaust(&s, 3600.0, None).unwrap();
        assert!((t - 6000.0).abs() < 1.0, "t={t}");
        // 리셋이 소진보다 먼저 → None
        assert!(predict_exhaust(&s, 3600.0, Some(5000.0)).is_none());
        // 감소 추세(slope≤0) → None
        assert!(
            predict_exhaust(&[(0.0, 60.0), (1800.0, 40.0), (3600.0, 20.0)], 3600.0, None)
                .is_none()
        );
    }

    /// 실물 응답 형태(2026-08-07 02:12 실측 · 값만 축약, 키·중첩은 원본 그대로).
    /// ★픽스처를 손으로 예쁘게 다듬지 않는다 — 실물이 안 때리는 형태로 만들면 초록불이 거짓이 된다.
    fn oauth_fixture() -> Value {
        serde_json::from_str(
            r#"{
              "five_hour": {"utilization": 0.0, "resets_at": "2026-08-07T07:10:00.688508+00:00",
                            "limit_dollars": null, "used_dollars": null, "remaining_dollars": null},
              "seven_day": {"utilization": 13.0, "resets_at": "2026-08-13T21:00:00.688530+00:00"},
              "seven_day_opus": null, "seven_day_sonnet": null, "seven_day_cowork": null,
              "extra_usage": {"is_enabled": false, "utilization": null},
              "member_dashboard_available": false,
              "limits": [
                {"kind":"session","group":"session","percent":0,"severity":"normal",
                 "resets_at":"2026-08-07T07:10:00.688508+00:00","scope":null,"is_active":false},
                {"kind":"weekly_all","group":"weekly","percent":13,"severity":"normal",
                 "resets_at":"2026-08-13T21:00:00.688530+00:00","scope":null,"is_active":true},
                {"kind":"weekly_scoped","group":"weekly","percent":6,"severity":"normal",
                 "resets_at":"2026-08-13T20:59:59.688768+00:00",
                 "scope":{"model":{"id":null,"display_name":"Fable"},"surface":null},"is_active":false}
              ]}"#,
        )
        .unwrap()
    }

    #[test]
    fn oauth_usage_parses_real_shape() {
        let (rate, scoped) = parse_oauth_usage(&oauth_fixture(), 1000.0);
        // 라벨 어휘는 statusline과 같아야 한다(한 표에서 같은 창이 두 이름으로 나오면 두 한도로 읽힌다)
        assert_eq!(rate.len(), 2);
        assert_eq!(rate[0].label, "5h", "5h 먼저 정렬");
        assert_eq!(rate[0].used_pct, 0.0);
        assert_eq!(rate[1].label, "7d");
        assert_eq!(rate[1].used_pct, 13.0);
        // RFC3339 → epoch (2026-08-13T21:00:00Z)
        assert_eq!(rate[1].resets_at, Some(1786654800.0));
        // 모델 스코프 게이지 — 이름은 응답이 준 것을 그대로 쓴다(상수 아님)
        assert_eq!(scoped.len(), 1);
        assert_eq!(scoped[0].model, "Fable");
        assert_eq!(scoped[0].used_pct, 6.0);
        assert_eq!(scoped[0].updated_at, 1000.0, "게이지는 자기 관측 시각을 들고 나간다");
        assert_eq!(scoped[0].source, "oauth");
    }

    #[test]
    fn oauth_usage_degrades_without_lying() {
        // ① limits[] 부재 → 최상위 five_hour/seven_day 보조 경로. **스코프 게이지는 안 만든다.**
        let mut v = oauth_fixture();
        v.as_object_mut().unwrap().remove("limits");
        let (rate, scoped) = parse_oauth_usage(&v, 1000.0);
        assert_eq!(rate.len(), 2, "보조 경로로 5h·7d는 살아난다");
        assert_eq!(rate[0].label, "5h");
        assert!(scoped.is_empty(), "최상위 형태엔 모델 스코프가 없다 — 지어내지 않는다");
        // ② display_name 없는 weekly_scoped → 게이지 없음(이름 없는 게이지는 무엇의 %인지 못 말한다)
        let v2: Value = serde_json::from_str(
            r#"{"limits":[{"kind":"weekly_scoped","percent":5,"resets_at":"2026-08-13T21:00:00Z",
                           "scope":{"model":{"id":null,"display_name":""},"surface":null}}]}"#,
        )
        .unwrap();
        let (r2, s2) = parse_oauth_usage(&v2, 1000.0);
        assert!(r2.is_empty() && s2.is_empty(), "이름 없는 스코프는 버린다");
        // ③ 형태 전면 변경 → 전부 비어 호출자가 「원천 소실」로 다룰 수 있다
        let v3: Value = serde_json::from_str(r#"{"something_else": 1}"#).unwrap();
        let (r3, s3) = parse_oauth_usage(&v3, 1000.0);
        assert!(r3.is_empty() && s3.is_empty());
        // ④ resets_at이 파싱 불가여도 pct는 살린다(시각 하나 때문에 값을 버리지 않는다)
        let v4: Value = serde_json::from_str(
            r#"{"limits":[{"kind":"session","percent":42,"resets_at":"어제"}]}"#,
        )
        .unwrap();
        let (r4, _) = parse_oauth_usage(&v4, 1000.0);
        assert_eq!(r4.len(), 1);
        assert_eq!(r4[0].used_pct, 42.0);
        assert_eq!(r4[0].resets_at, None);
    }

    // ── usage-two-accounts(TICKET=usage-two-accounts 2026-09-19): 계정별 OAuth 프로브 ──

    /// 실물 응답 2계정(2026-09-19 07:1x · 자기 세션 자격증명으로 읽기만 · 바이트 그대로 저장).
    /// ★식별 정보 없음을 확인하고 넣었다(uuid·메일·조직 0 — 한도 수치와 표시 문구뿐).
    fn oauth_fixture_account(which: char) -> Value {
        let raw = match which {
            'a' => include_str!("testdata/oauth_usage_account_a.json"),
            _ => include_str!("testdata/oauth_usage_account_b.json"),
        };
        serde_json::from_str(raw).unwrap()
    }

    #[test]
    fn oauth_usage_parses_both_real_accounts() {
        // 두 계정 모두 서버가 준 창은 5h·7d·7d·Fable 셋뿐이다(opus·sonnet 창은 null).
        let (ra, sa) = parse_oauth_usage(&oauth_fixture_account('a'), 1000.0);
        let (rb, sb) = parse_oauth_usage(&oauth_fixture_account('b'), 1000.0);
        let labels = |r: &[RateWindow]| r.iter().map(|w| w.label.clone()).collect::<Vec<_>>();
        assert_eq!(labels(&ra), ["5h", "7d"]);
        assert_eq!(labels(&rb), ["5h", "7d"]);
        assert_eq!((ra[0].used_pct, ra[1].used_pct), (2.0, 15.0));
        assert_eq!((rb[0].used_pct, rb[1].used_pct), (3.0, 43.0));
        assert_eq!(sa.len(), 1);
        assert_eq!(sb.len(), 1);
        assert_eq!((sa[0].model.as_str(), sa[0].used_pct), ("Fable", 21.0));
        assert_eq!((sb[0].model.as_str(), sb[0].used_pct), ("Fable", 40.0));
        // 2026-09-24T08:00:00.235872Z → 초 단위 절사
        assert_eq!(sb[0].resets_at, Some(1790236800.0));
    }

    /// 키체인 서비스명 산식 고정. 기대값은 셸 `printf '%s' <경로> | shasum -a 256`으로 **독립 계산**했다
    /// (같은 코드로 기대값을 만들면 산식이 틀려도 초록이다). 이 기계의 실물 항목 4개와의 대응은
    /// docs/HANDOFF-usage-two-accounts.md 표가 기록한다(개인 경로라 시험에는 중립 경로를 쓴다).
    #[test]
    fn keychain_service_names_match_measured_formula() {
        let home = Path::new("/srv/u");
        let svc = |rel: &str| keychain_service_for(home, &home.join(rel));
        assert_eq!(svc(".claude"), "Claude Code-credentials", "기본 dir = 접미 없음");
        assert_eq!(svc(".cys/claude"), "Claude Code-credentials-8b5dd325");
        assert_eq!(svc(".claude-acct2"), "Claude Code-credentials-ae069e2c");
        // 끝 슬래시가 붙으면 다른 이름이다 — 경로를 손으로 이어 붙이면 이 함정에 빠진다.
        assert_eq!(
            keychain_service_for(home, Path::new("/srv/u/.cys/claude/")),
            "Claude Code-credentials-af3852db"
        );
    }

    fn write_ident(dir: &Path, uuid: &str, email: &str) {
        std::fs::create_dir_all(dir).unwrap();
        std::fs::write(
            dir.join(".claude.json"),
            format!(r#"{{"oauthAccount":{{"accountUuid":"{uuid}","emailAddress":"{email}"}}}}"#),
        )
        .unwrap();
    }

    /// 계정 A(`~/.claude` + `~/.cys/claude-axdev`) · 계정 B(`~/.claude-acct2` + `~/.cys/claude`) —
    /// 이 기계의 실제 배치와 같은 모양. 반환 = (임시 홈, 프로필 열거).
    fn two_account_home(tag: &str) -> (PathBuf, Vec<PathBuf>) {
        let home = tmp(tag);
        write_ident(&home.join(".claude"), "uuid-a", "a@x.y");
        write_ident(&home.join(".cys/claude-axdev"), "uuid-a", "a@x.y");
        write_ident(&home.join(".claude-acct2"), "uuid-b", "b@x.y");
        write_ident(&home.join(".cys/claude"), "uuid-b", "b@x.y");
        std::fs::create_dir_all(home.join(".claude-worktrees")).unwrap(); // 신원 없는 잡동사니
        let dirs = cys::profile_gate::enumerate_profile_dirs(&home);
        (home, dirs)
    }

    #[test]
    fn probe_targets_one_per_account_default_first() {
        let (home, dirs) = two_account_home("probe-targets");
        let t = probe_targets(&mut AccountsState::default(), &home, &dirs);
        assert_eq!(t.len(), 2, "계정 둘 = 대상 둘(신원 없는 dir은 대상 아님)");
        assert_eq!(t[0].account_id, "uuid-a");
        assert_eq!(t[0].candidates[0], (".claude".to_string(), "Claude Code-credentials".to_string()));
        assert_eq!(t[0].candidates[1].0, ".cys/claude-axdev");
        assert_eq!(t[1].account_id, "uuid-b");
        assert_eq!(t[1].label, "b@x.y");
        let b: Vec<&str> = t[1].candidates.iter().map(|c| c.0.as_str()).collect();
        assert_eq!(b, [".claude-acct2", ".cys/claude"]);
        assert_eq!(t[1].candidates[1].1, keychain_service_for(&home, &home.join(".cys/claude")));
    }

    fn view_of(d: &Arc<Daemon>, uuid: &str) -> Option<AccountView> {
        let st = d.accounts.lock().unwrap();
        st.views.get(&AccountKey { provider: "claude".into(), account_id: uuid.into() }).cloned()
    }

    /// ★뮤턴트 가드: 비기본 계정(B)도 프로브된다 — 대상 열거를 기본 dir만으로 좁히면(종전 동작)
    /// B의 rate·scoped가 비어 이 시험이 적색이 된다.
    #[tokio::test]
    async fn probe_round_fills_both_accounts() {
        let (home, dirs) = two_account_home("probe-both");
        let d = test_daemon();
        let targets = probe_targets(&mut d.accounts.lock().unwrap(), &home, &dirs);
        let svc_b = keychain_service_for(&home, &home.join(".claude-acct2"));
        let fetch = |s: String| {
            let v = if s == svc_b { oauth_fixture_account('b') } else { oauth_fixture_account('a') };
            async move { Ok::<Value, String>(v) }
        };
        let mut bo = ProbeBackoff::new();
        probe_round(&d, &targets, &mut bo, 1000.0, &fetch).await;
        let a = view_of(&d, "uuid-a").expect("계정 A");
        let b = view_of(&d, "uuid-b").expect("계정 B가 프로브돼야 한다");
        assert_eq!(a.rate.iter().map(|w| w.used_pct).collect::<Vec<_>>(), [2.0, 15.0]);
        assert_eq!(b.rate.iter().map(|w| w.used_pct).collect::<Vec<_>>(), [3.0, 43.0]);
        assert_eq!(b.scoped.len(), 1, "계정 B의 7d·Fable 게이지");
        assert_eq!(b.scoped[0].used_pct, 40.0);
        assert_eq!(b.source, "oauth");
    }

    /// 한 계정의 실패는 다른 계정에 번지지 않는다 — 실패한 계정만 백오프하고 값은 건드리지 않는다.
    /// 또 같은 계정 안에서 앞 후보가 낡았으면(401) 다음 후보로 넘어간다.
    #[tokio::test]
    async fn probe_round_isolates_account_failure() {
        let (home, dirs) = two_account_home("probe-isolate");
        let d = test_daemon();
        let targets = probe_targets(&mut d.accounts.lock().unwrap(), &home, &dirs);
        let svc_b1 = keychain_service_for(&home, &home.join(".claude-acct2"));
        let svc_b2 = keychain_service_for(&home, &home.join(".cys/claude"));
        let calls = std::sync::Mutex::new(Vec::<String>::new());
        // A 계정 후보 전부 실패 · B는 첫 후보 401 → 둘째 후보 성공
        let fetch = |s: String| {
            calls.lock().unwrap().push(s.clone());
            let r = if s == svc_b2 {
                Ok(oauth_fixture_account('b'))
            } else if s == svc_b1 {
                Err("HTTP 401".to_string())
            } else {
                Err("security: 종료코드 Some(44)".to_string())
            };
            async move { r }
        };
        let mut bo = ProbeBackoff::new();
        probe_round(&d, &targets, &mut bo, 1000.0, &fetch).await;
        let b = view_of(&d, "uuid-b").expect("B는 A의 실패와 무관하게 채워진다");
        assert_eq!(b.rate.len(), 2);
        assert_eq!(b.scoped.len(), 1);
        assert!(view_of(&d, "uuid-a").map_or(true, |a| a.rate.is_empty() && a.scoped.is_empty()));
        assert_eq!(bo.get("uuid-a").map(|x| x.0), Some(1), "A만 실패 1회");
        assert_eq!(bo.get("uuid-b").map(|x| x.0), Some(0), "B는 성공 — 백오프 없음");
        assert_eq!(calls.lock().unwrap().iter().filter(|s| **s == svc_b1 || **s == svc_b2).count(), 2);
        // 다음 틱(180s 뒤): A는 백오프 중이라 건너뛰고 B만 다시 부른다.
        calls.lock().unwrap().clear();
        probe_round(&d, &targets, &mut bo, 1000.0 + 180.0, &fetch).await;
        let c = calls.lock().unwrap().clone();
        assert!(!c.is_empty() && c.iter().all(|s| *s == svc_b1 || *s == svc_b2), "백오프 중인 A는 부르지 않는다: {c:?}");
        // 그다음 틱(360s): A의 1회 실패 백오프(2배 주기)가 끝나 다시 부른다 — 영구 정지가 아니다.
        calls.lock().unwrap().clear();
        probe_round(&d, &targets, &mut bo, 1000.0 + 360.0, &fetch).await;
        assert!(calls.lock().unwrap().iter().any(|s| s == "Claude Code-credentials"), "A 재시도");
        assert_eq!(bo.get("uuid-a").map(|x| x.0), Some(2));
    }

    /// 429(또는 어떤 실패)는 값을 건드리지 않는다 — 직전 rate·scoped·관측 시각이 그대로 남고
    /// (죽은 값 강등은 읽기 시점 판정 rate_window_stale_reason 몫), 그 계정만 백오프한다.
    #[tokio::test]
    async fn probe_failure_keeps_previous_values_and_backs_off() {
        let (home, dirs) = two_account_home("probe-429");
        let d = test_daemon();
        let targets = probe_targets(&mut d.accounts.lock().unwrap(), &home, &dirs);
        let (rate, scoped) = parse_oauth_usage(&oauth_fixture_account('a'), 1000.0);
        note_oauth(&d, "uuid-a", "a@x.y", &rate, &scoped, 1000.0);
        let before = view_of(&d, "uuid-a").unwrap();
        let fetch = |_s: String| async move { Err::<Value, String>("HTTP 429".to_string()) };
        let mut bo = ProbeBackoff::new();
        probe_round(&d, &targets, &mut bo, 1180.0, &fetch).await;
        let after = view_of(&d, "uuid-a").unwrap();
        assert_eq!(after.updated_at, before.updated_at, "관측 시각 유지(신선한 척도, 지우기도 없음)");
        assert_eq!(
            after.rate.iter().map(|w| w.used_pct).collect::<Vec<_>>(),
            before.rate.iter().map(|w| w.used_pct).collect::<Vec<_>>()
        );
        assert_eq!(after.scoped.len(), 1, "Fable 게이지도 유지");
        assert_eq!(after.source, "oauth");
        // 백오프: 1회 실패 → 180×2^1 − 90 = 270초 뒤까지 대기.
        assert_eq!(bo.get("uuid-a"), Some(&(1, 1180.0 + 270.0)));
    }

    /// 응답에 모델 스코프 창이 없으면 옛 게이지를 지운다(없다 ≠ 죽었다 — 행을 그리지 않게).
    #[test]
    fn note_oauth_clears_scoped_when_server_has_none() {
        let d = test_daemon();
        let (rate, scoped) = parse_oauth_usage(&oauth_fixture_account('b'), 1000.0);
        note_oauth(&d, "uuid-b", "b@x.y", &rate, &scoped, 1000.0);
        assert_eq!(view_of(&d, "uuid-b").unwrap().scoped.len(), 1);
        let mut v = oauth_fixture_account('b');
        let lim = v["limits"].as_array_mut().unwrap();
        lim.retain(|l| l["kind"] != "weekly_scoped");
        let (rate2, scoped2) = parse_oauth_usage(&v, 1200.0);
        assert!(scoped2.is_empty());
        note_oauth(&d, "uuid-b", "b@x.y", &rate2, &scoped2, 1200.0);
        assert!(view_of(&d, "uuid-b").unwrap().scoped.is_empty(), "없는 창의 옛 게이지가 남으면 안 된다");
    }

    #[test]
    fn resolve_agents() {
        let mut st = AccountsState::default();
        // codex는 세션 파일 불요·단일 계정
        let (k, l, _, _) = resolve(&mut st, "codex", "").unwrap();
        assert_eq!((k.provider.as_str(), k.account_id.as_str()), ("codex", "default"));
        assert_eq!(l, "OpenAI Codex");
        // usage-noagy(2026-09-19): gemini/agy/antigravity는 더 이상 계정으로 귀속되지 않는다
        // — 박사님 결정("토큰 사용량 표시 기능에서 agy는 삭제하자. 의미가 없다").
        for agent in ["gemini", "agy", "antigravity"] {
            assert!(
                resolve(&mut st, agent, "").is_none(),
                "{agent} 가 여전히 계정으로 귀속된다 — usage-noagy 회귀"
            );
        }
        // 미지 agent → None
        assert!(resolve(&mut st, "mystery", "").is_none());
        // claude인데 신원 해석 불가 → None(스킵 — 유령 계정 금지)
        assert!(resolve(&mut st, "claude", "/nonexist/projects/x/s.jsonl").is_none());
    }

    // ── usage-noagy(TICKET=usage-noagy 2026-09-19): agy(antigravity) 계정 표 제외 회귀 ──

    /// 테스트 전용 격리 데몬 — schedule.rs test_daemon과 같은 패턴(고유 임시 소켓 dir).
    fn test_daemon() -> Arc<Daemon> {
        static SEQ: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
        let d = std::env::temp_dir().join(format!(
            "cys-acct-daemon-{}-{}-{}",
            std::process::id(),
            crate::state::now_epoch().to_bits(),
            SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
        ));
        let _ = std::fs::create_dir_all(&d);
        Daemon::new(d.join("cysd.sock"))
    }

    /// HOME 환경변수를 건드리는 테스트끼리 직렬화 — handlers.rs ACL_ENV_LOCK과 같은 이유
    /// (병렬 실행 시 서로 다른 테스트가 같은 프로세스 전역 HOME을 밟는다).
    static HOME_ENV_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

    /// ★뮤턴트 1: `~/.antigravity` 디렉터리가 있어도 seed_known은 antigravity 계정을 만들지 않는다
    /// — seed_known의 antigravity 시딩 블록을 되살리면 이 시험이 적색이 된다.
    #[test]
    fn seed_known_ignores_antigravity_dir() {
        let _g = HOME_ENV_LOCK.lock().unwrap();
        let prev_home = std::env::var("HOME").ok();
        let fake_home = tmp("seed-antigravity-dir");
        std::fs::create_dir_all(fake_home.join(".antigravity")).unwrap();
        std::env::set_var("HOME", &fake_home);

        let daemon = test_daemon();
        seed_known(&daemon);

        match prev_home {
            Some(h) => std::env::set_var("HOME", h),
            None => std::env::remove_var("HOME"),
        }

        let st = daemon.accounts.lock().unwrap();
        assert!(
            !st.views.keys().any(|k| k.provider == "antigravity"),
            "~/.antigravity 존재만으로 계정이 등록됐다 — usage-noagy 회귀: {:?}",
            st.views.keys().collect::<Vec<_>>()
        );
    }

    /// 옛 analytics.db(코드 개정 전에 기록된)에 antigravity 스냅샷 행이 남아 있어도,
    /// 부트 복원(seed_known)이 그 행으로 계정을 되살리지 않는다 — 클로드 계정 등 다른 provider
    /// 행은 그대로 복원돼야 한다(필터가 antigravity만 정확히 겨눈다는 것을 함께 확인).
    #[test]
    fn seed_known_drops_antigravity_snapshot_rows() {
        let _g = HOME_ENV_LOCK.lock().unwrap();
        let prev_home = std::env::var("HOME").ok();
        let fake_home = tmp("seed-antigravity-snapshot");
        std::env::set_var("HOME", &fake_home);

        let daemon = test_daemon();
        let now = crate::state::now_epoch();
        {
            let guard = daemon.analytics.lock().unwrap();
            let conn = guard.as_ref().expect("test_daemon 은 analytics.db 를 연다");
            crate::analytics::record_rate_snapshot(
                conn, now, "antigravity", "default", "Antigravity (agy)", "5h", 42.0, None,
            );
            crate::analytics::record_rate_snapshot(
                conn, now, "claude", "snap-u1", "a@b.c", "5h", 10.0, None,
            );
        }
        seed_known(&daemon);

        match prev_home {
            Some(h) => std::env::set_var("HOME", h),
            None => std::env::remove_var("HOME"),
        }

        let st = daemon.accounts.lock().unwrap();
        assert!(
            !st.views.keys().any(|k| k.provider == "antigravity"),
            "옛 analytics.db 의 antigravity 스냅샷 행이 부트 복원에서 되살아났다"
        );
        assert!(
            st.views.keys().any(|k| k.provider == "claude" && k.account_id == "snap-u1"),
            "필터가 antigravity 아닌 행까지 지웠다 — claude 스냅샷 복원 실패"
        );
    }

    /// note_rate("gemini", …)는 resolve()가 None을 내므로 호출이 남아 있어도 계정 표에 반영 0이다
    /// — usage.rs의 update_agy_usage 호출부는 그대로 두되 no-op임을 여기서 못박는다
    /// (HANDOFF-usage-noagy.md "호출 유지·no-op" 결정의 회귀 시험).
    #[test]
    fn note_rate_gemini_is_noop() {
        let daemon = test_daemon();
        let rate = vec![RateWindow { label: "5h".into(), used_pct: 50.0, resets_at: None }];
        note_rate(&daemon, "gemini", "", &rate, "agy-rpc", crate::state::now_epoch());
        let st = daemon.accounts.lock().unwrap();
        assert!(st.views.is_empty(), "gemini note_rate 가 계정을 만들었다 — usage-noagy 회귀");
    }

    // ── rate 창 stale 판정 (TICKET=cys-usage-stale-rate) ──
    // 실측값(2026-09-15 08:5x `cys usage-accounts --json` antigravity 행 · 프로세스 0):
    //   updated_at 1789172019.27(09-12 09:13 KST) · 5h resets_at 1789182252(09-12 12:04) used_pct 6.13813
    //   · 7d resets_at 1789689571(09-18) · stale_secs 257276 → 조회 시각 ≈ 1789429295.
    const AGY_OBS: f64 = 1789172019.271695;
    const AGY_5H_RESET: f64 = 1789182252.0;
    const AGY_7D_RESET: f64 = 1789689571.0;
    const AGY_NOW: f64 = 1789429295.0;

    #[test]
    fn rate_window_fresh_is_not_stale() {
        let now = 1_000_000.0;
        // 관측 1분 전 · 리셋은 미래 → 신선
        assert_eq!(rate_window_stale_reason(Some(now + 3600.0), now - 60.0, now), None);
        // resets_at 미상이어도 관측이 신선하면 신선
        assert_eq!(rate_window_stale_reason(None, now - 3600.0, now), None);
        // 경계: 리셋 시각 그 순간·정확히 24h 경과는 아직 신선(엄격 부등호)
        assert_eq!(rate_window_stale_reason(Some(now), now - 60.0, now), None);
        assert_eq!(rate_window_stale_reason(None, now - RATE_STALE_NO_OBS_SECS, now), None);
        // JSON: 신선 창도 stale 필드를 명시적으로 들고 나간다(false·null) — 필드 부재(옛 데몬)와 구별
        let w = RateWindow { label: "5h".into(), used_pct: 41.0, resets_at: Some(now + 3600.0) };
        let j = rate_window_json(&w, now - 60.0, now);
        assert_eq!(j["stale"], json!(false));
        assert!(j.get("stale_reason").is_some_and(|x| x.is_null()), "키는 있고 값은 null");
        assert_eq!(j["used_pct"], json!(41.0));
    }

    #[test]
    fn rate_window_resets_at_passed() {
        // 실측 agy 5h 창: 리셋(09-12 12:04)이 지났다 — 24h 무관측도 참이지만 사유는 리셋이 우선
        assert_eq!(
            rate_window_stale_reason(Some(AGY_5H_RESET), AGY_OBS, AGY_NOW),
            Some("resets_at_passed")
        );
        // 관측이 방금이어도 리셋이 지났으면 죽은 값 — 나이와 무관
        assert_eq!(
            rate_window_stale_reason(Some(AGY_NOW - 1.0), AGY_NOW - 5.0, AGY_NOW),
            Some("resets_at_passed")
        );
        // ★계약: used_pct·resets_at은 숫자 그대로 — null로 바꾸지 않는다(소비자 숫자 계약)
        let w = RateWindow {
            label: "5h".into(),
            used_pct: 6.138129999999997,
            resets_at: Some(AGY_5H_RESET),
        };
        let j = rate_window_json(&w, AGY_OBS, AGY_NOW);
        assert_eq!(j["label"], json!("5h"));
        assert_eq!(j["used_pct"].as_f64(), Some(6.138129999999997));
        assert_eq!(j["resets_at"].as_f64(), Some(AGY_5H_RESET));
        assert_eq!(j["stale"], json!(true));
        assert_eq!(j["stale_reason"], json!("resets_at_passed"));
    }

    #[test]
    fn rate_window_no_observation_24h() {
        // 실측 agy 7d 창: 리셋은 미래(09-18)지만 관측이 71h 전 → 무관측 사유
        assert_eq!(
            rate_window_stale_reason(Some(AGY_7D_RESET), AGY_OBS, AGY_NOW),
            Some("no_observation_24h")
        );
        let now = 1_000_000.0;
        // 24h + 1초
        assert_eq!(
            rate_window_stale_reason(None, now - RATE_STALE_NO_OBS_SECS - 1.0, now),
            Some("no_observation_24h")
        );
        // 관측 전(0.0) — 나이를 셀 수 없으면 신선이라 주장하지 않는다
        assert_eq!(rate_window_stale_reason(Some(now + 60.0), 0.0, now), Some("no_observation_24h"));
    }
}
