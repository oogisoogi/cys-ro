// (cysr-1116-s6 · TICKET=cysr-1116-s6-1119) 대화 화면 왼쪽 메뉴바(rail) 판정 — 순수. P2-DESIGN §11 조각 6 · §5-1 · §5-4 · §16-6 · 개정 E1·E2.
//
// 무엇을 하나: 데몬 값(좌석 목록 surface.list · 자기보고 org.status · 승인 대기 feed) + 앱 기록(사람이 옮긴 묶음) + 마스터 답 표식 + 부서 등록부를
//   받아 「맡긴 일」 카드 · 팀 묶음 · 「팀 만드는 중」 · 「부서로 올리는 중」 · 부서 줄을 낸다.
// ★팀 = 본부 안 좌석 묶음(개정 E1) — 묶음 이름·좌석은 **작업 화면 묶음 탭과 같은 모델**(seatrows.buildSeatRows + seatgroup.effectiveGroup)로
//   만든다(같은 입력 → 같은 이름 · bun 대조 시험). 팀 머리는 묶음이 2개 이상일 때만(seatrows.showGroupHeaders = 탭 줄과 같은 판정 · FR-L1).
// ★부서는 팀으로 세지 않는다(개정 E2 · FR-L1 개정) — 부서 등록부(list_depts)는 따로 「부서 N」 줄.
// ★모름은 칠하지 않는다: 자기보고·출력 시각을 못 받으면 「이 일의 소식을 못 받고 있어요」 · 10분 넘게 소식이 없으면 「조용함」(FR-P2 — 일하는 중으로 계속 칠하지 않음).
// ★좌석 번호·CTX 는 보이지 않는다(FR-P1).
// 규칙: 문서·창·저장소·Tauri 전역·현재 시각·타이머 금지(views 정적 핀) — 시각은 인자(nowMs)로만.

import { buildSeatRows, showGroupHeaders, type SeatInput, type SeatRow } from "../../seatrows";
import { cleanGroupName, effectiveGroup, parseSeatGroups, uniqueKeys, type GroupRow } from "../../seatgroup";
import type { Rec } from "./msgstep";

/** 새 소식이 이만큼 없으면 「조용함」(PRD FR-P2 · 10분). */
export const QUIET_SECS = 600;
/** 「만드는 중」·「부서로 올리는 중」 카드를 들고 있는 상한(설계 목표값 · 실측 없음) — 그 안에 묶음·부서가 안 생기면 카드를 내린다(마스터가 그만둔 경우 영원히 남지 않게). */
export const FORMING_MAX_MS = 30 * 60_000;

export const TEAM_FORMING_PREFIX = "⟪팀 만드는 중: ";
export const PROMOTING_PREFIX = "⟪부서로 올리는 중: ";
export const TEAM_PROPOSE_MARK = "⟪팀 제안⟫";
export const DEPT_PROPOSE_PREFIX = "⟪부서 제안: ";
const MARK_END = "⟫";

/** 빠른 답 — 누르면 이 글을 **그대로** 보낸 말로 보낸다(§5-4 · FR-C3 원문 그대로 · 화면은 판정하지 않음 · R4 예외 조건 그대로). */
export const TEAM_REPLY_YES = "네, 팀으로 나눠 주세요";
export const TEAM_REPLY_NO = "아니요, 지금처럼 해 주세요";
export const DEPT_REPLY_YES = "네, 부서로 올려 주세요";
export const DEPT_REPLY_NO = "지금은 아니요";

export type CardStatus = "need" | "run" | "wait" | "quiet" | "unknown";
export const CARD_STATUS: Record<CardStatus, { mark: string; label: string }> = {
  run: { mark: "●", label: "일하는 중" },
  wait: { mark: "◆", label: "기다림" },
  need: { mark: "▲", label: "확인 필요" },
  quiet: { mark: "○", label: "조용함(10분)" },
  unknown: { mark: "○", label: "이 일의 소식을 못 받고 있어요" },
};

export interface TaskCard {
  /** 카드 열쇠(팀 + 제목) */
  key: string;
  title: string;
  status: CardStatus;
  /** 마지막 소식 뒤 초(모르면 null) */
  newsSecs: number | null;
  helpers: number;
}

export interface TeamBlock {
  /** null = 팀 머리 없음(묶음 1개 이하) */
  team: string | null;
  summary: string;
  cards: TaskCard[];
}

