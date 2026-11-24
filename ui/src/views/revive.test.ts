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
  RESTART_TIMEOUT_MS,
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
  wokeUp,
  AUTH_RULES,
  LIMIT_LOGIN_BANDS,
  LIMIT_STALE_SECS,
  STALL_EVENT_MS,
  pickStall,
  resetClock,
  usageLimit,
  type ReviveFacts,
} from "./judge/revive";

type Row = Record<string, unknown> & { surface_id: number };
/** 부분 대조(bun-env 매처 선언에 toMatchObject 없음 — tsc) — 기대 객체의 칸만 골라 toEqual. */
const pick = (o: unknown, e: Record<string, unknown>) => Object.fromEntries(Object.keys(e).map((k) => [k, (o as Record<string, unknown> | null)?.[k]]));

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
    created_at: 1000 + sid,
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
  /** 데몬 조건부 닫기가 닫는 순간 다시 본 사실(앱 조회 뒤 바뀜) — 거절 사유 */
  closeRefuse: string | null = null;
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
    if (cmd === "close_surface_if_quiet") {
      if (this.closeFails) throw new Error("close_denied");
      // 데몬 조건부 닫기 대역 — 생성 시각 · 입력줄 사람 바이트 · 붙여넣기 · 30초 안 사람 입력을 닫기 순간에 다시 본다(handlers.rs surface.close if_quiet)
      const sid = args?.surfaceId;
      const r = this.rows.find((x) => x.surface_id === sid);
      if (!r) throw new Error("not_found: surface not found");
      const why =
        r.created_at !== args?.expectedCreatedAt ? "created_at_mismatch"
        : this.closeRefuse ?? (r.pending_input_human_bytes !== 0 ? "input_line_has_human_draft" : r.input_paste_open !== false ? "paste_open" : (r.human_idle_secs === undefined || (typeof r.human_idle_secs === "number" && r.human_idle_secs < 30)) ? "recent_human_input" : null);
      if (why) throw new Error(`close_refused: surface.close if_quiet refused: ${why} · not closed`);
      this.rows = this.rows.filter((x) => x.surface_id !== sid);
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
    expect(pick(reviveSituation(mk({ master: live({ agent_alive: false }) })), { kind: "down", down: "agent" })).toEqual({ kind: "down", down: "agent" }); // 사건 없이 행만
  });
  it("agent_never_started(사건) · 행 증거 90초 지속 → 「마스터가 아직 시작하지 못했어요」 · 90초 전 = ok", () => {
    const nev = live({ agent_alive: null, agent_seen: false, seat: "empty" });
    expect(pick(reviveSituation(mk({ master: nev, dead: { sid: 5, axis: "agent_never_started" } })), { kind: "down", down: "never", sid: 5 })).toEqual({ kind: "down", down: "never", sid: 5 });
    expect(reviveSituation(mk({ master: nev, neverSince: 0, now: NEVER_STARTED_MS - 1 })).kind).toBe("ok");
    expect(pick(reviveSituation(mk({ master: nev, neverSince: 0, now: NEVER_STARTED_MS })), { kind: "down", down: "never" })).toEqual({ kind: "down", down: "never" });
    expect(reviveSituation(mk({ master: live({ agent_alive: null, agent_seen: false, seat: "occupied" }), neverSince: 0, now: 1e9 })).kind).toBe("ok"); // 기동 중(Occupied) = 아님
  });
  it("vacant: 마스터 행 없음 ∧ (본 적 있음 ∨ 놓아짐 기록) → 「마스터가 멈춰 있어요」 · 새 설치 = none(꺼짐이라 하지 않음)", () => {
    expect(pick(reviveSituation(mk({ seenBefore: true })), { kind: "down", down: "vacant" })).toEqual({ kind: "down", down: "vacant" });
    expect(pick(reviveSituation(mk({ goneMark: true })), { kind: "down", down: "vacant" })).toEqual({ kind: "down", down: "vacant" });
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
    // (실물 ⑤ 멱등 재사용) 다른 축도 옛 마스터 창에 사람 초안이 있으면 켜지 않음
    expect(restartPlan({ kind: "down", down: "agent", axis: "agent_dead", sid: 5 }, live({ pending_input_human_bytes: 2 }))).toEqual({ kind: "draft_block", sid: 5 });
    expect(restartPlan({ kind: "down", down: "agent", axis: "agent_dead", sid: 5 }, live({ input_paste_open: true }))).toEqual({ kind: "draft_block", sid: 5 });
    expect(restartPlan({ kind: "down", down: "vacant", axis: "vacant", sid: null }, null)).toEqual({ kind: "start" });
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
    expect(restartSucceeded(5, live(), true)).toBe(false); // 같은 좌석 · 전에도 생존 = 아님
    expect(restartSucceeded(5, live({ surface_id: 9, agent_alive: null }))).toBe(false);
    expect(restartSucceeded(5, live({ surface_id: 9, gate_pending: { gate: "x" } }))).toBe(false);
    expect(restartSucceeded(null, live({ surface_id: 9 }))).toBe(true);
    // (실물 ⑤) 같은 좌석 되살림 = 전에 생존 아니었으면 성공 · 전에도 생존이었으면 아님
    expect(restartSucceeded(5, live(), false)).toBe(true);
    expect(restartSucceeded(5, live(), true)).toBe(false);
    expect(restartSucceeded(5, live({ agent_alive: null }), false)).toBe(false);
  });
  it("옛 빈 셸 정리 대상 = 역할 없음 ∧ Empty ∧ 사람 입력 0 ∧ 최근 사람 입력 없음", () => {
    const org = (o: Partial<Row>) => ({ surfaces: [row(5, null, { seat: "empty", agent_alive: null, ...o })] });
    expect(leftoverShell(org({}), { sid: 5, created_at: 1005 }, 9)).toBe(5);
    expect(leftoverShell(org({ role: "master" }), { sid: 5, created_at: 1005 }, 9)).toBe(null);
    expect(leftoverShell(org({ agent: null }), { sid: 5, created_at: 1005 }, 9)).toBe(null); // 사용자가 연 맨 셸(번호 재사용) = 닫지 않음
    expect(leftoverShell(org({ seat: "occupied" }), { sid: 5, created_at: 1005 }, 9)).toBe(null);
    expect(leftoverShell(org({ pending_input_human_bytes: 1 }), { sid: 5, created_at: 1005 }, 9)).toBe(null);
    expect(leftoverShell(org({ human_idle_secs: 3 }), { sid: 5, created_at: 1005 }, 9)).toBe(null);
    expect(leftoverShell(org({ human_idle_secs: 40 }), { sid: 5, created_at: 1005 }, 9)).toBe(5);
    expect(leftoverShell(org({ exited: true }), { sid: 5, created_at: 1005 }, 9)).toBe(null);
    expect(leftoverShell(org({}), { sid: 9, created_at: 1005 }, 9)).toBe(null);
    expect(leftoverShell(org({}), null, 9)).toBe(null);
    expect(leftoverShell(org({}), { sid: 5, created_at: 1 }, 9)).toBe(null); // 같은 번호 · 다른 좌석(생성 시각 다름)
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
    expect(e.count("close_surface_if_quiet")).toBe(0);
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
      expect(`${axis}:${e.count("start_master")}:${e.count("close_surface_if_quiet")}:${e.seatWrites()}:${e.book.view().phase.kind}`).toBe(`${axis}:1:${axis === "surface_exited" ? 0 : 0}:0:rest`);
      expect(e.roles("cso")).toBe(1);
      expect(e.roles("worker")).toBe(2);
    }
  });
  it("agent_never_started → 옛 좌석 사람 입력 0 확인 → close_surface_if_quiet(그 좌석 · 생성 시각) 다음 start_master(순서) · 쓰기 0", async () => {
    const e = new Env(base);
    Object.assign(e.rows[0], { agent_alive: null, agent_seen: false, seat: "empty" });
    e.emit("master.deadman", 5, { role: "master", axis: "agent_never_started" });
    e.observe();
    expect(e.band()?.title).toBe("마스터가 아직 시작하지 못했어요.");
    await e.book.restart();
    const seq = e.calls.filter((c) => c.cmd === "close_surface_if_quiet" || c.cmd === "start_master").map((c) => `${c.cmd}:${c.args?.surfaceId ?? ""}:${c.args?.expectedCreatedAt ?? ""}`);
    expect(seq).toEqual(["close_surface_if_quiet:5:1005", "start_master::"]);
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
    expect(e.count("close_surface_if_quiet") + e.count("start_master")).toBe(0);
    expect(e.band()?.title).toBe("그 창에 쓰다 만 글이 있어요.");
    expect(e.band()?.buttons).toContain("work");
    e.book.toWork();
    expect(e.views).toEqual(["work"]);
  });
  it("never_started — 앱 판정 통과 뒤 데몬이 조건부 닫기를 거절(그 사이 사람 입력) → 닫지 않음 · start_master 0 · 쓰다 만 글 안내", async () => {
    for (const why of ["recent_human_input", "input_line_has_human_draft", "paste_open"]) {
      const e = new Env(base);
      Object.assign(e.rows[0], { agent_alive: null, agent_seen: false, seat: "empty" });
      e.closeRefuse = why;
      e.emit("master.deadman", 5, { role: "master", axis: "agent_never_started" });
      e.observe();
      await e.book.restart();
      expect(`${why}:${e.count("close_surface_if_quiet")}:${e.count("start_master")}:${e.rows.some((r) => r.surface_id === 5)}`).toBe(`${why}:1:0:true`);
      expect(e.band()?.title).toBe("그 창에 쓰다 만 글이 있어요.");
    }
  });
  it("never_started — 다시 받은 행에 생성 시각이 없음(신원 모름) → 닫기 호출 0 · start_master 0 · 실패 안내", async () => {
    const e = new Env(base);
    Object.assign(e.rows[0], { agent_alive: null, agent_seen: false, seat: "empty", created_at: undefined });
    e.emit("master.deadman", 5, { role: "master", axis: "agent_never_started" });
    e.observe();
    await e.book.restart();
    expect(`${e.count("close_surface_if_quiet")}:${e.count("start_master")}:${e.book.view().phase.kind}`).toBe("0:0:restartfail");
  });
  it("never_started — 생성 시각 다름(그 사이 데몬 다시 켜져 번호 재사용) = 데몬 거절 → 닫지 않음 · 실패 안내 · start_master 0", async () => {
    const e = new Env(base);
    Object.assign(e.rows[0], { agent_alive: null, agent_seen: false, seat: "empty" });
    e.closeRefuse = "created_at_mismatch";
    e.emit("master.deadman", 5, { role: "master", axis: "agent_never_started" });
    e.observe();
    await e.book.restart();
    expect(e.count("start_master")).toBe(0);
    expect(e.rows.some((r) => r.surface_id === 5)).toBe(true);
    expect(e.book.view().phase.kind).toBe("restartfail");
  });
  it("vacant(회수 뒤 · 앱 새로 켬 · 저장소에 본 적 있음) → 꺼짐 띠 즉시 → start_master → 성공 뒤 옛 빈 셸 정리(사람 입력 0)", async () => {
    const e = new Env((x) => {
      x.store.set(SEEN_KEY, JSON.stringify({ sid: 5, created_at: 1005 }));
      x.rows = [row(5, null, { agent_alive: null, seat: "empty" }), row(6, "cso"), row(7, "worker")];
    });
    e.observe(); // 앱을 새로 켠 첫 조회 — 지난 deadman 은 못 받음
    expect(e.band()?.title).toBe("마스터가 멈춰 있어요.");
    await e.book.restart();
    expect(e.count("start_master")).toBe(1);
    e.observe();
    await e.flush();
    expect(e.calls.filter((c) => c.cmd === "close_surface_if_quiet").map((c) => `${c.args?.surfaceId}:${c.args?.expectedCreatedAt}`)).toEqual(["5:1005"]);
    expect(JSON.parse(e.store.get(SEEN_KEY) ?? "null")).toEqual({ sid: 100, created_at: 1100 });
    expect(e.roles("cso")).toBe(1);
    expect(e.seatWrites()).toBe(0);
  });
  it("(master#fe289e63) vacant → 다시 켜기 → 같은 좌석 에이전트는 살아났는데 역할 없음(멱등 재반환 · 역할 회수 뒤) = 성공 아님 · 시간 지나 실패 안내 · 옛 셸 정리 0", async () => {
    const e = new Env((x) => {
      x.store.set(SEEN_KEY, JSON.stringify({ sid: 5, created_at: 1005 }));
      x.rows = [row(5, null, { agent_alive: null, seat: "empty" }), row(6, "cso")];
    });
    e.startPlan = async (_n, env) => {
      Object.assign(env.rows[0], { agent_alive: true, seat: "occupied", agent_seen: true }); // 역할 없이 되살아남(데몬 결함 꼴)
    };
    e.observe();
    expect(e.band()?.key).toBe("down_vacant");
    await e.book.restart();
    e.observe();
    expect(e.book.view().phase.kind).toBe("restarting"); // role=master 행이 없으면 성공 아님(좌석 id·생존만으로 판정하지 않는다)
    await e.advance(RESTART_TIMEOUT_MS + 1000);
    e.observe();
    expect(e.book.view().phase.kind).toBe("restartfail");
    expect(e.count("close_surface_if_quiet")).toBe(0);
    // 역할을 다시 쥐면(데몬 고침 꼴) 그때 성공
    const g = new Env((x) => {
      x.store.set(SEEN_KEY, JSON.stringify({ sid: 5, created_at: 1005 }));
      x.rows = [row(5, null, { agent_alive: null, seat: "empty" }), row(6, "cso")];
    });
    g.startPlan = async (_n, env) => {
      Object.assign(env.rows[0], { role: "master", agent_alive: true, seat: "occupied", agent_seen: true });
    };
    g.observe();
    await g.book.restart();
    g.observe();
    expect(g.book.view().phase.kind).toBe("rest");
  });
  it("vacant 정리 — 저장 신원의 생성 시각이 다르면(데몬 다시 켜져 번호 재사용) · 옛 꼴(번호만)이면 닫지 않는다", async () => {
    for (const seen of [JSON.stringify({ sid: 5, created_at: 999 }), "5"]) {
      const e = new Env((x) => {
        x.store.set(SEEN_KEY, seen);
        x.rows = [row(5, null, { agent_alive: null, seat: "empty" }), row(6, "cso")];
      });
      e.observe();
      expect(e.band()?.key).toBe("down_vacant");
      await e.book.restart();
      e.observe();
      await e.flush();
      expect(`${seen}:${e.count("close_surface_if_quiet")}`).toBe(`${seen}:0`);
    }
  });
  it("vacant 정리 — 옛 빈 셸에 사람 입력이 있으면 닫지 않는다", async () => {
    const e = new Env((x) => {
      x.store.set(SEEN_KEY, JSON.stringify({ sid: 5, created_at: 1005 }));
      x.rows = [row(5, null, { agent_alive: null, seat: "empty", pending_input_human_bytes: 4 }), row(6, "cso")];
    });
    e.observe();
    await e.book.restart();
    e.observe();
    await e.flush();
    expect(e.count("close_surface_if_quiet")).toBe(0);
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

describe("codex 1R 고침", () => {
  const dead = (e: Env) => {
    base(e);
    e.rows[0].agent_alive = false;
  };
  it("관문 보류 뒤 관문 좌석이 보이기 전 다시 누름 → start_master 그대로 1(gate_wait 잠금) · 30초 뒤 풀림", async () => {
    const e = new Env(dead);
    e.startPlan = async () => {
      throw GATE_ERR;
    };
    e.observe();
    await e.book.restart();
    expect(e.book.view().phase.kind).toBe("gate_wait");
    expect(e.band()?.locked).toBe("restart");
    await e.book.restart();
    await e.book.restart();
    expect(e.count("start_master")).toBe(1);
    await e.advance(30_000);
    expect(e.book.view().phase.kind).toBe("rest");
  });
  it("복원 진행 = 앱 수명 값(deps.restoring · 대화 화면을 끈 동안 온 start 도) → 호출 0 · 잠금", async () => {
    let restoring = true;
    const e = new Env(dead);
    (e.book as unknown as { d: { restoring: () => boolean } }).d.restoring = () => restoring;
    e.observe();
    await e.book.restart();
    expect(e.count("start_master") + e.count("org_status")).toBe(0);
    expect(e.band()?.lockLabel).toBe("복원하는 중이에요");
    restoring = false;
    await e.book.restart();
    expect(e.count("start_master")).toBe(1);
  });
  it("등록 없는 마스터 좌석이 빈 셸로 90초 + 본 적 있음 → 꺼짐(seat_vacant_no_meta · 사건 없이) · 본 적 없음 = 아님", async () => {
    const mk = (seen: boolean) =>
      new Env((x) => {
        if (seen) x.store.set(SEEN_KEY, JSON.stringify({ sid: 5, created_at: 1005 }));
        x.rows = [row(5, "master", { agent: null, agent_alive: null, agent_seen: null, seat: "empty" })];
      });
    const a = mk(true);
    a.observe();
    expect(a.book.view().sit.kind).toBe("ok");
    a.now += NEVER_STARTED_MS;
    a.observe();
    expect(pick(a.book.view().sit, { kind: "down", down: "agent", axis: "seat_vacant_no_meta" })).toEqual({ kind: "down", down: "agent", axis: "seat_vacant_no_meta" });
    const b = mk(false);
    b.observe();
    b.now += NEVER_STARTED_MS * 2;
    b.observe();
    expect(b.book.view().sit.kind).toBe("ok");
  });
  it("(2R M3) 복원 start 뒤 화면을 내려 done 을 놓쳐도 앱 수명 값이 false 면 잠그지 않음", async () => {
    const e = new Env(dead);
    (e.book as unknown as { d: { restoring: () => boolean } }).d.restoring = () => false;
    e.observe();
    e.book.onAppEvent("restore-progress", { phase: "start" }); // done 을 못 받은 걸쇠
    await e.book.restart();
    expect(e.count("start_master")).toBe(1);
  });
  it("(2R M5) 빈 좌석 증거 종류가 바뀌면 90초를 새로 셈 · (2R minor) 다른 좌석 신원이면 등록 없는 빈 좌석 = 준비 중", () => {
    const e = new Env((x) => {
      x.store.set(SEEN_KEY, JSON.stringify({ sid: 5, created_at: 1005 }));
      x.rows = [row(5, "master", { agent: null, agent_alive: null, agent_seen: null, seat: "empty" })];
    });
    e.observe();
    e.now += NEVER_STARTED_MS - 1_000;
    Object.assign(e.rows[0], { agent: "claude", agent_seen: false }); // 등록됨 → never 증거로 바뀜
    e.observe();
    e.now += 2_000;
    e.observe();
    expect(e.book.view().sit.kind).toBe("ok"); // 합산이면 down 이었다
    e.now += NEVER_STARTED_MS;
    e.observe();
    expect(pick(e.book.view().sit, { kind: "down", down: "never" })).toEqual({ kind: "down", down: "never" });
    const f = new Env((x) => {
      x.store.set(SEEN_KEY, JSON.stringify({ sid: 5, created_at: 1 })); // 옛 데몬의 같은 번호
      x.rows = [row(5, "master", { agent: null, agent_alive: null, agent_seen: null, seat: "empty" })];
    });
    f.observe();
    f.now += NEVER_STARTED_MS * 2;
    f.observe();
    expect(f.book.view().sit.kind).toBe("ok");
  });
  it("옛 마스터 창에 30초 안 사람 입력 → 다시 켜지 않음(닫기·start 0) · 입력 시각 모름도 막음", async () => {
    for (const hi of [3, undefined]) {
      const e = new Env(dead);
      if (hi === undefined) delete e.rows[0].human_idle_secs;
      else e.rows[0].human_idle_secs = hi;
      e.observe();
      await e.book.restart();
      expect(`${hi}:${e.count("start_master")}:${e.book.view().phase.kind}`).toBe(`${hi}:0:draft_block`);
    }
  });
  it("깨움 5분 거름 = 앱을 다시 켜도(새 장부 · 같은 저장소) 유지", async () => {
    const e = new Env(base);
    e.observe();
    e.emit("master.idle", 5, { role: "master" });
    await e.book.wake();
    const store = e.store;
    const f = new Env((x) => {
      base(x);
      x.store = store;
      x.now = e.now + 60_000;
    });
    f.observe();
    f.emit("master.idle", 5, { role: "master" });
    await f.book.wake();
    expect(e.count("chat_send") + f.count("chat_send")).toBe(1);
  });
  it("(실물 ⑤) 자동 1회를 기다리는 동안 다른 길로 마스터가 살아남 → 기다림 거둠 · 자동 start_master 0", async () => {
    const e = new Env(dead);
    e.startPlan = async (_n, env) => {
      env.emit("role.claim_denied", null, { role: "master", path: "surface.create", seat_blocked: "seat_not_claimable", seat_human_recent: false });
      throw DENIED_ERR;
    };
    e.observe();
    await e.book.restart();
    expect(e.book.view().phase.kind).toBe("retry_wait");
    e.rows[0].agent_alive = true; // 데몬 쪽 자동 회생(같은 좌석)
    e.observe();
    expect(e.book.view().phase.kind).toBe("rest");
    await e.advance(RETRY_DELAY_MS * 3);
    expect(e.count("start_master")).toBe(1);
  });
  it("깨어남 판정 = 초 버림 보정(깨우기 직전 1초 안 옛 출력은 새 출력 아님)", () => {
    const m = masterRowOf({ surfaces: [row(5, "master", { idle_secs: 3 })] }, () => false) as MasterRow;
    expect(wokeUp(m, 0, 3_050)).toBe(false);
    expect(wokeUp(m, 0, 4_100)).toBe(true);
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

describe("S1-5 — 내 보내기 짝짓기(human_input_stamp)", () => {
  const m = (o: Partial<MasterRow>): MasterRow => ({ surface_id: 5, exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: 3, working: false, human_input_stamp: "1794:7", ...o });
  it("행의 차례 = 내 마지막 원자 제출 차례 → 30초 쉼 없음 · 다르면(다른 길 입력) 붙잡음 · 모름 = 붙잡음", () => {
    expect(sendGate({ master: m({}), approvalSeats: [], ownHumanStamp: "1794:7" })).toEqual({ ok: true });
    expect(pick(sendGate({ master: m({ human_input_stamp: "1794:8" }), approvalSeats: [], ownHumanStamp: "1794:7" }), { ok: false, code: "human_recent" })).toEqual({ ok: false, code: "human_recent" });
    expect(pick(sendGate({ master: m({ human_input_stamp: null }), approvalSeats: [], ownHumanStamp: "1794:7" }), { ok: false, code: "human_recent" })).toEqual({ ok: false, code: "human_recent" });
    expect(pick(sendGate({ master: m({}), approvalSeats: [], ownHumanStamp: null }), { ok: false, code: "human_recent" })).toEqual({ ok: false, code: "human_recent" });
    expect(pick(sendGate({ master: m({}), approvalSeats: [] }), { ok: false, code: "human_recent" })).toEqual({ ok: false, code: "human_recent" });
    expect(ownLastHumanInput(m({ human_input_stamp: "" }), "")).toBe(false);
    expect(ownLastHumanInput(m({ human_input_stamp: "1799:7" }), "1794:7")).toBe(false); // 데몬 다시 켜짐(세대 다름) = 아님
    // 짝짓기는 30초 쉼만 면제 — 입력줄 잔존·바쁨은 그대로 막는다
    expect(pick(sendGate({ master: m({ pending_input_human_bytes: 2 }), approvalSeats: [], ownHumanStamp: "1794:7" }), { ok: false, code: "draft" })).toEqual({ ok: false, code: "draft" });
    expect(pick(sendGate({ master: m({ working: true }), approvalSeats: [], ownHumanStamp: "1794:7" }), { ok: false, code: "busy" })).toEqual({ ok: false, code: "busy" });
  });
  it("masterRowOf 가 새 칸(human_input_stamp · agent · agent_seen · seat)을 읽는다 · 옛 데몬(칸 없음) = null", () => {
    const r = masterRowOf({ surfaces: [{ surface_id: 5, role: "master", human_input_stamp: "1794:3", agent: "claude", agent_seen: false, seat: "empty" }] }, () => false);
    expect(pick(r, { human_input_stamp: "1794:3", agent: "claude", agent_seen: false, seat: "empty" })).toEqual({ human_input_stamp: "1794:3", agent: "claude", agent_seen: false, seat: "empty" });
    const o = masterRowOf({ surfaces: [{ surface_id: 5, role: "master" }] }, () => false);
    expect(pick(o, { human_input_stamp: null, agent: null, agent_seen: null, seat: null })).toEqual({ human_input_stamp: null, agent: null, agent_seen: null, seat: null });
  });
});

describe("정적 핀 — 다시 켜기 = 기존 입력줄 쓰기 0 · 깨움 말 길 1곳", () => {
  const src = readFileSync(new URL("./revive.ts", import.meta.url), "utf8").replace(/\/\/.*$/gm, "");
  it("revive.ts 의 invoke = org_status · start_master · close_surface_if_quiet · chat_send(auto) 만 · 무조건 닫기(close_surface) 0", () => {
    const cmds = [...src.matchAll(/invoke\("([a-z_]+)"/g)].map((x) => x[1]).sort();
    expect([...new Set(cmds)]).toEqual(["chat_send", "close_surface_if_quiet", "org_status", "start_master"]);
    expect(src.match(/"close_surface"/g)).toBeNull();
    expect(src.split('"close_surface_if_quiet"').length - 1).toBe(2);
    expect(src.match(/expectedCreatedAt: seat\.created_at/g)?.length).toBe(2);
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

// ---------- (BA1 · TICKET=cysr-1119-s8) 멈춘 까닭 — 한도 · 로그인(DESIGN §7 BA1 · 카드 BORROW §3-1 A1) ----------
describe("BA1 멈춘 까닭 — 진리표(judge/revive · 순수)", () => {
  const T = 1_800_000_000_000; // 기준 시각(ms)
  const mk = (over: Partial<ReviveFacts>): ReviveFacts => ({ master: null, seenBefore: true, goneMark: false, dead: null, neverSince: null, idle: null, now: T, ...over });
  const live = (over: Partial<MasterRow> = {}): MasterRow => ({ surface_id: 5, exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false, idle_secs: 1, agent: "claude", agent_seen: true, seat: "occupied", ...over });
  const use = (pct: number, resetsAtMs: number | null, age: number | null = 10) => ({ rate: [{ label: "5h", used_pct: pct, resets_at: resetsAtMs === null ? null : resetsAtMs / 1000 }, { label: "7d", used_pct: 40, resets_at: (T + 5 * 86_400_000) / 1000 }], rate_age_secs: age });
  const lim = (pct: number, r: number | null, age: number | null = 10) => usageLimit(use(pct, r, age), T);
  const login = { rule: "not_logged_in", at: T - 1000 };

  it("한도 읽기 — 100%∧리셋 미래 = limited · 리셋 지남 = 아님 · 99% = 아님 · 30분 넘게 낡음/나이 모름 = 판정 안 함", () => {
    expect(lim(100, T + 3_600_000)).toEqual({ state: "limited", resetsAt: T + 3_600_000 });
    expect(lim(100, T - 1)).toEqual({ state: "fresh" }); // 5h 는 이미 리셋 · 7d 40% 만 남음
    expect(lim(99, T + 3_600_000)).toEqual({ state: "fresh" });
    expect(lim(100, T + 3_600_000, LIMIT_STALE_SECS + 1)).toEqual({ state: "none" }); // 거짓 띠 0
    expect(lim(100, T + 3_600_000, LIMIT_STALE_SECS)).toEqual({ state: "limited", resetsAt: T + 3_600_000 }); // 문턱 = 30분 포함
    expect(lim(100, T + 3_600_000, null)).toEqual({ state: "none" });
    expect(usageLimit(null, T)).toEqual({ state: "none" });
    expect(usageLimit({ rate: [], rate_age_secs: 5 }, T)).toEqual({ state: "none" });
    expect(lim(100, null)).toEqual({ state: "limited", resetsAt: null }); // 리셋 모름
    // 둘 다 100% = 늦은 리셋(그때까지 못 움직임)
    expect(usageLimit({ rate: [{ used_pct: 100, resets_at: (T + 3_600_000) / 1000 }, { used_pct: 100, resets_at: (T + 2 * 86_400_000) / 1000 }], rate_age_secs: 1 }, T)).toEqual({ state: "limited", resetsAt: T + 2 * 86_400_000 });
  });

  it("까닭 고르기 — 로그인 300초 안/밖 · 로그인 > 한도 · rate_limited 사건은 수치가 없을 때만", () => {
    const L = lim(100, T + 3_600_000);
    expect(pickStall(login, { state: "none" }, null, T)).toEqual({ why: "login", rule: "not_logged_in" });
    expect(pickStall({ rule: "auth_401", at: T - STALL_EVENT_MS + 1 }, { state: "none" }, null, T)).toEqual({ why: "login", rule: "auth_401" });
    expect(pickStall({ rule: "auth_401", at: T - STALL_EVENT_MS }, { state: "none" }, null, T)).toBe(null); // 300초 = 밖
    expect(pickStall(login, L, null, T)).toEqual({ why: "login", rule: "not_logged_in" }); // 로그인 + 한도 = 로그인
    expect(pickStall(null, L, null, T)).toEqual({ why: "limit", resetsAt: T + 3_600_000 });
    expect(pickStall(null, { state: "fresh" }, T - 1000, T)).toBe(null); // 신선한 수치 99% + rate_limited 사건 = 아님(수치가 이긴다)
    expect(pickStall(null, { state: "none" }, T - 1000, T)).toEqual({ why: "limit", resetsAt: null }); // 수치 없음 + 사건 = 한도(리셋 모름)
    expect(pickStall(null, { state: "none" }, T - STALL_EVENT_MS, T)).toBe(null);
  });

  it("사정 진리표 — 관문 > 꺼짐 > 로그인 > 한도 > 조용함 > 이상 없음", () => {
    const S_LOGIN = { why: "login", rule: "not_logged_in" } as const;
    const S_LIMIT = { why: "limit", resetsAt: T + 3_600_000 } as const;
    const idle = { sid: 5, at: T - 1000 };
    const cases: Array<[string, Partial<ReviveFacts>, string]> = [
      ["한도만", { master: live(), stall: S_LIMIT }, "limited"],
      ["로그인만", { master: live(), stall: S_LOGIN }, "login"],
      ["조용함 + 한도", { master: live(), stall: S_LIMIT, idle }, "limited"],
      ["조용함 + 로그인", { master: live(), stall: S_LOGIN, idle }, "login"],
      ["꺼짐 + 한도", { master: live({ agent_alive: false }), stall: S_LIMIT }, "down"],
      ["꺼짐(사건) + 로그인", { master: live({ agent_alive: null }), dead: { sid: 5, axis: "agent_dead" }, stall: S_LOGIN }, "down"],
      ["창 닫힘 + 한도", { master: null, dead: { sid: 5, axis: "surface_gone" }, stall: S_LIMIT }, "down"],
      ["관문 + 로그인", { master: live({ gate_pending: { kind: "trust" } }), stall: S_LOGIN }, "gate"],
      ["관문 + 한도", { master: live({ gate_pending: { kind: "trust" } }), stall: S_LIMIT }, "gate"],
      ["조용함만", { master: live(), idle }, "idle"],
      ["까닭 없음", { master: live(), stall: null }, "ok"],
      ["조회 실패 + 한도", { master: undefined, stall: S_LIMIT }, "unknown"],
    ];
    for (const [name, f, kind] of cases) expect([name, reviveSituation(mk(f)).kind]).toEqual([name, kind]);
    expect(reviveSituation(mk({ master: live(), stall: S_LIMIT }))).toEqual({ kind: "limited", sid: 5, resetsAt: T + 3_600_000 });
    expect(reviveSituation(mk({ master: live(), stall: S_LOGIN }))).toEqual({ kind: "login", sid: 5, rule: "not_logged_in" });
  });

  it("띠 — 한도 = 깨우기 단추 0 · 리셋 현지 HH:MM(24시간 넘으면 요일) · 로그인 = 작업 화면 단추 · 금지 말 0", () => {
    const hm = (ms: number) => { const d = new Date(ms); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; };
    const b1 = reviveBand({ kind: "limited", sid: 5, resetsAt: T + 3_600_000 }, { kind: "rest" }, false, T)!;
    expect(pick(b1, { key: "limited", tone: "wait", title: "마스터가 사용 한도에 닿아 쉬고 있어요." })).toEqual({ key: "limited", tone: "wait", title: "마스터가 사용 한도에 닿아 쉬고 있어요." });
    expect(b1.buttons).toEqual([]);
    expect(b1.buttons.includes("wake")).toBe(false);
    expect(b1.body).toBe(`${hm(T + 3_600_000)} 쯤 다시 움직여요. 보낸 말은 그때 차례대로 전달돼요.`);
    const far = T + 3 * 86_400_000;
    expect(resetClock(far, T)).toBe(`${["일", "월", "화", "수", "목", "금", "토"][new Date(far).getDay()]} ${hm(far)}`);
    expect(resetClock(T + 86_400_000, T)).toBe(hm(T + 86_400_000)); // 정확히 24시간 = HH:MM
    const b0 = reviveBand({ kind: "limited", sid: 5, resetsAt: null }, { kind: "rest" }, false, T)!;
    expect(b0.body).toBe("한도가 풀리면 다시 움직여요.");
    expect(b0.buttons).toEqual([]);
    const b2 = reviveBand({ kind: "login", sid: 5, rule: "auth_401" }, { kind: "rest" }, false, T)!;
    expect([b2.key, b2.tone, b2.title, b2.body, b2.buttons]).toEqual(["login", "err", "마스터가 다시 로그인해야 해요.", "작업 화면의 마스터 창에서 /login 을 입력해 주세요.", ["work"]]);
    for (const b of [b0, b1, b2]) for (const w of ["좌석", "데몬", "CTX", "surface", "세션", "토큰", "rate", "401"]) expect([w, `${b.title}${b.body}`.includes(w)]).toEqual([w, false]);
    // 눌러 둔 행동이 사정보다 앞선다(깨우는 중이면 그 띠)
    expect(reviveBand({ kind: "limited", sid: 5, resetsAt: null }, { kind: "waking", at: T }, false, T)?.key).toBe("waking");
  });

  it("되돌리기 상수 = 켜짐(판) · 룰 4개 = 데몬 AUTH_INTERLOCK_RULES 글자 그대로 · 창 = AUTH_INTERLOCK_WINDOW_SECS", () => {
    expect(LIMIT_LOGIN_BANDS).toBe(true);
    const st = readFileSync(new URL("../../../src/bin/cysd/state.rs", import.meta.url), "utf8");
    const m = st.match(/pub const AUTH_INTERLOCK_RULES: &\[&str\] =\s*&\[([^\]]*)\]/);
    expect(m).not.toBe(null);
    expect([...m![1].matchAll(/"([a-z0-9_]+)"/g)].map((x) => x[1])).toEqual([...AUTH_RULES]);
    expect(st).toContain(`pub const AUTH_INTERLOCK_WINDOW_SECS: f64 = ${STALL_EVENT_MS / 1000}.0;`);
    expect(st).toContain('"rate_limited",'); // 보조 룰 이름(내장 룰 표)
  });
});

describe("BA1 멈춘 까닭 — 장부(대역 데몬 · org.status usage · health.alert)", () => {
  const withUsage = (pct: number, resetIn: number | null, age: number | null = 5) => (e: Env) => {
    base(e);
    e.rows[0].usage = { rate: [{ label: "5h", used_pct: pct, resets_at: resetIn === null ? null : (e.now + resetIn) / 1000 }], rate_age_secs: age, rate_observed_at: e.now / 1000 - (age ?? 0) };
  };
  it("마스터 행 usage 100%∧리셋 미래 → 한도 띠(단추 0) · 다른 좌석 100% 는 무관", () => {
    const e = new Env(withUsage(100, 3_600_000));
    e.observe();
    expect(e.book.situation().kind).toBe("limited");
    expect(e.band()?.key).toBe("limited");
    expect(e.band()?.buttons).toEqual([]);
    const o = new Env(base);
    o.rows[2].usage = { rate: [{ used_pct: 100, resets_at: (o.now + 3_600_000) / 1000 }], rate_age_secs: 1 };
    o.observe();
    expect(o.book.situation().kind).toBe("ok");
  });
  it("조용함 사건 + 한도 = 한도 띠(깨우기 헛손 0) · 한도가 풀리면(99%) 조용함 띠로", () => {
    const e = new Env(withUsage(100, 3_600_000));
    e.observe();
    e.emit("master.idle", 5, { role: "master" });
    expect(e.band()?.key).toBe("limited");
    (e.rows[0].usage as { rate: Array<{ used_pct: number }> }).rate[0].used_pct = 99;
    e.observe();
    expect(e.band()?.key).toBe("idle");
  });
  it("알고 남긴 것(ADV D-05) — 한도로 멈춘 마스터는 수치 갱신이 끊겨 30분 뒤 판정 안 함 → 조용함 띠로 돌아감(값으로 고정 · 고치지 않음)", () => {
    const e = new Env(withUsage(100, 3 * 3_600_000, LIMIT_STALE_SECS + 1));
    e.observe();
    e.emit("master.idle", 5, { role: "master" });
    expect(e.band()?.key).toBe("idle");
  });
  it("health.alert 로그인 룰(마스터 좌석) → 로그인 띠 · 300초 뒤 사라짐 · 다른 좌석·다른 룰 = 무관", async () => {
    const e = new Env(base);
    e.observe();
    e.emit("health.alert", 7, { rule: "not_logged_in", line: "x", masked: true }); // 워커 좌석
    e.emit("health.alert", 5, { rule: "context_overflow", line: "x", masked: true }); // 다른 룰
    expect(e.book.situation().kind).toBe("ok");
    const ch = e.changes;
    e.emit("health.alert", 5, { rule: "not_logged_in", line: "x", masked: true });
    expect(e.changes).toBe(ch + 1); // 다시 그리기
    expect(e.book.situation()).toEqual({ kind: "login", sid: 5, rule: "not_logged_in" });
    expect(e.band()?.key).toBe("login");
    await e.advance(STALL_EVENT_MS - 1);
    expect(e.book.situation().kind).toBe("login");
    await e.advance(1);
    expect(e.book.situation().kind).toBe("ok");
  });
  it("rate_limited 사건 = 수치 없을 때만 한도(리셋 모름 글) · 수치가 신선하면 아님", () => {
    const e = new Env(base);
    e.observe();
    e.emit("health.alert", 5, { rule: "rate_limited", line: "x", masked: true });
    expect(e.band()?.body).toBe("한도가 풀리면 다시 움직여요.");
    const f = new Env(withUsage(40, 3_600_000));
    f.observe();
    f.emit("health.alert", 5, { rule: "rate_limited", line: "x", masked: true });
    expect(f.book.situation().kind).toBe("ok");
  });
  it("로그인 띠 「작업 화면에서 보기」 → 작업 화면 + 그 마스터 창 포커스 · 다른 띠의 작업 화면 단추는 포커스 0(1.1.18 그대로)", () => {
    const e = new Env(base);
    e.observe();
    e.emit("health.alert", 5, { rule: "token_expired" });
    e.book.toWork();
    expect([e.views, e.focused]).toEqual([["work"], [5]]);
    const g = new Env(base);
    g.observe();
    g.book.toWork();
    expect([g.views, g.focused]).toEqual([["work"], []]);
  });
  it("한도·로그인 띠에서 다시 켜기 = 아무것도 안 함(꺼짐 아님 · start_master 0)", async () => {
    const e = new Env(withUsage(100, 3_600_000));
    e.observe();
    await e.book.restart();
    e.emit("health.alert", 5, { rule: "login_required" });
    await e.book.restart();
    expect(e.count("start_master")).toBe(0);
  });
});
