// (TICKET=cysr-1121-ui K) 대화 화면 「붙잡아 둠」 — 11-26 윈 제보(「오래 기다린 말이에요 · 보낼까요?」 = 보냈다고 여김) + 11-27 사용자 제보
//   (「붙잡아둠, 앞 말을 보낸 뒤 보낼게요…」 · 작업 화면에서도 이런 텀이 있나). 판정 = workers/cysr-1121-ui/K-JUDGE.md · master 10:2x 결정.
//   K-1 글: 자동으로 나갈 말 = 「보낼 차례 기다림」 · 눌러야 나갈 말 = 「아직 안 보냄」 · 10분 말 안내 첫 마디 = 「아직 안 보냈어요」.
//   K-2 10분 상한 좁힘: 받아들인 뒤 같은 좌석에 다른 길 사람 입력이 없으면 10분 넘어도 자동(「(N분 전에 쓰신 말)」 표지) · 있으면 클릭 · 「보내지 않기」 단추.
//   K-3 바쁠 때도 넘김(U25 실측 = 받아 둔다): queue-operation enqueue → 「마스터가 받아 둠」 · attachment.queued_command(→ user 레코드) → 「전달됨」.
// 대조군 = fafe3eee1(v1.1.20): U25_BUSY_PASTE_OK=false(바쁘면 붙잡음) · accepted 단계·noOtherHumanInputSince·discardHeld·agedPrefix 없음 → 아래 전부 붉음.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { agedPrefix, ChatCore, dupPending, HELD_MAX_AGE_MS, HOLD_KEY, STALE, STALE_NOTE, type Deps } from "./core";
import { HUMAN_GAP_MAX, noOtherHumanInputSince, sendGate, type MasterRow } from "./judge/gate";
import { ACCEPTED_NOTE, applyRecords, HELD_CLICK_LABEL, mergeOutcome, settleSteps, SLOW_MS, STEP_LABEL, type Msg, type Rec } from "./judge/msgstep";

const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");

/** 데몬 흉내 — 사람 입력 표지 = `<세대>:<번호>` · 원자 제출이 쓰이면 번호 +1 · 다른 길 입력 = other() */
function harness(o: { approvals?: number[]; working?: boolean; stampKey?: boolean } = {}) {
  const calls: Array<{ cmd: string; args?: Record<string, unknown> }> = [];
  const mem = new Map<string, string>();
  let now = 5_000_000;
  let seq = 3;
  const st = {
    approvals: o.approvals ?? [],
    working: o.working ?? false,
    sid: 5,
    file: [] as Array<Record<string, unknown>>,
  };
  const stamp = () => (seq === 0 ? null : `1795:${seq}`);
  const row = () => {
    const r: Record<string, unknown> = { surface_id: st.sid, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: st.working };
    if (o.stampKey !== false) r.human_input_stamp = stamp();
    return r;
  };
  const deps: Deps = {
    invoke: async (cmd, args) => {
      calls.push({ cmd, args });
      if (cmd === "org_status") return { surfaces: [row()] };
      if (cmd === "feed_list") return { items: st.approvals.map((sid) => ({ kind: "approval", status: "pending", surface_id: sid })) };
      if (cmd === "chat_send") {
        seq += 1;
        return { outcome: "written", result: { sent: true, human_input_stamp: stamp() } };
      }
      if (cmd === "chat_transcript") {
        const a = (args ?? {}) as { afterOffset?: number; fromEnd?: boolean };
        if (a.fromEnd) return { status: "ok", session_id: "s-k", next_offset: st.file.length, size: st.file.length, records: [] };
        return { status: "ok", session_id: "s-k", next_offset: st.file.length, size: st.file.length, records: st.file.slice(a.afterOffset ?? 0) };
      }
      return null;
    },
    now: () => now,
    setTimeout: () => 0,
    clearTimeout: () => {},
    store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v), remove: (k) => void mem.delete(k) },
    working: (r) => r.working === true,
  };
  const core = new ChatCore(deps);
  core.attach();
  const writes = () => calls.filter((c) => c.cmd === "chat_send");
  return {
    core,
    st,
    mem,
    writes,
    other: () => void (seq += 1), // 작업 화면 등 다른 길로 사람이 마스터 창에 침
    setNow: (t: number) => void (now = t),
    getNow: () => now,
  };
}

