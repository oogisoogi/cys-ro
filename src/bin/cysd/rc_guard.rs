//! ★D25(1.1.8 · BACKLOG D25 · master 결정 [master#7f82e8c4] ① · [master#99924a73]) **기동 뒤 RC 감시** — 좌석의 claude
//! 대화 기록(jsonl)에 `remote_session_change` 가 `url` 을 달고 나타나면(= Remote Control 켜짐) 그 좌석이 RC 허용 역할
//! (`cys::rc_allowed_for` — 기동 인자와 같은 술어)이 아닐 때 끈다.
//!
//! 1차 방어는 기동 인자다(`--settings` 의 `disableRemoteControl:true` · cys.rs `apply_seat_settings_arg`). 이 감시는
//! 그 인자가 붙지 않은 좌석(사용자 cmd 에 자기 `--settings` 가 있는 경우 · 1.1.8 이전에 뜬 좌석)을 위한 2차 그물이다.
//!
//! 끄는 법 = 좌석 큐로 `/remote-control` 을 넣고(조용한 때 배달 · 타이핑 가드 규약 그대로), 메뉴가 뜨면
//! **「Disconnect this session」 줄이 선택돼 있을 때만** Return · 다른 줄이 선택돼 있으면 Esc 로 메뉴만 닫는다(키를
//! 추측해 옮기지 않는다 — 메뉴 순서는 claude 판마다 다를 수 있다). 어느 쪽이든 결과를 이벤트로 남기고, 끄기를 확인하지
//! 못하면 feed 경고가 오퍼레이터에게 남는다. ⚠`/remote-control` 은 꺼진 좌석에선 **켜는** 명령이다 → 넣기 직전에
//! 「마지막 기록 = 켜짐」 을 다시 대조하지 않으면 안 되므로, 감시는 마지막 기록이 켜짐일 때만 1회 발화한다(좌석당
//! 진행 중 표시 · 꺼짐 기록이 오면 해제).
use std::collections::HashSet;
use std::sync::atomic::Ordering;
use std::sync::{Arc, Mutex, OnceLock};

use serde_json::{json, Value};

use crate::state::{Daemon, Surface};

/// jsonl 한 줄 → RC 상태(순수). `None` = 이 줄은 RC 기록이 아님 · `Some(None)` = 꺼짐(url null) · `Some(Some(url))` = 켜짐.
pub(crate) fn parse_remote_session_url(line: &str) -> Option<Option<String>> {
    if !line.contains("remote_session_change") {
        return None;
    }
    let v: Value = serde_json::from_str(line).ok()?;
    let a = v.get("attachment")?;
    if a.get("type")?.as_str()? != "remote_session_change" {
        return None;
    }
    Some(a.get("url").and_then(|u| u.as_str()).filter(|u| !u.is_empty()).map(String::from))
}

/// 새 줄 묶음의 마지막 RC 상태(순수) — 마지막 기록이 이긴다.
pub(crate) fn last_rc_state(lines: &[String]) -> Option<Option<String>> {
    lines.iter().rev().find_map(|l| parse_remote_session_url(l))
}

#[derive(Debug, PartialEq, Eq)]
pub(crate) enum RcAction {
    /// 할 일 없음(허용 역할 · RC 기록 없음 · 이미 진행 중 · 꺼짐인데 진행 중 아님)
    None,
    /// 비허용 좌석이 켜짐 → 끄기 시작
    Disconnect,
    /// 진행 중이던 좌석이 꺼짐으로 확인됨
    Confirmed,
}

/// 감시 결정(순수).
pub(crate) fn rc_action(allowed: bool, in_flight: bool, state: Option<&Option<String>>) -> RcAction {
    match (allowed, state) {
        (true, _) | (_, None) => RcAction::None,
        (false, Some(Some(_))) if !in_flight => RcAction::Disconnect,
        (false, Some(None)) if in_flight => RcAction::Confirmed,
        _ => RcAction::None,
    }
}

