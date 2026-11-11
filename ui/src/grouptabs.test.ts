// grouptabs.ts 순수부 시험 — TICKET=cysr-tabs-sidebar-impl 조각 2a.
// 못박는 것: 노브 기본 켜짐 · 묶음 1개 이하 = 탭 없음(지금 화면 그대로) · 탭 순서 보존·새 묶음 뒤에 붙음 · 활성 탭 폴백 ·
//   넓게 보기(zoom) = 그 좌석만 + 그 묶음으로 전환 · 고정 좌석(master·cso)은 숨기지 않음 · 보기 트리는 ws.tree 를 바꾸지 않음 ·
//   저장값 정규화(형식 오류 = 기본값) · 재부팅 뒤(번호 재발급) 같은 탭 배치.
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { buildSeatRows, type SeatInput } from "./seatrows";
import { GROUP_TABS_KEY, groupTabsOn, normalizeTabState, reconcileTabs, seatKey, viewTree, zoomKeyOf } from "./grouptabs";
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
    const prev = { order: ["lms", "site"], active: "lms", zoom: null, zoomKey: null };
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
    const prev = { order: ["lms", "gone", "site"], active: "site", zoom: null, zoomKey: null };
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms"), seat(6, "worker-4", "/w/video")), prev, true);
    expect(r.state.order).toEqual(["lms", "site", "video"]);
    expect(r.view.tabs.map((t) => t.key)).toEqual(["lms", "site", "video"]);
    expect(r.view.active).toBe("site");
    expect(r.view.hidden.sort()).toEqual([4, 6]);
  });
  test("활성 묶음이 사라지면 첫 탭으로", () => {
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms")), { order: [], active: "gone", zoom: null, zoomKey: null }, true);
    expect(r.view.active).toBe("site");
  });
  test("넓게 보기 = 그 좌석만(+ 고정 좌석) · 활성 탭 = 그 좌석의 묶음", () => {
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms"), seat(5, "worker-3", "/w/lms")), { order: [], active: "site", zoom: 5, zoomKey: "role:worker-3" }, true);
    expect(r.view.active).toBe("lms");
    expect(r.view.zoom).toBe(5);
    expect(r.view.hidden.sort()).toEqual([3, 4]);
  });
  test("넓게 보던 좌석이 사라지면 넓게 보기를 푼다", () => {
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms")), { order: [], active: "site", zoom: 99, zoomKey: "role:worker-9" }, true);
    expect(r.view.zoom).toBeNull();
    expect(r.state.zoom).toBeNull();
  });
  test("묶음 1개여도 넓게 보기는 된다(좌석 줄 클릭) — 다른 좌석만 숨김", () => {
    const r = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/site")), { order: [], active: null, zoom: 4, zoomKey: "role:worker-2" }, true);
    expect(r.view.tabs).toEqual([]);
    expect(r.view.hidden).toEqual([3]);
  });
  test("재부팅 뒤 좌석 번호가 새로 발급돼도 같은 묶음 열쇠(폴더)라 같은 탭 배치", () => {
    const prev = reconcileTabs(model(M, seat(3, "worker", "/w/site"), seat(4, "worker-2", "/w/lms")), { order: ["lms", "site"], active: "lms", zoom: null, zoomKey: null }, true).state;
    const saved = JSON.parse(JSON.stringify(prev));
    const after = reconcileTabs(model(seat(101, "master", "/w"), seat(103, "worker", "/w/site"), seat(104, "worker-2", "/w/lms")), normalizeTabState(saved), true);
    expect(after.view.tabs.map((t) => t.key)).toEqual(["lms", "site"]);
    expect(after.view.active).toBe("lms");
    expect(after.view.hidden).toEqual([103]);
  });
});

