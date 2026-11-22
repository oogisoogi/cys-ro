// 3초 고리 판정(decideTick) 시험 — TICKET=cysr-1116-s2-1119 · P2-DESIGN §2-1 시험 ②「같은 입력 → 같은 판정」 · §3-3 게이트 1·2.
//   ① 순수성: tick.ts 에 화면·저장소·Tauri·시각·타이머 낱말 0
//   ② 재생: 조각 0 견본 덤프(분리 전 코드가 남긴 200틱)의 각 칸을 decideTick 에 넣으면 기록된 판정(유령 퇴거·쓸기·입양 순서·자리표 입력과 결과·
//      유령 카운터)과 바이트로 같다 · 같은 칸을 두 번 넣어도 같은 바이트
//   ③ F18: 런타임이 미뤄진 자리표(화면 줄 null) = 회수 보류(장부 유지) · 화면 줄이 생기면 그때 회수
//   ④ 입양 후보: 미룬 좌석(known)을 다시 고르지 않음 · 대기·삭제 중 탭에 붙이지 않음 · 역할 우선순위 · 퇴거·쓸기 뒤 트리를 봄
//   ⑤ 덤프 원천: TICKREC_REPLAY 환경값이 있으면 그 덤프도 같은 대조(e2e 새 번들 덤프 = 분리 뒤 코드가 남긴 기록)
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { decidePlaceholders, decideSockPre, decideTick, rolePri, type TickWs } from "./tick";

const SRC = readFileSync(new URL("./tick.ts", import.meta.url), "utf8");
const SAMPLE = new URL("../../../../docs/ui-p2/evidence/tickrec-200.sample.json", import.meta.url);

type Entry = Record<string, unknown> & {
  seq: number;
  wsTrunc: boolean;
  socks: { got: boolean; trunc?: boolean }[];
  ghost: unknown;
  sweep: unknown;
  adopt: unknown;
  adoptAbort: unknown[];
  ph: { sock: string; sid: number; close: boolean; in: unknown }[];
  ghostOut: unknown;
  err: string[];
  done: boolean;
};

/** 기록 칸에서 decideTick 과 견줄 부분만 같은 꼴로 뽑는다(자리표 `closed` = 집행 결과라 판정 밖). */
const recorded = (e: Entry) =>
  JSON.stringify({
    ghost: e.ghost,
    sweep: e.sweep,
    adopt: e.adopt,
    ph: e.ph.map((p) => ({ sock: p.sock, sid: p.sid, close: p.close, in: p.in })),
    ghostOut: e.ghostOut,
  });
const replayed = (e: Entry) => {
  const r = decideTick(e);
  return JSON.stringify({ ghost: r.ghost, sweep: r.sweep, adopt: r.adopt, ph: r.ph, ghostOut: r.ghostOut });
};
/** 재생 가능한 칸 — 끝까지 돈 칸 · 잘림 없음 · 입양 포기(await 사이 탭 지워짐 = 판정 밖 경합) 없음 · 오류 없음. */
const replayable = (e: Entry) => e.done && !e.wsTrunc && e.socks.every((s) => !s.trunc) && e.adoptAbort.length === 0 && e.err.length === 0;

function replayDump(path: URL | string): { n: number; decisions: Record<string, number>; mismatch: string[] } {
  const d = JSON.parse(readFileSync(path, "utf8")) as { schema: string; entries: Entry[] };
  expect(d.schema).toBe("cys-tickrec/1");
  const mismatch: string[] = [];
  const decisions = { adopt: 0, evict: 0, sweep: 0, phJudged: 0, phClose: 0 };
  let n = 0;
  for (const e of d.entries) {
    if (!replayable(e)) continue;
    n++;
    const want = recorded(e);
    const got = replayed(e);
    if (got !== want) mismatch.push(`seq ${e.seq}\n want ${want}\n  got ${got}`);
    if (replayed(e) !== got) mismatch.push(`seq ${e.seq} 두 번째 재생이 다름`);
    const r = decideTick(e);
    decisions.adopt += r.adopt.length;
    decisions.evict += r.ghost.reduce((a, g) => a + g.evict.length, 0);
    decisions.sweep += r.sweep.reduce((a, g) => a + g.targets.length, 0);
    decisions.phJudged += r.ph.length;
    decisions.phClose += r.ph.filter((p) => p.close).length;
  }
  return { n, decisions, mismatch };
}

