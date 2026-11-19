// (cysr-1116-s5 · TICKET=cysr-1116-s5-1119) 조각 5 시험 — 멈춤·깨우기·다시 켜기(P2-DESIGN §6-2 「시험(조각 5)」 · §7 4군 ①②).
//
// 대역 = 가짜 데몬(org.status 행 · start_master · close_surface · chat_send{auto} · 사건) + 가짜 시계·타이머 + 앱 저장소 Map.
// 「옛 사람 입력줄 바이트 변화 0」 = 다시 켜기 동안 기존 좌석에 쓰는 호출(chat_send·send_input·send_text·send_key) 계수 0 — PTY 쓰기는 이 호출로만 난다.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { ReviveBook, GONE_KEY, SEEN_KEY, type ReviveDeps } from "./revive";
import { masterRowOf, sendGate, ownLastHumanInput, type MasterRow } from "./judge/gate";
import {
  DEAD_AXES,
  RETRY_DELAY_MS,
  WAKE_DEDUPE_MS,
  WAKE_TEXT,
  WAKE_TIMEOUT_MS,
  denialNext,
  leftoverShell,
  restartPlan,
  restartSucceeded,
  reviveBand,
  reviveSituation,
  startOutcome,
  NEVER_STARTED_MS,
  type ReviveFacts,
} from "./judge/revive";

type Row = Record<string, unknown> & { surface_id: number };

function row(sid: number, role: string | null, over: Partial<Row> = {}): Row {
  return {
    surface_id: sid,
    role,
    exited: false,
    agent: "claude",
    agent_alive: true,
    agent_seen: true,
    seat: "occupied",
    gate_pending: null,
    pending_input_bytes: 0,
    pending_input_human_bytes: 0,
    input_paste_open: false,
    human_idle_secs: null,
    idle_secs: 5,
    ...over,
  };
}

type StartPlan = (n: number, env: Env) => Promise<void>;
const GATE_ERR = "마스터 pane 은 떴고 프로세스도 살아 있으나 **첫기동 관문**에 갇혀 있습니다(pane 은 닫지 않았습니다).";
const DENIED_ERR = "error: claim_denied: surface.create denied: privileged role 'master' is held by a live surface";

class Env {
  now = 1_000_000;
  timers: Array<{ at: number; fn: () => void; id: number }> = [];
  private tid = 0;
  rows: Row[] = [];
  store = new Map<string, string>();
  calls: Array<{ cmd: string; args?: Record<string, unknown> }> = [];
  tracked: Array<[string, number]> = [];
  hold = 0;
  views: string[] = [];
  focused: number[] = [];
  hints: Array<string | null> = [];
  helps = 0;
  changes = 0;
  nextSid = 100;
  /** start_master 의 n 번째 호출을 어떻게 할지 · 기본 = 새 마스터 좌석(옛 마스터 역할 회수) */
  startPlan: StartPlan = async (_n, env) => env.spawnMaster();
  starts = 0;
  closeFails = false;
  book: ReviveBook;

  constructor(seed?: (e: Env) => void) {
    seed?.(this);
    const d: ReviveDeps = {
      invoke: (cmd, args) => this.invoke(cmd, args),
      now: () => this.now,
      setTimeout: (fn, ms) => {
        const id = ++this.tid;
        this.timers.push({ at: this.now + ms, fn, id });
        return id;
      },
      clearTimeout: (h) => {
        this.timers = this.timers.filter((t) => t.id !== h);
      },
      store: { get: (k) => this.store.get(k) ?? null, set: (k, v) => void this.store.set(k, v), remove: (k) => void this.store.delete(k) },
      working: (r) => r.working === true,
      trackAuto: (id, seat) => void this.tracked.push([id, seat]),
      holdRemainingMs: () => this.hold,
      goView: (id) => void this.views.push(id),
      focusSeat: (sid) => void this.focused.push(sid),
      workHint: (t) => void this.hints.push(t),
      openHelp: () => void this.helps++,
      changed: () => void this.changes++,
    };
    this.book = new ReviveBook(d);
  }

  org() {
    return { surfaces: this.rows.map((r) => ({ ...r })) };
  }

  setLater(ms: number, fn: () => void): void {
    this.timers.push({ at: this.now + ms, fn, id: ++this.tid });
  }

  async invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown> {
    this.calls.push({ cmd, args });
    await Promise.resolve();
    if (cmd === "org_status") return this.org();
    if (cmd === "close_surface") {
      if (this.closeFails) throw new Error("close_denied");
      const sid = args?.surfaceId;
      this.rows = this.rows.filter((r) => r.surface_id !== sid);
      return null;
    }
    if (cmd === "start_master") return this.startPlan(++this.starts, this);
    if (cmd === "chat_send") return { outcome: "queued", queue_entry_id: `q${this.calls.length}` };
    throw new Error(`unexpected ${cmd}`);
  }

