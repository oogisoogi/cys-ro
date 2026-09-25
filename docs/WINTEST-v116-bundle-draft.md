# 윈 실기 묶음 재료(초안) — cysr 1.1.6 + 설치기 0.3.36 · 박사님 윈 노트북 한 자리

- TICKET=v116-integ-5 8단계 · master#0eb6ba6f(원장 17:31:24 surface:1105) · 작성 = worker@surface:1105 · 2026-09-25
- 성격: master 가 박사님용 묶음 브리프를 쓰기 위한 **재료 초안**이다. 업로드·공유·절단·태그·게시·배포는 전부 master/박사님 게이트이고, 이 문서를 만들면서 하나도 하지 않았다.
- 기준 트리 = fix/v116-integ **691111d5**(master ACCEPT · origin 일치) · CI 3종 초록(master 실측: ci-branch 36110130180 · windows-build 36110130147 · windows-health 36110130354).
- 표기: 【관측】 = 이 좌석이 도구로 잰 것 · 【판정】 = 그 관측에서 내린 결론 · 【미확인】 = 재지 못한 것.

---

## ① 1.1.6 설치 파일(윈 x64 NSIS)

| 항목 | 값 | 출처 |
|---|---|---|
| 런 · 아티팩트 | windows-build 36110130147 · `cys-windows-x64-nsis`(압축 140,880,569 B · 만료 2026-12-24) | `gh api …/runs/36110130147/artifacts` 【관측】 |
| 안의 파일 | **`cysr_1.1.5_x64-setup.exe`** · **140,856,763 B** | `gh run download` 【관측】 |
| sha256 | **ef67ee69cfa6743a2f696df3871c4aa0d1e41f9f7fcfff7b645da649bcf08948** | `shasum -a 256` 【관측】 |
| 판 문자열 | **1.1.5**(1.1.6 아님) — 소스 판번이 아직 1.1.5다: `src-tauri/tauri.conf.json:4` `"version": "1.1.5"` · `Cargo.toml:8` · `src-tauri/Cargo.toml:3` | 파일 이름 + 소스 3곳 【관측】 |
| 서명(Authenticode) | **없음** — PE 인증서 표(데이터 디렉터리 4) 크기 0 | PE 헤더 파싱 【관측】 |
| 업데이터 서명(.sig) | 이 아티팩트에는 **없음**(setup.exe 1개뿐) — 앱 안 Update 에 쓸 수 없다(②) | 【관측】 |

⚠ **【판정】 이 파일은 「내용은 1.1.6 후보(691111d5) · 판번 표기는 1.1.5」 인 시험용 빌드다.** 설치하면 앱·제어판·설치 폴더에 1.1.5 로 보인다. 박사님께 「1.1.6」 이라고 드리면 화면과 말이 어긋난다 → 묶음 브리프에 이 사실을 적거나, ② 의 판번 올림 뒤 빌드를 쓴다. Windows SmartScreen 경고(서명 없음)도 1.1.5 설치 때와 같이 뜬다 【미확인 · 박사님 기기에서】.

**박사님 윈 노트북으로 옮기는 방법(제안 1줄)**: GitHub Actions 아티팩트는 **로그인 없이는 못 받는다** — 저장소는 PUBLIC(`oogisoogi/cys-ro` · 옛 이름 cys-terminal 이 여기로 이어짐)인데도 아티팩트 zip 주소를 로그인 없이 받으면 **HTTP 401**【관측】. ⇒ ⒜ 박사님 노트북 브라우저에서 GitHub 로그인 → 런 36110130147 페이지 「Artifacts」 에서 zip 받기(가장 단순 · 박사님 손 1회) 또는 ⒝ master 가 받아 둔 파일을 사내 전달 경로(USB·드라이브 등)로 옮기고 sha256 을 박사님 기기에서 `Get-FileHash` 로 대조. ⒞ 게시(릴리스)로 올리는 방법은 공개 행위라 게이트 — ② 절단을 하면 draft 릴리스 자산으로 대체된다(draft 자산도 로그인 필요 · 아래).

---

## ② 「1.1.6 앱 안 Update(1.1.5 → 1.1.6)」 시험 — 절단·게시가 먼저 필요한가

**【판정】 필요하다 — 최소 「판번 올림 + 첫 절단(태그 → draft 릴리스)」, 그리고 기본 경로로 시험하려면 「게시」까지.** 게시 없이 하려면 시험 전용 우회(env)가 있으나 그것도 절단 산출물이 있어야 한다.

