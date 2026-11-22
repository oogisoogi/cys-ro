// (cysr-ui-slice3) 기계 문안(깨움 말·1회 안내 = 데몬 큐 항목) 단계 판정 — 순수(P2-DESIGN §5-1 「보낸 말(기계 문안) 단계」 줄).
//
// 사람 말과 달리 기계 문안은 데몬 큐를 탄다 — 단계의 근거는 데몬이 이미 방송하는 큐 사건뿐이다(새 조회 0 · 데몬 변경 0).
// 사건 칸 이름은 이 판(3a012bf4) 데몬 코드에서 확인한 그대로다:
//   queue.delivered      {queue_entry_id, merged_ids[]}                (governance.rs queue_delivered_payload · state.rs:605~621)
//   queue.inject_aborted {queue_entry_id, merged_ids[], disposed_ids[]} (governance.rs:11899·12199 — merged−disposed = 큐에 그대로 · 다음 틱 재시도)
//   queue.write_held     {entry_ids[] = merged_ids, reason, kind}       (governance.rs:12344~12360 — 입력줄에 반쯤 남음)
//   queue.write_released {entry_ids[], released:"composer_empty"}      (governance.rs:12806 — 「미배달로 풀림 · 다시 치지 않음」)
//   queue.dropped        {queue_entry_ids[], reason}                    (state.rs:529~560)
//   queue.expired        {queue_entry_id}                               (state.rs:969~991)
//   queue.parked         {queue_entry_ids[]}                            (state.rs:762~769 — 역할 좌석이 없어 보존 · 다시 켜지면 전달)
//   queue.rehomed        {queue_entry_ids[]}                            (state.rs:714~723 — 같은 번호로 새 좌석 큐에)
//   queue.revived        {queue_entry_id}                               (state.rs:997~1011 — 만료분이 다시 큐로)
//   queue.starved        {surface_ref · 항목 번호 없음}                   (governance.rs:11523 — 큐 머리가 600초 넘게 막힘)
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지(시각은 인자).

import { MEASURED_QUEUE_HOLD_AFTER_HUMAN_SECS } from "./gate";

export type AutoStep = "queued" | "retrying" | "partial" | "parked" | "delivered" | "failed" | "expired" | "unknown" | "slow";

export const AUTO_STEP_LABEL: Record<AutoStep, string> = {
  queued: "차례 기다림",
  retrying: "다시 시도 중(차례 기다림)",
  partial: "입력줄에 반쯤 남음 · 확인 중",
  parked: "마스터가 다시 켜지면 전달",
  delivered: "전달됨",
  failed: "못 보냄",
  expired: "못 보냄(기다리다 만료 · 되살아나면 다시 차례)",
  unknown: "전달 여부를 알 수 없어요(입력줄이 비어 풀림)",
  slow: "확인이 오래 걸려요",
};

export interface AutoMsg {
  /** 데몬 큐 항목 번호(chat_send{kind:auto} 응답의 queue_entry_id) */
  entryId: string;
  /** 적재한 좌석 */
  seat: number;
  step: AutoStep;
  /** 이 항목에 반영한 마지막 사건 seq(늦게 온 옛 사건이 새 단계를 덮지 않게 · §5-1 공통 규칙) */
  lastSeq: number;
  /** 못 보냄·반쯤 남음의 까닭(데몬 reason·why 원문 · 화면은 쉬운 말로 바꿔 보임) */
  why?: string;
}

export interface QueueEvent {
  name: string;
  seq: number | null;
  surfaceId: number | null;
  payload: Record<string, unknown>;
}

/** 데몬 사건(IPC 값 · 전부 의심) → QueueEvent · queue.* 가 아니면 null. */
export function queueEventOf(raw: unknown): QueueEvent | null {
  const e = raw as { name?: unknown; seq?: unknown; surface_id?: unknown; payload?: unknown } | null;
  if (!e || typeof e.name !== "string" || !e.name.startsWith("queue.")) return null;
  const seq = typeof e.seq === "number" && Number.isSafeInteger(e.seq) ? e.seq : null;
  const surfaceId = typeof e.surface_id === "number" && Number.isSafeInteger(e.surface_id) ? e.surface_id : null;
  const payload = e.payload && typeof e.payload === "object" ? (e.payload as Record<string, unknown>) : {};
  return { name: e.name, seq, surfaceId, payload };
}

