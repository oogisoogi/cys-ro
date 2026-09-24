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

// ───────────────────────────────────────────────────────────────────────────────────────────
// autoArrange — 창을 열고 닫을 때마다 자동 좌우 균등 정렬(TICKET=v116-auto-equalize · 오너 지시 2026-09-25 05:2x).
//
// 오너 원문: 「1. 마스터 cso는 지금 비율 그대로 둔다. 2. 워커들 창(페인)은 사용자가 거의 볼 일이 없다.
//   따라서 마스터가 창을 열고 닫을 때, 그리고 사용자가 열고 닫을 때 존재하는 페인들 모두 자동으로 좌우 균등 정렬한다.」
//
// 왜 formationIfRowOnly 로는 안 되나(재현 2026-09-25): HQ 기기에서 첫 배치가 좌열을 세로(col)로 나누는 순간
//   isRowOnly 가 거짓이 되어 그 뒤 입양은 다시 짜이지 않았다(새 워커 = 화면 절반 · master 0.20 · cso 0.05).
//   닫기는 아예 배치를 부르지 않아 형제가 자리를 독차지했다(워커 3 중 가운데 닫기 → 1/3 : 2/3).
//
// 규칙
//  · 좌열(첫 master 계열 + 첫 cso 계열) = 입력 트리의 그 서브트리를 **그대로** 둔다(위아래 비율 포함).
//    화면 가로 몫은 LeftShareMode "auto" 를 따른다(규칙값이면 새 워커 수로 다시 · 사람이 끈 값이면 그대로 — master 판정 D1 = C).
//    좌열을 못 찾으면(처음 배치 · 좌석이 흩어짐 · 좌열 안에 다른 좌석이 끼어 있음 · 좌열이 위아래 분할 속에 있음 ·
//    master·cso 가 좌우로 나란함)
//    formationLayout 표준(좌열 몫 leftColumnShare · master:cso = 4:1)으로 만든다.
//  · 나머지 좌석 전부 = 한 줄 좌우 균등. 좌→우 순서 = 입력 트리 순회 순서(사람이 위아래로 나눠 둔 것도 한 줄로 편다).
//  · master·cso 가 없으면 전부 한 줄 좌우 균등(우리 개발 기기 · 07-27 오너 확정 「개수 무관 1행 가로 균등」).
//  · ★좌석 집합 보존: 결과의 sid 집합 = (입력 − remove) ∪ add. 이 함수는 좌석을 지우거나 만들지 않는다 —
//    트리에서 빠진 좌석은 「살아 있는데 안 보이는 좌석」이 되기 때문이다(4군 ④).
//  · 죽은 좌석·자리표·역할 모르는 셸: 역할이 없으면 워커 칸과 같이 오른쪽 줄에 선다. 끝난(exited) 좌석을 빼는 것은
//    호출자의 remove 몫이다(이 함수는 생존을 모른다).
//
// 왜 add/remove 를 인자로 받나: 호출자가 먼저 트리를 감싸거나(입양의 0.5 래퍼) 잘라내면(replaceNode 의 형제 흡수)
//   좌열의 화면 몫이 그 순간 바뀌어 「지금 비율」을 잃는다. 바뀌기 **전** 트리에서 몫을 재야 한다.

export type ArrangeChange = {
  /// 새로 붙는 좌석. `after` 가 트리에 있으면 그 바로 다음 순서에, 없으면 맨 끝(오른쪽)에 선다.
  add?: { sid: number; after?: number }[];
  /// 빠지는 좌석(닫기 · 외부 닫힘 · 자리표 회수 · 죽은 좌석 정리).
  remove?: number[];
};

/// 좌열 가로 몫 정책(★master 판정 D1 = C · 2026-09-25 master#c443981e).
///  · "auto"(기본) = 입력 트리의 좌열 몫이 **직전 워커 수의 규칙값** leftColumnShare(이전 n)과 같으면(±RULE_TOL)
///    사람이 안 건드린 것 → 새 워커 수의 규칙값으로 다시 잰다 · 다르면 사람이 끈 값 → 그대로 보존.
///    (A「언제나 보존」은 첫 부팅에서 워커가 한 대씩 늘 때 첫 값 1/2 이 영구 고정됐고,
///     B「언제나 규칙값」은 사람이 넓힌 master 폭을 매번 되돌렸다 — 둘 다 피한다.)
///  · "standard" = 좌열까지 표준으로 새로 짠다(정렬 단추 = 종전 formationLayout 과 같은 결과 · 기존 기능 보존).
///  · master:cso 위아래 비율은 두 정책 모두 **트리 값 그대로**(standard 만 4:1 로 새로).
export type LeftShareMode = "auto" | "standard";
/// 「규칙값과 같다」의 허용 오차 — 규칙값끼리의 최소 간격(1/2 ↔ 1/3 = 0.167)보다 충분히 작다.
export const RULE_TOL = 0.01;

type RoleMap = Map<number, string | null | undefined>;

