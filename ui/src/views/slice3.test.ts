// (cysr-ui-slice3) 보낸 말 단계 전부 — §5-2 단계 표 fixture(전 행) · 공통층 시험 · 경합(불명 뒤 120초 안 다시 누름 = 중복 쓰기 0) · R3 30초.
// 판정 단위: 「쓰기 = chat_send 호출」(원자 제출 1요청) · 진실 = testkit Sim 의 쓰기 기록(바이트·Enter·세션 레코드·답).
import { describe, it, expect } from "bun:test";
import { DUP, dupPending, needsClick } from "./core";
import {
  applyRecords,
  applyRefusedAtWrite,
  canRetry,
  mergeOutcome,
  REFUSED_AT_WRITE_WINDOW_MS,
  SENDING_SILENT_MS,
  settleSteps,
  SLOW_MS,
  STEP_LABEL,
  stepFromOutcome,
  type Msg,
  type Step,
} from "./judge/msgstep";
import { applyQueueEvent, AUTO_HOLD_AFTER_HUMAN_MS, AUTO_STEP_LABEL, autoHoldRemainingMs, autoStepFor, queueEventOf, type AutoMsg, type QueueEvent } from "./judge/autostep";
import { composeOutbound } from "./judge/outbound";
import { Sim } from "./testkit";

const T = 1_000_000;
const msg = (p: Partial<Msg>): Msg => ({ id: "m1", text: "안녕", createdAt: T, sentAt: T, step: "injected", thread: [], replies: [], ...p });

