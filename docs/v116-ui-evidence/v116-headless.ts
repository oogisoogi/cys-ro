// v116-ui 헤드리스 시험 — ui/dist 실번들 + Tauri 흉내(shim.js) · 별도 바이너리 chrome-headless-shell · 종료 시 크롬 정리.
// usage: DIST=<ui/dist> CHS=<chrome-headless-shell> [OUT=<캡처 폴더>] [ONLY=c1,c3] bun v116-headless.ts → exit 0 PASS / 1 FAIL
// 판정 5축(브리프 v116-ui-close §6):
//   c1 산 창 Close·⌘W → 확인 1회(기본 포커스 = 취소 · 겹침 0 · 취소 시 close_surface 0) · exited 창 Close → 확인 0 · 바로 닫힘
//   c2 복원 직후 목록 조회 실패(이벤트 유실 잔재) → 다음 틱에 [exited] 옛 창 0
//   c3 창 2개 중 1개 exited(이벤트) → 남은 창 폭 = 전체 · PTY cols 재조정
//   c4 기본 화면 상단에 창 만들기 단추(+ New·Split) 0 · 전문가 모드 칸에 「창 만들기」 → 오른쪽/아래 메뉴
//   c5 작업기억이 정본 경로(~/.cys/pack/round/SESSION_STATE.md)에만 있을 때 복원 카드가 그 내용을 싣는다
// 원형 = D4-evidence/headless-layout-check.ts(996) 의 CDP 드라이버.
import { spawn } from "bun";
import { mkdtempSync, readFileSync, writeFileSync, rmSync, existsSync, mkdirSync } from "fs";
import { join } from "path";

const H = import.meta.dir;
const DIST = process.env.DIST!;
const CH = process.env.CHS!;
const OUT = process.env.OUT || "";
const ONLY = (process.env.ONLY || "c1,c2,c3,c4,c5").split(",");
const shim = readFileSync(join(H, "shim.js"), "utf8");
if (OUT) mkdirSync(OUT, { recursive: true });

const server = Bun.serve({
  port: 0, hostname: "127.0.0.1",
  fetch(req) {
    const p = new URL(req.url).pathname.replace(/^\/+/, "") || "index.html";
    const f = join(DIST, p);
    if (!existsSync(f)) return new Response("nf", { status: 404 });
    const ct = p.endsWith(".html") ? "text/html; charset=utf-8" : p.endsWith(".js") ? "text/javascript; charset=utf-8" : p.endsWith(".css") ? "text/css; charset=utf-8" : "application/octet-stream";
    return new Response(Bun.file(f), { headers: { "content-type": ct } });
  },
});
const prof = mkdtempSync("/tmp/v116chs-");
const chrome = spawn([CH, "--headless", "--remote-debugging-port=0", `--user-data-dir=${prof}`, "--no-first-run", "--hide-scrollbars", "about:blank"], { stderr: "pipe" });
let cleaned = false;
const cleanup = () => { if (cleaned) return; cleaned = true; try { chrome.kill(9); } catch {} server.stop(true); try { rmSync(prof, { recursive: true, force: true }); } catch {} };
process.on("exit", cleanup); process.on("SIGINT", () => { cleanup(); process.exit(130); }); process.on("SIGTERM", () => { cleanup(); process.exit(143); });

