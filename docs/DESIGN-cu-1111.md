# 컴퓨터 통제권 넘기기 — 설계 1장 (TICKET=cu-1111 · 1.1.11)

- 쓴 곳: worker-2@surface:1660 · 가지 `feat/1111-computer-use`(← int/1111 abc137c0) · 2026-10-26
- 박사님 원문(10-26 08:4x): 「사용자의 컴퓨터를 분석해서 마스터가 통제 가능한 항목을 제시하고 사용자가 선택하여 통제권을
  넘기는 구조 … 마스터가 바로 통제가 가능한 것은 자동으로 가져오고, 사용자의 손길이 필요한 것은 친절한 가이드를 제시한다.」
- 근거 자료: `ai-jarvis/docs/workshop/automation/control-perm/{DIAGNOSIS,EVIDENCE,VM-LOG}.md`(막힘 G1~G11 · M1~M15 · C1~C6 · W1~W7)
- 이 문서의 상태: **설계안 — master 승인 전 구현 0**(아래 §0 스파이크만 실행 · 전부 읽기 전용 · 설정 변경 0).

---

## 0. 탐지 스파이크 결과(이 문서의 토대 · 2026-10-26 09:0x · 박사님 맥 · 이 좌석 surface:1660 · 읽기만)

| # | 무엇을 | 어떻게(팝업 없음) | 결과 | 신뢰도 |
|---|---|---|---|---|
| S1 | 손쉬운 사용 권한 | `ApplicationServices.AXIsProcessTrusted()`(ctypes) | `True` | High(DIAGNOSIS §1 실측과 일치) |
| S2 | 화면 기록 권한 | `CoreGraphics.CGPreflightScreenCaptureAccess()`(ctypes) | `False` | High(같은 실측과 일치 — cysr 좌석은 박사님 맥에서도 화면 기록이 꺼져 있음) |
| S3 | 앱별 자동화 권한 | `CoreServices.AEDeterminePermissionToAutomateTarget(bundle, ****, ****, askUserIfNeeded=false)` | Finder `0`(허용됨) · KakaoTalk `-1744`(아직 안 물음) · Mail·Calendar `-600`(앱이 꺼져 있어 판정 불가) | High(-1743·-1744 = SDK `CoreServices` 헤더 정의 grep 확인 · 0 = 허용 · -600 = 대상 앱 미실행 — Mail·Calendar 가 꺼져 있던 관측과 일치 · 헤더 grep 은 못 함 → Med) |
| S4 | Claude in Chrome 확장 | 크롬 프로필 `Extensions/` 폴더 이름만 + 각 `manifest.json` 의 `name` | ID `fcoeoabgfenejglbffodgkkbkcdhcgfn` = 「Claude」(Default 프로필에만 있음 · 다른 2 프로필엔 없음) | High |
| S5 | 확장 연결 파일 | `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/` 파일 이름 | `com.anthropic.claude_code_browser_extension.json` 있음 | High(DIAGNOSIS §1 과 일치) |
| S6 | 요금제 | `~/.cys/claude/.claude.json` → `oauthAccount.organizationType`(값 하나만 읽음 · 이메일·이름 칸은 읽지도 출력하지도 않음) | `claude_max` | Med(값 어휘 `claude_pro`·`claude_team`·`claude_enterprise` 는 미실측 — 구현 때 모르는 값 = 「확인 못 함」) |
| S7 | 브라우저 도구 기본 켜짐 | 같은 파일 최상위 `claudeInChromeDefaultEnabled` | `true` | Med(이름은 실측 · `/chrome` → Enabled by default 와의 대응은 문서 문장 + 이름으로 추정) |
| S8 | 커넥터 연결 기록 | 같은 파일 `claudeAiMcpEverConnected`(서비스 이름 목록) | `claude.ai Google Drive`·`Notion`·`Claude Docs` | Med(「한 번이라도 연결됨」 기록 — 지금 연결 상태는 아님) |
| S9 | 화면 조작 도구(computer-use) 켜짐 | claude 2.1.310 실행 파일 문자열: `function BPe(e){return e===oC&&!nqe()}` · `function Io(e){…if(BPe(e))return!GPe(n.enabledMcpServers).includes(e)…}` · `oC="computer-use"` | computer-use 는 **기본 꺼짐**이고, 켜면 그 폴더(프로젝트) 설정의 `enabledMcpServers` 에 `"computer-use"` 가 들어간다(`/mcp` 토글 = `tengu_builtin_mcp_toggle`) | Med(내부 구현 · 판본 따라 바뀔 수 있음 → `measured_on` 핀 + 모르면 「확인 못 함」) |
| S10 | 같은 실행 파일의 터미널 표 | `gm={"iTerm.app":…,Apple_Terminal:…,ghostty:…,kitty…}` · 문자열 「terminal not detected; falling back to sentinel host」 | **cysr 은 이 표에 없다** | Low(뜻 = 화면 조작이 cysr 창을 「터미널」로 알아보지 못할 수 있음 → 맥 실기 확인 항목 R1) |

스파이크는 `scratchpad` 의 임시 파이썬으로만 돌렸고 저장소에 남기지 않았다.

---

## 1. 무엇을 만드는가(박사님 범위 그대로)

1. **분석** — 사용자 컴퓨터(맥·윈)를 살펴 「마스터가 통제할 수 있는 항목」 목록을 만든다.
2. **제시·선택** — 항목을 「바로 가능 / 내 손 한 번 필요 / 지금은 안 됨(이유)」 세 칸으로 보여 주고 **사용자가 고른 것만** 넘긴다(기본값 강요 없음).
3. **바로 가능한 것은 자동으로 가져온다**(사용자 추가 조작 0) · **손이 필요한 것은 단계별 안내**(왕초보 말투 · 화면 위치 · 맥/윈 각각 · 끝나면 마스터가 다시 확인).
4. 입구 = 사용자가 마스터에게 말로 — dept-by-chat 과 같은 「도구 + `say` 그대로」 패턴.

