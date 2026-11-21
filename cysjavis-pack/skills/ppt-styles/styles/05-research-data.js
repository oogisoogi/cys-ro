// 05 연구 발표 · 잉크+청록 — 숫자 콜아웃 · 네이티브 차트 · RQ 꼬리표 · 출처 줄
const { W, H, tx, box, runs, icon } = require("../lib/kit");
const pi = require("react-icons/pi"); // Phosphor(MIT) — 출처 표기 의무 없음
const HEAD = "NanumSquare Neo", BODY = "NanumBarunGothic";
const INK = "0F172A", TEAL = "0E7490", ORANGE = "EA580C", SLATE = "64748B", PALE = "F1F5F9", GRID = "E2E8F0", WHITE = "FFFFFF";
const THEME = { name: "ResearchData", headFontFace: HEAD, bodyFontFace: BODY,
  colors: { dk1: INK, lt1: WHITE, dk2: "334155", lt2: PALE, accent1: TEAL, accent2: ORANGE, accent3: "0891B2", accent4: SLATE, accent5: "94A3B8", accent6: "155E75", hlink: TEAL, folHlink: SLATE } };
function layouts(pres, d) {
  pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
  pres.defineSlideMaster({ title: "COVER", background: { color: WHITE }, objects: [] });
  pres.defineSlideMaster({ title: "DATA", background: { color: WHITE }, objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9.0, h: 0.7, fontSize: 28, bold: true, color: INK, fontFace: HEAD, margin: 0, valign: "middle", align: "left" }, text: "" } },
    { text: { text: d.footer, options: { x: 0.5, y: H - 0.38, w: 7.5, h: 0.28, fontSize: 10, color: SLATE, fontFace: BODY, margin: 0 } } } ],
    slideNumber: { x: 9.0, y: H - 0.38, w: 0.5, h: 0.28, fontSize: 10, color: SLATE, fontFace: BODY, align: "right" } });
}
async function titleSlide(pres, d) {
  const s = pres.addSlide({ masterName: "COVER" });
  box(pres, s, "rect", { x: 0, y: 0, w: 4.3, h: H, fill: INK, name: "panel" });
  tx(s, "RESEARCH REPORT", { x: 0.6, y: 0.8, w: 3.4, h: 0.3, size: 12, bold: true, color: "67E8F9", font: HEAD, charSpacing: 3, name: "label" });
  tx(s, d.title, { x: 0.6, y: 1.3, w: 3.4, h: 1.5, size: 36, bold: true, color: WHITE, font: HEAD, valign: "top", name: "t1" });
  tx(s, d.sub, { x: 0.6, y: 3.0, w: 3.3, h: 1.2, size: 16, color: "CBD5E1", font: BODY, valign: "top", name: "t2" });
  s.addImage({ data: await icon(pi.PiChartBarFill, TEAL), x: 8.5, y: 0.6, w: 0.9, h: 0.9, objectName: "ico" });
  d.fields.forEach(([k, v], i) => { const y = 1.9 + i * 0.95;
    tx(s, k, { x: 4.9, y, w: 4.5, h: 0.3, size: 12, color: SLATE, font: BODY, name: "metaKey" });
    tx(s, v, { x: 4.9, y: y + 0.3, w: 4.5, h: 0.45, size: 20, bold: true, color: INK, font: BODY, name: "metaVal" }); });
}
async function cardSlide(pres, d) {
  const s = pres.addSlide({ masterName: "DATA" }); s.addText(d.title, { placeholder: "title" });
  d.stats.forEach(([n, l], i) => { const x = 0.5 + i * 3.05;
    box(pres, s, "roundRect", { x, y: 1.15, w: 2.9, h: 1.3, fill: PALE, radius: 0.06, name: "stat" });
    tx(s, n, { x: x + 0.2, y: 1.2, w: 2.5, h: 0.75, size: 40, bold: true, color: i === 2 ? ORANGE : TEAL, font: HEAD, name: "statNo" });
    tx(s, l, { x: x + 0.2, y: 1.95, w: 2.5, h: 0.4, size: 14, color: SLATE, font: BODY, name: "statLabel" }); });
  // 세로축 = 값에 맞춰 둥근 최댓값(견본 4.4 → 5 · 428 → 500) · 정수만이면 천 단위 쉼표, 아니면 소수 한 자리(chart.max · chart.format 으로 덮어쓰기)
  const vmax = Math.max(0, ...d.chart.values.map(Number).filter(v => !isNaN(v))), step = vmax > 0 ? Math.pow(10, Math.floor(Math.log10(vmax))) : 1;
  const axMax = d.chart.max || Math.ceil(vmax / step) * step || 1, fmt = d.chart.format || (d.chart.values.every(v => Number.isInteger(+v)) ? "#,##0" : "0.0");
  s.addChart(pres.charts.BAR, [{ name: d.chart.name, labels: d.chart.labels, values: d.chart.values }], { x: 0.5, y: 2.65, w: 5.6, h: 2.4, barDir: "col", chartColors: [TEAL], showLegend: false, showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: fmt, valAxisMaxVal: axMax, valAxisMajorUnit: d.chart.max ? undefined : step, valAxisLabelFormatCode: "#,##0", dataLabelFontSize: 11, dataLabelColor: INK, dataLabelFontFace: BODY, catAxisLabelFontSize: 11, catAxisLabelColor: SLATE, catAxisLabelFontFace: BODY, valAxisLabelFontSize: 10, valAxisLabelColor: SLATE, valAxisLabelFontFace: BODY, valGridLine: { color: GRID, size: 0.5 }, catGridLine: { style: "none" }, objectName: "chart" });
  tx(s, runs(d.notes, 8, { bullet: true }), { x: 6.4, y: 2.75, w: 3.1, h: 1.9, size: 16, color: INK, font: BODY, valign: "top", name: "commentary" });
  tx(s, d.source, { x: 6.4, y: 4.7, w: 3.1, h: 0.3, size: 10, color: SLATE, font: BODY, name: "source" });
}
async function questionSlide(pres, d) {
  const s = pres.addSlide({ masterName: "DATA" }); s.addText(d.title, { placeholder: "title" });
  d.qs.forEach((q, i) => { const y = 1.35 + i * 1.45;
    box(pres, s, "roundRect", { x: 0.5, y: y + 0.28, w: 1.1, h: 0.5, fill: i ? ORANGE : TEAL, radius: 0.08, name: "rqTag" });
    tx(s, "RQ" + (i + 1), { x: 0.5, y: y + 0.28, w: 1.1, h: 0.5, size: 16, bold: true, color: WHITE, font: HEAD, align: "center", name: "rqTagText" });
    tx(s, q, { x: 1.9, y, w: 7.6, h: 1.05, size: 24, color: INK, font: BODY, name: "question" }); });
  box(pres, s, "rect", { x: 0.5, y: 4.3, w: 9.0, h: 0.6, fill: PALE, name: "band" });
  tx(s, d.note, { x: 0.7, y: 4.3, w: 8.6, h: 0.6, size: 16, color: SLATE, font: BODY, name: "note" });
}
module.exports = { THEME, layouts, titleSlide, cardSlide, questionSlide,
  meta: { id: "research-data", no: 5, name: "연구 발표 · 잉크+청록",
    mood: ["연구", "데이터", "분석적", "객관적", "학술", "명료한", "수치", "차트", "논문", "통계"],
    palette: [["잉크", INK], ["청록", TEAL], ["주황(강조 한 곳)", ORANGE], ["슬레이트(보조 글자)", SLATE], ["옅은 청회(판)", PALE]],
    fonts: { head: "나눔스퀘어 네오 Bold", body: "나눔바른고딕", license: "네이버 나눔글꼴 · SIL OFL 1.1" },
    motifs: ["왼쪽 잉크 패널 표지 + 오른쪽 조사 개요 칸", "40pt 숫자 콜아웃 3개", "네이티브 막대 차트(파워포인트에서 값 수정 가능) + 해석 글머리", "RQ1·RQ2 꼬리표 질문", "출처·표본 각주 줄"],
    good: ["연구·설문 결과 발표", "학회·세미나", "현황 분석·통계 보고"],
    avoid: ["어린이·가족 행사", "감성·묵상 중심 자리", "숫자가 없는 이야기 발표"],
    origin: "색 = Tailwind CSS 색 체계(slate-900 · cyan-700 · orange-600 · slate-500 · slate-100 · MIT) · 구성 = pptx 스킬의 「stat callout · chart + commentary」 권고",
    sample: { footer: "교육 프로그램 참여 실태 조사 — 아래 수치는 전부 서식 시연용 샘플이다",
      title: { title: "설문 결과 보고", sub: "교육 프로그램 참여 실태 조사\n(서식 시연용 샘플 데이터)", fields: [["조사 대상", "교육 프로그램 참여자(샘플)"], ["조사 기간", "2026년 9월(샘플)"], ["분석 방법", "기술 통계 · 교차 분석"]] },
      cards: { title: "핵심 수치 (샘플 데이터)", stats: [["240명", "응답자 수"], ["62%", "응답률"], ["3.8회", "월 평균 참여(가장 큰 차이)"]], chart: { name: "월 평균 참여 횟수", labels: ["20대", "30대", "40대", "50대+"], values: [2.1, 2.9, 3.8, 4.4] }, notes: ["연령이 높을수록 참여가 잦다", "20대와 50대+의 차이가 가장 크다", "30대 표본은 더 모아야 한다"], source: "출처: 자체 설문(샘플) · n=240" },
      question: { title: "연구 질문", qs: ["참여 빈도는 연령대에 따라 달라지는가?", "지속 참여를 설명하는 요인은 무엇인가?"], note: "가설과 분석 방법은 다음 장에서 다룬다." } } } };
