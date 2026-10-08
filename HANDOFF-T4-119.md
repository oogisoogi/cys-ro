# HANDOFF — TICKET=cysr-119-t4-app (worker-7 · 311 t4 → 후임/검토자)

- 작성: 2026-10-09 07:3x KST · 가지 `feat/119-t4-app`(off merge/v0.14.43 = 9d8fff71) · **push 0**(워커 금지 · 병합 = master)
- 판정: 설계 1장 통과 = master#fb304202(Q1~Q4 권고 채택 · 문구 규칙 ⓐⓑ) · 설계 = `docs/design/T4-APP-MENUS-119.md`(§7-1 = 판정 기록)

## 0. 델타(후임이 읽을 최소 범위)
- **이 파일 + 설계 §0(실측 표)·§3(보안 경계)·§7-1.** 재정독 불요: 종합 설계·SPEC 전문(§11 표만 설계 §2 에 옮겨 둠).
- 커밋 5개(순서 = master 지시):
  | # | 커밋 | 내용 |
  |---|---|---|
  | 1/5 | ecf743f3 | 사이드바 #ws-counsel-row(#ws-tabs 아래·#ws-usage 위) · 상담소 창(.modal-overlay · 남의 글 textContent 만) · counsel.ts 문구 정본 |
  | 2/5 | 6ecc9c0f | Rust `counsel_room_list` = 클라이언트 `agora read` 결과만 · 정렬/트리 순수 로직 · lib.rs 인구조사 2종 등재 |
  | 3/5 | 961cace9 | 뱃지 = `counsel_unread`(unread.json 읽기만) + 45초 수정 시각 폴링 · 읽음 처리 0 |
  | 4/5 | 51384e11 | 「아고라」 별도 창(보기 전용 · 아고라 오리진만 · 새 창/다운로드 거부 · incognito · devtools 끔 · capability 무등재) · open_url 정확 일치 2줄 |
  | 5/5 | (이 커밋) | 헤드리스 게이트 `ui/e2e/counsel_gate.py` + 캡처 3장 + 실 클라이언트 1회 시험(ignored) + 이 파일 |

## 1. 실측(도구 출력)
| 항목 | 결과 |
|---|---|
| ui `bun test` | 2715 pass · 0 fail(기준선 2745 = 83파일 → 85파일 · 71 skip 동일) |
| ui 타입검사 `bunx tsc -p tsconfig.check.json` | 오류 0(⚠작업트리에 node_modules 가 없으면 8 오류 — `bun install --frozen-lockfile` 뒤 0) |
| cys-app `cargo test --bins counsel` | 16 pass(+ ignored 1 = 실 클라이언트) |
| cys-app 전체 `cargo test -p cys-app --bins` | 275 pass · 0 fail · 2 ignored(실 클라이언트 1 포함) |
| lib 인구조사 4종(python 열거·원시 Command 동결·콘솔 정책·flag 0) | 4 pass |
| 윈 교차 타입검사 `scripts/win-typecheck.sh` | 오류 0 · 판정 0(경고 60 = 기존 파일) |
| 실 클라이언트 1회(0.1.14 사본 · `COUNSEL_LIVE_CFG`) | status ok · 상담소 id 1개 검증(실 명부 키 지문 = 핀) · 글 1(방 소개) · 0.46초 |
| 헤드리스 게이트(playwright 1.63 · chromium 1243) | 픽스처 13 + 실 결과 5 = **PASS** · 캡처 `docs/design/shots-119-t4/{sidebar-badge,counsel-panel-fixture,counsel-panel-live-empty}.png` |

## 2. 지시 없이 내린 판단
1. 뱃지 폴링 = **별도 `setInterval` 45초**(설계 초안 「사용량 틱에 얹기」 대신 · 3초 틱마다 Rust 를 부르지 않게) → `deptprogresswiring.test.ts` 총수 핀 11 → 12(사유 1줄).
2. 인구조사 검출기가 같은 파일 밖 포장 함수(`no_console`)를 못 읽어 counsel.rs 는 **`cmd.spawn_policy(cys::ChildLifetime::Attached)` 직접**(no_console 본체와 같은 등급).
3. `agora read` 를 `python -I` 로 부르지 않음 — `-I` 는 PYTHONUTF8 를 무시해 한국어 윈도(cp949)에서 JSON 출력이 깨질 수 있다. 팩 `javis_counsel.py` 호출 꼴(인자 없이 · env = inject_runtime_path)과 같게.
4. 「상담소 답」 = 명부의 그 id 키 **전부**가 핀 지문일 때만(한 줄이라도 다르면 그 키로 서명된 글이 `sig: ok` 로 올 수 있다).
5. 아고라 창 이동 허용에 `about:blank`·`about:srcdoc` 추가(사이트의 Cloudflare 확인 스크립트가 숨은 빈 틀을 만든다 · 실측 index.html).
6. 화면 글자 「master」 → 「마스터」(사이드바 기존 안내와 통일).

## 3. 미완 · 위험(정직)
- **실 앱 창 캡처 미실시**: 이 작업트리는 사이드카 자리표(빈 파일)라 앱을 실제로 띄우지 않았다. 캡처는 헤드리스(가짜 `__TAURI__`) + 실 클라이언트 결과 JSON 이다. ⇒ **아고라 창(on_navigation·incognito·주입 스크립트)은 실물에서 한 번도 안 떴다** — 판정 함수·스크립트 문자열은 단위 시험만. 실기 1회 필요(맥 빌드 후 · 윈 키트 10-16).
- 윈 `incognito` = WebView2 InPrivate 【추정】 · 윈 실기 항목에 「아고라 창 열기 → 외부 링크 → 기본 브라우저」 1줄 추가 필요.
- 이 맥 설치 클라이언트 = 0.1.4 → 실 앱에서는 「도구가 아직 준비되지 않았어요」 카드가 뜬다(정상 동작 · 1.1.8 팩 ensure-client 가 0.1.14 로 교체 · Q3 = 손대지 않음).
- 앱 CSP = `null`(기존) · 이 티켓에서 안 켬.

## 4. 재현
```bash
cd ui && bun install --frozen-lockfile && bun test && bunx tsc -p tsconfig.check.json
# Rust(CI 꼴): 사이드카 자리표 + 임시 팩 + CYS_* 환경 제거
triple="$(rustc -vV | sed -n 's/^host: //p')"; mkdir -p ui/dist src-tauri/binaries src-tauri/resources src-tauri/runtime
touch "src-tauri/binaries/cys-$triple" "src-tauri/binaries/cysd-$triple" src-tauri/resources/pack.tar.gz src-tauri/resources/pack-manifest.json
CYS_PACK_DIR="$(mktemp -d)" cargo test -p cys-app --bins counsel -- --test-threads=1
# 실 클라이언트 1회: <임시 설정 폴더>/lib = 0.1.14 꾸러미(install/agora-client-0.1.14.zip.b64 풀기) + 명부·participant.json 사본
COUNSEL_LIVE_CFG=<폴더> COUNSEL_LIVE_OUT=<json> cargo test -p cys-app --bins live_room_list_with_real_client -- --ignored
# 헤드리스 게이트
sh ui/build.sh && python3 ui/e2e/counsel_gate.py [<json>]
```
