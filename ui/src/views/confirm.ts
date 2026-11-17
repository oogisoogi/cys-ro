// (cysr-ui-slice4 · TICKET=cysr-ui-slice4-1118) 확인 대기 장부 — 공통층 한 부분(대화 화면이 켜져 있을 때만 돈다). P2-DESIGN §11 조각 4.
//
// 받는 것(전부 이미 있는 길 · 데몬 무변경):
//  · 마스터 물음 표식 = 결속 세션 기록(조각 1 chat_transcript). 시작 오프셋(대화 화면을 연 때) **앞** 기록은 3초마다 한 토막(2 MiB)씩
//    처음부터 훑는다(그동안 「확인할 것 살펴보는 중」 · FR-C1a) · 뒤 기록은 core 가 읽은 레코드를 그대로 받는다.
//  · 도우미 허락 = core 가 쓰기 직전·3초마다 받는 feed_list(pending) 원문을 같이 받는다(새 조회 0).
//  · 멈춤 = daemon-event 의 master.deadman · approval.stalled(대화 화면이 켜져 있을 때만 구독) + org.status 마스터 행.
// 직접 허락(FR-C5): 사람의 신뢰 클릭(그리기 쪽 isTrusted) → decide(판 묶음) → **처리 직전 feed·org 다시 받기** → recheck 통과 때만 feed_reply 1회.
//   아니면 호출 0 + 「이미 처리됐거나 바뀐 요청이에요」. 누른 사실은 기록(NFR-S5 ③ · 명령 원문 0자).

import type { Rec } from "./judge/msgstep";
import {
  approvalsOf,
  bandOf,
  itemStall,
  markersOf,
  openQuestions,
  recheck,
  replyErrorMsg,
  type Band,
  type Bound,
  type FeedApproval,
  type MarkerEvent,
  type StallInput,
} from "./judge/confirms";

export const DECISION_LOG_KEY = "cys-chat-decisions";
export const DECISION_LOG_MAX = 50;

export interface ConfirmDeps {
  invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown>;
  now(): number;
  store: { get(k: string): string | null; set(k: string, v: string): void };
}

export interface DecisionRecord {
  request_id: string;
  decision: "allow" | "deny";
  at: number;
  /** "replied" | recheck 코드 | feed_reply 오류 코드 */
  outcome: string;
}

interface Scan {
  sid: string | null;
  surface: number;
  /** 다음에 읽을 오프셋(앞 기록) */
  next: number;
  /** 시작 오프셋 — 여기까지가 앞 기록 */
  end: number;
}

export class ConfirmBook {
  private prior: MarkerEvent[] = [];
  private tail: MarkerEvent[] = [];
  /** 표식 근거로 쓴 레코드 uuid(앞 훑기와 뒤 읽기가 겹친 토막을 두 번 세지 않게) */
  private seen = new Set<string>();
  private tailSeen = new Set<string>();
  private scan: Scan | null = null;
  private priorDone = false;
  private scanning = false;
  private approvals: FeedApproval[] | null = null;
  private master: { sid: number | null | undefined; alive: boolean | null; idle: number | null } = { sid: undefined, alive: null, idle: null };
  private deadman: { at: number; sid: number | null } | null = null;
  private stalledIds = new Set<string>();
  private deciding = false;
  /** 마지막 허락·거절 결과(띠 아래 1줄) */
  notice: string | null = null;
  readonly decisions: DecisionRecord[] = [];

  constructor(
    private readonly d: ConfirmDeps,
    private readonly changed: () => void,
  ) {}

  // ---------- 세션 기록 ----------

  /** core 가 결속 세션의 시작 오프셋을 잡음. 같은 세션이면 그대로(대화 화면 왕복) · 다르면 처음부터. */
  startSession(sid: string | null, surface: number, startOffset: number): void {
    if (this.scan && this.scan.sid === sid && this.scan.surface === surface) return;
    this.prior = [];
    this.tail = [];
    this.seen.clear();
    this.tailSeen.clear();
    this.scan = { sid, surface, next: 0, end: startOffset };
    this.priorDone = startOffset <= 0;
    this.changed();
  }

  /** 결속 세션이 바뀌었거나 잘림 — 표식 처음부터(모름으로). */
  resetSession(): void {
    this.prior = [];
    this.tail = [];
    this.seen.clear();
    this.tailSeen.clear();
    this.scan = null;
    this.priorDone = false;
    this.changed();
  }

