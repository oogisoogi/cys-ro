// 3초 고리의 판정(decide) — TICKET=cysr-1116-s2-1119 · P2-DESIGN §2-1 ㉠ 「한 틱 = 모으기 → 판정 → 모형 반영 → 그리기」.
//
// ★이 파일은 순수다(§3-3 규칙 ①): 화면 문서·창·앱 저장소·Tauri·지금 시각·타이머를 쓰지 않는다. 시각이 필요한 판정(스윕 범위)은
//   모으기 단계(main.ts)가 끝내 결과(범위 번호)만 넘긴다. 정적 검사 = views/judge/tick.test.ts 「순수성」.
//
// ★무엇을 판정하나 — main.ts refreshPaneTitles 가 소켓마다 하던 판정 넷(종전에는 집행과 한 반복문에 섞여 있었다):
//   ① 유령 퇴거(wsreconcile.advanceGhostStrikes 그대로) ② 옛 자리 쓸기(exitedsweep.exitedSweepTargets 그대로)
//   ③ 역할 좌석 자동 입양 후보(종전 main.ts 입양 반복문의 조건을 여기로 옮김 — 「후보 고르기」와 「런타임 만들기」를 가름)
//   ④ 빈 자리표 회수(placeholderclose.shouldClosePlaceholder 그대로 · 입력 칸을 만드는 식만 여기 하나 — 조각 0 의 두 벌을 접음)
//   집행(퇴거·쓸기 = detachPane · 입양 = 모형에 붙이기 + 런타임 · 회수 = closePane)은 main.ts 에 그대로 있다(§8-2 ③ 「판정은 옮기고 집행은 제자리」).
//
// ★「같은 입력 → 같은 판정」(§2-1 시험 ②): decideTick 은 조각 0 기록기(views/tickrec.ts)가 남긴 한 칸을 그대로 받아 같은 판정을 다시 낸다 —
//   tick.test.ts 가 견본 덤프 200틱과 e2e 새 덤프로 바이트 대조한다. 그래서 이 파일의 입력 꼴은 기록기의 칸 이름을 따른다.
//
// ★관측값은 입력으로(1회 고침 F18): 자리표 화면 줄 수는 모으기 단계가 읽어 `lineCount` 로 넘긴다. 런타임이 미뤄진 좌석은 화면이 없어
//   null — placeholderclose 규칙대로 「모르면 닫지 않는다」(= 회수 판정 보류 · 장부에서 빼지 않음 → 런타임이 생긴 뒤 다시 판정).

import { advanceGhostStrikes } from "../../wsreconcile";
import { exitedSweepTargets } from "../../exitedsweep";
import { shouldClosePlaceholder } from "../../placeholderclose";

/** 판정이 보는 작업공간 한 개(모형 사본 · 트리는 번호 목록만). sock = 소켓 열쇠(기본 데몬 = ""). */
export interface TickWs {
  id: number;
  sock: string;
  pending: boolean;
  deleting: boolean;
  sids: number[];
}

/** 판정이 보는 좌석 목록 한 줄(list_surfaces 의 칸 중 판정이 쓰는 것만). */
export interface TickSurface {
  surface_id: number;
  role: string | null;
  exited: boolean;
}

/** 자리표 회수 판정 입력(placeholderclose.PlaceholderDecision 과 같은 칸). */
export interface PlaceholderIn {
  isOwnPlaceholder: boolean;
  touched: boolean;
  role: string | null;
  lineCount: number | null;
  isWindows: boolean;
  formationArrived: boolean;
  exited: boolean;
}

/** 한 소켓 앞 판정(유령·쓸기·입양 후보)의 결과. */
export interface SockPrePlan {
  /** 퇴거 전 그 소켓 전 작업공간 트리 합집합(유령 판정 입력 그대로 · 기록 대조용). */
  tree: number[];
  evict: number[];
  ghostNext: Map<string, number>;
  /** 이 패스가 그 소켓을 쓸었는가(무장 범위 안) — 무장 정리(settleSweep)의 입력. */
  sweepHere: boolean;
  sweepScope: number[];
  sweepTargets: number[];
  /** 입양 순서 그대로(역할 우선순위 master>cso>worker>reviewer · 같은 순위는 목록 순). wsId = 붙일 작업공간. */
  adopt: { sid: number; role: string; wsId: number }[];
}

