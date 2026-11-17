// (cysr-ui-slice3-fix-1118) 조각 3 독립 검증(VERIFY.cysr-ui-slice3 · 검증 좌석 2161) 지적 A~H 고침 시험.
// 재현 장면 V1·V2·V3·V7·V8·V9 는 검증 좌석의 `verify_s3_probe.test.ts` 를 옮겨 와 기대를 「고친 뒤」로 바꾼 것이다(고치기 전 = 붉음 확인).
import { describe, it, expect } from "bun:test";
import { DUP, dupPending, logOrder, needsClick, OBS_MAX_MS, sameTextDelivered, STATUS_TIMEOUT } from "./core";
import { applyRecords, canRetry, PASTE_WRAP, rematchPending, settleSteps, userRecordMatches, type Msg, type Rec } from "./judge/msgstep";
import { composeOutbound } from "./judge/outbound";
import { Sim, type SendKind } from "./testkit";

const T = 1_000_000;
const msg = (p: Partial<Msg>): Msg => ({ id: "m1", text: "안녕", createdAt: T, sentAt: T, step: "injected", thread: [], replies: [], ...p });
const iso = (ms: number) => new Date(ms).toISOString();
const bytesIn = (s: Sim) => s.writes.filter((w) => w.bytesIn).length;

async function ready(sim: Sim): Promise<void> {
  sim.core.attach();
  await sim.flush();
}

describe("A — 감싼 붙여넣기 기록(<pasted_content id=…>) = 속 글이 보낸 글과 글자 하나까지 같을 때만 전문 일치", () => {
  const body = "첫 줄\n둘째 줄\n셋째 줄";
  const wrap = (id: string, inner: string) => `\n\n<pasted_content id="${id}">\n${inner}\n</pasted_content id="${id}">\n`;
  const rec = (text: string, extra: Partial<Rec> = {}): Rec => ({ uuid: "u1", parent: "p0", role: "user", text, ts: iso(T + 900), ...extra });
  it("실측 꼴 2가지(id 숫자 3943 · 영숫자 3f02) → 전달됨", () => {
    for (const id of ["3943", "3f02"]) {
      expect(userRecordMatches(msg({ text: body }), rec(wrap(id, body)))).toBe(true);
      expect(applyRecords([msg({ text: body })], [rec(wrap(id, body))]).msgs[0].step).toBe("delivered");
    }
  });
  it("속 글이 한 글자라도 다르면 · 감싼 밖에 다른 글이 있으면 · 여닫는 id 가 다르면 · 앞뒤 줄바꿈 꼴이 다르면 = 불일치(모름 유지)", () => {
    const m = msg({ text: body });
    const bad = [
      wrap("1", body + " "),
      wrap("1", " " + body),
      wrap("1", body.replace("둘째", "둘 째")),
      "머리말" + wrap("1", body),
      wrap("1", body) + "꼬리",
      `\n\n<pasted_content id="1">\n${body}\n</pasted_content id="2">\n`,
      `\n<pasted_content id="1">\n${body}\n</pasted_content id="1">\n`,
      `\n\n<pasted_content id="1">${body}</pasted_content id="1">\n`,
      `\n\n<pasted_content id="1">\n${body}\n</pasted_content id="1">`,
      `\n\n<pasted_content id="">\n${body}\n</pasted_content id="">\n`,
      `\n\n<pasted_content id="a b">\n${body}\n</pasted_content id="a b">\n`,
      // 실측(이 좌석 기록): 속 글 안의 태그는 `<\pasted_content` 로 바뀌어 남는다 → 원문과 다름 → 모름(되돌려 맞추지 않음)
      wrap("1", "앞 <\\pasted_content id=\"N\"> 뒤"),
    ];
    for (const t of bad) expect(userRecordMatches(m, rec(t))).toBe(false);
    expect(userRecordMatches(msg({ text: '앞 <pasted_content id="N"> 뒤' }), rec(wrap("1", '앞 <\\pasted_content id="N"> 뒤')))).toBe(false);
  });
  it("감싼 꼴도 sidechain·사람 아닌 종류·보내기 6초 전 시각은 전달됨 0 · 글 조각 하나가 감싼 꼴이면 그 조각만으로 일치", () => {
    const m = msg({ text: body });
    expect(userRecordMatches(m, rec(wrap("1", body), { sidechain: true }))).toBe(false);
    expect(userRecordMatches(m, rec(wrap("1", body), { role: "assistant" }))).toBe(false);
    expect(applyRecords([m], [rec(wrap("1", body), { ts: iso(T - 6_000) })]).msgs[0].step).toBe("injected");
    expect(userRecordMatches(m, rec("훅 글\n" + wrap("1", body), { parts: ["훅 글", wrap("1", body)] }))).toBe(true);
  });
  it("PASTE_WRAP 은 한 줄 글·빈 속 글도 같은 규칙(속 글 = 보낸 글일 때만)", () => {
    expect(PASTE_WRAP.exec(wrap("7", "한 줄"))?.[2]).toBe("한 줄");
    expect(userRecordMatches(msg({ text: "한 줄" }), rec(wrap("7", "한 줄")))).toBe(true);
  });
  it("V2(core) — 여러 줄 말 → 감싼 레코드만 생김 → 전달됨 · 답이 그 말에 붙음(일반 말풍선 0) · 같은 글 다시 = 겹침 아님", async () => {
    const sim = new Sim({ plan: () => "written", recordDelay: () => null, replyDelay: () => null });
    await ready(sim);
    sim.startPolling();
    await sim.core.send(body);
    await sim.advance(900);
    sim.file.push({ uuid: "ux", parent: "root", role: "user", text: wrap("3943", body), ts: iso(sim.now) });
    sim.lastOutputAt = sim.now;
    await sim.advance(2_000);
    sim.file.push({ uuid: "ax", parent: "ux", role: "assistant", text: "답", ts: iso(sim.now) });
    sim.lastOutputAt = sim.now;
    await sim.advance(138_000);
    expect(sim.core.state.msgs[0].step).toBe("replied");
    expect(sim.core.state.msgs[0].replies.map((r) => r.text)).toEqual(["답"]);
    expect(sim.core.state.stray.length).toBe(0);
    expect(dupPending(sim.core.state.msgs, body)).toBe(false);
  });
});

