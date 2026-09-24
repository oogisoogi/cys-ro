# HANDOFF — v116-restart-toast · 맥 새 판 교체 뒤 「다시 켜기」 자리가 사라지지 않게

TICKET=v116-restart-toast · worker-43(surface:1091) · 브랜치 `fix/v116-restart-toast` ← 기점 **adf50d44** · 2026-09-24
증거 폴더 = `docs/v116-restart-toast-evidence/` · 설계 = 같은 폴더 `DESIGN.md`

## 한 줄 요약
맥에서 새 판 교체가 끝나면 헤더 「업데이트」 단추가 **「다시 켜기」**(배지 「!」)로 바뀌어, 60초 알림이 사라진 뒤에도 누르면 **이미 받은 판으로 다시 켠다**(install_update 재호출 0 = 재다운로드·재교체 0). 알림 수명(60초 · 오너 정책)은 그대로다.

## 필요성 · 효과 시점(정직 고지)
- 이 알림은 **교체를 마친 옛 앱**이 띄운다 → 1.1.6 에 넣은 수리는 **1.1.6 에서 다음 판으로 갈 때부터** 효과가 난다. 1.1.5→1.1.6 갱신 사용자는 여전히 옛 알림(60초 소멸)을 본다 → 1.1.6 공지 한 줄은 master 몫(13:5x 결정 ⓑ).
- 그래도 넣는 이유: 안 넣으면 1.1.6→1.1.7 사용자가 같은 반복(1085 VM-B 실측: 토스트를 놓친 뒤 매 회 재다운로드·재교체)을 한 세대 더 겪는다.
- 안 한 것: ⓐ 알림 무기한(master 불허 · 오너 정책) · ⓓ Rust 재다운로드 방지(UI 가 대기 중 install_update 를 부르지 않음을 c17b·c17c·c17h·c17n 으로 측정 — 남는 구멍 = 화면 기억이 사라지는 드문 경우 → 오늘 동작과 같음 · 악화 0).

## 무엇이 바뀌었나(제품)
- 새 모듈 `ui/src/restartpending.ts`(순수): 대기 판정 `decodeRestartPending`(판번 + build_id 짝) · 단추 동작 판정 · 문구.
- `ui/src/main.ts`:
  - 상태 `restartPendingVersion`(설정 = `update-restart-required` 리스너 하나 · 해제 = 재시작으로 프로세스가 끝나는 것뿐) + sessionStorage 사본 `cys-restart-pending-v1`(⌘R 을 넘김 · 저장 때 앱 판번·build_id 가 지금과 다르면 무효 = 새 앱으로 켜지면 저절로 풀림).
  - `onUpdateButton`: 복원을 기다린 뒤 대기면 `restartAfterUpdate`, 아니면 종전 `checkForUpdate(false)`.
  - `checkForUpdate`: 머리에서 대기면 확인 없이 「다시 켜기」만 다시 칠하고 끝 · 확인 응답을 기다린 뒤에도 한 번 더(그 사이 교체 완료 경합).
  - `promptBinaryPatch`: install_update 직전 대기면 다시 켜기로 넘김(설치 확인 창이 떠 있는 사이 교체 완료 경합).
  - `restartAfterUpdate`: 재진입 차단(첫 await 전 플래그 · finally 해제) — 연타·알림+단추 동시 = restart_after_update 1회.
  - `pack-updated` 리스너: 배지를 내린 뒤 대기면 다시 칠함.
  - 알림 문구: 「✅ 새 앱 설치 완료」 / 「새 앱 1.1.7 설치가 끝났습니다. 이 알림을 누르면 하던 대화를 저장하고 앱을 다시 켭니다. 나중에 하시려면 위쪽 「다시 켜기」 단추를 눌러 주세요.」
- Rust·index.html·toastttl.ts **무변경**. 윈도 동작 불변(이벤트를 내는 곳 = 맥 `install_update_darwin` 한 곳).

## 커밋(`git log --oneline adf50d44..HEAD` · 제품 fix 4 · 시험 test 5 · 문서 docs — 제품 마지막 = 26eeb1a0 · 정본 게이트 대상 = 9c41830d)
- 8244aa90 test 헤드리스 c17·c17w 적색 재현 · c00fd93f fix 본 수리 · 11161421 test 단위 · 21c007ba fix agy 1R #2 · b2fc1988 test c17x h~l + 뮤턴트 스크립트 · 4e3c2320 fix 클로드 적대 1R(build_id 짝 외 4) · ef489087 test c17m~p · 26eeb1a0 fix 주석 · 9c41830d test M17 봉합·c17q · (이 문서 커밋 = 그 뒤)

