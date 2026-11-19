//! seat_adopt 순수 판정 시험(T4 · codex T4 1R 처분 포함).
use super::*;

fn rec(pid: u32) -> SeatRecord {
    SeatRecord {
        schema: 1,
        skid: "a-b-0".into(),
        sock: "/x/a-b-0.sock".into(),
        keeper_pid: pid,
        keeper_start_us: Some(1000),
        surface_id: 7,
        display_no: Some(3),
        title: "t".into(),
        role: Some("worker".into()),
        cmd: "sleep 1".into(),
        cwd: "/".into(),
        created_at: 1.0,
        env_injected: true,
        rows: 24,
        cols: 80,
        agent_meta: Some(("claude".into(), "/bin/claude".into())),
        agent_session_id: Some("sid".into()),
        claude_config_dir: None,
        config_dir_trusted: true,
        registered_transcript: None,
        repin_anchor: None,
        agent_epoch: 2,
        conversation_epoch: 5,
        awakened_at: Some(9.0),
        directive_verified: None,
        pack_reinject: None,
        gate_pending: None,
        at: 1.0,
    }
}

#[test]
fn record_roundtrips_through_json_without_token() {
    let r = rec(42);
    let t = serde_json::to_string(&r).unwrap();
    assert!(!t.contains("seat_token"), "좌석 기록에 토큰 칸이 생기면 안 된다(비편입 계약)");
    let back: SeatRecord = serde_json::from_str(&t).unwrap();
    assert_eq!(serde_json::to_value(&back).unwrap(), serde_json::to_value(&r).unwrap());
}

fn j(rec: Option<(u32, Option<u64>, f64)>, reg: &RegRead, alive: bool, start: Option<u64>) -> Liveness {
    judge(&JudgeIn { rec, reg, alive, start_now: start, exe_is_seatkeep: Some(false) })
}

fn jx(rec: Option<(u32, Option<u64>, f64)>, reg: &RegRead, alive: bool, start: Option<u64>, exe: Option<bool>) -> Liveness {
    judge(&JudgeIn { rec, reg, alive, start_now: start, exe_is_seatkeep: exe })
}

#[test]
fn judge_alive_dead_unknown() {
    let ok = |phase: &str| RegRead::Ok(serde_json::json!({"phase": phase, "pid": 42, "start_us": 1000}));
    let r = Some((42u32, Some(1000u64), 1.0));
    assert_eq!(j(r, &ok("committed"), true, Some(1000)), Liveness::Alive);
    assert_eq!(j(r, &ok("exited"), true, Some(1000)), Liveness::Alive, "종료 기록을 쥔 산 seatkeep = 입양해 종료를 받는다");
    assert_eq!(j(r, &ok("committed"), true, Some(1001)), Liveness::Dead("pid_reused"));
    let reg_now = RegRead::Ok(serde_json::json!({"phase": "committed", "pid": 42, "start_us": 1001}));
    assert_eq!(j(r, &reg_now, true, Some(1001)), Liveness::Unknown("record_start_mismatch"), "기록만 어긋나면 산 seatkeep 을 지우지 않는다");
    assert_eq!(j(r, &ok("committed"), false, None), Liveness::Dead("keeper_gone"));
    assert_eq!(j(r, &ok("committed"), true, None), Liveness::Unknown("start_unreadable"));
    assert_eq!(j(r, &ok("prepare"), true, Some(1000)), Liveness::Unknown("preparing"));
    assert_eq!(j(r, &ok("ended_controller_lost"), true, Some(1000)), Liveness::Unknown("ending"));
    let other = RegRead::Ok(serde_json::json!({"phase": "committed", "pid": 43, "start_us": 1000}));
    assert_eq!(j(r, &other, true, Some(1000)), Liveness::Unknown("registry_pid_mismatch"));
}

