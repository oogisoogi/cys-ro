# HANDOFF — TICKET=cysr-1111-installer (1.1.11 · 같은 판 재설치 결함)

- 가지: `fix/1111-installer` ← rel/1.1.10 `3ce93329` · 좌석 worker@surface:1573 · 2026-10-22 14:00 ~
- 지시: 브리프 `docs/briefs/2026-10-22-cysr-1111-installer.md`(원장 14:00:05 · spawn 경로 · body sha256 `798e2e6a…` 대조 일치).
- push · 태그 · 판번 · 설치 · 발행 · rel/1.1.10 쓰기 · 윈 기기 접촉 · bootstrap.ps1 수정 = **0**.
  (bootstrap.ps1 은 읽기만 · 원본 sha256 `12c8eca6…0242` 작업 전후 동일 · 패치는 아래 §4 diff 로만.)

## 0. 한눈에

| # | 건 | 판정 · 조치 | 커밋 | 적 → 녹 · 뮤턴트 |
|---|---|---|---|---|
| A | 설치기 내용 오라클 | CYS_PLACE ① 판번 단락 폐기 → ④-b **내용 오라클**(정식 ↔ 방금 푼 `.new` 크기 + SHA-256). 같은 바이트 = 무행동 · 다르거나 판정 불가 = 정상 배치로 교체 | `b14d825e` | 모델 S3c 적(깨끗한 길 exit 0 + cys/cysd SAMEVER 잔존) → 녹 84011 상태 · 하네스 N9·N10 · 뮤턴트 5/5 적 |
| B | runtime 매니페스트 밖 dist-info | 설치 성공 갈래에서 **같은 배포 이름의 다른 판** dist-info 만 정리하는 도우미 | `ead6a3a1` | N11 e2e: 봉인 rc 1 → 정리 → rc 0 · 뮤턴트 5/5 적 |
| C | 같은 판·같은 release_seq 이중 게시 | 자동 갱신 보관소 = **막혀 있음** · GitHub 릴리스 = **열려 있었음** → draft-guard 를 공개 릴리스까지 확장 | `374d98ef` | test_release_trigger_split 적 2 → 녹 16/16 · 뮤턴트 4/4 적 |
| D | bootstrap 핀(조사만) | 완료 판정·핀 표지가 판번만 본다 → build_id 대조 패치안(diff) | — (다른 저장소) | 패치 사본 파서 오류 0 · lib 모드 행동 3종 확인 |

## 1. A — 설치기 내용 오라클 (`src-tauri/nsis-hooks.nsh` · `src-tauri/nsis/cys-samebytes.ps1`)

### 결함 (재현)
- `CYS_PLACE` ①이 `CYS_ORACLE`(VERSIONINFO 두 DWORD)가 「fresh」면 바로 끝냈다. 같은 판번 재빌드(1.1.10.0 == 1.1.10.0 · 다른 바이트)에서
  잠긴 cys/cysd 는 템플릿 `File` 이 `SetOverwrite try` 로 **무음 스킵** → 오라클은 옛 바이트를 「이번 빌드」로 읽음 → **exit 0 · 옛 바이트 잔존**.
- 재현 = 상태기계 모델(`scripts/tests/nsis-hook-model/model.py`)에 종류 `SAMEVER`(판번 같음·바이트 다름 · 세대로는 OLD)와
  시나리오 `S3c-samever-stale-running`(cys·cysd 이미지 잠금 · GUI 는 taskkill 로 풀림)을 넣어 수리 전 훅 미러로 돌림:
  `INVARIANT VIOLATION in S3c-samever-stale-running: clean path: expected a prev slot for cys` · 종단 = `cys.exe SAMEVER · cysd.exe SAMEVER · exit=0`.

### 수리
- ① 판번 오라클 결과(`$R2`)는 들고만 간다(단락 없음).
- ②~④ 는 종전 그대로(stale `.new` 제거 → `.new` 추출 → 크기·판번 검증).
- **④-b(신설)**: 판번이 「fresh」였던 정식만 `powershell -File $PLUGINSDIR\cys-samebytes.ps1 <정식> <.new>` → `0` 이면 `.new` 지우고 무행동 성공
  (종전 단락과 같은 결과 · prev 0), 그 밖(`1` 다름 · `2` 판독 불가 · `error` 실행 불가)은 **fail-closed = 교체**(⑤~⑧ 정상 배치 —
  교체에 실패하면 종전 거부 토큰이 그대로 유음). 판별 로그 1줄(ASCII):
  `cys: <bin>.exe has this version but not this build's bytes (samebytes=<rc>) - replacing`.
