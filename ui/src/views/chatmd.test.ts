// (TICKET=cysr-1119-s6 · V1) 마크다운 그리기 시험 — DESIGN §6 V1 합격 칸(견본 20종 DOM 에 스크립트·이벤트 속성·href 0 · innerHTML 0).
// 화면 시험 환경에 DOM 이 없다 → 「기록하는」 가짜 document: 만든 태그 · 쓴 속성(property·setAttribute) · HTML 해석 API 호출을 전부 남긴다.
// 진짜 크롬 판정(스크립트 실행 0 · 바깥 요청 0 · 18px)은 e2e ui/e2e/md_gate.py.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { MD_RENDER, mdKeeper, renderMd } from "./chat/md";
import { parseMd, type Block, type Inline } from "./judge/md";

const SAMPLES = JSON.parse(readFileSync(new URL("./md_samples.json", import.meta.url), "utf8")) as Array<[string, string]>;

/** 허용 태그 — 이 밖의 태그(script·img·a·iframe·svg·style·link·object·embed …)는 만들어지지 않아야 한다. */
const ALLOWED = new Set(["div", "p", "h1", "h2", "h3", "strong", "em", "code", "pre", "ul", "ol", "li", "span", "table", "thead", "tbody", "tr", "th", "td"]);
/** 허용 쓰기 = 고정 className · textContent 뿐(믿지 못할 글이 속성 값으로 들어가는 길 0). */
const ALLOWED_PROPS = new Set(["className", "textContent"]);

interface Rec {
  tags: string[];
  props: string[];
  danger: string[];
}
type Node = { text?: string; tag?: string; className?: string; kids: Node[] };

function withDoc<T>(fn: (rec: Rec) => T): T {
  const rec: Rec = { tags: [], props: [], danger: [] };
  const mk = (tag: string) => {
    rec.tags.push(tag);
    const node: Node = { tag, kids: [] };
    const target = {
      node,
      append: (...c: Array<{ node: Node } | string>) => {
        for (const x of c) node.kids.push(typeof x === "string" ? { text: x, kids: [] } : x.node);
      },
      appendChild: (x: { node: Node }) => {
        node.kids.push(x.node);
        return x;
      },
      setAttribute: (k: string, v: string) => void rec.danger.push(`setAttribute(${k}=${v})`),
      setAttributeNS: (_n: string, k: string) => void rec.danger.push(`setAttributeNS(${k})`),
      insertAdjacentHTML: () => void rec.danger.push("insertAdjacentHTML"),
      querySelectorAll: () => [], // mdKeeper 의 가로 스크롤 칸 찾기(대역 = 없음)
      dataset: new Proxy({}, { set: (_t, k) => (rec.danger.push(`dataset.${String(k)}`), true) }),
      style: new Proxy({}, { set: (_t, k) => (rec.danger.push(`style.${String(k)}`), true) }),
    };
    return new Proxy(target, {
      set(_t, k, v) {
        const key = String(k);
        rec.props.push(key);
        if (key === "className") node.className = String(v);
        else if (key === "textContent") node.kids = [{ text: String(v), kids: [] }];
        else rec.danger.push(`set ${key}`);
        return true;
      },
    });
  };
  const g = globalThis as { document?: unknown };
  const saved = g.document;
  g.document = {
    createElement: (t: string) => mk(t.toLowerCase()),
    createTextNode: (t: string) => ({ node: { text: t, kids: [] } }),
    createElementNS: (_n: string, t: string) => (rec.danger.push(`createElementNS(${t})`), mk(t)),
    write: () => void rec.danger.push("document.write"),
  };
  try {
    return fn(rec);
  } finally {
    g.document = saved;
  }
}
const textOf = (n: Node): string => (n.text ?? "") + n.kids.map(textOf).join("");
const nodes = (n: Node): Node[] => [n, ...n.kids.flatMap(nodes)];
/** (fix-1119-s6-adv M5) 엄한 대조 — 그린 글(textContent 이음) = 나무의 보이는 글(같은 규칙 · 기호를 지우지 않음).
 *  나무 쪽 「글자 손실 0」 은 judge/md.test.ts 가 표지 원문까지 다시 써서 원문과 견준다 → 둘을 이으면 원문 → 화면 글자 손실 0. */
const vInl = (c: Inline[]): string => c.map((n) => (n.k === "text" || n.k === "code" ? n.v : n.k === "link" ? `${vInl(n.c)} (${n.url})` : vInl(n.c))).join("");
const visible = (bs: Block[]): string =>
  bs
    .map((b) =>
      b.k === "h" || b.k === "p" ? vInl(b.c)
      : b.k === "pre" || b.k === "raw" ? b.v
      : b.k === "list" ? b.items.map((it) => (it.num === null ? "" : `${it.num} `) + vInl(it.c) + it.more.map((m) => (m.k === "pre" ? m.v : vInl(m.c))).join("")).join("")
      : [b.head, ...b.rows].map((r) => r.map(vInl).join("")).join(""),
    )
    .join("");
