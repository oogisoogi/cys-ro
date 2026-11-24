// (TICKET=cysr-1119-s6 · V1) 마크다운 나무 시험 — DESIGN §6 V1 합격 칸(견본 20종 · 글자 손실 0 · 같은 입력 같은 나무 · 64KB 넘음 · 1MB 시간).
// 마스터 답 = 믿지 못할 글. 나무는 글 조각(문자열)만 담고, 그리기(chat/md.ts)는 그 글을 textContent 로만 넣는다.
import { describe, expect, it } from "bun:test";
import { MD_MAX, parseMd, type Block, type Inline, type Item } from "./md";
import { readFileSync } from "node:fs";

/** 그리기와 같은 규칙으로 나무 → 보이는 글(링크 = 「글 (주소)」 · 순서 목록 = 적힌 번호 · 항목 안 울타리·문단 = 줄을 바꿔 이어 붙임). */
const inl = (c: Inline[]): string =>
  c.map((n) => (n.k === "text" || n.k === "code" ? n.v : n.k === "link" ? `${inl(n.c)} (${n.url})` : inl(n.c))).join("");
const more = (it: Item): string => it.more.map((m) => `\n${m.k === "pre" ? m.v : inl(m.c)}`).join("");
const text = (bs: Block[]): string =>
  bs
    .map((b) =>
      b.k === "h" || b.k === "p" ? inl(b.c)
      : b.k === "pre" || b.k === "raw" ? b.v
      : b.k === "list" ? b.items.map((it) => (it.num ?? "") + inl(it.c) + more(it)).join("\n")
      : [b.head, ...b.rows].map((r) => r.map(inl).join(" ")).join("\n"),
    )
    .join("\n");

/**
 * (fix-1119-s6-adv M5) 글자 손실 0 = 「파서가 서식 표지로 쓴 글자만」 뺀다 — 나무를 표지 원문(m·n·f·info·end·mark)까지 넣어 다시 쓰고(ser)
 * 빈칸만 걷어 원문과 견준다. 기호를 통째로 지우지 않으므로 역빗금·밑줄·별표·들여쓰기 아닌 글자 하나라도 빠지면 붉다.
 * 걷는 것 = 빈칸 · 표 구분 줄(두 쪽 다 줄째) · 탈출 안 된 「|」(표 칸 가름 · 두 쪽 다).
 */
const sInl = (c: Inline[]): string =>
  c.map((n) => (n.k === "text" ? n.v : n.k === "code" ? "`".repeat(n.n) + n.v + "`".repeat(n.n) : n.k === "link" ? `[${sInl(n.c)}](${n.url})` : n.m + sInl(n.c) + n.m)).join("");
const sPre = (b: { v: string; f: string; info: string; end: string }) => `${b.f}${b.info}\n${b.v}\n${b.end}`;
const ser = (bs: Block[]): string =>
  bs
    .map((b) =>
      b.k === "h" ? `${"#".repeat(b.level)} ${sInl(b.c)} ${b.end}`
      : b.k === "p" ? sInl(b.c)
      : b.k === "pre" ? sPre(b)
      : b.k === "raw" ? b.v
      : b.k === "list" ? b.items.map((it) => `${it.mark} ${sInl(it.c)}${it.more.map((m) => `\n${m.k === "pre" ? sPre(m) : sInl(m.c)}`).join("")}`).join("\n")
      : [b.head, ...b.rows].map((r) => `|${r.map((c) => sInl(c).replace(/\|/g, "\\|")).join("|")}|`).join("\n"),
    )
    .join("\n");
const DELIM_LINE = /^ {0,3}\|?[ \t]*:?-+:?(?:[ \t]*\|[ \t]*:?-+:?)*[ \t]*\|?[ \t]*$/;
const norm = (s: string): string =>
  s
    .split(/\r\n|\r|\n|\u2028|\u2029/)
    .filter((l) => !(l.includes("|") && DELIM_LINE.test(l)))
    .join("\n")
    .replace(/(?<!\\)\|/g, "")
    .replace(/\s+/g, "");
const lossless = (src: string): string => (norm(ser(parseMd(src))) === norm(src) ? "ok" : `손실: ${norm(src)} → ${norm(ser(parseMd(src)))}`);

/** 견본 20종 — 제목·목록·표·코드·섞임·깨진 표·닫히지 않은 울타리·스크립트·이벤트 속성·위험 주소·그림·HTML 꼴(e2e md_gate.py 와 같은 파일). */
const SAMPLES = JSON.parse(readFileSync(new URL("../md_samples.json", import.meta.url), "utf8")) as Array<[string, string]>; // URL 그대로(윈 pathname ENOENT 전례)

const find = (bs: Block[], k: Block["k"]) => bs.filter((b) => b.k === k);

