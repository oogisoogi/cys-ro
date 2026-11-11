# agy 좌석 문 — 입구별 판정 방식 (TICKET=cysr-agy-door-r5 · codex 4R 처분 · r6 = codex 5R 처분)

> 문의 목적(바뀌지 않음): cysr 제품과 **선의의** 에이전트가 **실수로** agy(구글 Antigravity CLI)를 자동 실행하는 길을 막는다.
> 같은 사용자 권한으로 하는 **고의** 우회를 막는 보안 경계가 아니다(아래 §6 「한계 — 이 판에서 막지 않는 것」 한 곳에 모았다).

## 1. 왜 판정 방식을 둘로 나눴나

codex 1R~4R 네 번 모두 같은 종류의 지적이 돌아왔다 — 셸 문자열을 **해석하는** 판정기의 우회(못 잡음)와 거짓 양성(잘못 막음).
셸 문법(인용·치환·래퍼·옵션)은 열거로 끝나지 않는다. 그래서 「사람이 그 자리에서 문장을 쓰지 않는 길」(기계 입구)은 셸을
해석하지 않는 **낱말 검사**로 바꿨고, 「에이전트·사람이 그 자리에서 쓰는 문장」(guard · `cys run`)만 **실행 자리 검사**를 남겼다.

| 회차 | 돌아온 부류(대표) | 처분 |
|---|---|---|
| 1R | `cys run -- agy` · 인용/대입/env/`sh -c`/`.bat` 해석 | 해석 규칙 추가 |
| 2R | `env -S` 묶음 · `cys run` argv 재조립 · 백스톱 복합 명령 | 해석 규칙 추가 |
| 독립 재검 | 첫 단순 명령만 봄(`cd x && agy`·`timeout 5 agy`·`sudo agy`) · 붙여 쓴 낱말 | 해석 규칙 추가 |
| 3R + 966 | `cmd /c`·powershell·`find -exec`·`-o/-O`·here-string·리다이렉트 머리·zsh 앞말·`$'agy'`·`a^gy`·파이프 셸 · 무판정 입구 5곳 | 해석 규칙 + 맨 낱말 안전망 |
| 4R | 치환 괄호 속 따옴표(blocking 2) · `call`/`start`/`watch`/`flock` 의 **인용된** agy 경로(blocking 3) · 프롬프트 거짓 양성(major 5) | **판정 방식 분리(이 문서)** |

같은 부류(「해석기가 못 본 셸 꼴」)가 다섯 번 왔다. 4R 의 blocking 2·3 은 해석 규칙을 하나 더 넣어도 6R 에서 다른 꼴로 돌아올 부류다.

## 2. 입구 ↔ 판정 방식 표

