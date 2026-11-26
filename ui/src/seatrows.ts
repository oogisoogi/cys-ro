// 왼쪽 막대 「좌석 줄」 — 순수 판정·묶음 (TICKET=cysr-tabs-sidebar-impl 조각 1a · 설계 docs/DESIGN-tabs-sidebar.md §2·§5).
//
// 무엇을 하나: 좌석 하나의 데몬 값(활동 점 판정 · 승인 피드 · 자기보고 · CTX)을 받아 줄 하나(번호 · 일감 이름 · 상태 · 꼬리표 · CTX)로
//   바꾸고, 고정 좌석(master·cso)과 폴더 묶음으로 나눈다. 타이머·IPC·DOM 0 — main.ts 는 입력을 모아 넘기고 그리기만 한다.
//
// ★새 화면 판독기를 만들지 않는다: 상태의 출처는 데몬이 이미 가진 값뿐이다.
//   - 활동 점(DotView) = roleactivity.ts projectActivity 결과(데몬 surface.list `display_activity` · activity.rs wire_at).
//   - 승인 피드 = 그 좌석의 대기 중 approval 피드(governance.rs check_approvals → approval.request · feed.item.resolved 로 해제).
//   - 자기보고 = org.status `status.state`(cys set-status).
// ★모름은 작업 중으로 칠하지 않는다: 관측 없음·낡음·형식 오류는 모두 "unknown".
// ★waiting(입력을 기다림)은 「대기」다 — 막 띄운 빈 좌석도 waiting 이므로 「확인 대기」라 부르면 뜻이 틀린다(master#c9265847 A).
//   「확인」 꼬리표는 좌석이 스스로 waiting/done 을 신고했을 때만 단다.
import type { ActivityRecord, DotView } from "./roleactivity";
import { pickCtx, type CtxSource } from "./ctxpick";
import { agoText } from "./views/judge/rail"; // (cysr-1119-s7 BA5) 대화 화면 카드와 같은 경과 말(함수 공유 · 호출 시점에만 쓰므로 서로 가져오기 안전)
import { LIMIT_LOGIN_BANDS, resetClock, usageLimit } from "./views/judge/revive";

export type SeatState = "working" | "idle" | "blocked" | "unknown" | "exited";
/** (BA1 · 1.1.19) + 「로그인 필요」 · 「한도 · HH:MM」(리셋 모름 = 「한도」) — 멈춘 까닭(대화 화면 띠와 같은 판정). */
export type SeatTag = "승인 창" | "확인" | "로그인 필요" | "한도" | `한도 · ${string}` | null;

export const SEAT_STATE_LABEL: Record<SeatState, string> = {
  working: "작업 중",
  idle: "대기",
  blocked: "막힘",
  unknown: "모름",
  exited: "끝남",
};

/** (1f · master#94f497c9 ②) 모양 정본 = 기존 역할 점(style.css .pane-role-dot act-*) — 좌석 줄·상황판이 같은 클래스를 쓴다.
 *  작업 중 = 깜박이는 원 · 대기 = 채운 원 · 막힘(승인 창) = 마름모(역할 점 「입력 대기」) · 모름 = 빈 원 · 끝남 = 「–」(역할 점은 숨김). */
export const SEAT_STATE_ACT: Record<SeatState, string> = {
  working: "act-working",
  idle: "act-waiting",
  blocked: "act-input",
  unknown: "act-unknown",
  exited: "act-exited",
};
/** 글자 모양(툴팁·접근 문구용 보조 — 화면 표지는 SEAT_STATE_ACT). */
export const SEAT_STATE_SHAPE: Record<SeatState, string> = {
  working: "●",
  idle: "◆",
  blocked: "▲",
  unknown: "○",
  exited: "–",
};

