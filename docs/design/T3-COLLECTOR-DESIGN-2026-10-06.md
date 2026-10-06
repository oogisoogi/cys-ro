# T3 수집기 설계 1장 (TICKET=agora-t3-pack-collector · 2026-10-06 13:2x · 295 t3-collector)

> 이 문서는 구현 **전** 설계다. 브리프 `~/axdev/master/briefs/2026-10-06-agora-t3-pack-collector.md` §2-0 2. 의 다섯 칸(⑴~⑸)과 §6 3·7·8,
> 그리고 §7 master 결정 6개를 전제로 쓴다. 📌 = master 판정이 필요한 자리(구현 착수 0).
> 실측 기준 = jarvis-agora **main e0f5df5** · cys = **merge/v0.14.43 7e7aa5da**(내 가지 `t3/collector-118` = `~/axdev/.wt/cys-118-t3`).
> 근거 표기 = `파일:줄`(그 커밋 기준). 「미확인」 = 재지 못한 것.

## 0. 한 줄 그림

```
[쓰는 자리 4종 · 팩/CLI]                       [일정 · cysd 30분마다]                          [아고라 클라이언트 · 발신 전부]
 훅 실패 cys_hook_fail ─┐                        schedule.json 잡 agora-counsel                  agora counsel auto --facts <파일>
 preflight FAIL/WARN ──┼─▶ javis_counsel.py signal ──▶ <설정>/counsel/signals.jsonl           ├ 끔·가입·날짜 판정(state.json)
 cys-dept rc≠0 ────────┤   (형식 밖 = 버림 · 끔 = 안 씀)      │                                 ├ 신호 1통 → 같은 바이트로 signals-sent.jsonl
 rotate·pack-update ───┘                                       │                                 ├ 일일 1통(사실 파일 → 닫힌 칸)
                                    javis_counsel.py tick ─────┴─▶ ① 클라이언트 첫 설치(동봉본) ─▶ ├ 주간(주기 1번) claude -p 1회 → verify → send
                                                                  ② 일일 사실 수집(결정론)        └ 결과 = state.json · counsel.log (화면 0)
```

## ⑴ 부품 배치 — 권고 그대로(발신·검증·원장 이동 = 아고라 클라이언트 · 신호 쓰기·사실 수집·일정·동봉 = 팩)

| 부품 | 자리 | 하는 일 | 근거 |
|---|---|---|---|
| A. 신호 쓰기 도우미 | 팩 `cysjavis-pack/bin/javis_counsel.py signal --source --op --error-code` (stdlib · `sys.path` 가드) | 한 줄 `{"ts","source","op","error_code","version","os"}` append · 정규식 밖 = 버림 · LF·BOM 0 · 실패 전부 삼킴(rc 0) · `counsel.auto` 꺼짐/못 읽음 = 안 씀 | `mail.py` 정규식 L60~L66 를 같은 값으로 복제 + 두 저장소 시험 벡터 동일 |
| B. 쓰는 자리 4종 | 팩·CLI 원본(아래 표) | A 를 부른다(Rust 는 같은 줄을 직접 append) | 명세 §13-3 표 |
| C. 일일 사실 수집 | 팩 `javis_counsel.py facts` | 일일 칸 재료를 결정론으로 모아 `<설정>/counsel/facts.json` 1개로(LLM 0) | §1-2 표 · 아래 ⑤ |
| D. 일정 진입 | 팩 `javis_counsel.py tick` | ①클라이언트 첫 설치 ②`facts` ③`<설정>/lib/bin/agora counsel auto --facts …` 호출 | ⑵ |
| E. 동봉·첫 설치 | 팩 `cysjavis-pack/install/agora-client-<핀>.zip.b64` + `install/agora-client.pin` | 📌1 참고 | master 결정 1 |
| F. 발신 일체 | 아고라 `agora/collector.py`(신설) + `agora counsel auto|off|on` + `whoami` 첫 줄 | 하루 판정 · 신호 묶기·발신·원장 이동 · 일일 · 주간 작성기·검증·발신 · 끄기 | 허용목록 `tests/wiring-allowlist.txt` L25 의 `send_weekly` 호출부가 `agora/` 안에 생긴다 → **같은 커밋**에서 L25 삭제 |

