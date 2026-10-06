//! 「하지 않는 조건」 판정(정책 §2 의 기계판) — 설계 AUTO-UPDATE-118 §3-4 게이트 N1~N14 · 1R BLOCK 15 · 📌14′·16.
//!
//! 순수 함수: 사실([`Facts`])은 호출부(`cys self-update --check`)가 모아 넘긴다. **모르는 사실(None) = 걸림(보류)**
//! — fail-closed. 판정 순서 = 싼 것 먼저(설계 고정 · 1R MINOR: `state_migration:"breaking"` 제외는 게이트가 아니라 피드
//! 판정 ⓛ 로 옮겼다 — 이 배열은 정본 순서 그대로): N9 → N10 → N8 → N11 → N13 → N14 → N6 → N12 →
//! N5 → N4 → N3 → N1 → N2 → N7. 첫 보류가 `last_defer` 사유이고, 표시를 위해 나머지도 끝까지 평가해 둔다.
//! 보류는 오류가 아니다(신호 없음 · daily 우편) — 예외 신호 3종: N12 `win_sac_on` · N13 `clock_suspect` ·
//! N14 `recover_agent_missing`.

use super::errors::ErrCode;
use serde::Serialize;

/// N1 — 마지막 출력 뒤 최소 경과.
pub const N1_QUIET_SECS: u64 = 10 * 60;
/// N2 — 사람 입력 뒤 최소 경과(좌석·OS 둘 다).
pub const N2_HUMAN_IDLE_SECS: u64 = 20 * 60;
/// N6 — 어댑터 없이 허용하는 배터리 하한.
pub const N6_BATTERY_MIN_PCT: u8 = 50;
/// N8 — 직전 갱신 뒤 최소 경과.
pub const N8_RECENT_SECS: u64 = 72 * 3600;

/// 좌석 1개의 사실(N1·N2·N3).
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct SeatFact {
    pub surface_id: u64,
    /// 재주입 3신호 ⓐ — 데몬 `derive_node_state == idle`.
    pub idle: bool,
    /// 재주입 3신호 ⓑ — 자기신고 ≠ working(미보고 = false · 보수).
    pub self_not_working: bool,
    /// 재주입 3신호 ⓒ — 어댑터 프롬프트 대기 화면.
    pub prompt_ready: bool,
    /// 마지막 출력 뒤 경과(초).
    pub quiet_secs: u64,
    /// 마지막 사람 입력 뒤 경과(초) · 사람 입력 0 = None(= 충분히 오래).
    pub human_idle_secs: Option<u64>,
    pub pending_input_bytes: u64,
    pub queue_depth: u64,
}

/// 전원(N6).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Power {
    pub adapter: bool,
    pub battery_pct: Option<u8>,
}

/// 게이트 입력 — `None` = 모름(= 보류).
#[derive(Debug, Clone, Default, Serialize)]
pub struct Facts {
    /// N9 — `update.auto` 설정(기본 ON) · 봉투 `halt`.
    pub auto_enabled: Option<bool>,
    pub envelope_halt: bool,
    /// N10 — 다른 트랜잭션·미완 복원(부서 rotate · `.pending-restore` · 갱신 저널 비종결 · 팩 저널 잔여).
    pub other_txn: Option<bool>,
    /// N8 — 직전 갱신 뒤 경과(초 · 갱신 이력 없음 = `u64::MAX`) · 이 릴리스의 실패 기록이 지금 막는가.
    pub since_last_update_secs: Option<u64>,
    pub failure_blocks: Option<bool>,
    /// N11 — 설치 `release_seq` · 릴리스 `min_from_release_seq`.
    pub installed_release_seq: Option<u64>,
    pub min_from_release_seq: Option<u64>,
    /// N13 — 시계 의심.
    pub clock_suspect: Option<bool>,
    /// N14 — 복구기 등록·검증 통과.
    pub recover_agent_ok: Option<bool>,
    /// N6.
    pub power: Option<Power>,
    /// N12 — 윈 스마트 앱 컨트롤 `"on"|"eval"|"off"` · 윈이 아니면 `Some("n/a")` · 레지스트리 값 없음(윈10 등) = `Some("absent")`.
    pub sac_state: Option<String>,
    /// N5 ⓐ 보류 신고가 지금을 덮음 · ⓑ 응답 대기 승인 요청 수 · ⓒ `publish` 잡 48시간 안.
    pub holds_active: Option<bool>,
    pub pending_approvals: Option<u64>,
    pub publish_within_48h: Option<bool>,
    /// N4 — `bulk` 잡 48시간 안 · 비대량 잡 60분 안.
    pub bulk_within_48h: Option<bool>,
    pub nonbulk_within_60m: Option<bool>,
    /// N3 — 보류 로그 미배달 수(좌석 큐는 `seats[].queue_depth`).
    pub hold_log_undelivered: Option<u64>,
    /// N1·N2·N3 — 좌석 사실(데몬 관측 · 판독 불가 = None).
    pub seats: Option<Vec<SeatFact>>,
    /// N2 — OS 입력 유휴(초).
    pub os_idle_secs: Option<u64>,
    /// N7 — 롤백 자산을 만들 수 있는가(공간 · 윈 설치판 본문·설치기).
    pub rollback_assets_ok: Option<bool>,
}