  /** 새 마스터 좌석이 서고 옛 마스터 행은 역할을 잃는다(승계·회수 뒤 꼴) — CSO·워커는 그대로. */
  spawnMaster(over: Partial<Row> = {}): void {
    for (const r of this.rows) if (r.role === "master") r.role = null;
    this.rows.push(row(this.nextSid++, "master", over));
  }

  emit(name: string, sid: number | null, payload: Record<string, unknown>): void {
    this.book.onEvent({ name, surface_id: sid, payload });
  }

  /** 3초 조회 1회 */
  observe(): void {
    const org = this.org();
    this.book.observe(masterRowOf(org, (r) => r.working === true), org);
  }

  async flush(): Promise<void> {
    for (let i = 0; i < 20; i++) await Promise.resolve();
  }

  async advance(ms: number): Promise<void> {
    const end = this.now + ms;
    for (;;) {
      await this.flush();
      const due = this.timers.filter((t) => t.at <= end).sort((a, b) => a.at - b.at)[0];
      if (!due) break;
      this.now = Math.max(this.now, due.at);
      this.timers = this.timers.filter((t) => t !== due);
      due.fn();
    }
    this.now = end;
    await this.flush();
  }

  count(cmd: string): number {
    return this.calls.filter((c) => c.cmd === cmd).length;
  }
  /** 기존 좌석 입력줄에 닿는 호출(PTY 쓰기 경로) — 다시 켜기 동안 0 이어야 한다 */
  seatWrites(): number {
    return this.calls.filter((c) => ["chat_send", "send_input", "send_text", "send_key", "send_key_raw"].includes(c.cmd)).length;
  }
  band() {
    return this.book.view().band;
  }
  roles(role: string): number {
    return this.rows.filter((r) => r.role === role && r.exited !== true).length;
  }
}

const base = (e: Env) => {
  e.rows = [row(5, "master"), row(6, "cso"), row(7, "worker"), row(8, "worker")];
};

