// TICKET=cysr-1119-s7 SEL(+W2) · W5 · W6 · BA5 — 선택 표시 한 곳 · 대비 계산 · 배선 원천 검사 (bun test · 의존성 0).
// 설계 = review/1119-DESIGN.md §5 SEL · §6 W5/W6 · §7 BA5. DOM 동작(클릭 → 표시)은 e2e ui/e2e/selection_gate.py 가 본다.
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { buildSeatRows, type SeatInput } from "./seatrows";
import { seatRowSelected, seatRowsSignature, seatRowTitle } from "./seatrowsdom";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const css = readFileSync(new URL("./views/views.css", import.meta.url), "utf8");
const tabbar = readFileSync(new URL("./tabbar.ts", import.meta.url), "utf8");

/** WCAG 2.x 상대 휘도 대비. */
function contrast(a: string, b: string): number {
  const lum = (h: string) => {
    const c = [0, 2, 4].map((i) => parseInt(h.slice(1 + i, 3 + i), 16) / 255).map((x) => (x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}
const r2 = (n: number) => Math.round(n * 100) / 100;

describe("SEL-1 상태 한 곳 — focusedSid 쓰기는 setFocusedSid 안의 한 줄뿐", () => {
  test("`focusedSid =` 대입(비교 제외)이 정확히 1곳이고 그 곳이 setFocusedSid 본문", () => {
    const writes = [...main.matchAll(/\bfocusedSid\s*=(?!=)/g)].map((m) => m.index!);
    const decl = main.indexOf("let focusedSid: number | null = null;");
    const others = writes.filter((i) => i !== decl + "let ".length);
    expect(others.length).toBe(1);
    const fn = main.indexOf("function setFocusedSid(");
    expect(fn).toBeGreaterThan(0);
    const body = main.slice(fn, main.indexOf("\n}\n", fn));
    expect(fn < others[0] && others[0] < fn + body.length).toBe(true);
    expect(body).toContain("syncSelection(");
  });
  test("setFocus 와 예전 우회 6곳이 모두 setFocusedSid 를 부른다", () => {
    expect((main.match(/setFocusedSid\(/g) ?? []).length).toBeGreaterThanOrEqual(8); // 정의 1 + 부르는 곳 7
    const sf = main.slice(main.indexOf("function setFocus(sid: number) {"), main.indexOf("function setFocus(sid: number) {") + 200);
    expect(sf).toContain("setFocusedSid(sid)");
  });
  test("좌석 줄을 다시 그린 뒤에도 선택을 다시 붙인다(서명에 포커스를 넣지 않음)", () => {
    const fn = main.slice(main.indexOf("function refreshSeatRows(): void {"));
    expect(fn.slice(0, fn.indexOf("\n}\n"))).toContain("syncSelection(");
  });
});

describe("SEL-2 좌석 줄 — 지금 작업공간 열쇠 + sid 만(C-09 · 부서마다 번호 겹침)", () => {
  test("같은 sid 라도 다른 부서 호스트 줄은 켜지지 않는다 · 이름 보고자 줄은 안 켠다", () => {
    const sel = { key: "1", sid: 3 };
    expect(seatRowSelected("1", 3, false, sel)).toBe(true);
    expect(seatRowSelected("2", 3, false, sel)).toBe(false);
    expect(seatRowSelected("1", 4, false, sel)).toBe(false);
    expect(seatRowSelected("1", 3, true, sel)).toBe(false);
    expect(seatRowSelected("1", 3, false, null)).toBe(false);
    expect(seatRowSelected("board", 3, false, { key: "board", sid: 3 })).toBe(false); // 상황판 호스트는 좌석 줄이 아니다
  });
  test("서명에 포커스가 없다 — 포커스 이동이 3초 고리 다시 그리기를 낳지 않는다", () => {
    const inp: SeatInput = { sid: 1, displayNo: 1, role: "worker", title: "", cwd: "/w/a", exited: false, dot: "waiting", approvalPending: false, statusState: null, task: null, ctxPct: 30, ctxSrc: "measured" };
    expect(seatRowsSignature(buildSeatRows([inp]))).not.toContain("sel");
  });
});

describe("BA5 서명 — 분이 바뀔 때만 다시 그림(C-20)", () => {
  const at = (ageSecs: number | null) => seatRowsSignature(buildSeatRows([{ sid: 1, displayNo: 1, role: "worker", title: "", cwd: "/w/a", exited: false, dot: "waiting", approvalPending: false, statusState: null, task: null, ctxPct: 30, ctxSrc: "measured", ageSecs }]));
  test("59초 → 61초 = 다름 · 61초 → 119초 = 같음 · 120초 = 다름", () => {
    expect(at(59)).not.toBe(at(61));
    expect(at(61)).toBe(at(119));
    expect(at(120)).not.toBe(at(119));
  });
  test("툴팁(접근 이름)에 「N분째」", () => {
    const m = buildSeatRows([{ sid: 1, displayNo: 1, role: "worker", title: "", cwd: "/w/a", exited: false, dot: "input", approvalPending: false, statusState: null, task: null, ctxPct: 30, ctxSrc: "measured", ageSecs: 2400 }]);
    expect(seatRowTitle(m.groups[0].rows[0])).toContain("40분째");
  });
});

describe("대비 값 표(WCAG 식 · 글자 ≥ 4.5 · 비글자 ≥ 3) — 설계 §5 숫자 고정", () => {
  const rows: [string, string, string, number, number][] = [
    ["좌석 줄 글자", "#ffffff", "#1f3a5f", 11.48, 4.5],
    ["좌석 줄·탭 막대", "#58a6ff", "#161b22", 6.85, 3],
    ["위 탭 글자", "#ffffff", "#1f3a5f", 11.48, 4.5],
    ["창 머리줄 제목", "#ffffff", "#1a4f9c", 7.95, 4.5],
    ["부서 카드 이름(W2)", "#ffffff", "#1f2630", 15.24, 4.5],
    ["부서 카드 보조(W2)", "#8b949e", "#1f2630", 4.95, 4.5],
    ["알약(W5)", "#ffffff", "#da3633", 4.61, 4.5],
  ];
  for (const [name, fg, bg, want, floor] of rows) {
    test(`${name} ${fg} / ${bg} = ${want}`, () => {
      expect(r2(contrast(fg, bg))).toBe(want);
      expect(contrast(fg, bg)).toBeGreaterThanOrEqual(floor);
    });
  }
  test("옛 값(결함)도 같은 식으로 재현 — 카드 accent 통채움 3.75 · hover 1.07 · 탭 --bg 1.04", () => {
    expect(r2(contrast("#ffffff", "#2f81f7"))).toBe(3.75);
    expect(r2(contrast("#1c2128", "#161b22"))).toBe(1.07);
    expect(r2(contrast("#1e1e1e", "#161b22"))).toBe(1.04);
  });
  test("표의 색이 views.css 덧씌움 절에 실제로 있다", () => {
    for (const c of ["#1f3a5f", "#58a6ff", "#1a4f9c", "#1f2630", "#da3633"]) expect(css).toContain(c);
  });
});

describe("views.css 「작업 화면 덧씌움」 절 — 원작자 style.css 무변경 · 크기 변화 0(C-17)", () => {
  const sec = css.slice(css.indexOf("작업 화면 덧씌움"));
  test("절이 있고 SEL·W2·W5·W6 선택자가 모두 들었다", () => {
    expect(css.indexOf("작업 화면 덧씌움")).toBeGreaterThan(0);
    for (const s of [".ws-seat.sel", ".group-tab.active", ".pane.focused .pane-title", ".ws-tab.active", ".pane.blocked .pane-title", ".pane-pill", ".toast"]) expect(sec).toContain(s);
  });
  test("선택 강조는 border 두께를 바꾸지 않는다(outline·box-shadow 로만 · PTY 크기 변경 0)", () => {
    const selRules = sec.split("}").filter((r) => /\.ws-seat\.sel|\.pane\.focused|\.group-tab\.active/.test(r));
    for (const r of selRules) expect(r).not.toMatch(/border(-(top|bottom|left|right))?(-width)?\s*:/);
  });
  test("W2 왼쪽 막대 = 인라인 부서색을 활성 카드에서만 이김(!important · master#e78fbc98 ①)", () => {
    expect(sec).toMatch(/\.ws-tab\.active\s*\{[^}]*border-left-color:\s*var\(--accent\)\s*!important/);
    expect(main).toContain("tab.style.borderLeftColor = color;"); // 인라인 색을 지우는 쪽으로 넓히지 않았다
  });
  test("윈 고대비 — forced-colors 에서 Highlight 테두리", () => {
    expect(sec).toMatch(/@media \(forced-colors: active\)[\s\S]*Highlight/);
  });
  test("W6 — 14px · 줄 높이 1.45 · 왼쪽 3px · 150ms · 움직임 줄이기 끔 · TTL 무변경", () => {
    expect(sec).toMatch(/\.toast\s*\{[^}]*font-size:\s*14px/);
    expect(sec).toMatch(/\.toast\s*\{[^}]*line-height:\s*1\.45/);
    expect(sec).toMatch(/\.toast\s*\{[^}]*border-left-width:\s*3px/);
    expect(sec).toMatch(/\.toast\s*\{[^}]*150ms/);
    expect(sec).toMatch(/prefers-reduced-motion: reduce\)[^{]*\{[^}]*\.toast[^}]*animation:\s*none/);
  });
});

describe("SEL-3·SEL-4·W5 배선 원천 검사", () => {
  test("위 탭 두 호출부가 표시용 인자(넓게 보기 좌석이 든 탭)를 넘긴다 — 동작용 active 는 그대로", () => {
    const calls = [...main.matchAll(/buildTabBar\(([^;]*)\);/g)].map((m) => m[1]);
    expect(calls.length).toBe(2);
    for (const c of calls) {
      expect(c).toContain("v.zoom === null ? v.active : null");
      expect(c).toContain("tabDisplayActive(v)");
    }
    expect(tabbar).toContain("zoomed");
  });
  test("3초 틱의 제목 역할색은 포커스 창을 건너뛴다(C-08)", () => {
    const line = main.split("\n").find((l) => l.includes("rt.titleEl.style.color = (titleColorRole")) ?? "";
    expect(line).toContain("!(focusedSid != null && paneKey(s.surface_id, sk) === paneKey(focusedSid, current()?.socket))"); // isFocusedPaneKey 와 같은 식(3초 틱 시험 하네스 대역 목록을 늘리지 않게 인라인)
    expect(main).toContain("return focusedSid != null && key === paneKey(focusedSid, current()?.socket);");
  });
  test("막힌 창 알약은 좌석 줄과 같은 판정(seatDot = input)에서 칠한다", () => {
    const fn = main.slice(main.indexOf("function refreshSeatRows(): void {"));
    const body = fn.slice(0, fn.indexOf("\n}\n"));
    expect(body).toContain('paintBlockedPill(prt, dotView === "input"');
    expect(body).toContain("const dotView = seatDot(");
  });
});
