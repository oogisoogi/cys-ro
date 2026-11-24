// (cysr-ui-slice1) 화면 목록 · 고르기 · 전환(직렬) · 띄우기 실패 물러남 — P2-DESIGN §4-1·§4-2.
//
// - 전환 단추는 화면이 그리지 않는다 — registry 가 #view-switch 에 하나 그린다(새 화면이 단추를 빠뜨려 사람이 갇히는 일 0).
// - 전환은 한 줄로 세운다: 진행 중이면 마지막 요청 하나만 남긴다(100ms 간격 20회 → 마지막 화면 1개).
// - 새 화면 mount 가 **성공한 뒤** 옛 화면을 내린다. 실패하면 작업 화면으로 물러나고 띠 1줄(FR-V7) · 같은 실행 3회 실패면 그 실행 동안 단추 흐림.
// - 화면의 구독·타이머는 registry 가 소유한다 → 내릴 때 강제 해제(누수 0 시험 = registry.test.ts).
// - 고른 화면은 **사람이 단추를 눌렀을 때만** `cys-view` 에 기억한다(시작 판정은 쓰기 0 — 작업 화면 동작 변화 0).

import type { Avail, ViewContext, ViewDescriptor, ViewInstance } from "./contract";
import { storedViewText, VIEW_KEY } from "./judge/viewpick";
import type { Store } from "./core";

export const FAIL_LIMIT = 3;
export const FALLBACK_BAND = "대화 화면에 문제가 있어 작업 화면으로 바꿨어요.";

export interface RegistryEnv<S, A> {
  /** 화면 주인 자리(#view-host) */
  host: HTMLElement;
  /** 공통 상태 구독(core.subscribe) */
  subscribe(fn: (s: S) => void): () => void;
  act: A;
  store: Store;
  setInterval(fn: () => void, ms: number): unknown;
  clearInterval(h: unknown): void;
  /** 단추·띠를 다시 그림(전환·실패·가용 판정 뒤) — DOM 은 index.ts 가 그린다 */
  paint(): void;
  /** 화면이 바뀌었음(공통층이 읽기 시작/멈춤 등) */
  onShown?(id: string): void;
}

interface Live {
  id: string;
  inst: ViewInstance;
  unsubs: Array<() => void>;
  timers: unknown[];
}

export class Registry<S, A> {
  private live: Live | null = null;
  private chain: Promise<void> = Promise.resolve();
  private wanted: string | null = null;
  private running = false;
  private fails = new Map<string, number>();
  private snapshots = new Map<string, unknown>();
  /** 화면별 「쓸 수 없음」 까닭(가용 판정 뒤) */
  readonly unavailable = new Map<string, string>();
  band: string | null = null;

  constructor(readonly views: ReadonlyArray<ViewDescriptor<S, A>>, private readonly env: RegistryEnv<S, A>) {}

  get current(): string | null {
    return this.live?.id ?? null;
  }

  ids(): string[] {
    return [...this.views].sort((a, b) => a.order - b.order).map((v) => v.id);
  }

  disabled(id: string): boolean {
    return (this.fails.get(id) ?? 0) >= FAIL_LIMIT || this.unavailable.has(id);
  }

  /** 지금 화면의 구독·타이머 수(누수 계수기 · 시험용) */
  liveCounts(): { subs: number; timers: number } {
    return { subs: this.live?.unsubs.length ?? 0, timers: this.live?.timers.length ?? 0 };
  }

  /** 시작 — 저장 판정으로 고른 화면을 띄운다(기억 쓰기 0). */
  start(id: string): Promise<void> {
    return this.request(id, false);
  }

  /** 사람이 단추를 누름 — 가용 판정 뒤 전환 + 기억. */
  async choose(id: string): Promise<void> {
    if (id === this.live?.id) return;
    const v = this.views.find((x) => x.id === id);
    if (!v || (this.fails.get(id) ?? 0) >= FAIL_LIMIT) return;
    let a: Avail;
    try {
      a = await v.available();
    } catch {
      a = { ok: true }; // 판정 예외 = 모름 → 흐리지 않는다(§9-3 긍정 신호만)
    }
    if (!a.ok) {
      this.unavailable.set(id, a.why);
      this.env.paint();
      return;
    }
    this.unavailable.delete(id);
    return this.request(id, true);
  }

