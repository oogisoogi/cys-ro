// (cysr-ui-slice1) 화면 공통층 — 대화 화면 상태 하나(단일 작성자) + 행동(데몬 무리). P2-DESIGN §3-2 core·actions 의 조각 1 최소판.
//
// 사람 말 한 건의 길(§2-5 · 조각 0.5 결과 반영):
//   입력 → composeOutbound(살균·`/`·`!` 막기) → **쓰기 직전 재조회 1회**(org.status + feed 승인 대기 · 3초 목록을 믿지 않음)
//   → sendGate(문턱: 마스터 생존 · 관문 없음 · 승인 대기 없음 · 입력줄 빈칸 · 다른 길 사람 입력 30초 · 바쁨[U25 측정 대기])
//   → 하나라도 아니면 **쓰기 0 · 붙잡음**(앱 저장소 cys-chat-hold 에 원문 · 보내면 즉시 지움)
//   → 통과면 chat_send{human}(데몬 원자 제출 · refuse_on_approval) 1회 → 결과 넷(written·held·failed·uncertain)
//   → written 이면 세션 기록 +1·+3·+7초 읽기 → 전문 일치 user 레코드 = 「전달됨」 → 사슬 위 assistant 글 = 마스터 답 말풍선.
// 다시 보내기 = 확정 실패(failed)일 때 사람이 누른 1회만. 불명(uncertain)·붙잡음 자동 재전송 = 붙잡음(쓰기 0으로 끝난 것)만 문턱 재통과 때 1건씩.
// 데몬·파일·localStorage 는 deps 로만 닿는다(시험 대역 · FR-X1).

import { composeOutbound } from "./judge/outbound";
import { approvalSeatsOf, masterRowOf, sendGate, type GateVerdict, type MasterRow } from "./judge/gate";
import { applyRecords, canRetry, READ_AFTER_MS, settleSteps, stepFromOutcome, type Msg, type Rec, type Reply } from "./judge/msgstep";

export const HOLD_KEY = "cys-chat-hold";
/** 붙잡은 말 상한(설계 §5-3 · 넘으면 새 말을 받지 않고 안내). */
export const HOLD_MAX = 20;
/** 화면에 남기는 말 수(메모리) — 끝나지 않은 말은 밀어내지 않는다. */
export const LOG_MAX = 200;
/** 대화 화면이 켜져 있을 때 마스터 상태 조회 주기(작업 화면 3초 고리와 같은 박자 · 조각 2 에서 한 벌로 합침 📌). */
export const POLL_MS = 3_000;
/** 앱을 다시 켜기 전에 붙잡아 둔(저장소에서 읽은) 말 — 자동으로 보내지 않는다. */
export const RESTORED = "restored";
/** 앞 말을 쓰는 중에 받은 말의 붙잡음 표지(앞 말이 끝나면 바로 문턱에 건다). */
const AFTER_PREV = "after_prev";
/** 데몬이 승인 창으로 거부한 말을 다시 문턱에 거는 최소 간격(설계 목표값 · 창이 닫히면 문턱 재통과 때 1회). */
export const HELD_REFUSED_BACKOFF_MS = 15_000;
/** 세션 기록 한 번 읽기에서 이어 읽는 최대 횟수(2 MiB × 이 수). */
const READ_CHAIN_MAX = 3;

export interface Store {
  get(k: string): string | null;
  set(k: string, v: string): void;
  remove(k: string): void;
}

export interface Deps {
  invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown>;
  now(): number;
  setTimeout(fn: () => void, ms: number): unknown;
  clearTimeout(h: unknown): void;
  store: Store;
  /** org.status 행 → 지금 답하는 중인가(appearance.nodeWorking) */
  working(row: Record<string, unknown>): boolean;
}

export type Health = "unknown" | "none" | "off" | "gate" | "busy" | "ready";

export const HEALTH_LABEL: Record<Health, string> = {
  unknown: "마스터 상태 확인 중",
  none: "마스터 준비 중",
  off: "마스터가 꺼져 있어요",
  gate: "마스터가 시작 확인을 기다려요",
  busy: "마스터가 답하는 중",
  ready: "마스터가 듣고 있어요",
};

export interface ChatState {
  master: MasterRow | null | undefined;
  health: Health;
  /** 마스터 좌석에 걸린 확인 대기(승인) 수 · null = 모름 */
  confirms: number | null;
  msgs: Msg[];
  stray: Reply[];
  draft: string;
  /** 보내기 전 다듬기에서 막힌 까닭(입력칸 아래 1줄) */
  notice: string | null;
  /** 마지막 조회 실패 여부(오류 수에 셈) */
  pollFailed: boolean;
  rev: number;
}

