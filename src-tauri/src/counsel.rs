//! 「상담소」·「아고라」 사이드바 메뉴의 Rust 쪽(1.1.9 T4 · TICKET=cysr-119-t4-app · 설계 docs/design/T4-APP-MENUS-119.md).
//!
//! ★앱은 릴레이에 가지 않는다(아고라 SPEC-mail-1to1 §11) — 망 호출·서명 검증은 아고라 클라이언트(`<설정>/lib/bin/agora`)의 일이고,
//!   앱은 그 클라이언트를 **읽기 동사(`read`)로만** 부르거나, 클라이언트가 쓴 파일을 **읽기만** 한다:
//!   `lib/config/desk-pin.txt`(상담소 핀) · `allowed_signers`(명부) · `participant.json`(내 id) · `mailbox/unread.json`(뱃지) ·
//!   `lib/PACKAGE-MANIFEST.json`(클라이언트 판). 이 모듈은 어느 파일에도 쓰지 않는다.
//! ★「상담소 답」 판별 = 보낸이 id 가 핀의 `desk` id 이고, 명부에 있는 그 id 의 키 지문이 **전부** 핀 지문과 같을 때만(§11 「상담소 판별」).
//!   `agora read` 의 `sig: ok` 는 「그 id 의 명부 키로 서명 검증됨」이라, 명부 키 = 핀 지문이면 보낸이 = 상담소다.
//!   표시명·방 제목으로는 정하지 않는다.

use crate::{inject_runtime_path, BOOT_PY_CANDIDATES};
use cys::SpawnPolicy as _;
use base64::Engine as _;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::io::Read as _;
use std::path::{Path, PathBuf};

/// 상담소 방을 읽을 수 있는 가장 낮은 클라이언트 판 — 0.1.4 는 커뮤니티 방 genesis 의 `budget` 칸을
/// 「계약에 없는 칸」으로 격리해 글이 0건으로 보인다(2026-10-09 실측 · 설계 §0 F2).
const MIN_CLIENT: (u64, u64, u64) = (0, 1, 14);
/// `agora read` 한 쪽 = 64KB 상한(클라이언트 READ_PAGE_BYTES) — 8쪽(≈512KB)까지만 따라간다.
const MAX_PAGES: usize = 8;
/// 한 번 부를 때의 시간 상한(망 지연 · 먹통 클라이언트가 창을 붙잡지 않게).
const READ_TIMEOUT: std::time::Duration = std::time::Duration::from_secs(20);

/// 아고라 설정 폴더 — 환경 `AGORA_CONFIG_DIR`(비어 있지 않으면) · 아니면 `<홈>/.config/agora`
/// (맥 `~/.config/agora` · 윈 `%USERPROFILE%\.config\agora` = 클라이언트 `participant.DEFAULT_DIR` 와 같은 식).
pub(crate) fn config_dir_from(env: Option<&str>, home: &Path) -> PathBuf {
    match env.map(str::trim) {
        Some(v) if !v.is_empty() => PathBuf::from(v),
        _ => home.join(".config").join("agora"),
    }
}

fn config_dir() -> PathBuf {
    config_dir_from(std::env::var("AGORA_CONFIG_DIR").ok().as_deref(), &cys::home_dir())
}

/// 참가자 id 형식(클라이언트·릴레이와 같은 꼴) — 형식 밖 값은 화면에 싣지 않는다.
pub(crate) fn valid_participant_id(s: &str) -> bool {
    (2..=64).contains(&s.len()) && s.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'.' || b == b'_' || b == b'-')
}

fn valid_thread_id(s: &str) -> bool {
    s.len() == 32 && s.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

/// 상담소 핀(`desk-pin.txt`) — `desk <id> <SHA256:지문>` · `room <32hex>` 만 쓴다(모르는 줄·`#` 주석은 버린다).
#[derive(Debug, Default, PartialEq)]
pub(crate) struct DeskPin {
    pub desks: Vec<(String, String)>,
    pub rooms: Vec<String>,
}

pub(crate) fn parse_desk_pin(text: &str) -> DeskPin {
    let mut pin = DeskPin::default();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let t: Vec<&str> = line.split_whitespace().collect();
        match t.as_slice() {
            ["desk", id, fp] if valid_participant_id(id) && fp.starts_with("SHA256:") && fp.len() > 7 => {
                pin.desks.push((id.to_string(), fp.to_string()))
            }
            ["room", tid] if valid_thread_id(tid) => {
                if !pin.rooms.iter().any(|r| r == tid) {
                    pin.rooms.push(tid.to_string())
                }
            }
            _ => {}
        }
    }
    pin
}

