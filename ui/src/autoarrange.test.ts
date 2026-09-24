// autoarrange.test.ts — 창 열기·닫기 자동 좌우 균등(TICKET=v116-auto-equalize · 오너 지시 2026-09-25 05:2x).
//
// ★이 스위트가 재야 하는 것:
//   ⑴좌열(master·cso)의 화면 몫과 위아래 비율이 열기·닫기를 지나도 **입력 트리 값 그대로**인가(오너 ①).
//   ⑵그 밖의 좌석은 몇 개든 한 줄 좌우 균등인가(오너 ②) — 사람이 위아래로 나눈 것도 편다.
//   ⑶좌석 집합 보존 — 결과 sid 집합 = (입력 − remove) ∪ add. 빠지면 「살아 있는데 안 보이는 좌석」(4군 ④).
//   ⑷재현된 세 결함(R1 HQ 첫 배치 뒤 재배치 멈춤 · R2 닫기 형제 독차지 · R3 새 창 0.5)이 이 함수로 사라지는가.
import { describe, it, expect } from "bun:test";
import { autoArrange, formationLayout, leftColumnShare, MASTER_CSO_RATIO, RULE_TOL, type LayoutNode, type Seat } from "./formation";

const P = (sid: number): LayoutNode => ({ type: "pane", sid });
const S = (a: LayoutNode, b: LayoutNode, dir: "row" | "col" = "row", ratio?: number): LayoutNode =>
  ratio === undefined ? { type: "split", dir, a, b } : { type: "split", dir, ratio, a, b };
function shares(n: LayoutNode, w = 1, out = new Map<number, number>()): Map<number, number> {
  if (n.type === "pane") { out.set(n.sid, w); return out; }
  const r = n.ratio ?? 0.5;
  if (n.dir === "row") { shares(n.a, w * r, out); shares(n.b, w * (1 - r), out); }
  else { shares(n.a, w, out); shares(n.b, w, out); } // 세로 분할은 가로 몫을 나누지 않는다
  return out;
}
function area(n: LayoutNode, w = 1, out = new Map<number, number>()): Map<number, number> {
  if (n.type === "pane") { out.set(n.sid, w); return out; }
  const r = n.ratio ?? 0.5;
  area(n.a, w * r, out); area(n.b, w * (1 - r), out);
  return out;
}
const sids = (n: LayoutNode | null, o: number[] = []): number[] => {
  if (!n) return o;
  if (n.type === "pane") o.push(n.sid); else { sids(n.a, o); sids(n.b, o); }
  return o;
};
const hasCol = (n: LayoutNode | null): boolean => !!n && n.type === "split" && (n.dir === "col" || hasCol(n.a) || hasCol(n.b));
const roles = (xs: [number, string | null][]) => new Map<number, string | null>(xs);
const seats = (xs: [number, string | null][]): Seat[] => xs.map(([sid, role]) => ({ sid, role }));
const W = (...ids: number[]) => ids.map((i): [number, string] => [i, "worker"]);
const HQ: [number, string][] = [[1, "master"], [2, "cso"]];

// 좌열 몫(가로) — master 칸의 가로 몫과 같다.
const leftW = (t: LayoutNode) => shares(t).get(1) ?? shares(t).get(2)!;
// 워커 칸 가로 몫이 모두 같은가.
function evenRest(t: LayoutNode, rest: number[]) {
  const sh = shares(t);
  const v = rest.map((s) => sh.get(s)!);
  for (const x of v) expect(x).toBeCloseTo(v[0], 12);
}

