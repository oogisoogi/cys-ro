# HANDOFF — TICKET=cysr-seatkeep-t3 (cysd 좌석 생성 경로 = 좌석 프로세스 손잡이 + seatkeep 경유 · 맥 · 노브 기본 끔)

- 가지 = `feat/seatkeep-t3`(← t2 `a48d36e1`) · push 0 · 설계 메모 = `docs/seatkeep/T3-DESIGN.md`
- master 지시: master#c125bc97(고칠 것 3: 잠금 2칸 = 노브 켬만 · `--end-on-controller-loss` · 출력 폭주 실측 / 답: rows·cols 수용 · 등록부 3파일 잔존 = T4) · master#fe07cc6a(D7 = 결정 B · SIGNAL target 칸)
- 시험대 = `~/axdev/terminal-ide-survey/2026-11-bench/seatkeep-t3/harness/`(t3life.py · t3a13.py · t3misc.py) · T2 시험대 사본 = `../t2copy/harness/`
- 격리 시험 실행기 = scratchpad `run_tests.sh <label> <cargo test 인자>`(CYS_* 제거 · HOME/XDG 임시 · CYS_SEATKEEP 만 통과)

## 상태(갱신 중)
(아래 「실측」 절을 채운다)

## 실측
### 커밋 · 시험 수
- 커밋: ① bda1f68e(손잡이 + 직접 PTY 옮기기) · ①' 98d03214(옮긴 자리 소스 핀 ⑦ · D7 시험기 좀비 · 선언) · ②③④ 942d6d7e · ba446e5d(Cargo.lock)
- 기준선(옮기기 전 a48d36e1 · 노브 없음): cysd 3224 통과 · 3 실패(native_publication 2 · pending_requests c8registry 1 = `Locked`) · 15 무시 · rc 101
- ① 트리 노브 끔: 3224 통과 · 6 실패 = native_publication 2(기준선과 같음) · pending_requests 1(`Locked` — 기준선과 다른 이름 · 같은 부류 흔들림) · 소스 핀 ⑦(옮긴 자리 · ①'에서 고침) · C8 핀(시험이 디스크 소스를 읽는 중에 ② 코드가 들어감 · 표 등재로 고침) · D7 시험기(좀비 = 산 것으로 셈 · ①'에서 고침)
- ② 트리 노브 끔(942d6d7e 직전 빌드): **3242 통과 · 2 실패(native_publication 2 = 기준선과 같음) · 16 무시** · rc 101
- seatkeep 단위: 30/30(T2 27 + 새 3: reap_marks_before_reaping · signal_target_leader_group_and_refusal · ensure_dir_is_race_safe_on_first_creation)

### 좌석 수명(master#c125bc97 ② · t3life.py · 릴리스 · results/t3life.jsonl)
| 노브 | cysd 내림 | 회차 | 좌석 SIGHUP 으로 끝남 | seatkeep 잔존 | 끝나기까지 ms | seatkeep 기록 사유 |
|---|---|---|---|---|---|---|
| 켬 | SIGKILL | 6 | 6/6 | 0 | 178~452 | controller_lost ×6 · 등록부 ended_controller_lost |
| 켬 | SIGTERM | 6 | 6/6 | 0 | 191~384 | controller_lost ×6 |
| 끔(직접 PTY) | SIGKILL | 6 | 6/6 | — | 74~200 | — |
| 끔(직접 PTY) | SIGTERM | 6 | 6/6 | — | 151~423 | — |
대조군(인자 없는 seatkeep = 자식 생존) = T2 `t2.py all` 의 조종자 SIGKILL 12회(아래 t2 재실행 줄).
