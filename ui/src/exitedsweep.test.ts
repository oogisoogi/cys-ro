// exitedsweep.test.ts — 복원 뒤 옛 자리 자동 정리(B17) 회귀 · TICKET=v110-darwin-update.
//
// 실기 맥락: 재시작·phoenix 복원이 끝나면 새 자리가 따로 서는데, 옛 자리는 빨간 [surface exited]
// 배너만 단 채 그대로 남았다. 데몬이 그 기록을 **알고 있어서**(exited=true) 기존 유령 수렴
// (knownIds 밖만 친다)에는 영원히 걸리지 않는다 — 그래서 축을 따로 세운다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { exitedSweepTargets } from "./exitedsweep";
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

describe("B17 배선", () => {
  it("복원 완료(done)에서 무장하고, 한 패스 뒤 finally 에서 내린다", () => {
    const done = main.indexOf('} else if (p.phase === "done") {');
    expect(done).toBeGreaterThan(-1);
    const block = main.slice(done, main.indexOf('} else if (p.phase === "error")', done));
    expect(block).toContain("exitedSweepArmed = true;");
    expect(block).toContain("void refreshPaneTitles();");
    // 무장 해제가 finally 에 있어야 예외 경로에서도 「1회」가 성립한다.
    const body = main.slice(main.indexOf("async function refreshPaneTitles() {"));
    const fin = body.indexOf("} finally {");
    expect(fin).toBeGreaterThan(-1);
    expect(body.slice(fin, fin + 600)).toContain("if (sweepArmed) exitedSweepArmed = false;");
  });

  it("스윕은 유령 수렴과 **다른 함수**로 판정한다(두 축을 뭉치지 않는다)", () => {
    expect(main).toContain("exitedSweepTargets(sweepArmed, sockSids, r.surfaces)");
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
    const sweep = body.indexOf("exitedSweepTargets(sweepArmed");
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

