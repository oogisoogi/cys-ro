// (TICKET=cysr-1121-ui-kfix) 통합 codex 2R REVISE(cysr-1121-integ-K-r2-codex.json) major 4건 — 재현 시험(고치기 전 붉음 · 고친 뒤 초록).
//   ① 10분 보호: 이미 읽은 남의 user 만 셈 → 남의 enqueue · 아직 안 읽은 기록 · 기록 읽기 실패 때 10분 넘은 말이 자동으로 나감(같은 지시 두 번).
//   ② 이 화면 제출이 불명인 동안 다른 길로 같은 글이 오면 「전달됨/받아 둠」 = 거짓 안심.
//   ③ 하던 일 중간 흡수(queued_command) 뒤 마스터 글 = 앞 일 출력이 새 말의 답으로 붙고 「답함」이 됨.
//   ④ 대기에서 빠짐(remove): accepted 에서만 · slow 뒤 무시 · 늦은 written 이 덮음 · 종결 없음(같은 글을 영영 막음).
// 새 이름(stepLabel·UNSURE_NOTE 등)은 이름공간으로 읽는다 — 고치기 전에도 파일이 읽혀 시험마다 붉음이 따로 보이게.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import * as C from "./core";
import * as MS from "./judge/msgstep";
import type { Deps } from "./core";
import type { Msg, Rec } from "./judge/msgstep";

const { ChatCore, HELD_MAX_AGE_MS, STALE, dupPending } = C;
const { applyRecords, mergeOutcome, settleSteps, SLOW_MS, STEP_LABEL, QUEUE_REMOVED_NOTE } = MS;
const label = (m: Msg): string => (MS as unknown as { stepLabel?: (m: Msg) => string }).stepLabel?.(m) ?? "stepLabel 없음";
const iso = (ms: number) => new Date(ms).toISOString();
const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");