/// 게이트 1칸의 결과.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Check {
    pub id: &'static str,
    /// 걸렸다(= 보류).
    pub hold: bool,
    /// 사실을 몰라서 걸렸다.
    pub unknown: bool,
    pub reason: String,
    /// 보류와 함께 낼 신호(N12·N13·N14 만).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub signal: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Report {
    /// 전부 통과.
    pub pass: bool,
    /// 첫 보류(= `state.json.last_defer`).
    pub first_hold: Option<Check>,
    pub checks: Vec<Check>,
}

/// 판정 순서(설계 §3-4 고정) — 시험이 이 배열을 설계 문자열과 대조한다.
pub const ORDER: [&str; 14] = ["N9", "N10", "N8", "N11", "N13", "N14", "N6", "N12", "N5", "N4", "N3", "N1", "N2", "N7"];

fn chk(id: &'static str, v: Option<Result<(), String>>) -> Check {
    match v {
        None => Check { id, hold: true, unknown: true, reason: "판정 불가(사실 없음)".into(), signal: None },
        Some(Ok(())) => Check { id, hold: false, unknown: false, reason: String::new(), signal: None },
        Some(Err(r)) => Check { id, hold: true, unknown: false, reason: r, signal: None },
    }
}

fn with_signal(mut c: Check, code: ErrCode) -> Check {
    if c.hold {
        c.signal = Some(code.as_str());
    }
    c
}

fn bool_gate(v: Option<bool>, msg: &str) -> Option<Result<(), String>> {
    v.map(|b| if b { Err(msg.to_string()) } else { Ok(()) })
}

