// 실제 makePane 본문 행동 시험 — TICKET=cysr-1116-s2-1119 · codex 3R(master#cca94b88 · master#edc48c75).
//   main.ts 의 makePane 함수 본문을 그대로 떼어 `with (scope)` 안에서 돌린다. scope 는 시험이 쥔 이름(invoke·listen·document·Terminal·
//   ResizeObserver·panes·paneGen …) 말고는 **무엇이든 대역**(부르면 대역 · 읽으면 대역 · await 하면 그대로)을 돌려주는 Proxy 라,
//   makePane 이 부르는 수십 개 보조 함수를 손으로 나열하지 않는다(나열 목록이 낡아 시험이 거짓 초록이 되는 꼴을 막는다).
//   ① 정리 보장 = 첫 줄부터 — term.open 직후·ResizeObserver(스트림 시작 뒤) 어디서 던져도 xterm·DOM·듣기·타이머·스트림을 되돌린다
//   ② 세대 — 기다린 사이 파기(destroyPaneRuntime = bumpPaneGen) → 같은 좌석 새 시도가 등록 → 옛 시도가 늦게 끝나도 새 런타임을 덮지 않고
//      새 스트림도 멈추지 않으며 제 것만 치운다
//   ③ 붙은 뒤 재판정(afterStream false) = stop_surface_stream + 치움 · 기록 이어 붙이기 인자가 start_surface_stream 에 실린다
//   ④ 인자 없는 makePane(작업 화면 입양) = start_surface_stream 인자 = 종전 그대로 { socket, surfaceId }
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";

declare const Bun: { Transpiler: new (o: { loader: "ts" }) => { transformSync(code: string): string } };
const SRC = readFileSync(new URL("../main.ts", import.meta.url), "utf8");
function fnText(name: string): string {
  const m = new RegExp(`^(?:async )?function ${name}\\(`, "m").exec(SRC);
  expect({ 함수: name, 존재: m !== null }).toEqual({ 함수: name, 존재: true });
  const a = (m as RegExpExecArray).index;
  return SRC.slice(a, SRC.indexOf("\n}\n", a) + 2);
}

/** 무엇이든 받아 주는 대역 — 부름·new·속성 읽기 = 대역 · then 없음(await 통과) · 수 변환 = 0 · 반복 = 빈 것. */
const STUB: unknown = new Proxy(function () {}, {
  get(_t, p) {
    if (p === "then") return undefined;
    if (p === Symbol.toPrimitive) return () => 0;
    if (p === Symbol.iterator) return function* () {};
    return STUB;
  },
  apply: () => STUB,
  construct: () => STUB as object,
  set: () => true,
});

type Log = string[];
/** 되돌림을 적는 가짜 객체 — 정한 메서드만 기록 · 나머지 속성 = 대역(쓰기는 보관). */
function rec(name: string, log: Log, methods: string[], init: Record<string, unknown> = {}): Record<string, unknown> {
  const t: Record<string | symbol, unknown> = { ...init };
  for (const m of methods) t[m] = (..._a: unknown[]) => void log.push(`${name}.${m}`);
  return new Proxy(t, {
    get(o, p) {
      if (p === "then") return undefined;
      if (p in o) return o[p];
      return STUB;
    },
    set(o, p, v) {
      o[p] = v;
      return true;
    },
  }) as Record<string, unknown>;
}

interface Gate {
  wait: Promise<void>;
  open: () => void;
}
function gate(): Gate {
  let open = () => {};
  const wait = new Promise<void>((r) => (open = r));
  return { wait, open };
}

