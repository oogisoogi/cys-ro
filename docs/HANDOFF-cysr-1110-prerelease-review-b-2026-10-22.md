# HANDOFF — cysr 1.1.10 발행 전 정밀 검토 B (원작자 병합 충돌 해소 · 병합 후속)

> TICKET=cysr-1110-prerelease-review-b · 2026-10-22 02:44~ · worker-3(surface:1552) · 가지 `fix/1110-prerelease-review-b` ← `1c2f3a14`(rel/1.1.10)
> 범위 = 원작자 병합 `ba38b6aa`(v0.14.49~51 · 충돌 26파일 46덩어리) + 병합 후속 `234fc129`·`2b2179b7`·`d8e28331`·`8c2e1a24`.
> 브리프 = `~/axdev/master/briefs/2026-10-22-cysr-1110-prerelease-review-b.md`(원장 body_sha256 af2fa801… 대조 성립).
> 판단 = master#4e61b71e(02:54 · 원장 대조 성립 — nonce·대상 surface:1552·제출 yes·내 질문 push 02:54:20 이후): Q1=B · Q2=B.
> push 0 · 태그 0 · 판번 0 · 앱 설치/교체 0 · 발행 0.

## 1. 어떻게 봤나

| 갈래 | 방법 | 누가 |
|---|---|---|
| UI(main.ts 10덩어리 · index.html · style.css · resetconfirm · alertquiet · starved 시험) | `git show ba38b6aa --cc` 전수 + `git diff ba38b6aa^1 ba38b6aa`(우리 쪽에서 사라진 줄 전수) · 화면 코드가 `getElementById("x")!` 로 찾는 요소가 index.html 에 다 있는지 스크립트 대조(빠짐 0) · 사용량 패널 배선 줄 수 병합 전후 같음(9=9) | 나 |
| Rust(cys.rs · cysd approval/delivery/governance/main/handlers · src-tauri main.rs · trash/factory_reset/pack/s5) | 원작자가 더한 줄(v0.14.48..v0.14.51)이 HEAD 에 있는지 파일별 대조 · 병합이 우리 쪽에서 지운 줄 전수 · invoke_handler 중복 등록 검사 · 소비자 grep | 서브에이전트 1(읽기 전용) → 내가 근거 재확인 |
| 팩·CI·문서(cys-dept · javis_org · run_bootstrap_health · CEO/CSO 지침 · 워크플로 3 · USER-MANUAL · RELEASE.md) | `bash -n` · `py_compile` 29개 · CI 가 부르는 시험 파일 실재(`ls`) · 원작자 신규 시험 등재 · `gen_ceo_template.py --check` · NOWIN 누락 검사 · 원작자 시험 20여 개 실행 | 서브에이전트 2(읽기 전용) → 내가 근거 재확인 |

이미 한 검토(codex 1R vendor B1·M2 · trash-harden 4R ACCEPT)는 다시 하지 않았다 — 「시험이 녹인데도 틀린 것」만 찾았다.

## 2. 지적표

