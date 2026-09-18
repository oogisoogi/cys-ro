# HANDOFF — usage-two-accounts (TICKET=usage-two-accounts · 2026-09-19 · worker surface:823)

## 박사님 결정 (원문, 09-19 07:1x)
「토큰량 표시기는 클로드 방식대로 5h/7d/fable만 표시하고, **두 계정 모두 정확하게 정보를 받아 표시하라.**」

## 무엇이 틀려 있었나 (실측)
- OAuth usage 프로브(`cysd` 상주 · 180초)가 키체인 항목 `Claude Code-credentials`(= `~/.claude` 프로필 = 계정A) **하나만** 읽었다.
- 그래서 계정B는 statusline 원천(페인이 턴을 돌 때만 옴)의 5h·7d뿐이었고 **7d·Fable 게이지가 아예 없었다**.
  운영 데몬 실측(07:2x): `66e877cb source=oauth … Fable 21%` · `d1599af5 source=statusline … scoped []`.

## 키체인 항목 이름 산식 (실측으로 확정 · 산식은 시험에 중립 경로로 고정 · 실물 대응은 아래 표)
- `~/.claude`(기본 · `CLAUDE_CONFIG_DIR` 미설정) → `Claude Code-credentials` (접미 없음)
- 그 밖의 프로필 dir → `Claude Code-credentials-<h8>`, **h8 = sha256(dir 절대경로 문자열)의 16진 앞 8자리**(끝 슬래시 없음).
- 근거: `security dump-keychain`의 서비스명 접미 4개가 프로필 4개와 하나씩 정확히 맞았다(확신도 High · 이 기계에서 4/4).

| 키체인 항목 | 프로필 | 계정(uuid 앞 8) | 항목 수정 시각 |
|---|---|---|---|
| `Claude Code-credentials` | `~/.claude` | 66e877cb (A) | 09-18 21:04 |
| `…-42f72ae1` | `~/.cys/claude-axdev` | 66e877cb (A) | 07-06 (낡음 · 401) |
| `…-0bb9bba4` | `~/.cys/claude-default-dept-1` | 66e877cb (A) | 07-13 (낡음 · 401) |
| `…-8e8febd2` | `~/.claude-acct2` | d1599af5 (B) | 09-18 05:29 |
| `…-a5d624bb` | `~/.cys/claude` | d1599af5 (B) | 09-18 21:58 |

★브리프 §2는 계정2 = `42f72ae1`이라고 적었지만, 실측상 `42f72ae1`은 계정A의 axdev 프로필 항목이다(접수 때 【경고】로 보고함).
Claude Code 원본 소스의 산식은 minify된 바이너리라 문자열로 찾지 못했다. 그래서 근거는 실측 4/4 일치뿐이다.
Claude Code가 산식을 바꾸면 시험은 초록으로 남고 운영에서 「원천 소실」 1줄로 드러난다(산식은 우리 것이 아니다).

## 무엇을 바꿨나
### `src/bin/cysd/accounts.rs`
1. `keychain_service_for(home, dir)` — 위 산식.
2. `probe_targets(state, home, dirs)` — 프로필 열거(`cys::profile_gate::enumerate_profile_dirs`: seed_known과 같은 정본)를
   `.claude.json`의 accountUuid로 **계정별로 묶는다**. 계정마다 후보 프로필 목록(기본 dir 먼저, 나머지는 경로순)을 둔다.
   **토큰을 꺼내는 dir과 신원을 읽는 dir이 언제나 같다**(짝 유지 · 유령 계정 0).
3. `probe_account` — 후보를 앞에서부터 시도해 처음 성공한 응답을 그 계정에 반영한다.
   후보를 여럿 두는 이유는 안 쓰는 프로필의 항목이 낡기 때문이다(실측: axdev·dept-1 항목 = 401).
4. `probe_round` — 계정마다 **따로** 조회하고 백오프도 **계정별로 따로** 센다(180s × 2^n − 반 주기, n≤3).
   한 계정의 실패가 다른 계정에 번지지 않는다. 로그 꼬리표는 uuid 앞 8자다(메일은 로그에 남기지 않는다).
5. `spawn_claude_oauth_probe` — 매 바퀴 대상을 다시 연다(부트 뒤 새 프로필·로그인 변경을 따라간다).
6. `oauth_probe_report`(`cysd --oauth-usage-probe`) — 계정마다 한 덩어리로 찍는다. 한 계정이라도 실패하면 rc=1.
7. `note_oauth` — 응답을 받았는데 모델 스코프 창이 없으면 옛 게이지를 **지운다**
   (종전엔 남겨 둬서 나이만 먹다 「죽은 창」으로 그려질 수 있었다 · 브리프 §3-3 「행을 그리지 않는다」).
8. 토큰 규율은 그대로다. 토큰은 메모리·curl stdin에만 두고 argv·로그·디스크에는 두지 않는다. 응답 본문을 로그에 찍지 않는다.
   실패 사유에는 프로필 표기와 HTTP 코드만 싣는다.

