# HANDOFF · TICKET=cysr-1111-adv-fixes · 2026-10-22 · worker-5(surface:1588)

가지 `fix/1111-adv-fixes` ← int/1111 `3a366520` · worktree `~/cys-terminal-src-wt/1111-advfix`.
출처 = 587 적대 검토 보고서 `~/axdev/master/briefs/2026-10-22-cysr-1111-adv-review-REPORT.md`(발견 11).
고친 것 = #1 · #2 · #4 · #5 · #6 · #9(커밋 1건씩 · 각 건 재현 적 → 수리 → 녹 → 뮤턴트 적). 손대지 않은 것 = #3 · #7 · #8 · #10 · #11(§3).
push·태그·판번·설치·발행·윈 기기 = 0.

## 1. 커밋

| # | 커밋 | 바뀐 파일 | 한 줄 |
|---|---|---|---|
| 1 | `f4ac435e` | `cysjavis-pack/bin/cys-dept` · `tests/test_d1_dept_ready_probe.py` · `tests/test_dept_name_guard.py` | 락 파일의 낡은 pid 를 재사용한 cysd 아닌 산 프로세스를 「산 승자」로 보지 않는다 |
| 4 | `125bf87c` | `src-tauri/nsis/cys-runtime-prune.ps1` · `scripts/tests/nsis-hook-compile/run.sh`(N11) | dist-info 이름/판 경계 = 마지막 `-` |
| 6 | `5d2bd975` | `tests/test_d1_dept_ready_probe.py` | d1 픽스처 락을 실물처럼 줄바꿈 없이 |
| 5 | `39cee656` | `ui/src/trashwiring.test.ts` | 크기 미리 보기 단추 — 열림 표시 잠금·해제 순서와 흐림 판정 고정 |
| 9 | `fba273de` | `src-tauri/nsis/cys-samebytes.ps1` · `run.sh`(N10) | PowerShell 제한 언어 모드에서도 같은 바이트 판정 |
| 2 | `b2a4b0f7` | `src/bin/cysd/trash.rs` | `c4_run` · 경쟁 검체에 `#[cfg(unix)]` |

## 2. 건별 — 재현 · 수리 · 뮤턴트

### #1 boot_lock_winner — pid 재사용 오인 (`cys-dept` boot_lock_winner)

- **재현(적)**: d1 새 모드 `lost_reused` = 우리 데몬은 즉사하고 락에는 **관계없는 산 `sleep` 의 pid**. HEAD 에서 새 시험
  `test_lock_pid_reused_by_a_live_non_cysd_process_still_fails_fast` → `33.1초 not less than 10 — 상한까지 헛대기`(정지 예산 30초를 다 씀 + 「다른 산 데몬」 거짓 안내).
- **수리**: `kill -0` 뒤에 `ps -p "$h" -o comm=` 의 끝 이름이 정확히 `cysd` 인지 본다(조회 실패 = 아님 = 종전 조기 실패).
  실 cysd `deadman::pid_is_cysd`(sysinfo 이름의 끝 이름 == `cysd` · 실패 = false)와 같은 판정이다. 맥 `ps comm` = 실행 경로(argv0) · 리눅스 = 실행 파일 이름(15자).
  윈도는 락 파일이 없어(`acquire_startup_lock` 이 `#[cfg(unix)]`) 이 줄에 닿지 않는다(동작 무변경).
- **시험 승자 신원 교체(필수 동반)**: 종전 승자는 `sleep`(d1)·파이썬(name_guard)이라 수리 뒤에는 승자가 아니게 된다.
  - d1 `lost_win`·`lost_never`: 승자 = `sleep` 을 `$T/w/cysd` 심링크로 실행(맥 comm = argv0 경로 · 리눅스 comm = 심링크 이름 = `cysd`). `lost_win` 의 「2초 뒤 응답」은 별도 서브셸이 `up` 을 세운다.
  - name_guard 경쟁 승자: 신원 = 이름이 `cysd` 인 대리 프로세스(같은 심링크 방식) · 파이썬 조정자는 `GUARD_WINNER_PID` 로 그 pid 를 락·소켓에 공개만 한다. 정리는 둘 다 거둔다.
  - 교체 전(수리본 + 옛 파이썬 승자): `test_create_spawn_loser_preserves_live_winner` **10회 중 2회 적** → 교체 뒤 **10/10 녹**.
