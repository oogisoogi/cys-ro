// 묶음 탭 — 순수 판정 (TICKET=cysr-tabs-sidebar-impl 조각 2a · 설계 docs/DESIGN-tabs-sidebar.md §1·§3·§8).
//
// 무엇을 하나: 좌석 줄 모델(seatrows.buildSeatRows)의 묶음을 탭으로 보고, 저장된 탭 상태(순서·활성·넓게 보기)를 지금 좌석에 맞춰
//   정리한 뒤 「이번 화면에서 숨길 좌석」을 낸다. 화면 트리는 viewTree 가 ws.tree 에서 **파생**한다 — ws.tree 는 언제나 전 좌석 트리
//   그대로다(입양·유령 퇴거·부서 간 이동·저장 경로 무변경 · 설계 §1 「트리는 하나만」).
// ★묶음 1개 이하 · 노브 꺼짐 = 탭 없음 · 숨김 0 → 지금(1.1.14) 화면 그대로(왕초보 화면 불변 §8).
// ★탭 열쇠 = 묶음 열쇠(폴더 이름 문자열)라 재부팅으로 좌석 번호가 새로 발급돼도 같은 배치가 돌아온다(wsreconcile.ts 머리 주석).
// ★숨김 = DOM 에서 떼어 두기(다른 부서 좌석과 같은 길) — PTY 는 마지막 크기 그대로(main.ts fitPane 가드).
import { arrangeWithoutRoles, autoArrange, DRAG_MAX, type LayoutNode } from "./formation";
import type { SeatRow, SeatRowsModel } from "./seatrows";

export const GROUP_TABS_KEY = "cys-group-tabs";
/** 기본 켜짐 — "0" 일 때만 끈다(꺼지면 지금처럼 전부 나란히). */
export function groupTabsOn(raw: string | null): boolean {
  return raw !== "0";
}

/** 부서(워크스페이스)마다 저장되는 탭 상태 — cys-layout-v2 의 ws.tabs. */
export interface TabState {
  /** 탭 순서(묶음 열쇠). 지금 없는 묶음은 정리 때 빠진다. */
  order: string[];
  active: string | null;
  /** 넓게 보기 중인 좌석 sid(좌석 줄 클릭) — null = 묶음 전체 나란히. */
  zoom: number | null;
  /** (codex 1R) 넓게 보기 좌석의 안정 열쇠(seatKey) — 재부팅으로 번호가 다시 발급돼도 같은 좌석을 찾는다. 없으면 넓게 보기를 붙들지 않는다. */
  zoomKey: string | null;
}

export interface TabInfo {
  key: string;
  label: string;
  sids: number[];
}

export interface TabView {
  /** 그릴 탭(묶음 2개 이상 · 노브 켜짐일 때만 · 아니면 빈 배열). */
  tabs: TabInfo[];
  active: string | null;
  zoom: number | null;
  /** 이번 화면에서 떼어 둘 좌석(고정 좌석 master·cso 는 절대 들지 않는다). */
  hidden: number[];
}

const EMPTY: TabState = { order: [], active: null, zoom: null, zoomKey: null };

/** 저장값(localStorage → JSON) 정규화 — 형식이 어긋나면 그 칸만 기본값. */
export function normalizeTabState(raw: unknown): TabState {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return { ...EMPTY };
  const o = raw as Record<string, unknown>;
  const order: string[] = [];
  if (Array.isArray(o.order)) for (const k of o.order) if (typeof k === "string" && !order.includes(k)) order.push(k);
  return {
    order,
    active: typeof o.active === "string" ? o.active : null,
    zoom: typeof o.zoom === "number" && Number.isSafeInteger(o.zoom) ? o.zoom : null,
    zoomKey: typeof o.zoomKey === "string" ? o.zoomKey : null,
  };
}

/** 좌석의 안정 열쇠(부서 = 소켓 하나라 소켓은 빼고) — 역할 우선 · 없으면 생성 폴더 · 둘 다 없으면 null(알아볼 수 없음). */
export function seatKey(r: Pick<SeatRow, "role" | "cwd">): string | null {
  const role = (r.role ?? "").trim();
  if (role) return `role:${role}`;
  return r.cwd ? `cwd:${r.cwd}` : null;
}

