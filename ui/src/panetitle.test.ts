// panetitle.test.ts — 창 머리 제목(D4 #12) · TICKET=v116-ui-close-r2.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { paneTitleText, renameCommitTitle, ruleTitleOf, stripExited, cwdBase, isAutoTitle, EXITED_TITLE_PREFIX, titleNo, NO_DISPLAY_NO } from "./panetitle";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");

describe("D4 #12 역할 없는 창 = 「번호 · 폴더 이름」", () => {
  it("자동 제목(빈 · surface N)이면 번호 먼저 + 마지막 폴더 이름", () => {
    expect(paneTitleText(7, "", "/Users/user/axdev/.wt/long/project-alpha", false)).toBe("7 · project-alpha");
    expect(paneTitleText(7, "surface 7", "/Users/user/", false)).toBe("7 · user");
    expect(paneTitleText(7, null, "C:\\Users\\x\\proj", false)).toBe("7 · proj");
    expect(paneTitleText(7, "", null, false)).toBe("7");
  });
  it("데몬이 지은 제목(역할 창 · 사람 이름)은 그대로", () => {
    expect(paneTitleText(1, "1 · master", "/Users/user/jarvis", false)).toBe("1 · master");
    expect(paneTitleText(1, "내 창", "/Users/user/jarvis", false)).toBe("내 창");
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

describe("D4 #12 이름 변경 확정(opus 결함 1·2·3 반영)", () => {
  it("역할 창: 빈 이름 = 기억해 둔 규칙 제목 「번호 · 특성」", () => {
    expect(renameCommitTitle("   ", "1 · master", "1 · master")).toBe("1 · master");
    expect(renameCommitTitle("", "1 · Opus · master", "1 · Opus · master")).toBe("1 · Opus · master");
  });
  it("(결함 3) 역할 창에 사람 이름을 붙였다가 비워도 규칙 제목으로", () => {
    expect(renameCommitTitle("", "foo", "12 · worker1")).toBe("12 · worker1");
  });
  it("(결함 1) 역할 없는 창: 빈 이름 = \"\"(자동 제목) · 번호로 시작하는 제목이 있어도 되돌리지 않는다", () => {
    expect(renameCommitTitle("", "12 · proj", null)).toBe("");
    expect(renameCommitTitle("", "12 · 메모", null)).toBe("");
  });
  it("(결함 1) 바뀐 것이 없으면 보내지 않는다(null) — 눌렀다 떼기만 해도 자동 제목이 굳던 것", () => {
    expect(renameCommitTitle("12 · proj", "12 · proj", null)).toBe(null);
    expect(renameCommitTitle(" 12 · proj ", "12 · proj", null)).toBe(null);
  });
  it("(결함 2) 「(끝남) 」 앞머리는 떼고 비교·저장", () => {
    expect(renameCommitTitle("(끝남) 12 · worker1", "(끝남) 12 · worker1", "12 · worker1")).toBe(null);
    expect(renameCommitTitle("(끝남) 새 이름", "(끝남) 12 · worker1", "12 · worker1")).toBe("새 이름");
    expect(stripExited("(끝남) x")).toBe("x");
  });
  it("이름을 적으면 그 이름(앞뒤 공백 제거)", () => {
    expect(renameCommitTitle("  새 이름 ", "1 · master", "1 · master")).toBe("새 이름");
  });
  it("ruleTitleOf — 역할 있고 이 번호로 시작할 때만", () => {
    expect(ruleTitleOf(1, "master", "1 · master")).toBe("1 · master");
    expect(ruleTitleOf(12, null, "12 · proj")).toBe(null);
    expect(ruleTitleOf(1, "master", "foo")).toBe(null);
    expect(ruleTitleOf(1, "master", "12 · master")).toBe(null);
  });
  it("배선: 규칙 제목은 역할 창에서만 기억 · 확정은 판정 모듈 · null 이면 쓰지 않음 · 툴팁 = 전체 경로", () => {
    expect(main).toContain("const rule = ruleTitleOf(s.surface_id, s.role, s.title, s.display_no);");
    expect(main).toContain("if (rule) rt.titleEl.dataset.ruleTitle = rule;");
    expect(main).toContain('const shownBefore = titleEl.textContent || "";');
    expect(main).toContain('const name = renameCommitTitle(titleEl.textContent || "", shownBefore, titleEl.dataset.ruleTitle ?? null);');
    expect(main).toContain("if (name === null) {");
    expect(main).toContain('rt.titleEl.title = s.live_cwd ?? "";');
  });
});

// ★v116-num T8 — 창 머리 번호 = 보이는 번호(데몬 display_no · 1~999 순환). M17(sid 그대로) 이면 아래가 적색.
describe("v116-num 보이는 번호", () => {
  it("titleNo — 번호 있음 · 없음(「—」) · 옛 데몬(필드 없음 = 내부 번호)", () => {
    expect(titleNo(1049, 50)).toBe("50");
    expect(titleNo(1049, null)).toBe(NO_DISPLAY_NO);
    expect(NO_DISPLAY_NO).toBe("—");
    expect(titleNo(1049, undefined)).toBe("1049");
    expect(titleNo(1049)).toBe("1049");
  });
  it("역할 없는 창 자동 제목 = 「보이는 번호 · 폴더」", () => {
    expect(paneTitleText(1049, "", "/a/proj", false, 50)).toBe("50 · proj");
    expect(paneTitleText(1049, "surface 1049", "/a/proj", false, 50)).toBe("50 · proj");
    expect(paneTitleText(1049, "", "/a/proj", false, null)).toBe("— · proj");
    expect(paneTitleText(1049, "", null, false, 50)).toBe("50");
    expect(paneTitleText(1049, "", "/a/proj", false)).toBe("1049 · proj");
    expect(paneTitleText(1049, "", "/a/proj", true, 50)).toBe(EXITED_TITLE_PREFIX + "50 · proj");
  });
  it("데몬이 지은 역할 창 제목은 그대로(번호를 다시 붙이지 않는다)", () => {
    expect(paneTitleText(1049, "50 · Opus · worker1", "/a/proj", false, 50)).toBe("50 · Opus · worker1");
    expect(paneTitleText(1500, "— · worker2", "/a/proj", false, null)).toBe("— · worker2");
  });
  it("ruleTitleOf — 보이는 번호로 시작할 때만 규칙 제목", () => {
    expect(ruleTitleOf(1049, "worker", "50 · worker1", 50)).toBe("50 · worker1");
    expect(ruleTitleOf(1049, "worker", "1049 · worker1", 50)).toBe(null);
    expect(ruleTitleOf(1500, "worker-2", "— · worker2", null)).toBe("— · worker2");
    expect(ruleTitleOf(1049, "worker", "1049 · worker1")).toBe("1049 · worker1");
  });
  it("배선: 머리 제목·규칙 제목에 display_no 를 넘긴다", () => {
    expect(main).toContain("paneTitleText(s.surface_id, s.title, s.live_cwd, !!s.exited, s.display_no)");
    expect(main).toContain('if ("display_no" in s) displayNoByKey.set(paneKey(s.surface_id, sk), s.display_no ?? null);');
  });
});
