// (cysr-1116-s6) 왼쪽 메뉴바 장부 시험 — 공통층 배선(대화 화면이 켜져 있을 때만 조회) · 묶음 사건 · 표식 · 부서 가이드 1회.
import { describe, expect, it } from "bun:test";
import { ChatCore, type Deps } from "./core";
import { DEPT_GUIDE_KEY, DEPTS_EVERY, LIST_MAX_MS, RailBook } from "./rail";

function harness(o: { surfaces?: Record<string, unknown>[]; depts?: unknown; listHang?: boolean } = {}) {
  const calls: Array<{ cmd: string; args?: Record<string, unknown> }> = [];
  const mem = new Map<string, string>();
  let now = 1_000_000;
  const timers: Array<{ at: number; fn: () => void; h: number }> = [];
  let hn = 0;
  const st = {
    surfaces: o.surfaces ?? [{ surface_id: 7, role: "worker-7", cwd: "/a/site", exited: false, group: null, group_set: false }],
    depts: o.depts ?? { depts: {} },
    listHang: o.listHang ?? false,
  };
  const master = { surface_id: 5, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null };
  const deps: Deps = {
    invoke: async (cmd, args) => {
      calls.push({ cmd, args });
      if (cmd === "org_status") return { surfaces: [master, { surface_id: 7, idle_secs: 3, status: { state: "working", task: "사이트 고치기", age_secs: 2 } }] };
      if (cmd === "feed_list") return { items: [] };
      if (cmd === "list_surfaces") return st.listHang ? new Promise(() => {}) : { surfaces: st.surfaces.map((s) => ({ ...s })) };
      if (cmd === "list_depts") return st.depts;
      if (cmd === "chat_transcript") return { status: "ok", session_id: "s1", next_offset: 0, size: 0, records: [] };
      if (cmd === "default_socket_slug") return "base";
      throw new Error(`unexpected ${cmd}`);
    },
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
    store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v), remove: (k) => void mem.delete(k) },
    working: (r) => r.working === true,
    defaultSlug: async () => "base",
  };
  const flush = async () => {
    for (let i = 0; i < 30; i++) await Promise.resolve();
  };
  const advance = async (ms: number) => {
    const until = now + ms;
    for (;;) {
      timers.sort((a, b) => a.at - b.at);
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
  return { core: new ChatCore(deps), calls, st, mem, flush, advance };
}

const count = (calls: Array<{ cmd: string }>, cmd: string) => calls.filter((c) => c.cmd === cmd).length;

describe("공통층 배선 — 대화 화면이 켜져 있을 때만", () => {
  it("켜지기 전 조회 = 좌석 목록·부서 등록부 0", async () => {
    const h = harness();
    await h.core.poll();
    await h.flush();
    expect(count(h.calls, "list_surfaces")).toBe(0);
    expect(count(h.calls, "list_depts")).toBe(0);
  });
  it("켜진 뒤 3초 조회마다 좌석 목록 1(본부) · 부서 등록부 = 처음 + 10번째마다", async () => {
    const h = harness();
    h.core.attach();
    await h.flush();
    for (let i = 0; i < DEPTS_EVERY + 1; i++) {
      await h.core.poll();
      await h.flush();
    }
    expect(count(h.calls, "list_surfaces")).toBe(DEPTS_EVERY + 1);
    expect(h.calls.filter((c) => c.cmd === "list_surfaces").every((c) => c.args?.socket === null)).toBe(true);
    expect(count(h.calls, "list_depts")).toBe(2);
    const m = h.core.rail.model;
    expect(m.loading).toBe(false);
    expect(m.blocks[0].cards[0]).toMatchObject({ title: "사이트 고치기", status: "wait", helpers: 1 });
  });
  it("좌석 목록이 멈춰도 조회 고리가 묶이지 않는다(상한 뒤 직전 값)", async () => {
    const h = harness({ listHang: true });
    h.core.attach();
    await h.flush();
    void h.core.poll();
    await h.advance(LIST_MAX_MS + 1);
    expect(h.core.rail.model.loading).toBe(true);
    void h.core.poll();
    await h.advance(LIST_MAX_MS + 1);
    expect(count(h.calls, "list_surfaces")).toBe(2); // 다음 조회도 다시 묻는다(앞 조회가 걸려 고리가 서지 않음)
  });
  it("세션 기록 마스터 답의 ⟪팀 만드는 중⟫ → 카드 · 본부 묶음 사건 → 내림 · 부서 사건 = 무시", async () => {
    const h = harness();
    h.core.attach();
    await h.flush();
    await h.core.poll();
    await h.flush();
    h.core.rail.onTail([{ uuid: "a1", parent: null, role: "assistant", text: "나눠 볼게요.\n⟪팀 만드는 중: 홍보팀⟫", ts: null }]);
    expect(h.core.rail.model.forming.map((f) => f.name)).toEqual(["홍보팀"]);
    h.core.rail.onEvent({ name: "surface.group.changed", socket_slug: "dept-1", surface_id: 7, payload: { surface_id: 7, group: "홍보팀" } });
    expect(h.core.rail.model.forming.map((f) => f.name)).toEqual(["홍보팀"]);
    h.core.rail.onEvent({ name: "surface.group.changed", socket_slug: "base", surface_id: 7, payload: { surface_id: 7, group: "홍보팀", previous: null } });
    expect(h.core.rail.model.forming).toEqual([]);
    expect(h.core.rail.model.blocks[0].cards[0].title).toBe("사이트 고치기");
  });
  it("데몬 사건 구독(listenDaemon)으로 들어온 묶음 사건도 메뉴바에 간다", async () => {
    let fire: ((ev: unknown) => void) | null = null;
    const h = harness();
    // listenDaemon 을 단 새 core
    const core = new ChatCore({
      ...(h.core as unknown as { d: Deps }).d,
      listenDaemon: (fn) => {
        fire = fn;
        return () => {
          fire = null;
        };
      },
    });
    core.attach();
    await h.flush();
    await core.poll();
    await h.flush();
    core.rail.onTail([{ uuid: "a1", parent: null, role: "assistant", text: "⟪팀 만드는 중: 홍보팀⟫", ts: null }]);
    expect(fire).not.toBeNull();
    fire!({ name: "surface.group.changed", socket_slug: "base", surface_id: 7, payload: { surface_id: 7, group: "홍보팀" } });
    expect(core.rail.model.forming).toEqual([]);
    core.detach();
    expect(fire).toBeNull();
  });
});

describe("부서 가이드(§16-5 ② · §16-6)", () => {
  const mk = (mem: Map<string, string>) => {
    let depts: unknown = { depts: {} };
    let n = 0;
    const b = new RailBook(
      {
        invoke: async (cmd) => (cmd === "list_depts" ? depts : cmd === "list_surfaces" ? { surfaces: [] } : undefined),
        now: () => 5,
        setTimeout: () => 0,
        clearTimeout: () => {},
        store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v) },
        working: () => false,
      },
      () => n++,
    );
    return { b, setDepts: (v: unknown) => (depts = v), changes: () => n };
  };
  it("부서 0 = 가이드 없음 · 처음 부서가 생기면 한 번(본 적 없음) · 「알겠어요」 = 본 적 있음 기록", async () => {
    const mem = new Map<string, string>();
    const { b, setDepts } = mk(mem);
    await b.refresh(undefined, null);
    expect(b.guide).toBeNull();
    setDepts({ depts: { "dept-1": { display_name: "홍보부" } } });
    for (let i = 0; i < DEPTS_EVERY; i++) await b.refresh(undefined, null);
    expect(b.model.depts.map((d) => d.title)).toEqual(["홍보부"]);
    expect(b.guide).toBe("first");
    b.ackGuide();
    expect(b.guide).toBeNull();
    expect(JSON.parse(mem.get(DEPT_GUIDE_KEY)!)).toMatchObject({ v: 1 });
    await b.refresh(undefined, null);
    expect(b.guide).toBeNull();
  });
  it("본 적 있으면 저절로 안 뜸 · 「부서 안내」는 늘 열림(다시 누르면 접힘)", async () => {
    const mem = new Map<string, string>([[DEPT_GUIDE_KEY, '{"v":1,"at":1}']]);
    const { b, setDepts } = mk(mem);
    setDepts({ depts: { "dept-1": {} } });
    await b.refresh(undefined, null);
    expect(b.guide).toBeNull();
    b.toggleGuide();
    expect(b.guide).toBe("again");
    b.toggleGuide();
    expect(b.guide).toBeNull();
  });
});
