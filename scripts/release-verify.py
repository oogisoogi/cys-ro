#!/usr/bin/env python3
"""릴리스 자산 검증 — 공개 발행 직전, 받아둔 자산 묶음이 온전한지 오프라인으로 판정한다 (2026-08-18).

`release-publish.yml` 이 draft 릴리스의 전 자산을 내려받은 뒤 이 스크립트를 부른다.
여기서 비영(非零)으로 죽으면 공개 발행(`--draft=false`)은 일어나지 않는다 — 이 파일이
공개 레인의 **마지막 fail-closed 관문**이다.

★왜 "복원"이 아니라 "재작성"인가 (실측 근거)
  이 파일은 0418f17 `feat(release): make signed promotion fail closed` 에서 24개 형제 파일과
  함께 태어났다. 그런데 main 에는 d67d8c3 `ci: register protected release publishing` 이
  **워크플로 1개(66줄)만 체리픽**해 얹었다 — 스크립트도 정책파일도 따라오지 않았다.
  그래서 `release-publish.yml` 이 부르는 이 파일이 main·태그 어디에도 없다(결함 6-2).

  옛 판본(0418f17)을 그대로 되살려도 v0.14.19 는 통과하지 못한다. 실측 3연속 실패:
    1) `release/assets-policy.json` 이 main·v0.14.19 **양쪽에 없다**(체리픽에서 누락)
       → `rendered_policy()` 가 시작하자마자 FileNotFoundError.
    2) 정책을 실제 14종에 맞춰 합성해 줘도 → `release verification failed: latest.json notes mismatch`.
       옛 판본은 notes 를 `f"cys {version}"` 로 못박았는데 실물은 한국어 안내 문장이다.
    3) 그 뒤로도 platforms 집합이 어긋난다 — 옛 판본은 3종만 허용하나 실물은 6종
       (`-app`·`-nsis` 별칭 추가). 업데이터 자산명도 옛 판본은 `cys_<V>_aarch64.app.tar.gz`
       를 가정하나 실물은 **버전 토큰이 없는** `cys_aarch64.app.tar.gz` 다 →
       `files[...]` KeyError 가 except 튜플에 없어 사유 없는 트레이스백으로 죽는다
       (비영 종료라 fail-closed 이긴 하나 "명확한 사유 출력" 계약 위반).
  즉 옛 판본은 v0.14.19 의 자산 계약과 어긋난다. 그래서 **검증 강도는 그대로 물려받고**
  (zip↔exe 바이트 동일성 · 업데이터 서명 교차대조 · 심볼릭링크 거부)
  **기대 목록의 정본만 갈아끼웠다**: 사라진 `assets-policy.json` 대신 `SHA256SUMS.txt`.

★`SHA256SUMS.txt` 를 정본으로 삼을 때의 구멍과 그 메움 (2026-08-18 적대적 리뷰로 교정)
  SUMS 는 자기 자신을 설명하는 목록이라, "애초에 빌드되지도·등재되지도 않은 자산"은
  디렉터리↔SUMS 대조만으로 절대 잡히지 않는다 — 양쪽 다 없으면 사이좋게 일치한다.
  그대로 두면 검증이 fail-open 이다. 구멍을 세 겹으로 메운다:
    (1) `REQUIRED_ASSETS` — SUMS 와 무관한 독립 하한선(플랫폼 무관 + 윈도우 레인 6종)
        (release-postprocess.py 의 `want4` 관례와 동형).
        ★맥 레인 2종(DMG)은 2026-09-09 에 `MAC_ASSETS` 로 갈라져 `decide_mac_lane` 이
        **전부-또는-전무**로 판정한다(아래 §맥 레인 참조).
    (2) `UPDATER_PLATFORMS` — latest.json 의 **플랫폼 키 집합과 키→자산 결속**을 못박는다.
        나머지 5종(업데이터 tar.gz 2 + .sig 3)의 유일한 포획 지점이다.
        ★초판(2026-08-18 오전)은 여기를 무단언으로 뒀다가 실측 반증당했다: macOS 업데이터
        4종을 디렉터리·SUMS·latest.json 에서 통째로 지우고 platforms 를 windows 2행만
        남기면 **exit 0** 으로 통과했다(= macOS 전 사용자의 앱 내 Update 가 죽은 묶음이
        마지막 관문을 초록으로 통과). 또 6행 전부의 url 을 Windows 설치본으로 덮어써도
        통과했다(= macOS 업데이터가 NSIS exe 를 내려받는 묶음). 둘 다 지금은 죽는다.
    (3) `ASSET_SHAPES` — 확장자별 컨테이너 지문. 0바이트·엉뚱한 포맷을 잡는다.
        ★한계를 정확히 적는다. **잘림(truncation)을 잡는 건 세 종뿐**이다:
          · `.dmg` — 검사 지점이 머리가 아니라 **꼬리 512B('koly' 트레일러)** 라 잘리면 죽는다.
          · `.zip` — 중앙 디렉터리가 파일 끝에 있고, 게다가 5단계가 멤버를 끝까지 스트리밍한다.
          · `.tar.gz` — gzip 스트림을 **끝까지 풀어** CRC32·ISIZE 를 대조한다(잘리면 EOFError).
        나머지(`.exe`)는 머리 매직만 본다 — 잘린 exe 는 여기서 안 잡힌다.
        그리고 (1)(2)는 **이름**만, (3)은 **껍데기**까지만 본다. "이 설치본이 실제로
        설치되는가"는 이 스크립트의 사거리 밖이다(그건 CI 게이트·수동 설치 검증의 몫).
  (1)+(2) 로 맥 포함 묶음 13종이 **전부** 덮인다: 필수 6 + 맥 레인 6 + 윈도우 exe 서명 1 = 13 —
  조용히 통째로 사라져도 통과하는 자산은 남지 않는다. 윈도우 단독 묶음은 8종(필수 6 + exe 서명 +
  SUMS)이고 같은 방식으로 빠짐없이 덮인다.
  (3)은 13종 **전부**에 걸린다. 확장자 규칙에 없는 자산이 섞이면 그것도 실패다 — 배포 구성이
  바뀌는 날 사람이 상수를 고치도록 강제하는 장치다(무단 자산 유입 차단).
  ★배포 구성을 의도적으로 바꾸는 날에는 이 세 상수를 **손으로** 고쳐야 한다. 그게 fail-closed 다.

★맥 레인 — 전부-또는-전무 (2026-09-09 · TICKET=cys-release-first-publish)
  박사님 09:05 결정(「맥 서명 없이 윈도우 먼저」)으로 Apple 시크릿 7종이 없는 동안에도 배포가
  성립해야 한다. 그렇다고 DMG 요구를 그냥 지우면 이 파일이 원래 막던 것 — 「맥 사용자에게
  반쪽만 도달하는 묶음」 — 이 다시 열린다. 그래서 요구를 **지우지 않고 옮겼다**:
    · `decide_mac_lane()` 이 디렉터리 실물로 맥 레인 6종(DMG 2 + 업데이터 tar 2 + 서명 2)의
      존재를 세어 **전부(6) 또는 전무(0)** 만 인정한다. 1~5종 = 즉사.
    · 그 판정(`mac_included`)이 그대로 `check_latest_json` ② 의 **기대 플랫폼 키 집합**이 된다
      (윈도우 단독 2키 · 맥 포함 6키). 디렉터리와 업데이터 표면이 갈리면 여기서 죽는다 —
      DMG 만 있고 darwin 행이 없는 묶음도, darwin 행만 있고 DMG 가 없는 묶음도 통과 못 한다.
  즉 완화된 것은 **양쪽 다 통째로 없는 묶음 하나**뿐이고, 그것은 통과 시 로그에
  「맥 자산 미포함(윈도우 단독 배포)」로 **명시**된다(무음 통과 금지).

★반대 방향도 막는다
  디렉터리에 있는데 SUMS 에 없는 파일은 **오류**다. 등재되지 않은 자산이 릴리스에 섞여 있으면
  무결성 보증 없이 함께 공개된다.

★자격증명을 쓰지 않는다
  `release-postprocess.py` 는 `git credential fill` 로 토큰을 얻지만 이 스크립트는 얻지 않는다.
  일부러 그렇다 — 내려받기는 워크플로가 `gh` 로 끝내고, 검증기는 (버전, 디렉터리)만의 순수 함수여야
  누구나·어디서나 같은 판정을 재현할 수 있다. 네트워크·토큰·리포 내 다른 파일에 의존하지 않는다.
  ★이 자기완결성 덕분에 워크플로가 이 파일 하나만 따로 가져와 쓸 수 있다 —
  `release-publish.yml` 의 2차 체크아웃(`path: .release-tools`, ref = 워크플로 자신의
  `github.sha`)이 그것이다. 발행 대상 태그 트리에 이 파일이 없어도 검증이 성립한다
  (v0.14.19 태그는 이 파일보다 먼저 잘렸다 — 그래서 태그 트리에서 부르면 `can't open file` 로 죽는다).
  ★예외 1건(2026-09-12 · TICKET=cys-v01436-pack-url): 8단계 팩 replay 단조 검사는 **벤더 latest
  팩 매니페스트**를 비교 기준으로 쓴다. 그 한 파일만 `main()` 이 공개 URL 에서 받는다(토큰 불요).
  `verify()` 자체는 여전히 순수 함수다 — 벤더 매니페스트를 인자로 받는다(생략 불가 · 기본값 없음).
  네트워크가 없으면 **통과가 아니라 실패**다. 오프라인 재현은 `--vendor-manifest-file` 로 한다.

★8단계 — 팩 replay 단조 (2026-09-12 · TICKET=cys-v01436-pack-url)
  사용자 기계는 설치에 성공한 팩의 signed_at 을 `~/.cys/.pack-accepted.json` 에 적고, 다음 팩은
  그보다 **엄격히 새 signed_at** 이어야 받는다(`src/packsig.rs` ⓔ). 벤더 팩을 한 번이라도 받은
  기계는 벤더 signed_at 을 기준선으로 들고 있다. 우리 팩의 signed_at 이 그 값 이하이면 그 기계는
  우리 팩을 replay 로 **조용히 영구 거부**한다. 그래서 발행 직전에 「우리 signed_at > 벤더 latest
  signed_at」 을 단언한다. 실측(2026-09-12): 우리 1789091457 > 벤더 1789084036.
  ⚠사거리: 비교 대상은 **벤더의 현재 latest** 한 판이다. 벤더가 발행을 멈추면(자산 404) 이 검사는
  조회 불가로 발행을 막는다 — 그때는 사람이 기준을 다시 정해야 한다(조용한 통과로 풀지 않는다).
  ★r2 보강(codex·agy 1R):
    · signed_at 타당 범위 — 우리 매니페스트 `now-90일 ≤ signed_at ≤ now+300초` · 벤더 매니페스트
      `signed_at ≤ now+300초`(과거 하한 없음 · r3 S1 — 벤더 휴면이 우리 발행을 막지 않게). 우리 쪽의
      음수·유물·미래 서명과 벤더 쪽의 미래 서명(기준선을 영구히 올린다)은 실패로 떨어진다.
    · 팩 전용 레인(`pack-release.yml`)도 같은 함수를 부른다 — `--pack-only --pack-manifest <경로>`
      (자산 묶음 검증 없이 8단계만 · 발행 단계 직전). 두 레인이 한 구현을 공유한다(중복 0).
    · 발행 뒤 벤더가 더 늦게 서명한 경우의 대처는 docs/RELEASE.md 「팩 replay 단조 런북」 절.
    · 관측 최대값 영속(high-water)·파일 override 금지는 채택하지 않았다(master r2 판정 — 실패 양상이
      재서명 1회로 회복되는 규모라 과잉).

동반 회귀 테스트: `python3 scripts/tests/test_release_verify.py` (합성 픽스처 · 네트워크 불요)

사용:
  python3 scripts/release-verify.py --version 0.14.19 --release-dir ~/cys-release-backup/v0.14.19-assets
  python3 scripts/release-verify.py --version 0.14.19 --release-dir reviewed-release --print-assets
  python3 scripts/release-verify.py --version 0.14.30 --release-dir d --repo oogisoogi/cys-ro
  python3 scripts/release-verify.py --version 0.14.36 --release-dir d --vendor-manifest-file vendor.json
  python3 scripts/release-verify.py --pack-only --pack-manifest pack-manifest.json      # 팩 전용 레인

종료코드: 0=통과, 1=검증 실패, 2=인자 오류
"""
import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import zipfile
import zlib
from datetime import datetime

