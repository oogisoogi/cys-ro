// 09 자연과 쉼 · 숲+아이보리 — 큰 원 겹침 표지 · 하루 흐름(점 세 개) · 좌우 분할 질문
const { W, H, tx, box, runs, icon } = require("../lib/kit");
const pi = require("react-icons/pi"); // Phosphor(MIT)
const FONT = "NanumBarunGothic";
const FOREST = "2D4A2B", SAGE = "7D8471", OLIVE = "A4AC86", IVORY = "FAF9F6", MOSS = "D5DBC0", TEXT = "263225", WHITE = "FFFFFF";
const THEME = { name: "NatureGreen", headFontFace: FONT, bodyFontFace: FONT,
  colors: { dk1: TEXT, lt1: WHITE, dk2: FOREST, lt2: IVORY, accent1: FOREST, accent2: OLIVE, accent3: SAGE, accent4: MOSS, accent5: "5C6B4E", accent6: "8A6F4D", hlink: FOREST, folHlink: SAGE } };
function layouts(pres, d) {
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
  pres.defineSlideMaster({ title: "FOREST", background: { color: FOREST }, objects: [] });
  pres.defineSlideMaster({ title: "SPLIT", background: { color: IVORY }, objects: [] });
  pres.defineSlideMaster({ title: "IVORY", background: { color: IVORY }, objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 8.8, h: 0.75, fontSize: 32, bold: true, color: FOREST, fontFace: FONT, margin: 0, valign: "middle", align: "left" }, text: "" } },
    { text: { text: d.footer, options: { x: 0.6, y: H - 0.4, w: 7, h: 0.3, fontSize: 10, color: SAGE, fontFace: FONT, margin: 0 } } } ] });
}
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "FOREST" });
  box(pres, s, "ellipse", { x: 5.8, y: 1.2, w: 5.6, h: 5.6, fill: OLIVE, name: "ringOuter" });
  box(pres, s, "ellipse", { x: 6.6, y: 2.0, w: 4.0, h: 4.0, fill: IVORY, name: "ringInner" });
  s.addImage({ data: await icon(pi.PiLeafFill, FOREST), x: 7.75, y: 3.0, w: 1.5, h: 1.5, objectName: "ico" });
  tx(s, d.title, { x: 0.7, y: 1.1, w: 5.3, h: 1.6, size: 40, bold: true, color: IVORY, font: FONT, name: "t1" });
  tx(s, d.sub, { x: 0.7, y: 2.85, w: 4.9, h: 0.9, size: 22, color: MOSS, font: FONT, valign: "top", name: "t2" });
  tx(s, d.meta, { x: 0.7, y: 4.45, w: 4.9, h: 0.4, size: 16, color: MOSS, font: FONT, name: "meta" });
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "IVORY" }); s.addText(d.title, { placeholder: "title" });
  box(pres, s, "rect", { x: 1.6, y: 2.03, w: 6.8, h: 0.04, fill: OLIVE, name: "flowLine" });
  for (let i = 0; i < d.cards.length; i++) { const c = d.cards[i], cx = 1.6 + i * 3.4;
    box(pres, s, "ellipse", { x: cx - 0.55, y: 1.5, w: 1.1, h: 1.1, fill: FOREST, name: "node" });
    s.addImage({ data: await icon(pi[c.icon], IVORY), x: cx - 0.27, y: 1.78, w: 0.54, h: 0.54, objectName: "nodeIco" });
    tx(s, c.when, { x: cx - 1.4, y: 2.75, w: 2.8, h: 0.35, size: 16, bold: true, color: SAGE, font: FONT, align: "center", name: "when" });
    tx(s, c.head, { x: cx - 1.4, y: 3.1, w: 2.8, h: 0.5, size: 24, bold: true, color: FOREST, font: FONT, align: "center", name: "nodeHead" });
    tx(s, runs(c.lines, 2), { x: cx - 1.4, y: 3.65, w: 2.8, h: 0.9, size: 18, color: TEXT, font: FONT, align: "center", valign: "top", name: "nodeBody" }); }
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "SPLIT" });
  box(pres, s, "rect", { x: 0, y: 0, w: 3.6, h: H, fill: FOREST, name: "panel" });
  s.addImage({ data: await icon(pi.PiPlantFill, OLIVE), x: 1.3, y: 1.4, w: 1.0, h: 1.0, objectName: "ico" });
  tx(s, d.title, { x: 0.4, y: 2.6, w: 2.8, h: 0.7, size: 36, bold: true, color: IVORY, font: FONT, align: "center", name: "panelTitle" });
  tx(s, d.note, { x: 0.4, y: 3.35, w: 2.8, h: 0.7, size: 14, color: MOSS, font: FONT, align: "center", valign: "top", name: "panelNote" });
  tx(s, runs(d.qs, 26), { x: 4.2, y: 0.9, w: 5.2, h: 3.8, size: 24, color: TEXT, font: FONT, name: "questions" });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "nature-green", no: 9, name: "자연과 쉼 · 숲+아이보리",
    mood: ["자연", "쉼", "평안한", "초록", "싱그러운", "회복", "숲", "묵상", "산책", "편안한"],
    palette: [["숲 초록", FOREST], ["세이지", SAGE], ["올리브", OLIVE], ["아이보리", IVORY], ["이끼(어두운 바탕 글자)", MOSS]],
    fonts: { head: "나눔바른고딕 Bold", body: "나눔바른고딕", license: "네이버 나눔글꼴 · SIL OFL 1.1" },
    motifs: ["숲색 표지 + 겹친 큰 원(화면 밖까지) + 잎", "하루 흐름 = 선 위의 점 세 개(아침·오후·저녁)", "왼쪽 숲색 패널 + 오른쪽 질문", "초록 한 계열만 · 다른 색 없음"],
    good: ["가족·장년 수련회, 피정 안내", "환경 주일·창조절", "큐티·묵상 나눔, 걷기 모임"],
    avoid: ["긴급 공지·홍보", "재정 보고", "어린이 대상(색이 차분해 눈길을 못 끈다)"],
    origin: "색 = anthropics/skills theme-factory 의 forest-canopy(2d4a2b·7d8471·a4ac86·faf9f6 · Apache-2.0) 그대로 · 구성 = pptx 스킬의 timeline/half-bleed 권고",
    sample: { footer: "쉼이 있는 가을 수련회",
      title: { title: "쉼이 있는\n가을 수련회", sub: "숲에서 걷고, 말씀 앞에 머물다", meta: "가을 · 1박 2일" },
      cards: { title: "하루의 리듬", cards: [{ icon: "PiSunHorizonFill", when: "아침", head: "묵상", lines: ["말씀 한 단락을", "조용히 읽는다"] }, { icon: "PiTreeFill", when: "오후", head: "숲길 걷기", lines: ["말없이 걷고", "둘씩 이야기한다"] }, { icon: "PiMoonStarsFill", when: "저녁", head: "나눔", lines: ["하루를 돌아보고", "서로 기도한다"] }] },
      question: { title: "나눔", note: "조용히 적어 보고\n둘씩 나눕니다", qs: ["지금 내게 필요한 쉼은 어떤 쉼입니까?", "돌아가서 지키고 싶은 한 가지는 무엇입니까?"] } } } };
