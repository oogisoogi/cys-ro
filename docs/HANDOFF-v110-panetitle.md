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
