# HANDOFF — v1.1.5 6차 트랙 DAEMON (D7·D9·D10) · TICKET=v115r2-daemon

작성 2026-09-23 · 브랜치 `fix/v115r2-daemon` (← 848b3f69 = 태그 v1.1.5) · 워커 surface:916
결함 정본 = `~/axdev/master/reports/cysr-115-2026-09-22/DEFECTS-2026-09-23.md`
증거 = 같은 폴더 `vm-verify/logs/{dept-s1,rA,rB}`

> 이 문서는 **상태를 복제하지 않는다** — 커밋·시험 결과는 아래 명령을 실행해서 읽는다.
> `git log --oneline 848b3f69..HEAD` · `cargo test --bin cysd d7_ d9_ d10_`

## 0. 무엇이 끝났나 (커밋)

| 항목 | 커밋 | 한 줄 |
|---|---|---|
| D10 | `4da83236` | 드레인 팬아웃 3곳이 **대상 소켓의** operator.token 을 `owner_token` 으로 싣는다 |
| D9 | `8adb8d0f` | `events` 를 autostart 금지 목록에 편입 + 닫힌 부서면 구독 종료 |
| D7⑵ | `acf4cdd5` | 역할 좌석의 미배달 큐를 폐기하지 않고 **주차·상속**(`queue.parked`/`queue.inherited`) |
| D7⑶ | `18caccd9` | `surface.creator` 신설 + `role.claim_denied` 에 `seat_blocked` 라벨 |

## 1. D7⑴ — 미완(이월) · **원인은 확정됐다**

### 실측 타임라인(교육부 `events-cys-dept-dept-1.jsonl` · epoch)
| 시각 | 사건 |
|---|---|
| 1790095927.99 | `surface.created` sid=1 **role=master · cmd=/bin/zsh · agent=null** · cwd 교육부 |
| 1790095932.52 | `queue.enqueued` sid=1 505B(각성문 · from=null) depth 1 |
| 1790096019.18 | `surface.created` sid=2 cso |
| 1790096042.17 | `surface.created` sid=3 worker |
| 1790096083.12 | `role.awakened` cso |
| 1790096087.88 | `queue.enqueued` sid=1 488B(**from=2** = CSO 보고) depth 2 |
| 1790096206.37 | **`queue.dropped` count=2 · 993B · reason=process_exited** → `surface.exited`(agent=null) |
| 1790096206.4x | `master.deadman` seat_state=**empty** · agent_alive=null · idle 289s · misses 3 |
| 1790096267.31 | `surface.closed` → `surface.reaped`(exited_grace_elapsed) |
| 1790096282.94 | `surface.created` sid=4 role=master · cmd=/bin/zsh |
| 1790096285.66 | `role.claimed` master(sid=4) |

⇒ **부서장 좌석 공백 = 357.67초**(sid=1 생성 → sid=4 role.claimed). sid=1 의 큐 2건은 **배달 0건**.

### 브리프 서술의 정정 2건
1. 「편성이 부서장을 안 띄움」 → **좌석은 생성됐다**(부서 allocate). 편성의 `_boot_node("master")` 가
   rc≠0 이라 `기동=cso,worker` 로 찍혔을 뿐이다(`javis_formation.ensure` 는 ok=rc==0 만 `booted` 에 넣는다).
2. 「hold-grace 로 보류」 → **아니다**. `empty_seat_action` 은 `fresh_shell = agent is None` 이면
   유예를 건너뛰고 `takeover` 를 돌려준다(SEAT_TAKEOVER_ROLES=master,cso). sid=1 은 agent=null 이므로
   act=**takeover** 였다.

### 남은 미지 1건 — 어느 분기로 rc≠0 이었나
`javis_boot_node` 의 takeover 경로에서 rc=1 로 끝나는 분기는 둘이다:
- `takeover_failed`(승계 후에도 role 이 옛 좌석에 남음 → 빈 셸 주입 0) ← **유력**
- `no_surface`(launch 후 3회 재조회에도 좌석 없음)

