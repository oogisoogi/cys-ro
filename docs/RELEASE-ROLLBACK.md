# 발행 경로와 롤백 절차 (1쪽)

> 작성 2026-09-09 · TICKET=cys-release-first-publish · 박사님 09:05 승인 「우리 서명 배포 전환 ·
> 윈도우 먼저 · 방아쇠 분리」의 운영 문서. 전체 릴리스 절차는 `docs/RELEASE.md`, 이 문서는
> **발행 한 동작이 무엇이며 어긋났을 때 무엇을 되돌릴 수 있는가**만 다룬다.

## 0. 버전 규약 — 우리 판은 벤더 태그보다 항상 patch ≥1 크다

> master 판정 2026-09-09(브리프의 「0.14.30 승계」 조항을 개정). 리베이스 기준이 된 **벤더 태그보다
> patch 를 최소 1 올린다** — 벤더 0.14.30 을 리베이스했으면 우리는 0.14.31, 다음에 벤더 0.14.31 을
> 리베이스하면 우리는 0.14.32.

⛔**태그를 달기 전에 반드시 로컬에서 `sh scripts/version-check.sh <달려는 태그>` 를 돌려라.**
버전 SOT 8곳은 **태그가 붙는 그 커밋 안에** 목표 번호로 들어 있어야 한다. 태그 이름만 올리고
SOT 를 안 올리면 CI 의 「Version SOT check (drift hard-gate)」가 **3개 레그 전부**를 죽이고,
그 번호는 그대로 소각된다(태그를 옮기는 것 = force = 금지).
실사고 2026-09-09: SOT 가 `0.14.31` 인 커밋에 `v0.14.32` 를 달아 전 레그 적색 → 번호 소각 →
`v0.14.33` 으로 재발행. 범프와 태그는 **한 세트**다 — 번호를 바꾸기로 하면 범프부터 다시 한다.

**실패한 태그의 번호는 재사용하지 않는다.** 태그를 달고 빌드가 적색이면 그 번호는 거기서 끝이고,
수리 뒤에는 **다음 번호**로 다시 낸다(실측 사례 2026-09-09: v0.14.31 빌드 적색 → 수리 → v0.14.32).
이유는 태그를 옮기는 것이 곧 force 이고, 같은 번호가 두 트리를 가리킨 이력이 남으면 「무엇이
v0.14.31 이었나」를 나중에 아무도 확정할 수 없기 때문이다. 실패 태그는 **존치**한다(삭제 금지) —
그것이 "이 번호는 발행되지 않았다"는 기록이다.

**왜**: 같은 태그 이름이 두 판을 가리키면 영구 분기가 된다. 실측(2026-09-09) — upstream 의
`v0.14.30` 은 `bc01f43` 을 가리키는데 그 위에 우리 커밋이 **47개** 쌓여 있었다. 그 상태로 우리도
`v0.14.30` 을 달면 두 원격을 가진 사람에게 같은 이름이 서로 다른 커밋 둘을 뜻하게 된다.
벤더 태그는 **로컬에 그대로 둔다**(삭제·이동 금지).

⚠**브랜치 이름과 판번호는 일부러 다르다**: 작업 브랜치는 `rebase/v0.14.30`(= 리베이스 **기준**이 된
벤더 태그명)이고, 그 브랜치가 내는 우리 릴리스는 `v0.14.31`이다. 헷갈리지 마라 — 브랜치명은
"무엇을 리베이스했나", 태그는 "우리가 무엇을 발행하나"를 가리킨다.
`release-production` 의 허용 ref 도 브랜치명 `rebase/v0.14.30` 그대로다.

## 1. 발행 경로 — 태그는 꼬리표, 발행은 버튼

| 단계 | 무엇이 | 누가 | 되돌릴 수 있나 |
|---|---|---|---|
| ① `git push origin vX.Y.Z` | `release.yml` 이 빌드·서명하고 **draft** 릴리스를 만든다 | worker(【push 요청】 후) | ○ draft 삭제 |
| ② 로컬 후처리 | `release-postprocess.py` 가 `x64-setup.zip`·`SHA256SUMS.txt` 를 만들어 draft 에 올린다 | worker(macOS) | ○ 자산 교체 |
| ③ dispatch `dry_run=true` | `release-publish.yml` 의 **verify** 잡이 내려받아 검증하고 산출물 표만 남긴다 | worker | ○ 아무것도 안 바뀐다 |
| ④ dispatch `dry_run=false` | **publish** 잡이 오너 승인 뒤 다시 받아 다시 검증하고 `--draft=false --latest` | **master 1회** | ✕ **비가역** |

