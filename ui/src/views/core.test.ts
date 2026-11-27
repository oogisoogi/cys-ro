// (cysr-ui-slice1) 공통층 보내기 길 시험 — 대역 데몬(invoke 기록기) · 가짜 시계·타이머.
// 판정 단위 = 「PTY 쓰기 = chat_send 호출 수」(원자 제출 1요청 = 쓰기 1 · 데몬 거부는 바이트 0).
import { describe, it, expect } from "bun:test";
import { CHAT_TRANSCRIPT_CHANGED, ChatCore, HELD_MAX_AGE_MS, HELD_REFUSED_BACKOFF_MS, HOLD_KEY, HOLD_MAX, healthOf, LOG_MAX, OBS_MAX_MS, RESTORED, STALE, STALE_NOTE, type Deps } from "./core";
import { READ_AFTER_MS } from "./judge/msgstep";
import { masterRowOf } from "./judge/gate";
import { readFileSync } from "node:fs";

interface Call {
  cmd: string;
  args?: Record<string, unknown>;
}

function harness(o: { master?: Record<string, unknown> | null; approvals?: number[]; sendOutcome?: Record<string, unknown> | (() => Record<string, unknown>); orgFail?: boolean; feedFail?: boolean; transcript?: Array<Record<string, unknown>>; busyPasteOk?: boolean } = {}) {
  const calls: Call[] = [];
  const mem = new Map<string, string>();
  let now = 1_000_000;
  const timers: Array<{ at: number; fn: () => void; h: number }> = [];
  let hn = 0;
  const st = {
    master: o.master === undefined ? { surface_id: 5, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false } : o.master,
    approvals: o.approvals ?? [],
    sendOutcome: o.sendOutcome ?? { outcome: "written", result: { sent: true } },
    orgFail: o.orgFail ?? false,
    feedFail: o.feedFail ?? false,
    file: [] as Array<Record<string, unknown>>,
    session: "sess-0001-aaaa",
  };
  const deps: Deps = {
    invoke: async (cmd, args) => {
      calls.push({ cmd, args });
      if (cmd === "org_status") {
        if (st.orgFail) throw new Error("down");
        return { surfaces: st.master ? [st.master] : [] };
      }
      if (cmd === "feed_list") {
        if (st.feedFail) throw new Error("down");
        return { items: st.approvals.map((sid) => ({ kind: "approval", status: "pending", surface_id: sid })) };
      }
      if (cmd === "chat_send") return typeof st.sendOutcome === "function" ? st.sendOutcome() : st.sendOutcome;
      if (cmd === "chat_transcript") {
        const a = args as { afterOffset: number; fromEnd: boolean };
        if (a.fromEnd) return { status: "ok", session_id: st.session, next_offset: st.file.length, size: st.file.length, records: [] };
        const recs = st.file.slice(a.afterOffset);
        return { status: "ok", session_id: st.session, next_offset: st.file.length, size: st.file.length, records: recs };
      }
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
    busyPasteOk: o.busyPasteOk,
  };
  const flush = async () => {
    for (let i = 0; i < 20; i++) await Promise.resolve();
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
  const writes = () => calls.filter((c) => c.cmd === "chat_send");
  return { calls, mem, st, deps, flush, advance, writes, core: new ChatCore(deps), setNow: (n: number) => (now = n), getNow: () => now };
}

describe("보내기 1 → 쓰기 1(원자) — 쓰기 직전 재조회 1회", () => {
  it("문턱 통과 = chat_send 1건 · kind human · 마스터 좌석 · 앞서 org_status + feed_list", async () => {
    const h = harness();
    h.core.attach();
    await h.flush();
    h.calls.length = 0;
    await h.core.send("안녕");
    expect(h.writes()).toHaveLength(1);
    expect(h.writes()[0].args).toEqual({ socket: null, surfaceId: 5, text: "안녕", kind: "human" });
    const cmds = h.calls.map((c) => c.cmd);
    expect(cmds.indexOf("org_status")).toBeLessThan(cmds.indexOf("chat_send"));
    expect(cmds.indexOf("feed_list")).toBeLessThan(cmds.indexOf("chat_send"));
    expect(h.core.state.msgs[0].step).toBe("injected");
  });
  it("살균·막기를 거친 글을 보낸다 · `/clear` 는 쓰기 0", async () => {
    const h = harness();
    await h.core.send("  안\x1b[201~녕  ");
    expect(h.writes()[0].args?.text).toBe("안 [201~녕");
    await h.core.send("/clear");
    await h.core.send("\u0001/clear");
    expect(h.writes()).toHaveLength(1);
    expect(h.core.state.notice).toMatch(/명령/);
  });
});

describe("입력칸 — 막힌 말은 남기고 받아들인 말만 비움 · 첫 보내기의 세션 시작점 RPC 는 문턱과 쓰기 사이에 끼지 않음", () => {
  it("submit: `/clear` = false(입력칸 그대로 · 안내) · 「안녕」 = true", async () => {
    const h = harness();
    expect(h.core.submit("/clear")).toBe(false);
    expect(h.core.state.notice).toMatch(/명령/);
    expect(h.core.submit("안녕")).toBe(true);
    await h.flush();
    expect(h.writes()).toHaveLength(1);
  });
  it("첫 보내기: chat_transcript(fromEnd) 뒤에 org_status·feed_list 를 다시 받고 곧바로 chat_send", async () => {
    const h = harness();
    h.core.attach(); // 마스터를 아직 모름 → 시작점 못 잡음
    await h.flush();
    h.calls.length = 0;
    await h.core.send("안녕");
    const cmds = h.calls.map((c) => c.cmd);
    const ci = cmds.indexOf("chat_send");
    const ti = cmds.indexOf("chat_transcript");
    expect(ti).toBeGreaterThan(-1);
    expect(ti).toBeLessThan(ci);
    expect(cmds.slice(ti + 1, ci).sort()).toEqual(["feed_list", "org_status"]);
  });
});

describe("문턱 실패 → 쓰기 0 · 붙잡음(조건 하나씩)", () => {
  const cases: Array<[string, Parameters<typeof harness>[0]]> = [
    ["★수용 1 사람 초안 12바이트", { master: { surface_id: 5, role: "master", agent_alive: true, pending_input_bytes: 12, pending_input_human_bytes: 12, input_paste_open: false, gate_pending: null, human_idle_secs: 999 } }],
    ["★수용 2 feed 승인 대기", { approvals: [5] }],
    ["feed 조회 실패", { feedFail: true }],
    ["org.status 조회 실패", { orgFail: true }],
    ["마스터 없음", { master: null }],
    ["에이전트 죽음", { master: { surface_id: 5, role: "master", agent_alive: false, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, human_idle_secs: null } }],
    ["관문", { master: { surface_id: 5, role: "master", agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: { k: 1 }, human_idle_secs: null } }],
    ["입력줄 칸 모름(human_idle_secs 칸 없음)", { master: { surface_id: 5, role: "master", agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null } }],
    ["다른 길 사람 입력 3초 전", { master: { surface_id: 5, role: "master", agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, human_idle_secs: 3 } }],
    ["바쁨(되돌리기 판 · busyPasteOk false)", { busyPasteOk: false, master: { surface_id: 5, role: "master", agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, human_idle_secs: null, working: true } }],
  ];
  const expectCode: Record<string, string> = {
    "★수용 1 사람 초안 12바이트": "draft",
    "★수용 2 feed 승인 대기": "approval",
    "feed 조회 실패": "approval_unknown",
    "org.status 조회 실패": "status_unknown",
    "마스터 없음": "no_master",
    "에이전트 죽음": "agent_dead",
    "관문": "gate_pending",
    "입력줄 칸 모름(human_idle_secs 칸 없음)": "input_unknown",
    "다른 길 사람 입력 3초 전": "human_recent",
    "바쁨(되돌리기 판 · busyPasteOk false)": "busy",
  };
  for (const [name, o] of cases)
    it(name, async () => {
      const h = harness(o);
      await h.core.send("안녕");
      expect(h.writes()).toHaveLength(0);
      expect(h.core.state.msgs[0].step).toBe("held");
      expect(h.core.state.msgs[0].code).toBe(expectCode[name]); // 견본이 이름과 같은 갈래에서 붙잡히는지(VERIFY 지적 3)
      expect(JSON.parse(h.mem.get(HOLD_KEY) as string).items[0].text).toBe("안녕"); // 붙잡은 말만 원문 보관
    });
  it("붙잡은 말 = 문턱이 열리면 오래된 것부터(앞 말이 나간 뒤 다음) · 둘째 말은 첫 말 뒤에 줄 서서 문턱을 따로 안 두드림 · 보내면 저장소에서 지움", async () => {
    const h = harness({ approvals: [5] });
    await h.core.send("하나");
    await h.core.send("둘");
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs.map((m) => m.code)).toEqual(["approval", "after_prev"]);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["하나", "둘"]);
    expect(h.mem.has(HOLD_KEY)).toBe(false);
  });
  it("★VERIFY 지적 1 — A 붙잡힘 → B 입력(문턱 열림) → 마스터 수신 순서 A, B", async () => {
    const h = harness({ approvals: [5] });
    await h.core.send("A 먼저 친 말");
    h.st.approvals = []; // 문턱이 열린 뒤 B 를 친다
    await h.core.send("B 나중에 친 말");
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["A 먼저 친 말", "B 나중에 친 말"]);
  });
  it("앞 말이 쉼 중(데몬 거부 뒤 15초)이면 뒤 말도 앞지르지 않음", async () => {
    let n = 0;
    const h = harness({ sendOutcome: () => (++n === 1 ? { outcome: "held", code: "approval_screen" } : { outcome: "written", result: { sent: true } }) });
    await h.core.send("A");
    await h.core.send("B");
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["A"]);
    h.setNow(h.getNow() + HELD_REFUSED_BACKOFF_MS);
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["A", "A", "B"]);
  });
  it("★master 결정 — 붙잡은 지 10분 넘은 말은 자동 제출 0 · 「아직 안 보냈어요 · 오래 기다린 말이라…」 · 클릭 1회로만(표지 칸 없는 옛 데몬 = 모름 = 종전 · K-2)", async () => {
    const h = harness({ approvals: [5] });
    await h.core.send("그 파일 지워 줘");
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    for (let i = 0; i < 5; i++) await h.core.poll();
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
    expect(h.core.state.msgs[0].note).toBe(STALE_NOTE);
    await h.core.confirmHeld(h.core.state.msgs[0].id);
    expect(h.writes().map((c) => c.args?.text)).toEqual(["그 파일 지워 줘"]);
  });
  it("문턱이 닫혀 있는 동안에도 10분이 지나면 「보낼까요?」로 바뀜(문턱이 열리는 순간 자동으로 나가는 일 0)", async () => {
    const h = harness({ approvals: [5] });
    await h.core.send("그 파일 지워 줘");
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    await h.core.poll(); // 아직 승인 대기 — 쓰기 시도 없음
    expect(h.core.state.msgs[0].code).toBe(STALE);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes()).toHaveLength(0);
  });
  it("10분 넘은 앞 말이 클릭 대기면 새 말은 그 뒤에 묶이지 않고 나감(사람이 안 누를 수도 있는 말이 막지 않게)", async () => {
    const h = harness({ approvals: [5] });
    await h.core.send("옛 말");
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    await h.core.send("새 말");
    expect(h.writes().map((c) => c.args?.text)).toEqual(["새 말"]);
  });
  it("앱을 다시 켜도 붙잡은 말이 남는다(cys-chat-hold) · ★자동 제출 0 — 사람이 「이 말 보내기」를 눌러야 다듬기부터 다시(codex 1R)", async () => {
    const h = harness({ master: null });
    await h.core.send("남아라");
    h.st.master = { surface_id: 5, role: "master", agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null };
    const again = new ChatCore(h.deps);
    expect(again.state.msgs.map((m) => [m.text, m.step, m.code])).toEqual([["남아라", "held", RESTORED]]);
    for (let i = 0; i < 5; i++) await again.poll();
    expect(h.writes()).toHaveLength(0);
    await again.confirmHeld(again.state.msgs[0].id);
    expect(h.writes().map((c) => c.args?.text)).toEqual(["남아라"]);
  });
  it("저장소에서 읽은 `/clear`(변조·손상) = 자동 제출 0 · 눌러도 다듬기에서 막힘", async () => {
    const h = harness();
    h.mem.set(HOLD_KEY, JSON.stringify({ v: 1, items: [{ id: "x1", text: "/clear", at: 1 }] }));
    const c = new ChatCore(h.deps);
    for (let i = 0; i < 3; i++) await c.poll();
    await c.confirmHeld(c.state.msgs[0].id);
    expect(h.writes()).toHaveLength(0);
    expect(c.state.notice).toMatch(/명령/);
  });
  it("★쓰기 전 「보내는 중」 영속 실패(저장소 쓰기 예외) = 쓰기 0 · 붙잡음 그대로(codex 1R)", async () => {
    const h = harness({ approvals: [5] });
    await h.core.send("안녕");
    h.st.approvals = [];
    h.deps.store.set = () => {
      throw new Error("quota");
    };
    h.deps.store.remove = () => {
      throw new Error("quota");
    };
    await h.core.poll();
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe("store_failed");
  });
});

