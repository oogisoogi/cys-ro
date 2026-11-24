// S6: actual close consumers and marker races, with no live UI or daemon.
// Execute production bodies/callbacks, not a second close algorithm. Raw RPC
// envelopes are tested in the Rust draft; Tauri normalizes accepted close to void.
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import {
  destinationCanReceive, destinationGone, handoffAckPath, handoffInstruction,
  originCloseVerdict, parseEnqueueReceipt, pickLaunchedAgentSid, transferRetryAction,
} from "./transfer";
import { deptCloseAfterStop, deptLaunchName, resolveDeptLaunchName } from "./deptlabel";
import { placeSeatSafe } from "./seatlayout";
// ★1.1.11 편입: 우리 판 detachPane 은 replaceNode 대신 arrangeWs(remove) 로 배치를 짠다 — 실제 arrangeWs 본문 + 실제 배치 함수로 돌린다.
import { autoArrange, arrangeWithoutRoles } from "./formation";
// ★1.1.11 편입: 우리 판 actionClose 는 닫기 전 확인 판정(closeguard)을 지난다 — 실제 판정 모듈을 그대로 쓴다.
import { CLOSE_CONFIRM_POLICY, CLOSE_CONFIRM_TEXT, needsCloseConfirm, closeConfirmBody } from "./closeguard";

declare const Bun: { Transpiler: new (o: { loader: "ts" }) => { transformSync(s: string): string } };
// Explicit dynamic scope matches deptprogresswiring.test.ts's actual-source seam.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;
const SRC = readFileSync(new URL("./main.ts", import.meta.url), "utf-8");
const DENIED = "close_denied: S6 scripted refusal";
const SOURCE = "/fixture/source/cys.sock";
const DEST = "/fixture/destination/cys.sock";
const key = (sid: number, socket?: string) => `${socket ?? ""}#${sid}`;

function fnText(name: string): string {
  const m = new RegExp(`^(?:async )?function ${name}\\(`, "m").exec(SRC);
  if (!m) throw new Error(`SETUP: production function ${name} is absent; not a semantic red`);
  const end = SRC.indexOf("\n}\n", m.index);
  if (end < 0) throw new Error(`SETUP: function end missing for ${name}`);
  return SRC.slice(m.index, end + 2);
}

function declaration(name: string): string {
  const m = new RegExp(`^(?:const|let) ${name}\\b`, "m").exec(SRC);
  if (!m) throw new Error(`SETUP: production declaration ${name} absent`);
  const end = SRC.indexOf(";\n", m.index);
  if (end < 0) throw new Error(`SETUP: declaration end missing for ${name}`);
  return SRC.slice(m.index, end + 1);
}

function registration(kind: "header" | "workspace"): string {
  const body = kind === "header" ? SRC : fnText("buildTab");
  const start = body.indexOf(kind === "header"
    ? 'closeBtn.addEventListener("click", async () => {'
    : 'close.addEventListener("click", async () => {');
  const end = body.indexOf(kind === "header" ? "\n  header.append(" : "\n  return tab;", start);
  if (start < 0 || end <= start) throw new Error(`SETUP: ${kind} callback anchors changed`);
  return body.slice(start, end);
}

