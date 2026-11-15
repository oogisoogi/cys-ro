# HANDOFF · TICKET=cysr-agy-door-r6 — codex 5R BLOCK 처분(마지막 고침 회차)

- 지시 = spawn 브리프(원장 2026-11-12 03:21:07 · 대상 surface:2008 · 본문 sha256 76613d3d… 대조 성립) · 작업 = worker-5(surface:2008)
- 가지 `fix/agy-policy-exposure` · 시작 머리 73d1a72e · 로컬 커밋만(push 0)
- 판정문 = `~/axdev/master/reports/2026-11-11-post-codex/codex-agy-5r.md` · 입구 표·한계 = `docs/agy-door-evidence/ENTRY-MODES.md`(§2 · §6 한계 · §7 데몬 입구 전수)

## 5R 8건 처분 표

| 5R | 심각도 | 처분 | 어디 | 시험 |
|---|---|---|---|---|
| 1 스크립트·심링크 | blocking | **줄임**(ⓐ 심링크 실제 이름 · ⓑ `sh/bash/zsh… 파일`·`source`·`.`·셔뱅 셸 글 파일 한 단계 읽기 · 등록·발화 둘 다 · 못 읽음 = 통과+표시) · 그 너머 = ENTRY-MODES §6 | `agy_door.rs` `resolves_to_agy`·`unread_scripts` · `schedule.rs` 발화 이벤트 `schedule.agy_door_unread` · `cys.rs` 등록 알림 | 단위 `symlink_and_one_level_script_codex_5r_blocking_1` · acceptance E23 · E24 · E13(`agyfirescript`) |
| 2 데몬 surface.create | blocking | **고침**(PTY 전 `create_refusal` = cmd·선언 agent 낱말 + 실체 한 단계) + 데몬 입구 전수 표(§7) — 빠진 줄 3개 같은 방식으로 닫음: `send_text {queued}`(큐 경로 무판정) · `send_text {agent_launch}` 기동 줄 · push `text_command` | `handlers.rs` `surface.create` · `agy_door_blocks_auto_send` · `schedule.rs` `run_text_command` | acceptance E20 · E21(queued) · E25 · 단위 · 소스 핀 |
| 3 좌석 식별 오분류 | blocking | **고침** — 생성 때 확정한 좌석 종류 `Surface.agy_kind`(= `seat_kind_is_agy` 낱말 검사)를 1순위(메타와 함께) · 저장 cmd 를 실행 자리 검사로 다시 읽지 않음 | `state.rs` · `handlers.rs` `agy_door_seat_closed` | acceptance E21 · 단위 · 소스 핀 |
| 4 sh -c 위치 인자 | major | **고침** — 글이 `$0`·`$1`…·`$@`·`$*` 를 쓰면 `$1`~ 를 명령 단위로 + 위치 인자 낱말 안전망 | `agy_door.rs` `program_of` 셸 갈래 · `uses_positional` | 단위 2(변이 1,134꼴 + 대조 189꼴) · acceptance E22 · E22c |
| 5 64KiB 문구 | major | **고침** — 「스크립트 파일로 옮겨」 삭제 → 「줄여 다시 등록 · agy 는 문을 연 뒤 사람이 직접」 | `machine_hint` | 단위 `too_long_text_does_not_prescribe_scripts_codex_5r_major_5` |
| 6 앱 2개 경합 | minor | **고침**(파일 잠금으로 끝남) — 옆 잠금 파일 `agy-seat-door.json.lock` OS 배타 잠금(`File::lock`) · 남는 것(잠금 미지원 FS)은 §6-6 | `write_door_at` | 단위 `door_write_waits_for_os_lock_codex_5r_minor_6` |
| 7 공백 경로 | minor | **고침** — `program_is_agy` = 실행 파일 경로 전용(공백 무관 마지막 이름 + 심링크) · 명령 문자열 = `names_agy` | `program_is_agy` | 단위 `exe_path_vs_command_string_codex_5r_minor_7` |
| 8 argv 상한 | minor | **고침** — Σ(길이+1) + 인자 개수 4,096 | `launch_refusal_argv_with` · `MAX_JUDGE_ARGS` | 단위 `argv_cap_counts_separators_and_args_codex_5r_minor_8` |
| ⑤ 거짓 양성(문제없다 목록) | — | 표만(§3 거짓 양성 표) — 줄어든 것 = 공백 든 해소 경로(③) · 새 규칙 없음 | — | 단위 `false_positive_table_codex_5r_item_5` |

