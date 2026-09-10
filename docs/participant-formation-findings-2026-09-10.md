# 참가자 기계 편성 결함 4건 — 처리 결과·규명 (TICKET=pack-participant-formation · 2026-09-10)

대상 기계: 박사님 노트북(Windows) · 우리 빌드 0.14.33 · 설치기 v0.3.7 · agy·codex 미설치 ·
Claude 구독 1개. 이하 「실측」은 그 기계에서 관측된 사실이고, 「소스 확인」은 이 저장소의
코드를 읽어 확정한 사실이다. 둘을 섞지 않는다.

## P1 리뷰어 2기 무구독 폴백 스폰 — 수리

**실측** 매 부팅마다 `reviewer-claude-1/2`(claude)가 서고, 리뷰 의뢰가 0인데 화면에
「86% weekly limit」. 사용자가 닫아도 다음 판정이 되살렸다.

**소스 확인** `javis_orchestra.reviewer_roster` 가 agy·codex 미감지 시 Claude 대체 슬롯을
만들고, `effective_required_roles` 가 그 대체 좌석을 **의무 역할**로 올렸다. 그래서
① ④-b `boot-reviewers` 가 2기를 스폰하고 ② ⑤ `check`·부트 결손 판정이 그 좌석의 부재를
결손으로 세어 ④를 다시 돌렸다 — 닫아도 되살아나는 고리의 정체가 이것이다.

**수리** 편성 프로파일 도입. 판정 소스는 **네이티브 CLI 실재 여부 하나**(설정 파일 추가 0):
- 네이티브(agy·codex)가 **하나도 없으면** 참가자 프로파일 → 리뷰어는 **온디맨드**.
  `boot-reviewers` 스폰 0·exit 0(Degrade 아님) · 의무 역할 = `cso·worker` ·
  formation 도 리뷰어를 결원·필수 CLI 양쪽에서 제외.
- 하나라도 있으면 **현행 동작 완전 보존**(우리 맥 = 네이티브 2 · 혼합 기계 = 네이티브 1 + 대체 1).
- 기동 경로는 남는다: `javis_boot_node.py --role reviewer-claude-1 --agent claude`.
  없앤 것은 능력이 아니라 **상시 점유**다.

부수 수리: formation 이 `partial:agy,codex` 로 **영구 고정**되던 것(배너 불멸)이 함께 풀린다.
complete 피드 본문도 프로파일 파생으로 바꿨다 — 3기가 선 기계에 「reviewer-gemini·
reviewer-codex 전부 기동 완료」라고 적던 **거짓 보고**를 제거했다.

## P2 자식 좌석 cwd = 홈 → 폴더 신뢰 관문 — 수리

**실측** master 좌석만 설치기가 `--cwd %USERPROFILE%\install-jarvis`(신뢰 시드됨)로 띄우고,
cso·worker·리뷰어는 홈에서 떠 「Yes, I trust this folder」(기본 선택 = No, exit)에 갇혔다.
master 페인에 `[관문감지] surface:N … (id=folder-trust)` 8건.

**수리** 자식 cwd 상속:
- `javis_formation.ensure` — 호출자가 cwd 를 주지 않으면 **master 좌석의 생성 cwd**(`cys status
  --json` 의 `cwd`)를 자식이 물려받는다. 해소는 ensure 호출당 1회. 못 얻으면 조용히 None(=홈,
  종전 동작) — 상속은 개선이지 전제가 아니다.
- `javis_phoenix` fresh 강등 — 원 좌석 cwd(topology entry) → master 좌석 cwd → 미지정 순.
- `live_cwd` 가 아니라 `cwd` 를 쓴다: 상속 대상은 「설치기가 신뢰를 심어 둔 폴더」이지 마스터가
  잠시 `cd` 해 간 현재 폴더가 아니다(그걸 물려주면 자식이 다시 관문에 갇힌다).

### 「통과 액션은 부트 경로가 집행한다」 문구 — 규명 결과

데몬의 관문 격상 문구(`src/bin/cysd/governance.rs` `gate_escalation_text`)는 human-only 가
아닌 관문에 대해 「통과 액션은 부트 경로가 자기 게이트 아래에서 집행한다」고 말한다.

**소스 확인 — 이 문장은 CLI 부트 경로에 대해서는 참이다.** 폴더신뢰 자동확인은
`src/bin/cys.rs::boot_agent_on_surface`(`trust_prompt_hit` → 1발 래치 Return)에 있고,
세 경로가 **모두** 그 함수를 지난다: `run_launch_agent_opts`(=`cys launch-agent`) ·
`run_node_recover` · `run_restore`. 데몬 auto-restore 도 phoenix → `cys restore` → 같은 함수다.
즉 「집행하는 자가 없다」는 경로는 **발견되지 않았다**.