★「바로 가능 → 자동으로 가져온다」의 정확한 뜻(정직 고지): 이 기능이 하는 「자동」은 **사용자 확인 뒤 넘김 장부에 올려 마스터가 바로 쓰기 시작하는 것**이다. 맥 권한·크롬 확장·`/mcp` 토글처럼 **사용자 쪽 설정을 마스터가 대신 켜는 일은 하지 않는다** — 그것은 「손 한 번」 칸이다(경계 §6). 따라서 「바로 가능」 = 「이미 다 켜져 있어서 추가로 할 일이 없는 것」이다.

## 2. 파일 위치

| 경로 | 무엇 |
|---|---|
| `cysjavis-pack/bin/javis_computer_control.py` | 도구 하나(동사 §4) · 표준 라이브러리 + ctypes 만(맥) · 윈은 `reg query`·경로 검사만 |
| `cysjavis-pack/skills/computer-control/SKILL.md` | 마스터 절차(dept-by-chat 서식) |
| `cysjavis-pack/bin/javis_preflight.py` | `HARNESS_SKILLS` 에 `computer-control` 1줄 추가(좌석 exec 전 스킬 링크 — `Unknown skill` 재발 방지 · dept-by-chat 선례) |
| `cysjavis-pack/directives/MASTER_DIRECTIVE.md` | 「내 컴퓨터에서 맡을 수 있는 것」 류 요청 → 스킬 `computer-control` 1~2줄 |
| `cysjavis-pack/bin/tests/test_computer_control.py` · `mut_computer_control.py` | 시험·뮤턴트(§8) |
| `src/factory_reset.rs` | 리셋 목록에 `computer-control` 1줄(dept-requests 선례) |
| 상태: `~/.cys/computer-control/` | `scan.json`(마지막 분석 · 항목 상태만) · `grants.json`(넘김 장부 — 현재 상태) · `ledger.jsonl`(넘김·거둠 기록 · append 전용) |
| `docs/DESIGN-cu-1111.md` | 이 문서(구현 뒤 CLI 계약 절을 덧붙인다) |

Rust 앱 쪽은 리셋 목록 1줄 말고는 손대지 않는다(UI 카드·사이드바는 범위 밖 — 박사님 원문의 입구는 「말로」다). 음성 대화 가지와 겹치는 파일은 `MASTER_DIRECTIVE.md`·`javis_preflight.py` 의 서로 다른 줄뿐이다.

## 3. 항목 사전

판정 표기: **바로** = 바로 가능 · **손** = 내 손 한 번 필요 · **안 됨** = 지금은 안 됨(이유 필수) · **?** = 확인 못 함(→ 언제나 「손」 칸에 「확인」 단계와 함께 놓는다 — **모르는 것을 「바로」에 두지 않는다**).

### 3-1. 맥

