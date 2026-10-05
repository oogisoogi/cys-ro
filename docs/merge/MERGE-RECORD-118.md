# MERGE-RECORD-118 — 1.1.8 원작자 전체 편입(v0.14.43) 실측 기록 (정책 §0-2 6항)

> TICKET=cysr-118-merge-lead · 작업트리 `~/axdev/.wt/cys-118-merge` · 가지 `merge/v0.14.43` · push 0.
> 정책 §0-2 6항 = 편입마다 **소요 · 충돌 파일 수 · 리뷰 · CI · 회귀 시간**을 표로 남긴다(3회 P50/P90 의 첫 표본).
> 0.14.30·1.1.7 때 이 기록이 없어 「계수 없음」이 생겼다 — 이 문서가 1.1.8 의 계수다.

## 1. 기준

| 항목 | 값 | 출처 |
|---|---|---|
| 첫 부모(우리) | v1.1.7 = 75d2407b | `git for-each-ref refs/tags/v1.1.7` |
| 둘째 부모(원작자) | up/v0.14.43 = 55d3d2d6(태그 객체 77e23215) | `git for-each-ref refs/tags/up/` |
| 공통 조상 | bc01f43c(원작자 v0.14.30) | CONFLICT-MEASURE-118 |
| 편입 방식 | `git merge --no-ff --no-commit`(rebase·이력 재작성 0) | 브리프 §2-1 |
| 병합 커밋 | c08489e7(10-05 23:46) | git log |
| 핀 파일 | `UPSTREAM_BASE` = v0.14.43 | 저장소 루트 |
| 판 번호 | 1.1.7 유지(판번·PACK_MIN_BINARY = 통합 리드 TK-G) | 브리프 §2-5 |

## 2. 소요(실측 · 시계 = 커밋 시각·각 단계 date 기록)

| 단계 | 시작 → 끝 | 소요 | 병렬 | 비고 |
|---|---|---|---|---|
| 충돌 해소(76파일) | 21:56 → 23:46 | 53분(해소 작업) | 서브 7기 | 핵심 3파일: main.ts 24m47s · cys.rs ~28m · handlers.rs 19m45s · ui 나머지 6파일 4m30s · 팩 27파일 ~28m · CI 10파일 26m |
| 컴파일 수리 | 22:52:47 → 22:58:24 | 5분37초 | 서브 1 | 83 오류 → 0 |
| 첫 측정(Rust·ui·팩) | 22:50 → 23:4x | ~55분 | 순차 | 팩 1회 1,991초 |
| 수리 1차 | 23:47 → 01:06 | 1시간 19분 | 서브 4갈래 | ui 23분 · Rust B 45분 · 데몬 A 52분 · 팩 D 55분 |
| 수리 2차(이 좌석) | 01:06 → 02:2x | ≈1시간 20분 | 서브 5기(≤3 동시) | DS-1 서브 2기 2분49초·6분27초 · X18 대조 6분35초 · X18 ⓐ 압축·수용 10분2초 · ui 8·9 6분8초 · Rust 전체 1회 13분26초 · cysd 전체 1회 7분7초 · 팩 전체 1회 28분13초(01:45:47→02:14:01 · 서브 동시 부하) · 재실행 11개 103초 |

- **한 줄 계수(다음 편입 예측용)**: 원작자 비머지 ≈650커밋 · 충돌 76파일 편입 = 해소 53분(서브 7) + 컴파일 6분 + 수리 2회 ≈2.5시간(서브 3~4) + 측정 1회 ≈50분(Rust 13분 · ui 6초 · 팩 33분).

## 3. 충돌 파일

- 76파일(내용 65 · 추가/추가 11) · merge 기본 표기 덩어리 합 = `docs/merge/work/conf43.tsv` · zdiff3 재표기 시 main.ts 85 · handlers 97 · cys.rs 140.
- 파일별 판정(ours/theirs/synth)·근거 = `docs/merge/RESOLUTION-LEDGER-118.md` §1(76파일 전건 · 행 없는 파일 0) + 단계별 원장.
- 부모별 순효과: v1.1.7 → HEAD = RESOLUTION-LEDGER §0 · up/v0.14.43 → HEAD = 같은 곳.

## 4. 시험(CI 대리 — 로컬 격리 env · EVIDENCE-118 §8)

