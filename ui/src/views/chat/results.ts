// (cysr-1116-s79 · TICKET=cysr-1116-s79-1119) 결과 받기 칸·카드 — 그리기만(판정 = judge/results · 행동 = act.results). P2-DESIGN §11 조각 7 · PRD S5.
//
// 두 자리: ① 「결과 N」 칸(대화 화면 왼쪽 rail 자리 · TICKET=cysr-1119-s5 CV-RAIL = rail 로 옮김 · 접힘 한 줄 머리 · 카드 한 줄)
//          ② 대화 안 카드 — 그 경로를 말한 마스터 답 말풍선 바로 뒤(답 속 경로만 · 스킬 결과는 칸에만).
// 카드 = 종류·이름 · 「새 결과」 · 열기 · 폴더 보기 · 고쳐 달라고 하기 / 없는 파일 = 「파일을 찾을 수 없어요」 + 「마스터에게 물어보기」.
// 「고쳐 달라고 하기」 = 입력칸 앞에 그 결과를 가리키는 말을 넣는다(쓰던 글은 지우지 않음 · 보낼 글 = 사람이 보는 그대로 · FR-C3).
// (1.1.19 OB-O4) 카드마다 「치우기」(목록에서만 숨김 · 파일 무변경) · 칸 머리 「모두 치우기」 = 같은 자리에서 「모두 치울까요?」 확인 1회(창 띄우기 0) · 보이는 결과 0 이면 머리 단추 숨김.
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
  /** (TICKET=cysr-1119-s5 · V5) 입력칸 글을 코드로 바꾼 뒤 — 보내기 단추·높이 다시 맞춤 */
  changed?(): void;
}

export interface ResultsHandle {
  /** 「결과 N」 칸(rail 자리) */
  el: HTMLElement;
  /** 말 목록을 다시 그린 뒤 — 칸 갱신 + 대화 안 카드 끼우기 · 돌려줌 = 보이는 결과 수와 머리 글(rail 숨김·좁은 창 단추가 같은 값을 씀) */
  paint(): { count: number; text: string };
  /** (TICKET=cysr-1119-s5 · CV-RAIL ①) 결과 칸 펼침(좁은 창 「결과 N」 단추가 펼쳐 보임) */
  setOpen(v: boolean): void;
}