  /** core 가 시작 오프셋 뒤를 읽은 레코드. */
  onTail(recs: readonly Rec[]): void {
    const ev: MarkerEvent[] = [];
    for (const r of recs) {
      if (r.uuid !== null) {
        if (this.seen.has(r.uuid)) continue; // 앞 훑기가 끝 너머까지 먼저 읽은 레코드
        this.seen.add(r.uuid);
        this.tailSeen.add(r.uuid);
      }
      ev.push(...markersOf(r));
    }
    if (ev.length) {
      this.tail.push(...ev);
      this.changed();
    }
  }

  /** 앞 기록 한 토막(대화 화면 poll 마다 1회). */
  async scanStep(): Promise<void> {
    const s = this.scan;
    if (!s || this.priorDone || this.scanning) return;
    this.scanning = true;
    try {
      const r = (await this.d.invoke("chat_transcript", { socket: null, surfaceId: s.surface, afterOffset: s.next, fromEnd: false }).catch(() => null)) as {
        status?: unknown;
        next_offset?: unknown;
        records?: unknown;
        session_id?: unknown;
        reset?: unknown;
      } | null;
      if (this.scan !== s) return; // 그사이 세션이 바뀜
      if (!r || r.status !== "ok" || typeof r.next_offset !== "number") return; // 모름 — 다음 틱에 다시
      const sid = typeof r.session_id === "string" ? r.session_id : null;
      if (sid !== s.sid || r.reset === true) {
        this.resetSession();
        return;
      }
      const recs = Array.isArray(r.records) ? (r.records as Rec[]) : [];
      for (const rec of recs) {
        if (rec.uuid !== null) {
          // 뒤 읽기가 이미 받은 레코드에 닿음 = 여기부터는 뒤 기록 — 앞 훑기 끝(순서가 뒤집히지 않게 · 해결이 물음보다 먼저 놀지 않게)
          if (this.tailSeen.has(rec.uuid)) {
            this.priorDone = true;
            break;
          }
          if (this.seen.has(rec.uuid)) continue;
          this.seen.add(rec.uuid);
        }
        this.prior.push(...markersOf(rec));
      }
      if (this.priorDone) {
        this.changed();
        return;
      }
      if (r.next_offset <= s.next) {
        this.priorDone = true; // 더 읽을 것이 없음(줄 끝 없음 등) — 멈춤 방지
      } else {
        s.next = r.next_offset;
        if (s.next >= s.end) this.priorDone = true;
      }
      this.changed();
    } finally {
      this.scanning = false;
    }
  }

  // ---------- feed · 마스터 · 사건 ----------

  /** core 가 받은 feed_list(pending)·org.status 원문(실패 = undefined). */
  observe(feed: unknown, org: unknown, master: { surface_id: number; agent_alive: boolean | null } | null | undefined): void {
    if (feed !== undefined) this.approvals = approvalsOf(feed);
    else this.approvals = null;
    if (master === undefined) this.master = { sid: undefined, alive: null, idle: null };
    else if (master === null) this.master = { sid: null, alive: null, idle: null };
    else this.master = { sid: master.surface_id, alive: master.agent_alive, idle: idleOf(org, master.surface_id) };
  }

  /** daemon-event 하나(대화 화면이 켜져 있을 때). */
  onEvent(ev: unknown): void {
    const e = (ev ?? {}) as { name?: unknown; payload?: unknown; surface_id?: unknown; socket_slug?: unknown };
    if (e.socket_slug) return; // 부서 데몬 사건 — 본부 마스터 대화와 무관
    const p = (e.payload ?? {}) as Record<string, unknown>;
    if (e.name === "master.deadman" && p.role === "master") {
      this.deadman = { at: this.d.now(), sid: typeof e.surface_id === "number" ? e.surface_id : null };
      this.changed();
    } else if (e.name === "approval.stalled" && typeof p.request_id === "string") {
      this.stalledIds.add(p.request_id);
      this.changed();
    }
  }

  private stallInput(): StallInput {
    return { now: this.d.now(), masterSid: this.master.sid, masterAlive: this.master.alive, masterIdleSecs: this.master.idle, deadman: this.deadman, stalledIds: this.stalledIds };
  }

