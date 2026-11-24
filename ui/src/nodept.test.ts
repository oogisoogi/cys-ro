// (tabs-sidebar 1h · master#edd9d8a8 · 박사님 「권고대로」) 부서 0개(본부만) 기기 = 화면에 「부서」 말·단추·안내 0 · 1개라도 있으면 그대로.
// 못박는 것: 판정 = 부서 수(레지스트리 deptSeen + 열린 부서 탭 ws.socket · 전문가 모드 아님) · 숨김 = body.no-depts + .dept-only(요소·코드 남음) ·
//   팔레트 「부서 워크스페이스 추가」 = 부서가 있거나 전문가 모드일 때만 · 0개면 「본부」 대신 「새 화면」 · 만드는 길(launchDept · 전문가 칸) 무변경.
// 화면 실측 = ui/e2e/nodept_gate.py.
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
const body = (name: string): string => {
  const i = main.indexOf(`function ${name}(`);
  return main.slice(i, main.indexOf("\n}\n", i));
};

describe("(1h) 부서 0개 = 부서 흔적 화면 0", () => {
  test("판정 = 부서 수(레지스트리에서 본 부서 + 열린 부서 탭)", () => {
    expect(body("deptsPresent")).toContain("return (deptSeen?.size ?? 0) > 0 || workspaces.some((w) => !!w.socket);");
    expect(body("applyDeptPresence")).toContain('document.body.classList.toggle("no-depts", !deptsPresent());');
    expect(body("renderWsTabs")).toContain("applyDeptPresence();");
  });
  // (1.1.19 · cysr-1119-s10b MD-CC) Control Center 「작업」 탭(설명문의 「모든 부서의」 조각)은 탭과 함께 빠졌다 — 남은 dept-only = 사이드바 안내 줄.
  test("숨김 = CSS 한 줄(요소는 남는다) · 안내 줄의 「부서」 조각에 dept-only · 작업 탭 설명문은 없음", () => {
    expect(css).toContain("body.no-depts .dept-only { display: none !important; }");
    expect(html).toContain('<div id="ws-dept-hint" class="dept-only">새 부서가 필요하면 마스터에게 말로 부탁하세요</div>');
    expect(html.includes("cc-view-tasks")).toBe(false);
  });
  test("팔레트 「부서 워크스페이스 추가」 = 부서가 있거나 전문가 모드일 때만 · 같은 문(launchDept)", () => {
    const b = body("buildPaletteItems");
    const gate = b.indexOf("if (deptsPresent() || expertModeOn(localStorage.getItem(EXPERT_KEY)))");
    expect(gate).toBeGreaterThan(0);
    expect(b.indexOf('id: "act:dept"')).toBeGreaterThan(gate);
    expect(b).toContain("action: () => { void launchDept(); }");
  });
  test("0개면 「본부」 대신 이름 없는 탭 = 「새 화면」(부서가 생기면 다시 「본부」) · 저장값 무변경", () => {
    expect(body("wsLabel")).toContain("return wsDisplayName(ws.name, UNTITLED, ws.id === hq && deptsPresent());");
  });
  test("만드는 길은 그대로 — 전문가 칸·부서 단추·새 부서 자동 열기", () => {
    expect(html).toContain('<div id="ws-expert" hidden>');
    expect(main).toContain("async function openNewlyRegisteredDepts(): Promise<boolean> {");
  });
});
