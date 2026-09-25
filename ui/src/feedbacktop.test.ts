// feedbacktop.test.ts — 피드백 단추(글자 「피드백」) = 상단 메뉴바 맨 앞(「정렬」 바로 왼쪽) · 사이드바 0 · 같은 창 · TICKET=v116-feedback-top.
//
// 박사님 09-26 00:2x 원문: 「피드백 보내기 확인했다. 다만, 메뉴 위치와 크기가 아쉽다. 상단 메뉴바 맨 처음에 넣자. 정렬 메뉴 왼쪽이다.」
// 00:3x 원문: 「1. 피드백 보내기에서 "피드백"으로 변경한다.」 — 단추 글자만(여는 창 제목 「피드백 보내기」·안내 문구 무변경).
// 화면 동작(보이는 크기 · 두 배경 테마 대비 · 누르면 피드백 창)은 docs/v116-ui-evidence/v116-headless.ts c19 가 실번들로 잰다.
// 여기는 자리(html) · 배선(main.ts) · 크기를 줄이는 규칙이 없음(style.css)을 소스 대조로 잰다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
const top = html.slice(html.indexOf('<header id="topbar">'), html.indexOf("</header>"));

describe("피드백 단추 = 상단 메뉴바 맨 앞", () => {
  it("상단바 첫 단추 = 「피드백」(박사님 00:3x 글자 변경) · 그다음 = 정렬", () => {
    const ids = [...top.matchAll(/<button\b[^>]*?\bid="([^"]+)"/g)].map((m) => m[1]); // 속성 순서 무관(적대 1R NIT)
    expect(ids[0]).toBe("btn-feedback");
    expect(ids[1]).toBe("btn-equalize");
    expect(/<button id="btn-feedback"[^>]*>피드백<\/button>/.test(top)).toBe(true);
    expect(top).toContain('title="피드백 — 아쉬운 점이나 문제를 사진·영상과 함께 운영팀에 보냅니다"');
  });

  it("사이드바(상단바 밖)에는 피드백 단추 0 — 한 곳", () => {
    const rest = html.replace(top, "");
    expect(rest).not.toContain('id="ws-feedback"');
    expect(rest).not.toContain('id="btn-feedback"');
    expect(html.split('id="btn-feedback"').length - 1).toBe(1);
  });

  it("누르면 종전과 같은 피드백 창(openFeedbackModal · 창 제목 「피드백 보내기」 그대로)", () => {
    expect(main).toContain('document.getElementById("btn-feedback")!.addEventListener("click", () => void openFeedbackModal());');
    expect(main).not.toContain('getElementById("ws-feedback")');
    expect(main).toContain('<div class="modal feedback-modal"><h3>피드백 보내기</h3>');
  });

  it("크기를 줄이는 규칙 0 — 글자·여백은 상단 단추 공통(#topbar button)을 그대로 쓴다", () => {
    const rules = [...css.matchAll(/([^{}]*#btn-feedback[^{}]*)\{([^}]*)\}/g)].map((m) => m[2]);
    expect(rules.length).toBeGreaterThan(0); // 강조 규칙은 있다
    for (const r of rules) expect(/font-size|padding|font:|height|transform/.test(r)).toBe(false);
    expect(/#ws-feedback\s*\{/.test(css)).toBe(false); // 사이드바 시절 규칙(작은 회색 글자)은 지웠다
  });
});