describe("judge/revive — 축 6 + vacant + never_started 판정(순수)", () => {
  const mk = (over: Partial<ReviveFacts>): ReviveFacts => ({ master: null, seenBefore: false, goneMark: false, dead: null, neverSince: null, idle: null, now: 0, ...over });
  const live = (over: Partial<MasterRow> = {}): MasterRow => ({ surface_id: 5, exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false, idle_secs: 1, agent: "claude", agent_seen: true, seat: "occupied", ...over });
  it("축 이름 = 데몬 DeadmanAxis::as_str 6개 그대로", () => {
    const rs = readFileSync(new URL("../../../src/bin/cysd/governance.rs", import.meta.url), "utf8");
    for (const a of DEAD_AXES) expect(rs).toContain(`=> "${a}"`);
    expect(DEAD_AXES.length).toBe(6);
  });
  it("surface_gone · surface_exited(마스터 행 없음) → 「마스터 창이 닫혀 있어요」", () => {
    for (const axis of ["surface_gone", "surface_exited"] as const) {
      const s = reviveSituation(mk({ dead: { sid: 5, axis } }));
      expect(s).toEqual({ kind: "down", down: "gone", axis, sid: 5 });
      expect(reviveBand(s, { kind: "rest" }, false, 0)?.title).toBe("마스터 창이 닫혀 있어요.");
    }
  });
  it("agent_dead · seat_vacant_no_meta · shell_proc_dead(그 좌석 사건) → 「마스터 프로그램이 멈췄어요」", () => {
    for (const axis of ["agent_dead", "seat_vacant_no_meta", "shell_proc_dead"] as const) {
      const s = reviveSituation(mk({ master: live({ agent_alive: null }), dead: { sid: 5, axis } }));
      expect(s).toEqual({ kind: "down", down: "agent", axis, sid: 5 });
      expect(reviveBand(s, { kind: "rest" }, false, 0)?.title).toBe("마스터 프로그램이 멈췄어요.");
    }
    expect(reviveSituation(mk({ master: live({ agent_alive: false }) }))).toMatchObject({ kind: "down", down: "agent" }); // 사건 없이 행만
  });
  it("agent_never_started(사건) · 행 증거 90초 지속 → 「마스터가 아직 시작하지 못했어요」 · 90초 전 = ok", () => {
    const nev = live({ agent_alive: null, agent_seen: false, seat: "empty" });
    expect(reviveSituation(mk({ master: nev, dead: { sid: 5, axis: "agent_never_started" } }))).toMatchObject({ kind: "down", down: "never", sid: 5 });
    expect(reviveSituation(mk({ master: nev, neverSince: 0, now: NEVER_STARTED_MS - 1 })).kind).toBe("ok");
    expect(reviveSituation(mk({ master: nev, neverSince: 0, now: NEVER_STARTED_MS }))).toMatchObject({ kind: "down", down: "never" });
    expect(reviveSituation(mk({ master: live({ agent_alive: null, agent_seen: false, seat: "occupied" }), neverSince: 0, now: 1e9 })).kind).toBe("ok"); // 기동 중(Occupied) = 아님
  });
  it("vacant: 마스터 행 없음 ∧ (본 적 있음 ∨ 놓아짐 기록) → 「마스터가 멈춰 있어요」 · 새 설치 = none(꺼짐이라 하지 않음)", () => {
    expect(reviveSituation(mk({ seenBefore: true }))).toMatchObject({ kind: "down", down: "vacant" });
    expect(reviveSituation(mk({ goneMark: true }))).toMatchObject({ kind: "down", down: "vacant" });
    expect(reviveSituation(mk({})).kind).toBe("none");
    expect(reviveSituation(mk({ master: undefined, seenBefore: true })).kind).toBe("unknown"); // 조회 실패 = 모름(꺼짐 아님)
  });
  it("낡은 사건: 그 좌석이 다시 살아 보이면 deadman 무시 · 다른 좌석 사건 무시 · 창이 산 좌석의 gone 사건 무시", () => {
    expect(reviveSituation(mk({ master: live(), dead: { sid: 5, axis: "agent_dead" } })).kind).toBe("ok");
    expect(reviveSituation(mk({ master: live({ agent_alive: null }), dead: { sid: 4, axis: "agent_dead" } })).kind).toBe("ok");
    expect(reviveSituation(mk({ master: live({ agent_alive: null }), dead: { sid: 5, axis: "surface_gone" } })).kind).toBe("ok");
  });
  it("관문 보류 → gate 띠(§6-3) · 조용함 사건 → 깨우기 띠", () => {
    expect(reviveSituation(mk({ master: live({ gate_pending: { gate: "trust" } }) }))).toEqual({ kind: "gate", sid: 5 });
    expect(reviveBand({ kind: "gate", sid: 5 }, { kind: "rest" }, false, 0)?.buttons).toEqual(["gate_answer"]);
    expect(reviveSituation(mk({ master: live(), idle: { sid: 5, at: 0 } }))).toEqual({ kind: "idle", sid: 5 });
  });
  it("never 길: 사람 입력 0 = 닫고 켬 · 사람 입력 있음·붙여넣기 열림·모름 = 닫지 않음(안내)", () => {
    const s = { kind: "down", down: "never", axis: "agent_never_started", sid: 5 } as const;
    expect(restartPlan(s, live())).toEqual({ kind: "close_then_start", sid: 5 });
    expect(restartPlan(s, live({ pending_input_human_bytes: 3 }))).toEqual({ kind: "draft_block", sid: 5 });
    expect(restartPlan(s, live({ input_paste_open: true }))).toEqual({ kind: "draft_block", sid: 5 });
    expect(restartPlan(s, live({ pending_input_human_bytes: null }))).toEqual({ kind: "draft_block", sid: 5 });
    expect(restartPlan(s, live({ surface_id: 9 }))).toEqual({ kind: "none" }); // 다시 받은 행이 다른 좌석
    expect(restartPlan({ kind: "down", down: "agent", axis: "agent_dead", sid: 5 }, live())).toEqual({ kind: "start" });
  });
  it("거절 다음 걸음: 사람 입력(칸·사유 원문) = 기다림 · seat_not_claimable = 1회 · 그 밖·사건 없음 = 실패", () => {
    expect(denialNext({ seat_blocked: "seat_not_claimable", seat_human_recent: true }, false)).toBe("hold_human");
    expect(denialNext({ seat_blocked: "recheck_cancelled", takeover_cancelled: "프로브 후 사람 입력 관측(사용자가 그 pane 을 사용 중)" }, false)).toBe("hold_human");
    expect(denialNext({ seat_blocked: "seat_not_claimable", seat_human_recent: false }, false)).toBe("retry");
    expect(denialNext({ seat_blocked: "seat_not_claimable" }, true)).toBe("fail");
    expect(denialNext({ seat_blocked: "recheck_cancelled", takeover_cancelled: "프로브 후 좌석 캐시가 Occupied 로 갱신됨(자손 프로세스 생성)" }, false)).toBe("fail");
    expect(denialNext(null, false)).toBe("fail");
  });
  it("start_master 결과 글 갈래 — 관문 문구·claim_denied 는 main.rs·cys CLI 원문에 실재", () => {
    expect(startOutcome(undefined)).toBe("ok");
    expect(startOutcome(GATE_ERR)).toBe("gate_pending");
    expect(startOutcome(DENIED_ERR)).toBe("denied");
    expect(startOutcome("boom")).toBe("failed");
    const main = readFileSync(new URL("../../../src-tauri/src/main.rs", import.meta.url), "utf8");
    const f = main.indexOf("async fn start_master(");
    expect(main.slice(f, f + 3000)).toContain("첫기동 관문");
    const h = readFileSync(new URL("../../../src/bin/cysd/handlers.rs", import.meta.url), "utf8");
    expect(h).toContain('"claim_denied",\n                            &format!(\n                                "surface.create denied');
  });
  it("성공 판정 = 좌석 id 바뀜 ∧ 에이전트 생존 ∧ 관문 없음(고장 난 빈 셸·같은 좌석 = 아님)", () => {
    expect(restartSucceeded(5, live({ surface_id: 9 }))).toBe(true);
    expect(restartSucceeded(5, live())).toBe(false);
    expect(restartSucceeded(5, live({ surface_id: 9, agent_alive: null }))).toBe(false);
    expect(restartSucceeded(5, live({ surface_id: 9, gate_pending: { gate: "x" } }))).toBe(false);
    expect(restartSucceeded(null, live({ surface_id: 9 }))).toBe(true);
  });
  it("옛 빈 셸 정리 대상 = 역할 없음 ∧ Empty ∧ 사람 입력 0 ∧ 최근 사람 입력 없음", () => {
    const org = (o: Partial<Row>) => ({ surfaces: [row(5, null, { seat: "empty", agent_alive: null, ...o })] });
    expect(leftoverShell(org({}), 5, 9)).toBe(5);
    expect(leftoverShell(org({ role: "master" }), 5, 9)).toBe(null);
    expect(leftoverShell(org({ agent: null }), 5, 9)).toBe(null); // 사용자가 연 맨 셸(번호 재사용) = 닫지 않음
    expect(leftoverShell(org({ seat: "occupied" }), 5, 9)).toBe(null);
    expect(leftoverShell(org({ pending_input_human_bytes: 1 }), 5, 9)).toBe(null);
    expect(leftoverShell(org({ human_idle_secs: 3 }), 5, 9)).toBe(null);
    expect(leftoverShell(org({ human_idle_secs: 40 }), 5, 9)).toBe(5);
    expect(leftoverShell(org({ exited: true }), 5, 9)).toBe(null);
    expect(leftoverShell(org({}), 9, 9)).toBe(null);
    expect(leftoverShell(org({}), null, 9)).toBe(null);
  });
});