## 지시 없이 내린 판단
1. **데몬 입구 전수에서 표 밖 3곳을 같은 방식으로 닫음**(브리프 「빠진 줄은 같은 방식으로 닫는다」 적용): `send_text {queued}` 는 큐에
   넣은 뒤 배달(watchdog)에 판정이 없어 `cys send --queued` 가 닫힌 문의 agy 좌석에 그대로 갔다(코드 확인 + 고치기 전 E21 `queued=False`) ·
   `agent_launch` 기동 줄(구판 CLI launch-agent 가 빈 셸에 agy 를 치는 꼴 · 고치기 전 E25 가짜 agy 실제 기동) · push 일정 `text_command`
   (내장·서명 승인 글 — 무인 셸 실행인데 문 판정 없음 · 시험은 소스 핀만: 승인 서명이 있어야 발화돼 하네스로 재현 못 함).
2. **좌석 종류 저장 위치 = `create_surface_with_env` 안**(핸들러가 아니라): 좌석 객체는 그 함수 한 곳에서만 만들어지므로 모든 좌석이 종류를
   가진다 → 브리프의 「메타 없는 옛 좌석 = names_agy」 갈래는 따로 둘 자리가 없고, 종류 계산 자체가 `names_agy(cmd)`(+ 선언 agent)라 같은 판정이다.
   휘발(영속 안 함) — restore 는 surface.create 를 다시 지나며 다시 확정한다.
3. **ⓑ 본문 읽기는 셸 글만**: 셔뱅 파이썬 파일 본문을 셸 실행 자리로 읽으면 `agy = 1` 같은 줄이 거짓 양성 → 셸에 넘긴 파일·셔뱅이 셸일 때만
   본문, 그 밖은 셔뱅 줄 낱말만. `source`/`.` 도 같은 「셸에 넘긴 파일」로 넣었다(브리프 ⓑ 의 `sh|bash|zsh <파일>` 과 같은 부류).
4. **ⓐⓑ 를 모든 기계 입구 ①에 덧붙임**(`is_agy_adapter` 안): 일정만이 아니라 채널·계정 어댑터·launch 어댑터·round-log·new-surface·
   surface.create 도 같은 판정을 쓰므로 한 자리에서. 실행 파일 찾기에 `PATH` 를 읽는다 — 모듈의 「환경 변수 안 읽음」 핀을
   「`search_path` 의 `PATH` 하나만 예외」로 좁혀 고쳤다(문 상태는 여전히 환경 변수와 무관).
5. **ⓑ 를 빼지 않았다**: 기존 acceptance 26항목·거짓 양성 시험 붉음 0 · 구현 시간 40분 안(03:25~03:40 사이 구현·단위 초록).
6. **minor 6 = 고침**(파일 잠금 몇 줄로 끝남 · `File::lock` · 잠금 파일 `agy-seat-door.json.lock` 이 `~/.cys` 에 남는다).
7. **acceptance E22c 판정 방식**: pane 밖 `cys run` 은 문과 무관하게 데몬 ACL(write-shell)이 거부 → 「문 사유 없음 + `cys agy-door-check -- argv` rc 0」으로.
8. **동시 5회 결과 폴더를 새로**(`concurrent-5-r6`) — r5 의 `concurrent-5` 원시 기록은 그대로 둔다.

