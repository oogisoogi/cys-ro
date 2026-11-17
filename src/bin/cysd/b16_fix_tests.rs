//! ★(1.1.16 · TICKET=cysr-1116-backlog-fix-1118) 독립 검증(VERIFY.cysr-1116-backlog.md · 검증 좌석 surface:2162) 지적 1·2·4·5·6 의
//! 재현을 단언 시험으로 옮긴 것. 검증 좌석의 계측 시험(`bv_verify_tests.rs` · 커밋 안 됨)은 PTY 바이트 기록기로 쟀다 — 여기서는
//! ⑴ 바이트가 꼭 필요한 한 건(붙여넣기 앞 거부)만 기록기 좌석(`stty raw -echo; exec cat > 파일` · POSIX)으로 재고
//! ⑵ 나머지는 데몬 응답(거부 = 쓰기 0 계약) · writer 쓰기 계수(`inject_track.wrote()` = 바이트를 PTY 에 쓴 writer 요청 수) ·
//!    입력줄 계수로 잰다(윈도우에서도 돈다).
//! 이 파일은 `send_settle_tests` 의 자식 모듈이다(그 픽스처·도우미를 그대로 쓴다).

use super::*;

/// 입력줄에 사람 본문이 보이는 화면(창이 닫힌 뒤 — 검증 전제 ⑴: 붙여넣기가 끝난 뒤 창이 떴다 닫히면 Claude 가 그 본문을 다시 보여 준다).
fn paint_line_with(t: &Arc<Surface>, body: &str) {
    let row = format!("❯ {body}");
    paint(t, &["────────", row.as_str(), "────────"], 1, 2 + body.chars().count() as u16 * 2);
}

/// 사람 입력 시각 기록을 60초 앞으로(타이핑 가드 3초 · 스케줄 사람 입력 창 30초 밖 — 검증 좌석과 같은 수법 · 실제로 기다리지 않음).
fn backdate_human_input(t: &Arc<Surface>) {
    let mut g = t.last_human_input.lock().unwrap();
    if let Some(x) = *g {
        *g = Some(x - Duration::from_secs(60));
    }
}

const HUMAN_BODY: &str = "사람이 보낸 말";

/// 사람 표지 원자 제출(앱 send_input 꼴)의 Enter 를 창으로 거부시킨다 — 붙여넣기 뒤(writer 가 쓰는 중 · Enter 앞)에 창을 그린다.
/// 끝나면 창을 닫고 입력줄에 그 본문을 보이고 사람 입력 시각을 60초 앞으로 돌린다. 반환 = 거부 처분 직후의 계수.
fn refuse_human_enter(fx: &Fx, t: &Arc<Surface>) -> (u64, u64, u64) {
    paint_empty_prompt(t);
    let r = atomic_send(fx, None, t, HUMAN_BODY, true, true);
    assert_eq!(r["result"]["sent"], json!(true), "전제: 쓰기 전에는 창이 없다: {r}");
    dialog_after(t, 300).join().unwrap(); // 붙여넣기(≈150ms) 뒤 · Enter(≈550ms) 앞
    assert!(!atomic_enter_written(t), "전제: Enter 가 거부됐다");
    let after = counts(t);
    paint_line_with(t, HUMAN_BODY);
    backdate_human_input(t);
    after
}

/// 적색→녹색(검증 지적 1 · 거부 처분 자체): 사람 길 Enter 거부 뒤 남은 본문은 **사람 몫**이다 — 사람 계수 > 0 · 마지막 기계 본문 기록 없음.
/// 종전: `counts=(1, 0, 1)`(사람 0) · 마지막 기계 본문 = 그 사람 본문(검증 e2-followon.txt).
#[test]
fn b16fix_refused_human_body_is_restored_as_human_draft() {
    let fx = fx("b16fix-restore");
    let t = agent_pane_settled(&fx, "worker-1", P + 3000);
    let (mirror, human, _) = refuse_human_enter(&fx, &t);
    assert!(mirror > 0, "입력줄 계수 0");
    assert!(human > 0, "남은 사람 본문을 사람 몫으로 세지 않았다(사람 계수 {human})");
    assert!(t.inject_track.last_body().is_none(), "사람 본문이 「마지막 기계 본문」으로 남았다 — H0 가 그것을 기계 잔여로 입증한다");
    let ev = named(&fx, "input.refused_at_write");
    assert_eq!(ev.len(), 1, "{ev:?}");
    assert_eq!(ev[0]["payload"]["stage"], json!("before_enter"), "{ev:?}");
}

