// 워크스페이스 복원 **배선** 회귀 핀 — main.ts 소스를 데이터로 읽어 계약을 단언한다
// (typegate.test.ts 관례: 런타임 코드 0줄 · 본체에서 import 되지 않는다 · DOM/Tauri 불요).
//
// ★왜 판정 테스트(wsreconcile.test.ts)만으로 부족한가 (2026-09-16 성찰 1회 지적):
// 이번 실사고에서 실제로 틀린 것은 **판정이 아니라 배선**이었다. 순수 함수는 옳아도
//   · main.ts 가 그 함수를 부르지 않거나
//   · 복원 체인의 await 하나가 시간 상한을 빠뜨리거나
//   · 되살아난 옛 술어 한 줄이 남아 있으면
// 화면은 그대로 사라진다. 실제로 성찰 1회가 찾은 blocker 는 '복원 체인의 마지막 두
// newSurface 만 상한을 빠뜨린 것'이었다 — 사람이 한 줄씩 세는 방식으로는 반드시 다시 빠진다.
// 그래서 배선을 기계가 센다. 여기 실패는 "고쳐 두었다고 믿는 것이 코드에 없다"는 뜻이다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

const MAIN_URL = new URL("./main.ts", import.meta.url);
const src = readFileSync(MAIN_URL, "utf-8");
/** 주석을 걷어낸 코드 본문 — '코드에 있는가'를 묻는 핀은 주석에 속으면 안 된다(설명문이 핀을 깨뜨린다). */
const code = src
  .split("\n")
  .map((l) => (l.trimStart().startsWith("//") ? "" : l.replace(/\s\/\/.*$/, "")))
  .join("\n");

/** start() 의 세션 복원 블록만 잘라낸다 — 트리 재구성 계약은 그 구간에만 적용된다. */
function restoreSlice(): string {
  const a = src.indexOf("// Session restore (멀티마스터 F4)");
  const b = src.indexOf("started = true;", a);
  expect(a).toBeGreaterThan(0); // 구간 앵커가 사라졌다 = 이 핀이 무엇도 지키지 않는다
  expect(b).toBeGreaterThan(a);
  return src.slice(a, b);
}

/**
 * start() **전체**(머리부터 `started = true` 까지). 시간 상한 계약은 여기에 적용된다.
 * ★왜 복원 블록만으로는 부족한가(2026-09-16 성찰 2회 blocker): 화면을 영구 백지로 만든 두 번째
 * 무상한 왕복은 복원 블록 **직전**의 기본 소켓 `daemon_status` 였다. 좁은 슬라이스는 그 자리를
 * 사정권 밖에 두었다 — 핀의 사정권이 결함의 사정권보다 좁으면 그 핀은 종이 방벽이다.
 */
function startSlice(): string {
  const a = src.indexOf("async function start() {");
  const b = src.indexOf("started = true;", a);
  expect(a).toBeGreaterThan(0);
  expect(b).toBeGreaterThan(a);
  return src.slice(a, b);
}

describe("복원 배선 — 판정 모듈이 실제로 꽂혀 있다", () => {
  it("★옛 차별 술어가 되살아나지 않았다 (`ws.socket != null && lb?.ok === true`)", () => {
    // 이 한 줄이 재부팅 후 본부 5팀을 화면에서 지웠다. 되살아나면 즉시 red.
    expect(code.includes("ws.socket != null && lb?.ok === true")).toBe(false);
  });

  it("복원 필터가 keepWorkspaceOnRestore 를 쓴다(판정 인라인 복제 금지)", () => {
    expect(restoreSlice().includes("keepWorkspaceOnRestore(")).toBe(true);
  });

  it("존재 진실원 보강이 missingKnownWorkspaces 를 쓴다", () => {
    expect(restoreSlice().includes("missingKnownWorkspaces(")).toBe(true);
  });

  it("3초 틱의 유령 수렴이 advanceGhostStrikes 를 쓴다(2연속 게이트 인라인 복제 금지)", () => {
    expect(src.includes("advanceGhostStrikes(")).toBe(true);
  });
});

