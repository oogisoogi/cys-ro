# HANDOFF — TICKET=cysr-1111-test-hygiene (2026-10-22 · worker@surface:1580)

> 브리프 = `docs/briefs/2026-10-22-cysr-1111-test-hygiene.md`(원장 surface:1580 kind=brief · spawn 경로 · brief_file 일치 확인).
> worktree = `~/cys-terminal-src-wt/1111-hygiene` · 가지 `fix/1111-test-hygiene` ← int/1111 `c5ba14e5`.
> 커밋 = `c712b775`(⑴⑵ 시험) · `ae2ca22c`(⑶ WINQ-2 동형 ⓐⓑ) · 이 HANDOFF. push·태그·설치·윈 기기 = 0.

## 0. 한눈에

| 목표 | 결과 | 근거 |
|---|---|---|
| ⑴ 티켓 스냅샷 시험이 소스 트리를 더럽힘 | 원인 확정 · 수리 · 재현 적→녹 · 뮤턴트 3(2 적 · 1 녹 = 백스톱 층 · 아래) | §1 |
| ⑵ `schedule.json.cys-lock` 재생성 주체 | **설치본 cysd(1.1.9) 고아** — 시험 autostart 로 `CYS_PACK_DIR=소스 bin` 을 쥐고 남음 · 인과 실측 · 원인 수리는 ⑴ 과 같은 줄 | §2 |
| ⑶ⓐ stale 리셋 `composer_edit_region_empty(&obs.screen)` | **같은 결함** → `layout_screen` 으로 수리 · 진단 짝(`input_line_visibility`)도 · 검체 1 · 뮤턴트 2 적 | §3 |
| ⑶ⓑ `cys.rs gate_carry_ok` | **같은 결함**(재료 = 데몬 `read_text` 전체 화면 = `contents()`) → `layout_text` 응답 필드 + `carry_layout` · 검체 2(+배선 핀) · 뮤턴트 4 적 | §3 |
| 검증 | lib 1101 · cys 628 · cysd 2708+1 플레이크 · bun 3184/0 · tsc 0 · win-typecheck 0(경고 65) · 팩 py 189 중 187 + 기준선 적 1 + 플레이크 1 · 트리 깨끗 | §4 |

## 1. ⑴ 시험 오염

- **재현(적)** — 짧은 임시 HOME · `CYS_PACK_DIR` 없음 · `env -i`: `python3 cysjavis-pack/bin/tests/test_orchestra_ticket_snapshot.py` → 시험은 OK 인데 **소스 트리 미추적 990개**(`.install-manifest.json`·`.pack-version`·`.pristine/`·`schedule.json`·`schedule.json.cys-lock`·`agents.json` …) + 새 고아 `/usr/local/bin/cysd`(ppid 1 · env `CYS_PACK_DIR=…/1111-hygiene/cysjavis-pack/bin`).
  - 사슬: `env.setdefault("CYS_PACK_DIR", BIN)` → `javis_orchestra.py --self-test` → `cys_status()`/`cys_agent_detect()` 가 PATH 의 설치본 `cys` 를 부름 → **`cys status` 가 데몬을 autostart** → 그 cysd 가 `CYS_PACK_DIR`(=소스 bin)에 팩을 깔고 고아로 남는다.
  - 긴 HOME(소켓 경로 104바이트 초과)에서는 autostart 가 거부돼 재현되지 않는다 — 이전 판에서 「가끔」 보였던 이유.
- **수리**(`c712b775` · 시험 1파일): `CYS_NO_AUTOSTART=1`(설치본 1.1.9 도 지킴 — 실측: 새 데몬 0 · 팩 파일 0) + 팩 자리 = `tempfile.TemporaryDirectory()`(밖에서 준 `CYS_PACK_DIR` 은 종전처럼 우선).
- **재현 판정 스크립트**(scratchpad `repro.sh`): 시험 rc · 미추적 증가 · 그 실행의 HOME 을 쥔 새 cysd(그 pid 만 종료).