| 입구 | 누가 문자열을 쓰나 | 판정 방식 | 판정 호출 자리 | 시험 |
|---|---|---|---|---|
| 일정 `cys schedule add --command`(등록 때) | 등록한 사람·에이전트 → 나중에 데몬이 무인 실행 | ① 낱말 | `src/bin/cys.rs` schedule add · `launch_refusal("", Some(c))` | acceptance E12 · E17 · E18a · 소스 핀 |
| 일정 발화(데몬) | 저장된 문 · 무인 | ① 낱말 | `src/bin/cysd/schedule.rs` `fire_command` | acceptance E13(데몬 `schedule.error` 사유) · 소스 핀(셸 스폰보다 앞) |
| 채널 `cys channel start --cmd` · 데몬 브리지 재스폰 | 저장된 문 · 무인 | ① 낱말 | `src/bin/cys.rs` channel start · `src/bin/cysd/channels.rs` `spawn_bridge` | acceptance E14 · E18b · 소스 핀 |
| 계정 사용량 어댑터(`accounts.json` `adapter:"cmd"`) | 파일 · 주기마다 무인 | ① 낱말 | `src/bin/cysd/accounts.rs` | 소스 핀 · 단위(`names_agy` 변이) |
| `javis_orchestra.py round-log --from-cmd` | 기계검증 명령 · 무인 | ① 낱말(`cys agy-door-check --machine` · cys 없으면 같은 규칙 파이썬) | `cysjavis-pack/bin/javis_orchestra.py` `agy_door_refusal` | acceptance E15 · 팩 `test_round_log_*` 2 · 소스 핀 |
| `cys launch-agent` / `cys restore` / 좌석 내 기동 / `cys boot` (어댑터 cmd) | `agents.json` 어댑터 설정 | ① 낱말(cmd 없으면 키 `gemini`) | `src/bin/cys.rs` `agy_door_refuse_launch` · `agy_door_restore_skip` · `boot_agent_on_surface` | acceptance E1·E2·E3·E5·E7·E8·E9·②E1·②E5 |
| `cys new-surface --cmd` | 좌석 프로그램 명령 | ① 낱말 | `src/bin/cys.rs` new-surface | acceptance E10·E11 |
| phoenix 부활(오라클 = `cys agent-detect`) | 해석된 실행 파일 경로 | ③ 파일 이름(`program_refused` · 폴더 이름 무시) | `src/bin/cys.rs` `apply_agy_door` | acceptance E4·E6 · 팩 D · 단위 `program_path_checks_name_only` |
| 데몬 `surface.create`(r6 · 5R blocking 2) | 원시 RPC · 구판 CLI · 신 CLI(신 CLI 는 자기 판정도 그대로) | ① 낱말(cmd · 선언 agent · cmd 없으면 키 `gemini`) + 실체 한 단계 | `src/bin/cysd/handlers.rs` `surface.create` · `create_refusal` | acceptance E20 · 단위 `create_gate_and_seat_kind_codex_5r_blocking_2_3` · 소스 핀 |
| 데몬 `surface.send_text` 좌석 식별(닫힌 문의 agy 좌석으로 가는 자동 지시 · 직접·`queued`) | 좌석 메타(해석된 실행 파일) · **생성 때 확정한 좌석 종류**(r6) | ③ 파일 이름 + ① 낱말(종류 = `seat_kind_is_agy`) | `src/bin/cysd/handlers.rs` `agy_door_blocks_auto_send` | acceptance E16 · E19 · **E21(5R blocking 3 · queued 포함)** · 소스 핀 |
| 데몬 `surface.send_text` 의 좌석 기동 줄(`agent_launch` 표지 · launch-agent·restore·node-recover 가 붙임) | 기계가 만든 기동 줄 | ① 낱말 | `agy_door_blocks_auto_send` | acceptance E25 |
| 데몬 push 일정 `text_command`(내장·서명 승인 글 · 무인 셸 실행) | 일정 파일 | ① 낱말(발화 때) | `src/bin/cysd/schedule.rs` `run_text_command` | 소스 핀 |
| Claude 자기 Bash(팩 훅 guard `[AGY-RUN]`) | 에이전트가 그 자리에서 | ② 실행 자리(`cys agy-door-check --cmd`) | `cysjavis-pack/hooks/guard.sh` | 팩 `test_agy_run_*` · `test_guard_exec_position_r5` |
| `cys run -- <argv>` | 에이전트·사람이 그 자리에서 | ② 실행 자리(argv) | `src/bin/cys.rs` `run_scoped` | 단위 argv 시험 · cys 소스 핀 |

① 낱말 검사 = `cys::agy_door::names_agy` · ② 실행 자리 검사 = `runs_agy` / `launch_refusal_argv` · ③ 파일 이름 = `program_is_agy`
(실행 파일 **경로** 전용 — 공백 든 경로도 경로 · 마지막 이름 + 심링크 해소 이름. 명령 **문자열**은 ① 이 맡는다 · 5R minor 7).

### ①+ 실체 한 단계 확인(r6 · 5R blocking 1 — 모든 기계 입구 ① 에 덧붙음 · `resolves_to_agy`)
- ⓐ 실행 자리 프로그램이 파일로 있으면(경로 꼴이면 그 파일 · 맨 이름이면 `PATH`) **심링크를 해소한 실제 파일의 마지막 이름**도 본다(`gem-review` → `agy`).
- ⓑ `sh|bash|zsh|dash|… <파일>` · `source <파일>` · `. <파일>` · 셔뱅 있는 글 파일을 직접 실행 = 그 파일을 **한 번만** 읽는다.
  셔뱅 줄은 낱말 검사 · 본문은 셸 글일 때만(셸에 넘겼거나 셔뱅의 **인터프리터**가 셸 — `env` 의 `-S`·`-i`·`-u NAME`·`NAME=값`·`--` 를 건너뛰고
  고른다 · ChatGPT F2) 줄 머리 `#` 주석을 걷고 ② 실행 자리 검사. 파이썬 등 다른 언어 본문은 셸로 읽으면 거짓 양성이 나므로 셔뱅 줄만 본다.
  더 깊이(그 파일이 부르는 파일) 읽지 않는다.
