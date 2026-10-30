# DESIGN-winchrome — 윈도우 크롬 다시 켜기 · 좌석 재시작 Job 동반 사망 수리

TICKET=cysr-1111-winchrome · 기준 060cb75b · 작성 2026-10-31

## 1. 문제

| 실측(윈 r2 · 판 7ccab38c) | 결과 |
|---|---|
| R5 A — 좌석에서 띄운 크롬 | cysd·rotate·크롬 11개가 같은 표본에서 소멸 · rotate rc 없음 · ledger 에 seat_restart_rotate 없음 · pending_seat_restart 잔존 |
| R5 C — 작업 스케줄러로 띄운 크롬 | cysd·rotate 소멸 · 크롬 11개 생존 |
| R5b — 크롬 창 2개 | before=[1,null] 로 1개로 셈 · chrome_not_quit · 「그대로 두었습니다」(창 하나는 이미 닫혔다) |

원인: cysd 는 자기 자신을 KILL_ON_JOB_CLOSE Job 에 넣는다(`src/bin/cysd/main.rs:1240` · `state.rs::winjob`). 그 뒤 생기는 자손은 전부 그 Job 에 들어간다. rotate 가 `taskkill /PID <cysd> /F` 로 데몬을 내리면 Job 핸들이 닫혀 Job 안의 크롬·재시작 대기·rotate 자신이 죽는다.

## 2. 후보 비교

기준: ① 데몬이 죽으면 자식이 정리된다(Job 의 본래 목적) ② 이탈은 명시한 스폰만 ③ 권한 혼재(관리자 Highest/Limited) ④ 바깥 Job 안의 cysd ⑤ 맥 무영향.

| 안 | ① 결박 유지 | ② 명시 스폰만 | ③ 권한 | ④ 중첩 | 비고 |
|---|---|---|---|---|---|
| ⓐ BREAKAWAY_OK 상시 + 해당 스폰만 이탈 flag | **깨짐** | **깨짐** | 무관 | 문서상 성립 | 아래 2-1 |
| ⓑ 작업 스케줄러 일회 작업(`update::win_task`) | 유지 | 유지 | **문제** | 성립 | 아래 2-2 |
| ⓒ 데몬이 스폰 한 번 동안만 BREAKAWAY_OK **(채택)** | 유지 | 유지 | 무관 | 문서상 성립 | 아래 2-3 |

### 2-1. ⓐ 를 버린 이유 — 동봉 Git Bash 가 이탈을 스스로 쓴다

msys2-runtime `winsup/cygwin/spawn.cc`(동봉 PortableGit 의 msys-2.0.dll 계열 · 태그 msys2-3.5.7 판독): 프로세스가 Job 안에 있고 그 Job 의 LimitFlags 에 `JOB_OBJECT_LIMIT_BREAKAWAY_OK` 또는 `SILENT_BREAKAWAY_OK` 가 있으면 **모든 자식 생성에 `CREATE_BREAKAWAY_FROM_JOB` 을 자동으로 붙인다**(PCA 서비스 우회 목적).

즉 Job 에 이 비트를 상시로 켜면, 좌석의 Git Bash(훅·스크립트)가 띄우는 python.exe 등이 전부 Job 을 빠져나간다. Job 의 본래 목적(09-10 참가자 기계의 고아 python3.exe → 설치 폴더 삭제 불가)을 그대로 되돌리는 회귀이고, 티켓 기준 「이탈은 명시한 스폰만」도 깨진다. 동봉 판의 실제 동작은 `tests/win_job_exit.rs::measure_…` 가 CI 로그에 `[measure]` 줄로 남긴다.

### 2-2. ⓑ 를 버린 이유

대조군 R5 C 가 생존 근거이고 저장소에 `win_task` 도 있지만, 등록 작업은 `RunLevel=LeastPrivilege` 다. 관리자(Highest)로 뜬 cysd 를 Limited rotate 가 `taskkill` 하면 거부될 수 있다(박사님 노트북 = 항상 관리자 · RunLevel 혼재는 1.1.12 N1 로 열려 있음). 좌석 환경변수도 잃고, 시스템에 작업 객체를 남겼다 지워야 한다.

### 2-3. 채택 — ⓒ 데몬 대행 + 순간 허용

