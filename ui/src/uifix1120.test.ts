// uifix1120.test.ts — 1.1.20 화면 작은 고침 묶음 핀(TICKET=cysr-1120-uifix-1126).
//
// 박사님 11-25 밤 원문(1.1.19 를 맥에서 쓰며):
//   ㉮ 「메뉴크기를 190으로 키웠다. 그런데 대화 화면, 작업 화면만 작은 크기 그대로 있다. 그리고 왼쪽 메뉴바 부분 크기는 어떻게 조절하는가?」
//   ㉯ 「a-+ 버튼이 보이지 않아서 하는 말이다.」
//   ㉰ 「사이드바 글자 크기 부분이 흰색 배경에 글자가 거의 인식하기 어렵다. 위치도 수정하고, 잘 보이게 고치자.」
//   ㉱ 「마스터, cso가 각각 2개씩 연이어 있는 이유가 무엇인가?」
// 화면에서 실제로 잰 수치(높이·글자 px·대비)는 작업 폴더 REPORT.md 의 WebKit 렌더 표. 여기는 그 동작을 만드는 소스 모양을 잰다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf8");
const stripCss = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "");
const rulesOf = (css: string) => [...stripCss(css).matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({ sel: m[1].trim(), body: m[2] }));

describe("F1 — 「대화 화면 | 작업 화면」 전환 단추가 메뉴 크기(%)를 따른다", () => {
  const views = rulesOf(read("./views/views.css"));
  const style = rulesOf(read("./style.css"));
  const btn = views.find((r) => r.sel === "#view-switch .vs-group button")!;
  const topBtn = style.find((r) => r.sel === "#topbar button")!;

  it("글자 = 옆 상단 단추와 같은 식 calc(12px × 배율)", () => {
    expect(topBtn.body).toContain("font-size: calc(12px * var(--ui-chrome-scale));");
    expect(btn.body).toContain("font-size: calc(12px * var(--ui-chrome-scale, 1.25));");
  });

  it("높이 = 옆 단추와 같은 위아래 여백 4px(고정 min-height 없음) · 좌우 여백도 배율(기본 125% = 종전 12px)", () => {
    expect(topBtn.body).toContain("padding: 4px 12px;");
    expect(btn.body).toContain("padding: 4px calc(12px * var(--ui-chrome-scale, 1.25) / 1.25);");
    expect(/min-height\s*:/.test(btn.body)).toBe(false);
    expect((12 * 1.25) / 1.25).toBe(12);
  });

  it("전환 단추 관련 규칙에 px 고정 글자 0(13px·28px 고정이 되돌아오지 않게)", () => {
    for (const r of views.filter((x) => x.sel.includes("#view-switch"))) {
      expect(`${r.sel}: ${/font-size:\s*\d+px/.test(r.body)}`).toBe(`${r.sel}: false`);
      expect(`${r.sel}: ${/min-height:\s*\d+px/.test(r.body)}`).toBe(`${r.sel}: false`);
    }
  });

  it("대화 화면 꼴(묶음 안쪽 여백 2px)은 단추 위아래에서 2px 를 덜어 같은 높이", () => {
    const chat = views.find((r) => r.sel === 'body.view-chat #view-switch .vs-group button')!;
    expect(views.find((r) => r.sel === "body.view-chat #view-switch .vs-group")!.body).toContain("padding: 2px;");
    expect(chat.body).toContain("padding-top: 2px; padding-bottom: 2px;");
  });
});