describe("V1 — 마크다운 나무(순수)", () => {
  it("견본 20종 = 글자 손실 0(입력 글자 = 출력 글자 − 파서가 쓴 표지)", () => {
    expect(SAMPLES.length).toBe(20);
    for (const [name, src] of SAMPLES) expect(`${name}: ${lossless(src)}`).toBe(`${name}: ok`);
  });

  it("같은 입력 → 같은 나무(순수 · 두 번 불러도 같음)", () => {
    for (const [, src] of SAMPLES) expect(JSON.stringify(parseMd(src))).toBe(JSON.stringify(parseMd(src)));
  });

  it("01 제목 = h1~h3 만 · h4+·붙은 샵 = 글 그대로", () => {
    const bs = parseMd(SAMPLES[0][1]);
    expect(find(bs, "h").map((b) => (b.k === "h" ? [b.level, inl(b.c)] : null))).toEqual([[1, "큰 제목"], [2, "중간 제목"], [3, "작은 제목"]]);
    expect(text(find(bs, "p"))).toBe("#### 넷째는 글 그대로\n#붙은 샵은 글");
  });

  it("03 굵게·기울임 · 낱말 안 밑줄·빈칸 둔 별표 = 글", () => {
    const [p] = parseMd(SAMPLES[2][1]);
    expect(p.k).toBe("p");
    const c = p.k === "p" ? p.c : [];
    expect(c.filter((n) => n.k === "strong").map((n) => inl([n]))).toEqual(["굵게", "밑줄 굵게"]);
    expect(c.filter((n) => n.k === "em").map((n) => inl([n]))).toEqual(["기울임", "밑줄 기울임", "a b c"]);
    const last = c[c.length - 1];
    expect(last.k === "em" && last.c.some((n) => n.k === "strong")).toBe(true); // *a **b** c* = 기울임 안 굵게
    expect(inl(c)).toContain("snake_case_name 그대로 · 2 * 3 * 4 = 24");
  });

  it("04 인라인 코드 = 글 그대로 · 닫히지 않은 백틱 = 글", () => {
    const [p] = parseMd(SAMPLES[3][1]);
    const c = p.k === "p" ? p.c : [];
    expect(c.filter((n) => n.k === "code").map((n) => (n.k === "code" ? n.v : ""))).toEqual(["npm install", "a`b"]);
    expect(inl(c)).toContain("닫히지 않은 `백틱 하나");
  });

  it("05·06 울타리 = 안의 글 해석 0 · 언어 이름 버림 · 닫히지 않으면 끝까지", () => {
    const b5 = parseMd(SAMPLES[4][1]);
    expect(b5.map((b) => b.k)).toEqual(["pre", "p"]);
    expect(b5[0].k === "pre" && b5[0].v).toBe("const a = '<b>x</b>';\n**굵게 아님** [링크 아님](https://example.invalid)");
    const b6 = parseMd(SAMPLES[5][1]);
    expect(b6.map((b) => b.k)).toEqual(["p", "pre"]);
    expect(b6[1].k === "pre" && b6[1].v).toBe("코드 1\n코드 2");
  });

  it("07·08 목록 = 한 단 들여쓰기까지(더 깊어도 1) · 적힌 번호 그대로 · 이어진 줄은 그 항목", () => {
    const [l] = parseMd(SAMPLES[6][1]);
    expect(l.k).toBe("list");
    if (l.k !== "list") return;
    expect(l.ordered).toBe(false);
    expect(l.items.map((i) => [i.depth, i.num, inl(i.c)])).toEqual([[0, null, "하나"], [0, null, "둘 굵게"], [1, null, "들여쓴 셋"], [1, null, "더 깊은 넷"], [0, null, "별 다섯"], [0, null, "더하기 여섯\n이어진 줄"]]);
    const [o] = parseMd(SAMPLES[7][1]);
    expect(o.k === "list" && o.ordered && o.items.map((i) => [i.num, inl(i.c)])).toEqual([["1.", "첫째"], ["2.", "둘째"], ["10)", "열째"]]);
  });

  it("09·10·11 표 = 구분 줄 있을 때만 · 칸 수 달라도 글 손실 0 · 탈출 파이프", () => {
    const [t] = parseMd(SAMPLES[8][1]);
    expect(t.k).toBe("table");
    if (t.k !== "table") return;
    expect(t.head.map(inl)).toEqual(["이름", "값"]);
    expect(t.rows.map((r) => r.map(inl))).toEqual([["a", "1"], ["b", "2 | 3"]]);
    expect(parseMd(SAMPLES[9][1]).map((b) => b.k)).toEqual(["p"]); // 구분 줄 없음 = 글
    const b11 = parseMd(SAMPLES[10][1]);
    expect(b11.map((b) => b.k)).toEqual(["table", "p"]);
    expect(b11[0].k === "table" && b11[0].rows.map((r) => r.map(inl))).toEqual([["1", "2", "3"], ["4"]]);
  });

  it("12 섞임 = 제목·문단·목록·표·울타리·문단 순서", () => {
    expect(parseMd(SAMPLES[11][1]).map((b) => b.k)).toEqual(["h", "p", "list", "table", "pre", "p"]);
  });

  it("13·14·18 HTML 꼴 = 글 그대로(요소로 바뀌는 길 없음 · 나무에 태그 칸 자체가 없음)", () => {
    for (const i of [12, 13, 17]) {
      const bs = parseMd(SAMPLES[i][1]);
      expect(bs.every((b) => b.k === "p")).toBe(true);
      expect(text(bs)).toBe(SAMPLES[i][1]);
    }
  });

  it("15·16·17 링크 = 「글 (주소)」 글 조각뿐 · 그림 = 원문 글 그대로 · 자동·맨 주소 = 글", () => {
    const links = (s: string) => parseMd(s).flatMap((b) => (b.k === "p" ? b.c.filter((n) => n.k === "link") : []));
    expect(links(SAMPLES[14][1]).map((n) => (n.k === "link" ? n.url : ""))).toEqual(["javascript:window.__pwn=1", "JaVaScRiPt:alert(1)", "vbscript:msgbox(1)"]);
    expect(links(SAMPLES[15][1]).map((n) => (n.k === "link" ? n.url : ""))).toEqual(["data:text/html;base64,PHNjcmlwdD4="]);
    expect(text(parseMd(SAMPLES[15][1]))).toContain("![그림](https://example.invalid/a.png)");
    expect(text(parseMd(SAMPLES[15][1]))).toContain("![d](data:image/svg+xml,<svg onload=alert(1)>)");
    expect(links(SAMPLES[16][1]).map((n) => (n.k === "link" ? n.url : ""))).toEqual(["https://example.invalid/docs?a=1&b=(2)"]);
    expect(text(parseMd(SAMPLES[16][1]))).toBe("문서 (https://example.invalid/docs?a=1&b=(2)) 와 <https://example.invalid/auto> 와 맨 주소 https://example.invalid/bare");
  });

  it("19·20 인용·가로줄 = 글 그대로 · 역빗금 = 글자 그대로(벗김 아님 · fix H1) · 실체 해석 0", () => {
    expect(text(parseMd(SAMPLES[18][1]))).toBe("> 인용 줄\n---\n***\n> 굵게는 그림");
    expect(text(parseMd(SAMPLES[19][1]))).toBe("\\*별표 그대로\\* &lt;b&gt; &amp; D:\\work\\a.txt");
  });

  it("(C-19) 64KB 넘음 = 앞 64KB 를 줄 경계에서 잘라 서식 · 나머지 = 원문 그대로(글자 손실 0)", () => {
    const line = "**굵게** 줄\n";
    const big = line.repeat(Math.ceil((MD_MAX + 1000) / line.length));
    expect(MD_MAX).toBe(65536);
    const bs = parseMd(big);
    const raw = bs[bs.length - 1];
    expect(raw.k).toBe("raw");
    if (raw.k !== "raw") return;
    const head = big.length - raw.v.length;
    expect(head <= MD_MAX).toBe(true);
    expect(big[head - 1]).toBe("\n"); // 줄 경계
    expect(big.slice(head)).toBe(raw.v); // 나머지 = 원문 그대로(기호 포함)
    expect(bs.slice(0, -1).every((b) => b.k === "p")).toBe(true);
    // 줄바꿈이 없는 64KB 넘는 한 줄 = 전부 원문
    const one = "x".repeat(MD_MAX + 5);
    expect(parseMd(one)).toEqual([{ k: "raw", v: one }]);
    // 64KB 이하 = raw 0
    expect(parseMd(line.repeat(100)).some((b) => b.k === "raw")).toBe(false);
  });

  it("1MB 답 · 병적 입력(백틱·별표·괄호·밑줄 64KB) = 빨리 끝남(나무 = 선형)", () => {
    const mixed = SAMPLES.filter((s) => !s[0].startsWith("06")).map((s) => s[1]).join("\n\n"); // 06(닫히지 않은 울타리)은 뒤를 통째로 코드로 삼켜 시간 시험을 무르게 함 → 뺌
    const mb = mixed.repeat(Math.ceil(1_048_576 / mixed.length));
    const cases = [mb, "x`".repeat(32000), "``a`".repeat(16000), "*a ".repeat(21000), "[".repeat(60000) + "]", "[a](".repeat(16000), "_x ".repeat(21000), "**a ".repeat(16000) + "**", "| a ".repeat(16000) + "\n|---|\n"];
    expect(parseMd(mb).filter((b) => b.k !== "raw").length).toBeGreaterThan(50); // 1MB 앞 64KB 가 실제로 서식됨(삼켜지지 않음)
    for (const c of cases) {
      const t0 = performance.now();
      const bs = parseMd(c);
      const ms = performance.now() - t0;
      console.log(`md parse ${c.length} chars = ${ms.toFixed(1)}ms · 블록 ${bs.length}`);
      expect(ms).toBeLessThan(250); // 합격선 = 맥 VM 50ms(통합 때 master) · 여기는 2차 시간(수 초) 회귀만 잡는 넉넉한 둑
    }
  });
});