**원장 이동 잠금** — 팩 A(쓰기)와 아고라 F(옮기기·비우기)가 같은 파일을 만진다 → 둘 다 **옆 잠금 파일** `<설정>/counsel/signals.lock` 을 잡는다.
팩 `javis_lock.FileLock`(POSIX `fcntl.flock` · 윈 `msvcrt.locking`) ↔ 아고라 `agora/_lock.py`(같은 두 수단) — 같은 OS 수단이라 서로 막힌다(윈 바이트 범위 위치 일치는 구현 때 시험으로 확인).
옮기기 = 잠금 안에서 `signals.jsonl` 원문 바이트 → `signals-sent.jsonl` 끝에 그대로 append(줄끝 LF 하나 · 재직렬화 0) → fsync → 원본 비우기(옮기기 먼저 · §13-3 2.).

## ⑵ 일정 수단 — 권고 = 팩 `schedule.json` `action:"command"` 잡

| 비교 | ⓐ schedule.json 잡(권고) | ⓑ launchd/schtasks(아고라 `resident install` 선례) | ⓒ cysd 내장 잡(Rust `builtin_jobs`) |
|---|---|---|---|
| 깔리는가 | 팩이 있는 PC 전부(팩 갱신 MergeUser = 새 vendor id 끝에 추가 · `pack.rs:2484-2545`) | `agora resident install` 을 **사람이 돌린 PC 만**(`onboard.py` 자동 설치 0 · 실측) | 바이너리 판올림 필요 |
| 윈 | 같은 문법 · 스케줄러 cfg 가름 없음(`main.rs:1407-1408`) · 셸 = 동봉 Git bash(`schedule.rs:2627-2656`) | schtasks XML 별도 경로(`resident.py:863`) | 같음 |
| 잠든 PC | `every_minutes` = 깨면 **한 번** 발화(`schedule.rs:1314-1321`) ⇒ 「그날 첫 판」이 깬 직후 생긴다 · `time` 잡은 10분 넘게 늦으면 **건너뜀**(L1477-1483 → 쓰지 않는다) | launchd 는 깬 뒤 발화 | ⓐ와 같음 |
| 부서 데몬 | `base_only: true` 로 본부 데몬 1개만(`schedule.rs:1650-1666` · 안 하면 부서 수만큼 중복) | 해당 없음 | 같음 |
| 승인 겹 | `command` 는 승인 겹 없음(L1654-1675) | 없음 | 없음 |
| 상한 | 600초 뒤 「시간 초과」 오류만 · 자식은 **안 죽인다**(L2773-2787) → 작성기가 스스로 상한(⑶) | 없음 | 같음 |

잡 1줄(안): `{"id":"agora-counsel","every_minutes":30,"action":"command","base_only":true,"if_absent":"skip","command":"\"${CYS_PY:-python3}\" \"${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_counsel.py\" tick"}`
- 30분 = 그날 첫 판 지연 상한(06:00 KST 직후 ≤30분 · 잠든 PC 는 깬 직후). 매 판 비용 = 날짜 판정만(파일 1개 읽기) — 하루 일은 판정 통과 1회.
- ⚠U1 이 잡마다 `bulk`·`publish` 필수 칸을 들인다(`u1:src/update/sched.rs:1-40` · 없으면 true) — 병합 때 그 칸 값 = master 판정(내 권고 `bulk:false`·`publish:true` · 뜻 미확인).
- **§13-6 「그날 첫 `agora` CLI 호출이 대신」 = 이 판 미구현 권고**(📌4): 팩이 있는 PC 는 cysd 일정이 반드시 있고, cysd 가 없으면 팩·좌석도 없다(신호도 안 생김).

## ⑶ 주간 작성기 실행 수단 — master 결정 3(헤드리스 단일 턴)의 구체안

