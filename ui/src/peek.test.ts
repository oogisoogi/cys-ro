// (TICKET=cysr-1119-s12 · DESIGN §4-3 CV-PEEK) 순수 판정 시험 — 배율 k(K-3) · 자동 응답 허용 목록(⑥ P0-PEEK-c 갈래) · 배출구 통과 판정(K-2 ⑴).
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { isAutoReply, PEEK_AUTOREPLY_PASS, PEEK_ENABLED, PEEK_HISTORY_REPLAY, PEEK_MIN_FONT_PX, PEEK_SCALE, PEEK_WIDE_MIN_PX, peekPasses, peekScale } from "./peek";

describe("peekScale — k = min(1, 칸 폭 / termHost 폭) · 11px 바닥 · k 가드", () => {
  it("칸이 넓으면 k = 1(배율 0) · 좁으면 비율", () => {
    expect(peekScale(1000, 800, 14)).toEqual({ k: 1, scroll: false, ok: true });
    const r = peekScale(600, 1000, 20);
    expect(r.k).toBeCloseTo(0.6, 6);
    expect([r.scroll, r.ok]).toEqual([false, true]);
  });
  it("글자가 11px 아래로 작아지면 k = 11 / fontSize 에서 멈추고 가로 스크롤", () => {
    const r = peekScale(300, 1000, 14); // 14 × 0.3 = 4.2px < 11
    expect(r.k).toBeCloseTo(PEEK_MIN_FONT_PX / 14, 6);
    expect([r.scroll, r.ok]).toEqual([true, true]);
    expect(14 * r.k).toBeCloseTo(11, 6);
  });
  it("글자가 원래 11px 이하면 줄이지 않는다(k ≤ 1)", () => {
    const r = peekScale(300, 1000, 10);
    expect(r.k).toBe(1);
    expect(r.scroll).toBe(true);
  });
  it("가드 — 폭 0·NaN·∞·음수 = 배율을 걸지 않음(k = 1) + 가로 스크롤 + 다시 잼(ok=false)", () => {
    for (const [inner, host] of [[600, 0], [600, NaN], [600, Infinity], [0, 800], [NaN, 800], [-5, 800], [600, -1]] as const) {
      expect({ inner, host, r: peekScale(inner, host, 14) }).toEqual({ inner, host, r: { k: 1, scroll: true, ok: false } });
    }
  });
  it("fontSize 를 모르면(0·NaN) 바닥 없이 비율만 — 그래도 유한 양수", () => {
    for (const fs of [0, NaN]) {
      const r = peekScale(400, 800, fs);
      expect(r.k).toBeCloseTo(0.5, 6);
      expect(r.ok).toBe(true);
    }
  });
  it("배율 끔(P0-PEEK-a 갈래) = k 1 · 넘치면 가로 스크롤만", () => {
    expect(peekScale(600, 1000, 14, false)).toEqual({ k: 1, scroll: true, ok: true });
    expect(peekScale(1200, 1000, 14, false)).toEqual({ k: 1, scroll: false, ok: true });
  });
});

