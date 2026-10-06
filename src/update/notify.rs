//! 결과 기록 — 데몬 쪽 몫(설계 AUTO-UPDATE-118 §3-12 · MI1·MA11 · §3-10 실패 기록 · T3 설계 1장 「updates 칸」).
//!
//! - `state.json`(갱신 상태 폴더): `last_result{result_id, kind, release_seq, from_release_seq, code, at}` · `last_defer` ·
//!   `failures[(component, channel, target, release_seq)] = {class, count, next_at}` · `last_success`(N8) · `seats_blocked`(📌18).
//!   쓰기 = 원본 JSON 객체를 읽어 **고친 칸만** 바꾸고 원자 저장(U1 `UpdState` 가 모르는 칸을 지우지 않는다 · 앱(U4)이 읽는 알림 칸
//!   `last_notified_result_id`·`pending_notification` 도 보존).
//! - 상담소 접점 `<AGORA_CONFIG_DIR|~/.config/agora>/counsel/updates.jsonl` 에 `{"from","to","result","at"}` 1줄(최근 7일 · 10줄 상한).
//! - 신호 = T3 수집기 대기열(`javis_counsel.py signal --source update --op update.apply --error-code <code>`) — 새 발신 경로 0.

use super::errors::ErrCode;
use super::failures::{self, Class};
use serde_json::{json, Map, Value};
use std::path::{Path, PathBuf};

pub const STATE_FILE: &str = "state.json";
pub const UPDATES_FILE: &str = "updates.jsonl";
pub const UPDATES_MAX: usize = 10;
pub const UPDATES_MAX_AGE_SECS: i64 = 7 * 86400;

/// 결과 1건(러너 Kind 의 기록용 이름).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Outcome {
    pub kind: &'static str,
    pub code: ErrCode,
    pub component: String,
    pub channel: String,
    pub target: String,
    pub release_seq: u64,
    pub from_release_seq: u64,
    pub from_version: String,
    pub to_version: String,
    /// V5·V7 위반 = 영구(MA7) — 코드 분류를 덮어쓴다.
    pub force_permanent: bool,
    pub detail: String,
}

fn read_obj(dir: &Path) -> Result<Map<String, Value>, String> {
    match std::fs::read(dir.join(STATE_FILE)) {
        Ok(b) => match serde_json::from_slice::<Value>(&b) {
            Ok(Value::Object(m)) => Ok(m),
            Ok(_) | Err(_) => Err("state.json 손상 — 덮지 않는다".into()),
        },
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(Map::new()),
        Err(e) => Err(e.to_string()),
    }
}

/// `state.json` 을 읽어 `f` 로 고친 뒤 원자 저장.
pub fn update_state(dir: &Path, f: impl FnOnce(&mut Map<String, Value>)) -> Result<(), String> {
    super::ensure_private_dir(dir)?;
    let mut m = read_obj(dir)?;
    f(&mut m);
    let b = serde_json::to_vec_pretty(&Value::Object(m)).map_err(|e| e.to_string())?;
    super::journal::durable_write(&dir.join(STATE_FILE), &b)
}

/// 결과 기록(순수 부분 = 칸 계산). `now` = 벽시계 초 · `stamp` = N8 용 Stamp.
pub fn apply(m: &mut Map<String, Value>, o: &Outcome, result_id: &str, now: i64, stamp: Option<&super::clock::Stamp>) {
    m.insert(
        "last_result".into(),
        json!({"result_id": result_id, "kind": o.kind, "release_seq": o.release_seq, "from_release_seq": o.from_release_seq,
               "code": o.code.to_string(), "at": now}),
    );
    let key = super::check::failure_key(&o.component, &o.channel, &o.target, o.release_seq);
    match o.kind {
        "ok" => {
            if let Some(s) = stamp {
                m.insert("last_success".into(), serde_json::to_value(s).unwrap_or(Value::Null));
            }
            if let Some(Value::Object(f)) = m.get_mut("failures") {
                f.remove(&key);
            }
            m.remove("seats_blocked");
        }
        "deferred" => {
            m.insert("last_defer".into(), json!({"code": o.code.to_string(), "detail": o.detail, "at": now}));
            record_failure(m, &key, o, now, true);
        }
        "seats_blocked" => {
            m.insert("seats_blocked".into(), json!({"reason": "journal_unrecoverable", "at": now}));
        }
        "journal_corrupt" => {
            m.remove("seats_blocked");
        }
        _ => record_failure(m, &key, o, now, false),
    }
}

