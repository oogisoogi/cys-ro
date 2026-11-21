// ★seatkeep-t1(codex 3R ④) — 조직 복원 「done」 알림 한 장을 고르는 순수 도우미(종전 main.ts 안의 같은 갈래를 옮김 · 문안 바이트 같음).
// 더한 것 하나: `pending`(죽은 부서를 다시 켰지만 자동 복원이 상한 안에 안 끝나 결과를 확인하지 못한 부서 수) — 성공도 실패도 아니므로
// 「✅ 직원 복귀 완료」를 내지 않고 「진행 중」으로 말한다(부서 알림 「OO: 다시 켰지만 … 확인하지 못했습니다」와 어긋나지 않게).
import { deptRegistryUnreadableNote } from "./deptreg";

export type RestoreDonePayload = {
  hq_ok?: boolean;
  hq_pending?: boolean; // 대기 상한을 넘겨 본부 좌석을 자동 복원이 아직 세우는 중
  hq_note?: string | null;
  ok?: number;
  fail?: number;
  pending?: number; // ★codex 3R ④: 다시 켰지만 결과를 확인하지 못한 부서 수(성공·실패 어느 쪽에도 세지 않음)
  depts_unreadable?: string | null;
};

export type RestoreDoneToast = { category: "health" | "watchdog"; name: string; detail: string };

export function restoreDoneToast(p: RestoreDonePayload): RestoreDoneToast {
  const ok = p.ok ?? 0;
  const fail = p.fail ?? 0;
  const pending = p.pending ?? 0;
  // 결함1: 부서가 있어도 본부(HQ) 복원 실패가 묻히지 않게 hq_ok===false를 health로 승격.
  // ★v113-restore: 본부 쪽은 실제 사정(실패·관문 대기·실행 불가)을 백엔드가 hq_note 로 준다.
  if (p.hq_ok === false)
    return { category: "health", name: "⚠ 본부 복원 확인 필요", detail: `${p.hq_note ?? "본부 복원이 끝나지 않았습니다."} (부서 성공 ${ok} · 실패 ${fail})` };
  if (fail > 0) return { category: "health", name: "⚠ 직원 복귀 일부 실패", detail: `부서 복원 성공 ${ok} · 실패 ${fail} — 상태를 점검하세요.` };
  // ①(Fable R2 A) 부서 목록을 못 읽어 부서 복원을 건너뛰었으면 「완료」 가 아니다.
  if (p.depts_unreadable) return { category: "health", name: "⚠ 부서 복원 건너뜀", detail: deptRegistryUnreadableNote(p.depts_unreadable) };
  if (p.hq_pending) return { category: "watchdog", name: "👥 직원 복귀 진행 중", detail: "본부 좌석은 자동 복원이 이어서 세웁니다. 실패하면 알림으로 알려 드립니다." };
  if (pending > 0)
    return {
      category: "watchdog",
      name: "👥 직원 복귀 진행 중",
      detail: `부서 ${pending}곳은 다시 켰지만 직원 자리 복귀가 아직 끝나지 않아 결과를 확인하지 못했습니다 — 잠시 뒤 ↻ 재시작을 눌러 다시 확인하세요.`,
    };
  return { category: "watchdog", name: "✅ 직원 복귀 완료", detail: `노드 세션 복원 완료 (부서 ${ok}).` };
}

/** 옛 자리 쓸기를 무장해도 되는가 — 본부·부서 어느 쪽이든 자동 복원이 아직 도는 중이면 아니다(in-seat 재연결 중인 좌석을 쓸지 않는다 · 794 r3). */
export function restoreDoneMaySweep(p: RestoreDonePayload): boolean {
  return !p.hq_pending && !(p.pending ?? 0);
}

// ★seatkeep-t1(r4 B → r5 축소 · codex r4 #4·#5·#6·#8) — 후속 감시는 **끝점별로만** 말한다: 확인됨(`followup-ok`) · 사정(`skip`) ·
// 확인 못 함(`followup-end` 의 `unconfirmed`). 조직 전체 「✅ 직원 복귀 완료」와 옛 자리 쓸기 무장은 이 회차의 첫 결과(`done`)만 정한다 —
// 늦은 성공이 첫 실패를 덮지 않는다(#6). 확인 못 함은 8초 알림이 아니라 sticky(#8) · 다음 복원 회차 시작에서 걷는다.

/** sticky id — 확인 못 한 끝점 안내(다음 회차 `start` 가 걷는다). */
export const RESTORE_UNCONFIRMED_TOAST_ID = "restore-unconfirmed";

/** 늦게 끝난 그 끝점의 자동 복원을 판정 층이 성공으로 확인했다 — 그 끝점만(조직 전체 「완료」 아님). */
export function followupConfirmedToast(place: string): RestoreDoneToast {
  return { category: "watchdog", name: `👥 ${place} 직원 복귀 확인됨`, detail: "늦게 끝난 자동 복원을 확인했습니다." };
}

export type FollowupEndPayload = { unconfirmed?: string[] };

/** 후속 감시 끝 — 확인 못 한 끝점이 있으면 sticky 한 장(무슨 일 + 무엇을 누르면 되는지) · 없으면 없음. 「완료」 낱말 0. */
export function followupEndToast(p: FollowupEndPayload): RestoreDoneToast | null {
  const places = (p.unconfirmed ?? []).filter((x) => typeof x === "string" && x.length > 0);
  if (!places.length) return null;
  return {
    category: "health",
    name: "⚠ 직원 복귀를 확인하지 못함",
    detail: `${places.join(" · ")}의 자동 복원이 끝났는지 아직 확인하지 못했습니다 — 잠시 뒤 ↻ 재시작을 눌러 다시 확인하세요.`,
  };
}

/** 회차 번호(`round`)가 지금 회차보다 작은 복원 이벤트 = 옛 회차의 것 → 버린다(#5). 번호 없는 이벤트(옛 백엔드·회차 밖 알림)는 버리지 않는다. */
export function restoreEventIsStale(round: number | undefined, current: number): boolean {
  return typeof round === "number" && round < current;
}
