# HANDOFF — 시험 불안정 3건: ⑴ test_phoenix_c6_reap ⑵ 병렬 cysd openpty ENXIO(PTY 고갈) ⑶ 워크플로 mktemp 잔재 · TICKET=v116-flake-pty

- 브리프 = `~/axdev/master/briefs/2026-09-24-v116-flake-pty.md`(맨 아래 「master 결정(13:5x)」 우선) + master 결정 2건(14:2x ⑵=B 보강 3가지 · 14:3x Opus 5.5 규칙·러너 회신)
- 좌석 = worker-44(surface:1092) · 모델 claude-opus-5-5 · effort high(세션 jsonl 실측 6건) · 계정 = `CLAUDE_CONFIG_DIR=~/.cys/claude`(원 계정) · 착수 13:55 KST
- worktree `~/axdev/.wt/v116-flake-pty` · 브랜치 `fix/v116-flake-pty` ← adf50d44 · ⛔ git push · 태그 · dispatch · 쌓인 tmp.* 삭제 · 제품 코드 변경 = 0
- 반복 실행 산출·도구(저장소 밖) = `~/axdev/.wt/v116-flake-pty-runs/` — `run_c6.sh`(c6 반복 · 회차마다 격리 HOME/TMPDIR/PACK · daemon.log 에 시각 붙이는 관측자) · `analyze_c6.py`(회차별 통과·첫 데몬 listening 시각·데몬 수) · `boot_time.py`(cysd 단독 기동 시간) · `enxio_run.sh`(병렬 cysd 반복 · PTY 수 1초 표본) · `residue_ctl.py`(워크플로 run 블록 원문 실행 + mktemp 대리 기록으로 잔재 귀속) · `gate_runner_v116fp.py`(master 러너 사본 — §11) · 고정 worktree 3개 `wt-adf50d44` · `wt-526325bf` · `wt-fix`(57c7345a) — **측정은 편집하지 않는 detached worktree 로만**(§12 오염 1건 뒤 규칙)

## 0. 한눈에

| 항목 | 결과 |
|---|---|
| ⑴ 원인(대조군 뒤 명명) | 빈 CYS_PACK_DIR 로 뜨는 **첫 데몬의 팩 설치(478파일)** 가 하네스 대기 12초(+락 패배한 두 번째 기동의 재시도 ≈2초)를 넘기면 c6 가 데몬 없이 진행 → `list=` 빈 출력 적색. 두 번째 기동은 원인이 아니라 **우연한 유예**였다 |
| ⑴ 계수(원본 · 교차 20쌍) | adf50d44 **13/20** · 526325bf **13/20**(커밋 차이 0) · 통과 회차 listening 10.0~14.3초 / 실패 회차 14.7~18.4초 |
| ⑴ 대조군(팩 선설치) | adf **10/10** · 526 **10/10**(listening 0.0~0.3초 · 매 회차 두 번째 기동이 있었는데도) |
| ⑴ 수리본 계수 | 【채움 fix-il】 |
| ⑵ | 시험 전용 모듈 `pty_test_support.rs` · ENXIO 만 상한 재시도(1+2+4+8초) · 재시도 줄은 캡처 우회 · 상한 초과 = 「PTY 고갈(openpty ENXIO) — 결함 판정 보류」(원인 단정 안 함 — 적대 1R·2R) · 관측 실패 9건 경로 전부 감쌈 · 실제 고갈 대조군 = master 결정 B 로 **돌리지 않음**(주입형 단위시험·뮤턴트로 대체) |
| ⑶ 잔재 대조군 | 수리 전 **6** → 수리 후 **0** → trap 제거 뮤턴트 **7** · 루프 2회째 중간 실패(exit 7) → rc 7 보존 · 잔재 0 |
| 뮤턴트 | c6 2/2 · ⑵ 7/7 · ⑶ 1/1 = **10/10 KILLED**(§6) |
| 이종 검증 | 클로드 적대 1R REJECT → 2R REJECT → 3R 【채움】 / agy 1R REJECT(blocking = 제 회귀 적발) → 2R ACCEPT(낡은 설계 칭찬 = 걸러 냄) → 3R 【채움】 |
| 정본 게이트(최종 코드 ac4ad017 · 사본 러너) | 【채움】 · 기준 = master adf50d44 결과(`~/msv-scratch/v116rv/results/adf50d44` · 98스텝 중 rc≠0 = D07b c6 1개) |
| 제품 코드 | **무접촉**(`git diff adf50d44.. -- src` 는 시험 모듈·시험 코드·cfg(test) 선언 1줄뿐 — §3) |

