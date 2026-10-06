//! 기준선 B0 · 사후 검증 V1~V9(설계 AUTO-UPDATE-118 §3-9 · BLOCK 10·13 · MA5·MA12 · D22 정정 반영).
//!
//! - B0 는 **S5b**(정비 장벽 안 · drain·재검사 뒤 · 데몬 정지 전)에 찍는다 — S2~S5 사이 사용자 변경이 V3/V5 실패로 오인되지 않는다.
//! - 판정은 순수 함수([`judge`]) — 사실 수집(데몬 RPC·`cys doctor`·파일 해시)은 러너의 실행층이 한다.
//! - V1~V7·V9 하나라도 실패 = 롤백(§3-10) · V8 = 기록만.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

/// 좌석 키(MA5 — 같은 수·다른 좌석 = 실패).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct SeatKey {
    pub surface_uuid: String,
    pub role: String,
    pub dept: String,
    pub session_id: String,
}

/// 사용자 소유 트리 — 바이트 동일 대조분 + 의미 대조분(schedule·acl · `MergeUser`).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct UserTree {
    /// `~/.cys` 기준 상대 경로 → sha256(`local/**`·지침·soul·CLAUDE).
    pub bytes: BTreeMap<String, String>,
    /// 파일(상대 경로) → 사용자 잡 id → 잡 본문.
    pub schedule_jobs: BTreeMap<String, BTreeMap<String, Value>>,
    /// 파일 → `rules`.
    pub acl_rules: BTreeMap<String, Value>,
    /// 파일 → 에이전트 이름 → `cmd`(모델 핀).
    pub agents_cmd: BTreeMap<String, BTreeMap<String, String>>,
}

/// 팩 판.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct PackId {
    pub version: String,
    pub digest: String,
}

/// 기준선 B0(저널 옆 `attempt.json` 에 함께 적는다).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Baseline {
    pub seats: BTreeSet<SeatKey>,
    pub doctor_fail: BTreeSet<String>,
    pub user: UserTree,
    pub features: BTreeSet<String>,
    pub hold_seq: u64,
    pub pack: PackId,
    /// ★2판(codex 1R C9): 옛 판 기판 표지 실측(맥 CDHash · 윈 설치 cys.exe sha256) — 롤백 V1 의 기대값.
    #[serde(default)]
    pub platform_mark: String,
}

/// 갱신(또는 롤백) 뒤 사실.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Post {
    /// 설치본 `cys build-info --json` 의 `{release_seq, build_id, target}`.
    pub release_seq: u64,
    pub build_id: String,
    pub target: String,
    /// 데몬 `system.identify` 의 build_id.
    pub daemon_build_id: String,
    /// (맥) 설치 번들 CDHash · (윈) VERSIONINFO 판 — 본문 값과 같아야 하는 「기판 표지」(없으면 빈 값 = 대조 생략 아님 → 기대도 빈 값일 때만 통과).
    pub platform_mark: String,
    pub ping_ok_streak: u32,
    pub cysd_procs: u32,
    pub seats: BTreeSet<SeatKey>,
    pub drain_seats: Option<BTreeSet<SeatKey>>,
    pub restore_rc: i32,
    pub doctor_fail: BTreeSet<String>,
    pub user: UserTree,
    pub forbidden_jobs: Vec<String>,
    pub features: BTreeSet<String>,
    pub merge_pending_new: Vec<String>,
    pub pack: PackId,
    pub hold_last_seq: u64,
    pub hold_delivered_seq: u64,
    /// 보류 로그에서 사라진 줄(재독 대조 · 0 이어야 함).
    pub hold_lost: u64,
}

/// 기대값(릴리스 본문 그 기판 행 · 롤백이면 옛 판 기록).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Expect {
    pub release_seq: u64,
    pub build_id: String,
    pub target: String,
    pub platform_mark: String,
    pub bundled_pack: PackId,
    /// 수용 기록상 이미 깔려 있던 더 새 독립 팩(MA12).
    pub newer_independent_pack: Option<PackId>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Check {
    pub id: &'static str,
    pub ok: bool,
    pub detail: String,
}

