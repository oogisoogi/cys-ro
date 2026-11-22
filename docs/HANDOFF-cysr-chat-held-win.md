# HANDOFF · TICKET=cysr-chat-held-win (2026-11-23)

가지 `fix/chat-held-win` (기점 bc8156865 = v1.1.16) · 발행·push·윈 설치 없음.

## 증상(박사님 11-22 23:59 윈 캡처)
대화 화면 말 「cysr 이번 업데이트에 대해 설명해줘」 → 「붙잡아 둠 · 마스터 상태 확인이 늦어져서 아직 쓰지 않았어요 — 다시 확인되면 보낼게요.」 · 마스터 카드 「마스터가 답하는 중」 · 배너 「확인할 것 살펴보는 중」. 마스터 jsonl 에 그 말 user 레코드 0(= 앱 안에서 멈춤).
후보판(68dcf537b)과 공개 v1.1.16(bc8156865)의 코드 차이 = 0(문서·워크플로만 · `git diff --name-only` 실측).

## 경로(실측 · 파일:줄은 bc8156865 기준)
- `ui/src/views/core.ts` deliver(): ① `freshBounded()` = feed_list → org_status **순차 2회**, 전체 상한 `OBS_MAX_MS`=500ms ② `offset === null` 이면 `initOffset()` = `chat_transcript{fromEnd}` 1회(상한 500ms) ③ 다시 `freshBounded()`(500ms) ④ 쓰기 직전 관측 나이 ≤ 500ms. 어느 창이든 넘으면 `status_timeout` 붙잡음.
- `src-tauri/src/viewcore.rs` chat_transcript: 데몬 RPC 2회(surface.list · org.status) 뒤 파일 열기. **윈 = `open_bound` 가 항상 `unsupported_platform`**(cfg(not(unix)) · 조각 10 미구현) → `{status:"unknown"}` → UI initOffset = "none" → **offset 이 영원히 null**.
- `src-tauri/src/main.rs` rpc_on/RPC_POOL: 앱의 모든 데몬 RPC 는 **소켓당 연결 1개를 tokio Mutex 로 직렬** 사용. Tauri 명령은 async(메인 스레드 아님). 윈 named pipe 는 풀 연결을 재사용(매번 새로 열지 않음 · PIPE_BUSY 재시도는 연결 시에만).
- 500ms 근거(SLICE-0.5-MEASURE-RESULT M12) = **맥 VM 데몬 몫**(surface.list p95 0.39ms)만 잰 값. 웹뷰→Tauri 구간·윈은 미측정(M9 윈 = 보류).

## 원인 판정
- **[관측·확정] 윈 증폭 구조**: 윈에선 offset 이 늘 null 이라 매 보내기가 500ms 창 **3개**(invoke 5개 + 안쪽 데몬 RPC 2개)를 연달아 통과해야 했다(맥 = 첫 보내기 뒤 창 1개 · invoke 2개). 3초 조회 고리·보낸 뒤 +1/+3/+7초 읽기도 offset null 이라 매번 chat_transcript 를 다시 불러 같은 직렬 연결에 조회를 쌓았다.
- **[재현·대조군]** `ui/src/views/heldwin.test.ts` — 직렬 풀 모형, invoke 180ms: 맥 = 쓰기 1 · 윈(안쪽 RPC 2) = 쓰기 0(붙잡힘). 고치기 전 15건 중 11 실패 / 고친 뒤 15 통과.
- **[관측·확정] 안내 가림**: 한 번 `status_timeout` 으로 붙잡힌 뒤 문턱이 다른 까닭(캡처의 「답하는 중」 = busy)으로 막히면 poll 이 deliver 를 안 불러 옛 안내가 그대로 남았다 → 진짜 까닭이 화면에서 가려졌다.
- **[추정 · 윈 실측 필요]** 윈 앱 안 invoke 왕복이 실제로 몇 ms 인지(WebView2 다리 + 직렬 풀 대기). 데몬 몫은 윈 CLI `cys status` 중앙 32ms(기동 포함)라 작다. 맥 대조: 데몬 org.status 1.1ms · 응답 74.6KB(그중 `todo` 칸 76KB · 좌석 1개). → `win-measure.ps1`(작업 폴더)로 데몬 파이프 왕복·master 행 working 재료 60초 표본을 받는다.
- 확신도: 증폭 구조·안내 가림 = 높음(코드·시험) · 「그날 어느 창이 넘었나」 = 중간(앱 계측 로그 없음).

