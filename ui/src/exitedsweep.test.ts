// exitedsweep.test.ts — 복원 뒤 옛 자리 자동 정리(B17) 회귀 · TICKET=v110-darwin-update.
//
// 실기 맥락: 재시작·phoenix 복원이 끝나면 새 자리가 따로 서는데, 옛 자리는 빨간 [surface exited]
// 배너만 단 채 그대로 남았다. 데몬이 그 기록을 **알고 있어서**(exited=true) 기존 유령 수렴
// (knownIds 밖만 친다)에는 영원히 걸리지 않는다 — 그래서 축을 따로 세운다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { exitedSweepTargets, armSweep, sweepArmedFor, settleSweep, SWEEP_ARM_TTL_MS } from "./exitedsweep";
import { formationIfRowOnly, type LayoutNode } from "./formation";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");

describe("B17 옛 자리 스윕 판정", () => {
  const rows = [
    { surface_id: 1, exited: true },
    { surface_id: 2, exited: false },
    { surface_id: 3 }, // exited 칸이 없는 기록 = 모른다 → 치지 않는다
  ];

  it("무장했을 때만, exited=true 인 자리만 친다", () => {
    expect(exitedSweepTargets(true, [1, 2, 3], rows)).toEqual([1]);
    expect(exitedSweepTargets(false, [1, 2, 3], rows)).toEqual([]);
  });

  it("트리에 없는 sid 는 치지 않는다(남의 워크스페이스 보호)", () => {
    expect(exitedSweepTargets(true, [2, 3], rows)).toEqual([]);
  });

  it("빈 목록은 판정 보류다 — 화면을 통째로 비우지 않는다", () => {
    // 데몬이 한 틱 빈 목록을 돌려주는 것은 "전부 죽었다"가 아니다(유령 수렴과 같은 규율).
    // ★이 성질은 명시 가드가 아니라 **술어의 방향**(있는 것만 친다)에서 나온다 — 방향을 뒤집는
    //   뮤턴트(m9)가 이 줄을 빨갛게 만든다. 가드 줄은 아무것도 지키지 않아 걷어냈다.
    expect(exitedSweepTargets(true, [1, 2, 3], [])).toEqual([]);
  });

  it("exited 가 참 같은 값이어도 true 가 아니면 치지 않는다(fail-safe)", () => {
    const odd = [{ surface_id: 9, exited: 1 as unknown as boolean }];
    expect(exitedSweepTargets(true, [9], odd)).toEqual([]);
  });
});

