// formation.ts — 역할 기반 배치(B16 · 오너 확정 2026-09-19 16:1x).
//
// 오너 확정: 「왼쪽 열 master(위) : cso(아래) = 4 : 1 · worker 는 오른쪽 열(늘면 오른쪽으로 분할)」.
//
// ★2026-07-27 에 역할별 4열 안이 폐기됐다(main.ts §정렬 주석 「되돌리지 마라」). 그 폐기의 근거는
//   **전제**였다: 「지금 master·CSO 는 cmux 페인이라 cys 에는 역할로 열을 묶을 전제가 없다」.
//   그 전제는 **우리 개발 기기에만** 참이다 — 참가자 기기(cysr)에서는 master·cso·worker 가 전부
//   cys 좌석이다(오너 윈 실기 2026-09-19 16:2x: 29 worker · 30 master · 31 cso). 전제가 다르므로
//   그 주석 자신의 논리("전제가 달라졌으므로 설계도 달라진다")에 따라 설계도 달라진다.
//   ⇒ 되돌리는 것이 아니라, 전제가 성립하는 기기에서만 켜지는 배치다(역할이 없으면 자동으로 무동작).
//
// ★그때의 붕괴 기전을 그대로 피한다(재발 방지가 이 모듈의 설계 제약이다):
//   ⑴역할 버킷이 비면 열이 사라졌다 → 여기서는 **빈 버킷을 아예 열로 만들지 않는다**.
//   ⑵evenComb 은 노드가 1개면 래퍼를 돌려주지 않아 요청한 "row" 가 소멸했다 → 여기서는 **열이
//     하나뿐이면 row 래퍼를 요구하지 않는다**(요구하지 않으므로 삼켜질 래퍼가 없다). 워커만 있는
//     함대는 종전처럼 가로 균등이 되고, master·cso 만 있는 함대는 의도대로 세로 4:1 이 된다.

export type LayoutNode =
  | { type: "split"; dir: "row" | "col"; ratio?: number; a: LayoutNode; b: LayoutNode }
  | { type: "pane"; sid: number };

export type Seat = { sid: number; role?: string | null };

/// 좌열 안에서 master 가 갖는 몫 — 오너 확정 4 : 1.
export const MASTER_CSO_RATIO = 4 / 5;

// 역할 정규화 — cso-2·worker-3 같은 서수판을 계열로 접는다(javis_formation 의 _canonical_role 과 같은 취지).
function family(role?: string | null): "master" | "cso" | "other" {
  const r = (role ?? "").trim();
  if (r === "master" || r.startsWith("master-")) return "master";
  if (r === "cso" || r.startsWith("cso-")) return "cso";
  return "other";
}

// 균등 가로 comb — 기존 evenComb(main.ts)과 같은 식. 노드 1개면 그 노드 자체(래퍼 없음).
function evenRow(nodes: LayoutNode[]): LayoutNode {
  let acc = nodes[nodes.length - 1];
  for (let i = nodes.length - 2; i >= 0; i--) {
    acc = { type: "split", dir: "row", ratio: 1 / (nodes.length - i), a: nodes[i], b: acc };
  }
  return acc;
}

/// 좌열이 화면에서 갖는 가로 몫. 오른쪽 워커 수가 늘수록 1/3 으로 수렴한다 —
/// 이미 출고된 adoptLayout(master 가중 = max(1,(n-1)/2))과 **같은 수렴값**이라 체감이 바뀌지 않는다.
export function leftColumnShare(workerCount: number): number {
  const wLeft = Math.max(1, workerCount / 2);
  return wLeft / (wLeft + workerCount);
}

/// 역할 배치. 반환 `null` = 배치할 것이 없다(호출자는 트리를 건드리지 않는다).
///
/// 인자
///  · `seats` — 화면에 살아 있는 좌석 [{sid, role}]. **좌→우 순서는 입력 순서를 보존**한다.
///  · `opts.masterCsoRatio` — 좌열 세로 비(기본 4/5 = 오너 확정 4:1).
///
/// 규칙
///  · 좌열 = master(위) : cso(아래). 둘 중 하나만 있으면 그 하나가 좌열 전체.
///  · 우열 = 나머지 좌석(worker·reviewer·역할 없는 셸) 가로 균등 — 늘면 오른쪽으로 분할된다.
///  · master·cso 가 둘 다 없으면 = 역할로 열을 묶을 전제가 없는 기기다 ⇒ 가로 균등(종전 동작).
export function formationLayout(
  seats: Seat[],
  opts?: { masterCsoRatio?: number },
): LayoutNode | null {
  if (seats.length === 0) return null;
  const pane = (s: Seat): LayoutNode => ({ type: "pane", sid: s.sid });
  const master = seats.find((s) => family(s.role) === "master");
  const cso = seats.find((s) => family(s.role) === "cso");
  // 좌열에 들어간 좌석을 제외한 나머지 — 입력 순서 보존.
  const rest = seats.filter((s) => s !== master && s !== cso);

  let left: LayoutNode | null = null;
  if (master && cso) {
    left = {
      type: "split",
      dir: "col",
      ratio: opts?.masterCsoRatio ?? MASTER_CSO_RATIO,
      a: pane(master),
      b: pane(cso),
    };
  } else if (master || cso) {
    left = pane((master ?? cso)!);
  }

  const right = rest.length > 0 ? evenRow(rest.map(pane)) : null;

  if (left && right) {
    return { type: "split", dir: "row", ratio: leftColumnShare(rest.length), a: left, b: right };
  }
  // ★열이 하나뿐이면 래퍼를 만들지 않는다 — 2026-07-27 붕괴 기전 ⑵ 의 정면 대응.
  return left ?? right;
}

function sidsInOrder(n: LayoutNode, out: number[] = []): number[] {
  if (n.type === "pane") out.push(n.sid);
  else { sidsInOrder(n.a, out); sidsInOrder(n.b, out); }
  return out;
}

function isRowOnly(n: LayoutNode): boolean {
  return n.type === "pane" || (n.dir === "row" && isRowOnly(n.a) && isRowOnly(n.b));
}

/// 본부 역할(master·cso)이 **cys 좌석으로 존재하는가** — 이 배치의 전제.
/// 거짓이면 역할로 열을 묶을 전제가 없는 기기다(우리 개발 기기: master·cso 는 cmux 페인).
export function hasHqSeats(roleBySid: Map<number, string | null | undefined>): boolean {
  for (const role of roleBySid.values()) {
    const f = family(role);
    if (f === "master" || f === "cso") return true;
  }
  return false;
}

/// 순수 row 트리일 때만 역할 배치로 다시 짠다 — 사용자가 세로(col) 분할을 만든 배치는 무접촉.
/// (adoptLayoutIfRowOnly 와 같은 좁힘 규약 · 사용자 배치 존중은 그대로 유지한다.)
/// 반환값이 입력과 **같은 객체**면 아무것도 바꾸지 않았다는 뜻이다.
export function formationIfRowOnly(
  tree: LayoutNode,
  roleBySid: Map<number, string | null | undefined>,
): LayoutNode {
  if (!isRowOnly(tree)) return tree;
  const seats: Seat[] = sidsInOrder(tree).map((sid) => ({ sid, role: roleBySid.get(sid) ?? null }));
  return formationLayout(seats) ?? tree;
}
