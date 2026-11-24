// focusguard.test.ts — 살아 있는 가드 배선 핀 두 묶음(① setFocus 포커스 가드 · ② pane 드롭 리스너 첫 줄 가드).
// ★(1.1.19 · TICKET=cysr-1119-s10b · DESIGN §8-6 MD-X3) feedbackwiring.test.ts :85-122 에서 **그대로** 옮겼다(단언 무변경) — 그 파일이 함께 읽던
//   죽은 파일 셋(feedbackmodal.ts · feedback_u6.ts · feedbackflow.ts = 881줄 · import 0)을 지우기 전에 살아 있는 시험부터 옮긴다.
//   (소스를 데이터로 읽어 계약을 단언한다 · 런타임 코드 0줄 · DOM/Tauri 불요.)
import { describe, it, expect } from "bun:test";
import { existsSync, readdirSync, readFileSync } from "node:fs";

const read = (rel: string): string => readFileSync(new URL(rel, import.meta.url), "utf-8");
const main = read("./main.ts");
const css = read("./style.css");

/** 주석을 걷어낸 코드 본문(wswiring 과 같은 규칙) — 설명문이 핀을 속이지 못하게. */
const stripComments = (s: string): string =>
  s
    .split("\n")
    .map((l) => (l.trimStart().startsWith("//") ? "" : l.replace(/\s\/\/.*$/, "")))
    .join("\n");

/** `function name(` 부터 짝이 맞는 닫는 중괄호까지(문자열 속 중괄호는 이 파일들에서 쓰지 않는다). */
function fnBody(src: string, header: string): string {
  const a = src.indexOf(header);
  expect(a).toBeGreaterThanOrEqual(0); // 앵커가 사라졌다 = 핀이 아무것도 지키지 않는다
  const open = src.indexOf("{", a);
  let depth = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}") {
      depth--;
      if (depth === 0) return src.slice(a, i + 1);
    }
  }
  throw new Error(`unbalanced: ${header}`);
}

describe("① setFocus 포커스 가드 (반박 D2 · blocking)", () => {
  const body = stripComments(fnBody(main, "function setFocus(sid: number)"));
  it("term.focus() 는 모달 층 판정 뒤에서만 불린다 — 가드 줄은 글자 그대로(`|| true` 같은 무력화도 RED)", () => {
    const lines = body.split("\n").filter((l) => l.includes("term.focus()"));
    expect(lines.length).toBe(1);
    expect(lines[0].trim()).toBe("if (!modalLayerOpen(document)) panes.get(key)?.term.focus();");
    // xterm 포커스를 주는 곳은 파일 전체에서 이 한 줄뿐이다(다른 자리에서 우회하면 가드가 무의미).
    expect(stripComments(main).split("term.focus()").length - 1).toBe(1);
  });
  it("건너뛴 포커스는 모달이 닫힌 뒤 되살린다(리뷰 minor #3) — 가드 바로 다음 줄이 else 분기", () => {
    const lines = body.split("\n").map((l) => l.trim());
    const i = lines.indexOf("if (!modalLayerOpen(document)) panes.get(key)?.term.focus();");
    expect(i).toBeGreaterThanOrEqual(0);
    expect(lines[i + 1]).toBe("else deferPaneFocusUntilModalsClose();");
  });
  it("되살리기는 호이스팅되는 함수 선언이고 절대 던지지 않는다(setFocus·3초 틱 보호) — body 직계 자식만 지켜본다", () => {
    const fn = stripComments(fnBody(main, "function deferPaneFocusUntilModalsClose() {"));
    expect(/^function deferPaneFocusUntilModalsClose\(\) \{\s*try \{\s*armDeferredPaneFocus\(\{/.test(fn)).toBe(true);
    expect(fn).toContain("} catch {");
    expect(fn).toContain("layerOpen: () => modalLayerOpen(document),");
    expect(fn).toContain("return a == null || a === document.body;"); // 다른 칸이 가진 포커스는 빼앗지 않는다
    expect(fn).toContain("if (focusedSid != null) setFocus(focusedSid);");
    expect(fn).toContain("mo.observe(document.body, { childList: true });");
    expect(fn).toContain("return () => mo.disconnect();");
    expect(fn).toContain("later: (fn) => void setTimeout(fn, 0),"); // 닫는 키의 남은 이벤트가 pane 으로 가지 않게
    expect(/import \{[^}]*armDeferredPaneFocus[^}]*\} from "\.\/modalguard";/.test(main)).toBe(true);
  });
  it("focused 표시·focusedSid 갱신은 가드와 무관하게 유지된다(탭 강조가 사라지지 않게)", () => {
    expect(body).toContain("setFocusedSid(sid);"); // (cysr-1119-s7 SEL-1) 포커스 쓰기 한 입구 — 값 대입은 setFocusedSid 안 · (integ1) S10b 가 ①② 를 이 파일로 옮겨 S7 고침을 여기 옮겨 얹음
    expect(body).toContain('classList.toggle("focused"');
  });
  it("판정은 modalguard 모듈에서 들여온다(인라인 복제 금지)", () => {
    expect(/import \{[^}]*modalLayerOpen[^}]*\} from "\.\/modalguard";/.test(main)).toBe(true);
  });
});

