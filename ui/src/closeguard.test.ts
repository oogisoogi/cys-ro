// closeguard.test.ts — 창 닫기 보호(D4 #7) · 남은 창 폭(X-1) · 창 만들기 이동(권고 C) 회귀 · TICKET=v116-ui-close.
//
// 실기 맥락: 박사님 09-23 「exited 페인 닫다가 실수로 작업 중 페인을 닫았다」(2회). 상단 Close·⌘W·팔레트
// 「패널 닫기」가 확인 없이 포커스 창을 바로 강제 종료했다(창 머리 × 만 두 번 눌러야 닫혔다).
// 화면 동작 자체(확인 창 1개 · 기본 포커스 = 취소 · 남은 창 폭)는 docs/v116-ui-evidence/v116-headless.ts 가
// 실번들로 잰다. 여기는 판정 진리표 + 배선이 그 판정을 지나는지(소스 대조)를 잰다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import {
  CLOSE_CONFIRM_POLICY,
  CLOSE_CONFIRM_TEXT,
  CLOSE_NAME_MAX,
  closeConfirmBody,
  needsCloseConfirm,
} from "./closeguard";
import { INTERNAL_TERMS } from "./restorebrief";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

describe("닫기 확인 판정 — 진리표", () => {
  it("권고 A(live-only): exited 확정만 묻지 않는다 · 산 창·모름은 묻는다", () => {
    expect(needsCloseConfirm("live-only", true)).toBe(false);
    expect(needsCloseConfirm("live-only", false)).toBe(true);
    expect(needsCloseConfirm("live-only", null)).toBe(true); // 모르면 묻는 쪽(fail-closed)
  });

  it("B(all): exited 창까지 모두 묻는다 — A-1 답이 B 면 상수 한 줄만 바꾼다", () => {
    expect(needsCloseConfirm("all", true)).toBe(true);
    expect(needsCloseConfirm("all", false)).toBe(true);
    expect(needsCloseConfirm("all", null)).toBe(true);
  });

  it("현재 정책 = 권고 A(박사님 A-1 답 전까지)", () => {
    expect(CLOSE_CONFIRM_POLICY).toBe("live-only");
  });
});

describe("닫기 확인 문안 — 공개 문구 규율", () => {
  it("창 이름을 넣고, 길면 자르고, 비면 「이 창」으로 말한다", () => {
    expect(closeConfirmBody("3 · worker1")).toContain("「3 · worker1」 창은 아직 켜져 있어요.");
    const long = "가".repeat(CLOSE_NAME_MAX + 10);
    const b = closeConfirmBody(long);
    expect(b).toContain("…");
    expect(b).not.toContain(long);
    expect(closeConfirmBody("  ")).toContain("이 창은 아직 켜져 있어요.");
    expect(closeConfirmBody(null)).not.toContain("{name}");
  });

  it("내부 용어·위협 표현·영어 0 — 문안 전문을 훑는다", () => {
    const all = [CLOSE_CONFIRM_TEXT.title, closeConfirmBody(""), CLOSE_CONFIRM_TEXT.yes, CLOSE_CONFIRM_TEXT.no].join("\n");
    for (const t of INTERNAL_TERMS) expect(all.toLowerCase()).not.toContain(t.toLowerCase());
    for (const t of ["강제", "종료", "삭제", "위험", "경고", "영구", "되돌릴 수 없"]) expect(all).not.toContain(t);
    expect(/[A-Za-z]/.test(all)).toBe(false);
  });
});

