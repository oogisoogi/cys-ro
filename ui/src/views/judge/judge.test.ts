// (cysr-ui-slice1) 순수 판정 시험 — outbound · gate · msgstep · viewpick. 같은 입력 2회 = 같은 출력(바이트) 포함.
import { describe, it, expect } from "bun:test";
import { composeOutbound, U21_LATER_LINE_SLASH_SAFE } from "./outbound";
import { approvalSeatsOf, HUMAN_QUIET_SECS, isOwnSend, masterRowOf, MEASURED_QUEUE_HOLD_AFTER_HUMAN_SECS, sendGate, U25_BUSY_PASTE_OK, type GateInput, type MasterRow } from "./gate";
import { applyRecords, ATOMIC_SUBMIT_MS, canRetry, M8_UUID_CHAIN, READ_AFTER_MS, settleSteps, SLOW_MS, stepFromOutcome, U20_PASTE_RECORD_FORM, type Msg, type Rec } from "./msgstep";
import { chatAvailability, pickView, storedViewText } from "./viewpick";

const twice = <T,>(f: () => T): T => {
  const a = f();
  const b = f();
  expect(JSON.stringify(a)).toBe(JSON.stringify(b));
  return a;
};

describe("composeOutbound — 살균·막기", () => {
  it("평문은 앞뒤 공백만 걷고 그대로", () => {
    expect(twice(() => composeOutbound("  안녕하세요\n둘째 줄  \n\n"))).toEqual({ ok: true, text: "안녕하세요\n둘째 줄" });
  });
  it("CRLF·CR → LF · 제어 문자(ESC·^U·DEL·C1) → 공백(울타리 표지 위조 불가)", () => {
    const r = composeOutbound("a\r\nb\rc\x1b[201~d\x15e\x7ff\u009bg");
    expect(r).toEqual({ ok: true, text: "a\nb\nc [201~d e f g" });
  });
  it("빈 글 · 공백뿐 · 제어 문자뿐 = 막음", () => {
    for (const t of ["", "   ", "\n\n", "\x1b\x15"]) expect(composeOutbound(t).ok).toBe(false);
  });
  it("맨 앞 / · ! = 막음(앞 공백·제어 문자 뒤에 숨겨도)", () => {
    for (const t of ["/clear", "!rm -rf x", "  /clear", "\u0001/clear", "\x1b!ls"]) {
      const r = composeOutbound(t);
      expect(r.ok).toBe(false);
      if (!r.ok) expect(r.code).toBe("leading_command");
    }
  });
  it("U21 측정 대기 — 둘째 줄 이하 맨 앞 / 는 기본값에서 막음 · 상수가 참이면 보냄", () => {
    expect(U21_LATER_LINE_SLASH_SAFE).toBe(false);
    const r = composeOutbound("요약해 줘\n  /clear");
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.code).toBe("later_line_slash");
    expect(composeOutbound("요약해 줘\n/clear", true)).toEqual({ ok: true, text: "요약해 줘\n/clear" });
    expect(composeOutbound("경로 a/b\n그리고 c").ok).toBe(true);
  });
});

const M = (p: Partial<MasterRow> = {}): MasterRow => ({
  surface_id: 5,
  exited: false,
  agent_alive: true,
  pending_input_bytes: 0,
  pending_input_human_bytes: 0,
  input_paste_open: false,
  gate_pending: null,
  human_idle_secs: null,
  working: false,
  ...p,
});
const G = (p: Partial<GateInput> = {}): GateInput => ({ master: M(), approvalSeats: [], ownLastSendAgeSecs: null, ...p });
const code = (g: GateInput) => {
  const v = sendGate(g);
  return v.ok ? "ok" : v.code;
};

