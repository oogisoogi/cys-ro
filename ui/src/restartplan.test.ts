import { describe, expect, test } from "bun:test";
import { restartRetryPlan } from "./restartplan";

// 데몬 문면 정본 = src/lib.rs MSG_TYPING_GUARD + handlers.rs draft_gate_denied_response 꼬리.
const GUARD = "human is typing in this pane; retry later or use --queued";

describe("restartRetryPlan (④ 1.1.7)", () => {
  test("기계 잔여(pending_input) 거부 → clear_first 1회 재시도 · 개행 없음", () => {
    const p = restartRetryPlan("claude --continue", `typing_guard: ${GUARD} [draft_gate:pending_input]`);
    expect(p).toEqual({ data: "claude --continue", clearFirst: true });
  });
  test("Error 객체로 와도 같다", () => {
    const p = restartRetryPlan("x", new Error(`typing_guard: ${GUARD} [draft_gate:pending_input]`));
    expect(p?.clearFirst).toBe(true);
  });
  test("사람 초안·화면 점유·일반 타이핑 가드·무관 실패는 재시도하지 않는다", () => {
    for (const e of [
      `typing_guard: ${GUARD} [draft_gate:human_draft]`,
      `typing_guard: ${GUARD} [draft_gate:screen_occupied]`,
      `typing_guard: ${GUARD}`,
      "acl_denied: sender not allowed",
      "",
      undefined,
    ]) {
      expect(restartRetryPlan("x", e)).toBeNull();
    }
  });
});
