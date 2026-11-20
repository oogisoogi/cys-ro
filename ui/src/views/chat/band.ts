// (cysr-ui-slice4 · TICKET=cysr-ui-slice4-1118) 확인 대기 띠 — 그리기만(판정 = judge/confirms · 행동 = act.confirm). P2-DESIGN §11 조각 4.
//
// 한 번에 하나(「다음」으로 넘김) · 머리 「확인이 필요해요 N」 / 모르면 「확인할 것 살펴보는 중」 / 0건 확정이면 숨김.
// 마스터 물음 = 「대화에서 답하기」(그 물음 자리로 + 입력칸 준비 · **입력칸 글은 건드리지 않음** — 보낸 말은 원문 그대로 · FR-C3).
// 도우미 허락 = 평소 「마스터가 확인하는 중」 · 마스터 멈춤일 때만 「무엇을 보기」 → 허락·거절(펼치기 전 허락 흐림 · 신뢰 클릭만 · 판 묶음).
// 글은 전부 textContent(명령 원문·마스터 글에 HTML 해석 0).

import type { ChatCore } from "../core";
import { ALLOW_AT_WORK_MSG, allowReady, bandLabel, boundOf, canAllowDirect, swapBlocked, SWAP_LINE, SWAP_NOTE, type BandItem, type StallWhy } from "../judge/confirms";

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

const STALL_TEXT: Record<StallWhy, string> = {
  deadman: "마스터가 멈췄어요",
  master_off: "마스터가 꺼져 있어요",
  no_master: "마스터가 없어요",
  stalled_event: "5분 넘게 아무도 답하지 않았어요",
  quiet: "마스터 소식이 5분 넘게 없어요",
};

export interface BandUi {
  log: HTMLElement;
  input: HTMLTextAreaElement;
}

export interface BandHandle {
  el: HTMLElement;
  /** 띠 아래 「답하는 물음」 줄(입력칸 위에 끼움) */
  hint: HTMLElement;
  paint(): void;
  /** 대화 화면 머리 [data-min=confirms] 글 */
  summary(): { text: string; count: string };
}