/** 역할 우선순위 — 부서 첫 입양 때 master 가 첫 pane(좌측·focus)이 되도록(종전 main.ts rolePri 그대로). */
export function rolePri(role: string | null): number {
  return role === "master" ? 0 : role === "cso" ? 1 : role?.startsWith("worker") ? 2 : role?.startsWith("reviewer") ? 3 : 4;
}

/** 입양할 작업공간 — 그 소켓의 첫(목록 순) 살아 있는 작업공간(대기 중·삭제 중 제외 · 종전 homeOf 그대로). */
export function homeWsOf<W extends { pending?: boolean; deleting?: boolean }>(
  ws: readonly W[],
  sameSock: (w: W) => boolean,
): W | undefined {
  return ws.find((w) => !w.pending && !w.deleting && sameSock(w));
}

/**
 * 한 소켓의 앞 판정. 집행 순서(퇴거 → 쓸기 → 입양)를 모형 사본 위에서 그대로 밟는다 — 입양 후보가 퇴거·쓸기 뒤의 트리를 보게.
 * known = 그 소켓에서 이미 화면 모형에 붙은 좌석(런타임 있음 ∪ 런타임 미룸) · 입력 ws·known 은 바꾸지 않는다.
 */
export function decideSockPre(input: {
  sock: string;
  ws: readonly TickWs[];
  surfaces: readonly TickSurface[];
  ghostStrike: ReadonlyMap<string, number>;
  /** 이 소켓의 스윕 무장 범위(null = 이 소켓은 무장 밖) — 모으기 단계가 sweepScopeFor 로 낸 값. */
  sweepScope: ReadonlySet<number> | null;
  known: ReadonlySet<number>;
  /** paneKey 꼴 열쇠(유령 카운터 키) — 기본 = `${sock}#${sid}`(main.ts paneKey 와 같은 꼴). */
  keyOf?: (sid: number) => string;
}): SockPrePlan {
  const { sock } = input;
  const keyOf = input.keyOf ?? ((sid: number) => `${sock}#${sid}`);
  const ws = input.ws.map((w) => ({ ...w, sids: [...w.sids] }));
  const known = new Set(input.known);
  const same = (w: TickWs) => w.sock === sock;
  // ① 유령 — 그 소켓 전 작업공간 트리 합집합(대기·삭제 중 포함 · 종전 호출 계약 그대로)
  const tree: number[] = [];
  for (const w of ws) if (same(w)) tree.push(...w.sids);
  const knownIds = new Set(input.surfaces.map((s) => s.surface_id));
  const g = advanceGhostStrikes(input.ghostStrike, tree, knownIds, keyOf, `${sock}#`);
  const detach = (sid: number) => {
    known.delete(sid);
    for (const w of ws) if (same(w) && w.sids.includes(sid)) w.sids = w.sids.filter((x) => x !== sid);
  };
  for (const sid of g.evict) detach(sid);
  // ② 옛 자리 쓸기 — 범위 = 퇴거 전 합집합 ∩ 무장 범위(종전 sockSids.filter 그대로)
  const sweepHere = input.sweepScope !== null;
  const scope = input.sweepScope;
  const sweepScope = scope ? tree.filter((sid) => scope.has(sid)) : [];
  const sweepTargets = exitedSweepTargets(sweepHere, sweepScope, input.surfaces);
  for (const sid of sweepTargets) detach(sid);
  // ③ 입양 후보 — 종전 반복문의 건너뛰기 조건 그대로(끝남 · 역할 없음 · 이미 붙음 · 집 없음 · 집 트리에 이미 있음)
  const adopt: SockPrePlan["adopt"] = [];
  for (const s of [...input.surfaces].sort((a, b) => rolePri(a.role) - rolePri(b.role))) {
    if (s.exited || !s.role || known.has(s.surface_id)) continue;
    const home = homeWsOf(ws, same);
    if (!home || home.sids.includes(s.surface_id)) continue;
    home.sids.push(s.surface_id);
    known.add(s.surface_id);
    adopt.push({ sid: s.surface_id, role: s.role, wsId: home.id });
  }
  return { tree, evict: g.evict, ghostNext: g.next, sweepHere, sweepScope, sweepTargets, adopt };
}

