// (TICKET=cysr-1119-s11 · DESIGN TC3) 대화 입력칸 끌어 놓기 — 공통층(core) 칩 상태 · 보낸 글 바이트 = 펼친 입력칸 글 · 받는 자리(main.ts 전역 drag-drop 리스너) 원천 검사.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { Sim } from "./testkit";
import { withDroppedFiles } from "./judge/dropfiles";

async function ready(sim: Sim): Promise<void> {
  sim.core.attach();
  await sim.flush();
  await sim.core.poll();
  await sim.flush();
}
const sentTexts = (sim: Sim) => sim.calls.filter((c) => c.cmd === "chat_send").map((c) => c.args?.text);

describe("TC3 core — 칩 상태", () => {
  it("같은 파일 두 번 놓기 = 칩 1개(중복 0) · 빼기 = 그 칩만", () => {
    const sim = new Sim();
    sim.core.addFiles(["/w/a.md"]);
    sim.core.addFiles(["/w/a.md", "/w/b.md"]);
    expect(sim.core.state.files).toEqual(["/w/a.md", "/w/b.md"]);
    sim.core.removeFile("/w/a.md");
    expect(sim.core.state.files).toEqual(["/w/b.md"]);
  });
  it("칩이 바뀌면 화면에 알림(구독자 호출) · 같은 것 다시 놓기 = 알림 0", () => {
    const sim = new Sim();
    let n = 0;
    sim.core.subscribe(() => n++);
    sim.core.addFiles(["/w/a.md"]);
    expect(n).toBe(1);
    sim.core.addFiles(["/w/a.md"]);
    expect(n).toBe(1);
    sim.core.removeFile("/w/nope.md");
    expect(n).toBe(1);
  });
  it("보낸 글 바이트 = 펼친 입력칸 글(chat_send text 그대로) · 받아들인 뒤 칩은 반드시 빔", async () => {
    const sim = new Sim({ recordDelay: () => null });
    await ready(sim);
    sim.core.addFiles(["/w/보고서.md", "/w/my notes.txt"]);
    const want = withDroppedFiles("이 둘을 읽어 줘", sim.core.state.files, false);
    expect(sim.core.submitInput("이 둘을 읽어 줘", false)).toBe(true);
    expect(sim.core.state.files).toEqual([]);
    await sim.advance(5_000);
    expect(sentTexts(sim)).toEqual([want]);
    expect(want).toBe("이 둘을 읽어 줘 @/w/보고서.md '/w/my notes.txt'");
  });
  it("글 없이 칩만 = @경로만 보냄 · 칩 없으면 사람 쓰기 길 글 그대로", async () => {
    const sim = new Sim({ recordDelay: () => null });
    await ready(sim);
    sim.core.addFiles(["/w/a.md"]);
    expect(sim.core.submitInput("", false)).toBe(true);
    await sim.advance(5_000);
    expect(sentTexts(sim)).toEqual(["@/w/a.md"]);
    const plain = new Sim({ recordDelay: () => null }); // 앞 말 확인 전 두 번째 말은 줄을 서므로 따로 잰다
    await ready(plain);
    expect(plain.core.submitInput("  그냥 말\n", false)).toBe(true);
    await plain.advance(5_000);
    expect(sentTexts(plain)).toEqual(["그냥 말"]); // 종전 다듬기(composeOutbound) 그대로
  });
  it("막힌 말(`/clear` 로 시작) = 보내지 않음 · 칩 그대로(고쳐 다시 보낼 수 있게)", async () => {
    const sim = new Sim({ recordDelay: () => null });
    await ready(sim);
    sim.core.addFiles(["/w/a.md"]);
    expect(sim.core.submitInput("/clear", false)).toBe(false);
    expect(sim.core.state.files).toEqual(["/w/a.md"]);
    expect(sentTexts(sim)).toEqual([]);
  });
  it("칩이 든 채 대화 화면을 떠났다 돌아옴 · 마스터 좌석이 바뀜 = 칩 남음(초안과 같이 메모리) → 보낸 뒤에는 빔", async () => {
    const sim = new Sim({ recordDelay: () => null });
    await ready(sim);
    sim.core.addFiles(["/w/a.md"]);
    sim.core.detach();
    await sim.flush();
    sim.core.attach();
    await sim.flush();
    expect(sim.core.state.files).toEqual(["/w/a.md"]);
    sim.seat.surface_id = 9; // 마스터 좌석 바뀜(다시 켜짐 등)
    await sim.core.poll();
    await sim.flush();
    expect(sim.core.state.files).toEqual(["/w/a.md"]);
    expect(sim.core.submitInput("봐", false)).toBe(true);
    await sim.advance(5_000);
    expect(sim.core.state.files).toEqual([]);
    const send = sim.calls.filter((c) => c.cmd === "chat_send");
    expect(send.map((c) => [c.args?.surfaceId, c.args?.text])).toEqual([[9, "봐 @/w/a.md"]]);
  });
  it("빠른 답 등 「그 글 그대로」 길(core.submit) = 칩 무관 · 칩 그대로 남음", async () => {
    const sim = new Sim({ recordDelay: () => null });
    await ready(sim);
    sim.core.addFiles(["/w/a.md"]);
    expect(sim.core.submit("좋아요 — 팀을 만들어 주세요")).toBe(true);
    await sim.advance(5_000);
    expect(sentTexts(sim)).toEqual(["좋아요 — 팀을 만들어 주세요"]);
    expect(sim.core.state.files).toEqual(["/w/a.md"]);
  });
  it("화면 원천: 입력칸 보내기만 submitInput(win) · 빠른 답은 submit 그대로", () => {
    const chat = readFileSync(new URL("./chat/index.ts", import.meta.url), "utf8");
    expect(chat.split("act.submitInput(").length - 1).toBe(1);
    expect(chat).toContain("if (act.submitInput(text, win)) {");
    expect(chat).toContain("if (act.submit(t)) {");
  });
  it("칩은 저장소에 쓰지 않음(메모리만 · 업로드 0)", async () => {
    const sim = new Sim({ recordDelay: () => null });
    await ready(sim);
    sim.core.addFiles(["/w/a.md"]);
    expect([...sim.mem.values()].some((v) => v.includes("/w/a.md"))).toBe(false);
    expect(sim.calls.some((c) => /upload|read_file|read_text/.test(c.cmd))).toBe(false);
  });
});

