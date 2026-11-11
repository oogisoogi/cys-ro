// 왼쪽 막대 맨 위 「상황판」 — TICKET=cysr-tabs-sidebar-impl 조각 1d(시안 · 1.1.15 포함 여부는 박사님이 캡처를 보고 정한다 · master#8ef1fcd7).
//
// 무엇을 하나: 좌석 줄 모델(seatrows)을 부서마다 받아 상태별 좌석 수(● 작업 중 · ◆ 대기 · ▲ 막힘 · ○ 모름)를 세고,
//   숫자를 누르면 그 상태의 좌석으로 차례로 옮겨 가게 좌석 목록을 준다. ★새 판정 없음 — seatrows.seatState 가 낸 줄 상태를 센다.
// 노브 = localStorage `cys-status-board`(0 끔 · 1 (가) 상태 수만 · 2 (나) + 한도 한 줄) — 기본 (가). 떼어 낼 때는 노브 0 또는 이 커밋 되돌리기.
// ★세지 않는 줄: 이름 보고자(화면 밖 master·cso — 앱 좌석이 아니다) · 끝난 좌석(끝남은 상태 4종 밖).
import { SEAT_STATE_LABEL, SEAT_STATE_SHAPE, type SeatRowsModel, type SeatState } from "./seatrows";

export const BOARD_KEY = "cys-status-board";
export type BoardVariant = "off" | "a" | "b";
export function boardVariant(raw: string | null): BoardVariant {
  return raw === "0" ? "off" : raw === "2" ? "b" : "a";
}

export type BoardState = Exclude<SeatState, "exited">;
export const BOARD_STATES: readonly BoardState[] = ["working", "idle", "blocked", "unknown"];
export interface SeatRef {
  wsId: number;
  sid: number;
}
export type BoardCounts = Record<BoardState, SeatRef[]>;

export function boardCounts(models: readonly { wsId: number; model: SeatRowsModel }[]): BoardCounts {
  const out: BoardCounts = { working: [], idle: [], blocked: [], unknown: [] };
  for (const { wsId, model } of models)
    for (const r of [...model.fixed, ...model.groups.flatMap((g) => g.rows)]) {
      if (r.named || r.state === "exited") continue;
      out[r.state].push({ wsId, sid: r.sid });
    }
  return out;
}

/** 숫자를 누를 때마다 다음 좌석(끝이면 처음). 직전 위치가 목록 밖이면 처음부터. */
export function nextSeat(xs: readonly SeatRef[], prev: number): { seat: SeatRef; index: number } | null {
  if (xs.length === 0) return null;
  const index = prev >= 0 && prev + 1 < xs.length ? prev + 1 : 0;
  return { seat: xs[index], index };
}

/** (나) 한도 한 줄 — 계정 7d 창 중 가장 높은 소진율 + 초기화까지 남은 시간. 7d 가 없으면 null. */
export function limitLine(rows: readonly { label: string; usedPct: number; resetsAt: number | null }[], nowSecs: number): string | null {
  const d7 = rows.filter((r) => r.label === "7d" && Number.isFinite(r.usedPct));
  if (!d7.length) return null;
  const top = d7.reduce((a, b) => (b.usedPct > a.usedPct ? b : a));
  const pct = `7d ${Math.round(top.usedPct)}%`;
  if (top.resetsAt == null || !Number.isFinite(top.resetsAt)) return pct;
  const left = Math.max(0, Math.floor(top.resetsAt - nowSecs));
  const d = Math.floor(left / 86400), h = Math.floor((left % 86400) / 3600), m = Math.floor((left % 3600) / 60);
  return `${pct} · 초기화까지 ${d > 0 ? `${d}일 ${h}시간` : `${h}시간 ${m}분`}`;
}

export interface BoardPaintOpts {
  variant: Exclude<BoardVariant, "off">;
  limit: string | null;
  /** 단일 부서일 때 카드 대신 여기에 다는 계정 줄(카드가 하던 일을 옮김) — 없으면 null. */
  extra: HTMLElement | null;
  onGo: (state: BoardState) => void;
  /** 부서 카드 아래 작은 줄(부서별 수) — 제목 없이 숫자만. */
  compact?: boolean;
  /** (1e) 승인 대기 수(전 부서 feed.pending 합) — 0 이면 그리지 않는다. */
  approvals?: number;
  onApprovals?: () => void;
}

/** 상태 수 칸 그리기 — 0 인 상태는 흐리게(누를 수 없음). */
export function paintBoard(host: HTMLElement, c: BoardCounts, o: BoardPaintOpts): void {
  const frag = document.createDocumentFragment();
  if (!o.compact) {
    const head = document.createElement("div");
    head.className = "ws-board-head";
    head.textContent = "상황판";
    frag.appendChild(head);
  }
  const line = document.createElement("div");
  line.className = "ws-board-counts";
  for (const st of BOARD_STATES) {
    const n = c[st].length;
    const b = document.createElement("button");
    b.type = "button";
    b.className = `ws-board-n st-${st}${n === 0 ? " zero" : ""}`;
    b.textContent = `${SEAT_STATE_SHAPE[st]} ${n}`;
    b.title = n === 0 ? `${SEAT_STATE_LABEL[st]} 0` : `${SEAT_STATE_LABEL[st]} ${n} — 누르면 그 좌석으로(여럿이면 차례로)`;
    b.disabled = n === 0;
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      o.onGo(st);
    });
    line.appendChild(b);
  }
  frag.appendChild(line);
  if (!o.compact && (o.approvals ?? 0) > 0) {
    const ap = document.createElement("button");
    ap.type = "button";
    ap.className = "ws-board-approvals";
    ap.textContent = `승인 대기 ${o.approvals}`;
    ap.title = "누르면 승인 창이 뜬 좌석으로 — 좌석 화면이 아닌 승인 요청이면 승인 목록(Control Center 승인 Feed)으로";
    ap.addEventListener("click", (e) => {
      e.stopPropagation();
      o.onApprovals?.();
    });
    frag.appendChild(ap);
  }
  if (o.variant === "b" && o.limit && !o.compact) {
    const lim = document.createElement("div");
    lim.className = "ws-board-limit";
    lim.textContent = o.limit;
    frag.appendChild(lim);
  }
  if (o.extra) frag.appendChild(o.extra);
  host.replaceChildren(frag);
  host.hidden = false;
}
