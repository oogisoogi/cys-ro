// adoptlayout.ts — 역할 pane 자동 입양 시 열 재배치(TICKET=cysr-102-pack-b B3 · master 판정 B 좁힌 판).
//
// 실기(깨끗한 VM run4): 입양이 매번 루트를 {row, a: 기존 트리, b: 새 pane} 로 감싸고 ratio 미지정(0.5)이라
// 셸 → master → cso → worker 순 입양이 [[[셸|master]|cso]|worker] = 1/8·1/8·1/4·1/2 가 됐다(마스터 칸 ≈100px).
// 처방: 입양이 일어난 ws 의 트리가 순수 row 열뿐이면 기존 좌→우 순서 그대로 가중 comb 로 다시 짠다 —
// master 열 = 25%(박사님 결정 09-25 14:5x · 옛 1/3·1/2) · 나머지 균등. col 분할이 하나라도 있으면(사용자 배치) 같은 객체 그대로(무접촉).
// 한계: 순수 row 트리에서 사용자가 드래그한 비율은 입양 순간 표준 배치로 리셋된다.

import { LEFT_SHARE_DEFAULT } from "./formation";

export type LayoutNode =
  | { type: "split"; dir: "row" | "col"; ratio?: number; a: LayoutNode; b: LayoutNode }
  | { type: "pane"; sid: number };

function sidsInOrder(n: LayoutNode, out: number[] = []): number[] {
  if (n.type === "pane") out.push(n.sid);
  else { sidsInOrder(n.a, out); sidsInOrder(n.b, out); }
  return out;
}

// 가중 comb — ratio_i = w_i / Σ(w_i..끝) 이면 열 i 의 몫이 정확히 w_i / Σw 가 된다.
// master 가중 = (n-1)·S/(1-S) (S = LEFT_SHARE_DEFAULT = 25%) → 칸 2개 이상이면 master 몫 = 정확히 25% · master 없으면 균등.
// ★박사님 결정 2026-09-25 14:5x(master#db159bcf): 좌열 기본 폭 = 화면 25% 상수(옛 가중 max(1,(n-1)/2) = 1/2·1/3 폐기).
//   (이 모듈은 main 에서 더는 불리지 않지만 옛 규칙이 남으면 되살아날 때 폭이 튄다 — 같은 상수로 맞춘다.)
export function adoptLayout(sids: number[], masterSids: Set<number>): LayoutNode {
  const n = sids.length;
  const mw = n >= 2 ? ((n - 1) * LEFT_SHARE_DEFAULT) / (1 - LEFT_SHARE_DEFAULT) : 1;
  const w = sids.map((sid) => (masterSids.has(sid) ? mw : 1));
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
