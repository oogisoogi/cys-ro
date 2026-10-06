// toastraw.test.ts — 오류 알림 본문 = 사람 말 · 백엔드 원문은 접힌 「자세히」 안쪽(D4 #14) · TICKET=v116-ui-close-r2.
// 화면 실측은 docs/v116-ui-evidence/v116-headless.ts c15.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const callLines = main.split("\n").filter((l) => /\b(toast|stickyToast)\(/.test(l) && !/^\s*(\/\/|\*)/.test(l));

describe("D4 #14 도우미", () => {
  it("setToastRaw — 접힌 details · 「자세히」 · textContent 로만 · 갱신 때 옛 원문 제거", () => {
    const f = main.slice(main.indexOf("function setToastRaw("), main.indexOf("// 우상단 ×"));
    expect(f.includes("prev?.remove();")).toBe(true);
    expect(f.includes("d.open = wasOpen;")).toBe(true); // (opus NIT) 갱신 때 펼침 유지
    expect(f.includes("  if (!raw) return;\n  const d = ")).toBe(true);
    expect(f.includes('document.createElement("details")')).toBe(true);
    expect(f.includes("pre.textContent = raw;")).toBe(true);
    expect(f.includes("innerHTML")).toBe(false);
    expect(f.includes(".open = true")).toBe(false);
    expect(main).toContain('const RAW_DETAIL_LABEL = "자세히";');
  });
  it("toast · stickyToast 둘 다 원문을 받아 붙이고, 알람 이력에는 원문을 남긴다(진단 재료 삭제 0)", () => {
    expect(main).toContain("function toast(category: string, name: string, detail: string, onClick?: () => void, raw?: string) {");
    expect(main).toContain("function stickyToast(id: string, category: string, name: string, detail: string, onClick?: () => void, raw?: string) {");
    expect(main.split("setToastRaw(el, raw);").length - 1).toBe(2);
    expect(main).toContain("recordAlarm(category, name, detail, undefined, raw);");
    expect(main).toContain("recordAlarm(category, name, detail, id, raw);");
    expect(main).toContain("detail: raw ? `${detail}\\n${RAW_DETAIL_LABEL}: ${raw}` : detail");
  });
});

describe("D4 #14 원문을 본문에 싣는 알림 0", () => {
  it("String(e) 는 원문 칸(마지막 인자)으로만 — 본문 인자로 쓰지 않는다", () => {
    const bad = callLines.filter((l) => /String\((e|e2|err)\)/.test(l) && !/undefined, (String\((e|e2|err)\)|`\$\{String\(e\)\})/.test(l));
    expect(bad).toEqual([]);
  });
  it("템플릿 ${e} 로 원문을 본문 앞에 붙이는 알림 0", () => {
    expect(callLines.filter((l) => /\$\{(e|err|e2)\}/.test(l))).toEqual([]);
  });
  it("대표 경로 — 부서 완전 삭제·완전 초기화 실패(고위험 경보)는 원문을 「자세히」로 보존", () => {
    expect(main).toContain('stickyToast(failId, "watchdog", "부서 완전 삭제 실패", `${nm} 부서는 삭제되지 않았습니다. 다시 시도해 주세요.`, undefined, String(e));');
    expect(main).toContain("undefined, `${String(e)}\\n상태 확인: cys factory-reset --plan`);");
  });
});

describe("D4 #14 알림 문구 — 내부 용어 0 (1.1.8 U4: 앱 업데이트 확인 창·updateplan.ts 는 경로와 함께 지웠다 — 남은 교대 확인창·알림만 잰다)", () => {
  const strs = (src: string) => (src.match(/`[^`]*`|"[^"\n]*"/g) ?? []).join("\n");
  it("교대 확인창·진행 알림에 drain·CDHash·reinject 0 · 저장 안심 문장 있음(교대 확인창 1곳 — 옛 업데이트·맥 재시작 창 2곳은 삭제)", () => {
    const s = strs(callLines.join("\n"));
    for (const w of ["(drain)", "CDHash", "reinject", "미저장분"]) expect(`${w}: ${s.includes(w)}`).toBe(`${w}: false`);
    expect(main.split("저장 직전 몇 초 사이의 입력은 빠질 수 있습니다").length - 1).toBe(1);
  });
});