증거로 못 고른다: 부서 `cysd-cys-dept-dept-1.log` 26줄에 launch-agent 흔적 0 · 클라이언트 stderr 미보존 ·
이벤트 원장에 sid=1~4 사이 **새 surface 생성 0건**(= takeover 가 새 좌석을 만들지 못했다는 정황).

### 다음 라운드가 할 일 (D7⑶ 가 깔아 둔 것을 쓴다)
1. 재현 1회 후 `role.claim_denied` 의 **`seat_blocked`** 를 읽는다 → `not_requested` /
   `recheck_cancelled` / `seat_not_claimable` 중 하나로 분기가 **결정론으로** 고정된다.
2. `surface.creator` 의 `caller_pid`·`creator_surface` 로 sid=4 의 **승계 주체**를 읽는다
   (deadman 회생인지 formation 심박인지 — 이번엔 이 칸이 비어 있어 못 골랐다).
3. 그 뒤에야 수리 대상이 정해진다. ⛔그 전에 `javis_formation`·`javis_boot_node` 를 손대지 마라 —
   지금은 **어느 분기를 고칠지가 미정**이고, 추정으로 고치면 다음 라운드가 또 추정한다.

### 관련 미결(범위 밖 관측)
- `javis_formation.ensure` 의 `order = list(effective_required_roles())` 는 **집합**을 리스트로
  만든다 → 「master 먼저(입양 경로) → CSO → 나머지」라는 바로 위 주석의 순서가 **보장되지 않는다**.
  이번 사고의 원인이라는 증거는 없다(순서 무관하게 rc≠0 이었다). 1.1.6 후보.

## 2. 곁 관측 — 1.1.6 후보 (master 판정 2026-09-23: HANDOFF 에만)

1. **autostart launchd 위임이 소켓을 안 본다**: `launchd::should_delegate_autostart(loaded) = loaded`.
   격리·부서 소켓의 연결 실패가 본부 `launchctl kickstart` 를 쏜다. D9 프로브는 `launchctl` 껍데기로
   이 경로를 끊어 라이브 무접촉을 보장한다(프로브 doc 의 【모의】 축 1개).
2. **부서 `cysd.log` 의 `ABI producer self-verify critical (Drift) — falling back to legacy
   serialization` 반복**(브리프가 「원인 1줄만」 요구): 이벤트 직렬화의 ABI 자기검증이 실패해 매 발행마다
   레거시 경로로 내려앉는다. **부서 데몬에서만** 반복되는지는 미확인(본부 `cysd-cys.log` 대조 필요).
   ⛔원인 규명 미실시 — 「무엇이 Drift 인가」를 재는 계기(어느 필드/버전이 불일치)가 로그에 없다.
   수리 전 그 계기부터 만들어야 한다.
3. `handlers.rs::caller_is_owner` doc 과 `cysjavis-pack/acl.json` `_doc` 의
   「`grep -c 'owner_token|operator_token' src/bin/cys.rs` = 0」 주장은 **A1(v114-dept-fd)부터 이미
   거짓**이고 D10 이 더 넓혔다(현재 클라이언트 첨부 지점 = `inject_text` 4 + `inject_text_on` 2 +
   `RealVerifyIo::send_return` 1). 문서 정정 미실시(이 티켓 범위 밖 = 디렉티브·팩 문서).

## 3. 이 티켓이 만든 관측 표면(새 이벤트)

