# HANDOFF — TICKET=win-dept-chat-inject-timeout (1.1.11 · 2026-10-29 · worker-2)

브랜치 `fix/1111-dept-chat-timeout` (기점 origin/int/1111 fec48a8a) · push·병합·빌드 = master 게이트(미실행).

## 1. 증거 (관측)
| 출처 | 내용 |
|---|---|
| `~/axdev/master/help-cases/fleet/2026-10-28/5484b2ec…-signal.json` | `hook.dept-chat-inject` × `hook.rc124` 1건 (2026-10-28T01:28:17Z) · `hook.inject-background` × `hook.rc124` 1건 (01:48:29Z) · source=master · windows-11 · 1.1.10 |
| `…/2026-10-29/5484b2ec…-signal.json` | `hook.dept-chat-inject` × `hook.rc124` 1건 (2026-10-29T00:12:03Z) |
| `…-daily.json` | hook_rc_nonzero 1(10-28) · 5(10-29) · depts active 0 · tombstones 0 · 10-29 좌석=master 1 |
| `git diff v1.1.10 HEAD` (훅·_lib·role-bootstrap·javis_dept_request) | 차이 0 — 윈 설치본 = int/1111 과 같은 코드 |

⚠ 10-29 hook_rc_nonzero 5 중 신호로 이름이 남은 것은 1건뿐이다 — 나머지 4건의 훅 이름·rc 는 이 자료로 알 수 없다(그 기계의 `%USERPROFILE%\.cys\state\hook-errors.log` 에 있다).

## 2. 훅 정체 (코드 판독)
- `cysjavis-pack/hooks/dept-chat-inject.sh` — UserPromptSubmit · master 좌석만 · 하네스 선언 timeout 5초(`javis_preflight.py` HOOK_TIMEOUT_S).
- 셸 선거름(외부 프로세스 0): `.hook-wake` 없고 부서 낱말도 없으면 끝. 통과하면
  `cys_timeout_run 4 "$CYS_PY" javis_dept_request.py hook-prompt` (`_lib.sh` 데드라인 실행기: GNU timeout → gtimeout → `$CYS_PY -c` 시계 · 초과 = rc 124).
- rc≠0 이면 `cys_hook_fail` → `hook-errors.log` 1줄 + 상담소 신호(`hook.dept-chat-inject` / `hook.rc124`) — 위 증거가 이 경로다.
- hook-prompt 본체: 표준 모듈만 import · 요청 폴더 나열 · 작은 JSON 읽기/쓰기(fsync). 열린 제안이 있을 때만 `javis_mission.machine_origin`(배달 원장 대조). 잠금·하위 프로세스 없음.
- 맥 실측: hook-prompt 1회 **0.04초**(python 3.14 · 3회 동일) · 131KB 원본 compile 0.011초 · 해석기 기동 0.01초.

## 3. 원인 — 관측 / 추정 구분
- **관측**: rc 124 = 안쪽 4초 상한이 터졌다(`cys_timeout_run` 계약 · 124 는 타임아웃 전용).
- **관측(맥 재현)**: 해석기 기동이 5초 걸리면 수리 전 코드에서 rc124 + 안내 누락이 그대로 난다(시험 축 A 수리 전 RED).
- **관측**: 같은 파이썬 주입 꼴(stdin 파이프)인 `directive-event-inject`(모든 Bash 앞 · 상한 5초)는 신호에 없다 → 「파이프 EOF 미도달로 늘 멈춘다」 같은 **체계적 행**은 약하게 기각(그 훅이 그 기계에서 실제로 도는지는 미확인).
- **추정(실기 미측정)**: 윈에서 해석기 기동이 간헐적으로 4초를 넘었다 — 근거: 본체 일은 맥에서 0.04초인데 100배 느려야 터진다 · 같은 턴의 role-bootstrap 이 파이썬을 여러 번 동시에 띄운다(hook-triage 8초·record·machine-origin) · 형제 `inject-background`(SessionStart · 동시 기동 최다 시점)도 같은 rc124 를 냈다. 후보 요인 = 냉시작·Defender 실시간 검사·`py` 런처 2단 기동·동시 기동 경합. 어느 것인지는 미확정.
- **영향(코드 판독)**: 터진 턴은 ① 부서 절차 안내 ② 아직 전하지 않은 부서 소식 ③ 카드 뒤 사람 답 기록(human_ack) 이 빠진다. ③이 빠지면 confirm 이 「no-human-answer」로 되묻는다 — 사용자 체감 = 「네」라고 했는데 또 묻는다.

