// wsname.test.ts — 이름 없는 탭의 보여 주는 이름(D4 #4 · master 판정 A) · TICKET=v116-ui-close.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { HQ_LABEL, UNNAMED_LABEL, hqWorkspaceId, wsDisplayName, renamedName } from "./wsname";

const U = "non title";
const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");

describe("본부 판정 — 마스터 좌석 우선 · 모르면 첫째 기본 탭", () => {
  const wss = [
    { id: 1, sids: [10] }, // 기본 데몬 탭 A(빈 셸)
    { id: 2, sids: [20, 21] }, // 기본 데몬 탭 B(마스터 21)
    { id: 3, socket: "/d/sales.sock", sids: [5] }, // 부서
    { id: 4, pending: true, sids: [] }, // 부서 준비 중(소켓 미정)
  ];
  it("마스터 좌석이 있는 기본 탭이 본부(둘째여도 빼앗기지 않는다)", () => {
    expect(hqWorkspaceId(wss, new Set([21]))).toBe(2);
  });
  it("마스터 정보를 모르거나(null·빈 집합) 어느 탭에도 없으면 첫째 기본 탭", () => {
    expect(hqWorkspaceId(wss, null)).toBe(1);
    expect(hqWorkspaceId(wss, new Set())).toBe(1);
    expect(hqWorkspaceId(wss, new Set([99]))).toBe(1);
  });
  it("(Fable 2R) 폴백은 id 최소 — 탭을 끌어 순서가 바뀌어도 본부가 옮겨 가지 않는다", () => {
    expect(hqWorkspaceId([wss[1], wss[0]], null)).toBe(1);
  });
  it("부서 탭·준비 중 탭은 본부가 아니다 · 기본 탭이 없으면 null", () => {
    expect(hqWorkspaceId([wss[2], wss[3]], new Set([5]))).toBeNull();
  });
});

describe("보여 주는 이름", () => {
  it("이름 없는 본부 = 본부 · 그 밖의 이름 없는 탭 = 새 화면 · 사람이 붙인 이름은 그대로", () => {
    expect(wsDisplayName(U, U, true)).toBe(HQ_LABEL);
    expect(wsDisplayName(U, U, false)).toBe(UNNAMED_LABEL);
    expect(wsDisplayName("", U, false)).toBe(UNNAMED_LABEL);
    expect(wsDisplayName("리서치부", U, true)).toBe("리서치부");
    expect(wsDisplayName("리서치부", U, false)).toBe("리서치부");
  });
  it("영어 「non title」 이 화면 이름으로 나오지 않는다", () => {
    for (const hq of [true, false]) expect(wsDisplayName(U, U, hq).includes("non title")).toBe(false);
  });
});

describe("이름 편집 — 자동 이름을 그대로 두면 저장값은 미정 그대로", () => {
  it("본부·새 화면을 그대로 두고 편집을 끝내면 untitled 유지(부서 표시명 회복·본부 판정 이동이 멈추지 않게)", () => {
    expect(renamedName("본부", "본부", U, U)).toBe(U);
    expect(renamedName(" 새 화면 ", "새 화면", U, U)).toBe(U);
  });
  it("비우면 untitled · 새 이름이면 그 이름 · 원래 사람 이름이 「본부」였으면 그대로", () => {
    expect(renamedName("", "본부", U, U)).toBe(U);
    expect(renamedName("기획실", "본부", U, U)).toBe("기획실");
    expect(renamedName("본부", "본부", "본부", U)).toBe("본부");
  });
});

describe("배선 — 저장값은 무변경 · 보여 주는 자리는 전부 wsLabel", () => {
  it("상수 UNTITLED(저장값) 그대로 · 복원 회복 판정 그대로", () => {
    expect(main).toContain('const UNTITLED = "non title";');
    expect(main).toContain('if (disp && (ws.name === UNTITLED || ws.name === "…" || /^dept-\\d+$/.test(ws.name))) {');
  });
  it("탭 이름 · 삭제 확인 · 전출 알림 · 부서 삭제 · 그룹 이름 · 부서장 알림이 wsLabel 을 쓴다", () => {
    expect(main).toContain("label.textContent = deptPlaceholderLabel({ pending: ws.pending, name: wsLabel(ws) });");
    expect(main).toContain("const wsName = wsLabel(ws);");
    expect(main).toContain("`→ ${wsLabel(destWs)}`");
    expect(main).toContain("`→ ${wsLabel(destWs)} (surface:${newSid})`");
    expect(main).toContain("const nm = info.name || wsLabel(ws);");
    expect(main).toContain('name: ws.name && ws.name !== UNTITLED ? ws.name : "그룹"');
    expect(main).toContain("label: ws ? wsLabel(ws) : deptSlugOfSocket(sock)");
    expect(main.includes("destWs.name || UNTITLED")).toBe(false);
    expect(main.includes("const wsName = ws.name || UNTITLED")).toBe(false);
  });
  it("이름 편집 확정이 renamedName 을 지나고, 본부 판정 재료는 기본 소켓 목록에서만 갱신된다", () => {
    expect(main).toContain("ws.name = renamedName(name, shownBeforeRename, ws.name, UNTITLED);");
    const at = main.indexOf("hqMasterSids = masterSids;");
    expect(at).toBeGreaterThan(-1);
    expect(main.slice(at - 400, at)).toContain("if ((sk ?? undefined) === undefined) {");
    expect(main.slice(at - 200, at)).toContain("if (masterSids.size) {"); // 마스터가 잠깐 끝나도 본부가 튀지 않게
    // 탭 이름 편집 중엔 탭 막대를 다시 그리지 않는다
    expect(main).toContain(`if (bar.querySelector('.ws-name[contenteditable="true"]')) return;`);
  });
});
