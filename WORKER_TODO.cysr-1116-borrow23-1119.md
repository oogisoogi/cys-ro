# WORKER_TODO — TICKET=cysr-1116-borrow23-1119 (worker-1116borrow23 · surface:2269)
기준점 dea2e1853 · 가지 feat/1116-borrow23 · 상한 4h · 이월 없음
비가역·비용(실행 금지): push·태그·CI·gh 쓰기·서명·발행·앱 교체·실사용 데몬/좌석

## ② 상태 판정 바로잡기(OSC 7501)
- [x] 격리 실측: 진짜 Claude Code 2.1.328 이 7501 을 내는가(무응답 0건 · 응답 시 blocked/clear/idle/working/done/clear)
- [x] 데몬: program_status.rs(파서·스캐너·저장소·요약) + reader 질의 응답·수신 + 종료/셸 복귀 지움
- [x] 데몬: activity wire 덧씌움(source·done 상태·뜻·근거) + 진단 CLI
- [x] UI: roleactivity 파서·투영(done·auth·근거) + 교차 핀
- [x] 시험(cargo cysd · bun · tsc) + 뮤턴트
- [x] codex ② 1R NOT_CONVERGED → 수리 → 2R NOT_CONVERGED(1건 수리·1건 설계대로) → 3R 01:31 대기(한도)
## ③ 가벼운 시작
- [x] 노브(기본값 = 현행 유지) + 부트/검사 경로 반영 + 지침 별도 커밋 + 기본값 제안
- [x] 팩 시험 = ci-branch.yml 팩 단계 그대로(최종 트리 재실행 중)
- [x] codex ③ 1R NOT_CONVERGED(BLOCKER1·MAJOR1·MINOR3) → 수리 → 2R 01:31 대기
## 끝
- [ ] HANDOFF.cysr-1116-borrow23-1119.md + 【확인요청】

- [x] 최종 codex = CONVERGED(b97964353) · 시험·뮤턴트 9/9 · HANDOFF
