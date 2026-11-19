# T6 rotate·업데이터·판 처리 — 설계 메모 (TICKET=cysr-1116-seatkeep-1119 · 1단계 = 문서만 · 코드 0)

- 근거 설계: `~/axdev/master/reports/2026-11-11-cysr-holder-design/DESIGN.md` §1-3(rotate 순서) · §3-2 ③(입양 → 복원 제외) · §4-1~4-5(장부 밖 holder · 상한 · 사전 실행 · 판 불일치 · 봉인·업데이터) · §5 A1·A4·A6·A9·A13 · §6 T6 행 · §7-7·10·11.
- 앞 단계: T4(입양 · `docs/seatkeep/T4-DESIGN.md`) · T5(토큰 이음 · `T5-DESIGN.md`). 노브 = `CYS_SEATKEEP_ADOPT=1`(+ `CYS_SEATKEEP=1`) 기본 끔 — 이 단계의 변경도 노브 끔이면 종전 동작.
- 위험 = **고위험(업데이터)** → 독립 검증 좌석 + codex 1R. 비가역·비용: 없음(코드·시험만 · 격리 HOME) — 단 아래 D4(launchd 실측)는 사용자 launchd 영역에 임시 작업을 올리므로 master 판단.

## 0. 지금 실측한 사실(머리 4ba42e596 · 파일:줄 = 조사 + 직접 대조 ★표)

| # | 사실 | 근거 |
|---|---|---|
| F1 | `run_rotate` = ① `drain --verify` → ② 데몬 교체(맥 기본 레인 = `daemon install --takeover` · 그 밖 = identify pid 에 `kill -TERM`/윈 `taskkill /F`) → 5초 소켓 사라짐 대기 → identify ×3 → ③ `.pending-restore` → ④ `init-pack` → 자동 복원 안정 대기(최대 120초) → ⑤ `restore --include-master` → ⑥ 부서 순회. seatkeep·입양 인지 0줄 | `src/bin/cys.rs:23164-23350` |
| F2 ★ | 맥 기본 레인 takeover 의 pid 모를 때 폴백 = **`pkill -TERM -f MacOS/cysd`** — seatkeep 인자에 `--controller-exe <번들>/Contents/MacOS/cysd` 가 있어 **살아 있는 seatkeep 을 같이 죽인다**(좌석 SIGHUP) · 좌석 명령 인자에 그 문자열이 있어도 걸림 | `cys.rs:21173-21175` · `seat_proc.rs:435` |
| F3 | 그 밖 이름 일치 종료 = 없음(`factory_reset` 은 실행 파일 이름 정확히 `cysd` · 나머지는 pid) | 조사 §2 |
| F4 ★ | 맥 업데이터 교체 = `renamex_np(RENAME_SWAP)` 뒤 옛 번들을 **`.cysr.app.old-<seq>` 로 rename** → 살아 있는 seatkeep 의 실행 파일 경로가 옛 번들 자리로 옮겨짐 → 새 cysd 의 입양 신원 대조(`proc_pidpath` = `<지금 cysd 옆>/cys-seatkeep`)가 **어긋나 미결**(입양 못 함 · 자동 복원 보류) | `update/mac.rs:249-268` · `seat_proc.rs:548-565` |
| F5 | 업데이터 상태기계 S7 stop = `rotate --stop-only --txn` · S9 교체 · S10 start_new = `rotate --skip-drain --txn` · 실패 = 되감기(`rollback_from` · `start_old` · `rb_swap`) · S11 = 세대 정리(옛 번들 삭제 시점 = 실측 필요) | `update/runner.rs:55-107, 386-399` · `realops.rs:722-890, 1024-1044` |
| F6 | 앱 판 내림(holder 모르는 판으로) 전용 경로 없음 — 되감기(`rollback`)가 사실상 판 내림(새 판이 seatkeep 을 띄운 뒤 옛 판으로 되돌림) | 조사 §3 |
| F7 | watchdog 중복 처치 = 좌석 루트 pid(= 자식 pid)의 **자손**만 관측 → seatkeep(부모)은 관측·처치 밖 | `governance.rs:6066-6188` |
| F8 | 복원 = `system.topology` 의 `live`(역할 있는 surface) → 입양 좌석은 역할을 갖고 다시 등록되므로 `cys restore` 「이미 가동 중 — 건너뜀」 · 자동 복원 = 미결(역할 모름) 있으면 그 기동 통째 보류 · 역할 아는 미결 = 그 역할 생성 거절 | `cys.rs:26245-26316` · `handlers.rs:14109` · `seat_adopt.rs:563-595` |
| F9 | cysd 정상 종료(SIGTERM) 정리 = ledger 의 scoped 그룹만 kill · seatkeep 은 ledger 밖(setsid · 새 세션) → **살 것으로 추정(실측 없음 — T4 실물은 SIGKILL 만)** | `main.rs:1492, 1556-1558` · `cys-seatkeep/main.rs:777` |
| F10 | launchd plist = `KeepAlive` · `ThrottleInterval 10` · `AbandonProcessGroup` 없음 → unload 때 launchd 가 작업의 **프로세스 그룹**에 신호 — seatkeep 은 다른 세션·그룹이라 **살 것으로 추정(실측 없음)** | `launchd.rs:157-159` |
| F11 | seatkeep = 신호 처리기 없음(외부 TERM = 기본 종료 → PTY 마스터 닫힘 → 좌석 SIGHUP) · RELEASE = 좌석 그룹 SIGHUP(조종자 연결 필요) · cysd 는 RELEASE 를 안 보냄 | `cys-seatkeep/main.rs:1627-1652` |
| F12 | 기록 없는 산 seatkeep = 입양 못 함 → 미결(`no_record_live_keeper`) + 역할(env) 예약 · 정리 규칙 없음(T4 = T6 몫) | `seat_adopt.rs` adopt_one |
| F13 | CLI(`cys.rs`) seatkeep 인지 = 0곳 | grep |

