# HANDOFF — TICKET=cysr-no-hands-gui-1118 (사용자가 일하는 동안 자비스가 손을 빌리지 않게 · 1.1.16)

- 가지 `feat/no-hands-gui-1118` ← integ/1116 `7d25c38e` · cwd `/Users/oogisoogi/axdev/.wt/cys-1116-nohands`
- push·태그·서명·발행 0 · 박사님 화면 입력 조작 0(⚠ 알림 1줄 사고 — §6)

## 1. 무엇이 바뀌었나
| 파일 | 변경 |
|---|---|
| `cysjavis-pack/bin/javis_idle_gate.py`(새) | 유휴 관문 도구 — `idle` · `wait --seconds 20 --timeout N --task T --est N` · `mark` · `check` · `end --restore` · `pending` · `done --id` |
| `cysjavis-pack/bin/tests/test_idle_gate.py`(새) | 관문 계약(가짜 시계) + 윈 원천 단위 + 문서 계약(손 떼기 요청 문장 0 · 스킬 절 · 지침 절 · 한글 문구) |
| `cysjavis-pack/bin/tests/mut_idle_gate.py`(새) | 뮤턴트 9종(관문 끔 · fail-open · 도중 입력 못 봄 · 시간 초과 go · 대기열 누락 · 윈 감김 · 재개 기준점 · 손 떼기 문구 · 상한 없음) |
| `cysjavis-pack/skills/computer-control/SKILL.md` | 새 절 「사용자가 일하는 동안 — 손을 빌리지 않기 (1.1.16)」 + 한글 일 표 · 67줄 「맥 한글은 화면 조작만」 → 파일 도구 먼저 · description 에 트리거 1구 |
| `cysjavis-pack/bin/javis_computer_control.py` | 맥 한글 안내 문구(MAC_APPS hwp note) = 파일 먼저 · 앱은 PDF·인쇄처럼 꼭 필요할 때만 |
| `cysjavis-pack/directives/MASTER_DIRECTIVE.md` | 「컴퓨터 통제」 절 **바로 뒤**(파일 끝 아님 — ownermem 좌석의 끝 추가와 충돌 회피) 「## ★ 사용자와 함께 쓰는 컴퓨터 — 손을 빌리지 않기 (1.1.16)」 2줄 |
| `CEO_TEMPLATE.md` · `RELEASED_MASTER_DIRECTIVE.sha256` · `src/released_directive_hashes.rs` | 생성기 재실행 산출(`gen_ceo_template.py` · `gen_released_directive_hashes.py`) |

## 2. 설계 요점(codex 1R REVISE 반영 후)
- 판정 원천 = OS 값만(맥 `ioreg -c IOHIDSystem` HIDIdleTime 나노초 · 윈 `GetLastInputInfo` − `GetTickCount` 32비트 감김 보정). 못 읽으면 쉼 아님(fail-closed → 미룸).
- 시각 비교 = 단조 시계(`time.monotonic`) · 세션에 「벽시계−단조」 차 기록 → 다른 프로세스에서 2초 넘게 다르면(재부팅·시계 기준 변경) 그 사이 입력을 모르는 것으로 보고 다시 기다림.
- 「마지막 입력 시각」 = 관측값 중 가장 늦은 것(최고값)을 세션에 이어 씀 · 관측 간격 ≤ 1초 — 윈 SendInput 이 옛 틱을 넣어 값이 뒤로 가도(MS 문서) 이미 본 입력이 지워지지 않음.
- 자비스의 키·클릭도 유휴 시계를 0 으로 돌릴 수 있다 → 동작 직후 `mark --sid`, 다음 동작 직전 `check --sid`: **mark 뒤 입력 1개라도 = 사용자**(여유 0 · 늦게 반영된 내 입력도 사용자로 봄 = 멈췄다 다시 기다림 = 안전 쪽) → 도구가 멈추고 다시 20초 쉼을 기다렸다 돌려준다(재개 = 새 기준점).
- go 판정 뒤 준비(맨 앞 앱 기록 · 알림)가 끝나면 쉼 조건을 다시 확인 — 준비 중 입력이 있으면 go 하지 않고 계속 기다림.
- 끝의 원래 앱 복귀(`end --sid --restore`)도 입력 조작 → 마지막 mark 뒤 사용자 입력이 있었거나 못 읽으면 되돌리지 않음(`restore_reason: user_active`).
- 화면 작업은 한 번에 하나: `wait` 이 `sid` 발급 · 진행 중이면 exit 5(busy) · mark/check/end 는 sid 일치만 · 버려진 세션은 900초(단조) 뒤 만료 · 세션·대기열 쓰기는 잠금(맥 flock · 윈 msvcrt) 안에서.
- 시간 초과 = exit 3 · `idle-pending.json` 대기열(같은 일 한 줄 · 자동으로 버리지 않음 · 같은 `--task` 로 나중에 통과하면 빠짐).
- 시작 알림 say 「잠깐 화면을 씁니다(약 n초). 하시던 일은 그대로 하셔도 됩니다 — …멈췄다가 쉬실 때 이어 합니다.」 · 끝 say 「화면 쓰기를 마쳤습니다(n초).」 · 맥은 알림 센터에도 1줄(포커스 0 · 최선 노력) · 윈은 대화 화면 1줄뿐.
- 상태 = `~/.cys/computer-control/idle-session.json` · `idle-pending.json` · `idle-gate.lock`(`CYS_IDLE_STATE` 로 바꿈).

