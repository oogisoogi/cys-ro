// v116-ui-effort ① — 상단 분할 두 단추를 사이드바 전문가 칸 「창 만들기 · 가로 / 세로」로 옮긴 회귀 핀.
// (박사님 판정 2026-09-23 = C: 「창은 마스터가 만든다 · 초보 화면엔 필요 없다 · 완전 삭제는 금지」)
//
// ★무엇을 재는가 — 세 축을 갈라서 잰다(한 축만 재면 다른 축이 조용히 무너진다):
//   ⑴ 초보 화면 축: 상단 도구줄에 분할 단추가 **없다**. 전문가 칸은 기본 꺼짐이라 초보 화면에 0개다.
//   ⑵ 비상 탈출구 축: 단추 **요소는 지워지지 않았다** — 전문가 칸 안에 정확히 1개씩 있고 클릭이
//      여전히 actionSplit 에 닿는다. 「상단에 없다」만 재면 제거와 이동이 구별되지 않는다.
//   ⑶ 단축키 축: ⌘D·⌘⇧D 가 여전히 actionSplit("row")·actionSplit("col") 을 부른다.
// 런타임 코드 0줄 — index.html·main.ts·style.css 를 데이터로 읽는다(wswiring.test.ts 관례).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
/** HTML 주석을 걷어낸 본문 — 설명 주석이 단언을 깨거나 거짓 초록을 내지 않게 한다. */
const body = html.replace(/<!--[\s\S]*?-->/g, "");
const src = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
/** 주석을 걷어낸 main.ts 코드 — 「코드에 있는가」를 묻는 핀은 주석에 속으면 안 된다. */
const code = src
  .split("\n")
  .map((l) => (l.trimStart().startsWith("//") ? "" : l.replace(/\s\/\/.*$/, "")))
  .join("\n");
const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");

const topbar = body.match(/<header id="topbar">([\s\S]*?)<\/header>/);
const expert = body.match(/<div id="ws-expert"([^>]*)>([\s\S]*?)<\/div><\/div>/);
/**
 * #ws-expert 의 **짝 맞는** 닫는 태그까지를 자른다(div 깊이를 센다).
 * ★정규식 「첫 </div></div> 까지」로는 부족하다 — 묶음을 칸 밖으로 빼 `</div><div>` 로 이어 붙이면
 *   그 정규식은 여전히 묶음을 칸 안으로 읽는다(뮤턴트 U5 가 실제로 살아남았다). 칸 밖 = 숨김 밖 =
 *   초보 화면에 노출이므로, 포함 판정은 반드시 중첩을 따라야 한다.
 */
function expertInner(h: string): string | null {
  const start = h.indexOf('<div id="ws-expert"');
  if (start < 0) return null;
  const re = /<div\b|<\/div>/g;
  re.lastIndex = start;
  let depth = 0;
  for (let m = re.exec(h); m; m = re.exec(h)) {
    depth += m[0] === "</div>" ? -1 : 1;
    if (depth === 0) return h.slice(start, m.index);
  }
  return null;
}
const win = body.match(/<span id="ws-win">([\s\S]*?)<\/span><\/div>/);
/** 태그를 걷어낸 보이는 글자(툴팁 제외) */
const visible = (s: string) => s.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();

describe("⑴ 초보 화면 — 상단 도구줄에서 분할 단추가 사라졌다", () => {
  it("상단 도구줄을 찾았다(못 찾으면 아래 부재 단언은 재지 못한 것이다)", () => {
    expect(topbar).not.toBeNull();
    expect(topbar![1]).toContain('id="btn-new"'); // 도구줄이 통째로 비어서 초록인 경우를 가른다
  });

  it("★상단에 분할 단추 요소가 없다 — id·글자 둘 다", () => {
    expect(topbar![1]).not.toContain('id="btn-split-h"');
    expect(topbar![1]).not.toContain('id="btn-split-v"');
    expect(/split/i.test(visible(topbar![1]))).toBe(false);
  });

  it("★화면에 보이는 글자 어디에도 Split 이 없다 — 상단·사이드바 전부", () => {
    expect(/split/i.test(visible(body))).toBe(false);
  });

  it("전문가 칸은 기본 꺼짐이다 — 그래서 초보 화면의 분할 단추는 0개다", () => {
    expect(expert).not.toBeNull();
    expect(/\bhidden\b/.test(expert![1])).toBe(true);
  });
});

