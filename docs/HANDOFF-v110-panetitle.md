# HANDOFF — TICKET=v110-panetitle (B14 페인 제목 규칙 · B16 배치 고정)

작성 2026-09-20 · 워커 surface:874 · 브랜치 `fix/v110-panetitle`(← `rebase/v1.0.2` 54c148cc) · 커밋 73be539c

---

## 1. 무엇이 문제였나 — 결함은 셋이 아니라 하나였다

오너 관측(2026-09-19 윈 cysr 1.0.2 실기): 「페인 제목에 서피스 번호·모델 표시·역할 키워드가 없다」.
세 가지가 빠진 것으로 보였지만 원인은 하나다.

| 조각 | 누가 만드나 | 왜 없었나 |
|---|---|---|
| 번호 | **아무도 안 만들었다** | CLI `workflow_title()`(`src/bin/cys.rs:12547`)은 `{role}-{agent} · {폴더}` 만 만든다. 번호는 `surface.create` **응답**에서야 정해지므로(`src/bin/cysd/state.rs:3185` `next_id.fetch_add`) CLI 가 만들 수 없다. |
| 모델 | 이미 데몬이 만든다 | `src/bin/cysd/panetitle.rs` `retitle_with_model()` — `handlers.rs` 의 `usage.report` 에서 statusline 마다 호출. **완비돼 있었다.** |
| 역할 특성 | CLI 가 폴더명으로 넣고 있었다 | 있었지만 `worker-claude · 폴더` 모양이라 오너 규칙(`번호 · 모델 · 특성`)과 달랐다. |

★도미노: `retitle_with_model` 은 **첫 조각이 숫자가 아니면 무접촉**이다(`panetitle.rs`). 번호가 없으니
모델 칸도 영원히 안 붙었다. ⇒ **번호 하나가 첫 조각이고, 그것만 세우면 모델 칸은 코드 변경 0으로 따라 붙는다.**

우리 개발 기기에 제목이 제대로 보이는 이유: `~/.cys/pack/bin/javis_panetitle.py` 가 번호를 붙여 주는데,
그 파일은 **이 저장소에 없다**(`cysjavis-pack/` 전수 0건 · git log 전 브랜치 0건). 우리 기기 전용 자산이라
참가자에게 배포된 적이 없다.

---

## 2. B14 — 무엇을 했나

**층위 = 데몬 `surface.create` 핸들러**(master 판정 2026-09-20 · 선택지 A 팩 3곳/B CLI 1곳/C 데몬 1곳 중 C).

- 로직: `src/bin/cysd/panetitle.rs` `initial_title(sid, role, cwd, requested, agent) -> Option<String>`
- 배선: `src/bin/cysd/handlers.rs` `surface.create` 의 `Ok(s) =>` 블록 첫머리 1곳.

한 곳이 생성 경로 전부를 덮는 근거(실측):

- `cys launch-agent` → `run_launch_agent_opts`(`cys.rs:12559`) → `surface.create`(`cys.rs:12635`)
- `cys restore`(`cys.rs:14769`) → **같은** `run_launch_agent_opts`
- GUI(Tauri) `create_surface` → 같은 RPC

### 규칙과 무접촉 4조건

제목 = `<번호> · <역할특성>` (모델 칸은 첫 statusline 턴에 데몬이 삽입 → `<번호> · <모델> · <역할특성>`).
create 시점에는 모델 관측이 없으므로 **여기서 모델을 지어내지 않는다.**

- 역할특성: `master`·`cso`(및 서수판) = **역할명** / 그 밖 = cwd basename, 단 범용 폴더명이면 role 폴백
  (`javis_panetitle.py` 의 GENERIC_DIRS·`re.sub(r"-(\d)", r"\1", role)` 규칙을 그대로 옮김 = 문자열 동형).
- ①role 없으면 무접촉 — UI 가 `live_cwd` 를 실시간 표시하는 셸을 죽이지 않는다.
- ②이미 **내 번호**로 시작하면 무접촉(멱등 · 우리 기기 `javis_panetitle.py` 선착분과 충돌 0).
  경계는 공백이거나 끝이다 — `87` 이 `874` 를 삼키지 않는다.
