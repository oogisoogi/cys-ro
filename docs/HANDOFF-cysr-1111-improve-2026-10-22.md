# HANDOFF — cysr-1111-improve (1.1.11 후보 분류표의 「개선」 행 · 2026-10-22)

- 좌석: worker@surface:1556 · 작업트리 `~/cys-terminal-src-wt/1111-improve` · 가지 `fix/1111-improve`
- 브리프: master spawn 07:25:56(원장 `kind:brief` · surface:1556 · submitted=true · 본문 sha256 `1400c14d…` = 브리프 파일 rstrip 해시 일치 실측)
- 기준: `fix/1111-next` `186f0e90`(← rel/1.1.10 `39189404`) · rebase 없음
- push · 태그 · 판번 · 설치 · 발행 · rel/1.1.10 쓰기 = **0** · 화면 문구 변경 = **0**(CLI 오류 문장 1줄 신설 — §1 B1)

## 0. 분류 — 「개선」 15행을 어떻게 나눴나

출처 = `docs/HANDOFF-cysr-1111-candidates-2026-10-22.md` §3 분류표에서 분류 칸이 「개선」인 15행.

| # | 후보 | 처리 | 까닭 |
|---|---|---|---|
| A3 | layout_why 진단 마커 | 끝남(1111-next `84ff3618`) | 브리프 ⑷ |
| C5 | 확인 미발급 무소식 종료 | 끝남(1111-next `e0b58100`) | 브리프 ⑷ |
| T1 | test_dept_team_token 18 적 | 끝남(1111-next `de40ef6e`) | 1111-next 에서 수리됨 |
| B1 | cys-dept 도장 검사가 teardown 뒤 | **수리 `ce9ac52a`** | |
| B2 | javis_org `isdigit` 유니코드 숫자 | **수리 `56cb0791`** | |
| B3 | 시험 하네스 hdiutil detach | **수리 `444bef00`** | |
| C3 | producer_active 거부 boundary | **수리 `0c55398f`** | |
| A4 | parked_overflow 묘비 surface | **수리 `f59ef4bf`** | |
| R5 | 지침 바이트 래칫 | **수리 `49de6a97`** | |
| MI-cysd | alert_route 드릴 흔들림 | **원인 규명 + 수리 `73b4dd74` → 정정 `83d37785`** | |
| A1 | 좌석 닫힘 큐 폐기 토스트에 좌석 번호 | 보고만 — 브리프 ⑴(화면 문구) | §3 |
| VE-3 | About 「based on cys 0.14.51」 | 보고만 — 브리프 ⑴(새 화면 문구 · 새 기능) | §3 |
| D2 | binary_too_old 상담 신호 중복 | 보고만 — 브리프 ⑵(신호 의미 판단) | §3 |
| Ra-D2b | 판번 안 올린 가지의 수동 release.yml 「Verify signed pack」 적 | 보고만 — 브리프 ⑵(CI 게이트 판단) | §3 |
| TH-2 | trash·factory_reset 윈 경로 핸들 결박 | 보고만 — 브리프 ⑶(윈 실기) + 새 API 의존 | §3 |

## 1. 수리 7건(커밋 8 · 각각 재현 시험 빨강 → 수리 → 녹 → 뮤턴트 빨강 실측 · 항목당 커밋 1)

