//! ★(1.1.16 · TICKET=cysr-1116-backlog-fix2-1118) 재검(VERIFY.cysr-1116-backlog-reverify.md · 재검 좌석 surface:2167) R1~R3 의 재현을
//! 단언 시험으로 옮긴 것. 재검 좌석의 계측 시험(`bv_verify_tests.rs` · 커밋 안 됨 · `bv_n1`·`bv_n2`·`bv_n4`)은 바깥 파이썬 기록기로 쟀다 —
//! 여기서는 바이트가 필요한 시험만 raw `cat` 기록기 좌석(`stty raw -echo; exec cat > 파일` · POSIX · b16_fix 와 같은 방식)으로 잰다.
//! 이 파일은 `send_settle_tests` 의 자식 모듈이다(그 픽스처·도우미를 그대로 쓴다).

use super::*;

const RULE: &str = "────────────────────────────────────────";

/// raw `cat` 기록기 좌석(claude 어댑터 · 데몬 좌석 표에 등록) — 데몬이 PTY 에 실제로 쓴 바이트가 `out` 파일에 그대로 쌓인다.
fn recorder_seat(fx: &Fx, out: &std::path::Path) -> Arc<Surface> {
    let cmd = format!("stty raw -echo; exec cat > '{}'", out.display());
    let t = fx.daemon.create_surface(None, Some(cmd), None, Some("worker-1".into()), 24, 80).expect("기록기 좌석");
    fx.daemon.surfaces.lock().unwrap().insert(t.id, t.clone());
    *t.agent_meta.lock().unwrap() = Some(("claude".into(), "claude".into()));
    let deadline = Instant::now() + Duration::from_secs(20);
    while !out.exists() {
        assert!(Instant::now() < deadline, "기록기 준비 안 됨");
        std::thread::sleep(Duration::from_millis(20));
    }
    std::thread::sleep(Duration::from_millis(600)); // stty 적용 뒤 첫 바이트
    t
}

/// 적색→녹색(재검 R1 · `bv_n2_stale_feed_item_clean_screen` 세 갈래): 화면에는 창이 없고(빈 입력줄 · 또는 사람 초안) feed 승인 대기 항목만
/// 남은 좌석에 「창이면 쓰지 마라」 원자 제출 → **쓰기 전** 거부(`approval_screen` 오류 응답) · PTY 0 바이트 · 사람 초안 계수 그대로.
/// 종전(8bdd08ad): 쓰기 전 판정은 화면·관문만 봐서 통과 → 쓰는 도중 탐침(feed 축 포함)이 Ctrl-U(`15`)만 쓰고 거부 · 응답 `sent:true` ·
/// 사람 초안 갈래는 그 Ctrl-U 가 실제 입력줄의 초안을 지웠다.
#[test]
#[cfg_attr(not(unix), ignore = "좌석 명령이 POSIX 셸 문법")]
fn b16fix2_stale_feed_item_refuses_before_any_write() {
    let fx = fx("b16fix2-stale-feed");
    let mut bad: Vec<String> = Vec::new();
    for (i, arm) in ["human-empty", "human-draft", "machine"].iter().enumerate() {
        let out = fx.dir.join(format!("rx-stale-{i}.bin"));
        let t = recorder_seat(&fx, &out);
        let xpid = P + 3201 + 2 * i as u32;
        let _x = pane(&fx, "worker-2", xpid);
        t.seat_cache.store(crate::governance::SeatState::Occupied.as_u8(), Ordering::Relaxed);
        paint_empty_prompt(&t);
        if *arm == "human-draft" {
            {
                let _gate = t.input_gate.lock().unwrap();
                t.apply_pending_input("사람 초안".as_bytes(), crate::governance::InputOrigin::Human);
            }
            paint(&t, &["────────", "❯ 사람 초안", "────────"], 1, 12);
        }
        if *arm == "machine" {
            *t.receiver_proof.lock().unwrap() = Some(Arc::new(crate::agent_write::PassThrough));
            crate::agent_write::set_test_sync_settle(false);
        }
        fx.daemon.push_feed_notification("approval", "claude 승인 대기 감지", "Do you want to proceed?", Some(t.id));
        assert!(!crate::governance::seat_approval_pending(&fx.daemon, &t), "전제: 화면 술어 거짓(창 없음)");
        assert!(crate::governance::approval_or_gate_pending(&fx.daemon, t.id), "전제: feed 승인 항목");
        let before = counts(&t);
        let ev0 = named(&fx, "input.refused_at_write").len();
        let r = if *arm == "machine" {
            atomic_send(&fx, Some(xpid), &t, "/clear", false, true)
        } else {
            atomic_send(&fx, None, &t, "사람이 보낸 말", true, true)
        };
        std::thread::sleep(Duration::from_millis(1500));
        crate::agent_write::set_test_sync_settle(true);
        let got = std::fs::read(&out).unwrap_or_default();
        let after = counts(&t);
        let late = named(&fx, "input.refused_at_write").len() - ev0;
        eprintln!("B16FIX2-R1[{arm}] 응답 {r} · PTY {got:02x?} · 계수 {before:?} → {after:?} · 쓰는 도중 거부 흔적 {late}");
        if r["error"]["code"] != json!(cys::ERR_APPROVAL_SCREEN) {
            bad.push(format!("{arm}: 쓰기 전 거부(오류 응답)가 아니다: {r}"));
        }
        if !got.is_empty() {
            bad.push(format!("{arm}: PTY 에 썼다: {got:02x?}"));
        }
        if (after.0, after.1) != (before.0, before.1) {
            bad.push(format!("{arm}: 입력줄 계수가 바뀌었다 {before:?} → {after:?}"));
        }
        if late != 0 {
            bad.push(format!("{arm}: 쓰는 도중 탐침까지 갔다(흔적 {late})"));
        }
        let _ = t.child.lock().unwrap().kill();
    }
    assert!(bad.is_empty(), "feed 항목만 남은 좌석에 썼다:\n{}", bad.join("\n"));
}

