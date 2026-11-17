// (cysr-ui-slice1) 공통층 보내기 길 시험 — 대역 데몬(invoke 기록기) · 가짜 시계·타이머.
// 판정 단위 = 「PTY 쓰기 = chat_send 호출 수」(원자 제출 1요청 = 쓰기 1 · 데몬 거부는 바이트 0).
import { describe, it, expect } from "bun:test";
import { ChatCore, HELD_REFUSED_BACKOFF_MS, HOLD_KEY, HOLD_MAX, healthOf, LOG_MAX, OBS_MAX_MS, RESTORED, type Deps } from "./core";
import { READ_AFTER_MS } from "./judge/msgstep";

interface Call {
  cmd: string;
  args?: Record<string, unknown>;
}

function harness(o: { master?: Record<string, unknown> | null; approvals?: number[]; sendOutcome?: Record<string, unknown> | (() => Record<string, unknown>); orgFail?: boolean; feedFail?: boolean; transcript?: Array<Record<string, unknown>> } = {}) {
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
    ["에이전트 죽음", { master: { surface_id: 5, role: "master", agent_alive: false, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false } }],
    ["관문", { master: { surface_id: 5, role: "master", agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: { k: 1 } } }],
    ["다른 길 사람 입력 3초 전", { master: { surface_id: 5, role: "master", agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, human_idle_secs: 3 } }],
    ["바쁨(U25 측정 대기)", { master: { surface_id: 5, role: "master", agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, working: true } }],
  ];
  for (const [name, o] of cases)
    it(name, async () => {
      const h = harness(o);
      await h.core.send("안녕");
      expect(h.writes()).toHaveLength(0);
      expect(h.core.state.msgs[0].step).toBe("held");
      expect(JSON.parse(h.mem.get(HOLD_KEY) as string).items[0].text).toBe("안녕"); // 붙잡은 말만 원문 보관
    });
  it("붙잡은 말 = 문턱이 열린 틱에 오래된 것 1건씩 · 보내면 저장소에서 지움", async () => {
    const h = harness({ approvals: [5] });
    await h.core.send("하나");
    await h.core.send("둘");
    expect(h.writes()).toHaveLength(0);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["하나"]);
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["하나", "둘"]);
    expect(h.mem.has(HOLD_KEY)).toBe(false);
  });
  it("앱을 다시 켜도 붙잡은 말이 남는다(cys-chat-hold) · ★자동 제출 0 — 사람이 「이 말 보내기」를 눌러야 다듬기부터 다시(codex 1R)", async () => {
    const h = harness({ master: null });
    await h.core.send("남아라");
    h.st.master = { surface_id: 5, role: "master", agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null };
    const again = new ChatCore(h.deps);
    expect(again.state.msgs.map((m) => [m.text, m.step, m.code])).toEqual([["남아라", "held", RESTORED]]);
    for (let i = 0; i < 5; i++) await again.poll();
    expect(h.writes()).toHaveLength(0);
    await again.confirmRestored(again.state.msgs[0].id);
    expect(h.writes().map((c) => c.args?.text)).toEqual(["남아라"]);
  });
  it("저장소에서 읽은 `/clear`(변조·손상) = 자동 제출 0 · 눌러도 다듬기에서 막힘", async () => {
    const h = harness();
    h.mem.set(HOLD_KEY, JSON.stringify({ v: 1, items: [{ id: "x1", text: "/clear", at: 1 }] }));
    const c = new ChatCore(h.deps);
    for (let i = 0; i < 3; i++) await c.poll();
    await c.confirmRestored(c.state.msgs[0].id);
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
    await c.confirmRestored(c.state.msgs[0].id);
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
  });
});
