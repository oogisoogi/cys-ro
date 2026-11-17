//! (cysr-ui-slice1 · TICKET=cysr-ui-slice1-1117) 대화 화면이 새로 쓰는 Tauri 명령 — **우리 새 파일**(원작자 이름과 겹침 0).
//!
//! 설계 정본 = `cysr-ui-research/P2-DESIGN.md` §2-5(사람 말 = 원자 제출) · §5-1(결속 세션 전문) · §5-5(명령 계약).
//!
//! - `chat_send{kind:"human"}` = 데몬 `surface.send_text {human, quiet, clear_first, refuse_on_approval}` + operator·owner 표지 **한 요청**.
//!   데몬이 Ctrl-U → 울타리 붙여넣기 → Enter 를 원자로 넣고(조각 0.5 M1 실측 0.73~0.84초), 승인·질문 창이면 **쓰기 전** 거부한다(M2 · 바이트 0).
//!   operator 표지 = 원장 무기록 = 오너 임무(§2-8 ㉩). 기존 `send_input` 은 `refuse_on_approval` 을 싣지 않으므로 쓰지 않는다(M2 대조: R1 실재).
//!   응답은 **분류 보존**(`rpc_full_classified`)으로 받아 넷으로 접는다 — written · held(승인 창 거부·정비 보류) · failed(확정 거부) · uncertain(불명 = 「확인 중」 · 다시 보내기 금지).
//! - `chat_transcript` = 좌석에 **결속된** 세션 기록(`org.status.registered_session_id`) 한 파일을 바이트 오프셋부터 읽는다.
//!   경로 = `<좌석 claude_config_dir>/projects/<cwd 슬러그>/<id>.jsonl`(조각 0.5 M9 맥 실측 · `~/.claude*` 꼴 가정 금지).
//!   경로 재료(설정 폴더·cwd·세션 id)는 **웹뷰가 아니라 데몬**에서 받는다 — 웹뷰가 넘기는 것은 좌석 번호와 오프셋뿐(허용 경로 = 결속 id 1개).
//!
//! 데몬 변경 0(NFR-F3). 원작자 파일 `main.rs` 에는 `mod viewcore;` 와 `generate_handler!` 이름 2줄만 넣는다(§8-1).

use serde_json::{json, Value};

use crate::{read_operator_token_for, resolve_socket, rpc_full_classified, rpc_on, TransportClass};

/// 데몬 오류 코드(정의처 = `cys::ERR_APPROVAL_SCREEN` · src/lib.rs) — 승인·질문 창 거부(바이트 0) = 화면은 「붙잡음」.
const CODE_APPROVAL_SCREEN: &str = cys::ERR_APPROVAL_SCREEN;
/// 데몬 오류 코드(정의처 = `cys::ERR_WRITE_OUTCOME_UNKNOWN`) — 쓰기 결과 모름(아직 쓰일 수 있음 · 재시도하면 두 번 쳐질 수 있음) = 「확인 중」.
const CODE_WRITE_OUTCOME_UNKNOWN: &str = cys::ERR_WRITE_OUTCOME_UNKNOWN;
/// 세션 기록 한 번에 읽는 상한(바이트) — 넘으면 다음 호출이 `next_offset` 부터 잇는다(잘림 없음 · 레코드 경계까지만 소비).
pub(crate) const TRANSCRIPT_READ_MAX: u64 = 2 * 1024 * 1024;

/// 사람 말 원자 제출 매개변수(순수). `tok` = 그 소켓 데몬의 operator.token(없으면 표지 없음 → 데몬이 fail-closed 로 원장 기록).
/// ★`human:true` · `machine_origin:false` · `queued:false` 고정 — 이 셋이 원장 무기록(오너 임무)의 조건이다(handlers.rs `human_verified`).
pub(crate) fn human_send_params(surface_id: u64, text: &str, tok: Option<&str>) -> Value {
    let mut p = json!({
        "surface_id": surface_id,
        "text": text,
        "quiet": true,
        "human": true,
        "queued": false,
        "clear_first": true,
        "refuse_on_approval": true,
        "machine_origin": false,
    });
    if let Some(t) = tok {
        p["owner_token"] = json!(t);
        p["operator_token"] = json!(t);
    }
    p
}

