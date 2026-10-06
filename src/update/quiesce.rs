//! 정비 모드 — 세대 토큰 · S5 재검사 · 보류 재생 원장(설계 AUTO-UPDATE-118 §3-3 · 1R BLOCK 5 · 2R 신규 BLOCK 6 · 3R 신규 BLOCK 1).
//! 데몬 쪽 RPC(`update.quiesce`·`update.release`·`update.seat_token`)와 배달 훅은 cysd `update_hold` 가 이 순수 함수·파일 계약을 쓴다.
//!
//! ★재생 원자성(설계와 다른 꼴 · 같은 보장 — HANDOFF-U2 §2): 설계는 `queue-state.json` 머리 칸 `hold_ingested` 를 큐와 같은 rename 에
//! 싣자고 했으나, 그 파일은 **JSON 배열**이고 옛 데몬(롤백 대상)이 배열로 읽는다(형식 변경 = 롤백 판독 불능). 그래서:
//! - ① 로그 → 큐(정확히 한 번): 큐 항목 id = `hold:<txn>:<seq>` · 넣기 전에 **이미 큐에 있는 id** 와 **재생 원장에 있는 id** 를 뺀다.
//!   재생 원장(`hold-delivery.jsonl` · append + fsync)은 주입 **전에** `delivering` 을 적으므로, 큐에서 사라진 항목(배달됨)도 원장에
//!   남는다 → 「큐 쓰기와 upto 기록 사이에 죽음」·「배달 뒤 upto 미기록」 어느 쪽이든 다시 넣는 일 0. `hold-ingested.json`(upto)은
//!   읽기 범위를 줄이는 최적화일 뿐 정확성 근거가 아니다.
//! - ② 큐 → 좌석(최대 한 번): 주입 직전 원장 `delivering` → 주입 → `delivered`(인계 실패 = `aborted` · 다음 틱 재시도 허용).
//!   재기동 뒤 `delivering` 만 남은 id = 자동 재주입 0 · 보낸 쪽에 「배달 확인 필요」 1건.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};
use std::io::Write;
use std::path::Path;

pub const LEDGER_FILE: &str = "hold-delivery.jsonl";
/// 보류 로그 쪽 커서 `{delivered_hold_seq}` — 큐 커밋을 **다시 읽어 확인한 뒤에만** 전진(설계 §3-3 ① · `--check` N3 이 같은 파일을 읽는다).
pub const INGESTED_FILE: &str = "hold-cursor.json";

pub fn read_cursor(dir: &Path) -> Option<u64> {
    read_json::<serde_json::Value>(dir, INGESTED_FILE).and_then(|v| v.get("delivered_hold_seq").and_then(|x| x.as_u64()))
}

pub fn write_cursor(dir: &Path, n: u64) -> Result<(), String> {
    write_json(dir, INGESTED_FILE, &serde_json::json!({"delivered_hold_seq": n}))
}
pub const SESSION_FILE: &str = "hold-session.json";
/// 기본 TTL(설계 `ttl_secs: 900`).
pub const DEFAULT_TTL_SECS: u64 = 900;
pub const ORIGIN: &str = "update_hold";

/// 좌석 하나의 관측(세대 토큰 칸).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SeatTok {
    pub surface_id: u64,
    pub role: Option<String>,
    pub output_gen: u64,
    /// 마지막 사람 입력의 데몬 단조 시각(ms · 데몬 시작 기준) — None = 사람 입력 없음.
    pub human_input_mono_ms: Option<u64>,
    pub pending_input_bytes: u64,
    pub queue_len: u64,
    /// 자기신고 working 이면 true · 판정 불가 = None.
    pub working: Option<bool>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Token {
    pub txn_id: String,
    pub gen: u64,
    pub hold_seq: u64,
    pub seats: Vec<SeatTok>,
}

