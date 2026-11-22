// 02 따뜻한 가족 · 테라코타+살구 — 둥근 흰 카드 · 색 원 아이콘 · 말풍선 질문
const { W, H, tx, box, runs, icon } = require("../lib/kit");
const pi = require("react-icons/pi"); // Phosphor(MIT) — 출처 표기 의무 없음
const HEAD = "NanumSquareRound", BODY = "NanumSquareRound";
const TERRA = "B85042", APRICOT = "F6D5B8", WARM = "FFF8F1", OLIVE = "6B7A4F", BROWN = "3D2B24", AMBER = "D9903D", WHITE = "FFFFFF";
const THEME = { name: "WarmFamily", headFontFace: HEAD, bodyFontFace: BODY,
  colors: { dk1: BROWN, lt1: WHITE, dk2: "6B4A3F", lt2: WARM, accent1: TERRA, accent2: OLIVE, accent3: AMBER, accent4: APRICOT, accent5: "8E4B3A", accent6: "8A7F78", hlink: TERRA, folHlink: "8A7F78" } };
function layouts(pres, d) {
  pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
  pres.defineSlideMaster({ title: "COVER", background: { color: WARM }, objects: [] });
  pres.defineSlideMaster({ title: "TERRA", background: { color: TERRA }, objects: [] });
  pres.defineSlideMaster({ title: "BASE", background: { color: WARM }, objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 8.8, h: 0.75, fontSize: 32, bold: true, color: BROWN, fontFace: HEAD, margin: 0, valign: "middle", align: "left" }, text: "" } },
    { text: { text: d.footer, options: { x: 0.6, y: H - 0.4, w: 7, h: 0.3, fontSize: 10, color: "8A7F78", fontFace: BODY, margin: 0 } } } ] });
}
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "COVER" });
  box(pres, s, "ellipse", { x: 6.2, y: 0.55, w: 4.5, h: 4.5, fill: APRICOT, name: "bigCircle" });
  box(pres, s, "ellipse", { x: 7.25, y: 1.6, w: 2.4, h: 2.4, fill: TERRA, name: "circle" });
  s.addImage({ data: await icon(pi.PiHouseFill, WHITE), x: 7.9, y: 2.25, w: 1.1, h: 1.1, objectName: "ico" });
  tx(s, d.title, { x: 0.7, y: 1.35, w: 5.6, h: 1.0, size: 44, bold: true, color: BROWN, font: HEAD, name: "t1" });
  tx(s, d.sub, { x: 0.7, y: 2.4, w: 5.4, h: 0.7, size: 26, bold: true, color: TERRA, font: HEAD, name: "t2" });
  tx(s, d.meta, { x: 0.7, y: 3.6, w: 5.4, h: 0.5, size: 18, color: OLIVE, font: BODY, name: "t3" });
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "BASE" }); s.addText(d.title, { placeholder: "title" });
  const tone = [TERRA, OLIVE, AMBER];
  for (let i = 0; i < d.cards.length; i++) { const c = d.cards[i], x = 0.6 + i * 3.0, y = 1.35;
    box(pres, s, "roundRect", { x, y, w: 2.8, h: 3.4, fill: WHITE, radius: 0.3, name: "card", shadow: { type: "outer", color: "B89A86", opacity: 0.25, blur: 8, offset: 2, angle: 90 } });
    box(pres, s, "ellipse", { x: x + 0.9, y: y + 0.3, w: 1.0, h: 1.0, fill: tone[i], name: "cardCircle" });
    s.addImage({ data: await icon(pi[c.icon], WHITE), x: x + 1.15, y: y + 0.55, w: 0.5, h: 0.5, objectName: "cardIco" });
    tx(s, c.head, { x: x + 0.2, y: y + 1.45, w: 2.4, h: 0.5, size: 24, bold: true, color: BROWN, font: HEAD, align: "center", name: "cardHead" });
    tx(s, runs(c.lines, 4), { x: x + 0.2, y: y + 2.0, w: 2.4, h: 1.2, size: 18, color: BROWN, font: BODY, align: "center", valign: "top", name: "cardBody" }); }
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "TERRA" });
  tx(s, d.title, { x: 0.7, y: 0.4, w: 8.6, h: 0.7, size: 32, bold: true, color: WHITE, font: HEAD, name: "qTitle" });
  d.qs.forEach((q, i) => { const y = 1.35 + i * 1.85;
    box(pres, s, "roundRect", { x: 0.7, y, w: 8.6, h: 1.6, fill: WHITE, radius: 0.35, name: "bubble" });
    box(pres, s, "ellipse", { x: 1.0, y: y + 0.4, w: 0.8, h: 0.8, fill: APRICOT, name: "bubbleNo" });
    tx(s, String(i + 1), { x: 1.0, y: y + 0.4, w: 0.8, h: 0.8, size: 24, bold: true, color: TERRA, font: HEAD, align: "center", name: "bubbleNoText" });
    tx(s, q, { x: 2.1, y: y + 0.15, w: 6.9, h: 1.3, size: 24, color: BROWN, font: BODY, name: "question" }); });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "warm-family", no: 2, name: "따뜻한 가족 · 테라코타+살구",
    mood: ["따뜻한", "가족적", "포근한", "친근한", "부드러운", "환대", "교회학교", "학부모", "정겨운", "다정한"],
    palette: [["테라코타", TERRA], ["살구", APRICOT], ["따뜻한 흰색", WARM], ["올리브", OLIVE], ["짙은 갈색(글자)", BROWN]],
    fonts: { head: "나눔스퀘어라운드 Bold", body: "나눔스퀘어라운드", license: "네이버 나눔글꼴 · SIL OFL 1.1" },
    motifs: ["큰 살구색 원 + 집 아이콘 표지", "모서리가 크게 둥근 흰 카드 + 색 원 아이콘", "테라코타 바탕 위 흰 말풍선 질문(번호 원)"],
    good: ["교회학교·학부모 발표", "가정 예배·구역 모임 안내", "새가족 환영·소개"],
    avoid: ["공식 보고·재정", "추모·엄숙한 예식", "데이터가 많은 발표"],
    origin: "색 = pptx 스킬 Warm Terracotta(B85042) + anthropics theme-factory golden-hour 계열을 한글 둥근 글꼴에 맞춰 재구성",
    sample: { footer: "교회학교 가을 학부모 발표회",
      title: { title: "우리 반을 소개합니다", sub: "교회학교 가을 학부모 발표회", meta: "함께 자라는 한 학기 이야기" },
      cards: { title: "함께 자라는 세 가지", cards: [{ icon: "PiBookOpenFill", head: "말씀", lines: ["매주 한 구절을", "함께 읽어요"] }, { icon: "PiPersonSimpleRunFill", head: "놀이", lines: ["몸으로 배우는", "성경 이야기"] }, { icon: "PiHouseFill", head: "가정", lines: ["집에서 이어 가는", "한 주 약속"] }] },
      question: { title: "함께 나눠요", qs: ["이번 학기, 우리 아이가 가장 즐거워한 순간은 언제였나요?", "가정에서 함께 해 보고 싶은 것은 무엇인가요?"] } } } };
