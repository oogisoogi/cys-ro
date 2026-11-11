// seatrowsdom.ts 순수부 + main.ts 배선 고정 (bun test) — TICKET=cysr-tabs-sidebar-impl 조각 1b.
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { buildSeatRows, type SeatInput } from "./seatrows";
import { seatRowsSignature, seatRowTitle } from "./seatrowsdom";

const inp = (o: Partial<SeatInput>): SeatInput => ({
  sid: 1, displayNo: 1, role: "worker", title: "", cwd: "/w/a", exited: false, dot: "working",
  approvalPending: false, statusState: null, task: null, ctxPct: 30, ctxSrc: "measured", ...o,
});

describe("서명 — 값이 같으면 같고 화면에 보이는 값이 바뀌면 달라진다", () => {
  test("같은 값 = 같은 서명(3초마다 DOM 재생성 0)", () => {
    expect(seatRowsSignature(buildSeatRows([inp({})]))).toBe(seatRowsSignature(buildSeatRows([inp({})])));
  });
  test("상태 · 꼬리표 · CTX 반올림 값 · 묶음 머리 유무가 바뀌면 달라진다", () => {
    const a = seatRowsSignature(buildSeatRows([inp({})]));
    expect(seatRowsSignature(buildSeatRows([inp({ dot: "waiting" })]))).not.toBe(a);
    expect(seatRowsSignature(buildSeatRows([inp({ approvalPending: true })]))).not.toBe(a);
    expect(seatRowsSignature(buildSeatRows([inp({ ctxPct: 31 })]))).not.toBe(a);
    expect(seatRowsSignature(buildSeatRows([inp({}), inp({ sid: 2, displayNo: 2, cwd: "/w/b" })]))).not.toBe(
      seatRowsSignature(buildSeatRows([inp({}), inp({ sid: 2, displayNo: 2, cwd: "/w/a" })])),
    );
  });
  test("CTX 소수점 흔들림(30.2 → 30.4)은 다시 그리지 않는다", () => {
    expect(seatRowsSignature(buildSeatRows([inp({ ctxPct: 30.2 })]))).toBe(seatRowsSignature(buildSeatRows([inp({ ctxPct: 30.4 })])));
  });
});

describe("툴팁 — 모양만으로 뜻을 전하지 않는다", () => {
  test("상태 이름·꼬리표·CTX 출처를 글로", () => {
    const r = buildSeatRows([inp({ displayNo: 934, task: "6강 발행", approvalPending: true, ctxPct: 52 })]).groups[0].rows[0];
    expect(seatRowTitle(r)).toBe("934번 좌석 · 6강 발행\n상태: 막힘 · 승인 창\nCTX 52%");
  });
  test("결측 CTX 는 0% 가 아니라고 적는다 · 낡음은 판정 불가", () => {
    const none = buildSeatRows([inp({ ctxPct: null, ctxSrc: "none" })]).groups[0].rows[0];
    expect(seatRowTitle(none)).toContain("0% 라는 뜻이 아니다");
    const stale = buildSeatRows([inp({ ctxPct: null, ctxSrc: "stale" })]).groups[0].rows[0];
    expect(seatRowTitle(stale)).toContain("판정 불가");
  });
});

describe("main.ts 배선 — 배선만 · 옛 페인 CTX 칸 없음", () => {
  const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  const body = (name: string): string => {
    const i = main.search(new RegExp(`(async )?function ${name}\\(`));
    expect(i >= 0).toBe(true);
    return main.slice(i, main.indexOf("\n}\n", i) + 3);
  };
  test("부서 카드마다 같은 호스트를 붙인다(그룹 안 카드 포함)", () => {
    expect(body("renderWsTabs")).toContain("bar.append(buildTab(ws), seatHost(String(ws.id)));");
    expect(body("renderWsTabs")).toContain("refreshSeatRows();");
    expect(body("buildGroupSection")).toContain("body.append(tab, seatHost(String(ws.id)));");
  });
  test("3초 고리 끝에서 다시 칠한다 · 10초 고리에서 승인 좌석을 갱신한다", () => {
    expect(body("refreshPaneTitles")).toContain("refreshSeatRows(); // (tabs-sidebar 조각1)");
    expect(body("refreshPaneTitles")).toContain("seatListBySock.set(sk ?? \"\", new Map(r.surfaces.map((s) => [s.surface_id, s])));");
    expect(body("refreshSidebarStatus")).toContain("await refreshApprovalSeats();");
  });
  test("좌석 줄 활동 점 = 데몬 관측 우선 · 모름일 때만 신선한 자기보고(seatDot) — 출력 활동 추정(surfaceWorking)은 쓰지 않는다", () => {
    expect(body("refreshSeatRows")).toContain("seatDot(p.view, self)");
    expect(body("refreshSeatRows").includes("surfaceWorking(")).toBe(false);
    expect(body("paintRoleDot")).toContain('p.view === "unknown" && surfaceWorking(rt.sid, rt.socket)');
  });
  test("옛 「페인 CTX」 머리·행이 다시 그려지지 않는다(신선도 꼬리만 남음)", () => {
    expect(main.includes('head.textContent = "페인 CTX";')).toBe(false);
    expect(body("renderSidebarUsage")).toContain("oldestFootText(");
  });
});
