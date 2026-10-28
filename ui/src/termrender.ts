// 터미널 글자 렌더를 cmux(Ghostty)와 같게 — 셀 크기·한글 폭 (TICKET=cysr-cmux-render-parity).
//
// 박사님 2026-10-28: 「폰트를 바꾸어도 얇기, 장평, 자간이 다르고 … 최대한 cmux 환경과 비슷하게」.
// 차이의 근거(Ghostty 원본 src/font · xterm 5.5 원본 src/browser 대조):
//  ① 셀 폭·높이 — Ghostty Metrics.calc 는 글꼴의 글자 폭·줄 높이를 **장치 화소로 반올림**한다
//     (JetBrains Mono 13pt·레티나 = 15.6→16 · 34.32→34 장치px = 8×17 css px). xterm DOM 렌더러는
//     폭을 반올림하지 않고(7.8) 높이를 올림한다(ceil 34.32=35 → 17.5). 한 칸 차이는 1px 미만이지만
//     120칸·35줄에 쌓이면 줄이 24px 좁고 화면이 17px 길어져 「장평·자간이 다르다」로 보인다.
//  ② 한글 폭 — Ghostty 는 대체 글꼴(한글 = Apple SD Gothic Neo)을 주 글꼴의 「水」 폭(ic_width)에 맞춰
//     키운다(Collection.scaleFactor · default_fallback_adjustment = .ic_width). xterm 은 원래 크기
//     (0.865em = 11.2px)로 두 칸(15.6px)에 그려 글자 뒤에 4px 틈이 생긴다(「한글 자간 틈」).
// 순수 계산은 이 파일 위쪽(termrender.test.ts), DOM·xterm 배선은 아래쪽이다.

// ── 순수 계산 ─────────────────────────────────────────────

// Ghostty Metrics.calc: cell = @round(face 값) — 장치 화소 단위. css px 로 되돌려 준다.
export function ghosttyCellCss(cssPx: number, dpr: number): number {
  if (!(cssPx > 0) || !(dpr > 0)) return cssPx;
  return Math.max(1, Math.round(cssPx * dpr)) / dpr;
}

// Ghostty Collection.scaleFactor(.ic_width) — 주 글꼴에 「水」가 없으면 icWidth = min(asciiHeight, 2×cellWidth)
// (Metrics.FaceMetrics.icWidth 추정식). 모든 값은 em 단위. 비정상 입력·터무니없는 배율은 1(손대지 않음).
export function hangulFitScale(cellWidthEm: number, asciiHeightEm: number, fallbackIcEm: number): number {
  if (!(cellWidthEm > 0) || !(fallbackIcEm > 0)) return 1;
  const primaryIc = asciiHeightEm > 0 ? Math.min(asciiHeightEm, 2 * cellWidthEm) : 2 * cellWidthEm;
  const s = primaryIc / fallbackIcEm;
  if (!Number.isFinite(s) || s < 0.5 || s > 2) return 1;
  return Math.round(s * 1000) / 1000;
}

// 한글 대체 글꼴 — 맥 = Apple SD Gothic Neo · 윈 = 맑은 고딕 · 그 밖 = Noto Sans KR. local() 이름은
// PostScript 이름과 전체 이름을 같이 둔다(엔진마다 맞추는 이름이 다르다).
export const HANGUL_FALLBACK_STACK = "'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR'";
const HANGUL_LOCAL = {
  normal: ["AppleSDGothicNeo-Regular", "Apple SD Gothic Neo Regular", "Malgun Gothic", "MalgunGothic", "NotoSansKR-Regular", "Noto Sans KR Regular"],
  bold: ["AppleSDGothicNeo-Bold", "Apple SD Gothic Neo Bold", "Malgun Gothic Bold", "MalgunGothicBold", "NotoSansKR-Bold", "Noto Sans KR Bold"],
};
// 한글 자모·호환 자모·음절만 — 한자·구두점은 배율을 걸지 않는다(정렬 기호가 커지면 줄이 어긋난다).
export const HANGUL_UNICODE_RANGE = "U+1100-11FF, U+3130-318F, U+A960-A97F, U+AC00-D7AF, U+D7B0-D7FF";

export function hangulFitFamily(scale: number): string {
  return `cys-hangul-fit-${Math.round(scale * 1000)}`;
}