- **녹**: d1 `DeptFirstBootWait` 9건 OK(98초) · name_guard 75건 OK.
- **뮤턴트**: 이름 판정 → `true` = `lost_reused` 적(33.4초). 강제 경주(boot_wait 의 핑과 `kill -0` 사이 `sleep 0.4` 주입) 수리본: name_guard 경쟁 5/5 녹 · d1 `lost_win` 녹(승자 대기 경로가 실제로 산다).
- 맥 `ps` 실측: 실 cysd(pid 989) `comm` = `/Applications/cy…/cysd` · `ucomm` = `cysd`. `exec -a cysd sleep` 은 맥 `comm` = `cysd`(argv0) · 복사한 `/bin/sleep` 은 맥에서 SIGKILL(137)로 죽어 쓰지 않았다.

### #2 trash `c4_run` · 경쟁 검체 `#[cfg(unix)]`

- **재현(적)**: 윈 기본 빌드 흉내 = `src/lib.rs` `trash_delete_supported` 의 `cfg!(windows)` → `true`(삭제 꺼짐) + c4 영역의 `#[cfg(unix)]` → `#[cfg(any())]`(윈에는 없음).
  HEAD: `cargo test --bin cysd -- trash::tests::c4` → `c4_a_reset_from_another_test_cannot_land_between_the_confirm_and_the_delete ... FAILED` · `panicked at src/bin/cysd/trash.rs:3266:9`(단언 `trash_root_missing`).
- **수리**: `c4_run` 과 경쟁 검체에 `#[cfg(unix)]`(본문을 떼어 낸 원 검체와 같은 문).
- **녹**: 같은 흉내 → c4 검체 0개 · `0 failed`. 흉내 해제(맥 정상) → c4 2 passed. win-typecheck rc 0(오류 0 · trash.rs 경고는 기존 `:1057 execute_one` 1건뿐).
- 흉내 편집은 커밋 전에 되돌렸다(`git diff` 로 확인).

### #4 `cys-runtime-prune.ps1` Get-DistKey

- **재현(적)**: N11 에 넣은 사례 — 실린 `python-dateutil-2.9.0.dist-info` + 사용자 `python-jose-3.3.0.dist-info`. HEAD(`IndexOf`) pwsh 7 실행 → `FAIL[N11]: … user-dist-info-with-dash-in-name-removed`.
- **수리**: `LastIndexOf('-')`(정규화된 판에는 `-` 가 없고 비정규 이름에는 있을 수 있다 → 마지막 `-` 가 경계).
- **녹**: `scripts/tests/nsis-hook-compile/run.sh` 전부 OK. N11 에 같이 넣은 양성: 실린 이름의 낡은 판 `python-dateutil-2.8.2.dist-info` 는 지워진다(요약 `removed=3`) · 실린 `python-dateutil-2.9.0` 은 남는다.
- **뮤턴트**: `IndexOf` 되돌림 = 위 재현 그대로 적.
- 한계: 판에 `-` 가 든 비정규 dist-info(예 `foo-1.0-beta`)는 키가 어긋나 「남김(kept)」 쪽으로 간다 — 지우지 않는 쪽이라 안전.

### #5 UI 시험 공백(b73fb075)

- 새 시험 2건(`ui/src/trashwiring.test.ts`):
  - `trashPreviewOnlyFlow`: 첫 줄이 `if (trashPreviewOnlyOpen) return;` · 잠금(`= true`)이 `await trashConfirmModal(names, true)` 앞 · 해제(`= false`)가 그 뒤 · 해제 뒤 `trashSyncPreviewButton(true)`.
  - `trashSyncPreviewButton`: 「고른 항목 삭제」 단추 시험과 같은 방식으로 본문 바이트 고정.
- **뮤턴트**(각각 `src/main.ts` 한 곳 · 매번 원본 복원): M-D1 가드 제거 · M-D2 `btn.disabled = false` · **M-D3 해제 제거(단추 영구 흐림)** → 모두 `52 pass 1 fail`(적). 기준 `53 pass 0 fail`.
- 운영 코드 변경 0.

