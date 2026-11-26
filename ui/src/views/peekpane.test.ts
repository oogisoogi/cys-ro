// (TICKET=cysr-1119-s12 · DESIGN §4-3 ⑤ K-2) 보기 칸 읽기 전용 — **실제 makePane 본문**을 떼어 돌린다(makepane.test.ts 와 같은 Proxy 대역 로더).
//   ① 표지 꺼짐(종전) = 사람 키·Shift+Enter·한글 입력이 send_input 으로 가는 바이트·인자가 고침 전 꼴 그대로({ socket, surfaceId, data } · machineOrigin 없음)
//   ② 표지 켬 = 같은 입력 전부 send_input 0 · 막은 수 = 시도 수 · 키 처리기 false · disableStdin · 글칸 tabindex -1 + blur
//   ③ 표지 끔 = 되살아남(send_input 1 · 같은 바이트) · tabindex 되돌림
//   ④ 보기 칸이 만든 런타임 = 처음부터 표지 켬 · 처음 크기 = 받은 PTY 크기(120×35 아님)
//   ⑤ makePane 안 send_input 호출 = sendRaw 한 곳뿐(휠 번역·붙여넣기·IME 우회 모두 sendRaw 를 지난다 — 그 밖의 배출구 0)
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { PEEK_AUTOREPLY_PASS, peekPasses } from "../peek";
import { imeStep, initialImeState, isHangulText } from "../ime";

declare const Bun: { Transpiler: new (o: { loader: "ts" }) => { transformSync(code: string): string } };
const SRC = readFileSync(new URL("../main.ts", import.meta.url), "utf8");
function fnText(name: string): string {
  const m = new RegExp(`^(?:async )?function ${name}\\(`, "m").exec(SRC);
  expect({ 함수: name, 존재: m !== null }).toEqual({ 함수: name, 존재: true });
  const a = (m as RegExpExecArray).index;
  return SRC.slice(a, SRC.indexOf("\n}\n", a) + 2);
}

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
const loose = (t: Record<string | symbol, unknown>) =>
  new Proxy(t, {
    get: (o, p) => (p === "then" ? undefined : p in o ? o[p] : STUB),
    set: (o, p, v) => ((o[p] = v), true),
  });

type H = (...a: unknown[]) => unknown;
function harness(o: { holdFirstSend?: boolean } = {}) {
  let release = () => {};
  let held = !o.holdFirstSend;
  const invokes: [string, Record<string, unknown>][] = [];
  const drops: string[] = [];
  const gone: string[] = [];
  const terms: Record<string, unknown>[] = [];
  const panes = new Map<string, unknown>();
  const taListeners: Record<string, H[]> = {};
  const document = { createElement: () => loose({ dataset: {}, style: {}, querySelector: () => null, addEventListener: () => {} }) };
  const scope: Record<string, unknown> = {
    PANE_STREAM_UNWANTED: "pane_stream_unwanted",
    PANE_STALE: "pane_stale",
    panes,
    paneGen: new Map<string, number>(),
    paneKey: (sid: number, socket?: string) => `${socket ?? ""}#${sid}`,
    document,
    navigator: { userAgent: "Mozilla/5.0 (Macintosh) AppleWebKit/605.1.15 (KHTML, like Gecko)" }, // WKWebView = 한글 입력 우회 배선이 붙는다
    localStorage: { getItem: () => null },
    peekPasses, // 실물 판정
    PEEK_AUTOREPLY_PASS, // 실물 갈래 상수(기본 false = xterm 입력 끔)
    imeStep, initialImeState, isHangulText, // 실물 한글 입력 리듀서(조합 확정 = sendRaw)
    notePeekDrop: (k: string) => void drops.push(k),
    peekSeatGone: (k: string) => void gone.push(k),
    Terminal: function (opts: Record<string, unknown>) {
      const attrs: Record<string, string> = {};
      const ta = loose({
        blurred: 0,
        value: "",
        addEventListener: (t: string, f: H) => void (taListeners[t] ??= []).push(f),
        getAttribute: (k: string) => (k in attrs ? attrs[k] : null),
        setAttribute: (k: string, v: string) => void (attrs[k] = v),
        removeAttribute: (k: string) => void delete attrs[k],
        blur() {
          (this as { blurred: number }).blurred++;
        },
        parentElement: null,
        attrs,
      });
      const t = loose({ ctor: opts, options: { ...opts }, textarea: ta, rows: opts.rows, cols: opts.cols, onDataFn: null as H | null, keyFn: null as H | null });
      t.onData = (f: H) => void (t.onDataFn = f);
      t.attachCustomKeyEventHandler = (f: H) => void (t.keyFn = f);
      terms.push(t);
      return t;
    },
    invoke: async (cmd: string, a: Record<string, unknown>) => {
      invokes.push([cmd, a]);
      if (cmd === "send_input" && !held) {
        held = true; // 첫 send_input 응답만 붙잡는다(뒤 글자는 sendChain 에 줄 선다)
        await new Promise<void>((r) => (release = r));
      }
      if (cmd === "attach_surface") return { output_event: "out", exited_event: "exit" };
      if (cmd === "start_surface_stream") return { stream_gen: 1 };
      return false; // app_mouse_enabled 등 = 꺼짐
    },
    listen: async () => () => {},
    ResizeObserver: function () {
      return { observe() {}, disconnect() {} };
    },
    window: loose({ setTimeout: () => 1 }),
    routeOnData: (data: string) => ({ action: "send", data }), // 종전 경로 그대로 통과(판정 함수는 onDataRoute 시험이 지킨다)
  };
  const tr = new Bun.Transpiler({ loader: "ts" });
  const code = tr.transformSync(fnText("makePane"));
  const real = new Set(Object.keys(scope));
  const env = new Proxy(scope, {
    has: (_t, p) => typeof p === "string" && (real.has(p) || !(p in globalThis)),
    get: (t, p) => (typeof p === "string" && real.has(p) ? t[p] : p === Symbol.unscopables ? undefined : STUB),
    set: (t, p, v) => ((t[p as string] = v), true),
  });
  const makePane = new Function("__scope", `with (__scope) {\n${code}\nreturn makePane;\n}`)(env) as (sid: number, title: string, socket?: string, opts?: unknown) => Promise<Record<string, unknown>>;
  const sends = () => invokes.filter((x) => x[0] === "send_input").map((x) => x[1]);
  const fire = async (t: Record<string, unknown>) => {
    // 사람 입력 세 길 — onData(자판) · Shift+Enter(키 처리기 직송) · 한글 입력(WKWebView input 우회)
    const keyFn = t.keyFn as H;
    (t.onDataFn as H)("a");
    const shiftEnter = keyFn({ type: "keydown", key: "Enter", shiftKey: true, altKey: false, ctrlKey: false, metaKey: false, keyCode: 13, isComposing: false });
    for (const f of taListeners["input"] ?? []) f({ inputType: "insertText", data: "가" });
    for (const f of taListeners["blur"] ?? []) f({}); // 조합 확정(자모 pending → 보냄)
    const plainKey = keyFn({ type: "keydown", key: "x", shiftKey: false, altKey: false, ctrlKey: false, metaKey: false, keyCode: 88, isComposing: false });
    for (let i = 0; i < 30; i++) await Promise.resolve();
    return { shiftEnter, plainKey };
  };
  return { makePane, invokes, sends, drops, gone, terms, fire, taListeners, release: () => release() };
}

