// (cysr-1116-s5 · TICKET=cysr-1116-s5-1119) 마스터 멈춤·깨우기·다시 켜기 띠 — 그리기만(판정 = judge/revive · 행동 = act.revive). P2-DESIGN §6 · 시안 c4-waking·c4-wakefail·c5-*.
//
// 화면 맨 위 한 줄(확인 대기 띠 위) · 글은 전부 textContent · 단추는 신뢰 클릭(e.isTrusted)만 · 잠긴 단추 = aria-disabled + 「…중」.
// 확인 대기 띠(조각 4)는 숨기지 않는다 — 마스터가 멈췄을 때 쓰는 「직접 허락」이 그 띠에 있다(FR-C5).

import type { ChatCore } from "../core";
import type { BandBtn, ReviveBand } from "../judge/revive";

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

const LABEL: Record<BandBtn, string> = {
  wake: "마스터 깨우기",
  restart: "마스터 다시 켜기",
  help: "도움 요청 보내기",
  work: "작업 화면에서 보기",
  gate_answer: "작업 화면에서 답하기",
};

export interface ReviveBandHandle {
  el: HTMLElement;
  paint(): void;
}

export function createReviveBand(act: ChatCore): ReviveBandHandle {
  const root = el("section", "cv-revive");
  root.setAttribute("aria-label", "마스터 상태");
  root.setAttribute("aria-live", "polite");
  root.hidden = true;
  let lastSig = "";

  const press = (b: BandBtn) => {
    const r = act.revive;
    if (b === "wake") void r.wake();
    else if (b === "restart") void r.restart();
    else if (b === "help") r.help();
    else if (b === "work") r.toWork();
    else if (b === "gate_answer") r.answerGate();
  };

  const draw = (band: ReviveBand | null) => {
    const sig = band ? JSON.stringify(band) : "";
    if (sig === lastSig) return; // 같은 띠면 다시 그리지 않는다(포커스 보존)
    lastSig = sig;
    root.replaceChildren();
    if (!band) {
      root.hidden = true;
      delete root.dataset.key;
      return;
    }
    root.hidden = false;
    root.dataset.key = band.key;
    root.dataset.tone = band.tone;
    const txt = el("div", "cvr-text");
    txt.append(el("b", "cvr-title", band.title), document.createTextNode(" "), el("span", "cvr-body", band.body));
    const acts = el("div", "cvr-acts");
    band.buttons.forEach((b, i) => {
      const locked = band.locked === b;
      const btn = el("button", i === 0 ? "cvr-btn cvr-pri" : "cvr-btn", locked && band.lockLabel ? band.lockLabel : LABEL[b]);
      btn.type = "button";
      btn.dataset.act = b;
      if (locked) btn.setAttribute("aria-disabled", "true");
      btn.addEventListener("click", (e) => {
        if (!e.isTrusted || locked) return; // 사람의 신뢰 클릭만 · 잠긴 단추는 아무것도 안 함
        press(b);
      });
      acts.append(btn);
    });
    root.append(txt, acts);
  };

  return {
    el: root,
    paint: () => draw(act.revive.view().band),
  };
}
