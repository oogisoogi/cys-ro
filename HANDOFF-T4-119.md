# HANDOFF — TICKET=cysr-119-t4-app (worker-7 · 311 t4 → 후임/검토자)

- 작성: 2026-10-09 07:3x KST · 가지 `feat/119-t4-app`(off merge/v0.14.43 = 9d8fff71) · **push 0**(워커 금지 · 병합 = master)
- 판정: 설계 1장 통과 = master#fb304202(Q1~Q4 권고 채택 · 문구 규칙 ⓐⓑ) · 설계 = `docs/design/T4-APP-MENUS-119.md`(§7-1 = 판정 기록)

## 0-4. 4판 델타(codex 3R MAJOR 1 → master#0fe94c77)
- `glob_match` 재귀 백트래킹 → 선형 반복식(두 포인터 · 마지막 `*` 위치 기억 · O(n·m)) · 의미론 불변 · 시험 = `*?`×32+Z × 64B < 10ms(별 스레드 1초 상한) + OpenSSH 정답지 9꼴 단위 시험 · 뮤턴트(재귀판 되돌림) = 시간 초과 적색 · cys-app 287/0 · 인구조사 4 · 윈 교차 타입검사 오류 0.

## 0-3. 3판 델타(codex 2R = ①⑤ 부분 해소 → master#fe827f4d · 나머지 7건 = 2R 「해소」)
| # | 2R 근거 | 고친 것 | 시험·증거 |
|---|---|---|---|
| ① | `split_fields`+`trim_matches('"')` 는 OpenSSH `strdelimw` 와 다름 — `x,"jarvis-*"` 를 `x,"jarvis-*` 로 비교해 공격 줄 누락 | OpenSSH 원본 이식: `strdelimw`(따옴표 지우고 이어 붙임 · 닫는 따옴표에서 끊김 · 안 닫힘 = 무효) · `match_pattern`·`match_pattern_list`(하위 패턴 ≥1023B = 목록 불일치 포함) · `parse_principals_key_and_options` 순서(키 먼저 → 안 되면 `sshkey_advance_past_options` 로 옵션 칸 건너뛰고 다시 · `\"` 처리) · 무효 줄 = 지문 None(fail-closed) | `strdelimw_matches_openssh_misc_c` · `signer_line_options_and_comments`(cert-authority·namespaces·valid-after/before·주석·안 닫힌 따옴표) · `several_valid_keys_for_desk_all_compared` · 공격 꼴 17 · **실 OpenSSH 10.3 정답지 9꼴 일치**(`shots-119-t4/openssh-oracle-2026-10-09.txt` · cert-authority 만 우리가 더 엄격) |
| ⑤ | `length > 256`·CR/LF 거부가 남음 = 길이 가정 | `typeof marker === "string"` 만 확인 · 경계 글자와 정확 일치(정규식 0) | 257자·여러 줄·정규식 특수문자·한글·1자·빈 표식 벗김 · 한 글자 다른 5꼴 안 벗김 |

