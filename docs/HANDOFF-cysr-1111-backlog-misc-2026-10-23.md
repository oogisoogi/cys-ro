# HANDOFF — TICKET=cysr-1111-backlog-misc (2026-10-23 · worker-1111misc@surface:1609)

> 브리프 = `~/axdev/master/briefs/2026-10-23-cysr-1111-backlog-misc.md`(원장 surface:1609 kind=brief · spawn 경로 · body_sha256 `1a93b3d5…` = 파일 끝 개행 제거본과 일치 확인).
> worktree = `~/cys-terminal-src-wt/1111-backlog-misc` · 가지 `fix/1111-backlog-misc` ← `abc137c0`.
> 커밋 = `614534cc`(#1) · `a7e4e0c5`(#2) · 이 HANDOFF. push·태그·설치 = 0 · 실제 open·브라우저 = 0.

## 0. 한눈에

| 항목 | 결과 | 근거 |
|---|---|---|
| #1 워커 §3 c) grill-me ↔ 모달 금지 모순 | 문구 교체(【질문】 master 상신) · 세 사본 동기 · 재현 적→녹 · 뮤턴트 2 적 | §1 |
| #2 test_round_stop_reason 고아 cysd | 재현됨(실행마다 1) · 원인 = round-init 의 `cys status` autostart · 봉인 · 회귀 시험 적→녹 · 실측 0 | §2 |
| 게이트 | lib 1101 · cys 628 · cysd 2709 · bun 3186/0 · tsc 0 · win-typecheck 0(경고 65) · 팩 py 189 중 188 + 기준선 적 1 · doc-contract 3본 초록 | §3 |

## 1. #1 워커 4규칙 c) — 의도 합의 = 【질문】 master 상신

- 모순: 종전 c) 「grill-me 스킬(`cys skill show grill-me`) 등으로 … 합의에 이를 때까지 질문을 반복한다」. grill-me 스킬은 **AskUserQuestion 모달로 최소 20개**를 묻고 **Stop 훅(grill-stop)이 floor 미충족 턴 종료를 막는다**(`cysjavis-pack/skills/grill-me/SKILL.md` 「최소 깊이」). 워커 좌석에는 모달에 답할 사람이 없다 → 좌석이 멈춘다. 실발생 0(브리프).
- 새 c): 「【질문】 머리표로 의뢰자(master)에게 상신해(`cys send --queued --to master "【질문】 ..."`) 합의에 이를 때까지 질문을 반복한다. 질문에는 선택지·근거·권고를 글로 적고, 답을 기다리는 동안 그 결정에 의존하지 않는 일은 계속한다. 선택형 모달(AskUserQuestion)로 멈추지 마라 — 워커 좌석에는 모달에 답할 사람이 없어 좌석이 멈춘다.」 (1줄 교체 · 줄 수 불변)
- c) 의 **세 사본**을 같이 바꿨다 — 한 사본만 바꾸면 위임 티켓이 옛 문구를 계속 배포한다:
  1. `cysjavis-pack/directives/WORKER_DIRECTIVE.md` §3 원문.
  2. `javis_orchestra.py` `RULE_MARKERS`(추출 무결성 마커) `"grill-me"` → `"【질문】"` — 안 바꾸면 새 원문 추출이 None → 폴백 강등. `FALLBACK_RULES` c) 원문 동기. `--self-test` 의 티켓 필수 토큰 `"grill-me"` → `"【질문】"`.
  3. `javis_preflight.py` `CONTENT_PINS["WORKER_DIRECTIVE.md"]` `("grill-me", …)` → `("【질문】", …)` — RULE_MARKERS 패리티(주석이 명시한 짝).
