//! `schedule.json` 의 `bulk`·`publish` **필수 칸**(설계 AUTO-UPDATE-118 §3-4 · 📌14′ · 📌16 · 3R MAJOR 4).
//!
//! - **스키마**: 잡 적재 때 두 칸이 bool 로 있어야 한다 — 없으면 적재 거부 + 왕초보 말투 문구([`MISSING_FIELDS_MSG`]).
//! - **판정**: 칸이 없거나 판독 불가인 잡 = `true` 로 본다(표식 누락 = 보류 쪽 · fail-closed).
//! - **이행**(1.1.8 첫 기동 · 1회 · 순서 고정 ①~⑤): ① 원시 JSON 읽기(새 스키마 검증 없이) ② 원본 백업 `.bak-118`
//!   (이미 있으면 덮지 않음) ③ 두 칸이 없거나 판독 불가인 잡에 `true` 를 써 넣음(이미 bool 이면 건드리지 않음) ④ 임시 파일
//!   → fsync → rename 원자 저장(이행 표지 `schedule_migration_118: "done"` 을 같은 쓰기에) ⑤ **그다음에** 새 스키마로 검증.
//!   ①~⑤ 가 끊기면 다음 기동이 ①부터 다시 한다(멱등).
//!
//! ⚠ U1 은 함수와 시험만 둔다. 실 사용자 `schedule.json` 에 이행을 쓰는 배선(cysd 기동·`cys schedule add`·내장 잡 두 칸 명시)은
//!   1.1.8 발행과 함께 가는 비가역 항목(설계 §8 비가역 ⑦)이라 이 티켓에서 연결하지 않는다 — 시험은 임시 폴더에서만 쓴다.

use serde_json::Value;
use std::path::{Path, PathBuf};

/// 적재 거부 문구(설계 §3-4 원문).
pub const MISSING_FIELDS_MSG: &str = "이 일이 한꺼번에 많은 일을 하거나(대량), 바깥으로 무언가를 내보내는(발행) 일인지 적어 주세요 — `bulk: true/false`, `publish: true/false`";
/// 이행 표지 키.
pub const MIGRATION_MARK_KEY: &str = "schedule_migration_118";
pub const MIGRATION_MARK_DONE: &str = "done";
/// 백업 접미.
pub const BACKUP_SUFFIX: &str = ".bak-118";

/// 잡 1개의 두 칸(판정용 — 없음·판독 불가 = true).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct JobFlags {
    pub bulk: bool,
    pub publish: bool,
}

pub fn job_flags(job: &Value) -> JobFlags {
    let f = |k: &str| job.get(k).and_then(|v| v.as_bool()).unwrap_or(true);
    JobFlags { bulk: f("bulk"), publish: f("publish") }
}

/// 새 스키마 검증(적재 게이트) — 두 칸이 bool 로 있어야 한다.
pub fn validate_job(job: &Value) -> Result<(), String> {
    let ok = |k: &str| job.get(k).map(|v| v.is_boolean()).unwrap_or(false);
    if ok("bulk") && ok("publish") {
        Ok(())
    } else {
        let id = job.get("id").and_then(|v| v.as_str()).unwrap_or("?");
        Err(format!("[{id}] {MISSING_FIELDS_MSG}"))
    }
}

/// ★1R MAJOR(M1): 구조 계약 — 뿌리 = 객체 · `jobs` = 배열 · 모든 잡 = 객체. 어긋나면 Err(이행 쓰기 0 · 사실 = 판정 불가).
pub fn check_structure(root: &Value) -> Result<(), String> {
    if super::mutant("M1") {
        return Ok(());
    }
    let jobs = root
        .as_object()
        .ok_or("뿌리가 객체가 아님")?
        .get("jobs")
        .ok_or("jobs 칸 없음")?
        .as_array()
        .ok_or("jobs 가 배열이 아님")?;
    if let Some(i) = jobs.iter().position(|j| !j.is_object()) {
        return Err(format!("jobs[{i}] 가 객체가 아님"));
    }
    Ok(())
}

/// 이행 결과.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct MigrationReport {
    /// 이번에 칸을 써 넣은 잡 id(daily 우편 「bulk 이행 잡 N건」 재료).
    pub migrated_ids: Vec<String>,
    /// 파일을 다시 썼는가(이미 이행됐으면 false).
    pub wrote: bool,
    /// 백업을 이번에 만들었는가.
    pub backup_created: bool,
}

