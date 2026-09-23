# HANDOFF — v1.1.5 10차 통합 = 정밀 디버깅 차단 결함 묶음 수리 (TICKET=v115r4-dbg)

- 브랜치 `fix/v115r4-dbg` ← `fd356c06`(9차 절단 · D7⑴ r7 까지) · 작업 좌석 surface:987 · 2026-09-23 15:45~
- 범위: master 브리프 `master/briefs/2026-09-23-v115r4-dbg-integ.md`(D1 #1+#2 · D2 R2) + 편입 통보
  #3 R12(master#095c3b31 · 보강 #7517197f) · #4 D10(#724f5754) · #5 D3 #F1(#ce0f6261 · 995 산출 #63c2dd9c) ·
  #7 D11(#e41254cc) · #8 D4 #1(#d12d76b2) · #9 F4(#7e38c3d5) · F5·D4 #2·D4 #3(#17d3c912) — 확정 12건.
- ⛔판번 bump·push·태그·절단 = 하지 않았다(master 소관). 라이브 `~/.cys`·앱·데몬 무접촉(시험은 전부 격리 HOME).

## 1. 결함과 수리

| 결함 | 증상 | 원인 | 수리(파일) |
|---|---|---|---|
| D1 #1 | ＋부서마다 약 34초 헛대기 | `cys-dept` 가 「이미 떠 있나」 사전 확인에 대기 함수 `ready()`(핑 120회)를 썼다 | 사전 확인 3자리(launch·allocate·create · rotate 는 launch 재귀)를 `alive()`(핑 1회)로 (`cys-dept`) |
| D1 #2 | 앱 ＋부서 응답이 편성 끝날 때까지(역할당 최대 200초) 안 옴 | 편성 백그라운드 서브셸이 호출자 stdout/stderr 를 물려받아 앱 `cmd.output()` 의 EOF 가 늦음 | 서브셸 자신의 표준 입출력 절단 `) </dev/null >/dev/null 2>&1 &` (`cys-dept` formation_ensure_async) |
| D2 R2 | ↻·갱신·재부팅 복원이 /clear **이전** 대화를 되살림 | resume 핀이 첫 세션에 1회 고정 → topology session_id 영속 → `claude --resume <옛 id>` | 등록 경로(SessionStart 훅 재등록)는 세션 교체를 추종 · 휴리스틱 발견만 1회 핀 (`src/bin/cysd/usage.rs` collect_for) |
| D2 R12 | 신규 설치 첫 master 「교육 부서 만들어 줘」 → `Unknown skill: dept-by-chat` · 갱신 사용자는 영구 | claude 는 세션 시작 때 스킬 목록을 고정하는데, 스킬 링크를 만드는 주체가 마스터 선언 체인의 사후 `preflight --fix` 뿐(좌석 06:45:36 < 링크 06:46:09 · 복원 경로엔 선언이 없어 링크 영영 없음) | ①좌석 spawn 직전 `javis_preflight.py --wire-seat`(cysd `state.rs`) ②`cys init-pack`(앱 갱신의 `--no-install-hook` 포함)도 같은 배선 1회(`src/bin/cys.rs`) |
| D10 | 갱신 레인 첫 「부서 만들어 줘」 → 「dept-1 데몬 기동 실패」 · 부서 cysd 고아 생존 · 등록 삭제 | 기동 **뒤** 대기도 `ready()`(≈12초) — 부서 첫 부팅의 팩 첫 설치(478파일 · VM 22초)보다 먼저 포기 · 실패 분기는 등록만 지우고 데몬은 안 끔 | `boot_wait`(상한 120초 · 진행 신호 cys.lock → 팩 파일 수 → .pack-version → cys.sock 이 움직이면 계속 · 30초 정지/데몬 사망이면 조기 실패) + `boot_fail_teardown`(방금 띄운 데몬 TERM→KILL 회수를 **확인한 뒤에만** 등록 원복 · 못 끄면 등록 유지) (`cys-dept` 3자리) |
| D3 #F1 | 옛 CLI 링크가 있는 기계에서 부서 데몬·팩이 **옛 판**(.pack-version 1.0.2 · 디렉티브 해시 불일치 · acl.json.new 재발) | `cys-dept` 머리가 `$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin` 을 호출자 PATH **앞**에 끼워 `/usr/local/bin/cysd`(옛 판 링크)가 자기 판을 이김 | 보강 경로 **말미 append** · `CYS_CYSD_BIN`·`CYS_CYS_BIN` 1순위(없을 때만 `command -v`) · 틱 `_spawn_create`·`find_cysd` 가 명시 전달 · 데몬/앱 공용 spawn env(`lib.rs spawn_env_pairs_from_process → self_bin_pairs`)가 자기 exe_dir 형제를 명시 전달 |
| D11 | 두 번째 부서부터 「네」 불포착(갱신 레인) | 부서 preflight 의 훅 등록기가 공유 계정(본부 ~/.cys/claude)의 본부 훅을 레거시 규칙으로 지우고 부서 경로로 갈아 끼움 → 본부 dept-chat-inject 소실 | `_discover_isolation_block`: 부서 팩 ∧ 계정 dir **= 본부 계정 dir(팩 부모/claude · realpath)** → 등록 대상 [] + 사유 (`javis_preflight.py` · 995 patch 적용 후 판정 교정 890167cd — §5) |
| D4 #1 | 맥 신규 설치 매 기동 「Claude Code CLI 없음」 오경보 | 진단 agent-detect 가 GUI PATH(~/.local/bin 없음)로 which claude — 좌석 PATH 와 불일치 | agent-detect 명령에 `inject_runtime_path`(좌석과 같은 규약) (`src-tauri/src/main.rs` · 996 patch 무수정) |
| F4 | 「네 만들어 주세요」류 동의가 거절·기타로 | 분류기가 부분일치 | classify_answer — 낱말 전부 사전 안일 때만 · 핵심어 규칙 · 섞임·물음표 = other (`javis_dept_request.py` · 995 patch 무수정) |
| F5 | 「교육부 만들어 줘」에 절차 안내 없음 | 셸 선거름·파이썬 판정이 「부서/팀」 낱말만 봄 | 셸 case 상위집합 + `dept_intent()`(이름 꼴 …부·…팀·…과 + 생성·닫기 동사 · 일반어 26 제외) (`dept-chat-inject.sh`·`javis_dept_request.py` · 995 patch 무수정) |
| D4 #2 | 1280=11px · 1024/800=68px 창 바닥(클로드 입력줄) 잘림 · 800 에서 버튼 4개 못 누름 | 상단바가 버튼 글자 세로 쪼개짐으로 49px 로 부풀었는데 #body-row 는 고정 38px 를 뺌 | 상단바 한 줄 고정 높이 + 좁으면 가로 스크롤 + 버튼 nowrap + daemon-info 말줄임 (`ui/src/style.css` · 996 권고안 무수정 · tauri minWidth 는 대안 patch 전용이라 불요) |
| D4 #3 | 승인 대기 「0」 빨간 배지 상시 노출 | `.badge` 의 display 가 UA `[hidden]` 을 이김 | `.badge[hidden]{display:none}` (`ui/src/style.css`) |

## 2. R12 설계 — 왜 이 자리인가

- **자리 = `src/bin/cysd/state.rs` `create_surface_with_env`**(좌석 spawn 직전 · 좌석 토큰 주입 앞). VM 증거상 master
  claude(5373)의 부모 = cysd(5017) 직접이라 `javis_boot_node.py` 경로로는 master 좌석을 못 덮는다. 이 함수는
  5경로(create RPC·launch-agent·boot·restore·schedule)의 단일 합류점 — 선언·복원·resume 공통. 빈 셸에 나중에
  claude 를 타이핑하는 경로(입양·node-recover)도 그 셸을 만든 순간 배선이 끝나 있다.
- **무엇을 돌리나** = `javis_preflight.py --wire-seat` — C26·C27·C29 를 **그대로** 호출하고 `wire_only` 로 C26 의
  도구·키 탐침(node -v 등)만 끈다. 링크 규약·사용자 실디렉 불가침·부서/임시 팩 격리 가드·appbuild 게이트 훅 등록이
  사후 `--fix` 와 한 코드. 각성 절차의 사후 `--fix` 는 그대로(대조군).
- **env** = 좌석과 같은 env 전량(`CommandBuilder::iter_full_env_as_str`) — 부서 좌석은 부서 계정 dir, 본부 좌석은
  `~/.cys/claude` 에 배선된다. 좌석 config dir 이 아직 없으면 만든다(격리 컨텍스트 제외 — 발견 규약이 「디렉터리
  존재」라 첫 기동 전 프로필은 영영 안 잡히던 틈).
- **실패 계약** = 스폰 불가·비0 종료·상한 10초 초과 → 기동 계속 + 이벤트 `seat.wire_failed` 1건 + stderr 1줄. 팩에
  preflight 가 없으면 조용히 건너뜀. 10초 < launch-agent 서브프로세스 상한 80초 · RPC 무진행 상한 40초. 호출 지점은
  락 미보유 구간(handlers.rs surface.create 주석). 실측: 파이썬 내부 0.09초 · 벽시계 0.8초(/usr/bin/python3 기동비).
- **시험 빌드 봉인** = `#[cfg(test)]` 에서는 호출자 env `CYS_TEST_SEAT_WIRE=1` 일 때만 — cargo 시험 샌드박스 팩은
  임시 경로 밖(target/)이라 격리 가드가 안 걸리고 실 HOME `~/.cys/claude` 링크를 샌드박스로 바꾸는 라이브 오염이
  난다. `cys init-pack` 배선 호출도 `#[cfg(not(test))]`(함수는 직접 호출 시험 + 호출 위치 구조 단언).
- 맥/윈 공통(설치기 무의존). ⚠윈도 `os.symlink` 제약은 사후 `--fix` 와 동일(시점만 당겼다 · 링크 방식 불변).

## 3. 검증 — 시험 · 기준선 적색 / 적용본 초록(직접 재실측)

| 대상 | 시험 | 기준선 | 적용본 |
|---|---|---|---|
| D1 #1+#2 | `cysjavis-pack/bin/tests/test_d1_dept_ready_probe.py` DeptReadyProbe 3 + DeptFormationDoesNotHoldCallerPipe 1 | fd356c06 cys-dept: FAIL 3(핑 122·123·123 > 10) + ERROR 1(90초 상한 초과) · 209초 | OK 4 · 14.9초 |
| D2 R2 | `cargo test --bin cysd dbg_d2`(`#[ignore]` 제거 2건) | 원 코드 FAILED 2(핀 aaaa… 고정) | ok 2 |
| R2 곁 | `dbg_d2_empty_persisted_session_id_is_filled_by_registration` | ⚠원 코드로도 초록(하한 단언 — §5) | ok |
| R12 ① | `cargo test --bin cysd dbg_r12` 2건(신규 설치 · 갱신 레인 복원 좌석) — 가짜 좌석 시작 순간 링크 존재 + 링크 시각 ≤ 시작 | 호출 제거 뮤턴트 = FAILED | ok 2 |
| R12 ② | `cargo test --bin cys dbg_r12` 2건(init-pack 배선 · 호출이 no_install_hook 반환 앞) | 호출 제거·무동작 뮤턴트 = FAILED | ok 2 |
| D10 | 같은 파일 DeptFirstBootWait 4건(첫 부팅 22·40초 대기 · 정지 → 조기 실패+데몬 회수+등록 원복 · 기동 중 사망) | 12초 ready 복귀 뮤턴트 = 적색 | OK |
| F1 | `test_dbg_d3_dept_path_precedence.py`(995 원작 무수정 · 축 A·B·C) + 같은 파일 DeptSelfBinPrecedence 2건 + `cargo test --lib dbg_f1` | fd356c06 cys-dept `--target`: rc=1(2축 재현) | rc=0 · OK |
| D11 | `test_dbg_d3_d11_shared_profile_hooks.py`(995 원작 · 사본 팩 격리 수정) | 기준선 rc=1(본부 dept-chat-inject 소실) | rc=0 · 2초 |
| F4 | `test_dbg_d3_f4_answer_classifier.py`(995 원작 + 채움말만 3건 추가 · 표본 54) | 기준선 rc=1(오판정 재현) | rc=0 · 불일치 0 · 기존 test_dept_request 78건 OK |
| F5 | `test_dbg_d3_f5_dept_intent.py`(995 원작 무수정 · 셸 훅 실행 포함) | 기준선 rc=1(「교육부 닫아 줘」 등 누락) | rc=0 · POS 13 누락 0 · NEG 9 오탐 0 |
| D4 #1 | `cargo test -p cys-app --bin cys-app claude_missing_hint`(996 원작) | 주입 제거 뮤턴트 = FAILED | ok · cys-app 전체 163 통과 |
| D4 #2·#3 | `D4-evidence/headless-layout-check.ts`(ui/dist 실번들 · 폭 1470·1280·1024·800 · 996 원작) — ui 빌드(build.sh) 1회로 dist 재생성 | fd356c06 style.css: rc=1(1024 숨김 배지 노출 · 800 바닥 68px · 못 누르는 버튼 4 · 세로 쪼개짐 9) | rc=0(4폭 전부) |

뮤턴트 하네스 = `scripts/v115r4_dbg_mutants.py`(치환 1곳 assert · 종료코드 판정 · 컴파일/문법 실패는 CRASH 로 분리 ·
적색 귀속 시험 이름 병기 · 원복 바이트 대조). 결과 = §6.

CI: `test_d1_dept_ready_probe` · `test_dbg_d3_dept_path_precedence` · `test_dbg_d3_d11_shared_profile_hooks` ·
`test_dbg_d3_f4_answer_classifier` · `test_dbg_d3_f5_dept_intent` 를 3완전 레인(ci-branch·release 양 루프·
pack-release) 대칭 등재 — 레인 대조 게이트 로컬 실행 비대칭 0. ⚠리눅스 레인(release pack-artifacts·pack-release
= ubuntu)에서의 실행은 로컬 미검증(맥에서만 실측 · 선례 test_dept_name_guard 가 같은 가짜 cys/cysd 하네스로
ubuntu 레인에서 cys-dept 를 돌림).

## 4. 4군 점검

1. ①폭주 큐 — 새 코드는 큐에 아무것도 넣지 않는다(좌석 배선 = 파일 링크·settings 등록만 · 입력줄 주입 0).
   D10 대기는 cys-dept 프로세스 안의 폴링(0.3초 · 상한 120초)이고 데몬 큐와 무관.
2. ②무clear — **R2 가 정확히 이 군**: /clear(순환) 뒤 SessionStart 재등록을 핀이 따라가 topology 가 새 세션을 영속 →
   ↻·갱신·재부팅이 순환 **후** 대화를 resume(시험 dbg_d2 2건 + 뮤턴트 2종).
3. ③자가치유 — R12 배선은 좌석을 만들 때마다 멱등으로 다시 돈다(링크가 지워져도 다음 좌석 기동이 복구) +
   init-pack(앱 갱신)도 복구. D10 실패 정리는 고아를 남기지 않는다(회수 확인 뒤 등록 원복 · 못 끄면 등록 유지 →
   `cys-dept down` 으로 회수 가능).
4. ④전 pane — R12 배선 실패는 좌석 생성을 막지 않는다(fail-open · 10초 상한 · 이벤트 1줄). 배선 자식은 좌석 토큰을
   받지 않는다(주입 앞). F1 은 부서 데몬 판만 바꾼다(본부 좌석 무관).

## 5. 정직 고지 · 남은 것

- R2 곁 단언(복원 직후 빈 값 영속 → 등록 도착 시 채움)은 **원 코드(is_none 게이트)로도 초록**이다. 즉 981 이 본
  「본부 cso None 3분+」은 SessionStart 재등록이 안 왔거나 늦은 쪽이고, R2 처방 범위 밖일 가능성이 높다(미검증).
- R12 ② init-pack 배선은 앱 갱신 경로(rotate ④)에서 도는 것을 코드 경로로만 확인(VM 실기 미실행).
- D1 #3(부서 편성 워커 각성문 ACL) — 브리프대로 미편입(채택 통보 없음).
- 995 F1 patch 대비 확장 3점: CYS_CYS_BIN 1순위 · find_cysd 명시 env 우선 · 데몬/앱 spawn env 명시 전달(lib.rs).
- ★D10 시간 모의의 한계(실측 발견): 옛 `ready()` 예산 = 120 × (핑 + 0.1초)라 핑 비용에 따라 길어진다. 이 하네스의
  가짜 핑은 ≈0.29초/회 → 옛 예산 ≈35초 ⇒ **22초 모의는 되돌림 뮤턴트에도 초록**(공허) · 40초 모의만 적색이었다.
  그래서 시간 무관 계약 단언(기동 뒤 3자리 = boot_wait · 기본 상한 ≥90초)을 더했다 — 되돌림·상한 12초 둘 다 결정론 적색.
  VM 실측(첫 부팅 22초 > 옛 예산 ≈20초)은 이 하네스에서 재현되지 않는다.
- ★F4-2(물음표 → other 제거)는 등가 뮤턴트다 — `?` 는 분리 문자가 아니라 「네?」 낱말이 이미 사전 불일치로 other
  (겹방어 두 번째 층). 하네스에서 제외하고 사유를 주석으로 남겼다. F4-1(핵심어 필수 제거)은 원작 표본에 채움말만
  입력이 없어 **초록(시험 공백)**이었다 → 표본 3건 추가 후 KILLED.
- ★995 D11 원작 시험은 저장소 팩을 심링크로 물려 `preflight --fix` 를 돌려, 체크아웃의 훅 2개 실행비트를 바꾸고
  `.probe/` 를 남겼다(작업트리 오염) → 사본 팩으로 수정(판정 논리 불변).
- ★81cf2538 의 CI 설명 주석 2줄이 들여쓰기 없이 들어가 `run: |` 블록이 깨졌다(yaml 파싱 실패 · 레인 대조 게이트는
  정규식이라 통과) → a3faba69 수리 · 이후 등재마다 `yaml.safe_load` 3파일 확인.
- cysd `ingest_drain_throughput_bench` 1건 적색(60e6532f 회귀 중 · 뮤턴트·다른 회귀 동시 부하) — 같은 프로세스 안 두
  구간의 상대 시간 벤치(「2배+ 느리면 적색」)이고 이 묶음은 해당 코드 무접촉. 단독 2회 통과(Δ +63.8% / −46.6%).
  417a138f 회귀에서도 초록. ⇒ 부하 민감 간헐(선재) 판정.
- ★D11 판정 교정(890167cd): 995 원안 「계정 dir 이름에 `dept-` 없으면 공유(본부)」는 cys-dept create 의 primary 계정
  포크 dir(`~/.cys/claude-<키>` — `dept-` 접두 없음 · allocate 만 `-dept-N`)까지 공유로 보고 부서 자기 프로필 훅 등록을
  0 으로 만들었다 — 최종 HEAD 건강 검체 H-EXIT-8 ⓒ(부서 팩 + 부서 계정 dir → 그 dir 한 건) 적색으로 적발. 「계정 dir
  realpath == 본부 계정 dir」로 좁혀 교정(D11 시험 A·B·C PASS · H-EXIT-8 GREEN · 뮤턴트 KILLED).
- D4 #2 는 996 **권고안**(상단바 한 줄 고정 + 가로 스크롤)이라 tauri.conf minWidth 는 넣지 않았다(대안 patch 전용).
- cys-app 시험용으로 src-tauri/binaries·resources·runtime 에 **gitignore 된 자리표**를 두었다(커밋 없음).

## 6. 실측 결과

### 6-1. 뮤턴트 (`scripts/v115r4_dbg_mutants.py` · 치환 1곳 assert · 종료코드 · CRASH 분리 · 원복 바이트 대조)

| 축 | 뮤턴트 | 판정 · 적색 귀속 |
|---|---|---|
| D1 #1 | D1-1a launch 사전확인 ready 복귀 · D1-1b create 사전확인 ready 복귀 | KILLED · DeptReadyProbe launch/create |
| D1 #2 | D1-2 편성 서브셸 fd 상속 복귀 | KILLED · DeptFormationDoesNotHoldCallerPipe |
| D2 R2 | D2-1 등록 경로 추종 제거 · D2-2 교체 쓰기 무력화 | KILLED · dbg_d2_registered_transcript_change_moves_resume_pin |
| R12 ① | R12-1 exec 전 배선 호출 제거 · R12-2 좌석 config dir 미생성 · R12-3 C29(dept-by-chat) 누락 | KILLED · dbg_r12_seat_profile_wired_before_agent_exec / update_lane_restore |
| R12 ② | R12-4 init-pack 배선 호출 제거 · R12-5 배선 함수 무동작 | KILLED · dbg_r12_init_pack_* |
| D10 | D10-1 기동 뒤 대기 ready 복귀 · D10-2 데몬 회수 제거 · D10-3 정지 조기실패 제거 · D10-4 기본 상한 12초 | KILLED · 사망/정지 시험 · 예산 계약 · 22초 모의 |
| F1 | F1-1 PATH prepend 복귀 · F1-2 CYS_CYSD_BIN 1순위 제거 · F1-3 틱 전달 제거 · F1-4 spawn env 쌍 제거 · F1-5 CYS_CYS_BIN 1순위 제거 | KILLED · 995 시험 rc=1 / dbg_f1 / DeptSelfBinPrecedence |
| D11 | D11-1 공유 본부 프로필 등록 금지 제거 | KILLED · 995 D11 시험 rc=1 |
| F4 | F4-1 긍정 핵심어 필수 제거 | KILLED(표본 보강 뒤) · F4-2 물음표 검사 제거 = 등가(겹방어) 제외 |
| F5 | F5-1 셸 선거름 이름꼴 제거 · F5-2 파이썬 이름꼴 판정 제거 · F5-3 일반어 제외 제거 | KILLED · 995 F5 시험 rc=1 |
| D4 #1 | D4-1 진단 좌석 PATH 주입 제거 | KILLED · claude_missing_hint_probes_with_seat_path |
| D4 #2·#3 | dist 사본 style.css 에서 상단바 고정 줄 제거 · .badge[hidden] 제거 | 헤드리스 rc=1(800 못 누르는 버튼 3 · 숨김 배지 표시) |

합계 = 하네스 25종 + UI 2종 = **27/27 KILLED · CRASH 0 · SURVIVED 0**(등가 1종 사유 명시 제외).

### 6-2. 전체 회귀(직접 실측 · 스냅샷 워크트리)

| 판 | 항목 | 결과 |
|---|---|---|
| 60e6532f(Rust 변경 전부 포함) | `cargo test --lib -- --test-threads=1` | rc=0 · 469s |
| 〃 | `cargo test --bin cysd -- --test-threads=1` | 1039 통과 · 1 실패 = ingest_drain_throughput_bench(§5 · 단독 2회 통과) · d7_* 21건 ok |
| 〃 | `cargo test --bin cys -- --test-threads=1` | rc=0 · 228s |
| 〃 | 팩 python(ci-branch 맥 루프 46종 + IG-35 3종) · detect/preflight self-test · gen --check · secret-scan --all | 전부 rc=0 |
| 〃 | 건강 검체(run_bootstrap_health.py --json) | GREEN · 149 통과 · 0 실패 · 1 skip(H-WIN-11 = 윈 실기 CI 전용) |
| 본 트리(8ff59a70~) | `cargo test -p cys-app --bins` | 163 통과(자리표 번들 자원) |
| c632b179 | 팩 python 전종 · gen --check · secret-scan --all · 건강 검체 | pyseal_census 적색 → 42cedce9 수리(22→24 등재) · 건강 검체 RED 1 = H-EXIT-8 → 890167cd D11 판정 교정 |
| **983e575d(최종)** | 팩 python 전종(ci-branch 맥 루프 + 신규 5종 + IG-35 3종 = 56단계) · detect/preflight self-test · gen --check · secret-scan --all · 건강 검체 | **전부 rc=0** · 건강 검체 GREEN 149 통과 · 0 실패 · 1 skip(H-WIN-11) |
| — | 레인 대조 게이트(로컬 실행) · yaml.safe_load 3파일 | 비대칭 0 · 파싱 OK |

### 6-3. 자기 사고 1건(정직)

cys-app 시험을 위해 src-tauri/binaries 에 **빈 자리표 사이드카**(cysd·cys)를 두었더니 tauri 빌드가 그것을
`target/debug/cysd`·`cys` 로 복사해 **빈 파일로 덮었다**(17:04 · 제 작업트리 target 한정 · 소스·저장소·라이브 무영향).
그 target 을 복제한 최종 스냅샷 회귀에서 `test_sandbox_state_isolation` 이 「Exec format error」로 적색이 나서 적발 →
회귀 중단 · `cargo build --bin cysd --bin cys` 재빌드 · 자리표 전부 삭제 · 최종 회귀를 처음부터 재실행(§6-2 983e575d 행).
그 이전 판(60e6532f·c632b179) 스냅샷은 덮이기 전 target 을 복제해 영향 없음(파일 크기 72MB 확인).

## 7. 커밋(fd356c06..HEAD)

`git log --oneline fd356c06..HEAD` 참조 — 제품(fix) · 시험(test) · CI(ci) · 문서(docs) 분리. ⛔판번 bump·push·태그 없음.
