// formation.test.ts — 역할 배치 회귀(B16 · 오너 확정 2026-09-19 16:1x 「좌열 master:cso = 4:1 · worker 오른쪽」).
//
// ★이 스위트가 반드시 재야 하는 것은 두 가지다:
//   ⑴오너가 확정한 비(4:1)와 방향(좌/우·상/하)이 실제 트리에서 그 값으로 나오는가.
//   ⑵2026-07-27 붕괴(역할 4열 안이 화면을 통째로 세로로 만든 사고)가 재발하지 않는가.
//     그 기전 ⑵는 「열이 1개일 때 래퍼가 소멸」이었으므로, 전원 워커 함대를 직접 태워 확인한다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { formationLayout, formationIfRowOnly, hasHqSeats, leftColumnShare, MASTER_CSO_RATIO, type LayoutNode, type Seat } from "./formation";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const P = (sid: number): LayoutNode => ({ type: "pane", sid });
const R = (a: LayoutNode, b: LayoutNode, dir: "row" | "col" = "row"): LayoutNode => ({ type: "split", dir, a, b });
// 화면 몫 — ratio 를 곱해 내려가며 각 pane 의 최종 면적 비를 구한다.
function shares(n: LayoutNode, w = 1, out = new Map<number, number>()): Map<number, number> {
  if (n.type === "pane") { out.set(n.sid, w); return out; }
  const r = n.ratio ?? 0.5;
  shares(n.a, w * r, out); shares(n.b, w * (1 - r), out);
  return out;
}
const seats = (...xs: [number, string | null][]): Seat[] => xs.map(([sid, role]) => ({ sid, role }));
const comb = (ids: number[]): LayoutNode => ids.slice(1).reduce<LayoutNode>((t, i) => R(t, P(i)), P(ids[0]));

describe("B16 오너 확정 비·방향", () => {
  it("좌열은 세로 분할이고 master:cso 면적비가 정확히 4:1", () => {
    const t = formationLayout(seats([30, "master"], [31, "cso"], [29, "worker"]))!;
    expect(t.type).toBe("split");
    const left = (t as any).a;
    expect(left.dir).toBe("col");          // 상하
    expect((t as any).dir).toBe("row");     // 좌우
    const sh = shares(left);                 // 좌열 안에서의 비
    expect(sh.get(30)! / sh.get(31)!).toBeCloseTo(4, 9);
    expect(MASTER_CSO_RATIO).toBeCloseTo(0.8, 9);
  });

  it("master 가 위·cso 가 아래 (순서를 뒤집어 넣어도)", () => {
    const t = formationLayout(seats([31, "cso"], [30, "master"], [29, "worker"]))! as any;
    expect(t.a.a).toEqual(P(30));
    expect(t.a.b).toEqual(P(31));
  });

  it("worker 는 오른쪽 열에 들어가고 늘어나면 오른쪽으로 분할된다", () => {
    const t = formationLayout(seats([30, "master"], [31, "cso"], [1, "worker"], [2, "worker-2"], [3, "worker-3"]))! as any;
    expect(t.b.dir).toBe("row");
    // 우열 안에서 워커는 균등 · 입력 순서 보존
    const right = shares(t.b);
    expect([...right.keys()]).toEqual([1, 2, 3]);
    for (const k of [1, 2, 3]) expect(right.get(k)).toBeCloseTo(1 / 3, 9);
  });

  it("전체 면적 합 = 1 · 워커가 늘수록 좌열은 1/3 로 수렴", () => {
    for (const n of [1, 2, 4, 6]) {
      const ws: [number, string | null][] = [...Array(n).keys()].map((i) => [100 + i, "worker"]);
      const t = formationLayout(seats([30, "master"], [31, "cso"], ...ws))!;
      const sh = shares(t);
      expect([...sh.values()].reduce((a, b) => a + b, 0)).toBeCloseTo(1, 9);
      expect(sh.get(30)! + sh.get(31)!).toBeCloseTo(leftColumnShare(n), 9);
    }
    expect(leftColumnShare(1)).toBeCloseTo(1 / 2, 9);
    expect(leftColumnShare(2)).toBeCloseTo(1 / 3, 9);
    expect(leftColumnShare(6)).toBeCloseTo(1 / 3, 9);
  });
});