pub fn backup_path(path: &Path) -> PathBuf {
    let mut s = path.as_os_str().to_os_string();
    s.push(BACKUP_SUFFIX);
    PathBuf::from(s)
}

/// 이행 ①~⑤ — 파일이 없으면 아무것도 안 한다(Ok · 빈 보고).
pub fn migrate_schedule_file(path: &Path) -> Result<MigrationReport, String> {
    // ① 원시 JSON 읽기(새 스키마 검증 없이).
    let raw = match std::fs::read(path) {
        Ok(b) => b,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(MigrationReport::default()),
        Err(e) => return Err(format!("① 읽기 {}: {e}", path.display())),
    };
    let mut root: Value = serde_json::from_slice(&raw).map_err(|e| format!("① 파싱 {}: {e}", path.display()))?;
    check_structure(&root).map_err(|e| format!("① 구조 {}: {e}", path.display()))?;
    let mut rep = MigrationReport::default();
    // ② 원본 백업(이미 있으면 덮지 않음 — 첫 원본이 정본).
    let bak = backup_path(path);
    if !bak.exists() {
        crate::pack::write_atomic(&bak, &raw).map_err(|e| format!("② 백업 {}: {e}", bak.display()))?;
        rep.backup_created = true;
    }
    // ③ 칸 이행(없음·판독 불가 = true · 이미 bool 은 그대로).
    let mut changed = false;
    if let Some(jobs) = root.get_mut("jobs").and_then(|j| j.as_array_mut()) {
        for job in jobs.iter_mut() {
            let Some(obj) = job.as_object_mut() else { continue };
            let mut touched = false;
            for k in ["bulk", "publish"] {
                if !obj.get(k).map(|v| v.is_boolean()).unwrap_or(false) {
                    obj.insert(k.to_string(), Value::Bool(true));
                    touched = true;
                }
            }
            if touched {
                changed = true;
                rep.migrated_ids.push(obj.get("id").and_then(|v| v.as_str()).unwrap_or("?").to_string());
            }
        }
    }
    let marked = root.get(MIGRATION_MARK_KEY).and_then(|v| v.as_str()) == Some(MIGRATION_MARK_DONE);
    if changed || !marked {
        if let Some(o) = root.as_object_mut() {
            o.insert(MIGRATION_MARK_KEY.to_string(), Value::String(MIGRATION_MARK_DONE.to_string()));
        }
        // ④ 원자 저장(tmp → fsync → rename → 부모 fsync · pack::write_atomic).
        let bytes = serde_json::to_vec_pretty(&root).map_err(|e| e.to_string())?;
        crate::pack::write_atomic(path, &bytes).map_err(|e| format!("④ 저장 {}: {e}", path.display()))?;
        rep.wrote = true;
    }
    // ⑤ 그다음에 새 스키마 검증(이행 뒤 남은 위반 = 0 이어야 정상).
    if let Some(jobs) = root.get("jobs").and_then(|j| j.as_array()) {
        for job in jobs {
            if job.is_object() {
                validate_job(job).map_err(|e| format!("⑤ {e}"))?;
            }
        }
    }
    Ok(rep)
}

// ── 다음 발화 판정(N4·N5 ⓒ) ──────────────────────────────────────────────────────────────

