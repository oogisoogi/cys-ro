// (cysr-ui-slice1) 대화 화면 1호 — 그리기만(판정은 judge/ · 행동은 ctx.act). P2-DESIGN §11 조각 1 최소판.
//
// 글은 전부 textContent 로만 넣는다(사람·마스터 글에 HTML 해석 0). 입력칸은 다시 그리지 않는다(포커스·한글 조합 보존 · §9-2).
// 최소 계약 4칸 = [data-min=confirms|lastSendStep|masterHealth|errors] · 화면 바꾸기는 공통 자리(#view-switch).

import type { ViewContext, ViewInstance, ViewModule } from "../contract";
import { DUP, dupPending, errorCount, FAST_POLL_MS, HEALTH_LABEL, lastSendStep, logOrder, needsClick, SAME_DELIVERED_NOTE, sameTextDelivered, type ChatCore, type ChatState } from "../core";
import { canRetry, HELD_CLICK_LABEL, STEP_LABEL, type Msg } from "../judge/msgstep";
import { AUTO_STEP_LABEL, type AutoMsg } from "../judge/autostep";
import { liveMsg, progressLine, stepTime } from "../judge/progress";
import { jumpLabel, newKeys, placeAfterPaint, stickToBottom } from "../judge/scroll";
import { createBand } from "./band";
import { applyExample, createEmpty } from "./empty";
import { createResults } from "./results"; // (s79 조각 7) 결과 받기 칸·카드
import { createReviveBand } from "./reviveband";
import { createRail, guideCard, isWindowsUa, quickReplies } from "./rail";
import { MD_RENDER, mdKeeper } from "./md"; // (TICKET=cysr-1119-s6 · V1) 마스터 답 = 안전한 마크다운(createElement+textContent · innerHTML 0)
import { createPeekPanel } from "./peek"; // (TICKET=cysr-1119-s12 · CV-PEEK) 워커 창 보기 칸
import { chipName } from "../judge/dropfiles"; // (TICKET=cysr-1119-s11 · TC3) 끌어 놓은 파일 칩

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
    // (TICKET=cysr-1118u-chat ①) 계정 한도 줄 — 작업 화면 상황판과 같은 값(act.limits · 새 조회 0) · 없으면 숨김.
    //   (TICKET=cysr-1119-s5 · V3) 자리 = 넓은 창 왼쪽 칸(rail) 아래 · 600px 이하(rail 숨김) = 머리 자리(같은 요소를 옮겨 붙임 · 1.1.18 의 좁은 창 보임 유지 · master#ef0385eb)
    const limits = el("div", "cv-limits");
    limits.setAttribute("aria-label", "토큰 사용 한도");
    limits.hidden = true;
    head.append(health, confirms, errors, guideBtn);

    const log = el("ol", "cv-log");
    log.setAttribute("aria-label", "대화");

    const live = el("div", "cv-live");
    live.setAttribute("aria-live", "polite");
    live.dataset.min = "lastSendStep";

    // (TICKET=cysr-1119-s5 · V5) 입력칸 = 한 장의 카드 — 한 줄에서 시작해 8줄까지 자람(그 뒤 칸 안 스크롤) · 안내는 아래 줄 · 둥근 보내기(빈 칸 = 꺼짐)
    const form = el("form", "cv-form");
    const input = el("textarea", "cv-input");
    input.rows = 1;
    input.placeholder = "마스터에게 보낼 말";
    input.setAttribute("aria-label", "마스터에게 보낼 말");
    input.value = act.state.draft;
    const sendBtn = el("button", "cv-send", "↑");
    sendBtn.type = "submit";
    sendBtn.setAttribute("aria-label", "보내기");
    sendBtn.title = "보내기";
    const foot = el("div", "cv-form-foot");
    foot.append(el("div", "cv-hint", "Enter 보내기 · Shift+Enter 줄바꿈"), sendBtn);
    const notice = el("div", "cv-notice");
    notice.setAttribute("role", "status");
    // (TICKET=cysr-1119-s11 · TC3) 끌어 놓은 파일 칩 줄 = 입력칸 카드 맨 위(받는 자리 = main.ts 전역 drag-drop · 이 화면은 그리기·빼기만) · 칩 없으면 숨김
    const chips = el("div", "cv-chips");
    chips.setAttribute("role", "group");
    chips.setAttribute("aria-label", "붙인 파일");
    chips.hidden = true;
    let chipSig = "";
    const paintChips = (files: readonly string[]) => {
      const sig = JSON.stringify(files);
      if (sig === chipSig) return; // 같으면 다시 그리지 않음(누름·포커스 보존)
      chipSig = sig;
      chips.replaceChildren(
        ...files.map((f) => {
          const chip = el("span", "cv-chip");
          const name = chipName(f);
          const label = el("span", "cv-chip-name", name);
          label.title = f;
          const x = el("button", "cv-chip-x", "×");
          x.type = "button";
          x.setAttribute("aria-label", `${name} 빼기`);
          x.title = `${name} 빼기`;
          x.addEventListener("click", () => {
            act.removeFile(f);
            input.focus();
          });
          chip.append(label, x);
          return chip;
        }),
      );
      chips.hidden = files.length === 0;
    };
    form.append(chips, input, foot);
    // 자동 높이: CSS field-sizing 이 없으면(웹뷰 판에 따라) 글 높이를 8줄 상한으로 직접 맞춘다
    const sizing = typeof CSS !== "undefined" && typeof CSS.supports === "function" && CSS.supports("field-sizing", "content");
    const fitInput = () => {
      if (sizing) return;
      input.style.height = "auto";
      const lh = parseFloat(getComputedStyle(input).lineHeight) || 30;
      input.style.height = `${Math.min(input.scrollHeight, Math.ceil(lh * 8))}px`;
    };
    const syncSend = () => {
      sendBtn.disabled = input.value.trim() === "" && act.state.files.length === 0; // (TC3) 칩만 있어도 보냄
      fitInput();
    };
    // (TICKET=cysr-1119-s5 · CV-EX3) 빈 화면 = 제목 · 안내 · 예시 3(누르면 입력칸에만 · 보내지 않음 · 쓰던 글은 그대로)
    const empty = createEmpty((ex) => {
      if (applyExample(input, act, ex)) syncSend();
    });
    // (TICKET=cysr-1119-s5 · V6) 위를 읽는 중 새 답 = 끌어내리지 않고 단추로 알림
    const jump = el("button", "cv-jump");
    jump.type = "button";
    jump.hidden = true;

    // (조각 4) 확인 대기 띠 = 화면 맨 위 · 「답하는 물음」 줄 = 입력칸 바로 위
    const band = createBand(act, { log, input });
    // (조각 5) 마스터 멈춤·깨우기·다시 켜기 띠 = 맨 위(확인 대기 띠 위)
    const revive = createReviveBand(act);
    // (TICKET=cysr-1119-s5 · CV-RAIL ⑤) 600px 이하(rail 숨김) = 가운데 칸 위 「결과 N」 한 줄 단추 → rail 을 덮개로 띄움(가운데 스크롤 상자는 여전히 하나)
    const narrowRes = el("button", "cv-res-narrow");
    narrowRes.type = "button";
    narrowRes.hidden = true;
    narrowRes.setAttribute("aria-expanded", "false");
    root.append(revive.el, band.el, head, narrowRes, log, jump, live, band.hint, form, notice);
    // (조각 6) 왼쪽 메뉴바(맡긴 일·팀·부서·결과 자리) + 가운데 대화 — 한 줄로(시안 rail)
    const wrap = el("div", "cv-wrap");
    // (TICKET=cysr-1119-s12 · CV-PEEK ②) 보기 칸 = 대화 칸 오른쪽(넓은 창) · 대화 칸 위 덮개(≤1300px) — 카드 누름은 rail 이 · 터미널은 main.ts(act.peek)
    const peekPanel = createPeekPanel(act.peek, wrap, () => {
      if (railArgs) rail.paint(...railArgs);
    });
    let railArgs: Parameters<typeof rail.paint> | null = null;
    const rail = createRail(act.peek ? { pick: (h) => peekPanel.open(h), openSid: () => peekPanel.sid() } : undefined);
    wrap.append(rail.el, root, peekPanel.el);
    host.append(wrap);
    const win = isWindowsUa(typeof navigator === "undefined" ? "" : navigator.userAgent);
    // (s79 조각 7 · TICKET=cysr-1119-s5 CV-RAIL ①) 「결과 N」 칸 = 왼쪽 칸(rail) 결과 자리 — 가운데 칸 스크롤 상자 = 대화 목록 하나
    const results = createResults(act, { log, input, changed: syncSend });
    rail.results.append(results.el);
    const setOverlay = (on: boolean) => {
      wrap.classList.toggle("rail-open", on);
      narrowRes.setAttribute("aria-expanded", String(on));
      if (on) results.setOpen(true);
    };
    narrowRes.addEventListener("click", () => setOverlay(!wrap.classList.contains("rail-open")));
    // 덮개는 「결과 N」 단추 자리를 가린다 → 가운데 칸 누름 · Esc 로 닫음
    const onRootClick = (e: MouseEvent) => {
      if (wrap.classList.contains("rail-open") && !narrowRes.contains(e.target as Node)) setOverlay(false);
    };
    const onWrapKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && wrap.classList.contains("rail-open")) setOverlay(false);
    };
    root.addEventListener("click", onRootClick);
    wrap.addEventListener("keydown", onWrapKey);
    // (V3) 한도 줄 자리 — 창 폭이 600px 선을 넘나들면 옮겨 붙임
    const narrowMq = typeof matchMedia === "function" ? matchMedia("(max-width: 600px)") : null;
    const placeLimits = () => {
      if (narrowMq?.matches) head.insertBefore(limits, guideBtn);
      else rail.foot.append(limits);
    };
    placeLimits();
    narrowMq?.addEventListener("change", placeLimits);

    // (V6) 스크롤 상태 — 본 마스터 답 열쇠 · 못 본 새 답 수 · 사람이 보낸 직후 맨 아래
    const seenReplies = new Set<string>();
    let firstPaint = true;
    let unread = 0;
    let forceBottom = false;
    const paintJump = () => {
      const t = jumpLabel(unread);
      jump.hidden = t === null;
      jump.textContent = t ?? "";
    };
    const toBottom = () => {
      log.scrollTop = log.scrollHeight;
      unread = 0;
      paintJump();
    };
    jump.addEventListener("click", toBottom);
    const onScroll = () => {
      if (unread > 0 && stickToBottom(log)) {
        unread = 0;
        paintJump();
      }
    };
    log.addEventListener("scroll", onScroll);

    const submit = () => {
      const text = input.value;
      if (!text.trim() && act.state.files.length === 0) return;
      forceBottom = true; // 사람이 보내면 맨 아래(받아들인 말만 · 아래에서 되돌림)
      if (act.submitInput(text, win)) { // (TC3) 칩이 있으면 core 가 글 끝에 @경로를 펼쳐 보내고 비움(빠른 답 = act.submit · 칩 무관)
        input.value = ""; // 받아들인 말만 비운다 — 막힌 말(`/clear` 등)은 고칠 수 있게 남긴다
        act.setDraft("");
        toBottom();
      } else forceBottom = false;
      syncSend();
      input.focus();
    };
    const onInput = () => {
      act.setDraft(input.value);
      syncSend();
    };
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
      const p = progressLine(m, Date.now(), live, { summary: !act.compat1118 }); // (TICKET=cysr-1119-integ1 · S4 HANDOFF ⑴ × S2 CH-E) 되돌리기 켜면 D = 요약 숨김
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
        const p = m ? progressLine(m, Date.now(), true, { summary: !act.compat1118 }) : null; // (integ1 · S4 ⑴ × S2 CH-E) 같은 값
        const txt = t.querySelector(".cv-prog-text");
        if (p && txt && txt.textContent !== p.text) txt.textContent = p.text;
      }
    });

    const bubble = (m: Msg, s: ChatState, live: boolean): HTMLLIElement => {
      const li = el("li", `cv-msg cv-me step-${m.step}`);
      li.dataset.msgId = m.id;
      li.append(el("div", "cv-text", m.text));
      const meta = el("div", "cv-step", needsClick(m) ? HELD_CLICK_LABEL : STEP_LABEL[m.step]); // (K-1) 눌러야 나갈 말 = 「아직 안 보냄」
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
      // (TICKET=cysr-1121-ui K-2 · master 10:2x) 붙잡은 말(자동으로 나갈 말 · 눌러야 나갈 말 모두)은 사람이 언제든 거둘 수 있다 — 10분 상한을 좁힌 짝(쓰기 0).
      if (m.step === "held") {
        const d = el("button", "cv-retry cv-discard", "보내지 않기");
        d.type = "button";
        d.addEventListener("click", (e) => {
          if (!e.isTrusted) return; // 사람의 신뢰 클릭만
          act.discardHeld(m.id);
        });
        li.append(d);
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
    // (fix-1119-s6-adv M3) 답 글이 그대로면 다시 그리지 않음 + 가로 스크롤 자리 되돌림(장치 = chat/md.ts mdKeeper · 단위 시험 = chatmd.test).
    const mdKept = mdKeeper();
    const masterBubble = (text: string, uuid: string | null, key: string, last = false): HTMLLIElement => {
      const li = el("li", MD_RENDER ? "cv-msg cv-master cv-mdmsg" : "cv-msg cv-master"); // (V1) cv-mdmsg = 풍선 없는 본문(CSS 가 이 표지에만 걸림 → 끄면 지금 꼴)
      if (uuid) li.dataset.uuid = uuid; // (조각 4) 「대화에서 답하기」가 그 물음 자리를 찾는 표지
      li.dataset.replyKey = key; // (V6) 새 답 셈 열쇠
      li.append(el("div", "cv-who", "마스터"), MD_RENDER ? mdKept.node(key, text) : el("div", "cv-text", text));
      // (조각 6 · §5-4 D7) ⟪팀 제안⟫·⟪부서 제안: 팀⟫ = 마지막 말일 때만 빠른 답 2개(누르면 그 글 그대로 보냄)
      if (last) {
        const q = quickReplies(text, (t) => {
          forceBottom = true;
          if (act.submit(t)) {
            toBottom();
            input.focus();
          } else forceBottom = false;
        });
        if (q) li.append(q);
      }
      return li;
    };

    // (TICKET=cysr-1118u-chat ①) 한도 줄 — 값이 바뀔 때만 다시 그린다(원천 = 작업 화면 15초 캐시 · 여기서는 5초마다 들여다봄 · 조회 0).
    let limitSig = "";
    const paintLimits = () => {
      const rows = act.limits();
      const sig = JSON.stringify(rows);
      if (sig === limitSig) return;
      limitSig = sig;
      limits.replaceChildren();
      limits.hidden = rows.length === 0;
      for (const r of rows) {
        const row = el("span", `cv-limit${r.stale ? " stale" : r.pct >= 80 ? " crit" : r.pct >= 60 ? " warn" : ""}`); // (J) 오래된 값 = 경고색 없이 흐리게
        row.title = r.title;
        row.append(el("span", "cv-limit-name", r.name ?? "7일 한도"), el("span", "cv-limit-text", r.line));
        // (V3) 6px 막대(왼쪽 칸에서만 보임 · 글 없음 = 글 대조 불변)
        const bar = el("span", "cv-limit-bar");
        bar.setAttribute("aria-hidden", "true");
        const fill = el("i");
        fill.style.width = `${Math.max(0, Math.min(100, Number.isFinite(r.pct) ? r.pct : 0))}%`;
        bar.append(fill);
        row.append(bar);
        limits.append(row);
      }
    };
    paintLimits();
    ctx.timers.every(5_000, paintLimits);

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
      const prevTop = log.scrollTop;
      mdKept.beforeClear();
      const stuck = forceBottom || stickToBottom(log); // (V6) 48px 문턱(1.1.18 = 4px)
      forceBottom = false;
      log.replaceChildren();
      if (s.msgs.length === 0 && s.stray.length === 0 && s.autos.length === 0) log.append(empty);
      // (조각 3 고침 · 검증 지적 B) 어느 말에도 안 묶인 마스터 글은 시각순으로 사람 말 사이에 끼운다(사람 말들 뒤에 몰리지 않게).
      const order = logOrder(s.msgs, s.stray);
      const lastItem = order[order.length - 1];
      const liveM = liveMsg(s.msgs); // (TICKET=cysr-1118-ui ①) 진행 줄을 살아 있게 다는 말(가장 최근 · 답 기다림)
      for (const id of [...openProg]) if (!s.msgs.some((m) => m.id === id)) openProg.delete(id); // (codex 1R minor) 밀려난 말의 펼침 상태는 버린다(보관량 = 지금 말 수 이하)
      for (const it of order) {
        if (it.kind === "stray") {
          log.append(masterBubble(it.r.text, it.r.uuid, it.r.uuid ?? `s:${it.r.text}`, it === lastItem));
          continue;
        }
        log.append(bubble(it.m, s, it.m === liveM));
        it.m.replies.forEach((r, k) => log.append(masterBubble(r.text, r.uuid, r.uuid ?? `m:${it.m.id}:${k}`, it === lastItem && k === it.m.replies.length - 1)));
      }
      for (const a of s.autos) log.append(autoLine(a));
      mdKept.afterFill();
      // (조각 6 · §16-6) 처음 부서가 생기면 한 번 · 「부서 안내」로 다시 보기
      if (act.rail.guide) log.append(guideCard(act.rail.guide, win, { ack: () => act.rail.ackGuide(), close: () => act.rail.toggleGuide() }));
      railArgs = [s, act.rail.model];
      rail.paint(s, act.rail.model);
      peekPanel.sync(act.rail.model.blocks.flatMap((b) => b.cards).flatMap((c) => c.helpers), act.rail.model.loading); // (CV-PEEK) 머리 글·답하기 단추 · 사라진 좌석 = 닫음
      band.paint(); // (조각 4) 말 목록을 다시 그린 뒤 — 답하는 물음 자리 표시를 다시 단다
      const res = results.paint(); // (s79 조각 7) 결과 칸 + 대화 안 카드(그 경로를 말한 마스터 답 뒤)
      rail.setResults(res.count); // (CV-RAIL ⑤-1) 숨김 = 결과 수
      narrowRes.hidden = res.count === 0;
      narrowRes.textContent = res.text;
      if (res.count === 0 && wrap.classList.contains("rail-open")) setOverlay(false);
      revive.paint(); // (조각 5)
      // (V6) 위치 — 붙어 있었으면 맨 아래(긴 새 답 = 첫 줄이 위) · 아니면 그대로 + 새 답 수
      const keys = [...log.querySelectorAll<HTMLElement>(".cv-master[data-reply-key]")].map((e) => e.dataset.replyKey ?? "");
      const fresh = firstPaint ? [] : newKeys(seenReplies, keys);
      firstPaint = false;
      seenReplies.clear();
      for (const k of keys) seenReplies.add(k);
      const firstEl = fresh.length ? log.querySelector<HTMLElement>(`.cv-master[data-reply-key="${CSS.escape(fresh[0])}"]`) : null;
      let first: { top: number; height: number } | null = null;
      if (firstEl) {
        const lr = log.getBoundingClientRect();
        const fr = firstEl.getBoundingClientRect();
        first = { top: fr.top - lr.top + log.scrollTop, height: fr.height };
      }
      log.scrollTop = placeAfterPaint(stuck, prevTop, { scrollTop: log.scrollTop, clientHeight: log.clientHeight, scrollHeight: log.scrollHeight }, first);
      unread = stuck ? 0 : unread + fresh.length;
      paintJump();
      paintChips(s.files);
      syncSend();
    };
    ctx.subscribe(paint);
    paint(act.state);
    act.attach();
    void act.poll();
    ctx.timers.every(FAST_POLL_MS, () => act.pollTick()); // (TICKET=cysr-1118u-chat ②) 1초 시계 — 온전한 조회는 POLL_MS 그대로 · 붙잡은 말이 기다릴 때만 그 사이 문턱 재조회
    // 이 자리는 아직 숨겨져 있다(registry 가 옛 화면을 내리며 같은 전환 안에서 보이게 함) — 숨은 요소엔 포커스가 안 들어가므로 전환 끝에 준다.
    queueMicrotask(() => {
      if (root.isConnected) input.focus();
    });

    return {
      unmount() {
        act.peek?.close("leave"); // (TICKET=cysr-1119-s12 · C-04) 대화 화면 떠남 = 보기 칸 닫는 자리 하나
        peekPanel.destroy();
        act.detach();
        input.removeEventListener("input", onInput);
        input.removeEventListener("keydown", onKey);
        form.removeEventListener("submit", onSubmit);
        log.removeEventListener("scroll", onScroll);
        root.removeEventListener("click", onRootClick);
        wrap.removeEventListener("keydown", onWrapKey);
        narrowMq?.removeEventListener("change", placeLimits);
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