- MASTER §6 c)(오너와 grill-me)·MASTER_CORE·CEO_TEMPLATE 은 **안 건드렸다** — 오너는 사람이라 모달에 답할 수 있다(모순 아님).
- 시험(적→녹): `test_content_pins_parity.py::WorkerIntentAgreementRoute::test_worker_c_routes_question_to_master_not_grill_me` — repo 원문 추출분의 c) 에 【질문】·master 有 · grill-me 無 · FALLBACK c) == 원문 c) · 발부 티켓에 grill-me 無. 등재: 이미 CI 3레인에 이름으로 열거된 파일에 넣었다(신규 파일이면 등재 누락 위험).
  - 적(수정 전): `'【질문】' not found in '- c) **의도 합의**: … grill-me 스킬 …'`.
  - 뮤턴트 M1 원문만 옛것 → 적(`WORKER §3 추출 실패 — RULE_MARKERS 와 원문이 어긋났다`). M2 orchestra 전체 옛것 → 적(같은 사유). M3 FALLBACK c) 만 옛 취지(grill-me)로 → 적(`FALLBACK_RULES c) 가 원문과 어긋났다`). 복원 뒤 녹.
- 기억 함정 3줄(pack-directive-edit-requires-regen-and-doc-contract): ⓐ `python3 scripts/gen_ceo_template.py --check` GREEN(드리프트 0 · WORKER 는 합성 입력이 아니라 CEO_TEMPLATE 무변) ⓑ `test_bootv2_doc_contract.py` exit 0 ⓒ `test_event_inject.py` exit 0(줄 수 불변이라 줄범위 상수 갱신 불요).
- 【부기 · 범위 밖 · 미수리】 원문 a) 와 `FALLBACK_RULES` a) 가 이미 어긋나 있다(원문 a) 에 2026-09-04 「품질의 범위는 제품·서비스다」 문단이 붙었고 FALLBACK 은 첫 문장뿐). 추출이 성공하는 한 티켓은 원문을 싣고, 추출이 실패할 때만 짧은 a) 가 나간다. 이번 티켓 범위가 아니라 손대지 않았다.
- 【부기】 설치본 `~/.cys/pack/directives/WORKER_DIRECTIVE.md`(비공개 인스턴스 · 「사람 게이트 금지」 조항이 있는 판)는 repo 와 다른 판이다 — 그 판의 §3 c) 도 같은 옛 문구다. 팩 갱신 경로가 그 파일을 어떻게 다루는지(덮어쓰기/보존)는 확인하지 않았다 → 새 preflight 의 C03 핀 `【질문】` 이 설치본에 없으면 C03 이 그 핀을 부재로 보고할 수 있다. master 판단.

## 2. #2 test_round_stop_reason 고아 cysd

- 재현(scratchpad `repro.sh` · `env -i` · `HOME=$(mktemp -d)` = `/var/folders/…/T/tmp.*` · `CYS_*` 상속 0 · 시험 뒤 2s · `ps eww` 로 HOME 일치 cysd 계수):
  | 판 | 러너 env | 시험 | 고아 cysd |
  |---|---|---|---|
  | 수정 전 A | 봉인 없음 | rc 0 OK | **1**(pid 14765 · `/usr/local/bin/cysd` · `CYS_PACK_DIR=…/tmpbmt0heca/pack` = RoundStopReason 임시 팩) |
  | 수정 전 B | `CYS_NO_AUTOSTART=1` | rc 0 OK(78 전건 · 데몬 필요한 시험 없음) | 0 |
  | 수정 후 C·D | 봉인 없음 | rc 0 OK ×2 | **0 · 0** |