describe("B — 사람 말과 첫 답 사이에 낀 다른 종류 레코드(role:link = 글 없는 고리)로 사슬을 잇는다 · 안 묶인 답은 시각순", () => {
  it("V3 — user → link(attachment) → link → assistant = 답이 그 말에 붙음 · 일반 말풍선 0 · 쉬면 답함", () => {
    const ap = applyRecords([msg({})], [
      { uuid: "u1", parent: "p0", role: "user", text: "안녕", ts: iso(T + 900) },
      { uuid: "att1", parent: "u1", role: "link", text: null, ts: null },
      { uuid: "att2", parent: "att1", role: "link", text: null, ts: null },
      { uuid: "a1", parent: "att2", role: "assistant", text: "네", ts: iso(T + 3_000) },
    ]);
    const settled = settleSteps(ap.msgs, T + 10_000, false);
    expect(settled[0].step).toBe("replied");
    expect(settled[0].replies.map((r) => r.text)).toEqual(["네"]);
    expect(ap.stray.length).toBe(0);
  });
  it("고리는 짝(전달됨)이 되지 않는다 · 아무 말의 사슬에도 없는 고리는 무시 · 고리 뒤 새 사람 글이면 사슬을 닫음", () => {
    const ap = applyRecords([msg({})], [{ uuid: "l", parent: "zz", role: "link", text: null, ts: null }]);
    expect(ap.msgs[0].step).toBe("injected");
    const ap2 = applyRecords([msg({})], [
      { uuid: "u1", parent: "p0", role: "user", text: "안녕", ts: iso(T + 900) },
      { uuid: "l1", parent: "u1", role: "link", text: null, ts: null },
      { uuid: "u9", parent: "l1", role: "user", text: "다른 사람 글", ts: iso(T + 2_000) },
      { uuid: "a9", parent: "u9", role: "assistant", text: "다른 답", ts: iso(T + 3_000) },
    ]);
    expect(ap2.msgs[0].replies.length).toBe(0);
    expect(ap2.stray.map((r) => r.text)).toEqual(["다른 답"]);
  });
  it("core(대역 실측 꼴 linksBetween 3): 답이 그 말에 붙고 답함", async () => {
    const sim = new Sim({ linksBetween: 3, replyDelay: () => 1_500 });
    await ready(sim);
    sim.startPolling();
    await sim.core.send("고리 시험");
    await sim.advance(30_000);
    expect(sim.core.state.msgs[0].step).toBe("replied");
    expect(sim.core.state.msgs[0].replies.length).toBe(1);
    expect(sim.core.state.stray.length).toBe(0);
  });
  it("안 묶인 답은 사람 말 뒤에 몰리지 않고 시각순(앞 말의 답이 뒤 말 앞에)", () => {
    const a = msg({ id: "a", text: "A", sentAt: T, createdAt: T });
    const b = msg({ id: "b", text: "B", sentAt: T + 10_000, createdAt: T + 10_000 });
    const order = logOrder([a, b], [
      { uuid: "s1", text: "A 의 답", at: T + 5_000 },
      { uuid: "s2", text: "B 뒤 답", at: T + 20_000 },
      { uuid: "s0", text: "시각 모름", at: undefined },
    ]);
    expect(order.map((x) => (x.kind === "msg" ? x.m.id : x.r.text))).toEqual(["a", "A 의 답", "b", "B 뒤 답", "시각 모름"]);
  });
  it("core: 안 묶인 답에 시각이 붙는다(기록 시각 · 없으면 읽은 시각)", async () => {
    const sim = new Sim({ recordDelay: () => null, replyDelay: () => null });
    await ready(sim);
    await sim.core.send("말");
    sim.file.push({ uuid: "a1", parent: "nowhere", role: "assistant", text: "떠돌이", ts: iso(sim.now + 100) });
    sim.file.push({ uuid: "a2", parent: "nowhere", role: "assistant", text: "시각 없음", ts: null });
    await sim.core.readTranscript();
    const st = sim.core.state.stray;
    expect(st.map((r) => r.text)).toEqual(["떠돌이", "시각 없음"]);
    expect(st[0].at).toBe(sim.now + 100);
    expect(st[1].at).toBe(sim.now);
  });
});

