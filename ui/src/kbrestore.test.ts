// TICKET=cysr-tabs-codex-fix-r3 — render 키보드 되돌림(codex 2R #4 · 3R blocking 1 · 3R 조건 ⑷)의 main.ts 본문을 그대로 떼어 실행한다(b230scroll.test.ts 관례).
//
// ★무엇을 지키는가:
//   ① paneHoldingKeyboard 는 **그 좌석의 xterm 입력칸(term.textarea)** 을 쥐었을 때만 좌석을 기억한다 — 좌석 안 다른 칸(이름 변경 중인 제목 등)은
//      기억하지 않는다(기억하면 render 뒤 setFocus 가 터미널로 옮겨 이름 글자·Enter 가 에이전트 입력으로 샌다 · 3R blocking 1).
//   ② restoreKeyboardAfterRender 조건 ⑷ — 떼기 전 키보드 좌석(held=A)과 포커스 표시 좌석(focusedSid=B)이 다르면 되돌리지 않는다
//      (A 로 되돌리면 표시 B·키보드 A 로 갈라진다 · 3R 「제거하지 말고 직접 단위 시험」 · 뮤턴트 M2 가 살아남던 구멍).
//   ③ render 는 좌석 이름 편집 중이면 아무것도 떼지 않고 미룬다 · 확정 처리기의 flushHeldRender 가 미룬 1회를 (사람 손이었으면 사람 손으로) 그린다.
// ★한계: 대역 DOM 위의 배선이다 — 실제 브라우저에서 이름 글자가 터미널로 0 인지는 focus_gate ⑭ 가 판정한다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

declare const Bun: { Transpiler: new (o: { loader: "ts" }) => { transformSync(code: string): string } };

const SRC = readFileSync(new URL("./main.ts", import.meta.url), "utf-8");
const tr = new Bun.Transpiler({ loader: "ts" });

