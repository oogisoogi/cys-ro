// termrender.ts 순수 계산 회귀 테스트 — cmux(Ghostty) 셀 크기·한글 맞춤 배율 (TICKET=cysr-cmux-render-parity).
//
// 기대값의 근거 = CoreText 로 잰 글꼴 값(2026-10-29 · ~/Library/Fonts + 시스템 글꼴):
//   JetBrains Mono: W 폭 600/1000 · hhea 1020/-300/0 · ASCII 외곽 높이 1050/1000 · 「水」 없음
//   Apple SD Gothic Neo: 「水」「한」 폭 865/1000
// 계산식 근거 = Ghostty src/font/Metrics.zig calc(@round) · Collection.zig scaleFactor(.ic_width).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { ghosttyCellCss, hangulFitScale, hangulFitFamily, withHangulFit, HANGUL_UNICODE_RANGE, BUNDLED_FONT_FILES, loadBundledFont, remeasureCells } from "./termrender";
import { BUNDLED_FONT_FAMILY, DEFAULT_FONT_STACK, composeFontFamily } from "./appearance";

describe("ghosttyCellCss — 장치 화소 반올림", () => {
  it("JetBrains Mono 13pt·레티나(2배) = 8×17 css px(Ghostty 16×34 장치px)", () => {
    expect(ghosttyCellCss(0.6 * 13, 2)).toBe(8); // 15.6 → 16
    expect(ghosttyCellCss(1.32 * 13, 2)).toBe(17); // 34.32 → 34
  });
  it("1배 화면도 반올림(7.8→8 · 17.16→17)", () => {
    expect(ghosttyCellCss(7.8, 1)).toBe(8);
    expect(ghosttyCellCss(17.16, 1)).toBe(17);
  });
  it("xterm 구 방식과 다르다 — 폭 미반올림(7.8)·높이 올림(17.5)이 아니다", () => {
    expect(ghosttyCellCss(7.8, 2)).not.toBe(7.8);
    expect(ghosttyCellCss(17.16, 2)).not.toBe(17.5);
  });
  it("0·음수·NaN 은 손대지 않는다", () => {
    expect(ghosttyCellCss(0, 2)).toBe(0);
    expect(Number.isNaN(ghosttyCellCss(NaN, 2))).toBe(true);
    expect(ghosttyCellCss(7.8, 0)).toBe(7.8);
  });
  it("아주 작은 값도 최소 1 장치px", () => {
    expect(ghosttyCellCss(0.1, 2)).toBe(0.5);
  });
});

describe("hangulFitScale — Ghostty ic_width 배율", () => {
  it("JetBrains Mono + Apple SD Gothic Neo = min(1.05, 1.2)/0.865 ≈ 1.214", () => {
    expect(hangulFitScale(0.6, 1.05, 0.865)).toBe(1.214);
  });
  it("ASCII 높이가 두 칸보다 크면 두 칸 폭이 기준(Menlo 1.054 > 1.204? 아니오 → 1.054)", () => {
    expect(hangulFitScale(0.602, 1.054, 0.865)).toBe(1.218);
    expect(hangulFitScale(0.5, 1.5, 1.0)).toBe(1); // 2×0.5=1.0 / 1.0
  });
  it("ASCII 높이를 못 재면 두 칸 폭", () => {
    expect(hangulFitScale(0.6, 0, 1.0)).toBe(1.2);
  });
  it("비정상 입력·터무니없는 배율은 1", () => {
    expect(hangulFitScale(0, 1, 1)).toBe(1);
    expect(hangulFitScale(0.6, 1, 0)).toBe(1);
    expect(hangulFitScale(0.6, 1, NaN)).toBe(1);
    expect(hangulFitScale(0.6, 1.2, 0.3)).toBe(1); // 4배
    expect(hangulFitScale(0.1, 0.2, 1)).toBe(1); // 0.2배
  });
});

describe("withHangulFit — 글꼴 스택에 끼우기", () => {
  it("한글 대체 글꼴 바로 앞에 들어간다(라틴 글꼴 순서 불변)", () => {
    const s = withHangulFit(DEFAULT_FONT_STACK, "cys-hangul-fit-1214");
    expect(s).toContain("Consolas, 'cys-hangul-fit-1214', 'Apple SD Gothic Neo'");
    expect(s.startsWith("'cys JetBrains Mono', 'JetBrains Mono', Menlo")).toBe(true);
  });
  it("사용자가 고른 글꼴은 맨 앞 그대로(한글 있는 D2Coding 이 먼저 잡힌다)", () => {
    const s = withHangulFit(composeFontFamily("D2Coding"), "cys-hangul-fit-1214");
    expect(s.startsWith("'D2Coding', ")).toBe(true);
    expect(s.indexOf("'D2Coding'")).toBeLessThan(s.indexOf("cys-hangul-fit"));
  });
  it("기준 글꼴이 없으면 끝에 붙이고, 맞춤 없음(null)이면 그대로", () => {
    expect(withHangulFit("Menlo, monospace", "x")).toBe("Menlo, monospace, 'x'");
    expect(withHangulFit(DEFAULT_FONT_STACK, null)).toBe(DEFAULT_FONT_STACK);
  });
  it("가족 이름은 배율마다 다르다(배율이 바뀌면 xterm 이 다시 잰다)", () => {
    expect(hangulFitFamily(1.214)).toBe("cys-hangul-fit-1214");
    expect(hangulFitFamily(1.218)).not.toBe(hangulFitFamily(1.214));
  });
  it("배율은 한글만 — 한자·구두점·상자 그림 문자는 범위 밖", () => {
    expect(HANGUL_UNICODE_RANGE).toContain("U+AC00-D7AF");
    expect(HANGUL_UNICODE_RANGE).not.toContain("4E00");
    expect(HANGUL_UNICODE_RANGE).not.toContain("2500");
  });
});