- 평소 Job = `KILL_ON_JOB_CLOSE` 만(지금과 같다). msys 의 조회에도 「이탈 불가」로 보인다.
- 좌석은 스스로 이탈하지 못한다. `cys spawn-outside-job` → RPC `system.spawn_outside_job` 으로 **데몬에게 맡긴다**.
- 데몬은 허용 목록을 검사하고(`cys::job_exit::validate` · `chrome <chrome.exe> --restore-last-session` · `seat_restart <python> javis_computer_control.py seat-restart-wait …` · 환경변수 6종), 잠금 안에서 비트 켬 → 스폰(`ChildLifetime::Survivor`) → 비트 끔. 끄기는 Drop 이 맡아 스폰 실패에도 꺼진다.
- 비트를 켜는 코드는 `src/job_exit.rs` 뿐이다(소스 핀). SILENT_BREAKAWAY_OK 는 쓰지 않는다.
- rotate 는 재시작 대기의 자식이라 대기가 Job 밖이면 함께 밖이다. 그래서 cysd 를 죽인 뒤에도 끝까지 돌아 rc·ledger·빚 정리까지 간다.
- 대기는 데몬의 자식으로 뜨므로 좌석 신원·토큰이 없다(앱 ↻ 와 같은 조건). 필요한 값은 인자(`--surface`)와 허용 환경변수(`CYS_BIN` 등)로 넘긴다.

**권한**: 이탈은 특권이 필요 없고 자식 토큰은 데몬과 같다. 지금 좌석에서 띄우는 크롬과 같은 수준이며 rotate 는 cysd 를 내릴 수 있다.

**중첩 Job**: MS 「Nested Jobs」 — 직속 Job 이 이탈을 허용하면 이탈을 불허하는 Job 을 만날 때까지 올라간다. cysd 의 직속 Job 은 우리 Job 이므로, 바깥 Job 이 불허해도 우리 Job 만 빠져나오면 된다(R5 는 우리 Job 이 닫혀 죽은 것). `escape_works_under_outer_job_that_refuses_breakaway` 가 잰다. Job 편입 실패(강등 모드)로 데몬이 바깥 불허 Job 에 직접 있으면 flag 가 거부되므로 `spawn_detached_daemon` 처럼 이탈 없이 1회 재시도한다(응답 `outside_job:false`).

**폴백(옛 데몬·거부)**: 크롬을 닫기 **전에** `--probe` 로 확인한다. 안 되면 크롬을 닫지 않고 안내한다. 이미 닫힌 뒤 켜기만 실패하면 좌석에서 직접 켠다(재시작 때 닫힐 수 있어도 안 켜진 것보다 낫다 · ledger `chrome_open_in_job`). 재시작 대기 스폰이 실패하면 좌석 안에서 띄우지 않는다 — 기존 문장 「예약에 실패했습니다 … ↻」 + 빚 유지.

**맥**: `platform() == "win"` 분기뿐 · RPC 는 맥에서 오류를 낸다 · 맥 스폰 인자 불변(시험 고정).

**남은 위험(ⓒ)**: 허용 구간(스폰 1회 · 수 ms) 안에 좌석의 msys 가 스폰하면 그 자식 1개는 Job 을 빠져나갈 수 있고, 구간 끝과 겹치면 그 스폰이 거부될 수 있다. 크롬 켜기 1회당 최대 2구간이라 드물지만 0 은 아니다.

## 3. M3 — 창이 여럿이면 안내로

전수 닫기를 고르지 않았다. 크롬 `SessionService::WindowClosing`(chrome/browser/sessions/session_service.cc): 다른 창이 남아 있으면 닫힌 창을 세션에서 **바로 지우고**, 마지막 창만 복원 대상으로 남긴다(메뉴 「종료」는 이 경로를 타지 않는다는 주석). 창을 하나씩 닫으면 `--restore-last-session` 이 마지막 창만 되살린다. 윈에서는 탭 수를 셀 길이 없어 손실을 잴 수도 없다. 「열린 탭은 그대로 돌아옵니다」를 지킬 수 없으므로 닫지 않는다.

- 창 수 = 최상위 창 전수(EnumWindows · `Chrome_WidgetWin_1` · 보임 · 소유자 없음 · 제목 있음 · 도구창 아님 · chrome.exe). 1 일 때만 닫는다.
- 2 이상 → 「크롬 창이 N개 열려 있어 닫지 않았습니다 … ⋮ 메뉴의 「종료」」 · 0·모름 → 「몇 개인지 확인하지 못해 닫지 않았습니다」. 재시작 빚은 유지.
- 창은 닫혔는데 프로세스가 남으면(백그라운드 실행) → 「크롬 창은 닫혔지만 …」. 「그대로 두었습니다」는 창이 남아 있을 때만.

## 4. 범위 밖 · 기록만

- **R5 B 경로**: 크롬이 꺼져 있을 때 `claude -p --chrome` 이 크롬을 띄우면 그 크롬은 Job 안이다. 사용자의 기존 탭은 없지만 좌석 재시작 때 닫힐 수 있다. 실기 R5 B 로 재고, 재현되면 1.1.12.
- **좌석에서 직접 친 `cys rotate`**: Job 안이라 지금도 rc 를 못 남긴다. 앱 ↻·작업 스케줄러 경로는 해당 없다.
- 크롬 관리자 권한 실행 여부는 이 수리로 달라지지 않는다.