#[test]
fn registry_missing_or_unreadable_never_kills_a_live_keeper() {
    // codex T4 1R #3: 산 pid 는 등록부가 없거나 못 읽혀도 죽음으로 보지 않는다(파일을 지우지 않음).
    let r = Some((42u32, Some(1000u64), 1.0));
    assert_eq!(j(r, &RegRead::Missing, true, Some(1000)), Liveness::Unknown("registry_missing_live"));
    assert_eq!(j(r, &RegRead::Error, true, Some(1000)), Liveness::Unknown("registry_io"));
    assert_eq!(j(r, &RegRead::Unparsable, true, Some(1000)), Liveness::Unknown("registry_unparsable"));
    // codex T4 2R 차단: 산 pid · 출생 시각이 기록과 다름 · 등록부 없음/오류 — 지금 그 pid 가 seatkeep 이 아니라는 양성 증거가 없으면 미결.
    for reg in [RegRead::Missing, RegRead::Error, RegRead::Unparsable] {
        assert_eq!(jx(r, &reg, true, Some(2000), None), Liveness::Unknown("start_mismatch_live"));
        assert_eq!(jx(r, &reg, true, Some(2000), Some(true)), Liveness::Unknown("start_mismatch_live"), "다른 seatkeep 일 수 있다");
        assert_eq!(jx(r, &reg, true, Some(2000), Some(false)), Liveness::Dead("pid_reused"), "seatkeep 이 아닌 프로세스 = 재사용 확정");
    }
    // 산 pid 가 아니면(끝남) 등록부가 없어도 죽음 확인.
    assert_eq!(j(r, &RegRead::Missing, false, None), Liveness::Dead("keeper_gone"));
}

#[test]
fn provisional_record_uses_registry_pid_and_ages_out() {
    let reg = RegRead::Ok(serde_json::json!({"phase": "committed", "pid": 50, "start_us": 7}));
    let prov = Some((0u32, None, 1.0));
    assert_eq!(target_pid(prov, &reg), Some(50));
    assert_eq!(j(prov, &reg, true, Some(7)), Liveness::Alive);
    assert_eq!(j(prov, &RegRead::Missing, false, None), Liveness::Unknown("provisional_starting"));
    assert_eq!(j(Some((0, None, PROVISIONAL_MAX_SECS + 1.0)), &RegRead::Missing, false, None), Liveness::Dead("never_started"));
}

#[test]
fn procargs_env_parse() {
    let mut b = 2i32.to_ne_bytes().to_vec();
    b.extend_from_slice(b"/bin/cys-seatkeep\0\0\0\0--dir\0/x\0A=1\0CYS_ROLE=worker-3\0B=2\0\0");
    assert_eq!(parse_procargs_env(&b, "CYS_ROLE").as_deref(), Some("worker-3"));
    assert_eq!(parse_procargs_env(&b, "A").as_deref(), Some("1"));
    assert_eq!(parse_procargs_env(&b, "--dir"), None, "인자는 env 가 아니다");
    assert_eq!(parse_procargs_env(&b, "Z"), None);
    assert_eq!(parse_procargs_env(&b[..3], "A"), None);
}

#[test]
fn process_start_us_reads_self_and_none_for_no_pid() {
    #[cfg(target_os = "macos")]
    {
        assert!(process_start_us(std::process::id()).is_some());
        assert!(process_start_us(0x7fff_fff0).is_none());
        assert_eq!(process_env_var(std::process::id(), "SEAT_ADOPT_NO_SUCH_KEY_X"), None);
    }
}

#[test]
fn reservation_blocks_role_and_unknown_role_blocks_all_role_creates() {
    let p = |skid: &str, role: Option<&str>| Pending { skid: skid.into(), role: role.map(str::to_string), pid: Some(1), start_us: None, until: None };
    assert!(blocked_by(&[], Some("worker")).is_none());
    let one = [p("k1", Some("worker-2"))];
    assert!(blocked_by(&one, Some("worker-2")).unwrap().contains("k1"));
    assert!(blocked_by(&one, Some("worker")).is_none(), "다른 역할은 막지 않는다");
    assert!(blocked_by(&one, None).is_none(), "역할 없는 셸 좌석은 막지 않는다");
    let unk = [p("k9", None)];
    assert!(blocked_by(&unk, Some("cso")).unwrap().contains("k9"));
    assert!(blocked_by(&unk, None).is_none());
}

#[test]
fn reservation_expires_with_keeper() {
    let p = Pending { skid: "k".into(), role: Some("r".into()), pid: Some(5), start_us: Some(10), until: None };
    assert!(pending_live(&p, |_| true, |_| Some(10), 0.0));
    assert!(!pending_live(&p, |_| false, |_| Some(10), 0.0), "seatkeep 이 끝나면 예약이 풀린다");
    assert!(!pending_live(&p, |_| true, |_| Some(11), 0.0), "pid 재사용 = 다른 프로세스 → 예약 풀림");
    let prov = Pending { skid: "k".into(), role: None, pid: None, start_us: None, until: Some(100.0) };
    assert!(pending_live(&prov, |_| true, |_| None, 99.0));
    assert!(!pending_live(&prov, |_| true, |_| None, 101.0));
}

