// altscroll.ts — 대체 화면 휠 번역(D5) 회귀 테스트.
//
// 이 파일이 고정하는 계약 넷:
//  ① 번역이 **일어난다**(억제 술어 충족 시 translate) — D5 의 본체. 이것이 죽으면 휠 무동작 복귀.
//  ② 번역이 **일어나지 않는다**(술어 불충족 시 pass) — less/vim·일반 버퍼의 종전 UX 무회귀.
//  ③ 줄 수의 상한이 우리 것이다(deltaMode=PAGE 에서도 rows 를 곱하지 않는다) — 증폭 봉인.
//  ④ 안내(Ctrl+O)는 「위로 연속 + 첫 행 무변화」에서만 1회 — 대체 화면엔 viewportY 축이 없다.
// 마지막 describe 는 **호출부 계수**다: 순수 함수가 옳아도 main.ts 가 부르지 않으면 D5 는 그대로다
// (수리 모듈을 호출부에서 세는 이 저장소 관례 — scrollfollow.test.ts 와 동형).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import {
  altWheelLines,
  altWheelSequence,
  altWheelAction,
  altHintNext,
  shouldShowAltFoldHint,
  ALT_HINT_INITIAL,
  ALT_HINT_UP_STREAK,
  DOM_DELTA_PIXEL,
  DOM_DELTA_LINE,
  DOM_DELTA_PAGE,
  LINES_PER_NOTCH,
  MAX_LINES_PER_EVENT,
  PIXELS_PER_NOTCH,
} from "./altscroll";
import type { WinWheelGateState } from "./wheelgate";

// 억제가 걸리는 상태 = Claude Code fullscreen on Windows(장부에 1003 · xterm 트래킹 미진입).
const suppressed: WinWheelGateState = {
  altActive: true,
  ledgerWantsAnyMotion: true,
  xtermTracking: false,
  allowAppMouse: false,
};
const optsCursor = { mode: "cursor" as const, applicationCursorKeys: false };
const opts = { mode: "page" as const, applicationCursorKeys: false }; // 기본 모드
const notch = { deltaY: PIXELS_PER_NOTCH, deltaMode: DOM_DELTA_PIXEL };

describe("줄 수 산정(③ 증폭 봉인)", () => {
  it("픽셀 모드 한 노치 = LINES_PER_NOTCH 줄", () => {
    expect(altWheelLines({ deltaY: PIXELS_PER_NOTCH, deltaMode: DOM_DELTA_PIXEL })).toBe(LINES_PER_NOTCH);
    expect(altWheelLines({ deltaY: -PIXELS_PER_NOTCH, deltaMode: DOM_DELTA_PIXEL })).toBe(LINES_PER_NOTCH);
  });
  it("트랙패드의 소량 델타도 최소 1줄(무동작으로 떨어지지 않는다)", () => {
    expect(altWheelLines({ deltaY: -4, deltaMode: DOM_DELTA_PIXEL })).toBe(1);
  });
  it("줄 모드는 deltaY 가 곧 줄 수", () => {
    expect(altWheelLines({ deltaY: -3, deltaMode: DOM_DELTA_LINE })).toBe(3);
  });
  it("★PAGE 모드도 rows 를 곱하지 않는다 — 노치당 LINES_PER_NOTCH", () => {
    // 벤더 xterm 은 이 자리에서 rows(80x24면 24)를 곱해 방향키 24개를 내보낸다(wheelgate (c)).
    expect(altWheelLines({ deltaY: -1, deltaMode: DOM_DELTA_PAGE })).toBe(LINES_PER_NOTCH);
  });
  it("이벤트당 상한을 넘기지 않는다", () => {
    expect(altWheelLines({ deltaY: -100000, deltaMode: DOM_DELTA_PIXEL })).toBe(MAX_LINES_PER_EVENT);
    expect(altWheelLines({ deltaY: -999, deltaMode: DOM_DELTA_LINE })).toBe(MAX_LINES_PER_EVENT);
    expect(altWheelLines({ deltaY: -50, deltaMode: DOM_DELTA_PAGE })).toBe(MAX_LINES_PER_EVENT);
  });
  it("세로 델타가 없거나 shift 휠이면 0(보낼 것 없음)", () => {
    expect(altWheelLines({ deltaY: 0, deltaMode: DOM_DELTA_PIXEL })).toBe(0);
    expect(altWheelLines({ deltaY: -100, deltaMode: DOM_DELTA_PIXEL, shiftKey: true })).toBe(0);
  });
});