/// 명부(`allowed_signers` · OpenSSH 꼴 `주체[,주체] [옵션] 키종류 base64 [주석]`)에서 그 id 의 키 지문 전부(`SHA256:` + 무패딩 base64).
pub(crate) fn roster_fingerprints(roster: &str, id: &str) -> Vec<String> {
    let mut out = Vec::new();
    for line in roster.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let t: Vec<&str> = line.split_whitespace().collect();
        if t.is_empty() || !t[0].split(',').any(|p| p == id) {
            continue;
        }
        let Some(k) = t.iter().position(|w| w.starts_with("ssh-") || w.starts_with("ecdsa-") || w.starts_with("sk-")) else {
            continue;
        };
        let Some(b64) = t.get(k + 1) else { continue };
        let Ok(blob) = base64::engine::general_purpose::STANDARD.decode(b64) else { continue };
        let digest = Sha256::digest(&blob);
        out.push(format!("SHA256:{}", base64::engine::general_purpose::STANDARD_NO_PAD.encode(digest)));
    }
    out
}

/// 핀과 명부가 함께 맞는 상담소 id 들 — 명부에 그 id 줄이 하나 이상이고 **모든** 줄의 지문이 핀 지문과 같을 때만.
/// (한 줄이라도 다르면 그 다른 키로 서명된 글이 `sig: ok` 로 올 수 있으므로 상담소로 보지 않는다.)
pub(crate) fn verified_desk_ids(pin: &DeskPin, roster: &str) -> Vec<String> {
    let mut out = Vec::new();
    for (id, fp) in &pin.desks {
        let fps = roster_fingerprints(roster, id);
        if !fps.is_empty() && fps.iter().all(|f| f == fp) && !out.contains(id) {
            out.push(id.clone());
        }
    }
    out
}

/// `PACKAGE-MANIFEST.json` 의 `version` 이 MIN_CLIENT 이상인가(숫자 마디 비교 · 못 읽으면 아니다).
pub(crate) fn client_version_ok(manifest: &str) -> bool {
    let Ok(v) = serde_json::from_str::<Value>(manifest) else { return false };
    let Some(s) = v.get("version").and_then(Value::as_str) else { return false };
    let parts: Vec<Option<u64>> = s.split('.').map(|p| p.parse::<u64>().ok()).collect();
    match parts.as_slice() {
        [Some(a), Some(b), Some(c)] => (*a, *b, *c) >= MIN_CLIENT,
        _ => false,
    }
}

/// 방 id — 핀의 `room` 줄 우선 · 없으면 클라이언트가 찾아 적어 둔 `counsel/state.json` 의 `room_ids`(§13-2).
pub(crate) fn pick_room(pin: &DeskPin, state_json: Option<&str>) -> Option<String> {
    if let Some(r) = pin.rooms.first() {
        return Some(r.clone());
    }
    let v: Value = serde_json::from_str(state_json?).ok()?;
    v.get("room_ids")?.as_array()?.iter().filter_map(Value::as_str).find(|s| valid_thread_id(s)).map(str::to_string)
}

/// 내 참가자 id — `participant.json` 의 `id`(형식 밖이면 빈 값 = 「내 글」 표식 없음).
pub(crate) fn my_id(participant_json: Option<&str>) -> String {
    participant_json
        .and_then(|s| serde_json::from_str::<Value>(s).ok())
        .and_then(|v| v.get("id").and_then(Value::as_str).map(str::to_string))
        .filter(|s| valid_participant_id(s))
        .unwrap_or_default()
}

/// `agora read` 한 쪽의 JSON → (이벤트, refs, 다음 커서). 형식이 어긋난 행은 버린다(화면에 싣지 않는다).
pub(crate) fn parse_read_page(v: &Value) -> (Vec<Value>, Vec<Value>, Option<String>) {
    let mut events = Vec::new();
    for e in v.get("events").and_then(Value::as_array).into_iter().flatten() {
        let s = |k: &str| e.get(k).and_then(Value::as_str);
        let (Some(id), Some(kind), Some(from), Some(ts)) = (s("message_id"), s("kind"), s("from"), s("ts")) else { continue };
        if !valid_participant_id(from) || e.get("sig").and_then(Value::as_str) != Some("ok") {
            continue;
        }
        let body = e.get("body").and_then(Value::as_str);
        let marker = e.get("untrusted").and_then(|u| u.get("marker")).and_then(Value::as_str);
        events.push(json!({"message_id": id, "kind": kind, "from": from, "ts": ts, "body": body, "marker": marker}));
    }
    let mut refs = Vec::new();
    for r in v.get("refs").and_then(Value::as_array).into_iter().flatten() {
        let s = |k: &str| r.get(k).and_then(Value::as_str);
        let (Some(from_id), Some(tid)) = (s("from_message_id"), s("thread_id")) else { continue };
        refs.push(json!({"from_message_id": from_id, "thread_id": tid, "message_id": s("message_id")}));
    }
    let next = v.get("next_cursor").and_then(Value::as_str).filter(|c| !c.is_empty()).map(str::to_string);
    (events, refs, next)
}

