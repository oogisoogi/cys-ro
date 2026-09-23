// panetitle.test.ts — 창 머리 제목(D4 #12) · TICKET=v116-ui-close-r2.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { paneTitleText, renameCommitTitle, cwdBase, isAutoTitle, EXITED_TITLE_PREFIX } from "./panetitle";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");

describe("D4 #12 역할 없는 창 = 「번호 · 폴더 이름」", () => {
  it("자동 제목(빈 · surface N)이면 번호 먼저 + 마지막 폴더 이름", () => {
    expect(paneTitleText(7, "", "/Users/u/axdev/.wt/long/project-alpha", false)).toBe("7 · project-alpha");
    expect(paneTitleText(7, "surface 7", "/Users/u/", false)).toBe("7 · u");
    expect(paneTitleText(7, null, "C:\\Users\\u\\proj", false)).toBe("7 · proj");
    expect(paneTitleText(7, "", null, false)).toBe("7");
  });
  it("데몬이 지은 제목(역할 창 · 사람 이름)은 그대로", () => {
    expect(paneTitleText(1, "1 · master", "/Users/u/jarvis", false)).toBe("1 · master");
    expect(paneTitleText(1, "내 창", "/Users/u/jarvis", false)).toBe("내 창");
  });
  it("번호를 모르면(생성 직후) 종전처럼", () => {
    expect(paneTitleText(null, "", null, false)).toBe("…");
    expect(paneTitleText(null, "x", null, false)).toBe("x");
  });
  it("cwdBase — 끝 구분자 무시 · 뿌리만이면 원문", () => {
    expect(cwdBase("/a/b/")).toBe("b");
    expect(cwdBase("/")).toBe("/");
    expect(cwdBase("C:\\x\\y")).toBe("y");
    expect(isAutoTitle("surface 12")).toBe(true);
    expect(isAutoTitle("12 · u")).toBe(false);
  });
});

describe("D4 #12 끝난 창 표지 = 앞머리(말줄임이 먼저 자르지 않게)", () => {
  it("「(끝남) 」이 맨 앞", () => {
    expect(EXITED_TITLE_PREFIX).toBe("(끝남) ");
    expect(paneTitleText(2, "2 · worker", null, true)).toBe("(끝남) 2 · worker");
    expect(paneTitleText(2, "", "/a/proj", true).startsWith("(끝남) 2 · proj")).toBe(true);
  });
});

describe("D4 #12 이름 비워 확정 = 기본으로 복귀(번호·특성 소실 0)", () => {
  it("편집 전 데몬 제목이 이 번호로 시작하면 그것을 되돌려 보낸다", () => {
    expect(renameCommitTitle("   ", "1 · master", 1)).toBe("1 · master");
    expect(renameCommitTitle("", "1 · Opus · master", 1)).toBe("1 · Opus · master");
  });
  it("다른 번호 · 사람 이름 · 자동 제목이면 \"\"(자동 제목 = 번호 · 폴더 이름)", () => {
    expect(renameCommitTitle("", "12 · master", 1)).toBe("");
    expect(renameCommitTitle("", "내 창", 1)).toBe("");
    expect(renameCommitTitle("", "", 1)).toBe("");
    expect(renameCommitTitle("", "surface 1", 1)).toBe("");
  });
  it("이름을 적으면 그 이름(앞뒤 공백 제거)", () => {
    expect(renameCommitTitle("  새 이름 ", "1 · master", 1)).toBe("새 이름");
  });
  it("배선: 편집 시작 때 데몬 제목을 잡아 두고 확정 때 판정 모듈을 거친다 · 툴팁 = 전체 경로", () => {
    expect(main).toContain('const before = titleEl.dataset.daemonTitle ?? "";');
    expect(main).toContain('const name = renameCommitTitle(titleEl.textContent || "", before, sid);');
    expect(main).toContain('rt.titleEl.dataset.daemonTitle = s.title ?? "";');
    expect(main).toContain('rt.titleEl.title = s.live_cwd ?? "";');
  });
});