- 읽기 방식(ChatGPT F3): 일반 파일이 아니면 열지 않는다 · 유닉스는 비차단으로 열고 **연 핸들**이 일반 파일인지 다시 본다 · 머리(`#!`)와 본문을
  **같은 핸들에서 한 번** 읽고 읽기 자체를 64KiB+1 바이트로 자른다. 같은 대상은 한 번만 찾는다.
- 상한(ChatGPT F3 · 64KiB 초과 명령과 **같은 방향 = 거부 쪽**): 셸 스크립트가 64KiB 를 넘으면 agy 로 본다 · 한 번의 판정에서 서로 다른 실행 대상이
  64개(`MAX_RESOLVE_TARGETS`)를 넘으면 파일을 하나도 찾지 않고 agy 로 본다(문 닫힘에서 거부). 셔뱅 없는 실행 파일(바이너리)은 크기와 무관하게 이름만.
- 못 읽은 파일은 **통과** + 표시(셸에 넘긴 스크립트 · 직접 실행 파일의 머리 읽기 실패 둘 다 — 판정 결과 세 갈래 Agy/NotAgy/Unread · ChatGPT F5):
  일정 등록 = stderr 「알림: 스크립트 … 를 읽지 못해」 · 일정 발화 = 데몬 이벤트 `schedule.agy_door_unread`.
- 판정 시점: 일정은 등록(CLI)·발화(데몬) 둘 다(acceptance E23 · E13 의 `agyfirescript`) · 채널·계정·launch 어댑터·round-log·new-surface·`surface.create` 는 그 입구의 판정 때.

### ② 의 위치 인자(r6 · 5R major 4)
`sh -c '<글>' <위치 인자…>` 에서 글이 `$0`·`$1`…·`$@`·`$*`(중괄호 꼴 포함)를 쓰면, `$1` 부터를 명령 단위로 판정하고 위치 인자 낱말 하나 전체가
agy 이름이면 agy — 단 `$0` 자리 낱말은 글이 `$0` 을 쓸 때만 본다(ChatGPT F4: `sh -c 'echo "$1"' agy x` 통과). (`cys run -- sh -c 'exec "$@"' sh agy`
거부 · `sh -c 'echo "$1"' sh agy-notes` 통과 · bash·zsh·dash·`env … sh -c` 같은 갈래). 글이 위치 인자를 쓰지 않으면 위치 인자는 보지 않는다(종전).
남는 보수적 거짓 양성: 글이 `$1` 을 **자료로만** 써도(`sh -c 'echo "$1"' sh agy`) 위치 인자 낱말 agy 는 막힌다(실행 문맥 구분은 셸 해석이라 하지 않음).

### ① 낱말 검사 규칙(셸을 해석하지 않는다)
- 영숫자·`.`·`_`·`-` 밖의 모든 글자(따옴표·괄호·역슬래시·경로 구분자·`$`·`=`·`:`·`;` …)를 구분자로 본다.
- 낱말을 소문자로 접고, 끝 점을 떼고, `.exe/.cmd/.bat/.ps1/.com` 을 떼어 `agy` 또는 `antigravity` 와 같으면 agy.
- 줄표로 시작하는 낱말은 끝이 이름이어도 agy(`env -vSagy` · `${X:-agy}` — 옵션 글자에 붙은 값).
- 원문과 「인용·이스케이프 글자(`'` `"` `\` `^` `` ` ``)를 지운 꼴」 둘 다 본다(`a''gy` · `ag\y` · `a^gy`).
- 64KiB 를 넘는 입력은 읽지 않고 agy 로 본다(문 닫힘에서 거부 · 거부 글이 「너무 깁니다」라고 말한다).
- 변이 생성 시험 `machine_word_check_catches_every_mutation`: 이름 2 × 대소문자 3 × 확장자 7 × 경로 머리 6 × 인용·치환 꼴 10 ×
  명령 문맥 17(+ 이름 안 끼움 60) = **42,900꼴 · 이름이 글자로 들어 있는데 통과 0건**.

