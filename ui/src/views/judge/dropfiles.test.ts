// (TICKET=cysr-1119-s11 · DESIGN TC3) 대화 입력칸 끌어 놓기 — 칩 목록 · 보낼 때 글 끝 @경로(ftdrop 인용 함수 재사용) · 업로드 0.
import { describe, expect, it } from "bun:test";
import { insertionText } from "../../ftdrop";
import { addDropped, chipName, withDroppedFiles } from "./dropfiles";

describe("TC3 칩 목록(addDropped)", () => {
  it("같은 파일 두 번 놓기 = 칩 1개(중복 0) · 순서 = 처음 놓은 순서", () => {
    expect(addDropped([], ["/a/x.md", "/a/x.md"])).toEqual(["/a/x.md"]);
    expect(addDropped(["/a/x.md"], ["/b/y.md", "/a/x.md"])).toEqual(["/a/x.md", "/b/y.md"]);
  });
  it("빈 경로는 칩이 되지 않음 · 원래 목록은 바꾸지 않음(새 배열)", () => {
    const before = ["/a/x.md"];
    const after = addDropped(before, ["", "/c/z.txt"]);
    expect(after).toEqual(["/a/x.md", "/c/z.txt"]);
    expect(before).toEqual(["/a/x.md"]);
  });
  it("칩 이름 = 파일 이름(맥 /  · 윈 \\ 둘 다)", () => {
    expect(chipName("/Users/user/문서/보고서.md")).toBe("보고서.md");
    expect(chipName("C:\\Users\\user\\보고서.md")).toBe("보고서.md");
  });
});

describe("TC3 보내는 글(withDroppedFiles) — 펼친 입력칸 글", () => {
  it("칩 없음 = 입력칸 글 바이트 그대로(사람 쓰기 길 무변경)", () => {
    for (const t of ["", "안녕", "  앞뒤 공백  ", "줄\n바꿈\n"]) expect(withDroppedFiles(t, [], false)).toBe(t);
  });
  it("글 + 칩 = 글(끝 공백 걷음) + 공백 1 + @절대경로(ftdrop insertionText 에이전트 꼴 · 끝 공백 없음)", () => {
    expect(withDroppedFiles("이 파일 봐 줘\n", ["/a/x.md", "/b/한글 이름.md"], false)).toBe("이 파일 봐 줘 @/a/x.md '/b/한글 이름.md'");
    const m = insertionText(["/a/x.md"], { agent: true, isWin: false, cwd: null }).trimEnd();
    expect(withDroppedFiles("봐", ["/a/x.md"], false)).toBe(`봐 ${m}`);
  });
  it("글 없이 칩만 = @경로만", () => {
    expect(withDroppedFiles("   ", ["/a/x.md"], false)).toBe("@/a/x.md");
  });
  it("윈 경로 = 같은 함수의 윈 갈래(공백 경로 인용 = insertionText isWin)", () => {
    const p = ["C:\\Users\\user\\my file.md"];
    expect(withDroppedFiles("봐", p, true)).toBe(`봐 ${insertionText(p, { agent: true, isWin: true, cwd: null }).trimEnd()}`);
    expect(withDroppedFiles("봐", ["C:\\a\\b.md"], true)).toBe("봐 @C:\\a\\b.md");
  });
});
