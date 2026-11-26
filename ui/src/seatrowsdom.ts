// 왼쪽 막대 「좌석 줄」 그리기 (TICKET=cysr-tabs-sidebar-impl 조각 1b · 설계 docs/DESIGN-tabs-sidebar.md §2·§8).
//
// seatrows.ts 의 모델을 DOM 으로 옮긴다 — 판정은 하지 않는다. main.ts 는 부서 카드마다 이 호스트를 붙이고(renderWsTabs)
//   3초 고리 끝에서 모델을 넘길 뿐이다(main.ts = 배선만 · upstream 병합 충돌 줄 수 최소화 · master#c9265847 D).
// ★같은 호스트 노드를 계속 쓴다: renderWsTabs 가 10초마다 목록을 비우고 다시 그려도 호스트 객체는 Map 에 살아 있어
//   다시 붙기만 한다 — 줄이 깜박이거나 툴팁·호버가 끊기지 않는다. 값이 같으면(서명 같음) DOM 을 다시 만들지 않는다.
// ★색은 기존 토큰만(--ok · --warn · --error · 사이드바 회색) · 모양 + 색 둘 다(설계 ⑨) · 글자 = 사이드바 배율(--wsbar-font).
import { roleDotColor } from "./appearance";
import {
  SEAT_STATE_ACT,
  SEAT_STATE_LABEL,
  seatAgeTip,
  showGroupHeaders,
  type SeatRow,
  type SeatRowsModel,
} from "./seatrows";
import { sevClassFor } from "./wsusage";

/** 값이 같으면 같은 문자열 — 다시 그릴지 판정(툴팁 문구·포커스는 넣지 않는다 · 순수).
 *  (cysr-1119-s7 BA5 · C-20) 경과는 **글(분 단위)** 로만 넣는다 — 초가 흘러도 같은 분이면 다시 그리지 않고, 분이 바뀌면 글이 굳지 않는다. */
export function seatRowsSignature(m: SeatRowsModel): string {
  const row = (r: SeatRow) =>
    [r.sid, r.no, r.name, r.state, r.tag ?? "", r.ctxPct == null ? "" : Math.round(r.ctxPct), r.ctxSrc, r.named ? 1 : 0, r.ageText ?? ""].join("\u0001");
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
  const tip = r.ageText ? seatAgeTip(r.ageSecs ?? null) : ""; // (cysr-1119-s7 BA5) 접근 이름에 「N분째」
  // (1.1.20 F4) 이름 보고자는 이름이 곧 번호 칸 글이라 이름 칸이 비어 있다 — 「(이름 없음)」 대신 who 만.
  const name = r.name ? ` · ${r.name}` : r.named ? "" : " · (이름 없음)";
  return `${who}${name}\n상태: ${SEAT_STATE_LABEL[r.state]}${tag}${tip ? ` · ${tip}` : ""}\n${ctx}`;
}

export interface SeatRowsDomOpts {
  /** 줄을 눌렀을 때(이름 보고자 줄은 부르지 않는다). */
  onPick: (sid: number) => void;
}

const SEAT_HOSTS = new Map<string, HTMLElement>();
const SEAT_SIGS = new WeakMap<HTMLElement, string>();

// ── (cysr-1119-s7 SEL-2) 고른 좌석 줄 표시 — 설계 1119-DESIGN §5 바꿈 2 ──
// 줄 열쇠가 data-sid 뿐이라(부서마다 번호가 겹친다 · C-09) 표시 대상 = **지금 작업공간 호스트 열쇠 + sid** 의 줄 하나.
// 서명에 넣지 않는다(포커스 이동이 3초 고리 다시 그리기를 낳지 않게) — 다시 그린 뒤 paintSeatRows 가 그 자리에서 다시 붙인다.
export interface SeatSelection {
  key: string;
  sid: number;
}
let seatSel: SeatSelection | null = null;

