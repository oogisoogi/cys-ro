# HANDOFF — 갈래 brand (TICKET=cysr-117-impl-brand · 브랜치 fix/117-brand · 기준 1bc32693)

- 좌석: worker-117brand(surface:1153 · 계정2) · 착수 19:18 · 이 문서 19:58(CTX 48.9% jsonl) · push = 아직 0(게이트 뒤 fix/117-brand 만 · force 금지)
- 원장: 브리프 master#4995aa0e · 확인 요청 1 master#6c71c56e · E3·E2 답 master#bd7a4a80(둘 다 A)

## 끝난 것(커밋)
| 항목 | 커밋 | 요지 · 시험 |
|---|---|---|
| ⑱ | 84c7c6e9 · cd90bf87 · 559fd8fe | 5자리 「cysr 는 cys 터미널(github.com/idoforgod/cys-terminal)에서 출발했습니다.」 · 결박 = test_default_fleet_formation ⓕ(128/128) + ui brandbadge.test.ts · LICENSE 3번째 줄 = sha256 핀 |
| E1 | 53db36a0 · 3ee779dd · (문서) E1-VERSION-CONSUMERS.md | clap name·bin_name = cysr(시험 cysr_alias_version_and_help_do_not_follow_argv0) · 맥 번들 링크 Contents/MacOS/cysr -> cys(mac-bundle-common.sh mac_link_cli_alias · scripts/tests/test_mac_cli_alias_link.py 5) · 소비처 21행 깨짐 0 |
| ② | 13db62de | ui/src/droppoint.ts(맥 = 나누지 않음) · droppoint.test.ts 5 · UI bun test 1465/1465 |
| G | 59574225 · 1656f861 | suggest-folder · propose --folder · folder_problem · javis_org 결속 = 끝 이름 = 표시명 · test_dept_request 84+ · 뮤턴트 M12·M12b·M12c |
| E2 | 96b5fad9 | 훅 POSTINSTALL UninstallString /P · 모델 재핀 · 컴파일 하네스 초록 |
| E3 | 35cda68d · 67969aa3 · e6909b2d | src-tauri/nsis/installer.nsi(원문 + AutoGui 30줄) · 다운그레이드 = 원래 화면 · check.py(P1~P4 · S1~S7·S3b · N1~N5) · ci-branch nsis 잡 배선 · windows-build T8 |

## 로컬 게이트(19:58 기준)
- ✅ cargo test --bin cys 340/340(E1 뒤 · 그 뒤 Rust 변경 0) · ✅ UI bun test 1465/1465 · ⚠ UI typecheck 적색 2 = 기존(restorebrief·updateplan · master 기록함)
- ✅ nsis-hook-compile · nsis-hook-model(39082) · nsis-template/check.py · secret-scan --all clean
- ⏳ 팩 파이썬 CI 루프 전량(백그라운드) · ⏳ mut_dept_request 전량(백그라운드 · 옛 M12 로 시작했을 수 있음 → `--only M12,M12b,M12c` 재실행 필요)
- 미실행: cargo test --lib/--bin cysd/-p cys-app(이 갈래 Rust 변경 = cys.rs 뿐) · run_bootstrap_health 전량 · 윈 CI(push 뒤 T8)

## 미완 · 다음
1. 적대 검증 R1(agy + Fable · 스냅샷 scratchpad/snap · 프롬프트 scratchpad/review-prompt.md) — 첫 두 번은 권한 설정 실수로 빈 출력, 세 번째 진행 중.
2. 게이트 마저 → push fix/117-brand → CI(ci-branch · windows-build T8) run id.
3. 【확인요청】 머리 3줄(끝낸 항목 · 남은 위험 · 확신도) + 경과 시간.

## 함정
- NSIS 훅은 .gitattributes eol=crlf — 파이썬으로 고치면 작업 트리가 LF 가 된다(블롭은 정규화라 무해 · 검사기는 CRLF 체크아웃에서도 초록 확인).
- 검사기 P4 는 difflib 정렬 순서 그대로의 삽입 목록 — 템플릿을 고치면 /tmp 생성기 없이 목록을 다시 떠야 한다(삽입 줄을 원문 대비로 출력해 붙인다).
- macOS 에 `timeout` 명령 없음 · Fable 헤드리스는 프롬프트를 stdin 으로(--allowedTools 가 가변 인자라 프롬프트를 먹는다) · agy 는 명령 권한 자동 거부 → 파일 읽기만 하도록 diff 파일을 준다.

## 남은 위험(보고용)
- E2: 제거 화면에서 「앱 데이터까지 지우기」 선택이 사라짐(완전 삭제 = 설치기 reset-clean) — master 가 박사님께 고지.
- E3: 템플릿 전체 컴파일·실행은 이 맥에서 불가 → windows-build T8 이 첫 실증 · SmartScreen 1장 잔존(서명 없음 · 원칙).
- E1: 창 밖 터미널(Terminal.app)의 cysr 는 여전히 「CLI 설치」(관리자 창 1) 필요.
- ② 맥 실기 좌·우 드롭 미실행(발행 전 master 게이트).
