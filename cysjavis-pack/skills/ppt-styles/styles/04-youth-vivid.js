// 04 젊은 수련회 · 검정+주황+노랑 — 초대형 글자 · 색 블록 · 알약 스티커
const { W, H, tx, box, runs, icon } = require("../lib/kit");
const pi = require("react-icons/pi"); // Phosphor(MIT) — 출처 표기 의무 없음
const FONT = "NanumSquare Neo", HEAVY = "NanumSquare Neo Heavy"; // Heavy 는 글꼴 이름으로 고른다(bold 플래그를 겹치면 가짜 굵기가 된다)
const BLACK = "121212", ORANGE = "FF5A1F", YELLOW = "FFD60A", WHITE = "FFFFFF", DARK = "2B2B2B";
const THEME = { name: "YouthVivid", headFontFace: FONT, bodyFontFace: FONT,
  colors: { dk1: BLACK, lt1: WHITE, dk2: DARK, lt2: "F4F4F4", accent1: ORANGE, accent2: YELLOW, accent3: "FF8A5C", accent4: "FFE566", accent5: "6B6B6B", accent6: "B3B3B3", hlink: ORANGE, folHlink: "6B6B6B" } };
function layouts(pres) {
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
  pres.defineSlideMaster({ title: "BLACK", background: { color: BLACK }, objects: [] });
  pres.defineSlideMaster({ title: "ORANGE", background: { color: ORANGE }, objects: [] });
}
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "BLACK" });
  box(pres, s, "parallelogram", { x: 5.9, y: 0, w: 5.2, h: H, fill: ORANGE, name: "block" });
  s.addImage({ data: await icon(pi.PiFireFill, BLACK), x: 7.55, y: 0.9, w: 1.5, h: 1.5, objectName: "ico" });
  tx(s, d.en, { x: 6.9, y: 3.6, w: 2.7, h: 1.3, size: 26, bold: true, color: BLACK, font: FONT, align: "right", name: "en" });
  tx(s, d.title, { x: 0.6, y: 0.75, w: 5.6, h: 2.2, size: 54, color: WHITE, font: HEAVY, name: "t1" });
  tx(s, d.sub, { x: 0.6, y: 3.05, w: 5.4, h: 0.7, size: 30, bold: true, color: YELLOW, font: FONT, name: "t2" });
  box(pres, s, "roundRect", { x: 0.6, y: 4.3, w: 4.9, h: 0.62, fill: YELLOW, radius: 0.31, name: "pill" });
  tx(s, d.meta, { x: 0.6, y: 4.3, w: 4.9, h: 0.62, size: 18, bold: true, color: BLACK, font: FONT, align: "center", name: "pillText" });
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "BLACK" });
  tx(s, d.title, { x: 0.6, y: 0.4, w: 8.8, h: 0.8, size: 36, color: WHITE, font: HEAVY, name: "title" });
  const fill = [ORANGE, YELLOW, WHITE];
  d.cards.forEach((c, i) => { const x = 0.6 + i * 3.0, y = 1.4;
    box(pres, s, "rect", { x, y, w: 2.8, h: 3.6, fill: fill[i], name: "block" });
    tx(s, "DAY", { x: x + 0.25, y: y + 0.2, w: 1.5, h: 0.35, size: 16, bold: true, color: BLACK, font: FONT, charSpacing: 3, name: "blockTag" });
    tx(s, String(i + 1), { x: x + 0.2, y: y + 0.5, w: 2.0, h: 1.4, size: 88, color: BLACK, font: HEAVY, name: "blockNo" });
    tx(s, c.head, { x: x + 0.25, y: y + 2.0, w: 2.3, h: 0.55, size: 28, bold: true, color: BLACK, font: FONT, name: "blockHead" });
    tx(s, runs(c.lines, 2), { x: x + 0.25, y: y + 2.6, w: 2.3, h: 0.85, size: 18, color: BLACK, font: FONT, valign: "top", name: "blockBody" }); });
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "ORANGE" });
  box(pres, s, "roundRect", { x: 0.6, y: 0.5, w: 1.9, h: 0.5, fill: BLACK, radius: 0.25, name: "tag" });
  tx(s, "QUESTION", { x: 0.6, y: 0.5, w: 1.9, h: 0.5, size: 14, bold: true, color: YELLOW, font: FONT, align: "center", charSpacing: 3, name: "tagText" });
  tx(s, d.qs[0], { x: 0.6, y: 1.2, w: 8.8, h: 1.6, size: 44, color: BLACK, font: HEAVY, name: "q1" });
  box(pres, s, "rect", { x: 0.6, y: 3.1, w: 8.8, h: 1.7, fill: BLACK, name: "q2Block" });
  tx(s, d.qs[1], { x: 0.95, y: 3.1, w: 8.1, h: 1.7, size: 30, bold: true, color: YELLOW, font: FONT, name: "q2" });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "youth-vivid", no: 4, name: "젊은 수련회 · 검정+주황+노랑",
    mood: ["젊은", "역동적", "에너지", "강렬한", "트렌디", "청년", "수련회", "홍보", "뜨거운", "힙한"],
    palette: [["검정", BLACK], ["주황", ORANGE], ["노랑", YELLOW], ["흰색", WHITE], ["짙은 회", DARK]],
    fonts: { head: "나눔스퀘어 네오 Heavy", body: "나눔스퀘어 네오", license: "네이버 나눔글꼴 · SIL OFL 1.1" },
    motifs: ["검정 바탕 + 기울어진 주황 블록(화면 밖까지)", "54pt 이상 초대형 제목", "노란 알약 스티커(일시·장소)", "DAY 1·2·3 통짜 색 블록", "주황 전면 + 검정 블록 질문"],
    good: ["청년·청소년 수련회 홍보", "행사 오프닝·카운트다운", "SNS 카드로 잘라 쓸 장면"],
    avoid: ["당회·재정 보고", "추모 예배", "글이 많은 강의(본문이 길면 금방 답답해진다)"],
    origin: "zarazhangrui/frontend-slides 의 「Bold Signal」(1a1a1a + FF5722 · 큰 번호 · 색 카드)을 pptxgenjs 도형으로 옮김(MIT)",
    sample: { footer: "",
      title: { title: "2026 청년\n겨울 수련회", sub: "다시, 불붙다", meta: "1월 · 2박 3일 · 신청은 주보 QR", en: "WINTER\nRETREAT" },
      cards: { title: "3일의 흐름", cards: [{ head: "모이다", lines: ["개회 예배", "조 모임"] }, { head: "깊어지다", lines: ["말씀 집회", "기도의 밤"] }, { head: "보내지다", lines: ["결단 예배", "파송"] }] },
      question: { title: "", qs: ["너는 지금\n어디에 서 있니?", "이번 겨울, 무엇을 내려놓고 올래?"] } } } };
