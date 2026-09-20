# 대화로 부서 만들기 — CLI 계약 (A1-2 · `javis_dept_request.py`)

- 설계 정본: `~/axdev/master/reports/jarvis-dept-redesign-2026-09-17/DESIGN-v2.1.md`(§3~§12)
- 적대 검증: 같은 폴더 `VERIFY-adversarial-r2.md`(치명 3 · 수정 필수 11)
- 이 문서는 **A1-2d(스킬·지침)가 글자 그대로 인용하는 계약**이다. 동사·인자·종료 코드·JSON 키·상태값이 바뀌면 이 문서와 스킬을 함께 고친다.
- 도구: `cysjavis-pack/bin/javis_dept_request.py` · 시험: `bin/tests/test_dept_request.py` · 뮤턴트: `bin/tests/mut_dept_request.py`
- 스케줄 잡: `src/bin/cysd/schedule.rs` 의 `dept-request-tick`(1분 · `base_only` · 마커 `deptreq`)

## 1. 한눈에

```
사용자 「설교준비부 만들어 줘」
  → 마스터: propose  (카드 출력 · 요청 번호 dr-…)
  → 사용자 「네」
  → 마스터: confirm dr-…   (request.json=confirmed 를 먼저 쓰고, 그다음 .pending 표지)
  → 스케줄 틱(1분): tick    (CSO 신원으로 cys-dept create · 결과 알림 [부서결과] dr-…)
  → 마스터: status --say dr-…  (판정 문장 그대로 사용자에게)
  → 가동이 되면 틱이 [부서가동] dr-… · 첫 일이 있으면 마스터가 kickoff dr-…
```

마스터는 부서 lifecycle 명령(`cys-dept create/down` · `javis_org destroy`)을 **직접 부르지 않는다**. 집행은 제품 코드에 박힌 스케줄 틱이 한다(대안 E).

## 2. 동사

| 동사 | 부르는 쪽 | 인자 | 하는 일 |
|---|---|---|---|
| `propose` | 마스터(본부) | `--name <표시명>` `--mission <맡을 일 한 줄>` `--claude-md-file <본문 파일>` [`--utterance-file <발화 원문>`] [`--first-task <처음 맡길 일>`] | 새 부서 카드. 열린 제안은 언제나 1장 — 새 제안이 나오면 옛 제안은 `superseded` |
| `propose --close <이름>` | 마스터(본부) | 표시명 · 카탈로그 표시명 · 시스템 이름(`dept-N`) 중 하나 | 닫기 카드(후보 1개) · 후보 여럿이면 거부(exit 5 · `candidates`) · 없으면 거부(exit 4) |
| `confirm <번호>` | 마스터(본부) | 요청 번호 | 사용자 「네」 뒤. `request.json` 을 `confirmed` 로 영속한 **뒤에** `.pending` 표지를 만든다 |
| `tick` | **스케줄 틱만** | — | 집행기(§4). `CYS_ROLE=cso` 가 아니면 exit 3 |
| `status` | 마스터 | `--pending` · `--all` · `--say <번호>` | 판정표(§5). `--say` 는 그 판정을 「말했다」로 기록(`said.json` · `request.json` 은 쓰지 않는다 — codex 1R F8) |
| `kickoff <번호>` | 마스터(본부) | 요청 번호 | 첫 일 한 문장을 부서장에게 요청당 1회(가동 판정일 때만) |
| `discard <번호>` | 마스터 | 요청 번호 | 레지스트리에 대응 부서가 **없을 때만** 이 요청이 넣은 카탈로그 항목·미션 파일·표식 있는 `CLAUDE.md` 를 걷는다. 틱과 **같은 잠금** 안에서만 하고(틱이 돌면 exit 7 `busy`), `confirmed` 이거나 첫 자식이 살아 있으면 거부(exit 7 `in_flight` · codex 1R F11) |
| `self-test` | 누구나 | — | 결정 트리 전 조합 · 키 계약 · javis_org 의미 대조 · 내장 뮤턴트 |

※브리프의 동사 나열(`propose/confirm/apply/status/discard`)의 `apply` 는 이 도구에서 `tick` 의 생성 단계(§4 ⓓ)다 — 사람·마스터가 부를 수 있는 `apply` 동사는 두지 않았다(설계 §3-4: 집행은 틱만).

### 2-1. 종료 코드