describe("(codex 1R) 넓게 보기 = 번호가 아니라 안정 열쇠(역할 · 없으면 폴더)", () => {
  test("재부팅 뒤 번호가 뒤바뀌어도(A 좌석 7→9 · B 좌석 → 7) B 를 넓게 보지 않고 A 를 따라간다", () => {
    const before = model(M, seat(7, "worker", "/w/site"), seat(8, "worker-2", "/w/lms"));
    const saved = JSON.parse(JSON.stringify({ order: ["site", "lms"], active: "site", zoom: 7, zoomKey: zoomKeyOf(before, 7) }));
    const after = reconcileTabs(model(M, seat(9, "worker", "/w/site"), seat(7, "worker-2", "/w/lms")), normalizeTabState(saved), true);
    expect(after.view.zoom).toBe(9);
    expect(after.view.active).toBe("site");
    expect([after.state.zoom, after.state.zoomKey]).toEqual([9, "role:worker"]);
  });
  test("넓게 보던 좌석이 사라지고 그 번호를 다른 좌석이 받았으면 넓게 보기만 풀고 저장된 활성 탭은 그대로", () => {
    const after = reconcileTabs(model(M, seat(7, "worker-2", "/w/lms"), seat(8, "worker-3", "/w/site")), { order: ["site", "lms"], active: "site", zoom: 7, zoomKey: "role:worker" }, true);
    expect(after.view.zoom).toBeNull();
    expect(after.view.active).toBe("site");
    expect([after.state.active, after.state.zoom, after.state.zoomKey]).toEqual(["site", null, null]);
  });
  test("열쇠 없는 저장값(옛 형식 zoom 만) = 알아볼 수 없음 → 풀기 · 활성 탭 유지", () => {
    const after = reconcileTabs(model(M, seat(7, "worker", "/w/site"), seat(8, "worker-2", "/w/lms")), normalizeTabState({ order: [], active: "lms", zoom: 7 }), true);
    expect(after.view.zoom).toBeNull();
    expect(after.view.active).toBe("lms");
  });
  test("역할 없는 좌석 = 폴더 열쇠 · 같은 폴더에 역할 없는 좌석이 둘이면 번호가 맞을 때만 붙들고 옮기지 않는다", () => {
    const two = model(M, seat(5, "", "/w/site"), seat(6, "", "/w/site"), seat(8, "worker-2", "/w/lms"));
    expect(zoomKeyOf(two, 5)).toBe("cwd:/w/site");
    expect(reconcileTabs(two, { order: [], active: null, zoom: 5, zoomKey: "cwd:/w/site" }, true).view.zoom).toBe(5);
    const moved = model(M, seat(15, "", "/w/site"), seat(16, "", "/w/site"), seat(5, "worker-2", "/w/lms"));
    expect(reconcileTabs(moved, { order: [], active: null, zoom: 5, zoomKey: "cwd:/w/site" }, true).view.zoom).toBeNull();
  });
  test("seatKey — 역할 우선 · 폴더 다음 · 둘 다 없으면 null · 고정 좌석(master)은 zoomKeyOf 대상 아님", () => {
    expect(seatKey({ role: " worker ", cwd: "/w" })).toBe("role:worker");
    expect(seatKey({ role: null, cwd: "/w/a" })).toBe("cwd:/w/a");
    expect(seatKey({ role: null, cwd: null })).toBeNull();
    expect(zoomKeyOf(model(M, seat(3, "worker", "/w/site")), 1)).toBeNull();
  });
});

describe("저장값 정규화", () => {
  test("형식 오류 = 기본값 · 문자열 아닌 순서 항목 버림 · zoom 은 정수만", () => {
    expect(normalizeTabState(undefined)).toEqual({ order: [], active: null, zoom: null, zoomKey: null });
    expect(normalizeTabState("x")).toEqual({ order: [], active: null, zoom: null, zoomKey: null });
    expect(normalizeTabState({ order: ["a", 3, "b", "a"], active: 5, zoom: 1.5, zoomKey: 3 })).toEqual({ order: ["a", "b"], active: null, zoom: null, zoomKey: null });
    expect(normalizeTabState({ order: ["a"], active: "a", zoom: 7, zoomKey: "role:w" })).toEqual({ order: ["a"], active: "a", zoom: 7, zoomKey: "role:w" });
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
    expect(body("pickSeat")).toContain("const off = st.zoom === sid && i === activeWs;");
    expect(body("pickSeat")).toContain("ws.tabs = { ...st, zoom: off ? null : sid, zoomKey: off || !m ? null : zoomKeyOf(m, sid) };");
    expect(body("pickSeat")).toContain("if (groupTabs && !fixed) {");
  });
});

