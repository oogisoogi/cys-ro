# 윈 실기 묶음 재료(최종판) — cysr 1.1.6 + 설치기 0.3.36 · 박사님 윈 노트북 한 자리

- 최종판: TICKET=v116-cut-close A부 · master#668dddf4(원장 19:20:27 surface:1112 submitted yes) + 개정 master#f703427c(원장 19:33:15 · 【결정필요】1 = B 채택 — 새 설치 길 포함) · 작성 = worker@surface:1112 · 2026-09-25 19:2x~
- 초안: TICKET=v116-integ-5 8단계 · master#0eb6ba6f · worker@surface:1105(커밋 3758bfed) — 초안의 ① 은 절단 **전** CI 아티팩트(`cysr_1.1.5_x64-setup.exe` · 판번 1.1.5 · .sig 없음)였다. 이 최종판은 절단 **뒤** draft 자산으로 바꿨다(아래 ①). 초안 원문은 git 이력(3758bfed)에 그대로 있다.
- 성격: master 가 박사님용 묶음 브리프를 쓰기 위한 **재료**다. 업로드·공유·배포·태그·게시·habitat/ai-jarvis 수정은 이 문서를 만들면서 **하나도 하지 않았다**(읽기·내려받기만 · 받은 파일은 이 좌석 scratchpad 에만 있음).
- 기준: 태그 v1.1.6 = 주석 태그 fa6e8abf → 커밋 **f243e04a**(master C3 18:47 push) · release.yml 태그 런 36120443264 success(18:47~19:15 · master 실측) · draft 릴리스 1개(비공개).
- 표기: 【관측】 = 이 좌석이 도구로 잰 것 · 【판정】 = 그 관측에서 내린 결론 · 【미확인】 = 재지 못한 것 · 【문서】 = 공식 문서 원문 인용 · 신뢰도 = 높음/중/낮음.

---

## ① 1.1.6 설치 파일(윈 x64 NSIS) — draft 릴리스 자산

| 항목 | 값 | 출처 · 신뢰도 |
|---|---|---|
| 릴리스 | `oogisoogi/cys-ro` 의 draft `cysr v1.1.6`(tagName v1.1.6 · isDraft=true · 만든 시각 2026-09-25T09:47:45Z = 18:47 KST) · 페이지 주소 `https://github.com/oogisoogi/cys-ro/releases/tag/untagged-588c290fb3de7caafd77` | `gh release view v1.1.6 --json …` 【관측 19:2x】 높음 |
| 파일 이름 | **`cysr_1.1.6_x64-setup.exe`** | 같은 출력 · 내려받은 파일 【관측】 높음 |
| 크기 | **140,837,194 B**(약 134 MiB) | API `size` = `ls -l` 둘 다 140837194 【관측】 높음 |
| sha256 | **a8ab563b0c7c0db5a5eebdba257a6d31ed1450c4438c380281b48cd61c7e6153** | `shasum -a 256`(내려받은 파일) = API `digest` 글자 일치 【관측】 높음 |
| 판 문자열 | **1.1.6** — 실행 파일 안 버전 정보: `ProductVersion 1.1.6` · `FileVersion 1.1.6` · `ProductName cysr`(UTF-16 문자열 「1.1.6」 2곳 · 「1.1.5」 0곳) | PE 리소스 문자열 판독 【관측】 높음 |
| 실행 파일 종류 | 32비트 PE(machine 0x14c · NSIS 설치기 겉껍질 = 「Nullsoft」 문자열 3곳) | PE 헤더 【관측】 높음 |
| 서명(Authenticode) | **없음** — PE 인증서 표(데이터 디렉터리 4) 위치·크기 0·0 ⇒ Windows 「알 수 없는 게시자」 경고가 뜬다(W8) | PE 헤더 파싱 【관측】 높음 |
| 업데이터 서명(.sig) | **있음** — `cysr_1.1.6_x64-setup.exe.sig` 412 B · sha256 c91ee1a0e924567eff84525e95643d6c2bb3ff2a04025133eb76eadf008420df · 앱에 박힌 공개키(`src-tauri/tauri.conf.json` plugins.updater.pubkey · 키 ID 831ca9172204e93e)로 **파일 서명·전역 서명 둘 다 검증 통과**(minisign ED = BLAKE2b-512 선해시 · 파이썬 cryptography Ed25519) | 【관측】 높음 |
| latest.json(draft) | 1,804 B · `version 1.1.6` · `build_id f243e04a8ede.20260925T0838Z` · 행 = `windows-x86_64` · `windows-x86_64-nsis` 둘뿐(맥 행 없음 · notes 「이 태그는 윈도우 단독 배포입니다 — macOS 자산은 포함되지 않습니다」) · 두 행의 signature = .sig 파일 전문과 글자 일치(412자) · url = `…/releases/download/v1.1.6/cysr_1.1.6_x64-setup.exe` | 【관측】 높음 |
| 같은 draft 의 나머지 자산 | `pack-manifest.json` 53,666 B · `pack-manifest.json.minisig` 303 B · `pack.tar.gz` 2,970,291 B(맥 자산은 B부에서 로컬 빌드 후 올릴 예정 · 지금 없음) | `gh release view` 【관측】 높음 |
| 받는 법(master·좌석) | `gh release download v1.1.6 -R oogisoogi/cys-ro -p 'cysr_1.1.6_x64-setup.exe'`(저장 = scratchpad · 공유·업로드 0) — 이 좌석에서 22.1초 | 【관측】 높음 |
| 로그인 없이 받기 | **안 된다** — 로그인 없는 `curl` 로 draft 자산 주소(`…/download/untagged-588c…/…exe.sig`) · 태그 주소(`…/download/v1.1.6/…exe.sig`) · draft 페이지 셋 다 **HTTP 404** | 【관측 19:2x】 높음 |

⚠ 【판정】 **latest.json 의 url 은 `…/download/v1.1.6/…` 인데, draft 인 동안 이 주소는 로그인 없이 404 다.** 발행(release-publish) 뒤에야 받아지는 주소다 — 그래서 발행 전에는 앱 안 Update 로 이 파일을 받을 수 없다(② 판정과 같은 결론 · 이번엔 실물로 확인).

---

## ② 박사님 윈 노트북으로 옮기는 방법 — 2안 + 권고

