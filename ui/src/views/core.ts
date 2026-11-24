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
import { ReviveBook } from "./revive";
import { RailBook } from "./rail";
import { addDropped, withDroppedFiles } from "./judge/dropfiles"; // (TICKET=cysr-1119-s11 · TC3) 끌어 놓은 파일 칩 · 보낼 때 @경로

export const HOLD_KEY = "cys-chat-hold";
/** 붙잡은 말 상한(설계 §5-3 · 넘으면 새 말을 받지 않고 안내). */
export const HOLD_MAX = 20;
/** 화면에 남기는 말 수(메모리) — 끝나지 않은 말은 밀어내지 않는다. */
export const LOG_MAX = 200;
/** 대화 화면이 켜져 있을 때 마스터 상태 조회 주기(작업 화면 3초 고리와 같은 박자 · 조각 2 에서 한 벌로 합침 📌). */
export const POLL_MS = 3_000;
/** (TICKET=cysr-1118u-chat ②) 자동으로 나갈 붙잡은 말이 문턱을 기다리는 동안의 가벼운 재조회 박자(대화 화면 1초 시계).
 *  윈 1.1.17 실측(v2): 쉬는 중 도착 2.6~3.5s / 5.4~5.8s 양분 · 도착 초 mod 3 = 1 · 답 끝 뒤 도착 15.7s — 붙잡힌 말이 POLL_MS(3초) 틱에서만 풀렸다.
 *  가벼운 재조회 = 상태 조회(feed_list·org_status) → 문턱 → 통과면 그 말 1건만(메뉴바·결과·세션 기록 읽기 0). 상태 확인 늦음 계열(slowHeld)은 3초 그대로(느린 연결에 조회를 쌓지 않게). */
export const FAST_POLL_MS = 1_000;
/** 1초 시계가 조금 일찍 불려도(타이머 흔들림) 박자를 한 칸 놓치지 않게 두는 여유. */
const TICK_SLOP_MS = 100;
/** 쓰기 직전 입력줄 관측(org.status 왕복)의 유효 상한(설계 목표값) — 넘으면 그 관측으로 쓰지 않는다(0.5 M12: 데몬 몫 < 1ms). */
export const OBS_MAX_MS = 500;
/** (TICKET=cysr-chat-held-win · ⓐ) 관측 기반 상한의 천장 — 상한 = clamp(최근 왕복 최대 × OBS_RTT_FACTOR, OBS_MAX_MS, OBS_CAP_MS).
 *  OBS_MAX_MS(500)는 0.5 M12 의 **맥 VM 데몬 몫(< 1ms)** 만 재고 정한 값이라 웹뷰→Tauri→파이프 왕복(윈 WebView2 · 연결 1개 직렬 풀)을 담지 못했다.
 *  바닥은 그대로 500(빠른 기계 = 예전과 같음) · 이 기계에서 **실제로 끝난** 조회 왕복이 길면 그만큼만 늘린다 · 천장 2초를 넘는 관측은 여전히 쓰기 근거가 아니다. */
export const OBS_CAP_MS = 2_000;
export const OBS_RTT_FACTOR = 2;
/** 관측 기반 상한이 보는 최근 왕복 수(끝난 조회만 · 늦게 끝나 버린 결과도 왕복 시간은 센다). */
export const OBS_RTT_WINDOW = 8;
/** (ⓑ) 상태 확인 늦음으로 이만큼 연속 붙잡히면 자동 전송을 멈추고 사람 클릭을 기다린다(작업 화면 직접 입력과 겹쳐 두 번 가지 않게). */
export const SLOW_HOLDS_MAX = 3;
/** (ⓑ) 상태 확인이 계속 늦어 자동으로 보내지 않는 말의 까닭 코드 — 「이 말 보내기」 클릭으로만 나간다. */
export const STATUS_SLOW = "status_slow";
export const STATUS_SLOW_NOTE = "마스터 상태 확인이 계속 늦어 자동으로 보내지 않아요 — 급하면 「작업 화면」에서 마스터 창에 직접 입력하거나, 「이 말 보내기」를 눌러 다시 시도하세요.";
/** (TICKET=cysr-chat-held-win) 결속 세션 기록이 없다(none · 1.1.16 윈 = unsupported_platform · ★1.1.17(cysr-1118-ui ①-4) 윈도 읽음 → 이제 none = 세션 미등록·파일 없음·링크 거부 등)고 확인된 좌석의 시작점 재조회 간격 — 3초 조회 고리마다 다시 묻지 않는다. */
export const TRANSCRIPT_NONE_RETRY_MS = 30_000;
/** (1.1.19 · 검증 고침3 N5) 「결속 세션 있음 · 파일 아직 없음」 동안 마지막 보내기 뒤 이 시간 안이면 PENDING_SENT_RETRY_MS 마다 다시 묻는다(첫 입력 = 파일이 곧 생김). */
export const PENDING_SENT_WINDOW_MS = 60_000;
export const PENDING_SENT_RETRY_MS = 10_000;
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
  return m.step === "held" && (m.code === RESTORED || m.code === STALE || m.code === DUP || m.code === STATUS_SLOW);
}
/** 상태 확인 늦음 계열 붙잡힘(재조회 시간 초과 · 쓰기 직전 관측 낡음). */
function slowHeld(m: Msg): boolean {
  return m.step === "held" && (m.code === STATUS_TIMEOUT || m.code === "status_stale");
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
/** (1.1.19 · TICKET=cysr-1119-s3 · CH-C) Tauri watch 사건 이름(viewcore.rs `CHAT_TRANSCRIPT_CHANGED`). */
export const CHAT_TRANSCRIPT_CHANGED = "chat-transcript-changed";
/** (1.1.19 · F06) 세션 기록 읽기 계기 — 읽기는 전부 `readTranscript(reason)` 한 함수(잠금 · offset 단일 소유 · from_offset 대조). */
export type ReadReason = "attach" | "event" | "align" | "after_send" | "poll" | "rebind" | "reset" | "again";
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
  /** (TICKET=cysr-chat-held-win) 대화 화면 문턱·마스터 카드 전용 「답하는 중」(judge/gate chatWorking — 자기 신고 없으면 출력 10초 정적 = 쉼). 없으면 working. */
  chatWorking?(row: Record<string, unknown>): boolean;
  /** (조각 4) daemon-event 구독 — 대화 화면이 켜져 있을 때만(attach~detach). 없으면 사건 없이(멈춤 = org.status·5분 규칙만).
   *  (통합 1116) 조각 3 의 `listen(name, handler)` 와 이름이 겹쳐 `listenDaemon` 으로 — 두 구독 모두 그대로 산다. */
  listenDaemon?(fn: (ev: unknown) => void): () => void;
  /** (조각 4) 다른 화면으로(「작업 화면에서 보기」) — registry.choose. */
  goView?(id: string): void;
  /** (조각 4 · 검증 F1) 본부 데몬 socket_slug(Tauri default_socket_slug) — 사건의 slug 대조용 · 대화 화면이 켜질 때 1회. */
  defaultSlug?(): Promise<string>;
  /** (조각 5) 작업 화면에서 그 좌석 창에 포커스(main.ts jumpToSurface) · 작업 화면 위 안내 띠 · 도움 요청 창(기존 피드백 창). */
  focusSeat?(sid: number): void;
  workHint?(text: string | null): void;
  openHelp?(): void;
  /** (조각 5) Tauri 앱 사건 구독(boot-degraded · restore-progress) — 대화 화면 attach~detach 동안만 · 없으면 그 사건 없이. */
  listenApp?(name: string, handler: (e: { payload: unknown }) => void): Promise<() => void>;
  /** (조각 5 · codex 1R major) 앱 수명 전체의 복원 진행 중 여부(main.ts briefGate) */
  restoring?(): boolean;
  /** (TICKET=cysr-1118u-chat ①) 계정 한도 줄(main.ts 상황판과 같은 판정 statusboard.chatLimitRows · 작업 화면 15초 캐시) — 없으면 줄 없음 · 새 조회 0. */
  limits?(): readonly LimitView[];
  /** (TICKET=cysr-1119-s2 · CH-E · F38) 되돌리기 — 환경 변수 `CYS_CHAT_COMPAT_1118=1` 의 값(앱 시작 때 읽은 것 · 원천 = Tauri `chat_compat_env` · S3 가 `views/index.ts` 에서 배선). 없거나 던지면 꺼짐.
   *  저장 키는 두지 않는다(F38 · 쓰는 주체 0). 켜면 C(watch)·D(과정 요약)를 1.1.18 꼴로 — 그 끄기 지점은 `ChatCore.compat1118` 한 값만 본다. */
  compat1118?(): boolean;
  /** (TICKET=cysr-1119-s12 · CV-PEEK) 워커 창 보기 — main.ts 가 그 좌석 터미널을 보기 칸에 옮겨 붙인다(읽기 전용 · 크기 변경 0). 없으면 카드 누름 0. */
  peek?: PeekPort;
}

