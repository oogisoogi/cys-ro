// 묶음 탭 머리 줄 그리기 — TICKET=cysr-tabs-sidebar-impl 조각 2b(설계 ③⑤ · master#357e735a).
// 탭 하나 = 묶음 이름 + 좌석별 상태 표지(역할 점과 같은 클래스 · 1f) + 좌석 수. 누르면 그 묶음 좌석이 나란히(넓게 보기 풀림).
// 판정은 하지 않는다 — seatrows 모델의 줄 상태를 그대로 그린다. 새 단추·새 색 없음(묶음 2개 이상일 때만 생긴다).
import { roleDotColor } from "./appearance";
import { SEAT_STATE_ACT, SEAT_STATE_LABEL, type SeatRowsModel } from "./seatrows";
import type { TabInfo } from "./grouptabs";

export function buildTabBar(tabs: readonly TabInfo[], model: SeatRowsModel, active: string | null, onPick: (key: string) => void): HTMLElement {
  const bar = document.createElement("div");
  bar.className = "group-tabbar";
  bar.setAttribute("role", "tablist");
  for (const t of tabs) {
    const g = model.groups.find((x) => x.key === t.key);
    const b = document.createElement("button");
    b.type = "button";
    b.className = `group-tab${t.key === active ? " active" : ""}`;
    b.setAttribute("role", "tab");
    b.setAttribute("aria-selected", String(t.key === active));
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