- 도우미는 컴파일 때 `File` 로 싣는다(원본 부재 = 빌드 실패) · POSTINSTALL 첫 `CYS_PLACE` 앞에서 `$PLUGINSDIR` 에 푼다.
- 도우미 읽기 = `FileShare ReadWrite+Delete`(실행 중 이미지도 읽힘) · 순수 ASCII(PS 5.1 은 BOM 없는 스크립트를 ANSI 로 읽음).
- 브리프의 「`SetOverwrite try` 무음 스킵 → 실패 표지/로그」는 이 오라클로 닫힌다: 스킵된 잠긴 정식은 이제 내용 불일치로 잡혀
  잠금 무관 배치(rename)로 교체되고, 그마저 실패하면 기존 `placement-refused:` 토큰 + exit 4(유음). `SetOverwrite try` 자체는 그대로(runtime 잔여용).

### 시험
| 시험 | 결과 |
|---|---|
| 모델(`model.py`) | **84011** 종단 상태 · I1/I3/I4 전부 유지 · 심층 레인 핀 **38/38**(신설 `lane:SAMEBYTES-EQUAL` 33537 · `lane:SAMEBYTES-DIFFER` 28761) · GUARD_PIN 재핀 |
| 컴파일 하네스(`nsis-hook-compile/run.sh`) | makensis v3.12 `-WX` 컴파일 OK · N1~N8 OK · **N9**(판번 결과는 `.new` 추출 뒤 ④-b 관문에서 처음 소비 · exit "0" 관문 · 도우미 선적재 · ASCII) · **N10**(도우미 pwsh 실행: 같음 0 · 다름 1 · 크기 다름 1 · 파일 없음 2 · 인자 없음 2) |
| `nsis-template/check.py` | OK |

뮤턴트(전부 적):
| # | 변이 | 잡은 곳 |
|---|---|---|
| M-A1 | 훅에 판번 단락 복원 | N9 + 모델 guard(exit 2) |
| M-A2 | 판정 불가를 같음으로(fail-open) | N9 + 모델 guard |
| M-A3 | 미러: 판번 같음 = 바이트 같음 | 모델 S3c I1 위반 |
| M-A4 | 도우미 catch 가 0 | N10(missing=0) |
| M-A5 | 도우미 미선적 | N9(shipped at=빈 값) + 모델 guard |

부수: 하네스 N9 진단 변수에 `|| true` — `pipefail` 아래 빈 grep 이 진단 없이 스크립트를 죽이던 것(M-A5 첫 측정에서 실측).
`docs/WINDOWS-UPGRADE-ATOMICITY-CHECKLIST.md` 의 「오라클 단락(①)」 서술 6곳을 ④-b 로 정정 · 사라진 앵커 `cys_pl_need` → `cys_pl_extract`(N6).
`unused label` 이 `-WX` 에서 치명이라(makensis 실측 warning 6012) `cys_pl_need_` 라벨은 지웠다.

## 2. B — 매니페스트 밖 dist-info 정리 (`src-tauri/nsis/cys-runtime-prune.ps1`)

