// (TICKET=cysr-1118u-chat ③) 윈 1.1.17 관찰(2374 05:56): 사람 말이 아닌 중계(RC 다리) 메시지로 시작한 턴의 진행 줄이 앞 사람 말 밑에 「답하는 중」으로 붙음.
// 채록(맥 master 세션 기록 · Claude Code 2.1.329): 중계로 시작한 턴의 첫 레코드 =
//   {type:"user", isMeta:true, turnOrigin:"peer", origin:{kind:"peer", from:"bridge:session_…"}, message.content = 문자열 "Another Claude session sent a message:\n<cross-session-message …>…"}
//   부모 = 앞 턴 끝(assistant end_turn → attachment·system 고리) · viewcore.rs 파서 → {role:"user", text:<그 문자열>}.
//   (같은 기록 표본: 턴 중에 온 중계 = attachment queued_command = 고리(11건 전부 도구 결과 뒤) · 도구 결과 바로 뒤의 글 있는 user = 그림 안내·스킬 본문·중단 표지 107건)
// 원인: 사슬은 msgstep :205 에서 닫히지만 앞 말의 단계는 그대로 → settleSteps 가 새 턴의 마스터 활동으로 「답하는 중」을 다시 칠함 · liveMsg 가 그 말에 진행 줄을 닮.
//   (빠른 연속: 앞 턴 끝과 중계 턴 시작 사이에 조회가 「쉼」을 못 보면 replying 이 그대로 남음)
// 대조군 = 기점(9c46ff6d0) — 아래 ①② 붉음 · ③(턴 안 덧붙임이 사슬을 끊음)도 기점 붉음.
import { describe, expect, it } from "bun:test";
import { applyRecords, settleSteps, type Msg, type Rec } from "./judge/msgstep";
import { liveMsg, progressLine } from "./judge/progress";

const T = Date.parse("2026-11-23T05:50:00Z");
const ts = (s: number) => new Date(T + s * 1000).toISOString();
const A: Msg = { id: "A", text: "오늘 할 일을 정리해 줘", createdAt: T, sentAt: T, step: "injected", thread: [], replies: [] };
const link = (uuid: string, parent: string): Rec => ({ uuid, parent, role: "link", text: null, ts: null });
const asst = (uuid: string, parent: string, text: string | null, tools: string[] = []): Rec => ({ uuid, parent, role: "assistant", text, ts: null, tools: tools.length ? tools.map((name) => ({ name, hint: null })) : null });
const result = (uuid: string, parent: string): Rec => ({ uuid, parent, role: "user", text: null, ts: ts(5) });
const PEER = 'Another Claude session sent a message:\n<cross-session-message from="bridge:session_01X" from-name="mac master" from-mode="bypass">\n[mac master] 윈 확인 부탁\n</cross-session-message>';

/** A 의 턴: 사람 말 → 도구 1 → 결과 → 답 글(end_turn) → 고리 2(attachment·system). withReply=false 면 답 글 없이 도구만. */
function turnA(withReply = true): Rec[] {
  return [
    { uuid: "uA", parent: "p0", role: "user", text: A.text, ts: ts(1) },
    asst("a1", "uA", null, ["Read"]),
    result("r1", "a1"),
    ...(withReply ? [asst("a2", "r1", "할 일 3가지예요.")] : [asst("a2", "r1", null, ["Bash"])]),
    link("l1", "a2"),
    link("l2", "l1"),
  ];
}
/** 중계로 시작한 턴: isMeta peer user(글 있음) → 도구 2 → 결과 → 답 글. */
const turnPeer: Rec[] = [
  { uuid: "uP", parent: "l2", role: "user", text: PEER, ts: ts(20) },
  asst("b1", "uP", null, ["Bash"]),
  result("rb1", "b1"),
  asst("b2", "rb1", null, ["Grep"]),
  result("rb2", "b2"),
  asst("b3", "rb2", "윈 확인 끝."),
];

function run(recs: Rec[], working: boolean | null): Msg {
  const r = applyRecords([A], recs);
  return settleSteps(r.msgs, T + 30_000, working)[0];
}

describe("③ 중계(peer)로 시작한 턴 = 앞 말 턴 끝", () => {
  it("① 빠른 연속(앞 턴 끝 → 바로 중계 턴 · 그 사이 「쉼」 관측 0): 앞 말 = 답함 · 진행 줄 살아 있지 않음 · 중계 턴 도구가 앞 말 과정에 0", () => {
    const m = run([...turnA(), ...turnPeer], true);
    expect(m.step).toBe("replied");
    expect(m.turnClosed).toBe(true);
    expect(liveMsg([m])).toBeNull();
    expect(progressLine(m, T + 30_000, liveMsg([m]) === m)?.live ?? false).toBe(false);
    expect((m.steps ?? []).map((s) => s.label).join(",")).not.toContain("Grep");
    expect(m.replies.map((x) => x.text)).toEqual(["할 일 3가지예요."]);
  });
  it("② 답 글 없이 끝난 앞 말(전달됨) + 중계 턴 중 마스터 일함 → 「답하는 중」으로 다시 칠하지 않음 · 진행 줄 0", () => {
    const m = run([...turnA(false), ...turnPeer], true);
    expect(m.step).toBe("delivered");
    expect(liveMsg([m])).toBeNull();
    // 한 번 더 조회(마스터 계속 일함)해도 그대로
    expect(settleSteps([m], T + 60_000, true)[0].step).toBe("delivered");
  });
  it("두 번에 나눠 읽어도 같다(앞 턴까지 읽고 replying → 다음 읽기에 중계 턴)", () => {
    const r1 = applyRecords([A], turnA());
    const s1 = settleSteps(r1.msgs, T + 10_000, true);
    expect(s1[0].step).toBe("replying");
    expect(liveMsg(s1)).toBe(s1[0]);
    const r2 = applyRecords(s1, turnPeer, new Set(r1.consumed));
    const s2 = settleSteps(r2.msgs, T + 30_000, true);
    expect(s2[0].step).toBe("replied");
    expect(liveMsg(s2)).toBeNull();
  });
  it("중계 턴의 답 글은 어느 말에도 묶이지 않은 「마스터」 일반 줄(stray)", () => {
    const r = applyRecords([A], [...turnA(), ...turnPeer]);
    expect(r.stray.map((x) => x.text)).toEqual(["윈 확인 끝."]);
  });
});