### ⒜ 노트북 브라우저에서 GitHub 로그인 → draft 릴리스 페이지에서 받기
- 【문서】 GitHub 저장소 역할 표(`docs.github.com/en/organizations/.../repository-roles-for-an-organization` · 표 머리 「Repository action | Read | Triage | Write | Maintain | Admin」): **「View draft releases」 = Read ✗ · Triage ✗ · Write ✓ · Maintain ✓ · Admin ✓**. 신뢰도 높음(원문 표를 받아 grep).
- 【문서】 REST 문서(`docs.github.com/en/rest/releases/releases`): 「Information about published releases are available to everyone. Only users with push access will receive listings for draft releases.」 신뢰도 높음.
- 【문서】 개인 계정 저장소 권한 문서(`…/permission-levels-for-a-personal-account-repository`): 「Repositories owned by personal accounts have a single owner who has full control of the repository.」 — `oogisoogi/cys-ro` 는 개인 계정 oogisoogi 소유이고 박사님 계정이 그 소유자다 ⇒ 로그인하면 draft 가 보인다.
- 【미확인】 공식 문서 원문에 「draft 자산을 **내려받을 수 있다**」는 문장은 찾지 못했다(「보인다(view)」·「목록에 나온다(listings)」까지만 원문). 다만 같은 계정 권한으로 `gh release download` 가 draft 자산을 받았다【관측】 — 브라우저 로그인 세션도 같은 권한이라 받아질 것으로 본다(신뢰도 중).
- 박사님 손: ① 노트북 브라우저에서 github.com 로그인(새 기기면 2단계 인증 1회) ② `https://github.com/oogisoogi/cys-ro/releases` 열기(목록 맨 위 「Draft」 표시 `cysr v1.1.6`) ③ Assets 의 `cysr_1.1.6_x64-setup.exe` 누르기 ④ (선택) PowerShell 에서 `Get-FileHash "$HOME\Downloads\cysr_1.1.6_x64-setup.exe" -Algorithm SHA256` 로 위 sha256 대조 = **3~4회**(로그인 상태면 2~3회).
- ⚠ draft 페이지 주소의 `untagged-588c…` 는 draft 동안만 쓰이는 임시 이름이다 — 박사님께는 페이지 주소보다 **Releases 목록 주소**를 드리는 편이 안전하다(【판정】 · 이름이 바뀌어도 목록은 그대로).
- ⚠ 브라우저 다운로드 보호: Edge SmartScreen 이 서명 없는 exe 내려받기 자체에 「흔히 다운로드되지 않는 파일」 경고를 띄울 수 있다 【미확인 · 박사님 기기에서】 — 뜨면 「…→ 유지」.

### ⒝ master 가 받아 둔 파일을 박사님 구글 드라이브로 옮기고 노트북에서 받아 해시 대조
- 경로: master 가 `gh release download` 로 받은 파일을 박사님 구글 드라이브(맥의 드라이브 동기 폴더 또는 웹 업로드)에 올림 → 노트북 브라우저에서 드라이브 열어 내려받기 → `Get-FileHash` 대조.
- 대용량 exe 경고 — 사실 확인 결과:
  - 【미확인 · 공식 문서】 구글 드라이브 공식 도움말 「파일 다운로드」(support.google.com/drive/answer/2423534)에는 바이러스 검사 크기 한도 문장이 **없다**(원문에 있는 것은 「의심스러운 파일을 받으려 하면 경고 메시지가 나올 수 있다」 한 줄뿐 · WebFetch 판독).
  - 【커뮤니티 · 신뢰도 중】 구글 드라이브 도움말 커뮤니티 글 제목들에 경고 문구가 그대로 있다: 「JXII-8.0.exe (1.4G) is too large for Google to scan for viruses. Would you still like to download this file」(support.google.com/drive/thread/4022435) · 「Zip (50M) is too large for Google to scan for viruses」(…/thread/266393368) · 「Virus scanning files in Google Drive larger than 100mb」(…/thread/225474267). ⇒ 134 MiB exe 는 「너무 커서 바이러스 검사를 못 함 → 그래도 받겠습니까」 창이 뜰 가능성이 높다 — 「그래도 다운로드」 1회가 는다. 정확한 한도 값(50MB·100MB 등)은 공식 확인 불가.
- 박사님 손: ① 노트북 브라우저에서 드라이브 열기(로그인 상태 가정) ② 파일 찾아 다운로드 ③ 「그래도 다운로드」(대용량 경고가 뜨면) ④ `Get-FileHash` 대조(**필수** — 사본을 한 번 더 거쳤으므로) = **4회**.
- 단점: 파일을 한 번 더 옮기므로 중간 사본이 생긴다(드라이브에 남음 · 실기 뒤 지워야 함) · 올리는 행위 = master 게이트(박사님 개인 드라이브라 외부 공개는 아님).

### 권고 = ⒜ (단점 병기)
- 이유: ⑴ 파일이 **GitHub 의 원본 자산에서 바로** 오므로 중간 사본이 없다(sha256 이 API digest 와 같은 원본) ⑵ master 준비 손이 0(업로드 없음) ⑶ 손 횟수가 ⒝ 보다 1회 적다.
- 단점: 노트북에 GitHub 로그인이 없으면 로그인(+2단계 인증)이 첫 손이 된다 · 공식 문서가 「내려받기」까지는 명시하지 않는다(신뢰도 중 — 막히면 ⒝ 로 넘어간다).
- 폴백: ⒜ 에서 404·권한 오류가 나면 ⒝.

---

## ③ 윈 점검표(1.1.6 실기) — 박사님이 실제로 할 순서

순서 전제 = master#f703427c 판정(B 채택): ㉮ 노트북에 **지금 깔려 있는 1.1.5** 위에 draft setup.exe 를 덮어 설치(W8·W9) → W1~W12 → ㉯ 설치기 0.3.36 재설치(스테이징)로 1.1.6 을 **새로** 깐다(④·⑤). 그래서 **W8·W9 가 맨 앞**이고, 나머지는 1.1.6 이 선 뒤에 본다. ⚠ 노트북에 지금 1.1.5 가 깔려 있는지는 【미확인】(지난 윈 실기 = 09-23 1.1.3→1.1.5 덮어 설치 기록 · SESSION_STATE 09-23 01:4x) — 1.1.5 가 아니면 W9 는 「그 판 → 1.1.6」 덮어 설치로 읽는다.

