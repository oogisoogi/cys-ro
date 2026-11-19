# HANDOFF · TICKET=cysr-1116-cc-autoopen-1120 — 컨트롤 센터(CC)가 저절로 뜨는 결함

- 기준판 = `dea2e1853`(1.1.16 통합 기준 · 다른 1116 갈래와 같음 — `git log` 로 확인) · 가지 `feat/1116-ccopen` · worktree `~/axdev/.wt/cys-1116-ccopen`
- 지금 떠 있는 앱 = `/Applications/cys.app` **1.1.14**(데몬 build_id `270e3e21e492` · 11-19 15:04 기동 · `cys identify` 실측). 아래 「라이브」 칸은 그 커밋(`270e3e21e`)의 `ui/src/main.ts` 기준이다.

## 1. CC 가 보이게 되는 모든 경로 (전수 · UI·Rust·이벤트)

CC 를 보이게 하는 코드는 `setCcOpen(true)` 하나뿐이다(`#cc-panel` 의 `hidden` 을 바꾸는 곳은 이 함수 1곳 · CSS 는 `#cc-panel[hidden]{display:none}` 과 `body.cc-office #cc-panel[hidden]` 두 짝으로 숨김이 지켜진다 · 앱 시작 때 `index.html` 은 `hidden`). 그래서 「CC 를 여는 경로」 = `setCcOpen(true)` 를 부르는 곳의 전수다.

| # | 경로 | 계기 | 사람 입력? | 라이브 1.1.14 | 이 가지(고친 뒤) |
|---|---|---|---|---|---|
| 1 | 상단 「Control Center」 단추 `btn-cc` | 클릭 | 사람 | 연다 | 연다 · 원인 `user.button` |
| 2 | 화면 설정 팝오버 「컨트롤 센터 열기」 | 클릭 | 사람 | 연다 | 연다 · `user.theme_pop` |
| 3 | 커맨드 팔레트(⌘K) 「Control Center 토글」·「승인 Feed 탭 열기」 | 선택 | 사람 | 연다 | 연다 · `user.palette` |
| 4 | 사이드바 상태판 「승인 요청 N」 단추(N>0 일 때만 보임) | 클릭 | 사람 | 연다 | 연다 · `user.board_approvals` |
| 5 | 데몬 이벤트 `approval.stalled` | 데몬 판정 | 아님 | **저절로 연다** | **저절로 연다(유일)** · `approval.stalled` |
| 6 | `feed.item.created`(wait 또는 auto_route) 뒤 30초/90초 유예 스케줄러 — 아직 pending 이거나 조회 2회 실패 | 시간 | 아님 | **저절로 연다** | **열지 않는다** · 로그 1줄 `feed.grace suppressed` |
| 7 | 데몬 이벤트 `ui.open_panel`(= `cys open-control-center` · 말로 열기) | CLI | 사람 CLI 또는 master 좌석만(데몬 호출자 게이트 `ui_command_caller_ok`) | **없음**(1.1.16 신설 · 라이브 앱엔 이 처리기가 없다) | 연다 · `ui.open_panel` |

CC 를 열지 **않는** 것(확인함):
- 다른 데몬 이벤트 분기(경보 `alert_route.*` · `watchdog.proc_count_high`·`duplicate_procs`·`load_high` · `health.*` · `context.threshold` · `pane.idle` · `approval.request` 등) — `onDaemonEvent` 안에서 여는 호출은 5·7 둘뿐이다(시험 ④가 소스에서 센다).
- Rust: 창을 앞으로 가져오는 곳 = `tauri_plugin_single_instance`(두 번째 실행 때 기존 창 `set_focus`)와 상담 창(`counsel.rs` 별도 창) 둘. **CC 를 여는 Rust 경로는 없다**(Rust 는 `daemon-event` 를 그대로 UI 에 넘길 뿐).
- UI 에서 창 활성화(`setFocus`·`window.focus`·`requestUserAttention`) 호출 0 · 밀도(glance)·탭 전환(`setCcTab`)은 CC 를 열지 않는다(⌘G 는 CC 가 열려 있을 때만 동작).