/** 넓게 보기 좌석 sid → 저장할 열쇠(그 좌석이 묶음에 없으면 null). */
export function zoomKeyOf(m: SeatRowsModel, sid: number): string | null {
  const row = m.groups.flatMap((g) => g.rows).find((r) => r.sid === sid);
  return row ? seatKey(row) : null;
}

/** 저장된 넓게 보기 → 지금 sid. 그 번호의 좌석 열쇠가 같으면 그대로 · 다르면(번호 재발급) 열쇠가 하나뿐인 좌석으로 옮김 · 못 찾거나 여럿이면 null(풀기). */
function resolveZoom(m: SeatRowsModel, zoom: number | null, zoomKey: string | null): number | null {
  if (zoom === null || zoomKey === null) return null;
  const rows = m.groups.flatMap((g) => g.rows);
  const same = rows.find((r) => r.sid === zoom);
  if (same && seatKey(same) === zoomKey) return zoom;
  const hits = rows.filter((r) => seatKey(r) === zoomKey);
  return hits.length === 1 ? hits[0].sid : null;
}

/** 저장 상태 + 지금 좌석 → 정리된 상태 + 이번 화면. */
export function reconcileTabs(m: SeatRowsModel, prev: TabState | undefined, on: boolean): { state: TabState; view: TabView } {
  const p = prev ?? EMPTY;
  if (!on) return { state: { ...p, zoom: null, zoomKey: null }, view: { tabs: [], active: null, zoom: null, hidden: [] } };
  const groups: TabInfo[] = m.groups.map((g) => ({ key: g.key, label: g.label, sids: g.rows.map((r) => r.sid) }));
  const keys = groups.map((g) => g.key);
  // 순서: 저장 순서 중 지금 있는 것 → 새 묶음은 모델 순(처음 나타난 순)으로 뒤에.
  const order = [...p.order.filter((k) => keys.includes(k)), ...keys.filter((k) => !p.order.includes(k))];
  // (codex 1R) 넓게 보기는 번호가 아니라 안정 열쇠로 확인한다 — 재부팅 뒤 다른 좌석이 같은 번호를 받아도 그 좌석을 넓게 보지 않는다.
  //   못 알아보면 넓게 보기만 풀고 저장된 활성 탭은 그대로 둔다.
  const zoom = resolveZoom(m, p.zoom ?? null, p.zoomKey ?? null);
  // (재실행 실측으로 찾음) 좌석 목록이 오기 전 모델(역할·폴더를 모르는 줄)로는 「그 좌석이 사라졌다」를 판정할 수 없다 —
  //   그동안은 넓게 보기만 잠시 풀어 보이고 저장된 열쇠는 지우지 않는다(목록이 오면 되살아난다).
  const identityUnknown = m.groups.some((g) => g.rows.some((r) => seatKey(r) === null));
  const keepStored = zoom === null && (p.zoomKey ?? null) !== null && identityUnknown;
  const zoomGroup = zoom === null ? undefined : groups.find((g) => g.sids.includes(zoom));
  let active: string | null = zoomGroup ? zoomGroup.key : p.active !== null && keys.includes(p.active) ? p.active : (order[0] ?? null);
  const all = groups.flatMap((g) => g.sids);
  const multi = groups.length > 1;
  let hidden: number[];
  if (zoom !== null) hidden = all.filter((s) => s !== zoom);
  else if (multi) hidden = all.filter((s) => !groups.find((g) => g.key === active)!.sids.includes(s));
  else hidden = [];
  if (!multi && zoom === null) active = p.active; // 탭이 없을 땐 저장 활성값을 건드리지 않는다(묶음이 다시 늘면 그대로)
  const byKey = new Map(groups.map((g) => [g.key, g]));
  return {
    state: {
      order: multi ? order : [...p.order, ...keys.filter((k) => !p.order.includes(k))],
      active: keepStored ? p.active : active,
      zoom: keepStored ? p.zoom : zoom,
      zoomKey: keepStored || zoom !== null ? (p.zoomKey ?? null) : null,
    },
    view: { tabs: multi ? order.map((k) => byKey.get(k)!) : [], active: multi ? active : null, zoom, hidden },
  };
}