| # | 무엇을 | 확인 방법 | 기대 | 근거 |
|---|---|---|---|---|
| W8 | (윈만) 설치 파일 = 서명 없음 · SmartScreen | ① 의 setup.exe 더블클릭 → 첫 화면 | 「Windows의 PC 보호」 → 「추가 정보 → 실행」(손 1 · 1.1.1 윈 실기 선례와 같음) | ① Authenticode 없음 【관측】 · SESSION_STATE 1.1.1 윈 실기 1차 「손 1 = SmartScreen 추가 정보→실행」 |
| W9 | (윈만) 1.1.5 위 덮어 설치 — 함대가 떠 있는 채로 | 지금 노트북에 깔린 1.1.5 함대(master·cso·worker1)를 켠 채 setup.exe 진행 → 끝나면 앱 재시작 안내대로 | ⑴ 설치 뒤 판번 1.1.6(PowerShell `cys --version` → `cys 1.1.6` · 이 명령은 맥 설치본에서 `cys 1.1.5` 를 찍는 것 실측) ⑵ 좌석이 되살아남 ⑶ **팩 병합 대기 `.new` 파일 0개** — PowerShell `Get-ChildItem $HOME\.cys\pack -Recurse -Filter *.new` 결과 없음(1.1.3→1.1.5 덮어 설치 때 `.new` 4개 발행 차단 결함의 재발 점검) | 메모리 tauri-nsis-update-mode-skips-uninstaller(NSIS 업데이트 모드는 옛 제거기를 안 불러 데몬·세션을 끊지 않는다) · SESSION_STATE 09-23 01:4x 「윈 1.1.3→1.1.5 덮어쓰기 = `.new` 4」 · HANDOFF-v116-integ.md §14(:221) 「1.1.5 D1 RefreshUser」 |
| W1 | 창 머리 번호 + `#N` 해석 1회 | PowerShell 에서 `cys list` → 창 머리 숫자와 5번째 칸 `no=N` 을 **같은 시각 캡처 1장**으로 대조 → `cys send '--surface=#<산 번호>' hello` | 창 머리 숫자 = `no=` 값 · stderr `#N → surface:N @<소켓 이름>` | HANDOFF §19-2 #5 · cys.rs:1463-1476(resolve_surface_arg) |
|  | ⚠ | PowerShell 에서 `#` 이 주석으로 먹히는지 【미확인】 — 작은따옴표로 감싸 넘길 것(`'--surface=#5'`) | | 맥 zsh 함정 §19-2 #5 ⚠ 의 윈 판 |
| W4 | 좌열 기본 폭 · 노트북 90칸 | 1.1.6 첫 기동 직후 master 칸 열 수(칸 안 `mode con` 또는 창 머리) | 좌열 = 창의 25%(상한 50%) · 노트북 화면에서 master 약 90칸(창이 좁으면 상한 50% 에서 멈춤) | 박사님 결정 14:5x · §22 · HANDOFF-v2 「좌열 기본 폭에 칸 여백」 |
| W3 | master:cso 위아래 4:1 | 본부 좌열 | 4:1 유지 | 박사님 결정 14:1x |
| W2 | 창 정렬 v2 — 워커 좌우 균등 | 셸 칸을 윈 단축키(Ctrl 계열 · 【미확인】 키 이름)로 2~3칸 → 칸마다 폭 | 워커 기둥 폭 서로 같음 · 사람이 위아래로 나눈 칸은 그대로 | HANDOFF-v2(편입 가지) · §22 |
| W5 | 팔레트 「세로 분할」 복원 | 명령 팔레트에 「분할」 | 「가로 분할」·「세로 분할」 둘 다 | HANDOFF-v2 바꾼 시험 7 |
| W6 | 제안 글 끄기(윈 경로) | master 에 한 번 말 걸고 답 뒤 입력칸 | 회색 제안 글 0 — 윈에서 좌석 env 가 닿는 유일한 경로 = `launch_create_env_pairs` | §17-2 6 · §17-8 ④ |
| W7 | 좌석 effort high | 좌석 claude 에서 `/effort` 또는 세션 기록 `"effort":"high"` | high | §19-2 #2 |
| W11 | (윈만) T-PACK 묘비 경로 | 창 하나 닫기(부서 없으면 본부 워커) → W10 의 재실행 | 닫은 역할 다시 안 섬 · 윈 묘비 경로 = T-PACK Fable M-4 수리(윈을 None 으로 두면 되살림 없음 → 수리) | javis_formation.py:1094 |
| W10 | (윈만) phoenix 복원 | 앱 종료·재실행 | 좌석 복원 · 윈 T5 스모크(CI windows-build 초록)와 같은 흐름 · 3차 CI 에서 「③ taskkill rc0」 플레이크 1회(§17-9 · 재실행 초록) | §17-9 |
| W12 | 1.1.6 공지와 어긋남 점검 | §17-5 공지 문안을 화면과 한 줄씩 대조 | ⑴ 「'눌러서 재시작' 알림」 — 앱 안 Update 를 거칠 때만(발행 뒤 · 이번 실기 범위 밖) ⑵ 「머리줄 업데이트 → 다시 켜기」 는 **맥 전용**이라 문안이 「맥에서는」 으로 한정돼 있다 → 윈에서 안 보여도 정상 ⑶ 복원 카드 세 절 · ⑷ 창 번호 1~999 · ⑸ 게이지 흐림 없음 · ⑹ effort high ⑺ 제안 글 0 — ⑶~⑺ 은 윈에서도 보여야 함 | §16 · §17-5 |
|  | ⚠ 공지 보완 후보 | 창 정렬 v2(§22)는 §17-5 초안에 **아직 없다** → 「창을 새로 열거나 닫으면 워커 창 폭이 자동으로 고르게 맞춰지고, 왼쪽 master·cso 열은 사용자가 정한 폭을 유지합니다」 류 1줄 추가 후보(문안 = master) · 판번은 이제 1.1.6 으로 화면과 공지가 맞는다(초안의 「1.1.5 표기」 어긋남은 해소) | | §17-5 · §22 · ① 판 문자열 1.1.6 【관측】 |

- 순서 이유(【판정】): W8·W9 = 설치 순간에만 볼 수 있다 → 맨 앞. W1·W4·W3 = 설치 직후 첫 화면에서 바로 보인다. W2·W5 = 창을 늘려야 보인다. W6·W7 = master 에 한 번 말을 걸어야 보인다. W11 → W10 = 창을 닫은 뒤 앱을 재실행해야 둘이 한 번에 보인다(닫기 먼저 · 재실행 뒤 묘비·복원 동시 확인). W12 = 앞의 관측을 공지와 대조하는 정리 단계라 마지막.
- VM 2차에서 **윈으로만** 볼 수 있는 항목: W8~W11(설치 파일 서명·덮어 설치·윈 phoenix·윈 묘비 경로) + W6 의 윈 env 경로.

---

## ④ 설치기 0.3.36 윈 실기

### 체크리스트 원문
**r3 원문 3줄 그대로**(인박스 2026-09-25T09:22:24+0900 · worker-46@surface:1094 【확인요청】 installer-0336 r3 · 「■ 윈 체크리스트(실기 때)」 절):

```
■ 윈 체크리스트(실기 때)
- PS 5.1 -File 사람 설치: [1/10] 고지 뒤 start·info 서버 도착(고지 문이 사람 설치를 막지 않음) · 고지 전 전송 0.
- 지난 실행이 끊긴 기기에서 재실행: [1/10] 앞 증거·그림 0 · 뒤는 정상.
- JARVIS_HELP_API_URL 없음 = 도움 보고 종전 주소 · 막힘 재현 시 보고 번호·폰 주소 표시.
```