| ID | 항목 | 탐지(전부 팝업 없음·읽기만) | 판정 규칙 | 손 칸 안내 요지(근거) |
|---|---|---|---|---|
| `chrome` | 로그인된 크롬으로 웹 일(지메일·구글 문서·클라우드플레어 화면 등) | ⑴크롬 앱 존재(`/Applications`·`~/Applications`) ⑵확장 ID `fcoeoab…` 폴더가 어느 프로필에 있는지(프로필 **이름은 출력하지 않고** 「프로필 n개 중 k개」) ⑶확장 켜짐(`Preferences` 의 그 ID 항목 `state`·`disable_reasons` 만) ⑷연결 파일 S5 존재 + 가리키는 실행 파일 존재 ⑸`claudeInChromeDefaultEnabled` | ⑴없음 → 안 됨(「크롬이 없습니다」 + 설치는 사용자 선택) · ⑵~⑸ 전부 참 → 바로 · 하나라도 거짓 → 손 · 값을 못 읽음 → ? | 웹 스토어 설치·로그인·압정(C2) → 마스터 칸 `/chrome` → Enabled by default(C1·G2) → 크롬 완전 종료 후 다시 켜기(G3) → cysr ↻ 재시작 → 마스터가 `recheck chrome`. 「Browser extension is not connected」면 `/status` Organization ↔ 확장 계정 맞추기(G4·C3). 로그인·보안문자·결제·영구 삭제는 사람이(C5·C6) |
| `connectors` | 커넥터(지메일·캘린더·드라이브·노션 등 — 메일·일정 내용은 커넥터로) | `claudeAiMcpEverConnected` 서비스 이름 | 목록 있음 → 서비스별로 바로(「연결 기록 있음」이라고 정직하게 · 지금 연결 확인은 사용 첫 회) · 없음 → 손 · 요금제 키가 API 키 로그인이면 → 안 됨(P3) | claude.ai → 설정 → 커넥터 → 「+」(EVIDENCE §2) · CLI 에서 따로 로그인하지 않는다 · 단체 계정은 「Access blocked」면 관리자 |
| `screen` | 데스크톱 앱 화면 조작(카톡·한글·어도비·오피스 등) | ⑴요금제 S6 ⑵computer-use 켜짐 S9(마스터 폴더의 `enabledMcpServers`) ⑶손쉬운 사용 S1 ⑷화면 기록 S2 | ⑴Team·Enterprise → 안 됨(「이 요금제에서는 화면 조작이 없습니다」 · P1) · ⑴모르는 값 → ? · ⑵~⑷ 전부 참 → 바로 · 그 밖 → 손(빠진 것만 단계로) | ⑵마스터 칸 `/mcp` → computer-use → Enable(G1·M1) ⑶·⑷ 시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용 / 화면 및 시스템 오디오 녹음 → cysr 켜기 · **맥 로그인 암호를 묻는 것이 정상**(G5·M5) · 목록에 cysr 이 없으면 「+」(손쉬운 사용 한정 · M4) · 「종료 및 다시 열기」 눌러도 대화 유지(M6) · 「cysd」 이름 창 = cysr 엔진 → 허용(G6·M7) · 그래도 안 되면 ↻ 재시작(M9) · 다른 칸이 잠금을 쥐면 그 칸 대화 끝내기(M10) |
| `apps` | 앱 목록(카탈로그 한정) | 정해진 목록만 존재 확인 — KakaoTalk · 한글(Hancom Office HWP) · Word·Excel·PowerPoint · Adobe(Photoshop·Illustrator·Acrobat 등 이름 접두) · 메일·캘린더·Finder(기본) | 각 앱 판정 = `screen` 판정을 따른다(화면 조작 경로) · 앱이 없으면 그 줄을 싣지 않는다 · **카톡 = 「보이는 만큼 읽기·직접 보내기」 한정 고지**(M14) · **맥 한글 = 화면 조작만**(M13) | `screen` 안내를 따른다 |
| `script` | 앱 자동화(스크립트 — 메일·캘린더·Finder·오피스 등 스크립트를 받는 앱) | S3(`askUserIfNeeded=false`) — 카탈로그 앱 중 설치된 것만 | `0` → 바로 · `-1744` → 손(「처음 시킬 때 맥이 묻는 창에서 허용」 · 암호 없음 · M8) · `-1743` → 손(시스템 설정 → 자동화 → cysr 아래 그 앱 켜기) · `-600`·그 밖 → ?(「앱이 꺼져 있어 확인 못 했습니다 — 켜 두시면 다시 볼게요」) | M8 · Apple mchl07817563 |
| `files` | 파일·폴더 | 경로 **존재만**(목록 열람 0): ⑴보호 안 받는 곳 — `~/CYSjavis`·홈의 일반 폴더 ⑵맥이 보호하는 곳 — 바탕화면·문서·다운로드·iCloud Drive·외장 디스크 | ⑴ → 바로 · ⑵ → 손(「마스터가 처음 그 폴더를 열 때 맥이 한 번 묻습니다 — 허용」) · **분석 단계에서 보호 폴더를 열지 않는다**(열면 그 자체가 창을 띄운다) · 전체 디스크 접근 권한 = 권하지 않음(M15) | 사용자가 고른 폴더만 넘김 장부에 경로로 올린다 |
| `browser-alt` | 예비 브라우저 길(Playwright 확장 · DevTools autoConnect) | Playwright 확장 ID `mmlmfjhmonkocbjadbfplnigmagldckm` 존재 · 마스터 사용자 설정의 `mcpServers` 이름만 | `chrome` 이 바로면 **제시하지 않는다** · `chrome` 이 손·안 됨일 때만 손 칸에 「예비 길(강사와 함께)」로 | DIAGNOSIS §4 권고 순서 · 예비 길엔 확장의 보호 규칙이 같다는 보장 없음 고지(codex 1R #2) |

### 3-2. 윈도우(★실기 0 — 아래 탐지 경로는 공식 문서·관례 근거의 가정 · 윈 master 실기로 확정할 때까지 「?」 판정으로 출고 가능)

> **정정(2026-10-26 · TICKET=cu-1111-win-fix · 커밋 621977c6)** — 윈 master 1차 실기(10-26 19:4x · 박사님 윈 노트북)에서 결함 3건이 나와 아래 표의 `chrome`·`screen` 줄과 표 밑 「출력 인코딩」을 고쳤다. 나머지 줄은 여전히 가정이다.

| ID | 탐지 | 판정 |
|---|---|---|
| `chrome` | `%LOCALAPPDATA%\Google\Chrome\User Data\<프로필>\Extensions\fcoeoab…` · 연결 파일 = 레지스트리 `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.anthropic.claude_code_browser_extension`(`reg query` · 읽기 · ★출력은 바이트로 받아 OEM → ANSI 코드페이지(`GetOEMCP`·`GetACP`)로 푼다 — 끝내 안 풀리면 대체 문자 · 디코드 실패가 판정을 바꾸지 않는다) · `claudeInChromeDefaultEnabled` | 맥과 같은 규칙 · WSL 안이면 안 됨(W6) |
| `connectors` | 맥과 같음 | 맥과 같음 |
| `screen` | — | **안 됨**: 「윈도우에서는 이 칸의 마스터가 화면을 조작할 수 없습니다(공식 · G8·W1). Claude 데스크톱 앱에서는 가능합니다 — 그 앱에 직접 시키셔야 합니다.」 + 데스크톱 앱 설치 여부만 덧붙임 — 근거 순서: ⑴`%LOCALAPPDATA%\AnthropicClaude`·`%LOCALAPPDATA%\Programs\Claude` ⑵MSIX 사용자 자료 폴더 `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc`(실기: MSIX 설치 `C:\Program Files\WindowsApps\Claude_2.19675.0.0_x64__pzs8sxrjxfjjc` · 패키지 앱 자료 = `LocalAppData\Packages\<패밀리 이름>` = Microsoft Learn MSIX 문서) ⑶`%ProgramFiles%\WindowsApps` 이름 목록(`Claude_*_pzs8sxrjxfjjc`) — 목록 권한 거부가 흔하므로 거부면 「?」(확인 못 함) · 목록을 읽었는데 없으면 「찾지 못했습니다」 |
| `apps` | 카탈로그 앱 존재(시작 메뉴 바로가기·알려진 설치 경로) | `screen` 이 안 됨이므로 「화면 조작 불가 · 스크립트 길은 아래」 |
| `script` | 한글 = 공식 자동화(OLE · `HWPFrame.HwpObject`) · 오피스 = COM — **존재 판정만**(레지스트리 ProgID 읽기) | 1.1.11 = **?** 고정(「윈도우 스크립트 길은 확인 중」) — 실제 COM 호출은 윈 실기 뒤 별 티켓(보안 모듈 창·UIPI W3 확인 필요) |
| `files` | 경로 존재만 | 바로(윈도우는 폴더 보호 창이 없다 — 단 「제어된 폴더 액세스」가 켜져 있으면 차단될 수 있음 → 윈 실기 확인 항목) |
| `browser-alt` | 맥과 같음 | 맥과 같음 |

**출력 인코딩(정정 · 윈 실기 ①)**: 윈 파이프의 파이썬 기본 stdout 은 ANSI 코드페이지(cp949)라 「—」(U+2014 · cp949 에 없음)에서 `UnicodeEncodeError` → `scan` rc 1 이었다. 도구는 stdout·stderr 를 **UTF-8 로 고정**한다 — 마스터의 Bash 도구(Git Bash)·PowerShell 도구는 출력을 UTF-8 로 읽으므로 콘솔 코드페이지로 쓰면 죽지 않아도 마스터 쪽 한글이 깨진다. cysr 좌석은 `PYTHONUTF8=1` 로 뜨므로(`src/lib.rs` `spawn_env_pairs`) 실경로에서 드러나는 쪽은 오히려 위 `reg query` 디코드 결함이다.

### 3-3. 출력에 싣지 않는 것(개인정보 최소화 — 출력은 마스터 대화로 들어가므로 곧 모델 제공자에게 간다)
이메일·이름·조직 이름·크롬 프로필 이름·방문 기록·쿠키·메일 본문·파일 이름 목록·앱 전체 목록(카탈로그 밖). 실리는 것 = 항목 ID·판정·이유 문장·카탈로그 앱 이름·「프로필 n개 중 k개」·커넥터 서비스 이름(S8).

## 4. 동사(도구 계약 — stdout = JSON 한 줄 · 마스터는 `say` 를 한 글자도 바꾸지 않고 전한다)

| 동사 | 하는 일 | 쓰기 |
|---|---|---|
| `scan` | §3 탐지 전부 → 세 칸 분류 → 번호 붙은 목록 `say`(「1. 크롬 — 바로 가능 …」) · 마지막 줄 「맡기실 번호를 말씀해 주세요. 고르지 않은 것은 넘겨받지 않습니다.」 | `scan.json`(항목 상태만) |
| `grant --pick <번호들> --answer-file <사용자 답 원문>` | 고른 것만 처리: 바로 → 장부 `active` · 손 → 장부 `pending` + 첫 안내 `say` · 안 됨 → 거부 문장(이유) | `grants.json` · `ledger.jsonl` |
| `guide <ID> [--step n]` | 손 칸 단계 안내(한 번에 한 단계 · 맥/윈 자동 · 화면 위치 문장 · 「다 하시면 '했어'라고 말씀해 주세요」) | 없음 |
| `recheck <ID>` | 그 항목만 다시 탐지 → 바뀌었으면 `pending → active` + 「이제 제가 맡습니다」 · 아니면 「아직 꺼져 있어요 — 여기를 한 번 더 봐 주세요」 + 빠진 단계만 | 장부 |
| `revoke <ID>` | 장부에서 거둠 → 맥 권한처럼 마스터가 끌 수 없는 것은 끄는 곳 안내 | 장부 |
| `status` | 장부 + 각 항목 지금 상태(재탐지) | 없음 |
| `open-settings <pane>` | 사용자가 「열어 줘」라고 한 뒤에만(스킬 규칙) — 허용 목록 URL 만 연다: 맥 `x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility`·`…Privacy_ScreenCapture`·`…Privacy_Automation`(V10 실기) · 윈 = 해당 없음(1.1.11) | 없음 |
| `self-test` | 판정표 전 조합 · 개인정보 금지 문자열 · 내장 뮤턴트 | 없음 |

종료 코드: 0 성공 · 2 사용 오류 · 4 대상 없음(모르는 ID·번호) · 5 거부(안 됨 항목을 고름) · 7 상태 불일치(scan 없이 grant · 낡은 scan — 30분) · 1 내부 오류. 거부도 `{"ok": false, "say": …, "reason": …}`.

**「바로 → 자동으로 가져온다」의 집행**: `grant` 가 장부를 `active` 로 쓰는 것으로 끝난다. 마스터는 그 뒤 해당 도구(크롬 확장 도구·화면 조작·커넥터·스크립트)를 쓸 때 장부에 있는 항목만 쓴다(§5 📌 D1).

## 5. 대화 흐름

```
사용자 「내 컴퓨터에서 네가 맡을 수 있는 걸 찾아 줘」
 → 마스터(스킬 computer-control): scan → say 그대로(세 칸 · 번호)
사용자 「1이랑 3번」 / 「크롬만」 / 「다 해 줘」
 → 마스터: 답 원문을 파일로 → grant --pick 1,3 --answer-file … → say 그대로
    · 바로 칸 → 「크롬은 지금부터 제가 맡겠습니다.」
    · 손 칸 → guide <ID> 1단계 say
 「다」는 **그 목록에 보인 바로·손 칸 번호 전부**로 마스터가 풀어 넘긴다(안 됨 칸 제외) — 목록에 없던 것을 넣지 않는다
사용자(손 단계 끝) 「했어」
 → 마스터: recheck <ID> → 됐으면 active · 아니면 빠진 단계만 다시
사용자 「화면 조작은 이제 그만」
 → 마스터: revoke screen → 끄는 곳 안내 say
```

- 승낙 판단 = dept-by-chat 6번과 같다(정해진 낱말이 아니라 뜻 · 답 원문 그대로 파일 · 애매하면 한 번 묻기).
- 손 안내 중에 마스터는 **OS 창을 대신 누르지 않는다** · 「설정 화면을 열어 드릴까요?」에 「네」일 때만 `open-settings`.

### 📌 master 결정 필요(설계 승인과 함께)

- **D1 넘김의 강도** — ⓐ 장부 + 지침(마스터가 장부 밖 항목을 쓰지 않는다는 규칙 · 기계 차단 없음) **권고** · ⓑ 장부 + 훅 차단(장부가 있는 기계에서 본부 마스터의 `mcp__computer-use__*`·`mcp__claude-in-chrome__*` 를 장부 밖이면 거부 · 장부 없는 기계는 종전 그대로). 권고 이유: ⓑ는 role-capability-gate(이미 3천 줄)에 본부 master 판정 축을 새로 넣는 일이라 1.1.11 범위·위험이 크다 · 단점: ⓐ는 LLM 규율이라 장부 밖 사용을 기계가 못 막는다(정직 고지) — ⓑ는 1.1.12 후보로 BACKLOG.
- **D2 요청 창 띄우기** — 손쉬운 사용·화면 기록 목록에 cysr 이 아예 없을 때(M3·M4) `AXIsProcessTrustedWithOptions(prompt)`·`CGRequestScreenCaptureAccess()` 로 **맥의 요청 창을 사용자 앞에 띄우는 것**(누르는 것은 사용자). 「OS 권한 창 자동 클릭 금지」에는 안 걸린다고 보지만 경계에 가까워 묻는다. 권고 = 사용자가 「네」한 뒤에만 허용 · 단점: 첫 실행 창 4~5개 겹침(G7)이 또 하나 는다.
- **D3 훅** — dept-by-chat 은 말 입구를 UserPromptSubmit 훅(`dept-chat-inject.sh`)으로 보강했다. 이번엔 **스킬 등록 + 지침 1~2줄만**으로 시작하고, 맥 실기에서 마스터가 스킬을 안 부르면 그때 훅을 붙이는 것을 권고(단순성) · 단점: 실기 1회분 지연 가능.

## 6. 경계(불변 — 시험이 단언한다)

| 금지 | 이 설계에서 지키는 방법 |
|---|---|
| 자격증명 대행·비밀번호 저장/전달 | 도구에 입력 칸이 없다 · 암호 창은 「맥 로그인 암호를 직접 넣으세요」 안내만 · 키체인·`Login Data`·쿠키 파일을 열지 않는다(시험: 열기 감시로 단언) |
| 백신·보안 설정 우회 | TCC 데이터베이스 읽기·쓰기 0 · `tccutil` 0 · 윈 SmartScreen·UAC 는 안내만(W4·W5) · 「제어된 폴더 액세스」 예외 추가 안 함 |
| OS 권한 창 자동 클릭 | 클릭·키 입력 코드 없음 · 탐지 API 는 전부 「묻지 않는」 판(`askUserIfNeeded=false` · preflight) — 뮤턴트가 `true` 로 바꾸면 시험이 죽는다 |
| 사용자 설정을 대신 켜기 | `.claude.json`·크롬 `Preferences`·`agents.json` 은 **읽기만** · `/mcp`·`/chrome` 토글은 사용자 손 · 기본값 = 「묻고 나서」 |
| 개인정보 외부 전송 | 분석 = 「무엇이 있고 연결됐는가」까지 · 출력 금지 목록 §3-3 · 보호 폴더 열람 0 · 네트워크 호출 0 |

## 7. 치명 위험 4군(cys 개발자 ABSOLUTE ANCHOR)

| 군 | 이 기능에서 | 판정 |
|---|---|---|
| ①폭주(재시도·큐 상한) | 도구 = 사람 말 1회당 1회 실행 · 재시도 루프 없음 · 스케줄 잡·백그라운드 프로세스 없음 · 외부 호출은 `reg query`·`open` 1회씩(각 5초 상한) · 탐지 대상 = 고정 카탈로그(앱 ≤ 20 · 크롬 프로필 ≤ 20 · 넘으면 앞 20개 + 「더 있음」) · 장부 줄 수 상한(1,000 — 넘으면 오래된 거둠 기록부터 정리) | 해당 없음에 가깝다(상한 명시) |
| ②무clear(컨텍스트 무한 증가) | `say` 상한(목록 ≤ 25줄 · 안내 1단계 ≤ 8줄) · 훅 없음(D3) → 매 턴 주입 0 | 해당 없음(상한 명시) |
| ③자가치유 전멸 시 페일백 | 탐지 하나가 실패해도 그 항목만 「?」(전체 실패 0) · ctypes 로드 실패·파이썬 없음 → 마스터가 정적 안내(워크숍 「처음 한 번 준비」 페이지)로 폴백 · 장부 손상 → 읽기 실패 시 장부 없음으로 보고 `ledger.jsonl` 은 보존(덮어쓰기 0) | 페일백 경로 명시 |
| ④전 pane 사망 | 프로세스 종료·재시작 코드 0 · ↻ 재시작·크롬 재시작은 **사용자에게 안내만** · `open` 은 설정 앱만 연다(허용 목록) | 해당 없음 |

윈도우는 맥 통과가 근거가 아니다 — 윈 칸은 실기 전까지 「?」로 출고하는 설계이고, 윈 실기 목록은 §8-3.

## 8. 시험 계획

### 8-1. 단위·뮤테이션(임시 HOME · 가짜 크롬 폴더·가짜 `.claude.json` · 탐지 함수 주입)
- 판정표 전 조합: 항목별 입력 축(예: `screen` = 요금제 5값 × computer-use 3값(켜짐·꺼짐·모름) × AX 2 × SC 2 = 60)을 전수로 돌려 세 칸 + ? 귀착 단언 · **「?」가 「바로」로 가는 조합 0** 단언.
- 개인정보: 가짜 `.claude.json` 에 표지 문자열(이메일·이름·조직 이름)·가짜 크롬 프로필 이름을 넣고 모든 동사 출력에 그 문자열이 없음을 단언.
- 열람 감시: `os.listdir`·`open` 을 감싸 보호 폴더(바탕화면·문서·다운로드)·`Login Data`·`Cookies`·키체인 경로 접근 0 단언.
- 쓰기 감시: `~/.cys/computer-control/` 밖 쓰기 0 · `.claude.json`·`Preferences` mtime 불변.
- 장부: `grant` 는 고른 번호만 · 「안 됨」 번호 거부(exit 5) · scan 없이/낡은 scan 이면 exit 7 · `ledger.jsonl` append 전용(크기 단조 증가).
- 뮤턴트(목표 12종 이상 · 킬러 시험 이름 귀속 · dept 선례 형식): ?→바로 · 요금제 검사 삭제 · `askUserIfNeeded=true` · 이메일 출력 · 보호 폴더 listdir · grant 기본 전부 · revoke 미기록 · 장부 덮어쓰기 · 윈에서 `screen` 을 바로로 · `browser-alt` 를 chrome 바로일 때도 제시 · open-settings 허용 목록 밖 URL · say 상한 제거.

### 8-2. 맥 실기(⛔호스트 라이브 자격증명 복사 금지)
- **VM**(tart `jarvis-clean-vanilla` 새 복제 · 이 가지 빌드 · Claude 로그인 없음): `chrome`(크롬 없음 → 설치 → 확장 없음 단계) · `screen`(S1·S2 꺼짐 → 사용자가 켬 → `recheck` 바로) · `script`(-1744 → 허용 → 0) · `files`(보호 폴더 열람 0 — `log stream` 으로 TCC 요청 0 확인) · `open-settings`. 로그인 필요 칸(`connectors`·computer-use 토글·요금제)은 「?」로 떨어지는지만 확인.
- **박사님 맥 읽기 전용 실행**(설정 변경 0 · 장부는 임시 HOME 이 아니라 실제 `~/.cys/computer-control` 이 생기므로 → `CYS_CC_STATE=<scratch>` 로 돌린다): S1~S9 실값이 판정에 맞게 들어가는지.
- R1(S10): 화면 조작이 cysr 창에서 동작하는지 — 로그인된 계정이 필요해 VM 에서 못 함 → **master 판단 필요**(박사님 맥 cysr 마스터에서 `/mcp` Enable 1회는 사용자 설정 변경이라 워커가 하지 않는다).

### 8-3. 윈 실기(master ↔ 윈 master)
확장 폴더·레지스트리 연결 키 실경로 · Claude 데스크톱 앱 설치 경로 · 한글 ProgID · 「제어된 폴더 액세스」 · 파이썬 해소(`cys_resolve_py`)로 도구가 뜨는지 · 한국어 콘솔 출력.

### 8-4. 적대 검토 1회
codex(또는 agy) — 범위 = 이 문서 §3·§6 + 구현 diff · 초점 = 권한/보안 경계(자동 클릭·우회·개인정보 유출·장부 우회).

## 9. 상한 제안(실측 계수 없음 · 이 티켓으로 첫 계수 확보)
구현+단위·뮤턴트 = 150분 · 맥 실기(VM + 박사님 맥 읽기) = 60분 · codex 1R + 반영 = 45분. 초과 예상 시 그 시점에 보고.

## 10. 범위 밖
앱 화면 카드(사이드바·Feed) · 부서 마스터 입구(본부 한정 — dept-by-chat 과 같음) · 윈 스크립트 실제 호출 · 장부 기계 차단(D1-ⓑ) · 예비 브라우저 길의 자동 등록(`claude mcp add` — 기본 꺼짐 · 사용자가 고르고 「네」할 때만 실행하는 안을 1.1.12 후보로).

## 11. 정직 고지(모르는 것)
- S6 요금제 값 어휘 중 `claude_pro`·`claude_team`·`claude_enterprise` 는 실물 미확인(이름 추정) — 모르는 값은 「?」.
- S9 는 Claude Code 내부 구현이다 — 판본이 바뀌면 깨질 수 있다(`measured_on: 2.1.310` 핀 · 다르면 「?」 + 「/mcp 에서 직접 확인」 안내).
- 「바로」 판정의 크롬은 「확장·연결 파일·기본 켜짐이 다 있다」까지다 — **확장의 로그인 계정이 마스터와 같은 조직인지는 확장 저장소를 열어야 알 수 있어 열지 않는다** → 첫 사용 때 「not connected」가 나면 G4 안내로 내려간다.

---

## 12. 구현 기록(2단계 · 2026-10-26 · 승인 = master#8d930a12 09:14 · 재개 = master#a30df3f1 18:40)

### 12-1. 만든 것
| 파일 | 내용 |
|---|---|
| `cysjavis-pack/bin/javis_computer_control.py` | 동사 9개(scan·grant·guide·recheck·revoke·status·open-settings·request-prompt·self-test) · 표준 라이브러리 + ctypes |
| `cysjavis-pack/skills/computer-control/SKILL.md` | 마스터 절차(dept-by-chat 서식) |
| `cysjavis-pack/bin/javis_preflight.py` | `HARNESS_SKILLS` += `computer-control`(좌석 exec 전 스킬 링크) |
| `src/factory_reset.rs` | `CYS_BASE_EXACT` += `computer-control`(배열 28→29) |
| `cysjavis-pack/bin/tests/test_computer_control.py` · `mut_computer_control.py` | 시험 39 · 뮤턴트 20 |

### 12-2. 승인 설계와 달라진 것(전부 이 문서 §3·§4 대비 · 이유 = 실측)
1. **앱 줄을 화면 조작 줄로 접음**(§3-1 `apps` 항목 → 없음): 호스트 실측에서 앱 8개가 화면 조작과 같은 판정·같은 안내를 8번 반복해 목록이 20줄이 됐다. 화면 조작 줄 제목에 「이 컴퓨터의 앱: 카카오톡·한글·…」로 싣고 카톡·한글 고지는 그 줄의 note 로 옮겼다. 넘김 단위 = 화면 조작 1개.
2. **같은 판정의 스크립트·폴더 줄을 한 줄로 합침**: ID = `script:mail,calendar` 형태. `recheck`·`guide`·`status` 는 합친 ID 의 구성원을 **지금 판정으로 다시 합친다**(가장 나쁜 칸 · 모름 하나면 모름).
3. **「처음 쓸 때 맥이 묻는 것」은 넘기면 바로 active**: 보호 폴더·아직 안 물은 앱 자동화(-1744)는 지금 할 일이 없어 `recheck` 로 영원히 안 바뀐다(pending 고착). 칸은 그대로 「손 한 번」으로 보이고, 넘길 때 그 한 번(「허용」)을 안내한다.
4. **윈 스크립트 = 「지금은 안 됨」**(§3-2 는 「?」): 「?」는 손 칸에 놓이고 `recheck` 로 풀릴 것처럼 보이는데 1.1.11 에서는 풀 길이 없다 — 「다음 판에서 엽니다」로 정직하게.
5. **computer-use 기록 대조 = 그 폴더 또는 git 최상위만**: 처음 스파이크는 「가장 가까운 상위 폴더」였으나, 상위(예: 홈)는 다른 프로젝트의 기록이라 빌려 쓰면 「바로」 오판이 난다(뮤턴트 M13).
6. **`request-prompt` 는 사용자 답 원문 파일을 요구**(D2 「네」 뒤에만의 기계 벨트 — 빈 파일 exit 2).
7. **`grant --folder <경로>`**: 사용자가 목록 밖 폴더를 말할 때(맥 보호 폴더 아래면 「처음 열 때 허용」).
8. **MASTER_DIRECTIVE 1~2줄 = 넣지 못함**(D3 일부 미이행 · 📌 master 결정): `test_cso_directive_rev.test_directive_byte_budget_ratchet` 가 `MASTER_DIRECTIVE.md` 를 84,987B 상한으로 묶고 HEAD 가 정확히 84,987B 다(여유 0) — 853B 절을 넣자 그 시험과 CEO_TEMPLATE 합성 등가 시험(`test_bootv2_doc_contract` ⑤)이 적색. 예산을 올리거나 다른 절을 줄이는 것은 이 티켓 범위 밖이라 되돌렸다. 지금 입구 = 스킬 등록만(스킬 설명이 마스터의 스킬 목록에 늘 실린다).
9. 「안 됨」 번호만 고르면 exit 5 · 섞여 있으면 나머지는 처리하고 거부 문장을 함께 낸다.

### 12-3. 동사 계약(구현 그대로)
- `scan` → `{"ok", "platform", "groups": {ready|hand|not_now: [번호]}, "items": [{n, id, tier, unknown}], "say"}` · `scan.json` 기록.
- `grant --scan <scan_id> --pick 1,3 --answer-file F [--folder P]` → `{"ok", "active": [ID], "pending": [ID], "refused": [ID], "next_guide", "say"}` · scan 없음/30분 지남 = exit 7(`no_scan`·`stale_scan`) · **보인 목록과 다른 목록(scan_id 불일치)·다른 폴더 = exit 7 `scan_replaced`** · 없는 번호 = exit 4 · 숫자 아님·빈 답 = exit 2 · 장부 기록에 답 원문은 sha256 만 · **감사 기록(ledger)을 먼저 쓰고 장부를 바꾼다**(기록 실패 = 장부 불변) · 장부 키 = 구성원 ID(`script:mail` — 합친 줄을 넘기면 구성원 각각).
- `guide <ID> [--step n]` → `{"ok", "step", "total", "last", "say"}`(지금 빠진 단계만 · n 은 1..total 로 자름) · 바로 칸이면 `done: true`.
- `recheck <ID>` → `{"ok", "tier", "states": {구성원 ID: 상태}, "say"}` — 바로가 되면 장부에 있는 구성원 중 pending → active(구성원마다 · 기록 먼저).
- `revoke <ID>` → 장부에서 빼고 끄는 곳 안내(합친 ID 면 구성원 전부 · 저장 먼저 → 기록) · 없으면 exit 4. 옛 판의 합친 키는 읽을 때 구성원으로 펼친다.
- `status` → `{"ok", "rows": [{id, state, now}], "say"}` — active 인데 지금 꺼져 있으면 경고 문장.
- `open-settings accessibility|screen|automation`(맥만 · 허용 목록 밖 exit 5) · `request-prompt ax|sc --answer-file F --meaning yes|no|unclear`(맥만 · yes 아니면 exit 5 `not_yes`).
- 상태 폴더 = `~/.cys/computer-control/`(`CYS_CC_STATE` 로 바꿈) · 시험 주입 = `CYS_CC_FAKE_PROBES` · `CYS_CC_PLATFORM` · `CYS_CC_PROJECT` · `CYS_CC_APP_ROOTS`.

### 12-4. 실기
| # | 어디서 | 무엇 | 결과 |
|---|---|---|---|
| E1 | 박사님 맥 · 이 좌석 · 상태 폴더 = scratchpad(실 `~/.cys/computer-control` 무접촉) | scan → grant 1,4,6 → guide → recheck → status → revoke · 거부 경로 | 전 동사 기대대로. 판정 = 크롬·커넥터·Finder/PowerPoint 자동화 바로 · 화면 조작 손(남은 것: /mcp · 화면 기록) — DIAGNOSIS §1(이 맥 cysr 좌석 화면 기록 꺼짐)과 일치 |
| E2 | 박사님 맥 · **원 계정 좌석**(CLAUDE_CONFIG_DIR=~/.cys/claude) · 전용 시험 폴더 `~/axdev/.wt/cu-r1-test` | **R1**: `/mcp` → computer-use Enable → 도구가 그 폴더에서 켜짐 판정(남은 것 = 화면 기록 1개) → 시험 세션에 request_access(Finder)·screenshot 시킴 | ⑴ `/mcp` 화면 = 「Built-in MCPs … ◯ computer-use」(기본 꺼짐 확인) · Enable 뒤 `.claude.json` 그 폴더 `enabledMcpServers = ["computer-use"]`(S9 실증) · ⑵ claude-in-chrome 은 `--chrome` 없이 켜짐(S7 실증) · ⑶ computer-use 는 cysr 안에서 **기동한다** — 자체 권한 화면 「Computer Use needs macOS permissions · Accessibility: ✔ granted · Screen Recording: ✘ not granted」 = 이 도구의 S1·S2 판정과 같다 · ⑷ request_access 결과 원문: 「… permissions need to be granted in **the Claude desktop app** on the computer where it's running」 → 시험 세션도 「Claude 앱을 켜 주세요」라고 안내 — **cysr 안에서는 틀린 이름**(스위치 이름 = cysr · VM-LOG V4). R1(터미널 미탐지)의 실제 증상 = 이 오안내다. 이 기능의 안내 문장은 cysr 로 적었다 · ⑸ 화면 기록을 켜는 것은 박사님 전역 설정이라 여기서 멈춤(실제 스크린샷은 미실측) · ⑹ 원복: `/mcp` → Disable → `enabledMcpServers = []` 확인 · 시험 좌석 close · 폴더 삭제. 원래 「그 폴더 기록 없음」이었고 지금은 「기록 있음·computer-use 꺼짐」(`.claude.json` 전역 파일 손편집은 하지 않았다) |
| E3 | 새 VM(tart clone `ws-perm-1025-a` → `cu-1111-vm` · cysr 1.1.10 · 크롬 · claude 로그인 없음 · 끝나고 삭제) | 도구를 **cysr 좌석 안에서** 실행(sha256 대조) | self-test ok · scan 7줄: Finder 자동화 바로 · 크롬 손(확장 없음·연결 파일 없음 + 기본 켜짐 모름) · 예비 길 손 · 커넥터 확인 필요(로그인 없음) · 화면 조작 확인 필요 · 메일·캘린더 확인 필요(앱 꺼짐) · 보호 폴더 손. **교정 1건**: 모름뿐인 줄에 「남은 것:」이 붙던 문장 → 「확인할 것:」(커밋 4ee2eac0 · 시험 추가) · `open-settings screen` → 시스템 설정 프로세스 0→1 |
| E4 | 같은 VM | 「보호 폴더 열람 0」을 TCC 로그로 확인 | **판정 불가**: 양성 대조(좌석에서 일부러 `ls ~/Desktop`)도 `log show` TCC 줄 0 — 이 VM 은 바탕화면 허락이 이미 있었고/또는 로그가 권한 없이 안 보인다. 이 주장의 근거는 단위 시험의 열람 감시(`test_no_protected_or_secret_reads`) + 코드(존재 확인 `os.path.isdir` 만)뿐이다 |

### 12-4b. 적대 검토 codex 1R(2026-10-26 · revision 4ee2eac0 · verdict REVISE · major 3 · 정본 = `~/.cys/pack/round/_reviews/cu-1111_…-r1-codex.json`)
| # | 지적(재현) | 반영 | 회귀 시험 · 뮤턴트 |
|---|---|---|---|
| 1 major | 사용자가 본 목록과 grant 가 푸는 목록이 묶이지 않음 — 다른 대화가 그 사이 scan 하면 「1번」이 다른 항목으로 넘어감 | scan 마다 `scan_id`+폴더 기록 · grant 는 `--scan` 필수 · 다르면 exit 7 `scan_replaced` | `test_grant_bound_to_seen_list` · M21 |
| 2 major | 합친 ID 그대로 저장 → 개별 거둠 뒤에도 묶음으로 권한 유지 | 장부 키 = 구성원 ID · 합친 ID 거둠 = 구성원 전부 · 옛 키 읽을 때 펼침 | `test_member_revoke_removes_everywhere` · `test_legacy_merged_key_normalized` · M22·M23·M24 |
| 3 major | 장부 저장 뒤 감사 기록 → 기록 실패해도 active 남음 | grant·recheck 활성화 = 기록 먼저(실패면 장부 불변) · revoke = 저장 먼저(실패해도 안전한 쪽) | `test_ledger_failure_leaves_no_active` · `test_recheck_ledger_failure_keeps_pending` · M25 |
| 논쟁점 | request-prompt 가 「아니요」 답도 통과 | `--meaning yes|no|unclear` 필수 · yes 아니면 exit 5 | `test_request_prompt_needs_meaning_yes` · M26 |
codex 가 못 한 것(정직): 읽기 전용 샌드박스라 단위 시험을 돌리지 못했다(메모리 대체 검증만) — 시험은 이 워커가 돌렸다(45 · 뮤턴트 26/26).

**codex R2**(revision 02c171d4 · verdict REVISE · major 1 · 정본 `…-r2-codex.json`): 1R 3건 해소 확인(목록 바인딩·감사 기록 순서 「확인했다」). 새 major 1 = **1R 반영이 만든 결함** — `recheck` 가 합친 ID 의 상태를 첫 구성원으로 대표해 ① 거둔 구성원까지 「맡습니다」라고 말하고 ② 첫 구성원이 active 면 다음 pending 구성원을 활성화하지 않았다. 반영 = 구성원마다 장부 보유·상태를 따로 계산(`states` 반환 · 맡기지 않은 구성원은 「맡기지 않으셨습니다」로 분리) · 회귀 `test_recheck_merged_reports_per_member` · `test_recheck_merged_activates_all_pending_members` · M27·M28. 시험 47 · 뮤턴트 28/28.

**codex R3**(revision f3ab895a · verdict **ACCEPT** · major 0 · 정본 `…-r3-codex.json`): R2 두 실패 시나리오 해소 확인 · 추가 수정 요구 없음. 정직 고지: 세 라운드 모두 codex 는 읽기 전용 샌드박스에서 메모리 대체 검증만 했고(R3 = 41건) 실제 OS 탐지·저장은 돌리지 않았다.

### 12-5. 1.1.12 후보(BACKLOG 한 줄 — master TODO 에 옮겨 적을 것)
- D1-ⓑ 장부 + 훅 차단: 장부가 있는 기계에서 본부 master 의 `mcp__computer-use__*`·`mcp__claude-in-chrome__*` 를 장부 밖이면 거부(role-capability-gate 에 본부 master 축).
- (실기 E2 ⑷) computer-use 가 cysr 을 터미널로 못 알아봐 「Claude desktop app」 이라고 안내하는 문제 — 스킬 `computer-control` 에 「cysr 로 바꿔 말하라」 고지를 넣었다(커밋 이 줄과 같은 커밋) · 2.1강 「안 되는 것」 표 반영은 master 경유(이 워커 범위 밖) · 근본(벤더 터미널 표)은 우리 밖.