describe("codex 2R — 마지막 관측 · 복원 id · 상한 교착 · 단회 소비", () => {
  it("feed 먼저 · org.status(입력줄) 마지막 · 그 뒤 다른 응답 기다림 0 → chat_send", async () => {
    const h = harness();
    h.core.attach();
    await h.core.poll(); // 마스터를 알고 세션 시작점을 잡아 둔다
    await h.flush();
    h.calls.length = 0;
    await h.core.send("안녕");
    expect(h.calls.map((c) => c.cmd)).toEqual(["feed_list", "org_status", "chat_send"]);
  });
  it("org.status 왕복이 상한을 넘으면 그 관측으로 쓰지 않음(붙잡음)", async () => {
    const h = harness();
    const orig = h.deps.invoke;
    h.deps.invoke = async (cmd, args) => {
      if (cmd === "org_status") h.setNow(h.getNow() + OBS_MAX_MS + 1);
      return orig(cmd, args);
    };
    await h.core.send("안녕");
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe("status_unknown");
  });
  it("★관측 뒤 영속·그리기가 늦어 쓰기 직전 관측 나이가 상한을 넘으면 쓰기 0(codex 3R)", async () => {
    const h = harness();
    await h.core.poll();
    let slow = false;
    h.core.subscribe(() => {
      if (slow) h.setNow(h.getNow() + OBS_MAX_MS + 1); // 그리기(구독자)가 느림
    });
    slow = true;
    await h.core.send("안녕");
    slow = false;
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].step).toBe("held");
  });
  it("저장소 id 는 쓰지 않음 — 새 말 id 와 같은 값이어도 새 말 보내기가 복원 `/clear` 를 고르지 않음", async () => {
    const h = harness();
    h.mem.set(HOLD_KEY, JSON.stringify({ v: 1, items: [{ id: `m${h.getNow()}-1`, text: "/clear", at: 1 }] }));
    const c = new ChatCore(h.deps);
    expect(c.state.msgs[0].id.startsWith("r")).toBe(true);
    await c.send("안녕");
    expect(h.writes().map((x) => x.args?.text)).toEqual(["안녕"]);
    expect(c.state.msgs.find((m) => m.code === RESTORED)?.text).toBe("/clear");
  });
  it("복원 말 20개(상한)여도 「이 말 보내기」는 자기 자신을 대체(교착 0)", async () => {
    const h = harness();
    h.mem.set(HOLD_KEY, JSON.stringify({ v: 1, items: Array.from({ length: HOLD_MAX }, (_, i) => ({ id: "x", text: `말${i}`, at: i })) }));
    const c = new ChatCore(h.deps);
    expect(c.state.msgs).toHaveLength(HOLD_MAX);
    await c.confirmHeld(c.state.msgs[0].id);
    expect(h.writes().map((x) => x.args?.text)).toEqual(["말0"]);
  });
  it("소비한 uuid 는 말 목록과 무관하게 세션 동안 한 번만 — 같은 레코드를 다시 받아도 다른 같은 글 말에 배정 0", async () => {
    const h = harness();
    h.core.attach();
    await h.core.poll();
    await h.flush();
    await h.core.send("안녕");
    h.st.file.push({ uuid: "u1", parent: null, role: "user", text: "안녕", ts: null });
    await h.core.readTranscript();
    expect(h.core.state.msgs[0].step).toBe("delivered");
    // 같은 레코드가 다시 들어오는 상황(대역 파일에 같은 줄을 한 번 더)
    h.setNow(h.getNow() + 31_000);
    await h.core.send("안녕");
    h.st.file.push({ uuid: "u1", parent: null, role: "user", text: "안녕", ts: null });
    await h.core.readTranscript();
    expect(h.core.state.msgs[1].step).toBe("injected");
  });
});

