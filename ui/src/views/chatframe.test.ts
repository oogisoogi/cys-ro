// (TICKET=cysr-1119-s5) 대화 화면 틀 원천 검사 — V2(전환 끝 1줄) · CV-RAIL(결과 칸 = rail) · V5 · V8 대비 · V11 지연. 화면 동작 = e2e chatscroll_gate.py.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";

const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const css = read("./views.css");
const chat = read("./chat/index.ts");
const reg = read("./registry.ts");

// WCAG 2.x 상대 휘도 대비
function lum(hex: string): number {
  const v = hex.replace("#", "");
  const c = [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16) / 255).map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function contrast(a: string, b: string): number {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

describe("V2 — 대화 화면 표지 = registry 전환 끝 1줄", () => {
  it("live 를 세운 바로 뒤 body.view-chat 토글(document 없으면 건너뜀) · 한 곳", () => {
    const line = 'if (typeof document !== "undefined") document.body.classList.toggle("view-chat", id === "chat");';
    expect(reg.split(line).length - 1).toBe(1);
    expect(reg.indexOf(line)).toBeGreaterThan(reg.indexOf("this.live = mounted;"));
    expect(css).toContain("body.view-chat #topbar { background: var(--cv-bg);");
  });
});

describe("CV-RAIL — 결과 칸 = 왼쪽 칸 · 가운데 칸 스크롤 상자 하나", () => {
  it("results.el 은 rail.results 에 붙고 가운데 칸 insertBefore 0", () => {
    expect(chat).toContain("rail.results.append(results.el);");
    expect(chat).not.toContain("root.insertBefore(results.el, log)");
    expect(chat).toContain("rail.setResults(res.count);");
    expect(read("./chat/rail.ts")).not.toContain("childElementCount");
  });
  it("rail 안 결과 칸 = max-height·overflow 풂 · s6 카드 규칙이 결과 카드를 덮지 않음", () => {
    expect(css).toContain(".cv-rail .cv-results { max-height: none; overflow: visible;");
    expect(css).toContain(".cv-rail .cvr-card:not(.cvr-res-card) { display: block;");
  });
});

describe("V5 · V8 · V11 — 스타일 계약", () => {
  it("V5 입력칸 = 한 줄에서 8줄까지(field-sizing + 8lh) · 한글 조합 Enter 무시 줄 그대로", () => {
    expect(css).toMatch(/\.cv-input \{[^}]*max-height: 8lh; field-sizing: content;/);
    expect(chat).toContain("input.rows = 1;");
    expect(chat).toContain('if (e.key !== "Enter" || e.shiftKey || e.isComposing || e.keyCode === 229) return;');
  });
  it("V8 포커스 링 대비 ≥ 3:1(밝은 대화 #fff · 어두운 대화 · 작업 화면 상단바·왼쪽 막대 #161b22)", () => {
    const pick = (re: RegExp) => (css.match(re) ?? [])[1];
    const light = pick(/:root \{ --cv-focus: (#[0-9a-f]{6});/);
    const bar = pick(/--cv-focus-bar: (#[0-9a-f]{6});/);
    const dark = pick(/:root:not\(\[data-theme="light"\]\) \{ --cv-focus: (#[0-9a-f]{6}); \}/);
    expect([light, bar, dark]).toEqual(["#2d5bcb", "#7ea2ff", "#7ea2ff"]);
    expect(contrast(light, "#ffffff")).toBeGreaterThanOrEqual(3);
    expect(contrast(light, "#f8f9fa")).toBeGreaterThanOrEqual(3); // 왼쪽 칸 바탕 --cv-soft
    expect(contrast(dark, "#15181e")).toBeGreaterThanOrEqual(3);
    expect(contrast(bar, "#161b22")).toBeGreaterThanOrEqual(3);
    expect(css).toContain(".cv-wrap :focus-visible { outline: 2px solid var(--cv-focus);");
    expect(css).not.toMatch(/:focus \{/); // 클릭(:focus)엔 링 규칙 0
  });
  it("V11 뼈대 = 250ms 지연 등장(backwards) · 움직임 줄이기 = 반짝임 없음 · 화면 읽기 글 유지", () => {
    expect(css).toContain("animation: cv-skel-in 1ms linear 250ms backwards, cv-skel-shimmer 1.6s linear 250ms infinite;");
    expect(css).toMatch(/prefers-reduced-motion: reduce\) \{\n  \.cvr-skel \{ animation: cv-skel-in 1ms linear 250ms backwards; \}/);
    expect(read("./chat/rail.ts")).toContain('sk.setAttribute("aria-label", "불러오는 중이에요");');
  });
});
