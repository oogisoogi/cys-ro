// 전문가 모드 판정 회귀 테스트 (bun test — 신규 의존성 0 · DOM/Tauri 불요).
//
// ★이 파일이 지키는 것은 단 하나다: **기본값이 꺼짐이다.** 그 한 줄이 이 티켓의 본체이고
//   (박사님 판정 2026-09-20 「기본값 = 숨김 확정」), 화면으로는 「안 보인다」로만 나타나서
//   조용히 뒤집혀도 아무도 모른다. 그래서 값 대조로 못박는다.
import { describe, it, expect } from "bun:test";
import { EXPERT_KEY, expertModeOn, expertModeRaw } from "./expertmode";

describe("expertModeOn — 기본값은 꺼짐이다", () => {
  it("★미설정(null·undefined)은 꺼짐 — 새 기기·새 사용자가 만나는 상태", () => {
    expect(expertModeOn(null)).toBe(false);
    expect(expertModeOn(undefined)).toBe(false);
  });

  it('켜짐으로 읽히는 값은 정확히 "1" 하나뿐이다', () => {
    expect(expertModeOn("1")).toBe(true);
  });

  it("★해석 불가·옛 판본 쓰레기 값은 전부 꺼짐으로 접힌다 — 틀릴 때 안전한 쪽으로 틀린다", () => {
    // 「참인 표기」를 늘리면 무엇이 켜짐인지가 읽는 쪽과 쓰는 쪽에서 갈린다. 그 갈림은 화면에만 난다.
    for (const raw of ["", "0", "true", "TRUE", "on", "yes", "y", "2", " 1", "1 ", "null", "undefined", "{}"]) {
      expect(expertModeOn(raw)).toBe(false);
    }
  });

  it("왕복 — 쓴 값을 그대로 읽으면 같은 상태가 나온다(저장 표기와 판정이 한 쌍)", () => {
    expect(expertModeOn(expertModeRaw(true))).toBe(true);
    expect(expertModeOn(expertModeRaw(false))).toBe(false);
  });

  it("키 이름이 고정돼 있다 — 바뀌면 사용자가 켜 둔 설정이 조용히 초기화된다", () => {
    expect(EXPERT_KEY).toBe("cys-expert-mode");
  });
});