### ② 실행 자리 검사(guard · `cys run`)에서 바꾼 것(codex 4R major 5 · blocking 3)
- 프롬프트 CLI(`claude` · `codex`)의 인자는 사람 말 — `claude -p agy` · `codex exec agy` 통과. 단 `mcp`(다른 프로그램 등록)·codex
  `sandbox`/`debug`(다른 프로그램 실행)가 보이면 면제하지 않는다.
- PowerShell 출력·조회 명령(`Write-Output` · `Write-Host` · `Get-Command` · `Test-Path` 등)은 조회 전용.
- 안전망: **낱말 하나 전체**가 agy 경로면 인용돼 있어도 agy(`call "C:\…\agy.cmd"` · `watch "/opt/agy"`) — 공백 든 프롬프트 글은 아님.
- 위임(`sh -c` · `cmd /c` · `powershell -Command` · `env -S` · `find -exec` · `su -c` · `script -c` · here-string)은 안쪽을 따로
  판정했으므로 바깥 안전망을 다시 돌리지 않는다(`powershell -Command Write-Output 'agy'` 거짓 양성의 원인).
- 64KiB 상한 · 치환 본문 64개 상한(넘으면 구조를 읽지 않고 agy 낱말 유무로 판정).

## 3. 받아들인 거짓 양성(기계 입구 ①) — 거부 글 원문

막히는 예: 일정·채널·계정 어댑터·round-log·launch-agent 어댑터 cmd 에 `claude -p 'review agy door'` · `echo agy` ·
`command -v agy` · `CLAUDE_CONFIG_DIR=/tmp/agy claude`(폴더 이름 agy) · `/Users/agy/...` 처럼 **사용자 이름이 agy 인 경로를 명령 글자에
적은** 경우. (해석된 실행 파일 경로를 보는 ③ 은 마지막 이름만 보므로 사용자 이름 agy 로는 막히지 않는다.)
막히지 않는 예: `docs/agy.md` · `agy-notes` · `agyx` · `pagy` · `agy를` · `안티그래비티`.

거부 글(문 닫힘 · 기계 입구 · `cys agy-door-check --machine --cmd 'claude -p agy'` 의 stderr 원문):

> agy_consumer_policy: cysr 은 Antigravity(agy) 좌석을 띄우지 않습니다 — 개인 요금제에서 다른 프로그램이 agy 를 부리면 구글 약관상
> 계정이 정지될 수 있기 때문입니다. agy 를 직접 쓰려면 새 탭에서 `agy` 를 치세요(괜찮습니다). 기업 요금제 등 허용된 경우에만, 사람이
> 앱 명령 팔레트의 「Antigravity(agy) 좌석 열기」로 열 수 있습니다. (자동으로 도는 명령 — 일정·채널·계정·복원 같은 것 — 은 셸 문법을
> 해석하지 않고, 글자 안에 「agy」라는 낱말이 하나라도 있으면 막습니다. agy 를 실행하려던 게 아니라 설명 글 등에 그 낱말이 들어 있을
> 뿐이라면, 그 낱말을 다른 말(예: 「안티그래비티」)로 바꿔 다시 등록하세요.)

64KiB 초과(r6 · 5R major 5 — 우회를 처방하던 「스크립트 파일로 옮겨 실행」 안내 삭제): 위 본문 뒤에 「(이 명령은 N바이트로 너무 길어서 —
상한 65536바이트 — 안을 살피지 않고 막았습니다. 명령을 짧게 줄여 다시 등록하세요. agy 를 쓰려던 것이라면, 앱에서 문을 연 뒤 사람이
직접 실행하세요.)」 · `cys run` argv 상한 = Σ(길이+1) 와 인자 개수 4,096(5R minor 8).