| # | 자리 | 무엇이 | 사용자가 언제 겪나 | 확신 | 처리 |
|---|---|---|---|---|---|
| R1 | `cysjavis-pack/bin/cys-dept:3445`(reap 휴지통 블록) · `src/bin/cysd/trash.rs:1631` · `Cargo.toml` `trash_win_validated` | 원작자 S8 로 reap 의 14일 `rm -rf` 가 「TRASH-OLD 표시만」이 됐는데, 윈도우는 앱 휴지통 삭제가 기본 꺼짐(워크플로 어디서도 안 켬) ⇒ **윈 1.1.10 = 격리분을 줄일 길이 0**. 병합 전 주석: 「transcripts.db(부서당 최대 324MB)가 무한 누적 · 이 sweep 가 유일한 회수 경로」 | 윈도우에서 부서를 만들고 닫거나 완전 초기화를 할 때마다 `%USERPROFILE%\.local\state\cys-trash` 가 줄지 않고 커진다(1.1.9 는 14일 뒤 줄었다) | 상 | **수리**(Q1=B) — §3-2 |
| R2 | `ui/src/main.ts` feed.item.created 분기(원작자 TOAST R2) | `cys feed push --wait` 대기 항목(auto_route 아님)에 OS 배너 직접 호출이 새로 붙음. 원작자는 토스트를 끄므로(true) 배너가 대신이지만, 우리는 토스트를 켜 두므로(false) **토스트 + OS 배너 둘 다** — 1.1.9 는 토스트만. 판정표 A안 「현재 화면 동작 유지」와 어긋남 | 허락을 기다리는 요청마다 컴퓨터 알림이 하나 더 뜬다 | 상(동작) · 영향 하 | **수리**(Q2=B) — §3-3 |
| R3 | `src/bin/cys.rs:11152`(CLI `factory-reset` 계획 출력) | 원작자 S8 이 화면 세 곳의 「약 14일 뒤 소거」 약속은 지웠지만 CLI 계획 출력 1줄은 원작자 v0.14.51 에도 남아 있었다(우리 병합이 그대로 받음) | `cysr factory-reset --plan` 을 본 사용자가 「14일 뒤 저절로 지워진다」고 믿는다(맥에서는 실제로 영구 보관) | 상 | **수리** — §3-1 |
| R4 | `src/bin/cysd/delivery.rs:195-224` 주석 · `:2579-2591` 시험 실패 문구 | 충돌 해소에서 우리 `MAX_PARTS = 6000` 을 지켰지만 원작자 S73 단락(「4000 → 4016」·「1 단위만 늘어도 적색」·「여유 0」·「처방은 0.14.52 포맷 압축」)이 그대로 붙음 — 우리 바는 6000/4 = 1,500 단위 | 사용자 영향 0. 이 핀이 언젠가 붉어지면 관리자가 틀린 처방을 읽는다 | 상 · 영향 하 | **수리**(주석·문구만) — §3-4 |
| R5 | `cysjavis-pack/bin/tests/test_cso_directive_rev.py:2452-2454` | 지침 바이트 상한 래칫이 원작자 재기준선(59,715 / 100,723 / 116,357)으로 느슨해짐 — 우리 실측 57,687 / 84,987 / 100,473 · 병합 전 CSO 상한 57,347(여유 0) | 사용자 영향 0. 앞으로 지침이 CSO ~2KB · MASTER/CEO ~15KB 늘어도 시험이 빨개지지 않는다 | 상 · 영향 하 | **미수리 · 다음 판 후보**(시험 전용 · 같은 시각 review-a 가지가 지침을 만질 수 있어 상한을 지금 조이면 그쪽이 헛되이 적색 — §5) |
| R6 | `src/bin/cys.rs:3498` `fleet_unreachable_to` | `ALERT_PROSE_QUIET=false` 여도 `cys fleet` 텍스트의 도달불가 부서 표시가 한 줄 → 두 줄(머리줄 + `   ⚠ 도달불가: …`) | 눈으로 보는 모양만. 팩 소비자는 전부 `fleet --json`(grep) | 상 · 영향 하 | 불성립(결함 아님 — 원작자 구조 수용의 모양 변화 · 기계 판독 0) |
| R7 | `src/bin/cys.rs:10794` · `src/pack.rs` `hooks_rel_confined` | `cys doctor` 팩 드리프트에 hooks/ WARN 신설 — `~/.cys/pack/hooks` 가 심링크인 기계는 모든 훅이 「판독 불가」 WARN | 일반 설치는 해당 없음(이 기계 실측: 심링크 아님) | 중 · 영향 하 | 불성립(일반 설치 0 · 개발자 연결 전용) |
| R8 | `cysjavis-pack/bin/javis_dept_request.py:1409` `_move_to_trash` | 우리 넷째 휴지통 생산자(`formation-YYYYmmdd-HHMMSS`)가 원작자 계약(생산자 셋) 밖 — `.producer` 표식 없음 · 이름 끝이 6자리라 `stamp_epoch_from_name` 이 나이를 못 읽음 | 「생산자 알 수 없음」은 삭제를 막지 않고(`producer_blocks(Unknown)=false` · `trash.rs:2711` 시험) 목록·삭제 됨 — 「오래됨」 표시만 안 붙는다 | 중 · 영향 하 | 불성립(삭제·표시 동작은 정상 · 나이 표시만) → 다음 판 후보 |
| R9 | 윈도우 휴지통 + 생존 판정 불가(`trash.rs:2415` 「판정 불가 = 삭제 차단」) | 윈도우에서 프로세스 생존 판정을 못 해, `trash_win_validated` 를 켜는 날 실패 경로에서 남은 `open` 표식 항목은 앱에서 영구히 못 지운다 | 지금은 윈 삭제가 꺼져 있어 0 | 중 | 다음 판 후보(그 feature 를 켜는 판의 선결 조건) |