/// 적색→녹색(재검 R2 · `bv_n4_feed_allow_on_new_dialogs`): 계획 승인 창은 **막기 전용** — 쓰기 직전 술어는 그 창을 그대로 막고(사람 말 거부 ·
/// 쓰기 0), 오퍼레이터 결정 집행(D24ⓐ `actuate_screen_approval` · `feed reply allow`)은 그 창을 승인 창으로 읽지 않는다(`gone` · PTY 0).
/// 대조: Bash 창(종전 문구)·Write 창은 그대로 `Ok("return")` · PTY `0d`.
/// 종전(8bdd08ad): 계획 승인 창 2종 모두 `Ok("return")` · PTY `0d`(= 계획 승인 + 자동 수락 모드 전환).
#[test]
#[cfg_attr(not(unix), ignore = "좌석 명령이 POSIX 셸 문법")]
fn b16fix2_plan_dialog_is_block_only_for_operator_actuation() {
    let fx = fx("b16fix2-plan-actuate");
    let screens: Vec<(&str, Vec<&str>, u16, Result<&str, &str>, Vec<u8>)> = vec![
        ("bash-proceed", vec![RULE, " Bash command", "   ls", " Do you want to proceed?", " ❯ 1. Yes", "   2. No", "", " Esc to cancel"], 4, Ok("return"), vec![0x0d]),
        ("write-create", vec![RULE, " Create file", " src/new.rs", " Do you want to create new.rs?", " ❯ 1. Yes", "   2. Yes, allow all edits during this session (shift+tab)", "   3. No"], 4, Ok("return"), vec![0x0d]),
        ("plan-auto-accept", vec![RULE, " Ready to code?", " Claude has written up a plan and is ready to execute. Would you like to", " proceed?", "", " ❯ 1. Yes, and auto-accept edits", "   2. Yes, manually approve edits", "   3. No, keep planning"], 5, Err("gone"), vec![]),
        ("plan-clear-context", vec![RULE, " Ready to code?", " Claude has written up a plan and is ready to execute. Would you like to", " proceed?", "", " ❯ 1. Yes, clear context and auto-accept edits", "   2. Yes, auto-accept edits", "   3. Yes, manually approve edits", "   4. No, keep planning"], 5, Err("gone"), vec![]),
    ];
    let mut bad: Vec<String> = Vec::new();
    for (i, (name, rows, cur, want, want_bytes)) in screens.iter().enumerate() {
        let out = fx.dir.join(format!("rx-plan-{i}.bin"));
        let t = recorder_seat(&fx, &out);
        paint(&t, rows, *cur, 2);
        // 막기는 그대로: 쓰기 직전 술어 참(계획 승인 창 포함 전부).
        if !crate::governance::seat_approval_pending(&fx.daemon, &t) {
            bad.push(format!("{name}: 쓰기 직전 술어가 창을 못 읽는다(막기 전용이 막지 않음)"));
        }
        let got_r = crate::governance::actuate_screen_approval(&fx.daemon, t.id, true);
        std::thread::sleep(Duration::from_millis(500));
        let got = std::fs::read(&out).unwrap_or_default();
        eprintln!("B16FIX2-R2 {name}: 허용 집행 → {got_r:?} · PTY {got:02x?}");
        if got_r != *want || got != *want_bytes {
            bad.push(format!("{name}: 집행 {got_r:?} · PTY {got:02x?} (기대 {want:?} · {want_bytes:02x?})"));
        }
        let _ = t.child.lock().unwrap().kill();
    }
    assert!(bad.is_empty(), "{}", bad.join("\n"));
}