describe("보기 칸 읽기 전용 — 실제 makePane(K-2 배출구 · DESIGN §4-3 ⑤)", () => {
  it("① 표지 꺼짐 = 종전 바이트·인자 그대로(사람 실키 = machineOrigin 없음)", async () => {
    const h = harness();
    const rt = await h.makePane(5, "t");
    expect(rt.peek).toBe(false);
    const r = await h.fire(h.terms[0]);
    expect(r).toEqual({ shiftEnter: false, plainKey: true }); // Shift+Enter 는 직송 뒤 xterm 기본 처리 막음(종전) · 보통 키 = xterm 처리
    const sent = h.sends();
    expect(sent.map((a) => a.data)).toEqual(["a", "\x1b\r", "가"]);
    for (const a of sent) expect(Object.keys(a).sort()).toEqual(["data", "socket", "surfaceId"]);
    expect(sent.every((a) => a.surfaceId === 5 && a.socket === undefined)).toBe(true);
    expect(h.drops).toEqual([]);
  });

  it("② 표지 켬 = send_input 0 · 막은 수 = 시도 수 · 키 처리기 false · disableStdin · tabindex -1 + blur", async () => {
    const h = harness();
    const rt = await h.makePane(5, "t");
    const t = h.terms[0] as { options: Record<string, unknown>; textarea: { attrs: Record<string, string>; blurred: number } };
    (rt.setPeek as (v: boolean) => void)(true);
    expect(rt.peek).toBe(true);
    expect(t.options.disableStdin).toBe(true);
    expect(t.textarea.attrs.tabindex).toBe("-1");
    expect(t.textarea.blurred).toBe(1);
    const r = await h.fire(h.terms[0]);
    expect(r).toEqual({ shiftEnter: false, plainKey: false }); // 키가 xterm 처리기 안까지 오지 않는다
    expect(h.sends()).toEqual([]);
    expect(h.drops).toEqual(["send", "send"]); // onData · 한글 입력(Shift+Enter 는 키 처리기 첫 줄에서 먼저 막혀 sendRaw 까지 오지 않음)
  });

  it("③ 표지 끔 = 되살아남 · 같은 바이트 · tabindex 되돌림(원래 없음 = 지움)", async () => {
    const h = harness();
    const rt = await h.makePane(5, "t");
    const t = h.terms[0] as { options: Record<string, unknown>; textarea: { attrs: Record<string, string> } };
    const setPeek = rt.setPeek as (v: boolean) => void;
    setPeek(true);
    setPeek(false);
    expect([rt.peek, t.options.disableStdin, "tabindex" in t.textarea.attrs]).toEqual([false, false, false]);
    await h.fire(h.terms[0]);
    expect(h.sends().map((a) => a.data)).toEqual(["a", "\x1b\r", "가"]);
  });

  it("④ 보기 칸이 만든 런타임 = 처음부터 표지 켬 · 처음 크기 = 그 좌석 PTY 크기", async () => {
    const h = harness();
    const rt = await h.makePane(7, "t", undefined, { peek: true, size: { rows: 41, cols: 97 } });
    const t = h.terms[0] as { ctor: Record<string, unknown>; options: Record<string, unknown> };
    expect([t.ctor.cols, t.ctor.rows]).toEqual([97, 41]);
    expect([rt.peek, t.options.disableStdin]).toEqual([true, true]);
    await h.fire(h.terms[0]);
    expect(h.sends()).toEqual([]);
    expect(h.invokes.some((x) => x[0] === "resize_surface")).toBe(false);
    // 대조: 인자 없음 = 종전 120×35
    const h2 = harness();
    await h2.makePane(8, "t");
    const t2 = h2.terms[0] as { ctor: Record<string, unknown> };
    expect([t2.ctor.cols, t2.ctor.rows]).toEqual([120, 35]);
  });

  // (검증 H2·H3 · master#d470f594 판정 = 불변식 우선) 읽기 전용 약속 = 「보기 칸에서 **새로 시작한** 입력 0」 — 보기 전에 사람이 시작한 전송(줄 선 글자)은
  //   끝까지 그 좌석으로 간다(focus_gate ⑬ 「줄 선 글자 = 끝까지 이 좌석 · 유실 0」 · 발사 때 버리면 친 글이 조용히 사라진다).
  it("⑥ 경계 ㉠ 보기 「전」 에 시작한 글 = 보기가 열린 뒤에도 끝까지 전달(줄 선 글자 유실 0)", async () => {
    const h = harness({ holdFirstSend: true });
    const rt = await h.makePane(5, "t");
    const onData = (h.terms[0] as { onDataFn: H }).onDataFn;
    onData("a"); // 발사됨 · 응답 붙잡힘
    onData("b"); // 줄 섬
    for (let i = 0; i < 10; i++) await Promise.resolve();
    (rt.setPeek as (v: boolean) => void)(true); // 그 사이 보기 칸이 열림
    h.release();
    for (let i = 0; i < 30; i++) await Promise.resolve();
    expect(h.sends().map((a) => a.data)).toEqual(["a", "b"]);
    expect(h.drops).toEqual([]);
  });
  it("⑦ 경계 ㉡ 보기 칸에서 「새로」 시작한 글 = 0(줄 선 글자가 있어도 그 뒤 새 입력은 줄에 못 섬)", async () => {
    const h = harness({ holdFirstSend: true });
    const rt = await h.makePane(5, "t");
    const onData = (h.terms[0] as { onDataFn: H }).onDataFn;
    onData("a");
    for (let i = 0; i < 10; i++) await Promise.resolve();
    (rt.setPeek as (v: boolean) => void)(true);
    onData("c"); // 보기 칸이 열린 뒤 새로 시작
    h.release();
    for (let i = 0; i < 30; i++) await Promise.resolve();
    expect(h.sends().map((a) => a.data)).toEqual(["a"]);
    expect(h.drops).toEqual(["send"]);
  });

  it("⑤ makePane 안 send_input 호출 = sendRaw 한 곳뿐 · 그 밖의 배출구 0 · 키·IME·휠 번역 세 자리 = sendRaw 경유", () => {
    // (1.1.20 #46 · S12 L4) 이름을 단언에 맞춤 — 붙여넣기는 이 원천 검사가 재지 않는다(xterm paste = onData 길 · 행동 = ② · 「처음 크기 = PTY 크기」 는 ④ 97×41).
    const body = fnText("makePane").split("\n").filter((l) => !l.trim().startsWith("//")).join("\n"); // 주석 줄 제외(설명 글의 invoke 낱말)
    expect(body.split('invoke("send_input"').length - 1).toBe(1);
    const s = body.indexOf("const sendRaw = (data: string) => {");
    const e = body.indexOf("\n  };\n", s);
    const at = body.indexOf('invoke("send_input"');
    expect(s > 0 && s < at && at < e).toBe(true);
    for (const k of ["sendRaw(act.data)", 'sendRaw("\\x1b\\r")', 'if ("send" in a) sendRaw(a.send);']) expect({ k, has: body.includes(k) }).toEqual({ k, has: true });
    // 파기 훅 = destroyPaneRuntime 이 부르는 unlisten 에 실림
    expect(body).toContain("unlisten: [cancelSendFail, peekGone, un1 as () => void, un2 as () => void]");
  });
});