확인했고 이상 없는 것(요지 — 서브에이전트 보고 원문은 이 세션 대화에만 있다):
- UI: 우리 고유 줄이 병합으로 사라진 곳 0(사라진 줄은 원작자가 같은 자리를 바꾼 곳 · 「14일」 문구 3줄뿐) · 사용량 패널(`ws-usage`) 배선 그대로 · 큐 막힘 경보 블록 그대로(스위치 false) · 휴지통 탭 요소 실재 · UI 시험 3173 녹(수리 전).
- Rust: approval BOM 디코더 두 경로 같은 바이트 · `MAX_PARTS=6000` 과 파생 `max_push_bytes` · `ALERT_PROSE_QUIET=false` 와 출하 단언 · operator_token 은 `feed reply --operator` 1곳 · `trash.*` 위임 자리·등급 판정 · quiescing 원작자 표지와 우리 `expire_orphan_feed` 공존 · `surface.quiescing_stale` 소비자 0(새 토스트·주입 0) · invoke_handler 108개 중복 0 · 휴지통 뿌리 셋이 같음 · `released_directive_hashes --check` OK.
- 팩·CI: `bash -n`·`py_compile` 통과 · CI 4 워크플로에서 사라진 시험 0 · 원작자 신규 시험 6개 등재 · CI 참조 파일 실재 · NOWIN 누락 0 · `gen_ceo_template.py --check` GREEN · `HOLD`·`TRASH-OLD`·`expect_gen`·rc 12 공존 · `.producer-<pid>` 로 경합 해소.

## 3. 수리(재현 시험 먼저 → 수리 → 녹 → 뮤턴트)

### 3-1. R3 — CLI 계획 출력의 옛 약속 (커밋 `d9def91a`)
- 시험 `src/bin/cys.rs` `factory_reset_trash_notice_tests` — ①`run_factory_reset` 본문에 「14일 뒤」 없음 ②앱 정본 문장(`ui/src/resetconfirm.ts` 의 상수)과 같은 말.
- 빨강(수리 전 · 「아직 자동 소거(약 14일 뒤)를 약속한다」) → 녹 → 뮤턴트(문장 한 글자) 적.
- 이후 Q1=B 로 문장이 맥/윈 둘이 되어 시험도 두 상수 + 고르는 판정(`if cys::trash_delete_supported() {`)을 함께 본다.

### 3-2. R1 — 윈도우 회수 경로 (master#4e61b71e Q1=B)
조건 = **앱 휴지통 삭제가 그 빌드에서 꺼져 있을 때만**(그 feature 가 켜지는 판부터 자동으로 원작자 S8 동작).
- 판정 정본 한 곳: `src/lib.rs` `pub fn trash_delete_supported()`(윈 = `cfg!(feature = "trash_win_validated")` · 그 밖 = true). 데몬 `trash.rs delete_supported()` 는 이것을 부른다(값 불변).
- 스크립트가 읽을 자리: `cys build-info --json` 에 가산 칸 `trash_delete_supported`(빌드 때 박힌 상수 · 데몬 접속 0). 소비자(`make-release-json.py` 등)는 칸을 이름으로 읽고 `BuildInfo` 는 직렬화 전용이라 옛/새 판 상호 판독 영향 0(확인).
- `cys-dept reap`: `uname` 이 MINGW·MSYS·CYGWIN 이고 build-info 출력에 `"trash_delete_supported":true` 가 **없으면**(false · 칸 없는 1.1.9 이하 · build-info 실패) 1.1.9 처럼 TTL(기본 14일) 초과분 `rm -rf` + `TRASH-EXPIRE` 줄. 그 밖(맥·리눅스·켜진 윈)은 S8 그대로. 요약 줄의 ` TRASH-EXPIRE=N` 은 정리 갈래일 때만 붙는다(맥 출력 바이트 = 종전과 같음 → `javis_purge_e2e.sh:142` 「TRASH-EXPIRE 가 돌아왔다」 단언 유지).
- 화면: 윈 휴지통 탭 안내에 「…오래된 항목은 지난 판처럼 약 14일이 지나면 저절로 정리됩니다.」 · 확인창 2곳(완전 초기화 · 부서 완전 삭제)은 `trashKeepNotice(IS_WINDOWS)` → 윈 = `TRASH_KEEP_NOTICE_WIN`. CLI 계획 출력도 같은 두 문장을 lib 판정으로 고른다.
- 문서: USER-MANUAL 휴지통 절·완전 초기화 절(맥/윈) · 발행 노트(윈 줄 · 「맥에서는 저절로 지워지지 않게」 절을 맥/윈 두 줄로 · D2 행 · 휴면 표 · 근거 표) · 체크리스트 A-4 두 행 · WIN-FIELD TRASH-5 신설(확인점 46) · V1 통과 기준 · 판정표 G9-W 행.
- 시험:
  - `cysjavis-pack/bin/tests/test_trash_old_marking.py` ⑤~⑧ — 제품 블록 바이트를 격리 실행 + 가짜 `uname`(MINGW64_NT) · 가짜 `cys build-info`: ⑤ 칸 false → 정리 ⑥ 칸 없음(1.1.9) → 정리 ⑦ build-info 실패 → 정리 ⑧ 칸 true → 표시만 · 3일 격리분은 언제나 그대로 · dry 는 아무것도 안 지움. 핀 ③ = `rm -rf "$_td"` 는 한 자리 · `_trash_reclaim = 1` 갈래 안 · 그 갈래는 칸이 true 가 아닐 때만.
    - 수리 전 cys-dept = 적 20건 · 뮤턴트1(정리 갈래 끔) 적 10 · 뮤턴트2(OS 무관 정리 = 맥도 지움) 적 8 · 원복 녹.
  - `src/update/buildinfo.rs` `build_info_shape` — 칸 이름·bool·압축 JSON 모양(`"trash_delete_supported":true` 문자열 대조가 cys-dept 와 같은 꼴) · 맥 = true.
  - `ui/src/resetconfirm.test.ts` 「격리분 수명 문장 — 맥/윈도우」 2건(문장 분리 · 두 확인창 배선).
