# DECISIONS-PENDING-118 — 판정 갈림 목록 (master 결정 · 세 칸 = 우리 유지 / 원작자 채택+오버레이 / 둘 다 폐기)
잠정 해소 = 컴파일 가능하게 둔 쪽. master 결정이 오면 해당 덩어리만 다시 푼다.

| ID | 자리 | 우리 | 원작자 | 잠정 | 근거 1줄 |
|---|---|---|---|---|---|
| **D-TEAM** ★ | 원작자 team-propose 기계(D-17)·team-confirm 대화 승인 토큰(T2) — 충돌 없이 자동 병합돼 들어온 코드 | dept-by-chat(JT §3 선택지 C) | `cys team-propose`·`team_spec`·`runTeamProposalFlow`·T2 토큰·MASTER §4-A 「말로 팀 만들기」 | **불일치(정정 필요)**: cys.rs = CLI·시험 mod 2 제거(X1) · main.ts = UI 배선 제거 · 팩(cys-dept·formation·bootstrap·MASTER §4-A) = 남음 · src-tauri = 남겨 둠 지시 | 정책 §0-1 「편입 제외 = 박사님 게이트(ⓔ)」 — 제거는 ⓔ. 권고 = 「휴면 유지(배선만 안 함)」로 통일(제거분 되살림) 또는 ⓔ 상신 |
| X1 | ui 배치 | formation autoArrange(v116 균등 · 적대 3R) | seatlayout U2 역할 칸 구멍·복원 결속 / U3 대표 1/3·layoutManual·daemonEpoch | 우리 | JT D-07 「유지」 · 원작자 wswiring/seatbind/seatlayout 단언·starvednotice(isClosingSid) 일부 적색 예상 |
| X2 | ui 업데이트 UX | updateplan·restartpending | updatestate U9 단일 상태 + 0.14.43 J2/WU | 우리 + J2/WU 이식 | 우리 윈 문안 「재시작 직전 대화 저장」 ↔ 원작자 R1F-UA(윈 drain 없음) 사실 대조 필요 |
| X3 | ui 부서 만들기 | deptconfirm·expertmode·launchDept | deptcreate U17 확인 창·전문가 칸 | 우리 + GU deptprogress(대기 문구·팀원 부팅 안내) 수용 | 대응물 없는 갈래만 수용 |
| X4 | modalguard | — | 모달 층 setFocus 가드 | 부분 수용 | 우리 피드백 창 안 focusin 되찾기는 미적용(JT D-19 잔여) |
| X6 | 좌석 신호 | appearance.nodeWorking | seatsig U12(빈 자리·신선 자기보고) | 겹침=우리 · 원작자 전용 갈래 수용 | 한 화면 두 규칙(CC 행 taskSeatView ↔ 부서 머리 nodeWorking) |
| X7 | CC 경보 | 헤더 개수 배지 제거(박사님 09-15 ⓔ) | probefail 추적기·unknown | 배지 미표시 + 스트립 판정 원작자 | 박사님 결정 보존 |
| X8 | 폴더 접근 안내 | v116 첫 실행·seat.folder_denied 토스트 | folderaccess U14/U18 | 합성 | folderaccess.ts PRIVACY_APP_NAME="cys" → cysr 로 바꿔야(브랜드) · 알람 이력 2건 가능 |
| X9 | CC 숨기기 → 사이드바 | 숨김 없음 | 숨기기가 사이드바·KPI 공유 | 합성(사이드바가 숨김 계정 원천 제외) | ★사이드바 패널(절대 보존) 입력에 원작자 개념이 처음 닿는 자리 — 박사님 커스텀 영향 확인 |
| X10 | CC Live 계정 조회 | 5초 직접 invoke | U1 공유 fetcher(in-flight 가드) | 우리 | 가드 개선 상실 |
| X11 | ccAggRate | 미관측 거름 | aggSeatRates(UI2 · 상위 판) | 원작자 | 우리 wsusage-null.test 문자열 핀 갱신 |
| X12 | 전출 awaitHandoffAck | replaceNode 허용 목록 | WP-4 새 함수 | 원작자 | 우리 autoarrange.test 핀 허용 목록에 추가 |
| X13 | injectRawToPane 토스트 | D4#14 사람 말+원문 칸 | sendfailwiring.test 가 옛 문자열 핀 | 우리 | 원작자 시험 1 적색 → 시험 조정 |
| H1 ★ | cysd 입력 게이트 사람 신뢰 축 | human_trusted(pane 무귀속 ∨ 오퍼레이터 토큰) · 권위 면제도 사람 초안 못 덮음 | 면제=게이트 생략 · 자기신고 human 은 ACL 층 문제 | 우리(오버레이 6) | 원작자 시험 적색 14~17 예상(고정물 v7_pane 이 GUI pid 를 pane 에 묶음) · ⓐ 유지+고정물 조정 ⓑ 원작자 ⓒ F2 만 |
| H2 | 좌석 승계·npm 고지 | 화면 출력 display_notice(A3) | 입력 주입 | 우리 | 원작자 시험 허용목록 2줄 조정 |
| H3 | 승인 저장소 | lock_records 파일 잠금 | mutate_records 트랜잭션 | 합성 | 응답 코드 records_unreadable → persist_failed(소비자 0) |
| H4 | ④ 대체로 사라지는 것 | EditKey 축 · F4 GUI 삽입 사람 몫 | 없음 | 원작자(정책 2-A) | 확인만 |
| H5 | usage.report claude 귀속 | D6-2 술어 | 프로필 경계·rate_account | 합성 · ⓓ | 확인만 |
| H6 | note_line_submitted | 우리 갈래2 R3 | H4 하드축+H0 | 원작자 · ⓓ | 확인만 |
| H7 | S21 표식 · SubmitGuarded | — | SubmitAfterGap 에만 | 원작자 | 순환 /clear Return 직후 본문은 S21 분리 보류 못 받음 |
| C1 | 복원·복귀 깨움 글 | 이어받은 좌석 지시 1장 | 한 제출 틀 | 합성 | 원작자 틀에 「이어서 작업」·「재개 말라」 공존 문제 |
| C2 | cys send 6초 대기 | 우리 루프 | 원작자 정착 재시도 | 원작자 | 확인만 |
| C3 | ⑰ schedule 락 | flock + 판독 실패 쓰기 금지·원자 저장 | 디렉터리 잠금 | 둘 다 쥠 | 교착 순서 점검 필요 |
| C4 | statusline | report_named | 총예산 구조 + agy 갈래(휴면) | 합성 | agy 갈래 제외 여부(박사님 09-19 agy 삭제) |
| C5 | ⑯ 오버레이 | refuse_on_approval | — | 원작자 시험 앵커 6 조정 | 확인만(단언 뜻 불변) |
| R1 | lane-parity 예행 | 우리 임시 폴더 격리 | 문자열 검사 | — | lane-parity-rehearsal.sh:439 수정 필요(범위 밖 파일) |
| R2 | PACK_MIN_BINARY | 1.1.7 두 레인 | — | 1.1.7 | 1.1.8 판정 = 통합 리드 TK-G |
| R3 | 원격 검증기 자산 13종 | DMG 없음·맥 레인 선택 | 13종 | — | 자체 시험 1 적색 |
| R4 | gktool 검사 | 자체서명 레인 | 공증 레인 | SKIP 계수 | 실기 미확인 |
| R5 | 작업 폴더에 없는 파일 | 판정 불가 차단 | — | 우리 | 확인만 |
| R6 | 매뉴얼 상단바 | — | — | — | UI 결과와 문면 대조 |
| R7 | 매뉴얼 팀 만들기·피드백 절 | 우리 판 | 원작자 판 문면 | 원작자 문면+차이 표기 | D-TEAM 에 종속 |
| R8 | 팀 토큰 시험 4 등재 | — | 등재 | 등재 | D-TEAM 에 종속(받지 않으면 적색) |
| P-WAIT | cys-dept 스폰 뒤 대기 | 우리 | GP 노브 | 우리 | |
| P-PROBE | cys-dept 스폰 전 검사 | 우리 | GP | 우리 | |
| P-J4 | rotate kill 뒤 판독 실패 재기동 | 우리 | 원작자 | 우리 | |
| P-NOWIN | 윈 창 숨김 정책 | hide_console·NOWIN | 원작자 | 우리 | |
| P-CLT | 맥 CLT 셔임 회피 | 우리 | U15 | 우리 | |
| P-OWNER | 오너 토큰 | 키워드 전달 | reinject 동사에서 추론 | 우리 | |
| P-I4F1 | 핑 게이트 × 새 세션 검증 | 우리 | 원작자 | 혼합(검토 필요) | |
| P-INSEAT | phoenix 빈 좌석 재사용 | 우리 | 원작자 | 우리 | test_phoenix_f1_production_path 49/63 적색 원인 |
| P-CNUM | preflight C82/C83 번호 | 우리 | 원작자 같은 번호 | 우리 | 번호 충돌 |
| P-TEAMDOC | 지침 팀 토큰 문면 | CEO 머리 = 우리 | MASTER §4-A 원작자 | 불일치 | D-TEAM 에 종속 |
| P-BYTES ★ | 지침 크기 | MASTER 80,509B | +27,696 → 108,205 · CSO → 62,210 · CEO_TEMPLATE → 116,415 | 원작자 추가 절 수용(master 22:28 확정) | test_cso_directive_rev 바이트 래칫 3 적색 · 각성 주입·clear 뒤 바닥 상승(JT-R3 §5) |
| P-EXIT12 | 부서 판독 실패 종료코드 | 12 | 10 | 12(팩 전체 재번호) | test_role_authority(_shell).py·Rust GUI·ui 쪽 10 기대 → 12 로 맞춰야 |

