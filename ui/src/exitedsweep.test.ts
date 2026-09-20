// exitedsweep.test.ts — 복원 뒤 옛 자리 자동 정리(B17) 회귀 · TICKET=v110-darwin-update.
//
// 실기 맥락: 재시작·phoenix 복원이 끝나면 새 자리가 따로 서는데, 옛 자리는 빨간 [surface exited]
// 배너만 단 채 그대로 남았다. 데몬이 그 기록을 **알고 있어서**(exited=true) 기존 유령 수렴
// (knownIds 밖만 친다)에는 영원히 걸리지 않는다 — 그래서 축을 따로 세운다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { applyB16Placement, exitedSweepTargets } from "./exitedsweep";

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

describe("B16 이음매", () => {
  it("적용하지 않았음을 값으로 돌려준다(조용한 미편입 금지)", () => {
    const r = applyB16Placement();
    expect(r.applied).toBe(false);
    expect(r.reason).toContain("fix/v110-panetitle");
  });

  it("호출부가 그 사실을 로그로 남긴다", () => {
    expect(main).toContain("const placement = applyB16Placement();");
    expect(main).toContain("if (!placement.applied) console.info");
  });
});