/// 적색→녹색(검증 지적 1 · ⓑ₂ⓒⓓ): 거부 뒤 기계가 보내는 Return(신 CLI 순서 = 직접 본문 거부 → `queued + absorb_return` 재적재 → 짝 Return ·
/// 옛 CLI·원시 RPC 단독 Return)과 기계 원자 제출(`clear_first` · 예: 순환 `/clear`)은 그 사람 본문을 **제출하지도 지우지도 않는다**
/// (거부 · PTY 쓰기 0). 종전: Return 이 써져 사람 본문이 제출됨(ⓑ₂ⓒ) · Ctrl-U 가 사람 본문을 지우고 `/clear` 제출(ⓓ).
/// 갈래마다 새 좌석에서 같은 거부를 만든 뒤 잰다 — 실패한 갈래를 한꺼번에 보고한다.
#[test]
fn b16fix_followons_do_not_submit_or_erase_refused_human_body() {
    let fx = fx("b16fix-followon");
    let mut bad: Vec<String> = Vec::new();
    for (i, arm) in ["b2", "c", "d"].iter().enumerate() {
        let (tp, xp) = (P + 3010 + 2 * i as u32, P + 3011 + 2 * i as u32);
        let t = agent_pane_settled(&fx, "worker-1", tp);
        let _x = pane(&fx, "worker-2", xp);
        refuse_human_enter(&fx, &t);
        let w0 = t.inject_track.wrote();
        let rs: Vec<Value> = match *arm {
            "b2" => vec![
                direct(&fx, Some(xp), &t, "기계 직접 본문"),
                rpc(&fx, Some(xp), "surface.send_text",
                    json!({"surface_id": t.id, "text": "기계 직접 본문", "queued": true, "absorb_return": true})),
                pair_return(&fx, Some(xp), &t),
            ],
            "c" => vec![rpc(&fx, Some(xp), "surface.send_key", json!({"surface_id": t.id, "key": "Return", "queued": false}))],
            _ => {
                *t.receiver_proof.lock().unwrap() = Some(Arc::new(crate::agent_write::PassThrough));
                vec![atomic_send(&fx, Some(xp), &t, "/clear", false, true)]
            }
        };
        std::thread::sleep(Duration::from_millis(1500));
        let wrote = t.inject_track.wrote() - w0;
        let (_, human, _) = counts(&t);
        eprintln!("B16FIX[{arm}] 쓰기 +{wrote} · 사람 계수 {human} · 응답 {rs:?}");
        if wrote != 0 || human == 0 {
            bad.push(format!("{arm}: PTY 쓰기 +{wrote} · 사람 계수 {human} · 응답 {rs:?}"));
        }
    }
    assert!(bad.is_empty(), "거부된 사람 본문을 기계가 제출·삭제했다:\n{}", bad.join("\n"));
}