## master 결정 [master#36f48cf7] 2026-10-05 22:34 (원장 대조 성립 · surface:1275 · submitted yes)
1. D-TEAM = **휴면으로 통일** — 코드·원작자 시험 4 유지 · CLI 서브커맨드·UI 배선·지침 §4-A 노출만 끊음(제거 아님 → ⓔ 불요). cys.rs·main.ts 의 「제거」 해소는 「휴면」으로 되돌림.
2. H1 = **ⓐ 유지**(사람 초안 못 덮음 포함) · 원작자 고정물 14~17 조정은 파일마다 원장 1줄 · 시험 삭제 금지.
3. P-BYTES = **선별** — 병합 코드가 실제로 부르는 절만(`--fire`·`--detach` 절차 · §5 clear 가드) · 휴면 기능(팀 토큰 등) 절 제외 · 바이트 래칫 시험 초록이 상한(래칫 완화 금지) · 선별 목록 = 원장.
4. X1 = **우리 균등 배치 유지**(박사님 09-25 D-1 · 사용자 닫기 존중) · 원작자 배치 시험은 우리 동작 기준으로 수정(삭제 금지).
5. X9 = **사이드바 패널엔 적용 안 함**(숨기기는 원작자 화면에서만).
6. C4 agy 갈래 = **휴면**(cfg off · 삭제 아님).
7. P-EXIT12 = **우리 12 유지** · 원작자 기대처(팩 시험 2 · GUI · ui) 재번호.
- 나머지 37 = 잠정 해소 수용(원장 보존).
- 다음 = (가): 진행 중 파일 완료 → git add → 격리 env 측정만 → 적색 목록+계수 【진행】 → 수리. 277 judge 결정표(핵심 3파일 · 10-06 21:00 전)와 어긋나면 원장에 「judge 대기」.