/** 줄 하나가 고른 줄인가(순수) — 호스트 열쇠·sid 둘 다 같고 이름 보고자 줄이 아닐 때만. */
export function seatRowSelected(hostKey: string, sid: number, named: boolean, sel: SeatSelection | null): boolean {
  if (hostKey === "board" || hostKey.startsWith("n")) return false; // 상황판·부서별 수 호스트 = 좌석 줄이 아니다
  return sel !== null && !named && hostKey === sel.key && sid === sel.sid;
}

function applySeatSelection(host: HTMLElement): void {
  const key = host.dataset.seatHost ?? "";
  for (const el of host.querySelectorAll<HTMLElement>(".ws-seat")) {
    const on = seatRowSelected(key, Number(el.dataset.sid), el.classList.contains("named"), seatSel);
    if (el.classList.contains("sel") !== on) el.classList.toggle("sel", on);
    if (on) el.setAttribute("aria-current", "true");
    else if (el.hasAttribute("aria-current")) el.removeAttribute("aria-current");
  }
}

/** 고른 좌석을 바꾼다(null = 표시 없음) — 모든 호스트를 그 자리에서 고친다(다시 그리기 0). */
export function setSeatSelection(key: string | null, sid: number | null): void {
  seatSel = key === null || sid === null ? null : { key, sid };
  for (const h of SEAT_HOSTS.values()) applySeatSelection(h);
}

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
  applySeatSelection(host); // (cysr-1119-s7 SEL-2) 다시 그린 줄에도 고른 표시를 다시 붙인다
}

function rowEl(r: SeatRow, fixed: boolean, opts: SeatRowsDomOpts): HTMLElement {
  const row = document.createElement("div");
  row.className = `ws-seat st-${r.state}${fixed ? " fixed" : ""}${r.named ? " named" : ""}`;
  row.dataset.sid = String(r.sid);
  // (1f) 표지 = 역할 점과 같은 클래스·같은 색(역할색) — 같은 값 = 같은 모양.
  const shape = document.createElement("span");
  shape.className = `ws-seat-dot ${SEAT_STATE_ACT[r.state]}`;
  shape.style.setProperty("--role-color", roleDotColor(r.role) ?? "#64748b");
  shape.setAttribute("aria-label", SEAT_STATE_LABEL[r.state]);
  const no = document.createElement("span");
  no.className = "ws-seat-no";
  no.textContent = r.no;
  const name = document.createElement("span");
  name.className = "ws-seat-name";
  name.textContent = r.name;
  row.append(shape, no, name);
  // (cysr-1119-s7 BA5) 경과 = 작은 글 · 꼬리표 줄은 둘째 줄(꼬리표 옆)로 — 첫 줄 이름 폭을 더 줄이지 않는다.
  let age: HTMLElement | null = null;
  if (r.ageText) {
    age = document.createElement("span");
    age.className = "ws-seat-age";
    age.textContent = r.ageText;
  }
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
    sub.append(tag);
    if (age) sub.appendChild(age);
    sub.appendChild(pct);
    row.appendChild(sub);
  } else if (age) {
    // (1.1.19 · S7 BA5 · TICKET=fix-1119-e2e-red3) 경과 칸도 꼬리표와 같은 규칙(1c · master#6ecef1a2 ①) — 첫 줄에 넣으면 216px 에서 이름이 2자 남짓으로 줄었다
    //   (seatrows_gate 「이름이 잘리면 최소 6글자 폭」 붉음 · axdev 26px). 경과 + CTX 를 둘째 줄(오른쪽)로 · 막대 폭은 늘리지 않는다.
    row.classList.add("tagged");
    const sub = document.createElement("span");
    sub.className = "ws-seat-sub";
    sub.append(age, pct);
    row.appendChild(sub);
  } else {
    row.appendChild(pct);
  }
  row.title = seatRowTitle(r);
  if (!r.named) {
    row.addEventListener("click", (e) => {
      e.stopPropagation(); // 부서 카드 클릭(부서 전환)과 섞이지 않게 — 전환은 onPick 이 함께 한다
      opts.onPick(r.sid);
    });
  }
  return row;
}
