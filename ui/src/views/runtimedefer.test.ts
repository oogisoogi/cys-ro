// 미룬 좌석 런타임 장부 시험 — TICKET=cysr-1116-s2-1119 · P2-DESIGN §2-3 ㉢ · 1회 고침 F20.
//   main.ts 의 실제 함수 본문(ensureSeatRuntime · seatAttached · seatInModel · destroyPaneRuntime · deferSeatRuntime · 기록 이어 붙이기 보조 · collectSids)을 떼어
//   `with (scope)` 안에서 돌린다(roleactivity.test.ts 와 같은 로더). makePane 은 계약 대역 — 실제 본문은 makepane.test.ts 가 지킨다.
//   ① 만드는 동안에도 「붙은 좌석」(3초 틱이 다시 입양할 틈 0) · 같은 좌석 두 번째 호출 = 생성 0
//   ② 기다린 사이 떼이면(destroyPaneRuntime = 세대 올림) 붙지 않음 · 장부 0 · 파기 → 재입양 → 옛 시도 늦게 끝나도 새 런타임·장부 무사(codex 3R)
//   ③ makePane 실패 = 장부 유지 · 자동 재시도 = 작업 화면 진입당 3회 · 진입마다 되돌림(영구 차단 0 · codex 3R) · 기다린 사이 떼였으면 다시 넣지 않음
//   ④ 아직 모형에 없는 좌석 = 만들지 않고 장부 유지 · 삭제 중 탭 좌석 = 만들지 않음
//   ⑤ 기록 이어 붙이기(codex 3R blocking) = 붙을 때 화면 행 커서 인자 · 결과가 ok 아니면 좌석 맨 위 안내 줄 · 일시 실패만 다시 불러오기 + 다음 진입 자동
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
const NAMES = ["collectSids", "seatAttached", "seatInModel", "deferSeatRuntime", "ensureSeatRuntime", "destroyPaneRuntime", "retryFailedRuntimes", "seatHistoryArgs", "seatHistoryVerdict", "showSeatHistoryNotice", "retrySeatHistory", "bumpPaneGen", "ensureSeatRuntimes"];

type FakeEl = { remove(): void; querySelector(sel: string): FakeEl | null; prepend(n: FakeEl): void; after(n: FakeEl): void; append(...n: unknown[]): void; addEventListener(t: string, f: () => void): void; className: string; textContent: string; dataset: Record<string, string>; type?: string; kids: FakeEl[]; click?: () => void };
function fakeEl(): FakeEl {
  const e: FakeEl = {
    kids: [], className: "", textContent: "", dataset: {},
    remove() {
      for (const p of all) p.kids = p.kids.filter((k) => k !== e);
    },
    querySelector(sel: string) {
      const c = sel.replace(/^\./, "");
      return e.kids.find((k) => k.className === c) ?? null;
    },
    prepend(n) {
      e.kids.unshift(n);
    },
    after() {},
    append(...n) {
      for (const k of n) if (typeof k === "object") e.kids.push(k as FakeEl);
    },
    addEventListener(t, f) {
      if (t === "click") e.click = f;
    },
  };
  all.push(e);
  return e;
}
const all: FakeEl[] = [];

