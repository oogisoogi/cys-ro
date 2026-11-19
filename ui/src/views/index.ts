// (cysr-ui-slice1) 화면 공통층 입구 — main.ts 는 `bootViews(...)` 한 줄만 부른다(배선만 · P2-DESIGN §3-1).
//
// 시작 화면 = 저장된 「사람이 고른 화면」(cys-view) · 없으면 작업 화면(§10 1.1.16 개정 = 새·기존 모두 작업 화면).
// ★대화 화면을 고르지 않으면: invoke 0 · 저장소 쓰기 0 · 타이머 0 — 작업 화면 동작 변화 0(tickrec_gate 대조).
//   (대화 화면 가용 판정·마스터 조회·세션 읽기는 전부 대화 화면을 누른 뒤에만 돈다.)

import type { ViewDescriptor } from "./contract";
import { ChatCore, type ChatState, type Store } from "./core";
import { chatView } from "./chat/index";
import { workView } from "./work/adapter";
import { chatAvailability, pickView, VIEW_KEY } from "./judge/viewpick";
import { masterRowOf } from "./judge/gate";
import { Registry } from "./registry";

export interface BootDeps {
  invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown>;
  working(row: Record<string, unknown>): boolean;
}

const MIN_CHAT = { confirms: "[data-min=confirms]", lastSendStep: "[data-min=lastSendStep]", masterHealth: "[data-min=masterHealth]", errors: "[data-min=errors]", switcher: "shared" } as const;
const MIN_WORK = { confirms: "#cc-pending-badge", lastSendStep: "", masterHealth: "", errors: "", switcher: "shared" } as const;

const store: Store = {
  get: (k) => localStorage.getItem(k),
  set: (k, v) => localStorage.setItem(k, v),
  remove: (k) => localStorage.removeItem(k),
};

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
    // (조각 3) 데몬 사건 구독 — main.ts 를 건드리지 않고 같은 Tauri 전역을 쓴다(core 가 대화 화면이 켜졌을 때만 부름 · 작업 화면 invoke 0 유지).
    listen: (name, handler) => (window as unknown as { __TAURI__: { event: { listen(n: string, h: (e: { payload: unknown }) => void): Promise<() => void> } } }).__TAURI__.event.listen(name, handler),
    // (조각 4) 대화 화면이 켜져 있을 때만 core 가 부른다 — 작업 화면만 쓰면 구독 0(동작 변화 0). (통합 1116) 조각 3 listen 과 이름이 겹쳐 listenDaemon.
    listenDaemon: (fn) => {
      const ev = (window as unknown as { __TAURI__?: { event?: { listen?: (n: string, h: (e: { payload: unknown }) => void) => Promise<() => void> } } }).__TAURI__?.event;
      if (!ev?.listen) return () => {};
      let off: (() => void) | null = null;
      let dead = false;
      void ev
        .listen("daemon-event", (e) => fn(e.payload))
        .then((u) => (dead ? u() : (off = u)))
        .catch(() => {});
      return () => {
        dead = true;
        off?.();
      };
    },
    goView: (id) => void booted?.registry.choose(id),
    defaultSlug: async () => String(await deps.invoke("default_socket_slug")),
  });
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
    { id: "work", label: "작업 화면", order: 2, minimum: MIN_WORK, available: async () => ({ ok: true }), load: async () => workView<ChatState, ChatCore>(bodyRow, host), outsideHost: true },
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
  booted = { core, registry };
  paintSwitch(switchHost, registry);
  void registry.start(first);
  return booted;
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
