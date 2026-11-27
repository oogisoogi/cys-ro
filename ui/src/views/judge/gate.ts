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
/** U25(마스터가 답하는 중에 친 말을 Claude Code 가 받아 두는가) — ★실측 = 받아 둔다(TICKET=cysr-1121-ui K-3 · 2026-11-27 · Claude Code 2.1.332 ·
 *  증거 workers/cysr-1121-ui/u25-evidence/u25-records.txt): 원자 제출 0.7초 뒤 `queue-operation enqueue`(화면 「Queued」) → 도구 경계에서 흡수
 *  (`attachment.queued_command`) 또는 턴 끝 dequeue 뒤 user 레코드. 대기 중 둘째 원자 제출의 Ctrl-U 는 대기 말을 지우지 않는다(두 말 차례 그대로).
 *  → true = 바쁠 때도 보냄(작업 화면에서 바쁠 때 치는 것과 같은 길 · 설계 P2-DESIGN §2 「마스터가 바쁠 때」의 원래 그림). 되돌리기 = 이 값을 false 로. */
export const U25_BUSY_PASTE_OK: boolean = true;

/** (TICKET=cysr-chat-held-win) 자기 신고(status)가 없거나 낡았을 때 대화 화면 문턱이 「답하는 중」을 가르는 출력 정적 초.
 *  앱 공통 판정(appearance.nodeWorking)은 「출력 60초 안 = 일하는 중」이라, 자기 신고가 없는 마스터(윈 좌석 492 = 재시작 뒤 set-status 0회)에선
 *  답을 마친 뒤에도 최소 60초 동안 대화 화면 말이 「답하는 중」으로 붙잡혔다.
 *  실측(맥 · 11-23 00:23~00:25 · Claude Code 좌석 2373 · org.status 0.5초 간격): 일하는 중(도구 실행 대기 25초) idle_secs 50표본 전부 0 /
 *  쉬는 중 75초 idle_secs 13→98 단조 증가(0 으로 돌아감 0회) → 출력 10초 정적이면 쉬는 중으로 본다. 작업 화면 표시 판정은 바꾸지 않는다. */
export const CHAT_QUIET_SECS = 10;
/** appearance.STATUS_FRESH_SECS 와 같은 값(이 파일은 순수 판정이라 가져오지 않고 시험이 같은지 대조한다). */
export const CHAT_STATUS_FRESH_SECS = 120;

/** 대화 화면 문턱용 「답하는 중」 — 자기 신고가 신선하면 앱 공통 판정(base) 그대로, 아니면 출력 정적 CHAT_QUIET_SECS 초로. idle_secs 모름 = base. 순수. */
export function chatWorking(r: Record<string, unknown>, base: (row: Record<string, unknown>) => boolean): boolean {
  if (r.exited === true) return false;
  const st = r.status as { age_secs?: unknown } | null | undefined;
  if (st && typeof st === "object") {
    const age = typeof st.age_secs === "number" ? st.age_secs : 0;
    if (age <= CHAT_STATUS_FRESH_SECS) return base(r);
  }
  const idle = r.idle_secs;
  return typeof idle === "number" && Number.isFinite(idle) && idle >= 0 ? idle <= CHAT_QUIET_SECS : base(r);
}

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
  /** (조각 3) 좌석 마지막 출력 뒤 초(org.status `idle_secs` · handlers.rs:12145) — 두 조회 사이 새 출력(짧은 답)을 알아채는 데만 씀 · 없으면 null */
  idle_secs?: number | null;
  /** (조각 5 · S1-5) 지금 남은 사람 입력 시각의 찍기 표지(org.status `human_input_stamp` = `<데몬 기동 ms>:<번호>` · 찍기 없음 = null)
   *  ★(TICKET=cysr-1121-ui K-2) 칸 자체가 없음(옛 데몬) = undefined — 「입력 없음(null)」과 갈라야 10분 상한 판정이 모르는 데몬에서 자동으로 틀리지 않는다. */
  human_input_stamp?: string | null;
  /** (조각 5 · §6-2) 등록 에이전트 이름(meta) · 이 좌석에서 그 에이전트를 본 적 있는가 · 좌석 판정("empty"/"occupied"/"unknown") — 없으면 null */
  agent?: string | null;
  agent_seen?: boolean | null;
  seat?: string | null;
  /** (1.1.19 · TICKET=cysr-1119-s3 · F29) 좌석에 결속된 세션 id(org.status `registered_session_id` · 3초 조회 원문) — 글만 · 없음·빈칸·꼴 틀림 = null.
   *  대화 화면 기록 watch 가 이 값으로 걸고(P3 v4 §3-7 C-1) 바뀌면 다시 건다(C-3). */
  registered_session_id?: string | null;
}