describe("다시 켜기 — 축별 길(대역 데몬)", () => {
  it("surface_gone → start_master 1 · 닫기 0 · 성공(새 좌석 생존) → 띠 없음 · CSO·워커 수 같음 · 옛 입력줄 쓰기 0", async () => {
    const e = new Env(base);
    e.observe();
    e.rows = e.rows.filter((r) => r.surface_id !== 5);
    e.emit("master.deadman", 5, { role: "master", axis: "surface_gone" });
    e.observe();
    expect(e.band()?.title).toBe("마스터 창이 닫혀 있어요.");
    const before = { cso: e.roles("cso"), worker: e.roles("worker") };
    await e.book.restart();
    expect(e.count("start_master")).toBe(1);
    expect(e.count("close_surface")).toBe(0);
    expect(e.book.view().phase.kind).toBe("restarting");
    e.observe();
    expect(e.book.view().phase.kind).toBe("rest");
    expect(e.band()).toBe(null);
    expect({ cso: e.roles("cso"), worker: e.roles("worker") }).toEqual(before);
    expect(e.roles("master")).toBe(1);
    expect(e.seatWrites()).toBe(0);
  });
  it("surface_exited · agent_dead · seat_vacant_no_meta · shell_proc_dead → start_master 1(같은 길) · 쓰기 0", async () => {
    for (const axis of ["surface_exited", "agent_dead", "seat_vacant_no_meta", "shell_proc_dead"] as const) {
      const e = new Env(base);
      e.observe();
      if (axis === "surface_exited") e.rows[0].exited = true;
      else e.rows[0].agent_alive = null;
      e.emit("master.deadman", 5, { role: "master", axis });
      e.observe();
      expect(e.book.view().sit.kind).toBe("down");
      await e.book.restart();
      e.observe();
      expect(`${axis}:${e.count("start_master")}:${e.count("close_surface")}:${e.seatWrites()}:${e.book.view().phase.kind}`).toBe(`${axis}:1:${axis === "surface_exited" ? 0 : 0}:0:rest`);
      expect(e.roles("cso")).toBe(1);
      expect(e.roles("worker")).toBe(2);
    }
  });
  it("agent_never_started → 옛 좌석 사람 입력 0 확인 → close_surface(그 좌석) 다음 start_master(순서) · 쓰기 0", async () => {
    const e = new Env(base);
    Object.assign(e.rows[0], { agent_alive: null, agent_seen: false, seat: "empty" });
    e.emit("master.deadman", 5, { role: "master", axis: "agent_never_started" });
    e.observe();
    expect(e.band()?.title).toBe("마스터가 아직 시작하지 못했어요.");
    await e.book.restart();
    const seq = e.calls.filter((c) => c.cmd === "close_surface" || c.cmd === "start_master").map((c) => `${c.cmd}:${c.args?.surfaceId ?? ""}`);
    expect(seq).toEqual(["close_surface:5", "start_master:"]);
    e.observe();
    expect(e.book.view().phase.kind).toBe("rest");
    expect(e.seatWrites()).toBe(0);
    expect(e.roles("cso") + e.roles("worker")).toBe(3);
  });
  it("never_started + 옛 창에 사람 입력 → 닫지 않음 · start_master 0 · 「그 창에 쓰다 만 글이 있어요」 + 작업 화면에서 보기", async () => {
    const e = new Env(base);
    Object.assign(e.rows[0], { agent_alive: null, agent_seen: false, seat: "empty", pending_input_human_bytes: 12 });
    e.emit("master.deadman", 5, { role: "master", axis: "agent_never_started" });
    e.observe();
    await e.book.restart();
    expect(e.count("close_surface") + e.count("start_master")).toBe(0);
    expect(e.band()?.title).toBe("그 창에 쓰다 만 글이 있어요.");
    expect(e.band()?.buttons).toContain("work");
    e.book.toWork();
    expect(e.views).toEqual(["work"]);
  });
  it("vacant(회수 뒤 · 앱 새로 켬 · 저장소에 본 적 있음) → 꺼짐 띠 즉시 → start_master → 성공 뒤 옛 빈 셸 정리(사람 입력 0)", async () => {
    const e = new Env((x) => {
      x.store.set(SEEN_KEY, "5");
      x.rows = [row(5, null, { agent_alive: null, seat: "empty" }), row(6, "cso"), row(7, "worker")];
    });
    e.observe(); // 앱을 새로 켠 첫 조회 — 지난 deadman 은 못 받음
    expect(e.band()?.title).toBe("마스터가 멈춰 있어요.");
    await e.book.restart();
    expect(e.count("start_master")).toBe(1);
    e.observe();
    await e.flush();
    expect(e.calls.filter((c) => c.cmd === "close_surface").map((c) => c.args?.surfaceId)).toEqual([5]);
    expect(e.store.get(SEEN_KEY)).toBe("100");
    expect(e.roles("cso")).toBe(1);
    expect(e.seatWrites()).toBe(0);
  });
  it("vacant 정리 — 옛 빈 셸에 사람 입력이 있으면 닫지 않는다", async () => {
    const e = new Env((x) => {
      x.store.set(SEEN_KEY, "5");
      x.rows = [row(5, null, { agent_alive: null, seat: "empty", pending_input_human_bytes: 4 }), row(6, "cso")];
    });
    e.observe();
    await e.book.restart();
    e.observe();
    await e.flush();
    expect(e.count("close_surface")).toBe(0);
  });
  it("앱 새로 켬 + 놓아짐 기록만(role.released 받았던 기록) → 꺼짐 띠 · 새 설치(기록 0) → 띠 0", async () => {
    const a = new Env((x) => {
      x.store.set(GONE_KEY, "1");
      x.rows = [row(6, "cso")];
    });
    a.observe();
    expect(a.band()?.key).toBe("down_vacant");
    const b = new Env((x) => {
      x.rows = [row(6, "cso")];
    });
    b.observe();
    expect(b.band()).toBe(null);
    expect(b.book.view().sit.kind).toBe("none");
  });
  it("role.released{master} · deadman 사건 = 놓아짐 기록(앱 저장소) · 살아 있는 마스터를 다시 보면 지움", () => {
    const e = new Env(base);
    e.emit("role.released", null, { role: "master" });
    expect(e.store.get(GONE_KEY)).toBe("1");
    e.observe();
    expect(e.store.get(GONE_KEY)).toBeUndefined();
    e.emit("role.released", null, { role: "worker" });
    expect(e.store.get(GONE_KEY)).toBeUndefined();
  });
});