  /** 지금의 띠(그리기용). 표식은 앞 훑기가 끝나야 「안다」. */
  band(): Band {
    const qs = this.scan !== null && this.priorDone ? openQuestions([...this.prior, ...this.tail]) : null;
    return bandOf(qs, this.approvals, this.stallInput());
  }

  /** 열린 물음(앞 훑기 중이어도 지금까지 본 것 · 시험용). */
  questionsSoFar() {
    return openQuestions([...this.prior, ...this.tail]);
  }

  get busy(): boolean {
    return this.deciding;
  }

  // ---------- 직접 허락·거절(FR-C5 · 신뢰 클릭에서만 불림) ----------

  /** 판에 묶인 허락·거절 — 처리 직전 다시 받아 recheck 통과 때만 feed_reply 1회. 진행 중이면 무시(클릭 1 → 호출 ≤ 1). */
  async decide(bound: Bound, decision: "allow" | "deny"): Promise<void> {
    if (this.deciding) return;
    this.deciding = true;
    this.notice = null;
    this.changed();
    let outcome = "replied";
    try {
      const feed = await this.d.invoke("feed_list", { status: "pending" }).catch(() => undefined);
      const org = await this.d.invoke("org_status", { socket: null }).catch(() => undefined);
      this.observe(feed, org, masterOf(org));
      const fresh = feed === undefined ? null : approvalsOf(feed);
      const st = this.stallInput();
      const rc = recheck(bound, fresh, (a) => itemStall(st, a));
      if (!rc.ok) {
        outcome = rc.code;
        this.notice = rc.msg;
        return;
      }
      try {
        await this.d.invoke("feed_reply", { requestId: bound.request_id, decision });
        this.notice = decision === "allow" ? "허락했어요 — 도우미가 이어서 해요." : "거절했어요 — 도우미에게 하지 말라고 전했어요.";
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e); // Tauri 거부 = "<code>: <message>" 글
        outcome = msg.split(":")[0]?.trim() || "error";
        this.notice = replyErrorMsg(msg);
      }
      // 결과를 띠에 바로 반영(다음 3초를 기다리지 않음)
      const after = await this.d.invoke("feed_list", { status: "pending" }).catch(() => undefined);
      if (after !== undefined) this.approvals = approvalsOf(after);
    } finally {
      this.record({ request_id: bound.request_id, decision, at: this.d.now(), outcome });
      this.deciding = false;
      this.changed();
    }
  }

  private record(r: DecisionRecord): void {
    this.decisions.push(r);
    if (this.decisions.length > DECISION_LOG_MAX) this.decisions.splice(0, this.decisions.length - DECISION_LOG_MAX);
    try {
      this.d.store.set(DECISION_LOG_KEY, JSON.stringify({ v: 1, items: this.decisions }));
    } catch {
      /* 기록 실패는 결정을 되돌리지 않는다(메모리 기록은 남음) */
    }
  }
}

/** org.status 행에서 그 좌석의 idle_secs(마지막 출력 뒤 초) · 모름 = null. */
function idleOf(org: unknown, sid: number): number | null {
  const rows = (org as { surfaces?: unknown } | null)?.surfaces;
  if (!Array.isArray(rows)) return null;
  const r = rows.find((x) => (x as { surface_id?: unknown } | null)?.surface_id === sid) as { idle_secs?: unknown } | undefined;
  const v = r?.idle_secs;
  return typeof v === "number" && Number.isFinite(v) && v >= 0 ? v : null;
}

/** org.status → 마스터 좌석(번호·생존)만 — gate.masterRowOf 와 같은 고르기(role master ∧ !exited · 번호 작은 것). */
function masterOf(org: unknown): { surface_id: number; agent_alive: boolean | null } | null | undefined {
  const rows = (org as { surfaces?: unknown } | null)?.surfaces;
  if (!Array.isArray(rows)) return undefined;
  const ms = rows
    .filter((r): r is Record<string, unknown> => !!r && typeof r === "object" && (r as { role?: unknown }).role === "master" && (r as { exited?: unknown }).exited !== true)
    .filter((r) => typeof r.surface_id === "number" && Number.isSafeInteger(r.surface_id))
    .sort((a, b) => (a.surface_id as number) - (b.surface_id as number));
  const r = ms[0];
  if (!r) return null;
  return { surface_id: r.surface_id as number, agent_alive: typeof r.agent_alive === "boolean" ? r.agent_alive : null };
}
