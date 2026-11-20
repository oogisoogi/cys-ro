// 08 인문 서재 · 종이+버건디 — 부리(세리프) 큰 제목 · 잡지식 3단 · 큰 따옴표 질문
const { W, H, tx, box, runs } = require("../lib/kit");
const SERIF = "MaruBuriOTF", SANS = "NanumBarunGothic";
const PAPER = "F7F4EC", INK = "22201C", BURG = "6D2E46", ROSE = "9A5873", OCHRE = "A67C52", STONE = "6F6A60", WHITE = "FFFFFF";
const THEME = { name: "EditorialSerif", headFontFace: SERIF, bodyFontFace: SANS,
  colors: { dk1: INK, lt1: WHITE, dk2: STONE, lt2: PAPER, accent1: BURG, accent2: OCHRE, accent3: ROSE, accent4: "4A4640", accent5: "C9B79C", accent6: "8C857A", hlink: BURG, folHlink: STONE } };
function layouts(pres, d) {
  pres.theme = { headFontFace: SERIF, bodyFontFace: SANS };
  pres.defineSlideMaster({ title: "COVER", background: { color: PAPER }, objects: [] });
  pres.defineSlideMaster({ title: "PAPER", background: { color: PAPER }, objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 0.4, w: 8.6, h: 0.8, fontSize: 32, bold: true, color: INK, fontFace: SERIF, margin: 0, valign: "middle", align: "left" }, text: "" } },
    { text: { text: d.footer, options: { x: 0.7, y: H - 0.42, w: 7, h: 0.3, fontSize: 10, color: STONE, fontFace: SANS, margin: 0 } } } ],
    slideNumber: { x: 8.8, y: H - 0.42, w: 0.5, h: 0.3, fontSize: 10, color: STONE, fontFace: SANS, align: "right" } });
}
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "COVER" });
  box(pres, s, "rect", { x: 7.0, y: 0, w: 3.0, h: H, fill: BURG, name: "block" });
  tx(s, d.side, { x: 7.35, y: 0.6, w: 2.3, h: 0.5, size: 20, color: PAPER, font: SERIF, name: "side" });
  tx(s, d.no, { x: 7.3, y: 3.3, w: 2.4, h: 1.8, size: 110, bold: true, color: ROSE, font: SERIF, name: "bigNo" });
  tx(s, d.label, { x: 0.7, y: 1.0, w: 6.0, h: 0.4, size: 16, bold: true, color: OCHRE, font: SANS, charSpacing: 2, name: "label" });
  tx(s, d.title, { x: 0.7, y: 1.5, w: 6.0, h: 1.2, size: 48, bold: true, color: INK, font: SERIF, name: "t1" });
  tx(s, d.sub, { x: 0.7, y: 2.85, w: 5.9, h: 0.9, size: 22, color: STONE, font: SERIF, valign: "top", name: "t2" });
  tx(s, d.meta, { x: 0.7, y: 4.55, w: 6.0, h: 0.4, size: 16, color: STONE, font: SANS, name: "meta" });
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "PAPER" }); s.addText(d.title, { placeholder: "title" });
  d.cards.forEach((c, i) => { const x = 0.7 + i * 3.0;
    tx(s, String(i + 1).padStart(2, "0"), { x, y: 1.4, w: 2.6, h: 0.95, size: 54, bold: true, color: OCHRE, font: SERIF, name: "colNo" });
    tx(s, c.head, { x, y: 2.4, w: 2.6, h: 0.6, size: 26, bold: true, color: INK, font: SERIF, name: "colHead" });
    tx(s, c.lines.join(" "), { x, y: 3.05, w: 2.6, h: 1.6, size: 18, color: STONE, font: SANS, valign: "top", lineSpacingMultiple: 1.2, name: "colBody" }); });
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "PAPER" });
  tx(s, "“", { x: 0.5, y: 0.5, w: 2.0, h: 2.2, size: 200, bold: true, color: BURG, font: SERIF, valign: "top", name: "quoteMark" });
  tx(s, d.title, { x: 2.6, y: 0.8, w: 6.7, h: 0.4, size: 16, bold: true, color: OCHRE, font: SANS, charSpacing: 2, name: "label" });
  tx(s, d.qs[0], { x: 2.6, y: 1.3, w: 6.7, h: 1.4, size: 32, bold: true, color: INK, font: SERIF, name: "q1" });
  tx(s, d.qs[1], { x: 2.6, y: 3.0, w: 6.7, h: 1.2, size: 24, color: STONE, font: SERIF, name: "q2" });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "editorial-serif", no: 8, name: "인문 서재 · 종이+버건디",
    mood: ["인문", "서재", "문학적", "사색", "깊이", "품격", "책", "고전", "지적인", "에세이"],
    palette: [["종이", PAPER], ["먹", INK], ["버건디", BURG], ["황토", OCHRE], ["돌회색(보조 글자)", STONE]],
    fonts: { head: "마루 부리 Bold", body: "나눔바른고딕(본문) · 마루 부리(인용)", license: "네이버 마루 부리·나눔글꼴 · SIL OFL 1.1" },
    motifs: ["오른쪽 버건디 세로 블록 + 큰 회차 숫자", "부리 글꼴 48pt 제목", "상자 없는 잡지식 3단(큰 숫자 → 제목 → 글)", "200pt 따옴표 + 부리 질문", "종이색 바탕"],
    good: ["인문·성서 강좌", "독서 모임·북토크", "설교 묵상 나눔·에세이 발표"],
    avoid: ["어린이 대상", "수치 보고", "빠르게 훑는 행사 안내"],
    origin: "색 = pptx 스킬 Berry & Cream(6D2E46·ECE2D0) · 구성 = frontend-slides 「Vintage Editorial」·「Paper & Ink」의 세리프 + 종이 바탕(MIT)",
    sample: { footer: "인문 성서 강좌 — 시편을 읽는 저녁",
      title: { label: "인문 성서 강좌", title: "시편을 읽는 저녁", sub: "서두르지 않고, 한 편씩", meta: "2026년 가을 · 화요일 저녁", side: "첫 번째 밤", no: "01" },
      cards: { title: "세 가지 읽기", cards: [{ head: "천천히 읽기", lines: ["한 절에 오래 머문다. 빨리 읽으면 지나치는 낱말이 있다."] }, { head: "소리 내어 읽기", lines: ["시는 귀로 듣는 글이다. 입으로 읽으면 호흡이 들린다."] }, { head: "함께 읽기", lines: ["같은 시를 읽고도 머문 자리가 다르다. 그 차이를 나눈다."] }] },
      question: { title: "나눔 질문", qs: ["이 시는 누구의 목소리로 들립니까?", "오늘 내 마음에 머문 한 단어는 무엇입니까?"] } } } };