// ── D4 #17(TICKET=v116-ui-close): 조회가 건너뛰어지거나 실패한 소켓은 다음 틱이 다시 쓴다 ─────────
//   종전 계약은 「한 패스 뒤 finally 에서 무조건 내린다」였고, 그 때문에 조회 실패 소켓의 [exited] 옛 창이
//   다음 복원까지 남았다(헤드리스 재현). 새 계약 = 「청소 줄까지 도달한 소켓만 무장에서 뺀다 · 5분 상한」.
describe("D4 #17 소켓별 무장 — 진리표", () => {
  const T0 = 1_000_000;
  const rows = [
    { surface_id: 1, exited: false },
    { surface_id: 7, exited: true }, // 이벤트를 놓친 옛 자리
  ];

  it("무장 = 그때 화면의 소켓 전부 · 소켓이 없으면 무장 없음", () => {
    const arm = armSweep(["", "/d/a.sock"], T0);
    expect(sweepArmedFor(arm, "", T0)).toBe(true);
    expect(sweepArmedFor(arm, "/d/a.sock", T0)).toBe(true);
    expect(sweepArmedFor(arm, "/d/other.sock", T0)).toBe(false); // 무장 뒤 생긴 소켓은 대상 밖
    expect(armSweep([], T0)).toBeNull();
    expect(sweepArmedFor(null, "", T0)).toBe(false);
  });

  it("패스 1 에서 부서 소켓 조회 실패 → 그 소켓은 무장이 남고, 패스 2 에서 쓸린다(잔재 0)", () => {
    let arm = armSweep(["", "/d/a.sock"], T0);
    // 패스 1: 본부("")만 청소 줄 도달 · 부서는 시간초과(청소 줄 미도달)
    arm = settleSweep(arm, [""], T0 + 3_000);
    expect(sweepArmedFor(arm, "", T0 + 6_000)).toBe(false); // 본부는 다시 쓸지 않는다(1회)
    expect(sweepArmedFor(arm, "/d/a.sock", T0 + 6_000)).toBe(true); // 부서는 아직 무장
    // 패스 2: 부서 조회 성공 → 옛 자리를 친다
    expect(exitedSweepTargets(sweepArmedFor(arm, "/d/a.sock", T0 + 6_000), [1, 7], rows)).toEqual([7]);
    arm = settleSweep(arm, ["/d/a.sock"], T0 + 6_000);
    expect(arm).toBeNull(); // 전부 쓸렸다 = 무장 해제(평시 창을 쓸지 않는다)
  });

  it("아무 소켓도 청소 줄에 못 닿은 패스(전부 실패·건너뜀) → 무장이 그대로 남는다", () => {
    const arm = armSweep(["", "/d/a.sock"], T0);
    const after = settleSweep(arm, [], T0 + 3_000);
    expect(sweepArmedFor(after, "", T0 + 3_000)).toBe(true);
    expect(sweepArmedFor(after, "/d/a.sock", T0 + 3_000)).toBe(true);
  });

  it("상한(5분)을 넘기면 무장이 사라진다 — 응답 없는 소켓 때문에 영구 무장 0", () => {
    const arm = armSweep(["/d/dead.sock"], T0);
    expect(sweepArmedFor(arm, "/d/dead.sock", T0 + SWEEP_ARM_TTL_MS)).toBe(true); // 경계 = 아직 유효
    expect(sweepArmedFor(arm, "/d/dead.sock", T0 + SWEEP_ARM_TTL_MS + 1)).toBe(false);
    expect(settleSweep(arm, [], T0 + SWEEP_ARM_TTL_MS + 1)).toBeNull();
  });

  it("무장이 길어져도 산 창은 치지 않는다 — 술어는 exited=true 만(4군 ④)", () => {
    const arm = armSweep([""], T0);
    const live = [{ surface_id: 1, exited: false }, { surface_id: 2 }];
    expect(exitedSweepTargets(sweepArmedFor(arm, "", T0 + 60_000), [1, 2], live)).toEqual([]);
  });
});

describe("B17 배선", () => {
  it("복원 완료(done)에서 무장한다 — 그때 화면의 소켓 전부", () => {
    const done = main.indexOf('} else if (p.phase === "done") {');
    expect(done).toBeGreaterThan(-1);
    const block = main.slice(done, main.indexOf('} else if (p.phase === "error")', done));
    expect(block).toContain('exitedSweepArm = armSweep(workspaces.map((w) => w.socket ?? ""), Date.now());');
    expect(block).toContain("void refreshPaneTitles();");
  });

  it("무장 정리는 finally 에서 — 청소 줄에 닿은 소켓만 뺀다(무조건 해제 금지 · D4 #17)", () => {
    const body = main.slice(main.indexOf("async function refreshPaneTitles() {"));
    const fin = body.indexOf("} finally {");
    expect(fin).toBeGreaterThan(-1);
    const finBlock = body.slice(fin, fin + 900);
    expect(finBlock).toContain("exitedSweepArm = settleSweep(sweepArm, sweptSockets, Date.now())");
    expect(finBlock).not.toContain("exitedSweepArm = null");
    // 「쓸렸다」 표시는 소켓 조회가 **성공한 경로 안**(try · 스윕 루프 뒤)에만 있다 — catch·건너뜀 경로엔 없다.
    const sweep = body.indexOf("exitedSweepTargets(sweepHere, sockSids, r.surfaces)");
    const mark = body.indexOf('if (sweepHere) sweptSockets.push(sk ?? "")');
    const sockCatch = body.indexOf("★소켓 하나의 실패가 다른 소켓의 갱신·렌더를 막지 않는다");
    expect(sweep).toBeGreaterThan(-1);
    expect(mark).toBeGreaterThan(sweep);
    expect(mark).toBeLessThan(sockCatch);
    expect(body.split("sweptSockets.push").length - 1).toBe(1);
  });

  it("스윕은 유령 수렴과 **다른 함수**로 판정한다(두 축을 뭉치지 않는다)", () => {
    expect(main).toContain("exitedSweepTargets(sweepHere, sockSids, r.surfaces)");
    expect(main).toContain("advanceGhostStrikes(ghostStrike,");
  });
});