describe("K-1 글 — 사람이 해야 할 일이 단계 이름에 든다", () => {
  it("자동으로 나갈 말 = 「보낼 차례 기다림」 · 눌러야 나갈 말 = 「아직 안 보냄」 · 10분 말 = 「아직 안 보냈어요」로 시작", () => {
    expect(STEP_LABEL.held).toBe("보낼 차례 기다림");
    expect(HELD_CLICK_LABEL).toBe("아직 안 보냄");
    expect(STALE_NOTE.startsWith("아직 안 보냈어요")).toBe(true);
    expect(Object.values(STEP_LABEL)).not.toContain("붙잡아 둠");
    const CHAT = strip(readFileSync(new URL("./chat/index.ts", import.meta.url), "utf8"));
    expect(CHAT).toContain('needsClick(m) ? HELD_CLICK_LABEL : STEP_LABEL[m.step]');
  });
  it("줄 선 말·답하는 중 안내 = 「그대로 두시면」·「누르실 것 없어요」", async () => {
    const CORE = readFileSync(new URL("./core.ts", import.meta.url), "utf8");
    const GATE = readFileSync(new URL("./judge/gate.ts", import.meta.url), "utf8");
    expect(CORE).toContain("앞 말이 전해진 뒤 이어서 보낼게요 — 그대로 두시면 돼요.");
    expect(CORE).not.toContain("앞 말을 보낸 뒤 보낼게요.");
    expect(GATE).toContain("답이 끝나면 저절로 보내요(누르실 것 없어요)");
  });
});

describe("K-3 바쁠 때도 넘김 — U25 실측(받아 둔다)", () => {
  it("마스터가 답하는 중이어도 기본값은 쓴다(쓰기 1 · 붙잡음 0)", async () => {
    const h = harness({ working: true });
    await h.core.send("바쁠 때 보낸 말");
    expect(h.writes().map((c) => c.args?.text)).toEqual(["바쁠 때 보낸 말"]);
    expect(h.core.state.msgs[0].step).not.toBe("held");
  });
  const base = (o: Partial<Msg> = {}): Msg => ({ id: "m1", text: "U25-B 첫 줄\n둘째 줄", createdAt: 1_000, sentAt: 1_000, step: "injected", thread: [], replies: [], ...o });
  const ts = (ms: number) => new Date(ms).toISOString();
  const enq = (text: string, at: number): Rec => ({ uuid: null, parent: null, role: "queued", text, ts: ts(at) });
  it("enqueue = 「마스터가 받아 둠」(짝 uuid 없음 · 사슬 0) → 흡수 queued_command(user 레코드) = 「전달됨」 → 그 뒤 답 = 이 말의 답", () => {
    const r1 = applyRecords([base()], [enq("U25-B 첫 줄\n둘째 줄", 1_700)]);
    expect(r1.msgs[0].step).toBe("accepted");
    expect(r1.msgs[0].note).toBe(ACCEPTED_NOTE);
    expect(r1.msgs[0].userUuid).toBeUndefined();
    expect(r1.msgs[0].thread).toEqual([]);
    expect(r1.consumed).toEqual([]);
    const q: Rec = { uuid: "q1", parent: "p0", role: "user", text: "U25-B 첫 줄\n둘째 줄", ts: ts(1_700) };
    const a: Rec = { uuid: "a1", parent: "q1", role: "assistant", text: "받았어요", ts: ts(40_000) };
    const r2 = applyRecords(r1.msgs, [q, a]);
    expect(r2.msgs[0].step).toBe("replying");
    expect(r2.msgs[0].userUuid).toBe("q1");
    expect(r2.msgs[0].replies.map((x) => x.text)).toEqual(["받았어요"]);
  });
  it("다른 글 · 보내기 전 시각 · 이미 짝 있는 말 = enqueue 로 바뀌지 않음", () => {
    expect(applyRecords([base()], [enq("다른 글", 1_700)]).msgs[0].step).toBe("injected");
    expect(applyRecords([base()], [enq("U25-B 첫 줄\n둘째 줄", -10_000)]).msgs[0].step).toBe("injected");
    expect(applyRecords([base({ step: "delivered", userUuid: "u9" })], [enq("U25-B 첫 줄\n둘째 줄", 1_700)]).msgs[0].step).toBe("delivered");
  });
  it("받아 둔 말 = 마스터가 일하는 동안 120초가 넘어도 「오래 걸려요」 아님 · 쉬는데 120초 넘게 안 읽히면 「오래 걸려요」", () => {
    const m = base({ step: "accepted" });
    expect(settleSteps([m], 1_000 + SLOW_MS + 1, true)[0].step).toBe("accepted");
    expect(settleSteps([m], 1_000 + SLOW_MS + 1, null)[0].step).toBe("accepted");
    expect(settleSteps([m], 1_000 + SLOW_MS + 1, false)[0].step).toBe("slow");
    expect(settleSteps([m], 1_000 + SLOW_MS - 1, false)[0].step).toBe("accepted");
  });
  it("늦게 온 written·불명 응답은 「받아 둠」을 되돌리지 않음 · 확정(붙잡음·못 보냄)은 이김", () => {
    expect(mergeOutcome(base({ step: "accepted" }), "injected")).toEqual({});
    expect(mergeOutcome(base({ step: "accepted" }), "checking")).toEqual({});
    expect(mergeOutcome(base({ step: "accepted" }), "held")).toEqual({ step: "held" });
  });
  it("받아 둔 말과 같은 글을 또 보내면 = 같은 말 겹침(두 번 가지 않게 · UNRESOLVED 에 받아 둠 포함)", () => {
    expect(dupPending([base({ step: "accepted" })], "U25-B 첫 줄\n둘째 줄")).toBe(true);
    expect(dupPending([base({ step: "accepted" })], "다른 글")).toBe(false);
  });
  it("되돌리기 = gate 인자 false 면 종전(바쁨 붙잡음)", () => {
    const m: MasterRow = { surface_id: 5, exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: true };
    expect(sendGate({ master: m, approvalSeats: [] })).toEqual({ ok: true });
    expect(sendGate({ master: m, approvalSeats: [], busyPasteOk: false }).ok).toBe(false);
  });
});