| 판 | 결과 |
|---|---|
| 수리 | rc 0 · 미추적 증가 0 · 락 없음 · 고아 0 → **녹** |
| M0 원본(`git show HEAD:`) | 미추적 1→990 · 락 생김 · 고아 1 → **적** |
| M1 봉인(`CYS_NO_AUTOSTART`)만 제거 | 소스 깨끗(임시 팩 층이 막음) · **고아 1** → **적** |
| M2 팩 자리만 BIN 복귀(봉인 유지) | 깨끗 · 고아 0 → **녹(생존)** — 데몬이 안 뜨면 그 자리에 쓰는 주체가 없다. 팩 자리 층은 봉인이 뚫릴 때의 백스톱(M1 이 그 층의 효과를 보인다) |
| 복원 | `cmp` 바이트 동일 |

## 2. ⑵ `schedule.json.cys-lock` — 주체 = 설치본 cysd 고아

- 코드: `src/bin/cysd/schedule.rs:209` `schedule_path() = pack::pack_dir().join("schedule.json")` · 쓰기 모드 락 `<schedule.json>.cys-lock`(`:891`·`:1031`·`:1608`). 즉 **`CYS_PACK_DIR` 을 쥔 데몬이 스케줄 틱마다** 그 자리에 락을 만든다.
- 인과 실측(내가 띄운 고아 32058 · HOME 일치 확인 뒤 그 pid 만 SIGTERM): 데몬 생존 중 락 삭제 → **~30초 만에 재생성** / 데몬 종료 뒤 삭제 → **90초 동안 0**.
- 「시험 밖에서도 다시 생김」(577 HANDOFF)의 정체: 1111-int 시험 1·2회차가 띄운 고아들이 **지금도 살아 있다**(18:3x 실측) —
  - `CYS_PACK_DIR=/Users/oogisoogi/cys-terminal-src-wt/1111-int/cysjavis-pack/bin` 을 쥔 cysd: **35254**(16:59:49) · **47888**(17:01:37) · **42824**(17:28:50) · **56642** — 1111-int 의 `bin/schedule.json.cys-lock` 이 18:32 에도 갱신돼 있었다.
  - 그 밖에 임시 팩 자리를 쥔 고아 cysd: 16628 · 17759 · 37524 · 45503 · 72303 · 82189 · 85963 · 87626(HOME = `/var/folders/…/T/tmp.*` · cwd = 1111-int / 1111-deptflake / deptflake scratchpad).
  - **내 것이 아니라 종료하지 않았다**(자기 pid 만 · 지침 §1-4). 정리는 master 판단 — 각 pid 의 `ps eww` 로 HOME 이 임시 폴더임을 확인하고 그 pid 만 종료하면 된다.
- 소스 트리에 락이 생기면 안 되는 이유: 락은 「살아 있는 데몬이 이 폴더를 팩으로 쓰고 있다」는 흔적이다 — 그 데몬은 팩 시드(986파일)·스케줄 재적재·잡 실행을 소스 트리에서 하고, `pyseal_census` 같은 소스 계수 시험을 적으로 만들며, 고아라 시험이 끝나도 계속 쓴다.
- **원인 수리 = ⑴ 과 같은 줄**(소스를 팩 자리로 넘기는 경로 제거 + autostart 봉인). 경로 이동·gitignore 는 하지 않았다.
- 【별건 · 미수리】 `test_round_stop_reason` 도 실행마다 고아 cysd 1개를 남긴다(팩 py 전건·단독 2회 재현 · 러너가 그 시험 HOME 을 쥔 pid 만 회수). 팩 자리는 임시라 소스 오염은 없다. 수리안(1줄): 그 시험 subprocess env 에 `CYS_NO_AUTOSTART=1`(또는 시험 끝에 데몬 종료) — 범위 밖이라 손대지 않음.

## 3. ⑶ WINQ-2 동형 — 둘 다 같은 결함

