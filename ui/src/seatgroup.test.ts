// seatgroup.ts 순수부 시험 — TICKET=cysr-tabs-sidebar-impl 조각 2d.
// 못박는 것: 열쇠 = 소켓 + 역할(없으면 생성 폴더) · 재부팅(번호 재발급) 뒤에도 같은 좌석의 묶음 · 해제 이벤트만 지운다 ·
//   목록의 null(데몬 재시작으로 빈 필드) = 앱 기록 유지 · 저장값 형식 오류 = 빈 기록 · 묶음이 좌석 줄 판정(buildSeatRows)에 들어간다.
import { describe, expect, test } from "bun:test";
import { applySeatGroup, parseSeatGroups, seatGroupKey, SEAT_GROUP_KEY, syncSeatGroupsFromList } from "./seatgroup";
import { buildSeatRows, type SeatInput } from "./seatrows";

describe("(2d) 옮긴 묶음 기록", () => {
  test("열쇠 · 저장값 정규화", () => {
    expect(SEAT_GROUP_KEY).toBe("cys-seat-group");
    expect(seatGroupKey(undefined, "worker-2", "/w/site")).toBe("#role:worker-2");
    expect(seatGroupKey("/d.sock", null, "/w/lms")).toBe("/d.sock#cwd:/w/lms");
    expect(seatGroupKey(undefined, null, null)).toBeNull();
    expect(parseSeatGroups(null)).toEqual({});
    expect(parseSeatGroups("{bad")).toEqual({});
    expect(parseSeatGroups("[1]")).toEqual({});
    expect(parseSeatGroups(JSON.stringify({ a: " lms ", b: 3, c: "" }))).toEqual({ a: "lms" });
  });
  test("새 값 = 기록 · 같은 값 = 변화 없음 · 해제(null) = 지움 · 열쇠 없음 = 무시", () => {
    const k = seatGroupKey(undefined, "worker", "/w/site");
    const a = applySeatGroup({}, k, "lms");
    expect(a).toEqual({ map: { "#role:worker": "lms" }, changed: true });
    expect(applySeatGroup(a.map, k, " lms ").changed).toBe(false);
    expect(applySeatGroup(a.map, k, null)).toEqual({ map: {}, changed: true });
    expect(applySeatGroup(a.map, null, "x")).toEqual({ map: a.map, changed: false });
  });
  test("목록 동기 = 데몬 값이 있는 좌석만 · null(데몬 재시작) 은 앱 기록 유지", () => {
    const m = { "#role:worker": "lms" };
    const r = syncSeatGroupsFromList(m, undefined, [
      { role: "worker", cwd: "/w/site", group: null },
      { role: "worker-2", cwd: "/w/site", group: "video" },
    ]);
    expect(r).toEqual({ map: { "#role:worker": "lms", "#role:worker-2": "video" }, changed: true });
    expect(syncSeatGroupsFromList(r.map, undefined, [{ role: "worker-2", cwd: "/w/site", group: "video" }]).changed).toBe(false);
  });
  test("재부팅 뒤 번호가 바뀌어도 같은 좌석(역할)의 묶음이 좌석 줄 묶음이 된다(사람이 옮긴 묶음 > 폴더)", () => {
    const m: Record<string, string> = { "#role:worker-2": "lms" };
    const seat = (sid: number, role: string, cwd: string): SeatInput => ({ sid, displayNo: sid, role, title: "", cwd, exited: false, dot: "working",
      approvalPending: false, statusState: null, task: null, ctxPct: null, ctxSrc: "none", group: m[seatGroupKey(undefined, role, cwd) ?? ""] ?? null });
    const rows = buildSeatRows([seat(103, "worker", "/w/site"), seat(104, "worker-2", "/w/site")]);
    expect(rows.groups.map((g) => [g.key, g.rows.map((r) => r.sid)])).toEqual([["site", [103]], ["lms", [104]]]);
  });
});