describe("F2 — 「왼쪽 목록 글자 크기」 = 글자·배경 구획 · 메뉴 크기(%) 바로 아래 · 지금 배율 % 표시 · 전문가에서 뺌", () => {
  const main = read("./main.ts")
    .split("\n")
    .map((l) => (l.trimStart().startsWith("//") ? "" : l.replace(/\s\/\/.*$/, "")))
    .join("\n");
  const pop = (() => {
    const i = main.indexOf("function openThemePopover(");
    return main.slice(i, main.indexOf("\n}\n", i));
  })();
  const fnBody = (name: string) => {
    const i = main.indexOf(`function ${name}(`);
    return main.slice(i, main.indexOf("\n}\n", i));
  };

  it("글자·배경 구획에서 menuSizeRow 바로 다음 줄 · 이름 「왼쪽 목록 글자 크기」(옛 「사이드바 글자 크기」 글 0)", () => {
    expect(pop).toContain("menuWeightRow, menuSizeRow, wsFontRow,");
    expect(pop).toContain('wsFontRow.textContent = "왼쪽 목록 글자 크기";');
    expect(main.includes('"사이드바 글자 크기"')).toBe(false);
  });

  it("전문가 구획에는 없다(줄 하나 = 입구 하나)", () => {
    const ex = pop.slice(pop.indexOf("expert.body.append("), pop.indexOf(";", pop.indexOf("expert.body.append(")));
    expect(ex.includes("wsFontRow")).toBe(false);
    expect((pop.match(/\.append\([^)]*wsFontRow/g) ?? []).length).toBe(1);
  });

  it("지금 배율을 % 로 — 열 때 · 누를 때 · 기본값 되돌릴 때 다시 적는다", () => {
    expect(pop).toContain("const syncWsFontPct = () => { wsFontPct.textContent = `${Math.round(wsbarFont * 100)}%`; };");
    expect(pop).toContain('b.addEventListener("click", () => { applyWsbarFontStep(dir); syncWsFontPct(); }); return b;');
    expect(pop).toContain("wsFontCtl.append(wsFontPct, mkWsFont(\"A−\", -1,");
    expect(pop).toContain("resetWsbarFont(); syncWsFontPct();");
    expect(Math.round(1.1 * 100)).toBe(110);
  });

  it("「이 구획만 기본값으로」 = 배율 1(100%) · 저장 지움 · 사용량 줄 다시 그림(applyWsbarFontStep 과 같은 뒤처리)", () => {
    const r = fnBody("resetWsbarFont");
    expect(r).toContain("wsbarFont = 1;");
    expect(r).toContain("applyWsbarVars();");
    expect(r).toContain('localStorage.removeItem("cys-wsbar-font");');
    expect(r).toContain("renderSidebarUsage([...lastSurfacesBySocket.values()].flat());");
    expect(main).toContain('clampWsbarFont(Number(localStorage.getItem("cys-wsbar-font")) || 1)');
  });

  it("조절부 묶음 꼴은 em 만(팝오버 두 축 금지 규칙 그대로)", () => {
    const style = rulesOf(read("./style.css"));
    for (const sel of ["#theme-pop .sp-wsfont", "#theme-pop .sp-wsfont-pct"]) {
      const r = style.find((x) => x.sel === sel);
      expect({ sel, 있음: !!r }).toEqual({ sel, 있음: true });
      expect(/\dpx/.test(r?.body ?? "")).toBe(false);
    }
  });
});

