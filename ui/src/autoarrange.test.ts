// autoarrange.test.ts — 창 열기·닫기 자동 좌우 균등(TICKET=v116-auto-equalize · 오너 지시 2026-09-25 05:2x).
//
// ★이 스위트가 재야 하는 것:
//   ⑴좌열(master·cso)의 화면 몫과 위아래 비율이 열기·닫기를 지나도 **입력 트리 값 그대로**인가(오너 ①).
//   ⑵그 밖의 좌석은 「기둥」(칸 하나 또는 위아래로 쌓인 묶음)끼리만 좌우 균등인가 — 사람이 위아래로 나눈 것은 그대로
//     (v2 · 박사님 결정 09-25 14:1x 「사용자가 임의로 세로로 정렬한 것들도 그대로 유지 · 오직 워커 페인들의 좌우폭만 균등」).
//   ⑶좌석 집합 보존 — 결과 sid 집합 = (입력 − remove) ∪ add. 빠지면 「살아 있는데 안 보이는 좌석」(4군 ④).
//   ⑷재현된 세 결함(R1 HQ 첫 배치 뒤 재배치 멈춤 · R2 닫기 형제 독차지 · R3 새 창 0.5)이 이 함수로 사라지는가.
import { describe, it, expect } from "bun:test";
import { autoArrange, formationLayout, defaultLeftShare, LEFT_SHARE_DEFAULT, LEFT_MIN_COLS, LEFT_SHARE_MAX, OLD_DEFAULT_SHARES, MASTER_CSO_RATIO, RULE_TOL, DRAG_MIN, DRAG_MAX, type LayoutNode, type Seat } from "./formation";
const leftColumnShare = (_n: number) => LEFT_SHARE_DEFAULT; // (박사님 결정 14:5x) 옛 규칙 함수 자리 — 기본 폭은 워커 수와 무관한 상수

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
// (v2) 기둥 = 루트를 가로(row) 분할로 끝까지 펼친 단위(칸 하나 또는 위아래 묶음). 시험 쪽 독립 구현(모듈 것을 빌리지 않는다).
const units = (n: LayoutNode | null, o: LayoutNode[] = []): LayoutNode[] => {
  if (!n) return o;
  if (n.type === "split" && n.dir === "row") { units(n.a, o); units(n.b, o); } else o.push(n);
  return o;
};
const unitWidths = (n: LayoutNode | null, w = 1, o: number[] = []): number[] => {
  if (!n) return o;
  if (n.type === "split" && n.dir === "row") { const r = n.ratio ?? 0.5; unitWidths(n.a, w * r, o); unitWidths(n.b, w * (1 - r), o); } else o.push(w);
  return o;
};
const hasNode = (n: LayoutNode | null, t: LayoutNode): boolean => !!n && (n === t || (n.type === "split" && (hasNode(n.a, t) || hasNode(n.b, t))));
// 좌열(첫 기둥)을 뺀 워커 기둥 폭이 모두 같은가 — HQ 없는 트리는 skipLeft=false.
function evenUnits(t: LayoutNode, skipLeft = false) {
  const w = unitWidths(t).slice(skipLeft ? 1 : 0);
  for (const x of w) expect(x).toBeCloseTo(w[0], 12);
}
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
  // ★v2(박사님 결정 09-25 14:1x · DESIGN-v2 처방표 4행)로 변경: 좌열 좌석이 워커와 한 기둥에 섞인 모양은 사람이 만든 위아래 나눔이다 —
  //   v1 은 표준으로 전부 다시 짜 그 나눔을 지웠다. v2 는 맞출 수 없으니 **무정렬**(새 칸 = 루트 오른쪽 1/(기둥+1) · 나머지 무접촉).
  it("좌열 이상 위치(좌열 안에 워커가 끼어 있음) → 무정렬 · 새 칸만 오른쪽(v2)", () => {
    const t0 = S(S(P(1), P(3), "col", 0.5), S(P(2), P(4)), "row", 0.5);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), { add: [{ sid: 5 }] })!;
    expect(t1).toEqual(S(t0, P(5), "row", 3 / 4));
    expect((t1 as any).a).toBe(t0);
  });
  it("좌열 이상 위치(master·cso 가 세로 열 안에 워커를 품음 · 그 열 몫 0.6) → 무정렬(v2)", () => {
    const t0 = S(S(P(1), S(P(3), P(2), "row"), "col", 0.7), P(4), "row", 0.6);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4, 5)]), { add: [{ sid: 5 }] })!;
    expect(t1).toEqual(S(t0, P(5), "row", 2 / 3));
  });
  it("좌열 이상 위치(좌열이 위아래 분할 속 · 루트가 위아래) → 무정렬 · 세로 비율을 가로 몫으로 오독하지 않는다(v2)", () => {
    const t0 = S(S(P(1), P(2), "col", 0.6), P(3), "col", 0.7);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), { add: [{ sid: 4 }] })!;
    expect(t1).toEqual(S(t0, P(4), "row", 1 / 2));
  });
  it("좌열 이상 위치(좌열이 위아래 분할 속) → 무정렬 · 닫기 = 그 자리 접힘(v2)", () => {
    const t0 = S(S(P(1), P(2), "col", 0.8), S(P(3), P(4), "row", 0.3), "col", 0.5);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), { remove: [3] })!;
    expect(t1).toEqual(S(S(P(1), P(2), "col", 0.8), P(4), "col", 0.5));
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
  it("기본 정책 = auto · 옛 기본값 허용 오차 0.01 · 끌기 범위 0.15~0.85", () => {
    expect(RULE_TOL).toBe(0.01);
    expect([DRAG_MIN, DRAG_MAX]).toEqual([0.15, 0.85]);
    const t0 = S(S(P(1), P(2), "col", 0.7), S(P(3), P(4)), "row", 0.42);
    const r = roles([...HQ, ...W(3, 4, 5)]);
    expect(autoArrange(t0, r, { add: [{ sid: 5 }] })).toEqual(autoArrange(t0, r, { add: [{ sid: 5 }] }, "auto"));
    expect(autoArrange(t0, r, { add: [{ sid: 5 }] })).not.toEqual(autoArrange(t0, r, { add: [{ sid: 5 }] }, "standard"));
  });
});