근거(줄 인용):
1. 앱 안 Update 는 `src-tauri/tauri.conf.json:51` 의 `https://github.com/oogisoogi/cys-ro/releases/latest/download/latest.json` 을 본다 — `releases/latest` 는 **공개(발행)된 최신 릴리스**만 가리킨다. 지금 그 자리의 latest.json 은 1.1.5 다.
2. 태그 절단 레인은 draft 에서 멈춘다: `.github/workflows/release.yml:15-16`(`tags: 'v*'`) · `:987` `releaseDraft: true`(「공개 발행·latest 마킹은 오너 승인 후」) · 공개 승격은 `.github/workflows/release-publish.yml:4-5`(`--draft=false` 만 · `workflow_dispatch` 입력 tag · SHA256SUMS sha · confirm=PUBLISH · dry_run 기본 true).
3. 업데이터 서명 파일(.sig)과 latest.json 은 절단 레인에서만 만들어진다: `release.yml:136`·`:951-955`(setup.exe(.sig) → latest.json 에 windows-x86_64 병합). windows-build 아티팩트엔 .sig 가 없다(①).
4. 판번: 소스가 1.1.5 라 이대로 절단하면 1.1.5 → 1.1.5 가 된다. 판번 같은 원격판은 build_id 가 다를 때만 「업데이트 있음」(`src-tauri/src/main.rs:5892-5894` same_version_ok) — 「1.1.5→1.1.6」 시험이 아니다.
5. 시험 전용 우회: `CYS_UPDATE_MANIFEST_URL`(`src-tauri/src/main.rs:5884-5887` · 「테스트 전용 env · Finder 런칭엔 env 없음」 · 설치는 박힌 pubkey 로 .sig 검증 불변). 윈에선 PowerShell 에서 env 를 세우고 앱을 그 셸에서 띄우면 된다【미확인 · 윈 실측 없음】. 단 가리킬 매니페스트와 자산이 **로그인 없이 받아지는 https 주소**여야 한다 — draft 자산은 로그인 필요(아티팩트 401 과 같은 부류 · draft 자체는 【미확인】)라 재호스팅이 필요하다.
6. 순서 문서와의 관계: `RELEASE-PROCESS-v2.md:174` 「첫 절단(태그) → CI · 절단 마감(K4) → 갱신 레인 VM 재확인 1회 → 윈 실기(박사님) → 발행」 — 윈 실기가 **발행 앞**이다. 기본 경로(1)의 앱 안 Update 는 발행 뒤에만 가능하므로, 발행 전 윈 실기에서 앱 안 Update 를 보려면 5 의 우회뿐이다.

**권고(단점 병기)**:
- A(권고) = 윈 실기(발행 전)는 **절단 draft 의 서명된 1.1.6 setup.exe 로 「새 설치 + 1.1.5 위 덮어 설치」** 를 보고, 앱 안 Update(기본 경로)는 **발행 직후 박사님 기기 1대 = 첫 사용자 확인**으로 한다. 단점: 앱 안 Update 결함이 발행 뒤에야 드러난다(되돌리기 = 아래 R4 로 latest 를 1.1.5 로 되돌림).
- B = 발행 전에 5 의 우회로 앱 안 Update 까지 본다. 단점: 매니페스트·자산 재호스팅(https · 로그인 없이) 준비가 필요하고, 그 재호스팅 자체가 공개 행위라 게이트 · 박사님 손이 env 설정·셸 실행까지 늘어난다.

**master 가 집행할 절단 단계(A 기준 · 명령 · 확인 · 되돌리기 한 줄씩)** — 전부 master/박사님 게이트 · 이 좌석은 하나도 실행하지 않았다:
| # | 단계 | 명령 | 확인 | 되돌리기 |
|---|---|---|---|---|
| C1 | 판번 올림(워커 티켓 · 커밋 1) | 3곳 `1.1.5`→`1.1.6`(tauri.conf.json:4 · Cargo.toml:8 · src-tauri/Cargo.toml:3) + `Cargo.lock` 갱신 · `scripts/version-check.sh`(3곳 일치 검사 — 이름으로 추정 · 【미확인】 사용법) | 판번 3곳 일치 · 정본 게이트 1회(또는 master 판정으로 A 레인만) | 되돌림 커밋 1 |
| C2 | git push(통합 가지) | `git push origin <C1 해시>:refs/heads/fix/v116-integ` | ls-remote 일치 · CI 3종 초록 | 그 전 해시로 되돌림 커밋(강제 push 금지) |
| C3 | 태그 절단 | `git tag v1.1.6 <C1 해시>` → `git push origin v1.1.6` | release.yml 태그 런 초록 · draft 릴리스 v1.1.6 에 맥·윈 자산 + `.sig` + `latest.json`(platforms 에 windows-x86_64·darwin) · 태그=소스 판번 단언(`release.yml:275`) | `gh release delete v1.1.6 --yes`(draft) + `git push origin :refs/tags/v1.1.6` + 로컬 `git tag -d v1.1.6` |
| C4 | 검증만(발행 0) | `gh workflow run release-publish.yml -f tag=v1.1.6 -f <SHA256SUMS sha> -f confirm=PUBLISH -f dry_run=true`(입력 이름 = release-publish.yml:50-70 원문 대조 필수) | 「Download the draft and verify it (publishes nothing)」 초록(`release-publish.yml:103`) | 없음(읽기만) |
| C5 | 윈 실기(박사님) | draft 의 `cysr_1.1.6_x64-setup.exe` 를 ①의 ⒜/⒝ 방식으로 옮겨 설치 | ③ 점검표 · ④ 설치기 체크리스트 | 문제 시 C3 되돌리기 |
| C6 | 발행 | `release-publish.yml` dry_run=false(오너 승인) | `releases/latest/download/latest.json` 이 1.1.6 · 박사님 기기 앱 안 Update 1.1.5→1.1.6 | 【R4】 `gh release edit v1.1.6 --draft=true` 로 내리면 latest 가 1.1.5 로 돌아간다【미확인 · 실제 되돌림 절차는 master 정본 확인】 |