describe("다시 켜기 — 거절·자동 재시도·잠금(4군 ①)", () => {
  const dead = (e: Env) => {
    base(e);
    e.rows[0].agent_alive = false;
  };
  it("거절 3회 주입(seat_not_claimable) → 자동 재시도 ≤ 1 · 그 뒤 실패 안내 · 30분 지나도 start_master 2", async () => {
    const e = new Env(dead);
    e.startPlan = async (_n, env) => {
      env.emit("role.claim_denied", null, { role: "master", path: "surface.create", seat_blocked: "seat_not_claimable", seat_human_recent: false, takeover_cancelled: null });
      throw DENIED_ERR;
    };
    e.observe();
    await e.book.restart();
    expect(e.book.view().phase.kind).toBe("retry_wait");
    expect(e.band()?.title).toBe("꺼진 마스터 자리를 정리하는 중이에요.");
    await e.advance(RETRY_DELAY_MS - 1);
    expect(e.count("start_master")).toBe(1);
    await e.advance(1);
    expect(e.count("start_master")).toBe(2);
    await e.advance(30 * 60_000);
    expect(e.count("start_master")).toBe(2);
    expect(e.book.counts.autoRetry).toBe(1);
    expect(e.book.view().phase.kind).toBe("restartfail");
    expect(e.band()?.buttons).toEqual(["help", "restart"]);
    // 사람이 다시 누름(셋째 거절) = 새 차례 — 자동 1회가 다시 생기지만 그 차례도 ≤ 1
    await e.book.restart();
    await e.advance(30 * 60_000);
    expect(e.count("start_master")).toBe(4);
    expect(e.book.counts.autoRetry).toBe(2);
  });
  it("거절 사유 = 사람 입력(seat_human_recent · 사유 원문) → 자동 재시도 0 · 「방금 누가 글을 쓰고 있어」 + 다시 켜기·작업 화면", async () => {
    for (const p of [
      { seat_blocked: "seat_not_claimable", seat_human_recent: true },
      { seat_blocked: "recheck_cancelled", seat_human_recent: false, takeover_cancelled: "프로브 후 사람 입력 관측(사용자가 그 pane 을 사용 중)" },
    ]) {
      const e = new Env(dead);
      e.startPlan = async (_n, env) => {
        env.emit("role.claim_denied", null, { role: "master", path: "surface.create", ...p });
        throw DENIED_ERR;
      };
      e.observe();
      await e.book.restart();
      await e.advance(10 * 60_000);
      expect(e.count("start_master")).toBe(1);
      expect(e.band()?.title).toBe("마스터 창에 방금 누가 글을 쓰고 있어 기다리고 있어요.");
      expect(e.band()?.buttons).toEqual(["restart", "work"]);
    }
  });
  it("거절 사건이 늦게 옴(1.5초 안) → 그 사건으로 판단 · 끝내 안 옴 → 실패(자동 0)", async () => {
    const late = new Env(dead);
    late.startPlan = async (_n, env) => {
      env.setLater(500, () => env.emit("role.claim_denied", null, { role: "master", path: "surface.create", seat_blocked: "seat_not_claimable" }));
      throw DENIED_ERR;
    };
    late.observe();
    const p = late.book.restart();
    await late.advance(2_000);
    await p;
    expect(late.book.view().phase.kind).toBe("retry_wait");
    const none = new Env(dead);
    none.startPlan = async () => {
      throw DENIED_ERR;
    };
    none.observe();
    const q = none.book.restart();
    await none.advance(2_000);
    await q;
    await none.advance(10 * 60_000);
    expect(none.count("start_master")).toBe(1);
    expect(none.book.view().phase.kind).toBe("restartfail");
  });
  it("연타 20회 → start_master 1 · 깨우기 연타 20회 → 깨움 말 1", async () => {
    const e = new Env(dead);
    let release!: () => void;
    e.startPlan = () => new Promise<void>((r) => (release = () => r()));
    e.observe();
    const ps = Array.from({ length: 20 }, () => e.book.restart());
    await e.flush();
    release();
    await Promise.all(ps);
    expect(e.count("start_master")).toBe(1);
    const w = new Env(base);
    w.observe();
    w.emit("master.idle", 5, { role: "master", axis: "silence" });
    const ws = Array.from({ length: 20 }, () => w.book.wake());
    await Promise.all(ws);
    expect(w.count("chat_send")).toBe(1);
  });
  it("복원 중(restore-progress start) → 다시 켜기 호출 0 · 단추 잠금 「복원하는 중이에요」 · done 뒤 1", async () => {
    const e = new Env(dead);
    e.observe();
    e.book.onAppEvent("restore-progress", { phase: "start" });
    await e.book.restart();
    expect(e.count("start_master") + e.count("org_status")).toBe(0);
    expect(e.band()?.locked).toBe("restart");
    expect(e.band()?.lockLabel).toBe("복원하는 중이에요");
    e.book.onAppEvent("restore-progress", { phase: "done" });
    await e.book.restart();
    expect(e.count("start_master")).toBe(1);
  });
  it("자동 1회가 복원 중에 걸리면 기다림 띠에 갇히지 않고 실패 안내(호출 0)", async () => {
    const e = new Env(dead);
    e.startPlan = async (_n, env) => {
      env.emit("role.claim_denied", null, { role: "master", path: "surface.create", seat_blocked: "seat_not_claimable" });
      throw DENIED_ERR;
    };
    e.observe();
    await e.book.restart();
    e.book.onAppEvent("restore-progress", { phase: "start" });
    await e.advance(RETRY_DELAY_MS + 1);
    expect(e.count("start_master")).toBe(1);
    expect(e.book.view().phase.kind).toBe("restartfail");
  });
  it("관문 보류(start_master 관문 오류) → 다시 켜는 중을 풀고 행의 gate_pending 으로 관문 띠", async () => {
    const e = new Env(dead);
    e.startPlan = async (_n, env) => {
      env.spawnMaster({ agent_alive: null, agent_seen: false, gate_pending: { gate: "trust", since: 1 } });
      throw GATE_ERR;
    };
    e.observe();
    await e.book.restart();
    e.observe();
    expect(e.book.view().phase.kind).toBe("rest");
    expect(e.band()?.key).toBe("gate");
    e.book.answerGate();
    expect(e.views).toEqual(["work"]);
    expect(e.focused).toEqual([100]);
    expect(e.hints.at(-1)).toContain("No, exit");
    e.rows[e.rows.length - 1].gate_pending = null; // 통과
    e.rows[e.rows.length - 1].agent_alive = true;
    e.observe();
    expect(e.band()).toBe(null);
  });
  it("성공 신호 없음(120초) → 실패 안내 · 고장 난 빈 셸(새 좌석 · 에이전트 모름)은 성공 아님", async () => {
    const e = new Env(dead);
    e.startPlan = async (_n, env) => env.spawnMaster({ agent_alive: null, agent_seen: false, seat: "occupied" });
    e.observe();
    await e.book.restart();
    e.observe();
    expect(e.book.view().phase.kind).toBe("restarting");
    await e.advance(120_000);
    expect(e.book.view().phase.kind).toBe("restartfail");
  });
  it("boot-degraded: 이 화면이 다시 켠 뒤 5분 안 = 「팀 준비가 덜 됐어요」 · 다시 켠 적 없음 = 무시", async () => {
    const e = new Env(dead);
    e.observe();
    await e.book.restart();
    e.observe();
    e.book.onAppEvent("boot-degraded", "fallback");
    expect(e.band()?.title).toBe("마스터는 켜졌지만 팀 준비가 덜 됐어요.");
    const f = new Env(base);
    f.observe();
    f.book.onAppEvent("boot-degraded", "fallback");
    expect(f.band()).toBe(null);
  });
  it("실패(그 밖 오류) → 「다시 켜지 못했어요」 + 도움 요청(기존 피드백 창)", async () => {
    const e = new Env(dead);
    e.startPlan = async () => {
      throw "cys sidecar missing";
    };
    e.observe();
    await e.book.restart();
    expect(e.band()?.title).toBe("마스터를 다시 켜지 못했어요.");
    e.book.help();
    expect(e.helps).toBe(1);
  });
});

