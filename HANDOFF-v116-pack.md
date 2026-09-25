# HANDOFF — TICKET=v116-pack (T-PACK 부서 자가치유 + R-B1 · agent_alive 퇴행)

- 좌석: worker-29@surface:1047 · worktree `~/axdev/.wt/cys-v116-pack` · 브랜치 `fix/v116-pack`(526325bf 에서)
- 표기: 【관측】 = 파일·로그·도구 출력으로 확인 · 【추정】 = 관측에서 끌어낸 해석 · 【미측정】 = 닿지 못함
- 재료: VM r4 = `~/axdev/master/reports/cysr-115-2026-09-22/vm-verify-r4/`(이하 `R4/`) · 시각 UTC

## 0-F. 최종(2026-09-24 13:1x · master#50e24753 ACCEPT)

- **판정**: ACCEPT — 코드 최종 = `5c8890d1`(526325bf 이후 28커밋 · 그 뒤 커밋은 이 문서(HANDOFF)만 바꾼다 · 로컬 · push 0). master 보고서 = `~/axdev/master/reports/cysr-116-plan/v116-pack/MASTER-REVERIFY-5c8890d1.md`(부모 `…-8f5b0878.md`).
- **재개 뒤 추가분**: ① phoenix 진행 중 묘비 존중 `fbdd3941` ③ 빈 좌석 회수 유예 600초 `3e8e683a` · 시험 cysd 누수 수리 `8f439373`(test_dept_name_guard CYS_* 격리·정리·잔존 0 단언) · 시크릿 스캔 걸림 수리 `5c8890d1`(시험 픽스처의 더미 사용자 이름 u → 스캐너 허용 이름 x · 문서의 실제 사용자 홈 경로 → `$HOME`).
- **D07c 정직 기록**: 5c8890d1 정본 게이트 1회차(master 러너 · 12:32~13:06 · 102스텝)에서 D07c(`cargo test --bin cysd -- --test-threads=1 --skip hwmon::`) rc=101 · 1042/2 — 두 실패(`surface_create_never_blocks_on_config_only_evidence` · `surface_create_privileged_gate_keeps_lock_order_no_deadlock`) 모두 `openpty failed … Device not configured`(ENXIO). 델타에 Rust 0 · 단독 재실행 ok · 전체 재실행 1044/0 · master 판단 = 호스트 PTY 고갈 환경 원인(같은 시각 다른 좌석 X-7 도 ENXIO). **1회차 원결과는 적색이었다**.
- **편입 때 주의점(병합은 1086 · master 지시 뒤 · 이 좌석은 병합 안 함)**:
  - 겹치는 파일(실측 `git diff --name-only`): T-USAGE 와 `src/bin/cysd/handlers.rs`·`main.rs` · T-NUM 과 `handlers.rs`·`state.rs`. 순서대로 `git merge-tree` 모의(usage+pack → +num) = 텍스트 충돌 0(13:1x · usage d24228db · num 17cc0a68 기준 — 그 뒤 브랜치가 움직이면 재확인).
  - handlers.rs: 내 변경 = `org.status` 팔 daemon 블록 `auto_restore` 1키 · T-USAGE = `usage.report` 팔 — 같은 `dispatch` 함수의 다른 match 팔(의미 충돌 없음 판단).
  - state.rs: 내 변경 = Daemon 필드 1 + 생성자 1줄(auto_restore 단계) — T-NUM ② 가 state.rs 를 크게 건드리므로 병합 뒤 cysd 빌드·`v116_auto_restore_*` 2시험 재확인.
  - CI 3파일(ci-branch·pack-release·release)의 스위트 목록 긴 줄에 새 4종을 덧붙였다 — 다른 티켓도 같은 줄에 덧붙이면 줄 단위 충돌이 난다(이번 모의에선 0). 해소 시 4종(`test_d1_4_orphan_reap` · `test_v116_rb1_formation` · `test_v116_auto_restore_status` · `test_v116_phoenix_midrun_tomb`)이 3레인 모두 남는지 확인.
  - `BUILTIN_JOBS_VERSION` 범프 없음(심박 잡 문자열 무변경 — §4).
  - `test_v116_auto_restore_status` 는 release.yml build 잡에서만 실제로 돈다(그 밖 레인 SKIP 초록).
  - 1.1.7 백로그 = §5(P4 · P5 · B 데몬 등록 시 묘비 해제 억제 · seat_state 뿌리 pid) · 목록 밖 시험 25개의 CYS_* 미격리 후보(grep 기반 · 미측정)는 master 판단 대기.

## 0. 파킹 델타(2026-09-24 08:5x · master#eee74a97 · 본부 cysr 1.0.2→1.1.5 업데이트 대기)

