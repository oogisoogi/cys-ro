// (TICKET=cysr-1121-ui K) 대화 화면 「붙잡아 둠」 — 11-26 윈 제보(「오래 기다린 말이에요 · 보낼까요?」 = 보냈다고 여김) + 11-27 사용자 제보
//   (「붙잡아둠, 앞 말을 보낸 뒤 보낼게요…」 · 작업 화면에서도 이런 텀이 있나). 판정 = workers/cysr-1121-ui/K-JUDGE.md · master 10:2x 결정.
//   K-1 글: 자동으로 나갈 말 = 「보낼 차례 기다림」 · 눌러야 나갈 말 = 「아직 안 보냄」 · 10분 말 안내 첫 마디 = 「아직 안 보냈어요」.
//   K-2 10분 상한 좁힘: 받아들인 뒤 같은 좌석에 다른 길 사람 입력이 없으면 10분 넘어도 자동(「(N분 전에 쓰신 말)」 표지) · 있으면 클릭 · 「보내지 않기」 단추.
//   K-3 바쁠 때도 넘김(U25 실측 = 받아 둔다): queue-operation enqueue → 「마스터가 받아 둠」 · attachment.queued_command(→ user 레코드) → 「전달됨」.
// 대조군 = fafe3eee1(v1.1.20): U25_BUSY_PASTE_OK=false(바쁘면 붙잡음) · accepted 단계·noOtherHumanInputSince·discardHeld·agedPrefix 없음 → 아래 전부 붉음.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { agedPrefix, ChatCore, DISCARD_FAILED_NOTE, DUP, dupPending, HELD_MAX_AGE_MS, HELD_REFUSED_BACKOFF_MS, HOLD_KEY, STALE, STALE_NOTE, type Deps } from "./core";
import { HUMAN_GAP_MAX, noOtherHumanInputSince, sendGate, type MasterRow } from "./judge/gate";
import { ABSORBED_NOTE, ACCEPTED_NOTE, applyRecords, canRetry, HELD_CLICK_LABEL, mergeOutcome, QUEUE_REMOVED_NOTE, rematchPending, settleSteps, SLOW_MS, STEP_LABEL, WITH_NEXT_NOTE, type Msg, type Rec } from "./judge/msgstep";

const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");