describe("깨우기(§6-1)", () => {
  it("조용함 사건 → 깨우기 띠 → 깨움 말 1건(kind auto · 원문) + 추적 · 깨어나면(일 시작) 띠 없음", async () => {
    const e = new Env(base);
    e.observe();
    e.emit("master.idle", 5, { role: "master", axis: "silence", idle_secs: 900 });
    e.rows[0].idle_secs = 900;
    e.observe();
    expect(e.band()?.key).toBe("idle");
    await e.book.wake();
    const c = e.calls.find((x) => x.cmd === "chat_send");
    expect(c?.args).toEqual({ socket: null, surfaceId: 5, text: WAKE_TEXT, kind: "auto" });
    expect(e.tracked.length).toBe(1);
    expect(e.band()?.key).toBe("waking");
    e.rows[0].working = true;
    e.observe();
    expect(e.band()).toBe(null);
  });
  it("사람 보내기 뒤 30초 묶임 동안은 기다렸다 보냄(R3) · 그 사이 다시 눌러도 1건", async () => {
    const e = new Env(base);
    e.observe();
    e.emit("master.idle", 5, { role: "master" });
    e.hold = 20_000;
    await e.book.wake();
    expect(e.count("chat_send")).toBe(0);
    expect(e.band()?.key).toBe("wake_wait");
    await e.book.wake();
    await e.advance(20_000);
    expect(e.count("chat_send")).toBe(1);
  });
  it("120초 안에 안 깨어남 → 실패 안내에 「마스터 다시 켜기」 + 「도움 요청」 함께 · 다시 켜기 누르면 start_master", async () => {
    const e = new Env(base);
    e.rows[0].idle_secs = 900;
    e.observe();
    e.emit("master.idle", 5, { role: "master" });
    await e.book.wake();
    await e.advance(WAKE_TIMEOUT_MS - 1);
    e.rows[0].idle_secs = 900 + 120;
    e.observe();
    expect(e.band()?.key).toBe("waking");
    await e.advance(1);
    expect(e.band()?.key).toBe("wakefail");
    expect(e.band()?.buttons).toEqual(["restart", "help"]);
    await e.book.restart();
    expect(e.count("start_master")).toBe(1);
  });
  it("5분 안 다시 깨우기 = 깨움 말을 또 보내지 않음 · 5분 뒤 = 1건 더", async () => {
    const e = new Env(base);
    e.rows[0].idle_secs = 900;
    e.observe();
    e.emit("master.idle", 5, { role: "master" });
    await e.book.wake();
    await e.advance(WAKE_TIMEOUT_MS);
    await e.book.wake();
    expect(e.count("chat_send")).toBe(1);
    await e.advance(WAKE_DEDUPE_MS);
    e.book.dismiss();
    await e.book.wake();
    expect(e.count("chat_send")).toBe(2);
  });
  it("깨움 말 큐 거부(failed) → 바로 실패 안내(다시 켜기 길)", async () => {
    const e = new Env(base);
    e.observe();
    const orig = e.invoke.bind(e);
    e.invoke = async (cmd, args) => (cmd === "chat_send" ? (e.calls.push({ cmd, args }), { outcome: "failed", code: "queue_full" }) : orig(cmd, args));
    e.emit("master.idle", 5, { role: "master" });
    await e.book.wake();
    expect(e.band()?.key).toBe("wakefail");
  });
});

