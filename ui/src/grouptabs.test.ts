// grouptabs.ts 순수부 시험 — TICKET=cysr-tabs-sidebar-impl 조각 2a.
// 못박는 것: 노브 기본 켜짐 · 묶음 1개 이하 = 탭 없음(지금 화면 그대로) · 탭 순서 보존·새 묶음 뒤에 붙음 · 활성 탭 폴백 ·
//   넓게 보기(zoom) = 그 좌석만 + 그 묶음으로 전환 · 고정 좌석(master·cso)은 숨기지 않음 · 보기 트리는 ws.tree 를 바꾸지 않음 ·
//   저장값 정규화(형식 오류 = 기본값) · 재부팅 뒤(번호 재발급) 같은 탭 배치.
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { buildSeatRows, type SeatInput } from "./seatrows";
import { GROUP_TABS_KEY, groupTabsOn, normalizeTabState, reconcileTabs, viewTree } from "./grouptabs";
import type { LayoutNode } from "./formation";

const seat = (sid: number, role: string, cwd: string): SeatInput => ({
  sid, displayNo: sid, role, title: "", cwd, exited: false, dot: "working", approvalPending: false,
  statusState: null, task: null, ctxPct: null, ctxSrc: "none",
});
const model = (...xs: SeatInput[]) => buildSeatRows(xs);
const M = seat(1, "master", "/w");
const C = seat(2, "cso", "/w/cso");

describe("노브", () => {
  test("열쇠 이름 · 기본 켜짐 · \"0\" 만 끔", () => {
    expect(GROUP_TABS_KEY).toBe("cys-group-tabs");
    expect(groupTabsOn(null)).toBe(true);
    expect(groupTabsOn("1")).toBe(true);
    expect(groupTabsOn("0")).toBe(false);
  });
});

