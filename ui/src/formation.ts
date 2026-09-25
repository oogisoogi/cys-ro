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
  // leftAuto — 루트 가로 분할에만 붙는 표지: 「좌열 폭이 기본값이다(사람이 안 끌었다)」. 창 크기가 바뀌면 기본값을 다시 재고,
  //   사람이 그 경계를 끌면 main.ts 가 지운다(박사님 결정 09-25 14:5x · master#73a7390d).
  | { type: "split"; dir: "row" | "col"; ratio?: number; a: LayoutNode; b: LayoutNode; leftAuto?: boolean }
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

/// 좌열(master·cso)이 화면에서 갖는 가로 몫의 기본값 — **화면 전체 가로의 25% · 워커 수와 무관한 상수**.
/// ★박사님 결정 2026-09-25 14:5x(master#db159bcf): 「마스터 cso 좌우폭은 균등 정렬에서 뺀다. 워커들로 한정했다. 이것은
///   사용자가 정한 넓이를 그대로 유지하되, 사용자가 디폴트값을 사용한다면 전체 화면은 25%를 유지한다. 그래야 대화하기가 좋을 것 같다.」
/// (옛 규칙 leftColumnShare(n) = 워커 1대 1/2 · 2대+ 1/3 은 폐기 — 좌열 몫을 워커 수로 재는 자리는 이 상수 하나로 모였다.)
export const LEFT_SHARE_DEFAULT = 0.25;
/// 좌열이 이 글자 칸 수보다 좁아지면(노트북) 이 칸 수만큼 넓힌다 — 대화하기 편한 최소 폭(master#73a7390d 설계).
export const LEFT_MIN_COLS = 90;
/// 좌열 기본 폭의 상한(아주 좁은 창에서도 워커 쪽에 절반은 남긴다).
export const LEFT_SHARE_MAX = 0.5;
/// 좌열 기본 폭 = 창 가로의 25% · 단 글자 90칸보다 좁으면 90칸 · 상한 50%.
///   넓은 모니터 = 화면의 1/4 · 노트북 = 대화하기 편한 최소 폭(박사님 질문 「노트북과 모니터를 파악하여 비율을 조정할 수 있는가」).
///   rootPx = 창(배치 영역) 가로 픽셀 · cellPx = 터미널 글자 한 칸 폭 · chromePx = 칸 안에서 글자가 못 쓰는 가로 픽셀
///   (안쪽 여백·스크롤바·반올림 나머지 — master#94526717: 여백을 안 넣으면 1920px 에서 87칸으로 「최소 90칸」 미달이었다).
///   모르면(0·NaN) 25%.
export function defaultLeftShare(rootPx: number, cellPx: number, chromePx = 0): number {
  if (!(rootPx > 0) || !(cellPx > 0)) return LEFT_SHARE_DEFAULT;
  const chrome = Number.isFinite(chromePx) && chromePx > 0 ? chromePx : 0;
  return Math.min(LEFT_SHARE_MAX, Math.max(LEFT_SHARE_DEFAULT, (LEFT_MIN_COLS * cellPx + chrome) / rootPx));
}
/// 여백을 실제 칸에서 못 잴 때(칸이 아직 없다 · 숨겨져 있다)의 폴백 — CSS 기준: .term-host 좌우 padding 2px×2 + 경계 1px +
///   반올림 나머지 한 칸 몫 여유. 실측(헤드리스 13px)에서 잰 칸 여백보다 크게 잡는다(모자라는 쪽으로 어긋나지 않게).
export const LEFT_CHROME_FALLBACK_PX = 24;
/// 1.1.5 이하의 옛 기본 폭(leftColumnShare = 워커 1대 1/2 · 2대+ 1/3). 저장 배치의 루트가 표지 없이 이 값(±RULE_TOL)이면 「기본을 쓰던 사용자」로
///   보고 기본 폭 표지를 붙인다(master#73a7390d) — ★복원 때 **한 번만**(main.ts 플래그 · Fable 적대 2R ②: autoArrange 안에서 매번 보면
///   이 판에서 새로 1/2·1/3 에 끈 폭까지 영영 되돌렸다). 잔여 위험: 옛 판에서 손으로 정확히 1/2·1/3(±0.01)에 맞춘 드문 사용자도 옮겨진다.
export const OLD_DEFAULT_SHARES = [1 / 2, 1 / 3];
/// 「옛 기본값과 같다」의 허용 오차.
export const RULE_TOL = 0.01;
export function migrateOldDefaultShare(tree: LayoutNode): LayoutNode {
  if (tree.type !== "split" || tree.dir !== "row" || tree.leftAuto) return tree;
  const r = tree.ratio ?? 0.5;
  return OLD_DEFAULT_SHARES.some((v) => Math.abs(r - v) <= RULE_TOL) ? { ...tree, leftAuto: true } : tree;
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
    return { type: "split", dir: "row", ratio: LEFT_SHARE_DEFAULT, a: left, b: right, leftAuto: true };
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
//    화면 가로 몫은 **다시 재지 않는다**(박사님 결정 14:5x) — 사람이 끈 폭이면 그 폭 · 아니면 기본 폭(defaultLeftShare = 창의 25% ·
//    노트북이면 글자 90칸 · 상한 50%) + leftAuto 표지.
//    좌열을 못 찾아도 좌열 좌석이 좌열 좌석만 품은 기둥에 있으면(처음 배치 · row 뿐인 트리 · master·cso 가 좌우로 나란함 ·
//    위아래 비율 손상) 좌열만 표준(기본 폭 · master:cso = 4:1)으로 새로 짓고 워커 기둥은 그대로 둔다(v2).
//    좌열 좌석이 워커와 한 기둥에 섞였으면 아래 「무정렬」(v1 은 이때 formationLayout 표준으로 전부 다시 짜 사람 나눔을 지웠다).
//  · ★(v2 · 박사님 결정 09-25 14:1x 「사용자가 임의로 세로로 정렬한 것들도 그대로 유지한다. 오직 워커 페인들의 좌우폭만
//    균등하게 정렬한다」 · DESIGN-v2) 나머지 좌석은 「기둥」 단위로 본다 — 기둥 = 루트를 가로(row) 분할로 끝까지 펼친 단위
//    (칸 하나 또는 위아래 묶음). 워커 기둥은 **같은 객체 그대로**(안의 위아래 비율 무접촉) · 기둥끼리만 좌우 균등.
//    (v1 은 사람이 위아래로 나눈 것도 한 줄로 폈다 — 폐기.)
//  · 새 칸(add): dir 없음/"row" = after 가 든 기둥 바로 오른쪽 새 기둥 · dir "col"(세로 분할) = after 칸 바로 아래(같은 기둥 ·
//    기둥 수 불변 = 폭 불변). after 가 좌열이면 좌열 무접촉 → 워커 맨 왼쪽 새 기둥 · after 없음 → 맨 오른쪽.
//  · 닫기(remove): 그 자리에서 잘라내고 형제가 자리를 받는다(기둥 폭 불변) · 기둥이 통째로 사라지면 남은 기둥 재균등.
//  · 좌열 좌석이 워커와 한 기둥에 섞였으면(사람이 워커를 master 아래에 넣음 · 좌열이 위아래 분할 속 · 역할이 바뀜) 맞출 수 없다 —
//    **무정렬**: 그 자리 접힘·반 나눔·루트 오른쪽 덧붙임만(사람 위아래 나눔을 지우지 않는다 · v1 은 표준으로 다시 짜 지웠다).
//  · master·cso 가 없으면 기둥 전부 좌우 균등(우리 개발 기기 · 07-27 오너 확정 「개수 무관 1행 가로 균등」의 기둥판).
//  · ★좌석 집합 보존: 결과의 sid 집합 = (입력 − remove) ∪ add. 이 함수는 좌석을 지우거나 만들지 않는다 —
//    트리에서 빠진 좌석은 「살아 있는데 안 보이는 좌석」이 되기 때문이다(4군 ④).
//  · 죽은 좌석·자리표·역할 모르는 셸: 역할이 없으면 워커 칸과 같이 오른쪽 줄에 선다. 끝난(exited) 좌석을 빼는 것은
//    호출자의 remove 몫이다(이 함수는 생존을 모른다).
//
// 왜 add/remove 를 인자로 받나: 호출자가 먼저 트리를 감싸거나(입양의 0.5 래퍼) 잘라내면(replaceNode 의 형제 흡수)
//   좌열의 화면 몫이 그 순간 바뀌어 「지금 비율」을 잃는다. 바뀌기 **전** 트리에서 몫을 재야 한다.

export type ArrangeChange = {
  /// 새로 붙는 좌석. `after` 가 트리에 있으면 그 칸이 든 기둥 바로 오른쪽 새 기둥(dir "col" = 그 칸 바로 아래 · 같은 기둥),
  /// 없으면 맨 끝(오른쪽) 새 기둥.
  add?: { sid: number; after?: number; dir?: "row" | "col" }[];
  /// 빠지는 좌석(닫기 · 외부 닫힘 · 자리표 회수 · 죽은 좌석 정리).
  remove?: number[];
};

/// 좌열 가로 몫 정책(★박사님 결정 2026-09-25 14:5x · master#db159bcf — 옛 D1 = C 「규칙값이면 다시 잰다」 폐기).
///  · "auto"(기본) = 사람이 끈 좌열 폭은 **절대 다시 재지 않는다** — 열기·닫기·세로 분할 어느 때도(루트 왼쪽 직계 · 끌기 범위 안 ·
///    leftAuto 표지 없음 · 옛 기본값 아님). 그 밖(처음 배치 · 좌열을 새로 짓는 경우 · 좌열뿐이던 화면 · 깊은 길 · leftAuto 표지 ·
///    옛 기본값 1/2·1/3)은 기본 폭 defaultShare(호출자가 창 크기로 잰 defaultLeftShare) + leftAuto 표지.
///  · "standard" = 정렬 단추 — 좌열 기본 폭 + master:cso 4:1 + 나머지 한 줄 균등(표준으로 새로).
///  · master:cso 위아래 비율은 auto 에서 **트리 값 그대로**(standard 만 4:1 로 새로).
export type LeftShareMode = "auto" | "standard";
/// 사람이 칸 경계를 끌 수 있는 범위(main.ts 경계 끌기 = Math.min(0.85, Math.max(0.15, …)) 와 같은 값).
/// ★「사람이 끈 값」은 좌열이 **루트의 왼쪽 직계 자식**이고 몫이 이 범위 안일 때만이다 — 이 함수와 경계 끌기가 만들 수 있는
///   모양이 그것뿐이다. 더 깊은 길(옛 입양·창 옮기기의 0.5 감싸기)이 만든 몫은 사람 값이 아니므로 표준으로 다시 잰다
///   (Opus 적대 1R F1 실측: R1 잔재 트리 0.25 · 창 옮기기 뒤 1/6 이 사람 값으로 오독돼 영구 고정됐다).
export const DRAG_MIN = 0.15;
export const DRAG_MAX = 0.85;

type RoleMap = Map<number, string | null | undefined>;

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

// 좌열 좌석 = 계열마다 **sid 가 가장 작은** master 계열 + cso 계열. 트리 위치·붙는 순서와 무관한 고르기라 같은 좌석 집합이면
//   언제나 같은 좌열이다(Fable 적대 2R ③ — 「있던 좌석 먼저 · 순서 첫」은 한 번 배치한 뒤 다시 부르면 좌열이 바뀌었다).
//   sid 는 만든 순서로 늘어나므로 보통은 먼저 선 좌석 = 옛 「순서 첫」과 같다.
function leftSids(order: number[], roles: RoleMap): number[] {
  const pick = (f: "master" | "cso") => order.filter((s) => family(roles.get(s)) === f).sort((x, y) => x - y)[0];
  return [pick("master"), pick("cso")].filter((s): s is number => s !== undefined);
}

// (v2) 기둥 목록 — 루트를 가로(row) 분할로 끝까지 펼친다. 가로 분할이 아닌 서브트리(칸 · 위아래 묶음)가 기둥 하나.
function rowUnits(n: LayoutNode, out: LayoutNode[] = []): LayoutNode[] {
  if (n.type === "split" && n.dir === "row") { rowUnits(n.a, out); rowUnits(n.b, out); }
  else out.push(n);
  return out;
}

// (v2) 빠지는 좌석을 그 자리에서 잘라낸다 — 형제가 자리를 받는다(replaceNode 의 접힘과 같다). 같은 sid 가 두 번 나오면
//   뒤엣것을 뺀다(좌석 중복 0). 바뀐 것이 없는 서브트리는 **같은 객체**로 돌려준다(사람 배치 무접촉의 근거).
function prune(n: LayoutNode, drop: Set<number>, seen: Set<number>): LayoutNode | null {
  if (n.type === "pane") {
    if (drop.has(n.sid) || seen.has(n.sid)) return null;
    seen.add(n.sid);
    return n;
  }
  const a = prune(n.a, drop, seen);
  const b = prune(n.b, drop, seen);
  if (a && b) return a === n.a && b === n.b ? n : { ...n, a, b };
  return a ?? b;
}

// (v2) 손상 비율(0·1·NaN·범위 밖 — 끌기로는 못 만드는 값)만 0.5 로 · 멀쩡하면 같은 객체(Fable 적대 1R R3).
function heal(n: LayoutNode): LayoutNode {
  if (n.type === "pane") return n;
  const a = heal(n.a);
  const b = heal(n.b);
  const bad = n.ratio !== undefined && !(Number.isFinite(n.ratio) && n.ratio > 0 && n.ratio < 1);
  return !bad && a === n.a && b === n.b ? n : { ...n, a, b, ...(bad ? { ratio: 0.5 } : {}) };
}

// (v2) target 칸을 make(칸)으로 바꾼다 — 나머지는 같은 객체.
function replacePane(n: LayoutNode, target: number, make: (p: LayoutNode) => LayoutNode): LayoutNode {
  if (n.type === "pane") return n.sid === target ? make(n) : n;
  const a = replacePane(n.a, target, make);
  const b = replacePane(n.b, target, make);
  return a === n.a && b === n.b ? n : { ...n, a, b };
}

// (v2) 맞출 수 없는 모양(좌열 좌석이 워커와 한 기둥에 섞임)의 최소 변경 — 사람 배치를 지우지 않는다.
//   닫기 = 그 자리 접힘 · after 가 있는 열기 = after 칸을 dir 방향으로 반 나눔(1.1.6 이전 분할과 같다) ·
//   after 없는 열기 = 루트 오른쪽 새 칸(몫 1/(기둥+1) — 나머지 비율은 그대로 줄어든다).
function minimalChange(tree: LayoutNode | null, change: ArrangeChange, drop: Set<number>): LayoutNode | null {
  const seen = new Set<number>();
  let t = tree ? prune(tree, drop, seen) : null;
  for (const { sid, after, dir } of change.add ?? []) {
    if (seen.has(sid)) continue;
    seen.add(sid);
    const p: LayoutNode = { type: "pane", sid };
    if (!t) t = p;
    else if (after !== undefined && after !== sid && sidsInOrder(t).includes(after)) {
      t = replacePane(t, after, (old) => ({ type: "split", dir: dir ?? "row", ratio: 0.5, a: old, b: p }));
    } else {
      const k = rowUnits(t).length;
      t = { type: "split", dir: "row", ratio: k / (k + 1), a: t, b: p };
    }
  }
  return t ? heal(t) : t; // 손상 비율만 0.5 로(끌기로 못 만드는 값 — 사람 배치가 아니다)
}

/// 역할을 모를 때(그 데몬의 목록을 한 번도 못 받았다)의 열기·닫기 — 다시 짜지 않고 그 자리 접힘·반 나눔·오른쪽 덧붙임만(Fable 적대 2R ①).
export function arrangeWithoutRoles(tree: LayoutNode | null, change: ArrangeChange = {}): LayoutNode | null {
  return minimalChange(tree, change, new Set(change.remove ?? []));
}

/// 자동 정렬. 반환 `null` = 좌석이 하나도 없다(빈 탭).
export function autoArrange(
  tree: LayoutNode | null,
  roles: RoleMap,
  change: ArrangeChange = {},
  mode: LeftShareMode = "auto",
  defaultShare: number = LEFT_SHARE_DEFAULT,
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

  // 좌열 좌석 = 계열마다 가장 작은 sid(leftSids) — 새로 붙는 둘째 master 가 after 때문에 앞에 서도 기존 좌열을 밀어내지 않는다(Fable 1R R2).
  const left = leftSids(order, roles);
  const rest = order.filter((s) => !left.includes(s));
  if (mode === "standard") {
    // 정렬 단추 = 종전 표준 그대로(좌열 4:1 · 나머지 한 줄 균등 — 사람이 누르는 것이라 위아래 나눔도 편다).
    if (left.length === 0) return evenRow(rest.map(pane));
    const std: LayoutNode =
      left.length === 2 ? { type: "split", dir: "col", ratio: MASTER_CSO_RATIO, a: pane(left[0]), b: pane(left[1]) } : pane(left[0]);
    return rest.length === 0 ? std : { type: "split", dir: "row", ratio: defaultShare, a: std, b: evenRow(rest.map(pane)), leftAuto: true };
  }

  // (v2) 기둥 — 입력 트리의 기둥마다 빠지는 좌석을 그 자리에서 잘라낸다. 잘린 기둥이 가로 조각으로 남으면 조각을 기둥으로 편다.
  const isLeft = (s: number) => left.includes(s);
  const seen = new Set<number>();
  const units: LayoutNode[] = [];
  for (const u of tree ? rowUnits(tree) : []) {
    const p = prune(u, drop, seen);
    if (p) rowUnits(p, units);
  }
  // 역할 표가 비어 있는데(데몬이 아직 목록을 안 줬다) 기본 폭 표지가 있는 트리 = 역할을 모르는 것이지 본부가 없는 것이 아니다 →
  //   다시 짜지 않는다(Fable 적대 2R ① 의 벨트 · 본 방어는 main.ts arrangeWs 의 「역할 표 없음 → arrangeWithoutRoles」).
  //   ★「본부 역할 0명」으로 넓히지 마라(Fable 3R ①): 옛 기본 이동이 워커만 있는 탭에도 표지를 붙이므로 그 탭의 닫기가 형제 독차지가 됐다.
  const rolesBlind = tree !== null && tree.type === "split" && tree.leftAuto === true && roles.size === 0;
  // 맞출 수 있는가 = 좌열 좌석을 품은 기둥은 좌열 좌석만 품는다. 아니면 무정렬(사람 위아래 나눔을 지우지 않는다).
  const fits = !rolesBlind && units.every((u) => {
    const us = sidsInOrder(u);
    return !us.some(isLeft) || us.every(isLeft);
  });
  if (!fits) return minimalChange(tree, change, drop);

  // 워커 기둥 + 새 칸 — after 가 든 기둥 바로 오른쪽(세로 분할 = 그 칸 아래) · after 가 좌열이면 맨 왼쪽 · 없으면 맨 오른쪽.
  const workers = units.filter((u) => !sidsInOrder(u).some(isLeft)).map(heal);
  for (const { sid, after, dir } of change.add ?? []) {
    if (seen.has(sid)) continue;
    seen.add(sid);
    if (isLeft(sid)) continue; // 좌열로 들어간다(아래 leftNode)
    const i = after === undefined ? -1 : workers.findIndex((u) => sidsInOrder(u).includes(after));
    if (i >= 0 && dir === "col") {
      workers[i] = replacePane(workers[i], after!, (old) => ({ type: "split", dir: "col", ratio: 0.5, a: old, b: pane(sid) }));
    } else if (i >= 0) workers.splice(i + 1, 0, pane(sid));
    else if (after !== undefined && isLeft(after) && seen.has(after)) workers.unshift(pane(sid));
    else workers.push(pane(sid));
  }
  if (left.length === 0) return evenRow(workers);

  // 입력 트리의 좌열을 찾는다 — 입력 기준 좌열 좌석을 정확히 그것만 덮는 온전한 세로 열이어야 한다.
  let keptLeft: LayoutNode | null = null;
  let share: number | null = null;
  if (tree) {
    const inLeft = leftSids(inOrder, roles);
    // 입력 좌열 좌석을 모두 품은 기둥 — 그 안에서 닫히는 워커는 먼저 잘라 낸 뒤 좌열인지 본다(Fable 적대 1R R1:
    //   사람이 워커를 cso 아래에 넣었다가 닫으면 남는 것은 사람이 끈 좌열이다 · 잘라 내기 전에 보면 표준으로 돌아갔다).
    const pil = inLeft.length > 0 ? rowUnits(tree).find((u) => { const us = sidsInOrder(u); return inLeft.every((s) => us.includes(s)); }) : undefined;
    const sub = pil ? prune(pil, new Set([...drop].filter((s) => !inLeft.includes(s))), new Set()) : null;
    if (pil && sub) {
      const subSids = sidsInOrder(sub);
      const exact = subSids.length === inLeft.length && inLeft.every((s) => subSids.includes(s));
      // 좌열 모양 = 칸 하나이거나 위아래(col) 둘. master·cso 가 좌우(row)로 나란한 것은 좌열이 아니다 —
      //   옛 판 배치(1.0.x adoptLayout = 가로 comb)나 창 옮기기가 남긴 모양이다 → 표준으로(헤드리스 c18 전체 실행이 적발).
      // 위아래 비율이 손상된 저장 배치(NaN·0·1)는 좌열로 보지 않는다(Opus 적대 1R F4) — 끌기로는 못 만드는 값이다.
      const okRatio = (r?: number) => r === undefined || (Number.isFinite(r) && r > 0 && r < 1);
      const colShaped = sub.type === "pane" || (sub.dir === "col" && okRatio(sub.ratio));
      const cs = exact && colShaped ? columnShare(tree, pil) : null;
      if (cs !== null) {
        // 좌열 구성이 그대로면 그 서브트리를 보존한다(위아래 비율 포함). 좌열 좌석이 빠지거나 새로 들어오면
        //   좌열만 표준으로 다시 짓되 몫은 이어받는다 — 좌석 하나 남은 좌열은 칸 하나라 비율이 없다.
        if (subSids.length === left.length && left.every((s) => subSids.includes(s))) keptLeft = sub;
        // (알아본 좌열의 윗칸은 언제나 master 또는 cso 다 — 「cso 가 아님」과 「master」는 같은 조건이라 뮤턴트 M31 이 등가로 드러났다.
        //  유령 수렴 뒤 옛 master 역할을 잃는 문제의 실제 봉합은 main.ts rememberRoles 의 이어 기억이다.)
        else if (sub.type === "split" && left.length === 2 && family(roles.get(sidsInOrder(sub.a)[0])) === "master") {
          // 첫 master 가 닫히고 master-2 가 올라온 경우 등 — 좌열 사람이 바꾼 위아래 비율은 이어받는다(Opus 적대 1R F4).
          keptLeft = { type: "split", dir: "col", ratio: sub.ratio ?? 0.5, a: pane(left[0]), b: pane(left[1]) };
        }
        const direct = tree.type === "split" && tree.dir === "row" && tree.a === pil;
        // 사람이 끈 폭이면 언제나 그대로(박사님 결정 14:5x · 옛 D1 = C 의 「규칙값이면 다시 잰다」와 v2 규칙 5 는 폐기).
        // leftAuto 표지(기본 폭) = 새 기본 폭으로(옛 1/2·1/3 은 복원 때 한 번 migrateOldDefaultShare 가 표지로 바꾼다).
        const wasDefault = (tree as { leftAuto?: boolean }).leftAuto === true;
        if (direct && !wasDefault && cs >= DRAG_MIN && cs <= DRAG_MAX) share = cs;
      }
    }
  }
  const leftNode =
    keptLeft ??
    (left.length === 2
      ? { type: "split" as const, dir: "col" as const, ratio: MASTER_CSO_RATIO, a: pane(left[0]), b: pane(left[1]) }
      : pane(left[0]));
  if (workers.length === 0) return leftNode;
  // 몫이 없으면(좌열 미발견·좌열이 화면 전체였다·사람 값이 아닌 깊은 길·기본 폭 표지·옛 기본값) 기본 폭 + 표지.
  return share === null
    ? { type: "split", dir: "row", ratio: defaultShare, a: leftNode, b: evenRow(workers), leftAuto: true }
    : { type: "split", dir: "row", ratio: share, a: leftNode, b: evenRow(workers) };
}
