# HANDOFF — TICKET=cysr-1111-winchrome

가지 fix/1111-win-chrome-job · 기준 060cb75b · 설계 = DESIGN-winchrome.md

## 끝난 것
- 데몬 Job 은 평소처럼 이탈 불가. 크롬·재시작 대기만 데몬이 스폰 1회 동안 이탈을 허용해 띄운다(`src/job_exit.rs` · RPC `system.spawn_outside_job` · 숨은 CLI `cys spawn-outside-job`).
- 재시작 대기가 Job 밖이라 그 자식 rotate 도 밖이다 → rc·ledger·빚 정리까지 간다.
- ★r4 1번 실패 뒤 C안(팩만): 윈에서 크롬이 켜져 있고 도구가 Job 밖에서 켠 기록이 없으면 재시작을 예약하지 않고 순서를 안내한다. 좌석에서 띄운 크롬을 살리는 수리는 **아니다** — 도구가 그 크롬을 죽이지 않게 할 뿐이다. 근거 = `R4-FAIL1-HYPOTHESES.md` · 설계 §3-4.
- M3: 윈은 창 1개일 때만 닫는다. 창 수는 최상위 창 전수. 실패 문장을 사실별로 분리.

## 게이트(맥 · 격리 HOME · CYS_* 해제)
C안(팩만 · Rust 0): 팩 test_computer_control 194/0 · test_dept_tick_stdin 8/0 · 뮤턴트 155 KILLED(생존 0 · r4 관문 19건 포함) · lane-parity --strict rc 0 · secret-scan --all 깨끗. Rust 를 다시 재지 않았다(변경 0). 아래는 C안 앞 기록이다.

lib 1142/0 · cys 736/0(기본 스택 · CI 동조건) · cysd 3222/0(1e35ac5f · 그 뒤 제품 Rust 변경 없음) · update_drainhold_e2e 4/4 · win-typecheck 오류 0(1e35ac5f) · 팩 test_computer_control 152/0 · test_dept_tick_stdin 8/0 · 뮤턴트 125 KILLED · lane-parity --strict rc 0 · secret-scan --all 깨끗. bun = ui 무변경이라 생략. `tests/win_job_exit.rs` 실행 = 미측정(CI windows-health 첫 실행).

## 함정
- ⚠ `cys spawn-outside-job` 을 clap 최상위 `Command` 변형으로 넣지 말 것 — 파서 프레임이 커져 aid_s5_cli_tests 가 기본 2MB 시험 스레드에서 넘친다(CI 41141594121 · `cys.rs` main 의 갱신 3동사 주석과 같은 이유). main 앞단에서 처리한다.
- ⚠ BREAKAWAY_OK 를 상시로 켜지 말 것 — 동봉 Git Bash 가 모든 자식에 이탈 flag 를 붙인다(소스 핀 `breakaway_bit_stays_inside_this_module`).
- 윈 실 프로세스 시험 `tests/win_job_exit.rs` 는 맥에서 0건이다. 컴파일은 win-typecheck 로 확인했고 **실행은 CI windows-health 가 처음이다**.
- 팩만 새것이고 데몬이 옛것이면 `--probe` 가 실패해 크롬을 닫지 않고 안내한다(rotate 뒤 정상).

## 윈 실기 항목(r5 · 코드가 달라진 것 먼저)
모든 재현은 **크롬 프로세스 0개에서** 시작한다(도구 크롬이 남아 있으면 좌석에서 띄워도 Job 밖 크롬이 쓰인다). Job 소속은 `in-caller-job`(jobq.ps1)으로 재고 anyjob 은 근거로 쓰지 않는다.

- r5-1. 1번 재시험: 좌석에서 크롬 + `chrome-enable --seat-restart now`(윈 재현과 같은 호출) → rc 6 · `seat_restart_manual:true` · ledger 에 `seat_restart_scheduled` 없음 · rotate 없음 · 크롬 그대로 · 순서 문장. `--seat-restart auto` + 키 꺼짐(S1)은 rc 0 · 나머지 같음.
- r5-2. S3 대조: 크롬 0개 → 좌석에서 창 1개 → 연결 파일 등록 지움 → chrome-enable → 닫고 다시 켬 · 예약 1 · rotate rc ∈ {0,21,25} · 크롬 **생존**. `chrome-enable.json` 의 `chrome_outside.pid` 가 크롬 본체(`--type=` 없는 chrome.exe)인지 확인. 다르면 스폰 pid 가 곧 끝나는 프로세스라 S3 도 안내로 떨어진다(안전하지만 자동 재시작이 사라진다).
- r5-3. 12번 개정: 창 2개 → 안내(예약 0) → ⋮ 「종료」 → ↻ → 시작 메뉴에서 켬 → chrome-enable → 「새로 켜신 것을 확인」 · 안내 되풀이 없음 · 빚 없음(`seat_guided_daemon`·`pending_seat_restart` 없음). 그 크롬이 in-caller-job=False 이고 다음 ↻ 뒤에도 **생존**하는지.
- r5-4. 탭 복원 재기: 안내 순서를 따른 뒤 ③ 으로 켠 크롬의 창·탭(강제 사망 때는 2창 2탭 → 1창 1탭이었다). 크롬 「시작 그룹」 설정에 따라 다를 수 있어 설정값도 적는다.
- r5-5. 6·10 회귀: 6번은 크롬 0개 또는 S3 상태에서 · 10번은 대기를 죽인 뒤 크롬 0개에서(켜진 크롬이 있으면 이제 예약 대신 안내가 나온다).
- r5-6. `chrome-disable --seat-restart auto` + 좌석 크롬 → 예약 0 · ↻ 안내. 크롬 0개 → 예약 1.