### #6 d1 픽스처 락 줄바꿈

- `echo "$pid" >` → `printf %s "$pid" >` 4곳(lost_dead·lost_win·lost_never·lost_reused) — 실물 `deadman::claim_lock` 의 `write!(file,"{pid}")` 와 같은 꼴.
- **뮤턴트 M7**(`|| [ -n "$h" ]` 제거 = 줄바꿈 없는 락을 못 읽음): 이제 d1 `lost_win` 적 — `'데몬 기동 실패' unexpectedly found … 락을 쥔 산 승자를 버리고 실패했다`. (보고서 기준: 종전 d1 은 생존 · name_guard 1건만 잡았다.)
- **녹**: d1 15건 OK(115초).

### #9 samebytes — PowerShell 제한 언어 모드

- **재현(적)**: 맥 pwsh 7 세션에서 `$ExecutionContext.SessionState.LanguageMode='ConstrainedLanguage'` 뒤 헬퍼 실행 → 같은 바이트 `2` · 다른 바이트 `2`(완전 모드는 0·1). `Get-FileHash` 는 같은 세션에서 해시를 냈다.
  N10 에 제한 모드 4행 추가 → HEAD `FAIL[N10]: … under ConstrainedLanguage — same=2 (want 0) · diff=2 (want 1) · size=1 · missing=2`.
- **수리**: `Get-Sha256Hex` 에서 언어 모드가 `FullLanguage` 가 아니면 `Get-FileHash -Algorithm SHA256` 으로 해시. 완전 모드는 종전 공유 열기(`FileShare ReadWrite+Delete`) 그대로. 한 호출의 두 파일은 같은 갈래를 타므로 비교 문자열 꼴이 같다.
- **판정 불가 시 기존 동작 유지**: 파일 없음 등은 여전히 `2` = 교체(N10 missing=2 · 제한 모드 missing=2).
- **P10-a 회귀 판정**: 수리로 제한 모드 기계의 같은 판 재설치가 `0`(무행동)이 되어 「prev 신규 0」 기대가 **회복**된다. 완전 모드 경로는 바이트 무변경이므로 기존 P10-a 판정 그대로.
- **녹**: run.sh 전부 OK · N10 `same=0 diff=1 size=1 missing=2 no-args=2; ConstrainedLanguage same=0 diff=1 size=1 missing=2` · 헬퍼 ASCII 0줄 위반.
- **뮤턴트**: 대체 경로가 상수 `'x'` 반환 → `FAIL[N10] … diff=0 (want 1)`.
- **윈 실기 몫(미확인)**: ① Windows PowerShell 5.1 의 `Get-FileHash` 가 제한 모드에서 실제로 허용되는지(시스템 모듈 = 신뢰 경로 · 맥 pwsh 7 로는 5.1 을 못 잰다) ② 그것이 **실행 중 이미지**(cys.exe·cysd.exe)를 여는지(내부 공유 모드가 우리 공유 열기와 다를 수 있다 — 못 열면 `2` = 교체 = 종전과 같은 안전 쪽) ③ 실제 AppLocker/WDAC 기계에서 같은 판 재설치 prev 신규 0. 같은 의존(.NET 정적 호출)이 기존 unlock-sweep 에도 있다(보고서 §9 · 범위 밖).

## 3. 손대지 않은 것

### #3 (윈 실기 몫) launch-agent 부트 ready 판정의 `contents()` 재료 — 윈 확인 절차

재료 차이만 실측돼 있다(보고서 §3: 픽스처 `winq2_conpty_redraw(WQ_IDLE_FULLSCREEN)` 에서 `leading_marker` 맥 `Some("❯")` · 윈 `None`). 영향은 윈 실기로만 판정된다.