describe("복원 배선 — 체인의 모든 대기에 시간 상한이 있다", () => {
  // 먹통(accept 후 무응답) 데몬 하나가 start() 를 붙잡으면 **탭이 하나도 렌더되지 않는다**.
  // 상한이 빠진 await 가 한 곳만 있어도 그 결함이 통째로 되살아난다.
  it("★복원 구간의 newSurface 호출은 전부 상한 인자(T_NEW)를 넘긴다", () => {
    // 줄 단위로 본다 — `newSurface(null, current().socket, T_NEW)` 처럼 인자에 괄호가 들어가면
    // 괄호 균형을 안 맞추는 정규식이 첫 `)` 에서 끊겨 T_NEW 를 놓친다(핀이 조용히 무력해진다).
    const lines = restoreSlice().split("\n").filter((l) => l.includes("newSurface("));
    expect(lines.length).toBeGreaterThan(0); // 호출이 사라졌다면 이 핀은 무의미해진다
    for (const l of lines) expect(l).toContain("T_NEW");
  });

  // 기동 구간이 직접 부르는 **데몬 왕복** 목록(이름이 계약이다 — 늘어나면 여기 추가).
  const DAEMON_CMDS = [
    "list_depts",
    "dept_tombstones",
    "daemon_status",
    "launch_dept_daemon",
    "list_surfaces",
    "create_surface",
    "org_status",
    "factory_reset_preview",
  ];
  // 상한 대신 **다른 방식으로 유계**임이 감사된 예외. 새로 추가하려면 여기에 이유와 함께 적어야 한다
  // (= 사람이 한 번은 의식적으로 판단하게 만드는 것이 이 목록의 목적이다).
  const AUDITED_UNBOUNDED = [
    // 300ms 데몬 대기 프로브: rpcT 로 감싸지 않는 대신 claimFlight 재진입 가드로 동시 1건을
    // 보장하고, 대기가 어떤 경로로 풀리든 stop() 이 인터벌을 회수한다(무계 적체 없음).
    'const call = invoke("daemon_status");',
  ];

  it("★기동 구간의 데몬 invoke 는 **전수** 검사한다 — 맨몸 호출이 새로 들어와도 잡힌다", () => {
    // ⚠종전 핀은 `(\w+)\(invoke\("cmd"` 로 **이미 감싸인 것만** 셌다. 래퍼가 아예 없는 줄은
    // 매치 0건이라 배열에 들어가지도 않아, 같은 커맨드의 rpcT 판이 하나라도 있으면 초록이었다
    // — 실제 blocker 가 정확히 그 모양으로 통과했다(돌연변이로 실증됨). 그래서 전수로 뒤집는다.
    const slice = startSlice();
    const bare: string[] = [];
    for (const m of slice.matchAll(/invoke\("(\w+)"/g)) {
      if (!DAEMON_CMDS.includes(m[1])) continue;
      const before = slice.slice(Math.max(0, m.index! - 6), m.index!);
      if (before.endsWith("rpcT(")) continue; // 상한 통과
      const lineStart = slice.lastIndexOf("\n", m.index!) + 1;
      const line = slice.slice(lineStart, slice.indexOf("\n", m.index!)).trim();
      if (AUDITED_UNBOUNDED.some((a) => line.includes(a))) continue; // 감사된 예외
      bare.push(line);
    }
    // 여기서 실패했다면: 그 줄을 `rpcT(invoke(...), T_*)` 로 감싸거나, 다른 방식으로 유계임을
    // 증명하고 AUDITED_UNBOUNDED 에 이유와 함께 등재하라. 조용히 목록에 넣지 마라.
    expect(bare).toEqual([]);
  });

  it("전수 검사가 실제로 무언가를 세고 있다(핀 자체의 계측 타당성)", () => {
    const slice = startSlice();
    const all = [...slice.matchAll(/invoke\("(\w+)"/g)].filter((m) => DAEMON_CMDS.includes(m[1]));
    expect(all.length).toBeGreaterThanOrEqual(6); // 0건이면 위 핀은 공회전이다
  });

  it("상한 값은 명명 상수다(리터럴 흩뿌리기 금지 · Windows 배율이 한 곳에서 걸린다)", () => {
    for (const k of ["T_REG", "T_LIST", "T_STATUS", "T_LAUNCH", "T_NEW", "winScaled"]) {
      expect(src.includes(`const ${k}`)).toBe(true);
    }
  });
});

describe("복원 배선 — 무응답과 사망을 구분한다", () => {
  it("★daemon_status 타임아웃은 재기동 사유가 아니다(중복 launch 폭주 차단)", () => {
    // 살아 있는(느린·먹통인) 데몬에 rival launch 를 걸면 중복 데몬·좌석 탈취로 번진다.
    const slice = restoreSlice();
    expect(slice.includes("statusUnknown")).toBe(true);
    expect(slice.includes("if (statusUnknown) continue;")).toBe(true);
  });
});

describe("복원 배선 — 같은 소켓에 요청을 쌓지 않는다(폭주 축)", () => {
  // JS 상한은 **JS 쪽 포기**일 뿐 Rust/데몬 왕복을 취소하지 못한다. 상한만 두고 3초마다 같은
  // 소켓에 새 요청을 보내면 대기열이 자란다 — 가드의 전부는 '언제 푸느냐'다.
  it("★in-flight 해제는 원 호출이 실제로 끝났을 때다(rpcT 포기 시점 아님)", () => {
    // rpcT 가 포기하는 순간 풀면 다음 틱이 또 얹는다 = 가드가 있으나 마나.
    expect(src.includes("function releaseFlightWhenSettled(")).toBe(true);
    // 두 주기 폴러(3초 틱 list_surfaces · 10초 사이드바 org_status) 모두에 걸려 있어야 한다.
    expect((src.match(/releaseFlightWhenSettled\(/g) ?? []).length).toBeGreaterThanOrEqual(3);
    // 조기 해제(finally 에서 지우기)가 되살아나면 red.
    expect(code.includes("inFlight.delete(flightKey)")).toBe(false);
    expect(code.includes("inFlight.delete(sbKey)")).toBe(false);
  });

  it("★영구 skip 방지 — 끝나지 않는 호출도 재시도 상한이 있다(자가치유 전멸 차단)", () => {
    expect(src.includes("const INFLIGHT_RETRY_MS")).toBe(true);
    expect(src.includes("Date.now() - since < INFLIGHT_RETRY_MS")).toBe(true);
  });
});

describe("복원 배선 — 묘비는 결측이면 닫는다(fail-closed)", () => {
  it("★묘비 조회 실패(null)에 부서를 만들지 않는다 — 순수부에 그 조항이 있다", () => {
    const ws = readFileSync(new URL("./wsreconcile.ts", import.meta.url), "utf-8");
    expect(ws.includes("if (tombs === null) return out;")).toBe(true);
  });
  it("그룹 삭제도 teardown 전에 삭제 의도를 남긴다(부활 경로 차단)", () => {
    const a = src.indexOf("async function confirmDeleteGroup(");
    const b = src.indexOf("stop_dept_daemon_by_socket", a);
    expect(a).toBeGreaterThan(0);
    expect(src.slice(a, b).includes("dept_tombstone_by_socket")).toBe(true); // 묘비가 teardown 앞이다
  });
});

describe("복원 배선 — 승인 대기 배지는 단일 진실원에서 낸다", () => {
  it("★건너뛴 소켓이 배지 합계를 깎지 않는다(지역 누산기 금지)", () => {
    // in-flight 가드로 건너뛴 소켓을 0으로 세면, 고장 난 데몬이 하나도 없는 정상 동시 호출에서도
    // 승인 대기 ⚠ 배지가 사라진다 — CEO·마스터가 워커의 승인 대기를 화면에서 놓친다.
    expect(code.includes("pendingApprovals = [...pendingBySocket.values()].reduce(")).toBe(true);
    expect(code.includes("pendingApprovals = pend;")).toBe(false);
  });
});

describe("복원 배선 — 저장본을 읽기 전에는 저장하지 않는다", () => {
  it("★saveLayout 은 layoutLoaded 게이트를 먼저 통과한다(배치 영구 파괴 차단)", () => {
    // start() 가 저장본 로드 **전에** 죽고 복구 경로가 render()→saveLayout() 을 부르면,
    // 빈 workspaces 가 사용자의 모든 탭·그룹·분할을 단일 키에 덮어쓴다(백업 없음).
    const i = code.indexOf("function saveLayout()");
    expect(i).toBeGreaterThan(0);
    const head = code.slice(i, i + 200);
    expect(head.includes("if (!layoutLoaded) return;")).toBe(true);
    // 게이트를 여는 곳은 저장본을 읽은 직후 한 곳뿐이어야 한다.
    expect((code.match(/layoutLoaded = true/g) ?? []).length).toBe(1);
  });

  it("★기동 실패 복구는 `started = true` 를 render() 보다 먼저 세운다(자가치유가 그리기에 의존 금지)", () => {
    const i = code.indexOf("startup failed:");
    expect(i).toBeGreaterThan(0);
    const tail = code.slice(i, i + 900);
    expect(tail.indexOf("started = true")).toBeLessThan(tail.indexOf("render()"));
  });
});

describe("복원 배선 — 부팅 1회의 부서 데몬 팬아웃에 상한이 있다", () => {
  it("★등재만 된 부서까지 한꺼번에 띄우지 않는다(A① 폭주)", () => {
    // `cys-dept launch` 한 번은 CEO 승격·티켓·5역할 편성 기동까지 부수효과로 착수한다.
    expect(code.includes("MAX_DEPT_LAUNCH_PER_START")).toBe(true);
    // ★면제 판정은 '저장본에 있었나'가 아니라 '사용자가 실제로 쓰는 탭인가'여야 한다 —
    // 자동 생성된 탭도 곧바로 저장본에 기록되므로, 저장본 기준이면 상한이 1회짜리로 소멸한다.
    expect(code.includes("ws.autoCreated === true && launched >= MAX_DEPT_LAUNCH_PER_START")).toBe(true);
    expect(code.includes("savedSockets")).toBe(false);
  });
  it("★예산 검사가 가장 비싼 루프(부서 데몬 확보)에도 있다", () => {
    // daemon_status(최대 10s·Win 20s) + launch(최대 60s·Win 120s)가 부서마다 직렬이다.
    // 이 루프에 예산이 없으면 죽은 부서 여럿에서 분 단위로 화면이 비고 자가치유도 꺼진 채다.
    const slice = restoreSlice();
    const i = slice.indexOf("const deptWsList");
    expect(i).toBeGreaterThan(0);
    expect(slice.slice(i, i + 700).includes("Date.now() > restoreDeadline")).toBe(true);
  });
  it("복원 체인에 총량 데드라인이 있다(직렬 상한 합만큼 백지로 두지 않는다)", () => {
    expect(code.includes("const START_BUDGET")).toBe(true);
    expect((code.match(/Date\.now\(\) > restoreDeadline/g) ?? []).length).toBeGreaterThanOrEqual(2);
  });
  it("★pane 0개 워크스페이스는 백지가 아니라 안내+손잡이를 그린다(본부·부서 공통)", () => {
    // 팬아웃 상한·예산 소진·launch/셸 생성 실패·데몬 무응답이 전부 tree:null 로 떨어진다.
    expect(code.includes("function renderIdleWorkspace(")).toBe(true);
    expect(code.includes("root.appendChild(renderIdleWorkspace(ws))")).toBe(true);
  });
  it("미룬 사유를 하나로 뭉치지 않는다(제품의 조절 vs 이 기계가 느림)", () => {
    expect(code.includes("cappedLaunch")).toBe(true);
    expect(code.includes("budgetLaunch")).toBe(true);
  });
});

// ────────────────────────────────────────────────────────────────────────────
// (포크 A2-2 · 2026-09-18) 재구현 뮤테이션 검산이 찾은 빈 그물 3칸을 메운다.
//   · UM3: P5 「탭 0개일 때만 본부 탭 복구」를 「본부 탭이 없으면」으로 넓혀도 초록이었다.
//   · UM5: 팬아웃 상한 조건 앞에 `false &&` 를 붙여도 부분문자열 핀이 그대로 초록이었다
//          (긴 문자열이 핀 문자열을 품는다 — 조건 전체를 if 괄호째로 묻는다).
//   · 묘비 조회 실패(null) 때 이미 있는 부서 탭을 지우지 않는다(적대 r1 치명 ②의 UI 짝).
// ────────────────────────────────────────────────────────────────────────────
function refreshSlice(): string {
  const a = src.indexOf("async function refreshPaneTitles() {");
  const b = src.indexOf("const sockets = [...new Set(", a);
  expect(a).toBeGreaterThan(0);
  expect(b).toBeGreaterThan(a);
  return src.slice(a, b);
}

describe("복원 배선 — 재구현 뮤테이션 빈칸 봉합(A2-2)", () => {
  it("★3초 틱의 본부 탭 복구는 '탭이 하나도 없을 때'만이다(닫은 탭 무한 부활 금지)", () => {
    const s = refreshSlice();
    // 복구 블록(UNTITLED push)을 여는 조건이 정확히 이것이어야 한다.
    expect(/if \(workspaces\.length === 0\) \{\s*workspaces\.push\(\{ id: wsCounter\+\+, name: UNTITLED/.test(s)).toBe(true);
    // 넓힌 판(본부 소켓 부재 기준)이 들어오면 red.
    expect(s.includes("w.socket == null")).toBe(false);
    expect((s.match(/workspaces\.push\(/g) ?? []).length).toBe(1);
  });
  it("★팬아웃 상한 조건이 if 괄호째로 그대로다(앞에 무력화 항이 끼지 않는다)", () => {
    expect(code.includes("if (ws.autoCreated === true && launched >= MAX_DEPT_LAUNCH_PER_START) {")).toBe(true);
    const m = /const MAX_DEPT_LAUNCH_PER_START = (\d+);/.exec(code);
    expect(m).not.toBeNull();
    expect(Number(m![1])).toBeGreaterThan(0);
    expect(Number(m![1])).toBeLessThan(5);
  });
  it("★묘비 조회 실패(null)면 이미 있는 부서 탭은 지우지 않는다 — 드롭은 묘비를 실제로 읽었을 때만", () => {
    expect(restoreSlice().includes("if (deptTombs && dn && deptTombs.has(dn)) {")).toBe(true);
  });
});

describe("복원 배선 — 존재 진실원 보강은 실제 워크스페이스 목록을 넘긴다(A2-2)", () => {
  it("★missingKnownWorkspaces 의 첫 인자는 걸러지지 않은 workspaces 그대로다", () => {
    // 목록을 걸러 넘기면(예: 본부 제외) 본부 탭이 '없다'로 오판돼 매 기동 중복 생성되거나,
    // 반대로 걸러진 부서가 '있다'로 오판돼 영영 안 만들어진다.
    expect(/missingKnownWorkspaces\(\s*workspaces,\s*\[\.\.\.displayBySocket\]/.test(restoreSlice())).toBe(true);
  });
});

describe("복원 브리핑 카드 — 자동으로 아무것도 보내지 않는다(A2-2 T8)", () => {
  function cardSlice(): string {
    const a = src.indexOf("async function showRestoreBrief()");
    const b = src.indexOf("async function start() {", a);
    expect(a).toBeGreaterThan(0);
    expect(b).toBeGreaterThan(a);
    return src.slice(a, b);
  }
  // ★계약 개정(TICKET=v111-restore · 브리프 2026-09-21). 종전 두 단언은 「보내는 호출은
  //   [이어서] 클릭 처리기 안에 **1곳**」 · 「그 한 줄은 machineOrigin 표식을 단다」였다 —
  //   즉 **클릭 1회가 마스터에 글을 넣는 경로**를 정상으로 못박고, 그 위험을 표식으로 완화했다.
  //   09-21 실기에서 그 클릭이 임무 0 함대를 폭주시킨 방아쇠였고(자기발의 티켓으로 세 자리
  //   60%+), 박사님 최상위 원칙(「중간에 사용자에게 묻는 단계를 모두 삭제」)이 그 버튼 자체를
  //   지웠다. 완화(표식)에서 **제거(경로 0)** 로 올라간 것이므로 단언은 강해졌다.
  it("★마스터에 보내는 호출이 **0곳**이다(카드는 알림일 뿐 주입 경로가 없다)", () => {
    const s = cardSlice();
    expect((s.match(/invoke\("send_input"/g) ?? []).length).toBe(0);
    // 다른 이름의 주입 경로로 되살아나는 것도 막는다(send_text·send_key 계열 전부).
    expect(/invoke\("send_(input|text|key)"/.test(s)).toBe(false);
  });
  it("★[이어서 진행] 버튼 자체가 없다 — 사용자에게 묻지 않는다", () => {
    const s = cardSlice();
    expect(s.includes("continueLabel")).toBe(false);
    expect(s.includes("continueText")).toBe(false);
    expect(s.includes('go.addEventListener("click"')).toBe(false);
  });
  it("60%+ 순환 권유의 재료를 카드에 넘긴다(권유 1줄 · 자동 집행 0)", () => {
    const s = cardSlice();
    expect(s.includes("seatCtx:")).toBe(true);
    expect(s.includes("ctx_pct")).toBe(true);
    // 권유가 곧 집행이 되지 않게: 이 구간에 순환 집행 호출이 없어야 한다.
    expect(/invoke\("[^"]*cycle[^"]*"/i.test(s)).toBe(false);
  });
  // ★v115-restore(B5 · 핀 재조준): 종전 핀은 「started = true 직후 곧장 부른다」를 고정했다 — 그것이 곧 결함
  //   (복원·드레인 저장 전에 카드가 떠 「기록 못 찾음」)이었다. 이제 = started 직후엔 유예 타이머만 걸고,
  //   실제 호출은 maybeShowRestoreBrief(판정 briefTiming) 하나를 지난다.
  it("복원이 끝난 뒤 한 번 부른다(started 직후 즉시 호출 0 · 판정 경유)", () => {
    const i = src.indexOf("started = true; // 복원 완료");
    expect(i).toBeGreaterThan(0);
    const near = src.slice(i, i + 400);
    expect(near.includes("void showRestoreBrief();")).toBe(false);
    expect(near.includes("briefGate.graceElapsed = true;")).toBe(true);
    expect(src.match(/void showRestoreBrief\(\)/g)?.length).toBe(1);
    expect(src.includes('if (briefTiming(briefGate) === "show") void showRestoreBrief();')).toBe(true);
  });
  it("파일 내용은 textContent 로만 넣는다(마크업 해석 금지)", () => {
    expect(cardSlice().includes("innerHTML")).toBe(false);
  });
});

describe("복원 배선 — 묘비를 못 읽으면 저장본의 죽은 부서도 다시 켜지 않는다(A2-2 r2 · P1-A)", () => {
  it("★launch_dept_daemon 앞에 묘비 미상 보류가 있고, 살아 있는 부서 판정(alive) 뒤다", () => {
    const s = restoreSlice();
    const alive = s.indexOf("if (alive) continue;");
    const hold = s.indexOf("if (deptTombs === null) {\n      tombUnknownLaunch += 1;\n      continue;\n    }");
    const launch = s.indexOf('invoke("launch_dept_daemon"');
    expect(alive).toBeGreaterThan(0);
    expect(hold).toBeGreaterThan(alive); // 살아 있는 부서는 먼저 빠진다 = 탭 손실 0
    expect(launch).toBeGreaterThan(hold); // 재기동 호출보다 앞이다
  });
  it("보류 사유를 다른 미룸(상한·예산)과 섞지 않고 따로 알린다", () => {
    expect(code.includes("`부서 ${tombUnknownLaunch}곳은 이번에 켜지 않았습니다`")).toBe(true);
  });
});

// ────────────────────────────────────────────────────────────────────────────
// A1-3 M7 — 새 부서 탭 자동 열림의 배선 핀. 판정은 wsreconcile(순수·wsreconcile.test.ts)에,
// 여기서는 「그 판정이 실제 경로에 꽂혀 있다」만 잰다.
// ────────────────────────────────────────────────────────────────────────────
function newDeptHelperSlice(): string {
  const a = src.indexOf("async function openNewlyRegisteredDepts(): Promise<boolean> {");
  const b = src.indexOf("\n}\n", a);
  expect(a).toBeGreaterThan(0);
  expect(b).toBeGreaterThan(a);
  return src.slice(a, b);
}

describe("M7① — 켜져 있는 동안 생긴 부서는 3초 틱이 탭을 연다", () => {
  it("★3초 틱이 소켓 집계 **앞**에서 새 부서 탭 열기를 부른다(같은 틱에 입양까지)", () => {
    expect(refreshSlice().includes("if (await openNewlyRegisteredDepts()) layoutChanged = true;")).toBe(true);
  });
  it("열기 판정은 걸러지지 않은 workspaces 와 이번 세션의 seen 으로 한다 · 결과 seen 을 되저장한다", () => {
    const h = newDeptHelperSlice();
    expect(/newlyRegisteredDepts\(workspaces, depts, seen, tombs, deptNameFromSocket\)/.test(h)).toBe(true);
    expect(h.includes("deptSeen = step.seen;")).toBe(true);
    // 묘비는 소켓 요청 쌓임 방지 가드 아래에서만 읽는다(①폭주 축).
    expect(h.includes('claimFlight("tombs:")')).toBe(true);
    // 새 타이머 금지 — 틱에 편승한다.
    expect(/setInterval|setTimeout/.test(h)).toBe(false);
  });
  it("★묘비 in-flight 가드는 rpcT 래핑이 아니라 **생 invoke promise** 에 걸린다(원 호출이 끝날 때 해제)", () => {
    const h = newDeptHelperSlice();
    const m = /releaseFlightWhenSettled\("tombs:", (\w+)\);/.exec(h);
    expect(m).not.toBeNull();
    const v = m![1];
    // 가드에 넘긴 변수는 생 invoke 로 만들어진다 — rpcT(...) 로 만들어졌으면 적색.
    expect(new RegExp(`const ${v} = invoke\\("dept_tombstones"\\);`).test(h)).toBe(true);
    // 시간 상한은 그 생 promise 를 감싸 기다리는 쪽에만 있다.
    expect(new RegExp(`await rpcT\\(${v}, T_REG\\)`).test(h)).toBe(true);
  });
  it("틱이 만든 탭도 시작 대조와 같은 표식·그룹 재결속을 갖는다", () => {
    const h = newDeptHelperSlice();
    expect(h).toContain("ws.autoCreated = true");
    expect(h).toContain("ws.groupId = g.id");
    expect(h).toContain("workspaces.push(ws);");
  });
  it("★시작 대조가 본 레지스트리를 seen 으로 심는다 — 이게 없으면 닫힌 탭 판정 기준이 없다", () => {
    expect(restoreSlice().includes("if (registered !== null) deptSeen = new Set(displayBySocket.keys());")).toBe(true);
  });
});

describe("M7② V-12 — 앱이 꺼진 채 생긴 부서는 시작 대조가 탭을 만든다(기존 경로 재사용 · 중복 구현 없음)", () => {
  it("시작 대조(missingKnownWorkspaces)는 부서 데몬 확보 루프보다 앞이고 레지스트리 전체를 넘긴다", () => {
    const r = restoreSlice();
    const iMissing = r.indexOf("missingKnownWorkspaces(");
    const iLoop = r.indexOf("const deptWsList = workspaces.filter((w) => w.socket);");
    expect(iMissing).toBeGreaterThan(0);
    expect(iLoop).toBeGreaterThan(iMissing);
    expect(/missingKnownWorkspaces\(\s*workspaces,\s*\[\.\.\.displayBySocket\]/.test(r)).toBe(true);
    // 반복문이 그 결과를 **그대로** 순회한다 — 앞에 다른 식이 끼면(예: 빈 배열 ?? …) 호출은 남아도 탭은 안 생긴다.
    expect(r.includes("for (const spec of missingKnownWorkspaces(")).toBe(true);
    // 루프 **본문**이 만든 탭을 실제로 목록에 넣는다(적대 r1 중요② · M9: push 삭제 생존).
    expect(/for \(const spec of missingKnownWorkspaces\([\s\S]{0,1500}?workspaces\.push\(ws\);/.test(r)).toBe(true);
  });
});

// ─── v110-sidebar ⓒ — 부서 생성은 **단 하나의 문**을 지나고, 그 문에 확인 창이 서 있다 ─────────
//
// ★이 describe 가 곧 B22(2026-09-20 05:02)의 재현 축이다. 그날 ＋부서 한 번이 확인 창도 토스트도
//   없이 곧장 부서를 만들었고, 그 꼬리에서 본부 MASTER_DIRECTIVE.md 가 CEO 템플릿으로 교체됐다.
//   화면·DOM 없이 그 사고를 재현하는 방법은 **경로를 세는 것**이다: 생성 명령에 닿는 길이 몇 개이고,
//   그 길들이 전부 확인 창 뒤에 있는가. 길이 둘이 되는 순간(표지 없는 경로) 확인 창은 장식이 된다.
describe("ⓒ 부서 생성 확인 창 — 문이 하나이고 그 앞에 확인이 있다", () => {
  /**
   * launchDept 함수 본문만 잘라낸다 — 게이트 계약은 그 구간에만 적용된다.
   * ★반드시 `code`(주석 제거본)에서 뜬다(이종 검증 agy 1R ⑥ 지적 수용 · 2026-09-20).
   *   초판은 `src` 를 썼고, 그러면 **확인 창 줄을 주석 처리해도 정규식이 그대로 매칭돼** 초록이
   *   난다. 이 파일 머리가 이미 그 이유로 `code` 를 만들어 두었는데 새 케이스만 그것을 안 썼다 —
   *   「설명문이 핀을 깨뜨린다」의 정확한 재발이다.
   */
  function launchDeptSlice(): string {
    const a = code.indexOf("async function launchDept(");
    expect(a).toBeGreaterThan(0); // 함수가 사라졌으면 이 핀이 지키는 것이 없다
    const b = code.indexOf("\n}", a);
    expect(b).toBeGreaterThan(a);
    return code.slice(a, b);
  }

  it("★생성 명령(allocate_dept_daemon)을 부르는 자리가 정확히 하나다", () => {
    // 여러 자리에서 부르면 확인 창을 한 곳에 세워도 나머지가 그대로 뚫린다.
    expect((code.match(/invoke\("allocate_dept_daemon"/g) ?? []).length).toBe(1);
  });

  it("★addDeptWorkspace 의 호출자가 정확히 하나다 — 그 하나가 launchDept 여야 한다", () => {
    // 정의(`async function addDeptWorkspace(`)는 호출이 아니므로 뺀 뒤 센다.
    const calls = (code.match(/(?<!function )addDeptWorkspace\(/g) ?? []).length;
    expect(calls).toBe(1);
    expect(launchDeptSlice()).toContain("addDeptWorkspace(");
  });

  it("★확인 창이 생성 호출보다 앞에 있고, 취소면 **되돌아 나간다**", () => {
    const h = launchDeptSlice();
    const iConfirm = h.indexOf("deptCreateConfirm()");
    const iCall = h.indexOf("addDeptWorkspace(");
    expect(iConfirm).toBeGreaterThan(0);
    expect(iCall).toBeGreaterThan(iConfirm);
    // ★순서만 재면 안 된다 — 확인 창을 띄워 놓고 결과를 버려도 순서 단언은 통과한다.
    //   실제로 안전을 만드는 것은 **취소에서 나가는 return** 이므로 그 문장을 직접 못박는다.
    expect(
      /if \(!\(await confirmModal\(c\.title, c\.body, c\.yes, c\.no\)\)\) \{\s*deptLaunching = false;\s*return;\s*\}/.test(h),
    ).toBe(true);
    // 문안은 deptconfirm.ts 가 정본이다(화면 코드에 인라인 복제 금지 — 복제되면 세 축 검사가 헛돈다).
    expect(h.includes('"· 이 컴퓨터에')).toBe(false);
  });

  it("★확인 우회 값은 모듈 밖에서 만들 수 없는 심볼이고, 넘기는 자리는 레거시 폴백 하나뿐이다", () => {
    // ★구 판본은 `{ skipConfirm: true }` 객체 리터럴이었다(agy 1R ② 지적 수용). 등장 1회를 세는
    //   것은 「지금 코드에 하나뿐」을 재는 것이지 **「아무나 지어낼 수 없다」**를 재는 것이 아니다.
    //   심볼은 모듈 스코프 밖으로 안 나가므로 외부에서 같은 값을 만들 방법이 없다.
    expect(code).toContain('const DEPT_LEGACY_RETRY: unique symbol = Symbol("dept-legacy-retry");');
    expect(code).not.toContain("skipConfirm"); // 옛 우회 인자가 되살아나면 적색
    // 인자로 **넘기는** 자리 = 1곳(선언·시그니처의 등장은 빼고 센다).
    // ⚠선언(시그니처)의 등장은 호출이 아니다 — `function launchDept(` 를 빼고 센다.
    //   안 빼면 2가 나오고, 그 2를 기대값으로 적는 순간 진짜 우회 호출 1건이 추가돼도 초록이 된다.
    const passes = (code.match(/(?<!function )launchDept\([^)]*DEPT_LEGACY_RETRY\)/g) ?? []).length;
    expect(passes).toBe(1);
    expect(code).toContain("if (fallbackLegacy) await launchDept(undefined, DEPT_LEGACY_RETRY);");
  });

  it("★연타 락이 DOM 요소가 아니라 모듈 상태에 있다 — 버튼이 없어도 잠긴다(agy 1R ③)", () => {
    // 표지(버튼)에 매단 락은 그 표지가 사라지는 순간 락이 아니게 된다. 구 판본은 버튼이 null 이면
    // 조기 반환도 잠금도 건너뛰어 **동시 실행이 허용**됐다(fail-closed → fail-open 역전).
    const h = launchDeptSlice();
    expect(code).toContain("let deptLaunching = false;");
    expect(h).toContain("if (deptLaunching) return;");
    // 확인 창 **앞에서** 잠근다 — 뒤에 잠그면 연타로 확인 창이 겹쳐 쌓인다.
    const iLock = h.indexOf("deptLaunching = true;");
    const iConfirm = h.indexOf("confirmModal(");
    expect(iLock).toBeGreaterThan(0);
    expect(iConfirm).toBeGreaterThan(iLock);
    // 취소로 나가는 길·본 작업의 finally 둘 다 락을 푼다(안 풀면 문이 영구히 닫힌다).
    expect((h.match(/deptLaunching = false;/g) ?? []).length).toBe(2);
  });

  it("★팔레트 act:dept 도 같은 문으로 들어간다 — 단추 없이 같은 일을 하는 경로를 남기지 않는다", () => {
    const i = code.indexOf('id: "act:dept"');
    expect(i).toBeGreaterThan(0);
    const item = code.slice(i, i + 400);
    expect(item).toContain("launchDept(");
    expect(item).not.toContain("addDeptWorkspace(");
  });

  it("★확인 창에 Escape = 취소가 배선돼 있다 (854 권고 4 · 05:02 실사건에서 안 닫혔다)", () => {
    const a = code.indexOf("function confirmModal(");
    expect(a).toBeGreaterThan(0);
    const modal = code.slice(a, code.indexOf("\n}", a));
    expect(modal).toContain('e.key !== "Escape"');
    expect(modal).toContain("done(false)");
    // ★stopPropagation 이 아니라 stopImmediatePropagation 이어야 한다(agy 1R ④): 앞엣것은 같은
    //   window 에 붙은 **다른** 리스너를 못 막아, 확인 창이 겹쳐 있으면 Escape 한 번에 둘 다 닫힌다.
    expect(modal).toContain("e.stopImmediatePropagation();");
    // 리스너를 떼는 줄이 없으면 확인 창을 여닫을 때마다 전역 핸들러가 쌓인다.
    expect(modal).toContain('window.removeEventListener("keydown", onKey, true);');
  });

  it("★기본 포커스는 여전히 취소 쪽이다 — 무심코 친 Enter 가 승인이 되면 확인 창의 뜻이 사라진다", () => {
    const a = code.indexOf("function confirmModal(");
    const modal = code.slice(a, code.indexOf("\n}", a));
    expect(modal).toContain('(ov.querySelector(".modal-no") as HTMLElement).focus();');
  });
});

// ─── v110-sidebar ⓑ′ — 전문가 모드 배선 ────────────────────────────────────────────────
describe("ⓑ′ 전문가 모드 — 기본 꺼짐 판정이 순수 모듈을 지난다", () => {
  it("★기본값 판정이 expertModeOn 을 쓴다 — main.ts 안에서 저장값을 직접 비교하지 않는다", () => {
    expect(code).toContain("applyExpertMode(expertModeOn(localStorage.getItem(EXPERT_KEY)))");
    // 인라인 복제가 생기면 기본값이 두 곳에 흩어지고 한쪽만 뒤집혀도 시험이 조용하다.
    expect(/localStorage\.getItem\(EXPERT_KEY\)\s*===/.test(code)).toBe(false);
  });

  it("저장도 같은 모듈의 표기를 쓴다(왕복 성립)", () => {
    expect(code).toContain("localStorage.setItem(EXPERT_KEY, expertModeRaw(on));");
  });

  it("★토글이 실제로 칸을 여닫는다 — 저장만 하고 화면을 안 고치면 다음 실행까지 안 바뀐다", () => {
    const a = code.indexOf("function applyExpertMode(");
    expect(a).toBeGreaterThan(0);
    const fn = code.slice(a, code.indexOf("\n}", a));
    expect(fn).toContain("expertBox.hidden = !on");
    expect(fn).toContain("expertToggle.checked = on");
  });
});

// ────────────────────────────────────────────────────────────────────────────
// TICKET=v111-restore ③ — 빈 자리표 회수 배선(master 판정 B · 조건 ⓐⓑⓒ)
// 판정 자체는 placeholderclose.test.ts 가 쥔다. 여기서는 **배선**만 못박는다 —
// 판정이 옳아도 배선이 어긋나면(남의 번호를 넣는다·손댐 표시를 안 한다) 그대로 사고다.
// ────────────────────────────────────────────────────────────────────────────
describe("빈 자리표 회수 — 배선", () => {
  it("ⓐ 회수 대상 번호는 **UI 가 만든 충전 셸**에서만 장부에 들어간다", () => {
    // 장부에 넣는 지점이 1곳이고, 그 지점이 newSurface 직후여야 한다.
    expect((src.match(/placeholderSids\.add\(/g) ?? []).length).toBe(1);
    expect(/const sid = await newSurface\(null, ws\.socket, T_NEW\);[\s\S]{0,200}?placeholderSids\.add\(sid\)/.test(src)).toBe(true);
  });
  it("★ⓐ 회수 루프는 장부에 없는 번호를 **먼저** 걸러낸다(남의 페인 불가침)", () => {
    expect(src.includes("if (!placeholderSids.has(sid)) continue;")).toBe(true);
  });
  it("ⓑ pane 입력 단일 경로(sendRaw)가 손댐을 표시한다", () => {
    expect(/const sendRaw = \(data: string\) => \{[\s\S]{0,300}?notePlaceholderTouched\(sid\)/.test(src)).toBe(true);
    // 표시 함수는 장부에 있는 번호만 손댐으로 올린다(남의 번호가 장부에 들어오지 않게).
    expect(src.includes("if (placeholderSids.has(sid)) touchedPlaceholders.add(sid);")).toBe(true);
  });
  it("★판정은 placeholderclose 가 단독으로 쥔다 — 조건을 배선부에 두 벌로 쓰지 않는다", () => {
    expect(src.includes('import { shouldClosePlaceholder } from "./placeholderclose";')).toBe(true);
    expect((src.match(/shouldClosePlaceholder\(/g) ?? []).length).toBe(1);
  });
  it("ⓒ 손댄 자리는 닫지 않고 알림도 없다 — 회수 구간에 토스트가 없다", () => {
    const a = src.indexOf("// ── ③ 빈 자리표 회수");
    const b = src.indexOf("const masterSids = new Set(", a);
    expect(a).toBeGreaterThan(0);
    expect(b).toBeGreaterThan(a);
    const slice = src.slice(a, b);
    expect(/toast\(/.test(slice)).toBe(false);
    expect(/osBanner\(/.test(slice)).toBe(false);
    // 그리고 한 번 판정한 번호는 장부에서 빠져 반복 시도가 없다.
    expect(slice.includes("placeholderSids.delete(sid);")).toBe(true);
  });
});
