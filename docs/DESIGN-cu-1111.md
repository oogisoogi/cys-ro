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

> **개정(2026-10-26 · TICKET=cu-1111-precedent · 근거 = 박사님 원문)** — 위 문단은 크롬에 한해 뒤집혔다. 박사님 원문(10-26 21:0x): 「크롬 조작을 위해 /chrome 실행, 크롬 껐다켜기 같은 작업을 주인에게 시키지 말고 마스터가 직접 하는 방법을 찾아라.」 · (21:3x) 「보안 관련해서 사용자가 계속 승인을 해주어야 하는 일이 발생하면 사실상 자비스를 사용하는 의미가 많이 퇴색한다.」 → 「바로 가능」 = **이미 켜져 있거나, 마스터가 직접 켤 수 있는 것**이다. 크롬의 기본 켜기·연결 파일·크롬 다시 켜기·좌석 재시작은 마스터가 `chrome-enable` 로 한다(§13). 사용자 손으로 남는 것 = 맥 권한 스위치(OS 가 사람만 누르게 막음) · 확장 설치·로그인 · 비밀번호 입력. 무엇을 묻고 무엇을 먼저 정하는지는 §14(선례 기반 이양).

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
| `chrome` | 로그인된 크롬으로 웹 일(지메일·구글 문서·클라우드플레어 화면 등) | ⑴크롬 앱 존재(`/Applications`·`~/Applications`) ⑵확장 ID `fcoeoab…` 폴더가 어느 프로필에 있는지(프로필 **이름은 출력하지 않고** 「프로필 n개 중 k개」) ⑶확장 켜짐(`Preferences` 의 그 ID 항목 `state`·`disable_reasons` 만) ⑷연결 파일 S5 존재 + 가리키는 실행 파일 존재 ⑸`claudeInChromeDefaultEnabled` | ⑴없음 → 안 됨(「크롬이 없습니다」 + 설치는 사용자 선택) · ⑵~⑸ 전부 참 → 바로 · ★(개정 cu-1111-precedent) ⑵⑶ 참이고 거짓이 ⑷·⑸뿐 → **바로**(「제가 할 것: 크롬 기본 켜기 · 연결 파일·크롬 다시 켜기」 → 넘기면 마스터가 `chrome-enable`) · ⑵⑶ 거짓 → 손 · 값을 못 읽음 → ? | 손 칸 = 웹 스토어 설치·로그인·압정(C2)만. ~~마스터 칸 `/chrome` → Enabled by default(C1·G2) → 크롬 완전 종료 후 다시 켜기(G3) → cysr ↻ 재시작~~ → **마스터가 직접(§13)**. 「Browser extension is not connected」면 먼저 마스터가 좌석 재시작(§13 ④) → 그래도면 `/status` Organization ↔ 확장 계정 맞추기(G4·C3 · 확장 로그인 = 사람). 로그인·보안문자·결제·영구 삭제는 §14 표를 따른다 |
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
| `chrome` | `%LOCALAPPDATA%\Google\Chrome\User Data\<프로필>\Extensions\fcoeoab…` · 연결 파일 = 레지스트리 `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.anthropic.claude_code_browser_extension`(`reg query` · 읽기 · ★출력은 바이트로 받아 OEM → ANSI 코드페이지(`GetOEMCP`·`GetACP`)로 푼다 — 끝내 안 풀리면 대체 문자 · 디코드 실패가 판정을 바꾸지 않는다) · `claudeInChromeDefaultEnabled`(좌석 설정 폴더 `CLAUDE_CONFIG_DIR` 의 것만 · ★키 없음 = 꺼짐 → 손 칸 단계 「/chrome 기본 켜기」 — 근거: Claude Code 2.1.310 시작 판정 `--chrome` → `CLAUDE_CODE_ENABLE_CFC` → 이 키 → 없으면 false · 공식 문서 code.claude.com/docs/en/chrome 「Enable Chrome by default」 · cysr 좌석은 `--chrome` 없이 뜬다(`agents.json` cmd · 실측 ps) · 윈 실기 r2) · ★(개정 cu-1111-precedent) 키 없음·꺼짐·연결 키 없음 = 「손 칸 /chrome」이 아니라 **바로(마스터가 `chrome-enable`)** — 윈 실기(10-26 20:3x) `claude -p --chrome`(좌석 `CLAUDE_CONFIG_DIR`) 1회로 연결 키 자동 생성 실측 | 맥과 같은 규칙 · WSL 안이면 안 됨(W6) |
| `connectors` | 맥과 같음 | 맥과 같음 |
| `screen` | — | **안 됨**: 「윈도우에서는 이 칸의 마스터가 화면을 조작할 수 없습니다(공식 · G8·W1). Claude 데스크톱 앱에서는 가능합니다 — 그 앱에 직접 시키셔야 합니다.」 + 데스크톱 앱 설치 여부만 덧붙임 — 근거 순서: ⑴`%LOCALAPPDATA%\AnthropicClaude`·`%LOCALAPPDATA%\Programs\Claude` ⑵MSIX 사용자 자료 폴더 `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc`(실기: MSIX 설치 `C:\Program Files\WindowsApps\Claude_2.19675.0.0_x64__pzs8sxrjxfjjc` · 패키지 앱 자료 = `LocalAppData\Packages\<패밀리 이름>` = Microsoft Learn MSIX 문서) ⑶`%ProgramFiles%\WindowsApps` 이름 목록(`Claude_*_pzs8sxrjxfjjc`) — 목록 권한 거부가 흔하므로 거부면 「?」(확인 못 함) · 목록을 읽었는데 없으면 「찾지 못했습니다」 |
| `apps` | 카탈로그 앱 존재(시작 메뉴 바로가기·알려진 설치 경로) | `screen` 이 안 됨이므로 「화면 조작 불가 · 스크립트 길은 아래」 |
| `script` | 한글 = 공식 자동화(OLE · `HWPFrame.HwpObject`) · 오피스 = COM — **존재 판정만**(레지스트리 ProgID 읽기) | 1.1.11 = **?** 고정(「윈도우 스크립트 길은 확인 중」) — 실제 COM 호출은 윈 실기 뒤 별 티켓(보안 모듈 창·UIPI W3 확인 필요) |
| `files` | 경로 존재만 | 바로(윈도우는 폴더 보호 창이 없다 — 단 「제어된 폴더 액세스」가 켜져 있으면 차단될 수 있음 → 윈 실기 확인 항목) |
| `browser-alt` | 맥과 같음 | 맥과 같음 |

**출력 인코딩(정정 · 윈 실기 ①)**: 윈 파이프의 파이썬 기본 stdout 은 ANSI 코드페이지(cp949)라 「—」(U+2014 · cp949 에 없음)에서 `UnicodeEncodeError` → `scan` rc 1 이었다. 도구는 stdout·stderr 를 **UTF-8 로 고정**한다 — 마스터의 Bash 도구(Git Bash)·PowerShell 도구는 출력을 UTF-8 로 읽으므로 콘솔 코드페이지로 쓰면 죽지 않아도 마스터 쪽 한글이 깨진다. cysr 좌석은 `PYTHONUTF8=1` 로 뜨므로(`src/lib.rs` `spawn_env_pairs`) 실경로에서 드러나는 쪽은 오히려 위 `reg query` 디코드 결함이다. 윈 재실기 r2(10-26 19:5x): 기본·`PYTHONUTF8=1`·`-X utf8` 세 방식 rc 0 · stderr 0. ⚠시험 조건 기록: `python -I` 는 `PYTHONUTF8` 등 환경변수를 무시하므로 「PYTHONUTF8 조건」 실험에 `-I` 를 섞지 않는다.

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
| 사용자 설정을 대신 켜기 | ~~`.claude.json`·크롬 `Preferences`·`agents.json` 은 **읽기만** · `/mcp`·`/chrome` 토글은 사용자 손 · 기본값 = 「묻고 나서」~~ → **개정(cu-1111-precedent · 박사님 10-26 21:0x 「/chrome 실행, 크롬 껐다켜기 같은 작업을 주인에게 시키지 말고 마스터가 직접 하는 방법을 찾아라」 · 21:5x 「우리 선례를 1.1.11에 적용하여 컴퓨터 유즈 자동화 기능을 보완하자」)**: 쓰기는 `chrome-enable`·`chrome-disable` 두 동작만 · 좌석 `.claude.json` 의 `claudeInChromeDefaultEnabled` **한 키**(공식 `/chrome`·`/config` 토글이 쓰는 같은 키 · 다른 칸 무변경 · 원래 값 기록 → 되돌리기) · 연결 파일은 Claude Code 자신이 만든다(헤드리스 1회) · 크롬 `Preferences`·`agents.json` 은 여전히 읽기만 · `/mcp`(computer-use)는 사용자 손 유지(§14 후보) · 기본값 = 「마스터가 정하고 보고」(§14) · 그 밖 동사(scan·grant·guide·recheck·revoke·status)는 여전히 읽기 전용(시험 `test_settings_files_unchanged_and_writes_only_state`) |
| 개인정보 외부 전송 | 분석 = 「무엇이 있고 연결됐는가」까지 · 출력 금지 목록 §3-3 · 보호 폴더 열람 0 · 네트워크 호출 0 |

## 7. 치명 위험 4군(cys 개발자 ABSOLUTE ANCHOR)

| 군 | 이 기능에서 | 판정 |
|---|---|---|
| ①폭주(재시도·큐 상한) | 도구 = 사람 말 1회당 1회 실행 · 재시도 루프 없음 · 스케줄 잡·백그라운드 프로세스 없음 · 외부 호출은 `reg query`·`open` 1회씩(각 5초 상한) · 탐지 대상 = 고정 카탈로그(앱 ≤ 20 · 크롬 프로필 ≤ 20 · 넘으면 앞 20개 + 「더 있음」) · 장부 줄 수 상한(1,000 — 넘으면 오래된 거둠 기록부터 정리) | 해당 없음에 가깝다(상한 명시) |
| ②무clear(컨텍스트 무한 증가) | `say` 상한(목록 ≤ 25줄 · 안내 1단계 ≤ 8줄) · 훅 없음(D3) → 매 턴 주입 0 | 해당 없음(상한 명시) |
| ③자가치유 전멸 시 페일백 | 탐지 하나가 실패해도 그 항목만 「?」(전체 실패 0) · ctypes 로드 실패·파이썬 없음 → 마스터가 정적 안내(워크숍 「처음 한 번 준비」 페이지)로 폴백 · 장부 손상 → 읽기 실패 시 장부 없음으로 보고 `ledger.jsonl` 은 보존(덮어쓰기 0) | 페일백 경로 명시 |
| ④전 pane 사망 | ~~프로세스 종료·재시작 코드 0 · ↻ 재시작·크롬 재시작은 **사용자에게 안내만**~~ → 개정(§13): 크롬 = 정상 종료 1회만(안 닫히면 그대로 · 강제 0 · 재시도 0) · 좌석 재시작 = 앱 ↻ 와 같은 `cys rotate --skip-depts`(저장 검증 → 복원)를 **이 턴 뒤 30초 지연·분리 프로세스 1개**로 · 「할 일 없음」이면 외부 명령 0(시험 `test_enable_already_on_is_noop`) · `open` 은 설정 앱·크롬만 | 재시작 경로 = 이미 쓰는 ↻ 경로 재사용(새 재시작 코드 0) |

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
| E5 | 박사님 윈 노트북 · 윈 master 실기 r1(10-26 19:4x · 도구 = int/1111 ae41322c) · 원 계정 좌석 | scan · self-test · status + 대조표(Get-AppxPackage · 레지스트리 · 크롬 프로필) | **결함 3건**: ① 기본 콘솔(stdout cp949 · UTF-8 모드 꺼짐)에서 scan rc 1 `internal:UnicodeEncodeError`(범인 「—」 U+2014 · self-test·status 는 rc 0) ② `-X utf8` 로는 rc 0 이지만 `_run`(text=True)이 `reg query` 의 cp949 출력을 UTF-8 로 못 읽음(0xbf) ③ Claude 데스크톱 앱 = MSIX(`WindowsApps\Claude_2.19675.0.0_x64__pzs8sxrjxfjjc`)인데 「찾지 못했습니다」. 그 밖 대조표: 확장 fcoeoab… = Default 프로필 있음 · NativeMessagingHosts 키 없음(→ 크롬 손 칸 판정은 맞음) · 한글·Word ProgID 있음 · `Get-MpPreference` 0x800106ba(주 백신 V3) · 나머지 일치. 수리 = 커밋 621977c6(출력 UTF-8 고정 · OEM→ANSI 디코드 · MSIX 근거 순서) · 시험 50 · 뮤턴트 33/33 |
| E6 | 같은 노트북 · 윈 실기 r2(19:5x · 도구 = 621977c6) | 기본 · `PYTHONUTF8=1` · `-X utf8` 세 방식 scan | ① 세 방식 rc 0 · stderr 0 통과 ③ 「설치돼 있습니다」 통과 ② **불통과**: chrome `hand`·`unknown:true` · missing `["nmh"]` — nmh 는 이제 바르게 false(디코드 수리 동작) · unknown 원인 = 좌석 설정 폴더 `.claude.json` 에 `claudeInChromeDefaultEnabled` 키 없음(개인 `~/.claude.json` 에만 있음 — master 결정: 개인 프로필을 대신 읽지 않는다). 수리 = 커밋 9c19a828(키 없음 = 공식 기본값 꺼짐 → 손 칸 「/chrome 기본 켜기」 · 근거 = 2.1.310 시작 판정 · 좌석은 `--chrome` 없이 뜬다) · 시험 51 · 뮤턴트 34/34. 시험 조건 기록: `python -I` 는 `PYTHONUTF8` 을 무시한다 |
| E7 | 같은 노트북 · 윈 실기 r3(도구 = 9c19a828) | scan | **통과**: rc 0/0 · chrome `hand`·`unknown:false` · 「/chrome 기본 켜기 · 크롬 다시 켜기」 · missing `["default_on","nmh"]`(단계 순서와 같음 · master 수용) · 나머지 칸 r2 와 동일 → int/1111 병합(6d8d4468) |

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