describe("B16 2026-07-27 붕괴 재발 방지", () => {
  it("전원 워커 7기 — 화면이 세로로 무너지지 않는다(가로 균등)", () => {
    // 그날의 함대 구성 그대로. 기전 ⑴빈 역할 버킷 ⑵열 1개일 때 row 래퍼 소멸.
    const t = formationLayout(seats(...[...Array(7).keys()].map((i): [number, string | null] => [i + 1, "worker"])))!;
    expect(t.type).toBe("split");
    expect((t as any).dir).toBe("row");   // ★세로였다면 여기서 빨개진다
    const sh = shares(t);
    expect(sh.size).toBe(7);
    for (const k of sh.keys()) expect(sh.get(k)).toBeCloseTo(1 / 7, 9);
  });

  it("master 만 · cso 만 — 빈 버킷이 열을 만들지 않는다", () => {
    expect(formationLayout(seats([30, "master"]))).toEqual(P(30));
    expect(formationLayout(seats([31, "cso"]))).toEqual(P(31));
    // master 1 + worker 1 = 좌열은 pane 하나(빈 cso 칸이 생기지 않는다)
    const t = formationLayout(seats([30, "master"], [1, "worker"]))! as any;
    expect(t.a).toEqual(P(30));
    expect(shares(t).get(30)).toBeCloseTo(1 / 2, 9);
  });

  it("좌석 0개는 null(호출자가 트리를 건드리지 않는다)", () => {
    expect(formationLayout([])).toBeNull();
  });
});

describe("B16 전제 판정 · 사용자 배치 존중", () => {
  it("hasHqSeats — master·cso 가 cys 좌석일 때만 참(우리 개발 기기는 거짓)", () => {
    expect(hasHqSeats(new Map([[1, "worker"], [2, "worker-2"]]))).toBe(false);
    expect(hasHqSeats(new Map([[1, "worker"], [2, null]]))).toBe(false);
    expect(hasHqSeats(new Map([[1, "worker"], [30, "master"]]))).toBe(true);
    expect(hasHqSeats(new Map([[1, "worker"], [31, "cso-2"]]))).toBe(true);
  });

  it("col 분할이 섞인 사용자 배치는 같은 객체 그대로(무접촉)", () => {
    const roles = new Map<number, string | null>([[30, "master"], [31, "cso"], [1, "worker"]]);
    const shallow = R(R(P(30), P(31), "col"), P(1));
    expect(formationIfRowOnly(shallow, roles)).toBe(shallow);
    const deep = R(R(P(30), P(1)), R(P(31), P(2), "col"));
    expect(formationIfRowOnly(deep, roles)).toBe(deep);
  });

  it("순수 row 트리는 역할 배치로 다시 짜인다 — 좌→우 워커 순서 보존", () => {
    const roles = new Map<number, string | null>([[1, "worker"], [30, "master"], [31, "cso"], [2, "worker-2"]]);
    const t = formationIfRowOnly(comb([1, 30, 31, 2]), roles) as any;
    expect(t.dir).toBe("row");
    expect(t.a.dir).toBe("col");
    expect([...shares(t.b).keys()]).toEqual([1, 2]);
  });
});

describe("B16 호출부 — 3경로가 같은 함수를 부른다", () => {
  // ★오너 지시 09-25 로 변경(TICKET=v116-auto-equalize): 세 경로가 지나는 「같은 함수」가 formationIfRowOnly/formationLayout
  //   에서 autoArrange(arrangeWs 한 곳)로 바뀌었다. 축(입양·복원 입양·정렬이 같은 배치 함수를 지난다)은 그대로다 —
  //   열기·닫기 전 경로의 핀은 autoarrange.test.ts 「호출부」 절이 쥔다.
  it("입양·복원 입양·정렬 세 곳 전부 arrangeWs(autoArrange)를 경유", () => {
    expect(main).toContain('import { autoArrange, type ArrangeChange, type LeftShareMode } from "./formation";');
    const eq = main.slice(main.indexOf("async function actionEqualize()"), main.indexOf("// ---------- workspace tabs ----------"));
    expect(eq).toContain('arrangeWs(ws, { remove: all.filter((sid) => !live.includes(sid)) }, "standard");');
    expect(main).toContain("arrangeWs(ws, { add: adoptAdds.get(ws) ?? [] });");
    expect(main).toContain("if (restoreAdds.length) arrangeWs(ws, { add: restoreAdds });");
    expect(main).not.toContain("formationIfRowOnly(");
  });
});