- ③exited 무접촉 — 이 자리에서는 **구조적으로 성립**한다(방금 만든 좌석은 exited 일 수 없다).
  ⚠일부러 분기를 만들지 않았다. 영원히 안 밟히는 가드는 검증도 안 되는 장식이기 때문이다.
- ④사용자 지정 이름 보존 — 지우지 않고 **번호만 앞에 붙인다**(`내 작업창` → `5 · 내 작업창`).
- 부가: 남의 번호를 물고 온 제목은 번호 칸만 교체한다(`285 · research` → `60 · research`).
  쌓지 않는 이유 = 안 그러면 `60 · 285 · research` 가 된다.

---

## 3. B16 — 무엇을 했나 · **B17 이 부를 함수(브리프 요구 항목)**

**층위 = UI.** 배치는 데몬·CLI 에 원시수단이 없다(아래 §5 한계 참조). 새 모듈 `ui/src/formation.ts`.

```ts
// ui/src/formation.ts
export type Seat = { sid: number; role?: string | null };
export const MASTER_CSO_RATIO = 4 / 5;            // 오너 확정 4:1

export function formationLayout(
  seats: Seat[],                                   // 좌→우 순서 보존(입력 순서)
  opts?: { masterCsoRatio?: number },
): LayoutNode | null;                              // null = 배치할 것 없음(트리 무접촉)

export function formationIfRowOnly(
  tree: LayoutNode,
  roleBySid: Map<number, string | null | undefined>,
): LayoutNode;                                     // 입력과 같은 객체 = 무접촉(사용자 col 배치 존중)

export function hasHqSeats(
  roleBySid: Map<number, string | null | undefined>,
): boolean;                                        // 본부 역할이 cys 좌석으로 존재하는가 = 이 배치의 전제

export function leftColumnShare(workerCount: number): number;  // 좌열 가로 몫(워커 수에 따라 1/2→1/3 수렴)
```

**B17 이 호출할 것**: 재시작 잔재를 정리한 **직후** `formationIfRowOnly(ws.tree, roleBySid)` 를 부르면
배치가 3경로와 같아진다. exited 좌석을 닫은 뒤 `roleBySid` 를 다시 만들어 넘겨라(닫힌 좌석이 섞이면
그 sid 가 열을 하나 차지한다).

### 배치 규칙
- 좌열 = master(위) : cso(아래) = **4:1**(세로 분할) · 우열 = 나머지 좌석 가로 균등(늘면 오른쪽 분할)
- 좌열 가로 몫 = `max(1, w/2) / (max(1, w/2) + w)` — 워커가 늘수록 1/3 수렴.
  ★이 수렴값은 **이미 출고된** `adoptLayout`(master 가중 `max(1,(n-1)/2)`)과 같다 — 체감이 바뀌지 않게 맞췄다.

### 3경로 (전부 같은 함수)
| 경로 | 위치 |
|---|---|
| 첫 설치·평시 입양 | `ui/src/main.ts` `refreshPaneTitles()` 입양 블록 뒤 |
| 재시작(복원) | `ui/src/main.ts` 복원 병합 루프 끝 |
| 「정렬」 버튼 | `ui/src/main.ts` `actionEqualize()` |

### ★2026-07-27 「되돌리지 마라」와의 관계 — 되돌린 것이 아니다
`main.ts` 정렬 절 주석은 역할별 4열 안을 폐기하며 **전제**를 근거로 들었다:
「지금 master·CSO 는 cmux 페인이라 cys 에는 역할로 열을 묶을 전제가 없다」.
그 전제는 **우리 개발 기기에만** 참이다 — 참가자 기기에서는 셋 다 cys 좌석이다
(오너 윈 실기 2026-09-19 16:2x: 29 worker · 30 master · 31 cso).
⇒ 그 주석 자신의 논리(「전제가 달라졌으므로 설계도 달라진다」)에 따라, **전제가 성립하는 기기에서만**
켜지도록 `hasHqSeats()` 로 게이트했다. 거짓이면 종전 `adoptLayoutIfRowOnly` 경로 그대로 = 우리 기기 무회귀.

