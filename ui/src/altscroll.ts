// 대체 화면(alt buffer) 휠 → 키 시퀀스 번역 — 순수 모듈. DOM·xterm·Tauri 0줄.
//
// ★왜 이 파일이 생겼나(D5 · 2026-09-23 Windows 실기 제보 「휠이 아무것도 안 한다」):
// wheelgate.ts (b)·(d) 가 예고한 **과잉 억제**가 실제로 났다. 경로를 실측으로 적는다 —
//  ① Windows 는 trackfilter 가 마우스 DECSET(MOUSE_PARAMS 8종)을 출력에서 전부 스트리핑한다
//     (ConPTY 결함 1호 차단) → xterm 은 트래킹에 **결코 진입하지 않는다**
//     (`term.modes.mouseTrackingMode` 상수 "none") → 휠은 마우스 보고로 나가지 않는다.
//     ∴ 입력측 필터(mousefilter.routeOnData)의 wheel 갈래는 **Windows 에서 도달하지 않는다** —
//     D5 의 수리를 그쪽에 넣으면 죽은 코드가 된다(이 파일이 따로 있는 이유).
//  ② 그 대신 xterm 은 대체 화면(=스크롤백 없음)의 휠을 **방향키로 스스로 합성**한다. 벤더 번들
//     실측(@xterm/xterm 5.5 lib/xterm.js · Terminal 의 "wheel" 리스너):
//       if (customWheelEventHandler && false === customWheelEventHandler(e)) return false;
//       if (!this.buffer.hasScrollback) { const t = viewport.getLinesScrolled(e); if (0===t) return;
//         const i = ESC + (decPrivateModes.applicationCursorKeys ? "O" : "[") + (e.deltaY<0?"A":"B");
//         let s=""; for (let e=0;e<Math.abs(t);e++) s+=i; return coreService.triggerDataEvent(s,true), ... }
//     ★핵심: 커스텀 휠 핸들러가 **먼저** 불리고 false 면 그 합성까지 함께 죽는다.
//  ③ Claude Code fullscreen 은 1003 을 켜므로 장부 판별자가 충족 → shouldSuppressWheelWin=true →
//     우리 핸들러가 false 를 돌려줌 → ②의 합성이 사라짐 → **휠 무동작**. 이것이 D5 다.
//
// ★그래서 무엇을 바꾸나: 억제는 유지하되(xterm 합성은 계속 차단) **우리가 직접 번역해 pty 에 쓴다**.
// 「억제를 그냥 푼다」(핸들러 미등록)와 결과가 같아 보이지만 두 가지가 다르다 —
//   ⓐ 줄 수의 소유권: xterm 합성은 `getLinesScrolled` 를 쓰므로 deltaMode=DOM_DELTA_PAGE 환경에서
//      **노치당 rows(80x24면 24개) 방향키**가 나간다(wheelgate (c) 가 남긴 증폭 위험 — 벤더 코드에
//      `deltaMode===DOM_DELTA_PAGE && (t *= rows)` 실재). 우리 번역은 rows 를 곱하지 않고 이벤트당
//      상한(MAX_LINES_PER_EVENT)을 둔다 = 증폭이 구조적으로 불가능하다.
//   ⓑ 무엇을 보낼지의 선택권: 방향키가 프롬프트 히스토리를 오염시키는 앱이 있으면 같은 자리에서
//      키 종류를 바꿀 수 있다(모드 1키 · 기본 page). 억제를 푸는 길에는 그 손잡이가 없다.
//
// ★번역의 규약적 근거: xterm 의 위 동작은 xterm(1) 의 alternate scroll(`?1007`) 관례다 —
// 대체 화면의 휠을 커서 키로 바꿔 페이저(less·man)가 굴러가게 하는 것. 우리는 그 관례를 그대로
// 재현하되 줄 수만 우리가 정한다. DECCKM(applicationCursorKeys)이 켜져 있으면 CSI 가 아니라 SS3
// (ESC O A/B)를 보내는 것도 벤더와 동일하다 — 다르게 보내면 앱이 키를 못 알아본다.
//
// ★이 모듈이 하지 않는 것(정직 고지): 「앱이 실제로 스크롤됐는가」는 판정하지 않는다. 대체 화면엔
// 우리가 읽을 스크롤백이 없고 앱의 반응은 비동기라, 이 파일은 **무엇을 보낼지**만 정한다.
// 「보냈는데 화면이 안 변했다」의 관측은 아래 힌트 상태기(altHintNext)가 첫 행 지문으로 근사한다.