SUMS_NAME = "SHA256SUMS.txt"          # ★과거 관례 — `SHA256SUMS`(확장자 없음) 아님
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
# `<64자 소문자 hex><공백 2칸><파일명>` — shasum -a 256 의 기본 출력 형식.
# 파일명 문자셋을 좁게 못박아 경로 탈출(`../`)·공백 트릭을 원천 차단한다.
ROW_RE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9_.-]+)$")
# 파일명에 박힌 버전 토큰(X.Y.Z)을 뽑는다. `cys_aarch64.app.tar.gz` 처럼 토큰이 없는 이름도
# 정상이므로(업데이터 자산은 버전을 안 달고 나온다) "있으면 일치해야 한다"로 다룬다.
TOKEN_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")

# ★배포 원본 레포 — latest.json 의 url 결속(③)을 이 값으로 판정한다.
#   ★2026-09-09 정정(TICKET=cys-release-first-publish): 종전 값은 벤더 `idoforgod/cys-terminal`
#   이었다. 개발자 업데이트 중단으로 **우리 포크가 배포자**가 된 뒤(2026-09-08 전환)에도 이 줄만
#   벤더로 남아, 우리 레포에서 tauri-action 이 만든 latest.json(url = github.com/oogisoogi/…)이
#   ③ 에서 **전 행 실패**했다 — REQUIRED_ASSETS 를 어떻게 풀든 발행이 불가능한 상태였다.
#   ⚠이 값 · `release.yml` 의 `SRC_REPO` · `src-tauri/tauri.conf.json` 의 updater endpoints 는
#     **같은 레포**여야 한다. 엇갈리면 업데이터가 남의 판을 본다(전환 시 세 곳 동시 수정).
RELEASE_REPO = "oogisoogi/cys-ro"

