// 묶음 탭 머리 줄 그리기 — TICKET=cysr-tabs-sidebar-impl 조각 2b(설계 ③⑤ · master#357e735a).
// 탭 하나 = 묶음 이름 + 좌석별 상태 표지(역할 점과 같은 클래스 · 1f) + 좌석 수. 누르면 그 묶음 좌석이 나란히(넓게 보기 풀림).
// 판정은 하지 않는다 — seatrows 모델의 줄 상태를 그대로 그린다. 새 단추·새 색 없음(묶음 2개 이상일 때만 생긴다).
import { roleDotColor } from "./appearance";
import { SEAT_STATE_ACT, SEAT_STATE_LABEL, type SeatRowsModel } from "./seatrows";
import type { TabInfo } from "./grouptabs";

/** (cysr-1119-s7 SEL-3) 표시용 선택 — `active`(동작용 · 넓게 보기 중 null)와 따로 넘긴다. 넓게 보기 중이면 그 좌석이 든 탭 = `active zoomed`.
 *  생략하면 지금 꼴(active 만). 동작(누름 · 넓게 보기 규칙)은 바뀌지 않는다 — 클래스·aria·「⤢」 표지만. */
export interface TabDisplay {
  key: string | null;
  zoomed: boolean;
}

export function buildTabBar(tabs: readonly TabInfo[], model: SeatRowsModel, active: string | null, onPick: (key: string) => void, display?: TabDisplay): HTMLElement {
  const shown = display ? display.key : active;
  const zoomed = !!display?.zoomed;
  const bar = document.createElement("div");
  bar.className = "group-tabbar";
  bar.setAttribute("role", "tablist");
  for (const t of tabs) {
    const g = model.groups.find((x) => x.key === t.key);
    const b = document.createElement("button");
    b.type = "button";
    const on = t.key === shown;
    b.className = `group-tab${on ? " active" : ""}${on && zoomed ? " zoomed" : ""}`;
    b.setAttribute("role", "tab");
    b.setAttribute("aria-selected", String(on));
    if (on && zoomed) {
      // 넓게 보기 표지 = 글 + 모양(색만으로 뜻을 전하지 않는다) · 접근 이름은 title 로
      const z = document.createElement("span");
      z.className = "group-tab-zoom";
      z.textContent = "⤢";
      z.setAttribute("aria-hidden", "true");
      b.appendChild(z);
      b.title = `${t.label} · 좌석 하나 넓게 보기 중`;
    }
    const name = document.createElement("span");
    name.className = "group-tab-name";
    name.textContent = t.label;
    const dots = document.createElement("span");
    dots.className = "group-tab-dots";
    for (const r of g?.rows ?? []) {
      const d = document.createElement("span");
      d.className = `ws-seat-dot ${SEAT_STATE_ACT[r.state]}`;
      d.style.setProperty("--role-color", roleDotColor(r.role) ?? "#64748b");
      d.title = `${r.no} · ${r.name} · ${SEAT_STATE_LABEL[r.state]}`;
      dots.appendChild(d);
    }
    const n = document.createElement("span");
    n.className = "group-tab-n";
    n.textContent = String(t.sids.length);
    b.append(name, dots, n);
    b.addEventListener("click", () => onPick(t.key));
    bar.appendChild(b);
  }
  return bar;
}