---

## 13. 크롬 = 마스터가 직접 켜고 다시 켠다 (TICKET=cu-1111-precedent 1단계 · 2026-10-26 · 브리프 `~/axdev/master/briefs/2026-10-26-chrome-auto-enable.md` 흡수)

박사님 원문(10-26 21:0x): 「크롬 조작을 위해 /chrome 실행, 크롬 껐다켜기 같은 작업을 주인에게 시키지 말고 마스터가 직접 하는 방법을 찾아라.」

### 13-1. 켜기 경로 비교(실측 · 맥 · 격리 설정 폴더)
측정 방법: 임시 HOME·임시 `CLAUDE_CONFIG_DIR`·가짜 API 키로 `claude -p --output-format stream-json --verbose` 를 띄워 시작 이벤트(`system/init`)의 도구 목록만 본다(실 설정·실 크롬 무접촉 · 스크립트 = scratchpad `cfc/probe.py`).

| # | 경로 | 실측·근거 | 판정 |
|---|---|---|---|
| ⓐ | 좌석 `settings.json` `env.CLAUDE_CODE_ENABLE_CFC="1"` | 격리 실측 = 크롬 도구 0 — 그러나 **⓪(아무것도 안 함)·ⓒ(`--chrome`)도 0** → 원인은 경로가 아니라 가짜 키: 바이너리 문자열 「[Claude in Chrome] Disabled: OAuth token has no scope accepted by /api/oauth/validate (… env-var and setup-token sessions default to user:inference only)」. 정적 근거: 「Claude Code ignored CLAUDE_CODE_ENABLE_CFC in this project's settings: a project can't turn on Claude in Chrome」(**프로젝트** 설정만 무시 · 원격·Cowork 세션 필터 `R6e`) → 사용자 설정은 막히지 않을 것으로 보이나 **행동 실측 불가**(구독 OAuth 가 필요 · 워커는 실 설정 폴더로 띄우지 않는다) | 비권고 — 미실측 · 그리고 환경 값이 키보다 앞서므로(판정 순서 ②) 사용자가 `/chrome` 에서 꺼도 다시 켜진다(사용자 통제 상실) |
| ⓑ | 좌석 `.claude.json` `claudeInChromeDefaultEnabled=true` | 시작 판정(2.1.310 바이너리 원문): `--chrome`/`--no-chrome` → `CLAUDE_CODE_ENABLE_CFC` → 원격이면 무시 → **이 키** → 없으면 false. 공식 토글 2곳이 같은 키를 **갱신 함수로** 쓴다: `/chrome` 의 `toggle-default` = `Re(_=>({..._,claudeInChromeDefaultEnabled:c}))` · `/config` 「Claude in Chrome enabled by default」 = 같은 꼴. 행동 근거 = 맥 실기 E2⑵(키 true → `--chrome` 없이 켜짐) · 윈 실기 3단계(좌석 키 True → claude-in-chrome 노출) | **권고** — 공식 토글과 같은 키 · 사용자가 언제든 `/chrome` 에서 끌 수 있음 · 되돌리기 = 원래 값 |
| ⓒ | `agents.json` cmd 에 `--chrome` | 판정 순서 ①(가장 강함) — 사용자가 `/chrome` 에서 꺼도 매번 켜짐 · 앱(Rust)의 좌석 명령 생성부를 바꿔야 함 | 비권고 — 범위·사용자 통제 상실 |

**우리 쓰기가 좌석의 쓰기를 덮는가(codex R1·R2 blocking)**: Claude Code 2.1.310 바이너리 원문(`saveConfigWithLock`) = `let P=${y}.lock`(y = 전역 설정 파일 `getGlobalClaudeFile()`) 로 proper-lockfile 잠금(`lockfilePath:P`) → **잠금 안에서 파일을 다시 읽고**(`Sd()`) 갱신 함수 적용 → 0600 으로 쓰기. 그래서 `write_chrome_key` 는 **같은 잠금**(`<.claude.json>.lock` 폴더 mkdir · 원자적)을 쥔 채 잠금 안에서 다시 읽고 → 키 하나 → 원자 교체 → 잠금 해제한다. 그동안 Claude 는 재시도하며 기다리고, 풀리면 우리 결과를 다시 읽어 그 위에 쓴다(우리 키 보존 · 우리도 그들 것을 덮지 않음). 남이 쥔 잠금은 지우지 않는다(오래된 것 포함) — 5초 안에 못 잡으면 쓰지 않고 실패. 덧붙여 교체 직전 원본 바이트 재확인(잠금을 안 지키는 다른 작성자 대비 · 3회).

반대 방향 — 실행 중 세션이 우리 키를 옛 사본으로 덮는가: 격리 세션(SessionStart 훅 8초 대기) 도중 키를 써 보니 세션이 그 뒤 파일을 다시 쓰지 않아 **판정 불가**(키는 남음). 공식 토글이 갱신 함수(읽은 현재값에 키만 덮음) 꼴이라 덮어쓸 가능성은 낮다고 보지만 Med — 완화: 키는 좌석 재시작 직전에 쓰고, 재시작 뒤 `recheck chrome`/`scan` 이 키를 다시 확인한다(사라졌으면 「제가 할 것」으로 다시 뜬다).

### 13-2. 연결 파일(NMH)
- 실물(맥 · 읽기만): `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.anthropic.claude_code_browser_extension.json` → `path` = **좌석 설정 폴더**의 `chrome/chrome-native-host`(셸 래퍼 · `exec …/claude --chrome-native-host` · 「Generated by Claude Code - do not edit manually」). 사용자당 1개 파일이라 **마지막으로 크롬 연동을 켠 설정 폴더**를 가리킨다.
- 만드는 주체 = Claude Code(크롬 연동이 켜진 채 **시작**할 때 · 바이너리 「Installed native host manifest at:」·윈 「Registered native host for … in Windows registry」). 우리는 파일을 손으로 쓰지 않고 좌석 설정으로 `claude -p --chrome --max-turns 1 --tools "" --disallowedTools mcp__claude-in-chrome "<무해 문장>"` 를 상태 폴더에서 1회 돌린다(윈 실기 10-26 20:3x 의 같은 길 · 도구 0 · 응답 1회 비용).
- ⚠ 부수 효과(바이너리 문자열): 「First-time install detected, opening reconnect page in browser」 — 확장이 깔려 있으면 처음 만들 때 크롬에 「다시 연결」 탭이 하나 열린다(사용자 화면에 보임 · 해롭지 않음 · 실기 확인 항목).
- 격리 실측에서는 가짜 키 세션이 크롬 연동을 시작 전에 끄므로 생성 0 — 생성 실측은 윈 실기(성공)와 맥 실기(의뢰) 몫.