1. 윈 실기(ConPTY)에서 이 가지의 판(또는 int/1111)으로 데몬을 띄운다.
2. **처음 여는 폴더**(폴더 신뢰 창이 뜨는 곳)에서 fullscreen claude 좌석을 `cys launch-agent --role worker --agent claude` 로 띄운다 — 부트 중 관문을 한 번 보게 하는 것이 핵심이다.
3. 신뢰 창을 사람이 통과시킨 뒤, launch-agent stderr 를 본다:
   - `[launch-agent] ready(…) — 주입 안전` 이 나오면 → 영향 없음(보고서 §3 의 추론이 실기에서 성립하지 않음).
   - `[launch-agent] 관문 증거 이월 보류: …` 가 찍힌 채 부트 시간 초과로 끝나면 → 재현. 판정 경로 = `src/bin/cys.rs:16634-16645`(`pick_marker_leading_on_screen` 재료 = 데몬 `surface.read_text` 의 `screen().contents()` · `handlers.rs:7561-7567`) → `gate_carry_ok`(17202) 의 `None if glyph_off_composer => false`.
4. 재현되면 수리 방향 = WINQ-2(c41e12f4)와 같은 방식 — 부트 ready 판정의 레이아웃 재료를 물리 행(`screen_rows_text`)으로.
5. 같은 기기에서 classic(비 fullscreen) 좌석도 한 번 띄워 대조한다(맥과 같은 ready 기대).

### #7 (PLAUSIBLE · 신규 회귀 아님)

승자 대기가 정지 예산으로 끝나면 `boot_fail_teardown` 이 승자의 소켓·등록을 지운다(`cys-dept:2606·2882·3215` → 1322-1336). 종전 조기 실패도 같은 정리 경로를 탔으므로 1.1.11 이 만든 회귀가 아니다. 「산 승자가 있으면 소켓·등록 삭제를 건너뛴다」는 설계 판단 사항이라 손대지 않았다(시험 `lost_never` 의 `assertFalse(self._reg_has_probe())` 가 지금 동작을 고정하고 있다).
참고: #1 수리로 「산 승자」 판정이 cysd 로 좁아져, 재사용 pid 때문에 이 갈래에 들어가는 경우는 없어졌다.

### #8 (PLAUSIBLE · 신규 회귀 아님 · fail-closed)

같은 판 재설치 + 잠긴 낡은 `.new` = 종전 성공 → 이제 `stale-new-locked` 거부(exit 3/4). 판이 다른 업그레이드와 같은 규칙이고 안전 쪽이며 드물다. P10-a 체크리스트에 「같은 판 재설치 + 잠긴 낡은 .new = 거부(정상)」 한 줄을 적어 두기를 권고(체크리스트 문서는 이 티켓 범위 밖이라 고치지 않았다).

### #10 (문서 부정확 · 운영 무영향)

`trash.rs:535-562` 의 가짜 시계가 세션 예산·항목별 상한·양보 간격 세 판정 모두에 걸린다(커밋 ff6225f5 설명은 「항목별 상한·양보 간격은 실제 시계」). `FAKE_SESSION_CLOCK` 과 그 분기는 `#[cfg(test)]` · 스레드 지역이라 운영 경로는 무관. 수리 자체는 뮤턴트 MT1 로 지켜진다. 경미 — 손대지 않음.

### #11 (사용성 · 경미) — 문구 보고만(고치지 않음)

`ui/src/trashconfirm.ts` `trashPreviewOnlyLines` 는 미리보기 전용 창(삭제 동작 없음 · 바로 위 안내 줄 「파일은 그대로 남아 있습니다」)에서도 거부 항목 앞에 **「이번에 지우지 않는 것(데몬이 거부했습니다):」** 머리말을 그대로 싣는다. 「이번에 지우지 않는 것」은 지우는 동작이 있는 것처럼 읽힌다. 문안은 master 결정 원문(「거부 사유는 기존 문구」)대로라 결함이 아니라 **확인 사항**이다 — 바꿀지 master 판단.

## 4. 검증 (최종 트리 = `b2a4b0f7` 기준 · 맥)

