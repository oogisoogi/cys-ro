// (cysr-1116-s79 · TICKET=cysr-1116-s79-1119) 작업 화면 띠 — 그리기만(판정 = judge/workband · 자료 = core). P2-DESIGN §11 조각 9 · PRD FR-C7.
//
// 자리 = 작업 화면(#body-row) 바로 위 한 줄 · 작업 화면이 켜져 있을 때만 붙는다(어댑터가 붙이고 뗀다).
// 자료: 대화 화면을 이번 실행에서 켠 적이 있으면 core 가 계속 살핀다(watchStart · 3초 · 보내기 0) · 켠 적이 없으면 띠 0 · 조회 0(작업 화면 동작 변화 0).
// 「마스터 창에서 답하기」 = 그 좌석으로 포커스(main.ts jumpToSurface 배선) · 쉬운 화면으로 데려가지 않는다.
// 글은 전부 textContent.

import type { ChatCore } from "../core";
import { pickWorkBand } from "../judge/workband";

export interface WorkBandDeps {
  /** 좌석으로 포커스(다른 탭이면 그 탭으로) — 없으면 단추가 안내만 */
  focusSeat?(sid: number): void;
}

export interface WorkBandHandle {
  el: HTMLElement;
  paint(): void;
}

export function createWorkBand(act: ChatCore, deps: WorkBandDeps): WorkBandHandle {
  const root = document.createElement("div");
  root.className = "wv-band";
  root.setAttribute("role", "status");
  root.setAttribute("aria-live", "polite");
  root.hidden = true;
  const text = document.createElement("span");
  text.className = "wvb-text";
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "wvb-act";
  const note = document.createElement("span");
  note.className = "wvb-note";
  root.append(text, btn, note);

  let onClick: (() => void) | null = null;
  btn.addEventListener("click", () => onClick?.());

  function paint(): void {
    const b = pickWorkBand(act.warm ? act.confirm.band() : null, act.state.draft, act.state.master?.surface_id ?? null);
    if (!b) {
      root.hidden = true;
      root.dataset.kind = "";
      onClick = null;
      return;
    }
    root.hidden = false;
    root.dataset.kind = b.kind;
    text.textContent = b.text;
    btn.textContent = b.action;
    note.textContent = "";
    if (b.kind === "draft") {
      onClick = () => act.goView("chat");
      return;
    }
    root.dataset.item = b.item.kind;
    const seat = b.seat;
    onClick = () => {
      if (seat === null || !deps.focusSeat) {
        note.textContent = "마스터 창을 찾지 못했어요 — 좌석 목록에서 마스터를 눌러 주세요.";
        return;
      }
      deps.focusSeat(seat);
    };
  }

  return { el: root, paint };
}