/// 게이트 1칸 평가.
fn eval_one(id: &str, f: &Facts) -> Check {
    match id {
        "N9" => chk("N9", f.auto_enabled.map(|on| {
            if !on {
                Err("사용자가 자동 갱신을 껐다".into())
            } else if f.envelope_halt {
                Err("봉투 halt(비상 정지)".into())
            } else {
                Ok(())
            }
        })),
        "N10" => chk("N10", bool_gate(f.other_txn, "다른 트랜잭션 진행·직전 복원 미완")),
        "N8" => chk("N8", match (f.since_last_update_secs, f.failure_blocks) {
            (Some(s), Some(fb)) => Some(if s < N8_RECENT_SECS {
                Err(format!("직전 갱신 {}시간 전(<72h)", s / 3600))
            } else if fb {
                Err("이 릴리스 실패 기록(격리·백오프)".into())
            } else {
                Ok(())
            }),
            _ => None,
        }),
        "N11" => chk("N11", match (f.installed_release_seq, f.min_from_release_seq) {
            (Some(i), Some(m)) => Some(if i < m { Err(format!("출발 판 하한 {i} < {m}")) } else { Ok(()) }),
            _ => None,
        }),
        "N13" => with_signal(chk("N13", bool_gate(f.clock_suspect, "시계 의심")), ErrCode::ClockSuspect),
        "N14" => with_signal(
            chk("N14", f.recover_agent_ok.map(|ok| if ok { Ok(()) } else { Err("복구기 미등록·불일치".into()) })),
            ErrCode::RecoverAgentMissing,
        ),
        "N6" => chk("N6", f.power.map(|p| {
            if p.adapter || p.battery_pct.map(|b| b >= N6_BATTERY_MIN_PCT).unwrap_or(false) {
                Ok(())
            } else {
                Err(format!("어댑터 없음 · 배터리 {:?}%", p.battery_pct))
            }
        })),
        "N12" => with_signal(
            // ★1R MAJOR(M2): 통과는 아는 안전 값(off·absent·n/a)뿐 — on/eval·미지 문자열 = 보류.
            chk("N12", f.sac_state.as_deref().map(|s| match s {
                "off" | "absent" | "n/a" => Ok(()),
                other if super::mutant("M2") && other != "on" && other != "eval" => Ok(()),
                other => Err(format!("스마트 앱 컨트롤 {other}")),
            })),
            ErrCode::WinSacOn,
        ),
        "N5" => chk("N5", match (f.holds_active, f.pending_approvals, f.publish_within_48h) {
            (Some(h), Some(p), Some(pb)) => Some(if h {
                Err("보류 신고(holds)가 지금을 덮음".into())
            } else if p > 0 {
                Err(format!("응답 대기 승인 요청 {p}건(외부 발행 대리 신호)"))
            } else if pb {
                Err("publish 잡 48시간 안".into())
            } else {
                Ok(())
            }),
            _ => None,
        }),
        "N4" => chk("N4", match (f.bulk_within_48h, f.nonbulk_within_60m) {
            (Some(b), Some(n)) => Some(if b {
                Err("bulk 잡 48시간 안".into())
            } else if n {
                Err("비대량 잡 60분 안".into())
            } else {
                Ok(())
            }),
            _ => None,
        }),
        "N3" => chk("N3", match (&f.seats, f.hold_log_undelivered) {
            (Some(seats), Some(h)) => {
                let q: u64 = seats.iter().map(|s| s.queue_depth).sum();
                Some(if q > 0 || h > 0 { Err(format!("배송 대기 {q} · 보류 로그 {h}")) } else { Ok(()) })
            }
            _ => None,
        }),
        "N1" => chk("N1", f.seats.as_ref().map(|seats| {
            match seats.iter().find(|s| !(s.idle && s.self_not_working && s.prompt_ready && s.quiet_secs >= N1_QUIET_SECS)) {
                Some(s) => Err(format!("좌석 {} 일하는 중(idle {} · 자기신고 {} · 프롬프트 {} · 침묵 {}s)",
                    s.surface_id, s.idle, s.self_not_working, s.prompt_ready, s.quiet_secs)),
                None => Ok(()),
            }
        })),
        "N2" => chk("N2", match (&f.seats, f.os_idle_secs) {
            (Some(seats), Some(os)) => Some(if os < N2_HUMAN_IDLE_SECS {
                Err(format!("OS 입력 {os}s 전"))
            } else if let Some(s) = seats.iter().find(|s| s.pending_input_bytes > 0) {
                Err(format!("좌석 {} 미제출 입력 {}B", s.surface_id, s.pending_input_bytes))
            } else if let Some(s) = seats.iter().find(|s| s.human_idle_secs.map(|h| h < N2_HUMAN_IDLE_SECS).unwrap_or(false)) {
                Err(format!("좌석 {} 사람 입력 {}s 전", s.surface_id, s.human_idle_secs.unwrap_or(0)))
            } else {
                Ok(())
            }),
            _ => None,
        }),
        "N7" => chk("N7", f.rollback_assets_ok.map(|ok| if ok { Ok(()) } else { Err("롤백 자산 미확보(공간·설치판)".into()) })),
        other => Check { id: "?", hold: true, unknown: true, reason: format!("미지 게이트 {other}"), signal: None },
    }
}

/// 본체 갱신 게이트 전체(순서 고정).
pub fn evaluate(f: &Facts) -> Report {
    evaluate_ids(f, &ORDER)
}

/// 팩 단독 갱신 게이트(§3-8 — N1·N2·N3·N4·N5·N8·N9·N10 · 재시작 없음 = 전원·데몬 정지 무관). 순서는 본체 순서의 부분열.
pub const PACK_ONLY: [&str; 8] = ["N9", "N10", "N8", "N5", "N4", "N3", "N1", "N2"];

pub fn evaluate_pack_only(f: &Facts) -> Report {
    evaluate_ids(f, &PACK_ONLY)
}

fn evaluate_ids(f: &Facts, ids: &[&str]) -> Report {
    let checks: Vec<Check> = ids.iter().map(|id| eval_one(id, f)).collect();
    let first_hold = checks.iter().find(|c| c.hold).cloned();
    Report { pass: first_hold.is_none(), first_hold, checks }
}

