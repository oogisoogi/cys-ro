// (cysr-1116-s6 · TICKET=cysr-1116-s6-1119) 대화 화면 왼쪽 메뉴바 그리기 + 부서 가이드 카드 + 빠른 답 단추. P2-DESIGN §11 조각 6 · §16-5 · §16-6.
//
// 시안 = cysr-ui-research/P2-mock app.js rail()(마스터 카드 · 맡긴 일 N · 팀 묶음 · 부서 N · 결과 N) · guideCard().
// 글은 전부 textContent(HTML 해석 0) · 누를 면 44px · 글자 18px 이상(§9-2). 판정은 judge/rail.ts · 장부는 ../rail.ts.
// 「결과 N」 칸은 조각 7 이 채운다 — 여기서는 자리([data-rail=results])만 두고 비어 있으면 숨긴다(판정 0).

import { HEALTH_LABEL, type ChatState } from "../core";
import { agoText, CARD_STATUS, DEPT_REPLY_NO, DEPT_REPLY_YES, quickReplyOf, TEAM_REPLY_NO, TEAM_REPLY_YES, type RailModel } from "../judge/rail";

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

export interface RailView {
  el: HTMLElement;
  /** 결과 자리(조각 7 이 채운다 · 비면 숨김) */
  results: HTMLElement;
  paint(s: ChatState, m: RailModel): void;
}

export function createRail(): RailView {
  const aside = el("aside", "cv-rail");
  aside.setAttribute("aria-label", "맡긴 일");
  const who = el("div", "cvr-who");
  who.dataset.rail = "master";
  const av = el("span", "cvr-av", "마");
  av.setAttribute("aria-hidden", "true");
  const whoText = el("span", "cvr-who-text");
  const whoName = el("b", undefined, "마스터");
  const whoSt = el("div", "cvr-st");
  whoText.append(whoName, whoSt);
  who.append(av, whoText);
  const tasks = el("div", "cvr-tasks");
  tasks.dataset.rail = "tasks";
  const depts = el("div", "cvr-depts");
  depts.dataset.rail = "depts";
  const results = el("div", "cvr-results");
  results.dataset.rail = "results";
  results.hidden = true; // 조각 7 이 채우기 전 = 빈 상태 = 숨김
  aside.append(who, tasks, depts, results);

  let last = "";
  const paint = (s: ChatState, m: RailModel) => {
    const sig = JSON.stringify([s.health, m]);
    if (sig === last) return;
    last = sig;
    whoSt.textContent = HEALTH_LABEL[s.health];
    who.dataset.health = s.health;
    who.classList.toggle("down", s.health === "off" || s.health === "none" || s.health === "gate");

    const head = el("h2", "cvr-h", m.loading ? "맡긴 일" : `맡긴 일 ${m.taskCount}`);
    const out: HTMLElement[] = [head];
    if (m.loading) out.push(card("불러오는 중이에요", null, "cvr-card cvr-loading"));
    for (const f of m.forming) {
      const c = card(f.name, f.line, `cvr-card cvr-forming cvr-${f.kind}`);
      c.dataset.forming = f.kind;
      out.push(c);
    }
    if (!m.loading && m.taskCount === 0 && m.forming.length === 0) out.push(el("p", "cvr-empty", "아직 맡긴 일이 없어요. 가운데에 맡길 일을 적어 보세요."));
    for (const b of m.blocks) {
      if (b.team !== null) {
        const h = el("h3", "cvr-team");
        h.dataset.team = b.team;
        h.append(document.createTextNode(b.team), el("span", "cvr-sum", ` · ${b.summary}`));
        out.push(h);
      }
      for (const t of b.cards) {
        const st = CARD_STATUS[t.status];
        const c = el("div", `cvr-card st-${t.status}`);
        c.dataset.task = t.key;
        c.dataset.status = t.status;
        if (b.team !== null) c.dataset.team = b.team;
        c.append(el("div", "cvr-t", t.title));
        const line = el("div", "cvr-s");
        line.append(el("i", "cvr-mk", st.mark), document.createTextNode(t.status === "unknown" ? st.label : `${st.label} · ${agoText(t.newsSecs)}`));
        c.append(line);
        c.append(el("div", "cvr-s cvr-help", `도우미 ${t.helpers}명`));
        out.push(c);
      }
    }
    tasks.replaceChildren(...out);

    const dl: HTMLElement[] = [];
    if (m.depts.length) {
      dl.push(el("h2", "cvr-h", `부서 ${m.depts.length}`));
      for (const d of m.depts) {
        const c = card(d.title, "부서 마스터가 맡고 있어요", "cvr-card cvr-dept");
        c.dataset.dept = d.name;
        dl.push(c);
      }
    }
    depts.replaceChildren(...dl);
    depts.hidden = dl.length === 0;
    results.hidden = results.childElementCount === 0;
  };
  return { el: aside, results, paint };
}