describe("sendGate — 문턱(조건 하나씩 실패 = 쓰기 0)", () => {
  it("모두 통과 = ok", () => {
    expect(twice(() => sendGate(G()))).toEqual({ ok: true });
  });
  it("조회 실패(모름) = status_unknown", () => expect(code(G({ master: undefined }))).toBe("status_unknown"));
  it("마스터 없음 · 끝남 = no_master", () => {
    expect(code(G({ master: null }))).toBe("no_master");
    expect(code(G({ master: M({ exited: true }) }))).toBe("no_master");
  });
  it("에이전트 죽음·모름 = agent_dead", () => {
    expect(code(G({ master: M({ agent_alive: false }) }))).toBe("agent_dead");
    expect(code(G({ master: M({ agent_alive: null }) }))).toBe("agent_dead");
  });
  it("관문 = gate_pending", () => expect(code(G({ master: M({ gate_pending: { kind: "first_run" } }) }))).toBe("gate_pending"));
  it("★수용 2 — feed 승인 대기 항목이 마스터 좌석에 있음 = approval · feed 모름 = approval_unknown · 다른 좌석 항목은 무관", () => {
    expect(code(G({ approvalSeats: [5] }))).toBe("approval");
    expect(code(G({ approvalSeats: null }))).toBe("approval_unknown");
    expect(code(G({ approvalSeats: [9] }))).toBe("ok");
  });
  it("★수용 1 — 사람 초안(12바이트) · 기계 잔여 · 붙여넣기 열림 = draft · 칸 모름 = input_unknown", () => {
    expect(code(G({ master: M({ pending_input_human_bytes: 12, pending_input_bytes: 12 }) }))).toBe("draft");
    expect(code(G({ master: M({ pending_input_human_bytes: 12 }) }))).toBe("draft");
    expect(code(G({ master: M({ pending_input_bytes: 3 }) }))).toBe("draft");
    expect(code(G({ master: M({ input_paste_open: true }) }))).toBe("draft");
    expect(code(G({ master: M({ pending_input_bytes: null }) }))).toBe("input_unknown");
    expect(code(G({ master: M({ pending_input_human_bytes: null }) }))).toBe("input_unknown");
    expect(code(G({ master: M({ input_paste_open: null }) }))).toBe("input_unknown");
  });
  it("다른 길 사람 입력 30초 안 = human_recent · 내 보내기면 통과 · 30초 지나면 통과", () => {
    expect(HUMAN_QUIET_SECS).toBe(30);
    expect(code(G({ master: M({ human_idle_secs: 3 }) }))).toBe("human_recent");
    expect(code(G({ master: M({ human_idle_secs: 3 }), ownLastSendAgeSecs: 4 }))).toBe("ok");
    expect(code(G({ master: M({ human_idle_secs: 3 }), ownLastSendAgeSecs: 20 }))).toBe("human_recent");
    expect(code(G({ master: M({ human_idle_secs: 30 }) }))).toBe("ok");
    expect(isOwnSend(10, 11.9)).toBe(true);
    expect(isOwnSend(10, 12.1)).toBe(false);
  });
  it("U25 측정 대기 — 바쁨 = busy(기본값) · 상수/인자가 참이면 통과", () => {
    expect(U25_BUSY_PASTE_OK).toBe(false);
    expect(code(G({ master: M({ working: true }) }))).toBe("busy");
    expect(code(G({ master: M({ working: true }), busyPasteOk: true }))).toBe("ok");
  });
  it("★수용 3 — 시간 상수 = 0.5 실측값(사람 보내기 뒤 큐 묶임 31.2초)", () => {
    expect(MEASURED_QUEUE_HOLD_AFTER_HUMAN_SECS).toBe(31.2);
  });
});

describe("masterRowOf · approvalSeatsOf — IPC 값 의심", () => {
  const w = () => false;
  it("org.status 꼴이 아니면 undefined(모름) · 마스터 없으면 null", () => {
    expect(masterRowOf(null, w)).toBeUndefined();
    expect(masterRowOf({}, w)).toBeUndefined();
    expect(masterRowOf({ surfaces: [{ surface_id: 1, role: "cso" }] }, w)).toBeNull();
    expect(masterRowOf({ surfaces: [{ surface_id: 1, role: "master", exited: true }] }, w)).toBeNull();
  });
  it("살아 있는 마스터 · 번호 작은 것 · 칸이 이상하면 null(모름)", () => {
    const r = masterRowOf({ surfaces: [{ surface_id: 9, role: "master" }, { surface_id: 4, role: "master", agent_alive: true, pending_input_bytes: "x", pending_input_human_bytes: 0, input_paste_open: false, human_idle_secs: -1 }] }, () => true);
    expect(r?.surface_id).toBe(4);
    expect(r?.pending_input_bytes).toBeNull();
    expect(r?.human_idle_secs).toBeNull();
    expect(r?.working).toBe(true);
    expect(r?.gate_pending).toBeNull();
  });
  it("feed.list {items} · 배열 · 꼴 틀림", () => {
    expect(approvalSeatsOf({ items: [{ kind: "approval", status: "pending", surface_id: 5 }, { kind: "approval", status: "resolved", surface_id: 6 }, { kind: "info", status: "pending", surface_id: 7 }] })).toEqual([5]);
    expect(approvalSeatsOf([])).toEqual([]);
    expect(approvalSeatsOf({})).toBeNull();
  });
});