# ★8단계 비교 기준 — 벤더 latest 팩 매니페스트(검사용 상수 · 배포 원본이 아니다).
#   사용자 기계의 replay 기준선이 될 수 있는 **남의 판**이다. 우리 팩이 이보다 새로 서명돼야 한다.
VENDOR_PACK_MANIFEST_URL = \
    "https://github.com/idoforgod/cys-terminal/releases/latest/download/pack-manifest.json"

# ★signed_at 타당 범위(r2 · codex 1R BLOCK · r3 S1 개정).
#   미래 시각 서명은 사용자 기계의 replay 기준선을 영구히 끌어올린다 → 상한(+300초 · 러너 시계 오차
#   허용폭)은 우리·벤더 둘 다. 과거 90일 하한은 **우리 산출물에만** — 음수·오래된 유물 서명을 막는다.
#   벤더에는 하한을 두지 않는다: 벤더가 오래 발행을 멈춰도 그 옛 값은 안전한 비교 기준이고, 하한을
#   걸면 벤더 휴면이 우리 발행을 막는다(2R codex·agy 가용성 결함).
SIGNED_AT_MAX_AGE_SEC = 90 * 86400
SIGNED_AT_MAX_FUTURE_SEC = 300

# ★SUMS 와 무관한 독립 하한선 ① — 이게 없으면 "빌드 자체가 안 돼 SUMS 에도 안 실린 자산"을 못 잡는다.
#   `{v}` 는 --version 으로 채운다. 여기 없는 자산은 아래 `UPDATER_PLATFORMS` 가 강제한다.
#
# ★2026-09-09 분할 (TICKET=cys-release-first-publish · 박사님 09:05 「맥 서명 없이 윈도우 먼저」)
#   종전 이 튜플은 DMG 2종을 **무조건** 요구했고 그것이 의도된 차단이었다(맥 업데이터가 죽은
#   묶음의 통과 금지 — 이 파일 머리말 §(2) 의 실측 반증 기록). 그 차단이 선 전제는 "맥 서명은
#   늘 있다" 였다. Apple 시크릿 7종이 아직 없는 지금(release.yml 의 macOS 레그 명시 skip),
#   같은 차단이 **어떤 배포도 못 하게** 막는다. 그래서 요구를 없애지 않고 **둘로 가른다**:
#     · REQUIRED_ASSETS — 플랫폼 무관 하한선 + 윈도우 레인 (항상 필수)
#     · MAC_ASSETS      — 맥 레인 (전부 있거나 전부 없거나)
#   ★이건 완화가 아니라 **이동**이다. 원래 막으려던 것("맥 업데이터가 죽은 묶음")은
#   `decide_mac_lane` 의 전부-또는-전무 + `check_latest_json` ② 의 키 집합 대조가 그대로 막는다:
#   「DMG 는 있는데 darwin 행이 없다」도, 「darwin 행은 있는데 DMG 가 없다」도 여전히 죽는다.
#   달라진 것은 **양쪽 다 통째로 없는 묶음**을 「윈도우 단독 배포」로 명시 통과시키는 것뿐이다.
REQUIRED_ASSETS = (
    "cys_{v}_x64-setup.exe",      # Windows 다운로드 버튼
    "cys_{v}_x64-setup.zip",      # .exe 직다운이 막힌 환경용 4번째 버튼
    "latest.json",                # 앱 내 Update 버튼(업데이터)의 정본
    "pack.tar.gz",                # cysjavis 팩 본체
    "pack-manifest.json",         # 팩 매니페스트
    "pack-manifest.json.minisig", # 팩 매니페스트 minisign 서명
)

# ★맥 레인의 다운로드 버튼 자산. 업데이터 4종(tar.gz 2 + .sig 2)은 `MAC_PLATFORMS` 가 강제하며,
#   `mac_lane_files()` 가 이 둘을 합쳐 "맥 레인 전집합 6종"을 만든다.
MAC_ASSETS = (
    "cys_{v}_aarch64.dmg",        # macOS Apple Silicon 다운로드 버튼
    "cys_{v}_x64.dmg",            # macOS Intel 다운로드 버튼
)