describe("자동 응답 허용 목록(DESIGN §4-3 ⑥ · P0-PEEK-c 갈래) — 정확 꼴만", () => {
  const allow = ["\x1b[?1;2c", "\x1b[?62;22c", "\x1b[>0;276;0c", "\x1b[?c", "\x1b[12;40R", "\x1b[1;1R", "\x1b[I", "\x1b[O",
    "\x1b[?12;40R", "\x1b[0n", "\x1b[?2004;1$y", "\x1b[4;2$y", "\x1b]11;rgb:1e1e/1e1e/1e1e\x1b\\", "\x1b]4;1;rgb:ff/00/00\x07", "\x1b[8;35;120t", "\x1b[4;700;1200t", "\x1b[6;17;8t", "\x1bP1$r0m\x1b\\", "\x1bP0$r\x1b\\"]; // 검증 M6 · 고침2 ⑤ DECRQSS · xterm 5.5.0 자기 응답
  const deny = [
    "\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D", "\x1bOA", "\x1bOB", "\x1bOC", "\x1bOD", // 방향키
    "\x1b[5~", "\x1b[6~", // PageUp/Down
    "\x1b[M !!", "\x1b[<0;10;5M", "\x1b[<64;3;3m", // 마우스
    "a", "\r", "\x1b\r", "y\r", "\x03", // 사람 키
    "\x1b[?1;2cX", "x\x1b[I", "\x1b[12;40R\r", "\x1b[12R", "\x1b[c", // 꼴 밖(앞뒤 덧붙음 · 자리 모자람)
    "\x1b[1n", "\x1b]11;rgb:zz/00/00\x07", "\x1b]52;c;aGk=\x07", "\x1b[9;1;1t", "\x1b[200~x", "\x1bP1$r0m", "\x1bP2$r\x1b\\", "\x1bP1$rA\x1bB\x1b\\", // 꼴 밖(다른 상태값 · 클립보드 OSC 52 · 붙여넣기 괄호)
  ];
  it("허용 꼴 전수 = 참", () => {
    for (const d of allow) expect({ d: JSON.stringify(d), ok: isAutoReply(d) }).toEqual({ d: JSON.stringify(d), ok: true });
  });
  it("방향키·PageUp/Down·마우스·사람 키·덧붙은 꼴 = 거짓", () => {
    for (const d of deny) expect({ d: JSON.stringify(d), ok: isAutoReply(d) }).toEqual({ d: JSON.stringify(d), ok: false });
  });
});

describe("peekPasses — 배출구 통과 판정(K-2 ⑴)", () => {
  it("보기 칸이 아니면 모든 글이 지난다(종전 그대로 · 바이트 판정 0)", () => {
    for (const d of ["a", "\x1b[A", "\x1b\r", "\x1b[?1;2c", "", "한글"]) expect(peekPasses(false, d)).toBe(true);
  });
  it("보기 칸 · 자동 응답 끔(기본) = 전부 버림", () => {
    for (const d of ["a", "\x1b[A", "\x1b\r", "\x1b[?1;2c", "\x1b[I", "한글"]) expect(peekPasses(true, d)).toBe(false);
  });
  it("보기 칸 · 자동 응답 켬 = 정확 꼴 자동 응답만", () => {
    expect(peekPasses(true, "\x1b[?1;2c", true)).toBe(true);
    expect(peekPasses(true, "\x1b[12;40R", true)).toBe(true);
    expect(peekPasses(true, "\x1b[I", true)).toBe(true);
    for (const d of ["a", "\x1b[A", "\x1b[5~", "\x1b[<0;1;1M", "\r"]) expect(peekPasses(true, d, true)).toBe(false);
  });
});

describe("갈래 상수(P0 전 기본값) · CSS 문턱 맞물림", () => {
  it("기본값 = 켬 · 배율 켬 · 기록 이어 붙이기 켬 · 자동 응답 버림", () => {
    expect([PEEK_ENABLED, PEEK_SCALE, PEEK_HISTORY_REPLAY, PEEK_AUTOREPLY_PASS]).toEqual([true, true, true, false]);
  });
  it("(master#048a4917) 문턱 1410 — 오른쪽 칸이 되는 모든 창 폭에서 대화 칸 ≥ 600px(CSS 의 rail 폭·45%·480px 를 읽어 계산)", () => {
    expect(PEEK_WIDE_MIN_PX).toBe(1410);
    const css = readFileSync(new URL("./views/views.css", import.meta.url), "utf8");
    const m = /max\(calc\(\(100% - (\d+)px\) \* ([0-9.]+)\), (\d+)px\)/.exec(css);
    expect(m !== null).toBe(true);
    const [rail, pct, floor] = [Number(m![1]), Number(m![2]), Number(m![3])];
    const chat = (w: number) => w - rail - Math.max((w - rail) * pct, floor);
    const bad: number[] = [];
    for (let w = PEEK_WIDE_MIN_PX + 1; w <= 3840; w++) if (chat(w) < 600) bad.push(w);
    expect(bad).toEqual([]);
    expect(chat(PEEK_WIDE_MIN_PX) < 600).toBe(true); // 문턱 바로 아래(1410)는 오른쪽 칸이면 599.5 — 그래서 덮개
  });
  it("views.css 오른쪽 칸/덮개 문턱 = PEEK_WIDE_MIN_PX", () => {
    const css = readFileSync(new URL("./views/views.css", import.meta.url), "utf8");
    expect(css).toContain(`@media (min-width: ${PEEK_WIDE_MIN_PX + 1}px) { .cv-wrap > .cv-peek`);
    expect(css).toContain(`@media (max-width: ${PEEK_WIDE_MIN_PX}px) {\n  .cv-wrap { position: relative; }\n  .cv-wrap > .cv-peek`);
  });
});