export function healthOf(m: MasterRow | null | undefined): Health {
  if (m === undefined) return "unknown";
  if (m === null) return "none";
  if (m.agent_alive !== true) return "off";
  if (m.gate_pending !== null && m.gate_pending !== undefined) return "gate";
  return m.working ? "busy" : "ready";
}

export function errorCount(s: ChatState): number {
  return s.msgs.filter((m) => m.step === "failed").length + (s.pollFailed ? 1 : 0);
}

export function lastSendStep(s: ChatState): Msg["step"] | null {
  return s.msgs.length ? s.msgs[s.msgs.length - 1].step : null;
}

type Listener = (s: ChatState) => void;

export class ChatCore {
  private s: ChatState = { master: undefined, health: "unknown", confirms: null, msgs: [], stray: [], draft: "", notice: null, pollFailed: false, rev: 0 };
  private listeners = new Set<Listener>();
  private seq = 0;
  /** 진행 중인 쓰기(원자 제출 1건) — 겹쳐 쓰지 않는다(클릭 1 → 호출 ≤ 1). */
  private writing = false;
  private polling = false;
  private offset: number | null = null;
  private sessionId: string | null = null;
  private reading = false;
  private readTimers = new Set<unknown>();
  private attached = false;
  private lastWorking: boolean | null = null;

  constructor(private readonly d: Deps) {
    this.loadHold();
  }

  get state(): ChatState {
    return this.s;
  }

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  listenerCount(): number {
    return this.listeners.size;
  }

  private set(patch: Partial<ChatState>): void {
    this.s = { ...this.s, ...patch, rev: this.s.rev + 1 };
    for (const fn of [...this.listeners]) fn(this.s);
  }

  // ---------- 앱 안 무리(FR-X4) ----------

  setDraft(text: string): void {
    if (text === this.s.draft) return;
    this.s = { ...this.s, draft: text, notice: null, rev: this.s.rev + 1 }; // 초안은 알림 없이(입력 중 다시 그리기 0)
  }

  /** 대화 화면이 켜짐 — 세션 기록 읽기 허용 · 시작 오프셋 잡기. */
  attach(): void {
    this.attached = true;
    void this.readTranscript();
  }

  /** 대화 화면이 내려감 — 읽기 예약 해제(공통층 상태·붙잡은 말은 그대로 · §4-3). */
  detach(): void {
    this.attached = false;
    for (const h of this.readTimers) this.d.clearTimeout(h);
    this.readTimers.clear();
  }

  // ---------- 저장소(붙잡은 말만 원문 · §5-3 cys-chat-hold) ----------

  private loadHold(): void {
    let raw: string | null = null;
    try {
      raw = this.d.store.get(HOLD_KEY);
    } catch {
      return;
    }
    if (raw === null) return;
    try {
      const o = JSON.parse(raw) as { v?: unknown; items?: unknown };
      if (o.v !== 1 || !Array.isArray(o.items)) return;
      const msgs: Msg[] = [];
      for (const it of o.items.slice(0, HOLD_MAX)) {
        const x = it as { id?: unknown; text?: unknown; at?: unknown };
        if (typeof x.id !== "string" || typeof x.text !== "string" || typeof x.at !== "number") continue;
        // ★저장소 글은 자동으로 보내지 않는다(codex 1R blocking — 저장소 변조·손상 글이 사람 표지를 달고 원장 무기록 오너 입력이 되는 길).
        //   사람이 「이 말 보내기」를 눌러야(신뢰 클릭) 다듬기(composeOutbound)부터 다시 거쳐 새 말로 간다.
        msgs.push({ id: x.id, text: x.text, createdAt: x.at, sentAt: null, step: "held", code: RESTORED, note: "앱을 다시 켜기 전에 붙잡아 둔 말이에요 — 보내려면 「이 말 보내기」를 눌러 주세요.", thread: [], replies: [] });
      }
      this.s = { ...this.s, msgs };
    } catch {
      /* 깨진 값은 읽지 않는다(지우지도 않는다) */
    }
  }

  /** 붙잡은 말만 저장 · 성공 여부를 돌려준다(쓰기 직전 「보내는 중」 영속 확인에 씀). */
  private saveHold(msgs: readonly Msg[]): boolean {
    const items = msgs.filter((m) => m.step === "held").map((m) => ({ id: m.id, text: m.text, at: m.createdAt }));
    try {
      if (items.length === 0) this.d.store.remove(HOLD_KEY);
      else this.d.store.set(HOLD_KEY, JSON.stringify({ v: 1, items }));
      return true;
    } catch {
      return false;
    }
  }

