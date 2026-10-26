# HANDOFF — hook-slim-1111 (1.1.11 · worker-2 677)

정본 설계·실측 = `docs/DESIGN-hook-slim-1111.md` · 윈 의뢰 = `docs/hook-slim-1111-win-measure-request.md` · 원작자 요약 = `docs/hook-slim-1111-author-summary.md`.

## 끝난 것
- 등록 조건 A(옵트인 표지) — Rust 4경로(데몬 기동·init-pack·doctor --fix·개인 프로필 병합) + 파이썬 `resolve_registration_targets` 같은 술어.
- 개인 프로필 팩 등록 제거(사용자 훅·다른 키 바이트 보존 · BOM/CRLF · 읽기 전용 존중 · 시각 붙은 사전 백업) — 제거 엔진 순서 보존 개편.
- B1 좌석 아닌 세션 즉시 탈출(팩 훅 11개) · Stop 관측 훅 분리 실행 · 선언 timeout 14행.
- 시험: Rust `hookslim` 14 · `test_hook_slim.py`(S1~S11·PF·FX·GT·DT) · 기존 검체 개정(아래) · 뮤턴트 `scripts/hookslim_mutants.py`.

## 시험 개정(계약이 바뀐 곳 — 리뷰 때 확인할 것)
- `run_bootstrap_health.py`: H-EXIT-8(신규 머신 폴백 = 표지 없음이면 계정 config) · `_HOOK_SEAT` 신설(좌석 본문을 재는 검체 10개 + `_a1_mock_env` 에만
  좌석 env 명시 — `_base_env` 의 「좌석 env 지움」 계약은 그대로) · H-WIN-2·G-PRELUDE 에 `CYS_HOOK_STOP_SYNC=1`(본문 동기 측정).
- `test_inject_context_role_seat.py` 11a/11b: 「신원·env 없는 세션 = 중립 문안 + 본부 작업기억(복원 생명선)」 → 「주입 0」(B1).
- `test_session_state_canon.py`·`test_inject_context_soul_l0.py`·`test_pack_guard_hooks_guidance.py`·`hooks/test_pre_dispatch.sh`: 좌석 env/동기 노브 명시.

## 함정
- 팩이 임시 폴더 아래면 preflight 는 등록을 통째로 끈다(`_path_under_tempdir`) — 「재부착 0」 시험은 HOME 을 임시 폴더 **밖**(`<repo>/target`)에 둬야
  의미가 있다(첫 판 PF 가 그래서 공허했다).
- `test_hook_r34` 의 시한 검체(RCF-3·RCF-4a·NZ-3·DL-1b)는 부하(load 4~6)에서 기준 커밋도 3회 중 2회 적색 — 기존 흔들림.
- 기준 커밋에서도 적색인 검진 4건: H-SECRET-1·H-WIN-16·H-CLT-1·H-CLT-2(환경·기존).
- commit-memory-nudge 는 Bash 본문에 `git commit` 문자열만 있어도 오발화한다(이 티켓 중 3회) — 별건.