| 이벤트 | 언제 | 무엇을 답하나 |
|---|---|---|
| `queue.parked` | 역할 좌석이 자력 종료 + 큐 잔존 | 「그 지시는 유실인가 보류인가」 |
| `queue.inherited` | 같은 역할을 새 좌석이 받음 | 「후임이 무엇을 물려받았나」(+`waited_secs`) |
| `queue.dropped(parked_overflow/parked_expired)` | 상한·TTL 초과 | 「유계가 언제 발동했나」 |
| `surface.creator` | 모든 좌석 생성 | 「누가 만들었나」(pane 귀속·고아를 두 칸으로) |
| `role.claim_denied.seat_blocked` | 특권 역할 거절 | 「승계가 **왜** 안 됐나」 |

## 3-1. D7⑵ 보장 범위(정직) — 넓힌 것과 넓히지 않은 것

- ✅넓힌 것: **같은 데몬 안에서 역할 좌석이 교체되는 창**. 09-22 VM 사고의 창이 정확히 그것이다
  (357.7초 · 데몬 재기동 0회).
- ⛔넓히지 않은 것: **데몬 재기동 생존**. `parked_queues` 는 WAL 영속이 아니다
  (`persist_queue_state` 는 좌석의 `pending_queue` 만 싣는다). 회귀는 아니다 — 종전에는 좌석 종료
  시점에 이미 폐기됐으므로 재기동 생존이 애초에 0 이었다. 필요하면 별 과제다.
- ⛔바이트 상한의 보장은 「`max_bytes` 이하」가 아니라 **「상한 + 최대 1항목」**이다(마지막 한 항목을
  크기로 버리면 상한보다 큰 지시가 어떤 상한에서도 영구 전달 불가가 된다 · 시험 축 ④가 고정).
- ★**TTL 의 기준점 = 그 역할에 「처음」 주차된 시각**(agy r1 ⑵ 봉합). 병합은 시각을 갱신하지 않는다 —
  갱신하면 같은 역할에 주차가 반복될 때 만기가 무한히 밀려 유계 주장이 거짓이 된다.
  ⚠부수 효과를 정직하게: **늙어가는 배치에 새로 병합된 항목은 TTL 을 온전히 못 받는다.** 무한 연장보다
  이 편이 안전하다고 판단했다(사라질 때는 사유가 붙는다). 항목별 만기로 바꾸려면 `QueueEntry` 에 칸을
  더해야 하고 그것은 WAL 스키마 변경이다 — 하지 않았다.
- ⛔들어가는 순서는 「승계 이관분 → 주차분」이고 이는 호출 순서의 결과다. **전역 시간순 병합이 아니다**
  (큐 규약은 좌석 단위 FIFO 만 약속한다).
- ✅**worker-N 키 정합은 우연이 아니라 `dedup_worker_role` 의 죽은 슬롯 재사용 덕이다**(state.rs).
  주차 키는 죽은 좌석의 **실제 역할명**(`worker`·`worker-2`)이고, 후임 `create --role worker` 는 dedup 이
  「살아있는 점유가 아니면 그 번호를 재사용」하므로 같은 이름으로 돌아온다 ⇒ 상속이 성립한다.
  ⚠그래서 **dedup 의 죽은 슬롯 재사용 규칙을 바꾸면 이 상속이 조용히 끊긴다** — 그 함수를 손대는 사람은
  `inherit_parked_queue` 의 키 정합을 함께 확인해야 한다. (한때 「worker-N 이 어긋나 영원히 상속 안 됨」을
  결함으로 의심했으나 dedup 코드 실측으로 반증했다 — 추정으로 「경계」를 적지 않기 위해 기록한다.)

## 3-2. 이종 적대검증(agy) r1 = **BLOCK** → 봉합 완료

의뢰 = D7⑵ diff 범위 한정 + 감싸는 맥락 동봉 + 6축 지정(락순서·이중상속·worker-N·유계·무음유실·회귀).
정본 verdict = `~/.cys/pack/round/_reviews/D7-2_…-r1-reviewer1.json`(`{"verdict":"BLOCK",
"evidence":"src/bin/cysd/state.rs:341"}`).