/// S5 재검사(순수): `t1` = drain 뒤 찍은 토큰 · `t2` = 정착 창 뒤 다시 찍은 토큰. 사유가 하나라도 있으면 보류(unknown = 보류 · fail-closed).
pub fn recheck_diff(t1: &Token, t2: &Token) -> Vec<String> {
    let mut why = Vec::new();
    if t1.txn_id != t2.txn_id || t1.gen != t2.gen {
        why.push("정비 모드 세대 바뀜".to_string());
    }
    let a: BTreeMap<u64, &SeatTok> = t1.seats.iter().map(|s| (s.surface_id, s)).collect();
    let b: BTreeMap<u64, &SeatTok> = t2.seats.iter().map(|s| (s.surface_id, s)).collect();
    if a.keys().ne(b.keys()) {
        why.push("좌석 집합 바뀜".to_string());
    }
    for (id, x) in &a {
        let Some(y) = b.get(id) else { continue };
        if y.human_input_mono_ms != x.human_input_mono_ms {
            why.push(format!("좌석 {id} 사람 입력"));
        }
        if y.output_gen != x.output_gen && !super::mutant("U2-S5OUT") {
            why.push(format!("좌석 {id} 새 출력"));
        }
        if y.queue_len > x.queue_len {
            why.push(format!("좌석 {id} 큐 증가"));
        }
        if y.pending_input_bytes > 0 {
            why.push(format!("좌석 {id} 미제출 입력"));
        }
        match y.working {
            Some(false) => {}
            Some(true) => why.push(format!("좌석 {id} working")),
            None => why.push(format!("좌석 {id} 판정 불가")),
        }
    }
    if t2.hold_seq > t1.hold_seq {
        why.push("보류 로그 증가".to_string());
    }
    why
}

/// 데몬이 RPC 토큰을 받아들이는 조건: 소유자 기록 `txn_id`·`epoch` 일치 · 묘비 아님 · 잠금이 실제로 잡혀 있음.
pub fn verify_owner_token(dir: &Path, token: &str) -> Result<super::lock::Token, String> {
    let t = super::lock::Token::parse(token).ok_or("토큰 형식")?;
    let o = super::lock::read_owner(dir).ok_or("소유자 기록 없음")?;
    if o.txn_id != t.txn_id || o.epoch != t.epoch || o.released {
        return Err("토큰 불일치·해제됨".into());
    }
    if super::lock::is_held(dir) != Some(true) && !super::mutant("U2-TOK") {
        return Err("잠금 없음".into());
    }
    Ok(t)
}

// ── 재생 원장 ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Mark {
    Ingested,
    Delivering,
    Delivered,
    Aborted,
    /// 재기동 뒤 `delivering` 만 남음 → 재주입 0 · 보낸 쪽 통지 끝.
    Unconfirmed,
    /// 대상 좌석 없음 등 — 배달하지 않고 통지.
    Undeliverable,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LedgerRow {
    pub id: String,
    pub mark: Mark,
    pub at: i64,
}

/// 원장 1줄 append + fsync(주입 전 `delivering` 은 이 함수가 Ok 를 돌려준 뒤에만 주입한다).
pub fn ledger_append(dir: &Path, id: &str, mark: Mark) -> Result<(), String> {
    super::ensure_private_dir(dir)?;
    let row = LedgerRow { id: id.to_string(), mark, at: super::clock::now_stamp().wall };
    let mut line = serde_json::to_vec(&row).map_err(|e| e.to_string())?;
    line.push(b'\n');
    let mut o = std::fs::OpenOptions::new();
    o.create(true).append(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        o.mode(0o600);
    }
    let mut f = o.open(dir.join(LEDGER_FILE)).map_err(|e| e.to_string())?;
    f.write_all(&line).map_err(|e| e.to_string())?;
    f.sync_data().map_err(|e| format!("fsync: {e}"))
}

/// id → 마지막 표지. 개행 없는 꼬리(쓰다 끊김)는 무시한다(그 표지는 Ok 를 돌려준 적이 없다).
pub fn ledger_marks(dir: &Path) -> Result<HashMap<String, Mark>, String> {
    let buf = match std::fs::read(dir.join(LEDGER_FILE)) {
        Ok(b) => b,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(HashMap::new()),
        Err(e) => return Err(e.to_string()),
    };
    let keep = buf.iter().rposition(|&b| b == b'\n').map(|i| i + 1).unwrap_or(0);
    let mut m = HashMap::new();
    for line in buf[..keep].split(|&b| b == b'\n').filter(|l| !l.is_empty()) {
        let r: LedgerRow = serde_json::from_slice(line).map_err(|e| format!("재생 원장 손상: {e}"))?;
        m.insert(r.id, r.mark);
    }
    Ok(m)
}

/// 주입 직전 판정(순수): 원장 표지가 없거나 `ingested`·`aborted` 면 주입 가능 · `delivering`·`delivered`·`unconfirmed`·`undeliverable`
/// = 주입 금지(큐에서 빼고 필요하면 통지).
pub fn may_inject(mark: Option<Mark>) -> bool {
    matches!(mark, None | Some(Mark::Ingested) | Some(Mark::Aborted)) || super::mutant("U2-ATMOST")
}