export interface SeatInput {
  sid: number;
  /** 데몬 display_no(좌석 머리의 번호). 없으면 sid 로 적는다. */
  displayNo: number | null;
  role: string | null;
  /** 데몬 제목(예: "931 · Opus · site"). */
  title: string;
  /** 좌석 **생성** 폴더(live_cwd 아님 — 일하다 cd 해도 묶음이 흔들리지 않게). */
  cwd: string | null;
  exited: boolean;
  /** projectActivity(...).view — 관측을 못 받았으면 null. */
  dot: DotView | null;
  /** 이 좌석에 대기 중인 승인 피드가 있다. */
  approvalPending: boolean;
  /** 자기보고 status.state(org.status) — 없으면 null. */
  statusState: string | null;
  /** 자기보고 status.task — 없으면 null. */
  task: string | null;
  ctxPct: number | null;
  ctxSrc: CtxSource;
  /** 사람이 옮긴 묶음(있으면 폴더보다 먼저) — 조각 2 에서 채운다. */
  group?: string | null;
  /** 번호 대신 적을 이름(surface 없는 이름 보고자 master·cso — wsusage namedCtxRows). */
  label?: string | null;
  /** (cysr-1119-s7 BA5) 이 상태가 된 지(초) — stateAgeSecs · 모르면 null. */
  ageSecs?: number | null;
  /** (BA1) 멈춘 까닭 — 한도(좌석 행 usage · judge usageLimit) · 로그인(그 좌석 로그인 룰 사건 300초 안 · main.ts 가 넘김). */
  stall?: { limit: string | null; login: boolean };
}

export interface SeatRow {
  sid: number;
  /** 이름 보고자 줄(화면에 창이 없다 — 누를 수 없다). */
  named: boolean;
  no: string;
  name: string;
  state: SeatState;
  tag: SeatTag;
  ctxPct: number | null;
  ctxSrc: CtxSource;
  role: string | null;
  /** 좌석 생성 폴더 — 넓게 보기 좌석을 재부팅 너머로 알아보는 열쇠의 둘째 재료(grouptabs.seatKey). */
  cwd?: string | null;
  /** (cysr-1119-s7 BA5) 경과 글(seatAgeText · 작업 중·이름 보고자 = "") — 분 단위로만 바뀐다(서명에 들어간다). */
  ageText?: string;
  /** 경과 초(툴팁 「N분째」용). */
  ageSecs?: number | null;
}

export interface SeatGroup {
  /** 묶음 열쇠(폴더 이름 또는 명시 묶음) — "" = 폴더 없음. */
  key: string;
  label: string;
  rows: SeatRow[];
}

export interface SeatRowsModel {
  /** 탭과 무관한 고정 좌석(master 계열 위 · cso 계열 아래). */
  fixed: SeatRow[];
  groups: SeatGroup[];
}

const NAME_MAX = 40;
export const NO_FOLDER_LABEL = "폴더 없음";

/** 좌석 상태 판정 — 끝남 > 막힘(승인 피드 또는 입력 대기 화면) > 활동 점. */
export function seatState(i: SeatInput): SeatState {
  if (i.exited) return "exited";
  if (i.approvalPending || i.dot === "input") return "blocked";
  if (i.dot === "working") return "working";
  if (i.dot === "waiting" || i.dot === "done") return "idle"; // ★(1.1.16 · 차용 ②) done = 끝났지만 안 봄 → 대기 + 「확인」 꼬리표
  return "unknown"; // unknown · stale · 관측 없음
}

export function seatTag(i: SeatInput, state: SeatState): SeatTag {
  if (state === "blocked") return "승인 창";
  if (state !== "exited" && i.stall?.login) return "로그인 필요"; // (BA1) 로그인 > 한도
  if (state !== "exited" && i.stall?.limit) return i.stall.limit as SeatTag;
  // 「확인」 = 좌석이 스스로 waiting/done 을 신고했고 화면이 일하는 중이 아닐 때만(일하는 중이면 낡은 신고다).
  if ((state === "idle" || state === "unknown") && (i.statusState === "waiting" || i.statusState === "done")) return "확인";
  // ★(1.1.16 · 차용 ②) 프로그램이 스스로 「끝남」을 알렸고 사람이 아직 안 봤다(OSC 7501 done · 사람이 입력하면 데몬이 대기로 내린다).
  if (state === "idle" && i.dot === "done") return "확인";
  return null;
}

/** 폴더 경로의 마지막 이름 — 맥 `/` · 윈 `\` 둘 다 자른다(설계 §6). */
export function folderKey(cwd: string | null | undefined): string {
  if (!cwd) return "";
  const parts = cwd.split(/[\\/]+/).filter((p) => p.length > 0);
  const last = parts[parts.length - 1] ?? "";
  return /^[A-Za-z]:$/.test(last) ? "" : last; // 드라이브 뿌리(C:\)는 이름이 아니다
}