function fnText(name: string): string {
  const m = new RegExp(`^function ${name}\\(`, "m").exec(SRC);
  expect({ 함수: name, 존재: m !== null }).toEqual({ 함수: name, 존재: true });
  const a = (m as RegExpExecArray).index;
  const b = SRC.indexOf("\n}\n", a);
  expect({ 함수: name, 끝: b > a }).toEqual({ 함수: name, 끝: true });
  return SRC.slice(a, b + 2);
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyFn = (...a: any[]) => any;
function loadWith(code: string, ret: string, scope: Record<string, unknown>): AnyFn {
  const js = tr.transformSync(code);
  return new Function("__scope", `with (__scope) {\n${js}\nreturn ${ret};\n}`)(scope) as AnyFn;
}

const BODY = { tagName: "BODY" };
interface FakeRt { sid: number; socket: string; el: { isConnected: boolean; contains: (n: unknown) => boolean }; term: { textarea: unknown }; titleEl: { isContentEditable: boolean } }
function fakeRt(sid: number): FakeRt {
  const textarea = { tagName: "TEXTAREA", sid };
  const titleEl = { tagName: "SPAN", isContentEditable: false, sid };
  const el = { isConnected: true, contains: (n: unknown) => n === textarea || n === titleEl };
  return { sid, socket: "s", el, term: { textarea }, titleEl };
}
function world(o: { active: unknown; focusedSid: number | null; attached?: number[]; modal?: boolean }) {
  const A = fakeRt(4), B = fakeRt(6);
  const panes = new Map<string, FakeRt>([["s#4", A], ["s#6", B]]);
  const focusCalls: number[] = [];
  const attached = new Set(o.attached ?? [4, 6]);
  const doc = { body: BODY, activeElement: o.active, getElementById: () => null };
  const scope: Record<string, unknown> = {
    document: doc,
    panes,
    paneKey: (sid: number, sock?: string) => `${sock ?? ""}#${sid}`,
    root: { contains: (el: unknown) => [...panes.values()].some((rt) => rt.el === el && attached.has(rt.sid)) },
    modalLayerOpen: () => !!o.modal,
    focusedSid: o.focusedSid,
    current: () => ({ socket: "s" }),
    setFocus: (sid: number) => void focusCalls.push(sid),
  };
  const holding = loadWith(fnText("paneHoldingKeyboard"), "paneHoldingKeyboard", scope);
  const restore = loadWith(fnText("restoreKeyboardAfterRender"), "restoreKeyboardAfterRender", scope);
  return { A, B, doc, holding, restore, focusCalls };
}

describe("① paneHoldingKeyboard — xterm 입력칸일 때만 좌석을 기억한다(3R blocking 1)", () => {
  it("좌석 A 의 xterm 입력칸 = A", () => {
    const w = world({ active: null, focusedSid: 4 });
    w.doc.activeElement = w.A.term.textarea;
    expect(w.holding()).toBe(w.A);
  });
  it("좌석 A 안이지만 이름 변경 중인 제목 칸 = 기억하지 않음(null)", () => {
    const w = world({ active: null, focusedSid: 4 });
    w.A.titleEl.isContentEditable = true;
    w.doc.activeElement = w.A.titleEl;
    expect(w.A.el.contains(w.A.titleEl)).toBe(true); // 좌석 안 요소임은 맞다 — 옛 판(rt.el.contains)은 여기서 A 를 돌려줬다
    expect(w.holding()).toBeNull();
  });
  it("BODY·없음 = null", () => {
    expect(world({ active: BODY, focusedSid: 4 }).holding()).toBeNull();
    expect(world({ active: null, focusedSid: 4 }).holding()).toBeNull();
  });
});

describe("② restoreKeyboardAfterRender 조건 ⑷ — held=A · focused=B 면 되돌리지 않는다(3R 조건 ⑷ · 뮤턴트 M2)", () => {
  it("held=A · focused=A · 둘 다 화면 · BODY = setFocus(A) 1회(대조 — 빈 통과 아님)", () => {
    const w = world({ active: BODY, focusedSid: 4 });
    w.restore(w.A);
    expect(w.focusCalls).toEqual([4]);
  });
  it("held=A · focused=B · A 도 계속 화면 · BODY = setFocus 0(키보드 A·표시 B 로 갈라지지 않는다)", () => {
    const w = world({ active: BODY, focusedSid: 6 });
    w.restore(w.A);
    expect(w.focusCalls).toEqual([]);
  });
  it("held=A 가 숨음(#root 밖) = 0 · 그사이 다른 칸이 포커스를 받음 = 0 · 모달 = 0", () => {
    const hidden = world({ active: BODY, focusedSid: 4, attached: [6] });
    hidden.restore(hidden.A);
    expect(hidden.focusCalls).toEqual([]);
    const other = world({ active: { tagName: "INPUT" }, focusedSid: 4 });
    other.restore(other.A);
    expect(other.focusCalls).toEqual([]);
    const modal = world({ active: BODY, focusedSid: 4, modal: true });
    modal.restore(modal.A);
    expect(modal.focusCalls).toEqual([]);
  });
});

describe("③ render — 좌석 이름 편집 중이면 떼지 않고 미룬다 · flushHeldRender 가 1회(3R blocking 1)", () => {
  function renderWorld(editing: boolean, viewByUser: boolean) {
    const log: string[] = [];
    const scope: Record<string, unknown> = {
      paneTitleEditing: () => editing,
      renderHeld: "no",
      viewByUser,
      paneHoldingKeyboard: () => { log.push("paneHoldingKeyboard"); return null; },
      panes: new Map(),
      root: { set innerHTML(_v: string) { log.push("root.clear"); } },
      current: () => { log.push("current"); return null; },
      wsViewTree: () => null,
      renderWsTabs: () => log.push("renderWsTabs"), deferredRuntimes: new Map<string, unknown>(), workRuntimeWanted: () => true, ensureSeatRuntimes: async () => {}, // (cysr-1116-s2) render 의 미룬 런타임 줄 — 빈 장부 = 무동작
      restoreKeyboardAfterRender: () => log.push("restore"),
      collectSids: () => [],
      requestAnimationFrame: () => {},
      saveLayout: () => log.push("saveLayout"),
    };
    const render = loadWith(fnText("render"), "render", scope);
    return { scope, render, log };
  }
  it("편집 중 + 사람 손 아님 = 아무것도 떼지 않음 · 미룸 표시 auto", () => {
    const w = renderWorld(true, false);
    w.render();
    expect(w.log).toEqual([]);
    expect(w.scope.renderHeld).toBe("auto");
  });
  it("편집 중 + 사람 손 = 미룸 표시 user(나중 auto 가 덮지 않음)", () => {
    const w = renderWorld(true, true);
    w.render();
    w.scope.viewByUser = false;
    w.render();
    expect(w.log).toEqual([]);
    expect(w.scope.renderHeld).toBe("user");
  });
  it("편집 아님 = 평소대로 그린다(대조)", () => {
    const w = renderWorld(false, false);
    w.render();
    expect(w.log).toContain("root.clear");
    expect(w.scope.renderHeld).toBe("no");
  });
  it("(ChatGPT F5) 편집 없이 정상으로 그리면 밀린 표식을 소비한다 — user 면 사람 손으로 다시 그리고 끝 · auto 면 그대로 그린다", () => {
    for (const held of ["user", "auto"] as const) {
      const w = renderWorld(false, false);
      const calls: string[] = [];
      w.scope.renderHeld = held;
      w.scope.renderByUser = () => calls.push("renderByUser");
      w.render();
      expect({ held, after: w.scope.renderHeld, calls, drew: w.log.includes("root.clear") })
        .toEqual({ held, after: "no", calls: held === "user" ? ["renderByUser"] : [], drew: held === "auto" });
    }
  });
  it("flushHeldRender — auto = render 1회 · user = renderByUser 1회 · no = 0 · 표시는 no 로", () => {
    for (const [held, want] of [["auto", ["render"]], ["user", ["renderByUser"]], ["no", []]] as const) {
      const calls: string[] = [];
      const scope: Record<string, unknown> = { renderHeld: held, render: () => calls.push("render"), renderByUser: () => calls.push("renderByUser") };
      loadWith(fnText("flushHeldRender"), "flushHeldRender", scope)();
      expect({ held, calls }).toEqual({ held, calls: [...want] });
      expect(scope.renderHeld).toBe("no");
    }
  });
  it("배선 — 좌석 제목 확정 처리기가 contentEditable 을 끈 바로 뒤 flushHeldRender 를 부른다", () => {
    const i = SRC.indexOf('titleEl.contentEditable = "false";\n            flushHeldRender();');
    expect(i).toBeGreaterThan(-1);
  });
});
