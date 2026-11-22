// 내용 JSON → 스타일을 입힌 .pptx 한 벌.
// 사용: node make_deck.js <내용.json> <결과.pptx>
//   내용.json = { "style": "<스타일 id>", "title": "<파일 속성 제목>", "footer": "…",
//                 "slides": [ { "kind": "title", … }, { "kind": "cards", … }, { "kind": "question", … } ] }
//   각 장의 칸 이름은 그 스타일 견본(styles/NN-<id>.js 의 meta.sample.title·cards·question)과 같다 — references/CATALOG.md 「입력 칸」.
// 빈 칸 처리(조용히 견본 글을 끼워 넣지 않는다):
//   글 칸이 없으면 "" · 목록이 없으면 [] · 아이콘 이름만 견본 값을 쓴다.
//   스타일 코드가 자리를 고정해 쓰는 목록(예: cards[1] · qs[1])은 그 개수까지 빈 항목으로 채운다(경고 출력).
//   카드가 견본 개수보다 많으면 같은 제목 「(계속)」 장으로 나눈다(화면 밖으로 밀려나지 않게).
const fs = require("fs"), path = require("path");
const deps = require("../lib/deps");
deps.setup();
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("../lib/theme");

const STYLES = path.join(deps.SKILL, "styles");
const KINDS = { title: "titleSlide", cards: "cardSlide", question: "questionSlide" };
const warn = [];

function loadStyle(id) {
  const f = fs.readdirSync(STYLES).find(n => /^\d\d-.*\.js$/.test(n) && n.replace(/^\d\d-/, "").replace(/\.js$/, "") === id);
  if (!f) {
    const ids = fs.readdirSync(STYLES).filter(n => /^\d\d-.*\.js$/.test(n)).map(n => n.replace(/^\d\d-/, "").replace(/\.js$/, ""));
    throw new Error(`스타일 「${id}」 이 없습니다. 고를 수 있는 것: ${ids.join(", ")}`);
  }
  return { st: require(path.join(STYLES, f)), src: fs.readFileSync(path.join(STYLES, f), "utf8"), file: f };
}
// 스타일 코드가 d.<key>[N] 처럼 고정 자리로 읽는 최소 개수
function minCount(src, key) { let n = 0; for (const m of src.matchAll(new RegExp(`d\\.${key}\\[(\\d+)\\]`, "g"))) n = Math.max(n, +m[1] + 1); return n; }
function blank(tpl) {
  if (typeof tpl === "string") return "";
  if (typeof tpl === "number") return 0;
  if (Array.isArray(tpl)) return [];
  if (tpl && typeof tpl === "object") { const o = {}; for (const k of Object.keys(tpl)) o[k] = k === "icon" ? tpl[k] : blank(tpl[k]); return o; }
  return tpl;
}
function norm(v, tpl, where, src, key) {
  if (typeof tpl === "string") {
    if (v == null) { if (key === "icon") return tpl; return ""; }
    return typeof v === "string" ? v : String(v);
  }
  if (typeof tpl === "number") { if (typeof v === "number") return v; if (v != null && !isNaN(+v)) return +v; return key === "active" ? tpl : 0; }
  if (Array.isArray(tpl)) {
    let a = Array.isArray(v) ? v : (v == null ? [] : [v]);
    const el = tpl[0];
    a = a.map((x, i) => (el === undefined ? x : norm(x, el, `${where}[${i}]`, src, null)));
    const need = key ? minCount(src, key) : 0;
    if (a.length < need) { warn.push(`${where}: ${a.length}개 → 이 스타일은 ${need}개 자리를 고정해 쓰므로 빈 항목으로 채움`); while (a.length < need) a.push(el === undefined ? "" : blank(el)); }
    return a;
  }
  if (tpl && typeof tpl === "object") {
    const o = (v && typeof v === "object" && !Array.isArray(v)) ? { ...v } : {};
    for (const k of Object.keys(tpl)) o[k] = norm(o[k], tpl[k], `${where}.${k}`, src, k);
    return o;
  }
  return v;
}

async function main() {
  const [inp, out] = process.argv.slice(2);
  if (!inp || !out) { console.error("사용: node make_deck.js <내용.json> <결과.pptx>"); process.exit(2); }
  let doc;
  try { doc = JSON.parse(fs.readFileSync(inp, "utf8")); } catch (e) { console.error(`내용 JSON 을 읽지 못했습니다: ${e.message}`); process.exit(2); }
  const { st, src } = loadStyle(doc.style);
  const m = st.meta, sample = m.sample;
  if (!Array.isArray(doc.slides) || !doc.slides.length) { console.error("slides 가 비어 있습니다 — 적어도 1장(kind: title|cards|question)이 필요합니다"); process.exit(2); }
  const top = {};
  for (const k of Object.keys(sample)) if (!(k in KINDS)) top[k] = norm(doc[k], sample[k], k, src, k);
  const pres = new pptxgen(); pres.layout = "LAYOUT_16x9";
  pres.title = String(doc.title || ""); pres.author = String(doc.author || ""); pres.company = "";
  st.layouts(pres, top);
  let count = 0;
  for (const [i, sl] of doc.slides.entries()) {
    const fn = KINDS[sl && sl.kind];
    if (!fn) throw new Error(`slides[${i}].kind = ${JSON.stringify(sl && sl.kind)} — title · cards · question 중 하나여야 합니다`);
    const tpl = sample[sl.kind];
    let d = norm(sl, tpl, `slides[${i}]`, src, null);
    const cap = Array.isArray(tpl.cards) ? tpl.cards.length : 0;
    if (sl.kind === "cards" && cap && d.cards.length > cap) {
      warn.push(`slides[${i}].cards: ${d.cards.length}개 → 이 스타일 한 장에 ${cap}개라 ${Math.ceil(d.cards.length / cap)}장으로 나눔`);
      for (let p = 0; p * cap < d.cards.length; p++) {
        const part = { ...d, cards: d.cards.slice(p * cap, (p + 1) * cap), title: p ? `${d.title} (계속)` : d.title };
        part.cards = norm(part.cards, tpl.cards, `slides[${i}].cards`, src, "cards");
        await st[fn](pres, part); count++;
      }
      continue;
    }
    await st[fn](pres, d); count++;
  }
  fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
  await pres.writeFile({ fileName: out });
  await applyTheme(out, st.THEME);
  for (const w of warn) console.log(`[경고] ${w}`);
  console.log(`OK ${m.id} ${count}장 → ${out}`);
  console.log(`SLIDES=${count}`);
}
main().catch(e => { console.error(`[ppt-styles] 실패: ${e.message}`); process.exit(1); });
