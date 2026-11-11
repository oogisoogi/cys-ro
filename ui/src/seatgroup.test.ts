// seatgroup.ts 순수부 시험 — TICKET=cysr-tabs-sidebar-impl 조각 2d · codex 1R 반영.
// 못박는 것: 열쇠 = 소켓 + 역할(없으면 생성 폴더) · 데몬이 정한 값(group_set) > 앱 기록 > 자동 · 해제(group_set ∧ null) = 앱 기록 지움(놓친 해제 복구) ·
//   group_set 없음(데몬 재시작·구판) = 앱 기록 유지 · 열쇠가 둘 이상 좌석에 같으면 읽지도 쓰지도 않음(딸려 옮겨짐 0) ·
//   재부팅(번호 재발급) 뒤에도 같은 좌석의 묶음 · 저장값 형식 오류 = 빈 기록.
import { describe, expect, test } from "bun:test";
import { effectiveGroup, parseSeatGroups, SEAT_GROUP_KEY, seatGroupKey, syncSeatGroupsFromList, uniqueKeys } from "./seatgroup";
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
  test("데몬이 정한 값 = 기록 · 같은 값 = 변화 없음 · group_set 없음 = 앱 기록 유지(데몬 재시작)", () => {
    const a = syncSeatGroupsFromList({}, undefined, [{ role: "worker", cwd: "/w/site", group: "lms", group_set: true }]);
    expect(a).toEqual({ map: { "#role:worker": "lms" }, changed: true });
    expect(syncSeatGroupsFromList(a.map, undefined, [{ role: "worker", cwd: "/w/site", group: "lms", group_set: true }]).changed).toBe(false);
    expect(syncSeatGroupsFromList(a.map, undefined, [{ role: "worker", cwd: "/w/site", group: null, group_set: false }])).toEqual({ map: a.map, changed: false });
    expect(syncSeatGroupsFromList(a.map, undefined, [{ role: "worker", cwd: "/w/site", group: null }])).toEqual({ map: a.map, changed: false }); // 구판 데몬
  });
  test("(codex 1R ③) 놓친 해제 복구 — 앱이 꺼진 동안 해제됐어도 다음 목록(group_set ∧ null)이 기록을 지운다", () => {
    const r = syncSeatGroupsFromList({ "#role:worker": "lms" }, undefined, [{ role: "worker", cwd: "/w/site", group: null, group_set: true }]);
    expect(r).toEqual({ map: {}, changed: true });
  });
  test("(codex 1R ②) 같은 열쇠 좌석이 둘이면 그 열쇠로는 읽지도 쓰지도 않는다 — A 만 옮겨도 B 는 그대로", () => {
    const list = [
      { role: null, cwd: "/w/site", group: "lms", group_set: true }, // A(옮김)
      { role: null, cwd: "/w/site", group: null, group_set: false }, // B
    ];
    expect(uniqueKeys(undefined, list).size).toBe(0);
    expect(syncSeatGroupsFromList({}, undefined, list)).toEqual({ map: {}, changed: false });
    const uniq = uniqueKeys(undefined, list);
    expect(effectiveGroup({ "#cwd:/w/site": "video" }, undefined, list[0], uniq)).toBe("lms"); // A = 데몬 값
    expect(effectiveGroup({ "#cwd:/w/site": "video" }, undefined, list[1], uniq)).toBeNull(); // B = 옛 기록도 안 읽는다(자동)
  });
  test("effectiveGroup — 데몬 값 > 앱 기록(열쇠 하나뿐) > null · 해제 = null(앱 기록이 있어도)", () => {
    const m = { "#role:worker": "lms" };
    const unknown = { role: "worker", cwd: "/w/site", group: null, group_set: false };
    const uniq = uniqueKeys(undefined, [unknown]);
    expect(effectiveGroup(m, undefined, unknown, uniq)).toBe("lms");
    expect(effectiveGroup(m, undefined, { ...unknown, group: "video", group_set: true }, uniq)).toBe("video");
    expect(effectiveGroup(m, undefined, { ...unknown, group: null, group_set: true }, uniq)).toBeNull();
    expect(effectiveGroup(m, undefined, undefined, uniq)).toBeNull();
  });
  test("재부팅 뒤 번호가 바뀌어도(데몬 값 모름) 같은 좌석(역할)의 묶음이 좌석 줄 묶음이 된다(사람이 옮긴 묶음 > 폴더)", () => {
    const m: Record<string, string> = { "#role:worker-2": "lms" };
    const rows = [
      { role: "worker", cwd: "/w/site", group: null, group_set: false },
      { role: "worker-2", cwd: "/w/site", group: null, group_set: false },
    ];
    const uniq = uniqueKeys(undefined, rows);
    const seat = (sid: number, i: number): SeatInput => ({ sid, displayNo: sid, role: rows[i].role, title: "", cwd: rows[i].cwd, exited: false, dot: "working",
      approvalPending: false, statusState: null, task: null, ctxPct: null, ctxSrc: "none", group: effectiveGroup(m, undefined, rows[i], uniq) });
    const model = buildSeatRows([seat(103, 0), seat(104, 1)]);
    expect(model.groups.map((g) => [g.key, g.rows.map((r) => r.sid)])).toEqual([["site", [103]], ["lms", [104]]]);
  });
});