**r5 권고 2줄**(원문 두 곳):
- habitat `docs/install-master/HANDOFF-installer-0336.md` §16 마지막 줄(커밋 dce10a5 · r5): 「윈 실기 체크리스트 2줄(PS 5.1 · 본부 자비스 입력칸 회색 제안 글 없음 · /effort 표시 high) = master 가 윈 실기 묶음에 넣음.」
- 인박스 2026-09-25T18:36:23+0900 worker-installer@surface:1108 【확인요청】 installer-0336-r4 「■ 4군 점검」 윈 설치파일 줄: 「미실측 = PS 5.1 실물(윈 실기 체크리스트에 「본부 자비스 입력칸 회색 제안 글 없음 · /effort 가 Not applied(high)」 두 줄 넣기 권고).」

체크리스트에 넣을 2줄(위 두 원문을 체크 항목으로 옮김 · 뜻 변경 없음):
```
- PS 5.1(Windows PowerShell) 설치로 깨운 본부 자비스: 한 번 말을 건 뒤 입력칸에 회색 제안 글 없음.
- 같은 자리에서 /effort: 표시가 high(Not applied(high) 꼴 포함).
```
- 두 줄의 근거(설치기 쪽): r4 커밋 aa89583 = wake.ps1 에 `CLAUDE_CODE_EFFORT_LEVEL='high'` · `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION='false'`(환경 키 없을 때만) · r5 커밋 2513925 = 창 폴백 `& $fallbackExe` 앞에도 두 값. 맥 pwsh 7 로는 실측했고 **PS 5.1 실물은 미실측**(1108 r4 보고 「9칸 중 8칸 실측 · PS 5.1 실물 1칸 미실측」) → 이 2줄이 그 1칸을 닫는다.
- ⚠ 이 2줄은 **설치기가 깨운 본부 자비스(wake.ps1 경로)** 를 본다. ③ W6·W7 은 **cys 앱이 띄우는 좌석(launch_create_env_pairs 경로)** 을 본다 — 같은 모양의 확인이지만 다른 경로라 **둘 다** 본다(㉮ 1.1.6 덮어 설치 뒤 W6·W7, ㉯ 새 설치 뒤 이 2줄).

### ㉯ 새 설치 — 권고 = 「앱까지 지우기 → 설치」 두 줄 · 대안 = 재설치 한 줄(📌 박사님 결정 사항 · 손 5~6회 차이 · master#6344c5e2)
【판정 · 신뢰도 높음(코드 원문)】 master#f703427c 의 「설치기 재설치(제거 뒤 새 설치)」 를 **재설치 한 줄(reinstall.ps1)** 로 하면 앱은 **지워지지 않는다**:
- habitat dce10a5 `install-master/reinstall.ps1:94` 원문 `powershell -ExecutionPolicy Bypass -File $ResetFile -KeepApp -Yes` · `:90` 주석 「-KeepApp : cys 프로그램은 지우지 않는다(설치 도우미가 [6/10] 에서 이미 깔린 프로그램을 그대로 쓴다).」
- 그 뒤 설치기 [5/10] 은 설치 자리의 표지(`jarvis-cys-pin.json`)를 본다(`bootstrap.ps1:1152-1164` Get-CysContentState). ㉮ 에서 사람이 setup.exe 로 깐 1.1.6 에는 이번 핀 지문의 표지가 없으므로(마지막 표지 = 지난 설치기의 1.1.5 핀 지문 → 'pin-changed' 또는 'no-stamp' · 【추정 · 노트북 실물 미확인】) 설치기는 임시 프리릴리스에서 1.1.6 을 다시 받아 **덮어** 깐다 — 받기·핀·덮어 설치는 재지만 「앱이 없는 기기에 처음 까는 길」은 안 잰다.
- ⇒ 워크숍 참가자의 첫 설치 길을 재려면 **① 지우기 한 줄(reset-clean · -KeepApp 없음)** 로 앱까지 지운 뒤 **② 설치 한 줄(bootstrap)** 을 돌린다. reset-clean 은 앱을 직접 지우지 않고 **윈도우 설정 앱에서 지우도록 안내**한다(`reset-clean.ps1:30-34` 원문 「cys 프로그램 자체는 이 스크립트가 지우지 않는다 — 윈도우 설정 앱에서 지우시게 안내한다.」 · 까닭 = 백신이 제거 프로그램 실행을 막고 PowerShell 을 종료시킨 실사고 2026-09-05). 로그인은 기본으로 남긴다(`:21` 「★로그인은 기본으로 남긴다」) → ② 에서 로그인 카드는 안 뜬다(로그아웃 갈래는 이번 범위 밖).

**① 지우기 한 줄**(명령 프롬프트 또는 PowerShell · 원문 = `reset-clean.ps1:15` 정본의 주소만 `/install/next/`):
```
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Remove-Item ([Environment]::GetFolderPath('UserProfile')+'\reset-clean.ps1') -ErrorAction SilentlyContinue; irm https://jarvis.godmeyou.kr/install/next/reset-clean.ps1 -OutFile ([Environment]::GetFolderPath('UserProfile')+'\reset-clean.ps1') -ErrorAction Stop; powershell -ExecutionPolicy Bypass -File ([Environment]::GetFolderPath('UserProfile')+'\reset-clean.ps1') } catch { Write-Host '설치 파일을 받지 못했습니다. 인터넷 연결을 확인하신 뒤 이 줄을 다시 붙여 넣어 주십시오.'; exit 1 }"
```
- 박사님이 만나는 물음(원문 `reset-clean.ps1` Read-Host 줄): `:1529` 「계속하려면 「지웁니다」 라고 입력해 주십시오」 → 설정 앱에서 cysr 제거 → `:1259` 「제거를 마치셨으면 Enter 를 눌러 주십시오」 → `:1300` 「이 폴더를 지웁니다. 계속하시려면 Enter …」 · 경우에 따라 `:1523`·`:1549` = 손 약 5~6회(입력 1 · 설정 앱 제거 2~3 · Enter 2).

**② 설치 한 줄**(명령 프롬프트 또는 PowerShell · 원문 = `bootstrap.ps1:941` 정본의 주소만 `/install/next/`):

