// (cysr-ui-slice1) 화면 공통층 입구 — main.ts 는 `bootViews(...)` 한 줄만 부른다(배선만 · P2-DESIGN §3-1).
//
// 시작 화면 = 저장된 「사람이 고른 화면」(cys-view) · 없으면 작업 화면(§10 1.1.16 개정 = 새·기존 모두 작업 화면).
// ★대화 화면을 고르지 않으면: invoke 0 · 저장소 쓰기 0 · 타이머 0 — 작업 화면 동작 변화 0(tickrec_gate 대조).
//   (대화 화면 가용 판정·마스터 조회·세션 읽기는 전부 대화 화면을 누른 뒤에만 돈다.)

import type { ViewDescriptor } from "./contract";
import { ChatCore, POLL_MS, type ChatState, type Store } from "./core";
import { chatView } from "./chat/index";
import { workView, type WorkExtra } from "./work/adapter";
import { createWorkBand } from "./work/band"; // (s79 조각 9) 작업 화면 띠
import { chatAvailability, pickView, VIEW_KEY } from "./judge/viewpick";
import { chatWorking, masterRowOf } from "./judge/gate";
import { Registry } from "./registry";

export interface BootDeps {
  invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown>;
  working(row: Record<string, unknown>): boolean;
  /** (s79 조각 9) 작업 화면 띠 「마스터 창에서 답하기」 — 그 좌석으로 포커스(main.ts jumpToSurface). 없으면 띠가 안내만. */
  focusSeat?(sid: number): void;
  /** (cysr-1116-s2 · P2-DESIGN §2-3 ㉢) 작업 화면이 보이게 된 직후(전환·물러남·시작) — main.ts 가 미룬 좌석 런타임을 만든다. */
  onWorkShown?(): void;
  /** (조각 5) 도움 요청 창(main.ts 기존 피드백 창) */
  openHelp?(): void;
  /** (조각 5) 복원 진행 중(main.ts briefGate — 앱 수명 전체) */
  restoring?(): boolean;
}

const MIN_CHAT = { confirms: "[data-min=confirms]", lastSendStep: "[data-min=lastSendStep]", masterHealth: "[data-min=masterHealth]", errors: "[data-min=errors]", switcher: "shared" } as const;
const MIN_WORK = { confirms: "#cc-pending-badge", lastSendStep: "", masterHealth: "", errors: "", switcher: "shared" } as const;

const store: Store = {
  get: (k) => localStorage.getItem(k),
  set: (k, v) => localStorage.setItem(k, v),
  remove: (k) => localStorage.removeItem(k),
};

/**
 * (cysr-1116-s2 · P2-DESIGN §2-3 ㉢) 좌석 터미널 런타임(xterm·출력 흐름)을 **지금** 만들어도 되는가 = 작업 화면이 보이거나 보일 차례인가.
 * 시작 값 = 고른 화면(pickView)이 작업 화면인가(대화 화면을 고른 기기는 시작 복원부터 런타임을 미룬다 · §9-4 「대화 화면만 쓴 새 설치 = 출력 흐름 0」) ·
 * 그 뒤 = 작업 화면 어댑터의 mount/unmount 가 바꾼다. 공통층이 없는 옛 index.html(bootViews 가 null) = 늘 참(종전 그대로).
 */
let runtimeWanted = true;
export function workRuntimeWanted(): boolean {
  return runtimeWanted;
}

/** (cysr-1116-s2 · integ I3·S4-3) main.ts onDaemonEvent 머리 배선 1줄 — 공통층이 안 떴으면(옛 index.html) 아무것도 안 함. */
export function viewsIngest(ev: unknown, hqSlug: string | null): void {
  if (booted) return booted.core.ingest(ev, hqSlug);
  // (codex 1R major) 공통층이 서기 전(앱 시작 ~ bootViews)에 온 사건은 상한 32 로 모았다가 bootViews 직후 한 번 흘린다(가장 오래된 것부터 버림).
  preBoot.push([ev, hqSlug]);
  if (preBoot.length > PRE_BOOT_MAX) preBoot.shift();
}
const PRE_BOOT_MAX = 32;
const preBoot: [unknown, string | null][] = [];

/** 이미 돈 적 있으면 같은 것을 돌려준다(시작 경로가 두 번 불려도 단추·고리 한 벌). */
let booted: { core: ChatCore; registry: Registry<ChatState, ChatCore> } | null = null;

