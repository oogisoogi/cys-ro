//! 사이드바 「피드백」(TICKET=cys-feedback-menu · 2026-09-15) — 앱 층 전용(데몬·팩 무접촉).
//!
//! 계약 정본 = 도움 서버 `docs/HELP-API.md` §11(feedback-webform · 726 확정 2026-09-15 18:09):
//!   ① `POST /api/feedback` JSON 접수 → 201(같은 client_key 재전송 = 200) `{ id, upload_token, … }`
//!   ② 파일마다 `PUT /api/feedback/<id>/files?kind=photo|video&filename=<이름>`
//!      헤더 `x-feedback-upload: <upload_token>` · 본문 = 파일 바이트 · 접수 뒤 60분 창.
//! 2단계인 이유(서버 근거): 요청 본문 상한 100MB · Worker 메모리 128MB — 한 번에 올리면 가장자리에서 거부된다.
//!
//! 로컬 보관함 = `~/.cys/feedback-outbox/<local_id>/`. 초안 = `meta.json` 없는 폴더(첨부만 쌓임),
//! 보낼 건 = `meta.json` 있는 폴더. 보내지 못하면(네트워크·5xx·rate_limited) 그대로 두고 뒤로 물러나며 다시 보낸다.
//! 끝나면(보냄·거절) 폴더를 지운다 — 보낸 사진·화면 캡처를 이 컴퓨터에 남기지 않는다.
//!
//! HTTP 는 이 크레이트에 클라이언트가 없어 `curl` 자식 프로세스로 보낸다(74269d9 사용량 관례와 같음).
//! 올리기 토큰은 argv 에 싣지 않고 `-K` 설정 파일로 넘긴 뒤 지운다(같은 사용자의 ps 노출 회피).

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::time::Duration;

// ---------- 서버 계약 · 한 곳 ----------

/// 도움 서버 주소. 로컬 확인용으로만 `CYS_FEEDBACK_BASE` 로 덮는다.
pub const FEEDBACK_BASE_DEFAULT: &str = "https://jarvis-install.godmeyou.kr";
/// 한도 = 서버 §11-2·11-3 값 그대로(사진 5,242,880 · 영상 95,000,000바이트 · 딱 그 크기는 받는다).
/// ★UI `ui/src/feedback.ts` 에도 같은 값이 있다 — 시험 `limits_match_ui_module` 이 두 곳을 대조한다.
pub const TITLE_MAX: usize = 120;
pub const BODY_MAX: usize = 5000;
pub const CONTACT_MAX: usize = 200;
pub const PHOTO_MAX_BYTES: u64 = 5_242_880;
pub const PHOTO_MAX_COUNT: usize = 5;
pub const VIDEO_MAX_BYTES: u64 = 95_000_000;
pub const VIDEO_MAX_COUNT: usize = 1;
/// 접수 뒤 파일을 올릴 수 있는 창(서버 410 upload_window_closed). 넘긴 파일은 시도하지 않고 뺀다.
pub const UPLOAD_WINDOW_SECS: u64 = 60 * 60;
/// 보내지 못한 건을 이 컴퓨터에 두는 최대 기간. 넘기면 지운다(서버 보존 90일과 별개인 로컬 상한).
pub const KEEP_PENDING_SECS: u64 = 30 * 24 * 3600;
/// 초안(보내기 전 첨부만 있는 폴더)이 버려졌다고 보는 나이.
pub const ORPHAN_DRAFT_SECS: u64 = 24 * 3600;
pub const UPLOAD_HEADER: &str = "x-feedback-upload";

/// 접수 본문의 칸 이름은 **이 함수 한 곳에만** 적는다(master 지시 18:08 — 서버 정본이 바뀌면 여기만 고친다).
pub fn post_body(meta: &Meta, app_version: &str, os: &str) -> Value {
    let mut v = json!({
        "title": meta.title,
        "body": meta.body,
        "notice_shown": true,
        "source": "app",
        "app_version": app_version,
        "os": os,
        "client_key": meta.client_key,
    });
    if !meta.contact.trim().is_empty() {
        v["contact"] = json!(meta.contact);
    }
    v
}

pub fn post_url(base: &str) -> String {
    format!("{}/api/feedback", base.trim_end_matches('/'))
}

pub fn put_url(base: &str, server_id: &str, kind: &str, filename: &str) -> String {
    format!(
        "{}/api/feedback/{}/files?kind={}&filename={}",
        base.trim_end_matches('/'),
        pct_encode(server_id),
        pct_encode(kind),
        pct_encode(filename)
    )
}

pub fn current_os() -> &'static str {
    if cfg!(target_os = "windows") {
        "win"
    } else {
        "mac"
    }
}

fn pct_encode(s: &str) -> String {
    let mut out = String::new();
    for b in s.bytes() {
        if b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.' | b'~') {
            out.push(b as char);
        } else {
            out.push_str(&format!("%{b:02X}"));
        }
    }
    out
}

// ---------- 응답 판정 ----------