describe("K-2 10분 상한 좁힘 — 받아들인 뒤 같은 좌석 다른 길 사람 입력 0 이면 자동", () => {
  it("noOtherHumanInputSince — 같음 · 늘어난 번호가 전부 내 것 · 그 밖(모름 포함) = false", () => {
    const own = new Set(["1795:4", "1795:5"]);
    expect(noOtherHumanInputSince("1795:3", "1795:3", new Set())).toBe(true);
    expect(noOtherHumanInputSince("1795:3", "1795:5", own)).toBe(true);
    expect(noOtherHumanInputSince("1795:3", "1795:5", new Set(["1795:5"]))).toBe(false); // 4 = 다른 길 입력
    expect(noOtherHumanInputSince("", "1795:2", new Set(["1795:1", "1795:2"]))).toBe(true); // 받아들일 때 입력 없음(null) → 1·2 둘 다 내 것
    expect(noOtherHumanInputSince("", null, new Set())).toBe(true);
    expect(noOtherHumanInputSince("1795:3", null, new Set())).toBe(false); // 번호가 0 으로 되돌아감 = 모름
    expect(noOtherHumanInputSince("1795:3", "1799:3", new Set())).toBe(false); // 데몬 다시 켜짐(세대 다름)
    expect(noOtherHumanInputSince("1795:5", "1795:4", new Set())).toBe(false); // 줄어듦
    expect(noOtherHumanInputSince(undefined, "1795:3", new Set())).toBe(false); // 기준 모름
    expect(noOtherHumanInputSince("1795:3", undefined, new Set())).toBe(false); // 지금 칸 없음(옛 데몬)
    expect(noOtherHumanInputSince("1795:3", "x:4", new Set())).toBe(false); // 꼴 틀림
    const many = new Set(Array.from({ length: HUMAN_GAP_MAX + 1 }, (_, i) => `1795:${i + 4}`));
    expect(noOtherHumanInputSince("1795:3", `1795:${HUMAN_GAP_MAX + 4}`, many)).toBe(false); // 차이 상한
  });
  it("승인 대기로 10분 넘게 붙잡힘 · 그 사이 다른 길 입력 0 → 문턱이 열리면 자동 · 앞에 「(N분 전에 쓰신 말)」", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send("그 파일 지워 줘");
    expect(h.writes()).toHaveLength(0);
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    await h.core.poll(); // 아직 승인 대기 — 10분 넘었지만 다른 길 입력 0 = 클릭으로 바꾸지 않음
    expect(h.core.state.msgs[0].code).not.toBe(STALE);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual([`${agedPrefix(HELD_MAX_AGE_MS + 1)}그 파일 지워 줘`]);
    expect(agedPrefix(HELD_MAX_AGE_MS + 1)).toBe("(10분 전에 쓰신 말) ");
    expect(h.core.state.msgs[0].text).toBe("(10분 전에 쓰신 말) 그 파일 지워 줘"); // 짝짓기 대상 = 실제 보낸 글
  });
  it("그 사이 다른 길 사람 입력 1회 → 10분 뒤 클릭 대기(「아직 안 보냈어요」) · 자동 0 · 누르면 원래 글로", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send("그 파일 지워 줘");
    h.other();
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    for (let i = 0; i < 3; i++) await h.core.poll();
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
    expect(h.core.state.msgs[0].note).toBe(STALE_NOTE);
    await h.core.confirmHeld(h.core.state.msgs[0].id);
    expect(h.writes().map((c) => c.args?.text)).toEqual(["그 파일 지워 줘"]);
  });
  it("10분 안의 다른 길 입력은 종전대로(30초 쉼 · 자동) — 이 규칙은 10분 넘은 말에만", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send("짧게 기다린 말");
    h.other();
    h.setNow(h.getNow() + 60_000);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["짧게 기다린 말"]);
  });
  it("마스터 좌석이 바뀜(다른 번호) → 10분 뒤 클릭", async () => {
    const h = harness({ approvals: [5, 6] });
    await h.core.poll();
    await h.core.send("옛 좌석에 쓴 말");
    h.st.sid = 6;
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("표지 칸 없는 옛 데몬 = 모름 → 10분 뒤 클릭(종전)", async () => {
    const h = harness({ approvals: [5], stampKey: false });
    await h.core.poll();
    await h.core.send("옛 데몬");
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("「보내지 않기」 = 붙잡은 말만 거둠(목록·저장소에서 지움 · 쓰기 0) · 보낸 말·없는 id = 그대로", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send("거둘 말");
    const id = h.core.state.msgs[0].id;
    expect(JSON.parse(h.mem.get(HOLD_KEY) as string).items).toHaveLength(1);
    h.core.discardHeld("없는 id");
    expect(h.core.state.msgs).toHaveLength(1);
    h.core.discardHeld(id);
    expect(h.core.state.msgs).toHaveLength(0);
    const kept = h.mem.get(HOLD_KEY); // 붙잡은 말 0 = 저장소 칸을 지우거나 빈 목록
    expect(kept === undefined || JSON.parse(kept).items.length === 0).toBe(true);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes()).toHaveLength(0);
    await h.core.send("보낸 말");
    const sent = h.core.state.msgs[0];
    h.core.discardHeld(sent.id);
    expect(h.core.state.msgs).toHaveLength(1);
  });
  it("화면 배선 — 붙잡은 말에 「보내지 않기」(신뢰 클릭만)", () => {
    const CHAT = strip(readFileSync(new URL("./chat/index.ts", import.meta.url), "utf8"));
    expect(CHAT).toMatch(/if \(m\.step === "held"\) \{\s*const d = el\("button", "cv-retry cv-discard", "보내지 않기"\);/);
    expect(CHAT).toMatch(/if \(!e\.isTrusted\) return;[^\n]*\n\s*act\.discardHeld\(m\.id\);/);
  });
});
