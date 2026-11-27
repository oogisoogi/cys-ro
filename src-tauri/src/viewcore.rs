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
/// - 그 자리 오류 = `try_write`(:386~402) 의 `write_stalled`·`write_failed` 둘뿐 — (조각 5 · S1-8) 둘 다 쓰기 줄에 넣지 못함(바이트 0)이라 목록에 넣었다(→ `failed`).
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
    // (1.1.16 · TICKET=cysr-1116-s5-1119 · 통합 📌 S1-8 · master 판단 = 옮김) `try_write`(handlers.rs) 의 두 오류 = 쓰기 줄(`write_tx.try_send`)에
    //   요청을 **넣지 못함** — 채널이 가득(Full) · 닫힘(Disconnected). 넣지 못한 요청은 writer 가 볼 수 없으므로 바이트 0 이 구조로 보장된다
    //   (넣은 뒤의 결과는 이 응답에 오지 않는다 · `sent:true` 가 「넣었다」). 그래서 「확인 중」이 아니라 「못 보냄 + 다시 보내기」.
    "write_stalled",
    "write_failed",
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

/// (조각 5 · §6-1) 기계 문안(깨움 말) 매개변수(순수) — 데몬 큐(`queued:true`) · `machine_origin:true` · `human:false`.
/// 원작자 `send_input` 의 UI 조립 문안 규칙과 같다: `owner_token`(ACL 등급) 만 붙이고 `operator_token`(원장 무기록 = 오너 임무 근거)은 **붙이지 않는다** —
/// 깨움 말은 사람 말이 아니므로 원장에 남아야 한다(임무 아님 · §2-8 ㉩). `clear_first` 없음(큐 배달자가 입력줄 빈칸·조용함을 기다린다).
pub(crate) fn auto_send_params(surface_id: u64, text: &str, tok: Option<&str>) -> Value {
    let mut p = json!({
        "surface_id": surface_id,
        "text": text,
        "quiet": true,
        "human": false,
        "queued": true,
        "clear_first": false,
        "machine_origin": true,
    });
    if let Some(t) = tok {
        p["owner_token"] = json!(t);
    }
    p
}

/// 큐 적재 응답(분류 보존) → 화면 결과(순수). `queued` = 데몬이 큐 항목 번호를 줌(그 뒤 단계는 큐 사건으로만) ·
/// `failed` = 전송 전 끊김 · 데몬 거부(큐에 안 들어감 — 오류 응답은 적재 전 거부다) · `uncertain` = 전송 뒤 끊김·꼴 이상·번호 없음.
pub(crate) fn classify_auto(r: Result<Value, (TransportClass, String)>) -> Value {
    match r {
        Err((TransportClass::Definite, e)) => json!({"outcome": "failed", "code": "transport_definite", "message": e}),
        Err((TransportClass::Uncertain, e)) => json!({"outcome": "uncertain", "code": "transport_uncertain", "message": e}),
        Ok(resp) => match resp["ok"].as_bool() {
            Some(true) => match resp["result"]["queue_entry_id"].as_str() {
                Some(qid) if resp["result"]["queued"].as_bool() == Some(true) && !qid.is_empty() => {
                    json!({"outcome": "queued", "queue_entry_id": qid, "result": resp["result"].clone()})
                }
                _ => json!({"outcome": "uncertain", "code": "no_queue_entry_id", "result": resp["result"].clone()}),
            },
            Some(false) => json!({
                "outcome": "failed",
                "code": resp["error"]["code"].as_str().unwrap_or(""),
                "message": resp["error"]["message"].as_str().unwrap_or("unknown error"),
            }),
            None => json!({"outcome": "uncertain", "code": "malformed_response"}),
        },
    }
}

/// `chat_send` — 대화 화면 말. `kind:"human"` = 사람 말 원자 제출 · `kind:"auto"` = 기계 문안(조각 5 깨움 말 · 데몬 큐 · 원장 기록).
#[tauri::command]
pub async fn chat_send(socket: Option<String>, surface_id: u64, text: String, kind: String) -> Result<Value, String> {
    let sock = resolve_socket(&socket);
    match kind.as_str() {
        "human" => {
            let tok = read_operator_token_for(&sock);
            let params = human_send_params(surface_id, &text, tok.as_deref());
            Ok(classify_send(rpc_full_classified(&sock, "surface.send_text", params).await))
        }
        "auto" => {
            let tok = read_operator_token_for(&sock);
            let params = auto_send_params(surface_id, &text, tok.as_deref());
            Ok(classify_auto(rpc_full_classified(&sock, "surface.send_text", params).await))
        }
        _ => Err(format!("unsupported_kind: {kind}")),
    }
}

/// (조각 5 · master#565d7c18 P1) 조건부 닫기 칸(순수) — 원작자 `close_surface_with` 가 만든 `{surface_id, owner_token}` 에 `if_quiet` · `expected_created_at` 만 더한다.
pub(crate) fn if_quiet_close_params(mut p: Value, expected_created_at: f64) -> Value {
    p["if_quiet"] = json!(true);
    p["expected_created_at"] = json!(expected_created_at);
    p
}

/// `close_surface_if_quiet` — 다시 켜기의 옛 마스터 창 닫기(never_started · 옛 빈 셸 정리) 전용. 데몬이 **닫기와 같은 잠금 안**에서
/// 입력줄 사람 바이트 0 ∧ 붙여넣기 닫힘 ∧ 30초 안 사람 입력 없음 ∧ 생성 시각 일치를 판정한다(불충족 = 닫지 않음 · `close_refused: …`).
/// 확인·첨부 정리는 원작자 `close_surface_with` 그대로(owner 표지 · Attachments) — 다른 것은 요청 칸 둘뿐.
#[tauri::command]
pub async fn close_surface_if_quiet(
    state: tauri::State<'_, crate::Attachments>,
    socket: Option<String>,
    surface_id: u64,
    expected_created_at: f64,
) -> Result<(), String> {
    let sock = resolve_socket(&socket);
    crate::close_surface_with(&state, &sock, surface_id, read_operator_token_for, move |socket, params| async move {
        rpc_full(&socket, "surface.close", if_quiet_close_params(params, expected_created_at)).await
    })
    .await
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

/// (TICKET=cysr-1118-ui ①) 진행 줄에 싣는 도구 단서 글자 상한(글자 수 · 바이트 아님).
pub(crate) const TOOL_HINT_MAX: usize = 60;

/// 글자 상한으로 자른다(순수 · 글자 경계 · 넘으면 끝에 `…`) · 줄바꿈은 첫 줄만.
fn clip_hint(s: &str) -> Option<String> {
    let first = s.lines().map(str::trim).find(|l| !l.is_empty())?;
    let mut out: String = first.chars().take(TOOL_HINT_MAX).collect();
    if first.chars().count() > TOOL_HINT_MAX {
        out.push('…');
    }
    Some(out)
}

/// (TICKET=cysr-1118-ui ①) 도구 호출 한 건 → 사람이 읽을 짧은 단서(순수) — 진행 줄 「과정 보기」 재료. **입력 전문은 넘기지 않는다**:
/// 파일 = 마지막 이름만 · 명령 = 설명(description)만(★codex 1R major — 명령 원문은 짧아도 비밀이 들 수 있어 **안 넘김** · 설명 없으면 단계 이름만) ·
/// 찾기 = 찾는 말 · 웹 = 검색어 / 주소의 호스트 이름만(사용자·비밀번호·포트·경로 0 · 못 풀면 없음) · 도우미 = 설명. 그 밖 = 없음(이름만).
pub(crate) fn tool_hint(name: &str, input: &Value) -> Option<String> {
    let s = |k: &str| input[k].as_str().filter(|v| !v.trim().is_empty());
    let base = |p: &str| p.rsplit(['/', '\\']).find(|x| !x.is_empty()).map(str::to_owned);
    match name {
        "Read" | "Edit" | "MultiEdit" | "Write" | "NotebookEdit" => s("file_path").or(s("notebook_path")).and_then(base).and_then(|b| clip_hint(&b)),
        "Bash" | "PowerShell" => s("description").and_then(clip_hint),
        "Grep" | "Glob" => s("pattern").and_then(clip_hint),
        "WebSearch" => s("query").and_then(clip_hint),
        "WebFetch" => s("url").and_then(url_host).and_then(|h| clip_hint(&h)),
        "Task" | "Agent" => s("description").and_then(clip_hint),
        _ => None,
    }
}

/// 주소 → 호스트 이름만(순수) — `scheme://[user[:pw]@]host[:port]/…` · 사용자·비밀번호·포트 버림 · 꼴이 아니거나 호스트 글자가 이상하면 None(원문 안 넘김).
fn url_host(u: &str) -> Option<String> {
    let rest = u.split_once("://")?.1;
    let auth = rest.split(['/', '?', '#']).next()?;
    let hostport = auth.rsplit('@').next()?;
    let host = if let Some(v6) = hostport.strip_prefix('[') { v6.split(']').next()? } else { hostport.split(':').next()? };
    (!host.is_empty() && host.chars().all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '-' | ':'))).then(|| host.to_ascii_lowercase())
}