describe("main.ts 원천 검사 — 배출구·문의 자리(K-2 · K-3)", () => {
  const SRC = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  const after = (head: string, n = 160) => {
    const i = SRC.indexOf(head);
    expect({ head, found: i >= 0 }).toEqual({ head, found: true });
    return SRC.slice(i + head.length, i + head.length + n);
  };
  it("sendRaw 첫 줄 = peekPasses 문(그 뒤에 종전 몸통 그대로)", () => {
    expect(after("const sendRaw = (data: string) => {\n").startsWith('    if (!peekPasses(peek, data)) return void notePeekDrop("send"), Promise.resolve();\n    follow = true;')).toBe(true);
  });
  it("xterm 키 처리기 첫 줄 = 보기 칸이면 false", () => {
    expect(after("term.attachCustomKeyEventHandler((e) => {\n").startsWith("    if (peek) return false;")).toBe(true);
  });
  it("injectRawToPane 첫 줄 · fitPane 첫 줄 · setFocus 첫 줄", () => {
    expect(after("async function injectRawToPane(rt: PaneRuntime, data: string) {\n", 400).startsWith("  if (rt.peek) {")).toBe(true);
    expect(after("async function injectRawToPane(rt: PaneRuntime, data: string) {\n", 400)).toContain('notePeekDrop("inject");\n    return toast("watchdog", "삽입 안 함"'); // 검증 M3 — 조용히 버리지 않음
    expect(after("function fitPane(rt: PaneRuntime) {\n").startsWith("  if (rt.peek) return;")).toBe(true);
    expect(after("function setFocus(sid: number) {\n").startsWith("  if (peekSid === sid) return;")).toBe(true);
  });
  it("paneAtPointStrict 는 보기 칸 좌석을 돌려주지 않는다 · 전역 keydown 은 IME 검사 바로 뒤에서 보기 칸 문", () => {
    expect(SRC).toContain("for (const rt of panes.values()) if (rt.el === paneEl) return rt.peek ? undefined : rt;");
    expect(after('window.addEventListener("keydown", (e) => {\n  if (e.isComposing || e.keyCode === 229) return; // IME 조합 중 무시\n', 400)).toContain('  if (peekOpen()) {\n    if (e.key === "Escape") closePeek("esc");');
  });
  it("표지를 바꾸는 곳 = setPeek 하나(peek = 대입은 makePane 안 두 곳: 선언 · setPeek)", () => {
    const mp = SRC.slice(SRC.indexOf("async function makePane("), SRC.indexOf("\n}\n", SRC.indexOf("async function makePane(")));
    expect((mp.match(/\bpeek = /g) ?? []).length).toBe(2);
    expect(mp).toContain("let peek = opts?.peek === true;");
    expect(mp).toContain("    peek = v;\n");
    expect(mp).toContain("    term.options.disableStdin = v && !PEEK_AUTOREPLY_PASS;"); // 자동 응답 통과 갈래면 xterm 입력을 끄지 않는다(끄면 자동 응답도 안 나온다)
    expect((SRC.match(/\.setPeek\(/g) ?? []).length).toBe(4); // openPeek 켬 · 작업 화면으로 넘김 끔 · closePeek 끔 · peekTick 남은 표지 끔
  });
  it("xterm 글자 크기 옵션을 보기 칸이 건드리지 않는다(K-3) — 보기 칸 코드에 fontSize 쓰기 0", () => {
    const a = SRC.indexOf("// ---------- (TICKET=cysr-1119-s12 · DESIGN §4-3 CV-PEEK 고침판)");
    const b = SRC.indexOf("function setFocus(sid: number) {");
    const peekCode = SRC.slice(a, b);
    expect(a > 0 && b > a).toBe(true);
    expect({ fontSet: /options\.fontSize\s*=/.test(peekCode), resize: peekCode.includes('invoke("resize_surface"'), fit: peekCode.includes("fit.fit(") }).toEqual({ fontSet: false, resize: false, fit: false });
  });
});
