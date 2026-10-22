# HANDOFF — TICKET=cysr-1111-int-winq2 (2026-10-22 · worker@surface:1576)

> 브리프 = `docs/briefs/2026-10-22-cysr-1111-int-winq2.md`(원장 surface:1576 kind=brief · spawn 경로) · 회신 = master#1c9e832c(원장 대조 성립 — 16:18:02 · surface:1576 · submitted=queued ∧ verdict_by=session_jsonl_nonce · 내 【경고】 16:17:54 이후).
> worktree = `~/cys-terminal-src-wt/1111-int` · 가지 `int/1111` · 커밋 = **WINQ-2 1개(`c41e12f4`)** · 합치기 커밋 0.

## 0. 끝난 것 한눈에

| 목표 | 결과 | 근거 |
|---|---|---|
| 1. `fix/1111-next` 합치기 | **합칠 것 없음 → 커밋 0**(master#1c9e832c 승인) | 아래 §1 |
| 2. WINQ-2 수리 | 원인 확정(맥 재현) · 수리 · 녹 · 뮤턴트 2 적 · 커밋 `c41e12f4` | 아래 §2 |
| 검증 | cargo lib 1101 · cys 627 · cysd 2707 실패 0 / bun 3184 pass 0 fail · tsc rc 0 / win-typecheck rc 0 / 팩 py 189 중 188 녹 + agora 기준선 적 1 | 아래 §3 |

## 1. 합치기 — 전제 불일치(브리프 방향 오기 · master 인정)

- 실측: `git merge-base int/1111 fix/1111-next` = `186f0e90` 자신 · `git rev-list --count int/1111..fix/1111-next` = **0** · `git merge --no-commit --no-ff fix/1111-next` → 「이미 업데이트 상태입니다」(작업트리 변화 0).
- 경로: `186f0e90`(next HANDOFF) → `ce9ac52a..45c5474c`(fix/1111-improve) → rel/1.1.10(`4badc0cd`·`3ce93329`) → int/1111. 즉 rel/1.1.10 이 이미 next 를 품고 있었다. 브리프의 「next 가 3ce93329 를 안 가짐(20커밋 뒤)」 자체는 맞다(`rev-list 186f0e90..3ce93329` = 20) — 뒤에 있으니 int 쪽에 이미 들어 있는 것이다.
- A3(`84ff3618` · `composer_layout_why` 의 틱 마커·플레이스홀더 면제)는 현 트리에 있다 → WINQ-2 는 **A3 가 들어간 코드에서** 다시 봤다.
- `fix/1111-dept-flake` 등 다른 가지는 손대지 않았다(master 지시 「별 가지 · master 가 나중에 합친다」).
- 인박스 【경고】 16:17:54 로 보고 → master#1c9e832c 「합치기 0 커밋 · WINQ-2 진행 승인」.

## 2. WINQ-2 — 윈 fullscreen 좌석 `--queued` 무기한 보류

### 2-1. 윈 실측(수집 · 원문은 윈 기기)
`~/axdev/master/SESSION_STATE.md:201` — 「WINQ-2 전체화면 좌석 --queued 95s+ 미배달(layout_why=no_marker_row · repaint_requested_at null · 테두리와 ❯ 한 줄)」. 원문 = 윈 `C:\Users\oogis\w1110\e-*.txt`(저장소 밖 · 이 티켓에서 원문 화면 사본은 못 봤다).

### 2-2. 원인(확신도: 코드 경로 = High · ConPTY 가 실제로 그렇게 보낸다는 부분 = Med — 아래 한계)
- `no_marker_row` 는 `composer_layout_why`(`src/readiness.rs` 판정부 경계 아래)가 **선두가 `❯` 인 줄을 하나도 못 찾을 때만** 나온다(`leading_marker_index` = 앞 공백만 벗기고 마커로 시작하는가). 그런데 화면에는 `❯` 가 보였다(「테두리와 ❯ 한 줄」).
- 두 사실을 함께 만족시키는 재료 차이: 진단과 틱 `layout_ok`(`governance.rs` `prompt_gate_input` 의 `composer_layout_static_ok`) 둘 다 **`screen.contents()`** 를 재료로 썼다. vt100 0.15.2 `Grid::write_contents`(`vendor/vt100/src/grid.rs:187`)는 **줄바꿈 표시(wrapped)가 선 행 뒤에 개행을 넣지 않는다** — 다음 행과 한 줄로 이어 붙인다. 줄바꿈 표시는 꽉 찬 행 다음 글자가 자동 줄바꿈으로 찍힐 때 선다(`screen.rs` `text` → `col_wrap(width, wrap=true)` · `grid.rs:684`).
- ConPTY 는 너비를 꽉 채운 행 뒤를 커서 이동 없이 이어 쓸 수 있다 → claude fullscreen 의 위 괘선(120 칸 `─`)이 꽉 찬 행이고, 그 뒤 composer 행 `❯ ` 이 이어 찍히면 `contents()` 에서 `────…────❯` **한 줄**이 된다. 그러면 ⓐ 선두 `❯` 줄 없음 = `no_marker_row` ⓑ 괘선 행도 사라짐 → 틱 `layout_ok` 거짓 → `alt_screen(전체화면 · 프롬프트 레이아웃 미확인)` 보류가 영원히 안 풀린다(출력이 멎어 있으니 화면도 안 바뀐다). 윈 화면 요약 「테두리와 ❯ 한 줄」 과 문자 그대로 맞는다.
- 입력줄 판독(`obs.line`)은 커서 **행 하나**(`contents_between(cr,0,cr,cols)`)라 영향이 없었다 — 그래서 「입력줄은 비었는데 레이아웃만 미확인」 꼴이 된다(1.1.9 W-2 와 같은 꼴).
- `repaint_requested_at null` 은 이 원인과 모순되지 않는다(재그리기 요청 축은 별개 조건 · 이 화면은 그 조건에 안 걸린다 — 판정 아님 · 해석).

### 2-3. 재현(맥 · 가짜 화면 검체 · 실물 계약 파생)
- 검체 `governance::tests::winq2_wrapped_rule_row_keeps_fullscreen_composer_deliverable`(cysd).
- 화면 = **맥 claude 2.1.306 idle fullscreen 실화면**(`testdata/claude_2_1_306_idle_fullscreen.raw` · 맥에서 배달되는 화면)을 파서에 먹인 뒤, **같은 행 글자를 같은 자리에** ConPTY 식으로 다시 그린다(`winq2_conpty_redraw` — 각 행을 `CUP` 로 찍되 앞 행이 마지막 열까지 차 있으면 `CUP` 를 생략하고 이어 씀 · 커서 위치 원화면 그대로). 글자·행·커서는 같고 그리는 방식만 다르다.
- 전제 단언(검체 안): 대체화면 · 행 단위로는 선두 `❯` 행이 있다 · composer 바로 위 행에 줄바꿈 표시 · `contents()` 에는 선두 `❯` 줄이 없다(= 윈 관측과 같은 화면).
- **수리 전 적**: `left: Some("no_marker_row")` ≠ `right: Some("ok")` — 윈 실측값과 같은 코드.

### 2-4. 수리(`c41e12f4` · `src/bin/cysd/governance.rs` 1파일)
- `screen_rows_text(screen)` = `screen.rows(0, cols)` 를 `\n` 으로 이은 **물리 행** 텍스트(줄바꿈 표시 행을 잇지 않음).
- `PromptObs.layout_screen` 새 필드 — `observe_prompt_ext` 두 갈래가 같은 파서 락 안에서 뜬다. `with_block_emptied`(재제출 판독)는 `screen` 과 똑같이 `as_empty_prompt` 로 덮는다(그 값은 원래 `screen.rows` 에서 만든 블록이다).
- 틱 `layout_ok` = `composer_layout_static_ok(&obs.layout_screen, …)` · 진단 `seat_screen_probe_with` 의 `composer_layout_why(&rows_text.join("\n"), …)` — **둘이 같은 재료**(A3 가 맞춘 「진단 = 틱」 계약 유지).
- 바꾸지 않은 것: 모달 판정(`modal_foreground(&obs.screen)`) · 마커 선택(`tick_prompt_marker(…, &contents)`) · `marker_seen` · 초안·stale 리셋 판독 — 재료 `contents()` 그대로(§4 동형 후보).
- 판정 규칙(`readiness.rs`) 무변경 · 화면 문구 변경 0.
- 정상 화면(줄바꿈 표시 행 없음)에서는 `contents()` 와 `rows().join("\n")` 의 줄 목록이 같다(마지막 개행 하나 차이 — `lines()` 로 읽으니 동일) → 맥 거동 불변. 기존 `wq_*`·`qa_*`·`a3_*`·`c5_*`·`rqfix*` 103건 녹으로 확인.

### 2-5. 녹 · 뮤턴트
| 판 | 결과 |
|---|---|
| 수리 뒤 | 검체 녹 · 관련 103건(`winq2_ wq_ a3_ qa_ c5_ rqfix`) 녹 |
| 뮤턴트 M1 = 틱만 옛 재료(`&obs.screen`) · 진단은 수리판 | **적** — 진단 `ok` 통과 뒤 배달 단언에서 `left: 1 right: 0` · 보류 사유 `alt_screen(전체화면 · 프롬프트 레이아웃 미확인)` = **윈 증상 그대로** |
| 뮤턴트 M2 = 진단만 옛 재료(`&contents`) · 틱은 수리판 | **적** — `Some("no_marker_row")` ≠ `Some("ok")` |
| 뮤턴트 뒤 복원 | `cmp` 로 수리판과 바이트 동일 확인 |

## 3. 시험 전건(HEAD = 수리 작업트리 · 맥 · 2026-10-22 16:4x~17:0x)

| 묶음 | 결과 |
|---|---|
| `cargo test --offline -p cys-terminal` | lib **1101** pass · 0 fail(2 ignored) · `--bin cys` **627** pass · 0 fail · `--bin cysd` **2707** pass · 0 fail(9 ignored) · rc 0 |
| ui `bun test` | **3184 pass · 85 skip · 0 fail**(98 파일 · 3269) |
| ui `bun run typecheck`(`tsc -p tsconfig.check.json`) | rc 0 |
| `sh scripts/win-typecheck.sh` | rc 0 · 오류 0 · 경고 65(trash-preview HANDOFF 기준선 65 와 같음 · 내 줄 경고 0) |
| 팩 py 전건(`cysjavis-pack/bin/tests/test_*.py` 189 · 격리 HOME · CYS_* 제거 · `CYS_PACK_DIR`·`JAVIS_ROOT`·`CYS_PROBE_RUNS` = 시험마다 빈 임시 폴더 · CYS_UPDATE_STATE_DIR 격리 · CYS_FEEDBACK_BASE=127.0.0.1:9) | **186 rc 0** · 적 3 = ⑴ `test_agora_known_authentic`(CYS_AGORA_ZIP_DIR 「제작 맥 전용」 부재 · **기준선 적** · 팩 diff 0) ⑵ `test_hook_r34`(「WIN-2 (msys) 시한 초과」) ⑶ `test_session_start_hook` — ⑵⑶ 은 따로 재실행 시 CYS_PACK_DIR 없음/격리 두 판 모두 **rc 0**(부하 시한 플레이크 · 판정 아님 · 해석). 자기 격리 가드 3건(`test_dept_team_token`·`test_preflight_phase1_checks`·`test_verify_gate`)은 이 판에서 요구 env 가 채워져 rc 0. |

- cysd 기준선: trash-preview HANDOFF 2회차 2704 이후 c4race 등 커밋이 있어 **이 가지의 수리 전 수치는 따로 재지 않았다** — 내 신규 시험은 1건(+1)이다.
- 팩 py 1·2회차(CYS_PACK_DIR 를 **지운** 판)는 183 rc 0 + 가드 거부 3 + 적 3 이었다 — 그중 `test_pyseal_census` 적(「참조 파일 집합 37개 고정 — 실측 45」)은 **시험 부산물** 때문이었다(아래 【별건】). 부산물을 치운 3회차에서 녹.
- 이 worktree 는 처음에 `target/` 이 없어 `1111-trash/target` 을 APFS 복제(`cp -cR`)해 빌드 캐시로 썼다(저장소 파일 무관).

## 4. 남은 것·한계(정직)

1. **윈 원문 화면 사본으로 재지 않았다.** 재현 화면은 맥 실화면을 ConPTY 식으로 다시 그린 것이다. ConPTY 가 claude fullscreen 괘선 뒤를 실제로 「CUP 생략 이어 쓰기」로 보내는지는 윈 바이트로 확인하지 않았다(확신도 Med). 근거 = 윈 요약 「테두리와 ❯ 한 줄」 + `no_marker_row` 둘을 동시에 만족하는 경로가 이것이다.
   - **윈 확인 제안(1줄 · master/윈 master 판단)**: 수리 판 키트에서 같은 절차(fullscreen 좌석 · 입력줄 비움 · `cys send --queued`)로 배달되는지 + 배달 전 `queue-blocked.json` `screen_diag.layout_why`. 수리 전 판이 남아 있으면 `cys read-screen` 의 그 줄이 `────…❯` 한 줄인지(= 원인 확증).
2. **동형 후보(이번에 안 고침 · 둘 다 fail-closed 방향)** — 같은 `contents()` 재료로 composer 를 줄 단위로 읽는 곳:
   - ⓐ stale 리셋 판독 `composer_edit_region_empty(&obs.screen, …)`(`governance.rs` `maybe_reset_stale_pending_input` 부근) · 입력줄 가시성 `composer_rest_empty` — 윈에서 선두 마커 줄이 사라지면 「비어 있음」 을 못 세워 리셋·Ctrl-U 처방이 안 붙는 쪽(배달을 열지 않음).
   - ⓑ 부트 관문 증거 이월 `cys.rs gate_carry_ok` → `composer_layout_static_ok(screen, …)` — 화면 재료가 데몬 read_text 다(그 재료가 줄바꿈 표시 행을 잇는지는 이 티켓에서 확인 안 함). 이으면 윈 fullscreen 좌석에서 관문을 한 번 본 뒤 이월이 안 풀릴 수 있다(보류 방향).
   - 고칠지·범위는 master 판단(이번 브리프 범위 밖이라 손대지 않음).
3. 모달 판정(`modal_foreground`)은 일부러 재료를 안 바꿨다 — 긴 선택지 라벨이 줄바꿈으로 이어지는 화면에서 잘린 선택지 판독(`r5_*`·`r7_*`)이 이어 붙인 재료를 전제로 핀돼 있을 수 있어, 바꾸면 이 티켓 밖 판정이 움직인다.
4. **【별건】 팩 py 시험이 소스 트리에 팩을 깐다(기존 결함 · 이번에 안 고침)**:
   - `cysjavis-pack/bin/tests/test_orchestra_ticket_snapshot.py:41` `env.setdefault("CYS_PACK_DIR", BIN)` — CYS_PACK_DIR 가 없는 격리 실행에서 **소스 `cysjavis-pack/bin` 을 팩 자리로** 넘기고, `javis_orchestra.py --self-test` 가 PATH 의 설치본 `cys`(이 맥 = 1.1.9)를 불러 그 자리에 팩 설치본 986파일(`.install-manifest.json`·`.pack-version`=1.1.9·`.pristine/`·`bin/` 등) + `cysjavis-pack/claude/` 를 만든다(2회차 시험별 감시로 이 시험 직후 처음 나타남 확인). 그 뒤 `test_pyseal_census` 가 그 부산물 8파일을 「신규 참조 파일」 로 세어 적.
   - `cysjavis-pack/bin/schedule.json.cys-lock` 도 소스 트리에 생긴다 — 2회차 감시에서 첫 시험 `test_agora_known_authentic` 직후부터 보였고, 시험 밖(`javis_memory.py add` · `git commit` 직후)에도 다시 생겼다 → **만드는 주체 미특정**(시험만의 문제가 아닐 수 있다). 지울 때마다 다시 생기므로 보고 시점에도 있을 수 있다(추적되지 않는 빈 lock 파일 · 커밋 무관).
   - 부산물은 지우기 전에 scratchpad 로 옮겨 보존했다(`junk1`·`junk2`) · 작업트리는 깨끗하다(`git status` = docs 2개만).
   - 수리안(1줄 · master 판단): 그 시험의 `setdefault` 를 임시 폴더로(`tempfile.mkdtemp()`) · lock 은 원인 시험 특정 뒤.
5. 증류: 장기기억 1건(아래 확인요청에 명시).