/// 데몬 응답(분류 보존) → 화면 결과 하나(순수). 꼴: `{outcome, code?, message?, result?}`.
/// - `written`   : ok · `sent:true` · 붙잡음 표시(`held`) 없음
/// - `held`      : 승인·질문 창 거부(`approval_screen` · 바이트 0) — 화면이 붙잡고 문턱 재통과 때 1회 제출
/// - `queued_hold`: 정비 보류(`hold_seq`) — 데몬이 붙잡아 스스로 배달 · 화면은 다시 보내지 않음
/// - `failed`    : 확정 거부(그 밖 오류 코드) · 전송 전 끊김(Definite = 데몬이 못 봄)
/// - `uncertain` : 전송 뒤 끊김·응답 파싱 실패(Uncertain) · `write_outcome_unknown` · ok 인데 `sent` 를 확인 못 함
pub(crate) fn classify_send(r: Result<Value, (TransportClass, String)>) -> Value {
    match r {
        Err((TransportClass::Definite, e)) => json!({"outcome": "failed", "code": "transport_definite", "message": e}),
        Err((TransportClass::Uncertain, e)) => json!({"outcome": "uncertain", "code": "transport_uncertain", "message": e}),
        Ok(resp) => {
            if resp["ok"].as_bool() == Some(true) {
                let res = resp["result"].clone();
                if res.get("hold_seq").map_or(false, |h| !h.is_null()) {
                    // 정비 보류(update_hold.rs `{held, hold_seq, queued:true}`) — 데몬이 붙잡아 두었다가 **스스로** 배달한다.
                    // 화면이 다시 보내면 두 번 간다 → 「차례 기다림(업데이트 뒤 전달)」 · 다시 보내기 0.
                    json!({"outcome": "queued_hold", "code": "update_hold", "result": res})
                } else if res.get("held").map_or(false, |h| !h.is_null()) {
                    // 본문은 쓰였고 제출이 붙잡힘(`held:"awaiting_submit"`) — 입력줄에 남았을 수 있다 · 다시 보내면 두 번 쳐질 수 있다 = 모름.
                    json!({"outcome": "uncertain", "code": "held_awaiting_submit", "result": res})
                } else if res["sent"].as_bool() == Some(true) {
                    json!({"outcome": "written", "result": res})
                } else {
                    // 성공 꼴인데 「썼다」를 확인할 칸이 없다 — 썼다고 칠하지 않는다(모름 = 확인 중).
                    json!({"outcome": "uncertain", "code": "no_sent_flag", "result": res})
                }
            } else {
                let code = resp["error"]["code"].as_str().unwrap_or("").to_string();
                let message = resp["error"]["message"].as_str().unwrap_or("unknown error").to_string();
                let outcome = match code.as_str() {
                    CODE_APPROVAL_SCREEN => "held",
                    CODE_WRITE_OUTCOME_UNKNOWN => "uncertain",
                    _ => "failed",
                };
                json!({"outcome": outcome, "code": code, "message": message})
            }
        }
    }
}

/// `chat_send` — 대화 화면 사람 말. `kind` 는 `"human"` 만 받는다(기계 문안 `"auto"` = 큐 경로는 조각 5·8 몫 · 지금은 거부).
#[tauri::command]
pub async fn chat_send(socket: Option<String>, surface_id: u64, text: String, kind: String) -> Result<Value, String> {
    if kind != "human" {
        return Err(format!("unsupported_kind: {kind}"));
    }
    let sock = resolve_socket(&socket);
    let tok = read_operator_token_for(&sock);
    let params = human_send_params(surface_id, &text, tok.as_deref());
    Ok(classify_send(rpc_full_classified(&sock, "surface.send_text", params).await))
}

