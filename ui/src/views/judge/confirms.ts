// (cysr-ui-slice4 · TICKET=cysr-ui-slice4-1118) 확인 대기 판정 — 순수. P2-DESIGN §11 조각 4 · §5-4 · §2-7 · PRD FR-C1~C6(C1a·C5a·C5b).
//
// 띠에 오르는 것 셋:
//  ① 마스터 물음 — 마스터 답 글의 **줄머리 정확 일치** 표식 `⟪확인 요청: …⟫` 만(§5-4). 표식이 없으면 띠 0(꾸미지 않음).
//     `⟪확인 해결: <같은 물음 앞 20자>⟫` 가 오면 그 물음을 닫는다(FR-C3 — 화면은 사람 말을 어느 물음의 답으로 붙이지 않는다).
//  ② 도우미 허락 — 데몬 feed 의 승인 대기(kind approval · 도우미 좌석). 평소 = 「마스터가 확인하는 중」(FR-C6).
//     **마스터가 멈췄을 때만** 직접 허락·거절(FR-C5) — 펼친 뒤에만 허락(C5a) · 요청 번호 + 보인 판에 묶음(C5b).
//  ③ 마스터 창 확인 — 마스터 좌석 자신의 승인 창(작업 화면에서 답함 · 직접 단추 0).
// 「모름」은 0 으로 칠하지 않는다(FR-C1a): 기록을 다 못 훑었거나 feed 를 못 받았으면 「확인할 것 살펴보는 중」.
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지(시각은 인자 · views 정적 핀).

import type { Rec } from "./msgstep";

export const ASK_PREFIX = "⟪확인 요청: ";
export const RESOLVE_PREFIX = "⟪확인 해결: ";
export const MARK_END = "⟫";
/** 해결 표식이 싣는 물음 앞 글자 수(§5-4). 코드 포인트 단위. */
export const RESOLVE_KEY_LEN = 20;
/** FR-C5 「사람 확인 대기가 생긴 뒤 마스터 소식 5분 없음」 — **설계 목표값 · P0 근거 없음 · deadman 경로 U1 미실측(측정 대기)**. 값은 이 한 곳. */
export const CONFIRM_STALL_MS = 300_000;
export const CONFIRM_STALL_MEASURED = false;
/** 데몬이 승인 「명령 원문」을 자르는 한도(governance.rs approval_command_block · 12행 · 600자) — 닿으면 잘림 표시(§2-7 F17). */
export const CMD_MAX_LINES = 12;
export const CMD_MAX_CHARS = 600;

export type MarkerEvent = { kind: "ask"; text: string; uuid: string | null } | { kind: "resolve"; key: string; uuid: string | null };

/** 마스터 답 레코드 하나 → 표식 사건들(순서대로). user·곁가지·글 없는 레코드 = 0 · 코드 울타리(```) 안 줄 = 0(인용·예시로 쓴 표식). */
export function markersOf(r: Rec): MarkerEvent[] {
  if (r.role !== "assistant" || r.sidechain || typeof r.text !== "string") return [];
  const out: MarkerEvent[] = [];
  let fence = false;
  for (const raw of r.text.replace(/\r\n?/g, "\n").split("\n")) {
    if (raw.startsWith("```")) {
      fence = !fence;
      continue;
    }
    if (fence) continue;
    const line = raw.replace(/\s+$/, "");
    if (!line.endsWith(MARK_END)) continue;
    if (line.startsWith(ASK_PREFIX)) {
      const text = line.slice(ASK_PREFIX.length, line.length - MARK_END.length).trim();
      if (text) out.push({ kind: "ask", text, uuid: r.uuid });
    } else if (line.startsWith(RESOLVE_PREFIX)) {
      const key = line.slice(RESOLVE_PREFIX.length, line.length - MARK_END.length).trim();
      if (key) out.push({ kind: "resolve", key: resolveKey(key), uuid: r.uuid });
    }
  }
  return out;
}

/** 물음의 앞 20자(코드 포인트) — 해결 표식 대조 열쇠. */
export function resolveKey(s: string): string {
  return Array.from(s.trim()).slice(0, RESOLVE_KEY_LEN).join("");
}

export interface Question {
  /** 띠 항목 열쇠(같은 물음이 닫혔다 다시 열리면 다른 열쇠) */
  id: string;
  text: string;
  /** 그 물음을 담은 마스터 답 레코드(대화 자리로 데려갈 때) */
  uuid: string | null;
}

/** 표식 사건을 차례로 다시 놀아 열린 물음을 낸다. 해결 = 앞 20자가 같은 열린 물음 가운데 **가장 오래된 하나만** 닫음(한 표식 = 한 물음).
 *  같은 글의 물음이 이미 열려 있으면 다시 묻는 것 — 새 항목을 만들지 않는다. */
export function openQuestions(events: readonly MarkerEvent[]): Question[] {
  const open: Question[] = [];
  let n = 0;
  for (const e of events) {
    n++;
    if (e.kind === "ask") {
      if (open.some((q) => q.text === e.text)) continue;
      open.push({ id: `q${n}`, text: e.text, uuid: e.uuid });
    } else {
      const i = open.findIndex((q) => resolveKey(q.text) === e.key);
      if (i >= 0) open.splice(i, 1);
    }
  }
  return open;
}