| 코드 | 뜻 |
|---|---|
| 0 | 성공(틱의 정상 skip 포함) |
| 1 | 내부 오류 · 자기시험 실패 · kickoff 발신 실패 |
| 2 | 사용 오류 · 입출력 실패(필수 인자 없음 · 본문 파일 못 읽음 · 레지스트리를 못 읽음 `registry_unreadable` — codex 1R F12) |
| 3 | `tick` 을 CSO 신원 밖에서 부름 |
| 4 | 대상 없음(번호 없음 · 닫을 부서 못 찾음) |
| 5 | 거부 — 중복 이름 · 상한 · 부서 레인 · 자원 hard · 닫기 후보 여럿 |
| 6 | 낡은 번호(`superseded` 제안의 `confirm`) |
| 7 | 상태 불일치(이미 처리됨 · 가동 전 kickoff · 이미 만든 부서의 discard · 안내문 변조 · 틱 처리 중 discard · 만드는 중 discard) |

거부(5·6·7·4)도 stdout 에 `{"ok": false, "say": "<사용자에게 할 말>", "reason": "<기계 사유>"}` 를 낸다. 마스터는 `say` 를 **그대로** 말한다.

### 2-2. 출력 JSON

- `propose` 성공: `{"ok": true, "request": "dr-YYMMDD-HHMMSS-xxxx", "card": "<카드 전문>"}`
- `confirm` 성공: `{"ok": true, "request": …, "say": "확인했습니다. 1분 안에 시작합니다 — 다 되면 알려 드리겠습니다."}`
- `status`: `{"ok": true, "rows": [판정, …]}` · `status --say`: 판정 1개
- 판정: `{"request", "dept", "row": 1~13, "verdict", "axes": {R,G,T,D,F,P,E}, "say"[, "tombstone_residue": true]}`
- `reason` 값: `lane` · `name` · `duplicate` · `cap` · `resource` · `mission` · `io` · `not_found` · `ambiguous` · `superseded` · `state` · `claude_md_changed` · `exists` · `no_first_task` · `already` · `not_running` · `send_failed` · `send_uncertain`(kickoff 전송 timeout — 재발송 금지 · 2R F11) · `busy` · `in_flight` · `registry_unreadable`

### 2-3. 요청 상태

`proposed` → (`superseded` | `discarded` | `confirmed`) → (`expired` | `created` | `reused` | `create-timeout` | `failed` | `closed`)

`fail_reason` 값: `cap:<n>` · `resource` · `claude_md_conflict` · `claude_md_changed` · `cysd_not_found` · `create_rc:<n>` · `create_hang` · `create_timeout_exhausted` · `close_rc:<n>` · `target_changed:<key|cwd|socket>`(닫기 대상 번호가 다른 부서가 됨 — codex 1R F10) · `crash:<예외 이름>`(요청 하나의 집행이 예외로 죽음 — agy 1R F1)

## 3. 파일

| 경로 | 내용 |
|---|---|
| `~/.cys/dept-requests/<번호>/request.json` | 요청 기록(판정 근거 아님 — 판정은 실물) |
| `…/<번호>/card.txt` | 사용자에게 보인 카드 |
| `…/<번호>/claude_md.txt` | 부서 폴더에 쓸 `CLAUDE.md` 전문(sha256 을 request.json 에 잠금) |
| `…/<번호>/utterance.txt` | 발화 원문(개인정보 — 수명 §4 ⓑ) |
| `~/.cys/dept-requests/.pending` | 생성 단계 표지(`confirm` 이 만들고 틱이 스캔 **전에** rename 으로 치움) |
| `~/.cys/dept-requests/.tick.lock` | 틱·discard 공용 잠금(OS 파일 잠금 `javis_lock.FileLock` — 보유 프로세스가 죽으면 커널이 푼다 · 회수 단계 없음 · codex 1R F9). 옛 판의 `.lock/` 디렉터리 방식은 폐기 |
| `…/<번호>/.rlock` · `said.json` · `kickoff.json` | 제안 교체·확인 전이 잠금(F8) · `status --say` 기록 · kickoff 1회 원자 표지(O_EXCL) |
| `~/.cys/dept-requests/.last-sweep` · `.tick-state.json` · `status-unknown.log` · `.create-<키>.log` · `.create-<키>-<n>.out` · `tick-errors.log` | 청소 시각 · 직전 생성 시각 · 판정 불능 원값 · create 진단(stderr) · n번째 create 호출의 stdout(파일 — 틱이 먼저 끝나도 자식이 파이프로 죽지 않는다 · F16) · 요청 단위 크래시·레지스트리 판독 실패 기록 |
| `<작업폴더>/CLAUDE.md` | 첫 줄 표식 `<!-- cys-dept-mission request=… sha256=… -->` + 역할 안내 고정 줄 + 본문 |