/// 음성 대조(검증 지적 1 · ⓐⓑⓕ 그대로): 거부 뒤 ⓐ 큐 틱 = 보류(큐에 남음 · 쓰기 0) · ⓑ 기계 직접 본문 = 거부(쓰기 0) ·
/// ⓕ 사람이 다시 보냄 = 정상 제출(Ctrl-U 로 옛 본문 지우고 새 본문 + Enter — 사람 몫 복원이 사람의 재전송을 막지 않는다).
#[test]
fn b16fix_followons_unchanged_queue_hold_direct_refusal_and_human_resend() {
    let fx = fx("b16fix-unchanged");
    // ⓐ
    let t = agent_pane_settled(&fx, "worker-1", P + 3020);
    let _x = pane(&fx, "worker-2", P + 3021);
    refuse_human_enter(&fx, &t);
    let w0 = t.inject_track.wrote();
    let r = rpc(&fx, Some(P + 3021), "surface.send_text", json!({"surface_id": t.id, "text": "기계 큐 본문", "queued": true}));
    assert_eq!(r["result"]["queued"], json!(true), "{r}");
    for _ in 0..3 {
        crate::governance::h_queue_tick(&fx.daemon);
        std::thread::sleep(Duration::from_millis(400));
    }
    assert_eq!(qlen(&t), 1, "ⓐ 큐 본문이 사람 본문 위로 배달됐다");
    assert_eq!(t.inject_track.wrote() - w0, 0, "ⓐ PTY 쓰기");
    // ⓑ
    let t = agent_pane_settled(&fx, "worker-1", P + 3022);
    let _x = pane(&fx, "worker-2", P + 3023);
    refuse_human_enter(&fx, &t);
    let w0 = t.inject_track.wrote();
    let r = direct(&fx, Some(P + 3023), &t, "기계 직접 본문");
    assert!(r["error"]["code"].is_string(), "ⓑ 기계 직접 본문이 받아들여졌다: {r}");
    std::thread::sleep(Duration::from_millis(600));
    assert_eq!(t.inject_track.wrote() - w0, 0, "ⓑ PTY 쓰기");
    // ⓕ
    let t = agent_pane_settled(&fx, "worker-1", P + 3024);
    refuse_human_enter(&fx, &t);
    paint_line_with(&t, HUMAN_BODY);
    let r = atomic_send(&fx, None, &t, "사람이 다시 보낸 말", true, true);
    assert_eq!(r["result"]["sent"], json!(true), "ⓕ 사람 재전송이 막혔다: {r}");
    std::thread::sleep(Duration::from_millis(200));
    paint_empty_prompt(&t);
    assert!(atomic_enter_written(&t), "ⓕ 사람 재전송의 Enter 가 써지지 않았다");
    assert_eq!(counts(&t).1, 0, "ⓕ 제출 뒤 사람 계수가 남았다");
}

/// 쓰는 도중 `phase` 단계에 들어서는 순간 창을 그리는 좌석 증명(에이전트 작업 길 · 결정론 — 시각 주입 없음).
struct PaintAtPhase {
    seat: std::sync::Weak<Surface>,
    phase: crate::agent_write::Phase,
}

impl PaintAtPhase {
    fn paint_if(&self, phase: crate::agent_write::Phase) {
        if phase == self.phase {
            if let Some(s) = self.seat.upgrade() {
                paint(&s, &DIALOG, 1, 8);
            }
        }
    }
}

impl crate::agent_write::Proof for PaintAtPhase {
    fn admit(&self) -> Result<(), crate::receiver::ProofLoss> {
        Ok(())
    }
    fn recheck(&self, phase: crate::agent_write::Phase) -> Result<(), crate::receiver::ProofLoss> {
        self.paint_if(phase);
        Ok(())
    }
    fn recheck_context(
        &self,
        phase: crate::agent_write::Phase,
        _ctx: &crate::agent_write::ProofContext<'_>,
    ) -> Result<(), crate::receiver::ProofLoss> {
        self.paint_if(phase);
        Ok(())
    }
}

fn paint_at_phase(t: &Arc<Surface>, phase: crate::agent_write::Phase) {
    *t.receiver_proof.lock().unwrap() = Some(Arc::new(PaintAtPhase { seat: Arc::downgrade(t), phase }));
}