describe("⑵ 비상 탈출구 — 단추는 지우지 않고 전문가 칸 「창 만들기」로 옮겼다", () => {
  it("★두 단추가 전문가 칸 안 「창 만들기」 묶음에 정확히 1개씩 있다", () => {
    expect(win).not.toBeNull();
    const inner = expertInner(body);
    expect(inner).not.toBeNull();
    expect(inner!).toContain('<span id="ws-win">'); // 짝 맞는 칸 안 = 숨김 칸 안
    expect(inner!).toContain('id="btn-split-h"');
    expect(inner!).toContain('id="btn-split-v"');
    for (const id of ["btn-split-h", "btn-split-v"]) {
      expect(win![1]).toContain(`id="${id}"`);
      expect(html.match(new RegExp(`id="${id}"`, "g"))?.length).toBe(1); // 중복 생성 금지
    }
  });

  it("★이름표 = 「창 만들기」 · 가로 = 오른쪽(⌘D) · 세로 = 아래(⌘⇧D)", () => {
    expect(win![1]).toContain('<span id="ws-win-label">창 만들기</span>');
    const h = win![1].match(/<button id="btn-split-h"([^>]*)>([^<]*)<\/button>/);
    const v = win![1].match(/<button id="btn-split-v"([^>]*)>([^<]*)<\/button>/);
    expect(h?.[2]).toBe("가로");
    expect(v?.[2]).toBe("세로");
    expect(h![1]).toContain("오른쪽");
    expect(h![1]).toContain("⌘D");
    expect(v![1]).toContain("아래");
    expect(v![1]).toContain("⌘⇧D");
  });

  it("★왕초보 말투 — 이름표·단추 글자·툴팁에 괄호 0 · 영어 0", () => {
    const texts = [visible(win![1]), ...[...win![1].matchAll(/title="([^"]*)"/g)].map((m) => m[1])];
    for (const t of texts) {
      expect(/[()（）]/.test(t)).toBe(false);
      expect(/split|pane|surface/i.test(t)).toBe(false);
    }
  });

  it("★클릭 배선이 살아 있다 — 가로=row · 세로=col", () => {
    expect(code).toContain('document.getElementById("btn-split-h")!.addEventListener("click", () => actionSplit("row"));');
    expect(code).toContain('document.getElementById("btn-split-v")!.addEventListener("click", () => actionSplit("col"));');
  });

  it("글자 크기가 사이드바 배율에 매여 있다 — 알약과 같은 14px 축", () => {
    for (const sel of ["#ws-win-label", "#ws-expert #btn-split-h, #ws-expert #btn-split-v"]) {
      const esc = sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const block = css.match(new RegExp(`(?:^|\\n)${esc}\\s*\\{([\\s\\S]*?)\\}`));
      expect(block).not.toBeNull();
      expect(block![1].replace(/\s/g, "")).toContain("font-size:calc(14px*var(--wsbar-font,1))");
    }
    // 상단 도구줄 배율(--ui-chrome-scale)을 그대로 끌고 오면 사이드바 A−/A＋ 에 안 따라간다.
    expect(/#ws-win[^{]*\{[^}]*--ui-chrome-scale/.test(css)).toBe(false);
  });
});

describe("⑶ 단축키는 그대로 산다", () => {
  const kd = code.slice(code.indexOf('window.addEventListener("keydown", (e) => {'));
  it("keydown 핸들러를 찾았다", () => {
    expect(kd.length).toBeGreaterThan(100);
  });
  it('★⌘D = actionSplit("row") · ⌘⇧D = actionSplit("col")', () => {
    expect(/e\.key === "d" && !e\.shiftKey\)\s*\{\s*e\.preventDefault\(\);\s*actionSplit\("row"\);/.test(kd)).toBe(true);
    expect(
      /\(e\.key === "D" \|\| e\.key === "d"\) && e\.shiftKey\)\s*\{\s*e\.preventDefault\(\);\s*actionSplit\("col"\);/.test(kd),
    ).toBe(true);
  });
});