#[test]
fn numbers_reopen_variants() {
    let dir = std::env::temp_dir().join(format!("cys_adopt_reopen_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let sock = dir.join("cys.sock");
    let _ = crate::recall::surface_numbers_boot(&sock, 1.0); // 표 만들기
    crate::recall::surface_numbers_insert(&sock, 5, Some(5), 1.0).unwrap();
    let _ = crate::recall::surface_numbers_boot(&sock, 2.0); // 열린 행 → boot_orphan
    assert!(crate::recall::surface_numbers_reopen(&sock, 5, Some(5), 1.0).is_ok(), "boot_orphan = 다시 연다");
    assert!(matches!(crate::recall::surface_numbers_reopen(&sock, 5, Some(5), 1.0), Err(crate::recall::NumbersWriteErr::PkConflict(_))), "열린 행 = 충돌");
    assert!(crate::recall::surface_numbers_reopen(&sock, 9, Some(9), 1.0).is_ok(), "행 없음 = 새로 쓴다");
    crate::recall::surface_numbers_close(&sock, 9, 3.0, "spawn_failed").unwrap();
    assert!(matches!(crate::recall::surface_numbers_reopen(&sock, 9, Some(9), 1.0), Err(crate::recall::NumbersWriteErr::PkConflict(_))), "다른 닫힘 = 충돌");
    // 입양 실패 되돌림 = boot_orphan → 다시 열 수 있다.
    crate::recall::surface_numbers_close(&sock, 5, 4.0, "boot_orphan").unwrap();
    assert!(crate::recall::surface_numbers_reopen(&sock, 5, Some(5), 1.0).is_ok());
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn registry_other_live_pid_guards_a_different_live_keeper() {
    let me = std::process::id();
    let reg = |pid: u32| RegRead::Ok(serde_json::json!({"phase": "committed", "pid": pid, "start_us": 1}));
    // 등록부 pid = 산 프로세스(이 시험 프로세스 · 실행 파일 ≠ cys-seatkeep → Some(false))는 「seatkeep 이 아니라는 증거」가 있어 막지 않는다.
    #[cfg(target_os = "macos")]
    assert_eq!(registry_other_live_pid(Some(1), &reg(me)), None, "산 pid 라도 seatkeep 이 아니면 지켜 줄 세대가 아니다");
    assert_eq!(registry_other_live_pid(Some(me), &reg(me)), None, "같은 pid = 따로 볼 것 없음");
    assert_eq!(registry_other_live_pid(Some(1), &reg(0x7fff_fff0)), None, "죽은 pid");
    assert_eq!(registry_other_live_pid(Some(1), &RegRead::Missing), None);
}


/// T5 세대 정합 — 입양 토큰 접두 = seatkeep id 의 (pid · 시작 시각)을 뒤집은 것일 때만 · 꼴 확인 · 사유 = 고정 낱말(값 0).
#[test]
fn check_adopted_token_generation_and_shape() {
    let skid = "1f2e-6aff3a1f-0";
    let rand = "0123456789abcdef0123456789abcdef";
    assert_eq!(check_adopted_token(skid, &format!("6aff3a1f-1f2e.{rand}")), Ok(()));
    // 시작 시각만 같고 pid 다른 위조 접두(A8ⓓ′-4) · pid 만 같고 시작 다름 · 순서 그대로(뒤집지 않음)
    assert_eq!(check_adopted_token(skid, &format!("6aff3a1f-1f2f.{rand}")), Err("generation_mismatch"));
    assert_eq!(check_adopted_token(skid, &format!("6aff3a20-1f2e.{rand}")), Err("generation_mismatch"));
    assert_eq!(check_adopted_token(skid, &format!("1f2e-6aff3a1f.{rand}")), Err("generation_mismatch"));
    // 꼴
    assert_eq!(check_adopted_token(skid, "6aff3a1f-1f2e"), Err("token_malformed"));
    assert_eq!(check_adopted_token(skid, "6aff3a1f-1f2e.0123"), Err("token_malformed"));
    assert_eq!(check_adopted_token(skid, &format!("6aff3a1f-1f2e.{}", rand.to_uppercase())), Err("token_malformed"));
    assert_eq!(check_adopted_token("1f2e-6aff3a1f", &format!("6aff3a1f-1f2e.{rand}")), Err("skid_malformed"));
    assert_eq!(check_adopted_token("1f2e-6aff3a1f-0-9", &format!("6aff3a1f-1f2e.{rand}")), Err("skid_malformed"));
    // 실제 발급기와 실제 seatkeep id 꼴이 맞물린다(같은 cysd 가 만든 둘)
    let started_at = 1_795_000_000.4_f64;
    let tok = crate::state::mint_seat_token(started_at).unwrap();
    let real_skid = format!("{:x}-{:x}-{}", std::process::id(), started_at as u64, 3);
    assert_eq!(check_adopted_token(&real_skid, &tok), Ok(()), "발급기 토큰과 seatkeep id 꼴이 어긋남");
}

/// T5 소스 핀(설계 ⑤): 좌석 토큰은 생성 때 한 곳(create_surface_core 의 `seat_token` 지역 값 → Surface 칸)에서만 정해진다.
/// 재발급·갱신(`.seat_token = …` 대입)이 새로 생기면 seatkeep 이 쥔 값(입양 때 넘김)과 어긋난다 → seatkeep 갱신 프레임과 함께 들어와야 하므로 붉힌다.
#[test]
fn seat_token_is_assigned_only_at_creation() {
    let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/bin/cysd");
    let mut hits = Vec::new();
    for e in std::fs::read_dir(&dir).unwrap() {
        let p = e.unwrap().path();
        let name = p.file_name().unwrap().to_string_lossy().into_owned();
        if !name.ends_with(".rs") || name.ends_with("_tests.rs") {
            continue;
        }
        let text = std::fs::read_to_string(&p).unwrap();
        // 운영 코드만(파일 안 `#[cfg(test)] mod tests` 앞까지 — 그 뒤 시험 본문은 보지 않는다).
        let prod = text.split("#[cfg(test)]\nmod tests").next().unwrap_or(&text);
        for (i, l) in prod.lines().enumerate() {
            let t = l.trim_start();
            if t.starts_with("//") {
                continue;
            }
            if let Some(k) = t.find(".seat_token") {
                let rest = t[k + ".seat_token".len()..].trim_start();
                if rest.starts_with('=') && !rest.starts_with("==") {
                    hits.push(format!("{name}:{}", i + 1));
                }
            }
        }
    }
    assert!(hits.is_empty(), "좌석 토큰 대입이 생성 밖에 생겼다(재발급 = seatkeep 갱신 프레임 필요): {hits:?}");
}

/// T5 실패 갈래 새지 않음(master#9e1379e9): 접두 불일치·꼴 불량 토큰 = None + 사건 `seat.adopt_token_skipped` 은 skid·사유 낱말만(토큰 값·난수 0).
#[test]
fn adopted_token_skip_event_never_carries_the_token() {
    let dir = std::env::temp_dir().join(format!("cys-t5skip-{}-{}", std::process::id(), crate::state::now_epoch() as u64));
    let _ = std::fs::create_dir_all(&dir);
    let daemon = Daemon::new(dir.join("cysd.sock"));
    let mut rx = daemon.bus.subscribe();
    let skid = "1f2e-6aff3a1f-0";
    let rand = "0123456789abcdef0123456789abcdef";
    let bad = [format!("6aff3a1f-1f2f.{rand}"), format!("6aff3a1f-1f2e.{}", &rand[..30])];
    for t in &bad {
        assert_eq!(adopted_token_or_skip(&daemon, skid, t.clone()), None);
    }
    let good = format!("6aff3a1f-1f2e.{rand}");
    assert_eq!(adopted_token_or_skip(&daemon, skid, good.clone()).as_deref(), Some(good.as_str()));
    let mut n = 0;
    while let Ok(e) = rx.try_recv() {
        if e["name"] == "seat.adopt_token_skipped" {
            n += 1;
            let s = e.to_string();
            assert!(!s.contains(&rand[..16]) && !s.contains("6aff3a1f-1f2f"), "사건에 토큰 조각이 실렸다: {s}");
            assert_eq!(e["payload"]["skid"], skid);
        }
    }
    assert_eq!(n, 2, "실패 둘 = 사건 둘 · 성공은 사건 없음");
    let _ = std::fs::remove_dir_all(&dir);
}