describe("codex 2R — 말 목록에서 밀려난 뒤에도 소비 이력 유지", () => {
  it("답함 말이 LOG_MAX 정리로 사라진 뒤 같은 uuid 레코드가 다시 와도 새 같은 글 말에 배정 0", async () => {
    let outcome: Record<string, unknown> = { outcome: "written", result: { sent: true } };
    const h = harness({ sendOutcome: () => outcome });
    h.core.attach();
    await h.core.poll();
    await h.flush();
    await h.core.send("안녕");
    h.st.file.push({ uuid: "u1", parent: null, role: "user", text: "안녕", ts: null }, { uuid: "a1", parent: "u1", role: "assistant", text: "답", ts: null });
    await h.core.readTranscript();
    await h.core.poll();
    expect(h.core.state.msgs[0].step).toBe("replied");
    outcome = { outcome: "failed", code: "not_found" };
    for (let i = 0; i < LOG_MAX; i++) await h.core.send(`채움${i}`);
    expect(h.core.state.msgs.some((m) => m.userUuid === "u1")).toBe(false); // 밀려남
    outcome = { outcome: "written", result: { sent: true } };
    await h.core.send("안녕");
    h.st.file.push({ uuid: "u1", parent: null, role: "user", text: "안녕", ts: null });
    await h.core.readTranscript();
    expect(h.core.state.msgs[h.core.state.msgs.length - 1].step).toBe("injected");
  });
});

describe("데몬 응답 넷", () => {
  it("승인 창 → 데몬 거부 = 붙잡음 · 쉼 동안 재시도 0 · 쉼 뒤 문턱 재통과 1회", async () => {
    let n = 0;
    const h = harness({ sendOutcome: () => (++n === 1 ? { outcome: "held", code: "approval_screen" } : { outcome: "written", result: { sent: true } }) });
    await h.core.send("안녕");
    expect(h.core.state.msgs[0].step).toBe("held");
    expect(h.core.state.msgs[0].code).toBe("approval_screen");
    await h.core.poll();
    expect(h.writes()).toHaveLength(1);
    h.setNow(h.getNow() + HELD_REFUSED_BACKOFF_MS);
    await h.core.poll();
    expect(h.writes()).toHaveLength(2);
    expect(h.core.state.msgs[0].step).toBe("injected");
  });
  it("불명 응답 → 「확인 중」 · 다시 보내기 0(폴 20번에도)", async () => {
    const h = harness({ sendOutcome: { outcome: "uncertain", code: "transport_uncertain" } });
    await h.core.send("안녕");
    expect(h.core.state.msgs[0].step).toBe("checking");
    for (let i = 0; i < 20; i++) await h.core.poll();
    await h.core.retry(h.core.state.msgs[0].id);
    expect(h.writes()).toHaveLength(1);
  });
  it("Tauri 다리 예외도 「확인 중」(쓰였는지 모름)", async () => {
    const h = harness({
      sendOutcome: () => {
        throw new Error("ipc");
      },
    });
    await h.core.send("안녕");
    expect(h.core.state.msgs[0].step).toBe("checking");
  });
  it("확정 실패 → 「못 보냄」 · 사람 다시 보내기 1회만(새 번호)", async () => {
    let n = 0;
    const h = harness({ sendOutcome: () => (++n === 1 ? { outcome: "failed", code: "not_found" } : { outcome: "failed", code: "not_found" }) });
    await h.core.send("안녕");
    const first = h.core.state.msgs[0];
    expect(first.step).toBe("failed");
    await h.core.retry(first.id);
    await h.core.retry(first.id);
    const second = h.core.state.msgs[1];
    await h.core.retry(second.id);
    expect(h.writes()).toHaveLength(2);
    expect(second.id).not.toBe(first.id);
  });
  it("정비 보류 → 차례 기다림 · 다시 보내기 0", async () => {
    const h = harness({ sendOutcome: { outcome: "queued_hold", code: "update_hold" } });
    await h.core.send("안녕");
    for (let i = 0; i < 5; i++) await h.core.poll();
    expect(h.core.state.msgs[0].step).toBe("queued_hold");
    expect(h.writes()).toHaveLength(1);
  });
});

