// (cysr-ui-slice1) 대화 화면 1호 — 그리기만(판정은 judge/ · 행동은 ctx.act). P2-DESIGN §11 조각 1 최소판.
//
// 글은 전부 textContent 로만 넣는다(사람·마스터 글에 HTML 해석 0). 입력칸은 다시 그리지 않는다(포커스·한글 조합 보존 · §9-2).
// 최소 계약 4칸 = [data-min=confirms|lastSendStep|masterHealth|errors] · 화면 바꾸기는 공통 자리(#view-switch).

import type { ViewContext, ViewInstance, ViewModule } from "../contract";
import { errorCount, HEALTH_LABEL, lastSendStep, POLL_MS, RESTORED, type ChatCore, type ChatState } from "../core";
import { canRetry, STEP_LABEL, type Msg } from "../judge/msgstep";

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
    head.append(health, confirms, errors);

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

    root.append(head, log, live, form, notice);
    host.append(root);

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

    const bubble = (m: Msg): HTMLLIElement => {
      const li = el("li", `cv-msg cv-me step-${m.step}`);
      li.dataset.msgId = m.id;
      li.append(el("div", "cv-text", m.text));
      const meta = el("div", "cv-step", STEP_LABEL[m.step]);
      meta.dataset.step = m.step;
      li.append(meta);
      if (m.note) li.append(el("div", "cv-note", m.note));
      if (m.step === "held" && m.code === RESTORED) {
        const b = el("button", "cv-retry cv-confirm", "이 말 보내기");
        b.type = "button";
        b.addEventListener("click", (e) => {
          if (!e.isTrusted) return; // 저장소에서 읽은 말은 사람의 신뢰 클릭으로만(자동 제출 0)
          void act.confirmRestored(m.id);
        });
        li.append(b);
      }
      if (canRetry(m)) {
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
    const masterBubble = (text: string): HTMLLIElement => {
      const li = el("li", "cv-msg cv-master");
      li.append(el("div", "cv-who", "마스터"), el("div", "cv-text", text));
      return li;
    };

    let lastRev = -1;
    const paint = (s: ChatState) => {
      if (s.rev === lastRev) return;
      lastRev = s.rev;
      health.textContent = HEALTH_LABEL[s.health];
      health.dataset.health = s.health;
      confirms.textContent = s.confirms === null ? "확인할 것 살펴보는 중" : `확인이 필요해요 ${s.confirms}`;
      confirms.dataset.count = s.confirms === null ? "" : String(s.confirms);
      const ec = errorCount(s);
      errors.textContent = ec > 0 ? `문제 ${ec}` : "문제 없음";
      errors.dataset.count = String(ec);
      const st = lastSendStep(s);
      live.textContent = st ? `마지막 보낸 말: ${STEP_LABEL[st]}` : "아직 보낸 말 없음";
      live.dataset.step = st ?? "";
      notice.textContent = s.notice ?? "";
      const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 4;
      log.replaceChildren();
      if (s.msgs.length === 0 && s.stray.length === 0) log.append(empty);
      for (const m of s.msgs) {
        log.append(bubble(m));
        for (const r of m.replies) log.append(masterBubble(r.text));
      }
      for (const r of s.stray) log.append(masterBubble(r.text));
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
        root.remove();
      },
      snapshot: () => ({ scrollTop: log.scrollTop }),
      restore: (s: unknown) => {
        const t = (s as { scrollTop?: unknown } | null)?.scrollTop;
        if (typeof t === "number") log.scrollTop = t;
      },
    };
  },
};