describe("B16 결선 — 닫기가 먼저, 배치가 나중", () => {
  const row = (sids: number[]): LayoutNode =>
    sids.slice(1).reduce<LayoutNode>(
      (acc, sid) => ({ type: "split", dir: "row", a: acc, b: { type: "pane", sid } }),
      { type: "pane", sid: sids[0] },
    );
  const sidsOf = (n: LayoutNode, out: number[] = []): number[] => {
    if (n.type === "pane") out.push(n.sid);
    else {
      sidsOf(n.a, out);
      sidsOf(n.b, out);
    }
    return out;
  };
  const drop = (n: LayoutNode, gone: Set<number>): LayoutNode | null => {
    if (n.type === "pane") return gone.has(n.sid) ? null : n;
    const a = drop(n.a, gone);
    const b = drop(n.b, gone);
    return a && b ? { ...n, a, b } : (a ?? b);
  };
  const surfaces = [
    { surface_id: 1, exited: false, role: "master" },
    { surface_id: 2, exited: false, role: "cso" },
    { surface_id: 3, exited: false, role: "worker" },
    { surface_id: 9, exited: true, role: "worker" }, // 재시작이 남긴 옛 자리
  ];

  it("닫은 뒤 새로 만든 roleBySid 로 배치하면 닫힌 좌석이 열을 차지하지 않는다", () => {
    const tree = row([1, 2, 3, 9]);
    const targets = exitedSweepTargets(true, sidsOf(tree), surfaces);
    expect(targets).toEqual([9]);
    const closed = drop(tree, new Set(targets))!;
    // ★roleBySid 는 **닫은 뒤** 만든다 — 살아 있는 좌석만으로.
    const roleBySid = new Map(surfaces.filter((s) => !s.exited).map((s) => [s.surface_id, s.role] as const));
    const laid = formationIfRowOnly(closed, roleBySid);
    expect(sidsOf(laid).sort()).toEqual([1, 2, 3]);
  });

  it("순서를 뒤집으면(배치 먼저) 닫힌 좌석이 그대로 열을 차지한다 — 그래서 순서가 계약이다", () => {
    const tree = row([1, 2, 3, 9]);
    const roleWithClosed = new Map(surfaces.map((s) => [s.surface_id, s.role] as const));
    const laidFirst = formationIfRowOnly(tree, roleWithClosed);
    expect(sidsOf(laidFirst)).toContain(9); // 닫히지 않은 채 배치됨 = 열 하나를 먹는다
  });

  it("배선이 그 순서다 — 스윕 루프가 배치 블록보다 앞에 있고, roleBySid 는 exited 를 뺀다", () => {
    const body = main.slice(main.indexOf("async function refreshPaneTitles() {"));
    const sweep = body.indexOf("exitedSweepTargets(sweepHere");
    const place = body.indexOf("formationIfRowOnly(ws.tree, roleBySid)");
    expect(sweep).toBeGreaterThan(-1);
    expect(place).toBeGreaterThan(-1);
    expect(sweep).toBeLessThan(place); // 닫기 → 배치
    // roleBySid 는 살아 있는 좌석만으로 만든다(닫은 sid 가 섞이면 열을 하나 차지한다).
    const build = body.indexOf("const roleBySid = new Map<number, string | null>(");
    expect(body.slice(build, build + 220)).toContain("filter((x) => !x.exited)");
    // 스윕이 친 ws 도 배치 대상 집합에 들어간다(입양이 없던 틱에도 배치가 돈다).
    expect(body.slice(sweep, place)).toContain("relayoutWs.add(w)");
  });
});