describe("F3 — 화면 설정 팝오버 단추 기본 꼴 = 어두운 바탕 · 밝은 글자(브라우저 기본 흰 바탕이 새지 않게)", () => {
  const style = rulesOf(read("./style.css"));
  const base = style.find((r) => r.sel === "#theme-pop button");

  it("#theme-pop button 단독 규칙이 바탕·테두리를 준다(글자색만 주던 공용 규칙 하나로는 흰 바탕이 샌다)", () => {
    expect({ 있음: !!base }).toEqual({ 있음: true });
    expect(base!.body).toContain("background: var(--bar);");
    expect(base!.body).toContain("border: 1px solid var(--border);");
    // 공용 규칙(글자 물려받기 · 밝은 글자)은 그대로
    expect(style.find((r) => r.sel === "#theme-pop button, #theme-pop select, #theme-pop input")!.body).toContain("color: var(--text);");
  });

  it("팝오버 단추 규칙 가운데 흰/밝은 바탕을 주는 것 0(밝은 글자 --text 위에)", () => {
    for (const r of style.filter((x) => x.sel.includes("#theme-pop") && /button|reset|toggle|move|head|sp-/.test(x.sel))) {
      const m = /background(?:-color)?\s*:\s*([^;]+)/.exec(r.body);
      if (!m) continue;
      expect(`${r.sel}: ${/#fff\b|#ffffff|white|#e[0-9a-f]{5}|#f[0-9a-f]{5}/i.test(m[1])}`).toBe(`${r.sel}: false`);
    }
  });

  it("대비 계산(WCAG 2.x 상대 휘도) — 밝은 글자 #c9d1d9 : 바탕 #161b22 ≥ 4.5 · 종전 #c9d1d9 : #c0c0c0 < 1.5", () => {
    const lum = (hex: string) => {
      const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
      return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    };
    const ratio = (a: string, b: string) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
    const css = read("./style.css");
    expect(css).toContain("--bar: #161b22;");
    expect(css).toContain("--text: #c9d1d9;");
    expect(ratio("#c9d1d9", "#161b22")).toBeGreaterThan(4.5);
    expect(ratio("#c9d1d9", "#c0c0c0")).toBeLessThan(1.5);
  });

  it("두 축 금지 그대로 — 새 규칙에 px 는 테두리·모서리뿐 · font-size 없음", () => {
    for (const d of base!.body.split(";").map((x) => x.trim()).filter(Boolean)) {
      const prop = d.slice(0, d.indexOf(":")).trim();
      if (/^(border|border-radius)$/.test(prop)) continue;
      expect(`${d} px=${/\dpx/.test(d)}`).toBe(`${d} px=false`);
    }
    expect(/font-size/.test(base!.body)).toBe(false);
  });
});

describe("F4 — 곁 목록 이름 보고자 줄(master·cso)이 같은 이름을 두 번 그리지 않는다", () => {
  it("원인 재현: 이름 보고자 입력은 label 과 title 이 같은 이름이다(번호 칸 + 이름 칸)", async () => {
    const { namedSeatInputs } = await import("./seatrows");
    const [m] = namedSeatInputs([{ name: "master", ctxPct: 64 }]);
    expect([m.label, m.title]).toEqual(["master", "master"]);
  });

  it("고침: 줄 모델 = 번호 칸 「master」 · 이름 칸 비움(「cso」 도 같음) · named 표식 그대로", async () => {
    const { namedSeatInputs, buildSeatRows } = await import("./seatrows");
    const m = buildSeatRows(namedSeatInputs([{ name: "master", ctxPct: 64 }, { name: "cso", ctxPct: 27 }]));
    expect(m.fixed.map((r) => [r.no, r.name, r.named])).toEqual([["master", "", true], ["cso", "", true]]);
  });

  it("번호가 있는 보통 좌석은 무변경(「566 agy검증」)", async () => {
    const { buildSeatRows } = await import("./seatrows");
    const m = buildSeatRows([{ sid: 9, displayNo: 566, role: "worker", title: "566 · Opus · agy검증", cwd: "/w/agy-handoff", exited: false, dot: "waiting", approvalPending: false, statusState: null, task: null, ctxPct: null, ctxSrc: "none" }]);
    expect([m.groups[0].rows[0].no, m.groups[0].rows[0].name]).toEqual(["566", "agy검증"]);
  });

  it("그려진 줄 글 = 「master」 한 번 · 툴팁 = 「master (화면 밖 보고자)」(「(이름 없음)」 아님)", async () => {
    const { namedSeatInputs, buildSeatRows } = await import("./seatrows");
    const { seatRowTitle } = await import("./seatrowsdom");
    const [r] = buildSeatRows(namedSeatInputs([{ name: "master", ctxPct: 64 }])).fixed;
    expect(`${r.no} ${r.name}`.trim().split(/\s+/)).toEqual(["master"]);
    const t = seatRowTitle(r);
    expect(t.split("\n")[0]).toBe("master (화면 밖 보고자)");
    expect(t.includes("(이름 없음)")).toBe(false);
  });

  it("남는 한 칸은 이름 글자색(밝게) — .ws-seat.named .ws-seat-no", () => {
    const r = rulesOf(read("./style.css")).find((x) => x.sel === ".ws-seat.named .ws-seat-no");
    expect(r?.body.trim()).toBe("color: var(--text);");
  });
});

