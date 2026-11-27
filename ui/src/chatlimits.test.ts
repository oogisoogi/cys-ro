// (TICKET=cysr-1118u-chat ①) 박사님 11-23 「윈 cysr 대화 화면에는 토큰 사용 표시가 안 보인다.」
//   원인 = views/index.ts onShown 이 대화 화면을 켜면 bodyRow(왼쪽 상황판 포함)를 숨긴다 → 대화 화면엔 한도 표시가 없었다.
//   고침 = 대화 화면 머리에 한도 줄(statusboard.chatLimitRows = 상황판과 같은 판정 · main.ts 15초 캐시 그대로 · 새 조회 0).
// 대조군 = 고치기 전 판(9c46ff6d0)에는 chatLimitRows · act.limits · cv-limits 가 없다 → 아래 ①②③ 붉음.
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { Sim } from "./views/testkit";

const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const MAIN = strip(readFileSync(new URL("./main.ts", import.meta.url), "utf8"));
const INDEX = strip(readFileSync(new URL("./views/index.ts", import.meta.url), "utf8"));
const CHAT = strip(readFileSync(new URL("./views/chat/index.ts", import.meta.url), "utf8"));

const reset1 = new Date(2026, 10, 27, 6, 0, 0).getTime() / 1000; // 금 06:00
const reset2 = new Date(2026, 10, 26, 17, 0, 0).getTime() / 1000; // 목 17:00
const now = reset2 - 3600 * 30;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const acct = (o: Record<string, unknown>): any => ({ provider: "claude", updated_at: now - 5, source: "oauth", ...o });
const one = acct({ account_id: "a1", label: "one@example.com", profiles: [".claude"], current_profiles: [".claude"], rate: [{ label: "5h", used_pct: 12, resets_at: now + 600 }, { label: "7d", used_pct: 43, resets_at: reset1 }] });
const two = acct({ account_id: "a2", label: "two@example.com", profiles: [".claude-acct2"], current_profiles: [".claude-acct2"], rate: [{ label: "5h", used_pct: 90, resets_at: now + 60 }, { label: "7d", used_pct: 81, resets_at: reset2 }] });

describe("① 대화 화면 한도 줄 = 작업 화면 상황판과 같은 판정", () => {
  test("계정 둘 = 계정마다 한 줄 · 상황판 accountLimitRows 와 값이 같다 · 이메일 0", async () => {
    const { chatLimitRows, accountLimitRows } = await import("./statusboard");
    const rows = chatLimitRows([one, two], now);
    expect(rows.map((r) => [r.name, r.pct, r.line])).toEqual([
      ["claude", 43, "43% · 금 06:00"],
      ["claude-acct2", 81, "81% · 목 17:00"],
    ]);
    expect(rows).toEqual(accountLimitRows([one, two], now).map((r) => ({ name: r.name, pct: r.pct, line: r.line, title: r.title, stale: r.stale })));
    expect(JSON.stringify(rows)).not.toContain("@");
  });
  test("계정 하나 = 상황판 한 줄(limitLine · limitTitle)과 같은 글 · 이름 없음", async () => {
    const { chatLimitRows, limitLine, limitTitle } = await import("./statusboard");
    const { accountRates } = await import("./wsusage");
    const rr = accountRates([one], now).map((r) => ({ label: r.label, usedPct: r.usedPct, resetsAt: r.resetsAt }));
    expect(chatLimitRows([one], now)).toEqual([{ name: null, pct: 43, line: limitLine(rr, now)!, title: limitTitle(rr, now)!, stale: false }]);
    expect(chatLimitRows([one], now)[0].line).toBe("43% · 금 06:00 초기화");
  });
  test("관측 전·7d 없음·빈 목록 = 줄 없음", async () => {
    const { chatLimitRows } = await import("./statusboard");
    expect(chatLimitRows([], now)).toEqual([]);
    expect(chatLimitRows(null, now)).toEqual([]);
    expect(chatLimitRows([{ ...one, updated_at: null }], now)).toEqual([]);
    expect(chatLimitRows([{ ...one, rate: [{ label: "5h", used_pct: 9, resets_at: null }] }], now)).toEqual([]);
  });
});

describe("② act.limits — 원천 그대로 · 없거나 던지면 빈 목록(대화 화면이 깨지지 않음)", () => {
  test("deps.limits 없음 = []", () => {
    const sim = new Sim();
    expect(sim.core.limits()).toEqual([]);
  });
  test("deps.limits 값 그대로 · 던지면 []", () => {
    const sim = new Sim();
    const v = [{ name: null, pct: 5, line: "5%", title: "7일 한도 5% 사용" }];
    (sim.deps as { limits?: () => unknown }).limits = () => v;
    expect(sim.core.limits()).toEqual(v);
    (sim.deps as { limits?: () => unknown }).limits = () => {
      throw new Error("x");
    };
    expect(sim.core.limits()).toEqual([]);
  });
  test("act.limits 는 조회를 하지 않는다(invoke 0)", () => {
    const sim = new Sim();
    (sim.deps as { limits?: () => unknown }).limits = () => [];
    sim.core.limits();
    expect(sim.calls.length).toBe(0);
  });
});

describe("③ 배선 — main.ts → bootViews → ChatCore → 대화 화면 머리", () => {
  test("main.ts 가 상황판과 같은 캐시(accountsCache)·같은 판정(chatLimitRows)을 넘긴다 · 새 invoke 0", () => {
    expect(MAIN).toContain("limits: () => chatLimitRows(accountsCache, Date.now() / 1000)");
    expect(MAIN.split('invoke("usage_accounts_all")').length - 1).toBe(1); // 조회 자리 = 15초 폴러 1곳(1.1.19 · cysr-1119-s10b: Control Center Live 조회는 Live 와 함께 빠졌다) — 대화 화면 몫 새 조회 0
  });
  test("views/index.ts 가 ChatCore 에 limits 를 건넨다", () => {
    expect(INDEX).toContain("limits: () => deps.limits?.() ?? []");
  });
  test("대화 화면 머리에 cv-limits(act.limits 로 그림 · 5초 들여다봄)", () => {
    expect(CHAT).toContain('el("div", "cv-limits")');
    // (TICKET=cysr-1119-s5 · V3) 자리 = 넓은 창 왼쪽 칸 아래 · 600px 이하 머리(같은 요소 옮겨 붙임 · master#ef0385eb)
    expect(CHAT).toContain("if (narrowMq?.matches) head.insertBefore(limits, guideBtn);");
    expect(CHAT).toContain("else rail.foot.append(limits);");
    expect(CHAT).toContain("const rows = act.limits();");
    expect(CHAT).toContain("ctx.timers.every(5_000, paintLimits);");
  });
});