// 동봉 글꼴(TICKET=cysr-bundle-jetbrains-mono) — 파일·라이선스·sha256 핀 · 등록 방식.
// sha256 = JetBrains/JetBrainsMono v2.304 릴리스 zip(6f6376c6…7bbf) 의 fonts/variable/*[wght].ttf · OFL.txt 원본 그대로.
describe("동봉 JetBrains Mono", () => {
  const file = (rel: string) => readFileSync(new URL(`../${rel}`, import.meta.url));
  const sha = (rel: string) => createHash("sha256").update(file(rel)).digest("hex");
  it("파일·OFL 이 공식 릴리스 바이트 그대로 동봉돼 있다", () => {
    expect(sha("fonts/JetBrainsMono-wght.ttf")).toBe("662a196d58f1183bf2d77428b6d5283fe3f45161ab021bea4036bc98e5cac016");
    expect(sha("fonts/JetBrainsMono-Italic-wght.ttf")).toBe("f115aaa12113718c02ce72864fe6823b87241bc23d3e44cf1220155f861063f2");
    expect(sha("fonts/OFL.txt")).toBe("30f0c136e3c88e422d0791acd97238870f9054a9729bc34cf2ff0d4ed8cac4ad");
  });
  it("build.sh 가 글꼴과 OFL 을 dist/fonts 로 복사한다(로더 경로와 같은 이름)", () => {
    const sh = readFileSync(new URL("../build.sh", import.meta.url), "utf8");
    for (const { url } of BUNDLED_FONT_FILES) expect(sh).toContain(url.replace("./fonts/", "fonts/"));
    expect(sh).toContain("fonts/OFL.txt");
    expect(sh).toContain("dist/fonts/");
  });
  it("기본 스택 맨 앞 = 동봉 별명(설치 글꼴 이름과 겹치지 않음) · 고른 글꼴은 그 앞", () => {
    expect(BUNDLED_FONT_FAMILY).not.toBe("JetBrains Mono");
    expect(DEFAULT_FONT_STACK.startsWith(`'${BUNDLED_FONT_FAMILY}', `)).toBe(true);
    expect(composeFontFamily("D2Coding").startsWith("'D2Coding', 'cys JetBrains Mono', ")).toBe(true);
  });
  it("문서 글꼴 목록에 정자·기울임 2개를 가변 굵기(100~800)로 한 번만 올리고, 정자 결과를 돌려준다", async () => {
    const added: { family: string; src: string; desc: FontFaceDescriptors }[] = [];
    const g = globalThis as any;
    const saved = { document: g.document, FontFace: g.FontFace };
    g.document = { fonts: { add: () => {} } };
    g.FontFace = class { constructor(public family: string, public src: string, public desc: FontFaceDescriptors) { added.push(this as any); }
      load() { return this.desc.style === "italic" ? Promise.reject(new Error("x")) : Promise.resolve(this); } };
    try {
      const a = loadBundledFont();
      const b = loadBundledFont();
      expect(a).toBe(b); // 한 번만
      expect(await a).toBe(true); // 기울임이 실패해도 정자가 올라오면 true
      expect(added.map((f) => [f.family, f.desc.weight, f.desc.style])).toEqual([
        [BUNDLED_FONT_FAMILY, "100 800", "normal"], [BUNDLED_FONT_FAMILY, "100 800", "italic"],
      ]);
      expect(added[0].src).toBe("url('./fonts/JetBrainsMono-wght.ttf') format('truetype')");
    } finally { g.document = saved.document; g.FontFace = saved.FontFace; }
  });
});

describe("remeasureCells — 동봉 글꼴이 늦게 올라왔을 때", () => {
  it("글꼴 설정 문자열이 그대로여도 칸을 다시 재고 글자 폭 캐시를 비운다", () => {
    const calls: string[] = [];
    remeasureCells({ _core: { _charSizeService: { measure: () => calls.push("measure") }, _renderService: { handleCharSizeChanged: () => calls.push("widths") } },
      refresh: () => calls.push("refresh"), rows: 3 });
    expect(calls).toEqual(["measure", "widths", "refresh"]);
  });
  it("xterm 내부 모양이 다르면 아무것도 안 한다(던지지 않음)", () => {
    expect(() => remeasureCells({})).not.toThrow();
  });
});