팩토리 리셋 목록에 `dept-requests` 를 넣었다(`src/factory_reset.rs`).

## 4. 틱 (`dept-request-tick` · 1분)

잡 명령: `pk="${CYS_PACK_DIR:-$HOME/.cys/pack}"; [ -f "$pk/bin/javis_dept_request.py" ] || exit 0; env CYS_ROLE=cso python3 "$pk/bin/javis_dept_request.py" tick`

⚠설계 v2.1 §3-2 의 `[ -e .pending ] || exit 0` 셸 게이트는 **넣지 않았다** — 적대 2R ② 와 브리프 「만료·고아 청소·개인정보 7일 삭제를 `.pending` 게이트 밖(매 틱 무조건)」에 따른 것이다. 비용 = 매분 파이썬 1회 기동(할 일이 없으면 폴더 목록 1회 · 편성 원장 목록 1회). 표지는 **생성 단계**의 관문으로 남는다.

한 틱의 순서(전부 멱등):

1. ⓐ 전역 잠금(OS 파일 잠금 · 못 잡으면 exit 0)
2. ⓑ **청소 — 매 틱 무조건**: 만료(확인 뒤 30분 넘게 집행이 시작되지 않은 요청) · 개인정보 수명(발화 원문 = **모든 상태**에서 제안 시각 `created_at` 7일 뒤 삭제 — codex 1R F1) · 요청 폴더 수명(`superseded`·`expired`·`discarded` = 마지막 움직임 30일) · 고아 편성 원장 청소(§4-1 · 레지스트리를 못 읽으면 보류) · 자가복구(진행 중 요청이 있는데 표지가 없으면 다시 세움)
3. 표지 선점: `.pending` → `.pending.claimed-<pid>` rename(스캔 **전**). 이어서 레지스트리를 읽을 수 없으면(파일은 있는데 해석 불가) 이번 틱의 생성·닫기·가동 판정 전부 보류(`tick-errors.log` · codex 1R F12)
4. ⓓ 생성 1건: 가장 오래된 `create-timeout`, 없으면 가장 오래 기다린 `confirmed` 1건만. 상한(레지스트리 항목 전부 < 2 · 메뉴 부서 · 묘비 잔존 부서 포함 — codex 1R F4) · 간격 10분 · 자원 hard 재점검 → 계정 시드 → `catalog_upsert` → `write_mission` → `ensure_dirs` → `CLAUDE.md` → `cysd` 탐색 → 호출 의도(호출 수·시각·간격 기준) 영속 → `cys-dept create <키>`(절대경로 · `start_new_session` · stdout 은 파일 · 기다림 300초) → `backfill_mission_key` → **첫 호출 전부터 있던** 묘비만 해소 1회 재시도(생성 뒤 새로 생긴 묘비 = GUI 닫기의 의도 기록일 수 있어 건드리지 않음 · codex 1R F17). 요청 하나의 집행이 예외로 죽으면 그 요청만 `failed(crash:…)`(agy 1R F1)
5. ⓔ 닫기 1건: 카드에 기록한 맡은 일 키·폴더·소켓이 지금 그 번호의 부서와 같을 때만(다르면 `failed(target_changed:…)` · codex 1R F10) `javis_org.py destroy --dept <dept-N> --purge --purge-state`(CSO 신원 · `--purge-workdir` 없음) → 원장 청소
6. ⓕ·ⓖ 알림: 상태 전이당 1회 `cys send --queued --to master "[부서결과] <번호>"` · 가동 판정 처음 1회 `"[부서가동] <번호>"` (Return 을 덧붙이지 않는다 — 큐 배달이 CR 을 포함한다). 보장 = **최대 1회**(기록을 먼저 영속하고 보낸다 · codex 1R F14) — 보내기 실패·유실은 마스터가 매 턴 부르는 `status --pending` 이 받친다
7. 표지 결론: 진행 중 요청이 있으면 표지를 만든다. **지우지 않는다**(치운 것은 3 이 이미 했고, 그 뒤에 생긴 표지는 이 틱이 못 본 confirm 의 것이다)
8. 잠금 해제

### 4-1. 고아 편성 원장 청소(B-1)