const msg = (p: Partial<Msg> = {}): Msg => ({ id: "a", text: "안녕", createdAt: 1000, sentAt: 1000, step: "injected", thread: [], replies: [], ...p });
const ts = (ms: number) => new Date(ms).toISOString();

describe("msgstep — 전달됨·답함은 근거가 있을 때만", () => {
  it("상수: 원자 제출 0.73~0.84초(0.5 숫자 1) · 첫 읽기 ≥ 최대 머무름 · 측정 대기 표지", () => {
    expect(ATOMIC_SUBMIT_MS.min).toBe(728);
    expect(ATOMIC_SUBMIT_MS.max).toBe(836);
    expect(READ_AFTER_MS[0]).toBeGreaterThanOrEqual(ATOMIC_SUBMIT_MS.max);
    expect(READ_AFTER_MS).toHaveLength(3);
    expect(U20_PASTE_RECORD_FORM).toBe("unmeasured");
    expect(M8_UUID_CHAIN).toBe("unmeasured");
    expect(SLOW_MS).toBe(120_000);
  });
  it("결과 넷 → 단계(모르는 꼴 = 확인 중)", () => {
    expect(stepFromOutcome("written")).toBe("injected");
    expect(stepFromOutcome("held")).toBe("held");
    expect(stepFromOutcome("queued_hold")).toBe("queued_hold");
    expect(stepFromOutcome("failed")).toBe("failed");
    expect(stepFromOutcome("uncertain")).toBe("checking");
    expect(stepFromOutcome(undefined)).toBe("checking");
  });
  it("전문 일치 user 레코드 → 전달됨 · 사슬 위 assistant 글 → 답하는 중 → 쉬면 답함", () => {
    const recs: Rec[] = [
      { uuid: "u1", parent: "x", role: "user", text: "안녕", ts: ts(1500) },
      { uuid: "a0", parent: "u1", role: "assistant", text: null, ts: ts(1600) },
      { uuid: "t1", parent: "a0", role: "user", text: null, ts: ts(1700) },
      { uuid: "a1", parent: "t1", role: "assistant", text: "네, 안녕하세요", ts: ts(1800) },
    ];
    const r = twice(() => applyRecords([msg()], recs));
    expect(r.msgs[0].step).toBe("replying");
    expect(r.msgs[0].userUuid).toBe("u1");
    expect(r.msgs[0].replies).toEqual([{ uuid: "a1", text: "네, 안녕하세요" }]);
    expect(r.stray).toEqual([]);
    expect(settleSteps(r.msgs, 2000, true)[0].step).toBe("replying");
    expect(settleSteps(r.msgs, 2000, false)[0].step).toBe("replied");
  });
  it("앞 200자만 같은 다른 말 = 짝 안 됨(틀린 「전달됨」 0) · 보내기 전 레코드 = 짝 안 됨", () => {
    const long = "가".repeat(300);
    const m = msg({ text: long });
    expect(applyRecords([m], [{ uuid: "u", parent: null, role: "user", text: long.slice(0, 200) + "나".repeat(100), ts: ts(1500) }]).msgs[0].step).toBe("injected");
    expect(applyRecords([msg({ sentAt: 100_000 })], [{ uuid: "u", parent: null, role: "user", text: "안녕", ts: ts(1000) }]).msgs[0].step).toBe("injected");
  });
  it("같은 글 두 번 → 순서대로 짝", () => {
    const a = msg({ id: "a", sentAt: 1000 });
    const b = msg({ id: "b", sentAt: 2000 });
    const r = applyRecords([b, a], [{ uuid: "u1", parent: null, role: "user", text: "안녕", ts: ts(1100) }]);
    expect(r.msgs.find((m) => m.id === "a")?.step).toBe("delivered");
    expect(r.msgs.find((m) => m.id === "b")?.step).toBe("injected");
  });
  it("새 사람 차례(다른 곳에서 친 말) 뒤 답은 옛 말에 붙지 않음 · uuid 없으면 일반 말풍선", () => {
    const r = applyRecords([msg({ step: "delivered", userUuid: "u1", thread: ["u1", "a1"] })], [
      { uuid: "u9", parent: "a1", role: "user", text: "다른 말", ts: ts(5000) },
      { uuid: "a9", parent: "u9", role: "assistant", text: "그 답", ts: ts(5100) },
      { uuid: null, parent: null, role: "assistant", text: "사슬 없음", ts: null },
    ]);
    expect(r.msgs[0].replies).toEqual([]);
    expect(r.stray.map((x) => x.text)).toEqual(["그 답", "사슬 없음"]);
  });
  it("훅이 덧붙인 조각 — 조각 하나가 같으면 짝 · 곁가지(sidechain) 무시", () => {
    expect(applyRecords([msg()], [{ uuid: "u", parent: null, role: "user", text: "안녕\n<hook>", parts: ["안녕", "<hook>"], ts: ts(1200) }]).msgs[0].step).toBe("delivered");
    expect(applyRecords([msg()], [{ uuid: "u", parent: null, role: "user", text: "안녕", ts: ts(1200), sidechain: true }]).msgs[0].step).toBe("injected");
  });
  it("근거 없는 대기 120초 → 오래 걸려요 · 다시 보내기 = 확정 실패 1회만", () => {
    expect(settleSteps([msg({ step: "checking", sentAt: 0 })], SLOW_MS, null)[0].step).toBe("slow");
    expect(settleSteps([msg({ step: "injected", sentAt: 0 })], SLOW_MS - 1, null)[0].step).toBe("injected");
    expect(canRetry(msg({ step: "failed" }))).toBe(true);
    expect(canRetry(msg({ step: "failed", retried: true }))).toBe(false);
    for (const s of ["checking", "slow", "held", "injected", "queued_hold"] as const) expect(canRetry(msg({ step: s }))).toBe(false);
  });
});

