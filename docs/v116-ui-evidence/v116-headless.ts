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
//   c11 master 자리가 카드 유예(15초) 뒤에 선다 → 그때 카드 1회 · 닫은 뒤 같은 신호가 다시 와도 0(R1c)
//   c12 좁은 창(800폭 · 2분할) 제목: 역할 없는 창 = 「번호 · 폴더 이름」(전체 경로는 툴팁) · 끝난 창 = 「(끝남)」이 맨 앞 ·
//       역할 창 이름을 비워 확정 → 「번호 · 특성」 그대로(D4 #12)
//   c13 used_pct null(미관측) → 창 머리 배지에 그 창 0 · Control Center 계정 게이지 「—」(0% 아님)(D4 #18 나머지 절반)
//   c14 경보 알림(승인 대기 · 방치 · 대화 기억 · 유휴 · 사망 · 응답 없음) 화면 글에 surface:N·역할 코드·내부 지침 문구 0 · 사망 알림에 안심 문장(D4 #8)
//   c15 업데이트 확인 실패 → 알림 본문 = 사람 말 · 백엔드 원문은 접힌 「자세히」 안쪽(삭제 0)(D4 #14)
//   c16 새 앱 설치 확인창 = 「설치」/「취소」(아니오 0 · D4 #20) · 본문에 drain·CDHash·본체·패치 0 · 저장 안심 문장(D4 #14)
//   c17 (v116-restart-toast) 맥 새 판 교체 완료 알림이 60초 뒤 사라져도 누를 재시작 자리가 남는다 — 헤더 「업데이트」 단추가
//       「다시 켜기」로 바뀌고 누르면 restart_after_update(install_update 재호출 0) · ⌘R 뒤에도 유지 · 새 판으로 켜지면 저절로 풀림 ·
//       연타 = 재시작 호출 1 · 살아 있는 세션 확인 창 취소·재시작 실패 뒤 다시 누를 수 있음 · c17w 윈 = 대기 상태 없음(설치 경로 불변)
//   c17x 경계 — 설치 확인 창이 떠 있는 사이 교체 완료 → 「설치」 눌러도 재다운로드 0(다시 켜기) · 대기 중 더 새 판(1.1.8) → 먼저 다시 켜기 ·
//        새 앱으로 켜진 뒤 확인이 1.1.8 을 설치로 안내 · 알림 × 로 닫아도 단추 유지 · (agy 1R) ⌘R 뒤 판번 조회 실패 = 복원 0 · 기억 보존 ·
//        복원이 판번을 기다리는 사이 새 교체 완료(1.1.8) → 복원(1.1.7)이 덮지 않음 · (클로드 적대 1R) m 같은 판 재빌드 ⌘R 유지·새 build 로 풀림 ·
//        n 진행 중 확인 뒤 교체 완료 → 설치 안내 0 · o ⌘R 직후 복원 전 첫 클릭 = 다시 켜기 · p 팩 적용 완료 뒤 배지 유지 ·
//        q 좁은 창(800폭) — 「다시 켜기」가 상단바를 넘치거나 두 줄로 꺾이지 않음
//   c5 작업기억이 정본 경로(~/.cys/pack/round/SESSION_STATE.md)에만 있을 때 복원 카드가 그 내용을 싣는다
// 원형 = D4-evidence/headless-layout-check.ts(996) 의 CDP 드라이버.
import { spawn } from "bun";
import { mkdtempSync, readFileSync, writeFileSync, rmSync, existsSync, mkdirSync } from "fs";
import { join } from "path";

const H = import.meta.dir;
const DIST = process.env.DIST!;
const CH = process.env.CHS!;
const OUT = process.env.OUT || "";
const ONLY = (process.env.ONLY || "c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13,c14,c15,c16,c17,c17x,c17w").split(",");
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
  // sessionStorage 는 같은 탭·같은 출처면 칸을 넘어 남는다(c17 재시작 대기) — 칸마다 비우고 시작한다.
  await ev(`sessionStorage.clear(); localStorage.setItem("cys-layout-v2", localStorage.getItem("cys-layout-v2") ?? "{}"); ${preLS}`);
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
  await load("two", "", `window.__shimFiles["/Users/user/.cys/pack/round/SESSION_STATE.md"] = "${body}"`);
  await Bun.sleep(16000); // 카드 유예(복원 신호 없음 → 15초 뒤 표시)
  const a = await ev(`({ card: !!document.getElementById("restore-brief"), text: document.getElementById("restore-brief")?.innerText ?? "" })`);
  check("c5 정본 경로 기록 → 카드 표시", a.card && a.text.includes("정본 경로 기록 표시 시험 줄") && !a.text.includes("찾지 못했"), JSON.stringify({ card: a.card, text: a.text.replace(/\n+/g, " / ").slice(0, 240) }));
}

