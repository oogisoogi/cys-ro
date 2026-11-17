# WORKER_TODO — TICKET=cysr-ui-slice3-1118 (cysr 화면 개편 조각 3 · 보낸 말 단계 전부 · surface:2157)

- 브리프 = master/briefs/2026-11-18-cysr-ui-slice3.md (원장 kind=brief · spawn 경로 · body_sha256 537c8511… = 파일 rstrip sha 일치)
- 기준 = 3a012bf4 (feat/ui-slice1 수용판) · 상한 ≈03:00

- [x] 0 자료: P2 §2-5·§5-1·§5-2·§11·부록 D·D-2 · 조각1 HANDOFF · 0.5 결과 · 데몬 사건 칸 실측(queue.* · input.refused_at_write)
- [ ] 1 judge: msgstep 보강(답하는 중 = 전달 뒤 활동 · 보내는 중 3초 무응답 → 확인 중 · 쓰기 직전 거부 사건 · 같은 말 겹침 · 증거 단계 되돌림 0) + autostep.ts(기계 문안 큐 사건 → 단계)
- [ ] 2 core: 사건 받기(대화 화면 켜졌을 때만) · 겹침 붙잡음 · 무응답 타이머 · 기계 문안 추적 API
- [ ] 3 chat 화면: 오래 걸려요 + 마스터 상태 · 겹침 안내 · 기계 문안 줄 · 여러 줄
- [ ] 4 시험: §5-2 단계 표 fixture 전 행 · core 시험 · M2·M3 하네스(행방 불명 0·틀림 0) · 경합(불명 뒤 120초 안 다시 누름 = 중복 쓰기 0) · R3 30초
- [ ] 5 chat_gate.py 확장 · tickrec_gate OFF 같음 · bun 전체 · tsc · 화면 게이트
- [ ] 6 뮤턴트(단계 판정 조건 하나씩)
- [ ] 7 codex 1R
- [ ] 8 바깥 증거(격리 HOME 실제 데몬 1회) — 시간 되면
- [ ] 9 HANDOFF.cysr-ui-slice3.md · 커밋 · 【확인요청】