- 태그 push 는 **발행하지 않는다**. `release.yml` 은 `releaseDraft: true` 까지다
  (핀: `scripts/tests/test_release_trigger_split.py`).
- `dry_run` 기본값은 **true** 다. 입력을 비운 채 실행해도 발행되지 않는다.
- ④ 는 `environment: release-production` 승인 게이트를 지난다. 승인 뒤 **같은 잡 안에서**
  다운로드·검증·승격이 연속으로 일어난다(승인 대기 중 draft 가 바뀌는 TOCTOU 창을 열지 않기 위함).
- ⚠ 팩 채널(`pack-v*` 태그 → `pack-release.yml`)은 **별도 레인**이고 승인 게이트 없이 곧장 공개된다.
  본체 발행과 혼동하지 마라.

## 2. 되돌릴 수 있는 것 — 업데이터 표면 (권장 1순위)

앱의 updater 엔드포인트는 **`releases/latest/download/latest.json`** 이다
(`src-tauri/tauri.conf.json`). 즉 **어느 릴리스가 `latest` 인가**가 배포 표면 전부를 결정한다.
그래서 가장 빠르고 가장 안전한 롤백은 릴리스를 지우는 것이 아니라 **`latest` 를 되돌리는 것**이다.

```bash
# 직전 정상 릴리스를 다시 latest 로 —— 이것만으로 신규 업데이트 유입이 멈춘다
gh release edit v<이전> -R oogisoogi/cys-terminal --tag v<이전> --latest
gh release view -R oogisoogi/cys-terminal --json tagName,isDraft   # 되읽어 확인
```

⚠`--tag` 를 반드시 동봉한다 — `tag_name` 을 빠뜨린 릴리스 PATCH 는 태그를 `untagged-<sha>` 로
리셋한 전례가 있고, 그러면 다운로드 URL 이 전부 어긋난다(`release-publish.yml` ④ 주석 참조).

## 3. 되돌릴 수 있는 것 — 문제 릴리스 자체

`latest` 를 되돌린 **뒤에** 판단한다. 순서를 바꾸지 마라 — 지우는 동안 그것이 latest 면 그 창에
들어온 참가자가 404 를 본다.

> ⚠**손대기 전에 먼저 확인하라 — 옛 릴리스 3개가 prerelease 상태인가?**
> 아니라면 우리 릴리스를 draft 로 내리는 순간 `/releases/latest` 의 fallback 이
> **0.12.58 매니페스트**(옛 `feat/tab-ui-font-blink` 릴리스의 latest.json)로 떨어진다.
> 확인: `gh release list -R oogisoogi/cys-terminal` — 옛 3개에 `Pre-release` 표시가 있어야 한다.
> 아니면 §3-b 를 **먼저** 집행하고 나서 이 절로 돌아와라.
> ✅ 2026-09-09 첫 발행 직후 셋 다 강등 완료(실측) — 지금은 이 선행 조건이 충족돼 있다.

```bash
gh release edit v<문제> -R oogisoogi/cys-terminal --tag v<문제> --draft=true   # 1순위: 비공개로
gh release delete v<문제> -R oogisoogi/cys-terminal                            # 최후: 삭제
```

- **1순위는 draft 로 되돌리는 것**이다. 자산이 보존돼 원인 규명이 가능하고, 되살릴 수 있다.
- ⚠**되돌린 뒤 `latest` 가 어디로 떨어지는지 반드시 확인하라.** GitHub 의 `/releases/latest` 는
  「draft·prerelease 가 아닌 릴리스」 중에서 고른다. 우리 릴리스를 draft 로 내리면 자동으로
  **그 다음 후보**가 latest 가 된다. 실측(2026-09-09): 이 저장소에는 2026-07 의 옛 릴리스 3개가
  남아 있고 그중 `feat/tab-ui-font-blink` 가 **0.12.58 짜리 latest.json 을 자산으로 갖고 있다**.
  즉 롤백이 엔드포인트를 「업데이트 없음」이 아니라 **0.12.58 매니페스트**로 떨어뜨릴 수 있다.
  롤백 직후 `curl -sL <endpoint>` 로 무엇이 나오는지 눈으로 보고, 아니면 §2 로 명시 복원하라.