/// Claude Code 프로젝트 폴더 이름(순수) — cwd 의 영숫자 밖 글자를 전부 `-` 로(`/a/.b` → `-a--b`).
pub(crate) fn transcript_slug(cwd: &str) -> String {
    cwd.chars().map(|c| if c.is_ascii_alphanumeric() { c } else { '-' }).collect()
}

/// 결속 세션 id 꼴(순수) — 영숫자·`-` 만 · 8~128자. 아니면 경로를 만들지 않는다(`..`·`/` 차단).
pub(crate) fn session_id_ok(id: &str) -> bool {
    (8..=128).contains(&id.len()) && id.chars().all(|c| c.is_ascii_alphanumeric() || c == '-')
}

/// 레코드 `message.content` → (사람이 읽는 글, 글 조각들)(순수). 문자열이면 그대로 · 배열이면 `type:"text"` 조각만 이음.
/// 그 밖(도구 결과·도구 호출·생각만)은 글 None — 말풍선은 아니지만 **부모 사슬을 잇는 고리**라 레코드는 돌려준다.
fn content_text(content: &Value) -> (Option<String>, Vec<String>) {
    if let Some(s) = content.as_str() {
        return (Some(s.to_string()), vec![s.to_string()]);
    }
    let Some(arr) = content.as_array() else { return (None, vec![]) };
    let parts: Vec<String> = arr
        .iter()
        .filter(|b| b["type"].as_str() == Some("text"))
        .filter_map(|b| b["text"].as_str().map(str::to_owned))
        .collect();
    if parts.is_empty() {
        (None, parts)
    } else {
        (Some(parts.join("\n")), parts)
    }
}

/// 세션 기록 덩이(순수) → (레코드들, 소비한 바이트). 줄 끝(`\n`)까지 온전한 줄만 읽고 마지막 미완 줄은 남긴다(다음 호출이 잇는다).
/// 레코드 = `{uuid, parent, role:"user"|"assistant", text(없으면 null), parts, ts, sidechain}` — user/assistant 전부(글 없는 고리 포함). 줄 파싱 실패는 건너뛴다(세기만).
pub(crate) fn parse_transcript_chunk(buf: &[u8]) -> (Vec<Value>, usize, usize) {
    let consumed = match buf.iter().rposition(|&b| b == b'\n') {
        Some(i) => i + 1,
        None => 0,
    };
    let mut out = Vec::new();
    let mut bad = 0usize;
    for line in buf[..consumed].split(|&b| b == b'\n') {
        if line.iter().all(|b| b.is_ascii_whitespace()) {
            continue;
        }
        let Ok(v) = serde_json::from_slice::<Value>(line) else {
            bad += 1;
            continue;
        };
        let role = match v["type"].as_str() {
            Some("user") => "user",
            Some("assistant") => "assistant",
            _ => continue,
        };
        let (text, parts) = content_text(&v["message"]["content"]);
        out.push(json!({
            "uuid": v["uuid"].as_str(),
            "parent": v["parentUuid"].as_str(),
            "role": role,
            "text": text,
            "parts": if parts.len() > 1 { json!(parts) } else { Value::Null },
            "ts": v["timestamp"].as_str(),
            "sidechain": v["isSidechain"].as_bool().unwrap_or(false),
        }));
    }
    (out, consumed, bad)
}

/// 좌석 목록·org.status 행에서 그 좌석 찾기(순수).
fn row_of(rows: &Value, surface_id: u64) -> Option<&Value> {
    rows["surfaces"].as_array()?.iter().find(|r| r["surface_id"].as_u64() == Some(surface_id))
}