/// 적색→녹색(검증 지적 5): 기계 길(`SubmitRefuse`) 응답이 **운영 빌드에서도** 결판을 기다려 거부 사실을 싣는다 — `sent:true`(호환) ·
/// `submitted:false` · `refused:"approval_screen"` · `refused_stage`. 시험 전용 동기 결판(`test_wait_settled`)을 끄고 잰다(= 운영 경로).
/// 거부 흔적의 요청 번호 = 응답 `request_id`. 창이 없으면 결판 칸을 싣지 않는다(종전 응답 그대로).
/// 종전: 응답 `{"sent":true,"request_id":…}` 뿐(검증 지적 5) · 운영은 저널 장벽까지만 기다렸다.
#[test]
fn b16fix_machine_refuse_response_reports_refusal() {
    let fx = fx("b16fix-machine-resp");
    let _x = pane(&fx, "worker-2", P + 3031);
    crate::agent_write::set_test_sync_settle(false);
    let t = agent_pane_settled(&fx, "worker-1", P + 3030);
    paint_empty_prompt(&t);
    paint_at_phase(&t, crate::agent_write::Phase::Submit);
    let r = atomic_send(&fx, Some(P + 3031), &t, "/clear", false, true);
    let ev = named(&fx, "input.refused_at_write");
    crate::agent_write::set_test_sync_settle(true);
    assert_eq!(r["result"]["sent"], json!(true), "호환: sent:true 는 둔다: {r}");
    assert_eq!(r["result"]["submitted"], json!(false), "거부 사실이 응답에 없다: {r}");
    assert_eq!(r["result"]["refused"], json!(cys::ERR_APPROVAL_SCREEN), "{r}");
    assert_eq!(r["result"]["refused_stage"], json!("before_enter"), "{r}");
    assert_eq!(ev.len(), 1, "{ev:?}");
    assert_eq!(ev[0]["payload"]["request_id"], r["result"]["request_id"], "거부 흔적의 요청 번호가 응답과 다르다");
    // 창 없음: 결판 칸 없음(제출됨).
    crate::agent_write::set_test_sync_settle(false);
    let u = agent_pane_settled(&fx, "worker-1", P + 3032);
    paint_empty_prompt(&u);
    *u.receiver_proof.lock().unwrap() = Some(Arc::new(crate::agent_write::PassThrough));
    let r = atomic_send(&fx, Some(P + 3031), &u, "/clear", false, true);
    crate::agent_write::set_test_sync_settle(true);
    assert_eq!(r["result"]["sent"], json!(true), "{r}");
    assert!(r["result"].get("submitted").is_none() && r["result"].get("refused").is_none(), "창이 없는데 거부 칸: {r}");
}

/// 적색→녹색(검증 지적 5 · 사람 길): 응답 `request_id` = 거부 흔적 `input.refused_at_write.request_id`(조각 3 화면이 어느 말인지 맞춘다).
/// 종전: 사람 길 응답에 요청 번호 없음 · 흔적에도 없음.
#[test]
fn b16fix_human_refuse_event_carries_request_id_of_response() {
    let fx = fx("b16fix-human-rid");
    let t = agent_pane_settled(&fx, "worker-1", P + 3040);
    paint_empty_prompt(&t);
    let r = atomic_send(&fx, None, &t, HUMAN_BODY, true, true);
    dialog_after(&t, 300).join().unwrap();
    assert!(!atomic_enter_written(&t));
    let rid = &r["result"]["request_id"];
    assert!(rid.is_string(), "사람 길 응답에 요청 번호가 없다: {r}");
    let ev = named(&fx, "input.refused_at_write");
    assert_eq!(ev.len(), 1, "{ev:?}");
    assert_eq!(&ev[0]["payload"]["request_id"], rid, "{ev:?}");
}

/// 적색→녹색(검증 지적 4 · 기계 길 · 결정론): 여는 울타리 바로 앞(Ctrl-U 정착 뒤)에 창이 서면 본문·Enter 0 · 응답 `refused_stage:"before_paste"`.
/// 종전: 붙여넣기 앞 탐침 없음 → 본문이 창에 들어가고 Enter 앞 탐침이 그때서야 거부.
#[test]
fn b16fix_machine_refuse_before_paste() {
    let fx = fx("b16fix-machine-paste");
    let _x = pane(&fx, "worker-2", P + 3051);
    let t = agent_pane_settled(&fx, "worker-1", P + 3050);
    paint_empty_prompt(&t);
    paint_at_phase(&t, crate::agent_write::Phase::OpenFence);
    let r = atomic_send(&fx, Some(P + 3051), &t, "/clear", false, true);
    assert_eq!(r["result"]["submitted"], json!(false), "{r}");
    assert_eq!(r["result"]["refused_stage"], json!("before_paste"), "붙여넣기 앞에서 거부하지 않았다: {r}");
    let partial = named(&fx, "surface.write_partial");
    assert_eq!(partial.len(), 1, "{partial:?}");
    assert!(partial[0]["payload"]["reason"].as_str().unwrap_or("").ends_with("paste_refused:approval_screen"), "{partial:?}");
    assert_eq!(named(&fx, "input.refused_at_write")[0]["payload"]["stage"], json!("before_paste"));
}