/// 재생 ① 계획(순수): `records` 중 `upto` 보다 크고 · 큐에 없고 · 원장에 없는 줄.
pub fn plan_replay<'a>(
    txn_id: &str,
    records: &'a [super::hold::HoldRecord],
    upto: u64,
    in_queue: &std::collections::HashSet<String>,
    marks: &HashMap<String, Mark>,
) -> Vec<&'a super::hold::HoldRecord> {
    let (cands, _) = super::hold::plan_ingest(txn_id, records, upto, in_queue);
    cands.into_iter().filter(|r| super::mutant("U2-REPLAY") || !marks.contains_key(&super::hold::queue_item_id(txn_id, r.hold_seq))).collect()
}

/// 정비 세션 기록(보류 로그 줄이 어느 트랜잭션 것인지 — 큐 id 의 `txn` 칸).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Session {
    pub txn_id: String,
    pub gen: u64,
    /// 이 세션이 시작될 때의 보류 로그 마지막 seq(이 세션의 줄 = 그보다 큰 것).
    pub from_hold_seq: u64,
}

pub fn write_json(dir: &Path, name: &str, v: &impl Serialize) -> Result<(), String> {
    super::ensure_private_dir(dir)?;
    let b = serde_json::to_vec_pretty(v).map_err(|e| e.to_string())?;
    super::journal::durable_write(&dir.join(name), &b)
}