## 재현 표(헤드리스 실번들 · chrome-headless-shell · 1280×820)
| 칸 | 내용 | 기준선 adf50d44 | 수리본 |
|---|---|---|---|
| c17a | 교체 완료 60초 뒤 누를 자리 = 단추 「다시 켜기」 · 배지 「!」 · 설치 안내 0 | FAIL(단추 「업데이트」 · 누를 자리 0) | PASS |
| c17b | 「다시 켜기」 → restart_after_update 1 · install_update 0 · 새 확인 0 | FAIL(설치 확인 창 → install_update 1 = 재다운로드) | PASS |
| c17c | ⌘R 뒤 유지 · 시작 확인이 설치 안내 0 · 누르면 재시작 | FAIL | PASS |
| c17d | 새 판으로 켜진 뒤 = 「업데이트」 · 기억 칸 삭제 · 확인 경로 | PASS(가드) | PASS |
| c17e | 연타(헤더 2 + 알림 1 · 같은 틱) → 재시작 1 · 설치 창 0 | (약한 판 PASS → 단언 강화) | PASS |
| c17f | 세션 확인 창 열린 채 재클릭 = 창 1 · 취소 뒤 유지 · 승낙 = force | FAIL(설치 창 2개) | PASS |
| c17g | 재시작 실패 → 실패 알림 · 유지 · 재시도 | FAIL | PASS |
| c17h~p | 경계(아래 디버깅 절) | — | PASS |
| c17w | 윈도 = 「업데이트」 · 설치 경로 불변 · 대기 0 | PASS | PASS |
- ⚠c17w 한계(정직): 흉내층은 윈도에서 이벤트를 원래 내지 않으므로 「대기가 안 생김」은 사실상 자명 — 이 칸이 지키는 것은 **윈 설치 경로 불변**뿐. 「윈에서 대기가 생기지 않음」의 실질 근거 = Rust 방출 지점 1곳 핀(단위 시험 · main.rs 문자열 리터럴만 센다 = 다른 모듈·상수 경유 방출은 못 본다) · 윈 실기 【미측정】.