// ───────────────────────── §5-2 단계 표 fixture — 행마다 「입력 → 단계」 ─────────────────────────
describe("§5-2 단계 표 fixture(사람 말 전 행)", () => {
  const rows: Array<[Step, string, () => Step]> = [
    ["held", "데몬 승인 창 거부(approval_screen) = 붙잡음(실패 아님)", () => stepFromOutcome("held")],
    ["queued_hold", "정비 보류 {held, hold_seq} = 차례 기다림", () => stepFromOutcome("queued_hold")],
    ["sending", "원자 제출 요청 중(응답 전 · 3초 안)", () => settleSteps([msg({ step: "sending" })], T + SENDING_SILENT_MS - 1, null)[0].step],
    ["injected", "원자 제출 성공(sent:true)", () => stepFromOutcome("written")],
    ["delivered", "sentAt 뒤 전문 일치 user 레코드", () => applyRecords([msg({})], [{ uuid: "u1", parent: "p", role: "user", text: "안녕", ts: new Date(T).toISOString() }]).msgs[0].step],
    ["replying", "전달 뒤 마스터 활동 = 작업 중", () => settleSteps([msg({ step: "delivered", userUuid: "u1", thread: ["u1"] })], T + 1, true)[0].step],
    ["replying", "전달 뒤 그 uuid 를 부모로 잇는 assistant 글", () => applyRecords([msg({ step: "delivered", userUuid: "u1", thread: ["u1"] })], [{ uuid: "a1", parent: "u1", role: "assistant", text: "네", ts: null }]).msgs[0].step],
    ["replied", "자손 assistant 글 + 활동 쉼", () => settleSteps([msg({ step: "replying", userUuid: "u1", thread: ["u1", "a1"], replies: [{ uuid: "a1", text: "네" }] })], T + 1, false)[0].step],
    ["failed", "확정 거부 코드(쓰기 전 거부)", () => stepFromOutcome("failed")],
    ["checking", "불명(Uncertain) 응답", () => stepFromOutcome("uncertain")],
    ["checking", "모르는 응답 꼴", () => stepFromOutcome("???")],
    ["checking", "응답 없이 3초", () => settleSteps([msg({ step: "sending" })], T + SENDING_SILENT_MS, null)[0].step],
    ["checking", "쓰기 직전 거부 사건(input.refused_at_write · 같은 좌석 · 5초 안)", () => applyRefusedAtWrite([msg({ seat: 5 })], 5, T + 600)[0].step],
    ["slow", "전달 확인 중 120초", () => settleSteps([msg({})], T + SLOW_MS, null)[0].step],
    ["slow", "확인 중 120초", () => settleSteps([msg({ step: "checking" })], T + SLOW_MS, null)[0].step],
  ];
  for (const [want, why, f] of rows) it(`${STEP_LABEL[want]} ← ${why}`, () => expect(f()).toBe(want));

  it("모든 단계에 화면 문구가 있다(행방 불명 0의 전제)", () => {
    const all: Step[] = ["held", "sending", "injected", "delivered", "replying", "replied", "failed", "checking", "slow", "queued_hold"];
    for (const s of all) expect(STEP_LABEL[s].length).toBeGreaterThan(0);
  });

  // 칠하지 말아야 할 것(틀림 0) — 조건 하나씩
  it("전달됨 아님: 보내기 전 시각 레코드 · 다른 글 · sidechain · assistant", () => {
    const old = { uuid: "u0", parent: null, role: "user" as const, text: "안녕", ts: new Date(T - 60_000).toISOString() };
    expect(applyRecords([msg({})], [old]).msgs[0].step).toBe("injected");
    expect(applyRecords([msg({})], [{ ...old, ts: null, text: "안녕하세요" }]).msgs[0].step).toBe("injected");
    expect(applyRecords([msg({})], [{ ...old, ts: null, sidechain: true }]).msgs[0].step).toBe("injected");
    expect(applyRecords([msg({})], [{ ...old, ts: null, role: "assistant" }]).msgs[0].step).toBe("injected");
  });
  it("답하는 중 아님: 활동 모름(null) · 쉼(false · 답 없음) · 아직 전달 전", () => {
    const d = msg({ step: "delivered", userUuid: "u1", thread: ["u1"] });
    expect(settleSteps([d], T + 1, null)[0].step).toBe("delivered");
    expect(settleSteps([d], T + 1, false)[0].step).toBe("delivered");
    expect(settleSteps([msg({})], T + 1, true)[0].step).toBe("injected");
  });
  it("답함 아님: 답 없음 · 활동 모름", () => {
    expect(settleSteps([msg({ step: "replying", thread: ["u1"] })], T + 1, false)[0].step).toBe("replying");
    expect(settleSteps([msg({ step: "replying", replies: [{ uuid: "a", text: "x" }] })], T + 1, null)[0].step).toBe("replying");
  });
  it("확인 중 아님: 보낸 지 3초 안 · 아직 보내기 전(sentAt 없음)", () => {
    expect(settleSteps([msg({ step: "sending" })], T + 2_999, null)[0].step).toBe("sending");
    expect(settleSteps([msg({ step: "sending", sentAt: null })], T + 9_999, null)[0].step).toBe("sending");
  });
  it("오래 걸려요 아님: 119.999초 · 전달됨·붙잡음·못 보냄은 시간으로 안 바뀜", () => {
    expect(settleSteps([msg({})], T + SLOW_MS - 1, null)[0].step).toBe("injected");
    for (const s of ["delivered", "held", "failed", "queued_hold"] as Step[]) expect(settleSteps([msg({ step: s })], T + 10 * SLOW_MS, null)[0].step).toBe(s);
  });
  it("쓰기 직전 거부 사건: 다른 좌석 · 창 밖 시각 · 이미 전달된 말 · 보내기 전 말 = 무시 · 둘이면 가장 최근 하나만", () => {
    expect(applyRefusedAtWrite([msg({ seat: 5 })], 6, T + 100)[0].step).toBe("injected");
    expect(applyRefusedAtWrite([msg({ seat: 5 })], 5, T + REFUSED_AT_WRITE_WINDOW_MS + 1)[0].step).toBe("injected");
    expect(applyRefusedAtWrite([msg({ seat: 5 })], 5, T - 1)[0].step).toBe("injected");
    expect(applyRefusedAtWrite([msg({ seat: 5, step: "delivered", userUuid: "u1" })], 5, T + 100)[0].step).toBe("delivered");
    expect(applyRefusedAtWrite([msg({ seat: 5, step: "held", sentAt: null })], 5, T + 100)[0].step).toBe("held");
    const two = applyRefusedAtWrite([msg({ id: "a", seat: 5, sentAt: T }), msg({ id: "b", seat: 5, sentAt: T + 1_000 })], 5, T + 1_500);
    expect(two.map((m) => m.step)).toEqual(["injected", "checking"]);
  });
  it("늦게 온 응답 합치기: 근거 단계는 written·불명으로 안 되돌림 · 확정(바이트 0)은 이기고 짝을 품 · 쓰기 직전 거부 표지 유지", () => {
    expect(mergeOutcome(msg({ step: "delivered", userUuid: "u1" }), "injected")).toEqual({});
    expect(mergeOutcome(msg({ step: "replied" }), "checking")).toEqual({});
    expect(mergeOutcome(msg({ step: "delivered", userUuid: "u1", thread: ["u1"] }), "failed")).toEqual({ step: "failed", userUuid: null, thread: [], replies: [] });
    expect(mergeOutcome(msg({ step: "checking", code: "refused_at_write" }), "injected")).toEqual({});
    expect(mergeOutcome(msg({ step: "checking", code: "no_answer_yet" }), "injected")).toEqual({ step: "injected" });
  });
  it("다시 보내기 = 확정 실패 + 아직 안 씀만(불명·확인 중·오래 걸려요·붙잡음·차례 기다림·쓰기 직전 거부 = 0)", () => {
    for (const s of ["held", "sending", "injected", "delivered", "replying", "replied", "checking", "slow", "queued_hold"] as Step[]) expect(canRetry(msg({ step: s }))).toBe(false);
    expect(canRetry(msg({ step: "failed" }))).toBe(true);
    expect(canRetry(msg({ step: "failed", retried: true }))).toBe(false);
  });
});