### `approval.stalled` 를 내는 곳(데몬) — 둘
- (a) `governance.rs check_approval_stall` — 데몬이 감지한 승인(`kind=approval` · 데몬 발행 id)이 `CYS_APPROVAL_STALL_SECS`(기본 300초) 넘게 pending · 살아 있는 좌석 항목만 · 항목당 1회. **라이브에서 켜져 있음.**
- (b) `handlers.rs escalate_no_ceo` — CEO 자동 결재 좌석이 없거나(`ceo_seat_empty`) 쓸 수 없거나 HumanOnly 위험이면 **즉시**(age 0). 단 `CYS_APPROVE_AUTO_ROUTE=1` 일 때만이다 — 기본 OFF · 라이브 데몬 환경에 그 값 없음(실측). ⇒ 라이브에서는 (a) 만 산다.

## 2. 11-20 07:3x 에 뜬 것 — 증거

| 증거 | 실측 | 뜻 |
|---|---|---|
| 데몬 이벤트 링(`cys events --after-seq 2162000` 재생 · 4,031건) | 06:52:34 ~ 07:38:21 사이 `ui.open_panel` 0 · `approval.stalled` 0 · `approval.request` 0 · `feed.item.created` 0 | 경로 5·6·7 의 계기가 그 시간에 **없었다** |
| `feed.jsonl` 마지막 항목 | 00:41:29 생성 → 00:43:18 `stale-cleared`(2분 · 5분 방치 아님) · 그 뒤 항목 0 | 유예 스케줄러(6)·방치(5) 모두 대상 없음 |
| 부서 데몬 | `~/.cys/depts.json` = `{"depts":{}}` · 부서 소켓 0 | 이벤트 원천은 본부 데몬 하나뿐 — 위 링이 전부다 |
| 라이브 앱 코드(1.1.14) | `ui.open_panel` 처리기 없음 | 7 은 라이브에 존재하지 않는다 |

**결론(확신도: 높음)**: 07:3x 에 기계(데몬 이벤트·유예 타이머)가 CC 를 연 것은 **아니다**.
남는 후보(기록이 없어 갈라지지 않는다 — 그래서 3번 장치를 넣었다):
- (가) 이미 열려 있던 CC 를 07:3x 에 보신 것. 가장 가까운 자동 열기 후보 = **11-19 17:12:26 「claude 승인 대기 감지 (surface:2253)」** — 데몬 감지 승인이 11분 33초 pending 뒤 `stale-cleared`(스스로 사라짐)로 닫혔다. 5분이 넘었으므로 (a) 경로가 ~17:17 에 `approval.stalled` 를 냈을 가능성이 높다(그 시각 이벤트 링은 이미 지워져 직접 확인은 불가 · 확신도 중). 이 항목은 사람 결재 없이 저절로 사라진 「감지 승인」이었다.
- (나) 사람 입력 경로(1~4) 중 하나의 의도치 않은 클릭(예: 상태판 「승인 요청 N」 단추는 N>0 일 때만 나타나 줄이 밀린다).
- 다음에 또 뜨면 `~/.cys/cc-open.log` 마지막 줄의 `cause=` 가 이 둘을 가른다.

## 3. 고친 것

- `ui/src/ccopen.ts`(신설 · 순수): **원인 표** `CC_OPEN_CAUSES` — 원인마다 `open`/`notify`. 표에 없는 원인은 `notify`(모르는 계기가 화면을 빼앗지 못한다 · fail-closed).
- `ui/src/main.ts`:
  - `openFeed(cause)` — 원인을 반드시 싣는다(타입). 원인 표가 `notify` 면 패널도 탭도 건드리지 않고 로그 1줄만.
  - `setCcOpen(open, cause?)` — 여는 순간(닫힘→열림) 원인 1줄 로그.
  - 모든 여는 호출(7곳)에 원인 문자열을 붙였다. 유예 스케줄러 배선 = `open: () => openFeed("feed.grace")`.