## 고침
1. 윈 증폭 제거(core.ts): initOffset 이 none 이면 좌석·시각을 기억(`transcriptNone`) → 보내기 길에서 다시 묻지 않음 · 세션 읽기 재조회는 30초 간격(`TRANSCRIPT_NONE_RETRY_MS`) · 상한을 넘겨 늦게 온 none 도 기억(offset 은 제때 온 답으로만 — 기존 세대 규칙 그대로).
2. Rust(viewcore.rs): `transcript_supported()`(= cfg!(unix)) 가 false 면 RPC 0 으로 같은 꼴 반환 · 시험 `transcript_supported_matches_open_bound`.
3. ⓐ 관측 기반 상한: `obsLimit()` = clamp(최근 8회 **끝난** 조회 왕복 최대 × 2, 500, 2000) · 순차 n 개는 `limitFor(n)`(천장 n×2000). 빠른 기계 = 500ms 그대로(기존 시험 무변경 통과). 쓰기 직전 낡음 검사·org 한 다리 검사도 같은 값.
4. ⓑ 상태 확인 늦음 3회 연속(`SLOW_HOLDS_MAX`) = `status_slow` → 자동 전송 멈춤 + 「작업 화면에서 직접 입력 / 이 말 보내기」 안내 · `needsClick` 에 포함(사람 클릭 1회로만). 이유 = 안내를 보고 사람이 마스터 창에 직접 치면 이 말이 뒤에 자동으로 또 나가 **두 번 전달**이 되는 길을 막기 위해.
5. 안내 갱신: 늦음으로 붙잡힌 말은 poll 이 제때 상태를 받았는데 문턱이 막히면 안내·코드를 지금 까닭(예: busy)으로 바꾼다(쓰기 0).

## 두 번 전달 0 불변식
읽기 조회 상한만 바뀜 · chat_send 1회 규칙·불명(uncertain) 재전송 0·「보내는 중」 선영속·세대 규칙 무변경. 늦은 조회 결과는 계속 버림(none 사실만 기억). 새 클릭 대기 상태는 기존 confirmHeld 길(새 번호 · 다듬기부터).

## ⚠ 계약 변경(검토 요청)
- `slice3fix.test.ts` V9: 30초 멈췄다 풀리면 예전 = 자동 전송 1 → 지금 = `status_slow` 클릭 대기 · 클릭 1회 = 전송 1. ⓑ 의 의도된 변경.
- 쓰기 직전 입력줄 관측 나이 상한이 느린 기계에서 최대 2초로 늘어남(기존 500ms). 사람 초안 보호의 주 장치(30초 사람 입력 쉼 · 데몬 refuse_on_approval)는 그대로. codex 1R 은 발행 티켓에서.

## 시험
- ui `bun test` 전체: 3964 pass · 89 skip · 0 fail (4053) · `heldwin.test.ts` 15/15 · `bunx tsc -p tsconfig.check.json` 오류 0.
- cargo `cargo test --bin cys-app viewcore`(TAURI_CONFIG 빈 번들): 26 passed.
- 재현: `cd ui && bun test src/views/heldwin.test.ts`.

## 추가 고침 (master#633f7ac0 · 윈 실측 뒤)
윈 실측(win-measure.ps1 · 00:18): 데몬 파이프 org.status 중앙 4.1ms·최대 10.3 · 새 연결 4.7ms · 60초 표본 3.8~23.1ms = 데몬 쪽 500ms 초과 없음. master 행 `status` 비어 있음(재시작 뒤 좌석 492 set-status 0회) · idle_secs 60초 내내 0.
- **[코드 확정] idle_secs** = `src/bin/cysd/state.rs` PTY 읽기 고리에서 출력 바이트가 오면 `last_output = Instant::now()`(거름 없음 · 커서·상태줄·에코 전부) → org.status `idle_secs` = 그 뒤 경과 초(handlers.rs org.status 행).
- **[코드 확정] 앱 공통 판정** `appearance.nodeWorking`: 자기 신고 신선(≤120초)이면 그 state · 아니면 `idle_secs ≤ 60` = 일하는 중. 대화 화면 문턱은 working 이면 `busy` 로 붙잡는다(U25_BUSY_PASTE_OK=false).
  → 자기 신고 없는 마스터는 **답을 마친 뒤에도 최소 60초(+조회 3초)** 「답하는 중」으로 막힌다(확정 지연). 쉬는 TUI 가 60초 안에 주기 출력을 내면 영구 막힘.
- **[실측 · 맥 대조]** Claude Code 좌석 2373 · org.status 0.5초 간격: 쉬는 중 75초 = idle_secs 13→98 단조 증가(0 복귀 0회) / 일하는 중(도구 실행 대기 25초) = 50표본 전부 0. → 맥에선 영구 막힘 없음 · 60초 지연만.
- **[미확정 · 윈]** 윈 Claude(ConPTY)가 쉬는 중에 주기 출력을 내는지 = `win-idle-sample.ps1`(백그라운드 90초 · 읽기 전용) 결과 대기. 주기 출력이 10초보다 잦으면 아래 고침으로도 막힘이 남는다(그때는 화면 입력창 표식(readiness) 신호를 org.status 에 싣는 데몬 고침이 필요).
- 고침: `judge/gate.ts chatWorking` — 자기 신고가 신선하면 앱 판정 그대로, 아니면 **출력 10초 정적 = 쉬는 중**(`CHAT_QUIET_SECS`). 주입 = `views/index.ts` bootViews → `Deps.chatWorking`(대화 화면 문턱·마스터 카드만 · 작업 화면·메뉴바·되살리기 판정 무변경). 시험 3건(heldwin.test.ts · 순수 판정 · 값 맞물림 · 윈 492 꼴 통합).
- 위험: 자기 신고 없는 마스터가 10초 넘게 출력 없이 일하는 경우 「쉬는 중」으로 보고 붙여넣는다(= U25 미측정 영역). 맥 실측상 일하는 동안 스피너가 계속 출력해 해당 없음.
- 시험: ui 전체 3967 pass · 89 skip · 0 fail(4056) · heldwin 18/18 · tsc 0.