describe("(2b) 고정 기둥 판정 — 탭 줄은 오른쪽 영역 위에만", async () => {
  const { fixedColumnSplit } = await import("./grouptabs");
  const pane = (sid: number): LayoutNode => ({ type: "pane", sid });
  const t: LayoutNode = { type: "split", dir: "row", ratio: 0.3, a: { type: "split", dir: "col", ratio: 0.8, a: pane(1), b: pane(2) }, b: { type: "split", dir: "row", a: pane(3), b: pane(4) } };
  test("master·cso 왼쪽 기둥 = 맞음 · master 만(cso 없음) = 맞음 · 고정 없음 = 아님 · 고정이 오른쪽에 섞임 = 아님", () => {
    expect(fixedColumnSplit(t, [1, 2])).toBe(true);
    expect(fixedColumnSplit({ type: "split", dir: "row", a: pane(1), b: pane(3) }, [1])).toBe(true);
    expect(fixedColumnSplit(t, [])).toBe(false);
    expect(fixedColumnSplit({ type: "split", dir: "row", a: pane(3), b: pane(1) }, [1])).toBe(false);
    expect(fixedColumnSplit(pane(1), [1])).toBe(false);
  });
});

describe("(2c) 같은 크기 재전송 0 — fitPane 배선", () => {
  const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  test("마지막으로 보낸 열·행과 같으면 resize_surface 를 보내지 않는다 · 실패면 기억을 지운다", () => {
    const i = main.indexOf("function fitPane(");
    const f = main.slice(i, main.indexOf("\n}\n", i));
    expect(f).toContain("if (lastSentSize.get(rt) === size) return;");
    expect(f.indexOf("if (lastSentSize.get(rt) === size) return;") < f.indexOf('invoke("resize_surface"')).toBe(true);
    expect(f).toContain(".catch(() => lastSentSize.delete(rt));");
    expect(f).toContain("if (rt.termHost.offsetWidth < 60 || rt.termHost.offsetHeight < 40) return;"); // 숨은 좌석 = PTY 마지막 크기 유지(기존 가드)
  });
  // (codex 1R 논쟁 · 재부착) 크기 기억은 런타임 객체에 묶인 WeakMap 이다. 붙기(start_surface_stream)는 makePane 안 한 곳뿐이고
  //   그 직후 새 런타임을 만들므로 새 PTY 에 붙을 때마다 기억은 비어 시작한다 = 첫 맞춤은 반드시 보낸다.
  //   같은 런타임을 새 PTY 에 다시 붙이는 길이 생기면 이 시험이 깨진다 — 그때 그 길에서 lastSentSize.delete(rt) 를 넣어라.
  test("붙기는 makePane 안 한 곳뿐 · 붙은 뒤 새 런타임 = 크기 기억 빈 채 시작", () => {
    expect(main.split('invoke("start_surface_stream"').length - 1).toBe(1);
    const i = main.indexOf("async function makePane(");
    const f = main.slice(i, main.indexOf("\n}\n", i));
    expect(f).toContain('await invoke("start_surface_stream", { socket, surfaceId: sid });');
    expect(f.indexOf('invoke("start_surface_stream"') < f.indexOf("const rt: PaneRuntime = {")).toBe(true);
    expect(main).toContain("const lastSentSize = new WeakMap<PaneRuntime, string>();");
  });
});

describe("(codex 1R) 다시 그리기 예약 가드", () => {
  const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  test("준비 중·모델 없음이면 예약하지 않는다(무한 마이크로태스크 고리 차단) · 저장값 정규화", () => {
    const i = main.indexOf("function refreshSeatRows(");
    const f = main.slice(i, main.indexOf("\n}\n", i));
    expect(f).toContain("if (ws && !ws.pending && seatModels.has(ws.id) && !tabRenderQueued) {");
    expect(f).toContain("reconcileTabs(seatModels.get(ws.id)!, normalizeTabState(ws.tabs), groupTabs)");
  });
});

