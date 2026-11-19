// 미룬 좌석 런타임 장부 시험 — TICKET=cysr-1116-s2-1119 · P2-DESIGN §2-3 ㉢ · 1회 고침 F20.
//   main.ts 의 실제 함수 본문(ensureSeatRuntime · seatAttached · seatInModel · destroyPaneRuntime · deferSeatRuntime · collectSids)을 떼어
//   `with (scope)` 안에서 돌린다(roleactivity.test.ts 와 같은 로더).
//   ① 만드는 동안에도 「붙은 좌석」(3초 틱이 다시 입양할 틈 0) · 같은 좌석 두 번째 호출 = 생성 0
//   ② 기다린 사이 떼이면(destroyPaneRuntime) 방금 만든 런타임만 파기 · 장부 0
//   ③ makePane 실패 = 등록된 런타임 파기 · 장부 유지 · 자동 재시도 3회 상한 · 작업 화면 재진입 때 다시 · 기다린 사이 떼였으면 다시 넣지 않음
//   ④ 아직 모형에 없는 좌석 = 만들지 않고 장부 유지 · 삭제 중 탭 좌석 = 만들지 않음
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";

declare const Bun: { Transpiler: new (o: { loader: "ts" }) => { transformSync(code: string): string } }; // roleactivity.test.ts 와 같은 앰비언트 선언(bun-env.d.ts 범위 밖)
const SRC = readFileSync(new URL("../main.ts", import.meta.url), "utf8");
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyFn = (...a: any[]) => any;
function fnText(name: string): string {
  const m = new RegExp(`^(?:async )?function ${name}\\(`, "m").exec(SRC);
  expect({ 함수: name, 존재: m !== null }).toEqual({ 함수: name, 존재: true });
  const a = (m as RegExpExecArray).index;
  return SRC.slice(a, SRC.indexOf("\n}\n", a) + 2);
}
const NAMES = ["collectSids", "seatAttached", "seatInModel", "deferSeatRuntime", "ensureSeatRuntime", "destroyPaneRuntime", "retryFailedRuntimes", "writeSeatHistory", "ensureSeatRuntimes"];

function harness(opts: { fail?: number; history?: string } = {}) {
  const paneKey = (sid: number, socket?: string): string => `${socket ?? ""}#${sid}`;
  const panes = new Map<string, { sid: number; disposed: boolean; observer: { disconnect(): void }; unlisten: (() => void)[]; term: { dispose(): void }; el: { remove(): void } }>();
  const workspaces: Record<string, unknown>[] = [
    { id: 1, socket: undefined, tree: { type: "pane", sid: 5 } },
    { id: 2, socket: undefined, tree: null },
  ];
  let release: (() => void) | null = null;
  let fails = opts.fail ?? 0;
  const made: number[] = [];
  const disposed: number[] = [];
  const roleDots: [number, string][] = [];
  const streams: number[] = [];
  const writes: string[] = [];
  const invokes: [string, Record<string, unknown>][] = [];
  const view = { work: true };
  const focusCalls: number[] = [];
  const deps: Record<string, unknown> = {
    PANE_STREAM_UNWANTED: "pane_stream_unwanted", DEFERRED_TOTAL_MAX: 9, SEAT_HISTORY_MAX: 5000, T_LIST: 8000,
    workRuntimeWanted: () => view.work,
    ensuringRuntimes: false, focusedSid: null as number | null, renders: 0,
    current: () => workspaces[0],
    wsViewTree: (w: { tree: unknown; view?: unknown }) => w.view ?? w.tree, // 묶음 탭·확대 = 보기 트리(시험이 view 로 준다)
    render: () => void (scope.renders = (scope.renders as number) + 1),
    setFocus: (sid: number) => {
      focusCalls.push(sid);
      scope.focusedSid = sid;
    },
    rpcT: (p: Promise<unknown>) => p,
    invoke: async (cmd: string, a: Record<string, unknown>) => {
      invokes.push([cmd, a]);
      if (cmd === "seat_history") return { text: opts.history ?? "" };
      return null;
    },
    paneKey, panes, workspaces, exitedPaneKeys: new Set<string>(), deferredRuntimes: new Map<string, unknown>(),
    setRoleDot: (rt: { sid: number }, role: string) => void roleDots.push([rt.sid, role]),
    makePane: async (sid: number, _t: string, socket?: string, o?: { beforeStream?: (term: unknown) => Promise<boolean> }) => {
      made.push(sid);
      await new Promise<void>((r) => (release = r));
      // 실제 makePane 처럼: 듣기 등록 뒤 · 스트림 시작 직전에 beforeStream — false 면 스스로 치우고 던진다
      if (o?.beforeStream && !(await o.beforeStream({ rows: 4, write: (x: string) => void writes.push(x) }))) throw new Error("pane_stream_unwanted");
      streams.push(sid);
      // 실제 makePane 처럼 끝에서 등록(panes.set) — 실패는 등록 전(attach_surface 거부 꼴)
      if (fails > 0) {
        fails--;
        throw new Error("attach_surface rejected");
      }
      const rt = { sid, disposed: false, observer: { disconnect() {} }, unlisten: [], term: { dispose: () => void disposed.push(sid) }, el: { remove() {} } };
      panes.set(paneKey(sid, socket), rt);
      return rt;
    },
  };
  const tr = new Bun.Transpiler({ loader: "ts" });
  const code = NAMES.map((n) => tr.transformSync(fnText(n))).join("\n");
  const scope: Record<string, unknown> = Object.assign(Object.create(null), deps);
  const fns = new Function("__scope", `with (__scope) {\n${code}\nreturn { ${NAMES.join(", ")} };\n}`)(scope) as Record<string, AnyFn>;
  const ledger = scope.deferredRuntimes as Map<string, unknown>;
  const go = () => release?.();
  const tick = async () => {
    for (let i = 0; i < 5; i++) await Promise.resolve();
  };
  return { fns, panes, workspaces, made, disposed, roleDots, ledger, go, tick, streams, writes, invokes, view, focusCalls, scope };
}

