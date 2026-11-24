// (TICKET=cysr-1119-s5 · V6) 스크롤 판정 시험 3 — 위 200px · 1.5배 답 · 48px 안(DESIGN §6 V6 합격 칸).
import { describe, expect, it } from "bun:test";
import { jumpLabel, newKeys, placeAfterPaint, STICK_PX, stickToBottom } from "./scroll";

describe("V6 — 새 답 단추 · 바닥 붙음", () => {
  it("문턱 = 48px(1.1.18 4px 아님)", () => {
    expect(STICK_PX).toBe(48);
    expect(stickToBottom({ scrollTop: 552, clientHeight: 400, scrollHeight: 1000 })).toBe(true); // 바닥까지 48
    expect(stickToBottom({ scrollTop: 551, clientHeight: 400, scrollHeight: 1000 })).toBe(false); // 49
  });

  it("① 위로 200px 올린 채 답 1개 도착 → 위치 불변 · 단추 「↓ 새 답 1 · 맨 아래로」", () => {
    const before = { scrollTop: 400, clientHeight: 400, scrollHeight: 1000 }; // 바닥까지 200
    const stuck = stickToBottom(before);
    expect(stuck).toBe(false);
    const fresh = newKeys(new Set(["a", "b"]), ["a", "b", "c"]);
    expect(fresh).toEqual(["c"]);
    expect(placeAfterPaint(stuck, before.scrollTop, { scrollTop: 400, clientHeight: 400, scrollHeight: 1300 }, { top: 1000, height: 300 })).toBe(400);
    expect(jumpLabel(fresh.length)).toBe("↓ 새 답 1 · 맨 아래로");
    expect(jumpLabel(0)).toBeNull();
  });

  it("② 바닥에 붙어 있고 칸 높이 1.5배 답 도착 → 답 첫 줄이 칸 위 24px 안", () => {
    const before = { scrollTop: 600, clientHeight: 400, scrollHeight: 1000 };
    const top = placeAfterPaint(stickToBottom(before), before.scrollTop, { scrollTop: 600, clientHeight: 400, scrollHeight: 1600 }, { top: 1000, height: 600 });
    const firstLineFromViewTop = 1000 - top;
    expect(firstLineFromViewTop).toBeGreaterThanOrEqual(0);
    expect(firstLineFromViewTop).toBeLessThan(25);
    expect(top).toBeLessThan(1600 - 400); // 맨 아래가 아님
  });

  it("③ 바닥 48px 안 + 짧은 답 → 단추 없이 따라감(맨 아래)", () => {
    const before = { scrollTop: 560, clientHeight: 400, scrollHeight: 1000 }; // 바닥까지 40
    expect(stickToBottom(before)).toBe(true);
    expect(placeAfterPaint(true, 560, { scrollTop: 560, clientHeight: 400, scrollHeight: 1100 }, { top: 1000, height: 100 })).toBe(700);
  });

  it("새 답 없음 + 붙어 있음 = 맨 아래 · 위치 상한 = 바닥", () => {
    expect(placeAfterPaint(true, 0, { scrollTop: 0, clientHeight: 400, scrollHeight: 900 }, null)).toBe(500);
    expect(placeAfterPaint(false, 9999, { scrollTop: 0, clientHeight: 400, scrollHeight: 900 }, null)).toBe(500);
    expect(placeAfterPaint(true, 0, { scrollTop: 0, clientHeight: 400, scrollHeight: 300 }, null)).toBe(0);
  });
});