그날의 **붕괴 기전**(⑴빈 역할 버킷 ⑵`evenComb` 이 노드 1개면 래퍼를 삼켜 요청한 row 가 소멸)은
설계 제약으로 삼았다: 빈 버킷은 열을 만들지 않고, 열이 하나면 **래퍼를 요구하지 않는다**.
전원 워커 7기(그날의 구성)를 그대로 태우는 시험으로 고정했다.

---

## 4. 실측 증거 (전부 이 티켓에서 직접 돌린 것)

| 항목 | 결과 |
|---|---|
| `cargo test --bin cysd` | **972 passed · 0 failed** (1 ignored) |
| `cd ui && bun test` | **869 pass · 0 fail** (29 파일) |
| `ui` typecheck | 기준선(54c148cc 사본) 15건 ↔ 현재 15건 · **신규 0** |
| B14 뮤테이션 | **9/9 KILLED** |
| B16 뮤테이션 | **10/10 KILLED** |
| 격리 데몬 3좌석 | **3/3** — `1 · master` · `2 · cso` · `3 · w1` |
| 대조군(역할 없음) | `surface 4` **무접촉** ✅ |
| 대조군(사용자 이름) | `5 · 내 작업창` **보존** ✅ |
| 재기동 뒤 생성 | **3/3** — `1 · master` · `2 · cso` · `3 · w2` |
| 라이브 무접촉 | 격리 소켓 `/tmp/b14gate.*/cys.sock` · 라이브 cysd pid 62178 **불변** · 잔여 프로세스 0 |

### 재현 명령

```bash
W=~/axdev/.wt/cys-v110-panetitle
cd $W && cargo build --bin cysd          # ★반드시 build — cargo test 는 target/debug/cysd 를 갱신하지 않는다(§5 함정1)
cargo test --bin cysd panetitle          # 21 tests
(cd ui && bun test formation)            # 11 tests
# 격리 게이트
D=$(mktemp -d /tmp/b14gate.XXXX); S=$D/cys.sock
CYS_SOCKET=$S $W/target/debug/cysd > $D/cysd.log 2>&1 &
mkdir -p $D/hq/cso $D/hq/workers/w1
cys --socket $S new-surface --role master --cwd $D/hq --cmd /bin/sh
cys --socket $S new-surface --role cso    --cwd $D/hq/cso --cmd /bin/sh
cys --socket $S new-surface --role worker --cwd $D/hq/workers/w1 --cmd /bin/sh
cys --socket $S list                     # 기대: 1 · master / 2 · cso / 3 · w1
```

---

## 5. 함정 · 한계 (다음 사람이 반드시 알아야 할 것)

1. ★**`cargo test --bin cysd` 는 `target/debug/cysd` 를 갱신하지 않는다.** 테스트 하네스만 빌드한다.
   이 티켓에서 실제로 밟았다 — 편집 뒤 낡은 바이너리로 게이트를 돌려 **거짓 음성**(제목 `surface 1`)을
   한 번 받았다. 격리 데몬을 띄우기 전에 `cargo build --bin cysd` 를 반드시 먼저 돌려라.
   판별법: `stat -f '%Sm %N' target/debug/cysd src/bin/cysd/*.rs` 로 시각 대조.
2. **에이전트 없는(`agent=null`) 좌석은 auto-restore 대상이 아니다.** 그래서 「재기동 뒤 3/3」은
   *복원된 좌석*이 아니라 *재기동한 데몬에서 새로 만든 좌석*으로 쟀다. 복원 경로가 번호를 얻는 근거는
   코드 축이다(`cys restore` → `run_launch_agent_opts` → 같은 `surface.create`). 실기기 복원 3/3 은
   **VM 티켓에서 확인해야 한다**(브리프 해소 판정: 깨끗한 VM 설치 캡처 + 재부팅 복원 뒤 유지).
3. **B16 배치 캡처 미수행.** 배치는 UI 층이라 `cys read-screen` 으로 안 보이고 GUI 실행이 필요하다.
   이 티켓에서는 순수 함수 시험 + 뮤테이션 10종으로만 고정했다. 실제 화면의 4:1 은 VM 캡처로 재라
   (렌더는 `renderNode` 가 `ratio` 를 그대로 flex 비율로 쓰므로 트리 비 = 화면 비다).
