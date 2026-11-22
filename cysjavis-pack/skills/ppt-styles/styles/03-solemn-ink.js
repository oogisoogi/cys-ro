// 03 엄숙한 보고 · 먹색+백 — 문서 같은 표지 · 번호 안건 줄 · 결의 체크 상자
const { W, H, tx, box, runs } = require("../lib/kit");
const FONT = "Apple SD Gothic Neo";
const INK = "1F2328", GRAY = "5B616A", PALE = "F3F4F6", LINE = "D0D4DA", NUM = "A8AEB7", WINE = "8C1D2B", WHITE = "FFFFFF";
const THEME = { name: "SolemnInk", headFontFace: FONT, bodyFontFace: FONT,
  colors: { dk1: INK, lt1: WHITE, dk2: GRAY, lt2: PALE, accent1: WINE, accent2: "3F4752", accent3: NUM, accent4: LINE, accent5: "6E7681", accent6: "2D333B", hlink: WINE, folHlink: GRAY } };
function layouts(pres, d) {
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
  pres.defineSlideMaster({ title: "COVER", background: { color: WHITE }, objects: [] });
  pres.defineSlideMaster({ title: "PLAIN", background: { color: WHITE }, objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 8.8, h: 0.7, fontSize: 30, bold: true, color: INK, fontFace: FONT, margin: 0, valign: "middle", align: "left" }, text: "" } },
    { text: { text: d.footer, options: { x: 0.6, y: H - 0.4, w: 7, h: 0.3, fontSize: 10, color: GRAY, fontFace: FONT, margin: 0 } } } ],
    slideNumber: { x: 8.9, y: H - 0.4, w: 0.5, h: 0.3, fontSize: 10, color: GRAY, fontFace: FONT, align: "right" } });
}
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "COVER" });
  tx(s, d.label, { x: 0.8, y: 0.95, w: 6, h: 0.4, size: 14, bold: true, color: WINE, font: FONT, charSpacing: 4, name: "label" });
  tx(s, d.title, { x: 0.8, y: 1.4, w: 8.4, h: 0.95, size: 40, bold: true, color: INK, font: FONT, name: "t1" });
  tx(s, d.sub, { x: 0.8, y: 2.35, w: 8.4, h: 0.6, size: 24, color: GRAY, font: FONT, name: "t2" });
  box(pres, s, "rect", { x: 0.8, y: 3.6, w: 8.4, h: 1.15, fill: PALE, name: "metaPanel" });
  d.fields.forEach(([k, v], i) => { const x = 1.05 + i * 2.75;
    tx(s, k, { x, y: 3.72, w: 2.5, h: 0.3, size: 12, color: GRAY, font: FONT, name: "metaKey" });
    tx(s, v, { x, y: 4.05, w: 2.5, h: 0.5, size: 18, bold: true, color: INK, font: FONT, name: "metaVal" }); });
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "PLAIN" }); s.addText(d.title, { placeholder: "title" });
  d.cards.forEach((c, i) => { const y = 1.35 + i * 1.2;
    tx(s, String(i + 1).padStart(2, "0"), { x: 0.6, y, w: 1.1, h: 1.0, size: 40, bold: true, color: NUM, font: FONT, name: "rowNo" });
    tx(s, c.head, { x: 1.8, y: y + 0.05, w: 7.6, h: 0.5, size: 24, bold: true, color: INK, font: FONT, name: "rowHead" });
    tx(s, c.lines.join(" · "), { x: 1.8, y: y + 0.55, w: 7.6, h: 0.4, size: 18, color: GRAY, font: FONT, name: "rowBody" });
    if (i < d.cards.length - 1) box(pres, s, "rect", { x: 0.6, y: y + 1.09, w: 8.8, h: 0.012, fill: LINE, name: "rowRule" }); });
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "PLAIN" }); s.addText(d.title, { placeholder: "title" });
  box(pres, s, "rect", { x: 0.6, y: 1.35, w: 8.8, h: 2.9, fill: PALE, name: "panel" });
  d.qs.forEach((q, i) => { const y = 1.6 + i * 1.3;
    box(pres, s, "rect", { x: 0.95, y: y + 0.33, w: 0.34, h: 0.34, line: { color: INK, width: 1.5 }, name: "check" });
    tx(s, q, { x: 1.6, y, w: 7.5, h: 1.0, size: 24, color: INK, font: FONT, name: "question" }); });
  tx(s, d.note, { x: 0.6, y: 4.4, w: 8.8, h: 0.4, size: 16, color: GRAY, font: FONT, name: "note" });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "solemn-ink", no: 3, name: "엄숙한 보고 · 먹색+백",
    mood: ["엄숙한", "공식적", "보고", "당회", "절제된", "무게 있는", "행정", "회의", "단정", "격식"],
    palette: [["먹색", INK], ["회색(보조 글자)", GRAY], ["옅은 회(판)", PALE], ["진홍(한 곳만)", WINE], ["번호 회색", NUM]],
    fonts: { head: "Apple SD Gothic Neo Bold", body: "Apple SD Gothic Neo", license: "macOS 기본 탑재(Apple 시스템 글꼴 · 파일 재배포 불가)" },
    motifs: ["문서 머리 같은 표지(구분 라벨 + 일자·보고자·구분 칸)", "01·02·03 큰 번호 + 안건 줄(줄 사이 가는 구분선)", "결의 체크 상자 + 질문 24pt", "표·수치가 들어갈 넓은 흰 여백"],
    good: ["당회·제직회·공동의회 보고", "재정·감사·행정 보고", "규정·절차 안내"],
    avoid: ["어린이·청년 행사", "환영·축하 자리", "감성적 메시지"],
    origin: "pptx 스킬 Charcoal Minimal(36454F·F2F2F2·212121) 방향 + 포인트 색을 한 곳(라벨)에만 쓰는 보고서 관례",
    sample: { footer: "2026년 3분기 운영위원회 보고(견본)",
      title: { label: "운영위원회 보고", title: "2026년 3분기 운영위원회 보고", sub: "재정 · 교육 · 시설", fields: [["일자", "2026-11-10"], ["보고", "총무 ○○○"], ["구분", "정기 회의 · 3분기"]] },
      cards: { title: "보고 안건", cards: [{ head: "재정 결산 보고", lines: ["수입·지출 결산", "예산 대비 집행"] }, { head: "교육부 운영 보고", lines: ["과정별 운영 현황", "다음 분기 계획"] }, { head: "시설 보수 계획", lines: ["보수 대상", "일정과 예산안"] }] },
      question: { title: "결의가 필요한 사항", qs: ["시설 보수 예산안을 원안대로 승인할 것인가?", "교육부 신규 과정의 개설 시기를 언제로 할 것인가?"], note: "※ 결의 결과는 회의록에 기록합니다." } } } };
