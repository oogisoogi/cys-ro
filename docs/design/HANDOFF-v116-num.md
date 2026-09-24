# HANDOFF — v116-num ①설계 (보이는 번호 1~999 순환)

## §0 델타 (②③ 구현 완료 · 2026-09-24 12:3x · TICKET=v116-num · 판정 [master#725963ea] ①ACCEPT → ②③)

- **어디까지 했나**: ②데몬 + ③표시 구현 완료 · 로컬 커밋만(push·병합 0 = master 게이트).
  · fix/v116-num: 8b8e90d1(②) → f657c1e0(code-1R 반영 + ③데몬 제목·CLI) → 이 커밋(code-2R 반영 · 문서 · 증거).
  · **fix/v116-num-ui**(로컬 · fix/v116-ui=3bc73856 위) 42596ebf = ③ 앱 창 머리·알림 번호. ⚠T-UI 가 만든 ui/src/panetitle.ts 위에만 선다 → **병합 때 T-UI 뒤에 cherry-pick**.
  · 사용자본(저장소 밖) ~/.cys/pack/bin/javis_panetitle.py · javis_reconstruct_state.py 선배포 완료(조건 ⑴) — 백업 = ~/.cys/state/v116-num-pack-backup/(원본 · sha256 ac3bf061…· c176fb6d…) · 자체 시험 PASS · 옛 데몬 plan 변경 0.
- **검증**: 뮤턴트 34/34 KILLED(r1 24 · r2 10) · E2E T5+T11 10/10(1,051좌석) · CLI E2E 15/15 · 회귀 cysd 1072×3 · cys 289 · lib 535 · UI 1244 · 적대 agy code 1R·2R ACCEPT · Fable code 1R·2R 메커니즘 결함 0(문서·시험 강도 발견 반영) · agy ui 1R(HIGH = T-UI 기존 동작 · 상신).
- **백그라운드**: 없음(검증자·뮤턴트·E2E 종료 · 격리 /tmp 폴더 0 · 기준선 작업트리 제거).
- **다음 할 일**: master 검수 → 병합 순서 T-USAGE → T-PACK → T-NUM(겹침 handlers.rs·governance.rs·cys.rs·lib.rs rebase) → T-UI 뒤 fix/v116-num-ui cherry-pick.
- **함정**: ⑴ 뮤턴트 실행 중 작업트리 편집·커밋 금지(실행기가 파일을 바꿨다 되돌린다) ⑵ M23 뮤턴트는 바이너리를 빌드하므로 실행 뒤 재빌드 ⑶ 윈도 CI 는 --bin cysd 레인이 없다(T12 미실행) ⑷ 부서 소켓에 CLI 금지 — E2E 는 /tmp 짧은 경로 격리 데몬 ⑸ zsh 는 변수에 담은 `env -u …` 를 단어로 안 나눈다(unset 루프로).
- **재현**: `python3 scripts/v116_num_mutants.py` · `python3 scripts/v116_num_e2e.py [--cli-only]` · `python3 cysjavis-pack/bin/tests/test_v116_num_cys_list_compat.py` · UI = `cd ../cys-v116-num-ui/ui && ~/.bun/bin/bun test`.

## (이력) §0 델타 (파킹 2026-09-24 08:5x · TICKET=park-for-cysr115-0924)

- **어디까지 했나**: ①설계 티켓 **완료**. 설계 문서 `docs/design/surface-display-number.md` 최종 = d68e0cdf(423줄). 【확인요청】 08:45 인박스 발신 완료. **master 검수 대기** 상태로 파킹.
- **진행 중이던 검증 라운드**: 없음(모두 종결). agy 1R~5R(5R ACCEPT · 발견 없음 = dry) · Fable 적대 1R~5R(5R 메커니즘 결함 0 · 문서 정합 발견 → 전수 반영). **6R 은 돌리지 않았다** — 권고 = 구현 ② 코드 리뷰에서 부팅 순서(§3-2 부팅 행)·락 범위(§3-2 ②)·경보 식별(`surface_id` 유무)을 다시 겨눈다.
- **백그라운드**: 없음(agy·서브에이전트 전부 종료 확인). 스크래치패드 비움(agy 판정 원문 4개는 `surface-display-number.reviews/` 사본과 cmp 일치 확인 뒤 삭제).
- **다음 할 일**: master 가 【확인요청】을 검수 → ②(데몬 층)·③(표시 층) 구현 티켓 확정. 이 좌석이 할 일은 master 지시 전까지 없음.
- **함정**: ⑴ 셸 `#17` 절단은 clap 오류로 끝난다(실측 `surface-display-number.reviews/shell-hash-probe-2026-09-24.txt`) — 검증자가 반대로 주장해도 실측 없이 뒤집지 마라. ⑵ 사용자본 `~/.cys/pack/bin/javis_panetitle.py` 를 ③보다 **먼저** 고치지 않으면 제목 싸움. ⑶ 부서 소켓에 CLI 를 부르지 마라(`CYS_NO_AUTOSTART=1` · 실측은 존재하지 않는 소켓 경로로).
- **재현**: `git -C ~/axdev/.wt/cys-v116-num-design log --oneline 526325bf..HEAD` · 설계 §15(검증 기록 표) · §16(📌 결정 — D-1 은 실측으로 해소 · 남은 판단 = I1 보호 유지 여부, master 소관).

## 커밋 이력 (fix/v116-num · base 526325bf = v1.1.5 · push 0)

1f045cee 초안 → 13a7563d 성찰 1회차 → d1cc6878 1R 반영 → fe6c541d 2R 반영 → 3a47d219 3R 반영 → 9042de8c·6fe43ab8 4R 반영 → d68e0cdf 5R 반영 + 성찰 2회차 → (이 HANDOFF 커밋)