describe("(codex 2R) 붙기 직전 재판정 · 실행 전체 상한 · 붙기 전 기록", () => {
  it("② makePane 을 기다리는 사이 대화 화면으로 → 기록 조회 0 · 스트림 0 · 런타임 0 · 장부 유지 · 횟수 안 셈 → 다음 진입에 붙음", async () => {
    const h = harness({ history: "a\nb" });
    h.fns.deferSeatRuntime(5, undefined, "t", null, 10);
    const p = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    h.view.work = false; // 대화 화면으로 돌아감
    h.go();
    expect(await p).toBe(false);
    expect(h.streams).toEqual([]);
    expect(h.invokes).toEqual([]); // 대화 화면이면 기록도 묻지 않는다
    expect(h.panes.has("#5")).toBe(false);
    expect(h.ledger.size).toBe(1);
    expect(h.fns.seatAttached(5, undefined)).toBe(true);
    h.view.work = true;
    const q = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    h.go();
    expect(await q).toBe(true);
    expect(h.streams).toEqual([5]);
  });
  it("③ 재진입마다 3회 묶음은 되돌리지만 실행 전체 상한 9회 — 10번째 시도 0", async () => {
    const h = harness({ fail: 100 });
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    for (let round = 0; round < 5; round++) {
      for (let i = 0; i < 3; i++) {
        const p = h.fns.ensureSeatRuntime("#5");
        await h.tick();
        h.go();
        await p;
      }
      h.fns.retryFailedRuntimes(); // 작업 화면 재진입
    }
    expect(h.made.length).toBe(9);
    expect(h.ledger.size).toBe(1); // 좌석은 붙은 채(재입양 0) · 「(없음)」 칸 = 더 시도하지 않음
  });
  it("① 기록: 미룬 그때 커서 − 화면 행 수부터 받아, 지금 화면에 다시 그려질 마지막 행 수만큼 빼고 쓴 뒤 행 수만큼 밀어 올린다 · 제어 문자 제거", async () => {
    const lines = Array.from({ length: 10 }, (_, i) => `줄${i}`);
    lines[2] = "색\x1b[31m빨강";
    const h = harness({ history: lines.join("\n") });
    h.fns.deferSeatRuntime(5, undefined, "t", null, 100);
    const p = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    h.go();
    expect(await p).toBe(true);
    expect(h.invokes).toEqual([["seat_history", { socket: undefined, surfaceId: 5, sinceLine: 96, maxLines: 10000 }]]);
    expect(h.writes).toEqual(["줄0\r\n줄1\r\n색[31m빨강\r\n줄3\r\n줄4\r\n줄5" + "\r\n".repeat(4)]);
    expect(h.streams).toEqual([5]); // 기록을 쓴 **뒤** 스트림
  });
  it("① 커서 모름(null) = 기록 조회 0 · 기록 조회 실패 = 기록 없이 붙음", async () => {
    const h = harness();
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    const p = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    h.go();
    expect(await p).toBe(true);
    expect(h.invokes).toEqual([]);
    expect(h.writes).toEqual([]);
  });
});