describe("시퀀스 조립", () => {
  it("위 = CSI A · 아래 = CSI B · 줄 수만큼 반복", () => {
    expect(altWheelSequence(-1, 3, "cursor", false)).toBe("\x1b[A\x1b[A\x1b[A");
    expect(altWheelSequence(1, 2, "cursor", false)).toBe("\x1b[B\x1b[B");
  });
  it("DECCKM(applicationCursorKeys)이면 SS3 — 벤더 xterm 과 동형", () => {
    expect(altWheelSequence(-1, 1, "cursor", true)).toBe("\x1bOA");
    expect(altWheelSequence(1, 1, "cursor", true)).toBe("\x1bOB");
  });
  it("폴백(page) = PgUp/PgDn · 한 노치 1페이지", () => {
    expect(altWheelSequence(-1, LINES_PER_NOTCH, "page", false)).toBe("\x1b[5~");
    expect(altWheelSequence(1, LINES_PER_NOTCH, "page", false)).toBe("\x1b[6~");
  });
  it("폴백도 이벤트당 페이지 상한이 있다", () => {
    expect(altWheelSequence(-1, MAX_LINES_PER_EVENT, "page", false)).toBe("\x1b[5~".repeat(3));
  });
  it("줄 수 0 이면 빈 문자열(호출측이 아무것도 안 보낸다)", () => {
    expect(altWheelSequence(-1, 0, "cursor", false)).toBe("");
  });
});

describe("판정(① 번역 · ② 무회귀)", () => {
  it("억제 충족(claude fullscreen on win) = 번역 · 기본 모드는 PgUp/PgDn", () => {
    const a = altWheelAction(suppressed, { deltaY: -PIXELS_PER_NOTCH, deltaMode: DOM_DELTA_PIXEL }, opts);
    expect(a.kind).toBe("translate");
    if (a.kind === "translate") {
      expect(a.data).toBe("\x1b[5~");
      expect(a.dir).toBe(-1);
      expect(a.lines).toBe(3);
    }
  });
  it("아래로 휠도 번역된다", () => {
    const a = altWheelAction(suppressed, notch, opts);
    expect(a.kind === "translate" && a.data).toBe("\x1b[6~");
  });
  it("전환 1키(cursor)에서는 커서 키가 나간다", () => {
    const a = altWheelAction(suppressed, { deltaY: -PIXELS_PER_NOTCH, deltaMode: DOM_DELTA_PIXEL }, optsCursor);
    expect(a.kind === "translate" && a.data).toBe("\x1b[A\x1b[A\x1b[A");
  });
  it("★일반 버퍼(alt 아님) = pass — 로컬 스크롤 종전 동작", () => {
    expect(altWheelAction({ ...suppressed, altActive: false }, notch, opts).kind).toBe("pass");
  });
  it("★less/man(장부 트래킹 무요청) = pass — xterm 방향키 합성 보존", () => {
    expect(altWheelAction({ ...suppressed, ledgerWantsAnyMotion: false }, notch, opts).kind).toBe("pass");
  });
  it("★vim 등 xterm 트래킹 진입 완료 = pass — 보고 경로 보존", () => {
    expect(altWheelAction({ ...suppressed, xtermTracking: true }, notch, opts).kind).toBe("pass");
  });
  it("★킬스위치(allowAppMouse) = pass — 앱이 마우스를 갖는다", () => {
    expect(altWheelAction({ ...suppressed, allowAppMouse: true }, notch, opts).kind).toBe("pass");
  });
  it("가로·shift 휠은 억제하되 보내지 않는다(consume)", () => {
    expect(altWheelAction(suppressed, { deltaY: 0, deltaMode: DOM_DELTA_PIXEL }, opts).kind).toBe("consume");
    expect(
      altWheelAction(suppressed, { deltaY: -100, deltaMode: DOM_DELTA_PIXEL, shiftKey: true }, opts).kind,
    ).toBe("consume");
  });
});