## 1. 목표(합격 기준 · 원 설계 A1·A4·A6·A9·A13 중 맥 몫)

1. **A1 계획 교체 생존**: 입양 노브 켬 · `cys rotate` 6회 → 좌석 pid 같음 · 좌석 기록에 SIGNAL 0 · 교체 뒤 read-screen·send 성공 · 복원이 같은 역할을 또 띄우지 않음(작성자 하나 = A6 의 좌석 수 판정).
2. **업데이트 생존**: 업데이터 S7→S9(번들 rename)→S10 뒤에도 입양 성공(F4 해결) · S11 세대 정리 뒤에도 같음.
3. **A9 판 처리**: ⓐ 사전 실행 — 새 cysd 가 살아 있는 seatkeep 을 입양 못 하면 rotate 를 멈추고 옛 cysd 그대로(좌석 무변경) ⓑ 되감기·판 내림(입양 모르는 판으로) → 그 전에 seatkeep 전부 끝냄 → 옛 판 phoenix 가 복원 · 작성자 하나.
4. **pkill 폴백이 seatkeep 을 안 건드림**(F2).
5. **기록 없는 산 seatkeep 정리 규칙**(F12) + **holder 총수 상한**(§4-2).
6. A4(진짜 Claude 기억 유지)·A13(비용) = 실측 항목(이 단계 끝 보고에 숫자 · 판정선은 master 가 먼저).

## 2. 설계

### 2-1 rotate(F1·F2·F9)
- ② 폴백: `pkill -f MacOS/cysd` → **후보 pid 를 모아 실행 파일 이름이 정확히 `cysd` 인 것만** TERM(`pgrep -f` 대신 Rust 안에서 `proc_pidpath` 기준). seatkeep·좌석 명령 인자 오탐 제거. 노브 무관(언제나 이 방식 — 좌석을 잘못 죽이는 길은 노브 끔에서도 없어야 함 · 뜻 변화 = 오탐 제거뿐).
- ① drain: 입양 노브 켬이면 seatkeep 좌석은 교체를 넘겨 살므로 **[DRAIN] 저장 확인 실패가 rc 를 낮추지 않게** 분리(원 설계 §2-1 표) — 재부팅 대비 보험이라 보내기는 유지.
- ⑤ 복원: 입양 좌석 = topology live → 이미 건너뜀(F8) · 변경 0 · 회귀 시험만.
- F9·F10 은 실측으로 닫는다(e2e 새 모드 `rotate`: 격리 HOME 에서 실제 `cys rotate --skip-drain` = 비기본 레인 → `kill -TERM pid` 길). launchd 길은 D4.

### 2-2 사전 실행(A9ⓐ · 원 설계 §4-3 ①)
- 새 실행 파일 `cysd --adopt-check --json`(점검 모드 · 잠금·소켓·입양 쓰기 0): 상태 폴더의 seatkeep 등록부를 읽어 산 seatkeep 마다 「이 cysd 가 입양할 수 있나」(실행 파일 신원 규칙 2-3 · 등록부 단계 · 핵심 판) → `{"adoptable": n, "blocked": [{"skid", "reason"}]}`.
- rotate ② 앞(입양 노브 켬일 때만): 새 판 cysd 로 점검 → `blocked` 가 있으면 rotate 중단 rc ≠ 0 · 옛 cysd 무접촉 · 「강제 진행」 옵션은 두지 않음(원 설계 = 관리용 종료 경로 + 작성자 종료 확인 뒤 복원 — T1 임대가 없어 지금은 못 함 → 중단만).
- 업데이터 S7 앞에도 같은 점검(새 번들의 cysd 로) — 막히면 S7 전에 멈춤(되감기 불요 단계).