describe("연타·겹침 — 클릭 1 → 호출 ≤ 1 · 말 버림 0", () => {
  it("쓰는 중에 받은 말은 앞 말 뒤에 1건씩", async () => {
    let release: () => void = () => {};
    let n = 0;
    const h = harness({
      sendOutcome: () => {
        n++;
        return { outcome: "written", result: { sent: true } };
      },
    });
    const orig = h.deps.invoke;
    let gateOnce = true;
    h.deps.invoke = async (cmd, args) => {
      if (cmd === "chat_send" && gateOnce) {
        gateOnce = false;
        await new Promise<void>((r) => (release = r));
      }
      return orig(cmd, args);
    };
    const core = new ChatCore(h.deps);
    const p1 = core.send("하나");
    await h.flush();
    const p2 = core.send("둘");
    const p3 = core.send("셋");
    await h.flush();
    expect(core.state.msgs.map((m) => m.step)).toEqual(["sending", "held", "held"]);
    release();
    await Promise.all([p1, p2, p3]);
    await h.flush();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["하나", "둘", "셋"]);
    expect(n).toBe(3);
  });
});

describe("전달 확인 중 → 전달됨 → 마스터 답(결속 세션 전문)", () => {
  it("+1·+3·+7초 읽기 · 전문 일치 user 레코드 = 전달됨 · 사슬 위 답 = 말풍선 · 쉬면 답함", async () => {
    const h = harness();
    h.core.attach();
    await h.flush();
    await h.core.send("안녕");
    expect(h.calls.filter((c) => c.cmd === "chat_transcript" && (c.args as { fromEnd: boolean }).fromEnd)).toHaveLength(1);
    const t0 = h.getNow();
    h.st.file.push({ uuid: "u1", parent: null, role: "user", text: "안녕", ts: new Date(t0 + 200).toISOString() });
    await h.advance(READ_AFTER_MS[0]);
    expect(h.core.state.msgs[0].step).toBe("delivered");
    h.st.file.push({ uuid: "a1", parent: "u1", role: "assistant", text: "네, 듣고 있어요", ts: new Date(t0 + 900).toISOString() });
    (h.st.master as Record<string, unknown>).working = true;
    await h.advance(READ_AFTER_MS[1] - READ_AFTER_MS[0]);
    expect(h.core.state.msgs[0].step).toBe("replying");
    expect(h.core.state.msgs[0].replies[0].text).toBe("네, 듣고 있어요");
    (h.st.master as Record<string, unknown>).working = false;
    await h.core.poll();
    expect(h.core.state.msgs[0].step).toBe("replied");
    expect(h.calls.filter((c) => c.cmd === "chat_transcript").length).toBeLessThan(8);
  });
  it("대화 화면이 내려가면 읽기 예약 해제(세션 읽기 0)", async () => {
    const h = harness();
    h.core.attach();
    await h.flush();
    await h.core.send("안녕");
    h.core.detach();
    const before = h.calls.filter((c) => c.cmd === "chat_transcript").length;
    await h.advance(10_000);
    expect(h.calls.filter((c) => c.cmd === "chat_transcript").length).toBe(before);
  });
  it("파일이 줄어 reset 이면 다시 읽은 옛 레코드로 근거를 만들지 않고 끝에서 다시(codex 1R)", async () => {
    const h = harness();
    h.core.attach();
    await h.flush();
    await h.core.send("안녕");
    const orig = h.deps.invoke;
    let once = true;
    h.deps.invoke = async (cmd, args) => {
      if (cmd === "chat_transcript" && once && !(args as { fromEnd: boolean }).fromEnd) {
        once = false;
        return { status: "ok", session_id: h.st.session, next_offset: 1, size: 1, reset: true, records: [{ uuid: "u1", parent: null, role: "user", text: "안녕", ts: null }] };
      }
      return orig(cmd, args);
    };
    await h.core.readTranscript();
    expect(h.core.state.msgs[0].step).toBe("injected");
  });
  it("결속 세션이 바뀌면 새 파일 끝에서 다시 시작", async () => {
    const h = harness();
    h.core.attach();
    await h.flush();
    h.st.session = "sess-0002-bbbb";
    h.st.file.push({ uuid: "old", parent: null, role: "assistant", text: "옛 글", ts: null });
    await h.core.readTranscript();
    expect(h.core.state.stray).toEqual([]);
  });
});

describe("상태 표시", () => {
  it("healthOf", () => {
    expect(healthOf(undefined)).toBe("unknown");
    expect(healthOf(null)).toBe("none");
    const row = { surface_id: 1, exited: false, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false };
    expect(healthOf({ ...row, agent_alive: false })).toBe("off");
    expect(healthOf({ ...row, agent_alive: null })).toBe("unknown"); // 등록 없는 좌석 = 「꺼져 있어요」 아님(VERIFY 지적 11)
  });
});