  private request(id: string, remember: boolean): Promise<void> {
    this.wanted = id;
    if (remember) {
      try {
        this.env.store.set(VIEW_KEY, storedViewText(id));
      } catch {
        /* 기억 실패는 전환을 막지 않는다 */
      }
    }
    if (this.running) return this.chain;
    this.running = true;
    this.chain = (async () => {
      try {
        while (this.wanted !== null && this.wanted !== this.live?.id) {
          const next = this.wanted;
          await this.switchTo(next);
          if (this.wanted === next) break;
        }
      } finally {
        this.running = false;
      }
    })();
    return this.chain;
  }

  private fallbackId(): string {
    return this.ids().includes("work") ? "work" : this.ids()[0];
  }

  private async switchTo(id: string): Promise<void> {
    const v = this.views.find((x) => x.id === id);
    if (!v) return;
    const unsubs: Array<() => void> = [];
    const timers: unknown[] = [];
    let mounted: Live | null = null;
    try {
      const mod = await v.load();
      const ctx: ViewContext<S, A> = {
        subscribe: (fn) => {
          const off = this.env.subscribe((s) => {
            try {
              fn(s);
            } catch {
              this.fail(id); // 그리기 중 예외 = 띄우기 실패와 같은 물러남
            }
          });
          unsubs.push(off);
          return off;
        },
        act: this.env.act,
        timers: {
          every: (ms, fn) => {
            timers.push(
              this.env.setInterval(() => {
                try {
                  fn();
                } catch {
                  this.fail(id);
                }
              }, ms),
            );
          },
        },
      };
      const inst = mod.mount(this.env.host, ctx);
      mounted = { id, inst, unsubs, timers };
      const snap = this.snapshots.get(id);
      if (snap !== undefined && inst.restore) inst.restore(snap);
    } catch {
      for (const off of unsubs) off();
      for (const h of timers) this.env.clearInterval(h);
      this.bumpFail(id);
      if (id !== this.fallbackId()) {
        this.wanted = this.fallbackId();
        this.band = FALLBACK_BAND;
      }
      this.env.paint();
      return;
    }
    this.unmountLive(); // 새 화면이 선 뒤에 옛 화면을 내린다(같은 프레임 · 두 화면 동시 노출 0)
    this.live = mounted;
    if (typeof document !== "undefined") document.body.classList.toggle("view-chat", id === "chat"); // (TICKET=cysr-1119-s5 · V2) 대화 화면일 때 상단바를 대화 바탕에(views.css body.view-chat)
    if (id !== this.fallbackId()) this.band = null;
    this.env.onShown?.(id);
    this.env.paint();
  }

  private unmountLive(): void {
    const old = this.live;
    if (!old) return;
    try {
      if (old.inst.snapshot) this.snapshots.set(old.id, old.inst.snapshot());
    } catch {
      /* 보기 상태 저장 실패는 무시 */
    }
    for (const off of old.unsubs) off();
    for (const h of old.timers) this.env.clearInterval(h);
    old.unsubs.length = 0;
    old.timers.length = 0;
    try {
      old.inst.unmount();
    } catch {
      /* 내리기 예외도 자원은 이미 해제 */
    }
    this.live = null;
  }

  private bumpFail(id: string): void {
    this.fails.set(id, (this.fails.get(id) ?? 0) + 1);
  }

  /** 띄운 뒤 예외 — 그 화면을 내리고 작업 화면으로 물러남. */
  private fail(id: string): void {
    if (this.live?.id !== id || id === this.fallbackId()) return;
    this.bumpFail(id);
    this.band = FALLBACK_BAND;
    void this.request(this.fallbackId(), false);
  }
}