/** 데몬 흉내(kheld1121 harness + 기록 읽기 실패 · 원자 제출 응답 늦추기) */
function harness(o: { approvals?: number[]; working?: boolean; outcomes?: string[]; deferSend?: boolean ; agedAutoSend?: boolean } = {}) {
  const calls: Array<{ cmd: string; args?: Record<string, unknown> }> = [];
  const mem = new Map<string, string>();
  const outs = [...(o.outcomes ?? [])];
  let now = 5_000_000;
  let seq = 3;
  let readFail = false;
  const gates: Array<() => void> = [];
  const st = { approvals: o.approvals ?? [], working: o.working ?? false, sid: 5, file: [] as Array<Record<string, unknown>> };
  const stamp = () => `1795:${seq}`;
  const row = () => ({ surface_id: st.sid, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: st.working, human_input_stamp: stamp() });
  const deps: Deps = {
    agedAutoSend: o.agedAutoSend, // (1.1.21 B안) 생략 = 끔
    invoke: async (cmd, args) => {
      calls.push({ cmd, args });
      if (cmd === "org_status") return { surfaces: [row()] };
      if (cmd === "feed_list") return { items: st.approvals.map((sid) => ({ kind: "approval", status: "pending", surface_id: sid })) };
      if (cmd === "chat_send") {
        if (o.deferSend) await new Promise<void>((res) => gates.push(res));
        const oc = outs.shift() ?? "written";
        if (oc === "held" || oc === "failed") return { outcome: oc, code: oc === "failed" ? "send_failed" : "approval_open" };
        seq += 1;
        return { outcome: oc, result: { sent: true, human_input_stamp: stamp() } };
      }
      if (cmd === "chat_transcript") {
        const a = (args ?? {}) as { afterOffset?: number; fromEnd?: boolean };
        if (a.fromEnd) return { status: "ok", session_id: "s-k", next_offset: st.file.length, size: st.file.length, records: [] };
        if (readFail) return null;
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
  return {
    core,
    st,
    writes: () => calls.filter((c) => c.cmd === "chat_send"),
    setNow: (t: number) => void (now = t),
    getNow: () => now,
    failRead: (v: boolean) => void (readFail = v),
    release: () => gates.shift()?.(),
  };
}
const tick = () => new Promise<void>((r) => setTimeout(r, 0));

describe("① 10분 보호 — 남의 enqueue · 안 읽은 기록 · 읽기 실패 = 클릭(자동 0)", () => {
  const ORIG = "그 파일 지워 줘";
  async function aged(h: ReturnType<typeof harness>) {
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    await h.core.poll();
  }
  it("받아들인 뒤 남의 enqueue(표지 안 늘어남 · 아직 흡수 안 됨)를 읽음 → 10분 넘은 말 = 클릭", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.st.file.push({ uuid: null, parent: null, role: "queued", text: "작업 화면에서 넣은 같은 지시", ts: iso(h.getNow() + 1_000) });
    await h.core.readTranscript("event");
    await aged(h);
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("마스터가 계속 바쁨(busy · U25 넘김) + 남의 enqueue → 클릭", async () => {
    const h = harness({ approvals: [5], working: true });
    await h.core.poll();
    await h.core.send(ORIG);
    h.st.file.push({ uuid: null, parent: null, role: "queued", text: "다른 기기에서 넣은 말", ts: iso(h.getNow() + 1_000) });
    await h.core.readTranscript("event");
    await aged(h);
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("남의 user 레코드가 기록에 있으나 아직 안 읽음 → 쓰기 전에 끝까지 읽고 클릭", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.st.file.push({ uuid: "f1", parent: null, role: "user", text: "RC 로 친 말", ts: iso(h.getNow() + 1_000) }); // readTranscript 부르지 않음 = 읽기 늦음
    await aged(h);
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("기록 읽기 실패(확인 못 함) → 클릭", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.failRead(true);
    await aged(h);
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("대조군 — 남의 입력 0 · 기록 끝까지 읽힘 → 10분 넘어도 자동(표지)", async () => {
    const h = harness({ agedAutoSend: true,  approvals: [5] });
    await h.core.poll();
    await h.core.send(ORIG);
    await aged(h);
    expect(h.writes().map((c) => c.args?.text)).toEqual([`(10분 전에 쓰신 말) ${ORIG}`]);
  });
});

describe("② 불명 제출 중 같은 글 — 「전달됨」·「받아 둠」으로 칠하지 않음(거짓 안심 0)", () => {
  const T = "배포 멈춰";
  const chk = (o: Partial<Msg> = {}): Msg => ({ id: "m1", text: T, createdAt: 1_000, sentAt: 1_000, step: "checking", code: "invoke_error", thread: [], replies: [], ...o });
  const user = (at: number): Rec => ({ uuid: "u1", parent: null, role: "user", text: T, ts: iso(at) });
  const enq = (at: number): Rec => ({ uuid: null, parent: null, role: "queued", text: T, ts: iso(at) });
  it("쓰였는지 모름(checking) + 같은 글 user 레코드 → 이름 ≠ 「전달됨」 · 출처 확인 불가 안내 · 답은 붙임", () => {
    const r = applyRecords([chk()], [user(1_500), { uuid: "a1", parent: "u1", role: "assistant", text: "멈췄어요", ts: iso(2_000) }]);
    const m = r.msgs[0];
    expect(label(m)).not.toBe(STEP_LABEL.delivered);
    expect(label(m)).not.toBe(STEP_LABEL.replying);
    expect((m as Msg & { unsure?: boolean }).unsure).toBe(true);
    expect(m.note).toBe((MS as unknown as { UNSURE_NOTE?: string }).UNSURE_NOTE);
    expect(m.replies.map((x) => x.text)).toEqual(["멈췄어요"]);
    expect(label(settleSteps(r.msgs, 3_000, false)[0])).not.toBe(STEP_LABEL.replied);
  });
  it("쓰였는지 모름 + 같은 글 enqueue → 이름 ≠ 「마스터가 받아 둠」", () => {
    const m = applyRecords([chk()], [enq(1_500)]).msgs[0];
    expect(label(m)).not.toBe(STEP_LABEL.accepted);
    expect((m as Msg & { unsure?: boolean }).unsure).toBe(true);
  });
  it("대조군 — 데몬이 썼다고 답한 말(wrote) = 「전달됨」·「받아 둠」 그대로", () => {
    expect(label(applyRecords([chk({ step: "injected", code: undefined, wrote: true } as Partial<Msg>)], [user(1_500)]).msgs[0])).toBe(STEP_LABEL.delivered);
    expect(label(applyRecords([chk({ step: "injected", code: undefined, wrote: true } as Partial<Msg>)], [enq(1_500)]).msgs[0])).toBe(STEP_LABEL.accepted);
  });
  it("화면 길: 불명 응답 → 다른 길 같은 글 기록 → 「전달됨」 아님", async () => {
    const h = harness({ outcomes: ["uncertain"] });
    await h.core.poll();
    await h.core.send(T);
    h.st.file.push({ uuid: "u9", parent: null, role: "user", text: T, ts: iso(h.getNow() + 500) });
    await h.core.readTranscript("event");
    expect(label(h.core.state.msgs[0])).not.toBe(STEP_LABEL.delivered);
    expect((h.core.state.msgs[0] as Msg & { unsure?: boolean }).unsure).toBe(true); // 같은 글 기록은 붙였으되(답 받기) 출처 확인 불가 표지
  });
  it("화면 길: 응답 오기 전에 같은 글 기록이 읽힘 → 뒤이어 written 이 오면 그때 「전달됨」", async () => {
    const h = harness({ deferSend: true });
    await h.core.poll();
    const p = h.core.send(T);
    for (let i = 0; i < 5; i++) await tick();
    expect(h.writes()).toHaveLength(1);
    h.st.file.push({ uuid: "u9", parent: null, role: "user", text: T, ts: iso(h.getNow() + 500) });
    await h.core.readTranscript("event");
    expect(label(h.core.state.msgs[0])).not.toBe(STEP_LABEL.delivered);
    h.release();
    await p;
    expect(label(h.core.state.msgs[0])).toBe(STEP_LABEL.delivered);
    expect(h.core.state.msgs[0].note).toBeUndefined();
  });
  it("화면 배선 — 말 단계 이름 = stepLabel(m)", () => {
    const CHAT = strip(readFileSync(new URL("./chat/index.ts", import.meta.url), "utf8"));
    expect(CHAT).toContain("needsClick(m) ? HELD_CLICK_LABEL : stepLabel(m)");
  });
});

describe("③ 하던 일 중간 흡수 — 그 뒤 마스터 글은 그 말의 답으로 붙이지 않음(일반 「마스터」 줄)", () => {
  const T0 = (s: string) => Date.parse(s);
  const mk = (id: string, text: string, sentIso: string): Msg => ({ id, text, createdAt: T0(sentIso), sentAt: T0(sentIso), step: "injected", thread: [], replies: [], wrote: true } as Msg);
  it("U25-B 재생: 흡수 말의 replies 0 · 앞 일 「DONE」 = stray · 쉬어도 「답함」 아님", () => {
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
    const b = r.msgs[1];
    expect(b.absorbed).toBe(true);
    expect(b.replies).toEqual([]);
    expect(r.stray.map((x) => x.text)).toEqual(["DONE\n\nThe ping command finished, but its summary line"]);
    expect(r.msgs[0].replies).toEqual([]);
    const s = settleSteps(r.msgs, T0("2026-11-27T01:29:45.000Z"), false);
    expect(s[1].step).not.toBe("replied");
  });
  it("U25-D 재생: 두 흡수 말 모두 replies 0 · 한 답 = stray · 둘 다 「답함」 아님", () => {
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
    const r = applyRecords([m0, m1, m2], recs);
    expect(r.msgs[1].replies).toEqual([]);
    expect(r.msgs[2].replies).toEqual([]);
    expect(r.msgs[1].withNext).toBe("m2");
    expect(r.stray.map((x) => x.text)).toEqual(["DONE\n\nU25-D 말 1 확인\nU25-D 말 2 확인\n\nThe ping fin"]);
    const s = settleSteps(r.msgs, T0("2026-11-27T01:31:10.000Z"), false);
    expect(s[1].step).not.toBe("replied");
    expect(s[2].step).not.toBe("replied");
  });
  it("대조군 — 흡수 아닌 보통 user 레코드 뒤 글 = 그 말의 답", () => {
    const m = mk("m1", "보통 말", "2026-11-27T01:00:00.000Z");
    const r = applyRecords([m], [
      { uuid: "u1", parent: null, role: "user", text: "보통 말", ts: "2026-11-27T01:00:00.500Z" },
      { uuid: "a1", parent: "u1", role: "assistant", text: "보통 답", ts: "2026-11-27T01:00:02.000Z" },
    ]);
    expect(r.msgs[0].replies.map((x) => x.text)).toEqual(["보통 답"]);
    expect(r.stray).toEqual([]);
  });
});

describe("④ 대기에서 빠짐 — slow 뒤에도 · 늦은 응답보다 우선 · 종결(같은 글 다시 보낼 수 있음)", () => {
  const T = "거둔 말";
  const acc = (o: Partial<Msg> = {}): Msg => ({ id: "m1", text: T, createdAt: 1_000, sentAt: 1_000, step: "accepted", note: MS.ACCEPTED_NOTE, thread: [], replies: [], wrote: true, queuedSeen: true, ...o } as Msg);
  const rm = (at: number): Rec => ({ uuid: null, parent: null, role: "queue_removed", text: T, ts: iso(at), reason: "user_cancelled" });
  it("받아 둠 → 쉬는데 120초 넘음(slow) → remove = 빠짐으로", () => {
    const slow = settleSteps([acc()], 1_000 + SLOW_MS + 1, false);
    expect(slow[0].step).toBe("slow");
    expect(mergeOutcome(slow[0], "injected").step).toBeUndefined(); // 받아 둔 뒤 오래 걸려요 = 늦은 written 이 「전달 확인 중」으로 되돌리지 않음
    const r = applyRecords(slow, [rm(1_000 + SLOW_MS + 5_000)]);
    expect(r.msgs[0].code).toBe("queue_removed");
    expect(r.msgs[0].note).toBe(QUEUE_REMOVED_NOTE);
  });
  it("enqueue → remove → 늦은 written·불명 응답 = 빠짐 안내 그대로", () => {
    const removed = applyRecords([acc()], [rm(30_000)]).msgs[0];
    expect(removed.code).toBe("queue_removed");
    expect(mergeOutcome(removed, "injected").step).toBeUndefined();
    expect(mergeOutcome(removed, "checking").step).toBeUndefined();
    expect(mergeOutcome(removed, "held").step).toBe("held"); // 확정(바이트 0)은 늘 이김 — 그 대기 말은 이 화면 것이 아니었다
  });
  it("화면 길: 응답 오기 전에 enqueue·remove 가 읽힘 → 뒤이어 written = 빠짐 안내 그대로", async () => {
    const h = harness({ deferSend: true });
    await h.core.poll();
    const p = h.core.send(T);
    for (let i = 0; i < 5; i++) await tick();
    h.st.file.push({ uuid: null, parent: null, role: "queued", text: T, ts: iso(h.getNow() + 300) });
    h.st.file.push({ uuid: null, parent: null, role: "queue_removed", text: T, ts: iso(h.getNow() + 900), reason: "user_cancelled" });
    await h.core.readTranscript("event");
    h.release();
    await p;
    expect(h.core.state.msgs[0].code).toBe("queue_removed");
    expect(h.core.state.msgs[0].note).toBe(QUEUE_REMOVED_NOTE);
  });
  it("종결: 빠진 말 = 「오래 걸려요」로 안 바뀜 · 이름 「대기에서 빠짐」 · 같은 글 새 말을 막지 않음", () => {
    const removed = applyRecords([acc()], [rm(30_000)]).msgs[0];
    expect(settleSteps([removed], 1_000 + SLOW_MS * 3, false)[0].step).toBe(removed.step);
    expect(label(removed)).toBe("대기에서 빠짐");
    expect(dupPending([removed], T)).toBe(false);
  });
  it("빠진 말과 새로 보낸 같은 글이 함께 기다릴 때 같은 글 기록은 새 말에 먼저 짝", () => {
    const removed = applyRecords([acc()], [rm(30_000)]).msgs[0];
    const fresh: Msg = { id: "m2", text: T, createdAt: 40_000, sentAt: 40_000, step: "injected", thread: [], replies: [], wrote: true } as Msg;
    const r = applyRecords([removed, fresh], [{ uuid: "u1", parent: null, role: "user", text: T, ts: iso(41_000) }]);
    expect(r.msgs[1].step).toBe("delivered");
    expect(r.msgs[0].code).toBe("queue_removed");
  });
});
