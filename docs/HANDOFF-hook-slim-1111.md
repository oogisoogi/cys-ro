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
  R3(검증 방어선 `back == want`)은 **등가 뮤턴트** 판정 — 정상 엔진은 기대값을 늘 맞추므로 결함 주입 없이는 죽일 수 없다(방어선 자체 = 무변경 거부 계약).
- ★발행 게이트 `scripts/scan-pack-secrets.sh`(master 672bfceb · 678 CI 적에서 발견 — 로컬 secret-scan --all 과 다른 스캐너): rc=1 · 2건 =
  `bin/javis_computer_control.py:1140`·`bin/tests/test_computer_control.py:25` 의 `@example.invalid` 이메일 모양 — **기준 커밋(a89ca937^)에서도 같은 2건**
  (cu-1111-win-fix 산출 · 이 티켓 무관). 이 티켓이 바꾼 팩 파일(시험 픽스처 포함 · 경로는 실행 시 tempfile 생성)은 0건.

## 남은 일(다음 좌석 · 순서대로)
1. codex·agy **R2**(같은 기준 · revision = R1 수리 2차 커밋).
2. 678(1111-merge01452) 병합 머리 위로 rebase + 게이트 재실행(아래 「재현」 전부 + scan-pack-secrets).
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
python3 -I scripts/bench_pack_hooks.py --pack cysjavis-pack --transcript <기록.jsonl> --out r.json --n 20 [--scenario seat --round]
```
