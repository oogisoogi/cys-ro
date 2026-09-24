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

// (v116-ui-close-r2 · master#f55cc917 A 채택) 같은 병의 나머지 절반 — main.ts 4경로도 같은 usedPctOf 를 거친다.
import { readFileSync } from "node:fs";
import { usedPctOf } from "./wsusage";
const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const fnBody = (head: string) => {
  const i = main.indexOf(head);
  return i < 0 ? "" : main.slice(i, main.indexOf("\n}\n", i));
};
test("usedPctOf: null·undefined·빈 값 = NaN(미관측) · 수·수 문자열 = 그 값", () => {
  expect(Number.isNaN(usedPctOf(null))).toBe(true);
  expect(Number.isNaN(usedPctOf(undefined))).toBe(true);
  expect(Number.isNaN(usedPctOf(""))).toBe(true);
  expect(usedPctOf(0)).toBe(0);
  expect(usedPctOf(42)).toBe(42);
  expect(usedPctOf("7")).toBe(7);
  expect(Number.isNaN(usedPctOf(" "))).toBe(true); // (opus NIT) 공백·불리언도 미관측
  expect(Number.isNaN(usedPctOf(false))).toBe(true);
});
test("창 머리 배지(renderUsage): 미관측 창을 걸러 낸 목록으로 배지·툴팁을 모두 그린다", () => {
  const f = fnBody("function renderUsage(");
  expect(f.includes("const rates = (u.rate ?? []).filter((w) => Number.isFinite(usedPctOf(w.used_pct)));")).toBe(true);
  expect(f.includes("for (const w of u.rate ?? [])")).toBe(false);
});
test("Control Center 합산(ccAggRate): 미관측 창은 후보가 아니다", () => {
  expect(fnBody("function ccAggRate(").includes("if (!Number.isFinite(usedPctOf(w.used_pct))) continue;")).toBe(true);
});
test("Control Center 최고 사용 계정(ccAcctMax): usedPctOf 로 읽는다", () => {
  const f = fnBody("function ccAcctMax(");
  expect(f.includes("const used = usedPctOf(r.used_pct);")).toBe(true);
  expect(f.includes("Number(r.used_pct)")).toBe(false);
});
test("Control Center 계정 게이지(renderAccounts gauge): 미관측 = 창 없음(「—」)", () => {
  // (opus 결함 5) 데몬이 죽었다고 판정한 창(stale)은 사유 표시가 우선 — null 판정보다 먼저 거른다
  expect(fnBody("function renderAccounts(").includes("if (r && r.stale !== true && !Number.isFinite(usedPctOf(r.used_pct))) r = undefined;")).toBe(true);
});