- `src-tauri/src/main.rs`: `log_cc_open` 명령 신설 → `~/.cys/cc-open.log` 에 append(256KiB 넘으면 `.1` 로 한 번 밀기 · 개행 접기 · 400자 상한 · 실패는 삼킴) · `invoke_handler` 등록.
- 로그 줄 모양: `2026-11-20T07:33:05.009+0900 cc-open auto opened cause=approval.stalled` / `… cc-open auto suppressed cause=feed.grace` / `… cc-open user opened cause=user.button`.

### 판정 — feed 30초/90초 유예 경로를 「열지 않음」으로 한 근거
그 항목(`cys feed push --wait`·auto_route)의 결재자는 master 다(워커 지침 §7) — 박사님은 결재자가 아니다. 30초 미결은 「master 가 아직 안 봄」이지 긴급이 아니고, 생성 토스트·승인 대기 배지가 이미 알린다. 사람 소환은 데몬 판정(`approval.stalled`)의 몫이다. ⇒ daemon-detected·stale 만 거르는 것보다 **유예 만료 자동 열기 자체를 없애는 것**이 박사님 원칙(긴급 외 보게 할 일 없음)과 맞다.
- 단점(정직): `--wait` 항목은 데몬 방치 스캔 (a) 의 대상이 아니다(데몬 발행 id 만 센다). master 가 끝내 안 보면 사람에게 화면 전환이 가지 않고, 요청한 워커는 `--wait` 시간 초과(exit 3)로 끝나 master 에 「막힘」을 올린다. 토스트·배지는 그대로 남는다.

### 판단 1건(지시 밖에서 내가 정한 것)
- `ui.open_panel`(말로 열기)은 **연다**로 두었다. 사람이 말로 시킨 것을 master 가 대행하는 명시 요청이고, 데몬이 호출자를 master 좌석·좌석 밖 사람 CLI 로 막는다. 다만 master 가 스스로 부르면 「저절로」와 구별되지 않는다 → 로그에 `cause=ui.open_panel` 로 남게 했다. 막으려면 `ccopen.ts` 표의 한 줄을 `notify` 로 바꾸면 된다(시험 ①이 같이 바뀐다).

## 4. 시험

