// 화면 설정(종전 「테마」) 실렌더 시험 — ui/dist 실번들 + Tauri 흉내(../v116-ui-evidence/shim.js) · chrome-headless-shell · 종료 시 크롬 정리.
// TICKET=cysr-1110-screen-settings · 박사님 2026-10-12(글자 2배 · 상단 단추 켬끔·순서 · 기본 숨김 5).
// usage: DIST=<ui/dist> CHS=<chrome-headless-shell> [OUT=<캡처·수치 폴더>] [ONLY=s1,s2] bun screen-settings-headless.ts → exit 0 PASS / 1 FAIL
// 판정 칸:
//   s1  기본 화면(저장 0 · 1440×900): 상단에 보이는 단추 = 6개(피드백·정렬·파일·Control Center·↻ 재시작·화면 설정) · 숨김 5개 폭 0
//   s2  팝오버 글자 px — 배율 1.25(기본) 에서 보이는 글자 전부 ≥ 25 · 배율 1.0 에서 ≥ 20 · 「메뉴 크기」 를 팝오버 안에서 바꾸면 따라 커짐
//   s3  팝오버가 화면 밖으로 안 나감 — 1440×900 · 1280×800 · 1280×800 배율 250% · 800×600(넘치는 몫 = 팝오버 안 스크롤)
//   s4  토글: 끔 5개를 하나씩 켬 → 그 즉시 상단에 보임 · 저장(version 1) · 새로 고침 뒤 유지 · 다시 끔 → 숨김
//   s5  고정 2(화면 설정·Control Center): 토글 비활성 · 눌러도 그대로 · 안내 줄 있음
//   s6  ▲▼: 맨 위 ▲·맨 아래 ▼ 비활성 · ▼ 한 번 = 상단에서 한 칸 오른쪽 · 저장
//   s7  끌어 놓기(실제 마우스 입력): 손잡이를 잡아 다른 줄 아래에 놓음 → 그 순서 · 끄는 동안 삽입선 보임 · 저장
//   s8  숨긴 채 단축키: + New·창 닫기 숨김 상태에서 ⌘T = 창 +1 · ⌘W = 닫기 확인 창
//   s9  기본값 복원: 「이 구획만」 = 상단 단추만 · 「모두」 = 글자·배경 + 상단 단추 · 저장 지움
//   s10 손상·구판 저장 = 기본값 · 저장에 없는 단추(나중에 생긴 단추) = 켠 채 맨 끝
//   s11 구획 접기: 제목 줄 누르면 몸통 숨김 · 팝오버 높이 줄어듦 · 다시 누르면 펼침
//   s12 상단바 한 줄 유지(1280폭 기본) — 높이 = --topbar-h · 가로 넘침 0
//   (codex 1R 채택 4건 · TICKET=cysr-1110-screen-settings-r2)
//   s13 좁은 창 + 큰 배율(500×600 · 250%): 팝오버 화면 밖 0 — 그 크기에서 바로 열기 · 넓은 창에서 연 뒤 줄이기 · 토글·맨 아래 단추는 팝오버 안 스크롤로 닿음
//   s14 끌기 취소: 끄는 도중 Esc(팝오버 닫힘) → 놓아도 순서·저장 불변 · 삽입선·전역 표시 0 / 창이 초점을 잃음 → 놓아도 불변 · 팝오버 열린 채 · 그 뒤 누름은 정상
//   s15 저장 예외: 저장이 던져도(QuotaExceeded 흉내) 상단 반영 + 토글 글자 동기 + 「저장되지 않았습니다」 1줄 · 저장이 되면 그 줄 사라짐 · 읽기가 던져도 앱은 기본값으로 선다
// 원형 = docs/v116-ui-evidence/v116-headless.ts 의 CDP 드라이버.
import { spawn } from "bun";
import { mkdtempSync, readFileSync, writeFileSync, rmSync, existsSync, mkdirSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

const H = import.meta.dir;
const DIST = process.env.DIST!;
const CH = process.env.CHS!;
const OUT = process.env.OUT || "";
const ONLY = (process.env.ONLY || "s1,s2,s3,s4,s5,s6,s7,s8,s9,s10,s11,s12,s13,s14,s15").split(",");
const shim = readFileSync(join(H, "../v116-ui-evidence/shim.js"), "utf8");
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
const prof = mkdtempSync(join(tmpdir(), "sschs-"));
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
const size = (w: number, h: number) => cdp("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false });
const SETTLE = Number(process.env.SETTLE || 2500);
// preLS = 앱 적재 **전** 같은 출처 빈 문서에서 실행(localStorage 준비). keep = 저장을 비우지 않고 다시 적재(새로 고침 흉내).
const load = async (preLS = "", keep = false, sc = "two") => {
  await cdp("Page.navigate", { url: `http://127.0.0.1:${server.port}/blank-origin` });
  await Bun.sleep(150);
  await ev(`sessionStorage.clear(); ${keep ? "" : `localStorage.clear(); localStorage.setItem("cys-layout-v2", "{}");`} ${preLS}`);
  await cdp("Page.navigate", { url: `http://127.0.0.1:${server.port}/index.html?sc=${sc}` });
  await Bun.sleep(SETTLE);
};
const KEY = "cys-topbar-layout";
// 페이지 안 도우미
const TB = `(() => { const vis = (b) => b.offsetParent !== null && b.getBoundingClientRect().width > 0; const all = [...document.querySelectorAll("#topbar > button[id]")]; const name = (b) => [...b.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join("").trim(); return { all: all.map(b => b.id), shown: all.filter(vis).map(name), shownIds: all.filter(vis).map(b => b.id), hiddenIds: all.filter(b => !vis(b)).map(b => b.id), hiddenW: all.filter(b => !vis(b)).map(b => b.getBoundingClientRect().width) }; })()`;
const OPEN = `(document.getElementById("theme-pop") || document.getElementById("btn-theme").click(), !!document.getElementById("theme-pop"))`;
const ROWS = `[...document.querySelectorAll("#theme-pop .tb-row")].map(r => ({ id: r.dataset.tbId, name: r.querySelector(".tb-name").textContent, on: r.querySelector(".tb-toggle").getAttribute("aria-checked") === "true", togDisabled: r.querySelector(".tb-toggle").disabled, upDisabled: r.querySelector(".tb-up").disabled, downDisabled: r.querySelector(".tb-down").disabled }))`;
const ROWBTN = (rowId: string, cls: string) => `[...document.querySelectorAll("#theme-pop .tb-row")].find(r => r.dataset.tbId === ${JSON.stringify(rowId)}).querySelector(${JSON.stringify("." + cls)})`;
// 팝오버에서 **보이는 글자**(글자 노드를 가진 요소 + 입력 부품)의 계산된 글자 크기
const FONTS = `(() => { const pop = document.getElementById("theme-pop"); const els = [...pop.querySelectorAll("*")].filter(e => e.getClientRects().length > 0 || e.tagName === "OPTION"); const hit = els.filter(e => /^(SELECT|INPUT|BUTTON|OPTION)$/.test(e.tagName) || [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())); const rows = hit.map(e => ({ k: e.tagName.toLowerCase() + (e.className ? "." + String(e.className).split(" ")[0] : "") + (e.type && e.tagName === "INPUT" ? "[" + e.type + "]" : ""), px: parseFloat(getComputedStyle(e).fontSize) })); const by = {}; for (const r of rows) by[r.k] = Math.min(by[r.k] ?? Infinity, r.px); const px = rows.map(r => r.px); return { n: rows.length, min: Math.min(...px), max: Math.max(...px), popPx: parseFloat(getComputedStyle(pop).fontSize), scale: getComputedStyle(document.documentElement).getPropertyValue("--ui-chrome-scale").trim(), byKind: by }; })()`;
const BOX = `(() => { const p = document.getElementById("theme-pop"); const r = p.getBoundingClientRect(); const a = document.getElementById("btn-theme").getBoundingClientRect(); return { vw: innerWidth, vh: innerHeight, left: Math.round(r.left), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom), w: Math.round(r.width), h: Math.round(r.height), scrollH: p.scrollHeight, clientH: p.clientHeight, scrollW: p.scrollWidth, clientW: p.clientWidth, anchorBottom: Math.round(a.bottom) }; })()`;
const inView = (b: any) => b.left >= 0 && b.top >= 0 && b.right <= b.vw && b.bottom <= b.vh;
const SAVED = `JSON.parse(localStorage.getItem(${JSON.stringify(KEY)}) || "null")`;
const kd = (k: string) => `window.dispatchEvent(new KeyboardEvent("keydown", { key: ${JSON.stringify(k)}, metaKey: true, bubbles: true, cancelable: true }))`;

const fails: string[] = [];
const numbers: Record<string, any> = {};
const check = (name: string, ok: boolean, detail: any) => { console.log(`${ok ? "PASS" : "FAIL"} ${name} — ${typeof detail === "string" ? detail : JSON.stringify(detail)}`); if (!ok) fails.push(name); numbers[name.split(" ")[0]] = { ok, detail }; };

const DEFAULT_SHOWN = ["피드백", "정렬", "파일", "Control Center", "↻ 재시작", "화면 설정"];
const DEFAULT_HIDDEN = ["btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-factory-reset"];
const HTML_ORDER = ["btn-feedback", "btn-equalize", "btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-files", "btn-cc", "btn-restart-daemon", "btn-factory-reset", "btn-theme"];

if (ONLY.includes("s1")) {
  await size(1440, 900); await load();
  const a = await ev(TB);
  await shot("s1-default-1440x900.png");
  check("s1 기본 화면: 상단에 보이는 단추 = 6개 · 숨김 5개(폭 0) · 저장 0", JSON.stringify(a.shown) === JSON.stringify(DEFAULT_SHOWN) && JSON.stringify(a.hiddenIds) === JSON.stringify(DEFAULT_HIDDEN) && a.hiddenW.every((w: number) => w === 0) && (await ev(SAVED)) === null, { shown: a.shown, hiddenIds: a.hiddenIds, hiddenW: a.hiddenW });
}

if (ONLY.includes("s2")) {
  await size(1440, 900); await load();
  await ev(OPEN); await Bun.sleep(150);
  const f125 = await ev(FONTS);
  await shot("s2-popover-scale125-1440x900.png");
  check("s2a 팝오버 글자 px(배율 1.25 · 기본) — 보이는 글자 전부 ≥ 25", f125.min >= 25 && f125.scale === "1.25", f125);
  await size(1440, 900); await load(`localStorage.setItem("cys-menu-scale", "100");`);
  await ev(OPEN); await Bun.sleep(150);
  const f100 = await ev(FONTS);
  await shot("s2-popover-scale100-1440x900.png");
  check("s2b 팝오버 글자 px(배율 1.0) — 보이는 글자 전부 ≥ 20", f100.min >= 20 && f100.scale === "1", f100);
  // 팝오버 안 「메뉴 크기(%)」 를 150 으로 → 상단 단추와 팝오버가 함께 커진다(한 축)
  const before = await ev(`({ pop: parseFloat(getComputedStyle(document.getElementById("theme-pop")).fontSize), top: parseFloat(getComputedStyle(document.getElementById("btn-feedback")).fontSize) })`);
  await ev(`(() => { const i = [...document.querySelectorAll("#theme-pop .theme-pop-row")].find(r => r.textContent.startsWith("메뉴 크기")).querySelector("input"); i.value = "150"; i.dispatchEvent(new Event("input", { bubbles: true })); })()`);
  await Bun.sleep(150);
  const after = await ev(`({ pop: parseFloat(getComputedStyle(document.getElementById("theme-pop")).fontSize), top: parseFloat(getComputedStyle(document.getElementById("btn-feedback")).fontSize), min: ${FONTS}.min })`);
  const box = await ev(BOX);
  check("s2c 「메뉴 크기」 100 → 150: 팝오버 20 → 30px · 상단 단추 12 → 18px(같은 손잡이) · 팝오버 화면 안", before.pop === 20 && after.pop === 30 && before.top === 12 && after.top === 18 && after.min >= 30 && inView(box), { before, after, box });
}

if (ONLY.includes("s3")) {
  const rows: any[] = []; let ok = true;
  for (const [w, h, pct] of [[1440, 900, null], [1280, 800, null], [1280, 800, 250], [800, 600, null]] as const) {
    await size(w, h); await load(pct ? `localStorage.setItem("cys-menu-scale", "${pct}");` : "");
    await ev(OPEN); await Bun.sleep(200);
    const b = await ev(BOX);
    // 맨 아래 줄까지 스크롤로 닿는가(넘치는 몫이 팝오버 안에서 흡수되는가)
    const reach = await ev(`(() => { const p = document.getElementById("theme-pop"); p.scrollTop = p.scrollHeight; const last = [...p.querySelectorAll(".theme-pop-reset")].at(-1).getBoundingClientRect(); const pr = p.getBoundingClientRect(); const r = { lastBottom: Math.round(last.bottom), popBottom: Math.round(pr.bottom), ok: last.bottom <= pr.bottom + 1 && last.top >= pr.top - 1 }; p.scrollTop = 0; return r; })()`);
    const good = inView(b) && reach.ok && b.top >= b.anchorBottom;
    if (!good) ok = false;
    rows.push({ win: `${w}x${h}`, scalePct: pct ?? 125, ...b, lastRowReachable: reach.ok, inView: inView(b) });
    await shot(`s3-popover-${w}x${h}${pct ? `-scale${pct}` : ""}.png`);
  }
  check("s3 팝오버가 화면 밖으로 안 나감(1440×900 · 1280×800 · 1280×800 배율 250% · 800×600) · 맨 아래 단추까지 스크롤로 닿음", ok, rows);
}

if (ONLY.includes("s4")) {
  await size(1440, 900); await load();
  await ev(OPEN); await Bun.sleep(150);
  const steps: any[] = []; let ok = true;
  for (const hid of DEFAULT_HIDDEN) {
    await ev(`${ROWBTN(hid, "tb-toggle")}.click()`); await Bun.sleep(60);
    const t = await ev(TB); const saved = await ev(SAVED);
    const row = (await ev(ROWS)).find((r: any) => r.id === hid);
    const good = t.shownIds.includes(hid) && row.on && saved?.version === 1 && saved.items.find((x: any) => x.id === hid)?.on === true;
    if (!good) ok = false;
    steps.push({ id: hid, shownNow: t.shownIds.includes(hid), rowOn: row.on, savedOn: saved?.items?.find((x: any) => x.id === hid)?.on });
  }
  const allOn = await ev(TB);
  await shot("s4-all-on-1440x900.png");
  check("s4a 끔 5개를 하나씩 켬 → 그 즉시 상단에 보임 · 저장 version 1", ok && allOn.shownIds.length === 11 && JSON.stringify(allOn.shownIds) === JSON.stringify(HTML_ORDER), { steps, shown: allOn.shown });
  await load("", true); // 새로 고침(저장 유지)
  const re = await ev(TB);
  check("s4b 새로 고침 뒤에도 11개 그대로(저장 복원)", re.shownIds.length === 11 && JSON.stringify(re.shownIds) === JSON.stringify(HTML_ORDER), { shown: re.shown });
  await ev(OPEN); await Bun.sleep(150);
  await ev(`${ROWBTN("btn-feedback", "tb-toggle")}.click()`); await Bun.sleep(60);
  const off = await ev(TB);
  check("s4c 켜진 단추(피드백)를 끔 → 그 즉시 숨김 · 요소는 남음(DOM 11개)", !off.shownIds.includes("btn-feedback") && off.all.length === 11 && off.hiddenIds.includes("btn-feedback"), { shown: off.shown, domCount: off.all.length });
}

if (ONLY.includes("s5")) {
  await size(1440, 900); await load();
  await ev(OPEN); await Bun.sleep(150);
  const before = await ev(ROWS);
  await ev(`${ROWBTN("btn-theme", "tb-toggle")}.click(); ${ROWBTN("btn-cc", "tb-toggle")}.click()`); await Bun.sleep(60);
  const t = await ev(TB); const after = await ev(ROWS);
  const note = await ev(`[...document.querySelectorAll("#theme-pop .sp-note")].map(n => n.textContent).find(x => x.includes("끌 수 없습니다")) || ""`);
  const pin = (rs: any[]) => rs.filter((r) => r.id === "btn-theme" || r.id === "btn-cc");
  check("s5 고정 2(화면 설정·Control Center): 토글 비활성 · 눌러도 켬 그대로 · 안내 줄 · 저장 0", pin(before).every((r) => r.togDisabled && r.on) && pin(after).every((r) => r.on) && t.shownIds.includes("btn-theme") && t.shownIds.includes("btn-cc") && note.length > 0 && (await ev(SAVED)) === null && before.filter((r: any) => r.togDisabled).length === 2, { pinned: pin(after), note });
}

if (ONLY.includes("s6")) {
  await size(1440, 900); await load();
  await ev(OPEN); await Bun.sleep(150);
  const r0 = await ev(ROWS);
  const edge = r0[0].upDisabled && !r0[0].downDisabled && r0.at(-1).downDisabled && !r0.at(-1).upDisabled && r0.slice(1, -1).every((r: any) => !r.upDisabled && !r.downDisabled);
  await ev(`${ROWBTN("btn-feedback", "tb-down")}.click()`); await Bun.sleep(60);
  const t1 = await ev(TB); const saved1 = await ev(SAVED);
  const focus1 = await ev(`(() => { const a = document.activeElement; return a?.closest?.(".tb-row")?.dataset.tbId + ":" + a?.className; })()`);
  await ev(`${ROWBTN("btn-theme", "tb-up")}.click()`); await Bun.sleep(60);
  const t2 = await ev(TB);
  const want1 = ["btn-equalize", "btn-feedback", ...HTML_ORDER.slice(2)];
  const want2 = [...want1.slice(0, 9), "btn-theme", "btn-factory-reset"];
  const box = await ev(BOX);
  await shot("s6-after-move-1440x900.png");
  check("s6 ▲▼: 맨 위 ▲·맨 아래 ▼ 비활성 · 피드백 ▼ = 정렬 다음 · 화면 설정 ▲ = 완전 초기화 앞 · 저장 · 초점 유지 · 팝오버가 옮겨 간 단추 아래", edge && JSON.stringify(t1.all) === JSON.stringify(want1) && JSON.stringify(saved1.items.map((x: any) => x.id)) === JSON.stringify(want1) && JSON.stringify(t2.all) === JSON.stringify(want2) && focus1 === "btn-feedback:tb-move tb-down" && box.top >= box.anchorBottom && inView(box), { edge, order1: t1.all, order2: t2.all, shown2: t2.shown, focus1 });
}

if (ONLY.includes("s7")) {
  await size(1440, 900); await load();
  await ev(OPEN); await Bun.sleep(150);
  const pt = async (rowId: string, sel: string, fy: number) => await ev(`(() => { const r = [...document.querySelectorAll("#theme-pop .tb-row")].find(r => r.dataset.tbId === ${JSON.stringify(rowId)}); const g = (${JSON.stringify(sel)} ? r.querySelector(${JSON.stringify(sel)}) : r).getBoundingClientRect(); return { x: g.left + g.width / 2, y: g.top + g.height * ${fy} }; })()`);
  // 목록은 팝오버 안에서 스크롤된다(1440×900 에서 전체 높이 > 창) — 잡을 줄·놓을 줄이 함께 보이게 구획 머리를 맨 위로 올린다.
  await ev(`document.querySelector('#theme-pop .sp-sec[data-sec="topbar"]').scrollIntoView({ block: "start" })`); await Bun.sleep(80);
  const from = await pt("btn-restart-daemon", ".tb-grip", 0.5);
  const to = await pt("btn-feedback", "", 0.8); // 피드백 줄의 아래쪽 절반 = 그 뒤
  const mouse = (type: string, x: number, y: number, buttons: number) => cdp("Input.dispatchMouseEvent", { type, x, y, button: "left", buttons, clickCount: 1 });
  await mouse("mousePressed", from.x, from.y, 1);
  await mouse("mouseMoved", from.x, from.y - 10, 1);
  await mouse("mouseMoved", to.x, to.y, 1);
  await Bun.sleep(80);
  const mid = await ev(`(() => { const l = document.querySelector(".ws-drop-indicator"); if (!l) return { line: false }; const r = l.getBoundingClientRect(); const z = getComputedStyle(l).zIndex; const fb = [...document.querySelectorAll("#theme-pop .tb-row")].find(r => r.dataset.tbId === "btn-feedback").getBoundingClientRect(); return { line: !l.hidden && r.width > 0, lineY: Math.round(r.top), rowBottom: Math.round(fb.bottom), z, popZ: getComputedStyle(document.getElementById("theme-pop")).zIndex, dragging: !!document.querySelector("#theme-pop .tb-row.tb-dragging"), pop: !!document.getElementById("theme-pop") }; })()`);
  await shot("s7-dragging-1440x900.png");
  await mouse("mouseReleased", to.x, to.y, 0);
  await Bun.sleep(120);
  const t = await ev(TB); const saved = await ev(SAVED);
  const want = ["btn-feedback", "btn-restart-daemon", ...HTML_ORDER.slice(1).filter((x) => x !== "btn-restart-daemon")];
  const left = await ev(`({ line: !!document.querySelector(".ws-drop-indicator"), body: document.body.classList.contains("ws-reordering"), pop: !!document.getElementById("theme-pop") })`);
  await shot("s7-after-drop-1440x900.png");
  check("s7 끌어 놓기(실제 마우스): ↻ 재시작을 피드백 아래로 → 그 순서(상단 + 저장) · 끄는 동안 삽입선(팝오버 위 층) · 놓은 뒤 삽입선 0 · 팝오버 열린 채", mid.line && mid.dragging && Number(mid.z) > Number(mid.popZ) && Math.abs(mid.lineY - mid.rowBottom) <= 2 && JSON.stringify(t.all) === JSON.stringify(want) && JSON.stringify(saved.items.map((x: any) => x.id)) === JSON.stringify(want) && !left.line && !left.body && left.pop, { mid, order: t.all, shown: t.shown, left });
}

if (ONLY.includes("s8")) {
  await size(1440, 900); await load();
  const t = await ev(TB);
  const n0 = await ev(`document.querySelectorAll("#root .pane").length`);
  await ev(`document.querySelector("#root .pane").dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
  await ev(kd("t")); await Bun.sleep(700);
  const n1 = await ev(`document.querySelectorAll("#root .pane").length`);
  await ev(`[...document.querySelectorAll("#root .pane")].find(p => (p.querySelector(".pane-title-text")?.textContent || "").includes("master")).dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
  await ev(kd("w")); await Bun.sleep(300);
  const modal = await ev(`document.querySelector(".modal-overlay")?.innerText ?? ""`);
  check("s8 숨긴 채 단축키: + New·창 닫기가 숨김인데 ⌘T = 창 +1 · ⌘W = 닫기 확인 창", t.hiddenIds.includes("btn-new") && t.hiddenIds.includes("btn-close") && n1 === n0 + 1 && modal.includes("이 창을 닫을까요?"), { hidden: t.hiddenIds, panes: `${n0}→${n1}`, modal: modal.replace(/\n+/g, " / ").slice(0, 60) });
}

if (ONLY.includes("s9")) {
  await size(1440, 900); await load(`localStorage.setItem("cys-menu-scale", "150"); localStorage.setItem("cys-title-size", "30");`);
  await ev(OPEN); await Bun.sleep(150);
  await ev(`${ROWBTN("btn-new", "tb-toggle")}.click(); ${ROWBTN("btn-feedback", "tb-down")}.click()`); await Bun.sleep(60);
  const dirty = await ev(TB);
  const RESET = (sec: string) => `document.querySelector('#theme-pop .sp-sec[data-sec="${sec}"] .theme-pop-reset').click()`;
  await ev(RESET("topbar")); await Bun.sleep(80);
  const a = await ev(TB); const aSaved = await ev(SAVED); const aScale = await ev(`localStorage.getItem("cys-menu-scale")`);
  check("s9a 「이 구획만 기본값으로」(상단 단추): 보이는 6개·순서 처음대로 · 저장 지움 · 글자·배경(메뉴 크기 150)은 그대로", dirty.shownIds.includes("btn-new") && JSON.stringify(a.shown) === JSON.stringify(DEFAULT_SHOWN) && JSON.stringify(a.all) === JSON.stringify(HTML_ORDER) && aSaved === null && aScale === "150", { dirtyShown: dirty.shown, shown: a.shown, saved: aSaved, menuScale: aScale });
  await ev(`${ROWBTN("btn-close", "tb-toggle")}.click()`); await Bun.sleep(60);
  await ev(RESET("look")); await Bun.sleep(80);
  const b = await ev(`({ scale: localStorage.getItem("cys-menu-scale"), title: localStorage.getItem("cys-title-size"), closeShown: ${TB}.shownIds.includes("btn-close") })`);
  check("s9b 「이 구획만 기본값으로」(글자·배경): 메뉴 크기·제목 크기 저장 지움 · 상단 단추(창 닫기 켬)는 그대로", b.scale === null && b.title === null && b.closeShown, b);
  await ev(`localStorage.setItem("cys-title-size", "30")`);
  await ev(RESET("reset")); await Bun.sleep(80);
  const c = await ev(`({ title: localStorage.getItem("cys-title-size"), saved: ${SAVED}, shown: ${TB}.shown, popPx: parseFloat(getComputedStyle(document.getElementById("theme-pop")).fontSize) })`);
  check("s9c 「모두 기본값으로 되돌리기」: 글자·배경 + 상단 단추 둘 다 처음 상태 · 팝오버 25px", c.title === null && c.saved === null && JSON.stringify(c.shown) === JSON.stringify(DEFAULT_SHOWN) && c.popPx === 25, c);
}

if (ONLY.includes("s10")) {
  await size(1440, 900);
  const rows: any[] = []; let ok = true;
  for (const [label, raw] of [
    ["JSON 아님", "{{{not json"],
    ["구판(version 0)", JSON.stringify({ version: 0, items: HTML_ORDER.map((id) => ({ id, on: true })) })],
    ["다음 판(version 2)", JSON.stringify({ version: 2, items: HTML_ORDER.map((id) => ({ id, on: true })) })],
    ["배열만", JSON.stringify(HTML_ORDER.map((id) => ({ id, on: true })))],
    ["항목 모양 틀림", JSON.stringify({ version: 1, items: [{ id: "btn-new", on: "yes" }] })],
    ["아는 단추 0", JSON.stringify({ version: 1, items: [{ id: "btn-gone", on: true }] })],
  ] as const) {
    await load(`localStorage.setItem(${JSON.stringify(KEY)}, ${JSON.stringify(raw)});`);
    const t = await ev(TB);
    const good = JSON.stringify(t.shown) === JSON.stringify(DEFAULT_SHOWN) && JSON.stringify(t.all) === JSON.stringify(HTML_ORDER);
    if (!good) ok = false;
    rows.push({ label, shown: t.shown.length, default: good });
  }
  check("s10a 손상·구판 저장 6종 = 기본값(보이는 6개 · 처음 순서) · 앱 정상 기동", ok && !logs.length, rows);
  // 저장에 없는 단추(「파일」 을 저장에서 뺌 = 나중에 생긴 단추 흉내) → 켠 채 맨 끝 · 고정 단추 끔 저장 → 켬 · 없어진 단추 id = 무시
  const partial = { version: 1, items: [{ id: "btn-theme", on: false }, { id: "btn-gone", on: true }, ...HTML_ORDER.filter((x) => x !== "btn-files" && x !== "btn-theme").map((id) => ({ id, on: id === "btn-new" }))] };
  await load(`localStorage.setItem(${JSON.stringify(KEY)}, ${JSON.stringify(JSON.stringify(partial))});`);
  const t = await ev(TB);
  check("s10b 저장에 없는 단추(파일) = 켠 채 맨 끝 · 고정 단추(화면 설정) 끔 저장 = 켬으로 읽음 · 없어진 단추 id 무시", t.all[0] === "btn-theme" && t.all.at(-1) === "btn-files" && JSON.stringify(t.shownIds) === JSON.stringify(["btn-theme", "btn-new", "btn-cc", "btn-files"]) && t.all.length === 11, { order: t.all, shown: t.shown });
}

if (ONLY.includes("s11")) {
  await size(1440, 900); await load();
  await ev(OPEN); await Bun.sleep(150);
  const heads = await ev(`[...document.querySelectorAll("#theme-pop .sp-sec-head")].map(h => h.textContent)`);
  const h0 = (await ev(BOX)).scrollH;
  await ev(`document.querySelector('#theme-pop .sp-sec[data-sec="topbar"] .sp-sec-head').click()`); await Bun.sleep(80);
  const a = await ev(`({ hidden: getComputedStyle(document.querySelector('#theme-pop .sp-sec[data-sec="topbar"] .sp-sec-body')).display === "none", expanded: document.querySelector('#theme-pop .sp-sec[data-sec="topbar"] .sp-sec-head').getAttribute("aria-expanded"), scrollH: document.getElementById("theme-pop").scrollHeight })`);
  await shot("s11-topbar-section-folded-1440x900.png");
  // 닫았다 다시 열어도 접힌 채(앱이 켜져 있는 동안 기억)
  await ev(`window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))`); await Bun.sleep(60);
  const closed = await ev(`!document.getElementById("theme-pop")`);
  await ev(OPEN); await Bun.sleep(100);
  const again = await ev(`getComputedStyle(document.querySelector('#theme-pop .sp-sec[data-sec="topbar"] .sp-sec-body')).display === "none"`);
  await ev(`document.querySelector('#theme-pop .sp-sec[data-sec="topbar"] .sp-sec-head').click()`); await Bun.sleep(80);
  const b = await ev(`({ shown: getComputedStyle(document.querySelector('#theme-pop .sp-sec[data-sec="topbar"] .sp-sec-body')).display !== "none", scrollH: document.getElementById("theme-pop").scrollHeight })`);
  check("s11 구획 3개(글자·배경 / 상단 단추 / 기본값 복원) · 제목 줄 누르면 접힘(높이 줄어듦) · Esc 로 닫힘 · 다시 열어도 접힌 채 · 다시 누르면 펼침", heads.length === 3 && heads[0].includes("글자·배경") && heads[1].includes("상단 단추") && heads[2].includes("기본값 복원") && a.hidden && a.expanded === "false" && a.scrollH < h0 && closed && again && b.shown && b.scrollH === h0, { heads, full: h0, folded: a.scrollH, closed, again });
}

if (ONLY.includes("s12")) {
  const rows: any[] = []; let ok = true;
  for (const w of [1440, 1280]) {
    await size(w, 800); await load();
    const a = await ev(`(() => { const t = document.getElementById("topbar"); const want = parseFloat(getComputedStyle(t).minHeight); const last = document.getElementById("btn-theme").getBoundingClientRect(); return { h: t.getBoundingClientRect().height, want, scrollW: t.scrollWidth, clientW: t.clientWidth, lastRight: Math.round(last.right), text: document.getElementById("btn-theme").textContent, title: document.getElementById("btn-theme").title }; })()`);
    const good = a.h === a.want && a.scrollW <= a.clientW && a.lastRight <= w && a.text === "화면 설정";
    if (!good) ok = false;
    rows.push({ w, ...a });
  }
  check("s12 상단바 한 줄(1440·1280폭 기본) — 높이 = --topbar-h · 가로 넘침 0 · 맨 끝 단추 = 「화면 설정」 화면 안", ok, rows);
}

if (ONLY.includes("s13")) {
  // 맨 아래 단추(세로) · 첫 줄 토글(가로)이 팝오버 안 스크롤로 닿는가
  const REACH = `(() => { const p = document.getElementById("theme-pop"); const pr = () => p.getBoundingClientRect(); const inside = (el) => { const r = el.getBoundingClientRect(), q = pr(); return r.left >= q.left - 1 && r.right <= q.right + 1 && r.top >= q.top - 1 && r.bottom <= q.bottom + 1; }; const last = [...p.querySelectorAll(".theme-pop-reset")].at(-1); last.scrollIntoView({ block: "nearest", inline: "nearest" }); const a = inside(last); const tog = p.querySelector(".tb-row .tb-toggle"); tog.scrollIntoView({ block: "nearest", inline: "nearest" }); const b = inside(tog); p.scrollTop = 0; p.scrollLeft = 0; return { lastReset: a, firstToggle: b }; })()`;
  await size(500, 600); await load(`localStorage.setItem("cys-menu-scale", "250");`);
  await ev(OPEN); await Bun.sleep(200);
  const a = await ev(BOX); const ar = await ev(REACH);
  const minW = await ev(`getComputedStyle(document.getElementById("theme-pop")).minWidth`);
  await shot("s13-popover-500x600-scale250.png");
  // 넓은 창에서 연 뒤 줄인다(codex 재현 순서)
  await size(1440, 900); await load(`localStorage.setItem("cys-menu-scale", "250");`);
  await ev(OPEN); await Bun.sleep(200);
  const wide = await ev(BOX);
  await size(500, 600); await Bun.sleep(300);
  const b = await ev(BOX); const br = await ev(REACH);
  await shot("s13-popover-shrunk-to-500x600-scale250.png");
  check("s13 좁은 창 + 큰 배율(500×600 · 250%): 팝오버 화면 밖 0(바로 열기 · 넓게 연 뒤 줄이기) · 폭 ≤ 창 − 8 · 토글·맨 아래 단추 스크롤로 닿음", inView(a) && a.w <= 492 && ar.lastReset && ar.firstToggle && inView(wide) && inView(b) && b.w <= 492 && br.lastReset && br.firstToggle, { direct: { left: a.left, right: a.right, top: a.top, bottom: a.bottom, w: a.w, h: a.h, vw: a.vw, vh: a.vh, scrollW: a.scrollW, clientW: a.clientW, minWidth: minW, ...ar }, wide: { w: wide.w, right: wide.right, vw: wide.vw }, shrunk: { left: b.left, right: b.right, bottom: b.bottom, w: b.w, vw: b.vw, vh: b.vh, ...br } });
}

if (ONLY.includes("s14")) {
  const mouse = (type: string, x: number, y: number, buttons: number) => cdp("Input.dispatchMouseEvent", { type, x, y, button: "left", buttons, clickCount: 1 });
  const pt = async (rowId: string, sel: string, fy: number) => await ev(`(() => { const r = [...document.querySelectorAll("#theme-pop .tb-row")].find(r => r.dataset.tbId === ${JSON.stringify(rowId)}); const g = (${JSON.stringify(sel)} ? r.querySelector(${JSON.stringify(sel)}) : r).getBoundingClientRect(); return { x: g.left + g.width / 2, y: g.top + g.height * ${fy} }; })()`);
  const STATE = `({ line: !!document.querySelector(".ws-drop-indicator"), body: document.body.classList.contains("ws-reordering"), dragRow: !!document.querySelector(".tb-row.tb-dragging"), pop: !!document.getElementById("theme-pop"), order: ${TB}.all, saved: ${SAVED} })`;
  const startDrag = async () => {
    await ev(`document.querySelector('#theme-pop .sp-sec[data-sec="topbar"]').scrollIntoView({ block: "start" })`); await Bun.sleep(80);
    const from = await pt("btn-restart-daemon", ".tb-grip", 0.5);
    const to = await pt("btn-feedback", "", 0.8);
    await mouse("mousePressed", from.x, from.y, 1);
    await mouse("mouseMoved", from.x, from.y - 10, 1);
    await mouse("mouseMoved", to.x, to.y, 1);
    await Bun.sleep(80);
    return { to, mid: await ev(STATE) };
  };
  // ⓐ 끄는 도중 Esc → 팝오버 닫힘 → 놓음
  await size(1440, 900); await load();
  await ev(OPEN); await Bun.sleep(150);
  const a0 = await startDrag();
  await cdp("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await cdp("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await Bun.sleep(80);
  const aEsc = await ev(STATE);
  await mouse("mouseReleased", a0.to.x, a0.to.y, 0); await Bun.sleep(150);
  const aUp = await ev(STATE);
  await ev(OPEN); await Bun.sleep(150);
  const aRows = (await ev(ROWS)).map((r: any) => r.id);
  const okA = a0.mid.line && a0.mid.dragRow && !aEsc.pop && !aEsc.line && !aEsc.body && JSON.stringify(aUp.order) === JSON.stringify(HTML_ORDER) && aUp.saved === null && !aUp.line && JSON.stringify(aRows) === JSON.stringify(HTML_ORDER);
  check("s14a 끄는 도중 Esc → 팝오버 닫힘 · 삽입선·전역 표시 0 → 놓아도 순서·저장 불변 · 다시 열어도 처음 순서", okA, { during: { line: a0.mid.line, dragRow: a0.mid.dragRow }, afterEsc: { pop: aEsc.pop, line: aEsc.line, body: aEsc.body }, afterUp: { order: aUp.order, saved: aUp.saved }, reopened: aRows });
  // ⓑ 끄는 도중 창이 초점을 잃음 → 놓음 → 그 뒤 토글 누름은 정상(삼켜지지 않는다)
  await load();
  await ev(OPEN); await Bun.sleep(150);
  const b0 = await startDrag();
  await ev(`window.dispatchEvent(new Event("blur"))`); await Bun.sleep(80);
  const bBlur = await ev(STATE);
  await mouse("mouseReleased", b0.to.x, b0.to.y, 0); await Bun.sleep(150);
  const bUp = await ev(STATE);
  const tg = await pt("btn-new", ".tb-toggle", 0.5);
  await mouse("mousePressed", tg.x, tg.y, 1); await mouse("mouseReleased", tg.x, tg.y, 0); await Bun.sleep(120);
  const bClick = await ev(`({ shown: ${TB}.shownIds.includes("btn-new"), saved: ${SAVED} })`);
  const okB = b0.mid.line && bBlur.pop && !bBlur.line && !bBlur.body && !bBlur.dragRow && JSON.stringify(bUp.order) === JSON.stringify(HTML_ORDER) && bUp.saved === null && bClick.shown && bClick.saved?.items?.find((x: any) => x.id === "btn-new")?.on === true && JSON.stringify(bClick.saved.items.map((x: any) => x.id)) === JSON.stringify(HTML_ORDER);
  check("s14b 끄는 도중 창이 초점을 잃음 → 끌기 버림(팝오버는 열린 채) → 놓아도 순서·저장 불변 → 그 뒤 실제 누름(+ New 토글)은 정상", okB, { afterBlur: { pop: bBlur.pop, line: bBlur.line, body: bBlur.body, dragRow: bBlur.dragRow }, afterUp: { order: bUp.order, saved: bUp.saved }, clickAfter: { newShown: bClick.shown, savedOrderUnchanged: JSON.stringify(bClick.saved?.items?.map((x: any) => x.id)) === JSON.stringify(HTML_ORDER) } });
  // ⓒ 취소 뒤 다시 끌면 정상으로 놓인다(취소가 다음 끌기를 망가뜨리지 않는다)
  const c0 = await startDrag();
  await mouse("mouseReleased", c0.to.x, c0.to.y, 0); await Bun.sleep(150);
  const cUp = await ev(STATE);
  const want = ["btn-feedback", "btn-restart-daemon", ...HTML_ORDER.slice(1).filter((x) => x !== "btn-restart-daemon")];
  check("s14c 취소 뒤 다시 끌어 놓기 = 정상 반영(↻ 재시작이 피드백 아래 · 저장)", JSON.stringify(cUp.order) === JSON.stringify(want) && JSON.stringify(cUp.saved?.items?.map((x: any) => x.id)) === JSON.stringify(want) && !cUp.line && !cUp.body, { order: cUp.order });
}

if (ONLY.includes("s15")) {
  await size(1440, 900); await load();
  await ev(OPEN); await Bun.sleep(150);
  // 저장이 던지게 만든다(용량 초과 흉내) — 이 키의 setItem·removeItem 만
  await ev(`(() => { const S = Storage.prototype; window.__origSet = S.setItem; window.__origRem = S.removeItem; S.setItem = function (k, v) { if (k === ${JSON.stringify(KEY)}) throw new DOMException("quota (test)", "QuotaExceededError"); return window.__origSet.call(this, k, v); }; S.removeItem = function (k) { if (k === ${JSON.stringify(KEY)}) throw new DOMException("blocked (test)", "SecurityError"); return window.__origRem.call(this, k); }; })()`);
  const WARN = `(() => { const w = document.querySelector("#theme-pop .sp-warn"); return { exists: !!w, visible: !!w && w.getClientRects().length > 0, text: w ? w.textContent : "", px: w ? parseFloat(getComputedStyle(w).fontSize) : 0 }; })()`;
  const w0 = await ev(WARN);
  await ev(`${ROWBTN("btn-new", "tb-toggle")}.click()`); await Bun.sleep(80);
  const a = await ev(`({ shown: ${TB}.shownIds.includes("btn-new"), rowOn: ${ROWS}.find(r => r.id === "btn-new").on, saved: ${SAVED}, warn: ${WARN} })`);
  await ev(`document.querySelector('#theme-pop .sp-sec[data-sec="topbar"]').scrollIntoView({ block: "start" })`);
  await shot("s15-unsaved-note-1440x900.png");
  // 기본값 복원(저장 지우기)도 던진다 → 화면은 기본값 · 알림 유지
  await ev(`document.querySelector('#theme-pop .sp-sec[data-sec="topbar"] .theme-pop-reset').click()`); await Bun.sleep(80);
  const r = await ev(`({ shown: ${TB}.shown, warn: ${WARN} })`);
  // 저장이 다시 되면 알림이 사라진다
  await ev(`Storage.prototype.setItem = window.__origSet; Storage.prototype.removeItem = window.__origRem;`);
  await ev(`${ROWBTN("btn-close", "tb-toggle")}.click()`); await Bun.sleep(80);
  const b = await ev(`({ shown: ${TB}.shownIds.includes("btn-close"), savedOn: ${SAVED}?.items?.find(x => x.id === "btn-close")?.on, warn: ${WARN} })`);
  check("s15a 저장이 던져도: 상단에 반영 · 토글 글자 = 켬(동기) · 「저장되지 않았습니다」 1줄 보임 · 페이지 예외 0 → 저장이 되면 그 줄 사라짐", w0.exists && !w0.visible && a.shown && a.rowOn && a.saved === null && a.warn.visible && a.warn.text.includes("저장되지 않았습니다") && a.warn.px >= 25 && JSON.stringify(r.shown) === JSON.stringify(DEFAULT_SHOWN) && r.warn.visible && b.shown && b.savedOn === true && !b.warn.visible && !logs.length, { before: w0.visible, afterThrow: { shown: a.shown, rowOn: a.rowOn, saved: a.saved, warnVisible: a.warn.visible, warnPx: a.warn.px, text: a.warn.text }, resetThrow: { shown: r.shown.length, warnVisible: r.warn.visible }, afterOk: b });
  // 읽기가 던지는 환경 — 앱은 기본값으로 선다(문서가 뜨기 전에 이 키의 getItem 만 던지게)
  const inj = await cdp("Page.addScriptToEvaluateOnNewDocument", { source: `(() => { const g = Storage.prototype.getItem; Storage.prototype.getItem = function (k) { if (k === ${JSON.stringify(KEY)}) throw new DOMException("blocked (test)", "SecurityError"); return g.call(this, k); }; })();` });
  await load(`localStorage.setItem(${JSON.stringify(KEY)}, ${JSON.stringify(JSON.stringify({ version: 1, items: HTML_ORDER.map((id) => ({ id, on: true })) }))});`);
  const t = await ev(TB);
  await cdp("Page.removeScriptToEvaluateOnNewDocument", { identifier: inj.result.identifier });
  check("s15b 저장 읽기가 던져도 앱은 선다 — 상단 = 기본값(보이는 6개)", JSON.stringify(t.shown) === JSON.stringify(DEFAULT_SHOWN) && !logs.length, { shown: t.shown });
}

if (logs.length) { console.log("페이지 예외:"); for (const l of logs) console.log("  " + l); fails.push("page-exception"); }
if (OUT) writeFileSync(join(OUT, "numbers.json"), JSON.stringify({ ticket: "cysr-1110-screen-settings", only: ONLY, fails, numbers }, null, 2) + "\n");
console.log(fails.length ? `FAIL ${fails.length}: ${fails.join(", ")}` : "ALL PASS");
cleanup();
process.exit(fails.length ? 1 : 0);