describe("③ 턴 안 덧붙임(도구 결과 바로 뒤의 글 있는 user)은 턴을 닫지 않는다", () => {
  const IMG = "[Image: original 2560x1600, displayed at 2420x1512.]";
  it("③ 그림 안내 뒤 도구가 계속 = 같은 말의 과정 · 진행 줄 살아 있음", () => {
    const recs: Rec[] = [
      { uuid: "uA", parent: "p0", role: "user", text: A.text, ts: ts(1) },
      asst("a1", "uA", null, ["Read"]),
      result("r1", "a1"),
      { uuid: "m1", parent: "r1", role: "user", text: IMG, ts: ts(2) },
      asst("a2", "m1", null, ["Grep"]),
    ];
    const r = applyRecords([A], recs);
    const m = settleSteps(r.msgs, T + 5_000, true)[0];
    expect(m.turnClosed).toBeUndefined();
    expect(m.step).toBe("replying");
    expect(m.thread).toContain("a2");
    expect((m.steps ?? []).length).toBe(2);
    expect(liveMsg([m])).toBe(m);
    expect(r.unmatched.length).toBe(0); // 사람 말 후보로 들고 있지 않음
  });
  it("중단 표지(도구 결과 뒤) 다음에 새로 친 사람 말 = 새 차례로 닫힘", () => {
    const recs: Rec[] = [
      { uuid: "uA", parent: "p0", role: "user", text: A.text, ts: ts(1) },
      asst("a1", "uA", "보는 중", ["Read"]),
      result("r1", "a1"),
      { uuid: "i1", parent: "r1", role: "user", text: "[Request interrupted by user for tool use]", ts: ts(2) },
      { uuid: "h2", parent: "i1", role: "user", text: "그만하고 다른 것", ts: ts(3) },
    ];
    const m = settleSteps(applyRecords([A], recs).msgs, T + 5_000, true)[0];
    expect(m.turnClosed).toBe(true);
    expect(m.step).toBe("replied");
  });
});

describe("③ codex 1R major — 결속이 풀렸다가 다시 묶이면 턴 끝 표지가 이월되지 않는다", () => {
  it("같은 글 외부 기록에 잘못 결속 → 다음 차례로 닫힘 → 늦은 held 응답(결속 풀림) → 실제 재전송 기록 결속 = 답하는 중 · 진행 줄", async () => {
    const { mergeOutcome } = await import("./judge/msgstep");
    // ① 같은 글의 외부 기록(작업 화면 직접 입력 등)에 잘못 결속 → 그 뒤 중계 턴으로 닫힘
    const wrong = applyRecords([A], [{ uuid: "uX", parent: "p0", role: "user", text: A.text, ts: ts(1) }, asst("x1", "uX", "다른 답"), link("lx", "x1"), { uuid: "uP", parent: "lx", role: "user", text: PEER, ts: ts(5) }]);
    let m = settleSteps(wrong.msgs, T + 6_000, true)[0];
    expect(m.turnClosed).toBe(true);
    // ② 늦게 온 확정 응답 = held(바이트 0) → 결속 풀림(mergeOutcome :313)
    m = { ...m, ...mergeOutcome(m, "held") };
    expect(m.userUuid).toBeNull();
    expect(m.turnClosed).toBeUndefined();
    // ③ 다시 보냄 → 실제 기록에 결속 → 마스터 일함 = 답하는 중 · 진행 줄
    m = { ...m, step: "injected", sentAt: T + 20_000 };
    const r = applyRecords([m], [{ uuid: "uA2", parent: "uP", role: "user", text: A.text, ts: ts(21) }, asst("a9", "uA2", null, ["Read"])], new Set(wrong.consumed));
    const s = settleSteps(r.msgs, T + 25_000, true)[0];
    expect(s.userUuid).toBe("uA2");
    expect(s.turnClosed).toBeUndefined();
    expect(s.step).toBe("replying");
    expect(liveMsg([s])).toBe(s);
  });
  it("rematchPending 으로 다시 묶일 때도 이월 0", async () => {
    const { rematchPending } = await import("./judge/msgstep");
    const closed: Msg = { ...A, step: "injected", sentAt: T, turnClosed: true, tail: "result" };
    const out = rematchPending([closed], [{ r: { uuid: "uA3", parent: "p0", role: "user", text: A.text, ts: ts(1) }, seenAt: T + 1_000 }]);
    expect(out.msgs[0].turnClosed).toBeUndefined();
    expect(out.msgs[0].tail).toBeUndefined();
  });
});