### ⓐ stale 리셋 + 진단 짝
- `maybe_reset_stale_pending_input` 의 `composer_edit_region_empty(&obs.screen, …)` → `readiness::scan_composer` 가 `screen.lines().rposition(선두 마커)` 로 composer 행을 찾는다 = WINQ-2 와 **같은 재료·같은 행 모양 판독**. 윈 식 화면(`────…❯` 한 줄)에서는 선두 마커 행이 없어 `None` → `screen_empty=false` → stale `pending_input_bytes` 가 **영영 리셋되지 않는다**(`input_pending` 무기한 · 보류 방향).
- 진단 `input_line_visibility` 의 `composer_rest_empty(&obs.screen, …)`("= stale 리셋의 술어") 도 같은 재료 → 윈 화면에서 `draft_visible=None`.
- 수리(`ae2ca22c`): 둘 다 `&obs.layout_screen`(577 `screen_rows_text` · 물리 행). 모달 AND 항(`modal_signature_with_marker(&obs.screen)`)은 577 과 같은 이유로 **그대로**.
- 검체 `governance::tests::winq2_wrapped_rule_row_lets_stale_pending_input_reset` — 맥 원화면(대조군) · 윈 식 다시 그리기 둘 다: 진단 `Some(false)` · 계수 7 → 첫 틱 스탬프 → 1.2s 뒤 리셋 0 → 다음 틱 배달.

### ⓑ 부트 관문 증거 이월
- 재료 추적: 부트 폴링 `surface.read_text {surface_id}`(lines 없음) → 데몬 `grid(None)` = **`screen().contents()`**(`handlers.rs`) → `pick_marker_leading_on_screen(text)` → `None` · `pick_marker_last` 는 있음 → `glyph_off_composer=true` → `gate_carry_ok` 거짓 → 관문을 한 번 본 부트가 윈 fullscreen 좌석에서 **`carry-unproven` 영구 보류**(디렉티브 미주입). 관문 보류 재관측(`gate_pending_reobserve_once` → `gate_guard_screen_with_quiet`)도 같은 재료.
- 수리(`ae2ca22c`):
  - 데몬: 전체 화면 응답에 **`layout_text`**(물리 행 · `text` 와 **같은 파서 락**) 추가. `lines` 응답에는 없음. `text` 무변경(모달·관문·사람용 출력 불변).
  - CLI: 순수 함수 `carry_layout(resp, text)` = `layout_text` 있으면 그것, 없으면 `text`(**구 데몬 스큐 = 종전 거동**). 부트 폴링·재관측 둘 다 마커 해소 · `pick_marker_last` · `gate_carry_ok` 화면 인자에 그 재료. `gate_or_modal_present` 는 `text` 그대로.
  - `gate_guard_screen_with_quiet` 반환 = `(text, layout, quiet)` 3튜플 → 확인 직전 재읽기 자리(`let Some((screen, _, _))`)와 그 TOCTOU 배선 핀 문자열 1곳을 같이 바꿨다(핀의 뜻 = 「확인 직전 재읽기 1회」 불변).
- 검체: `handlers::tests::read_text_full_screen_carries_physical_rows_for_wrapped_composer`(ConPTY 식 화면 → `text` 에 선두 ❯ 없음 · `layout_text` 에 있음 · 괘선 행 단독 · `lines` 응답엔 키 없음) · `cys seat_latch_negation_tests::winq2_carry_reads_physical_rows_of_a_wrapped_composer`(이어 붙인 화면 = 이월 거짓 · 물리 행 = 참 · `carry_layout` 선택 · 키 부재 폴백 · 두 호출부 배선 핀).

### 뮤턴트(scratchpad `mutants.py` · 한 곳씩 · 복원 `filecmp` 바이트 동일 3파일)
| 뮤턴트 | 결과 |
|---|---|
| Ma1 stale 리셋 재료 = `obs.screen` | **적** — `winq2-stale-win: … 리셋되지 않았다 left 7 right 0`(맥 대조군은 통과) |
| Ma2 진단 재료 = `obs.screen` | **적** — `winq2-stale-win: 진단이 빈 편집 영역을 못 읽었다 left None` |
| Mb1 데몬 `layout_text` = `contents()` | **적** |
| Mb2 `carry_layout` = `text` | **적** |
| Mb3 부트 폴링 마커 해소 = `text` | **적**(배선 핀) |
| Mb4 재관측 이월 화면 = `screen` | **적**(배선 핀) |

