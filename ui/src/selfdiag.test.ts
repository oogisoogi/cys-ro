// selfdiag.ts CEO 팔레트 노출 게이트 회귀 테스트 (스펙 D4 · 결정 D4 — 상호 배타·pending 우선 고정).
//
// 파일 실측(.pre-ceo·md·CEO_TEMPLATE 비교)은 Rust 쪽 순수 핀(src-tauri ceo_drift_verdict_gate_matrix)이
// 담당하고, 여기는 그 bool 신호 2개 → 팔레트 항목 결정의 계약만 고정한다.
import { describe, it, expect } from "bun:test";
import { ceoPaletteEntries, ceoPromoteFailToast, CEO_PROMOTE_HELD_TAG } from "./selfdiag";
import { readFileSync } from "node:fs";

describe("CEO 팔레트 항목 결정 — 상호 배타 매트릭스", () => {
  it("드리프트만 참 → '재실행' 단독 노출 (D4 의 유일한 신규 노출 케이스)", () => {
    expect(ceoPaletteEntries({ pending: false, drift: true })).toEqual(["repromote"]);
  });
  it("PENDING만 참 → 기존 '승격 진행' 단독 (기존 R8 동선 무회귀)", () => {
    expect(ceoPaletteEntries({ pending: true, drift: false })).toEqual(["pending"]);
  });
  it("동시 참 → pending 우선·재실행 숨김 (최초 승격 미완에 '재실행' 권유 금지)", () => {
    expect(ceoPaletteEntries({ pending: true, drift: true })).toEqual(["pending"]);
  });
  it("둘 다 거짓(invoke 실패 폴백 포함) → 노출 0 (조용한 기본값)", () => {
    expect(ceoPaletteEntries({ pending: false, drift: false })).toEqual([]);
  });
});


describe("A-Z14 — 승격 보류는 「보류」로, 실패는 「실패」로 알린다", () => {
  it("보류 태그(exit 5) → 보류 문구 · 지침이 그대로라고 말한다", () => {
    const t = ceoPromoteFailToast(`${CEO_PROMOTE_HELD_TAG}[cys-dept] CEO 승격 보류`, false);
    expect(t.held).toBe(true);
    expect(t.title).toBe("CEO 승격 보류");
    expect(t.body).toContain("그대로");
    expect(t.title + t.body).not.toContain("완료");
  });
  it("재실행 경로의 보류 → 재실행 보류 문구", () => {
    const t = ceoPromoteFailToast(`${CEO_PROMOTE_HELD_TAG}x`, true);
    expect(t.held).toBe(true);
    expect(t.title).toBe("CEO 승격 재실행 보류");
  });
  it("태그 없는 오류(부서 0개·가드·실행 실패) → 종전 실패 문구 그대로", () => {
    expect(ceoPromoteFailToast("[cys-dept] 부서 0개", false)).toEqual({
      held: false,
      title: "CEO 승격 실패",
      body: "CEO 자리를 세우지 못했습니다. 요청은 그대로 남아 있으니 잠시 뒤 다시 시도해 주세요.",
    });
    expect(ceoPromoteFailToast(new Error("boom"), true).title).toBe("CEO 승격 재실행 실패");
  });
  it("보류 문구는 왕초보 말투(「~해 주세요」) · 파일 이름·영문 기술어 0", () => {
    for (const t of [ceoPromoteFailToast(CEO_PROMOTE_HELD_TAG, false), ceoPromoteFailToast(CEO_PROMOTE_HELD_TAG, true)]) {
      expect(/주세요\.$/.test(t.body)).toBe(true);
      expect(/\.md|pre-ceo|DCE|exit|[A-Za-z_]{4,}/.test(t.body)).toBe(false);
    }
  });
  it("approve_ceo_promotion(promote-ceo) 호출 두 곳(Allow · 재실행)이 모두 이 함수로 실패·보류 문구를 만든다", () => {
    // promote-if-pending(팔레트 '승격 진행' = promote_pending_ceo)은 exit 5 를 내지 않아 이 태그와 무관하다.
    const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
    expect(main.match(/invoke\("approve_ceo_promotion"\)/g)?.length).toBe(2);
    expect(main.match(/ceoPromoteFailToast\(e, false\)/g)?.length).toBe(1);
    expect(main.match(/ceoPromoteFailToast\(e, true\)/g)?.length).toBe(1);
    expect(main).not.toContain('toast("health", "CEO 승격 재실행 실패"');
  });
});