/// 적색→녹색(재검 R3 a·b · `bv_n1_new_patterns_false_positive` 의 `tn*` 줄) + 음성 대조(같은 시험의 `fp*` 줄 = 거짓 양성 후보).
/// a = 계획 승인 창 선택 줄이 문장 아래 5번째 행(여백 1 + 선택지 4 뒤 · 의견 입력 행) · b = Write 창 파일 이름에 `?`.
/// 종전(8bdd08ad): tn2·tn7 술어 거짓 → Ctrl-U·본문·Enter 가 그 창에 들어갔다. fp 줄은 고침 전후 같은 값이어야 한다(재검 관측 그대로 —
/// 묶이는 fp4·fp4w·fp7 은 종전 문구 fp4old 도 같은 자리에서 묶이는 화면 = 입력창 없는 화면 · 가로줄 없이 커서가 인용 선택 행 위).
/// tn8* = codex 1R major 2(파일 이름 속 `─` — 문장 범위는 가로줄 **행**(줄머리 `─`)만 넘지 않는다).
/// (R3 c = 낱말 가운데에서 잘린 문장 · 대역 인공물로 판단해 손대지 않았다 — 여기 넣지 않는다.)
#[test]
fn b16fix2_dialog_variants_and_false_positive_table() {
    let fx = fx("b16fix2-variants");
    let screens: Vec<(&str, Vec<&str>, u16, bool)> = vec![
        // ── 거짓 양성 후보(창이 아닌 화면) — 재검 관측값 그대로
        ("fp1-prose-above-box-plan", vec!["● 그 창은 이렇게 생겼다:", "  Would you like to proceed?", "  ❯ 1. Yes", "    2. No", RULE, "❯ ", RULE, "  ? for shortcuts"], 5, false),
        ("fp2-review-above-box-write", vec!["● 코드 리뷰: 이 문구가 뜬다", "  Do you want to overwrite a.rs?", "  ❯ 1. Yes", "    2. No", RULE, "❯ ", RULE, "  ? for shortcuts"], 5, false),
        ("fp3-typed-in-box", vec!["● 답", RULE, "❯ Would you like to proceed?", "  ❯ 1. Yes", RULE, "  ? for shortcuts"], 3, false),
        ("fp4-transcript-no-box-plan", vec!["● 설명: 아래가 그 창이다", RULE, "  Would you like to proceed?", "  ❯ 1. Yes", "    2. No", "", "  Showing detailed transcript · ctrl+o to toggle"], 6, true),
        ("fp4w-transcript-no-box-write", vec!["● 설명: 아래가 그 창이다", RULE, "  Do you want to create new.rs?", "  ❯ 1. Yes", "    2. No", "", "  Showing detailed transcript · ctrl+o to toggle"], 6, true),
        ("fp4old-transcript-no-box-OLD-pattern", vec!["● 설명: 아래가 그 창이다", RULE, "  Do you want to proceed?", "  ❯ 1. Yes", "    2. No", "", "  Showing detailed transcript · ctrl+o to toggle"], 6, true),
        ("fp5-prose-hr-then-quote-above-box", vec!["● 설명", RULE, "  Would you like to proceed?", "  ❯ 1. Yes", RULE, "❯ ", RULE, "  ? for shortcuts"], 5, false),
        ("fp6-sentence-only-below-rule-no-choice", vec!["● 설명", RULE, "  Would you like to proceed?", "  (y/n)", "", "  Showing detailed transcript · ctrl+o to toggle"], 5, false),
        ("fp7-norule-cursor-on-quoted-choice", vec!["● 예:", "  Do you want to create a.rs?", "  ❯ 1. Yes", "    2. No"], 2, true),
        ("fp8-norule-cursor-elsewhere", vec!["● 예:", "  Do you want to create a.rs?", "  ❯ 1. Yes", "    2. No", "  끝"], 4, false),
        // ── 실제 창 모양의 변형 — 전부 읽어야 한다
        ("tn1-plan-4opts-cursor-on-4th", vec![RULE, " Claude has written up a plan and is ready to execute. Would you like to", " proceed?", "", "   1. Yes, clear context and auto-accept edits", "   2. Yes, auto-accept edits", "   3. Yes, manually approve edits", " ❯ 4. No, keep planning", "", " ctrl-g to edit plan"], 7, true),
        ("tn2-plan-5rows-cursor-on-5th(R3a)", vec![RULE, " Claude has written up a plan and is ready to execute. Would you like to", " proceed?", "", "   1. Yes, clear context and auto-accept edits", "   2. Yes, auto-accept edits", "   3. Yes, manually approve edits", "   4. No, keep planning", " ❯ 5. Type here to tell Claude what to change", "", " ctrl-g to edit plan"], 8, true),
        ("tn0b-plan-same-fits-in-80cols", vec![RULE, " Ready to code?", " Claude has written up a plan. Would you like to proceed?", " ❯ 1. Yes, and auto-accept edits", "   2. Yes, manually approve edits", "   3. No, keep planning", "", " ctrl-g to edit plan"], 3, true),
        ("tn3-plan-wrapped-sentence", vec![RULE, " Claude has written up a plan and is ready to execute. Would you like to", " proceed?", "", " ❯ 1. Yes, and auto-accept edits", "   2. No, keep planning"], 4, true),
        ("tn4-write-long-name-wrapped", vec![RULE, " Create file", " Do you want to create a-very-long-file-name-that-wraps-over-the-edge-of-the-", " terminal.rs?", " ❯ 1. Yes", "   2. Yes, allow all edits during this session (shift+tab)", "   3. No"], 4, true),
        ("tn5-write-cursor-on-3rd", vec![RULE, " Create file", " Do you want to create new.rs?", "   1. Yes", "   2. Yes, allow all edits during this session (shift+tab)", " ❯ 3. No, and tell Claude what to do differently (esc)"], 5, true),
        ("tn6-write-norule-tall-cursor-on-choice", vec![" 1 fn main() {}", " 2 // 긴 미리보기로 윗 가로줄이 밀려남", " Do you want to overwrite a.rs?", " ❯ 1. Yes", "   2. No"], 3, true),
        ("tn7-write-question-mark-in-name(R3b)", vec![RULE, " Create file", " Do you want to create what?.md?", " ❯ 1. Yes", "   2. No"], 3, true),
        ("tn7b-write-question-marks-in-name-cursor-on-3rd", vec![RULE, " Overwrite file", " Do you want to overwrite a?b?.rs?", "   1. Yes", "   2. Yes, allow all edits during this session (shift+tab)", " ❯ 3. No"], 5, true),
        // codex 1R major 2: 파일 이름 속 `─`(가로줄 글자) — 종전 `[^?]` 는 읽었고 첫 고침 `[^─]` 는 못 읽었다. 가로줄 **행**만 경계다.
        ("tn8-write-box-char-in-name", vec![RULE, " Create file", " Do you want to create a─b.rs?", " ❯ 1. Yes", "   2. No", " Esc to cancel"], 3, true),
        ("tn8b-write-box-char-and-question-in-name", vec![RULE, " Overwrite file", " Do you want to overwrite a─?b.rs?", " ❯ 1. Yes", "   2. No", " Esc to cancel"], 3, true),
        ("tn8c-write-box-char-name-wrapped", vec![RULE, " Create file", " Do you want to create a-very-long-file-name-with-a─box-char-that-wraps-over-the-", " edge─x.rs?", " ❯ 1. Yes", "   2. No"], 4, true),
        // codex 2R major: 공백에서 접혀 다음 행이 `─` 로 **시작**하는 이름(가로줄 행이 아니다 — 행 전체가 `─` 일 때만 가로줄 · is_rule_row).
        ("tn8d-write-wrapped-row-starts-with-box-char", vec![RULE, " Create file", " Do you want to create long-prefix", " ─b.rs?", " ❯ 1. Yes", "   2. No"], 4, true),
        // codex 3R major 1: 이름 연속 행이 `─`·공백이 섞인 머리로 시작(가로줄 행 아님).
        ("tn8e-write-wrapped-row-box-chars-and-spaces", vec![RULE, " Create file", " Do you want to create long-prefix", " ─ ─b.rs?", " ❯ 1. Yes", "   2. No"], 4, true),
        // codex 3R major 2(좌석 판독): 동사 바로 뒤 빈 행을 넘어 이름을 잇지 않는다(창이 아닌 모양 · 선택 행이 있어도).
        ("fp9-write-blank-row-after-verb", vec![RULE, " Do you want to create", "", " y.rs?", " ❯ 1. Yes", "   2. No"], 4, false),
    ];
    let mut bad: Vec<String> = Vec::new();
    for (i, (name, rows, cur, want)) in screens.iter().enumerate() {
        let t = agent_pane_settled(&fx, "worker-1", P + 3220 + i as u32);
        paint(&t, rows, *cur, 2);
        let got = crate::governance::seat_approval_pending(&fx.daemon, &t);
        if got != *want {
            bad.push(format!("{name}: 술어 {got} (기대 {want})"));
        }
    }
    assert!(bad.is_empty(), "{}", bad.join("\n"));
    // 정규식 단독(화면 전량 꼴 · 판독 범위 밖에서도): 문장 범위는 가로줄 **행**(전부 `─`)을 넘지 않는다 — codex 2R 고침의 음성 대조.
    let embed: Value = cys::pack::PACK_ALL
        .iter()
        .find(|(r, _)| *r == "agents.json")
        .map(|(_, c)| serde_json::from_str(c).expect("임베드 agents.json"))
        .expect("임베드 agents.json");
    let pat = embed["claude"]["approval_patterns"]
        .as_array()
        .expect("approval_patterns")
        .iter()
        .find(|p| p["name"] == json!("file-write-permission"))
        .and_then(|p| p["pattern"].as_str())
        .expect("file-write-permission");
    let re = regex::Regex::new(pat).expect("정규식");
    assert!(re.is_match("Do you want to create long-prefix\n ─b.rs?\n ❯ 1. Yes"), "행머리 ─ 이름 접힘");
    assert!(re.is_match("Do you want to create long-prefix\n ───  b.rs?\n ❯ 1. Yes"), "행머리 ─ 묶음 + 공백 뒤 이름");
    assert!(re.is_match("Do you want to create long-prefix\n ─ ─b.rs?\n ❯ 1. Yes"), "행머리 ─·공백 섞임(codex 3R major 1)");
    assert!(re.is_match("Do you want to create\n ─b.rs?\n ❯ 1. Yes"), "동사 뒤 접힘 + 행머리 ─");
    assert!(re.is_match("Do you want to\n write to src/a.rs?\n ❯ 1. Yes"), "낱말 사이 한 번 접힘");
    // codex 3R major 2: 동사 뒤·낱말 사이 공백이 가로줄 행·빈 행을 넘지 않는다.
    assert!(!re.is_match(&format!("Do you want to create\n{RULE}\n y.rs?\n ❯ 1. Yes")), "동사 바로 뒤 가로줄 행을 넘었다");
    assert!(!re.is_match(&format!("Do you want to create \n  {RULE}  \n y.rs?\n ❯ 1. Yes")), "동사 뒤 공백 + 앞뒤 공백 가로줄 행을 넘었다");
    assert!(!re.is_match("Do you want to create\n\n y.rs?\n ❯ 1. Yes"), "동사 바로 뒤 빈 행을 넘었다");
    assert!(!re.is_match("Do you want to create x\n\n y.rs?\n ❯ 1. Yes"), "이름 안 빈 행을 넘었다");
    assert!(!re.is_match("Do\n\nyou want to create y.rs?\n ❯ 1. Yes"), "낱말 사이 빈 행을 넘었다");
    assert!(!re.is_match(&format!("Do you want to create x\n{RULE}\n y.rs?\n ❯ 1. Yes")), "가로줄 행을 넘어 문장을 이었다");
    assert!(!re.is_match(&format!("Do you want to create x\n  {RULE}  \n y.rs?\n ❯ 1. Yes")), "앞뒤 공백 있는 가로줄 행을 넘었다");
}
