// 06 추모 예배 · 회청+은회 — 명조 가운데 정렬 · 가는 원 테두리 · 넓은 여백
const { W, H, tx, box, runs, icon } = require("../lib/kit");
const pi = require("react-icons/pi"); // Phosphor(MIT)
const FONT = "NanumMyeongjo";
const SLATE = "2E3440", MIST = "ECEFF4", SILVER = "D8DEE9", SAGE = "8FA39B", DEEPSAGE = "5E726A", TEXT = "3B4252", WHITE = "FFFFFF";
const THEME = { name: "MemorialQuiet", headFontFace: FONT, bodyFontFace: FONT,
  colors: { dk1: SLATE, lt1: WHITE, dk2: TEXT, lt2: MIST, accent1: SAGE, accent2: SILVER, accent3: DEEPSAGE, accent4: "4C566A", accent5: "A3ADBD", accent6: "7B8794", hlink: DEEPSAGE, folHlink: "7B8794" } };
function layouts(pres) {
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
  pres.defineSlideMaster({ title: "NIGHT", background: { color: SLATE }, objects: [] });
  pres.defineSlideMaster({ title: "MIST", background: { color: MIST }, objects: [
    { placeholder: { options: { name: "title", type: "title", x: 1.0, y: 0.45, w: 8.0, h: 0.7, fontSize: 28, bold: true, color: TEXT, fontFace: FONT, margin: 0, valign: "middle", align: "center" }, text: "" } } ] });
}
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "NIGHT" });
  box(pres, s, "ellipse", { x: 4.35, y: 0.6, w: 1.3, h: 1.3, line: { color: SILVER, width: 1 }, name: "ring" });
  s.addImage({ data: await icon(pi.PiBirdFill, SILVER), x: 4.7, y: 0.95, w: 0.6, h: 0.6, objectName: "ico" });
  tx(s, d.title, { x: 1.0, y: 2.15, w: 8.0, h: 0.9, size: 40, bold: true, color: WHITE, font: FONT, align: "center", name: "t1" });
  tx(s, d.verse, { x: 1.5, y: 3.2, w: 7.0, h: 0.9, size: 20, color: SILVER, font: FONT, align: "center", name: "verse" });
  tx(s, d.meta, { x: 1.5, y: 4.35, w: 7.0, h: 0.4, size: 16, color: SAGE, font: FONT, align: "center", name: "meta" });
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "MIST" }); s.addText(d.title, { placeholder: "title" });
  d.cards.forEach((c, i) => { const x = 1.0 + (i % 3) * 2.75, y = 1.5 + Math.floor(i / 3) * 1.6;
    box(pres, s, "rect", { x, y, w: 2.5, h: 1.35, fill: WHITE, line: { color: SILVER, width: 1 }, name: "order" });
    tx(s, c.head, { x, y: y + 0.2, w: 2.5, h: 0.5, size: 24, bold: true, color: TEXT, font: FONT, align: "center", name: "orderHead" });
    tx(s, c.lines.join(" "), { x: x + 0.1, y: y + 0.75, w: 2.3, h: 0.4, size: 16, color: DEEPSAGE, font: FONT, align: "center", name: "orderBody" }); });
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "MIST" }); s.addText(d.title, { placeholder: "title" });
  tx(s, d.qs[0], { x: 1.2, y: 1.45, w: 7.6, h: 1.1, size: 24, color: TEXT, font: FONT, align: "center", name: "q1" });
  s.addImage({ data: await icon(pi.PiLeafFill, SAGE), x: 4.8, y: 2.75, w: 0.4, h: 0.4, objectName: "leaf" });
  tx(s, d.qs[1], { x: 1.2, y: 3.35, w: 7.6, h: 1.1, size: 24, color: TEXT, font: FONT, align: "center", name: "q2" });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "memorial-quiet", no: 6, name: "추모 예배 · 회청+은회",
    mood: ["추모", "고요한", "위로", "잔잔한", "엄숙한", "절제된", "장례", "묵상", "경건한", "애도"],
    palette: [["회청", SLATE], ["안개 흰색", MIST], ["은회", SILVER], ["세이지", SAGE], ["먹회(글자)", TEXT]],
    fonts: { head: "나눔명조 Bold", body: "나눔명조", license: "네이버 나눔글꼴 · SIL OFL 1.1" },
    motifs: ["어두운 표지 한가운데 가는 원 + 비둘기", "명조 가운데 정렬(성구·순서·질문 전부)", "가는 테두리 흰 칸(예배 순서)", "질문 사이 작은 잎 하나", "장식 색 없음 · 넓은 여백"],
    good: ["추모·장례·위로 예배", "성금요일·고난주간 묵상", "임종·기일 예배 순서지"],
    avoid: ["행사 홍보", "어린이 대상", "수치·도표 보고"],
    origin: "색 = Nord 팔레트(Polar Night 2E3440·3B4252 · Snow Storm D8DEE9·ECEFF4 · MIT) + 세이지 한 색",
    sample: { footer: "",
      title: { title: "故 ○○○ 성도 추모 예배", verse: "여호와는 나의 목자시니 내게 부족함이 없으리로다", meta: "시편 23:1 · 2026-10-13" },
      cards: { title: "예배 순서", cards: [{ head: "묵도", lines: ["다 같이"] }, { head: "찬송", lines: ["다 같이"] }, { head: "기도", lines: ["맡은 이"] }, { head: "말씀", lines: ["시편 23편"] }, { head: "추모사", lines: ["유족 대표"] }, { head: "축도", lines: ["집례자"] }] },
      question: { title: "함께 기억합니다", qs: ["고인과 함께한 시간 가운데 가장 감사한 기억은 무엇입니까?", "남겨 주신 믿음의 본을 우리는 어떻게 이어 가겠습니까?"] } } } };
