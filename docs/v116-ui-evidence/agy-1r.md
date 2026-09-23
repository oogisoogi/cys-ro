VERDICT: BLOCK

1. 산 창을 확인 없이 닫는 경로가 남았거나 새로 생겼는가
- 결함 없음.
- 근거: `actionClose` 내부 `if (!collectSids(ws.tree).includes(sid)) return;`로 포커스나 워크스페이스가 바뀐 상태에서 보이지 않는 창이 종료되는 경로를 막았고, 모달 대기 중 창이 사라진 경우도 정상적으로 리턴됨.

2. 확인 창이 반복·중첩 발화하거나(폭주), 영원히 닫히지 않는 상태가 가능한가
- 결함 있음 (확인 창 폭주).
- 재현 입력: 산 창을 닫기 위해 확인 창에서 "닫기(Yes)"를 누른 직후, 네트워크 지연 시간 동안 화면에 남아있는 창에 대해 단축키(⌘W)나 팔레트를 연속해서 다시 호출함.
- 근거: `confirmModal` 종료 후 `finally { closeConfirmOpen = false; }`로 락이 즉시 풀림. 이후 `await invoke("close_surface", ...)`를 대기하는 동안 데몬 응답이 없어 아직 `exitedPaneKeys`에 등록되지 않았으므로, 다시 호출 시 `if (needsCloseConfirm(...))`를 통과해 모달이 거듭 팝업됨.
- 고칠 줄: `ui/src/main.ts`의 `actionClose` 함수에서 `await invoke("close_surface", ...)`를 호출하기 전에 창을 트리에서 선제적으로 지우거나(`destroyPaneRuntime`, `replaceNode`), 별도의 닫는 중 상태 처리를 해야 함.

3. 소켓별 무장(armSweep/sweepArmedFor/settleSweep)에서 결함이 있는가
- 결함 없음.
- 근거: 조회가 실패한 소켓은 소켓 루프(results)를 타지 않아 `if (sweepHere) sweptSockets.push(sk ?? "");`에 진입하지 않으므로 무장이 안전하게 유지됨. 틱 도중 무장이 갱신되어도 `exitedSweepArm === sweepArm` 조건이 막아주며, `sk ?? ""`와 `w.socket ?? ""`로 키도 완벽히 일치함.

4. 루트 직계 flex 제거가 다른 배치를 깨는가
- 결함 없음.
- 근거: `top.style.flex = "";`는 분할 컨테이너 또는 단일 창 최상위의 인라인 스타일만 지우며, 이후 전역 스타일시트(`#root > * {flex:1}`)가 개입해 정상적으로 남은 창이 전체 폭을 차지하도록 함. 드래그 리사이즈는 자식 노드의 flex를 조절하므로 영향받지 않음.

5. 복원 카드 후보 선택이 틀린 기록을 고르는 입력이 있는가. 첫 기동 판정을 깨는가
- 결함 있음 (정본 파일 누락 및 오판).
- 재현 입력: 정본 경로(`~/.cys/pack/round/SESSION_STATE.md`)에 요구사항대로 새 4절 제목(현재 위치 등)만 존재하고, 종전 `_round` 경로에 낡은 고정 3절 제목(완료 등)이 있는 백업이 존재할 때 기동.
- 근거: `hasBriefSections` 함수는 `HEADS.some(([, re]) => re.test(l))`를 통해 종전 고정 3절 제목만을 검사함. 따라서 새 4절 제목만 있는 정본 파일은 `false`를 반환하고, `pickBriefText` 내부의 `if (!hasBriefSections(f.text)) continue;`에 의해 정본이 무조건 버려짐. 결국 낡은 기록을 고르거나, 기록이 아예 없는 것으로 취급(null)되어 첫 기동 판정 카드를 깸.
- 고칠 줄: `ui/src/restorebrief.ts`의 `hasBriefSections` 함수 (또는 참조하는 `HEADS` 배열)가 정본의 새 4절 제목 패턴도 올바른 절로 인식하여 매칭하도록 수정해야 함.

6. 그 밖 정확성 결함
- 결함 없음.
rc=0