| # | 커밋 | 무엇이 틀렸나 | 시험(빨강 → 녹 · 뮤턴트) |
|---|---|---|---|
| B1 | `ce9ac52a` | `cys-dept down <부서> --purge-state` 의 격리 도장(`CYS_TRASH_STAMP`) 숫자 검사가 `dept_purge_state` 안 = kill·묘비·`reg_remove` **뒤**에만 있었다. 부적격 도장이면 부서는 닫히고 등재가 지워진 뒤 「격리 실패」로 끝났다. 게다가 state 폴더가 없으면 no-op 갈래로 빠져 **검사 자체를 안 하고 exit 0** 이었다(재현에서 새로 드러남). → `down_dept` 인자 파싱 직후 같은 검사(빈 값 = 기본 도장 · purge-state 와 같은 의미)로 exit 2 · 닫지 않음. | `test_dept_teardown_atomicity.py` D1~D3(가짜 HOME·스텁 cys). 수리 전 = 적 3(exit 0 · 등재 `{}` · 묘비 `tombstone dept-4 --dept` 기록) → 녹. 뮤턴트(거부의 `exit 2` → `:`) = 적 3. |
| B2 | `56cb0791` | `javis_org.destroy_dept` 의 도장 검사 `str.isdigit()` 가 `'²'`·`'٣'` 를 숫자로 받았다(bash `[0-9]` 와 어긋남 — 파이썬이 그 이름으로 먼저 옮기고 하위가 거부). → `isascii() and isdigit()`. | `javis_org.py --self-test` 의 m2 목록에 2줄. 수리 전 = 적(`down`·`verify` 호출됨) → `{"self_test":"ok"}`. 뮤턴트(`isascii` 제거) = 적. |
| B3 | `444bef00` | `scripts/tests/test_update_publish.py` 매체 전제 확인: 재시도 detach 가 같은 일반 분리를 다시 불렀고(바쁜 볼륨이면 같은 실패), 2회 실패로 마운트가 남아도 `finally` 의 `rmtree(d)` 가 마운트된 볼륨 **안으로** 들어갔다. → `hdiutil_retry(force_retry=True)` = 재시도에 `-force`(detach 만) · 분리 실패면 `d` 를 남기고 사유에 경로를 적는다. 시험 하네스 전용(사용자 경로 아님). | `TestHdiutilRetry` 새 1. 수리 전 = 적(`-force` 없음) → 녹. 뮤턴트 2(`force_retry` 끔 / 남김 가드 제거) = 둘 다 적. 1.1.10 시험(분리 2회 실패)은 이제 남긴 폴더를 스스로 치운다. 파일 전건 **113 OK**(skip 14). |
| C3 | `0c55398f` | 휴지통 미리보기 `producer_active` 거부의 `boundary` 가 `<항목>/.producer` 고정이었다. 1.1.10 M3 부터 생산자는 `.producer-<pid>` 를 쓰므로 원장(`DELETE-LEDGER.jsonl`)·응답 `refused[].boundary` 가 없는 파일을 가리켰다. → `producer_state_at` 이 판정과 함께 **판정을 낸 표식 경로**(표식 없음·항목을 못 읽음 = 항목 자신)를 돌려주고 거부가 그것을 싣는다. `producer_state` 는 그 겉면(판정 불변). 화면은 이 칸을 그리지 않는다. | `trash::tests::c3_producer_active_refusal_names_the_marker_that_decided`(cysd · 자기 pid 로 열린 표식). 수리 전 = 적(`.producer` ≠ `.producer-<pid>`) → 녹. 뮤턴트(boundary = 항목 경로) = 적. `trash::` 51 녹. |
| A4 | `f59ef4bf` | 역할 주차 상한 초과로 버려진 항목의 원장 묘비 `surface` 가 **나가는 좌석**이었다(`state.rs` reader EOF 가 `surf.id` 로 일괄 기록). 먼저 주차된 옛 항목이 넘치게 한 좌석에서 온 것처럼 남았다. → `park_queue_for_role` 이 버림분을 출처별로 돌려준다: 기존 배치 몫 = `first_from`(만기 묘비 `parked_expired` 와 같은 출처 표기) · 이번 몫 = `from_surface`. `queue.dropped` 이벤트는 종전처럼 1건(나가는 좌석 · id 순서 같음). | `handlers::tests::a4_parked_overflow_tombstone_names_the_seat_that_parked_the_entry`(cysd). 수리 전 = 적(`"1"` ≠ `"5"`) → 녹. 뮤턴트(옛 몫도 `from_surface`) = 적. `winqueue_parked*`·`park*` 녹. |
| R5 | `49de6a97` | `test_cso_directive_rev.py` 지침 바이트 래칫 상한이 1.1.8 원작자 재기준선(59,715 / 100,723 / 116,357)이라 우리 지침(57,687 / 84,987 / 100,473 B)이 CSO ~2KB · MASTER·CEO ~15KB 늘어도 적이 안 났다. → 오늘 실측으로 내림(주석 ③에 근거). review-a·b 의 지침 변경은 `39189404` 에 모두 들어온 뒤의 크기. | 수리 전: CSO 에 1,000 B 덧붙여도 **녹**(결함 실측). 수리 후 녹 · 뮤턴트(CSO +1 B · MASTER +1 B) = 둘 다 적. 파일 전건 OK. |
| MI-cysd | `73b4dd74` → 정정 `83d37785` | 1.1.10 minor 가 「원인 미판독」으로 남긴 `alert_route::drills::drill_edge_loop_clear_signals_are_never_held_by_the_hourly_cap` 흔들림(`alert_route.rs:4506` 「clear 개시 신호가 시간당 상한으로 보류됐다」). **원인**: 드릴 좌석은 실 PTY 의 `sleep 30` 이다. 단독 11~17초인 이 드릴이 고부하에서 30초를 넘기면 좌석 프로세스가 끝나고, 자력 종료 경로가 큐를 비우고 좌석을 죽여 그 뒤 신호가 배달되지 않는다. **1차 수리**(`73b4dd74`) = 드릴 좌석 전부를 `sleep 600` — ⚠이것이 cysd 전건에서 `handlers::tests::u18_cwd_blocked_observed_under_sandbox_read_deny` 를 **2회 연속 깨뜨렸다**(단독 녹 · 그 수리만 되돌린 전건 = 2704 통과 0 실패로 원인 확정 · 전건 동안 드릴 좌석 PTY 가 쌓임). **정정**(`83d37785`) = `seat`·`bare_seat` 는 `sleep 30` 그대로 · 몇 시간치 `Now` 를 미는 긴 드릴 3개(edge_loop_cap · steady · clear_vs_selfheal)만 `long_seat`(`sleep 600`) + `ReapSeats`(Drop · 패닉 포함)로 드릴 끝에 자식을 거둔다. | **재현**: 좌석을 `sleep 3` 으로 줄이면 같은 줄(4506)·같은 메시지로 실패(t=3612 이후 미배달 · 4초 만에). 정정 뒤 뮤턴트(`long_seat` = `sleep 3`) = edge_loop · clear_vs_selfheal 2 적(steady 는 녹 — 그 드릴은 좌석 사망에 덜 민감). 정정 뒤 cysd 전건 녹(u18 포함) · 실행 뒤 `sleep 600` 잔존 0(`pgrep -fl` 0줄). |

