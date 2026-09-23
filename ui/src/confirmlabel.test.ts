// confirmlabel.test.ts — 확인창 거절 버튼 말 통일(D4 #20) · TICKET=v116-ui-close-r2.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { CLOSE_CONFIRM_TEXT } from "./closeguard";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");

describe("D4 #20 확인창 거절 버튼 = 「취소」", () => {
  it("confirmModal 기본 거절 말 = 취소 (종전 아니오)", () => {
    const sig = main.slice(main.indexOf("function confirmModal("), main.indexOf("): Promise<boolean> {", main.indexOf("function confirmModal(")));
    expect(sig.includes('noLabel = "취소"')).toBe(true);
    expect(sig.includes("아니오")).toBe(false);
  });
  it("다른 확인창(창 닫기)도 같은 말", () => {
    expect(CLOSE_CONFIRM_TEXT.no).toBe("취소");
  });
  it("호출부가 거절 말을 따로 줄 때는 상황 말(나중에·닫기)만 — 「아니오」 0", () => {
    const calls = [...main.matchAll(/confirmModal\(([^;]*?)\);/gs)].map((m) => m[1]);
    expect(calls.length).toBeGreaterThan(5);
    for (const c of calls) expect(`${c.slice(0, 40)}: ${c.includes('"아니오"')}`).toBe(`${c.slice(0, 40)}: false`);
  });
});