if (ONLY.includes("c5")) {
  // 정본 파일이 설치 골격 그대로(고정 3절 제목 없음)면 카드는 「하던 일을 복원했어요」·빈 절을 싣지 않는다(T4 무회귀).
  const skel = readFileSync(join(H, "../../cysjavis-pack/round/SESSION_STATE.md"), "utf8");
  await load("two", "", `window.__shimFiles["/Users/user/.cys/pack/round/SESSION_STATE.md"] = ${JSON.stringify(skel)}`);
  await Bun.sleep(16000);
  const a = await ev(`({ card: !!document.getElementById("restore-brief"), text: document.getElementById("restore-brief")?.innerText ?? "" })`);
  check("c5b 정본 = 설치 골격(3절 없음) → 짧은 카드 · 빈 문장 0", a.card && !a.text.includes("하던 일을 복원") && !a.text.includes("적힌 것이 없습니다"), JSON.stringify({ card: a.card, text: a.text.replace(/\n+/g, " / ").slice(0, 200) }));
}

if (ONLY.includes("c6")) {
  for (const w of [1280, 800]) {
    await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: 820, deviceScaleFactor: 1, mobile: false });
    const body = "## 완료\\n- 끝난 일 1\\n- 끝난 일 2\\n## 진행 중\\n- 하던 일 1\\n- 하던 일 2\\n## 결정 필요\\n- 정할 일\\n2026-09-23 22:10";
    await load("two", "", `window.__shimFiles["/Users/user/.cys/pack/round/SESSION_STATE.md"] = "${body}"`);
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

if (ONLY.includes("c11")) {
  // (R1c) 복원 신호 없음 · master 없이 시작 → 15초 유예가 지나도 카드 0(마스터 자리 전용) → master 가 선다(role.claimed)
  //   → 카드 1회. 종전엔 유예 시점에 「한 번 띄움」 표지를 먼저 켜 버려 그 켜짐엔 카드가 영영 안 떴다.
  const body = "## 완료\\n- 늦게 선 마스터 시험 줄\\n## 진행 중\\n- 진행 줄\\n## 결정 필요\\n- 없음\\n2026-09-23 22:10";
  await load("late", "", `window.__shimFiles["/Users/user/.cys/pack/round/SESSION_STATE.md"] = "${body}"`);
  await Bun.sleep(16000);
  const a = await ev(`!!document.getElementById("restore-brief")`);
  await ev(`window.__shimAddSeat(1, "master", "/Users/user/jarvis"); window.__shimEmit("daemon-event", { name: "role.claimed", category: "system", surface_id: 1, payload: { role: "master", surface_ref: "surface:1" } })`);
  await Bun.sleep(800);
  const b = await ev(`({ card: !!document.getElementById("restore-brief"), text: document.getElementById("restore-brief")?.innerText ?? "" })`);
  await ev(`document.querySelector("#restore-brief .rb-close")?.click()`); await Bun.sleep(100);
  await ev(`window.__shimEmit("daemon-event", { name: "role.claimed", category: "system", surface_id: 1, payload: { role: "master", surface_ref: "surface:1" } }); window.__shimEmit("daemon-event", { name: "surface.created", category: "surface", surface_id: 1, payload: { role: "master" } })`);
  await Bun.sleep(800);
  const c = await ev(`!!document.getElementById("restore-brief")`);
  check("c11 master 늦게 섬 → 유예 시점 카드 0 · 선 뒤 카드 1회(기록 실림) · 닫은 뒤 재신호에 다시 안 뜸", !a && b.card && b.text.includes("늦게 선 마스터 시험 줄") && !c, JSON.stringify({ beforeMaster: a, afterMaster: b.card, reshown: c, text: b.text.replace(/\n+/g, " / ").slice(0, 160) }));
}

