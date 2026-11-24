// (TICKET=verify-1119-s3 · 독립 검증 좌석 · 기록만) 재현 시험 공용 대역 — Rust 쪽 상태를 흉내 낸다(viewcore.rs:798-871 을 읽고 옮김).
//  · watch = 도착 때 세대 +1 → RPC 뒤 잠금에서 세대 대조(다르면 superseded) → 쥠 · unwatch = 세대 +1 뒤 내림 · tail = 쥔 것이 없거나 좌석이 다르면 not_watching
//  · 0.25초 박자: 쥔 watch 가 있고 파일이 길어졌으면 사건(gen·size)
//  · ★tail 은 Rust 가 명령을 집어 든 순간의 길이·레코드를 찍고(read_transcript_from 의 첫 줄 = fstat · viewcore.rs:584) 그 뒤 지연을 거쳐 화면에 닿는다.
import { ChatCore, type Deps } from "./core";

export interface WorldOpt {
  reorder: boolean;
  compat: boolean;
  /** tail 응답이 화면에 닿기까지(ms · [최소, 최대]) — 기본 [0, 6] */
  tailMs?: [number, number];
  /** unwatch 를 Rust 가 집어 들기까지(ms) — 기본 reorder 면 0~3 */
  unwatchMs?: [number, number];
  /** watch 의 데몬 RPC 2개(ms) — 기본 [1, 30] */
  watchMs?: [number, number];
}

export function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 0x100000000;
  };
}