## 1. 필요성(항목별 · 고치지 않으면 무엇이 붉어지나 · 가려질 위험을 어떻게 막았나)

| 항목 | 고치지 않으면 | 가려질 위험 차단 |
|---|---|---|
| ⑴ c6 | 태그 레인 `release.yml` phoenix 스텝(`set -euo pipefail` · continue-on-error 없음)이 부하 따라 적색 → build 잡 실패 → pack-artifacts·stamp 막힘. ci-branch 는 phoenix 를 안 돌려 **브랜치 초록 · 태그 첫 적색** 구조 | 대기는 **상한**만 늘림(준비되면 즉시 반환 · 데몬 사망은 즉시 탈출) · 준비 시간을 매 실행 stderr 에 남김 · 데몬 미응답이면 첫 판정에서 적색 후 즉시 중단 · 제품 reap 끊기/라이브 오회수 뮤턴트 적색 유지 |
| ⑵ ENXIO | 병렬 게이트가 겹치는 순간 cysd 시험이 `create surface` 패닉으로 적색 — 제품 단언 실패와 모양이 같아 판정자가 결함으로 오인 | ENXIO **만** 재시도(다른 errno 즉시 원문 실패 · 뮤턴트) · 상한에서 반드시 실패 · 재시도 흔적은 초록에서도 남김 · 원인을 단정하지 않는 문구 |
| ⑶ mktemp | 로컬 gate_runner 재실행마다 `/var/folders/…/T/tmp.*` 누적(443개 · ≈317MB 관측) | 스텝 결과 불변(trap 실패 불가형 · rc 보존 실측) · 호출마다 빈 팩 폴더라는 종전 의미 유지 |
| 뺀 것 | ⓐ 제품 코드(state.rs openpty · 팩 설치 fsync) · ⓑ windows-health · **release.yml 802-804(브리프 목록에 있었으나 실제 `if: windows-latest` 전용 — master 수용)** · ⓓ 쌓인 tmp.* 삭제(disk-cleanup-rest 티켓) · 형제 시험 파일(w2_untomb · seat_revival)은 하네스 공통 수리로 함께 해소(파일 무수정) | |

## 2. ⑴ 원인 계수(도구 출력 · `analyze_c6.py`)

cysd 단독 기동(`boot_time.py` · 격리 소켓/상태 · 빈 팩): 28.5 · 32.8 · 44.1초(부하 32~47) · 33.6 · 37.1초(부하 9~10) — **CPU 1.16~1.23초**(ps cputime) = 디스크 대기. 팩이 이미 있으면 0.77~0.78초(3회 중 2회 · 첫 회는 빈 팩 설치 35.7초). 파일마다 `sync_all`(write_atomic · pack.rs:2729) → macOS 에선 F_FULLFSYNC 라는 것은【추정】.

| 라벨 | 코드 | 조건 | 통과 | 부하1 | 두 번째 기동 | 통과 회차 listening | 실패 회차 listening |
|---|---|---|---|---|---|---|---|
| adf-bg r1~r16 | adf50d44 원본 | 배경(14:04~14:16) | **0/16** | 8~14 | 16/16 | — | 대부분 미관측(teardown 전에 못 엶) |
| 526-bg | 526325bf 원본 | 배경(14:17~14:25 · 조용한 창) | 20/20 | 7.1~10.6 | 20/20 | 9.6~12.5초 | — |
| adf-il | adf50d44 원본 | **교차(ABAB)** · 14:25~ · 뒤 절반 게이트 동시 | **13/20** | 7.3~24.6 | 20/20 | 10.0~14.3초 | 15.0~18.4초 |
| 526-il | 526325bf 원본 | 교차 · 같은 창 | **13/20** | 8.2~27.9 | 20/20 | 10.4~13.3초 | 14.7~17.9초 |
| ctl-warm-adf | adf50d44 원본 + 팩 선설치 | 대조군 | **10/10** | 13.0~25.7 | 10/10 | 0.0~0.2초 | — |
| ctl-warm-526 | 526325bf 원본 + 팩 선설치 | 대조군 | **10/10** | 12.5~30.1 | 10/10 | 0.0~0.3초 | — |
| fix-il | 수리본(wt-fix 57c7345a) | 교차 · 게이트 동시 | 【채움】 | | 0 | | |
| adf-il2 | adf50d44 원본 | 교차 · 같은 창 | 【채움】 | | | | |

