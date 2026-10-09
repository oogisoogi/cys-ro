# HANDOFF · TICKET=cysr-1110-docs (1.1.9 발행 전 문서·설치 사이트 문안 · 2026-10-10)

- 판정: 1단계 실측표 통과 → master#e6c5cb95(08:12) = 결정 1B · 2A · 3A · 4(창 제목 교체 · 배포는 master 가 1.1.8 라이브 전환과 묶음).
- 저장소별 커밋(push 0 · 배포 0 · 라이브 사이트 트리 무접촉):
  - cys `docs/1110-naming`: `c88d456b` ③ · `d653b058` ⑤ · `7fb6ad31` ⑥ · (이 문서 커밋)
  - ai-jarvis `docs/1110-naming`: `c1fe6a9` ①

## 1. 끝난 것 — 치환 건수표

| 커밋 | 저장소 | 파일 | 바뀐 것 | 건수 |
|---|---|---|---|---|
| ① c1fe6a9 | ai-jarvis | `site/` 13쪽(devlog · get · howto 6 · index · notice 4) | 하단 원작자 표기를 한 줄로 축약: 「이 프로그램은 오픈소스 cys 터미널(GitHub: idoforgod)을 바탕으로 만들었습니다.」(GitHub 링크 유지 · CYSJavis·「파생판」·「허락을 받아 … 배포」 문장 삭제) | 13줄 (낱말 cys 39→13 · CYSJavis 13→0) |
| ① c1fe6a9 | ai-jarvis | `site/howto/manual.html:57` | 창 제목 「cysr — CYSJavis Terminal」 → 「cysr」 (1.1.8 창 제목 = `cysr` · 앱 커밋 f01b630b 가 v1.1.8 에 들어 있음) | 1줄 |
| ③ c88d456b | cys | `docs/RELEASE.md:249` | §1 잠복 DMG 레그의 `Install cys.app`·`.support/cys.app` 뒤에 「원작자 판 DMG 꼴의 옛 이름 · 지금 발행물은 zip 안 cysr.app 하나」 병기 | 1줄 |
| ⑤ d653b058 | cys | `cysjavis-pack/bin/tests/run_bootstrap_health.py:8574·10421` | 「업데이트」 → 「갱신」(주석 1 · 실패 메시지 1 · 둘 다 팩 갱신 뜻 · 동작 0) | 2줄 |
| ⑥ 7fb6ad31 | cys | `scripts/deploy-homepage.py` · `scripts/verify-release-remote.py` | 독스트링 머리에 「원작자(벤더) 홈페이지 레인 전용 · 우리 포크 미사용 — 우리 발행 = docs/RELEASE.md 현행 정본 절」 1줄 | 2줄 추가 |
| ④ | cys | `docs/DESIGN-factory-reset.md` | **무변경** — 해소 판정 grep(업데이트·삭제 RPC·env·단추 17종) 이미 0(81b792db · 10-07) | 0 |

무변경 판정(근거 포함):
- 실물 폴더 이름 `CYSjavis`(바탕화면·사용자 폴더) 15회 — 파일·폴더 이름은 식별자 예외. 바꾸면 사용자가 없는 폴더를 찾는다.
- 식별자 문맥 낱말 `cys` 3곳 — `devlog/index.html:116`(「예전 이름 cys 도 그대로 됩니다」 = 명령 이름) · `get/index.html:193`(V3 가 보여 주는 실행 파일 이름) · `help/J-UPD-03.html:46`(경로 `~/.cys/update`·`cys-update`).
- 지난 기록 속 「cys 터미널에서 출발」 2곳 — `devlog/index.html:107` · `notice/2026-10-04/index.html:66`(결정 2A · 날짜 박힌 지난 공지).
- cys 저장소 매니페스트 밖 `cys.app` 현행 꼴 13줄 — 전부 날짜 박힌 작업 기록(당시 실물 이름이 `cys.app`).
- 이월 ③(dist-win README 채널 · RELEASE.md cysinsight·DMG) — publish-docs-118(29c29859 · 1afc471a · 01c5cb7c · 10-07)에서 이미 해소.

## 2. 게이트 출력 (도구 출력 그대로)

ai-jarvis (`S=(-- 'site/*.html' 'site/*.js' 'site/get/*.command' 'site/get/*.cmd')`):
```
G1(credit 줄 수 · 13 = 축약 문안 동일)
  13     <p class="credit">이 프로그램은 오픈소스 cys 터미널(GitHub: <a href="https://github.com/idoforgod/cys-terminal">idoforgod</a>)을 바탕으로 만들었습니다.</p>
G2        0      # CYSJavis(대소문자 무시) 중 폴더 이름 「CYSjavis( |/|</b>| 폴더)」 밖
G3        0      # 낱말 cys 중 credit 줄 · 식별자 3 · 지난 기록 2 밖
G4        0      # idoforgod|cysinsight|cys\.app|cys_[0-9<]|CYSJavis Terminal 중 credit 줄 밖
G4b credit 안 CYSJavis 0
gate.sh rc=0     # GATE=PASS — 7단계 전부 통과 (치환 전 기준도 PASS 7/7)
build-web rc=0   # web/dist 재생성 · dist/index.html 의 credit 줄 1
```
치환 전 같은 게이트 실측(판별력 확인): G2 = 14 · G3(credit 제외) = 2(지난 기록 2 — 허용 목록에 넣기 전) · G4(credit 제외) = 1(창 제목).

cys:
```
G5  bun test ui/src/publicdocs.test.ts → 15 pass 0 fail
G6  DESIGN-factory-reset=0 run_bootstrap_health=0   (치환 전 0 · 2)
G7  0   # 매니페스트 22파일의 현행 뜻 cys.app 줄 (치환 전 1 = RELEASE.md:249)
G8  2 · ast 파싱 ok(3파일)
deploy-homepage.py --self-test → 7/7 PASS
secret-scan.sh <바뀐 4파일> → rc 0
```

## 3. 미완·함정·재현

