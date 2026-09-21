# HANDOFF — v112-wake (TICKET=v112-wake · 2026-09-21)

브랜치 `fix/v112-wake` (← rebase/v1.1 438d7113). 커밋 3건:

| 커밋 | 내용 | 원격 |
|---|---|---|
| f850f6b2 | lib `src/submit_probe.rs` — 제출 실측 3상태 공용 판정기(❯ 앵커) | push 완료(재승인 b33dfecd) |
| 3097c185 | lib 같은 파일 — 접힌 붙여넣기 `[Pasted text` = NotSubmitted | push 완료(재승인 7deb4e5a) |
| 9937b657 | ①②③④⑤⑥ 본체 | **로컬만 — push 는 재승인 뒤** |

## 끝난 것

### ① 감시 이벤트 → 잠든 master 1줄 각성 (`src/bin/cysd/watch_wake.rs` 신설)
- 트리거 2종: role 좌석(master 외) **입력줄 미제출 + 유휴**(`check_idle` · 판정 = 큐 배달자와 같은 `input_line_state`) · role 좌석 **에이전트 사망**(`agent.exited` 발행 지점).
  빈 입력줄의 유휴는 정상 대기라 깨우지 않는다(판단 — 종전대로 이벤트만).
- 경로: master `pending_queue` 적재 → 기존 `deliver_queued`(입력줄 빈 때만 · 프롬프트 경계 · 사람 타이핑 직후 금지 · 빈 좌석 보류) → 배달 2초 뒤 `cys::submit_probe` 로 제출 실측 → 미제출이면 Return **1회** → 결과 `watch_wakeup.submit` 이벤트.
- 폭주 방지: 이벤트 키 멱등 · 최소 간격 300s(`CYS_WATCH_WAKEUP_MIN_INTERVAL_SECS`) · 시간당 6(`CYS_WATCH_WAKEUP_HOURLY_CAP`) · 미배달 1건 · 1줄(개행 제거·200자) · 억제·실패 = `watch_wakeup.suppressed` 이벤트만 · `CYS_WATCH_WAKEUP=0` 전면 끔.
- 배경 구독(`cys events …` stdout)은 이제 보조다 — 각성의 주 경로는 큐 1줄.

### ② 1.0.1 1분 주기 재주입 규명 + 수리
규명(서브에이전트가 v1.0.1 태그 코드를 읽은 결과 · 줄번호 = v1.0.1 · 【관측】은 코드 판독, 【추정】은 기기 데이터 없이 한 추론):

| # | 발신 지점 | 트리거 | 왜 안 멈추나 | HEAD(1.1.1+) |
|---|---|---|---|---|
| A1 [RESUME] | cys.rs:10307 `boot_agent_on_surface` | cysd 콜드부트 auto-restore(main.rs:1788→2072) → phoenix `restore --auto` → `cys restore` · Tauri 업데이트 뒤 사이드카 restore | 「이미 복원했다」 표식 없음 · phoenix 차단기(300s 3회)는 VERIFIED 마다 리셋(javis_phoenix.py:2239) → 재기동 루프면 영영 안 걸림 【관측 · 루프는 추정】 | 9aab10b6 로 [RESUME]+[RESTORE] 합쳐 1건 · 좌석 표식 TTL 300s(in-seat 경로만) |
| A2 [RESTORE] | cys.rs:14592·14735·14791 | A1 과 같음 | 좌석당 2건 · 표식 없음 【관측】 | 위와 같음 |
| A3 각성 핑 + 전문 | cys.rs:14868 `run_reinject`(ACK 실패 시 14880 전문) | phoenix `stage_reinject`(6s)·`stage_g2_ack`(4s) — 복원마다 좌석당 핑 2 + 전문 최대 2 | 4~6초 대기로는 ACK 가 거의 안 옴 【추정】 · 「이미 깨어 있음」 기억 없음 · 단계 표식이 데몬 기동 시각에 묶여 재기동마다 초기화 【관측】 | phoenix `ack_ping_gate`(대형·유휴 세션은 핑 생략) · **run_reinject 자신은 무방비였다 → 이번에 수리** |
| B hook-missing feed | cys.rs:4917 `warn_if_awakening_hooks_missing` → feed.push(4978) | 매 launch-agent | 중복 억제 없음 · 윈도에서 훅 명령 문자열이 `bash "…"` 와 `C:/…/bash.exe "…"` 로 갈려 상시 missing 가능 【추정】 | **미수리(범위 밖 판단 · 아래 미결)** |
| C [RESUME]+[RECOVER] | cys.rs:14542 node-recover | `CYS_AGENT_AUTORESTART=1` 일 때만 | 기본 꺼짐 | 같음 |
| D cycle [RESUME] | cys.rs:14474 | cycle-autopilot-tick 1분 · live 모드만(기본 shadow) | 쿨다운·단일비행 가드 있음 | 같음 |
| G 훅 지침 덤프 | hooks/session-start.sh:203 | 매 SessionStart(resume 포함) | source 필터 없음 | HEAD 는 source 읽고 resume 크기 상한 |

