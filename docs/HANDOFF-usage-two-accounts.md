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

## 라이브 실측 캡처 (master 요청 · 2026-09-19 · 읽기만)
| 시각(KST) | 원천 | 계정 | 5h | 7d | 7d·Fable | 리셋 |
|---|---|---|---|---|---|---|
| 07:1x (직접 조회) | 키체인 `…-a5d624bb`(`~/.cys/claude`) → usage API 200 · 2,354B | B d1599af5 | 3% | 43% | **40%** | 5h 11:50 · 7d/Fable 09-24 17:00 |
| 07:1x (직접 조회) | 키체인 `Claude Code-credentials`(`~/.claude`) → 200 · 2,351B | A 66e877cb | 2% | 15% | 21% | 5h 12:10 · 7d/Fable 09-25 06:00 |
| 07:22:03 | `target/debug/cysd --oauth-usage-probe`(d7b890f3 빌드) | B | 3% | 43% | **40%** | 동일 |
| 07:22:03 | 같은 강제발화 | A | — | — | — | `.claude` HTTP 429 · 나머지 두 항목 401 |
| 07:2x | 운영 데몬(`cys usage-accounts --json` · 옛 코드) | A | 2% | 15% | 21% (80초 전 oauth) | — |
| 07:2x | 같은 운영 데몬 | B | 2% | 43% | **없음(scoped [])** · source=statusline | — |
원본 응답 두 개는 `src/bin/cysd/testdata/oauth_usage_account_{a,b}.json`에 바이트 그대로 있다(식별 정보 0).
(리셋 시각 = 응답 RFC3339를 KST로 바꾼 값.)

## master 확인 요청 2건 (07:26 【승인】 병기)
### ① 운영 데몬 안에서 계정A를 이중 프로브하지 않는가 → 데몬 하나 안에서는 하지 않는다
- 루프를 띄우는 곳은 `main.rs:1313` `accounts::spawn_claude_oauth_probe` 한 곳뿐이다(`git grep` 전수).
  종전 기본 프로브 함수 `oauth_probe_once`는 **삭제**됐다(`git grep oauth_probe_once` 0건). 옛 루프와 새 루프가 함께 도는 경로는 없다.
- 한 바퀴(`probe_round`) 안에서 대상은 accountUuid당 1개다(`probe_targets`가 uuid로 묶는다).
  계정 안에서는 첫 성공에서 멈춘다(`probe_account`의 `return Ok(())`). 다음 후보는 앞 후보가 실패했을 때만 부르고, 그 후보는 **다른 토큰**(다른 키체인 항목)이다.
  ⇒ 같은 토큰은 데몬 1개당 180초에 최대 1회다(실패 백오프 중이면 그보다 적다).
- ⚠**데몬 여러 개 사이는 별개다(실측 07:2x)**: cysd가 3개 떠 있다. 운영 `/Applications/cys.app/.../cysd`(pid 872) 외에
  `~/axdev/.wt/cys-v102-merge/target/debug/cysd` 2개(pid 22184 · 23469, 09-18 20:49 기동, **ppid 1 = 고아**)가 있다.
  둘 다 `HOME`이 실제 사용자 홈이고 소켓은 `/tmp/b1.sock`·`/tmp/b5.sock`이다. 옛 코드이므로 각자 계정A 기본 토큰을 180초마다 조회한다.
  ⇒ 지금 계정A 토큰은 180초에 3회 이상 조회되고 있다. 이것이 강제발화 429의 유력한 원인이다(판단 · 확신도 Med).
  제 프로세스가 아니라서 종료하지 않았다 = **master 판단 사안**.
  ⚠이 수정본이 배포된 뒤 같은 고아가 새 코드로 뜨면 계정B 토큰도 데몬 수만큼 겹쳐 조회된다. 기존 성질(데몬마다 프로브)이 계정 수만큼 넓어지는 것이다.
### ② 429는 백오프로 흡수되고 값은 유지되는가 → 그렇다(시험으로 고정)
- 429는 `fetch_oauth_usage`에서 `Err("HTTP 429")`가 된다. 후보가 전부 실패하면 `probe_round`의 Err 가지로 가서 그 계정만 백오프한다.
- 백오프 = **180s × 2^n − 90s(반 주기), n = min(연속 실패, 3)** → 270s · 630s · 1350s(상한).
  종전 「180s × 2^n · 상한 3(최대 24분)」과 거의 같다. 반 주기를 뺀 이유는 조회 소요만큼 늦게 오는 틱이 기한을 못 넘겨 한 틱을 더 건너뛰는 것을 막기 위해서다(상한 22.5분).