### 2-3 업데이트 뒤 seatkeep 신원(F4 · 결정점 D1)
- 지금 규칙 = 「pid 의 실행 파일 경로 == 지금 cysd 옆 cys-seatkeep」. 번들 rename 뒤 옛 seatkeep 은 `.cysr.app.old-<seq>/Contents/MacOS/cys-seatkeep` 로 보인다(S11 정리 뒤 = 지워진 파일 — `proc_pidpath` 반환값 실측 필요).
- 권고안(확신도 중): 신원 = ⓐ 경로가 지금 cysd 옆 **또는** 정식 번들의 형제 `.cysr.app.old-<seq>` 안 `Contents/MacOS/cys-seatkeep`(정확한 꼴) ⓑ 서명 번들이면 **코드서명 신원이 지금 cysd 와 같은 팀**(SecCode 정적 대조 · 미서명 개발 빌드 = ⓐ 경로만) ⓒ 지워진 파일이면 = 미결(종전). seatkeep 쪽 확인(조종자 실행 파일 = 같은 경로·요구사항)은 정식 경로의 새 cysd 를 그대로 받는지 실측(T2 확인이 경로 기준이면 정식 경로라 통과 예상).
- 대안: 업데이터가 S9 전에 seatkeep 을 끝냄(= 업데이트는 좌석을 안 넘김 · 단순) — 박사님 체감 목표(「판 교체에도 좌석이 산다」)를 못 채움 → 권고 안 함.
- 핵심 판(WELCOME·HELLO 고정 칸): 옛 seatkeep(이 판) ↔ 새 cysd(다음 판) = 같은 `CORE_VERSION` 이면 입양 · 다르면 사전 실행이 막음(2-2).

### 2-4 되감기·판 내림(A9ⓑ · F5·F6)
- 업데이터 되감기(`rollback_from`)와 `start_old` 직전: 되돌아갈 옛 판이 **입양을 모르는 판**(판 표지 = 옛 번들 build-info 의 판 번호 < 첫 입양 판 · 또는 옛 cysd `--adopt-check` 미지원)이면 **seatkeep 전부 관리용 종료**: 등록부 pid → 출생 시각·실행 파일 신원 확인(2-3) → SIGTERM(F11 · 프로토콜 무관 = 핵심 판 불일치에도 됨) → 끝남 확인(pid 사라짐 · 상한 5초 → SIGKILL). 그 뒤 옛 cysd 가 phoenix 로 복원(작성자 하나 = seatkeep·좌석이 먼저 끝났으므로).
- 같은 판끼리 되감기(둘 다 입양 앎) = 끝내지 않음(옛 cysd 가 입양).
- 업데이터 밖 판 내림(사람이 옛 앱을 직접 띄움) = 잔여 위험(원 설계 §7-10) — 이 단계는 막지 않고 기록.

### 2-5 기록 없는 산 seatkeep 정리 규칙(F12 · 결정점 D2)
- 생기는 때 = 생성 직후 기록 쓰기 전 cysd 가 죽은 극히 짧은 창 · 기록 쓰기 실패(T4 가 임시본을 자식 기동 전에 써서 거의 막음).
- 권고안 ⓐ(확신도 중): 기동 입양 뒤 그 seatkeep 이 **조종자 없음 ∧ 기록 없음**이면 관리용 종료(2-4 와 같은 신원 확인 → SIGTERM) + `seat.adopt_skipped{no_record_live_keeper, ended}` · 역할(env) 예약은 끝난 뒤 풀림 → 그 역할은 phoenix 가 topology 로 복원(대화 이어받기). 근거 = 번호·제목·메타를 모르는 좌석은 사람에게 안 보이고 입력도 못 받는 고아라 살려 둘 이익이 없고, 역할 예약이 복원을 막는 손해만 남는다.
- 대안 ⓑ: env(역할·cwd·명령) 로 새 번호 좌석으로 입양 — 기록 없는 칸(메타·세션·관문 보류)을 비운 채라 「반쯤 되살린 좌석」 위험 · 코드 큼.
- 대안 ⓒ: 지금처럼 미결 유지(사람 판단) — 박사님 손이 드는 단계라 4-5 원칙(완전 자동화)에 어긋남.

