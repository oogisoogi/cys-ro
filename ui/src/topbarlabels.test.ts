// topbarlabels.test.ts — 상단 단추·끝난 창 표시의 영어 제거(D4 #13) · TICKET=v116-ui-close.
// ★예외 1개 = 「Control Center」 — 기능 이름으로 사용 설명서·화면 안내 문구 여러 곳이 그 이름으로 가리킨다(이름을 바꾸면
//   안내가 서로 어긋난다). 이 목록을 늘리려면 이유를 여기 함께 적어라.
import { describe, it, expect } from "bun:test";
import { readFileSync, readdirSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const ALLOW = ["Control Center"];

describe("D4 #13 상단바 단추 글자 = 한국어", () => {
  const top = html.slice(html.indexOf('<header id="topbar">'), html.indexOf("</header>"));
  const labels = [...top.matchAll(/<button[^>]*>([\s\S]*?)<\/button>/g)].map((m) =>
    m[1].replace(/<span[\s\S]*?<\/span>/g, "").trim(),
  );

  it("단추 글자에 영어가 없다(허용 목록 제외)", () => {
    expect(labels.length).toBeGreaterThan(5);
    for (const l of labels) {
      const rest = ALLOW.reduce((acc, a) => acc.replace(a, ""), l);
      expect(/[A-Za-z]/.test(rest)).toBe(false);
    }
  });

  it("창 닫기 · 파일 · 업데이트", () => {
    for (const l of ["창 닫기", "파일", "업데이트"]) expect(labels).toContain(l);
  });

  it("안내 문구가 옛 영어 단추 이름을 가리키지 않는다 — ui/src 제품 파일 전부(Fable 적대 2R MAJOR: updateplan.ts 누락)", () => {
    const dir = new URL("./", import.meta.url);
    const files = readdirSync(dir, { withFileTypes: true })
      .filter((e) => e.isFile())
      .map((e) => e.name)
      .filter((f) => f.endsWith(".ts") && !f.endsWith(".test.ts") && !f.endsWith(".d.ts"));
    expect(files.length).toBeGreaterThan(20);
    for (const f of files) {
      // 주석 줄은 이력 설명이라 제외하고, 문자열에 실리는 안내만 본다
      const code = readFileSync(new URL(f, dir), "utf8").split("\n").filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join("\n");
      for (const bad of ["Update 버튼", "상단 Update", "Files 버튼", "Close 버튼"]) expect(`${f}: ${code.includes(bad)}`).toBe(`${f}: false`);
    }
    expect(main).toContain("상단 「업데이트」 버튼");
  });
});

describe("D4 #13 끝난 창 제목 표지 = 「(끝남)」(r2 · D4 #12 앞머리)", () => {
  it("제목 배선이 판정 모듈을 쓰고, 영어 [exited] 를 화면에 싣지 않는다", () => {
    expect(readFileSync(new URL("./panetitle.ts", import.meta.url), "utf8")).toContain('export const EXITED_TITLE_PREFIX = "(끝남) ";');
    expect(main).toContain("paneTitleText(s.surface_id, s.title, s.live_cwd, !!s.exited)");
    expect(main.includes('" [exited]"')).toBe(false);
  });
});