if (ONLY.includes("c12")) {
  await cdp("Emulation.setDeviceMetricsOverride", { width: 800, height: 820, deviceScaleFactor: 1, mobile: false });
  const LONG = "/Users/user/axdev/.wt/very-long-worktree-name/nested/project-alpha";
  await load("two", "", `Object.assign(window.__shimSeats[1], { role: null, title: "", live_cwd: ${JSON.stringify(LONG)} })`);
  await Bun.sleep(3500); // 제목 갱신 주기
  const TT = (n: string) => `(() => { const t = ${PANE(n)}?.querySelector(".pane-title-text"); return t ? { text: t.textContent, tip: t.title } : null; })()`;
  const a = await ev(`[...document.querySelectorAll("#root .pane .pane-title-text")].map(t => ({ text: t.textContent, tip: t.title }))`);
  const shell = a.find((x: any) => x.text.startsWith("2"));
  check("c12a 역할 없는 창 제목 = 「2 · project-alpha」(번호 먼저 · 폴더 이름) · 전체 경로는 툴팁", !!shell && shell.text === "2 · project-alpha" && shell.tip === LONG, JSON.stringify(a));
  // (opus 결함 1) 역할 없는 창에서 이름 변경을 열었다가 바꾸지 않고 확정 → 데몬에 쓰지 않는다(자동 제목이 고정 제목으로 굳지 않게)
  await ev(`${PANE("project-alpha")}.querySelector(".pane-title").dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, clientX: 500, clientY: 60 }))`);
  await Bun.sleep(150);
  await ev(`[...document.querySelectorAll("#ctx-menu .ctx-item")].find(x => x.textContent.trim() === "이름 변경")?.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }))`);
  await Bun.sleep(150);
  await ev(`document.activeElement?.blur()`); await Bun.sleep(300);
  const d = await ev(`({ renames: window.__shimCalls.filter(c => c.cmd === "rename_surface").length, seat2: window.__shimSeats[1].title })`);
  check("c12d 역할 없는 창 이름 변경 → 바꾸지 않고 확정 = 쓰기 0(자동 제목 유지)", d.renames === 0 && d.seat2 === "", JSON.stringify(d));
  await ev(`window.__shimExit(2, false)`); await Bun.sleep(3500);
  const b = await ev(TT("project-alpha"));
  check("c12b 끝난 창 = 「(끝남)」이 제목 맨 앞(좁아도 먼저 잘리지 않는다)", !!b && b.text.startsWith("(끝남) ") && b.text.includes("2 · project-alpha"), JSON.stringify(b));
  // 역할 창(master) 이름 변경 → 비워서 확정
  await ev(`${PANE("master")}.querySelector(".pane-title").dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, clientX: 50, clientY: 60 }))`);
  await Bun.sleep(150);
  await ev(`[...document.querySelectorAll("#ctx-menu .ctx-item")].find(x => x.textContent.trim() === "이름 변경")?.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }))`);
  await Bun.sleep(150);
  const editing = await ev(`document.activeElement?.classList.contains("pane-title-text") ?? false`);
  await ev(`(() => { const t = document.activeElement; t.textContent = ""; t.blur(); })()`);
  await Bun.sleep(3500);
  const c = await ev(`({ renames: window.__shimCalls.filter(c => c.cmd === "rename_surface").map(c => c.args.title), seat: window.__shimSeats[0].title, shown: [...document.querySelectorAll("#root .pane .pane-title-text")].map(t => t.textContent) })`);
  check("c12c 역할 창 이름 비워 확정 → 「1 · master」 유지(번호·특성 소실 0)", editing && c.seat === "1 · master" && c.shown.includes("1 · master"), JSON.stringify({ editing, ...c }));
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
}

if (ONLY.includes("c13")) {
  const inj = `(() => { const now = Date.now() / 1000;
    window.__shimSeats[0].usage = { agent: "claude", ctx_pct: 10, source: "statusline", updated_at: now, rate: [{ label: "5h", used_pct: null, resets_at: null }, { label: "7d", used_pct: 42, resets_at: null }] };
    window.__shimAccounts = [{ account_id: "a1", provider: "claude", label: "u@example.com", plan: null, source: "statusline", updated_at: now - 5, stale_secs: 5,
      rate: [{ label: "5h", used_pct: null, resets_at: null }, { label: "7d", used_pct: 30, resets_at: now + 86400 }], scoped: [] }]; })()`;
  await load("two", "", inj);
  await Bun.sleep(3500);
  const a = await ev(`(() => { const u = ${PANE("master")}?.querySelector(".pane-usage"); return { text: u?.textContent ?? "", tip: u?.title ?? "" }; })()`);
  check("c13a 창 머리 배지: 미관측 5h = 표시 0 · 7d 42% 는 그대로 · 툴팁에도 5h 0", a.text.includes("7d 42%") && !a.text.includes("5h") && !a.tip.includes("rate 5h"), JSON.stringify(a));
  await ev(`document.getElementById("btn-cc").click()`); await Bun.sleep(300);
  await ev(`[...document.querySelectorAll(".cc-tab")].find(x => x.textContent.trim() === "Live")?.click()`); await Bun.sleep(1500);
  const b = await ev(`[...document.querySelectorAll("#cc-accounts .cc-tbar")].map(t => (t.querySelector(".cc-tbar-lab")?.textContent ?? "") + "=" + (t.querySelector(".cc-tbar-pct")?.textContent ?? "") + (t.querySelector(".cc-tbar-fill") ? "+fill" : ""))`);
  check("c13b Control Center 계정 게이지: 미관측 5h = 「—」(채움 0) · 7d = 30%", Array.isArray(b) && b.includes("5h=—") && b.includes("7d=30%+fill"), JSON.stringify(b));
  await ev(`document.getElementById("btn-cc").click()`); await Bun.sleep(200);
}