### 거짓 양성 표(codex 5R 「문제없다」 ⑤ · r6 의 경로 처리로 줄어든 것만 — 새 규칙 추가 없음)

| 꼴 | ① 기계 입구(낱말) | ② guard·`cys run` | ③ 실행 파일 경로(좌석 메타·agent-detect) | r6 변화 |
|---|---|---|---|---|
| `grep agy log` | 막힘(받아들임) | 통과 | — | 없음 |
| `docs/agy/README` | 막힘(받아들임) | 통과(조회 프로그램 인자) | — | 없음 |
| `/Users/agy/bin/claude -p hi` | 막힘(받아들임) | 통과 | `/Users/agy/bin/claude` = 통과 | 없음 |
| `/Users/agy/Application Support/claude`(공백 든 해소 경로) | 막힘(받아들임 · 명령 글자로 쓰면) | — | **통과**(종전 = 공백 때문에 ① 로 읽어 막힘) | **줄어듦**(minor 7) |
시험 = 단위 `false_positive_table_codex_5r_item_5` · `exe_path_vs_command_string_codex_5r_minor_7`.

## 4. 남는 우회 — 독립 검증 966 의 77꼴에 두 판정을 그대로 대 봄(판정만 · 실행 없음)

| 판정 | 77꼴 중 막힘 | 통과한 꼴 |
|---|---|---|
| 종전(3R · 한 판정) | 57 | 15(아래 10 + 변수 `A=agy; $A` · `${X:-agy}` · `{agy,}` · perl/python exec) |
| **① 낱말(기계 입구)** | **65** | 10(이름이 글자에 없는 꼴 · 아래) + 정상 `claude` · 빈 명령 |
| ② 실행 자리(guard) | 58 | 위 10 + `A=agy; $A` · `${X:-agy}` · `{agy,}` · perl/python exec · `osascript` · `alias x=agy` |

①에서 남던 10꼴 = 전부 **이름이 명령 글자에 없는** 꼴. r5 는 이것을 「원리상 한계」로 묶었으나 codex 5R(blocking 1)이 그중 흔한 꼴은
줄일 수 있다고 지적 → r6 에서 **스크립트 파일(한 단계)·심링크**를 줄였다(위 ①+). 남는 것은 §6 한 곳에 적는다.

| 부류 | 꼴 | r6 |
|---|---|---|
| 글롭 | `~/.local/bin/ag[y]` · `~/.local/bin/ag?` | 남음(§6) |
| 스크립트 파일 | `sh x.sh` · `source x.sh` · `. ./x.sh` | **줄임** — 파일 내용 한 단계 읽기(E23 · 단위) · 두 단계 이상은 §6 |
| 인터프리터 파일 | `python3 x.py` | 남음(§6) — 셔뱅 줄만 본다 |
| 심링크 | `gem-review -p hi`(→ agy 심링크) | **줄임** — 실제 파일 이름(E24 · 단위) |
| 이름 바꾼 **사본**(복사본) | `myai -p hi`(agy 를 복사) | 남음(§6) |
| 실행 시점 조립 | `$(printf 'a%sy' g)` · `sh -c "$(printf 'a%sy' g)"` | 남음(§6) |

②(guard)에만 남는 추가 꼴(변수·`${…}`·중괄호·인터프리터 exec·osascript·alias)과 4R blocking 2(`true $(printf ')'); "/opt/agy"` —
치환 속 따옴표)는 「에이전트가 그 자리에서 일부러 꼬아 쓰는」 꼴이라 선의의 실수 범위 밖 — 알려진 한계로 둔다(브리프 지시 · 더
쫓지 않음). 같은 문을 기계 입구(일정·채널 등)에 넣으면 ① 이 막는다(acceptance E18a).

## 5. 사람 자판(codex 4R major 4)

