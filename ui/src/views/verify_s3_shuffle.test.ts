// (TICKET=verify-1119-s3 · 독립 검증 좌석 · 기록만) 순서 뒤섞기 — 가짜 시계 위에서 watch·읽기·화면 전환·보내기를 무작위 순서·무작위 지연으로.
// 고정: 결속 세션 하나 · 마스터 행 늘 있음 · 파일은 덧붙이기만 → 바라는 것 = 끝에 조용해지면 **모든 레코드가 정확히 한 번**.
// 같은 씨앗을 되돌리기 켬(1.1.18 길)으로도 돌려 대조한다 — 1.1.19 길에서만 어긋난 판만 반례로 센다.
import { describe, it, expect } from "bun:test";
import { world } from "./verify_s3_world";

async function run(seed: number, reorder: boolean, compat: boolean) {
  const w = world(seed, { reorder, compat });
  const names = Object.keys(w.acts);
  const trace: string[] = [];
  w.core.attach();
  await w.flush();
  void w.core.poll(); // 마스터를 알고 시작점(파일 끝)을 잡은 뒤부터 뒤섞는다 — 그 앞 레코드는 건너뛰는 것이 맞다(대역 응답은 타이머라 await 하지 않는다)
  await w.advance(600);
  const fromEnd0 = w.rust.fromEnd;
  const steps = 30 + Math.floor(w.rnd() * 30);
  for (let i = 0; i < steps; i++) {
    const a = names[Math.floor(w.rnd() * names.length)];
    trace.push(a);
    await w.acts[a]();
    await w.flush();
  }
  // 조용해지기: 대화 화면으로 · 활동 바뀜 계기 두 번(1.1.18 길의 읽기 계기) · 12초
  await w.toChat();
  await w.pass(3500);
  w.master.working = true;
  await w.pass(3500);
  w.master.working = false;
  await w.pass(6000);
  const all = w.file.map((r) => String(r.uuid));
  const dup = w.seen.filter((u, i) => w.seen.indexOf(u) !== i);
  const missing = all.filter((u) => !w.seen.includes(u));
  return { seed, reorder, trace, dup, missing, fromEnd0, order: w.seen.join(",") === all.filter((u) => w.seen.includes(u)).join(","), rust: w.rust, total: all.length, watching: w.rust.watch !== null };
}

describe("verify-1119-s3 — 순서 뒤섞기(결속 고정 · 덧붙이기만)", () => {
  for (const reorder of [false, true]) {
    it(`무작위 순서 400판 · 명령 처리 순서 뒤바뀜 ${reorder ? "있음" : "없음"} — 모든 레코드 정확히 한 번 · tail 겹침 0 · 시작점 다시 잡기 0(1.1.18 길 대조)`, async () => {
      const bad: Array<Record<string, unknown>> = [];
      const mk = () => ({ runs: 0, records: 0, dupRuns: 0, missRuns: 0, orderBad: 0, extraFromEnd: 0, maxTail: 0, armed: 0, superseded: 0, notWatching: 0, events: 0, endNotWatching: 0 });
      const sum = { v119: mk(), v118: mk() };
      let onlyNew = 0;
      for (let seed = 1; seed <= 400; seed++) {
        const res = { v119: await run(seed, reorder, false), v118: await run(seed, reorder, true) };
        for (const k of ["v119", "v118"] as const) {
          const r = res[k];
          const m = sum[k];
          m.runs++;
          m.records += r.total;
          m.maxTail = Math.max(m.maxTail, r.rust.maxTailInflight);
          m.armed += r.rust.armed;
          m.superseded += r.rust.superseded;
          m.notWatching += r.rust.notWatching;
          m.events += r.rust.events;
          if (!r.watching) m.endNotWatching++;
          if (r.dup.length) m.dupRuns++;
          if (r.missing.length) m.missRuns++;
          if (!r.order) m.orderBad++;
          if (r.rust.fromEnd > r.fromEnd0) m.extraFromEnd++;
        }
        const r = res.v119;
        const worse = (r.dup.length > 0 && res.v118.dup.length === 0) || (r.missing.length > 0 && res.v118.missing.length === 0) || (!r.order && res.v118.order) || (r.rust.fromEnd > r.fromEnd0 && res.v118.rust.fromEnd <= res.v118.fromEnd0);
        if (worse) {
          onlyNew++;
          if (bad.length < 4) bad.push({ seed, dup: r.dup, missing: r.missing, fromEnd0: r.fromEnd0, fromEnd: r.rust.fromEnd, trace: r.trace.join(" ") });
        }
      }
      console.log(`[뒤섞기 reorder=${reorder}] 1.1.19 길 ${JSON.stringify(sum.v119)}`);
      console.log(`[뒤섞기 reorder=${reorder}] 1.1.18 길 ${JSON.stringify(sum.v118)}`);
      console.log(`[뒤섞기 reorder=${reorder}] 1.1.19 길에서만 어긋난 판 = ${onlyNew}`);
      for (const b of bad) console.log("  반례:", JSON.stringify(b));
      expect(sum.v119.maxTail <= 1).toBe(true); // (만든 좌석 옮김 · 타입 게이트: bun:test Matchers 형 정의에 toBeLessThanOrEqual 없음 — 뜻 같음)
      expect(sum.v119.dupRuns).toBe(0);
      expect(onlyNew).toBe(0);
    });
  }
});
