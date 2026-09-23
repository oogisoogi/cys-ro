// v116-ui 헤드리스 시험 — ui/dist 실번들 + Tauri 흉내(shim.js) · 별도 바이너리 chrome-headless-shell · 종료 시 크롬 정리.
// usage: DIST=<ui/dist> CHS=<chrome-headless-shell> [OUT=<캡처 폴더>] [ONLY=c1,c3] bun v116-headless.ts → exit 0 PASS / 1 FAIL
// 판정 5축(브리프 v116-ui-close §6):
//   c1 산 창 Close·⌘W → 확인 1회(기본 포커스 = 취소 · 겹침 0 · 취소 시 close_surface 0) · exited 창 Close → 확인 0 · 바로 닫힘
//   c2 복원 직후 목록 조회 실패(이벤트 유실 잔재) → 다음 틱에 [exited] 옛 창 0
//   c3 창 2개 중 1개 exited(이벤트) → 남은 창 폭 = 전체 · PTY cols 재조정
//   c4 기본 화면 상단에 창 만들기 단추(+ New·Split) 0 · 전문가 모드 칸에 「창 만들기」 → 오른쪽/아래 메뉴
//   c6 복원 카드가 떠 있을 때 뒤에 뜬 경보(에이전트 사망 알림)가 카드에 가려지지 않는다(D4 #21 · 1280·800 폭)
//   c7 상단바 데몬 라벨 = 판번만(pid·소켓 경로·daemon 0) · 전문은 툴팁(D4 #5)
//   c8 이름 없는 본부 탭 = 「본부」 · 화면 어디에도 「non title」 0 · 탭 삭제 확인도 같은 이름(D4 #4)
//   c9 짧은 창(위 내용 없음)에서 첫 위 휠 → 「접어 두었습니다」 안내 0 · 긴 출력 맨 위 도달 → 안내 1(D4 #6)
//   c10 사이드바 「7d·<모델>」 게이지가 프로브 주기 안(150초 전 관측)에서는 흐려지지 않는다 · 400초 전이면 흐려진다(D4 #11)
//   c5 작업기억이 정본 경로(~/.cys/pack/round/SESSION_STATE.md)에만 있을 때 복원 카드가 그 내용을 싣는다
// 원형 = D4-evidence/headless-layout-check.ts(996) 의 CDP 드라이버.
import { spawn } from "bun";
import { mkdtempSync, readFileSync, writeFileSync, rmSync, existsSync, mkdirSync } from "fs";
import { join } from "path";

const H = import.meta.dir;
const DIST = process.env.DIST!;
const CH = process.env.CHS!;
const OUT = process.env.OUT || "";
const ONLY = (process.env.ONLY || "c1,c2,c3,c4,c5,c6,c7,c8,c9,c10").split(",");
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
  const a = await ev(`({ failWindowOver: Date.now() > window.__shimFailUntil, panes: document.querySelectorAll("#root .pane").length, exitedTitles: [...document.querySelectorAll(".pane-title-text")].filter(t => t.textContent.includes("[exited]") || t.textContent.includes("(끝남)")).length })`);
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

if (ONLY.includes("c6")) {
  for (const w of [1280, 800]) {
    await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: 820, deviceScaleFactor: 1, mobile: false });
    const body = "## 완료\\n- 끝난 일 1\\n- 끝난 일 2\\n## 진행 중\\n- 하던 일 1\\n- 하던 일 2\\n## 결정 필요\\n- 정할 일\\n2026-09-23 22:10";
    await load("two", "", `window.__shimFiles["/Users/u/.cys/pack/round/SESSION_STATE.md"] = "${body}"`);
    await Bun.sleep(16000); // 카드 유예
    // 경보 3건을 겹쳐 쌓는다(Fable F2 — 짧은 1건만으로는 알림 줄이 카드의 [닫기]까지 자라는 경우를 못 잰다)
    for (const role of process.env.MANY ? ["w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8", "w9", "w10"] : ["worker", "cso", "master"])
      await ev(`window.__shimEmit("daemon-event", { name: "agent.exited", category: "agent", surface_id: 2, payload: { role: "${role}" } })`);
    await Bun.sleep(400);
    const a = await ev(`(() => {
      const card = document.getElementById("restore-brief"); const t = [...document.querySelectorAll("#toasts .toast")].at(-1);
      if (!card || !t) return { card: !!card, toast: !!t };
      const r = document.getElementById("toasts").getBoundingClientRect(), c = card.getBoundingClientRect();
      const all = [...document.querySelectorAll("#toasts .toast")];
      // 알림 칸(40vh) 안에서 스크롤로 밀려난 알림은 원래 안 보인다 — 칸 안에 중심이 있는 알림만 「맨 위」를 잰다
      const inView = all.filter((x) => { const q = x.getBoundingClientRect(); const cy = q.top + q.height / 2; return cy >= r.top && cy <= r.bottom; });
      const eachOnTop = inView.length > 0 && inView.every((x) => { const q = x.getBoundingClientRect(); const e = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2); return !!e && x.contains(e); });
      const overlap = !(r.right <= c.left || r.left >= c.right || r.bottom <= c.top || r.top >= c.bottom);
      const cb = card.querySelector(".rb-close")?.getBoundingClientRect();
      const cbTop = cb ? document.elementFromPoint(cb.left + cb.width / 2, cb.top + cb.height / 2) : null;
      return { card: true, toast: true, toasts: all.length, inView: inView.length, toastOnTop: eachOnTop, overlap, closeReachable: !!cbTop && cbTop.classList.contains("rb-close"), cardInView: c.left >= 0 && c.right <= innerWidth + 1, text: t.innerText.slice(0, 40) };
    })()`);
    if (w === 1280) await shot("c6-alert-over-card.png");
    const ok = a.card && a.toast && a.toastOnTop && a.cardInView && a.closeReachable && !a.overlap;
    check(`c6 w${w} 복원 카드가 떠 있어도 경보 ${process.env.MANY ? "10" : "3"}건이 보인다(맨 위 · 겹침 0 · 카드 화면 안 · 카드 닫기 눌림)`, ok, JSON.stringify(a));
  }
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
}

