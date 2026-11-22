// (cysr-ui-slice1) 대화 화면 1호 — 그리기만(판정은 judge/ · 행동은 ctx.act). P2-DESIGN §11 조각 1 최소판.
//
// 글은 전부 textContent 로만 넣는다(사람·마스터 글에 HTML 해석 0). 입력칸은 다시 그리지 않는다(포커스·한글 조합 보존 · §9-2).
// 최소 계약 4칸 = [data-min=confirms|lastSendStep|masterHealth|errors] · 화면 바꾸기는 공통 자리(#view-switch).

import type { ViewContext, ViewInstance, ViewModule } from "../contract";
import { DUP, dupPending, errorCount, HEALTH_LABEL, lastSendStep, logOrder, needsClick, POLL_MS, SAME_DELIVERED_NOTE, sameTextDelivered, type ChatCore, type ChatState } from "../core";
import { canRetry, STEP_LABEL, type Msg } from "../judge/msgstep";
import { AUTO_STEP_LABEL, type AutoMsg } from "../judge/autostep";
import { liveMsg, progressLine, stepTime } from "../judge/progress";
import { createBand } from "./band";
import { createResults } from "./results"; // (s79 조각 7) 결과 받기 칸·카드
import { createReviveBand } from "./reviveband";
import { createRail, guideCard, isWindowsUa, quickReplies } from "./rail";

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

