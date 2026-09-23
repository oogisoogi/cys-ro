// wsusage-null.test.ts — used_pct null(미관측)은 0% 게이지가 아니다(D4 #18 · 원본 = 115 디버그 하위조사 B agentB-tests) · TICKET=v116-ui-close-r2.
import { expect, test } from "bun:test";
import { accountRates, aggregateRates, scopedRates } from "./wsusage";

const now = 1_000_000;
test("accountRates: used_pct null 은 0% 행이 되면 안 된다(미관측 ≠ 0%)", () => {
  const rows = accountRates(
    [{ provider: "claude", account_id: "a", label: "x@y", updated_at: now - 5,
       rate: [{ label: "5h", used_pct: null as any, resets_at: now + 100 }] }],
    now,
  );
  expect(rows.length).toBe(0);
});
test("aggregateRates: surface rate used_pct null 도 0% 로 접히면 안 된다", () => {
  const rows = aggregateRates(
    [{ surface_id: 1, socket: "", exited: false, adopted: true,
       usage: { agent: "claude", ctx_pct: 10, source: "statusline", updated_at: now - 5,
                rate: [{ label: "5h", used_pct: null as any, resets_at: null }] } }],
    now,
  );
  expect(rows.length).toBe(0);
});
test("scopedRates: used_pct null", () => {
  const rows = scopedRates(
    [{ provider: "claude", account_id: "a", label: "x", updated_at: now, rate: [],
       scoped: [{ model: "Fable", used_pct: null as any, resets_at: null, updated_at: now - 1, source: "oauth" }] }],
    now,
  );
  expect(rows.length).toBe(0);
});
