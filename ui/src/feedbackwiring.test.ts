// U6(0.14.41) 피드백 **배선** 회귀 핀 — 소스를 데이터로 읽어 계약을 단언한다
// (wswiring.test.ts 관례: 런타임 코드 0줄 · 본체에서 import 되지 않는다 · DOM/Tauri 불요).
//
// 판정 모듈(modalguard·feedback)이 옳아도 main.ts 가 그것을 부르지 않으면 결함은 그대로 산다.
// 여기 실패는 "고쳐 두었다고 믿는 것이 코드에 없다"는 뜻이다.
import { describe, it, expect } from "bun:test";
// (1.1.8 병합 UNW · master#c6a9de68) 휴면·미수용 기능의 배선 시험 묶음 — 휴면-on 레인(CYS_UI_DORMANT_LANE=1)에서만 돈다(삭제·무조건 skip 0 · 기본 CI 미실행 · BACKLOG 「휴면-on CI 레인 = 1.1.9」).
const itDormant = it.if((globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env?.CYS_UI_DORMANT_LANE === "1");
import { readFileSync } from "node:fs";

const read = (rel: string): string => readFileSync(new URL(rel, import.meta.url), "utf-8");
const main = read("./main.ts");
const html = read("../index.html");
const css = read("./style.css");
const guardSrc = read("./modalguard.ts");
const mainRs = read("../../src-tauri/src/main.rs");
const fbRs = read("../../src-tauri/src/feedback.rs");

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

/**
 * 모듈 최상위(괄호 깊이 0) **문장**들 — '최상위 부수효과 0' 판정용. 여러 줄에 걸친 상수 초기화
 * (`const X = "…" +\n "…";`)는 한 문장이다. 문장 경계 = 깊이 0 의 `;` 또는 줄 끝에서 깊이 0 으로 돌아오는 `}`.
 * 함수·클래스 본문(깊이 > 0)은 모으지 않는다 — 그 안의 호출은 부수효과가 아니라 정의다.
 */
function topLevelStatements(src: string): string[] {
  const code = stripComments(src)
    .split("\n")
    .map((l) => l.replace(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`/g, '""'))
    .join("\n")
    .replace(/\/\*[\s\S]*?\*\//g, ""); // 블록 주석(JSDoc) — 문자열을 걷은 뒤라 문자열 속 `/*` 에 속지 않는다
  const out: string[] = [];
  let depth = 0;
  let cur = "";
  const flush = () => {
    const t = cur.replace(/\s+/g, " ").trim();
    if (t && t !== ";") out.push(t);
    cur = "";
  };
  for (let i = 0; i < code.length; i++) {
    const ch = code[i];
    if (ch === "{" || ch === "(" || ch === "[") {
      if (depth === 0) cur += ch;
      depth++;
    } else if (ch === "}" || ch === ")" || ch === "]") {
      depth--;
      if (depth === 0) {
        cur += ch;
        // 줄 끝에서 닫히는 `}` 만 문장 끝(함수·인터페이스 선언). `import { a } from` 의 `}` 는 아니다.
        if (ch === "}" && /^[ \t]*(\n|$)/.test(code.slice(i + 1, i + 40))) flush();
      }
    } else if (depth === 0) {
      cur += ch;
      if (ch === ";") flush();
    }
  }
  flush();
  return out;
}

// ★(1.1.19 · cysr-1119-s10b MD-X3) ①②(살아 있는 가드) = focusguard.test.ts 로 옮김 · ③④(원작자 U6 작성 창 · 휴면 배선) = 대상 파일과 함께 지움.

describe("⑤ 새 모듈 위생", () => {
  // (1.1.19 · cysr-1119-s10b MD-X3) 죽은 U6 화면 파일 셋(feedback_u6 · feedbackmodal · feedbackflow)은 지웠다 — 살아 있는 modalguard.ts 만 잰다.
  const mods: [string, string][] = [["modalguard.ts", guardSrc]];
  it("최상위 부수효과 0 — 최상위 문장은 import·선언만", () => {
    for (const [name, src] of mods) {
      const stmts = topLevelStatements(src);
      expect(stmts.length).toBeGreaterThan(3); // 수집기가 아무것도 못 봤다 = 핀이 무력
      for (const st of stmts) {
        const ok = /^(import |export |const |let |function |async function |type |interface |declare )/.test(st);
        expect(`${name}: ${ok ? "ok" : st}`).toBe(`${name}: ok`);
        const fx = /\b(document|window|navigator)\.|setInterval\(|setTimeout\(|addEventListener\(|listen\(|invoke\(/.test(st);
        expect(`${name}: ${fx ? st : "no-fx"}`).toBe(`${name}: no-fx`);
      }
    }
  });
  it("수집기 자기검증 — 최상위 호출·DOM 접근을 실제로 잡는다", () => {
    const bad = 'import { a } from "./x";\nconst A = "x" +\n  "y";\nfunction f() {\n  document.body;\n}\nf();\nconst B = document.getElementById("z");\n';
    const st = topLevelStatements(bad);
    expect(st).toContain("f();");
    expect(st.some((x) => x.startsWith("const B") && x.includes("document."))).toBe(true);
    expect(st.some((x) => x.includes("document.body"))).toBe(false); // 함수 본문은 정의
  });
  it("구형 WKWebView 비호환 문법 0", () => {
    for (const [name, src] of mods) {
      const code = stripComments(src);
      for (const bad of ["(?<=", "(?<!", ".at(", "findLast", "structuredClone", "Object.hasOwn", "replaceAll("]) {
        expect(`${name}:${code.includes(bad) ? bad : ""}`).toBe(`${name}:`);
      }
    }
  });
});

// (1.1.8 병합 X17·T2) src-tauri/src/feedback.rs = 우리 본체(2단계 업로드 · 등록된 명령) + 원작자 1단계 판 `pub mod u6_local_bundle { … }`(휴면 · 명령 미등록).
//   원작자 단언(1단계 판의 계약)은 그 하위 모듈에 그대로 걸고, 우리 본체에는 같은 목적(등록 누락 0 · 윈도우 검은 창 0)을 우리 배선 기준으로 건다.
const U6_HEAD = "pub mod u6_local_bundle {";
const ourRsRaw = fbRs.slice(0, Math.max(0, fbRs.indexOf(U6_HEAD)));
const u6RsRaw = fbRs.slice(Math.max(0, fbRs.indexOf(U6_HEAD)));
const cmdsOf = (src: string): string[] => [...src.matchAll(/#\[tauri::command\]\s*(?:pub(?:\(crate\))? )?(?:async )?fn ([a-z_]+)/g)].map((m) => m[1]);

describe("⑥ Rust 배선 — 등록·창 정책·전송 부재", () => {
  const rs = stripComments(u6RsRaw);
  const cmdNames = cmdsOf(u6RsRaw);
  it("feedback.rs 의 모든 커맨드가 invoke_handler 에 등재된다(누락 = 런타임 'command not found')", () => {
    expect(fbRs.includes(U6_HEAD)).toBe(true);
    // 우리 본체(살아 있는 명령) — 전부 등재
    const ours = cmdsOf(ourRsRaw);
    expect(ours.length).toBeGreaterThan(5);
    for (const n of ours) {
      expect(n.startsWith("feedback_")).toBe(true);
      expect(`${n}:${mainRs.includes(`feedback::${n},`)}`).toBe(`${n}:true`);
    }
    // 원작자 1단계 판(휴면 · T2) — 명령이 있어도 등재하지 않는다(이름 충돌 feedback_submit·feedback_discard 포함 · 배선은 박사님 게이트)
    expect(cmdNames.length).toBeGreaterThan(5);
    for (const n of cmdNames) {
      expect(n.startsWith("feedback_")).toBe(true);
      expect(`${n}:${mainRs.includes(`feedback::u6_local_bundle::${n}`)}`).toBe(`${n}:false`);
    }
    expect(/^mod feedback;/m.test(mainRs)).toBe(true);
  });
  it("자식 프로세스를 만드는 함수는 전부 창 정책(no_console)을 건다 — 윈도우 검은 창 0", () => {
    // 우리 본체: 창 정책은 cys::SpawnPolicy(spawn_policy — Windows 콘솔 정책 포함) 경유 · 맥 전용 screencapture 는 윈도우에서 돌지 않는다(capture_supported 가 먼저 거른다).
    for (const c of stripComments(ourRsRaw).split(/\n(?=(?:pub(?:\(crate\))? )?(?:async )?fn )/)) {
      if (!c.includes("Command::new(")) continue;
      const ok = c.includes("spawn_policy(") || (c.includes('Command::new("/usr/sbin/screencapture")') && c.includes("capture_supported()"));
      expect(`${c.slice(0, 60)}:${ok}`).toBe(`${c.slice(0, 60)}:true`);
    }
    const chunks = rs.split(/\n(?=(?:pub(?:\(crate\))? )?(?:async )?fn )/);
    let spawners = 0;
    for (const c of chunks) {
      if (c.includes("Command::new(")) {
        spawners++;
        expect(c).toContain("no_console(&mut");
      }
    }
    expect(spawners).toBeGreaterThan(0);
  });
  // (1.1.8 병합) 이 단언은 원작자 1단계 판(u6_local_bundle) 에 건다 — 우리 본체는 2단계(서버 업로드 · cys-feedback-menu)라 전송이 설계다.
  it("서버 전송 없음(2단계 전까지) — curl·http·데몬 소켓 호출 0", () => {
    for (const bad of ['"curl"', "reqwest", "http://", "https://", "rpc_on(", "connect_to(", "send_text", "cmd.exe", '"cmd"', "rundll32"]) {
      expect(`${bad}:${rs.includes(bad)}`).toBe(`${bad}:false`);
    }
  });
  it("받는 주소는 README·SECURITY 의 공식 연락 주소와 같고 상수 한 곳에만 있다", () => {
    const readme = read("../../README.md");
    const security = read("../../SECURITY.md");
    const m = fbRs.match(/pub const FEEDBACK_TO: &str = "([^"]+)";/);
    expect(m).not.toBeNull();
    const addr = (m as RegExpMatchArray)[1];
    expect(readme).toContain(addr);
    expect(security).toContain(addr);
    expect(fbRs.split(addr).length - 1).toBe(1); // 상수 정의 1곳
    expect(main.includes(addr)).toBe(false); // UI 는 Rust 보고에서 받는다(1.1.19: 옛 U6 창 파일 대신 우리 main.ts 를 본다)
  });
});