문이 닫혀 있어도 사람이 그 agy 좌석에 직접 치는 것은 허용이다. 데몬은 「사람 표시(human) ∧ 기계 출처 아님(machine_origin 없음)」이면
운영자 토큰 판독이 실패해도(구 GUI · 토큰 파일 권한) 통과시키고, 배달 원장에 `agy_door: "토큰 미확인 통과"` 를 남긴다(acceptance E19).
`human` 표시는 앱 화면만 붙인다(`cys send` CLI 는 붙이지 않음 — E16 거부). 같은 사용자 권한의 프로그램이 소켓에 `human:true` 를 직접
써서 사람을 흉내 내는 것은 이 판에서 막지 않는다(§6-5) — 토큰이 있어도 같다(같은 사용자는 토큰 파일도 읽는다).

## 6. 한계 — 이 판(1.1.15)에서 막지 않는 것 · 다음 판 계획

이 문은 **실수 방지 장치**다(보안 경계 아님). 판정은 명령 **글자**와 그 글자가 가리키는 파일 **한 단계**까지만 본다. 아래는 이 판에서 막지 않는다:

1. **두 단계 이상 간접** — 스크립트가 부르는 스크립트(`sh outer.sh` → 안에서 `sh inner.sh` → agy) · 파이썬·노드 등 다른 언어 파일 안의 실행(`python3 x.py`).
2. **실행 중 조립** — 이름이 실행 때 계산되는 꼴(`$(printf 'a%sy' g)` · 변수 `A=agy; $A` · 글롭 `ag[y]`).
3. **별칭·셸 함수·환경 변수** — 로그인 셸 설정이 만든 `alias x=agy` · 함수 · `PATH` 를 바꿔 다른 이름이 agy 를 가리키게 하기 · 복사한 사본(`cp agy myai`).
4. **맨 셸 좌석에 글로 쳐 넣기** — 표지(`agent_launch`) 없이 빈 셸 좌석에 `agy` 를 입력하는 자동 지시(데몬은 지시 글 내용을 판정하지 않는다 —
   걸면 「agy」 낱말이 든 모든 지시가 막힌다). 표지가 있는 기동 줄은 막는다(E25).
5. **같은 사용자 권한의 고의** — 문 파일 직접 쓰기(표지 = 공개 상수) · 소켓에 사람 표시(`human:true`)를 위조한 요청.
6. **앱 두 벌 동시 문 조작 경합** — r6 에서 옆 잠금 파일의 OS 배타 잠금(`agy-seat-door.json.lock`)으로 직렬화했다(5R minor 6). 잠금 대기는
   5초 상한(넘으면 「다른 창이 지금 agy 좌석 문을 여닫는 중이에요. 잠시 뒤 다시 눌러 주세요.」) · 잠금 파일이 읽기 전용이면 읽기 핸들로 잠근다 ·
   열 수 없으면 「문을 바꾸지 못했어요 … 문은 그대로입니다」(ChatGPT F6 · 잠금 파일을 지우라고 안내하지 않는다). 남는 것: 잠금을 지원하지 않는
   파일 시스템(네트워크 홈 등)에서는 잠금 실패 = 문 쓰기 실패로 보고된다(닫힘 유지 · 안전 쪽). `File::lock`/`try_lock` = Rust 1.89.0 안정화 —
   저장소에 `rust-toolchain`·`rust-version` 고정 없음 · CI 는 `dtolnay/rust-toolchain` stable · 이 기계 1.97.0.
7. **판정 때와 실행 때의 차이** — 일정 등록 뒤 스크립트 내용이 바뀌면 발화 때 다시 읽는다(한 단계). 발화 판정과 실제 실행 사이의 짧은 틈에
   파일을 바꾸는 것은 막지 않는다. 데몬이 쓰는 `PATH`·현재 폴더가 실제 셸(로그인 프로파일)의 것과 다를 수 있다 — 못 찾은 파일은 통과.
8. **윈도우 실기** — PowerShell·`call`/`start`·`cmd /c` 갈래는 코드 경로만 맞췄고 윈도 실기에서 확인하지 않았다.

다음 판 계획(구현 안 함 · 이 판 범위 밖): **데몬이 시작된 프로세스의 실체를 확인**한다 — 기계 입구(일정·채널·좌석 생성·자동 지시)가 띄운
프로세스 트리에서 실행 파일 실체(경로·서명)가 agy 이면 문이 닫혀 있을 때 그 자리에서 멈춘다(위 1~4 를 글자 해석 없이 한 번에 닫는 길) ·
문 상태를 앱 서명·데몬 단일 기록자에 묶기(5).