// ───────────── (TICKET=fix-1119-s6-adv) 적대 검증 VERIFY-1119-s6 지적 고침 ─────────────
// 원칙 = 「마스터 답의 명령줄·경로·주소는 복사했을 때 원문과 글자가 같다」 가 표준 마크다운 충실도보다 위.
const F = "```";
const flat = (src: string): string => text(parseMd(src));

describe("V1 고침 — 복사 왕복(명령줄·경로·주소·정규식·코드 = 원문 글자 그대로)", () => {
  // [입력, 보이는 글에 그대로 있어야 할 조각들] — 검증 문서 H1~H5·M1·M2·M4 입력 + 「전문가라면」 복사 왕복 30줄
  const KEEP: Array<[string, string[]]> = [
    ["C:\\Users\\user\\.cys\\pack 폴더", ["C:\\Users\\user\\.cys\\pack"]], // H1 L07
    ["\\\\server\\share\\자료 를 여세요", ["\\\\server\\share\\자료"]], // L08
    ["D:\\_work\\[백업]\\!중요\\$Recycle.Bin", ["D:\\_work\\[백업]\\!중요\\$Recycle.Bin"]], // L09
    ["정규식 \\d+\\.\\d+ 을 쓰세요", ["\\d+\\.\\d+"]], // L10
    ["find . -name \\*.log -delete 를 실행", ["\\*.log"]], // L11
    ["echo \\$HOME 은 글자 그대로", ["\\$HOME"]], // L12
    ["__init__.py 파일을 여세요", ["__init__.py"]], // H2 L01
    ["src/__tests__/a.test.ts 와 src/__mocks__/b.ts 를 고칩니다", ["src/__tests__/a.test.ts", "src/__mocks__/b.ts"]], // L02
    ["주소: https://github.com/o/r/blob/main/src/__tests__/x.ts", ["https://github.com/o/r/blob/main/src/__tests__/x.ts"]], // L03
    ["https://example.invalid/a/_private_/b 를 여세요", ["https://example.invalid/a/_private_/b"]], // L04
    ['if __name__ == "__main__": 줄을 찾으세요', ['__name__ == "__main__"']], // L05
    ["~/.cache/__pycache__ 폴더를 지우세요", ["~/.cache/__pycache__"]], // L06
    ["cp src/*.ts dist/*.js", ["src/*.ts", "dist/*.js"]], // H3 L13
    ["src/**/*.ts 와 test/**/*.ts 를 포함", ["src/**/*.ts", "test/**/*.ts"]], // L14
    ["f(*args) 와 g(*rest) 를 부릅니다", ["f(*args)", "g(*rest)"]], // L19
    ["char *p, (*fp)(int);", ["char *p, (*fp)(int);"]], // L20
    ["*`*.log`* 파일", ["*.log"]], // L22
    ["함수 f(*args, **kwargs) 와 `g(*a, **k)` 를 견줍니다", ["f(*args, **kwargs)", "g(*a, **k)"]], // L23
    ["2*3*4 = 24", ["2*3*4"]], // M4 L15
    ["3*4=12, 5*6=30", ["3*4=12, 5*6=30"]], // L16
    ["2**10 = 1024 이고 3**2 = 9", ["2**10", "3**2"]], // L17
    ["합계 = 가격*(1+세율)*수량", ["가격*(1+세율)*수량"]], // L18
    ["/*주석*/ 을 지우세요", ["/*주석*/"]], // L21
    ["(*)는 필수, (*)는 선택", ["(*)는 필수, (*)는 선택"]], // L24
    ["handlers[name](event) 을 부릅니다", ["handlers[name](event)"]], // L25
    ["| 명령 | 뜻 |\n|---|---|\n| `ps aux \\| grep cys` | 찾기 |", ["ps aux | grep cys"]], // H4 L26
    ["| a | b |\n|---|---|\n| 1 | 2 |\ncmd1 || cmd2", ["cmd1 || cmd2"]], // L27
    ["ls -la | grep foo\n--- | ---\n끝", ["ls -la | grep foo", "--- | ---"]], // L28
    [`1. 첫째\n   - 안쪽:\n     ${F}python\n     def f():\n         return 1\n     ${F}\n2. 둘째`, ["def f():\n    return 1"]], // H5 L29
    [`- 설정:\n    ${F}yaml\n    services:\n      - name: web\n        port: 80\n    ${F}\n- 다음`, ["services:\n  - name: web\n    port: 80"]], // L30
    [`1. ${F}bash\n   npm install\n   ${F}\n2. 다음 단계\n\n끝 문단 **굵게**`, ["npm install", "끝 문단 굵게"]], // M1 L31
    [`1. 실행:\n   ${F}python\n   def f():\n       return 1\n   ${F}`, ["def f():\n    return 1"]], // M2 L32
    ["a\n+\nb", ["+"]], // L1 L34
    ["위\n\n* * *\n\n아래", ["* * *"]], // L1 L35
    ["~~~ 물결 장식 ~~~\n다음 줄", ["~~~ 물결 장식 ~~~"]], // L2 L38
  ];
  const ROUND = [ // 복사 왕복 30줄 — 산문·울타리 안 둘 다
    "git log --oneline -n 5 -- src/**/*.rs",
    "rg -n '__init__|_private_' ~/proj/src",
    "python3 -c 'import sys; print(sys.argv[1:])' a b",
    "awk -F'|' '{print $2}' data.txt",
    "sed -E 's/(\\w+)_(\\w+)/\\2_\\1/g' in.txt",
    "C:\\Users\\user\\AppData\\Local\\cys\\.cache",
    "\\\\nas\\backup\\2026\\_old",
    "%USERPROFILE%\\.ssh\\id_ed25519",
    "https://example.invalid/a_b/c__d__e/f*g?x=1&y=_z_",
    "http://localhost:8080/__debug__/",
    "^\\s*[-*+]\\s+(.*)$",
    "\\bfoo_bar\\b|\\*\\*",
    "ls *.log | xargs -n1 rm",
    "echo $((3*4)) && echo ${HOME}/__x__",
    "export PATH=\"$HOME/.bun/bin:$PATH\"",
    "kill -TERM -- -$(cat run.pid)",
    "def __repr__(self): return f'<{self.name!r}>'",
    "    if x ** 2 > y * 3:",
    "        return [*a, *b]",
    "key: value_with_underscores",
    "  - name: __svc__",
    "    args: ['*', '**/*.ts']",
    "SELECT * FROM t WHERE a = '_x_';",
    "a[i](x) + b[j](y)",
    "~/.config/cys/agents.json",
    "npm run build -- --outdir=dist/_app",
    "* not a bullet when glued*",
    "C:\\Program Files\\cys\\cys.exe --role=worker",
    "cat <<'EOF' > a.txt",
    "x = y*z + w*v",
  ];
  it("검증 문서 HIGH·MID 입력 + 대조 = 보이는 글에 원문 조각 그대로", () => {
    for (const [src, must] of KEEP) for (const m of must) expect(`${JSON.stringify(src)} ⊇ ${JSON.stringify(m)}: ${flat(src).includes(m)}`).toBe(`${JSON.stringify(src)} ⊇ ${JSON.stringify(m)}: true`);
  });
  it("복사 왕복 30줄 — 산문으로 줘도 · 울타리로 줘도 · 목록 안 울타리로 줘도 글자 같음", () => {
    expect(ROUND.length).toBe(30);
    for (const l of ROUND.filter((x) => !/^\s*([-*+]|\d+[.)])\s/.test(x))) expect(`${l} → ${flat(l)}`).toBe(`${l} → ${l}`); // 줄 머리 목록 표지 꼴은 산문에서 목록(L1 · 울타리로 줄 때 아래에서 견줌)
    const fenced = `${F}sh\n${ROUND.join("\n")}\n${F}`;
    expect(flat(fenced)).toBe(ROUND.join("\n"));
    const inList = `1. 이렇게:\n   ${F}sh\n${ROUND.map((l) => `   ${l}`).join("\n")}\n   ${F}\n2. 끝`;
    expect(flat(inList)).toBe(`1.이렇게:\n${ROUND.join("\n")}\n2.끝`);
  });
  it("글자 손실 0(엄한 대조) — 검증 문서 입력 전부 · 복사 왕복 30줄", () => {
    for (const [src] of KEEP) expect(`${JSON.stringify(src)}: ${lossless(src)}`).toBe(`${JSON.stringify(src)}: ok`);
    for (const l of ROUND) expect(`${l}: ${lossless(l)}`).toBe(`${l}: ok`);
  });
  it("무작위 3,000건 — 엄한 글자 손실 0 · 던짐 0(씨앗 고정)", () => {
    let seed = 1119;
    const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff), seed / 0x7fffffff);
    const AL = ["*", "**", "_", "__", "`", "``", "\\", "[", "]", "(", ")", "!", "#", "# ", "- ", "1. ", "|", "~", "~~~", F, " ", " ", "\n", "\n", "\n   ", "\t", "a", "가", "x_y", "\u2028", "\r", ".", ",", ":", "\\|", "<", ">"];
    for (let n = 0; n < 3000; n++) {
      let s = "";
      const len = 1 + Math.floor(rnd() * 200); // 길이 ~200(~40 은 「|x」 다음 「-」 구분 줄 먹힘을 못 봄 · 검증 좌석 2만 건이 잡음)
      for (let k = 0; k < len; k++) s += AL[Math.floor(rnd() * AL.length)];
      expect(`${JSON.stringify(s)}: ${lossless(s)}`).toBe(`${JSON.stringify(s)}: ok`);
    }
  });
});