4. **`topology.json` 의 `title` 은 마지막 상태가 아닐 수 있다.** `persist_topology` 가 create 내부에서
   먼저 돌고 제목 부여는 핸들러에서 그 뒤에 일어나, 마지막에 만든 좌석의 항목은 번호 이전 제목을 담는다.
   **무해한 이유**: `cys restore` 는 `entry["title"]` 을 **읽지 않고** 제목을 다시 짓는다(실측 — `cys.rs:14603~14900`
   에 `title` 참조 0건). 신경 쓰인다면 번호 부여를 `create_surface_with_env` 안으로 내리면 되지만,
   그 파일(`state.rs`)은 다른 소유자라 이 티켓 범위 밖으로 뒀다.
5. **`surface.rename` 에는 ACL 이 없다**(소켓을 열 수 있는 누구나 남의 제목을 바꾼다 —
   `docs/verdict-pane-title-numbering-2026-07-27.md` 의 기존 감사와 같은 결론). 이 티켓은 그 표면을
   넓히지도 좁히지도 않았다(우리는 create 안에서 자기 좌석만 건드린다).
6. **`adoptlayout.ts` 는 이제 「전제 없는 기기」 전용 폴백**이다. 본부 역할이 cys 좌석인 기기에서는
   `formation.ts` 가 그 자리를 대신한다. 두 모듈의 수렴값(좌열 1/3)을 일부러 맞춰 놨으니
   통합 티켓에서 하나로 접을 때 그 값을 기준으로 삼아라.

## 6. 판번(브리프 요구 실측)

`1.0.2` 의 단일 출처 = **`src-tauri/tauri.conf.json` 의 `"version"`**.
`scripts/build-macos-signed.sh:21` 과 `.github/workflows/release.yml:630` 이 그 파일을 `grep -m1` 으로
읽어 자산 이름 `cysr_${VERSION}_${ARCH}` 를 만든다. `src-tauri/Cargo.toml:3` 도 `1.0.2` 로 동기돼 있다.
⚠브리프의 「tauri.conf.json 은 0.14.37」은 이 브랜치에서 **거짓**이다(실측 `1.0.2`).
이 티켓은 판번을 바꾸지 않았다.

---

## 7. §v1.1.1 — 특성 칸 규칙 개정 (TICKET=v111-panetitle · 2026-09-21)

### 7-1. 오너 지시와 관측
오너 원문(2026-09-21 08:2x · 윈 1.1.0 갱신 실기 08:15 캡처를 보고):

> 「현재 머리글을 보면 번호+모델 이후 내용이 너무 길다. master, cso 하나면 충분하고, 워커도
> 맡은 역할 키워드 1나면 된다. 없으면 worker1이고」

그때 화면에 있던 제목 = `38 · Opus · master-claude · install-jarvis` (네 칸).

### 7-2. 왜 네 칸이 됐나 — 원인은 두 겹이다(둘 다 코드 실측)
1. **특성을 cwd basename 에서 뽑았다**(§2 의 1.1.0 규칙). 폴더 이름(`install-jarvis`)이 제목에 들어온다.
2. **`cys launch-agent` 의 `surface.create` 페이로드에 `agent` 키가 없다**(`src/bin/cys.rs:12635`).
   ⇒ create 시점 `agent_meta` 가 `None` ⇒ 1.1.0 의 `is_machine_title` 이 `{role}-{agent}` 를 대조할
   재료를 못 얻어, CLI 가 지은 `master-claude · install-jarvis` 를 **무접촉 ④(사람이 지은 이름)** 으로
   판정하고 번호만 앞에 붙였다. 즉 role-agent 결합명은 **가드가 의도대로 작동한 결과**로 살아남았다.

★그래서 1번만 고치면 참가자 기기 제목은 그대로였다 — 특성 산출 함수에 **도달조차 하지 않는다**.
이 자리가 이 티켓에서 가장 중요한 발견이다(브리프는 1번만 지목했다).

### 7-3. 새 규칙 — 특성은 role 하나에서만 나온다 (cwd 미참조)

