// 왼쪽 막대 맨 위 「상황판」 — TICKET=cysr-tabs-sidebar-impl 조각 1d(시안 · 1.1.15 포함 여부는 박사님이 캡처를 보고 정한다 · master#8ef1fcd7).
//
// 무엇을 하나: 좌석 줄 모델(seatrows)을 부서마다 받아 상태별 좌석 수(● 작업 중 · ◆ 대기 · ▲ 막힘 · ○ 모름)를 세고,
//   숫자를 누르면 그 상태의 좌석으로 차례로 옮겨 가게 좌석 목록을 준다. ★새 판정 없음 — seatrows.seatState 가 낸 줄 상태를 센다.
// 노브 = localStorage `cys-status-board`(0 끔 · 1 (가) 상태 수만 · 2 (나) + 한도 한 줄) — 기본 (가). 떼어 낼 때는 노브 0 또는 이 커밋 되돌리기.
// ★세지 않는 줄: 이름 보고자(화면 밖 master·cso — 앱 좌석이 아니다) · 끝난 좌석(끝남은 상태 4종 밖).
import { SEAT_STATE_ACT, SEAT_STATE_LABEL, type SeatRowsModel, type SeatState } from "./seatrows";

export const BOARD_KEY = "cys-status-board";
/** (1g · master#17b20312) 위치 = 「화면 설정」 「상황판 위치」(위 기본 · 아래) · 펼침 = 기억. */
export const BOARD_POS_KEY = "cys-status-board-pos";
export const BOARD_OPEN_KEY = "cys-status-board-open";
export const boardPos = (raw: string | null): "top" | "bottom" => (raw === "bottom" ? "bottom" : "top");
export const boardOpen = (raw: string | null): boolean => raw === "1";
/** 한도 한 줄의 막대 값 — limitLine 과 같은 7d 최고값(없으면 null). */
export function limitPct(rows: readonly { label: string; usedPct: number }[]): number | null {
  const d7 = rows.filter((r) => r.label === "7d" && Number.isFinite(r.usedPct));
  return d7.length ? Math.max(...d7.map((r) => r.usedPct)) : null;
}
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

type RateRow = { label: string; usedPct: number; resetsAt: number | null };
const top7d = (rows: readonly RateRow[]): RateRow | null => {
  const d7 = rows.filter((r) => r.label === "7d" && Number.isFinite(r.usedPct));
  return d7.length ? d7.reduce((a, b) => (b.usedPct > a.usedPct ? b : a)) : null;
};
const DAY = ["일", "월", "화", "수", "목", "금", "토"];
/** 초기화 시각 → 「금 06:00」(이 기기 시간대). */
export function resetDayTime(resetsAtSecs: number): string {
  const t = new Date(resetsAtSecs * 1000);
  return `${DAY[t.getDay()]} ${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}`;
}
/** (나) 한도 한 줄 — 계정 7d 창 중 가장 높은 소진율 + 초기화 요일·시각. 7d 가 없으면 null.
 *  (master#fcbc46fb 결정 ③) 기본 폭 216px 에서 글자 중간 잘림 0 = 「퍼센트 먼저 · 초기화 요일·시각 다음」의 짧은 꼴 · 전문은 limitTitle(툴팁)·펼침. */
export function limitLine(rows: readonly RateRow[], _nowSecs: number): string | null {
  const top = top7d(rows);
  if (!top) return null;
  const pct = `${Math.round(top.usedPct)}%`;
  if (top.resetsAt == null || !Number.isFinite(top.resetsAt)) return pct;
  return `${pct} · ${resetDayTime(top.resetsAt)} 초기화`;
}
/** 한도 한 줄의 전문(툴팁) — 7일 한도 · 사용률 · 초기화 요일·시각 · 남은 시간. */
export function limitTitle(rows: readonly RateRow[], nowSecs: number): string | null {
  const top = top7d(rows);
  if (!top) return null;
  const pct = `7일 한도 ${Math.round(top.usedPct)}% 사용`;
  if (top.resetsAt == null || !Number.isFinite(top.resetsAt)) return pct;
  const left = Math.max(0, Math.floor(top.resetsAt - nowSecs));
  const d = Math.floor(left / 86400), h = Math.floor((left % 86400) / 3600), m = Math.floor((left % 3600) / 60);
  return `${pct} · ${resetDayTime(top.resetsAt)} 초기화(${d > 0 ? `${d}일 ${h}시간` : `${h}시간 ${m}분`} 남음)`;
}

