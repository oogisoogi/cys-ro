// notifypolicy.ts — BA3 「지금 그 좌석을 보고 있으면 알림 생략」 한 규칙(TICKET=cysr-1119-s9 · DESIGN §7 BA3 · 결정 ③ 줄인 판).
// 순수 판정만 — 「보고 있음」·「앱 앞」 사실은 main.ts 가 모아 넘긴다(seatViewedNow · appInFront).
// 종류별 켜기/끄기 설정 줄·시험 알림 = 1.1.20(새 메뉴 성격) · 데몬 신호 0(BA4 = 1.1.20).

/** 되돌리기 스위치 — false 면 언제나 냄(1.1.18 꼴). */
export const NOTIFY_SKIP_WHEN_VIEWED = true;

/** 알림 종류 넷 = (확인 필요 · 끝남) × (앱 안 토스트 · OS 배너). 1.1.18 에 「끝남 OS 배너」 자리는 없다(판정표에만 있다). */
export const NOTIFY_KINDS = ["needs_you.toast", "needs_you.os", "finished.toast", "finished.os"] as const;
export type NotifyKind = (typeof NOTIFY_KINDS)[number];

export interface NotifyFacts {
  kind: NotifyKind;
  /** 그 좌석이 지금 화면에 보인다(작업 화면 · 지금 작업공간 · 탭·넓게 보기로 숨지 않음) */
  viewed: boolean;
  /** 앱 창이 앞에 있다(문서 보임 ∧ 창 초점) */
  appFront: boolean;
}

/** 알림을 내는가. 생략 = 「보고 있음 ∧ 앱 앞」 하나뿐 — 앱이 뒤에 있으면 좌석이 떠 있어도 사람은 못 보고 있다. */
export function notifyAllowed(f: NotifyFacts, skipWhenViewed: boolean = NOTIFY_SKIP_WHEN_VIEWED): boolean {
  if (!skipWhenViewed) return true;
  return !(f.viewed && f.appFront);
}