## 7. 데몬 입구 전수 표(r6 · 5R blocking 2 — 「CLI 에만 판정이 있고 데몬 핸들러엔 없는 입구」 찾기)

조사 방법(재현 가능): `grep -n "\.openpty(\|\.spawn_command(" src/bin/cysd/*.rs` = 운영 코드의 PTY 생성은 `state.rs` `create_surface_with_env`
한 곳(그 밖 `handlers.rs:34124` 등은 시험 모듈) · 그 함수의 운영 호출부 = `handlers.rs` `surface.create` 한 곳(같은 파일 5753행 주석과 grep 일치) ·
`grep -n "Command::new(\|hidden_command(\|command_shell()" src/bin/cysd/*.rs`(시험 파일 제외)로 프로세스 생성 자리 전수.

| 입구 | CLI 판정 위치 | 데몬 판정 위치 | 시험 |
|---|---|---|---|
| 좌석 생성 `surface.create`(new-surface · launch-agent · restore · GUI 새 탭 · 원시 RPC) — **유일한 PTY 생성 자리** | `cys.rs` new-surface `launch_refusal` | **r6 신설** `handlers.rs` `surface.create` → `create_refusal`(PTY 전) | acceptance E20 · 단위 · 소스 핀 |
| 자동 지시 `surface.send_text`(직접) → agy 좌석 | — | `agy_door_blocks_auto_send`(메타 · **좌석 종류** r6) | E16 · E19 · E21 |
| 자동 지시 `surface.send_text {queued}` → 큐 → watchdog 배달 | — | **r6 신설** 큐에 넣기 전 같은 판정(종전 = 큐 경로에 판정 없음) | E21(`rpc_queued`) |
| 좌석 기동 줄 `surface.send_text {agent_launch}`(launch-agent·restore·node-recover·좌석 내 기동의 데몬 쪽) | `cys.rs` `boot_agent_on_surface` · `agy_door_refuse_launch` · `agy_door_restore_skip` | **r6 신설** `agy_door_blocks_auto_send`(기동 줄 낱말) | E25 · E1·E2·E3·E5 |
| 일정 `--command` 등록 / 발화 | `cys.rs` schedule add(+ 못 읽은 스크립트 알림) | `schedule.rs` `fire_command`(+ `schedule.agy_door_unread`) — 등록 RPC 없음(일정 = 파일) | E12·E13·E23 |
| 일정 push `text_command` | (CLI 등록 경로 없음 — 내장·서명 승인 글) | **r6 신설** `schedule.rs` `run_text_command` | 소스 핀 |
| 채널 브리지 시작 / 재스폰 | `cys.rs` channel start | `channels.rs` `spawn_bridge` | E14 · E18b · E24 |
| 계정 사용량 어댑터 `adapter:"cmd"` | (파일) | `accounts.rs` `spawn_custom_adapters` 주기마다 | 소스 핀 |
| round-log `--from-cmd` | 팩 `javis_orchestra.py`(`cys agy-door-check --machine`) | (데몬 무관 — 팩이 직접 실행) | E15 |
| `cys run -- <argv>` | `cys.rs` `run_scoped`(argv) | (데몬 무관 — CLI 가 직접 실행 · 원장만 데몬) | E22 · 단위 |
| node-recover(데몬 워치독 `governance.rs` → `cys node-recover`) | `boot_agent_on_surface` | 기동 줄 = `agent_launch` 판정(위) · 메타가 agy 인 좌석 = 좌석 판정 | E2 |
| auto-restore(`main.rs` → `cys restore`) | `agy_door_restore_skip` | 기동 줄 = `agent_launch` 판정 | E3 · E5 |
| 고정 프로그램만 띄우는 자리(판정 불요 — 사용자 글이 실행 파일이 되지 않음): `boot_supervisor.rs`·`main.rs`(동봉 python + 팩 스크립트) · `cycle_jobs.rs`(cys cycle-agent) · `state.rs`(python `--wire-seat`) · `handlers.rs` `dept.run`(cys-dept) · `system.spawn_outside_job`(윈 허용 목록 chrome·seat_restart · `job_exit::validate`) · hwmon·locale·taskkill | — | — | — |

