// drain_verify 폴백 원인 분류 — 순수 함수(main.ts의 재시작 흐름이 배선만 한다).
//
// [F5] tauri drain_verify 커맨드는 JSON을 못 내면 Err 문자열 접두로 원인을 신호한다:
//   "unsupported:"  = 구버전 cys 바이너리(--verify 미지원, clap unknown-flag)
//   "verify_failed:" = 실행은 됐으나 크래시/하드캡 백스톱으로 결과 미산출
// 두 경우 모두 거동은 plain drain 폴백으로 동일하고, UI 문구만 정직하게 분기한다("무손실" 표현 없음).
// 그 외(알 수 없는 에러)는 null → 호출측이 rethrow(폴백 아님).

export type DrainVerifyFallback = "unsupported" | "verify_failed" | null;

export function classifyDrainVerifyFallback(errMsg: string): DrainVerifyFallback {
  if (errMsg.includes("unsupported")) return "unsupported";
  if (errMsg.includes("verify_failed")) return "verify_failed";
  return null;
}

// 폴백 사유별 사용자 토스트 문구(제목·본문). 거동은 동일하나 원인을 정직하게 알린다.
export function drainVerifyFallbackToast(reason: "unsupported" | "verify_failed"): {
  title: string;
  body: string;
} {
  if (reason === "unsupported") {
    return {
      title: "⚠ 저장 검증 미지원",
      body: "현재 cys 버전은 저장 검증을 지원하지 않습니다 — 기존 방식(best-effort 저장)으로 재시작합니다.",
    };
  }
  return {
    title: "⚠ 저장 검증 실패",
    body: "저장 검증 실행에 실패했습니다(원인 미상) — 기존 방식(best-effort 저장)으로 재시작합니다. 재시작 후 노드 상태를 점검하세요.",
  };
}

// ── ★[V111-F4] 재시작 뒤 알림 1줄(확인 창 폐기) ──────────────────────────────
// 오너 최상위 원칙(2026-09-21): 「한 번 누르면 재시작까지 한 번에 · 중간에 묻는 단계를 모두 삭제」.
// 그래서 구 「일부 노드 저장 미확인 … 그래도 재시작하시겠습니까?」 확인 창은 없앴다 — 드레인은 상한
// (max_wait_secs) 안에서 자동 재조회·연장하고, 상한 뒤엔 묻지 않고 재시작한다. 결과는 **재시작 뒤**
// 알림 한 줄로만 알린다(사람이 고를 것이 없는 사실 통보라 모달일 이유가 없다).
export type DrainVerifyNodeLite = {
  role: string;
  department?: string;
  surface: string;
  outcome: string;
  detail?: string;
};
export type DrainVerifyReportLite = {
  all_saved: boolean;
  total: number;
  summary: { saved: number };
  nodes: DrainVerifyNodeLite[];
  max_wait_secs?: number;
};

// ★[F2] 검증은 nonce '마커 기입'만 확인한다 — 내용 최신성은 노드 책임이라 라벨을 과대주장하지 않는다.
// ★[V111-F2] "입력 미제출"은 입력창 앵커 실측일 때만 붙는다(코어가 판정) — 못 잰 것은 timeout 으로 온다.
export const OUTCOME_LABEL: Record<string, string> = {
  saved: "체크포인트 마커 확인",
  timeout: "마커 미확인(시간초과)",
  delivery_failed: "지시 전달 실패(입력 미제출 실측)",
  unverifiable: "검증 불가(구버전 데몬)",
  skipped_restoring: "복원 중 — 건너뜀",
};

// 재시작 뒤 알림 — 전원 마커 확인이면 null(알릴 것이 없다 · 조용한 성공).
export function drainVerifyNotice(r: DrainVerifyReportLite): { title: string; body: string } | null {
  if (r.all_saved) return null;
  const bad = r.nodes.filter((n) => n.outcome !== "saved");
  if (!bad.length) return null;
  const seats = bad
    .map((n) => `${n.department ? n.department + " / " : ""}${n.role}(${n.surface}) ${OUTCOME_LABEL[n.outcome] ?? n.outcome}`)
    .join(" · ");
  const waited = r.max_wait_secs ? `최대 ${r.max_wait_secs}초까지 기다렸습니다. ` : "";
  return {
    title: "재시작 완료 — 일부 자리는 마지막 저장을 못 했어요",
    body:
      `자리 ${bad.length}개는 마지막 저장을 확인하지 못했지만 대화는 트랜스크립트로 복원했어요. ` +
      `${waited}${seats}`,
  };
}
