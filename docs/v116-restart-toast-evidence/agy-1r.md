BLOCK

1. `ui/src/main.ts` (+ `if (appVer) sessionStorage.setItem(RESTART_PENDING_KEY, encodeRestartPending(version, appVer));`)
   · 구체적 실패 시나리오: 새 판 교체가 끝나 창 A의 `sessionStorage`에 대기 상태가 기록됨 → 사용자가 새 탭/창 B를 엶 → `sessionStorage`는 탭(컨텍스트) 단위로 격리되므로 창 B는 값이 비어 있고 완료 이벤트도 놓쳐 대기 상태가 없는 것(null)으로 시작 → 창 B에서 `checkForUpdate` 실행 → 옛 데몬이 같은 판을 새 판이라 응답 → 설치 확인 창이 뜨고 승낙 시 다시 전량 재다운로드·재교체함 (`localStorage`를 쓰면 해결되나 격리 스토리지를 써서 다중 창 대응 실패).
   · 심각도: MAJOR
   · 기존 시험이 잡는지: 기존 헤드리스 시험(`c17`)은 같은 탭에서의 ⌘R(`Page.reload`)만 흉내 내므로, 새 창을 여는 시나리오를 다루지 않아 잡지 못함.

2. `ui/src/main.ts` (+ `sessionStorage.removeItem(RESTART_PENDING_KEY);`)
   · 구체적 실패 시나리오: ⌘R 새로고침 시 `restoreRestartPending`이 `sessionStorage`에서 유효한 대기 값을 읽음 → `invoke("app_version")` 호출 시 일시적인 IPC 지연이나 백엔드 오류로 예외(throw) 발생 → catch 블록으로 빠져 `appVer`가 `null`이 됨 → `decodeRestartPending(raw, null)`이 `null`을 반환 → 무효한 값으로 오판하고 `removeItem`을 강행해 올바른 대기 상태를 영구 삭제 → 새로고침 뒤 버튼이 "업데이트"로 돌아감.
   · 심각도: MINOR
   · 기존 시험이 잡는지: `app_version` 타임아웃/오류를 주입하는 흉내층이나 예외 시나리오가 없어 잡지 못함.

3. `ui/src/main.ts` (+ `if (restartPendingVersion === null) restartPendingVersion = v;`)
   · 구체적 실패 시나리오: M10 뮤턴트(`restartPendingVersion = v;`로 덮어쓰기) 적용 시 → 앱 시작 직후 `restoreRestartPending`이 `invoke` 결과를 기다리는 도중 백그라운드 교체가 끝나 이벤트 발생 → `markRestartPending`이 `restartPendingVersion`을 "1.1.8"로 갱신 → 직후 `invoke`가 끝나고 비어있던 스토리지의 반환값(`v = null`)이 도달 → 무조건 덮어쓰며 메모리의 "1.1.8" 대기 상태가 `null`로 파괴됨.
   · 심각도: MINOR
   · 기존 시험이 잡는지: 헤드리스 시험 `c17`은 로드 후 3500ms 대기 후 완료 이벤트를 발생시키므로, 초기 `invoke`와 이벤트가 겹치는 마이크로태스크 경합을 유발하지 못해 M10이 새 시험을 통과하고 살아남음(SURVIVED).

4. `ui/src/restartpending.ts` (+ `if (version === currentAppVersion) return null;`)
   · 구체적 실패 시나리오: M8 뮤턴트(해당 줄 삭제) 적용 시 → 사용자가 강제로 지금과 같은 판번(1.1.7)을 덮어씌워 설치 완료한 경우, `version`과 `currentAppVersion`이 같아 무효화되어야 할 상태가 유효한 것으로 처리되어 거짓 대기 상태가 생김.
   · 심각도: MINOR
   · 기존 시험이 잡는지: `restartpending.test.ts`의 『새 판으로 켜졌으면... 무효』 시험은 인자를 `appVersion = "1.1.6"`으로 넘겨 그 윗줄인 `appVersion !== currentAppVersion` 조건에서 이미 `null`을 반환받아버림. 정작 두 변수가 같은 조건(`appVersion === currentAppVersion`)을 통과해 이 줄까지 도달하는 시험 자체가 없어, 코드를 지워도 모든 단위 시험이 통과하고 살아남음(SURVIVED).
