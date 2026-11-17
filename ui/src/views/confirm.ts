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
  deadmanRevived,
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
/** 처리 직전 org.status 왕복 상한(core OBS_MAX_MS 와 같은 값 · 순환 import 를 피해 따로 둠). */
export const ORG_MAX_MS = 500;
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
  /** 앞 훑기가 「끝을 넘는 토막」에서 가져간 레코드 신원(개수) — 뒤 읽기가 같은 레코드를 한 번 더 세지 않게 한 번씩 지운다(검증 F9: 같은 글 다시 물음) */
  private priorTaken = new Map<string, number>();
  /** 뒤 읽기가 받은 레코드 신원 — 앞 훑기가 끝을 넘는 토막에서 여기 닿으면 멈춘다 */
  private tailSeen = new Set<string>();
  /** 2 MiB 넘는 한 줄을 건너뛴 적 있음 — 그 안의 표식은 못 봄 → 물음 쪽은 「모름」 유지(검증 F3) */
  private lossy = false;
  /** 본부 데몬 socket_slug(앱 전달기는 본부 사건에도 slug 를 붙인다 · 검증 F1) · null = 아직 모름(사건 안 받음) */
  private hqSlug: string | null = null;
  /** 「마스터 좌석 없음 / 꺼짐 확정」을 처음 본 시각(검증 F5 유예) */
  private absentSince: number | null = null;
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
    this.clearMarks();
    this.scan = { sid, surface, next: 0, end: startOffset };
    this.priorDone = startOffset <= 0;
    this.changed();
  }

  /** 결속 세션이 바뀌었거나 잘림 — 표식 처음부터(모름으로). */
  resetSession(): void {
    this.clearMarks();
    this.scan = null;
    this.priorDone = false;
    this.changed();
  }

  private clearMarks(): void {
    this.prior = [];
    this.tail = [];
    this.priorTaken.clear();
    this.tailSeen.clear();
    this.lossy = false;
  }

  /** 긴 줄을 건너뜀(뒤 읽기 쪽에서도 · core 가 알림). */
  markLossy(): void {
    if (this.lossy) return;
    this.lossy = true;
    this.changed();
  }

  /** core 가 시작 오프셋 뒤를 읽은 레코드. */
  onTail(recs: readonly Rec[]): void {
    const ev: MarkerEvent[] = [];
    for (const r of recs) {
      const id = recId(r);
      const n = this.priorTaken.get(id) ?? 0;
      if (n > 0) {
        this.priorTaken.set(id, n - 1); // 앞 훑기가 끝 너머까지 먼저 가져간 레코드 — 한 번만 건너뜀
        continue;
      }
      this.tailSeen.add(id);
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
        skipped_bytes?: unknown;
      } | null;
      if (this.scan !== s) return; // 그사이 세션이 바뀜
      if (!r || r.status !== "ok" || typeof r.next_offset !== "number") return; // 모름 — 다음 틱에 다시
      const sid = typeof r.session_id === "string" ? r.session_id : null;
      if (sid !== s.sid || r.reset === true) {
        this.resetSession();
        return;
      }
      if (typeof r.skipped_bytes === "number" && r.skipped_bytes > 0) this.lossy = true;
      const recs = Array.isArray(r.records) ? (r.records as Rec[]) : [];
      const crossing = r.next_offset > s.end; // 끝(시작 오프셋)을 넘는 토막 — 뒤 기록이 섞여 있다
      for (const rec of recs) {
        const id = recId(rec);
        if (crossing) {
          // 뒤 읽기가 이미 받은 레코드에 닿음 = 여기부터는 뒤 기록 — 앞 훑기 끝(순서가 뒤집히지 않게 · 해결이 물음보다 먼저 놀지 않게)
          if (this.tailSeen.has(id)) {
            this.priorDone = true;
            break;
          }
          this.priorTaken.set(id, (this.priorTaken.get(id) ?? 0) + 1);
        }
        this.prior.push(...markersOf(rec));
      }
      if (this.priorDone) {
        this.changed();
        return;
      }
      if (r.next_offset <= s.next) {
        // 못 나아감(아직 끝나지 않은 긴 줄 등) — 「다 훑음」으로 확정하지 않는다(모름 유지 · 다음 틱에 다시 · 검증 F3)
        this.changed();
        return;
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
    // 좌석 없음·꺼짐 확정이 이어진 시작 시각(모름이면 그대로 둠) — 유예 30초(검증 F5)
    if (this.master.sid !== undefined) {
      const absent = this.master.sid === null || this.master.alive === false;
      if (!absent) this.absentSince = null;
      else if (this.absentSince === null) this.absentSince = this.d.now();
    }
    // deadman 걸쇠 — 풀림(살아난 마스터의 새 출력·새 좌석)을 한 번 보면 지운다(검증 F2 · 그 뒤 모름이 와도 되살아나지 않음)
    if (this.deadman && deadmanRevived(this.stallInput())) this.deadman = null;
  }

  /** 본부 데몬 slug(대화 화면이 켜질 때 core 가 받아 넣음). */
  setHqSlug(slug: string | null): void {
    this.hqSlug = slug;
  }

  /** daemon-event 하나(대화 화면이 켜져 있을 때). */
  onEvent(ev: unknown): void {
    const e = (ev ?? {}) as { name?: unknown; payload?: unknown; surface_id?: unknown; socket_slug?: unknown };
    // 앱 전달기는 본부 사건에도 slug 를 붙인다(main.rs 전달기) — 본부 slug 와 같을 때만 받음 · 본부 slug 를 모르면 받지 않음(단추가 덜 열리는 쪽)
    if (e.socket_slug !== undefined && e.socket_slug !== null && e.socket_slug !== "" && (this.hqSlug === null || e.socket_slug !== this.hqSlug)) return;
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
    return { now: this.d.now(), masterSid: this.master.sid, masterAlive: this.master.alive, masterIdleSecs: this.master.idle, deadman: this.deadman, absentSince: this.absentSince, stalledIds: this.stalledIds };
  }

  /** 지금의 띠(그리기용). 표식은 앞 훑기가 끝나야 「안다」. */
  band(): Band {
    // 앞 훑기가 끝나야 물음을 보인다 · 긴 줄을 건너뛰었으면 보이되 「모름」(더 살펴보는 중)
    const qs = this.scan !== null && this.priorDone ? openQuestions([...this.prior, ...this.tail]) : null;
    return bandOf(qs, this.approvals, this.stallInput(), qs !== null && !this.lossy);
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
      const t0 = this.d.now();
      const org = await this.d.invoke("org_status", { socket: null }).catch(() => undefined);
      // org 왕복이 길면 낡은 관측 — 마스터 상태 모름으로(보내기 길 OBS_MAX_MS 와 같은 500ms · 검증 F6)
      const stale = this.d.now() - t0 > ORG_MAX_MS;
      this.observe(feed, stale ? undefined : org, stale ? undefined : masterOf(org));
      if (org === undefined || stale) {
        outcome = "org_unknown";
        this.notice = "마스터 상태를 확인하지 못해 처리하지 않았어요 — 잠시 뒤 다시 눌러 주세요.";
        return;
      }
      const fresh = feed === undefined ? null : approvalsOf(feed);
      const st = this.stallInput();
      // 지금 마스터 좌석의 승인이면(마스터가 그 좌석으로 옮겨 옴 등) 직접 허락 대상이 아니다(codex 1R 탐침 — 그 요청의 approval.stalled 만으로 통과하던 길).
      const rc = recheck(bound, fresh, (a) => (st.masterSid !== undefined && st.masterSid !== null && a.surface_id === st.masterSid ? null : itemStall(st, a)));
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

/** 레코드 신원 — uuid · 없으면 역할·시각·글(codex 1R 탐침: uuid 없는 레코드를 앞 훑기·뒤 읽기가 둘 다 세던 길 · M8 측정 대기). */
function recId(r: Rec): string {
  return r.uuid ?? `\u0001${r.role}\u0001${r.ts ?? ""}\u0001${r.text ?? ""}`;
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