describe("C — 「보내는 중」도 짝 후보 · 짝 못 찾은 사람 레코드는 소비하지 않음", () => {
  it("V1 — 앞 말 A 전달됨 · B 의 응답이 2.5초 걸리는 동안 읽힌 B 레코드 → B 전달됨(끝까지 「오래 걸려요」 아님)", async () => {
    let n = 0;
    const sim = new Sim({ plan: (): SendKind => (n++ === 0 ? "written" : "hang_written"), recordDelay: () => 200, replyDelay: () => null, hangMs: 2_500 });
    await ready(sim);
    sim.startPolling();
    await sim.core.send("첫 말");
    await sim.advance(40_000);
    const phase = (sim.now - 1_000_000) % 3_000;
    await sim.advance((3_000 - phase + 3_000 - 1_500) % 3_000 || 3_000);
    void sim.core.submit("둘째 말");
    await sim.advance(2_000);
    await sim.advance(140_000);
    expect(sim.recorded.has(1)).toBe(true);
    expect(sim.core.state.msgs[1].step).toMatch(/^(delivered|replying|replied)$/);
    expect(dupPending(sim.core.state.msgs, "둘째 말")).toBe(false);
  });
  it("순수: 보내는 중(보낸 시각 있음)인 말에 자기 레코드가 짝 · 보낸 시각 없는 보내는 중은 짝 아님", () => {
    const r: Rec = { uuid: "u1", parent: null, role: "user", text: "안녕", ts: iso(T + 900) };
    expect(applyRecords([msg({ step: "sending" })], [r]).msgs[0].step).toBe("delivered");
    expect(applyRecords([msg({ step: "sending", sentAt: null })], [r]).msgs[0].step).toBe("sending");
  });
  it("순수: 짝 못 찾은 사람 레코드는 consumed 에 안 들어가고 unmatched 로 나온다 → 말이 짝 후보가 되면 rematchPending 이 짝지음(한 번만)", () => {
    const r: Rec = { uuid: "u1", parent: null, role: "user", text: "안녕", ts: iso(T + 900) };
    const ap = applyRecords([msg({ step: "held", sentAt: null })], [r]);
    expect(ap.consumed).toEqual([]);
    expect(ap.unmatched).toEqual([r]);
    const later = rematchPending([msg({ step: "injected" })], ap.unmatched);
    expect(later.changed).toBe(true);
    expect(later.msgs[0].step).toBe("delivered");
    expect(later.msgs[0].userUuid).toBe("u1");
    expect(later.pool).toEqual([]);
    // 같은 글 두 말이 기다려도 레코드 하나 = 가장 먼저 보낸 말 하나만
    const two = rematchPending([msg({ id: "x", sentAt: T + 100 }), msg({ id: "y", sentAt: T })], [r]);
    expect(two.msgs.map((m) => m.step)).toEqual(["injected", "delivered"]);
    // 이미 짝이 있는 말·붙잡은 말·시각이 6초 앞선 레코드 = 짝 아님
    expect(rematchPending([msg({ userUuid: "z", step: "delivered" })], [r]).changed).toBe(false);
    expect(rematchPending([msg({ sentAt: T + 7_000 })], [r]).changed).toBe(false);
  });
  it("core: 레코드가 먼저 읽히고(말이 짝 후보 아님) 뒤에 말이 「확인 중」이 되면 다시 짝지어 전달됨", async () => {
    const sim = new Sim({ plan: () => "uncertain_written", recordDelay: () => null, replyDelay: () => null });
    await ready(sim);
    sim.startPolling();
    await sim.core.send("늦게 짝");
    const id = sim.core.state.msgs[0].id;
    // 짝 후보가 아닌 단계(붙잡음)로 잠시 바꿔 둔 사이 레코드가 읽힘 — 기존이면 「본 것」으로 소비돼 영영 못 씀
    const realStep = sim.core.state.msgs[0].step;
    (sim.core as unknown as { s: { msgs: Msg[] } }).s.msgs = sim.core.state.msgs.map((m) => (m.id === id ? { ...m, step: "queued_hold" } : m));
    sim.file.push({ uuid: "uz", parent: "root", role: "user", text: "늦게 짝", ts: iso(sim.now + 300) });
    await sim.core.readTranscript();
    expect(sim.core.state.msgs[0].step).toBe("queued_hold");
    (sim.core as unknown as { s: { msgs: Msg[] } }).s.msgs = sim.core.state.msgs.map((m) => (m.id === id ? { ...m, step: realStep } : m));
    await sim.advance(3_100); // 다음 조회가 말 목록을 갱신 → 다시 대어 봄
    expect(sim.core.state.msgs[0].step).toMatch(/^(delivered|replying|replied)$/);
    expect(sim.core.state.msgs[0].userUuid).toBe("uz");
    expect(sim.sends()).toBe(1);
  });
});