/** (TICKET=cysr-1119-s12 · DESIGN §4-3) 보기 칸 입구 — 열기·닫기(한 함수)·작업 화면에서 크게·지금 열린 좌석. */
export interface PeekPort {
  /** ok = 붙임 · nosize = 좌석 크기를 몰라 취소(「작업 화면에서 보기」) · gone = 좌석 없음·만들기 실패 · busy = 다른 열기가 진행 중 */
  open(sid: number, host: HTMLElement, onClosed: (reason: string) => void): Promise<"ok" | "nosize" | "gone" | "busy">;
  close(reason: string): void;
  big(sid: number): void;
  /** 열린 좌석 번호(내부 id) · 없으면 null */
  openSid(): number | null;
}

/** (TICKET=cysr-1118u-chat ①) 대화 화면 머리 한도 줄 하나 — name = null 이면 계정 하나(이름 없이 한 줄). 이메일 0(별명·폴더 라벨). */
export interface LimitView {
  name: string | null;
  pct: number;
  line: string;
  title: string;
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
  /** (TICKET=cysr-1119-s11 · TC3) 입력칸에 끌어 놓은 파일 경로(칩) — 메모리만(저장 0 · 업로드 0) · 보낼 때 글 끝에 펼침 · 받아들인 뒤 빔 */
  files: readonly string[];
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

/** (1.1.19 · 검증 V1) 기록 조회 답이 「결속 세션은 있는데 그 파일이 아직 없음」인가 — 그 세션 id(아니면 null). Rust `refine_open_why` 가 후보 경로가 정말 없을 때만 no_file. 순수. */
export function pendingFileSid(v: unknown): string | null {
  const r = v as { status?: unknown; why?: unknown; session_id?: unknown } | null;
  return r && r.status === "unknown" && r.why === "no_file" && typeof r.session_id === "string" && r.session_id !== "" ? r.session_id : null;
}

export class ChatCore {
  private s: ChatState = { master: undefined, health: "unknown", confirms: null, msgs: [], stray: [], draft: "", files: [], notice: null, pollFailed: false, autos: [], rev: 0 };
  private listeners = new Set<Listener>();
  private seq = 0;
  /** 진행 중인 쓰기(원자 제출 1건) — 겹쳐 쓰지 않는다(클릭 1 → 호출 ≤ 1). */
  private writing = false;
  private polling = false;
  /** (TICKET=cysr-1118u-chat ②) 마지막 온전한 조회 시작 시각 · 마지막 조회(가벼운 것 포함) 시작 시각. */
  private lastFullPollStart: number | null = null;
  private lastAnyPollStart: number | null = null;
  /** (codex 1R major) 마지막 상태 재조회(freshBounded)가 시간 상한을 넘겼는가 — 참이면 1초 재조회를 쉬고 3초 박자로(다음 조회가 제때 끝나면 풀림). */
  private lastFreshTimedOut = false;
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
  /** (TICKET=cysr-chat-held-win · ⓐ) 최근 끝난 조회 왕복(ms) — 관측 기반 상한의 재료. */
  private rtts: number[] = [];
  /** (TICKET=cysr-chat-held-win) 결속 세션 기록이 없다고 확인된 좌석·시각 — 그 좌석은 보내기 길에서 시작점을 다시 묻지 않는다(1.1.16 윈 = 늘 none · 1.1.17 윈 = 맥과 같이 ok 가 보통 · none 은 기록 못 연 좌석만). */
  private transcriptNone: { seat: number; at: number } | null = null;
  /** (1.1.19 · TICKET=cysr-1119-s3 · CH-C) 지금 건 결속 파일 watch(Tauri `chat_transcript_watch` 세대) — 있으면 읽기 = `chat_transcript_tail`(RPC 0). */
  private watching: { seat: number; session: string; gen: number } | null = null;
  /** watch 를 거는 중(응답 대기) · 끊은 횟수(늦게 온 watch 응답이 끊은 뒤에 걸리지 않게) · 못 건 시각(TRANSCRIPT_NONE_RETRY_MS 안에 다시 걸지 않음). */
  private watchStarting = false;
  private watchEpoch = 0;
  private watchFailAt: number | null = null;
  /** (C-4) 마지막 watch 사건(또는 watch 응답)의 파일 길이 — 1초 맞춤 = offset 이 이보다 작고 아직 그 길이까지 읽어 보지 않았으면 읽음. */
  private lastEventSize: number | null = null;
  /** (C-4) 마지막으로 받아들인 tail 응답이 본 파일 길이 — 끝에 쓰는 중인 미완 줄(next_offset < size)이 있어도 맞춤이 매초 헛돌지 않게. */
  private lastReadSize: number | null = null;
  /** (C-3 · reset) 잠금 안에서 처리할 다시 걸기 요청 · (F06) 연달아 어긋난 응답 수. */
  private rebindWanted = false;
  private resetWanted = false;
  private fromMismatch = 0;
  /** (검증 고침2 N1) 「결속 세션 있음 · 기록 파일 아직 없음」으로 0 에서 기다리는 중 — 파일을 한 번 읽어 볼 때까지 1.1.18 처럼 30초 문(보낸 직후만 열림) · watch 시도 0. */
  private pendingFile = false;
  private pendingNextAt = 0;
  /** 보낸 직후 열린 문 — 첫 빗나감 뒤 한 번 더(+7초 읽기)까지만 짧게 닫는다. */
  private pendingShort = false;
  /** (검증 고침3 N5) 파일을 기다리는 동안 마지막으로 보낸 시각 — 그 뒤 60초까지는 3초 조회가 10초마다 · 그 밖은 30초마다 스스로 다시 묻는다. */
  private pendingSendAt: number | null = null;
  /** (검증 V9) tail 이 연달아 던진 수 — 2 면 watch 를 내려놓고 1.1.18 길(경로로 다시 열기)로. */
  private tailErrors = 0;
  /** (검증 V10) 앱 사건 구독 세대 — 대화 화면 내림(detach)에서만 올린다(데몬 사건 구독 세대 listenGen 과 따로 · 화면 전환 도중 남은 구독이 풀리지 않게). */
  private appListenGen = 0;
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

  /** (조각 5) 멈춤·깨우기·다시 켜기 장부. */
  readonly revive: ReviveBook;
  /** (조각 5) 앱 사건(boot-degraded · restore-progress) 구독 해제 — 대화 화면 attach~detach 동안만. */
  private unlistenApp: Array<() => void> = [];
  /** (조각 5 · S1-5) 이 화면이 마스터 좌석에 낸 마지막 원자 제출의 사람 입력 표지(데몬 응답 human_input_stamp). */
  private ownHuman: { seat: number; stamp: string } | null = null;