import { shouldSuppressWheelWin, type WinWheelGateState } from "./wheelgate";

// 휠 한 번의 판정.
//   pass      = 손대지 않는다 → 호출측은 true 를 돌려 xterm 기본 처리로 보낸다.
//               ★무회귀의 정확한 진술: 「**억제 술어가 false 인 모든 경로**에서 xterm 기본 처리가
//               종전 그대로 보존된다」이다(일반 버퍼 로컬 스크롤 · 비-1003 alt 앱의 방향키 합성이
//               그 경로의 예시일 뿐, 보장은 앱 이름이 아니라 술어에 걸려 있다 — 이종 검증 지적 수용).
//   consume   = 억제하되 보낼 것이 없다(가로 휠·delta 0·shift 휠) → 호출측은 false 만 돌린다.
//   translate = 억제하고 data 를 pty 에 쓴다 → 호출측은 sendRaw(data) 후 false.
export type AltWheelAction =
  | { kind: "pass" }
  | { kind: "consume" }
  | { kind: "translate"; data: string; dir: -1 | 1; lines: number };

// page = PgUp/PgDn 번역 = **기본값**. cursor = 커서 키(CUU/CUD) 번역 = 게이트 1키로 전환.
//
// ★기본값이 page 인 근거(로컬 pty 실측 2026-09-23 · Claude Code 2.1.280 · 80x24 pty):
//   · 프롬프트에 글자를 둔 채 `ESC[A` 를 보내면 화면에 **"History 5/5"** 가 뜨고 입력줄이 과거
//     입력으로 **교체된다** = 방향키 번역은 프롬프트 히스토리를 오염시킨다(원 결함 재현).
//   · 같은 상태에서 `ESC[5~`(PgUp)·`ESC OA`(SS3) 는 **무반응**(각각 17·16 바이트, 화면 무변).
//   ⇒ 번역이 실제로 가 닿는 앱군(= 1003 을 켜는 fullscreen 앱 = Claude Code 계열)에서 커서 키는
//     **되돌릴 수 없는 방향의 손해**(조용한 오염)이고 PgUp 은 최악이라도 **지금과 같은 무동작**이다.
//     ∴ 기본값은 「나빠질 수 없는 쪽」으로 둔다 — 브리프의 초안(기본 cursor)에서 바꾼 유일한 항목이고
//     master 가 2026-09-23 채택했다. 뒤집기는 아래 게이트 1키(코드 무수정)다.
//   ⚠**이 안전성 주장의 사정거리(이종 검증 지적 수용 — 일반화하지 마라)**: 위 실측은 **Claude Code
//     2.1.280 inline + 번들 판독**이다. 1003 을 켜는 앱이 곧 Claude Code 인 것은 아니므로, PgUp 을
//     다른 기능에 할당한 앱에서는 page 기본이 무해하지 않을 수 있고 그런 앱에서는 cursor 가 나을 수
//     있다. DECCKM 만으로는 그 의미 차이를 가릴 수 없다 — 그래서 판별을 넓히지 않고 **게이트 1키**로
//     남겼다. 대상 앱·판본을 벗어난 「언제나 안전」 주장은 하지 않는다.
// ★번들 판독으로 보강(2026-09-23 · Claude Code 2.1.280 단일 실행파일 내장 JS · 오프셋 병기):
//   · 키바인딩 표에 `Chat: { up: "history:previous", down: "history:next" }` 가 있고
//     **Scroll 컨텍스트에는 up/down 바인딩이 아예 없다**(@177,028,660) — 방향키로는 transcript 가
//     원리적으로 굴러가지 않는다. 입력창 핸들러는 방향키를 **항상 소비**한다(@185,158,314).
//   · 반대로 pageup/pagedown 은 **fullscreen 일 때만** 입력창이 미처리로 흘려보내
//     (`case "pageup": if (fullscreen || ctrl) return;` @185,160,212) Scroll 컨텍스트의
//     `scroll:pageUp` 이 뷰포트 **½** 을 굴린다(@196,489,302). ⇒ 대체 화면 조건에 묶인 우리
//     번역과 정확히 같은 구간에서만 유효하다(비-fullscreen 에서는 입력창이 줄 시작/끝 이동으로
//     소비 — 위 inline 실측의 "무반응"이 이것이다).
//   · 앱은 심지어 이 오용을 **탐지해 경고**한다: "Scroll wheel is sending arrow keys · use
//     PgUp/PgDn to scroll"(@196,493,995) + 100ms 내 동일 방향키 8개 버스트 텔레메트리(@183,091,950).
//     커서 키 번역은 노치 3회면 그 문턱을 넘는다.
// ★【미측정】: Claude Code 의 **fullscreen(대체 화면)** 실행은 우리 맥에서 만들 수 없었다(settings
//   `tui` 키를 줘도 `?1049h` 미발화 — 롤아웃 게이트). 위 실측은 inline 모드 + 번들 정적 판독이다.
//   fullscreen 에서 PgUp 이 실제로 굴러가는지는 **박사님 Windows 실기가 최종 판정**이다.
// ★더 나은 정공법(이번 티켓 범위 밖 · master 판정): 같은 번들 판독이 앱이 SGR 휠 보고
//   (`ESC[<64;c;rM`)를 스스로 `wheelup`→`scroll:lineUp` 으로 디코드함을 보였다(@183,025,692).
//   즉 Windows 에서 **휠 보고를 앱에 전달**하면 번역 없이 앱이 제 방식(가속 포함)으로 굴린다.
//   막고 있는 것은 우리 쪽 ConPTY 결함 1호(입력 마우스 보고가 깨져 리터럴 타이핑) 대응으로
//   trackfilter 가 DECSET 을 스트리핑하는 것 — 그 재개방은 Windows 실기 계측이 선행 조건이다.
// ★less/man/vim 은 이 번역을 **타지 않는다**(억제 술어가 1003 요구 앱에만 걸려 pass) — 그쪽 휠은
//   종전대로 xterm 이 직접 합성한다. 그래서 「페이저가 PgUp 을 모르면 어쩌나」는 이 경로의 문제가
//   아니다(참고로 less 는 PgUp 도 SS3 방향키도 실측으로 굴러간다).
export type AltScrollMode = "cursor" | "page";