// 글꼴 스택에 맞춤 한글 글꼴을 끼운다 — 한글 대체 글꼴 바로 앞. 사용자가 고른 글꼴에 한글이 있으면
// (D2Coding 등) 그 글꼴이 앞에서 먼저 잡히므로 영향이 없다(Ghostty 도 주 글꼴에 있는 글자는 안 키운다).
export function withHangulFit(stack: string, fitFamily: string | null): string {
  if (!fitFamily) return stack;
  const anchor = "'Apple SD Gothic Neo'";
  const i = stack.indexOf(anchor);
  return i < 0 ? `${stack}, '${fitFamily}'` : `${stack.slice(0, i)}'${fitFamily}', ${stack.slice(i)}`;
}

// ── DOM·xterm 배선 ───────────────────────────────────────

const ASCII = Array.from({ length: 95 }, (_, i) => String.fromCharCode(32 + i)).join("");
// ★측정 요소는 반드시 문서에 붙인다 — WebKit 은 문서에 안 붙은 캔버스·OffscreenCanvas 에서 사용자 설치 글꼴을
// 못 본다(헤드리스 WebKit 실측: 같은 「13px D2Coding」이 붙은 캔버스 6.5px ↔ 안 붙은 캔버스 7.83px = Menlo).
let measureHost: HTMLElement | null = null;
let measureCtx: CanvasRenderingContext2D | null = null;
function host(): HTMLElement {
  if (!measureHost || !measureHost.isConnected) {
    measureHost = document.createElement("div");
    measureHost.setAttribute("aria-hidden", "true");
    measureHost.style.cssText = "position:absolute;left:-10000px;top:0;visibility:hidden;pointer-events:none;white-space:pre;";
    document.body.appendChild(measureHost);
    measureCtx = null;
  }
  return measureHost;
}
function ctx(): CanvasRenderingContext2D | null {
  if (!measureCtx || !measureHost?.isConnected) {
    const h = host();
    const cv = document.createElement("canvas");
    cv.width = cv.height = 1;
    h.appendChild(cv);
    measureCtx = cv.getContext("2d");
  }
  return measureCtx;
}
const registered = new Map<string, Promise<unknown>>();

// 주 글꼴(스택의 라틴 글꼴)과 한글 대체 글꼴을 캔버스로 재서 Ghostty 배율을 낸다. 못 재면 1.
export function measureHangulFitScale(fontStack: string): number {
  try {
    const c = ctx();
    if (!c) return 1;
    c.font = `100px ${fontStack}`;
    const cellW = c.measureText("W").width / 100;
    const a = c.measureText(ASCII);
    const asciiH = (a.actualBoundingBoxAscent + a.actualBoundingBoxDescent) / 100;
    // 사용자가 고른 글꼴에 한글이 있으면 맞춤을 걸지 않는다 — 「한」 폭이 대체 글꼴 폭과 다르면 주 글꼴 것이다.
    const hanInStack = c.measureText("한").width / 100;
    c.font = `100px ${HANGUL_FALLBACK_STACK}`;
    const ic = c.measureText("水").width / 100;
    const hanFallback = c.measureText("한").width / 100;
    if (Math.abs(hanInStack - hanFallback) > 0.01) return 1;
    return hangulFitScale(cellW, asciiH, ic);
  } catch {
    return 1;
  }
}

// 배율에 맞는 @font-face 를 (한 번만) 등록하고, 터미널에 줄 글꼴 스택을 돌려준다.
// onLoaded = 글꼴이 실제로 올라온 뒤 한 번 — 그 사이에 잰 글자 폭 캐시를 비우라는 신호.
export function termFontStack(baseStack: string, onLoaded?: () => void): string {
  if (typeof document === "undefined" || typeof FontFace === "undefined") return baseStack;
  const scale = measureHangulFitScale(baseStack);
  if (scale === 1) return baseStack;
  const family = hangulFitFamily(scale);
  let loading = registered.get(family);
  if (!loading) {
    const faces = (["normal", "bold"] as const).map((weight) => {
      const src = HANGUL_LOCAL[weight].map((n) => `local('${n}')`).join(", ");
      const f = new FontFace(family, src, {
        weight, unicodeRange: HANGUL_UNICODE_RANGE, sizeAdjust: `${Math.round(scale * 1000) / 10}%`,
      } as FontFaceDescriptors);
      document.fonts.add(f);
      return f.load().catch(() => null);
    });
    loading = Promise.all(faces);
    registered.set(family, loading);
  }
  if (onLoaded) loading.then(onLoaded);
  return withHangulFit(baseStack, family);
}

