// screensettings.test.ts — 「테마」 → 「화면 설정」 개편의 배선 핀(이름·글자 한 축·구획·상단 단추 적용) · TICKET=cysr-1110-screen-settings.
//
// 박사님 2026-10-12 원문: 「1. 현재 "테마" 메뉴의 글자들이 너무 작다. 지금의 2배 이상 키워야 제대로 볼 수 있다. 2. "테마"처럼 메뉴도
// 선택할 수 있게 하자. … 3. 메뉴 커스텀 기능은 "테마"에 한꺼번에 넣어 구현하는 것은 어떤가?」 → 09:1x 「최적안대로 한다.」
// 화면에서 실제로 재는 것(글자 px ≥ 25/20 · 화면 밖 0 · 숨김 5 · 토글 즉시 · 실제 마우스 끌기)은
// docs/screen-settings-evidence-2026-10-12/screen-settings-headless.ts. 여기는 그 동작을 만드는 소스 모양을 잰다
// (index.html · main.ts · style.css 를 데이터로 읽는다 — wswiring.test.ts 관례 · 주석 제거 본문 기준).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { TOPBAR_DEFAULT_OFF, TOPBAR_PINNED } from "./topbarlayout";

const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf8");
const html = read("../index.html");
const css = read("./style.css").replace(/\/\*[\s\S]*?\*\//g, "");
const main = read("./main.ts")
  .split("\n")
  .map((l) => (l.trimStart().startsWith("//") ? "" : l.replace(/\s\/\/.*$/, "")))
  .join("\n");
const top = html.slice(html.indexOf('<header id="topbar">'), html.indexOf("</header>"));
const rules = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({ sel: m[1].trim(), body: m[2] }));
const popRules = rules.filter((r) => r.sel.includes("#theme-pop"));
const pop = (() => {
  const i = main.indexOf("function openThemePopover(");
  return main.slice(i, main.indexOf("\n}\n", i));
})();