export function bootViews(deps: BootDeps): { core: ChatCore; registry: Registry<ChatState, ChatCore> } | null {
  if (booted) return booted;
  const switchHost = document.getElementById("view-switch");
  const host = document.getElementById("view-host");
  const bodyRow = document.getElementById("body-row");
  if (!switchHost || !host || !bodyRow) return null; // 자리가 없는 옛 index.html — 작업 화면 그대로
  const core = new ChatCore({
    invoke: deps.invoke,
    now: () => Date.now(),
    setTimeout: (fn, ms) => setTimeout(fn, ms),
    clearTimeout: (h) => clearTimeout(h as ReturnType<typeof setTimeout>),
    store,
    working: deps.working,
    chatWorking: (r) => chatWorking(r, deps.working), // (TICKET=cysr-chat-held-win) 대화 화면 문턱만 — 작업 화면·메뉴바·되살리기 판정은 deps.working 그대로
    // (cysr-1116-s2 · integ I3·S4-3) 데몬 사건은 main.ts 의 하나뿐인 daemon-event 구독이 viewsIngest(아래) 로 넘긴다 —
    //   종전 조각 3 `listen` · 조각 4 `listenDaemon` 두 구독과 `defaultSlug`(default_socket_slug 재조회)는 걷었다(구독 1 · 조회 0 · 대화 화면이 꺼진 동안 온 사건도 장부가 받음).
    goView: (id) => void booted?.registry.choose(id),
    // (s5 조각 5) 앱 사건(boot-degraded · restore-progress) — daemon-event 가 아니다(그것은 위 viewsIngest 단일 입구).
    //   ★통합(cysr-1116-integ-1120): s5 의 defaultSlug(default_socket_slug 재조회)는 s2 뜻대로 걷었다 — 본부 slug 는 ingest 가 넣는다.
    listenApp: (name, handler) => (window as unknown as { __TAURI__: { event: { listen(n: string, h: (e: { payload: unknown }) => void): Promise<() => void> } } }).__TAURI__.event.listen(name, handler),
    focusSeat: (sid) => deps.focusSeat?.(sid),
    openHelp: () => deps.openHelp?.(),
    restoring: () => deps.restoring?.() === true,
    workHint: (text) => paintWorkHint(switchHost, text, () => void booted?.registry.choose("chat")),
  });
  // (s79 조각 9 · FR-C7) 작업 화면이 켜져 있는 동안만 붙는 띠 — 대화 화면을 이번 실행에서 켠 적이 없으면 조회 0·띠 0(watchStart = false).
  const workExtra: WorkExtra<ChatState, ChatCore> = {
    mount(ctx) {
      const band = createWorkBand(ctx.act, { focusSeat: deps.focusSeat });
      bodyRow.before(band.el);
      ctx.subscribe(() => band.paint());
      band.paint();
      if (ctx.act.watchStart()) {
        void ctx.act.poll();
        ctx.timers.every(POLL_MS, () => void ctx.act.poll());
      }
      return () => {
        ctx.act.watchStop();
        band.el.remove();
      };
    },
  };
  // 작업 화면이 **숨김 → 보임**으로 바뀔 때만 main.ts 를 부른다(작업 화면으로 시작하는 기동은 처음부터 참이라 부르지 않는다 = 종전 흐름 그대로 ·
  //   대화 화면에 있던 동안 건너뛴 그리기와 미룬 런타임을 여기서 한 번에).
  const workShown = () => {
    const was = runtimeWanted;
    runtimeWanted = true;
    if (was) return;
    try {
      deps.onWorkShown?.();
    } catch {
      /* 런타임 만들기 실패는 그리기에서 끝난다 — 전환은 그대로 */
    }
  };
  const views: ViewDescriptor<ChatState, ChatCore>[] = [
    {
      id: "chat",
      label: "대화 화면",
      order: 1,
      minimum: MIN_CHAT,
      available: async () => {
        // §9-3 긍정 신호만: 이름 보고자 「마스터」 최근 ∧ 살아 있는 cys 마스터 좌석 없음 → 불가. 조회 실패 = 가능.
        const [named, org] = await Promise.all([
          deps.invoke("usage_named_reporters").catch(() => null),
          deps.invoke("org_status", { socket: null }).catch(() => undefined),
        ]);
        const m = org === undefined ? undefined : masterRowOf(org, deps.working);
        const liveCysMaster = m === undefined ? null : m !== null && m.agent_alive === true;
        return chatAvailability((named as { named?: unknown } | null)?.named ?? null, liveCysMaster, Date.now() / 1000);
      },
      load: async () => chatView,
    },
    { id: "work", label: "작업 화면", order: 2, minimum: MIN_WORK, available: async () => ({ ok: true }), load: async () => workView<ChatState, ChatCore>(bodyRow, host, { ...workExtra, shown: workShown, hidden: () => void (runtimeWanted = false) }), outsideHost: true },
  ];
  const registry: Registry<ChatState, ChatCore> = new Registry<ChatState, ChatCore>(views, {
    host,
    subscribe: (fn) => core.subscribe(fn),
    act: core,
    store,
    setInterval: (fn, ms) => setInterval(fn, ms),
    clearInterval: (h) => clearInterval(h as ReturnType<typeof setInterval>),
    paint: () => paintSwitch(switchHost, registry),
    // 자리 표시는 「켜진 화면」 하나로 정한다(VERIFY 지적 2): 시작 때 저장된 화면이 대화 화면이면 작업 화면이 한 번도 뜨지 않아
    //   작업 화면 어댑터의 내리기(자리 풀기)가 불리지 않았다 → 대화 화면이 숨은 자리 안에 떠서 조회만 돌았다. 작업 화면 밖 화면이
    //   켜지면 여기서 자리를 보이고 작업 화면을 숨긴다(작업 화면 자신은 어댑터가 반대로 한다 · 같은 전환 안 · 두 화면 동시 노출 0).
    onShown: (id) => {
      if (id === "work") return;
      host.hidden = false;
      bodyRow.style.display = "none";
    },
  });
  let raw: string | null = null;
  try {
    raw = localStorage.getItem(VIEW_KEY);
  } catch {
    raw = null;
  }
  const first = pickView(raw, registry.ids());
  runtimeWanted = first === "work"; // 대화 화면이 시작 화면이면 시작 복원부터 런타임을 미룬다(작업 화면이 뜨면 mount 가 참으로)
  booted = { core, registry };
  for (const [ev, slug] of preBoot.splice(0)) core.ingest(ev, slug); // 시작 구간 사건(위 viewsIngest) — 한 번만
  paintSwitch(switchHost, registry);
  void registry.start(first);
  return booted;
}