**따라서 관문 8건의 원인은 「집행자 부재」가 아니라 그 앞 단계다** — 자식이 *신뢰되지 않은
폴더*에서 떴다는 사실(P2)이 관문을 만들었고, 자동확인이 실패했다면 그 다음 후보는
(ⓐ) 그 Claude 판본의 문면이 코퍼스 needle·어댑터 패턴 어느 쪽에도 안 맞았거나
(ⓑ) 관문이 readiness 관측 창 **밖에서** 떴거나 둘 중 하나다.
⚠**둘 다 이 기계의 화면 실측 없이는 확정할 수 없다** — 추정으로 코퍼스를 넓히면 킬체인
(확인 에코 재매칭 → 2발째 Return 이 면책 창을 눌러 좌석 사망)을 다시 연다. P2 수리로 관문
자체가 뜨지 않게 되므로 이 축은 **재현 시 화면 캡처 후** 판단한다(문구는 손대지 않았다 — 참이므로).

## P3 데몬 자식 고아(Windows) — 수리

**실측** 설정 앱에서 cys 제거(cysd.exe 소멸) 뒤에도 office-bridge `python3.exe`
(`%LOCALAPPDATA%\cys\runtime\python\python3.exe` · pid 17600 · CPU 324s) 생존 → 설치 폴더
삭제 불가 → 재설치 정지.

**소스 확인** office-bridge 는 `kill_on_drop(true)` 뿐이었다. 그것은 **이 tokio 태스크가 Child 를
드롭할 때만** 동작한다 — `taskkill /F`·제거처럼 cysd 가 드롭 없이 사라지는 경로에서는 무효다.
반면 PTY 자식은 이미 데몬 소유 **Job Object(KILL_ON_JOB_CLOSE)** 에 편입돼 있었다
(`src/bin/cysd/state.rs::winjob`).

**수리** 같은 Job·같은 헬퍼에 런타임 자식 3종을 추가 편입(새 규약 발명 0):
`main.rs` office-bridge · `main.rs` auto-restore python · `boot_supervisor.rs` 부트 체인 python
(이 셋 중 뒤 둘은 핸들을 즉시 드롭하거나 대기만 해서 `kill_on_drop` 조차 없었다).

⚠**정직한 한계**: 「부모 종료 후 자식 부재」의 **런타임 실측은 Windows 실기 몫**이다. 이 커밋에
실린 것은 소스 트립와이어(편입 지점 전수 4 고정 · `test_participant_formation.py` ⓒ)뿐이다.

## P4 재부팅 뒤 자동 시작 — 규명 + 문구 정정

**실측** 재부팅 뒤 cys 가 안 떠 박사님이 손으로 실행. 작업 스케줄러 `\cysd` 는 Ready·oogis·
Limited·Execute=cysd.exe 로 **정상 등록**돼 있었다.

**소스 확인 — 등록은 맞고 문구가 틀렸다.** `cys daemon install` 이 만드는 태스크의 Action 은
`cysd.exe` **하나**다(`src/bin/cys.rs::cysd_task_xml` — LogonTrigger·InteractiveToken·
LeastPrivilege=Limited·RestartOnFailure PT1M×10·ExecutionTimeLimit PT0S). 즉 로그온 시 뜨는
것은 **데몬**이고 **cys 앱 창은 아무도 띄우지 않는다**. 사용자는 창이 없으니 「자동 시작 실패」로
읽는다. 문구를 정정했다(보장/미보장을 같은 자리에서 말한다).

**「지웠는데 재등장」의 소스 확인**: 앱은 Windows 첫 기동 온보딩에서
`maybe_windows_onboard()` → `cys daemon install`(schtasks `/Create /XML … /F` 멱등)을 **매번**
부른다(`src-tauri/src/main.rs`). 제거기가 태스크를 지워도 **앱을 한 번 켜면 다시 등록된다** —
재등장은 버그가 아니라 이 배선의 정상 귀결이다. 제거 절차는 「태스크 삭제」가 아니라
「앱 제거 후 태스크 삭제」 순서여야 한다.

**미확정(추정 금지)**: PowerShell `Unregister-ScheduledTask cysd` = 「액세스가 거부되었습니다」.
우리 제거 경로는 `schtasks /Delete /TN cysd /F` 라 그 명령을 쓰지 않는다(설치기 쪽 절차다).
권한 SD 문제인지 재등장과의 혼동인지는 **실기 재현 없이 단정하지 않는다** — 재현 절차:
`schtasks /Query /TN cysd /XML` 로 등록 주체 확인 → 앱 종료 후 `schtasks /Delete /TN cysd /F`
→ 재조회. 설치기(티켓 A ⓔ) 쪽에 이 사실과 절차를 전달한다.

## P0 회귀 축(수정 금지)

재부팅 뒤 **master 좌석 복원**(646 phoenix S3 콜드부트 수리 = `cys new-surface --agent` 선언
플래그로 설치기가 세운 master 를 부활 대상으로 만든 것 · `f44101c`)이 참가자 기계에서
실증됐다. 이 티켓은 그 경로를 **건드리지 않았다** — ⓑ 의 cwd 상속은 `_ensure_master_seat` 의
호출 인자(master 자신의 cwd)를 바꾸지 않고 **자식 좌석에만** 적용된다.
