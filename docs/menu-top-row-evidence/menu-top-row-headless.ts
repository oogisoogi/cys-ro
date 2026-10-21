// 상담소·아고라 상단 이동 실렌더 시험 — ui/dist 실번들 + Tauri 흉내(../v116-ui-evidence/shim.js) · chrome-headless-shell · 종료 시 크롬 정리.
// TICKET=cysr-menu-top-row · 박사님 2026-10-21 「상담소, 아고라 메뉴 위치가 왼쪽 메뉴바면 애매하다. 상단 피드백과 함께 배치하자.
// 순서는 피드백 상담소 아고라 순을 제안한다.」
// usage: DIST=<ui/dist> CHS=<chrome-headless-shell> [OUT=<캡처 폴더>] [ONLY=m1,m2] [BEFORE=1] bun menu-top-row-headless.ts → exit 0 PASS / 1 FAIL
//   BEFORE=1 = 1.1.9 번들(옮기기 전) 기록 모드 — 판정 없이 자리만 적고 캡처한다(전 캡처).
// 판정 칸:
//   m1 기본 화면(1280×820 · 저장 0): 상단에 보이는 단추 맨 앞 넷 = 피드백 · 상담소 · 아고라 · 정렬 · 사이드바(#wsbar)에 상담소·아고라 0
//   m2 누르면 종전 그대로: 상담소 = 상담소 창(counsel_room_list 1) · 아고라 = open_agora_window 1(앱이 주소를 열지 않음)
//   m3 키보드: 피드백에서 Tab → 상담소 → Tab → 아고라 · 상담소에서 Enter = 상담소 창 · 툴팁(title) = 정본 문구
//   m4 폭 1280·1024·800·640·390(+ 상담소 뱃지 「12」 켠 채): 상단바 높이 38 그대로 · 이웃 단추와 겹침 0 · 글자 잘림 0 · 줄바꿈 0 ·
//      800 이상 = 세 단추가 스크롤 없이 화면 안 · 그 아래 = 상단바 가로 스크롤로 끝까지 닿음(기록)
//   m5 1.1.9 에서 상단 단추 순서를 저장한 사람(상담소·아고라 없는 저장) → 새 판에서 상담소·아고라가 피드백 바로 뒤 · 켬
//   m6 화면 설정 → 상단 단추 목록에 「상담소」·「아고라」 줄(피드백 다음 · 켬 · 끌 수 있음)
// 원형 = docs/v116-ui-evidence/v116-headless.ts 의 CDP 드라이버.
import { spawn } from "bun";
import { mkdtempSync, readFileSync, writeFileSync, rmSync, existsSync, mkdirSync } from "fs";
import { join } from "path";

