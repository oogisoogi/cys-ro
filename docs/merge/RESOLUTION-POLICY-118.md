# RESOLUTION-POLICY-118 — 1.1.8 원작자 전체 편입(merge up/v0.14.43) 해소 규칙 (병합 리드 · surface:1275 · 2026-10-05)

입력: 브리프 TICKET=cysr-118-merge-lead · DESIGN-118 §2·§8 · JUDGMENT-TABLE-118 + JT-PART 4 · CYS-UPDATE-POLICY §0.
가지 = merge/v0.14.43(머리 v1.1.7 75d2407b) · 원작자 = up/v0.14.43 · 공통 조상 bc01f43c(v0.14.30).
충돌 표기 = zdiff3(ours = 우리 1.1.7 · base = v0.14.30 · theirs = 원작자 0.14.43).

## 1. 기본값 — 「원작자 채택 + 우리 오버레이」
1. 한쪽만 바꾼 것처럼 보이는 덩어리(base==ours 또는 base==theirs 와 사실상 같음) → 바뀐 쪽.
2. 양쪽이 **서로 다른 기능**을 같은 자리에 더함 → **둘 다**(합성 · 이름·변수 충돌은 합성으로 풀고 원장에 적음).
3. 양쪽이 **같은 결함·같은 기능**을 서로 다르게 구현(의미 중복) → §2 표를 따른다. 표에 없으면 §4.
4. 원작자 시험(test 파일·검체)은 지우지 않는다. 우리 시험은 우리 구현을 버린 경우에만 함께 버리고 원장에 적는다.

## 2. 의미 중복 결정(이미 정해진 것 — 근거 문서 병기)
### 2-A. 원작자가 상회 → 원작자 채택, 우리 1.1.7 재구현은 버림 (JT §4 · JT-PART-DELIVERY §5-2 · JT-PART-R3-CLEAR §7)
- 입력 계층 전부: 미제출 입력 계수 상태기계(C-03 원판 `apply_pending_input`·`pending_input_step`) · 초안 게이트(C-04 · `selector_row`) · C-05 · Text 모달 축(D-01 P1) · 짝 Return 흡수(wp-delivery A2·B) · 쓰기 직전 보류+재제출(prerelease F1·FV2-1·R3C-1) · 제출 정착 S21 · 내부 주입자 하드축(H0·H2·H4·H5) · 사이클 창 큐 보류(H1) · 붙여넣기 살균·울타리(C) · 채널 재배달 상한·간격(H3).
  ⇒ 우리 ④ `draft_gate`(3426508d) · ⑭ 고착 해제 · ⑮ 자동응답 면제는 원작자 판으로 대체(단 §3 오버레이 3·7 확인).
- C-06 GUI 재기동(`ui/src/restartplan.ts` 원작자 판 · 한국어 번역표 포함) · C-01 드롭(`ui/src/droppoint.ts` 원작자 판 · 강조·오류문구·진단).
- R3-2 복원 상한(단위 비례) · R3-4 훅 지연 · R3-5 · R3-6/6a · R3-1c(topology 락은 원작자 이름 하나로 — 우리 7e468cd6 과 같은 효과면 원작자 것) · clear 가드 v3 + `--fire` · `--detach`(ⓓ 리뷰 대상으로 원장 표시).
- ⑤ verifier_precheck(우리가 원작자 ef87ad63 을 재구현) · ③ 재주입 한 전송(원작자 U8 P0-M1 이 원본) → 원작자 판 기준, 우리 추가분(rc 83 등)만 오버레이.
### 2-B. 우리가 상회 → 우리 유지
- **앱 층 커스텀(절대)**: 사이드바 토큰 사용량 패널(`ui/src/wsusage.ts`·`#ws-usage`·`renderSidebarUsage`·`src/bin/cysd/accounts.rs`·`usage.rs` 의 우리 계정·스코프 게이지·stale·OAuth 프로브) · `cys-local` 서명 · cys-ro 발행 게이트(`.github/workflows/release.yml`·`pack-release.yml`) · 브랜드 표시명 cysr·판번 라벨(headerlabels) · 팩 원격 URL = 우리 포크 · PACK_MIN_BINARY 규칙(우리 두 레인).
- 지침 배포 `RefreshUser`/`MergeUser`(pack.rs)·발행 해시 표 · 합성 지침 크기 상한(메모리 2,000 · 스킬 3,000) · 훅 출력 9,000자 상한+목차(session-start.sh) · 복원 1좌석 1회(restore_mark.rs) · `--resume-saved` · topology S3 보존 로직.
- ⑯ `refuse_on_approval`(순환·DRAIN·재주입이 승인 창 위에서 바이트 0 거부) + precut ㉮ writer 직전 재판정.
- 팀 승인: 우리 dept-by-chat 경로 유지(JT §3 선택지 C) — 원작자 team-propose 기계(D-17 `team_spec`·`run_team_propose`·`runTeamProposalFlow`·`teamproposal.ts` 배선)와 team-confirm T2 토큰은 **받지 않는다**. 단 team-confirm T1 확인 창 z-index 는 받는다.
- 부서 레지스트리 판독 실패 = 무변경(① exit 12 · BOM · rotate 전 확인 · GUI 「못 읽음」) — 원작자 원판(종료코드 다름)과 겹치면 우리 번호·동작 유지, 원작자 추가분(상단바 아이콘화·한글 whoami·표시명 폴백·stop 결과 처리)은 받는다.
### 2-C. 동등(JT 「유지」) → 우리 유지 + 원작자 잔여 갈래만 수용
- B-10 wsreconcile(우리 ffcb8500) · D-07 배치(우리 formation.ts autoArrange) · D-08 업데이트 단추(우리 f19dbadd) · D-13~16 · D-19 피드백(우리 2단계 업로드 · 원작자 modalguard 는 잠정 수용 후보 — §4).

## 3. 오버레이 확인 목록(원작자 채택 자리에서 우리 것이 살아 있어야 하는 것)
1. ⑯ refuse_on_approval 2. precut ㉮ writer 재판정+계수 복원 3. ⑭ `maybe_release_stale_pending_input`(원작자 `queue.input_pending_reset` 과 겹치면 원작자 것 + 원장 표시) 4. `approval_in_prompt_tail` 5. `seat_inject_guarded`/`hold_for_vacant_seat` 6. `human_trusted` 축 7. ⑮(원작자 같은 함수 있으면 원작자) 8. RefreshUser 9. 지침 크기 상한 10. 훅 9,000자 11. restore_mark 12. `--resume-saved` 13. ⑰ schedule.json 판독 실패 쓰기 금지·원자 저장(락 설계는 §4).

## 4. 판정 갈림(병합 리드가 정하지 않는다 — 잠정 해소 + master 결정 목록)
- 표에 없는 의미 중복은 **잠정 = 우리 유지(사용자가 지금 보는 동작 보존)** 로 컴파일 가능하게 풀고, 원장에 「잠정·결정대기 Xn」으로 표시한다. master 결정이 오면 그 덩어리만 다시 푼다.
- 목록(갱신): `docs/merge/DECISIONS-PENDING-118.md`.
