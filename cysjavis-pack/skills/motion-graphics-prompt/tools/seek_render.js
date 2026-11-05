// 시간 고정 렌더 — window.seek(t) 가 있는 HTML 한 장을 스틸컷·프레임·mp4 로 찍는다.
// 사용:
//   스틸만  node seek_render.js <page.html> --out <폴더> --stills 2.5,11
//   영상    node seek_render.js <page.html> --out <폴더> --duration 15 [--fps 30] [--subframes 3] [--audio a.wav]
// 규칙: 화면은 오직 seek(t) 가 정한다(CSS 애니메이션·타이머·프레임 간 상태 금지). 스틸마다 결정론 검사를 한다 —
//       같은 t 를 「처음」과 「다른 시각을 거친 뒤」 두 번 찍어 바이트가 같아야 통과. 다르면 상태가 새는 것이다.
// 종료 코드: 0 통과 · 1 결정론 FAIL 또는 페이지 오류 · 2 사용법·입력 오류 · 3 window.seek 없음 · 4 의존(playwright·브라우저·ffmpeg) 없음
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execFileSync } = require("child_process");

const SKILL_DIR = path.resolve(__dirname, "..");

function need(lines) {
  for (const l of lines) console.error(l);
  process.exit(4);
}

// playwright 는 이 스킬 폴더의 node_modules 에서 보통 방식으로 찾는다(다른 스킬 폴더를 빌려 쓰지 않는다)
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

function hasBin(bin) {
  try {
    execFileSync(bin, ["-version"], { stdio: "ignore" });
    return true;
  } catch (e) {
    return false;
  }
}

function args(argv) {
  const o = { fps: 30, subframes: 1, width: 1920, height: 1080 };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) o[a.slice(2)] = argv[++i];
    else rest.push(a);
  }
  o.page = rest[0];
  for (const k of ["fps", "subframes", "width", "height", "duration"]) if (o[k] !== undefined) o[k] = Number(o[k]);
  return o;
}

const sha = b => crypto.createHash("sha256").update(b).digest("hex").slice(0, 12);

function bad(msg) {
  console.error("입력 오류 " + msg);
  process.exit(2);
}

(async () => {
  const o = args(process.argv.slice(2));
  if (!o.page || !o.out || (!o.stills && !o.duration)) {
    console.error("사용: node seek_render.js <page.html> --out <폴더> (--stills 2.5,11 | --duration 15 [--fps 30] [--subframes 3] [--audio a.wav])");
    process.exit(2);
  }
  if (!fs.existsSync(o.page)) bad(`페이지 파일이 없다: ${o.page}`);
  for (const k of ["fps", "subframes", "width", "height"]) if (!(o[k] > 0) || !Number.isFinite(o[k])) bad(`--${k} 는 0보다 큰 수여야 한다`);
  if (o.duration !== undefined && !(o.duration > 0)) bad("--duration 은 0보다 큰 초여야 한다");
  const ts = o.stills ? String(o.stills).split(",").map(s => s.trim()).filter(Boolean).map(Number) : [];
  if (o.stills && (!ts.length || ts.some(t => !Number.isFinite(t) || t < 0))) bad(`--stills 는 쉼표로 나눈 0 이상의 초여야 한다: ${o.stills}`);
  if (o.audio && !fs.existsSync(o.audio)) bad(`배경음 파일이 없다: ${o.audio}`);
  if (o.duration) {
    const miss = ["ffmpeg", "ffprobe"].filter(b => !hasBin(b));
    if (miss.length) need([
      `없음 ${miss.join("·")} — 영상(--duration)을 만들려면 필요하다(스틸만이면 없어도 된다).`,
      "  맥: brew install ffmpeg · 리눅스: sudo apt install ffmpeg · 윈도: winget install Gyan.FFmpeg",
    ]);
  }

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

  fs.mkdirSync(o.out, { recursive: true });
  const page = await browser.newPage({ viewport: { width: o.width, height: o.height } });
  const errs = [];
  page.on("pageerror", e => errs.push(String(e)));
  await page.goto("file://" + path.resolve(o.page));
  await page.evaluate(() => document.fonts.ready);
  if (!(await page.evaluate(() => typeof window.seek === "function"))) {
    console.error("실패 window.seek(t) 가 없다 — 시간 고정 렌더 계약 위반(CSS 애니메이션·타이머로 만든 페이지는 찍을 수 없다)");
    await browser.close();
    process.exit(3);
  }
  const anims = await page.evaluate(() => document.getAnimations().length);
  if (anims) console.log(`경고 CSS/웹 애니메이션 ${anims}개가 돌고 있다 — seek(t) 밖에서 움직이는 것이 있으면 프레임이 흔들린다`);
  const shot = async t => {
    await page.evaluate(t => window.seek(t), t);
    await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
    return page.screenshot();
  };

  let fail = 0;
  if (ts.length) {
    const first = [];
    for (const t of ts) first.push(await shot(t));
    // 결정론 검사: 역순으로 다시 찍어 비교(다른 시각을 거친 뒤에도 같은 그림이어야 한다)
    for (let i = ts.length - 1; i >= 0; i--) {
      await shot(ts[i] + 0.37);
      const again = await shot(ts[i]);
      const same = Buffer.compare(first[i], again) === 0;
      const name = `still-${String(ts[i]).replace(".", "_")}s.png`;
      fs.writeFileSync(path.join(o.out, name), first[i]);
      console.log(`스틸 ${name} sha=${sha(first[i])} 결정론=${same ? "OK" : "FAIL(재촬영 sha=" + sha(again) + ")"}`);
      if (!same) fail++;
    }
  }

  if (o.duration) {
    const rate = o.fps * o.subframes;
    const n = Math.round(o.duration * rate);
    const fdir = path.join(o.out, "frames");
    fs.rmSync(fdir, { recursive: true, force: true });
    fs.mkdirSync(fdir);
    for (let i = 0; i < n; i++) fs.writeFileSync(path.join(fdir, `${String(i).padStart(6, "0")}.png`), await shot(i / rate));
    const mp4 = path.join(o.out, "out.mp4");
    const vf = o.subframes > 1 ? [`tmix=frames=${o.subframes}`, `framestep=${o.subframes}`, "format=yuv420p"] : ["format=yuv420p"];
    const ff = ["-y", "-loglevel", "error", "-framerate", String(rate), "-i", path.join(fdir, "%06d.png")];
    if (o.audio) ff.push("-i", o.audio);
    ff.push("-vf", vf.join(","), "-r", String(o.fps), "-c:v", "libx264", "-crf", "18");
    if (o.audio) ff.push("-c:a", "aac", "-shortest");
    ff.push(mp4);
    execFileSync("ffmpeg", ff, { stdio: "inherit" });
    const probe = execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration:stream=width,height,r_frame_rate", "-of", "csv=p=0", mp4]).toString().trim().replace(/\n/g, " | ");
    console.log(`영상 ${mp4} 프레임 ${n}장(${rate}fps 촬영 → ${o.fps}fps${o.subframes > 1 ? " · 모션블러 " + o.subframes + "장 합성" : ""}) · ffprobe ${probe}`);
  }

  await browser.close();
  for (const e of errs) console.log("페이지 오류", e);
  if (errs.length) fail++;
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