export interface BoardPaintOpts {
  variant: Exclude<BoardVariant, "off">;
  limit: string | null;
  /** 한도 한 줄 전문(툴팁 · limitTitle). */
  limitTitle?: string | null;
  /** (1g) 한도 막대 값(%) · 펼침 상태 · 누르면 펼침/접힘. */
  limitPct?: number | null;
  open?: boolean;
  onToggle?: () => void;
  /** (1f) 사람이 손써야 하는 계정 문제(로그아웃 · 계정 불일치)가 있으면 한 낱말 표시 — accountNeedsAction. */
  acctWarn: boolean;
  onGo: (state: BoardState) => void;
  /** 부서 카드 아래 작은 줄(부서별 수) — 제목 없이 숫자만. */
  compact?: boolean;
  /** (1e) 좌석 밖 승인 요청 수(전 부서 feed.pending 합 − 좌석에 걸린 요청 · ◆ 막힘에 이미 든 것은 빼고) — 0 이면 그리지 않는다. */
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
    const dot = document.createElement("span");
    dot.className = `ws-board-dot ${SEAT_STATE_ACT[st]}`; // 역할 점과 같은 모양(1f)
    const num = document.createElement("span");
    num.className = "ws-board-num";
    num.textContent = String(n);
    b.append(dot, num);
    if (!o.compact) {
      // (master#fcbc46fb 결정 ②) 모양은 역할 점 정본 그대로 · 수 옆에 글자를 늘 붙여 정지 화면에서도 무엇의 수인지 읽힌다.
      const lab = document.createElement("span");
      lab.className = "ws-board-label";
      lab.textContent = SEAT_STATE_LABEL[st];
      b.appendChild(lab);
    }
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
    // (master#ec9c8b30 ③) 낱말을 가른다 — 좌석 화면에 뜬 「승인 창」은 ◆ 막힘 수에 이미 들어 있다 · 여기는 좌석에 걸리지 않은 「승인 요청」만.
    ap.textContent = `승인 요청 ${o.approvals}`;
    ap.title = "좌석 화면 밖의 승인 요청 — 누르면 승인 목록(Control Center 승인 Feed). 좌석 화면에 뜬 승인 창은 ◆ 막힘 수에 들어 있습니다.";
    ap.addEventListener("click", (e) => {
      e.stopPropagation();
      o.onApprovals?.();
    });
    frag.appendChild(ap);
  }
  if (o.limit && !o.compact) {
    // (1g) 둘째 줄 = 가장 높은 한도의 막대 + % + 초기화까지 · 누르면 아래 사용량 칸(모델별 7d · 5h · 가장 낡음)을 펼친다.
    const lim = document.createElement("button");
    lim.type = "button";
    lim.className = "ws-board-limit";
    lim.setAttribute("aria-expanded", String(!!o.open));
    lim.title = `${o.limitTitle ? `${o.limitTitle}\n` : ""}${o.open ? "사용량 접기" : "사용량 펼치기(모델별 7d · 5h · 가장 낡음)"}`;
    const caret = document.createElement("span");
    caret.className = "ws-board-caret";
    caret.textContent = o.open ? "▾" : "▸";
    lim.appendChild(caret);
    if (o.limitPct != null) {
      const track = document.createElement("span");
      track.className = "cc-tbar-track";
      const fill = document.createElement("span");
      const p = Math.min(100, Math.max(0, o.limitPct));
      fill.className = `cc-tbar-fill${p >= 80 ? " crit" : p >= 60 ? " warn" : ""}`;
      fill.style.width = `${p}%`;
      track.appendChild(fill);
      lim.appendChild(track);
    }
    const txt = document.createElement("span");
    txt.className = "ws-board-limit-text";
    txt.textContent = o.limit;
    lim.appendChild(txt);
    lim.addEventListener("click", (e) => {
      e.stopPropagation();
      o.onToggle?.();
    });
    frag.appendChild(lim);
  }
  if (o.acctWarn && !o.compact) {
    const w = document.createElement("div");
    w.className = "ws-board-acct";
    w.textContent = "계정 확인 필요";
    w.title = "로그아웃됐거나 기록과 다른 계정으로 도는 좌석이 있습니다 — 좌석 줄에 마우스를 올리거나 마스터에게 물어보세요";
    frag.appendChild(w);
  }
  host.replaceChildren(frag);
  host.hidden = false;
}

/** (1f) 상황판에 계정 경고를 띄울지 — 사람이 손써야 하는 사유(로그아웃 no_login · 계정 불일치 mismatch)만.
 *  카드의 「계정 미확인」(seatacct.parseSeatAccount 의 모든 미확인 사유 — 낡음·구버전·미등록 포함)은 여기서 띄우지 않는다. */
export function accountNeedsAction(states: readonly string[]): boolean {
  return states.some((s) => s === "no_login" || s === "mismatch");
}
