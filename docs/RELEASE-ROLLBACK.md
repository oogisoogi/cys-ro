# 발행 경로와 롤백 절차 (1쪽)

> 작성 2026-09-09 · TICKET=cys-release-first-publish · 박사님 09:05 승인 「우리 서명 배포 전환 ·
> 윈도우 먼저 · 방아쇠 분리」의 운영 문서. 전체 릴리스 절차는 `docs/RELEASE.md`, 이 문서는
> **발행 한 동작이 무엇이며 어긋났을 때 무엇을 되돌릴 수 있는가**만 다룬다.

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

```bash
gh release edit v<문제> -R oogisoogi/cys-terminal --tag v<문제> --draft=true   # 1순위: 비공개로
gh release delete v<문제> -R oogisoogi/cys-terminal                            # 최후: 삭제
```

- **1순위는 draft 로 되돌리는 것**이다. 자산이 보존돼 원인 규명이 가능하고, 되살릴 수 있다.
- 삭제는 자산까지 사라진다. 사후 분석이 불가능해지므로 오너 지시가 있을 때만.
- 태그(`refs/tags/vX.Y.Z`) 는 **남겨 둔다**. 태그를 지우고 같은 이름으로 다시 자르면
  이미 그 태그를 받아 간 클론과 이력이 갈린다.

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