function harness(opts: { fail?: number; started?: unknown } = {}) {
  const paneKey = (sid: number, socket?: string): string => `${socket ?? ""}#${sid}`;
  const panes = new Map<string, Record<string, unknown>>();
  const workspaces: Record<string, unknown>[] = [
    { id: 1, socket: undefined, tree: { type: "pane", sid: 5 } },
    { id: 2, socket: undefined, tree: null },
  ];
  const releases: (() => void)[] = [];
  let fails = opts.fail ?? 0;
  const made: number[] = [];
  const disposed: number[] = [];
  const roleDots: [number, string][] = [];
  const streams: [number, Record<string, unknown>][] = [];
  const resets: number[] = [];
  const invokes: [string, Record<string, unknown>][] = [];
  const view = { work: true };
  const focusCalls: number[] = [];
  const paneGen = new Map<string, number>();
  let started: unknown = opts.started === undefined ? { history: { status: "ok", rows: 3 } } : opts.started;
  const deps: Record<string, unknown> = {
    PANE_STREAM_UNWANTED: "pane_stream_unwanted", PANE_STALE: "pane_stale", DEFERRED_TRIES_MAX: 3, SEAT_HISTORY_TEXT: "이전 출력 일부를 불러오지 못했어요",
    seatHistoryEvents: [] as unknown[], seatHistoryRetry: new Map<string, number>(), paneGen,
    document: { createElement: () => fakeEl() },
    console: { warn() {} },
    workRuntimeWanted: () => view.work,
    ensuringRuntimes: false, focusedSid: null as number | null, renders: 0,
    current: () => workspaces[0],
    wsViewTree: (w: { tree: unknown; view?: unknown }) => w.view ?? w.tree, // 묶음 탭·확대 = 보기 트리(시험이 view 로 준다)
    render: () => void (scope.renders = (scope.renders as number) + 1),
    setFocus: (sid: number) => {
      focusCalls.push(sid);
      scope.focusedSid = sid;
    },
    invoke: async (cmd: string, a: Record<string, unknown>) => {
      invokes.push([cmd, a]);
      return cmd === "start_surface_stream" ? started : null;
    },
    paneKey, panes, workspaces, exitedPaneKeys: new Set<string>(), deferredRuntimes: new Map<string, unknown>(),
    setRoleDot: (rt: { sid: number }, role: string) => void roleDots.push([rt.sid, role]),
    // 실제 makePane 계약(makepane.test.ts 가 실제 본문으로 지킨다)의 대역 — 듣기 등록 뒤 beforeStream(false = 던짐 · 객체 = start 인자) →
    //   start → 세대 대조(바뀌면 pane_stale) → afterStream(false = 스트림 정지 + 던짐) → 등록. 실패 = 등록 전 · 스스로 치움.
    makePane: async (sid: number, _t: string, socket?: string, o?: { beforeStream?: (term: unknown) => Promise<false | Record<string, unknown>>; afterStream?: (p: unknown, st: unknown) => boolean }) => {
      made.push(sid);
      const key = paneKey(sid, socket);
      const gen = paneGen.get(key) ?? 0;
      await new Promise<void>((r) => releases.push(r));
      const term = { rows: 4, reset: () => void resets.push(sid), dispose: () => void disposed.push(sid) };
      const extra = o?.beforeStream ? await o.beforeStream(term) : {};
      if (extra === false) throw new Error("pane_stream_unwanted");
      if ((paneGen.get(key) ?? 0) !== gen) throw new Error("pane_stale");
      if (fails > 0) {
        fails--;
        throw new Error("attach_surface rejected");
      }
      streams.push([sid, { socket, surfaceId: sid, ...extra }]);
      const el = fakeEl();
      if (o?.afterStream && !o.afterStream({ term, el }, started)) {
        invokes.push(["stop_surface_stream", { socket, surfaceId: sid }]);
        throw new Error("pane_stream_unwanted");
      }
      const rt = { sid, socket, disposed: false, observer: { disconnect() {} }, unlisten: [], term, el };
      panes.set(key, rt);
      return rt;
    },
  };
  const tr = new Bun.Transpiler({ loader: "ts" });
  const code = NAMES.map((n) => tr.transformSync(fnText(n))).join("\n");
  const scope: Record<string, unknown> = Object.assign(Object.create(null), deps);
  const fns = new Function("__scope", `with (__scope) {\n${code}\nreturn { ${NAMES.join(", ")} };\n}`)(scope) as Record<string, AnyFn>;
  const ledger = scope.deferredRuntimes as Map<string, unknown>;
  const go = () => releases.shift()?.();
  const tick = async () => {
    for (let i = 0; i < 8; i++) await Promise.resolve();
  };
  const setStarted = (v: unknown) => void (started = v);
  const notice = (key: string) => ((panes.get(key)?.el as FakeEl | undefined)?.kids ?? []).find((k) => k.className === "pane-history-gap") ?? null;
  return { fns, panes, workspaces, made, disposed, roleDots, ledger, go, tick, streams, invokes, view, focusCalls, scope, resets, setStarted, notice, releases };
}

const once = async (h: ReturnType<typeof harness>, key = "#5") => {
  const p = h.fns.ensureSeatRuntime(key);
  await h.tick();
  h.go();
  return p;
};