- 실패 시 `note_oauth`를 부르지 않는다 ⇒ rate·scoped·updated_at·source가 **그대로** 남는다.
  「죽은 값」 강등은 쓰기에서 하지 않고, 읽기 시점 판정(`rate_window_stale_reason`: 리셋 시각 지남 또는 24시간 무관측)만 한다.
- 시험 `probe_failure_keeps_previous_values_and_backs_off`: 값이 있는 계정A에 429 → 값·관측 시각·Fable 유지 + 백오프 (1회, +270s).
  뮤턴트(실패 가지에서 rate를 비움) → 이 시험 적색 → 원복 뒤 20/20 초록.
- 시험 수: cysd 970 passed · 1 ignored(969 + 1).

## 후속 — TICKET=cysr-usage-two-accounts (2026-09-23 · worker surface:941)
### 원인 실측 (「계정2 = statusline · 약 30시간 stale」)
- 브리프 추정 「cmux 임시 settings(`--settings …cmux-claude-settings.*`)가 statusLine 을 덮는다」는 **반증**됐다.
  임시 파일의 최상위 키는 `hooks`·`preferredNotifChannel` 뿐이고, 라이브 데몬 `usage.named_reporters` 에 master 의 statusline 보고가 10초 전에 와 있었다.
- 진짜 원인 ①: cmux 페인(CYS_SURFACE_ID 없음)의 statusline 은 `usage.report_named` 로 간다. 이 핸들러는 ctx 만 저장하고 rate 는 버린다.
  계정 귀속(`note_rate`)은 `usage.report`(cys 페인)에서만 한다. 계정2를 쓰는 세션은 master·CSO(cmux) 뿐이라 statusline 공급원이 0이다.
- 원인 ②: 계정2의 마지막 statusline(09-22 02:54)은 `~/.cys/claude` 가 계정2였던 때의 것이다. 지금 그 프로필은 계정1로 다시 로그인돼 있다.
- 원인 ③: 라이브 cysd 1.0.2(09-18 빌드)에는 계정별 OAuth 프로브(d7b890f3 · v1.1.0 이후 태그)가 없다.
- HEAD(1.1.5) 강제발화(`cysd --oauth-usage-probe`) = 두 계정 모두 rc0(계정2는 `.claude-acct2` 항목). ⇒ 판올림만으로 계정2 숫자는 채워진다.
- R3(named 경로에도 rate 귀속)은 **기각**(master 09:00): named 는 소유 게이트가 없고 cwd 를 자기 신고한다. 계정 rate 는 토큰 리미트 게이트의 계기라 위조 입구를 여는 비용이 더 크다.

### 바꾼 것 (A안 = 패널 R1·R2)
- `accounts.rs`: `fresh_limit_secs(source)` — statusline 120초 · oauth 240초(주기 180 + 여유 60). 계정 행과 스코프 게이지가 **각자 자기 원천의 한도**를 싣는다.
  근거는 시험 `fresh_limit_values_follow_source_cadence` 에 있다: 한도는 주기보다 커야 하고, 첫 백오프 대기(270초)보다 작아야 한다.
- `wsusage.ts`: 흐림 판정은 데몬 한도를 따른다. 필드가 없으면(옛 판본 부서 데몬) 종전 120초다. 행에 `source` 를 싣고, `sourceGrade` 에 oauth(◆)·snapshot 을 더했다.
- `main.ts`: rate 행에도 ctx 행과 같은 출처 마크·나이 칸을 붙였다. `wsbar.showsRowAge` 는 스코프 게이지가 있으면 rate 행 폭(6em 이름 칸)으로 잰다.
- 왜 한도가 원천별이어야 하나: 120초 하나로 재면 oauth 로만 채워지는 행이 매 주기 약 60초씩 흐려지고, 툴팁이 「최근 관측 없음」을 거짓으로 말한다. 헤드리스 대조 캡처로 확인했다.