/// 잡이 `[now, now + horizon]` 안에 발화할 수 있는가 — **보수**: 판독 불가 = 발화한다(true).
/// `now_local` = 지역 시각(잡의 `time`·`days` 는 지역 시각 기준 — cysd 스케줄러와 같음).
pub fn may_fire_within(job: &Value, now_local: chrono::DateTime<chrono::Local>, horizon_secs: i64) -> bool {
    use chrono::{Datelike, Duration, TimeZone};
    let now_epoch = now_local.timestamp();
    if let Some(at) = job.get("at") {
        return match at.as_i64() {
            Some(t) => t >= now_epoch && t <= now_epoch + horizon_secs,
            None => !at.is_null(),
        };
    }
    // 주기 잡 = 창 안에 돈다고 본다(보수 — 다음 회차 시각은 스케줄러 상태에 있고, 주기가 창보다 길어도 곧 돌 수 있다).
    if job.get("every_minutes").map(|m| !m.is_null()).unwrap_or(false) {
        return true;
    }
    let Some(t) = job.get("time").and_then(|v| v.as_str()) else {
        return true; // 언제 도는지 모름 = 돈다
    };
    let Ok(hm) = chrono::NaiveTime::parse_from_str(t.trim(), "%H:%M") else {
        return true;
    };
    let days: Vec<String> = job
        .get("days")
        .and_then(|v| v.as_array())
        .map(|a| a.iter().filter_map(|d| d.as_str().map(|s| s.to_ascii_lowercase())).collect())
        .unwrap_or_default();
    let day_ok = |wd: chrono::Weekday| {
        if days.is_empty() {
            return true;
        }
        let name = format!("{wd:?}").to_ascii_lowercase(); // mon tue …
        days.iter().any(|d| d.starts_with(&name[..3]) || d == &name)
    };
    // 오늘부터 horizon 이 걸치는 날까지 후보 시각을 훑는다.
    let span_days = horizon_secs / 86_400 + 2;
    for off in 0..=span_days {
        let date = now_local.date_naive() + Duration::days(off);
        if !day_ok(date.weekday()) {
            continue;
        }
        let Some(cand) = chrono::Local.from_local_datetime(&date.and_time(hm)).earliest() else {
            return true; // 지역 시각 공백(서머타임) = 모름 = 돈다
        };
        let ts = cand.timestamp();
        if ts >= now_epoch && ts <= now_epoch + horizon_secs {
            return true;
        }
    }
    false
}

/// N4·N5 ⓒ 사실 묶음 — 여러 `schedule.json`(본부·부서)을 훑는다. 파일 판독 불가 = None(판정 불가 = 보류).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct ScheduleFacts {
    /// `bulk:true`(없음 포함) 잡의 다음 발화가 48시간 안.
    pub bulk_within_48h: bool,
    /// `bulk:false` 잡의 다음 발화가 60분 안.
    pub nonbulk_within_60m: bool,
    /// `publish:true`(없음 포함) 잡의 다음 발화가 48시간 안.
    pub publish_within_48h: bool,
    /// 칸 없는 잡 수(이행 대상 · daily 칸).
    pub unflagged_jobs: usize,
}

pub fn schedule_facts(files: &[PathBuf], now_local: chrono::DateTime<chrono::Local>) -> Option<ScheduleFacts> {
    let mut f = ScheduleFacts::default();
    for p in files {
        let raw = match std::fs::read(p) {
            Ok(b) => b,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => continue,
            Err(_) => return None,
        };
        let root: Value = serde_json::from_slice(&raw).ok()?;
        check_structure(&root).ok()?;
        let Some(jobs) = root.get("jobs").and_then(|j| j.as_array()) else { return None };
        for job in jobs {
            if validate_job(job).is_err() {
                f.unflagged_jobs += 1;
            }
            let flags = job_flags(job);
            if flags.bulk && may_fire_within(job, now_local, 48 * 3600) {
                f.bulk_within_48h = true;
            }
            if !flags.bulk && may_fire_within(job, now_local, 3600) {
                f.nonbulk_within_60m = true;
            }
            if flags.publish && may_fire_within(job, now_local, 48 * 3600) {
                f.publish_within_48h = true;
            }
        }
    }
    Some(f)
}