/// assistant 레코드 content → (도구 단계들, 생각 조각 있음)(순수). 단계 = `{name, hint}` · 도구 이름도 60자 상한.
fn tool_steps(content: &Value) -> (Value, bool) {
    let Some(arr) = content.as_array() else { return (Value::Null, false) };
    let think = arr.iter().any(|b| matches!(b["type"].as_str(), Some("thinking") | Some("redacted_thinking")));
    let tools: Vec<Value> = arr
        .iter()
        .filter(|b| b["type"].as_str() == Some("tool_use"))
        .filter_map(|b| {
            let name: String = b["name"].as_str()?.chars().take(TOOL_HINT_MAX).collect();
            let hint = tool_hint(&name, &b["input"]);
            Some(json!({"name": name, "hint": hint}))
        })
        .collect();
    (if tools.is_empty() { Value::Null } else { Value::Array(tools) }, think)
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
        // (TICKET=cysr-1121-ui K-3 · U25 실측 2026-11-27 · 증거 workers/cysr-1121-ui/u25-evidence) 마스터가 바쁠 때 넘긴 말은 Claude Code 가
        //   받아 둔다 — ① 받는 순간 `queue-operation enqueue`(uuid 없음 · content = 원문) ② 도구 경계에서 흡수되면 `attachment.queued_command`
        //   (uuid·부모 있음 · prompt = 원문 · type:user 레코드는 생기지 않음) ③ 턴 끝까지 남으면 dequeue 뒤 보통 user 레코드.
        //   ①은 「마스터가 받아 둠」 증거(role "queued" · 사슬 밖) · ②는 사람 말 레코드(role "user")로 넘긴다 — 둘 다 사람이 쓴 글 그대로라
        //   user 레코드와 같은 취급(NFR-S3 = 훅 글 등 「그 밖 종류」의 본문 0자 원칙은 그대로 · 이 두 꼴만 예외).
        if v["type"].as_str() == Some("queue-operation") {
            if v["operation"].as_str() == Some("enqueue") {
                if let Some(t) = v["content"].as_str() {
                    out.push(json!({
                        "uuid": Value::Null,
                        "parent": Value::Null,
                        "role": "queued",
                        "text": t,
                        "parts": Value::Null,
                        "ts": v["timestamp"].as_str(),
                        "sidechain": false,
                        "at": at,
                    }));
                }
            }
            continue;
        }
        if v["type"].as_str() == Some("attachment") && v["attachment"]["type"].as_str() == Some("queued_command") {
            let mode_ok = matches!(v["attachment"]["commandMode"].as_str(), None | Some("prompt"));
            if let (true, Some(uuid), Some(t)) = (mode_ok, v["uuid"].as_str(), v["attachment"]["prompt"].as_str()) {
                out.push(json!({
                    "uuid": uuid,
                    "parent": v["parentUuid"].as_str(),
                    "role": "user",
                    "text": t,
                    "parts": Value::Null,
                    "ts": v["attachment"]["timestamp"].as_str().or(v["timestamp"].as_str()),
                    "sidechain": v["isSidechain"].as_bool().unwrap_or(false),
                    "at": at,
                    "tools": Value::Null,
                    "thinking": false,
                }));
                continue;
            }
        }
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
        // (TICKET=cysr-1118-ui ①) 마스터 쪽 레코드만 도구 단계·생각 표지(진행 줄 재료 · 메모리만 · 화면 저장소 0 = NFR-S3)
        let (tools, thinking) = if role == "assistant" { tool_steps(&v["message"]["content"]) } else { (Value::Null, false) };
        out.push(json!({
            "uuid": v["uuid"].as_str(),
            "parent": v["parentUuid"].as_str(),
            "role": role,
            "text": text,
            "parts": if parts.len() > 1 { json!(parts) } else { Value::Null },
            "ts": v["timestamp"].as_str(),
            "sidechain": v["isSidechain"].as_bool().unwrap_or(false),
            "at": at,
            "tools": tools,
            "thinking": thinking,
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

/// ★1.1.16(TICKET=cysr-1116-debt-d-1119 · S3-2): 세션 기록 후보 경로(순수) — 데몬이 준 cwd 그대로의 슬러그가 먼저, 그 cwd 를 실제 경로로 푼
/// 값(`canonical` · 심볼릭 링크 해소 · 맥 `/tmp` → `/private/tmp`)이 다르면 그 슬러그를 다음 후보로. Claude Code 는 프로세스 cwd(getcwd = 풀린 경로)로
/// 프로젝트 폴더를 만들어, 링크 cwd 좌석에서는 첫 후보가 늘 없었다(조각 3 §11 실측 「전달 확인 중 → 오래 걸려요」). 열기는 두 후보 모두
/// [`open_bound`](설정 폴더 뿌리 + 링크 안 따름)를 지나므로 슬러그 글자만 다르고 뿌리 밖으로는 못 간다.
pub(crate) fn transcript_candidates(cfg: Option<&str>, cwd: Option<&str>, sid: Option<&str>, canonical: Option<&str>) -> Result<Vec<std::path::PathBuf>, &'static str> {
    let first = transcript_path(cfg, cwd, sid)?;
    let mut out = vec![first];
    if let Some(c) = canonical.filter(|c| Some(*c) != cwd && std::path::Path::new(c).is_absolute()) {
        if let Ok(p) = transcript_path(cfg, Some(c), sid) {
            if p != out[0] {
                out.push(p);
            }
        }
    }
    Ok(out)
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

/// 윈도 — ★TICKET=cysr-1118-ui ①-4: **연 핸들 자체를 대조**하는 판(`cys::bound_open::open_file_under` · 경로 재탐색 0 — codex 4R major 「경로 재탐색
/// 대조는 바꿔치기를 못 막음」에 대한 답): 마지막 요소는 링크를 따르지 않고 열고(reparse point = 거부) · 연 객체의 최종 경로가
/// 「설정 폴더 최종 경로 + 상대 요소」와 같아야 한다(중간 접합·링크 = 거부). 사유 코드는 유닉스 판과 같은 낱말. 윈 실기 시험 = windows-health `bound_open::`.
#[cfg(windows)]
pub(crate) fn open_bound(cfg: &std::path::Path, expected: &std::path::Path) -> Result<std::fs::File, &'static str> {
    cys::bound_open::open_file_under(cfg, expected)
}

/// 유닉스·윈도 밖 — 읽지 않는다(화면 = 「모름」).
#[cfg(not(any(unix, windows)))]
pub(crate) fn open_bound(_cfg: &std::path::Path, _expected: &std::path::Path) -> Result<std::fs::File, &'static str> {
    Err("unsupported_platform")
}

/// 이 플랫폼에서 결속 세션 파일을 열 수 있는가(= `open_bound` 가 실제 구현을 가졌는가 · ★cysr-1118-ui ①-4 = 윈도 포함).
/// false 면 chat_transcript 가 RPC 0 으로 unsupported_platform 을 돌려주고 화면은 transcriptNone 으로 30초마다만 다시 묻는다(cysr-chat-held-win).
pub(crate) const fn transcript_supported() -> bool {
    cfg!(any(unix, windows))
}

/// 윈도 확장 길이 접두 걷기(순수) — `\\?\C:\x` → `C:\x` · `\\?\UNC\s\h` → `\\s\h` · 그 밖 그대로.
pub(crate) fn strip_verbatim(p: &str) -> String {
    if let Some(r) = p.strip_prefix(r"\\?\UNC\") {
        return format!(r"\\{r}");
    }
    p.strip_prefix(r"\\?\").unwrap_or(p).to_owned()
}

/// (1.1.19 · TICKET=cysr-1119-s3 · CH-C) 좌석에 결속된 세션 기록을 찾아 연다 — `chat_transcript` 본문에서 그대로 옮긴 몫(데몬 RPC 2 ·
/// `transcript_candidates` · `open_bound` · 다른 프로젝트 폴더 뒤지지 않음). `Ok(Err(v))` = 화면에 그대로 돌려줄 「모름」 응답(꼴 = 1.1.18 과 같음).
/// `chat_transcript_watch` 가 같은 함수로 연다(허용 경로 규칙 한 벌 · P3 v4 §3-7 C-1).
async fn bound_transcript(sock: &std::path::Path, surface_id: u64) -> Result<Result<(String, std::path::PathBuf, std::fs::File), Value>, String> {
    let list = rpc_on(sock, "surface.list", json!({})).await?;
    let org = rpc_on(sock, "org.status", json!({})).await?;
    let Some(lrow) = row_of(&list, surface_id) else {
        return Ok(Err(json!({"status": "unknown", "why": "no_seat"})));
    };
    let sid = row_of(&org, surface_id).and_then(|r| r["registered_session_id"].as_str()).map(str::to_owned);
    // ★1.1.16(S3-2): cwd 를 실제 경로로 푼 값도 후보로(transcript_candidates 머리 주석) — 같은 세션 id 의 다른 프로젝트 폴더는 여전히 뒤지지 않는다.
    let canonical = lrow["cwd"].as_str().and_then(|c| std::fs::canonicalize(c).ok()).and_then(|p| p.to_str().map(str::to_owned));
    // (TICKET=cysr-1118-ui ①-4) 윈도 canonicalize 는 `\\?\` 접두(확장 길이 경로)를 붙인다 — Claude Code 는 보통 경로로 슬러그를 만드므로 접두를 걷은 값으로 후보를 만든다.
    let canonical = canonical.map(|c| strip_verbatim(&c));
    let paths = match transcript_candidates(lrow["claude_config_dir"].as_str(), lrow["cwd"].as_str(), sid.as_deref(), canonical.as_deref()) {
        Ok(p) => p,
        Err(why) => return Ok(Err(json!({"status": "unknown", "why": why}))),
    };
    let sid = sid.unwrap_or_default();
    // 다른 프로젝트 폴더는 뒤지지 않는다(codex 1R major — 같은 이름 파일이 다른 cwd 의 기록일 수 있음). 링크를 풀어 설정 폴더 안인지 확인.
    let cfg = lrow["claude_config_dir"].as_str().unwrap_or_default();
    let mut opened = Err("not_found");
    for p in &paths {
        opened = open_bound(std::path::Path::new(cfg), p).map(|f| (p.clone(), f));
        if opened.is_ok() {
            break;
        }
    }
    Ok(match opened {
        Ok((path, file)) => Ok((sid, path, file)),
        Err(why) => Err(json!({"status": "unknown", "why": refine_open_why(why, &paths), "session_id": sid})),
    })
}

/// (1.1.19 · TICKET=cysr-1119-s3 · 검증 V1) 「파일 없음」 = 후보 경로가 **정말 하나도 없을 때만**(윈 `status_reason` 은 모르는 오류도 no_file 로 접는다) —
/// 있는데 못 연 것은 `open_failed`. 화면은 「결속 세션 있음 · 파일 아직 없음(첫 입력 때 생김)」 일 때만 새 파일을 0 에서 읽는다(있던 파일을 처음부터 다시 읽지 않게).
pub(crate) fn refine_open_why(why: &'static str, paths: &[std::path::PathBuf]) -> &'static str {
    if why == "no_file" && paths.iter().any(|p| std::fs::symlink_metadata(p).is_ok()) {
        return "open_failed";
    }
    why
}

/// `chat_transcript` — 좌석에 결속된 세션 기록을 `after_offset` 부터 읽는다(`from_end` = 읽지 않고 끝 오프셋만).
/// 꼴: `{status:"ok", session_id, next_offset, size, records[], bad_lines, reset}` · 못 읽으면 `{status:"unknown", why}`(화면 = 「전달 확인 중」).
#[tauri::command]
pub async fn chat_transcript(socket: Option<String>, surface_id: u64, after_offset: u64, from_end: Option<bool>) -> Result<Value, String> {
    // (TICKET=cysr-chat-held-win) 결속 파일을 열 수 없는 플랫폼(윈 · open_bound = unsupported_platform)은 결과가 이미 정해져 있다 —
    //   데몬 RPC 2개(surface.list · org.status)를 먼저 부르지 않는다. 앱의 데몬 RPC 는 소켓당 연결 1개를 직렬로 나눠 쓰므로(RPC_POOL)
    //   이 두 조회가 대화 화면 보내기 길의 재조회(feed.list · org.status) 앞에 줄을 서서 500ms 상한을 먹었다. 꼴은 예전 실패 응답과 같다.
    if !transcript_supported() {
        return Ok(json!({"status": "unknown", "why": "unsupported_platform"}));
    }
    let sock = resolve_socket(&socket);
    // (1.1.19 · TICKET=cysr-1119-s3) 경로 찾기·열기 = [`bound_transcript`] 한 곳(watch 와 같은 함수 · 이 명령의 동작·응답 꼴은 그대로).
    let (sid, file) = match bound_transcript(&sock, surface_id).await? {
        Ok((sid, _path, file)) => (sid, file),
        Err(v) => return Ok(v),
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

// ---------- (1.1.19 · TICKET=cysr-1119-s3 · CH-C) 기록 바뀌면 곧 보이기 — watch · tail · 되돌리기 환경 변수 ----------
//
// 설계 정본 = P3 v4 §3-7 C-1·C-2 · 카드 C · 통합 설계 DESIGN §3-2 F06 · §3-3 F10 · 카드 E ①(master#ca4edc8b).
// - watch = 결속 파일을 **한 번** 열어(`bound_transcript` · 데몬 RPC 2 는 걸 때 1회) 핸들을 쥐고, 0.25초마다 **경로 stat**(F10 — 쥔 핸들 fstat 이 아님:
//   같은 경로가 지워지고 다시 만들어지면 쥔 핸들은 옛 파일을 가리켜 바뀜을 못 본다) → 길이 늘어남 = 사건 · 줄어듦/식별 바뀜 = reset 사건.
// - tail = 쥔 핸들에서 **RPC 없이** 이어 읽기(`read_transcript_from` 재사용) · 응답에 `from_offset`·`to_offset`(화면 읽기 길 하나의 대조 재료 · F06).
// - 상태 = 이 모듈 정적 값(마스터 결속 파일 1개 · P3 §3-8) — `main.rs` 에는 명령 이름만(PLAN §2 S3 · HANDOFF 어긋남 ①).

/// watch 박자(ms · P3 v4 §3-7 C-1 「0.25초」).
pub(crate) const WATCH_TICK_MS: u64 = 250;
/// watch 사건 이름 — 화면(core.ts)이 `listenApp` 으로 대화 화면이 켜진 동안만 받는다.
pub(crate) const CHAT_TRANSCRIPT_CHANGED: &str = "chat-transcript-changed";
/// 되돌리기 환경 변수(P3 v4 §5-2 · DESIGN §3-1 · 저장 키 없음 = F38).
pub(crate) const CHAT_COMPAT_ENV: &str = "CYS_CHAT_COMPAT_1118";

/// 경로 stat 한 번(또는 쥔 핸들 stat)의 결과 — `ident` = 유닉스 (장치, inode) · 윈 (만든 시각 100ns, 0).
/// ⚠윈: 안정판 Rust 에 파일 번호가 없어 만든 시각을 쓴다 — 같은 이름을 지우고 15초 안에 다시 만들면 OS 가 만든 시각을 물려준다(파일 터널링)
///   → 그 재생성은 식별로 못 잡고 **줄어듦으로만** 잡는다(HANDOFF 「알고 남긴 것」 ② · 시험 `t_u5_same_len_recreate_within_15s_verdicts`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct PathStat {
    pub(crate) len: u64,
    pub(crate) ident: (u64, u64),
}

/// 정규 파일이 아닌 것(링크로 바뀜 등)의 식별 — 어떤 실제 파일과도 같지 않게 두어 reset 으로 간다(다시 열기 = `open_bound` 가 거부).
const NOT_A_FILE: (u64, u64) = (u64::MAX, u64::MAX);

#[cfg(unix)]
fn ident_of(m: &std::fs::Metadata) -> (u64, u64) {
    use std::os::unix::fs::MetadataExt;
    (m.dev(), m.ino())
}
#[cfg(windows)]
fn ident_of(m: &std::fs::Metadata) -> (u64, u64) {
    use std::os::windows::fs::MetadataExt;
    (m.creation_time(), 0)
}
#[cfg(not(any(unix, windows)))]
fn ident_of(_m: &std::fs::Metadata) -> (u64, u64) {
    NOT_A_FILE
}

/// 경로 stat(F10) — 링크를 따르지 않는다(`symlink_metadata`). 실패 = None(다음 박자) · 정규 파일 아님 = [`NOT_A_FILE`].
pub(crate) fn path_stat(p: &std::path::Path) -> Option<PathStat> {
    let m = std::fs::symlink_metadata(p).ok()?;
    if !m.is_file() {
        return Some(PathStat { len: 0, ident: NOT_A_FILE });
    }
    Some(PathStat { len: m.len(), ident: ident_of(&m) })
}

/// 쥔 핸들 stat — 걸 때 「경로 = 연 파일」 확인과 tail 의 식별 대조 기준값에만 쓴다(박자마다의 바뀜 판정에는 쓰지 않는다 · F10).
pub(crate) fn handle_stat(f: &std::fs::File) -> Option<PathStat> {
    let m = f.metadata().ok()?;
    Some(PathStat { len: m.len(), ident: ident_of(&m) })
}

/// watch 한 박자의 관측 — **경로** stat(F10). 시험 `f10_recreated_file_is_reset_by_path_stat` 가 이 함수를 부른다(뮤턴트 = 쥔 핸들 stat → 붉음).
pub(crate) fn watch_probe(path: &std::path::Path, _held: &std::fs::File) -> Option<PathStat> {
    path_stat(path)
}

/// watch 사건 — 늘어남(size) · reset(size = 지금 길이).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum WatchEvent {
    Grew(u64),
    Reset(u64),
}

/// watch 상태기계(순수 · T-U5) — stat 실패 = 그대로(다음 박자) · 식별 바뀜 ∨ 줄어듦 = reset · 늘어남 = 사건 · 같음 = 0.
pub(crate) fn watch_step(prev: PathStat, now: Option<PathStat>) -> (PathStat, Option<WatchEvent>) {
    let Some(n) = now else { return (prev, None) };
    if n.ident != prev.ident || n.len < prev.len {
        return (n, Some(WatchEvent::Reset(n.len)));
    }
    if n.len > prev.len {
        return (n, Some(WatchEvent::Grew(n.len)));
    }
    (n, None)
}

/// 쥔 결속 파일(시험 가능한 몫 — 작업 손잡이는 [`Watched`]).
pub(crate) struct WatchedFile {
    pub(crate) surface_id: u64,
    pub(crate) session_id: String,
    pub(crate) path: std::path::PathBuf,
    pub(crate) file: std::fs::File,
    /// 걸 때 쥔 핸들의 식별 — tail 이 경로 식별과 대조(다르면 옛 파일 = reset).
    pub(crate) ident: (u64, u64),
    pub(crate) gen: u64,
}

struct Watched {
    f: WatchedFile,
    task: tauri::async_runtime::JoinHandle<()>,
}

static CHAT_WATCH: std::sync::Mutex<Option<Watched>> = std::sync::Mutex::new(None);
/// 마지막으로 시작된 watch/unwatch 의 세대 — 늦게 끝난 옛 watch(데몬 RPC 를 기다린 사이 unwatch·새 watch 가 옴)는 걸지 않는다.
static WATCH_LATEST: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);

fn watch_lock() -> std::sync::MutexGuard<'static, Option<Watched>> {
    CHAT_WATCH.lock().unwrap_or_else(|e| e.into_inner())
}

/// tail 본체(파일 IO · RPC 0) — 경로 식별이 쥔 핸들과 다르면 옛 파일을 읽지 않고 `reset:true` · 아니면 쥔 핸들에서 `after_offset` 부터.
/// 응답 = `read_transcript_from` 꼴 + `session_id` · `from_offset`(실제 읽기 시작 · 파일이 줄었으면 0) · `to_offset`(= next_offset).
pub(crate) fn tail_on(w: &WatchedFile, after_offset: u64) -> Result<Value, String> {
    if matches!(path_stat(&w.path), Some(s) if s.ident != w.ident) {
        return Ok(json!({
            "status": "ok", "session_id": w.session_id, "next_offset": 0, "size": 0, "records": [], "bad_lines": 0,
            "reset": true, "skipped_bytes": 0, "long_line_open": false, "from_offset": 0, "to_offset": 0,
        }));
    }
    let f = w.file.try_clone().map_err(|e| e.to_string())?;
    let mut v = read_transcript_from(f, after_offset)?;
    let from = if v["reset"] == json!(true) { 0 } else { after_offset };
    let size = v["size"].as_u64().unwrap_or(0);
    v["from_offset"] = json!(from);
    v["to_offset"] = v["next_offset"].clone();
    // 읽기 상한(TRANSCRIPT_READ_MAX)에 걸려 남은 몫이 있는가 — 화면은 이때만 이어 읽는다(끝의 미완 줄은 「더」가 아님)
    v["more"] = json!(size.saturating_sub(from) > TRANSCRIPT_READ_MAX);
    v["session_id"] = json!(w.session_id);
    Ok(v)
}

/// (검증 V4) unwatch 가 지금 쥔 watch 를 내려도 되는가(순수) — 세대를 준 unwatch 는 그 세대만(늦게 처리돼도 더 새 watch 를 안 내림) · 세대 없음 = 무엇이든.
pub(crate) fn unwatch_hits(current_gen: Option<u64>, req_gen: Option<u64>) -> bool {
    match (current_gen, req_gen) {
        (None, _) => false,
        (Some(_), None) => true,
        (Some(c), Some(r)) => c == r,
    }
}

/// 쥔 watch 를 끝낸다(작업 abort · 핸들 닫음) — 내렸으면 true. `gen` = [`unwatch_hits`].
fn stop_watch(gen: Option<u64>) -> bool {
    let mut g = watch_lock();
    if !unwatch_hits(g.as_ref().map(|w| w.f.gen), gen) {
        return false;
    }
    match g.take() {
        Some(w) => {
            w.task.abort();
            true
        }
        None => false,
    }
}

/// `chat_transcript_watch` — 화면이 3초 조회로 받은 결속(`registered_session_id`)으로 마스터 결속 파일을 한 번 열어 쥐고 0.25초 경로 stat 를 시작한다.
/// 꼴: `{status:"ok", session_id, size, gen}` · 못 걸면 `{status:"unknown", why}`(화면 = 1.1.18 읽기 길 그대로).
#[tauri::command]
pub async fn chat_transcript_watch(app: tauri::AppHandle, socket: Option<String>, surface_id: u64, session_id: String) -> Result<Value, String> {
    use std::sync::atomic::Ordering;
    let gen = WATCH_LATEST.fetch_add(1, Ordering::SeqCst) + 1;
    if !transcript_supported() {
        return Ok(json!({"status": "unknown", "why": "unsupported_platform"}));
    }
    if !session_id_ok(&session_id) {
        return Ok(json!({"status": "unknown", "why": "bad_session_id"}));
    }
    let sock = resolve_socket(&socket);
    let (sid, path, file) = match bound_transcript(&sock, surface_id).await? {
        Ok(x) => x,
        Err(v) => return Ok(v),
    };
    if sid != session_id {
        return Ok(json!({"status": "unknown", "why": "session_mismatch", "session_id": sid}));
    }
    let Some(start) = handle_stat(&file) else {
        return Ok(json!({"status": "unknown", "why": "stat_failed"}));
    };
    if path_stat(&path).map(|s| s.ident) != Some(start.ident) {
        return Ok(json!({"status": "unknown", "why": "path_changed"})); // 연 사이 경로가 다른 파일이 됨
    }
    let mut g = watch_lock();
    if WATCH_LATEST.load(Ordering::SeqCst) != gen {
        return Ok(json!({"status": "unknown", "why": "superseded"}));
    }
    if let Some(old) = g.take() {
        old.task.abort();
    }
    let probe_path = path.clone();
    let probe_file = file.try_clone().map_err(|e| e.to_string())?;
    let sid_ev = sid.clone();
    // 한 박자를 끝낸 **뒤** 다음 박자를 잰다(sleep · interval 아님 = 밀린 박자가 몰려 돌지 않음 · 겹침 0).
    let task = tauri::async_runtime::spawn(async move {
        let mut prev = start;
        loop {
            tokio::time::sleep(std::time::Duration::from_millis(WATCH_TICK_MS)).await;
            let (next, ev) = watch_step(prev, watch_probe(&probe_path, &probe_file));
            prev = next;
            let payload = match ev {
                Some(WatchEvent::Grew(size)) => json!({"surface_id": surface_id, "session_id": sid_ev, "gen": gen, "size": size, "reset": false}),
                Some(WatchEvent::Reset(size)) => json!({"surface_id": surface_id, "session_id": sid_ev, "gen": gen, "size": size, "reset": true}),
                None => continue,
            };
            let _ = tauri::Emitter::emit(&app, CHAT_TRANSCRIPT_CHANGED, payload);
        }
    });
    *g = Some(Watched { f: WatchedFile { surface_id, session_id: sid.clone(), path, file, ident: start.ident, gen }, task });
    Ok(json!({"status": "ok", "session_id": sid, "size": start.len, "gen": gen}))
}

/// `chat_transcript_unwatch` — 대화 화면이 내려감 · 결속 바뀜 · 되돌리기. `gen` 을 주면 그 watch 만(검증 V4 · 늦게 처리돼도 더 새 watch 를 안 내림) ·
/// 주지 않으면(거는 중에 끊음) 늦게 끝날 watch 도 걸리지 않게 세대를 올리고 무엇이든 내린다.
#[tauri::command]
pub async fn chat_transcript_unwatch(gen: Option<u64>) -> Result<Value, String> {
    if gen.is_none() {
        WATCH_LATEST.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    }
    Ok(json!({"status": "ok", "was": stop_watch(gen)}))
}

/// `chat_transcript_tail` — 쥔 결속 파일을 `after_offset` 부터(데몬 RPC 0). 쥔 것이 없거나 다른 좌석이면 `{status:"unknown", why:"not_watching"}`.
#[tauri::command]
pub async fn chat_transcript_tail(surface_id: u64, after_offset: u64) -> Result<Value, String> {
    let g = watch_lock();
    match g.as_ref() {
        Some(w) if w.f.surface_id == surface_id => tail_on(&w.f, after_offset).map(|mut v| {
            v["gen"] = json!(w.f.gen);
            v
        }),
        _ => Ok(json!({"status": "unknown", "why": "not_watching"})),
    }
}

/// 되돌리기 값 판정(순수) — 정확히 `"1"` 만 켬.
pub(crate) fn compat_env_on(v: Option<&str>) -> bool {
    v == Some("1")
}

/// `chat_compat_env` — 앱 시작 뒤 처음 읽은 `CYS_CHAT_COMPAT_1118` 값(켬 = C·D 를 1.1.18 꼴로 · P3 v4 §5-2 · 카드 E ①).
#[tauri::command]
pub fn chat_compat_env() -> bool {
    static V: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *V.get_or_init(|| compat_env_on(std::env::var(CHAT_COMPAT_ENV).ok().as_deref()))
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
    #[cfg(windows)]
    if drive_root(&t.to_string_lossy()).is_some_and(|r| windrive::is_remote_drive(&r)) {
        return Err("network_path".into()); // (codex 3R ④) 매핑 드라이브(SMB·WebDAV)는 정규 경로가 `\\?\H:\…` 꼴이라 UNC 검사를 지나간다 — 드라이브 뿌리 종류(GetDriveTypeW) = DRIVE_REMOTE 면 거절
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
        // (codex 3R ① · 이중) 앱 꾸러미의 정체는 이름이 아니라 `Contents/Info.plist`(+ 옛 `PkgInfo` · 실행 파일 자리 `MacOS`)다 — 이름을 바꾼 꾸러미(`Report.pdf` 등)는 확장자 검사를 지나간다.
        //   그런 표지가 있는 폴더는 열지 않는다(폴더 보기만). 열기 자체도 파일 관리자로만 한다(folder_open_command).
        if ["Info.plist", "PkgInfo", "MacOS"].iter().any(|n| std::fs::symlink_metadata(t.join("Contents").join(n)).is_ok()) {
            return Err("executable_confirm".into());
        }
        return Ok(());
    }
    if !meta.is_file() {
        return Err("executable_confirm".into());
    }
    let ext = t.extension().map(|e| e.to_string_lossy().to_ascii_lowercase()).unwrap_or_default();
    if !OPEN_ALLOWED_EXT.contains(&ext.as_str()) || is_alias(t) {
        return Err("executable_confirm".into());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if meta.permissions().mode() & 0o111 != 0 {
            return Err("executable_confirm".into()); // (codex 4R ①) 기존 open_path 의 실행 비트 게이트 — 이제 open_path 를 거치지 않으므로 여기로 옮김
        }
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

/// (codex 3R ④) 윈도 정규 경로의 드라이브 뿌리 `X:\` — `\\?\X:\…` 또는 `X:\…` 꼴만(그 밖 = None · 맥·리눅스 경로도 None). 순수 함수(모든 기판에서 시험).
#[cfg_attr(not(windows), allow(dead_code))] // 운영 호출 = 윈도만(result_target) · 다른 기판은 시험만
pub(crate) fn drive_root(s: &str) -> Option<String> {
    let r = s.strip_prefix(r"\\?\").unwrap_or(s);
    let b = r.as_bytes();
    (b.len() >= 3 && b[0].is_ascii_alphabetic() && b[1] == b':' && (b[2] == b'\\' || b[2] == b'/')).then(|| format!("{}:\\", b[0] as char))
}

// ---- windrive 시작(std 만 · 교차 타입체크 = 이 표지 사이를 떼어 x86_64-pc-windows-msvc 로 rustc --emit=metadata) ----
#[cfg(windows)]
mod windrive {
    /// `GetDriveTypeW` 의 DRIVE_REMOTE(네트워크 드라이브).
    pub(super) const DRIVE_REMOTE: u32 = 4;

    #[link(name = "kernel32")]
    extern "system" {
        /// `UINT GetDriveTypeW(LPCWSTR lpRootPathName)` — 뿌리(끝 `\`)를 받는다.
        fn GetDriveTypeW(root: *const u16) -> u32;
    }

    #[link(name = "kernel32")]
    extern "system" {
        /// `UINT GetWindowsDirectoryW(LPWSTR lpBuffer, UINT uSize)` — 성공 = 글자 수(NUL 뺌) · 버퍼가 작으면 필요한 크기 · 실패 = 0.
        fn GetWindowsDirectoryW(buf: *mut u16, size: u32) -> u32;
    }

    /// (codex 4R ①) 윈도 폴더(보통 `C:\Windows`) — 못 얻으면 None.
    pub(super) fn windows_dir() -> Option<String> {
        let mut buf = [0u16; 512];
        // SAFETY: buf 는 512 글자 쓰기 가능 · 크기를 그대로 넘긴다.
        let n = unsafe { GetWindowsDirectoryW(buf.as_mut_ptr(), buf.len() as u32) } as usize;
        (n > 0 && n < buf.len()).then(|| String::from_utf16_lossy(&buf[..n]))
    }

    /// 드라이브 뿌리(`H:\`)가 네트워크 드라이브인가.
    pub(super) fn is_remote_drive(root: &str) -> bool {
        use std::os::windows::ffi::OsStrExt;
        let w: Vec<u16> = std::ffi::OsStr::new(root).encode_wide().chain(std::iter::once(0)).collect();
        // SAFETY: w = NUL 로 끝나는 UTF-16 문자열 · 함수는 읽기만 한다.
        unsafe { GetDriveTypeW(w.as_ptr()) == DRIVE_REMOTE }
    }
}
// ---- windrive 끝 ----

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

/// (codex 3R ①) 결과 행동 계획 — OS 에 넘기기 전 판정까지(실행 0 · 시험 대상).
#[derive(Debug, PartialEq, Eq)]
pub(crate) enum OpenPlan {
    /// 파일 관리자에서 그 항목을 골라 보여 줌(맥 `open -R` · 윈 `explorer.exe /select,`)
    Reveal(String),
    /// 폴더 = 파일 관리자로만 — 맥 `open -a Finder <폴더>` · 윈 = 들어가지 않고 상위 폴더에서 골라 보여 줌(codex 4R ②) · LaunchServices 기본 열기 0
    Folder(String),
    /// 허용 목록 종류의 보통 파일(실행 비트 없음) = 기본 처리기로 엶
    File(String),
}

/// 정규 홈 아래 · 숨은 마디 0 · (윈) 셸 정션 폴더 거절 · 열기면 `open_verdict`(허용 목록·가명·꾸러미·실행 비트 · 꾸러미 표지 폴더) — 그 밖 = 거절 글(`executable_confirm` 등 · 화면은 force 로 다시 부르지 않음).
pub(crate) fn open_plan(path: &std::path::Path, reveal: bool, home: &std::path::Path) -> Result<OpenPlan, String> {
    let target = result_target(path, home)?;
    #[cfg(windows)]
    {
        let home_c = std::fs::canonicalize(home).map_err(|e| format!("not a local path: {e}"))?;
        if shell_junction_on_path(&target, &home_c) {
            return Err("executable_confirm".into()); // (codex 4R ②) `이름.{CLSID}` 폴더 · desktop.ini CLSID= 폴더 = 탐색기가 COM 이름공간·네트워크로 엮음 — 열기·폴더 보기 둘 다 0
        }
    }
    if reveal {
        return Ok(OpenPlan::Reveal(plain_path(&target)));
    }
    open_verdict(&target)?; // (s79 · V1·V2) 허용 목록 · 가명 · 꾸러미 — 그 밖 = executable_confirm(화면 = 폴더 보기 안내)
    let is_dir = std::fs::metadata(&target).map_err(|e| format!("not a local path: {e}"))?.is_dir();
    Ok(if is_dir { OpenPlan::Folder(plain_path(&target)) } else { OpenPlan::File(plain_path(&target)) })
}

/// (codex 4R ②) 이름이 셸 정션 꼴(`이름.{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}` · 대소문자 무시)인가 — 순수 함수(모든 기판에서 시험).
pub(crate) fn is_clsid_name(name: &str) -> bool {
    let Some(i) = name.rfind(".{") else { return false };
    let g = &name[i + 1..];
    let b = g.as_bytes();
    b.len() == 38
        && b[0] == b'{'
        && b[37] == b'}'
        && b[1..37].iter().enumerate().all(|(k, c)| if [8, 13, 18, 23].contains(&k) { *c == b'-' } else { c.is_ascii_hexdigit() })
}

/// (codex 4R ②) 폴더 안 `desktop.ini` 에 `CLSID=`·`CLSID2=` 줄이 있는가(읽기만 · 앞 64KB · UTF-8 또는 UTF-16LE BOM) — 탐색기가 그 폴더를 COM 이름공간으로 엮는 꼴.
pub(crate) fn desktop_ini_has_clsid(dir: &std::path::Path) -> bool {
    use std::io::Read;
    let Ok(f) = std::fs::File::open(dir.join("desktop.ini")) else { return false };
    let mut buf = Vec::new();
    if f.take(65_536).read_to_end(&mut buf).is_err() {
        return true; // 있는데 못 읽음 = 모름 → 거절 쪽
    }
    let text = if buf.starts_with(&[0xFF, 0xFE]) {
        let u: Vec<u16> = buf[2..].chunks_exact(2).map(|c| u16::from_le_bytes([c[0], c[1]])).collect();
        String::from_utf16_lossy(&u)
    } else {
        String::from_utf8_lossy(&buf).into_owned()
    };
    text.lines().any(|l| l.split_once('=').is_some_and(|(k, _)| matches!(k.trim().to_ascii_lowercase().as_str(), "clsid" | "clsid2")))
}

/// (codex 4R ②) 정규 대상과 그 조상(정규 홈 **아래**만) 중 셸 정션 폴더(CLSID 이름 · desktop.ini CLSID)가 있는가 — 운영 호출 = 윈도만(맥 동작 불변) · 판정은 모든 기판에서 시험.
#[cfg_attr(not(windows), allow(dead_code))]
pub(crate) fn shell_junction_on_path(target: &std::path::Path, home_c: &std::path::Path) -> bool {
    target.ancestors().take_while(|a| *a != home_c && a.starts_with(home_c)).any(|a| {
        a.file_name().is_some_and(|n| is_clsid_name(&n.to_string_lossy())) || (a.is_dir() && desktop_ini_has_clsid(a))
    })
}

/// (codex 4R ①) 윈도 탐색기 절대 경로 고르기(순수) — GetWindowsDirectoryW 값 → `SystemRoot` 환경값 → `C:\Windows` 순 · 드라이브 절대 꼴(`X:\…`)만 받음(상대·빈 값은 건너뜀).
#[cfg_attr(not(windows), allow(dead_code))]
pub(crate) fn explorer_path_from(win_dir: Option<&str>, system_root: Option<&str>) -> String {
    let dir = [win_dir, system_root].into_iter().flatten().map(str::trim).find(|d| drive_root(d).is_some()).unwrap_or(r"C:\Windows");
    format!(r"{}\explorer.exe", dir.trim_end_matches(['\\', '/']))
}

/// (codex 4R ①) 신뢰 실행기 = **절대 경로**(맨 이름 0) — 맥 `/usr/bin/open` · 윈 `%SystemRoot%\explorer.exe` · 그 밖 `/usr/bin/xdg-open`.
/// 맨 이름(`open`·`explorer`)은 맥 = 물려받은 PATH 를 뒤지고 · 윈 = 실행 파일 폴더를 시스템 폴더보다 먼저 뒤진다 — 같은 이름 가짜가 끼면 PDF 누름이 그것을 띄운다.
pub(crate) fn launcher() -> String {
    #[cfg(target_os = "macos")]
    {
        "/usr/bin/open".into()
    }
    #[cfg(windows)]
    {
        explorer_path_from(windrive::windows_dir().as_deref(), std::env::var("SystemRoot").ok().as_deref())
    }
    #[cfg(not(any(target_os = "macos", windows)))]
    {
        "/usr/bin/xdg-open".into()
    }
}

/// (codex 3R ① · 4R ①②) 계획 → 실행 명령(절대 경로 실행기 · 인자는 셸 파싱 없음).
/// 맥: 파일 `open <파일>` · 폴더 `open -a Finder <폴더>` · 보기 `open -R <항목>` / 윈: 파일 `explorer.exe <파일>` · 폴더·보기 = `explorer.exe /select,<항목>`(폴더에 들어가지 않음) / 그 밖: xdg-open(보기 = 부모 폴더).
pub(crate) fn launch_command(plan: &OpenPlan) -> std::process::Command {
    let mut c = std::process::Command::new(launcher());
    match plan {
        #[cfg(target_os = "macos")]
        OpenPlan::Reveal(p) => {
            c.arg("-R").arg(p);
        }
        #[cfg(target_os = "macos")]
        OpenPlan::Folder(p) => {
            c.args(["-a", "Finder"]).arg(p);
        }
        #[cfg(windows)]
        OpenPlan::Reveal(p) | OpenPlan::Folder(p) => {
            c.arg(format!("/select,{p}"));
        }
        #[cfg(not(any(target_os = "macos", windows)))]
        OpenPlan::Reveal(p) => {
            c.arg(std::path::Path::new(p).parent().map(|x| x.to_string_lossy().into_owned()).unwrap_or_else(|| p.clone()));
        }
        #[cfg(not(any(target_os = "macos", windows)))]
        OpenPlan::Folder(p) => {
            c.arg(p);
        }
        OpenPlan::File(p) => {
            c.arg(p);
        }
    }
    c
}

/// 결과 행동 집행(`open_plan` 다음) — 시험이 임시 홈으로 부를 수 있게 홈을 받는다.
pub(crate) fn result_open_in(path: &std::path::Path, reveal: bool, home: &std::path::Path) -> Result<(), String> {
    let plan = open_plan(path, reveal, home)?;
    // (통합 cysr-1116-integ-1120) GUI(cys-app) 자식 창 정책 = main.rs no_console 과 같은 등급(Attached = 윈 CREATE_NO_WINDOW · 맥·유닉스 무동작) —
    //   lib.rs consoleless_spawns_carry_window_policy 가 요구(체인에 등급 · 다른 파일의 래퍼는 census 가 인정하지 않는다).
    use cys::SpawnPolicy as _;
    launch_command(&plan).spawn_policy(cys::ChildLifetime::Attached).spawn().map(|_| ()).map_err(|e| e.to_string())
}

/// 결과 받기 카드의 「열기」·「폴더 보기」 — 마스터 글에서 온 경로라 정규 대상으로 다시 가둔다:
/// 정규 홈 아래 · 숨은 마디 0 · (윈) 셸 정션 0 · 열기면 허용 목록·꾸러미·실행 비트 거절(`executable_confirm` · 화면은 force 로 다시 부르지 않음) · 실행기 = 절대 경로(`launch_command`).
/// ⚠알려진 한계(TOCTOU · master#c48208b6 처분 = 고치지 않고 문서): 정규화 뒤 경로 **이름**을 넘기므로, 그 사이 같은 사용자 권한의 로컬 프로세스가
///   조상 폴더를 링크로 바꿔치기하면 다른 대상이 열릴 수 있다 — 그 프로세스는 이미 무엇이든 열 수 있어 새 권한을 주지 않는다(HANDOFF 「알려진 한계」).
#[tauri::command]
pub fn result_open(path: String, reveal: Option<bool>) -> Result<(), String> {
    result_open_in(std::path::Path::new(&path), reveal.unwrap_or(false), &cys::home_dir())
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
        #[cfg(unix)]
        {
            // (codex 4R ①) 옛 open_path 의 실행 비트 게이트를 옮겨 옴 — 허용 목록 이름이어도 실행 비트면 거절
            use std::os::unix::fs::PermissionsExt;
            let x = d.join("실행.html");
            std::fs::write(&x, b"#!/bin/sh\n").unwrap();
            std::fs::set_permissions(&x, std::fs::Permissions::from_mode(0o744)).unwrap();
            assert_eq!(open_verdict(&x).unwrap_err(), "executable_confirm");
        }
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

    /// (codex 3R ①) 이름을 바꾼 앱 꾸러미(`Report.pdf` · Info.plist APPL · 실행 파일이 표식 파일을 만듦) — 열기 계획 = 거절 · 집행해도 실행 0 ·
    /// 꾸러미 표지 없는 폴더 = 파일 관리자로만(`open -a Finder` · LaunchServices 기본 열기 0).
    #[test]
    fn renamed_app_bundle_folder_is_refused_and_folders_open_in_file_manager_only() {
        let base = std::env::temp_dir().join(format!("vc-bnd-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        let home = base.join("home");
        let marker = base.join("MARKER");
        let b = home.join("교회").join("Report.pdf");
        std::fs::create_dir_all(b.join("Contents").join("MacOS")).unwrap();
        std::fs::write(
            b.join("Contents").join("Info.plist"),
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?><plist version=\"1.0\"><dict><key>CFBundlePackageType</key><string>APPL</string><key>CFBundleExecutable</key><string>run</string><key>CFBundleIdentifier</key><string>invalid.cys.vc-bnd</string><key>LSUIElement</key><true/></dict></plist>",
        )
        .unwrap();
        let run = b.join("Contents").join("MacOS").join("run");
        std::fs::write(&run, format!("#!/bin/sh\ntouch '{}'\n", marker.display())).unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&run, std::fs::Permissions::from_mode(0o755)).unwrap();
        }
        // 계획부터 단언(뮤턴트가 거절을 빼도 아래 집행이 OS 를 부르기 전에 여기서 멈춘다)
        assert_eq!(open_plan(&b, false, &home).unwrap_err(), "executable_confirm");
        assert_eq!(result_open_in(&b, false, &home).unwrap_err(), "executable_confirm");
        std::thread::sleep(std::time::Duration::from_millis(1500));
        assert!(!marker.exists(), "이름 바꾼 꾸러미가 실행됨(표식 파일 생김)");
        // 표지 하나씩: PkgInfo 만 · MacOS 만도 거절
        for n in ["PkgInfo", "MacOS"] {
            let d = home.join("교회").join(format!("표지-{n}"));
            std::fs::create_dir_all(d.join("Contents")).unwrap();
            if n == "MacOS" {
                std::fs::create_dir_all(d.join("Contents").join(n)).unwrap();
            } else {
                std::fs::write(d.join("Contents").join(n), b"APPL????").unwrap();
            }
            assert_eq!(open_plan(&d, false, &home).unwrap_err(), "executable_confirm", "{n}");
        }
        // 폴더 보기는 됨(파일 관리자에서 고르기만 · 실행 0)
        assert!(matches!(open_plan(&b, true, &home), Ok(OpenPlan::Reveal(_))));
        // 꾸러미 표지 없는 보통 폴더 = Folder(파일 관리자) · 보통 문서 = File(open_path)
        let plain = home.join("교회").join("주보");
        std::fs::create_dir_all(&plain).unwrap();
        std::fs::write(plain.join("a.pdf"), b"%PDF-1.4").unwrap();
        let Ok(OpenPlan::Folder(fp)) = open_plan(&plain, false, &home) else { panic!("보통 폴더 = Folder 계획") };
        assert!(matches!(open_plan(&plain.join("a.pdf"), false, &home), Ok(OpenPlan::File(_))));
        let c = launch_command(&OpenPlan::Folder(fp.clone()));
        let args: Vec<String> = c.get_args().map(|a| a.to_string_lossy().into_owned()).collect();
        #[cfg(target_os = "macos")]
        {
            assert_eq!(c.get_program(), "/usr/bin/open");
            assert_eq!(args, vec!["-a".to_string(), "Finder".into(), fp.clone()], "맥 폴더 열기 = Finder 로만(LaunchServices 기본 열기 금지)");
        }
        #[cfg(windows)]
        {
            assert!(c.get_program().to_string_lossy().ends_with(r"\explorer.exe"));
            assert_eq!(args, vec![format!("/select,{fp}")], "윈 폴더 = 들어가지 않고 상위 폴더에서 골라 보여 줌");
        }
        // 집행 길 = 계획 → launch_command 한 길(소스 대조 — 실제 Finder 창은 띄우지 않음)
        let src = include_str!("viewcore.rs");
        let code: String = src.lines().filter(|l| !l.trim_start().starts_with("//")).collect::<Vec<_>>().join("\n");
        let body = &code[code.find("pub(crate) fn result_open_in(").expect("result_open_in")..];
        let body = &body[..body.find("\n}\n").expect("끝")];
        assert!(body.contains("let plan = open_plan(path, reveal, home)?;") && body.contains("launch_command(&plan).spawn_policy(cys::ChildLifetime::Attached).spawn()"), "집행이 계획·절대 경로 명령을 안 지남");
        assert!(!body.contains("crate::open_path") && !body.contains("crate::reveal_path"), "맨 이름 실행기를 쓰는 옛 open_path/reveal_path 를 다시 부름");
        let _ = std::fs::remove_dir_all(&base);
    }

    /// (codex 4R ①) 실행기 = 절대 경로 — 세 계획 모두 같은 실행기 · 맨 이름 spawn 0(이 파일 운영 코드 전체 grep) · 윈 탐색기 경로 고르기(순수) · 맥 인자 불변.
    #[test]
    fn launchers_are_absolute_paths_and_no_bare_name_spawn() {
        for plan in [OpenPlan::File("/h/a.pdf".into()), OpenPlan::Reveal("/h/a.pdf".into()), OpenPlan::Folder("/h/d".into())] {
            let c = launch_command(&plan);
            let prog = c.get_program().to_string_lossy().into_owned();
            assert_eq!(prog, launcher(), "{plan:?}");
            assert!(prog.starts_with('/') || drive_root(&prog).is_some(), "실행기가 절대 경로가 아님: {prog}");
        }
        #[cfg(target_os = "macos")]
        {
            assert_eq!(launcher(), "/usr/bin/open");
            let a = |p: OpenPlan| launch_command(&p).get_args().map(|x| x.to_string_lossy().into_owned()).collect::<Vec<_>>();
            assert_eq!(a(OpenPlan::File("/h/a.pdf".into())), vec!["/h/a.pdf"]); // 맥 동작 불변(옛 open_path = open <파일>)
            assert_eq!(a(OpenPlan::Reveal("/h/a.pdf".into())), vec!["-R", "/h/a.pdf"]); // 옛 reveal_path = open -R <항목>
        }
        assert_eq!(explorer_path_from(Some(r"C:\WINDOWS"), Some(r"D:\Win")), r"C:\WINDOWS\explorer.exe");
        assert_eq!(explorer_path_from(None, Some(r"D:\Win\")), r"D:\Win\explorer.exe");
        assert_eq!(explorer_path_from(Some(""), Some("evil")), r"C:\Windows\explorer.exe"); // 빈 값·상대 값 = 건너뜀
        assert_eq!(explorer_path_from(None, None), r"C:\Windows\explorer.exe");
        // 운영 코드 전체에서 Command::new 의 인자 = launcher() 하나뿐(맨 이름 문자열 0)
        let src = include_str!("viewcore.rs");
        let prod = &src[..src.find("#[cfg(test)]\nmod tests {").expect("시험 경계")];
        let code: String = prod.lines().filter(|l| !l.trim_start().starts_with("//")).collect::<Vec<_>>().join("\n");
        let news: Vec<&str> = code.match_indices("Command::new(").map(|(i, _)| &code[i..i + code[i..].find(')').unwrap() + 1]).collect();
        assert_eq!(news, vec!["Command::new(launcher()"], "맨 이름 또는 다른 실행기: {news:?}");
        for bare in ["\"open\"", "\"explorer\"", "\"explorer.exe\"", "\"xdg-open\""] {
            assert!(!code.contains(bare), "맨 이름 {bare}");
        }
        let w = &code[code.find("mod windrive {").expect("windrive")..];
        assert!(w.contains("fn GetWindowsDirectoryW(buf: *mut u16, size: u32) -> u32;"));
        let l = &code[code.find("pub(crate) fn launcher()").expect("launcher")..];
        let l = &l[..l.find("\n}\n").unwrap()];
        assert!(l.contains("explorer_path_from(windrive::windows_dir().as_deref(), std::env::var(\"SystemRoot\").ok().as_deref())"), "윈 = GetWindowsDirectoryW → SystemRoot → C:\\Windows");
    }

    /// (codex 4R ②) 윈 셸 정션 폴더 — CLSID 이름 · desktop.ini CLSID= 판정(모든 기판 · 실제 파일) + open_plan 의 윈도 갈래가 열기·보기 둘 다 거절(소스 대조 · 윈 실기 0).
    #[test]
    fn windows_shell_junction_folders_are_refused() {
        let g = "{208D2C60-3AEA-1069-A2D7-08002B30309D}";
        assert!(is_clsid_name(&format!("자료.{g}")));
        assert!(is_clsid_name(&format!("x.{}", g.to_ascii_lowercase())));
        for n in ["자료", "a.pdf", "{208D2C60-3AEA-1069-A2D7-08002B30309D}", "x.{208D2C60-3AEA-1069-A2D7-08002B30309}", "x.{208D2C60_3AEA-1069-A2D7-08002B30309D}", "x.{208D2C60-3AEA-1069-A2D7-08002B30309D}.pdf"] {
            assert!(!is_clsid_name(n), "{n}");
        }
        let base = std::env::temp_dir().join(format!("vc-jnc-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        let home = base.join("home");
        let plain = home.join("교회").join("주보");
        std::fs::create_dir_all(&plain).unwrap();
        std::fs::write(plain.join("a.pdf"), b"%PDF").unwrap();
        let home_c = std::fs::canonicalize(&home).unwrap();
        let canon = |p: &std::path::Path| std::fs::canonicalize(p).unwrap();
        assert!(!shell_junction_on_path(&canon(&plain.join("a.pdf")), &home_c));
        // CLSID 이름 폴더 = 그 자신 · 그 안 파일(조상) 둘 다
        let j = home.join("교회").join(format!("네트워크.{g}"));
        std::fs::create_dir_all(&j).unwrap();
        std::fs::write(j.join("b.pdf"), b"%PDF").unwrap();
        assert!(shell_junction_on_path(&canon(&j), &home_c));
        assert!(shell_junction_on_path(&canon(&j.join("b.pdf")), &home_c));
        // desktop.ini CLSID= (UTF-8 · UTF-16LE BOM · CLSID2 · 앞 공백·대소문자) = 거절 · 다른 줄만 = 통과
        let cases: [(&str, Vec<u8>, bool); 5] = [
            ("d1", b"[.ShellClassInfo]\r\nCLSID={208D2C60-3AEA-1069-A2D7-08002B30309D}\r\n".to_vec(), true),
            ("d2", { let mut v = vec![0xFF, 0xFE]; v.extend("[.ShellClassInfo]\r\n  clsid2={0}\r\n".encode_utf16().flat_map(|u| u.to_le_bytes())); v }, true),
            ("d3", b"[.ShellClassInfo]\r\nIconResource=x.ico,0\r\nLocalizedResourceName=@x\r\n".to_vec(), false),
            ("d4", b"[.ShellClassInfo]\r\nCLSID ={0}\r\n".to_vec(), true),
            ("d5", b"; CLSID mention in comment only\r\n".to_vec(), false),
        ];
        for (n, body, want) in cases {
            let d = home.join("교회").join(n);
            std::fs::create_dir_all(&d).unwrap();
            std::fs::write(d.join("desktop.ini"), body).unwrap();
            std::fs::write(d.join("c.pdf"), b"%PDF").unwrap();
            assert_eq!(desktop_ini_has_clsid(&d), want, "{n}");
            assert_eq!(shell_junction_on_path(&canon(&d.join("c.pdf")), &home_c), want, "{n} 조상");
        }
        // 홈 자신·홈 밖 조상은 보지 않음(홈 아래만)
        std::fs::write(home.join("desktop.ini"), b"CLSID={0}\r\n").unwrap();
        assert!(!shell_junction_on_path(&canon(&plain.join("a.pdf")), &home_c));
        // 맥 동작 불변: 이 기판(맥·리눅스)에서는 open_plan 이 정션 판정을 부르지 않는다
        #[cfg(not(windows))]
        assert!(matches!(open_plan(&j, false, &home), Ok(OpenPlan::Folder(_))));
        let src = include_str!("viewcore.rs");
        let code: String = src.lines().filter(|l| !l.trim_start().starts_with("//")).collect::<Vec<_>>().join("\n");
        let op = &code[code.find("pub(crate) fn open_plan(").expect("open_plan")..];
        let op = &op[..op.find("\n}\n").unwrap()];
        let at = op.find("if shell_junction_on_path(&target, &home_c) {\n            return Err(\"executable_confirm\".into());").expect("open_plan 이 정션을 거절 안 함");
        assert!(op[..at].contains("#[cfg(windows)]\n    {"), "윈도 갈래");
        assert!(at < op.find("if reveal {").unwrap(), "폴더 보기(reveal)보다 먼저 = 둘 다 거절");
        let _ = std::fs::remove_dir_all(&base);
    }

    /// (codex 3R ④) 윈 매핑 네트워크 드라이브 — 드라이브 뿌리 뽑기(순수 · 모든 기판) + result_target 의 윈도 갈래가 GetDriveTypeW == DRIVE_REMOTE 로 거절하는지(소스 대조 · 윈 실기 0).
    #[test]
    fn windows_mapped_network_drive_is_refused_static() {
        assert_eq!(drive_root(r"\\?\H:\Users\x\a.pdf").as_deref(), Some(r"H:\"));
        assert_eq!(drive_root(r"C:\Users\x").as_deref(), Some(r"C:\"));
        assert_eq!(drive_root("d:/x").as_deref(), Some(r"d:\"));
        assert_eq!(drive_root(r"\\?\UNC\srv\share\a"), None);
        assert_eq!(drive_root(r"\\srv\share\a"), None);
        assert_eq!(drive_root("/Users/x/a.pdf"), None);
        assert_eq!(drive_root("C:"), None);
        let src = include_str!("viewcore.rs");
        let code: String = src.lines().filter(|l| !l.trim_start().starts_with("//")).collect::<Vec<_>>().join("\n");
        let rt = &code[code.find("pub(crate) fn result_target(").expect("result_target")..];
        let rt = &rt[..rt.find("\n}\n").expect("끝")];
        let at = rt.find("windrive::is_remote_drive(&r)").expect("result_target 이 원격 드라이브를 안 봄");
        assert!(rt[..at].trim_end().ends_with("if drive_root(&t.to_string_lossy()).is_some_and(|r|"), "검사 대상 = 정규 대상 t 의 드라이브 뿌리");
        assert!(rt[..at].contains("#[cfg(windows)]\n    if drive_root("), "윈도 갈래");
        assert!(rt[at..].starts_with("windrive::is_remote_drive(&r)) {\n        return Err(\"network_path\".into());"), "원격 = network_path 거절");
        assert!(rt.find("windrive::is_remote_drive").unwrap() < rt.find("strip_prefix(&home_c)").unwrap(), "홈 가둠 전에 거절");
        let w = &code[code.find("mod windrive {").expect("windrive")..];
        let w = &w[..w.find("\n}\n").expect("끝")];
        assert!(w.contains("pub(super) const DRIVE_REMOTE: u32 = 4;"));
        assert!(w.contains("#[link(name = \"kernel32\")]") && w.contains("fn GetDriveTypeW(root: *const u16) -> u32;"));
        assert!(w.contains("GetDriveTypeW(w.as_ptr()) == DRIVE_REMOTE"));
        assert!(w.contains(".chain(std::iter::once(0))"), "NUL 끝");
    }

    #[test]
    fn if_quiet_close_sends_conditions_and_refusal_is_not_closed() {
        // (조각 5 P1) 요청 = 원작자 칸(surface_id · owner_token) + if_quiet · expected_created_at · 데몬 거절(close_refused) = Err(첨부 그대로)
        let state = crate::Attachments(std::sync::Mutex::new(std::collections::HashMap::new()));
        let sent = std::sync::Arc::new(std::sync::Mutex::new(Value::Null));
        let s2 = sent.clone();
        let r = tauri::async_runtime::block_on(crate::close_surface_with(&state, std::path::Path::new("/nonexistent/cys.sock"), 7, |_| Some("tok".into()), move |_sock, params| async move {
            let p = if_quiet_close_params(params, 1700000000.125);
            *s2.lock().unwrap() = p;
            Ok(json!({"ok": false, "error": {"code": "close_refused", "message": "surface.close if_quiet refused: recent_human_input · not closed", "reason": "recent_human_input"}}))
        }));
        assert_eq!(*sent.lock().unwrap(), json!({"surface_id": 7, "owner_token": "tok", "if_quiet": true, "expected_created_at": 1700000000.125}));
        let e = r.expect_err("거절인데 닫힘으로 봤다");
        assert!(e.starts_with("close_refused:") && e.contains("recent_human_input"), "{e}");
        let ok = tauri::async_runtime::block_on(crate::close_surface_with(&state, std::path::Path::new("/nonexistent/cys.sock"), 7, |_| None, |_sock, params| async move {
            let p = if_quiet_close_params(params, 1.0);
            Ok(json!({"ok": true, "result": {"surface_id": p["surface_id"], "closed": true, "cause": "OwnerClose", "if_quiet": true}}))
        }));
        assert_eq!(ok, Ok(()));
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
        // (조각 5 · S1-8) 쓰기 줄에 넣지 못함 = 바이트 0 → 못 보냄 + 다시 보내기
        assert_eq!(err("write_stalled")["outcome"], "failed");
        assert_eq!(err("write_failed")["outcome"], "failed");
        assert_eq!(err("")["outcome"], "uncertain", "코드 없음 = 쓰기 0 근거 아님");
        assert_eq!(err("something_new")["outcome"], "uncertain");
        assert_eq!(classify_send(Ok(json!({})))["outcome"], "uncertain", "ok 칸 없음");
        assert_eq!(classify_send(Err((TransportClass::Definite, "x".into())))["outcome"], "failed");
        assert_eq!(classify_send(Err((TransportClass::Uncertain, "x".into())))["outcome"], "uncertain");
    }

    /// (조각 5 · §6-1) 깨움 말 = 큐 · 기계 표지 · 사람 표지 0 · operator_token(원장 무기록) 0 · owner_token(ACL) 만.
    #[test]
    fn auto_params_are_queued_machine_text_without_operator_token() {
        let p = auto_send_params(7, "[깨우기] x", Some("TOK"));
        assert_eq!(p["queued"], true);
        assert_eq!(p["machine_origin"], true);
        assert_eq!(p["human"], false);
        assert_eq!(p["clear_first"], false);
        assert_eq!(p["surface_id"], 7);
        assert!(p.get("operator_token").is_none(), "깨움 말이 오너 임무(원장 무기록)가 되면 안 된다");
        assert!(p.get("refuse_on_approval").is_none());
        assert_eq!(p["owner_token"], "TOK");
        assert!(auto_send_params(7, "x", None).get("owner_token").is_none());
    }

    /// (조각 5) 큐 적재 응답 → queued(번호) · failed(거부·전송 전) · uncertain(번호 없음·꼴 이상·전송 뒤 끊김).
    #[test]
    fn classify_auto_needs_a_queue_entry_id() {
        let ok = |r: Value| classify_auto(Ok(json!({"ok": true, "result": r})));
        let q = ok(json!({"surface_id": 1, "queued": true, "depth": 1, "queue_entry_id": "q-9"}));
        assert_eq!(q["outcome"], "queued");
        assert_eq!(q["queue_entry_id"], "q-9");
        assert_eq!(ok(json!({"queued": true, "depth": 1}))["outcome"], "uncertain");
        assert_eq!(ok(json!({"queued": true, "queue_entry_id": ""}))["outcome"], "uncertain");
        assert_eq!(ok(json!({"queued": false, "queue_entry_id": "q"}))["outcome"], "uncertain");
        assert_eq!(classify_auto(Ok(json!({"ok": false, "error": {"code": "queue_full", "message": "m"}})))["outcome"], "failed");
        assert_eq!(classify_auto(Ok(json!({})))["outcome"], "uncertain");
        assert_eq!(classify_auto(Err((TransportClass::Definite, "x".into())))["outcome"], "failed");
        assert_eq!(classify_auto(Err((TransportClass::Uncertain, "x".into())))["outcome"], "uncertain");
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

    /// ★1.1.16(S3-2) 링크 cwd = 풀린 경로의 슬러그가 둘째 후보 · 같으면 하나 · 상대 경로·잘못된 세션 id 는 후보를 만들지 않음.
    #[test]
    fn debt_d_s32_transcript_candidates_add_the_resolved_cwd() {
        let id = Some("0a4b82d0-9e01-4b29-aaaa-bbbbbbbbbbbb");
        let c = transcript_candidates(Some("/h/.cys/claude"), Some("/tmp/x"), id, Some("/private/tmp/x")).unwrap();
        assert_eq!(c, vec![
            std::path::PathBuf::from("/h/.cys/claude/projects/-tmp-x/0a4b82d0-9e01-4b29-aaaa-bbbbbbbbbbbb.jsonl"),
            std::path::PathBuf::from("/h/.cys/claude/projects/-private-tmp-x/0a4b82d0-9e01-4b29-aaaa-bbbbbbbbbbbb.jsonl"),
        ]);
        assert_eq!(transcript_candidates(Some("/h/.cys/claude"), Some("/h/m1"), id, Some("/h/m1")).unwrap().len(), 1, "같은 경로 = 하나");
        assert_eq!(transcript_candidates(Some("/h/.cys/claude"), Some("/h/m1"), id, None).unwrap().len(), 1);
        assert_eq!(transcript_candidates(Some("/h/.cys/claude"), Some("/h/m1"), id, Some("rel/x")).unwrap().len(), 1, "상대 경로 후보 금지");
        assert_eq!(transcript_candidates(Some("/h/.cys/claude"), Some("/h/m1"), Some("../x"), Some("/p")).unwrap_err(), "bad_session_id");
    }

    /// 링크 cwd 실물 — 풀린 경로 쪽 프로젝트 폴더의 세션 파일을 두 번째 후보로 연다(뿌리 안 · 첫 후보는 없음).
    #[cfg(unix)]
    #[test]
    fn debt_d_s32_symlinked_cwd_opens_the_resolved_slug_file() {
        let base = std::env::temp_dir().join(format!("cys-s32-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        let real = base.join("real-work");
        std::fs::create_dir_all(&real).unwrap();
        let link = base.join("link-work");
        std::os::unix::fs::symlink(&real, &link).unwrap();
        let cfg = base.join("cfg");
        let id = "0a4b82d0-9e01-4b29-aaaa-bbbbbbbbbbbb";
        let canon = std::fs::canonicalize(&link).unwrap();
        let want = cfg.join("projects").join(transcript_slug(canon.to_str().unwrap()));
        std::fs::create_dir_all(&want).unwrap();
        std::fs::write(want.join(format!("{id}.jsonl")), "{}\n").unwrap();
        let c = transcript_candidates(cfg.to_str(), link.to_str(), Some(id), canon.to_str()).unwrap();
        let first = open_bound(&cfg, &c[0]);
        let second = open_bound(&cfg, &c[1]);
        let _ = std::fs::remove_dir_all(&base);
        assert!(first.is_err(), "링크 그대로의 슬러그에는 파일이 없다(전제)");
        assert!(second.is_ok(), "풀린 경로 슬러그의 세션 파일을 못 열었다: {:?}", second.err());
    }

    /// (TICKET=cysr-1121-ui K-3) 바쁠 때 넘긴 말의 실측 꼴(Claude Code 2.1.332 · u25-evidence) — enqueue = 「queued」(uuid 없음 · 원문) ·
    /// 흡수 `attachment.queued_command` = 사람 말 user(uuid·부모·원문) · dequeue/remove = 넘기지 않음 · 다른 attachment = 종전대로 글 없는 고리.
    #[test]
    fn k3_queued_command_and_enqueue_become_records() {
        let enq = r#"{"type":"queue-operation","operation":"enqueue","timestamp":"2026-11-27T01:29:00.750Z","sessionId":"s","content":"U25-B 첫 줄\n둘째 줄"}"#;
        let rem = r#"{"type":"queue-operation","operation":"remove","timestamp":"2026-11-27T01:29:34.945Z","sessionId":"s","content":"U25-B 첫 줄\n둘째 줄","reason":"absorbed_mid_turn"}"#;
        let deq = r#"{"type":"queue-operation","operation":"dequeue","timestamp":"2026-11-27T01:30:07.517Z","sessionId":"s"}"#;
        let abs = r#"{"parentUuid":"p1","isSidechain":false,"attachment":{"type":"queued_command","prompt":"U25-B 첫 줄\n둘째 줄","commandMode":"prompt","origin":{"kind":"human"},"timestamp":"2026-11-27T01:29:00.748Z","humanTurn":true},"type":"attachment","uuid":"q1","timestamp":"2026-11-27T01:29:00.748Z"}"#;
        let bash = r#"{"parentUuid":"p1","attachment":{"type":"queued_command","prompt":"ls","commandMode":"bash"},"type":"attachment","uuid":"q2","timestamp":"t"}"#;
        let hook = r#"{"type":"attachment","uuid":"x1","parentUuid":"q1","timestamp":"t3","attachment":{"type":"hook_additional_context","content":["비밀 글"]}}"#;
        let buf = format!("{enq}\n{rem}\n{deq}\n{abs}\n{bash}\n{hook}\n");
        let (recs, used, bad) = parse_transcript_chunk(buf.as_bytes());
        assert_eq!((used, bad), (buf.len(), 0));
        assert_eq!(recs.len(), 4, "enqueue 1 + 흡수 1 + bash 모드 고리 1 + 훅 고리 1 · remove·dequeue 0");
        assert_eq!(recs[0]["role"], "queued");
        assert_eq!(recs[0]["text"], "U25-B 첫 줄\n둘째 줄");
        assert!(recs[0]["uuid"].is_null());
        assert_eq!(recs[0]["ts"], "2026-11-27T01:29:00.750Z");
        assert_eq!(recs[1]["role"], "user");
        assert_eq!(recs[1]["uuid"], "q1");
        assert_eq!(recs[1]["parent"], "p1");
        assert_eq!(recs[1]["text"], "U25-B 첫 줄\n둘째 줄");
        assert_eq!(recs[1]["ts"], "2026-11-27T01:29:00.748Z");
        assert_eq!(recs[2]["role"], "link", "bash 모드 대기 명령은 사람 말 레코드로 올리지 않는다");
        assert!(recs[2]["text"].is_null());
        assert_eq!(recs[3]["role"], "link");
        assert!(recs[3]["text"].is_null(), "다른 attachment 본문은 여전히 0자(NFR-S3)");
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

    /// (TICKET=cysr-1118-ui ①) 진행 줄 재료 — 도구 이름 + 짧은 단서만(입력 전문 0) · 생각 표지 · user 레코드엔 없음.
    #[test]
    fn assistant_tool_use_becomes_short_steps_without_full_input() {
        let long_cmd = format!("echo {}\nrm -rf /tmp/x", "가".repeat(100));
        let a = json!({"type":"assistant","uuid":"a1","parentUuid":"u1","timestamp":"t","message":{"content":[
            {"type":"thinking","thinking":""},
            {"type":"tool_use","id":"t1","name":"Read","input":{"file_path":"/Users/x/secret/dir/core.ts","limit":5}},
            {"type":"tool_use","id":"t2","name":"Bash","input":{"command":"cargo test","description":"시험 돌리기"}},
            {"type":"tool_use","id":"t3","name":"Bash","input":{"command": long_cmd}},
            {"type":"tool_use","id":"t4","name":"Grep","input":{"pattern":"open_bound","path":"/a"}},
            {"type":"tool_use","id":"t5","name":"WebFetch","input":{"url":"https://example.com/p?q=1","prompt":"비밀 질문"}},
            {"type":"tool_use","id":"t6","name":"mcp__x__y","input":{"token":"zzz"}},
            {"type":"tool_use","id":"t7","name":"Edit","input":{"file_path":"C:\\Users\\x\\main.rs","old_string":"a","new_string":"b"}}
        ]}}).to_string();
        let u = json!({"type":"user","uuid":"u2","parentUuid":"a1","message":{"content":[{"type":"tool_result","tool_use_id":"t1","content":"파일 내용"}]}}).to_string();
        let (recs, _, _) = parse_transcript_chunk(format!("{a}\n{u}\n").as_bytes());
        let t = &recs[0]["tools"];
        assert_eq!(recs[0]["thinking"], true);
        assert_eq!(t[0], json!({"name":"Read","hint":"core.ts"}), "파일 = 마지막 이름만");
        assert_eq!(t[1], json!({"name":"Bash","hint":"시험 돌리기"}), "명령 = 설명 우선");
        assert_eq!(t[2], json!({"name":"Bash","hint":null}), "설명 없는 명령 = 단계 이름만(원문 0 · codex 1R major)");
        assert_eq!(t[3], json!({"name":"Grep","hint":"open_bound"}));
        assert_eq!(t[4], json!({"name":"WebFetch","hint":"example.com"}), "웹 = 호스트만");
        assert_eq!(t[5], json!({"name":"mcp__x__y","hint":null}), "모르는 도구 = 이름만");
        assert_eq!(t[6], json!({"name":"Edit","hint":"main.rs"}), "윈 경로도 마지막 이름");
        let all = recs[0].to_string();
        assert!(!all.contains("secret") && !all.contains("비밀") && !all.contains("zzz") && !all.contains("old_string"), "입력 전문·다른 칸 0");
        assert!(!all.contains("echo") && !all.contains("rm -rf"), "명령 원문 0");
        assert!(recs[1]["tools"].is_null() && recs[1]["thinking"] == false, "user 레코드(도구 결과)엔 없음");
        // 짧은 비밀 명령 · URL 자격증명·포트·경로
        let w = |name: &str, input: Value| tool_hint(name, &input);
        assert_eq!(w("Bash", json!({"command":"TOKEN=secret run"})), None);
        assert_eq!(w("WebFetch", json!({"url":"https://alice:secret@Example.com:8443/p?q=1"})), Some("example.com".into()));
        assert_eq!(w("WebFetch", json!({"url":"http://[::1]:80/x"})), Some("::1".into()));
        assert_eq!(w("WebFetch", json!({"url":"not a url secret"})), None, "꼴 아님 = 없음(원문 0)");
        assert_eq!(w("WebFetch", json!({"url":"https://a b@c/"})), Some("c".into()));
        assert!(!recs[1].to_string().contains("파일 내용"));
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

    /// (TICKET=cysr-1118-ui ①-4) 윈 canonicalize 의 확장 길이 접두를 걷어 Claude Code 슬러그와 같은 꼴로.
    #[test]
    fn strip_verbatim_drops_extended_length_prefix_only() {
        assert_eq!(strip_verbatim(r"\\?\C:\Users\x\p"), r"C:\Users\x\p");
        assert_eq!(strip_verbatim(r"\\?\UNC\srv\share\p"), r"\\srv\share\p");
        assert_eq!(strip_verbatim("/private/tmp/x"), "/private/tmp/x");
        assert_eq!(transcript_slug(&strip_verbatim(r"\\?\C:\Users\x\p")), "C--Users-x-p", "윈 슬러그(Claude Code 프로젝트 폴더 꼴)");
    }

    /// (TICKET=cysr-chat-held-win) 빠른 길(`transcript_supported` = false → RPC 0 · unsupported_platform)은 `open_bound` 의 실제 동작과 같아야 한다 —
    /// 열 수 있는 플랫폼에서 빠른 길을 타거나(기록 못 읽음), 못 여는 플랫폼에서 RPC 를 부르면(예전 윈 = 직렬 풀에 조회 2개) 안 된다.
    /// ★cysr-1118-ui ①-4: 윈도도 이제 true(연 핸들 대조 판) — 없는 설정 폴더 = no_config_dir(unsupported 아님).
    #[test]
    fn transcript_supported_matches_open_bound() {
        let cfg = std::path::Path::new("/nonexistent-cysr-chat-held-win");
        let r = open_bound(cfg, &cfg.join("x.jsonl"));
        assert_eq!(transcript_supported(), r.err() != Some("unsupported_platform"));
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

/// (cysr-1116-s2 · codex 3R) 미룬 좌석 첫 붙기 손잡기 — 연결 → `surface.attach {history_since, history_rows}` → ack 를 [`ATTACH_HISTORY_DEADLINE`] 안에.
/// 성공 = (ack 뒤에 선 읽기 끝, 데몬 history 칸). 그 뒤 바이트 = 밀려난 행 · 줄 내림 · 화면 스냅숏 · 실시간(데몬 한 락) — 그대로 흘리면 이음매 빠짐·겹침 0.
/// 실패 = (None, {status: timeout|error|not_attached}) — 호출자는 종전 길로 붙고 화면은 안내 줄을 단다.
/// 구 데몬(이 인자를 모름) = ack 에 history 칸 없음 → `{status:"unsupported"}`(기록 없이 붙은 것 = 화면이 안내).
pub(crate) async fn attach_with_history(
    sock: &std::path::Path,
    surface_id: u64,
    since: u64,
    rows: u16,
) -> (Option<tokio::io::BufReader<crate::Stream>>, Value) {
    use tokio::io::{AsyncBufReadExt, AsyncWriteExt};
    let run = async {
        let mut stream = crate::connect_to(sock).await.map_err(|_| "error")?;
        let req = json!({"id": 1, "method": "surface.attach", "params": {"surface_id": surface_id, "history_since": since, "history_rows": rows}});
        let mut line = serde_json::to_vec(&req).unwrap_or_default();
        line.push(b'\n');
        stream.write_all(&line).await.map_err(|_| "error")?;
        let mut reader = tokio::io::BufReader::new(stream);
        let mut ack = String::new();
        if reader.read_line(&mut ack).await.unwrap_or(0) == 0 {
            return Err("error");
        }
        let v: Value = serde_json::from_str(ack.trim()).unwrap_or(Value::Null);
        if v["ok"].as_bool() != Some(true) {
            return Err("not_attached");
        }
        let hist = match v["result"].get("history") {
            Some(h) if h.is_object() => h.clone(),
            _ => json!({"status": "unsupported"}),
        };
        Ok((reader, hist))
    };
    match tokio::time::timeout(ATTACH_HISTORY_DEADLINE, run).await {
        Ok(Ok((r, h))) => (Some(r), h),
        Ok(Err(code)) => (None, json!({"status": code})),
        Err(_) => (None, json!({"status": "timeout"})),
    }
}

/// 손잡기 상한 — 데몬이 락 안에서 뜨는 기록은 최대 5,000행(cysd `ATTACH_HISTORY_MAX_ROWS`)이라 정상은 수십 ms.
pub(crate) const ATTACH_HISTORY_DEADLINE: std::time::Duration = std::time::Duration::from_secs(5);

/// (cysr-1116-s2 · codex 4R major) 좌석 스트림 세대 — (소켓 slug, 좌석)마다 마지막 `start_surface_stream` 의 번호. 손잡기를 기다린 사이 더 새
/// 호출이 오면 옛 호출은 펌프를 세우지 않는다 · stop 은 자기 세대만 멈춘다.
#[derive(Default)]
pub(crate) struct StreamGens(std::sync::Mutex<std::collections::HashMap<(String, u64), u64>>);
static NEXT_STREAM_GEN: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(1);
impl StreamGens {
    /// 새 세대를 시작하고 그 번호를 돌려준다(그 키의 「지금」 = 이 번호).
    pub(crate) fn begin(&self, key: &(String, u64)) -> u64 {
        let g = NEXT_STREAM_GEN.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        self.0.lock().unwrap().insert(key.clone(), g);
        g
    }
    pub(crate) fn is_current(&self, key: &(String, u64), gen: u64) -> bool {
        self.0.lock().unwrap().get(key) == Some(&gen)
    }
}

/// 손잡이 끊기 꼴 — 시험이 가짜 손잡이로 abort 를 센다.
pub(crate) trait AbortHandle {
    fn abort_now(&self);
}
impl AbortHandle for tauri::async_runtime::JoinHandle<()> {
    fn abort_now(&self) {
        self.abort();
    }
}

/// 세대가 아직 「지금」이면 손잡이를 넣고(같은 키 옛 손잡이 = abort) true · 더 새 호출이 있으면 이 손잡이를 abort 하고 false.
/// 세대 잠금을 쥔 채 판정·넣기를 한 번에(그 사이 begin 이 끼지 않게).
pub(crate) fn commit_stream_into<H: AbortHandle>(
    gens: &StreamGens,
    map: &std::sync::Mutex<std::collections::HashMap<(String, u64), H>>,
    key: &(String, u64),
    gen: u64,
    handle: H,
) -> bool {
    let g = gens.0.lock().unwrap();
    if g.get(key) != Some(&gen) {
        handle.abort_now();
        return false;
    }
    if let Some(old) = map.lock().unwrap().insert(key.clone(), handle) {
        old.abort_now();
    }
    true
}
pub(crate) fn commit_stream(gens: &StreamGens, att: &crate::Attachments, key: &(String, u64), gen: u64, handle: tauri::async_runtime::JoinHandle<()>) -> bool {
    commit_stream_into(gens, &att.0, key, gen, handle)
}
/// stop — `gen` 을 주면 그 세대가 지금일 때만 멈춘다(옛 시도가 새 스트림을 멈추지 못하게).
pub(crate) fn stop_stream_in<H: AbortHandle>(
    gens: &StreamGens,
    map: &std::sync::Mutex<std::collections::HashMap<(String, u64), H>>,
    key: &(String, u64),
    gen: Option<u64>,
) -> bool {
    let g = gens.0.lock().unwrap();
    if let Some(gen) = gen {
        if g.get(key) != Some(&gen) {
            return false;
        }
    }
    match map.lock().unwrap().remove(key) {
        Some(h) => {
            h.abort_now();
            true
        }
        None => false,
    }
}

/// (cysr-1116-s2 · codex 4R blocking) 데몬이 기록 연결에서 청크를 놓쳤을 때 마지막에 쓰는 표지 — cysd `ATTACH_LAGGED_MARKER` 와 같은 바이트.
pub(crate) const ATTACH_LAGGED_MARKER: &[u8] = b"\x1b]7799;cys-attach-lagged\x07";
/// 놓침 복구 다시 손잡기 상한 — 넘으면 종전 스냅숏 길(기록 없이)로 붙고 화면에 안내 사건.
pub(crate) const LAG_RECOVER_MAX: u32 = 3;
/// 스트림 끝(최근 바이트 꼬리)이 놓침 표지로 끝나는가.
pub(crate) fn ends_with_lag_marker(tail: &[u8]) -> bool {
    tail.ends_with(ATTACH_LAGGED_MARKER)
}
/// 놓침 복구 재료 — 같은 커서로 다시 붙는다.
pub(crate) struct Recover {
    pub(crate) sock: std::path::PathBuf,
    pub(crate) socket: Option<String>,
    pub(crate) surface_id: u64,
    pub(crate) since: u64,
    pub(crate) rows: u16,
}

/// 기록 없이(종전 스냅숏 길) 손잡기 — 놓침 복구가 상한을 넘었을 때.
async fn attach_plain(sock: &std::path::Path, surface_id: u64) -> Option<tokio::io::BufReader<crate::Stream>> {
    use tokio::io::{AsyncBufReadExt, AsyncWriteExt};
    let run = async {
        let mut stream = crate::connect_to(sock).await.ok()?;
        let req = json!({"id": 1, "method": "surface.attach", "params": {"surface_id": surface_id}});
        let mut line = serde_json::to_vec(&req).unwrap_or_default();
        line.push(b'\n');
        stream.write_all(&line).await.ok()?;
        let mut reader = tokio::io::BufReader::new(stream);
        let mut ack = String::new();
        if reader.read_line(&mut ack).await.unwrap_or(0) == 0 {
            return None;
        }
        let v: Value = serde_json::from_str(ack.trim()).unwrap_or(Value::Null);
        (v["ok"].as_bool() == Some(true)).then_some(reader)
    };
    tokio::time::timeout(ATTACH_HISTORY_DEADLINE, run).await.ok().flatten()
}

/// 손잡기를 마친 읽기 끝을 이벤트로 흘린다 — 종전 `start_surface_stream` 고리와 같은 꼴(8KiB · base64 · 끝나면 exited).
/// `recover` 가 있으면(기록 연결) 데몬 놓침 표지로 끝난 연결 = xterm 전체 초기화(ESC c) 뒤 같은 커서로 다시 손잡기(최대 [`LAG_RECOVER_MAX`]) ·
/// 넘으면 기록 없이 붙고 `seat-history-status {socket, surface_id, status:"lagged"}` 사건(화면 안내 줄). 다시 손잡기 결과가 ok 가 아니어도 같은 사건.
pub(crate) async fn pump_surface_stream(
    app: tauri::AppHandle,
    mut reader: tokio::io::BufReader<crate::Stream>,
    event_output: String,
    event_exited: String,
    recover: Option<Recover>,
) {
    use base64::Engine;
    use tauri::Emitter;
    use tokio::io::AsyncReadExt;
    let emit_bytes = |app: &tauri::AppHandle, b: &[u8]| app.emit(&event_output, base64::engine::general_purpose::STANDARD.encode(b)).is_ok();
    let status = |app: &tauri::AppHandle, r: &Recover, st: &str| {
        let _ = app.emit("seat-history-status", json!({"socket": r.socket, "surface_id": r.surface_id, "status": st}));
    };
    let mut buf = [0u8; 8192];
    let mut tail: Vec<u8> = Vec::with_capacity(64);
    let mut tries = 0u32;
    'outer: loop {
        loop {
            match reader.read(&mut buf).await {
                Ok(0) | Err(_) => break,
                Ok(n) => {
                    tail.extend_from_slice(&buf[..n]);
                    if tail.len() > 64 {
                        tail.drain(..tail.len() - 64);
                    }
                    if !emit_bytes(&app, &buf[..n]) {
                        break 'outer;
                    }
                }
            }
        }
        let Some(r) = recover.as_ref() else { break };
        if !ends_with_lag_marker(&tail) {
            break;
        }
        tail.clear();
        // 놓침 — 화면을 통째로 비우고(ESC c = xterm 전체 초기화 · 스크롤백 포함) 같은 커서로 다시 그린다
        let _ = emit_bytes(&app, b"\x1bc");
        if tries < LAG_RECOVER_MAX {
            tries += 1;
            let (again, hist) = attach_with_history(&r.sock, r.surface_id, r.since, r.rows).await;
            if let Some(rd) = again {
                if hist["status"] != json!("ok") {
                    status(&app, r, hist["status"].as_str().unwrap_or("unsupported"));
                }
                reader = rd;
                continue;
            }
        }
        // 상한·손잡기 실패 = 종전 스냅숏 길(기록 없이) + 안내 — 기록 없는 연결은 놓침 표지를 쓰지 않으므로 다음 끝 = 종료
        status(&app, r, "lagged");
        match attach_plain(&r.sock, r.surface_id).await {
            Some(rd) => reader = rd,
            None => break,
        }
    }
    let _ = app.emit(&event_exited, ());
}

/// (cysr-1116-s2 · codex 3R major · 4R) 스트림 정지 — 붙기를 기다린 사이 대화 화면으로 돌아간 좌석(출력 흐름 0)·늦게 끝난 옛 시도 정리용.
/// `stream_gen` 을 주면 그 세대가 지금일 때만 멈춘다(옛 시도가 새 스트림을 멈추지 못하게 · codex 4R). exited 사건은 안 쏜다.
#[tauri::command]
pub fn stop_surface_stream(
    state: tauri::State<'_, crate::Attachments>,
    gens: tauri::State<'_, StreamGens>,
    socket: Option<String>,
    surface_id: u64,
    stream_gen: Option<u64>,
) -> bool {
    let sock = resolve_socket(&socket);
    let key = (crate::sock_slug(&sock), surface_id);
    stop_stream_in(&gens, &state.0, &key, stream_gen)
}

#[cfg(test)]
mod stream_owner_tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;
    struct Fake(Arc<AtomicUsize>);
    impl AbortHandle for Fake {
        fn abort_now(&self) {
            self.0.fetch_add(1, Ordering::SeqCst);
        }
    }
    fn key() -> (String, u64) {
        ("s".into(), 7)
    }
    /// 겹친 두 호출 — A 시작 → B 시작 → A 손잡기 끝(넣기) → B 넣기: 펌프 = B 하나 · A 는 스스로 abort.
    #[test]
    fn overlapping_starts_leave_exactly_one_pump() {
        let gens = StreamGens::default();
        let map = std::sync::Mutex::new(std::collections::HashMap::<(String, u64), Fake>::new());
        let (a_ab, b_ab) = (Arc::new(AtomicUsize::new(0)), Arc::new(AtomicUsize::new(0)));
        let ga = gens.begin(&key());
        let gb = gens.begin(&key());
        assert!(!commit_stream_into(&gens, &map, &key(), ga, Fake(a_ab.clone())), "옛 호출은 넣지 않는다");
        assert!(commit_stream_into(&gens, &map, &key(), gb, Fake(b_ab.clone())));
        assert_eq!((a_ab.load(Ordering::SeqCst), b_ab.load(Ordering::SeqCst), map.lock().unwrap().len()), (1, 0, 1));
        // 순서가 거꾸로(B 넣고 A 늦게)여도 같다
        let c_ab = Arc::new(AtomicUsize::new(0));
        assert!(!commit_stream_into(&gens, &map, &key(), ga, Fake(c_ab.clone())));
        assert_eq!((c_ab.load(Ordering::SeqCst), b_ab.load(Ordering::SeqCst)), (1, 0));
    }
    /// 같은 세대 안에서 덮어쓰면 옛 손잡이를 abort(두 펌프 0).
    #[test]
    fn overwrite_aborts_previous_handle() {
        let gens = StreamGens::default();
        let map = std::sync::Mutex::new(std::collections::HashMap::<(String, u64), Fake>::new());
        let g = gens.begin(&key());
        let (x, y) = (Arc::new(AtomicUsize::new(0)), Arc::new(AtomicUsize::new(0)));
        assert!(commit_stream_into(&gens, &map, &key(), g, Fake(x.clone())));
        assert!(commit_stream_into(&gens, &map, &key(), g, Fake(y.clone())));
        assert_eq!((x.load(Ordering::SeqCst), y.load(Ordering::SeqCst), map.lock().unwrap().len()), (1, 0, 1));
    }
    /// stop = 자기 세대만 · 세대 없음 = 종전(무엇이든 멈춤).
    #[test]
    fn stop_only_own_generation() {
        let gens = StreamGens::default();
        let map = std::sync::Mutex::new(std::collections::HashMap::<(String, u64), Fake>::new());
        let old = gens.begin(&key());
        let new = gens.begin(&key());
        let n = Arc::new(AtomicUsize::new(0));
        assert!(commit_stream_into(&gens, &map, &key(), new, Fake(n.clone())));
        assert!(!stop_stream_in(&gens, &map, &key(), Some(old)), "옛 세대 stop 은 새 스트림을 못 멈춘다");
        assert_eq!(n.load(Ordering::SeqCst), 0);
        assert!(stop_stream_in(&gens, &map, &key(), Some(new)));
        assert_eq!(n.load(Ordering::SeqCst), 1);
        assert!(!stop_stream_in(&gens, &map, &key(), None), "이미 비었다");
    }
    /// 놓침 표지 = cysd 와 같은 바이트 · 꼬리 판정.
    #[test]
    fn lag_marker_matches_daemon_and_tail_check() {
        let src = include_str!("../../src/bin/cysd/main.rs");
        assert!(src.contains(r#"const ATTACH_LAGGED_MARKER: &[u8] = b"\x1b]7799;cys-attach-lagged\x07";"#));
        assert_eq!(ATTACH_LAGGED_MARKER, b"\x1b]7799;cys-attach-lagged\x07");
        let mut t = b"some output".to_vec();
        assert!(!ends_with_lag_marker(&t));
        t.extend_from_slice(ATTACH_LAGGED_MARKER);
        assert!(ends_with_lag_marker(&t));
        t.push(b'x');
        assert!(!ends_with_lag_marker(&t));
    }
}

/// (1.1.19 · TICKET=cysr-1119-s3 · CH-C) watch · tail · 되돌리기 — T-U5 · F10 · F06(Rust 몫) · 카드 C 「tail = RPC 0」 · 카드 E ①.
#[cfg(test)]
mod chat_watch_tests {
    use super::*;

    fn st(len: u64, a: u64) -> PathStat {
        PathStat { len, ident: (1, a) }
    }
    fn tmp(tag: &str) -> std::path::PathBuf {
        let d = std::env::temp_dir().join(format!("vc-cw-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }
    const L1: &[u8] = b"{\"type\":\"assistant\",\"uuid\":\"a1\",\"message\":{\"content\":\"one\"}}\n";
    const L2: &[u8] = b"{\"type\":\"assistant\",\"uuid\":\"a2\",\"message\":{\"content\":\"two\"}}\n";

    #[test]
    fn t_u5_watch_step_state_machine() {
        // 늘어남 → 사건 1 · 같음 → 0 · 줄어듦 → reset · 식별 바뀜 → reset · stat 실패 → 0(그대로) · 실패 뒤 늘어남 → 사건
        assert_eq!(watch_step(st(10, 7), Some(st(12, 7))), (st(12, 7), Some(WatchEvent::Grew(12))));
        assert_eq!(watch_step(st(12, 7), Some(st(12, 7))), (st(12, 7), None));
        assert_eq!(watch_step(st(12, 7), Some(st(3, 7))), (st(3, 7), Some(WatchEvent::Reset(3))));
        assert_eq!(watch_step(st(12, 7), Some(st(40, 8))), (st(40, 8), Some(WatchEvent::Reset(40))), "식별이 바뀌면 길어져도 reset");
        assert_eq!(watch_step(st(12, 7), None), (st(12, 7), None), "stat 실패 = 다음 박자");
        assert_eq!(watch_step(st(12, 7), Some(st(20, 7))).1, Some(WatchEvent::Grew(20)));
        // reset 뒤 같은 관측은 다시 reset 을 내지 않는다(새 파일이 기준)
        let (p, _) = watch_step(st(12, 7), Some(st(3, 8)));
        assert_eq!(watch_step(p, Some(st(3, 8))).1, None);
        assert_eq!(WATCH_TICK_MS, 250);
    }

    #[test]
    fn t_u5_same_len_recreate_within_15s_verdicts() {
        // master#5c1d346c: 「같은 길이 · 15초 안 재생성」 지금 판정을 값으로 남긴다(고침 아님 · 기록).
        // ⑴ 유닉스(이 기계 실파일 · 옛 파일을 쥔 채 = inode 재사용 불가 · watch 도 쥔다) → 잡음
        let d = tmp("len");
        let p = d.join("s.jsonl");
        std::fs::write(&p, L1).unwrap();
        let held = std::fs::File::open(&p).unwrap();
        let start = handle_stat(&held).unwrap();
        std::fs::remove_file(&p).unwrap();
        std::fs::write(&p, L2).unwrap(); // 같은 길이
        assert_eq!(L1.len(), L2.len());
        let unix_verdict = match watch_step(start, watch_probe(&p, &held)).1 {
            Some(WatchEvent::Reset(_)) => "잡음",
            _ => "못 잡음",
        };
        #[cfg(unix)]
        assert_eq!(unix_verdict, "잡음");
        let _ = unix_verdict;
        // ⑵ 윈 꼴(식별 = 만든 시각 · 터널링이 옛 만든 시각을 물려줌 = 식별 같음 · 길이 같음) → 못 잡음(알고 남긴 것 ② · 줄어듦일 때만 잡음)
        let tunneled = PathStat { len: L1.len() as u64, ident: (133_000_000_000_000_000, 0) };
        let win_same_len = match watch_step(tunneled, Some(tunneled)).1 {
            Some(WatchEvent::Reset(_)) => "잡음",
            _ => "못 잡음",
        };
        assert_eq!(win_same_len, "못 잡음");
        let win_shorter = match watch_step(tunneled, Some(PathStat { len: 5, ..tunneled })).1 {
            Some(WatchEvent::Reset(_)) => "잡음",
            _ => "못 잡음",
        };
        assert_eq!(win_shorter, "잡음");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn f10_recreated_file_is_reset_by_path_stat() {
        // F10: 쥔 핸들 fstat 이 아니라 경로 stat — 지우고 더 길게 다시 만들어도 reset(쥔 핸들 stat 은 옛 파일 = 못 봄 → 뮤턴트 붉음)
        let d = tmp("f10");
        let p = d.join("s.jsonl");
        std::fs::write(&p, L1).unwrap();
        let held = std::fs::File::open(&p).unwrap();
        let start = handle_stat(&held).unwrap();
        std::fs::OpenOptions::new().append(true).open(&p).unwrap().write_all_compat(L2);
        let (prev, ev) = watch_step(start, watch_probe(&p, &held));
        assert_eq!(ev, Some(WatchEvent::Grew((L1.len() + L2.len()) as u64)), "덧붙이기 → 사건 1");
        assert_eq!(watch_step(prev, watch_probe(&p, &held)).1, None, "같음 → 0");
        std::fs::remove_file(&p).unwrap();
        let mut big = L1.to_vec();
        big.extend_from_slice(L2);
        big.extend_from_slice(L2);
        std::fs::write(&p, &big).unwrap();
        assert!(matches!(watch_step(prev, watch_probe(&p, &held)).1, Some(WatchEvent::Reset(_))), "재생성(더 김) → reset");
        assert_eq!(watch_step(prev, handle_stat(&held)).1, None, "대조: 쥔 핸들 stat 으로는 재생성이 안 보인다");
        std::fs::remove_file(&p).unwrap();
        assert_eq!(watch_step(prev, watch_probe(&p, &held)).1, None, "경로 없음(stat 실패) → 다음 박자");
        let _ = std::fs::remove_dir_all(&d);
    }

    trait WriteAllCompat {
        fn write_all_compat(self, b: &[u8]);
    }
    impl WriteAllCompat for std::fs::File {
        fn write_all_compat(mut self, b: &[u8]) {
            use std::io::Write;
            self.write_all(b).unwrap();
        }
    }

    #[test]
    fn tail_reports_from_and_to_offset() {
        let d = tmp("tail");
        let p = d.join("s.jsonl");
        std::fs::write(&p, L1).unwrap();
        let file = std::fs::File::open(&p).unwrap();
        let ident = handle_stat(&file).unwrap().ident;
        let w = WatchedFile { surface_id: 5, session_id: "sess-1".into(), path: p.clone(), file, ident, gen: 1 };
        let a = tail_on(&w, 0).unwrap();
        assert_eq!((a["from_offset"].as_u64(), a["to_offset"].as_u64()), (Some(0), Some(L1.len() as u64)));
        assert_eq!(a["records"][0]["uuid"], "a1");
        assert_eq!(a["session_id"], "sess-1");
        std::fs::OpenOptions::new().append(true).open(&p).unwrap().write_all_compat(L2);
        let b = tail_on(&w, L1.len() as u64).unwrap();
        assert_eq!(b["from_offset"].as_u64(), Some(L1.len() as u64));
        assert_eq!(b["to_offset"], b["next_offset"]);
        assert_eq!(b["records"].as_array().map(|r| r.len()), Some(1));
        assert_eq!(b["records"][0]["uuid"], "a2");
        assert_eq!(b["more"], false, "상한 안 = 더 없음");
        // 읽기 상한을 넘는 쌓임 → more = true · 이어 읽으면 false
        let n = (TRANSCRIPT_READ_MAX as usize / L1.len()) + 10;
        std::fs::OpenOptions::new().append(true).open(&p).unwrap().write_all_compat(&L1.repeat(n));
        let big = tail_on(&w, (L1.len() + L2.len()) as u64).unwrap();
        assert_eq!(big["more"], true);
        let rest = tail_on(&w, big["to_offset"].as_u64().unwrap()).unwrap();
        assert_eq!(rest["more"], false);
        assert!(rest["records"].as_array().map(|r| !r.is_empty()).unwrap_or(false));
        let c = tail_on(&w, 100_000_000).unwrap(); // 화면 오프셋이 파일보다 큼 = 줄어듦
        assert_eq!((c["reset"].as_bool(), c["from_offset"].as_u64()), (Some(true), Some(0)));
        // 경로가 다른 파일이 됨 → 옛 핸들을 읽지 않고 reset(records 0)
        std::fs::remove_file(&p).unwrap();
        std::fs::write(&p, L2).unwrap();
        let e = tail_on(&w, L1.len() as u64).unwrap();
        assert_eq!(e["reset"], true);
        assert_eq!(e["records"].as_array().map(|r| r.len()), Some(0));
        let _ = std::fs::remove_dir_all(&d);
    }

    fn body_of<'a>(src: &'a str, head: &str) -> &'a str {
        let i = src.find(head).unwrap_or_else(|| panic!("{head} 소실"));
        &src[i..i + src[i..].find("\n}\n").expect("fn 끝")]
    }

    #[test]
    fn chat_transcript_tail_has_no_rpc() {
        // 카드 C 「tail = RPC 0」 · watch 박자 작업도 RPC 0(데몬 조회는 걸 때 bound_transcript 1회뿐)
        let src = include_str!("viewcore.rs");
        let prod = &src[..src.find("#[cfg(test)]\nmod tests {").expect("시험 모듈 경계")];
        for head in ["pub async fn chat_transcript_tail(", "pub(crate) fn tail_on(", "pub(crate) fn watch_probe(", "pub(crate) fn path_stat("] {
            let b = body_of(prod, head);
            for bad in ["rpc_on(", "rpc_full", "connect_to(", "resolve_socket("] {
                assert!(!b.contains(bad), "{head} 안에 {bad}");
            }
        }
        let w = body_of(prod, "pub async fn chat_transcript_watch(");
        let task = &w[w.find("tauri::async_runtime::spawn(").expect("박자 작업")..];
        for bad in ["rpc_on(", "rpc_full", "bound_transcript("] {
            assert!(!task.contains(bad), "박자 작업 안에 {bad}");
        }
        assert_eq!(w.matches("bound_transcript(").count(), 1, "걸 때 1회");
    }

    #[test]
    fn chat_watch_loop_sleeps_not_interval() {
        // 한 박자 끝난 뒤 다음 박자(겹침 0 · 밀린 박자 몰림 0) · 박자 관측 = 경로 stat(watch_probe)
        let src = include_str!("viewcore.rs");
        let prod = &src[..src.find("#[cfg(test)]\nmod tests {").expect("시험 모듈 경계")];
        let w = body_of(prod, "pub async fn chat_transcript_watch(");
        assert!(w.contains("tokio::time::sleep(std::time::Duration::from_millis(WATCH_TICK_MS)).await;"));
        assert!(!w.contains("interval("));
        assert_eq!(w.matches("tauri::async_runtime::spawn(").count(), 1);
        assert!(w.contains("watch_step(prev, watch_probe(&probe_path, &probe_file))"));
        assert!(body_of(prod, "pub(crate) fn watch_probe(").contains("path_stat(path)"));
    }

    #[test]
    fn chat_transcript_and_watch_open_through_one_function() {
        // 허용 경로 규칙 한 벌(P3 v4 §3-7 C-1) — 두 명령 모두 bound_transcript 로 열고, 직접 RPC·open_bound 를 부르지 않는다
        let src = include_str!("viewcore.rs");
        let prod = &src[..src.find("#[cfg(test)]\nmod tests {").expect("시험 모듈 경계")];
        for head in ["pub async fn chat_transcript(", "pub async fn chat_transcript_watch("] {
            let b = body_of(prod, head);
            assert_eq!(b.matches("bound_transcript(").count(), 1, "{head}");
            assert!(!b.contains("rpc_on(") && !b.contains("open_bound("), "{head}");
        }
        let h = body_of(prod, "async fn bound_transcript(");
        assert!(h.contains(r#"rpc_on(sock, "surface.list""#) && h.contains(r#"rpc_on(sock, "org.status""#));
        assert!(h.contains("transcript_candidates(") && h.contains("open_bound("));
    }

    #[test]
    fn v4_unwatch_with_gen_only_hits_that_watch() {
        assert!(unwatch_hits(Some(3), Some(3)));
        assert!(!unwatch_hits(Some(4), Some(3)), "늦게 처리된 옛 세대 unwatch 는 새 watch 를 안 내림");
        assert!(unwatch_hits(Some(4), None), "세대 없음 = 무엇이든(거는 중 끊기)");
        assert!(!unwatch_hits(None, None) && !unwatch_hits(None, Some(1)));
    }

    #[test]
    fn v1_no_file_only_when_no_candidate_exists() {
        // 윈 status_reason 은 모르는 오류도 no_file — 후보가 있는데 못 열었으면 open_failed(화면이 있던 파일을 0 에서 다시 읽지 않게)
        let d = tmp("why");
        let a = d.join("a.jsonl");
        let b = d.join("b.jsonl");
        assert_eq!(refine_open_why("no_file", &[a.clone(), b.clone()]), "no_file");
        std::fs::write(&b, L1).unwrap();
        assert_eq!(refine_open_why("no_file", &[a.clone(), b.clone()]), "open_failed");
        assert_eq!(refine_open_why("symlinked_path", &[a, b]), "symlinked_path", "다른 사유는 그대로");
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn chat_compat_env_only_exact_1() {
        assert!(compat_env_on(Some("1")));
        for v in [None, Some(""), Some("0"), Some("true"), Some(" 1"), Some("1 "), Some("yes")] {
            assert!(!compat_env_on(v), "{v:?}");
        }
        assert_eq!(CHAT_COMPAT_ENV, "CYS_CHAT_COMPAT_1118");
    }
}