function harness(o: { throwAt?: string; hold?: Record<string, Gate> } = {}) {
  const log: Log = [];
  const invokes: [string, Record<string, unknown>][] = [];
  const panes = new Map<string, unknown>();
  const paneGen = new Map<string, number>();
  let elN = 0;
  let termN = 0;
  const document = {
    createElement: (tag: string) => {
      const n = tag === "div" ? `div${++elN}` : tag;
      return rec(n, log, ["remove"], { __name: n, dataset: {}, style: {}, querySelector: () => null });
    },
  };
  const scope: Record<string, unknown> = {
    PANE_STREAM_UNWANTED: "pane_stream_unwanted",
    PANE_STALE: "pane_stale",
    panes,
    paneGen,
    paneKey: (sid: number, socket?: string) => `${socket ?? ""}#${sid}`,
    document,
    Terminal: function () {
      const id = `term${++termN}`;
      return rec(id, log, ["dispose", "open", "write", "loadAddon"], { __name: id, rows: 35, cols: 120, textarea: null });
    },
    snapCellsToDevicePixels: () => {
      if (o.throwAt === "open") throw new Error("boom-open");
    },
    ResizeObserver: function () {
      if (o.throwAt === "observer") throw new Error("boom-observer");
      return rec("observer", log, ["disconnect", "observe"]);
    },
    window: rec("window", log, [], { setTimeout: () => 1 }),
    listen: async (name: string) => {
      log.push(`listen:${name}`);
      return () => void log.push(`unlisten:${name}`);
    },
    invoke: async (cmd: string, a: Record<string, unknown>) => {
      invokes.push([cmd, a]);
      const g = o.hold?.[cmd];
      if (g) {
        delete o.hold![cmd]; // 첫 호출만 붙잡는다(뒤 시도는 그냥 지나간다)
        await g.wait;
      }
      if (cmd === "attach_surface") return { output_event: `out-${a.surfaceId}`, exited_event: `exit-${a.surfaceId}` };
      if (cmd === "start_surface_stream") return a.historySince !== undefined ? { stream_gen: 42, history: { status: "ok", rows: 3 } } : { stream_gen: 41 };
      return null;
    },
  };
  const tr = new Bun.Transpiler({ loader: "ts" });
  const code = tr.transformSync(fnText("makePane"));
  const real = new Set(Object.keys(scope));
  const env = new Proxy(scope, {
    has: (_t, p) => typeof p === "string" && (real.has(p) || !(p in globalThis)),
    get: (t, p) => (typeof p === "string" && real.has(p) ? t[p] : p === Symbol.unscopables ? undefined : STUB),
    set: (t, p, v) => {
      t[p as string] = v;
      return true;
    },
  });
  const makePane = new Function("__scope", `with (__scope) {\n${code}\nreturn makePane;\n}`)(env) as (
    sid: number,
    title: string,
    socket?: string,
    opts?: unknown,
  ) => Promise<unknown>;
  const bump = (key: string) => paneGen.set(key, (paneGen.get(key) ?? 0) + 1);
  return { makePane, log, invokes, panes, bump };
}

/** 던진 글(없으면 null) — bun-env 타입에 rejects 가 없어 손으로 받는다. */
const errOf = async (p: Promise<unknown>): Promise<string | null> => {
  try {
    await p;
    return null;
  } catch (e) {
    return e instanceof Error ? e.message : String(e);
  }
};
const tick = async () => {
  for (let i = 0; i < 20; i++) await Promise.resolve();
};

