# r6 재현 시험 「고치기 전 붉음」 원시 기록(TICKET=cysr-agy-door-r6)

- 바이너리 = 고치기 전 머리 73d1a72e 를 따로 뽑은 작업 트리에서 빌드(`git worktree add --detach` · 별도 target 폴더) ·
  하네스 = r6 의 acceptance.py(E20~E25 · E13 스크립트 발화 추가분 포함 · `AGY_ACCEPT_BIN_DIR` 로 바이너리만 바꿈)
- 실행 2026-11-12 03:34~03:45(새 바이너리 1회와 동시)
- 붉은 항목(고치기 전): E21(좌석 식별 오분류 · rpc·queued·cys send 모두 통과) · E20(원시 RPC surface.create — 가짜 agy 실제 기동 2→3) ·
  E25(agent_launch 기동 줄 — 가짜 agy 실제 기동 3→4) · E22(sh -c 위치 인자 — 문 판정 없이 지나감 · 하네스에선 pane 밖 ACL 이 뒤에서 막음) ·
  E23(sh review.sh 등록 rc 0) · E24(심링크 채널 rc 0) · E13(문 닫은 뒤 'sh review2.sh' 발화 — 가짜 agy 실제 기동 8→9)
- E22c 는 이 기록 뒤 판정 방식을 고쳤다(pane 밖 `cys run` 은 데몬 ACL 로 rc 1 — 문과 무관) → 지금 하네스는 「문 사유 없음 + 같은 argv 의 문 판정 rc 0」.
