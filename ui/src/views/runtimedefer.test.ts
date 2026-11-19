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
const NAMES = ["collectSids", "seatAttached", "seatInModel", "deferSeatRuntime", "ensureSeatRuntime", "destroyPaneRuntime", "retryFailedRuntimes"];

function harness(opts: { fail?: number } = {}) {
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
  const deps: Record<string, unknown> = {
    paneKey, panes, workspaces, exitedPaneKeys: new Set<string>(), deferredRuntimes: new Map<string, unknown>(),
    setRoleDot: (rt: { sid: number }, role: string) => void roleDots.push([rt.sid, role]),
    makePane: async (sid: number, _t: string, socket?: string) => {
      made.push(sid);
      await new Promise<void>((r) => (release = r));
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
  return { fns, panes, workspaces, made, disposed, roleDots, ledger, go, tick };
}

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