- ⚠윈 실기 0 — 윈 Git Bash 에서 `build-info` 를 부르는 실제 동작은 WIN-FIELD TRASH-5(dry 만)로 확인한다.

### 3-3. R2 — `--wait` 배너 (master#4e61b71e Q2=B)
- `ui/src/alertquiet.ts` `waitBannerReplacesToast()`(= `alertsQuiet("toast")`) — 그 배너는 꺼진 토스트를 **대신하는** 면. `main.ts` 의 직접 호출 조건 머리에 붙임 ⇒ 우리 출하(false) = 1.1.9 와 같은 토스트만 · 원작자 값(true) = R2 그대로(배너 한 면). 가드 재고(`EXPECTED_GUARDS`)는 그대로.
- 시험: `toastaxis.test.ts`(샌드박스 대역 · 「AT-20 대조(보이는 쪽)」 배너 기대 1 → 0 · 출처 핀 문장 · 남긴 자리 지문 재기준선 `17801e6610300e2c → 83f3a45e7bfb4b70`) · `deptprogresswiring.test.ts`(wait 항목 호출열 = 1.1.9 의 `toast → scheduleFeedSwitchIfStillPending`).
  - 수리 전 main.ts = 적 4(동작 2 · 핀 2) · 뮤턴트(조건 반전) 적 7 · 원복 녹.
- 발행 노트 「기다리는 허락 요청을 컴퓨터 알림으로도」 절 삭제 · D15 행 「사용자 변화 0」 · 근거 표 행 삭제 · 【발행 전 확인】 7 → 6곳 · WIN-FIELD V2 ② 기대값 「OS 배너 0」.

### 3-4. R4 — delivery.rs 주석 (실행 영향 0)
S73 단락 앞에 「원작자 v0.14.51 판(4016)의 기록 · 우리는 6000 · 우리 바 1,500 단위」 고지 3줄 · 시험 실패 문구의 「여유 0 단위」를 「(원작자 4016 기준의 문면 — cysr 은 6000 이라 여유가 있다)」로.

## 4. 시험 묶음 결과
(커밋 직전 실측 — §6 에 붙인다)

## 5. 다음 판 후보
1. **R5 지침 바이트 래칫 재조임** — 우리 실측(57,687 / 84,987 / 100,473)으로. 지침을 만지는 가지가 모두 들어온 뒤 한 번에.
2. **「허락 요청 OS 알림」(원작자 R2)을 켤지** — 사용자 판단 대상(Q2 에서 1.1.9 동작으로 되돌림). 켜려면 `waitBannerReplacesToast` 를 true 쪽으로.
3. **윈 휴지통 삭제를 켜는 판**(`trash_win_validated`)의 선결: ①R9(윈 생존 판정 불가 → `open` 표식 항목 영구 차단) ②화면 확인창 문장 선택을 `IS_WINDOWS` 에서 `trash.list` 의 `delete_supported` 로 바꾸기(`ui/src/resetconfirm.ts` `trashKeepNotice` 주석) ③그날부터 reap 은 자동으로 S8(코드 변경 0 · 시험 ⑧).
4. **R8 `formation-*` 휴지통 항목** — 이름 스탬프를 epoch 초 또는 `%Y%m%dT%H%M%SZ` 로 맞추고 `.producer-<pid>` 표식 · 원작자 생산자 목록(`trash.rs:275`)에 넷째로 적기.
5. 저장소 뿌리의 추적 파일 `1`(0.14.32 `0acf317e` 부터 · probe 영수증 JSON 줄) — 원작자 잔재로 보임 · 지울지 판단.
