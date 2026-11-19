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
    judge(&JudgeIn { rec, reg, alive, start_now: start })
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