/// 적색→녹색(검증 지적 4 · 사람 길): Ctrl-U 정착 중(쓰기가 시작된 직후 — writer 의 Inject 표식이 선 순간) 창이 서면 붙여넣기·Enter 0 ·
/// 거부 흔적 stage `before_paste` · 남은 줄은 사람 몫(지적 1 과 같은 복원). 바이트 증거는 아래 기록기 시험과 writer 단위 시험(state.rs).
/// 종전: 정착 중 뜬 창에 붙여넣기 본문이 들어갔다(+100ms 점 · 검증 지적 4).
#[test]
fn b16fix_human_refuse_before_paste() {
    let fx = fx("b16fix-human-paste");
    let t = agent_pane_settled(&fx, "worker-1", P + 3060);
    paint_empty_prompt(&t);
    let r = atomic_send(&fx, None, &t, HUMAN_BODY, true, true);
    assert_eq!(r["result"]["sent"], json!(true), "{r}");
    let deadline = Instant::now() + Duration::from_secs(3);
    while !t.inject_track.busy_within(Duration::ZERO) {
        assert!(Instant::now() < deadline, "writer 가 쓰기를 시작하지 않았다");
        std::thread::sleep(Duration::from_millis(1));
    }
    paint(&t, &DIALOG, 1, 8);
    assert!(!atomic_enter_written(&t), "창 위에 Enter");
    let ev = named(&fx, "input.refused_at_write");
    assert_eq!(ev.len(), 1, "{ev:?}");
    assert_eq!(ev[0]["payload"]["stage"], json!("before_paste"), "붙여넣기 앞에서 거부하지 않았다: {ev:?}");
    assert!(counts(&t).1 > 0, "사람 몫 복원");
}

/// 바이트 증거(검증 지적 4 · 검증 좌석 기록기와 같은 방식): 좌석 = raw `cat` 기록기. Ctrl-U(0x15)가 PTY 에 닿는 순간 창을 그리면
/// 그 뒤 PTY 에 아무것도 오지 않는다(붙여넣기 0 · Enter 0) — 사람 길·기계 길 둘 다. 종전: `15` → 붙여넣기 → (Enter 거부).
#[test]
#[cfg_attr(not(unix), ignore = "좌석 명령이 POSIX 셸 문법")]
fn b16fix_paste_refused_when_dialog_rises_during_ctrl_u_settle_bytes() {
    let fx = fx("b16fix-paste-bytes");
    let _x = pane(&fx, "worker-2", P + 3071);
    for (i, human) in [true, false].into_iter().enumerate() {
        let out = fx.dir.join(format!("rx-paste-{i}.bin"));
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
        if !human {
            *t.receiver_proof.lock().unwrap() = Some(Arc::new(crate::agent_write::PassThrough));
            crate::agent_write::set_test_sync_settle(false);
        }
        paint_empty_prompt(&t);
        let (wt, wout) = (Arc::downgrade(&t), out.clone());
        let painter = std::thread::spawn(move || {
            let deadline = Instant::now() + Duration::from_secs(5);
            while Instant::now() < deadline {
                if std::fs::read(&wout).is_ok_and(|b| b.contains(&0x15)) {
                    if let Some(t) = wt.upgrade() {
                        paint(&t, &DIALOG, 1, 8);
                    }
                    return true;
                }
                std::thread::sleep(Duration::from_millis(1));
            }
            false
        });
        let r = if human {
            atomic_send(&fx, None, &t, HUMAN_BODY, true, true)
        } else {
            atomic_send(&fx, Some(P + 3071), &t, "/clear", false, true)
        };
        assert!(painter.join().unwrap(), "Ctrl-U 가 PTY 에 오지 않았다: {r}");
        std::thread::sleep(Duration::from_millis(1500));
        crate::agent_write::set_test_sync_settle(true);
        let got = std::fs::read(&out).unwrap_or_default();
        eprintln!("B16FIX-BYTES human={human} → {got:02x?} · 응답 {r}");
        assert_eq!(got, vec![0x15], "human={human}: Ctrl-U 정착 중 뜬 창에 붙여넣기·Enter 를 썼다: {got:02x?}");
        let _ = t.child.lock().unwrap().kill();
    }
}

