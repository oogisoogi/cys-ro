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
import { ConfirmBook } from "./confirm";

export const HOLD_KEY = "cys-chat-hold";
/** 붙잡은 말 상한(설계 §5-3 · 넘으면 새 말을 받지 않고 안내). */
export const HOLD_MAX = 20;
/** 화면에 남기는 말 수(메모리) — 끝나지 않은 말은 밀어내지 않는다. */
export const LOG_MAX = 200;
/** 대화 화면이 켜져 있을 때 마스터 상태 조회 주기(작업 화면 3초 고리와 같은 박자 · 조각 2 에서 한 벌로 합침 📌). */
export const POLL_MS = 3_000;
/** 쓰기 직전 입력줄 관측(org.status 왕복)의 유효 상한(설계 목표값) — 넘으면 그 관측으로 쓰지 않는다(0.5 M12: 데몬 몫 < 1ms). */
export const OBS_MAX_MS = 500;
/** 앱을 다시 켜기 전에 붙잡아 둔(저장소에서 읽은) 말 — 자동으로 보내지 않는다. */
export const RESTORED = "restored";
/** 붙잡은 지 이만큼 지난 말은 자동으로 보내지 않는다 — 사람 클릭 1회로만(master 결정 11-17 23:2x · 10분 · VERIFY 지적 5). */
export const HELD_MAX_AGE_MS = 600_000;
export const STALE = "stale";
/** 앞 말(쓰는 중이거나 붙잡힌 말) 뒤에 줄 선 말의 표지 — 오래된 것부터 1건씩(설계 §2-5 · VERIFY 지적 1). */
const AFTER_PREV = "after_prev";