- **그림 `site/assets/shots/cysr/02-title-bar.png` = 옛 제목 「cysr — CYSJavis Terminal」 그대로 → 교체 필요**(쓰는 곳 = `howto/manual.html:54` 한 곳 · 이 티켓 무접촉 · 1.1.8 앱 창 제목 줄을 새로 찍어 바꾼다).
- **배포 묶음(master)**: ① 커밋의 창 제목 문장은 1.1.8 이상과 맞는다. 라이브 판이 1.1.7 인 동안 배포하면 사이트와 실물이 어긋난다 → 1.1.8 라이브 전환(10-11 15:00)과 같은 배포로.
- **재현**: 게이트 명령은 위 그대로. 주의 — zsh 에서 파일 목록을 변수에 담아 `cat $F` 하면 단어 분리가 안 되어 0 이 나온다(배열 `"${S[@]}"` 로 넘길 것). `git grep -E '\bcys\b'` 는 POSIX ERE 라 `\b` 가 먹지 않아 0 이 나온다 — 낱말 검색은 `git grep -w cys`.
- `python3 -m py_compile` 은 팩 트리에 `__pycache__` 를 남긴다(이번에 만든 1개는 지웠다) — 팩 파일 문법 확인은 `ast.parse` 로.

## 4. 별 티켓 제안서 — 설치기 화면 줄의 낱말 cys → cysr (결정 3A)

### 4-1. 왜 이 티켓에서 뗐나
- ai-jarvis `site/install/` 6종(bootstrap.sh·.ps1 · reset-clean.sh·.ps1 · reinstall.sh·.ps1)은 **공개 jarvis-install 저장소 main d1a395b 와 바이트 동일한 사본**이다(sha256 4/4 일치 · ai-jarvis d4c68a9 「사본 동기」). `site/install/next/` 는 ai-jarvis `u5/install-link-118`(2a091fc) 산출. 사이트 사본만 고치면 다음 동기에서 되돌려지고 정본과 갈라진다.
- 설치기 시험이 화면 문구를 **글자 그대로** 잡고 있다 — jarvis-install `tests/` 88줄(아래 4-4).
- `tests/help-escalation.tsv` 가 문구 정본이고, 두 설치기와 도움말 문서가 그 줄을 글자 그대로 품는지 `install-master/checks.sh:1212` 가 잰다. 그 가운데 낱말 cys 가 든 줄 2개: `J-AV-02`(「백신의 보호 기록(격리함)에 cys 설치 파일이 있으면 …」) · `J-RM-01`(「열려 있는 cys 는 재설치가 스스로 닫습니다.」).
- 맥·윈 문구 짝: `install-master/checks.sh:326` 이 두 설치기의 언어 묶음 지문을 대조한다 · `install-master/ps1-sh-parity.tsv`(낱말 cys 23줄 — 대부분 함수 설명).
- 라이브 `/install/` 를 고치는 일 = 모든 사용자에게 나가는 설치기 변경(문자열 안 인용 실수 = 설치 실패).

### 4-2. 제안 순서
1. 정본(jarvis-install 개발 갈래 · 또는 u5 갈래)에서 R1 로 화면 줄 치환 — 맥·윈 짝을 같은 커밋에.
2. `help-escalation.tsv` 2줄 + 도움말 문서(J-AV-02 · J-RM-01) 같은 커밋에서 함께.
3. 시험 88줄의 기대 문구를 같은 커밋에서 갱신 → `install-master/checks.sh` · 설치기 시험 스위트 전건 녹.
4. 설치기 판 올림 → `/install/next/` 스테이징 → 실기 확인 → 라이브(master).

### 4-3. 치환 규칙 R1 (설치기 화면 줄)
- 바꿈: 사람에게 보이는 제품 이름 낱말 `cys`(뒤에 조사 · 「창」 · 「앱」 · 「프로그램」 · 「설치」 · 「상태」 · 「실행 링크」 · 「이후」 · 판 번호 등) → `cysr`. 진단표 칸 이름(`cys 상태` · `cys 실행 링크` · `cys 이후 전 행`)도 사람에게 보이므로 대상.
- 그대로: 실행 파일·경로(`cys.exe` · `cys-app.exe` · `cysd` · `~/.cys/…` · `%LOCALAPPDATA%\cys` · `cys-home` · `cys-update`) · 옛 앱 자리 이름(`cys.app` — 「옛 이름」 문맥) · 사용자가 칠 명령(설치기가 거는 링크는 `cys` 뿐 · `cysr` 별칭은 앱의 셸 CLI 단추를 누른 맥에만 생긴다 → 명령 예시를 `cysr` 로 바꾸면 안 되는 기계가 있다) · 작업·서비스 이름(작업 이름 `cysd` · LaunchAgent 라벨) · 실물 폴더 `CYSjavis`.
- 주석(`#`)은 대상 아님.