| role | 특성 | 근거 |
|---|---|---|
| `master` / `master-2` | `master` / `master2` | 역할명 자체가 특성(좌석 폴더가 그 노드를 말해 주지 않는다) |
| `cso` / `cso-2` | `cso` / `cso2` | 〃 |
| `worker-eduscan` | `eduscan` | 맡은 역할 키워드 1단어 |
| `worker-research` | `research` | 〃 |
| `worker` | `worker1` | 키워드 없음 → 머리+서수 |
| `worker-3` | `worker3` | 서수 = 생성 순(role 서수를 배정하는 쪽이 생성 순으로 준다) |
| `reviewer-gemini` / `reviewer-codex` | `gemini` / `codex` | 키워드 규칙 동형 — ⚠브리프 괄호 예는 `reviewer1` 이었다(§7-6 미결 1) |
| `reviewer` | `reviewer1` | 키워드 없음 |

결과 = `38 · Opus · master` · `36 · Opus · cso` · `37 · Opus · worker1` · `41 · Sonnet · eduscan`.

**무접촉 4조건은 그대로다**(규칙이 바뀌어도 경계는 안 바뀐다). 모델 칸의 주인(`retitle_with_model`)도
그대로다 — create 는 번호·특성만 세우고 첫 statusline 턴에 모델 칸이 붙는다.

### 7-4. 위 2번에 대한 봉합 — 기계 제목 판정 = **생산자 출력의 정확 재구성**
- 판정은 추측이 아니라 **재구성**이다. 두 생산자 모두 정의가 저장소 안에 있다:
  `surface {id}`(데몬 기본값) · `{role}-{agent}` / `{role}-{agent} · {cwd basename}`(CLI `workflow_title`).
- agent 를 알면 그 이름 하나로, 모르면(현 launch-agent 페이로드) **닫힌 어휘**
  `AGENT_NAMES = [claude, gemini, codex, grok]` 을 차례로 넣어 재구성하고 **전체 일치**만 인정한다.
- ★cwd 는 **알아보는 데만** 쓴다(특성을 짓는 데는 안 쓴다 — v1.1.1 규칙). 이 대조가 빠지면
  사람이 지은 `worker-claude · 회의록` 이 기계 제목으로 오인돼 「회의록」이 지워진다.
  ⇒ 이것은 가정이 아니라 **agy 이종 리뷰 R1 이 반례로 제시**했고(문제점 1), 그 지적을 수용해
  접두 휴리스틱을 전체 일치로 바꾼 것이다. 뮤턴트 M4 가 그 축을 잰다(접두로 되돌리면 적색).
- ★재구성이 빗나가면(다른 cwd·어휘에 없는 새 에이전트) 판정은 false 로 떨어져 제목이
  **사람 이름처럼 보존**된다 — 길어질 뿐 잃는 것은 없다(**안전 방향**).
  항구 처방은 호출부가 agent 를 싣는 것이다(§7-6 미결 2 = 1.1.2 티켓).

### 7-4-1. 번호가 이미 붙은 네 칸 제목의 단축 (agy R1 문제점 3 수용)
무접촉 ②(이미 내 번호로 시작하면 무접촉)를 글자 그대로 두면, 1.1.0 이 지은
`38 · Opus · master-claude · install-jarvis` 는 **번호를 갖고 있다는 이유로 영구 방치**된다 —
이 티켓의 목적이 그 기기에서 달성되지 않는다. 그래서 ② 안에서 한 겹 더 본다:
번호(와 모델 칸)를 떼어 낸 **본문이 기계 제목이면 규칙대로 다시 짓고**, 아니면 종전대로 무접촉.
모델 칸은 있는 그대로 옮긴다(그 칸의 주인은 `retitle_with_model` 이다).
· 실측: `38 · Opus · master-2-claude · install-jarvis` → `6 · Opus · master2`(번호는 자기 것으로).
· 사람 이름은 여전히 안 건드린다: `60 · worker-claude · 회의록` → 무접촉.