아래 r4 항목 중 1번은 위로 대체됐고, 나머지는 판이 바뀌었으니 필요한 것만 다시 본다. 4번 「창 1개 → 닫고 다시 켬」은 연결 파일을 새로 만들 때만 일어난다.

## 윈 실기 항목(r4)
1. ~~R5 A: 좌석에서 띄운 크롬 + chrome-enable → 좌석 재시작. 크롬 생존.~~ **r4 실패 · 재현 2/2**(S8 · cysd 종료 0.7초 뒤 크롬 0개 · 2창 2탭 → 1창 1탭). r5-1·r5-2 로 대체.
2. R5 B: 크롬 꺼 둠 + chrome-enable. 크롬이 떴다면 재시작 때 닫히는지 기록(설계 §4 · 미수리).
3. R5 C: 작업 스케줄러로 띄운 크롬 대조 — 생존 유지.
4. R5b: 창 2개 → 닫지 않음 · 「크롬 창이 2개」 문장. 창 1개 → 닫고 다시 켬. 최소화·다른 데스크톱 창도 세는지.
5. 백그라운드 실행 켠 크롬 창 1개 → 「크롬 창은 닫혔지만」 문장.
6. rotate rc·ledger: `~/.cys/computer-control/ledger.jsonl` 의 seat_restart_scheduled → seat_restart_rotate 순서.
7. 관리자 좌석에서 대기가 뜨는지(`cys spawn-outside-job --probe` rc 0) · 크롬·대기가 cysd Job 밖인지.
8. 재시작 대기가 CYS_BIN·CLAUDE_CONFIG_DIR 로 턴 종료를 읽는지(busy 로 900초 끝나지 않는지).
9. R5c: 크롬이 켜졌다 곧 꺼지는 경우 → failed · 다음 호출 60초 안 = 다시 안 켬 · 3회 뒤 「그만두었습니다」 · 창이 반복해서 뜨지 않음. 곧 꺼질 때까지 걸린 시간 기록(안정 창 5초 조정 근거).
10. 죽은 예약: 재시작 대기를 죽인 뒤 chrome-enable → 「이미 예약돼」 없이 새로 예약 · 대기가 살아 있으면 「이미 예약돼」 유지.
11. R5-B(크롬 0개) rc·ledger `seat_restart_rotate` · pending_seat_restart 없음.
12. 창 2개 → 안내 + 좌석 재시작 예약 → 메뉴 「종료」 뒤 다시 켜고 chrome-enable → 「새로 켜신 것을 확인」 · 크롬 안 닫힘 · 빚 없음.
13. chrome-enable 이 크롬을 닫은 직후 끊겼을 때 다음 호출이 켜기를 갚는지 · cysd 작업 폴더가 설치 폴더인지(F13) · 트레이 종료 뒤 탭 복원(F6).
14. CI 로그 `[measure]` 줄: BREAKAWAY_OK 상시 + Git Bash 자식 결과.

## 공개 노트 문장(윈 · 1안)
**크롬 연결을 켤 때 크롬이 꺼질 수 있는 경우, cysr 가 먼저 안내합니다.** 안내가 나오면 크롬 오른쪽 위 ⋮ 메뉴의 「종료」로 크롬을 닫고, cysr 위쪽 ↻ 재시작을 누른 뒤, 크롬은 시작 메뉴나 바탕 화면에서 켜 주세요. cysr 가 켠 크롬은 cysr 가 다시 시작해도 켜져 있습니다.

(마지막 문장은 r5-2 생존 확인 뒤에만 쓴다. 옛 문장 「그대로 켜져 있습니다」는 r4 1번으로 거짓이 확인돼 폐기했다.)

증류: memory `win-job-breakaway-msys-auto` · `chrome-window-close-session-loss`.

## 1.1.12 BACKLOG 등재 문장(master 처분 · 이 가지는 동결 · 코드 무변경)

근거 원문 = 독립 확인 `CHROMEVERIFY-FINDINGS.md`(F4·F5·F10·F13·G2 = 이 가지 · D-1~D-4 = 1760 c94ff414). 전부 드문 조건이고 r4 를 막지 않는다.

