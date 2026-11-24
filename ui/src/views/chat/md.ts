// (TICKET=cysr-1119-s6 · V1) 마크다운 나무 → DOM(DESIGN §6 V1 · VISUAL 카드 V1).
//
// 받는 글 = 마스터 답(믿지 못할 글). 요소는 createElement 로만 만들고 글은 textContent·글 마디로만 넣는다.
// 쓰는 속성 = 고정 className 뿐 — href·src·title·data-*·style·이벤트 속성 0 · innerHTML 0 · 외부 라이브러리 0.
// 링크 = 「글 (주소)」 보이는 글(누를 것 0 · 주소를 복사·열람할 수 있게 · C-11) · 그림·HTML 꼴 = 원문 글(judge/md.ts).

import { parseMd, type Inline } from "../judge/md";

/** 되돌리기 상수 — false = 지금 꼴(마스터 말 = textContent + pre-wrap 풍선 · chat/index.ts masterBubble). */
export const MD_RENDER = true;

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function inline(parent: HTMLElement, c: Inline[]): void {
  for (const n of c) {
    if (n.k === "text") parent.append(document.createTextNode(n.v));
    else if (n.k === "code") parent.append(el("code", undefined, n.v));
    else if (n.k === "strong" || n.k === "em") {
      const e = el(n.k);
      inline(e, n.c);
      parent.append(e);
    } else {
      const e = el("span", "cv-md-link");
      inline(e, n.c);
      parent.append(e, el("span", "cv-md-url", ` (${n.url})`));
    }
  }
}

function pre(v: string): HTMLPreElement {
  const pre = el("pre");
  pre.append(el("code", undefined, v));
  return pre;
}

/** 마스터 답 글 → `div.cv-md`(블록 나무 그대로 · 64KB 넘는 뒤쪽 = `div.cv-md-raw` 원문). */
export function renderMd(text: string): HTMLDivElement {
  const root = el("div", "cv-md");
  for (const b of parseMd(text)) {
    if (b.k === "h") {
      const h = el(b.level === 1 ? "h1" : b.level === 2 ? "h2" : "h3");
      inline(h, b.c);
      root.append(h);
    } else if (b.k === "p") {
      const p = el("p");
      inline(p, b.c);
      root.append(p);
    } else if (b.k === "pre") {
      root.append(pre(b.v));
    } else if (b.k === "list") {
      const list = el(b.ordered ? "ol" : "ul");
      for (const it of b.items) {
        const li = el("li", `${it.num === null ? "cv-md-bul" : "cv-md-num"}${it.depth === 1 ? " cv-md-d1" : ""}`);
        if (it.num !== null) li.append(el("span", "cv-md-n", `${it.num} `)); // 적힌 번호 그대로(글 · 복사해도 남음)
        inline(li, it.c);
        for (const m of it.more) { // (fix H5 · M1) 항목 안 울타리·뒤 글 = 그 항목 안 블록
          if (m.k === "pre") li.append(pre(m.v));
          else {
            const p = el("p");
            inline(p, m.c);
            li.append(p);
          }
        }
        list.append(li);
      }
      root.append(list);
    } else if (b.k === "table") {
      const wrap = el("div", "cv-md-table"); // 넓은 표 = 가로 스크롤(말 칸 밖으로 안 넘침)
      const table = el("table");
      const thead = el("thead");
      const hr = el("tr");
      for (const c of b.head) {
        const th = el("th");
        inline(th, c);
        hr.append(th);
      }
      thead.append(hr);
      const tbody = el("tbody");
      for (const r of b.rows) {
        const tr = el("tr");
        for (const c of r) {
          const td = el("td");
          inline(td, c);
          tr.append(td);
        }
        tbody.append(tr);
      }
      table.append(thead, tbody);
      wrap.append(table);
      root.append(wrap);
    } else root.append(el("div", "cv-md-raw", b.v));
  }
  return root;
}

/**
 * (fix-1119-s6-adv M3) 답 마디 저장 — 조회(3초)마다 대화 칸을 다시 채울 때 글이 같은 답은 renderMd 를 다시 부르지 않고 같은 마디를 돌려준다.
 * 다시 붙인 마디는 가로 스크롤 자리가 0 이 되므로 비우기 전(beforeClear) 넓은 울타리·표의 scrollLeft 를 적고 다 붙인 뒤(afterFill) 되돌린다 ·
 * 이번 그리기에 안 나온 열쇠는 버린다(메모리) · 한 그리기에 같은 열쇠가 두 번(열쇠 없는 같은 글 둘) = 마디를 옮기지 않게 새로 그림.
 */
export function mdKeeper() {
  const kept = new Map<string, { text: string; node: HTMLDivElement; sx: number[]; used: boolean }>();
  const scrollers = (n: HTMLElement): HTMLElement[] => [...n.querySelectorAll<HTMLElement>("pre, .cv-md-table")];
  return {
    node(key: string, text: string): HTMLDivElement {
      const k = kept.get(key);
      if (k && k.text === text && !k.used) {
        k.used = true;
        return k.node;
      }
      const node = renderMd(text);
      if (k?.used) return node;
      kept.set(key, { text, node, sx: [], used: true });
      return node;
    },
    beforeClear(): void {
      for (const k of kept.values()) {
        k.sx = scrollers(k.node).map((e) => e.scrollLeft);
        k.used = false;
      }
    },
    afterFill(): void {
      for (const [key, k] of kept) {
        if (!k.used) kept.delete(key);
        else if (k.sx.some((x) => x > 0)) scrollers(k.node).forEach((e, n) => (e.scrollLeft = k.sx[n] ?? 0));
      }
    },
    size: (): number => kept.size,
  };
}