## 리뷰 R1 처분(codex REVISE · agy REVISE · revision 4b849a2c · verdict 정본 `~/.cys/pack/round/_reviews/hook-slim-1111__…-r1-{codex,agy}.json`)
codex 는 샌드박스 탓에 정본 경로에 못 써 `/private/tmp/hook-slim-1111-r1-codex.json` 에 남겼고, 677 이 내용 무변경으로 정본 경로에 복사(sha256 7ef3d365… 일치).
| 지적 | 출처 | 처분 | 상태 |
|---|---|---|---|
| 첫 두 멤버 동시 삭제 시 구간 겹침 panic | codex·agy blocking | 수용 — `rejoin`(남는 항목만 원래 구분자로 잇기) | ✅ 수리 · 시험 leading_two_members_both_removed |
| hooks 통째 재직렬화 → 남는 사용자 훅 표기 변화 · 전체 재작성 폴백 | codex major | 수용 — 중첩 외과 삭제 · 기대값 불일치 = 무변경 거부(폴백 폐지) | ✅ remaining_user_hook_bytes_are_untouched |
| 팩 경로가 인자·부분 문자열이어도 삭제 | codex major | 수용 — 개인 프로필 전용 엄격 판정 `personal_pack_command` | ✅ strict_personal_predicate |
| 윈 MSYS `/c/…` 표기 | codex major | 수용 — 드라이브 정규화 · 윈 대소문자 무시 | ✅ 같은 시험(윈 실기는 의뢰문) |
| doctor 탐지가 BOM·statusLine 단독을 못 봄 | codex·agy major | 수용 — 탐지·제거 같은 계획 함수 `pack_registrations_in_personal_profile` | ✅ detection_sees_bom_and_statusline_only |
| 같은 초 백업 덮어씀 | codex minor | 수용 — create_new + `-N` | ✅ same_second_backups_do_not_clobber |
| `~/.claude/settings.json` → 좌석 config 심링크면 좌석 훅 삭제 | codex major | 수용 — 실파일·부모 정규화 후 좌석 config(`config_dir_for` ∪ `${CYS_ACCOUNT_DIR:-~/.cys/claude}`)와 같으면 좌석 프로필(Rust `pack::is_seat_profile_settings` = 제거 경로·doctor · 파이썬 `_is_personal_profile_settings` 같은 술어) | ✅ S12a·S12b · seat_profile_predicate_sees_through_symlinks |
| `CYS_ACCOUNT_DIR=~/.claude` 면 파이썬 폴백 재부착 | codex major | 부분 수용 — 명시 계정 dir 은 「좌석 프로필」로 두 언어 일관 취급(Rust 도 안 지움 → 싸움 0) · 위 심링크 수리와 같은 술어 · 한계: 데몬·preflight env 가 다르면 갈림(DESIGN §3-1) | ✅ S12c·S12c' |
| 분리 자식 잠금 전 틈(소비자 조기 통과)·PreCompact 비참여·빈 pid 영구 잠금·잠금 실패 시 무잠금 실행 | codex·agy major | 수용 — 부모가 반환 전 대기표 등록(`<state>/hook-detach/<이름>.q/`) · 소비자는 대기표+잠금을 기다림 · PreCompact 도 같은 잠금(대기 20초) · 빈 pid 2초 넘으면 회수 · 잠금 실패 = 건너뜀 + hook-errors 기록. 순서(FIFO)는 보장하지 않음 — 문서 정정(각 자식이 자기 시각을 쓰고 reflect 는 멱등이라 무해) | ✅ DT10~DT13 |
| 분리 자식 본문 상한 없음 | codex major | 수용 — reflect scan 60초·memory verify 30초 `cys_timeout_run` + 124 기록(파이썬 기동 자체 정지는 래퍼도 같이 멈추므로 대상 아님) · 시간 초과는 정합 경고로 쓰지 않음 | ✅ DT14 |
| `CYS_NO_PERSONAL_HOOK_MERGE=1` 노브를 제거 경로가 무시 | agy minor | 수용 — 제거 경로 진입부에도 같은 노브 | ✅ S12d |
| role-capability-gate 에 B1 탈출 없음 · 일부 훅 2키 검사 | agy minor | 앞은 수용 — 단 조건에 `CYS_ROLE` 포함(이 GATE 는 surface 없이 `CYS_ROLE` 폴백으로 집행 · 넷 다 비면 해소 역할 = 빈 값 = 통과라 동작 동일) · 2키 훅(session-start 등)은 기존 동작이라 범위 밖 | ✅ GT1(12훅)·GT5 · capgate 52 OK |
| 이벤트 판정이 페이로드 부분 문자열 | agy minor | 반박 — JSON 문자열 안의 같은 글자는 `\"…\":\"…\"` 로 이스케이프돼 `"hook_event_name":"Stop"` 패턴과 불일치 | ✅ DT9 |
| cargo 미실행(codex 샌드박스) | codex missing | 677 실행: `cargo test --lib` 1110 통과(수리 전) · hookslim 14 · factory_reset 60(수리 후) | — |