### 4-4. 시험이 잡고 있는 문구 — jarvis-install `tests/` 88줄
`grep -rnE 'cys (가|를|창|프로그램|설치|안에서|상태|실행 링크)' tests` 출력:
```
tests/mac-telemetry-run.sh:229:mkdir -p "$SB/p8b/home/install-jarvis"; printf '%s\n' "2026-09-16T22:00:00+0900 [6/10] cys 를 설치합니다." > "$SB/p8b/home/install-jarvis/bootstr
tests/v0318-emu-run.sh:81:      [ "$r" = "r5=0 r6=0" ] && [ "$niwr" = "0" ] && [ "$nrun" = "0" ] && has "$L" '같은 판\(v[0-9.]+\)의 cys 가 이미 설치돼 있습니다 \(지문 확인\) — 받지 않고'
tests/v0318-emu-run.sh:100:      t $? "[① 새 기계] cys 가 없으면 종전대로 받아 설치한다" "$why"
tests/v0318-emu-run.sh:204:t $? "[⑥ 부르는 자리] [7/10] 이 cys 를 확인한 뒤 cys 자리를 사용자 PATH 에 넣는다" "Step-VerifyCys 안에 Seed-CysPath 호출이 없다"
tests/help-escalation.tsv:27:way	J-AV-02	백신의 보호 기록(격리함)에 cys 설치 파일이 있으면 [복원]을 골라 주십시오.
tests/awaken-mutate.py:310:     "        Say '     남은 자리는 자비스가 이어서 세웁니다. cys 창의 자비스에게 무엇이 걸렸는지 물어보십시오.'",
tests/mac-install-mutate.sh:2:# 맥 [6/10] 실행 비트 게이트 — 「설치를 마쳤습니다」를 찍었는데 cys 가 실제로는 실행되지 않는 상태를 붉게 잡는다.
tests/mac-install-mutate.sh:9:# 무엇을 하는가: 실물 bootstrap.sh 를 함수 묶음으로 읽고(JARVIS_LIB_ONLY=1) step_install_cys 를 **가짜 zip** 으로 끝까지 부른다.
tests/mac-install-mutate.sh:14:#     F2 dead  — 실행 비트는 있으나 cys 가 돌지 않는다(비트로 못 고침) → 요구: 「마쳤습니다」 를 찍지 않는다
tests/mac-install-mutate.sh:146:            t $? "[$tag dead] 비트가 있어도 cys 가 안 돌면 「마쳤습니다」를 찍지 않는다(--version 실행 검사)" "$(grep '\[6/10\]' "$SB/out.txt" | tail -2 | tr '\n' '|
tests/mac-install-mutate.sh:168:    t $? "[defect nox] 벨트 없는 판은 「마쳤습니다」를 찍는데 cys 가 돌지 않는다(= 오늘 실기 재현 · 이 시험의 F1 이 여기서 붉다)" "마쳤다=$(claimed "$SB" && echo y || echo n) · 돈다=
tests/d5-f10-fail-events-and-407.sh:31:grep -q '^rc=' "$T/out-p407" || { echo "FAIL 측정 무효: step_download_cys 가 돌아오지 않았다"; tail -3 "$T/out-p407" | sed 's/^/  /'; exit 2; }
tests/defect-0930-mac-rh.sh:5:#   ⓐ CYS_CLI = 절대 경로 · 실행 가능 → 그것(옛 ~/.local/bin/cys 가 먼저 있어도)
tests/win-stale-cys-run.ps1:4:#   그 기계는 **cys 폴더는 있는데 설치 목록 항목이 없었다.** 설정 앱은 그 항목을 보므로 cys 가
tests/win-stale-cys-run.ps1:13:#   그 자리는 환경변수를 갈아 끼워도 격리되지 않는다. 진짜 cys 가 있으면 그 자리를 건드리게 된다.
tests/win-stale-cys-run.ps1:45:    Write-Host '::error::이 기계에 진짜 cys 설치 목록 항목이 있습니다 — 시험을 시작하지 않습니다.'
tests/win-stale-cys-run.ps1:53:#   지우개는 이름에 cys 가 들어간 등록을 찾아 **해제**한다. 그 자리는 사용자 폴더를 안 본다
tests/agent-flag-run.sh:8:# ⛔이 입구는 진짜 cys 를 부르지 않는다. 가짜를 놓고 **넘어간 인자만** 받아 적는다.
tests/agent-flag-run.sh:15:#   --cys       가짜 cys 가 「그 칸이 있다/없다」 중 무엇으로 답하는가(참가자 기기 = no-agent)
tests/agent-flag-run.sh:96:echo "── 가짜 cys 가 받은 인자 ─────────────────────────"
tests/delete-path-run.sh:24:    echo "거절: 이 기계에 cys 가 깔려 있고 CI 가 아닙니다 — 제거기 전체 실행은 게스트·러너에서만(운영 맥 보호)."; return 1
tests/delete-path-run.sh:250:t $? "[맥] ⓓ-2 ~/.cys 를 옮긴 뒤 수·크기가 다르면 「보관 확인 실패」 · 앱·클로드 안 지움 · rc 7" "rc=$(rc_of d2) · $(why d2)"
tests/delete-path-run.sh:299:# ── 결정⑵ 가드 단독(이어 하기를 끈 상태) — 같은 실행 둘째 회차가 끝나지 않은 표지가 있는 보관 폴더에 ~/.cys 를 또 옮기지 않는다
tests/delete-path-run.sh:304:t $? "[맥] 결정⑵ 가드 단독 — 이어 하기를 꺼도 둘째 회차가 끝나지 않은 표지 위에 ~/.cys 를 또 옮기지 않는다" "rc=$(rc_of rg2) · $(why rg2 4)"
tests/delete-path-run.sh:306:#    덮지 않고 · 옛 자료는 보관본에 · 표지 유지 · rc 7 · 쉬운 말 · 그 이름에 「되옮겼습니다」 0 · 이어 가지 않는다(~/.cys 를 또 옮기지 않음) ──
tests/delete-path-run.sh:371:# ── r1 F6(윈 짝) 완전 삭제에서 끄지 못한 cys 가 남으면 이번 회차에는 아무것도 옮기지 않는다(작업 폴더 · ~/.cys · 상태 그대로 · rc 7) · 재설치는 알림만 ──
tests/delete-path-run.sh:376:t $? "[맥] F6 완전 삭제에서 끄지 못한 cys 가 남으면 아무것도 옮기지 않는다(보관본 0 · ~/.cys 그대로 · 앱 그대로 · rc 7 · 윈 짝)" "rc=$(rc_of al) · 보관본 $(nbk "$H") · $(why al 5)"
tests/delete-path-run.sh:379:t $? "[맥] F6 재설치(앱 남김)는 끄지 못한 cys 가 있어도 알림만 하고 이어 간다(윈 -KeepApp 짝)" "rc=$(rc_of al2) · $(why al2 4)"
tests/delete-path-run.sh:710:t $? "[윈] ⓓ-2 ~\\.cys 를 옮긴 뒤 수·크기가 다르면 프로그램·클로드 안 지움 · rc 7" "rc=$(wrc d2) · $(wwhy d2)"
tests/delete-path-run.sh:762:t $? "[윈] 결정⑵ 가드 단독 — 이어 하기를 꺼도 둘째 회차가 끝나지 않은 표지 위에 ~\\.cys 를 또 옮기지 않는다" "rc=$(wrc g2) · $(wwhy g2 4)"
tests/delete-path-run.sh:763:# ── r2 Fable N7 윈 F6 짝 — 완전 삭제에서 끄지 못한 cys 가 남으면 아무것도 안 옮김(rc 7 · 보관본 0 · 프로그램 그대로) · 재설치는 알림만 ──
tests/delete-path-run.sh:767:t $? "[윈] r2 N7 완전 삭제에서 끄지 못한 cys 가 남으면 아무것도 안 옮긴다(rc 7 · 보관본 0 · 프로그램 그대로 · 거짓 약속 문구 0)" "rc=$(wrc al) · 보관본 $(wnbk al) · $(wwhy al 4)"
tests/delete-path-run.sh:769:t $? "[윈] r2 N7 재설치(-KeepApp)는 끄지 못한 cys 가 있어도 알림만 하고 이어 간다" "rc=$(wrc al2) · $(wwhy al2 4)"
tests/defect-0930-ci-win.ps1:1:# 0.3.38 윈 설치기 결함 묶음 — 실제 cys 설치 파일(NSIS)로 재는 러너 시험(윈도우 러너 전용 · 사람 기기에서 돌리지 않는다)
tests/v038-mutants.py:260: ("M58 깔린 cys 를 판 확인 없이 건너뛴다", "install-master/bootstrap.sh",
tests/v038-mutants.py:269:  '  if [ -d "$CYS_OLD_APP" ] || [ -d "$CYS_FORK_APP" ]; then\n    say "     돌고 있는 cys 가 있으면 먼저 끕니다."\n    cys_stop_old_app\n  fi\n',
tests/v038-mutants.py:272: ("M61 옛 cys 를 명령줄로 끈다", "install-master/bootstrap.sh",
tests/v038-mutants.py:297:  '  if [ "$KEEP_APP" = "1" ]; then\n    say "  [남김] cys 프로그램',
tests/v038-mutants.py:298:  '  if false; then\n    say "  [남김] cys 프로그램',
tests/d5-f2-reinstall-no-question.sh:6:#   ⇒ 시험 사본에서 절대경로 /Applications/·/usr/local/bin/cys 를 가짜 루트로 바꾸고, launchctl·security 는 PATH 가짜로 막는다.
tests/v0329-mutate.py:43:    # ③ 분류가 틀리면 옛 cys 가 「실패」로 계상되거나 성공이 폴백으로 떨어진다(동작 축 — 글자 축은 못 본다).
tests/rerun-after-done-run.sh:19:# ⛔바깥에 닿지 않는다 — USERPROFILE·HOME·JARVIS_HOME 은 mktemp -d 안 · PATH 에는 가짜 claude 만(진짜 claude·cys 를 안 본다) ·
tests/rerun-after-done-run.sh:45:BASEPATH="$SB/bin:/usr/bin:/bin"   # 진짜 claude·cys 가 있는 자리를 PATH 에서 뺀다
tests/remote-help-run.sh:5:# ⛔바깥에 닿지 않는다 — 가짜 서버(127.0.0.1)만 부른다. 진짜 cys·자비스를 부르지 않는다(가짜 cys 를 놓는다).
tests/remote-help-run.sh:494:  check "exec-cys 공백 든 절대 경로의 cys 를 인자 배열로 부른다 · PATH 의 같은 이름은 부르지 않는다" $? "$(ack_line 3)"
tests/remote-help-run.sh:760:MODE=full; J_CODE=J-DL-04; NOTICE_SHOWN=1; BLOCKED_STEP="cys 설치 파일 받기"
tests/remote-help-run.sh:770:  # 외부 검토 2차 재현 — cys 가 **실패하면서** 답에 surface: 를 섞는다(rc 1 · 「error: could not open surface:42」).
tests/remote-help-run.sh:772:  #   ⚠작업 폴더 경로에 공백이 있으면 cys 안에서 여는 갈래 자체를 건너뛴다 ⇒ 이 시험만 공백 없는 자리를 쓴다.
tests/remote-help-run.sh:778:MODE=full; J_CODE=J-DL-04; NOTICE_SHOWN=1; BLOCKED_STEP="cys 설치 파일 받기"
tests/remote-help-run.sh:787:  check "wake-seat-failed cys 가 실패하면서 답에 surface: 를 섞어도 성공으로 읽지 않는다 — 원격 해결이 돈다(보고 1건)" $? "$(cat "$SB/wake" 2>/dev/null) · 보고 $(grep -c '"pa
tests/remote-help-run.sh:837:  # D1 기각(외부 검토 1차) — REACHED_WAKE=1 은 파일에 한 자리뿐 · cys 창에 자비스를 연 줄 바로 뒤(주석 건너뜀) · 그 다음이 함대 부르기
tests/remote-help-run.sh:839:       /REACHED_WAKE=1/{n++; if (prev ~ /cys 안에서 자비스를 열었습니다/) at=1; want=1; prev=$0; next}
tests/remote-help-run.sh:843:  check "wire-wake REACHED_WAKE=1 은 깨우기가 성공한 뒤(cys 창을 연 갈래)에만 — 한 자리" $? "배선이 다르다"
tests/win-v3-mutate.py:40:    # ⓑ 프로그램을 남기기로 한 실행에서 목록 항목만 지운다 — 설정 앱에서 cys 가 사라진다(교착 자가 생산).
tests/win-v3-mutate.py:44:        Write-Host '  남김: cys 설치 목록 항목 (프로그램이 남아 있어 설정 앱에서 지우실 수 있게 둡니다)'
tests/win-v3-mutate.py:46:        Drop 'cys 설치 목록 항목' $RegKey
tests/win-v3-mutate.py:48:        "new": "    Drop 'cys 설치 목록 항목' $RegKey",
tests/reinstall-keepapp-emu-run.sh:6:#   ⓑ cys 프로그램 폴더(제거 프로그램 포함)를 지우지 않는다
tests/reinstall-keepapp-emu-run.sh:8:#   ⓓ 살펴보기 목록에 「[남김] cys 프로그램」 한 줄
tests/reinstall-keepapp-emu-run.sh:61:  t $? "[재설치] cys 프로그램 폴더를 지우지 않는다" "cys 폴더 또는 제거 프로그램이 사라졌다"
tests/reinstall-keepapp-emu-run.sh:64:  has "$SB/reset-out.txt" '\[남김\] cys 프로그램'
tests/reinstall-keepapp-emu-run.sh:65:  t $? "[재설치] 목록에 「[남김] cys 프로그램」 한 줄" "지우개 출력에 그 줄이 없다"
tests/d5-f3-no-false-done-when-blocked.sh:5:#   망 0: curl 은 가짜(자산 자리 = 404). 옛 cys 가 깔린 기계 = 가짜 cys 명령 + 자리 열기·함대 확인 함수를 「성공」으로 흉내.
tests/d5-f3-no-false-done-when-blocked.sh:25:# 옛 cys 가 살아 있는 기계의 함대 = 전부 성공으로 흉내(이 흉내에 닿는 것 자체가 결함의 경로다)
tests/delete-path-mutate.py:34:    # r1 F2(master#0337b3fa) — 겹침을 옛 「건너뛰기」로 되돌림 · 지난 되옮기기를 못 끝냈는데 ~/.cys 를 또 옮김
tests/delete-path-mutate.py:63:    # r1 F6 — 맥 완전 삭제에서 끄지 못한 cys 가 남아도 옮김 · ~/.cys 칸만 막음 풀기
tests/delete-path-mutate.py:67:     '  if [ "${PROC_BLOCKED:-0}" = "1" ]; then\n    :   # r1 F6 — cys 가 아직 돌고 있다: ~/.cys', '  if false; then\n    :   # r1 F6 — cys 가 아직 돌
tests/delete-path-mutate.py:150:     "# ── 「cys 를 곧 끕니다」 (v0.3.10", "$null = Read-Host '지웁니다'\n# ── 「cys 를 곧 끕니다」 (v0.3.10"),
tests/awaken-emu-run.sh:225:      grep -q '다음에 할 일: cys 창의 master 자리에 있는 자비스에게 위 한 줄을 전해 주십시오' "$O" && ! grep -q '설치가 끝났습니다' "$O"
tests/awaken-emu-run.sh:434:      grep -q '다음에 할 일: cys 창의 master 자리에 있는 자비스에게 위 한 줄을 전해 주십시오' "$O" && ! grep -q '설치가 끝났습니다' "$O"
tests/awaken-emu-run.sh:474:      grep -q '다음에 할 일: cys 창의 master 자리에 있는 자비스와 이어서 이야기하십시오' "$O" && ! grep -q '다시 하시는 법' "$O"
tests/awaken-emu-run.sh:512:      c="$(grep -n 'cys 안에서 자비스를 열었습니다 (surface:9)' "$L" 2>/dev/null | head -1 | cut -d: -f1)"
tests/v0332-emu-run.sh:340:t $? "[윈 rotate] 1.1.3 = 인자+env · 1.1.2 = env 만(옛 cys 가 모르는 인자로 실패하지 않게)" "113[$(cat "$BASE/st-rw113/rotcalls" 2>/dev/null)] 112[$(cat "$BASE/s
tests/login-keep-run.sh:202:t $? "[맥] ⓚ 남길 자리를 못 열면 ~/.cys 를 하나도 안 지우고 못 지움 1" "$(tail -3 "$BASE/mac-k/out.txt" | tr '\n' '|')"
tests/v0318-mutate.py:47:     "    $b0 = Test-CysBody\n    if ($b0.Body) { Say '[6/10] cys 가 이미 설치돼 있습니다 — 건너뜁니다.'; return 0 }\n    if ($false) {\n        $have0 = Get-Cy
tests/v0318-mutate.py:84:    # ⑥ [7/10] 의 호출이 빠지면 새 창에서 cys 를 못 찾는다
tests/d5-f3w-no-false-done-when-blocked.sh:78:  grep -q '설치가 끝나지 않았습니다 — 「cys 설치 파일 받기」 단계에서 멈췄습니다' "$BASE/say-$n" || bad "[$n] 결과 줄 「설치가 끝나지 않았습니다 — 「cys 설치 파일 받기」 …」가 없
tests/remote-help-ps1-static.py:180:    # D1 기각 — ReachedWake 는 깨우기가 끝까지 간 세 자리에만: ①cys 창을 열었다 ②자리 선점(claim-denied · 0.3.28) — 자비스는 이미 앱 안에 있고
tests/remote-help-ps1-static.py:188:       and re.search(r"if \(\$null -ne \$seatRc -and \$seatRc -eq 0 -and \$ref -match 'surface:'\) \{\n\s+Say \"     cys 안에서 자비스를 열었습니
tests/version-line-run.sh:36:n_old=$(( $(grep -vE '^\s*#' "$BS" | grep -c 'cys 가 답합니다') + $(grep -vE '^\s*#' "$BP" | grep -c 'cys 가 답합니다') ))
tests/version-line-run.sh:37:[ "$n_old" -eq 0 ]; t $? "[두 OS] 옛 「cys 가 답합니다」 줄 0" "남음 $n_old"
tests/version-line-run.sh:38:! grep -vE '^\s*#' "$BS" | grep -q 'cys 가 답하는데'; t $? "[맥] 어긋남 줄도 이름 없이" "옛 줄 남음"
tests/reinstall-keepapp-mutate.py:36:    # 편성 기록 지우기가 빠지면 프로그램 폴더 안의 topology.json 등이 남는다 → cys 가 켜지자마자 지난 동료 좌석을 되살린다(2026-09-15 윈 2차 재설치).
tests/d5-f12-wall-clock-wait.sh:90:grep -q '^rc=' "$BASE/out-dl" || { echo "잴 수 없음: step_download_cys 가 돌아오지 않았다" >&2; tail -3 "$BASE/out-dl" >&2; exit 2; }
tests/wake-env-run.sh:75:# ⓔ 맥 행동 — cys 가 없어 이 창에서 띄우는 갈래를 실제로 돌린다(step_wake → exec 가짜 claude)
tests/v0332-mutate.py:35:     '        Say \'     cys 안에서 열지 못했습니다. 프로그램이 답한 내용은 이렇습니다:\'\n        foreach ($ln in ($ref -split "`n")) { if ($ln.Trim()) { Say "       $ln
tests/login-seed.py:187:    print("이 기계에는 cys 가 실제로 깔려 있습니다: " + " · ".join(live), file=sys.stderr)
tests/awaken-emu/fleet.ps1:58:# 자식 자리 세션 기록(jsonl) 자리 = $env:USERPROFILE/.cys/claude/projects — 가짜 cys 가 SB/home 아래에 만든다(installer-awaken-jsonl)
```

### 4-5. 고칠 화면 줄 목록 — ai-jarvis `site/install/` 사본 기준(정본 jarvis-install 과 바이트 동일)
추출식: 출력 함수(say·printf·row·Say·Add-Row·Write-Host) 줄 중 제품 낱말 `cys` + 뒤 글자 · 주석 줄 제외. `next/` 사본(bootstrap.sh·.ps1 · reset-clean.ps1)은 같은 문구가 같은 수(48·33·16)로 있다.

#### site/install/bootstrap.sh — 48줄
```
1143:  printf '%s\n' "   1) Command(⌘)+스페이스를 누르고 터미널 이라고 치신 뒤 [터미널] 을 여십시오 (맥 터미널 앱 · 검은 창 — cys 창이 아닙니다)."
1309:    J-AV-02)    printf '%s\n' '백신의 보호 기록(격리함)에 cys 설치 파일이 있으면 [복원]을 골라 주십시오.' \
1819:  row "1-4" "cys 상태" "$cys_state (앱=$cysapp · 명령=${cyscmd:-없음} · 계정 준비=$cys_onboard)" "$cys_enum" "$cys_note"
1857:  row "1-8" "cys 실행 링크" "$link_state" "$link_enum" "$link_note"
1889:    row "2-*" "cys 이후 전 행" "-" "unknown" "cys 명령이 아직 없습니다 — 다음 단계에서 합니다"
1958:      printf -- '- ⓘ **cys 를 직접 열어 켰습니다.** %s\n' "$(cys_autostart_words "$AUTOSTART_STATE")"
1959:      printf -- '  다음에 컴퓨터를 켜시면 **cys 를 한 번 열어 주시면** 됩니다 — 그러면 그때부터 다시 돕니다. 따로 하실 일은 없습니다.\n'
1974:      printf -- '- 명령은 **맥 터미널 앱(검은 창)** 에서 실행하십시오 — cys 창이 아닙니다.\n'
1978:      printf -- '- 이제 **cys 창의 master 자리** 에서 자비스와 이어서 이야기하시면 됩니다. 설치 창(검은 터미널)은 닫으셔도 됩니다.\n'
3108:      say "[5/10] cys 설치 파일을 받습니다 (약 $((CYS_MAC_BYTES / 1000000))MB · 잠시 걸립니다)."
3110:      say "[5/10] cys 설치 파일을 받습니다 (잠시 걸립니다)."
3237:      say "     깔려 있는 cys ${v} 는 앱 안에서 업데이트할 수 없는 옛 판입니다 — 이번 설치에서 새 판(${CYS_DISPLAY_NAME} ${CYS_FORK_VERSION})으로 다시 설치합니다(하실 일은 없습니다)."
3246:      say "[6/10] cys 가 이미 설치돼 있습니다 — 건너뜁니다."
3254:      say "[6/10] cys 가 이미 설치돼 있습니다 (판본 ${CYS_FORK_VERSION} 확인) — 건너뜁니다."
3340:    say "[6/10] 이 창이 cys 안에서 열려 있어 cys 를 바꿔 넣을 수 없습니다(바꾸는 동안 이 창도 꺼집니다)."
3344:  say "[6/10] cys 를 설치합니다 (풀어서 넣습니다 · 1분쯤 걸립니다)."
3376:      { [ -d "$CYS_OLD_APP" ] || [ -d "$CYS_FORK_APP" ]; } && say "     전에 있던 cys 는 그 자리에 그대로 있습니다."
3390:    say "     돌고 있는 cys 가 있으면 먼저 끕니다."
3437:    say "[6/10] cys 를 프로그램 폴더에 넣지 못했습니다 (종료 코드 $rc)."
3438:    { [ -d "$CYS_OLD_APP" ] || [ -d "$CYS_FORK_APP" ]; } && say "     전에 있던 cys 는 그 자리에 그대로 있습니다."
3447:  [ -d "$prev" ] && say "     전에 있던 cys 는 한 벌 남겨 두었습니다: $(redact "$prev")"
3448:  [ -d "$oldprev" ] && [ ! -d "$CYS_OLD_APP" ] && say "     옛 이름의 cys(cys.app)는 한 벌 남겨 두었습니다: $(redact "$oldprev")"
3451:    say "     옛 이름의 cys($CYS_OLD_APP)를 옮기지 못해 그 자리에 남았습니다 — 새 판은 $CYS_FORK_APP 입니다(쓰시는 데 지장은 없습니다)."
3455:    say "[6/10] 넣은 뒤 실행해 보았더니 cys 가 실행되지 않습니다 (${CYS_APP_EXEC_WHY}) — 설치가 확인되지 않았습니다."
3467:  say "[6/10] cys 를 설치합니다."
3622:    off)   printf '%s\n' "자동 시작 등록은 있는데 꺼져 있습니다 — 컴퓨터를 켜실 때 cys 를 한 번 열어 주십시오." ;;
3672:    say "[7/10] (dry-run) cys 를 확인하지 않았습니다."
3676:    say "[7/10] cys 프로그램을 찾지 못했습니다."
3679:  say "[7/10] cys 프로그램을 찾았습니다: $(cys_app_dir)"
3871:    say "     cys 가 이미 돌고 있고 자동 시작도 등록돼 있어(LaunchAgent ${CYS_LAUNCHD_LABEL}) 그대로 둡니다."
3911:        [ "$AUTOSTART_STATE" = "yes" ] || say "     다음에 컴퓨터를 켜시면 cys 를 한 번 열어 주시면 됩니다. 그러면 그때부터 다시 돕니다."
4318:  say '   │   cys 창의 master 자리에 이렇게 입력해 주십시오:              │'
4329:  say '   cys 창의 master 자리를 열어 자비스가 무엇을 하고 있는지 보아 주십시오.'
4393:    say "     cys 창에서 자비스에게 이렇게 말해 주십시오: $FLEET_TRIGGER"
4399:    say "     cys 창에서 자비스에게 이렇게 말해 주십시오: $FLEET_TRIGGER"
4447:      say '   (설치 창을 닫아도 자비스 창은 그대로 둡니다 — 이어서 cys 창의 자비스와 이야기하시면 됩니다.)'
4473:    say "   │   cys 창의 master 자리에 이렇게 입력해 주십시오: │"
4479:    say "   cys 창 = 방금 열린 cys 앱 창입니다(이 검은 터미널 창이 아닙니다). 안 보이면 Dock 의 cys 아이콘을 누르십시오."
4532:    say "     오래 서지 않으면 cys 창의 자비스에게 무엇이 걸렸는지 물어보십시오."
4536:    say "     아직 그 한마디를 입력하지 않으셨다면, cys 창에서 지금 입력해 주시면 됩니다."
4537:    say "     치셨는데도 서지 않았다면 cys 창의 자비스에게 물어보십시오 — 무엇이 걸렸는지 사람 말로 알려 줍니다."
4880:      say "     여는 파일의 경로를 쓸 수 없어 cys 안에서는 열지 못합니다. 이 창에서 띄웁니다."
4893:        [ "$CYS_APP_OPENED" = "1" ] && say "     cys 앱 창을 열었습니다 — 자비스는 그 창의 master 자리에서 깨어납니다."
4894:        say "     cys 안에서 자비스를 열었습니다 ($ref). cys 창에서 이어서 이야기하십시오."
4975:    say "     cys 안에서 열지 못했습니다. 프로그램이 답한 내용은 이렇습니다:"
4978:    say "     cys 창 안에서 이어서 하고 싶으시면, cys 를 열고 그 안에서 아래 한 줄을 입력해 주십시오:"
5018:    say "     cys 앱 창을 자동으로 열지 못했습니다 — 응용 프로그램 폴더에서 $(basename "$app") 을 열어 주십시오(자비스는 그대로 깨웁니다)."
6089:for st_row in '5/10|cys 설치 파일 받기|step_download_cys' '6/10|cys 설치|step_install_cys' \
```

#### site/install/bootstrap.ps1 — 33줄
```
1227:            Say ("     깔려 있는 cys $v 는 앱 안에서 업데이트할 수 없는 옛 판입니다 — 이번 설치에서 새 판($CysDisplayName $CysVersion)으로 다시 설치합니다(하실 일은 없습니다).")
1512:        Add-Row '1-4' 'cys 상태' "등록만 남음 $cysVal" 'blocked' '**설치 목록에는 있는데 프로그램 실체가 없다** — 지난 설치가 끝까지 못 갔거나 지워졌다. **재설치로 풀린다**(다음 단계에서 합니다)'
1514:        Add-Row '1-4' 'cys 상태' "없음 $cysVal" 'ok' '깨끗한 기계의 정상값이다 (고장 아님)'
1516:        Add-Row '1-4' 'cys 상태' "앱+온보딩 $cysVal" 'ok' '이 계정에 이미 자리를 잡았다'
1518:        Add-Row '1-4' 'cys 상태' "앱만 $cysVal" 'blocked' '프로그램은 이 컴퓨터에 있으나 **이 계정에는 아직 자리를 안 잡았다** — 계정 단위 준비가 남았다'
1520:        Add-Row '1-4' 'cys 상태' "판정 불가 $cysVal" 'unknown' '드문 조합입니다 — 왼쪽 값을 그대로 보여 드립니다'
1589:        Add-Row '1-8' 'cys 실행 링크' '등록 → 빈 자리' 'blocked' '설치 목록이 가리키는 자리에 실행 파일이 없습니다'
1591:        Add-Row '1-8' 'cys 실행 링크' '-' 'unknown' '이 컴퓨터에서는 확인할 것이 없습니다'
1605:        Add-Row '2-*' 'cys 이후 전 행' '-' 'unknown' $why
3490:            if (($cs0 -eq 'match') -and ($gone.Count -eq 0)) { Say "[5/10] 같은 판(v$CysVersion)의 cys 가 이미 설치돼 있습니다 (지문 확인) — 받지 않고 건너뜁니다."; return 0 }
3494:        } elseif (-not $have0) { Say '[5/10] 설치된 cys 의 판본을 읽지 못해 있는 것을 그대로 씁니다 — 받지 않고 건너뜁니다.'; return 0 } else { Say "[5/10] 설치된 cys 는 v$have0 입니다 — v$CysVersion 을 
3522:        Say "[5/10] cys 설치 파일을 받습니다 (약 132MB · 잠시 걸립니다)."
3629:                if ($gone.Count -eq 0) { $script:CysBodyDir = [string]$b0.Path; [void](Clear-CysStaleInstallMemory $script:CysBodyDir); Say "[6/10] cys 가 이미 설치돼 있습니다
3636:        if (-not $have0) { $script:CysBodyDir = [string]$b0.Path; [void](Clear-CysStaleInstallMemory $script:CysBodyDir); Say '[6/10] cys 가 이미 설치돼 있습니다 — 판본을 읽지 못해 있
3675:    elseif ($refresh) { Say "[6/10] 같은 판(v$CysVersion)을 이번 판 파일로 덮어 설치합니다 (깔린 파일이 이번 판과 같다고 확인되지 않았습니다)." } elseif ($upgradeFrom) { Say "[6/10] cys 를 v$upgradeFrom 에
3734:    if ($oldLeft) { Say ('     쓰시던 cys(v' + $upgradeFrom + ')의 명령 파일(cys.exe)은 그대로 있습니다.') }
3757:    if ($Mode -eq 'dry') { Say '[7/10] (dry-run) cys 를 확인하지 않았습니다.'; return 0 }
3765:    if (-not $b.Body) { Say '[7/10] cys 프로그램을 찾지 못했습니다.'; return 7 }
3766:    Say "[7/10] cys 프로그램을 찾았습니다: $(Redact $b.Path)"
3866:        Say '     cys 가 이미 돌고 있고 자동 시작도 등록돼 있어(작업 이름 cysd) 그대로 둡니다.'
3918:                    Say '     다음에 컴퓨터를 켜시면 cys 를 한 번 열어 주시면 됩니다. 그러면 그때부터 다시 돕니다.'
4426:        Say "     ($($script:BlockedStep) 이(가) 끝나지 않아 cys 안에는 아직 열 수 없습니다. 이 창에서 띄웁니다.)"
4462:            Say '     여는 파일의 경로를 쓸 수 없어 cys 안에서는 열지 못합니다. 이 창에서 띄웁니다.'
4483:            Say "     cys 안에서 자비스를 열었습니다 ($ref). cys 창에서 이어서 이야기하십시오."
4566:        Say '     cys 안에서 열지 못했습니다. 프로그램이 답한 내용은 이렇습니다:'
4572:        Say '     cys 창 안에서 이어서 하고 싶으시면, cys 를 열고 그 안에서 아래 한 줄을 입력해 주십시오:'
5059:    Say '   │   cys 창의 master 자리에 이렇게 입력해 주십시오:              │'
5079:    Say '   cys 창의 master 자리를 열어 자비스가 무엇을 하고 있는지 보아 주십시오.'
5104:        Say "     cys 창에서 자비스에게 이렇게 말해 주십시오: $FleetTrigger"
5113:        Say "     cys 창에서 자비스에게 이렇게 말해 주십시오: $FleetTrigger"
5169:    Say ("   │   cys 창의 master 자리에 이렇게 입력해 주십시오: │")
5232:        Say '     아직 그 한마디를 입력하지 않으셨다면, cys 창에서 지금 입력해 주시면 됩니다.'
5233:        Say '     치셨는데도 서지 않았다면 cys 창의 자비스에게 물어보십시오 — 무엇이 걸렸는지 사람 말로 알려 줍니다.'
```

#### site/install/reset-clean.sh — 18줄
```
216:    table="$(printf '%s\n%s\t%s\t%s' "$table" "$pid" "$tok" "(cys 가 띄운 자식)")"
430:    [ -d "$CYS_APP" ] && say "  [있음] cys 프로그램 · $CYS_APP (남깁니다 — 다시 깔 때 판을 확인해 그대로 쓰거나 바꿉니다)" \
431:                      || say "  [없음] cys 프로그램 · $CYS_APP"
432:    [ -n "$CYS_APP_OLD" ] && say "  [있음] cys 프로그램(옛 이름) · $CYS_APP_OLD (남깁니다 — 다시 깔 때 새 이름으로 바꿔 넣으며 한 벌 보관합니다)"
434:    [ -d "$CYS_APP" ]; row $? 'cys 프로그램' "$CYS_APP"
435:    if [ -n "$CYS_APP_OLD" ]; then [ -d "$CYS_APP_OLD" ]; row $? 'cys 프로그램(옛 이름)' "$CYS_APP_OLD"; fi
440:  if [ "$KEEP_HISTORY" = "1" ]; then [ -d "$HOME/.cys" ]; row $? 'cys 계정 자리(로그인·이전 대화·부서 기록은 제자리로 되옮기고 나머지는 보관합니다)' "$HOME/.cys"
441:  else [ -d "$HOME/.cys" ]; row $? 'cys 계정 자리(보관 폴더로 옮깁니다)' "$HOME/.cys"; fi
443:  if [ "$KEEP_HISTORY" = "1" ] || [ "$KEEP_APP" = "1" ]; then [ -d "$HOME/.local/state/cys" ]; row $? 'cys 실행 상태(지난 편성 기록만 보관합니다)' "$HOME/.local/state/cys"
444:  else [ -d "$HOME/.local/state/cys" ]; row $? 'cys 실행 상태(보관 폴더로 옮깁니다)' "$HOME/.local/state/cys"; fi
542:    say "         ⚠이것은 위의 「cys 계정 자리」 안에 들어 있어 그 자리와 함께 옮겨지거나 새로 만들어집니다(cys 설치의 일부입니다)."
1898:    say "  🔴남음: cys 프로그램 — 아직 실행 중이라 옮기거나 지울 수 없어 이번에는 아무것도 옮기지 않았습니다."
1900:    say "         cys 창을 모두 닫아 주십시오 — 닫힌 뒤 다시 해 보면 이어서 옮깁니다(자료는 원래 자리에 그대로 있습니다)."
1902:    say "  [주의] cys 자리에서 아직 돌고 있는 것이 있습니다 — 폴더가 안 지워질 수 있습니다."
1995:    say "  [남김] $(short "$JARVIS_HOME") — cys 가 아직 돌고 있어 이번에는 옮기지 않았습니다(다음에 그대로 옮깁니다)."
2072:      say "  [남김] cys 프로그램 · $CYS_APP (다시 깔 때 판을 확인해 그대로 쓰거나 바꿉니다)"
2073:      [ -n "$CYS_APP_OLD" ] && say "  [남김] cys 프로그램(옛 이름) · $CYS_APP_OLD (다시 깔 때 새 이름으로 바꿔 넣으며 한 벌 보관합니다)"
2176:  say "cys 를 곧 끕니다. 저장하지 않으신 것이 있으면 지금 저장해 주세요."
```

#### site/install/reset-clean.ps1 — 16줄
```
883:        Write-Host '  [남김] cys 프로그램 — 프로그램 파일은 지우지 않고 그대로 둡니다(다시 깔 때 이 프로그램을 씁니다)'
887:        [void](Row 'cys 프로그램(프로그램 파일은 지우고, 안의 실행 기록은 보관 폴더로 옮깁니다)' $CysDir)
888:        [void](Row 'cys 프로그램(옛 자리)' $CysDirOld)
920:        [void](Row 'cys 설치 목록 항목(우리 설치 자리를 가리킬 때만 지웁니다)' $RegKeyR)
921:        [void](Row 'cys 설치 목록 항목(옛 이름 · 우리 설치 자리를 가리킬 때만 지웁니다)' $RegKey)
927:    if ($KeepHistory) { [void](Row 'cys 계정 자리(로그인·이전 대화·부서 기록은 제자리로 되옮기고 나머지는 보관합니다)' $CysHome) }
928:    else { [void](Row 'cys 계정 자리(보관 폴더로 옮깁니다)' $CysHome) }
988:        Write-Host '         이것은 위의 「cys 계정 자리」 안에 들어 있어 그 자리와 함께 옮겨지거나 새로 만들어집니다(cys 설치의 일부입니다).'
1860:        Write-Host '  [남음] cys 설치 목록 항목·설치 위치 기록·자동 실행 값 - 남겨야 할 자리를 확인하지 못해 프로그램과 함께 그대로 두었습니다.'
2269:        Write-Host ('  [남음] cys 프로그램 — 아직 실행 중이라 옮기거나 지울 수 없어 이번에는 아무것도 옮기지 않았습니다(' + $alive.Count + '가지).')
2271:        Write-Host '         cys 창을 모두 닫아 주십시오 — 닫힌 뒤 다시 해 보면 이어서 옮깁니다(자료는 원래 자리에 그대로 있습니다).'
2273:        Write-Host ('  [주의] cys 자리에서 아직 ' + $alive.Count + '개가 돌고 있습니다 — 지난 편성 기록이 안 옮겨질 수 있습니다.')
2371:        Write-Host ('  [남김] ' + (Short $JarvisDir) + ' - cys 가 아직 돌고 있어 이번에는 옮기지 않았습니다(다음에 그대로 옮깁니다).')
2454:            Write-Host '  남김: cys 프로그램 (재설치 — 지우지 않고 그대로 씁니다)'
2455:            if ($hasRegEntry -or (Test-Path $RegKeyR)) { Write-Host '  남김: cys 설치 목록 항목 (프로그램과 한 쌍이라 함께 둡니다)' }
2566:    Write-Host 'cys 를 곧 끕니다. 저장하지 않으신 것이 있으면 지금 저장해 주세요.'
```

#### site/install/reinstall.sh — 1줄
```
131:    say "지우기는 끝났으므로, 이 컴퓨터는 지금 「cys 프로그램만 남고 나머지는 안 깔린 상태」입니다."
```
