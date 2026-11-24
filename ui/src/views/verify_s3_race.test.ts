// (TICKET=verify-1119-s3 · 독립 검증 좌석 · 기록만) codex 가 짚은 순서 반례를 좌석 대역으로 재현(G1·G2) + 흐르는 덧붙임에서의 빈도(모형).
import { describe, it, expect } from "bun:test";
import { world } from "./verify_s3_world";

async function armed(o: Parameters<typeof world>[1], seed = 1) {
  const w = world(seed, o);
  w.core.attach();
  await w.flush();
  void w.core.poll();
  await w.advance(600); // 마스터 앎 → 시작점 → watch 걸림(대역 박자 = 250·500·750… ms)
  return w;
}

describe("verify-1119-s3 — 순서 반례(codex 지적 재현)", () => {
  // G1: tail 은 Rust 가 읽기 시작할 때 길이 S 를 찍는다. 그 응답이 화면에 닿기 전에 파일이 더 자라고 0.25초 박자가 그 길이(S+N)를 사건으로 알리면
  //     화면은 「tail 길이 < 사건 길이 = 다른 파일」(core.ts:1224 heldShorter)로 읽어 응답을 버리고 끝에서 다시 시작한다 → 그 사이 레코드 유실.
  it("G1 · 읽는 중에 파일이 더 자라고 박자 사건이 먼저 닿아도 — 정상 덧붙임을 파일 교체로 보지 않는다", async () => {
    const w = await armed({ reorder: false, compat: false, tailMs: [5, 5], watchMs: [1, 1] });
    expect(w.rust.watch).not.toBeNull();
    w.push(2);
    await w.advance(160); // 박자(750ms) → 사건 → tail → u1·u2
    expect(w.seen).toEqual(["u1", "u2"]);
    const fromEnd0 = w.rust.fromEnd;
    await w.advance(236); // 박자 4ms 앞
    w.push(1); // u3
    void w.core.readTranscript("after_send"); // 사건이 아닌 읽기 계기(보낸 뒤 +1/+3/+7초 · 3초 조회 · 다시 읽기) — Rust 가 길이 3 을 찍음
    await w.advance(1);
    w.push(1); // u4 — tail 응답이 닿기 전에 한 줄 더
    await w.advance(3); // 박자(1000ms): 길이 4 사건
    await w.advance(50); // tail 응답(길이 3) 도착
    await w.pass(8000);
    console.log(`[G1] 받은 레코드 ${JSON.stringify(w.seen)} · 파일 ${w.file.length}줄 · 시작점 다시 잡기 ${w.rust.fromEnd - fromEnd0}회 · unwatch ${w.calls.filter((c) => c === "chat_transcript_unwatch").length}회`);
    expect(w.rust.fromEnd - fromEnd0).toBe(0); // ★붉음 = 정상 덧붙임인데 끝에서 다시 시작
    expect(w.seen).toEqual(["u1", "u2", "u3", "u4"]); // ★붉음 = u3·u4 유실
  });

  // G2: 화면이 unwatch 를 보내고 곧바로 새 watch 를 건다. Rust 가 unwatch 를 새 watch 가 다 걸린 **뒤에** 처리하면(HANDOFF §3 ㉯6 ⑵)
  //     Rust 에는 watch 가 없고 화면은 걸려 있다고 믿는다 → 사건 0 · 3초 조회의 결속 재확인은 「같음」으로 지나감 → 계기 없는 덧붙임이 안 보인다.
  it("G2 · 늦게 처리된 unwatch 가 새 watch 를 내려도 — 계기 없는 덧붙임이 3초 조회 한두 번 안에 보인다", async () => {
    const w = await armed({ reorder: false, compat: false, unwatchMs: [40, 40], watchMs: [2, 2], tailMs: [1, 1] });
    w.core.watchStart(); // 대화 → 작업 → 대화 를 한 순간에
    w.core.detach();
    w.core.attach();
    w.core.watchStop();
    await w.advance(100);
    const rustHas = w.rust.watch !== null;
    w.push(2); // 마스터가 스스로 쓴 것(활동 바뀜 없음 · 보낸 말 없음)
    await w.pass(30_000);
    const at30 = [...w.seen];
    w.master.working = true;
    await w.pass(3500);
    w.master.working = false;
    await w.pass(6500);
    console.log(`[G2] unwatch 뒤 Rust watch 있음=${rustHas} · 30초 동안 받은 레코드 ${JSON.stringify(at30)} · 활동 바뀜 뒤 ${JSON.stringify(w.seen)} · not_watching ${w.rust.notWatching}회`);
    expect(rustHas).toBe(false); // 장면 검증: 화면은 걸렸다고 믿는데 Rust 에는 없음
    expect(w.seen).toEqual(["u1", "u2"]); // 계기가 오면 스스로 낫는다(HANDOFF 주장 확인)
    expect(at30).toEqual(["u1", "u2"]); // ★붉음 = 30초 동안 0(계기가 올 때까지 안 보임)
  });
});

