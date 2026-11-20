// (cysr-ui-slice1) 대화 화면 1호 — 그리기만(판정은 judge/ · 행동은 ctx.act). P2-DESIGN §11 조각 1 최소판.
//
// 글은 전부 textContent 로만 넣는다(사람·마스터 글에 HTML 해석 0). 입력칸은 다시 그리지 않는다(포커스·한글 조합 보존 · §9-2).
// 최소 계약 4칸 = [data-min=confirms|lastSendStep|masterHealth|errors] · 화면 바꾸기는 공통 자리(#view-switch).

import type { ViewContext, ViewInstance, ViewModule } from "../contract";
import { DUP, dupPending, errorCount, HEALTH_LABEL, lastSendStep, logOrder, needsClick, POLL_MS, SAME_DELIVERED_NOTE, sameTextDelivered, type ChatCore, type ChatState } from "../core";
import { canRetry, STEP_LABEL, type Msg } from "../judge/msgstep";
import { AUTO_STEP_LABEL, type AutoMsg } from "../judge/autostep";
import { createBand } from "./band";
import { createResults } from "./results"; // (s79 조각 7) 결과 받기 칸·카드

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

    // (조각 4) 확인 대기 띠 = 화면 맨 위 · 「답하는 물음」 줄 = 입력칸 바로 위
    const band = createBand(act, { log, input });
    root.append(band.el, head, log, live, band.hint, form, notice);
    host.append(root);
    // (s79 조각 7) 「결과 N」 칸 — rail 틀(조각 6)이 들어오면 그 왼쪽 칸으로 옮긴다(통합 때 master 조정) · 지금은 대화 위
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

    const bubble = (m: Msg, s: ChatState): HTMLLIElement => {
      const li = el("li", `cv-msg cv-me step-${m.step}`);
      li.dataset.msgId = m.id;
      li.append(el("div", "cv-text", m.text));
      const meta = el("div", "cv-step", STEP_LABEL[m.step]);
      meta.dataset.step = m.step;
      li.append(meta);
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
    const masterBubble = (text: string, uuid: string | null = null): HTMLLIElement => {
      const li = el("li", "cv-msg cv-master");
      if (uuid) li.dataset.uuid = uuid; // (조각 4) 「대화에서 답하기」가 그 물음 자리를 찾는 표지
      li.append(el("div", "cv-who", "마스터"), el("div", "cv-text", text));
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
      for (const it of logOrder(s.msgs, s.stray)) {
        if (it.kind === "stray") {
          log.append(masterBubble(it.r.text, it.r.uuid));
          continue;
        }
        log.append(bubble(it.m, s));
        for (const r of it.m.replies) log.append(masterBubble(r.text, r.uuid));
      }
      for (const a of s.autos) log.append(autoLine(a));
      band.paint(); // (조각 4) 말 목록을 다시 그린 뒤 — 답하는 물음 자리 표시를 다시 단다
      results.paint(); // (s79 조각 7) 결과 칸 + 대화 안 카드(그 경로를 말한 마스터 답 뒤)
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
