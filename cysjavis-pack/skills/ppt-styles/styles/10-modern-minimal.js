// 10 모던 미니멀 · 흑백+빨강 한 점 — 큰 검정 글자 · 빨간 정사각형 하나 · 번호 정사각형 3단
const { W, H, tx, box, runs } = require("../lib/kit");
const FONT = "Apple SD Gothic Neo";
const BLACK = "111111", WHITE = "FFFFFF", RED = "E63946", GRAY = "6B7280", LIGHT = "F3F4F6", DIM = "9CA3AF";
const THEME = { name: "ModernMinimal", headFontFace: FONT, bodyFontFace: FONT,
  colors: { dk1: BLACK, lt1: WHITE, dk2: "374151", lt2: LIGHT, accent1: RED, accent2: BLACK, accent3: GRAY, accent4: DIM, accent5: "D1D5DB", accent6: "4B5563", hlink: RED, folHlink: GRAY } };
function layouts(pres, d) {
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
  pres.defineSlideMaster({ title: "COVER", background: { color: WHITE }, objects: [] });
  pres.defineSlideMaster({ title: "BLACK", background: { color: BLACK }, objects: [] });
  pres.defineSlideMaster({ title: "WHITE", background: { color: WHITE }, objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 8.8, h: 0.75, fontSize: 32, bold: true, color: BLACK, fontFace: FONT, margin: 0, valign: "middle", align: "left" }, text: "" } },
    { text: { text: d.footer, options: { x: 0.6, y: H - 0.4, w: 7, h: 0.3, fontSize: 10, color: GRAY, fontFace: FONT, margin: 0 } } } ],
    slideNumber: { x: 8.9, y: H - 0.4, w: 0.5, h: 0.3, fontSize: 10, color: GRAY, fontFace: FONT, align: "right" } });
}
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "COVER" });
  box(pres, s, "rect", { x: 0.6, y: 0.7, w: 0.36, h: 0.36, fill: RED, name: "dot" });
  tx(s, d.title, { x: 0.6, y: 1.3, w: 8.8, h: 2.0, size: 56, bold: true, color: BLACK, font: FONT, name: "t1" });
  tx(s, d.sub, { x: 0.6, y: 3.4, w: 8.6, h: 0.6, size: 24, color: GRAY, font: FONT, name: "t2" });
  d.fields.forEach((v, i) => tx(s, v, { x: 0.6 + i * 3.0, y: 4.75, w: 2.8, h: 0.3, size: 12, color: GRAY, font: FONT, name: "metaCol" }));
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "WHITE" }); s.addText(d.title, { placeholder: "title" });
  d.cards.forEach((c, i) => { const x = 0.6 + i * 3.0;
    box(pres, s, "rect", { x, y: 1.5, w: 0.7, h: 0.7, fill: i === 0 ? RED : BLACK, name: "noBox" });
    tx(s, String(i + 1), { x, y: 1.5, w: 0.7, h: 0.7, size: 24, bold: true, color: WHITE, font: FONT, align: "center", name: "noText" });
    tx(s, c.head, { x, y: 2.45, w: 2.7, h: 0.6, size: 28, bold: true, color: BLACK, font: FONT, name: "colHead" });
    tx(s, c.lines.join(" "), { x, y: 3.1, w: 2.7, h: 1.5, size: 18, color: GRAY, font: FONT, valign: "top", name: "colBody" }); });
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "BLACK" });
  box(pres, s, "rect", { x: 0.6, y: 0.7, w: 0.36, h: 0.36, fill: RED, name: "dot" });
  tx(s, d.qs[0], { x: 0.6, y: 1.35, w: 8.8, h: 1.7, size: 40, bold: true, color: WHITE, font: FONT, name: "q1" });
  tx(s, d.qs[1], { x: 0.6, y: 3.3, w: 8.8, h: 1.0, size: 24, color: DIM, font: FONT, name: "q2" });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "modern-minimal", no: 10, name: "모던 미니멀 · 흑백+빨강 한 점",
    mood: ["깔끔한", "미니멀", "현대적", "세련된", "단순한", "여백", "프로페셔널", "기술", "선명한", "군더더기 없는"],
    palette: [["검정", BLACK], ["흰색", WHITE], ["빨강(한 점)", RED], ["회색(보조 글자)", GRAY], ["옅은 회", LIGHT]],
    fonts: { head: "Apple SD Gothic Neo Bold", body: "Apple SD Gothic Neo", license: "macOS 기본 탑재(Apple 시스템 글꼴 · 파일 재배포 불가)" },
    motifs: ["흰 바탕 + 56pt 검정 제목 + 빨간 정사각형 하나", "번호 정사각형 3단(상자·그림자 없음)", "검정 전면 + 흰 큰 질문", "아이콘 없음 · 왼쪽 정렬만"],
    good: ["AI·기술 세미나", "사업·기획 제안", "외부 기관 대상 소개 자료"],
    avoid: ["어린이·가족 행사(차갑게 보인다)", "추모 예배", "따뜻한 환영 자리"],
    origin: "frontend-slides 「Swiss Modern」(흑백 + 빨강 · 격자 · MIT) + pptx 스킬 Charcoal Minimal",
    sample: { footer: "AI 시대의 교회 행정",
      title: { title: "AI 시대의\n교회 행정", sub: "도구는 바뀌고, 목적은 남는다", fields: ["2026-10-13", "발표 ○○○", "교회 행정 세미나"] },
      cards: { title: "세 가지 원칙", cards: [{ head: "단순하게", lines: ["한 번에 한 가지 일만 맡긴다."] }, { head: "기록으로", lines: ["사람의 기억이 아니라 문서에 남긴다."] }, { head: "사람 먼저", lines: ["결정과 돌봄은 사람이 맡는다."] }] },
      question: { title: "", qs: ["우리가 자동화하려는 일은\n무엇인가?", "사람이 반드시 맡아야 할 일은 무엇인가?"] } } } };