describe("D — 시험 구멍(검증 O11·O14·O13): 중복 쓰기 계수로 판정", () => {
  it("O11 — 걸린 「보내는 중」(응답 6초) 사이 같은 글을 다시 보냄(0.05~5초) → chat_send 1 · 바이트 들어간 쓰기 1", async () => {
    for (const at of [50, 400, 1_500, 2_900, 3_100, 5_000]) {
      let n = 0;
      const sim = new Sim({ plan: (): SendKind => (n++ === 0 ? "hang_written" : "written"), recordDelay: () => null, replyDelay: () => null, hangMs: 6_000 });
      await ready(sim);
      sim.startPolling();
      void sim.core.submit("같은 말");
      await sim.advance(at);
      void sim.core.submit("같은 말");
      await sim.advance(60_000);
      expect([at, sim.sends(), bytesIn(sim)]).toEqual([at, 1, 1]);
      expect(sim.core.state.msgs[1].step).toBe("held");
      expect(sim.core.state.msgs[1].code).toBe(DUP);
    }
  });
  it("O14 — 클릭 대상이 아닌 말(불명 · 확인 중 · 줄 선 붙잡음 · 전달 확인 중)에 「이 말 보내기」가 닿아도 쓰기 0", async () => {
    for (const kind of ["uncertain_written", "uncertain_lost", "written"] as SendKind[]) {
      const sim = new Sim({ plan: () => kind, recordDelay: () => null, replyDelay: () => null });
      await ready(sim);
      await sim.core.send("말");
      const m = sim.core.state.msgs[0];
      expect(needsClick(m)).toBe(false);
      for (let i = 0; i < 3; i++) await sim.core.confirmHeld(m.id);
      expect(sim.core.state.msgs.map((x) => x.id)).toEqual([m.id]); // 그 말을 지우고 새 말로 바꾸지 않음
      await sim.advance(45_000); // 사람 입력 30초 묶음을 넘겨서도
      expect([kind, sim.sends()]).toEqual([kind, 1]);
      expect(sim.core.state.msgs.length).toBe(1);
    }
    // 앞 말 뒤에 줄 선 붙잡음(after_prev · 자동으로 나갈 말)도 클릭 대상 아님
    const sim = new Sim({ plan: () => "hang_written", recordDelay: () => null, replyDelay: () => null, hangMs: 4_000 });
    await ready(sim);
    void sim.core.submit("앞 말");
    await sim.advance(100);
    void sim.core.submit("뒤 말");
    await sim.flush();
    const behind = sim.core.state.msgs[1];
    expect(behind.step).toBe("held");
    expect(needsClick(behind)).toBe(false);
    await sim.core.confirmHeld(behind.id);
    expect(sim.sends()).toBe(1); // 앞 말이 걸린 동안 뒤 말을 앞질러 쓰지 않음
  });
  it("O13 — 쓰는 중에 다시 보내기를 누르면 아무것도 안 함(새 말 0 · 「보내는 중」이 보낸 시각 없이 굳지 않음)", async () => {
    let n = 0;
    const sim = new Sim({ plan: (): SendKind => (n++ === 0 ? "failed" : "hang_written"), recordDelay: () => null, replyDelay: () => null, hangMs: 5_000 });
    await ready(sim);
    await sim.core.send("실패한 말");
    const x = sim.core.state.msgs[0];
    expect(canRetry(x)).toBe(true);
    void sim.core.submit("걸린 다른 말");
    await sim.advance(100);
    const before = sim.core.state.msgs.length;
    await sim.core.retry(x.id); // 쓰는 중
    expect(sim.core.state.msgs.length).toBe(before);
    expect(sim.core.state.msgs[0].retried).toBeUndefined();
    await sim.advance(200_000);
    expect(sim.core.state.msgs.some((m) => m.step === "sending" && m.sentAt === null)).toBe(false);
    expect(sim.sends()).toBe(2);
    // 쓰기가 끝난 뒤에는 다시 보내기 1회가 그대로 된다
    void sim.core.retry(x.id);
    await sim.advance(10_000);
    expect(sim.sends()).toBe(3);
  });
});