describe("Opus 적대 1R 봉합 — F1 깊은 길 몫 · F4 좌열 비율", () => {
  const r = roles([...HQ, ...W(3, 4, 5, 6)]);
  it("F1 R1 잔재 트리(옛 입양 0.5 감싸기 · 좌열 0.125) → 사람 값으로 보지 않고 기본 몫 · 위아래 비율은 보존", () => {
    const old = S(formationLayout(seats([...HQ, ...W(3)]))!, P(4), "row", 0.5);
    expect(leftW(old)).toBeCloseTo(0.125, 12);
    const t = autoArrange(old, r, { add: [{ sid: 5 }] })!;
    expect(leftW(t)).toBeCloseTo(leftColumnShare(3), 12);
    evenRest(t, [3, 4, 5]);
    const a = area(t);
    expect(a.get(1)! / a.get(2)!).toBeCloseTo(4, 9);
  });
  it("F1 두 번 감싼 잔재(0.125)도 표준 몫", () => {
    const old = S(S(formationLayout(seats([...HQ, ...W(3)]))!, P(4), "row", 0.5), P(5), "row", 0.5);
    expect(leftW(autoArrange(old, r, { remove: [5] })!)).toBeCloseTo(leftColumnShare(2), 12);
  });
  it("F1 창 옮기기가 0.5 로 감싼 뒤(좌열 0.125) → 다음 열기·닫기에 기본 몫", () => {
    const moved = S(formationLayout(seats([...HQ, ...W(3, 4)]))!, P(5), "row", 0.5);
    expect(leftW(moved)).toBeCloseTo(0.125, 12);
    expect(leftW(autoArrange(moved, r, { add: [{ sid: 6 }] })!)).toBeCloseTo(leftColumnShare(4), 12);
    expect(leftW(autoArrange(moved, r, { remove: [3] })!)).toBeCloseTo(leftColumnShare(2), 12);
  });
  for (const [v, human] of [[DRAG_MIN, true], [DRAG_MAX, true], [DRAG_MIN - 0.01, false], [DRAG_MAX + 0.01, false]] as const) {
    it(`F1 끌기 범위 경계: 좌열 몫 ${v.toFixed(2)} → ${human ? "사람 값 보존" : "표준 몫"}`, () => {
      const t0 = S(S(P(1), P(2), "col", 0.8), S(P(3), P(4)), "row", v);
      expect(leftW(autoArrange(t0, r, { add: [{ sid: 5 }] })!)).toBeCloseTo(human ? v : leftColumnShare(3), 12);
    });
  }
  it("F4 첫 master 가 닫히고 master-2 가 올라와도 사람이 바꾼 위아래 비율(0.6) 보존", () => {
    const rr = roles([[1, "master"], [2, "cso"], [7, "master-2"], ...W(3)]);
    const t0 = S(S(P(1), P(2), "col", 0.6), S(P(7), P(3)), "row", 0.4);
    const t1 = autoArrange(t0, rr, { remove: [1] })!;
    expect((t1 as any).a).toEqual({ type: "split", dir: "col", ratio: 0.6, a: P(7), b: P(2) });
    expect(leftW(t1)).toBeCloseTo(0.4, 12);
  });
  it("F4 윗칸 역할이 master 가 아니어도(cso 만 아니면) master-2 승격 때 위아래 비율 보존 · 윗칸이 cso 면 표준 4:1", () => {
    // (유령 수렴으로 목록에서 빠진 옛 master 의 역할은 main.ts rememberRoles 가 화면에 남은 동안 이어서 기억한다 — 아래 호출부 핀)
    const rr = roles([[1, "master"], [2, "cso"], [7, "master-2"], ...W(3)]);
    const t0 = S(S(P(1), P(2), "col", 0.6), S(P(7), P(3)), "row", 0.4);
    expect((autoArrange(t0, rr, { remove: [1] })! as any).a).toEqual({ type: "split", dir: "col", ratio: 0.6, a: P(7), b: P(2) });
    const swapped = S(S(P(2), P(1), "col", 0.3), S(P(7), P(3)), "row", 0.4); // cso 가 위에 있던 좌열
    const rr2 = roles([[1, "master"], [2, "cso"], [7, "master-2"], ...W(3)]);
    expect((autoArrange(swapped, rr2, { remove: [1] })! as any).a).toEqual({ type: "split", dir: "col", ratio: MASTER_CSO_RATIO, a: P(7), b: P(2) });
  });
  for (const bad of [NaN, 1, 0, -0.2]) {
    it(`F4 손상된 좌열 위아래 비율(${bad}) → 좌열로 보지 않고 표준`, () => {
      const t0 = S(S(P(1), P(2), "col", bad), S(P(3), P(4)), "row", 0.4);
      const t1 = autoArrange(t0, r, { add: [{ sid: 5 }] })!;
      expect(t1).toEqual(formationLayout(seats([...HQ, ...W(3, 4, 5)])));
    });
  }
});