### `ui/src/main.ts` (Control Center 계정 행)
- 종전엔 5h·7d 두 줄만 그렸다. 이제 `a.scoped`의 모델 스코프 게이지(「7d·Fable」)를 **서버가 준 것만** 셋째 줄로 그린다.
  없으면 줄을 그리지 않는다. 5h·7d는 종전대로 늘 두 줄이다(없으면 「—」 · 없다/죽었다 구분은 rate 창에만).
- 스코프 게이지의 죽은 창 사유 문구는 게이지 자신의 관측 시각(`g.updated_at`)으로 잰다.
- `ccReset`: `label === "7d"` → `label.startsWith("7d")`로 바꿨다. 이게 없으면 「7d·Fable」 리셋이 시:분만 찍혀 오늘 리셋으로 읽힌다.
  다른 호출처는 모두 "5h"/"7d"만 넘기므로 동작이 같다.
- 사이드바(`wsusage.ts` accountRates·scopedRates)는 **무접촉**이다. 이미 계정별로 그리고 있어서, 데몬이 계정B의 scoped를 채우면 저절로 나온다.

### `src/bin/cysd/testdata/oauth_usage_account_{a,b}.json`
- 두 계정의 실물 응답이다(07:1x · 제 세션 자격증명으로 **읽기만** 해서 받았다). 바이트를 그대로 뒀다.
- 식별 정보(uuid·메일·조직)가 없는 것을 확인했다. 한도 수치와 표시 문구뿐이다.

## 시험 실측
| 항목 | 기준선 | 결과 |
|---|---|---|
| `cargo test -p cys-terminal --bin cysd` | 963 passed · 1 ignored | **969 passed · 1 ignored** (+6) |
| `accounts::` 필터 | 13 | **19** |
| `bun test`(ui) | 858 pass · 0 fail | **858 pass · 0 fail** |
| `bun run typecheck` | 12건(HEAD `git archive` 사본 실측) | **12건 · 신규 0**(행번호 정규화 diff 동일) |

전임 HANDOFF의 「동일 8건」은 오기다. HEAD 사본에서 재면 12건이고, 목록은 그 문서가 나열한 것과 같다.

신규 6건:
- `oauth_usage_parses_both_real_accounts`
- `keychain_service_names_match_measured_formula`
- `probe_targets_one_per_account_default_first`
- `probe_round_fills_both_accounts`
- `probe_round_isolates_account_failure`
- `note_oauth_clears_scoped_when_server_has_none`

## 뮤턴트 (실측)
- 변이: `probe_targets`에서 대상을 기본 dir만으로 좁혔다(`ordered.retain(|d| **d == default_dir)` = 종전 동작).
- 결과: **3건 적색**. `probe_round_fills_both_accounts`(지정 가드 · "계정 B가 프로브돼야 한다"), `probe_round_isolates_account_failure`, `probe_targets_one_per_account_default_first`.
- 원복 뒤 19/19 초록이다(원본 사본에서 복원했고, MUTANT 표지 0건을 확인했다).
- UI 변경(Control Center 행 · DOM 렌더)은 단위 시험 경로가 없어 뮤턴트를 걸지 않았다. 육안 확인은 앱 빌드 뒤 master 게이트다.

## 라이브 강제발화 (`target/debug/cysd --oauth-usage-probe` · 읽기만)
- 계정B(d1599af5): `.cys/claude` 항목으로 **5h 3% · 7d 43% · 7d·Fable 40%**를 받았다. `.claude-acct2` 항목은 실패했고 다음 후보로 넘어갔다.
- 계정A(66e877cb): 두 번 다 `.claude` 항목에서 **HTTP 429**였다(나머지 두 항목은 401).
  같은 시각 운영 데몬은 같은 토큰으로 80초 전에 oauth 성공(5h 2% · 7d 15% · Fable 21%)을 기록하고 있었다.
  ⇒ 제 조회가 운영 데몬 조회와 가까운 시점에 같은 토큰을 다시 쓴 탓으로 판단한다(서버 한도 창 길이는 미실측 · 확신도 Med).
  계정A 경로는 종전 코드와 같은 항목·같은 호출이다. 엔드포인트를 더 두드리지 않았다.
- ⚠운영 고려: 새 데몬이 뜨면 계정마다 180초에 1회 조회한다. 같은 토큰을 다른 프로세스(수동 강제발화 등)가 겹쳐 쓰면 429가 날 수 있다. 백오프가 흡수한다.

## 4군(비가역·비용)
해당 없음. 앱 빌드·릴리스·`/Applications`·`~/.cys` 접촉 0이다. 키체인은 읽기만 했다(쓰기·삭제 0).

## 남긴 것
- `cys todo-path`가 이 워커(role=worker)에게 `WORKER_3_TODO.md`를 줬는데, 그 파일은 다른 워커의 활성 원장(installer-0325-r2)이었다.
  그래서 덮어쓰지 않았고 todo는 세션 스크래치에 뒀다(기지 사실 `cys-todo-path-collides-for-generic-worker-role`의 재발).
- 계정 행 육안 확인(Fable 셋째 줄)은 앱 빌드 뒤 가능하다 = master 게이트.
