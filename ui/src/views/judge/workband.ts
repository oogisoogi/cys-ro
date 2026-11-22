// (cysr-1116-s79 · TICKET=cysr-1116-s79-1119) 작업 화면 띠 고르기 — 순수. P2-DESIGN §11 조각 9 · §4-3 · PRD FR-C7 · 걸어 보기 2차 #w1-ask · #w1-draft.
//
// 띠는 하나(확인 띠가 먼저 · 그다음 대화 초안 알림):
//  ① 확인 대기 = 대화 화면 띠와 **같은 판정**(judge/confirms.bandOf 결과를 그대로 받음 · 같은 판정을 두 화면이 따로 만들지 않음 §3-3 ④).
//     작업 화면에서의 행동 = 「마스터 창에서 답하기」(마스터 창으로 포커스) · 도우미 허락은 「도우미 창에서 답하기」(그 좌석으로) — 쉬운 화면으로 데려가지 않음.
//  ② 대화 초안 = 대화 화면 입력칸에 보내지 않은 글이 있음 → 「대화 화면에 쓰다 만 말이 있어요」(마스터 창 입력줄에는 넣지 않음 · 4군 ②).
// 모름(확인 대기를 다 못 훑음)이고 항목 0 이면 띠 0 — 작업 화면에는 이미 승인 요청 표지(#cc-pending-badge)가 있다(모름을 「없음」으로도, 「살펴보는 중」 띠로도 칠하지 않음).
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지.

import type { Band, BandItem } from "./confirms";

export type WorkBand =
  | { kind: "confirm"; item: BandItem; count: number; known: boolean; seat: number | null; text: string; action: string }
  | { kind: "draft"; text: string; action: string };

export const WORK_DRAFT_TEXT = "대화 화면에 쓰다 만 말이 있어요. 마스터 창에는 넣지 않았어요.";
export const WORK_DRAFT_ACTION = "대화 화면에서 이어 쓰기";
export const WORK_ANSWER_MASTER = "마스터 창에서 답하기";
export const WORK_ANSWER_HELPER = "도우미 창에서 답하기";

/** 띠 하나 고르기 · masterSid = 지금 마스터 좌석(모름·없음 = null — 단추는 그래도 보이되 누르면 안내). */
export function pickWorkBand(band: Band | null, draft: string, masterSid: number | null): WorkBand | null {
  const items = band?.items ?? [];
  if (band && items.length > 0) {
    const it = items[0];
    const count = items.length;
    const more = band.known ? "" : " · 더 살펴보는 중";
    const head = `확인이 필요해요 ${count}${more}`;
    if (it.kind === "ask") return { kind: "confirm", item: it, count, known: band.known, seat: masterSid, text: `${head} — 마스터가 물어요: ${it.q.text}`, action: WORK_ANSWER_MASTER };
    if (it.kind === "master_screen") return { kind: "confirm", item: it, count, known: band.known, seat: it.a.surface_id, text: `${head} — 마스터 창에 확인할 것이 떠 있어요.`, action: WORK_ANSWER_MASTER };
    return { kind: "confirm", item: it, count, known: band.known, seat: it.a.surface_id, text: `${head} — 도우미가 허락을 기다려요.`, action: WORK_ANSWER_HELPER };
  }
  if (draft.trim()) return { kind: "draft", text: WORK_DRAFT_TEXT, action: WORK_DRAFT_ACTION };
  return null;
}
