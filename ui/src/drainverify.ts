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
      body: "지금 판은 저장이 끝났는지 확인하는 기능이 없어, 저장을 한 번 요청한 뒤 확인 없이 재시작합니다.",
    };
  }
  return {
    title: "⚠ 저장 검증 실패",
    body: "저장이 끝났는지 확인하지 못해, 저장을 한 번 요청한 뒤 확인 없이 재시작합니다. 다시 켜진 뒤 각 창이 하던 일을 이어 가는지 살펴봐 주세요.",
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
// ★v115r5-t1 T1②: 사람이 읽는 알림 문구라 괄호 부기·내부 용어(마커·시간초과·구버전 데몬)를 뺀 쉬운 말.
export const OUTCOME_LABEL: Record<string, string> = {
  saved: "저장 확인",
  timeout: "제시간에 저장을 확인하지 못함",
  delivery_failed: "저장 지시가 전달되지 않음",
  unverifiable: "옛 판이라 확인할 수 없음",
  skipped_restoring: "복원 중이라 건너뜀",
};

// 재시작 뒤 알림 — 전원 마커 확인이면 null(알릴 것이 없다 · 조용한 성공).
// ★v115r5-t1 T1②: 이 알림은 **재시작 전** 저장 확인 결과만 말한다. ⑴ 확인 못 함(timeout)을 「저장을 못 했다」로
//   단정하지 않는다(자리가 늦게 저장했을 수 있다 — VM r3 행정부 부서장은 첫 지시 처리 중이었다) ⑵ 「대화는
//   복원했다」를 약속하지 않는다 — 드레인은 재시작 **전** 단계라 복원 결과를 모른다. 대화 이어짐은 재시작 뒤
//   실측 알림(continuityNotice)만 말한다. ⑶ 자리 번호는 재시작 전 번호라 뒤에는 없는 자리를 가리킨다 — 뺀다.
export function drainVerifyNotice(r: DrainVerifyReportLite): { title: string; body: string } | null {
  if (r.all_saved) return null;
  const bad = r.nodes.filter((n) => n.outcome !== "saved");
  if (!bad.length) return null;
  const seats = bad
    .map((n) => `${n.department ? n.department + " " : ""}${n.role} — ${OUTCOME_LABEL[n.outcome] ?? n.outcome}`)
    .join(" · ");
  const waited = r.max_wait_secs ? `최대 ${r.max_wait_secs}초까지 기다렸어요. ` : "";
  return {
    title: "재시작 전에 저장을 확인하지 못한 자리가 있어요",
    body: `자리 ${bad.length}개는 재시작 전에 마지막 저장을 확인하지 못했어요. ${waited}${seats}`,
  };
}

// ── ★v115r5-t1 T1③: 재시작 뒤 대화 이어짐 알림(실측 파생) ─────────────────────
// 원천 = tauri restart_continuity(각 데몬 phoenix 원장의 **이번 회차** 대조). 새 대화로 시작한 자리가 있을 때만
// 알린다 — 전원 이어짐이면 조용한 성공, 아직 판정 전(unsettled)인 자리는 어느 쪽으로도 말하지 않는다.
// 사람이 할 일은 없으므로 할 일을 만들지 않는다.
export type ContinuitySeat = { place: string; role: string };
export type ContinuityReport = { fresh: ContinuitySeat[]; unsettled: ContinuitySeat[]; continued: number };

export function continuityNotice(r: ContinuityReport | null | undefined): { title: string; body: string } | null {
  const fresh = r?.fresh ?? [];
  if (!fresh.length) return null;
  const seats = fresh.map((s) => `${s.place ? s.place + " " : ""}${s.role}`).join(" · ");
  return {
    title: "일부 자리는 새 대화로 시작했어요",
    body: `${seats} 자리는 이전 대화를 잇지 못해 새 대화로 시작했어요.`,
  };
}

// ★v113-restore B3: 갱신 직후 ↻ 는 복원이 아직 도는 자리를 「복원 중 — 건너뜀」으로 돌려준다(893 VM · DRAIN 1/3).
// 사용자가 다시 누르지 않아도 되게, 그 자리만 잠시 뒤 한 번 더 저장시킨다 — 이미 저장한 자리엔 지시를 또 넣지 않는다.
// 키 = 코어 `cys drain --verify --only` 형식(`<dept>/<surface>`). dept 가 없으면(구 코어) 재시도 대상에서 뺀다.
export type DrainRetryNode = DrainVerifyNodeLite & { dept?: string };

export function restoringRetryKeys(nodes: DrainRetryNode[]): string[] {
  return nodes
    .filter((n) => n.outcome === "skipped_restoring" && n.dept)
    .map((n) => `${n.dept}/${n.surface}`);
}

// 재시도 결과를 첫 결과에 겹친다 — 같은 자리(키 일치)는 재시도 쪽이 이기고, 요약·all_saved 는 합친 자리로 다시 센다.
export function mergeRetry<R extends { all_saved: boolean; total: number; summary: Record<string, number>; nodes: DrainRetryNode[] }>(
  first: R,
  retry: { nodes: DrainRetryNode[] },
): R {
  const key = (n: DrainRetryNode) => `${n.dept ?? ""}/${n.surface}`;
  const redo = new Map(retry.nodes.map((n) => [key(n), n]));
  const nodes = first.nodes.map((n) => redo.get(key(n)) ?? n);
  const summary: Record<string, number> = {};
  for (const k of Object.keys(first.summary)) summary[k] = 0;
  for (const n of nodes) summary[n.outcome] = (summary[n.outcome] ?? 0) + 1;
  return { ...first, nodes, summary, all_saved: nodes.length > 0 && nodes.every((n) => n.outcome === "saved") };
}
