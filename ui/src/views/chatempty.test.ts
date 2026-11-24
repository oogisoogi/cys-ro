// (TICKET=cysr-1119-s5 · CV-EX3) 빈 화면 예시 시험 — DESIGN §4-2 합격 칸(0건 = 단추 3 · 누름 → 입력칸 = 예시 · 데몬 호출 0).
// 화면 시험 환경에 DOM 이 없어 아주 작은 가짜 document 로 createEmpty 를 세운다(makepane.test.ts 와 같은 방식).
import { describe, expect, it } from "bun:test";
import { applyExample, CHAT_EXAMPLES, createEmpty, EMPTY_GUIDE, EMPTY_TITLE } from "./chat/empty";
import { ChatCore, type Deps } from "./core";

interface FakeEl {
  tagName: string;
  className: string;
  textContent: string;
  type?: string;
  children: FakeEl[];
  listeners: Record<string, Array<() => void>>;
  append(...c: FakeEl[]): void;
  addEventListener(k: string, f: () => void): void;
}
function fakeEl(tag: string): FakeEl {
  const e: FakeEl = {
    tagName: tag.toUpperCase(),
    className: "",
    textContent: "",
    children: [],
    listeners: {},
    append: (...c) => void e.children.push(...c),
    addEventListener: (k, f) => void (e.listeners[k] ??= []).push(f),
  };
  return e;
}
const all = (e: FakeEl): FakeEl[] => [e, ...e.children.flatMap(all)];

/** 가짜 document 를 그 시험 동안만 세운다(다른 시험 파일에 새지 않게 되돌림). */
function withDoc<T>(fn: () => T): T {
  const g = globalThis as { document?: unknown };
  const saved = g.document;
  g.document = { createElement: (t: string) => fakeEl(t) };
  try {
    return fn();
  } finally {
    g.document = saved;
  }
}

function core() {
  const calls: string[] = [];
  const deps: Deps = {
    invoke: async (cmd: string) => {
      calls.push(cmd);
      return {};
    },
    now: () => 1_000_000,
    setTimeout: () => 0,
    clearTimeout: () => {},
    store: { get: () => null, set: () => {}, remove: () => {} },
    working: () => false,
  } as unknown as Deps;
  return { act: new ChatCore(deps), calls };
}

function fakeInput(v = "") {
  const st = { value: v, focused: 0, sel: [-1, -1] as [number, number] };
  return {
    st,
    get value() {
      return st.value;
    },
    set value(x: string) {
      st.value = x;
    },
    focus: () => void st.focused++,
    setSelectionRange: (a: number, b: number) => void (st.sel = [a, b]),
  };
}

describe("CV-EX3 — 빈 화면 예시 3", () => {
  it("글 = P2-mock app.js:7-13 그대로 · 제목·안내", () => {
    expect([...CHAT_EXAMPLES]).toEqual(["교회 추수감사 행사 안내 페이지 만들어 줘", "이번 주 주보 PDF 정리해 줘", "다음 달 교사 모임 일정을 표로 만들어 줘"]);
    expect(EMPTY_TITLE).toBe("마스터에게 맡길 일을 적어 주세요");
    expect(EMPTY_GUIDE).toBe("이렇게 말해 보세요(누르면 입력칸에 들어가요)");
  });

  it("0건 칸 = 제목 · 안내 · 단추 3(글 = 예시) · 누르면 그 글을 넘김", () => {
    const picked: string[] = [];
    const li = withDoc(() => createEmpty((ex) => void picked.push(ex))) as unknown as FakeEl;
    expect(li.className).toBe("cv-empty");
    const btns = all(li).filter((e) => e.tagName === "BUTTON");
    expect(btns.map((b) => [b.type, b.className, b.textContent])).toEqual(CHAT_EXAMPLES.map((t) => ["button", "cv-ex-btn", t]));
    expect(all(li).find((e) => e.className === "cv-empty-title")?.textContent).toBe(EMPTY_TITLE);
    for (const b of btns) for (const f of b.listeners.click ?? []) f();
    expect(picked).toEqual([...CHAT_EXAMPLES]);
  });

  it("누름 → 입력칸 = 예시 · 초안 기억 · 포커스 · 커서 끝 · 데몬 호출 0(보내지 않음)", () => {
    const { act, calls } = core();
    const input = fakeInput("");
    expect(applyExample(input, act, CHAT_EXAMPLES[1])).toBe(true);
    expect(input.st.value).toBe(CHAT_EXAMPLES[1]);
    expect(act.state.draft).toBe(CHAT_EXAMPLES[1]);
    expect(input.st.focused).toBe(1);
    expect(input.st.sel).toEqual([CHAT_EXAMPLES[1].length, CHAT_EXAMPLES[1].length]);
    expect(calls).toEqual([]);
    expect(act.state.msgs.length).toBe(0);
  });

  it("쓰던 글이 있으면 덮지도 앞에 넣지도 않음(예시 무시) · 공백뿐 = 빈 것", () => {
    const { act, calls } = core();
    const input = fakeInput("쓰던 말");
    expect(applyExample(input, act, CHAT_EXAMPLES[0])).toBe(false);
    expect(input.st.value).toBe("쓰던 말");
    expect(input.st.focused).toBe(0);
    const blank = fakeInput("  \n ");
    expect(applyExample(blank, act, CHAT_EXAMPLES[0])).toBe(true);
    expect(blank.st.value).toBe(CHAT_EXAMPLES[0]);
    expect(calls).toEqual([]);
  });
});