describe("V1 고침 — 강조 경계(낱말·경로·식 안 = 글 · 짝 안 맞음 = 글)", () => {
  const kinds = (src: string) => {
    const [b] = parseMd(src);
    const c = b && (b.k === "p" || b.k === "h") ? b.c : [];
    return c.map((n) => (n.k === "text" ? `t:${n.v}` : n.k === "strong" || n.k === "em" ? `${n.k}:${inl(n.c)}` : `${n.k}`));
  };
  it("허용 꼴 — 줄 처음·빈칸·여는 괄호 앞 / 줄 끝·빈칸·문장 부호·한글 조사 뒤", () => {
    expect(kinds("**굵게**는 됩니다")).toEqual(["strong:굵게", "t:는 됩니다"]);
    expect(kinds("이것은 **굵게**.")).toEqual(["t:이것은 ", "strong:굵게", "t:."]);
    expect(kinds("(*기울임*) 과 「**굵게**」")).toEqual(["t:(", "em:기울임", "t:) 과 「", "strong:굵게", "t:」"]);
    expect(kinds("*a*, *b*!")).toEqual(["em:a", "t:, ", "em:b", "t:!"]);
    expect(kinds("*기울임*을 씁니다")).toEqual(["em:기울임", "t:을 씁니다"]); // 한 별표도 바로 뒤 한글 조사 허용(487 mutants2 Q1 짝)
    expect(kinds("***굵은 기울임*** 입니다")[0]).toBe("strong:굵은 기울임"); // L3 = 굵게 안 기울임 · 별표 0
    expect(flat("***굵은 기울임*** 입니다")).toBe("굵은 기울임 입니다");
    expect(kinds("__밑줄 굵게__ 와 _밑줄 기울임_")).toEqual(["strong:밑줄 굵게", "t: 와 ", "em:밑줄 기울임"]);
  });
  it("글로 남는 꼴 — 낱말 안 · 경로 안 · 식 안 · 이름(dunder) · 빈칸으로 시작·끝 · 짝 없음", () => {
    for (const s of ["a*b*c", "x*y* z", "a_b_ c", "src/*.ts", "/_x_/", "__init__", "_private_", "a * 빈칸 시작*", "*빈칸 끝 *", "**짝 없음", "f(*a) g(*b)", "a**b**c"]) expect(`${s}: ${kinds(s).join("|")}`).toBe(`${s}: t:${s}`);
  });
  it("코드 칸이 강조보다 먼저 — 코드 칸 안 별표는 닫는 짝이 아님(L22·L23 꼴)", () => {
    expect(flat("*a `b* c` d*")).toBe("a b* c d");
    expect(kinds("*a `b* c` d*")).toEqual(["em:a b* c d"]);
  });
  it("(P5 짝) 밑줄 여는 쪽 검사 — 낱말 바로 뒤 밑줄은 열지 않음(닫는 쪽만으로는 못 지키는 꼴)", () => {
    expect(flat("a_b_ c")).toBe("a_b_ c");
    expect(flat("x_y_ 와 z")).toBe("x_y_ 와 z");
  });
});