판정: ① 커밋 차이 없음(교차 13/20 = 13/20) ② 통과/실패가 첫 데몬 listening 시각 한 축으로 갈림(경계 ≈14.5초 = 대기 12초 + 락 패배 두 번째 기동의 재시도 1.55초 + probe) ③ 팩 선설치 대조군 20/20 ⇒ 원인 = 첫 기동 팩 설치 시간. 두 번째 기동은 모든 회차(통과 포함)에 있었으므로 판별자 아님(브리프 추정 적중).
- 실패 증상 분류: 실패 전 회차 = daemon.log 에 첫 데몬 `lane:` 뒤 `listening` 없음(또는 test 진행 뒤 늦게) + 두 번째 기동 `healthy-holder, occurrence #1` · new-surface 두 번 빈 결과(수리 뒤 rc/stderr = `cannot connect to cysd … No such file or directory`로 보임).

## 3. 수리(커밋 · 시험/워크플로 분리)

| 커밋 | 항목 | 내용 |
|---|---|---|
| 8f61e610 | ⑴ | 하네스 `start_daemon` 멱등(추적 데몬이 살아 있으면 두 번째를 띄우지 않고 기다림 · 기다리다 죽으면 새로 띄움) · `FRESH_BOOT_WAIT=120` · `_fresh_harness` 준비 시간 stderr · c6 준비 판정·new-surface rc/stderr·고정 2초 → exited 폴링(상한 20초) |
| c1383398 | ⑵ | `pty_test_support.rs` + 도우미 5종·usage 3곳 감쌈 |
| 57c7345a · 5e99a295 | ⑶ | 워크플로 17곳 + report_gate 블록 log mktemp 1줄 |
| e896e17b | ⑵ | master 결정 B 보강(실제 오류 모양 주입 · 원문 글자 일치 핀 · 비ENXIO 무재시도 · 총량 15초) + 판별기 `os error 6`/`os error 60` 부분일치 구멍 봉합 |
| 5645cfa6 | ⑵⑴ | 적대 1R 수용(캡처 우회 · c6 미응답 즉시 중단 · 대기 초 표기 · macOS 한정) — **이 커밋은 c6 구문 오류 회귀를 넣었다**(§12) |
| 68a84e6d | ⑴ | c6 구문 오류 수리(agy 1R 적발) |
| ac4ad017 | ⑵ | 적대 2R 수용(원인 단정 문구 폐기 · lsof 폐기 · 로거 주입 · 기본 제외 탐침 재실행 · NOCAPTURE 제거) + main.rs 시험 모듈 선언 이동(§12) |
| (문서) | — | 이 HANDOFF |

⑶ 형태(블록마다 첫 `set -` 줄 뒤 6줄):
```
CYS_TMP="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/cys-pack.XXXXXX")"
trap 'rm -rf "${CYS_TMP:?}" 2>/dev/null || { chmod -R u+w "${CYS_TMP:?}" 2>/dev/null; rm -rf "${CYS_TMP:?}" || echo "::warning::임시 팩 폴더 정리 실패: ${CYS_TMP}"; }' EXIT
… CYS_PACK_DIR="$(mktemp -d "$CYS_TMP/p.XXXXXX")" …
```
- 실측: `set -e` 아래 trap 안 rm 실패는 초록 스텝을 rc=1 로 붉힌다 → 실패 불가형으로 설계 · true 0 / false 1 / exit 3 보존 · 읽기전용 폴더 정리.
- YAML 6파일 PyYAML 유효 · run 블록 의미 대조(삽입 6줄 + 치환 외 변화 0 · run 밖 키 동일) · 바뀐 잡 = macos-rust-pack(ci-branch 7블록) · release build(aarch64 조건 2블록) · pack-artifacts · pack-release pack-only(ubuntu — GNU mktemp 템플릿 동작 동일).

## 4. ⑵ ENXIO