- 원인: 가짜 `cys`(PATH 앞 · 인자·env 기록 · rc 1)로 추적 → 실행당 `status --json` 2회 · `NO_AUTOSTART=unset`. 호출 경로 = `round-init` → `ack_gate_precheck("round-init")`(`javis_orchestra.py:2364`) → `cys_status()`(`:428`) → 진짜 cys 는 임시 HOME 에 데몬이 없으니 cysd autostart → 시험이 끝나도 고아. (시험 머리 docstring 「데몬 왕복 0(round-log·round-status 는 ACK 게이트 소비자가 아니다)」 는 맞지만 round-init 은 소비자다.)
- 수리(`a7e4e0c5`): 모듈 전역 `os.environ["CYS_NO_AUTOSTART"] = "1"` — 이 파일의 시험 env 는 전부 `dict(os.environ)` 사본이고 제자리 호출 시험(`test_triage_stale_stop…`)도 os.environ 을 쓰므로 한 줄로 전부 덮인다. `setdefault` 가 아니라 대입 = 러너가 `0` 을 줘도 봉인.
  - 브리프 문면은 「정리 보장(종료 훅)」이었으나 **기동 봉인**을 택했다: 띄운 뒤 죽이면 pid 판별(남의 데몬 오살 위험)·경쟁이 남고, 띄우지 않으면 고아가 생길 자리가 없다. 형제 수리 `c712b775`(ticket_snapshot) 와 같은 결. 이견이면 종료 훅으로 바꾸겠다.
- 회귀 시험: `RoundStopReason::test_round_init_status_probe_never_autostarts_a_daemon` — PATH 앞 가짜 cys 가 round-init 의 `status` 호출이 받은 `CYS_NO_AUTOSTART` 를 기록 · 전부 `1` 이어야 녹. 수정 전 적(`['status unset'] != ['status 1']`) → 수정 후 녹. 윈 레인 SKIP(가짜 cys 가 sh).
- 정리: 재현 A 가 낳은 pid 14765 만 종료(HOME = 내 `tmp.OZ8mBYYJA4` 일치 확인 뒤 · 종료 확인). 남의 프로세스 종료 0.

## 3. 검증 숫자(전부 이 worktree · HEAD = a7e4e0c5)

| 게이트 | 결과 |
|---|---|
| `cargo test --offline -p cys-terminal --lib` | **1101 pass** · 0 fail · 2 ignored |
| `--bin cys` | **628 pass** · 0 fail |
| `--bin cysd` | **2709 pass** · 0 fail · 9 ignored |
| ui `bun test` | **3186 pass · 85 skip · 0 fail**(98 파일) · `bun run typecheck` rc 0 |
| `sh scripts/win-typecheck.sh` | rc 0 · 오류 0 · 경고 65(기준선 65) |
| 팩 py 전건 189(시험마다 짧은 임시 HOME · 빈 `CYS_PACK_DIR`/`JAVIS_ROOT`/`CYS_PROBE_RUNS` · `CYS_UPDATE_STATE_DIR` 격리 · `CYS_FEEDBACK_BASE=127.0.0.1:9` · `CYS_*` 상속 0 · **autostart 봉인 없음**) | **188 rc 0** · 적 1 = `test_agora_known_authentic`(「CYS_AGORA_ZIP_DIR 없음 · 제작 맥 전용」 · 기준선 적) · **고아 cysd 남긴 시험 0** · 소스 미추적 증가 0 |
| doc-contract | `gen_ceo_template.py --check` GREEN · `test_bootv2_doc_contract` OK · `test_event_inject` ALL PASS · `test_content_pins_parity` 11 OK · `javis_orchestra --self-test` OK · `test_orchestra_ticket_snapshot`·`test_preflight_c03_states`·`test_orchestra_todo_path` OK |

- 빌드 캐시: `../1111-advfix/target`·`ui/node_modules` 를 APFS 복제(`cp -cR` · 둘 다 gitignore).

## 4. 남은 것·한계

1. §1 부기 2건(FALLBACK a) 표류 · 설치본 비공개 판 C03 핀) — 범위 밖 · master 판단.
2. #2 는 기동 봉인이다(브리프 문면 「종료 훅」과 다름 · 이유 §2).
3. 증류: 장기기억 `pack-py-tests-autostart-orphan-cysd` 본문 갱신(「test_round_stop_reason 미수리」 → 수리 경로·방법).
