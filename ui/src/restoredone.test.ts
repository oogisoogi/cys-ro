// ★seatkeep-t1(codex 3R ④) — 조직 복원 done 알림이 부서 「확인 못 함」과 어긋나지 않는다.
// 백엔드(src-tauri spawn_org_restore)는 상한 초과 부서를 ok·fail 어디에도 세지 않고 `pending` 으로 싣고, 그 부서 알림 = 「OO: 다시 켰지만 … 결과를 확인하지 못했습니다 — …」.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { followupConfirmedToast, followupEndToast, restoreDoneMaySweep, restoreDoneToast, restoreEventIsStale, type RestoreDonePayload } from "./restoredone";

describe("restoreDoneToast — 확인 못 한 부서가 있으면 「완료」라고 말하지 않는다", () => {
  it("진리표(hq_ok·fail·depts_unreadable·hq_pending·pending 32칸): pending>0 이면 어느 칸도 「✅ 직원 복귀 완료」·「복원 완료」가 아니다", () => {
    for (let b = 0; b < 32; b++) {
      const p: RestoreDonePayload = {
        hq_ok: b & 1 ? false : true,
        fail: b & 2 ? 1 : 0,
        depts_unreadable: b & 4 ? "x" : null,
        hq_pending: !!(b & 8),
        pending: b & 16 ? 1 : 0,
        ok: 1,
      };
      const t = restoreDoneToast(p);
      const all = `${t.name} ${t.detail}`;
      if (p.pending) {
        expect(all.includes("완료")).toBe(false);
        expect(restoreDoneMaySweep(p)).toBe(false);
      }
      // 다른 원인이 하나도 없을 때만 확인 못 함 문안이 본문 — 그 문안은 부서 알림과 같은 낱말(「확인하지 못했습니다」)을 쓴다.
      if (p.pending && p.hq_ok !== false && !p.fail && !p.depts_unreadable && !p.hq_pending) {
        expect(t.name).toBe("👥 직원 복귀 진행 중");
        expect(t.detail).toContain("부서 1곳은 다시 켰지만 직원 자리 복귀가 아직 끝나지 않아 결과를 확인하지 못했습니다");
        expect(t.detail).toContain("↻ 재시작");
      }
      if (b === 0) expect(t.name).toBe("✅ 직원 복귀 완료");
    }
  });
  it("종전 갈래 문안은 바이트 같다(옮기기만 함)", () => {
    expect(restoreDoneToast({ ok: 2, fail: 1 })).toEqual({ category: "health", name: "⚠ 직원 복귀 일부 실패", detail: "부서 복원 성공 2 · 실패 1 — 상태를 점검하세요." });
    expect(restoreDoneToast({ ok: 3 })).toEqual({ category: "watchdog", name: "✅ 직원 복귀 완료", detail: "노드 세션 복원 완료 (부서 3)." });
    expect(restoreDoneToast({ hq_pending: true }).detail).toBe("본부 좌석은 자동 복원이 이어서 세웁니다. 실패하면 알림으로 알려 드립니다.");
    expect(restoreDoneToast({ hq_ok: false, hq_note: "N", ok: 1, fail: 0 }).detail).toBe("N (부서 성공 1 · 실패 0)");
    expect(restoreDoneMaySweep({})).toBe(true);
    expect(restoreDoneMaySweep({ hq_pending: true })).toBe(false);
  });
});

describe("후속 감시 = 끝점별로만(r5 축소 · codex r4 #4·#5·#6·#8)", () => {
  it("확인됨 = 그 끝점만 · 확인 못 함 = 끝점 이름 + ↻ 안내 · 어느 쪽도 「완료」 낱말 0 · 없으면 알림 0", () => {
    const ok = followupConfirmedToast("행정부");
    expect(`${ok.name} ${ok.detail}`).toBe("👥 행정부 직원 복귀 확인됨 늦게 끝난 자동 복원을 확인했습니다.");
    expect(`${ok.name} ${ok.detail}`.includes("완료")).toBe(false);
    expect(followupEndToast({ unconfirmed: [] })).toBeNull();
    expect(followupEndToast({})).toBeNull();
    const end = followupEndToast({ unconfirmed: ["본부", "행정부"] })!;
    expect(end.category).toBe("health");
    expect(end.name).toBe("⚠ 직원 복귀를 확인하지 못함");
    expect(end.detail).toBe("본부 · 행정부의 자동 복원이 끝났는지 아직 확인하지 못했습니다 — 잠시 뒤 ↻ 재시작을 눌러 다시 확인하세요.");
    expect(`${end.name} ${end.detail}`.includes("완료")).toBe(false);
  });
  it("회차: 지금 회차보다 작은 번호 = 옛 것(버림) · 같은/큰 번호·번호 없음 = 버리지 않음", () => {
    expect(restoreEventIsStale(1, 2)).toBe(true);
    expect(restoreEventIsStale(2, 2)).toBe(false);
    expect(restoreEventIsStale(3, 2)).toBe(false);
    expect(restoreEventIsStale(undefined, 2)).toBe(false);
  });
  it("배선: main.ts — 회차 거르기가 모든 갈래 앞 · followup-ok/followup-end 는 「완료」·쓸기 무장 0 · 확인 못 함 = sticky · 새 회차 start 가 걷음", () => {
    const src = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
    const body = src.slice(src.indexOf('await listen("restore-progress", (e) => {'));
    const lis = body.slice(0, body.indexOf("\n  });\n"));
    const stale = lis.indexOf("if (restoreEventIsStale(p.round, restoreRound)) return;");
    expect(stale).toBeGreaterThan(0);
    expect(stale).toBeLessThan(lis.indexOf('if (p.phase === "start") briefGate.restoreStarted = true;'));
    expect(lis.includes("restoreRound = p.round;\n      dismissToast(RESTORE_UNCONFIRMED_TOAST_ID);")).toBe(true);
    expect(lis.includes('stickyToast("restore", "feed", "👥 직원 복귀 확인 중"')).toBe(true);
    const fu = lis.slice(lis.indexOf('} else if (p.phase === "followup-ok" && p.place) {'));
    expect(fu.length).toBeGreaterThan(0);
    expect(fu.includes("armSweep")).toBe(false); // 쓸기 무장은 done 만
    expect(fu.includes("restoreDoneToast")).toBe(false);
    expect(fu.includes("if (t) stickyToast(RESTORE_UNCONFIRMED_TOAST_ID, t.category, t.name, t.detail);")).toBe(true);
    expect(lis.includes('"settled"')).toBe(false);
    // 「✅ 직원 복귀 완료」 발행 자리 = restoreDoneToast(첫 회차 done) 한 곳뿐.
    const rd = readFileSync(new URL("./restoredone.ts", import.meta.url), "utf8");
    expect(rd.split('"✅ 직원 복귀 완료"').length - 1).toBe(1); // 문자열 값으로(주석 제외)
    expect(src.includes('"✅ 직원 복귀 완료"')).toBe(false);
  });
});