## 결정 뒤 새로 나온 갈림(22:37~ · 측정 보고와 함께 상신)
| ID | 자리 | 우리 | 원작자 | 잠정 | 근거 1줄 |
|---|---|---|---|---|---|
| X14 | drainverify 「데몬 무응답」 줄 | 우리 알림 | drainVerifyUnresponsiveLines | export 만(미배선) | 우리 drainVerifyNotice 에 붙일지 |
| X15 | 상단바 | 글자 단추(박사님 v1.1.6 T-UI) | 아이콘화(B-12 잔여) | 우리 | 정책 §2-B 「원작자 추가분 상단바 아이콘화 수용」 문면과 박사님 결정 충돌 |
| X16 | 묘비 미상 토스트 시험 | — | wswiring 단언 | .skip | 수리 단계에서 우리 동작 기준 |
| X17 | feedbackmodal.ts(원작자 U6 작성 창 · 미배선) | 우리 feedback.ts(2단계) | 원작자 feedback.ts API 전제 | 미정 — 타입 검사 실패 | ⓐ 원작자 feedback.ts 를 별도 이름으로 두고 휴면 컴파일 ⓑ 제거(ⓔ 게이트) ⓒ 검사 제외 |
| X18 ★ | CSO_DIRECTIVE 바이트 3자 모순 | 우리 고유 절 ~4.9KB(재시작 드레인 등) | 원작자 CSO 57,365B ≈ 래칫 상한 57,368B · 원작자 문구 핀 시험 14 | 래칫 초록(57,080B) · 원작자 설명·옛 데몬 폴백 9단락(4,996B) 삭감 → test_cso_directive_rev 23/73 적색(14 = 삭감 단락 핀 · 9 = 기존) | 셋(우리 절 · 원작자 문구 핀 · 래칫) 동시 불가 — ⓐ 우리 절 일부 포기 ⓑ 삭감 단락 핀 시험을 우리 문면 기준으로 조정(삭제 아님) ⓒ 래칫 완화(master 금지) |
| G1 | 큐 배달 승인 축 | approval_screen_now 화면 판독 | 원작자 승인 축 | OR 합성(막는 방향만) | 좌석·틱당 판독 1회 증가 |
| G2 | 에이전트 사망 시 미제출 계수 비움 | 1.1.7 회귀 봉합 | clear_pending_input API | 우리 의미 + 원작자 API | 확인만 |
| G3 | 배달 직전 pause 재확인(⑩ Q2) | 유지 | writer 탐침 | 둘 다 | 무해 중복 |
| S1 ★ | 역할 좌석 자체 종료 시 남은 큐 | parked_queues 주차 → claim_role 상속 | restored_queue 보존소 → rehome | 셸 종료 = 우리 · reap = 원작자 → 보존소 2개 공존(payload 이름 queue_role_parked_payload 로 가름) | 같은 기능 두 벌 · 상호작용 미실행 |
| S2 | 판독 불능 큐 WAL 보호 | ⑧ | X4 | 둘 다 | 보존 2회 시도 |
| A1 | 승인 저장소 경로 | 우리 경로 판 3(시험용 잔존) | 원작자 두 저장소 + 우리 BOM | 원작자 | 확인만 |
| A2 | 서명 키 | signing_secret_at | 부분집합 | 우리 | 확인만 |
| T1 | 부서 만들기 실행 경로(src-tauri) | dept.run 대행 | dept-create-progress 실시간 이벤트 | 우리 · 원작자 인자(team_spec·progress_id) 받음 · 팀 제안 검증 휴면 | X3 GU 진행 표시와 연동(이벤트 미배선 → 원작자 시험 2 적색) |
| T2 | 원작자 U6 피드백 백엔드 | 우리 본체 | feedback_submit·feedback_discard 이름 충돌 | 원작자 판 = feedback::u6_local_bundle 하위 모듈(명령 미등록 · 휴면) · STAGE_LOCK 만 합성 | X17 과 한 묶음 |
| T3 | send_input 실패 문자열 | message 만 | code: message | 코드 없을 때 우리 | 확인만 |
| T4 | 맥 업데이트 J2 시도 기록 | B7(기록 안 씀) | J2 | 맥 = 우리 · 윈 = 원작자 | |
| T5 | 온보딩 「cys 연결 설정」 문구 | cysr | cys | 미판정 | 브랜드 |
| U1 | 사용량 패널 agy 행 | 제외(박사님 09-19) | agy 행 재추가 | 우리 | 원작자 agy 시험 ~10 적색 |
| U2 | 계정 경보 로직 | 죽은 창 거름 | 원작자 경보 로직 | 원작자(표시값 불변) | 확인만 |
| U3 | OAuth 관측 → 경보 | 경보 입력에 포함(좌석 없는 계정도 경보) | — | 우리 | 📌5 와 연동 |
| U4 | 패널 표시 병합 | 리셋 지난 창이 살아 있는 창을 못 덮음(report_account 값 포함) | — | 우리 · ⓓ | 📌5 와 연동 |
| SC1 | schedule 락 2개(데몬) | 공유 락(무기한 대기) | 디렉터리 잠금 | 둘 다 · CLI 와 같은 순서 | 우리 락 무기한 대기 |
| SC2 | 예약 push 빈 좌석 보류 | inject 안 보류 | inject 제거 · inject_on | 원작자 inject_on 첫머리에 우리 보류 | |
| SC3·SC4 | ⑰ 판독 실패 쓰기 금지 | 유지 | 원작자 원샷 재큐가 판독 불가 schedule.json 을 빈 것으로 덮음 | 우리 규칙으로 원작자 경로 수리 · 무변경 시 쓰기 생략 | 원작자 결함을 우리가 고침 |
| M1 | cysd main.rs 원작자 팀 시험 mod | — | 유지 | 유지(휴면 기능 시험) | D-TEAM 휴면에 종속 |