describe("(독립 검증 F1 · codex 2R minor) 첫 진입 포커스", () => {
  const pump = async (h: ReturnType<typeof harness>) => {
    const p = h.fns.ensureSeatRuntimes(0);
    for (let i = 0; i < 5; i++) {
      await h.tick();
      h.go();
    }
    await p;
  };
  it("F1: 시작 복원이 런타임 없던 좌석에 포커스 번호만 잡아 둔 경우 — 그 좌석 런타임을 만든 뒤 다시 setFocus", async () => {
    const h = harness();
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    h.scope.focusedSid = 5; // start() 끝 setFocus(first) 가 남긴 번호(그때는 런타임 없음 → 표시·키보드 포커스 0)
    await pump(h);
    expect(h.panes.has("#5")).toBe(true);
    expect(h.focusCalls).toEqual([5]);
    expect(h.scope.renders).toBe(1);
  });
  it("포커스 없음 + 묶음 탭으로 숨은 좌석이 트리 첫째 → 보이는 보기 트리 첫 좌석", async () => {
    const h = harness();
    (h.workspaces[0] as { tree: unknown; view?: unknown }).tree = { type: "split", dir: "row", ratio: 0.5, a: { type: "pane", sid: 6 }, b: { type: "pane", sid: 5 } };
    (h.workspaces[0] as { view?: unknown }).view = { type: "pane", sid: 5 };
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    await pump(h);
    expect(h.focusCalls).toEqual([5]);
  });
  it("이미 런타임 있던 좌석에 포커스가 있으면 건드리지 않는다(탈취 0)", async () => {
    const h = harness();
    (h.workspaces[0] as { tree: unknown }).tree = { type: "split", dir: "row", ratio: 0.5, a: { type: "pane", sid: 4 }, b: { type: "pane", sid: 5 } };
    h.panes.set("#4", { sid: 4, disposed: false, observer: { disconnect() {} }, unlisten: [], term: { dispose() {} }, el: { remove() {} } });
    h.scope.focusedSid = 4;
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    await pump(h);
    expect(h.focusCalls).toEqual([]);
  });
});

describe("미룬 런타임 장부(ensureSeatRuntime)", () => {
  it("① 만드는 동안에도 붙은 좌석 · 두 번째 호출 = 생성 0 · 끝나면 장부 비고 런타임 1 · 역할 점", async () => {
    const h = harness();
    h.fns.deferSeatRuntime(5, undefined, "t", "worker-1");
    const p = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    expect(h.fns.seatAttached(5, undefined)).toBe(true); // 3초 틱의 known = 붙음 → 입양 후보 아님
    expect(await h.fns.ensureSeatRuntime("#5")).toBe(false);
    expect(h.made).toEqual([5]);
    h.go();
    expect(await p).toBe(true);
    expect(h.ledger.size).toBe(0);
    expect(h.panes.has("#5")).toBe(true);
    expect(h.roleDots).toEqual([[5, "worker-1"]]);
  });
  it("② 기다린 사이 떼임 → 방금 만든 런타임만 파기 · 장부 0", async () => {
    const h = harness();
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    const p = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    (h.workspaces[0] as { tree: unknown }).tree = null; // detachPane 이 트리에서 뗌
    h.fns.destroyPaneRuntime(5, undefined); //            … 그리고 장부를 비움
    h.go();
    expect(await p).toBe(false);
    expect(h.panes.has("#5")).toBe(false);
    expect(h.disposed).toEqual([5]);
    expect(h.ledger.size).toBe(0);
  });
  it("③ 실패 = 장부 유지(재입양 0) · 3회 뒤 자동 재시도 0 · 작업 화면 재진입(retryFailedRuntimes) = 한 벌 더 (codex 1R major)", async () => {
    const h = harness({ fail: 5 });
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    for (let i = 0; i < 3; i++) {
      const p = h.fns.ensureSeatRuntime("#5");
      await h.tick();
      h.go();
      expect(await p).toBe(false);
      expect({ i, left: h.ledger.size, attached: h.fns.seatAttached(5, undefined) }).toEqual({ i, left: 1, attached: true });
    }
    expect(await h.fns.ensureSeatRuntime("#5")).toBe(false); // 상한 — 생성 시도 0
    expect(h.made).toEqual([5, 5, 5]);
    h.fns.retryFailedRuntimes();
    const p = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    h.go();
    expect(await p).toBe(false); // 대역은 5번 실패하게 — 넷째 시도가 실제로 났는지만 본다
    expect(h.made).toEqual([5, 5, 5, 5]);
  });
  it("③-b 실패를 기다린 사이 떼였으면 다시 넣지 않는다", async () => {
    const h = harness({ fail: 1 });
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    const p = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    h.fns.destroyPaneRuntime(5, undefined);
    h.go();
    expect(await p).toBe(false);
    expect(h.ledger.size).toBe(0);
  });
  it("④ 모형에 없는 좌석 = 만들지 않고 장부 유지 · 삭제 중 탭 = 만들지 않음 · 런타임 있으면 장부만 비움", async () => {
    const h = harness();
    h.fns.deferSeatRuntime(9, undefined, "t", null);
    expect(await h.fns.ensureSeatRuntime("#9")).toBe(false);
    expect(h.made).toEqual([]);
    expect(h.ledger.has("#9")).toBe(true);
    (h.workspaces[0] as { deleting?: boolean }).deleting = true;
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    expect(await h.fns.ensureSeatRuntime("#5")).toBe(false);
    expect(h.made).toEqual([]);
    h.panes.set("#9", { sid: 9, disposed: false, observer: { disconnect() {} }, unlisten: [], term: { dispose() {} }, el: { remove() {} } });
    expect(await h.fns.ensureSeatRuntime("#9")).toBe(false);
    expect(h.ledger.has("#9")).toBe(false);
  });
});