export interface FormingCard {
  kind: "team" | "promote";
  name: string;
  line: string;
}

export interface DeptRow {
  name: string;
  title: string;
}

export interface RailModel {
  /** 데몬 값을 한 번도 못 받음 = 불러오는 중 */
  loading: boolean;
  /** 맡긴 일 수(만드는 중 카드 제외) */
  taskCount: number;
  blocks: TeamBlock[];
  forming: FormingCard[];
  depts: DeptRow[];
  /** 부서 등록부를 못 읽음(null = 모름) — 부서 줄을 비우지 않고 직전 값을 쓰는 것은 호출자 몫 */
  deptsKnown: boolean;
}

export interface Marker {
  kind: "team" | "promote";
  name: string;
  /** 표식을 본 시각(ms) */
  at: number;
}

/** 마스터 답 레코드 하나 → 「만드는 중」 표식(줄머리 정확 일치 · 코드 울타리 안 줄 = 0 · user·곁가지 = 0). confirms.markersOf 와 같은 울타리 규칙. */
export function formingMarkersOf(r: Rec): { kind: "team" | "promote"; name: string }[] {
  if (r.role !== "assistant" || r.sidechain || typeof r.text !== "string") return [];
  const out: { kind: "team" | "promote"; name: string }[] = [];
  for (const line of markerLines(r.text)) {
    if (!line.endsWith(MARK_END)) continue;
    const pick = line.startsWith(TEAM_FORMING_PREFIX) ? ("team" as const) : line.startsWith(PROMOTING_PREFIX) ? ("promote" as const) : null;
    if (!pick) continue;
    const raw = line.slice((pick === "team" ? TEAM_FORMING_PREFIX : PROMOTING_PREFIX).length, line.length - MARK_END.length);
    const name = cleanGroupName(raw); // 묶음 이름과 같은 정리(NFKC · 보이지 않는 문자 = 버림) — 데몬 묶음 사건과 같은 열쇠로 대조
    if (name) out.push({ kind: pick, name });
  }
  return out;
}

/** 빠른 답 표식(마스터 답 글) — ⟪팀 제안⟫ = 팀 · ⟪부서 제안: <팀>⟫ = 부서 · 둘 다 없으면 null. 마지막 표식이 이긴다. 울타리 안 줄은 셈하지 않는다. */
export function quickReplyOf(text: string): { kind: "team" } | { kind: "dept"; team: string } | null {
  let out: { kind: "team" } | { kind: "dept"; team: string } | null = null;
  for (const line of markerLines(text)) {
    if (line === TEAM_PROPOSE_MARK) out = { kind: "team" };
    else if (line.startsWith(DEPT_PROPOSE_PREFIX) && line.endsWith(MARK_END)) {
      const team = line.slice(DEPT_PROPOSE_PREFIX.length, line.length - MARK_END.length).trim();
      if (team) out = { kind: "dept", team };
    }
  }
  return out;
}