---

## ③ 윈 점검표(1.1.6 실기)

| # | 무엇을 | 확인 방법 | 기대 | 근거 |
|---|---|---|---|---|
| W1 | 창 머리 번호 + `#N` 해석 1회 | PowerShell 에서 `cys list` → 창 머리 숫자와 5번째 칸 `no=N` 을 **같은 시각 캡처 1장**으로 대조 → `cys send '--surface=#<산 번호>' hello` | 창 머리 숫자 = `no=` 값 · stderr `#N → surface:N @<소켓 이름>` | HANDOFF §19-2 #5 · cys.rs:1463-1476(resolve_surface_arg) |
|  | ⚠ | PowerShell 에서 `#` 이 주석으로 먹히는지 【미확인】 — 인용부호로 감싸 넘길 것(`'--surface=#5'`) | | 맥 zsh 함정 §19-2 #5 ⚠ 의 윈 판 |
| W2 | 창 정렬 v2 — 워커 좌우 균등 | 셸 칸 ⌘D 대신 윈 단축키(Ctrl 계열 · 【미확인】 키 이름)로 2~3칸 → 칸마다 폭 | 워커 기둥 폭 서로 같음 · 사람이 위아래로 나눈 칸은 그대로 | HANDOFF-v2(편입 가지) · §22 |
| W3 | master:cso 위아래 4:1 | 본부 좌열 | 4:1 유지 | 박사님 결정 14:1x |
| W4 | 좌열 기본 폭 · 노트북 90칸 | 첫 기동 직후 master 칸 열 수(칸 안 `mode con` 또는 창 머리) | 좌열 = 창의 25%(상한 50%) · 노트북 화면에서 master 약 90칸(창이 좁으면 상한 50% 에서 멈춤) | 박사님 결정 14:5x · §22 · HANDOFF-v2 「좌열 기본 폭에 칸 여백」 |
| W5 | 팔레트 「세로 분할」 복원 | 명령 팔레트에 「분할」 | 「가로 분할」·「세로 분할」 둘 다 | HANDOFF-v2 바꾼 시험 7 |
| W6 | 제안 글 끄기(윈 경로) | master 에 한 번 말 걸고 답 뒤 입력칸 | 회색 제안 글 0 — 윈에서 좌석 env 가 닿는 유일한 경로 = `launch_create_env_pairs` | §17-2 6 · §17-8 ④ |
| W7 | 좌석 effort high | 좌석 claude 기동 줄·세션 기록 `"effort":"high"` | high | §19-2 #2 |
| W8 | (윈만) 설치 파일 = 서명 없음 · SmartScreen | 설치 첫 화면 | 「알 수 없는 게시자」 경고 → 「추가 정보 → 실행」 | ① |
| W9 | (윈만) 덮어 설치(1.1.5 위) 중 데몬·좌석 | 1.1.5 가 떠 있는 상태에서 setup.exe | 설치 뒤 좌석 되살아남 · 【알려진 성질】 NSIS 업데이트 모드는 옛 제거기를 안 불러 데몬·세션을 끊지 않는다(메모리 tauri-nsis-update-mode-skips-uninstaller) → 설치 뒤 앱 재시작 안내를 따르는지 | windows-build 런 · 메모리 |
| W10 | (윈만) phoenix 복원 | 앱 종료·재실행 | 좌석 복원 · 윈 T5 스모크(CI 36110130147 초록)와 같은 흐름 · 3차 CI 에서 「③ taskkill rc0」 플레이크 1회(§17-9 · 재실행 초록) | §17-9 |
| W11 | (윈만) T-PACK 묘비 경로 | 복원 중 창 하나 닫기(부서 없으면 본부) | 닫은 역할 다시 안 섬 · 윈 묘비 경로 = T-PACK Fable M-4 수리(윈을 None 으로 두면 되살림 없음 → 수리) | javis_formation.py:1094 |
| W12 | 1.1.6 공지와 어긋남 점검 | §17-5 공지 문안을 화면과 한 줄씩 대조 | ⑴ 「'눌러서 재시작' 알림」 — 앱 안 Update 를 거칠 때만(②) ⑵ 「머리줄 업데이트 → 다시 켜기」 는 **맥 전용**이라 문안이 「맥에서는」 으로 한정돼 있다 → 윈에서 안 보여도 정상 ⑶ 복원 카드 세 절 · ⑷ 창 번호 1~999 · ⑸ 게이지 흐림 없음 · ⑹ effort high ⑺ 제안 글 0 — ⑶~⑺ 은 윈에서도 보여야 함 | §16 · §17-5 |
|  | ⚠ 공지 보완 후보 | ①의 판번: 판번 올림 전 빌드를 쓰면 화면이 1.1.5 → 공지 「1.1.6」 과 어긋남 · 창 정렬 v2(§22)는 §17-5 초안에 **아직 없다** → 「창을 새로 열거나 닫으면 워커 창 폭이 자동으로 고르게 맞춰지고, 왼쪽 master·cso 열은 사용자가 정한 폭을 유지합니다」 류 1줄 추가 후보(문안 = master) | | §17-5 · §22 |