describe("§5-1 기계 문안 큐 사건 → 단계(fixture 전 행 · 이 판 데몬 칸 이름)", () => {
  const a: AutoMsg = { entryId: "q7", seat: 5, step: "queued", lastSeq: 0 };
  const ev = (name: string, payload: Record<string, unknown>, surfaceId: number | null = 5, seq = 10): QueueEvent => ({ name, seq, surfaceId, payload });
  const rows: Array<[string, QueueEvent, AutoMsg["step"] | null]> = [
    ["delivered queue_entry_id", ev("queue.delivered", { queue_entry_id: "q7", merged_ids: ["q7"] }), "delivered"],
    ["delivered 묶음(merged_ids 안)", ev("queue.delivered", { queue_entry_id: "q6", merged_ids: ["q6", "q7"] }), "delivered"],
    ["inject_aborted merged−disposed = 다시 시도 중", ev("queue.inject_aborted", { queue_entry_id: "q7", merged_ids: ["q7"], disposed_ids: [] }), "retrying"],
    ["inject_aborted disposed = 못 보냄", ev("queue.inject_aborted", { queue_entry_id: "q7", merged_ids: ["q7"], disposed_ids: ["q7"] }), "failed"],
    ["write_held = 반쯤 남음", ev("queue.write_held", { entry_ids: ["q7"], reason: "stalled" }), "partial"],
    ["write_released = 미배달로 풀림(다시 치지 않음)", ev("queue.write_released", { entry_ids: ["q7"], released: "composer_empty" }), "failed"],
    ["dropped", ev("queue.dropped", { queue_entry_ids: ["q7"], reason: "process_exited" }), "failed"],
    ["expired", ev("queue.expired", { queue_entry_id: "q7" }), "failed"],
    ["parked = 다시 켜지면 전달", ev("queue.parked", { queue_entry_ids: ["q7"] }), "parked"],
    ["rehomed = 같은 번호 차례 기다림", ev("queue.rehomed", { queue_entry_ids: ["q7"] }), "queued"],
    ["revived = 다시 큐로", ev("queue.revived", { queue_entry_id: "q7" }), "queued"],
    ["starved(같은 좌석 · 번호 없음) = 오래 걸려요", ev("queue.starved", {}), "slow"],
    ["starved 다른 좌석 = 무관", ev("queue.starved", {}, 6), null],
    ["다른 항목 delivered = 무관", ev("queue.delivered", { queue_entry_id: "q8", merged_ids: ["q8"] }), null],
    ["모르는 사건 = 무관", ev("queue.enqueued", { queue_entry_id: "q7" }), null],
  ];
  for (const [why, e, want] of rows) it(`${why} → ${want === null ? "변화 없음" : AUTO_STEP_LABEL[want]}`, () => expect(autoStepFor(a, e)?.step ?? null).toBe(want));
  it("끝난 항목은 안 바뀜 · seq 가 거꾸로 온 옛 사건은 무시", () => {
    const done = applyQueueEvent([{ ...a, step: "delivered" }], ev("queue.dropped", { queue_entry_ids: ["q7"] }));
    expect(done[0].step).toBe("delivered");
    const s1 = applyQueueEvent([a], ev("queue.parked", { queue_entry_ids: ["q7"] }, 5, 20));
    expect(s1[0].step).toBe("parked");
    const s2 = applyQueueEvent(s1, ev("queue.inject_aborted", { merged_ids: ["q7"], disposed_ids: [] }, 5, 19));
    expect(s2[0].step).toBe("parked");
  });
  it("queueEventOf: queue.* 만 · 칸 꼴이 틀리면 안전하게 비움", () => {
    expect(queueEventOf({ name: "input.refused_at_write" })).toBeNull();
    expect(queueEventOf(null)).toBeNull();
    expect(queueEventOf({ name: "queue.delivered", seq: "x", surface_id: "5", payload: 3 })).toEqual({ name: "queue.delivered", seq: null, surfaceId: null, payload: {} });
  });
  it("R3: 사람 보내기 뒤 기계 문안 묶임 = 실측 31.2초", () => {
    expect(AUTO_HOLD_AFTER_HUMAN_MS).toBe(31_200);
    expect(autoHoldRemainingMs(null, T)).toBe(0);
    expect(autoHoldRemainingMs(T, T + 1_000)).toBe(30_200);
    expect(autoHoldRemainingMs(T, T + 31_200)).toBe(0);
  });
});

