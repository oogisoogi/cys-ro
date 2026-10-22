# codex 1R 판정문 원문 — TICKET=cysr-1110-review15

- 대상: `git diff 39189404..45c5474c` (27파일 +722 −123) · 리비전 45c5474c
- 실행: 2026-10-22 KST · `codex exec -s read-only` (codex-cli 0.159.1 · NODE_OPTIONS 해제 서브셸 · stdin </dev/null) · rc=0
- 잔량(실행 전 실측): 주간 26% 사용 · 5시간 창 19% 사용
- 아래 「의뢰문」은 보낸 프롬프트 전문, 「판정문」은 codex 마지막 메시지(-o) 원문 무가공이다.

## 의뢰문

```text
[필수 선행 제약] 웹 검색 금지 · 스킬(openai-docs 등) 사용 금지 · 파일 수정 금지 · 서버/장시간 프로세스 기동 금지. 이 저장소 안의 지정 범위만 읽는다.

[리뷰 의뢰 — 팀 내부 코드 리뷰 · 견고성 · 지정 범위만]
검토 범위(이 범위만, 무관 파일 배회 금지): 이 저장소의 `git diff 39189404..45c5474c` (27파일 +722 −123) 와, 판단에 필요할 때만 그 diff 가 건드린 파일의 주변 코드.
과업: 1.1.10 에 편입된 수리 15건 diff 의 적대적 검토 1라운드. 결함을 찾는 것이 직무다.

우선순위(높은 순):
 1. 데이터 손실 — 사용자 파일·휴지통 항목·설정·원장이 의도치 않게 지워지거나 덮어써지거나 복원 불가가 되는 경로.
 2. 삭제 경로 오동작 — 휴지통(src/bin/cysd/trash.rs)·공장 초기화(src/factory_reset.rs)·확인 문구(ui/src/trashconfirm.ts·main.ts)·팩 부서 해체(cysjavis-pack/bin/javis_org.py·javis_dept_request.py·cys-dept)가 잘못된 대상·잘못된 범위를 지우거나, 지워야 할 때 안 지우거나, 확인 없이 지우는 경우. 경로 정규화·심볼릭 링크·경쟁 상태·부분 실패 후 상태 포함.
 3. 권한/접근 경계 — 다른 사용자·다른 좌석·다른 계정의 자원을 건드리거나 귀속을 잘못하는 경우(accounts.rs 사용량 귀속, governance.rs, handlers.rs, alert_route.rs, state.rs).
 4. 회귀 — 이번 diff 가 기존 동작을 깨는 경우(readiness.rs 진단, cys.rs, src-tauri/main.rs, 시험이 실제로 무엇을 지키는지 · 시험이 결함을 놓치는지).

리뷰 형식: 각 지적마다 [문제점] 파일:라인 · 구체 시나리오(입력/상태 → 잘못된 결과) · 심각도(blocking|major|minor) · 수리 제안. 그 뒤 [논쟁점] [다음 단계 조언]. 근거 없는 인상비평·칭찬만 하는 리뷰 금지. 추측이면 추측이라고 적어라.
판정: verdict enum(ACCEPT|REVISE|BLOCK|ESCALATE) + evidence(file:line). 점수 금지.

출력 마지막에 아래 형태 그대로 채운 JSON 을 ```json 펜스 하나로 출력하라(파일 저장은 의뢰자가 한다):
{"verdict": "ACCEPT|REVISE|BLOCK|ESCALATE", "justification": "", "evidence": [{"claim": "", "ref": "file:line", "verified": false}], "issues": [{"severity": "blocking|major|minor", "where": "file:line", "what": "", "fix": ""}], "missing": [], "revision": "45c5474c"}
```

## 판정문(원문)

판정: **REVISE**. 변경 경로에 남은 결함 4건입니다. 아래는 신규 회귀로 확정한 지적이 아니라 **기존 결함의 잔존 또는 수리 불완전**입니다. 근거는 `45c5474c`의 코드와 파일 쓰기 없는 대역 실행입니다.

[문제점] 1 — `cysjavis-pack/bin/cys-dept:2972` · **major**

부서명 검증보다 종료가 먼저입니다. 정상적인 `dept-1` 상태 디렉터리가 있을 때, 권한 게이트를 통과한 `down 'dept-1/../cys' --purge-state`의 소켓 경로는 기지의 `~/.local/state/cys/cys.sock`으로 해석됩니다. 기대 세대가 없고 미등재 이름이면 울타리도 통과합니다(`:843`). 이후 `identify`가 응답한 PID를 종료하고 소켓을 제거한 **뒤에야** `dept_purge_state`가 이름을 거부합니다(`:331`).

대역 실행에서도 종료·소켓 제거 대상으로 진입한 뒤 exit 3이 나왔습니다. 실제 데몬은 건드리지 않았습니다. 신규 B1 시험은 잘못된 도장만 검사하므로 이 경로를 놓칩니다.

수리 제안: 인자 파싱 직후 부서명을 검증하고, 경로 구분자·상위 참조를 울타리·조회·종료보다 먼저 거부하십시오.

[문제점] 2 — `cysjavis-pack/bin/javis_dept_request.py:1412` · **major**

휴지통 이동이 기존 보관본을 덮어쓸 수 있습니다. 목적지는 초 단위 이름이며 `exist_ok=True`로 재사용됩니다. 같은 초에 같은 basename 원장이 재생성되어 다시 정리되면 `os.replace`(`:1415`)가 첫 보관본을 소실시킵니다. 메모리 대역에서 두 호출의 목적지가 같고, 첫 원장이 사라지는 것을 확인했습니다.

또한 목적지 디렉터리가 심볼릭 링크여도 거부하는 검사가 없어 외부 동명 파일을 덮어쓰는 경로가 남습니다. R8 시험은 날짜 형식만 검사합니다.

수리 제안: 스탬프를 마지막에 유지한 고유 항목 이름을 배타적으로 생성하고, 열린 디렉터리 기준으로 이동하십시오. 기존 목적지와 링크는 재사용하지 않아야 합니다.

[문제점] 3 — `src/bin/cysd/state.rs:782` · **minor**

A4의 출처 수리는 반복 병합에서 다시 틀립니다. A 좌석의 32건에 B 좌석의 32건을 합치면 A 항목은 모두 버려지고 B만 남지만, 저장된 `from_surface`는 계속 A입니다(`:786`). 이후 C의 1건 때문에 B의 첫 항목이 버려지면 묘비에는 A가 기록됩니다.

신규 시험(`handlers.rs:27646`)은 기존 배치가 단일 좌석에서 왔다는 조건만 검증합니다. 실제 접근 권한 침범은 확인하지 않았으며, 확정된 영향은 폐기 원장의 오귀속입니다.

수리 제안: 항목별 주차 출처를 보존하고 병합·초과 폐기·만기 처리에서 사용하십시오. A→B→C 병합 시험이 필요합니다.

[문제점] 4 — `scripts/tests/test_update_publish.py:84` · **minor**

B3 보호는 detach가 정상 반환한 실패에만 적용됩니다. attach 성공 후 detach 실행이 `OSError`로 끝나거나 재시도 대기 중 중단되면 `stuck=True`에 도달하지 못합니다. `finally`는 마운트가 남았을 수 있는 디렉터리에 `rmtree`를 호출합니다.

선택한 실제 함수에 detach 예외를 주입한 대역 실행에서 이 호출을 확인했습니다. 영향 범위는 시험용 볼륨이며, 사용자 파일 손실은 실증하지 않았습니다. 신규 시험은 반환 코드 실패만 다룹니다.

수리 제안: attach 시도 전부터 재귀 제거를 금지하고, detach 성공을 확인한 경우에만 해제하십시오. 예외·중단·attach 부분 실패도 보관 경로를 보고해야 합니다.

[논쟁점]

1·2는 이번 diff가 만든 결함으로 세면 안 됩니다. 다만 요청한 삭제 경로의 견고성 검토에서는 각각 잘못된 대상 종료와 보관본 소실 경로이므로 수정 대상으로 판단합니다. 3은 감사 기록 결함이며, 4는 시험 하네스에 한정됩니다.

[다음 단계 조언]

1·2를 먼저 수정하고, 경로 순회 입력의 부작용 이전 거부와 목적지 충돌·링크 보존 시험을 추가하십시오. 이어 3의 반복 병합, 4의 예외 경로를 검증하십시오. 전체 시험과 실제 데몬·마운트 실험은 이번 제약에 따라 실행하지 않았습니다.

```json
{
  "verdict": "REVISE",
  "justification": "신규 회귀로 확정한 지적은 없으나, 변경된 삭제·격리 경로에 잘못된 대상 종료와 휴지통 보관본 덮어쓰기 경로가 남고 A4·B3 수리도 일부 실패 상태를 놓친다.",
  "evidence": [
    {
      "claim": "down_dept는 부서명 경로 검증 전에 종료와 소켓 제거를 수행한다. 경로 순회 입력의 대역 실행에서도 해당 단계 진입 후 exit 3을 확인했다.",
      "ref": "cysjavis-pack/bin/cys-dept:2988",
      "verified": true
    },
    {
      "claim": "초 단위 목적지를 재사용하고 os.replace로 이동한다. 메모리 대역에서 동일 목적지의 첫 보관본 덮어쓰기를 확인했다.",
      "ref": "cysjavis-pack/bin/javis_dept_request.py:1415",
      "verified": true
    },
    {
      "claim": "병합 후 첫 좌석 번호를 계속 저장하고 다음 폐기에도 재사용하므로 여러 좌석이 섞인 배치의 항목 출처가 왜곡된다.",
      "ref": "src/bin/cysd/state.rs:786",
      "verified": true
    },
    {
      "claim": "detach 예외 주입 시 stuck이 false로 남아 finally에서 rmtree가 호출되는 것을 대역 실행으로 확인했다.",
      "ref": "scripts/tests/test_update_publish.py:84",
      "verified": true
    }
  ],
  "issues": [
    {
      "severity": "major",
      "where": "cysjavis-pack/bin/cys-dept:2972",
      "what": "기존 결함 잔존: dept-1/../cys 같은 부서명이 기지 소켓으로 해석될 수 있으며, 이름 거부 전에 해당 PID 종료와 소켓 제거를 수행한다.",
      "fix": "인자 파싱 직후 부서명을 검증하고 경로 구분자·상위 참조를 모든 부작용보다 먼저 거부한다."
    },
    {
      "severity": "major",
      "where": "cysjavis-pack/bin/javis_dept_request.py:1412",
      "what": "기존 결함 잔존: 초 단위 목적지 재사용과 os.replace로 기존 휴지통 원장을 덮어쓸 수 있고, 목적지 디렉터리 링크도 거부하지 않는다.",
      "fix": "스탬프를 마지막에 둔 고유 디렉터리를 배타 생성하고 디렉터리 핸들 기준으로 이동하며 기존 목적지와 링크 재사용을 거부한다."
    },
    {
      "severity": "minor",
      "where": "src/bin/cysd/state.rs:782",
      "what": "A4 수리 불완전: 이전 배치가 여러 좌석의 항목을 포함하면 폐기 묘비에 실제 출처 대신 첫 주차 좌석이 기록된다.",
      "fix": "항목별 주차 출처를 보존하고 A→B→C 반복 병합 및 만기 처리 시험을 추가한다."
    },
    {
      "severity": "minor",
      "where": "scripts/tests/test_update_publish.py:84",
      "what": "B3 수리 불완전: attach 성공 후 detach 예외나 중단에서는 stuck이 설정되지 않아 마운트가 남았을 수 있는 트리에 rmtree를 호출한다.",
      "fix": "attach 시도 전부터 재귀 제거를 금지하고 detach 성공 확인 후에만 허용하며 예외·중단·부분 실패에서는 경로를 보존하고 보고한다."
    }
  ],
  "missing": [
    "실제 데몬 연결·종료, 실파일 덮어쓰기, 실마운트 실패 재현은 수행하지 않았다.",
    "Rust·UI·팩 전체 시험과 Windows 실기는 실행하지 않았다."
  ],
  "revision": "45c5474c"
}
```
---

## 워커 대조(worker-3 · 위 원문과 별도) — 지적별 성립 판정 · HANDOFF 「한계」 대조 · 처분

| # | codex 지적(심각도) | 독립 재유도 | 판정 | HANDOFF 「한계」 대조 | 처분 |
|---|---|---|---|---|---|
| 1 | `cys-dept down` 이 부서명 검증 전에 identify·kill·소켓 삭제(major) | `dept_sock`(cys-dept:99-103)이 `dept-1/../cys` 를 `~/.local/state/cys/cys.sock`(기지 데몬)으로 해석 · `down_dept` 에 이름 검사 0 · 검사는 kill·rm 뒤 `dept_purge_state`(:331)뿐. **실측 적**: 기지 데몬 대역(sleep) 사망 · 기지 소켓 삭제 · exit 3. 플래그 없는 `down` 은 이름 검사가 아예 없어 exit 0 | **성립**(기존 결함 · B1 이 만진 같은 함수) | 3건 어디에도 없음(B1 은 도장만 앞당김) | **수리** — 인자 파싱 직후 `/`·`\`·`..` 거부(exit 2 · `dept_purge_state`·`javis_org.destroy_dept` 와 같은 집합). 정식 화이트리스트(`validate_dept_name`)는 옛 비정형 등재의 down 을 막을 수 있어 쓰지 않음 |
| 2 | `_move_to_trash` 같은 초·같은 basename 덮어쓰기 + 목적지 링크 미거부(major) | `os.replace` 는 덮어씀 — 실측 적(시각 고정 2회 청소 → 같은 경로). 한 회차 안은 `listdir` 이름이 달라 충돌 0 · 동시 청소는 레지스트리 잠금+재독으로 직렬 → 남는 경로 = 같은 초에 같은 원장 재생성·재청소. 초 단위는 R8 이전 형식도 같음 | 덮어쓰기 **성립**(기존 결함 · 발생 조건 희박) · 링크 **불성립**(같은 사용자 소유 휴지통 안에 링크를 심을 수 있어야 함 = 경계 아님 · 데몬 trash.rs 는 링크를 따로 거부) | 없음(candidates 「한계」 R8 은 옛 이름 나이 표시만) | **수리**(덮어쓰기) — 있으면 `<basename>.<n>` 으로 비켜 감 · 항목 폴더 스탬프 불변. 링크 = 보고만 |
| 3 | A4 반복 병합 시 묘비 출처 오귀속(minor) | state.rs:768-786 — `from_surface` 는 처음 값 고정 · 옛 몫 전부 `first_from` | **성립** | **improve 「한계」 A4 줄에 이미 기재**(항목별 출처 칸 부재) | 보고만 · 다음 판(원장 표기 · 데이터 손실 아님) |
| 4 | B3 detach 예외·중단 시 `stuck` 미설정 → 마운트 남은 채 rmtree(minor) | test_update_publish.py:77-86 — `stuck` 은 반환 사유가 있을 때만 · runner 예외·KeyboardInterrupt 는 finally 로 직행 | **성립**(시험 하네스 한정 · 지우는 것은 시험이 만든 dmg 내용) | improve 「한계」 B3 줄 = 「가짜 runner 로만 쟀다」— 예외 경로는 미기재 | 보고만 · 다음 판(사용자 데이터 무관) |

곁 발견(브리프 4): 누수 검체 = `run_bootstrap_health.py` **H-WIN-7**(:4074) 의 `CYS_ROLE=master` leg(r2). cygpath 목이 모든 `-w` 인자에 `X:\Prog Files\javis_bootstrap.py` 를 돌려주므로 `_lib.sh:626` 이 `CYS_STATE_DIR` 까지 그 문자열(맥에선 상대 경로)로 바꾸고, 조립기 실패 폴백의 `cys_hook_fail`(`_lib.sh:537`)이 러너 cwd 아래에 `hook-errors.log` 를 쓴다. role-less leg(r)는 그 폴백을 타지 않아 무누수(뮤턴트로 확인). 1줄 수리(`cwd=tmp`).