describe("대체 화면 안내(④)", () => {
  const fp = "＞ 프롬프트";
  it("위로 연속 + 첫 행 무변화가 문턱에 닿으면 1회", () => {
    let st = ALT_HINT_INITIAL;
    for (let i = 0; i < ALT_HINT_UP_STREAK; i++) st = altHintNext(st, -1, fp);
    expect(shouldShowAltFoldHint(false, st)).toBe(true);
    expect(shouldShowAltFoldHint(true, st)).toBe(false); // 이미 띄웠으면 안 띄운다
  });
  it("첫 행이 바뀌면(=앱이 실제로 굴러간다) 연속이 끊겨 안 뜬다", () => {
    let st = ALT_HINT_INITIAL;
    st = altHintNext(st, -1, "a");
    st = altHintNext(st, -1, "b");
    st = altHintNext(st, -1, "c");
    expect(shouldShowAltFoldHint(false, st)).toBe(false);
  });
  it("아래로 휠이 섞이면 연속이 리셋된다", () => {
    let st = ALT_HINT_INITIAL;
    st = altHintNext(st, -1, fp);
    st = altHintNext(st, -1, fp);
    st = altHintNext(st, 1, fp);
    st = altHintNext(st, -1, fp);
    expect(shouldShowAltFoldHint(false, st)).toBe(false);
  });
  it("첫 휠 한 번으로는 뜨지 않는다(스크롤백 판정과 달리 즉발 금지)", () => {
    expect(shouldShowAltFoldHint(false, altHintNext(ALT_HINT_INITIAL, -1, fp))).toBe(false);
  });
});

describe("배선(호출부 계수) — 번역이 실제 휠 경로에서 불린다", () => {
  const src = readFileSync(new URL("./main.ts", import.meta.url), "utf-8");
  it("win 휠 핸들러가 altWheelAction 판정을 쓰고 translate 를 pty 로 보낸다", () => {
    const i = src.indexOf('} else if (wheelKind === "win") {');
    expect(i).toBeGreaterThan(0);
    const win = src.slice(i, src.indexOf("const un1 = await listen", i));
    expect(win.includes("altWheelAction(")).toBe(true);
    expect(win.includes("winGateInputs(term, trackFilter, allowAppMouse)")).toBe(true);
    expect(win.includes("sendRaw(act.data)")).toBe(true);
    // pass 는 반드시 true(=xterm 기본 처리)로 돌아가야 한다 — false 면 less/vim 휠이 죽는다.
    expect(win.includes('if (act.kind === "pass") return true;')).toBe(true);
    // 종전의 '억제만' 배선(번역 없이 술어 결과만 반환)이 남아 있지 않다.
    expect(src.includes("() => !shouldSuppressWheelWin(")).toBe(false);
    // DECCKM 을 읽어야 SS3/CSI 를 옳게 가른다(안 읽으면 앱이 키를 못 알아보는 경로가 생긴다).
    expect(win.includes("applicationCursorKeys: term.modes.applicationCursorKeysMode")).toBe(true);
  });
  it("전환 1키가 게이트 2경로(localStorage ∪ env/파일)로 읽히고 **기본값이 page** 다", () => {
    expect(src.includes('localStorage.getItem("cysAltScrollCursor") === "1"')).toBe(true);
    expect(src.includes('invoke("alt_scroll_cursor_mode")')).toBe(true);
    // ★기본값 축(실측 근거 = 커서 키가 Claude Code 프롬프트 히스토리를 오염시킨다). 이 단언이
    // 빨개지면 기본이 조용히 뒤집힌 것이다 — 근거 없이 되돌리지 마라(altscroll.ts AltScrollMode).
    expect(src.includes('lsAltScrollCursor || beAltScrollCursor === true ? "cursor" : "page"')).toBe(true);
  });
  it("안내 확장이 휠 경로에 배선돼 있다(대체 화면판)", () => {
    const i = src.indexOf('} else if (wheelKind === "win") {');
    const win = src.slice(i, src.indexOf("const un1 = await listen", i));
    expect(win.includes("altHint = altHintNext(altHint,")).toBe(true);
    expect(win.includes("shouldShowAltFoldHint(foldHintShown, altHint)")).toBe(true);
  });
});