const FINAL: ReadonlySet<AutoStep> = new Set<AutoStep>(["delivered", "failed"]);

function ids(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

/** 이 사건이 이 항목에 주는 단계 · 관계없으면 null. 조건마다 한 줄 = 뮤턴트 시험 단위. */
export function autoStepFor(a: AutoMsg, ev: QueueEvent): { step: AutoStep; why?: string } | null {
  const p = ev.payload;
  const id = a.entryId;
  switch (ev.name) {
    case "queue.delivered":
      return p.queue_entry_id === id || ids(p.merged_ids).includes(id) ? { step: "delivered" } : null;
    case "queue.inject_aborted":
      if (ids(p.disposed_ids).includes(id)) return { step: "failed", why: typeof p.why === "string" ? p.why : "disposed" };
      return ids(p.merged_ids).includes(id) || p.queue_entry_id === id ? { step: "retrying" } : null;
    case "queue.write_held":
      return ids(p.entry_ids).includes(id) ? { step: "partial", why: typeof p.reason === "string" ? p.reason : undefined } : null;
    case "queue.write_released":
      // 데몬: 「입력줄이 비어 미배달로 풀림 · 다시 치지 않음」 — 사람이 그 반쯤 쓴 글을 Enter 로 보냈을 수도 있다(검토 지적 6) → 못 보냄이라 단정하지 않음.
      return ids(p.entry_ids).includes(id) ? { step: "unknown", why: "released_composer_empty" } : null;
    case "queue.dropped":
      return ids(p.queue_entry_ids).includes(id) ? { step: "failed", why: typeof p.reason === "string" ? p.reason : "dropped" } : null;
    case "queue.expired":
      return p.queue_entry_id === id ? { step: "expired", why: "expired" } : null; // 만료분은 queue.revived 로 되살아날 수 있다(검토 지적 3)
    case "queue.parked":
      return ids(p.queue_entry_ids).includes(id) ? { step: "parked" } : null;
    case "queue.rehomed":
      return ids(p.queue_entry_ids).includes(id) ? { step: "queued" } : null;
    case "queue.revived":
      return p.queue_entry_id === id ? { step: "queued" } : null;
    case "queue.starved":
      // 항목 번호가 없다 — 그 좌석에서 아직 기다리는 항목만 「오래 걸려요」(반쯤 남음·보존은 그 까닭이 더 정확해서 그대로).
      return ev.surfaceId === a.seat && (a.step === "queued" || a.step === "retrying") ? { step: "slow" } : null;
    default:
      return null;
  }
}

/** 사건 하나를 추적 중인 기계 문안들에 반영(순수 · 입력 불변). 끝난 항목(전달됨·못 보냄)은 바뀌지 않는다 · seq 가 거꾸로 온 사건은 무시. */
export function applyQueueEvent(autos: readonly AutoMsg[], ev: QueueEvent): AutoMsg[] {
  return autos.map((a) => {
    if (FINAL.has(a.step)) return a;
    if (ev.seq !== null && ev.seq <= a.lastSeq) return a;
    const r = autoStepFor(a, ev);
    if (!r) return a;
    return { ...a, step: r.step, why: r.why, lastSeq: ev.seq ?? a.lastSeq };
  });
}

/** R3(0.5 M10): 사람 보내기 뒤 마스터로 가는 큐 배달이 묶이는 시간(ms · 실측 31.2초). */
export const AUTO_HOLD_AFTER_HUMAN_MS = Math.round(MEASURED_QUEUE_HOLD_AFTER_HUMAN_SECS * 1000);

/** R3: 마지막 사람 보내기(lastHumanSentAt) 뒤 기계 문안이 데몬 큐에서 묶여 있을 남은 시간(ms · 0 = 묶임 없음).
 *  기계 문안을 보내는 쪽(조각 5 깨움)은 이 값이 0 일 때 보내고, 「차례 기다림」 줄은 이 값으로 「약 N초」를 보인다. */
export function autoHoldRemainingMs(lastHumanSentAt: number | null, now: number): number {
  if (lastHumanSentAt === null) return 0;
  return Math.max(0, lastHumanSentAt + AUTO_HOLD_AFTER_HUMAN_MS - now);
}
