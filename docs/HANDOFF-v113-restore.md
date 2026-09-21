# HANDOFF — TICKET=v113-restore (1.1.3 트랙 D · rotate 윈 · 복원 정직 알림 · 데몬·앱 소수정 · 배달 큐)

브랜치 `fix/v113-restore` (← 11845981 · v1.1.2 발행본) · 워커 surface:897 · 2026-09-21

## 커밋
| sha | 항목 | 내용 |
|---|---|---|
| 9c23f7e5 · 9492b7d5 | B1 | rotate 윈 stage 2 멈춤 — 표준 핸들 상속 봉인 + 단계 호출 파일 캡처 · 윈 대조군 시험(+ 원시 Command::new 동결 계수 복귀) |
| d648101b | 배달 큐 | 대체화면 claude 좌석 큐 영구 미배달 — 가로줄 사이 입력창이면 배달 · 보류 사유 분리 |
| 799b9dbe | B4 | 앱 본부 복원 알림 — 15s 뒤 1회 재실행 · 실제 사정만 말함 |
| e330cbac | B6 | death:master 오판 — 좌석 뿌리 argv 도 엄격 관측 |
| 73781a0e | B10 | 윈 콘솔 깜빡임 판별 프로브(docs/diag/win-flicker-probe.ps1 · 코드 수리 보류) |
| 5b147597 · 14d22ccc | B3 | ↻ 갱신 직후 「복원 중 — 건너뜀」 자리만 30s 뒤 재저장(`drain --verify --only`) |
| a5c6c1b6 | 항목2 | rotate ⑥ 부서 순회 |
| — | B8 | 코드 변경 0 — v112-wake 로 해소 확인(아래) |

## 원인과 수리 — 항목별
### B1 rotate 윈 stage 2(316s 상한)
- 【확정 · 윈 CI 대조군】 ②에서 옛 데몬 taskkill → `cys identify` 자식이 새 cysd 를 자동 기동 → 윈 `CreateProcess(bInheritHandles=TRUE)` 로
  cysd 가 부른 쪽(rotate·설치기)의 **출력 파이프 핸들**을 상속 → `.output()` 이 EOF 를 영원히 못 받음. `daemon install` 은 schtasks 등록만(기동 없음).
- 대조군 = `src/lib.rs` `win_std_inherit_tests`(봉인 없음 ≥10s 멈춤 재현 · 봉인 <8s) · windows-health 스텝 「cargo test --lib win_std_inherit」 = run 35610595025 에서 success(3 passed 단언).
- 수리 ① `cys::seal_std_handles_from_inheritance()` — cys main 첫 줄 · 윈 전용(자기 표준 핸들 HANDLE_FLAG_INHERIT 해제 · Rust `Stdio::inherit` 은 상속 사본을 새로 만들어 `cys run` 무영향)
  ② rotate 단계 호출 전부 `output_via_file`(임시 파일 캡처).
- 맥: 파이프 캡처로 되돌리는 뮤턴트가 unix 손자(`(sleep 12 &)`)에 12.09s 막힘 — 같은 모양의 unix 판 대조군.

### 배달 큐 prompt_not_ready(윈 CSO 미배달 2건)
- 【관측·대조군】 prompt_not_ready 는 입력줄이 빈데 준비 아님 전부(마커 부재·대체화면·승인 대기)를 한 말로 적었다. 격리 cysd 에 같은 가짜 claude 좌석을
  대체화면만 달리해 세움 → ALT=0 통과 · ALT=1 prompt_not_ready. 【추정】 윈 = D5 옵트인이라 claude 본 화면이 대체화면 → 대체화면 축이 영구 차단.
- 수리: 커서 행이 가로줄 두 개 사이 빈 「❯ 」면 대체화면이어도 배달(`alt_screen_blocks`·`is_rule_row`) · 사유 = `alt_screen(…)`/`approval_pending(…)`/`prompt_not_ready(…)`.
- 확정 판정법: 윈 실기에서 CSO 좌석 `cys queue list --json` 의 blocked_by 가 1.1.3 뒤 `alt_screen(…)` 으로 찍히지 않고 배달되면 해소.
- 넣지 않은 것: 대기 상한·세대 폐기(메시지 폐기 = 유실 · 기존 queue.starved 경보가 대기 상한 역할).

