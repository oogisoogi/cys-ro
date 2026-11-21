// 11 다크 라임 해설 · 먹+라임 한 점 — 어두운 기술 해설 영상 화면의 화소를 우리가 실측한 값(2026-10-30)으로 다시 짠 조합 · 먹 바탕 · 흰 굵은 제목 · 라임은 낱말 하나·활성 칩 하나만
const { W, H, tx, box, runs } = require("../lib/kit");
const FONT = "Apple SD Gothic Neo", MONO = "JetBrains Mono"; // 제목은 Pretendard 가 있으면 바꿔 써도 어울린다 · MONO 는 숫자·영문에만(한글이 없어 섞으면 명조로 대체된다)
const INK = "040606", PANEL = "121414", CHIP = "444444", WHITE = "F5F6F5", GRAY = "A6A8A8", DIM = "646462", LIME = "D8F629", BLACK = "000000"; // 전부 우리 화소 실측값
const THEME = { name: "LimeDark", headFontFace: FONT, bodyFontFace: FONT,
  colors: { dk1: INK, lt1: WHITE, dk2: PANEL, lt2: "F6F4F0", accent1: LIME, accent2: CHIP, accent3: GRAY, accent4: DIM, accent5: "1E1E1C", accent6: "555D02", hlink: LIME, folHlink: GRAY } };