- B1 이 새로 내는 CLI 오류 문장 1줄: `[cys-dept] down: 부적격 도장(CYS_TRASH_STAMP='<값>') — 숫자만 허용 · 닫지 않음`(stderr · 새 거부 갈래라 기존 문장 변경 아님). 이 변수는 시험·검증된 값 전달만 쓴다(review-a 판독).
- A4 는 묘비 1회 append 가 출처별 최대 2회가 됐다(옛 몫 · 이번 몫). 각각은 종전과 같은 「전부 아니면 전무」 배치다.

## 2. 시험 전건(HEAD `83d37785` · 맥 · 2026-10-22 07:5x~08:49)

| 묶음 | 결과 | 비고 |
|---|---|---|
| `cargo test --offline -p cys-terminal --lib` | **1101 통과 · 0 실패**(ignored 2) | `73b4dd74` 에서 실행 · 그 뒤 커밋(`83d37785`)은 cysd 시험 모듈(`#[cfg(all(test, unix))]`)만 바꿈 |
| `--bin cys` | **627 통과 · 0 실패** | 같은 트리(`73b4dd74`) · 위와 같은 이유로 재실행 생략 |
| `--bin cysd` | **2704 통과 · 0 실패**(ignored 9) · HEAD `83d37785` | 1111-next 2702 + 신규 2(C3 · A4). 경과는 아래 ↓ |
| ui `bun test` | 3261 중 **0 fail**(pass 3176 · skip 85) | ui 변경 0 |
| ui `bunx tsc -p tsconfig.check.json` | **rc 0** | |
| `sh scripts/win-typecheck.sh` | **rc 0** · 오류 0 · 경고 65 | `73b4dd74` 에서 실행(1111-next 와 같은 경고 수) · 이후 변경은 unix 전용 시험 모듈 |
| `run_bootstrap_health.py --only H-PRED-8,H-CONC-3` | **GREEN** — 2 PASS / 0 FAIL / 0 SKIP | 판정부 슬라이스 무변경 · 고정 `.tmp` 신규 0 |
| 팩 py 관련(격리 env `env -u CYS_CYS_BIN -u CYS_CYSD_BIN CYS_PACK_DIR=$(mktemp -d)`) | `test_dept_teardown_atomicity` · `test_producer_marker` · `test_win_dept_spawn` · `test_dept_b11_lock` · `test_dept_name_guard` · `test_trash_old_marking` · `test_role_authority` 전부 **rc 0** · `javis_org.py --self-test` ok · `test_cso_directive_rev` OK | |
| `scripts/tests/test_update_publish.py` | **113 OK**(skip 14) | B3 |
| 팩 py 189종 전건 | **미실행** | 팩 변경 = `cys-dept` 7줄 · `javis_org.py` 2줄 · 시험 2파일 — 그것을 부르는 시험만 돌렸다 |