/// 세션 파일 경로(순수 판정 + 파일 존재 확인은 호출자). 재료가 모자라면 Err(사유 코드).
pub(crate) fn transcript_path(cfg: Option<&str>, cwd: Option<&str>, sid: Option<&str>) -> Result<std::path::PathBuf, &'static str> {
    let cfg = cfg.filter(|c| !c.trim().is_empty()).ok_or("no_config_dir")?;
    let cfg_path = std::path::Path::new(cfg);
    if !cfg_path.is_absolute() || cfg_path.components().any(|c| matches!(c, std::path::Component::ParentDir)) {
        return Err("config_dir_not_absolute");
    }
    let cwd = cwd.filter(|c| !c.trim().is_empty()).ok_or("no_cwd")?;
    let sid = sid.ok_or("no_session")?;
    if !session_id_ok(sid) {
        return Err("bad_session_id");
    }
    Ok(cfg_path.join("projects").join(transcript_slug(cwd)).join(format!("{sid}.jsonl")))
}

/// 슬러그 폴더에 없을 때의 대비 — `<cfg>/projects/*/<id>.jsonl` **정확히 같은 이름 하나**만(긴 cwd 의 줄인 슬러그 등). 둘 이상이면 고르지 않는다.
fn find_by_id(cfg: &std::path::Path, sid: &str) -> Option<std::path::PathBuf> {
    let want = format!("{sid}.jsonl");
    let mut hit = None;
    for d in std::fs::read_dir(cfg.join("projects")).ok()?.flatten() {
        let p = d.path().join(&want);
        if p.is_file() {
            if hit.is_some() {
                return None;
            }
            hit = Some(p);
        }
    }
    hit
}

/// `chat_transcript` — 좌석에 결속된 세션 기록을 `after_offset` 부터 읽는다(`from_end` = 읽지 않고 끝 오프셋만).
/// 꼴: `{status:"ok", session_id, next_offset, size, records[], bad_lines, reset}` · 못 읽으면 `{status:"unknown", why}`(화면 = 「전달 확인 중」).
#[tauri::command]
pub async fn chat_transcript(socket: Option<String>, surface_id: u64, after_offset: u64, from_end: Option<bool>) -> Result<Value, String> {
    let sock = resolve_socket(&socket);
    let list = rpc_on(&sock, "surface.list", json!({})).await?;
    let org = rpc_on(&sock, "org.status", json!({})).await?;
    let Some(lrow) = row_of(&list, surface_id) else {
        return Ok(json!({"status": "unknown", "why": "no_seat"}));
    };
    let sid = row_of(&org, surface_id).and_then(|r| r["registered_session_id"].as_str()).map(str::to_owned);
    let path = match transcript_path(lrow["claude_config_dir"].as_str(), lrow["cwd"].as_str(), sid.as_deref()) {
        Ok(p) => p,
        Err(why) => return Ok(json!({"status": "unknown", "why": why})),
    };
    let sid = sid.unwrap_or_default();
    let path = if path.is_file() {
        path
    } else {
        match lrow["claude_config_dir"].as_str().and_then(|c| find_by_id(std::path::Path::new(c), &sid)) {
            Some(p) => p,
            None => return Ok(json!({"status": "unknown", "why": "no_file", "session_id": sid})),
        }
    };
    if from_end.unwrap_or(false) {
        // 대화 화면을 처음 띄울 때 — 지난 기록을 다 읽지 않고 끝에서 시작한다(이후 새 바이트만).
        let size = std::fs::metadata(&path).map_err(|e| e.to_string())?.len();
        return Ok(json!({"status": "ok", "session_id": sid, "next_offset": size, "size": size, "records": [], "bad_lines": 0, "reset": false}));
    }
    read_transcript_from(&path, after_offset).map(|mut v| {
        v["session_id"] = json!(sid);
        v
    })
}