export function createResults(act: ChatCore, ui: ResultsUi): ResultsHandle {
  const root = el("section", "cv-results");
  root.setAttribute("aria-label", "결과 받기");
  // (TICKET=cysr-1119-s5 · CV-RAIL ①④) rail 안 = 머리 「결과 N」 접힘 한 줄 단추(기본 접힘 · 펼침 = 이 화면 메모리 · 저장 0)
  //   카드 = 이름 + 「새 결과」 + 열기 한 줄 · 이름을 누르면 펼침(경로 · 폴더 보기 · 고쳐 달라고 하기) · 펼친 카드 id = 화면 메모리(3초 다시 그리기에도 복원 · C-18)
  const head = el("button", "cvr-head");
  head.type = "button";
  head.setAttribute("aria-live", "polite");
  const body = el("div", "cvr-body");
  const list = el("ul", "cvr-list");
  const empty = el("div", "cvr-empty", "끝난 일이 생기면 여기 모여요");
  const notice = el("div", "cvr-notice");
  notice.setAttribute("role", "status");
  // (OB-O4) 머리 줄 = 「결과 N」 + 「모두 치우기」 → 누르면 같은 자리에 확인 1회(치우기 · 그만두기)
  // (TICKET=cysr-1119-integ1 · S16×S5 풀이) 머리 줄 = S5 접힘 단추(head) + S16 「모두 치우기」·확인 · 카드 목록 = 펼침 칸(body) 안
  const headRow = el("div", "cvr-headrow");
  const clearAll = el("button", "cvr-clearall", "모두 치우기");
  clearAll.type = "button";
  const ask = el("span", "cvr-confirm");
  ask.setAttribute("role", "group");
  ask.setAttribute("aria-label", "모두 치울까요?");
  const askText = el("span", "cvr-confirm-text", "모두 치울까요? 파일은 지우지 않아요.");
  const yes = el("button", "cvr-confirm-yes", "치우기");
  yes.type = "button";
  const no = el("button", "cvr-confirm-no", "그만두기");
  no.type = "button";
  ask.append(askText, yes, no);
  ask.hidden = true;
  headRow.append(head, clearAll, ask);
  body.append(empty, list);
  root.append(headRow, body, notice);
  let open = false;
  const openCards = new Set<string>();
  const setOpen = (v: boolean) => {
    open = v;
    head.setAttribute("aria-expanded", String(open));
    body.hidden = !open;
  };
  setOpen(false);
  head.addEventListener("click", () => setOpen(!open));

  const book = act.results;
  let asking = false;
  clearAll.addEventListener("click", () => {
    asking = true;
    paint();
    yes.focus();
  });
  yes.addEventListener("click", () => {
    asking = false;
    book.hideAll(); // 장부가 changed → 다시 그림
    paint();
  });
  no.addEventListener("click", () => {
    asking = false;
    paint();
    clearAll.focus();
  });

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
    ui.changed?.();
  };

  /** (OB-O4) 「치우기」 — 목록에서만 숨김(파일 무변경) · 접근성 이름에 그 결과 이름(카드마다 같은 글이라 구별). */
  const hideButton = (r: Result): HTMLButtonElement => {
    const b = button("치우기", "cvr-hide", () => book.hide(r.id));
    b.setAttribute("aria-label", `${r.name} 치우기`);
    return b;
  };

  // (TICKET=cysr-1119-s5 · CV-RAIL ④) rail 카드 한 줄 — 이름(누르면 펼침) · 「새 결과」 · 첫 행동(열기 · 없는 파일 = 마스터에게 물어보기)
  const railCard = (r: Result): HTMLElement => {
    const box = el("li", "cvr-card cvr-res-card");
    box.dataset.result = r.id;
    box.dataset.source = r.source;
    const isOpen = openCards.has(r.id);
    const top = el("div", "cvr-top");
    const more = el("button", "cvr-more");
    more.type = "button";
    more.setAttribute("aria-expanded", String(isOpen));
    more.title = r.path;
    more.append(el("span", "cvr-name", r.name));
    more.addEventListener("click", () => {
      if (openCards.has(r.id)) openCards.delete(r.id);
      else openCards.add(r.id);
      paint();
    });
    top.append(more);
    if (!r.seen) top.append(el("span", "cvr-new", "새 결과"));
    box.append(top);
    const trusted = (how: "open" | "reveal") => (e: MouseEvent) => {
      if (!e.isTrusted) return; // 사람이 실제로 누른 클릭만(대본 클릭 = OS 실행기 호출 0)
      void book.act(r.id, how);
    };
    if (r.exists === false) {
      box.dataset.missing = "1";
      top.append(button("마스터에게 물어보기", "cvr-ask", () => prepare(missingPrefix(r))));
      box.append(el("div", "cvr-missing", "파일을 찾을 수 없어요."));
      if (isOpen) {
        box.append(el("div", "cvr-path", r.path));
        const mrow = el("div", "cvr-actions");
        mrow.append(hideButton(r)); // (integ1 · S16 OB-O4) 펼친 카드 안
        box.append(mrow);
      }
      return box;
    }
    const openBtn = button("열기", "cvr-open", trusted("open"));
    if (book.busy) openBtn.setAttribute("aria-disabled", "true");
    top.append(openBtn);
    if (!isOpen) return box;
    box.append(el("div", "cvr-kind", KIND_LABEL[kindOf(r.name, r.isDir)]), el("div", "cvr-path", r.path));
    if (r.exists === null) box.append(el("div", "cvr-checking", "파일이 있는지 확인하는 중"));
    const row = el("div", "cvr-actions");
    const folder = button("폴더 보기", "cvr-reveal", trusted("reveal"));
    if (book.busy) folder.setAttribute("aria-disabled", "true");
    row.append(folder, button("고쳐 달라고 하기", "cvr-revise", () => prepare(revisePrefix(r))), hideButton(r)); // (integ1 · S16 OB-O4) 펼친 카드 안
    box.append(row);
    return box;
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
      row.append(button("마스터에게 물어보기", "cvr-ask", () => prepare(missingPrefix(r))), hideButton(r));
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
    row.append(open, folder, button("고쳐 달라고 하기", "cvr-revise", () => prepare(revisePrefix(r))), hideButton(r));
    box.append(row);
    return box;
  };

  function paint(): { count: number; text: string } {
    const items = book.items;
    const vis = visibleResults(items);
    const label = resultsLabel(items);
    head.textContent = label.text;
    root.dataset.count = String(label.count);
    root.dataset.fresh = String(label.fresh);
    empty.hidden = vis.length > 0;
    if (vis.length === 0) asking = false;
    clearAll.hidden = vis.length === 0 || asking;
    ask.hidden = vis.length === 0 || !asking;
    for (const id of [...openCards]) if (!vis.some((r) => r.id === id)) openCards.delete(id); // 밀려난 카드의 펼침은 버린다
    list.replaceChildren(...vis.map((r) => railCard(r)));
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
    return { count: label.count, text: label.text };
  }

  return { el: root, paint, setOpen };
}