describe("⑷ 재현된 결함이 사라진다", () => {
  it("R1 HQ 첫 배치 뒤 워커 입양 → 재배치됨 · 좌열 = 새 워커 수의 규칙값 · 워커 균등(종전 = 새 워커 0.50 · master 0.20)", () => {
    const r = roles([...HQ, ...W(3, 4)]);
    const t0 = formationLayout(seats([...HQ, ...W(3)]))!;
    const t1 = autoArrange(t0, r, { add: [{ sid: 4 }] })!;
    expect(leftW(t1)).toBeCloseTo(leftColumnShare(2), 12);
    evenRest(t1, [3, 4]);
    // 위아래 비율 4:1 도 그대로
    const a = area(t1);
    expect(a.get(1)! / a.get(2)!).toBeCloseTo(4, 9);
  });
  it("R2 워커 3 중 가운데 닫기 → 남은 둘 균등(종전 = 1/3 : 2/3)", () => {
    const t0 = formationLayout(seats(W(3, 4, 5)))!;
    const t1 = autoArrange(t0, roles(W(3, 4, 5)), { remove: [4] })!;
    expect(sids(t1)).toEqual([3, 5]);
    evenRest(t1, [3, 5]);
  });
  it("R2b HQ 기기 가운데 워커 닫기 → 좌열 몫 그대로 · 남은 워커 균등", () => {
    const r = roles([...HQ, ...W(3, 4, 5)]);
    const t0 = formationLayout(seats([...HQ, ...W(3, 4, 5)]))!;
    const t1 = autoArrange(t0, r, { remove: [4] })!;
    expect(leftW(t1)).toBeCloseTo(leftW(t0), 12);
    evenRest(t1, [3, 5]);
  });
  it("R3 새 창 → 기존 워커와 같은 폭(종전 = 새 창 0.50)", () => {
    const t0 = formationLayout(seats(W(3, 4, 5)))!;
    const t1 = autoArrange(t0, roles(W(3, 4, 5)), { add: [{ sid: 9 }] })!;
    expect(sids(t1)).toEqual([3, 4, 5, 9]);
    evenRest(t1, [3, 4, 5, 9]);
  });
});