### 7-5. 증거 (전부 이 티켓에서 직접 돌린 것)
```
ⓐ cargo test --bin cysd panetitle        → 21 passed / 0 failed
   cargo test --bin cysd (전건)            → 982 passed / 0 failed / 1 ignored (rc 0)
   cargo test --bin cys workflow_title    → 1 passed (CLI 미변경 확인)
ⓑ 뮤턴트 9/9 KILLED (기준선 초록 선확인 · 변이 디스크 선-assert · 복원 finally)
   M1 master·cso 분기 제거                   → 5건 적색
   M2 worker1 서수 누락                      → 4건
   M3 worker-3 가 3 이 됨                     → 3건
   M4 기계 제목 판정을 접두 휴리스틱으로 완화   → 1건(사람 이름 꼬리 유실 축)
   M5 멱등 무접촉 제거                        → 4건
   M6 한 단어 가드(one_word) 제거             → 2건
   M7 레거시 단축 제거                        → 1건
   M8 특성 산출 되돌림(꼬리 오염)              → 4건
   M9 정화 순서 되돌림                        → 2건
   ★M8 자리에 처음 뒀던 「split_role 의 trim 제거」는 **SURVIVED** 였다 — one_word 가 그 trim 을
     흡수하므로 구별되지 않는 **등가 뮤턴트**였다. 그래서 중복 trim 을 코드에서 지웠다(§7-5-1).
ⓒ 격리 cysd(디버그 · /tmp 짧은 소켓 · HOME 격리 · CYS_BOOT_GATES=0 · killpg · 라이브 무접촉)
   [A] create 직후        1 · master  2 · cso  3 · worker1  4 · eduscan
                          5 · worker-2-claude · 회의록      ← 사람이 지은 이름은 보존
   [B] usage.report 1회 뒤 1 · Opus · master  2 · Opus · cso  3 · Opus · worker1  4 · Sonnet · eduscan
   [C] 레거시 네 칸 제목 투입(`38 · Opus · master-2-claude · install-jarvis`) → `6 · Opus · master2`
```
재현: 입력을 참가자 기기와 같게 넣는다 — `cys new-surface --role <role> --cwd <폴더> --title
"<role>-claude · <폴더 basename>"`(agent 키 없음) 뒤 `usage.report {surface_id, model}` 1회.
⚠title 의 폴더와 `--cwd` 의 basename 이 **어긋나면** 기계 제목 재구성이 빗나가 제목이 보존된다
(설계상 안전 방향이지만, 재현 실패를 결함으로 오독하기 쉽다 — 실제 CLI 는 둘을 같은 값으로 낸다).

### 7-5-1. 「한 단어」 가드(one_word) — 왜 뒀나
데몬은 role 문자열의 **글자를 검증하지 않는다**(`surface.create` 의 `--role` 은 임의 문자열 · 저장소
전수 grep 에서 role charset 검증 0건). 공백이 섞이면 제목 한 칸이 두 낱말이 되고, 구분자(` · `)가
섞이면 **없던 칸이 하나 생겨** 모델 칸 판정(`retitle_with_model`)이 엉뚱한 조각을 집는다.
`one_word()` 는 그 구조 오염만 막는다 — **실 입력에는 무동작**이다(우리 생산자가 내는 role 에는
공백이 없다). 도달 불가한 장식이 아니라는 근거 = 임의 caller 가 그 role 을 보낼 수 있다는 것이고,
뮤턴트 M6 이 그 축을 잰다.