- 삭제는 자산까지 사라진다. 사후 분석이 불가능해지므로 오너 지시가 있을 때만.
- 태그(`refs/tags/vX.Y.Z`) 는 **남겨 둔다**. 태그를 지우고 같은 이름으로 다시 자르면
  이미 그 태그를 받아 간 클론과 이력이 갈린다.

## 3-b. 옛 릴리스 강등 — 첫 발행의 **고정 절차 ④** (선택 사항 아님)

master 결정 2026-09-09. 2026-07 세대의 옛 릴리스 3개(`feat/tab-ui-font-blink`·
`fix/shift-enter-newline`·`fix/hangul-ime-composition-leak`)는 브랜치명 태그로 만들어진 것이고,
첫째 것이 우리 첫 발행 직전까지 **Latest** 였다. 이들을 prerelease 로 내려야 §3 의
「fallback 이 0.12.58 로 떨어지는」 지뢰가 사라진다.

```bash
for T in feat/tab-ui-font-blink fix/shift-enter-newline fix/hangul-ime-composition-leak; do
  gh release edit "$T" -R oogisoogi/cys-terminal --prerelease      # 가역
done
```

⛔**순서 불변** — 첫 발행 시의 집행 순서는 이렇게 넷이다:
  ① 우리 릴리스 공개(`--draft=false --latest`) → ② `curl -sL <endpoint>` 로 latest.json 왕복 확인
  → ③ **그 뒤** 옛 3개 prerelease 강등 → ④ 엔드포인트 재확인(여전히 우리 것인가).

**집행 실적 2026-09-09 (v0.14.33 첫 발행)** — 네 단계 그대로, 실측:
  ① `isDraft=false` · `publishedAt=2026-09-09T04:41:27Z` · `/releases/latest` = `v0.14.33`
  ② 엔드포인트 latest.json = version 0.14.33 · platforms 2키 · darwin 0 ·
     sha256 `9e28b194…5adb1d` = SUMS 등재값과 **바이트 일치**
  ③ 옛 3개 → `Pre-release` (삭제 0)
  ④ `/releases/latest` = **여전히 `v0.14.33`** · 엔드포인트 재왕복 sha256 **불변**(`9e28b194…`)
먼저 내리면 non-prerelease 릴리스가 하나도 없는 순간이 생기고, 그 창에서 `/releases/latest` 는
**404** 가 된다 — 업데이터에겐 「업데이트 없음」이 아니라 **오류**다.
⛔삭제는 하지 마라(prerelease 는 되돌릴 수 있고 삭제는 못 되돌린다).

## 4. 되돌릴 수 **없는** 것 — 정직하게 적는다

- **이미 갱신된 참가자는 되돌아오지 않는다.** 업데이터는 내려받아 설치까지 끝냈고, 우리에게는
  그들을 되돌릴 통로가 없다. `latest` 복원은 **앞으로의 유입만** 막는다.
- 되돌리려면 **더 높은 버전으로 고쳐 올리는 것**이 유일한 길이다(vX.Y.Z+1 정방향 수복).
  버전을 낮춰 재발행하는 경로는 없다 — updater 는 `release.version > current_version` 일 때만
  움직인다(`tauri-plugin-updater` 2.10.1 `updater.rs`).
- 공개된 순간 자산은 이미 내려받아졌을 수 있다. 서명키가 샜다면 롤백이 아니라 **키 교체**가 답이다.

## 5. 맥이 빠진 릴리스에서의 특이사항 (2026-09-09 현재)

Apple 서명 시크릿 7종이 없어 맥 레그가 skip 되므로, 이 세대의 릴리스에는 DMG·맥 업데이터 자산이
없고 `latest.json` 에 `darwin-*` 행이 없다.

- 맥 사용자의 앱 내 「업데이트 확인」은 **오류가 아니라 「업데이트 없음」**으로 돈다
  (`check_update` 의 `updater_target_absent` — 로그에는 「이 플랫폼용 릴리스 없음」이 남는다).
  이 동작이 없으면 맥 전 사용자가 매 확인마다 "업데이트 확인 실패"를 본다.
- 검증기는 이 묶음을 통과시키되 로그에 **「맥 자산 미포함(윈도우 단독 배포)」**를 명시한다.
  맥이 **반쪽**(DMG 만·darwin 행만·6종 중 일부)인 묶음은 종전대로 즉사한다.
- 맥 서명이 들어오는 날 되돌릴 것은 없다 — 자산이 6종 다 생기면 검증기가 자동으로
  「맥 포함」 경로로 판정한다. 상수를 되돌리는 작업은 없다.
