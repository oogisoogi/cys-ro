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

use crate::{read_operator_token_for, resolve_socket, rpc_full, rpc_full_classified, rpc_on, TransportClass};

/// 데몬 오류 코드(정의처 = `cys::ERR_APPROVAL_SCREEN` · src/lib.rs) — 승인·질문 창 거부(바이트 0) = 화면은 「붙잡음」.
const CODE_APPROVAL_SCREEN: &str = cys::ERR_APPROVAL_SCREEN;
/// 데몬 오류 코드(정의처 = `cys::ERR_WRITE_OUTCOME_UNKNOWN`) — 쓰기 결과 모름(아직 쓰일 수 있음 · 재시도하면 두 번 쳐질 수 있음) = 「확인 중」.
const CODE_WRITE_OUTCOME_UNKNOWN: &str = cys::ERR_WRITE_OUTCOME_UNKNOWN;
/// 데몬이 **쓰기 전에** 거부했음이 코드로 보장되는 오류 코드(handlers.rs `surface.send_text` 분기 · 거부 = 바이트 0).
/// 이 목록 밖 코드·코드 없음·꼴이 이상한 응답은 「쓰기 0」의 근거가 아니므로 `uncertain`(다시 보내기 금지)으로 접는다(codex 1R major).
/// 근거(이 가지 src/bin/cysd/handlers.rs `"surface.send_text"` 분기 7543~8377 · codex 4R 요청으로 줄 명시 · 독립 검증 VERIFY 지적 4 로 정정):
/// - 사람 표지 요청(`human:true` · `machine_origin:false`)은 `direct_agent_intent`(:3816~3839)가 첫 줄 :3824 에서 None → 에이전트 작업 길이 아니다.
///   쓰기 인계 = **`try_write` 직접(:8248)** · 넘기는 것 = `WriteReq::Inject{cr_delay_ms:400, clear_first:true, guard:None}`(:3773~3785).
/// - 그래서 응답 `sent:true` 는 「썼다」가 아니라 **「writer 줄에 넣었다」**(:8248 뒤 :8370) — 바이트는 그 뒤 ≈0.74초에 걸쳐 나간다(VM 증거:
///   응답 2.95ms · 쓰기 737.8ms). writer 단계에서 생긴 일은 호출자에게 돌아오지 않는다 → 화면은 `written` 을 「전달 확인 중」으로만 칠한다.
/// - 그 자리 오류 = `try_write`(:386~402) 의 `write_stalled`·`write_failed` 둘뿐(목록 밖 → `uncertain`).
/// - 아래 목록 가운데 이 요청 꼴에서 **닿지 않는** 것(죽은 갈래 · 다른 요청 꼴 대비로 둠): `invalid_params` :8112(에이전트 작업 길) ·
///   `journal_unavailable` :8303(에이전트 작업 길) · `typing_guard` :7878(사람 아닌 쓰기). 분류의 `write_outcome_unknown` · `queued_hold`(정비 보류
///   :7608 `if !human` 전용)도 같다.
const PRE_WRITE_REFUSALS: &[&str] = &[
    "invalid_params",          // :7545·:7548 본문·좌석 결측 · :7659 clear_first+queued · (:8112 UTF-8 = 에이전트 작업 길 · 이 요청 꼴은 안 닿음)
    "not_found",               // :7553 좌석 없음
    "target_changed",          // :7558 「nothing was typed」
    "process_exited",          // :7566 좌석 프로세스 끝남
    "acl_denied",              // :7599 ACL 거부(reject_send · last_human_input 도 안 찍음)
    "clear_first_unsupported", // :7667 launch-agent 등록 좌석 아님
    cys::ERR_TYPING_GUARD,        // :7957~7962·:8207~8218 초안 게이트(draft_gate_denied_response :2983 → 이 코드 · 토큰을 못 읽은 좌석 안 앱일 때만 :7911~7912) · (:7878 = 사람 아닌 쓰기)
    cys::ERR_JOURNAL_UNAVAILABLE, // (:8303 에이전트 작업 길 · 이 요청 꼴은 안 닿음) 「zero bytes written … nothing was typed」(:4704~4706)
    "no_agent",                // (1.1.16 · cysr-1116-integ-1118) 빈 셸 좌석 — 사람 표지 + refuse_on_approval 요청은 cysd `surface.send_text` 빈 셸 가드 앞 갈래가 타이핑 0 · 큐 0 으로 거절(이 요청 꼴은 큐 보류 갈래 `!human` 에 안 닿음)
];
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
/// - `failed`    : 쓰기 전 거부가 보장된 코드(`PRE_WRITE_REFUSALS`) · 전송 전 끊김(Definite = 데몬이 못 봄)
/// - `uncertain` : 전송 뒤 끊김·응답 파싱 실패(Uncertain) · `write_outcome_unknown` · 목록 밖 코드·코드 없음 · `ok` 칸 없음 · ok 인데 `sent` 를 확인 못 함
pub(crate) fn classify_send(r: Result<Value, (TransportClass, String)>) -> Value {
    match r {
        Err((TransportClass::Definite, e)) => json!({"outcome": "failed", "code": "transport_definite", "message": e}),
        Err((TransportClass::Uncertain, e)) => json!({"outcome": "uncertain", "code": "transport_uncertain", "message": e}),
        Ok(resp) => {
            if resp["ok"].as_bool().is_none() {
                return json!({"outcome": "uncertain", "code": "malformed_response"});
            }
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
                    c if PRE_WRITE_REFUSALS.contains(&c) => "failed",
                    _ => "uncertain",
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

/// (조각 4 · codex 1R major 5 · blocking) `feed.reply` 매개변수(순수). `screen_fingerprint` = 화면이 펼쳐 본 판의 데몬 지문(있을 때만 싣는다 —
/// 데몬이 집행 직전 지금 창 지문과 대조하는 자리 · 지금 데몬은 이 칸을 모르고 화면도 지문 없는 판엔 허락을 내지 않는다).
pub(crate) fn confirm_reply_params(request_id: &str, decision: &str, screen_fingerprint: Option<&str>, tok: Option<&str>) -> Value {
    let mut p = json!({"request_id": request_id, "decision": decision});
    if let Some(f) = screen_fingerprint.filter(|f| !f.is_empty()) {
        p["screen_fingerprint"] = json!(f);
    }
    if let Some(t) = tok {
        p["operator_token"] = json!(t);
    }
    p
}

/// 데몬 응답 → 화면 결과(순수). ok 면 `result` 그대로(`actuated` = 창을 실제로 눌렀는지 · null = 기록만 해소) · 아니면 `"<code>: <message>"`.
pub(crate) fn confirm_reply_outcome(resp: &Value) -> Result<Value, String> {
    if resp["ok"].as_bool() == Some(true) {
        Ok(resp["result"].clone())
    } else {
        Err(format!(
            "{}: {}",
            resp["error"]["code"].as_str().unwrap_or("error"),
            resp["error"]["message"].as_str().unwrap_or("unknown error")
        ))
    }
}

/// `confirm_reply` — 대화 화면 직접 허락·거절(본부 데몬 승인 항목 한정). 원작자 `feed_reply` 와 같은 operator token 첨부·1회 재시도이되
/// **데몬 결과를 버리지 않고** 돌려준다(`feed_reply` 는 `Ok(())` 로 `actuated` 를 버려 「기록만 해소」를 「집행 성공」으로 보이게 했다 · codex 1R major 5).
/// allow/deny 만 받는다. 원작자 `feed_reply` 는 손대지 않는다(작업 화면 동작 변화 0).
#[tauri::command]
pub async fn confirm_reply(request_id: String, decision: String, screen_fingerprint: Option<String>) -> Result<Value, String> {
    if decision != "allow" && decision != "deny" {
        return Err(format!("invalid_decision: {decision}"));
    }
    let sock = resolve_socket(&None);
    let call = |sock: std::path::PathBuf| {
        let params = confirm_reply_params(&request_id, &decision, screen_fingerprint.as_deref(), read_operator_token_for(&sock).as_deref());
        async move { rpc_full(&sock, "feed.reply", params).await }
    };
    let mut resp = call(sock.clone()).await?;
    // feed_reply 와 같은 좁은 창(토큰 회전 경합) — 신선 재독으로 1회만 재시도.
    if resp["ok"].as_bool() != Some(true) && matches!(resp["error"]["code"].as_str(), Some("self_approval_denied") | Some("owner_gui_required")) {
        resp = call(sock).await?;
    }
    confirm_reply_outcome(&resp)
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
/// 레코드 = `{uuid, parent, role:"user"|"assistant", text(없으면 null), parts, ts, sidechain, at}` — user/assistant 전부(글 없는 고리 포함). 줄 파싱 실패는 건너뛴다(세기만).
/// (조각 3 고침 · 검증 지적 B) 그 밖 종류(attachment·system 등)도 uuid 가 있으면 **글 없는 고리** `{uuid, parent, role:"link", text:null, …}` 로 넘긴다 —
/// 진짜 기록은 사람 말과 첫 답 사이에 이런 레코드(훅이 덧붙인 글 등)가 끼어, 빼면 답의 부모 사슬이 끊긴다. 본문·종류 이름·시각은 넘기지 않는다(NFR-S3 · 글 0자).
/// `at` = 그 줄이 시작하는 **덩이 안** 바이트 위치(`read_transcript_from` 이 파일 위치로 바꿈 · 조각 4 codex 1R minor — 앞 훑기·뒤 읽기 겹침을 위치로 가름).
pub(crate) fn parse_transcript_chunk(buf: &[u8]) -> (Vec<Value>, usize, usize) {
    let consumed = match buf.iter().rposition(|&b| b == b'\n') {
        Some(i) => i + 1,
        None => 0,
    };
    let mut out = Vec::new();
    let mut bad = 0usize;
    let mut pos = 0usize;
    for line in buf[..consumed].split(|&b| b == b'\n') {
        let at = pos;
        pos += line.len() + 1;
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
            _ => {
                let Some(uuid) = v["uuid"].as_str() else { continue };
                out.push(json!({
                    "uuid": uuid,
                    "parent": v["parentUuid"].as_str(),
                    "role": "link",
                    "text": Value::Null,
                    "parts": Value::Null,
                    "ts": Value::Null,
                    "sidechain": v["isSidechain"].as_bool().unwrap_or(false),
                    // (통합 1116) 고리도 줄 위치를 싣는다 — 조각 4 앞 훑기는 끝을 넘는 토막에 위치 없는 레코드가 하나라도 있으면
                    // 「다 훑음」을 확정하지 않으므로(confirm.ts scanStep), 위치 없는 고리가 끼면 띠가 「살펴보는 중」에 머문다. 위치 = 바이트 수(글 0자 · NFR-S3 그대로).
                    "at": at,
                }));
                continue;
            }
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
            "at": at,
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

/// 결속 파일 열기(파일 IO) — 신뢰 뿌리(설정 폴더)를 연 **폴더 핸들**에서 상대 경로 요소를 하나씩 링크를 따르지 않고 연다(유닉스 `openat`
/// + `O_NOFOLLOW`) — 중간 폴더·파일 어느 자리에 링크가 있거나 도중에 바뀌어도 뿌리 밖·다른 파일로 갈 수 없다(codex 2R·3R major).
/// 경로 문자열로 다시 찾아 확인하는 단계가 없다(확인·열기 사이 바꿔치기 0). 뿌리 자체(설정 폴더)는 데몬이 준 값이라 링크여도 따른다.
#[cfg(unix)]
pub(crate) fn open_bound(cfg: &std::path::Path, expected: &std::path::Path) -> Result<std::fs::File, &'static str> {
    use std::ffi::CString;
    use std::os::unix::ffi::OsStrExt;
    use std::os::unix::io::FromRawFd;
    let rel = expected.strip_prefix(cfg).map_err(|_| "outside_config_dir")?;
    let parts: Vec<&std::ffi::OsStr> = rel
        .components()
        .map(|c| match c {
            std::path::Component::Normal(n) => Ok(n),
            _ => Err("bad_component"),
        })
        .collect::<Result<_, _>>()?;
    if parts.is_empty() {
        return Err("bad_component");
    }
    let root = CString::new(cfg.as_os_str().as_bytes()).map_err(|_| "bad_component")?;
    // SAFETY: 경로는 NUL 없는 CString · 돌려받은 fd 는 아래에서 닫거나 File 로 넘긴다.
    let mut fd = unsafe { libc::open(root.as_ptr(), libc::O_RDONLY | libc::O_DIRECTORY | libc::O_CLOEXEC) };
    if fd < 0 {
        return Err("no_config_dir");
    }
    for (i, part) in parts.iter().enumerate() {
        let last = i + 1 == parts.len();
        let name = match CString::new(part.as_bytes()) {
            Ok(n) => n,
            Err(_) => {
                unsafe { libc::close(fd) };
                return Err("bad_component");
            }
        };
        let flags = libc::O_RDONLY | libc::O_NOFOLLOW | libc::O_CLOEXEC | if last { 0 } else { libc::O_DIRECTORY };
        // SAFETY: fd 는 위에서 연 폴더 · name 은 NUL 없는 CString.
        let next = unsafe { libc::openat(fd, name.as_ptr(), flags) };
        unsafe { libc::close(fd) };
        if next < 0 {
            let e = std::io::Error::last_os_error().raw_os_error();
            return Err(match e {
                Some(libc::ELOOP) => "symlinked_path",
                Some(libc::ENOTDIR) => "symlinked_path",
                Some(libc::ENOENT) => "no_file",
                _ => "no_file",
            });
        }
        fd = next;
    }
    // SAFETY: fd 는 방금 연 유일한 소유 fd.
    let f = unsafe { std::fs::File::from_raw_fd(fd) };
    if !f.metadata().map(|m| m.is_file()).unwrap_or(false) {
        return Err("not_a_file");
    }
    Ok(f)
}

/// 윈도 — 폴더 핸들 기준 상대 열기·reparse point 차단을 아직 만들지 않았다 → **읽지 않는다**(codex 4R major · 경로 재탐색 대조는 바꿔치기를 못 막음).
/// 화면은 「모름」(전달 확인 중 → 오래 걸려요)으로 남는다. 윈 구현·실측 = 조각 10.
#[cfg(not(unix))]
pub(crate) fn open_bound(_cfg: &std::path::Path, _expected: &std::path::Path) -> Result<std::fs::File, &'static str> {
    Err("unsupported_platform")
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
    // 다른 프로젝트 폴더는 뒤지지 않는다(codex 1R major — 같은 이름 파일이 다른 cwd 의 기록일 수 있음). 링크를 풀어 설정 폴더 안인지 확인.
    let cfg = lrow["claude_config_dir"].as_str().unwrap_or_default();
    let file = match open_bound(std::path::Path::new(cfg), &path) {
        Ok(f) => f,
        Err(why) => return Ok(json!({"status": "unknown", "why": why, "session_id": sid})),
    };
    if from_end.unwrap_or(false) {
        // 대화 화면을 처음 띄울 때 — 지난 기록을 다 읽지 않고 끝에서 시작한다(이후 새 바이트만).
        // 시작점 = **마지막 완성 줄의 끝**(쓰는 중인 미완 줄은 뒤 읽기가 그 줄 처음부터 읽는다 · codex 2R major — 줄 중간을 시작점으로 잡으면
        // 앞 훑기와 뒤 읽기가 같은 줄을 서로 다른 위치로 받아 해결 표식을 두 번 셌다).
        let size = file.metadata().map_err(|e| e.to_string())?.len();
        let start = last_line_end(&file, size)?;
        return Ok(json!({"status": "ok", "session_id": sid, "next_offset": start, "size": size, "records": [], "bad_lines": 0, "reset": false}));
    }
    read_transcript_from(file, after_offset).map(|mut v| {
        v["session_id"] = json!(sid);
        v
    })
}

/// 연 결속 파일 핸들을 오프셋부터 읽는다(파일 IO · 경로로 다시 열지 않음).
pub(crate) fn read_transcript_from(mut f: std::fs::File, after_offset: u64) -> Result<Value, String> {
    use std::io::{Read, Seek, SeekFrom};
    let size = f.metadata().map_err(|e| e.to_string())?.len();
    // 파일이 줄었으면(새 세션이 같은 이름? · 잘림) 처음부터 — 화면은 `reset` 으로 짝짓기를 다시 한다.
    let (start, reset) = if after_offset > size { (0, true) } else { (after_offset, false) };
    f.seek(SeekFrom::Start(start)).map_err(|e| e.to_string())?;
    let want = (size - start).min(TRANSCRIPT_READ_MAX);
    let mut buf = Vec::with_capacity(want as usize);
    (&f).take(want).read_to_end(&mut buf).map_err(|e| e.to_string())?;
    let (mut records, consumed, bad) = parse_transcript_chunk(&buf);
    for r in records.iter_mut() {
        if let Some(rel) = r["at"].as_u64() {
            r["at"] = json!(start + rel); // 덩이 안 위치 → 파일 위치
        }
    }
    let mut next = start + consumed as u64;
    let mut skipped: u64 = 0;
    let mut long_open = false;
    // (조각 4 · 독립 검증 F3) 한 줄이 읽기 한도보다 길면 줄 끝이 없어 영영 못 나아갔다(앞 훑기 「다 훑음」 오판 · 뒤 읽기 정지).
    //   그 줄은 내용을 읽지 않고 다음 줄 끝까지 건너뛰고 건너뛴 바이트를 알린다(화면 = 그 세션 물음은 「모름」 유지).
    //   줄 끝이 아직 없으면(쓰는 중) 그대로 두고 `long_line_open` 만 알린다.
    if consumed == 0 && buf.len() as u64 == TRANSCRIPT_READ_MAX {
        match next_newline_after(&f, start + buf.len() as u64, size)? {
            Some(end) => {
                skipped = end - start;
                next = end;
            }
            None => long_open = true,
        }
    }
    Ok(json!({
        "status": "ok",
        "next_offset": next,
        "size": size,
        "records": records,
        "bad_lines": bad,
        "reset": reset,
        "skipped_bytes": skipped,
        "long_line_open": long_open,
    }))
}

/// `size` 앞 마지막 `\n` 바로 뒤 오프셋(= 마지막 완성 줄의 끝 · 미완 줄의 시작) · `\n` 이 없으면 0. 뒤에서 64 KiB 씩 거슬러 읽는다(끝이 `\n` 이면 1바이트).
pub(crate) fn last_line_end(mut f: &std::fs::File, size: u64) -> Result<u64, String> {
    use std::io::{Read, Seek, SeekFrom};
    let mut end = size;
    let mut chunk = vec![0u8; 64 * 1024];
    while end > 0 {
        let n = end.min(64 * 1024);
        let from = end - n;
        f.seek(SeekFrom::Start(from)).map_err(|e| e.to_string())?;
        f.read_exact(&mut chunk[..n as usize]).map_err(|e| e.to_string())?;
        if let Some(i) = chunk[..n as usize].iter().rposition(|&b| b == b'\n') {
            return Ok(from + i as u64 + 1);
        }
        end = from;
    }
    Ok(0)
}

/// `from` 부터 `size` 까지 첫 `\n` 뒤 오프셋(내용은 버림 · 64 KiB 씩) · 없으면 None.
pub(crate) fn next_newline_after(mut f: &std::fs::File, from: u64, size: u64) -> Result<Option<u64>, String> {
    use std::io::{Read, Seek, SeekFrom};
    f.seek(SeekFrom::Start(from)).map_err(|e| e.to_string())?;
    let mut pos = from;
    let mut chunk = vec![0u8; 64 * 1024];
    while pos < size {
        let n = f.read(&mut chunk[..((size - pos).min(64 * 1024)) as usize]).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        if let Some(i) = chunk[..n].iter().position(|&b| b == b'\n') {
            return Ok(Some(pos + i as u64 + 1));
        }
        pos += n as u64;
    }
    Ok(None)
}

// ---------- (s79 · TICKET=cysr-1116-s79-1119 · 조각 7) 결과 열기·폴더 보기 ----------

/// 「열기」를 거절하는 확장자(대소문자 무시 · 양 OS 공통) — 실행 꾸러미(맥 `.app` 등은 **폴더**라 `open_path` 의 실행형 **파일** 검사를 지나간다) ·
/// URL·바로가기(`.webloc`·`.url`·`.lnk` 등 = 열면 OS 가 링크 대상을 엶) · 스크립트·설치기(연결 프로그램이 실행) — codex 2R blocking.
/// ★목록 정본 = 이 배열과 `ui/src/views/judge/results.ts` 의 `OPEN_REFUSED_EXT` — 두 목록이 같아야 한다(bun 시험 「열기 거절 확장자 = Rust 와 같은 목록」이 이 소스를 읽어 대조).
/// 폴더 보기(reveal)는 거절하지 않는다(파일 관리자에서 고르기만 · 실행 0).
pub(crate) const OPEN_REFUSED_EXT: &[&str] = &[
    "action", "app", "appex", "applescript", "application", "appref-ms", "bash", "bat", "bundle", "cmd", "com", "command", "cpl", "csh", "desktop", "exe", "framework", "gadget", "hta", "inetloc", "jar", "js", "jse", "kext", "lnk", "mpkg", "msc", "msi", "msp", "mst", "pif", "pkg", "plugin", "prefpane", "ps1", "psm1", "qlgenerator", "reg", "saver", "scpt", "scptd", "scr", "sh", "terminal", "tool", "url", "vb", "vbe", "vbs", "webloc", "website", "workflow", "ws", "wsf", "wsh", "xpc", "zsh",
];

/// 결과 경로의 정규 대상(심볼릭 링크를 끝까지 풂) — 정규 홈 **아래**(홈 자신 아님) · 홈 아래 마디에 숨은 이름(`.` 시작) 0.
/// 화면(judge/results)의 이름 검사는 글만 본다 — 홈 안 평범한 이름이 홈 밖(예 `/Applications/X.app`)을 가리키는 링크면 그 검사를 지나간다(codex 1R blocking).
pub(crate) fn result_target(path: &std::path::Path, home: &std::path::Path) -> Result<std::path::PathBuf, String> {
    let home_c = std::fs::canonicalize(home).map_err(|e| format!("not a local path: {e}"))?;
    let t = std::fs::canonicalize(path).map_err(|e| format!("not a local path: {e}"))?;
    if is_network_path(&t.to_string_lossy()) {
        return Err("network_path".into()); // (codex 2R) 윈도 UNC 홈·UNC 대상 = 로컬 아님 → 거절(맥 홈 아래 네트워크 마운트 판별은 안 함 = 알려진 한계)
    }
    let rel = t.strip_prefix(&home_c).map_err(|_| "outside_home".to_string())?;
    if rel.as_os_str().is_empty() {
        return Err("outside_home".into());
    }
    for c in rel.components() {
        match c {
            std::path::Component::Normal(seg) if !seg.to_string_lossy().starts_with('.') => {}
            std::path::Component::Normal(_) => return Err("hidden_path".into()),
            _ => return Err("outside_home".into()),
        }
    }
    Ok(t)
}

/// (s79 · 독립 검증 V1·V2 · master#beb80154) 「열기」 **허용 목록** — 보통 파일은 이 확장자(웹 페이지·문서·그림)만 OS 에 넘긴다 · 그 밖 = `executable_confirm`(폴더 보기만).
/// 거부 목록(OPEN_REFUSED_EXT)만으로는 목록 밖 처리기(`.fileloc`·`.webloc`·윈 `.url`·`.appref-ms`…)가 홈 밖 앱·URL 을 열었다(2272 실측).
/// ★목록 정본 = 이 배열과 `ui/src/views/judge/results.ts` 의 `OPEN_ALLOWED_EXT`(= PAGE·DOC·IMAGE) — bun 시험이 이 소스를 읽어 대조.
/// 거부 목록은 꾸러미 **폴더**(`.app` 등) 판정과 이중 방어로 남긴다(허용 목록은 파일만 덮음).
pub(crate) const OPEN_ALLOWED_EXT: &[&str] = &[
    "bmp", "csv", "doc", "docx", "gif", "heic", "htm", "html", "hwp", "hwpx", "jpeg", "jpg", "md", "odt", "pdf", "png", "ppt", "pptx", "rtf", "svg", "txt", "webp", "xls", "xlsx",
];

/// 맥 Finder 가명(bookmark) — 파일 머리 `book\0\0\0\0mark` 또는 `com.apple.FinderInfo` Finder flags kIsAlias(0x8000). 이름이 `행사안내.html` 이어도 LaunchServices 가 대상(홈 밖 앱)을 연다(2272 V1 실측).
pub(crate) fn is_alias(p: &std::path::Path) -> bool {
    use std::io::Read;
    let mut head = [0u8; 16];
    if let Ok(mut f) = std::fs::File::open(p) {
        if f.read(&mut head).ok() == Some(16) && &head[..12] == b"book\0\0\0\0mark" {
            return true;
        }
    }
    #[cfg(target_os = "macos")]
    {
        use std::os::unix::ffi::OsStrExt;
        let Ok(path) = std::ffi::CString::new(p.as_os_str().as_bytes()) else { return true };
        let name = c"com.apple.FinderInfo";
        let mut buf = [0u8; 32];
        // SAFETY: path·name 은 NUL 로 끝나는 C 문자열 · buf 는 32 바이트(FinderInfo 크기) · position 0 · options 0(링크 따라감 — 정규 경로라 링크 없음)
        let n = unsafe { libc::getxattr(path.as_ptr(), name.as_ptr(), buf.as_mut_ptr().cast(), buf.len(), 0, 0) };
        if n >= 10 && u16::from_be_bytes([buf[8], buf[9]]) & 0x8000 != 0 {
            return true;
        }
    }
    false
}

/// 「열기」 판정(정규 대상 · OS 에 넘기기 전) — 꾸러미 확장자 = 거절 · 꾸러미 아닌 폴더 = 허용 · 보통 파일 = 허용 목록 확장자 ∧ 가명 아님 ∧(윈) 숨김·시스템 속성 아님.
pub(crate) fn open_verdict(t: &std::path::Path) -> Result<(), String> {
    if is_launch_bundle(t) {
        return Err("executable_confirm".into());
    }
    let meta = std::fs::metadata(t).map_err(|e| format!("not a local path: {e}"))?;
    if meta.is_dir() {
        return Ok(());
    }
    if !meta.is_file() {
        return Err("executable_confirm".into());
    }
    let ext = t.extension().map(|e| e.to_string_lossy().to_ascii_lowercase()).unwrap_or_default();
    if !OPEN_ALLOWED_EXT.contains(&ext.as_str()) || is_alias(t) {
        return Err("executable_confirm".into());
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        if meta.file_attributes() & 0x6 != 0 {
            return Err("executable_confirm".into()); // FILE_ATTRIBUTE_HIDDEN(0x2)·SYSTEM(0x4) — AppData 류 숨은 자리의 바로가기 막음(2272 V2 minor)
        }
    }
    Ok(())
}

/// 정규 경로가 네트워크(UNC) 꼴인가 — `\\?\UNC\…` 또는 `\\server\…`(드라이브 꼴 `\\?\C:\` 은 아님). 맥·리눅스 경로는 늘 false.
pub(crate) fn is_network_path(s: &str) -> bool {
    s.starts_with(r"\\?\UNC\") || (s.starts_with(r"\\") && !s.starts_with(r"\\?\"))
}

/// 정규 대상이 열기 거절 확장자인가(대소문자 무시).
pub(crate) fn is_launch_bundle(p: &std::path::Path) -> bool {
    p.extension().map(|e| e.to_string_lossy().to_ascii_lowercase()).is_some_and(|e| OPEN_REFUSED_EXT.contains(&e.as_str()))
}

/// 윈도 정규 경로의 `\\?\C:\` 머리를 벗긴다(탐색기·셸이 그 꼴을 못 받는 경우) — 드라이브 꼴일 때만.
fn plain_path(p: &std::path::Path) -> String {
    let s = p.to_string_lossy().into_owned();
    #[cfg(windows)]
    {
        let b = s.as_bytes();
        if s.starts_with(r"\\?\") && b.len() > 6 && b[5] == b':' && b[4].is_ascii_alphabetic() {
            return s[4..].to_string();
        }
    }
    s
}

/// 결과 받기 카드의 「열기」·「폴더 보기」 — 마스터 글에서 온 경로라 정규 대상으로 다시 가둔다:
/// 정규 홈 아래 · 숨은 마디 0 · 열기면 실행 꾸러미 거절(`executable_confirm` · 화면은 force 로 다시 부르지 않음) · 그 밖은 기존 `open_path`(실행형 파일 게이트 · force 없음)·`reveal_path`.
/// ⚠알려진 한계(TOCTOU · master#c48208b6 처분 = 고치지 않고 문서): 정규화 뒤 경로 **이름**을 넘기므로, 그 사이 같은 사용자 권한의 로컬 프로세스가
///   조상 폴더를 링크로 바꿔치기하면 다른 대상이 열릴 수 있다 — 그 프로세스는 이미 무엇이든 열 수 있어 새 권한을 주지 않는다(HANDOFF 「알려진 한계」).
#[tauri::command]
pub fn result_open(path: String, reveal: Option<bool>) -> Result<(), String> {
    let target = result_target(std::path::Path::new(&path), &cys::home_dir())?;
    if reveal.unwrap_or(false) {
        return crate::reveal_path(plain_path(&target));
    }
    open_verdict(&target)?; // (s79 · V1·V2) 허용 목록 · 가명 · 꾸러미 — 그 밖 = executable_confirm(화면 = 폴더 보기 안내)
    crate::open_path(plain_path(&target), None)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn result_target_confines_to_canonical_home() {
        // (s79 · codex 1R blocking) 홈 안 링크가 홈 밖을 가리키면 거절 · 숨은 마디 거절 · 홈 자신 거절 · 정상 = 정규 대상
        let base = std::env::temp_dir().join(format!("vc-res-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        let home = base.join("home");
        let out = base.join("Applications").join("Evil.app");
        std::fs::create_dir_all(home.join("교회")).unwrap();
        std::fs::create_dir_all(home.join(".cys")).unwrap();
        std::fs::create_dir_all(&out).unwrap();
        std::fs::write(home.join("교회").join("a.html"), b"x").unwrap();
        std::fs::write(home.join(".cys").join("s.md"), b"x").unwrap();
        let ok = result_target(&home.join("교회").join("a.html"), &home).unwrap();
        assert!(ok.ends_with("교회/a.html") || ok.ends_with("교회\\a.html"));
        #[cfg(unix)]
        {
            std::os::unix::fs::symlink(&out, home.join("Report")).unwrap();
            assert_eq!(result_target(&home.join("Report"), &home).unwrap_err(), "outside_home");
            std::os::unix::fs::symlink(home.join(".cys"), home.join("plain")).unwrap();
            assert_eq!(result_target(&home.join("plain").join("s.md"), &home).unwrap_err(), "hidden_path");
        }
        assert_eq!(result_target(&home.join(".cys").join("s.md"), &home).unwrap_err(), "hidden_path");
        assert_eq!(result_target(&home.join("교회").join("..").join("..").join("Applications"), &home).unwrap_err(), "outside_home");
        assert_eq!(result_target(&home, &home).unwrap_err(), "outside_home");
        assert!(result_target(&home.join("없음.pdf"), &home).unwrap_err().starts_with("not a local path"));
        assert!(is_launch_bundle(&out));
        assert!(is_launch_bundle(std::path::Path::new("/x/A.APP")));
        assert!(!is_launch_bundle(&ok));
        // (codex 2R) URL·바로가기·스크립트도 열기 거절 · 대소문자 무시
        for n in ["a.webloc", "a.URL", "a.inetloc", "a.lnk", "a.sh", "a.command", "a.tool", "a.terminal", "a.scpt", "a.applescript", "a.workflow", "a.ps1", "a.bat", "a.cmd", "a.vbs", "a.js", "a.jse", "a.wsf", "a.hta", "a.reg", "a.msi", "a.scr", "a.EXE"] {
            assert!(is_launch_bundle(std::path::Path::new(n)), "{n}");
        }
        for n in ["a.html", "a.pdf", "a.png", "a.md", "a.hwp", "dir"] {
            assert!(!is_launch_bundle(std::path::Path::new(n)), "{n}");
        }
        // (s79 · 독립 검증 V1·V2) 열기 판정 = 허용 목록 · 가명 · 꾸러미 — 2272 표본
        let d = home.join("교회");
        assert_eq!(open_verdict(&ok), Ok(()));
        assert_eq!(open_verdict(&d), Ok(()));
        let mut alias = b"book\0\0\0\0mark\0\0\0\0".to_vec();
        alias.extend_from_slice(&[0u8; 64]);
        std::fs::write(d.join("행사안내.html"), &alias).unwrap(); // 가명인데 이름은 문서
        std::fs::write(d.join("주보 최종"), &alias).unwrap(); // 가명 · 확장자 없음
        std::fs::write(d.join("p.fileloc"), b"<plist/>").unwrap();
        std::fs::write(d.join("p.webloc"), b"<plist/>").unwrap();
        for n in ["행사안내.html", "주보 최종", "p.fileloc", "p.webloc"] {
            assert_eq!(open_verdict(&d.join(n)).unwrap_err(), "executable_confirm", "{n}");
        }
        for n in ["a.url", "a.appref-ms", "a.settingcontent-ms", "a.library-ms", "a.search-ms", "a.application", "a.appinstaller", "a.msix", "a.appx", "a.chm", "a.iso", "a.img", "a.vhd", "a.vhdx", "a.inf", "a.sct", "a.wsc", "a.ws", "a.msp", "a.psc1", "a.jnlp", "a.xll", "a.diagcab", "a.website", "a.theme", "a.exe", "a.py"] {
            std::fs::write(d.join(n), b"x").unwrap();
            assert_eq!(open_verdict(&d.join(n)).unwrap_err(), "executable_confirm", "{n}");
        }
        std::fs::create_dir_all(d.join("In.app")).unwrap();
        assert_eq!(open_verdict(&d.join("In.app")).unwrap_err(), "executable_confirm");
        #[cfg(target_os = "macos")]
        {
            // FinderInfo kIsAlias(0x8000) 만 선 옛 꼴 가명 — xattr 도구로 표지를 씀(도구가 없으면 건너뜀)
            let f = d.join("옛가명.pdf");
            std::fs::write(&f, b"%PDF-1.4").unwrap();
            let hex = "0000000000000000800000000000000000000000000000000000000000000000";
            if std::process::Command::new("/usr/bin/xattr").args(["-wx", "com.apple.FinderInfo", hex]).arg(&f).status().is_ok_and(|s| s.success()) {
                assert_eq!(open_verdict(&f).unwrap_err(), "executable_confirm");
            }
        }
        assert!(is_network_path(r"\\?\UNC\srv\share\a.pdf"));
        assert!(is_network_path(r"\\srv\share\a.pdf"));
        assert!(!is_network_path(r"\\?\C:\Users\x\a.pdf"));
        assert!(!is_network_path("/Users/x/a.pdf"));
        let _ = std::fs::remove_dir_all(&base);
    }

    #[test]
    fn over_long_line_is_skipped_to_next_line_end_and_reported() {
        // (조각 4 · 독립 검증 F3) 한도보다 긴 한 줄 → 다음 줄 끝까지 건너뜀 + skipped_bytes · 줄 끝이 아직 없으면 그대로 + long_line_open
        let dir = std::env::temp_dir().join(format!("vc-long-{}", std::process::id()));
        let _ = std::fs::create_dir_all(&dir);
        let p = dir.join("s.jsonl");
        let long = vec![b'x'; TRANSCRIPT_READ_MAX as usize + 10];
        let rec = br#"{"type":"assistant","uuid":"a2","message":{"content":"after"}}"#;
        let mut body = long.clone();
        body.push(b'\n');
        body.extend_from_slice(rec);
        body.push(b'\n');
        std::fs::write(&p, &body).unwrap();
        let v = read_transcript_from(std::fs::File::open(&p).unwrap(), 0).unwrap();
        assert_eq!(v["skipped_bytes"], long.len() as u64 + 1);
        assert_eq!(v["next_offset"], long.len() as u64 + 1);
        assert_eq!(v["long_line_open"], false);
        let w = read_transcript_from(std::fs::File::open(&p).unwrap(), long.len() as u64 + 1).unwrap();
        assert_eq!(w["records"][0]["uuid"], "a2", "건너뛴 뒤 다음 줄을 읽는다");
        assert_eq!(w["skipped_bytes"], 0);
        std::fs::write(&p, &long).unwrap(); // 줄 끝이 아직 없음(쓰는 중)
        let o = read_transcript_from(std::fs::File::open(&p).unwrap(), 0).unwrap();
        assert_eq!(o["next_offset"], 0);
        assert_eq!(o["long_line_open"], true);
        assert_eq!(o["skipped_bytes"], 0);
        let _ = std::fs::remove_dir_all(&dir);
    }

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
        assert_eq!(err("acl_denied")["outcome"], "failed");
        assert_eq!(err("typing_guard")["outcome"], "failed");
        // (1.1.16 · cysr-1116-integ-1118 · master#f7e14a93) 빈 셸 좌석 = 사람 표지 + refuse_on_approval 요청은 쓰기 0 · 큐 0(cysd eca3b956) → 못 보냄 + 다시 보내기
        assert_eq!(err("no_agent")["outcome"], "failed");
        assert_eq!(err("")["outcome"], "uncertain", "코드 없음 = 쓰기 0 근거 아님");
        assert_eq!(err("something_new")["outcome"], "uncertain");
        assert_eq!(classify_send(Ok(json!({})))["outcome"], "uncertain", "ok 칸 없음");
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
        assert_eq!(transcript_slug("/sandbox/a/axdev/.wt/x-1"), "-sandbox-a-axdev--wt-x-1");
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
        // (조각 3 고침 · 검증 지적 B) uuid 있는 다른 종류 = 글 없는 고리(본문·종류 이름·시각 안 넘김)
        let att = r#"{"type":"attachment","uuid":"x1","parentUuid":"u2","timestamp":"t3","attachment":{"type":"hook_additional_context","content":["비밀 글"]}}"#;
        let partial = r#"{"type":"user","uuid":"u3""#;
        let buf = format!("{a}\n{b}\n{tool}\n{meta}\n{att}\nnot json\n{partial}");
        let (recs, consumed, bad) = parse_transcript_chunk(buf.as_bytes());
        assert_eq!(recs.len(), 4, "user·assistant·도구 결과 고리(글 없음)·다른 종류 고리 — uuid 없는 요약 레코드는 뺌");
        assert_eq!(recs[3]["role"], "link");
        assert_eq!(recs[3]["uuid"], "x1");
        assert_eq!(recs[3]["parent"], "u2");
        assert!(recs[3]["text"].is_null() && recs[3]["parts"].is_null() && recs[3]["ts"].is_null());
        assert!(!recs[3].to_string().contains("비밀") && !recs[3].to_string().contains("hook_additional_context"), "고리에 본문·종류 이름 0");
        // (통합 1116) 고리도 줄 시작 위치(조각 4 앞 훑기가 위치로 앞·뒤 기록을 가름)
        assert_eq!(recs[3]["at"].as_u64(), Some((a.len() + 1 + b.len() + 1 + tool.len() + 1 + meta.len() + 1) as u64));
        assert_eq!(recs[0]["role"], "user");
        assert_eq!(recs[0]["text"], "안녕");
        assert_eq!(recs[1]["parent"], "u1");
        assert_eq!(recs[1]["text"], "네, 안녕하세요");
        assert!(recs[2]["text"].is_null());
        assert_eq!(recs[2]["parent"], "a1");
        assert_eq!(bad, 1);
        assert_eq!(consumed, buf.len() - partial.len());
    }

    #[cfg(unix)]
    #[test]
    fn open_bound_rejects_links_below_root_and_accepts_exact_file() {
        let base = std::env::temp_dir().join(format!("viewcore-c-{}", std::process::id()));
        let cfg = base.join("cfg");
        let pa = cfg.join("projects/-a");
        let pb = cfg.join("projects/-b");
        std::fs::create_dir_all(&pa).unwrap();
        std::fs::create_dir_all(&pb).unwrap();
        let ok = pa.join("abcdefgh.jsonl");
        std::fs::write(&ok, "{}\n").unwrap();
        let other = pb.join("otherid0.jsonl");
        std::fs::write(&other, "{}\n").unwrap();
        let secret = base.join("secret.txt");
        std::fs::write(&secret, "x").unwrap();
        let out_link = pa.join("linked00.jsonl");
        std::os::unix::fs::symlink(&secret, &out_link).unwrap();
        let in_link = pa.join("inside00.jsonl");
        std::os::unix::fs::symlink(&other, &in_link).unwrap();
        std::os::unix::fs::symlink(&pb, cfg.join("projects/-c")).unwrap();
        assert!(open_bound(&cfg, &ok).is_ok());
        assert_eq!(open_bound(&cfg, &out_link).unwrap_err(), "symlinked_path", "뿌리 밖 링크");
        assert_eq!(open_bound(&cfg, &in_link).unwrap_err(), "symlinked_path", "projects 안 다른 파일 링크(codex 2R)");
        assert_eq!(open_bound(&cfg, &cfg.join("projects/-c/otherid0.jsonl")).unwrap_err(), "symlinked_path", "중간 폴더 링크");
        assert_eq!(open_bound(&cfg, &pa.join("missing0.jsonl")).unwrap_err(), "no_file");
        assert_eq!(open_bound(&cfg, &pa).unwrap_err(), "not_a_file");
        assert_eq!(open_bound(&cfg, &secret).unwrap_err(), "outside_config_dir");
        std::fs::remove_dir_all(&base).ok();
    }

    #[test]
    fn long_text_is_not_truncated_and_reader_resumes_from_offset() {
        let dir = std::env::temp_dir().join(format!("viewcore-t-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join("s.jsonl");
        let long = "가".repeat(5000);
        let l1 = json!({"type":"user","uuid":"u1","message":{"content": long}}).to_string();
        std::fs::write(&p, format!("{l1}\n")).unwrap();
        let r = read_transcript_from(std::fs::File::open(&p).unwrap(), 0).unwrap();
        assert_eq!(r["records"][0]["text"].as_str().unwrap().chars().count(), 5000);
        let off = r["next_offset"].as_u64().unwrap();
        let l2 = json!({"type":"assistant","uuid":"a1","parentUuid":"u1","message":{"content":[{"type":"text","text":"답"}]}}).to_string();
        std::fs::write(&p, format!("{l1}\n{l2}\n")).unwrap();
        let r2 = read_transcript_from(std::fs::File::open(&p).unwrap(), off).unwrap();
        assert_eq!(r2["records"].as_array().unwrap().len(), 1);
        assert_eq!(r2["records"][0]["text"], "답");
        assert_eq!(r2["reset"], false);
        let r3 = read_transcript_from(std::fs::File::open(&p).unwrap(), 10_000_000).unwrap();
        assert_eq!(r3["reset"], true);
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn records_carry_file_line_start_position() {
        // (조각 4 · codex 1R minor) 레코드 `at` = 그 줄이 시작하는 파일 바이트 위치(오프셋부터 읽어도 파일 기준)
        let dir = std::env::temp_dir().join(format!("viewcore-at-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join("s.jsonl");
        let l1 = json!({"type":"assistant","message":{"content":"같은 글"}}).to_string();
        let junk = "{not json";
        let l3 = json!({"type":"assistant","message":{"content":"같은 글"}}).to_string();
        std::fs::write(&p, format!("{l1}\n{junk}\n{l3}\n")).unwrap();
        let r = read_transcript_from(std::fs::File::open(&p).unwrap(), 0).unwrap();
        let at: Vec<u64> = r["records"].as_array().unwrap().iter().map(|x| x["at"].as_u64().unwrap()).collect();
        let second = (l1.len() + 1 + junk.len() + 1) as u64;
        assert_eq!(at, vec![0, second], "uuid 없는 같은 글 두 줄도 위치로 갈린다(깨진 줄은 건너뛰되 위치 계산은 이어짐)");
        let r2 = read_transcript_from(std::fs::File::open(&p).unwrap(), second).unwrap();
        assert_eq!(r2["records"][0]["at"].as_u64(), Some(second), "중간 오프셋부터 읽어도 파일 기준 위치");
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn confirm_reply_params_and_outcome_keep_actuated() {
        // (조각 4 · codex 1R major 5 · blocking) 지문은 있을 때만 · 결과는 버리지 않음(actuated null = 기록만)
        let p = confirm_reply_params("daemon-1", "allow", None, Some("tok"));
        assert_eq!(p, json!({"request_id": "daemon-1", "decision": "allow", "operator_token": "tok"}));
        assert!(confirm_reply_params("daemon-1", "deny", Some(""), None).get("screen_fingerprint").is_none(), "빈 지문 = 안 실음");
        assert_eq!(confirm_reply_params("daemon-1", "allow", Some("fp1"), None)["screen_fingerprint"], "fp1");
        let ok = confirm_reply_outcome(&json!({"ok": true, "result": {"request_id": "daemon-1", "decision": "deny", "actuated": null}})).unwrap();
        assert!(ok.get("actuated").is_some() && ok["actuated"].is_null(), "기록만 해소(actuated null)를 그대로 올린다");
        let act = confirm_reply_outcome(&json!({"ok": true, "result": {"actuated": "return"}})).unwrap();
        assert_eq!(act["actuated"], "return");
        let e = confirm_reply_outcome(&json!({"ok": false, "error": {"code": "approval_screen_gone", "message": "m"}})).unwrap_err();
        assert_eq!(e, "approval_screen_gone: m");
    }

    #[test]
    fn from_end_start_is_last_complete_line_end() {
        // (조각 4 · codex 2R major) 미완 줄(줄 끝 없음)이 있으면 시작점 = 그 줄의 처음 — 뒤 읽기가 그 줄을 처음부터 읽고 앞 훑기는 그 줄을 「뒤」로 본다
        let dir = std::env::temp_dir().join(format!("viewcore-le-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join("s.jsonl");
        let l1 = json!({"type":"assistant","message":{"content":"a"}}).to_string();
        let open = |b: &str| {
            std::fs::write(&p, b).unwrap();
            std::fs::File::open(&p).unwrap()
        };
        let whole = format!("{l1}\n");
        assert_eq!(last_line_end(&open(&whole), whole.len() as u64).unwrap(), whole.len() as u64, "끝이 줄바꿈 = 크기 그대로");
        let partial = format!("{l1}\n ");
        assert_eq!(last_line_end(&open(&partial), partial.len() as u64).unwrap(), (l1.len() + 1) as u64, "미완 줄(공백 1바이트) = 그 줄 처음");
        assert_eq!(last_line_end(&open(" "), 1).unwrap(), 0, "줄바꿈 없음 = 0");
        assert_eq!(last_line_end(&open(""), 0).unwrap(), 0);
        let big = format!("{l1}\n{}", "x".repeat(200_000));
        assert_eq!(last_line_end(&open(&big), big.len() as u64).unwrap(), (l1.len() + 1) as u64, "64 KiB 넘게 거슬러 읽음");
        // codex 2R 재현: 미완 줄이 나중에 완성되면 그 줄의 위치 = 시작점(뒤) — 앞 훑기(at < 시작점)와 겹치지 않는다
        let done = format!("{l1}\n {}\n", json!({"type":"assistant","message":{"content":"⟪확인 해결: x⟫"}}));
        let start = (l1.len() + 1) as u64;
        let r = read_transcript_from(open(&done), 0).unwrap();
        let at: Vec<u64> = r["records"].as_array().unwrap().iter().map(|x| x["at"].as_u64().unwrap()).collect();
        assert_eq!(at, vec![0, start], "완성된 줄의 위치 = 시작점(앞 기록 아님)");
        std::fs::remove_dir_all(&dir).ok();
    }
}