describe("V1 고침2 — 두 별표(`**…**`)만 너그럽게 · 한 별표·밑줄은 엄하게(master#103504d7 N-A)", () => {
  const strongOf = (src: string): string[] => {
    const out: string[] = [];
    const walk = (c: Inline[]) => c.forEach((n) => (n.k === "strong" ? out.push(inl(n.c)) : n.k === "em" || n.k === "link" ? walk(n.c) : null));
    for (const b of parseMd(src)) {
      if (b.k === "p" || b.k === "h") walk(b.c);
      if (b.k === "list") b.items.forEach((it) => walk(it.c));
      if (b.k === "table") [b.head, ...b.rows].forEach((r) => r.forEach(walk));
    }
    return out;
  };
  // 487 강조 표(repro/emph.ts) 의 두 별표 줄 — [입력, 그려질 굵게, 보이는 글]
  const BOLD: Array<[string, string[], string]> = [
    ["**굵게**는 됩니다", ["굵게"], "굵게는 됩니다"],
    ["결과는**3건**입니다", ["3건"], "결과는3건입니다"],
    ["이것은 **굵게** 입니다", ["굵게"], "이것은 굵게 입니다"],
    ["**굵게**(설명) 입니다", ["굵게"], "굵게(설명) 입니다"],
    ["- **B1**(BLOCK) 정규식", ["B1"], "B1(BLOCK) 정규식"],
    ["(**굵게**) 입니다", ["굵게"], "(굵게) 입니다"],
    ["**요약**: 내용", ["요약"], "요약: 내용"],
    ["**요약**:내용", ["요약"], "요약:내용"],
    ["**하나**, **둘**. 끝", ["하나", "둘"], "하나, 둘. 끝"],
    ['**"확정한다"** 라고', ['"확정한다"'], '"확정한다" 라고'],
    ["**'값'** 입니다", ["'값'"], "'값' 입니다"],
    ["**「제목」** 입니다", ["「제목」"], "「제목」 입니다"],
    ["**가**·**나**", ["가", "나"], "가·나"],
    ["**가** · **나**", ["가", "나"], "가 · 나"],
    ["**예**/**아니오**", ["예", "아니오"], "예/아니오"],
    ["**전**→**후**", ["전", "후"], "전→후"],
    ["**합계**=10", ["합계"], "합계=10"],
    ["주의—**굵게** 입니다", ["굵게"], "주의—굵게 입니다"],
    ["주의:**굵게** 입니다", ["굵게"], "주의:굵게 입니다"],
    ["this is **bold** text", ["bold"], "this is bold text"],
    ["**굵게** 로 시작", ["굵게"], "굵게 로 시작"],
    ["**`코드` 굵게** 입니다", ["코드 굵게"], "코드 굵게 입니다"],
    ["| **가** | 나 |\n|---|---|\n| **다**(라) | 마 |", ["가", "다"], "가 나\n다(라) 마"],
    ["## **굵게**(설명)", ["굵게"], "굵게(설명)"],
  ];
  it("두 별표 줄 = 전부 그려짐(별표 0 · 범위 바름)", () => {
    for (const [src, bold, vis] of BOLD) {
      expect(`${src} → ${JSON.stringify(strongOf(src))}`).toBe(`${src} → ${JSON.stringify(bold)}`);
      expect(`${src} → ${flat(src)}`).toBe(`${src} → ${vis}`);
    }
  });
  it("글로 남는 두 별표 = 이웃이 ASCII 영숫자·별표(master 규칙) · 글롭 빗금(덧붙임) · 같은 줄 안에 짝 없음", () => {
    for (const s of ["**약**3건", "un**believ**able", "the **file**s are", "2**10 = 1024 이고 3**2 = 9", "src/**/*.ts 와 test/**/*.ts", "**/*.ts 와 a.ts**", "x**y + z**w", "**굵게\n다음 줄**"]) expect(`${s}: ${JSON.stringify(strongOf(s))}`).toBe(`${s}: []`);
  });
  it("(487 재실행2 Q18 짝) 닫는 표지 바로 앞 빗금 = 표지 아님 — `**src/**` = 글(P-B 수용 값 · 여는 쪽만으로는 못 지킴)", () => {
    expect(strongOf("**src/** 폴더")).toEqual([]);
  });
  it("(487 재실행2 P-A · 알고 수용한 값) 식 꼴 `**` 가 한 줄에 두 번 = 굵게로 먹힘 — 바꾸려면 VERIFY-1119-s6.md 「재실행2」 P-A 와 master#dc60dfc4 수용 까닭 3 을 먼저 읽을 것", () => {
    // 수용 까닭: ① CommonMark 도 같은 값 ② 마스터 답 표본 200 에서 0번(식은 백틱 안 = 코드 칸 먼저) ③ 좁히면 `**(중요)**`·`**굵게**(설명)` 이 다시 깨짐
    expect(strongOf("(a+b)**(c+d) 와 (e+f)**(g+h)")).toEqual(["(c+d) 와 (e+f)"]);
  });
  it("한 별표·밑줄은 엄한 그대로(H2·H3·M4 닫힘 유지)", () => {
    for (const s of ["__init__.py", "cp src/*.ts dist/*.js", "f(*args) 와 g(*rest)", "3*4=12, 5*6=30", "this is _italic_ text"]) expect(`${s}: ${flat(s)}`).toBe(`${s}: ${s}`);
  });
  it("두 별표 짝 못 찾음 = 줄마다 한 번(병적 입력 선형)", () => {
    const c = `${"**a ".repeat(4000)}\n`.repeat(4);
    let ms = Infinity;
    for (let k = 0; k < 3; k++) {
      const t0 = performance.now();
      parseMd(c);
      ms = Math.min(ms, performance.now() - t0);
    }
    expect(ms < 50 ? "≤50ms" : `${ms.toFixed(1)}ms`).toBe("≤50ms");
  });
});