if (ONLY.includes("c7")) {
  for (const w of [1280, 800]) {
    await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: 820, deviceScaleFactor: 1, mobile: false });
    await load("two");
    const a = await ev(`(() => { const el = document.getElementById("daemon-info"); const first = el.firstChild?.textContent ?? ""; return { text: first, title: el.title, fits: el.clientWidth >= el.scrollWidth }; })()`);
    check(`c7 w${w} 상단바 라벨 = 판번만(찌그러짐 0) · 툴팁 = 전문`, a.text === "엔진 v1.1.6" && a.fits && !/pid|sock|daemon|\/Users\//.test(a.text) && a.title.includes("pid=4242") && a.title.includes("sock="), JSON.stringify(a));
  }
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
}

if (ONLY.includes("c8")) {
  await load("two", `localStorage.removeItem("cys-layout-v2")`);
  const a = await ev(`(() => { const names = [...document.querySelectorAll(".ws-tab .ws-name")].map(x => x.textContent); return { names, nonTitle: document.body.innerText.includes("non title") }; })()`);
  await ev(`document.querySelector(".ws-tab .ws-close")?.click()`); await Bun.sleep(300);
  const b = await ev(`({ modal: document.querySelector(".modal-overlay h3")?.textContent ?? "" })`);
  await ev(`document.querySelector(".modal-no")?.click()`);
  await shot("c8-hq-tab.png");
  check("c8 본부 탭 이름 = 본부 · non title 0 · 삭제 확인도 본부", a.names[0] === "본부" && !a.nonTitle && b.modal.includes("본부") && !b.modal.includes("non title"), JSON.stringify({ ...a, ...b }));
}

if (ONLY.includes("c9")) {
  const hintCount = `[...document.querySelectorAll("#toasts .toast")].filter(t => t.innerText.includes("접어 두었습니다")).length`;
  const wheelUp = (who: string, n: number) => `(() => { const h = ${PANE(who)}.querySelector(".xterm"); for (let i = 0; i < ${n}; i++) h.dispatchEvent(new WheelEvent("wheel", { deltaY: -120, bubbles: true, cancelable: true })); })()`;
  await load("two");
  await ev(wheelUp("master", 1)); await Bun.sleep(400);
  const a = await ev(hintCount);
  // 긴 출력(스크롤백 생김) 뒤 맨 위까지 올린다
  await ev(`window.__shimEmit("out-2", btoa(Array.from({ length: 300 }, (_, i) => "line " + i).join("\\r\\n")))`); await Bun.sleep(400);
  await ev(wheelUp("worker", 400)); await Bun.sleep(600);
  const b = await ev(hintCount);
  check("c9 짧은 창 첫 위 휠 → 안내 0 · 긴 출력 맨 위 → 안내 1", a === 0 && b === 1, JSON.stringify({ shortPane: a, afterLongTop: b }));
}

if (ONLY.includes("c10")) {
  const acct = (scopedAge: number) => `(() => { const now = Date.now() / 1000; window.__shimAccounts = [{ account_id: "a1", provider: "claude", label: "u@example.com", plan: null, adapter: true, profiles: [".claude"], source: "statusline", updated_at: now - 5, stale_secs: 5,
    rate: [{ label: "5h", used_pct: 20, resets_at: now + 3600 }, { label: "7d", used_pct: 30, resets_at: now + 86400 }],
    scoped: [{ model: "Fable", used_pct: 6, resets_at: now + 86400, updated_at: now - ${scopedAge}, source: "oauth" }] }]; })()`;
  const read = `(() => { const r = [...document.querySelectorAll(".wsu-rate")].find(x => x.textContent.includes("Fable")); return r ? { found: true, stale: r.classList.contains("stale"), text: r.textContent.trim().slice(0, 40) } : { found: false }; })()`;
  const res: any = {};
  for (const age of [150, 400]) {
    await load("two", "", acct(age));
    await Bun.sleep(4000);
    res[age] = await ev(read);
  }
  check("c10 7d·Fable 게이지: 150초 전 관측 = 흐림 0 · 400초 전 = 흐림", res[150].found && !res[150].stale && res[400].found && res[400].stale, JSON.stringify(res));
}

if (logs.length) console.log("page exceptions:\n  " + logs.slice(0, 5).join("\n  "));
console.log(fails.length ? `FAIL (${fails.length}): ${fails.join(" · ")}` : "ALL PASS");
cleanup();
process.exit(fails.length ? 1 : 0);