let port = 0;
for (let i = 0; i < 100 && !port; i++) { await Bun.sleep(100); const f = join(prof, "DevToolsActivePort"); if (existsSync(f)) port = Number(readFileSync(f, "utf8").split("\n")[0]); }
if (!port) { console.log("NO-CDP"); cleanup(); process.exit(2); }
const tl = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json() as any[];
const ws = new WebSocket(tl.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pend = new Map<number, (v: any) => void>(); const logs: string[] = [];
ws.onmessage = (m) => { const d = JSON.parse(String(m.data)); if (d.id && pend.has(d.id)) { pend.get(d.id)!(d); pend.delete(d.id); } else if (d.method === "Runtime.exceptionThrown") logs.push("EXC " + (d.params.exceptionDetails?.exception?.description || d.params.exceptionDetails?.text || "").slice(0, 200)); };
const cdp = (method: string, params: any = {}) => new Promise<any>((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr: string) => (await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
const shot = async (name: string) => { if (!OUT) return; const r = await cdp("Page.captureScreenshot", { format: "png" }); writeFileSync(join(OUT, name), Buffer.from(r.result.data, "base64")); };
await cdp("Page.enable"); await cdp("Runtime.enable");
await cdp("Page.addScriptToEvaluateOnNewDocument", { source: shim });
await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
// preLS = 앱 적재 **전** 같은 출처 빈 문서에서 실행(localStorage 준비) · post = 적재 직후(흉내층 값 주입)
const load = async (sc: string, preLS = "", post = "") => {
  await cdp("Page.navigate", { url: `http://127.0.0.1:${server.port}/blank-origin` });
  await Bun.sleep(150);
  await ev(`localStorage.setItem("cys-layout-v2", localStorage.getItem("cys-layout-v2") ?? "{}"); ${preLS}`);
  await cdp("Page.navigate", { url: `http://127.0.0.1:${server.port}/index.html?sc=${sc}` });
  if (post) { await Bun.sleep(5); await ev(post); }
  await Bun.sleep(Number(process.env.SETTLE || 3500));
};
// 도우미(페이지 안) — 창 찾기 · 호출 계수
const PANE = (needle: string) => `[...document.querySelectorAll("#root .pane")].find(p => (p.querySelector(".pane-title-text")?.textContent||"").includes(${JSON.stringify(needle)}))`;
const NCALL = (cmd: string) => `window.__shimCalls.filter(c => c.cmd === ${JSON.stringify(cmd)}).length`;
const key = (k: string) => `window.dispatchEvent(new KeyboardEvent("keydown", { key: ${JSON.stringify(k)}, metaKey: true, bubbles: true, cancelable: true }))`;

const fails: string[] = [];
const check = (name: string, ok: boolean, detail: string) => { console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${detail}`); if (!ok) fails.push(name); };

if (ONLY.includes("c1")) {
  await load("two");
  await ev(`${PANE("master")}.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
  await ev(`document.getElementById("btn-close").click()`);
  await Bun.sleep(200);
  const a = await ev(`({ ov: document.querySelectorAll(".modal-overlay").length, focusNo: document.activeElement?.classList.contains("modal-no") ?? false, closes: ${NCALL("close_surface")}, text: document.querySelector(".modal-overlay")?.innerText ?? "" })`);
  await shot("c1-close-confirm.png");
  check("c1a 산 창 Close → 확인 1회 · 기본 포커스 = 취소 · 어느 창인지 이름 표시", a.ov === 1 && a.focusNo && a.closes === 0 && a.text.includes("「1 · master」"), JSON.stringify({ ov: a.ov, focusNo: a.focusNo, closes: a.closes }));
  if (a.ov) console.log("     문안: " + a.text.replace(/\n+/g, " / "));
  await ev(`document.querySelector(".modal-no")?.click()`);
  await Bun.sleep(200);
  const b = await ev(`({ ov: document.querySelectorAll(".modal-overlay").length, panes: document.querySelectorAll("#root .pane").length, closes: ${NCALL("close_surface")} })`);
  check("c1b 취소 → 창 그대로 · close_surface 0", b.ov === 0 && b.panes === 2 && b.closes === 0, JSON.stringify(b));
  await ev(key("w")); await Bun.sleep(150); await ev(key("w")); await Bun.sleep(150);
  const c = await ev(`({ ov: document.querySelectorAll(".modal-overlay").length, closes: ${NCALL("close_surface")} })`);
  check("c1c 산 창 ⌘W 두 번 → 확인 창 1개(겹침 0) · close_surface 0", c.ov === 1 && c.closes === 0, JSON.stringify(c));
  await ev(`window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }))`);
  await Bun.sleep(150);
  await ev(`document.getElementById("btn-close").click()`); await Bun.sleep(150);
  await ev(`document.querySelector(".modal-yes")?.click()`); await Bun.sleep(400);
  const d = await ev(`({ ov: document.querySelectorAll(".modal-overlay").length, panes: document.querySelectorAll("#root .pane").length, closed: window.__shimCalls.filter(c => c.cmd === "close_surface").map(c => c.args.surfaceId) })`);
  check("c1d 확인 → 그 창만 닫힘", d.ov === 0 && d.panes === 1 && JSON.stringify(d.closed) === "[1]", JSON.stringify(d));
  // (Fable 적대 MAJOR-1) Control Center 가 열린 채 ⌘W → 확인 창이 **보이는 맨 위**에 있어야 한다(CC 뒤에 숨으면 안 된다)
  await load("two");
  await ev(`${PANE("master")}.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
  await ev(`document.getElementById("btn-cc").click()`); await Bun.sleep(300);
  const ccBefore = await ev(`!document.getElementById("cc-panel").hidden`);
  await ev(key("w")); await Bun.sleep(300);
  const f = await ev(`(() => { const m = document.querySelector(".modal-overlay .modal"); if (!m) return { modal: false }; const r = m.getBoundingClientRect(); const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return { modal: true, onTop: !!top && m.contains(top), ccHidden: document.getElementById("cc-panel").hidden, closes: ${NCALL("close_surface")} }; })()`);
  check("c1f Control Center 열린 채 ⌘W → CC 먼저 닫힘 · 확인 창이 맨 위에 보임 · 닫기 0", ccBefore && f.modal && f.onTop && f.ccHidden && f.closes === 0, JSON.stringify({ ccBefore, ...f }));
  await ev(`window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }))`); await Bun.sleep(150);
  const g = await ev(`({ ov: document.querySelectorAll(".modal-overlay").length, focusInPane: !!document.activeElement?.closest?.("#root .pane") })`);
  check("c1g 취소(Escape) 뒤 키보드 포커스가 그 창으로 돌아온다", g.ov === 0 && g.focusInPane, JSON.stringify(g));
  // exited 창 — 이벤트 없이 종료(창에 [exited] 남음) → Close 는 확인 없이 바로
  await load("two");
  await ev(`window.__shimExit(2, false)`); await Bun.sleep(3500);
  await ev(`${PANE("worker")}.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
  await ev(`document.getElementById("btn-close").click()`); await Bun.sleep(400);
  const e = await ev(`({ ov: document.querySelectorAll(".modal-overlay").length, closed: window.__shimCalls.filter(c => c.cmd === "close_surface").map(c => c.args.surfaceId), panes: document.querySelectorAll("#root .pane").length })`);
  check("c1e exited 창 Close → 확인 0 · 바로 닫힘", e.ov === 0 && JSON.stringify(e.closed) === "[2]" && e.panes === 1, JSON.stringify(e));
}

if (ONLY.includes("c2")) {
  await load("two");
  // 이벤트 유실 종료(창 2 = [exited] 잔재) → 복원 완료 신호 → 바로 다음 조회 1회 실패 주입
  await ev(`window.__shimExit(2, false)`); await Bun.sleep(3500);
  const before = await ev(`document.querySelectorAll("#root .pane").length`);
  // ⚠실패 창 5초(틱 3초 + 여유): 복원 완료 뒤 **무장된 패스가 적어도 1회** 조회 실패를 겪게 한다. 횟수로 주입하면
  //   (종전 판) 완료 처리기의 미제출 안내 조회나 무장 전에 시작된 틱이 실패를 먹어 재현이 시각에 따라 갈렸다.
  await ev(`window.__shimFailUntil = Date.now() + 5000; window.__shimEmit("restore-progress", { phase: "done", hq_ok: true, ok: 0, fail: 0 })`);
  await Bun.sleep(10000); // 실패 창 5초 + 성공 틱 1회 이상
  const a = await ev(`({ failWindowOver: Date.now() > window.__shimFailUntil, panes: document.querySelectorAll("#root .pane").length, exitedTitles: [...document.querySelectorAll(".pane-title-text")].filter(t => t.textContent.includes("[exited]")).length })`);
  check("c2 조회 실패 뒤 다음 틱 → [exited] 옛 창 0", before === 2 && a.panes === 1 && a.exitedTitles === 0, JSON.stringify({ before, ...a }));
}

if (ONLY.includes("c3")) {
  await load("two");
  const lastCols = (sid: number) => `(window.__shimCalls.filter(c => c.cmd === "resize_surface" && c.args.surfaceId === ${sid}).at(-1)?.args.cols ?? null)`;
  const b = await ev(`({ root: document.getElementById("root").getBoundingClientRect().width, pane: ${PANE("master")}.getBoundingClientRect().width, cols: ${lastCols(1)} })`);
  await ev(`window.__shimExit(2, true)`); await Bun.sleep(1500);
  const a = await ev(`({ root: document.getElementById("root").getBoundingClientRect().width, pane: ${PANE("master")}.getBoundingClientRect().width, cols: ${lastCols(1)}, panes: document.querySelectorAll("#root .pane").length, flex: ${PANE("master")}.style.flex })`);
  await shot("c3-remaining-width.png");
  check("c3 남은 창 폭 = 전체 · PTY cols 재조정", a.panes === 1 && Math.abs(a.pane - a.root) <= 2 && a.cols > b.cols * 1.6, `before ${JSON.stringify(b)} → after ${JSON.stringify(a)}`);
}

if (ONLY.includes("c4")) {
  await load("two", `localStorage.removeItem("cys-expert-mode")`);
  const a = await ev(`(() => { const vis = (el) => !!el && el.offsetParent !== null; const tb = [...document.querySelectorAll("#topbar button")].filter(vis).map(b => b.textContent.trim()); const all = [...document.querySelectorAll("body *")].filter(vis); const hits = all.filter(el => /new split|split|\\+ New|창 만들기/i.test([...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(""))).map(el => el.textContent.trim().slice(0, 20)); return { tb, hits }; })()`);
  await shot("c4a-beginner.png");
  check("c4a 초보 화면 창 만들기·Split·New 단추 0", a.hits.length === 0, JSON.stringify(a));
  await load("two", `localStorage.setItem("cys-expert-mode", "1")`);
  const b = await ev(`(() => { const btn = [...document.querySelectorAll("#ws-expert button")].find(x => x.textContent.includes("창 만들기")); if (!btn || btn.offsetParent === null) return { btn: false }; btn.click(); const items = [...document.querySelectorAll("#ctx-menu .ctx-item")].map(x => x.textContent); return { btn: true, items }; })()`);
  await shot("c4b-expert-create.png");
  const n0 = await ev(`document.querySelectorAll("#root .pane").length`);
  await ev(`[...document.querySelectorAll("#ctx-menu .ctx-item")][1]?.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }))`);
  await Bun.sleep(600);
  const n1 = await ev(`({ panes: document.querySelectorAll("#root .pane").length, col: document.querySelectorAll("#root .split.col").length })`);
  check("c4b 전문가 칸 「창 만들기」 → 오른쪽/아래 메뉴 · 아래 누르면 세로 분할", b.btn && b.items?.length === 2 && n1.panes === n0 + 1 && n1.col >= 1, JSON.stringify({ ...b, n0, ...n1 }));
}

if (ONLY.includes("c5")) {
  const body = "# 작업기억\\n2026-09-23 22:10 저장\\n## 완료\\n- 정본 경로 기록 표시 시험 줄\\n## 진행 중\\n- 진행 줄\\n## 결정 필요\\n- 없음\\n";
  await load("two", "", `window.__shimFiles["/Users/u/.cys/pack/round/SESSION_STATE.md"] = "${body}"`);
  await Bun.sleep(16000); // 카드 유예(복원 신호 없음 → 15초 뒤 표시)
  const a = await ev(`({ card: !!document.getElementById("restore-brief"), text: document.getElementById("restore-brief")?.innerText ?? "" })`);
  check("c5 정본 경로 기록 → 카드 표시", a.card && a.text.includes("정본 경로 기록 표시 시험 줄") && !a.text.includes("찾지 못했"), JSON.stringify({ card: a.card, text: a.text.replace(/\n+/g, " / ").slice(0, 240) }));
}

if (ONLY.includes("c5")) {
  // 정본 파일이 설치 골격 그대로(고정 3절 제목 없음)면 카드는 「하던 일을 복원했어요」·빈 절을 싣지 않는다(T4 무회귀).
  const skel = readFileSync(join(H, "../../cysjavis-pack/round/SESSION_STATE.md"), "utf8");
  await load("two", "", `window.__shimFiles["/Users/u/.cys/pack/round/SESSION_STATE.md"] = ${JSON.stringify(skel)}`);
  await Bun.sleep(16000);
  const a = await ev(`({ card: !!document.getElementById("restore-brief"), text: document.getElementById("restore-brief")?.innerText ?? "" })`);
  check("c5b 정본 = 설치 골격(3절 없음) → 짧은 카드 · 빈 문장 0", a.card && !a.text.includes("하던 일을 복원") && !a.text.includes("적힌 것이 없습니다"), JSON.stringify({ card: a.card, text: a.text.replace(/\n+/g, " / ").slice(0, 200) }));
}

if (logs.length) console.log("page exceptions:\n  " + logs.slice(0, 5).join("\n  "));
console.log(fails.length ? `FAIL (${fails.length}): ${fails.join(" · ")}` : "ALL PASS");
cleanup();
process.exit(fails.length ? 1 : 0);