## judge 결정표 대조(감사 22:4x · report-judge-audit.txt · 일치 33 · 불일치 3 · judge 대기 9 · 보류 8)
| 항목 | 지금 | 결정표 | 처리 |
|---|---|---|---|
| K17 ⑯ | 모든 경로 살아 있음(cys.rs:22385~22685·5579·23588/23678·24603 · handlers.rs:6261·6880) · 형태 = 우리 WriteReq::SubmitGuarded | 원작자 SubmitAfterGap 에 refuse 모드 | 수리 단계: submit_cr 판정에 SubmitGuarded 포함 + writer 표식 소비 → H7 틈 닫기(안전 핵심은 이미 충족) |
| K07 | 우리 restartRetryPlan 폐기(원작자 planRestartInject 채택) | 재시도 오버레이 유지 | **judge 대기** |
| K10/X16 | wswiring 원작자 배치 시험 `.skip` | 우리 동작 기준 수정(삭제 금지) | 수리 단계에서 .skip 해제·우리 기준 수정 |
| K49 | schedule BUILTIN_JOBS_VERSION 3 · ctx-relay-base/tick + 원작자 경보 라우터 공존 | ctx_relay 폐기 · 버전 4 | **judge 대기**(같은 통보 2회 위험) |
| K26 | 우리 dbg-D2 추종이 OS 무관 + 원작자 clear_repin_verdict 공존(usage.rs:1554) | 📌2 = 윈 한정 폴백 | **judge 대기 📌2** |
| 📌1 | 윈 cys send 재시도 0 + 정착 0(우리 6초 루프 삭제 · cys.rs:3149) = 1.1.7 대비 후퇴 | 윈 안전망 유지 | **judge 대기 📌1** — 수리 후보 |
| 📌5 | 창 밖 값을 우리 패널·usage-accounts 가 거르지 않음(잠복 · 우리 CLI 는 report_account 안 부름) | 거름 오버레이 | **judge 대기 📌5** |
| R2 | MASTER 지침이 --detach·--fire 지시 · PACK_MIN_BINARY 1.1.7 | 1.1.8 | TK-G(판번) |
| 📌7ⓐ | javis_dept_request.py:2240 `mach is not True` | `is False` 1줄 | **judge 대기 📌7** |
| D-TEAM 보충 | role-bootstrap.sh ⑤-b 팀 토큰 발급 절 활성 | 끊기 권고 | **judge 대기**(master 문면 = CLI·UI·지침 노출만) |
| 함정 6 | idoforgod 3건 = HEAD(1.1.7)에도 있던 출처 고지 | 「=0」 | 기준을 「HEAD 대비 증가 0」으로 — 충족 |