// ── 2차(master#e7ebb977 「같은 병」 셋) — F5~F7 ──
const lumHex = (hex: string) => {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const contrast = (a: string, b: string) => { const x = lumHex(a), y = lumHex(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
/** 알파 합성(글자/바탕 색 p% 를 바탕 위에) — color-mix(in srgb, A p%, transparent) 를 바탕 B 위에 얹은 색 */
const mixHex = (a: string, b: string, p: number) =>
  "#" + [1, 3, 5].map((i) => Math.round(parseInt(a.slice(i, i + 2), 16) * p + parseInt(b.slice(i, i + 2), 16) * (1 - p)).toString(16).padStart(2, "0")).join("");

describe("F5 — 대화 화면 상단 「피드백」 글자가 밝은 테마 흰 띠 위에서도 보인다(≥ 4.5:1)", () => {
  const views = rulesOf(read("./views/views.css"));
  const fb = views.find((r) => r.sel === "body.view-chat #topbar #btn-feedback");

  it("대화 화면 전용 규칙이 있고 선택자가 style.css `#topbar #btn-feedback` 보다 세다(id 2 + class 1)", () => {
    expect({ 있음: !!fb }).toEqual({ 있음: true });
    expect(fb!.body).toContain("color: var(--cv-accent);");
    expect(fb!.body).toContain("background: color-mix(in srgb, var(--cv-accent) 10%, transparent);");
    expect(rulesOf(read("./style.css")).find((r) => r.sel === "#topbar #btn-feedback")!.body).toContain("color: #fff;"); // 작업 화면 강조는 그대로
  });

  it("크기 규칙 0(상단 단추 공통 그대로 · feedbacktop.test.ts 와 같은 뜻)", () => {
    for (const r of views.filter((x) => x.sel.includes("#btn-feedback"))) expect(/font-size|padding|font:|height|transform/.test(r.body)).toBe(false);
  });

  it("계산 대비 — 밝은 테마(--cv-accent #2d5bcb · 띠 #ffffff) · 어두운 테마(#7ea2ff · 띠 #15181e) 둘 다 ≥ 4.5 · 종전 흰 글자 / #d1e3fd = 1.3", () => {
    const css = read("./views/views.css");
    expect(css).toContain("--cv-accent: #2d5bcb;");
    expect(css).toContain("--cv-accent: #7ea2ff;");
    expect(contrast("#2d5bcb", mixHex("#2d5bcb", "#ffffff", 0.1))).toBeGreaterThan(4.5);
    expect(contrast("#7ea2ff", mixHex("#7ea2ff", "#15181e", 0.1))).toBeGreaterThan(4.5);
    expect(contrast("#ffffff", "#d1e3fd")).toBeLessThan(1.5);
  });
});

describe("F6 — 눌린 전환 단추 글자 = 토큰(--cv-on-accent) · 다크 모드 2.47:1 → ≥ 4.5 · 밝은 테마 무변", () => {
  const css = read("./views/views.css");
  const views = rulesOf(css);

  it("눌린 단추 글자가 #fff 고정이 아니라 토큰", () => {
    const r = views.find((x) => x.sel === '#view-switch .vs-group button[aria-pressed="true"]')!;
    expect(r.body).toContain("color: var(--cv-on-accent);");
    expect(/color:\s*#fff/.test(r.body)).toBe(false);
  });

  it("토큰 값 — 밝은 테마 #ffffff(종전과 같음) · 다크 #15181e(다크 분기 안)", () => {
    const light = views.find((x) => x.sel === ":root" && x.body.includes("--cv-accent: #2d5bcb;"))!;
    expect(light.body).toContain("--cv-on-accent: #ffffff;");
    const darkBlock = css.slice(css.indexOf("@media (prefers-color-scheme: dark)"), css.indexOf("}", css.indexOf("--cv-accent: #7ea2ff;")));
    expect(darkBlock).toContain("--cv-on-accent: #15181e;");
  });

  it("계산 대비 — 밝은 #ffffff / #2d5bcb ≥ 4.5(무변) · 다크 #15181e / #7ea2ff ≥ 4.5 · 종전 다크 #ffffff / #7ea2ff < 3", () => {
    expect(contrast("#ffffff", "#2d5bcb")).toBeGreaterThan(4.5);
    expect(contrast("#15181e", "#7ea2ff")).toBeGreaterThan(4.5);
    expect(contrast("#ffffff", "#7ea2ff")).toBeLessThan(3);
  });
});

describe("F7 — 「cysr」 글자·아이콘 단추 규칙도 메뉴 크기(%)를 따른다(기본 125% = 종전 크기)", () => {
  const style = rulesOf(read("./style.css"));
  const at = (expr: string, scale: number) => Function(`return ${expr.replace(/px/g, "").replace(/var\(--ui-chrome-scale\)/g, String(scale)).replace(/^calc/, "")}`)() as number;

  it("#brand 글자 = calc(13px × 배율 / 1.25) → 100% 10.4 · 125% 13(종전 body 13px 와 같음) · 190% 19.76", () => {
    const b = style.find((r) => r.sel === "#brand")!;
    const m = /font-size:\s*(calc\([^;]+\));/.exec(b.body)!;
    expect(m[1]).toBe("calc(13px * var(--ui-chrome-scale) / 1.25)");
    expect([at(m[1], 1), at(m[1], 1.25), at(m[1], 1.9)].map((v) => Math.round(v * 100) / 100)).toEqual([10.4, 13, 19.76]);
  });

  it(".icon-btn 폭·높이·아이콘 = 배율 식 · 125% 에서 종전 28×26 · 16px", () => {
    const b = style.find((r) => r.sel === "#topbar button.icon-btn")!;
    const w = /width:\s*(calc\([^;]+\));/.exec(b.body)![1], h = /height:\s*(calc\([^;]+\));/.exec(b.body)![1];
    const svg = /width:\s*(calc\([^;]+\));/.exec(style.find((r) => r.sel === "#topbar button.icon-btn svg")!.body)![1];
    expect([at(w, 1.25), at(h, 1.25), at(svg, 1.25)]).toEqual([28, 26, 16]);
    expect(/\b(28|26|16)px;/.test(b.body)).toBe(false);
  });

  it("1.1.19 화면에 .icon-btn 을 쓰는 요소는 없다(+New·Split 은 글자 단추 — 공통 #topbar button 규칙이 이미 배율을 따름)", () => {
    const html = read("../index.html");
    const main = read("./main.ts");
    expect(html.includes("icon-btn")).toBe(false);
    expect(main.includes("icon-btn")).toBe(false);
    expect(/<button id="btn-new"[^>]*>\+ New<\/button>/.test(html)).toBe(true);
  });
});

describe("F8 — 대화 화면 보내기 단추(.cv-send) 글자 = 토큰(--cv-on-accent)", () => {
  it("#fff 고정이 아니라 토큰 · 바탕 = --cv-accent 그대로 · 비활성 꼴 무변", () => {
    const views = rulesOf(read("./views/views.css"));
    const r = views.find((x) => x.sel === ".cv-send")!;
    expect(r.body).toContain("background: var(--cv-accent); color: var(--cv-on-accent);");
    expect(/color:\s*#fff/.test(r.body)).toBe(false);
    expect(views.find((x) => x.sel === ".cv-send:disabled")!.body).toContain("color: var(--cv-sub);");
  });
});