/** 사람이 눌러야만 나가는 붙잡은 말(다시 켠 뒤 복원 · 10분 넘음). */
export function needsClick(m: Msg): boolean {
  return m.step === "held" && (m.code === RESTORED || m.code === STALE);
}
/** 문턱이 열리면 자동으로 나갈 붙잡은 말. */
function autoHeld(m: Msg): boolean {
  return m.step === "held" && !needsClick(m);
}
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
  /** (조각 4) daemon-event 구독 — 대화 화면이 켜져 있을 때만(attach~detach). 없으면 사건 없이(멈춤 = org.status·5분 규칙만). */
  listen?(fn: (ev: unknown) => void): () => void;
  /** (조각 4) 다른 화면으로(「작업 화면에서 보기」) — registry.choose. */
  goView?(id: string): void;
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
  if (m.agent_alive === false) return "off";
  if (m.agent_alive !== true) return "unknown"; // null = 등록 없는 좌석 등 · 「꺼져 있어요」라 말하지 않음(VERIFY 지적 11)
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
  /** 이 결속 세션에서 이미 근거로 쓴 레코드 uuid — 말 목록 정리와 무관하게 유지 · 세션이 바뀌면 비움(codex 2R major). */
  private consumed = new Set<string>();
  private reading = false;
  private readTimers = new Set<unknown>();
  private attached = false;
  private lastWorking: boolean | null = null;
  /** (조각 4) 확인 대기 장부 — 띠·표식·직접 허락. */
  readonly confirm: ConfirmBook;
  private unlisten: (() => void) | null = null;

  constructor(private readonly d: Deps) {
    this.loadHold();
    this.confirm = new ConfirmBook({ invoke: d.invoke, now: d.now, store: d.store }, () => this.set({}));
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
    if (!this.unlisten && this.d.listen) this.unlisten = this.d.listen((ev) => this.confirm.onEvent(ev));
    void this.readTranscript();
  }

  /** 대화 화면이 내려감 — 읽기 예약 해제(공통층 상태·붙잡은 말은 그대로 · §4-3). */
  detach(): void {
    this.attached = false;
    this.unlisten?.();
    this.unlisten = null;
    for (const h of this.readTimers) this.d.clearTimeout(h);
    this.readTimers.clear();
  }

  /** (조각 4) 띠의 「작업 화면에서 보기」. */
  goView(id: string): void {
    this.d.goView?.(id);
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
        const x = it as { text?: unknown; at?: unknown };
        if (typeof x.text !== "string" || typeof x.at !== "number") continue;
        // ★저장소 글은 자동으로 보내지 않는다(codex 1R blocking — 저장소 변조·손상 글이 사람 표지를 달고 원장 무기록 오너 입력이 되는 길).
        //   사람이 「이 말 보내기」를 눌러야(신뢰 클릭) 다듬기(composeOutbound)부터 다시 거쳐 새 말로 간다.
        // 저장소 id 는 믿지 않는다 — 새 말 id(`m…`)와 겹칠 수 없는 내부 id(`r…`)를 준다(codex 2R blocking: 같은 id 로 복원 /clear 가 새 말 대신 선택되던 길).
        msgs.push({ id: `r${msgs.length + 1}`, text: x.text, createdAt: x.at, sentAt: null, step: "held", code: RESTORED, note: "앱을 다시 켜기 전에 붙잡아 둔 말이에요 — 보내려면 「이 말 보내기」를 눌러 주세요.", thread: [], replies: [] });
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
  /** 승인 대기(feed)를 먼저, **입력줄 상태(org.status)를 마지막에** 받는다 — 마지막 관측 뒤 다른 응답을 기다리지 않게(codex 2R blocking).
   *  org.status 왕복이 OBS_MAX_MS 를 넘으면 그 관측은 낡은 것으로 보고 모름(undefined → 붙잡음). */
  private async fetchFresh(): Promise<{ master: MasterRow | null | undefined; approvals: number[] | null; obsAt: number; feed?: unknown; org?: unknown }> {
    const feed = await this.d.invoke("feed_list", { status: "pending" }).catch(() => undefined);
    const t0 = this.d.now();
    const org = await this.d.invoke("org_status", { socket: null }).catch(() => undefined);
    const stale = this.d.now() - t0 > OBS_MAX_MS;
    return { master: org === undefined || stale ? undefined : masterRowOf(org, this.d.working), approvals: feed === undefined ? null : approvalSeatsOf(feed), obsAt: t0, feed, org };
  }

  private gateOf(f: { master: MasterRow | null | undefined; approvals: number[] | null; obsAt: number }): GateVerdict {
    return sendGate({ master: f.master, approvalSeats: f.approvals });
  }

  private applyFresh(f: { master: MasterRow | null | undefined; approvals: number[] | null; obsAt: number; feed?: unknown; org?: unknown }): void {
    const m = f.master;
    this.confirm.observe(f.feed, f.org, m);
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
    // 앞 말을 쓰는 중이거나 **앞서 붙잡힌(자동으로 나갈) 말이 있으면** 이 말은 그 뒤에 줄 선다 — 사람 지시의 앞뒤가 뒤집히지 않게(VERIFY 지적 1).
    const behind = this.writing || this.s.msgs.some(autoHeld);
    const msg: Msg = behind
      ? { id: `m${this.d.now()}-${++this.seq}`, text, createdAt: this.d.now(), sentAt: null, step: "held", code: AFTER_PREV, note: "앞 말을 보낸 뒤 보낼게요.", thread: [], replies: [] }
      : { id: `m${this.d.now()}-${++this.seq}`, text, createdAt: this.d.now(), sentAt: null, step: "sending", thread: [], replies: [] };
    this.s = { ...this.s, draft: "", notice: null };
    this.putMsgs([...this.s.msgs, msg]);
    if (!behind) await this.deliver(msg.id);
    else if (!this.writing) await this.pump();
  }

  /** 자동으로 나갈 붙잡은 말 가운데 **가장 오래된 것 하나만** 문턱에 건다(그 말이 쉼 중이면 아무것도 안 함 — 뒤 말이 앞지르지 않게). */
  private async pump(): Promise<void> {
    if (this.writing) return;
    this.markStale();
    const first = this.s.msgs.find(autoHeld);
    if (!first || (first.notBefore !== undefined && this.d.now() < first.notBefore)) return;
    await this.deliver(first.id);
  }

  /** 붙잡은 지 10분 넘은 자동 말 → 사람 클릭 대기로(자동 제출 0). */
  private markStale(): void {
    const now = this.d.now();
    if (!this.s.msgs.some((m) => autoHeld(m) && now - m.createdAt > HELD_MAX_AGE_MS)) return;
    this.putMsgs(
      this.s.msgs.map((m) =>
        autoHeld(m) && now - m.createdAt > HELD_MAX_AGE_MS ? { ...m, code: STALE, notBefore: undefined, note: "오래 기다린 말이에요 · 보낼까요? 「이 말 보내기」를 누르면 지금 보냅니다." } : m,
      ),
    );
  }

  /** 사람 클릭이 필요한 붙잡은 말(다시 켠 뒤 복원 · 10분 넘음) — 「이 말 보내기」를 눌렀을 때만(다듬기부터 다시 · 새 번호 · 지금 시각). 막히면 그 말은 그대로 둔다. */
  async confirmHeld(id: string): Promise<void> {
    const hits = this.s.msgs.filter((x) => x.id === id);
    if (hits.length !== 1) return; // 같은 id 가 둘 이상이면 고르지 않는다
    const m = hits[0];
    if (!needsClick(m)) return;
    // 이 말을 **대체**하는 동작이라 붙잡음 상한에 자기 자신을 세지 않는다(codex 2R major — 상한 20 교착). 다듬기는 그대로.
    const out = composeOutbound(m.text);
    if (!out.ok) {
      this.set({ notice: out.msg });
      return;
    }
    this.putMsgs(this.s.msgs.filter((x) => x.id !== id));
    await this.accept(out.text);
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
      if (this.d.now() - msg.createdAt > HELD_MAX_AGE_MS) {
        // 10분 넘게 기다린 말은 여기서도 쓰지 않는다(사람 클릭으로 새 말이 되어야 함).
        this.patchMsg(id, { step: "held", code: STALE, notBefore: undefined, note: "오래 기다린 말이에요 · 보낼까요? 「이 말 보내기」를 누르면 지금 보냅니다." });
        return;
      }
      const sentAt = this.d.now();
      // ★쓰기 전에 「보내는 중」을 먼저 영속한다 — 저장소에서 이 말이 붙잡음 목록에서 빠진 것이 확인돼야 쓴다(codex 1R blocking:
      //   지우기 실패 + 불명 결과면 다시 켤 때 같은 말이 또 나가던 길). 저장 실패 = 쓰기 0 · 붙잡음 그대로.
      if (!this.patchMsg(id, { step: "sending", sentAt, code: undefined, note: undefined, notBefore: undefined })) {
        this.patchMsg(id, { step: "held", sentAt: null, code: "store_failed", note: "앱 저장소에 쓸 수 없어 보내지 않았어요(같은 말이 두 번 가는 것을 막으려고) — 잠시 뒤 다시 해 볼게요.", notBefore: this.d.now() + HELD_REFUSED_BACKOFF_MS });
        return;
      }
      // ★쓰기 바로 앞에서 관측 나이를 다시 잰다(codex 3R blocking) — 영속·그리기가 늦어 마지막 입력줄 관측이 낡았으면 쓰지 않는다.
      if (this.d.now() - fresh.obsAt > OBS_MAX_MS) {
        this.patchMsg(id, { step: "held", sentAt: null, code: "status_stale", note: "마스터 입력줄 확인이 오래돼서 쓰지 않았어요 — 다시 확인되면 보낼게요." });
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
    // 이 말이 나갔으면(붙잡히지 않았으면) 다음 차례 1건 — 붙잡혔으면 멈춘다(뒤 말이 앞지르지 않게 · 다음은 poll 이 오래된 것부터).
    if (this.s.msgs.find((x) => x.id === id)?.step !== "held") await this.pump();
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
      void this.confirm.scanStep(); // (조각 4) 대화 화면을 연 때보다 앞 기록의 표식을 한 토막씩
      this.lastWorking = fresh.master ? fresh.master.working : null;
      const awaiting = this.s.msgs.some((m) => ["injected", "checking", "slow", "delivered", "replying"].includes(m.step));
      // 활동이 바뀐 틱 1회 — (조각 4) 기다리는 말이 없어도 마스터가 **쉬게 된** 틱이면 읽는다(마스터가 스스로 낸 물음 표식 · 새 주기 조회 0)
      if ((awaiting || this.lastWorking === false) && prevWorking !== null && prevWorking !== this.lastWorking) void this.readTranscript();
      else if (this.offset === null && fresh.master) void this.readTranscript(); // 마스터를 안 첫 틱에 세션 시작점을 잡아 둔다(보내기 길에서 그 RPC 를 빼려고)
      const now = this.d.now();
      this.markStale();
      const held = this.s.msgs.find(autoHeld); // 가장 오래된 자동 말 하나 — 쉼 중이면 이번 틱은 아무것도 안 보냄
      if (held && (held.notBefore === undefined || now >= held.notBefore) && this.gateOf(fresh).ok) heldId = held.id;
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
        this.confirm.startSession(this.sessionId, m.surface_id, r.next_offset);
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
          this.consumed.clear();
          this.offset = null;
          this.confirm.resetSession();
          await this.initOffset();
          return;
        }
        if (r.reset === true) {
          // 파일이 줄었다(잘림·교체) — 다시 읽은 옛 레코드로 새 전달·답 근거를 만들지 않는다(codex 1R major). 끝에서 다시 시작.
          this.offset = null;
          this.confirm.resetSession();
          await this.initOffset();
          return;
        }
        const recs = Array.isArray(r.records) ? (r.records as Rec[]) : [];
        this.offset = r.next_offset;
        if (recs.length) this.confirm.onTail(recs);
        if (recs.length) {
          const applied = applyRecords(this.s.msgs, recs, this.consumed);
          for (const u of applied.consumed) this.consumed.add(u);
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