# ★독립 하한선 ② — 업데이터 표면의 정본. **키 집합과 키→자산 결속을 둘 다 못박는다.**
#   집합을 안 박으면 macOS 레인이 통째로 사라져도 통과하고(행이 줄면 검사도 함께 줄어든다),
#   결속을 안 박으면 darwin 행이 Windows 설치본을 가리켜도 통과한다. 둘 다 실측으로 확인된
#   fail-open 이었다(docstring 참조).
#   출처: tauri-action 이 매트릭스 3잡의 산출을 병합해 내는 실물 표면. 로컬 백업 전수 실측
#   (2026-08-18): v0.14.0 … v0.14.19 **21개 묶음 · 126행 전부**가 이 6키·이 결속과 일치,
#   불일치 0. (v0.13.23 은 3키 시절이라 대상 밖 — `-app`·`-nsis` 는 tauri v2 업데이터의
#   별칭 키이고, 옛 판본이 3키로 못박았다가 깨진 지점이 바로 여기다.)
#   ★2026-09-09 분할 — 자산 하한선과 같은 이유로 레인을 가른다. 기대 키 집합은 **고정 6키가
#   아니라 묶음에 따라 정해진다**: 윈도우 단독이면 2키, 맥 포함이면 6키. 어느 쪽이든 `!=` 대조라
#   행이 하나라도 줄거나 늘면 죽는다(fail-open 이 열리지 않는다).
REQUIRED_PLATFORMS = {
    "windows-x86_64":      "cys_{v}_x64-setup.exe",
    "windows-x86_64-nsis": "cys_{v}_x64-setup.exe",
}
MAC_PLATFORMS = {
    "darwin-aarch64":      "cys_aarch64.app.tar.gz",
    "darwin-aarch64-app":  "cys_aarch64.app.tar.gz",
    "darwin-x86_64":       "cys_x64.app.tar.gz",
    "darwin-x86_64-app":   "cys_x64.app.tar.gz",
}
# 맥 포함 묶음의 기대 전집합(종전 상수와 같은 6키) — 외부 소비자·테스트가 이 이름을 쓴다.
UPDATER_PLATFORMS = dict(REQUIRED_PLATFORMS, **MAC_PLATFORMS)
# latest.json 최상위 필드 집합 — notes 삭제·임의 키 주입을 잡는다(0418f17 판본에서 계승).
LATEST_JSON_FIELDS = {"version", "notes", "pub_date", "platforms"}

# ★독립 하한선 ③ — 확장자별 컨테이너 지문. 이름만 맞고 알맹이가 0바이트/쓰레기인 묶음을 잡는다.
#   전부 로컬 백업 v0.14.19 실측으로 대조했다(2026-08-18 · 13종 전수):
#     dmg      = UDIF 규격의 **끝 512B 'koly' 트레일러**(머리는 zlib 압축이라 `78 01` 로 시작한다
#                — 머리 매직으로는 dmg 를 식별할 수 없다. 실측으로 확인한 지점)
#     exe      = MZ · zip = PK\x03\x04 · tar.gz = gzip 매직 1f 8b · minisig = minisign 텍스트 헤더
#     sig      = **base64 텍스트**이고 풀면 `untrusted comment:` 로 시작한다(tauri updater 서명).
#                실측: 3종 전부 `dW50cnVzdGVkIGNvbW…` = b64("untrusted com…").
#   ★suffix 매칭은 endswith 라 충돌이 없다 — `*.exe.sig`/`*.tar.gz.sig` 는 `.sig` 로,
#     `*.json.minisig` 는 `.minisig` 로만 걸린다(".minisig"[-4:] == "isig" ≠ ".sig").
#   ★사거리 명시: 여기까지가 "껍데기"다. 설치본이 실제로 설치되는지는 보지 않는다.
ASSET_SHAPES = (
    (".tar.gz",  "gzip"),        # 특수 규칙 — 매직 + 스트림을 끝까지 풀어 CRC32·ISIZE 대조
    (".minisig", b"untrusted comment:"),
    (".dmg",     "koly"),        # 특수 규칙 — 머리가 아니라 꼬리 512바이트를 본다
    (".exe",     b"MZ"),
    (".zip",     b"PK\x03\x04"),
    (".sig",     "minisign-b64"),  # 특수 규칙 — base64 로 풀리고 minisign 헤더여야 한다
    (".json",    "json"),        # 특수 규칙 — 파싱되고 최상위가 객체여야 한다
)


class VerifyError(Exception):
    """검증 실패. 메시지가 곧 사용자에게 보이는 사유다."""


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files(release_dir):
    """디렉터리의 일반 파일만 {이름: 경로}로 모은다. 그 외 항목은 전부 거부(fail-closed)."""
    if not os.path.isdir(release_dir):
        raise VerifyError("릴리스 디렉터리가 없다: %s" % release_dir)
    files = {}
    for name in sorted(os.listdir(release_dir)):
        path = os.path.join(release_dir, name)
        # ★심볼릭링크 거부: 링크를 끼워 넣으면 "검증한 바이트"와 "발행되는 바이트"가 갈릴 수 있다.
        if os.path.islink(path) or not os.path.isfile(path):
            raise VerifyError("일반 파일이 아닌 항목이 섞여 있다: %s" % name)
        files[name] = path
    if not files:
        raise VerifyError("릴리스 디렉터리가 비어 있다: %s" % release_dir)
    return files


