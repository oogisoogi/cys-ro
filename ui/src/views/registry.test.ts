// (cysr-ui-slice1) 등록·전환·물러남·누수 시험(P2-DESIGN §4-2 수명 계약) + 정적 핀(순수 판정 · main.ts/main.rs 배선).
import { describe, it, expect } from "bun:test";
import { readFileSync, readdirSync } from "node:fs";
import { FAIL_LIMIT, FALLBACK_BAND, Registry, type RegistryEnv } from "./registry";
import type { ViewDescriptor, ViewModule } from "./contract";
import { VIEW_KEY } from "./judge/viewpick";

type S = { n: number };

function setup(opts: { chatThrows?: () => boolean; chatAvail?: { ok: true } | { ok: false; why: string }; paintThrows?: { on: boolean } } = {}) {
  const mem = new Map<string, string>();
  const subs = new Set<(s: S) => void>();
  const intervals = new Set<number>();
  let hn = 0;
  const log: string[] = [];
  const mod = (id: string, throws?: () => boolean): ViewModule<S, null> => ({
    mount(_h, ctx) {
      if (throws?.()) throw new Error("boom");
      log.push(`mount:${id}`);
      ctx.subscribe(() => {
        if (id === "chat" && opts.paintThrows?.on) throw new Error("paint");
      });
      ctx.subscribe(() => {});
      ctx.timers.every(1000, () => {});
      return { unmount: () => log.push(`unmount:${id}`) };
    },
  });
  const views: ViewDescriptor<S, null>[] = [
    { id: "chat", label: "대화 화면", order: 1, minimum: { confirms: "a", lastSendStep: "b", masterHealth: "c", errors: "d", switcher: "shared" }, available: async () => opts.chatAvail ?? { ok: true }, load: async () => mod("chat", opts.chatThrows) },
    { id: "work", label: "작업 화면", order: 2, minimum: { confirms: "a", lastSendStep: "", masterHealth: "", errors: "", switcher: "shared" }, available: async () => ({ ok: true }), load: async () => mod("work") },
  ];
  const env: RegistryEnv<S, null> = {
    host: {} as HTMLElement,
    subscribe: (fn) => {
      subs.add(fn);
      return () => subs.delete(fn);
    },
    act: null,
    store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v), remove: (k) => void mem.delete(k) },
    setInterval: () => {
      const h = ++hn;
      intervals.add(h);
      return h;
    },
    clearInterval: (h) => void intervals.delete(h as number),
    paint: () => {},
  };
  return { reg: new Registry(views, env), mem, subs, intervals, log, emit: (s: S) => [...subs].forEach((f) => f(s)) };
}

describe("registry — 수명 계약", () => {
  it("시작 = 작업 화면 · 저장소 쓰기 0 · 순서 = 대화 | 작업", async () => {
    const t = setup();
    await t.reg.start("work");
    expect(t.reg.current).toBe("work");
    expect(t.mem.size).toBe(0);
    expect(t.reg.ids()).toEqual(["chat", "work"]);
  });
  it("사람이 고름 = 전환 + cys-view 기억 · 새 화면이 선 뒤 옛 화면 내림 · 옛 화면 구독·타이머 0", async () => {
    const t = setup();
    await t.reg.start("work");
    await t.reg.choose("chat");
    expect(t.reg.current).toBe("chat");
    expect(JSON.parse(t.mem.get(VIEW_KEY) as string)).toEqual({ v: 1, id: "chat", decidedBy: "user" });
    expect(t.log).toEqual(["mount:work", "mount:chat", "unmount:work"]);
    expect(t.subs.size).toBe(2);
    expect(t.intervals.size).toBe(1);
    await t.reg.choose("work");
    expect(t.subs.size).toBe(2);
    expect(t.intervals.size).toBe(1);
    expect(t.log.slice(-2)).toEqual(["mount:work", "unmount:chat"]);
  });
  it("100회 왕복 뒤 누수 0(구독·타이머 = 켜진 화면 몫만)", async () => {
    const t = setup();
    await t.reg.start("work");
    for (let i = 0; i < 100; i++) await t.reg.choose(i % 2 ? "work" : "chat");
    expect(t.subs.size).toBe(2);
    expect(t.intervals.size).toBe(1);
    expect(t.reg.liveCounts()).toEqual({ subs: 2, timers: 1 });
  });
  it("전환 도중 또 전환 20회 → 마지막 화면 1개", async () => {
    const t = setup();
    await t.reg.start("work");
    const ps: Promise<void>[] = [];
    for (let i = 0; i < 20; i++) ps.push(t.reg.choose(i % 2 ? "work" : "chat"));
    await Promise.all(ps);
    await t.reg.choose("chat");
    expect(t.reg.current).toBe("chat");
    expect(t.subs.size).toBe(2);
  });
  it("띄우기 실패 → 작업 화면으로 물러남 + 띠 · 3회면 그 실행 동안 단추 흐림", async () => {
    const t = setup({ chatThrows: () => true });
    await t.reg.start("work");
    for (let i = 0; i < FAIL_LIMIT; i++) {
      await t.reg.choose("chat");
      expect(t.reg.current).toBe("work");
      expect(t.reg.band).toBe(FALLBACK_BAND);
    }
    expect(t.reg.disabled("chat")).toBe(true);
    await t.reg.choose("chat");
    expect(t.subs.size).toBe(2);
  });
  it("그리기 중 예외 → 작업 화면으로 물러남 + 띠", async () => {
    const flag = { on: false };
    const t = setup({ paintThrows: flag });
    await t.reg.start("work");
    await t.reg.choose("chat");
    flag.on = true;
    t.emit({ n: 1 }); // registry 가 감싼 구독 안에서 잡힘(밖으로 안 던짐)
    for (let i = 0; i < 5; i++) await Promise.resolve();
    await (t.reg as unknown as { chain: Promise<void> }).chain; // 물러남 전환을 기다림(새 요청 없이)
    expect(t.reg.current).toBe("work");
    expect(t.reg.band).toBe(FALLBACK_BAND);
    expect(t.subs.size).toBe(2);
  });
  it("쓸 수 없는 기기(긍정 신호) → 전환 0 · 까닭 기억 · 저장 0", async () => {
    const t = setup({ chatAvail: { ok: false, why: "cys 밖 마스터" } });
    await t.reg.start("work");
    await t.reg.choose("chat");
    expect(t.reg.current).toBe("work");
    expect(t.reg.unavailable.get("chat")).toBe("cys 밖 마스터");
    expect(t.mem.has(VIEW_KEY)).toBe(false);
  });
});

