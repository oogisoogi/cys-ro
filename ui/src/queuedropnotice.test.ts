import { describe, it, expect } from "bun:test";
import { queueDropNotice } from "./queuedropnotice";

describe("queueDropNotice — 사람이 닫은 좌석의 큐 폐기 1줄(Q1-A ①)", () => {
  it("1건 · 여럿은 건수를 그대로 말한다", () => {
    expect(queueDropNotice({ reason: "surface_closed", owner_close: true, count: 1 })?.title).toBe(
      "대기 중이던 지시 1건을 버렸습니다(기록은 남아 있습니다)",
    );
    expect(queueDropNotice({ reason: "surface_closed", owner_close: true, count: 3 })?.title).toBe(
      "대기 중이던 지시 3건을 버렸습니다(기록은 남아 있습니다)",
    );
  });
  it("0건이면 알림 0", () => {
    expect(queueDropNotice({ owner_close: true, count: 0 })).toBe(null);
  });
  it("사람 닫기가 아니면(회수·만기·주차 초과·옛 데몬) 알림 0", () => {
    for (const p of [
      { owner_close: false, count: 2 },
      { reason: "parked_expired", count: 2 },
      { reason: "surface_closed", count: 2 }, // owner_close 키가 없는 옛 데몬
    ]) {
      expect(queueDropNotice(p)).toBe(null);
    }
  });
  it("payload 를 믿지 않는다(문자열 건수·음수·소수·비객체)", () => {
    for (const p of [{ owner_close: true, count: "5" }, { owner_close: true, count: -1 }, { owner_close: true, count: 1.5 }, null, "x", 3]) {
      expect(queueDropNotice(p)).toBe(null);
    }
  });
  it("위협 표현이 없다", () => {
    const t = queueDropNotice({ owner_close: true, count: 2 })!.title;
    for (const w of ["⚠", "경고", "위험", "실패", "오류", "!"]) expect(t.includes(w)).toBe(false);
  });
});
