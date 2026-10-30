# HANDOFF — TICKET=cysr-1111-adv4fix (2026-10-31)

가지 `fix/1111-adv4-fixes` ← 7ccab38c · 작업 폴더 `~/cys-terminal-src-wt/1111-adv4fix` · 로컬 커밋만.

## 끝난 것
- 754890ad = M5·M4(`javis_computer_control.py` · 시험 · 뮤턴트 M140~M145)
- 47b47318 = M2(`docs/RELEASE-ROLLBACK.md` §2·§2-b·§3·§4)
- 3a40f006 = M1(팩 py stdin=DEVNULL · `test_dept_tick_stdin` 전 팩 핀 + 무효 핸들 모의)

## 지금
master 【확인요청】 1차 수용. surface:1756 독립 확인 중(M12 이견 · 맥 stdin 표본 실행 포함). 그 FINDINGS 가 오면 고침 1회 — 그때까지 대기.

## 미완·주의
- 윈 실기 0(M1 = 맥 모의) · §2-b 리허설 0 · 체크리스트 3-8 정정 = master 병합 때.
- M12: 코드 읽기로는 재상승 가능 · rc 3 도달 경로 못 찾음(check.rs:454 · feed.rs:653·799 · cli.rs:356-376 · make-envelope.py:67). 실행 재현 안 함.
- M5 잔여: 끄기→다시 켜기 15분 안 = rotate 2회 가능.

## 재현
- 격리 실행: HOME 임시 · CYS_* 해제 · 시험에 따라 CYS_PACK_DIR·JAVIS_ROOT·CYS_PROBE_RUNS 지정.
- `python3 -m unittest test_dept_tick_stdin test_computer_control`(bin/tests) · `python3 tests/mut_computer_control.py --only M140,M141,M142,M143,M144,M145`.
- 함정: test_phoenix_c6_reap·H-CLT-1·2 는 HEAD 에서도 적색(이 기계 조건) · `_fake_seq` 인덱스는 프로세스 안에서 이어진다(`self.m._seq_chrome_running = 0`).
