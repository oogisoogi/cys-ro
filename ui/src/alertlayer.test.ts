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
// (1.1.8 병합) 원작자 층서 토큰(:root --z-*)을 받았으므로 z-index 가 var(--z-x) 면 :root 값을 따라간다(숫자 리터럴도 그대로).
const zToken = (name: string): number => Number(new RegExp(`${name}:\\s*(\\d+)`).exec(css)?.[1] ?? NaN);
const z = (sel: string): number => {
  const v = /z-index:\s*([^;]+);/.exec(block(sel))?.[1]?.trim() ?? "";
  const ref = /^var\(\s*(--z-[\w-]+)\s*\)$/.exec(v);
  return ref ? zToken(ref[1]) : Number(/^\d+$/.test(v) ? v : NaN);
};

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

  // (1.1.8 병합 · 원작자 층서 수용 — style.css #toasts = var(--z-toast)) 옛 계약 「확인 창·Control Center 보다 아래」는
  // 원작자 2026-09-23 수리(토스트가 CC 패널 뒤에 묻혀 실패가 조용해짐)로 바뀌었다. 단언의 목적(알림 줄이 창의 조작부를
  // 가로채지 않는다)은 원작자 회피 규칙으로 지킨다: 확인 창 밖의 창이 떠 있으면 토스트는 그 창 **밑**(그래도 CC 위).
  it("확인 창 밖의 창이 떠 있으면 알림 줄은 그 창(.modal-overlay) 밑 · Control Center 위 — 조작부를 가로채지 않는다", () => {
    expect(zToken("--z-toast-under-modal")).toBeLessThan(z(".modal-overlay"));
    expect(zToken("--z-toast-under-modal")).toBeGreaterThan(z("#cc-panel"));
    expect(css).toContain("body:has(.modal-overlay:not(.confirm-overlay)) #toasts { z-index: var(--z-toast-under-modal); }");
  });

  it("복원 카드는 알림 줄(아래)과 다른 모서리 — 오른쪽 **위**(상단바 아래)에 선다 · 아래·왼쪽에 붙지 않는다", () => {
    const b = block("#restore-brief");
    expect(b).toContain("top: calc(var(--topbar-h, 38px) + 12px)");
    expect(/(^|[\s;{])bottom:/.test(b)).toBe(false); // 아래에 붙으면 알림 줄과 다시 겹친다
    expect(/(^|[\s;{])left:/.test(b)).toBe(false); // 왼쪽 아래 = 편성 CSO 창·파일 목록 가림(Fable F1·F3)
    expect(block("#toasts")).toContain("bottom: 12px");
  });
});