**지적 2건 — 둘 다 실재했다. 내가 커밋 메시지에 적은 두 주장이 거짓이었다.**
| # | 지적 | 내 거짓 주장 | 봉합 |
|---|---|---|---|
| ⑴ | `map.retain(…)` 이 **다른 역할**의 만기 주차분을 무이벤트로 삭제 | 「초과·만기분은 조용히 사라지지 않고 사유를 달고 발행된다」 | 만기분을 **반환**해 호출부가 `queue.dropped(parked_expired)` 발행 · payload 에 role·from_surface additive |
| ⑵ | 병합 때 `parked_at = now` → TTL 무한 연장 | 「유계 = TTL 600s」 | 살아있는 배치의 **시각 보존** · 이미 만기인 배치는 병합하지 않고 만기로 내보냄 |

내 주석이 「만기 고지는 상속 시점」이라 적어 둔 것이 함정이었다 — `retain` 이 먼저 지우면 그 상속
시점이 **영영 오지 않는다**(`remove` 가 None). ★**「어디서 고지한다」를 주석에 적었다고 고지가 되는 것이
아니다** — 그 경로가 실제로 도달하는지를 재는 시험이 없었다(지금은 있다).

리뷰어가 **정상 경계로 판정한 것**(논쟁점): 락순서 AB-BA 위험 없음 · 이중 상속 차단됨(`remove` 소진) ·
worker-N 은 역할 종속 배달 규약상 정상 경계.

봉합 시험 2건 + 뮤턴트 3건(M-D7-12 ⑴ 되돌림 · 13 ⑵ 되돌림 · 14 role 칸 제거) 전부 KILLED.

## 4. 재현·검증 명령

```bash
cargo test --bin cysd d7_          # 6건(주차·상속·대조군·TTL·상한·창작자·거절라벨)
cargo test --bin cys d10_          # 2건 · cargo test --lib d9_  # 2건
python3 scripts/d9_events_no_daemon_revival.py --wait 12   # D9 라이브 3축(격리·라이브 무접촉)
```
뮤턴트 하네스는 스크래치패드에 있었다(저장소 미편입) — 목록·판정은 【확인요청】 표 참조.

### ⚠게이트 실행 시 주의 2건(실측으로 배운 것)
1. **뮤테이션 하네스와 전체 스위트를 같은 트리에서 동시에 돌리지 마라.** 이번에 `cargo test --bin
   cysd` 가 뮤턴트 적용 중인 소스를 컴파일해 **52 실패**를 냈다. 단독 재측정 = 1021 passed · 0 failed.
   「내 변경이 깨뜨렸다」로 읽기 전에 동시 실행을 먼저 배제하라.
2. **`cargo test`(src-tauri)는 이 환경에서 전처리 없이는 컴파일되지 않는다** — 번들 자원
   (`binaries/cys{,d}-<triple>` · `runtime/` · `resources/pack.tar.gz` · `resources/pack-manifest.json`)과
   `ui/dist` 가 있어야 한다. 전부 gitignore 이고 `scripts/bundle-prep.sh`·`ui/build.sh` 가 만든다.
   이번에는 디버그 바이너리 사본 + 빈 자리표 + `sh ui/build.sh` 로 세워 실측했다(162 passed · 0 failed).
   이 결손은 선재 환경 전제이고 이 티켓은 `src-tauri/` 를 **한 줄도 건드리지 않았다**.

## 5. 남은 규율 부기

- ⛔판번 bump 하지 않았다 · ⛔`git push` 하지 않았다(master 재승인 대기).
- 라이브 cysr·라이브 소켓 무접촉: D9 프로브는 `/tmp/d9-<pid>` + HOME 격리 + launchctl 껍데기.
  다른 워커의 격리 cysd(`/tmp/b1.sock` 등)와 라이브 앱 cysd 가 같은 기계에 산다 — 정리는 **정확
  소켓 일치**로만 했다(패턴 kill 금지).