/// 파일 하나를 오프셋부터 읽는다(파일 IO · 경로는 위에서 정한 결속 파일 하나).
pub(crate) fn read_transcript_from(path: &std::path::Path, after_offset: u64) -> Result<Value, String> {
    use std::io::{Read, Seek, SeekFrom};
    let mut f = std::fs::File::open(path).map_err(|e| e.to_string())?;
    let size = f.metadata().map_err(|e| e.to_string())?.len();
    // 파일이 줄었으면(새 세션이 같은 이름? · 잘림) 처음부터 — 화면은 `reset` 으로 짝짓기를 다시 한다.
    let (start, reset) = if after_offset > size { (0, true) } else { (after_offset, false) };
    f.seek(SeekFrom::Start(start)).map_err(|e| e.to_string())?;
    let want = (size - start).min(TRANSCRIPT_READ_MAX);
    let mut buf = Vec::with_capacity(want as usize);
    f.take(want).read_to_end(&mut buf).map_err(|e| e.to_string())?;
    let (records, consumed, bad) = parse_transcript_chunk(&buf);
    Ok(json!({
        "status": "ok",
        "next_offset": start + consumed as u64,
        "size": size,
        "records": records,
        "bad_lines": bad,
        "reset": reset,
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn human_params_are_one_atomic_request_with_both_tokens() {
        let p = human_send_params(7, "안녕", Some("TOK"));
        assert_eq!(p["surface_id"], 7);
        assert_eq!(p["text"], "안녕");
        for k in ["quiet", "human", "clear_first", "refuse_on_approval"] {
            assert_eq!(p[k], true, "{k}");
        }
        for k in ["queued", "machine_origin"] {
            assert_eq!(p[k], false, "{k}");
        }
        assert_eq!(p["operator_token"], "TOK");
        assert_eq!(p["owner_token"], "TOK");
        let n = human_send_params(7, "x", None);
        assert!(n.get("operator_token").is_none() && n.get("owner_token").is_none());
    }

    #[test]
    fn classify_covers_the_four_outcomes() {
        let ok = |r: Value| classify_send(Ok(json!({"ok": true, "result": r})));
        let err = |c: &str| classify_send(Ok(json!({"ok": false, "error": {"code": c, "message": "m"}})));
        assert_eq!(ok(json!({"surface_id": 1, "sent": true}))["outcome"], "written");
        assert_eq!(ok(json!({"held": true, "hold_seq": 3, "queued": true}))["outcome"], "queued_hold");
        assert_eq!(ok(json!({"sent": true, "held": "awaiting_submit"}))["outcome"], "uncertain");
        assert_eq!(ok(json!({"surface_id": 1}))["outcome"], "uncertain");
        assert_eq!(err("approval_screen")["outcome"], "held");
        assert_eq!(err("write_outcome_unknown")["outcome"], "uncertain");
        assert_eq!(err("not_found")["outcome"], "failed");
        assert_eq!(err("")["outcome"], "failed");
        assert_eq!(classify_send(Err((TransportClass::Definite, "x".into())))["outcome"], "failed");
        assert_eq!(classify_send(Err((TransportClass::Uncertain, "x".into())))["outcome"], "uncertain");
    }

    #[test]
    fn codes_match_the_daemon_constants() {
        assert_eq!(CODE_APPROVAL_SCREEN, "approval_screen");
        assert_eq!(CODE_WRITE_OUTCOME_UNKNOWN, "write_outcome_unknown");
    }

    #[test]
    fn slug_and_path_follow_measured_layout() {
        assert_eq!(transcript_slug("/Users/a/axdev/.wt/x-1"), "-Users-a-axdev--wt-x-1");
        assert_eq!(transcript_slug("/h/한글"), "-h---");
        let p = transcript_path(Some("/h/.cys/claude"), Some("/h/m1"), Some("0a4b82d0-9e01-4b29-aaaa-bbbbbbbbbbbb")).unwrap();
        assert_eq!(p, std::path::PathBuf::from("/h/.cys/claude/projects/-h-m1/0a4b82d0-9e01-4b29-aaaa-bbbbbbbbbbbb.jsonl"));
        assert_eq!(transcript_path(None, Some("/h"), Some("abcdefgh")).unwrap_err(), "no_config_dir");
        assert_eq!(transcript_path(Some("rel/dir"), Some("/h"), Some("abcdefgh")).unwrap_err(), "config_dir_not_absolute");
        assert_eq!(transcript_path(Some("/h/../etc"), Some("/h"), Some("abcdefgh")).unwrap_err(), "config_dir_not_absolute");
        assert_eq!(transcript_path(Some("/h"), None, Some("abcdefgh")).unwrap_err(), "no_cwd");
        assert_eq!(transcript_path(Some("/h"), Some("/h"), None).unwrap_err(), "no_session");
        assert_eq!(transcript_path(Some("/h"), Some("/h"), Some("../../etc/pw")).unwrap_err(), "bad_session_id");
        assert_eq!(transcript_path(Some("/h"), Some("/h"), Some("short")).unwrap_err(), "bad_session_id");
    }

    #[test]
    fn chunk_parser_reads_whole_lines_only_and_keeps_text() {
        let a = r#"{"type":"user","uuid":"u1","parentUuid":null,"timestamp":"t1","message":{"role":"user","content":"안녕"}}"#;
        let b = r#"{"type":"assistant","uuid":"a1","parentUuid":"u1","timestamp":"t2","message":{"content":[{"type":"thinking","thinking":"x"},{"type":"text","text":"네, 안녕하세요"}]}}"#;
        let tool = r#"{"type":"user","uuid":"u2","parentUuid":"a1","message":{"content":[{"type":"tool_result","content":"zz"}]}}"#;
        let meta = r#"{"type":"summary","summary":"s"}"#;
        let partial = r#"{"type":"user","uuid":"u3""#;
        let buf = format!("{a}\n{b}\n{tool}\n{meta}\nnot json\n{partial}");
        let (recs, consumed, bad) = parse_transcript_chunk(buf.as_bytes());
        assert_eq!(recs.len(), 3, "user·assistant·도구 결과 고리(글 없음) — 요약 레코드는 뺌");
        assert_eq!(recs[0]["role"], "user");
        assert_eq!(recs[0]["text"], "안녕");
        assert_eq!(recs[1]["parent"], "u1");
        assert_eq!(recs[1]["text"], "네, 안녕하세요");
        assert!(recs[2]["text"].is_null());
        assert_eq!(recs[2]["parent"], "a1");
        assert_eq!(bad, 1);
        assert_eq!(consumed, buf.len() - partial.len());
    }

    #[test]
    fn long_text_is_not_truncated_and_reader_resumes_from_offset() {
        let dir = std::env::temp_dir().join(format!("viewcore-t-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join("s.jsonl");
        let long = "가".repeat(5000);
        let l1 = json!({"type":"user","uuid":"u1","message":{"content": long}}).to_string();
        std::fs::write(&p, format!("{l1}\n")).unwrap();
        let r = read_transcript_from(&p, 0).unwrap();
        assert_eq!(r["records"][0]["text"].as_str().unwrap().chars().count(), 5000);
        let off = r["next_offset"].as_u64().unwrap();
        let l2 = json!({"type":"assistant","uuid":"a1","parentUuid":"u1","message":{"content":[{"type":"text","text":"답"}]}}).to_string();
        std::fs::write(&p, format!("{l1}\n{l2}\n")).unwrap();
        let r2 = read_transcript_from(&p, off).unwrap();
        assert_eq!(r2["records"].as_array().unwrap().len(), 1);
        assert_eq!(r2["records"][0]["text"], "답");
        assert_eq!(r2["reset"], false);
        let r3 = read_transcript_from(&p, 10_000_000).unwrap();
        assert_eq!(r3["reset"], true);
        std::fs::remove_dir_all(&dir).ok();
    }
}