## 0-2. 2판 델타(codex 1R BLOCK 5 · MAJOR 4 → master#6576ea7c 결정대로 9건 전부 코드 해소)
| # | 결함(리뷰) | 고친 것 | 시험(무는지) |
|---|---|---|---|
| ① BLOCK | 명부 주체를 문자열 일치로 읽어 `jarvis-*` 공격 키를 놓침 | `glob_match`·`principal_matches` = OpenSSH match_pattern(_list) 의미론(쉼표·`*`·`?`·`!` 부정 · 따옴표 주체 · 옵션 칸) · 그 id 에 맞는 **모든 줄** 대조 · 지문 못 낸 줄 = 불일치(fail-closed) | `wildcard_attacker_line_breaks_desk_verification`(9꼴) · `principal_pattern_list_is_openssh_semantics` · 뮤턴트(부정 무력화) 적색 2 |
| ② BLOCK | 격리 없는 python → sitecustomize 가 검증 전에 가짜 출력 | `read_command` = `python -I -B -X utf8` + 자식 env 에서 PYTHONPATH·HOME·STARTUP·USERBASE·INSPECT·EXECUTABLE 제거(-B = -I 아래서도 .pyc 안 씀 · SEAL-1) | `sitecustomize_injection_does_not_run_before_the_client`(공격 env 를 다시 넣어도 무효) · `read_command_is_isolated_and_read_only` · 뮤턴트(`-I` 제거) 적색 5 |
| ③ BLOCK | `about:blank`·`srcdoc` 를 top-level 에도 허용 | **`about:` 전면 거부**(https 아고라 오리진만). 실측 wry 0.55.1 = 맥은 모든 틀에 URL 만 넘김(구분 불가) · 윈은 top-level 만 | 이동 판정 위장 꼴 14 · `ui/e2e/agora_frames_probe.py` 실 로비: 서브 틀 about:blank 탐색 2회(관측) · Cloudflare 확인 스크립트를 막아도 목록 정상·오류 0(WebKit·Chromium) → `shots-119-t4/agora-frames-probe-2026-10-09.txt` |
| ④ BLOCK | 반쯤 쓴 unread.json 의 수정 시각을 캐시 → 같은 ms 완성본 영구 누락 | `parseUnread` → `{state, settled}` · `stepUnread` = settled(없음·정상·v≠1)일 때만 수정 시각 기억 | `stepUnread — 부분 쓰기 뒤 …` 2건 |
| ⑤ BLOCK | 표식 16 hex 고정 가정 | 꼴 가정 0 — 비지 않고 한 줄·≤256자인 응답 값과 바이트 정확 일치만 | 32 hex·다른 접두 벗김 · 빈/여러 줄/긴 표식 안 벗김 |
| ⑥ MAJOR | 거부된 이동을 브라우저로 자동 전달(탭 폭탄) | `on_navigation = agora_nav_allowed`(거부만) · `on_new_window = Deny` · `open_outside` 삭제 · 사람이 누른 바깥 링크 = 주입 스크립트가 창 안 안내 1줄(「바깥 링크는 이 창에서 열리지 않아요. 아래 주소를 복사해서 브라우저에서 여세요:」 + 주소 · textContent · 10초) · open_url 정확 일치 2줄 유지 | `init_script_embeds_my_id_as_json_and_blocks_forms`(안내·오리진 4조건·window.open 0) |
| ⑦ MAJOR | stdout 무제한 적재 | 전체 상한 512KB(8쪽×64KB) · 읽는 스레드가 상한 넘는 순간 멈추고 본 스레드가 자식 즉시 종료 · 첫 쪽 넘침 = error · 이후 쪽 넘침 = 앞쪽만 + partial | `stdout_flood_is_cut_at_cap_not_buffered`(<10초 · 둘째 쪽 넘침 = partial) |
| ⑧ MAJOR | capability 시험이 문자열 검색 | 모든 capability 파일(json 외 꼴 = 실패) + tauri*.conf.json 인라인 → windows·webviews glob(`*`·`?`·`[` = 연다고 봄)·remote·범위 칸 없음 구조 판정 | `capability_judge_catches_globs_star_and_remote`(8꼴) · 실 capability 전건 |
| ⑨ MAJOR | 가짜 CLI 가 argv 를 안 봄 | 가짜 CLI = argv `read --thread_id <핀 방> [--cursor <값>]` · 격리 플래그 3 · AGORA_CONFIG_DIR · 금지 env 0 아니면 exit 9 · 커서 쪽 넘김 시험 신설 | 뮤턴트(`read`→`post`) 적색 4 |

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
3. ~~`agora read` 를 `python -I` 없이~~ → **2판에서 뒤집음**(master 결정 ② = `-I -B -X utf8` · §0-2 ②).
4. 「상담소 답」 = 명부의 그 id 키 **전부**가 핀 지문일 때만(한 줄이라도 다르면 그 키로 서명된 글이 `sig: ok` 로 올 수 있다).
5. ~~아고라 창 이동 허용에 `about:blank`·`about:srcdoc` 추가~~ → **2판에서 철회**(§0-2 ③).
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

## 5. 종결(2026-10-09 08:4x)
- **병합 = 45ed1133**(merge/v0.14.43 ← feat/119-t4-app `--no-ff` · 9d8fff71..ee899c67 · master 직접 판독 + 스냅샷 게이트 ee899c67 전건 녹 = ui 0 fail · tsc 0 · cys-app 287/0 · lib 1027/0) · codex 3R 잔여 BLOCK 0·MAJOR 0.
- **남은 한계 = 실 앱 창 미실행**(작업트리 사이드카가 빈 자리표라 Tauri 창을 띄운 적 없음 · 아고라 창의 이동 차단·incognito·바깥 링크 안내·내 글 강조는 단위 시험 + 헤드리스만).
  - 맥 실기(10-16 · 1.1.9 후보 설치본) 1회: 사이드바 「아고라」 → 상단 「설치 안내 →」 클릭 = 창 이동 0 + 아래 안내 1줄(주소 포함) · 「상담소」 = 클라이언트 0.1.14 이면 방 소개 + 「아직 글이 없어요」(0.1.4 면 「도구가 아직 준비되지 않았어요」 카드).
  - 윈 키트(wintest-v1.1.9) 1줄 추가: 같은 두 동작 + 아고라 창을 닫았다 다시 열어 저장소가 비어 있는지(incognito = WebView2 InPrivate 【추정】 확인).
  - 그때 볼 명령 2줄:
    `python3 ui/e2e/agora_frames_probe.py`   # 실 로비 틀 탐색·확인 스크립트 막음에도 목록 정상(두 엔진)
    `COUNSEL_LIVE_CFG=<0.1.14 설정 폴더> cargo test -p cys-app --bins live_room_list_with_real_client -- --ignored`   # 실 방 읽기 status ok

## 6. 공개 미러 CI ⓒ(iii) 적색 해소(2026-10-09 · TICKET=cysr-119-t4-pyseal · 98ae0efe)
- 원인 = 2언어 미러 불일치: Rust 핀(src/lib.rs expected)엔 T4 가 counsel.rs:1 을 이미 등재했는데 파이썬 미러 `test_pyseal_census.py` RUST_SPAWN_PIN 엔 없었다(run 37860860661 · 두 잡 같은 1건).
- 봉인 = 코드 무변경 — counsel.rs `read_command` 가 이미 `inject_runtime_path`(ENV_PY_NO_BYTECODE · main.rs 4지점과 같은 GUI 규약) + `-I -B` + spawn_policy(Attached). 고친 것 = 미러 핀 1줄 + lib.rs 전수 열거 주석 1줄.
- 실측: census FAIL 0 · lib 핀 1 passed · cys-app counsel 27/0(1 ignored) · secret-scan --all clean.