describe("② pane 드롭 리스너 첫 줄 가드", () => {
  it("tauri://drag-drop pane 리스너의 첫 문장이 피드백 창 가드다", () => {
    const a = main.indexOf('await listen("tauri://drag-drop", (e) => {');
    expect(a).toBeGreaterThan(0);
    const firstStmt = stripComments(main.slice(a).split("\n").slice(1).join("\n"))
      .split("\n")
      .map((l) => l.trim())
      .find((l) => l.length > 0);
    // (1.1.8 병합 X17 · U6 휴면) 원작자 가드는 원작자 작성 창(.feedback-overlay — 창 안 드롭 = 첨부)이 떠 있을 때의 오배달을 막는다.
    //   우리 피드백 창(main.ts openFeedbackModal · 2단계)은 드롭 첨부가 없고 전체 덮개 .modal-overlay 를 쓴다 — 드롭 목적지는
    //   paneAtPointStrict(elementFromPoint → closest(".pane"))만 쓰므로 덮개 위 드롭은 pane 에 닿지 않는다(같은 목적 · 우리 배선 기준).
    expect(firstStmt).toBe("setOsDropTarget(undefined);");
    const body = stripComments(main.slice(a, main.indexOf("\n  });\n", a)));
    expect(body).toContain("const rt = paneAtPointStrict(p.position);");
    expect(body.split("injectPathsToPane(").length - 1).toBe(1);
    expect(body.indexOf("if (!rt) {")).toBeLessThan(body.indexOf("void injectPathsToPane(rt, paths);"));
    const sa = main.indexOf("function paneAtPointStrict(");
    expect(sa).toBeGreaterThan(0);
    const strict = stripComments(main.slice(sa, main.indexOf("\n}\n", sa)));
    expect(strict).toContain("document.elementFromPoint(css.x, css.y)");
    expect(strict).toContain('closest(".pane")');
    expect(/\.modal-overlay \{\s*position: fixed; inset: 0;/.test(css.replace(/\/\*[\s\S]*?\*\//g, ""))).toBe(true); // 덮개가 pane 을 가린다
    expect(main).toContain('ov.className = "modal-overlay";'); // 우리 피드백 창도 그 덮개를 쓴다
  });
});

// (1.1.19 · cysr-1119-s10b · DESIGN §8-6 MD-X3 합격 「import 0 원천 검사」) 죽은 파일 셋은 없고, 어느 화면 소스도 그 이름을 들여오지 않는다.
describe("MD-X3 — 죽은 U6 화면 파일 셋 삭제 · import 0", () => {
  const DEAD = ["feedbackmodal", "feedback_u6", "feedbackflow"];
  const walk = (dir: URL): string[] =>
    readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
      e.isDirectory() ? walk(new URL(`${e.name}/`, dir)) : e.name.endsWith(".ts") ? [new URL(e.name, dir).href] : [],
    );
  it("파일 셋(+ 그 파일만 보던 시험 둘)이 없다", () => {
    for (const n of [...DEAD, "feedback_u6.test", "feedbackflow.test"]) expect({ n, 있음: existsSync(new URL(`./${n}.ts`, import.meta.url)) }).toEqual({ n, 있음: false });
  });
  it("ui/src 의 모든 .ts 가 그 셋을 import 하지 않는다(정적 import · 동적 import · require)", () => {
    const files = walk(new URL("./", import.meta.url));
    expect(files.length).toBeGreaterThan(100); // 훑기가 실제로 돈다
    const hits: string[] = [];
    for (const f of files) {
      const src = readFileSync(new URL(f), "utf-8");
      for (const n of DEAD) if (new RegExp(`(from|import\\(|require\\()\\s*["'][./]*${n}["']`).test(src)) hits.push(`${f.split("/src/")[1]} → ${n}`);
    }
    expect(hits).toEqual([]);
  });
});