export interface GateInput {
  /** undefined = org.status 조회 실패(모름) · null = 마스터 좌석 없음 */
  master: MasterRow | null | undefined;
  /** 이 데몬의 승인 대기(feed kind=approval status=pending) 항목이 걸린 좌석 번호들 · null = feed 조회 실패(모름) */
  approvalSeats: readonly number[] | null;
  busyPasteOk?: boolean;
  /** (조각 5 · S1-5) 이 화면이 이 마스터 좌석에 낸 마지막 원자 제출의 사람 입력 표지(데몬 응답 `human_input_stamp`) — 행의 값과 같으면
   *  「남은 사람 입력 = 내 보내기」라 30초 쉼을 걸지 않는다(다른 길 입력이 그 뒤에 찍히면 차례가 바뀐다 · 시각이 아니라 번호로 짝짓기). */
  ownHumanStamp?: string | null;
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
  busy: "마스터가 지금 답하는 중이라 끼워 넣지 않았어요 — 답이 끝나면 저절로 보내요(누르실 것 없어요).",
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
  if (m.human_idle_secs !== null && m.human_idle_secs < HUMAN_QUIET_SECS && !ownLastHumanInput(m, g.ownHumanStamp)) return verdict("human_recent");
  if (m.working && !(g.busyPasteOk ?? U25_BUSY_PASTE_OK)) return verdict("busy");
  return { ok: true };
}

/** (조각 5 · S1-5) 행의 사람 입력 표지가 내 마지막 원자 제출의 표지와 같은가 — 둘 다 빈칸 아닌 글일 때만(모르면 아님 = 30초 쉼 그대로).
 *  표지 = 데몬 기동 세대 + 줄지 않는 번호 → 데몬이 다시 켜지거나 되돌림이 있어도 남의 입력과 같아지지 않는다(codex 1R ABA). */
export function ownLastHumanInput(m: MasterRow, own: string | null | undefined): boolean {
  return typeof own === "string" && own !== "" && typeof m.human_input_stamp === "string" && m.human_input_stamp === own;
}

/** (TICKET=cysr-1121-ui K-2 · master 10:2x 「붙잡은 뒤 같은 좌석 사람 입력 0」) 기준 표지(말을 받아들일 때 본 값 · "" = 그때 입력 없음) 뒤로
 *  지금 표지까지 늘어난 사람 입력 차례가 **전부 이 화면이 실제로 쓴 제출**인가(순수). 표지 = 데몬 `<기동 ms>:<번호>`(handlers.rs human_input_stamp_label) —
 *  모름(기준 없음 · 지금 칸 없음 · 꼴 틀림 · 데몬이 다시 켜짐 = 세대 다름 · 번호가 줄어듦 · 차이가 너무 큼) = false(= 종전대로 사람 클릭). */
export const HUMAN_GAP_MAX = 200;
export function noOtherHumanInputSince(base: string | undefined, now: string | null | undefined, own: ReadonlySet<string>): boolean {
  if (typeof base !== "string" || now === undefined) return false;
  const cur = now ?? "";
  if (cur === base) return true;
  const parse = (x: string): [string, number] | null => {
    const m = /^(\d+):(\d+)$/.exec(x);
    return m ? [m[1], Number(m[2])] : null;
  };
  const c = parse(cur);
  if (!c) return false;
  const b: [string, number] | null = base === "" ? [c[0], 0] : parse(base);
  if (!b || b[0] !== c[0] || c[1] < b[1] || c[1] - b[1] > HUMAN_GAP_MAX) return false;
  for (let k = b[1] + 1; k <= c[1]; k++) if (!own.has(`${c[0]}:${k}`)) return false;
  return true;
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
    idle_secs: num(r.idle_secs),
    human_input_stamp: typeof r.human_input_stamp === "string" && r.human_input_stamp !== "" ? r.human_input_stamp : "human_input_stamp" in r && r.human_input_stamp === null ? null : undefined, // (K-2) 칸 없음·꼴 틀림 = undefined(모름)
    agent: typeof r.agent === "string" ? r.agent : null,
    agent_seen: bool(r.agent_seen),
    seat: typeof r.seat === "string" ? r.seat : null,
    registered_session_id: typeof r.registered_session_id === "string" && r.registered_session_id !== "" ? r.registered_session_id : null,
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