#[derive(Debug, Clone, PartialEq)]
pub struct HttpResp {
    /// None = 응답을 못 받음(네트워크·타임아웃·curl 실행 실패).
    pub status: Option<u16>,
    pub body: String,
    pub err: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Disp {
    Done,
    Retry,
    Drop,
}

pub fn error_code(body: &str) -> Option<String> {
    serde_json::from_str::<Value>(body)
        .ok()?
        .get("error")?
        .as_str()
        .map(str::to_string)
}

/// 재시도 규칙(726 제안 · master 전달): 400·401·404·410·411·413·415·429 file_cap·507 = 다시 안 보냄 ·
/// 429 rate_limited·5xx·네트워크 = 다시 보냄.
/// ★429 는 **file_cap 이라고 적힌 것만** 버린다 — 본문이 안 읽히는 429(앞단 프록시가 막은 경우 등)를
/// 버리면 일시적 제한 한 번에 피드백이 사라진다.
pub fn classify(r: &HttpResp) -> Disp {
    match r.status {
        None => Disp::Retry,
        Some(s) if (200..300).contains(&s) => Disp::Done,
        Some(429) => {
            if error_code(&r.body).as_deref() == Some("file_cap") {
                Disp::Drop
            } else {
                Disp::Retry
            }
        }
        Some(507) => Disp::Drop,
        Some(s) if s >= 500 => Disp::Retry,
        Some(_) => Disp::Drop,
    }
}

/// 60초에서 시작해 두 배씩 · 6시간 상한.
pub fn backoff_secs(attempts: u32) -> u64 {
    let base = 60u64.saturating_mul(1u64 << attempts.min(20));
    base.min(6 * 3600)
}

// ---------- 보관함 상태 ----------

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FileEntry {
    pub kind: String,
    pub file: String,
    pub name: String,
    pub mime: String,
    pub bytes: u64,
    /// pending · done · dropped
    pub state: String,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Meta {
    pub v: u32,
    pub local_id: String,
    pub client_key: String,
    pub created_at: u64,
    pub title: String,
    pub body: String,
    #[serde(default)]
    pub contact: String,
    pub files: Vec<FileEntry>,
    #[serde(default)]
    pub server_id: Option<String>,
    #[serde(default)]
    pub upload_token: Option<String>,
    #[serde(default)]
    pub accepted_at: Option<u64>,
    #[serde(default)]
    pub attempts: u32,
    #[serde(default)]
    pub next_at: u64,
    #[serde(default)]
    pub last_error: Option<String>,
}

pub fn outbox_dir() -> PathBuf {
    cys::home_dir().join(".cys/feedback-outbox")
}

/// UI 가 넘기는 초안 번호는 폴더 이름이 된다 — 경로 조각이 섞이면 보관함 밖을 쓰거나 지운다.
pub fn valid_local_id(id: &str) -> bool {
    (16..=40).contains(&id.len()) && id.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

pub fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn fresh_hex() -> String {
    use std::sync::atomic::{AtomicU64, Ordering};
    static SEQ: AtomicU64 = AtomicU64::new(0);
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!(
        "{:x}{:08x}{:04x}",
        nanos,
        std::process::id(),
        SEQ.fetch_add(1, Ordering::Relaxed) & 0xffff
    )
}

fn draft_path(outbox: &Path, id: &str) -> Result<PathBuf, String> {
    if !valid_local_id(id) {
        return Err("invalid_draft".into());
    }
    Ok(outbox.join(id))
}

pub fn new_draft(outbox: &Path) -> Result<String, String> {
    let id = fresh_hex();
    let id = id[id.len().saturating_sub(40)..].to_string();
    std::fs::create_dir_all(outbox.join(&id)).map_err(|e| format!("보관함 폴더를 만들지 못했습니다: {e}"))?;
    Ok(id)
}

fn safe_ext(name: &str) -> String {
    let ext: String = Path::new(name)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_ascii_lowercase()
        .chars()
        .filter(|c| c.is_ascii_alphanumeric())
        .take(5)
        .collect();
    if ext.is_empty() {
        "bin".into()
    } else {
        ext
    }
}

/// 초안 폴더에 이미 놓인 첨부(`photo-N.*` · `video-N.*`) 목록.
pub fn staged_files(dir: &Path) -> Vec<(String, String, u64)> {
    let mut out = Vec::new();
    if let Ok(rd) = std::fs::read_dir(dir) {
        for e in rd.flatten() {
            let name = e.file_name().to_string_lossy().to_string();
            let kind = if name.starts_with("photo-") {
                "photo"
            } else if name.starts_with("video-") {
                "video"
            } else {
                continue;
            };
            if name.ends_with(".part") {
                continue;
            }
            let bytes = e.metadata().map(|m| m.len()).unwrap_or(0);
            out.push((kind.to_string(), name, bytes));
        }
    }
    out.sort();
    out
}

/// 첨부 한 건을 받을 수 있는지 — 장 수·크기 한도(화면 캡처도 사진 5장 안에서 센다 · master 채택 18:10).
pub fn check_attach(existing: &[(String, String, u64)], kind: &str, bytes: u64) -> Result<(), String> {
    let (max_count, max_bytes) = match kind {
        "photo" => (PHOTO_MAX_COUNT, PHOTO_MAX_BYTES),
        "video" => (VIDEO_MAX_COUNT, VIDEO_MAX_BYTES),
        _ => return Err("unsupported_type".into()),
    };
    if bytes == 0 {
        return Err("empty_file".into());
    }
    if bytes > max_bytes {
        return Err("file_too_large".into());
    }
    if existing.iter().filter(|(k, _, _)| k == kind).count() >= max_count {
        return Err("file_cap".into());
    }
    Ok(())
}

fn next_slot(dir: &Path, kind: &str, ext: &str) -> String {
    let mut n = 1;
    loop {
        let taken = staged_files(dir)
            .iter()
            .any(|(_, f, _)| f.starts_with(&format!("{kind}-{n}.")));
        if !taken {
            return format!("{kind}-{n}.{ext}");
        }
        n += 1;
    }
}

/// 첨부 바이트를 초안 폴더에 쓴다(임시 이름 → 이름 바꾸기). 원래 파일 이름은 meta 로만 간다.
pub fn stage_bytes(outbox: &Path, id: &str, kind: &str, name: &str, bytes: &[u8]) -> Result<Value, String> {
    let dir = draft_path(outbox, id)?;
    if !dir.is_dir() || dir.join("meta.json").exists() {
        return Err("invalid_draft".into());
    }
    check_attach(&staged_files(&dir), kind, bytes.len() as u64)?;
    let file = next_slot(&dir, kind, &safe_ext(name));
    let part = dir.join(format!("{file}.part"));
    std::fs::write(&part, bytes).map_err(|e| format!("첨부를 저장하지 못했습니다: {e}"))?;
    std::fs::rename(&part, dir.join(&file)).map_err(|e| format!("첨부를 저장하지 못했습니다: {e}"))?;
    Ok(json!({ "file": file, "bytes": bytes.len() }))
}

pub fn unstage(outbox: &Path, id: &str, file: &str) -> Result<(), String> {
    let dir = draft_path(outbox, id)?;
    let known = staged_files(&dir).into_iter().any(|(_, f, _)| f == file);
    if !known {
        return Err("not_found".into());
    }
    std::fs::remove_file(dir.join(file)).map_err(|e| e.to_string())
}

pub fn discard(outbox: &Path, id: &str) -> Result<(), String> {
    let dir = draft_path(outbox, id)?;
    if dir.is_dir() {
        std::fs::remove_dir_all(&dir).map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn char_len(s: &str) -> usize {
    s.chars().count()
}

pub fn validate_text(title: &str, body: &str, contact: &str) -> Result<(), String> {
    let t = title.trim();
    let b = body.trim();
    if t.is_empty() || char_len(t) > TITLE_MAX {
        return Err("invalid_title".into());
    }
    if b.is_empty() || char_len(b) > BODY_MAX {
        return Err("invalid_body".into());
    }
    if char_len(contact.trim()) > CONTACT_MAX {
        return Err("invalid_contact".into());
    }
    Ok(())
}

fn write_meta(dir: &Path, meta: &Meta) -> Result<(), String> {
    let tmp = dir.join("meta.json.part");
    let text = serde_json::to_string_pretty(meta).map_err(|e| e.to_string())?;
    std::fs::write(&tmp, text).map_err(|e| format!("보관함에 쓰지 못했습니다: {e}"))?;
    std::fs::rename(&tmp, dir.join("meta.json")).map_err(|e| format!("보관함에 쓰지 못했습니다: {e}"))
}

fn read_meta(dir: &Path) -> Option<Meta> {
    let text = std::fs::read_to_string(dir.join("meta.json")).ok()?;
    serde_json::from_str(&text).ok()
}

/// 초안을 「보낼 건」으로 굳힌다. 파일 이름 표시는 첨부할 때 UI 가 준 이름이다(`names`: 저장이름 → 원래이름).
pub fn seal(
    outbox: &Path,
    id: &str,
    title: &str,
    body: &str,
    contact: &str,
    names: &serde_json::Map<String, Value>,
    now: u64,
) -> Result<PathBuf, String> {
    let dir = draft_path(outbox, id)?;
    if !dir.is_dir() {
        return Err("invalid_draft".into());
    }
    validate_text(title, body, contact)?;
    let files = staged_files(&dir)
        .into_iter()
        .map(|(kind, file, bytes)| {
            let name = names
                .get(&file)
                .and_then(|v| v.as_str())
                .map(str::to_string)
                .unwrap_or_else(|| file.clone());
            let mime = mime_for_file(&file);
            FileEntry { kind, file, name, mime, bytes, state: "pending".into(), error: None }
        })
        .collect();
    let meta = Meta {
        v: 1,
        local_id: id.to_string(),
        client_key: format!("app{}", fresh_hex()),
        created_at: now,
        title: title.trim().to_string(),
        body: body.trim().to_string(),
        contact: contact.trim().to_string(),
        files,
        server_id: None,
        upload_token: None,
        accepted_at: None,
        attempts: 0,
        next_at: 0,
        last_error: None,
    };
    write_meta(&dir, &meta)?;
    Ok(dir)
}

fn mime_for_file(file: &str) -> String {
    match safe_ext(file).as_str() {
        "jpg" | "jpeg" => "image/jpeg",
        "png" => "image/png",
        "webp" => "image/webp",
        "heic" | "heif" => "image/heic",
        "mp4" | "m4v" => "video/mp4",
        "mov" => "video/quicktime",
        "webm" => "video/webm",
        _ => "application/octet-stream",
    }
    .to_string()
}

// ---------- 보내기 ----------

pub trait Transport {
    fn post_json(&self, dir: &Path, url: &str, body: &Value) -> HttpResp;
    fn put_file(&self, dir: &Path, url: &str, token: &str, file: &str, mime: &str) -> HttpResp;
}

#[derive(Debug, Clone, PartialEq)]
pub enum Outcome {
    Sent { id: String, dropped: Vec<(String, String)> },
    Retry { error: String },
    Rejected { error: String },
    Expired,
    Missing,
}

fn describe(r: &HttpResp) -> String {
    match (r.status, error_code(&r.body), &r.err) {
        (Some(s), Some(code), _) => format!("{s} {code}"),
        (Some(s), None, _) => format!("{s}"),
        (None, _, Some(e)) => e.clone(),
        (None, _, None) => "network".into(),
    }
}

fn schedule_retry(dir: &Path, meta: &mut Meta, now: u64, error: String) -> Outcome {
    meta.attempts = meta.attempts.saturating_add(1);
    meta.next_at = now + backoff_secs(meta.attempts - 1);
    meta.last_error = Some(error.clone());
    let _ = write_meta(dir, meta);
    Outcome::Retry { error }
}

/// 보낼 건 한 폴더를 끝까지(또는 다음 재시도까지) 진행한다. 끝나면 폴더를 지운다.
/// Rejected(접수 거절)는 폴더를 **남긴다** — 창에서 보냈으면 사용자가 고쳐 다시 보내고, 뒤에서
/// 돌 때는 호출자(flush)가 지운다.
pub fn process(dir: &Path, t: &dyn Transport, base: &str, app_version: &str, now: u64) -> Outcome {
    let Some(mut meta) = read_meta(dir) else { return Outcome::Missing };
    if now.saturating_sub(meta.created_at) > KEEP_PENDING_SECS {
        let _ = std::fs::remove_dir_all(dir);
        return Outcome::Expired;
    }
    let pending = |m: &Meta| m.files.iter().any(|f| f.state == "pending");
    if meta.server_id.is_none() || (pending(&meta) && meta.upload_token.is_none()) {
        let resp = t.post_json(dir, &post_url(base), &post_body(&meta, app_version, current_os()));
        match classify(&resp) {
            Disp::Retry => return schedule_retry(dir, &mut meta, now, describe(&resp)),
            Disp::Drop => {
                return Outcome::Rejected { error: error_code(&resp.body).unwrap_or_else(|| describe(&resp)) };
            }
            Disp::Done => {
                let v: Value = serde_json::from_str(&resp.body).unwrap_or(Value::Null);
                let Some(id) = v["id"].as_str() else {
                    return schedule_retry(dir, &mut meta, now, "bad_response".into());
                };
                meta.server_id = Some(id.to_string());
                // 창은 **처음** 접수된 때부터 센다(같은 client_key 재전송이 창을 다시 열지 않는다).
                meta.accepted_at.get_or_insert(now);
                match v["upload_token"].as_str() {
                    Some(token) => meta.upload_token = Some(token.to_string()),
                    // 60분 창이 지난 재전송은 200 · upload_token null(§11-2) — 파일은 더 못 붙인다.
                    // 이것을 「응답 이상」으로 재시도하면 같은 답을 영원히 받는다. 파일만 빼고 글은 보낸 것으로 끝낸다.
                    None => {
                        meta.upload_token = None;
                        for f in meta.files.iter_mut().filter(|f| f.state == "pending") {
                            f.state = "dropped".into();
                            f.error = Some("upload_window_closed".into());
                        }
                    }
                }
                let _ = write_meta(dir, &meta);
            }
        }
    }
    let server_id = meta.server_id.clone().unwrap_or_default();
    let token = meta.upload_token.clone().unwrap_or_default();
    let accepted = meta.accepted_at.unwrap_or(now);
    for i in 0..meta.files.len() {
        if meta.files[i].state != "pending" {
            continue;
        }
        if now.saturating_sub(accepted) >= UPLOAD_WINDOW_SECS {
            meta.files[i].state = "dropped".into();
            meta.files[i].error = Some("upload_window_closed".into());
            let _ = write_meta(dir, &meta);
            continue;
        }
        let f = meta.files[i].clone();
        let resp = t.put_file(dir, &put_url(base, &server_id, &f.kind, &f.name), &token, &f.file, &f.mime);
        match classify(&resp) {
            Disp::Done => meta.files[i].state = "done".into(),
            Disp::Drop => {
                meta.files[i].state = "dropped".into();
                meta.files[i].error = Some(error_code(&resp.body).unwrap_or_else(|| describe(&resp)));
            }
            Disp::Retry => return schedule_retry(dir, &mut meta, now, describe(&resp)),
        }
        let _ = write_meta(dir, &meta);
    }
    let dropped = meta
        .files
        .iter()
        .filter(|f| f.state == "dropped")
        .map(|f| (f.name.clone(), f.error.clone().unwrap_or_default()))
        .collect();
    let _ = std::fs::remove_dir_all(dir);
    Outcome::Sent { id: server_id, dropped }
}

/// 보관함 전체를 한 번 훑는다: 때가 된 건은 보내고, 오래된 초안은 지운다.
pub fn flush(outbox: &Path, t: &dyn Transport, base: &str, app_version: &str, now: u64) -> Value {
    let (mut sent, mut pending, mut dropped) = (0, 0, 0);
    let Ok(rd) = std::fs::read_dir(outbox) else {
        return json!({ "sent": 0, "pending": 0, "dropped": 0 });
    };
    let mut dirs: Vec<PathBuf> = rd.flatten().map(|e| e.path()).filter(|p| p.is_dir()).collect();
    dirs.sort();
    for dir in dirs {
        let name = dir.file_name().and_then(|n| n.to_str()).unwrap_or("");
        if !valid_local_id(name) {
            continue;
        }
        let Some(meta) = read_meta(&dir) else {
            let old = std::fs::metadata(&dir)
                .and_then(|m| m.modified())
                .ok()
                .and_then(|m| m.duration_since(std::time::UNIX_EPOCH).ok())
                .map(|d| now.saturating_sub(d.as_secs()) > ORPHAN_DRAFT_SECS)
                .unwrap_or(false);
            if old {
                let _ = std::fs::remove_dir_all(&dir);
            }
            continue;
        };
        if meta.next_at > now {
            pending += 1;
            continue;
        }
        match process(&dir, t, base, app_version, now) {
            Outcome::Sent { .. } => sent += 1,
            Outcome::Retry { .. } => pending += 1,
            Outcome::Rejected { .. } | Outcome::Expired => {
                let _ = std::fs::remove_dir_all(&dir);
                dropped += 1;
            }
            Outcome::Missing => {}
        }
    }
    json!({ "sent": sent, "pending": pending, "dropped": dropped })
}

// ---------- curl ----------

pub struct Curl {
    pub app_version: String,
}

fn valid_token(token: &str) -> bool {
    !token.is_empty() && token.len() <= 512 && token.bytes().all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.'))
}

impl Curl {
    fn run(&self, dir: &Path, args: &[String], limit: Duration) -> HttpResp {
        let out = dir.join(".curl-code");
        let resp = dir.join(".curl-resp");
        let _ = std::fs::remove_file(&resp);
        let Ok(sink) = std::fs::File::create(&out) else {
            return HttpResp { status: None, body: String::new(), err: Some("tmp_create".into()) };
        };
        let mut cmd = std::process::Command::new(if cfg!(windows) { "curl.exe" } else { "curl" });
        cmd.current_dir(dir)
            .args(["-sS", "--connect-timeout", "15", "--max-time", &limit.as_secs().to_string(), "-o", ".curl-resp", "-w", "%{http_code}"])
            .arg("-H")
            .arg(format!("user-agent: cys-app/{}", self.app_version))
            .args(args)
            .stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::from(sink))
            .stderr(std::process::Stdio::null());
        {
            // 콘솔 창 숨김 — flag word 는 cys::ChildLifetime 등급표가 유일 정의처(TICKET=cysr-console-flicker-r2).
            use cys::SpawnPolicy as _;
            cmd.spawn_policy(cys::ChildLifetime::Attached);
        }
        let result = match cmd.spawn() {
            Err(e) => HttpResp { status: None, body: String::new(), err: Some(format!("curl: {e}")) },
            Ok(mut child) => {
                // curl 자신이 --max-time 으로 끝나지만, 걸려도 앱 스레드가 굳지 않게 10초 여유를 둔 상한을 따로 건다.
                let deadline = std::time::Instant::now() + limit + Duration::from_secs(10);
                let ok = loop {
                    match child.try_wait() {
                        Ok(Some(st)) => break st.success(),
                        Ok(None) if std::time::Instant::now() > deadline => {
                            let _ = child.kill();
                            let _ = child.wait();
                            break false;
                        }
                        Ok(None) => std::thread::sleep(Duration::from_millis(100)),
                        Err(_) => break false,
                    }
                };
                let code = std::fs::read_to_string(&out).unwrap_or_default();
                let status = code.trim().parse::<u16>().ok().filter(|s| *s >= 100 && ok);
                let body = std::fs::read_to_string(&resp).unwrap_or_default();
                HttpResp { status, body, err: if status.is_none() { Some("network".into()) } else { None } }
            }
        };
        let _ = std::fs::remove_file(&out);
        let _ = std::fs::remove_file(&resp);
        result
    }
}

impl Transport for Curl {
    fn post_json(&self, dir: &Path, url: &str, body: &Value) -> HttpResp {
        let path = dir.join(".post.json");
        if std::fs::write(&path, body.to_string()).is_err() {
            return HttpResp { status: None, body: String::new(), err: Some("tmp_write".into()) };
        }
        let args: Vec<String> = ["-H", "content-type: application/json", "--data-binary", "@.post.json", url]
            .iter()
            .map(|s| s.to_string())
            .collect();
        let r = self.run(dir, &args, Duration::from_secs(60));
        let _ = std::fs::remove_file(&path);
        r
    }

    fn put_file(&self, dir: &Path, url: &str, token: &str, file: &str, mime: &str) -> HttpResp {
        if !valid_token(token) {
            return HttpResp { status: Some(401), body: r#"{"error":"upload_unauthorized"}"#.into(), err: None };
        }
        let cfg = dir.join(".put.cfg");
        if std::fs::write(&cfg, format!("header = \"{UPLOAD_HEADER}: {token}\"\n")).is_err() {
            return HttpResp { status: None, body: String::new(), err: Some("tmp_write".into()) };
        }
        let limit = if file.starts_with("video-") { 900 } else { 120 };
        let args: Vec<String> = ["-K", ".put.cfg", "-H", &format!("content-type: {mime}"), "-T", file, url]
            .iter()
            .map(|s| s.to_string())
            .collect();
        let r = self.run(dir, &args, Duration::from_secs(limit));
        let _ = std::fs::remove_file(&cfg);
        r
    }
}

// ---------- 화면 캡처(맥) ----------

pub fn capture_supported() -> bool {
    cfg!(target_os = "macos")
}

/// 맥 밖에서는 캡처를 지원하지 않는다(capture_supported() == false 와 같은 뜻).
/// (1.1.8 병합) 원작자 창 정책 점검(spawn_policy_tests)이 맥 전용 스폰을 #[cfg] 로 가두길 요구 — 함수째 OS 로 가른다.
#[cfg(not(target_os = "macos"))]
pub fn capture_into(_outbox: &Path, _id: &str) -> Result<Value, String> {
    Err("capture_unsupported".into())
}

/// 지금 화면(주 모니터)을 사진 한 장으로 초안에 넣는다. 창을 가린 뒤 부르는 것은 UI 몫이다.
#[cfg(target_os = "macos")]
pub fn capture_into(outbox: &Path, id: &str) -> Result<Value, String> {
    if !capture_supported() {
        return Err("capture_unsupported".into());
    }
    let dir = draft_path(outbox, id)?;
    if !dir.is_dir() || dir.join("meta.json").exists() {
        return Err("invalid_draft".into());
    }
    check_attach(&staged_files(&dir), "photo", 1)?;
    let file = next_slot(&dir, "photo", "png");
    let part = format!("{file}.part");
    let status = std::process::Command::new("/usr/sbin/screencapture")
        .args(["-x", "-t", "png", &part])
        .current_dir(&dir)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map_err(|e| format!("capture_failed: {e}"))?;
    let bytes = std::fs::metadata(dir.join(&part)).map(|m| m.len()).unwrap_or(0);
    if !status.success() || bytes == 0 {
        let _ = std::fs::remove_file(dir.join(&part));
        return Err("capture_failed".into());
    }
    if bytes > PHOTO_MAX_BYTES {
        let _ = std::fs::remove_file(dir.join(&part));
        return Err("file_too_large".into());
    }
    std::fs::rename(dir.join(&part), dir.join(&file)).map_err(|e| e.to_string())?;
    Ok(json!({ "file": file, "bytes": bytes }))
}

// ---------- Tauri 명령 ----------

fn base_url() -> String {
    std::env::var("CYS_FEEDBACK_BASE").unwrap_or_else(|_| FEEDBACK_BASE_DEFAULT.to_string())
}

/// 창에서 보내기와 뒤에서 다시 보내기가 같은 폴더를 동시에 만지지 않게 한 줄로 세운다.
static SEND_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

/// ★1.1.8 병합(원작자 U6 `FB_LOCK` 취지 합성): 초안 폴더를 바꾸는 작업(첨부·화면 캡처·첨부 빼기·버리기)은 한 번에
/// 하나 — 칸 번호 배정(`next_slot`)·장 수 상한(`check_attach`)이 동시 호출로 어긋나지 않게. UI 도 첨부를 한 줄로
/// 세우지만 여기가 최종 방어다. 앞선 작업이 패닉했더라도 상태는 매 호출 디스크에서 다시 읽으므로 이어서 쓴다.
static STAGE_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

fn stage_lock() -> std::sync::MutexGuard<'static, ()> {
    STAGE_LOCK.lock().unwrap_or_else(|p| p.into_inner())
}

#[tauri::command]
pub fn feedback_new_draft() -> Result<Value, String> {
    let id = new_draft(&outbox_dir())?;
    Ok(json!({ "id": id, "capture_supported": capture_supported() }))
}

/// 첨부 바이트는 JSON 이 아닌 원시 본문으로 받는다(영상 95MB 를 base64 로 부풀리지 않는다).
/// 헤더: x-draft · x-kind(photo|video) · x-name(encodeURIComponent 한 원래 이름).
#[tauri::command]
pub fn feedback_stage_file(request: tauri::ipc::Request<'_>) -> Result<Value, String> {
    let tauri::ipc::InvokeBody::Raw(bytes) = request.body() else {
        return Err("invalid_body".into());
    };
    let h = |k: &str| request.headers().get(k).and_then(|v| v.to_str().ok()).unwrap_or("").to_string();
    let kind = h("x-kind");
    if kind != "photo" && kind != "video" {
        return Err("unsupported_type".into());
    }
    let _g = stage_lock();
    stage_bytes(&outbox_dir(), &h("x-draft"), &kind, &h("x-name"), bytes)
}

#[tauri::command]
pub fn feedback_unstage(draft: String, file: String) -> Result<(), String> {
    let _g = stage_lock();
    unstage(&outbox_dir(), &draft, &file)
}

#[tauri::command]
pub fn feedback_discard(draft: String) -> Result<(), String> {
    let _g = stage_lock();
    discard(&outbox_dir(), &draft)
}

#[tauri::command]
pub async fn feedback_capture(draft: String) -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let _g = stage_lock();
        capture_into(&outbox_dir(), &draft)
    })
        .await
        .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn feedback_submit(
    draft: String,
    title: String,
    body: String,
    contact: String,
    names: serde_json::Map<String, Value>,
) -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let _g = SEND_LOCK.lock().unwrap_or_else(|p| p.into_inner());
        let outbox = outbox_dir();
        let dir = seal(&outbox, &draft, &title, &body, &contact, &names, now_secs())?;
        let curl = Curl { app_version: env!("CARGO_PKG_VERSION").to_string() };
        Ok(match process(&dir, &curl, &base_url(), &curl.app_version, now_secs()) {
            Outcome::Sent { id, dropped } => json!({
                "state": "sent", "id": id,
                "dropped": dropped.iter().map(|(n, e)| json!({ "name": n, "error": e })).collect::<Vec<_>>(),
            }),
            Outcome::Retry { error } => json!({ "state": "queued", "error": error }),
            Outcome::Rejected { error } => {
                // 사용자가 고쳐 다시 보낼 수 있게 초안(첨부)은 남기고 「보낼 건」 표시만 걷는다.
                let _ = std::fs::remove_file(dir.join("meta.json"));
                json!({ "state": "rejected", "error": error })
            }
            Outcome::Expired | Outcome::Missing => json!({ "state": "rejected", "error": "invalid_draft" }),
        })
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn feedback_flush() -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(|| {
        let Ok(_g) = SEND_LOCK.try_lock() else {
            return json!({ "busy": true });
        };
        let curl = Curl { app_version: env!("CARGO_PKG_VERSION").to_string() };
        flush(&outbox_dir(), &curl, &base_url(), &curl.app_version, now_secs())
    })
    .await
    .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    fn tmp_outbox(tag: &str) -> PathBuf {
        let p = std::env::temp_dir().join(format!("cys-fb-test-{tag}-{}", fresh_hex()));
        std::fs::create_dir_all(&p).unwrap();
        p
    }

    fn resp(status: u16, body: &str) -> HttpResp {
        HttpResp { status: Some(status), body: body.into(), err: None }
    }

    /// 순서대로 응답을 돌려주고, 받은 요청을 적어 두는 가짜 전송.
    struct Fake {
        replies: RefCell<Vec<HttpResp>>,
        calls: RefCell<Vec<String>>,
    }
    impl Fake {
        fn new(r: Vec<HttpResp>) -> Self {
            Fake { replies: RefCell::new(r), calls: RefCell::new(vec![]) }
        }
        fn next(&self) -> HttpResp {
            let mut r = self.replies.borrow_mut();
            assert!(!r.is_empty(), "예상보다 요청이 많다: {:?}", self.calls.borrow());
            r.remove(0)
        }
    }
    impl Transport for Fake {
        fn post_json(&self, _dir: &Path, url: &str, body: &Value) -> HttpResp {
            self.calls.borrow_mut().push(format!("POST {url} {}", body["client_key"].as_str().unwrap_or("")));
            self.next()
        }
        fn put_file(&self, dir: &Path, url: &str, token: &str, file: &str, _mime: &str) -> HttpResp {
            assert!(dir.join(file).exists(), "올리는 파일이 초안 폴더에 있어야 한다: {file}");
            self.calls.borrow_mut().push(format!("PUT {url} {token}"));
            self.next()
        }
    }

    fn sealed(outbox: &Path, photos: usize) -> PathBuf {
        let id = new_draft(outbox).unwrap();
        for i in 0..photos {
            stage_bytes(outbox, &id, "photo", &format!("사진 {i}.JPG"), b"\xff\xd8\xff data").unwrap();
        }
        let mut names = serde_json::Map::new();
        names.insert("photo-1.jpg".into(), json!("사진 0.JPG"));
        seal(outbox, &id, "제목", "내용", "", &names, 1_000).unwrap()
    }

    const ACCEPT: &str = r#"{"ok":true,"id":"fb_1","upload_token":"tok-abc","notice":"n"}"#;

    #[test]
    fn classify_follows_contract_retry_table() {
        assert_eq!(classify(&HttpResp { status: None, body: "".into(), err: Some("x".into()) }), Disp::Retry);
        assert_eq!(classify(&resp(201, "")), Disp::Done);
        assert_eq!(classify(&resp(200, "")), Disp::Done);
        // §11-8 표 전부(409 = client_key_used).
        for s in [400, 401, 404, 409, 410, 411, 413, 415, 507] {
            assert_eq!(classify(&resp(s, r#"{"error":"x"}"#)), Disp::Drop, "{s}");
        }
        assert_eq!(classify(&resp(429, r#"{"ok":false,"error":"file_cap"}"#)), Disp::Drop);
        assert_eq!(classify(&resp(429, r#"{"ok":false,"error":"rate_limited"}"#)), Disp::Retry);
        // 본문이 안 읽히는 429 는 버리지 않는다(앞단이 막은 일시 제한).
        assert_eq!(classify(&resp(429, "<html>")), Disp::Retry);
        for s in [500, 502, 503] {
            assert_eq!(classify(&resp(s, "")), Disp::Retry, "{s}");
        }
    }

    #[test]
    fn post_body_carries_contract_fields_and_omits_blank_contact() {
        let meta = Meta {
            v: 1, local_id: "a".repeat(16), client_key: "appkey1234567890".into(), created_at: 0,
            title: "t".into(), body: "b".into(), contact: "  ".into(), files: vec![],
            server_id: None, upload_token: None, accepted_at: None, attempts: 0, next_at: 0, last_error: None,
        };
        let v = post_body(&meta, "0.14.37", "mac");
        assert_eq!(v["notice_shown"], json!(true));
        assert_eq!(v["source"], json!("app"));
        assert_eq!(v["os"], json!("mac"));
        assert_eq!(v["app_version"], json!("0.14.37"));
        assert_eq!(v["client_key"], json!("appkey1234567890"));
        assert!(v.get("contact").is_none(), "빈 연락처는 칸째 빼야 한다: {v}");
        let mut m2 = meta.clone();
        m2.contact = "010".into();
        assert_eq!(post_body(&m2, "x", "win")["contact"], json!("010"));
        // client_key 는 서버 모양(영문숫자_- 16~64자)에 맞아야 재전송 멱등이 산다.
        let key = format!("app{}", fresh_hex());
        assert!((16..=64).contains(&key.len()) && key.bytes().all(|b| b.is_ascii_alphanumeric()), "{key}");
    }

    #[test]
    fn put_url_encodes_filename_and_query() {
        let u = put_url("https://h/", "fb_1", "photo", "화면 1&x=2.png");
        assert!(u.starts_with("https://h/api/feedback/fb_1/files?kind=photo&filename="), "{u}");
        assert!(!u.contains(' ') && !u.contains("&x=2"), "이름 속 &·공백이 질의를 깨면 안 된다: {u}");
    }

    #[test]
    fn draft_id_rejects_path_pieces() {
        let ob = tmp_outbox("id");
        for bad in ["../../etc", "abc", "0123456789abcdef/..", "0123456789ABCDEF", ""] {
            assert!(!valid_local_id(bad), "{bad}");
            assert_eq!(discard(&ob, bad), Err("invalid_draft".into()), "{bad}");
        }
        let id = new_draft(&ob).unwrap();
        assert!(valid_local_id(&id), "만든 번호가 스스로의 검사를 통과해야 한다: {id}");
        let _ = std::fs::remove_dir_all(&ob);
    }

    #[test]
    fn capture_counts_inside_five_photos_and_video_limit() {
        let mut existing: Vec<(String, String, u64)> = (1..=5).map(|i| ("photo".into(), format!("photo-{i}.png"), 10)).collect();
        assert_eq!(check_attach(&existing, "photo", 10), Err("file_cap".into()));
        assert_eq!(check_attach(&existing, "video", VIDEO_MAX_BYTES), Ok(()));
        assert_eq!(check_attach(&existing, "video", VIDEO_MAX_BYTES + 1), Err("file_too_large".into()));
        existing.pop();
        assert_eq!(check_attach(&existing, "photo", PHOTO_MAX_BYTES), Ok(()));
        assert_eq!(check_attach(&existing, "photo", PHOTO_MAX_BYTES + 1), Err("file_too_large".into()));
        existing.push(("video".into(), "video-1.mp4".into(), 10));
        assert_eq!(check_attach(&existing, "video", 10), Err("file_cap".into()));
        assert_eq!(check_attach(&existing, "photo", 0), Err("empty_file".into()));
    }

    #[test]
    fn stage_rejects_sixth_photo_on_disk() {
        let ob = tmp_outbox("six");
        let id = new_draft(&ob).unwrap();
        for i in 0..5 {
            stage_bytes(&ob, &id, "photo", &format!("{i}.png"), b"x").unwrap();
        }
        assert_eq!(stage_bytes(&ob, &id, "photo", "6.png", b"x"), Err("file_cap".into()));
        assert_eq!(staged_files(&ob.join(&id)).len(), 5);
        let _ = std::fs::remove_dir_all(&ob);
    }

    #[test]
    fn sent_path_posts_then_puts_each_file_and_removes_folder() {
        let ob = tmp_outbox("sent");
        let dir = sealed(&ob, 2);
        let fake = Fake::new(vec![resp(201, ACCEPT), resp(201, "{}"), resp(201, "{}")]);
        let out = process(&dir, &fake, "https://h", "v", 1_000);
        assert_eq!(out, Outcome::Sent { id: "fb_1".into(), dropped: vec![] });
        let calls = fake.calls.borrow();
        assert_eq!(calls.len(), 3);
        assert!(calls[0].starts_with("POST https://h/api/feedback app"));
        assert!(calls[1].contains("/api/feedback/fb_1/files?kind=photo&filename=") && calls[1].ends_with(" tok-abc"));
        assert!(!dir.exists(), "보낸 뒤 사진이 이 컴퓨터에 남으면 안 된다");
        let _ = std::fs::remove_dir_all(&ob);
    }

    #[test]
    fn network_failure_keeps_folder_and_retry_reuses_client_key() {
        let ob = tmp_outbox("retry");
        let dir = sealed(&ob, 1);
        let net = HttpResp { status: None, body: String::new(), err: Some("network".into()) };
        let fake = Fake::new(vec![net]);
        assert!(matches!(process(&dir, &fake, "https://h", "v", 1_000), Outcome::Retry { .. }));
        let m = read_meta(&dir).expect("보관함에 남아야 한다");
        assert_eq!((m.attempts, m.next_at), (1, 1_000 + 60));
        let key1 = fake.calls.borrow()[0].clone();
        // 두 번째 시도: 같은 client_key 로 접수 → 파일 PUT 이 rate_limited → 다시 대기.
        let fake2 = Fake::new(vec![resp(200, ACCEPT), resp(429, r#"{"error":"rate_limited"}"#)]);
        assert!(matches!(process(&dir, &fake2, "https://h", "v", 1_100), Outcome::Retry { .. }));
        assert_eq!(fake2.calls.borrow()[0], key1, "재시도 접수는 같은 client_key 여야 한다(중복 방지)");
        let m = read_meta(&dir).unwrap();
        assert_eq!((m.attempts, m.next_at, m.accepted_at), (2, 1_100 + 120, Some(1_100)));
        // 세 번째 시도: 토큰이 있으니 접수를 다시 하지 않고 파일만 올린다.
        let fake3 = Fake::new(vec![resp(201, "{}")]);
        assert!(matches!(process(&dir, &fake3, "https://h", "v", 1_400), Outcome::Sent { .. }));
        assert_eq!(fake3.calls.borrow().len(), 1);
        let _ = std::fs::remove_dir_all(&ob);
    }

    #[test]
    fn file_cap_and_window_drop_files_but_text_still_sends() {
        let ob = tmp_outbox("drop");
        let dir = sealed(&ob, 2);
        let fake = Fake::new(vec![resp(201, ACCEPT), resp(429, r#"{"error":"file_cap"}"#), resp(201, "{}")]);
        match process(&dir, &fake, "https://h", "v", 1_000) {
            Outcome::Sent { dropped, .. } => assert_eq!(dropped.len(), 1, "{dropped:?}"),
            o => panic!("{o:?}"),
        }
        // 창 60분이 지난 뒤 이어서 보낼 때: 남은 파일은 시도하지 않고 뺀다.
        let dir = sealed(&ob, 1);
        let mut m = read_meta(&dir).unwrap();
        m.server_id = Some("fb_2".into());
        m.upload_token = Some("tok".into());
        m.accepted_at = Some(1_000);
        write_meta(&dir, &m).unwrap();
        let fake = Fake::new(vec![]);
        match process(&dir, &fake, "https://h", "v", 1_000 + UPLOAD_WINDOW_SECS) {
            Outcome::Sent { dropped, .. } => assert_eq!(dropped[0].1, "upload_window_closed"),
            o => panic!("{o:?}"),
        }
        let _ = std::fs::remove_dir_all(&ob);
    }

    /// §11-2: 60분이 지난 뒤 같은 client_key 로 다시 접수하면 200 · upload_token null. 파일은 빼고 끝내야 한다
    /// (응답 이상으로 보고 재시도하면 같은 답을 영원히 받는다).
    #[test]
    fn late_resend_with_null_token_finishes_without_files() {
        let ob = tmp_outbox("nulltok");
        let dir = sealed(&ob, 2);
        let late = r#"{"ok":true,"id":"fb_9","upload_token":null,"notice":"n"}"#;
        let fake = Fake::new(vec![resp(200, late)]);
        match process(&dir, &fake, "https://h", "v", 1_000) {
            Outcome::Sent { id, dropped } => {
                assert_eq!(id, "fb_9");
                assert_eq!(dropped.len(), 2, "{dropped:?}");
                assert!(dropped.iter().all(|(_, e)| e == "upload_window_closed"));
            }
            o => panic!("재시도로 떨어지면 안 된다: {o:?}"),
        }
        assert_eq!(fake.calls.borrow().len(), 1, "토큰 없이 PUT 을 시도하면 안 된다");
        assert!(!dir.exists());
        let _ = std::fs::remove_dir_all(&ob);
    }

    #[test]
    fn rejected_post_is_not_retried_and_flush_removes_it() {
        let ob = tmp_outbox("reject");
        let dir = sealed(&ob, 0);
        let fake = Fake::new(vec![resp(400, r#"{"error":"invalid_title"}"#)]);
        assert_eq!(process(&dir, &fake, "https://h", "v", 1_000), Outcome::Rejected { error: "invalid_title".into() });
        assert!(dir.join("meta.json").exists(), "process 는 거절 폴더를 스스로 지우지 않는다(창에서 고쳐 보냄)");
        let fake = Fake::new(vec![resp(400, r#"{"error":"invalid_title"}"#)]);
        let v = flush(&ob, &fake, "https://h", "v", 1_000);
        assert_eq!(v["dropped"], json!(1));
        assert!(!dir.exists());
        let _ = std::fs::remove_dir_all(&ob);
    }

    #[test]
    fn flush_waits_for_next_at_and_expires_old_entries() {
        let ob = tmp_outbox("flush");
        let dir = sealed(&ob, 0);
        let mut m = read_meta(&dir).unwrap();
        m.next_at = 5_000;
        write_meta(&dir, &m).unwrap();
        let fake = Fake::new(vec![]);
        assert_eq!(flush(&ob, &fake, "https://h", "v", 4_999)["pending"], json!(1));
        assert!(fake.calls.borrow().is_empty(), "때가 안 된 건을 보내면 안 된다");
        let v = flush(&ob, &fake, "https://h", "v", 1_000 + KEEP_PENDING_SECS + 1);
        assert_eq!(v["dropped"], json!(1));
        assert!(!dir.exists(), "30일 넘은 건은 지운다");
        let _ = std::fs::remove_dir_all(&ob);
    }

    #[test]
    fn backoff_doubles_and_caps() {
        assert_eq!(backoff_secs(0), 60);
        assert_eq!(backoff_secs(1), 120);
        assert_eq!(backoff_secs(3), 480);
        assert_eq!(backoff_secs(30), 6 * 3600);
    }

    #[test]
    fn validate_text_counts_characters_not_bytes() {
        assert_eq!(validate_text(&"가".repeat(TITLE_MAX), "b", ""), Ok(()));
        assert_eq!(validate_text(&"가".repeat(TITLE_MAX + 1), "b", ""), Err("invalid_title".into()));
        assert_eq!(validate_text("  ", "b", ""), Err("invalid_title".into()));
        assert_eq!(validate_text("t", "", ""), Err("invalid_body".into()));
        assert_eq!(validate_text("t", "b", &"x".repeat(CONTACT_MAX + 1)), Err("invalid_contact".into()));
    }

    /// 실제 curl 왕복 스모크 — 계약 흉내 로컬 서버가 있을 때만 돈다(`CYS_FEEDBACK_SMOKE_BASE=http://127.0.0.1:<port>`).
    /// 가짜 전송이 못 재는 축(curl 인자·-K 토큰 헤더·-T 길이·퍼센트 인코딩·응답 코드 판독)을 잰다.
    #[test]
    #[ignore]
    fn smoke_real_curl_against_local_server() {
        let Ok(base) = std::env::var("CYS_FEEDBACK_SMOKE_BASE") else { return };
        let ob = tmp_outbox("smoke");
        let id = new_draft(&ob).unwrap();
        let png = [&b"\x89PNG\r\n\x1a\n"[..], &[0u8; 2000][..]].concat();
        stage_bytes(&ob, &id, "photo", "화면 캡처 1&2.png", &png).unwrap();
        stage_bytes(&ob, &id, "video", "clip.mov", &vec![7u8; 300_000]).unwrap();
        let mut names = serde_json::Map::new();
        names.insert("photo-1.png".into(), json!("화면 캡처 1&2.png"));
        let dir = seal(&ob, &id, "스모크 제목", "줄1\n줄2", "010", &names, now_secs()).unwrap();
        let curl = Curl { app_version: "0.14.37-smoke".into() };
        let first = process(&dir, &curl, &base, &curl.app_version, now_secs());
        eprintln!("SMOKE first={first:?}");
        let out = match first {
            Outcome::Retry { .. } => process(&dir, &curl, &base, &curl.app_version, now_secs()),
            o => o,
        };
        eprintln!("SMOKE final={out:?}");
        assert!(matches!(out, Outcome::Sent { ref dropped, .. } if dropped.is_empty()), "{out:?}");
        assert!(!dir.exists());
        let _ = std::fs::remove_dir_all(&ob);
    }

    /// 한도는 Rust(여기)와 UI(`ui/src/feedback.ts`) 두 곳에 있다 — 한쪽만 바뀌면 창은 받는데 보관함이
    /// 거절하거나 그 반대가 된다. 두 곳의 숫자를 글자로 대조한다.
    #[test]
    fn limits_match_ui_module() {
        let ui = include_str!("../../ui/src/feedback.ts");
        let num = |name: &str| -> u64 {
            let line = ui
                .lines()
                .find(|l| l.starts_with(&format!("export const {name} = ")))
                .unwrap_or_else(|| panic!("UI 에 {name} 선언이 없다"));
            line.split('=').nth(1).unwrap().trim().trim_end_matches(';').replace('_', "").parse().unwrap()
        };
        assert_eq!(num("TITLE_MAX"), TITLE_MAX as u64);
        assert_eq!(num("BODY_MAX"), BODY_MAX as u64);
        assert_eq!(num("CONTACT_MAX"), CONTACT_MAX as u64);
        assert_eq!(num("PHOTO_MAX_BYTES"), PHOTO_MAX_BYTES);
        assert_eq!(num("PHOTO_MAX_COUNT"), PHOTO_MAX_COUNT as u64);
        assert_eq!(num("VIDEO_MAX_BYTES"), VIDEO_MAX_BYTES);
        assert_eq!(num("VIDEO_MAX_COUNT"), VIDEO_MAX_COUNT as u64);
    }
}

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// ★1.1.8 병합(원작자 0.14.43 전체 편입 · 결정 대기 T3) — 원작자 U6(0.14.41) 「피드백 보내기」 1단계 = **휴면**.
//   화면에 배선된 판 = 위 우리 판(2단계 업로드·보관함 재시도·화면 캡처 · 정책 §2-C D-19 동등 = 우리 유지).
//   원작자 판(로컬 묶음 + 메일 앱 + 폴더 열기 · 서버 전송 없음)은 같은 파일 이름(add/add)이라 하위 모듈로 옮겨
//   코드·시험만 보존한다: `#[tauri::command]` 표지를 주석으로 돌려 명령으로 등록하지 않는다(같은 이름
//   `feedback_submit`·`feedback_discard` 가 우리 명령과 겹친다 · ui feedbackmodal.ts 미배선). 원작자 기능의
//   제거·배선은 박사님 게이트(ⓔ) — 여기서는 아무 동작도 하지 않는다. `use super::no_console` → `crate::no_console`.
// ═══════════════════════════════════════════════════════════════════════════════════════════════
#[allow(dead_code, unused_imports)]
pub mod u6_local_bundle {
//! U6(0.14.41) 피드백 1단계 — **이 컴퓨터에 묶음 만들기 + 메일 앱 열기 + 폴더 열기**.
//!
//! 흐름: 작성 창(ui/src/feedbackmodal.ts) → 초안 폴더 `~/.cys/feedback/<id>/` 에 첨부 사본을 바로
//! 쓴다(끌어다 놓기 = OS 경로 복사 · 파일 고르기/붙여넣기 = 원시 IPC 조각) → [메일로 보내기] =
//! `description.txt`·(동의 시)`diag.json`·`manifest.json` 기록 → 묶음 폴더를 열고, 기본 메일 앱을
//! mailto(받는 주소·제목·본문 자동)로 연다. 첨부는 사용자가 폴더에서 메일 창으로 끌어다 넣는다.
//!
//! ★하지 않는 것(설계 §3 U6 · 반박 D1 blocking): 서버 업로드·HTTP 전송·수신 스크립트. 공개 업로드
//!   수신기를 설치 파일과 같은 호스팅 계정에 두면 설치 파일·체크섬 바꿔치기(공급망) 위험이 생긴다 —
//!   격리 호스팅이 정해진 뒤 2단계에서 붙인다.
//! ★피드백 원문은 데몬 RPC·`cys send`·channel inbound·에이전트 큐 어디로도 가지 않는다(①폭주 축 ·
//!   외부 글의 프롬프트 인젝션 차단). 이 모듈에는 데몬 소켓 호출이 없다(ui feedbackwiring 핀).
//! ★진단은 앱 안 경량 정보만 — `cys doctor` 를 돌리지 않는다(반박 M5: 런타임 전수 해시·손자 고아).
//! ★자식 프로세스(open/explorer/xdg-open)는 전부 `no_console` 창 정책을 건다(윈도우 검은 창 0) —
//!   explorer 는 GUI 서브시스템이라 플래그가 무시되지만, 스폰 지점마다 정책을 명시한다는 규약을 따른다.
//! ★저장 위치 `~/.cys/feedback` 은 완전 초기화 인벤토리(src/factory_reset.rs CYS_BASE_EXACT2)에 있다.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use crate::no_console;

/// 받는 주소 — README.md(문의)·SECURITY.md 의 공식 연락 주소. **이 상수 한 곳에만** 둔다
/// (UI 는 묶음 보고의 `to` 로 받는다 · ui/src/feedbackwiring.test.ts 가 두 문서와 대조).
pub const FEEDBACK_TO: &str = "cysinsight@gmail.com";

// 상한 — UI(ui/src/feedback.ts)가 먼저 알려 주고 여기서 다시 강제한다(값 파리티는 feedback.test.ts).
const MAX_FILES: usize = 10;
const MAX_FILE_BYTES: u64 = 200 * 1024 * 1024;
const MAX_TOTAL_BYTES: u64 = 300 * 1024 * 1024;
const MIN_DESC_CHARS: usize = 5;
const MAX_DESC_CHARS: usize = 10_000;
/// 원시 IPC 조각 하나의 상한(UI 는 4MB 로 보낸다 — 두 배 여유).
const MAX_CHUNK_BYTES: usize = 8 * 1024 * 1024;
/// 사진·영상·텍스트만. 실행형·스크립트·SVG(스크립트 포함 가능)는 받지 않는다.
const ALLOWED_EXT: [&str; 13] = [
    "png", "jpg", "jpeg", "gif", "webp", "heic", "mov", "mp4", "m4v", "webm", "txt", "log", "json",
];
/// mailto 전체 길이 상한. 윈도우 셸의 URL 처리(약 2,048자)에 맞춰 보수적으로, 맥·리눅스는 넉넉히.
/// 넘치면 설명을 줄이고 "전체 내용은 첨부 description.txt" 로 안내한다(build_mailto).
#[cfg(windows)]
const MAILTO_MAX: usize = 2000;
#[cfg(not(windows))]
const MAILTO_MAX: usize = 8000;

const DESC_FILE: &str = "description.txt";
const DIAG_FILE: &str = "diag.json";
const MANIFEST_FILE: &str = "manifest.json";
const PART_SUFFIX: &str = ".part";

/// 묶음 폴더를 바꾸는 작업(첨부·삭제·기록·버리기)은 한 번에 하나 — 칸 번호 배정·합계 상한이
/// 동시 호출로 어긋나지 않게. UI 도 첨부를 한 줄로 세우지만 여기가 최종 방어다.
static FB_LOCK: Mutex<()> = Mutex::new(());

fn lock() -> std::sync::MutexGuard<'static, ()> {
    // 앞선 작업이 패닉했더라도 파일 상태는 매 호출 디스크에서 다시 읽으므로 이어서 쓴다.
    FB_LOCK.lock().unwrap_or_else(|p| p.into_inner())
}

fn feedback_root() -> PathBuf {
    cys::home_dir().join(".cys").join("feedback")
}

// ── 이름 규칙(경로 조작 차단) ───────────────────────────────────────────────

/// 묶음 번호 `fb-YYYYMMDD-HHMMSS-xxxx`(xxxx = 소문자 16진 4자리)만 통과 — `..`·구분자·절대경로 차단.
fn valid_id(id: &str) -> bool {
    let b = id.as_bytes();
    b.len() == 23
        && id.starts_with("fb-")
        && b[11] == b'-'
        && b[18] == b'-'
        && b[3..11].iter().all(u8::is_ascii_digit)
        && b[12..18].iter().all(u8::is_ascii_digit)
        && b[19..].iter().all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(c))
}

/// 1970-01-01 기준 일수 → (연, 월, 일). H. Hinnant civil_from_days(외부 크레이트 의존 없음).
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

fn utc_parts(secs: u64) -> (i64, u32, u32, u32, u32, u32) {
    let days = (secs / 86_400) as i64;
    let rem = secs % 86_400;
    let (y, m, d) = civil_from_days(days);
    (y, m, d, (rem / 3600) as u32, ((rem % 3600) / 60) as u32, (rem % 60) as u32)
}

fn iso_utc(secs: u64) -> String {
    let (y, m, d, hh, mm, ss) = utc_parts(secs);
    format!("{y:04}-{m:02}-{d:02}T{hh:02}:{mm:02}:{ss:02}Z")
}

fn new_id(secs: u64, salt: u64) -> String {
    let (y, m, d, hh, mm, ss) = utc_parts(secs);
    format!("fb-{y:04}{m:02}{d:02}-{hh:02}{mm:02}{ss:02}-{:04x}", salt & 0xffff)
}

fn now_secs_nanos() -> (u64, u64) {
    let d = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    (d.as_secs(), d.subsec_nanos() as u64)
}

/// 이름의 마지막 구성요소(맥 `/`·윈도우 `\` 둘 다 구분자로 본다 — UI extOf 와 같은 규칙).
fn last_component(name: &str) -> &str {
    name.rsplit(['/', '\\']).next().unwrap_or(name)
}

/// 허용 확장자(소문자)면 Some. 점으로 시작하는 이름·확장자 없는 이름은 None.
fn allowed_ext_of(name: &str) -> Option<String> {
    let base = last_component(name);
    let (stem, ext) = base.rsplit_once('.')?;
    if stem.is_empty() || ext.is_empty() {
        return None;
    }
    let e = ext.to_ascii_lowercase();
    ALLOWED_EXT.contains(&e.as_str()).then_some(e)
}

fn kind_of(ext: &str) -> &'static str {
    match ext {
        "mov" | "mp4" | "m4v" | "webm" => "video",
        "txt" | "log" | "json" => "text",
        _ => "image",
    }
}

/// 저장 이름 `att-NN.ext`(NN = 01..99). 원래 이름은 manifest 에만 남긴다 — 윈도우 예약어(CON·NUL)·
/// 구분자·긴 이름·유니코드 정규화 차이가 파일 시스템에 닿지 않게.
fn stored_name(index: u32, ext: &str) -> String {
    format!("att-{index:02}.{ext}")
}

/// `att-NN.ext` 또는 `att-NN.ext.part` 를 해석 → (번호, 확장자, 진행 중 여부). 그 밖은 None.
fn parse_att_name(name: &str) -> Option<(u32, String, bool)> {
    let (core, part) = match name.strip_suffix(PART_SUFFIX) {
        Some(c) => (c, true),
        None => (name, false),
    };
    let rest = core.strip_prefix("att-")?;
    let (num, ext) = rest.split_once('.')?;
    if num.len() != 2 || !num.bytes().all(|c| c.is_ascii_digit()) {
        return None;
    }
    let n: u32 = num.parse().ok()?;
    if n == 0 || !ALLOWED_EXT.contains(&ext) {
        return None;
    }
    Some((n, ext.to_string(), part))
}

/// manifest 용 원래 이름 — 마지막 구성요소만, 제어문자 제거, 200자 상한.
fn display_name(original: &str) -> String {
    let s: String = last_component(original).chars().filter(|c| !c.is_control()).collect();
    let s = s.trim();
    if s.is_empty() {
        "(이름 없음)".to_string()
    } else {
        s.chars().take(200).collect()
    }
}

fn bundle_dir(root: &Path, id: &str) -> Result<PathBuf, String> {
    if !valid_id(id) {
        return Err("잘못된 묶음 번호입니다.".into());
    }
    let d = root.join(id);
    let m = std::fs::symlink_metadata(&d).map_err(|_| "묶음 폴더가 없습니다.".to_string())?;
    if !m.file_type().is_dir() {
        return Err("묶음 폴더가 아닙니다.".into());
    }
    Ok(d)
}

// ── 첨부 ────────────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct AttachInfo {
    /// 묶음 폴더 안 저장 이름(`att-01.png`).
    pub name: String,
    /// 사용자가 넣은 원래 이름(표시용).
    pub original: String,
    pub size: u64,
    /// image | video | text
    pub kind: String,
}

struct Tally {
    finals: Vec<(String, u64)>,
    parts: Vec<String>,
    used: Vec<u32>,
}

impl Tally {
    fn total(&self) -> u64 {
        self.finals.iter().map(|(_, s)| *s).sum()
    }
    fn next_index(&self) -> Option<u32> {
        (1..=99).find(|i| !self.used.contains(i))
    }
}

fn tally(dir: &Path) -> Result<Tally, String> {
    let mut t = Tally { finals: Vec::new(), parts: Vec::new(), used: Vec::new() };
    let rd = std::fs::read_dir(dir).map_err(|e| format!("묶음 폴더를 읽지 못했습니다: {e}"))?;
    for ent in rd.flatten() {
        let name = ent.file_name().to_string_lossy().into_owned();
        if let Some((n, _, part)) = parse_att_name(&name) {
            t.used.push(n);
            if part {
                t.parts.push(name);
            } else {
                let size = ent.metadata().map(|m| m.len()).unwrap_or(0);
                t.finals.push((name, size));
            }
        }
    }
    t.finals.sort();
    Ok(t)
}

/// 한 번에 하나만 올리는 규약이라, 새 첨부를 시작할 때 남은 `.part` 는 중단된 이전 전송의 찌꺼기다.
fn sweep_parts(dir: &Path, t: &mut Tally) {
    for p in t.parts.drain(..) {
        let _ = std::fs::remove_file(dir.join(&p));
        if let Some((n, _, _)) = parse_att_name(&p) {
            t.used.retain(|u| *u != n);
        }
    }
}

/// 더해도 되는가(개수·파일·합계 상한). 사람이 읽는 이유를 돌려준다.
fn check_limits(t: &Tally, size: u64) -> Result<(), String> {
    if size == 0 {
        return Err("빈 파일은 첨부할 수 없습니다.".into());
    }
    if size > MAX_FILE_BYTES {
        return Err("파일 하나는 200MB까지입니다.".into());
    }
    if t.finals.len() >= MAX_FILES {
        return Err(format!("첨부는 {MAX_FILES}개까지입니다."));
    }
    if t.total() + size > MAX_TOTAL_BYTES {
        return Err("첨부 합계는 300MB까지입니다.".into());
    }
    Ok(())
}

fn ext_or_reject(original: &str) -> Result<String, String> {
    allowed_ext_of(original).ok_or_else(|| {
        let base = last_component(original);
        let ext = base.rsplit_once('.').map(|(_, e)| e).unwrap_or("");
        if ext.is_empty() {
            "확장자 없는 파일은 첨부할 수 없습니다 — 사진·영상·텍스트(로그)만 받습니다.".to_string()
        } else {
            format!(".{ext} 파일은 첨부할 수 없습니다 — 사진·영상·텍스트(로그)만 받습니다.")
        }
    })
}

fn create_draft_in(root: &Path) -> Result<String, String> {
    std::fs::create_dir_all(root).map_err(|e| format!("피드백 폴더를 만들지 못했습니다: {e}"))?;
    let (secs, nanos) = now_secs_nanos();
    let pid = std::process::id() as u64;
    for attempt in 0..8u64 {
        let salt = nanos ^ (pid << 7) ^ attempt.wrapping_mul(0x9e37);
        let id = new_id(secs, salt);
        match std::fs::create_dir(root.join(&id)) {
            Ok(()) => return Ok(id),
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(e) => return Err(format!("묶음 폴더를 만들지 못했습니다: {e}")),
        }
    }
    Err("묶음 폴더를 만들지 못했습니다(이름 충돌).".into())
}

/// 끌어다 놓은 파일(OS 경로)을 묶음으로 복사한다. 복사 중 중단돼도 `.part` 만 남는다.
fn attach_path_in(root: &Path, id: &str, src: &str) -> Result<AttachInfo, String> {
    let _g = lock();
    let dir = bundle_dir(root, id)?;
    let meta = std::fs::metadata(src).map_err(|e| format!("파일을 읽지 못했습니다: {e}"))?;
    if meta.is_dir() {
        return Err("폴더는 첨부할 수 없습니다 — 파일을 넣어 주세요.".into());
    }
    if !meta.is_file() {
        return Err("일반 파일만 첨부할 수 있습니다.".into());
    }
    let ext = ext_or_reject(src)?;
    let mut t = tally(&dir)?;
    sweep_parts(&dir, &mut t);
    check_limits(&t, meta.len())?;
    let idx = t.next_index().ok_or("첨부 칸이 가득 찼습니다.")?;
    let name = stored_name(idx, &ext);
    let part = dir.join(format!("{name}{PART_SUFFIX}"));
    let copied = std::fs::copy(src, &part).map_err(|e| {
        let _ = std::fs::remove_file(&part);
        format!("파일을 복사하지 못했습니다: {e}")
    })?;
    std::fs::rename(&part, dir.join(&name)).map_err(|e| {
        let _ = std::fs::remove_file(&part);
        format!("파일을 저장하지 못했습니다: {e}")
    })?;
    Ok(AttachInfo { name, original: display_name(src), size: copied, kind: kind_of(&ext).into() })
}

/// 파일 고르기·붙여넣기 전송 시작 — 형식·상한을 먼저 보고 `.part` 칸을 예약한다. 반환 = 저장 이름.
fn attach_begin_in(root: &Path, id: &str, original: &str, size: u64) -> Result<String, String> {
    let _g = lock();
    let dir = bundle_dir(root, id)?;
    let ext = ext_or_reject(original)?;
    let mut t = tally(&dir)?;
    sweep_parts(&dir, &mut t);
    check_limits(&t, size)?;
    let idx = t.next_index().ok_or("첨부 칸이 가득 찼습니다.")?;
    let name = stored_name(idx, &ext);
    std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(dir.join(format!("{name}{PART_SUFFIX}")))
        .map_err(|e| format!("첨부 칸을 만들지 못했습니다: {e}"))?;
    Ok(name)
}

/// 조각 이어쓰기 — offset 이 지금 길이와 같아야 한다(빈틈·겹침 금지). 반환 = 새 길이.
fn attach_chunk_in(root: &Path, id: &str, slot: &str, offset: u64, data: &[u8]) -> Result<u64, String> {
    let _g = lock();
    let dir = bundle_dir(root, id)?;
    match parse_att_name(slot) {
        Some((_, _, false)) => {}
        _ => return Err("잘못된 첨부 이름입니다.".into()),
    }
    if data.len() > MAX_CHUNK_BYTES {
        return Err("조각이 너무 큽니다.".into());
    }
    let part = dir.join(format!("{slot}{PART_SUFFIX}"));
    let cur = std::fs::metadata(&part)
        .map_err(|_| "전송이 끊겼습니다 — 다시 넣어 주세요.".to_string())?
        .len();
    if cur != offset {
        return Err(format!("전송 순서가 어긋났습니다(기대 {cur}, 받은 {offset})."));
    }
    let new_len = cur + data.len() as u64;
    let t = tally(&dir)?;
    if new_len > MAX_FILE_BYTES || t.total() + new_len > MAX_TOTAL_BYTES {
        let _ = std::fs::remove_file(&part);
        return Err("첨부 상한(파일 200MB · 합계 300MB)을 넘었습니다.".into());
    }
    let mut f = std::fs::OpenOptions::new()
        .append(true)
        .open(&part)
        .map_err(|e| format!("첨부를 쓰지 못했습니다: {e}"))?;
    f.write_all(data).map_err(|e| format!("첨부를 쓰지 못했습니다: {e}"))?;
    Ok(new_len)
}

/// 전송 마무리 — 받은 길이가 선언한 크기와 같을 때만 `.part` → 최종 이름.
fn attach_commit_in(root: &Path, id: &str, slot: &str, size: u64, original: &str) -> Result<AttachInfo, String> {
    let _g = lock();
    let dir = bundle_dir(root, id)?;
    let ext = match parse_att_name(slot) {
        Some((_, e, false)) => e,
        _ => return Err("잘못된 첨부 이름입니다.".into()),
    };
    let part = dir.join(format!("{slot}{PART_SUFFIX}"));
    let got = std::fs::metadata(&part).map_err(|_| "전송이 끊겼습니다 — 다시 넣어 주세요.".to_string())?.len();
    if got != size || size == 0 {
        let _ = std::fs::remove_file(&part);
        return Err(format!("받은 크기가 맞지 않습니다({got} / {size}) — 다시 넣어 주세요."));
    }
    std::fs::rename(&part, dir.join(slot)).map_err(|e| format!("첨부를 저장하지 못했습니다: {e}"))?;
    Ok(AttachInfo { name: slot.to_string(), original: display_name(original), size, kind: kind_of(&ext).into() })
}

/// 첨부 하나 빼기(최종 파일 또는 진행 중 `.part`).
fn detach_in(root: &Path, id: &str, name: &str) -> Result<(), String> {
    let _g = lock();
    let dir = bundle_dir(root, id)?;
    if parse_att_name(name).is_none() {
        return Err("잘못된 첨부 이름입니다.".into());
    }
    match std::fs::remove_file(dir.join(name)) {
        Ok(()) => Ok(()),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(e) => Err(format!("첨부를 빼지 못했습니다: {e}")),
    }
}

/// 작성 창을 버릴 때 초안 폴더 삭제. **이미 만든 묶음(manifest 있음)은 지우지 않는다**
/// — 사용자가 아직 메일에 첨부하지 않았을 수 있다.
fn discard_in(root: &Path, id: &str) -> Result<(), String> {
    let _g = lock();
    let dir = bundle_dir(root, id)?;
    if dir.join(MANIFEST_FILE).exists() {
        return Err("이미 만든 묶음은 지우지 않습니다.".into());
    }
    std::fs::remove_dir_all(&dir).map_err(|e| format!("초안을 지우지 못했습니다: {e}"))
}

// ── 진단(동의 시) ───────────────────────────────────────────────────────

/// UI 가 아는 경량 사실(모두 선택 표시용). 문자열은 길이 상한으로 자른다.
#[derive(Deserialize, Debug, Clone, Default)]
pub struct DiagFacts {
    #[serde(default)]
    pub user_agent: String,
    #[serde(default)]
    pub daemon: String,
    #[serde(default)]
    pub daemon_version: Option<String>,
    #[serde(default)]
    pub workspaces: u32,
    #[serde(default)]
    pub panes: u32,
}

fn clip(s: &str, n: usize) -> String {
    s.chars().filter(|c| !c.is_control()).take(n).collect()
}

/// 홈 경로 접두 → `~` (ASCII 대소문자 무시 — 윈도우 경로는 대소문자 무관). 뒤가 경로 끝(구분자·
/// 문자열 끝·구분 문자)일 때만 바꾼다 — 홈이 "/Users/user"면 남의 "/Users/userx"를 먹지 않는다.
fn replace_home_ci(hay: &str, home: &str) -> String {
    if home.is_empty() {
        return hay.to_string();
    }
    // ASCII 소문자화는 바이트 길이를 바꾸지 않으므로 두 문자열의 위치가 그대로 대응한다.
    let lh = hay.to_ascii_lowercase();
    let ln = home.to_ascii_lowercase();
    let mut out = String::with_capacity(hay.len());
    let mut i = 0;
    while let Some(p) = lh[i..].find(&ln) {
        let s = i + p;
        let e = s + ln.len();
        let boundary = hay[e..].chars().next().is_none_or(is_seg_end);
        out.push_str(&hay[i..s]);
        if boundary {
            out.push('~');
        } else {
            out.push_str(&hay[s..e]);
        }
        i = e;
    }
    out.push_str(&hay[i..]);
    out
}

fn is_seg_end(c: char) -> bool {
    matches!(c, '/' | '\\' | '"' | '\'' | ':' | ';' | ',') || c.is_whitespace()
}

/// `marker` 뒤 `n` 개 경로 구성요소를 `with` 로 바꾼다(대소문자 무시).
fn redact_after(s: &str, marker: &str, n: usize, with: &str) -> String {
    let lower = s.to_ascii_lowercase();
    let mut out = String::with_capacity(s.len());
    let mut i = 0;
    while let Some(p) = lower[i..].find(marker) {
        let start = i + p + marker.len();
        out.push_str(&s[i..start]);
        let mut j = start;
        for k in 0..n {
            let seg_len = s[j..].find(is_seg_end).unwrap_or(s.len() - j);
            j += seg_len;
            if k + 1 < n && s[j..].starts_with(['/', '\\']) {
                j += 1;
            } else {
                break;
            }
        }
        if s[start..j].starts_with('<') || start == j {
            out.push_str(&s[start..j]);
        } else {
            out.push_str(with);
        }
        i = j;
    }
    out.push_str(&s[i..]);
    out
}

fn redact_emails(s: &str) -> String {
    let chars: Vec<char> = s.chars().collect();
    let local = |c: char| c.is_ascii_alphanumeric() || "._%+-".contains(c);
    let domain = |c: char| c.is_ascii_alphanumeric() || ".-".contains(c);
    let mut out = String::with_capacity(s.len());
    let mut i = 0;
    while i < chars.len() {
        if chars[i] == '@' {
            let mut a = i;
            while a > 0 && local(chars[a - 1]) {
                a -= 1;
            }
            let mut b = i + 1;
            while b < chars.len() && domain(chars[b]) {
                b += 1;
            }
            let dom: String = chars[i + 1..b].iter().collect();
            let dom = dom.trim_end_matches('.');
            let tld_ok = dom
                .rsplit_once('.')
                .is_some_and(|(h, t)| !h.is_empty() && t.len() >= 2 && t.chars().all(|c| c.is_ascii_alphabetic()));
            if a < i && tld_ok {
                // 이미 out 에 들어간 로컬 부분을 걷어 낸다.
                let drop = i - a;
                for _ in 0..drop {
                    out.pop();
                }
                out.push_str("<email>");
                i = i + 1 + dom.chars().count();
                continue;
            }
        }
        out.push(chars[i]);
        i += 1;
    }
    out
}

/// 진단 문자열 가림 — 홈 경로 접두 → `~`, 사용자 폴더 이름 → `<user>`, macOS 임시 폴더 → `<tmp>`,
/// 이메일 → `<email>`. ★JSON **원문 텍스트**가 아니라 **파싱된 문자열 값**에 적용한다(반박 D7:
/// 원문에서는 윈도우 경로가 `C:\\Users\\` 로 이스케이프돼 가림을 빠져나간다). 채널 아웃바운드
/// 가림(cysd channels.rs V6)과는 목적이 달라 공유하지 않는다(그쪽은 경로 전체를 삼킨다).
fn redact_text(s: &str, home: &str) -> String {
    let mut out = s.to_string();
    let home = home.trim_end_matches(['/', '\\']);
    if home.chars().count() >= 3 {
        for h in [home.to_string(), home.replace('\\', "/"), home.replace('/', "\\")] {
            out = replace_home_ci(&out, &h);
        }
    }
    out = redact_after(&out, "/users/", 1, "<user>");
    out = redact_after(&out, "\\users\\", 1, "<user>");
    out = redact_after(&out, "/home/", 1, "<user>");
    out = redact_after(&out, "/var/folders/", 2, "<tmp>");
    redact_emails(&out)
}

fn redact_value(v: &mut Value, home: &str) {
    match v {
        Value::String(s) => *s = redact_text(s, home),
        Value::Array(a) => a.iter_mut().for_each(|x| redact_value(x, home)),
        Value::Object(o) => o.values_mut().for_each(|x| redact_value(x, home)),
        _ => {}
    }
}

fn pack_version() -> Option<String> {
    std::fs::read_to_string(cys::pack::pack_dir().join(".pack-version"))
        .ok()
        .map(|s| clip(s.trim(), 64))
        .filter(|s| !s.is_empty())
}

/// 진단 JSON(가림 적용 후 · 보기 좋게). 같은 입력이면 같은 바이트 — [보낼 내용 보기]에 보인 것이
/// 곧 저장되는 것이다(시각은 manifest 에만 둔다).
fn build_diag(facts: &DiagFacts, app_version: &str, pack: Option<String>, home: &str) -> String {
    let mut v = json!({
        "schema": 1,
        "app_version": clip(app_version, 64),
        "pack_version": pack,
        "os": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "user_agent": clip(&facts.user_agent, 512),
        "daemon": clip(&facts.daemon, 64),
        "daemon_version": facts.daemon_version.as_deref().map(|s| clip(s, 64)),
        "workspaces": facts.workspaces,
        "panes": facts.panes,
    });
    redact_value(&mut v, home);
    serde_json::to_string_pretty(&v).unwrap_or_else(|_| "{}".into())
}

// ── 묶음 기록 ───────────────────────────────────────────────────────────

#[derive(Deserialize, Debug, Clone)]
pub struct OriginalName {
    pub name: String,
    pub original: String,
}

#[derive(Serialize, Debug, Clone)]
pub struct BundleReport {
    pub id: String,
    /// 묶음 폴더(표시용 — 홈은 `~` 로 줄인다).
    pub folder: String,
    pub to: String,
    pub subject: String,
    pub attachments: Vec<AttachInfo>,
    pub total_bytes: u64,
    pub include_diag: bool,
    /// macOS 에 Mail 앱이 있어 [Mail 앱에 첨부해 열기]를 보여 줄 수 있는가.
    pub mail_app: bool,
}

fn desc_chars(s: &str) -> usize {
    s.trim().chars().count()
}

fn first_line_summary(desc: &str) -> String {
    let line = desc.trim().lines().next().unwrap_or("").trim();
    let s: String = line.chars().filter(|c| !c.is_control()).take(40).collect();
    if line.chars().count() > 40 {
        format!("{s}…")
    } else {
        s
    }
}

fn subject_for(id: &str, desc: &str) -> String {
    let head = first_line_summary(desc);
    if head.is_empty() {
        format!("[cys 피드백] {id}")
    } else {
        format!("[cys 피드백] {id} — {head}")
    }
}

fn tilde_folder(id: &str) -> String {
    format!("~/.cys/feedback/{id}")
}

#[allow(clippy::too_many_arguments)]
fn submit_in(
    root: &Path,
    id: &str,
    description: &str,
    include_diag: bool,
    diag_json: Option<String>,
    originals: &[OriginalName],
    app_version: &str,
    now_secs: u64,
) -> Result<BundleReport, String> {
    let _g = lock();
    let dir = bundle_dir(root, id)?;
    let n = desc_chars(description);
    if n < MIN_DESC_CHARS {
        return Err(format!("무엇이 있었는지 {MIN_DESC_CHARS}자 이상 적어 주세요."));
    }
    if n > MAX_DESC_CHARS {
        return Err(format!("설명은 {MAX_DESC_CHARS}자까지입니다."));
    }
    let mut t = tally(&dir)?;
    sweep_parts(&dir, &mut t);
    let attachments: Vec<AttachInfo> = t
        .finals
        .iter()
        .map(|(name, size)| {
            let ext = parse_att_name(name).map(|(_, e, _)| e).unwrap_or_default();
            let original = originals
                .iter()
                .find(|o| o.name == *name)
                .map(|o| display_name(&o.original))
                .unwrap_or_else(|| name.clone());
            AttachInfo { name: name.clone(), original, size: *size, kind: kind_of(&ext).into() }
        })
        .collect();
    let write = |file: &str, body: &str| -> Result<(), String> {
        let tmp = dir.join(format!("{file}.tmp"));
        std::fs::write(&tmp, body.as_bytes()).map_err(|e| format!("{file} 를 쓰지 못했습니다: {e}"))?;
        std::fs::rename(&tmp, dir.join(file)).map_err(|e| format!("{file} 를 쓰지 못했습니다: {e}"))
    };
    let desc = description.trim().replace("\r\n", "\n");
    write(DESC_FILE, &format!("{desc}\n"))?;
    let diag_path = dir.join(DIAG_FILE);
    let include_diag = include_diag && diag_json.is_some();
    match (include_diag, diag_json) {
        (true, Some(d)) => write(DIAG_FILE, &format!("{d}\n"))?,
        _ => {
            let _ = std::fs::remove_file(&diag_path);
        }
    }
    let subject = subject_for(id, &desc);
    let manifest = json!({
        "schema": 1,
        "id": id,
        "created_at": iso_utc(now_secs),
        "app_version": clip(app_version, 64),
        "to": FEEDBACK_TO,
        "subject": subject,
        "include_diag": include_diag,
        "description_chars": n,
        "attachments": attachments,
    });
    // manifest 가 **마지막**이다 — 이 파일이 있으면 묶음이 완성됐다는 표지(버리기 거부 기준).
    write(MANIFEST_FILE, &serde_json::to_string_pretty(&manifest).unwrap_or_else(|_| "{}".into()))?;
    Ok(BundleReport {
        id: id.to_string(),
        folder: tilde_folder(id),
        to: FEEDBACK_TO.to_string(),
        subject,
        total_bytes: attachments.iter().map(|a| a.size).sum(),
        attachments,
        include_diag,
        mail_app: mail_app_available(),
    })
}

// ── 메일(mailto) ────────────────────────────────────────────────────────

/// RFC 3986 unreserved 만 남기고 전부 %XX(UTF-8 바이트). 줄바꿈은 호출 전에 CRLF 로 맞춘다(RFC 6068).
fn pct(s: &str) -> String {
    let mut out = String::with_capacity(s.len() * 3);
    for b in s.bytes() {
        if b.is_ascii_alphanumeric() || matches!(b, b'-' | b'.' | b'_' | b'~') {
            out.push(b as char);
        } else {
            out.push_str(&format!("%{b:02X}"));
        }
    }
    out
}

fn crlf(s: &str) -> String {
    s.replace("\r\n", "\n").replace('\r', "\n").replace('\n', "\r\n")
}

fn mailto_url(to: &str, subject: &str, body: &str) -> String {
    format!("mailto:{to}?subject={}&body={}", pct(&crlf(subject)), pct(&crlf(body)))
}

const TRUNC_NOTE: &str = "\n…(길어서 여기까지만 넣었습니다 — 전체 내용은 첨부 파일 description.txt 에 있습니다)";

fn mail_footer(id: &str, app_version: &str, files: &[String], include_diag: bool) -> String {
    let mut f = format!("\n\n—\n묶음 번호: {id}");
    // ★리뷰1 minor #1: 개인정보 고지("진단 정보 함께 넣기…체크를 끄면 넣지 않습니다")와 본문을 맞춘다 —
    // 진단 동의가 없으면 앱·OS·CPU 줄도 넣지 않는다(고지가 약속하지 않은 값을 몰래 담지 않는다).
    if include_diag {
        f.push_str(&format!(
            "\n앱: cys {} · {} {}",
            clip(app_version, 32),
            std::env::consts::OS,
            std::env::consts::ARCH
        ));
    }
    if !files.is_empty() {
        f.push_str(&format!(
            "\n첨부할 파일: {}\n→ 함께 열린 폴더({})에서 이 메일 창으로 끌어다 넣어 주세요.",
            files.join(", "),
            tilde_folder(id)
        ));
    }
    f
}

/// 받는 주소·제목·본문을 채운 mailto — 전체 길이가 `max` 를 넘으면 설명을 글자 단위로 줄이고
/// description.txt 를 첨부 목록에 더한다. 반환 (url, 줄였는가).
fn build_mailto(
    id: &str,
    subject: &str,
    desc: &str,
    app_version: &str,
    files: &[String],
    include_diag: bool,
    max: usize,
) -> (String, bool) {
    let full = mailto_url(FEEDBACK_TO, subject, &format!("{desc}{}", mail_footer(id, app_version, files, include_diag)));
    if full.len() <= max {
        return (full, false);
    }
    let mut files2 = files.to_vec();
    if !files2.iter().any(|f| f == DESC_FILE) {
        files2.insert(0, DESC_FILE.to_string());
    }
    let footer = mail_footer(id, app_version, &files2, include_diag);
    let chars: Vec<char> = desc.chars().collect();
    let fits = |k: usize| {
        let head: String = chars[..k].iter().collect();
        let u = mailto_url(FEEDBACK_TO, subject, &format!("{head}{TRUNC_NOTE}{footer}"));
        (u.len() <= max).then_some(u)
    };
    // 들어가는 최대 글자 수를 이분 탐색(길이는 글자 수에 대해 단조 증가).
    let (mut lo, mut hi) = (0usize, chars.len());
    let mut best = fits(0);
    if best.is_some() {
        while lo < hi {
            let mid = (lo + hi).div_ceil(2);
            match fits(mid) {
                Some(u) => {
                    best = Some(u);
                    lo = mid;
                }
                None => hi = mid - 1,
            }
        }
    }
    match best {
        Some(u) => (u, true),
        // 꼬리만으로도 넘치는 극단(긴 제목·긴 목록) — 번호만 남긴 최소형.
        None => (mailto_url(FEEDBACK_TO, &format!("[cys 피드백] {id}"), &format!("묶음 번호: {id}")), true),
    }
}

// ── 여는 프로세스(창 정책 · 좀비 회수) ──────────────────────────────────

/// 기본 앱으로 연다 — macOS `open` · 윈도우 `explorer`(셸 파싱 없음 · cmd 메타문자 주입 경로 0) ·
/// 그 밖 `xdg-open`. mailto 는 기본 메일 앱으로, 폴더는 Finder/탐색기로 간다.
fn opener_command(target: &std::ffi::OsStr) -> std::process::Command {
    #[cfg(target_os = "macos")]
    let mut cmd = std::process::Command::new("open");
    #[cfg(windows)]
    let mut cmd = std::process::Command::new("explorer");
    #[cfg(not(any(target_os = "macos", windows)))]
    let mut cmd = std::process::Command::new("xdg-open");
    cmd.arg(target);
    no_console(&mut cmd);
    cmd
}

/// 띄우고 잊는다 — 다만 종료 상태는 별도 스레드가 회수한다(unix 좀비 누적 방지). 재시도 없음.
fn spawn_reaped(mut cmd: std::process::Command) -> Result<(), String> {
    let mut child = cmd.spawn().map_err(|e| format!("열지 못했습니다: {e}"))?;
    std::thread::spawn(move || {
        let _ = child.wait();
    });
    Ok(())
}

#[cfg(target_os = "macos")]
const MAIL_APP_PATHS: [&str; 2] = ["/System/Applications/Mail.app", "/Applications/Mail.app"];

fn mail_app_available() -> bool {
    #[cfg(target_os = "macos")]
    {
        MAIL_APP_PATHS.iter().any(|p| Path::new(p).exists())
    }
    #[cfg(not(target_os = "macos"))]
    {
        false
    }
}

/// 완성된 묶음에서 메일에 붙일 파일 목록(첨부 → 진단 순).
fn bundle_files(dir: &Path) -> Result<Vec<String>, String> {
    let t = tally(dir)?;
    let mut files: Vec<String> = t.finals.into_iter().map(|(n, _)| n).collect();
    if dir.join(DIAG_FILE).exists() {
        files.push(DIAG_FILE.to_string());
    }
    Ok(files)
}

fn completed_bundle(root: &Path, id: &str) -> Result<PathBuf, String> {
    let dir = bundle_dir(root, id)?;
    if !dir.join(MANIFEST_FILE).exists() {
        return Err("아직 묶음을 만들지 않았습니다.".into());
    }
    Ok(dir)
}

fn mailto_for_bundle(root: &Path, id: &str, max: usize) -> Result<String, String> {
    let dir = completed_bundle(root, id)?;
    let desc = std::fs::read_to_string(dir.join(DESC_FILE)).map_err(|e| format!("설명을 읽지 못했습니다: {e}"))?;
    let desc = desc.trim();
    let files = bundle_files(&dir)?;
    // diag.json 존재 = submit_in 이 쓴 최종 include_diag(제출 당시 동의 · 파일 쓰기 성공)의 그물.
    let include_diag = dir.join(DIAG_FILE).exists();
    let (url, _) = build_mailto(id, &subject_for(id, desc), desc, env!("CARGO_PKG_VERSION"), &files, include_diag, max);
    Ok(url)
}

// ── Tauri 커맨드(얇은 층 — 무거운 일은 blocking 풀에서) ─────────────────────
// 동기 커맨드는 메인 스레드에서 돈다 — 200MB 복사가 화면을 멈추지 않게 전부 async + spawn_blocking.

async fn blocking<T: Send + 'static>(f: impl FnOnce() -> Result<T, String> + Send + 'static) -> Result<T, String> {
    tokio::task::spawn_blocking(f).await.map_err(|e| format!("작업 실행 실패: {e}"))?
}

// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_draft_new() -> Result<String, String> {
    blocking(|| create_draft_in(&feedback_root())).await
}

// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_attach_path(id: String, path: String) -> Result<AttachInfo, String> {
    blocking(move || attach_path_in(&feedback_root(), &id, &path)).await
}

// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_attach_begin(id: String, original: String, size: u64) -> Result<String, String> {
    blocking(move || attach_begin_in(&feedback_root(), &id, &original, size)).await
}

/// 원시 IPC(본문 = 바이트) — 헤더 `x-fb-id`·`x-fb-slot`·`x-fb-offset`. JSON·base64 없이 조각을 받는다.
// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_attach_chunk(request: tauri::ipc::Request<'_>) -> Result<u64, String> {
    let tauri::ipc::InvokeBody::Raw(bytes) = request.body() else {
        return Err("첨부 조각 형식이 아닙니다.".into());
    };
    let hdr = |k: &str| -> Option<String> {
        request.headers().get(k).and_then(|v| v.to_str().ok()).map(str::to_string)
    };
    let id = hdr("x-fb-id").ok_or("묶음 번호가 없습니다.")?;
    let slot = hdr("x-fb-slot").ok_or("첨부 이름이 없습니다.")?;
    let offset: u64 = hdr("x-fb-offset")
        .and_then(|s| s.parse().ok())
        .ok_or("전송 위치가 없습니다.")?;
    if bytes.len() > MAX_CHUNK_BYTES {
        return Err("조각이 너무 큽니다.".into());
    }
    let data = bytes.clone();
    blocking(move || attach_chunk_in(&feedback_root(), &id, &slot, offset, &data)).await
}

// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_attach_commit(id: String, slot: String, size: u64, original: String) -> Result<AttachInfo, String> {
    blocking(move || attach_commit_in(&feedback_root(), &id, &slot, size, &original)).await
}

// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_detach(id: String, name: String) -> Result<(), String> {
    blocking(move || detach_in(&feedback_root(), &id, &name)).await
}

// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_discard(id: String) -> Result<(), String> {
    blocking(move || discard_in(&feedback_root(), &id)).await
}

// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_diag_preview(facts: DiagFacts) -> Result<String, String> {
    blocking(move || {
        let home = cys::home_dir().to_string_lossy().into_owned();
        Ok(build_diag(&facts, env!("CARGO_PKG_VERSION"), pack_version(), &home))
    })
    .await
}

// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_submit(
    id: String,
    description: String,
    include_diag: bool,
    facts: Option<DiagFacts>,
    originals: Vec<OriginalName>,
) -> Result<BundleReport, String> {
    blocking(move || {
        let home = cys::home_dir().to_string_lossy().into_owned();
        let diag = if include_diag {
            Some(build_diag(&facts.unwrap_or_default(), env!("CARGO_PKG_VERSION"), pack_version(), &home))
        } else {
            None
        };
        submit_in(
            &feedback_root(),
            &id,
            &description,
            include_diag,
            diag,
            &originals,
            env!("CARGO_PKG_VERSION"),
            now_secs_nanos().0,
        )
    })
    .await
}

/// 기본 메일 앱을 받는 주소·제목·본문 자동으로 연다(mailto). 사용자 행위 1회당 1번 — 재시도 없음.
// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_open_mail(id: String) -> Result<(), String> {
    blocking(move || {
        let url = mailto_for_bundle(&feedback_root(), &id, MAILTO_MAX)?;
        spawn_reaped(opener_command(std::ffi::OsStr::new(&url)))
    })
    .await
}

/// 묶음 폴더를 연다(첨부를 메일 창으로 끌어다 넣도록).
// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_reveal(id: String) -> Result<(), String> {
    blocking(move || {
        let dir = bundle_dir(&feedback_root(), &id)?;
        spawn_reaped(opener_command(dir.as_os_str()))
    })
    .await
}

/// (macOS) Mail 앱 새 메시지에 묶음 파일을 첨부해 연다 — `open -a Mail <파일…>`. 받는 주소·제목은
/// 이 경로로 채울 수 없어(자동화 권한 창 없이 가능한 유일한 첨부 경로) 화면이 안내한다.
/// 실패하면 Err → UI 가 폴더 열기로 떨어진다. 그 밖 OS 는 Err.
// (1.1.8 휴면 — 명령 미등록) #[tauri::command]
pub async fn feedback_open_mail_app(id: String) -> Result<(), String> {
    blocking(move || {
        #[cfg(target_os = "macos")]
        {
            if !mail_app_available() {
                return Err("Mail 앱이 없습니다.".into());
            }
            let dir = completed_bundle(&feedback_root(), &id)?;
            let mut files = bundle_files(&dir)?;
            files.push(DESC_FILE.to_string());
            let mut c = std::process::Command::new("open");
            c.arg("-a").arg("Mail");
            for f in &files {
                c.arg(dir.join(f));
            }
            no_console(&mut c);
            spawn_reaped(c)
        }
        #[cfg(not(target_os = "macos"))]
        {
            let _ = id;
            Err("이 운영체제에서는 지원하지 않습니다.".into())
        }
    })
    .await
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp_root(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!(
            "cys-fb-test-{tag}-{}-{}",
            std::process::id(),
            now_secs_nanos().1
        ));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    fn src_file(root: &Path, name: &str, bytes: &[u8]) -> String {
        let p = root.join("src").join(name);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(&p, bytes).unwrap();
        p.to_string_lossy().into_owned()
    }

    #[test]
    fn id_format_and_path_traversal_rejected() {
        let id = new_id(1_790_163_296, 0xab12);
        assert_eq!(id, "fb-20260923-113456-ab12");
        assert!(valid_id(&id));
        for bad in [
            "",
            "fb-20260923-113456-AB12",
            "fb-20260923-113456-ab1",
            "fb-20260923-113456-ab12/..",
            "../fb-20260923-113456",
            "fb-2026092x-113456-ab12",
            "fb-20260923_113456-ab12",
            "..",
            "/etc",
        ] {
            assert!(!valid_id(bad), "{bad}");
        }
        assert!(valid_id(&new_id(0, 0xffff_ffff)), "salt 는 4자리로 잘린다");
    }

    #[test]
    fn utc_calendar_is_exact() {
        assert_eq!(iso_utc(0), "1970-01-01T00:00:00Z");
        assert_eq!(iso_utc(951_782_400), "2000-02-29T00:00:00Z");
        assert_eq!(iso_utc(1_709_164_800), "2024-02-29T00:00:00Z");
        assert_eq!(iso_utc(1_790_163_296), "2026-09-23T11:34:56Z");
    }

    #[test]
    fn ext_rules_match_ui() {
        assert_eq!(allowed_ext_of("/Users/user/화면 기록.MOV").as_deref(), Some("mov"));
        assert_eq!(allowed_ext_of("C:\\Users\\홍길동\\Pictures\\shot.PNG").as_deref(), Some("png"));
        assert_eq!(allowed_ext_of(".hidden"), None);
        assert_eq!(allowed_ext_of("noext"), None);
        assert_eq!(allowed_ext_of("dir.v2/README"), None);
        for bad in ["a.exe", "a.php", "a.sh", "a.svg", "a.html", "a.command", "a.zip"] {
            assert_eq!(allowed_ext_of(bad), None, "{bad}");
        }
        assert_eq!(kind_of("mov"), "video");
        assert_eq!(kind_of("log"), "text");
        assert_eq!(kind_of("heic"), "image");
    }

    #[test]
    fn stored_names_parse_and_reject_tricks() {
        assert_eq!(stored_name(3, "png"), "att-03.png");
        assert_eq!(parse_att_name("att-03.png"), Some((3, "png".into(), false)));
        assert_eq!(parse_att_name("att-03.mp4.part"), Some((3, "mp4".into(), true)));
        for bad in ["att-3.png", "att-00.png", "att-03.exe", "../att-03.png", "att-03.png/x", "att-ab.png", "diag.json"] {
            assert_eq!(parse_att_name(bad), None, "{bad}");
        }
        assert_eq!(display_name("C:\\Users\\홍길동\\a\u{7}.png"), "a.png");
        assert_eq!(display_name("/tmp/"), "(이름 없음)");
    }

    #[test]
    fn attach_path_copies_into_bundle_with_safe_name() {
        let root = tmp_root("path");
        let id = create_draft_in(&root).unwrap();
        assert!(valid_id(&id));
        let s = src_file(&root, "화면 1.PNG", b"\x89PNGxxxx");
        let a = attach_path_in(&root, &id, &s).unwrap();
        assert_eq!(a.name, "att-01.png");
        assert_eq!(a.original, "화면 1.PNG");
        assert_eq!(a.size, 8);
        assert_eq!(a.kind, "image");
        assert_eq!(std::fs::read(root.join(&id).join("att-01.png")).unwrap(), b"\x89PNGxxxx");
        // 형식·폴더·없는 파일 거부
        let exe = src_file(&root, "setup.exe", b"MZ");
        assert!(attach_path_in(&root, &id, &exe).unwrap_err().contains(".exe"));
        let dir = root.join("src").to_string_lossy().into_owned();
        assert!(attach_path_in(&root, &id, &dir).unwrap_err().contains("폴더"));
        assert!(attach_path_in(&root, &id, "/nonexistent/x.png").is_err());
        // 잘못된 묶음 번호는 파일 시스템에 닿기 전에 거부
        assert!(attach_path_in(&root, "../x", &s).unwrap_err().contains("묶음 번호"));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn limits_count_file_and_total() {
        let root = tmp_root("limits");
        let id = create_draft_in(&root).unwrap();
        let s = src_file(&root, "a.png", b"x");
        for _ in 0..MAX_FILES {
            attach_path_in(&root, &id, &s).unwrap();
        }
        assert!(attach_path_in(&root, &id, &s).unwrap_err().contains("10개"));
        // 파일 하나 상한 — 희소 파일(실제 쓰기 없음)로 경계 확인
        let id2 = create_draft_in(&root).unwrap();
        let big = root.join("src").join("big.mp4");
        std::fs::File::create(&big).unwrap().set_len(MAX_FILE_BYTES + 1).unwrap();
        assert!(attach_path_in(&root, &id2, &big.to_string_lossy()).unwrap_err().contains("200MB"));
        // 합계 상한은 begin 단계에서(선언 크기) 먼저 거른다
        let t = Tally { finals: vec![("att-01.mp4".into(), 250 * 1024 * 1024)], parts: vec![], used: vec![1] };
        assert!(check_limits(&t, 51 * 1024 * 1024).unwrap_err().contains("300MB"));
        assert!(check_limits(&t, 50 * 1024 * 1024).is_ok());
        assert!(check_limits(&t, 0).unwrap_err().contains("빈 파일"));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn chunk_protocol_is_contiguous_and_verified() {
        let root = tmp_root("chunk");
        let id = create_draft_in(&root).unwrap();
        let slot = attach_begin_in(&root, &id, "녹화.mov", 10).unwrap();
        assert_eq!(slot, "att-01.mov");
        assert!(root.join(&id).join("att-01.mov.part").exists());
        assert_eq!(attach_chunk_in(&root, &id, &slot, 0, b"hello").unwrap(), 5);
        // 겹침·빈틈 거부
        assert!(attach_chunk_in(&root, &id, &slot, 0, b"hello").unwrap_err().contains("순서"));
        assert!(attach_chunk_in(&root, &id, &slot, 7, b"hello").is_err());
        assert_eq!(attach_chunk_in(&root, &id, &slot, 5, b"world").unwrap(), 10);
        // 이름 조작 거부
        assert!(attach_chunk_in(&root, &id, "../att-01.mov", 10, b"x").is_err());
        assert!(attach_chunk_in(&root, &id, "att-01.mov.part", 10, b"x").is_err());
        // 선언 크기와 다르면 커밋 거부 + 찌꺼기 제거
        let slot2 = attach_begin_in(&root, &id, "b.png", 4).unwrap();
        attach_chunk_in(&root, &id, &slot2, 0, b"abc").unwrap();
        assert!(attach_commit_in(&root, &id, &slot2, 4, "b.png").is_err());
        assert!(!root.join(&id).join(format!("{slot2}.part")).exists());
        // 정상 커밋
        // (slot2 실패로 예약이 풀렸고, begin 이 첫 전송의 .part 를 찌꺼기로 치웠으므로 다시 시작)
        let slot3 = attach_begin_in(&root, &id, "녹화.mov", 10).unwrap();
        attach_chunk_in(&root, &id, &slot3, 0, b"helloworld").unwrap();
        let a = attach_commit_in(&root, &id, &slot3, 10, "녹화.mov").unwrap();
        assert_eq!(a.kind, "video");
        assert_eq!(std::fs::read(root.join(&id).join(&slot3)).unwrap(), b"helloworld");
        assert!(!root.join(&id).join(format!("{slot3}.part")).exists());
        // 형식 거부는 칸을 만들기 전에
        assert!(attach_begin_in(&root, &id, "x.exe", 3).unwrap_err().contains(".exe"));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn chunk_cannot_grow_past_file_cap() {
        let root = tmp_root("cap");
        let id = create_draft_in(&root).unwrap();
        let slot = attach_begin_in(&root, &id, "v.mp4", MAX_FILE_BYTES).unwrap();
        let part = root.join(&id).join(format!("{slot}.part"));
        std::fs::OpenOptions::new().write(true).open(&part).unwrap().set_len(MAX_FILE_BYTES).unwrap();
        let err = attach_chunk_in(&root, &id, &slot, MAX_FILE_BYTES, b"x").unwrap_err();
        assert!(err.contains("상한"), "{err}");
        assert!(!part.exists(), "넘친 전송의 .part 는 지운다");
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn submit_writes_bundle_and_manifest_last() {
        let root = tmp_root("submit");
        let id = create_draft_in(&root).unwrap();
        let s = src_file(&root, "shot.png", b"png!");
        attach_path_in(&root, &id, &s).unwrap();
        // 중단된 전송 찌꺼기는 묶음에 들어가지 않는다
        std::fs::write(root.join(&id).join("att-02.mov.part"), b"half").unwrap();
        assert!(submit_in(&root, &id, " 짧음 ", false, None, &[], "0.14.41", 0).unwrap_err().contains("5자"));
        let r = submit_in(
            &root,
            &id,
            "  업데이트 뒤 화면이 비어요\r\n두 번째 줄  ",
            true,
            Some("{\"schema\": 1}".into()),
            &[OriginalName { name: "att-01.png".into(), original: "/Users/홍길동/Desktop/shot.png".into() }],
            "0.14.41",
            1_790_163_296,
        )
        .unwrap();
        let dir = root.join(&id);
        assert_eq!(std::fs::read_to_string(dir.join(DESC_FILE)).unwrap(), "업데이트 뒤 화면이 비어요\n두 번째 줄\n");
        assert!(dir.join(DIAG_FILE).exists());
        assert!(!dir.join("att-02.mov.part").exists());
        let m: Value = serde_json::from_str(&std::fs::read_to_string(dir.join(MANIFEST_FILE)).unwrap()).unwrap();
        assert_eq!(m["id"], id.as_str());
        assert_eq!(m["to"], FEEDBACK_TO);
        assert_eq!(m["created_at"], "2026-09-23T11:34:56Z");
        assert_eq!(m["attachments"][0]["original"], "shot.png", "원래 이름은 마지막 구성요소만(홈 경로 비노출)");
        assert_eq!(r.attachments.len(), 1);
        assert_eq!(r.to, FEEDBACK_TO);
        assert_eq!(r.folder, format!("~/.cys/feedback/{id}"));
        assert!(r.subject.contains(&id) && r.subject.contains("업데이트 뒤 화면이 비어요"));
        assert!(r.include_diag);
        // 진단 동의를 끄고 다시 쓰면 diag.json 이 사라진다
        let r2 = submit_in(&root, &id, "다섯 글자 이상", true, None, &[], "0.14.41", 0).unwrap();
        assert!(!r2.include_diag);
        assert!(!dir.join(DIAG_FILE).exists());
        // 완성된 묶음은 버리기로 지우지 않는다
        assert!(discard_in(&root, &id).unwrap_err().contains("이미"));
        assert!(dir.exists());
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn discard_and_detach_stay_inside_bundle() {
        let root = tmp_root("discard");
        let id = create_draft_in(&root).unwrap();
        let s = src_file(&root, "a.png", b"x");
        attach_path_in(&root, &id, &s).unwrap();
        assert!(detach_in(&root, &id, "../../src/a.png").is_err());
        assert!(detach_in(&root, &id, "manifest.json").is_err());
        detach_in(&root, &id, "att-01.png").unwrap();
        detach_in(&root, &id, "att-01.png").unwrap(); // 멱등
        assert!(discard_in(&root, "..").is_err());
        assert!(discard_in(&root, "fb-20260923-113456-ab12").is_err(), "없는 묶음");
        discard_in(&root, &id).unwrap();
        assert!(!root.join(&id).exists());
        assert!(root.join("src/a.png").exists(), "원본은 건드리지 않는다");
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn mailto_is_encoded_bounded_and_truncates_with_notice() {
        let id = "fb-20260923-113456-ab12";
        let files = vec!["att-01.png".to_string(), DIAG_FILE.to_string()];
        let (u, cut) = build_mailto(id, "[cys 피드백] 제목 & 기호?", "첫 줄\n둘째 줄 = 100%", "0.14.41", &files, true, 8000);
        assert!(!cut);
        assert!(u.starts_with(&format!("mailto:{FEEDBACK_TO}?subject=")));
        assert!(u.contains("&body="));
        assert_eq!(u.matches('&').count(), 1, "본문의 & 는 인코딩된다");
        assert_eq!(u.matches('?').count(), 1, "본문의 ? 는 인코딩된다");
        assert!(!u.contains(' ') && !u.contains('\n') && !u.contains('\r'));
        assert!(u.contains("%0D%0A"), "줄바꿈은 CRLF(RFC 6068)");
        assert!(u.contains("att-01.png"));
        // 긴 설명(한글 3,000자)은 윈도우 상한 안으로 줄이고 description.txt 를 안내한다
        let long = "가".repeat(3000);
        let (u2, cut2) = build_mailto(id, "[cys 피드백] x", &long, "0.14.41", &files, true, 2000);
        assert!(cut2);
        assert!(u2.len() <= 2000, "{}", u2.len());
        assert!(u2.contains("description.txt"));
        assert!(u2.contains(&pct("가가가")), "앞부분은 남는다");
        // 극단: 상한이 꼬리보다 작아도 최소형으로 떨어진다(패닉·빈 URL 금지)
        let (u3, _) = build_mailto(id, "[cys 피드백] x", &long, "0.14.41", &files, true, 50);
        assert!(u3.starts_with("mailto:") && u3.contains(id));
    }

    #[test]
    fn redaction_applies_to_parsed_values_on_both_platforms() {
        let mut v = json!({
            "mac": "/Users/user/Desktop/CYSjavis/x.log",
            "other_user": "/Users/youruser/Library",
            "win": "C:\\Users\\홍길동\\AppData\\Local\\cys\\boot-supervisor.log",
            "win_fwd": "c:/users/홍길동/AppData",
            "d_drive": "D:\\Users\\runner\\work",
            "linux": "/home/alice/.cys",
            "tmp": "/private/var/folders/38/dn_9t23x39z56tzd_bx80pnh0000gn/T/cys-paste",
            "mail": "문의 someone.name+tag@example.co.kr 로",
            "nested": ["C:\\Users\\홍길동\\x"],
            "keep": "0.14.41 · macos aarch64",
        });
        redact_value(&mut v, "/Users/user");
        let s = serde_json::to_string(&v).unwrap();
        for leak in ["user/Desktop", "youruser", "홍길동", "runner", "alice", "dn_9t23", "someone.name", "example.co.kr"] {
            assert!(!s.contains(leak), "{leak} 가 새어 나갔다: {s}");
        }
        assert_eq!(v["mac"], "~/Desktop/CYSjavis/x.log", "홈 접두는 ~ 로(경로 모양 보존)");
        assert_eq!(v["other_user"], "/Users/<user>/Library");
        assert_eq!(v["win"], "C:\\Users\\<user>\\AppData\\Local\\cys\\boot-supervisor.log");
        assert_eq!(v["tmp"], "/private/var/folders/<tmp>/T/cys-paste");
        assert_eq!(v["mail"], "문의 <email> 로");
        assert_eq!(v["keep"], "0.14.41 · macos aarch64");
        // 윈도우 홈 접두(대소문자·구분자 무관)
        assert_eq!(redact_text("c:/users/홍길동/x", "C:\\Users\\홍길동"), "~/x");
        // 접두 경계 — 홈 이름으로 시작하는 남의 폴더는 ~ 가 아니라 <user>
        assert_eq!(redact_text("/Users/userx/a", "/Users/user"), "/Users/<user>/a");
        assert_eq!(redact_text("/Users/user", "/Users/user/"), "~");
    }

    #[test]
    fn diag_is_deterministic_redacted_and_small() {
        let f = DiagFacts {
            user_agent: "Mozilla/5.0 (Macintosh) /Users/user/leak".into(),
            daemon: "응답함".into(),
            daemon_version: Some("0.14.41".into()),
            workspaces: 3,
            panes: 7,
        };
        let a = build_diag(&f, "0.14.41", Some("0.14.41".into()), "/Users/user");
        let b = build_diag(&f, "0.14.41", Some("0.14.41".into()), "/Users/user");
        assert_eq!(a, b, "미리보기 = 저장본(같은 입력 → 같은 바이트)");
        let v: Value = serde_json::from_str(&a).unwrap();
        assert_eq!(v["workspaces"], 3);
        assert_eq!(v["panes"], 7);
        assert_eq!(v["os"], std::env::consts::OS);
        assert!(!a.contains("/Users/user"));
        assert!(v.get("created_at").is_none(), "시각은 manifest 에만");
        let huge = DiagFacts { user_agent: "x".repeat(5000), ..Default::default() };
        let c = build_diag(&huge, "v", None, "/Users/user");
        assert!(c.len() < 1500, "문자열은 상한으로 자른다");
    }

    #[test]
    fn opener_uses_platform_shell_opener_without_cmd() {
        let c = opener_command(std::ffi::OsStr::new("mailto:x"));
        let prog = c.get_program().to_string_lossy().into_owned();
        #[cfg(target_os = "macos")]
        assert_eq!(prog, "open");
        #[cfg(windows)]
        assert_eq!(prog, "explorer");
        #[cfg(not(any(target_os = "macos", windows)))]
        assert_eq!(prog, "xdg-open");
        let args: Vec<String> = c.get_args().map(|a| a.to_string_lossy().into_owned()).collect();
        assert_eq!(args, vec!["mailto:x".to_string()], "대상 하나만 — 셸·추가 인자 없음");
    }

    /// 리뷰1 minor #1 — 개인정보 고지("(동의하신 경우) 앱·운영체제 버전… 체크를 끄면 넣지 않습니다")와
    /// 실제 메일 본문이 같아야 한다. 진단을 끄면 본문에 앱·OS 줄이 없고, 켜면 있다.
    #[test]
    fn mail_body_env_line_follows_diag_consent() {
        let root = tmp_root("consent");
        let env_line = pct(&format!("앱: cys {} · {} {}", env!("CARGO_PKG_VERSION"), std::env::consts::OS, std::env::consts::ARCH));
        // 끔
        let id = create_draft_in(&root).unwrap();
        submit_in(&root, &id, "진단 없이 보내는 피드백", false, None, &[], "0.14.41", 0).unwrap();
        let off = mailto_for_bundle(&root, &id, 8000).unwrap();
        assert!(off.contains(&pct(&format!("묶음 번호: {id}"))), "묶음 번호는 늘 들어간다");
        assert!(!off.contains(&pct("앱: cys")), "진단을 끄면 앱 버전 줄을 넣지 않는다: {off}");
        assert!(!off.contains(std::env::consts::ARCH), "진단을 끄면 CPU 종류를 넣지 않는다");
        // 켬
        let id2 = create_draft_in(&root).unwrap();
        submit_in(&root, &id2, "진단과 함께 보내는 피드백", true, Some("{\"schema\": 1}".into()), &[], "0.14.41", 0).unwrap();
        let on = mailto_for_bundle(&root, &id2, 8000).unwrap();
        assert!(on.contains(&env_line), "진단을 켜면 앱·OS 줄이 들어간다: {on}");
        assert!(on.contains(DIAG_FILE), "진단 파일을 첨부 목록에 안내한다");
        // 길어서 줄이는 경로도 같은 규칙
        let id3 = create_draft_in(&root).unwrap();
        submit_in(&root, &id3, &"가".repeat(3000), false, None, &[], "0.14.41", 0).unwrap();
        let cut = mailto_for_bundle(&root, &id3, 2000).unwrap();
        assert!(cut.contains("description.txt") && !cut.contains(&pct("앱: cys")), "{cut}");
        let _ = std::fs::remove_dir_all(&root);
    }

    /// 리뷰1 R16 — 묶음 폴더 자리가 심볼릭 링크면(누가 `~/.cys/feedback/<번호>` 를 다른 곳으로 걸어 둠)
    /// 첨부·버리기가 링크 너머 폴더에 쓰거나 지우지 않는다.
    #[cfg(unix)]
    #[test]
    fn bundle_dir_rejects_symlinked_bundle_folder() {
        let root = tmp_root("symlink");
        let outside = root.join("outside");
        std::fs::create_dir_all(&outside).unwrap();
        std::fs::write(outside.join("keep.txt"), b"k").unwrap();
        let id = "fb-20260923-113456-ab12";
        std::os::unix::fs::symlink(&outside, root.join(id)).unwrap();
        let s = src_file(&root, "a.png", b"x");
        assert!(attach_path_in(&root, id, &s).unwrap_err().contains("묶음 폴더가 아닙니다"));
        assert!(attach_begin_in(&root, id, "b.png", 1).unwrap_err().contains("묶음 폴더가 아닙니다"));
        assert!(discard_in(&root, id).unwrap_err().contains("묶음 폴더가 아닙니다"));
        assert!(submit_in(&root, id, "다섯 글자 이상", false, None, &[], "0.14.41", 0).is_err());
        let left: Vec<String> =
            std::fs::read_dir(&outside).unwrap().flatten().map(|e| e.file_name().to_string_lossy().into_owned()).collect();
        assert_eq!(left, vec!["keep.txt".to_string()], "링크 너머에 쓰지도 지우지도 않는다");
        assert!(std::fs::symlink_metadata(root.join(id)).unwrap().file_type().is_symlink(), "링크 자체도 그대로");
        let _ = std::fs::remove_dir_all(&root);
    }

    /// 리뷰1 minor #5 — 결과 화면·메일 꼬리의 폴더 표기는 그 OS 사용자가 알아보는 모양이고, 사용자 이름을 드러내지 않는다.
    #[test]
    fn bundle_folder_display_is_platform_native_and_hides_user() {
        let root = tmp_root("display");
        let id = create_draft_in(&root).unwrap();
        let s = src_file(&root, "a.png", b"x");
        attach_path_in(&root, &id, &s).unwrap();
        let r = submit_in(&root, &id, "폴더 표기 확인용 설명", false, None, &[], "0.14.41", 0).unwrap();
        #[cfg(windows)]
        let want = format!("%USERPROFILE%\\.cys\\feedback\\{id}");
        #[cfg(not(windows))]
        let want = format!("~/.cys/feedback/{id}");
        assert_eq!(r.folder, want);
        let url = mailto_for_bundle(&root, &id, 8000).unwrap();
        assert!(url.contains(&pct(&want)), "메일 꼬리도 같은 표기: {url}");
        let home = cys::home_dir().to_string_lossy().into_owned();
        if home.chars().count() >= 3 {
            assert!(!r.folder.contains(&home) && !url.contains(&pct(&home)), "홈 절대경로(사용자 이름) 비노출");
        }
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn report_shape_is_stable_for_the_ui() {
        let r = BundleReport {
            id: "fb-20260923-113456-ab12".into(),
            folder: "~/.cys/feedback/fb-20260923-113456-ab12".into(),
            to: FEEDBACK_TO.into(),
            subject: "s".into(),
            attachments: vec![AttachInfo { name: "att-01.png".into(), original: "a.png".into(), size: 1, kind: "image".into() }],
            total_bytes: 1,
            include_diag: false,
            mail_app: false,
        };
        let v = serde_json::to_value(&r).unwrap();
        let mut keys: Vec<&str> = v.as_object().unwrap().keys().map(|k| k.as_str()).collect();
        keys.sort_unstable();
        assert_eq!(keys, ["attachments", "folder", "id", "include_diag", "mail_app", "subject", "to", "total_bytes"]);
        let mut ak: Vec<String> = v["attachments"][0].as_object().unwrap().keys().cloned().collect();
        ak.sort();
        assert_eq!(ak, ["kind", "name", "original", "size"]);
    }
}
}
