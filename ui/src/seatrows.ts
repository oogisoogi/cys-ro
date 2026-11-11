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
import type { DotView } from "./roleactivity";
import type { CtxSource } from "./ctxpick";

export type SeatState = "working" | "idle" | "blocked" | "unknown" | "exited";
export type SeatTag = "승인 창" | "확인" | null;

export const SEAT_STATE_LABEL: Record<SeatState, string> = {
  working: "작업 중",
  idle: "대기",
  blocked: "막힘",
  unknown: "모름",
  exited: "끝남",
};

/** 모양(색과 함께 쓴다 — 색만으로 구별하지 않는다 · 설계 ⑨). */
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
}

export interface SeatRow {
  sid: number;
  no: string;
  name: string;
  state: SeatState;
  tag: SeatTag;
  ctxPct: number | null;
  ctxSrc: CtxSource;
  role: string | null;
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
  if (i.dot === "waiting") return "idle";
  return "unknown"; // unknown · stale · 관측 없음
}

export function seatTag(i: SeatInput, state: SeatState): SeatTag {
  if (state === "exited") return null;
  if (state === "blocked") return "승인 창";
  if (i.statusState === "waiting" || i.statusState === "done") return "확인";
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

/** formation.ts family() 와 같은 규칙(그 함수는 export 되지 않아 같은 식을 둔다). */
function fixedRank(role: string | null): number {
  const r = (role ?? "").trim();
  if (r === "master" || r.startsWith("master-")) return 0;
  if (r === "cso" || r.startsWith("cso-")) return 1;
  return -1;
}

const sortNo = (i: SeatInput): number => i.displayNo ?? i.sid;

function toRow(i: SeatInput): SeatRow {
  const state = seatState(i);
  return {
    sid: i.sid,
    no: String(i.displayNo ?? i.sid),
    name: seatName(i),
    state,
    tag: seatTag(i, state),
    ctxPct: i.ctxPct,
    ctxSrc: i.ctxSrc,
    role: i.role,
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