/// 클라이언트 `read` 1회 — 번들 python(inject_runtime_path)으로 `<설정>/lib/bin/agora` 를 부른다(팩 javis_counsel.py 의 호출 꼴과 같다).
/// stdout 은 별도 스레드가 읽는다(64KB 넘는 출력이 파이프를 막아 시간 상한까지 매달리지 않게).
fn run_read(agora: &Path, cfg: &Path, room: &str, cursor: Option<&str>) -> Result<Value, String> {
    let mut last_err = String::new();
    for py in BOOT_PY_CANDIDATES {
        let mut cmd = std::process::Command::new(py);
        inject_runtime_path(&mut cmd);
        cmd.env("AGORA_CONFIG_DIR", cfg);
        cmd.arg(agora).arg("read").arg("--thread_id").arg(room);
        if let Some(c) = cursor {
            cmd.arg("--cursor").arg(c);
        }
        cmd.stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::null());
        // 창 정책 = GUI no_console 과 같은 등급(Attached · 윈도 콘솔 창 숨김) — 인구조사가 이 파일 안에서 판독하도록 직접 건다.
        cmd.spawn_policy(cys::ChildLifetime::Attached);
        let mut child = match cmd.spawn() {
            Ok(c) => c,
            Err(e) => {
                last_err = format!("{py}: {e}");
                continue;
            }
        };
        let mut out = child.stdout.take().ok_or("stdout")?;
        let reader = std::thread::spawn(move || {
            let mut buf = Vec::new();
            let _ = out.read_to_end(&mut buf);
            buf
        });
        let deadline = std::time::Instant::now() + READ_TIMEOUT;
        let status = loop {
            match child.try_wait() {
                Ok(Some(s)) => break s,
                Ok(None) if std::time::Instant::now() < deadline => std::thread::sleep(std::time::Duration::from_millis(50)),
                Ok(None) => {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err("timeout".into());
                }
                Err(e) => return Err(e.to_string()),
            }
        };
        let buf = reader.join().map_err(|_| "reader".to_string())?;
        if !status.success() {
            return Err(format!("agora read rc={:?}", status.code()));
        }
        return serde_json::from_slice(&buf).map_err(|e| format!("json: {e}"));
    }
    Err(format!("python 없음({last_err})"))
}

fn read_opt(p: &Path) -> Option<String> {
    std::fs::read_to_string(p).ok()
}

/// 상담소 방 글 전부(읽기 전용) — 상태: `ok` · `no_client`(클라이언트 없음/0.1.14 미만) · `no_room` · `error`.
/// 정렬·댓글 트리·표식 벗기기는 UI 순수 모듈(counsel.ts)이 한다 — 여기서는 검증된 행만 추려 넘긴다.
pub(crate) fn room_list_at(cfg: &Path) -> Value {
    let lib = cfg.join("lib");
    let agora = lib.join("bin").join("agora");
    if !agora.is_file() || !read_opt(&lib.join("PACKAGE-MANIFEST.json")).is_some_and(|m| client_version_ok(&m)) {
        return json!({"status": "no_client"});
    }
    let pin = parse_desk_pin(&read_opt(&lib.join("config").join("desk-pin.txt")).unwrap_or_default());
    let Some(room) = pick_room(&pin, read_opt(&cfg.join("counsel").join("state.json")).as_deref()) else {
        return json!({"status": "no_room"});
    };
    let desk_ids = verified_desk_ids(&pin, &read_opt(&cfg.join("allowed_signers")).unwrap_or_default());
    let me = my_id(read_opt(&cfg.join("participant.json")).as_deref());
    let (mut events, mut refs) = (Vec::new(), Vec::new());
    let mut cursor: Option<String> = None;
    let mut partial = false;
    for page in 0..MAX_PAGES {
        let v = match run_read(&agora, cfg, &room, cursor.as_deref()) {
            Ok(v) => v,
            Err(e) if page == 0 => return json!({"status": "error", "detail": e}),
            Err(_) => {
                partial = true;
                break;
            }
        };
        let (ev, rf, next) = parse_read_page(&v);
        events.extend(ev);
        refs.extend(rf);
        match next {
            Some(n) if page + 1 < MAX_PAGES => cursor = Some(n),
            Some(_) => partial = true,
            None => break,
        }
    }
    json!({"status": "ok", "room_id": room, "me": me, "desk_ids": desk_ids, "events": events, "refs": refs, "partial": partial})
}

