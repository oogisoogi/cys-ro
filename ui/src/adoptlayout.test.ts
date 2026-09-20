// adoptlayout.test.ts — 자동 입양 열 재배치 회귀(TICKET=cysr-102-pack-b B3 · master 판정 B 좁힌 판).
//
// 실기(깨끗한 VM run4 · 3-master-focus-full.png): 4분할 시 마스터 칸 ≈100px — 입양이 루트를 매번 0.5 로 감싼 결과
// [[[셸|master]|cso]|worker] = 1/8·1/8·1/4·1/2. 기대 = master ≥ 1/3 · col 분할이 섞인 사용자 배치는 무접촉.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { adoptLayout, adoptLayoutIfRowOnly, type LayoutNode } from "./adoptlayout";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");

const P = (sid: number): LayoutNode => ({ type: "pane", sid });
const R = (a: LayoutNode, b: LayoutNode, dir: "row" | "col" = "row"): LayoutNode => ({ type: "split", dir, a, b });
function shares(n: LayoutNode, w = 1, out = new Map<number, number>()): Map<number, number> {
  if (n.type === "pane") { out.set(n.sid, w); return out; }
  const r = n.ratio ?? 0.5;
  shares(n.a, w * r, out); shares(n.b, w * (1 - r), out);
  return out;
}
const comb = (ids: number[]): LayoutNode => ids.slice(1).reduce<LayoutNode>((t, i) => R(t, P(i)), P(ids[0]));

describe("B3 master 칸 폭", () => {
  it("run4 재현 트리: 수정 전 master 1/8 → 재배치 후 1/3 · 나머지 2/9 · 순서 보존", () => {
    const run4 = comb([1, 2, 3, 4]);
    expect(shares(run4).get(2)).toBeCloseTo(1 / 8, 9);
    const sh = shares(adoptLayoutIfRowOnly(run4, new Set([2])));
    expect(sh.get(2)).toBeCloseTo(1 / 3, 9);
    for (const k of [1, 3, 4]) expect(sh.get(k)).toBeCloseTo(2 / 9, 9);
    expect([...sh.keys()]).toEqual([1, 2, 3, 4]);
  });

  it("열 수 2·3·5·6·8 에서 master ≥ 1/3 · 합 1", () => {
    expect(shares(adoptLayout([2, 3], new Set([2]))).get(2)).toBeCloseTo(0.5, 9);
    for (const n of [3, 5, 6, 8]) {
      const ids = [...Array(n).keys()].map((i) => i + 1);
      const sh = shares(adoptLayoutIfRowOnly(comb(ids), new Set([2])));
      expect(sh.get(2)!).toBeGreaterThan(1 / 3 - 1e-9);
      expect([...sh.values()].reduce((a, b) => a + b, 0)).toBeCloseTo(1, 9);
    }
  });

  it("master 없음 = 균등 · 단일 pane = 전체", () => {
    const sh = shares(adoptLayoutIfRowOnly(comb([1, 3, 4]), new Set()));
    for (const k of [1, 3, 4]) expect(sh.get(k)).toBeCloseTo(1 / 3, 9);
    expect(shares(adoptLayoutIfRowOnly(P(7), new Set([7]))).get(7)).toBe(1);
  });
});

describe("B3 좁힌 판 — col 분할 포함 트리 무접촉", () => {
  it("얕은·깊은 col 분할이 있으면 같은 객체를 그대로 돌려준다", () => {
    const shallow = R(R(P(1), P(2), "col"), P(3));
    expect(adoptLayoutIfRowOnly(shallow, new Set([2]))).toBe(shallow);
    const deep = R(R(P(1), P(2)), R(P(3), P(4), "col"));
    expect(adoptLayoutIfRowOnly(deep, new Set([2]))).toBe(deep);
  });
});

describe("B3 호출부 — 입양 루프가 실제로 재배치를 부른다", () => {
  it("refreshPaneTitles 의 입양 블록 뒤에서 adoptLayoutIfRowOnly 를 입양 ws 에만 적용", () => {
    const s = main.indexOf("async function refreshPaneTitles() {");
    expect(s).toBeGreaterThan(-1);
    const body = main.slice(s, main.indexOf("\n}\n", s));
    const wrap = body.indexOf('{ type: "split", dir: "row", a: ws.tree, b: { type: "pane", sid: s.surface_id } }');
    const add = body.indexOf("adoptedWs.add(ws);");
    // ★B16(2026-09-20)에서 이 줄이 삼항으로 갈렸다 — 본부 역할이 cys 좌석인 기기는 formationIfRowOnly,
    //   전제가 없는 기기(우리 개발 기기)는 종전 adoptLayoutIfRowOnly. **이 스위트가 지키는 축은
    //   「호출 문자열」이 아니라 「입양 뒤에 · 입양 ws 에만 재배치가 걸린다」이므로** 축은 그대로 두고
    //   조준만 옮긴다(줄을 지우면 그 축이 통째로 사라진다).
    const call = body.indexOf("adoptLayoutIfRowOnly(ws.tree, masterSids)");
    expect(wrap).toBeGreaterThan(-1);
    expect(add).toBeGreaterThan(wrap);
    expect(call).toBeGreaterThan(add);
    expect(body.slice(add, call)).toContain("for (const ws of adoptedWs)");
    // 전제가 없는 기기의 폴백이 살아 있는가(무회귀 축) + 전제가 있는 기기의 분기가 같은 루프 안인가.
    expect(body.slice(add, call)).toContain("hasHqSeats(roleBySid)");
    expect(body.slice(add)).toContain("formationIfRowOnly(ws.tree, roleBySid)");
    expect(main).toContain('import { adoptLayoutIfRowOnly } from "./adoptlayout";');
  });
});