/// 정책 §6-7 금지 내장 잡.
pub const FORBIDDEN_JOBS: &[&str] = &["formation-ensure-10min"];

fn v5(b: &UserTree, p: &UserTree) -> Result<(), String> {
    for (k, h) in &b.bytes {
        match p.bytes.get(k) {
            Some(h2) if h2 == h => {}
            Some(_) => return Err(format!("{k} 바뀜")),
            None => return Err(format!("{k} 사라짐")),
        }
    }
    for (f, jobs) in &b.schedule_jobs {
        let after = p.schedule_jobs.get(f).ok_or(format!("{f} 사라짐"))?;
        for (id, body) in jobs {
            match after.get(id) {
                // 사용자 잡 본문 ⊆ 갱신 뒤(벤더가 칸을 더한 것은 허용 · 사용자 칸 값 변경 = 실패)
                Some(v) if subset(body, v) => {}
                Some(_) => return Err(format!("{f} 잡 {id} 바뀜")),
                None => return Err(format!("{f} 잡 {id} 사라짐")),
            }
        }
    }
    for (f, r) in &b.acl_rules {
        if p.acl_rules.get(f) != Some(r) {
            return Err(format!("{f} rules 바뀜"));
        }
    }
    for (f, m) in &b.agents_cmd {
        let after = p.agents_cmd.get(f).ok_or(format!("{f} 사라짐"))?;
        for (name, cmd) in m {
            if after.get(name) != Some(cmd) {
                return Err(format!("{f} {name} cmd 바뀜"));
            }
        }
    }
    Ok(())
}

/// `a` 의 모든 칸이 `b` 에 같은 값으로 있다(객체는 재귀 · 그 밖은 같음).
pub fn subset(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Object(x), Value::Object(y)) => x.iter().all(|(k, v)| y.get(k).map(|w| subset(v, w)).unwrap_or(false)),
        _ => a == b,
    }
}

/// V1~V9 판정. `rollback` = 옛 판 기준 재검사(RB_VERIFIED) — 그때는 V9 를 기준선 팩과 대조한다.
pub fn judge(b0: &Baseline, post: &Post, exp: &Expect, rollback: bool) -> Vec<Check> {
    let mut out = Vec::new();
    let mut push = |id: &'static str, r: Result<(), String>| {
        let ok = r.is_ok();
        out.push(Check { id, ok, detail: r.err().unwrap_or_default() });
    };
    push(
        "V1",
        if post.release_seq == exp.release_seq
            && post.build_id == exp.build_id
            && post.target == exp.target
            && post.daemon_build_id == exp.build_id
            && post.platform_mark == exp.platform_mark
        {
            Ok(())
        } else {
            Err(format!(
                "build-info {}/{}/{} 데몬 {} 표지 {} ≠ 기대 {}/{}/{} 표지 {}",
                post.release_seq, post.build_id, post.target, post.daemon_build_id, post.platform_mark, exp.release_seq, exp.build_id, exp.target, exp.platform_mark
            ))
        },
    );
    push("V2", if post.ping_ok_streak >= 3 && post.cysd_procs == 1 { Ok(()) } else { Err(format!("ping {} · cysd {}개", post.ping_ok_streak, post.cysd_procs)) });
    let seats_ok = post.seats == b0.seats && post.drain_seats.as_ref().map(|d| d == &b0.seats).unwrap_or(true) && post.restore_rc == 0;
    let hold_ok = post.hold_lost == 0 && post.hold_delivered_seq <= post.hold_last_seq && post.hold_last_seq >= b0.hold_seq;
    push(
        "V3",
        if seats_ok && hold_ok && !super::mutant("U2-V3") {
            Ok(())
        } else {
            let missing: Vec<_> = b0.seats.difference(&post.seats).map(|s| s.surface_uuid.clone()).collect();
            let extra: Vec<_> = post.seats.difference(&b0.seats).map(|s| s.surface_uuid.clone()).collect();
            Err(format!("좌석 누락 {missing:?} 추가 {extra:?} restore rc {} · 보류 사라짐 {}", post.restore_rc, post.hold_lost))
        },
    );
    let new_fail: Vec<_> = post.doctor_fail.difference(&b0.doctor_fail).cloned().collect();
    push("V4", if new_fail.is_empty() { Ok(()) } else { Err(format!("새 FAIL {new_fail:?}")) });
    push("V5", v5(&b0.user, &post.user));
    push("V6", if post.forbidden_jobs.is_empty() { Ok(()) } else { Err(format!("금지 잡 {:?}", post.forbidden_jobs)) });
    let lost: Vec<_> = b0.features.difference(&post.features).cloned().collect();
    push("V7", if lost.is_empty() { Ok(()) } else { Err(format!("기능 누락 {lost:?}")) });
    out.push(Check { id: "V8", ok: true, detail: if post.merge_pending_new.is_empty() { String::new() } else { format!("병합 대기 새 항목 {:?}(기록만)", post.merge_pending_new) } });
    let pack_ok = if rollback {
        post.pack == b0.pack
    } else {
        post.pack == exp.bundled_pack || exp.newer_independent_pack.as_ref() == Some(&post.pack)
    };
    out.push(Check { id: "V9", ok: pack_ok, detail: if pack_ok { String::new() } else { format!("팩 {:?}", post.pack) } });
    out
}