describe("E — `/`·`!` 막기: 앞쪽 보이지 않는 글자를 떼고 · 둘째 줄도 같은 규칙 · 줄 나눔 확대", () => {
  const lead: Array<[string, string]> = [
    ["U+200B", "​"], ["U+200C", "‌"], ["U+200D", "‍"], ["U+2060", "⁠"], ["U+00AD", "­"],
    ["U+200E", "‎"], ["U+200F", "‏"], ["U+202A", "‪"], ["U+202B", "‫"], ["U+202E", "‮"],
    ["U+2066", "⁦"], ["U+2067", "⁧"], ["U+2069", "⁩"], ["U+061C", "؜"], ["U+180E", "᠎"],
    ["U+034F", "͏"], ["U+0301", "́"], ["U+FE0F", "️"], ["U+115F", "ᅟ"], ["U+3164", "ㅤ"],
    ["U+FFA0", "ﾠ"], ["U+2800", "⠀"], ["U+E0020", "\u{E0020}"],
    // 이미 막히던 것(회귀 확인)
    ["U+FEFF", "﻿"], ["U+00A0", " "], ["U+3000", "　"], ["U+2028", " "], ["U+2029", " "],
    ["U+0085", "\u0085"], ["ESC", "\u001B"], ["NUL", "\u0000"], ["VT", "\u000B"], ["DEL", "\u007F"],
    // 여러 개 섞음
    ["U+200B+U+3164+NBSP", "​ㅤ "],
  ];
  it("V8 — 검증 목록 23종 + 기존 10종 + 섞음 × `/clear`·`!ls` = 전부 막힘(통과 0)", () => {
    const pass: string[] = [];
    for (const [name, ch] of lead) for (const cmd of ["/clear", "!ls"]) if (composeOutbound(ch + cmd).ok) pass.push(`${name}+${cmd}`);
    expect(pass).toEqual([]);
  });
  it("범주로 보는 그 밖 글자(Cf U+2061 · Mn U+0300 · Zs U+2009)도 막힘 · 둘째 줄도 같은 규칙", () => {
    for (const ch of ["⁡", "̀", " "]) {
      expect(composeOutbound(ch + "/clear").ok).toBe(false);
      expect(composeOutbound("가\n" + ch + "/clear").ok).toBe(false);
    }
  });
  it("둘째 줄: NBSP·전각 공백·U+200B·U+3164 앞세움 + `/`·`!` = 막힘 · U+2028/U+2029/NEL/세로 탭/폼 피드/CR 로 나뉜 둘째 줄 = 막힘", () => {
    const rows = [
      "가\n /clear", "가\n　/clear", "가\n​/clear", "가\nㅤ/clear", "가\n   /clear", "가\n\t/clear", "가\n!ls", "가\n​!ls",
      "가\r/clear", "가 /clear", "가 /clear", "가\u0085/clear", "가\u000B/clear", "가\u000C/clear", "가 ​!ls",
    ];
    for (const raw of rows) expect([raw, composeOutbound(raw).ok]).toEqual([raw, false]);
  });
  it("모양만 닮은 글자(전각 ／·！ · ∕ · ⁄)는 통과 · 줄 가운데 `/`·`!` 는 통과 · 보내는 글은 바뀌지 않음", () => {
    for (const raw of ["／clear", "！ls", "∕clear", "⁄clear", "가\n／clear", "가 /clear 뒤", "느낌표! 좋아요", "a/b\nc!d"]) {
      const o = composeOutbound(raw);
      expect([raw, o.ok]).toEqual([raw, true]);
    }
    const o = composeOutbound("가 나");
    expect(o.ok && o.text).toBe("가 나"); // 판정만 줄로 보고 글은 그대로
  });
});