export interface FeedApproval {
  request_id: string;
  surface_id: number;
  /** 데몬 epoch 초(소수) */
  created_at: number;
  /** feed 본문 원문(판 대조에 그대로 씀) */
  body: string;
  excerpt: string;
  /** 「명령 원문」(없으면 "") */
  command: string;
  /** 데몬의 기계 낱말 대조 추정(「쓰기·삭제 가능」 등) · 없으면 null */
  readonly: string | null;
  /** 데몬 자름 한도에 닿음 */
  truncated: boolean;
}

const CMD_HEAD = "\n— 명령 원문:\n";
const RO_HEAD = "\n— 읽기 전용 판정(기계 추정 · 근거 아님): ";

/** 데몬 승인 feed 본문(governance.rs `push_feed_notification("approval", …)`) → 조각. 꼴이 다르면 전부 excerpt 로(꾸미지 않음). */
export function parseApprovalBody(body: string): { excerpt: string; command: string; readonly: string | null } {
  const c = body.indexOf(CMD_HEAD);
  const r = body.lastIndexOf(RO_HEAD);
  if (c < 0 || r < c) return { excerpt: body, command: "", readonly: null };
  return { excerpt: body.slice(0, c), command: body.slice(c + CMD_HEAD.length, r), readonly: body.slice(r + RO_HEAD.length).trim() || null };
}

/** feed.list(status=pending) 응답 → 승인 대기 항목들(kind approval · pending · 번호·좌석·시각·본문이 온전한 것만) · 꼴이 틀리면 null(모름). */
export function approvalsOf(feed: unknown): FeedApproval[] | null {
  const items = Array.isArray(feed) ? feed : (feed as { items?: unknown } | null)?.items;
  if (!Array.isArray(items)) return null;
  const out: FeedApproval[] = [];
  for (const it of items) {
    const f = it as Record<string, unknown> | null;
    if (!f || f.kind !== "approval" || f.status !== "pending") continue;
    if (typeof f.request_id !== "string" || !f.request_id) continue;
    if (typeof f.surface_id !== "number" || !Number.isSafeInteger(f.surface_id)) continue;
    if (typeof f.created_at !== "number" || !Number.isFinite(f.created_at)) continue;
    const body = typeof f.body === "string" ? f.body : "";
    const p = parseApprovalBody(body);
    const truncated = p.command.split("\n").length >= CMD_MAX_LINES || Array.from(p.command).length >= CMD_MAX_CHARS;
    out.push({ request_id: f.request_id, surface_id: f.surface_id, created_at: f.created_at, body, ...p, truncated });
  }
  return out.sort((a, b) => a.created_at - b.created_at);
}

/** 마스터 쪽 관측(멈춤 판정 입력). */
export interface StallInput {
  now: number;
  /** undefined = 모름 · null = 마스터 좌석 없음 */
  masterSid: number | null | undefined;
  /** 데몬 agent_alive(null = 모름) */
  masterAlive: boolean | null;
  /** 마스터 좌석 마지막 출력 뒤 초(org.status idle_secs) · null = 모름 */
  masterIdleSecs: number | null;
  /** 받은 master.deadman(가장 최근) */
  deadman: { at: number; sid: number | null } | null;
  /** approval.stalled 를 받은 요청 번호 */
  stalledIds: ReadonlySet<string>;
}

export type StallWhy = "deadman" | "master_off" | "no_master" | "stalled_event" | "quiet";

/** 마스터가 말할 수 없는가(항목과 무관한 축) — deadman 사건(그 뒤 같은 마스터가 살아 출력했거나 새 마스터가 섰으면 풀림) · 꺼짐 확정 · 좌석 없음. 모름 = 아님. */
export function masterSilenced(i: StallInput): StallWhy | null {
  if (i.masterSid === null) return "no_master";
  if (i.masterSid !== undefined && i.masterAlive === false) return "master_off";
  const d = i.deadman;
  if (d) {
    const revived = i.masterAlive === true && i.masterSid !== undefined && (i.masterSid !== d.sid || (i.masterIdleSecs !== null && i.masterIdleSecs * 1000 < i.now - d.at));
    if (!revived) return "deadman";
  }
  return null;
}

/** 이 도우미 허락에 사람이 직접 단추를 둘 수 있는가(FR-C5) — 마스터 멈춤 · 그 요청의 approval.stalled · 생긴 지 5분 ∧ 마스터 소식 5분 없음. */
export function itemStall(i: StallInput, a: FeedApproval): StallWhy | null {
  const m = masterSilenced(i);
  if (m) return m;
  if (i.stalledIds.has(a.request_id)) return "stalled_event";
  const age = i.now - a.created_at * 1000;
  if (age >= CONFIRM_STALL_MS && i.masterIdleSecs !== null && i.masterIdleSecs * 1000 >= CONFIRM_STALL_MS) return "quiet";
  return null;
}

