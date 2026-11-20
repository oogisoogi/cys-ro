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
import { applyRecords, applyRefusedAtWrite, applyRefusedById, canRetry, mergeOutcome, READ_AFTER_MS, rematchPending, SENDING_SILENT_MS, settleSteps, SLOW_MS, stepFromOutcome, type Msg, type PendingRec, type Rec, type Reply, type Step } from "./judge/msgstep";
import { applyQueueEvent, autoHoldRemainingMs, queueEventOf, type AutoMsg } from "./judge/autostep";
import { ConfirmBook } from "./confirm";
import { ResultBook } from "./results"; // (s79 조각 7) 결과 받기 장부

export const HOLD_KEY = "cys-chat-hold";
/** 붙잡은 말 상한(설계 §5-3 · 넘으면 새 말을 받지 않고 안내). */
export const HOLD_MAX = 20;
/** 화면에 남기는 말 수(메모리) — 끝나지 않은 말은 밀어내지 않는다. */
export const LOG_MAX = 200;
/** 대화 화면이 켜져 있을 때 마스터 상태 조회 주기(작업 화면 3초 고리와 같은 박자 · 조각 2 에서 한 벌로 합침 📌). */
export const POLL_MS = 3_000;
/** 쓰기 직전 입력줄 관측(org.status 왕복)의 유효 상한(설계 목표값) — 넘으면 그 관측으로 쓰지 않는다(0.5 M12: 데몬 몫 < 1ms). */
export const OBS_MAX_MS = 500;
/** (조각 3 고침 · 검증 지적 F) 시간 상한을 넘긴 재조회 표지. */
const TIMED_OUT: unique symbol = Symbol("timed_out");
/** 재조회가 시간 상한을 넘겨 쓰지 않은 말의 까닭 코드. */
export const STATUS_TIMEOUT = "status_timeout";
/** 앱을 다시 켜기 전에 붙잡아 둔(저장소에서 읽은) 말 — 자동으로 보내지 않는다. */
export const RESTORED = "restored";
/** 붙잡은 지 이만큼 지난 말은 자동으로 보내지 않는다 — 사람 클릭 1회로만(master 결정 11-17 23:2x · 10분 · VERIFY 지적 5). */
export const HELD_MAX_AGE_MS = 600_000;
export const STALE = "stale";
/** 앞 말(쓰는 중이거나 붙잡힌 말) 뒤에 줄 선 말의 표지 — 오래된 것부터 1건씩(설계 §2-5 · VERIFY 지적 1). */
const AFTER_PREV = "after_prev";
/** (조각 3) 같은 글의 앞 말이 아직 끝나지 않았는데(보내는 중·전달 확인 중·확인 중·오래 걸려요·차례 기다림·자동으로 나갈 붙잡음) 또 보낸 말.
 *  자동으로 보내지 않는다 — 앞 말이 끝난 뒤 사람이 「한 번 더 보내기」를 눌러야 나간다(같은 말 두 번 방지 · NFR-R1 · 「불명 = 다시 보내기 0」). */
export const DUP = "dup_pending";

/** 사람이 눌러야만 나가는 붙잡은 말(다시 켠 뒤 복원 · 10분 넘음 · 같은 말 겹침). */
export function needsClick(m: Msg): boolean {
  return m.step === "held" && (m.code === RESTORED || m.code === STALE || m.code === DUP);
}

/** (조각 3) 끝나지 않은 말 — 같은 글을 또 보내면 두 번 갈 수 있는 상태. */
const UNRESOLVED: ReadonlySet<Step> = new Set<Step>(["sending", "injected", "checking", "slow", "queued_hold"]);

/** (조각 3) 이 글과 같은 글의 앞 말이 아직 끝나지 않았는가(exceptId = 자기 자신 제외). 순수. */
export function dupPending(msgs: readonly Msg[], text: string, exceptId?: string): boolean {
  return msgs.some((m) => m.id !== exceptId && m.text === text && (UNRESOLVED.has(m.step) || autoHeld(m)));
}
/** 문턱이 열리면 자동으로 나갈 붙잡은 말. */
function autoHeld(m: Msg): boolean {
  return m.step === "held" && !needsClick(m);
}
/** (조각 3 고침 · 검증 지적 H · master 결정 = 거둠) 같은 글의 다른 말이 이미 「전달됨」 이상인가 — 그러면 확정 실패 말의 「다시 보내기」를 거둔다. 순수. */
export function sameTextDelivered(msgs: readonly Msg[], text: string, exceptId?: string): boolean {
  return msgs.some((m) => m.id !== exceptId && m.text === text && (m.step === "delivered" || m.step === "replying" || m.step === "replied"));
}
export const SAME_DELIVERED_NOTE = "같은 글이 이미 전달됐어요 — 다시 보내지 않아요.";
/** (조각 3 고침 · 검증 지적 B) 그릴 차례(순수) — 사람 말 차례는 그대로 두고, 어느 말에도 안 묶인 마스터 글을 시각(at)이 그 뒤인 첫 사람 말 앞에 끼운다.
 *  사람 말 시각 = 보낸 시각(없으면 받아들인 시각) · 시각 없는 글은 맨 뒤. */