describe("(codex 2R·3R) 붙기 직전·직후 재판정 · 진입당 상한 · 기록 이어 붙이기", () => {
  it("② makePane 을 기다리는 사이 대화 화면으로 → 스트림 0 · 런타임 0 · 장부 유지 · 횟수 안 셈 → 다음 진입에 붙음", async () => {
    const h = harness();
    h.fns.deferSeatRuntime(5, undefined, "t", null, 10);
    const p = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    h.view.work = false; // 대화 화면으로 돌아감
    h.go();
    expect(await p).toBe(false);
    expect(h.streams).toEqual([]);
    expect(h.panes.has("#5")).toBe(false);
    expect(h.ledger.size).toBe(1);
    expect(h.fns.seatAttached(5, undefined)).toBe(true);
    h.view.work = true;
    expect(await once(h)).toBe(true);
    expect(h.streams.length).toBe(1);
  });
  it("③(3R major) start 를 기다린 사이 대화 화면으로 → 붙은 뒤 재판정 = 스트림 정지 · 런타임 0 · 장부 유지 · 횟수 안 셈", async () => {
    const h = harness();
    h.fns.deferSeatRuntime(5, undefined, "t", null, 10);
    const p = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    // beforeStream 은 작업 화면에서 통과하고, start 뒤 afterStream 직전에 대화 화면으로 — 대역의 start 직후에 끼우려고 beforeStream 뒤 화면을 바꾼다
    const orig = h.scope.workRuntimeWanted as () => boolean;
    let calls = 0;
    h.scope.workRuntimeWanted = () => (++calls >= 2 ? false : orig());
    h.go();
    expect(await p).toBe(false);
    expect(h.streams.length).toBe(1); // 붙었고
    expect(h.invokes.filter((x) => x[0] === "stop_surface_stream").length).toBe(1); // 곧 멈췄다
    expect(h.panes.has("#5")).toBe(false);
    expect(h.ledger.size).toBe(1);
    expect((h.ledger.get("#5") as { tries: number; making: boolean }).tries).toBe(0);
    expect((h.ledger.get("#5") as { making: boolean }).making).toBe(false);
  });
  it("④(3R major) 진입당 상한 3 · 진입마다 되돌림 = 영구 차단 0 — 5번 진입 = 15번 시도 · 장부(붙음) 유지", async () => {
    const h = harness({ fail: 100 });
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    for (let round = 0; round < 5; round++) {
      for (let i = 0; i < 3; i++) expect(await once(h)).toBe(false);
      expect(await h.fns.ensureSeatRuntime("#5")).toBe(false); // 이 진입의 상한 — 시도 0
      h.fns.retryFailedRuntimes(); // 작업 화면 재진입
    }
    expect(h.made.length).toBe(15);
    expect(h.ledger.size).toBe(1);
  });
  it("① 기록 이어 붙이기: start 인자 = 미룬 그때 화면 행 커서 + xterm 행 수 · ok = 안내 0 · 사건 1", async () => {
    const h = harness();
    h.fns.deferSeatRuntime(5, undefined, "t", null, 100);
    expect(await once(h)).toBe(true);
    expect(h.streams).toEqual([[5, { socket: undefined, surfaceId: 5, historySince: 100, historyRows: 4 }]]);
    expect(h.notice("#5")).toBe(null);
    expect((h.scope.seatHistoryEvents as { key: string; status: string }[]).map((e) => [e.key, e.status])).toEqual([["#5", "ok"]]);
  });
  it("②(3R blocking) 잘림·모르는 커서·구 데몬 = 안내 줄(다시 불러오기 없음) · 커서 모름 = 인자 없이 붙고 안내", async () => {
    for (const [cursor, started, status] of [
      [100, { history: { status: "truncated", rows: 5000 } }, "truncated"],
      [100, { history: { status: "unknown_cursor", rows: 0 } }, "unknown_cursor"],
      [100, null, "unsupported"],
      [null, null, "no_cursor"],
    ] as const) {
      const h = harness({ started });
      h.fns.deferSeatRuntime(5, undefined, "t", null, cursor);
      expect(await once(h)).toBe(true);
      const n = h.notice("#5");
      expect({ status, text: n?.textContent, data: n?.dataset.status, button: n?.kids.length ?? -1 }).toEqual({ status, text: "이전 출력 일부를 불러오지 못했어요", data: status, button: 0 });
      expect((h.scope.seatHistoryRetry as Map<string, number>).size).toBe(0);
      if (cursor === null) expect(h.streams[0][1]).toEqual({ socket: undefined, surfaceId: 5 });
    }
  });
  it("②(3R blocking) 손잡기 시한·오류 = 안내 줄 + 다시 불러오기 → 누르면 화면 비우고 같은 커서로 다시 붙음 · ok 면 안내 지움 · 다음 진입 자동 재시도", async () => {
    const h = harness({ started: { history: { status: "timeout" } } });
    h.fns.deferSeatRuntime(5, undefined, "t", null, 100);
    expect(await once(h)).toBe(true);
    const n = h.notice("#5") as FakeEl;
    expect(n.dataset.status).toBe("timeout");
    const btn = n.kids[0];
    expect(btn.textContent).toBe("다시 불러오기");
    expect((h.scope.seatHistoryRetry as Map<string, number>).get("#5")).toBe(100);
    // 누름 — 아직 시한 → 안내 그대로
    btn.click?.();
    await h.tick();
    expect(h.resets).toEqual([5]);
    expect(h.invokes.filter((x) => x[0] === "start_surface_stream").at(-1)).toEqual(["start_surface_stream", { socket: undefined, surfaceId: 5, historySince: 100, historyRows: 4 }]);
    expect(h.notice("#5")?.dataset.status).toBe("timeout");
    // 다음 작업 화면 진입 = 자동 재시도 · 이번엔 ok → 안내 지움 · 장부 비움
    h.setStarted({ history: { status: "ok", rows: 9 } });
    h.fns.retryFailedRuntimes();
    await h.tick();
    expect(h.resets).toEqual([5, 5]);
    expect(h.notice("#5")).toBe(null);
    expect((h.scope.seatHistoryRetry as Map<string, number>).size).toBe(0);
    // 파기된 좌석은 재시도 장부에서 빠진다
    h.setStarted({ history: { status: "error" } });
    void h.fns.retrySeatHistory("#5");
    h.fns.destroyPaneRuntime(5, undefined);
    expect((h.scope.seatHistoryRetry as Map<string, number>).size).toBe(0);
  });
  it("⑤(3R major) 파기 → 같은 좌석 재입양 → 옛 시도 늦게 끝남: 새 런타임·새 장부 무사 · 옛 시도 = 횟수·장부 무접촉", async () => {
    const h = harness();
    h.fns.deferSeatRuntime(5, undefined, "t", null, 1);
    const a = h.fns.ensureSeatRuntime("#5"); // 옛 시도 — 붙잡힘
    await h.tick();
    h.fns.destroyPaneRuntime(5, undefined); // 떼기(세대 올림 · 장부 비움)
    h.fns.deferSeatRuntime(5, undefined, "t", null, 2); // 재입양(대화 화면 모형만 → 새 장부)
    const b = h.fns.ensureSeatRuntime("#5"); // 새 시도
    await h.tick();
    h.releases[1](); // 새 시도가 먼저 끝남
    expect(await b).toBe(true);
    const fresh = h.panes.get("#5");
    h.releases[0](); // 옛 시도가 늦게 끝남
    expect(await a).toBe(false);
    expect(h.panes.get("#5")).toBe(fresh);
    expect(h.disposed).toEqual([]); // 새 런타임을 부수지 않았다
    expect(h.ledger.size).toBe(0);
    expect(h.streams.map((x) => x[1].historySince)).toEqual([2]); // 옛 시도는 붙지도 않았다(세대 대조)
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
    h.panes.set("#4", { sid: 4, disposed: false, observer: { disconnect() {} }, unlisten: [], term: { dispose() {} }, el: fakeEl() });
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
  it("② 기다린 사이 떼임 → 세대가 바뀌어 makePane 이 붙지 않고 제 것을 치움(makepane.test ②) · 등록 0 · 장부 0", async () => {
    const h = harness();
    h.fns.deferSeatRuntime(5, undefined, "t", null);
    const p = h.fns.ensureSeatRuntime("#5");
    await h.tick();
    (h.workspaces[0] as { tree: unknown }).tree = null; // detachPane 이 트리에서 뗌
    h.fns.destroyPaneRuntime(5, undefined); //            … 그리고 장부를 비움
    h.go();
    expect(await p).toBe(false);
    expect(h.panes.has("#5")).toBe(false);
    expect(h.streams).toEqual([]); // 붙지도 않았다
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
    h.panes.set("#9", { sid: 9, disposed: false, observer: { disconnect() {} }, unlisten: [], term: { dispose() {} }, el: fakeEl() });
    expect(await h.fns.ensureSeatRuntime("#9")).toBe(false);
    expect(h.ledger.has("#9")).toBe(false);
  });
});