describe("viewpick — 1.1.16 = 새·기존 모두 작업 화면 · 사람이 고른 화면만 기억", () => {
  const ids = ["chat", "work"];
  it("§10 표(개정): 없음·깨짐·옛 꼴·없는 화면 = 작업 화면 · 고른 화면 = 그 화면", () => {
    expect(pickView(null, ids)).toBe("work");
    expect(pickView("{깨짐", ids)).toBe("work");
    expect(pickView('"chat"', ids)).toBe("work");
    expect(pickView(JSON.stringify({ v: 2, id: "chat" }), ids)).toBe("work");
    expect(pickView(JSON.stringify({ v: 1, id: "board" }), ids)).toBe("work");
    expect(pickView(storedViewText("chat"), ids)).toBe("chat");
    expect(pickView(storedViewText("work"), ids)).toBe("work");
  });
  it("§9-3 긍정 신호만 불가: 새 설치(마스터 없음)·꺼짐·이름 보고 없음·모름 = 가능 · cys 밖 마스터 최근 = 불가", () => {
    const now = 10_000;
    const named = [{ name: "master", updated_at: now - 60 }];
    expect(chatAvailability(named, true, now).ok).toBe(true);
    expect(chatAvailability([], false, now).ok).toBe(true);
    expect(chatAvailability(null, false, now).ok).toBe(true);
    expect(chatAvailability(named, null, now).ok).toBe(true);
    expect(chatAvailability([{ name: "master", updated_at: now - 601 }], false, now).ok).toBe(true);
    expect(chatAvailability(named, false, now).ok).toBe(false);
  });
});
