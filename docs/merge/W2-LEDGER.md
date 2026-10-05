# W2-LEDGER — 1.1.8 W 결함 묶음 ② 팩 python·훅·부서 (TICKET=cysr-118-w2-pack · 가지 w2/pack-118)

> 브리프 = master#64aeea16(2026-10-06 02:26) · 결함 정본 = master/reports/cysr-118-plan/BACKLOG-118.md §W · 원칙 = user-input-natural-language-not-fixed-dictionary.
> 측정 = 격리 래퍼(짧은 HOME·시험마다 새 CYS_PACK_DIR · 디버그 바이너리 = cys-118-merge 같은 커밋 3ea970bb) — 실 ~/.cys·/Applications 쓰기 0.

| # | 항목 | 판정·처방 | 바뀐 파일 | 시험 | 소요 |
|---|---|---|---|---|---|
| D14 | SESSION_STATE 정본 경로 분기 | 정본 = **레인 팩 round/**(지침 MASTER §0③·§9 · cys todo-path · cycle 저장 검증과 같은 자리) · 단일 해소 `javis_session.session_state_path` + 셸 쌍둥이 `_lib.sh cys_session_state_path` · 소비처 orchestra(next-action·gate-status·셀프테스트) · preflight C61 · state_snapshot · inject-context(lead 좌석) · save-state(lead 좌석) · 옛 자리(<cwd>/_round) 기록은 정본이 설치 골격일 때만 정본으로 복사(백업 · 옛 파일 무접촉 · 삭제 0 · 결과 1줄 주입) · `adopt --retire` 는 명시 개명만 · member·역할 미상 좌석은 종전(프로젝트 _round = 그 프로젝트 기억) · 맥 실측: 우리 맥 cys 레인은 pack/round 19,048B(07-27)만 · ~/_round 는 .state_log 미끼뿐(SESSION_STATE 0) · axdev/master 는 cmux master 고유(팩 밖 · 무관) | bin/javis_session.py · hooks/_lib.sh · hooks/inject-context.sh · hooks/save-state.sh · bin/javis_orchestra.py · bin/javis_preflight.py · bin/javis_state_snapshot.py | 신규 test_session_state_canon(A~F 30) · test_state_snapshot_root E3(자리만 정본으로) · test_inject_context_role_seat 12c(hub lead 출처 경로 한 줄 정규화 d14_to_canon) · test_todo_shared_constants(+javis_session) · 관련 11건 초록 | 약 60분 |