- 원인(winseal HANDOFF §1 재확인): 설치기는 `runtime\` 을 비우지 않고 파일 단위로 덮어 펼친다 → 패키지 판이 바뀌면 옛
  `<이름>-<판>.dist-info` 가 남아 runtime-seal 「추가」(10-22: `pip-26.2.2.dist-info` → FAIL 32).
- 택한 길 = **설치기가 정리**(봉인 판독기는 「자동 삭제 0」 계약 · 봉인이 잔재를 봐주게 하면 변조 탐지가 약해진다).
- 지우는 것은 하나뿐: runtime-manifest 에 **없는** dist-info 폴더 중, 매니페스트가 **같은 부모 폴더에 같은 배포 이름(pip 정규화 —
  대소문자 무시 · `-_.` 동일)의 다른 판**을 싣고 있는 것.
- 무접촉: 패키지 코드 · 매니페스트에 없는 이름(사용자 pip 설치분 — 봉인이 계속 보고) · 링크이거나 링크를 품은 폴더(PS 5.1 의
  `-Recurse` 가 정션을 따라갈 수 있어 직접 걸어 확인) · 매니페스트 부재(무행동 · `skipped` 1줄).
- 매니페스트는 텍스트로 훑는다(PS 5.1 `ConvertFrom-Json` 2MB 한계) — 오탐은 「덜 지우는」 쪽으로만 난다.
- 훅: `cys_post_ok` 뒤(성공 갈래)에서만 실행 · 결과 1줄 `cys-runtime-prune: stale-dist-info removed=N failed=M kept-unshipped=K` 상세 로그 · 설치 결과 불변.
- 모델: 정식·실패 파일·표지·종료코드 무접촉이라 무관 판정 주석 + 재핀.

| 시험(N11 · pwsh 실행) | 결과 |
|---|---|
| 정적: `cys_post_ok` < 선적 < 호출 · 호출 1회 · ASCII | OK |
| 실 `javis_runtime_seal.py emit` → 잔재(pip-26.2.2 + 대소문자 변형 setuptools-79.0) → **verify rc 1** | 재현 |
| 도우미 실행 → **verify rc 0** · 요약 `removed=2 failed=0` | OK |
| 음성: 사용자 dist-info · 패키지 코드 파일 · 링크 dist-info · 링크 품은 dist-info · 링크 대상 · 무매니페스트 skip 줄 | 전부 생존/확인 |

뮤턴트(전부 적): M-B1 지우기 무력화 · M-B2 이름 규칙 제거(사용자 dist-info 삭제) · M-B3 링크 가드 제거 · M-B4 무매니페스트 가드 제거
(처음엔 **생존** — 가드가 없어도 `ReadAllText($null)` 예외가 catch 로 빠져 결과가 같은 등가 뮤턴트 → skip 줄 단언을 더해 적) · M-B5 실패 갈래로 이동.

## 3. C — 같은 판·같은 release_seq 이중 게시

| 경로 | 판정 | 근거 |
|---|---|---|
| 자동 갱신 보관소(`/update/` · R2) | **막혀 있다** | `scripts/update/release-gate.py` body: 같은 seq 다른 바이트 = 거부 · 새 seq = 최댓값 + 1 만 · `scripts/update/publish-site.py` `plan`: 같은 거부(덮어쓰기 rc 3) |
| GitHub 릴리스(setup.exe 공개 배포처) | **열려 있었다** | `release.yml` draft-guard 선택식이 `.draft and .tag_name == env.TAG` — 공개 릴리스는 셈 밖. 고정 tauri-action `84b9d35b` `src/create-release.ts` 는 `releaseDraft: true` 여도 **모든 릴리스**에서 `tag_name` 을 찾아 공개본을 집고, `src/upload-release-assets.ts` 가 같은 이름 자산을 지운 뒤(`Deleting existing …`) 다시 올린다 · 팩 자산은 `gh release upload --clobber` |

⇒ 공개 뒤 같은 태그로 전체 재실행·수동 실행하면 `vars.CYSR_RELEASE_SEQ` 그대로 = **같은 판·같은 seq 의 다른 바이트**가 공개 setup.exe 를 교체
(VERSIONINFO 4마디 = 판 + seq 가 같아 설치기 판번 오라클이 못 가르는 계급 — A 와 같은 뿌리).

수리: 가드가 같은 태그 릴리스 **전부**를 보고, 공개본이면 별도 사유로 중단(draft 사유 유지 · 조회 실패 = 멈춤 그대로).
- **【결정 1건 — 지시 없이 내가 내린 판단】** 기존 시험 `test_23` 의 단언 「published 같은 태그 = 진행(0)」을 「멈춤(1)」으로 **뒤집었다**.
  그 단언은 1.1.9 B1 2판(codex MINOR ⑫ 실행 시험 · `23fe88aa`)에서 draft 전용 선택식의 동작을 기록한 것이며 근거 서술은 없다.
  재태그 금지(release-pipeline-map §10-10)와 같은 방향이라 뒤집었다. 공개 뒤 같은 태그 재생산이 필요한 흐름이 따로 있다면 되돌릴 대상이다.
- 시험: 적 2(선택식 핀 · 2페이지 공개 같은 태그) → 녹 16/16. 뮤턴트 4/4 적(공개 갈래 끔 · 공개 표지 누락 · draft 전용 선택식 복귀 · 공개 수 0 고정).
- 범위 밖(보고만): **다른 판·같은 seq**(master 가 vars 를 안 올리고 다음 판 태그) — GitHub 릴리스는 막지 않지만 보관소 게이트가 두 번째 본문을 거부하고,
  VERSIONINFO 는 판 마디가 달라 설치기 오라클은 가른다.

## 4. D — bootstrap 핀 (조사만 · `~/axdev/ai-jarvis/site/install/bootstrap.ps1` 무수정)

대상 = 사이트 사본(설치기 0.3.41 · cysr 핀 1.1.9 · 저장소 최신 커밋 `0731e51`).

**결함**: 6/10 단계 완료 고리(`:3727-3733`)가 `cys.exe` ProductVersion == `$CysVersion`(+ 같은 판이면 설치기 exit 0)만 보고 `$done` →
`:3739` `Save-CysPinStamp` 가 **그때의 cys.exe 지문**을 이번 핀(`setup_sha256`)에 묶어 `jarvis-cys-pin.json` 에 쓴다.
설치기가 잠긴 같은 판 cys.exe 를 못 바꾸고 0 을 답하면(10-22 kit B = A 의 결함) **옛 바이트 지문이 이번 핀 표지로 박힌다** →
다음 실행 `Get-CysContentState`(`:1263-1275`)가 setup 지문 같음 + exe 지문 같음 = `'match'` → **그 핀 동안 영영 건너뜀**.
(A 수리 뒤의 설치기는 스스로 교체하지만, 옛 설치기·설치기의 거짓 0 에 대한 바깥 방어선이 bootstrap 에 없다.)

**패치안**: 핀에 `$CysWinBuildId` 를 더하고, ⑴ 완료 고리는 판번 조건이 맞을 때 `cys.exe phoenix-identity` 의 `build_id` 가 핀 값일 때만 끝,
⑵ 핀 표지는 build_id 가 핀 값일 때만 쓰고 표지에 `build_id` 를 남긴다. 화면 문구 변경 0(로그 줄만).
- build_id 출처 일치 확인: `phoenix-identity`(`src/bin/cys.rs` Command::PhoenixIdentity) · `build-info`(`src/update/buildinfo.rs:60`) 모두
  `crate::pack::build_id()` = 빌드 env `CYSR_BUILD_ID`(`<커밋12>.<UTC시각>`) → 자동 갱신 본문 windows-x64 행 `build_id`(`make-release-json.py` 가 build-info 에서 채움).
- ⚠build-info 는 공개 릴리스 자산이 아니라 릴리스 런 아티팩트(`update-inputs-windows-x64`)다 → `win-pin-release.sh` 처럼 릴리스를 때려 대조하는 시험은
  지금 재료로는 못 만든다(본문 또는 아티팩트를 읽는 대조 = 후속).
- 측정 불가(백신이 cys.exe 실행을 막음 등) = 완료 아님 → 「새 프로그램을 넣지 못했습니다」 갈래(엄격 쪽). 완화가 필요하면 master 판단.
- 검증(사본 · 맥 pwsh): 파서 오류 0(원본도 0) · `JARVIS_LIB_ONLY=1` 로 사본을 읽어 가짜 cys 로 — 핀 일치 = 표지 씀(True) · 다른 build_id = 표지 안 씀 + 로그 1줄 ·
  없는 exe = `''`.

```diff
--- a/site/install/bootstrap.ps1
+++ b/site/install/bootstrap.ps1
@@ -152,6 +152,11 @@
 $CysWinFile     = "cysr_${CysVersion}_x64-setup.exe"
 $CysWinBytes    = 152133980
 $CysWinSha256   = 'c351c1ab481238d24507a773be581f86d7beb486ef965006997fc4e56f9aebb4'   # 릴리스 v1.1.9 SHA256SUMS.txt 의 그 줄과 바이트 일치(tests/win-pin-release.sh 가 릴리스를 때려 다시 잰다)