describe("F — 쓰기 직전 재조회 시간 상한(500ms) · 넘거나 실패 = 쓰기 0 · 붙잡음 + 안내 · 보내는 중 굳음 0", () => {
  it("V9 — org_status 가 안 돌아오면 → 「보내는 중」에 굳지 않고 붙잡음(status_timeout) · chat_send 0 · 조회 고리도 계속 돎 · 풀리면 보냄 1", async () => {
    const sim = new Sim({ plan: () => "written" });
    await ready(sim);
    sim.startPolling();
    await sim.advance(7_000);
    const orig = sim.deps.invoke;
    let hang = true;
    let hung = 0;
    (sim.deps as { invoke: typeof orig }).invoke = (cmd, args) => (cmd === "org_status" && hang ? (hung++, new Promise<unknown>(() => {})) : orig(cmd, args));
    void sim.core.submit("멈춘 동안 보낸 말");
    await sim.advance(OBS_MAX_MS + 50);
    const m = sim.core.state.msgs[0];
    expect(m.step).toBe("held");
    expect(m.code).toBe(STATUS_TIMEOUT);
    expect(m.sentAt).toBeNull();
    expect(m.note).toMatch(/아직 쓰지 않았어요/);
    await sim.advance(30_000);
    expect(sim.sends()).toBe(0);
    expect(hung).toBeGreaterThan(5); // 조회 고리가 멈추지 않고 계속 돎(3초마다)
    expect(sim.core.state.health).toBe("unknown");
    expect(sim.core.state.msgs.some((x) => x.step === "sending")).toBe(false);
    hang = false;
    await sim.advance(10_000);
    expect(sim.sends()).toBe(1);
    expect(sim.core.state.msgs[0].step).toMatch(/^(injected|delivered|replying|replied)$/);
  });
  it("feed_list 가 멈춰도 같음(쓰기 0 · 붙잡음) · 재조회 실패(던짐)는 기존대로 모름 → 붙잡음", async () => {
    for (const mode of ["feed_hang", "org_throw"] as const) {
      const sim = new Sim({ plan: () => "written" });
      await ready(sim);
      await sim.advance(100);
      const orig = sim.deps.invoke;
      (sim.deps as { invoke: typeof orig }).invoke = (cmd, args) =>
        mode === "feed_hang" && cmd === "feed_list" ? new Promise<unknown>(() => {}) : mode === "org_throw" && cmd === "org_status" ? Promise.reject(new Error("x")) : orig(cmd, args);
      void sim.core.submit("말");
      await sim.advance(OBS_MAX_MS + 50);
      expect([mode, sim.core.state.msgs[0].step, sim.sends()]).toEqual([mode, "held", 0]);
    }
  });
  it("쓰기 직전 세션 시작점 잡기(chat_transcript)가 멈춰도 쓰기 0 · 붙잡음(status_timeout)", async () => {
    const sim = new Sim({ plan: () => "written" });
    const orig = sim.deps.invoke;
    (sim.deps as { invoke: typeof orig }).invoke = (cmd, args) => (cmd === "chat_transcript" ? new Promise<unknown>(() => {}) : orig(cmd, args));
    await ready(sim);
    void sim.core.submit("말");
    await sim.advance(2 * OBS_MAX_MS + 50);
    expect(sim.core.state.msgs[0].step).toBe("held");
    expect(sim.core.state.msgs[0].code).toBe(STATUS_TIMEOUT);
    expect(sim.sends()).toBe(0);
  });
  it("정상(빠른 응답)에서는 동작 그대로 — 바로 씀 · 전달됨", async () => {
    const sim = new Sim({});
    await ready(sim);
    await sim.core.send("보통 말");
    expect(sim.sends()).toBe(1);
    await sim.advance(5_000);
    expect(sim.core.state.msgs[0].step).toMatch(/^(delivered|replying|replied)$/);
  });
});

