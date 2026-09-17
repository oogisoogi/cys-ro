// adoptlayout.ts — 역할 pane 자동 입양 시 열 재배치(TICKET=cysr-102-pack-b B3 · master 판정 B 좁힌 판).
//
// 실기(깨끗한 VM run4): 입양이 매번 루트를 {row, a: 기존 트리, b: 새 pane} 로 감싸고 ratio 미지정(0.5)이라
// 셸 → master → cso → worker 순 입양이 [[[셸|master]|cso]|worker] = 1/8·1/8·1/4·1/2 가 됐다(마스터 칸 ≈100px).
// 처방: 입양이 일어난 ws 의 트리가 순수 row 열뿐이면 기존 좌→우 순서 그대로 가중 comb 로 다시 짠다 —
// master 열 = 1/3(열 2개면 1/2) · 나머지 균등. col 분할이 하나라도 있으면(사용자 배치) 같은 객체 그대로(무접촉).
// 한계: 순수 row 트리에서 사용자가 드래그한 비율은 입양 순간 표준 배치로 리셋된다.

export type LayoutNode =
  | { type: "split"; dir: "row" | "col"; ratio?: number; a: LayoutNode; b: LayoutNode }
  | { type: "pane"; sid: number };

function sidsInOrder(n: LayoutNode, out: number[] = []): number[] {
  if (n.type === "pane") out.push(n.sid);
  else { sidsInOrder(n.a, out); sidsInOrder(n.b, out); }
  return out;
}

// 가중 comb — ratio_i = w_i / Σ(w_i..끝) 이면 열 i 의 몫이 정확히 w_i / Σw 가 된다.
// master 가중 = max(1, (n-1)/2) → n≥3 에서 master 몫 = 1/3 · n=2 에서 1/2 · master 없으면 균등.
export function adoptLayout(sids: number[], masterSids: Set<number>): LayoutNode {
  const n = sids.length;
  const w = sids.map((sid) => (masterSids.has(sid) ? Math.max(1, (n - 1) / 2) : 1));
  let acc: LayoutNode = { type: "pane", sid: sids[n - 1] };
  let tail = w[n - 1];
  for (let i = n - 2; i >= 0; i--) {
    tail += w[i];
    acc = { type: "split", dir: "row", ratio: w[i] / tail, a: { type: "pane", sid: sids[i] }, b: acc };
  }
  return acc;
}

export function isRowOnly(n: LayoutNode): boolean {
  return n.type === "pane" || (n.dir === "row" && isRowOnly(n.a) && isRowOnly(n.b));
}

export function adoptLayoutIfRowOnly(tree: LayoutNode, masterSids: Set<number>): LayoutNode {
  return isRowOnly(tree) ? adoptLayout(sidsInOrder(tree), masterSids) : tree;
}