describe("⑴ 좌열 보존(오너 ①)", () => {
  it("사람이 끈 좌열 몫(0.4)과 위아래 비율(0.6)이 열기·닫기 뒤에도 그대로", () => {
    const left = S(P(1), P(2), "col", 0.6);
    const t0 = S(left, S(P(3), P(4), "row", 0.3), "row", 0.4);
    const r = roles([...HQ, ...W(3, 4, 5)]);
    const opened = autoArrange(t0, r, { add: [{ sid: 5 }] })!;
    expect(leftW(opened)).toBeCloseTo(0.4, 12);
    expect((opened as any).a).toBe(left); // 좌열 서브트리 = 같은 객체(위아래 비율 포함 무변경)
    evenRest(opened, [3, 4, 5]);
    const closed = autoArrange(opened, r, { remove: [3] })!;
    expect(leftW(closed)).toBeCloseTo(0.4, 12);
    expect((closed as any).a).toBe(left);
    evenRest(closed, [4, 5]);
  });
  it("입양 래퍼(0.5)로 감싸기 전 트리를 넘기므로 사람이 끈 좌열 몫이 반으로 줄지 않는다", () => {
    const t0 = S(S(P(1), P(2), "col", 0.8), P(3), "row", 0.45);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), { add: [{ sid: 4 }] })!;
    expect(leftW(t1)).toBeCloseTo(0.45, 12);
  });
  it("master 가 닫히면 cso 가 좌열 전체 · 몫 그대로", () => {
    const t0 = formationLayout(seats([...HQ, ...W(3, 4)]))!;
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), { remove: [1] })!;
    expect((t1 as any).a).toEqual(P(2));
    expect(shares(t1).get(2)).toBeCloseTo(leftW(t0), 12);
    evenRest(t1, [3, 4]);
  });
  it("master 만 있다가 cso 가 들어오면 좌열 = master(위):cso(아래) 4:1 · 몫 그대로", () => {
    const t0 = S(P(1), S(P(3), P(4), "row", 0.5), "row", 0.3);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), { add: [{ sid: 2 }] })!;
    expect(leftW(t1)).toBeCloseTo(0.3, 12);
    const a = area(t1);
    expect(a.get(1)! / a.get(2)!).toBeCloseTo(4, 9);
    evenRest(t1, [3, 4]);
  });
  it("좌열뿐이던 화면에 첫 워커 → 표준 몫(퇴화 몫 1 을 쓰지 않는다)", () => {
    const t0 = formationLayout(seats(HQ))!;
    const t1 = autoArrange(t0, roles([...HQ, ...W(3)]), { add: [{ sid: 3 }] })!;
    expect(leftW(t1)).toBeCloseTo(leftColumnShare(1), 12);
  });
  it("워커가 다 닫히면 좌열만 남는다(래퍼 없음 · 위아래 비율 그대로)", () => {
    const t0 = formationLayout(seats([...HQ, ...W(3)]))!;
    const t1 = autoArrange(t0, roles([...HQ, ...W(3)]), { remove: [3] })!;
    expect(t1).toEqual({ type: "split", dir: "col", ratio: MASTER_CSO_RATIO, a: P(1), b: P(2) });
  });
  it("좌열 이상 위치(좌열 안에 워커가 끼어 있음) → 표준 배치로 폴백", () => {
    const t0 = S(S(P(1), P(3), "col", 0.5), S(P(2), P(4)), "row", 0.5);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), { add: [{ sid: 5 }] })!;
    expect(t1).toEqual(formationLayout(seats([...HQ, ...W(3, 4, 5)])));
  });
  it("좌열 이상 위치(master·cso 가 세로 열 안에 워커를 품음 · 그 열 몫 0.6) → 그 몫을 이어받지 않고 표준 배치", () => {
    const t0 = S(S(P(1), S(P(3), P(2), "row"), "col", 0.7), P(4), "row", 0.6);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4, 5)]), { add: [{ sid: 5 }] })!;
    expect(t1).toEqual(formationLayout(seats([...HQ, ...W(3, 4, 5)])));
  });
  it("좌열 이상 위치(좌열이 위아래 분할 속 · 비율이 규칙값과 다름) → 표준 배치로 폴백(세로 비율을 가로 몫으로 오독하지 않는다)", () => {
    const t0 = S(S(P(1), P(2), "col", 0.6), P(3), "col", 0.7);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), { add: [{ sid: 4 }] })!;
    expect(t1).toEqual(formationLayout(seats([...HQ, ...W(3, 4)])));
  });
  it("좌열 이상 위치(좌열이 위아래 분할 속) → 표준 배치로 폴백", () => {
    const t0 = S(S(P(1), P(2), "col", 0.8), P(3), "col", 0.5);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), { add: [{ sid: 4 }] })!;
    expect(t1).toEqual(formationLayout(seats([...HQ, ...W(3, 4)])));
  });
  it("master·cso 가 좌우로 나란한 저장 배치(옛 판·창 옮기기) → 좌열로 보지 않고 표준 배치(헤드리스 c18 전체 실행 적발)", () => {
    const t0 = S(S(P(1), P(2), "row", 0.5), P(3), "row", 0.5);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), { add: [{ sid: 4 }] })!;
    expect(t1).toEqual(formationLayout(seats([...HQ, ...W(3, 4)])));
    // 위아래가 뒤바뀐(cso 위) 좌열은 사람이 만든 모양이다 — 그대로 보존
    const swapped = S(P(2), P(1), "col", 0.3);
    const t2 = autoArrange(S(swapped, P(3), "row", 0.4), roles([...HQ, ...W(3, 4)]), { add: [{ sid: 4 }] })!;
    expect((t2 as any).a).toBe(swapped);
    expect(leftW(t2)).toBeCloseTo(0.4, 12);
  });
  it("mode=standard(정렬 단추) = 종전 formationLayout 과 같은 결과", () => {
    const t0 = S(S(P(1), P(2), "col", 0.6), S(P(3), P(4), "row", 0.3), "row", 0.4);
    const r = roles([...HQ, ...W(3, 4)]);
    expect(autoArrange(t0, r, {}, "standard")).toEqual(formationLayout(seats([...HQ, ...W(3, 4)])));
  });
  it("기본 정책 = auto(D1 = C) · 허용 오차 0.01", () => {
    expect(RULE_TOL).toBe(0.01);
  });
});

