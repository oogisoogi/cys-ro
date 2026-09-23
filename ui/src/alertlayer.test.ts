// alertlayer.test.ts — 경보(알림 줄)가 복원 카드에 가려지지 않는다(D4 #21) · TICKET=v116-ui-close.
//
// 실기 맥락(D4-ui.md #21 · VM v5 · D2 s6): 복원 카드가 오른쪽 아래 알림 줄을 덮어, 그 뒤에 뜬 「Claude Code CLI가
// 없습니다」·「❌ 에이전트 사망」 알림이 카드 뒤에 깔려 안 보였다. 화면 실측은 docs/v116-ui-evidence/v116-headless.ts c6.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
const block = (sel: string): string => {
  const i = css.indexOf(`\n${sel} {`);
  expect(i).toBeGreaterThan(-1);
  return css.slice(i, css.indexOf("}", i));
};
const z = (sel: string): number => Number(/z-index:\s*(\d+)/.exec(block(sel))?.[1] ?? NaN);

describe("D4 #21 세로 배분 — 카드(위)와 알림 줄(아래)이 둘 다 길어져도 만나지 않는다(Fable 2R)", () => {
  it("알림 줄 상한 40vh · 카드 상한이 그 40vh 를 빼고 잡힌다(두 값은 짝)", () => {
    expect(block("#toasts")).toContain("max-height: 40vh;");
    expect(block("#restore-brief")).toContain("max-height: calc(100vh - var(--topbar-h, 38px) - 12px - 40vh - 12px - 12px);");
  });
});

describe("D4 #21 경보 층위 — 알림 줄은 복원 카드보다 위", () => {
  it("#toasts z-index > #restore-brief z-index", () => {
    expect(z("#toasts")).toBeGreaterThan(z("#restore-brief"));
  });

  it("그래도 확인 창(.modal-overlay)·Control Center·팔레트보다는 아래(층 계약 무변경)", () => {
    expect(z("#toasts")).toBeLessThan(z(".modal-overlay"));
    expect(z("#toasts")).toBeLessThan(z("#cc-panel"));
  });

  it("복원 카드는 알림 줄(아래)과 다른 모서리 — 오른쪽 **위**(상단바 아래)에 선다 · 아래·왼쪽에 붙지 않는다", () => {
    const b = block("#restore-brief");
    expect(b).toContain("top: calc(var(--topbar-h, 38px) + 12px)");
    expect(/(^|[\s;{])bottom:/.test(b)).toBe(false); // 아래에 붙으면 알림 줄과 다시 겹친다
    expect(/(^|[\s;{])left:/.test(b)).toBe(false); // 왼쪽 아래 = 편성 CSO 창·파일 목록 가림(Fable F1·F3)
    expect(block("#toasts")).toContain("bottom: 12px");
  });
});