def parse_sums(path):
    """SHA256SUMS.txt 를 {파일명: 다이제스트}로 판다. 한 줄이라도 이상하면 실패."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except UnicodeError as e:
        raise VerifyError("%s 가 UTF-8 로 읽히지 않는다: %s" % (SUMS_NAME, e))
    rows = text.splitlines()
    if not rows:
        raise VerifyError("%s 가 비어 있다" % SUMS_NAME)
    sums = {}
    for i, row in enumerate(rows, 1):
        m = ROW_RE.match(row)
        if not m:
            raise VerifyError("%s %d번째 줄 형식 오류: %r" % (SUMS_NAME, i, row))
        digest, name = m.group(1), m.group(2)
        if name in sums:
            raise VerifyError("%s 에 중복 등재: %s" % (SUMS_NAME, name))
        sums[name] = digest
    # ★자기 자신 제외 규약(release-postprocess.py 3단계와 동일). 자기를 등재하면 논리적으로
    #   대조가 불가능하다 — 해시를 쓰는 순간 파일이 바뀌기 때문이다.
    if SUMS_NAME in sums:
        raise VerifyError("%s 가 자기 자신을 등재했다 — 자기 제외 규약 위반" % SUMS_NAME)
    return sums


def check_version_tokens(version, names):
    """파일명에 박힌 버전 토큰이 전부 --version 과 같은지 본다."""
    stamped = 0
    for name in sorted(names):
        tokens = set(TOKEN_RE.findall(name))
        if not tokens:
            continue                      # 버전을 안 다는 자산(업데이터 tar.gz 등) — 정상
        stamped += 1
        bad = sorted(t for t in tokens if t != version)
        if bad:
            raise VerifyError("파일명 버전 토큰 불일치: %s 에 %s (기대 %s)"
                              % (name, ", ".join(bad), version))
    # ★공허한 통과 차단: 전 자산이 버전을 안 달았다면 "다른 버전 묶음"을 잡을 근거가 없다.
    if stamped == 0:
        raise VerifyError("버전 토큰이 박힌 자산이 하나도 없다 — %s 묶음임을 확인할 수 없다" % version)


def check_windows_zip(version, files):
    """zip 이 setup.exe **한 개**만, 바이트 동일하게 품고 있는지(0418f17 판본에서 계승)."""
    exe = "cys_%s_x64-setup.exe" % version
    zipname = "cys_%s_x64-setup.zip" % version
    with zipfile.ZipFile(files[zipname]) as archive:
        members = archive.namelist()
        if members != [exe]:
            raise VerifyError("zip 은 루트에 %s 하나만 있어야 한다 — 실제: %r" % (exe, members))
        # 대용량이라 스트리밍으로 대조한다(통째로 메모리에 올리지 않는다).
        h = hashlib.sha256()
        with archive.open(exe) as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    if h.hexdigest() != sha256_file(files[exe]):
        raise VerifyError("zip 안의 %s 가 릴리스의 .exe 와 바이트 동일하지 않다" % exe)


def read_text_strict(path, what):
    """텍스트 자산 읽기 — 바이너리 쓰레기가 들어오면 UnicodeDecodeError 대신 사유를 낸다."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError as e:
        raise VerifyError("%s 가 UTF-8 텍스트가 아니다: %s" % (what, e))


def check_asset_shapes(files, names):
    """확장자별 컨테이너 지문 — 이름은 맞는데 알맹이가 0바이트·쓰레기·엉뚱한 포맷인 자산을 잡는다.

    ★규칙에 없는 확장자는 **실패**다. 배포 구성이 바뀌는 날 사람이 ASSET_SHAPES 를 고치도록
      강제하는 장치이자, 무단 자산 유입을 막는 빗장이다.
    """
    for name in sorted(names):
        path = files[name]
        rule = None
        for suffix, candidate in ASSET_SHAPES:
            if name.endswith(suffix):
                rule = candidate
                break
        if rule is None:
            raise VerifyError("확장자 규칙에 없는 자산이다(배포 구성이 바뀌었으면 "
                              "ASSET_SHAPES 를 손으로 갱신하라): %s" % name)

        size = os.path.getsize(path)
        if size == 0:
            raise VerifyError("자산이 0바이트다: %s" % name)

        if isinstance(rule, bytes):                       # 머리 매직
            with open(path, "rb") as fh:
                head = fh.read(len(rule))
            if head != rule:
                raise VerifyError("컨테이너 지문 불일치: %s (머리 %r · 기대 %r)" % (name, head, rule))

        elif rule == "koly":                              # dmg — 꼬리 512B UDIF 트레일러
            if size < 512:
                raise VerifyError("dmg 가 UDIF 트레일러(512B)보다 작다: %s (%d바이트)" % (name, size))
            with open(path, "rb") as fh:
                fh.seek(-512, os.SEEK_END)
                if fh.read(4) != b"koly":
                    raise VerifyError("dmg 끝에 UDIF 'koly' 트레일러가 없다"
                                      "(잘렸거나 dmg 가 아니다): %s" % name)

        elif rule == "gzip":                              # tar.gz — 끝까지 풀어 CRC32·ISIZE 대조
            with open(path, "rb") as fh:
                if fh.read(2) != b"\x1f\x8b":
                    raise VerifyError("gzip 매직이 아니다: %s" % name)
            try:
                with gzip.open(path, "rb") as fh:
                    for _ in iter(lambda: fh.read(1 << 22), b""):
                        pass
            except (OSError, EOFError, zlib.error) as e:
                raise VerifyError("gzip 스트림이 끝까지 풀리지 않는다(잘렸거나 손상): %s — %s: %s"
                                  % (name, type(e).__name__, e))

        elif rule == "minisign-b64":                      # tauri updater 서명
            raw = read_text_strict(path, name).strip()
            try:
                decoded = base64.b64decode(raw, validate=True)
            except ValueError as e:                       # binascii.Error 는 ValueError 하위
                raise VerifyError("서명 파일이 base64 가 아니다: %s — %s" % (name, e))
            if not decoded.startswith(b"untrusted comment:"):
                raise VerifyError("서명 파일이 minisign 형식이 아니다"
                                  "(풀어도 'untrusted comment:' 로 시작하지 않는다): %s" % name)

        elif rule == "json":
            try:
                obj = json.loads(read_text_strict(path, name))
            except json.JSONDecodeError as e:
                raise VerifyError("JSON 자산이 파싱되지 않는다: %s — %s" % (name, e))
            if not isinstance(obj, dict):
                raise VerifyError("JSON 자산의 최상위가 객체가 아니다: %s" % name)

        else:                                             # 상수를 고치면서 분기를 안 단 경우
            raise VerifyError("ASSET_SHAPES 규칙을 해석할 수 없다: %s → %r" % (name, rule))


