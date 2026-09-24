# HANDOFF — v116-auto-equalize (창 열기·닫기 자동 좌우 균등 · cysr 1.1.6)

- 설계·성찰·적대 검토 경과·증거 = `docs/v116-auto-equalize/`(DESIGN.md 가 정본).
- ⚠ **bisect 때 b5d4bd52 건너뜀** — 새 시험 1건이 적색인 채 커밋됐다(적색 시험 · d207034f 에서 정정). 역사 재작성 안 함(master 판정 09-25).
- master 판정: D1 = C · D2 = A(메뉴 「아래에 새 창」 제거) · ⓒ 팔레트 「세로 분할」 제거 · ⌘⇧D 는 이름 없이 유지(오른쪽 분할과 같게 동작).
- 재는 명령: `cd ui && ~/.bun/bin/bun test` · 뮤턴트 `python3 docs/v116-auto-equalize/mutate.py <git archive 사본 폴더>` ·
  헤드리스 `DIST=ui/dist CHS=<chrome-headless-shell> bun docs/v116-ui-evidence/v116-headless.ts`(c18 = 이 티켓).