fn record_failure(m: &mut Map<String, Value>, key: &str, o: &Outcome, now: i64, deferred: bool) {
    let class = if o.force_permanent { Class::Permanent } else { failures::classify(o.code) };
    // 보류(S1~S6 · 조건 불충족)는 실패가 아니다 — 일시 원인 코드라도 백오프 칸을 만들지 않는다(다음 틱이 다시 본다).
    if class == Class::NotAFailure || (deferred && class != Class::Permanent) {
        return;
    }
    let f = m.entry("failures").or_insert_with(|| json!({}));
    let Some(f) = f.as_object_mut() else { return };
    let count = f.get(key).and_then(|v| v.get("count")).and_then(Value::as_u64).unwrap_or(0) as u32 + 1;
    let (cls, next_at) = match class {
        Class::Permanent => ("permanent", i64::MAX),
        _ => ("transient", failures::backoff_after(count).map(|s| now + s as i64).unwrap_or(i64::MAX)),
    };
    f.insert(key.to_string(), json!({"class": cls, "count": count, "next_at": next_at}));
}

/// 상담소 접점 폴더(`javis_counsel.config_dir()` 와 같은 규칙).
pub fn counsel_dir() -> Option<PathBuf> {
    if let Some(v) = std::env::var_os("AGORA_CONFIG_DIR").filter(|v| !v.is_empty()) {
        return Some(PathBuf::from(v).join("counsel"));
    }
    let home = std::env::var_os("HOME").or_else(|| std::env::var_os("USERPROFILE"))?;
    Some(PathBuf::from(home).join(".config").join("agora").join("counsel"))
}

/// `updates.jsonl` 에 1줄 — 최근 7일 · 10줄 상한으로 다시 써서 원자 저장.
pub fn append_update(dir: &Path, from: &str, to: &str, result: &str, at: i64) -> Result<(), String> {
    let path = dir.join(UPDATES_FILE);
    let mut rows: Vec<Value> = std::fs::read_to_string(&path)
        .unwrap_or_default()
        .lines()
        .filter_map(|l| serde_json::from_str::<Value>(l).ok())
        .filter(|v| v.get("at").and_then(Value::as_i64).map(|t| at - t <= UPDATES_MAX_AGE_SECS).unwrap_or(false))
        .collect();
    rows.push(json!({"from": from, "to": to, "result": result, "at": at}));
    let skip = rows.len().saturating_sub(UPDATES_MAX);
    let text: String = rows.iter().skip(skip).map(|v| format!("{v}\n")).collect();
    std::fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    super::journal::durable_write(&path, text.as_bytes())
}

/// 즉시 1통 대상(§3-12 예외 — 그날 이미 보냈어도).
pub fn immediate(code: ErrCode) -> bool {
    matches!(code, ErrCode::RollbackFailed | ErrCode::RollbackBlocked | ErrCode::JournalCorrupt | ErrCode::InstalledRevoked)
}

/// 상담소 신호 1건(수집기 대기열) — best-effort · 수집기 부재 = 조용히 끝(신호 없음 · 새 발신 경로 0).
pub fn signal(pack_dir: &Path, code: ErrCode) {
    let script = pack_dir.join("bin").join("javis_counsel.py");
    if !script.is_file() {
        return;
    }
    let py = if cfg!(windows) { "python" } else { "python3" };
    use crate::SpawnPolicy;
    let _ = crate::python_command(py)
        .spawn_policy(crate::ChildLifetime::Attached)
        .arg(&script)
        .args(["signal", "--source", "update", "--op", "update.apply", "--error-code", &code.to_string()])
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status();
}