  /** (cysr-1116-s6 · 조각 6) 왼쪽 메뉴바 장부 — 맡긴 일·팀·부서(대화 화면이 켜져 있을 때만 조회). */
  readonly rail: RailBook;
  /** (TICKET=cysr-1119-s12 · CV-PEEK) 보기 칸 입구 — 없으면 null(카드 누름 처리기 0). */
  get peek(): PeekPort | null {
    return this.d.peek ?? null;
  }

  /** (TICKET=cysr-1119-s2 · CH-E · F38) 되돌리기 값 하나 — `Deps.compat1118` 이 정확히 true 일 때만 켬(없음·던짐·그 밖 값 = 꺼짐 · 저장소는 읽지 않음). */
  get compat1118(): boolean {
    try {
      return this.d.compat1118?.() === true;
    } catch {
      return false;
    }
  }

  /** (TICKET=cysr-1119-s2 · F36) `chat_transcript` IPC 인자 — 호출 셋(initOffset · readTranscript · confirm.scanStep)이 모두 이것을 거친다.
   *  꼴 = 1.1.18 그대로(compat 켬·끔 같음 · Rust `compat` 인자 = 카드 B = 1.1.20). 인자 꼴을 바꿀 일이 생기면 이 한 곳에서 `compat1118` 을 본다. */
  readonly transcriptArgs = (surfaceId: number, afterOffset: number, fromEnd: boolean): Record<string, unknown> => ({ socket: null, surfaceId, afterOffset, fromEnd });

  constructor(private readonly d: Deps) {
    this.loadHold();
    this.confirm = new ConfirmBook({ invoke: d.invoke, now: d.now, store: d.store, onChat: this.onChatScreen, transcriptArgs: this.transcriptArgs }, () => this.set({}));
    this.rail = new RailBook({ invoke: d.invoke, now: d.now, setTimeout: d.setTimeout, clearTimeout: d.clearTimeout, store: d.store, working: d.working }, () => this.set({}));
    this.results = new ResultBook({ invoke: d.invoke, now: d.now, store: d.store, onChat: this.onChatScreen }, () => this.set({}));
    this.revive = new ReviveBook({
      invoke: d.invoke,
      now: d.now,
      setTimeout: d.setTimeout,
      clearTimeout: d.clearTimeout,
      store: d.store,
      working: d.working,
      trackAuto: (id, seat) => this.trackAuto(id, seat),
      holdRemainingMs: () => this.autoHoldRemainingMs(),
      goView: (id) => this.d.goView?.(id),
      focusSeat: (sid) => this.d.focusSeat?.(sid),
      workHint: (t) => this.d.workHint?.(t),
      openHelp: () => this.d.openHelp?.(),
      changed: () => this.set({}),
      pollSoon: () => void this.poll(),
      restoring: () => this.d.restoring?.() === true,
    });
  }

  get state(): ChatState {
    return this.s;
  }