#[cfg(test)]
pub(crate) fn all_pass_facts() -> Facts {
    Facts {
        auto_enabled: Some(true),
        envelope_halt: false,
        other_txn: Some(false),
        since_last_update_secs: Some(u64::MAX),
        failure_blocks: Some(false),
        installed_release_seq: Some(9),
        min_from_release_seq: Some(1),
        clock_suspect: Some(false),
        recover_agent_ok: Some(true),
        power: Some(Power { adapter: true, battery_pct: None }),
        sac_state: Some("n/a".into()),
        holds_active: Some(false),
        pending_approvals: Some(0),
        publish_within_48h: Some(false),
        bulk_within_48h: Some(false),
        nonbulk_within_60m: Some(false),
        hold_log_undelivered: Some(0),
        seats: Some(vec![SeatFact {
            surface_id: 1,
            idle: true,
            self_not_working: true,
            prompt_ready: true,
            quiet_secs: 3600,
            human_idle_secs: None,
            pending_input_bytes: 0,
            queue_depth: 0,
        }]),
        os_idle_secs: Some(3600),
        rollback_assets_ok: Some(true),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn order_is_design_fixed() {
        // 설계 §3-4 「판정 순서 = 싼 것 먼저(N9 → N10 → N8 → N11 → N13 → N14 → N6 → N12 → N5 → N4 → N3 → N1 → N2 → N7)」
        let design = "N9 → N10 → N8 → N11 → N13 → N14 → N6 → N12 → N5 → N4 → N3 → N1 → N2 → N7";
        let want: Vec<&str> = design.split('→').map(|s| s.trim()).collect();
        assert_eq!(ORDER.to_vec(), want);
        let r = evaluate(&all_pass_facts());
        assert!(r.pass, "{:?}", r.first_hold);
        assert_eq!(r.checks.iter().map(|c| c.id).collect::<Vec<_>>(), ORDER.to_vec());
    }

    /// 각 칸 참/거짓 — 한 칸만 바꿔 그 칸이 첫 보류가 되는지.
    #[test]
    fn each_gate_true_false() {
        type Mut = fn(&mut Facts);
        let cases: Vec<(&str, Mut)> = vec![
            ("N9", |f| f.auto_enabled = Some(false)),
            ("N9", |f| f.envelope_halt = true),
            ("N10", |f| f.other_txn = Some(true)),
            ("N8", |f| f.since_last_update_secs = Some(N8_RECENT_SECS - 1)),
            ("N8", |f| f.failure_blocks = Some(true)),
            ("N11", |f| f.min_from_release_seq = Some(10)),
            ("N13", |f| f.clock_suspect = Some(true)),
            ("N14", |f| f.recover_agent_ok = Some(false)),
            ("N6", |f| f.power = Some(Power { adapter: false, battery_pct: Some(49) })),
            ("N6", |f| f.power = Some(Power { adapter: false, battery_pct: None })),
            ("N12", |f| f.sac_state = Some("on".into())),
            ("N12", |f| f.sac_state = Some("eval".into())),
            ("N12", |f| f.sac_state = Some("garbage".into())), // 1R M2: 미지 값 = 보류
            ("N5", |f| f.holds_active = Some(true)),
            ("N5", |f| f.pending_approvals = Some(1)),
            ("N5", |f| f.publish_within_48h = Some(true)),
            ("N4", |f| f.bulk_within_48h = Some(true)),
            ("N4", |f| f.nonbulk_within_60m = Some(true)),
            ("N3", |f| f.hold_log_undelivered = Some(1)),
            ("N3", |f| f.seats.as_mut().unwrap()[0].queue_depth = 2),
            ("N1", |f| f.seats.as_mut().unwrap()[0].idle = false),
            ("N1", |f| f.seats.as_mut().unwrap()[0].self_not_working = false),
            ("N1", |f| f.seats.as_mut().unwrap()[0].prompt_ready = false),
            ("N1", |f| f.seats.as_mut().unwrap()[0].quiet_secs = N1_QUIET_SECS - 1),
            ("N2", |f| f.os_idle_secs = Some(N2_HUMAN_IDLE_SECS - 1)),
            ("N2", |f| f.seats.as_mut().unwrap()[0].pending_input_bytes = 3),
            ("N2", |f| f.seats.as_mut().unwrap()[0].human_idle_secs = Some(60)),
            ("N7", |f| f.rollback_assets_ok = Some(false)),
        ];
        for (id, m) in cases {
            let mut f = all_pass_facts();
            m(&mut f);
            let r = evaluate(&f);
            let h = r.first_hold.unwrap_or_else(|| panic!("{id} 가 걸리지 않음"));
            assert_eq!(h.id, id);
            assert!(!h.unknown);
        }
        // 경계: 배터리 정확히 50% = 통과 · 침묵 정확히 10분 = 통과 · 72h 정확히 = 통과 · sac absent/off/n/a = 통과
        let mut f = all_pass_facts();
        f.power = Some(Power { adapter: false, battery_pct: Some(50) });
        f.seats.as_mut().unwrap()[0].quiet_secs = N1_QUIET_SECS;
        f.since_last_update_secs = Some(N8_RECENT_SECS);
        f.os_idle_secs = Some(N2_HUMAN_IDLE_SECS);
        for s in ["off", "absent", "n/a"] {
            f.sac_state = Some(s.into());
            assert!(evaluate(&f).pass, "{s}");
        }
    }

    /// unknown = 보류(fail-closed) — 사실 칸 하나씩 None.
    #[test]
    fn unknown_fact_holds_each_gate() {
        type Mut = fn(&mut Facts);
        let cases: Vec<(&str, Mut)> = vec![
            ("N9", |f| f.auto_enabled = None),
            ("N10", |f| f.other_txn = None),
            ("N8", |f| f.since_last_update_secs = None),
            ("N8", |f| f.failure_blocks = None),
            ("N11", |f| f.installed_release_seq = None),
            ("N13", |f| f.clock_suspect = None),
            ("N14", |f| f.recover_agent_ok = None),
            ("N6", |f| f.power = None),
            ("N12", |f| f.sac_state = None),
            ("N5", |f| f.pending_approvals = None),
            ("N4", |f| f.nonbulk_within_60m = None),
            ("N3", |f| f.hold_log_undelivered = None),
            ("N3", |f| f.seats = None), // 좌석 사실이 없으면 그것을 읽는 첫 칸(N3)부터 걸린다
            ("N2", |f| f.os_idle_secs = None),
            ("N7", |f| f.rollback_assets_ok = None),
        ];
        for (id, m) in cases {
            let mut f = all_pass_facts();
            m(&mut f);
            let h = evaluate(&f).first_hold.unwrap_or_else(|| panic!("{id} unknown 이 통과"));
            assert_eq!((h.id, h.unknown), (id, true), "{id}");
        }
        // 좌석 사실 없음 = N3·N1·N2 셋 다 unknown 보류
        let mut f = all_pass_facts();
        f.seats = None;
        let unk: Vec<&str> = evaluate(&f).checks.iter().filter(|c| c.unknown).map(|c| c.id).collect();
        assert_eq!(unk, vec!["N3", "N1", "N2"]);
    }

    #[test]
    fn first_hold_follows_order_and_signals_only_on_three() {
        let mut f = all_pass_facts();
        f.os_idle_secs = Some(1); // N2
        f.clock_suspect = Some(true); // N13 (앞)
        f.sac_state = Some("on".into()); // N12
        let r = evaluate(&f);
        assert_eq!(r.first_hold.as_ref().unwrap().id, "N13");
        let held: Vec<&str> = r.checks.iter().filter(|c| c.hold).map(|c| c.id).collect();
        assert_eq!(held, vec!["N13", "N12", "N2"]);
        let sig: Vec<(&str, String)> = r.checks.iter().filter_map(|c| c.signal.clone().map(|s| (c.id, s))).collect();
        assert_eq!(sig, vec![("N13", "update.clock_suspect".to_string()), ("N12", "update.win_sac_on".to_string())]);
        let mut f = all_pass_facts();
        f.recover_agent_ok = Some(false);
        assert_eq!(evaluate(&f).first_hold.unwrap().signal.as_deref(), Some("update.recover_agent_missing"));
    }

    #[test]
    fn pack_only_ignores_power_sac_recover_and_n7() {
        let mut f = all_pass_facts();
        f.power = None;
        f.sac_state = Some("on".into());
        f.recover_agent_ok = None;
        f.rollback_assets_ok = None;
        f.clock_suspect = None;
        assert!(evaluate_pack_only(&f).pass);
        f.seats.as_mut().unwrap()[0].idle = false;
        assert_eq!(evaluate_pack_only(&f).first_hold.unwrap().id, "N1");
        assert!(!evaluate(&f).pass);
    }
}