## 3. 한글 일 표(스킬 정본)
앱 필요 = 서식 그대로 PDF 저장·인쇄(앞으로 불러야 실제 저장 · 10-25 실측) · HWPX→HWPX 서식 유지 저장(rhwp 는 .hwp 로만 · kordoc 역변환은 서식 빠짐) · 복잡 문서는 사본에 파일 도구 → render 확인 → 깨질 때만 앱. 나머지(읽기·변환·비교·양식 칸·본문/표/칸 편집·새 문서·미리보기)는 파일 도구 · 관문 없음.

## 4. 시험
| 항목 | 결과 |
|---|---|
| test_idle_gate | 20 OK(실대기 0 · 실 OS 값 0) |
| 고치기 전(문서 계약) | 4건 붉음: hwp 문구 · 스킬 절 · MASTER 절 · CEO 절(「손 떼기」 문장 검사는 고치기 전에도 0건 — 팩에 그런 문장이 원래 없음 = 참가자 증상은 규칙 부재에서 온 모델 기본 행동) |
| mut_idle_gate | 9/9 KILLED |
| test_computer_control | 112 OK(좌석 환경변수 `CYS_ROLE`·`CYS_SURFACE_ID`·`CLAUDE_CODE_ENABLE_CFC` 를 뺀 실행 · 그대로 두면 기준선 7d25c38e 도 같은 14건 붉음 = 시험 격리 결함 · 이 티켓 무관) |
| mut_computer_control | (§7 갱신) |
| test_bootv2_doc_contract · test_event_inject · test_computer_use_audit | rc 0 · rc 0 · 17 OK |
| 합성기 `gen_ceo_template.py --check` · `gen_released_directive_hashes.py --check` | GREEN · OK |
| test_cso_directive_rev | 74/75 — 바이트 예산 핀 1건 붉음 = **기준선부터**(86,642 > 85,365) · 이 절로 87,1xx · master 결정 |
| 실기 판독(읽기만) | 박사님 사용 중 HIDIdleTime 1.1→3.3→0.2… 재설정 관측(이 맥에서 원천 정상) |

## 5. 바깥 증거
- Microsoft Learn GetLastInputInfo: 「session-specific user input information for only the session that invoked the function」 · 「tick count … not guaranteed to be incremental … SendInput, which supplies its own tick count」 — https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getlastinputinfo (High)
- HIDIdleTime = IOHIDSystem 속성 · 나노초(Apple cocoa-dev 목록 · 여러 오픈소스 구현) · 「connected hardware and other software may reset the HIDIdleTime value」(DSSW Power Manager 안내) · 2023 Jamf 글 = M2 에서 안 줄어든 사례 1건(Med — 이 맥 실측은 정상) — https://dssw.co.uk/powermanager/guide/finding-and-fixing/inactivity/ · https://community.jamf.com/t5/jamf-pro/user-idle-time-timer-script-not-working-any-more-with-m2/m-p/297956

## 6. 함정·잔여 위험
- ⚠ 사고 1건: 실기 스모크에서 `end` 에 `CYS_IDLE_NO_NOTIFY` 를 빠뜨려 박사님 맥 알림 센터에 「화면 쓰기를 마쳤습니다(0초)」 1줄(입력·포커스 조작 0). 시험은 전부 가짜 시계 + 알림 끔.
- 잔여 위험(미측정 · codex 1R blocking 중 남는 부분): 자비스 동작이 끝난 순간 ~ `mark` 사이(모델 지연 수 초)의 사용자 입력은 「내 동작」과 구분 못 한다(mark 뒤 입력은 이제 여유 0 으로 잡음). 합성 입력이 HIDIdleTime 을 실제로 0 으로 돌리는지도 미측정(박사님 화면에 합성 입력을 보내야 재는 것이라 하지 않음) — 돌리지 않는다면 이 틈도 없다. 화면 없는 시험 기기(VM)에서 재는 것이 다음 단계. 스킬은 「동작 직후 곧바로 mark」로 틈을 줄인다.
- 윈 SendInput 역행: 우리가 한 번이라도 본 입력은 최고값으로 지켜지지만, 관측 전에 사용자 입력 직후 역행이 일어나면 못 본다(관측 간격 ≤ 1초로 줄임).
- 윈 GetLastInputInfo 는 세션 한정 — cysr 좌석이 사용자 세션에서 돈다는 전제(서비스 세션 0 이면 값이 틀림 · 윈 실기 확인 항목).
- `rhwp-advanced` 스킬은 hwp·rhwp-edit 가 가리키지만 팩에 없음(참고 · 범위 밖).

## 7. codex 1R
(갱신 예정)