### B4 「복원 실패 — 본부 노드 복원 실행 실패」
- 【관측】 이 문구는 phoenix exit=3 이 아니라 앱 `spawn_org_restore` 가 사이드카 `cys restore --include-master` rc≠0 을 보고 냄. cys restore 는 실패 또는 관문 보류가 하나라도 있으면 1.
- 수리: 첫 실행 실패면 15s 뒤 1회 재실행(복원 멱등) · 그래도 실패면 요약 줄(`restore 완료: 재기동 N · 실패 N · 관문 보류 N`)로 실제 사정만 — 제목 「본부 복원 확인 필요」.
  요약 문장 드리프트 핀 = cys-app 시험이 cys.rs 문자열을 include_str 로 대조.

### B6 death:master 오판
- 【관측 = 코드 확정】 893 VM: surface pid 1754 자체가 claude(`Ss+`) = 설치기 master 는 셸 없이 claude 가 페인의 직접 프로세스. 좌석 판정은 셸 자손만 봐서 빈 자리 → AgentNeverStarted.
- 수리: `root_agent_cmd` — 뿌리 argv 가 기지 에이전트와 엄격 매칭이면 관측(좌석 캐시·생존·윈 claim_role 확정·무meta 관측 4곳). 생존 판정은 그 좌석 meta 의 에이전트로만 좁힘.

### B8 supervisor 만료 통지
- ⓐ 정상 기동 뒤 30분 만료 = 주입 0 — v112-wake 로 해소(시험 `running_intent_past_ttl_retires_quietly_but_pending_expiry_stays_loud` · 뮤턴트 KILLED).
- ⓑ 진짜 무산 통지에 대한 master 반응 규칙 = 팩에 없음 → 트랙 P 에 MASTER_DIRECTIVE 문구 요청 중계(①기계 통지 줄은 사람 요청 아님 ②origin 표에 `supervisor`).

### B10 윈 콘솔 깜빡임
- Rust 스폰 전수 점검 = 콘솔 없는 부모(cysd·앱)의 자식은 전부 hidden_command/no_console · cysd·앱은 windows_subsystem. 1.0.1 NOWIN 뒤에도 재현 → 스폰원이 Rust 밖일 가능성(훅 `sh cys-hook.sh`·HUD 브리지·아고라 상주).
- 추정 수리 금지 → `docs/diag/win-flicker-probe.ps1`(1초 간격 새 프로세스 + 부모 이름·명령줄 → 바탕화면 tsv) 박사님 실기 1회로 스폰 주체 확정 후 수리.

### B3 ↻ 갱신 직후 건너뜀
- 수리: `cys drain --verify --only <dept>/<surface:N>`(반복) 신설 · UI ↻ 흐름이 `skipped_restoring` 자리만 30s 뒤 재저장 → 결과 병합(`mergeRetry`) → 재시작. 남으면 종전 알림 1줄.
- 해소 판정: 갱신 직후 복원 중 ↻ → delivery-base.jsonl `[DRAIN-VERIFY]` 3자리.

### 항목2 rotate 부서 순회
- 수리: rotate ⑥ — 본부 rotate 에서만, depts.json 에 있고 살아 있는 부서마다 `bash cys-dept rotate <이름>` + 그 부서 소켓 `cys restore --include-master`(앱 rotate_dept_daemon 과 같은 두 단계 · 같은 env SOT `spawn_env_pairs_from_process`). 부서 실패는 rc 25. 죽은 부서는 되살리지 않음(앱과 같은 규칙).
- 트랙 P 문구 요청 불요(구현됨). 단 「부서 레인 순회 없음」 고지 문구(A5)가 있으면 이제 거짓 — 트랙 P 확인 필요.