표에 없는 데몬 프로세스·PTY 생성 자리 = 0(위 grep 범위 · 시험 파일 `*_tests.rs` 와 `#[cfg(test)]` 모듈 제외).

### §7-1 범위 넓혀 다시(r6 2회차 · ChatGPT 「표 밖 0 입증 불가」에 대한 답)
명령: `grep -rEn 'Command::new\(|hidden_command\(|python_command\(|\.spawn_command\(|\.openpty\(|posix_spawn|libc::exec|libc::fork|execvp|CommandBuilder::new\(' src --include='*.rs'`
(`src/bin/cys.rs`(CLI — 입구별 판정은 §2 표)·`*_tests.rs` 제외) = **199줄** · 그중 시험 모듈 앞(운영 코드) **60줄**을 감싼 함수로 전부 분류했다:
- 사용자·파일 글이 실행 파일이 되는 자리 = `accounts.rs` `spawn_custom_adapters`(sh/cmd 2) · `channels.rs` `spawn_bridge`(2) · `schedule.rs` `fire_command`·
  `run_text_command` · `state.rs` PTY(`create_surface_with_env` — 위 grep 의 `.openpty`/`spawn_command` 는 같은 함수) → **전부 판정 있음**(§7 표).
- 고정 프로그램 = `boot_supervisor.rs`·`main.rs`(동봉 python + 팩 스크립트 · auto-restore = 팩 phoenix 복원기 → agent-detect 판정)·`teamtoken.rs`(python)·
  `cycle_jobs.rs`·`governance.rs`(cys node-recover · taskkill)·`schedule.rs` `launch_via_cli`(cys launch-agent → CLI 판정)·`handlers.rs`(`spawn_outside_job` 윈 허용 목록 ·
  `dept.run` = cys-dept)·`hwmon`·`usage`(lsof)·`state.rs`(defaults·locale)·`pty_test_support`.
- 라이브러리(`src/*.rs` · `src/update/*`) = 업데이터·초기화·launchd·앱 묶음(launchctl·codesign·ditto·curl·unzip 등 고정 도구) · `lib.rs` 의 `hidden_command`/`python_command`
  (래퍼 자체 — 호출부가 위 목록) · `agy_statusline.rs` `probe_spawn`(윈도우 전용 · cys 자기 상태줄 훅을 agy 와 같은 방식으로 한 번 실행 — agy 실행 아님).
- **새 입구 0** — 단, grep 은 완전성 증명이 아니다(함수 포인터·동적 조립 인자는 위 함수들 안의 값으로만 들어온다는 것까지가 확인 범위).

### §7-2 지연 실행 전수(적재·등록 때만 판정하고 실행 때 재판정이 없는 꼴 · ChatGPT F1)
| 지연 실행 | 적재·등록 때 판정 | 실행 때 판정 |
|---|---|---|
| 자동 지시 큐(`send_text {queued}` · 빈 좌석 보류 `hold_for_vacant_seat` · 정비 모드 보류 재생 `update_hold` · 알림 등 큐 생산자 전부) → watchdog 틱·`queue.deliver` | 있음(`queued` 갈래) | **r6 2회차 신설** — `governance.rs` `deliver_head_locked` 머리의 `drop_agy_door_closed`(PTY 쓰기 전 · 폐기 + 원장 묘비 `agy_consumer_policy` + `queue.dropped`) · 사람 자판 적재(`send_human`)는 통과 · acceptance **E26** |
| 일정 `--command` 발화 | 있음(CLI) | 있음(`fire_command`) |
| push 일정 `text_command` | (등록 경로 없음) | 있음(`run_text_command`) |
| 채널 브리지 재스폰 | 있음(CLI) | 있음(`spawn_bridge` 매 스폰) |
| 계정 어댑터 주기 실행 | (파일) | 있음(주기마다) |
| 복구 기동(node-recover · auto-restore · phoenix) | — | 있음(실행 때 CLI·오라클 판정 + 데몬 `agent_launch` 기동 줄 판정) |