- master 결정 B(14:2x): 실제 PTY 고갈 대조군 금지(기기 511 공유 · 박사님 창까지 맞음) → 주입형. 보강 ① 실제 오류 모양: `format!("openpty failed: {}", format!("failed to openpty: {:?}", io::Error::from_raw_os_error(libc::ENXIO)))`(state.rs `map_err` ∘ 벤더 portable-pty unix.rs:46 `bail!`) — 09-24 로그 원문과 **글자 일치 핀** ② EACCES·EMFILE·ENFILE·ETIMEDOUT = 재시도 0 · 대기 0 · 원문 그대로 ③ 총량 15초 뒤 반드시 실패(「무한 재시도」 뮤턴트 0.02초 안 적색).
- 관측 ENXIO 실패 9건 경로(X-7 7회째: watch_wake.rs:442 seat ×5 · usage.rs:2073 · usage.rs:2137 / D07c: handlers.rs:11741 make_surface · handlers.rs:18468 create_rpc 직접) = 전부 감쌈. 미포함(정직): 그 밖 직접 `create_surface` 시험 호출(governance·state·channels·boot_supervisor) — 거기 ENXIO 는 종전 원문 적색.
- 원인 단정 문구 폐기 이유(적대 2R 재현): PTY 는 셸 자식이 슬레이브를 쥐면 살아 있어 「다른 프로세스 보유」로 잡힘 → 제품이 자식을 못 거둬 새는 경우가 「환경」으로 보임 · 자기(핸들 ≈3/좌석) vs 전체(장치) 단위 불일치. ⇒ 문구 = 「PTY 고갈(openpty ENXIO) — 결함 판정 보류: 좌석 생성 자원 고갈로 멈췄다(제품 단언 실패 아님) · 원인(동시 병렬 시험 / 제품 PTY 누수)은 같은 시각 기기 PTY 수·동시 가동으로 가른다 · … · 기기 PTY n/max · 원문」. **브리프 예시 문구(「제품 결함 아님」)와 다르다 — 근거 없는 단정을 뺀 판단**.
- 부수효과(정직): 재시도 뒤 성공하면 실패한 시도가 surface id 를 1개씩 소비 · RPC 경로는 `surface.create_failed` 이벤트 1건씩 — 재시도 줄이 fd 2 에 남아 추적 가능.

병렬 기본 `cargo test --bin cysd -- --skip hwmon::`(격리 HOME · 짧은 TMPDIR · 게이트 동시 = 제 정본 게이트 가동 중):