### 13-3. 크롬 다시 켜기(필요할 때만)
- 조건 = **이번 실행에서 연결 파일이 새로 생겼고 크롬이 그 전부터 켜져 있었다**(공식 문서: 「Chrome reads this file on startup, so if the extension isn't detected on your first attempt, restart Chrome」). 그 밖에는 크롬을 건드리지 않는다.
- 순서 = 사용자 입력 유휴 ≥ 20초(맥 `ioreg` HIDIdleTime · 윈 `GetLastInputInfo` · 선례 `hancom-front-needs-idle-gate`) → 못 채우면 기다림(최대 `--wait` 초 · 상한 540) 뒤 「미뤘습니다」로 끝(`pending: chrome_restart` · 다음 턴 재호출) → 화면 알림 1줄(`cys feed push --kind computer-control --tier d` · 정보성) → 3초 → **유휴 재확인**(알림을 보고 손을 댔으면 닫지 않고 미룸 · codex R1 blocking) → 정상 종료 → 닫힘 확인(20초) → `--restore-last-session` 으로 켬 → 창·탭 수 전후 대조.
- **연결 파일 만들기에도 같은 관문**(codex R1·R2 blocking): 처음 만들 때 Claude Code 가 크롬에 「다시 연결」 탭을 열 수 있어(§13-2) — 크롬이 꺼져 있어도 그 탭이 크롬을 띄울 수 있으므로 **크롬 상태와 무관하게** 유휴가 아니면 만들기 자체를 미룬다(`pending: nmh`).
- **미룬 일은 빚으로 남는다**(agy R1 blocking): 상태 파일 `pending_chrome_restart`·`pending_seat_restart` → 다음 `chrome-enable` 이 크롬이 켜져 있으면 재시작 → 좌석 재시작 순으로 갚고 지운다 · 그 사이 크롬이 꺼졌으면 크롬 빚 청산(다음에 켤 때 연결 파일을 읽는다) · 크롬 상태를 모르면 계속 미룸.
- 정상 종료(선례 `never-kill-user-app-without-consent` · 강제 종료 0): 맥 = 크롬 자동화 허락(S3 = 0)이 있으면 AppleScript `quit` · 없으면 이 사용자의 크롬 **본 프로세스 pid 하나**에 SIGTERM(크롬이 정상 종료로 처리 · 이름 일괄 종료 `pkill` 금지 = 워커 지침 §1-4) · 윈 = 창마다 `CloseMainWindow()`(닫기 단추와 같음). 20초 안에 안 닫히면 **그대로 둔다**(「강제로 끄지 않습니다」 + 사용자가 닫았다 켜면 연결됨).
- 창 수: 맥은 자동화 허락이 있을 때만 셈(없으면 허락 창을 띄우지 않으려고 「확인 못 함」) · 윈은 `MainWindowHandle` 있는 크롬 프로세스 수(근사). 줄었으면 「최근 닫은 탭」 안내.

### 13-4. 마스터 좌석 재시작(마스터가 스스로)
- 크롬 연동은 **시작할 때** 정해진다(키 = 「이후 시작하는 세션」). 실행 중 좌석에 붙이는 길은 터미널에 없다(IDE 호스트 전용 `claude_in_chrome_at_startup` 만 존재 — 바이너리).
- 데몬 경로 조사: `cys cycle-agent` = `/clear` 사이클(프로세스 재시작 아님) · `cys node-recover` = **죽은** 좌석만 · `cys restore --include-master` = 죽은 역할 일괄 재기동 · **`cys rotate` = 앱 ↻ 재시작 단추(rotate_daemon)와 같은 5단(저장 검증 → 데몬 교체 → 복귀 표식 → 팩 반영 → 조직 복원)** — 사용자에게 「↻ 눌러 주세요」라고 하던 바로 그 일이다.
- 집행 = `chrome-enable` 이 끝날 때 **분리된 프로세스 1개**(이 도구의 `seat-restart-wait` · 맥 `start_new_session` · 윈 NEW_PROCESS_GROUP|NO_WINDOW — 숨은 새 콘솔 · 콘솔 떼기(DETACHED)는 자손마다 새 창이라 쓰지 않는다 · H-WIN-16)가 30초 뒤부터 5초 간격으로 **턴 종료 두 신호가 두 번 연속** 맞을 때만 `cys rotate --skip-depts`: ① 좌석 출력 유휴(`cys status --json` 의 그 좌석 `idle_secs` ≥ 20) ② 좌석 자신의 세션 기록(`registered_session_id` → `<좌석 설정>/projects/*/<id>.jsonl`)의 마지막 대화 줄 = `assistant` · `stop_reason: end_turn`(읽는 칸 = type·stop_reason 뿐 · 내용 0). 출력이 조용해도 도구 응답을 기다리는 중이면 마지막 줄이 `tool_use` 라 재시작하지 않는다(codex R2 blocking). rotate 의 저장 검증([DRAIN])이 마스터에게 저장을 시킨 뒤 재시작·이어하기(⚠ rotate 는 저장 확인 실패에도 끝까지 간다 — `ROTATE_RC_DRAIN_PARTIAL` · 그래서 턴 종료 확인이 이 대기 쪽에 있어야 한다).
- 좌석 ID(`CYS_SURFACE_ID`)가 없거나 15분 안에 턴 종료를 확인 못 하거나 rotate 가 중단 코드로 끝나면 **재시작하지 않고 빚**(`pending_seat_restart`)으로 남긴다 — 빚은 예약 성공이 아니라 **재시작 성공**에서만 지운다 · 예약이 살아 있는 동안(`seat_restart_scheduled_at` · 17분) 다음 `chrome-enable` 은 중복 예약하지 않는다(codex R2). 마스터 지침: `chrome-enable` 뒤 새 일을 시작하지 않고 턴을 끝낸다(스킬).
- 최소 대안(1.1.12 후보 · 미구현): 마스터 좌석만 정상 종료 → `cys restore --include-master`(resume) — 다른 좌석을 건드리지 않지만 「살아 있는 좌석 1개만 재시작」 RPC 가 없어 새 데몬 코드가 필요하다.
- 실기 확인 항목: ① 분리 프로세스가 좌석 pty 종료 뒤에도 살아 rotate 를 끝까지 하는지(맥·윈) ② 윈 좌석이 작업 개체(job)에 묶여 분리가 막히는지.

### 13-5. 되돌리기 `chrome-disable`
켤 때 기록한 **원래 값**으로(원래 키가 없었으면 키를 지움 · 원래 값은 키를 쓰기 **전에** 디스크에 기록 — codex R1 · 키가 이미 켜져 있어 연결 파일만 만들 때도 만들기 전에 기록 · 다시 켜면 앞선 끄기의 「키 되돌림 끝」 표지를 지워 다음 끄기가 키를 다시 되돌린다 — codex R3 · 그때는 새 주기이므로 원래 값 = 다시 켜기 직전 값(그 사이 사용자가 바꾼 값을 옛 값으로 덮지 않는다 — codex R4)) · 우리가 만든 연결 파일만 지움(맥 = 만들 때 sha256 · 윈 = 만들 때 등록값(매니페스트 경로) + 그 매니페스트 sha256 → 지우기 직전 지금 값과 대조 · 그 사이 다른 프로그램이 고쳐 썼으면 두고 알림 · codex R1 blocking) · 지우기 실패면 되돌리기 기록을 남겨 다음에 다시 · 기록이 없으면 키를 false 로 · 좌석 재시작은 기본 안 함(`--seat-restart auto` 로 요청).

### 13-6. 시험·뮤턴트(이 단계)
시험 52 → 68(크롬 판정 4 개정·신설 + `TestChromeEnable` 15 + `_act` 표준입력 1) · 뮤턴트 34 → 51(M35~M51 · 51/51 KILLED). 외부 명령은 전부 `_act` 하나를 지나고 시험은 `CYS_CC_FAKE_ACT` 기록 파일로 대체한다(실제 크롬·좌석·`claude` 무접촉). 단언: 키 하나만 바뀜·권한 유지 · 할 일 없으면 외부 명령 0 · 재시작은 분리·지연 · 헤드리스 claude 는 상태 폴더에서 · 「새 연결 파일 ∧ 크롬 켜져 있었음」일 때만 크롬 재시작 · 알림 → 종료 → 켬 순서 · 강제 종료 문자열 0(`-9`·`KILL`·`pkill`·`killall`·`taskkill`·`Stop-Process`·`Force`) · 유휴 관문 · 안 닫히면 그대로 · 기다림 상한 · 기록 실패면 키 불변 · 되돌리기 원래 값·남이 고친 파일 보존.


---

## 14. 선례 기반 이양 — 마스터가 먼저 정하고 보고 (TICKET=cu-1111-precedent 2단계 · 2026-10-26~27)

### 14-1. 원칙(박사님 원문 그대로)
- 08:54 「사용자의 컴퓨터를 분석해서 마스터가 통제 가능한 항목을 제시하고 사용자가 선택하여 통제권을 넘기는 구조이다. 마스터가 바로 통제가 가능한 것은 자동으로 가져오고, 사용자의 손길이 필요한 것은 친절한 가이드를 제시한다.」
- 21:3x 「보안 관련해서 사용자가 계속 승인을 해주어야 하는 일이 발생하면 사실상 자비스를 사용하는 의미가 많이 퇴색한다. 상남자 프롬프트로 클로드를 구동하는 것도 같은 이유이다.」
- 21:4x 「바깥으로 새는 일과 관련하여 디모데, 당회록 등의 사례가 있었다. 자료 자체로만 보면 외부로 들고 나는 일이 맞다. 하지만 교회라는 상황, 한정된 상황 속에서 실제적으로 안전하게 사용되는 환경 등의 조건이 붙을 때는 자동화 권한을 허락했다. 이런 경우를 고려해서 사용자에게 물어서 결정하는 것이 필요하다. 기계적인 적용은 피해야 한다. 로그인도 마찬가지이다. 당장 크롬 사용 권한만 해도 대부분의 로그인 접근을 허용한 셈이다. 사용자의 컴퓨터 유즈 상황과 패턴을 가능한 파악해서 맞춤형으로 적용해야 한다.」
- 21:5x 「사람이 인공지능을 사용할 때는 보다 고차원의 분석과 판단을 통해 주인의 필요에 맞는 선택과 결정을 기대하는 것이다.」 → 「좋다. 보고는 하자. 그리고 우리 선례를 1.1.11에 적용하여 컴퓨터 유즈 자동화 기능을 보완하자.」

이것을 제품 규칙 다섯으로 옮겼다:
1. **기본값 = 마스터가 먼저 정하고 한 뒤 짧게 보고**(「이렇게 했습니다 · 다르게 원하시면 말씀해 주세요」) — 묻지 않는다. `adopt` 가 「바로」 칸을 먼저 맡는다(08:54 「바로 통제가 가능한 것은 자동으로 가져오고」).
2. **한 번 묻기 = 선례로 갈리지 않는 새 유형일 때만** — 답은 상시 기록(`decisions.json`)이고 같은 항목은 다시 묻지 않는다(도구가 `already_decided` exit 7 로 막는다 · 사용자가 스스로 바꾼 때만 `--user-changed`).
3. **로그인·바깥 전송은 일괄 금지가 아니다** — 이미 쓰는 서비스(커넥터 연결 이름 · 설치된 카탈로그 앱 + 마지막 사용일)면 마스터가 하고 보고 · 쓰는지 모르면 한 번 묻기 · 처음 쓰는 서비스(=가입)면 건마다. 바깥 전송은 「누가·무엇을·어디로·실제로 안전한 환경인가」를 한 번 묻고(조건부 허락 = 조건 문장 필수) 그 뒤 상시.
4. **건마다 남는 칸**(상시 기록으로 바뀌지 않음) = 결제 · 서명 제출 · 새 서비스 가입 · 비밀번호/2단계/생체 입력 · 주인 이름으로 남에게 보내는 메시지·게시·삭제 · 약관이 자동화를 금지한 서비스 · 업데이트가 끼운 처음 보는 창의 비가역 선택.
5. **안 함**(우회 0 · 사유 문장) = 일부러 막힌 부류(관리자 권한 창·UAC·화면 캡처 차단·키보드 보안·안티치트·보안문자) · 설치 경계 절대 금지 3(원격 명령 통로·자격증명 대행·백신 우회).

개인 프로필 대리 읽기 금지(cu-1111 E6 master 결정)는 그대로다 — 사용 패턴은 **존재·빈도**만 본다(§14-3).

### 14-2. 이양 표(유형별 · 도구 `CATEGORIES` 와 1:1 · 시험·self-test 가 단언)
| 유형(ID) | 무엇 | 기본 결정 | 선례 근거(원문 = 각 파일 · `~/.claude/projects/-Users-oogisoogi-axdev/memory/`) | 제품 칸으로 옮긴 것 |
|---|---|---|---|---|
| `login` | 이미 쓰는 서비스 재로그인·OAuth 「허용」·만료 인증 갱신 | **do**(쓰는 서비스) · ask(쓰는지 모름) · each(처음 = 가입) | `test-login-approval-master-does`(10-01 「로그인 승인도 마스터가 할 수 있지 않은가? 알아서 진행하라」 · 10-02 「앞으로 필요에 의한 로그인, 권한 인증 같은 나의 검토가 필요하지 않은 작업들은 마스터가 알아서 진행하라」) | 「바로」 · 실제로 뜬 비밀번호·2단계·생체만 사람 |
| `credential_input` | 비밀번호·2단계 코드·생체 입력 | **each** | 같은 파일(「비밀번호 입력·2단계 인증 코드·기기 생체 인증(박사님 손이 물리적으로 필요)」) | 그 한 번만 사람 · 받지도 저장하지도 않음 |
| `payment` · `sign_submit` · `signup` | 결제 · 서명·동의 제출 · 새 서비스 가입 | **each** | `~/axdev/CLAUDE.md` 「master 가 바꿀 수 없는 예외 1」(「결제·서명 제출·새 서비스 가입 단추는 그 건마다 박사님 한 줄 허락」) | 유일하게 남는 「안 됨 → 사람」 칸 |
| `send_as_owner` | 주인 이름으로 남에게 보내는 메시지·게시·삭제 | **each** | `test-login-approval-master-does` 확장(10-21 「여전히 묻는 것 = … 박사님 이름으로 남에게 보내는 메시지·게시·삭제」) | 건마다 |
| `external_send` | 자료를 바깥으로 | **ask**(새 유형) → 상시 | `jarvis-purpose-no-repeated-approvals` 정정 절(10-26 21:4x 디모데·당회록) | 맥락 판단 · 한 번 묻고 상시 · 조건부 허락 |
| `settings_change` | cysr·클로드 좌석 설정(크롬 켜기 등) | **do** | `domain-management-master-delegated`(10-20 「관리범위는 확장한다 … 필요성이 확인되는대로 계속 권한을 확대할 것이다」) · `release-work-fully-autonomous`(10-11 「발행 관련 내용 전체를 자율적으로 진행하라」) | 권한은 필요 확인 시 넓어지는 방향 = 기본값 설계 근거 · 원래 값 기록(되돌리기) |
| `app_quit` | 사용자 앱 다시 켜기·닫기 | **do**(정상 종료만) | `never-kill-user-app-without-consent`(10-01 한글 미저장분 손실) | 정상 종료 · 저장 확인 · 강제 0 · 안 닫히면 그대로(§13-3) |
| `app_force_quit` | 멈춘 앱 강제 종료 | **each** | 같은 파일(「진단까지는 자율, 종료는 질문 1줄」) | 자동 저장본 확보 → 1줄 묻기 |
| `screen_op` | 앱을 앞으로 불러 누르기·입력 | **do**(유휴 20초 관문) | `hancom-front-needs-idle-gate`(10-25 「것죄은」 사고) | 모든 화면 조작 공통 관문 |
| `app_security_dialog` | 앱 자동화 보안 창 | **do**(공식 상시 설정 먼저) | SESSION_STATE 10-26 22:3x(한컴 공식 보안모듈 등록 → SaveAs 확인 창 0) | 창을 누르기 전에 창을 없애는 공식 설정 |
| `kakao_login` | 카톡 PC 로그인 | **do** + 고지 | SESSION_STATE 10-26 20:3x·22:2x(윈 T3 「다른 PC 강제 로그아웃」 · 박사님 윈 창 「당연히 로그인도 알아서 해야 할 것이고」) | 「한 대만 됩니다 — 다른 컴퓨터가 로그아웃될 수 있습니다」 |
| `terms_risk` | 약관이 자동화를 금지한 서비스(네이버 = `login`·`external_send` 대상에 「네이버/naver」가 있으면 자동 귀속) | **each** | SESSION_STATE 10-26 20:0x(네이버 약관 2026-10-01 자동화 수단 로그인·게재 금지) | 계정 정지 = 되돌릴 수 없음 → 건마다 |
| `update_dialog` | 업데이트가 끼운 처음 보는 창의 설치·동의·결제·로그아웃 | **each**(정지·질문) | winparity REPORT §10-4 ⑤ | 멈추고 본 것 그대로 묻기 |
| `blocked` | 관리자 권한 창·UAC·캡처 차단·키보드 보안·안티치트·보안문자 | **never** | winparity REPORT §10-2(1·2·3·4·5·10) | 「사람 손 1회 필요: 무엇」 |
| `install_boundary` | 원격 명령 통로·자격증명 대행·백신 우회 | **never** | `install-convenience-security-boundary`(09-09 절대 금지 3) | 그대로 유지(바깥 위험 = 수습 불가) |
| (목록 밖) | 새 유형 | **ask** → 상시 | 21:5x 「선례로 갈리지 않을 때만 한 번 묻는다」 | `basis: new_type` |

정직 고지: `install-convenience-security-boundary` 의 ⓐ「원격 명령 통로」는 09-10 박사님 재결정으로 **설치 도움 원격 세션**에 한해 조건부 허용으로 개정됐다(그 메모리 본문). 이 표의 `install_boundary` 는 브리프 지시(「그대로 유지」)대로 컴퓨터 통제 기능 안에서 상시 통로를 열지 않는다는 뜻이다 — 설치 도움 원격 세션 설계와는 별개.

### 14-3. 사용 패턴(맞춤의 근거 · 읽는 것 = 존재·빈도만)
- `services` = `.claude.json` 의 커넥터 연결 기록 이름(S8 · 이미 §3-3 에서 출력 허용) · `apps` = 카탈로그 앱 설치 여부 + 맥 `mdls -name kMDItemLastUsedDate <앱 번들>`(앱 번들의 Spotlight 메타데이터 · 날짜 → 「n일 전」 정수만) · 윈 = 설치 여부만(마지막 사용 = None).
- 읽지 않는 것: 크롬 방문 기록·쿠키·Login Data·키체인 · 개인 `~/.claude.json` · 메일·파일 내용(§6 · 시험 `test_no_protected_or_secret_reads` 가 `adopt`·`decide` 도 감시).
- §3-3 출력 허용 목록 추가: 「카탈로그 앱의 마지막 사용 n일 전」(보고 문장 근거로만).

### 14-4. 도구 계약(2단계에서 더한 것)
- `adopt` → `{"ok", "scan_id", "active", "hand", "not_now", "skipped", "next_action", "say"}` · 바로 칸(+처음 쓸 때만 묻는 칸)을 장부 `active`(by=adopt) · 이미 맡은 것은 건너뜀(멱등) · 사용자가 전에 거둔 항목(`take:<ID>` = deny)은 가져오지 않고 「전에 빼라고 하신 것」으로 알림 · 감사 기록 먼저.
- `revoke` 가 `take:<구성원 ID>` = deny 를 상시 기록 · `grant` 로 사용자가 다시 고르면 그 기록을 푼다.
- `decide <유형> [--subject] [--in-use yes|no|unknown] [--what]` → `{"decision": do|ask|each|never, "basis": precedent:<키>|standing:<시각>|new_type, "report"|"ask"|"say"}` · **쓰기 0**(시험 `test_decide_writes_nothing`).
- `remember <유형> --subject --answer-file --meaning allow|deny|conditional [--condition] [--user-changed]` → 상시 기록(키 = `유형:대상 정규화 sha256 앞 16자` — 대상 원문을 파일에 남기지 않음 · 표시용 `label` 은 가린 문자열) · each/never 유형 = exit 5 `not_recordable` · 이미 있음 = exit 7 `already_decided` · 조건부인데 조건 없음 = exit 2 · 답 원문은 sha256 만 · 감사 기록 먼저 · 상한 5,000 — **도달하면 옛 결정을 지우지 않고 새 기록을 거절**(exit 7 `decisions_full` · 지우면 그 항목을 다시 묻게 된다 · codex R1).
- 판정 순서(`judge` · 자가 발견 + codex R1 반영): 네이버 대상 login/external_send → each(약관) · each/never 유형 → 그대로(상시 기록 무시) · `login` 인데 `--in-use no`(처음 쓰는 서비스) → each(가입 · 상시 허락보다 먼저) · 상시 기록 있음(새 유형 포함) → 그 결정 · 모르는 유형 → ask(new_type) · login → 사용 패턴 · 그 밖 → 표의 기본 결정.
- 출력에 싣는 대상·한 일·조건 문자열은 이메일·긴 번호 모양을 `<이메일>`·`<번호>` 로 가린다(§3-3 · codex R1) · 기록 키 = 유형 + 대상 해시(목록 밖 새 유형은 유형 이름도 해시 · 대상은 **자르지 않고** 정규화 — 옛 판은 앞 120자였다 · ★한 대상 = 한 키 = 한 기록 — 옛 판 키 호환은 없다 · §16-10) · 조건 원문은 **기록 파일에만**(원장엔 답 해시만 · 가리면 허락 범위를 잃는다 · codex R2 #9) · 조건은 자르지 않는다(2,000자 넘으면 기록 거절 `condition_too_long` — codex R3) · 새 조건부 기록엔 원문 표지 `full` · ★조건은 **사용자 말 그대로** 기록한다 — 범위 낱말·받는 사람 목록 같은 조건 문법을 강제하지 않는다(§16-5 · D16) · 표지 없이 300자 이상인 옛 판 조건(끝이 잘렸을 수 있음)은 조건 확인이 있어도 each + `supplement: true`(그 답으로 다시 적으면 `--user-changed` 없이 덮인다 · 재질문 고리 0).
- 조건부 상시 허락 = `decide … --condition-met yes|no|unknown`(마스터가 이번 건을 조건과 대조): yes → do · no → each(이번만 묻기) · unknown(기본) → **check**(`condition` = 사용자가 한 말 원문 · 이번 건이 맞는지는 **마스터가 말뜻으로** 판단하고 다시 부른다 · 애매하면 그때만 사용자에게 1회 · §16-5) — 조건 확인 없이 do 를 내지 않는다(codex R2).
- 「이미 쓰는가」 대조 = **낱말 단위**(이름의 낱말이 전부 대상의 낱말 안에 있어야 일치 · 「카카오톡 로그인」 = 카카오톡 · 「wordpress.com」 ≠ Word · codex R2) · 대상의 접속 이름 = URL 은 파서의 실제 hostname(사용자정보·경로·쿼리 속 도메인은 대상이 아니다 · URL = 공백 전까지 통째로 파싱 · 끝 문장부호 제외 — 호스트 뒤 비ASCII 를 잘라 앞부분만 대조하지 않는다 · ★호스트는 **허용 꼴**(`_HOST_OK` = ASCII 글자·숫자·하이픈 라벨을 점으로 · 끝점 1개 허용)만 대조 — 제어 문자·%·비ASCII·빈 라벨 등 그 밖은 전부 모름 · 퓨니코드 라벨(`xn--`) = 모름(유효성을 못 잰다 · 정식 도메인 목록엔 없음) · URL 의 끝 = 글의 낱말 경계(ASCII 공백·탭·줄바꿈)뿐 — 그 밖 공백류(VT·U+3000·NBSP)는 URL 안에 남아 모름 · 호스트 없이 끊긴 `://` = 모름 · self-test 가 정식 URL 호스트 자리에 글자 하나를 끼운 전 꼴(ASCII 128 + 비ASCII 표본 7 × 16자리)을 돈다(codex R8)) · 그 밖은 도메인 모양 · 둘 이상이거나 깨진 URL(잘못된 포트 · 브라우저와 호스트가 갈리는 역슬래시) = 모름 → ask(codex R5·R6) · 대상에 도메인이 있으면 이름 닮음이 아니라 **정식 도메인 목록**(`SERVICE_DOMAINS` · 커넥터 이름·카탈로그 앱 ID → 로그인 도메인 · 점 경계 뒤끝 일치)으로만 일치 — `word.invalid`·`gmail.invalid`·`word.example.invalid`·`evilgmail.com` = 모름 → ask(codex R3·R4).
- ★**옛 판 키 호환 없음**(master#7d1b6e77 · §16-10): 옛 판 꼴(92c47060 `유형:정규화 원문` · ad474d66 `유형 원문:대상 해시` · 앞 120자 해시) 기록은 따르지도 막지도 않는다 — 이 기능은 이 티켓에서 처음 생겨 발행·설치 0 · 잘린 조건(옛 판 300자) 보완(`supplement`)은 조건부로만(`supplement_meaning`) · 그 기록 자리 교체(개수 그대로라 한도 무관).

### 14-5. 범용 조작 원칙(675 REPORT §10-4 · 박사님 22:0x 「업데이트와 관계 없이 항상 적용할 수 있는 범용적인 방법」 · 맥·윈 공통)
1. **저장 좌표·선택자 0** — 좌표는 그 동작 직전 스냅샷에서만 · **스냅샷 1장 = 상태를 바꾸는 동작 1개**(windows-mcp label 은 마지막 스냅샷 좌표) · 그 뒤 반드시 다시 찍는다.
2. **동작마다 검증** — 기대 결과 한 줄 → 동작 → 재촬영 대조 · 완료 판정은 결정론 증거(파일·내용·창 제목)로만. **「항상 성공」이 아니라 「항상 확인」**.
3. **경로 순서** = 앱 계약 API(COM·스크립트·명령행) → UIA 이름 → 픽셀(단일 모니터 원본 해상도) → 키보드 · 실패 시 다른 경로로 · 같은 경로·같은 시도 2회까지 · 다 실패하면 정지·보고.
4. 계약 API 가 있으면 먼저 쓰되 결과는 화면·파일로 확인 · COM 이 띄우는 승인 창도 화면 고리로 본다(→ `app_security_dialog` 공식 상시 설정).
5. **막힌 부류는 우회하지 않고 이름 붙여 넘긴다**(→ `blocked` never) · 업데이트가 끼운 처음 보는 대화상자의 비가역 선택 = 정지·질문(→ `update_dialog` each).

윈 실기 3단계 관측(10-26 21:5x · 윈 master 210)을 원칙의 사례로 둔다: ⑴ 한글 음절로 끝난 입력 뒤 Enter 가 IME 조합 확정에 먹혀 줄바꿈이 안 됨 → 한글 끝 입력 뒤엔 Enter 2회 또는 확정 키(원칙 2 = 결과 확인으로 잡힘) ⑵ 한글 화면 첫 입력 0글자(문서 초점 전) → 문서 클릭으로 초점 → 정확(원칙 2) ⑶ 카톡 = UIA 요소 미노출 → 좌표 조작(원칙 3 픽셀 경로 · 확률 낮음 · 확인 필수) ⑷ windows-mcp 가 자기 클릭 직후에도 USER_CONTROL(8~10초) 양보 → 동작 전 ControlStatus 확인(USER_CONTROL 은 끄지 않는다 — 사람 비상 정지) ⑸ PowerShell 5.1 스크립트의 한글 = UTF-8 BOM 필수 ⑹ 한글 COM SaveAs 보안 창 = 공식 보안모듈 등록으로 0(22:3x).

### 14-6. 속도 원칙 — **확정 = S9**(윈 실험 TICKET=win-speed 최종 · 윈 master 210 · 원장 윈 컴퓨터 `~/w1026/speed/ledger.md` 15/15 회차 검증 · master#291cc1d4 10-27 07:0x 채택 · 이 컴퓨터(맥)에서 원장 원본은 못 봄 — 수치는 master 전달분 그대로)
- **채택 S9**: ① 손 = Sonnet 서브에이전트(화면 고리) · master 는 지시와 결정론 판정만(서브에이전트의 「됐다」는 증거가 아니다) ② 오피스·한글 = **COM 1순위**(계약 API) ③ 기다림·창 찾기 = **PowerShell 표적 UIA 조회**(그 창·그 요소만) — windows-mcp `WaitFor` 는 매 호출 데스크톱 전체 트리를 훑어 15~25초라 **금지** ④ 고정 `Wait` 금지 · USER_CONTROL 은 끄지 않는다(사람 비상 정지 보존 — 원인을 없애는 쪽으로).
- **실측(S0 대비)**: 시간 **−70%** · 토큰 **−56%** · 성공 **15/15**. 판독 = 빨라진 것은 한 동작이 아니라 **동작 수(124 → 43)** — 경로를 앞당겨(COM·표적 조회) 화면 고리 자체를 줄인 효과다.
- **불채택(실측)**: `WaitFor` 만(+19% — 더 느림) · `region` 캡처(효과 0 · 500요소 상한) · 키보드 묶음(−10% — 효과 작음) · 앱별 길 메모(Ctrl+N 시작 화면에서 실패 · F12 저장은 됨 — 메모 유지 비용 대비 불안정).
- 경로 순서는 14-5 ③ 그대로(계약 API → UIA 이름(표적 조회) → 픽셀 → 키보드) — 후보였던 「키보드가 UIA 앞」은 불채택 실측으로 폐기했다(14-5 와의 불일치 해소).

### 14-7. 팩 디렉티브(master 결정 A · master#1da2515c)
`MASTER_DIRECTIVE.md` 끝에 「★ 컴퓨터 통제 — 선례로 먼저 정하고 보고 (1.1.11)」 절 395 B(조건 ≤ 400 B) · 바이트 래칫 MASTER 84,987 → 85,382 · CEO 100,473 → 100,868(같은 바이트 · `gen_ceo_template.py` 재합성 · `--check` GREEN). 파일 **끝**에 둔 이유: 중간(L62)에 넣었더니 §2 줄 번호 핀(`test_event_inject` F·C — 339–381 · CEO 482–524)이 밀려 적색 → 다른 절 줄 번호를 하나도 움직이지 않는 자리로 옮김. 근거 상세는 이 문서와 스킬(결정 C 병행).

### 14-8. 시험·뮤턴트(2단계 누계)
시험 68 → 84(`TestPrecedent` 14 · 탭 수 대조 2 · privacy·열람 감시에 `adopt`·`decide` 추가) · self-test 357 → 562 조합(이양 판정 불변식: each/never 는 상시 기록이 있어도 do 아님 · 네이버 = each · 새 유형 = ask · 모르는 서비스 로그인 = ask) · 뮤턴트 51 → 65(M52~M65).

---

## 15. 실기 의뢰문 (master → 맥 실기 / 윈 master · 발행 게이트 §2 「cu-1111-precedent」)

공통 준비: 도구 = 이 가지 커밋의 `cysjavis-pack/bin/javis_computer_control.py`(sha256 대조 후 사용) · 상태 폴더는 실기 전용(`CYS_CC_STATE=<실기 폴더>`)으로 돌려 실 `~/.cys/computer-control` 을 더럽히지 않는다 · 각 단계 전후 `<좌석 설정 폴더>/.claude.json` 사본(키 1개 diff 확인) · 크롬 연결 파일 사본(맥 파일 · 윈 `reg export HKCU\Software\Google\Chrome\NativeMessagingHosts\com.anthropic.claude_code_browser_extension`). 끝나면 전부 원복(`chrome-disable` + 사본 대조).

| # | 상황 | 하는 일 | 기록할 것(결정론 증거) | 합격 |
|---|---|---|---|---|
| R1 | 크롬 **꺼져 있음** · 연결 파일 없음(맥: 파일을 실기 폴더로 옮겨 둠 · 윈: reg export 뒤 delete) · 좌석 키 false/없음 | `chrome-enable --seat-restart no` | stdout JSON · `.claude.json` 전후 diff(키 1개만) · 연결 파일 생성 여부·`path` · 크롬 「다시 연결」 탭이 열렸는지(부수 효과 §13-2) · 크롬 프로세스 수 전후 | done ⊇ {default_on, nmh} · 크롬 재시작 0(꺼져 있었으므로) · 다른 키 diff 0 |
| R2 | 크롬 **켜져 있음** · 창 2개 · 탭 합 N(≥ 5 · 고정 탭·시크릿 창 없이) · 연결 파일 없음 | 사용자 손 떼고(유휴 ≥ 20초) `chrome-enable --seat-restart no` | 알림 1줄이 화면(Feed)에 떴는지 · 정상 종료 경로(맥: 자동화 허락 0 이면 osascript / 아니면 SIGTERM) · **「Chrome이 제대로 종료되지 않았습니다 · 복원」 경고가 뜨는지** · 다시 켠 뒤 창·탭 수(눈으로 세기 + 도구 say) · 고정 탭 | 탭 수 전후 같음 · 경고 0 · 강제 종료 0 |
| R2-m | (맥 전용 · master 지시) R2 를 **크롬 자동화 허락이 없는 상태**(S3 ≠ 0)에서 | 같음 | 크롬 본 pid 에 SIGTERM 이 갔는지(ledger `chrome_quit`) · **세션이 복원되는지(--restore-last-session)** · 「정상 종료 안 됨」 경고 여부 | 복원 = 탭 수 같음 · 경고 0 — 경고가 뜨면 이 경로를 「크롬을 닫아 주세요」 손 칸으로 되돌리는 결정을 master 에 올린다 |
| R3 | R2 중 사용자가 키보드를 계속 침 | `chrome-enable --wait 30` → 손을 쉰 뒤 한 번 더 `chrome-enable` | 1회차: 크롬 무접촉 · 연결 파일 미생성 · `pending: ["nmh"]` · 「다시 연결」 탭 0 / 알림 직후 손을 대면 `pending: ["chrome_restart"]` · 2회차: 미룬 크롬·좌석 재시작을 갚음 | 1회차 크롬 종료 0 · 2회차 재시작 완수 |
| R4 | 크롬 확장 **미설치**(맥: 시험 프로필 · 윈: 확장 끈 프로필) | `scan` → `guide chrome` | 크롬 줄 = 손 칸 · 안내 = 웹 스토어 「추가」·확장 로그인만 · `/chrome` 단어 0 | 손 칸 · `/chrome` 안내 0 |
| R5 | 좌석 재시작 | `chrome-enable`(기본 `--seat-restart auto`) 뒤 턴 종료 · 대조: 같은 호출 뒤 일부러 긴 명령(예: `sleep 90`)을 돌려 턴을 끌기 | 턴이 끝난 뒤에만 `cys rotate --skip-depts` 가 끝까지 도는지(분리 프로세스가 pty 종료 뒤 생존 · 윈 작업 개체 분리) · 긴 명령 중에는 재시작 0 · ledger `seat_restart_rotate` rc · 재시작 뒤 `mcp__claude-in-chrome__*` 도구 노출 · 대화 이어짐 | 턴 중 재시작 0 · 도구 노출 · 대화 이어짐 · 다른 좌석 복원 |
| R6 | 되돌리기 | `chrome-disable` | 키 = 원래 값(없었으면 없음) · 우리가 만든 연결 파일만 삭제(그 사이 바뀌었으면 보존) | 사본과 diff 0 |
| R7 | 이양 표 재질문 0 | ① `adopt` 2회(두 번째 = 「새로 맡을 것은 없습니다」) ② `decide login --subject <이미 쓰는 서비스>` = do ③ `decide external_send --subject "<새 유형>"` = ask → 답 → `remember` → 같은 `decide` = do(standing) → 같은 `remember` = exit 7 ④ `decide payment` = each · `remember payment` = exit 5 ⑤ `revoke connectors` → `adopt` = skipped | stdout JSON 전부 | 재질문 0 · 기록 1 |
| R8 | 경합(살아 있는 좌석이 키를 덮는가 · §13-1 Med) | 마스터 좌석이 살아 있는 동안 `chrome-enable --seat-restart no` → 10분 뒤 `.claude.json` 키 재확인 | 키 유지 여부 | 유지 |

윈 전용 확인: `chrome-enable` 의 헤드리스 `claude -p --chrome` 가 `claude.exe` 로 풀리는지 · `CloseMainWindow` 로 모든 크롬 창이 닫히는지(백그라운드 앱 「계속 실행」 설정이 켜져 있으면 프로세스가 남아 not_quit 이 나는지) · 연결 등록 삭제(`reg delete`) 후 크롬 연동 끊김 · 좌석 재시작 대기(`seat-restart-wait` · NEW_PROCESS_GROUP|NO_WINDOW)가 5초마다 `cys` 를 부르는 동안 검은 창이 한 번도 뜨지 않는지(H-WIN-16 의 실기 짝).
맥 전용 확인: `ioreg` HIDIdleTime 이 실제 유휴 초와 맞는지 · osascript 탭 세기 스크립트가 자동화 허락 0 에서 「창 탭」 두 숫자를 내는지.

---

## 16. 이종 적대 검토 R1 (2026-10-27 · revision 92c47060 · 발행 게이트 §2 「이종 2」)

정본: `~/.cys/pack/round/_reviews/cu-1111-precedent_…-r1-codex.json` · `…-r1-agy.json`(둘 다 읽기 전용 세션 · 의뢰자가 마지막 JSON 을 정본 경로에 저장). agy 는 headless 에서 셸 권한이 자동 거부돼 권한 우회 대신 **diff 원문을 프롬프트에 넣어** 재실행했다(도구 0 · 정적 검토).

| # | 검토 | 지적 | 판정 | 반영 | 회귀 시험 · 뮤턴트 |
|---|---|---|---|---|---|
| 1 | agy blocking · codex major | 유휴로 미룬 크롬 재시작을 다음 호출이 `created=False` 로 영영 빠뜨림 | 실재 | 빚을 상태 파일에(§13-3) | `test_deferred_restart_is_owed_and_paid_next_call` · `test_owed_restart_cleared_when_chrome_closed_meanwhile` · M67·M68 |
| 2 | agy minor | 설치 앱 이름 완전 일치만(「카카오톡 로그인」 = 모름) | 실재 | 부분 일치 | `test_usage_app_name_with_extra_words` · M69 |
| 3 | codex major | 새 유형은 remember 해도 영원히 ask | 실재 — **검토 도착 전 자가 발견**(47d4b0d4) | 판정 순서 | `test_new_type_answer_is_remembered_no_reask` · M66 |
| 4 | codex blocking | 상시 허락이 `--in-use no`(가입 = 건마다)를 덮음 | 실재 | 가입 판정을 상시 기록보다 먼저 | `test_signup_beats_standing_allow` · self-test 불변식 · M77 |
| 5 | codex major | 상한 500 에서 옛 결정 삭제 → 재질문 | 실재 | 지우지 않고 새 기록 거절(상한 5,000) | `test_decisions_cap` · M78 |
| 6 | codex blocking | 알림 뒤 3초 사이 입력 재개를 확인하지 않고 종료 · 연결 파일 생성(크롬 탭 열림)이 관문 밖 | 실재 | 알림 뒤 유휴 재확인 · 생성에도 관문 | `test_touch_after_notice_aborts_quit` · `test_idle_gate_defers_without_touching_chrome` · M79·M80 |
| 7 | codex blocking | `.claude.json` 읽기-수정-교체 사이 좌석의 쓰기를 덮음 | 실재(창) | 비교-교체 · 충돌이면 무변경 실패 · 남는 마이크로초 창 정직 고지 | `test_cas_conflict_leaves_file_untouched` · M72 |
| 8 | codex major | 원래 값 기록이 키 쓰기 뒤 → 기록 실패 시 되돌리기 불능 | 실재 | 키보다 먼저 기록 | `test_prior_saved_before_key_write` · M73 |
| 9 | codex blocking | 윈 되돌리기가 등록값 대조 없이 삭제 · 삭제 결과 미확인 | 실재 | 등록값 + 매니페스트 sha 대조 · 실패면 기록 유지(맥도 같음) | `test_win_disable_keeps_registry_changed_by_others` · `test_disable_remove_failure_keeps_record` · M74·M75 |
| 10 | codex major | 대상·한 일·조건 문자열을 그대로 출력(이메일 등) | 실재 | 가림 + 기록 키 해시 | `test_personal_strings_masked_and_keys_hashed` · M76 |
| 11 | codex 논쟁점 | 고정 30초 좌석 재시작이 긴 턴을 끊을 수 있음 | 수용 | 좌석 출력 유휴 2회 연속 뒤 · 15분 넘으면 빚 | `test_seat_waiter_rotates_only_after_turn_ends` · `test_seat_waiter_gives_up_and_owes` · M70·M71 |

곁에서 고친 시험 결함: 「강제 종료 문자열 0」 단언이 행동 기록 전체(임시 경로 포함)를 훑어 임시 폴더 이름이 `9` 로 시작하면 `-9` 가 우연히 일치 — 종료·켜기 명령 인자 토큰만 보도록 좁힘.
codex 가 못 한 것(정직): 읽기 전용 샌드박스에서 임시 폴더를 못 만들어 단위 시험·뮤턴트를 돌리지 못했다(메모리 재현만) — 시험은 이 워커가 돌렸다.

R1 반영 뒤 누계: 시험 97 녹(3회 연속) · self-test 562 조합 · 뮤턴트 79/79 KILLED(M62 = 「상한에서 오래된 결정 삭제」를 끄는 뮤턴트였는데 그 코드가 R1 #5 로 없어져 퇴역 · 반대 방향을 M78 이 잰다 · M40·M43·M66 찾는 문자열 갱신).

### 16-2. R2 (revision ad474d66)
- **agy R2 = ACCEPT**(issues 0 · R1 2건 해소 확인 · 반영 diff 신규 결함 없음 · 정본 `…-r2-agy.json`).
- **codex R2 = REVISE**(blocking 4 · major 6 · R1-1·2·3·5·7 해소 확인 · 정본 `…-r2-codex.json`) — 처분:

| # | 지적 | 판정 | 반영 | 회귀 시험 · 뮤턴트 |
|---|---|---|---|---|
| 1 | blocking — 재확인↔교체 창이 남아 다른 키 손실 0 미충족 | 실재 | Claude Code 와 **같은 설정 잠금**(`.claude.json.lock` · 바이너리 원문 근거 §13-1) + 잠금 안 재읽기 | `test_config_lock_respected` · M81 |
| 2 | blocking — 꺼진 크롬이면 연결 파일 생성 관문 생략 | 실재 | 크롬 상태 무관 관문 | `test_nmh_gate_even_when_chrome_off` · M82 |
| 3 | blocking — 출력 유휴 ≠ 턴 종료 · 좌석 ID 없으면 관문 생략 | 실재 | 세션 기록 마지막 줄 `end_turn` 확인 · 좌석 ID 없으면 재시작 0(빚) | `test_seat_waiter_quiet_tool_wait_is_not_turn_end` · `test_seat_waiter_without_surface_owes` · M83·M84 |
| 4 | blocking — 키 형식 변경이 옛 결정을 잃음 | 실재(이 가지 안에서만 존재한 형식이지만 재질문 0 원칙상 보존) | 옛 키 조회·재기록 금지·바꿀 때 이관 | `test_legacy_key_still_honored` · M88 |
| 5 | major — 윈 생성 기록 sha 가 늘 null → 자기 등록도 못 지움 · 기록까지 버림 | 실재 | 등록값이 가리키는 매니페스트 sha 기록 · sha 없으면 지우지도 기록을 버리지도 않음 | `test_win_round_trip_enable_then_disable` · M93 |
| 6 | major — 삭제 실패 뒤 다시 끄기가 키를 false 로 다시 씀 | 실재 | `key_restored` 표지 · 원래 값 보존 | `test_disable_retry_does_not_rewrite_key` · M92 |
| 7 | major — 가림이 이메일·번호만(이름·조직·프로필 이름 미보호) · 새 유형 이름 원문이 키에 | **부분 수용** | 새 유형 이름 해시(수용) · 이름류 가림은 기각 — 근거 아래 | `test_new_type_key_hashed` · M89 |
| 8 | major — 「word」 부분 일치가 wordpress.com 을 쓰는 서비스로 오인 | 실재 | 낱말 단위 대조 | `test_word_app_does_not_match_wordpress` · M90 |
| 9 | major — 조건을 가려 저장해 허락 범위를 잃음 | 실재(R1 #10 반영의 과잉) | 조건 원문 로컬 보존 · 조건부는 `--condition-met` 확인 뒤에만 do(모르면 check) | `test_external_send_conditional` · self-test 3조합 · M91 |
| 10 | major — 좌석 재시작 예약 실패·rotate 실패면 빚이 사라짐 | 실재 | 빚은 재시작 성공에서만 해제 · 중복 예약 방지 | `test_schedule_failure_keeps_seat_debt` · `test_seat_waiter_rotate_failure_keeps_debt_success_clears` · M85·M86·M87 |

**#7 이름류 가림 기각 근거**: §3-3 의 출력 금지 목록은 「이 도구가 컴퓨터에서 **읽어 온** 값」(`.claude.json` 의 이메일·이름·조직 · 크롬 프로필 이름 · 방문 기록 등)이 마스터 대화로 새지 않게 하는 규칙이다. `decide`·`remember` 의 대상·한 일·조건 문자열은 도구가 읽어 온 것이 아니라 **마스터가 대화 안에서 이미 쓴 글**(또는 사용자가 대화에서 말한 조건)을 되돌려 주는 것이라 새 노출이 생기지 않는다. 이름은 모양으로 가릴 수도 없다(일반 낱말과 구별 불가) — 이메일·긴 번호 가림은 그래도 남겨 두는 방어 겹이다. 도구가 컴퓨터에서 읽어 오는 값의 출력 금지(§3-3 원래 범위)는 그대로 시험한다(`test_privacy_no_markers_in_any_output` — `adopt`·`decide` 포함).

R2 반영 뒤 누계: 시험 108 녹(`-W error`) · self-test 565 조합 · 뮤턴트 92/92 KILLED(M1~M93 · M62 퇴역 · R1·R2 반영으로 어긋난 찾는 문자열 6개 갱신 · M92 는 처음 생존 → 「두 끄기 사이 사용자가 /chrome 에서 다시 켬」 반례로 시험 강화 뒤 KILLED). codex R3 = 다음 좌석(HANDOFF).

### 16-3. R3 (revision 793c7a10)
- **codex R3 = REVISE**(blocking 1 · major 5 · R2 #1·2·3·5·10 해소 확인 · 정본 `…-r3-codex.json`) — 처분:

| # | 지적 | 판정 | 반영 | 회귀 시험 · 뮤턴트 |
|---|---|---|---|---|
| 1 | blocking — ad474d66 판 새 유형 키(`유형 원문:대상 해시`)를 조회하지 않아 그 판의 결정이 ask 로 | 실재 | 옛 판 키 두 형식 모두 조회 · 재기록 금지 · 바꿀 때 둘 다 이관 | `test_r2_format_new_type_key_honored` · M88(갱신)·M94 |
| 2 | major — check 가 저장된 조건 원문을 출력(뒤 대화에서 다시 읽힘 · §16-2 기각 근거 밖 · 문서 「로컬에만」과 모순) | **수용**(§16-2 의 기각 근거는 「이번 대화에서 쓴 글」에만 맞다 — 저장된 조건을 뒤 대화에서 다시 내보내는 경로에는 맞지 않는다) | 이메일·긴 번호 = 차례 자리표(`<이메일1>`·`<번호1>`) · 이번 건(`--what`)의 이메일·번호 ⊆ 조건 여부를 로컬 대조해 참/거짓만 · 이름·조직 이름은 모양으로 가릴 수 없어 **스킬 계약**으로 막는다(`--condition` = 역할·범위 낱말) | `test_check_hides_condition_identifiers_and_matches_locally` · M95·M96 |
| 3 | major — 삭제 실패로 남은 `key_restored` 를 다시 켜기가 안 지워 다음 끄기가 키를 안 되돌림 | 실재 | 다시 켜며 손대기 전에 표지를 지운다 | `test_reenable_after_failed_delete_restores_key`(원래 없음·false·true) · M97 |
| 4 | major — 도메인 하위 이름(`word.example.invalid` 의 word)을 Word 사용 근거로 | 실재 | 도메인이 있으면 등록 이름 하나만 대조(2단계 국가 도메인 `co.kr` 등 처리) | `test_word_subdomain_is_not_word_app` · M102·M103 · M90(갱신) |
| 5 | major — 조건을 300자에서 잘라 끝의 제한이 사라짐 | 실재 | 자르지 않음 · 2,000자 넘으면 기록 거절 · 옛 판에서 잘렸을 수 있는 조건(300자 · `full` 표지 없음)은 조건 확인이 있어도 each | `test_condition_too_long_rejected_not_truncated` · `test_legacy_truncated_condition_never_do` · M99·M100·M101 |
| 6 | major — 키가 원래 true 이고 연결 파일만 만들면 원래 값을 기억하지 않아 끄기가 false 로 씀 | 실재 | 연결 파일을 만들기 전에도 원래 값 기록 | `test_prior_true_nmh_only_round_trip` · M98 |

R3 반영 뒤 누계: 시험 115 녹(`-W error` · 2회) · self-test 565 조합 · 뮤턴트 102/102 KILLED(M94~M103 신설 · R3 반영으로 어긋난 찾는 문자열 7개 갱신 = M46·M69·M73·M80·M82·M88·M90). 새 시험 7개는 793c7a10 원본에서 전부 적색(실측).


### 16-4. R4 (revision 43ac4d18)
- **codex R4 = REVISE**(blocking 0 · major 4 · R3 #1·5·6 해소 · #3 제시 반례 해소 · 정본 `…-r4-codex.json`) — 처분:

| # | 지적 | 판정 | 반영 | 회귀 시험 · 뮤턴트 |
|---|---|---|---|---|
| 1 | major — 스킬 계약(역할·범위 낱말)은 이미 저장된 이름·조직·프로필을 못 막는다 · check 가 자리표 바꾼 조건 글을 그대로 출력 | 실재(§16-3 #2 처리의 미달) | 조건 글은 **출력 0**(로컬 기록에만) · 조건부 허락은 범위 낱말 4개(`SCOPES`)나 받는 사람 목록(해시)으로만 기록 · 그렇게 적지 않은 옛 조건부 = each | `test_check_hides_condition_text_and_matches_locally` · `test_conditional_needs_structure` · M95·M101·M104·M105·M106·M108 |
| 2 | major — 허용·금지 주소가 함께 있는 조건에서 「포함 여부 참」이 금지 대상도 참으로 만든다 | 실재(R3 반영이 만든 결함) | 받는 사람마다 `<허용n>`·`<금지n>`·「목록 밖」 | 같은 시험 · M96 |
| 3 | major — 등록 이름 대조가 `word.invalid`(Word)·`gmail.invalid`(Gmail)를 사용 중으로 | 실재 | 도메인은 정식 도메인 목록(`SERVICE_DOMAINS`)으로만 · 점 경계 뒤끝 일치 | `test_domain_matches_only_official_domains` · M102·M103 · M69·M90(갱신) |
| 4 | major — 앞 주기를 되돌린 뒤 사용자가 키를 바꾸고 다시 켜면 옛 원래 값으로 덮는다 | 실재(R3 반영이 남긴 결함) | 앞 주기 키를 되돌렸으면 새 주기 — 원래 값 = 다시 켜기 직전 값 | `test_new_cycle_prior_is_value_just_before`(원래 true→사용자 false · false→없음 · 없음→true) · M107 |

**라운드마다 새 결함이 나오는 까닭(R1~R4 공통 뿌리 · master#642e721c 요청 형식)**: 결함이 세 부류로만 되풀이된다 — ⑴ **자유 글의 출력·대조**(R1 가림 → R2 가림 과잉 → R3 원문 출력 → R4 이름·허용/금지 구별 소실) ⑵ **이름 닮음 대조**(부분 문자열 → 낱말 → 등록 이름 → 정식 도메인) ⑶ **되돌리기 상태 표지**(`prior_key`·`key_restored`·`pending_*` 가 반영마다 하나씩 늘며 서로 얽힘) + 갈래 ⑷ **기록 형식 변경 호환**(R2 키 변경 → R3 직전 판 형식 누락). 뿌리는 같다 — **반례 하나를 막는 국소 수리**를 했고, 그 수리가 같은 부류의 다음 반례를 열었다(특히 R3 #2·R4 #2·#4 는 직전 반영이 만든 결함). 그래서 R4 반영은 부류째 닫는 쪽으로 바꿨다: ⑴ 자유 글을 **판정·출력 경로에서 빼고** 정해 둔 낱말·해시만 쓴다(가릴 대상이 출력에 아예 없다) · ⑵ 추정 대조를 **허용 목록**(정식 도메인)으로 바꿔 모르면 ask · ⑶ 되돌리기는 「주기」로 정의(되돌림이 끝난 뒤 다시 켜면 원래 값을 새로 잡는다)하고 사용자 변경을 낀 왕복 시험을 원래 값 3종으로 · ⑷ 옛 판 키 형식은 목록(`_legacy_keys`)으로 한곳에 모아 조회·이관을 함께 시험.

R4 반영 뒤 누계: 시험 117 녹(`-W error`) · self-test 565 조합 · 뮤턴트 107/107 KILLED(M104~M108 신설 · M69·M90·M95·M96·M101·M102·M103 다시 씀). 바뀐·새 시험 8개는 43ac4d18 원본에서 전부 적색(실측).

### 16-5. R5 (revision db9b3d97) — 설계 전환: 조건의 뜻은 도구가 해석하지 않는다(master#6528f666 · D16)
- **codex R5 = REVISE**(blocking 0 · major 4 · R4 4건의 원 반례는 전부 해소 판정 · 정본 `…-r5-codex.json`). 지적: ① 범위 낱말 하나면 자유 글 조건을 구조 완료로 인정 → 「A팀 저장소·오늘까지」와 「B팀·다음 달까지」가 같은 check 정보로 축약(조직·기한 소실 · §16-4 「부류째 닫음」 불성립) ② 같은 수신자를 허용·금지 양쪽에 기록 가능 · check 는 허용 먼저 → 금지를 숨김 ③ 잘리지 않은 옛 자유 글 조건도 매번 each · 구조화 재기록은 `already_decided` 로 막힘 → 재질문 고리 ④ `_host` 가 URL 의 실제 hostname 이 아니라 첫 도메인 모양 → `https://mail.google.com@<다른 호스트>` = do(R4 반영이 만든 회귀).
- **뿌리(master 판정)**: R1~R5 의 major 가 「사용자가 붙인 조건 글을 도구가 결정론으로 해석」하는 한 부류에서 계속 나온다(가림 → 자리표 → 범위 낱말 → 해시 목록 → 이름 범위·기한 문법…). 이것은 D16 「사용자 말 = 자연어 맥락 판정 · 고정 사전 금지 · **출처 축은 결정론 / 뜻 축은 자연어**」 위반이다 — 사용자 말을 고정 문법으로 옮기는 한 문법 밖 제한(조직·기한·예외)은 언제나 소실되고, 반례마다 문법이 늘었다(§16-4 의 ⑴ 이 그 기록). 그래서 반례를 막지 않고 **부류를 없앤다**.
- **전환(계약)**: ⑴ 도구는 조건 글을 해석하지 않는다 — 사용자 말 원문 그대로 기록 파일에 저장(원장·감사 기록엔 답 해시만) · `decide` 가 조건부 항목이면 `check` + `condition`(원문)을 마스터에게 돌려주고, 이번 건이 맞는지는 마스터가 말뜻으로 판단(`--condition-met yes|no` · 애매하면 그때만 사용자에게 1회) ⑵ 결정론은 **출처 축**에만 — 대상 식별(④ URL 실제 hostname · 대상 둘 이상·깨진 URL = 모름) · 같은 대상의 뜻이 다른 기록 공존 시 더 좁은 쪽(②의 남은 몫 — 받는 사람 목록이 없어져 목록 교집합 자체가 사라졌고, 남는 공존 경로는 지금 키·옛 키뿐) · 재질문 고리 차단(③ 옛 자유 글 조건 = 조건부로 그대로 승계 · 잘렸을 수 있는 300자 옛 기록만 each + `supplement` 로 한 번 다시 받아 덮기) ⑶ 범위 낱말(`SCOPES`)·받는 사람 목록(`--allow-id`·`--deny-id`)·`condition_structure` 거절·`what_ids` 는 **되돌렸다**(자유 글 조건 기록 허용) — 이름 범위·기한 문법은 넣지 않았다.
- **R4 #1(check 가 조건 글을 출력 → 뒤 대화에서 이름·조직이 다시 읽힘)과의 관계 — 의도된 되돌림**: 조건 원문은 이 사용자 자신의 말이고 받는 쪽은 이 사용자 자신의 마스터 좌석이다. 뜻 판정을 마스터가 맡는 이상 원문 없이는 판정이 불가하다(R4 #1 을 막은 대가가 R5 ①). 가림은 그대로 둔다 — 원장·감사 기록·`remember` 의 말(`mask`)·do 의 `report` 에는 원문이 없고, SKILL 은 「조건 원문은 판단에만 쓰고 보고·다른 좌석·외부로 옮기지 않는다」.

| # | 지적 | 판정 | 반영 | 회귀 시험 · 뮤턴트 |
|---|---|---|---|---|
| 1 | major — 범위 낱말만으로 조건 제한 소실 | 실재 · **부류 소멸로 처분**(D16) | 조건 문법 전부 제거 · 원문을 check 로 마스터에게 · 뜻 판정 = 마스터 | `test_free_text_condition_recorded_and_returned_verbatim` · `test_external_send_conditional`(갱신) · M95·M104 |
| 2 | major — 허용·금지 교집합이 금지를 숨김 | 실재 · 받는 사람 목록 제거로 경로 소멸 · 남은 공존(지금 키·옛 키) = 더 좁은 쪽 | `_lookup` = 안 함 > 조건부 > 허락 | `test_conflicting_records_strictest_wins`(5조합) · M106 |
| 3 | major — 옛 자유 글 조건 = 매번 each + 재기록 막힘 | 실재 | 옛 자유 글 조건 = 조건부 그대로(check) · 300자 옛 기록만 each + `supplement` · 그 기록은 `--user-changed` 없이 덮기 | `test_legacy_truncated_condition_never_do`(yes·unknown·no → each · 다시 적기 → check · 그 뒤 재기록 막힘 · 299자 = check) · `test_r2_format_new_type_key_honored`(갱신) · self-test(잘린 옛 조건 × 확인 3값) · M54·M96·M101·M105 |
| 4 | major — `_host` = 첫 도메인 모양(사용자정보 속 정식 도메인으로 do) | 실재(R4 반영이 만든 회귀) | `_hosts`: URL = `urllib.parse` hostname · 그 밖 도메인 모양 · 둘 이상·깨진 URL = 모름 → ask | `test_url_target_is_real_hostname`(7건) · M108·M109·M110 |

R5 반영 뒤 누계: 시험 118 녹(`-W error`) · self-test 568 조합 · 뮤턴트 109/109 KILLED(M54·M88·M95·M96·M101·M104~M108 다시 씀 · M109·M110 신설). 바뀐·새 시험 8개는 db9b3d97 원본에서 전부 적색(실측). `scan-pack-secrets` = R4 시험 이메일 자리표 11곳 소멸(받는 사람 목록 제거) · 남은 2곳은 기반 `CC-TEST-EMAIL`(678 수리분 · rebase 때 흡수). codex R6 범위 = 결정론 축만(대상 식별·기록 공존·재질문 고리·잘린 옛 기록).

### 16-6. R6 (revision c09d8a13 · rebase 뒤 · 범위 = 결정론 축만)
- **codex R6 = REVISE**(blocking 0 · major 4 · minor 1 · R5 ② 해소 판정 · D16 의 뜻 판정·원문 반환은 지시대로 검토 제외 · 정본 `…-r6-codex.json`) — 처분:

| # | 지적 | 판정 | 반영 | 회귀 시험 · 뮤턴트 |
|---|---|---|---|---|
| 1 | major — urllib hostname ≠ 브라우저 호스트: `https://a.invalid\@mail.google.com/` = mail.google.com(브라우저는 a.invalid) · 잘못된 포트(`:bad`·`:999999`)도 do | 실재 | 역슬래시가 있는 URL = 모름 · `port` 판독 실패 = 깨진 URL = 모름 | `test_url_target_is_real_hostname`(+5건) · M116·M117 |
| 2 | major — 보완 예외가 잘린 기록만이 아니라 대상 전체를 바꿈(허락으로 덮기 · 공존하는 온전한 옛 기록 삭제) | 실재 | 보완 = 조건부로만(그 밖 = `supplement_meaning` · 사용자 변경 경로) · 지우는 것은 잘린 기록뿐 · 지금 키의 온전한 조건·안 함 보존(허락 위엔 방금 다시 받은 더 좁은 조건) | `test_supplement_only_replaces_cut_records` · M112·M113·M114 |
| 3 | major — 조건끼리 같은 순위라 키 배치에 따라 잘린 조건이 가려짐(확인으로 do) | 실재 | 순위 = 안 함 0 · 잘린 조건 1 · 조건 2 · 허락 3 — 키 자리 무관 | `test_cut_condition_wins_regardless_of_key_position`(두 배치 × yes·unknown) · M111 |
| 4 | major — 5,000 한도에서 옛 키 잘린 기록 보완이 `decisions_full`(개수가 늘지 않는데 거절 → 재질문 고리) | 실재 | 한도 = 정리될 키를 뺀 뒤 개수 | `test_supplement_at_cap_replaces_in_place`(새 항목은 여전히 거절) · M115 · M78(갱신) |
| 5 | minor — 「Gmail (https://mail.google.com)」 의 닫는 괄호를 호스트에 붙여 과잉 ask | 실재 | URL = ASCII 인쇄 문자까지 · 끝 `).,;:!?]}>'"` 제외 | 같은 시험 · M118 |

- **rebase 뒤 건강성 전량에서 자가 발견(H-WIN-16 · U5-WIN-FLASH)**: 좌석 재시작 대기의 윈 분리 스폰이 `DETACHED_PROCESS`(0x8 · 콘솔 떼기) — 콘솔 없는 프로세스가 `cys` 를 부를 때마다 새 창이 뜬다(1.1.7 「1분마다 검은 창」 부류). `NEW_PROCESS_GROUP|NO_WINDOW` 로(숨은 새 콘솔 — 좌석 콘솔이 닫혀도 살고 자손이 물려받음) · 팩 creationflags 동결표 `javis_computer_control.py` 1 → 2(사유 기재 · `run_bootstrap_health.py`). 앞 라운드 리뷰 4회가 못 본 것은 건강성 전량을 rebase 전 가지에서 돌리지 않았기 때문이다(게이트 목록 누락 — 이번부터 매 반영 뒤 `--only H-WIN-16` 포함).

R6 반영 뒤 누계: 시험 121 녹(`-W error`) · self-test 568 조합 · 뮤턴트 117/117 KILLED(M54·M78·M88·M105·M106 다시 씀 · M111~M118 신설). 바뀐·새 시험 4개는 c09d8a13 원본에서 전부 적색(실측) · H-WIN-16 녹(`--only`).

### 16-7. R7 (revision ffe37487 · 범위 = 결정론 축만)
- **codex R7 = REVISE**(blocking 0 · major 2 · R6 #1·#3·#4·#5 해소 · #2 일부 미해소 · 정본 `…-r7-codex.json`) — 처분:

| # | 지적 | 판정 | 반영 | 회귀 시험 · 뮤턴트 |
|---|---|---|---|---|
| 1 | major — URL 을 ASCII 인쇄 문자까지만 잘라 `https://mail.google.comé/`·`https://mail.google.com。invalid/` 를 mail.google.com 으로 → do(R6 반영이 만든 회귀) | 실재 | URL = 공백 전까지 통째로 파싱(비ASCII 가 붙은 호스트 `mail.google.comé` 는 정식 도메인과 달라 모름 → ask · 경로의 한글은 그대로 허용) — 따로 넣었던 「호스트 비ASCII = 모름」 검사는 이 위에서 관찰 차이 0(뮤턴트 등가 생존 실측)이라 뺐다 | `test_url_target_is_real_hostname`(+3건) · M119(ASCII 자르기 되살림) · M116(갱신) |
| 2 | major — 지금 키 = 허락 · 옛 키 = 잘린 조건이면 보완이 온전한 허락을 덮는다(§14-4 「허락 위엔 다시 받은 조건」 예외가 SKILL 「잘린 기록만」과 불일치) | 실재 | 보완 = 잘린 기록을 **그 키 자리에서** 교체(지금 키·다른 기록 무접촉 · 개수 그대로) — 예외 문구 삭제 · 조회는 순위대로(잘린 것이 바뀐 뒤 조건 2 < 허락 3 → check) | `test_supplement_only_replaces_cut_records`(온전한 조건·허락 × 옛 키 잘림 → 둘 다 보존) · `test_supplement_at_cap_replaces_in_place`(+사용자 변경 옮김 한도 안) · M113·M114·M78(갱신) |

- 논쟁점(issue 아님) — 「NEW_PROCESS_GROUP|NO_WINDOW 스폰이 좌석 콘솔이 닫힌 뒤에도 사는지는 H-WIN-16 통과로 입증되지 않는다」: 맞다. H-WIN-16 은 창 정책(콘솔 떼기 0)만 잰다. 생존은 윈 실기 항목으로 §15 의뢰문에 있다(좌석 재시작 1회 뒤 대기 프로세스가 끝까지 돌아 재시작을 집행하는가) — 이 컴퓨터(맥)에서는 잴 수 없다(정직 고지).

R7 반영 뒤 누계: 시험 121 녹(`-W error`) · self-test 568 조합 · 뮤턴트 118/118 KILLED(M78·M113·M114·M116 다시 씀 · M119 신설) · 바뀐 시험 2개는 ffe37487 원본에서 적색(실측) · 건강성 전량(ffe37487) 167/2/1skip = 678 기준선과 같음(잔여 적 H-CLT-1·2 = 호스트 의존) · H-WIN-16 녹.

### 16-8. R8 (revision 6de6676b · 범위 = 결정론 축만 · push 뒤 CI 와 병행)
- **codex R8 = REVISE**(blocking 0 · major 1 · R7 #1·#2 해소 · 정본 `…-r8-codex.json`) — 처분:

| # | 지적 | 판정 | 반영 | 회귀 시험 · 뮤턴트 |
|---|---|---|---|---|
| 1 | major — URL 을 공백 전까지 받으면서 제어 문자(U+0000·0001·007F)가 hostname 에 들어온다 · urllib 은 거절하지 않아 `https://unrelated.invalid\u0000.mail.google.com/` 이 정식 도메인 뒤끝 대조를 통과 → do(R7 반영이 만든 회귀) | 실재 | 호스트 **허용 꼴**(`_HOST_OK`) 밖은 모름 — 금지 문자를 하나씩 막지 않고 허용 꼴만 통과 · 끝점 1개는 같은 호스트 · 끊긴 `://` = 모름 · self-test 에 호스트 자리 한 글자 끼움 전수(2,160 꼴) | `test_url_target_is_real_hostname`(+6건) · self-test(2,728 조합) · M121·M122·M123 |

- **자가 발견(R8 단락을 쓰다가 · 결정론 표면 전수 점검)**: `_norm` 이 대상을 120자에서 잘랐다 — ⑴ 앞 120자가 같은 두 대상이 **한 결정을 나눠 가진다**(긴 받는 곳 설명의 허락이 다른 곳에 적용) ⑵ 120자 뒤의 「네이버」를 못 봐 약관 서비스 건마다(each) 가 사용 근거로 do 가 될 수 있었다. 정규화는 자르지 않는다 · 옛 판 키(앞 120자)는 `_legacy_keys` 첫 꼴로 조회만. ⚠ 처음 적은 「남는 위험 = 고침 전 개발 기록뿐」은 **틀렸다**(codex R9 #1 — 정확히 120자인 대상의 *새* 지금 키가 더 긴 대상의 옛 키와 같아 새 기록끼리도 옮았다) → §16-9 에서 대상 표지로 닫음. `test_long_subject_not_cut` · M124·M125 · M89·M94(갱신).
- 등가 생존 2건을 코드에서 뺐다(관찰 차이 0 실측): R7 의 「호스트 비ASCII = 모름」(M119 생존 — 통째 파싱 뒤엔 정식 도메인과 달라 이미 모름) · R8 첫 판의 「제어·서식 문자 = 모름」(M120 생존 — `_HOST_OK` 가 이미 막음). 뮤턴트가 죽일 수 없는 방어는 문서가 아니라 착각이라 남기지 않는다.
- **결정론 축 결함이 왜 아직 나오나(master#c53833f5 요청 단락)**: R5~R8 의 결정론 major 10건(R5 #1 의 뜻 축 1건 제외)은 **두 표면에만** 있다 — ⑴ 대상 글에서 접속 호스트를 뽑는 `_hosts` 4건(R5 #4 · R6 #1 · R7 #1 · R8 #1 + R6 minor) — **4건 모두 직전 반영이 만든 회귀** ⑵ 기록 조회·보완(`_lookup`·`cmd_remember`) 6건(R5 #2·#3 · R6 #2·#3·#4 · R7 #2) — 그중 4건은 R5 처분에서 새로 넣은 보완 경로의 결함이다. 뿌리는 §16-4 와 같은 「반례 하나씩 막기」인데 대상이 바뀌었다 — 브라우저(WHATWG)와 파이썬 urllib 의 URL 해석 차이를 **금지 목록**(사용자정보 → 역슬래시 → 포트 → 끝 부호 → 비ASCII → 제어 문자)으로 하나씩 메웠고, 메울 때마다 소비 범위·분기가 바뀌어 다음 틈을 열었다. ⑵ 도 같은 꼴이다(보완 경로를 넣고 → 덮어쓰기 범위 · 순위 · 한도를 차례로 메움). 이번 처분은 ⑴ 의 방식을 끊었다: ⑴ **허용 목록**으로 뒤집음(호스트 = 엄격한 ASCII 라벨 꼴만 · 그 밖은 전부 「모름 → 묻기」 — 틀려도 더 묻는 쪽으로만 틀린다) ⑵ **전수 시험**(정식 URL 호스트 자리 16곳 × 글자 135종 끼움 = 2,160 꼴을 self-test 가 매번 돌고, do 는 브라우저가 같은 호스트로 읽는 자리·글자(맨 앞 `@` · 맨 끝 `:` `.` `/` `?` `#` 공백)에서만 허용 — 이 판정식이 구현과 독립인 오라클이다). **남은 결정론 표면 목록**(이 도구 전부): ① `_hosts` — 위 전수(한 글자 끼움)까지 · 두 글자 이상 변형과 스킴 없는 자유 글(도메인 모양 낱말 대조 — 마스터가 쓴 대상 설명이지 브라우저가 여는 주소가 아니다)은 전수 밖 ② 정식 도메인 대조 `hit`(같음·점 경계 뒤끝 — 고정 목록) ③ 도메인 없는 대상의 낱말 대조 `_toks`(이름 낱말 ⊆ 대상 낱말) ④ 키 정규화 `_norm`·`decision_key`·`_legacy_keys`(이번 120자 자르기 고침) ⑤ 기록 순위·보완·한도 `_rank`·`_lookup`·`cmd_remember` ⑥ 판정 순서 `judge`(self-test 가 유형 × 대상 × 사용 근거 전수). **전수 시험 방안(다음 단계 · 이 티켓 범위 밖이면 master 판단)**: ①은 두 글자 끼움·한 글자 지움·바꿈으로 넓히면 수만 꼴(초 단위) · ⑤는 **이번에 넣었다** — `test_record_states_exhaustive` = 지금 키/옛 키 × {없음·허락·안 함·조건·잘린 조건} 5×5 × 뜻 3 × 사용자 변경 여부 = 150 꼴을 구현과 독립인 판정식(조회 = 가장 좁은 것 · 보완 = 조건부로만·잘린 자리만·개수 불변 · 사용자 변경 = 지금 키 하나 · 그 밖 = 무변경 거절)과 대조. 실측: 현 판 녹 · **c09d8a13(R6 이 잡은 판)·ffe37487(R7 이 잡은 판) 원본에서 적** — 리뷰가 하나씩 찾은 ⑵ 부류를 한 번에 잡는 시험이다(6de6676b 는 녹 — 두 결함 반영 뒤라 맞음).

R8 반영 뒤 누계: 시험 123 녹(`-W error`) · self-test **2,728** 조합(+ 호스트 끼움 전수 2,160) · 뮤턴트 123/123 KILLED(M121~M125 신설 · M89·M94 다시 씀 · 등가 생존 M119·M120 은 해당 코드째 삭제). 바뀐·새 시험 3개는 6de6676b 원본에서 적(`test_url_target_is_real_hostname` · `test_long_subject_not_cut`) · `test_record_states_exhaustive` 는 c09d8a13·ffe37487 에서 적.

### 16-9. R9 (revision 832be152 · 범위 = 결정론 축만 · 상한 10 중 9)
- **codex R9 = REVISE**(blocking 0 · major 2 · R8 #1 해소 · 정본 `…-r9-codex.json`) — 처분(master#569a75ff 「major 면 전수 범위로 덮고 R10 이 마지막」):

| # | 지적 | 판정 | 반영 | 회귀 시험 · 뮤턴트 |
|---|---|---|---|---|
| 1 | major — 정규화 120자 대상 A 의 **새** 지금 키 = A 뒤에 글을 붙인 B 의 옛 판(앞 120자) 키 → 새 A 의 허락·거절이 B 로 옮고, B 의 `--user-changed` 가 옛 키 정리로 A 의 기록을 지운다(login 거절 A 삭제 → 사용 근거로 do 재현) · §16-8 의 위험 한정 불성립 | 실재(R8 반영이 만든 회귀) | 새 기록 = 대상 표지 `for`(지금 키 · 해시) · `_found` = 옛 판 키 자리에서 `for` 가 다른 기록은 제외(조회·삭제 모두) · 사용자 변경의 정리는 `_found` 가 돌려준 이 대상 키만 · 보완(잘린 자리 교체)도 `for` 로 제 것 | **`test_key_space_boundary_120`** = 길이 119·120·121 × 아는 유형 2·새 유형(이름 120·121자) 2 × 기록 차례 2 × (처음 기록·사용자 변경) 전수 — 옮김 0 · 삭제 0 · 둘 다 남음 · M126·M127·M128 · M88(갱신) |
| 2 | major — `_HOST_OK` 는 꼴만 봐 잘못된 A-label(`xn--a`)을 통과 · 끝점 제거로 `https://xn--a.mail.google.com./` 가 ask → do · 전수 판정식의 `c.isspace()` 가 구현과 같은 공백 가정을 공유(VT·U+3000 끼움을 정답으로) | 실재 | 퓨니코드 라벨 = 모름(이 컴퓨터는 A-label 유효성을 못 잰다 · 정식 도메인 목록엔 `xn--` 가 없어 잃는 do 0) · URL 끝 = ASCII 공백·탭·줄바꿈뿐(그 밖 공백류는 URL 안 → 호스트 꼴에서 모름) · 판정식의 낱말 경계 = **고정 목록**(`:./?#` + 공백·탭·CR·LF) · 끼움 표본 +3(NBSP·NEL·LS) | `test_url_target_is_real_hostname`(+6) · self-test 2,776 · M129·M130 · M119·M121·M123(갱신) |

- 보장 범위 정정(§16-8 의 「브라우저가 같은 호스트로 읽는」 표현): 끼움 전수의 do 허용 자리는 **브라우저 파서 동치가 아니라 「글 속 주소 낱말」 해석**이다 — 맨 끝 ASCII 공백은 브라우저 URL 로는 잘못이지만 대상 글(「https://mail.google.com 로그인」)에선 주소의 끝이다. 이 판정식은 구현의 분류 함수를 빌리지 않는 고정 목록이고, 목록 밖은 전부 모름(더 묻는 쪽)이다. WHATWG 파서 자체를 오프라인으로 들이는 것은 팩 의존성 0 원칙과 충돌해 넣지 않았다(정직 고지 — 남는 차이는 「브라우저는 받는데 우리는 묻는」 쪽뿐: 퍼센트 인코딩 호스트·유니코드 호스트·전각 점 등).

R9 반영 뒤 누계: 시험 124 녹(`-W error`) · self-test **2,776** 조합 · 뮤턴트 128/128 KILLED(M126~M130 신설 · M88·M119·M121·M123 다시 씀) · 바뀐·새 시험 2개(`test_key_space_boundary_120` · `test_url_target_is_real_hostname`)는 832be152 원본에서 적(실측).

### 16-10. R10 (revision 08630b53 · 마지막 라운드) — 설계 B: 옛 판 키 호환 삭제(master#7d1b6e77)
- **codex R10 = REVISE**(blocking 0 · major 1 · R9 #1·#2 의 직접 반례 해소 · 정본 `…-r10-codex.json`): R9 의 대상 표지 `for` 는 **조회·삭제**만 막고 **쓰기**는 슬롯 소유자를 보지 않았다 — 정규화 120자 A · B = A + 「 추가」 · B 의 옛 판 잘린 조건이 key(A) 슬롯(옛 판 = 앞 120자 키)에 있을 때 B 보완이 그 슬롯에 `for=key(B)` 로 쓰고 → A 의 첫 기록이 `_found` 에서 B 것을 남의 것으로 빼 `already_decided` 없이 key(A) 를 덮어 → B 의 조건 소실 → B login(조건 불일치 · Gmail 사용 근거) each → **do**.
- **뿌리 = 옛 판 키 호환 층 자체**: 옛 판 기록은 소유자를 알 수 없고(A 것일 수도 B 것일 수도) 슬롯을 여러 대상이 나눠 쓴다 — 어떤 쓰기 규칙도 「남의 판정을 바꾸지 않음」을 보장하려면 그림자 표·이관 구조가 또 커진다(이 층에서 나온 결함 = R2 blocking · R3 #1 blocking · R5 #2 · R6 #2·#3·#4 · R7 #2 · R9 #1 · R10 #1).
- **결정 B(master#7d1b6e77) · 근거(실측)**: decide/remember 는 d5a83f4b(이 티켓)에서 처음 생겼고 **태그 0 · 발행·설치 0**(`git tag --contains d5a83f4b` 빈 결과 · 원격엔 `origin/fix/1111-precedent` 뿐) · 이 맥에 `~/.cys/computer-control/` 자체가 없음 → 「옛 기록 보존」의 대상(실사용자 기록)이 없다. R2·R3 blocking(옛 판 키 결정 유실)은 그 기록이 있다는 전제였다 — 전제가 실재하지 않으므로 호환 층은 위험(슬롯 공유)만 남긴다.
- **집행**: `_legacy_keys`·`KEY_CUT`·`_found`·`_rank`·대상 표지 `for`·사용자 변경의 옛 키 정리·보완의 다른 자리 쓰기를 **삭제** — `_lookup` = 키 하나(유형 + 자르지 않은 대상 해시) · `cmd_remember` = 그 키 하나만 읽고 쓴다. 잘린 조건 보완(300자 옛 판 조건 · 기록 꼴 호환)은 같은 키 자리 교체로 남겼다(키 공유가 없어 비간섭과 무관 · 범위 밖 변경 0).
- **시험**: 뒤집음 `test_legacy_keys_not_followed`(옛 판 3꼴 + 앞 120자 해시 기록 = 따르지 않고 재기록도 안 막음) · **비간섭 전수 `test_two_subjects_non_interference`** = 두 대상(정규화 120자 A · A + 「 추가」) × A 키 자리 상태 5(없음·허락·안 함·조건·**잘린 조건 = R10 반례 자리**) × 첫 쓰기 6(뜻 3 × 사용자 변경) × 둘째 쓰기 3 × 차례 2 × 유형 2(external_send · login 사용 근거 있음) = 360 꼴 — 판정식 = 「한 대상의 쓰기 전후 다른 대상의 판정 같음」(구현과 독립) · 08630b53 원본에서 적(실측). 상태 전수는 한 키 × 상태 5 × 뜻 3 × 사용자 변경 = 30 꼴로 줄였다. 지운 시험 = 공존·순위·옛 키 이관 4개(대상 코드째 삭제).
- 뮤턴트: 삭제 11(M88·M94·M106·M111·M113·M114·M115·M125~M128 — 대상 코드 없음) · 다시 씀 3(M54·M78·M105) · 신설 2(M131 옛 판 키 다시 따름 · M132 키를 앞 120자로 = 별칭 부활).

R10 반영 뒤 누계: 시험 122 녹(`-W error`) · self-test 2,776 조합 · 뮤턴트 **119/119** KILLED · 바뀐·새 시험 2개(`test_legacy_keys_not_followed` · `test_two_subjects_non_interference`)는 08630b53 원본에서 적(실측).