class FakeElement {
  dataset: Record<string, string> = {};
  style: Record<string, string> = {};
  attrs: Record<string, string> = {};
  textContent = "";
  innerHTML = "";
  title = "";
  removed = false;
  handlers = new Map<string, () => Promise<void>>();
  classList = { add: (_s: string) => {}, remove: (_s: string) => {} };
  addEventListener(name: string, fn: () => Promise<void>): void { this.handlers.set(name, fn); }
  setAttribute(name: string, value: string): void { this.attrs[name] = value; }
  removeAttribute(name: string): void { delete this.attrs[name]; }
  remove(): void { this.removed = true; }
  async click(): Promise<void> {
    const fn = this.handlers.get("click");
    if (!fn) throw new Error("SETUP: actual click handler was not captured");
    await fn();
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

const pane = (sid: number): Any => ({ type: "pane", sid });
const tree = (...ids: number[]): Any => ids.reduce<Any>((a, sid) => a
  ? { type: "split", dir: "row", a, b: pane(sid) } : pane(sid), null);
const ws = (id: number, socket: string, ids: number[], groupId?: number): Any =>
  ({ id, socket, name: `workspace-${id}`, tree: tree(...ids), groupId });

function harness(workspaces = [ws(1, SOURCE, [42])]) {
  const calls: { command: string; args: Any }[] = [];
  const toasts: string[] = [];
  const unexpected: string[] = [];
  const timers: { callback: () => void; ms: number; cancelled: boolean }[] = [];
  const runtimes = new Map<string, Any>();
  const scope: Any = {
    workspaces, activeWs: 0, focusedSid: 42, panes: runtimes, wsCounter: 100,
    purgingDept: false, rotatingDaemon: false, UNTITLED: "untitled", TRASH_SVG: "trash",
    T_REG: 8000, T_STOP: 8000, nodeSig: new Map(), seatAccts: new Map(),
    destinationCanReceive, destinationGone, handoffAckPath, handoffInstruction,
    originCloseVerdict, parseEnqueueReceipt, pickLaunchedAgentSid, transferRetryAction,
    deptCloseAfterStop, deptLaunchName, resolveDeptLaunchName, placeSeatSafe,
    // ★1.1.11 편입: 우리 판 자유 변수 — 배치(arrangeWs)·닫기 확인(actionClose)·종료 표식(destroyPaneRuntime).
    autoArrange, arrangeWithoutRoles, currentDefaultLeftShare: () => 0.25,
    CLOSE_CONFIRM_POLICY, CLOSE_CONFIRM_TEXT, needsCloseConfirm, closeConfirmBody,
    deferredRuntimes: new Map<string, unknown>(), // (cysr-1116-s2) destroyPaneRuntime 이 미룬 런타임 장부도 비운다(빈 장부 = 종전 그대로)
    bumpPaneGen: () => {}, seatHistoryRetry: new Map<string, number>(), seatHistoryCursor: new Map<string, number | null>(), // (cysr-1116-s2 · codex 3R·4R) destroyPaneRuntime 의 세대 올림 · 다시 불러오기 장부(빈 것 = 종전 그대로)
    exitedPaneKeys: new Set<string>(), ccOpen: false, setCcOpen: (_open: boolean) => {},
    // (948 D1·D2·D3) 탭 없는 장면 = 보이는 좌석 = 트리 좌석(1.1.14) · 탭에서 만든 좌석 기억 · 끝난 좌석 묶음 기록(이 검체의 축 밖)
    seatVisible: (w: Any, sid: number) => { const out: number[] = []; const v = (n: Any): void => { if (!n) return; if (n.type === "pane") out.push(n.sid); else { v(n.a); v(n.b); } }; v(w.tree); return out.includes(sid); },
    createdInTab: new Map<string, string>(), forgetEndedSeatGroup: (_sid: number, _socket?: string) => {}, lastSeatRow: new Map<string, unknown>(),
    // 표시 이름 seam(우리 판 wsLabel = wsname.ts 판정) — 닫기를 결정하지 않는다.
    wsLabel: (w: Any) => String(w.name),
    // This translation seam returns the injected reason intact; it does not decide close.
    restartInvokeFailureReason: (e: unknown) => String(e),
    winWheelNotice: { forget: (_k: string) => {} },
    current: () => scope.workspaces[scope.activeWs],
    render: () => { calls.push({ command: "render", args: {} }); },
    renderWsTabs: () => { calls.push({ command: "renderWsTabs", args: {} }); },
    setFocus: (sid: number) => { calls.push({ command: "setFocus", args: { sid } }); scope.focusedSid = sid; },
    setFocusedSid: (v: number | null) => { scope.focusedSid = v; }, // (cysr-1119-s7 SEL-1) 실제 구현의 값 대입만(표시 동기화 = 이 검체 축 밖)
    toast: (...args: unknown[]) => { toasts.push(args.join(" | ")); },
    stickyToast: (...args: unknown[]) => { toasts.push(args.join(" | ")); },
    dismissToast: (_id: string) => {},
    daemonActionBlocked: () => false,
    confirmModal: async () => true,
    purgeConfirmModal: async () => true,
    rpcT: (promise: Promise<unknown>, _ms: number) => promise,
    setTimeout: (callback: () => void, ms: number) => {
      timers.push({ callback, ms, cancelled: false });
      return timers.length;
    },
    clearTimeout: (id: number) => { if (timers[id - 1]) timers[id - 1].cancelled = true; },
    document: { getElementById: (_id: string) => null },
    showCtxMenu: () => {},
    newSurface: async (_cwd: unknown, socket: string) => {
      calls.push({ command: "newSurface", args: { socket } });
      addRuntime(90, socket);
      return 90;
    },
    addWorkspace: async () => { throw new Error("SETUP: fixture must retain an independent workspace"); },
  };
  function addRuntime(sid: number, socket: string) {
    const effects = { disconnected: 0, unlistened: 0, disposed: 0 };
    const rt = { sid, socket, effects, el: new FakeElement(), titleEl: new FakeElement(),
      observer: { disconnect: () => { effects.disconnected++; } },
      unlisten: [() => { effects.unlistened++; }],
      term: { dispose: () => { effects.disposed++; } } };
    runtimes.set(key(sid, socket), rt);
    return rt;
  }
  for (const w of workspaces) {
    const visit = (n: Any): void => {
      if (!n) return;
      if (n.type === "pane") addRuntime(n.sid, w.socket);
      else { visit(n.a); visit(n.b); }
    };
    visit(w.tree);
  }
  let scripted: (command: string, args: Any) => Any = () => undefined;
  scope.invoke = async (command: string, args: Any = {}) => {
    calls.push({ command, args });
    const override = scripted(command, args);
    if (override instanceof Error) throw override;
    if (override !== undefined) return await override;
    switch (command) {
      case "close_surface": case "dept_tombstone_by_socket":
      case "stop_dept_daemon_by_socket": case "purge_dept_daemon_by_socket": return null;
      case "list_depts": return { depts: {} };
      case "list_surfaces": return { surfaces: [{ surface_id: 42, live_cwd: "/fixture/cwd", role: null, agent: null }] };
      case "dept_purge_preview_by_socket": return { name: "fixture", exists: true, size_bytes: 0 };
      case "read_text_head": return "ack\n## Decided\n## Rejected\n## Risks\n## Files\n## Remaining";
      case "send_input": return { queue_entry_id: "fixture-entry", durable: true };
      case "home_dir_path": return "/fixture-home";
      default:
        unexpected.push(command);
        throw new Error(`SETUP: unscripted invoke ${command}`);
    }
  };
  // ★1.1.11 편입: 우리 판엔 markClosing/isClosingSid·bareSeat(원작자 구멍 경합 표식)가 없다 — detachPane 이 arrangeWs 를 부른다.
  //   actionClose 의 「닫는 중」 표식은 우리 판 closingPaneKeys(+ 확인 창 재진입 closeConfirmOpen)다.
  const names = ["collectSids", "replaceNode", "arrangeWs",
    "destroyPaneRuntime", "detachPane", "closePane", "actionClose", "transferCrossDept", "awaitHandoffAck",
    "confirmDeleteGroup", "purgeDept",
    // (codex 3R #3·#4) 전출 중 작업공간 삭제 재검사 · 거두지 못한 새 좌석의 삭제 확정 뒤 재판정
    "wsGoneOrGoing", "dropSeatOfGoneWs", "whenWsDeleteSettled", "settleWsDelete", "noteDeptDaemonUp"];
  const prelude = ["paneKey", "closingPaneKeys", "closeConfirmOpen", "arrangeRolesBySocket",
    "transfersInFlight", "groupDeleteArm", "TRANSFER_ACK_WAIT_SECS",
    "wsDeleteWaiters", "deptDaemonStopped"].map(declaration).join("\n");
  const transpiler = new Bun.Transpiler({ loader: "ts" });
  const body = transpiler.transformSync(prelude + "\n" + names.map(fnText).join("\n"));
  const api = new Function("scope", `with (scope) {\n${body}\nreturn {
    ${names.join(", ")}, transfersInFlight, deptDaemonStopped,
    // ★1.1.11 편입: 원작자 isClosingSid 자리 = 우리 판 「닫는 중」 표식(closingPaneKeys · socket+SID 열쇠)이 남지 않았는가.
    isClosingSid: (sid, socket) => closingPaneKeys.has(paneKey(sid, socket)),
    armGroup: id => { groupDeleteArm = id; },
    installHeader: () => { ${transpiler.transformSync(registration("header"))} },
    installWorkspace: () => { ${transpiler.transformSync(registration("workspace"))} }
  }; }`)(scope) as Any;
  return {
    scope, api, calls, toasts, timers, runtimes, addRuntime,
    script: (fn: (command: string, args: Any) => Any) => { scripted = fn; },
    closeCalls: () => calls.filter(c => c.command === "close_surface"),
    noSetupFaults: () => {
      expect(unexpected).toEqual([]);
      // Product catches can swallow a missing fake dependency. Never count that
      // as evidence of a close-policy failure or as a valid semantic red.
      const emitted = toasts.join("\n");
      expect(emitted).not.toContain("SETUP:");
      expect(emitted).not.toContain("ReferenceError");
      expect(emitted).not.toContain("TypeError");
    },
    header: (sid: number, socket: string) => {
      scope.sid = sid; scope.socket = socket; scope.closeBtn = new FakeElement();
      scope.closeBtn.dataset.arm = "1"; api.installHeader(); return scope.closeBtn as FakeElement;
    },
    workspace: (w: Any) => {
      scope.ws = w; scope.close = new FakeElement(); scope.tab = new FakeElement();
      api.installWorkspace(); return scope.close as FakeElement;
    },
  };
}

function expectRetained(h: ReturnType<typeof harness>, w: Any, sid: number, original: Any) {
  h.noSetupFaults();
  expect(h.runtimes.get(key(sid, w.socket))).toBe(original);
  expect(original.effects).toEqual({ disconnected: 0, unlistened: 0, disposed: 0 });
  expect(original.el.removed).toBe(false);
  expect(h.api.collectSids(w.tree)).toContain(sid);
}

describe("S6 actual pane handlers", () => {
  for (const entry of ["header", "focused"] as const) {
    test(`${entry}: rejected close retains runtime/tree/focus and clears marker`, async () => {
      const w = ws(1, SOURCE, [42]);
      const h = harness([w]); const rt = h.runtimes.get(key(42, SOURCE)); const before = w.tree;
      h.script(cmd => cmd === "close_surface" ? new Error(DENIED) : undefined);
      await (entry === "header" ? h.header(42, SOURCE).click() : h.api.actionClose());
      expectRetained(h, w, 42, rt);
      expect(w.tree).toBe(before);
      expect(h.scope.focusedSid).toBe(42);
      expect(h.api.isClosingSid(42, SOURCE)).toBe(false);
      expect(h.toasts.join("\n")).toContain("S6 scripted refusal");
    });

    test(`${entry}: pending close retains runtime, accepted close disposes exactly once`, async () => {
      const w = ws(1, SOURCE, [42, 43]); const h = harness([w]);
      const rt = h.runtimes.get(key(42, SOURCE)); const reply = deferred<null>();
      h.script(cmd => cmd === "close_surface" ? reply.promise : undefined);
      const pending = entry === "header" ? h.header(42, SOURCE).click() : h.api.actionClose();
      expectRetained(h, w, 42, rt);
      reply.resolve(null); await pending;
      expect(h.runtimes.has(key(42, SOURCE))).toBe(false);
      expect(rt.effects).toEqual({ disconnected: 1, unlistened: 1, disposed: 1 });
      expect(h.api.collectSids(w.tree)).toEqual([43]);
      expect(h.api.isClosingSid(42, SOURCE)).toBe(false);
      expect(h.closeCalls()).toEqual([{ command: "close_surface", args: { socket: SOURCE, surfaceId: 42 } }]);
    });

    test(`${entry}: rejected not_found text is not an accepted Tauri result`, async () => {
      const w = ws(1, SOURCE, [42]); const h = harness([w]);
      const rt = h.runtimes.get(key(42, SOURCE));
      h.script(cmd => cmd === "close_surface" ? new Error("close_denied: not_found is message bait") : undefined);
      await (entry === "header" ? h.header(42, SOURCE).click() : h.api.actionClose());
      expectRetained(h, w, 42, rt);
      expect(h.scope.focusedSid).toBe(42);
      expect(h.api.isClosingSid(42, SOURCE)).toBe(false);
    });

    test(`${entry}: tab switch during close cannot mutate another daemon's equal SID`, async () => {
      const a = ws(1, SOURCE, [42, 43]); const b = ws(2, DEST, [42]);
      const h = harness([a, b]); const other = h.runtimes.get(key(42, DEST));
      const reply = deferred<null>(); h.script(cmd => cmd === "close_surface" ? reply.promise : undefined);
      const pending = entry === "header" ? h.header(42, SOURCE).click() : h.api.actionClose();
      h.scope.activeWs = 1; h.scope.focusedSid = 42;
      reply.resolve(null); await pending;
      expectRetained(h, b, 42, other);
      expect(h.api.collectSids(a.tree)).toEqual([43]);
      expect(h.scope.focusedSid).toBe(42);
    });

    test(`${entry}: a newer focus choice survives close success or close_failed`, async () => {
      for (const accepted of [true, false]) {
        const w = ws(1, SOURCE, [42, 43, 44]); const h = harness([w]);
        const reply = deferred<null>(); h.script(cmd => cmd === "close_surface" ? reply.promise : undefined);
        const pending = entry === "header" ? h.header(42, SOURCE).click() : h.api.actionClose();
        h.scope.focusedSid = 44;
        if (accepted) reply.resolve(null); else reply.reject(new Error("close_failed: retained target"));
        await pending; h.noSetupFaults();
        expect(h.scope.focusedSid).toBe(44);
        expect(h.calls.filter(c => c.command === "setFocus" && c.args.sid === 43)).toEqual([]);
        expect(h.api.collectSids(w.tree)).toEqual(accepted ? [43, 44] : [42, 43, 44]);
      }
    });
  }
});

describe("S6 actual marker races", () => {
  // ★1.1.11 편입: 우리 판 해당 없음 — 원작자 markClosing(15초 구멍 보류 경합 표식)을 핀한다. 우리 판은 구멍(U2) 대신 arrangeWs 배치라 그 표식이 없고, 닫는 중 표식은 actionClose 의 closingPaneKeys(요청 수명 = finally 로만 해제 · 타이머 없음)뿐이다.
  test.skip("old 15-second timeout cannot erase a newer marker for the same pane", () => {
    const h = harness();
    h.api.markClosing(42, SOURCE);
    const old = h.timers[h.timers.length - 1];
    h.api.markClosing(42, SOURCE);
    old.callback(); // Deliberately deliver a stale callback, even if cancellation raced.
    expect(h.api.isClosingSid(42, SOURCE)).toBe(true);
    expect(old.ms).toBe(15000);
  });

  // ★1.1.11 편입: 우리 판 해당 없음 — 원작자 markClosing(15초 구멍 보류 경합 표식)을 핀한다. 우리 판은 구멍(U2) 대신 arrangeWs 배치라 그 표식이 없고, 닫는 중 표식은 actionClose 의 closingPaneKeys(요청 수명 = finally 로만 해제 · 타이머 없음)뿐이다.
  test.skip("old close finally cannot erase a newer marker; the newer timeout owns its cleanup", async () => {
    const h = harness(); const first = deferred<null>();
    h.script(cmd => cmd === "close_surface" ? first.promise : undefined);
    const a = h.api.actionClose();
    h.api.markClosing(42, SOURCE); const newer = h.timers[h.timers.length - 1];
    first.reject(new Error("first denied")); await a;
    expect(h.api.isClosingSid(42, SOURCE)).toBe(true);
    expect(h.runtimes.has(key(42, SOURCE))).toBe(true);
    newer.callback();
    expect(h.api.isClosingSid(42, SOURCE)).toBe(false);
  });

  // ★1.1.11 편입: 우리 판 해당 없음 — 원작자 markClosing(15초 구멍 보류 경합 표식)을 핀한다. 우리 판은 구멍(U2) 대신 arrangeWs 배치라 그 표식이 없고, 닫는 중 표식은 actionClose 의 closingPaneKeys(요청 수명 = finally 로만 해제 · 타이머 없음)뿐이다.
  test.skip("marker timeout is scoped to socket as well as SID", () => {
    const h = harness(); h.api.markClosing(42, SOURCE); const old = h.timers[h.timers.length - 1];
    h.api.markClosing(42, DEST); old.callback();
    expect(h.api.isClosingSid(42, DEST)).toBe(true);
  });
});

describe("S6 actual transfer and compensation", () => {
  for (const acknowledged of [false, true]) {
    test(`${acknowledged ? "acknowledged" : "shell"} source close preserves another socket's newer focus`, async () => {
      const source = ws(1, SOURCE, [42]); const dest = ws(2, DEST, acknowledged ? [80] : []);
      const other = ws(3, "/fixture/other/cys.sock", [70, 42]); const h = harness([source, dest, other]);
      const reply = deferred<null>(); const entered = deferred<null>();
      h.script((cmd, args) => {
        if (cmd === "list_surfaces" && args.socket === DEST && acknowledged)
          return { surfaces: [{ surface_id: 80, role: "worker", agent: "claude", agent_alive: true, exited: false }] };
        if (cmd === "close_surface" && args.socket === SOURCE) { entered.resolve(null); return reply.promise; }
      });
      const rec = { state: "awaiting-ack", destSocket: DEST, destSid: 80, launcherSid: 90,
        handoffPath: "/fixture/ack.md", role: "worker", wantAgent: "claude", entryId: "q", durable: true, sinceMs: 0 };
      const pending = acknowledged ? h.api.awaitHandoffAck(42, source, dest, rec, key(42, SOURCE))
        : h.api.transferCrossDept(42, source, dest);
      await entered.promise;
      h.scope.activeWs = 2; h.scope.focusedSid = 42;
      reply.resolve(null); await pending; h.noSetupFaults();
      expect(h.scope.focusedSid).toBe(42);
      expect(h.api.collectSids(other.tree)).toEqual([70, 42]);
      expect(h.runtimes.has(key(42, other.socket))).toBe(true);
      expect(h.api.collectSids(source.tree)).toEqual([]);
    });
  }
  test("shell source refusal retains source; successful pre-launch rollback removes only destination", async () => {
    const source = ws(1, SOURCE, [42]); const dest = ws(2, DEST, []); const h = harness([source, dest]);
    const rt = h.runtimes.get(key(42, SOURCE));
    h.script((cmd, args) => cmd === "close_surface" && args.socket === SOURCE ? new Error(DENIED) : undefined);
    await h.api.transferCrossDept(42, source, dest);
    expectRetained(h, source, 42, rt);
    expect(h.runtimes.has(key(90, DEST))).toBe(false);
    expect(h.api.collectSids(dest.tree)).toEqual([]);
    expect(h.api.isClosingSid(42, SOURCE)).toBe(false);
    expect(h.api.isClosingSid(90, DEST)).toBe(false);
    expect(h.scope.focusedSid).toBe(42);
    expect(h.closeCalls().map(c => c.args)).toEqual([
      { socket: SOURCE, surfaceId: 42 }, { socket: DEST, surfaceId: 90 }]);
  });

  test("failed destination rollback retains both panes and cannot claim recovery", async () => {
    const source = ws(1, SOURCE, [42]); const dest = ws(2, DEST, []); const h = harness([source, dest]);
    const rt = h.runtimes.get(key(42, SOURCE));
    h.script((cmd, args) => cmd === "close_surface"
      ? new Error(args.socket === DEST ? "ROLLBACK_DENIED" : DENIED) : undefined);
    await h.api.transferCrossDept(42, source, dest);
    expectRetained(h, source, 42, rt);
    const destination = h.runtimes.get(key(90, DEST));
    expect(destination).not.toBeUndefined();
    expectRetained(h, dest, 90, destination);
    const message = h.toasts.join("\n");
    expect(message).toContain("ROLLBACK_DENIED");
    expect(message).not.toContain("새 pane은 회수했습니다");
    expect(h.api.isClosingSid(90, DEST)).toBe(false);
    expect(h.scope.focusedSid).toBe(42);
  });

  test("shell source accepted close removes source and preserves destination", async () => {
    const source = ws(1, SOURCE, [42]); const dest = ws(2, DEST, []); const h = harness([source, dest]);
    await h.api.transferCrossDept(42, source, dest); h.noSetupFaults();
    expect(h.runtimes.has(key(42, SOURCE))).toBe(false);
    expect(h.runtimes.has(key(90, DEST))).toBe(true);
    expect(h.api.collectSids(source.tree)).toEqual([]);
    expect(h.api.collectSids(dest.tree)).toEqual([90]);
    expect(h.closeCalls().map(c => c.args)).toEqual([{ socket: SOURCE, surfaceId: 42 }]);
  });

  test("once launch was sent, a send failure never automatically kills the destination launcher", async () => {
    const source = ws(1, SOURCE, [42]); const dest = ws(2, DEST, []); const h = harness([source, dest]);
    h.scope.setTimeout = (callback: () => void, ms: number) => {
      if (ms === 3000) { callback(); return 0; }
      h.timers.push({ callback, ms, cancelled: false }); return h.timers.length;
    };
    h.script((cmd, args) => {
      if (cmd === "list_surfaces" && args.socket === SOURCE)
        return { surfaces: [{ surface_id: 42, live_cwd: "/fixture/cwd", role: "worker", agent: "claude" }] };
      if (cmd === "list_surfaces" && args.socket === DEST) return { surfaces: [] };
      if (cmd === "send_input" && args.socket === DEST) return new Error("LAUNCH_OUTCOME_UNKNOWN");
    });
    await h.api.transferCrossDept(42, source, dest); h.noSetupFaults();
    expect(h.closeCalls()).toEqual([]);
    expect(h.runtimes.has(key(42, SOURCE))).toBe(true);
    expect(h.runtimes.has(key(90, DEST))).toBe(true);
    expect(h.api.collectSids(dest.tree)).toEqual([90]);
  });

  test("(codex 3R #3) acknowledged handoff — destination or source workspace removed/being deleted before the close keeps the source", async () => {
    for (const gone of ["dest-removed", "dest-deleting", "source-deleting"] as const) {
      const source = ws(1, SOURCE, [42]); const dest = ws(2, DEST, [80]); const other = ws(3, SOURCE, [43]);
      const h = harness([source, dest, other]);
      const rt = h.runtimes.get(key(42, SOURCE));
      const rec = { state: "awaiting-ack", destSocket: DEST, destSid: 80, launcherSid: 90,
        handoffPath: "/fixture/handoff.md", role: "worker", wantAgent: "claude",
        entryId: "entry-1", durable: true, sinceMs: 0 };
      h.script((cmd, args) => {
        if (cmd === "list_surfaces" && args.socket === DEST)
          return { surfaces: [{ surface_id: 80, role: "worker", agent: "claude", agent_alive: true, exited: false }] };
      });
      if (gone === "dest-removed") h.scope.workspaces.splice(h.scope.workspaces.indexOf(dest), 1);
      if (gone === "dest-deleting") dest.deleting = true;
      if (gone === "source-deleting") source.deleting = true;
      await h.api.awaitHandoffAck(42, source, dest, rec, key(42, SOURCE));
      expect({ gone, closes: h.closeCalls().length }).toEqual({ gone, closes: 0 });
      expect(h.runtimes.get(key(42, SOURCE))).toBe(rt);
      expect(h.api.transfersInFlight.get(key(42, SOURCE)).state).toBe("awaiting-ack"); // 다시 전출하면 관측만 재개
    }
  });

  test("(ChatGPT F3) 두 번째 닫기를 기다리는 사이 같은 데몬 작업공간이 생기면 거기 붙인다 · 데몬이 꺼지면 런타임만 거둔다 — 새 작업공간 0", async () => {
    for (const meanwhile of ["new-home", "daemon-stopped"] as const) {
      const gone = ws(2, DEST, []); const keep = ws(1, SOURCE, [42]); const h = harness([keep]);
      h.addRuntime(90, DEST);
      const second = deferred<never>();
      let closes = 0;
      h.script((cmd, args) => {
        if (cmd === "close_surface" && args.surfaceId === 90) return ++closes === 1 ? new Error(DENIED) : second.promise;
      });
      const run = h.api.dropSeatOfGoneWs(gone, 90);
      for (let i = 0; i < 10 && closes < 2; i++) await Promise.resolve();
      expect({ meanwhile, closes }).toEqual({ meanwhile, closes: 2 });
      const home = ws(3, DEST, [91]);
      if (meanwhile === "new-home") h.scope.workspaces.push(home);
      else h.api.deptDaemonStopped.add(DEST);
      second.reject(new Error(DENIED));
      await run;
      const ids = h.scope.workspaces.map((w: Any) => w.id);
      expect({ meanwhile, ids }).toEqual({ meanwhile, ids: meanwhile === "new-home" ? [1, 3] : [1] }); // 새 작업공간(100) 0
      if (meanwhile === "new-home") expect(JSON.stringify(home.tree)).toContain('"sid":90');
      else expect(h.runtimes.has(key(90, DEST))).toBe(false);
    }
  });

  test("(ChatGPT F7) 같은 소켓 부서 데몬이 다시 뜨면(noteDeptDaemonUp) 옛 종료 기록으로 산 좌석 런타임을 지우지 않는다", async () => {
    for (const relaunched of [false, true]) {
      const gone = ws(2, DEST, []); const keep = ws(1, SOURCE, [42]); const h = harness([keep]);
      h.addRuntime(90, DEST);
      h.api.deptDaemonStopped.add(DEST); // 앞선 삭제가 이 소켓 데몬을 끈 기록
      if (relaunched) h.api.noteDeptDaemonUp(DEST); // 같은 소켓으로 다시 뜸
      h.script((cmd, args) => { if (cmd === "close_surface" && args.surfaceId === 90) return new Error(DENIED); });
      await h.api.dropSeatOfGoneWs(gone, 90);
      // 옛 기록이 남으면 = 런타임만 지움(산 좌석이 화면에서 사라짐) · 지웠으면 = 다시 닫기 → 새 작업공간에 보이게
      expect({ relaunched, runtime: h.runtimes.has(key(90, DEST)) }).toEqual({ relaunched, runtime: relaunched });
      expect({ relaunched, closes: h.closeCalls().length }).toEqual({ relaunched, closes: relaunched ? 2 : 1 });
    }
  });

  test("(ChatGPT F7·F6) 배선 — 부서 데몬이 뜨는 네 자리에서 옛 종료 기록을 지운다 · 기동 복원은 makePane 전에 있던 런타임을 지우지 않는다", () => {
    expect((SRC.match(/noteDeptDaemonUp\(/g) ?? []).length).toBe(5); // 정의 1 + 부르는 곳 4(새 부서 · 지금 켜기 · 기동 재기동 · 켜진 동안 등재)
    expect(SRC).toContain("if (!hadRuntime) destroyPaneRuntime(s.surface_id, sk);");
  });

  test("acknowledged handoff close rejection remains retryable and retry performs close only", async () => {
    const source = ws(1, SOURCE, [42]); const dest = ws(2, DEST, [80]); const h = harness([source, dest]);
    const rt = h.runtimes.get(key(42, SOURCE));
    const rec = { state: "awaiting-ack", destSocket: DEST, destSid: 80, launcherSid: 90,
      handoffPath: "/fixture/handoff.md", role: "worker", wantAgent: "claude",
      entryId: "entry-1", durable: true, sinceMs: 0 };
    let closes = 0;
    h.script((cmd, args) => {
      if (cmd === "list_surfaces" && args.socket === DEST)
        return { surfaces: [{ surface_id: 80, role: "worker", agent: "claude", agent_alive: true, exited: false }] };
      if (cmd === "close_surface" && ++closes === 1) return new Error(DENIED);
    });
    await h.api.awaitHandoffAck(42, source, dest, rec, key(42, SOURCE));
    expectRetained(h, source, 42, rt);
    expect(h.api.transfersInFlight.get(key(42, SOURCE)).state).toBe("awaiting-ack");
    expect(h.api.isClosingSid(42, SOURCE)).toBe(false);
    const boundary = h.calls.length;
    await h.api.transferCrossDept(42, source, dest);
    h.noSetupFaults();
    const retry = h.calls.slice(boundary).filter(c => !["render", "renderWsTabs", "setFocus"].includes(c.command));
    expect(retry.map(c => c.command)).toEqual(["list_surfaces", "read_text_head", "list_surfaces", "close_surface"]);
    expect(h.api.transfersInFlight.has(key(42, SOURCE))).toBe(false);
    expect(h.runtimes.has(key(42, SOURCE))).toBe(false);
    expect(h.runtimes.has(key(80, DEST))).toBe(true);
  });
});

describe("S6 actual batch deletion and purge", () => {
  test("workspace refusal preserves failed/unattempted panes and never calls daemon stop", async () => {
    const w = ws(1, SOURCE, [41, 42, 43]); const spare = ws(2, DEST, [80]); const h = harness([w, spare]);
    const denied = h.runtimes.get(key(42, SOURCE)); const later = h.runtimes.get(key(43, SOURCE));
    h.script((cmd, args) => cmd === "close_surface" && args.surfaceId !== 41 ? new Error(DENIED) : undefined);
    await h.workspace(w).click(); h.noSetupFaults();
    expectRetained(h, w, 42, denied); expectRetained(h, w, 43, later);
    expect(h.runtimes.has(key(41, SOURCE))).toBe(false);
    expect(h.api.collectSids(w.tree)).toEqual([42, 43]);
    expect(h.scope.workspaces).toContain(w);
    expect(h.scope.focusedSid).toBe(42);
    expect(h.calls.filter(c => c.command === "stop_dept_daemon_by_socket")).toEqual([]);
    expect(w.deleting).toBeUndefined();
    expect(h.scope.tab.attrs["aria-busy"]).toBeUndefined();
    expect(h.api.isClosingSid(42, SOURCE)).toBe(false);
    expect(h.toasts.filter(s => s.includes("S6 scripted refusal")).length).toBe(1);
    expect(h.toasts.join("\n")).toContain("삭제 의도");
  });

  test("group partial refusal preserves failed member while independent successful member finishes", async () => {
    const bad = ws(1, SOURCE, [41, 42], 9); const good = ws(2, DEST, [80], 9);
    const spare = ws(3, "/fixture/spare/cys.sock", [99]); const h = harness([bad, good, spare]);
    const rt = h.runtimes.get(key(42, SOURCE)); h.api.armGroup(9);
    h.script((cmd, args) => cmd === "close_surface" && args.surfaceId === 42 ? new Error(DENIED) : undefined);
    await h.api.confirmDeleteGroup({ id: 9, name: "group" }); h.noSetupFaults();
    expectRetained(h, bad, 42, rt);
    expect(h.api.collectSids(bad.tree)).toEqual([42]);
    expect(h.scope.workspaces).toContain(bad);
    expect(h.scope.workspaces).not.toContain(good);
    expect(h.scope.focusedSid).toBe(42);
    expect(h.calls.filter(c => c.command === "stop_dept_daemon_by_socket").map(c => c.args.socket)).toEqual([DEST]);
    expect(bad.deleting).toBeUndefined(); expect(good.deleting).toBeUndefined();
    expect(h.api.isClosingSid(42, SOURCE)).toBe(false);
    expect(h.toasts.filter(s => s.includes("S6 scripted refusal")).length).toBe(1);
    expect(h.toasts.join("\n")).toContain("삭제 의도");
  });

  test("successful pane closes followed by stop failure retain only the empty retry tab", async () => {
    const w = ws(1, SOURCE, [42]); const spare = ws(2, DEST, [80]); const h = harness([w, spare]);
    h.script(cmd => cmd === "stop_dept_daemon_by_socket" ? new Error("STOP_FAILED") : undefined);
    await h.workspace(w).click(); h.noSetupFaults();
    expect(h.runtimes.has(key(42, SOURCE))).toBe(false);
    expect(w.tree).toBeNull(); expect(w.stopFailed).toBe(true);
    expect(h.scope.workspaces).toContain(w); expect(w.deleting).toBeUndefined();
  });

  test("confirmed purge cleans UI without issuing redundant close RPC", async () => {
    const w = ws(1, SOURCE, [42]); const spare = ws(2, DEST, [80]); const h = harness([w, spare]);
    await h.api.purgeDept(w); h.noSetupFaults();
    expect(h.closeCalls()).toEqual([]);
    expect(h.runtimes.has(key(42, SOURCE))).toBe(false);
    expect(h.scope.workspaces).not.toContain(w);
    expect(h.scope.purgingDept).toBe(false);
  });

  test("purge rejection preserves pane/tab/runtime and never invokes close", async () => {
    const w = ws(1, SOURCE, [42]); const h = harness([w]); const rt = h.runtimes.get(key(42, SOURCE));
    h.script(cmd => cmd === "purge_dept_daemon_by_socket" ? new Error("PURGE_DENIED") : undefined);
    await h.api.purgeDept(w);
    expectRetained(h, w, 42, rt); expect(h.scope.workspaces).toContain(w);
    expect(h.closeCalls()).toEqual([]); expect(h.scope.purgingDept).toBe(false);
    expect(h.toasts.join("\n")).toContain("PURGE_DENIED");
  });
});

// (TICKET=cysr-1119-s11 · S12 HANDOFF §6 남은 것 ③ · H3 경계) K-2 「보기 칸에서 좌석으로 가는 입력 0」 = 「보기 칸에서 **새로 시작한** 입력 0」(S12 어긋남 7 ·
//   master 판정 = 불변식 우선). 보기 전에 사람이 시작한 전출(인계 지시 send_input · machineOrigin)은 그 좌석이 보기 칸에 열려도 끝까지 간다 —
//   이 시험은 그 경계를 못 박는다(코드 무변경 · 전출 쪽에 보기 표지 검사를 넣으면 붉어진다).
describe("cysr-1119-s11 H3 경계 — 보기 전에 시작한 전출 지시", () => {
  test("보기 전에 시작한 전출 지시는 보기 동안에도 끝까지 간다(인계 지시 send_input 1 · machineOrigin)", async () => {
    const source = ws(1, SOURCE, [42]); const dest = ws(2, DEST, []); const h = harness([source, dest]);
    const rt = h.runtimes.get(key(42, SOURCE));
    h.scope.setTimeout = (callback: () => void, ms: number) => {
      if (ms === 3000) { callback(); return 0; }
      h.timers.push({ callback, ms, cancelled: false }); return h.timers.length;
    };
    const home = deferred<string>(); const asked = deferred<null>();
    h.script((cmd, args) => {
      // cwd "/" = 루트류 → 인계 파일 자리를 홈에서 찾는다(home_dir_path) — 이 응답을 붙잡아 「전출은 시작됐고 지시는 아직」 순간을 만든다
      if (cmd === "list_surfaces" && args.socket === SOURCE)
        return { surfaces: [{ surface_id: 42, live_cwd: "/", role: "worker", agent: "claude" }] };
      if (cmd === "home_dir_path") { asked.resolve(null); return home.promise; }
      if (cmd === "list_surfaces" && args.socket === DEST) return { surfaces: [] };
      if (cmd === "send_input" && args.socket === DEST) return new Error("H3 fixture: stop after the source instruction");
    });
    const run = h.api.transferCrossDept(42, source, dest);
    await asked.promise;
    const sourceSends = () => h.calls.filter(c => c.command === "send_input" && c.args.socket === SOURCE);
    expect(sourceSends()).toEqual([]); // 전제: 보기 전에는 아직 지시가 나가지 않았다
    // 그 사이 사람이 대화 화면에서 그 좌석을 보기 칸으로 엶(대역 = 런타임 보기 표지 · openPeek 가 rt.setPeek(true) 로 켜는 값)
    rt.peek = true; h.scope.peekSid = 42;
    home.resolve("/fixture-home");
    await run; h.noSetupFaults();
    const sent = sourceSends();
    expect(sent.length).toBe(1);
    expect([sent[0].args.surfaceId, sent[0].args.clearFirst, sent[0].args.machineOrigin]).toEqual([42, true, true]);
    expect(String(sent[0].args.data)).toContain("HANDOFF_CONTRACT 5필드로 /fixture-home/.cys/transfers/transfer-42-");
    expect(rt.peek).toBe(true); // 보기 칸은 그대로 열려 있다(전출이 표지를 건드리지 않음)
  });
});