/** 일감 이름 — 자기보고 task 첫 줄 우선 · 없으면 데몬 제목의 마지막 조각(「번호 · 모델 · 특성」 → 특성). */
export function seatName(i: SeatInput): string {
  const firstLine = (i.task ?? "").split("\n")[0].trim();
  const raw = firstLine || lastTitleSegment(i.title);
  return raw.length > NAME_MAX ? raw.slice(0, NAME_MAX - 1) + "…" : raw;
}

function lastTitleSegment(title: string): string {
  const segs = (title ?? "").split(" · ").map((s) => s.trim()).filter((s) => s.length > 0);
  return segs[segs.length - 1] ?? "";
}

/** formation.ts family() 와 같은 규칙(그 함수는 export 되지 않아 같은 식을 둔다).
 *  (cysr-1116-s6 · 검증 i7 · master#c4bc0244) + `ceo`·`ceo-*` = 마스터 계열 고정 좌석(데몬 alert_route CLEAR_SIGNAL_ROLES 가 master 와 같이 다룸) —
 *  팀(묶음)이 아니다 · 데몬 team.rs is_fixed_role 과 같은 규칙(화면 팀 이름 = 데몬 팀 판정). formation.ts family() 는 배치 규칙이라 그대로. */
function fixedRank(role: string | null): number {
  const r = (role ?? "").trim();
  if (r === "master" || r.startsWith("master-") || r === "ceo" || r.startsWith("ceo-")) return 0;
  if (r === "cso" || r.startsWith("cso-")) return 1;
  return -1;
}

const sortNo = (i: SeatInput): number => i.displayNo ?? i.sid;

// ── (cysr-1119-s7 BA5 · W5) 경과 시간 — 설계 1119-DESIGN §7 BA5 · §6 W5 · 카드 정본 BORROW A5 ──
/** 되돌리기 = 숨김 상수(false → 좌석 줄 경과 칸 0 · 서명도 지금 꼴). */
export const SEAT_AGE_SHOW = true;

/** 좌석 줄 경과 글 = 대화 화면 agoText 그대로(두 화면 같은 말) · 작업 중 = 빈칸(늘 바뀌어 잡음 · BORROW A5). */
export function seatAgeText(state: SeatState, ageSecs: number | null): string {
  if (!SEAT_AGE_SHOW || state === "working") return "";
  return agoText(ageSecs);
}

/** 접근 이름 「N분째」(agoText 의 「전」 → 「째」 · 「방금」은 그대로 · 모르면 빈칸). */
export function seatAgeTip(ageSecs: number | null): string {
  if (ageSecs === null) return "";
  return agoText(ageSecs).replace(/ 전$/, "째");
}

/** 막힌 창 알약 문구 — 「승인 기다림 · N분」(반올림 = agoText) · 나이 모르면 「승인 기다림」만(지어내지 않는다). */
export function blockedPillText(ageSecs: number | null): string {
  return ageSecs === null ? "승인 기다림" : `승인 기다림 · ${agoText(ageSecs).replace(/ 전$/, "")}`;
}

const VIEW_OF_STATE: Record<string, DotView> = { working: "working", waiting: "waiting", waiting_for_input: "input", done: "done" };

/** 표시 상태가 된 지(초) — 데몬 `display_activity.stable_age_secs`(activity.rs wire_at · 프로그램 보고면 그 나이로 덮임)
 *  + 그 응답을 낳은 요청 시작 뒤 흐른 시간(roleactivity 보수적 나이와 같은 앵커).
 *  표시가 모름·지연이면 마지막 관측 나이 · 표시 상태가 화면 관측과 다른 출처(승인 피드·자기보고)에서 왔으면 null(그 나이를 모른다). */
export function stateAgeSecs(rec: ActivityRecord | undefined, nowMs: number, view: DotView): number | null {
  if (!rec || rec.parsed.kind !== "observation") return null;
  const p = rec.parsed;
  const wire = view === "unknown" || view === "stale" ? p.observedAgeSecs : VIEW_OF_STATE[p.state] === view ? p.stableAgeSecs : null;
  return wire === null ? null : wire + Math.max(0, nowMs - rec.startMs) / 1000;
}