cysd 전건 경과(정직):
1. `73b4dd74`(MI 1차 수리) 전건 2회 = 둘 다 **2703 통과 · 1 실패** `u18_cwd_blocked_observed_under_sandbox_read_deny`(단독 2회 녹). 1111-next 기준선은 같은 시험 0 실패였으므로 내 변경을 의심 → MI 1차 수리만 되돌린 전건 = **2704 · 0 실패** → 원인 = MI 1차 수리. 정정 커밋 `83d37785`.
2. 정정 직후 전건 = 2703 · 1 실패 `trash::tests::only_the_background_walk_yields_to_the_dispatch_path`(trash.rs:3670 ⒝ 「마감 없는 순회가 양보했다」 · 실행 끝 부하 11.7). 이 단언은 전역 계수기 `YIELD_COUNT`(trash.rs:321)를 `== 0` 으로 재는데, 같은 프로세스의 다른 시험이 마감 있는 순회를 동시에 돌리면 계수가 오른다 — 내 C3 시험은 마감 없이(`None`) 불러 양보를 만들지 않는다. `trash::` 단독 3회 = 51 녹 ×3 · 그 뒤 HEAD 전건 = **2704 · 0 실패**. 기존 경합 흔들림으로 판독(이번에 고치지 않음 · §4).

## 3. 보고만 — 판단 대상 5건(손대지 않음)

| # | 무엇 | 왜 손대지 않았나 | 판단에 필요한 사실(실측) |
|---|---|---|---|
| A1 | 좌석 닫힘 큐 폐기 토스트 「대기 중이던 지시 N건을 버렸습니다」에 좌석 번호 싣기 | 화면 문구 변경(브리프 ⑴) | 화면 = `ui/src/main.ts:10075` `queueDropNotice(payload)`(문구·조건 = `queuedropnotice.ts`). 이벤트는 `Some(surf.id)` 로 나가므로 화면이 이미 계산하는 `seatNo(sid, …)`(같은 파일 9928행 관례)로 번호를 낼 수 있다 — 문구를 정하면 1줄 + 핀 갱신. |
| VE-3 | About 「based on cys 0.14.51」 표기 | 새 화면 문구 · 새 기능(브리프 ⑴) | `git grep -i 'based on cys'` 0건(vendor HANDOFF §6-3). |
| D2 | 발행 창 동안 1.1.8/1.1.9 기기의 `update.binary_too_old` 상담 신호 누적(중복 제거 없음) | 신호의 의미를 바꾸는 판단(브리프 ⑵) — 쓰는 쪽에서 접으면 「몇 번 겪었나」(빈도)가 사라진다 | 쓰는 곳 = 팩 `javis_counsel.py write_signals`(줄마다 append · 2MB 상한 · 줄 = ts·source·op·error_code·version·os). review-a 판독: 송신기가 같은 줄을 count 로 접는다 · 하루 ~4줄 · 로컬 화면 소비자 0. 고친다면 팩에서(옛 바이너리에도 닿음) · 선택지 = ⓐ그대로(소음 허용) ⓑ같은 (op, error_code, version) 은 N시간에 1줄. |
| Ra-D2b | 판번을 안 올린 가지에서 release.yml 을 손으로 돌리면 「Verify signed pack end-to-end」 적 | CI 게이트를 약하게 할지의 판단(브리프 ⑵) · 확인하려면 워크플로 실행(외부 동작)이 필요 | 단계 = `./target/release/cys pack-update --from . --dry-run`(`release.yml:2012`). 팩 `min_binary` > 빌드한 바이너리 판번이면 `VersionGate::BinaryTooOld` → `binary-too-old`(`cys.rs:28520` 부근). 지금 이 가지는 Cargo `1.1.10` = 팩 하한이라 해당 없음 — 하한을 판번보다 먼저 올린 가지에서만 난다. 태그 실행은 판번을 먼저 올려 녹. 선택지 = ⓐ절차 메모(수동 실행 전 판번) ⓑdispatch 일 때만 그 경우를 구분해 알리고 통과(게이트 약화). |
| TH-2 | `trash.rs`·`factory_reset.rs` 윈도우 경로의 핸들 결박 | 윈 실기 선결(브리프 ⑶) · 안정 std 에 `openat`·file index 가 없어 새 의존(windows-sys 계열)이 필요 | 윈 휴지통 삭제는 기본 꺼짐(`delete_supported`). trash-harden HANDOFF §5. |

