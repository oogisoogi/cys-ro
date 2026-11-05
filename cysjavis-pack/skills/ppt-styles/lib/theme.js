// pptxgenjs 가 쓴 pptx 의 테마 색표(ppt/theme/themeN.xml 의 a:clrScheme)를 스타일 THEME 색으로 바꿔 쓴다.
// pptxgenjs 는 글꼴(pres.theme)은 넣지만 색표는 Office 기본값으로 남긴다 → 파워포인트의 「테마 색」 메뉴가 스타일과 어긋난다.
// 우리 구현(표준 동작만: zip 열기 → 색 12칸 교체 → 다시 쓰기). jszip 은 pptxgenjs 와 함께 설치된다.
const fs = require("fs");
const KEYS = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];
const HEX = /^[0-9A-Fa-f]{6}$/;
function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;"); }
async function applyTheme(file, theme) {
  const JSZip = require("jszip");
  const colors = theme.colors || {};
  for (const k of KEYS) if (colors[k] != null && !HEX.test(colors[k])) throw new Error(`THEME.colors.${k} = "${colors[k]}" — 16진수 6자리(# 없이)여야 합니다`);
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  // 슬라이드에 6자리가 아닌 색이 들어가면 파워포인트가 「복구」 창을 띄운다 → 여기서 막는다.
  for (const n of Object.keys(zip.files).filter(n => /^ppt\/slides\/slide\d+\.xml$/.test(n))) {
    const xml = await zip.file(n).async("string");
    const bad = [...xml.matchAll(/<a:srgbClr val="([^"]*)"/g)].map(m => m[1]).filter(v => !HEX.test(v));
    if (bad.length) throw new Error(`${n} 에 잘못된 색 값 ${[...new Set(bad)].join(", ")} — 색은 16진수 6자리(# 없이)로 주세요`);
  }
  const themes = Object.keys(zip.files).filter(n => /^ppt\/theme\/theme\d+\.xml$/.test(n));
  for (const n of themes) {
    let xml = await zip.file(n).async("string");
    if (theme.name) xml = xml.replace(/(<a:theme\b[^>]*\bname=")[^"]*"/, `$1${esc(theme.name)}"`).replace(/(<a:clrScheme\b[^>]*\bname=")[^"]*"/, `$1${esc(theme.name)}"`);
    for (const k of KEYS) {
      if (!colors[k]) continue;
      const re = new RegExp(`<a:${k}>[\\s\\S]*?</a:${k}>`);
      if (!re.test(xml)) throw new Error(`${n} 에 a:${k} 칸이 없습니다(예상과 다른 pptx)`);
      xml = xml.replace(re, `<a:${k}><a:srgbClr val="${colors[k].toUpperCase()}"/></a:${k}>`);
    }
    zip.file(n, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
  return themes.length;
}
module.exports = { applyTheme };