/** 데몬 흉내 — 사람 입력 표지 = `<세대>:<번호>` · 원자 제출이 쓰이면 번호 +1 · 다른 길 입력 = other() */
function harness(o: { approvals?: number[]; working?: boolean; stampKey?: boolean; outcomes?: string[] } = {}) {
  const calls: Array<{ cmd: string; args?: Record<string, unknown> }> = [];
  const mem = new Map<string, string>();
  const outs = [...(o.outcomes ?? [])]; // (K R1) 원자 제출 응답 차례 — 비면 written
  let storeFail = false; // (K R1) 저장소 쓰기 실패 흉내
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
        const oc = outs.shift() ?? "written";
        if (oc === "held" || oc === "failed") return { outcome: oc, code: oc === "failed" ? "send_failed" : "approval_open" }; // 바이트 0 = 번호 그대로
        seq += 1;
        return { outcome: oc, result: { sent: true, human_input_stamp: stamp() } }; // written · uncertain(불명도 표지를 실어 올 수 있음 · viewcore.rs classify_send)
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
    store: {
      get: (k) => mem.get(k) ?? null,
      set: (k, v) => {
        if (storeFail) throw new Error("quota");
        mem.set(k, v);
      },
      remove: (k) => {
        if (storeFail) throw new Error("quota");
        mem.delete(k);
      },
    },
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
    failStore: (v: boolean) => void (storeFail = v),
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
    expect(CHAT).toContain('needsClick(m) ? HELD_CLICK_LABEL : stepLabel(m)'); // (kfix ②·④) 단계 이름 = stepLabel
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
  it("(C안 · 1.1.21 내림) 마스터가 답하는 중이면 기본값은 붙잡는다(쓰기 0) — 「바쁠 때 넘김」 끔", async () => {
    const h = harness({ working: true });
    await h.core.send("바쁠 때 보낸 말");
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].step).toBe("held");
  });
  const base = (o: Partial<Msg> = {}): Msg => ({ id: "m1", text: "U25-B 첫 줄\n둘째 줄", createdAt: 1_000, sentAt: 1_000, step: "injected", thread: [], replies: [], wrote: true, ...o }); // (kfix ②) 데몬이 썼다고 답한 말
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
  it("(C안) 기본값 = 바쁨 붙잡음 · gate 인자 true 면 넘김(K-3 길은 코드에 남음)", () => {
    const m: MasterRow = { surface_id: 5, exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: true };
    expect(sendGate({ master: m, approvalSeats: [] }).ok).toBe(false);
    expect(sendGate({ master: m, approvalSeats: [], busyPasteOk: true })).toEqual({ ok: true });
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
    expect(h.core.state.msgs[0].text).toBe("그 파일 지워 줘"); // (K R1) 원문은 그대로
    expect(h.core.state.msgs[0].sentText).toBe("(10분 전에 쓰신 말) 그 파일 지워 줘"); // 짝짓기 대상 = 이번 시도에 실제 보낸 글
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

// (TICKET=cysr-1121-ui K R1) codex 1R REVISE 고침 — review/K-codex-r1.json issues ⑤·④·③·①·⑥·minor.
describe("K R1 ⑤ 원문 보존 — 10분 표지는 시도마다 원문에서 한 번만(sentText) · 겹침·다시 보내기는 원문으로", () => {
  const ORIG = "그 파일 지워 줘";
  const P = "(10분 전에 쓰신 말) ";
  it("붙잡음 → 10분 넘어 자동 → 데몬 거부(붙잡음) → 다시 자동 = 표지 한 번씩 · 원문·저장본 그대로", async () => {
    const h = harness({ approvals: [5], outcomes: ["held", "written"] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes()).toHaveLength(1);
    const m = h.core.state.msgs[0];
    expect(m.step).toBe("held");
    expect(m.text).toBe(ORIG);
    expect(m.sentText).toBeUndefined(); // 붙잡음으로 돌아가면 지움
    expect(JSON.parse(h.mem.get(HOLD_KEY) as string).items.map((x: { text: string }) => x.text)).toEqual([ORIG]);
    h.setNow(h.getNow() + HELD_REFUSED_BACKOFF_MS + 1);
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual([P + ORIG, P + ORIG]);
    expect(h.core.state.msgs[0].text).toBe(ORIG);
    expect(h.core.state.msgs[0].sentText).toBe(P + ORIG);
  });
  it("표지 붙여 보낸 말이 불명 → 사람이 원문을 다시 침 = 같은 말 겹침(쓰기 0) · 표지 붙은 기록이 오면 그 말이 「전달됨」", async () => {
    const h = harness({ approvals: [5], outcomes: ["uncertain"] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual([P + ORIG]);
    expect(h.core.state.msgs[0].step).toBe("checking");
    h.setNow(h.getNow() + 60_000);
    await h.core.send(ORIG);
    expect(h.writes()).toHaveLength(1);
    expect(h.core.state.msgs[1].code).toBe(DUP);
    expect(dupPending(h.core.state.msgs, ORIG, h.core.state.msgs[1].id)).toBe(true);
    // 짝짓기 = sentText
    const m0 = h.core.state.msgs[0];
    const r = applyRecords([m0], [{ uuid: "u1", parent: null, role: "user", text: P + ORIG, ts: new Date(m0.sentAt as number).toISOString() }]);
    expect(r.msgs[0].step).toBe("delivered");
    expect(applyRecords([m0], [{ uuid: "u2", parent: null, role: "user", text: ORIG, ts: new Date(m0.sentAt as number).toISOString() }]).msgs[0].step).toBe("checking");
    expect(rematchPending([m0], [{ r: { uuid: "u3", parent: null, role: "user", text: P + ORIG, ts: null }, seenAt: (m0.sentAt as number) + 1 }]).msgs[0].step).toBe("delivered");
  });
  it("표지 붙여 보낸 말이 확정 실패 → 다시 보내기 = 원문(새 말 · 10분 안 = 표지 없음)", async () => {
    const h = harness({ approvals: [5], outcomes: ["failed"] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    const m = h.core.state.msgs[0];
    expect(m.step).toBe("failed");
    expect(m.text).toBe(ORIG);
    expect(canRetry(m)).toBe(true);
    await h.core.retry(m.id);
    expect(h.writes().map((c) => c.args?.text)).toEqual([P + ORIG, ORIG]);
  });
  it("확정 실패 → 다시 보낸 말이 또 10분 넘게 붙잡힘 → 새 표지 한 번만(겹침 0)", async () => {
    const h = harness({ approvals: [5], outcomes: ["failed"] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    h.st.approvals = [5];
    await h.core.retry(h.core.state.msgs[0].id);
    expect(h.writes()).toHaveLength(1);
    expect(h.core.state.msgs[1].step).toBe("held");
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 120_001);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual([P + ORIG, "(12분 전에 쓰신 말) " + ORIG]);
  });
});

describe("K R1 ④ 대기에서 빠짐(흡수 아닌 remove) — 「받아 둠」을 사실로 두지 않음", () => {
  const ts = (ms: number) => new Date(ms).toISOString();
  const acc = (o: Partial<Msg> = {}): Msg => ({ id: "m1", text: "거둔 말", createdAt: 1_000, sentAt: 1_000, step: "accepted", note: ACCEPTED_NOTE, thread: [], replies: [], wrote: true, queuedSeen: true, ...o }); // (kfix ④) 대기 들어감을 본 말
  const rm = (text: string, at: number, reason: string | null): Rec => ({ uuid: null, parent: null, role: "queue_removed", text, ts: ts(at), reason });
  it("같은 글 remove(까닭 = 사람 거둠 · 모르는 꼴 · 없음) → 「확인 중」 + 확인 불가 안내 · 다시 보내기 0", () => {
    for (const reason of ["user_cancelled", "weird_reason", null]) {
      const r = applyRecords([acc()], [rm("거둔 말", 30_000, reason)]);
      expect(r.msgs[0].step).toBe("checking");
      expect(r.msgs[0].code).toBe("queue_removed");
      expect(r.msgs[0].note).toBe(QUEUE_REMOVED_NOTE);
      expect(canRetry(r.msgs[0])).toBe(false);
      expect(r.consumed).toEqual([]);
      expect(r.unmatched).toEqual([]);
    }
  });
  it("다른 글 · 받아 둠 아닌 말 · 보내기 전 시각 = 그대로 · 표지 붙여 보낸 말은 sentText 로 대조", () => {
    expect(applyRecords([acc()], [rm("다른 말", 30_000, "x")]).msgs[0].step).toBe("accepted");
    expect(applyRecords([acc({ step: "injected", queuedSeen: undefined })], [rm("거둔 말", 30_000, "x")]).msgs[0].step).toBe("injected"); // 대기 들어감을 못 본 말
    expect(applyRecords([acc()], [rm("거둔 말", -10_000, "x")]).msgs[0].step).toBe("accepted");
    expect(applyRecords([acc({ sentText: "(10분 전에 쓰신 말) 거둔 말" })], [rm("(10분 전에 쓰신 말) 거둔 말", 30_000, "x")]).msgs[0].step).toBe("checking");
  });
  it("빠진 뒤 같은 글 user 레코드가 오면 「전달됨」으로 고쳐짐(확인 중도 짝 후보)", () => {
    const r1 = applyRecords([acc()], [rm("거둔 말", 30_000, "x")]);
    const r2 = applyRecords(r1.msgs, [{ uuid: "u1", parent: null, role: "user", text: "거둔 말", ts: ts(31_000) }]);
    expect(r2.msgs[0].step).toBe("delivered");
    expect(r2.msgs[0].note).toBeUndefined();
  });
});

describe("K R1 ③ 하던 일 중간 흡수 — U25-B·U25-D 실측 꼴 재생(u25-evidence/u25-records.txt)", () => {
  const T = (iso: string) => Date.parse(iso);
  const mk = (id: string, text: string, sentIso: string): Msg => ({ id, text, createdAt: T(sentIso), sentAt: T(sentIso), step: "injected", thread: [], replies: [], wrote: true });
  it("U25-B: 앞 일 도구 결과 → 흡수(queued_command) → 앞 일 「DONE」 = 이 말 답 아님(일반 마스터 줄 · kfix ③) · 같이 흡수된 앞 말 없음", () => {
    const m0 = mk("m0", "Run this bash command once and wait for it to finish: ping -c 30 127.0.0.1 | tail -1 .", "2026-11-27T01:28:51.000Z");
    const m1 = mk("m1", "U25-B 시험 첫 줄\n둘째 줄 끝", "2026-11-27T01:29:00.000Z");
    const recs: Rec[] = [
      { uuid: "f5731a73", parent: null, role: "user", text: m0.text, ts: "2026-11-27T01:28:51.230Z" },
      { uuid: "b5ec5e08", parent: "f5731a73", role: "assistant", text: null, ts: "2026-11-27T01:28:52.586Z", tools: [{ name: "Bash", hint: null }] },
      { uuid: null, parent: null, role: "queued", text: m1.text, ts: "2026-11-27T01:29:00.750Z" },
      { uuid: "e302bd9b", parent: "b5ec5e08", role: "user", text: null, ts: "2026-11-27T01:29:34.894Z" },
      { uuid: "866cf6e4", parent: "e302bd9b", role: "link", text: null, ts: null },
      { uuid: "9fcf96ba", parent: "866cf6e4", role: "user", text: m1.text, ts: "2026-11-27T01:29:00.748Z", queued: true },
      { uuid: "6d6fedba", parent: "9fcf96ba", role: "link", text: null, ts: null },
      { uuid: "996df2d3", parent: "6d6fedba", role: "assistant", text: null, ts: "2026-11-27T01:29:38.421Z", thinking: true },
      { uuid: "1490af3c", parent: "996df2d3", role: "assistant", text: "DONE\n\nThe ping command finished, but its summary line", ts: "2026-11-27T01:29:39.067Z" },
    ];
    const r = applyRecords([m0, m1], recs);
    const [a, b] = r.msgs;
    expect(a.absorbed).toBeUndefined();
    expect(b.userUuid).toBe("9fcf96ba");
    expect(b.absorbed).toBe(true);
    expect(b.withNext).toBeUndefined();
    expect(b.replies).toEqual([]); // (kfix ③) 앞 일 이야기가 섞인 글 = 이 말의 답으로 붙이지 않음
    expect(r.stray.map((x) => x.text)).toEqual(["DONE\n\nThe ping command finished, but its summary line"]);
    expect(a.replies).toEqual([]);
  });
  it("U25-D: 두 말이 한 경계에서 흡수 → 앞 말 = 「다음 말과 함께」(withNext) · 한 답 = 일반 마스터 줄(kfix ③)", () => {
    const m0 = mk("m0", "Run this bash command once and wait for it to finish: ping -c 20 127.0.0.1 | tail -1 .", "2026-11-27T01:30:33.000Z");
    const m1 = mk("m1", "U25-D 말 1", "2026-11-27T01:30:39.500Z");
    const m2 = mk("m2", "U25-D 말 2", "2026-11-27T01:30:41.700Z");
    const recs: Rec[] = [
      { uuid: "b9e21a57", parent: null, role: "user", text: m0.text, ts: "2026-11-27T01:30:33.603Z" },
      { uuid: "57bc30fd", parent: "b9e21a57", role: "assistant", text: null, ts: "2026-11-27T01:30:34.558Z", tools: [{ name: "Bash", hint: null }] },
      { uuid: null, parent: null, role: "queued", text: "U25-D 말 1", ts: "2026-11-27T01:30:40.274Z" },
      { uuid: null, parent: null, role: "queued", text: "U25-D 말 2", ts: "2026-11-27T01:30:42.431Z" },
      { uuid: "a1d98cfe", parent: "57bc30fd", role: "user", text: null, ts: "2026-11-27T01:31:06.620Z" },
      { uuid: "adbdfe23", parent: "a1d98cfe", role: "user", text: "U25-D 말 1", ts: "2026-11-27T01:30:40.273Z", queued: true },
      { uuid: "8e8063c5", parent: "adbdfe23", role: "user", text: "U25-D 말 2", ts: "2026-11-27T01:30:42.429Z", queued: true },
      { uuid: "2b488b42", parent: "8e8063c5", role: "link", text: null, ts: null },
      { uuid: "0ab84299", parent: "2b488b42", role: "assistant", text: null, ts: "2026-11-27T01:31:08.209Z", thinking: true },
      { uuid: "3f2373c8", parent: "0ab84299", role: "assistant", text: "DONE\n\nU25-D 말 1 확인\nU25-D 말 2 확인\n\nThe ping fin", ts: "2026-11-27T01:31:08.356Z" },
    ];
    const r1 = applyRecords([m0, m1, m2], recs.slice(0, 4));
    expect(r1.msgs.map((m) => m.step)).toEqual(["delivered", "accepted", "accepted"]);
    const r = applyRecords(r1.msgs, recs.slice(4));
    const [, a, b] = r.msgs;
    expect(a.absorbed).toBe(true);
    expect(a.withNext).toBe("m2");
    expect(a.replies).toEqual([]);
    expect(b.absorbed).toBe(true);
    expect(b.withNext).toBeUndefined();
    expect(b.replies).toEqual([]);
    expect(r.stray.map((x) => x.text)).toEqual(["DONE\n\nU25-D 말 1 확인\nU25-D 말 2 확인\n\nThe ping fin"]);
    const settled = settleSteps(r.msgs, T("2026-11-27T01:31:10.000Z"), false);
    expect(settled[1].step).toBe("delivered");
    expect(settled[2].step).toBe("delivered"); // (kfix ③) 앞 일 완료문만으로 「답함」 확정 0
  });
  it("앞 흡수 말이 이미 답을 받았으면 「함께」 아님 · 흡수 아닌 보통 user 레코드 = 표지 없음", () => {
    const m1: Msg = { id: "m1", text: "말 1", createdAt: 1_000, sentAt: 1_000, step: "replying", userUuid: "q1", thread: ["q1", "a1"], replies: [{ uuid: "a1", text: "말 1 답" }], absorbed: true };
    const m2: Msg = { id: "m2", text: "말 2", createdAt: 2_000, sentAt: 2_000, step: "accepted", thread: [], replies: [] };
    const r = applyRecords([m1, m2], [{ uuid: "q2", parent: "a1", role: "user", text: "말 2", ts: new Date(3_000).toISOString(), queued: true }]);
    expect(r.msgs[0].withNext).toBeUndefined();
    expect(r.msgs[1].absorbed).toBe(true);
    const plain = applyRecords([{ ...m2, step: "injected" }], [{ uuid: "u2", parent: null, role: "user", text: "말 2", ts: new Date(3_000).toISOString() }]);
    expect(plain.msgs[0].absorbed).toBeUndefined();
  });
  it("확정 결과로 결속을 풀면 흡수 표지도 풂 · 화면 배선 = 앞 말 「함께」 · 흡수 말 안내", () => {
    const m: Msg = { id: "m1", text: "말", createdAt: 1, sentAt: 1, step: "delivered", userUuid: "q", thread: ["q"], replies: [], absorbed: true, withNext: "m2" };
    const p = mergeOutcome(m, "failed");
    expect(p.absorbed).toBeUndefined();
    expect("absorbed" in p && "withNext" in p).toBe(true);
    expect(ABSORBED_NOTE).toBe("하던 일 중간에 받아 읽었어요 — 그 뒤 마스터 글은 하던 일 이야기와 섞여 있어 아래 「마스터」 줄로 따로 보여요");
    expect(WITH_NEXT_NOTE).toBe("다음 말과 함께 받아 읽었어요 — 그 뒤 마스터 글은 아래 「마스터」 줄로 따로 보여요");
    const CHAT = strip(readFileSync(new URL("./chat/index.ts", import.meta.url), "utf8"));
    // (kfix2 ②′) 흡수·함께 안내는 absorbedNote 한 곳(확인 못 함이면 단정 없는 문구) — 확인된 말은 위 두 문구 그대로(kfix2_1121.test.ts 가 값 검사).
    expect(CHAT).toContain('const ab = absorbedNote(m);');
    expect(CHAT).toContain('if (ab) li.append(el("div", "cv-note cv-absorbed", ab));');
  });
});

describe("K R1 ① 남의 사람 차례 — 표지가 같아도 세션 기록에 남의 user 차례가 나타나면 10분 넘은 말 = 클릭", () => {
  it("10분 넘게 붙잡힘 · 표지 불변 · 받아들인 뒤 남의 user 레코드(RC·다른 기기) → 「아직 안 보냈어요」 · 쓰기 0", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send("그 파일 지워 줘");
    h.st.file.push({ uuid: "f1", parent: null, role: "user", text: "다른 기기에서 친 말", ts: new Date(h.getNow() + 1_000).toISOString() });
    await h.core.readTranscript("event");
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
    expect(h.core.state.msgs[0].note).toBe(STALE_NOTE);
  });
  it("남의 차례가 받아들이기 전 시각이면 그대로 자동(대조군)", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send("그 파일 지워 줘");
    h.st.file.push({ uuid: "f1", parent: null, role: "user", text: "앞서 친 말", ts: new Date(h.getNow() - 60_000).toISOString() });
    await h.core.readTranscript("event");
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["(10분 전에 쓰신 말) 그 파일 지워 줘"]);
  });
});

describe("K R1 ⑥ 내 표지 = written 만", () => {
  it("앞 말이 불명(표지 실어 옴) → 그 번호는 내 것이 아님 → 뒤 말이 10분 넘으면 클릭 · 쓰기 0", async () => {
    const h = harness({ outcomes: ["uncertain"] });
    await h.core.poll();
    await h.core.send("앞 말");
    expect(h.writes()).toHaveLength(1);
    h.st.approvals = [5];
    await h.core.send("뒷 말");
    const back = h.core.state.msgs[1];
    expect(back.step).toBe("held");
    expect(back.heldStamp).toBe("1795:3"); // 받아들일 때 본 표지 = 불명 쓰기(1795:4) 앞
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes()).toHaveLength(1);
    expect(h.core.state.msgs[1].code).toBe(STALE);
  });
  it("대조군 — 앞 말이 written 이면 그 번호는 내 것 → 뒤 말 10분 넘어도 자동", async () => {
    const h = harness({ outcomes: ["written"] });
    await h.core.poll();
    await h.core.send("앞 말");
    h.st.approvals = [5];
    await h.core.send("뒷 말");
    expect(h.core.state.msgs[1].heldStamp).toBe("1795:3");
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["앞 말", "(10분 전에 쓰신 말) 뒷 말"]);
  });
});

describe("K R1 minor 「보내지 않기」 저장 실패 = 말을 지우지 않음", () => {
  it("저장소에 못 쓰면 말 그대로 + 「거두지 못했어요」 · 저장본에도 남음 · 다시 누르면 거둠", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send("거둘 말");
    const id = h.core.state.msgs[0].id;
    h.failStore(true);
    h.core.discardHeld(id);
    expect(h.core.state.msgs.map((m) => m.id)).toEqual([id]);
    expect(h.core.state.notice).toBe(DISCARD_FAILED_NOTE);
    expect(JSON.parse(h.mem.get(HOLD_KEY) as string).items).toHaveLength(1);
    h.failStore(false);
    h.core.discardHeld(id);
    expect(h.core.state.msgs).toHaveLength(0);
    expect(h.mem.get(HOLD_KEY)).toBeUndefined();
  });
});