// (TICKET=cysr-1119-s2 · DESIGN §3-5 고침 ③ · K19) 상한 안내 글 = 사실대로(붙잡은 말 가운데 눌러야 나가는 말이 있을 수 있음 · 거절된 새 말은 나중에 저절로 가지 않음).
//   셈(`held` ≥ HOLD_MAX)·저장 꼴·키·상한은 1.1.18 그대로 — 글만 바뀐다.
describe("K19 — hold_cap_notice_text(붙잡은 말 상한 안내 글)", () => {
  const CAP_TEXT = `붙잡아 둔 말이 ${HOLD_MAX}개 이상이라 이 말은 받지 않았어요 — 위의 말이 보내지면 다시 보낼 수 있어요(『이 말 보내기』가 붙은 말은 눌러야 보내져요). 입력칸 글은 그대로 있어요.`;
  it("hold_cap_notice_text — 붙잡음 20(복원 15 + 바쁠 때 5) + 새 말 → 글자 그대로 · 입력칸 유지 · 셈·저장 꼴 = 1.1.18", async () => {
    const h = harness({ busyPasteOk: false }); // (K-3) 「바쁠 때 붙잡힘 5」 = 되돌리기 판 동작으로 상한 셈을 만든다
    h.mem.set(HOLD_KEY, JSON.stringify({ v: 1, items: Array.from({ length: 15 }, (_, i) => ({ id: "x", text: `옛말${i}`, at: i })) }));
    h.st.master = { ...(h.st.master as Record<string, unknown>), working: true };
    const c = new ChatCore(h.deps);
    for (let i = 0; i < 5; i++) await c.send(`바쁠때${i}`);
    const held = () => c.state.msgs.filter((m) => m.step === "held");
    expect(held()).toHaveLength(HOLD_MAX);
    expect(held().filter((m) => m.code === RESTORED)).toHaveLength(15);
    const saved = h.mem.get(HOLD_KEY);
    expect(c.submit("새 말")).toBe(false); // 입력칸 글은 그대로(화면이 비우지 않음)
    await h.flush();
    expect(c.state.notice).toBe(CAP_TEXT);
    expect(held()).toHaveLength(HOLD_MAX); // 셈 그대로 · 새 말은 목록에 들어가지 않음
    expect(c.state.msgs.some((m) => m.text === "새 말")).toBe(false);
    expect(h.writes()).toHaveLength(0);
    expect(h.mem.get(HOLD_KEY)).toBe(saved); // 저장 바이트 그대로
    const box = JSON.parse(saved as string) as { v: number; items: Array<{ id: string; text: string; at: number }> };
    expect(box.v).toBe(1);
    expect(box.items).toHaveLength(HOLD_MAX);
    expect(Object.keys(box.items[0]).sort()).toEqual(["at", "id", "text"]);
  });
  it("hold_cap_notice_text — 19 이면 받는다(경계 = 1.1.18 셈 그대로)", async () => {
    const h = harness();
    h.mem.set(HOLD_KEY, JSON.stringify({ v: 1, items: Array.from({ length: HOLD_MAX - 1 }, (_, i) => ({ id: "x", text: `옛말${i}`, at: i })) }));
    const c = new ChatCore(h.deps);
    expect(c.submit("새 말")).toBe(true);
    await h.flush();
    expect(c.state.notice).not.toBe(CAP_TEXT);
  });
});