- 자리 = 아고라 `agora/collector.py` · 기존 `resident.py` 의 깨움 부품을 **그대로 재사용**: `find_agent`(L396) · `_agent_env`/`claude_config_dir`(L532·L574 = 그 집 계정 설정 폴더) · `run_agent`(L473 · 시간 상한 · `_kill_tree` L495).
- cwd = `<설정>/counsel/writer/`(전용 빈 폴더 · master cwd 아님 → 핀·jsonl 오염 0). 「새 cwd 신뢰 창」은 `-p` 모드에서 뜨지 않는지 **구현 첫 시험에서 실측**(뜨면 그 자리에서 【질문】).
- 인자(안) = `claude -p <프롬프트> --output-format json --max-turns 1` + 도구 0(정확한 플래그 이름은 설치된 claude 판에서 실측 후 확정) · 시간 상한 300초(cysd 600초 안).
- 1주기 1호출 — 호출 **전에** `state.json` 에 `weekly[<주기>] = "writing"` 을 적는다(죽어도 재호출 0) · 입력 상한 24KB(넘으면 오래된 줄부터 자름 · 자른 사실을 state 에).
- 입력(결정론) = `evidence_sources(ctx)` 표 + 그 주기의 일일 사실 요약(계수만). 프롬프트 = 「아래 표의 (종류,id)와 그 원문의 부분 문자열만 인용 · 출력 = JSON 세 칸(blocked·workarounds·wishes) 각 ≤3」. `top_features` 는 **모델이 아니라** `cmd` 집계 상위 5 를 기계로 채운다 · `owner_note` 칸 0.
- 출력 처리: JSON 못 읽음·시간 초과·rc≠0 = **「포기」**(빈 보고 아님 · `weekly_skipped` 안 실음 · 다음 주기에 다시) → `verify_evidence` 거부 항목 빼고 **다시 verify(토큰 0)** → 비면 빈 보고(발신 0 · 다음 일일에 `weekly_skipped`) → 거부 0 일 때만 `send_weekly`.
- `send_weekly` 반환: `pending` = 다음 판 같은 주기 재호출(작성기 재실행 0 · pending 문서 재전송) · `superseded`·`expired` = 로그 · 429 = 그 주기 포기 · `rejected` 비지 않음 = 작성기 결함 로그(시험 적색 대상).
- 토큰 = 참가자 계정 주 1회 1호출. 시험 중 우리 계정 호출 수는 보고에 적는다.

## ⑷ role → `source` 사상표(실측 = cys `cys list` 실값 + 배정 코드)

| `CYS_ROLE` 실값 | 근거 | `source` |
|---|---|---|
| `master` | `javis_formation.py:106` · `cys-dept:2828` | `master` |
| `cso` · `cso-N` · `cso-fresh-<epoch>` | `schedule.rs:1841` · `alert_route.rs:132-141` | `cso` |
| `worker` · `worker-N` · `worker-<접미>`(실측 `worker-eduscan`) | `state.rs:3451-3474` · `cys list` 13:2x | `worker` |
| `reviewer` · `reviewer-codex` · `reviewer-gemini` · `reviewer-grok` · `reviewer-claude-N` · `planner*` | `javis_formation.py:107-121` · `javis_boot_node.py:180-186` · `caps.rs:113` | `worker`(권고 · 좌석에서 난 훅 실패라 좌석 층) — 대안 = 버림 |
| 그 밖·빈 값(좌석 밖에서 돈 훅·팩 도구) | — | `pack` |
| 팩 doctor · 부서 도구 | 명세 §13-3 | `pack`(역할 무관) |
| rotate · pack-update | 명세 §13-3 | `update`(역할 무관) |
판정 = 접두(`<역할>` 또는 `<역할>-…`) · 소문자만.

## ⑸ 일일 보고 `day`·계수 — 권고 그대로

- `day` = 발신 시점 `counsel.day_of(now)`(06:00 KST 경계 · `counsel.py:183`). 같은 판의 신호 통과 봉투 날짜가 같아 데스크 `signature_mismatch`(L708 · 「같은 날 = 봉투 ts 의 day_of」)와 맞는다.
- 계수(`tick_errors`·`hook_rc_nonzero`) = **지난 일일 발신 성공 시각 이후** 새 줄 수(줄 머리 시각으로 셈 · 256KB 넘김 `.1` 파일까지 읽음 → 회전에도 안 샌다). 첫 판 = 최근 24시간.
- `errors.signatures` = **같은 판에 보낸 신호 통의 서명 집합**(신호 429·0건이면 빈 목록) ⇒ 부분집합 보장.
- 신호와 일일은 같은 판에서 신호 먼저 · 각자 다른 `thread_id`(`counsel/state.json` 에 대화 id 둘).

## §6 3·7·8 실측 표(일일 칸 출처 · 쓰는 자리)