export type LogItem = { kind: "msg"; m: Msg } | { kind: "stray"; r: Reply };
export function logOrder(msgs: readonly Msg[], stray: readonly Reply[]): LogItem[] {
  const out: LogItem[] = [];
  const timed = stray.filter((r) => typeof r.at === "number").sort((a, b) => (a.at as number) - (b.at as number)); // (codex 1R minor) 시각으로 안정 정렬(입력 순서 의존 X)
  let k = 0;
  for (const m of msgs) {
    const t = m.sentAt ?? m.createdAt;
    while (k < timed.length && (timed[k].at as number) < t) out.push({ kind: "stray", r: timed[k++] });
    out.push({ kind: "msg", m });
  }
  while (k < timed.length) out.push({ kind: "stray", r: timed[k++] });
  for (const r of stray) if (typeof r.at !== "number") out.push({ kind: "stray", r });
  return out;
}
/** (조각 3 고침 · 검증 지적 C) 짝 못 찾은 사람 레코드를 들고 있는 상한(개수 · 시간 = SLOW_MS). */
const PENDING_USER_MAX = 50;
/** 데몬이 승인 창으로 거부한 말을 다시 문턱에 거는 최소 간격(설계 목표값 · 창이 닫히면 문턱 재통과 때 1회). */
export const HELD_REFUSED_BACKOFF_MS = 15_000;
/** 세션 기록 한 번 읽기에서 이어 읽는 최대 횟수(2 MiB × 이 수). */
const READ_CHAIN_MAX = 3;
/** ★1.1.16(S3-1) 응답보다 먼저 온 거부 사건 번호를 기억하는 개수(쓰기는 한 번에 1건 — 여유분) */
const REFUSED_EARLY_MAX = 16;

export interface Store {
  get(k: string): string | null;
  set(k: string, v: string): void;
  remove(k: string): void;
}

export interface Deps {
  invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown>;
  /** (조각 3) 데몬 사건 구독(Tauri `daemon-event`) — 대화 화면이 켜져 있을 때만 건다 · 없으면 사건 근거 없이 돈다(시험·옛 판). */
  listen?(name: string, handler: (e: { payload: unknown }) => void): Promise<() => void>;
  now(): number;
  setTimeout(fn: () => void, ms: number): unknown;
  clearTimeout(h: unknown): void;
  store: Store;
  /** org.status 행 → 지금 답하는 중인가(appearance.nodeWorking) */
  working(row: Record<string, unknown>): boolean;
  /** (조각 4) daemon-event 구독 — 대화 화면이 켜져 있을 때만(attach~detach). 없으면 사건 없이(멈춤 = org.status·5분 규칙만).
   *  (통합 1116) 조각 3 의 `listen(name, handler)` 와 이름이 겹쳐 `listenDaemon` 으로 — 두 구독 모두 그대로 산다. */
  listenDaemon?(fn: (ev: unknown) => void): () => void;
  /** (조각 4) 다른 화면으로(「작업 화면에서 보기」) — registry.choose. */
  goView?(id: string): void;
  /** (조각 4 · 검증 F1) 본부 데몬 socket_slug(Tauri default_socket_slug) — 사건의 slug 대조용 · 대화 화면이 켜질 때 1회. */
  defaultSlug?(): Promise<string>;
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
  /** (조각 3) 추적 중인 기계 문안(데몬 큐 항목) — 단계는 큐 사건으로만(judge/autostep) */
  autos: AutoMsg[];
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
  private s: ChatState = { master: undefined, health: "unknown", confirms: null, msgs: [], stray: [], draft: "", notice: null, pollFailed: false, autos: [], rev: 0 };
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
  private readAgain = false;
  private readTimers = new Set<unknown>();
  private attached = false;
  private lastWorking: boolean | null = null;
  /** (조각 3) 지난 조회 시각 — 「두 조회 사이 새 출력」 판정용 */
  private lastPollAt: number | null = null;
  /** (조각 3) 사건 구독 해제 함수 · 구독 세대(붙였다 뗐다 경합 방지) · 기본 데몬 소켓 이름(부서 데몬 사건과 좌석 번호가 겹침) */
  private unlisten: (() => void) | null = null;
  private listenGen = 0;
  private defaultSlug: string | null = null;
  /** (조각 3) 마지막으로 바이트가 나갔을 수 있는 사람 보내기 시각(R3 — 기계 문안 묶임 계산) */
  private lastHumanSentAt: number | null = null;
  /** (조각 3 고침 · 검증 지적 C) 짝 못 찾은 사람 레코드(받은 시각 at) — 말이 짝 후보가 되면 다시 대어 본다 · 메모리만 · 세션이 바뀌면 비움 */
  private pendingUser: PendingRec[] = [];
  /** (codex 1R major) 세션 시작점 조회 세대 — 늦게 돌아온 옛 조회(시간 상한을 넘겼거나 뒤 조회가 이미 시작된 것)는 offset·세션을 바꾸지 못한다 */
  private initGen = 0;
  /** (조각 4) 확인 대기 장부 — 띠·표식·직접 허락. */
  readonly confirm: ConfirmBook;
  /** (조각 4 · 통합 1116) 장부용 사건 구독 해제 — 조각 3 구독(unlisten)과 따로 든다(두 구독 모두 대화 화면 attach~detach 동안만). */
  private unlistenConfirm: (() => void) | null = null;
  /** (s79 조각 7) 결과 받기 장부 — 답 속 경로 · 스킬 산출 폴더 · 열기/폴더 보기. */
  readonly results: ResultBook;
  /** (s79 조각 9) 이번 실행에서 대화 화면을 한 번이라도 켰는가 — 아니면 작업 화면 띠도 조회 0(대화 화면을 안 고르면 invoke 0 불변식). */
  private everAttached = false;
  /** (s79 조각 9) 작업 화면에서 띠만 살피는 중 — 조회·세션 읽기만 하고 붙잡은 말은 보내지 않는다(사람이 마스터 창에 치는 중일 수 있음 · 4군 ②). */
  private watchOnly = false;
  /** (s79 · codex 3R ②) await 뒤 화면 재판정 — **한 도우미**(deliver · ResultBook.act · ConfirmBook.decide 공용): 작업 화면 살핌 중(watchOnly)이면 false = 쓰기·OS 행동 0(붙잡음).
   *  기다리는 사이(재조회·list_dir·feed/org) 사람이 작업 화면을 누를 수 있다 — 그때는 사람이 마스터 창에 직접 칠 수 있으므로 대화 화면의 행동을 이어 하지 않는다. */
  readonly onChatScreen = (): boolean => !this.watchOnly;