## 함정
- acceptance 에 새 도우미 함수를 `main()` 안 람다로 두면 앞 입구(E21)에서 쓰기 전 정의 오류 — 모듈 수준 함수로.
- zsh 에서 `echo =====` 는 `=` 확장으로 실패(명령 경계 표시는 `echo '---'`).
- ⓑ 의 본문 읽기를 모든 셔뱅 파일에 하면 파이썬 글(`agy = 1`)을 셸로 읽어 거짓 양성 → 셸 글일 때만 본문 · 그 밖은 셔뱅 줄만.

## master 재현(스냅샷에서 도는 한 덩이 · 실 agy·라이브 데몬 무접촉 · 약 15분)
```sh
H=<머리 커밋>; S=/tmp/r6-snap-$$; git -C ~/axdev/.wt/cys-agy-policy worktree add --detach "$S" "$H" && cd "$S" \
 && export PATH="$HOME/.cargo/bin:$PATH" && cargo build --bin cys --bin cysd \
 && cargo test --lib agy_door && cargo test --bin cys agy && cargo test --bin cysd -- agy send_text delivery surface_create schedule \
 && env -u CYS_PACK_DIR DISABLE_AUTOUPDATER=1 python3 docs/agy-door-evidence/acceptance.py   # 종합 PASS · 33항목
```
(고치기 전 붉음 대조 = 같은 하네스에 `AGY_ACCEPT_BIN_DIR=<73d1a72e 빌드의 target/debug>` — 원시 기록 `docs/agy-door-evidence/r6-prefix-red/`)

## ChatGPT 닫힘 확인용 「꼭 물을 것 3줄」 · 범위 = 73d1a72e..<머리>
1. cysd 안에서 사용자·파일이 준 글이 실행 파일이 되는 자리가 `surface.create`·`send_text`(직접·queued·agent_launch)·일정 발화(`fire_command`·`run_text_command`)·
   채널·계정 어댑터 밖에 남아 있는가 — ENTRY-MODES §7 의 grep 범위(PTY 생성 = `create_surface_with_env` 한 곳)로 「표 밖 0」이 성립하는가?
2. `sh -c` 위치 인자 판정과 실체 한 단계 확인(심링크·`sh 파일`·`source`·셔뱅 셸 글)이 r5 까지 막던 꼴을 하나라도 풀었거나(회귀),
   정상 자동화(`sh -c 'echo "$1"' sh x` · 파이썬 셔뱅 스크립트 · 공백 든 실행 파일 경로)를 새로 막는가?
3. 좌석 식별을 생성 때 확정한 종류(`Surface.agy_kind` · 낱말 검사)+메타로 바꾼 뒤, 닫힌 문의 agy 좌석에 자동 지시가 닿는 길(직접·queued·GUI 자동 문안·
   node-recover 기동 줄)이 남는가 — 사람 자판(human ∧ ¬machine_origin) 통과·원장 표시는 그대로인가?

## 릴리스 노트 「알려진 한계」 쉬운 말 3줄(초안)
- cysr 는 Antigravity(agy)를 자동으로 띄우지 않습니다. 일정·채널·자동 지시 같은 자동 기능이 agy 를 실행하려 하면 막고 까닭을 알려 줍니다. 사람이 새 탭에서 직접 `agy` 를 치는 것은 언제나 됩니다.
- 이 장치는 실수를 막는 장치이지 보안 장치가 아닙니다. 명령 글자와 그 글자가 가리키는 파일 한 단계(바로 가기 링크·셸 스크립트 내용)까지만 살펴서, 스크립트가 다시 부르는 스크립트·실행 중에 만들어지는 이름·별칭이나 복사본은 이번 판에서 막지 못합니다.
- 설명 글에 「agy」라는 낱말만 들어 있어도 자동 기능이 막힐 수 있습니다 — 그 낱말을 다른 말(예: 「안티그래비티」)로 바꾸면 됩니다. 기업 요금제처럼 허용된 경우에만 앱의 「Antigravity(agy) 좌석 열기」로 문을 엽니다.