「master 노드 부재」: phoenix `_alive` 가 seat=empty 를 죽음으로 본다 — 윈도에서 프로세스 트리 판독이 claude 를 놓치면 전 좌석이 빈 좌석으로 보여 복원이 매번 전원을 되살린다 【추정 — 그 기기의 `cys status --json` seat·agent_alive 필요】.

수리(이번): `src/reinject_guard.rs` + cys.rs `run_reinject --check` 배선 — 좌석별 기록 파일(`<상태폴더>/reinject-guard/<sid>.json` · 데몬 재기동을 넘어 유지) · ACK 뒤 1시간 핑·전문 0 · 시간당 핑 3 · 간격 120s→240s · ACK 수신 즉시 이력 비움. 강제 reinject(--check 없음 · CEO 경로)는 건드리지 않는다.

**1.0.1 기기를 1.1.2 로 올리면 폭주가 멈추나 — 【추정 · 코드 경로 기준】 「유계로 줄어든다, 0 은 아니다」**
- A3(핑+전문 = CTX 100% 의 주범)은 좌석당 **시간당 3회 이하**, ACK 가 한 번이라도 오면 1시간 0회.
- A1/A2 는 합쳐져 in-seat 경로에서 좌석당 **5분에 1회 이하**(fresh 기동 경로는 표식 없음).
- 남는 것: 데몬이 1분마다 재기동하는 원인·윈도 좌석 판정·hook-missing 문자열 불일치는 이번에 안 고쳤다 → 그 기기 데이터(`phoenix-restore.log` · `lockloss.state` · `cys status --json` 의 started_at 변화 · settings.json 훅 command 문자열) 없이는 「멈춘다」라고 쓸 수 없다.

### ③ supervisor 만료 통지 (`src/bin/cysd/boot_supervisor.rs`)
- 발신 지점 = `notify_no_spawn`(선언 pane 에 `WriteReq::Inject` · cr 120ms = 제출까지) · 트리거 `decide()` 의 `expired`(INTENT_MAX_AGE_SECS=1800).
- 【관측】 결함: 성공 디스패치는 인텐트를 running 으로 남기고 해제 조건이 수명뿐 + `decide()` 에서 expired 검사가 running 대기보다 앞 → **정상 기동한 선언도 30분 뒤 「팀이 이 선언으로 뜨지 않았다」가 master 자리에 들어간다**(09:24 설치 → 09:59 통보와 부합).
- 수리: running 인 채 수명 초과 = `expired_running` → 통보 0(feed·pane 둘 다) · 스풀에서만 걷음. 진짜 무산 통보는 `[cys-supervisor · 기계 통지 · 사용자 할 일 없음] … master 할 일 1줄: 오너에게 묻지 말고 cys list 로 확인해 1줄 보고` 형식(화면 통보 약속을 담은 훅 문구·cys.rs 문구는 그대로 두었다).

### ④ 1.0.1 「Update 0」 (`ui/src/main.ts`)
- 사실 1줄: 1.0.1 은 **기동 1회 + 6시간 setInterval** 만 확인하고, 백그라운드 확인이 실패하면 배지를 건드리지 않아(`updateplan.ts` unknown) 이전 성공의 「0」이 남는다 — 서명키·엔드포인트·latest.json(windows-x86_64 서명 有)·버전 비교는 정상 【관측】. 그 기기가 1.0.2 발행(09-18) 뒤 어떤 확인에도 성공 못 했을 것 【추정】. 수동 Update 버튼은 오류를 보여 준다.
- 수리: 벽시계 6h(15분마다 확인) + 창 포커스·visibility 복귀 시 30분 문턱. tsc 0 오류.

