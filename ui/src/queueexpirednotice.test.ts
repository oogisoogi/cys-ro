import { describe, it, expect } from "bun:test";
import { queueExpiredItem, queueExpiredNotice, EXPIRED_NOTICE_ORIGIN } from "./queueexpirednotice";

describe("queueExpiredNotice — 큐 만료(유실) 1줄(cysr-queued-paste-submit ⓒ)", () => {
  it("좌석·역할 표기와 건수를 그대로 말한다", () => {
    const it1 = queueExpiredItem({ surface_ref: "surface:61", role: "master", queue_entry_id: "q1", origin: "queue" });
    expect(it1).toEqual({ surfaceRef: "surface:61", role: "master" });
    const n = queueExpiredNotice(it1!, 3);
    expect(n.title).toBe("전달하지 못한 메시지 3건이 시간이 지나 대기열에서 빠졌습니다");
    expect(n.detail).toContain("master(surface:61)");
    expect(n.detail).toContain("cys queue list --expired");
  });
  it("역할이 없으면 좌석 표기만", () => {
    const it2 = queueExpiredItem({ surface_ref: "surface:7", role: null });
    expect(queueExpiredNotice(it2!, 1).detail.startsWith("surface:7 창이")).toBe(true);
  });
  it("만료 통지 항목 자신의 만료는 알리지 않는다(통지의 통지 연쇄 금지)", () => {
    expect(queueExpiredItem({ surface_ref: "surface:9", origin: EXPIRED_NOTICE_ORIGIN })).toBe(null);
  });
  it("payload 를 믿지 않는다", () => {
    for (const p of [null, "x", 3, {}, { surface_ref: 5 }, { surface_ref: "" }]) {
      expect(queueExpiredItem(p)).toBe(null);
    }
  });
  it("위협 표현이 없다", () => {
    const n = queueExpiredNotice({ surfaceRef: "surface:1", role: "worker" }, 2);
    for (const w of ["위험", "경고", "실패", "오류", "삭제"]) {
      expect(n.title + n.detail).not.toContain(w);
    }
  });
});