describe("H — 같은 글의 다른 말이 「전달됨」 이상이면 확정 실패 X 의 다시 보내기를 거둠", () => {
  it("V7(마지막 장면) — X 실패 · Y 전달됨 → X 단추 0 · retry 눌러도 쓰기 0 · 안내", async () => {
    let n = 0;
    const sim = new Sim({ plan: (): SendKind => (n++ === 0 ? "failed" : "written"), recordDelay: () => 200, replyDelay: () => null });
    await ready(sim);
    sim.startPolling();
    await sim.core.send("말");
    await sim.core.send("말");
    await sim.advance(5_000);
    const [x, y] = sim.core.state.msgs;
    expect(y.step).toMatch(/^(delivered|replying|replied)$/);
    expect(canRetry(x)).toBe(true);
    expect(sameTextDelivered(sim.core.state.msgs, x.text, x.id)).toBe(true);
    await sim.advance(40_000);
    await sim.core.retry(x.id);
    await sim.advance(5_000);
    expect(sim.sends()).toBe(2);
    expect(bytesIn(sim)).toBe(1);
    expect(sim.core.state.notice).toMatch(/이미 전달됐어요/);
  });
  it("같은 글이 아직 전달 전(전달 확인 중)이면 거두지 않음(겹침 규칙이 따로 막음) · 다른 글이 전달된 것은 상관없음", () => {
    const x = msg({ id: "x", step: "failed", text: "말" });
    expect(sameTextDelivered([x, msg({ id: "y", step: "injected", text: "말" })], "말", "x")).toBe(false);
    expect(sameTextDelivered([x, msg({ id: "y", step: "delivered", text: "다른 말" })], "말", "x")).toBe(false);
    for (const st of ["delivered", "replying", "replied"] as const) expect(sameTextDelivered([x, msg({ id: "y", step: st, text: "말" })], "말", "x")).toBe(true);
    expect(sameTextDelivered([msg({ id: "x", step: "delivered", text: "말" })], "말", "x")).toBe(false); // 자기 자신 제외
  });
});