/// 본부·부서 `schedule.json` 경로 목록 — 본부 = 팩 폴더 · 부서 = `<팩 폴더 부모>/pack-dept-*/schedule.json`.
pub fn schedule_files(pack_dir: &Path) -> Vec<PathBuf> {
    let mut out = vec![pack_dir.join("schedule.json")];
    if let Some(parent) = pack_dir.parent() {
        if let Ok(rd) = std::fs::read_dir(parent) {
            let mut v: Vec<PathBuf> = rd
                .flatten()
                .filter(|e| e.file_name().to_string_lossy().starts_with("pack-dept-") && e.path().is_dir())
                .map(|e| e.path().join("schedule.json"))
                .collect();
            v.sort();
            out.extend(v);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::TimeZone;
    use serde_json::json;

    fn tmpdir(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("cys-u1-sched-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn flags_missing_or_unreadable_are_true() {
        assert_eq!(job_flags(&json!({"id": "a"})), JobFlags { bulk: true, publish: true });
        assert_eq!(job_flags(&json!({"bulk": "no", "publish": 0})), JobFlags { bulk: true, publish: true });
        assert_eq!(job_flags(&json!({"bulk": false, "publish": false})), JobFlags { bulk: false, publish: false });
    }

    #[test]
    fn load_validation_rejects_missing_with_plain_message() {
        let e = validate_job(&json!({"id": "x", "bulk": false})).unwrap_err();
        assert!(e.contains("[x]") && e.contains("bulk: true/false") && e.contains("publish: true/false"));
        assert!(validate_job(&json!({"id": "x", "bulk": false, "publish": true})).is_ok());
        assert!(validate_job(&json!({"id": "x", "bulk": "false", "publish": true})).is_err());
    }

    /// 이행 ①~⑤ 순서·백업·멱등·이미 있는 칸 보존(시험 폴더에서만 쓴다).
    #[test]
    fn migration_order_backup_idempotent_and_preserves_existing() {
        let d = tmpdir("mig");
        let p = d.join("schedule.json");
        let orig = json!({"jobs": [
            {"id": "owner-daily", "time": "20:00", "action": "push"},
            {"id": "vendor", "every_minutes": 30, "action": "push", "bulk": false, "publish": false},
            {"id": "half", "time": "09:00", "action": "push", "bulk": false, "publish": "?"}
        ]});
        let orig_bytes = serde_json::to_vec_pretty(&orig).unwrap();
        std::fs::write(&p, &orig_bytes).unwrap();
        let r = migrate_schedule_file(&p).unwrap();
        assert_eq!(r.migrated_ids, vec!["owner-daily".to_string(), "half".to_string()]);
        assert!(r.wrote && r.backup_created);
        assert_eq!(std::fs::read(backup_path(&p)).unwrap(), orig_bytes, "② 백업 = 원본 바이트");
        let after: Value = serde_json::from_slice(&std::fs::read(&p).unwrap()).unwrap();
        assert_eq!(after[MIGRATION_MARK_KEY], json!("done"));
        assert_eq!((after["jobs"][0]["bulk"].clone(), after["jobs"][0]["publish"].clone()), (json!(true), json!(true)));
        assert_eq!((after["jobs"][1]["bulk"].clone(), after["jobs"][1]["publish"].clone()), (json!(false), json!(false)), "이미 있는 칸 보존");
        assert_eq!((after["jobs"][2]["bulk"].clone(), after["jobs"][2]["publish"].clone()), (json!(false), json!(true)), "판독 불가 칸만 true");
        assert_eq!(after["jobs"][0]["time"], json!("20:00"), "다른 칸 보존");
        // 멱등: 두 번째 = 쓰기 0 · 백업 덮지 않음
        let snapshot = std::fs::read(&p).unwrap();
        let r2 = migrate_schedule_file(&p).unwrap();
        assert_eq!(r2, MigrationReport::default());
        assert_eq!(std::fs::read(&p).unwrap(), snapshot);
        assert_eq!(std::fs::read(backup_path(&p)).unwrap(), orig_bytes, "백업은 첫 원본 그대로");
        // ③ 뒤 ④ 전에 끊긴 상황(표지 없음 · 칸 일부만) = 다시 ①부터 → 수렴
        std::fs::write(&p, serde_json::to_vec(&json!({"jobs": [{"id": "z", "bulk": true}]})).unwrap()).unwrap();
        let r3 = migrate_schedule_file(&p).unwrap();
        assert_eq!(r3.migrated_ids, vec!["z".to_string()]);
        assert!(!r3.backup_created, "백업이 이미 있으면 덮지 않음");
        // 파일 없음 = 아무것도 안 함
        assert_eq!(migrate_schedule_file(&d.join("none.json")).unwrap(), MigrationReport::default());
        // 깨진 JSON = 오류(쓰기 0)
        std::fs::write(d.join("bad.json"), b"{").unwrap();
        assert!(migrate_schedule_file(&d.join("bad.json")).is_err());
        assert!(!backup_path(&d.join("bad.json")).exists());
        let _ = std::fs::remove_dir_all(&d);
    }

    /// ★1R MAJOR(M1) 뮤테이션: 구조 손상(`{}`·`{"jobs":"bad"}`·비객체 잡·배열 뿌리) = 사실 None · 이행 쓰기 0.
    #[test]
    fn m1_structure_damage_is_unknown_not_empty() {
        let d = tmpdir("m1");
        let pack = d.join("pack");
        std::fs::create_dir_all(&pack).unwrap();
        let p = pack.join("schedule.json");
        for bad in [json!({}), json!({"jobs": "bad"}), json!({"jobs": [1, {"id": "x"}]}), json!([{"id": "x"}])] {
            std::fs::write(&p, bad.to_string()).unwrap();
            assert_eq!(schedule_facts(&[p.clone()], at(2026, 10, 6, 10, 0)), None, "{bad}");
            assert!(migrate_schedule_file(&p).is_err(), "{bad}");
            assert!(!backup_path(&p).exists(), "구조 손상 = 백업·쓰기 0");
        }
        let _ = std::fs::remove_dir_all(&d);
    }

    fn at(y: i32, mo: u32, d: u32, h: u32, mi: u32) -> chrono::DateTime<chrono::Local> {
        chrono::Local.with_ymd_and_hms(y, mo, d, h, mi, 0).earliest().unwrap()
    }

    #[test]
    fn next_fire_window_is_conservative() {
        let now = at(2026, 10, 6, 10, 0); // 화요일
        assert!(may_fire_within(&json!({"time": "20:00"}), now, 48 * 3600));
        assert!(!may_fire_within(&json!({"time": "20:00"}), now, 3600));
        assert!(may_fire_within(&json!({"time": "10:30"}), now, 3600));
        // 요일 한정: 금요일만 → 48시간(목 10:00까지) 안 아님
        assert!(!may_fire_within(&json!({"time": "09:00", "days": ["fri"]}), now, 48 * 3600));
        assert!(may_fire_within(&json!({"time": "09:00", "days": ["thu"]}), now, 48 * 3600));
        // at
        let t = now.timestamp();
        assert!(may_fire_within(&json!({"at": t + 100}), now, 3600));
        assert!(!may_fire_within(&json!({"at": t + 7200}), now, 3600));
        assert!(!may_fire_within(&json!({"at": t - 5}), now, 3600));
        // 주기 잡 = 돈다 · 판독 불가 = 돈다
        assert!(may_fire_within(&json!({"every_minutes": 1440}), now, 3600));
        assert!(may_fire_within(&json!({"time": "25:99"}), now, 3600));
        assert!(may_fire_within(&json!({"id": "nothing"}), now, 3600));
        assert!(may_fire_within(&json!({"at": "soon"}), now, 3600));
    }

    #[test]
    fn schedule_facts_bulk_publish_windows_and_unreadable() {
        let d = tmpdir("facts");
        let pack = d.join("pack");
        std::fs::create_dir_all(&pack).unwrap();
        std::fs::create_dir_all(d.join("pack-dept-a")).unwrap();
        let now = at(2026, 10, 6, 10, 0);
        std::fs::write(pack.join("schedule.json"), json!({"jobs": [
            {"id": "v", "time": "10:30", "bulk": false, "publish": false}
        ]}).to_string()).unwrap();
        std::fs::write(d.join("pack-dept-a/schedule.json"), json!({"jobs": [
            {"id": "owner", "time": "20:00"}
        ]}).to_string()).unwrap();
        let files = schedule_files(&pack);
        assert_eq!(files.len(), 2);
        let f = schedule_facts(&files, now).unwrap();
        assert_eq!(f, ScheduleFacts { bulk_within_48h: true, nonbulk_within_60m: true, publish_within_48h: true, unflagged_jobs: 1 });
        // 부서 잡이 칸을 갖추면(false) → 60분 창 밖 비대량 잡만 남음
        std::fs::write(d.join("pack-dept-a/schedule.json"), json!({"jobs": [
            {"id": "owner", "time": "20:00", "bulk": false, "publish": false}
        ]}).to_string()).unwrap();
        std::fs::write(pack.join("schedule.json"), json!({"jobs": []}).to_string()).unwrap();
        assert_eq!(schedule_facts(&files, now).unwrap(), ScheduleFacts::default());
        std::fs::write(pack.join("schedule.json"), b"{broken").unwrap();
        assert_eq!(schedule_facts(&files, now), None, "판독 불가 = 판정 불가");
        let _ = std::fs::remove_dir_all(&d);
    }
}