| 라벨 | 코드 | 회 | 결과 | ENXIO | 재시도 줄 | 기기 PTY 최대 | 부하1 |
|---|---|---|---|---|---|---|---|
| fix-gate | 수리본(c1383398~e896e17b 시험 바이너리) | 5 | 3 초록 · 2 = `a_spawned_pty_child_does_not_inherit_the_lock_fd` 1건 | 0 | 0(당시는 캡처로 안 보이는 판 — 1R #1) | 353~355 | 15~24 |
| adf-gate | adf50d44 원본 | 5 | 3 초록 · 2 = 같은 시험 1건 | 0 | — | 356~359 | 12~17 |
| 단독(게이트 없음) | — | — | 【미측정】 · 시간 상한 | | | | |

- 판정: ENXIO 재현 0(10회) — 병렬 1회만으로 기기 PTY 353~359 → **두 병렬 실행이 겹치면 511 초과**라는 기제와 일치(추정 · 강). `a_spawned_pty_child…lock_fd` 는 원본에서도 병렬 2/5 → 기존 병렬 전용 불안정(워크플로는 직렬 · 이 티켓 무관 · §13 곁 항목).

## 5. ⑶ 잔재 대조군(`residue_ctl.py` · 블록 = ci-branch 「게이트 대장 회귀 + flake N=5」 원문)

| 회 | 트리 | mktemp 호출 | 끝난 뒤 남은 경로 | 그중 /var/folders |
|---|---|---|---|---|
| 수리 전 | wt-adf50d44 | 6 | **6** | 6 |
| 수리 후(57c7345a) | 편집 트리 | 7 | 1(같은 블록 `log="$(mktemp)"` 파일 → 5e99a295 로 포함) | 1 |
| 수리 후(5e99a295~) | 편집 트리 | 7 | **0** | 0 |
| 뮤턴트 trap 제거 | 편집 트리 | 7 | **7** | 1 |
| 경계: 루프 2회째 exit 7 | 편집 트리 | 4 | 0 · rc=7 보존 | 0 |

귀속 방법: PATH 앞 `mktemp` 대리가 **이 스텝이 만든 경로**만 기록 — 같은 사용자 임시 폴더에 다른 워커가 만드는 tmp.* 와 섞이지 않음. 대조군이 만든 잔재 3개(파일)는 귀속 확정분만 제가 지움(ⓓ 기존 잔재 무접촉).

## 6. 뮤턴트

| # | 대상 | 변이 | 결과 |
|---|---|---|---|
| MC1 | 제품 팩 `javis_phoenix.py` reap | close-surface --reap 호출 제거 | **KILLED** 2/2(「Reap 회수됨」 적색 · 수리 하네스 준비 19.5초) |
| MC2 | 같은 파일 | 라이브(exited=false)까지 회수 | **KILLED** 2/2(「라이브 오회수 0」 적색) |
| M1 | pty_test_support | 모든 오류 재시도 | KILLED |
| M2 | 〃 | 상한 제거 | KILLED(0.02초) |
| M3 | 〃 | 판별을 openpty 전체로 확대 | KILLED |
| M5 | 〃 | 재시도 줄 eprintln(캡처됨) | KILLED(자기 재실행 시험) |
| M6 | 〃 | 문구에 원인 단정(「(환경) — 제품 결함 아님」) | KILLED |
| M7 | 〃 | 재실행에서 RUST_TEST_NOCAPTURE 제거 삭제 | M5+NOCAPTURE=1 에서 헛초록 재현 → 제거 있으면 적색(필요성 실측) |
| (M4) | 폐기된 lsof 판별 | 항상 환경 | 5645cfa6 에서 KILLED — 설계 폐기로 소멸 |
| R1 | ⑶ 워크플로 | trap 제거 | KILLED(잔재 7) |
= c6 2 + ⑵ 7(M1·M2·M3·M5·M6·M7 + 폐기 전 M4) + ⑶ 1 = **10/10**. 뮤턴트는 전부 복원 확인(`git status` 깨끗 · wt-fix `git checkout`).

## 7. 성찰(9단계)

### 7-1. 설계(원인 계수 뒤 · 14:3x 기록)
정직 고지: 코드 초안은 원본 16회(0/16) + 단독 기동 실측 뒤 14:16 에 썼고 성찰 기록은 14:3x. 원문 = `v116-flake-pty-runs/reflect-design.md`.

| 단계 | ⑴ | ⑵ | ⑶ |
|---|---|---|---|
| 1 의도 | 거짓 적색 제거 · 진짜 적색 유지 | 환경/결함 문구 분리 1차 · 재시도 2차 | 잔재 제거 · 결과 불변 |
| 2 설계 | 멱등 + 대기 상한 + 준비 시간 기록 | cfg(test) 모듈 + 도우미 감쌈 | 루트 1 + 실패 불가 trap |
| 3 파급 | start_daemon 호출자 16 + 시험 4 · kill→재기동 지점 전부 `_tracked_daemon=None`/wait 확인 | 도우미 5 + usage 3 | ★master 러너 원문 assert 파급 발견 |
| 4 결함 | 120초가 기동 퇴행을 가릴 수 있음 → 준비 시간 기록(판정 안 함 = 잔여 위험) | ★`os error 6`⊂`os error 60` 구멍 봉합 | ★set -e 아래 trap rm 실패 = 적색 → 실패 불가형 · 윈도 스텝 제외 |
| 5 결정론 | 계수 = 스크립트 | 판정 = 단위시험·뮤턴트 | 잔재 = 대리 기록 귀속 |
| 6 적대 | ★두 번째 기동은 원인 아님(우연한 유예) | 실제 고갈 대조군 = 기기 피해 → master B | 기존 trap 0(있으면 스크립트가 거부) |
| 7 언어 | 저장소 관례(한국어 주석) 유지 | 〃 | 〃 |
| 8 필요성 | 태그 레인 | 병렬 겹침 | 잔재 누적 |
| 9 저장 | reflect-design.md | 〃 | 〃 |

### 7-2. 완료 전 【채움】

## 8. 이종 검증

| 회 | 검증자 | 판정 | 핵심 · 처리 |
|---|---|---|---|
| 1R | 클로드 적대(서브에이전트 · jsonl model=claude-opus-5-5 74건 — 'opus' 별칭으로 띄웠으나 5.5 로 풀림 실측 · 이후 model 생략) | REJECT | major: 재시도 줄이 libtest 캡처로 초록에서 사라짐 + 「제품 결함 아님」 근거 없음 → 수용 · minor 6(범위·부수효과·c6 미응답 계속 진행 시 autostart·대기 초·macOS 한정·할당 접두 mktemp 실패 무시) → #7 외 수용(#7 = 기존 패턴 · 기록만) |
| 1R | agy | REJECT | **blocking: 5645cfa6 c6 구문 오류 — 실측 확인(ast.parse 실패) → 68a84e6d** · minor: create_surface 오류형 불일치 → 반박(반환형 `Result<Arc<Surface>, String>` state.rs:3501 · 컴파일·시험 통과) |
| 2R | 클로드 적대(model 생략 = 상속) | REJECT | major 2(자식 보유 PTY 가 「다른 프로세스」로 잡혀 누수가 「환경」 · 핸들/장치 단위 불일치 — 재현) + minor 5 → 원인 단정 자체 폐기(ac4ad017) |
| 2R | agy | ACCEPT | 폐기 전 lsof 판별 설계를 칭찬 — 클로드 2R 재현과 충돌 → **립서비스로 걸러 냄**(규율 4-1) |
| 3R | 클로드 적대 | 【채움】 | |
| 3R | agy | 【채움】 | |

## 9. 완료 뒤 정밀 디버깅(경계)

| 경계 | 결과 |
|---|---|
| 데몬 즉사(`PHOENIX_HARNESS_CYSD=/usr/bin/false`) | 수리본 c6 = 3초(ac4ad017)·9초(57c7345a) 에 「격리 데몬 응답」 적색 · 잔존 0 — 120초 헛대기 없음(poll 탈출) |
| 데몬 무응답(`exec sleep 1000`) | 120.4초 뒤 적색 · 잔존 0(teardown killpg) |
| HOME 공유 두 c6 동시 | 둘 다 적색(서로 teardown) · 거짓 초록 0 · 잔존 0 — 기존 설계(HOME 당 HARN_DIR 1개) · 워크플로 직렬 · gate_runner 격리 HOME |
| 부하 40+ | 원본 스모크 부하 58 에서 3/5 적색 관측 · 수리본은 부하 ≤30 에서만 계수(【미측정: 40+】 — 인위 부하는 다른 워커 피해라 안 만듦) · 단독 기동 부하 47 에서 44초 → 상한 120초 안 |
| 재시도 상한 도달 | 단위시험(주입 대기) · 총량 15초 · 시도 5회 |
| PTY 가 시험 중간에 풀림 | 단위시험(ENXIO 2번 뒤 성공 → 시도 3 · 대기 1+2초) |
| trap × set -e | rc 0/1/3/7 보존 · rm 실패 = 경고 1줄 |
| 루프 스텝 중간 실패 | exit 7 보존 · 잔재 0 |
| 표적 뮤테이션 | §6 |
| 어디까지 뒤졌나 | c6 원본 76회(16+20+20+20) · 대조군 20 · 수리본 【채움】 · 뮤턴트 c6 4회 · 단독 기동 8회 · 병렬 cysd 10회 · 잔재 대조군 5회 · 경계 6종 |

## 10. 정본 게이트(최종 코드 · 수리 전후 같은 러너 계열)
【채움】

## 11. master 러너 호환(사본)
- 원본 `~/axdev/master/reports/cysr-116-plan/reverify-tools/gate_runner.py` 는 워크플로 원문의 `CYS_PACK_DIR="$(mktemp -d)"` 를 13곳에서 고정 문자열로 assert/합성 → ⑶ 편입 트리에서 A04 AssertionError(14:29 실측). **원본은 손대지 않음**(master 회신 = master 가 옛·새 형태 둘 다 받는 판으로 고침).
- 사본 = `~/axdev/.wt/v116-flake-pty-runs/gate_runner_v116fp.py` · 원본 대비 diff 요약: ① 고정 문자열 13곳을 `CYS_PACK_DIR="$(mktemp -d "$CYS_TMP/p.XXXXXX")"` 로 ② `ROOT_LINES`(루트·trap 두 줄 원문) 상수 + 분해 스텝(A04 · A05 · R08 3레인 · D07) 원문에 두 줄 실재 `assert_root` ③ 합성 스크립트에 `$CYS_TMP` 가 있고 정의가 없으면 두 줄 선두 부착(`run()`) ④ 스텝 ID·순서·타임아웃 불변 → compare_runs 호환.

## 12. 정직 고지(제 실수와 처리)
1. **측정 오염**: 첫 adf 20회를 편집 중 트리로 돌려 r17 부터 수리본 혼입(r17 = 하네스만 수리 · r18 = 둘 다) → 중단·격리(`c6/adf-bg-CONTAMINATED-r17plus`) · r1~r16 만 유효 · 이후 고정 worktree 만.
2. **반복기 결함 2건(⑵)**: 긴 TMPDIR(69바이트)로 deadman 시험 5건 거짓 실패 → 무효(`enxio/INVALID-longtmpdir…`) / 고아 정리 중 glob 삭제가 새 회차 TMPDIR 을 지움 → 무효(`INVALID2…`) · 잔존 프로세스 0 · PTY 40 복귀 실측.
3. **c6 구문 오류 회귀(5645cfa6)**: 패치 스크립트 삼중따옴표 안 `\n` 이 실제 줄바꿈으로 들어감 + 패치 뒤 c6 미실행 → agy 1R 적발 → 68a84e6d · 이후 파이썬 파일 수정마다 `ast.parse` + 실행.
4. **main.rs 선언 위치 회귀(c1383398~)**: 파일 머리 `#[cfg(test)] mod …` 가 건강성 검체 `_rs_prod`(첫 cfg(test) 이후 절단)를 깨 B01 H-TICK-ALIVE 적색(5e99a295 게이트 실측) → ac4ad017 에서 시험 구역으로 이동 · 단독 GREEN.
5. 5e99a295 정본 게이트는 A13 도중 중단(최종 코드로 대체 · 부분 결과 `…/5e99a295-STOPPED-superseded` · 그때까지 rc≠0 = B01 뿐 = 4번).
6. 수리본 c6 교차 계수는 wt-fix(57c7345a) — 이후 c6 변경(68a84e6d·5645cfa6)은 **미응답 실패 경로와 판정 문구**뿐(초록 경로 의미 동일) · HEAD c6 는 정상 6/6(14.0초)·즉사 경로 실측.

## 13. 곁 항목(수리 안 함)
- 【1.1.7 후보 · master TODO】 빈 팩 첫 기동 28~44초 소켓 불통(부하 시 · CPU 1.2초) — 업데이트 직후 첫 기동 체감.
- `handlers::tests::a_spawned_pty_child_does_not_inherit_the_lock_fd` 병렬 전용 불안정(원본 2/5 · 수리본 2/5) — 워크플로 직렬이라 게이트 무영향 · 시험 문구는 「프로덕션 락 누수」라 적으니 병렬에서 보면 오인 소지.
- `test_v116_auto_restore_status` 태그 레인에서만 실제 실행(브리프 이월 ⑶ · 기록만).
- release.yml 760 `GLOG="$(mktemp)"`(DMG 산출 뒤 릴리스 전용 · 로컬 게이트 비대상) · 적대 1R #7 할당 접두 mktemp 실패 무시(기존 패턴).
- 직접 `create_surface` 시험 호출 ≈90곳 미포함(§4).

## 14. 편입 주의
- T-PACK(e98c42c8) 워크플로 스위트 목록 줄과 이 티켓의 mktemp 줄이 4줄 안 인접 hunk(ci-branch 567/571 · pack-release 216/220 · release 463/467 · 1180/1184) → T-PACK 먼저 · 기계적 해소.
- T-SEAT · T-USAGE · T-NUM 이 handlers.rs·usage.rs·watch_wake.rs 시험 도우미를 만지면 겹침.
- T-PACK 새 phoenix 시험 4종은 편입 뒤 수리 하네스로 재실행.
- 편입 전 master 러너(§11) 교체 필수.

## 15. 4군 점검
- ①폭주 큐: 재시도 = ENXIO 한정 · 상한 4회 · 1+2+4+8초 · 매회 fd 2 1줄 · 상한 뒤 반드시 실패(뮤턴트 M2 적색) · 시험 전용.
- ②무clear 100%+: 무관 — 좌석 기동·주입 무접촉.
- ③자가치유 전멸: phoenix 하네스가 덜 깐깐해지지 않음 — 제품 reap 끊기(MC1)·라이브 오회수(MC2) 적색 유지 · 데몬 즉사/무응답 = 적색 · 전 phoenix 스위트 = 정본 게이트 D07b 【채움】.
- ④전 pane 사망: 제품 PTY 고갈 동작 무변경 · 시험은 그 상황을 「결함 판정 보류 · 자원 고갈」로 구별해 드러냄(원인 단정 안 함) · 윈 = windows-health·윈 전용 스텝 무접촉 · 윈 실기 【미측정】.