export function world(seed: number, opt: WorldOpt) {
  const rnd = rng(seed);
  const ri = (a: number, b: number) => a + Math.floor(rnd() * (b - a + 1));
  let now = 9_000_000;
  const timers: Array<{ at: number; fn: () => void; h: number }> = [];
  let hn = 0;
  const at = (ms: number, fn: () => void) => void timers.push({ at: now + ms, fn, h: ++hn });
  const later = <T>(ms: number, v: () => T): Promise<T> => (ms <= 0 ? Promise.resolve().then(v) : new Promise((res) => at(ms, () => res(v()))));
  const file: Array<Record<string, unknown>> = [];
  const SID = "sess-0001-aaaa";
  const master = { surface_id: 5, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false, registered_session_id: SID } as Record<string, unknown>;
  // ---- Rust 대역 ----
  const rust = { latest: 0, watch: null as null | { gen: number; seat: number; len: number }, armed: 0, superseded: 0, notWatching: 0, maxTailInflight: 0, tailInflight: 0, fromEnd: 0, events: 0 };
  const app = new Map<string, Array<(e: { payload: unknown }) => void>>();
  const beat = () => {
    const w = rust.watch;
    if (w && file.length > w.len) {
      w.len = file.length;
      rust.events++;
      const payload = { surface_id: w.seat, session_id: SID, gen: w.gen, size: file.length, reset: false };
      for (const h of app.get("chat-transcript-changed") ?? []) h({ payload });
    }
    at(250, beat);
  };
  at(250, beat);
  const arrive = () => (opt.reorder ? ri(0, 3) : 0); // Tauri 비동기 명령의 처리 시작이 보낸 순서와 다를 수 있음(HANDOFF §2 ④)
  const calls: string[] = [];
  const deps: Deps = {
    invoke: async (cmd, args) => {
      calls.push(cmd);
      if (cmd === "org_status") return later(ri(0, 4), () => ({ surfaces: [{ ...master }] }));
      if (cmd === "feed_list") return later(ri(0, 4), () => ({ items: [] }));
      if (cmd === "chat_send") return later(ri(0, 30), () => ({ outcome: "written", result: { sent: true } }));
      if (cmd === "chat_transcript") {
        const a = args as { afterOffset: number; fromEnd: boolean };
        if (a.fromEnd) rust.fromEnd++;
        return later(ri(1, 30), () =>
          a.fromEnd
            ? { status: "ok", session_id: SID, next_offset: file.length, size: file.length, records: [] }
            : { status: "ok", session_id: SID, next_offset: file.length, size: file.length, records: file.slice(a.afterOffset), reset: a.afterOffset > file.length },
        );
      }
      if (cmd === "chat_transcript_watch") {
        const a = args as { surfaceId: number };
        return later(arrive(), () => ++rust.latest).then((gen) =>
          later(ri(...(opt.watchMs ?? [1, 30])), () => {
            if (rust.latest !== gen) {
              rust.superseded++;
              return { status: "unknown", why: "superseded" };
            }
            rust.watch = { gen, seat: a.surfaceId, len: file.length };
            rust.armed++;
            return { status: "ok", session_id: SID, size: file.length, gen };
          }),
        );
      }
      if (cmd === "chat_transcript_unwatch")
        return later(opt.unwatchMs ? ri(...opt.unwatchMs) : arrive(), () => {
          rust.latest++;
          const was = rust.watch !== null;
          rust.watch = null;
          return { status: "ok", was };
        });
      if (cmd === "chat_transcript_tail") {
        const a = args as { surfaceId: number; afterOffset: number };
        rust.tailInflight++;
        rust.maxTailInflight = Math.max(rust.maxTailInflight, rust.tailInflight);
        return later(arrive(), () => {
          const w = rust.watch; // Rust 가 명령을 집어 든 순간 — 길이·레코드를 여기서 찍는다
          return !w || w.seat !== a.surfaceId ? null : { gen: w.gen, size: file.length, recs: file.slice(a.afterOffset) };
        }).then((snap) =>
          later(ri(...(opt.tailMs ?? [0, 6])), () => {
            rust.tailInflight--;
            if (!snap) {
              rust.notWatching++;
              return { status: "unknown", why: "not_watching" };
            }
            return { status: "ok", session_id: SID, gen: snap.gen, from_offset: a.afterOffset, to_offset: snap.size, next_offset: snap.size, size: snap.size, records: snap.recs, reset: false, more: false };
          }),
        );
      }
      if (cmd === "default_socket_slug") return "slug";
      throw new Error(`unexpected ${cmd}`);
    },
    listenApp: (name, handler) =>
      later(ri(0, 3), () => {
        const hs = app.get(name) ?? [];
        hs.push(handler);
        app.set(name, hs);
        return () => app.set(name, (app.get(name) ?? []).filter((h) => h !== handler));
      }),
    now: () => now,
    setTimeout: (fn, ms) => {
      const h = ++hn;
      timers.push({ at: now + ms, fn, h });
      return h;
    },
    clearTimeout: (h) => {
      const i = timers.findIndex((t) => t.h === h);
      if (i >= 0) timers.splice(i, 1);
    },
    store: { get: () => null, set: () => {}, remove: () => {} },
    working: (r) => r.working === true,
    compat1118: () => opt.compat,
  } as Deps;
  const flush = async () => {
    for (let i = 0; i < 80; i++) await Promise.resolve();
  };
  const advance = async (ms: number) => {
    const until = now + ms;
    for (;;) {
      timers.sort((a, b) => a.at - b.at || a.h - b.h);
      const t = timers[0];
      if (!t || t.at > until) break;
      timers.shift();
      now = t.at;
      t.fn();
      await flush();
    }
    now = until;
    await flush();
  };
  const core = new ChatCore(deps);
  const seen: string[] = [];
  (core.confirm as unknown as { onTail(r: Array<{ uuid?: string }>): void }).onTail = (r) => void seen.push(...r.map((x) => String(x.uuid)));
  let nrec = 0;
  let view: "chat" | "work" = "chat";
  let sinceTick = 0;
  let sincePoll = 0;
  /** 앱 1초 시계(pollTick) 를 시간 흐름에 맞춰 부른다 — pollTick 이 3초마다 poll 을 스스로 낸다. */
  const pass = async (ms: number) => {
    let left = ms;
    while (left > 0) {
      const step = Math.min(left, 1000 - sinceTick);
      await advance(step);
      left -= step;
      sinceTick += step;
      sincePoll += step;
      if (sinceTick >= 1000) {
        sinceTick = 0;
        core.pollTick();
        await flush();
      }
    }
  };
  const acts: Record<string, () => Promise<void>> = {
    append: async () => {
      const k = ri(1, 3);
      for (let i = 0; i < k; i++) file.push({ uuid: `u${++nrec}`, parent: null, role: "assistant", text: `답 ${nrec}`, ts: null });
    },
    wait_short: async () => pass(ri(1, 120)),
    wait_beat: async () => pass(ri(200, 700)),
    wait_long: async () => pass(ri(1000, 4000)),
    to_work: async () => {
      if (view !== "chat") return;
      core.watchStart(); // 새 화면 먼저
      core.detach();
      view = "work";
    },
    to_chat: async () => {
      if (view !== "work") return;
      core.attach();
      core.watchStop();
      view = "chat";
    },
    flip_fast: async () => {
      // 대화 → 작업 → 대화 를 몇 ms 안에(unwatch·watch 가 잇달아)
      if (view !== "chat") return;
      core.watchStart();
      core.detach();
      await advance(ri(0, 4));
      core.attach();
      core.watchStop();
    },
    work_toggle: async () => {
      master.working = !master.working;
    },
    send: async () => {
      if (view === "chat") core.submit(`말 ${ri(1, 9999)}`);
    },
  };
  const push = (k: number) => {
    for (let i = 0; i < k; i++) file.push({ uuid: `u${++nrec}`, parent: null, role: "assistant", text: `답 ${nrec}`, ts: null });
  };
  return { core, rust, file, seen, acts, pass, advance, flush, rnd, ri, calls, master, push, at, getView: () => view, toChat: acts.to_chat };
}