/// `/remote-control` 메뉴 화면 → 넣을 키(순수). 「Disconnect this session」 줄이 없으면 `None`(아직 안 뜸).
/// 그 줄에 준비 마커(`❯`)가 그 글 앞에 있으면 Return, 아니면 Esc(메뉴만 닫음).
pub(crate) fn rc_menu_key(rows: &[String], marker: &str) -> Option<&'static [u8]> {
    let row = rows.iter().find(|r| r.contains("Disconnect this session"))?;
    let at = row.find("Disconnect this session")?;
    if !marker.is_empty() && row[..at].contains(marker) {
        Some(b"\r")
    } else {
        Some(b"\x1b")
    }
}

fn in_flight() -> &'static Mutex<HashSet<u64>> {
    static S: OnceLock<Mutex<HashSet<u64>>> = OnceLock::new();
    S.get_or_init(Default::default)
}

/// usage 수집기가 좌석 jsonl 새 줄을 읽을 때마다 부른다(claude 좌석만).
pub(crate) fn observe_lines(daemon: &Arc<Daemon>, s: &Arc<Surface>, lines: &[String]) {
    let Some(state) = last_rc_state(lines) else {
        return;
    };
    let role = s.role.lock().unwrap().clone().unwrap_or_default();
    let allowed = cys::rc_allowed_for(&role, cys::is_dept_socket(&daemon.socket_path), &cys::rc_allowed_roles());
    let flying = in_flight().lock().unwrap_or_else(|e| e.into_inner()).contains(&s.id);
    let surface_ref = cys::surface_ref(s.id);
    match rc_action(allowed, flying, Some(&state)) {
        RcAction::None => {}
        RcAction::Confirmed => {
            in_flight().lock().unwrap_or_else(|e| e.into_inner()).remove(&s.id);
            daemon.bus.publish("seat.rc_off_confirmed", "governance", Some(s.id), json!({"surface_ref": surface_ref, "role": role}));
        }
        RcAction::Disconnect => {
            in_flight().lock().unwrap_or_else(|e| e.into_inner()).insert(s.id);
            // URL 은 싣지 않는다(세션 접속 주소 = 노출 정보 · 존재 사실만).
            daemon.bus.publish(
                "seat.rc_unexpected_on",
                "governance",
                Some(s.id),
                json!({"surface_ref": surface_ref, "role": role, "url_present": true}),
            );
            daemon.push_feed_notification(
                "warn",
                &format!("Remote Control 켜짐 감지 — 허용 역할 아님 ({surface_ref} · {role})"),
                "폰 노출은 RC 허용 역할(정책 rc_allowed_roles · 기본 master)만이다. 데몬이 /remote-control 로 끄기를 시도한다 — \
                 결과는 이벤트 seat.rc_disconnect_attempt · 끄기 확인 = seat.rc_off_confirmed. 확인이 안 오면 그 좌석에서 \
                 /remote-control → Disconnect this session 을 직접 고르라.",
                Some(s.id),
            );
            let (d, seat) = (daemon.clone(), s.clone());
            std::thread::spawn(move || disconnect(&d, &seat));
        }
    }
}