## 실측
- 커밋: f4576ffa(고침) · 996ee189(acceptance E20~E25 · 문서) · 6907f84d(E22c 대조 · 고치기 전 붉음 기록) · 34dd0f0c(동시 5회 기록) · 이 커밋(인계)
- 고치기 전 붉음(73d1a72e 빌드 · 03:34~03:45): E20·E21·E22·E23·E24·E25·E13(스크립트 발화) 적색 — E20·E25·E13 은 가짜 agy 가 **실제로 기동** · `docs/agy-door-evidence/r6-prefix-red/`
- acceptance 동시 5회(6907f84d 바이너리 · 03:58:07~04:09:51 · 부하 4.7→5.5) = **5/5 PASS · 각 33항목**(r5 26 + E20·E21·E22·E22c·E23·E24·E25 · E13 에 스크립트 발화 단언 2) ·
  `docs/agy-door-evidence/concurrent-5-r6/` · `acceptance-result.json` = run1 사본(첫 동시 실행 03:46~03:57 은 E22c 하네스 결함 — 숨은 동사를 `--socket` 뒤에 불러 clap 오류 — 로 5/5 같은 1항목 적색 → 하네스만 고침)
- 단위: lib agy_door 29(새 9 · 변이 42,900꼴 + 새 1,134꼴 · 대조 189꼴) · cys bin agy 13 · cysd agy|send_text|delivery|surface_create|schedule 238 · 팩 test_agy_door 20 · phoenix 루프 P1~P7·M1~M5 OK
- 뮤턴트 14/14 적색(lib 8: 위치 인자·실체 확인·스크립트 표지·좌석 종류 선언·경로/명령 분리·argv 상한·64KiB 문구·OS 잠금 / 데몬 소스 핀 6: surface.create·좌석 종류 판정·queued·text_command·기동 줄·종류 저장)
- 전체 단위(34dd0f0c · 순차 · --test-threads=4 · CARGO_BUILD_JOBS=4): lib **1232 통과/0 실패**(2 ignored · 04:10~04:16) · cys bin **759/0**(04:16~04:30) ·
  cysd bin **3227/0**(15 ignored · 04:30~04:42). (cys-app·통합 시험·phoenix host-gate 는 이번에 안 돌림 — 변경 파일 밖)
- 윈도우(PowerShell·call/start·cmd /c) = 코드 경로만 · **윈 실기 미확인**
- 걸린 시간: 03:21 착수 → 04:42 전체 시험 끝(81분 · 상한 100분 안)

## 함정(추가)
- acceptance 에서 pane 밖 `cys run` 은 데몬 ACL(`external lacks 'write-shell'`)로 rc 1 — 문 판정 통과 여부를 rc 로 재지 말 것.
- 숨은 동사 `cys agy-door-check` 는 첫 인자일 때만 — `cys --socket … agy-door-check` 는 clap 오류(「unrecognized subcommand」).
- 데몬 `send_text` 의 판정은 `queued` 갈래보다 **뒤**에 있었다 — 새 판정을 넣을 때 큐 갈래(7568행 부근)가 먼저 return 하는지 볼 것.
- 장기기억 증류: 위 함정 3줄이 대상이나 브리프 「라이브 `~/.cys` 무접촉」이라 `javis_memory.py add` 는 보류(master 판단).

## 미완
- ChatGPT 닫힘 확인(master 가 건다 · 위 3줄) · push 0 · 릴리스 노트 반영(master)

## 2회차(master#17469565 · ChatGPT BLOCK 처분 · 05:10~ · 원장 대조 성립 05:09:49)
판정문 = `~/axdev/chatgpt-desk/runs/2026-11-12/REVIEW-cysr-agy-r6-cd094675.md`