같은 분류표에서 「개선」 행이 아닌 것(정책 12 · 실기 6 · 결함 5)은 브리프대로 손대지 않았다. R8 행의 부속 메모(`formation-*` 생산자 `.producer` 표식 · `trash.rs:275` 주석의 생산자 목록에 `javis_dept_request.py` 기재)는 「결함」 행 소속이라 범위 밖으로 두었다 — 주석의 「생산자 셋」은 실제로는 넷이다.

## 4. 남은 것·한계(정직)

- B2 의 시험 자리 `javis_org.py --self-test` 는 CI 단계에 걸려 있지 않다(`.github/workflows`·`scripts` 에서 호출 0 — grep 실측). 같은 m2 목록의 기존 줄들도 같은 처지다. 자동 잠금이 필요하면 CI 에 그 자기검사 1줄을 거는 판단이 남는다.
- B3 은 가짜 runner 로만 쟀다 — 실제로 바쁜 볼륨을 만들어 `-force` 가 통하는지는 재지 않았다(맥 러너 간헐 실패가 드물다).
- MI-cysd: 흔들림을 고부하로 직접 재현하지는 않았고, 좌석 수명을 줄여 **같은 줄·같은 메시지**를 결정론으로 낸 기제 재현이다. 같은 `sleep 30` 좌석은 governance 등 다른 드릴(cysd 안 217곳)에도 있다 — 이번엔 몇 시간치 `Now` 를 미는 alert_route 긴 드릴 3개만 바꿨다. ⚠교훈: 좌석 수명을 일괄로 늘리면 전건 동안 PTY 가 쌓여 남의 시험이 깨진다(이번 1차 수리의 실수) — 늘린 좌석은 그 드릴 끝에 거둬야 한다.
- `trash::tests::only_the_background_walk_yields_to_the_dispatch_path` 의 전역 `YIELD_COUNT` 경합(§2 경과 2) — 고치려면 그 시험이 `PREVIEW_TEST_SERIAL` 밖의 마감 있는 순회와 겹치지 않게 하거나 계수를 스레드별로 재야 한다. 이번 범위 밖(개선 행 아님) · 다음 판 후보로 적는다.
- A4: 기존 배치가 여러 좌석의 항목이 섞인 것이면(여러 번 병합) 옛 몫은 모두 `first_from`(처음 주차한 좌석)으로 적힌다 — 항목별 출처 칸이 `ParkedQueue` 에 없어서다(만기 묘비와 같은 한계 · 버림이 오래된 것부터라 가장 오래된 항목에는 정확).
- 윈 실기 0 · 리뷰어 교차 검토 0(브리프에 요구 없음).
- 증류 1건: `cysd-drill-seat-lifetime-pty-pileup`(드릴 좌석 수명을 일괄로 늘리면 전건 PTY 누적이 남의 시험을 깬다).