/** 나무 마디 → 「태그.class:글」 줄(구조 단언용 · 같은 꼴이 같은 태그가 되는가). */
const tagged = (root: Node, tag: string): string[] => nodes(root).filter((n) => n.tag === tag).map((n) => `${n.className ?? ""}:${textOf(n)}`);

describe("V1 — 마크다운 그리기(createElement + textContent 만)", () => {
  it("MD_RENDER = true(켬) · 끄면 지금 꼴(되돌리기 상수 · DESIGN §6)", () => {
    expect(MD_RENDER).toBe(true);
  });

  it("견본 20종 — 허용 태그만 · 쓰기 = className·textContent 만 · setAttribute·dataset·style·innerHTML·NS 0", () => {
    for (const [name, src] of SAMPLES) {
      withDoc((rec) => {
        renderMd(src);
        expect(`${name}: ${rec.tags.filter((t) => !ALLOWED.has(t)).join(",")}`).toBe(`${name}: `);
        expect(`${name}: ${rec.props.filter((p) => !ALLOWED_PROPS.has(p)).join(",")}`).toBe(`${name}: `);
        expect(`${name}: ${rec.danger.join(",")}`).toBe(`${name}: `);
      });
    }
  });

  it("견본 20종 — 그린 글 = 입력 글자 − 기호(글자 손실 0) · className 은 고정 이름뿐", () => {
    for (const [name, src] of SAMPLES) {
      withDoc(() => {
        const root = (renderMd(src) as unknown as { node: Node }).node;
        expect(`${name}: ${textOf(root)}`).toBe(`${name}: ${visible(parseMd(src))}`);
        for (const n of nodes(root)) if (n.className !== undefined) expect(n.className).toMatch(/^cv-md(-[a-z0-9]+)?( cv-md-[a-z0-9]+)*$/);
      });
    }
  });

  it("견본 보이는 글 정답(md_samples_visible.json · e2e md_gate 가 진짜 크롬 글과 글자째 견줌) = 지금 나무의 보이는 글", () => {
    const golden = JSON.parse(readFileSync(new URL("./md_samples_visible.json", import.meta.url), "utf8")) as string[];
    expect(golden).toEqual(SAMPLES.map(([, src]) => visible(parseMd(src))));
  });

  it("링크 = 「글 (주소)」 보이는 글 · 그림 = 원문 글 · 스크립트 꼴 = 글", () => {
    withDoc((rec) => {
      const root = (renderMd("[눌러](javascript:window.__pwn=1) ![g](https://example.invalid/a.png) <script>x</script>") as unknown as { node: Node }).node;
      expect(textOf(root)).toBe("눌러 (javascript:window.__pwn=1) ![g](https://example.invalid/a.png) <script>x</script>");
      expect(rec.tags).not.toContain("a");
      expect(rec.tags).not.toContain("img");
      expect(rec.tags).not.toContain("script");
    });
  });

  it("64KB 넘음 = 앞 서식 + 나머지 원문 한 덩이(cv-md-raw)", () => {
    withDoc(() => {
      const big = "**굵게** 줄\n".repeat(8000); // 9자 × 8000 = 72,000 > 64KB
      const root = (renderMd(big) as unknown as { node: Node }).node;
      const raw = root.kids[root.kids.length - 1];
      expect(raw.className).toBe("cv-md-raw");
      const tail = textOf(raw);
      expect(big.endsWith(tail) && tail.includes("**")).toBe(true); // 나머지 = 원문 그대로(기호 포함)
      const head = big.slice(0, big.length - tail.length);
      expect(textOf(root)).toBe(head.replace(/\*\*/g, "").replace(/\n$/, "") + tail); // 앞 = 기호만 빠짐(한 문단 · 끝 줄바꿈 1개 = 줄 경계)
    });
  });

  it("원천 검사 — chat/md.ts 에 HTML 해석·속성 쓰기·주소 칸 0", () => {
    const src = readFileSync(new URL("./chat/md.ts", import.meta.url), "utf8").replace(/\/\/.*$/gm, "");
    for (const w of ["innerHTML", "outerHTML", "insertAdjacentHTML", "setAttribute", "DOMParser", "createContextualFragment", "document.write", ".href", ".src", "dataset", ".style", "createElementNS", "eval(", "Function("]) expect(`${w}:${src.includes(w)}`).toBe(`${w}:false`);
  });

  // (fix-1119-s6-adv M5-③) 살아남은 그리기 뮤턴트 R1~R9·R11 짝 — 어느 꼴이 어느 태그·class 가 되는가.
  it("구조 — 순서/점 목록·항목 class·들여쓴 표지·제목 단계·표 머리·굵게/기울임·인라인 코드·울타리·표 감싸개·번호 뒤 빈칸", () => {
    const draw = (i: number) => withDoc(() => (renderMd(SAMPLES[i][1]) as unknown as { node: Node }).node);
    const s01 = draw(0);
    expect([tagged(s01, "h1"), tagged(s01, "h2"), tagged(s01, "h3")]).toEqual([[":큰 제목"], [":중간 제목"], [":작은 제목"]]); // R4
    const s03 = draw(2);
    expect([tagged(s03, "strong"), tagged(s03, "em")]).toEqual([[":굵게", ":밑줄 굵게", ":b"], [":기울임", ":밑줄 기울임", ":a b c"]]); // R6
    const s04 = draw(3);
    expect(tagged(s04, "code")).toEqual([":npm install", ":a`b"]); // R7
    const s05 = draw(4);
    expect(tagged(s05, "pre").length).toBe(1); // R8
    expect(tagged(s05, "p")).toEqual([":뒤 문단"]);
    const s07 = draw(6);
    expect([tagged(s07, "ul").length, tagged(s07, "ol").length]).toEqual([1, 0]); // R1
    expect(tagged(s07, "li").map((x) => x.split(":")[0])).toEqual(["cv-md-bul", "cv-md-bul", "cv-md-bul cv-md-d1", "cv-md-bul cv-md-d1", "cv-md-bul", "cv-md-bul"]); // R2·R3
    const s08 = draw(7);
    expect([tagged(s08, "ul").length, tagged(s08, "ol").length]).toEqual([0, 1]); // R1
    expect(tagged(s08, "li")).toEqual(["cv-md-num:1. 첫째", "cv-md-num:2. 둘째", "cv-md-num:10) 열째"]); // R2·R11
    expect(tagged(s08, "span")).toEqual(["cv-md-n:1. ", "cv-md-n:2. ", "cv-md-n:10) "]); // R11
    const s09 = draw(8);
    expect([tagged(s09, "th"), tagged(s09, "td").length]).toEqual([[":이름", ":값"], 4]); // R5
    expect(tagged(s09, "div").map((x) => x.split(":")[0])).toEqual(["cv-md", "cv-md-table"]); // R9
    const s15 = draw(14);
    expect(tagged(s15, "span").filter((x) => x.startsWith("cv-md-url"))[0]).toBe("cv-md-url: (javascript:window.__pwn=1)"); // R10
  });

  it("항목 안 울타리 = li 안 pre(코드 들여쓰기 보존 · 언어 이름 0 · 뒤 답을 삼키지 않음)", () => {
    withDoc(() => {
      const F = "```";
      const root = (renderMd(`1. 첫째\n   - 안쪽:\n     ${F}python\n     def f():\n         return 1\n     ${F}\n2. 둘째\n\n끝 **굵게**`) as unknown as { node: Node }).node;
      expect(tagged(root, "pre")).toEqual([":def f():\n    return 1"]);
      const li = nodes(root).filter((n) => n.tag === "li");
      expect(li.map((n) => n.kids.some((k) => k.tag === "pre"))).toEqual([false, true, false]);
      expect(textOf(root).includes("python")).toBe(false);
      expect(tagged(root, "strong")).toEqual([":굵게"]);
    });
  });

  it("(fix2 ④) 답 마디 저장 — 같은 글 두 번 그리기 = 같은 마디 · 글 바뀜 = 새 마디 · 안 나온 열쇠 = 버림 · 한 그리기 같은 열쇠 둘 = 따로", () => {
    withDoc(() => {
      const k = mdKeeper();
      const a1 = k.node("u1", "**가**");
      k.afterFill();
      k.beforeClear();
      const a2 = k.node("u1", "**가**");
      expect(a2).toBe(a1); // 같은 글 = 같은 마디(renderMd 다시 안 부름)
      const b1 = k.node("u2", "나");
      k.afterFill();
      k.beforeClear();
      const a3 = k.node("u1", "**가 바뀜**");
      expect(a3).not.toBe(a1); // 글 바뀜 = 새 마디
      expect(textOf((a3 as unknown as { node: Node }).node)).toBe("가 바뀜");
      k.afterFill(); // u2 안 나옴 = 버림
      expect(k.size()).toBe(1);
      k.beforeClear();
      expect(k.node("u2", "나")).not.toBe(b1);
      const d1 = k.node("s:같은 글", "같은 글");
      const d2 = k.node("s:같은 글", "같은 글");
      expect(d2).not.toBe(d1); // 한 그리기에 같은 열쇠 둘 = 마디를 옮기지 않음
    });
  });
});
