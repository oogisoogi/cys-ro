// 격리 데몬 실재생 — 헤드리스 UI(새 번들) ↔ 브리지(/rpc) ↔ 격리 cysd(짧은 /tmp 소켓). 라이브 앱·데몬 무접촉.
// list_surfaces·create_surface·close_surface 만 진짜 데몬으로 · 나머지(출력 흐름 등)는 shim.js 흉내.
import { spawn, spawnSync } from "bun";
import { mkdtempSync, readFileSync, writeFileSync, rmSync, existsSync, mkdirSync } from "fs";
import { join } from "path";
const DIST = process.env.DIST!, CH = process.env.CHS!, SOCK = process.env.SOCK!, OUT = process.env.OUT!, CYSX = process.env.CYSX!;
mkdirSync(OUT, { recursive: true });
const shim = readFileSync(process.env.SHIM!, "utf8");
const bridge = `(() => { const orig = window.__TAURI__.core.invoke; const R = { list_surfaces: 1, create_surface: 1, close_surface: 1 };
  const inv = (cmd, args) => R[cmd] ? fetch("/rpc", { method: "POST", body: JSON.stringify({ cmd, args: args || {} }) }).then(r => r.json()).then(j => { window.__shimCalls.push({ cmd, args: args || {} }); if (j.err) throw new Error(j.err); return j.res; }) : orig(cmd, args);
  window.__TAURI__.core.invoke = inv; window.__TAURI_INTERNALS__.invoke = inv; })();`;
async function rpc(method: string, params: any): Promise<any> {
  return await new Promise((resolve, reject) => {
    let buf = "";
    Bun.connect({ unix: SOCK, socket: {
      open(s) { s.write(JSON.stringify({ id: 1, method, params }) + "\n"); },
      data(s, d) { buf += new TextDecoder().decode(d); const i = buf.indexOf("\n"); if (i >= 0) { s.end(); const j = JSON.parse(buf.slice(0, i)); j.ok === false || j.error ? reject(new Error(JSON.stringify(j.error ?? j))) : resolve(j.result ?? j); } },
      error(_s, e) { reject(e); },
    } }).catch(reject);
  });
}
const server = Bun.serve({ port: 0, hostname: "127.0.0.1", async fetch(req) {
  const p = new URL(req.url).pathname.replace(/^\/+/, "") || "index.html";
  if (p === "rpc") {
    const { cmd, args } = await req.json();
    try {
      const res = cmd === "list_surfaces" ? await rpc("surface.list", {})
        : cmd === "create_surface" ? await rpc("surface.create", { cwd: args.cwd ?? "/tmp", title: args.title ?? null, rows: args.rows ?? 35, cols: args.cols ?? 120 })
        : (await rpc("surface.close", { surface_id: args.surfaceId }), null);
      return Response.json({ res });
    } catch (e) { return Response.json({ err: String(e) }); }
  }
  const f = join(DIST, p);
  if (!existsSync(f)) return new Response("nf", { status: 404 });
  const ct = p.endsWith(".html") ? "text/html; charset=utf-8" : p.endsWith(".js") ? "text/javascript; charset=utf-8" : p.endsWith(".css") ? "text/css; charset=utf-8" : "application/octet-stream";
  return new Response(Bun.file(f), { headers: { "content-type": ct } });
} });
const prof = mkdtempSync("/tmp/aeqchs-");
const chrome = spawn([CH, "--headless", "--remote-debugging-port=0", `--user-data-dir=${prof}`, "--no-first-run", "--hide-scrollbars", "about:blank"], { stderr: "pipe" });
writeFileSync(join(OUT, "chrome.pid"), String(chrome.pid));
const cleanup = () => { try { chrome.kill(9); } catch {} server.stop(true); try { rmSync(prof, { recursive: true, force: true }); } catch {} };
process.on("exit", cleanup);
let port = 0;
for (let i = 0; i < 100 && !port; i++) { await Bun.sleep(100); const f = join(prof, "DevToolsActivePort"); if (existsSync(f)) port = Number(readFileSync(f, "utf8").split("\n")[0]); }
const tl = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json() as any[];
const ws = new WebSocket(tl.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pend = new Map<number, (v: any) => void>(); const logs: string[] = [];
ws.onmessage = (m) => { const d = JSON.parse(String(m.data)); if (d.id && pend.has(d.id)) { pend.get(d.id)!(d); pend.delete(d.id); } else if (d.method === "Runtime.exceptionThrown") logs.push("EXC " + (d.params.exceptionDetails?.exception?.description || "").slice(0, 200)); };
const cdp = (method: string, params: any = {}) => new Promise<any>((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr: string) => (await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
const shot = async (name: string) => { const r = await cdp("Page.captureScreenshot", { format: "png" }); writeFileSync(join(OUT, name), Buffer.from(r.result.data, "base64")); };
await cdp("Page.enable"); await cdp("Runtime.enable");
await cdp("Page.addScriptToEvaluateOnNewDocument", { source: shim + "\n" + bridge });
await cdp("Emulation.setDeviceMetricsOverride", { width: 1440, height: 860, deviceScaleFactor: 1, mobile: false });
await cdp("Page.navigate", { url: `http://127.0.0.1:${server.port}/index.html?sc=none` });
await Bun.sleep(5000);
const G = `(() => { const r = document.getElementById("root").getBoundingClientRect(); const o = {}; document.querySelectorAll("#root .pane[data-sid]").forEach(p => { const b = p.getBoundingClientRect(); o[p.dataset.sid] = +(b.width / r.width).toFixed(3) + "×" + +(b.height / r.height).toFixed(3); }); return o; })()`;
const cysx = (...a: string[]) => { const r = spawnSync([CYSX, ...a]); return (r.stdout.toString() + r.stderr.toString()).trim(); };
const step = async (name: string) => { const g = await ev(G); console.log(`${name.padEnd(46)} ${JSON.stringify(g)}`); await shot(name.split(" ")[0] + ".png"); return g; };
await step("s0 복원 입양(master·cso·worker)");
const o1 = cysx("new-surface", "--role", "worker", "--cwd", "/tmp", "--cmd", "sleep 1800"), o2 = cysx("new-surface", "--role", "worker", "--cwd", "/tmp", "--cmd", "sleep 1800");
const MID = Number(o1.split(":")[1]);
console.log("   daemon:", o1, o2);
await Bun.sleep(4000); await step("s1 master 가 워커 2대 열기(데몬)");
console.log("   daemon:", cysx("close-surface", String(MID)));
await Bun.sleep(8000); await step("s2 master 가 가운데 워커 닫기(데몬 close)");
const firstW = await ev(`[...document.querySelectorAll("#root .pane[data-sid]")].map(p => +p.dataset.sid)[2]`);
await ev(`document.querySelector('#root .pane[data-sid="' + ${firstW} + '"]').dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
await ev(`window.dispatchEvent(new KeyboardEvent("keydown", { key: "w", metaKey: true, bubbles: true, cancelable: true }))`); await Bun.sleep(300);
await ev(`document.querySelector(".modal-yes")?.click()`); await Bun.sleep(1500);
await step("s3 사람이 첫 워커 닫기(⌘W·확인)");
await ev(`localStorage.setItem("cys-expert-mode", "1")`);
await ev(`window.dispatchEvent(new KeyboardEvent("keydown", { key: "t", metaKey: true, bubbles: true, cancelable: true }))`); await Bun.sleep(2500);
await step("s4 사람이 새 창(⌘T)");
console.log("   daemon list:\n" + cysx("list"));
if (logs.length) console.log("page exceptions:\n  " + logs.join("\n  "));
cleanup(); process.exit(0);