## 증거 요약
- 시험: cys `rotate_`·`drain`·`v113_` · cysd `v113_`·`b1_`·`deadman`·`seat_agent`·`liveness`·`running_intent_past_ttl` · cys-app `v113_` · UI bun drainverify 13/13 · `cargo test --lib` 528/528.
- 뮤턴트: B1 3 · 큐 5 · B4 4 · B6 4 · B8 1 · B3 6 · ⑥ 4 = 27/27 KILLED(생존 1건은 핀 추가 뒤 KILLED).
- 격리 실측(맥 · /tmp 격리 cysd · 라이브 무접촉): 큐 = 새 cysd 에서 테두리 있는 대체화면 좌석 통과 / 없는 좌석 alt_screen 보류.
  rotate(비-기본 소켓 · 가짜 좌석 3 · 파이프로 받음) = 114s 완주 · 데몬 pid 970→2926 · rc=25(복원 = held_input_not_ready — 격리 HOME 에 로그인된 claude 가 없어서 · 하네스 한계).

## 미실측 · 잔여 위험
- 실 claude 좌석 3 격리 rotate·↻: 로그인된 claude 설정 폴더가 라이브(~/.cys/claude)뿐이라 이 기계에서 불가 → VM 실기(S1·S2)로 넘김.
- 윈 전 경로(B1 실기 rc 0/21 · 큐 alt_screen · 깜빡임 프로브) = 박사님 실기.
- 대체화면 입력창 모양(가로줄 두 개 사이 「❯ 」)은 submit_probe 모듈 doc 의 09-21 실기 서술에 기댄다 — 윈 대체화면 claude 화면 실측은 아직 없음. 모양이 다르면 여전히 보류(안전한 쪽).
- B4 재실행 15s·B3 재저장 30s 는 실측 계수 없음(893 「갱신 직후 40s」 관측에서 잡은 값).
- rotate ⑥ 은 기본 소켓 rotate 에서만 돈다 — 이 기계에서 기본 소켓 rotate 는 라이브를 건드려 실측 불가(순수·배선 시험만).
- 윈 rotate 임시 캡처 파일: 손자 cysd 가 상속 핸들을 쥐면 삭제 실패로 %TEMP% 에 0바이트 파일이 남을 수 있음(무해 · 봉인 뒤로는 상속 자체가 없어야 함).

## 이종 검증(agy)
- 1R(e2d01015 · diff 만 · 파일 도구 없음) = ACCEPT · findings [] — **불채택**(master 판정 [master#dae1e92f]): 연 파일 0 · 인용 줄번호 어긋남 · 핵심 논점 미검토.
- 2R(같은 커밋 detached 사본 · `--add-dir --sandbox` · 4영역 반례 요구) = **REVISE**. 반례별 처분(코드 대조):
  - A B1 봉인(lib.rs 표준 핸들만 봉인 · 부모가 넘긴 비표준 상속 핸들은 샌다) → **부분 인정 · 잔여 위험**. cys 안에서 부모가 넘긴 미지의 상속 핸들은 열거·봉인할 수단이 없다(std 의 PROC_THREAD_ATTRIBUTE_HANDLE_LIST 는 불안정 API). 관측된 설치기→rotate 파이프는 rotate 의 표준 핸들이라 봉인 대상이다.
  - B ⑥(부서 소켓 rotate 도 base=true 라 다른 부서를 건드린다) → **기각**: base = `cys::lane::socket_is_base(socket_path)`(cys.rs run_rotate) · rotate_state_root 는 표식 폴더에만 쓰인다.
  - C 큐(가로줄 사이 빈 「❯」 모양의 메뉴에 오주입) → **인정·봉합 f9e6f07e**: 커서 행 전체가 마커 뒤 공백일 때만 입력창(선택 메뉴 `❯ 1. Yes` 차단) · 시험 `v113_alt_screen_framed_menu_row_still_blocks` · 조건 제거 뮤턴트 KILLED.
  - D B3(재시도 exit 1 이면 앱이 예외로 결과를 버린다) → **기각**: 앱 `drain_verify` 는 stdout 이 JSON 이면 종료코드와 무관하게 Ok(JSON) · `run_drain_verify` 는 보고를 찍은 뒤 1 을 돌려준다.
- 2R 의 files_read = `src/bin/cys.rs:1367-14532` 뿐 — A·C·D 는 diff 기반 지적이었다. 스냅샷 git status 깨끗(무쓰기 실측).
