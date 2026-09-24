# HANDOFF — 태그 레인 phoenix 거짓 적색 2종: ① test_phoenix_e2e_replacement ② test_phoenix_w2_untomb_fullcycle · TICKET=v116-phoenix-e2e

- 브리프 = `~/axdev/master/reports/v116-phoenix-e2e-2026-09-24/brief-v116-phoenix-e2e.md`(master#61752476 · 18:5x)
- 좌석 = worker-52(surface:1101) · 계정2(oogisoogi2) · 모델 claude-opus-5-5(세션 jsonl model 필드 287건 전부) · 착수 18:44 KST
- worktree `~/axdev/.wt/v116-phoenix-e2e` · 브랜치 `fix/v116-phoenix-e2e` ← 9f62f1a4(v116-flake-pty ACCEPT) · ⛔ git push · 태그 · dispatch · 릴리스 · 라이브 `~/.cys` = 0 · **제품 코드 변경 0**(`git diff 9f62f1a4.. -- src .github` 빈 출력)
- 측정 산출·도구(저장소 밖) = `~/axdev/.wt/v116-phoenix-e2e-runs/`
  - `run_phx.sh` / `run_phx2.sh`: 회차마다 격리 HOME·TMPDIR·빈 PACK(= release.yml 스텝의 시험별 새 mktemp 재현) · daemon.log·phoenix-restore.log 새 줄에 시각(epoch)을 붙이는 관측자(시험 무접촉) · run_phx2 = 소켓 경로 길이 가드(§9-1) 추가판
  - `analyze_phx.py`: 회차별 칸 결과 · 부트별 준비(listen−spawn) · 부트별 판정 줄(listen→`티켓=`/`죽은 역할 0`) · healthy-holder · 패닉
  - 주입: `slowwrap/python3`(데몬 auto-restore 인터프리터만 `PHX_SLOW_AUTORESTORE` 초 지연 = 부하 모사) · `crashwrap/python3`(auto-restore 가 판정 줄 없이 즉시 exit 1) · `mut/hangd`(소켓을 열지 않는 무응답 데몬)
  - 큐: `diag_queue.sh`(진단 교차) · `mut_queue.sh`(뮤턴트 · 매 변이 뒤 원복 diff 0 확인) · `load_queue.sh` · `final_queue.sh`
  - 측정 전용 detached worktree(편집 금지): `wt-adf50d44` · `wt-9f62f1a4` · `wt-7965705d` · `wt-e5f23c65` · `wt-4f278839`(최종) · `wt-mut`(뮤턴트 전용)
  - 표 원본(스크립트 출력 그대로): `diag-table.md` · `load-table.md` · agy 원문 `agy/agy-r{1,2}.md`

## 0. 한눈에

| 항목 | 결과 |
|---|---|
| ① e2e 원인 | 재기동마다 **고정 창**(ping 12초 + 판정 줄 20초 · ③ 8초) 안에 phoenix(auto-restore)가 판정 줄 `[phoenix] 티켓=…`을 써야 초록. 저부하 실측 판정 줄 = listen 뒤 **2.2~7.8초**(20회) → ③ 여유 최소 0.8초(load 24). 부하 30~64(1092 표)에서 넘침 = 거짓 적색 |
| ① 결정론 재현 | auto-restore 인터프리터 15초 지연 → 수리 전(9f62f1a4) **③ 적색 2/2**(판정 줄 17.6~18.5초 > 8초) · 20초 지연 → 수리 전 **①②③ 전부 적색 2/2** · 수리본 15초 2/2 · 20초 5/5 **초록** |
| ① 수리 | 재기동 1회(준비+판정 줄) **상한 90초** · 판정 줄(개행까지)이 나오면 즉시 반환 · 데몬 종료 / daemon.log 의 auto-restore 종료 줄(판정 줄 없이 끝남) / 데몬 미응답 = **상한 전 즉시 적색** · 칸별 준비·판정 초 stderr 기록 |
| ② w2 원인 | 빈 팩 첫 기동(11~35초)이 대기 12초를 넘으면 두 번째 cysd 가 startup lock 에 짐(healthy-holder) → 데몬 없이 진행 → `① roster=[]` |
| ② 판정 | **기점 9f62f1a4 에 이미 해소**(하네스 멱등 start_daemon + 120초 = 8f61e610 · v116-flake-pty ⑴). adf50d44 초록 **1/10** vs 9f62f1a4 **10/10**. master A/B(526325bf · 2efaf0a7)는 두 커밋 모두 8f61e610 미포함(`git merge-base --is-ancestor` 실측) = 수리 전 코드 적색 |
| ② 수리(잔여) | 데몬 미응답이면 「셋업: 격리 데몬 응답」 적색 후 즉시 중단(종전 = roster=[] 뒤 `close-surface(None)` TypeError · 데몬 없이 `cys new-surface` 가 추적 밖 cysd 를 autostart 할 수 있음 — c6 와 같은 처리) |
| 커밋 | 7965705d(e2e) · e5f23c65(w2) · 4f278839(적대 1R 방어 강화) · (문서) 이 HANDOFF |
| 뮤턴트 | **10/10 KILLED**(비제품 5 + 제품 5 · §5) + 최종 코드 재실행(§5-2) |
| 부하 반복 | e5f23c65: e2e 10/10 · w2 10/10(게이트 동시 · load 5.7~12.6) · 20초 지연 5/5 · **최종 4f278839: e2e 12/12 · w2 12/12(게이트 동시 · load 4.7~11.0) · 20초 지연 3/3 · 적색 0** |
| 정본 게이트 | 4f278839 · master 러너 v2 · 스냅샷 · **98스텝 rc≠0 0** · 기준 9f62f1a4 대비 신규 0 · 해소 3(= e2e_replacement ③) |
| 적대 검증 | agy 1R REJECT(REVISE 1 · 재현 없음 → 방어 수용) → 2R **ACCEPT** · Opus 적대 1R **ACCEPT**(기록만 5) → 2R **ACCEPT**(4f278839 재실행 포함) · 합격 시험(구현 안 본 새 Opus) e5f23c65 **S1~S8 PASS** → 4f278839 **S1~S8 PASS** |

## 1. 필요성(고치지 않으면 · 가려질 위험 차단)

| 항목 | 고치지 않으면 | 가려질 위험을 어떻게 막았나 |
|---|---|---|
| ① e2e | 태그 레인 `release.yml` phoenix 스텝(`set -euo pipefail` · continue-on-error 없음 · 시험 glob 전건)이 부하에 따라 적색 → build 잡 실패 → 릴리스 막힘. 브랜치 레인은 phoenix 를 안 돌려 **브랜치 초록 · 태그 첫 적색** 구조(1092 §1 과 동일) | 대기는 **상한**만 늘림(판정 줄 즉시 반환) · 판정 줄이 영영 없을 확정 상태(데몬 종료 · auto-restore 종료 줄 · skipped · 스레드 panic)는 상한을 안 기다리고 적색 · 판정 칸 본문·조건 불변 · 매 재기동 준비/판정 초를 stderr 에 남김 |
| ② w2 | (거짓 적색 자체는 기점에서 해소) 데몬이 끝내 응답하지 않는 날 TypeError 로 끝나 원인이 안 보이고, CI(CYS_NO_AUTOSTART 미설정)에선 `cys --socket <격리> new-surface` 가 격리 밖 cysd 를 autostart 할 수 있음 | 데몬 미응답 = 판정 1줄 적색 후 중단 · 좌석이 없으면 ① 적색 유지 후 중단 · new-surface rc/stderr 를 ① 판정에 |

## 2. 진단(규칙 ④ — 수정 전 코드로 실제 증상 재현)

### 2-1. 교차 40회(ABAB · 18:50~19:17 · `diag-table.md` 원문 발췌)

| 라벨 | 코드 | 통과 | load1 | gate_runner | 첫 기동 준비 | 판정 줄(listen→) | healthy-holder |
|---|---|---|---|---|---|---|---|
| e2e-adf | adf50d44 | **10/10** | 4.86~24.17 | 2~9 | (원본 = 12초 뒤 teardown 이 설치 중 데몬을 죽여 다음 기동이 이어받음 · 1.7~21.1초) | 2.3~7.8초 | 0 |
| e2e-9f6 | 9f62f1a4 | **10/10** | 5.41~24.20 | 2~11 | 15.8~30.9초 | 2.2~5.8초 | 0 |
| w2-adf | adf50d44 | **1/10** | 5.70~17.88 | 2~6 | 통과 1회 = 11.2초 / 적색 9회 = 12초 안 listen 없음 | — | **9/9 적색 전부 1** |
| w2-9f6 | 9f62f1a4 | **10/10** | 5.21~17.59 | 2~5 | 11.1~35.0초 | — | 0 |

- w2 판별: 첫 기동 ≤12초 → 초록 · 그 밖 → 적색(예외 0). 적색 9회 모두 `FAIL ① live 역할 desired 엔트리 등재 | roster=[]` 뒤 `close-surface(None)` TypeError(요약 줄 없음).
- e2e: 오늘 저부하에선 원본도 초록 — 부하 30+ 실측은 1092 §10 표(원본 0/3 · HEAD 2/3 · 정본 게이트 9f62f1a4 ③ 적색)가 정본. **자연 부하 30+ 재현 = 【미측정】**(인위 부하는 다른 워커 피해라 만들지 않음 · 대신 결정론 지연 주입 §2-2).
- ③ teardown 뒤 새 기동의 멱등 분기(브리프 질문): `teardown()` 3단계가 `_tracked_daemon=None` 으로 만들므로 `_boot_and_capture` 의 `start_daemon` 은 **언제나 새 데몬을 띄운다** = 교체 시뮬레이션(kill→재기동) 의도대로. 멱등 분기(추적 데몬 생존 시 대기)는 타지 않음(harness `start_daemon` · `teardown` 코드).
- 옛 판정 줄 오염 가능성 배제: auto-restore 자식은 setsid 없이 데몬 프로세스 그룹에 있음(main.rs `run_auto_restore_once`) → teardown killpg 로 함께 종료 · `_wipe_state` 가 로그를 지운 뒤라 늦은 쓰기는 지워진 inode 로 감.

### 2-2. 결정론 재현(지연 주입 · `load-table.md`)

| 라벨 | 코드 | 지연 | 결과 | 판정 줄 |
|---|---|---|---|---|
| o15 | 9f62f1a4(수리 전) | 15초 | **3/5 ×2 — ③ 적색 2/2** | ①② 17.6~18.0초(20초 창 안) · ③ 창 8초 초과 |
| s20-old | 9f62f1a4(수리 전) | 20초 | **1/5 ×2 — ①②③ 적색** | 창 밖 |
| fix-slow15 | 7965705d | 15초 | 6/6 ×2 | 17.8~18.6초 |
| s20-new | e5f23c65 | 20초 | 6/6 ×5 | 22.5~25.5초 |
| fix-slow150 | 7965705d | 150초 | **2/6 적색**(상한) | 각 재기동 90.0~90.1초에 포기 · 총 306.7초 |

## 3. 수리(커밋)

| 커밋 | 파일 | 내용 |
|---|---|---|
| 7965705d | test_phoenix_e2e_replacement.py | `STAGE_WAIT=90` · `_boot_and_capture(stage)` = teardown → daemon.log 크기(offset) → `start_daemon(wait=90)` → 판정 줄 폴링(0.25초) · 조기 적색 3경로(데몬 종료 · offset 뒤 auto-restore 종료 줄 · 미응답) · stderr `[e2e] ① 재기동 준비 Xs · 판정 줄 Ys (상한 90s)` · 첫 기동/재기동 미응답 = 「… 데몬 응답」 적색 후 즉시 중단(`_stage`·`_finish`) |
| e5f23c65 | test_phoenix_w2_untomb_fullcycle.py | 「셋업: 격리 데몬 응답」 판정 + 미응답 중단 · ① 판정 = 좌석 ref 필요 + new-surface rc/stderr · 좌석 없으면 중단 |
| 4f278839 | 두 파일 | 적대 1R 방어 강화: 판정 줄 **개행까지** 쓰였을 때만 반환(agy #1) · 종료 신호 + `auto-restore skipped` · `auto-restore 스레드 panic`(Opus #2) · 로그 읽기 `errors="replace"`(Opus #5) · w2 두 번째 ping 제거(start_daemon 은 ping 성공 때만 pid · Opus #3) |

- 최악 소요(Opus 적대 계산): e2e ≈ 126 + 3×105 ≈ 440초 < gate_runner 시험당 900초 · 실측 상한 초과 306.7~317.9초.
- 시험 판정 줄 수 변화: e2e 5 → 6(「셋업: 격리 데몬 응답(첫 기동)」) · w2 7 → 8(「셋업: 격리 데몬 응답」). compare_runs 는 스텝 rc 비교라 영향 없음.

## 4. 성찰(9단계 · 완료 전)

| 단계 | 적용 | 이유 1줄 |
|---|---|---|
| 1 의도 | 적용 | 거짓 적색 제거 · 진짜 적색 유지 — 뮤턴트 10/10 · 판정 칸 조건 불변 |
| 2 설계 | 적용 | 1092 c6 방식(상한·즉시 탈출·경과 초) 재사용 + e2e 전용 「판정 줄 없이 끝남」 탈출(제품 자체 종료 신호 daemon.log) |
| 3 파급 | 적용 | 시험 2파일만 · 하네스·c6·제품 무접촉 · 게이트 러너 스텝 ID 불변 |
| 4 결함 | 적용 | 잔여 위험 = 상한 90초 안의 **지연 회귀는 초록**(기록만 · §9) |
| 5 결정론 | 적용 | 모든 수치 = 스크립트 출력(analyze_phx · summary.tsv · compare_runs) |
| 6 적대 | 적용 | 제 측정 결함 2건을 스스로 적발·무효 처리(§9-1) |
| 7 운영자 관점 | 적용 | 적색 사유가 stderr `[e2e]` 줄과 판정 1줄로 바로 보임 |
| 8 필요성 | 적용 | 태그 레인 적색원 1개(e2e) 제거 · w2 는 기점 해소 판정 + 원인 가시화 |
| 9 저장 | 적용 | 이 파일 |

## 5. 뮤턴트

### 5-1. e5f23c65(수리본) — 10/10 KILLED

| # | 대상 | 변이 | 결과 |
|---|---|---|---|
| mE-die | e2e | 데몬 = /usr/bin/false(즉사) | 적색 3.7초 · 「셋업: 격리 데몬 응답(첫 기동)」 |
| mW-die | w2 | 〃 | 적색 2.9초 · 「셋업: 격리 데몬 응답」 · Traceback 0 (대조 oW-die = 수리 전 w2 → TypeError Traceback 1) |
| mE-hang | e2e | 무응답 데몬(sleep) | 적색 122.8초(첫 기동 상한 120초) |
| mW-hang | w2 | 〃 | 적색 136.3초 · Traceback 0 |
| mE-crash | e2e | auto-restore 즉시 exit 1(판정 줄 없음) | 2/6 적색 · 각 재기동 0.7~1.5초에 「판정 줄 없이 끝남」 |
| mW-pop | w2(디스크 phoenix) | 묘비 역할 roster pop(codex W2 BLOCKING 회귀) | 적색 2/2 · ③ 엔트리 보존 · ⑤ 부활 복귀 |
| mW-byp | w2 | 명시 --roles 묘비 필터 우회 | 적색 2/2 · ⑥ |
| mC-nore | c6 | close-surface --reap 호출 제거(reap 끊기) | 적색 2/2 · 「C6 exited 잔재 Reap 회수됨」 |
| mC-live | c6 | 라이브까지 회수(라이브 오회수) | 적색 2/2 · 「C6 라이브 오회수 0」 |
| mE-tgt | e2e(임베드 phoenix · 재빌드) | target_roles=[] | 적색 2/2 · ③ 타겟팅 |

- 원복: 매 변이 뒤 `git checkout` + `git diff --quiet` 확인 · 임베드 변이 뒤 재빌드 rc=0.
- 곁 관찰(기록만): mE-tgt 에서 ③ 둘째 칸 「대상역할= 라인 존재」는 초록(문자열 존재만 봄) — 첫 칸이 적색을 냄 · 기존 시험 설계.

### 5-2. 4f278839(최종) 재실행 — 이번 라운드가 건드린 경로
| # | 변이 | 결과 |
|---|---|---|
| fm-crash | auto-restore 즉시 exit 1 | e2e 2/6 적색 · 재기동마다 0.4~0.9초에 「판정 줄 없이 끝남」(개행 조건 뒤에도 조기 적색 유지) |
| fm-dieE / fm-dieW | 데몬 즉사 | 3.8초 / 3.7초 적색 · Traceback 0 |
| fm-hangW | 무응답 데몬 | w2 135.9초 적색 · Traceback 0(두 번째 ping 제거 뒤) |
| fs150 | auto-restore 150초 지연 | e2e 2/6 적색 · ①②③ 각 90.2~90.3초에 포기 · 총 307.3초 |

## 6. 부하 반복(최종 코드 · 정본 게이트 동시 · 두 스트림 병렬)
`final-table.md`(스크립트 출력) 요약 · 20:0x 전후 · 정본 게이트 4f278839 동시 · gate_runner 6~7(pgrep 수):

| 라벨 | 시험 | 회 | 결과 | load1 | 첫 기동 | 판정 줄(`[e2e]` stderr · 재기동 시작부터) |
|---|---|---|---|---|---|---|
| fl-e2e | e2e | 12 | **12/12 초록**(6/6) | 4.73~10.98 | 23.4~37.2초 | 2.5~6.6초 |
| fl-w2 | w2 | 12 | **12/12 초록**(8/8) | 4.73~9.85 | 21.6~37.4초 | — |
| fs20 | e2e · 20초 지연 | 3 | **3/3 초록** | 8.18~10.37 | — | 22초대 |

- 적색 0 · 잔존 경고(warn.log) 0 · SUN_LEN 0. 자연 부하는 낮았다(§9-6) — 고부하는 지연 주입으로 모사.

## 7. 정본 게이트(master-verify-snapshot · master 러너 v2)
- 대상 = 4f278839 · `master-verify-snapshot.sh` 스냅샷(라이브 트리 아님) · master 러너 `gate_runner.py`(v2 · 원본 무수정) · 19:30~20:18 · 결과 `~/msv-scratch/v116pe-w52/results/4f278839/summary.tsv` · 로그 `run-4f278839.out` 끝 = `완료 · 스텝 98 · rc≠0 0` · `[msv] 끝 … rc=0` · 추적 파일 변경 수=0.
- 기준 = 1092 9f62f1a4 결과(`~/msv-scratch/v116rv-w44/results/9f62f1a4` · rc≠0 = D07b.test_phoenix_e2e_replacement 1개).
- `compare_runs.py`(결과 `cmp-4f278839-vs-9f62f1a4.json`): **대상 실패 0 · 기준 실패 3 · 신규 0 · 해소 3**(D07b.test_phoenix_e2e_replacement 스텝 + ③ 두 칸).
- D07b 두 시험(게이트 부하 속): e2e_replacement rc=0 40.4초 · w2_untomb_fullcycle rc=0 32.2초 · c6_reap rc=0 24.9초 · B01 건강성 rc=0.
- 중단 1판(정직): e5f23c65 게이트는 적대 1R 수용 커밋(4f278839) 때문에 B01 도중 제가 중단(SIGTERM → msv 가 스냅샷 제거) · 부분 결과 `results/e5f23c65-STOPPED-superseded`(그때까지 rc≠0 0).

## 8. 이종·적대 검증(규칙 ①②③⑤⑥)

| 회 | 검증자 | 대상 | 판정 | 핵심 · 처리 |
|---|---|---|---|---|
| 1R | agy(타사) | e5f23c65 전문 | REJECT | REVISE #1 판정 줄 부분 읽기 → 「대상역할=」 잘림 거짓 적색 — **재현 없음**(phoenix `log()` = 한 줄 write+flush) → 규칙 ② 상 기록만이나 비용 0 방어로 **수용**(4f278839) · #2 w2 중복 ping → 수용 |
| 1R | Opus 적대(서브에이전트 · jsonl model=claude-opus-5-5 40건) | e5f23c65 | **ACCEPT** | 기록만 5: #1 지연 회귀가 초록 뒤(rv-slow60 = 60초 지연 6/6 초록) → §9 잔여 위험 · #2 skipped/panic 종료 신호 → 수용 · #3 w2 두 번째 ping → 수용 · #4 ① 로그 생성 칸이 데몬 헤더만으로 통과(기존) → 기록 · #5 strict UTF-8 → 수용. 자체 변이 rv-crash 적색 확인 |
| 2R | agy | e5f23c65..4f278839 | **ACCEPT** | 기록만 4(전부 수용 확인) |
| 2R | Opus 적대(같은 서브에이전트) | 4f278839 | **ACCEPT** | 재실행 rv2-ok 6/6 · rv2-crash 적색 · rv2-w2 8/8 · 반례 0 |
| ⑤ | 합격 시험(구현·diff 안 본 새 Opus · jsonl model=claude-opus-5-5 34건) | e5f23c65 | **S1~S8 PASS** | S2 대조 = 수리 전 20초 지연 1/5 적색 · S3 120초 지연 = 재기동마다 90초에 포기 · S4 즉사 31.3초 · S6 124.4/136.6초 · S8 잔존 0 |
| ⑤ | 〃(같은 서브에이전트 · 구현·diff 여전히 안 봄) | 4f278839 | **S1~S8 PASS** | S1 e2e 6/6×2 · w2 8/8×2 · S2 20초 22.6~23.4초 · 40초 42.8~44.2초 초록 · S3 120초 = 90.2초×3 포기 · S4 25.5초 · S5 4.3/3.1초 · S6 123.8/135.3초 · S8 잔존 0 · e5f23c65 대비 ±2초 이내 |

- 같은 모델(Opus) ACCEPT 는 독립 증거로 세지 않는다(규칙 ②) — 수렴 근거 = 타사 agy 2R ACCEPT(최종 delta) + 결정론 게이트 + 뮤턴트 + 풀리지 않은 반례 0 · master 독립 재실행 = 【대기】.
- 비가역 사안 아님(시험 코드 · 로컬 커밋) → 타사 1곳(agy). codex 미소환.

## 9. 정직 고지 · 잔여 위험

1. **측정 무효 1건(제 결함)**: 첫 재현 판(`INVALID-sunlen-repro-slow15-9f6`)은 라벨이 길어 격리 소켓 경로가 SUN_LEN(104바이트)을 넘어 데몬이 bind 패닉 — 지연이 아니라 경로 길이로 붉었다(0/5). 격리·재측정(o15) · 이후 `run_phx2.sh` 에 100바이트 가드 · analyze 에 panic 표시. 다른 판 SUN_LEN 0건 확인.
2. **러너 수정 중 실행 1건**: 진단 큐가 `run_phx.sh` 를 쓰는 중에 파일을 고쳐 가동 중이던 한 호출(w2-9f6 r1)의 꼬리(잔존 프로세스 점검)가 bash 구문 오류로 빠짐 — 그 회차 요약 줄은 이미 기록됨(7/7 PASS). 이후 러너 수정은 사본(run_phx2)으로만.
3. `다른 phoenix`(op) 열은 agy 가 도는 동안 부풀려짐(19:23~ 약 650) — agy 프롬프트 인자에 시험 소스가 들어가 `pgrep -fl` 이 여러 줄로 셈. 동시 시험 수 지표로 쓰지 말 것.
4. **잔여 위험(기록만 · 적대 Opus #1)**: 상한 90초 안의 제품 **지연 회귀**(예: auto-restore 개시 60초 지연)는 이제 초록 — 흔적은 stderr `[e2e] … 판정 줄 62.9s` 뿐. 부하와 구분할 판별자가 없어 판정하지 않음(1092 의 120초 상한과 같은 설계 선택).
5. 기존 약한 칸(기록만 · Opus #4 · mE-tgt 곁 관찰): ① 「로그 생성」은 데몬 헤더만으로 통과 · ③ 「대상역할= 라인 존재」는 문자열 존재만 — 옆 칸이 적색을 내 전체 초록은 안 됨. 범위 밖.
6. 자연 부하 30+ 조건 반복 【미측정】 — 측정 창 load 4.6~24.2. 부하 모사는 지연 주입(15·20·40·60·120·150초)으로 대신.
7. 윈도 실기 【미측정】 — 두 시험은 macOS release 레그 전용(`if: matrix.target == 'aarch64-apple-darwin'`) · 윈도 스텝 무접촉.

## 10. 곁 항목(수리 안 함)
- phoenix auto-restore 1회 소요(저부하 2~8초 · 부하 30+ 20초 이상)의 대부분은 debug 바이너리 `cys` 호출·python 기동(판정 전 `3중 identity` 까지 2~3.5초) — 제품 성능 관찰만(1.1.7 후보 판단은 master).
- ① 「로그 생성」·③ 「대상역할= 라인 존재」 칸 강화(§9-5).
- `test_phoenix_c6_reap`·하네스는 이번에 무접촉 — c6 는 1092 수리 그대로(뮤턴트 mC-nore·mC-live 적색 재확인).

## 11. 4군 점검
- ①폭주 큐: 해당 없음 — 재시도·큐 없음 · 폴링 0.25초 · 재기동당 상한 90초 · 첫 기동 120초 · 시험당 최악 ≈440초.
- ②무clear 100%+: 무관 — 좌석 기동·주입 무접촉.
- ③자가치유 전멸: 하네스가 덜 깐깐해지지 않음 — 판정 칸 조건 불변 · 데몬 즉사/무응답/phoenix 즉사/상한 초과 = 적색 · 제품 뮤턴트 5종(묘비 pop·필터 우회·reap 끊기·라이브 오회수·타겟팅 붕괴) 적색 유지.
- ④전 pane 사망 + 윈 무접촉: 제품 동작 무변경 · 윈도 스텝 무접촉 · 윈 실기 【미측정】.

## 12. 이어받기 — 남은 것과 판정법
1. 정본 게이트 4f278839 — 해소 판정: `~/msv-scratch/v116pe-w52/results/run-4f278839.out` 끝 `[msv] 끝 … rc=` + `python3 ~/axdev/master/reports/cysr-116-plan/reverify-tools/compare_runs.py ~/msv-scratch/v116pe-w52/results/4f278839 ~/msv-scratch/v116rv-w44/results/9f62f1a4 ~/msv-scratch/v116pe-w52/results/cmp-4f278839-vs-9f62f1a4.json`(대상 · 기준 · 결과) 신규 실패 0.
2. master 독립 재실행 — 해소 판정: master 결과의 D07b 두 시험 rc=0.
3. 편입 주의: T-PACK 새 phoenix 시험 4종이 편입되면 같은 하네스로 재실행(1092 §14 승계) · 이 티켓은 시험 2파일 + 이 문서만 더한다(기점 9f62f1a4 = v116-flake-pty 최종이라 그 HANDOFF·하네스 수리를 이미 포함) — 다른 티켓이 두 시험 파일을 만지지 않는 한 겹침 없음.