/** 자리표 회수 판정 한 건(입력 + 결과 · 기록 대조용). */
export interface PlaceholderVerdict {
  wsId: number;
  sid: number;
  in: PlaceholderIn;
  close: boolean;
}

/**
 * 한 소켓의 자리표 회수 판정 — 입양을 모형에 붙인 **뒤**의 트리로 한다(편성 도착 = 그 탭에 산 역할 좌석).
 * 대상 = 그 소켓의 대기 중 아닌 작업공간(삭제 중은 포함 · 종전 조건 그대로) · 장부(placeholders)에 있는 번호만(ⓐ 남의 페인 불가침).
 * lineCount(sid) = 모으기 단계가 읽은 화면 줄 수(런타임 없으면 null).
 */
export function decidePlaceholders(input: {
  sock: string;
  ws: readonly TickWs[];
  surfaces: readonly TickSurface[];
  placeholders: ReadonlySet<number>;
  touched: ReadonlySet<number>;
  lineCount: (wsId: number, sid: number) => number | null;
  isWindows: boolean;
}): PlaceholderVerdict[] {
  const out: PlaceholderVerdict[] = [];
  if (!input.placeholders.size) return out;
  const left = new Set(input.placeholders);
  for (const w of input.ws) {
    if (w.pending || w.sock !== input.sock) continue;
    const sids = w.sids;
    const formationArrived = input.surfaces.some((x) => !x.exited && !!x.role && sids.includes(x.surface_id));
    for (const sid of sids) {
      if (!left.has(sid)) continue; // ⓐ 남의 페인은 여기서 이미 걸러진다
      const su = input.surfaces.find((x) => x.surface_id === sid);
      const d: PlaceholderIn = {
        isOwnPlaceholder: left.has(sid),
        touched: input.touched.has(sid),
        role: su?.role ?? null,
        lineCount: input.lineCount(w.id, sid),
        isWindows: input.isWindows,
        formationArrived,
        exited: su?.exited ?? true,
      };
      const close = shouldClosePlaceholder(d);
      if (close) left.delete(sid); // 한 번 판정한 자리는 장부에서 뺀다(종전 그대로 · 같은 패스 재판정 0)
      out.push({ wsId: w.id, sid, in: d, close });
    }
  }
  return out;
}

// ── 기록 재생(조각 0 덤프 한 칸 → 같은 판정) ─────────────────────────────────────────────

type J = unknown;

interface RecEntry {
  ws: { id: number; sock: string; pending: boolean; deleting: boolean; sids: number[] }[];
  wsTrunc?: boolean;
  ghostIn: [string, number][];
  placeholders: number[];
  touched: number[];
  socks: { sock: string; got: boolean; trunc?: boolean; surf?: { sid: number; role: string | null; ex: boolean; pane: boolean }[] }[];
  sweep: { sock: string; here: boolean; scope: number[] }[];
  ph: { sock: string; sid: number; in: { lc: number | null; win: boolean } }[];
  ph_closed?: never;
}

/** 재생 결과 — 기록기의 같은 이름 칸과 바이트로 대조하는 꼴(역할 이름은 기록에 있는 꼴 그대로 · 해시 그대로). */
export interface ReplayOut {
  ghost: { sock: string; tree: number[]; evict: number[] }[];
  sweep: { sock: string; here: boolean; scope: number[]; targets: number[] }[];
  adopt: { sock: string; sid: number; role: string | null }[];
  ph: { sock: string; sid: number; close: boolean; in: { own: boolean; touched: boolean; role: string | null; lc: number | null; win: boolean; arrived: boolean; ex: boolean } }[];
  ghostOut: [string, number][];
}