### ⑤ 팩 디렉티브 (MASTER §5 · CSO §4 · WORKER §6) — 각 3줄
- MASTER: `[cys-감시]` 줄 = 데몬 감시 통지 → 도구로 확인 · 처리 · 1줄 보고 · 되묻지 않음.
- CSO·WORKER: 임무 0 이면 오너에게 질문 금지 → master 에 1줄 보고 후 대기.
- 삽입 위치는 전부 §2 뒤 → `test_event_inject` §2 줄 범위 상수 불변. CEO_TEMPLATE 재합성(--check GREEN · 83997B).

### ⑥ 승인 Feed pending 자동 만료 (`governance.rs expire_orphan_feed`)
- 닫는 조건: 이전 데몬 세대(created_at < 데몬 기동) · `--wait` 요청인데 발행자 pid 사망. 상태 `expired`(decision 없음 = deny 아님) · feed.jsonl last-wins 로 상태만 바뀜(삭제 0) · `feed.item.expired` 이벤트.
- 발사 후 망각(wait=false)은 pid 축으로 닫지 않는다(발행 CLI 가 곧 끝나는 게 정상). `FeedItem.wait` 신설(serde default=false).

## 증거
- cargo: lib 525 · cys 258 · cysd 994 통과 · 실패 0 (9937b657 트리 · 15:1x)
- pack: `test_bootv2_doc_contract` ALL PASS · `test_event_inject` ALL PASS · `gen_ceo_template.py --check` GREEN
- 뮤턴트 6/6 KILLED(M1 멱등 키 · M2 유휴 입력 필터 · M3 expired_running · M4 feed wait 축 · M5 reinject 시간당 상한 · M6 최소 간격) + lib 2건(❯ 앵커 · 접힌 붙여넣기)
- 격리 재현(격리 cysd `/tmp/cysiso.*` · 실제 claude 좌석 2 = haiku · CYS_IDLE_SECONDS=20):
  15:18:54 worker 입력줄에 [RESTORE] 미제출 → 15:19:19 `pane.idle`(24s) → 같은 틱 master 큐 1줄 → 11ms 뒤 배달 → 15:19:24 `watch_wakeup.submit verdict=submitted`(Return 재전송 없음) → master 가 worker 확인·제출 → 15:20:48 worker 입력줄 비고 처리 시작 · master 가 1줄 표로 보고.
  15:21:02 두 번째 미제출 → `watch_wakeup.suppressed reason=min_interval`(주입 0). 같은 이벤트 키 2회 → 주입 1회는 통합 시험(실 Daemon + check_idle)으로 증명.
  정리: 격리 cysd·claude 2·구독기 종료 · 잔존 0 확인 · /tmp 폴더 삭제.

## 미결 · 함정
- ⚠ `src/bin/cys.rs` 의 SubmitProbe 사본은 891(v112-restore)이 lib 호출로 바꾼다 — 병합 순서 restore → wake.
- 재현 중 관측: 격리 데몬의 내장 스케줄이 master 자리에 `[heartbeat] phoenix 세대 스냅샷 정기화` 를 넣었다 — 사람 대면 자리에 기계 산문이 들어가는 같은 계열(③과 같은 병) · 이번 범위 밖, 기록만.
- 재현 중 관측: master 가 턴 중이어도 Claude 입력 박스(❯)가 열려 있으면 큐 배달자가 배달한다(벤더 규약상 큐잉 → 다음 경계에서 처리). 「턴 중이면 대기 후 1회」는 Claude 쪽 큐잉으로 성립했다.
- B(hook-missing 무중복 억제 · 윈도 훅 명령 문자열 불일치)는 미수리 — 이 트레인 범위(이벤트→각성·reinject·supervisor) 밖으로 판단. 필요하면 별도 티켓.
- 윈도 기기 데이터 요청(② 원인 확정용): `phoenix-restore.log`, `lockloss.state`, `phoenix/breaker.json`, `cys status --json`(seat·agent_alive·daemon.started_at), `~/.cys/claude/settings.json` 훅 command.
