// statusboard.ts 순수부 — TICKET=cysr-tabs-sidebar-impl 조각 1d(상황판 시안 · master#8ef1fcd7).
import { describe, expect, test } from "bun:test";
import { buildSeatRows, type SeatInput } from "./seatrows";
import { BOARD_KEY, boardCounts, boardVariant, limitLine, limitTitle, nextSeat, resetDayTime } from "./statusboard";

const s = (sid: number, o: Partial<SeatInput> = {}): SeatInput => ({
  sid, displayNo: sid, role: "worker", title: "", cwd: "/w/a", exited: false, dot: "working",
  approvalPending: false, statusState: null, task: null, ctxPct: null, ctxSrc: "none", ...o,
});

describe("노브", () => {
  test("열쇠 · 기본 (가) · 0 끔 · 2 (나) · 그 밖 = 기본", () => {
    expect(BOARD_KEY).toBe("cys-status-board");
    expect(boardVariant(null)).toBe("a");
    expect(boardVariant("0")).toBe("off");
    expect(boardVariant("2")).toBe("b");
    expect(boardVariant("x")).toBe("a");
  });
});

describe("상태 수 — 좌석 줄과 같은 판정(seatState)을 센다", () => {
  test("부서 여럿 합 · 이름 보고자·끝난 좌석은 세지 않음 · 좌석 순서 = 부서 순 → 줄 순", () => {
    const a = buildSeatRows([s(1, { role: "master", dot: "waiting" }), s(2), s(3, { dot: "input" }), s(4, { exited: true }), s(-1, { role: "master", label: "master", dot: null })]);
    const b = buildSeatRows([s(10, { dot: "unknown" }), s(11, { approvalPending: true }), s(12, { dot: "waiting" })]);
    const c = boardCounts([{ wsId: 7, model: a }, { wsId: 8, model: b }]);
    expect([c.working.length, c.idle.length, c.blocked.length, c.unknown.length]).toEqual([1, 2, 2, 1]);
    expect(c.blocked).toEqual([{ wsId: 7, sid: 3 }, { wsId: 8, sid: 11 }]);
    expect(c.idle).toEqual([{ wsId: 7, sid: 1 }, { wsId: 8, sid: 12 }]);
  });
});

describe("숫자를 누르면 차례로", () => {
  test("다음 좌석 · 끝이면 처음 · 목록이 줄면 0 부터 · 빈 목록 = null", () => {
    const xs = [{ wsId: 1, sid: 3 }, { wsId: 1, sid: 5 }, { wsId: 2, sid: 9 }];
    expect(nextSeat(xs, -1)).toEqual({ seat: xs[0], index: 0 });
    expect(nextSeat(xs, 0)).toEqual({ seat: xs[1], index: 1 });
    expect(nextSeat(xs, 2)).toEqual({ seat: xs[0], index: 0 });
    expect(nextSeat(xs, 7)).toEqual({ seat: xs[0], index: 0 });
    expect(nextSeat([], 0)).toBeNull();
  });
});

describe("한도 한 줄((나)) — master#fcbc46fb 결정 ③ 퍼센트 먼저 · 초기화 요일·시각 다음 · 전문 = 툴팁", () => {
  // 2026-11-13(금) 06:00 이 기기 시간대 — 요일·시각은 Date 로 만들어 시간대에 묶이지 않게 한다.
  const reset = new Date(2026, 10, 13, 6, 0, 0).getTime() / 1000;
  const now = reset - (86400 * 2 + 3600 * 3 + 59);
  test("7d 중 가장 높은 값 · 「86% · 금 06:00 초기화」 · 툴팁 = 7일 한도·남은 시간", () => {
    const rows = [
      { label: "7d", usedPct: 50, resetsAt: now + 3600 * 5 },
      { label: "7d", usedPct: 86, resetsAt: reset },
      { label: "5h", usedPct: 99, resetsAt: now + 60 },
    ];
    expect(limitLine(rows, now)).toBe("86% · 금 06:00 초기화");
    expect(limitTitle(rows, now)).toBe("7일 한도 86% 사용 · 금 06:00 초기화(2일 3시간 남음)");
  });
  test("하루 안 = 툴팁 시간·분 · 시각 모름 = 퍼센트만 · 7d 없음 = null · 짧은 꼴은 「초기화까지」 문구를 쓰지 않는다", () => {
    const r = [{ label: "7d", usedPct: 12.4, resetsAt: reset }];
    expect(limitLine(r, reset - (3600 * 3 + 600))).toBe("12% · 금 06:00 초기화");
    expect(limitTitle(r, reset - (3600 * 3 + 600))).toBe("7일 한도 12% 사용 · 금 06:00 초기화(3시간 10분 남음)");
    expect(limitLine([{ label: "7d", usedPct: 40, resetsAt: null }], now)).toBe("40%");
    expect(limitLine([{ label: "5h", usedPct: 40, resetsAt: null }], now)).toBeNull();
    expect(limitTitle([{ label: "5h", usedPct: 40, resetsAt: null }], now)).toBeNull();
    expect(resetDayTime(new Date(2026, 10, 15, 23, 5).getTime() / 1000)).toBe("일 23:05");
  });
});