// ───────────────────────── 공통층(core) — 대역 데몬 ─────────────────────────
async function ready(sim: Sim): Promise<void> {
  sim.core.attach();
  await sim.flush();
  await sim.core.poll();
  await sim.flush();
}

describe("core 조각 3 — 단계 길", () => {
  it("응답 없이 3초 → 「확인 중」 · 그동안 다시 보내기 0 · 응답 written 이 오면 「전달 확인 중」 → 기록 → 전달됨", async () => {
    const sim = new Sim({ plan: () => "hang_written", hangMs: 8_000, recordDelay: () => 20_000 });
    await ready(sim);
    sim.core.submit("안녕");
    await sim.flush();
    expect(sim.core.state.msgs[0].step).toBe("sending");
    await sim.advance(SENDING_SILENT_MS);
    const m = sim.core.state.msgs[0];
    expect(m.step).toBe("checking");
    expect(canRetry(m)).toBe(false);
    await sim.advance(5_100);
    expect(sim.core.state.msgs[0].step).toBe("injected");
    await sim.advance(21_000);
    await sim.core.readTranscript();
    expect(sim.core.state.msgs[0].step).toMatch(/^(delivered|replying)$/);
    expect(sim.sends()).toBe(1);
  });
  it("걸린 요청 중 기록이 먼저 보이면 전달됨 · 늦은 written 응답이 「전달 확인 중」으로 되돌리지 않음", async () => {
    const sim = new Sim({ plan: () => "hang_written", hangMs: 8_000, recordDelay: () => 100, replyDelay: () => null });
    await ready(sim);
    sim.core.submit("안녕");
    await sim.advance(7_000); // 3초 확인 중 → 기록 읽기(+1·+3초) → 전달됨
    expect(sim.core.state.msgs[0].step).toBe("delivered");
    await sim.advance(2_000); // 응답 도착
    expect(sim.core.state.msgs[0].step).toBe("delivered");
  });
  it("전달 → 마스터 일함 = 답하는 중 → 답 + 쉼 = 답함 (poll 관측으로만)", async () => {
    const sim = new Sim({ recordDelay: () => 100, replyDelay: () => 9_000 });
    await ready(sim);
    sim.startPolling();
    sim.core.submit("안녕");
    await sim.advance(1_200);
    expect(sim.core.state.msgs[0].step).toBe("delivered");
    await sim.advance(3_000);
    expect(sim.core.state.msgs[0].step).toBe("replying");
    await sim.advance(12_000);
    expect(sim.core.state.msgs[0].step).toBe("replied");
    expect(sim.core.state.msgs[0].replies.map((r) => r.text)).toEqual(["답 0"]);
  });
  it("M8 uuid 없는 기록 꼴: 전달됨까지만 · 답을 그 말에 묶지 않음(답함 0 · 일반 말풍선)", async () => {
    const sim = new Sim({ noUuid: true, recordDelay: () => 100, replyDelay: () => 500 });
    await ready(sim);
    sim.startPolling();
    sim.core.submit("안녕");
    await sim.advance(20_000);
    const m = sim.core.state.msgs[0];
    expect(["delivered", "replying"]).toContain(m.step);
    expect(m.replies).toHaveLength(0);
    expect(sim.core.state.stray.map((r) => r.text)).toEqual(["답 0"]);
  });
  it("쓰기 직전 거부 사건 → 「확인 중」 + 안내 · 다시 보내기 0 · 뒤 말은 입력줄 잔여로 붙잡힘(쓰기 0)", async () => {
    const sim = new Sim({ plan: (n) => (n === 0 ? "refuse_at_write" : "written") });
    await ready(sim);
    sim.startPolling();
    sim.core.submit("안녕");
    await sim.advance(600);
    const m = sim.core.state.msgs[0];
    expect(m.step).toBe("checking");
    expect(m.code).toBe("refused_at_write");
    expect(m.note).toMatch(/입력줄에 남았/);
    expect(canRetry(m)).toBe(false);
    sim.core.submit("둘째");
    await sim.advance(10_000);
    expect(sim.sends()).toBe(1);
    expect(sim.core.state.msgs[1].code).toBe("draft");
  });
  it("쓰기 직전 거부 사건: 부서 데몬(다른 소켓)·소켓 이름 모름 = 무시", async () => {
    const sim = new Sim({ plan: () => "written", recordDelay: () => null });
    await ready(sim);
    sim.core.submit("안녕");
    await sim.advance(100);
    sim.emit("input.refused_at_write", 5, { reason: "approval_screen" }, 1, "dept-slug");
    expect(sim.core.state.msgs[0].step).toBe("injected");
    sim.emit("input.refused_at_write", 5, { reason: "approval_screen" }, 2);
    expect(sim.core.state.msgs[0].step).toBe("checking");
  });
  it("사건 구독 = 대화 화면이 켜져 있을 때만(붙이기 전 default_socket_slug·listen 0 · 내리면 해제)", async () => {
    const sim = new Sim();
    expect(sim.calls.length).toBe(0);
    expect(sim.listens).toBe(0);
    sim.core.attach();
    await sim.flush();
    expect(sim.listens).toBe(1);
    sim.core.detach();
    expect(sim.unlistens).toBe(1);
    sim.core.attach();
    sim.core.detach(); // 구독이 서기 전에 내림 → 선 뒤 곧바로 해제(누수 0)
    await sim.flush();
    expect(sim.listens - sim.unlistens).toBe(0);
  });
});

