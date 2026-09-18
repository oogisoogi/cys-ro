// permtoast.test.ts — TCC 폴더 접근 토스트 브랜드명 회귀(TICKET=v110-misc B3).
//
// 실기: perm-warning 토스트 본문이 "cys를 허용한 뒤"로 앱 명칭 개칭(cysr) 전 문구를 그대로
// 남기고 있었다(ui/src/main.ts). 개칭 뒤에도 옛 문구가 조용히 재발하지 않게 핀으로 고정한다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");

describe("TCC 폴더 접근 토스트", () => {
  it("옛 명칭 'cys를 허용한 뒤' 가 없다", () => {
    expect(main).not.toContain("cys를 허용한 뒤");
  });

  it("perm-warning 리스너가 'cysr을 허용한 뒤' 를 말한다", () => {
    const idx = main.indexOf('listen("perm-warning"');
    expect(idx).toBeGreaterThan(-1);
    const block = main.slice(idx, main.indexOf("});", idx));
    expect(block).toContain("cysr을 허용한 뒤 앱을 재시작하세요");
  });
});