- 대상 = `~/.cys/state/formation/*.json` 중 ⑴파일 안 `socket` 필드로 `javis_formation._sanitize_key` 를 **다시 계산해 파일명과 같고** ⑵그 소켓이 `cys-dept-<이름>` 모양이며 ⑶그 이름이 레지스트리에 없는 것(이동 직전 레지스트리 재독).
- 본부 원장(`base` · 빈 소켓 · base 소켓 키)은 명시 제외 — 부서 모양 판별과 두 겹이다(뮤턴트 M7 이 둘을 따로 잰다).
- 120자 절단 분기(`_sanitize_key` 의 해시 접미)는 ⑴의 재계산으로 그대로 맞는다(파일명 파싱을 하지 않는다).
- 삭제가 아니라 `~/.local/state/cys-trash/formation-<시각>/` 로 이동.

### 4-2. create-timeout(2R ⑦)

300초 안에 끝나지 않으면 `create-timeout` 으로 기록하고 첫 자식 pid 를 남긴다. 다음 틱들은 **그 pid 가 살아 있으면 재호출하지 않는다**(첫 자식의 EXIT trap 이 두 번째 등재를 지우는 경합 방지). 죽었으면 레지스트리에서 `mission_key == 키` 를 찾아 판정하고, 없을 때만 다시 부른다(요청당 2회). 첫 자식이 1시간 넘게 살아 있으면 `failed(create_hang)`.

★codex 1R F2·F5·F7(A1-2b): 이 재진입 규칙은 `create-timeout` 상태만이 아니라 **한 번이라도 create 를 부른 모든 요청**에 적용된다 — 틱이 기다리다 죽으면 디스크 상태는 `confirmed` 로 남기 때문이다. 다시 부를 때는 첫 호출과 같은 상한·간격 10분·자원·안내문(`claude_md.txt` 해시 + 설치된 `CLAUDE.md`) 검사를 다시 지난다. 남은 창: spawn 과 pid 기록 사이(마이크로초 단위)에 틱이 죽으면 pid 가 없어 생존 검사를 못 한다 — 그 경우에도 호출 수·간격 기준은 spawn 전에 영속돼 있어 10분 뒤 재호출·요청당 2회 상한은 지켜진다.

## 5. 판정표(결정 트리 · 위에서부터 첫 매칭)

