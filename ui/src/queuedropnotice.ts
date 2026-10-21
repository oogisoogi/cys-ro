// 좌석 닫힘 큐 폐기 알림(순수 모듈 · TICKET=cysr-1110-winqueue Q1-A ① · master#904c96af 2026-10-21).
//
// 사람이 좌석(창)을 닫으면 그 좌석에 아직 전달되지 않은 지시는 버려진다(정책 유지 — 데몬 원장에 묘비는 남는다).
// 종전에는 그 사실이 화면에 0 이었다(윈 1.1.9 실기 W-2 10-17 02:1x · 박사님이 닫은 창의 큐 2건 소멸).
// 데몬 `queue.dropped` 이벤트가 **사람 닫기**(`owner_close=true`)이고 1건 이상일 때만 1줄을 낸다 — 회수(Reap)·0건은 알림 0.
// 문구는 왕초보 말투 · 위협 표현 금지(master 지시). payload 는 신뢰하지 않는다(타입 검사).
// 경보 숨김 스위치(ALERTS_QUIET · alertquiet.ts)를 따른다 — main.ts 가 데몬 출처 래퍼 daemonToast 로 낸다(1.1.10 통합 cysr-1110-integrate 연결 · 시험 toastaxis 두 값).

export interface QueueDropNotice {
  title: string;
  detail: string;
}

export function queueDropNotice(payload: unknown): QueueDropNotice | null {
  if (!payload || typeof payload !== "object") return null;
  const p = payload as Record<string, unknown>;
  if (p.owner_close !== true) return null;
  const n = typeof p.count === "number" && Number.isInteger(p.count) ? p.count : 0;
  if (n < 1) return null;
  return { title: `대기 중이던 지시 ${n}건을 버렸습니다(기록은 남아 있습니다)`, detail: "" };
}
