// 왼쪽 막대 「좌석 줄」 그리기 (TICKET=cysr-tabs-sidebar-impl 조각 1b · 설계 docs/DESIGN-tabs-sidebar.md §2·§8).
//
// seatrows.ts 의 모델을 DOM 으로 옮긴다 — 판정은 하지 않는다. main.ts 는 부서 카드마다 이 호스트를 붙이고(renderWsTabs)
//   3초 고리 끝에서 모델을 넘길 뿐이다(main.ts = 배선만 · upstream 병합 충돌 줄 수 최소화 · master#c9265847 D).
// ★같은 호스트 노드를 계속 쓴다: renderWsTabs 가 10초마다 목록을 비우고 다시 그려도 호스트 객체는 Map 에 살아 있어
//   다시 붙기만 한다 — 줄이 깜박이거나 툴팁·호버가 끊기지 않는다. 값이 같으면(서명 같음) DOM 을 다시 만들지 않는다.
// ★색은 기존 토큰만(--ok · --warn · --error · 사이드바 회색) · 모양 + 색 둘 다(설계 ⑨) · 글자 = 사이드바 배율(--wsbar-font).
import {
  SEAT_STATE_LABEL,
  SEAT_STATE_SHAPE,
  showGroupHeaders,
  type SeatRow,
  type SeatRowsModel,
} from "./seatrows";
import { sevClassFor } from "./wsusage";

/** 값이 같으면 같은 문자열 — 다시 그릴지 판정(나이·툴팁 문구는 넣지 않는다 · 순수). */
export function seatRowsSignature(m: SeatRowsModel): string {
  const row = (r: SeatRow) =>
    [r.sid, r.no, r.name, r.state, r.tag ?? "", r.ctxPct == null ? "" : Math.round(r.ctxPct), r.ctxSrc, r.named ? 1 : 0].join("\u0001");
  return JSON.stringify([
    m.fixed.map(row),
    m.groups.map((g) => [g.key, g.label, g.rows.map(row)]),
    showGroupHeaders(m),
  ]);
}

/** 줄 하나의 접근 문구(툴팁) — 상태 이름 · CTX 출처까지 글로 남긴다(모양만으로 뜻을 전하지 않는다). */
export function seatRowTitle(r: SeatRow): string {
  const who = r.named ? `${r.no} (화면 밖 보고자)` : `${r.no}번 좌석`;
  const ctx =
    r.ctxPct == null
      ? r.ctxSrc === "stale"
        ? "CTX 판정 불가(낡은 신고 또는 끝난 좌석)"
        : "CTX 아직 관측 없음(0% 라는 뜻이 아니다)"
      : `CTX ${Math.round(r.ctxPct)}%${r.ctxSrc === "self" ? " · 자기보고" : ""}`;
  const tag = r.tag ? ` · ${r.tag}` : "";
  return `${who} · ${r.name || "(이름 없음)"}\n상태: ${SEAT_STATE_LABEL[r.state]}${tag}\n${ctx}`;
}

export interface SeatRowsDomOpts {
  /** 줄을 눌렀을 때(이름 보고자 줄은 부르지 않는다). */
  onPick: (sid: number) => void;
}

const SEAT_HOSTS = new Map<string, HTMLElement>();
const SEAT_SIGS = new WeakMap<HTMLElement, string>();

/** 부서 하나의 호스트(같은 열쇠면 같은 노드). */
export function seatHost(key: string): HTMLElement {
  let h = SEAT_HOSTS.get(key);
  if (!h) {
    h = document.createElement("div");
    h.className = "ws-seats";
    h.dataset.seatHost = key;
    h.hidden = true;
    SEAT_HOSTS.set(key, h);
  }
  return h;
}

/** 사라진 부서의 호스트를 버린다. */
export function pruneSeatHosts(keep: (key: string) => boolean): void {
  for (const k of [...SEAT_HOSTS.keys()]) if (!keep(k)) SEAT_HOSTS.delete(k);
}

/** 모델을 호스트에 그린다 — 서명이 같으면 아무것도 하지 않는다. 좌석이 0 이면 호스트를 숨긴다. */
export function paintSeatRows(host: HTMLElement, m: SeatRowsModel, opts: SeatRowsDomOpts): void {
  const empty = m.fixed.length === 0 && m.groups.every((g) => g.rows.length === 0);
  const sig = empty ? "" : seatRowsSignature(m);
  if (SEAT_SIGS.get(host) === sig && host.hidden === empty) return;
  SEAT_SIGS.set(host, sig);
  host.hidden = empty;
  if (empty) {
    host.replaceChildren();
    return;
  }
  const frag = document.createDocumentFragment();
  for (const r of m.fixed) frag.appendChild(rowEl(r, true, opts));
  const heads = showGroupHeaders(m);
  for (const g of m.groups) {
    if (heads) {
      const gh = document.createElement("div");
      gh.className = "ws-seat-group";
      const name = document.createElement("span");
      name.className = "ws-seat-group-name";
      name.textContent = g.label;
      const n = document.createElement("span");
      n.className = "ws-seat-group-n";
      n.textContent = String(g.rows.length);
      gh.append(name, n);
      gh.title = g.key ? `묶음: ${g.label} (좌석 생성 폴더 이름)` : "폴더를 모르는 좌석";
      frag.appendChild(gh);
    }
    for (const r of g.rows) frag.appendChild(rowEl(r, false, opts));
  }
  host.replaceChildren(frag);
}

function rowEl(r: SeatRow, fixed: boolean, opts: SeatRowsDomOpts): HTMLElement {
  const row = document.createElement("div");
  row.className = `ws-seat st-${r.state}${fixed ? " fixed" : ""}${r.named ? " named" : ""}`;
  row.dataset.sid = String(r.sid);
  const shape = document.createElement("span");
  shape.className = "ws-seat-shape";
  shape.textContent = SEAT_STATE_SHAPE[r.state];
  shape.setAttribute("aria-label", SEAT_STATE_LABEL[r.state]);
  const no = document.createElement("span");
  no.className = "ws-seat-no";
  no.textContent = r.no;
  const name = document.createElement("span");
  name.className = "ws-seat-name";
  name.textContent = r.name;
  row.append(shape, no, name);
  const pct = document.createElement("span");
  const sev = r.ctxPct == null ? "" : sevClassFor(r.ctxPct, 60, 80);
  pct.className = `ws-seat-ctx${sev ? " " + sev : ""}`;
  pct.textContent = r.ctxPct == null ? "—" : `${Math.round(r.ctxPct)}%`;
  if (r.tag) {
    // (1c · master#6ecef1a2 ①) 꼬리표가 붙은 줄은 꼬리표 + CTX 를 둘째 줄(오른쪽)로 내린다 — 첫 줄 이름이 막대 폭을 다 쓴다
    //   (한 줄에 다 넣으면 기본 폭 216px 에서 이름이 1~2자만 남았다 · 막대 폭은 늘리지 않는다).
    row.classList.add("tagged");
    const tag = document.createElement("span");
    tag.className = `ws-seat-tag${r.state === "blocked" ? " blocked" : ""}`;
    tag.textContent = r.tag;
    const sub = document.createElement("span");
    sub.className = "ws-seat-sub";
    sub.append(tag, pct);
    row.appendChild(sub);
  } else row.appendChild(pct);
  row.title = seatRowTitle(r);
  if (!r.named) {
    row.addEventListener("click", (e) => {
      e.stopPropagation(); // 부서 카드 클릭(부서 전환)과 섞이지 않게 — 전환은 onPick 이 함께 한다
      opts.onPick(r.sid);
    });
  }
  return row;
}