  constructor(private readonly d: Deps) {
    this.loadHold();
    this.confirm = new ConfirmBook({ invoke: d.invoke, now: d.now, store: d.store, onChat: this.onChatScreen }, () => this.set({}));
    this.results = new ResultBook({ invoke: d.invoke, now: d.now, store: d.store, onChat: this.onChatScreen }, () => this.set({}));
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
    this.attachAs(false);
  }

  /** (s79 · codex 3R ③) 켜기 한 곳 — ★살핌 표지(watchOnly·paused)를 **먼저** 세우고 구독·조회를 시작한다(옛 순서 = attach 뒤에 세움 → 전환 순간 대화 화면 몫 조회가 나갔다).
   *  살핌(watch) = 작업 화면 띠 자료만: 사건 구독 · 세션 읽기(chat_transcript) · poll(feed_list·org_status) — default_socket_slug·home_dir_path 0(대화 화면에서 이미 받아 둔 값을 씀). */
  private attachAs(watch: boolean): void {
    this.watchOnly = watch;
    this.results.paused = watch; // (s79 · V4) 작업 화면 살핌 중엔 list_dir 0
    this.attached = true;
    if (!watch) this.everAttached = true;
    if (!this.unlistenConfirm && this.d.listenDaemon)
      this.unlistenConfirm = this.d.listenDaemon((ev) => {
        this.confirm.onEvent(ev);
        this.results.onEvent(ev); // (s79 조각 7) skill.run_finished
      });
    if (!watch && this.d.defaultSlug)
      void this.d
        .defaultSlug()
        .then((s) => {
          const slug = typeof s === "string" && s ? s : null;
          this.confirm.setHqSlug(slug);
          this.results.setHqSlug(slug); // (s79 조각 7)
        })
        .catch(() => {});
    if (!watch) void this.results.start(); // (s79 조각 7) 홈 1회(살핌 중 = 다시 묻지 않음)
    void this.readTranscript();
    void this.startListening();
  }

  /** (s79 조각 9 · FR-C7) 작업 화면이 켜짐 — 대화 화면을 이번 실행에서 켠 적이 있을 때만 띠 자료를 계속 받는다(아니면 false · 조회 0).
   *  붙잡은 말은 보내지 않는다(watchOnly) — 작업 화면에서는 사람이 마스터 창에 직접 칠 수 있다. */
  watchStart(): boolean {
    if (!this.everAttached) return false;
    this.attachAs(true);
    return true;
  }

  /** (s79 조각 9) 작업 화면이 내려감. */
  watchStop(): void {
    if (!this.watchOnly) return;
    this.watchOnly = false;
    this.detach();
  }

  /** (s79 조각 9) 작업 화면 띠가 이 실행에서 자료를 받을 수 있는가(대화 화면을 켠 적이 있음). */
  get warm(): boolean {
    return this.everAttached;
  }

  /** 대화 화면이 내려감 — 읽기 예약 해제(공통층 상태·붙잡은 말은 그대로 · §4-3). */
  detach(): void {
    // (s79 조각 9) registry 는 새 화면을 먼저 띄우고 옛 화면을 내린다 — 대화 → 작업 전환이면 작업 화면이 이미 살피는 중(watchOnly)이다.
    //   그때 대화 화면의 내리기가 구독·세션 읽기를 끄면 작업 화면 띠가 새 물음을 못 본다 → 살피는 중이면 끄지 않는다(끄는 것은 watchStop).
    if (this.watchOnly) return;
    this.attached = false;
    this.unlistenConfirm?.();
    this.unlistenConfirm = null;
    for (const h of this.readTimers) this.d.clearTimeout(h);
    this.readTimers.clear();
    this.listenGen++;
    if (this.unlisten) {
      try {
        this.unlisten();
      } catch {
        /* 이미 풀림 */
      }
      this.unlisten = null;
    }
  }

