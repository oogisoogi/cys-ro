// (cysr-ui-slice1) 사람 말 쓰기 직전 화면 문턱 — 순수(P2-DESIGN §2-5 「화면 문턱 넷」 + 조각 0.5 결과 master 결정 1·2).
//
// 원자 제출은 데몬이 Ctrl-U → 울타리 → Enter 를 한 번에 넣는다. 그래서 문턱이 틀리면 되돌릴 수 없다:
//  · 사람 초안이 있으면 Ctrl-U 가 그 초안을 **거부 없이 지운다**(0.5 숫자 4 · 12바이트 → 0) → 입력줄 빈칸이 유일한 방어.
//  · 데몬의 승인 창 판정(쓰기 직전 · 가로줄 아래 꼬리)과 승인 대기 항목(feed)은 **술어가 다르다**(0.5 숫자 3) → 둘 다 본다.
//    데몬 쪽은 같은 요청 안의 refuse_on_approval 이 보고, 화면은 feed 대기 항목을 본다.
//  · 사람 키 직후는 데몬이 막지 않는다(0.5 M3ⓒ) → `human_idle_secs` 30초 안이면 붙잡는다. 내 직전 보내기도 데몬에는 사람 입력으로
//    찍히지만, 시각만으로는 다른 길 입력과 가를 수 없다(codex 1R major) → 구별하지 않고 같이 붙잡는다(30초 뒤 자동 1건).
// 「모름」(null·조회 실패)은 전부 **붙잡음** 쪽으로 접는다 — 이 문턱은 쓰지 않는 쪽이 안전하다.
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지(views.test.ts 정적 검사).

/** 사람 입력 뒤 큐 배달이 묶이는 시간(데몬 `CYS_QUEUE_HUMAN_QUIET_SECS` 기본 30 · 0.5 M10 실측 = 사람 보내기 뒤 큐 배달 31.16초 · 대조 2.98초).
 *  화면 문턱은 이 창 안의 **다른 길** 사람 입력을 붙잡는다. */
export const HUMAN_QUIET_SECS = 30;
/** 0.5 M10 실측 묶임(초) — 기계 문안을 사람 보내기 뒤 언제 보낼지(조각 5)·「30초 뒤 다시」 문구가 이 값을 쓴다. */
export const MEASURED_QUEUE_HOLD_AFTER_HUMAN_SECS = 31.2;
/** U25(마스터가 답하는 중에 친 말을 Claude Code 가 받아 두는가) — **측정 대기**(0.5 M5 보류).
 *  값이 오면 이 상수만 바꾼다: true = 바쁠 때도 보냄 · false = 못 믿음(마스터가 쉬면 보냄 · 지금 기본값). */
export const U25_BUSY_PASTE_OK: boolean = false;

/** 마스터 좌석 한 줄(org.status 행에서 판정에 쓰는 칸만). null = 데몬이 그 칸을 주지 않음(모름). */
export interface MasterRow {
  surface_id: number;
  exited: boolean;
  agent_alive: boolean | null;
  pending_input_bytes: number | null;
  pending_input_human_bytes: number | null;
  input_paste_open: boolean | null;
  /** 관문(첫기동 등) — null/없음 = 관문 없음 */
  gate_pending: unknown;
  /** null = 사람 입력 없음(데몬이 null 로 줌) · undefined = 칸 자체가 없음(모름) */
  human_idle_secs: number | null | undefined;
  /** 지금 답하는 중(appearance.nodeWorking) */
  working: boolean;
}

export interface GateInput {
  /** undefined = org.status 조회 실패(모름) · null = 마스터 좌석 없음 */
  master: MasterRow | null | undefined;
  /** 이 데몬의 승인 대기(feed kind=approval status=pending) 항목이 걸린 좌석 번호들 · null = feed 조회 실패(모름) */
  approvalSeats: readonly number[] | null;
  busyPasteOk?: boolean;
}

export type GateCode =
  | "status_unknown"
  | "no_master"
  | "agent_dead"
  | "gate_pending"
  | "approval"
  | "approval_unknown"
  | "draft"
  | "input_unknown"
  | "human_recent"
  | "busy";

export type GateVerdict = { ok: true } | { ok: false; code: GateCode; msg: string };