## 4. 검증(맥 · 커밋 전 작업트리 = 커밋 내용)

| 묶음 | 결과 |
|---|---|
| `cargo test --offline -p cys-terminal` | lib **1101** pass 0 fail(2 ignored) · `--bin cys` **628** pass 0 fail(+1 신규) · `--bin cysd` **2708** pass · **1 fail** = `u18_cwd_blocked_observed_under_sandbox_read_deny`(아래) |
| u18 플레이크 판별 | 안쪽 검체 `u18_inner_sandboxed_cwd_probe` 가 샌드박스 셸 출력을 15s 안에 못 받음(`스폰 cwd 가 바뀌었다: ` 빈 화면). 내 판: 전건 중 적 1 · 단독 17회 = 녹 13 · 적 3(모두 앞쪽 6회 안 · 30s) · 출력 미확인 1. 적 뒤 마지막 10회 연속 녹(0.85~4.2s · 마지막 6회는 부하 평균 43 에서). HEAD 원본(변경 걷어냄 · 바이트 복원 확인): 단독 4/4 녹. 안쪽 검체는 `surface.create` + `parser.contents()` 만 쓰고 이 변경(`read_text` 응답·stale 리셋·이월)과 접점 없음 → **시한 플레이크로 해석(판정 아님 · 원인 미규명 · HEAD 표본 4회는 작다)** |
| ui `bun test` | **3184 pass · 85 skip · 0 fail**(98 파일) · `bun run typecheck` rc 0 |
| `sh scripts/win-typecheck.sh` | rc 0 · 오류 0 · 경고 65(기준선 65) |
| 팩 py 전건 189(시험마다 짧은 임시 HOME · 빈 `CYS_PACK_DIR`/`JAVIS_ROOT`/`CYS_PROBE_RUNS` · `CYS_UPDATE_STATE_DIR` 격리 · `CYS_FEEDBACK_BASE=127.0.0.1:9` · `CYS_*` 상속 0) | **187 rc 0** · 적 2 = `test_agora_known_authentic`(「CYS_AGORA_ZIP_DIR 없음 · 제작 맥 전용」 · **기준선 적 · 이월 목록과 같음**) · `test_hook_r34`(NZ-3·DL-1b·WIN-2 시한 · 이월 플레이크 · **단독 재실행 rc 0**). 시험별 소스 미추적 증가 = **0건 전 시험**. 고아 데몬 = `test_round_stop_reason` 1(§2 별건) |
| 작업트리 | 시험 뒤 `git status` = `docs/briefs/`(브리프 · 미커밋 관례)뿐 |

- 기준선 ID+사유 diff: agora(같은 사유) · hook_r34(같은 시한 항목) — 신규 적 0. `session_start_hook` 은 이번 판 rc 0.
- 빌드 캐시: `1111-int/target` 을 APFS 복제(`cp -cR`) · ui `node_modules` 도 같은 방식(둘 다 gitignore · 저장소 무관).
- 재현 중 생긴 소스 부산물(990개 · 3판)은 지우기 전 scratchpad `junk1`·`junk_m0`·`junk_m1`·`junk_m2` 로 옮겨 보존.

## 5. 남은 것·한계(정직)

1. **윈 바이트로 재지 않았다** — ⓐⓑ 재현 화면은 577 과 같은 「맥 화면을 ConPTY 식으로 다시 그림」 계열이다(ConPTY 가 실제로 CUP 생략 이어 쓰기를 하는지는 577 §4-1 의 Med 그대로).
2. ⓑ 는 **데몬·CLI 양쪽**이 새 판이어야 효과가 난다(새 CLI × 옛 데몬 = 키 부재 → 종전 재료 · 회귀 0 · 수리 효과 0).
3. 이 맥의 기존 고아 cysd 12개(§2 목록) — 종료 안 함 · master 판단.
4. `test_round_stop_reason` 고아 데몬 — 별건 · 미수리.
5. 증류: 장기기억 1건(확인요청에 명시).