export const chatView: ViewModule<ChatState, ChatCore> = {
  mount(host: HTMLElement, ctx: ViewContext<ChatState, ChatCore>): ViewInstance {
    const act = ctx.act;
    const root = el("section", "cv");
    root.setAttribute("aria-label", "대화 화면");

    const head = el("div", "cv-head");
    const health = el("div", "cv-health");
    health.dataset.min = "masterHealth";
    const confirms = el("div", "cv-confirms");
    confirms.dataset.min = "confirms";
    const errors = el("div", "cv-errors");
    errors.dataset.min = "errors";
    // (조각 6 · §16-6) 「부서 안내」 — 저장소와 무관하게 늘 열림(가이드 다시 보기)
    const guideBtn = el("button", "cv-guide-btn", "부서 안내");
    guideBtn.type = "button";
    guideBtn.addEventListener("click", (e) => {
      if (!e.isTrusted) return;
      act.rail.toggleGuide();
    });
    head.append(health, confirms, errors, guideBtn);

    const log = el("ol", "cv-log");
    log.setAttribute("aria-label", "대화");
    const empty = el("li", "cv-empty", "마스터에게 하고 싶은 말을 아래에 적어 보내세요. 예: 「오늘 할 일을 정리해 줘」");

    const live = el("div", "cv-live");
    live.setAttribute("aria-live", "polite");
    live.dataset.min = "lastSendStep";

    const form = el("form", "cv-form");
    const input = el("textarea", "cv-input");
    input.rows = 3;
    input.placeholder = "마스터에게 보낼 말 (Enter 보내기 · Shift+Enter 줄바꿈)";
    input.setAttribute("aria-label", "마스터에게 보낼 말");
    input.value = act.state.draft;
    const sendBtn = el("button", "cv-send", "보내기");
    sendBtn.type = "submit";
    const notice = el("div", "cv-notice");
    notice.setAttribute("role", "status");
    form.append(input, sendBtn);

    // (조각 4) 확인 대기 띠 = 화면 맨 위 · 「답하는 물음」 줄 = 입력칸 바로 위
    const band = createBand(act, { log, input });
    // (조각 5) 마스터 멈춤·깨우기·다시 켜기 띠 = 맨 위(확인 대기 띠 위)
    const revive = createReviveBand(act);
    root.append(revive.el, band.el, head, log, live, band.hint, form, notice);
    // (조각 6) 왼쪽 메뉴바(맡긴 일·팀·부서·결과 자리) + 가운데 대화 — 한 줄로(시안 rail)
    const rail = createRail();
    const wrap = el("div", "cv-wrap");
    wrap.append(rail.el, root);
    host.append(wrap);
    const win = isWindowsUa(typeof navigator === "undefined" ? "" : navigator.userAgent);
    // (s79 조각 7) 「결과 N」 칸 — rail 틀(조각 6)이 들어오면 그 왼쪽 칸으로 옮긴다(통합 때 master 조정) · 지금은 대화 위
    //   (통합 cysr-1116-integ-1120: 옮기기 = 화면 배치 결정이라 master 📌 · 이 판은 대화 위 그대로)
    const results = createResults(act, { log, input });
    root.insertBefore(results.el, log);

    const submit = () => {
      const text = input.value;
      if (!text.trim()) return;
      if (act.submit(text)) {
        input.value = ""; // 받아들인 말만 비운다 — 막힌 말(`/clear` 등)은 고칠 수 있게 남긴다
        act.setDraft("");
      }
      input.focus();
    };
    const onInput = () => act.setDraft(input.value);
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Enter" || e.shiftKey || e.isComposing || e.keyCode === 229) return; // 한글 조합 중 Enter 무시(§9-2)
      e.preventDefault();
      submit();
    };
    const onSubmit = (e: Event) => {
      e.preventDefault();
      submit();
    };
    input.addEventListener("input", onInput);
    input.addEventListener("keydown", onKey);
    form.addEventListener("submit", onSubmit);

    // (TICKET=cysr-1118-ui ①) 진행 줄 — 접힌 한 줄(지금 단계 · 단서 · 경과 초) · 누르면 「과정 보기」(실제 단계 목록 · 시각). 펼침 = 이 화면 메모리만.
    const openProg = new Set<string>();
    const prog = (m: Msg, live: boolean): HTMLElement | null => {
      const p = progressLine(m, Date.now(), live);
      if (!p) return null;
      const steps = m.steps ?? [];
      const box = el("div", `cv-prog${p.live ? " live" : ""}`);
      box.dataset.msgId = m.id;
      const open = openProg.has(m.id) && steps.length > 0;
      const btn = el("button", "cv-prog-head");
      btn.type = "button";
      btn.disabled = steps.length === 0;
      btn.setAttribute("aria-expanded", String(open));
      btn.title = steps.length ? (open ? "과정 접기" : "과정 보기 — 읽은 파일 · 실행한 명령 · 찾은 말 · 중간 글") : "아직 과정 기록이 없어요";
      btn.append(el("span", "cv-prog-caret", steps.length ? (open ? "▾" : "▸") : "•"), el("span", "cv-prog-text", p.text));
      btn.addEventListener("click", () => {
        if (openProg.has(m.id)) openProg.delete(m.id);
        else openProg.add(m.id);
        const cur = act.state.msgs.find((x) => x.id === m.id);
        const next = cur ? prog(cur, liveMsg(act.state.msgs) === cur) : null;
        if (next) box.replaceWith(next);
      });
      box.append(btn);
      if (open) {
        const ol = el("ol", "cv-steps");
        ol.setAttribute("aria-label", "과정");
        for (const st of steps) {
          const li = el("li", `cv-stepi k-${st.kind}`);
          li.append(el("span", "cv-stepi-at", stepTime(st.at)), el("span", "cv-stepi-label", st.label));
          if (st.hint) li.append(el("span", "cv-stepi-hint", st.hint));
          ol.append(li);
        }
        box.append(ol);
      }
      return box;
    };
    // 경과 초 = 1초마다 글만 바꾼다(말 목록 전체를 다시 그리지 않음 · 입력칸·스크롤 그대로)
    ctx.timers.every(1_000, () => {
      for (const t of log.querySelectorAll<HTMLElement>(".cv-prog.live")) {
        const m = act.state.msgs.find((x) => x.id === t.dataset.msgId);
        const p = m ? progressLine(m, Date.now(), true) : null;
        const txt = t.querySelector(".cv-prog-text");
        if (p && txt && txt.textContent !== p.text) txt.textContent = p.text;
      }
    });

    const bubble = (m: Msg, s: ChatState, live: boolean): HTMLLIElement => {
      const li = el("li", `cv-msg cv-me step-${m.step}`);
      li.dataset.msgId = m.id;
      li.append(el("div", "cv-text", m.text));
      const meta = el("div", "cv-step", STEP_LABEL[m.step]);
      meta.dataset.step = m.step;
      li.append(meta);
      const pg = prog(m, live);
      if (pg) li.append(pg);
      if (m.note) li.append(el("div", "cv-note", m.note));
      // (조각 3 · PRD FR-A2a) 오래 걸려요 = 마스터 상태를 함께 보인다(근거 없이 「못 보냄」으로 바꾸지 않음 · 다시 보내기 0).
      if (m.step === "slow") li.append(el("div", "cv-note cv-slow-health", `마스터 상태: ${HEALTH_LABEL[s.health]} — 다시 보내지 않고 계속 확인해요.`));
      // (조각 3) 같은 말 겹침: 앞 말이 끝나기 전에는 누를 단추가 없다(불명·확인 중 = 다시 보내기 0).
      const dupBlocked = m.code === DUP && dupPending(s.msgs, m.text, m.id);
      if (needsClick(m) && !dupBlocked) {
        const b = el("button", "cv-retry cv-confirm", m.code === DUP ? "한 번 더 보내기" : "이 말 보내기");
        b.type = "button";
        b.addEventListener("click", (e) => {
          if (!e.isTrusted) return; // 복원·10분 넘은 말은 사람의 신뢰 클릭으로만(자동 제출 0)
          void act.confirmHeld(m.id);
        });
        li.append(b);
      }
      // (조각 3 고침 · 검증 지적 H) 같은 글이 이미 전달됐으면 다시 보내기를 거두고 그 사실만 알린다.
      if (canRetry(m) && sameTextDelivered(s.msgs, m.text, m.id)) li.append(el("div", "cv-note cv-same-delivered", SAME_DELIVERED_NOTE));
      else if (canRetry(m) && !dupPending(s.msgs, m.text, m.id)) {
        const b = el("button", "cv-retry", "다시 보내기");
        b.type = "button";
        b.addEventListener("click", (e) => {
          if (!e.isTrusted) return; // 사람의 신뢰 클릭만(NFR-S5)
          void act.retry(m.id);
        });
        li.append(b);
      }
      return li;
    };
    // (조각 3) 기계 문안(깨움 말·1회 안내) = 사람 말이 아니므로 말풍선이 아니라 한 줄 표지(§5-2 auto · 단계는 큐 사건으로만).
    const autoLine = (a: AutoMsg): HTMLLIElement => {
      const li = el("li", `cv-auto auto-${a.step}`, `자동 안내: ${AUTO_STEP_LABEL[a.step]}`);
      li.dataset.entry = a.entryId;
      li.dataset.step = a.step;
      return li;
    };
    const masterBubble = (text: string, uuid: string | null = null, last = false): HTMLLIElement => {
      const li = el("li", "cv-msg cv-master");
      if (uuid) li.dataset.uuid = uuid; // (조각 4) 「대화에서 답하기」가 그 물음 자리를 찾는 표지
      li.append(el("div", "cv-who", "마스터"), el("div", "cv-text", text));
      // (조각 6 · §5-4 D7) ⟪팀 제안⟫·⟪부서 제안: 팀⟫ = 마지막 말일 때만 빠른 답 2개(누르면 그 글 그대로 보냄)
      if (last) {
        const q = quickReplies(text, (t) => {
          if (act.submit(t)) input.focus();
        });
        if (q) li.append(q);
      }
      return li;
    };

    let lastRev = -1;
    const paint = (s: ChatState) => {
      if (s.rev === lastRev) return;
      lastRev = s.rev;
      health.textContent = HEALTH_LABEL[s.health];
      health.dataset.health = s.health;
      // (조각 4) 확인 대기 수 = 띠와 같은 값(마스터 물음 + 승인 대기 · 모르면 「살펴보는 중」)
      const sum = band.summary();
      confirms.textContent = sum.text;
      confirms.dataset.count = sum.count;
      const ec = errorCount(s);
      errors.textContent = ec > 0 ? `문제 ${ec}` : "문제 없음";
      errors.dataset.count = String(ec);
      const st = lastSendStep(s);
      live.textContent = st ? `마지막 보낸 말: ${STEP_LABEL[st]}` : "아직 보낸 말 없음";
      live.dataset.step = st ?? "";
      notice.textContent = s.notice ?? "";
      const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 4;
      log.replaceChildren();
      if (s.msgs.length === 0 && s.stray.length === 0 && s.autos.length === 0) log.append(empty);
      // (조각 3 고침 · 검증 지적 B) 어느 말에도 안 묶인 마스터 글은 시각순으로 사람 말 사이에 끼운다(사람 말들 뒤에 몰리지 않게).
      const order = logOrder(s.msgs, s.stray);
      const lastItem = order[order.length - 1];
      const liveM = liveMsg(s.msgs); // (TICKET=cysr-1118-ui ①) 진행 줄을 살아 있게 다는 말(가장 최근 · 답 기다림)
      for (const id of [...openProg]) if (!s.msgs.some((m) => m.id === id)) openProg.delete(id); // (codex 1R minor) 밀려난 말의 펼침 상태는 버린다(보관량 = 지금 말 수 이하)
      for (const it of order) {
        if (it.kind === "stray") {
          log.append(masterBubble(it.r.text, it.r.uuid, it === lastItem));
          continue;
        }
        log.append(bubble(it.m, s, it.m === liveM));
        it.m.replies.forEach((r, k) => log.append(masterBubble(r.text, r.uuid, it === lastItem && k === it.m.replies.length - 1)));
      }
      for (const a of s.autos) log.append(autoLine(a));
      // (조각 6 · §16-6) 처음 부서가 생기면 한 번 · 「부서 안내」로 다시 보기
      if (act.rail.guide) log.append(guideCard(act.rail.guide, win, { ack: () => act.rail.ackGuide(), close: () => act.rail.toggleGuide() }));
      rail.paint(s, act.rail.model);
      band.paint(); // (조각 4) 말 목록을 다시 그린 뒤 — 답하는 물음 자리 표시를 다시 단다
      results.paint(); // (s79 조각 7) 결과 칸 + 대화 안 카드(그 경로를 말한 마스터 답 뒤)
      revive.paint(); // (조각 5)
      if (atBottom) log.scrollTop = log.scrollHeight;
    };
    ctx.subscribe(paint);
    paint(act.state);
    act.attach();
    void act.poll();
    ctx.timers.every(POLL_MS, () => void act.poll());
    // 이 자리는 아직 숨겨져 있다(registry 가 옛 화면을 내리며 같은 전환 안에서 보이게 함) — 숨은 요소엔 포커스가 안 들어가므로 전환 끝에 준다.
    queueMicrotask(() => {
      if (root.isConnected) input.focus();
    });

    return {
      unmount() {
        act.detach();
        input.removeEventListener("input", onInput);
        input.removeEventListener("keydown", onKey);
        form.removeEventListener("submit", onSubmit);
        wrap.remove();
      },
      snapshot: () => ({ scrollTop: log.scrollTop }),
      restore: (s: unknown) => {
        const t = (s as { scrollTop?: unknown } | null)?.scrollTop;
        if (typeof t === "number") log.scrollTop = t;
      },
    };
  },
};
