// 사람·master 가 옮긴 좌석 묶음의 앱 쪽 기록 — 순수 판정 (TICKET=cysr-tabs-sidebar-impl 조각 2d · 설계 §1·§5 · codex 1R 반영).
//
// 무엇을 하나: 데몬 `surface.list` 의 group·group_set 칸(이벤트 surface.group.changed 는 그 칸을 바로 고쳐 쓴다)을 읽어
//   ① 데몬이 이번 기동 중 정한 값(group_set = true)이 있으면 **그 좌석은 그 값**(묶음 이름 또는 null = 해제 = 자동 규칙) ·
//   ② 정한 값이 없으면(데몬 재시작 등 = 모름) 앱 기록을 쓴다. 앱 기록 열쇠 = 소켓 + 역할(없으면 생성 폴더 = grouptabs.seatKey) —
//   재부팅으로 번호가 바뀌어도 같은 좌석을 찾기 위해서다.
// ★열쇠가 그 소켓 안에서 둘 이상의 좌석에 같으면(역할 없는 같은 폴더 좌석 등) 그 열쇠로는 읽지도 쓰지도 않는다 — 다른 좌석이
//   딸려 옮겨지지 않게(codex 1R ②). 그런 좌석은 데몬 값(①)으로만 옮겨지고, 데몬이 다시 켜지면 자동 규칙으로 돌아간다.
// ★해제(group_set = true · group = null)는 앱 기록을 지운다 — 앱이 이벤트를 놓쳐도 다음 목록이 해제를 되살린다(codex 1R ③).
import { seatKey } from "./grouptabs";

export const SEAT_GROUP_KEY = "cys-seat-group";
export type SeatGroups = Record<string, string>;
/** surface.list 원행 중 이 판정이 읽는 칸. */
export interface GroupRow {
  role?: unknown;
  cwd?: unknown;
  group?: unknown;
  group_set?: unknown;
}

/** 저장값 → 기록. 형식이 어긋나면 빈 기록 · 문자열이 아닌 값·빈 이름은 버린다. */
export function parseSeatGroups(raw: string | null): SeatGroups {
  try {
    const o = JSON.parse(raw ?? "{}");
    if (!o || typeof o !== "object" || Array.isArray(o)) return {};
    const out: SeatGroups = {};
    for (const [k, v] of Object.entries(o)) if (typeof v === "string" && v.trim()) out[k] = v.trim();
    return out;
  } catch {
    return {};
  }
}

/** 기록 열쇠 — 소켓(본부 = "") + seatKey. 좌석을 알아볼 재료가 없으면 null(기록하지 않는다). */
export function seatGroupKey(socket: string | null | undefined, role: string | null | undefined, cwd: string | null | undefined): string | null {
  const k = seatKey({ role: role ?? null, cwd: cwd ?? null });
  return k ? `${socket ?? ""}#${k}` : null;
}

const str = (v: unknown): string | null => (typeof v === "string" ? v : null);
const keyOf = (socket: string | null | undefined, s: GroupRow): string | null => seatGroupKey(socket, str(s.role), str(s.cwd));

/** 그 소켓 목록에서 열쇠가 **하나뿐인** 좌석들의 열쇠 집합(둘 이상이면 빠진다). */
export function uniqueKeys(socket: string | null | undefined, surfaces: readonly GroupRow[]): Set<string> {
  const n = new Map<string, number>();
  for (const s of surfaces) {
    const k = keyOf(socket, s);
    if (k) n.set(k, (n.get(k) ?? 0) + 1);
  }
  return new Set([...n].filter(([, c]) => c === 1).map(([k]) => k));
}

/** 데몬이 정한 값(group_set = true)을 앱 기록에 반영 — 열쇠가 하나뿐인 좌석만 · 묶음 = 기록 · 해제 = 지움. */
export function syncSeatGroupsFromList(m: SeatGroups, socket: string | null | undefined, surfaces: readonly GroupRow[]): { map: SeatGroups; changed: boolean } {
  const uniq = uniqueKeys(socket, surfaces);
  let map = m;
  let changed = false;
  for (const s of surfaces) {
    if (s.group_set !== true) continue; // 모름(데몬 재시작·구판 데몬) = 앱 기록 유지
    const k = keyOf(socket, s);
    if (!k || !uniq.has(k)) continue;
    const g = str(s.group)?.trim() || null;
    if (g === null ? !(k in map) : map[k] === g) continue;
    if (g === null) {
      const { [k]: _drop, ...rest } = map;
      map = rest;
    } else map = { ...map, [k]: g };
    changed = true;
  }
  return { map, changed };
}

/** 이 좌석의 묶음 — 데몬이 정한 값 > (열쇠가 하나뿐일 때) 앱 기록 > null(자동 규칙 = 생성 폴더). */
export function effectiveGroup(m: SeatGroups, socket: string | null | undefined, s: GroupRow | undefined, uniq: ReadonlySet<string>): string | null {
  if (!s) return null;
  if (s.group_set === true) return str(s.group)?.trim() || null;
  const k = keyOf(socket, s);
  return k && uniq.has(k) ? (m[k] ?? null) : null;
}
