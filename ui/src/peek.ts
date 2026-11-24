// (TICKET=cysr-1119-s12 · DESIGN §4-3 CV-PEEK 고침판) 대화 화면 「워커 창 보기」 — 순수 판정(문서·창·저장소·Tauri 0).
//
// 보기 칸은 **읽기 전용**이다(K-2): 좌석으로 가는 글은 화면 쪽 배출구(main.ts sendRaw · injectRawToPane)에서 막고, 글자 크기·PTY 크기는
// 바꾸지 않는다(K-3): CSS 배율(transform: scale(k))만. 아직 안 잰 가정(P0-PEEK-a·b·c)의 갈래는 아래 상수 하나씩으로 바꾼다.

/** 되돌리기(빌드) — false 면 rail 카드 누름 처리기가 붙지 않는다(보기 칸 0 · 1.1.18 꼴). */
export const PEEK_ENABLED = true;
/** P0-PEEK-a 갈래 — WKWebView·WebView2 에서 배율 아래 글자 번짐이 크면 false: 배율 0 + 칸 안 가로 스크롤만(좌석 열 수 그대로). */
export const PEEK_SCALE = true;
/** P0-PEEK-b 갈래 — 런타임 없는 좌석을 볼 때 미룬 동안의 기록을 이어 붙이는가. false = 지금 화면 스냅숏만(1.1.18 안내 줄 「이전 출력 일부를…」).
 *  ★설계 문장은 「재생 줄 수 상한(rows 배수) 낮춤」 이었으나 history_rows 는 받는 xterm 행 수라 상한이 아니다(HANDOFF §0 어긋남 1 · master#195ffa9f). */
export const PEEK_HISTORY_REPLAY = true;
/** P0-PEEK-c 갈래 — 보기 칸 동안 터미널 자동 응답(장치 속성·커서 위치·포커스 보고)을 좌석에 보내는가. 기본 false = 전부 버림.
 *  true 면 아래 정확 꼴 허용 목록만 지나간다(사람 키는 키 처리기 return false + disableStdin 으로 애초에 만들어지지 않는다 · 이중). */
export const PEEK_AUTOREPLY_PASS = false;
/** 배율 아래 글자가 이보다 작아지지 않게 — 더 줄여야 하면 배율을 여기서 멈추고 칸 안 가로 스크롤. */
export const PEEK_MIN_FONT_PX = 11;
/** 창 폭이 이보다 크면 오른쪽 칸 · 이하면 대화 칸 위 덮개(대화 칸을 좁히지 않음 · C-05) — 값 = views.css `@media (min-width: 1411px)`·`(max-width: 1410px)` 와 같다(시험이 맞춘다). */
export const PEEK_WIDE_MIN_PX = 1410; // (master#048a4917) 1300 → 1410 — 1301~1410 창에서 대화 칸이 600px 아래(rail 320 + 보기 칸 바닥 480)였다 · 이제 모든 폭 ≥ 600
/** 배율을 못 건 프레임(폭 0·NaN) 뒤 다시 재는 횟수 상한. */
export const PEEK_MEASURE_TRIES = 2;

/** 자동 응답 정확 꼴(P0-PEEK-c 갈래 · 설계 §4-3 ⑥ + 검증 M6 = xterm 이 스스로 내는 응답 전수) — 그 밖(방향키·PageUp/Down·마우스·사람 키 …) = 목록 밖. */
export const PEEK_AUTOREPLY_PATTERNS: readonly RegExp[] = [
  /^\x1b\[[?>][0-9;]*c$/, // 장치 속성(DA1·DA2)
  /^\x1b\[\??[0-9]+;[0-9]+R$/, // 커서 위치(CPR · 확장 DECXCPR `?`)
  /^\x1b\[[IO]$/, // 포커스 보고
  /^\x1b\[0n$/, // 상태 보고(DSR 5 응답) — 검증 M6: xterm 5.5.0 이 스스로 내는 응답 전수(triggerDataEvent 호출 grep)
  /^\x1b\[\??[0-9]+;[0-9]+\$y$/, // 모드 질의 응답(DECRPM)
  /^\x1b\][0-9]+(;[0-9]+)?;rgb:[0-9a-fA-F]{1,4}\/[0-9a-fA-F]{1,4}\/[0-9a-fA-F]{1,4}(\x1b\\|\x07)$/, // 색 질의 응답(OSC 4·10·11·12)
  /^\x1b\[[468];[0-9]+;[0-9]+t$/, // 창·칸 크기 보고(XTWINOPS 14·16·18 응답)
  /^\x1bP[01]\$r[^\x1b]*\x1b\\$/, // 설정 질의 응답(DECRQSS · 검증 고침2 ⑤)
];

export function isAutoReply(data: string): boolean {
  return PEEK_AUTOREPLY_PATTERNS.some((re) => re.test(data));
}

/** 보기 칸 동안 이 글을 좌석에 보내는가. 보기 칸이 아니면 언제나 보낸다(종전 그대로). */
export function peekPasses(peek: boolean, data: string, passAutoReply: boolean = PEEK_AUTOREPLY_PASS): boolean {
  if (!peek) return true;
  return passAutoReply && isAutoReply(data);
}

export interface PeekScale {
  /** 배율(0 < k ≤ 1) */
  k: number;
  /** 칸 안 가로 스크롤이 필요한가(배율을 바닥에서 멈췄거나 · 배율을 못 걸었거나 · 배율 끔) */
  scroll: boolean;
  /** 재기가 정상이었는가 — false 면 다음 프레임에 한 번 더 잰다(PEEK_MEASURE_TRIES 까지) */
  ok: boolean;
}

const pos = (v: number): boolean => typeof v === "number" && Number.isFinite(v) && v > 0;

/** k = min(1, 칸 안쪽 폭 / termHost 폭) · 글자가 PEEK_MIN_FONT_PX 아래면 그 바닥에서 멈춤 · 재기가 0·NaN·∞ 면 k = 1(배율 0) + 가로 스크롤. */
export function peekScale(innerW: number, hostW: number, fontSize: number, enabled: boolean = PEEK_SCALE): PeekScale {
  if (!pos(innerW) || !pos(hostW)) return { k: 1, scroll: true, ok: false };
  if (!enabled) return { k: 1, scroll: hostW > innerW, ok: true };
  let k = Math.min(1, innerW / hostW);
  if (pos(fontSize) && fontSize * k < PEEK_MIN_FONT_PX) k = Math.min(1, PEEK_MIN_FONT_PX / fontSize);
  if (!pos(k)) return { k: 1, scroll: true, ok: false };
  return { k, scroll: hostW * k > innerW + 0.5, ok: true };
}

/** 닫는 까닭(closePeek 한 함수 · C-04) — 시험·진단이 센다. */
export type PeekCloseReason = "esc" | "button" | "leave" | "detach" | "destroy" | "gen" | "big" | "tick" | "reopen" | "gone";
/** 막은 길(notePeekDrop) — 시험·진단이 센다. */
export type PeekDropKind = "send" | "inject" | "key" | "focus" | "shortcut" | "drop";