  /** (TICKET=cysr-1118u-chat ①) 지금 계정 한도 줄 — 원천이 없거나 던지면 빈 목록(줄을 그리지 않음). */
  limits(): readonly LimitView[] {
    try {
      return this.d.limits?.() ?? [];
    } catch {
      return [];
    }
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

  /** (TICKET=cysr-1119-s11 · TC3) 끌어 놓은 파일을 칩으로 — 같은 경로는 한 번만 · 바뀐 것이 없으면 알림 0. */
  addFiles(paths: readonly string[]): void {
    const files = addDropped(this.s.files, paths);
    if (files.length !== this.s.files.length) this.set({ files });
  }

  /** (TICKET=cysr-1119-s11 · TC3) 칩 하나 빼기(「<이름> 빼기」 단추). */
  removeFile(path: string): void {
    if (this.s.files.includes(path)) this.set({ files: this.s.files.filter((f) => f !== path) });
  }

  /** 대화 화면이 켜짐 — 세션 기록 읽기 허용 · 시작 오프셋 잡기. */
  attach(): void {
    this.attachAs(false);
  }

  /** (s79 · codex 3R ③) 켜기 한 곳 — ★살핌 표지(watchOnly·paused)를 **먼저** 세우고 구독·조회를 시작한다(옛 순서 = attach 뒤에 세움 → 전환 순간 대화 화면 몫 조회가 나갔다).
   *  살핌(watch) = 작업 화면 띠 자료만: 사건 구독 · 세션 읽기(chat_transcript) · poll(feed_list·org_status) — default_socket_slug·home_dir_path 0(대화 화면에서 이미 받아 둔 값을 씀). */
  private attachAs(watch: boolean): void {
    this.watchOnly = watch;
    if (watch) this.stopWatch(); // (1.1.19 · CH-C) 작업 화면 살핌 = 기록 watch 안 함(대화 화면이 보일 때만 · K10)
    else void this.compat1118; // (CH-E) 값 원천을 일찍 깨운다(index.ts 가 처음 물을 때 Tauri 에 1회 묻는다)
    this.results.paused = watch; // (s79 · V4) 작업 화면 살핌 중엔 list_dir 0
    this.attached = true;
    if (!watch) this.everAttached = true;
    if (!this.unlistenConfirm && this.d.listenDaemon)
      this.unlistenConfirm = this.d.listenDaemon((ev) => {
        this.confirm.onEvent(ev);
        this.results.onEvent(ev); // (s79 조각 7) skill.run_finished
        this.rail.onEvent(ev); // (조각 6) 묶음 사건 surface.group.changed — 「팀 만드는 중 → 진행」
      });
    if (!watch && this.d.defaultSlug)
      void this.d
        .defaultSlug()
        .then((s) => {
          const slug = typeof s === "string" && s ? s : null;
          this.confirm.setHqSlug(slug);
          this.results.setHqSlug(slug); // (s79 조각 7)
          this.rail.setHqSlug(slug);
        })
        .catch(() => {});
    if (!watch) void this.results.start(); // (s79 조각 7) 홈 1회(살핌 중 = 다시 묻지 않음)
    void this.readTranscript("attach");
    if (!watch) void this.ensureWatch(); // (CH-C) 결속을 이미 알면 바로 · 모르면 시작점을 잡은 뒤(initOffset)
    void this.startListening();
    void this.startAppListening();
  }

  /** (조각 5) 앱 사건 — boot-degraded(팀 준비 덜 됨) · restore-progress(복원 중 다시 켜기 잠금). */
  private async startAppListening(): Promise<void> {
    const listen = this.d.listenApp;
    if (!listen || this.unlistenApp.length) return;
    const gen = this.appListenGen;
    for (const name of ["boot-degraded", "restore-progress", CHAT_TRANSCRIPT_CHANGED]) {
      try {
        const un = await listen(name, (e) => (name === CHAT_TRANSCRIPT_CHANGED ? this.onWatchEvent(e.payload) : this.revive.onAppEvent(name, e.payload)));
        if (!this.attached || gen !== this.appListenGen) un();
        else this.unlistenApp.push(un);
      } catch {
        /* 구독 실패 = 그 사건 없이 */
      }
    }
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
    this.d.peek?.close("detach"); // (TICKET=cysr-1119-s12 · C-04) 물러남 = 보기 칸 닫는 자리 하나(살피는 중이어도 대화 화면은 내려간다)
    // (s79 조각 9) registry 는 새 화면을 먼저 띄우고 옛 화면을 내린다 — 대화 → 작업 전환이면 작업 화면이 이미 살피는 중(watchOnly)이다.
    //   그때 대화 화면의 내리기가 구독·세션 읽기를 끄면 작업 화면 띠가 새 물음을 못 본다 → 살피는 중이면 끄지 않는다(끄는 것은 watchStop).
    if (this.watchOnly) return;
    this.attached = false;
    this.stopWatch(); // (1.1.19 · CH-C) 대화 화면이 내려감 = watch 끊음(숨김 → 사건 0)
    this.unlistenConfirm?.();
    this.unlistenConfirm = null;
    for (const h of this.readTimers) this.d.clearTimeout(h);
    this.readTimers.clear();
    this.listenGen++;
    this.appListenGen++;
    for (const un of this.unlistenApp.splice(0)) {
      try {
        un();
      } catch {
        /* 이미 풀림 */
      }
    }
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

  /**
   * (cysr-1116-s2 · integ I3·S4-3) 데몬 사건 단일 입구 — main.ts onDaemonEvent 머리 배선 1줄이 앱의 **하나뿐인** daemon-event 구독에서
   * 사건마다 부른다(종전 = 대화 화면이 켜질 때 조각 3·조각 4 가 같은 사건을 따로 두 번 구독 · default_socket_slug 도 두 번 조회).
   * hqSlug = main.ts 가 이미 받아 둔 본부 데몬 slug(모르면 null — 그때는 두 처리기 모두 종전처럼 버린다 · 새 조회 0).
   * 대화 화면이 꺼져 있는 동안 온 사건(예 master.deadman)도 장부가 받는다 — 상태만 바뀌고 그리기는 켜진 화면이 한다(작업 화면 = 그리기 0).
   */
  ingest(raw: unknown, hqSlug: string | null): void {
    if (typeof hqSlug === "string" && hqSlug.length > 0) {
      if (this.defaultSlug === null) this.defaultSlug = hqSlug;
      this.confirm.setHqSlug(hqSlug);
      this.results.setHqSlug(hqSlug); // (통합 cysr-1116-integ-1120) s79 결과 장부도 같은 본부 slug — 종전 defaultSlug 조회 자리(s2 가 걷음)
      this.rail.setHqSlug(hqSlug); // (통합) s6 메뉴바 장부도 같은 본부 slug
    }
    this.onDaemonEvent(raw);
    this.confirm.onEvent(raw);
    // (통합 cysr-1116-integ-1120) s79 조각 7 skill.run_finished — 종전 listenDaemon 구독(s2 가 걷음)은 붙어 있는 동안(대화 화면 · 작업 화면 살핌)만 살았다 → 그 뜻 그대로.
    if (this.attached) this.results.onEvent(raw);
    // (통합 cysr-1116-integ-1120) s6 조각 6 surface.group.changed — 같은 까닭(s2 가 listenDaemon·defaultSlug 를 걷음)으로 ingest 에서 · 붙어 있을 때만(s6 구독 수명).
    if (this.attached) this.rail.onEvent(raw);
  }

  /** 데몬 사건 하나 — 기본 데몬(마스터가 사는 곳) 사건만 받는다(부서 데몬은 좌석 번호가 겹친다 · 소켓 이름을 모르면 아무것도 받지 않음). */
  onDaemonEvent(raw: unknown): void {
    const e = raw as { name?: unknown; socket_slug?: unknown; surface_id?: unknown } | null;
    if (!e || typeof e.name !== "string") return;
    if (this.defaultSlug === null || e.socket_slug !== this.defaultSlug) return;
    this.revive.onEvent(raw); // (조각 5) deadman·idle·released·claim_denied·takeover — 본부 데몬 것만
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
    const feed = await this.timed(this.d.invoke("feed_list", { status: "pending" })).catch(() => undefined);
    const t0 = this.d.now();
    const org = await this.timed(this.d.invoke("org_status", { socket: null })).catch(() => undefined);
    const stale = this.d.now() - t0 > this.obsLimit();
    return { master: org === undefined || stale ? undefined : masterRowOf(org, this.d.chatWorking ?? this.d.working), approvals: feed === undefined ? null : approvalSeatsOf(feed), obsAt: t0, feed, org };
  }

  /** (TICKET=cysr-chat-held-win · ⓐ) 관측 기반 상한 = clamp(최근 OBS_RTT_WINDOW 회 끝난 왕복의 최대 × OBS_RTT_FACTOR, OBS_MAX_MS, OBS_CAP_MS).
   *  관측이 없으면 바닥(OBS_MAX_MS) — 빠른 기계·멈춘(끝나지 않는) 조회는 예전과 같다. */
  obsLimit(): number {
    return this.limitFor(1);
  }
  /** 순차 조회 n 개 전체의 상한 = clamp(n × 최근 왕복 최대 × OBS_RTT_FACTOR, OBS_MAX_MS, n × OBS_CAP_MS) — 빠른 기계는 n 과 무관하게 바닥 500ms(예전 판정 그대로). */
  private limitFor(n: number): number {
    if (this.rtts.length === 0) return OBS_MAX_MS;
    return Math.min(n * OBS_CAP_MS, Math.max(OBS_MAX_MS, Math.ceil(n * Math.max(...this.rtts) * OBS_RTT_FACTOR)));
  }

  /** 조회 1건의 왕복을 잰다(끝난 것만 · 상한을 넘겨 결과를 버린 조회도 끝난 시각으로 센다 — 그래야 느린 기계에서 상한이 따라 늘어난다). 결과는 그대로 넘긴다. */
  private timed<T>(p: Promise<T>): Promise<T> {
    const t0 = this.d.now();
    p.then(
      () => {
        this.rtts.push(this.d.now() - t0);
        if (this.rtts.length > OBS_RTT_WINDOW) this.rtts.shift();
      },
      () => {},
    );
    return p;
  }

  /** (조각 3 고침 · 검증 지적 F) 재조회 전체에 시간 상한 — 데몬이 살아 있지만 멈춰도 보내기·조회 고리가 멈추지 않게.
   *  상한 = limitFor(2)(순차 조회 2개 · feed_list → org_status) — 빠른 기계 = 예전 500ms 그대로 · org 한 다리의 낡음 검사는 obsLimit().
   *  넘으면 모름(마스터 undefined · 승인 대기 null → 문턱이 붙잡음 · 쓰기 0) + timedOut 표지. 늦게 온 답은 버린다. */
  private async freshBounded(): Promise<{ master: MasterRow | null | undefined; approvals: number[] | null; obsAt: number; timedOut?: boolean; feed?: unknown; org?: unknown }> {
    const r = await this.bounded(this.fetchFresh(), this.limitFor(2));
    this.lastFreshTimedOut = r === TIMED_OUT; // (TICKET=cysr-1118u-chat ② · codex 1R major) 늦은 연결 = 1초 재조회 멈춤(끝나지 않은 조회를 매초 쌓지 않게)
    return r === TIMED_OUT ? { master: undefined, approvals: null, obsAt: this.d.now(), timedOut: true } : r;
  }

  private bounded<T>(p: Promise<T>, ms: number = this.obsLimit()): Promise<T | typeof TIMED_OUT> {
    return new Promise((res) => {
      let done = false;
      const h = this.d.setTimeout(() => {
        if (done) return;
        done = true;
        res(TIMED_OUT);
      }, ms);
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
    const own = f.master && this.ownHuman && this.ownHuman.seat === f.master.surface_id ? this.ownHuman.stamp : null;
    return sendGate({ master: f.master, approvalSeats: f.approvals, ownHumanStamp: own });
  }

  private applyFresh(f: { master: MasterRow | null | undefined; approvals: number[] | null; obsAt: number; feed?: unknown; org?: unknown }): void {
    const m = f.master;
    this.confirm.observe(f.feed, f.org, m);
    this.revive.observe(m, f.org); // (조각 5)
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

  /** (TICKET=cysr-1119-s11 · TC3) 입력칸 보내기 전용 — 칩이 있으면 글 끝에 펼쳐 보냄. 빠른 답 등 「그 글 그대로」 길은 submit(칩 무관 · 칩 그대로). */
  submitInput(raw: string, isWin: boolean): boolean {
    const text = this.admitWithFiles(raw, isWin);
    if (text === null) return false;
    void this.accept(text);
    return true;
  }

  /** submit 과 같되 끝까지 기다린다(시험·내부용). */
  async send(raw: string): Promise<void> {
    const text = this.admit(raw);
    if (text !== null) await this.accept(text);
  }

  /** (TICKET=cysr-1119-s11 · TC3) 칩이 있으면 글 끝에 펼친 뒤 다듬기 · 받아들였으면 칩을 비움(보낸 뒤에는 반드시 빔) · 막혔으면 칩 그대로. 칩 없음 = 종전 admit 그대로. */
  private admitWithFiles(raw: string, isWin: boolean): string | null {
    const text = this.admit(withDroppedFiles(raw, this.s.files, isWin));
    if (text !== null && this.s.files.length) this.s = { ...this.s, files: [] };
    return text;
  }

  /** 다듬기·붙잡음 상한 — 통과면 보낼 글 · 아니면 null(안내 1줄). */
  private admit(raw: string): string | null {
    const out = composeOutbound(raw);
    if (!out.ok) {
      this.set({ notice: out.msg });
      return null;
    }
    if (this.s.msgs.filter((m) => m.step === "held").length >= HOLD_MAX) {
      // (TICKET=cysr-1119-s2 · DESIGN §3-5 고침 ③ · K19) 사실대로 — 붙잡은 말 가운데 눌러야 나가는 말(needsClick)이 있을 수 있고, 거절된 이 말은 나중에 저절로 가지 않는다. 셈·꼴 = 1.1.18.
      this.set({ notice: `붙잡아 둔 말이 ${HOLD_MAX}개 이상이라 이 말은 받지 않았어요 — 위의 말이 보내지면 다시 보낼 수 있어요(『이 말 보내기』가 붙은 말은 눌러야 보내져요). 입력칸 글은 그대로 있어요.` });
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

  /** (TICKET=cysr-chat-held-win · ⓑ) 상태 확인 늦음으로 붙잡는다(바이트 0) — 연속 SLOW_HOLDS_MAX 회째면 자동 전송을 멈추고 사람 클릭 대기(STATUS_SLOW).
   *  두 번 전달 0: 안내를 보고 사람이 작업 화면에서 직접 치면, 이 말이 나중에 자동으로 또 나가면 안 된다 → 클릭으로만. */
  private holdSlow(id: string, code: string, note: string): void {
    const cur = this.s.msgs.find((x) => x.id === id);
    const n = (cur?.slowHolds ?? 0) + 1;
    if (n >= SLOW_HOLDS_MAX) this.patchMsg(id, { step: "held", sentAt: null, code: STATUS_SLOW, note: STATUS_SLOW_NOTE, notBefore: undefined, slowHolds: n });
    else this.patchMsg(id, { step: "held", sentAt: null, code, note, slowHolds: n });
  }

  /** 한 말을 문턱에 걸고, 통과면 원자 제출 1회. */
  private async deliver(id: string): Promise<void> {
    if (this.writing) return;
    this.writing = true;
    try {
      let fresh = await this.freshBounded(); // ★쓰기 직전 재조회 1회(3초 목록을 믿지 않음 · 시간 상한 = 검증 지적 F)
      this.applyFresh(fresh);
      // (TICKET=cysr-chat-held-win) 결속 기록이 없다고 이미 확인된 좌석(1.1.16 윈 = 늘 none · 1.1.17 = 기록 못 연 좌석)은 보내기 길에서 시작점을 다시 묻지 않는다 —
      //   예전엔 윈에서 매 보내기가 시간 상한 창 3개(재조회 → 시작점 → 재조회)를 연달아 통과해야 했고, 하나만 늦어도 붙잡혔다(맥 = 창 1개).
      //   none 이면 묻든 안 묻든 결과가 같다(전달됨 0 · 「오래 걸려요」) — 건너뛸 기록 자체가 없다. 배경 재조회는 poll 이 30초마다.
      const noneSeat = fresh.master && this.transcriptNone?.seat === fresh.master.surface_id;
      if (this.offset === null && fresh.master && !noneSeat) {
        // 보낸 user 레코드를 건너뛰지 않게 세션 기록 시작점을 먼저 잡는다 — 이 RPC 가 문턱 판정과 쓰기 사이에 끼지 않게 다시 조회한다.
        // (codex 2R major) 시작점 조회가 상한을 넘겼거나 겹친 조회에 밀려 결과를 버렸으면(「stale」) 시작점이 정해지지 않은 채 쓰지 않는다 — 붙잡음.
        //   조회는 끝났지만 기록이 없다(「none」 · 윈도·파일 없음)면 예전처럼 보낸다(전달됨 0 · 오래 걸려요).
        const init = await this.initOffset();
        fresh = init === "stale" ? { master: undefined, approvals: null, obsAt: this.d.now(), timedOut: true } : await this.freshBounded();
        this.applyFresh(fresh);
      }
      if (fresh.timedOut) {
        // 아직 안 썼다(바이트 0) → 「확인 중」이 아니라 붙잡음 · 다시 확인되면 poll 이 문턱에 다시 건다.
        this.holdSlow(id, STATUS_TIMEOUT, "마스터 상태 확인이 늦어져서 아직 쓰지 않았어요 — 다시 확인되면 보낼게요.");
        return;
      }
      const g = this.gateOf(fresh);
      if (!g.ok) {
        this.patchMsg(id, { step: "held", code: g.code, note: g.msg, slowHolds: undefined });
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
      if (this.d.now() - fresh.obsAt > this.obsLimit()) {
        this.holdSlow(id, "status_stale", "마스터 입력줄 확인이 오래돼서 쓰지 않았어요 — 다시 확인되면 보낼게요.");
        return;
      }
      if (this.s.msgs.find((x) => x.id === id)?.slowHolds !== undefined) this.patchMsg(id, { slowHolds: undefined }); // 쓰기 직전까지 왔다 = 연속 끊김
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
      const r = (res ?? {}) as { outcome?: unknown; code?: unknown; message?: unknown; result?: { request_id?: unknown; human_input_stamp?: unknown } };
      const step = stepFromOutcome(r.outcome);
      // ★1.1.16(S3-1): 데몬 요청 번호를 그 말에 붙인다(쓰기 직전 거부 사건과 번호로 짝짓기) · 먼저 온 사건이면 지금 적용한다(아래 patch 뒤).
      const rid = typeof r.result?.request_id === "string" && r.result.request_id.length > 0 ? r.result.request_id : undefined;
      if (rid) this.patchMsg(id, { requestId: rid });
      // (조각 5 · S1-5) 데몬이 찍은 사람 입력 차례 — 다음 말의 30초 쉼을 「내 보내기」면 걸지 않는 짝짓기 열쇠
      const hst = r.result?.human_input_stamp;
      if (typeof hst === "string" && hst !== "") this.ownHuman = { seat: m.surface_id, stamp: hst };
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

  /** (TICKET=cysr-chat-held-win) 상태 확인 늦음으로 붙잡힌 가장 오래된 자동 말을 이 조회 결과로 다시 본다(쓰기 0 · 단계 표시만).
   *  ⑴ 이 조회도 늦었다 → 연속 횟수 +1(SLOW_HOLDS_MAX 회째 = 클릭 대기 · ⓑ) ⑵ 제때 왔는데 문턱이 막힘(답하는 중 등) → 안내를 지금 까닭으로 바꾸고 연속을 끊는다
   *  (예전엔 옛 「상태 확인이 늦어져서」가 그대로 남아 진짜 까닭 — 예: 마스터가 답하는 중 — 을 가렸다 · 윈 캡처 11-22 23:59). ⑶ 문턱이 열림 → 그대로(곧 deliver 가 판정). */
  private reviewSlowHeld(fresh: { master: MasterRow | null | undefined; approvals: number[] | null; obsAt: number; timedOut?: boolean }): void {
    const first = this.s.msgs.find(autoHeld);
    if (!first || !slowHeld(first)) return;
    if (fresh.timedOut || fresh.master === undefined) {
      this.holdSlow(first.id, first.code as string, first.note ?? "");
      return;
    }
    const g = this.gateOf(fresh);
    if (!g.ok) this.patchMsg(first.id, { code: g.code, note: g.msg, slowHolds: undefined });
  }

  /** (TICKET=cysr-1118u-chat ②) 1초 문턱 재조회가 필요한가 — 대화 화면 · 쓰는 중 아님 · 자동으로 나갈 붙잡은 말(쉼 끝 · 상태 확인 늦음 계열 아님)이 있을 때만. */
  private fastWanted(now: number): boolean {
    if (this.watchOnly || this.writing || this.lastFreshTimedOut) return false;
    const first = this.s.msgs.find(autoHeld); // pump·poll 과 같은 「가장 오래된 하나」 — 그 말이 쉼 중이면 뒤 말도 못 나간다
    return !!first && !slowHeld(first) && (first.notBefore === undefined || now >= first.notBefore);
  }

  /** (TICKET=cysr-1118u-chat ②) 대화 화면 1초 시계 — POLL_MS 마다 온전한 조회 · 그 사이엔 붙잡은 말이 문턱을 기다릴 때만 가벼운 조회(FAST_POLL_MS 박자). */
  pollTick(): void {
    const now = this.d.now();
    if (this.lastFullPollStart === null || now - this.lastFullPollStart >= POLL_MS - TICK_SLOP_MS) void this.poll();
    else if (!this.polling && this.fastWanted(now) && !(this.lastAnyPollStart !== null && now - this.lastAnyPollStart < FAST_POLL_MS - TICK_SLOP_MS)) void this.heldPoll();
    this.alignRead(); // (1.1.19 · C-4) 붙잡은 말 문턱(위) 다음에 맞춤 — 사건이 빠졌거나 그 읽기가 실패해도 1초 안에
  }

  /** (1.1.19 · TICKET=cysr-1119-s3 · C-4) 1초 맞춤 — watch 중이고 offset 이 마지막 사건 길이보다 작으면 읽는다(로컬 파일 · RPC 0). */
  private alignRead(): void {
    const sz = this.lastEventSize;
    if (this.watching && sz !== null && this.offset !== null && this.offset < sz && (this.lastReadSize === null || this.lastReadSize < sz)) void this.readTranscript("align");
  }

  /** (TICKET=cysr-1118u-chat ②) 가벼운 조회 = 상태 조회 → 단계 갱신 → 문턱 → 통과면 가장 오래된 자동 말 1건(poll 과 같은 규칙 · 쓰기 직전 재조회는 deliver 안에서 그대로).
   *  메뉴바·결과·표식 훑기·세션 기록 읽기 0 · 활동 바뀜 기준값(lastWorking·lastPollAt)도 건드리지 않는다(온전한 조회의 기록 읽기 계기가 그대로). */
  private async heldPoll(): Promise<void> {
    if (this.polling) return;
    this.polling = true;
    this.lastAnyPollStart = this.d.now();
    let heldId: string | null = null;
    try {
      const fresh = await this.freshBounded();
      this.applyFresh(fresh);
      this.reviewSlowHeld(fresh);
      this.markStale();
      const held = this.s.msgs.find(autoHeld);
      if (!this.watchOnly && held && (held.notBefore === undefined || this.d.now() >= held.notBefore) && this.gateOf(fresh).ok) heldId = held.id;
    } finally {
      this.polling = false;
    }
    if (heldId !== null) await this.deliver(heldId);
  }

  /** 대화 화면이 켜져 있을 때 POLL_MS 마다(그 사이 붙잡은 말 문턱 재조회 = pollTick·heldPoll). 붙잡은 말이 있고 문턱이 열렸으면 오래된 것 1건을 보낸다(그 안에서 다시 재조회). */
  async poll(): Promise<void> {
    // (조각 3 · 하네스 seed 49) 쓰는 중에도 조회·단계 갱신은 한다 — 응답이 걸린 보내기(수 초) 동안 다른 말의 「답함」·「오래 걸려요」가 멈추지 않게.
    //   보내기는 deliver 가 쓰는 중이면 바로 돌아간다(겹쳐 쓰기 0 · 클릭 1 → 호출 ≤ 1).
    if (this.polling) return;
    this.polling = true;
    this.lastFullPollStart = this.lastAnyPollStart = this.d.now(); // (TICKET=cysr-1118u-chat ②) pollTick 박자 기준
    let heldId: string | null = null;
    try {
      const fresh = await this.freshBounded(); // (조각 3 고침 · 검증 지적 F) 멈춘 데몬에 조회 고리가 묶이지 않게
      const prevWorking = this.lastWorking;
      this.applyFresh(fresh);
      if (!this.watchOnly && !this.compat1118) this.watchBinding(fresh.master); // (1.1.19 · C-3 · 검증 고침2 N2 = 되돌리기 켬이면 1.1.18 그대로 건너뜀) 결속 재확인은 3초 조회로만(이 조회 값 · 새 조회 0)
      this.reviewSlowHeld(fresh);
      void this.confirm.scanStep(); // (조각 4) 대화 화면을 연 때보다 앞 기록의 표식을 한 토막씩
      if (!this.watchOnly) void this.results.tick(); // (s79 조각 7) 아직 모르는 결과의 실재 확인(틱당 상한) · 작업 화면 살핌 중 = 0(V4 · 조회 3종만)
      // ★통합(cysr-1116-integ-1120): 작업 화면 살핌 중(watchOnly)은 s79 V4(조회 3종만) — rail 의 list_surfaces·list_depts 를 부르지 않는다.
      if (this.attached && !this.watchOnly) void this.rail.refresh(fresh.org, fresh.approvals); // (조각 6) 왼쪽 메뉴바 — 이 조회 값 + 좌석 목록(쓰기 직전 재조회와 별개)
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
      else if (this.watching) void this.readTranscript("poll");
      else if (this.pendingFile && this.d.now() >= this.pendingNextAt) void this.readTranscript("poll"); // (검증 고침3 N5) 파일 아직 없음 — 문이 지났으면 스스로 한 번 묻는다(되돌리기 켬은 pendingFile 0 = 1.1.18 그대로) // (1.1.19 · 검증 V4·V5) 놓친 사건·Tauri 쪽에서 사라진 watch 를 되찾는 안전망 — tail = RPC 0(없어졌으면 not_watching → 1.1.18 길)
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
    if (this.pendingFile) {
      // (검증 고침2 N1) 보낸 말이 첫 입력 = 파일이 곧 생김 → 문을 연다(보낸 뒤 읽기가 파일이 생기는 것을 곧 본다)
      this.pendingNextAt = 0;
      this.pendingShort = true;
      this.pendingSendAt = this.d.now();
    }
    for (const ms of READ_AFTER_MS) {
      const h = this.d.setTimeout(() => {
        this.readTimers.delete(h);
        void this.readTranscript("after_send");
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
    const call = this.timed(this.d.invoke("chat_transcript", this.transcriptArgs(m.surface_id, 0, true))).catch(() => null);
    // (TICKET=cysr-chat-held-win) 「이 좌석엔 결속 기록이 없다」는 시각에 매이지 않는 사실이다 — 상한을 넘겨 늦게 온 답이어도 기억한다(시작점 offset 은 여전히 제때 온 답으로만).
    //   느린 윈에서 첫 조회가 늘 늦으면 none 을 영영 못 배워 보내기마다 시작점 창을 다시 거치던 길.
    void call.then((v) => {
      const st = (v as { status?: unknown } | null)?.status;
      if (typeof st === "string" && st !== "ok" && (this.compat1118 || pendingFileSid(v) === null)) this.transcriptNone = { seat: m.surface_id, at: this.d.now() };
    });
    const r = (await this.bounded(call)) as
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
      this.transcriptNone = null;
      void this.ensureWatch(); // (1.1.19 · CH-C) 시작점을 잡았으니 결속 파일 watch(조건이 안 맞으면 아무것도 안 함 · 보내는 중이면 다음 3초 조회에)
      return "ok";
    }
    const pending = this.compat1118 ? null : pendingFileSid(r); // (검증 고침2 N2) 되돌리기 켬 = 1.1.18 그대로(30초 문 · 이 갈래를 안 탐)
    if (pending !== null) {
      // (1.1.19 · 검증 V1 · A0) 결속 세션은 있는데 그 기록 파일이 아직 없다(SessionStart 가 먼저 등록 · 파일은 첫 입력 때 생김 — cysd handlers.rs 주석).
      //   새 파일의 레코드는 처음부터 전부 새 것이다 → 0 에서 읽는다(「기록 없음 30초 문」으로 가면 그 사이 쓰인 첫 말·답을 파일 끝에서 건너뛰었다).
      this.offset = 0;
      this.sessionId = pending;
      this.confirm.startSession(pending, m.surface_id, 0);
      this.transcriptNone = null;
      this.pendingFile = true;
      this.pendingSendAt = null;
      this.pendingNextAt = this.d.now() + TRANSCRIPT_NONE_RETRY_MS; // 없는 동안 = 1.1.18 「기록 없음」과 같은 박자(보내면 열림 · N1)
      this.pendingShort = false;
      return "ok";
    }
    this.transcriptNone = { seat: m.surface_id, at: this.d.now() }; // (TICKET=cysr-chat-held-win) 보내기 길·조회 고리가 매번 다시 묻지 않게
    return "none";
  }

  // ---------- (1.1.19 · TICKET=cysr-1119-s3 · CH-C) 기록 바뀌면 곧 보이기 — watch 수명 ----------

  /** watch 를 건다 — 대화 화면이 보임 ∧ 되돌리기 끔 ∧ 시작점·세션을 앎 ∧ 3초 조회 결속 id = 그 세션 id 일 때만(P3 v4 §3-7 C-1).
   *  못 걸면 TRANSCRIPT_NONE_RETRY_MS 안에 다시 묻지 않는다(걸 때 데몬 RPC 2 — 3초마다 쌓지 않게). 걸리면 그 사이 늘어난 몫을 맞춤으로 읽는다. */
  private async ensureWatch(): Promise<void> {
    if (!this.attached || this.watchOnly || this.watching || this.watchStarting || this.compat1118) return;
    if (this.pendingFile) return; // (검증 고침2 N1) 파일을 아직 못 읽었다 = 걸어도 no_file — 읽기가 파일을 본 뒤 3초 조회가 건다
    if (this.writing) return; // (검증 V6) 보내는 중 = watch 걸기(데몬 RPC 2)가 보내기의 둘째 재조회 앞에 줄 서지 않게 — 다음 3초 조회가 건다
    const m = this.s.master;
    const sid = this.sessionId;
    if (!m || sid === null || this.offset === null || m.registered_session_id !== sid) return;
    if (this.watchFailAt !== null && this.d.now() - this.watchFailAt < TRANSCRIPT_NONE_RETRY_MS) return;
    const epoch = this.watchEpoch;
    this.watchStarting = true;
    type WatchResp = { status?: unknown; gen?: unknown; size?: unknown } | null;
    let r: WatchResp = null;
    try {
      r = (await this.d.invoke("chat_transcript_watch", { socket: null, surfaceId: m.surface_id, sessionId: sid }).catch(() => null)) as WatchResp;
    } finally {
      this.watchStarting = false;
    }
    const ok = r?.status === "ok" && typeof r.gen === "number";
    if (ok && epoch === this.watchEpoch && this.attached && !this.watchOnly && this.sessionId === sid && this.s.master?.surface_id === m.surface_id) {
      this.watching = { seat: m.surface_id, session: sid, gen: r!.gen as number };
      this.watchFailAt = null;
      this.lastEventSize = typeof r!.size === "number" ? r!.size : null;
      this.alignRead();
      return;
    }
    if (ok) void this.d.invoke("chat_transcript_unwatch", { gen: r!.gen }).catch(() => {}); // 기다리는 사이 끊김·결속 바뀜 = 건 것(그 세대만)을 바로 거둠
    else {
      const why = r?.status === "unknown" ? (r as { why?: unknown }).why : null;
      // superseded = 뒤에 온 unwatch·watch 에 밀림 · no_file = 새 세션 파일이 아직 없음(검증 V1) — 둘 다 실패 아님(다음 3초 조회에 다시)
      if (why !== "superseded" && why !== "no_file") this.watchFailAt = this.d.now();
    }
  }

  /** watch 를 끊는다(대화 화면 내려감 · 작업 화면 살핌 · 결속 바뀜 · reset). 건 것이 있거나 거는 중이었으면 Tauri 에도 알린다. */
  private stopWatch(): void {
    const w = this.watching;
    const had = w !== null || this.watchStarting;
    this.watchEpoch++;
    this.watching = null;
    this.lastEventSize = this.lastReadSize = null;
    this.tailErrors = 0;
    // (검증 V4) 건 세대를 알면 그 세대만 내린다 — 늦게 처리돼도 그 뒤에 건 새 watch 를 내리지 않는다 · 거는 중(세대 모름)이면 무엇이든
    if (had) void this.d.invoke("chat_transcript_unwatch", w ? { gen: w.gen } : {}).catch(() => {});
  }

  /** (C-3) 3초 조회 값으로 결속 재확인 — 좌석·결속 id 가 watch 와 다르면 끊고 잠금 안에서 다시 시작점 → 다시 걸기 · watch 가 없으면 걸어 본다. */
  private watchBinding(m: MasterRow | null | undefined): void {
    if (m === undefined) return; // 모름 = 그대로
    const w = this.watching;
    if (m === null) {
      // (검증 V3) 마스터 행이 한 번 빠짐 = 결속이 바뀐 근거가 아니다 — 끊기만 하고 offset·세션은 쥔다(같은 결속으로 돌아오면 그 자리에서 다시 건다)
      if (w) this.stopWatch();
      return;
    }
    const reg = m.registered_session_id;
    // 결속이 바뀐 근거 = 좌석이 바뀜 ∨ 결속 id(글)가 지금 세션과 다름 · 결속 id 없음(미등록·옛 데몬) = 끊기만(1.1.18 길이 스스로 가린다)
    const changed = w ? m.surface_id !== w.seat || (typeof reg === "string" && reg !== w.session) : typeof reg === "string" && this.sessionId !== null && reg !== this.sessionId;
    if (changed) {
      this.stopWatch();
      void this.readTranscript("rebind");
      return;
    }
    if (w && reg !== w.session) {
      this.stopWatch();
      return;
    }
    if (!w) void this.ensureWatch();
  }

  /** Tauri watch 사건 — 지금 건 세대·좌석 것만. 늘어남 = 읽기 · reset(줄어듦·파일 바뀜) = 잠금 안에서 시작점 다시 → 다시 걸기. */
  private onWatchEvent(raw: unknown): void {
    const p = raw as { surface_id?: unknown; gen?: unknown; size?: unknown; reset?: unknown } | null;
    const w = this.watching;
    if (!w || !p || p.gen !== w.gen || p.surface_id !== w.seat) return;
    if (p.reset === true) {
      this.stopWatch();
      void this.readTranscript("reset");
      return;
    }
    if (typeof p.size === "number") this.lastEventSize = Math.max(this.lastEventSize ?? 0, p.size);
    void this.readTranscript("event");
  }

  /** (1.1.19 · F06) 세션 기록 읽기 **한 길** — 사건·1초 맞춤·보낸 뒤 +1/+3/+7초·3초 조회·attach·rebind·reset 이 모두 여기로 온다.
   *  `reading` 잠금(겹침 0 · 읽는 중 계기 = 끝난 뒤 1회 더) · `this.offset` 단일 소유 · watch 중이면 `chat_transcript_tail`(RPC 0) 아니면 `chat_transcript`.
   *  응답의 시작 오프셋(tail = `from_offset` · 기존 명령 = 보낸 offset)이 지금 offset 과 같을 때만 받아들인다(아니면 버리고 한 번 더 · 두 번 어긋나면 watch 를 끊고 1.1.18 길). */
  async readTranscript(reason: ReadReason = "poll"): Promise<void> {
    if (reason === "reset") this.resetWanted = true;
    if (reason === "rebind") this.rebindWanted = true;
    if (this.reading) {
      this.readAgain = true; // (조각 3 · 하네스 seed 49) 읽는 중에 온 계기(활동 바뀜 등)를 버리지 않는다 — 끝난 뒤 1회 더
      return;
    }
    if (!this.attached) return;
    const m = this.s.master;
    if (!m) return;
    this.reading = true;
    try {
      if (this.rebindWanted || this.resetWanted) {
        // (C-3 · reset) 결속 바뀜 = 세션째 비움 · 파일 바뀜 = 옛 레코드로 근거를 만들지 않음 — 둘 다 끝에서 다시 시작(initOffset 이 다시 건다)
        const rebind = this.rebindWanted;
        this.rebindWanted = this.resetWanted = false;
        this.stopWatch();
        if (rebind) {
          this.sessionId = null;
          this.consumed.clear();
        }
        this.pendingUser = [];
        this.offset = null;
        this.pendingFile = false;
        this.confirm.resetSession();
        await this.initOffset();
        return;
      }
      if (this.offset === null) {
        // (TICKET=cysr-chat-held-win) 기록 없음(none)이 확인된 좌석은 TRANSCRIPT_NONE_RETRY_MS 안에 다시 묻지 않는다 — 윈에서 3초마다·보낸 뒤 +1·+3·+7초마다
        //   같은 연결(직렬 풀)에 조회를 쌓아 보내기 길의 재조회를 늦추던 몫.
        const tn = this.transcriptNone;
        if (tn && tn.seat === m.surface_id && this.d.now() - tn.at < TRANSCRIPT_NONE_RETRY_MS) return;
        await this.initOffset();
        return;
      }
      if (this.pendingFile && this.d.now() < this.pendingNextAt) return; // (검증 고침2 N1) 파일 아직 없음 = 30초 문(보낸 직후만 열림)
      for (let i = 0; i < READ_CHAIN_MAX; i++) {
        const from: number = this.offset;
        const w = this.watching;
        const tail = w !== null && w.seat === m.surface_id;
        const evAtIssue = this.lastEventSize; // (검증 V2) 이 tail 을 보내기 **전에** 본 경로 길이 — 같은 파일이면 tail(그 뒤에 잰 핸들 길이)이 이보다 작을 수 없다
        const r = (await (tail
          ? this.d.invoke("chat_transcript_tail", { surfaceId: m.surface_id, afterOffset: from })
          : this.d.invoke("chat_transcript", this.transcriptArgs(m.surface_id, from, false))
        ).catch(() => null)) as {
          status?: unknown;
          next_offset?: unknown;
          size?: unknown;
          records?: unknown;
          session_id?: unknown;
          reset?: unknown;
          skipped_bytes?: unknown;
          from_offset?: unknown;
          more?: unknown;
        } | null;
        if (this.pendingFile) {
          if (r && r.status === "ok") this.pendingFile = false; // 파일이 생겼다 — 0 에서 읽은 이 응답을 그대로 받아들인다
          else {
            const now = this.d.now();
            // 보낸 직후 첫 빗나감 = +7초 읽기까지만 · 마지막 보내기 뒤 60초 안 = 10초 · 그 밖 = 30초(검증 고침3 N5 — 다시 묻는 박자는 3초 조회가 연다)
            this.pendingNextAt = now + (this.pendingShort ? 6_000 : this.pendingSendAt !== null && now - this.pendingSendAt < PENDING_SENT_WINDOW_MS ? PENDING_SENT_RETRY_MS : TRANSCRIPT_NONE_RETRY_MS);
            this.pendingShort = false;
            return;
          }
        }
        if (!r || r.status !== "ok" || typeof r.next_offset !== "number") {
          if (tail && r && r.status !== "ok" && this.watching === w) {
            // Tauri 쪽 watch 가 없어짐(not_watching 등) — 이 화면 watch 를 내려놓고 1.1.18 길로(다음 계기 · 3초 조회 안전망이 곧 다시 읽고 다시 걸어 본다)
            this.watching = null;
            this.lastEventSize = this.lastReadSize = null;
          } else if (tail && !r && this.watching === w && ++this.tailErrors >= 2) {
            // (검증 V9) 쥔 핸들 읽기가 연달아 던짐 — watch 를 내려놓고(30초 안 다시 안 걸기) 1.1.18 길로 곧바로
            this.stopWatch();
            this.watchFailAt = this.d.now();
            this.readAgain = true;
          }
          return;
        }
        if (tail) this.tailErrors = 0;
        if (typeof r.skipped_bytes === "number" && r.skipped_bytes > 0) this.confirm.markLossy(); // (조각 4 · 검증 F3) 2 MiB 넘는 줄을 건너뜀
        const sid = typeof r.session_id === "string" ? r.session_id : null;
        if (sid !== this.sessionId) {
          // 결속 세션이 바뀜(마스터 다시 켜짐·/clear) — 새 파일 끝에서 다시 시작(옛 오프셋으로 새 파일을 읽지 않는다)
          this.stopWatch();
          this.sessionId = sid;
          this.consumed.clear();
          this.pendingUser = [];
          this.offset = null;
          this.pendingFile = false;
          this.confirm.resetSession();
          await this.initOffset();
          return;
        }
        // (1.1.19 · F10 보강) 쥔 핸들 길이(tail) < 경로 stat 길이(사건) = 둘이 다른 파일(덧붙이기 전용 파일에선 생길 수 없음 · 윈 터널링으로
        //   만든 시각을 물려받은 더 긴 재생성) — 옛 핸들을 계속 읽으면 새 내용이 영영 안 보인다 → reset 과 같이.
        const heldShorter = tail && typeof r.size === "number" && evAtIssue !== null && r.size < evAtIssue;
        if (r.reset === true || heldShorter) {
          // 파일이 줄었다(잘림·교체) — 다시 읽은 옛 레코드로 새 전달·답 근거를 만들지 않는다(codex 1R major). 끝에서 다시 시작.
          this.stopWatch();
          this.offset = null;
          this.pendingUser = [];
          this.confirm.resetSession();
          await this.initOffset();
          return;
        }
        // (1.1.19 · F06) 이 응답이 지금 offset 에서 읽은 것인가 — 아니면 같은 바이트를 두 번 셀 수 있으니 버리고 한 번 더.
        const fromOff = typeof r.from_offset === "number" ? r.from_offset : from;
        if (fromOff !== this.offset) {
          if (++this.fromMismatch >= 2) {
            this.fromMismatch = 0;
            this.stopWatch(); // 두 번 연달아 어긋남 = watch 를 믿지 않는다(1.1.18 길 · 다음 3초 조회가 다시 걸어 봄)
          } else this.readAgain = true;
          return;
        }
        this.fromMismatch = 0;
        if (tail && typeof r.size === "number") this.lastReadSize = r.size;
        const recs = Array.isArray(r.records) ? (r.records as Rec[]) : [];
        this.offset = r.next_offset;
        if (recs.length) this.confirm.onTail(recs);
        if (recs.length) this.results.onTail(recs); // (s79 조각 7) 답 속 경로
        if (recs.length) this.rail.onTail(recs); // (조각 6) 「팀 만드는 중」·「부서로 올리는 중」 표식
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
        if (tail && r.more !== true) return; // (C-4) tail = 읽기 상한에 걸렸을 때만 잇는다(끝의 미완 줄을 세 번 다시 읽지 않음 · 기존 명령 길은 1.1.18 그대로)
      }
    } finally {
      this.reading = false;
      if (this.readAgain) {
        this.readAgain = false;
        void this.readTranscript("again");
      }
    }
  }
}