/// UI 명령 — 클라이언트 호출(망)이 있으므로 블로킹 스레드에서 돈다(창이 멈추지 않게).
#[tauri::command]
pub(crate) async fn counsel_room_list() -> Value {
    let cfg = config_dir();
    tokio::task::spawn_blocking(move || room_list_at(&cfg))
        .await
        .unwrap_or_else(|_| json!({"status": "error", "detail": "join"}))
}

// ── 뱃지(§11 `mailbox/unread.json` · 읽기만) ─────────────────────────────────
/// 뱃지 파일 상한 — 정상 파일은 수 KB(대화 최대 50행). 넘으면 깨진 파일로 본다(UI 가 직전 값 유지).
const UNREAD_MAX_BYTES: u64 = 256 * 1024;

/// 뱃지 파일의 수정 시각(ms)과 글자. 없으면 `exists:false`(UI = 숨김). 판독(깨짐·판 `v`)은 UI 순수 모듈 몫이다.
pub(crate) fn unread_at(cfg: &Path) -> Value {
    let p = cfg.join("mailbox").join("unread.json");
    let Ok(meta) = std::fs::metadata(&p) else { return json!({"exists": false}) };
    let mtime = meta
        .modified()
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0);
    let text = if meta.len() > UNREAD_MAX_BYTES { None } else { std::fs::read_to_string(&p).ok() };
    json!({"exists": true, "mtime_ms": mtime, "text": text})
}

#[tauri::command]
pub(crate) fn counsel_unread() -> Value {
    unread_at(&config_dir())
}

// ── 아고라 창(읽기 전용 웹뷰) ──────────────────────────────────────────────
pub(crate) const AGORA_HOST: &str = "agora.godmeyou.kr";
const AGORA_HOME: &str = "https://agora.godmeyou.kr/";
const AGORA_LABEL: &str = "agora";

/// 창 안 이동 허용 = `https://agora.godmeyou.kr` 오리진만(포트·사용자정보 없음) + 빈 틀(`about:blank`·`about:srcdoc` —
/// 사이트의 보안 확인 스크립트가 쓰는 숨은 틀). 그 밖은 창 안에서 열지 않는다(허용 목록 안이면 기본 브라우저로).
pub(crate) fn agora_nav_allowed(url: &tauri::Url) -> bool {
    match url.scheme() {
        "https" => {
            url.host_str() == Some(AGORA_HOST) && url.port().is_none() && url.username().is_empty() && url.password().is_none()
        }
        "about" => matches!(url.path(), "blank" | "srcdoc"),
        _ => false,
    }
}

/// 창마다 먼저 도는 스크립트 — ⑴폼 제출 막기(보기 전용) ⑵「내 글」 강조(글쓴이 칸 글자 == 내 id 인 글 상자에 테두리).
/// 서버 변경 0 · 내 id 는 JSON 문자열로 박는다(형식 밖이면 빈 값 = 강조 안 함). 남의 페이지 DOM 은 클래스 1개만 더한다.
pub(crate) fn agora_init_script(me: &str) -> String {
    let me_js = serde_json::to_string(if valid_participant_id(me) { me } else { "" }).unwrap_or_else(|_| "\"\"".into());
    format!(
        r#"(function(){{
  if (location.hostname !== "{host}") return;
  document.addEventListener("submit", function (e) {{ e.preventDefault(); e.stopPropagation(); }}, true);
  var ME = {me_js};
  if (!ME) return;
  function ensureStyle() {{
    if (!document.head || document.getElementById("cysr-mine-style")) return;
    var s = document.createElement("style");
    s.id = "cysr-mine-style";
    s.textContent = ".speech.cysr-mine{{outline:2px solid #2f81f7;outline-offset:2px;border-radius:6px}}";
    document.head.appendChild(s);
  }}
  function mark() {{
    ensureStyle();
    var els = document.querySelectorAll(".speech-who");
    for (var i = 0; i < els.length; i++) {{
      if (els[i].textContent !== ME) continue;
      var box = els[i].closest(".speech");
      if (box && !box.classList.contains("cysr-mine")) box.classList.add("cysr-mine");
    }}
  }}
  var queued = false;
  function schedule() {{ if (queued) return; queued = true; setTimeout(function () {{ queued = false; mark(); }}, 200); }}
  function start() {{ mark(); new MutationObserver(schedule).observe(document.documentElement, {{ childList: true, subtree: true }}); }}
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
}})();"#,
        host = AGORA_HOST,
        me_js = me_js
    )
}