const H = import.meta.dir;
const DIST = process.env.DIST!;
const CH = process.env.CHS!;
const OUT = process.env.OUT || "";
const BEFORE = process.env.BEFORE === "1";
const ONLY = (process.env.ONLY || "m1,m2,m3,m4,m5,m6").split(",");
const shim = readFileSync(join(H, "../v116-ui-evidence/shim.js"), "utf8");
// 상담소 뱃지 흉내 — sessionStorage "__menuUnread" 가 있으면 counsel_unread 가 그 숫자로 답한다(없으면 흉내층 기본 = null).
const extra = `(() => { const n = sessionStorage.getItem("__menuUnread"); if (n === null) return; const o = window.__TAURI__.core.invoke;
  const w = (c, a) => c === "counsel_unread" ? (window.__shimCalls.push({ cmd: c, args: a || {} }), Promise.resolve({ exists: true, mtime_ms: 1, text: JSON.stringify({ v: 1, count: Number(n) }) })) : o(c, a);
  window.__TAURI__.core.invoke = w; window.__TAURI_INTERNALS__.invoke = w; })();`;
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
const prof = mkdtempSync("/tmp/menutop-chs-");
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
await cdp("Page.addScriptToEvaluateOnNewDocument", { source: extra });
await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
const size = (w: number, h = 820) => cdp("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false });
await size(1280);
// preLS = 앱 적재 **전** 같은 출처 빈 문서에서 실행(localStorage·sessionStorage 준비) — 칸마다 저장을 비우고 시작한다.
const load = async (preLS = "") => {
  await cdp("Page.navigate", { url: `http://127.0.0.1:${server.port}/blank-origin` });
  await Bun.sleep(150);
  await ev(`sessionStorage.clear(); localStorage.clear(); ${preLS}`);
  await cdp("Page.navigate", { url: `http://127.0.0.1:${server.port}/index.html?sc=two` });
  await Bun.sleep(Number(process.env.SETTLE || 3000));
};
const key = async (k: string, code: string, vk: number) => {
  await cdp("Input.dispatchKeyEvent", { type: "rawKeyDown", key: k, code, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk });
  if (k === "Enter") await cdp("Input.dispatchKeyEvent", { type: "char", key: k, code, text: "\r", windowsVirtualKeyCode: vk });
  await cdp("Input.dispatchKeyEvent", { type: "keyUp", key: k, code, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk });
  await Bun.sleep(120);
};
const NCALL = (cmd: string) => `window.__shimCalls.filter(c => c.cmd === ${JSON.stringify(cmd)}).length`;
// 상단바·사이드바 자리 기록 — 보이는 단추(글자 = 안쪽 뱃지 뺀 글자) · 사이드바의 상담소·아고라 수
const PLACE = `(() => {
  const vis = (b) => b.offsetParent !== null && b.getBoundingClientRect().width > 0;
  const name = (b) => [...b.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join("").trim();
  const top = [...document.querySelectorAll("#topbar > button[id]")].filter(vis);
  const side = [...document.querySelectorAll("#wsbar button")].filter(vis).filter(b => /상담소|아고라/.test(b.textContent));
  return { top: top.map(name), topIds: top.map(b => b.id), side: side.map(name), sideRow: !!document.getElementById("ws-counsel-row") };
})()`;
// 폭별 측정 — 이웃 겹침 · 글자 잘림 · 줄바꿈(높이가 정렬 단추와 다름) · 세 단추 화면 안 · 상단바 높이·넘침
const MEASURE = `(() => {
  const bar = document.getElementById("topbar");
  const vis = (b) => b.offsetParent !== null && b.getBoundingClientRect().width > 0;
  const btns = [...bar.querySelectorAll(":scope > button[id]")].filter(vis);
  const hEq = Math.round(document.getElementById("btn-equalize").getBoundingClientRect().height);
  const overlaps = []; const clipped = []; const wrapped = [];
  btns.forEach((b, i) => {
    const r = b.getBoundingClientRect();
    if (i + 1 < btns.length && r.right > btns[i + 1].getBoundingClientRect().left + 0.5) overlaps.push(b.id + ">" + btns[i + 1].id);
    if (b.scrollWidth > b.clientWidth + 1 || b.scrollHeight > b.clientHeight + 1) clipped.push(b.id);
    // 줄바꿈 = 두 줄 높이(정렬 단추의 1.5배 초과). ±2px 차이는 줄바꿈이 아니다 — 1.1.9 에서도 Control Center(라틴 글꼴) 27 · 한글 단추 29(실측 2026-10-21).
    if (!b.classList.contains("icon-btn") && r.height > hEq * 1.5) wrapped.push(b.id + ":" + Math.round(r.height));
  });
  const three = ["btn-feedback", "btn-counsel", "btn-agora"].map(id => document.getElementById(id).getBoundingClientRect());
  const badge = document.getElementById("counsel-badge"); const cb = document.getElementById("btn-counsel").getBoundingClientRect(); const bb = badge.getBoundingClientRect();
  const brandGap = Math.round(document.getElementById("app-ver").getBoundingClientRect().left - document.getElementById("brand").getBoundingClientRect().right);
  return { barH: Math.round(bar.getBoundingClientRect().height), overflow: bar.scrollWidth - bar.clientWidth, brandGap,
    overlaps, clipped, wrapped, threeInView: three.every(r => r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= bar.getBoundingClientRect().bottom),
    threeReach: three.every(r => r.right <= bar.scrollWidth + bar.getBoundingClientRect().left),
    badge: badge.hidden ? null : badge.textContent, badgeInside: badge.hidden || (bb.left >= cb.left && bb.right <= cb.right && bb.top >= cb.top && bb.bottom <= cb.bottom) };
})()`;

const fails: string[] = [];
const check = (name: string, ok: boolean, detail: string) => { console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${detail}`); if (!ok) fails.push(name); };

if (BEFORE) {
  // 전 기록(1.1.9) — 판정 없이 자리만 적고 캡처
  for (const w of [1280, 800]) {
    await size(w); await load();
    console.log(`BEFORE ${w}: ${JSON.stringify(await ev(PLACE))}`);
    await shot(`before-119-w${w}.png`);
  }
  await size(1280); await load(`sessionStorage.setItem("__menuUnread", "12")`);
  console.log(`BEFORE badge: ${JSON.stringify(await ev(PLACE))}`);
  await shot("before-119-w1280-badge.png");
  cleanup(); process.exit(0);
}

if (ONLY.includes("m1")) {
  await size(1280); await load();
  const a = await ev(PLACE);
  await shot("after-w1280.png");
  check("m1 상단 맨 앞 넷 = 피드백 · 상담소 · 아고라 · 정렬 · 사이드바 상담소·아고라 0 · 옛 줄 0",
    JSON.stringify(a.top.slice(0, 4)) === JSON.stringify(["피드백", "상담소", "아고라", "정렬"]) && a.side.length === 0 && !a.sideRow, JSON.stringify(a));
}

if (ONLY.includes("m2")) {
  await size(1280); await load();
  await ev(`document.getElementById("btn-counsel").click()`); await Bun.sleep(400);
  const c = await ev(`({ modal: !!document.querySelector(".modal.counsel-modal"), h: document.querySelector(".counsel-modal .counsel-h")?.textContent ?? null, list: ${NCALL("counsel_room_list")} })`);
  await shot("after-counsel-modal.png");
  check("m2a 상담소 누름 → 상담소 창(제목 「상담소」) · counsel_room_list 1", c.modal && c.h === "상담소" && c.list === 1, JSON.stringify(c));
  await ev(`document.querySelector(".counsel-modal .counsel-close")?.click()`); await Bun.sleep(200);
  await ev(`document.getElementById("btn-agora").click()`); await Bun.sleep(300);
  const g = await ev(`({ agora: ${NCALL("open_agora_window")}, openUrl: window.__shimCalls.filter(c => c.cmd === "open_url").length, modal: document.querySelectorAll(".modal-overlay").length })`);
  check("m2b 아고라 누름 → open_agora_window 1 · open_url 0 · 실패 창 0", g.agora === 1 && g.openUrl === 0 && g.modal === 0, JSON.stringify(g));
}

if (ONLY.includes("m3")) {
  await size(1280); await load();
  await ev(`document.getElementById("btn-feedback").focus()`);
  const f0 = await ev(`document.activeElement?.id`);
  await key("Tab", "Tab", 9); const f1 = await ev(`document.activeElement?.id`);
  await key("Tab", "Tab", 9); const f2 = await ev(`document.activeElement?.id`);
  await key("Tab", "Tab", 9); const f3 = await ev(`document.activeElement?.id`);
  await shot("after-keyboard-focus.png");
  check("m3a 키보드 Tab 순서 = 피드백 → 상담소 → 아고라 → 정렬", f0 === "btn-feedback" && f1 === "btn-counsel" && f2 === "btn-agora" && f3 === "btn-equalize", JSON.stringify([f0, f1, f2, f3]));
  await ev(`document.getElementById("btn-counsel").focus()`);
  await key("Enter", "Enter", 13);
  const e = await ev(`({ modal: !!document.querySelector(".modal.counsel-modal"), list: ${NCALL("counsel_room_list")} })`);
  check("m3b 상담소에 초점 두고 Enter → 상담소 창", e.modal && e.list === 1, JSON.stringify(e));
  const t = await ev(`({ c: document.getElementById("btn-counsel").title, a: document.getElementById("btn-agora").title })`);
  check("m3c 툴팁 = 정본 문구(상담소 · 아고라)", t.c === "상담소 — cysr 사용자들이 묻고 받은 답을 한곳에서 봅니다(보기 전용)" && t.a === "아고라 — AI 동료들이 토론하는 광장을 봅니다(보기 전용) · 참여는 마스터에게 말로 부탁하세요", JSON.stringify(t));
}

if (ONLY.includes("m4")) {
  const res: any = {};
  for (const w of [1280, 1024, 800, 640, 390]) {
    await size(w); await load(`sessionStorage.setItem("__menuUnread", "12")`);
    const m = await ev(MEASURE);
    res[w] = m;
    await shot(`after-w${w}-badge.png`);
  }
  await size(1280);
  console.log(`     m4 상단바 넘침(px): ${Object.entries(res).map(([w, m]: any) => `${w}=${m.overflow}`).join(" · ")}`);
  // 800 이상 = 상단바 넘침 0(1.1.9 와 같음 — 맨 오른쪽 「화면 설정」 까지 스크롤 없이 보인다) · 그 아래 = 가로 스크롤로 끝까지 닿음(1.1.9 도 640 에서 넘쳤다)
  // brandGap = 「cysr」 과 판번 사이 — 1.1.9 와 같은 4px(gap 8 − margin 4). 0 이면 「cysrv1.1.9」 로 붙는다.
  const okW = (w: string, m: any) => m.barH === 38 && m.brandGap >= 3 && !m.overlaps.length && !m.clipped.length && !m.wrapped.length && m.badge === "12" && m.badgeInside && m.threeReach && (Number(w) < 800 || (m.threeInView && m.overflow === 0));
  check("m4 폭 1280·1024·800·640·390(뱃지 12) — 높이 38 · 겹침 0 · 잘림 0 · 줄바꿈 0 · 뱃지는 상담소 단추 안 · 800 이상 세 단추 화면 안 · 상단바 넘침 0 · 「cysr」·판번 사이 띄움 유지", Object.entries(res).every(([w, m]) => okW(w, m)), JSON.stringify(res));
}

if (ONLY.includes("m5")) {
  // 1.1.9 상단바 11개 — 순서 저장(+ New 켬 · 파일 끔 · 정렬을 맨 뒤로) · 상담소·아고라 없음
  const OLD = ["btn-feedback", "btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-files", "btn-cc", "btn-restart-daemon", "btn-factory-reset", "btn-theme", "btn-equalize"];
  const saved = JSON.stringify({ version: 1, items: OLD.map((id) => ({ id, on: id === "btn-new" || !["btn-split-h", "btn-split-v", "btn-close", "btn-factory-reset", "btn-files"].includes(id) })) });
  await size(1280); await load(`localStorage.setItem("cys-topbar-layout", ${JSON.stringify(saved)})`);
  const a = await ev(PLACE);
  await shot("after-m5-saved-119-layout.png");
  check("m5 1.1.9 순서 저장 사용자 → 피드백 · 상담소 · 아고라 · + New … 정렬(맨 뒤 그대로) · 파일 꺼진 채",
    JSON.stringify(a.topIds) === JSON.stringify(["btn-feedback", "btn-counsel", "btn-agora", "btn-new", "btn-cc", "btn-restart-daemon", "btn-theme", "btn-equalize"]), JSON.stringify(a));
}

if (ONLY.includes("m6")) {
  await size(1280); await load();
  await ev(`document.getElementById("btn-theme").click()`); await Bun.sleep(200);
  const rows = await ev(`[...document.querySelectorAll("#theme-pop .tb-row")].map(r => ({ id: r.dataset.tbId, name: r.querySelector(".tb-name").textContent, on: r.querySelector(".tb-toggle").getAttribute("aria-checked") === "true", togDisabled: r.querySelector(".tb-toggle").disabled }))`);
  await shot("after-screen-settings-list.png");
  const pick = (rows || []).slice(0, 3);
  check("m6 화면 설정 → 상단 단추 목록 맨 앞 셋 = 피드백 · 상담소 · 아고라(켬 · 끌 수 있음)",
    JSON.stringify(pick.map((r: any) => r.name)) === JSON.stringify(["피드백", "상담소", "아고라"]) && pick.every((r: any) => r.on && !r.togDisabled), JSON.stringify(pick));
}

if (logs.length) console.log("page exceptions:\n  " + logs.slice(0, 5).join("\n  "));
console.log(fails.length ? `FAIL (${fails.length}): ${fails.join(" · ")}` : "ALL PASS");
cleanup();
process.exit(fails.length ? 1 : 0);