describe("같은 말 겹침 — 중복 쓰기 0", () => {
  it("불명 → 같은 글 다시 보냄 = 쓰기 0 · 붙잡음(겹침) · 앞 말이 확인 중인 동안 「한 번 더」도 0 · 앞 말이 전달되면 사람 클릭 1회로 1건", async () => {
    const sim = new Sim({ plan: (n) => (n === 0 ? "uncertain_written" : "written"), recordDelay: (n) => (n === 0 ? 150_000 : 100) });
    await ready(sim);
    sim.startPolling();
    sim.core.submit("안녕");
    await sim.advance(1_000);
    expect(sim.core.state.msgs[0].step).toBe("checking");
    sim.core.submit("안녕");
    await sim.advance(100);
    expect(sim.sends()).toBe(1);
    const d = sim.core.state.msgs[1];
    expect(d.step).toBe("held");
    expect(d.code).toBe(DUP);
    expect(needsClick(d)).toBe(true);
    expect(dupPending(sim.core.state.msgs, d.text, d.id)).toBe(true); // 화면 단추 없음
    await sim.core.confirmHeld(d.id);
    expect(sim.sends()).toBe(1);
    await sim.advance(130_000);
    expect(sim.core.state.msgs[0].step).toBe("slow");
    expect(sim.sends()).toBe(1);
    await sim.advance(25_000); // 150초 뒤 첫 말 기록 → 전달됨
    await sim.core.readTranscript();
    expect(sim.core.state.msgs[0].step).toMatch(/delivered|replying|replied/);
    expect(dupPending(sim.core.state.msgs, d.text, d.id)).toBe(false);
    await sim.core.confirmHeld(d.id);
    await sim.advance(100);
    expect(sim.sends()).toBe(2);
  });
  it("★(하네스 seed 131) 확정 실패 X 뒤 같은 글 Y 가 확인 중이면 X 의 다시 보내기도 막음(쓰기 0 · 안내) · Y 가 전달되면 풀림", async () => {
    const sim = new Sim({ plan: (n) => (n === 0 ? "failed" : n === 1 ? "uncertain_written" : "written"), recordDelay: (n) => (n === 1 ? 200_000 : 100), replyDelay: () => null });
    await ready(sim);
    sim.startPolling();
    await sim.core.send("같은 글");
    const x = sim.core.state.msgs[0];
    expect(x.step).toBe("failed");
    sim.core.submit("같은 글"); // 실패한 말은 끝난 말 → 새 말 Y 는 겹침 아님 → 씀(불명)
    await sim.advance(40_000);
    expect(sim.sends()).toBe(2);
    expect(sim.core.state.msgs[1].step).toBe("checking");
    await sim.core.retry(x.id);
    await sim.advance(10_000);
    expect(sim.sends()).toBe(2);
    expect(sim.core.state.notice).toMatch(/확인 중/);
    await sim.advance(170_000); // Y 기록 → 전달됨
    await sim.core.readTranscript();
    expect(sim.core.state.msgs[1].step).toMatch(/^(delivered|replying|replied)$/);
    await sim.core.retry(x.id);
    await sim.advance(40_000);
    expect(sim.sends()).toBe(3);
  });
  it("Enter 연타 20회(같은 글) → 쓰기 1", async () => {
    const sim = new Sim({ recordDelay: () => null });
    await ready(sim);
    for (let i = 0; i < 20; i++) sim.core.submit("안녕");
    await sim.advance(60_000);
    expect(sim.sends()).toBe(1);
  });
  it("다시 보내기 연타 20회 → 쓰기 +1(확정 실패 1회만)", async () => {
    const sim = new Sim({ plan: (n) => (n === 0 ? "failed" : "written"), recordDelay: () => null });
    await ready(sim);
    await sim.core.send("안녕");
    expect(sim.core.state.msgs[0].step).toBe("failed");
    const id = sim.core.state.msgs[0].id;
    sim.startPolling();
    await Promise.all(Array.from({ length: 20 }, () => sim.core.retry(id)));
    await sim.advance(60_000);
    expect(sim.sends()).toBe(2);
  });
  it("★경합(전문가 시험): 불명 응답 뒤 120초 사이 아무 때나 사람이 같은 말을 다시 누름 → 중복 쓰기 0 (시각 주입 41점 × 실제로 쓰였음/안 쓰였음)", async () => {
    let total = 0;
    for (const landed of [true, false]) {
      for (let k = 0; k <= 40; k++) {
        const at = Math.round((k * 119_900) / 40) + 100; // 0.1초 ~ 120초
        const sim = new Sim({ plan: (n) => (n === 0 ? (landed ? "uncertain_written" : "uncertain_lost") : "written"), recordDelay: () => null });
        await ready(sim);
        sim.startPolling();
        sim.core.submit("이 일 해 줘");
        await sim.advance(at);
        sim.core.submit("이 일 해 줘"); // 다시 누름(입력칸에 다시 쳐서 Enter)
        for (const m of sim.core.state.msgs) if (needsClick(m)) await sim.core.confirmHeld(m.id); // 단추를 눌러 봄(있다면)
        await sim.advance(120_000 - at + 30_000);
        expect(sim.sends()).toBe(1);
        expect(sim.writes.filter((w) => w.bytesIn).length).toBeLessThanOrEqual(1);
        total++;
      }
    }
    expect(total).toBe(82);
  });
  it("다른 글은 겹침이 아님 · 앞 말이 전달된 뒤 같은 글은 새 말(사람이 또 하고 싶은 말)", async () => {
    const sim = new Sim({ recordDelay: () => 100, replyDelay: () => null });
    await ready(sim);
    sim.startPolling();
    sim.core.submit("하나");
    await sim.advance(40_000);
    sim.core.submit("둘");
    await sim.advance(40_000);
    sim.core.submit("하나");
    await sim.advance(40_000);
    expect(sim.sends()).toBe(3);
  });
});

