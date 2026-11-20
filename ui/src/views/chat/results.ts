// (cysr-1116-s79 · TICKET=cysr-1116-s79-1119) 결과 받기 칸·카드 — 그리기만(판정 = judge/results · 행동 = act.results). P2-DESIGN §11 조각 7 · PRD S5.
//
// 두 자리: ① 「결과 N」 칸(대화 화면 왼쪽 rail 자리 — rail 틀은 조각 6 이 만든다 · 지금은 대화 위에 끼우고 통합 때 rail 로 옮긴다)
//          ② 대화 안 카드 — 그 경로를 말한 마스터 답 말풍선 바로 뒤(답 속 경로만 · 스킬 결과는 칸에만).
// 카드 = 종류·이름 · 「새 결과」 · 열기 · 폴더 보기 · 고쳐 달라고 하기 / 없는 파일 = 「파일을 찾을 수 없어요」 + 「마스터에게 물어보기」.
// 「고쳐 달라고 하기」 = 입력칸 앞에 그 결과를 가리키는 말을 넣는다(쓰던 글은 지우지 않음 · 보낼 글 = 사람이 보는 그대로 · FR-C3).
// 글은 전부 textContent(경로·이름에 HTML 해석 0) · 열기·폴더 보기 = 신뢰 클릭만(NFR-S5 · OS 실행기에 닿는 행동).

import type { ChatCore } from "../core";
import { KIND_LABEL, kindOf, missingPrefix, resultsLabel, revisePrefix, visibleResults, withPrefix, type Result } from "../judge/results";

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

export interface ResultsUi {
  log: HTMLElement;
  input: HTMLTextAreaElement;
}

export interface ResultsHandle {
  /** 「결과 N」 칸(rail 자리) */
  el: HTMLElement;
  /** 말 목록을 다시 그린 뒤 — 칸 갱신 + 대화 안 카드 끼우기 */
  paint(): void;
}

export function createResults(act: ChatCore, ui: ResultsUi): ResultsHandle {
  const root = el("section", "cv-results");
  root.setAttribute("aria-label", "결과 받기");
  const head = el("h2", "cvr-head");
  head.setAttribute("aria-live", "polite");
  const list = el("ul", "cvr-list");
  const empty = el("div", "cvr-empty", "끝난 일이 생기면 여기 모여요");
  const notice = el("div", "cvr-notice");
  notice.setAttribute("role", "status");
  root.append(head, empty, list, notice);

  const book = act.results;

  const button = (text: string, cls: string, onClick: (e: MouseEvent) => void): HTMLButtonElement => {
    const b = el("button", cls, text);
    b.type = "button";
    b.addEventListener("click", onClick);
    return b;
  };

  const prepare = (prefix: string) => {
    const next = withPrefix(ui.input.value, prefix);
    ui.input.value = next;
    act.setDraft(next);
    ui.input.focus();
    const at = Math.min(prefix.length, next.length);
    ui.input.setSelectionRange(at, at);
  };

  const card = (r: Result, where: "rail" | "log"): HTMLElement => {
    const box = el(where === "rail" ? "li" : "div", where === "rail" ? "cvr-card" : "cvr-card cvr-inlog");
    box.dataset.result = r.id;
    box.dataset.source = r.source;
    const kind = KIND_LABEL[kindOf(r.name, r.isDir)];
    const top = el("div", "cvr-top");
    top.append(el("span", "cvr-kind", kind), el("span", "cvr-name", r.name));
    if (!r.seen) {
      const nb = el("span", "cvr-new", "새 결과");
      top.append(nb);
    }
    box.append(top);
    box.append(el("div", "cvr-path", r.path));
    if (r.exists === false) {
      box.dataset.missing = "1";
      box.append(el("div", "cvr-missing", "파일을 찾을 수 없어요."));
      const row = el("div", "cvr-actions");
      row.append(button("마스터에게 물어보기", "cvr-ask", () => prepare(missingPrefix(r))));
      box.append(row);
      return box;
    }
    if (r.exists === null) box.append(el("div", "cvr-checking", "파일이 있는지 확인하는 중"));
    const row = el("div", "cvr-actions");
    const trusted = (how: "open" | "reveal") => (e: MouseEvent) => {
      if (!e.isTrusted) return; // 사람이 실제로 누른 클릭만(대본 클릭 = OS 실행기 호출 0)
      void book.act(r.id, how);
    };
    const open = button("열기", "cvr-open", trusted("open"));
    const folder = button("폴더 보기", "cvr-reveal", trusted("reveal"));
    if (book.busy) {
      open.setAttribute("aria-disabled", "true");
      folder.setAttribute("aria-disabled", "true");
    }
    row.append(open, folder, button("고쳐 달라고 하기", "cvr-revise", () => prepare(revisePrefix(r))));
    box.append(row);
    return box;
  };

  function paint(): void {
    const items = book.items;
    const vis = visibleResults(items);
    const label = resultsLabel(items);
    head.textContent = label.text;
    root.dataset.count = String(label.count);
    root.dataset.fresh = String(label.fresh);
    empty.hidden = vis.length > 0;
    list.replaceChildren(...vis.map((r) => card(r, "rail")));
    notice.textContent = book.notice ?? "";
    notice.hidden = !book.notice;
    // 대화 안 카드 — 그 경로를 말한 마스터 답 말풍선 뒤(말 목록은 매번 새로 그려지므로 매번 끼운다)
    for (const r of vis) {
      if (r.source !== "reply" || !r.uuid) continue;
      const at = ui.log.querySelector<HTMLElement>(`.cv-master[data-uuid="${CSS.escape(r.uuid)}"]`);
      if (!at) continue;
      const li = el("li", "cvr-logrow");
      li.append(card(r, "log"));
      at.after(li);
    }
  }

  return { el: root, paint };
}
