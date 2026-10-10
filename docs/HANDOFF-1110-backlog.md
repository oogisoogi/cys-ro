# HANDOFF — TICKET=cysr-1110-backlog (1.1.10 결함·시험 백로그 묶음)

- 가지: `fix/1110-backlog` (기준 `4f660dfb` = merge/v0.14.43) · 좌석 318(surface:1317 · worker-4) · 2026-10-10 08:04 ~ 09:1x
- 원칙대로 항목 1개 = 커밋 1개(+시험). 정정·추가 지시로 갈라진 항목은 `4b`·`6b`·`7b` 로 따로 커밋했다.
- 시험은 전부 **격리 HOME**(좌석 `CYS_*` 전부 제거 + 빈 임시 HOME)에서 돌렸다. 실 홈 `~/.cys/pack` 에는 쓰지 않았다(읽기 2회: 설치된 디렉티브의 수정 지점 확인).

## 0. 한눈에

| # | 항목 | 커밋 | 결과 |
|---|---|---|---|
| 1 | test_7c 대기 조건 | `e12dcd28` | 「파일 있음」→「개행으로 끝나는 내용」 · 재현 시험 3 · 뮤턴트 = CI 와 같은 IndexError |
| 2 | hdiutil 재시도 | `061e041a` | 실패마다 사유 출력 + 1회 재시도 · 2회 실패 = 적색(건너뛰기 0) |
| 3 | T3 벽시계 여유 | `6deb9b4a` | 원인은 이미 174c49a6 이 제거 · 남은 여유 1초 → 2초(문턱 = 정답·뮤턴트 한가운데) |
| 4 | 팩 시험 목 우회 | `5e445ef2` | dept_create_progress 는 이미 수리됨(재확인) · 같은 TODO 의 2종째 test_hook_fail_log 수리 |
| 4b | session-start 자동기동 봉인 | `61443cb9` | usage-register·claim-role 도 `CYS_NO_AUTOSTART=1` (master#4ec83d4b) |
| 5 | CrossLockRace 재현 | (커밋 없음) | 맥 50회 · 부하 동반 · 적색 0 · 윈 CI 반복 = master |
| 6 | LOCK_WAIT_S 판단 | `970bd443`(문서) | 판정 요청 → master A+B 채택(#09eeb379) |
| 6b | 상한 5.0 + 버림 횟수 신호 | `9b2d9b5a` | `counsel.dropped` · `counsel.dropped_writes.<N>` · 0 이면 줄 없음 |
| 7 | D-U6 선택 도구 등급 | `1fb91fe2` | 새 등급 INFO · 수리 지점 = `add()` 한 곳 |
| 7b | D-U6 정정 | `be682ae4` | 부재만 INFO · C19 자기검증 실패 = WARN 유지(master#2089a445) |
| 8 | rate_limited 확증 | (건너뜀) | 실물 = CSO active-monitor(git 밖 · 가동 중) · 설계 메모 §3 (master#772edf4b) |
| 9 | 전역 restore 잠금 | `0b665b06` | `<restore-claims>/.lock` OS 배타 잠금 · 16 스레드 × 20판 소실 0 |
| 10 | phoenix 공유 HOME 격리 | `644bb133` | 하네스 데몬 = 전용 임시 홈 · f1 58/63 → 63/63 · 실 홈 무접촉 단언 |
| 11 | 알림 수신 멱등 키 | `d81c640b` | master#c6c3784a: 경로 A(app-notify.json)로 한정 · 이미 멱등 → 코드 0 · 재투입 시험 1 · 뮤턴트 적 |
| 12 | 팩 디렉티브·성찰 보고서 수정 지점 | (코드 0) | §2 에 파일:행 |

전체 회귀(이 가지 HEAD · 격리 HOME): `cargo test --bin cys` **602/0** · test_javis_counsel 75/0 · test_trust_seed 276/0 · test_update_publish 104/0(skip 14 = 기존 조건) · test_hook_fail_log 11/0 · session_start_r31·session_start_hook OK · run_bootstrap_health 162 PASS / 2 FAIL(H-CLT-1·2) = 기준(HEAD 5e445ef2 임시 작업트리)과 FAIL 줄 전문 동일 · phoenix c6 7/7 · e2e 7/7 · f1 63/63 · w3 58/58 · w2_untomb 8/8 · sandbox_state_isolation OK · seat_revival 15/15 · secret-scan(변경 15파일) clean. 팩 회귀 묶음(javis_preflight·javis_counsel 을 부르는 시험 38파일 · 위에서 따로 센 4개 제외) = **38/38 녹**(test_preflight_phase1_checks 는 격리 env `JAVIS_ROOT`·`CYS_PROBE_RUNS` 를 주어야 도는 시험 · 주고 26/0).
  - ★전제 보강(master#e38309e4): 같은 묶음에 `test_agora_known_authentic.py` 까지 넣어 돌리려면 `CYS_AGORA_ZIP_DIR=<게시 zip 폴더>`(그 파일 머리 주석의 실행 줄) 가 필요하다 — 없으면 설계상 FAIL(skip 금지). 내 38 은 그 파일을 **뺀** 수(42 − 따로 센 3 − 그 파일 1)이고, master 게이트 재검의 38/38 은 그 env 를 준 실행이다.

## 1. 항목별 — 재현 → 수리 → 재현 0 → 뮤턴트

**1 test_7c** — 원인: formation 스텁이 `open(…,'a')` 로 파일을 만든 뒤 쓰기가 닫히기 전, 빈 파일을 시험이 읽음(`splitlines()[-1]` IndexError). 수리: `_wait_formation_argv` = 개행으로 끝나는 내용이 생길 때까지(상한 50 × 0.1초 그대로). 재현 시험 = 빈 파일을 먼저 만들고 0.3초 뒤 줄을 씀. 뮤턴트(종전 대기) = 같은 IndexError 2건.

**2 hdiutil** — `hdiutil_retry(args, partial=…)`: 실패하면 rc·stderr 를 즉시 출력하고, 실패한 create 가 남긴 반쪽 dmg 를 지운 뒤 1회만 다시. 두 번 다 실패하면 사유 2줄을 붙여 적색. 건너뛰기 없음. 뮤턴트(재시도 0) 적.

**3 T3 벽시계** — 【관측】 4.66초 적색의 원인(경과·끝내기 실소요가 판별 구간에 들어감)은 174c49a6 이 이미 고쳤다. 남은 문제는 여유가 1초뿐이라는 것(맥 실측 정답 3.00 · 문턱 4.0 · 뮤턴트 5.07). 축척을 키워(상한 12 · 띄우기 4 → 몫 7) 문턱을 정답(7.0)과 뮤턴트(11.07)의 한가운데(9.0)에 두었다 = 양쪽 여유 2초. 시험 시간 +4초.

**4 목 우회** — test_dept_create_progress 는 publish-docs-118 ⑦ 에서 이미 수리됨(좌석 env 그대로 실행해도 105/0 · 새 cysd 0). 같은 TODO 줄의 2종째 test_hook_fail_log(hf-ss-*) 는 미수리였다: 격리 실행 1회마다 `/usr/local/bin/cysd` 고아 1(부모 1 · HOME = 시험 폴더). 원인 = 시험이 좌석 env 와 PATH 의 실 `cys` 를 물려줌 → session-start 훅의 usage-register·claim-role(봉인 없음)이 형제 cysd 를 띄우고, 그 데몬이 시험 팩에 `hooks/core_inject.py` 를 깔아 시험 전제(조립기 없음)까지 깨짐. 수리 = 상속 `CYS_*` 화이트리스트 + PATH 선두 목 cys(rc 2)·cysd + 케이스 폴더를 쥔 프로세스 0 단언.

**4b 봉인(제품)** — session-start.sh 의 usage-register(clear 아닌 갈래)·claim-role 재대조를 surface-role·reclaim-role 과 같은 서브셸 봉인으로. 인자·순서 불변. 계약 핀 갱신: r31 SS-2·9b·10c, hook 18e(뒤집힘) + 18f 신설(모든 봉인이 서브셸 안). 실 cys 종단(목 없음) = 새 cysd 0.

**5 CrossLockRace** — 맥 50회(yes × 16 부하) 50/50. 시험은 10-07 counsel-race 가 이미 「버린 쓰기」와 「쓴 뒤 사라진 줄」을 가르게 고쳤다.

**6·6b 상담소 쓰기 상한** — 판단 문서 `docs/design/counsel-lock-wait-1110.md`(맥 7조건 실측 · 윈 인용 · 선택지 A/B/C). master 채택 A+B 구현: `LOCK_WAIT_S` 5.0 · 버리면 `counsel/dropped.tally` 1바이트 → 다음 성공 쓰기가 잠금 안에서 떼어 세고 신호 1줄. C(비동기 큐) = 1.1.11 후보(아고라 클라이언트 수집 계약 변경 필요).

**7·7b D-U6** — `_optional_tool_grade`(preflight `add()`): C19 「pack/bin 누락」만 INFO · 자기검증 실패·실행 불가 = WARN(실결함) · C21 부재 = INFO · C24 부재·판독불가·설치 보류 = INFO, 설치 뒤 OC 키·MCP 등록 WARN 유지. 상태 문자열을 읽는 곳은 preflight 자신뿐(실측). 신호 계약은 (op, error_code) 만 싣기 때문에 C19 실패 **문구**는 신호에 못 싣는다(preflight 출력·detail 에만).
집계 불일치(신호 fail 3 ↔ 함대 표 fail 1)는 자연 해소되지 않는다: 함대 표 = `cys doctor --json`(Rust 17항목) · 신호 = preflight C행(80여) — 계기가 다르다.

**9 전역 restore 잠금** — 획득(만들기 → 치우기 → 만들기)·해제(읽기 → 지우기)를 `<restore-claims>/.lock` 의 `File::lock`(유닉스 flock · 윈 LockFileEx) 안에서. 잠금 실패 = 진다(resume 끔). 획득 중 해제는 잠금 재진입 없는 내부판(같은 프로세스에서 두 번째 핸들로 잠그면 스스로 멈춘다). 뮤턴트(잠금 제거) = 「잠금 쥔 동안 대기」·「16 스레드 승자 1·소실 0」 둘 다 적 → 잠금 없으면 경합이 실제로 난다.

**10 phoenix 공유 HOME** — 재현: 같은 HOME 에서 c6 → e2e → f1 = f1 58/63(S1~S5 records resume mode). 원인: 하네스 데몬이 부른 쪽 HOME 을 물려받아 `$HOME/.cys/pack` 에 팩(23항목)을 깔고, f1 은 팩 env 가 없으면 그 `agents.json` 을 읽는다. 수리: 하네스 데몬 HOME = 전용 임시 홈(`PHOENIX_HARNESS_HOME` 으로 고정 가능) · 팩 경로 env 미상속 · `real_home_untouched()` manifest 단언(c6·e2e) · f1 은 import 전에 전용 임시 홈. 수리 뒤 같은 HOME 순차 = 7/7 · 7/7 · 63/63 · 공유 HOME 에 `.cys` 생성 0.

## 2. 대기·판정 요청

- **11 알림 수신 멱등 키 — 종결**(`d81c640b`). 정의 출처가 없어 【질문】(09:02) → master#c6c3784a 가 경로 A(앱 갱신 알림 `app-notify.json` · `last_notified_result_id`)로 한정. 이미 멱등(`updnotice::plan` 이 닫힌 result_id 는 표시 안 함 · 롤백 실패만 설계상 하루 1회)이라 코드 0 · 시험 `same_result_id_delivered_twice_is_shown_once`(ok·rollback_ok·installed_revoked 각각 · 같은 id 를 다른 바이트로 재투입 + 하루 넘김 = 표시 1) · 뮤턴트(닫힌 id 검사 끔) 적 · cys-app --bins 289/0. B(상담소 수신)·C(cysd 큐) = 범위 밖.
  app 시험 준비 = 실 디버그 바이너리를 `src-tauri/binaries/{cys,cysd}-<triple>` 로 복사 + 빈 resources·runtime·ui/dist(전부 git 무시) · 끝나고 지웠다.
- **12 수정 지점(별도 티켓 · 코드 0)**:
  - 팩 디렉티브 §6-9 불변식 5(b)⑶: 설치 팩 `directives/WORKER_DIRECTIVE.md:179`(「⑶제출 판정 yes」 → 「submitted yes 또는 queued∧verdict_by=session_jsonl_nonce」) + 같은 파일 `:236`(§6-12 「nonce·대상·제출판정·시각 4요건」 같은 뜻으로). ⚠ 이 저장소의 팩 원본 `cysjavis-pack/directives/WORKER_DIRECTIVE.md`(277줄)에는 §6-9 가 없다 — 설치본은 합성 결과이므로 합성기 원본 위치를 먼저 확인해야 한다.
  - 한주 성찰 보고서 「주인 이해 회복」 절: jarvis-agora 저장소(데스크 main 9529f73) `agora/counsel.py:1126` `WEEKLY_PROMPT_ADDENDUM`(절 작성 지시 3항목 · 5줄 상한 · 왕초보 말투) + `:1271` `_weekly_report_md`(보고서 절 배치). 팩이 아니라 데스크 코드다.

## 3. 설계 메모 — 8 rate_limited 확증(master#772edf4b · 적용 = CSO 유지보수 창 · master 집행)

1. 확증 조건 = HEALTH streak ≥ PERSIST **그리고** `cys usage-accounts --json` 의 해당 계정 rate(5h) ≥ 밴드(60).
2. 유휴 「무진전」 단독으로는 confirmed 금지 — rate 판독 불가·밴드 미만이면 CANDIDATE 유지(사유에 「rate 교차 미충족」).
3. 실물 = CSO `cso-active-monitor.sh` HEALTH 블록(990~1002행 · git 밖) · 시험 = 같은 폴더 `test-cso-active-monitor.sh` 에 오탐 재현(5h 2~8% + 유휴) → 0 · 진짜 429 + 5h ≥ 60 → confirmed 2케이스.

## 4. 관찰(수정 0)

- 윈 C19 FAIL 원문은 신호에 없다(신호 계약 = 코드만) — Win master 수집 신호/로컬 preflight 출력에서 확인 필요.
- 좌석 PATH 에 `~/.npm-global/bin` 누락(ps eww 실측): role `worker` 좌석 1314·1315 = 있음 · 번호 붙은 `worker-N` 좌석 1316·1317·1318·1320 = 없음.
- `javis_orchestra.py:433` self-test 의 `cys status --json` 이 데몬 없는 HOME 에서 형제 cysd 를 낳는다(격리 실행 1회 = 고아 1 · 거둠). preflight C19 가 이 self-test 를 부른다 — 4b 와 같은 꼴.
- `run_bootstrap_health.py` 가 `tests/` 아래 `X:\Prog Files\javis_bootstrap.py/hook-errors.log` 를 남긴다(기준 판도 같음 · 지움).
- 다른 좌석의 고아 cysd 1(08:50 · 작업 폴더 `.wt/cys-oss-scanner`) — 손대지 않음.
- master 발신 2건(#772edf4b · #09eeb379)이 원장에 `submitted: queued` 로 남아 있다(재조회 1회 동일). 둘 다 내 질문·판정 요청에 대한 답이라 이행했다.
- 하네스 임시 홈(`phoenix-harn-home-*`)은 시험 뒤 지우지 않는다(데몬이 아직 쓰는 중일 수 있음 · 시스템 임시 폴더).

## 5. 재현 명령

```bash
STRIP() { env | grep -o '^CYS_[A-Z0-9_]*' | sed 's/^/-u /'; }
ISO() { env $(STRIP) HOME=$(mktemp -d) "$@"; }
cd cysjavis-pack/bin/tests
ISO python3 -m unittest test_trust_seed test_javis_counsel test_update_publish test_hook_fail_log
ISO python3 test_session_start_r31.py; ISO python3 test_session_start_hook.py
cargo build --bin cys --bin cysd     # phoenix c6·e2e 는 target/debug 바이너리를 쓴다
H=$(mktemp -d); for t in test_phoenix_c6_reap.py test_phoenix_e2e_replacement.py test_phoenix_f1_production_path.py; do env $(STRIP) HOME=$H python3 $t | tail -1; done   # 같은 HOME 순차
cargo test --bin cys restore_claim
```
