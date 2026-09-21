# HANDOFF — TICKET=v114-dept-fd (cysr 1.1.4 핫픽스 · 2026-09-22)

브랜치 `fix/v114-dept-fd` ← `5b92f041`(v1.1.3 태그 커밋). 커밋 2개: `fbf8d191`(수리 1″·1‴·2·3) · 이 문서가 들어간 커밋(할 일 15·16).

## 결함과 원인(확정 범위)
- 증상(901 VM 09-22): 앱 ↻ 뒤 부서 좌석 6개 claude 기동 실패 → 빈 zsh · [DRAIN-VERIFY] 가 셸에 타이핑됨.
- claude 오류 문구(「low max file descriptors · limit 256」)는 **원인이 아니다**. 이 맥 실측: hard 가 허용하면 claude 가 soft 를 1048576 으로 스스로 올린다 · hard 256 에서도 기동 성공.
- 원인(901 VM 부록 A): 설치 직후 「cysr 데스크톱 폴더 접근」 [허용 안 함] → **앱이 띄운 사슬만** `~/Desktop/CYSjavis/<부서>` 를 못 읽음. 본부 cysd 자손(말로 만든 부서)은 읽음.
- 이 맥 대조군(권한 무변경): launchd 소생 `/bin/sh` = ~/Desktop·~/Documents 거부 · claude 자손 셸 = 둘 다 허용.

## 바뀐 것
| 수리 | 자리 | 내용 |
|---|---|---|
| 1″ | cysd `dept.run`(handlers.rs) · 앱 `run_dept_tool`(main.rs) | 맥에서 앱의 부서 데몬 기동 4경로(launch·rotate·create·allocate)를 본부 데몬 자식으로 대행. 게이트 = 본부 소켓만 · 호출자 pid 미상 거부 · 좌석(pane) 자손 거부 · 동사/이름 화이트리스트 · 180s 상한. 실패 시 앱 직접 실행 폴백. 윈 제외. |
| 1‴ | governance.rs `notify_seat_folder_denied` · ui main.ts | 역할 좌석이 비어 있고 데몬이 좌석 폴더를 PermissionDenied 로 못 읽으면 `seat.folder_denied` 좌석당 1회 → 원인 문장 토스트. |
| 2 | cys.rs `drain --hq-only` · `run_rotate` | `rotate --skip-depts` 일 때 저장 확인 = 본부 좌석만. 부서 순회 rotate 는 종전(①에서 부서 좌석 포함). |
| 3 | handlers.rs `surface.send_text` · governance `agent_seat_vacant_now` | 등록 에이전트 좌석이 「뿌리=셸 ∧ 자손 0 ∧ 뿌리≠에이전트」면 직접 주입 보류 → 큐 적재 + `inject.skipped_no_agent` + 오류 `no_agent`. |
| 15 | cys.rs `with_owner_token` · 앱 `run_sidecar_restore_report` | 앱 사이드카 `cys restore` 에 그 데몬의 operator.token 을 `CYS_OWNER_TOKEN` 으로 넘기고, inject_text 의 주입 요청 4곳이 `owner_token` 을 싣는다 → 부서 ACL `external→worker` 거부 해소(데몬은 pane 무귀속일 때만 오너로 인정). |
| 16 | lib.rs `dept_registry_cwd` · 앱/rotate ⑥ restore `--cwd` · cys-dept `dept_seat_cwd` | 부서 좌석 cwd = 레지스트리 부서 폴더(실재할 때만). restore 는 저장 cwd 가 홈·미지정인 좌석만 교정(기존 계약). allocate 빈 셸 = `CYS_DEPT_CWD` > 레지스트리 cwd > `$HOME`. |
| 기타 | lib.rs 원시 스폰 동결표 | `src-tauri/src/main.rs` 39→37(cys-dept 직접 스폰 3곳 → 1곳). |

## 미실측(정직 고지)
- **수리 1″ 는 미확정**: [허용 안 함] 상태에서 ⓐ앱 직접 ⓑ본부 대행 좌석 claude 생존 표가 없다. master 판정 = 1.1.4 절단 뒤 901 VM 재실기에서 측정. 우리 맥 `tccutil reset` + [허용 안 함] 은 라이브 기기 권한 변경 + 사람 클릭이라 기각됨.
- 16: Desktop 아래 부서 폴더는 앱 사슬이 거부 상태면 실재 검사(stat)도 실패할 수 있어 홈으로 폴백한다(좌석은 살고 cwd 만 홈).
- UI(main.ts) 추가분은 구문만 확인 — 워크트리에 ui/node_modules 가 없어 형검사 미실행.
- 【모의】 격리 하네스는 가짜 cys-dept·원시 RPC 로 사슬·ACL 만 쟀다(실 claude·TCC 미포함).

## VM 표에서 읽는 자리
- `~/.cys/dept-launch-path.log` — 한 줄 = `<시각>\t<cys-dept 인자>\tpath=delegated|direct:<사유>`(사유 = `not_macos` · `rpc_error:<문구>`).
- 이벤트 `dept.launch.path`(본부 데몬 · 대행 경로) · `seat.folder_denied`(부서 데몬 · 폴더 거부 좌석) · `inject.skipped_no_agent`(빈 셸 주입 보류).
- 부서 좌석 사슬 판별: `ps -o pid,ppid,command` 로 부서 cysd 의 부모가 본부 cysd(대행) 인지 launchd/앱(직접) 인지.
- 재설치 드레인: 설치기 로그 「저장 확인 N/M」 의 M 이 본부 좌석 수(3)면 수리 2 동작.

## 시험(이 워크트리 실측 · 마지막 코드 편집 뒤)
- `cargo test --lib` 529/0 · `--bin cysd` 1008/0(fbf8d191 시점 · 이후 cysd 무변경) · `--bin cys` 278/0 · `cys-app --bins` 162/0.
- 뮤턴트 9/9 KILLED(M1~M7 = fbf8d191 · M8 owner_token 미부착 · M9 레지스트리 cwd 실재 검사 제거).
- 게이트: gen_ceo_template --check GREEN · bootv2_doc_contract · event_inject · CI 팩 목록 44/44(fbf8d191 시점) · test_dept_request·dept_name_guard OK(최종) · secret-scan.
- 알려진 이 기기 한정 적색: `factory_reset::tests::execute_moves_writes_manifest_and_is_rerun_safe` — 기준선 5b92f041 에서도 실패(master 실측) · 내 최종 실행에서는 통과(환경 의존).

## 함정
- 격리 cysd 소켓은 `<tmp>/cys/cys.sock` 모양이어야 본부로 판정된다(`socket_is_base`) · debug cysd 기동은 10초 이상 걸릴 수 있다.
- 같은 프로세스가 만든 좌석에 그 프로세스가 보내면 `creator` 등급으로 ACL 이 열린다 — ACL 시험은 별도 프로세스로.
- 뮤턴트 대상 문자열이 시험 핀에도 있으면 프로덕션(첫 등장 · tests 모듈 앞)만 변이하라.