| 건 | 처분 | 고친 줄(1cb4685b 기준) | 시험 |
|---|---|---|---|
| F1 blocking 배달 시점 재판정 | **고침** — 배달 직전 `drop_agy_door_closed`(닫힌 문 agy 좌석행 기계 항목 · agy 기동 줄 → 폐기 + 원장 묘비 `agy_consumer_policy` + `queue.dropped`) · 사람 자판 적재 = 출처 `send_human` 통과 | `governance.rs:4600-4636`(상수·함수) · `:12419`(호출 = `deliver_head_locked` 머리 — 틱·queue.deliver 공통) · `handlers.rs:7595`(출처 표기) | acceptance E26(고치기 전 붉음 = PTY 에 쓰임 · `r6-prefix-red/e26-before-F1.txt`) · 소스 핀 3 |
| F2 blocking 셔뱅 env -S | **고침** — `shebang_interpreter`(env 옵션 건너뜀) | `agy_door.rs:216-245` · `:257` | 단위 `shebang_env_split_and_options_chatgpt_f2`(9꼴 거부 · env python3 통과) |
| F3 major 읽기 상한 | **고침** — 일반 파일만 · 비차단 열기 + 핸들 재확인 · `take(상한+1)` 한 번 읽기(머리·본문 같은 핸들) · 같은 대상 1회 · 서로 다른 대상 64 초과 = 거부 쪽 · 스크립트 64KiB 초과 = 거부 쪽(명령 상한과 같은 방향) · 바이너리는 크기 무관 이름만 | `agy_door.rs:193-` `read_capped` · `judge_file` · `resolve_judgements` | 단위 `bounded_reads_and_target_caps_chatgpt_f3`(4,000 같은 낱말 · 4,000 서로 다른 낱말 각 3초 상한 · FIFO 막힘 없음) |
| F4 minor `$0` 거짓 양성 | **고침**(15분 안) — `$0` 자리는 글이 `$0` 을 쓸 때만 | `program_of` 셸 갈래 · `uses_dollar0` | 단위 `dollar0_only_when_used_chatgpt_f4` · 남는 보수적 거짓 양성 1종(`sh -c 'echo "$1"' sh agy`) = §6/§2 위치 인자 절에 정책으로 |
| F5 minor 세 갈래 | **고침** — `Judge::{Agy,NotAgy,Unread}` · 직접 실행 파일 머리 읽기 실패도 Unread(통과+표시) | `judge_file` | 단위 `direct_exec_unreadable_is_unread_chatgpt_f5` |
| F6 minor 잠금 대기 | **고침** — 5초 상한 try 반복 · 읽기 전용 잠금 파일 = 읽기 핸들 · 왕초보 오류 2종 · 지우라는 안내 없음 | `agy_door.rs:854-` `door_os_lock` | 단위 `lock_wait_capped_and_readonly_lock_file_chatgpt_f6` |
| 답 ① 표 밖 0 | grep 범위 확장(src 전체 · 생성 API 10종) = 199줄 · 운영 60줄 전부 분류 · 새 입구 0 → ENTRY-MODES §7-1 · 지연 실행 전수 = §7-2 | — | — |
| 답 ② File::lock 판 | Rust 1.89.0 안정화(releases.rs 1.89.0) · 저장소 고정 없음(rust-toolchain·rust-version 없음 · CI dtolnay stable) · 이 기계 1.97.0 | — | — |

- 뮤턴트 11/11 적색(처음 10/11 — 「일반 파일 확인 둘 다 제거」 녹색: `locate_target` 이 이미 FIFO 를 거르므로 시험이 읽기 함수에 안 닿음 → `read_capped(FIFO)` 직접 단언 추가 후 적색)
- acceptance 동시 5회(1cb4685b · 05:24:23~05:36:28) = 5/5 PASS · 각 34항목(E26 추가) · `concurrent-5-r6b/`
- CTX 45.7%(jsonl 라이브 · 05:24)
- 전체 단위(1092a635 · 순차): lib **1237/0**(2 ignored · 05:38~05:44) · cysd **3227/0**(15 ignored · 05:44~05:55) · cys bin agy 13/0 · cys bin 전체는 2회차에 cys.rs 무변경이라 안 돌림(1회차 759/0)
- master 재현 = 1회차 「master 재현」 한 덩이와 같음(acceptance 가 E26 포함 34항목 · 약 16분) · E26 단독 = `python3 docs/agy-door-evidence/acceptance.py --only-e26`(약 1분)
- 걸린 시간 2회차: 05:10 → 05:56(46분 · 상한 75분 안)
