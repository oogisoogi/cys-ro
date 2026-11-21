// <폴더>/<id>-N.png 3장 → <폴더>/sheet-<id>.png(가로 3장) · 전체 → <폴더>/sheet-all.png · 사용: node sheet.js <폴더>
const fs = require("fs"), path = require("path");
const deps = require("../lib/deps");
deps.setup();
const sharp = require("sharp");
(async () => {
  const B = process.argv[2]; if (!B) { console.error("사용: node sheet.js <폴더>"); process.exit(2); }
  const G = 12, TW = 640, TH = 360;
  const ids = fs.readdirSync(path.join(deps.SKILL, "styles")).filter(f => /^\d\d-.*\.js$/.test(f)).sort().map(f => require(path.join(deps.SKILL, "styles", f)).meta.id);
  const rows = [];
  for (const id of ids) {
    const pages = fs.readdirSync(B).filter(f => f.startsWith(id + "-") && /-\d+\.png$/.test(f)).sort(); if (pages.length !== 3) continue;
    const comp = []; for (let i = 0; i < 3; i++) comp.push({ input: await sharp(path.join(B, pages[i])).resize(TW, TH, { fit: "fill" }).png().toBuffer(), left: G + i * (TW + G), top: G });
    const out = path.join(B, "sheet-" + id + ".png");
    await sharp({ create: { width: 3 * TW + 4 * G, height: TH + 2 * G, channels: 3, background: "#8A8F98" } }).composite(comp).png().toFile(out); rows.push(out);
  }
  const rh = TH + 2 * G, comp = rows.map((r, i) => ({ input: r, left: 0, top: i * rh }));
  if (rows.length) await sharp({ create: { width: 3 * TW + 4 * G, height: rows.length * rh, channels: 3, background: "#8A8F98" } }).composite(comp).png().toFile(path.join(B, "sheet-all.png"));
  console.log("sheets", rows.length);
})().catch(e => { console.error(e.message || e); process.exit(1); });
