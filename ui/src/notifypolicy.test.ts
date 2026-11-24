// notifypolicy.test.ts — BA3 「지금 그 좌석을 보고 있으면 알림 생략」 한 규칙(TICKET=cysr-1119-s9 · DESIGN §7 BA3 · 결정 ③ 줄인 판).
// 진리표 16칸 = 알림 종류 4((확인 필요 · 끝남) × (앱 안 토스트 · OS 배너)) × 보고 있음/아님 × 앱 앞/뒤.
// 되돌리기 = 상수 NOTIFY_SKIP_WHEN_VIEWED=false → 16칸 전부 냄(1.1.18 꼴).
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { NOTIFY_KINDS, NOTIFY_SKIP_WHEN_VIEWED, notifyAllowed, type NotifyKind } from "./notifypolicy";

const KINDS: NotifyKind[] = ["needs_you.toast", "needs_you.os", "finished.toast", "finished.os"];

describe("BA3 notifypolicy — 16칸 진리표", () => {
  test("알림 종류 = 넷(확인 필요·끝남 × 토스트·OS 배너) — 표 밖 종류 0", () => {
    expect([...NOTIFY_KINDS]).toEqual(KINDS);
  });

  test("출하 값 = 켬(보고 있으면 생략)", () => {
    expect(NOTIFY_SKIP_WHEN_VIEWED).toBe(true);
  });

  const cells: [NotifyKind, boolean, boolean, boolean][] = [];
  for (const kind of KINDS)
    for (const viewed of [true, false])
      for (const appFront of [true, false])
        // 내는가 = 「보고 있음 ∧ 앱 앞」이 아닐 때만 · 앱이 뒤에 있으면 그 좌석이 화면에 떠 있어도 사람은 못 보고 있다
        cells.push([kind, viewed, appFront, !(viewed && appFront)]);

  test("16칸 전부 — 생략은 「보고 있음 ∧ 앱 앞」 4칸뿐", () => {
    expect(cells.length).toBe(16);
    const got = cells.map(([kind, viewed, appFront]) => [kind, viewed, appFront, notifyAllowed({ kind, viewed, appFront })]);
    expect(got).toEqual(cells);
    expect(cells.filter((c) => !c[3]).length).toBe(4);
  });

  test("되돌리기 — 상수 false 면 16칸 전부 냄(1.1.18 꼴)", () => {
    for (const [kind, viewed, appFront] of cells) expect([kind, viewed, appFront, notifyAllowed({ kind, viewed, appFront }, false)]).toEqual([kind, viewed, appFront, true]);
  });

  test("판정은 순수 — 입력 말고는 읽지 않는다(document·window·localStorage·Date 0)", () => {
    const src = readFileSync(new URL("./notifypolicy.ts", import.meta.url), "utf8").replace(/\/\/.*$/gm, "");
    for (const w of ["document", "window", "localStorage", "Date", "import "]) expect([w, src.includes(w)]).toEqual([w, false]);
  });
});

// main.ts 배선 — 생략 판정이 닿는 자리는 승인 요청(토스트·OS 배너)과 끝남(조용한 창 토스트) 둘뿐이다.
describe("BA3 배선(main.ts 원천)", () => {
  const SRC = readFileSync(new URL("./main.ts", import.meta.url), "utf8")
    .split("\n")
    .map((l) => (l.trimStart().startsWith("//") ? "" : l.replace(/\s\/\/.*$/, "")))
    .join("\n");
  const ev = (() => {
    const i = SRC.indexOf("function onDaemonEvent(");
    return SRC.slice(i, SRC.indexOf("\n}\n", i));
  })();
  const branch = (name: string) => {
    const i = ev.indexOf(`if (name === "${name}") {`);
    return ev.slice(i, ev.indexOf("\n  }\n", i));
  };

  test("approval.request = 토스트·OS 배너 각각 판정을 거친다(종류 needs_you.toast · needs_you.os)", () => {
    const b = branch("approval.request");
    expect(b).toContain('notifyAllowed({ kind: "needs_you.toast", viewed, appFront })');
    expect(b).toContain('notifyAllowed({ kind: "needs_you.os", viewed, appFront })');
    expect(b).toMatch(/if \(notifyAllowed\(\{ kind: "needs_you\.toast"[^\n]*\) daemonToast\("approval", c\.title, c\.body\);/);
    expect(b).toMatch(/if \(notifyAllowed\(\{ kind: "needs_you\.os"[^\n]*\) daemonOsBanner\(c\.title, c\.body\);/);
    // 배지·Feed 갱신은 알림 생략과 무관하게 그대로
    expect(b).toContain("refreshFeed();");
    expect(b).toContain("refreshSidebarStatus();");
  });

  test("pane.idle = 토스트가 판정을 거친다(finished.toast) · 배지 갱신 그대로", () => {
    const b = branch("pane.idle");
    expect(b).toMatch(/if \(notifyAllowed\(\{ kind: "finished\.toast"[^\n]*\) daemonToast\("idle", c\.title, c\.body\);/);
    expect(b).toContain("refreshSidebarStatus();");
  });

  test("판정을 거치는 자리는 셋뿐(다른 분기 0) · 끝남 OS 배너는 1.1.18 에 자리가 없다(새 배너 0)", () => {
    expect((ev.match(/notifyAllowed\(/g) ?? []).length).toBe(3);
    expect(ev).not.toContain('"finished.os"');
  });

  test("「보고 있음」 = 작업 화면 보임 ∧ 컨트롤 센터 닫힘 ∧ 이벤트 데몬 = 지금 작업공간 데몬 ∧ seatVisible", () => {
    const i = SRC.indexOf("function seatViewedNow(");
    expect(i).toBeGreaterThan(0);
    const f = SRC.slice(i, SRC.indexOf("\n}\n", i));
    expect(f).toContain("workRuntimeWanted()");
    expect(f).toContain("ccOpen");
    expect(f).toContain("eventSock(");
    expect(f).toContain("seatVisible(");
    expect(f).toContain("current()");
  });

  test("「앱 앞」 = 문서 보임 ∧ 창 초점", () => {
    const i = SRC.indexOf("function appInFront(");
    expect(i).toBeGreaterThan(0);
    const f = SRC.slice(i, SRC.indexOf("\n}\n", i));
    expect(f).toContain('document.visibilityState === "visible"');
    expect(f).toContain("document.hasFocus()");
  });
});