| 칸·자리 | 출처(실측) | 이 판 처리 |
|---|---|---|
| `version.host` | `cys --version`(clap · `cys.rs:17`) | 그대로 |
| `version.pack` | `<팩>/.pack-version` 첫 줄(`pack.rs:1981`) | 그대로 |
| `os` | `platform.mac_ver()` / `platform.release()` → `macos-15.6` · `windows-11` | 정규식 밖이면 `macos`·`windows` 만 |
| `seats` | `cys list` 의 `role=` 열 → ★**범주로 접는다**(리뷰 ⑬ · 원 역할 이름엔 사용자·호스트 이름이 들 수 있다): `master` · `cso`(cso·cso-*) · `worker`(worker·worker-*·reviewer*·planner*) · 그 밖(빈 값 포함) = `pack` · `roles` = 범주 정렬·중복 제거 · `count` = 비종료 좌석 수 | 그대로 |
| `doctor` | **`cys doctor --json`**(Rust · `cys.rs:10798` · `summary{ok,warn,fail,skip}` L10852 · 항목 이름 16개 전부 `[a-z0-9-]{1,40}` 적합 · 명세 예시 `dept-awakening-seed`·`runtime-seal` 이 이 이름) | 그대로 |
| `errors.tick_errors` | `~/.cys/dept-requests/tick-errors.log` 새 줄(`javis_dept_request.py:1923` · 줄 머리 iso) | 그대로 · 그 밖 tick 오류 계수기는 없음(미확인 = 0건) |
| `errors.hook_rc_nonzero` | `${CYS_STATE_DIR:-~/.cys/state}/hook-errors.log` 새 줄(`_lib.sh:536-552`) | 그대로 |
| `updates` | U1 `state.json` 에 `last_result` **없음**(설계 문서에만 · `AUTO-UPDATE-118.md:333` · 러너 = U2/U4) | **이 판 칸 생략** · 접점 파일 `<설정>/counsel/updates.jsonl`(`{"from","to","result","at"}` 한 줄씩 · 최근 7일 ≤10) 형식만 정의 → U2 러너가 쓰면 다음 날부터 실림 |
| `depts` | active = `${CYS_DEPTS_JSON:-~/.cys/depts.json}` 항목 수(`cys-dept:63`) · tombstones = `<본부 상태>/dept_tombstones.json`(`cys-dept:150-157`) | 못 읽으면 칸 생략 |
| `uptime` | `~/.cys/state/delivery-base.epoch.json` 의 `started`(데몬 기동 시각 · `delivery.rs:791-827`) ⚠명세가 든 `boot-epoch` 는 **난수**(시각 아님 · `boot_supervisor.rs:829-882`) | `last_boot` = 데몬 기동 시각 · `uptime_s` = now − 그 값 |
| 훅 `op` | `cys_hook_fail` 실호출 6곳 · 이름 5종(session-start · directive-event-inject · dept-chat-inject · inject-background · role-bootstrap) → `hook.<이름>` 전부 ≤32 | `error_code` = `hook.rc<rc>` |
| doctor 신호 | `javis_preflight.py main()` 집계 L11103 뒤 · id 91개(`C27.xxx` 꼴 · 원문 그대로는 정규식 0/91) | `op` = `preflight.c<NN>` · `error_code` = `doctor.c<NN>.fail|warn`(명세 표 꼴) — ⚠C82·C83 이 두 검사씩, `C03.pin.*` 6개가 한 `op` 로 접힌다(📌3) |
| 부서 도구 | exit 11 = 잠금 실패(윈 · 실발생은 파이썬 heredoc `sys.exit(11)` 8곳 → 셸로 전파) · exit 12 = depts.json 판독 실패(파이썬 11곳 + 셸 7곳) | `cys-dept` 맨 위 EXIT 트랩 1개 → rc ∉ {0, 2} 이면 `op`=`dept.<동사>` · `error_code`=`dept.exit<rc>`(2 = 인자 오타 = 잡음이라 뺌 · 권고) |
| 업데이트 | `run_rotate`(`cys.rs:20930` · rc 21~25 상수 L20811-20815) · `run_pack_update`(L26928 · Err→1 · 3 = 재주입 저하 · 4 = 수락 저하 · `binary-too-old`) | Rust 함수 1개(신호 줄 직접 append · 파이썬 호출 0) · `error_code` = `update.drain_partial`·`update.daemon`·`update.daemon_up`·`update.pack`·`update.restore`·`update.reinject_degraded`·`update.accepted_degraded`·`update.binary_too_old`·`update.failed`(그 밖 Err) · master 결정 2: 즉시 4종 = 「그날 첫 신호 통이면 즉시 · 아니면 다음 날 + 로컬 로그 1줄」 → 이 판 러너가 없어 해당 코드 발생 자리 0(접점만) |