### 7-5-2. 이종 검증 라운드 (agy R1 · 2026-09-21)
`agy -p`(gemini) 1라운드 = **REVISE 4건**. 처리:
| 지적 | 판정 | 처리 |
|---|---|---|
| ①접두 판정이 `worker-claude · 회의록` 을 먹는다 | **수용** | 판정을 생산자 출력 **전체 일치 재구성**으로 교체(§7-4) · 뮤턴트 M4 |
| ②-1 `master - 2` 가 master 분기를 놓친다 | **수용** | `one_word` 정화를 조립 **전**으로(§7-5-1) · 뮤턴트 M9 |
| ②-2 `worker-a-b` 의 하이픈 | **반박** | 하이픈은 공백이 아니다 — `eduscan-daily` 는 한 낱말이고 `reviewer-gemini → gemini` 와 같은 계열이다. 계약은 「공백·구분자·보이지 않는 글자 없음」으로 명시(시험 표에 `worker-eduscan-daily` 고정) |
| ②-3 제로폭 공백(U+200B)이 통과한다 | **수용** | 금지 목록 대신 **허용 구조**(영숫자·하이픈·밑줄만 남김)로 전환 · 뮤턴트 M6 |
| ③번호 붙은 네 칸 제목이 영구 방치된다 | **수용** | ② 안에서 본문이 기계 제목이면 단축(§7-4-1) · 뮤턴트 M7 · 격리 실측 [C] |
| ④시험 표에 이상한 role 이 없다 | **부분 반박** | 지적 시점의 판본에는 이미 `my worker`·`worker- 2`·`a · b`·NBSP 가 들어 있었다(리뷰어가 받은 전문이 그 편집 **이전** 것이었다). 그럼에도 U+200B·탭·`·`(이름이 안 남는 role)을 추가했다 |

### 7-6. 미결 · 함정 (다음 사람이 반드시 알아야 할 것)
1. **reviewer 계열 특성 — 확정됐다**(master 판정 `[master#6f1fee58]` 2026-09-21 08:39:58 · 원장 4요건
   성립). `reviewer-gemini → gemini` · `reviewer-codex → codex` 로 **A 채택**. 근거 = 오너 규칙
   「맡은 역할 키워드 1단어」와 같은 판정이고 화면에서 리뷰어가 갈린다. 브리프 괄호 예(`reviewer1`)는
   예시였고 **문면보다 규칙이 우선**한다는 것이 그 판정의 내용이다. (`reviewer` 단독은 여전히 `reviewer1`.)
2. **⑵ 항구 처방 = 1.1.2 티켓**(master 판정 `[master#6f1fee58]` — 별도 티켓 채택. 이 티켓은 아래 봉합으로
   커밋한다). **`launch-agent` 페이로드에 agent 키 싣기**는 이 티켓에서 **하지 않았다**. `agent_meta` 가 create
   시점에 채워지면 사망 감지(`governance` agent_seen)·topology 영속·형제 create ACL 까지 함께 움직인다
   — 제목 티켓의 외과 범위를 넘는다. 별도 티켓으로 올렸고, 그때 `handlers.rs:4762` 주석이 적은
   「agent_meta=None 이라 topology 에 agent 없이 영속돼 콜드부트 부활이 그 역할을 제외한다」가 함께 닫힌다.
3. **우리 맥의 라이브 팩 `~/.cys/pack/bin/javis_panetitle.py` 는 여전히 cwd basename 규칙이다**
   (읽기만 함 · 라이브 무접촉 · master 접수 `[master#6f1fee58]`: 무접촉 유지 · 우리 맥 1.1.1 갱신 때
   master 가 유지보수 창에서 정렬한다 · 저장소 대상 없음 확인). 그 스크립트를 돌리면 **우리 기기에서만** 제목이 옛 규칙으로 되돌아간다.
   ⚠저장소에는 이 파일이 **없다**(`cysjavis-pack/bin/javis_panetitle.py` 부재 — grep 확정). 그래서
   이 티켓의 「동형 수정」 대상이 repo 안에 없다. 팩 갱신은 master 게이트.
4. **이미 떠 있는 좌석은 안 고쳐진다** — `initial_title` 은 create 에서만 돈다. 업데이트 뒤에도 기존
   페인은 옛 제목을 유지하고, 다음 `launch-agent`·`restore` 때 새로 지어진다(restore 는 저장된 제목이
   아니라 `workflow_title` 을 다시 계산해 보낸다 — `src/bin/cys.rs:12635`).
5. **기계 제목 재구성은 cwd 에 의존한다** — 데몬이 들고 있는 `s.cwd` 와 CLI 가 `workflow_title` 에
   쓴 cwd 가 어긋나면(경로 정규화·심볼릭 링크 등) 재구성이 빗나가 제목이 **길게 보존**된다.
   안전 방향이지만 「왜 안 짧아지지」의 1번 확인 항목이다(격리 실측에서는 둘이 같아 4/4 일치).