def mac_lane_files(version):
    """맥 레인이 포함될 때 **반드시 함께 오는** 자산 전집합 6종.

    DMG 2종(`MAC_ASSETS`) + 업데이터 tar.gz 2종 + 그 서명 2종(`MAC_PLATFORMS` 의 값에서 유도).
    유도하는 이유: 상수를 두 벌 적으면 그중 하나는 반드시 뒤처진다(`build_decl_line` 과 같은 교리).
    """
    names = []
    for tpl in MAC_ASSETS:
        names.append(tpl.format(v=version))
    for tpl in MAC_PLATFORMS.values():
        asset = tpl.format(v=version)
        for n in (asset, asset + ".sig"):
            if n not in names:
                names.append(n)
    return sorted(names)


def decide_mac_lane(version, listed):
    """맥 레인 포함 여부를 **전부-또는-전무**로 판정한다. 반쪽이면 실패.

    이 함수가 종전 `REQUIRED_ASSETS` 의 DMG 강제를 대신한다. 지키는 계약은 그대로다 —
    「맥 사용자에게 반쪽만 도달하는 묶음」을 발행하지 않는다. 달라진 것은 **통째로 없는 묶음**을
    윈도우 단독 배포로 인정하는 것뿐이고, 그 판정 결과는 `check_latest_json` 의 기대 키 집합으로
    그대로 흘러가 latest.json 과 **교차 검증**된다(디렉터리와 업데이터 표면이 갈리면 죽는다).
    """
    lane = mac_lane_files(version)
    present = [n for n in lane if n in listed]
    if not present:
        return False
    if len(present) != len(lane):
        absent = [n for n in lane if n not in listed]
        raise VerifyError(
            "맥 레인이 반쪽이다 — 있는 것 %d종(%s) · 없는 것 %d종(%s). "
            "맥은 전부 포함하거나 전부 빼야 한다(반쪽 = 맥 사용자에게 죽은 묶음)."
            % (len(present), ", ".join(present), len(absent), ", ".join(absent)))
    return True


def check_latest_json(version, files, sums, mac_included, repo=RELEASE_REPO):
    """업데이터 정본 대조 — 앱 내 Update 버튼이 실제로 무엇을 받게 되는지 본다.

    네 겹으로 못박는다. 앞의 둘이 없으면 검사 자체가 사라지거나 엉뚱한 걸 검사한다:
      ① 최상위 필드 **집합** == LATEST_JSON_FIELDS — notes 삭제·임의 키 주입 차단.
      ② platforms **키 집합** == 이 묶음의 기대 키 집합 — 행이 줄면 그 행에 걸린 검사도
         함께 사라진다(fail-open).
         ★기대 집합은 고정이 아니라 `mac_included`(디렉터리 실측 판정)로 정해진다:
           윈도우 단독 = `REQUIRED_PLATFORMS` 2키 · 맥 포함 = `UPDATER_PLATFORMS` 6키.
           **디렉터리 쪽 판정을 업데이터 표면에 그대로 들이대는 것이 이 배선의 핵심**이다 —
           DMG 는 올려놓고 darwin 행을 빠뜨린 묶음(그리고 그 반대)이 여기서 죽는다.
      ③ 키 → **자산 결속** — darwin 행이 Windows 설치본을 가리키는 묶음이 여기서 죽는다.
      ④ 가리킨 자산과 그 `.sig` 가 SUMS 에 등재돼 있고, signature 값 == `.sig` 파일 내용.
    ①②③ 은 실측으로 반증당해 뒤늦게 채운 구멍이다 — 없앨 때는 반증부터 다시 하라.
    """
    try:
        latest = json.loads(read_text_strict(files["latest.json"], "latest.json"))
    except json.JSONDecodeError as e:
        raise VerifyError("latest.json 이 JSON 이 아니다: %s" % e)
    if not isinstance(latest, dict):
        raise VerifyError("latest.json 최상위는 객체여야 한다")
    # ── ① 최상위 필드 집합 ──
    if set(latest) != LATEST_JSON_FIELDS:
        raise VerifyError("latest.json 최상위 필드 집합 오류 — 누락 %s · 잉여 %s (기대 %s)"
                          % (sorted(LATEST_JSON_FIELDS - set(latest)) or "없음",
                             sorted(set(latest) - LATEST_JSON_FIELDS) or "없음",
                             sorted(LATEST_JSON_FIELDS)))
    if latest.get("version") != version:
        raise VerifyError("latest.json version 불일치: %r (기대 %s)" % (latest.get("version"), version))
    # notes 는 값을 못박지 않는다 — 옛 판본이 `f"cys {version}"` 로 박았다가 실물(한국어 안내
    # 문장)과 어긋나 깨졌다. "비어 있지 않은 문자열"까지만 요구한다.
    if not isinstance(latest.get("notes"), str) or not latest["notes"].strip():
        raise VerifyError("latest.json notes 가 비어 있거나 문자열이 아니다: %r" % (latest.get("notes"),))

    pub_date = latest.get("pub_date")
    if not isinstance(pub_date, str):
        raise VerifyError("latest.json pub_date 가 문자열이 아니다")
    try:
        parsed = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
    except ValueError:
        raise VerifyError("latest.json pub_date 가 RFC3339 가 아니다: %r" % pub_date)
    if parsed.tzinfo is None:
        raise VerifyError("latest.json pub_date 에 타임존이 없다: %r" % pub_date)

    platforms = latest.get("platforms")
    if not isinstance(platforms, dict) or not platforms:
        raise VerifyError("latest.json platforms 가 비어 있거나 객체가 아니다")

    # ── ② 플랫폼 키 집합 ── (행이 줄면 검사도 함께 줄어드는 fail-open 을 여기서 막는다)
    expected_platforms = dict(REQUIRED_PLATFORMS)
    if mac_included:
        expected_platforms.update(MAC_PLATFORMS)
    if set(platforms) != set(expected_platforms):
        raise VerifyError("latest.json platforms 키 집합 오류(%s 묶음) — 누락 %s · 잉여 %s "
                          "(기대 %d종 %s)"
                          % ("맥 포함" if mac_included else "윈도우 단독",
                             sorted(set(expected_platforms) - set(platforms)) or "없음",
                             sorted(set(platforms) - set(expected_platforms)) or "없음",
                             len(expected_platforms), sorted(expected_platforms)))

    base = "https://github.com/%s/releases/download/v%s/" % (repo, version)
    for key in sorted(platforms):
        row = platforms[key]
        if not isinstance(row, dict) or set(row) != {"signature", "url"}:
            raise VerifyError("업데이터 행 필드 집합 오류: %s" % key)
        # ── ③ 키 → 자산 결속 ── (darwin 행이 Windows 설치본을 가리키는 사고를 막는다)
        asset = expected_platforms[key].format(v=version)
        expected_url = base + asset
        if row["url"] != expected_url:
            raise VerifyError("업데이터 url 결속 위반: %s → %r (기대 %s)"
                              % (key, row["url"], expected_url))
        # ── ④ 등재·서명 ──
        if asset not in sums:
            raise VerifyError("업데이터가 등재되지 않은 자산을 가리킨다: %s → %s" % (key, asset))
        sig_name = asset + ".sig"
        if sig_name not in sums:
            raise VerifyError("업데이터 자산의 서명 파일이 없다: %s" % sig_name)
        expected = read_text_strict(files[sig_name], sig_name).strip()
        if not expected:
            raise VerifyError("서명 파일이 비어 있다: %s" % sig_name)
        if row["signature"] != expected:
            raise VerifyError("업데이터 서명 불일치: %s (%s)" % (key, sig_name))
    return sorted(platforms)