describe("D1 = C(master 판정 2026-09-25 master#c443981e) — 규칙값이면 다시 재고 사람이 끈 값이면 보존", () => {
  const r12 = roles([...HQ, ...W(...Array.from({ length: 12 }, (_, i) => 10 + i))]);
  it("첫 부팅 워커 1→7 한 대씩 입양 → 좌열 1/2 → 1/3(A 였으면 1/2 영구 고정)", () => {
    let t: LayoutNode | null = formationLayout(seats(HQ));
    const got: number[] = [];
    for (let k = 0; k < 7; k++) {
      t = autoArrange(t, r12, { add: [{ sid: 10 + k }] })!;
      got.push(leftW(t));
      evenRest(t, Array.from({ length: k + 1 }, (_, i) => 10 + i));
    }
    expect(got[0]).toBeCloseTo(1 / 2, 12);
    for (let k = 1; k < 7; k++) expect(got[k]).toBeCloseTo(leftColumnShare(k + 1), 12);
    expect(got[6]).toBeCloseTo(1 / 3, 12);
  });
  it("사람이 0.40 으로 끈 뒤 열기·닫기 반복 → 0.40 유지 · 위아래 비율 유지", () => {
    const left = S(P(1), P(2), "col", 0.65);
    let t: LayoutNode = S(left, S(P(10), P(11)), "row", 0.4);
    const ops: { add?: { sid: number }[]; remove?: number[] }[] = [
      { add: [{ sid: 12 }] }, { add: [{ sid: 13 }] }, { remove: [10] }, { add: [{ sid: 14 }] }, { remove: [12, 13] }, { remove: [11] },
    ];
    for (const op of ops) {
      t = autoArrange(t, r12, op)!;
      expect(leftW(t)).toBeCloseTo(0.4, 12);
      expect((t as any).a).toBe(left);
    }
    expect(sids(t)).toEqual([1, 2, 14]);
  });
  it("워커가 0 이 됐다가 다시 생기면 표준 몫(좌열이 화면 전체였던 순간 몫 정보가 없다)", () => {
    let t: LayoutNode = S(S(P(1), P(2), "col", 0.8), P(10), "row", 0.6);
    t = autoArrange(t, r12, { remove: [10] })!;
    t = autoArrange(t, r12, { add: [{ sid: 11 }] })!;
    expect(leftW(t)).toBeCloseTo(leftColumnShare(1), 12);
  });
  for (const [d, rule] of [[+RULE_TOL * 0.9, true], [-RULE_TOL * 0.9, true], [+RULE_TOL * 1.5, false], [-RULE_TOL * 1.5, false]] as const) {
    it(`경계: 직전 규칙값(워커 1 = 1/2) ${d >= 0 ? "+" : ""}${d.toFixed(4)} → ${rule ? "규칙값으로 다시" : "사람 값 보존"}`, () => {
      const v = leftColumnShare(1) + d;
      const t0 = S(S(P(1), P(2), "col", 0.8), P(10), "row", v);
      const t1 = autoArrange(t0, r12, { add: [{ sid: 11 }] })!;
      expect(leftW(t1)).toBeCloseTo(rule ? leftColumnShare(2) : v, 12);
    });
  }
  it("닫기로 워커 수가 줄어도 규칙값 따라감(1/3 → 1/2)", () => {
    const t0 = formationLayout(seats([...HQ, ...W(10, 11)]))!;
    const t1 = autoArrange(t0, r12, { remove: [11] })!;
    expect(leftW(t1)).toBeCloseTo(leftColumnShare(1), 12);
  });
});