/// 창 밖 링크 — https 이고 `open_url` 허용 목록 안일 때만 기본 브라우저로(그 밖은 아무것도 열지 않는다).
fn open_outside(url: &str) {
    let _ = crate::open_url(url.to_string());
}

/// 「아고라」 단추 — 별도 창(라벨 `agora`). 이미 열려 있으면 앞으로.
/// 경계: capability 무등재(= 이 창은 앱 명령 호출 0) · 이동 = 아고라 오리진만 · 새 창·다운로드 거부 ·
/// 저장소 = 비영속(incognito · 메인 창과 공유 0 · 닫으면 소멸) · 개발자 도구 끔.
/// ★창 만들기는 비동기 명령에서 한다(동기 명령에서 만들면 윈도에서 교착 — Tauri 문서).
#[tauri::command]
pub(crate) async fn open_agora_window(app: tauri::AppHandle) -> Result<(), String> {
    use tauri::Manager as _;
    if let Some(w) = app.get_webview_window(AGORA_LABEL) {
        let _ = w.unminimize();
        let _ = w.show();
        return w.set_focus().map_err(|e| e.to_string());
    }
    let me = my_id(read_opt(&config_dir().join("participant.json")).as_deref());
    let url = AGORA_HOME.parse::<tauri::Url>().map_err(|e| e.to_string())?;
    tauri::WebviewWindowBuilder::new(&app, AGORA_LABEL, tauri::WebviewUrl::External(url))
        .title("아고라 — 보기 전용")
        .inner_size(1100.0, 800.0)
        .incognito(true)
        .devtools(false)
        .initialization_script(agora_init_script(&me))
        .on_navigation(|u| {
            if agora_nav_allowed(u) {
                true
            } else {
                open_outside(u.as_str());
                false
            }
        })
        .on_new_window(|u, _features| {
            open_outside(u.as_str());
            tauri::webview::NewWindowResponse::Deny
        })
        .on_download(|_w, _e| false)
        .build()
        .map(|_| ())
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    const PIN: &str = "# 주석\n\
desk jarvis-counsel SHA256:yvjI714ZM9bpFldLoJFwATQgEX6JR1VT7Rh5jDGokiw\n\
chair SHA256:4CKkbxfRkimcSmlPXo6HQ6jg5U3XrSEqHDNulBcI9B0\n\
room 2a3c1932d7eccf316cc4a0b312e558c7\n\
weekly_period_days 7\n\
room NOT-HEX\n";

    #[test]
    fn config_dir_env_wins_else_home_dot_config_agora() {
        let home = Path::new("/h");
        assert_eq!(config_dir_from(Some("/x/ag"), home), PathBuf::from("/x/ag"));
        assert_eq!(config_dir_from(Some("  "), home), home.join(".config").join("agora"));
        assert_eq!(config_dir_from(None, home), home.join(".config").join("agora"));
        // 윈 동등성: 같은 식(홈 = %USERPROFILE%) — 구분자만 플랫폼 것.
        let wh = Path::new("C:\\Users\\u");
        assert_eq!(config_dir_from(None, wh), wh.join(".config").join("agora"));
    }

    #[test]
    fn desk_pin_reads_desk_and_room_only() {
        let p = parse_desk_pin(PIN);
        assert_eq!(p.desks, vec![("jarvis-counsel".into(), "SHA256:yvjI714ZM9bpFldLoJFwATQgEX6JR1VT7Rh5jDGokiw".into())]);
        assert_eq!(p.rooms, vec!["2a3c1932d7eccf316cc4a0b312e558c7".to_string()]);
        assert_eq!(parse_desk_pin(""), DeskPin::default());
        assert!(parse_desk_pin("desk x SHA256:abc").desks.is_empty(), "id 형식 밖(1글자)");
        assert!(parse_desk_pin("desk jarvis-a nofp").desks.is_empty(), "지문 꼴 밖");
    }

    // 실 명부의 상담소 줄(공개키 · 2026-10-09 실측 — 지문이 꾸러미 핀 `desk` 값과 같다).
    fn real_key() -> &'static str {
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL20PmJBFHWN8fGdkyuqWQCrr8Buf19P1vPITDmxXtRA"
    }

    #[test]
    fn roster_fingerprint_matches_openssh_sha256_form() {
        let roster = format!("jarvis-counsel {}\nother {}\n", real_key(), real_key());
        let fps = roster_fingerprints(&roster, "jarvis-counsel");
        assert_eq!(fps, vec!["SHA256:yvjI714ZM9bpFldLoJFwATQgEX6JR1VT7Rh5jDGokiw".to_string()], "실 핀 값과 같아야 한다");
        // 옵션 칸·주체 목록(쉼표)도 읽는다.
        let r2 = format!("a,jarvis-counsel namespaces=\"file\" {} comment\n", real_key());
        assert_eq!(roster_fingerprints(&r2, "jarvis-counsel"), fps);
        assert!(roster_fingerprints(&roster, "nobody").is_empty());
    }

    #[test]
    fn desk_is_verified_only_when_every_roster_key_matches_pin() {
        let roster = format!("jarvis-counsel {}\n", real_key());
        let fp = roster_fingerprints(&roster, "jarvis-counsel")[0].clone();
        let pin = DeskPin { desks: vec![("jarvis-counsel".into(), fp.clone())], rooms: vec![] };
        assert_eq!(verified_desk_ids(&pin, &roster), vec!["jarvis-counsel".to_string()]);
        // 같은 id 에 다른 키가 하나 더 있으면 → 상담소로 보지 않는다.
        let two = format!("{roster}jarvis-counsel ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ9AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n");
        assert!(verified_desk_ids(&pin, &two).is_empty());
        // 명부에 없으면 → 아니다 · 지문이 다르면 → 아니다.
        assert!(verified_desk_ids(&pin, "").is_empty());
        let wrong = DeskPin { desks: vec![("jarvis-counsel".into(), "SHA256:zzz".into())], rooms: vec![] };
        assert!(verified_desk_ids(&wrong, &roster).is_empty());
    }

    #[test]
    fn client_version_gate_is_numeric() {
        assert!(client_version_ok(r#"{"version":"0.1.14"}"#));
        assert!(client_version_ok(r#"{"version":"0.2.0"}"#));
        assert!(client_version_ok(r#"{"version":"1.0.0"}"#));
        assert!(!client_version_ok(r#"{"version":"0.1.4"}"#), "0.1.4 = 상담소 방 genesis 격리(실측)");
        assert!(!client_version_ok(r#"{"version":"0.1.9"}"#), "글자 비교면 0.1.9 > 0.1.14 로 틀린다");
        assert!(!client_version_ok(r#"{"version":"0.1"}"#));
        assert!(!client_version_ok("{"));
    }

    #[test]
    fn room_from_pin_else_state_json() {
        let p = parse_desk_pin(PIN);
        assert_eq!(pick_room(&p, None).as_deref(), Some("2a3c1932d7eccf316cc4a0b312e558c7"));
        let none = DeskPin::default();
        assert_eq!(pick_room(&none, Some(r#"{"room_ids":["bad","0123456789abcdef0123456789abcdef"]}"#)).as_deref(),
            Some("0123456789abcdef0123456789abcdef"));
        assert_eq!(pick_room(&none, Some("{")), None);
        assert_eq!(pick_room(&none, None), None);
    }

    #[test]
    fn my_id_from_participant_json() {
        assert_eq!(my_id(Some(r#"{"id":"jarvis-ab12cd34ef"}"#)), "jarvis-ab12cd34ef");
        assert_eq!(my_id(Some(r#"{"id":"<script>"}"#)), "");
        assert_eq!(my_id(None), "");
    }

    #[test]
    fn read_page_keeps_only_signed_well_formed_rows() {
        let v = json!({
            "events": [
                {"message_id":"m1","kind":"post","from":"jarvis-a1","ts":"2026-10-08T12:00:00Z","sig":"ok","body":"<<AGORA-DATA-0123456789abcdef\nhi\nAGORA-DATA-0123456789abcdef>>","untrusted":{"marker":"AGORA-DATA-0123456789abcdef"}},
                {"message_id":"m2","kind":"post","from":"bad id!","ts":"t","sig":"ok","body":"x"},
                {"message_id":"m3","kind":"post","from":"jarvis-a1","ts":"t","sig":"bad","body":"x"},
                {"kind":"post","from":"jarvis-a1","ts":"t","sig":"ok"}
            ],
            "refs": [{"role":"ref","from_message_id":"m1","thread_id":"t1","message_id":"m0","why":null,"resolved":true}],
            "next_cursor": "events:abc"
        });
        let (ev, rf, next) = parse_read_page(&v);
        assert_eq!(ev.len(), 1);
        assert_eq!(ev[0]["marker"], "AGORA-DATA-0123456789abcdef");
        assert_eq!(rf, vec![json!({"from_message_id":"m1","thread_id":"t1","message_id":"m0"})]);
        assert_eq!(next.as_deref(), Some("events:abc"));
        assert_eq!(parse_read_page(&json!({"next_cursor": null})).2, None);
    }

    /// 격리 하네스 — 임시 설정 폴더 + 가짜 `lib/bin/agora`(고정 JSON) → 실제 호출 경로 왕복.
    fn fixture(version: &str, script_json: &str) -> tempfile_lite::Dir {
        let d = tempfile_lite::Dir::new("counsel");
        let lib = d.path().join("lib");
        std::fs::create_dir_all(lib.join("bin")).unwrap();
        std::fs::create_dir_all(lib.join("config")).unwrap();
        std::fs::write(lib.join("PACKAGE-MANIFEST.json"), format!(r#"{{"version":"{version}"}}"#)).unwrap();
        std::fs::write(lib.join("config").join("desk-pin.txt"), PIN).unwrap();
        std::fs::write(d.path().join("participant.json"), r#"{"id":"jarvis-me00000001"}"#).unwrap();
        let script = format!("import sys\nsys.stdout.write({script_json:?})\n");
        std::fs::write(lib.join("bin").join("agora"), script).unwrap();
        d
    }

    #[test]
    fn harness_round_trip_through_fake_client() {
        let page = json!({"events":[{"message_id":"g","kind":"genesis","from":"jarvis-chair1","ts":"2026-10-05T13:14:43Z","sig":"ok","body":"intro","untrusted":{"marker":null}}],"refs":[],"next_cursor":null}).to_string();
        let d = fixture("0.1.14", &page);
        let v = room_list_at(d.path());
        assert_eq!(v["status"], "ok", "{v}");
        assert_eq!(v["room_id"], "2a3c1932d7eccf316cc4a0b312e558c7");
        assert_eq!(v["me"], "jarvis-me00000001");
        assert_eq!(v["events"].as_array().unwrap().len(), 1);
        assert_eq!(v["partial"], false);
        assert_eq!(v["desk_ids"], json!([]), "명부 파일이 없으면 상담소 답 표식 0");
    }

    #[test]
    fn harness_old_client_and_missing_room_and_bad_output() {
        let d = fixture("0.1.4", "{}");
        assert_eq!(room_list_at(d.path())["status"], "no_client");
        let empty = tempfile_lite::Dir::new("counsel-empty");
        assert_eq!(room_list_at(empty.path())["status"], "no_client");
        let d2 = fixture("0.1.14", "not json");
        assert_eq!(room_list_at(d2.path())["status"], "error");
        let d3 = fixture("0.1.14", "{}");
        std::fs::write(d3.path().join("lib").join("config").join("desk-pin.txt"), "# 빈 핀\n").unwrap();
        assert_eq!(room_list_at(d3.path())["status"], "no_room");
    }

    #[test]
    fn unread_file_is_read_only_with_mtime_and_size_cap() {
        let d = tempfile_lite::Dir::new("counsel-unread");
        assert_eq!(unread_at(d.path()), json!({"exists": false}), "없으면 exists:false(UI = 숨김)");
        std::fs::create_dir_all(d.path().join("mailbox")).unwrap();
        let p = d.path().join("mailbox").join("unread.json");
        std::fs::write(&p, r#"{"v":1,"count":2}"#).unwrap();
        let v = unread_at(d.path());
        assert_eq!(v["exists"], true);
        assert_eq!(v["text"], r#"{"v":1,"count":2}"#);
        assert!(v["mtime_ms"].as_u64().unwrap() > 0);
        std::fs::write(&p, vec![b' '; (UNREAD_MAX_BYTES + 1) as usize]).unwrap();
        assert_eq!(unread_at(d.path())["text"], Value::Null, "상한 초과 = 깨진 파일 취급(UI 직전 값)");
        // 읽기만 — 파일이 그대로다.
        assert_eq!(std::fs::metadata(&p).unwrap().len(), UNREAD_MAX_BYTES + 1);
    }

    #[test]
    fn agora_window_navigation_is_our_origin_only() {
        let ok = |u: &str| agora_nav_allowed(&u.parse::<tauri::Url>().unwrap());
        assert!(ok("https://agora.godmeyou.kr/"));
        assert!(ok("https://agora.godmeyou.kr/room?id=2a3c1932d7eccf316cc4a0b312e558c7#x"));
        assert!(ok("https://agora.godmeyou.kr/cdn-cgi/challenge-platform/scripts/jsd/main.js"));
        assert!(ok("about:blank") && ok("about:srcdoc"), "사이트 보안 확인용 빈 틀");
        for bad in [
            "http://agora.godmeyou.kr/",
            "https://agora.godmeyou.kr.evil.com/",
            "https://evil.agora.godmeyou.kr/",
            "https://godmeyou.kr/",
            "https://jarvis-install.godmeyou.kr/",
            "https://agora.godmeyou.kr:8443/",
            "https://user@agora.godmeyou.kr/",
            "https://agora.godmeyou.kr@evil.com/",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "about:config",
            "tauri://localhost/",
        ] {
            assert!(!ok(bad), "창 안 이동을 막아야 한다: {bad}");
        }
    }

    #[test]
    fn open_url_allows_our_two_hosts_exactly_not_subdomains() {
        assert!(crate::host_in_allowlist("agora.godmeyou.kr", &[]));
        assert!(crate::host_in_allowlist("jarvis-install.godmeyou.kr", &[]));
        for bad in ["godmeyou.kr", "evil.agora.godmeyou.kr", "agora.godmeyou.kr.evil.com", "x.jarvis-install.godmeyou.kr", "agora.godmeyou.krx"] {
            assert!(!crate::host_in_allowlist(bad, &[]), "{bad}");
        }
        // 사용자정보(@) 위장 = 실제 호스트 evil.com 으로 판정된다.
        assert!(crate::url_host_allowed("https://agora.godmeyou.kr@evil.com/").is_err());
        assert!(crate::url_host_allowed("http://agora.godmeyou.kr/").is_err(), "https 만");
        assert!(crate::url_host_allowed("https://jarvis-install.godmeyou.kr/").is_ok());
    }

    #[test]
    fn init_script_embeds_my_id_as_json_and_blocks_forms() {
        let s = agora_init_script("jarvis-me00000001");
        assert!(s.contains(r#"var ME = "jarvis-me00000001";"#));
        assert!(s.contains(r#"document.addEventListener("submit""#) && s.contains("e.preventDefault()"));
        assert!(s.contains(r#"if (location.hostname !== "agora.godmeyou.kr") return;"#));
        assert!(!s.contains("innerHTML") && !s.contains("fetch(") && !s.contains("__TAURI__"), "남의 페이지에 쓰는 것은 클래스·스타일 1개뿐");
        // 형식 밖 id(따옴표·태그)는 박지 않는다 → 강조 안 함.
        let bad = agora_init_script("\"; alert(1); //");
        assert!(bad.contains(r#"var ME = "";"#));
    }

    #[test]
    fn agora_window_gets_no_app_ipc_capability() {
        // 경계 = capability 무등재: Tauri 2 는 등재되지 않은 창·원격 오리진에 앱 명령을 열지 않는다.
        let cap: Value = serde_json::from_str(include_str!("../capabilities/default.json")).unwrap();
        assert_eq!(cap["windows"], json!(["main"]), "capability 창 = main 하나뿐이어야 한다");
        assert!(cap.get("remote").is_none(), "원격 주소에 앱 명령을 여는 remote 칸 0");
        let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("capabilities");
        for e in std::fs::read_dir(&dir).unwrap() {
            let raw = std::fs::read_to_string(e.unwrap().path()).unwrap();
            assert!(!raw.contains(AGORA_LABEL) || !raw.contains("\"windows\""), "아고라 창 라벨이 capability 에 들어갔다");
            assert!(!raw.contains("godmeyou"), "아고라 주소가 capability 에 들어갔다");
        }
    }

    /// 시험 전용 임시 폴더(의존성 0 · 끝나면 지운다).
    mod tempfile_lite {
        pub struct Dir(std::path::PathBuf);
        impl Dir {
            pub fn new(tag: &str) -> Self {
                let n = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
                let p = std::env::temp_dir().join(format!("cysr-{tag}-{}-{n}", std::process::id()));
                std::fs::create_dir_all(&p).unwrap();
                Dir(p)
            }
            pub fn path(&self) -> &std::path::Path {
                &self.0
            }
        }
        impl Drop for Dir {
            fn drop(&mut self) {
                let _ = std::fs::remove_dir_all(&self.0);
            }
        }
    }
}