## 4. 수리 (최소)
| 파일 | 변경 |
|---|---|
| `cysjavis-pack/hooks/dept-chat-inject.sh` | 안쪽 상한 `cys_timeout_run 4` → `8` (같은 이벤트 role-bootstrap hook-triage 와 같은 값) |
| `cysjavis-pack/bin/javis_preflight.py` | HOOK_TIMEOUT_S `("dept-chat-inject.sh","UserPromptSubmit")` 5 → 10 (안쪽 < 바깥 — 바깥이 먼저 자르면 rc 기록도 못 남는다) |
| `cysjavis-pack/bin/tests/test_dept_chat_inject_timeout.py` | 신규 시험 3축 |

- 기존 설치: preflight 판정은 선언을 **하한**으로 본다(`hook_timeout_satisfied` · 5 < 10 = 불충족) → `--fix` 가 `max(cur, 10)` 로 올린다(javis_preflight.py `_event_hook_registered`/등록부 코드 판독 — 이 훅 특정 시험은 안 했다).
- 대가: 해석기가 느린 턴에 사람 프롬프트가 최대 8초(종전 4초) 기다린다. 정상 턴은 그대로(맥 0.04초).

## 5. 시험 (맥 · 이 브랜치)
| 시험 | 수리 전 | 수리 후 |
|---|---|---|
| A 기동 5초 해석기 → 안내 나옴 · rc124 0 | **FAIL** (rc=124 기록 · 윈 증상 재현) | ok |
| B 멈춘 해석기 → 안쪽 상한에서 끊김 · rc124 기록 | ok | ok |
| C 안쪽 상한 ≥ 8 ∧ < 하네스 선언 | FAIL (4) | ok |
| 뮤턴트: 선언만 5로 되돌림(안쪽 8) | — | C **FAIL** (잡힘) |
| test_dept_request.py | — | 112 OK |
| test_dbg_d3_f5_dept_intent.py | — | PASS |
| test_hook_fail_log.py | — | 11 OK |
| test_capgate_registration.py | — | 57 OK |
| test_session_start_hook.py | — | ALL PASS |

미실행: `run_bootstrap_health.py` 전체(대형 · 이 훅은 timeout 없는 픽스처로만 등장).
시험 함정: GNU timeout 없는 맥은 `cys_timeout_run` 이 `$CYS_PY -c …` 를 시계로 쓴다 — 느린 가짜 해석기가 시계까지 늦추면 시험이 60초 멈춘다(그래서 가짜는 `-c` 일 땐 안 늦춘다).

## 6. 윈 실기 절차 (미실행 — 원인 확정용)
1. 그 기계(또는 같은 1.1.10 윈 11 마스터 좌석) `%USERPROFILE%\.cys\state\hook-errors.log` 에서 `dept-chat-inject … rc=124` 줄의 `py=` 값(어느 해석기: python.exe · py.exe · WindowsApps 별칭)과 10-29 의 나머지 4건 훅 이름을 읽는다.
2. 좌석 Git Bash 에서 시계 분기 확인: `command -v timeout; timeout --version` (GNU 면 ①, System32 면 ③ 파이썬 시계).
3. 본체 시간 측정(운영 요청 폴더 오염 방지 — 임시 폴더):
   `time (printf '%s' '{"prompt":"교육부 만들어 줘","session_id":"t"}' | CYS_DEPT_REQUESTS="$TEMP/dci-rq" "$CYS_PY" ~/.cys/pack/bin/javis_dept_request.py hook-prompt >/dev/null)`
   — 재부팅 직후 1회(냉) · 연속 5회(온) 기록.
4. 이 브랜치 설치 후 `preflight --fix` → `~/.cys/claude/settings.json`(또는 좌석 settings) 의 dept-chat-inject `timeout` 이 10 인지 확인.
5. 마스터에 「부서」 낱말 든 프롬프트 20회 → `hook-errors.log` 의 새 rc=124 0건이면 통과.
6. 3번의 냉시작이 8초를 넘으면 상한 조정만으로 부족하다 — 다음 후보: hook-prompt 를 작은 모듈로 떼어 기동·컴파일 비용 축소, 또는 같은 턴 role-bootstrap 파이썬 호출과의 경합 축소(별 티켓).

## 7. 비가역·비용
push · int/1111 병합 · 빌드·배포 = master 게이트 — 하나도 하지 않았다.
