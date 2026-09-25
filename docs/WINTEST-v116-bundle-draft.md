# 윈 실기 묶음 재료(최종판) — cysr 1.1.6 + 설치기 0.3.36 · 박사님 윈 노트북 한 자리

- 최종판: TICKET=v116-cut-close A부 · master#668dddf4(원장 19:20:27 surface:1112 submitted yes) · 작성 = worker@surface:1112 · 2026-09-25 19:2x~
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

순서 전제 = ④ 의 판정(설치기 0.3.36 시험이 기기에 **1.1.5** 함대를 세운 뒤 → 그 위에 1.1.6 setup.exe 덮어 설치). 그래서 **W8·W9 가 맨 앞**이고, 나머지는 1.1.6 이 선 뒤에 본다.

| # | 무엇을 | 확인 방법 | 기대 | 근거 |
|---|---|---|---|---|
| W8 | (윈만) 설치 파일 = 서명 없음 · SmartScreen | ① 의 setup.exe 더블클릭 → 첫 화면 | 「Windows의 PC 보호」 → 「추가 정보 → 실행」(손 1 · 1.1.1 윈 실기 선례와 같음) | ① Authenticode 없음 【관측】 · SESSION_STATE 1.1.1 윈 실기 1차 「손 1 = SmartScreen 추가 정보→실행」 |
| W9 | (윈만) 1.1.5 위 덮어 설치 — 함대가 떠 있는 채로 | 설치기 시험이 남긴 1.1.5 함대(master·cso·worker1)를 켠 채 setup.exe 진행 → 끝나면 앱 재시작 안내대로 | ⑴ 설치 뒤 판번 1.1.6(PowerShell `cys --version` → `cys 1.1.6` · 이 명령은 맥 설치본에서 `cys 1.1.5` 를 찍는 것 실측) ⑵ 좌석이 되살아남 ⑶ **팩 병합 대기 `.new` 파일 0개** — PowerShell `Get-ChildItem $HOME\.cys\pack -Recurse -Filter *.new` 결과 없음(1.1.3→1.1.5 덮어 설치 때 `.new` 4개 발행 차단 결함의 재발 점검) | 메모리 tauri-nsis-update-mode-skips-uninstaller(NSIS 업데이트 모드는 옛 제거기를 안 불러 데몬·세션을 끊지 않는다) · SESSION_STATE 09-23 01:4x 「윈 1.1.3→1.1.5 덮어쓰기 = `.new` 4」 · HANDOFF-v116-integ.md §14(:221) 「1.1.5 D1 RefreshUser」 |
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
- ⚠ 이 2줄은 **설치기가 깨운 본부 자비스(wake.ps1 경로)** 를 본다. ③ W6·W7 은 **cys 앱이 띄우는 좌석(launch_create_env_pairs 경로)** 을 본다 — 같은 모양의 확인이지만 다른 경로라 **둘 다** 본다(W9 덮어 설치 전에 이 2줄, 1.1.6 뒤에 W6·W7).

### 박사님이 치는 한 줄(스테이징 · 라이브 무접촉)
선행 조건(아래 표)이 다 선 뒤, 노트북 **명령 프롬프트 또는 PowerShell** 에 붙여 넣는 한 줄. 라이브 한 줄(`bootstrap.ps1:941`의 try/catch 정본)과 글자가 같고 **주소만 `/install/` → `/install/next/`** 다:

```
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Remove-Item ([Environment]::GetFolderPath('UserProfile')+'\install-jarvis.ps1') -ErrorAction SilentlyContinue; irm https://jarvis.godmeyou.kr/install/next/bootstrap.ps1 -OutFile ([Environment]::GetFolderPath('UserProfile')+'\install-jarvis.ps1') -ErrorAction Stop; powershell -ExecutionPolicy Bypass -File ([Environment]::GetFolderPath('UserProfile')+'\install-jarvis.ps1') } catch { Write-Host '설치 파일을 받지 못했습니다. 인터넷 연결을 확인하신 뒤 이 줄을 다시 붙여 넣어 주십시오.'; exit 1 }"
```
- 근거: ⑴ 정본 한 줄 = habitat fix/installer-0336(dce10a5) `install-master/bootstrap.ps1:941` 【관측】 ⑵ 스테이징 경로 = 메모리 `~/.claude/projects/-Users-oogisoogi-axdev/memory/installer-field-test-staging-path.md` 원문: 「bootstrap.ps1 단독은 형제 파일을 안 받으므로 `next/bootstrap.ps1` 한 줄이면 된다.」 ⑶ 옛 꼴(`irm …; powershell -File …`)을 쓰지 않는 이유 = 메모리 `windows-oneliner-semicolon-runs-after-failed-download`: 「받기 실패(-ErrorAction Stop 포함)에도 ; 뒤가 돌아 옛 파일을 실행한다 — $ 없는 try/catch + 선삭제가 정본」 — 이 노트북은 지난 실기(0.3.3x·1.1.5)의 `install-jarvis.ps1` 이 남아 있을 수 있어 특히 해당.
- 「PS 5.1 -File 사람 설치」 = 위 한 줄 안쪽의 `powershell -ExecutionPolicy Bypass -File` 이 Windows PowerShell 5.1 로 돈다(윈 기본 `powershell` = 5.1) → r3 체크리스트 1줄째를 그대로 덮는다.
- 「지난 실행이 끊긴 기기에서 재실행」(r3 2줄째): 같은 한 줄을 한 번 돌리다 **[3/10] 이후 아무 곳에서 창을 닫고**(Ctrl-C 또는 창 닫기) 다시 붙여 넣는다 = 박사님 손 +1. 【판정】 한 자리에서 보려면 이 순서(끊기 → 재실행)여야 한다.
- 로그아웃 갈래를 볼 필요가 있으면: 메모리 installer-field-test-staging-path 「①지우기가 로그인을 기본으로 남겨 [3/10] 카드 갈래가 안 돈다 → `Remove-Item ~\.claude\.credentials.json` 뒤 `next/bootstrap.ps1` 재실행으로 진입」 — 이번 체크리스트에는 없는 항목이라 **기본은 하지 않음**(master 판단).