// ---------- (1.1.19 · TICKET=cysr-1119-s3 · CH-C) 기록 바뀌면 곧 보이기 — F06 읽기 길 하나 · C-1~C-4 · F29 · 되돌리기 C 끄기 지점 ----------
// 대역 파일 = 레코드 배열 · 오프셋 = 레코드 번호(위 harness 와 같은 뜻) · tail 은 대역 시계로 늦게 답할 수 있다(겹침 계수).
function chHarness(o: { compat?: boolean | (() => boolean); tailDelay?: number; regSid?: string | null; busyPasteOk?: boolean } = {}) {
  const calls: Array<{ cmd: string; args?: Record<string, unknown> }> = [];
  let now = 2_000_000;
  const timers: Array<{ at: number; fn: () => void; h: number }> = [];
  let hn = 0;
  const st = {
    master: { surface_id: 5, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false, registered_session_id: o.regSid === undefined ? "sess-0001-aaaa" : o.regSid } as Record<string, unknown>,
    file: [] as Array<Record<string, unknown>>,
    session: "sess-0001-aaaa",
    watchGen: 0,
    watchOk: true,
    tailFail: 0,
    /** 다음 tail 응답을 이 오프셋에서 읽은 것으로(늦게 온 옛 응답 흉내) */
    staleFrom: null as number | null,
    inflight: 0,
    maxInflight: 0,
    /** watch 응답을 superseded 로(Tauri 가 unwatch 를 뒤에 처리) */
    superseded: 0,
    /** 파일 끝 미완 줄 길이(오프셋 단위) — tail 의 size 가 이만큼 크고 next_offset 은 완성 줄 끝 */
    openTail: 0,
    /** tail 이 쥔 핸들 = 옛 파일(경로는 새 파일 · 윈 터널링 꼴) — 이 값이면 tail 은 이 길이까지만 본다 */
    heldLen: null as number | null,
  };
  const app = new Map<string, Array<(e: { payload: unknown }) => void>>();
  const later = <T>(ms: number, v: () => T): Promise<T> =>
    ms <= 0 ? Promise.resolve(v()) : new Promise((res) => timers.push({ at: now + ms, fn: () => res(v()), h: ++hn }));
  const deps: Deps = {
    invoke: async (cmd, args) => {
      calls.push({ cmd, args });
      if (cmd === "org_status") return { surfaces: [st.master] };
      if (cmd === "feed_list") return { items: [] };
      if (cmd === "chat_send") return { outcome: "written", result: { sent: true } };
      if (cmd === "chat_transcript") {
        const a = args as { afterOffset: number; fromEnd: boolean };
        if (a.fromEnd) return { status: "ok", session_id: st.session, next_offset: st.file.length, size: st.file.length, records: [] };
        return { status: "ok", session_id: st.session, next_offset: st.file.length, size: st.file.length, records: st.file.slice(a.afterOffset) };
      }
      if (cmd === "chat_transcript_watch") {
        const a = args as { surfaceId: number; sessionId: string };
        if (st.superseded > 0) {
          st.superseded--;
          return { status: "unknown", why: "superseded" };
        }
        if (!st.watchOk || a.sessionId !== st.session) return { status: "unknown", why: "session_mismatch" };
        return { status: "ok", session_id: st.session, size: st.file.length, gen: ++st.watchGen };
      }
      if (cmd === "chat_transcript_unwatch") return { status: "ok", was: true };
      if (cmd === "chat_transcript_tail") {
        const a = args as { afterOffset: number };
        st.inflight++;
        st.maxInflight = Math.max(st.maxInflight, st.inflight);
        return later(o.tailDelay ?? 0, () => {
          st.inflight--;
          if (st.tailFail > 0) {
            st.tailFail--;
            return null;
          }
          const from = st.staleFrom ?? a.afterOffset;
          st.staleFrom = null;
          if (st.heldLen !== null) return { status: "ok", session_id: st.session, gen: st.watchGen, from_offset: from, to_offset: st.heldLen, next_offset: st.heldLen, size: st.heldLen, records: [], reset: false };
          return { status: "ok", session_id: st.session, gen: st.watchGen, from_offset: from, to_offset: st.file.length, next_offset: st.file.length, size: st.file.length + st.openTail, records: st.file.slice(from), reset: false };
        });
      }
      throw new Error(`unexpected ${cmd}`);
    },
    listenApp: async (name, handler) => {
      const hs = app.get(name) ?? [];
      hs.push(handler);
      app.set(name, hs);
      return () => app.set(name, (app.get(name) ?? []).filter((h) => h !== handler));
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
    store: { get: () => null, set: () => {}, remove: () => {} },
    working: (r) => r.working === true,
    busyPasteOk: o.busyPasteOk,
  };
  if (o.compat !== undefined) (deps as Deps & { compat1118?: () => boolean }).compat1118 = typeof o.compat === "function" ? o.compat : () => o.compat as boolean;
  const flush = async () => {
    for (let i = 0; i < 40; i++) await Promise.resolve();
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
  const emit = (payload: Record<string, unknown>) => {
    for (const h of app.get("chat-transcript-changed") ?? []) h({ payload });
  };
  const core = new ChatCore(deps);
  let seen = 0;
  (core.confirm as unknown as { onTail(r: unknown[]): void }).onTail = (r) => void (seen += r.length);
  const rec = (i: number) => ({ uuid: `u${i}`, parent: null, role: "assistant", text: `답 ${i}`, ts: null });
  const n = (cmd: string) => calls.filter((c) => c.cmd === cmd).length;
  return { core, st, calls, n, flush, advance, emit, rec, seen: () => seen, app, getNow: () => now };
}

/** 대화 화면을 켜고 결속 파일 watch 까지 건 상태로. */
async function watched(h: ReturnType<typeof chHarness>) {
  h.core.attach();
  await h.flush();
  await h.core.poll();
  await h.advance(10);
}

describe("CH-C 기록 바뀌면 곧 보이기(1.1.19 · S3)", () => {
  it("f29_master_row_registered_session_id — 3초 조회 원문의 결속 id 를 MasterRow 칸으로(글만 · 그 밖 null)", () => {
    const base = { surface_id: 1, role: "master" };
    expect(masterRowOf({ surfaces: [{ ...base, registered_session_id: "sess-1" }] }, () => false)?.registered_session_id).toBe("sess-1");
    for (const v of [undefined, null, 7, "", { a: 1 }]) expect(masterRowOf({ surfaces: [{ ...base, registered_session_id: v }] }, () => false)?.registered_session_id).toBeNull();
  });

  it("c_watch — 결속을 안 뒤 watch 1회(3초 조회의 결속 id = 기록 세션 id) · 사건 → tail(RPC 0) 로 읽음", async () => {
    const h = chHarness();
    await watched(h);
    expect(h.n("chat_transcript_watch")).toBe(1);
    expect(h.calls.find((c) => c.cmd === "chat_transcript_watch")?.args).toEqual({ socket: null, surfaceId: 5, sessionId: "sess-0001-aaaa" });
    const before = h.n("chat_transcript");
    h.st.file.push(h.rec(1), h.rec(2));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 2, reset: false });
    await h.advance(10);
    expect(h.n("chat_transcript_tail")).toBe(1);
    expect(h.n("chat_transcript")).toBe(before); // 사건 읽기 = RPC 2개짜리 기존 명령 0
    expect(h.seen()).toBe(2);
  });

  it("f06_one_read_path_counts_each_byte_once — 같은 순간 사건·1초 맞춤·3초 계기 셋 → 각 레코드 1회 · tail 겹침 0", async () => {
    const h = chHarness({ tailDelay: 40 });
    await watched(h);
    for (let i = 1; i <= 5; i++) h.st.file.push(h.rec(i));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 5, reset: false }); // 사건
    h.core.pollTick(); // 1초 맞춤(사건 size > offset)
    h.st.master.working = true; // 3초 계기(활동 바뀜) — 다음 조회에서
    await h.core.poll();
    h.st.master.working = false;
    await h.core.poll();
    await h.advance(500);
    expect(h.seen()).toBe(5);
    expect(h.st.maxInflight).toBe(1);
    expect(h.core.state.stray.map((r) => r.uuid)).toEqual(["u1", "u2", "u3", "u4", "u5"]);
  });

  it("f06_stale_from_offset_is_dropped — 응답의 from_offset 이 지금 offset 과 다르면 버리고 다시 읽음(두 번 셈 0)", async () => {
    const h = chHarness();
    await watched(h);
    h.st.file.push(h.rec(1), h.rec(2));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 2, reset: false });
    await h.advance(10);
    expect(h.seen()).toBe(2);
    h.st.file.push(h.rec(3));
    h.st.staleFrom = 0; // 옛 오프셋(0)에서 읽은 응답이 지금(2) 읽기의 답으로 옴
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 3, reset: false });
    await h.advance(10);
    expect(h.seen()).toBe(3); // 뮤턴트(from_offset 대조 제거) = 5(u1·u2 두 번)
    expect(h.n("chat_transcript_tail")).toBe(3); // 버리고 한 번 더
  });

  it("c_old_gen_or_other_seat_event_is_ignored — 세대·좌석이 다른 사건은 읽지 않음", async () => {
    const h = chHarness();
    await watched(h);
    h.st.file.push(h.rec(1));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen + 9, size: 1, reset: false });
    h.emit({ surface_id: 6, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 1, reset: false });
    await h.advance(10);
    expect(h.n("chat_transcript_tail")).toBe(0);
  });

  it("c_reset_event_rewatches — reset 사건 → watch 끊고 시작점 다시 → 다시 걸기(옛 레코드 0)", async () => {
    const h = chHarness();
    await watched(h);
    h.st.file = [h.rec(7)]; // 같은 경로가 다른 내용으로
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 1, reset: true });
    await h.advance(10);
    expect(h.n("chat_transcript_unwatch")).toBe(1);
    expect(h.calls.filter((c) => c.cmd === "chat_transcript" && (c.args as { fromEnd: boolean }).fromEnd).length).toBe(2);
    expect(h.n("chat_transcript_watch")).toBe(2);
    expect(h.seen()).toBe(0);
  });

  it("c3_rebind_on_registered_session_change — 3초 조회의 결속 id 가 바뀌면 unwatch → 시작점 → 새 id 로 watch · 옛 파일 레코드 0", async () => {
    const h = chHarness();
    await watched(h);
    h.st.session = "sess-0002-bbbb";
    h.st.master.registered_session_id = "sess-0002-bbbb";
    h.st.file = [h.rec(1), h.rec(2)]; // 새 세션 파일(끝에서 시작)
    await h.core.poll();
    await h.advance(10);
    expect(h.n("chat_transcript_unwatch")).toBe(1);
    const w = h.calls.filter((c) => c.cmd === "chat_transcript_watch");
    expect(w.length).toBe(2);
    expect((w[1].args as { sessionId: string }).sessionId).toBe("sess-0002-bbbb");
    expect(h.seen()).toBe(0);
    h.st.file.push(h.rec(3));
    h.emit({ surface_id: 5, session_id: "sess-0002-bbbb", gen: h.st.watchGen, size: 3, reset: false });
    await h.advance(10);
    expect(h.seen()).toBe(1);
  });

  it("c3_no_binding_no_watch — 결속 id 없음(옛 데몬·미등록) = watch 0 · 1.1.18 읽기 길 그대로", async () => {
    const h = chHarness({ regSid: null });
    await watched(h);
    expect(h.n("chat_transcript_watch")).toBe(0);
    h.st.file.push(h.rec(1));
    h.st.master.working = true;
    await h.core.poll();
    h.st.master.working = false;
    await h.core.poll();
    await h.advance(10);
    expect(h.n("chat_transcript_tail")).toBe(0);
    expect(h.seen()).toBe(1);
  });

  it("c4_align_reads_when_event_read_failed — 사건 뒤 읽기가 실패해도 1초 맞춤이 다시 읽음 · 사건 없으면 맞춤 0(검증 V5: 옛 이름 「event_missed」 가 본문과 달라 고침)", async () => {
    const h = chHarness();
    await watched(h);
    h.core.pollTick(); // 사건 없음 → 맞춤 0
    await h.advance(10);
    expect(h.n("chat_transcript_tail")).toBe(0);
    h.st.file.push(h.rec(1));
    h.st.tailFail = 1;
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 1, reset: false });
    await h.advance(10);
    expect(h.seen()).toBe(0);
    await h.advance(1000);
    h.core.pollTick();
    await h.advance(10);
    expect(h.seen()).toBe(1);
  });

  it("c4_align_after_held_poll — 1초 틱 안 순서 = 붙잡은 말 문턱(상태 조회) 먼저, 맞춤 다음", async () => {
    const h = chHarness({ busyPasteOk: false }); // (K-3) 「답하는 중」 붙잡음 = 되돌리기 판 동작
    await watched(h);
    h.st.master.working = true;
    await h.core.poll();
    h.core.submit("안녕");
    await h.advance(10);
    expect(h.core.state.msgs[0]?.step).toBe("held");
    h.st.master.working = false;
    h.st.file.push(h.rec(1));
    h.st.tailFail = 1; // 사건 읽기는 실패 → 맞춤이 남음
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 1, reset: false });
    await h.advance(1100);
    const mark = h.calls.length;
    h.core.pollTick();
    await h.flush();
    const after = h.calls.slice(mark).map((c) => c.cmd);
    expect(after.indexOf("feed_list")).toBeGreaterThanOrEqual(0);
    expect(after.indexOf("chat_transcript_tail")).toBeGreaterThan(after.indexOf("feed_list"));
  });

  it("c_watch_only_while_chat_visible — 작업 화면 살핌 = unwatch · 내린 뒤 사건 = 읽기 0 · 다시 켜면 다시 걸기", async () => {
    const h = chHarness();
    await watched(h);
    expect(h.core.watchStart()).toBe(true); // 대화 → 작업(새 화면 먼저)
    h.core.detach(); // 옛 화면 내림(살핌 중이라 그대로)
    await h.flush();
    expect(h.n("chat_transcript_unwatch")).toBe(1);
    h.st.file.push(h.rec(1));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 1, reset: false });
    await h.advance(10);
    expect(h.n("chat_transcript_tail")).toBe(0);
    h.core.attach(); // 작업 → 대화
    h.core.watchStop();
    await h.advance(10);
    expect(h.n("chat_transcript_watch")).toBe(2);
    h.core.detach();
    await h.flush();
    expect(h.n("chat_transcript_unwatch")).toBe(2);
    h.st.file.push(h.rec(2));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 2, reset: false });
    await h.advance(10);
    expect(h.calls.filter((c) => c.cmd === "chat_transcript_tail").length <= 1).toBe(true); // 다시 켠 뒤 따라잡기 1회만
  });

  it("c_compat_1118_no_watch — 되돌리기 켬 = watch·tail 0 · 1.1.18 읽기 길 · 던지면 끔(watch 함)", async () => {
    const h = chHarness({ compat: true });
    await watched(h);
    h.st.file.push(h.rec(1));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: 1, size: 1, reset: false });
    h.core.pollTick();
    await h.advance(10);
    expect(h.n("chat_transcript_watch") + h.n("chat_transcript_tail")).toBe(0);
    const t = chHarness({
      compat: () => {
        throw new Error("x");
      },
    });
    await watched(t);
    expect(t.n("chat_transcript_watch")).toBe(1);
  });

  it("c_watch_failure_backs_off — watch 가 못 걸리면 3초 조회마다 다시 걸지 않음(30초 뒤 1회)", async () => {
    const h = chHarness();
    h.st.watchOk = false;
    await watched(h);
    expect(h.n("chat_transcript_watch")).toBe(1);
    for (let i = 0; i < 5; i++) {
      await h.advance(3000);
      await h.core.poll();
    }
    expect(h.n("chat_transcript_watch")).toBe(1);
    h.st.watchOk = true;
    await h.advance(30_000);
    await h.core.poll();
    await h.advance(10);
    expect(h.n("chat_transcript_watch")).toBe(2);
  });

  it("c4_align_reads_when_event_missed — 사건이 아예 안 와도(구독 전·emit 실패) 3초 조회 안전망 tail(RPC 0)이 읽음(검증 V5)", async () => {
    const h = chHarness();
    await watched(h);
    h.st.file.push(h.rec(1), h.rec(2)); // 사건 없음
    const rpc0 = h.n("chat_transcript");
    await h.advance(3000);
    await h.core.poll();
    await h.advance(10);
    expect(h.seen()).toBe(2);
    expect(h.n("chat_transcript")).toBe(rpc0); // 데몬 RPC 0(tail)
  });

  it("v4_unwatch_carries_gen — 건 세대를 알면 unwatch 에 그 세대를 싣는다(늦게 처리돼도 새 watch 를 안 내림)", async () => {
    const h = chHarness();
    await watched(h);
    const g = h.st.watchGen;
    h.core.detach();
    await h.flush();
    expect(h.calls.filter((c) => c.cmd === "chat_transcript_unwatch").map((c) => c.args)).toEqual([{ gen: g }]);
  });

  it("a0_fresh_seat_no_file_reads_from_zero — 처음부터 기록 파일이 없던 좌석(결속 id 있음): 끔 = 파일이 생기면 첫 말·답을 0 에서 · 없는 동안 watch 0 · 켬 = 1.1.18 그대로(이 결함 남음 · master#f03515c6 N2)", async () => {
    for (const compat of [false, true]) {
      const h = chHarness({ compat });
      const deps = (h.core as unknown as { d: Deps }).d;
      const real = deps.invoke;
      let noFile = true;
      // 가로챈 호출도 장부에 적는다(검증 고침2 ④ — 장부 밖 호출이면 「watch 0」 이 뜻 없는 단언)
      deps.invoke = async (cmd, args) => {
        if (noFile && (cmd === "chat_transcript" || cmd === "chat_transcript_watch")) {
          h.calls.push({ cmd, args });
          return { status: "unknown", why: "no_file", session_id: h.st.session };
        }
        return real(cmd, args);
      };
      await watched(h);
      for (let i = 0; i < 5; i++) {
        await h.advance(3000);
        await h.core.poll();
      }
      expect(h.n("chat_transcript_watch")).toBe(0); // 파일 없는 동안 watch 시도 0(N1)
      h.core.submit("안녕"); // 첫 입력 = 파일이 생김
      await h.advance(10);
      noFile = false;
      h.st.file.push({ uuid: "user-1", parent: null, role: "user", text: "안녕", ts: null }, h.rec(1));
      await h.advance(1100); // 보낸 뒤 +1초 읽기
      expect(h.seen()).toBe(compat ? 0 : 2); // 끔 = 0 에서 읽음 · 켬 = 1.1.18 처럼 끝에서 시작(잃음)
      if (!compat) {
        await h.advance(3000);
        await h.core.poll();
        await h.advance(10);
        expect(h.n("chat_transcript_watch")).toBe(1); // 파일을 본 뒤 3초 조회가 건다
      }
    }
  });

  it("c_superseded_is_not_failure — Tauri 가 앞 unwatch 를 뒤에 처리해 watch 가 superseded = 실패 아님(다음 3초 조회에 다시 · 30초 물러남 0)", async () => {
    const h = chHarness();
    h.st.superseded = 1;
    await watched(h);
    expect(h.n("chat_transcript_watch")).toBe(1);
    await h.advance(3000);
    await h.core.poll();
    await h.advance(10);
    expect(h.n("chat_transcript_watch")).toBe(2);
  });

  it("c4_align_no_spin_on_open_line — 미완 줄(next_offset < size)이면 사건 읽기 1번 · 1초 맞춤은 새 바이트가 올 때까지 0", async () => {
    const h = chHarness();
    await watched(h);
    h.st.file.push(h.rec(1));
    h.st.openTail = 1; // 쓰는 중인 줄
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 2, reset: false });
    await h.advance(10);
    expect(h.seen()).toBe(1);
    expect(h.n("chat_transcript_tail")).toBe(1); // 이어 읽기 사슬이 헛돌지 않음
    const polls0 = h.n("org_status");
    for (let i = 0; i < 3; i++) {
      await h.advance(1000);
      h.core.pollTick();
      await h.advance(10);
    }
    // 1초 맞춤은 헛돌지 않는다 — 늘어난 tail 은 3초 조회 안전망(검증 V5 · 조회 1번에 1번)뿐
    expect(h.n("chat_transcript_tail") - 1).toBe(h.n("org_status") - polls0);
    expect(h.n("chat_transcript_tail")).toBeLessThan(3);
    h.st.openTail = 0;
    h.st.file.push(h.rec(2));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 2, reset: false });
    await h.advance(10);
    expect(h.seen()).toBe(2);
  });

  it("c_tail_shorter_than_path_is_reset — tail(쥔 핸들) 길이 < 사건(경로 stat) 길이 = 다른 파일(윈 터널링 · 더 긴 재생성) → reset · 다시 걸기(고착 0)", async () => {
    const h = chHarness();
    await watched(h);
    h.st.file.push(h.rec(1));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 1, reset: false });
    await h.advance(10);
    expect(h.seen()).toBe(1);
    h.st.heldLen = 1; // 경로는 다른 파일(더 김) · 핸들은 옛 파일(길이 1)
    h.st.file = [h.rec(7), h.rec(8), h.rec(9)];
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 3, reset: false });
    await h.advance(10);
    expect(h.n("chat_transcript_unwatch")).toBe(1);
    expect(h.n("chat_transcript_watch")).toBe(2);
    h.st.heldLen = null;
    for (let i = 0; i < 3; i++) {
      await h.advance(1000);
      h.core.pollTick();
      await h.advance(10);
    }
    expect(h.n("chat_transcript_tail")).toBeLessThan(5); // 매초 헛도는 맞춤 0
  });

  it("c_names_match_rust — 사건 이름(TS·Rust 두 정의) 같음 · core 가 부르는 새 명령 4개 = main.rs 등재 · tail 응답 칸 이름 = Rust", () => {
    const rs = readFileSync(new URL("../../../src-tauri/src/viewcore.rs", import.meta.url), "utf8");
    expect(/pub\(crate\) const CHAT_TRANSCRIPT_CHANGED: &str = "([^"]+)";/.exec(rs)?.[1]).toBe(CHAT_TRANSCRIPT_CHANGED);
    const main = readFileSync(new URL("../../../src-tauri/src/main.rs", import.meta.url), "utf8");
    const reg = main.slice(main.indexOf("tauri::generate_handler!["), main.indexOf("\n        ])", main.indexOf("tauri::generate_handler![")));
    const core = readFileSync(new URL("./core.ts", import.meta.url), "utf8") + readFileSync(new URL("./index.ts", import.meta.url), "utf8");
    for (const c of ["chat_transcript_watch", "chat_transcript_unwatch", "chat_transcript_tail", "chat_compat_env"]) {
      expect(core.includes(`invoke("${c}"`)).toBe(true);
      expect(reg.split("\n").some((l) => l.trim().startsWith(`viewcore::${c},`))).toBe(true);
      expect(rs.includes(`pub async fn ${c}(`) || rs.includes(`pub fn ${c}(`)).toBe(true);
    }
    for (const k of ['"from_offset"', '"to_offset"', '"more"', '"gen"', '"surface_id"', '"reset"', '"size"']) expect(rs).toContain(k);
  });

  it("index.ts 배선 — chat_compat_env 를 처음 물을 때 1회 · Deps.compat1118 로 넘김 · 저장 키 0", () => {
    const src = readFileSync(new URL("./index.ts", import.meta.url), "utf8");
    expect(src.match(/invoke\("chat_compat_env"/g)?.length).toBe(1);
    expect(/\n    compat1118[,:]/.test(src)).toBe(true); // ChatCore Deps 에 넘김
    expect(src.includes("cys-chat-compat-1118")).toBe(false);
  });
});