describe("⑵ 나머지 좌석 한 줄 균등(오너 ②)", () => {
  for (const n of [0, 1, 2, 7, 12]) {
    const ws = Array.from({ length: n }, (_, i) => 10 + i);
    it(`HQ 있음 · 워커 ${n}`, () => {
      const r = roles([...HQ, ...W(...ws)]);
      const t = autoArrange(formationLayout(seats(HQ)), r, { add: ws.map((sid) => ({ sid })) })!;
      expect(sids(t)).toEqual([1, 2, ...ws]);
      if (n) { evenRest(t, ws); expect(leftW(t)).toBeCloseTo(leftColumnShare(n), 12); }
      expect(hasCol(t)).toBe(true); // 좌열 위아래만
      const shW = shares(t);
      const total = [1, ...ws].reduce((s, k) => s + shW.get(k)!, 0);
      expect(total).toBeCloseTo(1, 12);
    });
    it(`HQ 없음 · 워커 ${n}`, () => {
      const t = autoArrange(null, roles(W(...ws)), { add: ws.map((sid) => ({ sid })) });
      if (!n) { expect(t).toBeNull(); return; }
      expect(sids(t)).toEqual(ws);
      expect(hasCol(t)).toBe(false);
      evenRest(t!, ws);
    });
  }
  it("HQ 한쪽만(master) · 워커 2", () => {
    const t = autoArrange(null, roles([[1, "master"], ...W(3, 4)]), { add: [{ sid: 1 }, { sid: 3 }, { sid: 4 }] })!;
    expect((t as any).a).toEqual(P(1));
    expect(leftW(t)).toBeCloseTo(leftColumnShare(2), 12);
    evenRest(t, [3, 4]);
  });
  it("HQ 한쪽만(cso) · 워커 1", () => {
    const t = autoArrange(null, roles([[2, "cso"], ...W(3)]), { add: [{ sid: 3 }, { sid: 2 }] })!;
    expect((t as any).a).toEqual(P(2));
    expect(sids(t)).toEqual([2, 3]);
  });
  it("사람이 위아래로 나눈 워커 칸 → 다음 열기 때 한 줄로 편다(순회 순서 보존)", () => {
    const t0 = S(S(P(3), P(4), "col", 0.7), S(P(5), P(6), "col"), "row", 0.5);
    const t1 = autoArrange(t0, roles(W(3, 4, 5, 6, 7)), { add: [{ sid: 7 }] })!;
    expect(hasCol(t1)).toBe(false);
    expect(sids(t1)).toEqual([3, 4, 5, 6, 7]);
    evenRest(t1, [3, 4, 5, 6, 7]);
  });
  it("분할 = 대상 바로 다음 순서에 선다", () => {
    const t0 = formationLayout(seats(W(3, 4, 5)))!;
    const t1 = autoArrange(t0, roles(W(3, 4, 5)), { add: [{ sid: 9, after: 3 }] })!;
    expect(sids(t1)).toEqual([3, 9, 4, 5]);
    evenRest(t1, [3, 9, 4, 5]);
  });
  it("역할 모르는 셸·끝난 좌석(역할 없음)은 워커 줄에 선다", () => {
    const t = autoArrange(null, roles([...HQ]), { add: [{ sid: 1 }, { sid: 2 }, { sid: 50 }] })!;
    expect(sids(t)).toEqual([1, 2, 50]);
    expect((t as any).b).toEqual(P(50));
  });
  it("서수판 역할(master-2 · cso-3)도 계열로 접는다 · 둘째 master 는 워커 줄", () => {
    const t = autoArrange(null, roles([[5, "master-2"], [6, "cso-3"], [7, "master"], ...W(8)]), {
      add: [5, 6, 7, 8].map((sid) => ({ sid })),
    })!;
    expect((t as any).a.a).toEqual(P(5));
    expect((t as any).a.b).toEqual(P(6));
    expect(sids((t as any).b)).toEqual([7, 8]);
  });
  it("같은 트리에 변화 없이 다시 불러도 같다(멱등)", () => {
    const r = roles([...HQ, ...W(3, 4, 5)]);
    const t1 = autoArrange(formationLayout(seats([...HQ, ...W(3)])), r, { add: [{ sid: 4 }, { sid: 5 }] })!;
    expect(autoArrange(t1, r)).toEqual(t1);
  });
});