/** 화면 트리 = ws.tree 에서 숨길 좌석을 뺀 파생(원본 무변경). 숨김 0 이면 같은 객체.
 *  역할 표가 있으면 autoArrange(사람이 끈 왼쪽 기둥 폭 보존 · 나머지 기둥 균등) · 없으면(목록 전) 그 자리 잘라내기. */
export function viewTree(
  tree: LayoutNode | null,
  roles: Map<number, string | null | undefined> | undefined,
  hidden: readonly number[],
  defaultShare: number,
): LayoutNode | null {
  if (!tree) return null;
  if (hidden.length === 0) return tree;
  const change = { remove: [...hidden] };
  return roles ? autoArrange(tree, roles, change, "auto", defaultShare) : arrangeWithoutRoles(tree, change);
}

/** (2b · master#357e735a) 보기 트리의 루트가 「고정 기둥(master·cso) | 오른쪽 영역」 가로 분할인가 — 탭 머리 줄은 오른쪽 영역 위에만 그린다.
 *  맞으면 true(루트 = row 분할 · 왼쪽 서브트리 좌석 = 고정 좌석 전부 · 오른쪽에 고정 좌석 없음). 고정 좌석이 없으면 false(탭 줄 = 전체 위). */
export function fixedColumnSplit(tree: LayoutNode | null, fixedSids: readonly number[]): boolean {
  if (!tree || tree.type !== "split" || tree.dir !== "row" || fixedSids.length === 0) return false;
  const sids = (n: LayoutNode, out: number[] = []): number[] => {
    if (n.type === "pane") out.push(n.sid);
    else { sids(n.a, out); sids(n.b, out); }
    return out;
  };
  const left = sids(tree.a);
  return left.length === fixedSids.length && fixedSids.every((s) => left.includes(s)) && !sids(tree.b).some((s) => fixedSids.includes(s));
}

/** (2b-2 · master#fcbc46fb 결정 ① A안) 격자 칸 최소 폭(글자 열) · 최소 높이(줄 · 설계 §4). */
export const GRID_MIN_COLS = 40;
export const GRID_MIN_ROWS = 12;
/** (2b-3 · 11-11 기둥 폭 규칙 — 최소 폭을 낮추고 싱글/듀얼/노트북 모니터에 맞춘 최적 비율)
 *  탭 화면의 고정 기둥(master·cso) 열 수 = clamp(64, ⌊배치 영역 열 수 × 36%⌋, 96) — 옛 「최소 90열」(묶음 탭 노브 끔 = formation.defaultLeftShare)은 탭 화면에서 쓰지 않는다.
 *  비율은 정수 백분율로 계산한다(0.36 같은 소수 곱은 경계에서 ⌊⌋ 가 한 칸 어긋날 수 있다). */
export const PILLAR_MIN_COLS = 64;
export const PILLAR_MAX_COLS = 96;
export const PILLAR_PCT = 36;
export function pillarCols(areaCols: number): number {
  return Math.min(PILLAR_MAX_COLS, Math.max(PILLAR_MIN_COLS, Math.floor((Math.max(0, Math.floor(areaCols)) * PILLAR_PCT) / 100)));
}
/** 그 열 수를 루트 가로 분할 몫으로 — 배치 영역 열 수 = ⌊배치 영역 px ÷ 글자 칸 px⌋(글자 크기를 따라감 · px 고정값 없음) ·
 *  기둥 px = 열 수 × 글자 칸 + 칸 여백(안쪽 여백·스크롤바·경계 · 호출자가 잰 값). 못 재면 null(호출자가 기존 기본 폭).
 *  오른쪽이 좁아져도 기둥을 더 줄이지 않는다(64열 고정) — 몫은 기존 끌기 상한(DRAG_MAX)만 넘지 않게 둔다(새 최소 창 폭 동작 없음). */
