# HANDOFF — usage-noagy (TICKET=usage-noagy · 2026-09-19)

## 박사님 결정 (원문, 06-5x)
「토큰 사용량 표시 기능에서 agy는 삭제하자. 의미가 없다.」

★agy는 에이전트로는 그대로 남는다. 이 티켓은 **계정 사용량 표(usage-accounts)에서만** 뺐다.
팩(`cysjavis-pack/`)·directives·`agents.json`은 열지도 고치지도 않았다(브리프 §0 지시).

## 무엇을 바꿨나 (`src/bin/cysd/accounts.rs`)
1. **`resolve()`**: `"gemini" | "agy" | "antigravity"` 매핑 분기 삭제 → `_ => None`으로 떨어진다.
   결과: `note_rate(daemon, "gemini", …)`(usage.rs:1299 `update_agy_usage` 안)는 신원 해석
   실패로 조기 리턴 — **호출은 남겨뒀고, 그 호출이 계정 표에 아무 영향을 못 준다(no-op)**.
   - ★**결정**: 호출을 지우지 않고 남겼다. 이유 — `update_agy_usage`는 이 note_rate 호출과
     별개로 surface 단위 `s.observed_usage`(agy 노드의 CTX 배지)도 갱신하는데, 그건 브리프
     §0/2-4에서 **범위 밖·무접촉**으로 명시됐다. 두 부작용이 한 함수에 같이 있어서, 호출을
     지우면 무접촉 대상까지 건드리게 된다. 남겨 둔 채 계정 표 쪽만 no-op으로 만드는 편이
     외과적이다. `note_rate_gemini_is_noop` 시험이 이 결정을 회귀 고정한다.
2. **`seed_known()` — 부트 시딩**: `~/.antigravity` 디렉터리 존재만으로 계정을 만들던 블록
   삭제(구 라인 308~328). `seed_known_ignores_antigravity_dir` 시험이 뮤턴트 가드다 — 이 블록을
   되살리면 그 시험이 적색이 되는 것을 직접 확인했다(재삽입→적색→원복→재검증 완료).
3. **`seed_known()` — 부트 복원(analytics.db 스냅샷)**: 옛 코드가 기록해 둔 `rate_snapshots`에
   `provider="antigravity"` 행이 남아 있어도, 부트 복원 루프에서 그 행만 `continue`로 버린다.
   ★이게 없으면 코드에서 시딩을 지워도 **우리 기기·참가자 기기의 과거 analytics.db 기록으로
   계정이 되살아난다**(브리프 §0 항목2의 핵심 우려). `seed_known_drops_antigravity_snapshot_rows`
   시험이 이 필터가 antigravity만 정확히 겨누는지(다른 provider 행은 안 지운다) 함께 확인한다.
4. **주석 정리**: `AccountKey.provider`·`AccountView.label`·`AccountView.source` 필드 주석에서
   antigravity/agy 어휘 제거(더 이상 유효한 값이 아니므로).
5. **`resolve_agents` 시험 갱신**: `gemini`/`agy`/`antigravity` 세 문자열 전부 `resolve()`가
   `None`을 내는지로 바꿨다(구판은 `gemini`가 antigravity 계정으로 귀속된다고 단언했었다).

## `ui/src/wsusage.test.ts` — antigravity 픽스처 교체
- UI(`wsusage.ts`)는 `provider` 문자열을 **특별 취급하지 않는다**(grep 확인 — `accountRates`·
  `scopedRates` 어디에도 antigravity/agy 분기 없음). 그래서 소스 쪽은 무접촉이고, **픽스처만**
  실물 antigravity 값 대신 provider-중립 커스텀 계정(`grok`/`accounts.json adapter:"cmd"` 형태)
  으로 바꿨다 — 같은 시나리오(등록만 되고 미관측인 계정·죽은 창 stale 판정)는 그대로 보존된다.
  값(실측 6.138…%·8.881…%·타임스탬프)은 원본 그대로 뒀다 — "픽스처를 예쁘게 다듬으면 초록불이
  거짓이 된다"는 이 파일 자체의 규율을 지켰다.
