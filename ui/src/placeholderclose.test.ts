import { describe, it, expect } from "bun:test";
import { shouldClosePlaceholder, PLACEHOLDER_MAX_LINES, type PlaceholderDecision } from "./placeholderclose";

/** 닫아도 되는 기준 상태 — 각 시험은 여기서 한 축만 틀어 그 축이 실제로 판정을 쥐는지 본다. */
const OK: PlaceholderDecision = {
  isOwnPlaceholder: true,
  touched: false,
  role: null,
  lineCount: 1,
  formationArrived: true,
  exited: false,
};

describe("shouldClosePlaceholder — 기준 상태", () => {
  it("네 조건이 다 맞으면 닫는다", () => expect(shouldClosePlaceholder(OK)).toBe(true));
});

describe("ⓐ UI 가 만든 번호만 대상이다 — 남의 페인 절대 불가침", () => {
  it("★내가 만든 자리표가 아니면 다른 축이 전부 맞아도 안 닫는다", () => {
    expect(shouldClosePlaceholder({ ...OK, isOwnPlaceholder: false })).toBe(false);
  });
  it("★남의 맨 셸(역할 없음·무접촉·짧은 화면)은 자리표와 구별이 안 되지만 번호로 갈린다", () => {
    // 박사님이 직접 연 터미널이 정확히 이 모양이다 — 번호 기억이 유일한 구분자다.
    const stranger = { ...OK, isOwnPlaceholder: false, lineCount: 1, touched: false };
    expect(shouldClosePlaceholder(stranger)).toBe(false);
  });
});

describe("ⓑ 무접촉일 때만 닫는다", () => {
  it("★키 입력이 한 번이라도 있었으면 안 닫는다", () => {
    expect(shouldClosePlaceholder({ ...OK, touched: true })).toBe(false);
  });
  it("★프롬프트 밖 출력이 있으면 안 닫는다(상한 초과)", () => {
    expect(shouldClosePlaceholder({ ...OK, lineCount: PLACEHOLDER_MAX_LINES + 1 })).toBe(false);
  });
  it("상한 경계(정확히 상한)는 닫는다", () => {
    expect(shouldClosePlaceholder({ ...OK, lineCount: PLACEHOLDER_MAX_LINES })).toBe(true);
  });
  it("★화면 줄 수를 모르면(null) 닫지 않는다 — 모르는 것을 무접촉으로 접지 않는다", () => {
    expect(shouldClosePlaceholder({ ...OK, lineCount: null })).toBe(false);
  });
  it("★편성이 아직 안 붙었으면 닫지 않는다 — 그 자리가 그 탭의 유일한 화면이다", () => {
    expect(shouldClosePlaceholder({ ...OK, formationArrived: false })).toBe(false);
  });
});

describe("ⓒ 자리표가 아니게 된 자리는 건드리지 않는다", () => {
  it("역할이 붙었으면(입양·승계) 안 닫는다", () => {
    expect(shouldClosePlaceholder({ ...OK, role: "master" })).toBe(false);
    expect(shouldClosePlaceholder({ ...OK, role: "worker-2" })).toBe(false);
  });
  it("이미 죽은 자리는 이 경로가 가져가지 않는다", () => {
    expect(shouldClosePlaceholder({ ...OK, exited: true })).toBe(false);
  });
});

describe("모르면 닫지 않는다 — 각 축을 하나씩 틀어 전수로 확인", () => {
  it("★기준 상태에서 한 축만 나쁘게 바꾸면 전부 false 가 된다(어느 축도 장식이 아니다)", () => {
    const worse: Partial<PlaceholderDecision>[] = [
      { isOwnPlaceholder: false },
      { touched: true },
      { role: "cso" },
      { lineCount: null },
      { lineCount: PLACEHOLDER_MAX_LINES + 1 },
      { formationArrived: false },
      { exited: true },
    ];
    for (const w of worse) {
      expect(shouldClosePlaceholder({ ...OK, ...w })).toBe(false);
    }
    // 그리고 그 축들을 되돌리면 다시 true — 시험이 항상 false 를 내는 것이 아님을 못박는다.
    expect(shouldClosePlaceholder(OK)).toBe(true);
  });
});
