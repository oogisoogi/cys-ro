# agy 좌석 문 — 입구별 판정 방식 (TICKET=cysr-agy-door-r5 · codex 4R 처분)

> 문의 목적(바뀌지 않음): cysr 제품과 **선의의** 에이전트가 **실수로** agy(구글 Antigravity CLI)를 자동 실행하는 길을 막는다.
> 같은 사용자 권한으로 하는 **고의** 우회를 막는 보안 경계가 아니다(아래 「원리상 한계」).

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
| 데몬 `surface.send_text` 좌석 식별(닫힌 문의 agy 좌석으로 가는 자동 지시) | 좌석 메타(해석된 실행 파일) · 좌석 cmd | ③ 파일 이름 + ② 실행 자리 | `src/bin/cysd/handlers.rs` | acceptance E16 · E19(사람 자판 통과·대조) · 소스 핀 |
| Claude 자기 Bash(팩 훅 guard `[AGY-RUN]`) | 에이전트가 그 자리에서 | ② 실행 자리(`cys agy-door-check --cmd`) | `cysjavis-pack/hooks/guard.sh` | 팩 `test_agy_run_*` · `test_guard_exec_position_r5` |
| `cys run -- <argv>` | 에이전트·사람이 그 자리에서 | ② 실행 자리(argv) | `src/bin/cys.rs` `run_scoped` | 단위 argv 시험 · cys 소스 핀 |

① 낱말 검사 = `cys::agy_door::names_agy` · ② 실행 자리 검사 = `runs_agy` / `launch_refusal_argv` · ③ 파일 이름 = `program_is_agy`.

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

64KiB 초과: 위 본문 뒤에 「(이 명령은 N바이트로 너무 길어서 — 상한 65536바이트 — 안을 살피지 않고 막았습니다. 명령을 짧게 줄이거나
스크립트 파일로 옮겨 그 파일을 실행하게 하세요.)」

## 4. 남는 우회 — 독립 검증 966 의 77꼴에 두 판정을 그대로 대 봄(판정만 · 실행 없음)

| 판정 | 77꼴 중 막힘 | 통과한 꼴 |
|---|---|---|
| 종전(3R · 한 판정) | 57 | 15(아래 10 + 변수 `A=agy; $A` · `${X:-agy}` · `{agy,}` · perl/python exec) |
| **① 낱말(기계 입구)** | **65** | 10 원리상 한계 + 정상 `claude` · 빈 명령 |
| ② 실행 자리(guard) | 58 | 위 10 + `A=agy; $A` · `${X:-agy}` · `{agy,}` · perl/python exec · `osascript` · `alias x=agy` |

①에서 남는 10꼴 = 전부 **이름이 명령 글자에 없는** 꼴 — 줄일 수 있는 것 0:

| 부류 | 꼴 | 왜 원리상 못 막나 |
|---|---|---|
| 글롭 | `~/.local/bin/ag[y]` · `~/.local/bin/ag?` | 이름이 실행 때 파일 목록에서 만들어진다 |
| 스크립트 파일 | `sh x.sh` · `source x.sh` · `. ./x.sh` | 이름이 다른 파일 안에 있다 |
| 인터프리터 파일 | `python3 x.py` | 같음 |
| 이름 바꾼 사본 · 심링크 | `gem-review -p hi` · `myai -p hi` | 실행 파일 이름 자체가 다르다 |
| 실행 시점 조립 | `$(printf 'a%sy' g)` · `sh -c "$(printf 'a%sy' g)"` | 이름이 실행 때 계산된다 |

②(guard)에만 남는 추가 꼴(변수·`${…}`·중괄호·인터프리터 exec·osascript·alias)과 4R blocking 2(`true $(printf ')'); "/opt/agy"` —
치환 속 따옴표)는 「에이전트가 그 자리에서 일부러 꼬아 쓰는」 꼴이라 선의의 실수 범위 밖 — 알려진 한계로 둔다(브리프 지시 · 더
쫓지 않음). 같은 문을 기계 입구(일정·채널 등)에 넣으면 ① 이 막는다(acceptance E18a).

## 5. 사람 자판(codex 4R major 4)

문이 닫혀 있어도 사람이 그 agy 좌석에 직접 치는 것은 허용이다. 데몬은 「사람 표시(human) ∧ 기계 출처 아님(machine_origin 없음)」이면
운영자 토큰 판독이 실패해도(구 GUI · 토큰 파일 권한) 통과시키고, 배달 원장에 `agy_door: "토큰 미확인 통과"` 를 남긴다(acceptance E19).
`human` 표시는 앱 화면만 붙인다(`cys send` CLI 는 붙이지 않음 — E16 거부). 같은 사용자 권한의 프로그램이 소켓에 `human:true` 를 직접
써서 사람을 흉내 내는 것은 원리상 한계다 — 토큰이 있어도 같다(같은 사용자는 토큰 파일도 읽는다).

## 6. 원리상 한계(그대로) · 다음 판 후보

- 같은 사용자로 도는 프로그램의 문 파일 직접 쓰기(표지 = 공개 상수) · 위 §4 의 10꼴 · 사람 흉내 소켓 요청.
- 다음 판 설계 후보(구현 안 함): C = 데몬이 실행 파일 실체로 agy 프로세스를 찾아 끄는 사후 감시 · D = 문 상태를 앱 서명에 묶기.