function toRow(i: SeatInput): SeatRow {
  const state = seatState(i);
  const ageSecs = i.ageSecs ?? null;
  const no = i.label || String(i.displayNo ?? i.sid);
  const name = seatName(i);
  return {
    sid: i.sid,
    named: !!i.label,
    no,
    // (1.1.20 · cysr-1120-uifix F4 · 박사님 11-25 「마스터, cso가 각각 2개씩 연이어 있는 이유가 무엇인가?」)
    //   이름 보고자 줄(master·cso — namedSeatInputs)은 번호 칸(label)과 이름 칸(title 마지막 조각)에 같은 이름이 들어가
    //   「master master」 로 두 번 그려졌다. 이름이 번호 칸 글과 같으면 이름 칸을 비운다 — 한 줄에 같은 말 한 번.
    name: name === no ? "" : name,
    state,
    tag: seatTag(i, state),
    ctxPct: i.ctxPct,
    ctxSrc: i.ctxSrc,
    role: i.role,
    cwd: i.cwd,
    ageText: i.label ? "" : seatAgeText(state, ageSecs),
    ageSecs,
  };
}

/** 좌석들 → 고정 좌석 + 묶음. 묶음 순서 = 머리 번호 순으로 훑을 때 처음 나타난 순 · 줄 순서 = 머리 번호 순. */
export function buildSeatRows(inputs: readonly SeatInput[]): SeatRowsModel {
  const sorted = [...inputs].sort((a, b) => sortNo(a) - sortNo(b) || a.sid - b.sid);
  const fixed = sorted
    .filter((i) => fixedRank(i.role) >= 0)
    .sort((a, b) => fixedRank(a.role) - fixedRank(b.role) || sortNo(a) - sortNo(b))
    .map(toRow);
  const groups: SeatGroup[] = [];
  const byKey = new Map<string, SeatGroup>();
  for (const i of sorted) {
    if (fixedRank(i.role) >= 0) continue;
    const explicit = (i.group ?? "").trim();
    const key = explicit || folderKey(i.cwd);
    let g = byKey.get(key);
    if (!g) {
      g = { key, label: key || NO_FOLDER_LABEL, rows: [] };
      byKey.set(key, g);
      groups.push(g);
    }
    g.rows.push(toRow(i));
  }
  return { fixed, groups };
}

/** 묶음 머리를 그릴지 — 묶음이 2개 이상일 때만(묶음 1개 = 지금 1.1.14 화면과 같게 · 설계 §8). */
export function showGroupHeaders(m: SeatRowsModel): boolean {
  return m.groups.length > 1;
}

/** feed_list_all(status=pending) 응답 → 승인 창이 떠 있는 좌석 열쇠 집합(`${socket}#${sid}` · 본부 socket = undefined).
 *  열쇠 모양은 main.ts nodeSig 와 같다. 형식이 어긋난 항목은 건너뛴다(IPC 값은 전부 의심한다). */
export function approvalSeatKeys(all: unknown): Set<string> {
  const out = new Set<string>();
  const socks = (all as { sockets?: unknown } | null)?.sockets;
  if (!Array.isArray(socks)) return out;
  for (const x of socks) {
    if (!x || typeof x !== "object") continue;
    const o = x as { socket?: unknown; dept?: unknown; items?: unknown };
    if (!Array.isArray(o.items)) continue;
    const sock = o.dept === null ? undefined : typeof o.socket === "string" ? o.socket : null;
    if (sock === null) continue;
    for (const it of o.items) {
      const f = it as { kind?: unknown; status?: unknown; surface_id?: unknown } | null;
      if (!f || f.kind !== "approval" || f.status !== "pending") continue;
      if (typeof f.surface_id !== "number" || !Number.isSafeInteger(f.surface_id)) continue;
      out.add(`${sock}#${f.surface_id}`);
    }
  }
  return out;
}

/** feed_list_all 응답 중 **지금 좌석 줄에 있는 좌석**에 걸린 대기 승인 요청 수(항목 단위) — 상황판 「승인 요청」은 전체에서 이것을 뺀다
 *  (그 좌석은 이미 ◆ 막힘으로 세어진다 · master#ec9c8b30 ③ 겹쳐 세기 제거). 열쇠 모양 = approvalSeatKeys. */
