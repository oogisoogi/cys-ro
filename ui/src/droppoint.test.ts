// droppoint.ts 순수 함수 회귀 테스트 (bun test — 신규 의존성 0). (1.1.7 ② Retina 드롭 오배달)
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { dropPointToCss } from "./droppoint";

describe("dropPointToCss — 플랫폼별 드롭 좌표 단위", () => {
  test("맥 Retina(dpr 2) = 나누지 않는다(wry 가 이미 포인트 단위)", () => {
    // 1600pt 폭 창의 오른쪽 창(x=1200) — 나누면 600 이 되어 왼쪽 창으로 간다(오배달 재현값).
    expect(dropPointToCss({ x: 1200, y: 300 }, 2, true)).toEqual({ x: 1200, y: 300 });
  });
  test("맥 dpr 1 도 그대로", () => {
    expect(dropPointToCss({ x: 10, y: 20 }, 1, true)).toEqual({ x: 10, y: 20 });
  });
  test("윈도 = 물리 픽셀을 dpr 로 나눈다(종전 동작 유지)", () => {
    expect(dropPointToCss({ x: 1500, y: 300 }, 1.5, false)).toEqual({ x: 1000, y: 200 });
    expect(dropPointToCss({ x: 800, y: 400 }, 2, false)).toEqual({ x: 400, y: 200 });
  });
  test("좌표 없음 = undefined(호출측이 무동작+토스트)", () => {
    expect(dropPointToCss(undefined, 2, true)).toBeUndefined();
    expect(dropPointToCss(undefined, 2, false)).toBeUndefined();
  });
  test("dpr 없음·0·NaN = 1 로 본다(0 나눗셈·NaN 좌표 방지)", () => {
    for (const bad of [undefined, 0, NaN, -1, Infinity]) {
      expect(dropPointToCss({ x: 30, y: 40 }, bad as number | undefined, false)).toEqual({ x: 30, y: 40 });
    }
  });
});

// 배선 핀(적대 검증 R1 Fable): 순수 함수만 재면 호출부가 isMac 에 false 를 넘겨도 초록이다 — 실제 호출이 IS_MACOS 를 넘기는지 소스로 못박는다.
describe("paneAtPointStrict 배선", () => {
  const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  test("드롭 좌표 환산 = dropPointToCss(pos, window.devicePixelRatio, IS_MACOS)", () => {
    expect(main).toContain("dropPointToCss(pos, window.devicePixelRatio, IS_MACOS)");
    expect(main).not.toMatch(/elementFromPoint\(pos\.x \/ dpr/);
  });
});