describe("① 순수성(§3-3 규칙 ①)", () => {
  it("tick.ts 에 document·window·localStorage·__TAURI__·Date.now·setTimeout·setInterval·invoke·performance 0", () => {
    const src = SRC.replace(/\/\/.*$/gm, "");
    for (const w of ["document", "window", "localStorage", "__TAURI__", "Date.now", "setTimeout", "setInterval", "invoke", "performance", "Math.random"]) expect(`${w}:${src.includes(w)}`).toBe(`${w}:false`);
  });
  it("import = 순수 판정 모듈 셋뿐(wsreconcile·exitedsweep·placeholderclose)", () => {
    const imports = [...SRC.matchAll(/^import .* from "([^"]+)";$/gm)].map((m) => m[1]).sort();
    expect(imports).toEqual(["../../exitedsweep", "../../placeholderclose", "../../wsreconcile"]);
  });
});

describe("② 재생 — 분리 전 코드의 기록(조각 0 견본 200틱) = decideTick", () => {
  it("재생 가능한 칸 전부 바이트 같음 · 두 번 넣어도 같음 · 판정 종류가 실제로 들어 있음", () => {
    const r = replayDump(SAMPLE);
    expect(r.mismatch).toEqual([]);
    expect(r.n).toBeGreaterThanOrEqual(150);
    // 견본의 판정 수(조각 0 인계 §8): 입양 6 · 유령 퇴거 1 · 옛 자리 쓸기 1 · 자리표 판정 5(회수 1) — 빈 대조가 아님을 못박는다.
    expect(r.decisions.adopt).toBeGreaterThanOrEqual(6);
    expect(r.decisions.evict).toBeGreaterThanOrEqual(1);
    expect(r.decisions.sweep).toBeGreaterThanOrEqual(1);
    expect(r.decisions.phJudged).toBeGreaterThanOrEqual(5);
    expect(r.decisions.phClose).toBeGreaterThanOrEqual(1);
  });
  it("음성 대조 — 기록의 판정 하나를 바꾸면 대조가 잡는다(비교기가 비어 있지 않다)", () => {
    const d = JSON.parse(readFileSync(SAMPLE, "utf8")) as { entries: Entry[] };
    const e = d.entries.find((x) => replayable(x) && Array.isArray(x.adopt) && (x.adopt as unknown[]).length > 0)!;
    expect(e !== undefined).toBe(true);
    const bent = { ...e, adopt: [...(e.adopt as unknown[])].reverse().concat([{ sock: "~", sid: 1, role: "master" }]) } as Entry;
    expect(replayed(e)).toBe(recorded(e));
    expect(recorded(bent)).not.toBe(replayed(e));
  });
  const extra = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env?.TICKREC_REPLAY;
  (extra ? it : it.skip)("⑤ 환경값 TICKREC_REPLAY 덤프(e2e 새 번들 기록)도 같은 대조", () => {
    const r = replayDump(extra as string);
    expect(r.mismatch).toEqual([]);
    expect(r.n).toBeGreaterThanOrEqual(100);
  });
});

const ws = (id: number, sids: number[], sock = "", extra: Partial<TickWs> = {}): TickWs => ({ id, sock, pending: false, deleting: false, sids, ...extra });

