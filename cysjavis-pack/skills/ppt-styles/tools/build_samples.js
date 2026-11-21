// 스타일별 견본 3장(제목·카드·질문) → <출력폴더>/<id>.pptx · 사용: node build_samples.js <출력폴더> [id …]
const fs = require("fs"), path = require("path");
const deps = require("../lib/deps");
deps.setup();
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("../lib/theme");
(async () => {
  const [outDir, ...want] = process.argv.slice(2);
  if (!outDir) { console.error("사용: node build_samples.js <출력폴더> [id …]"); process.exit(2); }
  fs.mkdirSync(outDir, { recursive: true });
  const dir = path.join(deps.SKILL, "styles");
  const files = fs.readdirSync(dir).filter(f => /^\d\d-.*\.js$/.test(f)).sort();
  let n = 0;
  for (const f of files) {
    const st = require(path.join(dir, f)); const m = st.meta;
    if (want.length && !want.includes(m.id)) continue;
    const pres = new pptxgen(); pres.layout = "LAYOUT_16x9"; pres.title = m.name + " — 샘플"; pres.author = "ppt-styles";
    st.layouts(pres, m.sample);
    await st.titleSlide(pres, m.sample.title); await st.cardSlide(pres, m.sample.cards); await st.questionSlide(pres, m.sample.question);
    const out = path.join(outDir, m.id + ".pptx");
    await pres.writeFile({ fileName: out }); await applyTheme(out, st.THEME); console.log("written", m.id); n++;
  }
  if (want.length && n !== want.length) { console.error(`없는 스타일 id 가 있습니다: ${want.join(" ")}`); process.exit(2); }
})().catch(e => { console.error(e.message || e); process.exit(1); });
