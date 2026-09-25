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
  // ★박사님 결정 09-25 14:5x(master#db159bcf)로 변경: master 몫 1/3(열 2개면 1/2) → 언제나 25%(LEFT_SHARE_DEFAULT).
  it("run4 재현 트리: 수정 전 master 1/8 → 재배치 후 25% · 나머지 1/4 · 순서 보존", () => {
    const run4 = comb([1, 2, 3, 4]);
    expect(shares(run4).get(2)).toBeCloseTo(1 / 8, 9);
    const sh = shares(adoptLayoutIfRowOnly(run4, new Set([2])));
    expect(sh.get(2)).toBeCloseTo(0.25, 9);
    for (const k of [1, 3, 4]) expect(sh.get(k)).toBeCloseTo(0.25, 9);
    expect([...sh.keys()]).toEqual([1, 2, 3, 4]);
  });

  it("열 수 2·3·5·6·8 에서 master = 정확히 25% · 합 1(워커 수와 무관 · 박사님 결정 14:5x)", () => {
    expect(shares(adoptLayout([2, 3], new Set([2]))).get(2)).toBeCloseTo(0.25, 9);
    for (const n of [3, 5, 6, 8]) {
      const ids = [...Array(n).keys()].map((i) => i + 1);
      const sh = shares(adoptLayoutIfRowOnly(comb(ids), new Set([2])));
      expect(sh.get(2)!).toBeCloseTo(0.25, 9);
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
  // ★오너 지시 09-25 로 변경(TICKET=v116-auto-equalize): 입양은 이제 트리를 0.5 로 감싸지 않고 붙는 좌석을 모아
  //   배치 함수(arrangeWs → autoArrange)에 넘긴다. 이 모듈(adoptLayout)은 main 에서 더는 불리지 않는다(순수 함수 시험은 남긴다).
  //   축은 그대로 — 「입양 뒤에 · 입양 ws 에만 재배치가 걸린다」.
  it("refreshPaneTitles 의 입양 블록 뒤에서 arrangeWs 를 입양 ws 에만 적용 · 0.5 감싸기 0", () => {
    const s = main.indexOf("async function refreshPaneTitles() {");
    expect(s).toBeGreaterThan(-1);
    const body = main.slice(s, main.indexOf("\n}\n", s));
    expect(body).not.toContain('{ type: "split", dir: "row", a: ws.tree, b: { type: "pane", sid: s.surface_id } }');
    // (Opus 적대 1R F2 뒤) 붙는 좌석마다 런타임이 선 그 자리에서 배치 — 틱 끝 모음 배치(relayoutWs)는 걷었다.
    const mk = body.indexOf("const rt = await makePane(s.surface_id, s.title, sk);");
    const call = body.indexOf("arrangeWs(ws, { add: [{ sid: s.surface_id }] });", mk);
    expect(mk).toBeGreaterThan(-1);
    expect(call).toBeGreaterThan(mk);
    const between = body.slice(mk + "const rt = await makePane(s.surface_id, s.title, sk);".length, call).replace(/\/\/[^\n]*/g, "");
    expect(between).not.toContain("await "); // 런타임이 선 뒤 트리에 붙기 전까지 다른 await(던질 자리) 0
    expect(main).not.toContain('from "./adoptlayout"');
  });
});
