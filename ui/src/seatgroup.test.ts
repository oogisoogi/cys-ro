// seatgroup.ts 순수부 시험 — TICKET=cysr-tabs-sidebar-impl 조각 2d · codex 1R 반영.
// 못박는 것: 열쇠 = 소켓 + 역할(없으면 생성 폴더) · 데몬이 정한 값(group_set) > 앱 기록 > 자동 · 해제(group_set ∧ null) = 앱 기록 지움(놓친 해제 복구) ·
//   group_set 없음(데몬 재시작·구판) = 앱 기록 유지 · 열쇠가 둘 이상 좌석에 같으면 읽지도 쓰지도 않음(딸려 옮겨짐 0) ·
//   재부팅(번호 재발급) 뒤에도 같은 좌석의 묶음 · 저장값 형식 오류 = 빈 기록.
import { describe, expect, test } from "bun:test";
import { cleanGroupName, effectiveGroup, forgetSeatGroup, parseSeatGroups, SEAT_GROUP_KEY, seatGroupKey, syncSeatGroupsFromList, uniqueKeys } from "./seatgroup";
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

describe("(948 D3) 끝난 좌석의 옮긴 묶음 기록 지우기 — 같은 역할명을 재배정받은 새 좌석이 물려받지 않게", () => {
  const w4 = { role: "worker-4", cwd: "/u/axdev/lms" };
  const others = [{ role: "worker-5", cwd: "/u/axdev/lms" }, w4];
  test("끝난 좌석 열쇠(하나뿐) = 지움 · 다른 기록 그대로 · 새 worker-4 는 자동 규칙(앱 기록 없음)", () => {
    const m = { "#role:worker-4": "video", "#role:worker-5": "site" };
    const r = forgetSeatGroup(m, undefined, w4, others);
    expect(r).toEqual({ map: { "#role:worker-5": "site" }, changed: true });
    const fresh = { role: "worker-4", cwd: "/u/axdev/newproj" };
    expect(effectiveGroup(r.map, undefined, fresh, uniqueKeys(undefined, [fresh]))).toBeNull();
  });
  test("기록 없음 · 좌석 줄 모름 · 열쇠가 둘 이상(기록이 쓰이지 않던 좌석) = 그대로", () => {
    const m = { "#role:worker-4": "video" };
    expect(forgetSeatGroup({}, undefined, w4, others).changed).toBe(false);
    expect(forgetSeatGroup(m, undefined, undefined, others)).toEqual({ map: m, changed: false });
    expect(forgetSeatGroup(m, undefined, w4, [w4, { role: "worker-4", cwd: "/x" }]).changed).toBe(false);
    expect(forgetSeatGroup(m, "/d.sock", w4, others).changed).toBe(false); // 다른 소켓 열쇠는 건드리지 않는다
  });
  test("(ChatGPT 1R #6) 같은 열쇠 좌석 B 가 있는 동안 기록 주인 A(데몬이 정한 묶음 = 기록 값)가 끝나면 지운다 — 남으면 B 가 혼자 남는 순간 A 의 묶음을 물려받는다", () => {
    const k = "#cwd:/u/axdev/proj";
    const a = { role: null, cwd: "/u/axdev/proj", group: "video", group_set: true };
    const b = { role: null, cwd: "/u/axdev/proj", group: null, group_set: false };
    expect(forgetSeatGroup({ [k]: "video" }, undefined, a, [a, b])).toEqual({ map: {}, changed: true });
    // (codex 1R #3) 주인 아닌 B 가 목록에서 먼저 빠진 뒤 끝남 = 호출자(main.forgetEndedSeatGroup)가 B 의 마지막 줄을 넣어 겹침을 본다 → 그대로
    expect(forgetSeatGroup({ [k]: "video" }, undefined, b, [{ ...a, group_set: false }, b]).changed).toBe(false);
    // 주인이 아닌 쪽(B · 데몬 값 없음)이 끝나면 = 열쇠가 겹쳐 있으니 그대로(남의 기록 보존)
    expect(forgetSeatGroup({ [k]: "video" }, undefined, b, [a, b]).changed).toBe(false);
    // 주인 판정은 「데몬이 정한 값 = 기록 값」 일 때만 — 다른 묶음이면 주인 아님
    expect(forgetSeatGroup({ [k]: "lms" }, undefined, a, [a, b]).changed).toBe(false);
  });
  test("재시작 복원(끝 신호 없이 번호만 바뀜)은 이 함수를 부르지 않는다 — 기록이 남아 같은 역할 좌석이 그 묶음으로", () => {
    const m = { "#role:worker-4": "video" };
    const renumbered = { role: "worker-4", cwd: "/u/axdev/lms" };
    expect(effectiveGroup(m, undefined, renumbered, uniqueKeys(undefined, [renumbered]))).toBe("video");
  });
});

describe("(948 D7) 묶음 이름 = NFKC 뒤 Cc·Cf·Zl·Zp 거부(데몬 parse_seat_group 과 같은 규칙)", () => {
  test("폭 0 · BOM · 줄/문단 구분 · NEL · 방향 표시 · 소프트 하이픈 = 못 쓰는 이름(null)", () => {
    for (const bad of ["\u200Bsite", "\uFEFFsite", "si\u2028te", "si\u2029te", "si\u0085te", "a\u202Eb", "a\u2066b", "si\u00ADte", "x".repeat(65)]) expect(cleanGroupName(bad)).toBeNull();
    // (ChatGPT 1R #9) 범주 밖 보이지 않는 문자(Default_Ignorable_Code_Point) · 고립 대리 문자(JS 만 가질 수 있음)
    for (const bad of ["si\u034Fte", "site\uFE0F", "site\uFE0E", "\u3164site", "si\u115Fte", "site\uD800", "\uDC00site"]) expect(cleanGroupName(bad)).toBeNull();
  });
  test("NFKC 정규화 · 앞뒤 공백 · 결합 문자는 합침 · 한글 그대로 · 문자열 아님 = null", () => {
    expect(cleanGroupName("ｓｉｔｅ")).toBe("site");
    expect(cleanGroupName("  ﬁle ")).toBe("file");
    expect(cleanGroupName("e\u0301")).toBe("\u00E9");
    expect(cleanGroupName("교육 부서")).toBe("교육 부서");
    expect(cleanGroupName("\u2028site\n")).toBe("site"); // 앞뒤 White_Space(줄 구분·줄바꿈 포함)는 자른다 — 데몬 str::trim 과 같다
    expect([cleanGroupName("  "), cleanGroupName(5), cleanGroupName(null)]).toEqual([null, null, null]);
  });
  test("저장값·데몬 값 모두 같은 규칙 — BOM 붙은 이름은 버리고, 전각은 같은 탭 열쇠로", () => {
    expect(parseSeatGroups(JSON.stringify({ a: "\uFEFFsite", b: "ｌｍｓ" }))).toEqual({ b: "lms" });
    expect(effectiveGroup({}, undefined, { role: "w", cwd: "/x", group: "\u200Bsite", group_set: true }, new Set())).toBeNull();
    expect(effectiveGroup({}, undefined, { role: "w", cwd: "/x", group: "ｓｉｔｅ", group_set: true }, new Set())).toBe("site");
  });
});