## R1 수리 2차(⏳ 5건 · 10-27 worker-2 677) — 게이트 결과
- `cargo test --lib` 1116/0(2 ignored) · `--bin cysd` 2709/0 · `--bin cys` 628/0 · `--lib hookslim` 15/15(+1 seat 술어 · prev 체인 CRLF 보강).
- `test_hook_slim.py` 65/0(S12a~d·S12c'·DT9~DT14·GT5 신규) · `test_capgate_hook_shell.py` 52 OK.
- `run_bootstrap_health.py` 164/4 — 4 = 기준 커밋과 같은 적색(H-SECRET-1·H-WIN-16·H-CLT-1·H-CLT-2) · H-EXIT-8·H-WIN-2·G-PRELUDE 통과.
- 뮤턴트 `scripts/hookslim_mutants.py --rust` 32개(M15~M22·R7~R10 신규): 첫 판 29/32 → 살아남은 M22(파이썬 좌석 술어 — 폴백이 같은 파일을 돌려줘 가려짐)·
  R6(CRLF — R1 외과 삭제 뒤 이 줄은 statusLine 원복 갈래 전용) 은 검체 보강 후 개별 재실행으로 KILLED 확인 → 31/32.
  R3(검증 방어선 `back == want`)을 여기서 「등가」로 적었으나 **틀렸다** — agy R2 가 반례 제시(아래 R2 처분 ②).
- ★발행 게이트 `scripts/scan-pack-secrets.sh`(master 672bfceb · 678 CI 적에서 발견 — 로컬 secret-scan --all 과 다른 스캐너): rc=1 · 2건 =
  `bin/javis_computer_control.py:1140`·`bin/tests/test_computer_control.py:25` 의 `@example.invalid` 이메일 모양 — **기준 커밋(a89ca937^)에서도 같은 2건**
  (cu-1111-win-fix 산출 · 이 티켓 무관). 이 티켓이 바꾼 팩 파일(시험 픽스처 포함 · 경로는 실행 시 tempfile 생성)은 0건.

## 리뷰 R2 처분(agy REVISE · revision 21d45a70 · verdict 정본 `~/.cys/pack/round/_reviews/hook-slim-1111__…-r2-agy.json`)
agy 는 R1 12건 전부 해소로 판정하고 신규 2건을 냈다. codex R2 는 사용량 한도로 미실행 → master cbcd0c12 지시로 05:30 재실행(수리 커밋 기준).
| 지적 | 처분 | 상태 |
|---|---|---|
| ① blocking: `restored_prev_statusline` 이 ` sh `·` bash `·`/bash.exe` 부분 문자열을 뒤에서 찾아 경계를 정함 — 윈 형식에서 이전 값에 ` sh ` 가 있거나 런처가 역슬래시 `…\bash.exe` 면 None → 사용자 상태줄이 원복 대신 삭제(이 함수는 티켓 전부터 있었으나 이 티켓이 개인 프로필에 자동 적용) | 수용 — 소유 판정과 같은 `shell_words` 낱말 분해로 첫 할당 낱말의 값을 꺼낸다(`shlex.quote` 이어 붙이기·겹따옴표 포함) · 유일 호출처가 사라진 `shell_unquote_single` 제거 | ✅ restored_prev_statusline_variants(반례 2 포함) · 뮤턴트 R12 |
| ② major: `OJ` 가 중복 키를 덮어써 판정이 JSON.parse 와 갈림 — 첫 `hooks` 에만 팩 훅이면 「없음」(doctor OK 오판) · 중복 `Stop` 을 남긴 채 통과 · R3 「등가」 주장 반박(중복 이벤트 키에서 R3 만 통과) | 수용 — `OJ` 는 중복을 모두 보존 · 판정 범위(`hooks`·`statusLine` 하위) 안 중복 = 계획 단계 거부(`dup_in_scope` · 탐지·제거 공통 → doctor 「판정 불가」) · 범위 밖 중복은 원문 그대로 남고 재판독 대조로 정확 비교. R3: 21d45a70 에서는 **비등가였다**(agy 옳음) — 수리 뒤 그 입력 부류는 앞단에서 거부되어 R3 은 2차 방어선(알려진 구별 입력 없음) | ✅ duplicate_keys_are_refused_without_writing(반례 4 + 범위 밖 중복 통과) · 뮤턴트 R11 |

- agy **R3 = ACCEPT**(revision 5f255f32 · verdict `…-r3-agy.json`): R2 2건 해소 · 기준 ①~⑦ 미달·신규 결함 0.

## 리뷰 R2 처분(codex REVISE · revision 5f255f32 · verdict 정본 `~/.cys/pack/round/_reviews/hook-slim-1111__…-r2-codex.json`)
codex 는 정본 경로 쓰기 거부(샌드박스)로 대체 경로 `/private/tmp/hook-slim-1111-r2-codex.json` 에 썼다 → 그대로 정본 경로에 복사(cmp 동일). major 4 · 전부 수용.
| 지적 | 처분 | 상태 |
|---|---|---|
| I1 `CLAUDE_CONFIG_DIR=~/alias-config → ~/.claude` + 표지 없음 — 발견의 realpath 중복 제거가 원경로를 숨겨 별칭만 남고, 별칭 이름이 `.claude*` 가 아니라 개인 프로필 아님 → 팩 훅·statusLine 재등록 + 재직렬화 | 수용 — `_is_personal_profile_settings` 이름 규칙을 원래 경로·파일 실경로 폴더·폴더 실경로 셋에 건다(좌석 비교는 그대로 앞) · 모든 writer 가 `resolve_registration_targets` 하나를 거친다 | ✅ S12e(대상 탐침 · 수리 되돌리면 적 확인) · 뮤턴트 M29 |
| I2 죽은 주인 「다시 읽고 rm」 비원자 — 두 회수자가 같은 죽은 pid 를 확인하면 뒤 회수자가 새 주인 잠금을 지워 둘 다 본문 진입(실 함수로 재현) · 빈 pid 회수도 같은 경합 | 수용 — 회수자 직렬화 `<이름>.lock.reap`(mkdir) 안에서 다시 읽고 지움 · 3초 넘게 남은 `.reap` 만 치움 · 해제 = 주인 토큰일 때만 | ✅ DT16(회수 중이면 기다림 3~8초) · DT16b(죽은 주인 잠금에 8개 동시 획득 = 보호 구간 겹침 0) · 뮤턴트 M23 |
| I3 소비자 5초 < 생산자 스냅샷 상한 10초 — 7초 생산자면 5.8초 뒤 OLD 스냅샷을 최신처럼 주입 | 수용 — 대기 = 부를 때 있던 표(epoch ≤ 시작 시각)가 모두 처리될 때까지 · 상한 12초 · 넘기면 rc 1 → inject-context 는 이전 스냅샷 생략 + 1줄 고지 · 배수기 없는 고아 표는 한 번 깨움 | ✅ DT17·DT17b(12초 뒤 생략·고지)·DT17c(큐 비면 즉시 주입) · DT10d·DT10e · 뮤턴트 M16·M24·M25·M28 |
| I4 같은 상태의 모든 세션이 이름 하나의 잠금 + 자식 120초 대기 뒤 입력 폐기 — 정상 상한 안의 reflect 셋이 겹치면 하나 유실(결과 손실 0 위반 · DT13 이 폐기를 성공으로 잠금) | 수용 — **영속 큐 + 배수기 하나**: 대기표 = 입력 원문 · 배수기는 기다리지 않고 잡아 보고 살아 있는 주인에 물러남 · 큐 끝까지 · 해제 뒤 재확인 → 대기 한도·폐기 0 · 동기 잠금 20초 실패 = 큐에 넘김(DT13 계약 반전) | ✅ DT15(긴 본문 중 3건 = 3줄 · 한 배수기) · DT13·DT13b(넘긴 입력이 주인 사망 뒤 처리) · DT18(동기 주인 해제 뒤 깨움) · DT19(해제 뒤 재확인) · 뮤턴트 M15·M17·M19·M19b·M26·M27 |
| (비차단) 중첩 `{"metadata":{"hook_event_name":"Stop"}}` 가 최상위 PreCompact 를 Stop 으로 판정 | 기록만 — codex 도 실제 Claude 입력 발생 증거 없음으로 차단 결함 단정 안 함 · 판정은 글자 일치 그대로(파이썬 파싱 비용 회피) | — |

## R2 수리 뒤 rebase(master d53e9107 · int/1111 = 2d32a22d)
- 텍스트 충돌 0(8 커밋). 678 §5 예상 지점(cys.rs `run_init_pack`·`diag_hook_personal` · run_bootstrap_health.py 픽스처) 무충돌.
- rebase 뒤 발견·수리 2건: ① lane-parity `--strict` 3단계 「사유 없는 미등재 test_hook_slim」 → 3완전 레인 5루프 등재(ci-branch 2 · release 2 · pack-release 1) ·
  CI 팩 루프는 cys 빌드 전이라 바이너리 없으면 **셸 훅 부분(GT·DT)만** 재고 바이너리 경로(S·S12·PF)는 「SKIP(부분)」 명시(종전: 통째 SKIP = 조용한 통과)
  ② `secret-scan --all` 18건 = 이 티켓 factory_reset.rs 시험 픽스처의 더미 사용자 `u`·`U`(허용 더미 = user|x|youruser|USERNAME|runner|home) → `user`(뜻 무변경).

- rebase 뒤 게이트(맥 arm64 · 라이브 무접촉 = CYS_* 제거 · 팩 레인은 HOME·CYS_PACK_DIR 임시):
  | 게이트 | 결과 |
  |---|---|
  | cargo `--lib` | 1133 / 0 / 2 ign |
  | cargo `--bin cys` 전체 | 735 / 0 / 1 ign |
  | cargo `--bin cysd`(CI 형식 `--test-threads=1 --skip hwmon::tests::snapshot_has_all_sections`) | 3217 / 0 / 15 ign |
  | ci-branch mac 완전 레인 목록 144(doc-contract·pins·바이트 래칫 `test_cso_directive_rev`·test_hook_slim 포함) | **144 / 144 녹**(test_hook_slim 77 / 0) |
  | 부트스트랩 건강성 전량 | 167 / 2 / 1 skip — 잔여 적 H-CLT-1·H-CLT-2(호스트 설치본 python · 678 §2-1 과 동일) |
  | `scan-pack-secrets.sh` · `secret-scan.sh --all` | rc 0 · clean(1876 파일) |
  | `lane-parity-rehearsal.sh --strict` · `--self-test` | rc 0 · 0 |
  | 뮤턴트 `--rust` | 41 / 42 KILLED — 생존 R3(2차 방어선 · 위 agy R2 ② 처분: 구별 입력은 앞단 `dup_in_scope` 가 거부 · 알려진 구별 입력 없음) |
  | 윈도우 실기 | 미측정(CI windows-build·windows-health 가 독립 검증) |

## 남은 일(다음 좌석 · 순서대로)
1. push(`fix/1111-hookslim` · 실행직전확인요청 뒤) → CI 3종(ci-branch·windows-build·windows-health).
2. codex R3(수리 커밋 기준) · agy R4 여부는 master 판단.
3. 【확인요청】.
- 미확정 유지: 1,059초 사례 원인(§2-5) · B2(1.1.12 BACKLOG · 아래).

## 1.1.12 BACKLOG
- **B2(master 02da1acc 지시)**: 원 계정 좌석(CLAUDE_CONFIG_DIR 없이 `~/.claude` 로 뜨는 좌석 · 우리 맥 14일 156세션)을 띄울 때 좌석 settings
  (`claude --settings ~/.cys/seat-settings/<역할>.json` — 이미 좌석 기동 줄에 붙어 있다 · 쓰는 곳 `lib.rs claude_seat_settings`)에 팩 훅을 싣고
  `~/.claude` 는 **완전 무팩**으로. 그러면 우리 맥도 표지가 필요 없다. 선행 검증: ① `--settings` 층의 hooks 가 프로필 settings 의 hooks 와 **합쳐지는지·
  같은 명령이 중복 발화하는지**(Claude Code 버전별 실측) ② launch-agent·restore·schedule·boot 5경로가 전부 그 파일을 붙이는지 ③ 좌석 프로필
  (`~/.cys/claude`)과 겹칠 때 중복 0.
- commit-memory-nudge 오탐(문자열 일치 → 실제 git commit 실행 판정).
- 1,059초 사례 원인 재추적(전원 로그가 남는 기간에 재발 시 `pmset -g log` 대조).

## 재현
```
cargo build --bin cys --bin cysd
cargo test --lib hookslim
python3 cysjavis-pack/bin/tests/test_hook_slim.py --diff-out /tmp/hookslim_diffs.md
python3 cysjavis-pack/bin/tests/run_bootstrap_health.py
python3 scripts/hookslim_mutants.py --rust
bash scripts/scan-pack-secrets.sh            # 팩 발행 hard-gate(CI ci-branch·pack-release·release) — 이메일 모양·개인 홈경로 fail-closed
bash scripts/secret-scan.sh --all            # 저장소 전체(H-SECRET-1) — 더미 사용자 이름은 허용 목록만
bash scripts/lane-parity-rehearsal.sh --strict && bash scripts/lane-parity-rehearsal.sh --self-test
python3 -I scripts/bench_pack_hooks.py --pack cysjavis-pack --transcript <기록.jsonl> --out r.json --n 20 [--scenario seat --round]
```