// WheelEvent 에서 이 모듈이 읽는 부분만 추린 구조적 뷰(테스트가 페이크를 만들 수 있게).
// deltaMode 상수는 WheelEvent 공개 계약이다: 0=PIXEL · 1=LINE · 2=PAGE.
export interface WheelDeltaView {
  deltaY: number;
  deltaMode: number;
  shiftKey?: boolean; // xterm 은 shift 휠을 스크롤 0 으로 본다(가로/빠른 스크롤 관용) — 동형 유지
}

export const DOM_DELTA_PIXEL = 0;
export const DOM_DELTA_LINE = 1;
export const DOM_DELTA_PAGE = 2;

// 휠 노치 하나가 굴리는 줄 수 — 통상 터미널 관용치(mousefilter 의 WHEEL_LINES 와 같은 값이지만
// 소비자가 다르다: 저쪽은 로컬 스크롤 줄 수, 이쪽은 pty 로 나가는 키 개수다. 억지로 합치지 마라).
export const LINES_PER_NOTCH = 3;
// 픽셀 모드에서 노치 하나로 치는 |deltaY| — Chromium 계열(WebView2)의 기본 노치값 관례.
export const PIXELS_PER_NOTCH = 100;
// 이벤트당 방향키 상한. ★이 상한이 wheelgate (c) 가 우려한 증폭(노치당 rows 개)을 봉인한다.
// 넘기면: 그 이벤트의 여분 줄은 버려진다(사용자는 한 번 더 굴리면 된다) — 되돌릴 수 있는 방향.
export const MAX_LINES_PER_EVENT = 12;
// page 모드에서 이벤트당 페이지 상한(한 번의 휠로 화면 3장 이상 넘기지 않는다).
export const MAX_PAGES_PER_EVENT = 3;

function clamp(n: number, lo: number, hi: number): number {
  return n < lo ? lo : n > hi ? hi : n;
}

