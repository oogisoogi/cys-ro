#!/usr/bin/env node
// cmux(Ghostty) 렌더 정합 게이트 — 헤드리스 WebKit(레티나 2배)에서 xterm 칸 크기·배경·한글 맞춤을 잰다
// (수동 · CI 미배선 · TICKET=cysr-cmux-render-parity 2026-10-29).
//
// 기대값 근거 = Ghostty src/font/Metrics.zig calc(장치 화소 @round) 를 CoreText 실측 글꼴 값에 적용한 결과:
//   JetBrains Mono 13pt → 칸 8×17 css px · 한글(Apple SD Gothic Neo) 1.214배 · 배경 #1e1e1e
//   동봉 JetBrains Mono(ui/fonts · TICKET=cysr-bundle-jetbrains-mono) → 설치 글꼴 이름을 뺀 스택(@nosys)에서도 8×17 · 한글 1.214
//   D2Coding 13pt → 칸 폭 6.5(높이는 WebKit 이 글꼴 line gap 을 빼고 재서 14 — Ghostty 15 와 1px 차 · 알려진 차이)
// 「수정 전」 모드(old)는 대조용으로만 잰다 — 사용자 설치 글꼴이 OffscreenCanvas 에서 안 보여 Menlo 로 잰 칸(7.83×15).
//
// 실행: PW_CORE=<playwright-core 경로> node ui/e2e/render_parity/gate.mjs [캡처 폴더]
//   · playwright-core 1.63 + webkit-2359 실측(2026-10-29). 맥 전용(JetBrains Mono·D2Coding 설치 기기).
//   · exit 0 = 전부 PASS · 1 = 불일치 · 2 = 환경 없음
import { execFileSync } from "child_process";
import { readFileSync, writeFileSync, mkdtempSync, mkdirSync, copyFileSync } from "fs";
import { tmpdir } from "os";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
const here = dirname(fileURLToPath(import.meta.url));
const UI = join(here, "..", "..");
const PW = process.env.PW_CORE;
if (!PW) { console.error("PW_CORE(playwright-core 폴더) 가 필요하다"); process.exit(2); }
const { webkit } = await import(join(PW, "index.mjs"));
const out = process.argv[2] || mkdtempSync(join(tmpdir(), "render-parity-"));
const bundle = join(out, "bundle.js");
execFileSync("bun", ["build", join(here, "harness.ts"), "--outfile", bundle, "--target", "browser"], { cwd: UI, stdio: "inherit" });
const html = `<!doctype html><html><head><meta charset="utf-8">
<style>${readFileSync(join(UI, "node_modules/@xterm/xterm/css/xterm.css"), "utf8")}</style>
<style>html,body{margin:0;-webkit-font-smoothing:antialiased;background:#222}#t{width:960px;height:420px}</style>
</head><body><div id="t"></div><script>${readFileSync(bundle, "utf8")}</script></body></html>`;
const page = join(out, "page.html");
writeFileSync(page, html);
// 동봉 글꼴을 앱과 같은 상대 경로(./fonts/)에 둔다. GATE_MUTANT=nofonts = 파일을 빼서 게이트가 잡는지 본다(뮤턴트).
if (process.env.GATE_MUTANT !== "nofonts") {
  mkdirSync(join(out, "fonts"), { recursive: true });
  for (const f of ["JetBrainsMono-wght.ttf", "JetBrainsMono-Italic-wght.ttf"]) copyFileSync(join(UI, "fonts", f), join(out, "fonts", f));
}
const b = await webkit.launch();
let fail = 0;
const check = (name, ok, got) => { console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${JSON.stringify(got)}`); if (!ok) fail++; };
const shots = {};
for (const mode of ["old", "new", "old:D2Coding", "new:D2Coding", "new:@nosys", "new:@sysonly"]) {
  const pg = await b.newPage({ deviceScaleFactor: 2, viewport: { width: 1000, height: 460 } });
  await pg.goto("file://" + page);
  const r = await pg.evaluate((m) => window.__run(m), mode);
  await pg.locator("#t").screenshot({ path: join(out, `${mode.replace(":", "-")}.png`) });
  // 글자 줄(0~4 = 라틴·한글·색) 만 따로 찍는다 — 5~6 줄 상자 문자(─)는 칸 이음매 안티앨리어스가 웹 글꼴·설치 글꼴에서
  // 다르게 겹친다(같은 바이트 · 이음매 화소만 최대 48/255 · 2026-10-29 실측) — 글리프 동일성 판정에서 뺀다.
  shots[mode] = Buffer.concat(await Promise.all([0, 1, 2, 3, 4].map((i) => pg.locator(".xterm-rows > div").nth(i).screenshot())));
  await pg.close();
  const c = r.cssCell;
  if (mode === "new") {
    check("JetBrains Mono 칸 = 8×17", c.width === 8 && c.height === 17, c);
    check("배경 = #1e1e1e", r.bgPixelCss === "rgb(30, 30, 30)", r.bgPixelCss);
    check("한글 맞춤 글꼴 적재(배율 1.214)", r.fontFamily.includes("cys-hangul-fit-1214") && r.hangulFont.some((f) => f.includes("cys-hangul-fit-1214:normal:loaded")), r.hangulFont);
  } else if (mode === "new:D2Coding") {
    check("D2Coding 칸 폭 = 6.5(설치 글꼴로 잼)", c.width === 6.5, c);
    check("D2Coding 은 한글 맞춤 없음(자체 한글)", !r.fontFamily.includes("cys-hangul-fit"), r.fontFamily);
  } else if (mode === "new:@nosys") {
    // 글꼴 미설치 기기 흉내 — 스택에 설치 글꼴 이름이 없으니 8×17 은 동봉 글꼴로만 나온다(Menlo 면 8×15).
    check("미설치 환경: 동봉 글꼴 적재(정자·기울임)", r.bundled.includes("normal:loaded") && r.bundled.includes("italic:loaded"), r.bundled);
    check("미설치 환경: 칸 = 8×17(동봉 JetBrains Mono)", c.width === 8 && c.height === 17, c);
    check("미설치 환경: 한글 맞춤 배율 1.214(동봉 글꼴 기준으로 다시 잼)", r.fontFamily.includes("cys-hangul-fit-1214"), r.fontFamily);
  } else if (mode === "new:@sysonly") {
    // 대조군 — 설치된 JetBrains Mono(같은 2.304 바이트)로 그린 그림과 동봉 글꼴 그림이 화소까지 같아야 한다.
    check("글리프 = 동봉 글꼴(미설치 그림 == 설치 글꼴 그림 · 글자 줄 0~4 화소 일치)", Buffer.compare(shots["new:@nosys"], shots[mode]) === 0, { cell: c });
  } else {
    console.log(`관측 ${mode} — 칸 ${JSON.stringify(c)} · 배경 ${r.bgPixelCss}`);
  }
}
await b.close();
console.log(`캡처 = ${out}`);
process.exit(fail ? 1 : 0);
