// 워크스페이스 탭의 **보여 주는 이름** — 판정부(D4 #4 · TICKET=v116-ui-close · master 판정 master#849929fc = A).
//
// ★저장값은 그대로다: 이름 없는 탭의 저장 이름은 계속 UNTITLED(「non title」)이고, 화면 배치 저장본·부서 표시명 회복
//   판정(main.ts 복원 경로의 `ws.name === UNTITLED`)은 그 값을 본다. 여기서는 **보여 줄 때만** 바꾼다 — 저장본 이행 0.
// ★「본부」는 하나다: 이름 없는 기본 데몬 탭이 여럿이면(＋ 새 워크스페이스) 모두 「본부」로 부르면 거짓이 된다.
//   판정 = 마스터 좌석이 있는 기본 데몬 탭 → 그 정보를 모르면 첫째 기본 데몬 탭(폴백). 나머지 이름 없는 탭 = 「새 화면」.

export const HQ_LABEL = "본부";
export const UNNAMED_LABEL = "새 화면";

export interface WsBrief {
  id: number;
  /** 부서 탭이면 그 부서 데몬 소켓. 없으면(undefined·null) 기본 데몬 탭. */
  socket?: string | null;
  pending?: boolean;
  /** 그 탭 화면에 있는 창 번호들. */
  sids: readonly number[];
}

/**
 * 「본부」로 부를 탭의 id. ① 기본 데몬 탭 중 마스터 좌석(masterSids)을 가진 첫 탭 ② 마스터 정보를 모르거나
 * (null) 어느 탭에도 없으면 가장 먼저 만든(id 최소) 기본 데몬 탭 ③ 기본 데몬 탭이 없으면 null.
 * ★둘째 기본 탭이 「본부」를 빼앗지 않게 ①이 ②보다 먼저다(master 보강 1).
 */
export function hqWorkspaceId(wss: readonly WsBrief[], masterSids: ReadonlySet<number> | null): number | null {
  const base = wss.filter((w) => !w.socket && !w.pending);
  if (masterSids && masterSids.size) {
    const withMaster = base.find((w) => w.sids.some((sid) => masterSids.has(sid)));
    if (withMaster) return withMaster.id;
  }
  // (Fable 2R) 폴백은 배열 순서가 아니라 **가장 먼저 만든 탭(id 최소)** — 탭을 끌어 순서를 바꿔도 본부가 옮겨 가지 않게.
  return base.length ? base.reduce((a, b) => (b.id < a.id ? b : a)).id : null;
}

/** 보여 줄 이름. 사람이 붙인 이름(저장값 ≠ untitled · 비지 않음)은 그대로 — 이름 없는 탭만 「본부」/「새 화면」. */
export function wsDisplayName(name: string | null | undefined, untitled: string, isHq: boolean): string {
  const n = (name ?? "").trim();
  if (n && n !== untitled) return n;
  return isHq ? HQ_LABEL : UNNAMED_LABEL;
}

/**
 * 탭 이름 편집을 마쳤을 때 저장할 값. 비우면 untitled(종전). ★보여 주던 자동 이름(「본부」·「새 화면」)을 그대로 두고
 * 편집만 끝냈다면 저장값은 **untitled 그대로** — 안 그러면 더블클릭 한 번으로 자동 이름이 저장 이름으로 굳어,
 * 부서 표시명 회복·본부 판정 이동이 그 탭에서 멈춘다.
 */
export function renamedName(input: string, shownBefore: string, prevName: string, untitled: string): string {
  const v = input.trim();
  if (!v) return untitled;
  if (prevName === untitled && v === shownBefore) return untitled;
  return v;
}
