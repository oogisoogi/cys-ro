// render_parity 게이트의 페이지 쪽 — 같은 문단을 「수정 전」(old)·「수정 후」(new) 경로로 그려 칸 크기를 잰다.
// ★old 는 2026-10-29 이전 main.ts 의 Terminal 옵션을 그대로 얼려 둔 대조군이다(배경 #0d1117 · 글자 #c9d1d9 ·
//  셀 보정·한글 맞춤 없음). new 는 지금 main.ts 와 같은 함수(termTheme · termFontStack · snapCellsToDevicePixels)를 쓴다.
import { Terminal } from "@xterm/xterm";
import { composeFontFamily, DEFAULT_FONT_STACK } from "../../src/appearance";
import { termTheme } from "../../src/theme";
import { termFontStack, snapCellsToDevicePixels, refreshGlyphWidths, loadBundledFont, remeasureCells } from "../../src/termrender";
const TEXT = [
  "\x1b[0mcys 터미널 렌더 비교 — The quick brown fox jumps over the lazy dog 0123456789",
  "한글 문단: 사용자들이 터미널 형태의 화면에 익숙하지 않다. 글꼴이라도 편하게 볼 수 있어야 한다.",
  "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
  "한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한한",
  "\x1b[31mred \x1b[32mgreen \x1b[33myellow \x1b[34mblue \x1b[35mmagenta \x1b[36mcyan \x1b[1;37mbold-white\x1b[0m  ls -la ~/axdev | grep 'cys' && echo $?",
  "╭──────────────╮  ▌ 상태: 작업 중 · 컨텍스트 34%  │ ✓ 완료",
  "╰──────────────╯",
].join("\r\n");
(window as any).__run = async (arg: string | null) => {
  const [mode, face] = (arg || "new").split(":");
  const el = document.getElementById("t")!;
  // face 「@nosys」 = 글꼴 미설치 기기 흉내 — 스택에서 설치 글꼴 이름 'JetBrains Mono' 를 빼 동봉 글꼴만 남긴다.
  // face 「@sysonly」 = 대조군 — 동봉 글꼴 없이 설치된 JetBrains Mono 만(같은 바이트면 그림이 같아야 한다).
  const base = face === "@nosys" ? DEFAULT_FONT_STACK.replace("'JetBrains Mono', ", "")
    : face === "@sysonly" ? DEFAULT_FONT_STACK.replace("'cys JetBrains Mono', ", "")
    : composeFontFamily(face || null);
  let term: Terminal;
  if (mode === "old") {
    term = new Terminal({ cols: 110, rows: 20, fontFamily: base, fontSize: 13, fontWeight: "normal" as any,
      theme: { background: "#0d1117", foreground: "#c9d1d9" } });
    term.open(el);
  } else {
    let t!: Terminal;
    const fam = termFontStack(base, () => t && refreshGlyphWidths(t));
    t = term = new Terminal({ cols: 110, rows: 20, fontFamily: fam, fontSize: 13, fontWeight: "normal" as any, theme: termTheme("#1e1e1e") });
    term.open(el);
    snapCellsToDevicePixels(term);
    // main.ts 와 같은 순서 — 창을 먼저 만들고(글꼴 아직 안 올라옴), 동봉 글꼴이 올라오면 다시 잰다.
    const ok = await loadBundledFont();
    if (ok) { term.options.fontFamily = termFontStack(base, () => refreshGlyphWidths(t)); remeasureCells(term); }
  }
  await new Promise<void>((r) => term.write(TEXT, () => r()));
  await document.fonts.ready;
  await new Promise((r) => setTimeout(r, 300));
  const dims = (term as any)._core._renderService.dimensions;
  const rows = el.querySelectorAll(".xterm-rows > div");
  const spanOf = (rowIdx: number, ch: string) => {
    const r = rows[rowIdx] as HTMLElement; const range = document.createRange();
    const walker = document.createTreeWalker(r, NodeFilter.SHOW_TEXT); let n: Node | null; const out: number[] = [];
    while ((n = walker.nextNode())) { const t = n.textContent || ""; for (let i = 0; i < t.length; i++) if (t[i] === ch) { range.setStart(n, i); range.setEnd(n, i + 1); const b = range.getBoundingClientRect(); out.push(+b.left.toFixed(2), +b.width.toFixed(2)); if (out.length >= 4) return out; } }
    return out;
  };
  const rowEl = rows[2] as HTMLElement;
  return {
    mode, fontFamily: term.options.fontFamily, dpr: devicePixelRatio,
    cssCell: dims.css.cell, deviceCell: dims.device.cell, deviceChar: dims.device.char,
    rowLineHeight: rowEl?.style.lineHeight, rowLetterSpacing: (el.querySelector(".xterm-rows") as HTMLElement).style.letterSpacing,
    W_row2_first2: spanOf(2, "W"), 한_row3_first2: spanOf(3, "한"),
    hangulFont: (document.fonts as any) && Array.from(document.fonts as any).map((f: any) => `${f.family}:${f.weight}:${f.status}:${f.sizeAdjust}`),
    bundled: Array.from(document.fonts as any).filter((f: any) => f.family.includes("cys JetBrains Mono")).map((f: any) => `${f.style}:${f.status}`),
    bgPixelCss: getComputedStyle(el.querySelector(".xterm-viewport") as HTMLElement).backgroundColor,
  };
};