describe("③ F18 — 런타임 미룬 자리표 = 회수 보류", () => {
  const base = {
    sock: "",
    surfaces: [{ surface_id: 9, role: null, exited: false }, { surface_id: 10, role: "master", exited: false }],
    placeholders: new Set([9]),
    touched: new Set<number>(),
    isWindows: false,
  };
  it("화면 줄 null(런타임 없음) → close false · 같은 입력 두 번 같은 바이트", () => {
    const run = () => decidePlaceholders({ ...base, ws: [ws(1, [9, 10])], lineCount: () => null });
    expect(run()).toEqual([{ wsId: 1, sid: 9, close: false, in: { isOwnPlaceholder: true, touched: false, role: null, lineCount: null, isWindows: false, formationArrived: true, exited: false } }]);
    expect(JSON.stringify(run())).toBe(JSON.stringify(run()));
  });
  it("같은 장면에 화면 줄이 생기면(런타임 생성 뒤) 그때 회수", () => {
    expect(decidePlaceholders({ ...base, ws: [ws(1, [9, 10])], lineCount: () => 1 }).map((v) => v.close)).toEqual([true]);
  });
  it("장부 밖 번호(남의 페인)는 판정 대상조차 아님 · 손댄 자리는 닫지 않음", () => {
    expect(decidePlaceholders({ ...base, placeholders: new Set<number>(), ws: [ws(1, [9, 10])], lineCount: () => 1 })).toEqual([]);
    expect(decidePlaceholders({ ...base, touched: new Set([9]), ws: [ws(1, [9, 10])], lineCount: () => 1 }).map((v) => v.close)).toEqual([false]);
  });
  it("대기 중 탭 제외 · 삭제 중 탭은 대상(종전 조건 그대로)", () => {
    expect(decidePlaceholders({ ...base, ws: [ws(1, [9, 10], "", { pending: true })], lineCount: () => 1 })).toEqual([]);
    expect(decidePlaceholders({ ...base, ws: [ws(1, [9, 10], "", { deleting: true })], lineCount: () => 1 }).map((v) => v.close)).toEqual([true]);
  });
});

describe("④ 입양 후보(decideSockPre)", () => {
  const pre = (o: Partial<Parameters<typeof decideSockPre>[0]>) =>
    decideSockPre({ sock: "", ws: [ws(1, [])], surfaces: [], ghostStrike: new Map(), sweepScope: null, known: new Set(), ...o });
  it("역할 우선순위 master>cso>worker>reviewer · 같은 순위 = 목록 순 · 역할 없음·끝남 제외", () => {
    const r = pre({
      surfaces: [
        { surface_id: 5, role: "reviewer-codex", exited: false },
        { surface_id: 4, role: "worker-2", exited: false },
        { surface_id: 3, role: "worker-1", exited: false },
        { surface_id: 2, role: "cso", exited: false },
        { surface_id: 1, role: "master", exited: false },
        { surface_id: 6, role: null, exited: false },
        { surface_id: 7, role: "worker-3", exited: true },
      ],
    });
    expect(r.adopt.map((a) => a.sid)).toEqual([1, 2, 4, 3, 5]);
    expect([rolePri("master"), rolePri("cso"), rolePri("worker-9"), rolePri("reviewer-x"), rolePri(null)]).toEqual([0, 1, 2, 3, 4]);
  });
  it("미룬 좌석(known 에 있음 · 런타임 없음)은 다시 고르지 않는다 = 두 탭 이중 입양 0", () => {
    const r = pre({ ws: [ws(1, []), ws(2, [8])], surfaces: [{ surface_id: 8, role: "worker-1", exited: false }], known: new Set([8]) });
    expect(r.adopt).toEqual([]);
  });
  it("집 = 그 소켓 첫 살아 있는 탭(대기·삭제 중 건너뜀) · 다른 소켓 탭 제외 · 없으면 입양 0", () => {
    const s = [{ surface_id: 8, role: "worker-1", exited: false }];
    expect(pre({ ws: [ws(1, [], "", { pending: true }), ws(2, [], "", { deleting: true }), ws(3, [])], surfaces: s }).adopt).toEqual([{ sid: 8, role: "worker-1", wsId: 3 }]);
    expect(pre({ ws: [ws(1, [], "/dept.sock")], surfaces: s }).adopt).toEqual([]);
    expect(pre({ ws: [ws(1, [], "", { pending: true })], surfaces: s }).adopt).toEqual([]);
  });
  it("유령 2연속 퇴거 · 쓸기 = 무장 범위 ∩ 트리 ∩ 끝남 · 입력 모형은 바꾸지 않는다", () => {
    const w = [ws(1, [20, 21, 22])];
    const known = new Set([20, 21, 22]);
    const surfaces = [{ surface_id: 21, role: "worker-1", exited: true }, { surface_id: 22, role: "master", exited: false }];
    const one = pre({ ws: w, surfaces, known, sweepScope: new Set([21]) });
    expect(one.evict).toEqual([]); // 1회차 = 관측만
    expect(one.sweepTargets).toEqual([21]);
    const two = pre({ ws: w, surfaces, known, ghostStrike: one.ghostNext });
    expect(two.evict).toEqual([20]);
    expect(w[0].sids).toEqual([20, 21, 22]);
    expect([...known]).toEqual([20, 21, 22]);
  });
});