## 📌 master 판정이 필요한 자리(구현 착수 0 · 각 권고 + 단점)

1. **동봉 형식 — 결정 1 「핀 zip 동봉」이 그대로는 안 된다.** 팩은 `include_str!` 로 바이너리에 박힌다(`build.rs:15-21·48-61` · UTF-8 텍스트만 · CRLF 면 빌드 실패) → zip(바이너리) 불가.
   **권고 ⓐ** = `install/agora-client-<판>.zip.b64`(base64 텍스트 · 줄 76자 LF) + `install/agora-client.pin`(`<판> <sha256> <바이트>`) — 풀 때 디코드 → **사이트 zip 과 같은 sha256** 대조(지문 대조가 그대로 산다) → `<설정>/lib/` 에 풀고 `<설정>/lib/.pin` 표식. 단점 = 바이너리 +약 0.9MB(680,840B × 4/3) · 팩 파일 1개가 큼.
   ⓑ 클라이언트 소스 트리를 팩에 그대로(55파일 텍스트) — 단점: 사이트 zip 지문과 다른 이름(트리 해시) · 팩 git 에 아고라 사본. ⓒ 첫 tick 때 사이트에서 핀 sha 로 내려받기 — 단점: 사이트·네트워크 의존(설치기 옛 방식 · 09-09 분리 이전).
   **무접촉 규칙**: `<설정>/lib` 가 이미 있고 `.pin` 판·sha = 핀 → 무접촉 · `.pin` 없거나 다른 판(사람·옛 설치기가 깐 것) → **무접촉 + 로그**(교체 = U1/U2 `agora-client` component) → 그 PC 는 그 클라이언트가 `counsel auto` 를 모르면 발신 0(state 에 사유). ⇒ **§9 로 대체**(`.pin` 글자 → 트리 지문 · known 옛 판은 교체).
   ★**판 순서**: 동봉할 zip 은 T3 클라이언트 코드가 든 **0.1.14**(0.1.13 에는 `counsel auto` 가 없다) → 순서 = 아고라 T3 커밋 → 0.1.14 빌드(지문) → 팩에 b64·핀 → 게시는 master.
2. **훅 신호의 실제 범위**: 명세 「훅 39개 중 38개가 쓰는 프리루드의 종료 자리」는 실재하지 않는다 — 훅은 계약상 늘 exit 0 이고 rc 를 남기는 자리는 `cys_hook_fail` 6곳(5개 훅)뿐 · 훅 프로세스 자체 rc 를 모으는 곳은 없음(실측 0건). 권고 = **그 6곳만**(`cys_hook_fail` 끝 1줄 · 실패 경로에서만 파이썬 1회 · 늘 return 0 유지). 단점 = 다른 훅 내부 실패는 신호가 안 된다.
3. **doctor 신호 `op` 접힘**: 명세 꼴(`preflight.c<NN>`)을 따르면 C82(2개)·C83(2개)·C03.pin.*(6개)가 한 줄로 묶인다. 권고 = 명세 꼴 유지(이름까지 넣으면 `op` 32자 초과 2건 · `doctor.c38.silent-failure-catalog` 33·`doctor.c79.cycle-verifier-heartbeat` 35). 단점 = 그 몇 검사는 데스크에서 구분 안 됨.
   + preflight 는 `inject-context.sh`(매 프롬프트 경로)·`javis_bootstrap --fix` 에서 돈다 → 같은 WARN 이 하루 수백 줄 가능 → `signals.jsonl` 상한(7일 지난 줄·5,000줄 넘는 앞줄 버림 · 미가입 PC 의 무한 증가도 막음) 권고.
4. **§13-6 CLI 첫 호출 대체** = 이 판 미구현 권고(⑵ 마지막 줄 근거). 단점 = 명세 문장 1개 미이행(명세에 「팩 PC = cysd 일정이 대신」 1줄 정정 필요 = master 몫).
5. **Rust 편집**: `cys.rs` `run_rotate`·`run_pack_update` 끝 + 새 작은 모듈 1개. U1 가지도 `cys.rs` 를 고친다(L2768·L5303·L24157 근처 · 내 자리 L20930대·L27060대와 **같은 줄 아님** · `build.rs` 는 내가 안 건드림). W2 는 `javis_preflight.py` L5875(내 자리 L11103 과 다름). ⇒ 브리프 §4 ③ 해당 없음으로 판단 · 병합 순서만 master.
6. **좌석 역할 `reviewer*`·`planner*` → `worker`**(⑷) — 대안 = 버림.

