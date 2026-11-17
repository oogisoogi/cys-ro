# 조각 0.5 실측 계획서 — cysr 화면 개편 2단계 (실행 0 · master 승인 뒤 실행)

- TICKET=cysr-ui-slice0-1117 · 2026-11-17 · 워커 surface:2145 · 브리프 [master#52772539]
- 근거 설계 = `~/axdev/cysr-ui-research/P2-DESIGN.md`(762fc10) §11 표 「0.5 실측」 줄 · §2-5 · §13-2 · 검증 `VERIFY-P2-r2.md` §2-1·R6·「미확인」 줄
- 코드 기준 = 이 가지 `feat/ui-slice0`(← `integ/1115-r2` 36412afb). 아래 파일:줄은 이 가지 기준(설계의 cc460b17 줄과 다를 수 있음).
- **이 문서는 계획뿐이다. 이 문서를 쓰는 동안 실측 명령은 하나도 실행하지 않았다.** (읽은 것 = 저장소 코드 · `tart list` 목록 출력 1회)

---

## 0. 무엇을 재나 — 항목표

설계 §11 「0.5」 줄 + 브리프 목록 + 재검증 r2 가 「조각 0.5 에 넣을 것」으로 적은 것을 빠짐없이 모았다. 출처 칸이 「설계」 뿐인 항목은 브리프 목록에는 없으나 설계 0.5 줄에 있는 것이다(범위를 넓힌 것이 아니라 설계 원문 그대로).

| # | 항목 | 왜 필요한가(어느 결정이 기대나) | 출처 |
|---|---|---|---|
| M1 | 원자 제출(`clear_first` + 사람 표지 + `refuse_on_approval`)이 좌석에 실제로 넣는 **바이트와 Enter**(순서·간격) | ㉤·㉩ — 「Ctrl-U → 울타리 붙여넣기 → 400ms 뒤 Enter 한 요청」 가정 | 브리프 · 설계 |
| M2 | **승인·질문 창이 떠 있을 때 거부** — 바이트 0 · 승인 안 눌림 | 4군 ② · R1 | 브리프 · 설계 |
| M3 | `clear_first`+`human:true`+operator 표지 조합이 **타이핑 가드·초안 게이트**를 어떻게 지나는가(사람 초안 있음 · 기계 잔여 있음 · 방금 사람 입력) | 「Ctrl-U 가 사람 초안을 지울 수 있다」 단점의 실제 크기 | r2 「미확인」 줄 |
| M4 | **마스터 좌석 안 `javis_mission.py status`** — 원자 제출 1건 뒤 임무 있음(exit 0 · source = 오너) · 큐(기계) 1건 뒤 임무 무변경 | ㉩ 「대화 화면 말 = 오너 임무」 | 브리프 · 설계 · r2 §2-1 |
| M5 | **U25** Claude Code 가 답하는 중에 울타리 붙여넣기 + Enter 를 받는 꼴(대기 줄에 쌓이나 · 끼어드나 · 버리나) | ㉩ 「마스터가 바쁠 때」 | 브리프 · 설계 §13-2 |
| M6 | **U21** 둘째 줄 이하 맨 앞 `/` 가 울타리 안에서 명령으로 실행되는가 | `composeOutbound` ⑤ 「명령 아님〔추정〕」 | 브리프 · 설계 §2-5 |
| M7 | **U20** 받는 쪽 세션 기록의 꼴 — ⓐ 긴 붙여넣기(설계 §11 착수 전제 표기) ⓑ 큐 묶음 배달 `[큐 다이제스트…]`(설계 §13-2 표기) | 「전달 확인」 판정 재료 | 브리프 · 설계(⚠ 아래 주) |
| M8 | **세션 레코드 `uuid`/`parentUuid`** 존재 · 내 말 레코드의 `parentUuid` = 직전 레코드 `uuid` | §5-2 「전달됨 = 결속 세션 전문 일치 + uuid 부모 잇기」 | 브리프 · r2 F13·T2 |
| M9 | **U26** 결속 세션 id → 파일 찾기(`~/.claude*/projects/*/<id>.jsonl`) — 맥 · 윈 | `chat_transcript` | 브리프 · 설계 §13-2 |
| M10 | **R3** 사람 표지 보내기 뒤 30초 동안 마스터로 가는 큐 배달이 묶이는가 · 그동안 승계 거절 사유 | §2-5 R3 · §6-2 「30초 1회」 예외 | 설계 |
| M11 | **V-N1** 좌석 밖 이름 보고자(`usage.report_named`) 칸에 마스터 역할이 실리는 꼴 | §9-3 「대화 화면 불가 = 긍정 신호」 | 설계 |
| M12 | **R6** 목록 조회 왕복 시간(쓰기 직전 재조회 창의 크기) — 데몬 쪽 몫 | r2 R6 「수십 ms 안팎 · 실측 = 조각 0.5」 | r2 |

⚠ **주(설계 안 표기 갈림 · 발견 1건)**: 설계 §11 착수 전제는 「긴 붙여넣기의 세션 레코드 꼴(U20)」이라 쓰고, §13-2 표는 U20 을 「큐 묶음 배달 `[큐 다이제스트…]` 꼴」로 적었다. 둘 다 재는 것이 싸므로 M7 을 ⓐ·ⓑ 둘로 나눴다 — 번호 정리는 설계 다음 고침 때(master 판단).

---

## 1. 어디서 재나 — 시험 환경

### 1-1. 후보 비교 (권고 = A)

| 기준 | **A. tart VM `jarvis-clean-vanilla` 복제본**(권고) | B. 이 기기 안 별도 프로필·별도 소켓 | C. tart VM `vm-v117-login-base` 복제본 |
|---|---|---|---|
| 박사님 실사용 데몬·마스터·앱과의 분리 | **완전** — 다른 커널·다른 파일 시스템·다른 launchd. 이 기기의 유닉스 소켓은 VM 안에서 보이지 않는다(구조상 접근 불가) | **부분** — 같은 사용자 계정·같은 launchd·같은 `~/Library`. 장기기억 함정 3건이 바로 이 꼴에서 났다: 좌석 env 의 `CYS_*` 가 시험을 실 데몬으로 끌어감(pack-test-env-must-strip-cys-prefix) · 빈 HOME 에서도 PATH 의 실 `cys` 가 cysd 를 자동 기동 · 가짜 claude 도 등록을 함 | 완전(A 와 같음) |
| 진짜 Claude Code 가 필요한 항목(M4~M9) | VM 안에서 Claude Code 설치 + **시험 계정 로그인** 필요 | 같은 기기 계정 설정을 공유할 위험(`CLAUDE_CONFIG_DIR` 하나 빠지면 실사용 설정에 씀) | 이름상 로그인 단계가 끝난 바탕 — **무엇이 로그인돼 있는지 미확인**(실행 전 확인 1회) |
| 되돌림 | 복제본 삭제 1줄(원본 무손상) | 지운 것·남은 것을 사람이 대조해야 함(소켓·launchd·토큰 파일) | 복제본 삭제 1줄 |
| 비용 | VM 1기(디스크 50GB 표기 · 복제는 APFS 복제) | 0 | A 와 같음 |

- **버린 안 B 의 까닭(1줄)**: 「오염 0」을 증명하려면 분리가 구조로 성립해야 한다 — B 는 규율(환경 변수 몇 개)에 기대고, 그 규율이 실제로 세 번 깨졌다.
- **A 와 C 중 고르기**: C 에 시험 계정 로그인이 이미 있으면 C(로그인 단계 절약) · 아니면 A. 어느 쪽이든 **원본 VM 은 건드리지 않고 복제본에서만** 한다.

### 1-2. 환경 준비 (실행 = master 승인 뒤 · 이 칸의 명령은 이 기기에서 치는 것이 `tart` 뿐)

| 단계 | 명령(호스트) | 기대 | 되돌림 |
|---|---|---|---|
| E1 복제 | `tart clone jarvis-clean-vanilla s05-measure` | `tart list` 에 `s05-measure` | `tart delete s05-measure` |
| E2 기동 | `tart run --no-graphics s05-measure &`(창 없는 실행) · `tart ip s05-measure` | IP 1개 | `tart stop s05-measure` |
| E3 빌드 반입 | 이 가지의 앱 빌드 산출물(1.1.15 후보 · 서명 = cys-local 아님 · 시험 전용)을 VM 으로 복사(`tart` 공유 폴더 또는 scp) | VM 안 `~/Applications/cys.app` 실행 가능 | 복제본 삭제로 함께 사라짐 |
| E4 Claude Code | VM 안에서 Claude Code 설치 · **시험 계정 로그인**(master 몫 · 「로그인·권한 인증 전반 = master」 규칙) | VM 안 `claude --version` · 로그인 상태 | 복제본 삭제 |
| E5 대역 좌석 | VM 안에서 `tests/fixtures/fake_claude.c` 를 컴파일해 `claude` 라는 이름으로 PATH 앞에(대역 전용 폴더) — 받은 바이트를 `$HOME/got.log` 에 그대로 쓴다(fake_claude.c:31) · 시각 기록이 필요하므로 **VM 안 사본에만** 줄마다 단조 시각을 덧붙이는 1줄 변형 | 대역 좌석이 등록되고 `got.log` 가 생김 | 복제본 삭제 |

- ⚠ E3 의 「설치」는 VM 안이다 — 브리프의 금지(「설치·발행·서명·~/Applications 쓰기 0」)는 **이 기기** 대상이고, VM 안 설치는 시험 환경 구성이라 따로 master 승인 항목으로 올린다(§5 G2).
- 네트워크: VM 은 Claude API 로 나가야 한다(M4~M9). 그 밖의 바깥 쓰기(깃 push·발행) 0.

### 1-3. 실사용 환경 오염 0 증명 방법

「실행 전 지문 = 실행 뒤 지문」을 기계로 대조한다. 지문은 **읽기만** 하는 명령으로 뜬다(이 기기에서).

| 지문 | 명령(읽기 전용) | 같아야 하는 것 |
|---|---|---|
| F1 데몬 프로세스 | `pgrep -x cysd` · 각 pid 의 `ps -o lstart= -p <pid>` | pid 집합·시작 시각 같음(재기동 0) |
| F2 좌석 표 | `cys list --json`(박사님 데몬) → 좌석 id·역할·에이전트 생존을 정렬해 sha256 | 같음(측정 중 박사님 일로 바뀐 좌석은 그 줄만 사람 확인) |
| F3 팩 | `git -C ~/.cys/pack status --porcelain` 이 없으면 `find ~/.cys/pack -newer <시작 표지 파일> -type f` | 측정 구간에 바뀐 파일 0 |
| F4 앱·설치본 | `/usr/libexec/PlistBuddy -c 'Print CFBundleVersion' ~/Applications/cys.app/Contents/Info.plist` · `codesign -dv` 의 CDHash | 같음 |
| F5 launchd | `launchctl list | grep -i cys` 정렬 sha256 · `ls -l ~/Library/LaunchAgents` | 같음 |
| F6 마스터 대화 | 박사님 마스터 좌석 jsonl 의 크기 증가가 박사님 대화분 말고 없음 — 측정 명령은 이 파일을 읽지도 쓰지도 않는다(구조 증명: 모든 측정 명령은 `tart ssh`/`tart exec` 접두로만 친다) | 측정 명령 출처 0건 |
| F7 인박스·원장 | `~/.cys/cmux-inbox.md`·`~/.claude/channels/.master-send-ledger.jsonl` 에 측정발 줄 0(측정 좌석은 VM 안이라 쓸 길이 없음 — 보고 push 만 예외) | 측정발 0 |

- **구조 증명 1줄**: 측정 명령표(§2)의 모든 줄은 VM 안에서 실행된다(접두 = `vm$`). 호스트에서 치는 것은 `tart` 와 §1-3 읽기 지문뿐이다. 그래서 오염은 「명령표에 호스트 줄이 섞였는가」 한 질문으로 줄어든다 — 실행 기록(셸 이력 사본)을 첨부해 그 질문에 답한다.

---

## 2. 무엇을 치고 무엇을 기대하나 — 항목별 절차

표기: `vm$` = VM 안 셸(`tart ssh` 또는 `tart exec`) · `rpc` = VM 안에서 VM 데몬 소켓에 JSON 한 줄(`{"id":1,"method":…,"params":…}` + 줄바꿈 · Tauri `rpc_full` 과 같은 꼴 · src-tauri/src/main.rs:194~196)을 보내는 작은 파이썬(이 문서 부록 R 의 틀 · VM 안 사본만). 사람 표지 = VM 데몬 소켓 옆 `operator.token`(src-tauri/src/main.rs:5021~5045 와 같은 자리)에서 읽어 `operator_token`·`owner_token` 에 싣는다(앱 `send_input` 과 같은 조건 · main.rs:606~644).

공통 원자 제출 요청(설계 §2-5 「새 방식」 그대로):

```json
{"method":"surface.send_text","params":{"surface_id":<S>,"text":"<본문>","human":true,"quiet":true,
 "queued":false,"clear_first":true,"machine_origin":false,"refuse_on_approval":true,
 "operator_token":"<VM 토큰>","owner_token":"<VM 토큰>"}}
```

### M1 원자 제출 바이트·Enter (대역 좌석 · 진짜 Claude 불필요)

1. `vm$ cys launch-agent --role master --agent claude`(PATH 앞 = 대역) → 좌석 S.
2. `rpc` 공통 요청 · 본문 = `가나 abc`(울타리·한글·공백 확인용).
3. `vm$ od -c ~/got.log` + 시각 기록.
- **기대(설계 가정)**: ① `0x15`(Ctrl-U) ② `ESC [ 2 0 0 ~` + 본문 UTF-8 + `ESC [ 2 0 1 ~`(울타리) ③ 약 400ms 뒤 `\r` 1개 — 바이트 순서 정확히 이 셋 · 응답 `ok:true`.
- 판정: 순서·개수 일치 = 가정 성립 · 간격 실측값을 기록(설계 목표값 400ms 의 실제 값).
- 변형 M1-b: 본문 여러 줄(`첫 줄\n둘째 줄`) → 울타리 안 `\n` 이 그대로인지(Enter 로 바뀌지 않는지).
- 되돌림: 없음(VM 안 파일).

### M2 승인 창이 떠 있을 때 거부 (대역 좌석)

1. 대역 좌석 화면에 데몬이 승인 창으로 읽는 글을 띄운다 — **글은 데몬 시험 고정값을 그대로 쓴다**(cysd 승인 감지 시험의 화면 견본 · 이 문서에 그 영문 원문을 옮겨 적지 않는다: 화면 훑기가 문서 글을 승인 창으로 오탐한 선례 · 워커 지침 「도구 권한 승인 프롬프트는 별개다」 주).
2. 데몬이 승인 대기 항목을 만든 것을 `rpc feed.list` 로 확인(pending 1).
3. `rpc` 공통 요청.
- **기대**: 응답 = 거부(오류 · 「쓰기 직전 승인·질문 창」 · handlers.rs:2927~2956 의 `refuse_on_approval` 경로) · `got.log` 증가 바이트 **0** · `feed.list` 의 그 항목 여전히 pending(승인 안 눌림).
- 변형 M2-b(경합): 승인 창을 요청 직전 100ms 안에 띄움 → 데몬이 「쓰기 직전 재판정」에서 막는가(precut ㉮ 주석 handlers.rs:2927).
- 되돌림: 대역 좌석 종료.

### M3 원자 제출 × 타이핑 가드·초안 게이트 (대역 좌석)

세 장면 각각 공통 요청 1건:

| 장면 | 준비 | 기대(코드 읽기 근거) | 재는 것 |
|---|---|---|---|
| ⓐ 사람 초안 있음 | 사람 표지로 `안녕` 만 넣음(Enter 없음) → `pending_input_human_bytes > 0` | CLI `--clear-first` 설명 = 「사람 초안이 있으면 typing_guard/draft_gate 로 거부 · 기계 잔여만 지운다」(src/bin/cys.rs:95~98) — **그것이 사람 표지 원자 요청에도 같은가가 이 칸의 질문** | 응답 코드 · `got.log` 증가(Ctrl-U 가 나갔나) · 초안 생존 |
| ⓑ 기계 잔여 있음 | 사람 표지 없이 `잔여` 만 넣음 | Ctrl-U 로 지우고 제출(설계 가정) | 바이트 열 · 잔여가 본문 앞에 붙었나(이어붙기 0) |
| ⓒ 방금 사람 입력(3초 안) | 사람 표지 키 1개 직후 | 타이핑 가드가 사람 표지 요청을 막지 않음〔추정〕 | 응답 코드 |

- 판정: 각 장면의 실제 동작을 표로 기록 — 설계 §2-5 「단점(정직) Ctrl-U 는 사람 초안을 지울 수 있다」가 **실제로 성립하는지**(ⓐ 가 거부면 단점이 사라짐 · 통과면 단점 유지).

### M4 마스터 좌석 안 `javis_mission.py status` (진짜 Claude Code)

1. VM 안 cysr 앱으로 첫 기동 → 마스터 좌석 M(진짜 Claude Code · 시험 계정).
2. 기준선: M 좌석 안에서 `vm$ python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_mission.py" status --json` → 기록(새 설치라 「임무 없음」 예상).
3. `rpc` 공통 요청 · 본문 = 짧은 실제 부탁 1문장.
4. 마스터가 받은 뒤 2 를 다시.
5. 큐(기계) 1건: `{"queued":true,"machine_origin":true,"from":"chat-auto",…}`(설계 `chat_send` 계약 표 auto 줄) → 2 를 다시.
- **기대**: 3 뒤 `rc 0`·`source` = 오너 쪽 값 · 5 뒤 임무 값 무변경(기계로 접힘).
- ⚠ 「좌석 안에서」 = 마스터 좌석의 env(`CYS_SURFACE_ID`·`CYS_SOCKET`)로 — 같은 VM 의 다른 셸에서 치면 다른 판정이 나올 수 있다(임무 게이트가 좌석 env 를 읽음). 방법: M 좌석에 `!` 접두 셸 명령 대신 **좌석 env 를 복사한 별도 셸**(`ps eww <M 의 claude pid>` 로 env 를 읽어 같은 값으로)에서 친다 — M 의 대화에 글을 넣지 않기 위해서.
- 되돌림: 없음(VM).

### M5 U25 — 답하는 중에 받은 말

1. M 에 「1부터 200까지 한 줄씩 천천히 세어 줘」(긴 답 유도).
2. 답이 흐르는 중(세션 기록에 assistant 줄이 늘어나는 중)에 `rpc` 공통 요청 · 본문 = `중간 질문: 지금 몇까지 셌어?`.
- **관찰**: 화면(VM 안 `cys read-screen`) — 대기 줄 표시가 생기나 · 답이 끊기나 · 버려지나 / 세션 기록 — 내 말 user 레코드가 언제 생기나(답 끝난 뒤 vs 즉시) · `parentUuid` 가 무엇을 가리키나.
- 판정: 세 꼴(대기·끼어들기·버림) 중 무엇인지 + 화면 표시 글(설계 §5-2 「답하는 중 → 보낸 말 단계」 판정 재료).

### M6 U21 — 둘째 줄 맨 앞 `/`

1. M 이 조용할 때 `rpc` 공통 요청 · 본문 = `안녕\n/clear`(울타리 안 둘째 줄).
- **관찰**: 세션 id 가 바뀌는가(`/clear` 실행 = 새 세션) · 세션 기록의 user 레코드 본문에 `/clear` 글자가 그대로 있는가.
- 판정: 명령 아님(본문으로 남음) = 설계 ⑤ 가정 성립 → 「둘째 줄 `/` 는 막지 않음」 유지 · 실행됨 = 모든 줄 맨 앞 `/` 막기로 바꿔야 함(조각 3 수용 기준 변경 → master 보고).
- ⚠ 시험 계정 VM 좌석에서만. 실행되면 그 좌석 대화가 지워질 뿐(VM).

### M7 U20 — 세션 기록의 꼴 두 가지

- ⓐ 긴 붙여넣기: 본문 5,000자(여러 줄) 원자 제출 1건 → user 레코드 `message.content` 가 원문 전체인가 · 「붙여넣은 글 N줄」 같은 자리표 글인가 · 길이.
- ⓑ 큐 묶음: 같은 발신자로 큐 2건을 연달아 적재(마스터 바쁠 때) → 배달된 한 덩어리의 머리 글(`[큐 다이제스트…]` 꼴 · governance.rs 묶음 배달) · user 레코드 본문 · 마스터 답이 두 건을 각각 다루나.
- 판정: ⓐ 원문 전체면 「전달됨 = 결속 세션 전문 일치」 그대로 · 자리표면 일치 규칙을 「앞 N자 + 길이」 등으로 바꿔야 함(조각 3 설계 보강 → master 보고).

### M8 세션 레코드 `uuid`/`parentUuid`

- M4·M5·M7 의 user 레코드마다 `uuid`·`parentUuid`·`sessionId`·`type` 칸 유무 · `parentUuid` = 바로 앞 레코드 `uuid` 인지(파일 순서 기준).
- 판정: 칸 없음·잇기 깨짐이 하나라도 있으면 「uuid 부모 잇기」를 전달 판정에서 빼고 「전문 일치 + 시각 창」만 쓰는 쪽으로 보고.

### M9 U26 — 세션 id → 파일

- 맥(VM): 데몬 `control.session_detail`/analytics 가 고른 경로와 `vm$ ls ~/.claude*/projects/*/<id>.jsonl` 결과가 같은가 · `CLAUDE_CONFIG_DIR` 로 띄운 좌석이면 그 폴더 쪽인가.
- **(master G4 · 11-17) 윈 절반 = 보류 · 재개 조건 = 조각 10 윈 실기 착수.**
- **윈: 이 계획의 VM 은 맥이라 윈 절반은 따로다** — 윈 샌드박스(또는 윈 VM)에서 같은 절차 · 윈 경로(`%USERPROFILE%\.claude\projects\…`) 확인. 윈 환경 선택 = master 결정(§5 G4).

### M10 R3 — 30초 큐 묶임

1. M 좌석에 원자 제출 1건(시각 T0).
2. 즉시 큐(기계) 1건 적재.
3. 배달 시각 T1 기록(데몬 이벤트 `queue.delivered` — 이름은 cysd 시험 activity_bench_tests.rs:350 · alert_route.rs:4216 에서 확인 · 또는 세션 기록 시각).
- **기대**: T1 − T0 ≥ 30초(`CYS_QUEUE_HUMAN_QUIET_SECS` 기본값 · governance.rs:6595~6600) · 그동안 승계 요청(`start_master` 류)이 「최근 사람 입력」으로 거절되는 꼴(사유 글·코드) 기록.

### M11 V-N1 — 이름 보고자 칸

1. VM 안 좌석이 아닌 셸에서 cmux 마스터와 같은 길로 이름 보고 — 좌석 밖 statusline 보고가 `usage.report_named` 로 가는 분기(src/bin/cys.rs:21836~21840) · cwd = 시험 폴더 · 데몬 받는 쪽 handlers.rs:11029.
2. `rpc usage.named_reporters '{}'` 로 목록 읽기(handlers.rs:11062 · 앱 `usage_named_reporters` 가 부르는 같은 메서드).
- **관찰**: 행에 역할(master) 이 실리는 칸이 있나 · 있으면 이름·꼴.
- 판정: 실림 = 설계 §9-3 「긍정 신호」 판정 가능 · 안 실림 = 「불가 판정 0(늘 가능)」 으로 둔다(설계가 이미 정한 대체).

### M12 R6 — 목록 왕복

- `rpc surface.list` 100회 왕복 시간 p50/p95(VM · 좌석 3·12개 두 장면). 웹뷰 → Tauri 구간은 조각 1 대역 하네스에서 잰다(이 항목 = 데몬 몫만).

---

## 3. 순서 · 예상 소요

- 순서: E1~E5 → M1·M2·M3(대역 · 진짜 Claude 불필요 · 먼저 끝냄) → E4 확인 → M4·M6·M8 → M5 → M7 → M10 → M11 → M12 → 지문 대조(§1-3) → `tart delete`.
- 예상 시간·토큰: **실측 계수 없음 — 이 실측의 첫 실행으로 확보**(master 규칙 「실측 계수만」).

## 4. 결과 기록 양식

항목마다 한 칸: `#`·환경(VM 이름·빌드 sha·Claude Code 판)·친 명령 원문·원 출력(바이트는 `od -c`)·기대·실제·판정(성립/불성립/판정 불가)·설계에 주는 영향(조각 번호). 결과 파일 = 이 문서 옆 `SLICE-0.5-MEASURE-RESULT.md`(실행 때 새로).

## 5. 실행 전 master 결정 필요 (게이트)

| # | 결정 | 권고 | 단점 |
|---|---|---|---|
| G1 | VM = A(`jarvis-clean-vanilla` 복제) 또는 C(`vm-v117-login-base` 복제) | C 에 시험 계정 로그인이 있으면 C · 없으면 A | C 의 바탕 상태가 미확인(확인 1회 비용) |
| G2 | VM 안 빌드 반입·설치(1.1.15 후보 · 시험 전용 서명) | 승인 — VM 밖 영향 0 | 반입 빌드가 이 가지와 같은지 sha 확인 1단계 늘어남 |
| G3 | VM 안 Claude Code 시험 계정 로그인 | master(「로그인·권한 인증 = master」) · 2단계·생체가 실제로 뜨면 그때만 박사님 | 시험 계정 토큰 소모(M4~M9 · 짧은 대화 10여 회) |
| G4 | M9 윈 절반의 환경 | 윈 샌드박스 1회(조각 10 윈 실기와 묶어도 됨) | 묶으면 U26 윈 답이 늦어짐 |

---

## 부록 R. `rpc` 틀 (VM 안 사본 전용 · 이 저장소에 실행 파일로 두지 않음)

```python
# vm 안에서만: python3 rpc.py <method> '<params json>'
import json, os, socket, sys
sock = os.environ["CYS_SOCKET"]                      # VM 데몬 소켓(VM 안 cys identify 로 확인)
tok_path = os.path.join(os.path.dirname(sock), "operator.token")
params = json.loads(sys.argv[2])
if params.get("human") and not params.get("queued") and not params.get("machine_origin"):
    t = open(tok_path).read().strip()
    params["operator_token"] = t; params["owner_token"] = t
s = socket.socket(socket.AF_UNIX); s.connect(sock)
s.sendall((json.dumps({"id": 1, "method": sys.argv[1], "params": params}) + "\n").encode())
print(s.makefile().readline())
```