```
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Remove-Item ([Environment]::GetFolderPath('UserProfile')+'\install-jarvis.ps1') -ErrorAction SilentlyContinue; irm https://jarvis.godmeyou.kr/install/next/bootstrap.ps1 -OutFile ([Environment]::GetFolderPath('UserProfile')+'\install-jarvis.ps1') -ErrorAction Stop; powershell -ExecutionPolicy Bypass -File ([Environment]::GetFolderPath('UserProfile')+'\install-jarvis.ps1') } catch { Write-Host '설치 파일을 받지 못했습니다. 인터넷 연결을 확인하신 뒤 이 줄을 다시 붙여 넣어 주십시오.'; exit 1 }"
```
- 근거: ⑴ 정본 한 줄 = habitat fix/installer-0336(dce10a5) `install-master/bootstrap.ps1:941` 【관측】(라이브 `/install/bootstrap.ps1` 0.3.35 도 같은 try/catch 꼴 2곳 【관측】) ⑵ 스테이징 경로 = 메모리 `~/.claude/projects/-Users-oogisoogi-axdev/memory/installer-field-test-staging-path.md` 원문: 「bootstrap.ps1 단독은 형제 파일을 안 받으므로 `next/bootstrap.ps1` 한 줄이면 된다.」 ⑶ 옛 꼴(`irm …; powershell -File …`)을 쓰지 않는 이유 = 메모리 `windows-oneliner-semicolon-runs-after-failed-download`: 「받기 실패(-ErrorAction Stop 포함)에도 ; 뒤가 돌아 옛 파일을 실행한다 — $ 없는 try/catch + 선삭제가 정본」 — 이 노트북은 지난 실기의 `install-jarvis.ps1` 이 남아 있을 수 있어 특히 해당.
- 「PS 5.1 -File 사람 설치」(r3 1줄째) = 위 한 줄 안쪽의 `powershell -ExecutionPolicy Bypass -File` 이 Windows PowerShell 5.1 로 돈다(윈 기본 `powershell` = 5.1).
- 「지난 실행이 끊긴 기기에서 재실행」(r3 2줄째): ② 를 한 번 돌리다 **[3/10] 이후 아무 곳에서 창을 닫고**(Ctrl-C 또는 창 닫기) ② 를 다시 붙여 넣는다 = 박사님 손 +1. 【판정】 한 자리에서 보려면 이 순서(끊기 → 재실행)여야 한다. 끊긴 뒤 재실행은 이미 받은 1.1.6 을 다시 쓸 수 있다(표지 'match' 면 [5/10] 건너뜀 · `bootstrap.ps1:3142` 원문 「같은 판(v$CysVersion)의 cys 가 이미 설치돼 있습니다 (지문 확인) — 받지 않고 건너뜁니다.」) — ⚠ 끊는 자리가 [6/10](설치) **앞**이면 새 설치 길이 재실행 쪽에서 이어지고, **뒤**면 재실행은 설치를 건너뛴다. **새 설치 화면을 온전히 보려면 [3/10]~[4/10] 에서 끊는다**(【판정】 · 단계 번호 = 설치기 화면 표기).
- 새 설치에서 확인할 첫 화면(master 지시 · 1.1.1 윈 실기 합격 기록과 같은 축 · SESSION_STATE 09-21 14:2x 원문 「함대 3 = 43 jarvis·44 cso·45 worker1 · 10/10 rc=0 · 9/10 wake:cys-seat · awaken:auto·master/child-verified」): ⑴ 머리글 「cysr 1.1.6 · 설치 도우미 0.3.36」(`bootstrap.ps1:128-129` 주석 「화면 머리글은 이 값으로 「<이름> <판> · 설치 도우미 <설치기 판>」」) ⑵ [5/10] 이 임시 프리릴리스에서 받음 ⑶ 10/10 끝 ⑷ **창 3개**(master·cso·worker1 — 1.1.x 자리 제목 규칙 = 메모리 cysr-seat-title-is-role-not-jarvis 「총괄 자리는 jarvis 가 아니라 master」) ⑸ **본부 각성**(본부 자비스가 첫 인사로 깨어남) ⑹ r5 2줄(회색 제안 글 없음 · `/effort` high).
- 로그아웃 갈래를 볼 필요가 있으면: 메모리 installer-field-test-staging-path 「①지우기가 로그인을 기본으로 남겨 [3/10] 카드 갈래가 안 돈다 → `Remove-Item ~\.claude\.credentials.json` 뒤 `next/bootstrap.ps1` 재실행으로 진입」 — 이번 체크리스트에는 없는 항목이라 **기본은 하지 않음**(master 판단).
- **대안(📌 박사님 결정 사항) = 재설치 한 줄** — PowerShell 창에서(명령 프롬프트는 `$env:` 를 못 읽는다):
```
$env:JARVIS_BASE_URL='https://jarvis.godmeyou.kr/install/next'; powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Remove-Item ([Environment]::GetFolderPath('UserProfile')+'\reinstall-jarvis.ps1') -ErrorAction SilentlyContinue; irm https://jarvis.godmeyou.kr/install/next/reinstall.ps1 -OutFile ([Environment]::GetFolderPath('UserProfile')+'\reinstall-jarvis.ps1') -ErrorAction Stop; powershell -ExecutionPolicy Bypass -File ([Environment]::GetFolderPath('UserProfile')+'\reinstall-jarvis.ps1') } catch { Write-Host '설치 파일을 받지 못했습니다. 인터넷 연결을 확인하신 뒤 이 줄을 다시 붙여 넣어 주십시오.'; exit 1 }"
```
  근거: `reinstall.ps1:35` 정본의 주소만 `/install/next/` + 앞에 `$env:JARVIS_BASE_URL` 1문장(`reinstall.ps1:64` 원문 `$Base = if ($env:JARVIS_BASE_URL) { $env:JARVIS_BASE_URL } else { 'https://jarvis.godmeyou.kr/install' }` · 메모리 installer-field-test-staging-path 의 한 줄 꼴). 장점 = 박사님 손이 두 줄 방식보다 약 5~6회 적다(「지웁니다」·설정 앱 제거·Enter 없음 · `-Yes`). 단점 = 앱을 남기므로(-KeepApp) **새 설치 길은 재지 않는다** — ㉮ 와 같은 덮어 설치를 받기 경로(임시 프리릴리스)만 바꿔 한 번 더 재는 셈이다. 끊기(r3 2줄째)는 같은 한 줄 재실행으로 본다.

