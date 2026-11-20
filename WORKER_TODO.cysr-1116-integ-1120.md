# WORKER_TODO — TICKET=cysr-1116-integ-1120 (worker-1116integ · surface:2321)

브리프 = ~/axdev/master/briefs/1116-full/integ.md (원장 13:29:41 spawn · submitted true) + _common.md
가지 integ/1116-r1120 ← dea2e1853 · 상한 4시간(13:29 ~ 17:29) · CTX 60% 매듭

## 준비
- [x] 원장 대조 · 13갈래 머리 = 브리프 커밋 일치 · 전부 dea2e1853 위
- [x] 갈래별 바뀐 파일·겹침 표(asset ⊂ skillrev 확인)
- [x] target APFS 복제(cys-1116-integ 에서)
- [x] 기준선 시험 숫자(dea2e1853): cargo 대상별 목록 수 · bun · 팩 시험 파일 수
- [x] 갈래 HANDOFF 사실 추출(서브에이전트 → scratchpad/lane-facts.md)

## 병합(--no-ff · 표 순)
- [x] 1 debt-u e0953c7e0
- [x] 2 flaky 7dd80224e
- [x] 3 ccopen 88def9658
- [x] 4 asset-skills 1ff82d08a
- [x] 5 skill-revisions f9ed0fcac
- [x] 6 b23 33a72a906
- [x] 7 debt-d e5c0d229f
- [x] 8 skt1 b03d1cd70
- [x] 9 s79 f51261ee0
- [x] 10 s2 06711fbc9
- [x] 11 s5 305f08930
- [x] 12 s6 94ddcd1cf
- [x] 13 seatkeep 9b591371b

## 게이트·점검
- [ ] 전체 게이트(docs/integ-1116/gate-1116.sh)
- [ ] 부하성 시험 load<15 단독 3회(test_9b · dept_name_guard · c6_reap · seatkeep_input_ack_stall · k17)
- [ ] 시험 숫자 전후 표
- [ ] git grep -c oogisoogi = s5 예외 목록 대조
- [x] 의미 충돌 점검(병합 중 6건 고침 · 아래 HANDOFF)(입력 게이트 s5↔seatkeep↔s6 · 업데이터 debt-d↔skt1↔seatkeep)
- [ ] HANDOFF.cysr-1116-integ-1120.md · 【확인요청】
