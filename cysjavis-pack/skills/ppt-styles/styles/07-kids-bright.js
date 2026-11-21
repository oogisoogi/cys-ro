// 07 어린이 성경학교 · 하늘+노랑+산호 — 해·구름·별 · 알록달록 큰 카드 · 큰 글씨
const { W, H, tx, box, runs, icon } = require("../lib/kit");
const pi = require("react-icons/pi"); // Phosphor(MIT)
const FONT = "NanumSquareRound", XB = "NanumSquareRound ExtraBold";
const SKY = "4CC9F0", YELLOW = "FFD166", CORAL = "EF476F", GREEN = "06D6A0", NAVY = "073B4C", WHITE = "FFFFFF";
const THEME = { name: "KidsBright", headFontFace: FONT, bodyFontFace: FONT,
  colors: { dk1: NAVY, lt1: WHITE, dk2: "0B5C75", lt2: "E8F8FD", accent1: SKY, accent2: YELLOW, accent3: CORAL, accent4: GREEN, accent5: "118AB2", accent6: "F78C6B", hlink: "118AB2", folHlink: "0B5C75" } };
function layouts(pres) {
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
  pres.defineSlideMaster({ title: "SKY", background: { color: SKY }, objects: [] });
  pres.defineSlideMaster({ title: "SUN", background: { color: YELLOW }, objects: [] });
  pres.defineSlideMaster({ title: "WHITE", background: { color: WHITE }, objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9.0, h: 0.85, fontSize: 36, color: NAVY, fontFace: XB, margin: 0, valign: "middle", align: "left" }, text: "" } } ] });
}
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "SKY" });
  box(pres, s, "ellipse", { x: 7.2, y: 0.3, w: 3.0, h: 3.0, fill: YELLOW, name: "sun" });
  [[0.3, 4.2, 2.8, 1.2], [1.9, 4.5, 3.0, 1.3], [6.0, 4.4, 3.4, 1.4]].forEach(([x, y, w, h]) => box(pres, s, "ellipse", { x, y, w, h, fill: WHITE, name: "cloud" }));
  [[6.3, 0.45, 0.5], [6.7, 3.55, 0.3]].forEach(([x, y, w]) => box(pres, s, "star5", { x, y, w, h: w, fill: WHITE, name: "star" }));
  tx(s, d.title, { x: 0.6, y: 0.85, w: 6.4, h: 1.2, size: 60, color: NAVY, font: XB, name: "t1" });
  box(pres, s, "roundRect", { x: 0.6, y: 2.3, w: 5.9, h: 0.9, fill: CORAL, radius: 0.45, name: "pill" });
  tx(s, d.sub, { x: 0.6, y: 2.3, w: 5.9, h: 0.9, size: 30, color: WHITE, font: XB, align: "center", name: "t2" });
  tx(s, d.meta, { x: 0.6, y: 3.4, w: 6.0, h: 0.5, size: 22, bold: true, color: NAVY, font: FONT, name: "t3" });
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "WHITE" }); s.addText(d.title, { placeholder: "title" });
  const fill = [CORAL, YELLOW, GREEN], ink = [WHITE, NAVY, NAVY];
  for (let i = 0; i < d.cards.length; i++) { const c = d.cards[i], x = 0.5 + i * 3.05, y = 1.3;
    box(pres, s, "roundRect", { x, y, w: 2.9, h: 3.7, fill: fill[i], radius: 0.4, name: "card" });
    box(pres, s, "ellipse", { x: x + 0.8, y: y + 0.3, w: 1.3, h: 1.3, fill: WHITE, name: "cardCircle" });
    s.addImage({ data: await icon(pi[c.icon], NAVY), x: x + 1.1, y: y + 0.6, w: 0.7, h: 0.7, objectName: "cardIco" });
    tx(s, c.head, { x: x + 0.2, y: y + 1.8, w: 2.5, h: 0.6, size: 30, color: ink[i], font: XB, align: "center", name: "cardHead" });
    tx(s, runs(c.lines, 2), { x: x + 0.2, y: y + 2.45, w: 2.5, h: 1.0, size: 20, bold: true, color: ink[i], font: FONT, align: "center", valign: "top", name: "cardBody" }); }
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "SUN" });
  tx(s, d.title, { x: 0.6, y: 0.35, w: 8.8, h: 0.8, size: 36, color: NAVY, font: XB, name: "qTitle" });
  box(pres, s, "ellipse", { x: 0.6, y: 1.5, w: 2.6, h: 2.6, fill: CORAL, name: "qCircle" });
  tx(s, "?", { x: 0.6, y: 1.5, w: 2.6, h: 2.6, size: 130, color: WHITE, font: XB, align: "center", name: "qMark" });
  d.qs.forEach((q, i) => { const y = 1.35 + i * 1.6;
    box(pres, s, "roundRect", { x: 3.6, y, w: 5.9, h: 1.4, fill: WHITE, radius: 0.35, name: "qCard" });
    tx(s, q, { x: 3.9, y, w: 5.3, h: 1.4, size: 24, bold: true, color: NAVY, font: FONT, name: "question" }); });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "kids-bright", no: 7, name: "어린이 성경학교 · 하늘+노랑+산호",
    mood: ["아이들", "어린이", "밝은", "신나는", "알록달록", "귀여운", "성경학교", "즐거운", "명랑한", "놀이"],
    palette: [["하늘", SKY], ["노랑", YELLOW], ["산호", CORAL], ["초록", GREEN], ["짙은 청록(글자)", NAVY]],
    fonts: { head: "나눔스퀘어라운드 ExtraBold", body: "나눔스퀘어라운드 Bold", license: "네이버 나눔글꼴 · SIL OFL 1.1" },
    motifs: ["하늘 바탕 + 노란 해 + 흰 구름 + 별", "산호색 알약 부제", "색이 다른 큰 둥근 카드 + 흰 원 아이콘", "큰 물음표 원 + 흰 질문 카드", "본문도 굵게 · 60pt 제목"],
    good: ["여름·겨울 성경학교", "유치부·유년부 설교 보조", "어린이 주일 순서·게임 안내"],
    avoid: ["당회·재정 보고", "추모 예배", "성인 학술 강의"],
    origin: "원색 다섯을 고르게 쓰는 아동용 배색(4CC9F0·FFD166·EF476F·06D6A0·073B4C) · 구성 = frontend-slides 「Pastel Geometry」의 큰 도형 반복(MIT)",
    sample: { footer: "",
      title: { title: "여름 성경학교", sub: "하나님이 만드신 세상!", meta: "유년부 · 첫째 날" },
      cards: { title: "오늘 뭐 해요?", cards: [{ icon: "PiMusicNotesFill", head: "찬양", lines: ["신나게", "불러요"] }, { icon: "PiBookOpenFill", head: "말씀", lines: ["창조 이야기", "들어요"] }, { icon: "PiPaintBrushFill", head: "만들기", lines: ["나만의 지구", "만들어요"] }] },
      question: { title: "생각해 봐요", qs: ["하나님이 첫째 날에 만드신 것은 무엇일까요?", "내가 가장 좋아하는 동물은 무엇인가요?"] } } } };