const MSG: Record<GateCode, string> = {
  status_unknown: "마스터 상태를 확인하는 중이에요 — 확인되면 보낼게요.",
  no_master: "마스터가 아직 없어요 — 마스터가 준비되면 보낼게요.",
  agent_dead: "마스터가 꺼져 있거나 상태를 알 수 없어요 — 마스터가 준비되면 보낼게요.",
  gate_pending: "마스터가 시작 확인을 기다리고 있어요 — 작업 화면에서 답해 주시면 그다음에 보낼게요.",
  approval: "마스터 창에 확인할 것이 떠 있어요 — 그 확인이 끝나면 보낼게요.",
  approval_unknown: "확인할 것이 있는지 살펴보는 중이에요 — 확인되면 보낼게요.",
  draft: "마스터 창에 쓰다 만 글이 있어요 — 그 글을 지우지 않으려고 기다려요. 작업 화면에서 그 글을 보내거나 지우면 보낼게요.",
  input_unknown: "마스터 입력줄 상태를 확인하는 중이에요 — 확인되면 보낼게요.",
  human_recent: "마스터 창에 사람 입력이 있은 지 30초가 안 됐어요(방금 보낸 말 포함) — 30초 동안 조용하면 보낼게요.",
  busy: "마스터가 답하는 중이에요 — 끝나면 보낼게요.",
};

const verdict = (code: GateCode): GateVerdict => ({ ok: false, code, msg: MSG[code] });

/** 쓰기 직전 판정 — 하나라도 아니면 쓰지 않는다(붙잡음). 조건마다 한 줄 = 뮤턴트 시험 단위. */
export function sendGate(g: GateInput): GateVerdict {
  const m = g.master;
  if (m === undefined) return verdict("status_unknown");
  if (m === null || m.exited) return verdict("no_master");
  if (m.agent_alive !== true) return verdict("agent_dead");
  if (m.gate_pending !== null && m.gate_pending !== undefined) return verdict("gate_pending");
  if (g.approvalSeats === null) return verdict("approval_unknown");
  if (g.approvalSeats.includes(m.surface_id)) return verdict("approval");
  if (m.pending_input_bytes === null || m.pending_input_human_bytes === null || m.input_paste_open === null || m.human_idle_secs === undefined) return verdict("input_unknown");
  if (m.pending_input_human_bytes > 0 || m.pending_input_bytes > 0 || m.input_paste_open) return verdict("draft");
  if (m.human_idle_secs !== null && m.human_idle_secs < HUMAN_QUIET_SECS) return verdict("human_recent");
  if (m.working && !(g.busyPasteOk ?? U25_BUSY_PASTE_OK)) return verdict("busy");
  return { ok: true };
}

/** org.status 행(IPC 값 · 전부 의심) → MasterRow. 마스터 = role === "master" ∧ !exited(main.ts 와 같은 판정) · 둘 이상이면 번호가 작은 것. */
export function masterRowOf(org: unknown, working: (row: Record<string, unknown>) => boolean): MasterRow | null | undefined {
  const rows = (org as { surfaces?: unknown } | null)?.surfaces;
  if (!Array.isArray(rows)) return undefined;
  const ms = rows
    .filter((r): r is Record<string, unknown> => !!r && typeof r === "object" && (r as { role?: unknown }).role === "master" && (r as { exited?: unknown }).exited !== true)
    .filter((r) => typeof r.surface_id === "number" && Number.isSafeInteger(r.surface_id))
    .sort((a, b) => (a.surface_id as number) - (b.surface_id as number));
  const r = ms[0];
  if (!r) return null;
  const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) && v >= 0 ? v : null);
  const bool = (v: unknown): boolean | null => (typeof v === "boolean" ? v : null);
  return {
    surface_id: r.surface_id as number,
    exited: false,
    agent_alive: bool(r.agent_alive),
    pending_input_bytes: num(r.pending_input_bytes),
    pending_input_human_bytes: num(r.pending_input_human_bytes),
    input_paste_open: bool(r.input_paste_open),
    gate_pending: r.gate_pending ?? null,
    human_idle_secs: "human_idle_secs" in r ? num(r.human_idle_secs) ?? (r.human_idle_secs === null ? null : undefined) : undefined,
    working: working(r),
  };
}

/** feed.list(status=pending) 응답 → 승인 대기 좌석 번호들 · 꼴이 틀리면 null(모름). */
export function approvalSeatsOf(feed: unknown): number[] | null {
  const items = Array.isArray(feed) ? feed : (feed as { items?: unknown } | null)?.items;
  if (!Array.isArray(items)) return null;
  const out: number[] = [];
  for (const it of items) {
    const f = it as { kind?: unknown; status?: unknown; surface_id?: unknown } | null;
    if (!f || f.kind !== "approval" || f.status !== "pending") continue;
    if (typeof f.surface_id === "number" && Number.isSafeInteger(f.surface_id)) out.push(f.surface_id);
  }
  return out;
}