export function seatApprovalItems(all: unknown, shown: ReadonlySet<string>): number {
  let n = 0;
  const socks = (all as { sockets?: unknown } | null)?.sockets;
  if (!Array.isArray(socks)) return 0;
  for (const x of socks) {
    if (!x || typeof x !== "object") continue;
    const o = x as { socket?: unknown; dept?: unknown; items?: unknown };
    if (!Array.isArray(o.items)) continue;
    const sock = o.dept === null ? undefined : typeof o.socket === "string" ? o.socket : null;
    if (sock === null) continue;
    for (const it of o.items) {
      const f = it as { kind?: unknown; status?: unknown; surface_id?: unknown } | null;
      if (!f || f.kind !== "approval" || f.status !== "pending") continue;
      if (typeof f.surface_id !== "number" || !Number.isSafeInteger(f.surface_id)) continue;
      if (shown.has(`${sock}#${f.surface_id}`)) n++;
    }
  }
  return n;
}

/** surface.list 원행 하나(+ 이미 판정한 활동 점 · 자기보고 · 승인 여부) → SeatInput. 원행이 없으면(아직 목록 전) 모름으로 둔다.
 *  CTX 는 ctxpick.pickCtx(측정값 우선 · 끝남/사망 = 판정 불가 · 결측 = null). */
export function seatInputOf(
  sid: number,
  s: any,
  dot: DotView | null,
  self: { state: string | null; task: string | null } | undefined,
  approvalPending: boolean,
  loginRecent = false,
): SeatInput {
  const ctx = pickCtx({ exited: s?.exited, agent_alive: s?.agent_alive, usage: s?.usage });
  // (BA1) 한도 = 이 행 usage 의 데몬 시각(rate_observed_at + rate_age_secs)으로 판정 — 화면 시계·새 조회 0
  const u = s?.usage;
  const dnow = typeof u?.rate_observed_at === "number" && typeof u?.rate_age_secs === "number" ? (u.rate_observed_at + u.rate_age_secs) * 1000 : NaN;
  const lim = LIMIT_LOGIN_BANDS && Number.isFinite(dnow) ? usageLimit(u, dnow) : null;
  const limit = lim?.state === "limited" ? (lim.resetsAt === null ? "한도" : `한도 · ${resetClock(lim.resetsAt, dnow)}`) : null;
  return {
    sid,
    displayNo: typeof s?.display_no === "number" ? s.display_no : null,
    role: typeof s?.role === "string" ? s.role : null,
    title: typeof s?.title === "string" ? s.title : "",
    cwd: typeof s?.cwd === "string" ? s.cwd : null,
    exited: s?.exited === true,
    dot: s ? dot : null,
    approvalPending,
    statusState: self?.state ?? null,
    task: self?.task ?? null,
    ctxPct: ctx.pct,
    ctxSrc: ctx.src,
    ...(limit || (LIMIT_LOGIN_BANDS && loginRecent) ? { stall: { limit, login: LIMIT_LOGIN_BANDS && loginRecent } } : {}),
  };
}

/** 이름 보고자(surface 없는 master·cso — wsusage namedCtxRows 의 행) → 고정 줄 입력. 활동은 모른다(모름). */
export function namedSeatInputs(rows: readonly { name: string; ctxPct: number | null }[]): SeatInput[] {
  return rows.map((c, k) => ({
    sid: -1 - k,
    displayNo: null,
    role: c.name,
    title: c.name,
    cwd: null,
    exited: false,
    dot: null,
    approvalPending: false,
    statusState: null,
    task: null,
    ctxPct: c.ctxPct,
    ctxSrc: c.ctxPct == null ? "none" : "measured",
    label: c.name,
  }));
}

/** 화면 표시 활동 점 — **역할 점(paintRoleDot)과 좌석 줄이 함께 쓰는 단 하나의 판정**(master#6ecef1a2 ④).
 *  데몬 관측이 있으면 그대로. 관측이 「모름」일 때만 자기보고 판정(appearance.ts nodeWorking = 신선한 자기보고, 없으면 최근 60초 출력)이
 *  작업 중이면 작업 중 — 사용자가 이미 보던 역할 점 동작 그대로다. 「모름」은 신호가 아무것도 없을 때만 남는다. */
export function seatDot(view: DotView, selfWorking: boolean, approvalPending = false): DotView {
  if (approvalPending) return "input"; // 그 좌석에 승인 창이 떠 있다(데몬 승인 피드 — agy·grok 처럼 화면 문법이 없는 좌석도 잡힌다)
  return view === "unknown" && selfWorking ? "working" : view;
}