- **끝난 것**: R-B1 원인(§1) · agent_alive 판정(§2) · 설계·판정 A(§3·§4) · D1 #4 + B8 뿌리 방어선 · R-B1 P1·P1′(=D1 #5)·P2-b·P3 구현 · 이종 검증 **수렴**(Fable 2R ACCEPT · agy 2R dry — §7-1) · 디버깅 패스(회귀·cargo 직렬 1045/0·뮤턴트 13 중 12 + M12 재처리 KILLED — §7-2) · 성찰 2회차(§7-3) · VM 체크리스트(§6) · 1.1.7 백로그(§5) · 기억 증류 1건(project_cysd-seat-state-root-pid-blind).
- **남은 것(다음 할 일)**: ⑴ 【확인요청】 master 발신 — **✅ 발신 완료 2026-09-24T09:38:48+0900**(재개 master#3e7d8657 · HEAD 7a8aebac 대조 성립 · 좌석 surface:1058 · 재개 직후 시험 5종 재실행 rc=0) · master 판정 대기 ⑵ (가능 · 미착수) F6 · D3-f ⑶ 병합은 master(T-USAGE → T-PACK → T-NUM).
- **재개 판정 이행(master#f5ba25d5 · 09-24)**: ① R-B1 실사례 = A 채택 → `fbdd3941`(phoenix 스폰 직전 묘비 재조회 3곳 · tombstoned_mid_run · 집계 제외) ② B(데몬 등록 시 묘비 해제 억제)·「close-surface 없이 끝난 좌석=사고사」 = 1.1.7(§5) ③ m-1 = 유예 600초 → `3e8e683a`. 끝나면 【확인요청】 재발신.
- **진행 중이던 검증 라운드**: 없음(전부 종결). 파킹 직전 최종 회귀 스냅샷(HEAD · 08:56 종료 · 전부 rc=0): d1 #4+rb1+v115_dept 통합 OK · test_formation 43/43 · default_fleet 120/120 · dept_request OK · d1_dept_ready_probe OK · nowin_captured_spawns OK · import_guard 138/138.
- **재개 첫 행동**: `git -C ~/axdev/.wt/cys-v116-pack log --oneline 526325bf..HEAD` 로 최종 커밋 확인 → 이 문서 §4·§7 을 근거로 【확인요청】 작성·발신.
- **함정**: ① 이 좌석의 셸 env 에 라이브 `CYS_SOCKET`·`CYS_ROLE` 이 있다 — 시험·cargo 는 `env -u CYS_SOCKET -u CYS_ROLE CYS_NO_AUTOSTART=1` 로 ② cargo = `export PATH="$HOME/.cargo/bin:$PATH"` ③ `test_dbg_d3_d11_shared_profile_hooks` 는 /tmp 아래 사본에서 돌리면 위치 탓 적색 ④ cargo 병렬 실행은 선재 PoisonError flake(직렬 `--test-threads=1` 로 판정).

---

## 1. R-B1 원인 — 「재부팅 뒤 빈 셸이 master 역할을 먼저 쥔다」

### 1-1. 한 줄 요약

재부팅 뒤 앱이 미뤄 둔 행정부(dept-3) 데몬을 **본부 편성 심박(10분 잡)이 `cys status` 한 번으로 자동 기동**시키고,
그렇게 막 뜬 빈 데몬 위에서 **① 데몬 자신의 자동 복원(phoenix)** 과 **② 편성 ensure** 가 동시에 좌석을 세운다.
편성은 master 가 안 보이니 **폴더 지정 없이(=홈) 빈 셸 master 자리표**를 만들고, 데몬의 역할 등록은 「나중에 등록한 쪽이 이긴다」라서
복원이 세운 진짜 부서장(`--resume`)이 역할을 빼앗긴다. 이후 부서장 앞 배달은 그 빈 셸에 걸려 다음 데몬 재기동까지 풀리지 않는다.

### 1-2. 층별 원인(파일:행)

| 층 | 무엇이 일어났나 | 근거 |
|---|---|---|
| L1 방아쇠 | 본부 스케줄 잡 `formation-heartbeat`(10분)가 등재 부서마다 `javis_formation.py ensure --socket <부서>` 를 **`--cwd` 없이** 돈다. 잡 셸에는 `CYS_NO_AUTOSTART` 봉인이 없어, 죽어 있던 dept-3 소켓에 `cys status --json` 을 부르는 순간 **CLI 자동 기동이 dept-3 cysd 를 띄운다**(`cys-dept launch` 를 거치지 않음 → CEO 승격·계정격리 env(`CYS_ACCOUNT_DIR`)·스케줄 시드 없이 뜸) | 잡 정의 `src/bin/cysd/schedule.rs:211-219` · 잡 환경 `schedule.rs:1361-1371`(`apply_spawn_env` = PATH·HOME 만 · `src/lib.rs:1932`) · 자동 기동 `src/bin/cys.rs:2410-2463`(`connect`) · 편성의 첫 호출 `cysjavis-pack/bin/javis_formation.py:456-478`(`_live_roles` → `cys status --json`) · 봉인 핀 `src/lib.rs:6100-6130` 은 **Rust 스폰 지점만** 검사해 셸 잡을 못 본다 |
| L1 관측 | 【관측】 16:04:36 본부 이벤트 = 편성 완결 feed 2건(dept-1·dept-2 차례) → 6초 뒤 16:04:42 dept-3 `daemon.started` · `dept-launch-path.log` 에 dept-3 줄 **없음**(앱 대행 경로 아님) · dept-3 `cysd.log` 첫 줄에 launch 흔적 없음. 【추정 · 강】 6초 = launchd kickstart 시도(4초 폴링 · `cys.rs:2437-2447`) 뒤 형제 기동 | `R4/logs/axis1-reboot/x/col-reboot/evrec/cys.jsonl` · `cys/dept-launch-path.log` · `state-cys-dept-dept-3/cysd.log` |
| L2 자리표 | 편성 `ensure` 가 막 뜬 데몬의 로스터(비어 있음)를 보고 master 부터 세운다 → `_ensure_master_seat(socket, cwd=None)` → `cys new-surface --role master`(**`--cwd` 없음 = 데몬 기본 = 홈**) = claude 없는 빈 zsh 가 master 로 등록 | `javis_formation.py:1105-1117`(master 먼저) · `:821-846`(`--cwd` 는 인자가 있을 때만 · 심박은 cwd 를 안 줌) · 【관측】 `surface.created s9 {cwd:$HOME, role:master, caller_pid:7549}` +0.4s |
| L3 경합 | 같은 순간 데몬 자동 복원(phoenix · 데몬 기동 +0.3s)이 `launch-agent --restore` 로 행정부 폴더에 master(s10)·cso·worker 를 세운다. 데몬의 생성 관문(살아 있는 보유자 확인)은 PTY 스폰 **전**에 한 번 보고, 역할 등록은 스폰 **뒤**에 「나중 등록이 이김」으로 덮어쓴다 → 두 생성이 모두 관문을 통과하고 늦게 등록된 **s9(빈 셸)가 master 를 차지**. s10 에서 뜬 claude 의 claim-role 은 「보유자 생존」으로 거부(승계 미요청) | 관문 `src/bin/cysd/handlers.rs:3119-3190` · 등록 `src/bin/cysd/state.rs:3817-3842`(주석 「비-worker 는 기존 latest-wins」 · 관문↔등록 비원자는 `handlers.rs:3149-3152` 주석이 스스로 인정) · 거부 `handlers.rs:4897-4955` · 【관측】 `role.claim_denied s10 {current_holder:9}` + `role.takeover_cancelled 「보유자 생존(승계 미요청…)」` +1.2s |
| L4 worker 여분 | 편성이 cso 다음 worker 를 `javis_boot_node` 로 띄울 때, 자식 폴더 상속 `_master_seat_cwd` 가 **첫 master 좌석 = s9(홈)** 의 폴더를 물려준다 → 복원의 worker(s12 · +34.1s)보다 3초 늦게 `launch-agent --role worker --cwd $HOME`(s13 · +37.3s) → 데몬 dedup 이 `worker-2` 로 등록. topology 에 영속돼 **재부팅마다 +1**(2회차 = worker-2 2자리) | `javis_formation.py:481-499`(첫 master 의 cwd) · `:1117-1121` · `javis_boot_node.py:1480-1535`(row 없으면 launch) · `state.rs:3828-3839`(`dedup_worker_role`) · 【관측】 `surface.created s13 {cwd:$HOME, role:worker, caller_pid:8062}` → 목록 `worker-2` · 재부팅 2회차 s18·s19 worker-2 |
| L5 배달 보류 | `--to master` 는 역할 보유자 s9 로 간다. 배달기는 빈 좌석(`empty_seat`)에 타이핑하지 않고 보류(`queue.held`) — 보류분을 옮기는 것은 **좌석 승계(큐 이관)** 또는 **데몬 재기동 뒤 재홈**뿐이라, s9 가 역할을 쥔 채 살아 있는 동안 영구 보류 → 다음 재부팅의 `queue.rehomed` 에서야 배달(70·79분) | 재홈 `state.rs:3356-3372`(`rehome_restored_queue` · 재기동 경로 `governance.rs:5992`) · 【관측】 `queue.held {surface_ref:surface:9, reason:empty_seat}` 16:06:12 · 17:25:10·15 `queue.delivered` |
| L6 침묵 | 이중 보유를 알리는 알림 0 · phoenix 는 `manual_seats:[master]`(빈 좌석 잔존)를 로그에만 적음 · 편성은 심박 잡 `|| true` 로 결과가 묻힘 | `state-cys-dept-dept-3/phoenix-restore.log` 마지막 블록 `honesty_note` · `schedule.rs:216` 꼬리 `|| true` |

### 1-3. 1.1.2 대조군과의 차이 — 어디서 왔나

- 【관측】 1.1.2(c112 · 재부팅 1회차)도 **같은 자리표**가 있다: dept-3 `daemon.started 17:01:54` 와 같은 초에 `surface.created s4 {cwd:$HOME, role:master}` — 즉 L1·L2 는 **1.1.2 에도 있던 결함**이다.
- 【관측】 차이는 복원 시각이다: 1.1.2 dept-3 phoenix auto-restore epoch = 17:03:51(데몬 기동 **+117초** · 그때는 편성이 이미 cso·worker 를 세웠고 phoenix 대상 = master 만 · `per_role_outcome master=unverified` · 새 좌석 0) ↔ 1.1.5 = 16:04:42(**+0.3초** · 대상 cso·master·worker 셋 · 편성과 동시).
- 【추정】 ⇒ 1.1.5 에서 새로 보인 「이중 보유 + worker 여분」 = **같은 자리표 결함 위에 복원이 편성과 같은 순간 달리게 된 것**. 1.1.2→1.1.5 의 `cysd/main.rs`·`javis_phoenix.py`·`javis_formation.py` 코드 차이(`git diff v1.1.2 v1.1.5`)에서 복원 시작 시각을 바꾼 줄은 찾지 못했다 — 117초 지연의 원인(1.1.2 쪽 첫 복원 실행이 늦은 이유)은 【미측정】(1.1.2 dept-3 `cysd.log` 에 재시도 줄이 없어 판정 불가). **특정 커밋으로 좁히지 못했다**(정직 고지).
- 【추정】 같은 경합은 `cys-dept launch`(재부팅 뒤 앱 대행 경로)에도 있다 — launch 도 `formation_ensure_async` 를 `--cwd` 없이 띄운다(`cysjavis-pack/bin/cys-dept:121-139`·`:1330`). r4 에서 dept-1·dept-2 가 무사했던 것은 그 순간 자원 게이트가 hard(load 15)라 편성이 아무것도 안 세웠기 때문으로 보인다(`pending-resource`) — **부하가 낮은 재부팅이면 dept-1·2 에도 날 수 있다**.

---

## 2. agent_alive 퇴행(1-b) — 이 티켓의 코드 결함이 아니라 「설치본 1.0.2 + 좌석 띄우는 방식 변경」

(서브에이전트 조사 · 도구 출력 근거 · 코드·프로세스 조작 0)

- 【관측】 이 기계의 설치본 = `/Applications/cys.app` **1.0.2**(바이너리 mtime 09-18 · cysd pid 62178 · 09-19 18:17 기동 · `daemon.build_id=54c148cc…20260918`). 00:20↔02:50 사이 앱·데몬·팩(`~/.cys/pack/bin`) 변경 0 · 재부팅 0 · 절전 0.
- 【관측】 바뀐 것 = **master 가 워커를 띄우는 방식**: 09-23 22:33 까지 `cys launch-agent`(셸 아래 claude) → 23:02 부터 `cys new-surface --cmd "env -u NODE_OPTIONS … claude …"`(1021~1050 전부). 이 방식은 `zsh -lc` 가 claude 로 **교체(exec)** 되어 좌석의 뿌리 프로세스 = claude 자신이 된다(`cys list` pid = claude · 부모 = cysd). 00:20 성공한 1019 는 옛 방식 좌석이다.
- 【관측】 판정 사슬: master-send.sh:1106-1107 → agent-alive.sh(`agent_alive is True` 일 때만 살아 있음) · 1.0.2 데몬의 사망 감지는 뿌리 pid 를 증거에서 **뺀다**(54c148cc `governance.rs:3452-3477` `descendant_pids` 가 root 를 seen 처리) → 한 번도 못 본 좌석 = `agent_alive None` · 잠깐 본 좌석 = 사망 판정 `False` → 60초 뒤 **살아 있는 워커의 역할 회수**(cysd.log 「role 회수」 1026·1027·1028·1029·1031·1033·1036·1045·1048).
- 【관측】 수리는 이미 있다: `e330cbac`(09-21 · 「좌석 뿌리 argv 도 엄격 관측에 포함」) = v1.1.4·v1.1.5 조상 · 설치본 1.0.2 에는 없음(`merge-base --is-ancestor`).
- ⇒ 이 티켓 범위 판정: **1.1.6 코드 수리 대상 아님**(1.1.5 에 이미 수리됨). 운영 쪽 처방 = 워커를 `launch-agent`/`spawn-worker.sh` 로 띄우기(또는 설치본을 포크 경로로 1.1.x 로 올리기 · 앱 교체 = master 게이트).
- 🔴 **곁 발견(1.1.5 에도 남음 · 이 티켓 D1 #4 설계에 직결)**: 좌석 판정 `seat_state`(`src/bin/cysd/governance.rs:3184-3195`)도 **뿌리 pid 의 자손만** 센다. 뿌리가 claude 자신인 좌석(`new-surface --cmd claude`)은 claude 에게 자식 프로세스가 없는 순간 `seat=="empty"` 로 보인다 → 기존 B8 빈 좌석 회수(`javis_boot_node.py:1497-1525` reap-launch)와 이번 D1 #4 회수가 **산 claude 를 빈 셸로 오판할 경로**가 된다(제품 기본 경로 launch-agent 는 뿌리 = 셸이라 해당 없음 · 운영자·autopilot 검증자 `new-surface --cmd` 좌석이 해당). → 팩 쪽 5번째 방어선(뿌리 프로세스 = 셸 · `ps` 로 확인)을 D1 #4 와 B8 양쪽에 둔다(§3-2).

---

## 3. 설계 — 처방 후보 비교(구현 전 · master 판정 대기)

### 3-1. R-B1 처방 후보

| # | 무엇을 | 막는 층 | 파일(소유) | 장점 | 단점·위험 |
|---|---|---|---|---|---|
| P1 | 편성(심박·launch 꼬리)이 부르는 모든 `cys`·`boot_node` 자식에 `CYS_NO_AUTOSTART=1` — 심박이 부서 데몬을 **부작용으로** 되살리지 않는다 | L1 | `javis_formation.py`(T-PACK) | 계정격리 env 없이 뜨는 부서 데몬(`cys-dept:1284-1290` G3 경고가 말하는 「조용히 풀리는 격리」)이 사라진다 · 팩 한 파일 | **우연히 하던 자가치유가 없어진다** — r4 에서 행정부가 사람 손 없이 4분 뒤 켜진 것이 바로 이 부작용이었다 → P1 은 반드시 P1′ 와 같이 |
| P1′ | = **D1 #5 흡수**: 심박이 「등재 ∧ 묘비 아님 ∧ 데몬 무응답」 부서를 `cys-dept launch <이름>` 으로 **틱당 1부서 · 시도 원장(3회·쿨다운)** 안에서 되살리고 사람 말 알림 1줄 | L1 대체 | `javis_formation.py` + 심박 잡 명령(부서 이름 전달) `schedule.rs:216` | 되살림이 정식 경로(계정격리·CEO·스케줄 시드·편성)로 간다 · D1 #5(부서 데몬 크래시 무부활)도 함께 닫힘 | 심박 잡 문자열(데몬 파일) 1줄 변경 → `BUILTIN_JOBS_VERSION` 범프 필요 여부 확인 · 앱이 「다음에 켭니다」로 미룬 부서도 10분 안에 켜진다(현행 사실상 동작과 같음) |
| P2 | 편성이 **데몬 자동 복원이 끝날 때까지 좌석을 세우지 않는다**(대기 상한 뒤 보류 `partial:restoring` · 다음 틱 재판정) | L3 · L4 | 판정 신호 두 안 ↓ | 경합 자체를 없앤다 — master 이중 보유·worker-2 둘 다 | 새 부서 만들기 직후 팀이 늦게 설 수 있다(신호 정밀도에 달림) |
| P2-a | 신호 = 팩만: 데몬 나이(`org.status` `daemon.started_at` · 이미 있음) + phoenix `restore.lease` 비차단 탐침(`javis_phoenix.py:2017-2034`) | | `javis_formation.py` | 데몬 무접촉 | 복원 1차 실패 → 60초 재시도 대기(`cysd/main.rs:2043-2049`) 동안은 lease 가 비어 있어 **틈이 남는다** — 나이 문턱을 150초쯤으로 잡으면 막히지만 새 부서 팀이 그만큼 늦게 선다 |
| P2-b | 신호 = 데몬이 `org.status` `daemon.auto_restore` = `running`·`retry_wait`·`done`·`off` 를 노출 · 팩은 이것을 보고, 칸이 없는 옛 데몬이면 P2-a 로 폴백 | | `cysd/main.rs`(`loop_auto_restore` 상태 기록) · `state.rs`(Daemon 필드 1) · `handlers.rs`(키 1) + `javis_formation.py` | 정확 — 새 부서(복원 NOOP 즉시 `done`)는 지연 0 · 재시도 대기 틈도 닫힘 | **T-PACK 파일 목록 밖 데몬 3파일**(state.rs = §3-0 에서 N-1 단독 · 단 N-1 구현은 1파 뒤 단독 슬롯이라 동시 편집 없음) |
| P3 | 벨트: 편성 master 자리 `--cwd` 미지정이면 부서 레지스트리 폴더(`javis_boot_node.dept_registry_cwd` 재사용) · 자식 cwd 상속은 **에이전트가 앉은(비어 있지 않은) master 좌석** 우선 | L2 · L4 | `javis_formation.py` | 홈 폴더 자리표·홈 worker 가 원천 차단 | 단독으로는 경합(이중 보유)을 못 막는다 — 자리표가 행정부 폴더에 생길 뿐 |
| P4 | 데몬 특권 역할(master·cso) 등록을 관문과 원자화 — 등록 순간 다른 살아 있는 보유자가 있으면 덮어쓰지 않고 거부 | L3 일반 | `state.rs:3817-3842` · `handlers.rs:3119-3190` | 어떤 경합에서도 「나중 등록이 이김」이 사라진다 | 이미 PTY 를 띄운 뒤의 거부라 그 창을 닫는 롤백 설계가 필요(M~L) · worker-2 는 못 막음 · **1.1.7 권고** |
| P5 | 이미 깨진 상태 치유(업데이트 뒤 기존 사용자 topology 의 홈 빈 셸 master · worker-2 항목) | 잔재 | 데몬 역할 재지정 RPC 필요 | — | 빈 보유자를 닫아도 진짜 좌석의 역할은 그 창 안에서 다시 claim 해야 붙는다(외부에서 못 붙임) → 설계 필요 · **1.1.7 권고**(1.1.6 은 재발 차단까지) |

**권고 = P1 + P1′(D1 #5 흡수) + P2-b(P2-a 폴백 포함) + P3.** P4·P5 는 1.1.7.
- 근거: L1 을 막으면서 부활 경로를 정식 경로로 바꾸고(P1·P1′), 경합의 두 주체를 줄 세우며(P2), 홈 자리표를 원천 차단(P3)한다. 이 넷이면 r4 타임라인의 L1~L5 전부가 재현 불가다.
- 권고의 단점: 데몬 파일 3개(P2-b) + 심박 잡 1줄(P1′)을 건드린다 — T-PACK 이 팩 전용이라는 계획서 경계를 넘는다. 넘지 않으려면 P2-a(팩 전용)로 가되 새 부서 팀 지연(최대 ≈150초)이나 재시도 틈 중 하나를 감수해야 한다.
- 확신도: 원인 층 L2~L5 = 높음(이벤트·코드 일치) · L1(심박 자동 기동) = 중상(직접 로그 없음 — 시각·경로 정황 4개 일치) · 1.1.2↔1.1.5 차이의 커밋 = 미특정.

### 3-2. D1 #4 빈 셸 회수 규칙(A-2 = 유예 2분 · master 권고대로 진행 고지)

- **대상(모두 참일 때만)**: 닫히지 않음 ∧ **역할 없음** ∧ 에이전트 메타 있음(`agent` 칸 = launch-agent 로 에이전트가 앉았던 좌석 · 사용자가 연 평범한 창은 `agent=None` 이라 제외) ∧ **`seat == "empty"`(커널 사실 = 자손 프로세스 0)** ∧ `idle_secs ≥ 600`(★09-24 master#f5ba25d5 m-1 판정으로 120→600)(출력 0 = 사람 타이핑 에코도 0) ∧ `queue_depth == 0` ∧ 생성 폴더가 그 부서 폴더 안(레지스트리 cwd 접두 · 모르면 회수 안 함).
- **`agent_alive` 는 판정에 쓰지 않는다** — §2 의 퇴행(산 claude 좌석이 None/False 로 보임)이 그대로 오판 경로가 되기 때문. 살아 있음의 근거는 커널 사실 `seat` 하나다(산 claude = 자손 → `occupied`).
- **닫기 직전 재조회**: 새 `cys status --json` 으로 위 조건을 **같은 pid** 에 대해 다시 전부 확인(B8 의 `act2` 규율과 같음 · `javis_boot_node.py:1515-1521`) → `cys close-surface <ref> --reap`(묘비 없음).
- **알림(사람 말)**: 「<부서> 의 빈 창 1개를 정리했습니다 — 그 창의 claude 가 꺼진 뒤 2분 넘게 아무 일도 없었습니다. 그 자리의 일은 새 창이 이어받습니다.」 feed 1건 + 이벤트 `seat.orphan_reaped`.
- **어디서 도나**: 편성 ensure(심박 10분 · 부서마다)의 로스터 판정 **앞** — 역할이 이미 채워진 부서에서도 돈다(역할이 없을 때만 부르면 새 좌석이 선 뒤엔 영영 안 돈다). 유예 2분은 바닥값이고 실제 회수는 「사망 +2분 이후 첫 심박」.
- **4군 ④(산 좌석 닫힘 0) 방어선 5겹**: ① `seat=="empty"`(자손 0) ② 역할 없음(역할 가진 좌석은 절대 대상 아님 · 부서장·CSO·워커 현역 전부 제외) ③ 에이전트 메타 필수(사용자 평범한 창 제외) ④ 닫기 직전 같은 pid 재조회 ⑤ **뿌리 프로세스가 셸이고 `ps` 상 자식 0**(§2 곁 발견 — 뿌리가 claude 자신인 좌석은 `seat` 가 틀리므로 커널에 직접 묻는다 · `ps` 를 못 쓰는 OS(윈도) = 회수 안 함). 같은 ⑤를 기존 B8 reap-launch 에도 건다.
- 시험 틀(구현 전 선작성): 가짜 `cys` 가 status JSON 을 돌려주는 격리 시험 — 대상 1건 회수 · 각 조건 하나씩 거짓이면 회수 0(6건) · 재조회에서 좌석이 찼으면 회수 0 · `agent_alive=None/False` 인 **산 좌석(occupied)** 회수 0(퇴행 대조) · 뮤턴트(조건 하나씩 제거 → 시험이 잡는지).

### 3-3. 설계 성찰(9단계 · 설계 1회차 · 항목마다 적용 여부·이유 1줄)

| 단계 | 적용 | 결과(이 설계에서 바뀐 것) |
|---|---|---|
| 1 원칙 재성찰(품질·로컬·구독) | 적용 | 속도 대신 「재부팅 뒤 부서장 대화가 이어지고 역할 1자리」를 기준으로 삼음 → 새 부서 팀 지연을 감수하는 P2-a 단독안을 권고에서 내림 |
| 2 구체 설계안 | 적용 | §3-1 P1~P5 · §3-2 회수 규칙 |
| 3 의도·영향 범위·변경 계획 | 적용 | 의도 1문장 = 「막 뜬 부서 데몬에서 복원과 편성이 같은 자리를 두 번 세우지 않게 하고, claude 가 죽고 남은 빈 창을 2분 뒤 안전하게 치운다」 · 파급: formation(심박·launch 꼬리 둘 다 부름) · boot_node(B8) · 데몬 3파일(P2-b 채택 시) · 심박 잡 문자열(P1′) · 시험 = test_formation·boot_node self-test·신규 |
| 4 설계 결함 재조사 | 적용 — **결함 3건 발견·반영** | ⑴ P1 봉인 env(`CYS_NO_AUTOSTART=1`)가 P1′ 의 `cys-dept launch` → 새 cysd → **좌석 env 로 상속**되면 사용자 창의 `cys` 가 본부 데몬을 못 되살린다 → launch 호출만은 `env -u CYS_NO_AUTOSTART` 로 부른다 ⑵ `seat` 가 뿌리 pid 를 못 봄(§2 곁) → 회수 방어선 ⑤ 추가 ⑶ `ps` 없는 윈도에서 ⑤를 강제하면 B8 이 윈도에서 영영 안 돈다 → 윈도 = B8 현행 유지 · D1 #4 새 회수는 윈도에서 끔(근거 없으면 안 닫음) |
| 5 파이썬 치환(결정론) | 적용 | 회수 판정·대기 판정은 전부 순수 함수(입력 = status JSON · ps 출력) + self-test · LLM 판단 0 · 시간 문턱은 상수 1곳(`javis_budget` 우선) |
| 6 적대 A/B/C | 적용 | A(운영 실패): 복원이 60초 재시도 대기 중일 때 편성이 끼어드는 틈 → P2-b 가 `retry_wait` 로 막음(P2-a 는 못 막음 — 인정) · 사용자가 내린 부서를 심박이 되살리나 → `down` = 묘비+등재 삭제(`cys-dept:1658-1664`)라 심박 목록에 안 옴 = 방어됨 / B(단순성): P4 원자화는 이번엔 과잉 — 1.1.7 / C(유지보수): 「빈 셸 master」 제품 정책(create·allocate)과 회수의 경계를 주석에 명시(역할 있는 좌석은 절대 대상 아님) |
| 7 언어 원칙 | 비적용 | 이 저장소의 팩 코드·주석 관례가 한국어다(`javis_formation.py`·`javis_boot_node.py` 전부) — 외과적 변경 원칙(기존 스타일)이 우선 |
| 8 개선 필요성 최종 점검 | 적용 | P5(기존 깨진 상태 치유)는 필요하지만 역할 재지정 수단이 없어 1.1.6 에서 억지로 넣으면 산 좌석을 닫는 쪽으로 기울 위험 → 1.1.7 로 미룸이 맞다 |
| 9 저장 후 구현 | 대기 | 이 문서가 저장본 · 구현은 master 판정 뒤 |

---

## 4. 판정·구현 기록

- master#5c9ceb39(08:00): ⑴ R-B1 = **A 채택**(데몬 변경 최소·별도 커밋 · BUILTIN_JOBS_VERSION 코드 판정 · handlers.rs 다른 함수만) ⑵ D1 #4 규칙 확정 ⑶ B8 에도 뿌리 방어선 ⑷ 1-b 운영 처방은 master.

| 커밋 | 종류 | 내용 |
|---|---|---|
| efda1e7e | 팩 | D1 #4 `reap_orphan_seats`·`orphan_seat_verdict`·`root_is_bare_shell`·`seat_root_block` + B8 승계·회수 전 뿌리 확인(`javis_boot_node.py`) |
| bebab866 | 시험 | `test_d1_4_orphan_reap.py` 17 · `test_v115_dept.py` 뿌리 claude 픽스처 3 + 가짜 ps/pgrep |
| eb5f9e34 | 데몬 | `daemon.auto_restore` — main.rs(accept 전 running · 재시도 대기 retry_wait · 복원 스레드 끝 done) · state.rs 필드 1 · handlers.rs org.status daemon 블록 키 1 |
| 9258095e | 시험 | cargo `v116_auto_restore_phase_names_and_retry_rule_match_the_loop` · 격리 cysd `test_v116_auto_restore_status.py`(옵트아웃 = off · 관측 running→done) |
| 6f7ce28b | 팩 | 편성 P1 봉인 · P1′(=D1 #5) 되살림 · P2 복원 대기 · P3 cwd · D1 #4 매 틱 배선 · boot_node `--reap-orphans` |
| 2f7d045b | 시험 | `test_v116_rb1_formation.py` 22 · `test_formation.py` 하니스 새 접점 스텁(트립와이어 9z 가 실 cys 호출을 잡음 → 스텁) |
| c701c0bd | CI | 새 시험 3종 3레인 4목록 등재 |
| fbdd3941 | 팩·시험·CI | ★재개 ①(master#f5ba25d5): phoenix `current_tombstones` + 스폰 직전 재조회 3곳(resume 회차 · 빈 좌석 재사용 · fresh 강등) · 저널 `tombstoned_mid_run` · 결과 `tombstoned_mid_run_roles` · 완결성·판정 집계 제외 · `test_v116_phoenix_midrun_tomb`(C0+T1~T3 · 뮤턴트 4 KILLED · 수정 전 코드 T1~T3 적색 = 실사고 재현) · CI 3레인 등재 |
| 3e8e683a | 팩·시험 | ★재개 ③(m-1): 회수 유예 120→600초 · 알림 「10분」 · 경계 시험 599/600 · 뮤턴트 3 KILLED(상수 120 · 경계 `<=` · 문구 2분) |
| 8f439373 | 시험 | ★CSO 누수 실측(master#42e6b050): `test_dept_name_guard` 가 좌석 env 의 `CYS_CYSD_BIN`·`CYS_CYS_BIN`(1.1.5 데몬 주입 · cys-dept 1순위)을 지우지 않아 진짜 cysd 를 격리 HOME 에 띄우고 방치(09-24 18기) + 적색 8건 → 상속 CYS_* 전부 제거 · 케이스 정리(폴더를 쥔 프로세스 TERM→KILL + rmtree · addCleanup) · `DaemonLeakGuard` + `tearDownModule` 잔존 0 단언(lsof 전수 · 지워진 경로 포함) · 뮤턴트 3 KILLED |

- **BUILTIN_JOBS_VERSION 판정(코드)**: 범프 **불요**. 심박 잡(`schedule.rs:211-219`) 문자열을 바꾸지 않았다 — 부서명은 편성이 레지스트리(`~/.cys/depts.json`)에서 소켓으로 역산한다. 근거 = `schedule.rs:299-326`: 저장된 builtin 의 `_builtin_version` 이 코드 값보다 작을 때만 코드 정의로 갱신하고, 범프하면 builtin 전부가 교체돼 운영자 수기 편집이 소실된다(`:99-103` 주석).
- **handlers.rs 겹침**: 내 변경 = `org.status` 팔의 daemon 블록 1키(≈6853) · T-USAGE(D6-1-2 patch) = `usage.report` 팔(≈6527). 둘 다 거대 `dispatch` 함수 안의 **서로 다른 match 팔**이고 300줄 이상 떨어져 줄 단위 병합 충돌은 없다 — 다만 「같은 함수」라는 점은 정직 고지.
- schedule.rs 무변경 · state.rs = 필드 1 + 생성자 1줄.

## 5. 1.1.7 백로그(master 판정 ⑴)

- **P4** 데몬 특권 역할(master·cso) 등록 원자화 — 생성 관문(PTY 전)과 `roles.insert`(latest-wins · `state.rs:3827-3840`) 사이 창을 닫는다. 이미 띄운 PTY 롤백 설계 필요(M~L). 이번 판은 편성이 복원을 기다려 알려진 경합 주체만 줄 세웠다 — 다른 두 생성자(예: 사용자 `launch-agent` 와 복원)가 겹치면 여전히 latest-wins.
- **P5** 이미 깨진 상태 치유 — 업데이트 전 재부팅으로 topology 에 들어간 「홈 빈 셸 master」·「worker-2(홈)」 항목이 다음 재부팅 복원 때 다시 설 수 있다. 빈 보유자를 닫아도 진짜 좌석의 역할은 그 창 안에서 다시 claim 해야 붙어 외부 재지정 RPC 가 필요.
- **B(09-24 R-B1 실사례 · master#f5ba25d5)** 복원 경로가 띄운 좌석은 데몬 역할 등록 때 묘비를 지우지 않게(`state.rs:3853-3857` 해제 분기 · launch-agent 복원 표식) — 1.1.6 팩 재조회(fbdd3941)가 남긴 「재조회↔launch-agent 사이 수 초 창」을 닫는다. 「close-surface 없이 끝난 좌석 = 사고사로 부활」(우리 맥 7좌석) 원칙 재검토는 master 가 1.1.7 설계 티켓으로 별도 등재.
- (곁) 데몬 `seat_state`(`governance.rs:3184-3195`)가 뿌리 pid 를 안 본다 — 이번 판은 팩 방어선으로 막았고, 데몬 판정 자체(및 `seat_claimable_now` 를 쓰는 데몬 승계)는 그대로다.

## 6. VM 확인 체크리스트(다음 VM 좌석용 · R-B1 이 닫혔다고 말하려면)

1. 새 clone 설치 → 부서 3개(말로) → **부하가 낮은 상태에서** 재부팅 1회 · **부하가 높은 상태(부서 3 동시)** 재부팅 1회(자원 게이트로 미뤄진 부서가 생기게).
2. 각 부서 소켓 `cys status --json`(CYS_NO_AUTOSTART=1 · 부서 소켓 조회는 master 게이트) → 부서마다 master·cso·worker **역할별 1자리** · `role=worker-2` 0 · cwd 가 홈(`/Users/<u>`)인 좌석 0 · 전체 claude 수 = 12.
3. 부서 이벤트(evrec)에서 데몬 기동 뒤 `surface.created` 가 **복원 caller 하나에서만**(편성 caller 의 master·worker 생성 0) · `role.claim_denied` 중 `requested_surface` 가 claude 좌석인 것 0.
4. `daemon.auto_restore` 가 기동 직후 running → done 으로 바뀌는지 · 편성 상태파일(`~/.cys/state/formation/<소켓키>.json`)에 `partial:restoring` 이 한때 보여도 다음 틱 complete.
5. 미뤄진 부서(행정부 같은)가 켜진 경로: `dept-launch-path.log` 에 줄이 없고 부서 `cysd.log` 첫 줄 전에 `[cys-dept] … 가동 완료` 가 본부 편성 쪽 로그/알림(「부서 다시 켜기」 · 「다시 켰습니다」)으로 남는지 — 즉 **CLI 자동기동이 아니라 cys-dept launch 로** 켜졌는지.
6. 부서장 앞 `cys send --to master --queued`(ping) → 즉시 진짜 부서장 대화에 도착 · `queue.held empty_seat` 0.
7. 알림: 행정부를 되살렸다는 사람 말 1줄 · 이중 보유 0 이므로 이상 알림 0.
8. D1 #4: 부서 워커 claude `kill -9` → +61s 데드맨 역할 회수 → 다음 편성 심박(최대 10분)에 새 워커 → 사망 +10분(유예 600초) 이후 첫 심박에 옛 빈 셸 회수 + 「빈 창 정리」 알림 1 · **다른 좌석 닫힘 0**.
9. 재부팅 2회째에도 2·3·6 동일(여분 누적 0).
10. (★09-24 추가) R-B1 실사례: 부서 복원 진행 중(`daemon.auto_restore=running`)에 역할 좌석 하나를 `cys close-surface` → 그 역할이 같은 런에서 다시 서지 않음 · topology 묘비 유지 · phoenix 결과 `tombstoned_mid_run_roles` 에 그 역할 · completeness 가 그 역할 때문에 INCOMPLETE 아님.

## 7. 검증 · 디버깅 · 성찰 2회차(완료 전)

### 7-1. 이종 검증(수렴 = 서로 다른 검증자 dry)
| 라운드 | 검증자 | 판정 | 발견 → 처리 |
|---|---|---|---|
| 1R | agy(`~/.local/bin/agy` · 수정 전문) | ACCEPT · 발견 0 | 방어 8건 확인 |
| 1R | Fable 적대 서브에이전트(「산 좌석을 빈 셸로 오판해 닫는가」) | ACCEPT-WITH-FIXES | M-1 사용자 셸 · M-2 승계 뒤 회수 재확인 · M-3 걸린 복원 · M-4 윈도 묘비 · m-2 NFC/심링크 → **수정 64e869e2**(+ M-1 보강 SHELL=claude 불인정) · m-1·m-3·m-4·m-5 미수용(사유 §7-4) |
| 2R | Fable | ACCEPT | 5건 닫힘 확인 · 새 MINOR m-6(승계 중 exited 옛 좌석 잔존) → **수정 6cd9078f** · m-7(SHELL 경로 공백 = 보존 쪽 · 미수정) |
| 2R | agy(후속 수정 diff 전체 · m-6 포함) | ACCEPT · **발견 0(dry)** | — |

### 7-2. 정밀 디버깅 패스(서브에이전트 · 격리 복사본 · 뮤턴트)
- 회귀: CI 긴 루프 53종 중 52 통과 · 1 = `test_dbg_d3_d11_shared_profile_hooks` rc=2 — 복사본을 /private/tmp 아래 둔 **실행 위치 탓**(그 시험은 /tmp 팩 등록을 막는다) · `~/.cache` 로 뽑아 재실행 시 526325bf·c701c0bd 모두 통과. phoenix 16종 중 1 = `test_phoenix_w2_untomb_fullcycle` **기준판 526325bf 에서도 같은 실패(선재 · CI 루프 밖)**.
- cargo: `--bin cysd --test-threads=1` 1045 통과/0 실패 · `--lib` 534/0. 병렬 실행 44~51 실패 = ACL 시험 PoisonError 연쇄 · **기준판도 50 실패(선재 flake · 계획서 X-7)**.
- 기준판 적색: 새 시험 d1_4 17/17 · rb1 22/22 오류 · v115_dept b8 6 실패 · test_formation rc=1.
- 뮤턴트 13: KILLED 12 · M4a(첫 뿌리 확인만 제거 = 재조회가 같은 확인을 다시 해 보존 · 사유 표기만 다름 → 동치 뮤턴트) · **M12(retry_wait 기록 제거) 생존 → 회귀 핀 추가(2006deae) 뒤 KILLED**. m-6 뮤턴트 KILLED(직접 확인).
- flake: 격리 데몬 첫 응답 20초 창이 부하 중 2/9 실패 → 60초.
- 안전 고지: 서브에이전트의 첫 `cargo test --bin cysd` 1회가 셸의 라이브 `CYS_SOCKET`·`CYS_ROLE` 을 지우지 않은 채 실행됐다(이후 전부 제거 + `CYS_NO_AUTOSTART=1`) — cysd 시험은 자체 임시 소켓을 쓰나 확인은 못 함.
- 「어디까지 뒤졌나」: 팩 시험 53종 + phoenix 16 + seat_revival · cargo 1045+534 · 뮤턴트 13(+m-6 1 · M12 재) · 기준판 적색 4묶음 · 이종 리뷰 4회 · 격리 데몬 실측 ≥10회. 안 한 것: VM 재부팅(별도 티켓 · §6) · 윈도 실기 · F6·D3-f(시간은 있었으나 CTX 60% 매듭선 우선 — 미착수).

### 7-3. 성찰 2회차(완료 전)
| 단계 | 적용 | 한 줄 |
|---|---|---|
| 1 원칙 | 적용 | 판정 입력을 커널 사실(`ps`·`pgrep`)과 데몬 원장 단계로만 — LLM·추정 0 |
| 2·3 설계·파급 | 적용 | 파급 = boot_node(B8·D1 #4) · formation(심박·launch 꼬리) · 데몬 3파일 · CI 3레인 — 전부 커밋 표 §4 |
| 4 결함 재조사 | 적용 | 이종 검증이 찾은 M-1~M-4·m-6 은 설계 1회차가 못 본 것(사용자 셸 · 승계 뒤 창 · 무기한 대기 · 윈도) — 반영 |
| 5 결정론 | 적용 | 판정 전부 순수 함수 + 시험 · M12 가 보여 준 「판정 함수만 시험하고 기록 지점은 안 봄」 틈을 구동 시험으로 메움 |
| 6 적대 | 적용 | Fable 2R · agy 2R 수렴 |
| 7 언어 | 비적용 | 저장소 관례(한국어 주석) |
| 8 필요성 | 적용 | P4·P5·seat_state 데몬 수리 = 1.1.7(§5) · m-1 잔여 위험 명시(§7-4) |

### 7-4. 미수용·잔여 위험(정직)
- **m-1 → ✅ 완화(09-24 · 3e8e683a · 유예 600초)** — 아래는 원 기록. **m-1(잔여 위험 · 4군 ④ 의 유일한 열린 칸)**: 사람이 claude 를 끈 뒤 빈 프롬프트를 2분 넘게 **읽기만** 하면(출력 0 · 자식 0 · 역할 없음 · 에이전트 메타 있음) 다음 심박에 그 창이 닫히고 스크롤백이 사라진다. A-2 확정값(2분) · 「빈 창 정리」 알림 1줄로 짝. 완화안(기록): `live_cwd != cwd` 를 활동 신호로 보존 · 또는 유예를 심박 1틱(600s)으로.
- m-3 심박 600s 캡: 부서당 최악 ≈ 복원 대기 120 + 회수 60 → 3부서 ≈ 570s < 600 · 4부서부터 초과 가능(종전 boot_node 130s×역할 축도 이미 초과하던 선재 축).
- m-4 묘비 경로 = 기본 소켓 규약 하드코딩(비기본 본부 소켓이면 「없음」과 「모름」 융합 · 실방어 = down 의 등재 삭제).
- m-5 크래시루프 부서 = 10분당 1회 재기동(폭주 아님 · 알림 매번) → 1.1.7.
- m-7 SHELL 경로 공백 = 셸 불인정 = 보존(안전 방향).
- (master 검수 8f5b0878 기록) `test_v116_auto_restore_status` 는 ci-branch·pack-release·pack-artifacts 레인에서 `target/debug` cysd/cys 가 없어 **언제나 SKIP 초록**이다 — 실제로 도는 곳은 release.yml build 잡(빌드 뒤) 하나. 브랜치 CI 초록이 이 시험의 통과를 뜻하지 않는다.
- 편성 시도 원장에서 `seat_kept_*` 제외(M-1 부가안) = M-1 본수정으로 원인 소멸 → 보류.
