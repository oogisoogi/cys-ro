// scrollfollow.ts 회귀 테스트 — v115-restore B1(위로 스크롤이 스트리밍 중 바닥으로 끌려 내려가는 결함).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { nextFollow, shouldShowFoldHint, FOLD_HINT_BODY } from "./scrollfollow";

describe("바닥 고정 재판정(B1 ①)", () => {
  it("트랙패드 소량 위 델타 — 첫 프레임 atBottom=true 여도 follow 는 false 로 유지된다", () => {
    // 옛 배선(follow = atBottom())이면 여기서 true 로 되살아나 다음 write 스냅이 끌어내린다.
    let f = true;
    f = nextFollow(f, -0.5, true, false);
    expect(f).toBe(false);
    // 후속 소량 위 델타가 계속 와도(뷰포트 여전히 바닥) 해제 유지
    f = nextFollow(f, -0.3, true, false);
    expect(f).toBe(false);
  });
  it("아래로 휠 뒤 바닥 도달 = 재고정 · 바닥 전이면 해제 유지", () => {
    let f = nextFollow(true, -120, false, false);
    expect(f).toBe(false);
    f = nextFollow(f, 60, false, false); // 아직 바닥 아님
    expect(f).toBe(false);
    f = nextFollow(f, 60, true, false); // 바닥 도달
    expect(f).toBe(true);
  });
  it("키 입력 = 즉시 재고정 · 가로 휠 = 무변", () => {
    expect(nextFollow(false, -10, false, true)).toBe(true);
    expect(nextFollow(false, 0, true, false)).toBe(false);
    expect(nextFollow(true, 0, false, false)).toBe(true);
  });
});

describe("맨 위 도달 안내(B1 ②)", () => {
  it("위로 휠 + 맨 위 + 위 내용이 있었다 = 1회만", () => {
    expect(shouldShowFoldHint(false, -40, 0, 120, "normal")).toBe(true);
    expect(shouldShowFoldHint(true, -40, 0, 120, "normal")).toBe(false);
  });
  it("맨 위가 아니거나 아래로 휠이면 안 띄운다", () => {
    expect(shouldShowFoldHint(false, -40, 12, 120, "normal")).toBe(false);
    expect(shouldShowFoldHint(false, 40, 0, 120, "normal")).toBe(false);
  });
  it("(D4 #6) 스크롤백이 없는 짧은 창(baseY 0)·대체 화면(vim·less)에서는 첫 위 휠에 띄우지 않는다", () => {
    expect(shouldShowFoldHint(false, -40, 0, 0, "normal")).toBe(false);
    expect(shouldShowFoldHint(false, -40, 0, 120, "alternate")).toBe(false);
    expect(shouldShowFoldHint(false, -40, 0, 0, "alternate")).toBe(false);
  });
  it("(D4 #6) 배선이 스크롤백 줄 수·버퍼 종류를 넘긴다", () => {
    const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
    expect(main).toContain("shouldShowFoldHint(foldHintShown, dy, ab.viewportY, ab.baseY, ab.type)");
  });
  it("문구 = 내부 용어 0(surface·xterm·스크롤백 등)", () => {
    expect(FOLD_HINT_BODY).toContain("Ctrl+O");
    expect(/surface|xterm|scrollback|스크롤백|버퍼|pty/i.test(FOLD_HINT_BODY)).toBe(false);
  });
});

describe("배선(호출부 계수) — 수리 모듈이 실제 휠 경로에서 불린다", () => {
  it("휠 rAF 는 nextFollow·shouldShowFoldHint 를 부르고 옛 되돌림(follow = atBottom())은 0건", () => {
    const src = readFileSync(new URL("./main.ts", import.meta.url), "utf-8");
    const i = src.indexOf('termHost.addEventListener(\n    "wheel",');
    expect(i).toBeGreaterThan(0);
    const wheel = src.slice(i, src.indexOf("{ passive: true }", i));
    expect(wheel.includes("follow = nextFollow(follow, dy, atBottom(), false);")).toBe(true);
    expect(wheel.includes("shouldShowFoldHint(foldHintShown, dy,")).toBe(true);
    expect(src.includes("follow = atBottom();")).toBe(false);
  });
});