- `ui/src/ccopen.test.ts`(신설 · 20개 · 실측 20 pass): ① 원인 표 · 데몬 출처 자동 열기 = `approval.stalled`·`ui.open_panel` 둘뿐 · 표 밖 = 알림만 ② `openFeed` 실물(main.ts 에서 꺼내 실행) 경로별 열림/안 열림 ③ 유예 스케줄러 전 구간(probefail 실물 + 가짜 타이머 · 30초/90초/조회 실패/결재됨) CC 0 ④ 배선 전수(모든 여는 호출의 원인 = 표의 원인 · 표의 원인 = 전부 배선 · `onDaemonEvent` 안 여는 호출 = 2개) ⑤ 로그 줄 모양·전이만·한 줄.
- 뮤턴트(고침을 되돌리면 붉음 · 실측): M1 `feed.grace=open`(고침 되돌림) 8 fail · M2 `openFeed` 관문 제거 5 fail · M3 `approval.stalled=notify` 4 fail · M4 열림 로그 제거 1 fail · M5 워치독 분기에 새 자동 열기 1 fail · M6 스케줄러가 원인 없이 열기 3 fail · M7 표 밖 원인 fail-open 1 fail.
- 기존 핀 2곳 갱신: `probefail.test.ts`·`toastaxis.test.ts` 의 `open: openFeed,` → `open: () => openFeed("feed.grace"),`.
- Rust: `cc_open_log_appends_one_line_and_rotates_at_cap`(append·개행 접기·회전·등록 핀) ok · 뮤턴트 R1 등록 제거 = FAILED · R2 회전 제거 = FAILED(원본 복원 cmp 동일) · `cargo test -p cys-app --bin cys-app` 전체 349 pass · 0 fail · 2 ignored.
- bun 전체: 3762 pass · 88 skip · 5 fail(전부 5초 시한 초과 · load 57~72) → 그 파일들(toastaxis·views/tickrec·views/msgharness·probefail)을 `--timeout 120000` 으로 다시 = 206 pass · 0 fail. `bunx tsc -p tsconfig.check.json`(7.0.2) rc 0. `sh ui/build.sh` 번들 성공.
- 화면 게이트(실제 번들 + 대역 · chrome-headless-shell 1248): cc_button · seatgroup · cc_popover_z · statusboard · confirm = PASS(콘솔 오류 0 · cc_button 은 「approval.stalled = 자동 열림」·「승인 요청 누름 = 열림」·「화면 설정 열기 = 열림」을 실제로 잰다 · seatgroup 은 「말로 열기 = 열림」). cc_resize · office_cc = 실행 불가(게이트가 CHROME_PATH 를 안 쓰고 설치되지 않은 playwright 1223 브라우저를 찾음 · 표준 게이트 목록 밖 · 이 변경과 무관).
- 표준 화면 게이트(gate-1116 목록): tickrec(기준 번들 대조 포함) · chat · restart_confirm · focus · seatrows · pillar · rolereuse · stty · nodept · restart · hidden_block = PASS. race = 1회째 R9e 순서 단언 1건 FAIL → 대조군: 기준판 dea2e1853 번들 1회째도 rc 1(R 장면 클릭 「Element is not attached」) · 2회째 기준판 PASS · 이 가지 PASS(load 71~90) ⇒ 부하 타이밍 깜빡임 · 이 변경과 무관(race 는 CC 경로를 건드리지 않는다). 게이트가 작업 트리에 쓴 캡처 2장·폴더 1개는 되돌렸다(커밋 0).

## 4-1. 원작자 파일 바뀐 줄(UPSTREAM_BASE v0.14.52 에 있는 파일)
| 파일 | +/- | 바뀐 자리(기준판 줄) |
|---|---|---|
| `ui/src/main.ts` | +26 −11 | 246(import 1줄) · 1214(setCcOpen 머리 + logCcOpen 신설) · 6183(상태판) · 7321(화면 설정) · 8087~8088(openFeed) · 8116(스케줄러 배선) · 9839~9840(팔레트 2) · 10956(ui.open_panel) · 10966(approval.stalled) · 12365(btn-cc) |
| `src-tauri/src/main.rs` | +44 −0 | 501 뒤(log_cc_open·append_capped_log 신설) · 8504 뒤(invoke_handler 1줄) · 8844 뒤(시험 1개) |
| `ui/src/probefail.test.ts` | +2 −1 | 452(배선 핀) |
| `ui/src/toastaxis.test.ts` | +2 −1 | 950(배선 핀) |
신설(우리): `ui/src/ccopen.ts` · `ui/src/ccopen.test.ts` · 이 HANDOFF · TODO. secret-scan(staged 8파일) clean · 새 파일에 사용자 이름 든 절대 경로 0.

## 5. 재현 메모
- UI 시험: `cd ui && bun test src/ccopen.test.ts`
- Rust: `cargo test -p cys-app --bin cys-app cc_open_log` — 사이드카 입력이 없으면 `resource path binaries/cysd-… doesn't exist`(rc 101)로 빌드가 막힌다 → `docs/integ-1116/gate-1116.sh` 의 `cys-app-inputs` 단계와 같은 자리표시(바이너리 = 다른 worktree 의 것 APFS 복제 · `ui/dist` = `sh ui/build.sh`).
- 부하가 높을 때(load 50~70) `bun test` 전체에서 5초 시한 시험(views/msgharness·tickrec·toastaxis T-1 퍼즈)이 시간 초과로 붉어진다 — `--timeout 120000` 으로 같은 파일을 다시 돌리면 초록(실측). 이 변경과 무관.
