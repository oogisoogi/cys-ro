// (TICKET=cysr-1118u-chat ②) 대화 화면 전달 3초 조회 틱 → 붙잡은 말이 문턱을 기다리는 동안 1초.
// 윈 1.1.17 실측(v2 · 2374 05:56): 쉬는 중 도착 2.6~3.5s / 5.4~5.8s 양분 · 도착 초 mod 3 = 1 · K1 6/10 ≤5초 · K2(답 끝 뒤 도착) 15.7s.
// 원인 = 문턱(답하는 중 등)에 붙잡힌 말은 대화 화면 POLL_MS(3초) 조회에서만 다시 문턱에 걸렸다 → 문턱이 열린 뒤 최대 3초 늦게 나감.
// 대조군 = 종전 꼴(3초마다 poll) — 같은 장면에서 열린 뒤 지연이 1초를 넘는 자리가 있다(원인 재현). 고친 꼴(1초 pollTick) = 모든 자리 ≤ 1초.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { FAST_POLL_MS, POLL_MS } from "./core";
import { Sim } from "./testkit";

const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const CHAT = strip(readFileSync(new URL("./chat/index.ts", import.meta.url), "utf8"));

type Loop = "old3s" | "tick1s";
/** 대화 화면 시계 대역 — old3s = 종전(3초마다 poll) · tick1s = 고친 대화 화면(1초마다 pollTick). */
function startLoop(sim: Sim, loop: Loop): void {
  const ms = loop === "old3s" ? POLL_MS : FAST_POLL_MS;
  const tick = () => {
    if (loop === "old3s") void sim.core.poll();
    else (sim.core as unknown as { pollTick(): void }).pollTick();
    sim.later(ms, tick);
  };
  sim.later(ms, tick);
}

async function ready(sim: Sim, loop: Loop): Promise<void> {
  sim.core.attach();
  await sim.flush();
  void sim.core.poll(); // 대화 화면 mount 의 첫 조회
  startLoop(sim, loop);
  await sim.advance(POLL_MS + 1_000);
}

/** 마스터가 답하는 중에 보낸 말 → 붙잡힘 → openAfter 뒤 쉼 → 첫 chat_send 까지 지연(ms). */
async function heldLatency(loop: Loop, openAfter: number): Promise<{ lat: number; sends: number; step: string }> {
  const sim = new Sim({ busyPasteOk: false }) /* (K-3) 「답하는 중」 붙잡음 장치 = 되돌리기 판 동작 */;
  await ready(sim, loop);
  sim.seat.working = true;
  sim.core.submit("둘");
  await sim.advance(10);
  const step = sim.core.state.msgs[sim.core.state.msgs.length - 1].step;
  let openAt = 0;
  sim.later(openAfter, () => {
    sim.seat.working = false;
    openAt = sim.now;
  });
  await sim.advance(openAfter + 10_000);
  const send = sim.calls.find((c) => c.cmd === "chat_send");
  return { lat: send ? send.at - openAt : -1, sends: sim.sends(), step };
}

const OFFSETS = Array.from({ length: 30 }, (_, i) => 4_000 + i * 100); // 문턱이 열리는 자리 = 3초 박자 안 전 위상(100ms 간격)

describe("② 붙잡은 말 = 문턱이 열린 뒤 1초 안에 나감", () => {
  it("대조군(종전 3초 poll): 붙잡힌 뒤 열린 자리에 따라 1초 넘게 늦는 경우가 있다(원인 재현 · 최대 ≈3초)", async () => {
    const lats: number[] = [];
    for (const o of OFFSETS) {
      const r = await heldLatency("old3s", o);
      expect(r.step).toBe("held");
      expect(r.sends).toBe(1);
      lats.push(r.lat);
    }
    expect(Math.max(...lats)).toBeGreaterThan(FAST_POLL_MS);
    expect(POLL_MS).toBeGreaterThanOrEqual(Math.max(...lats));
  });
  it("고친 꼴(1초 pollTick): 모든 위상에서 열린 뒤 ≤ 1초 · 쓰기 정확히 1", async () => {
    const lats: number[] = [];
    for (const o of OFFSETS) {
      const r = await heldLatency("tick1s", o);
      expect(r.step).toBe("held");
      expect(r.sends).toBe(1);
      lats.push(r.lat);
    }
    expect(FAST_POLL_MS).toBeGreaterThanOrEqual(Math.max(...lats));
    expect(Math.min(...lats)).toBeGreaterThanOrEqual(0);
  });
});