### 선행 조건 — 누가(master 게이트) · 명령 · 되돌리기
| # | 선행 조건 | 누가 | 명령(원문 출처) | 되돌리기 |
|---|---|---|---|---|
| P1 | 서버·고지 = ai-jarvis `feat/hw-model-0336` **f1b1ccf4** 배포(설치 전용 사이트 Worker `jarvis-install-site` — 고지 페이지 `web-install/src/page.ts` + 수신 `web-install/src/telemetry.ts:130` ENV_TEXT_KEYS 에 hw_model·mem_gb·disk_free_gb) · 발행 순서 원문 「서버·고지 먼저 → 설치기」(master#70a20b94) | master 게이트 | `site/hub` 를 f1b1ccf4 로 빨리감기(원격 site/hub ⊂ feat · 앞선 6커밋 · 뒤진 0 【관측】) → `bash web-install/deploy.sh`(드라이런) → `bash web-install/deploy.sh --go`(원문 = deploy.sh 머리말 「쓰는 법」) | 되돌림 커밋(`git revert`) 뒤 `deploy.sh --go` — deploy.sh G3 「마지막으로 배포한 커밋이 지금 HEAD 의 조상이 아니면 거부」 때문에 **옛 커밋 재배포는 거부된다**(머리말 원문) · 이 서버 변경은 모르는 키를 「버린다(거부 아님)」(installer-0336 브리프 D6-c · telemetry.ts:225-231) 라 옛 설치기에 무해 |
| P2 | 설치기 최종 해시 확정(1108 r5 뒤) | master(1108 【확인요청】 r5 ACCEPT) | 【빈칸】 — 지금 habitat fix/installer-0336 로컬 HEAD = **dce10a5**(r5 · 18:53 커밋 · 【확인요청】 상한 19:50 · 아직 미보고) · 원격 fix/installer-0336 = 13a2392(r3) 【관측】 | 해당 없음(판정 단계) |
| P3 | 스테이징 게시 = `/install/next/` 에 그 해시의 ps1 3파일 | master 게이트 | ai-jarvis site/hub 에서 `mkdir -p site/install/next && cp <habitat 최종 해시 트리>/install-master/{bootstrap,reinstall,reset-clean}.ps1 site/install/next/` → 커밋 → `bash web/build-web.sh && (cd web && unset NODE_OPTIONS && npx wrangler deploy --config /Users/oogisoogi/axdev/ai-jarvis/web/wrangler.jsonc)`(배포 줄 원문 = `~/axdev/master/installer-golive.sh` 5단계 · 스테이징 선례 커밋 = ai-jarvis 26e442a·68f5097·956aeb4·fe5d8bf) · 게시 뒤 `curl -H 'Cache-Control: no-cache'` 로 next/ sha 3/3 대조(메모리 원문: 「첫 curl 이 엣지 HIT 로 구판을 줄 수 있으니 20초 뒤 no-cache 재측」) | `rm -rf site/install/next` 커밋 → 같은 배포 줄 → `next/bootstrap.ps1` **404** 실측(메모리 원문 「실기 통과 뒤 릴리스 커밋에서 next/ 삭제(임시 경로 잔존 금지 · 404 실측)」 · golive.sh 4단계도 같은 삭제) |
| P4 | 설치기 cys 핀 = 시험 동안 **1.1.5(발행본)** 유지 | master(확인만) | 확인 명령: `grep -n -E '^\$CysVersion' <habitat 최종 해시>/install-master/bootstrap.ps1` → `'1.1.5'` · `$CysDownloadDir` = `…/cys-ro/releases/download/v${CysVersion}/`(발행 릴리스 주소) — dce10a5 에서 `:134-135` 가 정확히 이 값 【관측】 · 라이브 `/install/bootstrap.ps1:130` 도 1.1.5 · InstallerVersion 0.3.35 【관측 19:2x】 | 해당 없음(바꾸지 않음) |
| P5 | 라이브 무접촉 확인 | master | 게시 전후 `/install/bootstrap.ps1` sha 동일(지금 = InstallerVersion 0.3.35) · `/install/next/bootstrap.ps1` 게시 전 404 【관측 19:2x】 | — |

### 판정 — 「설치기 시험 → 그 위에 1.1.6 setup.exe 덮어 설치(W9)」 순서가 맞는가
【판정】 **맞다(이 순서가 유일하게 안전하다)**. 신뢰도 높음(근거는 전부 코드·원장 실측).
1. 설치기 핀이 1.1.5(P4)이므로 설치기는 1.1.5 를 깐다. 그 결과가 곧 W9 에 필요한 「1.1.5 가 떠 있는 기기」다 — 1.1.5 를 따로 깔 손이 없다.
2. **반대 순서(1.1.6 먼저 → 설치기)** 는 핀 1.1.5 설치기가 1.1.6 기기에 1.1.5 를 **내려 까는**(판 되감기) 시험이 된다 — 실제 사용자 경로가 아니고, 1.1.6 덮어 설치(W9)도 못 본다.
3. 1.1.5→1.1.6 덮어 설치는 기존 참가자가 실제로 겪는 길(발행 뒤 setup.exe 재설치)과 같고, 1.1.3→1.1.5 에서 난 `.new` 4 결함(발행 차단급)의 재발을 여기서 본다(W9 ⑶).
4. 설치기 체크리스트 5줄(r3 3 + r5 2)은 1.1.5 함대 위에서 본다 — 이 5줄은 **설치기** 쪽 코드(wake.ps1·고지 문)를 재는 것이라 cys 판번과 무관하다(【판정】 · wake.ps1 은 설치기가 쓰는 파일).
- ⚠ 이 순서가 **안 덮는 것**(📌 master): 「설치기로 1.1.6 을 **새로** 까는 길」(워크숍 참가자의 첫 설치 길). 선례(1.1.1·1.1.3·1.1.5 윈 실기)는 임시 공개 호스트(`oogisoogi/jarvis-install` 프리릴리스 `wintest-v1.1.x-…`)에 setup.exe 를 올리고 next/bootstrap.ps1 의 `$CysDownloadDir` 1줄을 치환해 새 판을 설치기로 깔았다(ai-jarvis fe5d8bf 원문: 「$CysDownloadDir = "https://github.com/oogisoogi/jarvis-install/releases/download/wintest-v1.1.3-20260922/"」). 이번 브리프는 핀 1.1.5 유지이므로 그 길은 **이번 실기 범위 밖** — 1.1.6 의 새 설치 길은 설치기 핀을 1.1.6 으로 올리는 다음 판(발행 뒤)에서 본다. 대안(박사님·master 판단): 선례처럼 wintest 임시 호스트를 쓰면 한 자리에서 새 설치까지 볼 수 있으나 **공개 업로드 = 게이트** · 박사님 손 +1(설치기 한 번 더).
- 관측(행동 0 · master 참고): 옛 임시 호스트 `oogisoogi/jarvis-install` 프리릴리스 **`wintest-v1.1.5-20260923`(제목 「임시 · 윈 실기용 · 실기 뒤 삭제」)가 아직 남아 있다** — 자산 bootstrap.ps1 481,193 B · cysr_1.1.5_x64-setup.exe 140,687,576 B · .sig 412 B 【관측 19:2x `gh release list/view`】. 지우는 것은 비가역·공개 행위라 master 게이트.

---

## ⑤ 박사님 세션 진행 순서(번호 목록)

전제: P1~P5 선행 조건이 선 뒤 master 가 「시작하셔도 됩니다」 알림. 노트북 = 지난 실기 기기(oogis · 1.1.x 설치 이력 있음).

1. **설치 파일 받기**(② ⒜): github.com 로그인 → Releases 목록 → `cysr_1.1.6_x64-setup.exe` 받기 — 손 2~4(로그인 상태에 따라). *받아만 두고 아직 실행하지 않는다.*
2. **설치기 0.3.36 시험 1회차**(④ 한 줄): 명령 프롬프트/PowerShell 에 한 줄 붙여 넣기 → **[3/10] 이후에서 창 닫기**(끊긴 기기 만들기) — 손 2.
3. **설치기 재실행**(같은 한 줄): 10/10 까지 · 체크리스트 r3 1·2줄(고지 뒤 서버 도착 · 앞 증거 0)은 master 가 텔레메트리로 대조 — 손 1(+ SmartScreen·로그인 창이 뜨면 각 1).
4. **본부 자비스에 한 번 말 걸기** → r5 2줄(회색 제안 글 없음 · `/effort` = high) — 손 2(말 걸기 1 · `/effort` 1) · 사진 1.
5. (선택 · 막힘 재현 시에만) r3 3줄째(보고 번호·폰 주소) — 막힘이 없으면 건너뜀.
6. **1.1.6 덮어 설치**(W8·W9): 1 에서 받은 setup.exe 실행 → SmartScreen 「추가 정보 → 실행」 → 설치 → 앱 재시작 안내대로 — 손 3(실행 · 추가 정보 · 실행). 그 뒤 `.new` 확인 한 줄(W9 ⑶) — 손 1.
7. **첫 화면 점검**(W1·W4·W3): `cys list` 캡처 1장 + `cys send '--surface=#N' hello` — 손 2 · 사진 1.
8. **창 늘리기·팔레트**(W2·W5): 셸 칸 2~3개 · 팔레트에 「분할」 — 손 3~4 · 사진 1.
9. **master 말 걸기**(W6·W7): 답 뒤 입력칸 · `/effort` — 손 2 · 사진 1.
10. **창 하나 닫고 앱 재실행**(W11 → W10): 손 2 · 사진 1.
11. **공지 대조**(W12): master 가 사진으로 대조(박사님 손 0).

- 박사님 손 합계: **약 19~24회**(받기 2~4 · 설치기 3~5 · r5 2 · 덮어 설치 4 · W1~W11 11~12 · 선택 항목 제외) · 사진 약 5장.
- 예상 소요(실측 계수 인용):
  - 설치기 1회 = **약 10분대** — 1.1.1 윈 실기 1차 「텔레메트리 mkLNG74P 14:1x~14:25:52 10/10 rc=0」(SESSION_STATE · 시작 분은 「14:1x」 로만 기록 → 정확한 분 미상). 이번은 2회(끊기 + 재실행)라 **약 15~25분**(끊는 1회차는 [3/10] 에서 끝나므로 짧다 · 이 배분은 실측 아님).
  - 재시작 레인(W10·W11) = 1.1.1 윈 실기 2차 「14:3x」 = 1차 끝(14:25:52) 뒤 **약 10분 안** 합격 기록 【SESSION_STATE 원문 · 분 단위 미상】.
  - 1.1.6 덮어 설치(W9) · 파일 받기(1) = **실측 없음 · 첫 실기로 계수 확보**(참고: 이 좌석 GitHub 받기 22.1초 · 노트북 회선은 다름).
  - 합계 = 실측 계수 있는 구간만 약 25~35분 + 실측 없는 구간(받기·덮어 설치·W1~W7 사진) — 전체 시간은 **실측 없음**으로 표기한다.

---

## 막힌 곳 · 미확인(정직)
- 윈 실측 0 — 이 좌석엔 윈 기기가 없다. ③의 【미확인】(PowerShell `#`·윈 단축키 이름)과 ② 의 Edge 내려받기 경고·드라이브 경고 실제 문구는 박사님 실기에서만 닫힌다.
- ② ⒜ 「로그인하면 draft 자산을 브라우저로 내려받을 수 있다」 = 공식 문서는 「보인다·목록에 나온다」까지 · 내려받기는 같은 권한의 `gh` 실측으로 추정(신뢰도 중).
- ② ⒝ 구글 드라이브 대용량 경고 = 공식 도움말 문장 없음 · 커뮤니티 글 제목의 문구만(신뢰도 중).
- ④ P2 설치기 최종 해시 = 빈칸(1108 r5 【확인요청】 전 · 로컬 후보 dce10a5).
- ⑤ 소요 = 설치기·재시작 구간만 실측 계수(분 단위 일부 미상) · 나머지 실측 없음.
- 내려받은 setup.exe·.sig·latest.json 은 이 좌석 scratchpad 에만 있다(공유·업로드 0).