/** (조각 5 · §6-3) 작업 화면 위 관문 안내 1줄 + 「대화 화면으로」 · 닫기. text=null 이면 숨김. 대화 화면으로 가면 닫힌다. textContent 만. */
function paintWorkHint(host: HTMLElement, text: string | null, backToChat: () => void): void {
  let h = host.querySelector<HTMLElement>(".vs-hint");
  if (!h) {
    h = document.createElement("div");
    h.className = "vs-hint";
    h.setAttribute("role", "status");
    host.append(h);
  }
  h.replaceChildren();
  if (text === null) {
    h.hidden = true;
    return;
  }
  const t = document.createElement("span");
  t.textContent = text;
  const back = document.createElement("button");
  back.type = "button";
  back.textContent = "대화 화면으로";
  const close = document.createElement("button");
  close.type = "button";
  close.textContent = "닫기";
  const hide = () => paintWorkHint(host, null, backToChat);
  back.addEventListener("click", () => {
    hide();
    backToChat();
  });
  close.addEventListener("click", hide);
  h.append(t, back, close);
  h.hidden = false;
}

/** 전환 단추 「대화 화면 | 작업 화면」 + 띠 1줄(물러남·쓸 수 없음 까닭). textContent 만. */
function paintSwitch(host: HTMLElement, reg: Registry<ChatState, ChatCore>): void {
  let group = host.querySelector<HTMLElement>(".vs-group");
  if (!group) {
    group = document.createElement("div");
    group.className = "vs-group";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "화면 바꾸기");
    host.append(group);
  }
  const cur = reg.current;
  const btns: HTMLButtonElement[] = [];
  for (const v of [...reg.views].sort((a, b) => a.order - b.order)) {
    let b = group.querySelector<HTMLButtonElement>(`button[data-view="${v.id}"]`);
    if (!b) {
      b = document.createElement("button");
      b.type = "button";
      b.dataset.view = v.id;
      b.textContent = v.label;
      const id = v.id;
      b.addEventListener("click", () => void reg.choose(id));
    }
    b.setAttribute("aria-pressed", String(cur === v.id));
    const why = reg.unavailable.get(v.id);
    b.classList.toggle("vs-dim", reg.disabled(v.id));
    b.title = why ?? (reg.disabled(v.id) ? "이번 실행에서는 이 화면을 쓸 수 없어요" : `${v.label}으로 바꾸기`);
    btns.push(b);
  }
  group.replaceChildren(...btns);
  let band = host.querySelector<HTMLElement>(".vs-band");
  if (!band) {
    band = document.createElement("div");
    band.className = "vs-band";
    band.setAttribute("role", "status");
    host.append(band);
  }
  const reason = [...reg.unavailable.values()][0] ?? null;
  const text = reg.band ?? reason ?? "";
  band.textContent = text;
  band.hidden = text === "";
}
