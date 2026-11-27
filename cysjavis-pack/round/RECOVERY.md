# RECOVERY.md — 재기동 복원 프로토콜 (골격)

> 재부팅·세션 만료·컨텍스트 클리어 후 master가 가장 먼저 실행하는 절차.

1. **SESSION_STATE.md를 읽는다** — 현재 위치·지시 대장·노드 상태표·미해결 게이트·다음 액션.
2. `round/*_TODO.md` 를 읽어 각 노드의 미완 작업을 파악한다.
3. memory/MEMORY.md 색인에서 관련 장기기억을 회상한다.
4. `git log --oneline | head` 로 커밋 체인을 대조한다.
4-b. **배달 원장 다이제스트** — `BOOT_SNAPSHOT.md` 가 있으면 그것을, 없으면 MASTER_DIRECTIVE
   '귀속 판별' 절 절차로 직접 조회한다. 내 발신·수신 기계 배달을 **기억이 아니라 원장으로** 복원한다.
5. 데몬 확인: `cys ping` (죽었으면 `cysd &`). 세션(PTY)은 데몬 소유라 데몬이 살아 있으면
   surface들은 그대로다 — `cys list`로 확인.
6. 죽은 노드를 재기동·재각성한다: `cys launch-agent --role <역할> --agent <cli>`.
   ⚠ 먼저 `cys status --json` 의 `daemon.auto_restore` 를 본다 — `running`·`retry_wait`·`held` 인 동안은 데몬 자동 복원이 아직 좌석을 되살리는 중이니 기다린다(그 밖 값 = `done`·`off`·없음이면 바로 진행). 그 뒤에도 죽어 있는 노드만 띄운다 — 먼저 띄우면 저장 대화 대신 새 대화로 뜬다(`cys launch-agent` 도 복원 중이면 띄우지 않고 rc 95 로 알린다).
7. **미해결 게이트부터** 작업을 재개한다. 완료된 단계를 다시 하지 않는다.
