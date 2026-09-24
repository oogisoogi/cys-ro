// ctxgroup.test.ts — 페인 CTX 부서 좌석 이름 「dept-」 잘림(D4 #10) · TICKET=v116-ui-close-r2.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { ctxLines, type CtxRow } from "./wsusage";

const r = (surfaceId: number, socket: string, name = ""): CtxRow => ({ surfaceId, name, socket, ctxPct: 10, ageSecs: 1, updatedAt: 1, stale: false, source: "statusline" });
const D = "/Users/u/.local/state/cys-dept-dept-3/cys.sock";
const label = (s: string) => (s ? "영업 기획 부서" : "본부");

describe("D4 #10 ctxLines — 부서마다 머리줄 1개 · 행 라벨은 번호만", () => {
  it("소켓이 여럿이면 소켓이 바뀔 때마다 머리줄(부서 이름 전체)", () => {
    const L = ctxLines([r(0, "", "master"), r(1, ""), r(2, ""), r(12, D), r(13, D)], true, label);
    expect(L.map((x) => (x.kind === "group" ? `[${x.label}]` : String(x.row.name || x.row.surfaceId)))).toEqual(["master", "[본부]", "1", "2", "[영업 기획 부서]", "12", "13"]);
  });
  it("소켓이 하나면 머리줄 0(종전 화면 그대로)", () => {
    expect(ctxLines([r(1, ""), r(2, "")], false, label).every((x) => x.kind === "row")).toBe(true);
  });
  it("이름 보고자(master·cso) 행에는 머리줄을 두지 않는다", () => {
    expect(ctxLines([r(0, "", "master"), r(0, "", "cso")], true, label).filter((x) => x.kind === "group").length).toBe(0);
  });
});

describe("D4 #10 배선", () => {
  const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  it("행 라벨에 소켓 태그(「dept-3:12」)를 붙이지 않는다 · 머리줄은 부서 탭 이름", () => {
    expect(main).toContain("sid.textContent = c.name ? c.name : String(c.surfaceId);");
    expect(main.includes("`${tag}:${c.surfaceId}`")).toBe(false);
    expect(main).toContain("for (const line of ctxLines(ctxRows, showSocket, ctxGroupLabel)) {");
    const f = main.slice(main.indexOf("function ctxGroupLabel("), main.indexOf("function wsLabel("));
    expect(f.includes('if (!socket) return "본부";')).toBe(true);
    expect(f.includes("return ws ? wsLabel(ws) :")).toBe(true);
  });
  it("머리줄은 패널 폭에 한 줄(말줄임은 머리줄 전체 폭 기준)", () => {
    const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
    expect(css).toContain(".wsu-ctx-group {");
    expect(/\.wsu-ctx-group \{[^}]*width:/.test(css)).toBe(false);
    expect(/\.wsu-ctx-group \{[^}]*font-size: \.9em/.test(css)).toBe(true); // (opus 결함 4) 패널 배율을 따른다
  });
});