+# ★(1.1.11 · cysr-1111-installer) 이번 핀 cys.exe 의 build_id(`cys phoenix-identity` · 컴파일 상수 `<커밋12>.<UTC시각>`).
+#   판번(ProductVersion)은 정체가 아니다 — 같은 판번 재빌드(10-22 kit B: 1.1.10 == 1.1.10 · 다른 바이트)를 가르는 값이 이것이다.
+#   출처 = 그 판 자동 갱신 본문(cysr-release-<seq>.json)의 windows-x64 행 build_id — make-release-json.py 가 릴리스 런 아티팩트
+#   update-inputs-windows-x64 의 build-info(설치된 cys.exe 가 말한 값)에서 채운다. 판을 올릴 때 함께 올린다(대조 시험 = 후속).
+$CysWinBuildId  = '<핀 판 본문 windows-x64 행의 build_id>'
 $CysDownloadUrl = $CysDownloadDir + $CysWinFile
 
 $LoginPollInterval = 2     # 초 — 승인 프로세스가 끝난 뒤 로그인을 다시 확인하는 간격
@@ -1129,6 +1134,13 @@
 #   (1.1.6 발행 자산 · 1.1.7 빌드 실측 · 0.3.38).
 function Get-CysExeVersion($path) {
     try { return [string](Get-Item -LiteralPath $path -ErrorAction Stop).VersionInfo.ProductVersion } catch { return '' }
+}
+# (1.1.11 · cysr-1111-installer) cys.exe 가 스스로 말하는 build_id — 데몬 불요(phoenix-identity = 컴파일 상수 출력) · 상한 10초 · 못 읽으면 ''.
+function Get-CysExeBuildId($path) {
+    if (-not $path -or -not (Test-Path -LiteralPath $path)) { return '' }
+    $o = Invoke-CysCapped $path 'phoenix-identity' 10000
+    if (-not $o) { return '' }
+    try { return [string]($o | ConvertFrom-Json -ErrorAction Stop).build_id } catch { return '' }
 }
 # 프로그램 파일 셋(명령줄 · 데몬 · 창)이 한 폴더에 다 있는가.
 function Test-CysDirHasBins($dir) {
@@ -1280,7 +1292,11 @@
     $exeSha = $null
     if ($b -and $b.Cli) { $exeSha = Get-CysFileSha256 $b.Cli }
     if (-not $sp -or ($null -eq $exeSha)) { Write-Log 'cys pin stamp: not written (cys.exe 지문을 못 쟀다)'; return $false }
-    $o = [ordered]@{ version = $CysVersion; setup_sha256 = $CysWinSha256; exe_sha256 = $exeSha; installer_version = $InstallerVersion; at = (Get-Date -Format o) }
+    # ★(1.1.11) 표지는 「이번 핀의 내용」이라는 주장이다 — cys.exe 의 build_id 가 핀 값이 아니면 쓰지 않는다(옛 바이트 지문을 핀에 묶지 않는다).
+    $bid = ''
+    if ($b -and $b.Cli) { $bid = Get-CysExeBuildId $b.Cli }
+    if ($bid -cne $CysWinBuildId) { Write-Log ('cys pin stamp: not written (build id ' + $(if ($bid) { $bid } else { '(unreadable)' }) + ' != pin ' + $CysWinBuildId + ')'); return $false }
+    $o = [ordered]@{ version = $CysVersion; setup_sha256 = $CysWinSha256; exe_sha256 = $exeSha; build_id = $bid; installer_version = $InstallerVersion; at = (Get-Date -Format o) }
     try { Write-TextNoBom $sp ($o | ConvertTo-Json); Write-Log ('cys pin stamp: written v' + $CysVersion + ' exe=' + $exeSha.Substring(0, 12)); return $true }
     catch { Write-Log ('cys pin stamp: write failed - ' + $_.Exception.Message); return $false }
 }