- **D-1 안 닫힌 크롬을 빚 청산으로 처리**: 빚을 디스크에 쓴 뒤 크롬이 실제로 닫히기 전에 도구가 끊기면, 다음 호출이 그 크롬을 「켜져 있습니다」로 치고 빚을 지운다. 이후 안내가 없다. 고치려면 「닫는 중」 빚 상태를 하나 더 둔다.
- **D-2 살아 있는 대기가 Job 안 크롬을 닫음**: `cmd_chrome_enable` 에서 「이미 예약돼 있습니다」 판단이 Job 안 크롬 판단보다 앞이다. 대기 생존 + 이탈 스폰 실패가 겹치면 그 대기가 크롬을 닫는다. `in_job` 을 먼저 보고, 살아 있는 대기는 빚을 내려 멈추게 한다.
- **D-3 시작 시각을 못 읽으면 Job 안 크롬 표지가 풀림**: pid 는 아는데 시작 시각을 못 읽으면 `_in_job_chrome_alive` 가 없는 것으로 치고 재시작을 예약한다(안전하지 않은 쪽). 시작 시각 None 은 `bool(running)` 으로 판단하고, `_proc_start` 의 None 을 「죽음」과 「모름」으로 나눈다.
- **D-4 끊김 반복 때 재시도 상한 무효**: 빚 갚기는 켠 **뒤에** 횟수·시각을 적는다. 끊김이 반복되면 상한 3회·간격 60초가 듣지 않는다. 켜기 전에 횟수·시각을 디스크에 쓴다(F3 의 나머지 절반).
- **F4 허용 구간 틈**: Job 이탈 허용 구간(스폰 1회 · 크롬 켜기 1회당 최대 2구간) 안에 좌석 msys 가 스폰하면 그 자식이 Job 을 빠져나가거나, 구간 끝과 겹치면 그 스폰이 거부된다. 없애려면 좌석 Job 비트를 건드리지 않는 별도 대행 경로가 필요하다.
- **F5 이름 위장**: 허용 목록의 `chrome` 은 실행 파일 이름만 보므로 `chrome.exe` 라는 이름의 임의 파일이 지난다. 보안 경계가 아니라 수명 관리 오용 방지 수준이다(`-` 로 시작하는 argv[1] 거부는 1.1.11 에서 고침).
- **F10 claude 가 띄운 크롬**: 크롬이 꺼져 있을 때 `claude -p --chrome` 이 띄운 크롬은 Job 안이라 좌석 재시작 때 경고 없이 닫힌다. r4 R5-B 로 재현 여부를 재고 재현되면 고친다.
- **F13 대기의 작업 폴더**: 재시작 대기·크롬이 데몬의 작업 폴더를 물려받아, 대기는 데몬 사후 최대 15분 그 폴더를 쥔다. 데몬 폴더가 설치 폴더면 09-10 사고 꼴이다. r4 에서 cysd 작업 폴더를 재고 필요하면 고정한다.
- **A안 Job 소속 측정**(R4-FAIL1 §6): cysd 가 `in_our_job` 으로 크롬 pid 소속을 답하고, chrome-enable 은 Job 안 크롬이 창 1개면 닫고 밖에서 다시 켠다. 좌석 크롬을 실제로 살리는 수리이고 1.1.11 C안의 「시작 메뉴 크롬도 자동 재시작을 잃는다」를 없앤다. D-2 를 함께 넣는다. Rust·r5급 윈 실기가 필요하다.
- **대기의 rotate 직전 재확인**: C안은 예약할 때만 본다. 크롬이 꺼진 채 예약된 뒤 좌석에서 크롬을 켜면 대기가 그대로 rotate 한다. 앞서 뜬 살아 있는 대기도 같다(D-2). A안의 RPC 로 대기가 직전에 묻는다.
- **rotate 관문**: 앱 ↻ · 좌석에서 친 `cys rotate` 는 chrome-enable 을 거치지 않아 좌석 크롬을 안내 없이 죽인다(윈 실측 = 탭 손실). rotate 앞에 Job 안 크롬 확인이 필요하다.
- **바깥 Job 의문**: 도구 크롬은 in-caller-job=False 인데 anyjob=J 다. 설계 §2-3 의 바깥 Job 에 남은 것일 수 있다. 그 Job 의 정체와 닫힐 때 크롬이 어떻게 되는지 미확인이다(r4 A2 에서 rotate 는 견뎠다).
- **↻ 인지 오판**: 안내 뒤 데몬이 사용자의 ↻ 말고 다른 이유(충돌·갱신)로 바뀌어도 빚을 지운다. 그 경우 좌석 재시작 안내가 한 번 빠진다.
- **G2 겹친 대기의 기록 충돌**: 측정이 한 번 실패하면 대기가 둘 뜨고, 앞 대기의 `owe` 가 뒤 대기의 예약 기록을 지운다. 뒤 대기는 앞 대기 성공 뒤 멈춘다. 예약별 식별자가 필요하다.
