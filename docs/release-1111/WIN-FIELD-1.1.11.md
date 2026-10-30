# WIN-FIELD-1.1.11 — cysr 1.1.11 윈도우 실기 확인점(씨앗)

- 형식 = `docs/release-1110/WIN-FIELD-1.1.10.md` §1 표와 같다(ID · 출처 · 무엇을 · 어떻게 · 통과 기준 · 맥/비고).
- 이 파일은 TICKET=cysr-1111-fable-fixes 가 **처음 만든 씨앗**이다(2026-10-23 · 1.1.11 용 WIN-FIELD 파일이 저장소에 없었다).
  1.1.11 의 다른 가지(trash-preview T1 V1 절차 · installer §6 · winq2 HANDOFF §4-1)의 항목은 아직 옮겨 오지 않았다 —
  발행 준비 티켓이 이 표에 합친다(이 파일의 행은 지우지 말고 그 옆에 붙인다).
- 출처 보고서 = Fable 적대 검토 `~/axdev/master/reports/fable-debug-1022/cysr-1111.md`(이하 「Fable」) · 수리 = `docs/HANDOFF-cysr-1111-fable-fixes-2026-10-23.md`.

## A. fable-fixes — 6

| ID | 출처 | 무엇을 | 어떻게 | 통과 기준 | 맥 / 비고 |
|---|---|---|---|---|---|
| FABLE-F1 | Fable F1 · 커밋 `857cd6d2` | 좌석 순환(`cys cycle-agent`)의 유휴 판정이 물리 행 재료(`layout_text`)로 composer 를 읽는다 — 윈 fullscreen 좌석에서 「빈 composer 인데 영구 보류」·「화면 초안인데 유휴」 둘 다 없어야 함 | **제안**(⚠순환은 그 좌석 대화를 지운다 — 시험 좌석에서만): WG-2 좌석(fullscreen claude)에서 ① 입력줄 비움 → `cysr cycle-agent --role <역할>`(또는 autopilot 1회) ② 입력줄에 글자 몇 개 친 채로 같은 명령 | **제안**: ① 순환 진행(rc 84 「cycle-target-busy」 · rc 85 「cycle-human-draft」 없음) ② rc 85(초안 보호) · 친 글자 그대로 | 맥 = 시험 `f1_cycle_idle_reads_physical_rows_of_a_wrapped_composer`(합성 화면) · 원인 확증(ConPTY 가 괘선 뒤를 이어 보냄)은 WINQ-2 와 같은 한계 — WINQ-2 화면 사본을 같은 좌석에서 함께 뜨면 한 번에 잰다 |
| FABLE-F2 | Fable F2 · 커밋 `11e774eb` | 휴지통 「크기 미리 보기」가 `.producer-<pid>` 상태 `open` + **죽은 생산자** 항목도 크기를 잰다(종전 = 윈 생존 판정 불가로 영구 「생산자 표식 상태 … 거부」) | **제안**: trash-preview HANDOFF §T1 「1.1.11 윈 실기 확인 절차」 1~7 을 그대로 하되, 고르는 항목 중 하나를 **중단된 부서 생성 잔재**(안에 `.producer-*` 파일이 있고 그 `pid` 가 지금 없는 것 · `Get-Process -Id <pid>` 가 오류)로 고른다. 그런 항목이 없으면 수집만(없음 기록) | **제안**: 그 항목 줄에 크기·개수가 나오고 칩 = `producer did not finish (interrupted)`(종전 윈 = `producer liveness undeterminable (treated as running)`) · 「생산자 표식 상태」 거부 문구 없음 · 파일 보존(§T1 7) | 맥 = 시험 `list_maps_a_live_and_a_dead_producer_pid_to_running_and_interrupted`(전 플랫폼으로 풀림 · 윈 CI 에서 처음 돈다) · win-typecheck rc 0 |
| FABLE-F2b | Fable F2 「추가로」 | 윈에서 휴지통 뿌리 신원(`RootDir` dev/ino)이 전부 `(0,0)` — 미리보기 B2 「뿌리 바꿔치기」 검사는 윈에서 **항상 통과**(검사 없음과 같다) | 실기 대상 아님(해석) — 알려진 한계로 기록 | 「윈 미리보기에 뿌리 바꿔치기 검사가 있다」고 적지 않는다 | 미리보기 전용(삭제 0)이라 피해 없음 · 윈 삭제를 켜는 판에서는 선결 |
| FABLE-F4 | Fable F4ⓑ · 커밋 `58684e16` | 설치기 POSTINSTALL dist-info 정리(`cys-runtime-prune.ps1`)가 **ConstrainedLanguage** 기계에서도 돈다(종전 = `stopped` 1줄 · 정리 0) | **제안**: 같은 판 설치 뒤 설치 로그에서 `cys-runtime-prune:` 줄 확인(보통 기계) · AppLocker/WDAC 기계가 있으면 그 기계에서도 | **제안**: `cys-runtime-prune: stale-dist-info removed=N failed=0 …` · `stopped (` 줄 없음 | 맥 = 하네스 N11 inst4(pwsh 7.6 언어 모드 강제 · removed=3) · Windows PowerShell 5.1 실측 0 |
| FABLE-F4a | Fable F4ⓐ | GPO 실행 정책(AllSigned/Restricted)·AppLocker 가 `%TEMP%` 도우미를 막는 기계 = 같은 바이트 재설치도 매번 3종 스왑 · 실행 중 cysd 이미지 `.prev`→`.prev2`… 슬롯 생김 | 그런 기계에서만 관측 — 수리 대상 아님 | **정상**으로 분류(안전 쪽 비용 · cysd 스윕이 회수 · 종료코드 0) | 하네스 N9·N10 = 설계대로 |
| FABLE-F5 | Fable F5 · adv-fixes #8 | 같은 판 재설치 + AV·인덱서가 쥔 낡은 `cys.new.exe` = `placement-refused: cys.exe(stale-new-locked)` · `cys-install-failure.txt` · exit 4 | 관측되면 기록 — 재실행으로 풀림 | **정상**(거부 · 루프 아님 · 재실행 rc 0)으로 분류. 종전(1.1.10) 은 같은 경우 exit 0 이었다 | 코드 변경 0 — 처분 = HANDOFF §2 |