/**
 * 조각 0 덤프 한 칸을 decide 두 함수에 다시 넣는다(§2-1 시험 ②). 칸에 없는 것은 기록에서 가져온다:
 *   · 스윕 범위 = 기록된 sweep[].scope(이미 트리 ∩ 범위) · 화면 줄 수 = 기록된 ph[].in.lc(모으기 단계 관측값 = F18)
 *   · 이 틱에 새로 연 부서 탭(ws 에 없는 소켓) = 빈 트리 작업공간으로 뒤에 붙인다(열기 판정은 레지스트리 파일 입력이라 이 칸 밖).
 * 반환 = 기록과 같은 꼴(소켓 열쇠 = 기록의 해시 열쇠 · 기본 데몬 "~").
 */
export function decideTick(entry: J): ReplayOut {
  const e = entry as RecEntry;
  let ws: TickWs[] = e.ws.map((w) => ({ id: w.id, sock: w.sock, pending: !!w.pending, deleting: !!w.deleting, sids: [...w.sids] }));
  if (ws.length === 0) ws.push({ id: -1, sock: "~", pending: false, deleting: false, sids: [] }); // 종전 「탭 0개 = 본부 빈 탭 되살림」
  let nextId = -2;
  for (const s of e.socks) if (s.got && !ws.some((w) => w.sock === s.sock)) ws.push({ id: nextId--, sock: s.sock, pending: false, deleting: false, sids: [] });
  let ghost = new Map<string, number>(e.ghostIn);
  const placeholders = new Set(e.placeholders);
  const touched = new Set(e.touched);
  const out: ReplayOut = { ghost: [], sweep: [], adopt: [], ph: [], ghostOut: [] };
  for (const s of e.socks) {
    if (!s.got || !s.surf) continue;
    const surfaces: TickSurface[] = s.surf.map((x) => ({ surface_id: x.sid, role: x.role, exited: x.ex }));
    const known = new Set(s.surf.filter((x) => x.pane).map((x) => x.sid));
    const sw = e.sweep.find((x) => x.sock === s.sock);
    const pre = decideSockPre({ sock: s.sock, ws, surfaces, ghostStrike: ghost, sweepScope: sw && sw.here ? new Set(sw.scope) : null, known });
    ghost = pre.ghostNext;
    out.ghost.push({ sock: s.sock, tree: pre.tree, evict: pre.evict });
    out.sweep.push({ sock: s.sock, here: pre.sweepHere, scope: pre.sweepScope, targets: pre.sweepTargets });
    // 모형 반영(집행과 같은 순서) — 퇴거·쓸기 떼기 → 입양 붙이기
    const gone = new Set([...pre.evict, ...pre.sweepTargets]);
    ws = ws.map((w) => (w.sock === s.sock ? { ...w, sids: w.sids.filter((x) => !gone.has(x)) } : w));
    for (const a of pre.adopt) {
      const w = ws.find((x) => x.id === a.wsId);
      if (w) w.sids = [...w.sids, a.sid];
      out.adopt.push({ sock: s.sock, sid: a.sid, role: a.role });
    }
    const lcOf = new Map(e.ph.filter((p) => p.sock === s.sock).map((p) => [p.sid, p.in.lc] as const));
    const win = e.ph.find((p) => p.sock === s.sock)?.in.win ?? false;
    const verdicts = decidePlaceholders({ sock: s.sock, ws, surfaces, placeholders, touched, lineCount: (_w, sid) => lcOf.get(sid) ?? null, isWindows: win });
    for (const v of verdicts) {
      if (v.close) placeholders.delete(v.sid);
      out.ph.push({
        sock: s.sock, sid: v.sid, close: v.close,
        in: { own: v.in.isOwnPlaceholder, touched: v.in.touched, role: v.in.role, lc: v.in.lineCount, win: v.in.isWindows, arrived: v.in.formationArrived, ex: v.in.exited },
      });
    }
  }
  out.ghostOut = [...ghost];
  return out;
}