describe("정적 핀 — 순수 판정 · 배선", () => {
  const dir = new URL("./judge/", import.meta.url); // URL 그대로 fs 에(윈도 「/D:/…」 pathname ENOENT 전례 · VERIFY 지적 8 · clipath.test repoUrl 꼴)
  it("judge/*.ts 에 document·window·localStorage·__TAURI__·Date.now·setTimeout 0(시험 파일 제외)", () => {
    const files = readdirSync(dir, { withFileTypes: true }).map((d) => d.name).filter((f) => f.endsWith(".ts") && !f.endsWith(".test.ts"));
    expect(files.length).toBeGreaterThanOrEqual(4);
    for (const f of files) {
      const src = readFileSync(new URL(f, dir), "utf8").replace(/\/\/.*$/gm, "");
      for (const w of ["document", "window", "localStorage", "__TAURI__", "Date.now", "setTimeout"]) expect(`${f}:${src.includes(w)}`).toBe(`${f}:false`);
    }
  });
  it("main.ts = import 1 + bootViews 1회 · layoutLoaded = true 바로 다음 줄", () => {
    const src = readFileSync(new URL("../main.ts", import.meta.url), "utf8");
    expect(src.split('from "./views/index"').length - 1).toBe(1);
    expect(src.split("bootViews(").length - 1).toBe(1);
    const lines = src.split("\n");
    const i = lines.findIndex((l) => l.includes("bootViews("));
    expect(lines[i - 1].trim()).toBe("layoutLoaded = true;");
  });
  it("chat_send 호출처 = core.ts 의 deliver 1곳 · kind human 고정", () => {
    const core = readFileSync(new URL("./core.ts", import.meta.url), "utf8");
    expect(core.split('"chat_send"').length - 1).toBe(1);
    expect(core).toContain('kind: "human"');
    const main = readFileSync(new URL("../main.ts", import.meta.url), "utf8");
    expect(main.includes("chat_send")).toBe(false);
  });
  it("Tauri: viewcore 등록 · 원자 제출 매개변수(refuse_on_approval·clear_first·human) · send_input 무변경 사용 0", () => {
    const rs = readFileSync(new URL("../../../src-tauri/src/viewcore.rs", import.meta.url), "utf8");
    for (const k of ['"refuse_on_approval": true', '"clear_first": true', '"human": true', '"machine_origin": false', '"queued": false']) expect(rs).toContain(k);
    expect(/send_input\s*\(/.test(rs)).toBe(false); // 기존 send_input 은 refuse_on_approval 을 싣지 않는다(0.5 M2 대조 = R1)
    const main = readFileSync(new URL("../../../src-tauri/src/main.rs", import.meta.url), "utf8");
    expect(main).toContain("viewcore::chat_send,");
    expect(main).toContain("viewcore::chat_transcript,");
    expect(main).toContain("mod viewcore;");
  });
  it("index.html 자리 2개 · views.css 연결 · build.sh 복사 · 전환 단추는 상단 단추 켬끔 목록 밖(div 안)", () => {
    const html = readFileSync(new URL("../../index.html", import.meta.url), "utf8");
    expect(html).toContain('<div id="view-switch"></div>');
    expect(html).toContain('<div id="view-host" hidden></div>');
    expect(html).toContain('href="./views.css"');
    const sh = readFileSync(new URL("../../build.sh", import.meta.url), "utf8");
    expect(sh).toContain("cp src/views/views.css dist/views.css");
  });
});
