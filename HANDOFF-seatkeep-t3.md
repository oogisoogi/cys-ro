# HANDOFF — TICKET=cysr-seatkeep-t3 (cysd 좌석 생성 경로 = 좌석 프로세스 손잡이 + seatkeep 경유 · 맥 · 노브 기본 끔)

- 가지 = `feat/seatkeep-t3`(← t2 `a48d36e1`) · push 0 · 설계 메모 = `docs/seatkeep/T3-DESIGN.md`
- master 지시: master#c125bc97(고칠 것 3: 잠금 2칸 = 노브 켬만 · `--end-on-controller-loss` · 출력 폭주 실측 / 답: rows·cols 수용 · 등록부 3파일 잔존 = T4) · master#fe07cc6a(D7 = 결정 B · SIGNAL target 칸)
- 시험대 = `~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t3/harness/`(t3life.py · t3a13.py · t3misc.py) · T2 시험대 사본 = `../t2copy/harness/`
- 격리 시험 실행기 = scratchpad `run_tests.sh <label> <cargo test 인자>`(CYS_* 제거 · HOME/XDG 임시 · CYS_SEATKEEP 만 통과)

## 상태(갱신 중)
(아래 「실측」 절을 채운다)
