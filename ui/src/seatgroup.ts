// 사람·master 가 옮긴 좌석 묶음의 앱 쪽 기록 — 순수 판정 (TICKET=cysr-tabs-sidebar-impl 조각 2d · 설계 §1·§5).
//
// 무엇을 하나: 데몬의 `surface.group.changed` 이벤트와 `surface.list` 의 group 칸을 받아, 재부팅으로 좌석 번호가 바뀌어도 같은 좌석을
//   알아보는 열쇠(소켓 + 역할, 역할 없으면 소켓 + 생성 폴더 = grouptabs.seatKey)로 묶음 이름을 기억한다. 데몬 필드는 메모리 전용이라
//   데몬이 다시 켜지면 비지만, 앱 기록이 남아 같은 탭으로 돌아온다(남는 한계 = 데몬 재시작 전에 앱을 한 번도 안 켠 경우 · 설계 §5).
// ★데몬 값이 있으면 그것이 이긴다(최신 명령) · 데몬 값이 없음(null)은 「모름」으로 보고 앱 기록을 지우지 않는다 — 지우는 것은
//   해제 이벤트(group = null) 하나뿐.
import { seatKey } from "./grouptabs";

export const SEAT_GROUP_KEY = "cys-seat-group";
export type SeatGroups = Record<string, string>;

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

/** 해제 이벤트·새 값 반영. 바뀌었으면 changed = true(호출측이 저장·다시 그리기). */
export function applySeatGroup(m: SeatGroups, key: string | null, group: string | null): { map: SeatGroups; changed: boolean } {
  if (!key) return { map: m, changed: false };
  const g = group?.trim() || null;
  if (g === null) {
    if (!(key in m)) return { map: m, changed: false };
    const { [key]: _, ...rest } = m;
    return { map: rest, changed: true };
  }
  if (m[key] === g) return { map: m, changed: false };
  return { map: { ...m, [key]: g }, changed: true };
}

/** 목록 동기 — 데몬이 값을 가진 좌석만 반영(null = 모름 → 앱 기록 유지). */
export function syncSeatGroupsFromList(
  m: SeatGroups,
  socket: string | null | undefined,
  surfaces: readonly { role?: unknown; cwd?: unknown; group?: unknown }[],
): { map: SeatGroups; changed: boolean } {
  let map = m;
  let changed = false;
  for (const s of surfaces) {
    if (typeof s.group !== "string" || !s.group.trim()) continue;
    const r = applySeatGroup(map, seatGroupKey(socket, typeof s.role === "string" ? s.role : null, typeof s.cwd === "string" ? s.cwd : null), s.group);
    map = r.map;
    changed ||= r.changed;
  }
  return { map, changed };
}