describe("② 조회 수 — 붙잡은 말이 없으면 종전과 같다 · 있을 때만 1초", () => {
  async function orgCalls(loop: Loop, held: boolean, ms: number): Promise<{ org: number; other: Record<string, number> }> {
    const sim = new Sim({ busyPasteOk: false }) /* (K-3) 「답하는 중」 붙잡음 장치 = 되돌리기 판 동작 */;
    await ready(sim, loop);
    if (held) {
      sim.seat.working = true;
      sim.core.submit("둘");
    }
    const from = sim.calls.length;
    await sim.advance(ms);
    const win = sim.calls.slice(from);
    const other: Record<string, number> = {};
    for (const c of win) if (c.cmd !== "org_status" && c.cmd !== "feed_list") other[c.cmd] = (other[c.cmd] ?? 0) + 1;
    return { org: win.filter((c) => c.cmd === "org_status").length, other };
  }
  it("붙잡은 말 없음: 30초 org_status 수 = 종전 3초 poll 과 같다(1초 시계가 조회를 늘리지 않음)", async () => {
    const a = await orgCalls("old3s", false, 30_000);
    const b = await orgCalls("tick1s", false, 30_000);
    expect(b.org).toBe(a.org);
    expect(b.other).toEqual(a.other);
  });
  it("붙잡은 말 있음(답하는 중): 30초 org_status ≈ 1초마다 · 다른 조회(메뉴바·결과·세션 기록)는 종전 박자 그대로", async () => {
    const a = await orgCalls("old3s", true, 30_000);
    const b = await orgCalls("tick1s", true, 30_000);
    expect(b.org).toBeGreaterThanOrEqual(28);
    expect(31).toBeGreaterThanOrEqual(b.org);
    expect(b.other).toEqual(a.other); // 가벼운 조회 = 상태 조회만
  });
  it("상태 확인 늦음 계열(status_timeout)로 붙잡힌 말 = 1초 재조회 안 함(느린 연결에 조회를 쌓지 않음)", async () => {
    const sim = new Sim({ busyPasteOk: false }) /* (K-3) 「답하는 중」 붙잡음 장치 = 되돌리기 판 동작 */;
    await ready(sim, "tick1s");
    const inv = sim.deps.invoke;
    let org = 0;
    sim.deps.invoke = (cmd, args) => {
      if (cmd !== "org_status") return inv(cmd, args);
      org++;
      return new Promise(() => {}); // 상태 조회가 끝나지 않음(느린 연결) → 재조회 시간 상한 → status_timeout
    };
    sim.core.submit("둘");
    await sim.advance(2_000);
    const m = sim.core.state.msgs[sim.core.state.msgs.length - 1];
    expect([m.step, m.code]).toEqual(["held", "status_timeout"]);
    const before = org;
    await sim.advance(9_000);
    expect(3).toBeGreaterThanOrEqual(org - before); // 3초 박자(9초 = 3회) — 1초 박자였다면 9
    expect(sim.sends()).toBe(0);
  });
});

describe("② codex 1R major — 문턱(답하는 중)에 붙잡힌 뒤 연결이 멈추면 조회를 매초 쌓지 않는다", () => {
  async function hungAfterBusy(loop: Loop): Promise<number> {
    const sim = new Sim({ busyPasteOk: false }) /* (K-3) 「답하는 중」 붙잡음 장치 = 되돌리기 판 동작 */;
    await ready(sim, loop);
    sim.seat.working = true;
    sim.core.submit("둘");
    await sim.advance(10);
    expect(sim.core.state.msgs[sim.core.state.msgs.length - 1].code).toBe("busy");
    const inv = sim.deps.invoke;
    let org = 0;
    sim.deps.invoke = (cmd, args) => {
      if (cmd !== "org_status") return inv(cmd, args);
      org++;
      return new Promise(() => {}); // 끝나지 않는 조회(멈춘 연결)
    };
    await sim.advance(9_000);
    return org;
  }
  it("9초 동안 끝나지 않은 org_status 수 ≤ 종전 3초 박자(codex 재현: 종전 3 · 고치기 전 9)", async () => {
    const old = await hungAfterBusy("old3s");
    const now = await hungAfterBusy("tick1s");
    expect(old).toBe(3);
    expect(old + 1).toBeGreaterThanOrEqual(now); // 첫 가벼운 조회 1건(멈춤을 알아채는 몫)까지만
  });
  it("연결이 다시 제때 답하면 1초 재조회가 돌아온다(문턱 열림 → ≤1초 안 쓰기)", async () => {
    const sim = new Sim({ busyPasteOk: false }) /* (K-3) 「답하는 중」 붙잡음 장치 = 되돌리기 판 동작 */;
    await ready(sim, "tick1s");
    sim.seat.working = true;
    sim.core.submit("둘");
    await sim.advance(10);
    const inv = sim.deps.invoke;
    let hang = true;
    sim.deps.invoke = (cmd, args) => (hang && cmd === "org_status" ? new Promise(() => {}) : inv(cmd, args));
    await sim.advance(6_000);
    hang = false;
    await sim.advance(6_000); // 온전한 조회가 제때 끝나 늦음 표지가 풀림
    let openAt = 0;
    sim.later(1_500, () => {
      sim.seat.working = false;
      openAt = sim.now;
    });
    await sim.advance(5_000);
    const send = sim.calls.find((c) => c.cmd === "chat_send");
    expect(send !== undefined).toBe(true);
    expect(FAST_POLL_MS).toBeGreaterThanOrEqual((send?.at ?? 0) - openAt);
  });
});

describe("② 배선 — 대화 화면 시계 = 1초 pollTick", () => {
  it("chat/index.ts: every(FAST_POLL_MS, pollTick) · 종전 every(POLL_MS, poll) 0", () => {
    expect(CHAT).toContain("ctx.timers.every(FAST_POLL_MS, () => act.pollTick());");
    expect(CHAT).not.toContain("ctx.timers.every(POLL_MS, () => void act.poll());");
    expect(FAST_POLL_MS).toBe(1_000);
    expect(POLL_MS).toBe(3_000);
  });
});