// ★박사님 결정 09-25 14:5x(master#db159bcf) + master#73a7390d 로 변경: 옛 D1 = C(「직전 워커 수의 규칙값이면 새 워커 수로 다시」)
//   폐기 — 좌열 폭은 **다시 재지 않는다**. 기본 폭 = 창의 25% · 노트북이면 글자 90칸 · 상한 50%(defaultLeftShare) + leftAuto 표지.
describe("박사님 결정 14:5x — 좌열 가로 폭은 균등 정렬에서 뺀다 · 기본 = 창의 25%(노트북 90칸 · 상한 50%)", () => {
  const r12 = roles([...HQ, ...W(...Array.from({ length: 12 }, (_, i) => 10 + i))]);
  const ws = (...ids: number[]) => ids;
  it("defaultLeftShare: 넓은 창 3440px = 25% · 노트북 1512px = 90칸 몫 · 아주 좁은 창 = 50% 상한 · 모르면 25%", () => {
    const cell = 7.8; // 13px 고정폭 글꼴 한 칸
    expect(defaultLeftShare(3440, cell)).toBe(0.25);
    expect(defaultLeftShare(1512, cell)).toBeCloseTo((LEFT_MIN_COLS * cell) / 1512, 12);
    expect(defaultLeftShare(1512, cell) * 1512 / cell).toBeCloseTo(90, 9);
    expect(defaultLeftShare(900, cell)).toBe(0.5);
    for (const [w, c] of [[0, cell], [NaN, cell], [1512, 0], [1512, NaN], [-5, cell]]) expect(defaultLeftShare(w, c)).toBe(0.25);
    expect([LEFT_SHARE_DEFAULT, LEFT_MIN_COLS, LEFT_SHARE_MAX]).toEqual([0.25, 90, 0.5]);
    expect(OLD_DEFAULT_SHARES).toEqual([1 / 2, 1 / 3]);
  });
  it("기본 폭은 워커 0→1→2→5 열기·닫기 내내 그대로(25%) · 표지 유지", () => {
    let t: LayoutNode | null = autoArrange(null, r12, { add: [{ sid: 1 }, { sid: 2 }] });
    for (const add of [ws(10), ws(11), ws(12, 13, 14)]) {
      t = autoArrange(t, r12, { add: add.map((sid) => ({ sid })) })!;
      expect(leftW(t)).toBe(0.25);
      expect((t as any).leftAuto).toBe(true);
    }
    for (const rm of [[12], [10, 11], [13]]) {
      t = autoArrange(t, r12, { remove: rm })!;
      expect(leftW(t)).toBe(0.25);
    }
    expect(sids(t)).toEqual([1, 2, 14]);
  });
  it("입양 경로(트리 없음·좌열 먼저·워커 나중)도 기본 폭 · 창 폭이 다르면 그 폭의 기본값", () => {
    const d = defaultLeftShare(1512, 7.8);
    let t: LayoutNode | null = null;
    for (const sid of [1, 10, 2, 11]) t = autoArrange(t, r12, { add: [{ sid }] }, "auto", d);
    expect(leftW(t!)).toBeCloseTo(d, 12);
    expect((t as any).leftAuto).toBe(true);
  });
  it("창 크기가 바뀌면(기본값 d → d') 표지 있는 트리만 새 기본값 · 사람이 끈 0.40(표지 없음)은 그대로", () => {
    const a = autoArrange(null, r12, { add: [1, 2, 10, 11].map((sid) => ({ sid })) }, "auto", 0.25)!;
    expect(leftW(autoArrange(a, r12, {}, "auto", 0.46)!)).toBeCloseTo(0.46, 12);
    const human = S(S(P(1), P(2), "col", 0.65), S(P(10), P(11)), "row", 0.4);
    const h1 = autoArrange(human, r12, { add: [{ sid: 12 }] }, "auto", 0.46)!;
    expect(leftW(h1)).toBeCloseTo(0.4, 12);
    expect((h1 as any).leftAuto).toBeUndefined();
    expect(autoArrange(h1, r12, {}, "auto", 0.3)).toEqual(h1); // 창 크기 변경(재배치 호출) 뒤에도 그대로
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
  it("정렬 단추 = 기본 폭 복귀(사람 0.40 → d) + 4:1 + 표지", () => {
    const t0 = S(S(P(1), P(2), "col", 0.65), S(P(10), P(11)), "row", 0.4);
    const t1 = autoArrange(t0, r12, {}, "standard", 0.3)!;
    expect(leftW(t1)).toBeCloseTo(0.3, 12);
    expect((t1 as any).leftAuto).toBe(true);
    expect((t1 as any).a.ratio).toBe(MASTER_CSO_RATIO);
  });
  it("워커가 0 이 됐다가 다시 생기면 기본 몫(좌열이 화면 전체였던 순간 몫 정보가 없다)", () => {
    let t: LayoutNode = S(S(P(1), P(2), "col", 0.8), P(10), "row", 0.6);
    t = autoArrange(t, r12, { remove: [10] })!;
    t = autoArrange(t, r12, { add: [{ sid: 11 }] })!;
    expect(leftW(t)).toBe(0.25);
  });
  for (const old of [1 / 2, 1 / 3]) for (const [d, migrate] of [[0, true], [+RULE_TOL * 0.9, true], [-RULE_TOL * 0.9, true], [+RULE_TOL * 1.5, false], [-RULE_TOL * 1.5, false]] as const) {
    it(`옛 기본값(1.1.5 이하) ${old.toFixed(3)} ${d >= 0 ? "+" : ""}${d.toFixed(4)} · 표지 없음 → ${migrate ? "기본을 쓰던 것 → 새 기본으로" : "사람 값 보존"}`, () => {
      const v = old + d;
      const t0 = S(S(P(1), P(2), "col", 0.8), S(P(10), P(11)), "row", v);
      const t1 = autoArrange(t0, r12, { add: [{ sid: 12 }] }, "auto", 0.27)!;
      expect(leftW(t1)).toBeCloseTo(migrate ? 0.27 : v, 12);
      expect((t1 as any).leftAuto).toBe(migrate ? true : undefined);
    });
  }
});

describe("⑵ 나머지 좌석 한 줄 균등(오너 ②)", () => {
  for (const n of [0, 1, 2, 7, 12]) {
    const ws = Array.from({ length: n }, (_, i) => 10 + i);
    it(`HQ 있음 · 워커 ${n}`, () => {
      const r = roles([...HQ, ...W(...ws)]);
      const t = autoArrange(formationLayout(seats(HQ)), r, { add: ws.map((sid) => ({ sid })) })!;
      expect(sids(t)).toEqual([1, 2, ...ws]);
      if (n) { evenRest(t, ws); expect(leftW(t)).toBe(LEFT_SHARE_DEFAULT); }
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
  // ★v2(박사님 결정 09-25 14:1x)로 변경: v1 은 「한 줄로 편다」였다 — 이제 위아래 묶음(기둥)은 그대로, 기둥끼리만 균등.
  it("사람이 위아래로 나눈 워커 칸 → 다음 열기 때도 그대로 · 기둥끼리 균등(v2)", () => {
    const c1 = S(P(3), P(4), "col", 0.7), c2 = S(P(5), P(6), "col");
    const t0 = S(c1, c2, "row", 0.5);
    const t1 = autoArrange(t0, roles(W(3, 4, 5, 6, 7)), { add: [{ sid: 7 }] })!;
    expect(units(t1)).toEqual([c1, c2, P(7)]);
    expect(units(t1)[0]).toBe(c1);
    expect(units(t1)[1]).toBe(c2);
    evenUnits(t1);
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

describe("v2 기둥 — 박사님 결정 09-25 14:1x 「master:cso 4:1 유지 · 사람이 세로로 나눈 것 유지 · 오직 워커 좌우폭만 균등」", () => {
  const LEFT = () => S(P(1), P(2), "col", MASTER_CSO_RATIO);
  it("사양1 좌열 서브트리(위아래 4:1)는 같은 객체 · 사람이 끈 좌열 몫 0.4 보존 · 워커 쪽에 위아래 기둥이 있어도", () => {
    const left = LEFT(), c = S(P(3), P(4), "col", 0.7);
    const t0 = S(left, S(c, P(5)), "row", 0.4);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4, 5, 6)]), { add: [{ sid: 6 }] })!;
    expect((t1 as any).a).toBe(left);
    expect(leftW(t1)).toBeCloseTo(0.4, 12);
    expect(units(t1).slice(1)).toEqual([c, P(5), P(6)]);
    evenUnits(t1, true);
  });
  it("사양2 워커 위아래 기둥은 같은 객체로(안의 비율 0.7 그대로) · 기둥끼리만 균등 — 본부 있음", () => {
    const c = S(P(3), P(4), "col", 0.7);
    const t0 = S(LEFT(), S(c, P(5)), "row", leftColumnShare(2));
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4, 5, 6)]), { add: [{ sid: 6 }] })!;
    expect(units(t1)[1]).toBe(c);
    expect(unitWidths(t1).slice(1).length).toBe(3);
    evenUnits(t1, true);
    expect(leftW(t1)).toBeCloseTo(leftColumnShare(3), 12); // 규칙값(손 안 탐) → 새 기둥 수의 규칙값
  });
  it("사양2 기둥 안에 가로 분할이 섞인 사람 배치(col(row(3,4),5))도 통째 보존", () => {
    const c = S(S(P(3), P(4), "row", 0.3), P(5), "col", 0.6);
    const t1 = autoArrange(S(c, P(6)), roles(W(3, 4, 5, 6, 7)), { add: [{ sid: 7 }] })!;
    expect(units(t1)[0]).toBe(c);
    expect(units(t1).length).toBe(3);
    evenUnits(t1);
  });
  it("사양3 새 창 after = 기둥 안 칸 → 그 기둥 바로 오른쪽 새 기둥 · after 없음 → 맨 오른쪽 · after = 좌열 → 워커 맨 왼쪽", () => {
    const c = S(P(3), P(4), "col", 0.7);
    const t0 = S(c, P(5));
    const r = roles(W(3, 4, 5, 9));
    expect(units(autoArrange(t0, r, { add: [{ sid: 9, after: 4 }] }))).toEqual([c, P(9), P(5)]);
    expect(units(autoArrange(t0, r, { add: [{ sid: 9, after: 3 }] }))).toEqual([c, P(9), P(5)]);
    expect(units(autoArrange(t0, r, { add: [{ sid: 9, after: 5 }] }))).toEqual([c, P(5), P(9)]);
    expect(units(autoArrange(t0, r, { add: [{ sid: 9 }] }))).toEqual([c, P(5), P(9)]);
    expect(units(autoArrange(t0, r, { add: [{ sid: 9, after: 77 }] }))).toEqual([c, P(5), P(9)]);
    const h = S(LEFT(), t0, "row", leftColumnShare(2));
    const t2 = autoArrange(h, roles([...HQ, ...W(3, 4, 5, 9)]), { add: [{ sid: 9, after: 1 }] })!;
    expect(units(t2).slice(1)).toEqual([P(9), c, P(5)]);
    evenUnits(t2, true);
  });
  it("사양3 세로 분할(dir col) = after 칸 바로 아래 · 같은 기둥 · 기둥 수·폭·좌열 몫 불변", () => {
    const left = LEFT();
    const t0 = S(left, P(3), "row", leftColumnShare(1));
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 9)]), { add: [{ sid: 9, after: 3, dir: "col" }] })!;
    expect(t1).toEqual(S(left, S(P(3), P(9), "col", 0.5), "row", leftColumnShare(1)));
    expect((t1 as any).a).toBe(left);
    // 기둥 안 깊은 칸 아래로도(바깥 비율 0.7 그대로)
    const c = S(P(3), P(4), "col", 0.7);
    const t2 = autoArrange(S(c, P(5)), roles(W(3, 4, 5, 9)), { add: [{ sid: 9, after: 4, dir: "col" }] })!;
    expect(units(t2)).toEqual([S(P(3), S(P(4), P(9), "col", 0.5), "col", 0.7), P(5)]);
    evenUnits(t2);
  });
  it("사양3 세로 분할 대상이 좌열이면 좌열 무접촉 → 워커 맨 왼쪽 새 기둥 · 대상 없음 → 맨 오른쪽", () => {
    const left = LEFT();
    const t0 = S(left, P(3), "row", leftColumnShare(1));
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 9)]), { add: [{ sid: 9, after: 1, dir: "col" }] })!;
    expect((t1 as any).a).toBe(left);
    expect(units(t1).slice(1)).toEqual([P(9), P(3)]);
    const t2 = autoArrange(t0, roles([...HQ, ...W(3, 9)]), { add: [{ sid: 9, after: 55, dir: "col" }] })!;
    expect(units(t2).slice(1)).toEqual([P(3), P(9)]);
  });
  it("사양4 기둥 안 칸 닫기 = 형제가 자리를 받음 · 기둥 폭·좌열 몫 불변", () => {
    const left = LEFT();
    const t0 = S(left, S(S(P(3), P(4), "col", 0.7), P(5)), "row", leftColumnShare(2));
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4, 5)]), { remove: [4] })!;
    expect(t1).toEqual(S(left, S(P(3), P(5), "row", 0.5), "row", leftColumnShare(2)));
    // 깊은 기둥 안(바깥 비율 0.6 보존)
    const deep = S(S(P(3), S(P(4), P(6), "col", 0.3), "col", 0.6), P(5));
    const t2 = autoArrange(deep, roles(W(3, 4, 5, 6)), { remove: [6] })!;
    expect(units(t2)).toEqual([S(P(3), P(4), "col", 0.6), P(5)]);
    evenUnits(t2);
  });
  it("사양4 기둥 통째로 사라지면 남은 기둥 재균등 · 남은 위아래 기둥은 같은 객체", () => {
    const c = S(P(3), P(4), "col", 0.7);
    const t0 = S(c, S(P(5), P(6)));
    const t1 = autoArrange(t0, roles(W(3, 4, 5, 6)), { remove: [5] })!;
    expect(units(t1)).toEqual([c, P(6)]);
    expect(units(t1)[0]).toBe(c);
    evenUnits(t1);
    const t2 = autoArrange(t0, roles(W(3, 4, 5, 6)), { remove: [3, 4] })!;
    expect(units(t2)).toEqual([P(5), P(6)]);
    evenUnits(t2);
  });
  it("사양4 닫힌 뒤 기둥이 가로 조각으로 남으면(col(row(3,4),5) 에서 5 닫힘) 조각을 기둥으로 편다 · 멱등", () => {
    const t0 = S(S(S(P(3), P(4), "row", 0.3), P(5), "col", 0.6), P(6));
    const r = roles(W(3, 4, 5, 6));
    const t1 = autoArrange(t0, r, { remove: [5] })!;
    expect(units(t1)).toEqual([P(3), P(4), P(6)]);
    evenUnits(t1);
    expect(autoArrange(t1, r)).toEqual(t1);
  });
  it("규칙5 좌열 몫의 워커 수 = 워커 기둥 수(세로 분할·기둥 안 닫기가 좌열 폭을 안 바꾼다) · 기둥 수 변화엔 규칙값 따라감", () => {
    const left = LEFT();
    const t0 = S(left, S(S(P(3), P(4), "col"), P(5)), "row", leftColumnShare(2));
    const r = roles([...HQ, ...W(3, 4, 5)]);
    const shut5 = autoArrange(t0, r, { remove: [5] })!; // 기둥 2 → 1 = 규칙값 1/2
    expect(leftW(shut5)).toBeCloseTo(leftColumnShare(1), 12);
    const shut4 = autoArrange(t0, r, { remove: [4] })!; // 기둥 2 → 2 = 그대로
    expect(leftW(shut4)).toBeCloseTo(leftColumnShare(2), 12);
  });
  it("규칙5 워커 1대를 세로 분할(기둥 1·좌석 2 · 좌열 1/2 그대로) 뒤 새 워커 입양 → 규칙값 1/2 을 「손 안 탄 값」으로 알아보고 1/3 로(뮤턴트 M9)", () => {
    const left = LEFT();
    const t0 = S(left, P(3), "row", leftColumnShare(1));
    const r = roles([...HQ, ...W(3, 4, 5)]);
    const t1 = autoArrange(t0, r, { add: [{ sid: 4, after: 3, dir: "col" }] })!;
    expect(leftW(t1)).toBeCloseTo(leftColumnShare(1), 12); // 세로 분할 = 기둥 수 불변 → 좌열 폭 불변
    const t2 = autoArrange(t1, r, { add: [{ sid: 5 }] })!;
    expect(leftW(t2)).toBeCloseTo(leftColumnShare(2), 12); // 좌석 수(2)로 셌다면 1/2 를 사람 값으로 오독해 고정됐다
    expect(units(t2).slice(1)).toEqual([S(P(3), P(4), "col", 0.5), P(5)]);
    evenUnits(t2, true);
  });
  it("처리표 3행: 좌열 좌석이 칸 하나 기둥으로 흩어진 트리(row 뿐 · 첫 배치) → 좌열만 표준 4:1 · 워커 위아래 기둥 보존", () => {
    const c = S(P(3), P(4), "col", 0.7);
    const t0 = S(P(1), S(P(2), c));
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 4)]), {})!;
    expect(t1).toEqual({ ...(S(S(P(1), P(2), "col", MASTER_CSO_RATIO), c, "row", LEFT_SHARE_DEFAULT) as any), leftAuto: true });
    expect((t1 as any).b).toBe(c);
  });
  it("처리표 4행: 역할이 바뀌어 cso 가 워커 기둥 안에 → 무정렬(워커를 옮기거나 펴지 않음)", () => {
    const t0 = S(P(1), S(P(3), P(2), "col", 0.6), "row", 0.5);
    const t1 = autoArrange(t0, roles([...HQ, ...W(3, 5)]), { add: [{ sid: 5 }] })!;
    expect(t1).toEqual(S(t0, P(5), "row", 2 / 3));
    // 닫기·세로 분할도 그 자리에서만
    // 섞인 워커가 닫혀 섞임이 사라지면 맞출 수 있는 모양 — 좌열만 표준 4:1(지워지는 사람 위아래 나눔 0)
    expect(autoArrange(t0, roles([...HQ, ...W(3)]), { remove: [3] })).toEqual(S(P(1), P(2), "col", MASTER_CSO_RATIO));
    expect(autoArrange(t0, roles([...HQ, ...W(3, 5)]), { add: [{ sid: 5, after: 3, dir: "col" }] })).toEqual(
      S(P(1), S(S(P(3), P(5), "col", 0.5), P(2), "col", 0.6), "row", 0.5));
  });
  it("처리표 4행: 무정렬 + 트리 없음/빈 트리에 첫 칸", () => {
    const t0 = S(S(P(1), P(3), "col"), P(2));
    expect(sids(autoArrange(t0, roles([...HQ, ...W(3)]), { remove: [1, 2, 3], add: [{ sid: 3 }] }))).toEqual([3]);
  });
  it("정렬 단추(standard)는 표준 그대로 — 사람 위아래 나눔도 편다(사람이 누르는 것)", () => {
    const t0 = S(LEFT(), S(S(P(3), P(4), "col", 0.7), P(5)), "row", 0.4);
    const r = roles([...HQ, ...W(3, 4, 5)]);
    expect(autoArrange(t0, r, {}, "standard")).toEqual(formationLayout(seats([...HQ, ...W(3, 4, 5)])));
  });
  it("멱등 — v2 결과를 변화 없이 다시 넣으면 같다(위아래 기둥 · 사람 좌열 몫)", () => {
    const r = roles([...HQ, ...W(3, 4, 5, 6)]);
    const t0 = S(S(P(1), P(2), "col", 0.65), S(S(P(3), P(4), "col", 0.7), P(5)), "row", 0.42);
    const t1 = autoArrange(t0, r, { add: [{ sid: 6, after: 3 }] })!;
    expect(autoArrange(t1, r)).toEqual(t1);
  });
});