describe("R3 — 사람 입력 30초 묶음(0.5 숫자 5 = 31.2초)", () => {
  it("A 보낸 1초 뒤 B → B 붙잡음(방금 보낸 말 포함 30초) → A 뒤 30~33초 사이에 자동 1건 · 기계 문안 묶임 남은 시간 = 31.2초 기준", async () => {
    const sim = new Sim({ recordDelay: () => null });
    await ready(sim);
    sim.startPolling();
    sim.core.submit("A");
    await sim.advance(1_000);
    const tA = sim.writes[0].at;
    expect(sim.core.autoHoldRemainingMs()).toBe(AUTO_HOLD_AFTER_HUMAN_MS - (sim.now - tA));
    sim.core.submit("B");
    await sim.advance(100);
    expect(sim.core.state.msgs[1].code).toBe("human_recent");
    let tB: number | null = null;
    await sim.advance(40_000, () => {
      if (tB === null && sim.writes.length === 2) tB = sim.writes[1].at;
    });
    expect(tB).not.toBeNull();
    expect((tB as unknown as number) - tA).toBeGreaterThanOrEqual(30_000);
    expect((tB as unknown as number) - tA).toBeLessThanOrEqual(33_100);
  });
});

describe("여러 줄 · `/`·`!` 막기(살균 뒤)", () => {
  it("여러 줄 = 줄바꿈 그대로 1건 · CRLF 기록과도 전문 일치 → 전달됨", async () => {
    const sim = new Sim({ recordDelay: () => 100, replyDelay: () => null });
    await ready(sim);
    sim.core.submit("첫 줄\r\n둘째 줄\n\n셋째 줄  ");
    await sim.advance(1_200);
    expect(sim.writes[0].text).toBe("첫 줄\n둘째 줄\n\n셋째 줄");
    expect(sim.core.state.msgs[0].step).toBe("delivered");
    const crlf = applyRecords([msg({ text: "첫 줄\n둘째 줄" })], [{ uuid: "u", parent: null, role: "user", text: "첫 줄\r\n둘째 줄\r\n", ts: null }]);
    expect(crlf.msgs[0].step).toBe("delivered");
  });
  it("살균 뒤 맨 앞 `/`·`!` = 막음(제어 문자·BOM·NBSP·줄 구분자 앞세움 포함) · 둘째 줄 `/` = 막음(U21 측정 대기)", () => {
    for (const bad of ["/clear", "\u0001/clear", "\u001b/clear", " /clear", "﻿!ls", " /compact", "　/clear", " \t\n!rm -rf ~", "\u0085/x"]) {
      const o = composeOutbound(bad);
      expect(o.ok).toBe(false);
    }
    expect(composeOutbound("안녕\n/clear")).toMatchObject({ ok: false, code: "later_line_slash" });
    expect(composeOutbound("안녕\n  /clear")).toMatchObject({ ok: false, code: "later_line_slash" });
    expect(composeOutbound("경로는 a/b 이고\n둘째 줄")).toMatchObject({ ok: true });
  });
});