function card(title: string, line: string | null, cls: string): HTMLElement {
  const c = el("div", cls);
  c.append(el("div", "cvr-t", title));
  if (line) c.append(el("div", "cvr-s", line));
  return c;
}

/** 운영체제 — 가이드 3번 줄을 닫기 카드(javis_dept_request.py render_close_card `keep` 분기)와 같게 고른다. */
export function isWindowsUa(ua: string): boolean {
  return /Windows/i.test(ua);
}

/** 부서 가이드 원문(§16-5 ② · 시안 GUIDE) — 3번 줄만 운영체제별. 꼬리는 이 화면의 실제 자리(머리 줄 「부서 안내」 단추)로 적는다. */
export function guideLines(win: boolean): { title: string; lines: string[]; again: string; ok: string } {
  return {
    title: "부서, 이렇게 쓰면 돼요",
    lines: [
      "부서는 한 가지 일을 오래 맡는 작은 팀이에요. 부서 마스터와 도우미 3명이 따로 일해요.",
      "저는 여러 부서를 함께 살피는 역할로 바뀌어요. 마지막 부서를 닫으면 다시 보통 마스터로 돌아와요.",
      win
        ? "언제든 「홍보팀 부서 닫아 줘」라고 말하면 닫을 수 있어요. 만든 파일은 폴더에 그대로 남고, 대화 기록도 이 컴퓨터에 그대로 남아요(저절로 정리되지 않아요)."
        : "언제든 「홍보팀 부서 닫아 줘」라고 말하면 닫을 수 있어요. 만든 파일은 폴더에 그대로 남고, 대화 기록은 휴지통에 보관돼요.",
      "닫으면 부서 도우미가 바로 꺼져서, 하던 일이 있으면 거기서 멈춰요. 하던 일이 끝난 뒤에 닫아 달라고 하시는 게 좋아요. 남은 일은 저에게 다시 맡기시면 돼요.",
      "만들 때와 닫을 때 제가 확인을 여쭤보면 「네」라고 직접 답해 주세요. 처음 한 번 「이 폴더를 믿겠습니까」 창이 뜨면 「예」 쪽을 눌러 주세요.",
    ],
    again: "이 안내는 오른쪽 위 「부서 안내」 단추로 다시 볼 수 있어요.",
    ok: "알겠어요",
  };
}

/** 가이드 카드(대화 목록 안 한 줄). first = 「알겠어요」 단추(누르면 본 적 있음) · again = 닫기 단추만. */
export function guideCard(mode: "first" | "again", win: boolean, on: { ack(): void; close(): void }): HTMLLIElement {
  const g = guideLines(win);
  const li = el("li", "cv-guide");
  li.dataset.guide = mode;
  const sec = el("section", "cvg-card");
  sec.setAttribute("aria-label", "부서 안내");
  sec.append(el("h3", "cvg-h", g.title));
  const ol = el("ol", "cvg-list");
  for (const l of g.lines) ol.append(el("li", undefined, l));
  sec.append(ol);
  const acts = el("div", "cvg-acts");
  const b = el("button", "cv-retry cvg-btn", mode === "first" ? g.ok : "닫기");
  b.type = "button";
  b.addEventListener("click", (e) => {
    if (!e.isTrusted) return; // 사람의 신뢰 클릭만
    if (mode === "first") on.ack();
    else on.close();
  });
  acts.append(b);
  sec.append(acts);
  if (mode === "first") sec.append(el("p", "cvg-note", g.again));
  li.append(sec);
  return li;
}

/** 마스터 답 끝 빠른 답 단추(§5-4 · D7 마스터 먼저 제안 · §16-5 ①) — 마지막 말일 때만 붙인다(뒤에 말이 오면 사라짐).
 *  누르면 단추 글을 **그대로** 보낸 말로(send) — 화면은 판정하지 않는다. 사람의 신뢰 클릭만. */
export function quickReplies(text: string, send: (t: string) => void): HTMLElement | null {
  const q = quickReplyOf(text);
  if (!q) return null;
  const [yes, no] = q.kind === "team" ? [TEAM_REPLY_YES, TEAM_REPLY_NO] : [DEPT_REPLY_YES, DEPT_REPLY_NO];
  const row = el("div", "cv-quick");
  row.dataset.quick = q.kind;
  for (const t of [yes, no]) {
    const b = el("button", "cv-retry cv-quick-btn", t);
    b.type = "button";
    b.addEventListener("click", (e) => {
      if (!e.isTrusted) return;
      send(t);
    });
    row.append(b);
  }
  return row;
}
