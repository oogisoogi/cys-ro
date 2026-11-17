// (cysr-ui-slice3) M2·M3 하네스 — PRD M2 「행방 불명 0」 · M3 「틀림 0」 · 4군 ① 「같은 말 두 번 0」.
// 씨앗 고정 무작위 시나리오 N개: 사람 말 8개(20%는 앞 말과 같은 글) · 데몬 응답 7꼴(written·불명(씀/안 씀)·확정 거부·걸림(씀/안 씀)·쓰기 직전 거부)
// · 승인 창·feed 대기·사람 초안·마스터 꺼짐을 아무 때나 켜고 끔 · 세션 기록 늦음/안 생김(U20 접힌 꼴 대역) · uuid 없는 꼴(M8) · 사람 클릭(이 말 보내기·다시 보내기).
// 0.25초마다 화면 단계(core 상태)를 진실(testkit Sim 쓰기 기록)과 대조한다. 「확인 중·오래 걸려요·보내는 중」은 「모름」이라 틀림이 아니다(PRD M3).
import { describe, it, expect } from "bun:test";
import { DUP, dupPending, needsClick } from "./core";
import { canRetry, STEP_LABEL, type Msg } from "./judge/msgstep";
import { Sim, type SendKind } from "./testkit";

/** 진단·넓게 돌리기용 환경 변수(타입 검증 설정에 node 타입이 없어 전역에서 읽음) */
const ENV: Record<string, string | undefined> = (globalThis as unknown as { process?: { env: Record<string, string | undefined> } }).process?.env ?? {};

function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const KINDS: Array<[SendKind, number]> = [
  ["written", 55],
  ["uncertain_written", 8],
  ["uncertain_lost", 7],
  ["failed", 7],
  ["hang_written", 6],
  ["hang_lost", 5],
  ["refuse_at_write", 12],
];

function pick<T>(r: () => number, ws: Array<[T, number]>): T {
  const tot = ws.reduce((s, [, w]) => s + w, 0);
  let x = r() * tot;
  for (const [v, w] of ws) if ((x -= w) < 0) return v;
  return ws[ws.length - 1][0];
}

export interface Tally {
  scenarios: number;
  msgs: number;
  samples: number;
  missing: number;
  wrong: number;
  dupRisk: number;
  multiWrite: number;
  steps: Record<string, number>;
  kinds: Record<string, number>;
  wrongWhy: string[];
}

