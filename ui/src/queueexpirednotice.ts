// 큐 만료(유실) 알림(순수 모듈 · TICKET=cysr-queued-paste-submit).
//
// 좌석이 입력을 받지 못한 채(입력줄에 미제출 글 · 바쁨 등) 큐 항목이 TTL(기본 6시간)을 넘기면 활성 큐에서 빠진다(보존은 된다).
// 종전에는 이 사실이 화면에 0 이었다 — 데몬 `queue.expired` 를 GUI 가 starved 머리 기억 정리에만 썼다(윈 base 10-13 00:28 실례:
// 부서 보고가 약 6시간 뒤 조용히 사라짐). 오너가 알도록 좌석마다 1줄로 묶어 알린다(같은 좌석의 동시 만료는 한 번에 센다 — main.ts).
// 만료 통지 항목 자신(origin `queue-expired-notice`)의 만료는 알리지 않는다(통지의 통지 연쇄 금지).
// 문구는 왕초보 말투 · 위협 표현 금지. payload 는 신뢰하지 않는다(타입 검사).

export const EXPIRED_NOTICE_ORIGIN = "queue-expired-notice";

export interface QueueExpiredItem {
  surfaceRef: string;
  role: string | null;
}

/** 알릴 만료 1건이면 그 좌석 표기를, 아니면 null. */
export function queueExpiredItem(payload: unknown): QueueExpiredItem | null {
  if (!payload || typeof payload !== "object") return null;
  const p = payload as Record<string, unknown>;
  if (p.origin === EXPIRED_NOTICE_ORIGIN) return null;
  if (typeof p.surface_ref !== "string" || p.surface_ref === "") return null;
  return { surfaceRef: p.surface_ref, role: typeof p.role === "string" && p.role !== "" ? p.role : null };
}

/** 좌석 하나의 만료 n건 → 알림 문구. */
export function queueExpiredNotice(item: QueueExpiredItem, n: number): { title: string; detail: string } {
  const seat = item.role ? `${item.role}(${item.surfaceRef})` : item.surfaceRef;
  return {
    title: `전달하지 못한 메시지 ${n}건이 시간이 지나 대기열에서 빠졌습니다`,
    detail: `${seat} 창이 그동안 입력을 받지 못했습니다. 내용은 보관돼 있어 'cys queue list --expired' 로 볼 수 있습니다`,
  };
}
