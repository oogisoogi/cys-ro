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
fn procargs_flag_parse_stops_at_seat_command() {
    let mut b = 6i32.to_ne_bytes().to_vec();
    b.extend_from_slice(b"/x/cys-seatkeep\0\0\0cys-seatkeep\0--lock\0/s/d.lock\0--\0--lock\0/evil\0CYS_ROLE=w\0\0");
    assert_eq!(parse_procargs_flag(&b, "--lock").as_deref(), Some("/s/d.lock"));
    assert_eq!(parse_procargs_flag(&b, "--dir"), None);
    // `--` 뒤(좌석 명령)의 같은 낱말은 seatkeep 인자가 아니다.
    let mut c = 4i32.to_ne_bytes().to_vec();
    c.extend_from_slice(b"/x/cys-seatkeep\0\0cys-seatkeep\0--\0--lock\0/evil\0\0");
    assert_eq!(parse_procargs_flag(&c, "--lock"), None);
    // 값 없는 끝 · 잘린 버퍼.
    let mut d = 2i32.to_ne_bytes().to_vec();
    d.extend_from_slice(b"/x\0\0a\0--lock\0\0");
    assert_eq!(parse_procargs_flag(&d, "--lock"), None);
    assert_eq!(parse_procargs_flag(&b[..3], "--lock"), None);
}

#[test]
fn bind_from_same_other_unknown() {
    let me = std::path::Path::new("/private/tmp/no-such-skb/d.lock");
    assert_eq!(bind_from(me, Some("/private/tmp/no-such-skb/d.lock")), Bind::Mine);
    assert_eq!(bind_from(me, Some("/private/tmp/no-such-skb/e.lock")), Bind::Other);
    assert_eq!(bind_from(me, None), Bind::Unknown);
    // 같은 파일의 다른 글자(심링크 /tmp → /private/tmp) = 같음.
    let d = std::env::temp_dir().join(format!("skb-{}", std::process::id()));
    std::fs::create_dir_all(&d).unwrap();
    let real = std::fs::canonicalize(&d).unwrap().join("x.lock");
    std::fs::write(&real, b"").unwrap();
    let via = d.join("x.lock");
    assert_eq!(bind_from(&real, via.to_str()), Bind::Mine);
    let _ = std::fs::remove_dir_all(&d);
}

/// M1: 노브 끔 사용자 = seatkeep 폴더가 없다 → 즉시 반환 · 폴더를 만들지 않는다 · 사건 0(종전 바이트).
#[cfg(target_os = "macos")] // end_orphans_in = 맥 전용(seatkeep) · TICKET=cysr-1116-wincompile-1121
#[test]
fn end_orphans_without_folder_touches_nothing() {
    let daemon = crate::state::Daemon::new(std::env::temp_dir().join(format!("sko-{}/d.sock", std::process::id())));
    let mut rx = daemon.bus.subscribe();
    let dir = std::env::temp_dir().join(format!("sko-none-{}", std::process::id())).join("seatkeep");
    assert_eq!(end_orphans_in(&daemon, &dir, std::path::Path::new("/private/tmp/no-such-sko.lock")), 0);
    assert!(!dir.exists() && !dir.parent().unwrap().exists(), "폴더를 만들지 않는다");
    assert!(rx.try_recv().is_err(), "사건 0");
    let _ = std::fs::remove_dir_all(daemon.socket_path.parent().unwrap());
}

/// M1·D2: 관리용 종료는 신원이 서지 않으면 신호를 보내지 않는다 — 대상 = 이 시험 프로세스 자신(cys-seatkeep 이 아님 · 살아 있어야 함).
#[test]
fn end_keeper_refuses_a_process_that_is_not_seatkeep() {
    #[cfg(target_os = "macos")]
    {
        let me = std::process::id();
        let dir = std::env::temp_dir().join(format!("ske-{me}"));
        let lock = dir.join("d.lock");
        let start = process_start_us(me);
        assert_eq!(end_keeper(&dir, "x-1-0", me, start, &lock, &RegRead::Missing), Err("end_exe_not_seatkeep"));
        assert_eq!(end_keeper(&dir, "x-1-0", me, start.map(|s| s + 1), &lock, &RegRead::Missing), Err("end_start_mismatch"));
        assert_eq!(end_keeper(&dir, "x-1-0", me, None, &lock, &RegRead::Missing), Err("end_start_unknown"));
        assert_eq!(end_keeper(&dir, "x-1-0", 0x7fff_fff0, Some(1), &lock, &RegRead::Missing), Err("end_keeper_gone"));
        assert!(!dir.exists());
    }
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
    let p = |skid: &str, role: Option<&str>| Pending { skid: skid.into(), role: role.map(str::to_string), pid: Some(1), ..Default::default() };
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
    let p = Pending { skid: "k".into(), role: Some("r".into()), pid: Some(5), start_us: Some(10), ..Default::default() };
    assert!(pending_live(&p, |_| true, |_| Some(10), 0.0));
    assert!(!pending_live(&p, |_| false, |_| Some(10), 0.0), "seatkeep 이 끝나면 예약이 풀린다");
    assert!(!pending_live(&p, |_| true, |_| Some(11), 0.0), "pid 재사용 = 다른 프로세스 → 예약 풀림");
    let prov = Pending { skid: "k".into(), until: Some(100.0), ..Default::default() };
    assert!(pending_live(&prov, |_| true, |_| None, 99.0));
    assert!(!pending_live(&prov, |_| true, |_| None, 101.0));
}

