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

/// 지금 화면(주 모니터)을 사진 한 장으로 초안에 넣는다. 창을 가린 뒤 부르는 것은 UI 몫이다.
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
    stage_bytes(&outbox_dir(), &h("x-draft"), &kind, &h("x-name"), bytes)
}

#[tauri::command]
pub fn feedback_unstage(draft: String, file: String) -> Result<(), String> {
    unstage(&outbox_dir(), &draft, &file)
}

#[tauri::command]
pub fn feedback_discard(draft: String) -> Result<(), String> {
    discard(&outbox_dir(), &draft)
}

#[tauri::command]
pub async fn feedback_capture(draft: String) -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(move || capture_into(&outbox_dir(), &draft))
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