// 빈도(모형 — 실기 값 아님): 마스터가 60초 동안 20~120ms 마다 한 줄씩 쓰고, 그 사이 활동 바뀜·보내기(사건이 아닌 읽기 계기)가 섞일 때
// G1 꼴(끝에서 다시 시작)이 몇 판에서 나고 몇 줄이 사라지는가 — tail 응답 지연(ms)별.
async function stream(seed: number, tailMs: [number, number], compat: boolean) {
  const w = await armed({ reorder: true, compat, tailMs }, seed);
  const fromEnd0 = w.rust.fromEnd;
  for (let t = w.ri(20, 120); t < 60_000; t += w.ri(20, 120)) w.at(t, () => w.push(1));
  for (let t = w.ri(2000, 5000); t < 60_000; t += w.ri(2000, 5000)) w.at(t, () => void (w.master.working = !w.master.working));
  for (let t = w.ri(4000, 9000); t < 60_000; t += w.ri(8000, 15000)) w.at(t, () => void w.core.submit(`말 ${t}`));
  await w.pass(61_000);
  w.master.working = true;
  await w.pass(3500);
  w.master.working = false;
  await w.pass(6500);
  const all = w.file.map((r) => String(r.uuid));
  const lost = all.filter((u) => !w.seen.includes(u)).length;
  const dup = w.seen.length - new Set(w.seen).size;
  return { total: all.length, lost, dup, reinit: w.rust.fromEnd - fromEnd0 };
}

// (만든 좌석 옮김 · 고침2 N3 · [master#f03515c6]) 기본 `bun test`(시험당 5초)에서도 돌게 — 한 it(400판 × 2길 · 14~24초)을 지연 구간별 it 넷으로 나누고
//   판 수를 구간마다 15 로 줄였다(타입 정의 src/bun-env.d.ts 의 it 은 시간 상한 인자를 받지 않음). 고침 전(526cf0609) 값으로 보면 30~80ms = 37/100 ·
//   150~300ms = 100/100 판이 어긋났으므로 15판에서도 V2 회귀를 잡는다(5~15ms 구간 5/100 은 15판에서 놓칠 수 있음 = 검출력 줄어듦 · 정직 기록).
const FLOW_SEEDS = 15;
describe("verify-1119-s3 — 흐르는 덧붙임 60초 × 15판(모형 · 구간별)", () => {
  for (const tailMs of [[1, 3], [5, 15], [30, 80], [150, 300]] as Array<[number, number]>) {
    it(`tail 지연 ${tailMs[0]}~${tailMs[1]}ms — 끝에서 다시 시작한 판 수 · 사라진 줄 수(1.1.18 길 대조 = 0)`, async () => {
      const acc = { runs: 0, hitRuns: 0, reinit: 0, lost: 0, total: 0, dup: 0, ctlLost: 0, ctlReinit: 0 };
      for (let seed = 1; seed <= FLOW_SEEDS; seed++) {
        const r = await stream(seed, tailMs, false);
        const c = await stream(seed, tailMs, true);
        acc.runs++;
        acc.total += r.total;
        acc.lost += r.lost;
        acc.dup += r.dup;
        acc.reinit += r.reinit;
        if (r.reinit > 0 || r.lost > 0) acc.hitRuns++;
        acc.ctlLost += c.lost;
        acc.ctlReinit += c.reinit;
      }
      console.log(`[흐름 모형] tail 지연 ${tailMs[0]}~${tailMs[1]}ms: ${FLOW_SEEDS}판 중 어긋난 판 ${acc.hitRuns} · 끝에서 다시 시작 ${acc.reinit}회 · 사라진 줄 ${acc.lost}/${acc.total} · 두 번 온 줄 ${acc.dup} ‖ 1.1.18 길: 사라진 줄 ${acc.ctlLost} · 다시 시작 ${acc.ctlReinit}`);
      expect(acc.hitRuns).toBe(0); // ★붉음 = 이 지연에서 정상 덧붙임 중 유실이 남
    });
  }
});