/** 이 이벤트가 요구하는 줄 수(부호 포함 실수). 0 = 보낼 것 없음. rows 는 곱하지 않는다(위 ⓐ). */
export function altWheelRawLines(w: WheelDeltaView): number {
  if (!w.deltaY || w.shiftKey) return 0; // deltaY 0·NaN·shift = xterm 과 동형으로 스크롤 없음
  if (w.deltaMode === DOM_DELTA_LINE) return w.deltaY;
  if (w.deltaMode === DOM_DELTA_PAGE) return w.deltaY * LINES_PER_NOTCH;
  return (w.deltaY / PIXELS_PER_NOTCH) * LINES_PER_NOTCH; // PIXEL(기본) 및 미지 모드
}

// 이벤트 사이에 남는 소수 줄을 이고 가는 누산기 — **트랙패드 대응의 핵심**.
// ★왜 필요한가(이종 검증 REVISE 2026-09-23 · 치명 등급 지적을 수용): 초판은 이벤트당
// `clamp(lines, 1, …)` 로 **모든 미세 델타를 최소 1줄로 올림**했다. 트랙패드 한 번 튕김은 수십
// 이벤트라, 기본 모드(PgUp = 반 페이지)에서 수십 번의 반 페이지 점프가 pty 로 나갔을 것이다.
// 벤더 xterm 도 같은 자리에서 누산기(`_wheelPartialScroll`)를 쓴다 — 우리만 안 쓰면 트랙패드에서
// 우리 경로가 벤더보다 거칠어진다. ∴ 한 줄을 채울 때까지 모으고 나머지는 이월한다.
// 방향이 바뀌면 이월분은 버린다(반대 방향 잔여가 다음 스크롤을 앞당기면 손이 미끄러진 느낌이 난다).
export interface WheelAccum {
  carry: number; // 아직 방출하지 않은 줄(부호 포함)
}
export const WHEEL_ACCUM_INITIAL: WheelAccum = { carry: 0 };

/** 누산 한 걸음. lines 는 방향을 뺀 절댓값이고 dir 은 방출이 있을 때만 유효하다. */
export function altWheelStep(
  prev: WheelAccum,
  w: WheelDeltaView,
): { next: WheelAccum; dir: -1 | 1; lines: number } {
  const raw = altWheelRawLines(w);
  if (!raw || !Number.isFinite(raw)) {
    // 유한하지 않은 델타(Infinity·NaN)는 누산에 섞으면 누산기를 영구 오염시킨다 — 그 이벤트만 버린다.
    return { next: prev, dir: 1, lines: 0 };
  }
  const sameDir = prev.carry === 0 || prev.carry > 0 === raw > 0;
  const acc = (sameDir ? prev.carry : 0) + raw;
  const dir: -1 | 1 = acc < 0 ? -1 : 1;
  const whole = Math.min(Math.floor(Math.abs(acc)), MAX_LINES_PER_EVENT);
  return { next: { carry: acc - dir * whole }, dir, lines: whole };
}

/**
 * 보낼 바이트열. 커서 키는 DECCKM 에 따라 CSI/SS3 를 가른다(벤더와 동형 — 다르면 앱이 못 읽는다).
 * @param dir -1 = 위 · 1 = 아래
 * @param lines altWheelLines 결과(≥1)
 */
export function altWheelSequence(
  dir: -1 | 1,
  lines: number,
  mode: AltScrollMode,
  applicationCursorKeys: boolean,
): string {
  if (lines <= 0) return "";
  if (mode === "page") {
    const pages = clamp(Math.round(lines / LINES_PER_NOTCH), 1, MAX_PAGES_PER_EVENT);
    return (dir < 0 ? "\x1b[5~" : "\x1b[6~").repeat(pages);
  }
  const one = "\x1b" + (applicationCursorKeys ? "O" : "[") + (dir < 0 ? "A" : "B");
  return one.repeat(lines);
}

/**
 * 휠 한 번의 최종 판정. **억제 술어는 여기서 부른다** — 호출측(main.ts)이 술어와 번역을 따로
 * 조립하면 둘이 어긋나는 오배선(억제는 하는데 번역은 안 하는 상태 = D5 그대로)이 다시 가능해진다.
 * 술어 자체(shouldSuppressWheelWin)는 한 줄도 고치지 않았다 — wheelgate.test.ts 의 16조합
 * 진리표가 그대로 감시선으로 남는다.
 */
