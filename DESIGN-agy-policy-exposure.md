# 설계 — cysr 이 사용자의 구글 개인 계정을 약관 위험에 놓는 자리 전수 + 최소 수리안

> TICKET=cysr-agy-policy-exposure · 1단계(조사·설계 · **코드 수정 0**) · 작성 = worker-10(surface:1942) · 2026-11-11
> 기준 = 가지 `fix/agy-policy-exposure` ← v1.1.14 `270e3e21` · 원작자 비교 = upstream 태그 v0.14.54(로컬) · v0.14.55·v0.14.56(GitHub API 읽기)
> 이 문서는 표와 설계만 담는다. agy 를 실행·로그인·호출하지 않았고(시험 포함), 구글 포럼·이슈에 아무것도 쓰지 않았다.

---

## 0. 한 줄 결론

- **설치 직후, 사용자가 아무 말도 하지 않으면 cysr 은 agy 를 띄우지 않는다(아니오).** 기본 부트·부서 편성·데몬 자동 재기동 어느 것도 agy 를 세우지 않는다(코드로 확인 — §2-1).
- 그러나 **사용자가 agy 를 깔아 둔 PC 에서는, Claude 지휘자가 스스로 판단해 agy 좌석을 띄우고 지시를 타이핑해 넣는 길이 열려 있다.** 지휘자 지침(MASTER_DIRECTIVE §7)이 「중요 포인트에는 agy·codex 리뷰어를 **의무적으로** 사용한다」고 시키기 때문이다. 이것이 구글이 개인 요금제에서 「아니오」라고 한 바로 그 모양(ⓐ)이다.
- 한 번 agy 좌석이 생기면 **앱 재시작·업데이트·재부팅 때마다 복원기가 사람 손 없이 agy 를 다시 띄우고 지침을 다시 넣는다**(ⓐ).
- 권고 = **㉮ 「Claude·cys 가 agy 좌석을 띄우는 길」을 바이너리 한 곳에서 닫고(컴파일 상수 휴면), 리뷰어 슬롯은 이미 있는 Claude 대체 리뷰어로 자동 폴백 + 지침 문구 정리.** 사람이 cys 탭에서 직접 `agy` 를 치는 것은 그대로 둔다.

---

## 1. 근거 — 구글 원문 (재열람 결과)

> §1 의 문구·날짜는 2026-11-11 공개 페이지를 다시 열어 확인한 결과다(핵심 문장은 원본 파일에서 글자 그대로 재확인). 상세 인용·URL·날짜 = 부록 A.

- **브리프 인용과 일치**: FAQ 두 문장(「Wrapping agy inside third-party coding agents or applications … is not supported under consumer plans」 · 「Using third-party software … to access Antigravity is a violation of our Terms of Service … suspension or termination … we recommend using a Gemini Enterprise or Google AI Studio API key」)이 오늘도 그대로 있다. FAQ 에는 날짜 표기가 없다.
- **브리프에 없던 것 3가지**: ① 약관 본문 6항이 같은 금지를 **계약 조항**으로 둔다(「breach of this Agreement」 · Antigravity **및 Gemini CLI** 계정 정지 사유) ② Gemini CLI 는 2026-06-18 부터 개인 로그인(무료·AI Pro·Ultra)을 받지 않는다 — 개인 계정으로 Gemini 를 부를 다른 CLI 길이 없다 ③ 포럼에서 「아니오」라 답한 사람(Naveen)은 포럼 표지상 **직원 표시가 없다(미확인)** · 직원 표시가 있는 유일한 답(09-30)은 「예」였으나 이후 FAQ 가 우선한다고 공지됨. 판정은 포럼이 아니라 FAQ·약관 원문으로 충분하다.
- 바깥에서 실제 정지 보고가 나왔다(11-06 oh-my-pi 사용자 「banned today by Google」 · 부록 B) — 위험은 이론이 아니다.

### 1-1. cysr 의 쓰임을 원문에 대어 보면
cysr 의 「제미나이 검토자」 = **cysr(제3자 응용)이 agy 를 자기 창 안에서 띄우고(`cys launch-agent --agent gemini` → `~/.local/bin/agy --dangerously-skip-permissions`), 역할 지침을 입력창에 타이핑해 넣고(launch-agent 주입), 그 뒤 Claude 지휘자가 `cys send --to reviewer-gemini` 로 검토 의뢰를 계속 타이핑해 넣는 구조**다. 사람은 그 창에 입력하지 않는다(우리 운영 규칙도 「워커·리뷰어 창엔 사람이 입력하지 않는다」). 이는 원문의 「third-party coding agents or applications 안에 agy 를 감싸 넣기」, 포럼의 「Claude Code 가 공식 agy 를 하위 프로세스로 띄움」·「다중 에이전트 틀의 일꾼」에 **문언 그대로** 해당한다. 해석의 여지가 거의 없다.

---

## 2. 자리 전수

### 2-0. 세는 법
- 대상 = 저장소 `src/`·`src-tauri/`·`ui/`·`cysjavis-pack/`·`scripts/`·`docs/`·`README*`·`USER-MANUAL.md`. 정규식 `\bagy\b|antigravity|gemini`(대소문자 무시) grep.
- **원시 줄 수(2,937줄)** 는 대부분 위험과 무관하다 — 시험 파일, 그리고 「agy 1R」 같은 **과거 검토 인용 주석**(개발 중 우리가 agy 를 검토자로 썼던 흔적)이다. 그래서 표는 **실행 경로 단위(자리)** 로 센다. 원시 분포:

| 영역 | 줄 | 그중 시험 파일 | 그중 검토 인용 주석(위험 무관) |
|---|---:|---:|---:|
| src | 1,207 | 20 | 136 |
| src-tauri | 16 | 0 | 7 |
| ui | 200 | 127 | 19 |
| cysjavis-pack | 709 | 296 | 52 |
| scripts | 11 | 3 | 7 |
| docs(내부 설계·인계 문서) | 760 | 33 | 264 |
| README.md / README.en.md / USER-MANUAL.md | 2 / 2 / 30 | 0 | 0 |

- **설치기**: 이 저장소에 agy 를 내려받거나 로그인시키는 설치 단계는 없다(`scripts/`·`dist-win/`·`update-worker/` grep 0건 — scripts 11줄은 전부 검토 인용 주석). agy 설치 안내는 바이너리 안 문자열 2곳뿐(§2-2 #15). 별도 설치기 저장소는 이 저장소 안에서 확인되지 않았다(있다면 master 가 위치를 알려 줄 것).
- **공개 사이트** `docs/index.html`: agy·Gemini 언급 0건.

### 2-1. 기본값이 안전한가 — 새 설치 경로를 따라가 봄(코드 추적)

| 단계 | 코드 | agy 가 불리는가 |
|---|---|---|
| 앱 첫 실행 → 팀 부트 | `src-tauri/src/main.rs:7104` `spawn_orchestra_boot` → `cys boot` → `src/bin/cys.rs:12553` `BOOT_PLAN = [cso, worker]`(둘 다 claude) | **아니오** |
| 마스터 선언 부트 | `cysjavis-pack/bin/javis_orchestra.py:167` `BOOT_PLAN` 같은 2행 · `cmd_boot_reviewers`(`:1361`) 는 `--spawn` 없으면 **스폰 0** | **아니오** |
| 부서(팀) 만들기 — 단추·말 | `javis_formation.py:106` `REQUIRED_ROLES = (master, cso, worker)` · 리뷰어 「온디맨드」 | **아니오** |
| 데몬: 죽은 좌석 자동 재기동 | `src/bin/cysd/governance.rs:886` `CYS_AGENT_AUTORESTART` 기본 **꺼짐** | **아니오** |
| 데몬: agy 사용량 갈래·상태줄 자동 연결 | `src/lib.rs:3022` `AGY_LANE_COMPILED = false`(1.1.10 휴면) · `src/pack.rs:1346` 설치 때 연결 안 넣음 | **아니오** |
| 데몬: agy 쿼터 수집기 | `src/bin/cysd/usage.rs:3248` 상시 돌지만 **agent=gemini 좌석이 있을 때만** 일함(`:3275`) | 좌석 없으면 **아니오** |

→ **새 설치 · 사용자 무발화 = agy 호출 0.** 단, 이것은 「agy 좌석이 한 번도 생기지 않았을 때」의 이야기다. 아래 #1~#6 중 하나로 좌석이 한 번 생기면 #7·#8 이 사람 손 없이 그 좌석을 이어 간다.

### 2-2. 자리 표

열 뜻: **언제** = 기본 부트 / 사용자가 말로 시킬 때 / Claude 가 스스로 / 자동(재시작·복원) · **입력** = agy 입력창에 누가 글을 넣는가 · **로그인** = 사용자 구글 로그인(OAuth)을 쓰는가 · **등급** = ⓐ 구글이 「아니오」라 한 모양 / ⓑ 애매 / ⓒ 허용(사람이 직접) / ― 위험 없음(문구·표시뿐).

| # | 자리(파일:줄) | 무엇 | 언제 | 입력 | 로그인 | 등급 · 근거 |
|---|---|---|---|---|---|---|
| 1 | `cysjavis-pack/agents.json:34-35` 어댑터 `gemini` | `cmd = ~/.local/bin/agy --dangerously-skip-permissions` · 지침을 stdin 으로 밀어 넣는 어댑터 정의 | (정의 — 아래 모든 기동의 원천) | cys(launch-agent 주입) | 예(agy 첫 기동 OAuth — `notes`: 「로그인은 사람 단계(Google OAuth)」) | **ⓐ** — 「wrapping agy inside third-party … applications」 |
| 2 | `src/bin/cys.rs:20626` `run_launch_agent_opts` · `:16987` `boot_agent_on_surface` (`cys launch-agent --role reviewer-gemini --agent gemini`) | agy 를 cys 창에 띄우고 역할 지침을 타이핑 | 이 명령을 부르는 모든 경로(#3~#8) | cys → 이후 Claude 지휘자 | 예 | **ⓐ** — 제3자 응용이 agy 를 띄우고 입력을 넣음 |
| 3 | `cysjavis-pack/directives/MASTER_DIRECTIVE.md:461-468` §7 「중요 포인트에는 **agy·codex 리뷰어를 의무적으로** 사용」 · `:521-523` 앵커4-6 「deep research = agy 담당」 · `:525-528` 앵커4-7 무승인 모드 · `:173` 여는 법 | Claude 지휘자에게 agy 를 띄워 부리라고 **지시** | **Claude 가 스스로**(agy 가 설치돼 있으면) | Claude 지휘자 | 예 | **ⓐ** — 포럼 「Claude Code 가 agy 를 하위 프로세스로」·「다중 에이전트 일꾼」 그대로 |
| 4 | `directives/CEO_TEMPLATE.md:316·604-611·664-670·853-860` | 부서장(CEO) 지침 — #3 과 같은 문면 | Claude 가 스스로(부서) | Claude | 예 | **ⓐ** |
| 5 | `directives/WORKER_DIRECTIVE.md:256-258` §11 · `REVIEWER_DIRECTIVE.md:1·156` · `RSI_LEARNING_DIRECTIVE.md:73`(「cys=agy·codex 등」 이종 검증) · `VIBECODING_ENFORCEMENT.md:19` | 워커·학습 루프·바이브코딩도 agy 검증을 쓰라고 지시 | Claude 가 스스로 | Claude(워커가 `cys send` 로 리뷰어 의뢰 — §11 허용) | 예 | **ⓐ** |
| 6 | `cysjavis-pack/bin/javis_orchestra.py:147-149` `REVIEWER_SLOTS` · `:291` `detect_reviewer` · `:1361` `cmd_boot_reviewers --spawn` | agy 가 **설치돼 있으면 네이티브 agy 를 먼저** 띄움(없을 때만 Claude 대체) | Claude 가 스스로(지침 #3 이 부르는 명령) · 사용자가 말로 시킬 때 | Claude | 예 | **ⓐ** |
| 6-b | `cysjavis-pack/skills/appbuild-plan-debate/SKILL.md:3·13` 「gemini·codex 2명이 10턴+ **인간 개입 없이** 토론」 · `skills/vibecoding/SKILL.md:80·91·126` | 스킬이 agy 기동·라운드를 지시 | 사용자가 「앱 만들어」 등 말할 때 스킬이 스스로 | Claude | 예 | **ⓐ** — 「인간 개입 없이」가 문면에 있다 |
| 7 | `cysjavis-pack/bin/javis_phoenix.py:2786` `spawn_fresh_production`(launch-agent `--agent <저장된 agent>`) · `:3777` | 복원기가 topology 에 남은 reviewer-gemini 를 **fresh 재기동** | **자동** — 앱 재시작·업데이트·데몬 사건 | cys(지침 + `[RESTORE]`) | 예 | **ⓐ** — 사람 손 0 의 자동 기동 |
| 8 | `src/bin/cys.rs:25801` `run_restore`(GUI 콜드부트·사이드카 `src-tauri/src/main.rs:4231` 가 `restore --include-master` 호출) | topology 의 모든 좌석을 agent 그대로 재기동(`--continue` 이어붙기) — gemini 포함, 거르는 조건 없음 | **자동** | cys | 예 | **ⓐ** |
| 9 | `ui/src/main.ts:9023`(명령 팔레트 「재기동 → reviewer-gemini」) · `:4977`(부서 간 전출 `LAUNCH_BY_ROLE`) | 사람이 단추를 눌러 agy 좌석을 띄움 — 그 뒤 입력은 Claude | 사용자가 누를 때 | 띄움 = 사람 클릭 · 이후 입력 = Claude | 예 | **ⓐ** — 띄운 손은 사람이어도 그 뒤 agy 를 부리는 것은 Claude·cys |
| 10 | `src/bin/cysd/usage.rs:3104` `agy_quota_probe` | agy 좌석이 있으면 데몬이 agy 안의 **로컬 언어 서버**(127.0.0.1)에 `RetrieveUserQuotaSummary` 를 curl 로 두드림 — 토큰 없이 보내 지금은 401(CSRF) 로 거절됨(`:2819-2826` 주석 · 2026-09-23 실측) | 자동(agy 좌석이 있을 때 · 15초 주기 · 거절 후 백오프) | cys(데몬) | 토큰은 읽지 않음 | **ⓑ** — 「제3자 소프트웨어로 Antigravity 접근」에 문언상 걸칠 수 있으나, 로컬 호출이고 인증 없이 거절되며 구글 서버로 나가지 않는다. 판단 근거 부족 — 애매로 둔다 |
| 11 | `cysjavis-pack/hooks/cys-agy-statusline.sh` · `src/agy_statusline.rs` · `src/pack.rs:1339-1381` | agy 의 **공식 상태줄 기능**(agy 가 사용자 설정의 명령을 부름)에 cys 스크립트를 연결 — 1.1.10 부터 cysr 은 새로 넣지 않음(휴면) · 예전 판이 넣은 연결은 남아 있을 수 있음 | 사람이 agy 를 쓸 때 agy 가 부름 | agy → cys(방향이 반대) | 해당 없음(쿼터 숫자만) | **ⓑ(낮음)** — agy 가 공식 기능으로 사용자 명령을 부르는 것이라 「agy 를 감싸기」는 아니다. 다만 Antigravity 데이터를 제3자 앱이 받는다는 점에서 0 은 아님 · 이미 휴면 |
| 12 | `src/bin/cysd/accounts.rs:545·908·1015` · `ui/src/usagebar.ts` | agy 계정 사용량 표 귀속 | 휴면(`AGY_LANE_COMPILED=false`) | ― | ― | **―** (실행되지 않음) |
| 13 | `src/bin/cysd/governance.rs:1100-1106` | agy 좌석이 죽으면 지휘자에게 「에이전트 agy 종료 감지 — 처리하라」 한 줄 | 자동(좌석이 있을 때) | cys → **Claude 지휘자**에게(agy 아님) | ― | **ⓑ(낮음)** — 그 자체는 agy 를 부르지 않으나, 지휘자가 「처리」로 재기동할 계기가 된다 |
| 14 | 사람이 cys 탭(셸)에서 직접 `agy` 를 치고 직접 대화 | cys 는 터미널 에뮬레이터 역할만 | 사람이 할 때 | **사람** | 예 | **ⓒ** — 원문 「사람이 터미널에서 직접」. 단 그 창에 Claude 가 `cys send` 로 쓰면 ⓐ 가 된다(그래서 #3 지침에 금지 문장이 필요) |
| 15 | `src/bin/cys.rs:14271·14287` 설치 안내 문자열(「Antigravity CLI `agy` 설치 후 …」·「npm i -g @google/antigravity」) | agy 설치를 권함 | `cys boot`/`agent-detect` 의 미설치 안내에 표시 | ― | ― | **―→ⓐ 유도** — 그 자체는 무해하나 ⓐ 용도로 설치를 권한다 |
| 16 | `README.md:242·317` · `README.en.md:215·295` | 「Claude·Gemini·Codex 3사 리뷰어가 **상근**」 홍보 문구 | 공개 문서 | ― | ― | **―→ⓐ 유도** — 그 쓰임을 장점으로 광고 · 게다가 「상근」은 2026-09-10 온디맨드 정책 이후 사실과도 다름 |
| 17 | `USER-MANUAL.md:53-54·88·545-556` | 「팀원 자리는 설치된 프로그램(claude·agy·codex)의 자리만 … 리뷰어 자리(agy·codex)는 설치했을 때만 생김 · 최대 5자리」 | 공개 설명서 | ― | ― | **―→ⓐ 유도** + **사실 불일치**: 현행 편성 코드(`javis_formation.py:106`)는 리뷰어를 세우지 않는다(3자리). 문구가 낡았다 |
| 18 | `USER-MANUAL.md:332-336·420·438·467·1795·1930-1932` | Antigravity 사용량 휴면 고지 · 노드 표시 이름 | 공개 설명서 | ― | ― | **―** (사실 고지) |
| 19 | 표시 전용: `ui/src/seatlayout.ts:461-478`(agy 칸 배치) · `ui/src/appearance.ts:65`(색) · `ui/src/roleactivity.ts` · `src/bin/cysd/panetitle.rs` · `src/readiness.rs`(gemini 화면 판독) · `src/first_run_gates.rs` · `src/bin/cysd/classifier.rs`·`receiver.rs`(gemini 이름 인식) · `src/factory_reset.rs:853-985`(예전 연결 제거) · `cysjavis-pack/bin/javis_resource_gate.py`(프로세스 집계) · `javis_formation.py`(ROLE_CLI 표) · `javis_radio.py:99`(리뷰어 격리) | 이미 떠 있는 좌석을 그리거나, 이름을 알아보거나, 지우는 코드 | ― | ― | ― | **―** (agy 를 띄우거나 입력하지 않음) |

**집계(실행 경로 단위)**: 자리 19개(6-b 포함 20행) — **ⓐ 10**(#1·2·3·4·5·6·6-b·7·8·9) · **ⓑ 3**(#10·11·13) · **ⓒ 1**(#14) · **― 6**(#12·15·16·17·18·19 — 그중 #15·16·17 은 ⓐ 를 **유도**하는 문구라 수리 대상).

### 2-3. 기존 사용자(업그레이드)는 어떤가
- 예전 판(0.14.x 원작자 판, 또는 2026-09-10 이전 우리 판)은 `cys boot` 가 리뷰어 3행(reviewer-gemini·codex·grok)을 **부트 때마다 세웠다**(실패해도 부트는 계속되는 Degrade 행 · `cys.rs:12545-12551` 주석의 이력 · 원작자 v0.14.54 `src/bin/cys.rs:11871-11877` 에 그 3행이 지금도 있다 — §3). 그 시절 설치본의 `topology.json` 에 `reviewer-gemini` 가 남아 있으면 **#8 복원이 앱을 켤 때마다 agy 를 다시 띄운다.** 업그레이드 사용자는 「아무 말도 안 했는데 agy 가 뜨는」 상태일 수 있다 — 실측은 하지 않았다(라이브 `~/.cys` 무접촉 규칙). 2단계에서 격리 HOME 으로 재현할 것.
- `~/.cys/pack/agents.json` 은 사용자 소유라 팩 갱신이 덮지 않는다(agents.json `_doc` · W-B 이관 규칙). **그래서 수리는 agents.json 이 아니라 바이너리 쪽 게이트여야 기존 설치에도 닿는다.**

---

## 3. 원작자(upstream) 상태

- 확인 범위: 로컬 태그 v0.14.52~v0.14.54 커밋 본문 grep(「terms of service·약관·suspen·consumer·third-party」 0건) · GitHub API 로 v0.14.55·v0.14.56(2026-11-01 발행) 릴리스 노트 grep 0건 · `main` HEAD `ed367aa7`(2026-10-31) · 이슈 목록 검색(agy·antigravity·gemini·약관).
- 결과: **원작자는 이 문제를 다루지 않았다.** 게다가 원작자 판은 우리보다 노출이 크다 — v0.14.54 `src/bin/cys.rs:11871-11877` 의 `BOOT_PLAN` 에 `("reviewer-gemini", "gemini", false)` 행이 남아 있어, **agy 가 깔린 PC 에서는 `cys boot`(앱 첫 실행 팀 부트 포함)만으로 agy 가 뜬다**(우리 cysr 은 2026-09-10 에 이 행을 뺐다 · v0.14.55·56 의 같은 줄은 파일이 커서 API 로 확인하지 못함). v0.14.56 의 `agents.json` gemini `cmd` 는 그대로 `~/.local/bin/agy --dangerously-skip-permissions` 이고, `MASTER_DIRECTIVE.md` 의 「agy·codex 리뷰어를 의무적으로」 문장도 그대로 있다. 열린 이슈 #70·#83(agy 좌석 큐 배달 결함)은 오히려 agy 좌석을 **더 잘 부리려는** 방향이다.
- 함의: 맞출 방향이 없다. 우리 수리는 원작자 코드를 지우지 않고 **우리 판에서 켜지 않는**(1.1.8 휴면 스위치와 같은 꼴) 방식이어야 병합 충돌이 작다. 원작자에게 알릴지는 공개 행위라 master 판단(§6 📌).

---

## 4. 바깥 증거 — 같은 문제를 겪은 다른 오픈소스

3건 이상이 11월 첫 열흘 안에 같은 결론에 닿았다(상세 = 부록 B): **oh-my-pi** 는 실제 사용자 정지 보고 뒤 Antigravity 를 「일시정지」(로그인·사용량 조회까지 거부, 저장 로그인은 보존) · **craft-anything** 는 agy 실행 어댑터를 지우고 `agy` 이름을 거부하는 PR(미병합) · **agentv-os** 는 처음부터 구글 개인 로그인을 빼고 API 열쇠만. 공통 처방 = **끄되 지우지 않음 + API 열쇠로 안내** → 우리 ㉮(+ 나중에 ㉯)와 같은 방향.

---

## 5. 수리안

공통 전제: ⛔agents.json 은 사용자 소유라 손대도 기존 설치에 안 닿는다 → 게이트는 **바이너리**에. 지침(pack)은 팩 갱신으로 닿는다.

### ㉮ Claude·cys 가 agy 좌석을 띄우는 길을 닫음 + Claude 대체 리뷰어로 자동 폴백 + 지침·문구 정리 (권고)

| 조각 | 파일 · 바뀌는 곳 | 줄 수 추정 |
|---|---|---:|
| ㉮-1 휴면 술어 | `src/lib.rs` `dormant` 모듈에 `AGY_SEAT_COMPILED: bool = false` + `agy_seat_enabled()` + 「이 어댑터가 agy 인가」 순수 판정(어댑터 키 `gemini` **또는** cmd 바이너리 basename `agy`/`agy.exe` — 사용자가 키를 바꿔도 잡힘) | +30 |
| ㉮-2 기동 거부 | `src/bin/cys.rs` `run_launch_agent_opts`·`boot_agent_on_surface` 진입에서 agy 면 **스폰 0 · 새 exit 코드 · 한국어 처방**(「구글 개인 요금제 약관상 cysr 은 agy 를 띄우지 않습니다 — 직접 쓰려면 새 탭에서 agy 를 치세요」). 이 둘이 #2·#6·#7·#8·#9 의 **공통 길목**이다(phoenix·restore·UI·boot_node 전부 launch-agent/boot_agent_on_surface 경유 — 코드로 확인) | +25 |
| ㉮-3 감지 오라클 | `src/bin/cys.rs` `run_agent_detect` 가 agy 어댑터를 `installed:false · reason:"agy_consumer_policy"` 로 낸다 → `javis_orchestra.detect_reviewer` 1순위가 이 오라클이므로 **python 수정 없이** `reviewer_roster` 가 `reviewer-claude-1`(반증 페르소나 · REVIEWER_DIRECTIVE §6) 로 자동 폴백 | +10 |
| ㉮-4 복원 처리 | `run_restore`·phoenix 가 ㉮-2 거부를 받으면 그 좌석만 「건너뜀(사유)」 한 줄 · 실패로 세지 않음(리뷰어는 이미 Degrade 정책) — 기존 typed outcome 에 사유만 추가 | +15 |
| ㉮-5 지침 | `MASTER_DIRECTIVE §7·앵커4-6·4-7·④-b` · `CEO_TEMPLATE` 같은 곳 · `WORKER_DIRECTIVE §11` · `REVIEWER_DIRECTIVE` 머리·§6 · `RSI_LEARNING §6` · `VIBECODING_ENFORCEMENT` · 스킬 `appbuild-plan-debate`·`vibecoding`: 「agy·codex」→「codex · Claude 대체 리뷰어」 + 금지 1문장(「agy 좌석을 띄우거나, 사람이 연 agy 창에 `cys send` 로 쓰지 마라 — 구글 개인 요금제가 금지하는 쓰임이며 사용자 계정이 정지될 수 있다」) · 출하 지침 해시표 재생성(`scripts/gen_released_directive_hashes.py`) | ±40(문면) |
| ㉮-6 UI | `ui/src/main.ts:4977·9023` 의 `reviewer-gemini` 행 제거(팔레트에서 안 보이게) · 시험 갱신 | −4, 시험 ±10 |
| ㉮-7 문구 | `README(.en).md` 「3사 리뷰어 상근」 → 사실대로 · `USER-MANUAL` §2 머리·§545-556 낡은 5자리 문구 정정 + 새 절 「Antigravity(agy) — cysr 이 띄우지 않는 이유」 · 설치 안내 문자열 #15 에서 agy 권유 제거 | ±40(문면) |

- **왕초보 화면 변화**: 거의 없다. 기본 상태에서 agy 는 원래 안 떴다. 「검토자」가 필요해질 때 agy 창 대신 Claude 대체 검토자 창이 뜬다(라벨 「Claude 대체」 — 이미 있는 화면). agy 를 직접 쓰고 싶은 사람은 새 탭에서 `agy` 를 치면 된다.
- **기존 사용자 영향**: topology 에 reviewer-gemini 가 남은 설치본은 다음 재시작부터 그 좌석이 **안 뜨고** 「건너뜀(사유)」 한 줄이 남는다. 리뷰 품질: 벤더 다양성이 Claude+codex 둘로 줄어든다(REVIEWER_DIRECTIVE §6 가 이미 정직 라벨·페르소나로 보완하는 설계).
- **원작자 병합에 대한 내성**: 원작자 판 `BOOT_PLAN` 에는 reviewer-gemini 행이 있으므로(§3), 앞으로의 원작자 병합에서 그 행이 되살아날 수 있다. 게이트를 **편성표가 아니라 기동 길목(㉮-2)** 에 두면 그 경우에도 agy 는 뜨지 않는다 — 이것이 편성표 수정만으로는 부족한 이유다.
- **원작자 병합 충돌**: ㉮-1~4 는 우리 `dormant` 모듈(원작자에 없음)과 함수 머리 몇 줄 → 작음. ㉮-5 지침은 원작자 파일의 같은 문단을 고치므로 **원작자가 그 문단을 바꿀 때마다 충돌**한다 — 줄이려면 문단을 고치지 말고 각 지침 §7 머리에 「cysr 판 덮어쓰기」 문단 하나만 **추가**하는 꼴을 권함(삽입은 충돌이 작다). agents.json·REVIEWER_SLOTS 는 건드리지 않는다.
- **되돌리기**: 상수 `AGY_SEAT_COMPILED=true` 빌드 + 지침 문단 제거. 1.1.10 agy 갈래 휴면과 같은 꼴이라 시험 이음매(`force_for_thread`)도 재사용.
- **남는 것(1.1.16 이후)**: ① 자율주행 축1 `gate-status` 의 평가자 표가 `gemini` 를 요구한다(`javis_orchestra.py:3072`) — agy 가 없으면 수렴 불가. 자율주행은 기본 꺼짐·임무 게이트라 1.1.15 위험은 아니지만 정리 필요(평가자 칸을 「이종 리뷰어 2」로 일반화 · 대체 리뷰어는 정직 라벨) ② #10 쿼터 수집기는 ㉮-2 로 gemini 좌석이 사라지면 저절로 놀지만, 코드 자체 휴면은 따로(oh-my-pi 가 사용량 조회까지 끈 선례 — 부록 B · 같은 휴면 상수 하나로 묶으면 +3줄).

### ㉯ Gemini 검토자를 API 열쇠 방식 어댑터로 바꿈 (열쇠 없으면 codex·Claude)
- 내용: 새 어댑터 `gemini-api` — 구글이 권하는 길(AI Studio·Vertex API 열쇠)로 Gemini 를 부르는 검토자. 열쇠가 없으면 ㉮ 처럼 폴백.
- 파일: agents.json 새 어댑터(사용자 소유 파일이라 임베드 계층으로) · 어떤 CLI 를 쓸지(구 Gemini CLI 의 API 열쇠 모드 등) 선정·실측 · 준비 표지(ready/prompt marker)·관문 판독 실측 · 열쇠 보관(값 비노출) · 설명서 절 — **수백 줄 + 실측 여러 번**.
- 왕초보 화면: 「Gemini 열쇠 넣기」 칸이 새로 생김. 열쇠 발급은 사용자의 **유료 과금 동의**가 필요할 수 있다.
- 기존 사용자: 열쇠를 넣기 전엔 ㉮ 와 같다.
- 원작자 충돌: 새 어댑터·감지 표를 늘리므로 중간.
- 되돌리기: 어댑터 제거.
- 판단: **1.1.15(11-18 동결)에는 무리**. 벤더 다양성을 되찾고 싶을 때의 2단계 후보. 돈이 걸리므로 박사님 게이트(①돈).

### ㉰ 고지만 (기동 전 경고 + 설명서)
- 내용: launch-agent 가 agy 기동 직전 경고 한 줄 · 설명서에 「개인 요금제에서는 쓰지 마세요」.
- 줄 수: 20 내외. 화면 변화 작음. 충돌 작음. 되돌리기 쉬움.
- **결함**: 경고를 읽는 것은 사람이 아니라 Claude 지휘자다(#3 에서 Claude 가 스스로 띄우므로). 지침이 「의무」라고 시키는 한 경고만으로는 Claude 가 계속 띄우고, #7·#8 자동 복원은 경고를 볼 사람조차 없다. 왕초보 계정 보호라는 목표를 못 채운다. **권하지 않음.**

### 권고와 1.1.15 최소 조각
- **권고 = ㉮.** 확신도 높음 — 근거: 위험 쓰임의 모든 기동이 바이너리의 두 함수(`run_launch_agent_opts`·`boot_agent_on_surface`)를 지난다는 것을 코드로 확인했고, 대체 리뷰어 폴백 기계가 이미 있어 새 기능이 필요 없다.
- **1.1.15 최소 조각 = ㉮-1 + ㉮-2 + ㉮-3 + ㉮-5 + ㉮-7 의 README/USER-MANUAL 핵심 줄.** 이유: ㉮-2 가 실제 기동을 막고(기존 설치 포함), ㉮-3 이 폴백을 자동으로 만들고, ㉮-5 가 Claude 가 「의무」로 agy 를 찾는 것을 멈춘다. ㉮-4(복원 사유 한 줄)·㉮-6(UI 팔레트)·㉮-7 나머지는 ㉮-2 가 이미 막고 있으므로 1.1.16 으로 미뤄도 위험이 남지 않는다 — 다만 ㉮-4 가 없으면 복원 결과에 「실패」로 보일 수 있어, 시간이 되면 함께 넣는 것이 낫다.
- 검증 계획(2단계): 단위 시험(술어 · 거부 exit · agent-detect 출력) · 격리 HOME 에 reviewer-gemini 가 든 topology 를 심고 `cys restore` → 스폰 0·사유 줄 실측 · `javis_orchestra.py boot-reviewers --spawn --plan` 이 reviewer-claude-1 로 폴백하는지 · 가짜 agy 바이너리(셸 스크립트, 실제 agy 아님)로 「설치된 PC」 재현.

---

## 6. 남은 불확실성 · 박사님/master 판단 거리

- 📌 #10(로컬 언어 서버 프로브)·#11(공식 상태줄 연결)의 등급은 **ⓑ 애매**로 남긴다 — 구글 원문이 「로컬 프로세스에 인증 없이 묻기」·「agy 가 부르는 사용자 명령」을 직접 말하지 않는다.
- 📌 원작자에게 알릴지(이슈 작성 = 공개 행위)는 master·박사님 판단. 우리 수리는 알리지 않아도 성립한다.
- 업그레이드 사용자의 topology 에 실제로 reviewer-gemini 가 남아 있는지(§2-3)는 실측하지 않았다.

---

## 부록 A — 구글 원문 인용(재열람 2026-11-11)

> 수집 = 조사 서브에이전트(curl·Discourse JSON·`gh` 읽기 전용) · **핵심 문장은 worker-10 이 내려받은 원본 파일에서 다시 grep 해 글자 그대로 확인했다**(✔ 표시). 원본 보관 = 이 세션 scratchpad `web/`(faq.txt·terms.txt·t*.json 등 — 커밋하지 않음).

**A-1. Antigravity FAQ** — https://antigravity.google/docs/faq/ · 페이지에 날짜 없음(서버 `Last-Modified` 2026-11-10 16:09 GMT = 배포 시각이지 내용 날짜 아님)
- ✔ 「Why can't I use third-party software (such as Claude Code, OpenClaw, or OpenCode) with my Antigravity login?」 → 「Using third-party software, tools, or services to access Antigravity is a violation of our Terms of Service and severely degrades the experience for legitimate product users. Such actions can result in suspension or termination of your account. To use a third-party coding agent with Gemini, we recommend using a Gemini Enterprise or Google AI Studio API key.」
- ✔ 「Can I use Antigravity CLI headless mode in third-party coding agents or automate account switching?」 → 「Antigravity CLI headless mode (agy -p) is intended for direct scripting and CI workflows. Wrapping agy inside third-party coding agents or applications, or automating account rotation, is not supported under consumer plans.」
- 주의: 「Wrapping agy」 문장은 `-p` 로 한정하지 않는다 — cysr 처럼 **대화형 agy 화면에 키 입력으로 지시를 넣는 꼴**을 직접 말한 출처는 없지만, 문언은 그것을 빼 주지 않는다(추론 · 확신도 높음).

**A-2. Antigravity 추가 약관** — https://antigravity.google/terms · 날짜 없음
- ✔ 6항: 「You must not abuse, harm, interfere with, or disrupt the Service. This includes, but is not limited to, using the Service in connection with products not provided by us. Using third party software, tools, or services to access the Service (e.g. using OpenClaw with Antigravity OAuth) is a breach of this Agreement. Such actions may be grounds for suspension or termination of your Antigravity and/or Gemini CLI accounts.」

**A-3. Gemini CLI 는 대안이 아니다**
- README(배너 2026-10-28 편집): 「No free tier or Google AI plans: Free individual access and Google AI Pro / Ultra (Google One) moved to Antigravity CLI on June 18, 2026」
- 구글 개발자 블로그(2026-05-19): 「On June 18, 2026, Gemini CLI … will stop serving requests for Google AI Pro and Ultra …」 · 「Gemini CLI will remain accessible via paid Gemini and Gemini Enterprise Agent Platform API keys.」
- → 개인 로그인으로 Gemini 를 부르는 길은 agy 하나뿐이고, 그 길이 막혔다. 남는 길은 **유료 API 열쇠**(㉯)뿐.
- (agents.json gemini `notes` 의 「구 Gemini CLI 가 2026-06-18 소비자 티어 중단되어 이주」 서술과 일치.)

**A-4. 구글 개발자 포럼** (Discourse JSON 의 신원 표지 = `staff`·`moderator`·`primary_group_name`·`flair_name` · ✔ 직접 확인)

| 글 | 날짜 | 답변자 | 신원 표지 | 답 |
|---|---|---|---|---|
| 189905 | 10-16 | Rebbanpalli_Naveen | staff=False · moderator=False · 그룹 없음 · flair 없음 · title 「Regular」 | 자기 스크립트·CI = **Yes** · Claude Code·Codex 가 공식 agy 를 하위 프로세스로 = 개인 요금제에서 **No** · 「The Antigravity FAQ reflects our current policy … and supersedes earlier forum comments where they differ.」 |
| 196472 | 10-29 | Rebbanpalli_Naveen | 위와 같음 | 「Wrapping or embedding agy -p as a worker backend inside third-party coding agents, multi-agent orchestration frameworks, or standalone applications is not supported under consumer plans and can trigger automated Terms of Service enforcement.」 · 「Having an intermediate local Python coordination service spawn and manage the agy -p process … does not change this restriction」 |
| 185992(이전 답) | 09-30 | chunduriv | **staff=True · moderator=True · 그룹 tfteam · flair google** | Claude Code 가 수정 안 한 `agy.exe` 를 headless 로 띄우는 것 = **Yes** — 그러나 189905 답이 「FAQ 가 이전 포럼 답을 대신한다」고 했고, 질문자의 10-01 반문(FAQ 와 모순)에 답이 없다 |
| 199021·198794 | 11-09 | Rebbanpalli_Naveen | 위와 같음 | Claude Code·Codex 가 `agy -p` 를 부르는 것 = 「No … violates Section 6 … can trigger automated account suspension」 |
| 198841 | 11-09 | Rebbanpalli_Naveen | 위와 같음 | 정지된 계정의 자동 이의제기는 **한 번만** 복구 |

- **답변자 신원**: 「아니오」를 말한 Naveen·Ambati 는 포럼 표지상 **직원 표시가 없다(미확인)**. 직원 표시가 있는 유일한 답(chunduriv · 09-30)은 오히려 「예」였고, 그 뒤 FAQ·약관이 더 엄격해졌다. **그러나 판정의 무게는 포럼이 아니라 A-1·A-2 공식 원문에 있다** — 원문만으로 cysr 의 쓰임은 「아니오」다.

## 부록 B — 다른 오픈소스 사례 (✔ = `gh` 로 직접 재확인)

| 프로젝트 | 무엇이 있었나 | 그들이 택한 처방 |
|---|---|---|
| storytold/craft-anything | 이슈 #929(11-05) — 앱 루프 안에서 `agy … -p` 를 돌리는 어댑터 | ✔ PR #1295 「Stop running Antigravity's agy in Craft Anything」 — **열림·미병합**. 어댑터 삭제 + `antigravity` 백엔드·`agy` 프로그램 이름을 **거부**. 기여자: 「Google's ACP page doesn't say whether personal plans may use it through a third-party tool」 이라 ACP 도 안 씀 |
| can1357/oh-my-pi | 이슈 #12487·#18341 — 사용자 「I was banned today by Google」(11-06) · `403 PERMISSION_DENIED` ToS 위반 | ✔ 릴리스 v18.18.4(11-09): 「Paused Google Antigravity, since Google may restrict accounts that use it outside its own apps」 — 로그인·토큰 갱신·**사용량 조회까지** 거부, 저장된 로그인은 보존(규칙을 빼면 다시 동작) · 이 프로젝트는 OAuth 를 직접 재사용한 꼴이라 우리와 모양은 다르다 |
| radomird/agentv-os | ✔ PR #276(11-10 병합) | 구글 개인 요금제 로그인은 **처음부터 넣지 않음** — Google API 열쇠만 지원 |
| cheaper-inference/OmniRoute | PR #19572(11-10 병합 · 조사 서브에이전트 보고 · worker-10 미재확인) | `antigravity`/`agy` 공급자에서 11월 `403 … disabled … violation of Terms of Service` 보고 → AI Studio 열쇠·Vertex 공급자로 안내 |

- 공통분모: **끄되 지우지 않는다**(oh-my-pi 「pause」 · craft-anything 「refuse」) + **API 열쇠 길로 안내**. 우리 ㉮(휴면 상수 + 거부 + 대체 폴백)와 같은 방향이다. oh-my-pi 가 **사용량 조회까지** 끈 점은 우리 #10(로컬 쿼터 프로브)도 ㉮ 범위에서 함께 휴면시키는 근거가 된다.
- 구글 쪽 미해결: google-antigravity/antigravity-cli 이슈 #711(07-29)·#1493(11-10) — 제3자 ACP·PTY 감싸기 허용 여부 질문에 구글 답 없음(조사 서브에이전트 보고).

## 7. 알려진 한계 (1.1.15 판 · 독립 검증 966 · codex 3R 반영 · master 범위 판단 2026-11-11)
- 목적 = 「제품과 선의의 에이전트가 **실수로** agy 를 부리는 길을 닫는다」 — 고의 우회를 막는 보안 경계가 아니다(sudoers·Claude Code 권한 문서와 같은 결론).
- 문자열 판정이 원리상 못 막는 부류: 이름 바꾼 사본 · 심링크 · 변수/`${…}` 에 담은 이름 · `eval` · 글롭(`ag[y]`·`ag?`) · 스크립트 파일(`sh x.sh`·`source`) · 인터프리터 exec(python·perl) · `cys send` 로 맨 셸 좌석에 글자 입력 · 같은 사용자 프로세스의 문 파일 직접 쓰기(표지 = 공개 상수).
- 줄인 부류(목록·규칙으로 닫음): 복합 명령 · 감싸개(env·timeout·sudo·xargs·script 등) · 셸 -c(값 먹는 옵션 포함)·here-string·파이프로 셸에 먹이기 · 리다이렉트 머리 · zsh 앞말 · cmd /c·powershell · find -exec · 치환 본문 재귀 · 인용 안 된 agy 낱말 안전망.
- 무판정 입구였던 곳(일정 command · 채널 · 계정 어댑터 · round-log · Claude 자기 Bash · 닫힌 뒤 agy 좌석 자동 지시)은 같은 판정기로 닫음.
- 다음 판 설계 후보(구현 안 함): C = 데몬이 실행 파일 실체로 agy 프로세스를 찾아 끄는 사후 감시 · D = 문 상태를 앱 서명에 묶기.