/// 끄기 시도 — 좌석 큐에 `/remote-control` → 메뉴가 뜨면 [`rc_menu_key`]. 최대 90초 관측.
fn disconnect(daemon: &Arc<Daemon>, s: &Arc<Surface>) {
    let entry = daemon.next_queue_entry("/remote-control".to_string(), None, "rc-guard");
    let depth = {
        let mut q = s.pending_queue.lock().unwrap();
        q.push_back(entry.clone());
        q.len()
    };
    daemon.bus.publish("queue.enqueued", "queue", Some(s.id), crate::state::queue_enqueued_payload(&entry, depth, json!("rc-guard"), None));
    daemon.persist_queue_state();
    let marker = "❯";
    let mut outcome = "menu_not_seen";
    for _ in 0..180 {
        std::thread::sleep(std::time::Duration::from_millis(500));
        if s.exited.load(Ordering::Relaxed) {
            outcome = "seat_exited";
            break;
        }
        let rows: Vec<String> = {
            let p = s.parser.lock().unwrap_or_else(|e| e.into_inner());
            let screen = p.screen();
            let (_, cols) = screen.size();
            screen.rows(0, cols).collect()
        };
        if let Some(key) = rc_menu_key(&rows, marker) {
            let _ = s.write_tx.send(crate::state::WriteReq::Data(key.to_vec()));
            outcome = if key == b"\r" { "disconnect_selected_return" } else { "menu_closed_not_selected" };
            break;
        }
    }
    daemon.bus.publish(
        "seat.rc_disconnect_attempt",
        "governance",
        Some(s.id),
        json!({"surface_ref": cys::surface_ref(s.id), "outcome": outcome}),
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    const ON: &str = r#"{"parentUuid":"x","isSidechain":false,"attachment":{"type":"remote_session_change","url":"https://claude.ai/code/session_abc","commit":"c"},"type":"attachment"}"#;
    const OFF: &str = r#"{"parentUuid":"x","isSidechain":false,"attachment":{"type":"remote_session_change","url":null,"commit":"c"},"type":"attachment"}"#;

    #[test]
    fn d25_parse_remote_session_url_shapes() {
        assert_eq!(parse_remote_session_url(ON), Some(Some("https://claude.ai/code/session_abc".into())));
        assert_eq!(parse_remote_session_url(OFF), Some(None), "실 기록 모양(url null) = 꺼짐");
        assert_eq!(parse_remote_session_url(r#"{"type":"user","message":"remote_session_change 라는 낱말"}"#), None, "본문 낱말 ≠ 기록");
        assert_eq!(parse_remote_session_url("not json remote_session_change"), None);
        let lines = vec![ON.to_string(), OFF.to_string()];
        assert_eq!(last_rc_state(&lines), Some(None), "마지막 기록이 이긴다");
        assert_eq!(last_rc_state(&[OFF.to_string(), ON.to_string()]), Some(Some("https://claude.ai/code/session_abc".into())));
        assert_eq!(last_rc_state(&["{}".to_string()]), None);
    }

    #[test]
    fn d25_rc_action_table() {
        let on = Some(Some("u".to_string()));
        let off: Option<Option<String>> = Some(None);
        assert_eq!(rc_action(false, false, on.as_ref()), RcAction::Disconnect, "비허용 + 켜짐 = 끄기");
        assert_eq!(rc_action(false, true, on.as_ref()), RcAction::None, "이미 진행 중 = 재발화 0");
        assert_eq!(rc_action(true, false, on.as_ref()), RcAction::None, "허용 역할(master·relay) = 통과");
        assert_eq!(rc_action(false, true, off.as_ref()), RcAction::Confirmed);
        assert_eq!(rc_action(false, false, off.as_ref()), RcAction::None);
        assert_eq!(rc_action(false, false, None), RcAction::None);
    }

    #[test]
    fn d25_rc_menu_key_only_returns_when_disconnect_selected() {
        let rows = |t: &str| -> Vec<String> { t.lines().map(str::to_string).collect() };
        assert_eq!(rc_menu_key(&rows("Remote Control\n❯ Disconnect this session\n  Show QR code"), "❯"), Some(&b"\r"[..]));
        assert_eq!(rc_menu_key(&rows("Remote Control\n  Disconnect this session\n❯ Show QR code"), "❯"), Some(&b"\x1b"[..]), "다른 줄 선택 = Esc");
        assert_eq!(rc_menu_key(&rows("❯ "), "❯"), None, "메뉴 아직 안 뜸");
        assert_eq!(rc_menu_key(&rows("Disconnect this session ❯"), "❯"), Some(&b"\x1b"[..]), "마커가 글 뒤 = 선택 아님");
    }
}