describe("TC3 받는 자리 — main.ts 전역 drag-drop 리스너(원천)", () => {
  const main = readFileSync(new URL("../main.ts", import.meta.url), "utf8").replace(/\r\n/g, "\n");
  const strip = (s: string) => s.replace(/\/\/.*$/gm, "");
  const a = main.indexOf('await listen("tauri://drag-drop", (e) => {');
  const body = strip(main.slice(a, main.indexOf("\n  });\n", a)));
  it("입력칸 판정이 paneAtPointStrict 앞 · 참이면 대화 길로 가고 끝 · 작업 화면 길(injectPathsToPane) 1회 그대로", () => {
    expect(a).toBeGreaterThan(0);
    const judge = body.indexOf("if (chatInputAtPoint(p.position)) {");
    expect(judge).toBeGreaterThan(0);
    expect(judge).toBeLessThan(body.indexOf("const rt = paneAtPointStrict(p.position);"));
    expect(body.slice(judge, body.indexOf("}", judge))).toContain("void dropPathsToChat(paths);");
    expect(body.split("injectPathsToPane(").length - 1).toBe(1);
  });
  it("chatInputAtPoint = 대화 화면일 때만 · 같은 환산(dropPointToCss) · 놓은 점 직격 요소가 .cv-form 안", () => {
    const s = main.indexOf("function chatInputAtPoint(");
    expect(s).toBeGreaterThan(0);
    const f = strip(main.slice(s, main.indexOf("\n}\n", s)));
    expect(f).toContain('viewsBoot?.registry.current !== "chat"');
    expect(f).toContain("dropPointToCss(pos, window.devicePixelRatio || 1, DROP_PLATFORM)");
    expect(f).toContain("document.elementFromPoint(css.x, css.y)");
    expect(f).toContain('closest(".cv-form")');
  });
  // (1.1.20 #51 · S11 📌2) 끌어 놓는 동안 입력칸 강조 · 대화 화면 밖에 놓으면 입력칸으로 안내(작업 화면 「pane 위」 문구는 작업 화면에만).
  it("끌기 강조 = enter·over 에서 chatInputAtPoint 로 켜고 · leave·drop 에서 끈다 · CSS 짝 규칙 실재", () => {
    for (const ev of ["tauri://drag-enter", "tauri://drag-over"]) {
      const i = main.indexOf(`await listen("${ev}", (e) => {`);
      expect(i).toBeGreaterThan(0);
      const b = strip(main.slice(i, main.indexOf("\n  });\n", i)));
      expect(b).toContain("setChatDropTarget(chatInputAtPoint(p.position));");
    }
    const l = main.indexOf('await listen("tauri://drag-leave", () => {');
    expect(l).toBeGreaterThan(0);
    expect(strip(main.slice(l, main.indexOf("\n  });\n", l)))).toContain("setChatDropTarget(false);");
    expect(body).toContain("setChatDropTarget(false);");
    const f = main.indexOf("function setChatDropTarget(");
    expect(strip(main.slice(f, main.indexOf("\n}\n", f)))).toContain('classList.toggle("cv-drop-target", on)');
    const css = readFileSync(new URL("./views.css", import.meta.url), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
    expect(/\.cv-form\.cv-drop-target\s*\{[^}]*dashed/.test(css)).toBe(true);
  });
  it("입력칸 밖에 놓음 = 대화 화면이면 입력칸 안내(런타임 유무와 무관) · 작업 화면만 「pane 위」 문구", () => {
    const miss = body.indexOf("if (!rt) {");
    const blk = body.slice(miss, body.indexOf("return;", miss));
    const chatAt = blk.indexOf('if (viewsBoot?.registry.current === "chat") toast("watchdog", CHAT_DROP_MISS.name, CHAT_DROP_MISS.detail);');
    expect(chatAt).toBeGreaterThan(0);
    expect(blk.indexOf('else if (panes.size > 0) toast("watchdog", "드롭 취소", "pane 위에 놓아야 삽입됩니다");')).toBeGreaterThan(chatAt);
    expect(main).toContain("파일은 아래 「마스터에게 보낼 말」 칸 위에 놓아 주세요");
  });
  it("dropPathsToChat = ftdrop 결과 3종(같은 순수 함수) · PTY 쓰기 0(send_input·injectRawToPane 0) · 칩 = core.addFiles", () => {
    const s = main.indexOf("async function dropPathsToChat(");
    expect(s).toBeGreaterThan(0);
    const f = strip(main.slice(s, main.indexOf("\n}\n", s)));
    for (const k of ["splitPath(", 'invoke("list_dir"', "classifyPathCheck(", "pathCheckToast(", "renderFileTree()", "addFiles(paths)"]) expect(f).toContain(k);
    expect(f).not.toContain("send_input");
    expect(f).not.toContain("injectRawToPane");
  });
});