pub fn read_json<T: for<'de> Deserialize<'de>>(dir: &Path, name: &str) -> Option<T> {
    serde_json::from_slice(&std::fs::read(dir.join(name)).ok()?).ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::update::hold::{queue_item_id, HoldLog};
    use std::collections::HashSet;

    fn seat(id: u64) -> SeatTok {
        SeatTok { surface_id: id, role: Some(format!("w{id}")), output_gen: 10, human_input_mono_ms: Some(5), pending_input_bytes: 0, queue_len: 0, working: Some(false) }
    }
    fn tok(seats: Vec<SeatTok>) -> Token {
        Token { txn_id: "t".into(), gen: 1, hold_seq: 0, seats }
    }

    /// §7-1 「정비 모드: 토큰 뒤 사람 입력·새 출력·큐 → S5 보류」 + unknown = 보류.
    #[test]
    fn s5_recheck_flags_each_change_and_unknown() {
        let t1 = tok(vec![seat(1), seat(2)]);
        assert!(recheck_diff(&t1, &t1.clone()).is_empty());
        let cases: Vec<(&str, Box<dyn Fn(&mut Token)>)> = vec![
            ("사람 입력", Box::new(|t: &mut Token| t.seats[0].human_input_mono_ms = Some(99))),
            ("새 출력", Box::new(|t: &mut Token| t.seats[0].output_gen = 11)),
            ("큐 증가", Box::new(|t: &mut Token| t.seats[1].queue_len = 1)),
            ("미제출", Box::new(|t: &mut Token| t.seats[1].pending_input_bytes = 3)),
            ("working", Box::new(|t: &mut Token| t.seats[1].working = Some(true))),
            ("판정 불가", Box::new(|t: &mut Token| t.seats[1].working = None)),
            ("좌석 집합", Box::new(|t: &mut Token| t.seats.push(seat(3)))),
            ("세대", Box::new(|t: &mut Token| t.gen = 2)),
            ("보류 로그", Box::new(|t: &mut Token| t.hold_seq = 1)),
        ];
        for (want, f) in cases {
            let mut t2 = t1.clone();
            f(&mut t2);
            let w = recheck_diff(&t1, &t2);
            assert!(w.iter().any(|x| x.contains(want)), "{want}: {w:?}");
        }
    }

    /// ★B8 crash 행렬(U1 이관): 보류 로그(ACK 뒤 내구) → 재생 ① 의 각 지점에서 죽어도 같은 줄이 두 번 큐에 들어가지 않고 사라지지도
    /// 않는다. 지점 = ⓐ 큐 쓰기 전 ⓑ 큐 쓰기 뒤·upto 전 ⓒ 주입 직전 `delivering` 뒤 ⓓ 주입 뒤·`delivered` 전 ⓔ 정상.
    #[test]
    fn b8_crash_matrix_replay_exactly_once_and_inject_at_most_once() {
        let base = std::env::temp_dir().join(format!("cys-u2-b8-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        for point in ["a", "b", "c", "d", "e"] {
            let d = base.join(point);
            let mut h = HoldLog::open(&d).unwrap();
            for i in 0..3 {
                let ack = h.append("w1", "send", &format!("m{i}"), 1).unwrap();
                // ACK 재독: ACK 받은 줄은 다시 열어도 있다
                assert_eq!(HoldLog::open(&d).unwrap().records_after(ack.hold_seq - 1).unwrap()[0].hold_seq, ack.hold_seq);
            }
            let recs = h.records_after(0).unwrap();
            let txn = "0123456789abcdef0123456789abcdef";
            // 「데몬」 = 큐(id 집합) + 주입 기록. 1회차.
            let mut queue: HashSet<String> = HashSet::new();
            let mut injected: Vec<String> = Vec::new();
            let marks = ledger_marks(&d).unwrap();
            let plan: Vec<String> = plan_replay(txn, &recs, 0, &queue, &marks).iter().map(|r| queue_item_id(txn, r.hold_seq)).collect();
            assert_eq!(plan.len(), 3);
            if point != "a" {
                queue.extend(plan.iter().cloned()); // 큐 원자 쓰기 성공
            }
            if point == "e" || point == "c" || point == "d" {
                write_cursor(&d, 3).unwrap();
            }
            // 첫 항목 주입 시도
            let first = plan[0].clone();
            if matches!(point, "c" | "d" | "e") {
                assert!(may_inject(ledger_marks(&d).unwrap().get(&first).copied()));
                ledger_append(&d, &first, Mark::Delivering).unwrap();
                if point != "c" {
                    injected.push(first.clone());
                }
                if point == "e" {
                    ledger_append(&d, &first, Mark::Delivered).unwrap();
                    queue.remove(&first);
                }
            }
            // ── 죽음 → 재기동: 큐 파일(queue)은 남고, 원장·로그는 디스크에서 다시 읽는다 ──
            let marks = ledger_marks(&d).unwrap();
            let upto: u64 = read_cursor(&d).unwrap_or(0);
            let again: Vec<String> = plan_replay(txn, &recs, upto, &queue, &marks).iter().map(|r| queue_item_id(txn, r.hold_seq)).collect();
            queue.extend(again.iter().cloned());
            // 정확히 한 번: 3줄 전부가 「큐에 있음 ∪ 원장 표지」 에 정확히 한 번
            for r in &recs {
                let id = queue_item_id(txn, r.hold_seq);
                let present = queue.contains(&id) || marks.contains_key(&id);
                assert!(present, "{point}: {id} 사라짐");
            }
            // 재기동 뒤 주입 판정: delivering 만 남은 항목은 재주입 0(최대 한 번)
            for id in queue.clone() {
                if may_inject(marks.get(&id).copied()) {
                    injected.push(id.clone());
                }
            }
            let mut seen = HashSet::new();
            for i in &injected {
                assert!(seen.insert(i.clone()), "{point}: {i} 두 번 주입");
            }
            if point == "a" || point == "b" {
                assert_eq!(injected.len(), 3, "{point}: 전부 한 번씩");
            }
            if point == "c" {
                assert_eq!(injected.len(), 2, "c: delivering 만 남은 1건은 재주입 안 함(통지 대상)");
            }
        }
    }

    #[test]
    fn owner_token_must_match_and_lock_must_be_held() {
        let d = std::env::temp_dir().join(format!("cys-u2-qtok-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        let g = crate::update::lock::acquire(&d, "runner").unwrap();
        let t = g.token().render();
        assert!(verify_owner_token(&d, &t).is_ok());
        let mut bad = crate::update::lock::Token::parse(&t).unwrap();
        bad.epoch += 1;
        assert!(verify_owner_token(&d, &bad.render()).is_err());
        drop(g);
        assert!(verify_owner_token(&d, &t).is_err(), "해제 뒤 = 거부");
    }

    #[test]
    fn ledger_ignores_torn_tail() {
        let d = std::env::temp_dir().join(format!("cys-u2-ledger-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        ledger_append(&d, "hold:x:1", Mark::Delivering).unwrap();
        let mut f = std::fs::OpenOptions::new().append(true).open(d.join(LEDGER_FILE)).unwrap();
        f.write_all(br#"{"id":"hold:x:1","mark":"deliv"#).unwrap();
        assert_eq!(ledger_marks(&d).unwrap().get("hold:x:1"), Some(&Mark::Delivering));
        assert!(!may_inject(Some(Mark::Delivering)) && may_inject(Some(Mark::Aborted)) && may_inject(None));
    }
}