export function createBand(act: ChatCore, ui: BandUi): BandHandle {
  const root = el("section", "cv-band");
  root.setAttribute("aria-label", "확인 대기");
  root.dataset.band = "";
  const head = el("div", "cvb-head");
  head.setAttribute("aria-live", "polite");
  const body = el("div", "cvb-body");
  const nav = el("div", "cvb-nav");
  const notice = el("div", "cvb-notice");
  notice.setAttribute("role", "status");
  root.append(head, body, nav, notice);

  const hint = el("div", "cv-answering");
  hint.hidden = true;

  /** 지금 보이는 항목 열쇠(없어지면 첫 항목) · 펼친 판 열쇠 · 화면 쪽 안내 · 답하는 물음 */
  let curKey: string | null = null;
  const expanded = new Set<string>();
  let localNote: string | null = null;
  let answering: { id: string; text: string; uuid: string | null; msgs: number } | null = null;
  const defaultPlaceholder = ui.input.placeholder;
  /** (s79 · S4-7 · 검증 F10) 보던 항목이 사라져 저절로 온 항목(열쇠·온 시각) — 온 지 잠깐은 거절·내림을 받지 않는다 */
  let arrived: { key: string; at: number } | null = null;
  const swapped = (key: string): boolean => {
    if (!swapBlocked(arrived, key, Date.now())) return false;
    localNote = SWAP_NOTE;
    paint();
    return true;
  };

  const setAnswering = (a: typeof answering) => {
    answering = a;
    hint.replaceChildren();
    if (!a) {
      hint.hidden = true;
      ui.input.placeholder = defaultPlaceholder;
      return;
    }
    hint.hidden = false;
    const x = el("button", "cva-cancel", "✕");
    x.type = "button";
    x.setAttribute("aria-label", "답하는 물음 지우기");
    x.addEventListener("click", () => setAnswering(null));
    hint.append(el("span", "cva-label", "답하는 물음: "), el("span", "cva-text", a.text), x);
    ui.input.placeholder = "이 물음에 대한 답을 적어 주세요 — 적은 말은 그대로 마스터에게 가요";
  };

  const goTo = (q: { id: string; text: string; uuid: string | null }) => {
    // 그 물음이 있는 대화 자리로(마스터 답 말풍선 · 없으면 맨 아래) + 입력칸 준비. 입력칸 글은 건드리지 않는다.
    const at = q.uuid ? ui.log.querySelector<HTMLElement>(`.cv-master[data-uuid="${CSS.escape(q.uuid)}"]`) : null;
    for (const h of ui.log.querySelectorAll(".cv-asked")) h.classList.remove("cv-asked");
    if (at) {
      at.classList.add("cv-asked");
      at.scrollIntoView({ block: "center" });
    } else ui.log.scrollTop = ui.log.scrollHeight;
    setAnswering({ id: q.id, text: q.text, uuid: q.uuid, msgs: act.state.msgs.length });
    ui.input.focus();
  };

  const button = (text: string, cls: string, onClick: (e: MouseEvent) => void): HTMLButtonElement => {
    const b = el("button", cls, text);
    b.type = "button";
    b.addEventListener("click", onClick);
    return b;
  };

  const itemNode = (it: BandItem): HTMLElement => {
    const box = el("div", "cvb-item");
    box.dataset.kind = it.kind;
    if (arrived?.key === it.key && swapBlocked(arrived, it.key, Date.now())) {
      box.dataset.swapped = "1";
      box.append(el("div", "cvb-swapped", SWAP_LINE));
    }
    if (it.kind === "ask") {
      box.append(el("div", "cvb-text", `마스터가 물어요: ${it.q.text}`));
      const waking = act.state.health !== "ready" && act.state.health !== "busy";
      box.append(button(waking ? "대화에서 답하기 · 깨어나면 전달" : "대화에서 답하기", "cvb-answer", () => goTo(it.q)));
      // (s79 · S4-7 · 검증 F7) 마스터가 해결 표식을 안 내도 사람이 띠에서 내릴 길 — 마스터에게 보내는 것 0
      box.append(
        button("이 물음은 끝났어요", "cvb-dismiss", (e) => {
          if (!e.isTrusted) return;
          if (swapped(it.key)) return;
          arrived = null;
          localNote = null;
          act.confirm.dismiss(it.q);
        }),
      );
      return box;
    }
    if (it.kind === "master_screen") {
      box.append(el("div", "cvb-text", "마스터 창에 확인할 것이 떠 있어요 — 작업 화면에서 답해 주세요."));
      box.append(button("작업 화면에서 보기", "cvb-work", () => act.goView("work")));
      return box;
    }
    const a = it.a;
    if (it.stall === null) {
      box.append(el("div", "cvb-text", "도우미가 허락을 기다려요 — 마스터가 확인하는 중"));
      return box;
    }
    box.dataset.direct = "1";
    // 단추는 이 그리기 순간의 판(번호·시각·본문·좌석·지문)에 묶인다 — 누른 뒤 core 가 처리 직전 다시 받아 대조(FR-C5b).
    const bound = boundOf(a);
    const decide = (dec: "allow" | "deny") => (e: MouseEvent) => {
      if (!e.isTrusted) return; // 사람이 실제로 누른 클릭만(NFR-S5 ①② · 대본 클릭 무시 · 안내도 없음)
      if (act.confirm.busy) return;
      const r = allowReady(it, expanded.has(it.key), dec);
      if (!r.ok) {
        localNote = r.msg;
        paint();
        return;
      }
      // (s79 · F10) 보던 것과 다른 요청이 저절로 와 2초가 안 됐으면 처리 0 — 허락은 펼침(의도된 누름)이 먼저라 사실상 거절에 걸림
      if (swapped(it.key)) return;
      localNote = null;
      void act.confirm.decide(bound, dec);
    };
    if (!canAllowDirect(a)) {
      // 데몬 지문 표지 없음(지금 데몬) — 화면만으로는 지금 도우미 창이 그 명령인지 증명할 수 없다 → 직접 단추 = 거절 + 작업 화면에서 보기만(codex 1R blocking · master 결정)
      box.dataset.direct = "deny";
      box.append(el("div", "cvb-text", `도우미가 허락을 기다려요 — ${ALLOW_AT_WORK_MSG}`));
      const row = el("div", "cvb-actions");
      row.append(button("거절", "cvb-deny", decide("deny")), button("작업 화면에서 그 창 보기", "cvb-work", () => act.goView("work")));
      box.append(row);
      return box;
    }
    box.append(el("div", "cvb-text", `도우미가 허락을 기다려요 — ${STALL_TEXT[it.stall]}. 직접 정할 수 있어요.`));
    const open = expanded.has(it.key);
    const tog = button(open ? "접기" : "무엇을 보기", "cvb-what", () => {
      if (arrived?.key === it.key) arrived = null; // (s79 · F10) 펼침 = 사람이 이 요청을 들여다봄 — 저절로 온 표시를 거둠
      if (expanded.has(it.key)) expanded.delete(it.key);
      else expanded.add(it.key);
      localNote = null;
      paint();
    });
    tog.setAttribute("aria-expanded", String(open));
    box.append(tog);
    if (open) {
      const d = el("div", "cvb-detail");
      d.append(el("div", "cvb-dl", "무엇을 하려는지(도우미 화면의 명령 원문 그대로):"));
      d.append(el("pre", "cvb-cmd", a.command || a.excerpt));
      if (a.readonly) d.append(el("div", "cvb-ro", `기계 추정(근거 아님): ${a.readonly}`));
      d.append(el("div", "cvb-why", "왜: 왜 하는지는 도우미 화면에 없어요 · 마스터를 깨워 물어보세요."));
      if (a.truncated) {
        d.append(el("div", "cvb-trunc", "명령이 길어 다 보이지 않아요 — 작업 화면에서 확인해 주세요."));
        d.append(button("작업 화면에서 보기", "cvb-work", () => act.goView("work")));
      }
      box.append(d);
    }
    const allow = button("허락", "cvb-allow", decide("allow"));
    if (!open) {
      allow.setAttribute("aria-disabled", "true");
      allow.classList.add("cvb-dim");
      allow.title = "먼저 「무엇을 보기」를 펼쳐 주세요";
    }
    const deny = button("거절", "cvb-deny", decide("deny"));
    const row = el("div", "cvb-actions");
    row.append(allow, deny);
    box.append(row);
    return box;
  };

  function paint(): void {
    const b = act.confirm.band();
    const label = bandLabel(b);
    const items = b.items;
    // 펼침은 지금 있는 판에만 — 판이 바뀌면(같은 번호 · 다른 본문) 접힌 채 다시 보인다.
    for (const k of [...expanded]) if (!items.some((x) => x.key === k)) expanded.delete(k);
    if (answering && (act.state.msgs.length > answering.msgs || !items.some((x) => x.kind === "ask" && x.key === answering?.id))) setAnswering(null);
    if (answering?.uuid) ui.log.querySelector(`.cv-master[data-uuid="${CSS.escape(answering.uuid)}"]`)?.classList.add("cv-asked");
    let i = items.findIndex((x) => x.key === curKey);
    if (i < 0) {
      i = 0;
      // (s79 · F10) 보던 항목이 사라져 다른 항목이 같은 자리에 옴(「다음」을 누른 것이 아님) — 온 시각을 적어 잠깐 누름을 받지 않는다
      if (curKey !== null && items[0] && items[0].key !== arrived?.key) arrived = { key: items[0].key, at: Date.now() };
    }
    if (arrived && !items.some((x) => x.key === arrived?.key)) arrived = null;
    curKey = items[i]?.key ?? null;
    head.textContent = label ?? "";
    body.replaceChildren(...(items[i] ? [itemNode(items[i])] : []));
    nav.replaceChildren();
    if (items.length > 1) {
      nav.append(el("span", "cvb-pos", `${i + 1} / ${items.length}`));
      nav.append(
        button("다음", "cvb-next", () => {
          curKey = items[(i + 1) % items.length].key;
          // 저절로 온 표시(arrived)는 그대로 — 「다음」으로 갔다 2초 안에 되돌아와도 보호가 남는다(codex 1R major)
          localNote = null;
          paint();
        }),
      );
    }
    const note = localNote ?? act.confirm.notice;
    notice.textContent = note ?? "";
    notice.hidden = !note;
    root.hidden = label === null && !note;
    root.dataset.count = b.known ? String(items.length) : "";
  }

  return {
    el: root,
    hint,
    paint,
    summary() {
      const b = act.confirm.band();
      return { text: bandLabel(b) ?? "확인할 것 없음", count: b.known ? String(b.items.length) : "" };
    },
  };
}