describe("S1-5 — 내 보내기 짝짓기(human_input_seq)", () => {
  const m = (o: Partial<MasterRow>): MasterRow => ({ surface_id: 5, exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: 3, working: false, human_input_seq: 7, ...o });
  it("행의 차례 = 내 마지막 원자 제출 차례 → 30초 쉼 없음 · 다르면(다른 길 입력) 붙잡음 · 모름 = 붙잡음", () => {
    expect(sendGate({ master: m({}), approvalSeats: [], ownHumanSeq: 7 })).toEqual({ ok: true });
    expect(sendGate({ master: m({ human_input_seq: 8 }), approvalSeats: [], ownHumanSeq: 7 })).toMatchObject({ ok: false, code: "human_recent" });
    expect(sendGate({ master: m({ human_input_seq: null }), approvalSeats: [], ownHumanSeq: 7 })).toMatchObject({ ok: false, code: "human_recent" });
    expect(sendGate({ master: m({}), approvalSeats: [], ownHumanSeq: null })).toMatchObject({ ok: false, code: "human_recent" });
    expect(sendGate({ master: m({}), approvalSeats: [] })).toMatchObject({ ok: false, code: "human_recent" });
    expect(ownLastHumanInput(m({ human_input_seq: 0 }), 0)).toBe(false);
    // 짝짓기는 30초 쉼만 면제 — 입력줄 잔존·바쁨은 그대로 막는다
    expect(sendGate({ master: m({ pending_input_human_bytes: 2 }), approvalSeats: [], ownHumanSeq: 7 })).toMatchObject({ ok: false, code: "draft" });
    expect(sendGate({ master: m({ working: true }), approvalSeats: [], ownHumanSeq: 7 })).toMatchObject({ ok: false, code: "busy" });
  });
  it("masterRowOf 가 새 칸(human_input_seq · agent · agent_seen · seat)을 읽는다 · 옛 데몬(칸 없음) = null", () => {
    const r = masterRowOf({ surfaces: [{ surface_id: 5, role: "master", human_input_seq: 3, agent: "claude", agent_seen: false, seat: "empty" }] }, () => false);
    expect(r).toMatchObject({ human_input_seq: 3, agent: "claude", agent_seen: false, seat: "empty" });
    const o = masterRowOf({ surfaces: [{ surface_id: 5, role: "master" }] }, () => false);
    expect(o).toMatchObject({ human_input_seq: null, agent: null, agent_seen: null, seat: null });
  });
});