pub fn passed(checks: &[Check]) -> bool {
    checks.iter().all(|c| c.ok || c.id == "V8")
}

// ── 사용자 소유 트리 수집(§3-5 표 「사용자 소유 트리」 · B0·V5 재료) ─────────────────────────

const BYTE_NAMES: &[&str] = &["soul.md", "CLAUDE.md"];

/// `cys_root`(= `~/.cys`) 아래 사용자 소유 트리를 읽는다: `local/**` · 본부 `pack` + 모든 `pack-dept-*` 의 지침 `*_DIRECTIVE.md`·
/// `soul.md`·`CLAUDE.md`(바이트) · `schedule.json`·`acl.json`·`agents.json`(의미).
pub fn collect_user_tree(cys_root: &Path) -> Result<UserTree, String> {
    let mut t = UserTree::default();
    let local = cys_root.join("local");
    for rel in super::snapshot::list_files(&local, &|_| true)? {
        t.bytes.insert(format!("local/{rel}"), super::snapshot::sha256_file(&local.join(&rel))?.0);
    }
    let mut packs = vec!["pack".to_string()];
    if let Ok(rd) = std::fs::read_dir(cys_root) {
        let mut v: Vec<String> = rd.filter_map(|e| e.ok()).map(|e| e.file_name().to_string_lossy().to_string()).filter(|n| n.starts_with("pack-dept-")).collect();
        v.sort();
        packs.extend(v);
    }
    for p in packs {
        let root = cys_root.join(&p);
        if !root.is_dir() {
            continue;
        }
        for rel in super::snapshot::list_files(&root, &|_| true)? {
            let name = rel.rsplit('/').next().unwrap_or_default();
            let key = format!("{p}/{rel}");
            let full = root.join(&rel);
            if name.ends_with("_DIRECTIVE.md") || BYTE_NAMES.contains(&name) {
                t.bytes.insert(key, super::snapshot::sha256_file(&full)?.0);
            } else if rel == "schedule.json" || rel == "acl.json" || rel == "agents.json" {
                let v: Value = serde_json::from_slice(&std::fs::read(&full).map_err(|e| e.to_string())?).map_err(|e| format!("{key}: {e}"))?;
                match rel.as_str() {
                    "schedule.json" => {
                        let jobs = v.get("jobs").and_then(Value::as_array).cloned().unwrap_or_default();
                        let m = jobs
                            .into_iter()
                            .filter(|j| j.get("_builtin_version").is_none()) // 벤더 내장 잡은 사용자 잡이 아니다
                            .filter_map(|j| j.get("id").and_then(Value::as_str).map(|id| (id.to_string(), j.clone())))
                            .collect();
                        t.schedule_jobs.insert(key, m);
                    }
                    "acl.json" => {
                        t.acl_rules.insert(key, v.get("rules").cloned().unwrap_or(Value::Null));
                    }
                    _ => {
                        let mut m = BTreeMap::new();
                        if let Some(o) = v.get("agents").and_then(Value::as_object).or_else(|| v.as_object()) {
                            for (name, a) in o {
                                if let Some(c) = a.get("cmd").and_then(Value::as_str) {
                                    m.insert(name.clone(), c.to_string());
                                }
                            }
                        }
                        t.agents_cmd.insert(key, m);
                    }
                }
            }
        }
    }
    Ok(t)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn seat(u: &str) -> SeatKey {
        SeatKey { surface_uuid: u.into(), role: "worker".into(), dept: "hq".into(), session_id: format!("s-{u}") }
    }

    fn fixture() -> (Baseline, Post, Expect) {
        let mut b = Baseline::default();
        b.seats = [seat("a"), seat("b")].into();
        b.doctor_fail = ["runtime-seal".to_string()].into();
        b.user.bytes.insert("local/x.md".into(), "h1".into());
        b.user.schedule_jobs.insert("pack/schedule.json".into(), [("mine".to_string(), json!({"id":"mine","every_minutes":60}))].into());
        b.user.acl_rules.insert("pack/acl.json".into(), json!([1]));
        b.user.agents_cmd.insert("pack/agents.json".into(), [("claude".to_string(), "claude --model opus".to_string())].into());
        b.features = ["sidebar-usage".to_string()].into();
        b.hold_seq = 3;
        b.pack = PackId { version: "1.1.7".into(), digest: "d7".into() };
        let e = Expect { release_seq: 9, build_id: "B".into(), target: "darwin-aarch64".into(), platform_mark: "cd".into(), bundled_pack: PackId { version: "1.1.8".into(), digest: "d8".into() }, newer_independent_pack: None };
        let p = Post {
            release_seq: 9,
            build_id: "B".into(),
            target: "darwin-aarch64".into(),
            daemon_build_id: "B".into(),
            platform_mark: "cd".into(),
            ping_ok_streak: 3,
            cysd_procs: 1,
            seats: b.seats.clone(),
            drain_seats: Some(b.seats.clone()),
            restore_rc: 0,
            doctor_fail: b.doctor_fail.clone(),
            user: {
                let mut u = b.user.clone();
                u.schedule_jobs.get_mut("pack/schedule.json").unwrap().insert("vendor-new".into(), json!({"id":"vendor-new"}));
                u.schedule_jobs.get_mut("pack/schedule.json").unwrap().get_mut("mine").unwrap()["bulk"] = json!(true);
                u
            },
            forbidden_jobs: vec![],
            features: ["sidebar-usage".to_string(), "new".to_string()].into(),
            merge_pending_new: vec!["x.new".into()],
            pack: e.bundled_pack.clone(),
            hold_last_seq: 5,
            hold_delivered_seq: 5,
            hold_lost: 0,
        };
        (b, p, e)
    }

    fn failed(c: &[Check]) -> Vec<&'static str> {
        c.iter().filter(|c| !c.ok).map(|c| c.id).collect()
    }

    #[test]
    fn happy_path_passes_and_v8_is_record_only_and_vendor_additions_pass() {
        let (b, p, e) = fixture();
        let c = judge(&b, &p, &e, false);
        assert!(passed(&c), "{c:?}");
        assert!(!c.iter().find(|c| c.id == "V8").unwrap().detail.is_empty());
    }

    /// §7-1 사후 검증 시험 행(V3 같은 수·다른 좌석 · V5 job 소실 · cmd 변경 · local 1바이트 · V7 누락 · V9 더 새 독립 팩).
    #[test]
    fn each_violation_fails_its_row() {
        let (b, p, e) = fixture();
        let mut q = p.clone();
        q.seats = [seat("a"), seat("c")].into(); // 같은 수 · 다른 좌석
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V3"]);
        let mut q = p.clone();
        q.hold_lost = 1;
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V3"]);
        let mut q = p.clone();
        q.user.schedule_jobs.get_mut("pack/schedule.json").unwrap().remove("mine");
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V5"]);
        let mut q = p.clone();
        q.user.agents_cmd.get_mut("pack/agents.json").unwrap().insert("claude".into(), "claude --model haiku".into());
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V5"]);
        let mut q = p.clone();
        q.user.bytes.insert("local/x.md".into(), "h2".into());
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V5"]);
        let mut q = p.clone();
        q.features.remove("sidebar-usage");
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V7"]);
        let mut q = p.clone();
        q.doctor_fail.insert("new-fail".into());
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V4"]);
        let mut q = p.clone();
        q.forbidden_jobs = vec!["formation-ensure-10min".into()];
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V6"]);
        let mut q = p.clone();
        q.daemon_build_id = "A".into();
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V1"]);
        let mut q = p.clone();
        q.cysd_procs = 2;
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V2"]);
        // V9 더 새 독립 팩 = 통과(MA12) · 그 밖 팩 = 실패
        let mut q = p.clone();
        q.pack = PackId { version: "1.1.9".into(), digest: "d9".into() };
        assert_eq!(failed(&judge(&b, &q, &e, false)), vec!["V9"]);
        let mut e2 = e.clone();
        e2.newer_independent_pack = Some(q.pack.clone());
        assert!(passed(&judge(&b, &q, &e2, false)));
        // 롤백 재검사 = 기준선 팩
        let mut q = p.clone();
        q.pack = b.pack.clone();
        assert!(passed(&judge(&b, &q, &e, true)));
    }

    #[test]
    fn user_tree_collects_bytes_and_semantic_rows() {
        let d = std::env::temp_dir().join(format!("cys-u2-ut-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        for (p, b) in [
            ("local/a.md", "A"),
            ("pack/directives/WORKER_DIRECTIVE.md", "W"),
            ("pack/soul.md", "S"),
            ("pack/schedule.json", r#"{"jobs":[{"id":"mine","every_minutes":5},{"id":"b","_builtin_version":4}]}"#),
            ("pack/acl.json", r#"{"rules":[{"x":1}]}"#),
            ("pack/agents.json", r#"{"agents":{"claude":{"cmd":"claude --model opus"}}}"#),
            ("pack-dept-edu/CLAUDE.md", "C"),
            ("pack/other.txt", "ignored"),
        ] {
            let f = d.join(p);
            std::fs::create_dir_all(f.parent().unwrap()).unwrap();
            std::fs::write(f, b).unwrap();
        }
        let t = collect_user_tree(&d).unwrap();
        assert_eq!(t.bytes.keys().cloned().collect::<Vec<_>>(), vec!["local/a.md", "pack-dept-edu/CLAUDE.md", "pack/directives/WORKER_DIRECTIVE.md", "pack/soul.md"]);
        assert_eq!(t.schedule_jobs["pack/schedule.json"].keys().cloned().collect::<Vec<_>>(), vec!["mine"]);
        assert_eq!(t.agents_cmd["pack/agents.json"]["claude"], "claude --model opus");
        assert_eq!(t.acl_rules["pack/acl.json"], json!([{"x":1}]));
    }
}