if (ONLY.includes("c14")) {
  await load("two");
  const E = (n: string, sid: number | null, cat: string, p: any) => `window.__shimEmit("daemon-event", ${JSON.stringify({ name: n, category: cat, surface_id: sid, socket_slug: "", payload: p })})`;
  await ev([
    E("approval.request", 2, "feed", { role: "worker", surface_ref: "surface:2", excerpt: "Do you want to proceed?" }),
    E("approval.stalled", 2, "watchdog", { title: "배포 승인", age_secs: 400, surface_ref: "surface:2" }),
    E("context.threshold", 2, "watchdog", { role: "worker", context_pct: 83, threshold: 60, surface_ref: "surface:2", action: "cycle-agent(저장→검증→clear→복원) 집행 대상 — MASTER_DIRECTIVE §컨텍스트 사이클" }),
    E("pane.idle", 2, "watchdog", { idle_seconds: 900, surface_ref: "surface:2" }),
    E("master.idle", 1, "info", { role: "master", idle_secs: 320, threshold_secs: 300 }),
    E("agent.exited", 2, "surface", { role: "worker", agent: "claude", surface_ref: "surface:2" }),
    E("master.deadman", 1, "alert", { role: "master", axis: "agent_dead", reason: "agent process dead", surface_ref: "surface:1" }),
  ].join(";"));
  await Bun.sleep(600);
  const a = await ev(`[...document.querySelectorAll("#toasts .toast")].map(t => t.innerText.replace(/\\n+/g, " / "))`);
  const txt = (a as string[]).join(" | ");
  const bad = /surface:\d|\bmaster\b|\bworker\b|MASTER_DIRECTIVE|cycle-agent|deadman|에이전트 사망|\d+s\b/.exec(txt);
  const death = (a as string[]).find((t) => t.includes("❌"));
  check("c14 경보 7종 화면 글: 코드 원문 0 · ❌ 사망 알림에 「창과 작업 폴더는 그대로」 + 확인 행동", (a as string[]).length >= 7 && !bad && !!death && death.includes("그대로 남아 있습니다") && death.includes("2번 작업 창"), JSON.stringify({ n: (a as string[]).length, bad: bad?.[0] ?? null, death: death ?? null, sample: txt.slice(0, 300) }));
}

if (ONLY.includes("c15")) {
  await load("two", "", `window.__shimFailUpdate = true`);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(800);
  const a = await ev(`(() => { const t = [...document.querySelectorAll("#toasts .toast")].find(x => x.querySelector(".toast-name")?.textContent === "업데이트 확인 실패"); if (!t) return { found: false }; const d = t.querySelector("details.toast-raw"); return { found: true, detail: t.querySelector(".toast-detail").textContent, details: !!d, open: d?.open ?? null, summary: d?.querySelector("summary")?.textContent ?? "", raw: d?.querySelector(".toast-raw-text")?.textContent ?? "", visible: t.innerText.replace(/\\n+/g, " / ") }; })()`);
  check("c15 업데이트 확인 실패 → 본문 사람 말 · 원문은 접힌 「자세히」 안(보이는 글에 원문 0 · 원문 보존)", a.found && !a.detail.includes("error sending") && a.details && a.open === false && a.summary === "자세히" && a.raw.includes("error sending request") && !a.visible.includes("error sending"), JSON.stringify(a));
}