export function altWheelAction(
  s: WinWheelGateState,
  accum: WheelAccum,
  w: WheelDeltaView,
  opts: { mode: AltScrollMode; applicationCursorKeys: boolean },
): { action: AltWheelAction; next: WheelAccum } {
  // ★억제되지 않는 경로에서는 누산기를 **건드리지 않는다**: 그 휠은 xterm 이 제 누산기로 처리하므로
  // 우리가 함께 세면 두 번 세는 셈이고, 나중에 억제 구간에 들어갔을 때 묵은 잔여가 튄다.
  if (!shouldSuppressWheelWin(s)) return { action: { kind: "pass" }, next: accum };
  const { next, dir, lines } = altWheelStep(accum, w);
  if (lines <= 0) return { action: { kind: "consume" }, next };
  const data = altWheelSequence(dir, lines, opts.mode, opts.applicationCursorKeys);
  if (!data) return { action: { kind: "consume" }, next };
  return { action: { kind: "translate", data, dir, lines }, next };
}

// ─────────────────────────────────────────────────────────────────────────────
// 「더 위는 Ctrl+O」 안내 — 대체 화면판 (B1 ② 의 확장).
//
// scrollfollow.shouldShowFoldHint 는 `viewportY <= 0`(스크롤백 맨 위)으로 판정한다. 대체 화면엔
// 스크롤백이 없어 viewportY 가 늘 0 이므로 그 술어를 그대로 쓰면 **첫 휠에 바로** 뜬다(오발).
// 그래서 축을 바꾼다: 「위로 휠을 연속으로 주는데 화면 첫 행이 그대로다」 = 더 굴러갈 데가 없다.
//
// ★화면 무변화의 근사(정직 고지): 지문은 **이번 휠 시점**의 첫 행이므로, 직전 휠이 보낸 키의
// 결과를 본다(앱 렌더는 비동기라 같은 틱에 못 읽는다). 즉 한 이벤트만큼 늦다 — 그래서 문턱을
// 1 이 아니라 ALT_HINT_UP_STREAK 로 둔다. 첫 행이 시계·스피너처럼 매 프레임 바뀌는 앱에서는
// 지문이 늘 달라 안내가 **뜨지 않는다**(오발보다 미발을 택한 방향 — 안내는 보조 수단이다).
export interface AltHintState {
  streak: number; // 「위로 + 첫 행 무변화」 연속 횟수
  fp: string; // 직전에 본 첫 행 지문
  t: number; // 그 지문을 본 시각(ms)
}
export const ALT_HINT_INITIAL: AltHintState = { streak: 0, fp: "", t: 0 };
export const ALT_HINT_UP_STREAK = 3;
// 연속으로 세기 전에 앱이 그릴 시간을 준다. ★이 간격이 없으면 트랙패드 한 번 튕김(수십 이벤트)에서
// 세 이벤트가 전부 **갱신 전 같은 지문**을 보고 문턱을 넘어, 문서 한가운데서 안내가 뜬다
// (이종 검증 2026-09-23 높음 등급 지적 — 수용). 간격보다 빨리 온 이벤트는 지문만 갱신하고 세지 않는다.
export const ALT_HINT_MIN_GAP_MS = 250;

/** 휠 한 번 뒤의 힌트 상태. dir/fp/now 는 이번 이벤트 시점 값. */
export function altHintNext(prev: AltHintState, dir: -1 | 1, fp: string, now: number): AltHintState {
  if (dir > 0) return { streak: 0, fp, t: now }; // 아래로 = 위 끝 탐색이 아니다 — 리셋
  if (now - prev.t < ALT_HINT_MIN_GAP_MS) return { ...prev, fp }; // 너무 빠르다 = 아직 못 그렸다
  const same = prev.fp === fp && prev.streak > 0; // 첫 비교(streak 0)는 비교 대상이 없다
  return { streak: same ? prev.streak + 1 : 1, fp, t: now };
}

/** 지금 안내를 띄울까. 앱 세션당 1회는 호출측(foldHintShown)이 지킨다. */
export function shouldShowAltFoldHint(alreadyShown: boolean, st: AltHintState): boolean {
  return !alreadyShown && st.streak >= ALT_HINT_UP_STREAK;
}
