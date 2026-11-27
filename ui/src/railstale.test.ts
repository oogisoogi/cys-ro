// (TICKET=cysr-1121-ui J) 11-26 윈 제보 — 왼쪽 상황판 「claude 86% · 금 06:00」 = 계정1 값인데 usage-accounts 로는 51시간 전(오래됨).
//   CLI·펼침 사용량 칸(usagebar)은 「오래됨」 이라 적는데 상황판·대화 머리 한도 줄은 표시 없이 붉게(80% 문턱) 그렸다.
//   원인 = statusboard 가 accountRates 의 관측 나이(ageSecs)·출처(snapshot)·데몬 죽은 창 표지(windowStale)를 버리고 % 만 넘겼다.
//   고침 = railRateRow(펼침 칸과 같은 30분 선 + 스냅샷 + 죽은 창) → 「N% · 오래됨」 / 죽은 창 「— · 오래됨」 · 경고색 걷음 · 신선한 값 먼저.
// 대조군 = fafe3eee1(v1.1.20) 에는 railRateRow·limitStale 가 없다 → 아래 전부 붉음.
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { accountLimitRows, chatLimitRows, limitLine, limitPct, limitStale, limitTitle, railRateRow } from "./statusboard";
import { accountRates } from "./wsusage";

const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const reset1 = new Date(2026, 10, 27, 6, 0, 0).getTime() / 1000; // 금 06:00
const reset2 = new Date(2026, 10, 26, 17, 0, 0).getTime() / 1000; // 목 17:00
const now = reset2 - 3600 * 30;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const acct = (o: Record<string, unknown>): any => ({ provider: "claude", updated_at: now - 5, source: "statusline", ...o });
const a1 = (ageSecs: number, extra: Record<string, unknown> = {}, w: Record<string, unknown> = {}) =>
  acct({ account_id: "a1", label: "one@example.com", profiles: [".claude"], current_profiles: [".claude"], updated_at: now - ageSecs, rate: [{ label: "7d", used_pct: 86, resets_at: reset1, ...w }], ...extra });
const a2 = acct({ account_id: "a2", label: "two@example.com", profiles: [".claude-acct2"], current_profiles: [".claude-acct2"], rate: [{ label: "7d", used_pct: 38, resets_at: reset2 }] });
const rr = (list: unknown[]) => accountRates(list as never, now).map(railRateRow);

describe("J ① 오래됨 판정 = 펼침 사용량 칸과 같은 30분 선", () => {
  test("3분(120초 stale 선 넘음)은 아직 신선 — 가끔만 보고하는 계정이 깜빡이지 않는다", () => {
    expect(limitStale(rr([a1(180)]))).toBe(false);
    expect(limitLine(rr([a1(180)]), now)).toBe("86% · 금 06:00 초기화");
  });
  test("29분 = 신선 · 30분 = 오래됨", () => {
    expect(limitStale(rr([a1(29 * 60)]))).toBe(false);
    expect(limitStale(rr([a1(30 * 60)]))).toBe(true);
  });
  test("부트 예열 스냅샷은 나이와 무관하게 오래됨", () => {
    expect(limitStale(rr([a1(5, { source: "snapshot" })]))).toBe(true);
  });
});

describe("J ② 계정 하나(한 줄 · 대화 머리 이름 없는 줄)", () => {
  test("51시간 전 값 = 「86% · 오래됨」 · 툴팁에 관측 나이 · 경고색 걷음 신호", () => {
    const rows = rr([a1(51 * 3600)]);
    expect(limitLine(rows, now)).toBe("86% · 오래됨");
    expect(limitStale(rows)).toBe(true);
    expect(limitTitle(rows, now)).toContain("2일 전 관측");
    expect(limitTitle(rows, now)).toContain("오래됨");
    const chat = chatLimitRows([a1(51 * 3600)], now);
    expect(chat).toEqual([{ name: null, pct: 86, line: "86% · 오래됨", title: limitTitle(rows, now)!, stale: true }]);
  });
  test("데몬이 죽은 창으로 판정(24시간 무관측) = 값 대신 「—」", () => {
    const rows = rr([a1(51 * 3600, {}, { stale: true, stale_reason: "no_observation_24h" })]);
    expect(limitLine(rows, now)).toBe("— · 오래됨");
    expect(limitTitle(rows, now)).toContain("지난 창이라 지금 값이 아닙니다");
  });
  test("신선한 값이 오래된 높은 값에 가려지지 않는다(글자·막대 같은 값)", () => {
    const rows = rr([a1(51 * 3600), a2]);
    expect(limitLine(rows, now)).toBe("38% · 목 17:00 초기화");
    expect(limitPct(rows)).toBe(38);
    expect(limitStale(rows)).toBe(false);
  });
  test("신선한 값만 있으면 종전 글 그대로", () => {
    expect(limitLine(rr([a2]), now)).toBe("38% · 목 17:00 초기화");
    expect(limitTitle(rr([a2]), now)).not.toContain("오래됨");
  });
});

describe("J ③ 계정 둘 이상(상황판 계정별 줄 · 대화 머리)", () => {
  test("제보 장면 — 계정1 51시간 전 86% = 「86% · 오래됨」·stale · 계정2 신선 = 종전 꼴", () => {
    const rows = accountLimitRows([a1(51 * 3600), a2], now);
    expect(rows.map((r) => [r.name, r.pct, r.line, r.stale])).toEqual([
      ["claude", 86, "86% · 오래됨", true],
      ["claude-acct2", 38, "38% · 목 17:00", false],
    ]);
    expect(rows[0].title).toContain("오래됨(2일 전 관측");
    expect(chatLimitRows([a1(51 * 3600), a2], now).map((r) => r.stale)).toEqual([true, false]);
  });
  test("죽은 창 = 「— · 오래됨」", () => {
    const rows = accountLimitRows([a1(51 * 3600, {}, { stale: true, stale_reason: "resets_at_passed" }), a2], now);
    expect(rows[0].line).toBe("— · 오래됨");
    expect(rows[0].stale).toBe(true);
  });
});

describe("J ④ 그리는 쪽 배선(경고색 걷음)", () => {
  const BOARD = strip(readFileSync(new URL("./statusboard.ts", import.meta.url), "utf8"));
  const MAIN = strip(readFileSync(new URL("./main.ts", import.meta.url), "utf8"));
  const CHAT = strip(readFileSync(new URL("./views/chat/index.ts", import.meta.url), "utf8"));
  const CSS = readFileSync(new URL("./style.css", import.meta.url), "utf8");
  const VCSS = readFileSync(new URL("./views/views.css", import.meta.url), "utf8");
  test("상황판 계정별 줄 = stale 이면 crit·warn 을 달지 않는다 · 한 줄 막대도", () => {
    expect(BOARD).toMatch(/if \(r\.stale\) row\.classList\.add\("stale"\);\s*else if \(r\.pct >= 80\)/);
    expect(BOARD).toMatch(/o\.limitStale \? "" : p >= 80/);
  });
  test("main.ts 가 같은 판정(railRateRow · limitStale)을 넘긴다", () => {
    expect(MAIN).toContain("accountRates(accountsCache, nowSecs).map(railRateRow)");
    expect(MAIN).toContain("limitStale: limitStale(rateRows)");
  });
  test("대화 머리 = stale 이면 경고색 없음 · 흐림 규칙 있음", () => {
    expect(CHAT).toContain('r.stale ? " stale" : r.pct >= 80');
    expect(VCSS).toContain(".cv-limit.stale");
    expect(CSS).toContain(".ws-board-acct-row.stale");
  });
});
