// 01 교회 강의 · 남색+금 — 우리가 실제 연속 강의 덱에 썼던 THEME·레이아웃·card()·question() 을 옮긴 것(견본 글은 중립 예시)
const { W, H, icon } = require("../lib/kit");
const pi = require("react-icons/pi"); // Phosphor(MIT) — 출처 표기 의무 없음(원래 Font Awesome 은 CC BY 4.0 이라 바꿈)
const FONT = "Apple SD Gothic Neo";
const THEME = { name: "LectureNavyGold", headFontFace: FONT, bodyFontFace: FONT,
  colors: { dk1: "1B2A49", lt1: "FFFFFF", dk2: "3A4A6B", lt2: "EEF1F7", accent1: "C9A227", accent2: "2F6FAE", accent3: "7A5C3E", accent4: "4F7A5A", accent5: "8E4B3A", accent6: "6B6B6B", hlink: "2F6FAE", folHlink: "6B6B6B" } };
const NAVY = "1B2A49", GOLD = "C9A227", INK = "1B2A49", MUTE = "5A6478", PALE = "EEF1F7", WHITE = "FFFFFF", ICE = "CADCFC";
const FOOT_Y = H - 0.38;
function layouts(pres, d) {
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
  pres.defineSlideMaster({ title: "DARK", background: { color: NAVY }, objects: [] });
  pres.defineSlideMaster({ title: "LIGHT", background: { color: WHITE }, objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.32, w: 9.0, h: 0.75, fontSize: 32, bold: true, color: INK, margin: 0, valign: "middle", align: "left" }, text: "" } },
    { text: { text: d.footer, options: { x: 0.5, y: FOOT_Y, w: 6.6, h: 0.3, fontSize: 10, color: MUTE, margin: 0, valign: "middle" } } } ],
    slideNumber: { x: 9.0, y: FOOT_Y, w: 0.5, h: 0.3, fontSize: 10, color: MUTE } });
}
function card(pres, s, x, y, w, h, head, lines, o = {}) { s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: o.fill || PALE }, line: { color: o.fill || PALE }, rectRadius: 0.1, objectName: "card" }); if (head) s.addText(head, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.42, fontSize: o.headSize || 22, bold: true, color: NAVY, margin: 0, isTextBox: true, valign: "middle", objectName: "cardHead" }); if (lines && lines.length) { const r = lines.map((t, i) => ({ text: t, options: { breakLine: i < lines.length - 1, paraSpaceAfter: 4 } })); s.addText(r, { x: x + 0.15, y: y + (head ? 0.56 : 0.12), w: w - 0.3, h: h - (head ? 0.66 : 0.24), fontSize: o.size || 20, color: INK, margin: 0, isTextBox: true, valign: "top", objectName: "cardBody" }); } }
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "DARK" });
  s.addShape(pres.ShapeType.rect, { x: 0.7, y: 0.85, w: 0.9, h: 0.07, fill: { color: GOLD }, line: { color: GOLD }, objectName: "bar" });
  s.addText(d.title, { x: 0.7, y: 1.1, w: 7.2, h: 0.9, fontSize: 44, bold: true, color: WHITE, margin: 0, isTextBox: true, objectName: "t1" });
  s.addText(d.sub, { x: 0.7, y: 2.0, w: 7.2, h: 0.7, fontSize: 28, color: GOLD, margin: 0, isTextBox: true, objectName: "t2" });
  s.addText(d.lead, { x: 0.7, y: 2.75, w: 8.0, h: 0.5, fontSize: 20, color: ICE, margin: 0, isTextBox: true, objectName: "t3" });
  s.addImage({ data: await icon(pi.PiScrollFill, GOLD), x: 8.1, y: 1.15, w: 1.2, h: 1.2, objectName: "ico" });
  s.addText(d.meta, { x: 0.7, y: 3.55, w: 6.5, h: 0.4, fontSize: 18, color: ICE, margin: 0, isTextBox: true, objectName: "t4" });
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "LIGHT" }); s.addText(d.title, { placeholder: "title" });
  card(pres, s, 0.5, 1.25, 4.3, 2.9, d.cards[0].head, d.cards[0].lines, { size: 17 });
  s.addShape(pres.ShapeType.rightArrow, { x: 4.83, y: 2.5, w: 0.34, h: 0.4, fill: { color: GOLD }, line: { color: GOLD }, objectName: "flowArrow" });
  card(pres, s, 5.2, 1.25, 4.3, 2.9, d.cards[1].head, d.cards[1].lines, { size: 17 });
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "LIGHT" }); s.addText(d.title, { placeholder: "title" });
  s.addText("?", { x: 0.5, y: 1.2, w: 1.6, h: 3.0, fontSize: 150, bold: true, color: GOLD, margin: 0, isTextBox: true, valign: "middle", align: "center", objectName: "qmark" });
  const r = d.qs.map((t, i) => ({ text: t, options: { breakLine: i < d.qs.length - 1, paraSpaceAfter: 16 } }));
  s.addText(r, { x: 2.3, y: 1.25, w: 7.0, h: 3.3, fontSize: 24, color: INK, margin: 0, isTextBox: true, valign: "middle", objectName: "questions" });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "church-navy-gold", no: 1, name: "교회 강의 · 남색+금",
    mood: ["차분한", "격조", "교회", "강의", "고전", "신뢰", "단정", "정돈된", "성경공부", "연속 강좌"],
    palette: [["남색", "1B2A49"], ["금", "C9A227"], ["옅은 청회", "EEF1F7"], ["청", "2F6FAE"], ["회청(보조 글자)", "5A6478"]],
    fonts: { head: "Apple SD Gothic Neo Bold", body: "Apple SD Gothic Neo", license: "macOS 기본 탑재(Apple 시스템 글꼴 · 글꼴 파일 재배포 불가 · 윈도·리눅스에는 없어 열면 대체 글꼴로 보인다)" },
    motifs: ["어두운 표지 + 밝은 본문(샌드위치)", "옅은 청회 둥근 카드", "금색 화살표·아이콘(Phosphor)", "금색 큰 물음표 + 질문 24pt", "숫자 콜아웃·시간선·표"],
    good: ["성경 강의·연속 강좌", "교리·성경공부·사내 교육 연속 강좌", "줌 PPT 배경 모드(오른쪽 아래 비움)"],
    avoid: ["어린이 대상", "홍보·행사 포스터처럼 눈길을 끌어야 하는 자리"],
    origin: "우리가 실제 연속 강의 덱에 쓴 구성. 남색+금 조합은 Anthropic pptx 스킬이 권하는 Midnight Executive 팔레트와 같은 방향",
    sample: { footer: "데이터 읽기 기초 — 2강 표와 그래프 읽기  |  사내 아카데미(견본)",
      title: { title: "데이터 읽기 기초", sub: "2강. 표와 그래프 읽기", lead: "A. 표를 읽는 순서 → 행 · 열 · 단위      B. 그래프의 함정", meta: "사내 아카데미(견본) · 2026-11-10(화)" },
      cards: { title: "오늘의 흐름", cards: [{ head: "A. 표를 읽는 순서", lines: ["행 · 열 · 단위", "1. 제목과 기준 시점 확인", "2. 단위와 반올림 확인", "3. 합계와 비율 대조", "4. 빠진 칸 찾기"] }, { head: "B. 그래프의 함정", lines: ["세로축이 0에서 시작하는가", "막대 — 크기 비교", "선 — 시간에 따른 변화", "원 — 전체 중 비율", "두 축 그래프 — 오독 주의"] }] },
      question: { title: "함께 생각해 봅시다", qs: ["최근에 본 그래프 가운데 처음 읽은 뜻과 실제 수치가 달랐던 것이 있습니까?", "우리 팀 보고서에서 단위를 가장 자주 빠뜨리는 표는 무엇입니까?"] } } } };
