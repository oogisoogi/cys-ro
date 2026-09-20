// drainverify.ts 순수 함수 회귀 테스트 (bun test — 신규 의존성 0).
//
// [F5] drain_verify 폴백 사유 분기: 구버전 미지원과 크래시/하드캡을 구분해 UI가 정직한 문구를 고르게 한다.
// 거동(plain drain 폴백)은 양쪽 동일하고 분류·문구만 다르다.
import { describe, it, expect } from "bun:test";
import { classifyDrainVerifyFallback, drainVerifyFallbackToast, drainVerifyNotice } from "./drainverify";

describe("classifyDrainVerifyFallback — drain_verify 폴백 사유 분기", () => {
  it("구버전 미지원(unsupported 접두) → 'unsupported'", () => {
    expect(
      classifyDrainVerifyFallback("unsupported: cys drain --verify 미지원(구버전 바이너리) (stderr: ...)"),
    ).toBe("unsupported");
  });
  it("크래시/하드캡(verify_failed 접두) → 'verify_failed'", () => {
    expect(
      classifyDrainVerifyFallback("verify_failed: drain --verify 실행 실패(exit=Some(3)...) (stderr: )"),
    ).toBe("verify_failed");
  });
  it("알 수 없는 에러 → null(폴백 아님·상위 rethrow)", () => {
    expect(classifyDrainVerifyFallback("some other tauri error")).toBeNull();
  });
});

describe("drainVerifyFallbackToast — 사유별 정직 문구", () => {
  it("미지원은 '미지원' 문구, '무손실' 표현 없음", () => {
    const t = drainVerifyFallbackToast("unsupported");
    expect(t.title).toContain("미지원");
    expect(t.body).toContain("기존 방식");
    expect(t.body).not.toContain("무손실");
  });
  it("검증 실패는 '실패·점검 권고' 문구, 미지원과 구별", () => {
    const t = drainVerifyFallbackToast("verify_failed");
    expect(t.title).toContain("실패");
    expect(t.body).toContain("점검");
    expect(t.body).not.toContain("무손실");
    // 두 문구가 실제로 다른지(정직성 교정의 핵심)
    expect(t.body).not.toBe(drainVerifyFallbackToast("unsupported").body);
  });
});

describe("drainVerifyNotice — 확인 창 폐기 후의 사후 알림 1줄", () => {
  const node = (role: string, outcome: string) => ({ role, surface: "surface:9", outcome });
  it("전원 마커 확인이면 알림이 없다(조용한 성공)", () => {
    expect(
      drainVerifyNotice({ all_saved: true, total: 3, summary: { saved: 3 }, nodes: [node("master", "saved")] }),
    ).toBeNull();
  });
  it("미확인 자리가 있으면 '대화는 복원했다'를 함께 말한다(묻지 않는다)", () => {
    const n = drainVerifyNotice({
      all_saved: false,
      total: 3,
      summary: { saved: 1 },
      nodes: [node("master", "saved"), node("worker", "timeout"), node("cso", "delivery_failed")],
      max_wait_secs: 40,
    });
    expect(n).not.toBeNull();
    expect(n!.body).toContain("자리 2개");
    expect(n!.body).toContain("복원");
    expect(n!.body).toContain("최대 40초");
    // ★확인 창을 없앴으므로 질문 문구가 남아 있으면 안 된다(회귀 가드).
    expect(n!.body).not.toContain("하시겠습니까");
    expect(n!.title).not.toContain("하시겠습니까");
    // 자리별 사유가 사람 말로 붙는다.
    expect(n!.body).toContain("마커 미확인(시간초과)");
    expect(n!.body).toContain("입력 미제출 실측");
  });
  it("all_saved=false 인데 나열할 노드가 없으면(0노드) 알리지 않는다", () => {
    expect(drainVerifyNotice({ all_saved: false, total: 0, summary: { saved: 0 }, nodes: [] })).toBeNull();
  });
});

// ★[V111-F4] 확인 창 폐기의 **소스 가드** — 순수 함수로는 「모달을 안 띄운다」를 못 잰다(모달은 main.ts
// 흐름에 있다). 그래서 재시작 흐름 함수 본문에 확인 모달 호출이 없다는 것을 직접 단언한다.
// (함수 본문으로 범위를 좁힌다 — 파일 전체 grep 이면 다른 흐름의 정당한 모달에 걸려 공허해진다.)
describe("manualRestartAllDaemons — 저장 미확인 확인 창이 없다", () => {
  it("재시작 흐름 본문에 '일부 노드 저장 미확인' 모달 호출이 없다", async () => {
    const src = await Bun.file(new URL("./main.ts", import.meta.url)).text();
    const i = src.indexOf("async function manualRestartAllDaemons()");
    expect(i).toBeGreaterThan(-1);
    // ★주석을 걷어낸 **선언문만** 본다 — 이 가드가 자기 설명 주석(「"그래도 재시작"에 아니오를…」)에
    //   스스로 걸렸다. 가드는 코드에 묻고 산문에 묻지 않는다.
    const raw = src.slice(i, src.indexOf("\n}\n", i));
    const body = raw
      .split("\n")
      .filter((l) => !l.trim().startsWith("//"))
      .join("\n");
    expect(body).not.toContain("일부 노드 저장 미확인");
    expect(body).not.toContain("그래도 재시작");
    // 대신 사후 알림을 부른다(빼면 사용자는 아무것도 못 듣는다).
    expect(body).toContain("drainVerifyNotice");
    // 첫 진입 확인 모달(버튼 의도 확인)은 범위 밖이라 그대로 있다 — 이 시험이 그것까지 지우지 않는다.
    expect(body.replace(/\s+/g, " ")).toContain('confirmModal( "데몬 재시작"');
  });
});