  // ---------- 데몬 사건(조각 3 · 이미 방송되는 사건만 · 새 조회 0) ----------

  private async startListening(): Promise<void> {
    if (!this.d.listen || this.unlisten) return;
    if (this.defaultSlug === null && this.watchOnly) return; // (s79 · codex 3R ③) 살핌 중엔 default_socket_slug 0 — 소켓 이름을 모르면 사건을 하나도 받지 않으니 구독도 안 함(대화 화면에서 받음)
    const gen = ++this.listenGen;
    if (this.defaultSlug === null) {
      try {
        const v = await this.d.invoke("default_socket_slug");
        this.defaultSlug = typeof v === "string" && v.length > 0 ? v : null;
      } catch {
        this.defaultSlug = null;
      }
    }
    if (gen !== this.listenGen || !this.attached) return;
    try {
      const un = await this.d.listen("daemon-event", (e) => this.onDaemonEvent(e.payload));
      if (gen !== this.listenGen || !this.attached) un();
      else this.unlisten = un;
    } catch {
      /* 구독 실패 = 사건 근거 없이(세션 기록·응답만으로) 돈다 */
    }
  }

  /** ★1.1.16(S3-1) 응답보다 먼저 온 「쓰기 직전 거부」 사건의 요청 번호(최근 몇 개만). 응답이 그 번호를 실어 오면 그때 적용한다. */
  private refusedEarly: string[] = [];
  private applyEarlyRefusal(id: string): void {
    const rid = this.s.msgs.find((x) => x.id === id)?.requestId;
    if (!rid || !this.refusedEarly.includes(rid)) return;
    this.refusedEarly = this.refusedEarly.filter((x) => x !== rid);
    const [next] = applyRefusedById(this.s.msgs, rid);
    if (next.some((m, i) => m !== this.s.msgs[i])) this.putMsgs(next);
  }

  /** 데몬 사건 하나 — 기본 데몬(마스터가 사는 곳) 사건만 받는다(부서 데몬은 좌석 번호가 겹친다 · 소켓 이름을 모르면 아무것도 받지 않음). */
  onDaemonEvent(raw: unknown): void {
    const e = raw as { name?: unknown; socket_slug?: unknown; surface_id?: unknown } | null;
    if (!e || typeof e.name !== "string") return;
    if (this.defaultSlug === null || e.socket_slug !== this.defaultSlug) return;
    if (e.name === "input.refused_at_write") {
      // ★1.1.16(TICKET=cysr-1116-debt-d-1119 · S3-1): 요청 번호가 실린 사건(원자 제출 Enter 직전 거부) = 번호로만 짝짓는다 — 좌석·5초 창 0.
      const rid = (raw as { payload?: { request_id?: unknown } }).payload?.request_id;
      if (typeof rid === "string" && rid.length > 0) {
        const [next, found] = applyRefusedById(this.s.msgs, rid);
        if (!found) this.refusedEarly = [...this.refusedEarly.filter((x) => x !== rid), rid].slice(-REFUSED_EARLY_MAX); // 응답보다 먼저 옴
        else if (next.some((m, i) => m !== this.s.msgs[i])) this.putMsgs(next);
        return;
      }
      if (typeof e.surface_id !== "number") return;
      // 사건 시각 = 데몬 timestamp(초) — 받은 시각을 쓰면 데몬 재연결 뒤 다시 흘러온 옛 사건이 방금 보낸 말에 붙는다(검토 지적 5).
      const ts = (raw as { timestamp?: unknown }).timestamp;
      if (typeof ts !== "number" || !Number.isFinite(ts)) return;
      const next = applyRefusedAtWrite(this.s.msgs, e.surface_id, Math.round(ts * 1000));
      if (next.some((m, i) => m !== this.s.msgs[i])) this.putMsgs(next);
      return;
    }
    const q = queueEventOf(raw);
    if (!q || this.s.autos.length === 0) return;
    const autos = applyQueueEvent(this.s.autos, q);
    if (autos.some((a, i) => a !== this.s.autos[i])) this.set({ autos });
  }

  /** (조각 3) 기계 문안 1건을 추적한다(보내는 쪽 = 조각 5 깨움 · chat_send{kind:auto} 응답의 queue_entry_id). 같은 번호는 한 번만. */
  trackAuto(entryId: string, seat: number): void {
    if (this.s.autos.some((a) => a.entryId === entryId)) return;
    this.set({ autos: [...this.s.autos, { entryId, seat, step: "queued" as const, lastSeq: -1 }].slice(-LOG_MAX) });
  }