describe("(2b-2 · A안) 격자 — 4개 이하 한 줄(시안 #C) · 5개부터 두 줄 이상 · 칸 최소 40열×12줄(못 지키면 가장 덜 모자란 고른 격자)", async () => {
  const { gridColumns, gridView, GRID_MIN_COLS, GRID_MIN_ROWS } = await import("./grouptabs");
  const pane = (sid: number): LayoutNode => ({ type: "pane", sid });
  const row = (...xs: LayoutNode[]): LayoutNode => xs.slice(1).reduce((acc, x) => ({ type: "split", dir: "row", a: acc, b: x }) as LayoutNode, xs[0]);
  const shape = (n: LayoutNode): unknown => (n.type === "pane" ? n.sid : n.dir === "col" ? ["col", shape(n.a), shape(n.b)] : ["row", shape(n.a), shape(n.b)]);
  const rowsOf = (n: LayoutNode): number[][] => {
    const leaves = (x: LayoutNode): number[] => (x.type === "pane" ? [x.sid] : [...leaves(x.a), ...leaves(x.b)]);
    return n.type === "split" && n.dir === "col" ? [...rowsOf(n.a), ...rowsOf(n.b)] : [leaves(n)];
  };
  // 1920 실측(e2e grid_gate 탐침): 오른쪽 975px · 높이 1150px · 칸 최소 = 40열 334px · 12줄 230px
  const W = 975, H = 1150, MW = 334, MH = 230;
  test("4개 이하 = 한 줄(폭과 무관 · 시안 #C) · 재료 모름 = ⌈n÷2⌉", () => {
    expect([GRID_MIN_COLS, GRID_MIN_ROWS]).toEqual([40, 12]);
    expect([1, 3, 4].map((n) => gridColumns(n, W, H, MW, MH))).toEqual([1, 3, 4]);
    expect([5, 7, 12].map((n) => gridColumns(n, 0, 0, 0, 0))).toEqual([3, 4, 6]);
  });
  test("5개부터 = 최소 칸을 지키는 가장 적은 줄 · 1920 실측 = 5→2열(3줄) · 7→2열(4줄) · 넓은 영역 = 7→4열(2줄)", () => {
    expect([5, 7].map((n) => gridColumns(n, W, H, MW, MH))).toEqual([2, 2]);
    expect(gridColumns(7, 1500, 1150, MW, MH)).toBe(4);
    expect(gridColumns(12, 1500, 1150, MW, MH)).toBe(4);
  });
  test("최소를 못 지키면 가장 덜 모자란 고른 격자(설계 §4 최소 아래 허용) — 1920 의 12개 = 2열 6줄이 아니라 덜 모자란 쪽", () => {
    const c = gridColumns(12, W, H, MW, MH);
    const fit = (k: number) => Math.min(W / k / MW, H / Math.ceil(12 / k) / MH);
    for (let k = 1; k <= 6; k++) expect(fit(c)).toBeGreaterThanOrEqual(fit(k));
    expect(fit(c)).toBeLessThan(1);
  });
  test("고정 기둥(1·2) 오른쪽만 접는다 · 좌석 7 을 4열 = 4+3 · 12 를 4열 = 4+4+4 · 고정 기둥 폭(ratio) 유지 · 입력 무변경", () => {
    const left: LayoutNode = { type: "split", dir: "col", ratio: 0.8, a: pane(1), b: pane(2) };
    const t = (k: number): LayoutNode => ({ type: "split", dir: "row", ratio: 0.3, a: left, b: row(...Array.from({ length: k }, (_, i) => pane(10 + i))) });
    const t7 = t(7);
    const before = JSON.stringify(t7);
    const g7 = gridView(t7, [1, 2], () => 4)!;
    expect(JSON.stringify(t7)).toBe(before);
    expect(g7.type === "split" && g7.ratio).toBe(0.3);
    expect(g7.type === "split" && shape(g7.a)).toEqual(["col", 1, 2]);
    expect(g7.type === "split" && rowsOf(g7.b)).toEqual([[10, 11, 12, 13], [14, 15, 16]]);
    const g12 = gridView(t(12), [1, 2], () => 4)!;
    expect(g12.type === "split" && rowsOf(g12.b)).toEqual([[10, 11, 12, 13], [14, 15, 16, 17], [18, 19, 20, 21]]);
  });
  test("한 줄로 충분 · 사람이 위아래로 나눈 기둥이 섞임 · 트리 없음 = 그대로(같은 객체) · 고정 좌석 없으면 전체를 접는다", () => {
    const t3: LayoutNode = { type: "split", dir: "row", ratio: 0.3, a: pane(1), b: row(pane(10), pane(11), pane(12)) };
    expect(gridView(t3, [1], () => 3)).toBe(t3);
    const mixed: LayoutNode = { type: "split", dir: "row", a: pane(1), b: row(pane(10), { type: "split", dir: "col", a: pane(11), b: pane(12) }, pane(13), pane(14), pane(15)) };
    expect(gridView(mixed, [1], () => 2)).toBe(mixed);
    expect(gridView(null, [], () => 2)).toBeNull();
    expect(rowsOf(gridView(row(pane(10), pane(11), pane(12)), [], () => 2)!)).toEqual([[10, 11], [12]]);
  });
});