@@ -3726,15 +3742,23 @@
         #   끝 확인(0.3.38 ⓑ) = /D 자리에 프로그램 파일 셋 + cys.exe 파일 판 = 이번 판. 설치 목록·종료 코드의 말은 믿지 않는다
         #   (09-30 노트북: 설치 목록은 없는 폴더를 가리키며 1.1.6 이라 했다).
         #   같은 판 덮어 깔기는 설치 전 파일이 이미 조건을 만족한다 ⇒ 설치기가 스스로 끝나고 성공(0)을 답했을 때만 마친 것이다.
+        #   ★(1.1.11) 판번이 맞아도 끝이 아니다 — cys.exe 가 말하는 build_id 가 이번 핀의 것이어야 끝이다. 같은 판번 재빌드를 덮을 때
+        #   설치기가 잠긴 cys.exe 를 못 바꾸고도 0 을 답한 실기(10-22 kit B)에서, 판번만 보던 이 고리는 「마쳤다」 + 핀 표지를 박았다
+        #   (그 뒤 표지 = 옛 바이트 지문 → 다음 실행 'match' → 영영 건너뜀). build_id 는 앞 조건이 다 맞을 때만 잰다(한 번 부르기 상한 10초).
+        $bidSeen = $null
         for ($i = 0; $i -lt 60; $i++) {
             if ((Test-CysDirHasBins $dir) -and ((Get-VersionNumber (Get-CysExeVersion (Join-Path $dir 'cys.exe'))) -eq $CysVersion) -and
-                ((-not $refresh) -or ($p.HasExited -and $p.ExitCode -eq 0))) { $done = $true; break }
+                ((-not $refresh) -or ($p.HasExited -and $p.ExitCode -eq 0))) {
+                $bidSeen = Get-CysExeBuildId (Join-Path $dir 'cys.exe')
+                if ($bidSeen -ceq $CysWinBuildId) { $done = $true; break }
+            }
             if ($refresh -and $p.HasExited -and ($p.ExitCode -ne 0)) { break }   # 같은 판은 파일로 가를 수 없다 — 설치기가 실패를 답했으면 거기서 끝 · 성공(0)이면 파일이 자리 잡기를 상한까지 기다린다
             Start-Sleep -Seconds 1
         }
     } catch {
         Write-Log ('cys installer start failed: ' + $_.Exception.Message)
     }