## [master#cd9e534c] judge 집행 조건 5(R1 신설) + master 추가 결정(📌) — 수리 단계 반영 대상
1. D-TEAM 휴면 = **데몬 스위치 1개(기본 off)** 로 구현 2. ⑯ refuse 이식은 **간격 없는 키(Data 경로)까지** 3. detach 위임 뒤 **양성 캐시 60초** 4. EXIT12 재번호에 **원작자 cys-dept :2877/:2908/:2913 포함** 5. 사이드바 패널 보존 범위 = **OAuth·weekly_scoped 생산자까지**.
- 1.1.8 범위 추가(master 결정): 📌1 윈 입력 안전장치 켬 · 📌5 사용량 우선순위 데몬 · 📌7ⓐ fail-open 1줄 · 📌7ⓓ 윈 프로세스 간 잠금. 세부 = DECISION-TABLE-118 §0 「master 결정 13」 표.

## 수리 1차에서 나온 결정 필요(ui · 17f40a9c 뒤 91 실패의 정체)
| ID | 무엇 | 사실 | 권고 |
|---|---|---|---|
| DS-1 ★ | 원작자 GU 팀원 부팅 안내(수용 결정 X3)가 「5석 다 붙음」을 완료로 봄 | 우리 기본 함대 = 3석(master·cso·worker · 09-10 결정) → 새 부서는 「모두 붙었습니다」가 영영 안 뜨고 3분 뒤 「더 붙지 않습니다」 오보(코드 정독 · 실행 미확인) · 드리프트 시험 2(deptcreate·deptprogressseats)가 바로 이것을 잡음 · 목록을 3으로 바꾸면 58 적색 | 의무 역할 출처(DEPT_SEAT_ROLES)를 우리 편성 도구 정본과 결속하는 수리 티켓(시험 기대값 동반 조정) — 1.1.8 범위 |
| X2-R | 업데이트 설치 재진입 | SAC 검사 중 「설치」 재클릭 → 우리 판은 검사 3회·확인 창 중첩 · 원작자는 막음(시험 5 · 1건은 시간 초과로 스위트 +5초) | 우리 installingUpdate 가드를 SAC 사전 검사 구간까지 넓힘(소수정) |
| X2-W | 윈 설치 문구 사실 대조 | 시험 1 | 원작자 R1F-UA 문면으로 |
| UNW | 미배선 기능 배선 시험 ≈80(U1 사이드바+X10 34 · U17 전문가 칸 19 · U17 launchDept 실패 알림 6 · U9 10 · U16 8 · U6 3) | 조정하면 시험 목적과 반대 단언이 됨 | 이 시험들은 「1.1.8 휴면/미수용」 묶음으로 별도 판정: ⓐ 휴면 스위치 켠 상태로만 돌게 격리 ⓑ ⓔ(박사님 게이트)로 시험 동반 제외 ⓒ 적색 허용 목록(CI 비차단) |
| cysr 문구 | src-tauri 「데몬을 시작하지 못했습니다」 문면 cys → cysr | folderaccess 시험 1 | 수리 B 또는 리드 |