function layouts(pres, d) {
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
  pres.defineSlideMaster({ title: "COVER", background: { color: INK }, objects: [] });
  pres.defineSlideMaster({ title: "LECTURE", background: { color: INK }, objects: [
    { text: { text: d.footer, options: { x: 0.4, y: 0.18, w: 6.6, h: 0.4, fontSize: 16, bold: true, color: WHITE, fontFace: FONT, margin: 0 } } },
    { rect: { x: 7.3, y: 0.2, w: 2.3, h: 0.36, fill: { color: INK }, line: { color: DIM, width: 0.75 }, rectRadius: 0.06 } },
    { text: { text: d.badge, options: { x: 7.3, y: 0.2, w: 2.3, h: 0.36, fontSize: 10, bold: true, color: LIME, fontFace: FONT, align: "center", margin: 0 } } },
    { rect: { x: 0.4, y: 0.75, w: 9.2, h: 4.45, fill: { color: INK }, line: { color: "2F2F2C", width: 0.75 } } } ],
    slideNumber: { x: 9.0, y: H - 0.35, w: 0.6, h: 0.25, fontSize: 9, color: DIM, fontFace: MONO, align: "right" } });
}
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "COVER" });
  tx(s, d.eyebrow, { x: 0.7, y: 0.9, w: 8.6, h: 0.45, size: 18, bold: true, color: GRAY, font: FONT, name: "eyebrow" });
  tx(s, [{ text: d.title + " ", options: { color: WHITE } }, { text: d.lime, options: { color: LIME } }], { x: 0.7, y: 1.45, w: 8.6, h: 1.3, size: 54, bold: true, font: FONT, name: "t1" });
  box(pres, s, "rect", { x: 0.7, y: 3.0, w: 0.06, h: 1.15, fill: LIME, name: "limeBar" });
  box(pres, s, "rect", { x: 0.76, y: 3.0, w: 5.6, h: 1.15, fill: PANEL, name: "subCard" });
  tx(s, d.sub, { x: 1.0, y: 3.08, w: 5.2, h: 0.6, size: 28, bold: true, color: WHITE, font: FONT, name: "t2" });
  tx(s, d.note, { x: 1.0, y: 3.62, w: 5.2, h: 0.45, size: 18, color: GRAY, font: FONT, name: "t3" });
  tx(s, d.fields.join("  ·  "), { x: 0.7, y: 4.85, w: 8.6, h: 0.3, size: 11, color: DIM, font: FONT, charSpacing: 1, name: "meta" });
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "LECTURE" });
  tx(s, "| " + d.label, { x: 0.8, y: 0.95, w: 6, h: 0.35, size: 14, color: GRAY, font: FONT, name: "label" });
  tx(s, [{ text: d.title + " ", options: { color: WHITE } }, { text: d.lime, options: { color: BLACK, highlight: LIME } }], { x: 0.8, y: 1.3, w: 8.4, h: 0.8, size: 36, bold: true, font: FONT, name: "title" });
  tx(s, "한마디로: " + d.gloss, { x: 0.8, y: 2.08, w: 8.4, h: 0.4, size: 16, color: GRAY, font: FONT, name: "gloss" });
  d.cards.forEach((c, i) => { const y = 2.7 + i * 0.78, on = i === d.active;
    box(pres, s, "roundRect", { x: 0.8, y, w: 5.4, h: 0.62, fill: on ? LIME : CHIP, radius: 0.08, name: "chip" });
    tx(s, String(i + 1).padStart(2, "0"), { x: 0.95, y, w: 0.6, h: 0.62, size: 16, bold: true, color: on ? BLACK : DIM, font: MONO, name: "chipNo" });
    tx(s, c.head, { x: 1.55, y, w: 1.9, h: 0.62, size: 22, bold: true, color: on ? BLACK : WHITE, font: FONT, name: "chipHead" });
    tx(s, c.lines.join(" "), { x: 3.4, y, w: 2.75, h: 0.62, size: 16, color: on ? BLACK : GRAY, font: FONT, name: "chipBody" }); });
  box(pres, s, "rect", { x: 6.6, y: 2.7, w: 2.6, h: 2.18, fill: INK, line: { color: LIME, width: 1.25 }, name: "diagram" });
  tx(s, d.side, { x: 6.75, y: 2.85, w: 2.3, h: 1.9, size: 16, color: WHITE, font: FONT, valign: "top", name: "diagramText" });
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "COVER" });
  tx(s, "| " + d.label, { x: 0.7, y: 1.2, w: 8.6, h: 0.4, size: 16, color: GRAY, font: FONT, align: "center", name: "label" });
  tx(s, [{ text: d.qs[0] + " ", options: { color: WHITE } }, { text: d.lime, options: { color: BLACK, highlight: LIME } }, { text: d.after || "", options: { color: WHITE } }], { x: 0.7, y: 1.7, w: 8.6, h: 1.5, size: 44, bold: true, font: FONT, align: "center", name: "q1" });
  tx(s, d.qs[1], { x: 0.7, y: 3.35, w: 8.6, h: 0.6, size: 24, color: GRAY, font: FONT, align: "center", name: "q2" });
  box(pres, s, "rect", { x: 4.6, y: 4.3, w: 0.8, h: 0.05, fill: LIME, name: "limeRule" });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "lime-dark", no: 11, name: "다크 라임 해설 · 먹+라임 한 점",
    mood: ["다크", "어두운", "라임", "테크", "개발자", "해설", "강의 영상", "유튜브", "모던", "선명한"],
    palette: [["먹(바탕)", INK], ["짙은 면(카드)", PANEL], ["칩 회색", CHIP], ["흰 글자", WHITE], ["회색 보조 글자", GRAY], ["흐린 글자", DIM], ["라임(강조 · 화면의 1~3%)", LIME]],
    fonts: { head: "Apple SD Gothic Neo Bold(Pretendard 가 있으면 바꿔 써도 된다)", body: "Apple SD Gothic Neo · 눈썹·번호 = JetBrains Mono", license: "Apple SD Gothic Neo = macOS 기본(재배포 불가 · 윈도·리눅스에는 없음) · JetBrains Mono = OFL 1.1(설치돼 있으면 쓰고 없으면 대체 글꼴로 보인다)" },
    motifs: ["먹 바탕 + 흰 54pt 굵은 제목 + 마지막 낱말만 라임 글자", "「| 라벨」 → 굵은 제목(낱말 하나 라임 형광) → 「한마디로:」 회색 풀이 3단", "번호 칩 목록 — 지금 말하는 항목만 라임 칩·검정 글자, 나머지는 회색 칩", "라임 외곽선 상자 하나로 도식", "아이콘 없음 · 그림자 없음"],
    good: ["AI·기술 해설 강의(영상·PPT)", "유튜브 설명 화면·라이브 자료", "개발·자동화 사례 발표"],
    avoid: ["어린이·가족 행사", "추모 예배", "인쇄물(먹 바탕은 잉크·가독성 손해)"],
    origin: "어두운 기술 해설 영상 화면 4편의 화소를 우리가 실측한 색값(2026-10-30)으로 다시 짠 조합 — 그림·글꼴·문구는 가져오지 않았다",
    sample: { footer: "자동화 입문 EP1 · 반복 업무를 맡기는 법", badge: "시리즈 · 자동화 입문 EP1",
      title: { eyebrow: "기술 해설 강의(견본)", title: "자동화 입문", lime: "EP1", sub: "어떤 일부터 맡겨야 할까?", note: "5편 시리즈의 첫 질문", fields: ["2026-11-10", "샘플 문구", "ppt-styles 11"] },
      cards: { label: "맡기기 전에 정할 것", title: "자동화의", lime: "첫 단추", gloss: "무엇을 맡길지부터 고른다", active: 1, side: "칩은 말하는 순서대로 하나씩 켠다 — 지금 말하는 항목만 라임.",
        cards: [{ head: "반복", lines: ["매주 되풀이되는 일"] }, { head: "규칙", lines: ["판단 기준이 글로 적히는 일"] }, { head: "확인", lines: ["결과를 사람이 검토할 자리"] }] },
      question: { label: "생각해 볼 질문", qs: ["가장 먼저 맡길", "매주 30분 이상 드는 반복 업무에서 찾아본다"], lime: "자동화", after: " 대상은?" } } } };
