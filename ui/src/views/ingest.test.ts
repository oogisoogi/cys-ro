// 데몬 사건 단일 입구 시험 — TICKET=cysr-1116-s2-1119 · integ HANDOFF I3·S4-3(조각 3 `listen` · 조각 4 `listenDaemon` 두 구독 → main.ts 한 구독 + 배선 1줄).
//   ① 화면 공통층 입구(views/index.ts)는 daemon-event 를 스스로 구독하지 않는다 · default_socket_slug 를 다시 묻지 않는다
//   ② main.ts 의 daemon-event 구독 = 1 · onDaemonEvent 머리에 viewsIngest 배선 1줄(본부 slug = main.ts 가 이미 받은 값)
//   ③ core.ingest = 두 처리기(조각 3 onDaemonEvent · 조각 4 confirm.onEvent)에 같은 사건을 한 번씩
//   (행동 시험 — 대화 화면을 열기 전 deadman 이 장부에 남음 — 은 confirm.test.ts 「S4-3」)
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";

const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const INDEX = strip(readFileSync(new URL("./index.ts", import.meta.url), "utf8"));
const CORE = readFileSync(new URL("./core.ts", import.meta.url), "utf8");
const MAIN = readFileSync(new URL("../main.ts", import.meta.url), "utf8");

describe("데몬 사건 구독 = 하나(I3·S4-3)", () => {
  it("① views/index.ts: listen·listenDaemon·defaultSlug·default_socket_slug 0", () => {
    for (const w of ["listen", "listenDaemon", "defaultSlug", "default_socket_slug", "__TAURI__"]) expect(`${w}:${INDEX.includes(w)}`).toBe(`${w}:false`);
  });
  it("② main.ts: daemon-event 구독 1 · viewsIngest 배선 1줄 = onDaemonEvent 머리(첫 문장 const name 바로 뒤)", () => {
    expect(MAIN.split('listen("daemon-event"').length - 1).toBe(1);
    expect(MAIN.split("viewsIngest(").length - 1).toBe(1); // 배선 1(import 줄은 「viewsIngest,」)
    expect(MAIN).toContain('import { bootViews, viewsIngest, workRuntimeWanted } from "./views/index";');
    const body = MAIN.slice(MAIN.indexOf("function onDaemonEvent(event: Record<string, unknown>) {"));
    const lines = body.split("\n");
    expect(lines[1].trim()).toBe('const name = String(event.name ?? "");');
    expect(lines[2].trim().startsWith("viewsIngest(event, defaultSocketSlug);")).toBe(true);
  });
  it("③ core.ingest = 본부 slug 넣기 + 두 처리기 한 번씩", () => {
    const at = CORE.indexOf("  ingest(raw: unknown, hqSlug: string | null): void {");
    expect(at).toBeGreaterThan(0);
    const body = CORE.slice(at, CORE.indexOf("\n  }\n", at));
    expect(body.split("this.onDaemonEvent(raw);").length - 1).toBe(1);
    expect(body.split("this.confirm.onEvent(raw);").length - 1).toBe(1);
    expect(body).toContain("this.confirm.setHqSlug(hqSlug);");
  });
  it("④ (codex 1R major) 공통층이 서기 전 사건 = 상한 32 버퍼 → bootViews 직후 한 번 흘림", () => {
    expect(INDEX).toContain("preBoot.push([ev, hqSlug]);");
    expect(INDEX).toContain("if (preBoot.length > PRE_BOOT_MAX) preBoot.shift();");
    expect(INDEX).toContain("for (const [ev, slug] of preBoot.splice(0)) core.ingest(ev, slug);");
    expect(INDEX).toContain("const PRE_BOOT_MAX = 32;");
  });
});

describe("(codex 1R blocking) 자리표 닫기 직전 재판정", () => {
  it("closePane 바로 앞에서 그 자리를 지금 화면 줄 수로 다시 판정하고, 닫기 판정이 아니면 닫지 않는다", () => {
    const tick = MAIN.slice(MAIN.indexOf("async function refreshPaneTitles() {"));
    const close = tick.indexOf("await closePane(sid, ws.socket);");
    const fresh = tick.indexOf("const fresh = decidePlaceholders({");
    expect(fresh).toBeGreaterThan(0);
    expect(fresh).toBeLessThan(close);
    const seg = tick.slice(fresh, close);
    expect(seg).toContain("placeholders: new Set([sid]),");
    expect(seg).toContain("lineCount: (_w, x) => placeholderScreenLines(panes.get(paneKey(x, ws.socket))?.term),");
    expect(seg).toContain("if (!fresh?.close) continue;");
    expect(seg.indexOf("if (!fresh?.close) continue;")).toBeLessThan(seg.indexOf("placeholderSids.delete(sid);"));
  });
});