### 2-6 holder 총수 상한(§4-2)
- 새 seatkeep 좌석 생성 때 등록부 산 seatkeep 수 ≥ 상한이면 그 좌석만 **직접 PTY 로 강등**(생성 실패 아님 · 경고 사건) — 상한 값 = 기존 워커·좌석 상한과 같은 값을 기본(실측 A13 뒤 master 가 정함).

### 2-7 watchdog·이름(F7)
- 변경 0 · 회귀 시험 1(seatkeep 은 처치 관측 밖 · 좌석 루트 pid = 자식 pid 유지).

## 3. 시험(수용)

| 축 | 시험 | 종류 |
|---|---|---|
| A1 | e2e `rotate` 모드: 실제 `cys rotate --skip-drain` ×6(격리 · 비기본 레인 = TERM 길) · 좌석 pid 같음 · SIGNAL 0 · read-screen·send · 같은 역할 좌석 수 1 | e2e |
| pkill | 폴백 후보 거르개 단위(실행 파일 이름 `cysd` 만) + 가짜 seatkeep(인자에 `MacOS/cysd`) 생존 | 단위 + e2e |
| 업데이트 | 격리 번들 두 벌(복사본)로 rename 교체 흉내 → 새 cysd 입양 성공 · 옛 번들 지운 뒤 = 미결(또는 2-3 실측 결과대로) | e2e(`update` 모드) |
| A9ⓐ | 핵심 판을 바꾼 시험 빌드(환경값 분기 1빌드) → `--adopt-check` blocked → rotate 중단 · 좌석 무변경 3/3 | e2e |
| A9ⓑ | 되감기 흉내(입양 모름 판 = 노브 끔 cysd) 전에 관리용 종료 → 좌석 끝남 확인 → 복원 1 · 작성자 하나 3/3 | e2e |
| 정리 규칙 | 기록 없는 산 seatkeep(시험에서 기록 삭제) → 기동 뒤 끝남 · 역할 예약 풀림 · 복원 1 | e2e |
| 상한 | 상한 = 1 로 두 번째 좌석 = 직접 PTY 강등 + 사건 | 단위/e2e |
| 뮤턴트 | 폴백 거르개 끔 · 신원 규칙 옛 번들 갈래 끔 · 사전 실행 무시 · 되감기 종료 끔 · 정리 규칙 끔 · 상한 끔 | 러너 |
| 노브 끔 | 위 갈래 전부 종전(rotate·업데이터 경로 무변 — 폴백 거르개만 언제나) | 기존 시험 + 바이트 비교 |
| A4·A6·A13 | 진짜 claude 좌석 기억(암호어) rotate 5회 · 작성자 수 · 비용(좌석 1·5·20) — 숫자 보고 | 실측(격리 프로필 · D5) |

## 4. 결정점(master)

- **D1 업데이트 뒤 신원**: 권고 = 2-3 ⓐ+ⓑ(옛 번들 자리 허용 + 같은 팀 서명) / 대안 = 업데이트는 좌석을 안 넘김(S9 전 종료).
- **D2 기록 없는 산 seatkeep**: 권고 = ⓐ 관리용 종료 + 복원 / 대안 ⓑ 새 번호 입양 · ⓒ 미결 유지.
- **D3 범위 쪼개기**: 권고 = T6a(rotate 폴백·drain 분리·A1 실측·정리 규칙·상한·사전 실행) → T6b(업데이터 신원·되감기 종료·업데이트 e2e) 두 매듭 · 각각 【확인요청】 + codex 1R. 근거 = 업데이터 갈래가 원작자 상태기계(`update/*`)를 건드려 고위험 축이 다르다.
- **D4 launchd 실측(F10)**: 사용자 launchd 영역에 임시 작업(`launchctl submit` · 시험 라벨 · 격리 HOME 데몬)을 올려 unload 뒤 seatkeep 생존을 잰다 — 실사용 데몬 무접촉이지만 사용자 영역 등록이라 허락 필요. 대안 = 원리(F10)만 기록하고 VM 실기 단계로 미룸.
- **D5 A4 진짜 claude 좌석**: 격리 프로필 claude 를 시험 좌석에 띄워 rotate 5회(계정 토큰 소모 소량) — 허락 필요 여부.

## 5. 하지 않는 것
- T1(대화 임대)·강제 진행 rotate · 윈도우(T7) · 노브 기본 켬 판단(T8 숫자 뒤).