export function tabPillarShare(rootPx: number, cellPx: number, chromePx = 0): number | null {
  if (!(rootPx > 0) || !(cellPx > 0)) return null;
  const cols = pillarCols(rootPx / cellPx);
  return Math.min(DRAG_MAX, (cols * cellPx + Math.max(0, chromePx)) / rootPx);
}
/** (2b-3) 한 줄에 둘 수 있는 가장 많은 칸 = 칸 폭이 최소 폭(40열 px) 이상이 되는 가장 큰 수(최소 1). */
export function gridRowMax(areaW: number, minW: number): number {
  return areaW > 0 && minW > 0 ? Math.max(1, Math.floor(areaW / minW)) : 1;
}
/** 한 줄에 둘 좌석 수(순수 · 2b-3 = 한 규칙 · 옛 「4개 이하 한 줄」 예외 폐지 — 기둥이 36% 로 줄어 1920 에서 3칸 한 줄이 40열을 넘는다).
 *  칸 최소(폭 minW · 높이 minH px)를 지키는 가장 적은 줄 = 한 줄 최대 칸 수(gridRowMax)로 줄 수를 정하고, 줄마다 고르게(4개 = 2×2 · 5개 = 3+2).
 *  높이까지 지킬 수 없으면 「가장 덜 모자란」 고른 격자(칸 폭÷최소폭 과 칸 높이÷최소높이 중 작은 쪽이 가장 큰 것 · 설계 §4 「최소 아래 허용」).
 *  재료를 모르면(첫 그림 전 · 잴 수 없음) 2b-2 대로 4개 이하 한 줄 · 5개부터 ⌈n÷2⌉. */
export function gridColumns(n: number, areaW: number, areaH: number, minW: number, minH: number): number {
  if (n <= 1) return 1;
  if (!(areaW > 0 && areaH > 0 && minW > 0 && minH > 0)) return n <= 4 ? n : Math.ceil(n / 2);
  const even = (c: number) => Math.ceil(n / Math.ceil(n / c)); // 같은 줄 수에서 가장 고른 열 수(≤ c)
  const fit = (c: number) => Math.min(areaW / c / minW, areaH / Math.ceil(n / c) / minH);
  const max = Math.min(n, gridRowMax(areaW, minW));
  if (fit(max) >= 1) return even(max);
  let best = max, bestFit = -1;
  for (let c = n; c >= 1; c--) {
    const f = fit(even(c));
    if (f > bestFit) [best, bestFit] = [even(c), f];
  }
  return best;
}
const evenSplit = (nodes: LayoutNode[], dir: "row" | "col"): LayoutNode => {
  let acc = nodes[nodes.length - 1];
  for (let i = nodes.length - 2; i >= 0; i--) acc = { type: "split", dir, ratio: 1 / (nodes.length - i), a: nodes[i], b: acc };
  return acc;
};
const rowLeaves = (n: LayoutNode, out: LayoutNode[] = []): LayoutNode[] => {
  if (n.type === "split" && n.dir === "row") {
    rowLeaves(n.a, out);
    rowLeaves(n.b, out);
  } else out.push(n);
  return out;
};
/** (2b-2) 보기 트리의 오른쪽 영역(고정 기둥이 있으면 그 오른쪽 · 없으면 전체)을 고른 격자로 접는다 — 열 수 = cols(좌석 수) ·
 *  줄 수 = ⌈n÷열⌉ · 줄마다 가로 균등 · 줄 사이 세로 균등. 한 줄로 충분하면 · 사람이 위아래로 나눈 기둥이 섞여 있으면 그대로(같은 객체).
 *  입력 트리는 바꾸지 않는다. */
export function gridView(tree: LayoutNode | null, fixedSids: readonly number[], cols: (n: number) => number): LayoutNode | null {
  if (!tree) return tree;
  const split = fixedColumnSplit(tree, fixedSids);
  const area = split && tree.type === "split" ? tree.b : tree;
  const units = rowLeaves(area);
  if (units.some((u) => u.type !== "pane")) return tree;
  const c = Math.max(1, Math.floor(cols(units.length)));
  if (c >= units.length) return tree;
  const rows: LayoutNode[] = [];
  for (let i = 0; i < units.length; i += c) rows.push(evenSplit(units.slice(i, i + c), "row"));
  const grid = evenSplit(rows, "col");
  return split && tree.type === "split" ? { ...tree, b: grid } : grid;
}