if (ONLY.includes("c16")) {
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }`);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(800);
  const a = await ev(`(() => { const m = document.querySelector(".modal-overlay .modal"); if (!m) return { modal: false }; return { modal: true, yes: m.querySelector(".modal-yes")?.textContent, no: m.querySelector(".modal-no")?.textContent, text: m.innerText.replace(/\\n+/g, " / ") }; })()`);
  const bad = /drain|CDHash|본체|패치|미저장분/.exec(a.text ?? "");
  check("c16 새 앱 설치 확인창 = 설치/취소 · 내부 용어 0 · 저장 안심 문장", a.modal && a.yes === "설치" && a.no === "취소" && !bad && /대화가 돌아옵니다/.test(a.text), JSON.stringify({ ...a, bad: bad?.[0] ?? null }));
  await ev(`document.querySelector(".modal-no")?.click()`);
}

if (ONLY.includes("c17")) {
  const MAC_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36";
  await cdp("Emulation.setUserAgentOverride", { userAgent: MAC_UA });
  // 누를 수 있는 재시작 자리 = 누르면 동작하는 알림 + 「다시 켜기」 상태의 헤더 단추
  const SPOTS = `(() => { const b = document.getElementById("btn-update"); const label = (b.firstChild?.nodeValue ?? "").trim();
    const toastsClickable = [...document.querySelectorAll("#toasts .toast")].filter(t => typeof t.onclick === "function").length;
    const installToasts = [...document.querySelectorAll("#toasts .toast")].map(t => t.innerText).filter(t => /누르면 설치/.test(t)).length;
    return { label, toastsClickable, installToasts, badge: document.getElementById("update-badge").hidden ? null : document.getElementById("update-badge").textContent, tip: b.title,
      restarts: window.__shimCalls.filter(c => c.cmd === "restart_after_update").map(c => !!c.args.force), installs: ${NCALL("install_update")}, checks: ${NCALL("check_update")},
      modal: document.querySelector(".modal-overlay .modal")?.innerText.replace(/\\n+/g, " / ") ?? null }; })()`;
  const RESTART_EV = `window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`;
  // ── A. 교체 완료 알림 → 60초 수명 경과 → 헤더 단추로 다시 켜기
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }`);
  await ev(RESTART_EV); await Bun.sleep(400);
  const a0 = await ev(SPOTS);
  const toastText = await ev(`[...document.querySelectorAll("#toasts .toast")].filter(t => typeof t.onclick === "function").map(t => t.innerText.replace(/\\n+/g, " / ")).join(" | ")`);
  console.log("     알림 문안: " + toastText);
  await Bun.sleep(61000); // 지속형 알림 수명 60초(toastttl.ts STICKY_TTL_MS) 경과
  const a1 = await ev(SPOTS);
  await shot("c17a-after-ttl.png");
  check("c17a 교체 완료 60초 뒤 = 알림은 사라지고(오너 정책) 헤더 단추가 「다시 켜기」로 남는다 · 설치 안내 0", a0.toastsClickable >= 1 && a1.toastsClickable === 0 && a1.label === "다시 켜기" && a1.badge === "!" && a1.installToasts === 0, JSON.stringify({ before: a0, after: a1 }));
  const c0 = a1.checks;
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(600);
  let a2 = await ev(SPOTS);
  if (a2.modal && /설치/.test(a2.modal)) { await ev(`document.querySelector(".modal-yes")?.click()`); await Bun.sleep(400); a2 = { ...(await ev(SPOTS)), installModal: a2.modal }; } // 기준선: 설치 확인 창 → 재다운로드
  check("c17b 「다시 켜기」 누름 → restart_after_update 1회 · install_update 0 · 새 확인 0", JSON.stringify(a2.restarts) === "[false]" && a2.installs === 0 && a2.checks === c0, JSON.stringify(a2));
  // ── B. 화면 새로고침(⌘R) — 같은 옛 앱 프로세스 · 확인은 여전히 1.1.7 을 「새 판」이라 답한다
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }; sessionStorage.setItem("__shimUpdate", JSON.stringify(window.__shimUpdate))`);
  await ev(RESTART_EV); await Bun.sleep(400);
  await cdp("Page.reload", {}); await Bun.sleep(3500);
  const b1 = await ev(SPOTS);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(600);
  const b2 = await ev(SPOTS);
  if (b2.modal) { await ev(`document.querySelector(".modal-no")?.click()`); await Bun.sleep(200); }
  // (뮤턴트 M17 생존 봉합) ⌘R 뒤엔 시작 확인이 머리에서 끝나므로 배지 「!」 는 다시 칠하기만이 켠다 — 여기서 잰다.
  check("c17c ⌘R 뒤에도 「다시 켜기」·배지 「!」 유지 · 시작 확인이 설치 안내를 띄우지 않음 · 누르면 재시작(설치 0)", b1.label === "다시 켜기" && b1.badge === "!" && b1.installToasts === 0 && JSON.stringify(b2.restarts) === "[false]" && b2.installs === 0, JSON.stringify({ afterReload: b1, afterClick: b2 }));
  // ── C. 새 판으로 켜진 앱(판번 = 대기 판번) — 대기 상태가 저절로 풀린다(남은 기억이 있어도)
  await ev(`sessionStorage.setItem("__shimAppVersion", "1.1.7"); sessionStorage.removeItem("__shimUpdate")`);
  await cdp("Page.reload", {}); await Bun.sleep(3500);
  const c1 = await ev(`({ key: sessionStorage.getItem("cys-restart-pending-v1"), ...${SPOTS} })`);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(600);
  const c2 = await ev(SPOTS);
  check("c17d 새 판으로 켜진 뒤 = 단추 「업데이트」 · 남은 기억 칸 삭제 · 누르면 확인(재시작 0)", c1.label === "업데이트" && c1.key === null && c2.restarts.length === 0 && c2.checks > c1.checks, JSON.stringify({ c1, c2 }));
  // ── D. 연타 — 헤더 두 번 + 알림 한 번을 한 틱에 → 재시작 호출 1
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }`);
  await ev(RESTART_EV); await Bun.sleep(400);
  await ev(`(() => { const b = document.getElementById("btn-update"); b.click(); b.click(); [...document.querySelectorAll("#toasts .toast")].find(t => typeof t.onclick === "function")?.click(); })()`);
  await Bun.sleep(600);
  const d1 = await ev(SPOTS);
  check("c17e 연타(헤더 2 + 알림 1 · 같은 틱) → restart_after_update 1회 · 설치 0 · 설치 확인 창 0", JSON.stringify(d1.restarts) === "[false]" && d1.installs === 0 && d1.modal === null, JSON.stringify(d1));
  // ── E. 살아 있는 세션 확인 창 — 열린 동안 다시 눌러도 창 1개 · 취소 뒤 다시 누를 수 있음 · 승낙 = force 재호출
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }; window.__shimRestartLive = true`);
  await ev(RESTART_EV); await Bun.sleep(400);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(500);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(500);
  const e1 = await ev(`({ modals: document.querySelectorAll(".modal-overlay").length, ...${SPOTS} })`);
  await ev(`document.querySelector(".modal-no")?.click()`); await Bun.sleep(300);
  const e2 = await ev(SPOTS);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(500);
  await ev(`document.querySelector(".modal-yes")?.click()`); await Bun.sleep(400);
  const e3 = await ev(SPOTS);
  check("c17f 세션 확인 창 열린 채 재클릭 = 창 1 · 취소 뒤 「다시 켜기」 유지 · 다시 눌러 승낙 → force 호출", e1.modals === 1 && JSON.stringify(e1.restarts) === "[false]" && e2.label === "다시 켜기" && JSON.stringify(e3.restarts) === "[false,false,true]" && e3.installs === 0, JSON.stringify({ e1, e2, e3 }));
  // ── F. 재시작 실패 → 알림 뒤에도 「다시 켜기」 유지 · 다시 누르면 다시 시도
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }; window.__shimRestartFail = true`);
  await ev(RESTART_EV); await Bun.sleep(400);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(500);
  const f1 = await ev(`({ failToast: [...document.querySelectorAll("#toasts .toast .toast-name")].some(t => t.textContent === "재시작 실패"), ...${SPOTS} })`);
  await ev(`window.__shimRestartFail = false; document.getElementById("btn-update").click()`); await Bun.sleep(500);
  const f2 = await ev(SPOTS);
  check("c17g 재시작 실패 → 실패 알림 · 「다시 켜기」 유지 · 다시 눌러 재시도 → 호출 2", f1.failToast && f1.label === "다시 켜기" && JSON.stringify(f2.restarts) === "[false,false]" && f2.installs === 0, JSON.stringify({ f1, f2 }));
}