def _signed_at(obj, what, now, age_floor=True):
    """signed_at 을 **정확히 int** 로만 받고(bool·문자열·실수 거부) 타당 범위를 확인한다.

    age_floor=False(벤더 매니페스트 · r3 S1): 과거 90일 하한을 적용하지 않는다 — 벤더가 오래 발행을
    멈춰도 그 옛 값은 여전히 안전한 비교 기준이다. 미래 +300초 상한은 둘 다 적용한다.
    """
    if not isinstance(obj, dict):
        raise VerifyError("%s 가 JSON 객체가 아니다" % what)
    value = obj.get("signed_at")
    if type(value) is not int:
        raise VerifyError("%s 의 signed_at 이 정수가 아니다: %r" % (what, value))
    hi = now + SIGNED_AT_MAX_FUTURE_SEC
    if age_floor:
        lo = now - SIGNED_AT_MAX_AGE_SEC
        if not (lo <= value <= hi):
            raise VerifyError("%s 의 signed_at 이 타당 범위 밖이다: %d (허용 [%d, %d] = now-90일..now+300초 · now=%d)"
                              % (what, value, lo, hi, now))
    elif value > hi:
        raise VerifyError("%s 의 signed_at 이 타당 범위 밖이다: %d (허용 상한 %d = now+300초 · now=%d)"
                          % (what, value, hi, now))
    return value


def load_vendor_manifest(url=VENDOR_PACK_MANIFEST_URL, path=None, timeout=30):
    """8단계 비교 기준을 얻는다. 받지 못하면 **실패**다(모르는 채 발행하지 않는다)."""
    try:
        if path is not None:
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
            src = path
        else:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
            src = url
    except Exception as e:
        raise VerifyError("벤더 팩 매니페스트 조회 불가 — replay 단조를 판정할 수 없어 발행을 막는다"
                          "(%s: %s: %s)" % (path or url, type(e).__name__, e))
    try:
        return json.loads(raw)
    except ValueError as e:
        raise VerifyError("벤더 팩 매니페스트가 JSON 이 아니다(%s): %s" % (src, e))


def check_pack_replay_monotonic(files, vendor_manifest, now=None):
    """우리 pack-manifest.json 의 signed_at 이 벤더 latest 보다 **엄격히 커야** 한다.

    같거나 작으면 벤더 팩을 받은 기계가 우리 팩을 replay 로 거부한다(`src/packsig.rs` ⓔ 는 `<=` 거부).
    """
    try:
        ours = json.loads(read_text_strict(files["pack-manifest.json"], "pack-manifest.json"))
    except ValueError as e:
        raise VerifyError("pack-manifest.json 이 JSON 이 아니다: %s" % e)
    if now is None:
        now = int(time.time())
    ours_at = _signed_at(ours, "pack-manifest.json", now)
    vendor_at = _signed_at(vendor_manifest, "벤더 latest 팩 매니페스트", now, age_floor=False)
    if ours_at <= vendor_at:
        raise VerifyError("팩 replay 단조 위반 — 우리 signed_at %d <= 벤더 latest signed_at %d. "
                          "벤더 팩을 받은 기계가 이 팩을 replay 로 거부한다(다시 서명하라)"
                          % (ours_at, vendor_at))
    return ours_at, vendor_at