describe("Fable 적대 1R 봉합(model = claude-fable-5-1) — R1 좌열 속 워커 닫힘 · R2 둘째 master 가 좌열을 밀어냄 · R3 손상 비율", () => {
  it("R1 워커가 좌열 기둥 안(cso 아래)에 있다가 닫히면 → 좌열 사람 값(가로 0.4 · 위아래 0.6) 그대로", () => {
    const r = roles([...HQ, ...W(3, 4)]);
    const t0 = S(S(P(1), S(P(2), P(3), "col", 0.5), "col", 0.6), P(4), "row", 0.4);
    expect(autoArrange(t0, r, { remove: [3] })).toEqual(S(S(P(1), P(2), "col", 0.6), P(4), "row", 0.4));
    // master 바로 아래에 끼어 있던 경우 · 둘을 한 번에 닫는 경우도
    const t1 = S(S(S(P(1), P(3), "col", 0.5), P(2), "col", 0.6), P(4), "row", 0.4);
    expect(autoArrange(t1, r, { remove: [3] })).toEqual(S(S(P(1), P(2), "col", 0.6), P(4), "row", 0.4));
    const r5 = roles([...HQ, ...W(3, 4, 5)]);
    const t2 = S(S(S(P(1), P(3), "col", 0.5), S(P(2), P(5), "col", 0.5), "col", 0.6), P(4), "row", 0.4);
    expect(autoArrange(t2, r5, { remove: [3, 5] })).toEqual(S(S(P(1), P(2), "col", 0.6), P(4), "row", 0.4));
  });
  it("R2 새로 붙는 둘째 master(master-2)는 기존 좌열 master 를 밀어내지 않는다(after 가 앞이어도)", () => {
    const r = roles([...HQ, ...W(3), [9, "master-2"]]);
    const left = S(P(1), P(2), "col", 0.8);
    const t0 = S(P(3), left, "row", 0.5);
    const t1 = autoArrange(t0, r, { add: [{ sid: 9, after: 3 }] })!;
    expect((t1 as any).a).toBe(left);
    expect(units(t1).slice(1)).toEqual([P(3), P(9)]);
    evenUnits(t1, true);
  });
  it("R3 워커 기둥 안 손상 비율(0·1·NaN·음수)은 0.5 로 · 멀쩡한 기둥은 같은 객체", () => {
    const r = roles([...HQ, ...W(3, 4, 5, 6, 9)]);
    for (const bad of [0, 1, NaN, -0.3, 1.7]) {
      const good = S(P(5), P(6), "col", 0.7);
      const t0 = S(S(P(1), P(2), "col", 0.8), S(S(P(3), P(4), "col", bad), good), "row", 0.4);
      const t1 = autoArrange(t0, r, { add: [{ sid: 9 }] })!;
      expect(units(t1)[1]).toEqual(S(P(3), P(4), "col", 0.5));
      expect(units(t1)[2]).toBe(good);
    }
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
    const bad = r() < 0.05 ? [0, 1, NaN][Math.floor(r() * 3)] : null; // (Fable R3) 손상 비율도 섞는다
    return S(randTree(r, ids.slice(0, k)), randTree(r, ids.slice(k)), r() < 0.5 ? "row" : "col", bad !== null ? bad : r() < 0.3 ? undefined : 0.05 + r() * 0.9);
  }
  const ROLE_POOL = ["master", "cso", "worker", "worker-2", "reviewer", null, "master-2", "cso-2"];
  it("무작위 트리 3000개 × 열기·닫기 — sid 집합 = (입력 − remove) ∪ add · 중복 0 · 기둥 폭 합 = 1 · 사람 위아래 나눔 무접촉(v2)", () => {
    const r = rng(20260925);
    for (let iter = 0; iter < 3000; iter++) {
      const n = Math.floor(r() * 14);
      const ids = Array.from({ length: n }, (_, i) => 100 + i);
      const tree = n ? randTree(r, ids) : null;
      const rm = new Map<number, string | null>();
      for (const s of [...ids, 900, 901, 902]) rm.set(s, ROLE_POOL[Math.floor(r() * ROLE_POOL.length)]);
      const remove = ids.filter(() => r() < 0.25);
      // (Opus 적대 1R F5) 없는 좌석 닫기 · 이미 있는 좌석 다시 붙이기 · 빠지는 좌석을 after 로 가리키기도 섞는다
      const add = [900, 901, 902, ...(ids.length && r() < 0.2 ? [ids[0]] : [])].filter(() => r() < 0.4).map((sid) => ({ sid, after: r() < 0.5 && ids.length ? ids[Math.floor(r() * ids.length)] : undefined, dir: r() < 0.3 ? ("col" as const) : undefined }));
      if (r() < 0.2) remove.push(777);
      for (const mode of ["auto", "standard"] as const) {
        const out = autoArrange(tree, rm, { add, remove }, mode);
        const want = new Set([...ids.filter((s) => !remove.includes(s)), ...add.map((a) => a.sid)]); // = (입력 − remove) ∪ add
        const got = sids(out);
        expect(new Set(got)).toEqual(want);
        expect(got.length).toBe(want.size);
        if (out) {
          const tot = [...area(out).values()].reduce((a, b) => a + b, 0);
          expect(tot).toBeCloseTo(1, 9);
          // (Opus 적대 1R F5) 가로 몫: 좌열 한 칸 + 워커 칸 전부 = 1 · 모든 비율이 (0,1) 안
          // 가로 몫: 루트를 가로로 펼친 기둥들의 폭 합 = 1(v2 — 위아래 기둥 안 칸은 폭을 나눠 갖지 않는다)
          expect(unitWidths(out).reduce((a, b) => a + b, 0)).toBeCloseTo(1, 9);
          const ratiosOk = (n: LayoutNode): boolean => n.type === "pane" || (n.ratio === undefined || (n.ratio > 0 && n.ratio < 1)) && ratiosOk(n.a) && ratiosOk(n.b);
          expect(ratiosOk(out)).toBe(true);
          const lf = (x: number) => { const f = String(rm.get(x) ?? ""); return f === "master" || f.startsWith("master-") || f === "cso" || f.startsWith("cso-"); };
          // 좌열 좌석 = 이미 있던 좌석에서 먼저(Fable R2 봉합과 같은 고르기) · 없으면 새 좌석에서
          const pref = [...got.filter((x) => ids.includes(x)), ...got.filter((x) => !ids.includes(x))];
          const leftPicked = [pref.find((s) => /^master(-|$)/.test(String(rm.get(s) ?? ""))), pref.find((s) => /^cso(-|$)/.test(String(rm.get(s) ?? "")))].filter((x) => x !== undefined) as number[];
          void lf;
          if (mode === "standard") {
            // 정렬 단추 = 종전 표준: 좌열 밖 세로 분할 0 · 좌열 아닌 칸 전부 같은 가로 몫 · 좌열 두 칸은 위아래
            const sh = shares(out);
            const restW = got.filter((s) => !leftPicked.includes(s)).map((s) => sh.get(s)!);
            for (const x of restW) expect(x).toBeCloseTo(restW[0], 9);
            if (leftPicked.length === 2) expect(sh.get(leftPicked[0])!).toBeCloseTo(sh.get(leftPicked[1])!, 9);
          } else {
            // (v2) 사람이 만든 위아래 나눔 무접촉 — 좌열 좌석이 없고 · 닫히는 좌석도 · 새 칸의 기준(after)도 없는 입력 기둥은
            //   결과에 **같은 객체**로 남는다(맞출 수 있든 없든).
            if (tree) for (const u of units(tree)) {
              const us = sids(u);
              if (us.some((x) => leftPicked.includes(x) || remove.includes(x) || add.some((a) => a.after === x || a.sid === x))) continue;
              const damaged = (n: LayoutNode): boolean => n.type === "split" && ((n.ratio !== undefined && !(Number.isFinite(n.ratio) && n.ratio > 0 && n.ratio < 1)) || damaged(n.a) || damaged(n.b));
              if (damaged(u)) continue; // (Fable R3) 손상 비율 기둥은 0.5 로 고쳐진다 — 같은 객체가 아니다
              expect(hasNode(out, u)).toBe(true);
            }
            // 결과가 「맞춘 모양」(좌열 좌석을 품은 기둥이 좌열 좌석만 품음)이면 워커 기둥끼리 가로 몫이 같다
            const ou = units(out);
            const fixed = ou.every((u) => { const us = sids(u); return !us.some((x) => leftPicked.includes(x)) || us.every((x) => leftPicked.includes(x)); });
            if (fixed) {
              const uw = unitWidths(out).filter((_, i) => !sids(ou[i]).some((x) => leftPicked.includes(x)));
              for (const x of uw) expect(x).toBeCloseTo(uw[0], 9);
              if (leftPicked.length === 2) expect(shares(out).get(leftPicked[0])!).toBeCloseTo(shares(out).get(leftPicked[1])!, 9);
            }
          }
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
    expect(b).toContain('ws.tree = autoArrange(ws.tree, arrangeRolesBySocket.get(ws.socket ?? "") ?? new Map(), change, mode, currentDefaultLeftShare());');
  });
  const paths: [string, string, string, string][] = [
    ["자동 입양(3초 틱)", "async function refreshPaneTitles() {", "\n}\n", "arrangeWs(ws, { add: [{ sid: s.surface_id }] });"],
    ["자리표 회수(틱 안)", "── ③ 빈 자리표 회수", "const masterSids", "arrangeWs(ws, { remove: [sid] });"],
    ["새 창", "async function actionNew() {", "\n}\n", "arrangeWs(ws, { add: [{ sid }] });"],
    ["분할", "async function actionSplit(", "\n}\n", "arrangeWs(ws, { add: [{ sid, after: target, dir }] });"],
    ["닫기(Close·⌘W·팔레트)", "async function actionClose() {", "\n}\n", "arrangeWs(ws, { remove: [sid] });"],
    ["창 머리 ×", 'closeBtn.dataset.arm !== "1"', "header.append(", "arrangeWs(ws, { remove: [sid] });"],
    ["외부 닫힘·유령·스윕(detachPane)", "function detachPane(", "\n}\n", "arrangeWs(ws, { remove: [sid] });"],
    ["복원 때 죽은 좌석 정리", "const dead = deadLiveSids(", "workspaces = workspaces.filter", "if (dead.length) arrangeWs(ws, { remove: dead });"],
    ["복원 입양", "재시작(복원) 경로도 **같은 함수**", "plain 셸 1개로 충전", "arrangeWs(ws, { add: [{ sid: s.surface_id }] });"],
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

describe("호출부 — 입양은 런타임이 선 그 자리에서 트리에 붙는다(Opus 적대 1R F2)", () => {
  for (const [name, head, mk] of [
    ["3초 틱", "async function refreshPaneTitles() {", "const rt = await makePane(s.surface_id, s.title, sk);"],
    ["복원", "재시작(복원) 경로도 **같은 함수**", "await makePane(s.surface_id, s.title, sk);"],
  ] as const) {
    it(`${name}: makePane 과 arrangeWs(add) 사이에 다른 await 0 · 틱 끝 모음 배치 0`, () => {
      const b = code(fnBody(head, name === "3초 틱" ? "\n}\n" : "plain 셸 1개로 충전"));
      const i = b.indexOf(mk);
      const j = b.indexOf("arrangeWs(ws, { add: [{ sid: s.surface_id }] });", i);
      expect(i).toBeGreaterThan(-1);
      expect(j).toBeGreaterThan(i);
      expect(b.slice(i + mk.length, j)).not.toContain("await ");
      expect(b).not.toContain("relayoutWs");
      expect(b).not.toContain("adoptAdds");
    });
  }
  it("이미 붙은 좌석을 또 붙이거나 없는 좌석을 닫으면 배치 무변경(정렬 단추만 예외)", () => {
    const b = code(fnBody("function arrangeWs(", "\n}\n"));
    expect(b).toContain('if (!effective && mode !== "standard") return;');
  });
  it("역할 표는 목록에서 사라져도 화면에 남은 좌석의 역할을 이어서 기억한다(유령 수렴 뒤 좌열 인식 · Opus 2R 잔여)", () => {
    const b = code(fnBody("function rememberRoles(", "\n}\n"));
    expect(b).toContain("if (!next.has(sid) && onScreen.has(sid)) next.set(sid, role);");
  });
  it("창 머리 × = 그 창을 품은 탭을 짠다(기다리는 사이 탭을 옮겨도)", () => {
    const b = code(fnBody('closeBtn.dataset.arm !== "1"', "header.append("));
    expect(b).toContain("collectSids(w.tree).includes(sid)) ?? current();");
  });
});

// ★v2(박사님 결정 09-25 14:1x · master#88533ed8)로 변경: v1(master 판정 ⓒ)은 「세로 분할」을 뺐다 — 창이 언제나 한 줄로 펴져
//   이름이 거짓이 됐기 때문이다. v2 는 사람이 만든 위아래 나눔을 지키므로 세로 분할이 다시 참이다 → 복원.
describe("v2 — 팔레트 「세로 분할」 복원 · ⌘⇧D = 세로 분할", () => {
  it("팔레트 빌트인 액션에 세로 분할 = actionSplit(\"col\") · 가로 분할·패널 균등화 유지", () => {
    const b = code(fnBody("// ── (5) 빌트인 webview 액션(정적) ──", "\n  );\n"));
    expect(b).toContain('{ id: "act:split-col", title: "세로 분할", keywords: "split col 분할", action: () => actionSplit("col") },');
    expect(b).toContain('{ id: "act:split-row", title: "가로 분할"');
    expect(b).toContain('{ id: "act:equalize", title: "패널 균등화"');
  });
  it("⌘⇧D 단축키 = actionSplit(\"col\")(세로 분할 · row 로 바꾸지 않는다)", () => {
    expect(/e\.shiftKey\) \{\s*e\.preventDefault\(\);\s*actionSplit\("col"\);/.test(main)).toBe(true);
  });
  it("actionSplit 은 방향을 버리지 않고 arrangeWs 에 넘긴다", () => {
    const b = code(fnBody("async function actionSplit(", "\n}\n"));
    expect(b).not.toContain("void dir");
    expect(b).toContain("arrangeWs(ws, { add: [{ sid, after: target, dir }] });");
  });
});