describe("이름·입구 — 「화면 설정」", () => {
  it("단추 글자 = 화면 설정 · title = 화면 설정 — 글자·배경·상단 단추 · id·자리(맨 끝) 그대로", () => {
    expect(top).toContain('<button id="btn-theme" title="화면 설정 — 글자·배경·상단 단추">화면 설정</button>');
    const ids = [...top.matchAll(/<button\b[^>]*?\bid="([^"]+)"/g)].map((m) => m[1]);
    expect(ids.at(-1)).toBe("btn-theme");
    expect(/>테마<\/button>/.test(html)).toBe(false);
    expect(main).toContain('document.getElementById("btn-theme")!.addEventListener("click", (e) =>');
  });

  it("팝오버 구획 3개 = 글자·배경 / 상단 단추 / 기본값 복원 · 제목 줄로 접는다", () => {
    const secs = [...pop.matchAll(/mkSection\("([a-z]+)", "([^"]+)"\)/g)].map((m) => [m[1], m[2]]);
    expect(secs).toEqual([["look", "글자·배경"], ["topbar", "상단 단추"], ["reset", "기본값 복원"]]);
    expect(pop).toContain("pop.append(look.sec, bar.sec, all.sec);");
    expect(pop).toContain("body.hidden = folded;");
    expect(pop).toContain('head.setAttribute("aria-expanded", String(!folded));');
  });

  it("① 글자·배경 = 종전 항목 8개 그대로(배경색·폰트·제목 크기·제목 굵기·제목=역할색·본문 굵기·메뉴 굵기·메뉴 크기)", () => {
    expect(pop).toContain("look.body.append(row, fontRow, titleSizeRow, titleWeightRow, titleColorRow, termWeightRow, menuWeightRow, menuSizeRow,");
    for (const t of ['"배경색"', '"폰트"', '"제목 크기"', '"제목 굵기"', '"제목=역할색"', '"본문 굵기"', '"메뉴 굵기"', '"메뉴 크기(%)"']) expect(pop).toContain(t);
  });

  it("③ 기본값 복원 = 두 구획을 한 번에 · 각 구획에도 「이 구획만」", () => {
    expect(pop).toContain('mkReset("모두 기본값으로 되돌리기", () => { resetLook(); resetBar(); })');
    expect((pop.match(/mkReset\("이 구획만 기본값으로", (resetLook|resetBar)\)/g) || []).length).toBe(2);
    // 상단 단추 기본값 = 저장을 지운다(다음 판의 기본값을 그대로 따른다)
    expect(pop).toContain("const resetBar = () => commitTb(defaultTopbarLayout(TOPBAR_DOM_IDS), null);");
  });
});

describe("글자 2배 — 한 축(20px × 메뉴 배율)", () => {
  const root = popRules.find((r) => r.sel === "#theme-pop")!;

  it("팝오버 글자 = calc(20px * var(--ui-chrome-scale)) — 기본 배율 1.25 → 25px(종전 12px 의 2배 이상)", () => {
    expect(root.body).toContain("font-size: calc(20px * var(--ui-chrome-scale));");
    expect(/--ui-chrome-scale:\s*1\.25;/.test(css)).toBe(true);
    expect((20 * 1.25) / 12).toBeGreaterThanOrEqual(2);
  });

  it("안쪽 부품은 그 글자를 물려받는다 — 팝오버 규칙 가운데 font-size 선언은 위 한 줄뿐(px 고정 글자 0)", () => {
    expect(popRules.length).toBeGreaterThan(15);
    expect(popRules.filter((r) => /font-size\s*:/.test(r.body)).map((r) => r.sel)).toEqual(["#theme-pop"]);
    const inherit = popRules.find((r) => r.sel.includes("#theme-pop button") && r.sel.includes("#theme-pop select") && r.sel.includes("#theme-pop input"))!;
    expect(inherit.body).toContain("font: inherit;");
    for (const r of popRules) expect(`${r.sel}: ${/(^|[;\s])font\s*:\s*\d/.test(r.body)}`).toBe(`${r.sel}: false`); // font: 12px … 축약 0
  });

  it("크기·여백도 같은 축(em) — 안쪽 규칙의 px 는 테두리·모서리·그림자뿐", () => {
    for (const r of popRules.filter((x) => x.sel !== "#theme-pop")) {
      for (const d of r.body.split(";").map((x) => x.trim()).filter(Boolean)) {
        const prop = d.slice(0, d.indexOf(":")).trim();
        if (/^(border|border-top|border-radius|box-shadow)$/.test(prop)) continue;
        expect(`${r.sel} { ${d} } px=${/\dpx/.test(d)}`).toBe(`${r.sel} { ${d} } px=false`);
      }
    }
    // main.ts 가 줄마다 px 폭을 박지 않는다(종전 입력 칸 56px 인라인)
    expect(/style\.width\s*=/.test(pop)).toBe(false);
    expect(/style\.fontSize\s*=/.test(pop)).toBe(false);
  });

  it("작은 창 = 팝오버 안 스크롤(화면 밖 0) — 폭·높이 상한 + overflow auto · 높이는 단추 아래 남은 만큼", () => {
    expect(root.body).toContain("max-width: calc(100vw - 8px);");
    expect(/max-height:\s*calc\(100vh - var\(--topbar-h\) - 8px\);\s*overflow:\s*auto;/.test(root.body)).toBe(true);
    // 최소 폭 = 256px × 배율(기본 320px) — 단 창 폭 안으로 접는다(codex 1R MED-1: 250% 의 640px 이 500px 창을 넘겼다)
    expect(root.body).toContain("min-width: min(calc(256px * var(--ui-chrome-scale)), calc(100vw - 8px));");
    expect(/min-width:\s*calc\(/.test(root.body)).toBe(false); // 창 폭을 모르는 맨 최소 폭 0
    expect(pop).toContain("pop.style.maxHeight = `${Math.max(80, window.innerHeight - r.bottom - 8)}px`;");
    expect(pop).toContain('window.addEventListener("resize", fitPop);');
    expect(pop).toContain('window.removeEventListener("resize", fitPop);');
    // 「메뉴 크기」 를 바꾸면 팝오버도 커지므로 자리를 다시 잡는다
    expect(pop).toContain('msInp.addEventListener("input", () => { applyMenuScale(msInp.value); fitPop(); });');
  });

  it("[hidden] 짝 규칙 — 접힌 구획 몸통 · 꺼진 상단 단추", () => {
    expect(rules.some((r) => r.sel === "#theme-pop .sp-sec-body[hidden]" && /display:\s*none/.test(r.body))).toBe(true);
    expect(rules.some((r) => r.sel === "#topbar > button[hidden]" && /display:\s*none/.test(r.body))).toBe(true);
  });
});

describe("상단 단추 — 적용·저장 배선", () => {
  const apply = (() => {
    const i = main.indexOf("function applyTopbarLayout(");
    return main.slice(i, main.indexOf("\n}\n", i));
  })();

  it("숨김 = hidden 속성(요소·누름 처리기 유지) · 순서 = 목록대로 끝에 다시 붙임 · 요소를 지우는 코드 0", () => {
    expect(apply).toContain("b.hidden = !it.on;");
    expect(apply).toContain("topbarEl.appendChild(b);");
    expect(/\.remove\(\)|removeChild|innerHTML|replaceChildren/.test(apply)).toBe(false);
  });

  it("저장 = localStorage cys-topbar-layout(TOPBAR_LAYOUT_KEY) · 기본값 복원 = 키 삭제 · 시작 시 복원은 저장을 다시 쓰지 않는다", () => {
    expect(apply).toContain("if (persist === null) localStorage.removeItem(TOPBAR_LAYOUT_KEY);");
    expect(apply).toContain("else if (persist) localStorage.setItem(TOPBAR_LAYOUT_KEY, serializeTopbarLayout(items));");
    expect(main).toContain("let topbarLayout: TopbarItem[] = parseTopbarLayout(topbarSavedRaw(), TOPBAR_DOM_IDS);");
    expect(main).toContain("\napplyTopbarLayout(topbarLayout, false);\n");
    // 저장 키를 글자로 따로 적은 곳 0(모듈 상수 한 곳)
    expect(main.includes('"cys-topbar-layout"')).toBe(false);
  });

  it("대상 = #topbar 바로 아래의 id 달린 단추 전부(목록을 코드에 따로 적지 않는다 — 새 단추가 저절로 든다)", () => {
    expect(main).toContain('[...topbarEl.querySelectorAll<HTMLButtonElement>(":scope > button[id]")].map((b) => b.id);');
    // 시작 적용이 기본 순서를 읽은 **뒤**에 온다(먼저 옮기면 「기본 순서」 가 사용자 순서로 오염된다)
    expect(main.indexOf("const TOPBAR_DOM_IDS")).toBeLessThan(main.indexOf("\napplyTopbarLayout(topbarLayout, false);"));
    expect(main.indexOf("const TOPBAR_DOM_IDS")).toBeGreaterThan(-1);
  });

  it("줄 = [≡ 손잡이][이름][▲][▼][켬/끔] · 토글은 누르는 즉시 적용+저장 · 고정 단추 토글 비활성", () => {
    expect(pop).toContain('r.append(grip, name, mkMove("tb-up", "▲", -1,');
    expect(pop).toContain('mkMove("tb-down", "▼", 1,');
    expect(pop).toContain('grip.textContent = "≡";');
    expect(pop).toContain('tog.setAttribute("role", "switch");');
    expect(pop).toContain('tog.textContent = it.on ? "켬" : "끔";');
    expect(pop).toContain("tog.disabled = pinned;");
    expect(pop).toContain("const pinned = isTopbarPinned(it.id);");
    expect(pop).toContain('tog.addEventListener("click", () => commitTb(setTopbarItemOn(topbarLayout, it.id, !it.on), true,');
    expect(pop).toContain("b.disabled = !canMoveTopbarItem(topbarLayout, it.id, delta);");
    expect(pop).toContain("commitTb(moveTopbarItem(topbarLayout, it.id, delta), true,");
    // commitTb = 적용(+저장) → 목록 다시 그림 → 팝오버 자리 다시
    const c = pop.slice(pop.indexOf("const commitTb ="), pop.indexOf("const renderTbList ="));
    expect(c.indexOf("applyTopbarLayout(next, persist);")).toBeGreaterThan(-1);
    expect(c.indexOf("applyTopbarLayout(next, persist);")).toBeLessThan(c.indexOf("renderTbList();"));
    expect(c).toContain("fitPop();");
    expect(pop).toContain("끌 수 없습니다"); // 안내 1줄
  });

  it("끌어 놓기 = 사이드바 순서 바꾸기 부품 재사용(삽입선·4px 임계·뒤따르는 click 삼킴) · 결과는 dropTopbarItem", () => {
    const i = main.indexOf("function startTopbarRowDrag(");
    const drag = main.slice(i, main.indexOf("\n}\n", i));
    for (const s of ["makeDropLine()", "placeDropLine(line!, r.left, before ? r.top : r.bottom, r.width);", "suppressNextClick()", 'document.body.classList.add("ws-reordering")', 'document.body.classList.remove("ws-reordering")', "line?.remove();", "< 4) return;"]) expect(drag).toContain(s);
    expect(drag).toContain("commit(dropTopbarItem(topbarLayout, srcId, drop.anchorId, drop.before));");
    expect(pop).toContain("startTopbarRowDrag(e, it.id, tbList, (next) => commitTb(next));");
    expect(/\.ws-drop-indicator\s*\{[^}]*z-index:\s*var\(--z-drop-indicator\)/.test(css)).toBe(true);
  });
});

// ── codex 1R(이종 적대검토 2026-10-12) 채택 4건의 핀 — 화면 동작은 실렌더 s13(좁은 창 250%) · s14(끌기 취소) · s15(저장 예외)가 잰다.
describe("codex 1R — 끌기 취소(MED-2) · 저장 예외(LOW)", () => {
  const drag = (() => {
    const i = main.indexOf("function startTopbarRowDrag(");
    return main.slice(i, main.indexOf("\n}\n", i));
  })();
  const apply = (() => {
    const i = main.indexOf("function applyTopbarLayout(");
    return main.slice(i, main.indexOf("\n}\n", i));
  })();

  it("취소는 순서를 저장하지 않는다 — cancel 본문에 commit 0 · 놓기(up)만 commit", () => {
    const cancel = drag.slice(drag.indexOf("const cancel = ("), drag.indexOf("const onBlur ="));
    expect(cancel.length).toBeGreaterThan(50);
    expect(cancel).toContain("teardown();");
    expect(/commit\(/.test(cancel)).toBe(false);
    expect((drag.match(/commit\(dropTopbarItem\(/g) || []).length).toBe(1);
    const up = drag.slice(drag.indexOf("const up = () => {"), drag.indexOf("const cancel = ("));
    expect(up).toContain("commit(dropTopbarItem(topbarLayout, srcId, drop.anchorId, drop.before));");
  });

  it("끝내기 공통(teardown) = 처리기 3개·삽입선·전역 표시·취소 손잡이를 모두 걷는다", () => {
    const td = drag.slice(drag.indexOf("const teardown = () => {"), drag.indexOf("const up = () => {"));
    for (const s of ['window.removeEventListener("mousemove", move, true);', 'window.removeEventListener("mouseup", up, true);', 'window.removeEventListener("blur", onBlur);', "cancelTopbarDrag = null;", "line?.remove();", 'document.body.classList.remove("ws-reordering");', 'classList.remove("tb-dragging")']) expect(td).toContain(s);
  });

  it("세 경로가 취소에 닿는다 — 팝오버 닫힘(Esc 포함)은 close() 첫 줄 · 창이 초점을 잃음은 blur 처리기", () => {
    const close = pop.slice(pop.indexOf("const close = () => {"), pop.indexOf("const dismiss ="));
    expect(close.indexOf('cancelTopbarDrag?.("close");')).toBeGreaterThan(-1);
    expect(close.indexOf('cancelTopbarDrag?.("close");')).toBeLessThan(close.indexOf("pop.remove();"));
    expect(/if \(e\.key === "Escape"\) close\(\);/.test(pop)).toBe(true);
    expect(drag).toContain('const onBlur = () => cancel("blur");');
    expect(drag).toContain('window.addEventListener("blur", onBlur);');
    expect(drag).toContain("cancelTopbarDrag = cancel;");
    // 닫힘으로 취소됐을 때만 다음 mouseup 뒤의 click 1회를 삼킨다(초점을 잃은 취소는 아무것도 남기지 않는다)
    expect(drag).toContain('if (wasDragging && why === "close") window.addEventListener("mouseup", () => suppressNextClick(), { capture: true, once: true });');
  });

  it("저장이 던져도 화면에는 끝까지 바른다 — DOM 적용이 저장보다 먼저 · 예외 = false · 읽기 예외 = 기본값", () => {
    expect(apply.indexOf("b.hidden = !it.on;")).toBeLessThan(apply.indexOf("try {"));
    expect(/try \{[\s\S]*localStorage\.setItem\(TOPBAR_LAYOUT_KEY[\s\S]*\} catch \{\s*return false;\s*\}\s*return true;/.test(apply)).toBe(true);
    expect(main).toContain("function applyTopbarLayout(items: TopbarItem[], persist: boolean | null): boolean {");
    const raw = main.slice(main.indexOf("function topbarSavedRaw()"), main.indexOf("let topbarLayout: TopbarItem[]"));
    expect(/try \{\s*return localStorage\.getItem\(TOPBAR_LAYOUT_KEY\);\s*\} catch \{\s*return null;/.test(raw)).toBe(true);
  });

  it("저장 실패 = 목록을 화면과 같게 다시 그리고 「저장되지 않았습니다」 1줄을 보인다(성공하면 숨긴다)", () => {
    const c = pop.slice(pop.indexOf("const commitTb ="), pop.indexOf("const renderTbList ="));
    expect(c.indexOf("const saved = applyTopbarLayout(next, persist);")).toBeGreaterThan(-1);
    expect(c.indexOf("renderTbList();")).toBeLessThan(c.indexOf("tbUnsaved.hidden = saved;"));
    expect(pop).toContain('const tbUnsaved = mkNote("⚠ 저장되지 않았습니다 — 지금 화면에는 반영됐지만, 앱을 다시 켜면 이전 상태로 돌아갑니다.");');
    expect(pop).toContain("tbUnsaved.hidden = true;");
    // 알림 줄에 display 를 주지 않는다(hidden 속성이 듣게)
    for (const r of rules.filter((x) => x.sel.includes(".sp-note"))) expect(/display\s*:/.test(r.body)).toBe(false);
  });
});

describe("codex 1R — 숨긴 「완전 초기화」 를 가리키는 안내(MED-3)", () => {
  // 기본 화면에는 「완전 초기화」 가 없다(끔 5) — 「상단바 단추를 누르라」 만 적으면 없는 단추를 가리킨다.
  // 네 곳 모두 켜는 길(화면 설정 → 상단 단추 → 완전 초기화)을 함께 적는다.
  const path = (s: string) => {
    const a = s.indexOf("화면 설정"), b = s.indexOf("상단 단추", a), c = s.indexOf("완전 초기화", b);
    return a >= 0 && b > a && c > b;
  };
  const line = (rel: string, needle: string) => {
    const lines = read(rel).split("\n");
    const i = lines.findIndex((l) => l.includes(needle));
    expect({ 파일: rel, 찾음: i >= 0 }).toEqual({ 파일: rel, 찾음: true });
    return lines.slice(i, i + 3).join("\n");
  };

  it("앱 토스트(새로 시작 대기 멈춤)", () => {
    const t = line("./main.ts", "기다림을 멈췄습니다(아무것도 바뀌지 않았습니다)");
    expect(path(t)).toBe(true);
    expect(read("./main.ts").includes("끝난 뒤 툴바의 [완전 초기화]를 눌러 주세요.\"")).toBe(false);
  });

  it("사용 설명서 2곳(§ 완전 초기화 · 문제 해결 표)", () => {
    const manual = read("../../USER-MANUAL.md");
    expect(path(line("../../USER-MANUAL.md", '되돌리려면 상단의 **완전 초기화** 버튼'))).toBe(true);
    expect(path(line("../../USER-MANUAL.md", "연습 흔적(부서·세션·기억)이 자꾸 살아나 충돌").split("\n")[0])).toBe(true);
    expect(manual.includes("topbar **완전 초기화** 버튼")).toBe(false);
  });

  it("깨끗이 지우기 안내(GUIDE-clean-reset-KR) 머리말", () => {
    expect(path(line("../../docs/GUIDE-clean-reset-KR.md", "이 문서 대신 앱 상단의 **완전 초기화** 버튼"))).toBe(true);
  });

  it("CLI 거부 안내(cysr factory-reset · 앱이 켜져 있을 때)", () => {
    const rs = line("../../src/bin/cys.rs", "지금 켜져 있는 cys 앱에서 하는 것이 가장 쉽다").split("\n")[0];
    expect(path(rs)).toBe(true);
    expect(read("../../src/bin/cys.rs").includes("상단바 '완전 초기화' 버튼을 쓰는 것이 가장 쉽다")).toBe(false);
  });
});

describe("숨겨도 기능은 남는다 — 기본 끔 5개의 누름 처리기·단축키", () => {
  it("끔 5개·고정 2개 모두 html 에 요소가 있고 main.ts 가 누름 처리기를 건다", () => {
    for (const id of [...TOPBAR_DEFAULT_OFF, ...TOPBAR_PINNED]) {
      expect(html.split(`id="${id}"`).length - 1).toBe(1);
      expect(main).toContain(`document.getElementById("${id}")!.addEventListener("click",`);
    }
    // html 이 hidden 을 미리 박지 않는다(끔은 저장·기본값을 읽은 main.ts 가 정한다 — html 에 박으면 켠 사람에게도 숨는다)
    expect(/<button\b[^>]*\bhidden\b/.test(top.replace(/"[^"]*"/g, '""'))).toBe(false);
  });

  it("단축키 ⌘T · ⌘D · ⌘⇧D · ⌘W 는 단추를 거치지 않는다(단추가 숨어도 동작)", () => {
    expect(/e\.key === "t"\) \{\s*e\.preventDefault\(\);\s*actionNew\(\);/.test(main)).toBe(true);
    expect(/e\.key === "d" && !e\.shiftKey\) \{\s*e\.preventDefault\(\);\s*actionSplit\("row"\);/.test(main)).toBe(true);
    expect(main).toContain('actionSplit("col");');
    expect(/e\.key === "w"\) \{/.test(main)).toBe(true);
    // 단축키 처리기가 상단 단추의 .click() 을 부르지 않는다
    for (const id of TOPBAR_DEFAULT_OFF) expect(main.includes(`getElementById("${id}")!.click()`) || main.includes(`getElementById("${id}")?.click()`)).toBe(false);
  });

  it("index.html 의 v116-recut-newsplit 주석이 새 보이는 길(화면 설정 토글)을 가리킨다", () => {
    const c = html.slice(html.indexOf("v116-recut-newsplit"), html.indexOf('<button id="btn-new"'));
    expect(c).toContain("cysr-1110-screen-settings");
    expect(c).toContain("화면 설정");
    expect(c).toContain("TOPBAR_DEFAULT_OFF");
    expect(c).toContain("⛔");
  });
});

describe("사용 설명서", () => {
  const manual = read("../../USER-MANUAL.md");
  it("상단 단추 켬끔·순서 안내 · 단추 이름 = 화면 설정(옛 이름으로 누르라는 안내 0)", () => {
    expect(manual).toContain("상단 단추는 `화면 설정` → 「상단 단추」에서 하나씩 켜고 끄고, 순서를 바꿉니다");
    expect(manual).toContain("처음에는 `+ New` · `Split →` · `Split ↓` · `창 닫기` · `완전 초기화` 가 꺼져 있습니다");
    expect(manual.includes("`테마` 버튼")).toBe(false);
  });
});