| 묶음 | 병합 직후(수리 전) | 수리 1차 뒤 | 수리 2차 뒤(현재) | 남은 적색의 분류 |
|---|---|---|---|---|
| Rust lib | 704 / 57 | 762 / 0 | **763 / 0**(무시 1 = 실물 번들 필요 · v1.1.7 부터) | — |
| Rust cys | 565 / 9 | 576 / 1 | **577 / 0** | — |
| Rust cysd | 2,391 / 53 | 2,445 / 5 | **2,449 / 1** | 부하 흔들림 1(원작자 return_absorb b_claimed… · 직전 전체 실행 초록 · 모듈 3회 초록) |
| ui tsc | 13 | 0 | **0** | — |
| ui bun | 2,684 / 147(skip 30) | 2,791 / 91 | **2,807 / 0 · 휴면 레인 81** | — (켠 레인 = 그 81 만 적색) |
| 팩 python(163) | 실패 42 | 대상 34 중 10 | **151 / 12** | 환경 8(원작자 v0.14.43·우리 v1.1.7 기준판 모두 적색) · 원작자 자체 4 |

### 4-1. 팩 전체 재측정(수리 2차 · 짧은 HOME)
- 전체 1회(짧은 HOME `/private/tmp/claude-501/s118/pk` · 시험마다 새 CYS_PACK_DIR · 01:45:47→02:14:01 · 1,693초): **163 중 적색 16**. 측정 도중 결정 반영으로 바뀐 시험 + 새 적색을 다시 돌림(11개 · 103초): core_inject · cso_directive_rev · pyseal_census · trust_seed **초록 전환**.
  - pyseal_census 적색 원인 = 작업 폴더(`docs/merge/work/` · git 제외)의 측정 결과 json 이 저장소 스캔에 걸림(작업물 오염 · 저장소 밖으로 옮긴 뒤 초록 · 깨끗한 체크아웃엔 없음). trust_seed = 전체 실행 부하 때만 적색(단독 초록).
- **남은 적색 12(최종)**:
  - 환경 8(두 기준판 모두 적색 · MEASURE-118 §4 그대로): run_bootstrap_health(시간 초과) · test_bootstrap_chain · test_dept_doctrine_v1 · test_dept_ticket_deficit_zero · test_dept_ticket_request · test_lane_isolation_v1 · test_preflight_phase1_checks · test_verify_gate.
  - 원작자 자체 4(원작자판도 적색·시간 초과): test_dept_create_progress(시간 초과 · X-WAIT 노브 핀) · test_dept_name_guard(X-J4 · reg_remove 인자) · test_dept_team_token(새 빌드로 휴면 스위치 끈/켠 두 레인 모두 22 중 16 · 원인 = 시험 CLI 가 시험용 HOME 의 데몬 소켓 미기동 `daemon_unreachable` — 스위치 무관) · test_session_start_hook 18e(봉인 자리 환경).
- 휴면-on 레인(기본 CI 미실행 · BACKLOG B1·B4): ui 81(`CYS_UI_DORMANT_LANE=1`) · teamtoken D8·D11(`CYS_ENABLE_TEAM_FLOW=1`) · session_start_hook 22·22b master(`CYS_DORMANT_LANE=1`) — 켠 레인 실측 = 그 항목들만 적색(정상).
- ⚠고아 디버그 데몬: 원작자 dept_create_progress·dept_team_token 시험이 데몬을 남긴다(전체 1회 16 · team_token 2회 8) — 전부 격리 HOME 소속 확인 뒤 정리(최종 0). CI 레인에서도 같은 누출 가능.

- 원작자 기준판(같은 격리 env): lib 702/0 · cys 464/0 · cysd 2,126/2 — 원작자 판도 사실상 초록(MEASURE-118 §2).
- 실 팩·실 설치본 쓰기 0: 이 좌석 시작(01:05) 뒤 `~/.cys/pack` 변경 = `state/evt_spool.jsonl`(라이브 훅) · `round/WORKER_TODO.md`(01:07 실 CLI `cys todo-path`) 2건뿐 — 시험·디버그 바이너리 쓰기 0. 고아 디버그 데몬 0(`pgrep -f cys-118-merge/target/debug/cysd`).

## 5. 리뷰

- judge(277) 결정표 대조 = report-judge-audit(일치 33 · 불일치 3 · judge 대기 9 · 보류 8) → master 결정 13 + 집행 조건 5 반영(DECISIONS-PENDING-118).
- 보안 경계 ⓓ = `master/reports/cysr-118-plan/REVIEW-D-118.md`.
- 수리 2차의 적대 라운드 = 0(이 티켓에선 master 발주만).

## 6. 회귀·결정 대기

- 결정: master#114e0c71(9건) · master#f0e81041(⑤ master 좌석) 전부 반영 — 남은 결정 대기 0. BACKLOG-118 B1~B4.
- 원작자 결함 행 = 팩 4(§4-1) · Rust 0. b3_status_polling 은 수리 1차 측정에서 원작자판도 적색이었으나 이번 전체 실행 2회 모두 초록 → **부하 흔들림으로 정정**(고정 결함 아님).