+    if ((-not $done) -and ($null -ne $bidSeen)) { Write-Log ('cys build id mismatch: installed=' + $(if ($bidSeen) { $bidSeen } else { '(unreadable)' }) + ' pin=' + $CysWinBuildId) }
     if ($done) {
         [void](Save-CysPinStamp ([pscustomobject]@{ Path = $dir; Cli = (Join-Path $dir 'cys.exe') }))
         $script:CysBodyDir = [string]$dir
```

## 5. 검증 숫자

이번 가지의 Rust·TS·팩 변경 = **0줄**(`git diff 3ce93329 HEAD -- src src-tauri/src Cargo.toml Cargo.lock build.rs ui cysjavis-pack` 빈 값) — 아래는 회귀 없음 확인용.

| 시험 | 결과 |
|---|---|
| `cargo test --lib` | **1101 passed · 0 failed** · 2 ignored |
| `cargo test --bin cys` | **627 passed · 0 failed** |
| `cargo test --bin cysd` | 2703 passed · **1 failed** · 9 ignored — `trash::tests::a_name_set_whose_session_budget_runs_out_ends_the_job_instead_of_showing_a_preview`(「예산을 넘긴 순회가 Done 으로 끝났다 — shown 0 · refusals 1」). **단독 재실행 3/3 통과**. 시험이 이 기계의 순회 시간을 재고 그 절반을 예산으로 주는 시간 의존형이라, 전체 병렬 부하에서 첫 측정이 느리고 둘째 순회가 빨라지면 예산 안에 끝난다 → 부하 의존 흔들림(선존 · Rust 변경 0). ⚠브리프 부기 「휴지통 미리보기 안 나옴」과 같은 모듈이다 — 관련 여부는 **조사하지 않았다**(범위 밖). |
| `sh scripts/win-typecheck.sh` | **rc 0** — 오류 0 · 경고 65 · 판정 0 |
| ui `bun test` | **3176 pass · 0 fail** · 85 skip(98 파일) |
| ui `tsc -p tsconfig.check.json` | **rc 0 · 오류 0** — 첫 실행은 rc 1(TS7006 8건)이었고 원인은 이 작업트리에 `ui/node_modules` 부재(타입 해석 실패) · `bun install --frozen-lockfile`(잠금 그대로 · gitignore) 뒤 0 |
| 팩 py 전건(`cysjavis-pack/bin/tests/test_*.py` 189 · 격리 HOME · CYS_* 제거 · CYS_UPDATE_STATE_DIR 격리 · CYS_FEEDBACK_BASE=127.0.0.1:9) | **185 rc 0** · 4 은 자기 격리 가드가 실행 거부: `test_dept_team_token`(CYS_PACK_DIR 요구) · `test_preflight_phase1_checks`·`test_verify_gate`(JAVIS_ROOT·CYS_PROBE_RUNS 요구) → 요구 env 로 재실행 **23·26·9 OK** · `test_agora_known_authentic` = CYS_AGORA_ZIP_DIR(「제작 맥 전용 · skip 금지」) 부재로 적 — 팩 diff 0 이라 기준선과 같은 결과 |
| makensis v3.12 | 하네스 `-WX` 컴파일 OK(N1~N11) · `nsis-template/check.py` OK · 모델 OK |
| release.yml 을 읽는 시험 11종 | 전부 rc 0(test_release_trigger_split 16 · postprocess_gate 82 · release_verify 140 · update_publish 113(skip 14) · check_no_ioreport_link 12 · version_sot_mutation · default_fleet_formation · pyseal_census · runtime_manifest_parity 11 · secret_scan_limit 10 · wp7_gate_triage) |
| 훅·봉인 관련 py | test_update_publish · test_verify_win_crt · test_preflight_c80_runtime_seal · test_runtime_seal · test_runtime_manifest_parity rc 0 |
| `scripts/secret-scan.sh`(변경·신규 9 파일) | clean |

## 6. 윈 실기로만 확정되는 것 (이 맥에서 못 잼 — 정직 고지)

- NSIS 훅은 맥에서 **컴파일만** 된다(실행 기층 없음). A·B 의 런타임 증거는 ⑴ 모델 미러(분기 전수) ⑵ 하네스 정적 핀 ⑶ 도우미 `.ps1` 의 **pwsh 7(맥)** 실행이다.
  윈도우 PowerShell **5.1** 실행·실행 중 이미지(cysd 잠금) 공유 읽기·`$PLUGINSDIR` 풀기는 윈 실기 몫.
- 실기 재현 절차(제안): 같은 판번·다른 바이트 키트 2개를 데몬 가동 중 순서대로 `/S` 설치 → 기대 = exit 0 · `cys.exe`·`cysd.exe` SHA = 두 번째 키트 사이드카 ·
  `cysd.prev.exe` 생김 · 상세 로그에 `has this version but not this build's bytes` 2줄. 이어 같은 키트 재설치 → prev 신규 0 · 판별 로그 0줄.
- dist-info: 1.1.9 깨끗한 설치 위에 pip 판이 다른 runtime 을 펼친 키트 → `cys-runtime-prune: … removed=1` · `cys doctor` runtime-seal PASS.

## 7. 이월 · 부기 (범위 밖 · 보고만)

- `windows-build.yml` T4-4 주석이 아직 「CYS_PLACE ① 오라클 단락 :187-193」을 인용한다 — 단언(`prev 존재 OR 설치 SHA == 소스 SHA`)은
  새 동작에서도 참이라 동작 영향 없음 · 주석만 낡음(워크플로 파일이라 이번에 안 건드림).
- 브리프 부기 후보 「휴지통 미리보기(크기 측정) 안 나옴」 — 조사하지 않았다(범위 밖 지시대로 보고만).
- 화면·설치 문구 변경 0. 새 줄은 상세 로그(DetailPrint 1종 · 도우미 요약 1종 · bootstrap Write-Log 2종)뿐 — 문구 정책상 확인 대상이면 master 판단.

## 8. 증류

- 메모리 후보(작성 안 함 · master 판단): 「VERSIONINFO 는 정체가 아니다 — 같은 판·같은 seq 재빌드를 가르는 것은 바이트(설치기 ④-b) 또는
  build_id(bootstrap)다 · 고정 tauri-action 은 releaseDraft:true 여도 공개 릴리스를 집어 같은 이름 자산을 지우고 다시 올린다」.