/// 적색→녹색(검증 지적 2): Claude Code 2.1.325~326 번들 창 제목 3종(`Do you want to create …?` · `… overwrite …?` · `Would you like to
/// proceed?`)을 포함한 7종 창이 **이미 떠 있으면** 사람 표지 `clear_first + refuse_on_approval` 은 거부 · 쓰기 0(검증 `bv_pred_dialogs` 표).
/// 종전: 3종은 술어가 못 읽어 `sent:true` → Ctrl-U·붙여넣기·Enter(기본 선택 「1. Yes」).
#[test]
fn b16fix_refuse_on_approval_reads_all_seven_dialogs() {
    let fx = fx("b16fix-pred");
    let rule = "────────────────────────────────────────";
    let screens: Vec<(&str, Vec<&str>, u16)> = vec![
        ("bash-proceed", vec![rule, " Bash command", "   rm -rf build", " Do you want to proceed?", " ❯ 1. Yes", "   2. Yes, and don't ask again for rm commands", "   3. No", "", " Esc to cancel · Tab to amend"], 4),
        ("edit-make-this-edit", vec![rule, " Edit file", " src/a.rs", " Do you want to make this edit to a.rs?", " ❯ 1. Yes", "   2. Yes, allow all edits during this session (shift+tab)", "   3. No", "", " Esc to cancel · Tab to amend"], 4),
        ("write-create", vec![rule, " Create file", " src/new.rs", " Do you want to create new.rs?", " ❯ 1. Yes", "   2. Yes, allow all edits during this session (shift+tab)", "   3. No", "", " Esc to cancel · Tab to amend"], 4),
        ("write-overwrite", vec![rule, " Overwrite file", " src/a.rs", " Do you want to overwrite a.rs?", " ❯ 1. Yes", "   2. Yes, allow all edits during this session (shift+tab)", "   3. No", "", " Esc to cancel · Tab to amend"], 4),
        // 80칸 창에서 Claude(Ink)가 단어 경계로 접은 꼴(한 줄로 그리면 81칸이라 끝 「?」 가 다음 행 그리기에 덮인다).
        ("plan-exit", vec![rule, " Ready to code?", " Claude has written up a plan and is ready to execute. Would you like to", " proceed?", "", " ❯ 1. Yes, and auto-accept edits", "   2. Yes, manually approve edits", "   3. No, keep planning", "", " ctrl-g to edit plan"], 5),
        ("fetch", vec![rule, " Fetch", " https://example.com", " Do you want to allow Claude to fetch this content?", " ❯ 1. Yes", "   2. Yes, and don't ask again for example.com", "   3. No, and tell Claude what to do differently (esc)"], 4),
        ("ask-user-question", vec![rule, " 어느 쪽으로 할까요?", " ❯ 1. 가", "   2. 나", "   3. Type something.", "", " Enter to select · ↑/↓ to navigate · Esc to cancel"], 2),
    ];
    let mut bad = Vec::new();
    for (i, (name, rows, cur)) in screens.iter().enumerate() {
        let t = agent_pane_settled(&fx, "worker-1", P + 3100 + i as u32);
        paint(&t, rows, *cur, 9);
        let w0 = t.inject_track.wrote();
        let r = atomic_send(&fx, None, &t, HUMAN_BODY, true, true);
        std::thread::sleep(Duration::from_millis(1200));
        let wrote = t.inject_track.wrote() - w0;
        if r["error"]["code"] != json!(cys::ERR_APPROVAL_SCREEN) || wrote != 0 {
            bad.push(format!("{name}: 응답 {r} · PTY 쓰기 +{wrote}"));
        }
    }
    assert!(bad.is_empty(), "이미 뜬 창에 사람 말을 썼다:\n{}", bad.join("\n"));
}

