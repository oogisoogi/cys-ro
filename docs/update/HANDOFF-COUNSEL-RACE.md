# HANDOFF — TICKET=cysr-118-counsel-race (상담소 수집기 윈 교차 잠금 경합 시험 간헐 적색)

좌석 = surface:1296(297) · cwd = ~/axdev/.wt/cys-118-counsel · 가지 `counsel/race-118` off `5ff5ca89`(merge/v0.14.43)
브리프 = `~/axdev/master/briefs/2026-10-07-cysr-118-counsel-race.md` · 발주 master#2029e637(원장 일치 16:58) · 착수 17:0x · 상한 3h
미러 push = `fix/counsel-race-118` 1가지만 · 본 가지 push 0 · 맥 러너 반복 0(윈만)

## TODO
- [ ] 1. 실패 3런 실측(누락 수·위치·소요) — 누락 꼴이 「한 줄 유실」인가 「덩어리 누락」인가
      해소 판정: 3런 로그의 누락 수 · 「additional elements」 숫자 표
- [ ] 2. 대조군(맥) — 같은 시험 반복 N회 · 적색 수
      해소 판정: 「맥 N회 중 M회 적색」 수치
- [ ] 3. 윈 재현 + 계측(쓰는 쪽 반환값·대기 시간 · 옮기는 쪽 잠금 보유 시간 · 실패 시 두 파일 덤프) — `[skip ci]` 커밋 + windows-health 수동 발화(프로브 전용 · 맥 러너 0)
      해소 판정: 「윈 N회 중 M회 적색」 + 누락 줄 = 「잠금 상한 초과로 버린 쓰기(반환 0)」 인지 「쓴 뒤 사라진 줄(반환 1)」 인지 대응표
- [ ] 4. 원인 명명(재현 뒤에만) → 실결함 수리 또는 시험 수리 · 뮤턴트(잠금 제거) 적색 실측
      해소 판정: 수리 뒤 윈 반복 N회 0 적색 + 뮤턴트 적색
- [ ] 5. 임시 워크플로·프로브 제거 → 미러 push 1회 → CI 3런 success → 【확인요청】(사용자 체감 영향 1줄)
      해소 판정: `git diff 5ff5ca89 -- .github` = 0 · gh run list 3런 success