describe("탭 판정", () => {
  test("묶음 1개 이하 = 탭 없음 · 숨김 0(왕초보 화면 = 지금 그대로)", () => {
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/site")), undefined, true);
    expect(r.view.tabs).toEqual([]);
    expect(r.view.hidden).toEqual([]);
  });
  test("노브 꺼짐 = 묶음이 여럿이어도 탭 없음 · 숨김 0 · 저장 순서는 지우지 않는다", () => {
    const prev = { order: ["lms", "site"], active: "lms", zoom: null };
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms")), prev, false);
    expect(r.view.tabs).toEqual([]);
    expect(r.view.hidden).toEqual([]);
    expect(r.state.order).toEqual(["lms", "site"]);
  });
  test("묶음 2개 = 탭 2개 · 처음 = 첫 묶음 활성 · 다른 묶음 좌석만 숨김 · 고정 좌석은 언제나 보임", () => {
    const r = reconcileTabs(model(M, C, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms"), seat(5, "worker-3", "/w/site")), undefined, true);
    expect(r.view.tabs.map((t) => [t.key, t.sids])).toEqual([["site", [3, 5]], ["lms", [4]]]);
    expect(r.view.active).toBe("site");
    expect(r.view.hidden).toEqual([4]);
  });
  test("저장된 탭 순서를 지킨다 · 사라진 묶음은 빠지고 새 묶음은 뒤에 붙는다", () => {
    const prev = { order: ["lms", "gone", "site"], active: "site", zoom: null };
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms"), seat(6, "worker-4", "/w/video")), prev, true);
    expect(r.state.order).toEqual(["lms", "site", "video"]);
    expect(r.view.tabs.map((t) => t.key)).toEqual(["lms", "site", "video"]);
    expect(r.view.active).toBe("site");
    expect(r.view.hidden.sort()).toEqual([4, 6]);
  });
  test("활성 묶음이 사라지면 첫 탭으로", () => {
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms")), { order: [], active: "gone", zoom: null }, true);
    expect(r.view.active).toBe("site");
  });
  test("넓게 보기 = 그 좌석만(+ 고정 좌석) · 활성 탭 = 그 좌석의 묶음", () => {
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms"), seat(5, "worker-3", "/w/lms")), { order: [], active: "site", zoom: 5 }, true);
    expect(r.view.active).toBe("lms");
    expect(r.view.zoom).toBe(5);
    expect(r.view.hidden.sort()).toEqual([3, 4]);
  });
  test("넓게 보던 좌석이 사라지면 넓게 보기를 푼다", () => {
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms")), { order: [], active: "site", zoom: 99 }, true);
    expect(r.view.zoom).toBeNull();
    expect(r.state.zoom).toBeNull();
  });
  test("묶음 1개여도 넓게 보기는 된다(좌석 줄 클릭) — 다른 좌석만 숨김", () => {
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/site")), { order: [], active: null, zoom: 4 }, true);
    expect(r.view.tabs).toEqual([]);
    expect(r.view.hidden).toEqual([3]);
  });
  test("재부팅 뒤 좌석 번호가 새로 발급돼도 같은 묶음 열쇠(폴더)라 같은 탭 배치", () => {
    const prev = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms")), { order: ["lms", "site"], active: "lms", zoom: null }, true).state;
    const saved = JSON.parse(JSON.stringify(prev));
    const after = reconcileTabs(model(seat(101, "master", "/w"), seat(103, "worker", "/w/site"), seat(104, "worker-2", "/w/lms")), normalizeTabState(saved), true);
    expect(after.view.tabs.map((t) => t.key)).toEqual(["lms", "site"]);
    expect(after.view.active).toBe("lms");
    expect(after.view.hidden).toEqual([103]);
  });
});

describe("저장값 정규화", () => {
  test("형식 오류 = 기본값 · 문자열 아닌 순서 항목 버림 · zoom 은 정수만", () => {
    expect(normalizeTabState(undefined)).toEqual({ order: [], active: null, zoom: null });
    expect(normalizeTabState("x")).toEqual({ order: [], active: null, zoom: null });
    expect(normalizeTabState({ order: ["a", 3, "b", "a"], active: 5, zoom: 1.5 })).toEqual({ order: ["a", "b"], active: null, zoom: null });
    expect(normalizeTabState({ order: ["a"], active: "a", zoom: 7 })).toEqual({ order: ["a"], active: "a", zoom: 7 });
  });
});

describe("보기 트리 — ws.tree 를 바꾸지 않는 파생", () => {
  const pane = (sid: number): LayoutNode => ({ type: "pane", sid });
  const roles = new Map<number, string>([[1, "master"], [2, "cso"], [3, "worker"], [4, "worker-2"], [5, "worker-3"]]);
  const tree: LayoutNode = {
    type: "split", dir: "row", ratio: 0.3,
    a: { type: "split", dir: "col", ratio: 0.8, a: pane(1), b: pane(2) },
    b: { type: "split", dir: "row", ratio: 1 / 3, a: pane(3), b: { type: "split", dir: "row", ratio: 0.5, a: pane(4), b: pane(5) } },
  };
  const sids = (n: LayoutNode | null, out: number[] = []): number[] => {
    if (!n) return out;
    if (n.type === "pane") out.push(n.sid);
    else { sids(n.a, out); sids(n.b, out); }
    return out;
  };
  test("숨김 없음 = 같은 트리 객체", () => {
    expect(viewTree(tree, roles, [], 0.25)).toBe(tree);
  });
  test("숨김 = 그 좌석이 빠진 트리 · 원본 트리는 그대로 · 사람이 끈 왼쪽 기둥 폭(0.3) 보존 · 남은 기둥 균등", () => {
    const before = JSON.stringify(tree);
    const v = viewTree(tree, roles, [4], 0.25)!;
    expect(JSON.stringify(tree)).toBe(before);
    expect(sids(v)).toEqual([1, 2, 3, 5]);
    expect(v.type === "split" && v.ratio).toBe(0.3);
    const right = v.type === "split" ? v.b : null;
    expect(right?.type === "split" && right.ratio).toBe(0.5);
  });
  test("역할 표가 없으면(목록 전) 그 자리에서 잘라낸다", () => {
    expect(sids(viewTree(tree, undefined, [3, 4], 0.25))).toEqual([1, 2, 5]);
  });
  test("빈 트리 = null", () => {
    expect(viewTree(null, roles, [1], 0.25)).toBeNull();
  });
});

describe("main.ts 배선(2a) — 배선만", () => {
  const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  const body = (name: string): string => {
    const i = main.search(new RegExp(`(async )?function ${name}\\(`));
    expect(i >= 0).toBe(true);
    return main.slice(i, main.indexOf("\n}\n", i) + 3);
  };
  test("render() 는 보기 트리(wsViewTree)를 그리고 맞춤도 그 트리의 좌석만 — ws.tree 는 건드리지 않는다", () => {
    expect(body("render")).toContain("const tree = ws ? wsViewTree(ws) : null;");
    expect(body("render")).toContain("for (const sid of collectSids(tree ?? null)) {");
    expect(body("wsViewTree").includes("ws.tree =")).toBe(false);
  });
  test("탭 상태는 저장된다(saveLayout 이 tabs 를 털지 않는다)", () => {
    expect(body("saveLayout").includes("tabs:")).toBe(false);
  });
  test("노브 = 화면 설정 「묶음 탭」 · 기본값 복원 = 켜짐", () => {
    expect(main).toContain("let groupTabs = groupTabsOn(localStorage.getItem(GROUP_TABS_KEY));");
    expect(main).toContain('groupTabsRow.textContent = "묶음 탭"');
    expect(main).toContain("if (!groupTabs) applyGroupTabs(true); gtCb.checked = true;");
  });
  test("좌석 줄 클릭 = 넓게 보기 토글 · 고정 좌석은 대상 아님", () => {
    expect(body("pickSeat")).toContain("ws.tabs = { ...st, zoom: st.zoom === sid && i === activeWs ? null : sid };");
    expect(body("pickSeat")).toContain("if (groupTabs && !fixed) {");
  });
});