describe("V1 고침 — 울타리·표 경계(살아남은 파서 뮤턴트 P2·P3·P6 짝)", () => {
  it("(P2) 백틱 울타리 정보 글에 백틱 = 울타리 아님", () => {
    const bs = parseMd("```a`b\n코드 아님\n");
    expect(bs[0].k).toBe("p");
    expect(flat("```a`b\n코드 아님\n")).toBe("```a`b\n코드 아님");
  });
  it("(P3) 인라인 코드 앞뒤 빈칸 한 칸씩 걷음 · 빈칸뿐이면 그대로", () => {
    const codes = (s: string) => parseMd(s).flatMap((b) => (b.k === "p" ? b.c.filter((n) => n.k === "code").map((n) => (n.k === "code" ? n.v : "")) : []));
    expect(codes("`` `x` `` 와 ` a `")).toEqual(["`x`", "a"]);
    expect(codes("`  `")).toEqual(["  "]);
  });
  it("(P6) 머리 칸 수 ≠ 구분 칸 수 = 표 아님(글)", () => {
    expect(parseMd("| a | b |\n|---|\n| 1 | 2 |").map((b) => b.k)).toEqual(["p"]);
    expect(parseMd("|!\n-").map((b) => b.k)).toEqual(["p"]); // 구분 줄에 「|」 없음 = 표 아님(「-」 한 줄이 먹히지 않음 · 검증 좌석 무작위 2만 건 39건의 뿌리)
    expect(lossless("|!\n-")).toBe("ok");
  });
  it("울타리 정보 글 = 언어 이름 꼴만 버림(나무에 info 로 · 그리기 0) · 빈칸 든 정보 글 = 울타리 아님", () => {
    const [p] = parseMd(`${F}python\nx = 1\n${F}`);
    expect(p.k === "pre" && [p.v, p.info]).toEqual(["x = 1", "python"]);
    expect(parseMd("~~~ 물결 장식 ~~~\n다음 줄")[0].k).toBe("p"); // 정보 글에 울타리 글자(물결) = 울타리 아님(장식 줄 = 글)
  });
  it("(fix2 N-B) 정보 글이 언어 이름 꼴이 아니어도 울타리 = 울타리(코드 몸 그대로 · 뒤 답 서식 그대로) · 닫는 울타리 = 같은 표지·길이 이상", () => {
    for (const info of ["bash title=run.sh", "ts:src/a.ts", "python {1,3}", "shell script", "text/plain", "실행 예", "bash", "c++"]) {
      const src = `${F}${info}\nrm -rf *.log && echo **done**\n${F}\n\n끝 **굵게**\n- 항목`;
      const bs = parseMd(src);
      expect(`${info}: ${bs.map((b) => b.k).join(",")}`).toBe(`${info}: pre,p,list`);
      expect(bs[0].k === "pre" && [bs[0].v, bs[0].info]).toEqual(["rm -rf *.log && echo **done**", info]);
      expect(flat(src)).toBe("rm -rf *.log && echo **done**\n끝 굵게\n항목");
      expect(lossless(src)).toBe("ok");
    }
    expect(parseMd("````\n```\n안\n````\n").map((b) => b.k)).toEqual(["pre"]); // 짧은 표지 = 닫지 않음
    expect(parseMd("```\nx\n~~~\ny\n```").map((b) => (b.k === "pre" ? b.v : b.k))).toEqual(["x\n~~~\ny"]); // 다른 표지 = 닫지 않음
  });
  it("(fix2 N-G) 목록 안 울타리 몸이 덜 들여쓰여도 닫는 울타리까지 코드 · 닫히지 않으면 다음 항목에서 끝", () => {
    const src = `1. 실행:\n   ${F}bash\nnpm install\nnpm test\n   ${F}\n2. 다음`;
    const [l] = parseMd(src);
    expect(l.k === "list" && l.items.map((it) => it.more.map((m) => (m.k === "pre" ? m.v : "p")))).toEqual([["npm install\nnpm test"], []]);
    expect(flat(src)).toBe("1.실행:\nnpm install\nnpm test\n2.다음");
    expect(lossless(src)).toBe("ok");
  });
  it("맨 앞 울타리 몸 = 여는 줄 들여쓰기만큼만 걷음(그보다 깊은 들여쓰기 보존)", () => {
    const [p] = parseMd(`  ${F}\n  a\n      b\nc\n  ${F}`);
    expect(p.k === "pre" && p.v).toBe("a\n    b\nc");
  });
  it("항목 안 닫히지 않은 울타리 = 다음 항목·맨 앞 줄에서 끝남(뒤 답 전체를 삼키지 않음)", () => {
    const bs = parseMd(`1. ${F}sh\n   ls\n2. 둘째\n\n끝 **굵게**`);
    expect(bs.map((b) => b.k)).toEqual(["list", "p"]);
    expect(flat(`1. ${F}sh\n   ls\n2. 둘째\n\n끝 **굵게**`)).toBe("1.\nls\n2.둘째\n끝 굵게");
  });
});

