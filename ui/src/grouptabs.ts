// 묶음 탭 — 순수 판정 (TICKET=cysr-tabs-sidebar-impl 조각 2a · 설계 docs/DESIGN-tabs-sidebar.md §1·§3·§8).
//
// 무엇을 하나: 좌석 줄 모델(seatrows.buildSeatRows)의 묶음을 탭으로 보고, 저장된 탭 상태(순서·활성·넓게 보기)를 지금 좌석에 맞춰
//   정리한 뒤 「이번 화면에서 숨길 좌석」을 낸다. 화면 트리는 viewTree 가 ws.tree 에서 **파생**한다 — ws.tree 는 언제나 전 좌석 트리
//   그대로다(입양·유령 퇴거·부서 간 이동·저장 경로 무변경 · 설계 §1 「트리는 하나만」).
// ★묶음 1개 이하 · 노브 꺼짐 = 탭 없음 · 숨김 0 → 지금(1.1.14) 화면 그대로(왕초보 화면 불변 §8).
// ★탭 열쇠 = 묶음 열쇠(폴더 이름 문자열)라 재부팅으로 좌석 번호가 새로 발급돼도 같은 배치가 돌아온다(wsreconcile.ts 머리 주석).
// ★숨김 = DOM 에서 떼어 두기(다른 부서 좌석과 같은 길) — PTY 는 마지막 크기 그대로(main.ts fitPane 가드).
import { arrangeWithoutRoles, autoArrange, type LayoutNode } from "./formation";
import type { SeatRowsModel } from "./seatrows";

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

const EMPTY: TabState = { order: [], active: null, zoom: null };

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
  };
}

/** 저장 상태 + 지금 좌석 → 정리된 상태 + 이번 화면. */
export function reconcileTabs(m: SeatRowsModel, prev: TabState | undefined, on: boolean): { state: TabState; view: TabView } {
  const p = prev ?? EMPTY;
  if (!on) return { state: { ...p, zoom: null }, view: { tabs: [], active: null, zoom: null, hidden: [] } };
  const groups: TabInfo[] = m.groups.map((g) => ({ key: g.key, label: g.label, sids: g.rows.map((r) => r.sid) }));
  const keys = groups.map((g) => g.key);
  // 순서: 저장 순서 중 지금 있는 것 → 새 묶음은 모델 순(처음 나타난 순)으로 뒤에.
  const order = [...p.order.filter((k) => keys.includes(k)), ...keys.filter((k) => !p.order.includes(k))];
  const zoomGroup = p.zoom === null ? undefined : groups.find((g) => g.sids.includes(p.zoom as number));
  const zoom = zoomGroup ? p.zoom : null;
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
    state: { order: multi ? order : [...p.order, ...keys.filter((k) => !p.order.includes(k))], active, zoom },
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