// xterm 셀 크기 측정을 바로잡는다 — 두 가지를 한 자리에서.
//  ⑴ 측정 글꼴: xterm 5.5 는 OffscreenCanvas 로 「W」를 잰다(TextMetricsMeasureStrategy). WebKit 의
//     OffscreenCanvas 는 **사용자가 설치한 글꼴(JetBrains Mono·D2Coding 등)을 못 보고** Menlo 로 잰다
//     (헤드리스 WebKit 실측: D2Coding 13px = 문서 캔버스 6.5px ↔ OffscreenCanvas 7.83px). 그래서 칸은
//     Menlo 크기(7.83×15)인데 글자는 고른 글꼴로 그려져, D2Coding 은 글자 사이가 벌어지고 JetBrains Mono 는
//     17px 짜리 글자가 15px 줄에 끼인다 — 「글꼴을 바꿔도 장평·자간이 다르다」. 문서 캔버스로 다시 잰다.
//  ⑵ 반올림: 잰 값을 Ghostty Metrics.calc 처럼 장치 화소로 반올림한다(ghosttyCellCss).
// xterm 내부(_core._charSizeService)에 손을 대므로, 모양이 다르면(업그레이드) 아무것도 안 한다.
type CharSizeSvc = { measure(): void; _measureStrategy?: { measure(): { width: number; height: number } } };
type TermLike = { options: { fontFamily?: string; fontSize?: number }; _core?: { _charSizeService?: CharSizeSvc } };

// 칸 크기 측정 — 문서에 붙인 숨김 span 에 「W」 32자(xterm DomMeasureStrategy 와 같은 방식)를 100px 로 그려
// 비례 환산한다. 높이 = span 의 normal 줄 높이 = 글꼴의 ascent+descent+line gap — Ghostty lineHeight 와 같은 정의
// (캔버스 fontBoundingBox 는 line gap 을 빼고 정수로 잘린다). 못 재면 null.
export function measureCellCss(fontFamily: string, fontSize: number): { width: number; height: number } | null {
  try {
    const s = document.createElement("span");
    s.style.cssText = `font-family:${fontFamily};font-size:100px;line-height:normal;font-kerning:none;`;
    s.textContent = "W".repeat(32);
    host().appendChild(s);
    const r = s.getBoundingClientRect();
    s.remove();
    const w = (r.width / 32 / 100) * fontSize;
    const h = (r.height / 100) * fontSize;
    return w > 0 && h > 0 ? { width: w, height: h } : null;
  } catch {
    return null;
  }
}

export function snapCellsToDevicePixels(term: unknown): boolean {
  const t = term as TermLike;
  const svc = t._core?._charSizeService;
  const strat = svc?._measureStrategy;
  if (!svc || !strat || typeof strat.measure !== "function") return false;
  const raw = strat.measure.bind(strat);
  strat.measure = () => {
    const r = measureCellCss(t.options.fontFamily ?? "monospace", t.options.fontSize ?? 13) ?? raw();
    const dpr = window.devicePixelRatio || 1;
    return { width: ghosttyCellCss(r.width, dpr), height: ghosttyCellCss(r.height, dpr) };
  };
  svc.measure();
  return true;
}

// 글자 폭 캐시 비우기 — 맞춤 한글 글꼴이 늦게 올라왔을 때(DOM 렌더러 WidthCache 는 글꼴 설정이
// 바뀔 때만 비워진다). 공개 API 가 없어 RenderService.handleCharSizeChanged(치수 재계산 + 캐시 비움)를 부른다.
export function refreshGlyphWidths(term: unknown): void {
  const t = term as { _core?: { _renderService?: { handleCharSizeChanged?: () => void } }; refresh?: (a: number, b: number) => void; rows?: number };
  t._core?._renderService?.handleCharSizeChanged?.();
  t.refresh?.(0, (t.rows ?? 1) - 1);
}
