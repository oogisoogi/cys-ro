// (TICKET=cysr-1119-s12 · DESIGN §4-3 CV-PEEK 고침판) 대화 화면 보기 칸 — 껍데기(머리·안내·터미널 자리)만. 터미널 옮겨 붙이기·배율·읽기 전용은 main.ts(act.peek).
//
// 자리: 창 > 1410px = 대화 칸 오른쪽 칸(폭 max(rail 뺀 나머지 45%, 480px)) · ≤ 1410px = 대화 칸 위 덮개(master#048a4917)(대화 칸을 좁히지 않음 · C-05) — views.css.
// 머리줄에 좌석 닫기(×)·이름 바꾸기·끌기 없음(K-2 #5 · 작업 화면 머리줄은 제자리). 글은 전부 textContent. 누를 면 44px · 글자 18px.

import type { Helper } from "../judge/rail";
import type { PeekPort } from "../core";

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

export const PEEK_TEXT = {
  region: "워커 창 보기",
  ro: "읽기 전용",
  big: "작업 화면에서 크게",
  answer: "작업 화면에서 답하기",
  close: "닫기",
  closeLabel: "보기 칸 닫기",
  nosize: "이 창의 크기를 아직 몰라 여기서 열지 못했어요.",
  gone: "이 창을 지금 열 수 없어요.",
  toWork: "작업 화면에서 보기",
} as const;

export interface PeekPanel {
  el: HTMLElement;
  /** 지금 보기 칸에 있는 좌석(없으면 null) — rail 다시 그리기가 「보는 중」 표시에 쓴다 */
  sid(): number | null;
  open(h: Helper): void;
  /** rail 모델이 바뀔 때 — 머리 글·「답하기」 단추를 맞춘다(좌석이 목록에서 사라지면 닫음) */
  sync(helpers: readonly Helper[], loading: boolean): void;
  /** 화면을 내릴 때 — 문서 keydown 듣기 해제 */
  destroy(): void;
}

export function createPeekPanel(port: PeekPort | null, wrap: HTMLElement, onChange: () => void): PeekPanel {
  const box = el("aside", "cv-peek");
  box.setAttribute("role", "region");
  box.setAttribute("aria-label", PEEK_TEXT.region);
  box.hidden = true;
  const head = el("div", "cv-peek-head");
  const name = el("span", "cv-peek-name");
  const ro = el("span", "cv-peek-ro", PEEK_TEXT.ro);
  const answer = el("button", "cv-peek-btn cv-peek-answer", PEEK_TEXT.answer);
  answer.type = "button";
  answer.hidden = true;
  const big = el("button", "cv-peek-btn cv-peek-big", PEEK_TEXT.big);
  big.type = "button";
  const close = el("button", "cv-peek-btn cv-peek-close", PEEK_TEXT.close);
  close.type = "button";
  close.setAttribute("aria-label", PEEK_TEXT.closeLabel);
  head.append(name, ro, answer, big, close);
  const note = el("div", "cv-peek-note");
  note.setAttribute("role", "status");
  note.hidden = true;
  const body = el("div", "cv-peek-body");
  const host = el("div", "cv-peek-host"); // main.ts 가 배율 요소 + termHost 를 여기에 붙인다
  body.append(host);
  box.append(head, note, body);

  let cur: Helper | null = null;
  let seq = 0; // 열기 차례 — 늦게 끝난 옛 열기가 새 칸을 바꾸지 않게
  const shut = () => {
    cur = null;
    box.hidden = true;
    note.hidden = true;
    wrap.classList.remove("peek-open");
    onChange();
  };
  const show = (h: Helper) => {
    cur = h;
    name.textContent = h.label;
    answer.hidden = !h.need;
    box.hidden = false;
    wrap.classList.add("peek-open");
  };
  const fail = (text: string, h: Helper) => {
    note.replaceChildren(el("span", undefined, text), " ");
    const b = el("button", "cv-peek-btn", PEEK_TEXT.toWork);
    b.type = "button";
    b.addEventListener("click", (e) => {
      if (!e.isTrusted) return;
      port?.big(h.sid);
    });
    note.append(b);
    note.hidden = false;
  };
  const open = (h: Helper) => {
    if (!port) return;
    if (cur?.sid === h.sid && !box.hidden && port.openSid() === h.sid) return; // 이미 붙은 같은 좌석만 무시 — 안내만 뜬 칸·만드는 중은 다시 누르면 다시 연다(검증 M2)
    const my = ++seq;
    note.hidden = true;
    show(h);
    onChange();
    void port
      .open(h.sid, host, () => {
        if (my === seq) shut();
      })
      .then((r) => {
        if (my !== seq || r === "ok") return;
        if (r === "busy") return;
        fail(r === "nosize" ? PEEK_TEXT.nosize : PEEK_TEXT.gone, h);
      });
  };
  close.addEventListener("click", (e) => {
    if (!e.isTrusted) return;
    seq++; // 진행 중인 열기가 늦게 끝나도 이 칸을 다시 열지 않게
    port?.close("button"); // 열린 칸이 없어도 부른다 — main.ts 쪽 진행 중인 열기를 취소한다
    shut();
  });
  big.addEventListener("click", (e) => {
    if (!e.isTrusted || !cur) return;
    port?.big(cur.sid);
  });
  answer.addEventListener("click", (e) => {
    if (!e.isTrusted || !cur) return;
    port?.big(cur.sid); // 승인 창은 작업 화면 그 좌석에서 답한다(보기 칸 = 읽기 전용)
  });
  // (검증 M1) Esc = 닫기 — 만드는 중이거나 안내만 뜬 칸도(main.ts 전역 Esc 는 터미널이 붙은 뒤에만 안다) · 진행 중인 열기도 취소
  const onEsc = (e: KeyboardEvent) => {
    if (e.key !== "Escape" || box.hidden || e.isComposing || e.keyCode === 229) return; // (검증 NEW-2) 한글 조합 취소 Esc 는 칸을 닫지 않는다
    seq++;
    port?.close("esc");
    shut();
  };
  document.addEventListener("keydown", onEsc);
  const sync = (helpers: readonly Helper[], loading: boolean) => {
    if (!cur || loading) return; // 목록을 아직(또는 다시) 못 받은 그리기 = 판정 0(일시 실패로 칸을 닫지 않는다 · ㉯ 코드 성찰 고침 3)
    const h = helpers.find((x) => x.sid === cur!.sid);
    if (!h) {
      seq++;
      port?.close("gone");
      shut();
      return;
    }
    if (h.label !== cur.label || h.need !== cur.need) show(h);
  };
  const destroy = () => document.removeEventListener("keydown", onEsc);
  return { el: box, sid: () => cur?.sid ?? null, open, sync, destroy };
}