// 좌석 집합을 전부 덮는 가장 작은 서브트리.
function coveringSubtree(n: LayoutNode, want: Set<number>): LayoutNode {
  if (n.type === "pane") return n;
  const inA = new Set(sidsInOrder(n.a));
  if ([...want].every((s) => inA.has(s))) return coveringSubtree(n.a, want);
  const inB = new Set(sidsInOrder(n.b));
  if ([...want].every((s) => inB.has(s))) return coveringSubtree(n.b, want);
  return n;
}

// 루트에서 target 까지 내려가며 가로 몫을 곱한다. 길에 세로(col) 분할이 있으면 null(= 온전한 세로 열이 아니다).
function columnShare(root: LayoutNode, target: LayoutNode): number | null {
  let share = 1;
  let n = root;
  while (n !== target) {
    if (n.type === "pane") return null;
    const r = n.ratio ?? 0.5;
    const inA = contains(n.a, target);
    if (!inA && !contains(n.b, target)) return null;
    if (n.dir !== "row") return null;
    share *= inA ? r : 1 - r;
    n = inA ? n.a : n.b;
  }
  return share;
}
function contains(n: LayoutNode, t: LayoutNode): boolean {
  if (n === t) return true;
  return n.type === "split" && (contains(n.a, t) || contains(n.b, t));
}

// 좌열 좌석 = 순서상 첫 master 계열 + 첫 cso 계열(formationLayout 과 같은 고르기).
function leftSids(order: number[], roles: RoleMap): number[] {
  const m = order.find((s) => family(roles.get(s)) === "master");
  const c = order.find((s) => family(roles.get(s)) === "cso");
  return [m, c].filter((s): s is number => s !== undefined);
}

/// 자동 정렬. 반환 `null` = 좌석이 하나도 없다(빈 탭).
export function autoArrange(
  tree: LayoutNode | null,
  roles: RoleMap,
  change: ArrangeChange = {},
  mode: LeftShareMode = "auto",
): LayoutNode | null {
  const inOrder = tree ? sidsInOrder(tree) : [];
  const drop = new Set(change.remove ?? []);
  // 최종 좌석 순서 — 중복 제거 · add 는 after 다음(없으면 끝).
  const order: number[] = [];
  for (const s of inOrder) if (!drop.has(s) && !order.includes(s)) order.push(s);
  for (const { sid, after } of change.add ?? []) {
    if (order.includes(sid)) continue;
    const i = after === undefined ? -1 : order.indexOf(after);
    if (i >= 0) order.splice(i + 1, 0, sid);
    else order.push(sid);
  }
  if (order.length === 0) return null;
  const pane = (sid: number): LayoutNode => ({ type: "pane", sid });

  const left = leftSids(order, roles);
  const rest = order.filter((s) => !left.includes(s));
  if (left.length === 0) return evenRow(rest.map(pane));

  // 입력 트리의 좌열을 찾는다 — 입력 기준 좌열 좌석을 정확히 그것만 덮는 온전한 세로 열이어야 한다.
  let keptLeft: LayoutNode | null = null;
  let share: number | null = null;
  let untouched = false; // 좌열 몫이 직전 규칙값 그대로였다(사람 손 안 탐)
  if (tree && mode !== "standard") {
    const inLeft = leftSids(inOrder, roles);
    if (inLeft.length > 0) {
      const sub = coveringSubtree(tree, new Set(inLeft));
      const subSids = sidsInOrder(sub);
      const exact = subSids.length === inLeft.length && inLeft.every((s) => subSids.includes(s));
      // 좌열 모양 = 칸 하나이거나 위아래(col) 둘. master·cso 가 좌우(row)로 나란한 것은 좌열이 아니다 —
      //   옛 판 배치(1.0.x adoptLayout = 가로 comb)나 창 옮기기가 남긴 모양이다 → 표준으로(헤드리스 c18 전체 실행이 적발).
      const colShaped = sub.type === "pane" || sub.dir === "col";
      const cs = exact && colShaped ? columnShare(tree, sub) : null;
      if (cs !== null) {
        // 좌열 구성이 그대로면 그 서브트리를 보존한다(위아래 비율 포함). 좌열 좌석이 빠지거나 새로 들어오면
        //   좌열만 표준으로 다시 짓되 몫은 이어받는다 — 좌석 하나 남은 좌열은 칸 하나라 비율이 없다.
        if (subSids.length === left.length && left.every((s) => subSids.includes(s))) keptLeft = sub;
        share = cs;
        const prevRest = inOrder.length - inLeft.length;
        untouched = prevRest > 0 && Math.abs(cs - leftColumnShare(prevRest)) <= RULE_TOL;
      }
    }
  }
  const leftNode =
    keptLeft ??
    (left.length === 2
      ? { type: "split" as const, dir: "col" as const, ratio: MASTER_CSO_RATIO, a: pane(left[0]), b: pane(left[1]) }
      : pane(left[0]));
  if (rest.length === 0) return leftNode;
  // 몫이 없거나(표준·좌열 미발견) 퇴화면(좌열이 화면 전체였다 = 워커가 처음 생긴다) 표준 몫.
  // 사람 손을 안 탄 몫은 새 워커 수의 규칙값으로(D1 = C).
  if (untouched || share === null || !(share > 0 && share < 1)) share = leftColumnShare(rest.length);
  return { type: "split", dir: "row", ratio: share, a: leftNode, b: evenRow(rest.map(pane)) };
}