describe("닫기 배선 — 세 입구가 모두 판정을 지난다", () => {
  const fn = main.slice(main.indexOf("async function actionClose() {"));
  const body = fn.slice(0, fn.indexOf("\n}\n") + 3);

  it("actionClose 는 close_surface 보다 앞에서 판정·확인 창을 거친다", () => {
    const judge = body.indexOf("needsCloseConfirm(CLOSE_CONFIRM_POLICY,");
    const ask = body.indexOf("await confirmModal(CLOSE_CONFIRM_TEXT.title");
    const close = body.indexOf('invoke("close_surface"');
    expect(judge).toBeGreaterThan(-1);
    expect(ask).toBeGreaterThan(judge);
    expect(close).toBeGreaterThan(ask);
    expect(body.split('invoke("close_surface"').length - 1).toBe(1); // 우회 닫기 경로 0
  });

  it("취소면 닫지 않고, 묻는 사이 그 창이 사라졌으면 다른 창을 닫지 않는다", () => {
    expect(body).toContain("if (!ok) return;");
    const recheck = body.indexOf("if (!ws.tree || !collectSids(ws.tree).includes(sid)) return;");
    expect(recheck).toBeGreaterThan(body.indexOf("if (!ok) return;"));
    // 낡은 포커스(이 탭에 없는 창)는 처음부터 닫지 않는다
    expect(body.indexOf("if (!collectSids(ws.tree).includes(sid)) return;")).toBeLessThan(body.indexOf("needsCloseConfirm("));
  });

  it("확인 창 겹침 0 — 진행 중 플래그", () => {
    expect(body).toContain("if (closeConfirmOpen) return;");
    expect(body).toMatch(/finally \{\s*closeConfirmOpen = false;/);
  });

  it("상단 Close · ⌘W · 팔레트 「패널 닫기」가 모두 actionClose 다", () => {
    expect(main).toContain('document.getElementById("btn-close")!.addEventListener("click", actionClose);');
    expect(main).toMatch(/e\.key === "w"\) \{\s*e\.preventDefault\(\);\s*actionClose\(\);/);
    expect(main).toContain('{ id: "act:close", title: "패널 닫기", keywords: "close 닫기", action: () => actionClose() }');
  });

  it("exited 판정 재료 = 데몬 목록의 exited 하나뿐 — 스트림 종료 이벤트로는 넣지 않는다", () => {
    const adds = main.split("exitedPaneKeys.add(").length - 1;
    expect(adds).toBe(1);
    expect(main).toContain("if (s.exited) exitedPaneKeys.add(paneKey(s.surface_id, sk));");
    // 스트림 종료 처리기(= 연결 끊김에도 발화) 안에는 없다
    const ex = main.indexOf("const un2 = await listen(ev.exited_event");
    expect(main.slice(ex, main.indexOf("});", ex))).not.toContain("exitedPaneKeys");
  });

  it("창 머리 × 는 무변경(두 번 눌러 닫기 · 판정 미사용)", () => {
    const x = main.indexOf('closeBtn.addEventListener("click", async () => {');
    const xBody = main.slice(x, main.indexOf("header.append(roleEl", x));
    expect(xBody).toContain('closeBtn.dataset.arm !== "1"');
    expect(xBody).not.toContain("needsCloseConfirm");
  });
});

describe("X-1 남은 창 폭 — 루트 직계의 인라인 flex 를 지운다", () => {
  it("render() 가 루트에 붙이는 요소의 style.flex 를 비운 뒤 붙인다", () => {
    const r = main.slice(main.indexOf("function render() {"));
    const rBody = r.slice(0, r.indexOf("\n}\n"));
    const clear = rBody.indexOf('top.style.flex = "";');
    const append = rBody.indexOf("root.appendChild(top);");
    expect(clear).toBeGreaterThan(-1);
    expect(append).toBeGreaterThan(clear);
  });

  it("스타일시트가 루트 직계 폭을 정한다는 전제(#root > * {flex:1})가 살아 있다", () => {
    const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
    expect(css).toMatch(/#root > \* \{ flex: 1;/);
  });
});

describe("권고 C — 창 만들기는 상단에서 빠지고 전문가 칸에", () => {
  it("상단바에 + New · Split → · Split ↓ 단추가 없다", () => {
    const top = html.slice(html.indexOf('<header id="topbar">'), html.indexOf("</header>"));
    for (const id of ["btn-new", "btn-split-h", "btn-split-v"]) expect(top).not.toContain(`id="${id}"`);
    expect(top).not.toMatch(/>\s*(\+ New|Split →|Split ↓)\s*</);
    expect(top).toContain('id="btn-close"'); // 닫기는 남는다(확인 1회를 거친다)
  });

  it("전문가 칸(기본 숨김) 안에 「창 만들기」 단추 1개", () => {
    expect(html).toMatch(/<div id="ws-expert" hidden>[\s\S]*?id="btn-pane-create"[^>]*>창 만들기<\/button>[\s\S]*?<\/div>/);
  });

  it("누르면 오른쪽/아래 두 갈래 — 종전 Split 과 같은 함수 · 단축키 유지", () => {
    const w = main.indexOf('document.getElementById("btn-pane-create")!');
    const wBody = main.slice(w, main.indexOf("});", w));
    expect(wBody).toContain('label: "오른쪽에 새 창 (⌘D)", action: () => void actionSplit("row")');
    expect(wBody).toContain('label: "아래에 새 창 (⌘⇧D)", action: () => void actionSplit("col")');
    expect(main).toMatch(/e\.key === "t"\) \{\s*e\.preventDefault\(\);\s*actionNew\(\);/);
    expect(main).toMatch(/e\.key === "d" && !e\.shiftKey\) \{\s*e\.preventDefault\(\);\s*actionSplit\("row"\);/);
    expect(main).toContain('actionSplit("col");');
    // 지운 단추를 여전히 붙잡는 배선이 남으면 앱 시작에서 널 역참조로 죽는다
    for (const id of ["btn-new", "btn-split-h", "btn-split-v"]) expect(main).not.toContain(`getElementById("${id}")`);
  });
});