def verify(version, release_dir, vendor_manifest, repo=RELEASE_REPO, now=None):
    if not VERSION_RE.match(version):
        raise VerifyError("--version 은 X.Y.Z 여야 한다: %r" % version)

    files = collect_files(release_dir)
    if SUMS_NAME not in files:
        raise VerifyError("%s 가 없다 — 기대 자산 목록의 정본이 없으면 판정할 수 없다" % SUMS_NAME)
    sums = parse_sums(files[SUMS_NAME])

    # ── 1. 완전성: 디렉터리 ↔ SUMS 양방향 대조 (누락 0 · 미등재 0) ──
    present = set(files) - {SUMS_NAME}
    listed = set(sums)
    missing = sorted(listed - present)
    unlisted = sorted(present - listed)
    if missing:
        raise VerifyError("자산 누락 %d종 — %s" % (len(missing), ", ".join(missing)))
    if unlisted:
        raise VerifyError("SUMS 에 없는 자산이 섞여 있다 %d종(무결성 보증 없이 공개된다) — %s"
                          % (len(unlisted), ", ".join(unlisted)))

    # ── 2. 독립 하한선: SUMS 가 통째로 빠뜨린 자산을 잡는 유일한 지점 ──
    required = [a.format(v=version) for a in REQUIRED_ASSETS]
    absent = [a for a in required if a not in listed]
    if absent:
        raise VerifyError("배포 필수 자산 누락 %d종 — %s" % (len(absent), ", ".join(absent)))

    # ── 2-b. 맥 레인 — 전부-또는-전무 (반쪽 묶음은 여기서 죽는다) ──
    #    판정 근거는 **디렉터리 실물**이다. 이 값이 7단계의 기대 플랫폼 키 집합이 되어
    #    latest.json 과 교차 검증된다 — 한쪽만 맥을 가진 묶음이 통과할 틈이 없다.
    mac_included = decide_mac_lane(version, listed)

    # ── 3. 파일명 버전 토큰 ──
    check_version_tokens(version, listed)

    # ── 4. 컨테이너 지문 — 이름만 맞고 알맹이가 쓰레기인 자산을 잡는다 ──
    #    ★재계산 대조보다 **먼저** 둔다. SUMS 를 쓰레기에 맞춰 재생성한 묶음은 4단계를
    #      사이좋게 통과하므로(체크섬은 일치한다), 그런 묶음의 사유를 여기서 먼저 낸다.
    check_asset_shapes(files, listed)

    # ── 5. 전 줄 재계산 대조 ──
    for name in sorted(sums):
        if sha256_file(files[name]) != sums[name]:
            raise VerifyError("체크섬 불일치: %s" % name)

    # ── 6. Windows zip ↔ exe 바이트 동일성 ──
    check_windows_zip(version, files)

    # ── 7. 업데이터(latest.json) 교차 대조 ──
    platforms = check_latest_json(version, files, sums, mac_included, repo=repo)

    # ── 8. 팩 replay 단조 — 벤더 팩을 받은 기계도 이 팩을 받을 수 있는가 ──
    check_pack_replay_monotonic(files, vendor_manifest, now=now)

    return sorted(sums), platforms, mac_included


def main():
    ap = argparse.ArgumentParser(description="릴리스 자산 묶음을 오프라인으로 검증한다")
    ap.add_argument("--version", help="기대 버전 (X.Y.Z — 태그의 v 를 뗀 값 · 전체 검증 시 필수)")
    ap.add_argument("--release-dir", help="전 자산을 내려받아 둔 디렉터리 (전체 검증 시 필수)")
    # ★r2 R1 — 팩 전용 레인(pack-release.yml)의 진입점. 8단계(팩 replay 단조)만 돈다(같은 함수).
    ap.add_argument("--pack-only", action="store_true",
                    help="자산 묶음 없이 팩 replay 단조(8단계)만 검사 — --pack-manifest 필수")
    ap.add_argument("--pack-manifest", default=None, help="--pack-only 대상 pack-manifest.json 경로")
    ap.add_argument("--print-assets", action="store_true", help="검증된 자산명을 한 줄씩 출력")
    # ★매개변수화하되 **기본값이 곧 정본**이다(마스터 판정 2026-09-09 · REPO 1곳).
    #   플래그는 포크·미러에서 같은 검증기를 재현하기 위한 것이지, 배포 원본을 흔들라는 게 아니다.
    ap.add_argument("--repo", default=RELEASE_REPO,
                    help="배포 원본 레포 owner/name (기본 %(default)s — latest.json url 결속 판정 기준)")
    # ★8단계 기준의 오프라인 재현용. 생략하면 벤더 URL 에서 받는다 — 건너뛰는 선택지는 없다.
    ap.add_argument("--vendor-manifest-file", default=None,
                    help="벤더 latest pack-manifest.json 사본 경로 (기본: %s 에서 받음)"
                         % VENDOR_PACK_MANIFEST_URL)
    args = ap.parse_args()

    if args.pack_only:
        if not args.pack_manifest:
            ap.error("--pack-only 에는 --pack-manifest 가 필요하다")
        try:
            if os.path.islink(args.pack_manifest) or not os.path.isfile(args.pack_manifest):
                raise VerifyError("pack-manifest 파일이 없다(또는 심볼릭 링크): %s" % args.pack_manifest)
            vendor = load_vendor_manifest(path=args.vendor_manifest_file)
            ours_at, vendor_at = check_pack_replay_monotonic(
                {"pack-manifest.json": args.pack_manifest}, vendor)
        except VerifyError as e:
            print("::error::팩 replay 단조 검증 실패 — %s" % e, file=sys.stderr)
            return 1
        except Exception as e:
            print("::error::팩 replay 단조 검증 중단(판정 불가) — %s: %s"
                  % (type(e).__name__, e), file=sys.stderr)
            return 1
        print("✅ 팩 replay 단조 통과 — 우리 signed_at %d > 벤더 latest signed_at %d"
              % (ours_at, vendor_at))
        return 0

    if not args.version or not args.release_dir:
        ap.error("전체 검증에는 --version 과 --release-dir 가 필요하다(팩 전용은 --pack-only)")

    try:
        vendor = load_vendor_manifest(path=args.vendor_manifest_file)
        assets, platforms, mac_included = verify(args.version, args.release_dir, vendor,
                                                 repo=args.repo)
    except VerifyError as e:
        print("::error::릴리스 검증 실패 — %s" % e, file=sys.stderr)
        return 1
    except Exception as e:
        # ★fail-closed 의 마지막 빗장: 예상 못 한 예외도 "판정 불가 = 실패"로 떨어뜨린다.
        #   (옛 판본은 KeyError 를 못 받아 사유 없는 트레이스백을 냈다.)
        print("::error::릴리스 검증 중단(판정 불가) — %s: %s"
              % (type(e).__name__, e), file=sys.stderr)
        return 1

    if args.print_assets:
        print("\n".join(assets))
    # ★맥 포함 여부를 **판정 결과로 명시**한다 — 「조용히 빠진 것」과 「의도해서 뺀 것」을
    #   사람이 로그만 보고 구분할 수 있어야 한다(브리프: 없으면 「미포함」 명시).
    print("✅ 릴리스 검증 통과 — %s · 자산 %d종(+%s) · 업데이터 %d행 전부 서명 일치 · 맥 자산 %s"
          % (args.version, len(assets), SUMS_NAME, len(platforms),
             "포함" if mac_included else "미포함(윈도우 단독 배포 — 맥 사용자는 이 릴리스를 받지 않는다)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
