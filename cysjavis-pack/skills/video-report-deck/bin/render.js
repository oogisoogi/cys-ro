// 프레임 렌더 — plan.json 의 frames 마다 deck.html 의 renderFrame() 을 불러 1920×1080 PNG 로 찍는다.
// 사용: node render.js <plan.json> <frames-dir>
// 종료 코드: 0 성공 · 1 렌더 오류 · 2 사용법 · 4 의존(playwright·브라우저) 없음
const fs = require("fs");
const path = require("path");

const SKILL_DIR = path.resolve(__dirname, "..");
const FONT_DIR = path.join(SKILL_DIR, "fonts");
const FONT_URL = "https://github.com/orioncactus/pretendard/releases/tag/v1.3.9";
const FONT_FILES = ["Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Black"].map(w => `Pretendard-${w}.woff2`);

function need(lines) {
  for (const l of lines) console.error(l);
  process.exit(4);
}

// playwright 는 이 스킬 폴더의 node_modules 에서 보통 방식으로 찾는다
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (e) {
  if (e && e.code !== "MODULE_NOT_FOUND") throw e;
  need([
    "없음 playwright(Node 모듈) — 이 스킬 폴더에서 한 번 설치한다:",
    `  cd "${SKILL_DIR}" && npm i && npx playwright install chromium`,
  ]);
}

(async () => {
  const [planPath, outDir] = process.argv.slice(2);
  if (!planPath || !outDir) {
    console.error("사용: node render.js <plan.json> <frames-dir>");
    process.exit(2);
  }
  const plan = JSON.parse(fs.readFileSync(planPath, "utf8"));
  // 브라우저는 playwright 가 자기 버전에 맞춰 받아 둔 것을 쓴다(경로를 손으로 고정하지 않는다)
  const exe = chromium.executablePath();
  if (!exe || !fs.existsSync(exe)) need([
    "없음 playwright 용 크롬 — 이 스킬 폴더에서 한 번 받는다:",
    `  cd "${SKILL_DIR}" && npx playwright install chromium`,
  ]);
  let browser;
  try {
    browser = await chromium.launch();
  } catch (e) {
    if (/Executable doesn't exist|playwright install/i.test(String(e && e.message))) need([
      "없음 playwright 용 헤드리스 크롬 — 이 스킬 폴더에서 한 번 받는다:",
      `  cd "${SKILL_DIR}" && npx playwright install chromium`,
    ]);
    throw e;
  }
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const warns = new Set();
  page.on("console", m => { if (m.type() === "warning") warns.add(m.text()); });
  await page.goto("file://" + path.join(SKILL_DIR, "deck.html"));
  // 글꼴을 미리 다 불러 둔다(첫 장면이 대체 글꼴로 찍히지 않게) — 파일이 없으면 load 가 NetworkError 로 거절되므로 삼키고 대체 글꼴로 간다
  await page.evaluate(async () => {
    const tryLoad = f => document.fonts.load(f, "가A1").catch(() => null);
    for (const w of [400, 500, 600, 700, 800, 900]) await tryLoad(`${w} 40px Pretendard`);
    await tryLoad("700 40px 'JetBrains Mono'");
    await document.fonts.ready;
  });
  const ok = await page.evaluate(() => document.fonts.check("800 40px Pretendard", "가"));
  if (!ok) {
    // 팩은 글꼴 파일을 싣지 않는다 — 없으면 시스템 고딕(tokens.css --sans 다음 글꼴)으로 찍고 받는 곳을 알린다
    console.log("알림 Pretendard 글꼴이 없어 시스템 고딕으로 찍는다. 쓰려면:");
    console.log(`  ${FONT_URL} 에서 Pretendard-1.3.9.zip 을 받아 web/static/woff2/ 의 ${FONT_FILES.join(" ")} 를`);
    console.log(`  "${FONT_DIR}" 에 둔다(또는 기기에 설치 · SIL OFL 1.1 · https://github.com/orioncactus/pretendard/blob/main/LICENSE).`);
  }
  for (const f of plan.frames) {
    await page.evaluate(([deck, scene, fr]) => window.renderFrame(deck, scene, fr), [plan.deck, plan.scenes[f.scene], f]);
    await page.screenshot({ path: path.join(outDir, f.png) });
  }
  await browser.close();
  console.log("frames", plan.frames.length);
  for (const w of warns) console.log("경고", w);
})().catch(e => { console.error(e); process.exit(1); });