describe("정적 핀 — 다시 켜기 = 기존 입력줄 쓰기 0 · 깨움 말 길 1곳", () => {
  const src = readFileSync(new URL("./revive.ts", import.meta.url), "utf8").replace(/\/\/.*$/gm, "");
  it("revive.ts 의 invoke = org_status · start_master · close_surface · chat_send(auto) 만", () => {
    const cmds = [...src.matchAll(/invoke\("([a-z_]+)"/g)].map((x) => x[1]).sort();
    expect([...new Set(cmds)]).toEqual(["chat_send", "close_surface", "org_status", "start_master"]);
    expect(src.split('"chat_send"').length - 1).toBe(1);
    expect(src).toContain('kind: "auto"');
    for (const w of ["send_input", "send_text", "send_key"]) expect(src.includes(w)).toBe(false);
  });
  it("viewcore.rs 깨움 말 = 큐 · 기계 표지 · operator_token 0", () => {
    const rs = readFileSync(new URL("../../../src-tauri/src/viewcore.rs", import.meta.url), "utf8");
    const f = rs.indexOf("pub(crate) fn auto_send_params(");
    const body = rs.slice(f, rs.indexOf("\n}\n", f));
    for (const k of ['"queued": true', '"machine_origin": true', '"human": false']) expect(body).toContain(k);
    expect(body.includes("operator_token")).toBe(false);
  });
});
