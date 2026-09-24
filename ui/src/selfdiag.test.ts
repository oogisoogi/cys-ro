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
  const T = CEO_PROMOTE_HELD_TAG;
  it("보류 · 부트 필요(Allow) → 보류 제목 · 안내 등급 · 부트 안내 · 지침 그대로 · 「완료」 없음", () => {
    const t = ceoPromoteFailToast(`${T}boot:[cys-dept] CEO 승격 보류(부트 필요) — x`, false);
    expect([t.held, t.boot, t.category, t.title]).toEqual([true, true, "feed", "CEO 승격 보류"]);
    expect(t.body).toBe("아직 CEO로 바꾸지 않았어요. 지금 설정은 그대로예요. 본부 마스터를 먼저 한 번 시작한 뒤 다시 눌러 주세요.");
    expect(t.title + t.body).not.toContain("완료");
  });
  it("보류 · 부트 필요(재실행 경로) → 같은 부트 안내(「새 설정」이라 말하지 않음)", () => {
    const t = ceoPromoteFailToast(`${T}boot:y`, true);
    expect([t.title, t.category]).toEqual(["CEO 승격 재실행 보류", "feed"]);
    expect(t.body).toContain("본부 마스터를 먼저 한 번 시작한 뒤");
    expect(t.body).not.toContain("새 설정");
  });
  it("보류 · 그 밖(상위집합 검사 등) → 부트를 권하지 않고 「자세히」로 이유 안내", () => {
    for (const rep of [false, true]) {
      const t = ceoPromoteFailToast(`${T}other:[cys-dept] CEO 승격 보류(지침 미교체) — z`, rep);
      expect([t.held, t.boot, t.category]).toEqual([true, false, "feed"]);
      expect(t.body).not.toContain("시작");
      expect(t.body).toContain("「자세히」를 눌러 확인해 주세요.");
      expect(t.body).toContain("그대로예요");
    }
  });
  it("「자세히」 원문에는 기계 태그·사유가 안 보인다", () => {
    expect(ceoPromoteFailToast(`${T}boot:원문 줄`, false).raw).toBe("원문 줄");
    expect(ceoPromoteFailToast(`Error: ${T}other:원문`, true).raw).toBe("원문");
    expect(ceoPromoteFailToast("그냥 오류", false).raw).toBe("그냥 오류");
  });
  it("태그 없는 오류(부서 0개·가드·실행 실패) → 종전 실패 문구 · 경보 등급", () => {
    const t = ceoPromoteFailToast("[cys-dept] 부서 0개", false);
    expect([t.held, t.category, t.title]).toEqual([false, "health", "CEO 승격 실패"]);
    expect(t.body).toBe("CEO 자리를 세우지 못했습니다. 요청은 그대로 남아 있으니 잠시 뒤 다시 시도해 주세요.");
    const r = ceoPromoteFailToast(new Error("boom"), true);
    expect([r.title, r.category]).toEqual(["CEO 승격 재실행 실패", "health"]);
  });
  it("보류 문구는 왕초보 말투(「~해 주세요」) · 파일 이름·영문 기술어 0", () => {
    for (const e of [`${T}boot:`, `${T}other:`]) {
      for (const rep of [false, true]) {
        const t = ceoPromoteFailToast(e, rep);
        expect(/주세요\.$/.test(t.body)).toBe(true);
        expect(/\.md|pre-ceo|DCE|exit|[A-Za-z_]{4,}/.test(t.body)).toBe(false);
      }
    }
  });
  it("approve_ceo_promotion(promote-ceo) 호출 두 곳이 도우미의 등급·제목·본문·원문을 그대로 쓴다", () => {
    // promote-if-pending(팔레트 '승격 진행' = promote_pending_ceo)은 exit 5 를 내지 않아 이 태그와 무관하다.
    const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
    expect(main.match(/invoke\("approve_ceo_promotion"\)/g)?.length).toBe(2);
    expect(main.match(/ceoPromoteFailToast\(e, false\)/g)?.length).toBe(1);
    expect(main.match(/ceoPromoteFailToast\(e, true\)/g)?.length).toBe(1);
    expect(main.match(/toast\(t\.category, t\.title, t\.body, undefined, t\.raw\);/g)?.length).toBe(2);
    expect(main).not.toContain('toast("health", "CEO 승격 재실행 실패"');
  });
});