| 항목 | 결과 |
|---|---|
| `cargo test --lib` | **1101 passed · 0 failed** · 2 ignored(662초) |
| `cargo test --bin cys` | **627 passed · 0 failed**(141초) |
| `cargo test --bin cysd` | **2707 passed · 0 failed** · 9 ignored(534초) — `c4_a_reset…` ok |
| ui `bun test` | **3271 tests · 0 fail** · 85 skip |
| ui `bunx tsc -p tsconfig.check.json` | **rc 0**(`bun install --frozen-lockfile` 뒤 — 이 작업트리에 node_modules 가 없었다) |
| `scripts/win-typecheck.sh` | **rc 0** · 오류 0 · 경고 65(trash.rs 는 기존 `:1057` 1건) |
| `scripts/tests/nsis-hook-compile/run.sh` | 전부 OK(N10 제한 모드 4행 · N11 이름-'-' 사례 포함) |
| 팩 py 전건 189종(격리 HOME · `CYS_*` 제거 · `CYS_UPDATE_STATE_DIR` 격리 · `CYS_FEEDBACK_BASE=127.0.0.1:9` · 동시 4) | **186 rc 0** · 적 3 ↓ |

팩 전건 적 3의 판정(기준선 ID·사유 diff 0):
- `test_agora_known_authentic` — `CYS_AGORA_ZIP_DIR 없음 …` 3건. 기준선 `3a366520`(임시 작업트리)에서 **같은 3건 · 같은 사유** 실측 = 브리프의 기준선 적.
- `test_hook_r34` — `RCF-4a 늦은 기록자 + 느린 자식(4s) → 시한(1s)` 1건(동시 4 실행). 직렬 재실행 **ALL PASS**(RCF-4a 2.67초) = 브리프 이월의 동시 실행 시한 플레이크.
- `test_pyseal_census` — `ⓑ 참조 파일 집합 37개 고정 — 실측 45`. 원인 = 같은 전건 안의 `test_orchestra_ticket_snapshot` 이 소스 `cysjavis-pack/bin` 을 팩 자리로 써 설치본(`.pristine/`·`bin/` 등 28항목 + `cysjavis-pack/claude/`)을 깔았고 그것을 셌다(int-winq2 HANDOFF 의 「별건 팩 시험 소스트리 오염」과 같은 것 · 581 test-hygiene 영역). 부산물을 지운 깨끗한 트리에서 직렬 재실행 **PYSEAL-CENSUS-OK**.
- 실행 방법 고지: 1차 실행기가 모든 모듈을 `python3 -m unittest` 로 돌려 스크립트형 79개가 rc 5(시험 0건)로 나왔다 — 그 79개는 `python3 <파일>` 로, `test_preflight_phase1_checks`·`test_verify_gate` 는 요구 env(`JAVIS_ROOT`·`CYS_PROBE_RUNS` 임시)로 다시 돌려 위 숫자를 얻었다. unittest rc 0 이면서 `Ran 0` 인 43개는 import 때 본문이 돌아 `ALL PASS` 를 낸 것을 꼬리로 확인했다.
- 건별 대상 시험: d1 15 OK · name_guard 75 OK · 경쟁 승자 시험 10/10 · UI 53 pass.

## 5. 남긴 것 · 이월

- 이월(브리프 그대로): 팩 기준선 적 `test_agora_known_authentic` · 동시 실행 시한 플레이크(hook_r34 · session_start_hook) · 581 test-hygiene(겹치는 파일 손대지 않음 — `test_orchestra_ticket_snapshot`·`schedule.json.cys-lock` 쪽 변경 0).
- `ui/node_modules` 는 typecheck 를 위해 `bun install --frozen-lockfile` 로 설치했다(gitignore · 커밋 0).
- 강제 경주·흉내·뮤턴트 편집은 전부 원본 복원 뒤 `git diff` 로 비어 있음을 확인했다.
- 팩 전건이 깐 소스트리 부산물(`cysjavis-pack/bin` 아래 28항목 + `cysjavis-pack/claude/` · 전부 untracked · 20:45 생성)은 `git clean -fd cysjavis-pack` 으로 지웠다. 그 뒤 cargo 실행 중 다시 생긴 `cysjavis-pack/bin/schedule.json.cys-lock`(untracked)은 581 영역이라 **손대지 않고 남겼다**.
- 기준선 대조용 임시 작업트리(scratchpad `wt-base` · 3a366520)는 `git worktree remove` 로 정리(목록 0).
