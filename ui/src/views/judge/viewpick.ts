// (cysr-ui-slice1) 어느 화면으로 시작하나 · 대화 화면을 이 기기에서 쓸 수 있나 — 순수(P2-DESIGN §10 · §9-3).
//
// §10 【개정 11-17 21:3x · 박사님 「권고대로 한다. 1.1.16도 바로 진행하라.」】 1.1.16 = 새·기존 설치 **모두 작업 화면**으로 시작.
// 사람이 전환 단추로 고른 화면만 `cys-view` 에 기억한다(다음 실행도 그 화면). 저장 값이 없거나·깨졌거나·없는 화면이면 작업 화면.
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지.

export const VIEW_KEY = "cys-view";
export const DEFAULT_VIEW = "work";

export interface StoredView {
  v: 1;
  id: string;
  decidedBy: "user";
}

/** 저장 원문(문자열 또는 null) → 고를 화면 id. 등록된 화면이 아니면 작업 화면(NFR-T4 · 애매하면 바꾸지 않는 쪽). */
export function pickView(raw: string | null, registered: readonly string[]): string {
  if (raw === null) return DEFAULT_VIEW;
  let o: unknown;
  try {
    o = JSON.parse(raw);
  } catch {
    return DEFAULT_VIEW;
  }
  const id = (o as { v?: unknown; id?: unknown } | null)?.id;
  if ((o as { v?: unknown } | null)?.v !== 1 || typeof id !== "string") return DEFAULT_VIEW;
  return registered.includes(id) ? id : DEFAULT_VIEW;
}

export function storedViewText(id: string): string {
  const s: StoredView = { v: 1, id, decidedBy: "user" };
  return JSON.stringify(s);
}

/** 이름 보고자 「마스터」가 최근이면 cys 밖 마스터(cmux 등)로 본다(설계 목표값 10분). */
export const NAMED_MASTER_FRESH_SECS = 600;

/** §9-3 「대화 화면 불가 = 긍정 신호가 있을 때만」: 이름 보고자에 마스터가 최근 있음 ∧ 살아 있는 cys 마스터 좌석 없음.
 *  새 설치(좌석 0)·마스터 꺼짐·이름 보고 없음(참가자 기기 기본 — 0.5 M11) = 늘 가능. 모름(조회 실패) = 가능(흐림 0 · 띠로 안내). */
export function chatAvailability(named: unknown, liveCysMaster: boolean | null, nowSecs: number): { ok: true } | { ok: false; why: string } {
  if (liveCysMaster !== false) return { ok: true };
  if (!Array.isArray(named)) return { ok: true };
  const fresh = named.some((r) => {
    const o = r as { name?: unknown; updated_at?: unknown } | null;
    return !!o && o.name === "master" && typeof o.updated_at === "number" && nowSecs - o.updated_at <= NAMED_MASTER_FRESH_SECS;
  });
  return fresh ? { ok: false, why: "이 컴퓨터의 마스터는 cysr 밖에서 돌고 있어요 — 대화 화면은 cysr 안의 마스터와만 이야기할 수 있어요." } : { ok: true };
}