/// M2: 역할 모름 미결의 「역할 있는 생성 전부 거절」은 상한 벽시계까지만 — 역할 아는 미결은 상한 없이 그 역할만.
#[test]
fn unknown_role_block_all_expires_but_known_role_stays() {
    let unk = Pending { skid: "u".into(), pid: Some(1), blocks_all_until: Some(100.0), ..Default::default() };
    assert!(blocked_by_at(std::slice::from_ref(&unk), Some("cso"), 99.0).is_some());
    assert!(blocked_by_at(std::slice::from_ref(&unk), Some("cso"), 100.5).is_none(), "상한 뒤 = 막지 않음");
    assert!(blocks_all(&unk, 99.0) && !blocks_all(&unk, 101.0));
    let known = Pending { skid: "k".into(), role: Some("seatr".into()), pid: Some(1), ..Default::default() };
    assert!(blocked_by_at(std::slice::from_ref(&known), Some("seatr"), 1e12).is_some(), "역할 아는 예약은 상한 없음");
    assert!(!blocks_all(&known, 0.0));
    // 상한 칸 없는 옛 리터럴 = 종전(늘 막음).
    let old = Pending { skid: "o".into(), pid: Some(1), ..Default::default() };
    assert!(blocked_by_at(std::slice::from_ref(&old), Some("x"), 1e12).is_some());
}

/// M2: 재시도가 같은 좌석 예약을 바꿔도 처음 시각·상한은 그대로(상한이 재시도마다 새로 시작되지 않게).
#[test]
fn retry_keeps_first_since_and_block_deadline() {
    let first = Pending { skid: "u".into(), since: 10.0, blocks_all_until: Some(70.0), ..Default::default() };
    let again = Pending { skid: "u".into(), since: 20.0, blocks_all_until: Some(80.0), reason: "r2".into(), ..Default::default() };
    let c = carry_pending(Some(&first), again.clone());
    assert_eq!((c.since, c.blocks_all_until, c.reason.as_str()), (10.0, Some(70.0), "r2"));
    let fresh = carry_pending(None, again);
    assert_eq!((fresh.since, fresh.blocks_all_until), (20.0, Some(80.0)));
    // 역할이 판명된 재판정(상한 없음)은 옛 상한을 남겨도 역할 아는 예약이라 전면 차단 아님.
    let known = Pending { skid: "u".into(), role: Some("w".into()), since: 30.0, ..Default::default() };
    assert!(!blocks_all(&carry_pending(Some(&first), known), 0.0));
}

/// T6a 사전 점검 판정표: 입양 가능 = 산 seatkeep · 실행 파일 이 cysd 옆 · 핵심 판 같음 · 결박 Mine/Unknown. 남의 것·죽은 것 = 막힘 아님.
#[test]
fn adopt_check_block_reasons() {
    let a = Liveness::Alive;
    assert_eq!(check_block_reason(&a, Some(true), true, &Bind::Mine), None);
    assert_eq!(check_block_reason(&a, Some(true), true, &Bind::Unknown), None);
    assert_eq!(check_block_reason(&a, Some(false), true, &Bind::Mine).as_deref(), Some("exe_not_beside_this_cysd"));
    assert_eq!(check_block_reason(&a, None, true, &Bind::Mine).as_deref(), Some("exe_unreadable"));
    assert_eq!(check_block_reason(&a, Some(true), false, &Bind::Mine).as_deref(), Some("core_version_mismatch"));
    assert_eq!(check_block_reason(&Liveness::Unknown("registry_io"), Some(true), true, &Bind::Mine).as_deref(), Some("registry_io"));
    assert_eq!(check_block_reason(&Liveness::Dead("keeper_gone"), None, false, &Bind::Mine), None);
    assert_eq!(check_block_reason(&Liveness::Unknown("registry_io"), Some(false), false, &Bind::Other), None);
}

/// 사전 점검 = 폴더 없음 → 빈 결과 · 폴더를 만들지 않는다(쓰기 0).
#[test]
fn adopt_check_without_folder_is_empty_and_writes_nothing() {
    let dir = std::env::temp_dir().join(format!("skc-none-{}", std::process::id())).join("seatkeep");
    let v = adopt_check_in(&dir, std::path::Path::new("/private/tmp/no-such-skc.lock"));
    assert_eq!(v, serde_json::json!({"adoptable": 0, "blocked": [], "foreign": 0, "dead": 0}));
    assert!(!dir.parent().unwrap().exists());
}

/// M2 조회: 노브 끔 = 칸 없음(None · `org.status` 종전 바이트).
#[test]
fn status_json_absent_when_knob_off() {
    if !enabled() {
        let daemon = crate::state::Daemon::new(std::env::temp_dir().join(format!("sks-{}/d.sock", std::process::id())));
        assert!(status_json(&daemon).is_none());
        let _ = std::fs::remove_dir_all(daemon.socket_path.parent().unwrap());
    }
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

#[cfg(target_os = "macos")] // registry_other_live_pid = 맥 전용(seatkeep_exe_matches) · TICKET=cysr-1116-wincompile-1121
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