## 검증
- 단위: `bun test` 1270/1270(50 파일) · 새 파일 `restartpending.test.ts` 24건 · `bunx tsc -p tsconfig.check.json` 오류 7 = 기존 7(headerlabels 3 · restorebrief 3 · updateplan 1) · 신규 0.
- 헤드리스(실번들 · `docs/v116-ui-evidence/v116-headless.ts` · 전수 = `docs/v116-restart-toast-evidence/headless-final.txt`): c1~c16 무회귀 · c17a~g · c17h~q · c17w. 최종 전수 1회에서 c17q 가 FAIL — 첫 판 단언 「상단바 넘침 증가 0」 이 상단바 설계(좁으면 가로 스크롤 · D4 #2)와 어긋나 교정(실측: 800폭 평소 넘침 50px → 다시 켜기 54px · +4px · 단추 한 줄·높이 불변·화면 안·페이지 넘침 0) → 교정본 c17x 재실행 ALL PASS(`headless-c17x-final.txt`).
- 뮤턴트(`mutate_rt.py` · 단위 + 헤드리스 실번들 · 원문 복원 assert): 18개 → 1차 17/18(M17 배지 칠하기 제거 생존 — c17a 의 배지는 시작 확인이 이미 「!」로 칠해 둬 구별 불가) → c17c(⌘R 뒤 = 칠하기만이 배지를 켠다)에 단언 추가 → **18/18 KILLED**(`mutants-result.txt`).
- 이종 검증: agy 1R BLOCK 4(#1 다른 창 sessionStorage = 기각 · 근거 tauri.conf.json 창 1개 · WebviewWindowBuilder·window.open 0 / #2~#4 수용) → agy 2R ACCEPT. 클로드 적대(서브에이전트 · jsonl model = claude-opus-5-5 54/54) 1R BLOCK(MAJOR 1 build_id · MINOR 5 수용 · 2 범위 밖) → 2R ACCEPT(사소 3: 칸 번호 주석·시험 이름 = 수리 · 아래 한계 1 = 기록). 수렴 = 서로 다른 검증자 dry. codex 미사용(브리프 금지).
- 정본 게이트: (아래 「게이트」 절)

## 한계(정직)
- 교체 완료 순간 `app_build_id` 조회가 실패하면(정적 문자열 명령이라 실제 확률 ≈ 0) 저장 사본의 build_id 가 비어 「같은 판 재빌드」 대기는 ⌘R 뒤 판번 규칙으로 무효 → 그 경우만 수리 전 동작(재다운로드 가능). 판번이 다른 일반 새 판은 영향 없음.
- 대기 기억이 사라지는 드문 경우(화면 기억 초기화) = 수리 전 동작으로 후퇴(악화 0).
- 윈 실기·맥 실기 【미측정】 — 헤드리스 흉내층 증거만. 맥 실기(VM)는 v116-vm-1 몫.

## 4군 점검
- ①폭주 큐: `restartAfterUpdate` 재진입 차단(첫 await 전 플래그 · finally) — 같은 틱 헤더 2 + 알림 1 = restart_after_update 1(c17e) · 세션 확인 창 열린 채 재클릭 = 창 1(c17f) · 뮤턴트 M4·M5 KILLED.
- ②무clear 100%+: 좌석 기동·CTX·데몬 RPC 무접촉(diff = ui/src/main.ts 업데이트 구간 + 새 모듈 · Rust 0줄).
- ③자가치유 전멸: 새 재시작 경로 0 — 기존 `restart_after_update` 호출 2곳 그대로(단위 핀) · 복원·복귀 마커 무변경 · 실패·취소 뒤 대기 유지·다시 누를 수 있음(c17f·c17g).
- ④전 pane 사망: `app.restart()` 실패 창 = 기존 동작 그대로(Rust diff 0줄 · 이 수리는 그 경로를 부르는 입구만 늘림) · 윈 = 대기 상태 미발생(방출 1곳 핀 · c17w 설치 경로 불변) · 윈 실기 【미측정】.

## 완료 뒤 정밀 디버깅 — 어디까지 뒤졌나
- 경계 17칸: 교체 직후 ⌘R(c17c) · 대기 중 조용한 확인(c17c 시작 확인 · 6시간·포커스 확인은 같은 함수 머리 가드 = 구조 핀 · 벽시계 발화 자체는 헤드리스 미발화) · 더 새 판(c17i) · 재시작 실패 뒤 재시도(c17g) · 세션 확인 창 취소(c17f) · 알림 ×(c17j) · 좁은 창(c17q) · 설치 확인 창 경합(c17h) · 판번 조회 실패(c17k) · 복원 경합(c17l) · 같은 판 재빌드(c17m) · 진행 중 확인 경합(c17n) · 복원 전 첫 클릭(c17o) · 팩 적용 완료(c17p) · 연타(c17e) · 새 판으로 켜짐(c17d) · 윈(c17w).
- 표적 뮤테이션 18/18.
- 계수: 읽은 파일 17(main.ts · restartpending.ts/test · updateplan.ts · toastttl.ts · clipath.ts · index.html · style.css · updatebutton/topbarlabels/brandbadge.test.ts · src-tauri main.rs · macupdate.rs · pack.rs · tauri.conf.json · shim.js · v116-headless.ts) · 경로 = 대기 설정 1 · 해제 0 · 확인 입구 4(시작·6시간·포커스·단추) · 설치 입구 2(promptBinaryPatch · autotest) · 재시작 입구 2(알림·단추) · 셸 명령 약 70회.

## 게이트
(진행 중 — 결과 채움)

## 곁 항목(범위 밖 · master 판단)
1. 【기존 결함】 다운로드 진행 중(upd-bin) 헤더 재클릭 → 옛 앱이 같은 판을 새것으로 판정 → 두 번째 install_update(재다운로드). 첫 확인 응답 전 두 번 누르면 설치 확인 창 2개. 수리 전부터 있던 결함(클로드 적대 1R #3) · 수리안 = `installingUpdate` 플래그(첫 await 전 · finally) 1개 + 헤드리스 1칸.
2. 【기존 문구】 「다시 켜기」 뒤 이어지는 확인 창 제목 「재시작 (새 판 v1.1.7)」 · 단추 「재시작」 · 실패 알림 「재시작 실패」 — 괄호·「새 판」·「v」·「재시작」(데몬 「↻ 재시작」과 같은 낱말). 이 수리로 바뀌지 않은 문자열이라 손대지 않음(대원칙 2). 수리안 = 제목 「새 앱 1.1.7 로 다시 켜기」 · 단추 「다시 켜기」 · 실패 알림 「다시 켜기 실패」.
3. 【절충】 대기 중엔 팩 확인(check_pack_update)도 건너뜀 → 다시 켜기를 며칠 미루면 무중단 팩 적용도 그동안 미룸. 다시 켜면 풀림.
4. 【시험 전용 경로】 `CYS_AUTOTEST_PATCH_INSTALL=1` 자동 설치(main.ts autotest)는 대기 가드 밖 — 제품 영향 0.
5. 【같은 계열】 HANDOFF-v116-integ §11 ⑵ perm-guide 도 같은 60초 소멸 계열(이 티켓 범위 밖).
6. 【미측정】 「앱 종료 뒤 다시 열기로 새 판이 뜨는가」(1085 이월 ⑶) — VM 2차 행 후보.
