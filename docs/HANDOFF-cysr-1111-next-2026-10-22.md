# HANDOFF — cysr-1111-next (1.1.11 후보 분류표에서 master 가 고른 권고 3건 · 2026-10-22)

- 좌석: worker@surface:1555 · 작업트리 `~/cys-terminal-src-wt/1111-next` · 가지 `fix/1111-next`
- 브리프: master spawn 05:30:23(원장 `kind:brief` · surface:1555 · submitted=true · 대조 성립)
- 기준: `fix/1111-candidates` `6782e9a3`(← rel/1.1.10 `7f15c059`) → **rebase `39189404`**(master#713687b2 · 원장 대조 성립 06:31:21 · rel/1.1.10 머리) · 충돌 1곳(아래 §3)
- rebase 전 끝 = 로컬 가지 `backup/1111-next-pre-rebase`(`3b7c3220`)
- push · 태그 · 판번 · 설치 · 발행 · rel/1.1.10 쓰기 = **0** · 화면 문구 변경 = **0**

## 1. 수리 3건(각각 재현 시험 빨강 → 수리 → 녹 → 뮤턴트 빨강 실측 · 항목당 커밋 1)

| # | 커밋(rebase 뒤) | 무엇이 틀렸나 | 시험(빨강 → 녹 · 뮤턴트) |
|---|---|---|---|
| T1 | `de40ef6e` | `test_dept_team_token.py` 의 `make_env` 가 `CYS_CYS_BIN`·`CYS_CYSD_BIN` 을 지우지 않았다. `cys-dept` 는 이 두 변수를 PATH 보다 먼저 쓰므로, cys 좌석 안에서 돌리면 앱이 내보낸 실 설치본(`/Applications/cys.app/Contents/MacOS/cys` · team-token 휴면)이 시험의 가짜 cys 대신 답했다. 형제 시험(`test_team_create_u16.py:109` · `test_dept_notice_lane.py:45`)과 같은 꼴로 pop 목록에 2개 추가. | 수리 전 좌석 env 에서 23 중 **18 적** → 수리 후 **23/23 녹**. 뮤턴트 = 수리 전 원본(같은 18 적). 팩 전건 안에서도 녹(§2). |
| A3 | `84ff3618` | ⒜ 진단(`seat_screen_probe_with` 의 `layout_why`)은 `pick_marker_for_screen`(화면 전체에서 가장 뒤 후보)으로 마커를 골랐고, 틱(`observe_prompt_ext`)은 **커서행 선두 후보가 우선**이다. 다중 마커 어댑터(codex `›`·`»`)에서 빈 composer 아래 상태줄에 비선두 `»` 가 있으면 진단만 `»` 를 골라 `no_marker_row` 를 냈다(틱은 `›` 로 레이아웃을 통과시켜 배달). → 틱의 규칙을 순수 함수 `tick_prompt_marker`(governance.rs)로 빼서 둘이 같이 쓴다. ⒝ `composer_layout_why` 의 `scan_composer` 실패 갈래가 **플레이스홀더 면제 없이** 마커 줄 문면을 봐서, 플레이스홀더 + 아래 선택지 행 화면을 `marker_row_text` 로 오표기했다(정답 `marker_below`). → 면제를 `rest_is_placeholder`(readiness.rs)로 빼서 `scan_composer` 와 같이 쓴다. | ⒜ `governance::tests::a3_layout_why_uses_the_tick_marker`(cysd) — 수리 전 적(`Some("no_marker_row")` ≠ `Some("ok")`) → 녹 · 같은 화면에서 틱은 배달함까지 단언. 뮤턴트(진단만 옛 `pick_marker_for_screen`) = 적. ⒝ `readiness::tests::a3_composer_layout_why_exempts_the_placeholder_like_the_verdict`(lib · 5 화면 · 진단 코드 ⇔ 판정 일치 대조 포함) — 수리 전 적(`marker_row_text` ≠ `marker_below`) → 녹. 뮤턴트(진단 쪽 면제만 되돌림) = 적. |
| C5 | `e0b58100` | 휴지통 삭제 모달 `ready()` 가 `confirm_nonce`(네이티브 단회 확인) 부재를 보지 않고 타이핑을 열었다. 네이티브가 확인을 발급하지 못하면(확인 잠금 오염 등 · 도달 곤란) 「삭제」를 눌러도 `trashDeleteFlow` 의 nonce 가드가 상태줄·알림 없이 끝났다(무소식 종료). → `ready()` 에 `if (!prev.confirm_nonce) { refuse("confirm_unbound", ""); return; }`. 사유 코드는 네이티브가 내는 것과 같고, 문구는 순수 모듈 표(`trashconfirm.ts` 의 `confirm_unbound` 줄)에 **이미 있던 것**이다(문구 변경 0). | `ui/src/trashwiring.test.ts` 새 핀 — 가드 → 거부 → 반환이 타이핑 여는 곳(`inp.disabled = false;`)보다 앞. 수리 전 적 → 녹. 뮤턴트(가드의 `return` 제거) = 적. ⚠이 핀은 main.ts 를 **데이터로 읽는** 기존 관례의 배선 핀이다(DOM 런타임 시험 아님). |

- A3 는 **진단 전용**이다 — 게이트·배달·리셋은 `layout_why` 를 읽지 않는다. 틱의 마커 선택 결과와 `scan_composer` 판정은 거동이 바뀌지 않는다(같은 식을 함수로 옮겼을 뿐 · 기존 `wq_*`·`composer_layout*` 시험 녹).

## 2. 시험 전건(rebase 뒤 HEAD `e0b58100` · 맥 · 2026-10-22 06:3x~07:2x)

| 묶음 | 결과 | 비고 |
|---|---|---|
| `cargo test --offline -p cys-terminal` | lib **1101** · `--bin cys` **627** · `--bin cysd` **2702** 통과 · **실패 0**(ignored 2 · 9) · rc 0 | 기준(이전 HANDOFF 1100 · 627 · 2701) 대비 lib +1 · cysd +1 = A3 신규 시험 2 |
| ui `bun test` | 3261 중 **0 fail** · 85 skip(pass 3176) | 신규 1 = C5 핀 |
| ui `bunx tsc -p tsconfig.check.json` | **rc 0** | ⚠이 작업트리는 처음에 `ui/node_modules` 가 없어 TS2307(모듈 못 찾음) 3 + TS7006 5 로 rc 1 이었다 → `bun install --frozen-lockfile` 뒤 rc 0 · git 상태 변화 0(`ui/node_modules/` 는 .gitignore) |
| `sh scripts/win-typecheck.sh` | **rc 0** · 오류 0 · 경고 65 | 이전 HANDOFF 와 같은 경고 수 · 내가 만진 줄의 경고 0 |
| `run_bootstrap_health.py --only H-PRED-8,H-CONC-3` | **GREEN** — 2 PASS / 0 FAIL / 0 SKIP | master#713687b2 지시 · 판정부 슬라이스 안에 `.count()`·`.matches(m` 신규 0 |
| 팩 py 전건(`cysjavis-pack/bin/tests/test_*.py` **189종** · 직렬 1회 · 좌석 env) | 적 4 → 판정 아래 · **최종 남은 적 = 1(기준선)** | ↓ |

팩 적 4의 판정:
- `test_agora_known_authentic` — `CYS_AGORA_ZIP_DIR 없음`(제작 맥 전용 시험) = **기준선 그대로**.
- `test_hook_r34` — RCF-4a · DL-1b 시한 2 FAIL → **2회째 rc 0 녹**(load 2.4~2.6) = 기준선의 시한 플레이크.
- `test_preflight_phase1_checks` · `test_verify_gate` — rc 2 · 0초 · `REFUSE(hard assert): 격리 env 미설정 [JAVIS_ROOT, CYS_PROBE_RUNS]`(시험 자신의 라이브 오염 차단 장치). `JAVIS_ROOT=<임시> CYS_PROBE_RUNS=<임시>/probe_runs.jsonl` 로 다시 돌려 **둘 다 OK**. 제품 회귀 아님.
- `test_dept_team_token` — 전건 안에서 **rc 0**(T1 로 적 18 소멸 확인) · `test_dept_name_guard` 이번엔 1회째 녹.
- 참고: rebase 전에 돌리다 멈춘 부분 실행(151/189)에서는 phoenix 3종(`c6_reap`·`e2e_replacement`·`w2_untomb_fullcycle`)이 적이었다 — `target/debug/cysd` 가 낡은 짝이었던 탓으로 판독([[phoenix-harness-binary-pair-mismatch]]). rebase 뒤 `cargo build --bin cys --bin cysd` 를 먼저 하고 돌린 전건에서는 **셋 다 녹**.

## 3. rebase(master#713687b2)

- `39189404` 위로 rebase — 커밋 9개 재적용(555 의 6개 + 내 3개). 충돌 = `src/readiness.rs` 1곳: master 가 `composer_layout_why` 를 「판정부 끝(핀 슬라이스 경계)」 아래로 옮겼고, 내 A3⒝ 는 옛 자리의 그 함수를 만졌다. 해소 = 옛 자리는 HEAD(함수 없음)를 받고, 옮겨진 함수(경계 아래 · 현재 `readiness.rs:2061`)에 내 1줄 수정(`rest_is_placeholder` 면제)을 다시 얹었다.
- 내 보조 함수 `rest_is_placeholder` 는 판정부 슬라이스 **안**(`scan_composer` 바로 위)에 있다 — `scan_composer` 가 판정부 함수라 그 곁에 뒀다. 본문에 `.count()`·`.matches(m` 이 없고, H-PRED-8 GREEN 으로 확인했다.

## 4. 남은 것·한계(정직)

- A3 재현은 손으로 그린 화면(codex 마커 · 괘선 상자 · 상태줄에 비선두 `»`)이다. **codex 실화면 사본으로는 재지 않았다**. 윈 축2 사본 수리 티켓(WQ-2)에서 이 진단을 읽을 때, 이제 틱과 같은 마커·면제로 재므로 그 코드가 가리키는 규칙이 틱의 실제 거짓 규칙이다.
- C5 는 정적 배선 핀으로만 잠갔다(이 저장소 ui 시험 관례 · DOM 런타임 없음). 실제로 확인 잠금을 오염시켜 모달을 띄워 본 실기는 0.
- C5 화면은 「이 명령에 맞는 확인 단계가 없습니다 — 지우지 않았습니다. 새로 미리보기를 하세요.」 + 「다시 미리보기를 하세요 — 아무 것도 지우지 않았습니다.」 두 줄이 겹쳐 말한다 — `refuse()` 의 기존 꼴(네이티브 `confirm_unbound` 가 올 때도 같음)이라 그대로 뒀다. 다듬을지는 문구 판단(master).
- 윈 실기 0 · 리뷰어 교차 검토 0(브리프에 요구 없음 — 필요하면 지시 바람).
- 증류 1건: `pack-full-run-isolation-env-false-reds`(팩 전건 격리 env 거짓 적 · 새 작업트리 tsc 의존 설치).