export async function runScenario(seed: number, t: Tally, dump = false): Promise<void> {
  const r = rng(seed);
  const noUuid = r() < 0.15;
  const sim = new Sim({
    plan: () => pick(r, KINDS),
    recordDelay: () => {
      const x = r();
      return x < 0.8 ? 100 + Math.floor(r() * 3_900) : x < 0.9 ? 30_000 + Math.floor(r() * 170_000) : null;
    },
    replyDelay: () => (r() < 0.7 ? 500 + Math.floor(r() * 19_500) : null),
    hangMs: 4_000 + Math.floor(r() * 6_000),
    noUuid,
  });
  sim.core.attach();
  await sim.flush();
  sim.startPolling();
  const texts: string[] = [];
  const accepted: string[] = [];
  // 사람 말 8개 · 0~300초 사이
  for (let i = 0; i < 8; i++) {
    const at = Math.floor(r() * 300_000);
    const text = texts.length > 0 && r() < 0.2 ? texts[Math.floor(r() * texts.length)] : `말 ${seed}-${i}${r() < 0.2 ? "\n둘째 줄" : ""}`;
    texts.push(text);
    sim.later(at, () => {
      if (sim.core.submit(text)) accepted.push(text);
    });
  }
  // 환경 사건: 4~20초마다 하나 · 막힘 상태는 2~10초 켜졌다 꺼짐(승인 창·feed 대기·사람 초안·마스터 꺼짐) · 가끔 남은 글 지움
  let envT = 0;
  while (envT < 330_000) {
    envT += 4_000 + Math.floor(r() * 16_000);
    const x = r();
    const dur = 2_000 + Math.floor(r() * 8_000);
    sim.later(envT, () => {
      if (x < 0.2) {
        sim.screen = true;
        sim.later(dur, () => (sim.screen = false));
      } else if (x < 0.4) {
        sim.approvals = [5];
        sim.later(dur, () => (sim.approvals = []));
      } else if (x < 0.55) {
        sim.seat.pending_input_human_bytes = 12;
        sim.seat.pending_input_bytes = 12;
        sim.lastHumanAt = sim.now;
        sim.later(dur, () => {
          sim.seat.pending_input_human_bytes = 0;
          sim.seat.pending_input_bytes = 0;
        });
      } else if (x < 0.62) {
        sim.seat.agent_alive = false;
        sim.later(dur, () => (sim.seat.agent_alive = true));
      } else if (x < 0.8) sim.seat.pending_input_bytes = 0; // 사람이 작업 화면에서 남은 글을 지움(쓰기 직전 거부 뒤 잔여)
    });
  }
  // 사람 클릭: 5초마다 보이는 단추를 가끔 누름(화면 규칙 그대로 — 겹침 중 단추 없음)
  let clickT = 0;
  while (clickT < 330_000) {
    clickT += 5_000;
    sim.later(clickT, () => {
      for (const m of sim.core.state.msgs) {
        const visible = needsClick(m) && !(m.code === DUP && dupPending(sim.core.state.msgs, m.text, m.id));
        if (visible && r() < 0.3) void sim.core.confirmHeld(m.id);
        if (canRetry(m) && r() < 0.5) void sim.core.retry(m.id); // 화면은 겹침 중 단추를 숨기지만, 하네스는 core 가 스스로 막는지까지 본다(단추 규칙을 빼고 누름)
      }
    });
  }

  // 표본 시계: 0.25초마다 빈 타이머 하나(advance 가 타이머마다 check 를 부른다 → 표본 간격 ≤ 0.25초)
  const sample = () => void sim.later(250, sample);
  sample();
  let seenWrites = 0;
  const check = () => {
    t.samples++;
    const msgs = sim.core.state.msgs;
    // M2 — 받아들인 말은 전부 목록에 있고 단계 문구가 있다
    if (msgs.length < accepted.length) t.missing++;
    for (const m of msgs) if (!STEP_LABEL[m.step]) t.missing++;
    // 4군 ① — 새 쓰기마다: 같은 글의 앞 쓰기(바이트 들어감)가 아직 세션 기록으로 확인되지 않았으면 위험
    for (; seenWrites < sim.writes.length; seenWrites++) {
      const w = sim.writes[seenWrites];
      if (!w.bytesIn) continue;
      for (let j = 0; j < seenWrites; j++) {
        const p = sim.writes[j];
        if (p.bytesIn && p.text === w.text && !sim.recorded.has(j)) t.dupRisk++;
      }
    }
    // M3 — 단계 ≠ 진실
    for (const m of msgs) {
      const ws = sim.writes.map((w, i) => ({ w, i })).filter((x) => x.w.msgId === m.id);
      const inIdx = ws.filter((x) => x.w.bytesIn);
      if (inIdx.length > 1) t.multiWrite++;
      const bad = (why: string) => {
        t.wrong++;
        if (t.wrongWhy.length < 10) t.wrongWhy.push(`seed ${seed} ${m.id} ${m.step}: ${why}`);
      };
      switch (m.step) {
        case "held":
        case "failed":
        case "queued_hold":
          if (inIdx.length > 0) bad("바이트가 들어갔는데 붙잡음/못 보냄");
          break;
        case "injected":
          if (inIdx.length === 0) bad("바이트 0 인데 전달 확인 중");
          break;
        case "delivered":
        case "replying":
        case "replied": {
          const rec = inIdx.filter((x) => sim.recorded.has(x.i));
          if (rec.length === 0) bad("세션 기록이 없는데 전달됨 이상");
          if (m.userUuid && sim.recordOf.has(m.userUuid) && sim.writes[sim.recordOf.get(m.userUuid) as number].msgId !== m.id) bad("다른 말의 레코드에 짝지음");
          if (m.step === "replied" && !inIdx.some((x) => sim.replied.has(x.i))) bad("답이 없는데 답함");
          break;
        }
        default:
          break; // sending·checking·slow = 모름
      }
    }
  };
  await sim.advance(360_000, check);
  if (dump) console.log(JSON.stringify({ writes: sim.writes, file: sim.file, msgs: sim.core.state.msgs.map((m) => ({ id: m.id, text: m.text, step: m.step, sentAt: m.sentAt, userUuid: m.userUuid, code: m.code })) }, null, 0));
  t.scenarios++;
  t.msgs += sim.core.state.msgs.length;
  for (const m of sim.core.state.msgs as Msg[]) t.steps[m.step] = (t.steps[m.step] ?? 0) + 1;
  for (const w of sim.writes) t.kinds[w.outcome + (w.refused ? "(거부)" : "")] = (t.kinds[w.outcome + (w.refused ? "(거부)" : "")] ?? 0) + 1;
}

describe("M2·M3 하네스 — 행방 불명 0 · 틀림 0 · 같은 말 두 번 0", () => {
  it("씨앗 1~200 · 시나리오마다 6분(가짜 시계) · 0.25초 이하 간격 표본", async () => {
    const t: Tally = { scenarios: 0, msgs: 0, samples: 0, missing: 0, wrong: 0, dupRisk: 0, multiWrite: 0, steps: {}, kinds: {}, wrongWhy: [] };
    const only = Number(ENV.MSGHARNESS_DUMP_SEED ?? 0); // 진단용: 그 씨앗 하나만 돌려 쓰기·기록·말 목록을 찍는다
    if (only > 0) {
      await runScenario(only, t, true);
      console.log(t.wrongWhy.join("\n"));
      return;
    }
    const n = Number(ENV.MSGHARNESS_SEEDS ?? 200); // 기본 200 · 넓게 돌릴 때 환경 변수로
    for (let seed = 1; seed <= n; seed++) await runScenario(seed, t);
    console.log(`[M2·M3] ${JSON.stringify({ ...t, wrongWhy: t.wrongWhy })}`);
    expect(t.scenarios).toBe(n);
    expect(t.msgs).toBeGreaterThan(1_000);
    expect(t.missing).toBe(0);
    expect(t.wrongWhy).toEqual([]);
    expect(t.wrong).toBe(0);
    expect(t.dupRisk).toBe(0);
    expect(t.multiWrite).toBe(0);
    // 하네스가 실제로 여러 갈래를 지났는지(빈 시험 방지)
    for (const s of ["held", "injected", "delivered", "replied", "failed", "checking", "slow"]) expect(t.steps[s] ?? 0).toBeGreaterThan(0);
  });
});