export type BandItem =
  | { kind: "ask"; key: string; q: Question }
  | { kind: "helper"; key: string; a: FeedApproval; stall: StallWhy | null }
  | { kind: "master_screen"; key: string; a: FeedApproval };

export interface Band {
  /** 다 알고 있는가 — 아니면 0 을 「없음」으로 칠하지 않는다 */
  known: boolean;
  items: BandItem[];
}

/** 판 열쇠 — 같은 번호여도 시각·본문이 바뀌면 다른 판(펼침이 이어지지 않음). */
export function versionKey(a: FeedApproval): string {
  return `${a.request_id}\u0000${a.created_at}\u0000${a.body}`;
}

/** 띠 항목(한 번에 하나를 보이는 쪽은 그리기) — 마스터 물음 먼저(대화가 1차 통로) · 그다음 승인 대기(오래된 것부터). */
export function bandOf(questions: readonly Question[] | null, approvals: readonly FeedApproval[] | null, stall: StallInput): Band {
  const items: BandItem[] = [];
  for (const q of questions ?? []) items.push({ kind: "ask", key: q.id, q });
  for (const a of approvals ?? []) {
    if (stall.masterSid !== undefined && stall.masterSid !== null && a.surface_id === stall.masterSid) items.push({ kind: "master_screen", key: versionKey(a), a });
    else items.push({ kind: "helper", key: versionKey(a), a, stall: itemStall(stall, a) });
  }
  return { known: questions !== null && approvals !== null && stall.masterSid !== undefined, items };
}

/** 띠 머리 글 · null = 띠 숨김(0건 확정일 때만 · FR-C1a). */
export function bandLabel(b: Band): string | null {
  const n = b.items.length;
  if (!b.known) return n === 0 ? "확인할 것 살펴보는 중" : `확인이 필요해요 ${n} · 더 살펴보는 중`;
  return n === 0 ? null : `확인이 필요해요 ${n}`;
}

/** 직접 허락 단추를 누를 수 있는가(FR-C5·C5a) — 멈춤 아니면 단추 자체가 없음 · 펼치기 전 = 흐림 + 안내. 거절은 펼침 없이 됨. */
export function allowReady(item: BandItem, expanded: boolean, decision: "allow" | "deny"): { ok: true } | { ok: false; msg: string } {
  if (item.kind !== "helper" || item.stall === null) return { ok: false, msg: "마스터가 확인하는 중이에요 — 마스터에게 맡겨 주세요." };
  if (decision === "allow" && !expanded) return { ok: false, msg: "먼저 「무엇을 보기」를 펼쳐 무엇을 허락하는지 확인해 주세요." };
  return { ok: true };
}

/** 클릭이 묶인 판(요청 번호 + 화면에 보인 본문 + 시각 + 좌석 · FR-C5b). */
export interface Bound {
  request_id: string;
  created_at: number;
  body: string;
  surface_id: number;
}

export function boundOf(a: FeedApproval): Bound {
  return { request_id: a.request_id, created_at: a.created_at, body: a.body, surface_id: a.surface_id };
}

export type RecheckCode = "unknown" | "gone" | "changed" | "not_stalled";

const RECHECK_MSG: Record<RecheckCode, string> = {
  unknown: "요청 상태를 확인하지 못해 처리하지 않았어요 — 잠시 뒤 다시 눌러 주세요.",
  gone: "이미 처리됐거나 바뀐 요청이에요.",
  changed: "이미 처리됐거나 바뀐 요청이에요.",
  not_stalled: "마스터가 다시 확인하고 있어요 — 마스터에게 맡겨 주세요.",
};

/** 처리 직전 재확인(순수) — 새로 받은 feed 에 같은 번호가 대기 중이고 시각·본문·좌석이 같고, 지금도 멈춤일 때만 통과. 아니면 호출 0. */
export function recheck(b: Bound, fresh: readonly FeedApproval[] | null, stallNow: (a: FeedApproval) => StallWhy | null): { ok: true } | { ok: false; code: RecheckCode; msg: string } {
  const no = (code: RecheckCode) => ({ ok: false as const, code, msg: RECHECK_MSG[code] });
  if (fresh === null) return no("unknown");
  const a = fresh.find((x) => x.request_id === b.request_id);
  if (!a) return no("gone");
  if (a.created_at !== b.created_at || a.body !== b.body || a.surface_id !== b.surface_id) return no("changed");
  if (stallNow(a) === null) return no("not_stalled");
  return { ok: true };
}

/** feed_reply 실패 글(`"<code>: <message>"`) → 사람 글. */
export function replyErrorMsg(err: string): string {
  const code = err.split(":")[0]?.trim() ?? "";
  if (/already resolved/.test(err) || code === "not_found") return "이미 처리됐거나 바뀐 요청이에요.";
  if (code === "approval_screen_gone") return "도우미 창의 확인이 이미 사라졌어요 — 누를 것이 없었어요.";
  if (code === "approval_actuation_refused") return "도우미 창 모양이 예상과 달라 누르지 않았어요 — 작업 화면에서 확인해 주세요.";
  return `처리하지 못했어요${code ? ` (${code})` : ""} — 작업 화면에서 확인해 주세요.`;
}