describe("V1 고침 — B1 줄 끝 글자(맨 CR · U+2028 · U+2029) = 줄 가름 · 한 답 ≤ 50ms", () => {
  const LS = String.fromCharCode(0x2028);
  const PS = String.fromCharCode(0x2029);
  it("줄 끝 글자 = 줄을 가름(같은 줄 안에 남지 않음)", () => {
    for (const e of ["\r\n", "\r", "\n", LS, PS]) {
      expect(parseMd(`# 제목${e}본문`).map((b) => b.k)).toEqual(["h", "p"]);
      const [l] = parseMd(`- 가${e}- 나`);
      expect(l.k === "list" && l.items.map((it) => inl(it.c))).toEqual(["가", "나"]);
    }
  });
  it("병적 입력 = 64KB 문턱 아래 · 줄 끝 글자 든 판 전부 50ms 안(검증 문서 합격선 · 호스트)", () => {
    const N = 65000;
    const cases: Array<[string, string]> = [];
    for (const e of ["\r", LS, PS]) {
      cases.push([`제목 꼴 ${e.charCodeAt(0)}`, `# ${" ".repeat(N)}${e}x`]);
      cases.push([`목록 꼴 ${e.charCodeAt(0)}`, `- ${" ".repeat(N)}${e}x`]);
      cases.push([`백틱 울타리 꼴 ${e.charCodeAt(0)}`, `${"`".repeat(N)}${e}x`]);
      cases.push([`물결 울타리 꼴 ${e.charCodeAt(0)}`, `${"~".repeat(N)}${e}x`]);
      cases.push([`표 구분 꼴 ${e.charCodeAt(0)}`, `| a |\n|${"-".repeat(N)}${e}x`]);
      cases.push([`줄 3개 ${e.charCodeAt(0)}`, `# ${" ".repeat(20000)}${e}x\n`.repeat(3)]);
    }
    cases.push(["백틱 묶음 길이 1..359(L4)", Array.from({ length: 359 }, (_, k) => "`".repeat(k + 1)).join("a")]);
    cases.push(["닫는 울타리 꼴 빈칸+x", `${F}\n${"`".repeat(30000)}${" ".repeat(30000)}x`]);
    cases.push(["가로줄 꼴 64KB", "* ".repeat(32000)]);
    cases.push(["밑줄 이름 반복", "__a__ ".repeat(10000)]);
    cases.push(["여는 괄호 + 별표 반복", "(*a ".repeat(16000)]);
    cases.push(["목록 안 울타리 반복", `- a\n  ${F}\n  b\n  ${F}\n`.repeat(3000)]);
    for (const [name, c] of cases) {
      parseMd(c); // 데우기(첫 컴파일 시간 제외)
      let ms = Infinity; // 3회 중 최소(부하·GC 한 번 멈춤 제외 · 2차 시간이면 최소도 수 초라 못 가림)
      for (let k = 0; k < 3; k++) {
        const t0 = performance.now();
        parseMd(c);
        ms = Math.min(ms, performance.now() - t0);
      }
      expect(`${name} ${c.length}자: ${ms < 50 ? "≤50ms" : `${ms.toFixed(1)}ms`}`).toBe(`${name} ${c.length}자: ≤50ms`);
    }
  });
});