- `main.ts`의 `refreshUsageAccounts`도 확인 — antigravity/agy 특별 취급 없음 → 무접촉.

## 범위 밖(브리프 §0/2-4, 무접촉 확인)
- `usage.rs`의 `update_agy_usage`·`collect_agy_for` 등 surface 단위 `observed_usage`(agy 노드
  CTX 관측) 경로 — 노드 CTX 감시는 계정 표와 별개이므로 손대지 않았다.
- 팩(`cysjavis-pack/`)·`directives/`·`agents.json` — agy는 리뷰어 에이전트로 그대로 존속.

## 시험 실측 (기준선 → 결과)
★기준선은 별도 stash 실행이 아니라 **원본 소스 직독**(수정 전 accounts.rs 전문을 읽고 기존
`#[test]` fn 10개를 직접 셈)으로 얻었다 — 이후 뮤턴트 재삽입/재삭제 실사격(아래 절)으로
델타가 정확히 신규 3건분임을 교차 확인했으니 추정이 아니다.

| 항목 | 기준선(원본 직독) | 결과(실측) |
|---|---|---|
| `cargo test -p cys-terminal --bin cysd`(accounts.rs만) | 10 passed | **13 passed**(+3 신규) |
| `cargo test -p cys-terminal --bin cysd`(전체) | 960 passed·1 ignored | **963 passed·1 ignored**(+3) |
| `bun test`(ui 전체) | — | **858 pass·0 fail**(3065 expect) |
| `bun test wsusage.test.ts` | — | **70 pass·0 fail** |
| `bun run typecheck` | 사전 실패 8건(비관련) | **동일 8건**(main.ts import 3·암묵 any 5·headerlabels/updateplan의 `toMatch` 3 — 전부 이 티켓 무관 파일·구간, `cys-typecheck-fails-on-pristine-upstream` 기지 사실과 일치) |
| 비밀 스캔 | — | `scripts/secret-scan.sh` clean(mode=staged·2파일) |

## 뮤턴트 검증 (실측)
`seed_known()`의 antigravity 시딩 블록을 원본 그대로 재삽입 →
`seed_known_ignores_antigravity_dir` 시험이 **FAILED**(`~/.antigravity 존재만으로 계정이
등록됐다`)로 적색 전환 확인 → 블록 재삭제 → 13개 시험 전부 재통과 확인. 그물이 실제로
그 축을 잡는다는 것을 실사격으로 증명했다(공허한 통과 아님).

## 4군(비가역·비용) 결정
해당 없음 — 앱 빌드·릴리스·`/Applications/cys.app`·`~/.cys` 접촉 없음(브리프 §3대로).
로컬 커밋 + `git push -u origin fix/v110-usage-noagy`만 실행.

## 커밋
`(TICKET=usage-noagy)` — 커밋 sha는 이 파일과 같은 커밋에 실린다(git log 참조).

## 남긴 것 / 다음
- `accounts.rs` 하단 `AGY_OBS`/`AGY_5H_RESET`/`AGY_7D_RESET`/`AGY_NOW` 상수(≈옛 라인
  1158~1161)는 **그대로 뒀다** — 이건 `rate_window_stale_reason`(provider 무관 순수 함수)의
  회귀 시험이 쓰는 실측 숫자일 뿐, antigravity를 유효 provider로 취급하는 코드가 아니다.
  브리프 범위(§0 읽기 범위)와 §5 외과적 변경 원칙상 손대지 않는 것이 맞다고 판단했다 — 이견
  있으면 별도 티켓으로.
- 증류 대상 없음(이 작업은 국지적 provider 제거라 새 스킬·장기기억으로 남길 일반화된 교훈은
  없다고 판단 — 이견 있으면 지적 바란다).