#[cfg(test)]
mod tests {
    use super::*;

    fn o(kind: &'static str, code: ErrCode) -> Outcome {
        Outcome {
            kind,
            code,
            component: "cysr".into(),
            channel: "stable".into(),
            target: "darwin-aarch64".into(),
            release_seq: 9,
            from_release_seq: 8,
            from_version: "1.1.8".into(),
            to_version: "1.1.9".into(),
            force_permanent: false,
            detail: String::new(),
        }
    }

    #[test]
    fn state_fields_preserve_unknown_keys_and_classify_failures() {
        let d = std::env::temp_dir().join(format!("cys-u2-notify-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        update_state(&d, |m| {
            m.insert("last_notified_result_id".into(), json!("r0"));
        })
        .unwrap();
        update_state(&d, |m| apply(m, &o("rollback", ErrCode::VerifyFailed), "r1", 1000, None)).unwrap();
        let v: Value = serde_json::from_slice(&std::fs::read(d.join(STATE_FILE)).unwrap()).unwrap();
        assert_eq!(v["last_notified_result_id"], "r0", "앱 알림 칸 보존");
        assert_eq!(v["last_result"]["kind"], "rollback");
        let f = &v["failures"]["cysr/stable/darwin-aarch64/9"];
        assert_eq!((f["class"].as_str(), f["count"].as_u64(), f["next_at"].as_i64()), (Some("transient"), Some(1), Some(1000 + 6 * 3600)));
        // V5/V7 위반 = 영구
        let mut p = o("rollback", ErrCode::VerifyFailed);
        p.force_permanent = true;
        update_state(&d, |m| apply(m, &p, "r2", 2000, None)).unwrap();
        let v: Value = serde_json::from_slice(&std::fs::read(d.join(STATE_FILE)).unwrap()).unwrap();
        assert_eq!(v["failures"]["cysr/stable/darwin-aarch64/9"]["class"], "permanent");
        // 성공 = 그 실패 칸 지움 + seats_blocked 지움
        update_state(&d, |m| apply(m, &o("seats_blocked", ErrCode::JournalCorrupt), "r3", 3000, None)).unwrap();
        update_state(&d, |m| apply(m, &o("ok", ErrCode::Ok), "r4", 4000, None)).unwrap();
        let v: Value = serde_json::from_slice(&std::fs::read(d.join(STATE_FILE)).unwrap()).unwrap();
        assert!(v["failures"].get("cysr/stable/darwin-aarch64/9").is_none() && v.get("seats_blocked").is_none());
        // 보류는 실패 기록 아님(일시 원인) · last_defer 만
        update_state(&d, |m| apply(m, &o("deferred", ErrCode::DiskLow), "r5", 5000, None)).unwrap();
        let v: Value = serde_json::from_slice(&std::fs::read(d.join(STATE_FILE)).unwrap()).unwrap();
        assert_eq!(v["last_defer"]["code"], ErrCode::DiskLow.to_string());
        assert!(v["failures"].get("cysr/stable/darwin-aarch64/9").is_none());
        // 손상 state.json 은 덮지 않는다
        std::fs::write(d.join(STATE_FILE), b"[1").unwrap();
        assert!(update_state(&d, |_| {}).is_err());
    }

    #[test]
    fn updates_jsonl_keeps_last_ten_within_seven_days() {
        let d = std::env::temp_dir().join(format!("cys-u2-upd-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        append_update(&d, "1.1.7", "1.1.8", "ok", 0).unwrap();
        for i in 0..12 {
            append_update(&d, "1.1.8", "1.1.9", "rollback", UPDATES_MAX_AGE_SECS + 100 + i).unwrap();
        }
        let rows: Vec<Value> = std::fs::read_to_string(d.join(UPDATES_FILE)).unwrap().lines().map(|l| serde_json::from_str(l).unwrap()).collect();
        assert_eq!(rows.len(), UPDATES_MAX);
        assert!(rows.iter().all(|r| r["from"] == "1.1.8" && r.as_object().unwrap().len() == 4), "7일 지난 줄 정리 · 칸 4개");
    }
}
