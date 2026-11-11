// statusboard.ts 순수부 — TICKET=cysr-tabs-sidebar-impl 조각 1d(상황판 시안 · master#8ef1fcd7).
import { describe, expect, test } from "bun:test";
import { buildSeatRows, type SeatInput } from "./seatrows";
import { BOARD_KEY, boardCounts, boardVariant, limitLine, nextSeat } from "./statusboard";

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

describe("한도 한 줄((나))", () => {
  const now = 1_000_000;
  test("7d 중 가장 높은 값 · 초기화까지 남은 시간", () => {
    const rows = [
      { label: "7d", usedPct: 50, resetsAt: now + 3600 * 5 },
      { label: "7d", usedPct: 86, resetsAt: now + 86400 * 2 + 3600 * 3 + 59 },
      { label: "5h", usedPct: 99, resetsAt: now + 60 },
    ];
    expect(limitLine(rows, now)).toBe("7d 86% · 초기화까지 2일 3시간");
  });
  test("하루 안 = 시간·분 · 시각 모름 = 퍼센트만 · 7d 없음 = null", () => {
    expect(limitLine([{ label: "7d", usedPct: 12.4, resetsAt: now + 3600 * 3 + 600 }], now)).toBe("7d 12% · 초기화까지 3시간 10분");
    expect(limitLine([{ label: "7d", usedPct: 40, resetsAt: null }], now)).toBe("7d 40%");
    expect(limitLine([{ label: "5h", usedPct: 40, resetsAt: null }], now)).toBeNull();
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
