//! seat_adopt 순수 판정 시험(T4).
use super::*;

fn rec(pid: u32) -> SeatRecord {
    SeatRecord {
        schema: 1,
        skid: "a-b-0".into(),
        sock: "/x/a-b-0.sock".into(),
        keeper_pid: pid,
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
fn record_roundtrips_through_json() {
    let r = rec(42);
    let t = serde_json::to_string(&r).unwrap();
    assert!(!t.contains("seat_token"), "좌석 기록에 토큰 칸이 생기면 안 된다(비편입 계약)");
    let back: SeatRecord = serde_json::from_str(&t).unwrap();
    assert_eq!(serde_json::to_value(&back).unwrap(), serde_json::to_value(&r).unwrap());
}

#[test]
fn judge_alive_only_when_committed_same_pid_alive_same_start() {
    let r = rec(42);
    let reg = serde_json::json!({"phase": "committed", "pid": 42, "start_us": 1000});
    assert_eq!(judge(&r, Some(&reg), true, Some(1000)), Liveness::Alive);
    assert_eq!(judge(&r, Some(&reg), true, Some(1001)), Liveness::Dead("pid_reused"));
    assert_eq!(judge(&r, Some(&reg), false, Some(1000)), Liveness::Dead("keeper_gone"));
    assert_eq!(judge(&r, Some(&reg), true, None), Liveness::Unknown("start_unreadable"));
    assert_eq!(judge(&r, None, true, Some(1000)), Liveness::Dead("registry_missing"));
    let other = serde_json::json!({"phase": "committed", "pid": 43, "start_us": 1000});
    assert_eq!(judge(&r, Some(&other), true, Some(1000)), Liveness::Dead("pid_mismatch"));
    for (ph, want) in [("prepare", Liveness::Dead("never_committed")), ("exited", Liveness::Dead("ended")),
                       ("ended_controller_lost", Liveness::Dead("ended"))] {
        let reg = serde_json::json!({"phase": ph, "pid": 42, "start_us": 1000});
        assert_eq!(judge(&r, Some(&reg), true, Some(1000)), want, "phase {ph}");
    }
    assert_eq!(judge(&r, Some(&serde_json::Value::Null), true, Some(1000)), Liveness::Unknown("registry_unparsable"));
}

#[test]
fn process_start_us_reads_self_and_none_for_no_pid() {
    #[cfg(target_os = "macos")]
    {
        assert!(process_start_us(std::process::id()).is_some());
        assert!(process_start_us(0x7fff_fff0).is_none());
    }
}