/** 코드 울타리 밖 줄(뒤 공백 자름). 울타리 = 줄 앞 공백 뒤 ``` 또는 ~~~ 3개 이상 · 닫는 줄 = 같은 글자 · 같거나 더 긴 줄(CommonMark). */
function markerLines(text: string): string[] {
  const out: string[] = [];
  let fence: { ch: string; n: number } | null = null;
  for (const raw of text.replace(/\r\n?/g, "\n").split("\n")) {
    const f = /^\s*(`{3,}|~{3,})/.exec(raw);
    if (f) {
      const ch = f[1][0];
      const n = f[1].length;
      if (fence === null) fence = { ch, n };
      else if (fence.ch === ch && n >= fence.n && raw.trim() === f[1].trim()) fence = null;
      continue;
    }
    if (fence) continue;
    out.push(raw.replace(/\s+$/, ""));
  }
  return out;
}

/** 표식 장부에 더함 — 같은 종류·같은 이름이면 시각만 새로(한 카드). */
export function addMarkers(book: readonly Marker[], found: readonly { kind: "team" | "promote"; name: string }[], at: number): Marker[] {
  let out = [...book];
  for (const f of found) {
    out = out.filter((m) => !(m.kind === f.kind && m.name === f.name));
    out.push({ kind: f.kind, name: f.name, at });
  }
  return out;
}

export interface RailInput {
  /** surface.list 행(본부 데몬) · undefined = 아직 못 받음 */
  surfaces: readonly Record<string, unknown>[] | undefined;
  /** org.status 응답(본부) · undefined = 못 받음 */
  org: unknown;
  /** 승인 대기 좌석 번호(feed) · null = 모름 */
  approvalSeats: readonly number[] | null;
  /** 앱 기록 cys-seat-group 원문(작업 화면이 주인 · 읽기만) */
  seatGroupsRaw: string | null;
  /** list_depts 응답 · undefined = 모름 */
  depts: unknown;
  markers: readonly Marker[];
  nowMs: number;
  /** org.status 행 → 지금 일하는 중인가(appearance.nodeWorking) */
  working(row: Record<string, unknown>): boolean;
}

const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) && v >= 0 ? v : null);

function fixedRole(role: unknown): boolean {
  const r = typeof role === "string" ? role.trim() : "";
  return r === "master" || r.startsWith("master-") || r === "cso" || r.startsWith("cso-");
}

/** 부서 등록부 → 부서 줄(표시명 우선). 꼴이 틀리면 null(모름). */
export function deptRowsOf(v: unknown): DeptRow[] | null {
  const d = (v as { depts?: unknown } | null)?.depts;
  if (!d || typeof d !== "object" || Array.isArray(d)) return null;
  const out: DeptRow[] = [];
  for (const [name, meta] of Object.entries(d as Record<string, unknown>)) {
    const dn = (meta as { display_name?: unknown } | null)?.display_name;
    out.push({ name, title: typeof dn === "string" && dn.trim() ? dn.trim() : name });
  }
  return out.sort((a, b) => a.title.localeCompare(b.title));
}

/** rail 모델 — 같은 입력이면 같은 결과(순수). */
export function railModel(i: RailInput): RailModel {
  const deptRows = i.depts === undefined ? null : deptRowsOf(i.depts);
  const depts = deptRows ?? [];
  const forming = formingCards(i, depts);
  if (i.surfaces === undefined) return { loading: true, taskCount: 0, blocks: [], forming, depts, deptsKnown: deptRows !== null };
  const orgRows = new Map<number, Record<string, unknown>>();
  const rows = (i.org as { surfaces?: unknown } | null)?.surfaces;
  if (Array.isArray(rows)) for (const r of rows) if (r && typeof r === "object" && typeof (r as { surface_id?: unknown }).surface_id === "number") orgRows.set((r as { surface_id: number }).surface_id, r as Record<string, unknown>);
  const seatGroups = parseSeatGroups(i.seatGroupsRaw);
  const live = i.surfaces.filter((s) => s && typeof s.surface_id === "number" && s.exited !== true);
  const uniq = uniqueKeys(null, live as GroupRow[]);
  const inputs: SeatInput[] = [];
  const news = new Map<number, number | null>();
  for (const s of live) {
    if (fixedRole(s.role)) continue; // 마스터·운영 좌석은 맡긴 일 카드가 아니다(마스터 카드는 따로)
    const sid = s.surface_id as number;
    const o = orgRows.get(sid);
    const st = (o?.status ?? null) as { state?: unknown; task?: unknown; age_secs?: unknown } | null;
    const appr = i.approvalSeats !== null && i.approvalSeats.includes(sid);
    const dot = o ? (i.working(o) ? "working" : "waiting") : null;
    inputs.push({
      sid,
      displayNo: typeof s.display_no === "number" ? s.display_no : null,
      role: typeof s.role === "string" ? s.role : null,
      title: typeof s.title === "string" ? s.title : "",
      cwd: typeof s.cwd === "string" ? s.cwd : null,
      exited: false,
      dot,
      approvalPending: appr,
      statusState: typeof st?.state === "string" ? st.state : null,
      task: typeof st?.task === "string" ? st.task : null,
      ctxPct: null,
      ctxSrc: "none",
      group: effectiveGroup(seatGroups, null, s as GroupRow, uniq), // 작업 화면과 같은 규칙: 데몬이 정한 값 > 앱 기록 > 폴더
    });
    const idle = o ? num(o.idle_secs) : null;
    const age = num(st?.age_secs);
    news.set(sid, idle === null ? age : age === null ? idle : Math.min(idle, age));
  }
  const model = buildSeatRows(inputs);
  const heads = showGroupHeaders(model);
  const blocks: TeamBlock[] = [];
  let taskCount = 0;
  for (const g of model.groups) {
    const cards = cardsOf(g.rows, news, orgRows);
    taskCount += cards.length;
    if (heads) blocks.push({ team: g.label, summary: teamSummary(cards), cards });
    else if (blocks.length === 0) blocks.push({ team: null, summary: "", cards });
    else blocks[0].cards.push(...cards);
  }
  // 「팀 만드는 중」은 그 이름 묶음이 생기면 내린다(§5-1 개정 E1 — 묶음 사건 또는 3초 목록의 group 칸)
  const groupNames = new Set(model.groups.map((g) => g.key));
  const still = forming.filter((f) => f.kind !== "team" || !groupNames.has(f.name));
  return { loading: false, taskCount, blocks: blocks.filter((b) => b.cards.length > 0 || b.team !== null), forming: still, depts, deptsKnown: deptRows !== null };
}

function formingCards(i: RailInput, depts: readonly DeptRow[]): FormingCard[] {
  const out: FormingCard[] = [];
  for (const m of i.markers) {
    if (i.nowMs - m.at > FORMING_MAX_MS) continue;
    if (m.kind === "promote") {
      // 부서 등록부에 그 이름(표시명 또는 열쇠)이 생기면 부서 줄로 바뀐다(§16-6)
      if (depts.some((d) => d.title === m.name || d.name === m.name)) continue;
      out.push({ kind: "promote", name: m.name, line: "부서로 올리는 중이에요" });
    } else out.push({ kind: "team", name: m.name, line: "팀 만드는 중이에요" });
  }
  return out;
}

/** 같은 팀 안 같은 일감 이름 좌석 = 카드 하나(도우미 N명). 상태 = 막힘 > 일하는 중 > 기다림 > 조용함 > 모름 순으로 가장 앞선 것. */
function cardsOf(rows: readonly SeatRow[], news: ReadonlyMap<number, number | null>, orgRows: ReadonlyMap<number, Record<string, unknown>>): TaskCard[] {
  const byName = new Map<string, { title: string; sids: number[] }>();
  for (const r of rows) {
    const title = r.name || "이름 없는 일";
    const c = byName.get(title) ?? { title, sids: [] };
    c.sids.push(r.sid);
    byName.set(title, c);
  }
  const rank: CardStatus[] = ["need", "run", "wait", "quiet", "unknown"];
  const out: TaskCard[] = [];
  for (const c of byName.values()) {
    const sts = c.sids.map((sid) => seatCardStatus(rows.find((r) => r.sid === sid)!, news.get(sid) ?? null, orgRows.has(sid)));
    const status = rank.find((k) => sts.includes(k)) ?? "unknown";
    const ages = c.sids.map((sid) => news.get(sid)).filter((x): x is number => typeof x === "number");
    out.push({ key: c.title, title: c.title, status, newsSecs: ages.length ? Math.min(...ages) : null, helpers: c.sids.length });
  }
  return out;
}

/** 좌석 하나의 카드 상태(FR-P2: 10분 넘게 소식 없음 = 조용함 · 일하는 중으로 칠하지 않음). */
export function seatCardStatus(r: Pick<SeatRow, "state" | "tag">, newsSecs: number | null, observed: boolean): CardStatus {
  if (r.state === "blocked") return "need";
  if (!observed || newsSecs === null) return "unknown";
  if (newsSecs > QUIET_SECS) return "quiet";
  if (r.state === "working") return "run";
  return "wait";
}

/** 팀 머리 요약 — 확인 필요 있음 > 일하는 중 수 > 기다림(시안 teamSummary). */
export function teamSummary(cards: readonly TaskCard[]): string {
  const need = cards.filter((c) => c.status === "need").length;
  const run = cards.filter((c) => c.status === "run").length;
  if (need) return `▲ 확인 필요 ${need}`;
  if (run) return `● 일하는 중 ${run}`;
  if (cards.length && cards.every((c) => c.status === "quiet")) return "○ 조용함";
  return "◆ 기다림";
}

/** 마지막 소식 시각을 쉬운 말로. */
export function agoText(secs: number | null): string {
  if (secs === null) return "소식 모름";
  if (secs < 60) return "방금";
  if (secs < 3600) return `${Math.floor(secs / 60)}분 전`;
  return `${Math.floor(secs / 3600)}시간 전`;
}