describe("(1f) 계정 경고 · 모양 어휘", () => {
  test("손써야 할 사유(로그아웃·불일치)만 경고 · 낡음·구버전·미등록·확인 중은 경고 아님", async () => {
    const { accountNeedsAction } = await import("./statusboard");
    expect(accountNeedsAction(["known", "stale", "no_key", "none", "pending", "bad"])).toBe(false);
    expect(accountNeedsAction(["known", "no_login"])).toBe(true);
    expect(accountNeedsAction(["mismatch"])).toBe(true);
  });
  test("상태 → 역할 점 클래스 = 한 벌(같은 값 = 같은 모양 · 막힘 = 역할 점 입력 대기 마름모)", async () => {
    const { SEAT_STATE_ACT } = await import("./seatrows");
    expect(SEAT_STATE_ACT).toEqual({ working: "act-working", idle: "act-waiting", blocked: "act-input", unknown: "act-unknown", exited: "act-exited" });
    const css = (await import("node:fs")).readFileSync(new URL("./style.css", import.meta.url), "utf-8");
    expect(css).toContain(".ws-seat-dot.act-input, .ws-board-dot.act-input { border-radius: 1px; transform: rotate(45deg) scale(0.8); }");
    expect(css).toContain(".pane .pane-role-dot.act-input { border-radius: 1px; transform: rotate(45deg) scale(0.8);");
  });
});

// (TICKET=cysr-1118-ui ②) 박사님 11-22 19:4x 「이상하다. 계정도 하나밖에 안 보인다.」 — 두 계정 7d 가 다 수집되는데 상황판은 최고 하나만 그렸다(top7d).
describe("계정별 한도 줄 — 계정 둘 이상이면 계정마다 한 줄", () => {
  const reset1 = new Date(2026, 10, 27, 6, 0, 0).getTime() / 1000; // 금 06:00
  const reset2 = new Date(2026, 10, 26, 17, 0, 0).getTime() / 1000; // 목 17:00
  const now = reset2 - 3600 * 30;
  // 대역 행 = IPC 꼴 그대로(칸 일부만) — 타입은 계약 밖 값도 받는지 보려고 느슨하게
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const acct = (o: Record<string, unknown>): any => ({ provider: "claude", updated_at: now - 5, source: "oauth", ...o });
  const two = [
    acct({ account_id: "a1", label: "one@example.com", profiles: [".claude"], current_profiles: [".claude"], rate: [{ label: "7d", used_pct: 43, resets_at: reset1 }] }),
    acct({ account_id: "a2", label: "two@example.com", profiles: [".claude-acct2"], current_profiles: [".claude-acct2"], rate: [{ label: "5h", used_pct: 90, resets_at: now + 60 }, { label: "7d", used_pct: 38, resets_at: reset2 }] }),
  ];
  test("두 계정 = 두 줄(이름 · % · 초기화 요일·시각) · 이름 = 폴더 라벨/별명(이메일 0) · 차례 = 이름순(값이 바뀌어도 줄이 자리를 바꾸지 않음)", async () => {
    const { accountLimitRows } = await import("./statusboard");
    const rows = accountLimitRows(two, now);
    expect(rows.map((r) => [r.name, r.pct, r.line])).toEqual([
      ["claude", 43, "43% · 금 06:00"],
      ["claude-acct2", 38, "38% · 목 17:00"],
    ]);
    expect(rows[1].title).toBe("claude-acct2 — 7일 한도 38% 사용 · 목 17:00 초기화(1일 6시간 남음)");
    expect(JSON.stringify(rows)).not.toContain("@");
    const aliased = accountLimitRows([{ ...two[1], alias: "계정2" }, two[0]], now);
    expect(aliased.map((r) => r.name)).toEqual(["claude", "계정2"]);
  });
  test("관측 전(updated_at 없음)·7d 없는 계정은 줄 없음 · 하나뿐이면 1줄(종전 한 줄 꼴은 호출자가 그대로)", async () => {
    const { accountLimitRows } = await import("./statusboard");
    expect(accountLimitRows([two[0], { ...two[1], updated_at: null }], now).length).toBe(1);
    expect(accountLimitRows([two[0], { ...two[1], rate: [{ label: "5h", used_pct: 1, resets_at: null }] }], now).length).toBe(1);
    expect(accountLimitRows([], now)).toEqual([]);
  });
  test("같은 이름 두 계정은 뒤에 번호 · 시각 모름 = 퍼센트만", async () => {
    const { accountLimitRows } = await import("./statusboard");
    const same = [two[0], { ...two[1], profiles: [".claude"], current_profiles: [".claude"], rate: [{ label: "7d", used_pct: 5, resets_at: null }] }];
    expect(accountLimitRows(same, now).map((r) => [r.name, r.line])).toEqual([["claude", "43% · 금 06:00"], ["claude 2", "5%"]]);
  });
});
