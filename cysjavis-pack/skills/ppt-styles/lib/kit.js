// ppt-styles 공통 키트 — 스타일 파일이 쓰는 최소 도우미(텍스트·도형·아이콘·줄 묶음). pptxgenjs 함정은 여기서 한 번만 막는다.
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const sharp = require("sharp");
const W = 10, H = 5.625; // LAYOUT_16x9 (인치)
// 글자 상자: isTextBox(접근성) · margin 0(도형과 줄 맞춤) · fontFace 명시(한글 a:ea 까지 같은 글꼴로 적힌다)
function tx(s, text, o) { const { size, font, name, ...rest } = o; s.addText(text, { margin: 0, isTextBox: true, valign: "middle", fontSize: size, fontFace: font, objectName: name || "text", ...rest }); }
// 도형: fill 을 hex 로 주면 테두리도 같은 색(이음매 없음) · fill 없이 line 만 주면 외곽선 도형
function box(pres, s, kind, o) { const { fill, line, name, radius, ...rest } = o; const opt = { ...rest, objectName: name || "shape" }; if (fill) opt.fill = { color: fill, transparency: o.alpha || 0 }; opt.line = line || (fill ? { color: fill, width: 0 } : { type: "none" }); if (radius != null) opt.rectRadius = radius; delete opt.alpha; s.addShape(pres.ShapeType[kind], opt); }
// 여러 줄 → 문단 묶음(마지막 줄만 breakLine 없음 · 문단 간격은 paraSpaceAfter)
function runs(lines, gap = 6, opt = {}) { return lines.map((t, i) => ({ text: t, options: { breakLine: i < lines.length - 1, paraSpaceAfter: gap, ...opt } })); }
// react-icons 컴포넌트 → PNG data URI(색 = hex 6자리)
async function icon(Comp, color, px = 256) { const svg = renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: px })); const buf = await sharp(Buffer.from(svg)).png().toBuffer(); return "image/png;base64," + buf.toString("base64"); }
module.exports = { W, H, tx, box, runs, icon };