/// 음성 대조(검증 지적 2 · 거짓 양성): 모델 답 본문·사람 입력의 같은 문장은 창이 아니다 — 쓰기 직전 화면 술어도, 데몬 승인 스캔
/// (`check_approvals` = 화면 **전량**에 패턴 · 그래서 새 패턴은 번호 선택 행 `❯ N.` 을 문장 바로 아래(가로줄을 넘지 않고)에 요구한다)도
/// 이 화면들을 창으로 읽지 않는다. 새 패턴 두 개는 **새 이름**이라 사용자 소유 agents.json(동명 디스크 우선)에도 합집합으로 닿는다.
#[test]
fn b16fix_new_dialog_patterns_ignore_prose_and_typed_answers() {
    let fx = fx("b16fix-prose");
    let embed: Value = cys::pack::PACK_ALL
        .iter()
        .find(|(r, _)| *r == "agents.json")
        .map(|(_, c)| serde_json::from_str(c).expect("임베드 agents.json"))
        .expect("임베드 agents.json");
    let pats: Vec<(String, regex::Regex)> = embed["claude"]["approval_patterns"]
        .as_array()
        .expect("approval_patterns")
        .iter()
        .map(|p| (p["name"].as_str().unwrap().to_string(), regex::Regex::new(p["pattern"].as_str().unwrap()).expect("정규식")))
        .collect();
    for want in ["file-write-permission", "plan-approval"] {
        assert!(pats.iter().any(|(n, _)| n == want), "임베드에 {want} 패턴이 없다");
    }
    let prose: Vec<(&str, Vec<&str>, u16, u16)> = vec![
        ("prose-create-pr", vec!["● Do you want to create a PR?", "  1. Yes", "  2. No", "", "────────", "❯ ", "────────"], 5, 2),
        ("prose-plan-list", vec!["● Would you like to proceed?", "", "  1. Option A", "  2. Option B", "────────", "❯ ", "────────"], 5, 2),
        ("typed-answer", vec!["● Do you want to overwrite the config?", "────────", "❯ 1. yes please", "────────"], 2, 16),
        ("typed-proceed", vec!["● Would you like to proceed?", "────────", "❯ 1.", "────────"], 2, 5),
    ];
    for (i, (name, rows, row, col)) in prose.iter().enumerate() {
        let t = agent_pane_settled(&fx, "worker-1", P + 3120 + i as u32);
        paint(&t, rows, *row, *col);
        assert!(!crate::governance::seat_approval_pending(&fx.daemon, &t), "{name}: 쓰기 직전 술어가 본문을 창으로 읽었다");
        let screen = t.parser.lock().unwrap().screen().contents();
        for (n, re) in &pats {
            if n == "file-write-permission" || n == "plan-approval" {
                assert!(!re.is_match(&screen), "{name}: 승인 스캔(화면 전량) 패턴 {n} 이 본문을 창으로 읽었다:\n{screen}");
            }
        }
    }
    // 양성 대조: 화면 전량(승인 스캔이 보는 글)에서도 창 3종은 잡힌다.
    let dialogs: Vec<Vec<&str>> = vec![
        vec!["● 작업 중", " Create file", " Do you want to create new.rs?", " ❯ 1. Yes", "   2. No"],
        vec![" Do you want to overwrite a.rs?", "   1. Yes", " ❯ 2. Yes, allow all edits", "   3. No"],
        vec![" Claude has written up a plan and is ready to execute. Would you", " like to proceed?", "", " ❯ 1. Yes, and auto-accept edits"],
        vec![" Do you want to", " write to src/a.rs?", " ❯ 1. Yes"],
    ];
    for (i, rows) in dialogs.iter().enumerate() {
        let t = agent_pane_settled(&fx, "worker-1", P + 3130 + i as u32);
        paint(&t, rows, 3, 4);
        let screen = t.parser.lock().unwrap().screen().contents();
        assert!(pats.iter().any(|(_, re)| re.is_match(&screen)), "창 {i} 를 승인 스캔이 못 읽는다:\n{screen}");
    }
}

/// 적색→녹색(검증 지적 6): 재검사 틱이 닫힌 agy 문 때문에 큐 Return 재전송 기록을 닫을 때 버스 흔적 1건 — 보류 경로
/// (`queue.submit_withheld_dropped` 사유 `agy_door_closed`)와 같은 꼴의 `queue.submit_retry_dropped`. 종전: 이벤트 0(stderr 한 줄뿐).
#[test]
fn b16fix_agy_door_close_of_retry_record_leaves_bus_trace() {
    if cys::agy_door::door_open() {
        eprintln!("건너뜀: 이 HOME 에서는 agy 좌석 문이 열려 있다(격리 HOME 에서 돌릴 것)");
        return;
    }
    let fx = fx("b16fix-agy-trace");
    let t = agy_swallowed_seat(&fx, P + 3140, "send");
    let step = step_at(&fx, &t, Instant::now(), 2_100);
    assert_eq!(step, "agy_door_closed");
    let ev = named(&fx, "queue.submit_retry_dropped");
    assert_eq!(ev.len(), 1, "{ev:?}");
    assert_eq!(ev[0]["payload"]["reason"], json!("agy_door_closed"));
    assert_eq!(ev[0]["payload"]["queue_entry_id"], json!("q-agy.1"));
    assert!(named(&fx, "queue.submit_retried").is_empty());
}