### 선행 조건 — 누가(master 게이트) · 명령 · 되돌리기
| # | 선행 조건 | 누가 | 명령(원문 출처) | 되돌리기 |
|---|---|---|---|---|
| P1 | 서버·고지 = ai-jarvis `feat/hw-model-0336` **f1b1ccf4** 배포(설치 전용 사이트 Worker `jarvis-install-site` — 고지 페이지 `web-install/src/page.ts` + 수신 `web-install/src/telemetry.ts:130` ENV_TEXT_KEYS 에 hw_model·mem_gb·disk_free_gb) · 발행 순서 원문 「서버·고지 먼저 → 설치기」(master#70a20b94) | master 게이트 | `site/hub` 를 f1b1ccf4 로 빨리감기(원격 site/hub ⊂ feat · 앞선 6커밋 · 뒤진 0 【관측】) → `bash web-install/deploy.sh`(드라이런) → `bash web-install/deploy.sh --go`(원문 = deploy.sh 머리말 「쓰는 법」) | 되돌림 커밋(`git revert`) 뒤 `deploy.sh --go` — deploy.sh G3 「마지막으로 배포한 커밋이 지금 HEAD 의 조상이 아니면 거부」 때문에 **옛 커밋 재배포는 거부된다**(머리말 원문) · 이 서버 변경은 모르는 키를 「버린다(거부 아님)」(installer-0336 브리프 D6-c · telemetry.ts:225-231) 라 옛 설치기에 무해 |
| P2 | 설치기 최종 해시 확정(1108 r5 뒤 · P7 r6 커밋 뒤) | master(1108 【확인요청】 ACCEPT) | 【빈칸】 — 지금 habitat fix/installer-0336 로컬 HEAD = **dce10a5**(r5 · 18:53 커밋) · 원격 fix/installer-0336 = 13a2392(r3) 【관측 19:2x】 · P7(핀 1.1.6) 이 r6 커밋을 하나 더 얹으므로 **스테이징에 올릴 해시 = r6 머리** | 해당 없음(판정 단계) |
| P3 | 스테이징 게시 = `/install/next/` 에 P2 해시의 ps1 3파일(단 bootstrap.ps1 = P8 치환본) | master 게이트 | ai-jarvis site/hub 에서 `mkdir -p site/install/next && cp <habitat P2 해시 트리>/install-master/{bootstrap,reinstall,reset-clean}.ps1 site/install/next/` → (P8 치환) → 커밋 → `bash web/build-web.sh && (cd web && unset NODE_OPTIONS && npx wrangler deploy --config /Users/oogisoogi/axdev/ai-jarvis/web/wrangler.jsonc)`(배포 줄 원문 = `~/axdev/master/installer-golive.sh` 5단계 · 스테이징 선례 커밋 = ai-jarvis 26e442a·68f5097·956aeb4·fe5d8bf) · 게시 뒤 `curl -H 'Cache-Control: no-cache'` 로 next/ sha 3/3 대조(메모리 원문: 「첫 curl 이 엣지 HIT 로 구판을 줄 수 있으니 20초 뒤 no-cache 재측」) | `rm -rf site/install/next` 커밋 → 같은 배포 줄 → `next/bootstrap.ps1` **404** 실측(메모리 원문 「실기 통과 뒤 릴리스 커밋에서 next/ 삭제(임시 경로 잔존 금지 · 404 실측)」 · golive.sh 4단계도 같은 삭제) |
| P4 | 라이브 설치기는 그대로(**라이브 핀 1.1.5 · 0.3.35 무접촉**) — 핀 1.1.6 은 스테이징(next/)에만 선다 | master(확인만) | 확인: 라이브 `/install/bootstrap.ps1:130` `$CysVersion = '1.1.5'` · InstallerVersion 0.3.35 【관측 19:2x】 · 스테이징 쪽 핀 = P7 · 주소 = P8 | 해당 없음(바꾸지 않음) |
| P5 | 라이브 무접촉 확인 | master | 게시 전후 `/install/bootstrap.ps1` sha 동일 · `/install/next/bootstrap.ps1` 게시 전 404 【관측 19:2x】 | — |
| P6 | jarvis-install 임시 프리릴리스 `wintest-v1.1.6-<날짜>` · 자산 = draft 의 `cysr_1.1.6_x64-setup.exe`(+ `.sig`) **그대로** | master 게이트(공개 업로드 · 실기 뒤 삭제) | **선례 생성 명령 원문 = 【미확인】**(인박스·SESSION_STATE·TODO·브리프에서 `gh release create wintest…` 줄을 못 찾음 · 1.1.1 은 결과만 기록: SESSION_STATE 09-21 13:5x 「임시 호스트 jarvis-install 프리릴리스 `wintest-v1.1.1-20260921`(exe 140,416,627 B + .sig · URL 200)」). 선례의 **속성**은 실측: `wintest-v1.1.5-20260923` = prerelease true · draft false · target main · 제목 「wintest 1.1.5 (임시 · 윈 실기용 · 실기 뒤 삭제)」 · 본문 「윈 실기용 임시 호스트 · 발행 뒤 삭제」 · 자산 bootstrap.ps1·exe·.sig 【`gh api …/releases` 관측】. 자산 교체 선례 원문 = 인박스 09-23 18:50:15 worker@987 ⑨ `gh release upload wintest-v1.1.5-20260923 -R oogisoogi/jarvis-install <새 exe> <새 sig> --clobber`. 참고(선례 아님 · 도구 도움말 실측): `gh release create` 에 `-p/--prerelease` · `-t/--title` · `-n/--notes` · `--target` 이 있다(gh 2.87.3 `--help`). 프리릴리스는 「Latest」 가 되지 않는다 — 【문서】 REST 원문 「Drafts and prereleases cannot be set as latest.」 · 실행 전 확인 = ⑴ `gh release view wintest-v1.1.6-<날짜> -R oogisoogi/jarvis-install` 가 「release not found」(같은 이름 없음) ⑵ 올릴 파일 `shasum -a 256 cysr_1.1.6_x64-setup.exe` = a8ab563b…6153 · `.sig` = c91ee1a0… · 크기 140,837,194 ⑶ `-R` 대상이 jarvis-install 인지(cys-ro 아님) · 명령(도구 도움말 실측 꼴 · 선례 아님) = `gh release create wintest-v1.1.6-<날짜> -R oogisoogi/jarvis-install --prerelease --target main -t 'wintest 1.1.6 (임시 · 윈 실기용 · 실기 뒤 삭제)' -n '윈 실기용 임시 호스트 · 발행 뒤 삭제' cysr_1.1.6_x64-setup.exe cysr_1.1.6_x64-setup.exe.sig`(제목·본문·target = wintest-v1.1.5 실측 속성과 같은 꼴) · 실행 뒤 확인 = 자산 주소 로그인 없는 `curl -sIL` 200 · 크기 140,837,194 · sha256 a8ab563b… | 삭제 — 명령 원문 【미확인】(선례 삭제 기록 없음 · P9 참조) · 도구 도움말 실측: `gh release delete <tag> --yes --cleanup-tag`(태그까지 삭제) · 실행 전 확인 = `gh release view <tag> -R oogisoogi/jarvis-install --json tagName,isPrerelease,name` 이 prerelease true · 제목 「wintest 1.1.6 …」 인지 |
| P7 | 설치기 핀 1.1.6 올림 = 설치기 좌석 **r6 몫**(habitat 커밋) | master 발주 → 1108(또는 설치기 좌석) | 고치는 곳 = `bootstrap.ps1` 「릴리스 핀 자리」 블록뿐(`:127` 원문 「다음 판 … 으로 올릴 때 고치는 곳은 **이 블록뿐**이다: $CysDisplayName · $CysVersion · $CysWinFile(자산 이름이 바뀌면) · $CysWinBytes · $CysWinSha256」). **윈 값(지금 실측)** = `$CysVersion '1.1.6'` · `$CysWinFile` 그대로(`"cysr_${CysVersion}_x64-setup.exe"` → 풀면 `cysr_1.1.6_x64-setup.exe` = draft 자산 이름 글자 일치) · `$CysWinBytes 140837194` · `$CysWinSha256 'a8ab563b0c7c0db5a5eebdba257a6d31ed1450c4438c380281b48cd61c7e6153'`(① 표 · API digest·내려받은 실물 2/3 일치 · ⚠핀 주석의 정본 출처 「릴리스 SHA256SUMS.txt」 는 **아직 없다** — B부 postprocess 뒤 3/3 대조) · **맥 값 = B부 산출 뒤**(zip 이름·크기·sha256·CDHash·build_id). ⚠ `tests/win-pin-release.sh` 는 발행 전 [릴리스] 항이 404 로 적색(1.1.5 선례: 인박스 09-23 14:53:59 worker@962 「④ [전환] 맥/윈 핀 = 릴리스 실측 → 공개 URL SHA256SUMS HTTP 404 (드래프트라 공개 다운로드 불가)」) | r6 커밋 되돌림(가역 · 로컬) |
| P8 | next/bootstrap.ps1 의 `$CysDownloadDir` **1줄만** 임시 프리릴리스 주소로 | master(P3 과 함께) | 선례 원문 ⑴ 인박스 09-23 14:53:59 worker@962 「wintest 치환본 … 커밋본과의 diff = 1줄(127행): $CysDownloadDir = "https://github.com/oogisoogi/jarvis-install/releases/download/wintest-v1.1.5-20260923/"   # wintest 임시 호스트(실기용 · 발행 뒤 폐기) — 기존 프리릴리스의 bootstrap.ps1 과 같은 치환 방식」 ⑵ 인박스 09-23 18:50:15 worker@987 「9차 선례 = 핀 커밋 → 127행 $CysDownloadDir 1줄 치환」 ⑶ ai-jarvis fe5d8bf(1.1.3) next/bootstrap.ps1 의 `$CysDownloadDir = "https://github.com/oogisoogi/jarvis-install/releases/download/wintest-v1.1.3-20260922/"`. 이번 줄 = `:135`(dce10a5 기준 · r6 뒤 줄번호 재확인) → `$CysDownloadDir = "https://github.com/oogisoogi/jarvis-install/releases/download/wintest-v1.1.6-<날짜>/"`. 확인 = 치환본과 P2 커밋본의 diff 가 정확히 1줄 · 그 주소 + `cysr_1.1.6_x64-setup.exe` 가 로그인 없이 200. ⚠ 선례 1.1.5 는 치환본 bootstrap.ps1 을 프리릴리스 자산으로도 올렸다(자산 목록 실측) — 이번에 next/ 만 쓰면 프리릴리스에 bootstrap.ps1 은 불필요(【판정】 · 한 줄이 next/ 를 가리키므로) | next/ 삭제(P3 되돌리기)와 함께 사라진다 |
| P9 | 옛 프리릴리스 `wintest-v1.1.5-20260923` 삭제(제목 「실기 뒤 삭제」 인데 남아 있음 【관측 19:2x】) | master 게이트(비가역 · P6 와 같은 때) | 명령 원문 【미확인】(선례 삭제 기록 못 찾음) · 명령(도구 도움말 실측 꼴 · 선례 아님): `gh release delete wintest-v1.1.5-20260923 -R oogisoogi/jarvis-install --yes --cleanup-tag` · 실행 전 확인 = `gh release view wintest-v1.1.5-20260923 -R oogisoogi/jarvis-install --json tagName,isPrerelease,name` → `wintest-v1.1.5-20260923 true wintest 1.1.5 (임시 · 윈 실기용 · 실기 뒤 삭제)`(19:4x 실측 값 · 이 셋이 같을 때만 실행) · 실행 뒤 확인 = `gh release list -R oogisoogi/jarvis-install` 에서 사라짐 · 옛 자산 주소 404 | 되돌리기 없음(비가역) — 필요하면 같은 자산(bootstrap.ps1 481,193 B · exe 140,687,576 B · .sig 412 B)으로 다시 만들 수 있으나 태그 커밋(605cdc35)·게시 시각은 새 값이 된다 |

### 판정 — 순서(㉮ 덮어 설치 → W1~W12 → ㉯ 지우기 → 새 설치)
【판정】 **맞다.** 신뢰도 높음(근거 = 코드·원장 실측).
1. ㉮ 는 **지금 노트북의 1.1.5** 를 바탕으로 쓴다 — 기존 참가자가 발행 뒤 겪는 덮어 설치 길이고, 1.1.3→1.1.5 에서 난 `.new` 4 결함(발행 차단급)의 재발을 여기서 본다(W9 ⑶).
2. ㉯ 는 앱까지 지운 기기에 **핀 1.1.6 설치기(스테이징)** 로 새로 깐다 — 워크숍 참가자의 첫 설치 길(master#f703427c B 채택 까닭).
3. 반대 순서(㉯ 먼저)면 ㉮ 의 바탕(1.1.5)이 사라져 덮어 설치를 못 본다 — 1.1.5 를 다시 깔 손이 든다.
4. ㉯ 끝에 1.1.6 이 새로 선 기기가 남는다 = 발행 뒤 앱 안 Update(1.1.6→다음 판) 시험 바탕으로 이어 쓸 수 있다(【판정】).
- 이전 판(A 기준 · 19:30 커밋 6ad09601)의 「설치기 시험(핀 1.1.5) → 그 위 덮어 설치」 판정은 master#f703427c 로 대체됐다(이력은 git 에 있다).

---

## ⑤ 박사님 세션 진행 순서(번호 목록)

전제: P1~P9 선행 조건이 선 뒤 master 가 「시작하셔도 됩니다」 알림. 노트북 = 지난 실기 기기(oogis · 1.1.x 설치 이력 있음 · 지금 1.1.5 인지는 【미확인】).

**W0 먼저**: 노트북 앱의 현재 판 확인 — PowerShell 에서 `cys --version`(`cys 1.1.5` 기대 · 맥 설치본에서 이 명령이 `cys 1.1.5` 를 찍는 것 실측) — 손 1 · 사진 1. 1.1.5 가 아니면 ㉮ 덮어 설치의 바탕이 달라지므로 master 에 먼저 알린다(W9 는 「그 판 → 1.1.6」 으로 읽는다 · master#6344c5e2 권고).

**㉮ 1.1.6 덮어 설치 + 점검표**
1. **설치 파일 받기**(② ⒜): github.com 로그인 → Releases 목록 → `cysr_1.1.6_x64-setup.exe` 받기 — 손 2~4(로그인 상태에 따라).
2. **덮어 설치**(W8·W9): 지금 깔린 1.1.5 함대를 켠 채 setup.exe 실행 → SmartScreen 「추가 정보 → 실행」 → 설치 → 앱 재시작 안내대로 — 손 3~4. 이어 `cys --version`(1.1.6) + `.new` 확인 한 줄(W9 ⑶) — 손 2 · 사진 1.
3. **첫 화면 점검**(W1·W4·W3): `cys list` 캡처 + `cys send '--surface=#N' hello` — 손 2 · 사진 1.
4. **창 늘리기·팔레트**(W2·W5): 셸 칸 2~3개 · 팔레트에 「분할」 — 손 3~4 · 사진 1.
5. **master 말 걸기**(W6·W7): 답 뒤 입력칸 · `/effort` — 손 2 · 사진 1.
6. **창 하나 닫고 앱 재실행**(W11 → W10): 손 2 · 사진 1.
7. **공지 대조**(W12): master 가 사진으로 대조(박사님 손 0).
- ㉮ 소계: 손 **약 16~20회** · 사진 **5장**.

**㉯ 지우기 → 설치기 0.3.36 새 설치(스테이징 · 1.1.6 을 임시 프리릴리스에서 받음)**
8. **① 지우기 한 줄**(④): 「지웁니다」 입력 → 윈도우 설정 앱에서 cysr 제거 → Enter → 폴더 지우기 Enter — 손 **약 5~6회**(붙여넣기 1 포함 약 6~7).
9. **② 설치 한 줄 1회차 → [3/10]~[4/10] 에서 창 닫기**(끊긴 기기 만들기 · r3 2줄째 준비) — 손 2.
10. **② 설치 한 줄 재실행 → 10/10**: r3 1·2줄(고지 뒤 서버 도착 · 앞 증거 0)은 master 가 텔레메트리로 대조 · 설치 중 SmartScreen·확인 창이 뜨면 각 1 — 손 1~3 · 사진 1(끝 화면 · 머리글 「cysr 1.1.6 · 설치 도우미 0.3.36」).
11. **첫 설치 화면 점검**: 창 3개(master·cso·worker1) · 본부 각성 — 손 0 · 사진 1.
12. **본부 자비스에 한 번 말 걸기** → r5 2줄(회색 제안 글 없음 · `/effort` = high) — 손 2 · 사진 1.
13. (선택 · 막힘 재현 시에만) r3 3줄째(보고 번호·폰 주소) — 막힘이 없으면 건너뜀.
- ㉯ 소계: 손 **약 11~14회** · 사진 **3장**.

- 박사님 손 합계: **약 28~35회**(W0 1 + ㉮ 16~20 + ㉯ 11~14 · 선택 항목 제외 · 이전 판 19~24 에서 ㉯ 지우기·새 설치만큼 늘었다) · 사진 약 **9장**. ㉯ 를 대안(재설치 한 줄)으로 하면 ㉯ 의 지우기 손 약 5~6회가 빠진다(박사님 결정 사항).
- 예상 소요(실측 계수 인용):
  - 설치기 1회(새 설치 · 10/10) = **약 10분대** — 1.1.1 윈 실기 1차 「텔레메트리 mkLNG74P 14:1x~14:25:52 10/10 rc=0」(SESSION_STATE · 시작 분은 「14:1x」 로만 기록 → 정확한 분 미상). ㉯ 는 끊는 1회차 + 재실행 1회라 **약 15~25분**(끊는 1회차는 [3/10]~[4/10] 에서 끝나 짧다 · 이 배분은 실측 아님).
  - 재시작 레인(W10·W11) = 1.1.1 윈 실기 2차 「14:3x」 = 1차 끝(14:25:52) 뒤 **약 10분 안** 합격 기록 【SESSION_STATE 원문 · 분 단위 미상】.
  - 파일 받기 · 덮어 설치(W9) · 지우기(①) = **실측 없음 · 첫 실기로 계수 확보**(참고: 이 좌석 GitHub 받기 22.1초 · 노트북 회선은 다름).
  - 합계 = 실측 계수 있는 구간만 약 25~35분 + 실측 없는 구간 — 전체 시간은 **실측 없음**으로 표기한다.
- 실기 뒤 정리(master 게이트 · 박사님 손 0): P3 되돌리기(next/ 삭제 → 404) · P6 임시 프리릴리스 삭제 — 둘 다 「실기 뒤 삭제」 규율(메모리 installer-field-test-staging-path · 선례 제목).

---

## 막힌 곳 · 미확인(정직)
- 윈 실측 0 — 이 좌석엔 윈 기기가 없다. ③의 【미확인】(PowerShell `#`·윈 단축키 이름)과 ② 의 Edge 내려받기 경고·드라이브 경고 실제 문구는 박사님 실기에서만 닫힌다.
- ② ⒜ 「로그인하면 draft 자산을 브라우저로 내려받을 수 있다」 = 공식 문서는 「보인다·목록에 나온다」까지 · 내려받기는 같은 권한의 `gh` 실측으로 추정(신뢰도 중).
- ② ⒝ 구글 드라이브 대용량 경고 = 공식 도움말에 문장 없음 · 커뮤니티 글 제목의 문구만(신뢰도 중).
- 노트북에 지금 깔린 판이 1.1.5 인지 · 설치 자리 표지(`jarvis-cys-pin.json`) 상태 = 【미확인】(기기 실물 필요).
- ④ P2 설치기 최종 해시 = 빈칸(1108 r5 【확인요청】 전 · 로컬 후보 dce10a5 · P7 r6 커밋이 하나 더 얹힌다).
- ④ P6 프리릴리스 생성 · P9 삭제 명령의 **선례 원문 = 못 찾음**(결과·속성·자산 교체 명령만 원문 인용) — 표의 `gh release …` 형태는 도구 도움말 실측이지 선례가 아니다.
- ④ P7 윈 핀 값의 3번째 대조(릴리스 SHA256SUMS.txt)는 B부 postprocess 뒤에만 가능 · 맥 핀 값은 B부 산출 뒤.
- ⑤ 소요 = 설치기·재시작 구간만 실측 계수(분 단위 일부 미상) · 나머지 실측 없음.
- 내려받은 setup.exe·.sig·latest.json 은 이 좌석 scratchpad 에만 있다(공유·업로드 0).