- VM 2차에서 **윈으로만** 볼 수 있는 항목: W8~W11(설치 파일 서명·덮어 설치·윈 phoenix·윈 묘비 경로) + W6 의 윈 env 경로 · §19-3·§21 의 「윈(CI 미서명 setup.exe)」 빈칸이 여기서 채워진다.

---

## ④ 설치기 0.3.36 윈 체크리스트 + 발행 순서

**원문 그대로**(인박스 2026-09-25T09:22:24+0900 · worker-46@surface:1094 【확인요청】 installer-0336 r3 · 「■ 윈 체크리스트(실기 때)」 절):

```
■ 윈 체크리스트(실기 때)
- PS 5.1 -File 사람 설치: [1/10] 고지 뒤 start·info 서버 도착(고지 문이 사람 설치를 막지 않음) · 고지 전 전송 0.
- 지난 실행이 끊긴 기기에서 재실행: [1/10] 앞 증거·그림 0 · 뒤는 정상.
- JARVIS_HELP_API_URL 없음 = 도움 보고 종전 주소 · 막힘 재현 시 보고 번호·폰 주소 표시.
```

**발행 순서 원문**(원장 master#70a20b94 · 2026-09-25T09:53:24+0900 → surface:1094 · 본문 마지막 줄 그대로):

```
- ⛔그 밖(서버 배포 · 설치기 발행 · 사이트 반영)은 여전히 master/박사님 게이트 — 발행 순서(서버·고지 먼저 → 설치기)와 윈 실기(네 체크리스트)는 1.1.6 윈 실기와 한 자리에서 묶어 잡는다.
```

- 같은 본문의 승인 대상 해시: habitat `fix/installer-0336` ← 13a23924950268a1a23c44d4b7b1536bdb10ab18 · ai-jarvis `feat/hw-model-0336` ← **f1b1ccf4**de9ab6210b6e17aa376a72453add7bd2(= 먼저 배포할 서버 쪽).
- 순서(요약 아님 · 위 원문의 전개): ⑴ 서버 ai-jarvis feat/hw-model-0336 **f1b1ccf4** 배포 ⑵ 고지 반영 ⑶ 설치기 0.3.36 발행 — 전부 master/박사님 게이트.
- **설치기 최종 해시 = 「r4 뒤」(빈칸)** — 1108 이 r4 소수정 중(master#0eb6ba6f). habitat 쪽 13a2392 는 r3 ACCEPT 값이고 발행 해시가 아니다.
- M-5(같은 인박스 절): 0.3.36 이 라이브가 되어도 앱 안에는 아무것도 안 보임 · 설치기를 다시 돌릴 때만 머리글 「설치 도우미 0.3.36」 과 [1/10] 첫 화면 고지가 보임 — 윈 실기 때 「설치기 재실행」 칸에서 확인.

---

## 막힌 곳 · 미확인(정직)
- 윈 실측 0 — 이 좌석엔 윈 기기가 없다. ③의 【미확인】(PowerShell `#`·윈 단축키 이름·env 우회의 윈 동작)은 박사님 실기 또는 윈 CI 로만 닫힌다.
- draft 릴리스 자산이 로그인 없이 받아지는지 = 【미확인】(절단 전이라 대상이 없다 · 아티팩트는 401 관측).
- `scripts/version-check.sh` 의 사용법 · C6 되돌리기(R4)의 정본 절차 = 【미확인】(master 정본 확인 필요).
- 내려받은 setup.exe 는 이 좌석 scratchpad 에만 있다(공유·업로드 0).