  private putMsgs(msgs: Msg[], extra: Partial<ChatState> = {}): boolean {
    let kept = msgs;
    if (kept.length > LOG_MAX) {
      const done = new Set(["replied", "failed"]);
      let drop = kept.length - LOG_MAX;
      kept = kept.filter((m) => !(drop > 0 && done.has(m.step) && drop-- > 0));
    }
    const saved = this.saveHold(kept);
    this.set({ msgs: kept, ...extra });
    return saved;
  }

  private patchMsg(id: string, patch: Partial<Msg>): boolean {
    return this.putMsgs(this.s.msgs.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }

  // ---------- 데몬 무리 ----------

  /** 마스터 상태 + 승인 대기를 새로 받는다. 실패는 undefined/null(모름). */
  private async fetchFresh(): Promise<{ master: MasterRow | null | undefined; approvals: number[] | null }> {
    const [org, feed] = await Promise.all([
      this.d.invoke("org_status", { socket: null }).catch(() => undefined),
      this.d.invoke("feed_list", { status: "pending" }).catch(() => undefined),
    ]);
    return { master: org === undefined ? undefined : masterRowOf(org, this.d.working), approvals: feed === undefined ? null : approvalSeatsOf(feed) };
  }

  private gateOf(f: { master: MasterRow | null | undefined; approvals: number[] | null }): GateVerdict {
    return sendGate({ master: f.master, approvalSeats: f.approvals });
  }

  private applyFresh(f: { master: MasterRow | null | undefined; approvals: number[] | null }): void {
    const m = f.master;
    const confirms = f.approvals === null || !m ? (f.approvals === null ? null : 0) : f.approvals.filter((x) => x === m.surface_id).length;
    const working = m ? m.working : null;
    const msgs = settleSteps(this.s.msgs, this.d.now(), working);
    this.putMsgs(msgs, { master: m, health: healthOf(m), confirms, pollFailed: m === undefined });
  }

  /** 사람이 보내기를 누름(또는 Enter) — 받아들였으면 true(화면이 입력칸을 비움) · 막혔으면 false(입력칸 그대로 · 안내 1줄).
   *  받아들인 말은 바로 문턱·쓰기로 간다(끝을 기다리려면 `send`). */
  submit(raw: string): boolean {
    const text = this.admit(raw);
    if (text === null) return false;
    void this.accept(text);
    return true;
  }

  /** submit 과 같되 끝까지 기다린다(시험·내부용). */
  async send(raw: string): Promise<void> {
    const text = this.admit(raw);
    if (text !== null) await this.accept(text);
  }

  /** 다듬기·붙잡음 상한 — 통과면 보낼 글 · 아니면 null(안내 1줄). */
  private admit(raw: string): string | null {
    const out = composeOutbound(raw);
    if (!out.ok) {
      this.set({ notice: out.msg });
      return null;
    }
    if (this.s.msgs.filter((m) => m.step === "held").length >= HOLD_MAX) {
      this.set({ notice: `붙잡아 둔 말이 ${HOLD_MAX}개라 더 받지 않아요 — 마스터가 깨어나면 차례로 보내요.` });
      return null;
    }
    return out.text;
  }

  private async accept(text: string): Promise<void> {
    const busy = this.writing; // 앞 말을 쓰는 중 — 이 말은 붙잡았다가 앞 말이 끝나면 같은 문턱으로(겹쳐 쓰기 0 · 말 버림 0)
    const msg: Msg = busy
      ? { id: `m${this.d.now()}-${++this.seq}`, text, createdAt: this.d.now(), sentAt: null, step: "held", code: AFTER_PREV, note: "앞 말을 보낸 뒤 보낼게요.", thread: [], replies: [] }
      : { id: `m${this.d.now()}-${++this.seq}`, text, createdAt: this.d.now(), sentAt: null, step: "sending", thread: [], replies: [] };
    this.s = { ...this.s, draft: "", notice: null };
    this.putMsgs([...this.s.msgs, msg]);
    if (!busy) await this.deliver(msg.id);
  }

  /** 앱을 다시 켜기 전에 붙잡아 둔 말 — 사람이 「이 말 보내기」를 눌렀을 때만(다듬기부터 다시 · 새 번호). 막히면 그 말은 그대로 둔다. */
  async confirmRestored(id: string): Promise<void> {
    const m = this.s.msgs.find((x) => x.id === id);
    if (!m || m.step !== "held" || m.code !== RESTORED) return;
    const text = this.admit(m.text);
    if (text === null) return;
    this.putMsgs(this.s.msgs.filter((x) => x.id !== id));
    await this.accept(text);
  }

  /** 확정 실패한 말을 사람이 다시 보냄(1회 · 새 번호). */
  async retry(id: string): Promise<void> {
    const m = this.s.msgs.find((x) => x.id === id);
    if (!m || !canRetry(m) || this.writing) return;
    const msg: Msg = { id: `m${this.d.now()}-${++this.seq}`, text: m.text, createdAt: this.d.now(), sentAt: null, step: "sending", thread: [], replies: [], retried: true };
    this.putMsgs([...this.s.msgs.map((x) => (x.id === id ? { ...x, retried: true } : x)), msg]);
    await this.deliver(msg.id);
  }

  /** 한 말을 문턱에 걸고, 통과면 원자 제출 1회. */
  private async deliver(id: string): Promise<void> {
    if (this.writing) return;
    this.writing = true;
    try {
      let fresh = await this.fetchFresh(); // ★쓰기 직전 재조회 1회(3초 목록을 믿지 않음)
      this.applyFresh(fresh);
      if (this.offset === null && fresh.master) {
        // 보낸 user 레코드를 건너뛰지 않게 세션 기록 시작점을 먼저 잡는다 — 이 RPC 가 문턱 판정과 쓰기 사이에 끼지 않게 다시 조회한다.
        await this.initOffset();
        fresh = await this.fetchFresh();
        this.applyFresh(fresh);
      }
      const g = this.gateOf(fresh);
      if (!g.ok) {
        this.patchMsg(id, { step: "held", code: g.code, note: g.msg });
        return;
      }
      const m = fresh.master as MasterRow;
      const msg = this.s.msgs.find((x) => x.id === id);
      if (!msg) return;
      const sentAt = this.d.now();
      // ★쓰기 전에 「보내는 중」을 먼저 영속한다 — 저장소에서 이 말이 붙잡음 목록에서 빠진 것이 확인돼야 쓴다(codex 1R blocking:
      //   지우기 실패 + 불명 결과면 다시 켤 때 같은 말이 또 나가던 길). 저장 실패 = 쓰기 0 · 붙잡음 그대로.
      if (!this.patchMsg(id, { step: "sending", sentAt, code: undefined, note: undefined, notBefore: undefined })) {
        this.patchMsg(id, { step: "held", sentAt: null, code: "store_failed", note: "앱 저장소에 쓸 수 없어 보내지 않았어요(같은 말이 두 번 가는 것을 막으려고) — 잠시 뒤 다시 해 볼게요.", notBefore: this.d.now() + HELD_REFUSED_BACKOFF_MS });
        return;
      }
      let res: unknown;
      try {
        res = await this.d.invoke("chat_send", { socket: null, surfaceId: m.surface_id, text: msg.text, kind: "human" });
      } catch (e) {
        res = { outcome: "uncertain", code: "invoke_error", message: String(e) }; // Tauri 다리 자체 실패 = 쓰였는지 모름
      }
      const r = (res ?? {}) as { outcome?: unknown; code?: unknown; message?: unknown };
      const step = stepFromOutcome(r.outcome);
      const code = typeof r.code === "string" ? r.code : undefined;
      if (step === "held") {
        // 데몬 거부(바이트 0) — feed 대기 항목 없이 창만 떠 있을 수 있다(0.5 숫자 3 술어 차이) → 같은 말 재시도는 한동안 쉰다(3초마다 두드리지 않음 · 4군 ①).
        this.patchMsg(id, { step, sentAt: null, code, notBefore: this.d.now() + HELD_REFUSED_BACKOFF_MS, note: "마스터 창에 확인할 것이 떠 있어서 쓰지 않았어요 — 그 확인이 끝나면 보낼게요." });
        return;
      }
      if (step === "failed") {
        this.patchMsg(id, { step, code, note: `보내지 못했어요${code ? ` (${code})` : ""}.` });
        return;
      }
      this.patchMsg(id, { step, code, note: step === "queued_hold" ? "업데이트 중이라 차례를 기다려요 — 끝나면 데몬이 전달해요." : undefined });
      if (step === "injected" || step === "checking") this.scheduleReads();
    } finally {
      this.writing = false;
    }
    const next = this.s.msgs.find((x) => x.step === "held" && x.code === AFTER_PREV);
    if (next) await this.deliver(next.id); // 앞 말이 끝난 뒤 1건 — 다시 재조회·문턱(같은 말 두 번 0)
  }

  /** 대화 화면이 켜져 있을 때 POLL_MS 마다. 붙잡은 말이 있고 문턱이 열렸으면 오래된 것 1건을 보낸다(그 안에서 다시 재조회). */
  async poll(): Promise<void> {
    if (this.polling || this.writing) return;
    this.polling = true;
    let heldId: string | null = null;
    try {
      const fresh = await this.fetchFresh();
      const prevWorking = this.lastWorking;
      this.applyFresh(fresh);
      this.lastWorking = fresh.master ? fresh.master.working : null;
      const awaiting = this.s.msgs.some((m) => ["injected", "checking", "slow", "delivered", "replying"].includes(m.step));
      if (awaiting && prevWorking !== null && prevWorking !== this.lastWorking) void this.readTranscript(); // 활동이 바뀐 틱 1회
      else if (this.offset === null && fresh.master) void this.readTranscript(); // 마스터를 안 첫 틱에 세션 시작점을 잡아 둔다(보내기 길에서 그 RPC 를 빼려고)
      const now = this.d.now();
      const held = this.s.msgs.find((m) => m.step === "held" && m.code !== RESTORED && (m.notBefore === undefined || now >= m.notBefore));
      if (held && this.gateOf(fresh).ok) heldId = held.id;
    } finally {
      this.polling = false;
    }
    if (heldId !== null) await this.deliver(heldId); // deliver 안에서 다시 재조회·문턱(이 틱의 값은 쓰기 근거가 아니다)
  }

  // ---------- 세션 기록(결속 세션 전문 · chat_transcript) ----------

  private scheduleReads(): void {
    if (!this.attached) return;
    for (const ms of READ_AFTER_MS) {
      const h = this.d.setTimeout(() => {
        this.readTimers.delete(h);
        void this.readTranscript();
      }, ms);
      this.readTimers.add(h);
    }
  }

  private async initOffset(): Promise<void> {
    const m = this.s.master;
    if (!m) return;
    try {
      const r = (await this.d.invoke("chat_transcript", { socket: null, surfaceId: m.surface_id, afterOffset: 0, fromEnd: true })) as { status?: unknown; next_offset?: unknown; session_id?: unknown };
      if (r?.status === "ok" && typeof r.next_offset === "number") {
        this.offset = r.next_offset;
        this.sessionId = typeof r.session_id === "string" ? r.session_id : null;
      }
    } catch {
      /* 모름 — 다음 읽기에서 다시 */
    }
  }

  async readTranscript(): Promise<void> {
    if (this.reading || !this.attached) return;
    const m = this.s.master;
    if (!m) return;
    this.reading = true;
    try {
      if (this.offset === null) {
        await this.initOffset();
        return;
      }
      for (let i = 0; i < READ_CHAIN_MAX; i++) {
        const r = (await this.d.invoke("chat_transcript", { socket: null, surfaceId: m.surface_id, afterOffset: this.offset, fromEnd: false }).catch(() => null)) as {
          status?: unknown;
          next_offset?: unknown;
          size?: unknown;
          records?: unknown;
          session_id?: unknown;
          reset?: unknown;
        } | null;
        if (!r || r.status !== "ok" || typeof r.next_offset !== "number") return;
        const sid = typeof r.session_id === "string" ? r.session_id : null;
        if (sid !== this.sessionId) {
          // 결속 세션이 바뀜(마스터 다시 켜짐·/clear) — 새 파일 끝에서 다시 시작(옛 오프셋으로 새 파일을 읽지 않는다)
          this.sessionId = sid;
          this.offset = null;
          await this.initOffset();
          return;
        }
        if (r.reset === true) {
          // 파일이 줄었다(잘림·교체) — 다시 읽은 옛 레코드로 새 전달·답 근거를 만들지 않는다(codex 1R major). 끝에서 다시 시작.
          this.offset = null;
          await this.initOffset();
          return;
        }
        const recs = Array.isArray(r.records) ? (r.records as Rec[]) : [];
        this.offset = r.next_offset;
        if (recs.length) {
          const applied = applyRecords(this.s.msgs, recs);
          // 「답함」은 여기서 칠하지 않는다(null) — 들고 있는 활동 값은 이 답보다 옛 관측일 수 있다. 다음 조회(poll)의 새 관측으로만.
          const known = new Set(this.s.stray.map((x) => x.uuid).filter((u): u is string => u !== null));
          const fresh = applied.stray.filter((x) => x.uuid === null || !known.has(x.uuid));
          this.putMsgs(settleSteps(applied.msgs, this.d.now(), null), { stray: [...this.s.stray, ...fresh].slice(-LOG_MAX) });
        }
        if (typeof r.size !== "number" || r.next_offset >= r.size) return;
      }
    } finally {
      this.reading = false;
    }
  }
}