## 시험 계획(요약 · 브리프 2-5 그대로)
아고라: 결정론 생성(같은 원장·now·핀 → 같은 canonical) · 이동 전후 `evidence_sources` 키 동일 · CRLF 입력 → LF 쓰기 · 06:00 KST·월요일 06:00 경계 · items 101 · 32KB · 429·code 8 · 끔·못 읽는 설정 · 핀 데스크 0·2 · 빈 보고 · 거부 1 · 작성기 rc≠0/시간 초과/JSON 깨짐 = 포기 · 뮤테이션 새 분기 전건 KILLED(대상 줄을 실제로 바꾸는 뮤턴트 확인) · `commit_gate.sh` 전건.
팩: `javis_counsel.py` 단위 시험(`cysjavis-pack/bin/tests/` 관례) · 훅 「항상 return 0」 회귀(`test_hook_fail_log.py` 확장) · 잠금 상호배제(팩 쓰기 ↔ 아고라 옮기기) · Rust 신호 함수 단위 시험 · 팩 건강 검체 로컬 실행.
라이브 = 시험 참가자 키만(격리 `AGORA_CONFIG_DIR`) · 데스크 `mail.sync` added·quarantined 0 실측.

## 8. master 판정 반영(0b3820fe · 13:28) — 구현 기준
- 📌1 = ⓐ(b64 + 핀 · 디코드 후 사이트 zip sha256 대조 · `<설정>/lib/.pin` · 무접촉) · 팩에는 한 판만(옛 판 b64 는 같은 커밋에서 삭제) · 동봉 판 = 0.1.14.
- 📌2 = `cys_hook_fail` 6곳만 · 📌3 = `preflight.c<NN>` 유지 + 상한(7일·5,000줄) · 📌4 = §13-6 미구현 · 📌5 = 병합 순서 U1 → U3 → T3(build.rs 불가침) · 📌6 = reviewer*·planner* → worker.
- ★**접기(추가 1) 명세 대조 1줄**: 명세 §1-1 items 는 `count` 칸을 가진다 → 같은 묶기 키(= `source`·`op`·`error_code`·`version` 의 sha256 앞 32) 줄은 발신 때 **한 항목 + `count`**(그날 첫 줄만 남기는 길은 쓰지 않음 · `os` = 그 묶음 마지막 줄 값 · `first_seen`/`last_seen` = 최소/최대 ts). 판이 다른 같은 오류는 묶기 키가 달라 다른 항목이다(명세 그대로).
- U1 잡 칸 = `bulk:false` · `publish:true`(현 스케줄러가 모르는 칸을 받는지는 팩 구현에서 실측 후 반영).
- 이 문서 자리 이동: 아고라 저장소(공개 표현 규약 = 이 문서의 터미널 내부 이름이 금칙어) → 팩 저장소 `docs/design/` · 아고라 쪽 0106476 커밋은 push 전이라 되감았다(작성자 판단).

