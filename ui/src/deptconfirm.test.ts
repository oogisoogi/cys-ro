// 부서 생성 확인 문안 회귀 테스트 (bun test — 신규 의존성 0).
//
// ★재는 것은 「확인 창이 뜬다」가 아니라 **「무엇이 바뀌는지 세 축이 실제로 적혀 있다」**이다
//   (박사님 판정 2026-09-20 ⓒ = 3줄 · 데몬 1 추가 · 좌석 3 · 본부 지침 교체).
//   문안은 사람이 고치는 물건이라 한 축이 빠져도 나머지 두 줄이 그럴듯해서 눈으로는 안 잡힌다.
import { describe, it, expect } from "bun:test";
import { deptCreateConfirm } from "./deptconfirm";

describe("deptCreateConfirm — 무엇이 바뀌는지 3줄", () => {
  const c = deptCreateConfirm();
  const lines = c.body.split("\n");

  it("본문이 정확히 3줄이다", () => {
    expect(lines.length).toBe(3);
    for (const l of lines) expect(l.trim().length).toBeGreaterThan(0); // 빈 줄로 수만 맞추는 것 금지
  });

  it("★① 데몬 1개가 더 켜진다는 사실이 적혀 있다 (cys-dept:1263)", () => {
    expect(c.body).toContain("데몬");
  });

  it("★② 좌석 3개가 만들어진다는 사실이 **수와 함께** 적혀 있다 (cys-dept:1300 · 상비편성 3좌석)", () => {
    // 「자리가 만들어집니다」만으로는 규모를 모른다 — 이 티켓이 요구한 것은 수다.
    expect(/3/.test(c.body)).toBe(true);
    expect(c.body).toContain("자리");
  });

  it("★③ 본부 지침 파일이 교체된다는 사실이 **파일 이름과 함께** 적혀 있다 (cys-dept:1270 → :918)", () => {
    // B22 의 실제 피해가 이것이다. 나중에 경보를 본 사람이 같은 이름을 찾을 수 있어야 한다.
    expect(c.body).toContain("MASTER_DIRECTIVE.md");
    expect(c.body).toContain("교체");
  });

  it("★③ 되돌아가는 조건이 함께 적혀 있다 — 조건 없는 경고는 비가역으로 읽힌다 (cys-dept:1508 → :1002)", () => {
    expect(c.body).toContain("되돌아갑니다");
  });

  it("★단추 글자 — 취소가 있고, 진행 단추는 기본값('확인')이 아니라 무엇을 하는지 말한다", () => {
    expect(c.no).toBe("취소");
    expect(c.yes).not.toBe("확인");
    expect(c.yes).toContain("부서");
  });

  it("제목이 물음이다 — 알림이 아니라 결정을 요구하는 창이라는 것이 첫 줄에서 보여야 한다", () => {
    expect(c.title.endsWith("?")).toBe(true);
  });
});
