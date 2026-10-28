// 배경색 커스텀 테마의 순수 계산 — hex 파싱·상대 휘도·가독 대비 전경색 선택.
//
// main.ts의 applyBgColor는 이 함수들에 배선만 한다(DOM·localStorage는 호출측).
// 순수 함수라 어두운 색·밝은 색·경계값을 결정론으로 회귀 테스트할 수 있다(theme.test.ts).

// 기본(다크) 배경·전경 — 하드코딩 리터럴 대신 이 상수를 단일 출처로 참조.
// ★cmux 정합(박사님 2026-10-28 「최대한 cmux 환경과 비슷하게 · 배경색까지」): cmux 기본 테마 =
// Ghostty 「Apple System Colors」(cmux.app/Contents/Resources/ghostty/themes · 바이너리에 같은 값 내장).
// 구 값 = 배경 #0d1117 · 글자 #c9d1d9(회청색 — 대비가 낮아 「뿌옇다」의 한 원인) · 밝은 배경 글자 #1f2328.
export const DEFAULT_BG = "#1e1e1e";
export const DARK_FG = "#ffffff"; // 어두운 배경용 밝은 글자 = cmux foreground
export const LIGHT_FG = "#000000"; // 밝은 배경용 어두운 글자 = cmux 「Apple System Colors Light」 foreground

// "#rrggbb" → [r,g,b] (0-255). 형식이 아니면 null(호출측이 기본색으로 폴백).
// <input type="color">는 항상 6자리 소문자 hex를 준다.
export function hexToRgb(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-fA-F]{6})$/.exec(hex.trim());
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// 상대 휘도(0-1): (0.2126R+0.7152G+0.0722B)를 255로 정규화. 파싱 실패 시 0(어둡다고 간주).
export function relativeLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0;
  const [r, g, b] = rgb;
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}

// 배경 위에서 읽히는 전경색 — 휘도>0.5(밝은 배경)면 어두운 글자, 아니면 밝은 글자.
export function readableForeground(hex: string): string {
  return relativeLuminance(hex) > 0.5 ? LIGHT_FG : DARK_FG;
}

// 터미널 팔레트(ANSI 16색·커서·선택색) — cmux 기본 테마 원값 그대로. 배경 휘도로 다크/라이트 두 벌 중 고른다
// (cmux 도 시스템 모양에 따라 「Apple System Colors」/「… Light」를 쓴다).
export type TermPalette = {
  cursor: string; cursorAccent: string; selectionBackground: string; selectionForeground: string;
  black: string; red: string; green: string; yellow: string; blue: string; magenta: string; cyan: string; white: string;
  brightBlack: string; brightRed: string; brightGreen: string; brightYellow: string;
  brightBlue: string; brightMagenta: string; brightCyan: string; brightWhite: string;
};
export const CMUX_DARK_PALETTE: TermPalette = {
  cursor: "#98989d", cursorAccent: "#ffffff", selectionBackground: "#3f638b", selectionForeground: "#ffffff",
  black: "#1a1a1a", red: "#cc372e", green: "#26a439", yellow: "#cdac08", blue: "#0869cb", magenta: "#9647bf", cyan: "#479ec2", white: "#98989d",
  brightBlack: "#464646", brightRed: "#ff453a", brightGreen: "#32d74b", brightYellow: "#ffd60a",
  brightBlue: "#0a84ff", brightMagenta: "#bf5af2", brightCyan: "#76d6ff", brightWhite: "#ffffff",
};
export const CMUX_LIGHT_PALETTE: TermPalette = {
  ...CMUX_DARK_PALETTE,
  selectionBackground: "#abd8ff", selectionForeground: "#000000",
  brightYellow: "#e5bc00", brightCyan: "#69c9f2",
};

// xterm 테마 한 벌 — 배경은 사용자가 고른 색(없으면 기본), 글자·팔레트는 그 배경의 밝기에 맞는 cmux 값.
export function termTheme(bg: string): TermPalette & { background: string; foreground: string } {
  const light = relativeLuminance(bg) > 0.5;
  return { ...(light ? CMUX_LIGHT_PALETTE : CMUX_DARK_PALETTE), background: bg, foreground: readableForeground(bg) };
}