describe("실제 makePane — 정리 보장(첫 줄부터) · 세대 · 붙은 뒤 재판정 (codex 3R)", () => {
  it("④ 대조군: 인자 없음 = 등록 1 · start 인자 종전 그대로 · 되돌림 0", async () => {
    const h = harness();
    const rt = await h.makePane(5, "t");
    expect(h.panes.get("#5")).toBe(rt);
    expect(h.invokes.find((x) => x[0] === "start_surface_stream")).toEqual(["start_surface_stream", { socket: undefined, surfaceId: 5 }]);
    expect(h.log.filter((x) => /remove|dispose|unlisten|disconnect/.test(x))).toEqual([]);
    expect(h.invokes.some((x) => x[0] === "stop_surface_stream")).toBe(false);
  });

  it("① term.open 직후(첫 attach 전) 던짐 → xterm·DOM 되돌림 · 등록 0 · attach 0", async () => {
    const h = harness({ throwAt: "open" });
    expect(await errOf(h.makePane(5, "t"))).toBe("boom-open");
    expect(h.panes.size).toBe(0);
    expect(h.log).toContain("term1.dispose");
    expect(h.log).toContain("div1.remove");
    expect(h.invokes.some((x) => x[0] === "attach_surface")).toBe(false);
  });

  it("① 스트림 시작 **뒤** ResizeObserver 에서 던짐 → 스트림 정지 · 듣기 2 해제 · xterm·DOM 되돌림 · 등록 0", async () => {
    const h = harness({ throwAt: "observer" });
    expect(await errOf(h.makePane(5, "t"))).toBe("boom-observer");
    expect(h.panes.size).toBe(0);
    expect(h.invokes.find((x) => x[0] === "stop_surface_stream")).toEqual(["stop_surface_stream", { socket: undefined, surfaceId: 5, streamGen: 41 }]);
    for (const k of ["unlisten:out-5", "unlisten:exit-5", "term1.dispose", "div1.remove"]) expect(h.log).toContain(k);
    // 거꾸로 — 스트림 정지가 듣기 해제보다 먼저(되돌림 목록 역순)
    const order = h.invokes.findIndex((x) => x[0] === "stop_surface_stream");
    expect(order).toBeGreaterThan(h.invokes.findIndex((x) => x[0] === "start_surface_stream"));
    expect(h.log.indexOf("unlisten:exit-5")).toBeLessThan(h.log.indexOf("term1.dispose"));
  });

  it("③ 붙은 뒤 재판정 false(대화 화면으로 돌아감) → stop_surface_stream · 치움 · 표지 pane_stream_unwanted · 기록 인자 실림", async () => {
    const h = harness();
    const seen: unknown[] = [];
    expect(
      await errOf(
        h.makePane(5, "t", undefined, {
        beforeStream: async () => ({ historySince: 77, historyRows: 35 }),
        afterStream: (_p: unknown, started: unknown) => {
          seen.push(started);
          return false;
        },
        }),
      ),
    ).toBe("pane_stream_unwanted");
    expect(h.invokes.find((x) => x[0] === "start_surface_stream")).toEqual(["start_surface_stream", { socket: undefined, surfaceId: 5, historySince: 77, historyRows: 35 }]);
    expect(seen).toEqual([{ stream_gen: 42, history: { status: "ok", rows: 3 } }]);
    // (codex 4R major) stop 은 자기 세대만 — 이 호출의 stream_gen 을 싣는다(옛 시도가 새 스트림을 멈추지 못하게)
    expect(h.invokes.find((x) => x[0] === "stop_surface_stream")).toEqual(["stop_surface_stream", { socket: undefined, surfaceId: 5, streamGen: 42 }]);
    expect(h.panes.size).toBe(0);
    expect(h.log).toContain("term1.dispose");
  });

  it("② 파괴 → 같은 좌석 재입양 → 옛 시도 늦게 끝남: 새 런타임 그대로 · 새 스트림 정지 0 · 옛 것만 치움", async () => {
    for (const holdAt of ["attach_surface", "start_surface_stream"]) {
      const g = gate();
      const h = harness({ hold: { [holdAt]: g } });
      const old = h.makePane(5, "t"); // 옛 시도 — holdAt 첫 호출에서 멈춤
      await tick();
      h.bump("#5"); // destroyPaneRuntime(5) — 세대 올림
      const fresh = await h.makePane(5, "t"); // 재입양 = 새 시도(막힘 없음) → 등록
      expect(h.panes.get("#5")).toBe(fresh);
      g.open(); // 옛 시도가 늦게 끝남
      expect(await errOf(old)).toBe("pane_stale");
      expect({ holdAt, same: h.panes.get("#5") === fresh, size: h.panes.size }).toEqual({ holdAt, same: true, size: 1 });
      expect(h.invokes.filter((x) => x[0] === "stop_surface_stream")).toEqual([]); // 새 시도의 스트림을 멈추지 않는다
      const f = fresh as { el: { __name: string }; term: { __name: string } };
      expect(h.log).toContain("term1.dispose"); // 옛 시도 = term1 · 제 것만
      expect(f.term.__name).toBe("term2");
      expect(h.log).not.toContain(`${f.term.__name}.dispose`); // 새 런타임 xterm 무사
      expect(h.log).not.toContain(`${f.el.__name}.remove`); // 새 런타임 DOM 무사
      expect(h.log).toContain("div1.remove"); // 옛 시도의 pane 뿌리 DOM 은 치움
    }
  });
});