  /** (조각 3 · R3) 지금 기계 문안을 큐에 넣으면 데몬이 묶어 둘 남은 시간(ms) — 마지막 사람 보내기 뒤 31.2초(0.5 M10). */
  autoHoldRemainingMs(): number {
    return autoHoldRemainingMs(this.lastHumanSentAt, this.d.now());
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
    if (this.pendingUser.length) {
      // (조각 3 고침 · 검증 지적 C) 말 단계가 바뀔 때마다 앞서 짝 못 찾은 사람 레코드를 다시 대어 본다(오래된 것은 버림)
      const now = this.d.now();
      this.pendingUser = this.pendingUser.filter((p) => now - p.seenAt <= SLOW_MS);
      const rm = rematchPending(kept, this.pendingUser);
      if (rm.changed) {
        kept = rm.msgs;
        this.pendingUser = rm.pool;
        for (const m of kept) if (m.userUuid) this.consumed.add(m.userUuid);
      }
    }
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

  /** (조각 3 고침 · 검증 지적 F) 재조회 전체에 시간 상한(OBS_MAX_MS · 조각 4 ORG_MAX_MS 와 같은 500ms) — 데몬이 살아 있지만 멈춰도 보내기·조회 고리가 멈추지 않게.
   *  넘으면 모름(마스터 undefined · 승인 대기 null → 문턱이 붙잡음 · 쓰기 0) + timedOut 표지. 늦게 온 답은 버린다. */
  private async freshBounded(): Promise<{ master: MasterRow | null | undefined; approvals: number[] | null; obsAt: number; timedOut?: boolean; feed?: unknown; org?: unknown }> {
    const r = await this.bounded(this.fetchFresh());
    return r === TIMED_OUT ? { master: undefined, approvals: null, obsAt: this.d.now(), timedOut: true } : r;
  }

  private bounded<T>(p: Promise<T>): Promise<T | typeof TIMED_OUT> {
    return new Promise((res) => {
      let done = false;
      const h = this.d.setTimeout(() => {
        if (done) return;
        done = true;
        res(TIMED_OUT);
      }, OBS_MAX_MS);
      p.then(
        (v) => {
          if (done) return;
          done = true;
          this.d.clearTimeout(h);
          res(v);
        },
        () => {
          if (done) return;
          done = true;
          this.d.clearTimeout(h);
          res(TIMED_OUT);
        },
      );
    });
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
    // (조각 3) 같은 글의 앞 말이 아직 끝나지 않았으면 이 말은 자동으로 보내지 않는다(사람이 같은 말을 다시 친 경우 · 불명 응답 뒤 다시 누름 포함).
    if (dupPending(this.s.msgs, text)) {
      const dup: Msg = { id: `m${this.d.now()}-${++this.seq}`, text, createdAt: this.d.now(), sentAt: null, step: "held", code: DUP, note: "같은 말이 아직 확인 중이라 두 번 가지 않게 붙잡아 뒀어요 — 앞 말이 끝나면 「한 번 더 보내기」로 보낼 수 있어요(글을 조금 바꾸면 바로 보내요).", thread: [], replies: [] };
      this.s = { ...this.s, draft: "", notice: null };
      this.putMsgs([...this.s.msgs, dup]);
      return;
    }
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
    if (this.watchOnly) return; // (s79 · codex 1R major) 앞 말 전달 중에 작업 화면으로 옮겼으면 다음 붙잡은 말은 대화 화면으로 돌아온 뒤에(사람이 마스터 창에 칠 수 있음)
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
    if (m.code === DUP && dupPending(this.s.msgs, m.text, m.id)) {
      this.set({ notice: "같은 말이 아직 확인 중이에요 — 앞 말이 끝나면 보낼 수 있어요." }); // 불명·확인 중인 앞 말이 있는 동안은 사람 클릭으로도 다시 보내지 않는다
      return;
    }
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
    if (sameTextDelivered(this.s.msgs, m.text, m.id)) {
      this.set({ notice: SAME_DELIVERED_NOTE }); // (조각 3 고침 · 검증 지적 H) 같은 글이 이미 전달됨 → 다시 보내기 거둠
      return;
    }
    if (dupPending(this.s.msgs, m.text, m.id)) {
      // (조각 3 · M2·M3 하네스 seed 131 이 찾음) 같은 글의 다른 말이 아직 확인 중이면 다시 보내기도 막는다 — 두 번 갈 수 있다.
      this.set({ notice: "같은 말이 아직 확인 중이에요 — 그 말이 끝나면 다시 보낼 수 있어요." });
      return;
    }
    const msg: Msg = { id: `m${this.d.now()}-${++this.seq}`, text: m.text, createdAt: this.d.now(), sentAt: null, step: "sending", thread: [], replies: [], retried: true };
    this.putMsgs([...this.s.msgs.map((x) => (x.id === id ? { ...x, retried: true } : x)), msg]);
    await this.deliver(msg.id);
  }

  /** 한 말을 문턱에 걸고, 통과면 원자 제출 1회. */
  private async deliver(id: string): Promise<void> {
    if (this.writing) return;
    this.writing = true;
    try {
      let fresh = await this.freshBounded(); // ★쓰기 직전 재조회 1회(3초 목록을 믿지 않음 · 시간 상한 = 검증 지적 F)
      this.applyFresh(fresh);
      if (this.offset === null && fresh.master) {
        // 보낸 user 레코드를 건너뛰지 않게 세션 기록 시작점을 먼저 잡는다 — 이 RPC 가 문턱 판정과 쓰기 사이에 끼지 않게 다시 조회한다.
        // (codex 2R major) 시작점 조회가 상한을 넘겼거나 겹친 조회에 밀려 결과를 버렸으면(「stale」) 시작점이 정해지지 않은 채 쓰지 않는다 — 붙잡음.
        //   조회는 끝났지만 기록이 없다(「none」 · 윈도·파일 없음)면 예전처럼 보낸다(전달됨 0 · 오래 걸려요).
        const init = await this.initOffset();
        fresh = init === "stale" ? { master: undefined, approvals: null, obsAt: this.d.now(), timedOut: true } : await this.freshBounded();
        this.applyFresh(fresh);
      }
      if (fresh.timedOut) {
        // 아직 안 썼다(바이트 0) → 「확인 중」이 아니라 붙잡음 · 다시 확인되면 poll 이 문턱에 다시 건다.
        this.patchMsg(id, { step: "held", sentAt: null, code: STATUS_TIMEOUT, note: "마스터 상태 확인이 늦어져서 아직 쓰지 않았어요 — 다시 확인되면 보낼게요." });
        return;
      }
      const g = this.gateOf(fresh);
      if (!g.ok) {
        this.patchMsg(id, { step: "held", code: g.code, note: g.msg });
        return;
      }
      // (s79 · 독립 검증 V3) 재조회를 기다리는 사이 작업 화면으로 옮겼으면 쓰지 않는다 — 작업 화면에선 사람이 마스터 창에 직접 칠 수 있다(쓰기 0).
      //   대화 화면으로 돌아오면 poll 이 다시 문턱에 건다.
      if (!this.onChatScreen()) {
        this.patchMsg(id, { step: "held", sentAt: null, code: "work_view", note: "작업 화면으로 옮겨서 아직 쓰지 않았어요 — 대화 화면으로 돌아오면 보낼게요." });
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
      if (!this.patchMsg(id, { step: "sending", sentAt, seat: m.surface_id, code: undefined, note: undefined, notBefore: undefined })) {
        this.patchMsg(id, { step: "held", sentAt: null, code: "store_failed", note: "앱 저장소에 쓸 수 없어 보내지 않았어요(같은 말이 두 번 가는 것을 막으려고) — 잠시 뒤 다시 해 볼게요.", notBefore: this.d.now() + HELD_REFUSED_BACKOFF_MS });
        return;
      }
      // ★쓰기 바로 앞에서 관측 나이를 다시 잰다(codex 3R blocking) — 영속·그리기가 늦어 마지막 입력줄 관측이 낡았으면 쓰지 않는다.
      if (this.d.now() - fresh.obsAt > OBS_MAX_MS) {
        this.patchMsg(id, { step: "held", sentAt: null, code: "status_stale", note: "마스터 입력줄 확인이 오래돼서 쓰지 않았어요 — 다시 확인되면 보낼게요." });
        return;
      }
      let res: unknown;
      // (조각 3) 응답 없이 3초 = 「확인 중」(보내는 중이 끝없이 머물지 않게 · 다시 보내기 0). 응답이 오면 그 응답으로 바뀐다.
      const silent = this.d.setTimeout(() => {
        this.putMsgs(settleSteps(this.s.msgs, this.d.now(), null));
        this.scheduleReads();
      }, SENDING_SILENT_MS);
      try {
        res = await this.d.invoke("chat_send", { socket: null, surfaceId: m.surface_id, text: msg.text, kind: "human" });
      } catch (e) {
        res = { outcome: "uncertain", code: "invoke_error", message: String(e) }; // Tauri 다리 자체 실패 = 쓰였는지 모름
      } finally {
        this.d.clearTimeout(silent);
      }
      const r = (res ?? {}) as { outcome?: unknown; code?: unknown; message?: unknown; result?: { request_id?: unknown } };
      const step = stepFromOutcome(r.outcome);
      // ★1.1.16(S3-1): 데몬 요청 번호를 그 말에 붙인다(쓰기 직전 거부 사건과 번호로 짝짓기) · 먼저 온 사건이면 지금 적용한다(아래 patch 뒤).
      const rid = typeof r.result?.request_id === "string" && r.result.request_id.length > 0 ? r.result.request_id : undefined;
      if (rid) this.patchMsg(id, { requestId: rid });
      const code = typeof r.code === "string" ? r.code : undefined;
      if (step !== "held" && step !== "failed" && step !== "queued_hold") this.lastHumanSentAt = sentAt; // 바이트가 나갔을 수 있음(R3)
      const cur = this.s.msgs.find((x) => x.id === id);
      const merged = cur ? mergeOutcome(cur, step) : {};
      if (cur && merged.step === undefined) {
        // 세션 기록으로 이미 「전달됨」 이상(또는 쓰기 직전 거부 사건) — 늦게 온 응답(written·불명)이 되돌리지 않는다.
        if (cur.step === "checking") this.scheduleReads();
      } else if (step === "held") {
        // 데몬 거부(바이트 0) — feed 대기 항목 없이 창만 떠 있을 수 있다(0.5 숫자 3 술어 차이) → 같은 말 재시도는 한동안 쉰다(3초마다 두드리지 않음 · 4군 ①).
        this.patchMsg(id, { ...merged, step, sentAt: null, code, notBefore: this.d.now() + HELD_REFUSED_BACKOFF_MS, note: "마스터 창에 확인할 것이 떠 있어서 쓰지 않았어요 — 그 확인이 끝나면 보낼게요." });
        return;
      } else if (step === "failed") {
        this.patchMsg(id, { ...merged, step, code, note: `보내지 못했어요${code ? ` (${code})` : ""}.` });
        return;
      } else {
        this.patchMsg(id, { ...merged, step, code, note: step === "queued_hold" ? "업데이트 중이라 차례를 기다려요 — 끝나면 데몬이 전달해요." : undefined });
        if (step === "injected" || step === "checking") this.scheduleReads();
      }
    } finally {
      this.writing = false;
    }
    this.applyEarlyRefusal(id);
    // 이 말이 나갔으면(붙잡히지 않았으면) 다음 차례 1건 — 붙잡혔으면 멈춘다(뒤 말이 앞지르지 않게 · 다음은 poll 이 오래된 것부터).
    if (this.s.msgs.find((x) => x.id === id)?.step !== "held") await this.pump();
  }

  /** 대화 화면이 켜져 있을 때 POLL_MS 마다. 붙잡은 말이 있고 문턱이 열렸으면 오래된 것 1건을 보낸다(그 안에서 다시 재조회). */
  async poll(): Promise<void> {
    // (조각 3 · 하네스 seed 49) 쓰는 중에도 조회·단계 갱신은 한다 — 응답이 걸린 보내기(수 초) 동안 다른 말의 「답함」·「오래 걸려요」가 멈추지 않게.
    //   보내기는 deliver 가 쓰는 중이면 바로 돌아간다(겹쳐 쓰기 0 · 클릭 1 → 호출 ≤ 1).
    if (this.polling) return;
    this.polling = true;
    let heldId: string | null = null;
    try {
      const fresh = await this.freshBounded(); // (조각 3 고침 · 검증 지적 F) 멈춘 데몬에 조회 고리가 묶이지 않게
      const prevWorking = this.lastWorking;
      this.applyFresh(fresh);
      void this.confirm.scanStep(); // (조각 4) 대화 화면을 연 때보다 앞 기록의 표식을 한 토막씩
      if (!this.watchOnly) void this.results.tick(); // (s79 조각 7) 아직 모르는 결과의 실재 확인(틱당 상한) · 작업 화면 살핌 중 = 0(V4 · 조회 3종만)
      this.lastWorking = fresh.master ? fresh.master.working : null;
      const awaiting = this.s.msgs.some((m) => ["injected", "checking", "slow", "delivered", "replying"].includes(m.step));
      // (조각 3 · 하네스 seed 370) 짧은 답(두 조회 사이 3초 안에 일 시작·끝)은 「활동 바뀜」으로 안 잡힌다 → 마스터 출력이 지난 조회 뒤에 있었으면(idle_secs) 그 틱도 읽는다.
      //   새 조회 0(이 조회 값만 씀) · 로컬 세션 파일 오프셋 읽기 · 기다리는 말이 있을 때만.
      const pollAt = this.d.now();
      const idle = fresh.master ? fresh.master.idle_secs : null;
      const outputSincePoll = this.lastPollAt !== null && typeof idle === "number" && idle * 1000 < pollAt - this.lastPollAt;
      this.lastPollAt = pollAt;
      // (조각 4) 기다리는 말이 없어도 마스터가 **쉬게 된** 틱이면 읽는다(마스터가 스스로 낸 물음 표식 · 새 주기 조회 0)
      const changed = prevWorking !== null && prevWorking !== this.lastWorking;
      if ((changed && (awaiting || this.lastWorking === false)) || (awaiting && outputSincePoll)) void this.readTranscript(); // 활동이 바뀐 틱 · 새 출력이 있던 틱
      else if (this.offset === null && fresh.master) void this.readTranscript(); // 마스터를 안 첫 틱에 세션 시작점을 잡아 둔다(보내기 길에서 그 RPC 를 빼려고)
      const now = this.d.now();
      this.markStale();
      const held = this.s.msgs.find(autoHeld); // 가장 오래된 자동 말 하나 — 쉼 중이면 이번 틱은 아무것도 안 보냄
      if (!this.watchOnly && held && (held.notBefore === undefined || now >= held.notBefore) && this.gateOf(fresh).ok) heldId = held.id; // (s79 조각 9) 작업 화면에서 살피는 중엔 보내지 않음
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

  /** 세션 기록 시작점(파일 끝)을 잡는다 — 결과: ok(잡음) · none(조회는 끝났지만 기록 없음·오류) · stale(상한을 넘겼거나 더 새 조회에 밀려 결과를 버림).
   *  (codex 1R·2R major) 모든 시작점 조회에 상한(OBS_MAX_MS)과 세대를 건다 — 늦게 돌아온 옛 조회가 파일 끝으로 덮어 보낸 말 레코드를 건너뛰지 않게. */
  private async initOffset(): Promise<"ok" | "none" | "stale"> {
    const m = this.s.master;
    if (!m) return "none";
    const gen = ++this.initGen; // 새 조회가 시작되면 앞선 조회의 늦은 결과는 버린다
    // (통합 1116 · S3-11 codex 1R major) 조회 **거절**은 시간 초과가 아니다 — 끝난 오류 = none(예전처럼 보냄). bounded 는 거절도 TIMED_OUT 으로
    //   합치므로 여기서 먼저 null 로 받는다(기록 조회만 계속 실패하는 좌석에서 말이 영원히 붙잡히지 않게). 세대가 밀렸으면 아래 stale 그대로.
    const r = (await this.bounded(this.d.invoke("chat_transcript", { socket: null, surfaceId: m.surface_id, afterOffset: 0, fromEnd: true }).catch(() => null))) as
      | { status?: unknown; next_offset?: unknown; session_id?: unknown }
      | typeof TIMED_OUT;
    if (r === TIMED_OUT) {
      if (gen === this.initGen) this.initGen++; // 늦게 돌아와도 버리게
      return "stale";
    }
    if (gen !== this.initGen) return "stale";
    if (r?.status === "ok" && typeof r.next_offset === "number") {
      this.offset = r.next_offset;
      this.sessionId = typeof r.session_id === "string" ? r.session_id : null;
      this.confirm.startSession(this.sessionId, m.surface_id, r.next_offset);
      return "ok";
    }
    return "none";
  }

  async readTranscript(): Promise<void> {
    if (this.reading) {
      this.readAgain = true; // (조각 3 · 하네스 seed 49) 읽는 중에 온 계기(활동 바뀜 등)를 버리지 않는다 — 끝난 뒤 1회 더
      return;
    }
    if (!this.attached) return;
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
          skipped_bytes?: unknown;
        } | null;
        if (!r || r.status !== "ok" || typeof r.next_offset !== "number") return;
        if (typeof r.skipped_bytes === "number" && r.skipped_bytes > 0) this.confirm.markLossy(); // (조각 4 · 검증 F3) 2 MiB 넘는 줄을 건너뜀
        const sid = typeof r.session_id === "string" ? r.session_id : null;
        if (sid !== this.sessionId) {
          // 결속 세션이 바뀜(마스터 다시 켜짐·/clear) — 새 파일 끝에서 다시 시작(옛 오프셋으로 새 파일을 읽지 않는다)
          this.sessionId = sid;
          this.consumed.clear();
          this.pendingUser = [];
          this.offset = null;
          this.confirm.resetSession();
          await this.initOffset();
          return;
        }
        if (r.reset === true) {
          // 파일이 줄었다(잘림·교체) — 다시 읽은 옛 레코드로 새 전달·답 근거를 만들지 않는다(codex 1R major). 끝에서 다시 시작.
          this.offset = null;
          this.pendingUser = [];
          this.confirm.resetSession();
          await this.initOffset();
          return;
        }
        const recs = Array.isArray(r.records) ? (r.records as Rec[]) : [];
        this.offset = r.next_offset;
        if (recs.length) this.confirm.onTail(recs);
        if (recs.length) this.results.onTail(recs); // (s79 조각 7) 답 속 경로
        if (recs.length) {
          const applied = applyRecords(this.s.msgs, recs, this.consumed);
          for (const u of applied.consumed) this.consumed.add(u);
          const readAt = this.d.now();
          const pooled = new Set(this.pendingUser.map((p) => p.r.uuid).filter((u): u is string => u !== null));
          for (const r of applied.unmatched) if (r.uuid === null || !pooled.has(r.uuid)) this.pendingUser.push({ r, seenAt: readAt });
          if (this.pendingUser.length > PENDING_USER_MAX) this.pendingUser = this.pendingUser.slice(-PENDING_USER_MAX);
          // 「답함」은 여기서 칠하지 않는다(null) — 들고 있는 활동 값은 이 답보다 옛 관측일 수 있다. 다음 조회(poll)의 새 관측으로만.
          const known = new Set(this.s.stray.map((x) => x.uuid).filter((u): u is string => u !== null));
          const fresh = applied.stray.filter((x) => x.uuid === null || !known.has(x.uuid)).map((x) => (x.at === undefined ? { ...x, at: readAt } : x));
          this.putMsgs(settleSteps(applied.msgs, this.d.now(), null), { stray: [...this.s.stray, ...fresh].slice(-LOG_MAX) });
        }
        if (typeof r.size !== "number" || r.next_offset >= r.size) return;
      }
    } finally {
      this.reading = false;
      if (this.readAgain) {
        this.readAgain = false;
        void this.readTranscript();
      }
    }
  }
}