if (ONLY.includes("c17x")) {
  await cdp("Emulation.setUserAgentOverride", { userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36" });
  const X = `({ label: (document.getElementById("btn-update").firstChild?.nodeValue ?? "").trim(), restarts: window.__shimCalls.filter(c => c.cmd === "restart_after_update").map(c => !!c.args.force), installs: ${NCALL("install_update")}, modal: document.querySelector(".modal-overlay .modal")?.innerText.replace(/\\n+/g, " / ") ?? null, toasts: document.querySelectorAll("#toasts .toast").length })`;
  // h. 설치 확인 창이 떠 있는 사이 다른 설치의 교체가 끝남 → 「설치」 → install_update 0 · 다시 켜기
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }`);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(600);
  const h0 = await ev(X);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`); await Bun.sleep(300);
  await ev(`document.querySelector(".modal-yes")?.click()`); await Bun.sleep(500);
  const h1 = await ev(X);
  check("c17h 설치 확인 창 떠 있는 사이 교체 완료 → 「설치」 눌러도 install_update 0 · restart_after_update 1", !!h0.modal && /설치/.test(h0.modal) && h1.installs === 0 && JSON.stringify(h1.restarts) === "[false]", JSON.stringify({ h0, h1 }));
  // i. 대기(1.1.7) 중 더 새 판(1.1.8)이 나옴 → 옛 앱에선 먼저 다시 켜기(재다운로드 0) → 새 앱(1.1.7)으로 켜지면 확인이 1.1.8 설치 안내
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }; sessionStorage.setItem("__shimUpdate", JSON.stringify(window.__shimUpdate))`);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`); await Bun.sleep(300);
  await ev(`window.__shimUpdate = { version: "1.1.8", notes: "" }; sessionStorage.setItem("__shimUpdate", JSON.stringify(window.__shimUpdate))`);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(500);
  const i1 = await ev(X);
  await ev(`sessionStorage.setItem("__shimAppVersion", "1.1.7")`);
  await cdp("Page.reload", {}); await Bun.sleep(3500);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(600);
  const i2 = await ev(X);
  if (i2.modal) { await ev(`document.querySelector(".modal-no")?.click()`); await Bun.sleep(200); }
  check("c17i 대기 중 더 새 판 → 옛 앱 = 다시 켜기(설치 0) · 새 앱으로 켜진 뒤 = 「업데이트」 → 1.1.8 설치 확인", i1.label === "다시 켜기" && JSON.stringify(i1.restarts) === "[false]" && i1.installs === 0 && i2.label === "업데이트" && /새 앱 1\.1\.8 설치/.test(i2.modal ?? ""), JSON.stringify({ i1, i2 }));
  // j. 알림을 × 로 닫아도 단추는 「다시 켜기」 그대로
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }`);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`); await Bun.sleep(300);
  await ev(`[...document.querySelectorAll("#toasts .toast")].find(t => typeof t.onclick === "function")?.querySelector(".toast-x")?.click()`); await Bun.sleep(200);
  const j1 = await ev(`({ clickable: [...document.querySelectorAll("#toasts .toast")].filter(t => typeof t.onclick === "function").length, ...${X} })`);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(500);
  const j2 = await ev(X);
  check("c17j 알림 × 로 닫음 → 누르는 알림 0 · 단추 「다시 켜기」 · 누르면 재시작 1(× 는 재시작 0)", j1.clickable === 0 && j1.restarts.length === 0 && j1.label === "다시 켜기" && JSON.stringify(j2.restarts) === "[false]" && j2.installs === 0, JSON.stringify({ j1, j2 }));
  // k. (agy 1R #2) ⌘R 뒤 판번 조회가 실패 → 복원하지 않되(검증 불가) 기억은 지우지 않는다 → 다음 새로고침에 복원
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }; sessionStorage.setItem("__shimUpdate", JSON.stringify(window.__shimUpdate))`);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`); await Bun.sleep(300);
  await ev(`sessionStorage.setItem("__shimFailAppVersion", "1")`);
  await cdp("Page.reload", {}); await Bun.sleep(3500);
  const k1 = await ev(`({ kept: sessionStorage.getItem("cys-restart-pending-v1"), ...${X} })`);
  await ev(`sessionStorage.removeItem("__shimFailAppVersion")`);
  await cdp("Page.reload", {}); await Bun.sleep(3500);
  const k2 = await ev(X);
  check("c17k ⌘R 뒤 판번 조회 실패 → 복원 0(단추 「업데이트」) · 기억 보존 → 조회가 되는 다음 새로고침에 「다시 켜기」", k1.label === "업데이트" && !!k1.kept && k2.label === "다시 켜기", JSON.stringify({ k1, k2 }));
  // l. (agy 1R #3) ⌘R 복원이 판번 조회를 기다리는 사이 새 교체(1.1.8)가 끝남 → 복원한 1.1.7 이 메모리의 1.1.8 을 덮지 않는다
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }; sessionStorage.setItem("__shimUpdate", JSON.stringify(window.__shimUpdate))`);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`); await Bun.sleep(300);
  await ev(`sessionStorage.setItem("__shimAppVersionDelayMs", "2000")`);
  await cdp("Page.reload", {}); await Bun.sleep(400);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.8", reason: "app_replaced" })`);
  await Bun.sleep(3500);
  const l1 = await ev(`({ tip: document.getElementById("btn-update").title, ...${X} })`);
  await ev(`sessionStorage.removeItem("__shimAppVersionDelayMs")`);
  check("c17l 복원 대기 중 새 교체 완료(1.1.8) → 대기 판번 = 1.1.8 유지(복원 1.1.7 이 덮지 않음)", l1.label === "다시 켜기" && /1\.1\.8/.test(l1.tip) && !/1\.1\.7/.test(l1.tip), JSON.stringify(l1));
  // m. (클로드 적대 1R MAJOR) 같은 판 재빌드(1.1.6 build-A → 1.1.6 build-B) — ⌘R 뒤에도 대기 유지 · build-B 로 켜지면 풀림
  await load("two", "", `window.__shimUpdate = { version: "1.1.6", notes: "" }; sessionStorage.setItem("__shimUpdate", JSON.stringify(window.__shimUpdate))`);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.6", reason: "app_replaced" })`); await Bun.sleep(300);
  await cdp("Page.reload", {}); await Bun.sleep(3500);
  const m1 = await ev(X);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(500);
  const m2 = await ev(X);
  await ev(`sessionStorage.setItem("__shimBuildId", "build-B"); sessionStorage.removeItem("__shimUpdate")`);
  await cdp("Page.reload", {}); await Bun.sleep(3500);
  const m3 = await ev(`({ key: sessionStorage.getItem("cys-restart-pending-v1"), ...${X} })`);
  check("c17m 같은 판 재빌드 → ⌘R 뒤 「다시 켜기」 유지 · 누르면 재시작(설치 0) · 새 build 로 켜지면 「업데이트」·칸 삭제", m1.label === "다시 켜기" && JSON.stringify(m2.restarts) === "[false]" && m2.installs === 0 && m3.label === "업데이트" && m3.key === null, JSON.stringify({ m1, m2, m3 }));
  // n. (클로드 적대 1R #2) 단추 확인이 응답을 기다리는 사이 교체 완료 → 설치 확인 창·설치 안내 0 · 「다시 켜기」 유지
  //    (시작 확인 때는 새 판 없음 — 시작 확인의 8초 안내가 판정에 섞이지 않게 · 누르기 직전에 1.1.7 이 나온다)
  await load("two", "");
  await ev(`window.__shimUpdate = { version: "1.1.7", notes: "" }; window.__shimCheckDelayMs = 1500; document.getElementById("btn-update").click()`); await Bun.sleep(300);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`); await Bun.sleep(2200);
  const n1 = await ev(`({ badge: document.getElementById("update-badge").textContent, tip: document.getElementById("btn-update").title, installToasts: [...document.querySelectorAll("#toasts .toast")].filter(t => /누르면 설치/.test(t.innerText)).length, ...${X} })`);
  check("c17n 진행 중 확인 뒤 교체 완료 → 설치 확인 창 0 · 설치 안내 0 · 「다시 켜기」·툴팁 유지", n1.modal === null && n1.installs === 0 && n1.installToasts === 0 && n1.label === "다시 켜기" && n1.badge === "!" && /설치가 끝났습니다/.test(n1.tip), JSON.stringify(n1));
  // o. (클로드 적대 1R #4) ⌘R 직후 복원이 끝나기 전 첫 클릭 → 확인이 아니라 다시 켜기
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }; sessionStorage.setItem("__shimUpdate", JSON.stringify(window.__shimUpdate))`);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`); await Bun.sleep(300);
  await ev(`sessionStorage.setItem("__shimAppVersionDelayMs", "1500")`);
  await cdp("Page.reload", {}); await Bun.sleep(300);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(2500);
  const o1 = await ev(X);
  await ev(`sessionStorage.removeItem("__shimAppVersionDelayMs")`);
  check("c17o ⌘R 직후 복원 전 첫 클릭 → restart_after_update 1 · 설치 0 · 설치 확인 창 0", JSON.stringify(o1.restarts) === "[false]" && o1.installs === 0 && o1.modal === null, JSON.stringify(o1));
  // p. (클로드 적대 1R #6) 대기 중 팩 적용 완료 → 배지 「!」 유지
  await load("two", "");
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`); await Bun.sleep(300);
  await ev(`window.__shimEmit("pack-updated", { pack_version: "9.9.9" })`); await Bun.sleep(300);
  const p1 = await ev(`({ badgeHidden: document.getElementById("update-badge").hidden, badge: document.getElementById("update-badge").textContent, ...${X} })`);
  check("c17p 대기 중 팩 적용 완료 → 배지 「!」 유지 · 단추 「다시 켜기」", !p1.badgeHidden && p1.badge === "!" && p1.label === "다시 켜기", JSON.stringify(p1));
  // q. 좁은 창 — 단추 글자가 「업데이트」(4자)보다 긴 「다시 켜기」(5자)가 돼도 상단바 넘침·줄바꿈 0 · 단추가 화면 안
  await cdp("Emulation.setDeviceMetricsOverride", { width: 800, height: 820, deviceScaleFactor: 1, mobile: false });
  await load("two", "");
  const Q = `(() => { const bar = document.getElementById("topbar"); const b = document.getElementById("btn-update"); const c = document.getElementById("btn-close"); const r = b.getBoundingClientRect();
    return { label: (b.firstChild?.nodeValue ?? "").trim(), barOverflow: bar.scrollWidth - bar.clientWidth, h: Math.round(r.height), hRef: Math.round(c.getBoundingClientRect().height), inView: r.left >= 0 && r.right <= window.innerWidth, pageOverflow: document.documentElement.scrollWidth - window.innerWidth }; })()`;
  const q0 = await ev(Q);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`); await Bun.sleep(300);
  const q1 = await ev(Q);
  await shot("c17q-w800-restart.png");
  check("c17q w800 「다시 켜기」 = 상단바 넘침 증가 0 · 단추 한 줄(높이 = 이웃 단추) · 화면 안 · 페이지 가로 넘침 0", q1.label === "다시 켜기" && q1.barOverflow <= q0.barOverflow && q1.h === q1.hRef && q1.inView && q1.pageOverflow <= 0, JSON.stringify({ q0, q1 }));
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
}

if (ONLY.includes("c17w")) {
  // 윈도: 백엔드가 교체 완료 이벤트를 내지 않는다(install_update_plugin 이 곧장 재시작) → 대기 상태가 생기지 않고 설치 경로 그대로
  await cdp("Emulation.setUserAgentOverride", { userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36" });
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }`);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(600);
  const w = await ev(`({ label: (document.getElementById("btn-update").firstChild?.nodeValue ?? "").trim(), modal: document.querySelector(".modal-overlay .modal")?.innerText.replace(/\\n+/g, " / ") ?? "", restarts: ${NCALL("restart_after_update")}, pending: sessionStorage.length })`);
  await ev(`document.querySelector(".modal-yes")?.click()`); await Bun.sleep(400);
  const w2 = await ev(`({ installs: ${NCALL("install_update")}, restarts: ${NCALL("restart_after_update")} })`);
  check("c17w 윈도 = 단추 「업데이트」 · 누르면 설치 확인 → install_update · 재시작 대기 0", w.label === "업데이트" && /새 앱 1\.1\.7 설치/.test(w.modal) && w.restarts === 0 && w.pending === 0 && w2.installs === 1 && w2.restarts === 0, JSON.stringify({ ...w, ...w2 }));
  await cdp("Emulation.setUserAgentOverride", { userAgent: "" });
}

if (logs.length) console.log("page exceptions:\n  " + logs.slice(0, 5).join("\n  "));
console.log(fails.length ? `FAIL (${fails.length}): ${fails.join(" · ")}` : "ALL PASS");
cleanup();
process.exit(fails.length ? 1 : 0);