describe("⑶ 좌석 집합 보존(속성 시험)", () => {
  // 결정론 난수(mulberry32) — 실패하면 같은 시드로 재현된다.
  function rng(seed: number) {
    return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function randTree(r: () => number, ids: number[]): LayoutNode {
    if (ids.length === 1) return P(ids[0]);
    const k = 1 + Math.floor(r() * (ids.length - 1));
    return S(randTree(r, ids.slice(0, k)), randTree(r, ids.slice(k)), r() < 0.5 ? "row" : "col", r() < 0.3 ? undefined : 0.05 + r() * 0.9);
  }
  const ROLE_POOL = ["master", "cso", "worker", "worker-2", "reviewer", null, "master-2", "cso-2"];
  it("무작위 트리 3000개 × 열기·닫기 — sid 집합 = (입력 − remove) ∪ add · 중복 0 · 가로 몫 합 = 1", () => {
    const r = rng(20260925);
    for (let iter = 0; iter < 3000; iter++) {
      const n = Math.floor(r() * 14);
      const ids = Array.from({ length: n }, (_, i) => 100 + i);
      const tree = n ? randTree(r, ids) : null;
      const rm = new Map<number, string | null>();
      for (const s of [...ids, 900, 901, 902]) rm.set(s, ROLE_POOL[Math.floor(r() * ROLE_POOL.length)]);
      const remove = ids.filter(() => r() < 0.25);
      const add = [900, 901, 902].filter(() => r() < 0.4).map((sid) => ({ sid, after: r() < 0.5 && ids.length ? ids[Math.floor(r() * ids.length)] : undefined }));
      for (const mode of ["auto", "standard"] as const) {
        const out = autoArrange(tree, rm, { add, remove }, mode);
        const want = new Set([...ids.filter((s) => !remove.includes(s)), ...add.map((a) => a.sid)]);
        const got = sids(out);
        expect(new Set(got)).toEqual(want);
        expect(got.length).toBe(want.size);
        if (out) {
          const tot = [...area(out).values()].reduce((a, b) => a + b, 0);
          expect(tot).toBeCloseTo(1, 9);
          // 좌열 밖에는 세로 분할이 없다 · 좌열 좌석이 아닌 칸은 모두 같은 가로 몫
          const lf = new Set(got.filter((s) => { const f = String(rm.get(s) ?? ""); return f === "master" || f.startsWith("master-") || f === "cso" || f.startsWith("cso-"); }));
          const sh = shares(out);
          const leftPicked = [got.find((s) => /^master(-|$)/.test(String(rm.get(s) ?? ""))), got.find((s) => /^cso(-|$)/.test(String(rm.get(s) ?? "")))].filter((x) => x !== undefined);
          const restW = got.filter((s) => !leftPicked.includes(s)).map((s) => sh.get(s)!);
          for (const x of restW) expect(x).toBeCloseTo(restW[0], 9);
          // 좌열 두 칸은 언제나 위아래(가로 몫이 같다) — 좌우로 나란히 남지 않는다
          if (leftPicked.length === 2) expect(sh.get(leftPicked[0]!)!).toBeCloseTo(sh.get(leftPicked[1]!)!, 9);
          void lf;
        }
      }
    }
  });
});

// ── 호출부 핀 — 열기·닫기 전 경로가 arrangeWs 한 곳을 지난다(브리프 3) ──────────────────────────
import { readFileSync } from "node:fs";
const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const fnBody = (head: string, end: string) => {
  const i = main.indexOf(head);
  expect(i).toBeGreaterThan(-1);
  const j = main.indexOf(end, i + head.length);
  expect(j).toBeGreaterThan(i);
  return main.slice(i, j);
};
// 주석을 걷어낸 선언만 본다(설명 주석이 낱말을 품어 거짓 초록/적색을 내지 않게).
const code = (s: string) => s.replace(/\/\/[^\n]*/g, "");

describe("호출부 — 열기·닫기 9경로 + 정렬 단추가 같은 함수", () => {
  it("단일 입구 arrangeWs = autoArrange 한 줄", () => {
    const b = code(fnBody("function arrangeWs(", "\n}\n"));
    expect(b).toContain('ws.tree = autoArrange(ws.tree, arrangeRolesBySocket.get(ws.socket ?? "") ?? new Map(), change, mode);');
  });
  const paths: [string, string, string, string][] = [
    ["자동 입양(3초 틱)", "async function refreshPaneTitles() {", "\n}\n", "arrangeWs(ws, { add: adoptAdds.get(ws) ?? [] });"],
    ["자리표 회수(틱 안)", "── ③ 빈 자리표 회수", "const masterSids", "arrangeWs(ws, { remove: [sid] });"],
    ["새 창", "async function actionNew() {", "\n}\n", "arrangeWs(ws, { add: [{ sid }] });"],
    ["분할", "async function actionSplit(", "\n}\n", "arrangeWs(ws, { add: [{ sid, after: target }] });"],
    ["닫기(Close·⌘W·팔레트)", "async function actionClose() {", "\n}\n", "arrangeWs(ws, { remove: [sid] });"],
    ["창 머리 ×", 'closeBtn.dataset.arm !== "1"', "header.append(", "arrangeWs(ws, { remove: [sid] });"],
    ["외부 닫힘·유령·스윕(detachPane)", "function detachPane(", "\n}\n", "arrangeWs(ws, { remove: [sid] });"],
    ["복원 때 죽은 좌석 정리", "const dead = deadLiveSids(", "workspaces = workspaces.filter", "if (dead.length) arrangeWs(ws, { remove: dead });"],
    ["복원 입양", "const restoreAdds: { sid: number }[] = [];", "plain 셸 1개로 충전", "if (restoreAdds.length) arrangeWs(ws, { add: restoreAdds });"],
    ["정렬 단추·팔레트 패널 균등화", "async function actionEqualize() {", "\n}\n", '"standard");'],
  ];
  for (const [name, head, end, call] of paths) {
    it(`${name} → arrangeWs · 트리를 손으로 감싸거나 잘라내지 않는다`, () => {
      const b = code(fnBody(head, end));
      expect(b).toContain(call);
      expect(b).not.toContain("replaceNode(");
      expect(/a: ws\.tree, b:/.test(b)).toBe(false);
    });
  }
  it("replaceNode 호출은 창 옮기기 두 함수(movePane·transferCrossDept)에만 남는다 — 열기·닫기 경로 0", () => {
    const calls = [...code(main).matchAll(/replaceNode\(/g)].map((m) => m.index!);
    const inside = (head: string) => {
      const i = code(main).indexOf(head);
      const j = code(main).indexOf("\n}\n", i);
      return (k: number) => k > i && k < j;
    };
    const def = inside("function replaceNode(");
    const mv = inside("function movePane(");
    const tx = inside("async function transferCrossDept(");
    const stray = calls.filter((k) => !def(k) && !mv(k) && !tx(k));
    expect(stray).toEqual([]);
    expect(calls.filter((k) => mv(k) || tx(k)).length).toBeGreaterThan(0); // 대상 밖 경로는 그대로(무접촉)
  });
  it("열기 경로에 0.5 래퍼(`a: ws.tree`)가 한 곳도 없다", () => {
    expect(/a: ws\.tree\b/.test(code(main))).toBe(false);
  });
  it("역할 표는 틱·복원·정렬 세 곳에서 채운다(끝난 좌석 포함)", () => {
    const c = code(main);
    expect((c.match(/rememberRoles\(/g) || []).length).toBe(4); // 정의 1 + 호출 3
    expect(c).toContain("rememberRoles(sk, r.surfaces);");
    expect(c).toContain("rememberRoles(ws.socket, r.surfaces);");
  });
});