## 9. 리뷰 반영(2026-10-06 · 판 가지 `t3/collector-118` 을 U1 병합본 4d0aab95 위로 옮긴 뒤)
- **설치 잠금(⑥)**: `ensure_client` 는 `<설정>/lib.install.lock`(신호 잠금과 같은 수단 · `a+` · 0번 바이트 · 대기 상한 60초 → `busy`)을 존재 판정부터 게시까지 쥐고, 잠금 안에서 다시 판다. 게시는 **덮지 않는 rename**(맥 `renamex_np RENAME_EXCL` · 리눅스 `renameat2 RENAME_NOREPLACE` · 윈 `MoveFileEx` 기본) — 그 사이 `lib` 가 생기면 임시 트리를 버린다(`raced`).
- **같은 판 = 트리 지문(⑦)**: 지문 = sha256(정렬한 `<posix 상대경로>\t<파일 sha256>\n` 줄의 UTF-8 · 맨 위 `.pin`·`__pycache__/`·`*.pyc` 뺌). 핀 = `<판> <zip sha256> <zip 바이트> <트리 지문>`(3칸 옛 꼴도 받는다 — 지문을 동봉 zip 에서 잰다). 없음 = 설치 · 핀 지문 = 무동작 · `install/agora-client-known.txt`(0.1.12 · 0.1.13) 지문 = 교체(옆으로 치움 → 게시 → 삭제 · 사이에 끊기면 `lib` 없음 = 다음 판이 새로 깐다 · 찌꺼기 `lib.tmp-*`·`lib.old-*` 는 잠금 안에서 치운다) · 그 밖 = 불가침 + 로그. ⚠동봉 판을 올릴 때 지금 판 지문을 known 에 더해야 그 판 PC 가 따라온다.
- **한 판 상한(⑨)**: tick 전체 540초(cysd 600초 안) · agora 몫 = 540 − 경과(바닥 30) · 넘으면 자식 프로세스 그룹째 끝낸다(POSIX `start_new_session` + `killpg` · 윈 `taskkill /T /F`) + `tick.log` `timeout`.
- **BACKLOG(cysd · 이 티켓 밖)**: cysd 는 600초 시간 초과된 command 잡의 자식(그룹)을 죽이지 않는다(`schedule.rs:2784-2786` `fire_command` = `tokio::time::timeout(600s, c.output())` · `kill_on_drop` 미설정 → 「command timed out (600s)」 오류만 · 셸·그 자손은 계속 돈다) — 잡 쪽 자기 상한이 유일한 방어선이다.

## 10. 리뷰 3R 반영(2026-10-06 · §9 의 일부를 대체)
- **①** 신호 쓰기 = `signals.lock` 을 잡은 **뒤** 끄기 재확인 — 첫 확인과 잠금 사이 `agora counsel off`(설정 끔 → 잠금 쥐고 모은 줄 지움)가 끼면 0줄.
- **③** facts = `cutoff`(지금 · 밀리초로 자름)를 오류 로그 읽기 **전에** 정하고 계수 창 = `(since, cutoff]`(since = state.json `daily_ok_at` 또는 cutoff − 24h) · facts.json 에 `cutoff`·`since` · 아고라가 cutoff 를 일일 pending 에 박고 성공 때 `daily_ok_at = cutoff`(facts 없음·cutoff 없음·2시간 넘음 = 일일 거절). 팩 tick 은 facts 쓰기 실패여도 로그 남기고 agora 를 돌린다(daily 완료 표식은 팩이 쓰지 않는다).
- **④** 게시 = 원자 「있으면 실패」 rename 만(맥 `renamex_np RENAME_EXCL` · 리눅스 `renameat2 RENAME_NOREPLACE` · 윈 `os.rename`) · 수단 없음/파일 시스템 거절 = 아무것도 안 함 + `no_atomic_noreplace`(옛 lexists→rename 대체 길 삭제) · 교체 중 경합 = 옆으로 옮긴 `lib.old-*` 는 지우지 않고 로그(`kept_old`) · 자동 청소 = `lib.tmp-*` 만(§9 의 「`lib.old-*` 도 치운다」 폐기).
- **⑤** 트리 지문 **v2** = sha256(정렬한 `<종류>\t<posix 상대경로>\t<sha256 또는 ->\n`) · 종류 f·d(빈 폴더 포함)·l·o · 뺌 그대로 · zip 지문 = 같은 산식(폴더 = 명시 항목 + 모든 항목 상위 경로) · 설치된 트리에 링크·특수 파일·빈 폴더 = 불가침 + 로그 · 빈 폴더를 만드는 동봉 zip = 거부 · 핀 넷째 칸 ≠ 동봉 zip v2 지문 = 설치 거부(`pin_fingerprint_mismatch`) · known 표 v2 재계산(0.1.12 `1362a6e5…` · 0.1.13 `2f7b44a0…`).
- **⑥** cysd `Job` 이 `bulk`·`publish` 를 보존(동결 원샷 재직렬화가 떨어뜨려 U1 `validate_job` 이 거부하던 자리 · 동작 변화 0).
- **⑦** 한 판 상한 = 남은 몫(540 − 경과 · 내림) < 30초면 agora 를 띄우지 않는다(`no_time`) · 그 밖 = 남은 몫 그대로(§9 의 「바닥 30」 폐기 — 총합이 540 을 넘었다).
- **⑧** 윈 CI(`windows-health.yml`)가 `test_javis_counsel.py` 를 실기로 돌린다(교차 잠금 경합·0번 바이트 잠금 포함 · POSIX 전용 검체만 사유 붙여 건너뜀).
