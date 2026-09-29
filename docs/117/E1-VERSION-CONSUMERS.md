# E1 — `--version` 출력 「cys X」 → 「cysr X」 소비처 전수표 (TICKET=cysr-117-impl-brand · master#6c71c56e 요청)

- 측정: 2026-09-29 19:3x · 151 SPLIT 의 「숫자 정규식 무해」 판정을 **다시 잰 것**(grep 원문 = 아래 파일:줄).
- 범위: ①설치기(`~/axdev/jarvis-habitat/install-master` · 사본 `~/axdev/jarvis-install`) ②우리 스크립트(`~/.claude/channels/*` · 설치본 `~/.cys/pack/{bin,hooks}`) ③저장소(fix/117-brand) ④서버(`~/axdev/ai-jarvis/web-install` 원격 보고 칸).
- 판정 기준: 「cys 」 접두 의존(깨짐) / 숫자만 추출(무해) / 원문 표시·기록(무해 · 표시 글자만 바뀜) / 성공 여부만(무해).

| # | 소비처(파일:줄) | 무엇을 하나 | 모양 | 판정 |
|---|---|---|---|---|
| 1 | habitat `bootstrap.sh:3324-3328` `cys_app_exec_ok` | 설치 뒤 실행 확인 | `case "$out" in *[0-9].[0-9]*)` | 숫자만 · 무해 |
| 2 | habitat `bootstrap.sh:3680-3690` CLI 고르기 | 이번 판이 답하는 길 선택 · 판 대조 | `case "$v" in *"$CYS_FORK_VERSION"*)` (부분 일치) | 숫자 부분 일치 · 무해 |
| 3 | habitat `bootstrap.sh:3691-3698` | 화면 「[7/10] cys 가 답합니다: $ver」 | 원문 표시 | 무해(화면에 「cysr 1.1.7」로 보임 — 문구 「cys 가 답합니다」와 섞임 · 표시만) |
| 4 | habitat `bootstrap.sh:4564-4569` `rotate_skip_depts_flag` | 1.1.3 이상이면 --skip-depts | `grep -oE '[0-9]+\.[0-9]+\.[0-9]+'` | 숫자만 · 무해 |
| 5 | habitat `bootstrap.sh:1189-1193` `cys_version_line` → `:388` 원격 보고 `PG_ENV_CYS_VER` · `:1925` 표 행 | 기록·표시 | 원문 | 무해 |
| 6 | habitat `bootstrap.ps1:1051-1055` `Get-CysVersionLine` → `:1534` 표 행 | 표시 | 원문 | 무해 |
| 7 | habitat `bootstrap.ps1:3432-3441` CLI 고르기·「[7/10] cys 가 답합니다」 | 성공 여부 + 원문 표시 | `if ($ver)` | 무해(표시만) |
| 8 | habitat `bootstrap.ps1:3793-3798` `Get-RotateSkipDeptsFlag` (← `:3810`) | 1.1.3 이상 판정 | 정규식 `([0-9]+)\.([0-9]+)\.([0-9]+)` | 숫자만 · 무해 |
| 9 | habitat `checks.sh:136-141·886` | 설치기 자기 시험(코드에 `cys --version` 문자열이 있는지) | 소스 grep | 무해(출력 무관) |
| 10 | `~/axdev/jarvis-install/bootstrap.sh:3324·3688` | habitat 과 같은 줄(사본) | 1·2 와 같음 | 무해 |
| 11 | `ai-jarvis/web-install/src/telemetry.ts:130` `ENV_TEXT_KEYS` `cys_ver` | 원격 보고 칸 저장 | 글자로 받아 지우고 자름(파싱 없음) | 무해 |
| 12 | `~/.claude/channels/*` | — | `cys --version` 파싱 0건(`cmux-layout-guard.sh:360` 은 claude 인자 판별 · 무관) | 해당 없음 |
| 13 | 팩 `bin/javis_phoenix.py:192-195` `_extract_version` | 진단 로그 | `\d+\.\d+\.\d+` | 숫자만 · 무해 |
| 14 | 팩 `bin/javis_fleet_report.py:205-209` | 설치본 vs 소스 판 비교(advisory) | `(\d+\.\d+\.\d+\S*)` | 숫자만 · 무해 |
| 15 | 팩 `bin/javis_bootstrap.py:767-768` `_binary_version` | 부트 보고 원문 | 첫 줄 원문 | 무해 |
| 16 | 팩 `bin/javis_reconstruct_state.py:347` | 상태 재구성 원문 | 원문 | 무해 |
| 17 | 팩 `hooks/session-start.sh:62-63` | 세션 시작 주입 원문 `CYS_VER` | 원문 | 무해 |
| 18 | 저장소 `scripts/deploy_gate.py:312-315` | 스모크(rc 0 + 원문 출력) | rc | 무해 |
| 19 | 저장소 `windows-build.yml:223-225` A1 | cys·cysr 두 출력이 **서로 같은가** | 상호 비교 | 무해(둘 다 「cysr X」) |
| 20 | 저장소 `windows-build.yml:853-854` T4-14 | `$vOut -match [regex]::Escape($expVer)` | 숫자 부분 일치 | 무해 |
| 21 | 저장소 팩 시험 스텁(`test_bootstrap_chain.py:62` 등 · `run_bootstrap_health.py:2541`) | 가짜 cys 가 「cys 0.0.0-stub」 출력 | 스텁 자체 문자열(실 바이너리 무관) | 무해 |

**결론: 「cys 」 접두에 의존해 깨지는 소비처 = 0건.** 바뀌는 것은 설치기 화면 3·7 의 표시 한 줄(「cys 가 답합니다: cysr 1.1.7」 — 문구와 이름이 섞여 보임)뿐이고 이는 다른 저장소(설치기)라 이 티켓에서 고치지 않는다(설치기 문구를 cysr 로 바꿀지 = 설치기 티켓 후보).
한계(정직): grep 모양 `cys(.exe)? --version` · `'--version'` 인자 배열 기준 — 셸 변수로 조립한 호출 이름(예 `"$cli" --version`)은 1·2·5 처럼 따로 읽어 확인했고, 그 밖 저장소(`hybrid-jarvis`·`jarvis-platform`)는 0건.