축: R 요청 상태(9) · G 레지스트리 `mission_key == 키`(2) · T base 데몬 묘비(2 — `~/.local/state/cys/dept_tombstones.json`, Windows `%LOCALAPPDATA%\cys\`) · D 부서 데몬 `status --json` 응답(2 · 5초) · F 편성 원장(complete/pending/missing) · P 관문(open/closed/unknown) · E `create` 뒤 15분 경과(2).

| # | 조건 | 판정(`verdict`) |
|---|---|---|
| 1 | R=없음 ∧ G | `unconfirmed-dept`(메뉴로 만든 부서 · `--all` 에서만) |
| 2 | R=proposed | `awaiting-confirm` |
| 3 | R=expired | `expired` |
| 4 | R=failed | `failed` |
| 5 | R=closed ∨ **(T ∧ ¬G)** | `closed` |
| 6 | R=confirmed ∧ ¬G | `queued` |
| 7 | R∈{created,reused,create-timeout} ∧ ¬G | `stalled` |
| 8 | G ∧ ¬D ∧ (F=complete ∨ E) | `gone`(가동했다 사라짐) |
| 9 | G ∧ ¬D | `daemon-starting` |
| 10 | G ∧ D ∧ P=open | `needs-human` |
| 11 | G ∧ D ∧ F∈{pending,missing} | `seats-starting` |
| 12 | G ∧ D ∧ F=complete | `running`(P=unknown 이면 확인 창 안내 한 문장 추가) |
| 13 | 그 밖 | `unknown`(여섯 축 원값을 `status-unknown.log` 에 기록) |

- **5행(적대 2R ③)**: 묘비는 이름(`dept-N`)으로만 걸리고 번호는 재사용된다. 설계 v2.1 의 `R=closed ∨ T` 는 같은 번호로 다시 만든 부서(묘비 해소 실패 · `CYS_DEPT_ROTATE` · REUSE_UP 경로)를 「닫혀 있습니다」라고 말한다. `T ∧ G` 는 실물 행(8~12)으로 판정하고 결과에 `tombstone_residue: true` 를 결정론 칸으로 싣는다. 틱은 **자기 생성 직후 1회만** 해소를 재시도한다(다른 때는 하지 않는다 — GUI 닫기가 먼저 기록한 묘비를 지우면 닫은 부서가 되살아난다).
- **P 축**: `gate_pending` 이 하나라도 null 이 아니면 open. 전부 null 이면 `javis_boot_node.gate_pending_axis_enabled()`(데몬과 같은 3스위치 미러)가 참일 때만 closed, 아니면 unknown(C18 — null 은 「관문 없음」과 「축이 꺼짐」을 구별하지 못한다).
- **망라성**: 1296 조합 전부가 1~13 중 한 행에 떨어지고 1~12 행이 전부 도달된다(self-test). 13행 조합 36개는 전부 `R=없음 ∧ ¬G ∧ ¬T`(요청도 부서도 없는 이름)뿐이다 — self-test 가 전수 출력한다.
- **설계 문장 정정 1건**: 설계 §6-2 는 「8행을 지우면 13번으로 떨어진다」고 적었으나 실제로는 **9행(「켜는 중」)** 이 받는다 — 꺼진 부서를 켜는 중이라고 말하게 되므로 더 나쁘다. 내장 뮤턴트는 실제 귀착 행(9)으로 단언한다.
  - 정정 주석(2026-09-18 · TICKET=dept-impl-A1-2b): 이 정정(「8행→9행」)은 master 판정으로 승인됐다(HANDOFF-A1-2 §4 판단 7건 전건 승인). 설계 v2.1 §6-2 의 「13번」 문장은 이 문서로 대체된다.
- 닫기 요청(`kind=close`)은 이 트리 밖의 짧은 표로 말한다(확인 대기 · 닫을 차례 · 만료 · 닫힘 · 실패).

## 6. 카드

만들기 카드 8줄(+첫 일 1줄 · +첫 부서 줄) — 설계 §7 서식. 계산해서 채우는 칸:

- **지금 여유**: `부서 k/2`(살아 있는 부서 = 레지스트리 − 묘비 · 메뉴 부서 포함) · `켜진 Claude 자리 지금 N개 → 만들면 N+3개`(N = `javis_resource_gate.py check --json` 의 `measured.nodes` — 두 번째 계수기를 만들지 않는다 · 2R ⑥).
- **로그인**(2R ④⑤): 공유안이 서는 조건 = 계정 키(`shared`) ≠ `CYS_PRIMARY_ACCOUNT`(기본 `owner`) — **카드마다 재판정**한다. 같으면 「로그인을 한 번」 문장으로 자동 전환. 새 폴더가 설정 파일 `projects` 에서 그 폴더나 상위 폴더로 신뢰돼 있지 않으면 「처음 한 번 확인 창」 문장을 붙인다(읽기만 — 신뢰 시드는 `javis_seat` 단일 소유).
- **첫 부서 줄**: `~/.cys/.master-bootstrapped` 존재 ∧ `MASTER_DIRECTIVE.md.pre-ceo` 부재 ∧ `MASTER_DIRECTIVE.md ≠ CEO_TEMPLATE.md` 일 때만(cys-dept `ceo_promote` 의 자동 승격 조건).
- **폴더**: `~/Desktop` 이 없으면 「바탕화면에는 보이지 않을 수 있습니다」를 덧붙인다(Windows OneDrive 바탕화면).
- 카드에 시스템 이름(`dept-N`)·내부 용어를 싣지 않는다(시험이 단언) — 닫기 카드만 대상 확인을 위해 `dept-N` 을 보인다(설계 §8-2).

## 7. 계정(D2)

- 기본 `CYS_DEPT_ACCOUNT_MODE=shared`: 카탈로그 `accounts["shared"] = ${CYS_ACCOUNT_DIR:-~/.cys/claude}` 를 시드하고 부서 항목 `account` 를 `shared` 로 둔다 → `cys-dept` 포크 분기를 타지 않아 본부와 같은 설정 폴더(`cys-dept` 무수정).
- 폴백 `CYS_DEPT_ACCOUNT_MODE=fork`(또는 계정 키 충돌): 계정 키 = `CYS_PRIMARY_ACCOUNT`(기본 `owner`) → 현행 포크 경로(`<계정폴더>-<키>` · 로그인 1회). T0 가 불성립이면 기본값 상수 `ACCOUNT_MODE_DEFAULT` 를 `"fork"` 로 바꾼다.
- 알려진 부작용(A-7): 카탈로그 `accounts` 시드가 org-provision 경로의 계정 승인 게이트도 연다 — 남는 방어는 `new_dept_approved` 하나. 시드했다는 사실은 `request.json` 의 `account_seeded` 에 남긴다. ⚠`cys-dept:1325` 는 포크의 목적을 「config state 경합 완화」라고 적는다 — 공유안은 이 완화를 **의도적으로 되돌리는** 결정이다(T0 가 그 대가를 잰다).
- 비대칭 고지(2R 부기): 기존 부서 자동 생성 경로(`javis_bootstrap._dept_fallback`)에는 사람 축(`CYS_DECL_ORIGIN=hook-human`)이 있고, 이 대화 경로에는 없다(「확인한 주체가 사람」의 코드 증거 부재 · 설계 §3-4). 뚫렸을 때 피해 상한 = 부서 1개.

## 8. 미션 배달

- 영속 채널 = 부서 작업 폴더의 `CLAUDE.md`. **실제로 이 파일을 cwd 로 읽는 것은 부서장(master) 좌석 하나다**(`cys-dept` 가 master 만 `--cwd <작업폴더>` 로 띄운다). 운영 담당·작업자는 편성이 `<작업폴더>/cso/` · `<작업폴더>/workers/w1/` 에 띄우고, 그 폴더에는 `javis_seat` 의 얇은 `CLAUDE.md` 가 먼저 있다 — 상위 파일은 상위 폴더 탐색으로만 닿고 두 파일의 우선순위는 미확인이다(2R 1-A · V-MISSION 관찰 항목).
- 이미 `CLAUDE.md` 가 있으면(codex 1R F6 · 2R F4): 이 요청의 바이트와 **같을 때만** 그대로 두고, 다르면 무엇이든(표식 없는 사용자 파일 · 사람이 고친 생성 파일 · 다른 요청의 생성 파일) 건드리지 않고 `failed(claude_md_conflict)` — 교체 분기는 없다(대조와 교체 사이 창 제거). 옛 실패 요청의 잔여물은 그 요청의 `discard` 로 걷는다. 없으면 임시 파일을 `link` 로 붙여 **no-clobber** 로 놓는다.
- `discard` 는 표식이 그 요청 것이고 표식 자기 해시가 맞을 때만 `CLAUDE.md` 를 지운다 — 사람이 고쳤으면 남기고 `kept` 로 알린다(2R F12).
- 확인 뒤 `claude_md.txt` 가 바뀌거나 사라지거나 해독 불가가 되면 `confirm` 은 exit 7, 틱은 `failed(claude_md_changed)`(재호출 직전에도 다시 대조 · codex 1R F7·F15).
- `kickoff` 본문: `[부서시작 <번호>] (CLAUDE.md sha256 <앞 12자리>) 오너가 처음 맡긴 일: <카드에 보였던 그 문장>` — 12자리는 `CLAUDE.md` 표식 줄의 sha256 과 같은 값이다(부서장이 대조).

## 9. 시험·뮤턴트

- `python3 -m unittest tests.test_dept_request`(bin 폴더에서) — 임시 HOME · 가짜 cys/cys-dept/cysd/org · 실 `~/.cys/dept-requests` 무접촉 단언.
- `python3 tests/mut_dept_request.py` — 변이 43종(A1-2 17종 + A1-2b 1R 17종 M17~M33 + 2R 9종 M34~M42 · 수리 1건당 1 · 2R F13·F15 는 결정론 시험 부재로 뮤턴트 없음 — 심사표 정직 고지). 적용 단언 → 기대 킬러 시험 이름으로 귀속 → import 오류는 CRASH(측정 무효)로 따로 센다. `M7a`(본부 제외만 끄기)는 부서 모양 판별이 두 번째 벨트라 **생존이 예상값**이고, 두 벨트를 함께 끈 `M7` 이 킬되는 것으로 그물을 증명한다.
- `python3 javis_dept_request.py self-test` — 결정 트리 1296 조합 · 13행 조합 전수 출력 · 내장 뮤턴트(8행 삭제 · 옛 5행) · javis_org 의미 대조(+한 글자 변이) · 레인 · 계정 키.
- Rust: `cargo test --bin cysd builtin` — 잡 계약 핀(command 레인 · base_only · 마커 · CSO 신원 · 표지 게이트 부재 · 매분 · 버전 불변) + id 선점 conflict 핀.

## 10. 범위 밖(이 티켓에서 안 한 것)

앱 M1·M7(A1-3) · Feed 카드 T6 · Windows purge-state(N3) · 스킬·MASTER_DIRECTIVE·CEO_TEMPLATE(A1-2d) · A1-2e 좌석 컨텍스트 정지선(배포 전 선결 — 이 기능은 그 전에 배포하지 않는다).
