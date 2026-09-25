// v116-ui 헤드리스 시험 — ui/dist 실번들 + Tauri 흉내(shim.js) · 별도 바이너리 chrome-headless-shell · 종료 시 크롬 정리.
// usage: DIST=<ui/dist> CHS=<chrome-headless-shell> [OUT=<캡처 폴더>] [ONLY=c1,c3] bun v116-headless.ts → exit 0 PASS / 1 FAIL
// 판정 5축(브리프 v116-ui-close §6):
//   c1 산 창 Close·⌘W → 확인 1회(기본 포커스 = 취소 · 겹침 0 · 취소 시 close_surface 0) · exited 창 Close → 확인 0 · 바로 닫힘
//   c2 복원 직후 목록 조회 실패(이벤트 유실 잔재) → 다음 틱에 [exited] 옛 창 0
//   c3 창 2개 중 1개 exited(이벤트) → 남은 창 폭 = 전체 · PTY cols 재조정
//   c4 (v116-recut-newsplit) 기본 화면 상단에 + New · Split → · Split ↓ 보임(1.1.5 되살림) · 누르면 창 +1(Split ↓ = 세로 분할) ·
//      전문가 모드 칸에 「창 만들기」 → 오른쪽 한 갈래
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
//        q 좁은 창(800폭) — 「다시 켜기」가 상단바를 넘치거나 두 줄로 꺾이지 않음 ·
//        r (master 편입 ①) 다운로드 진행 중 헤더 재클릭 · 확인 창 2개 쌓인 채 둘 다 「설치」 → install_update 1
//   c18 (v116-auto-equalize · 오너 지시 2026-09-25) 창을 열고 닫을 때마다 자동 좌우 균등 — master·cso 좌열 몫·위아래 비율 유지:
//       a 본부+워커1 → 워커 입양(R1 재현 자리) · b 외부 닫힘(가운데) · c ⌘W 닫기 · d 창 머리 × · e 새 창(창 만들기) ·
//       f 사람이 끈 좌열 0.40·위아래 0.65 보존 · g 워커만(본부 없는 기기) 열기·닫기 · h 1280·1920·800 폭 ·
//       i (v2 · 박사님 결정 09-25 14:1x) 팔레트 「세로 분할」 복원 · ⌘⇧D = 대상 아래(같은 기둥 · 기둥 폭 불변) ·
//       v (v2) 사람이 세로로 나눈 기둥이 입양·닫기 뒤에도 그대로 · 좌열 4:1 유지 · 기둥끼리만 균등 · 팔레트 세로 분할 실행
//       D·h·w·o (박사님 결정 14:5x · master#73a7390d) 좌열 기본 폭 = 창의 25% · 노트북 글자 90칸 · 상한 50% — 창 폭별(3440·1920·1280·800) ·
//       창 크기 변경 때 기본 폭만 다시 잼(사람 0.40 그대로) · 옛 기본 1/3 저장 배치 → 새 기본으로
//   c5 작업기억이 정본 경로(~/.cys/pack/round/SESSION_STATE.md)에만 있을 때 복원 카드가 그 내용을 싣는다
// 원형 = D4-evidence/headless-layout-check.ts(996) 의 CDP 드라이버.
import { spawn } from "bun";
import { mkdtempSync, readFileSync, writeFileSync, rmSync, existsSync, mkdirSync } from "fs";
import { join } from "path";

const H = import.meta.dir;
const DIST = process.env.DIST!;
const CH = process.env.CHS!;
const OUT = process.env.OUT || "";
const ONLY = (process.env.ONLY || "c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13,c14,c15,c16,c17,c17x,c17w,c18").split(",");
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
  // ★(v116-recut-newsplit · 박사님 09-25 23:2x) 상단 「+ New · Split → · Split ↓」 되살림(1.1.5 모습) — 종전 기대값 = 초보 화면에
  //   창 만들기·Split·New 0. 지금 = 상단에 세 단추가 보이고(1.1.5 글자) · 전문가 칸 「창 만들기」는 초보 화면에 여전히 0.
  const TOP3 = ["+ New", "Split →", "Split ↓"];
  check("c4a 초보 화면 상단 + New · Split → · Split ↓ 보임 · 「창 만들기」 0", TOP3.every((t) => a.tb.includes(t)) && !a.hits.some((h: string) => h.includes("창 만들기")), JSON.stringify(a));
  await load("two", `localStorage.setItem("cys-expert-mode", "1")`);
  const b = await ev(`(() => { const btn = [...document.querySelectorAll("#ws-expert button")].find(x => x.textContent.includes("창 만들기")); if (!btn || btn.offsetParent === null) return { btn: false }; btn.click(); const items = [...document.querySelectorAll("#ctx-menu .ctx-item")].map(x => x.textContent); return { btn: true, items }; })()`);
  await shot("c4b-expert-create.png");
  const n0 = await ev(`document.querySelectorAll("#root .pane").length`);
  await ev(`[...document.querySelectorAll("#ctx-menu .ctx-item")][0]?.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }))`);
  await Bun.sleep(600);
  const n1 = await ev(`({ panes: document.querySelectorAll("#root .pane").length, col: document.querySelectorAll("#root .split.col").length })`);
  // ★오너 지시 09-25 로 변경(TICKET=v116-auto-equalize · master 판정 D2): 창은 언제나 좌우 균등으로 다시 서므로 「아래에 새 창」 항목을 뺐다.
  //   종전 기대값 = 메뉴 2갈래 · 「아래」 → 세로 분할(col ≥ 1). 지금 = 메뉴 1갈래(오른쪽) · 누르면 창 +1 · 세로 분할 0.
  check("c4b 전문가 칸 「창 만들기」 → 오른쪽 한 갈래(「아래」 0) · 누르면 창 +1 · 세로 분할 0", b.btn && b.items?.length === 1 && !b.items.some((x: string) => x.includes("아래")) && n1.panes === n0 + 1 && n1.col === 0, JSON.stringify({ ...b, n0, ...n1 }));
  // c4c 는 hq5 장면을 쓴다 — 저장 배치(localStorage)가 뒤 칸(c5~)으로 새지 않게 c4b 가 남긴 상태를 통째로 떠 두었다가 되돌린다.
  const lsBefore = await ev(`JSON.stringify(Object.fromEntries(Object.keys(localStorage).map(k => [k, localStorage.getItem(k)])))`);
  // 누르면 = 단축키와 같은 결과: + New ≡ ⌘T · Split → ≡ ⌘D · Split ↓ ≡ ⌘⇧D. 장면 = c18i 와 같은 hq5 · 대상 = 워커 4
  //   (세로 분할이 실제로 서는 자리 — "two" 장면의 master 대상은 ⌘⇧D 도 세로 분할을 만들지 않는다 · 배치 v2 동작).
  //   판정 = 창 +1 · 세로 분할 수 증가(Split → 0 · Split ↓ +1) · 단추 결과의 배치 모양이 단축키 결과와 같다.
  const SHAPE = `(() => { const r = document.getElementById("root").getBoundingClientRect(); return { panes: document.querySelectorAll("#root .pane").length, col: document.querySelectorAll("#root .split.col").length, box: [...document.querySelectorAll("#root .pane")].map(p => { const b = p.getBoundingClientRect(); return [p.dataset.sid, +((b.left - r.left) / r.width).toFixed(2), +((b.top - r.top) / r.height).toFixed(2), +(b.width / r.width).toFixed(2), +(b.height / r.height).toFixed(2)].join(":"); }).sort() }; })()`;
  const via = async (how: string) => {
    await load("hq5", `localStorage.removeItem("cys-layout-v2")`); // 칸마다 같은 출발 — 앞 부름의 저장 배치 0
    const s0 = await ev(SHAPE);
    await ev(`document.querySelector('#root .pane[data-sid="4"]').dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
    await ev(how); await Bun.sleep(700);
    return { s0, s1: await ev(SHAPE) };
  };
  const btn = (id: string) => `document.getElementById(${JSON.stringify(id)}).click()`;
  const kd = (k: string, shift = false) => `window.dispatchEvent(new KeyboardEvent("keydown", { key: ${JSON.stringify(k)}, metaKey: true, shiftKey: ${shift}, bubbles: true, cancelable: true }))`;
  const rows: any[] = [];
  let okAll = true;
  for (const [id, keyExpr, dCol] of [["btn-new", kd("t"), 0], ["btn-split-h", kd("d"), 0], ["btn-split-v", kd("D", true), 1]] as const) {
    const b = await via(btn(id));
    const k = await via(keyExpr);
    // 새 창 번호는 부를 때마다 달라질 수 있으므로 모양 비교는 번호를 뗀 좌표 목록으로 한다
    const strip = (xs: string[]) => xs.map((x) => x.split(":").slice(1).join(":")).sort().join(",");
    const ok = b.s1.panes === b.s0.panes + 1 && b.s1.col === b.s0.col + dCol && strip(b.s1.box) === strip(k.s1.box);
    if (!ok) okAll = false;
    rows.push({ id, panes: `${b.s0.panes}→${b.s1.panes}`, col: `${b.s0.col}→${b.s1.col}`, sameAsKey: strip(b.s1.box) === strip(k.s1.box) });
  }
  await shot("c4c-after-split-v.png");
  check("c4c 상단 + New ≡ ⌘T · Split → ≡ ⌘D · Split ↓ ≡ ⌘⇧D(워커 4) — 창 +1 · 세로 분할 +0/+0/+1 · 배치 모양 = 단축키 결과", okAll, JSON.stringify(rows));
  await cdp("Page.navigate", { url: `http://127.0.0.1:${server.port}/blank-origin` }); await Bun.sleep(150);
  await ev(`localStorage.clear(); for (const [k, v] of Object.entries(${lsBefore})) localStorage.setItem(k, v);`);
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
  // (v116-exited-banner) 좌석 종료 배너 「[surface exited]」 가 화면 **맨 아래**(내용 뒤)에 뜨는가 — 박사님 09-24 「중간에 나온다」.
  //   좌석 화면 4상태를 만든 뒤 종료(__shimExit) → 보이는 행(DOM 렌더러 .xterm-rows)에서 배너 행 · 그 아래 내용 · 배너 행 글자 판독.
  //   ⒜ 주 화면 · 커서가 입력 상자 안(아래에 테두리·안내 줄이 남음 = Ink 인라인 화면 흉내)  ⒝ 대체 화면(1049h) · 커서 중간 · 1049l 없이 종료
  //   ⒞ 평범한 셸 끝줄(대조 — 커서가 이미 맨 아래)  ⒟ 대체 화면 진입·이탈(1049h→1049l) 뒤 종료(복귀 커서 = 진입 전 자리)
//   ⒠ 스크롤 영역(DECSTBM 5~20)·원점 모드(DECOM)가 남은 채 종료 · 영역 밖 맨 아래 줄에 상태 줄
//   ⒡ 스크롤백 뒤 화면 지우기 → 짧은 화면(커서 2행 · 아래 안내 줄) — 배너가 내용 바로 뒤(맨 밑으로 튀지 않음)
//   붙음 = 배너 바로 위 빈 줄 ≤ 1(⒟ 처럼 커서 줄이 빈 채 끝나면 1줄)
  //   합격 = 배너 행이 존재 · 배너 아래 빈 줄뿐 · 배너 행 글자 = 「[surface exited]」 그대로(남의 글자 위에 덮어쓰지 않음) · ⒜ 는 스크롤백 맨 위(앞 8행 안) 「fill 0」 보존.
  const enc = `((s) => btoa(String.fromCharCode(...new TextEncoder().encode(s))))`;
  const fill = `Array.from({ length: 80 }, (_, i) => "fill " + i).join("\\r\\n") + "\\r\\n"`;
  const STATES: Record<string, string> = {
    a: `${fill} + "╭──────────────╮\\r\\n│ ❯ 입력       │\\r\\n╰──────────────╯\\r\\n  ? for shortcuts\\r\\n  ctx 12% · opus" + "\\x1b[3A\\x1b[5G"`,
    b: `${fill} + "\\x1b[?1049h\\x1b[H\\x1b[2J" + Array.from({ length: 30 }, (_, i) => "tui " + i).join("\\r\\n") + "\\x1b[12;5H"`,
    c: `${fill} + "user@mac ~ % "`,
    // b2 대체 화면이 마지막 행까지 참(60줄 → 화면 44행 전부 · 커서 중간) — opus 적대 1R MINOR-1: 손실은 맨 윗줄 1줄까지만
    b2: `${fill} + "\\x1b[?1049h\\x1b[H\\x1b[2J" + Array.from({ length: 60 }, (_, i) => "tui " + i).join("\\r\\n") + "\\x1b[12;5H"`,
    // b3 대체 화면 · 마지막 행만 빔(43줄 = 0~42행) · 커서 중간 — opus 2R MINOR-3: 손실 0
    b3: `${fill} + "\\x1b[?1049h\\x1b[H\\x1b[2J" + Array.from({ length: 43 }, (_, i) => "tui " + i).join("\\r\\n") + "\\x1b[12;5H"`,
    // b4 대체 화면 · 내용 10줄 · 커서는 빈 마지막 행에 둔 채 종료 — agy 2R: 손실 0 · 배너가 내용 바로 뒤
    b4: `${fill} + "\\x1b[?1049h\\x1b[H\\x1b[2J" + Array.from({ length: 10 }, (_, i) => "tui " + i).join("\\r\\n") + "\\x1b[999;1H"`,
    // ⒠ 죽은 앱이 스크롤 영역(5~20행)·원점 모드(DECOM)를 남긴 채 커서를 영역 안에 두고 종료 · 맨 아래 줄(영역 밖)에 상태 줄
    e: `${fill} + "\\x1b[999;1HSTATUS LINE" + "\\x1b[5;20r\\x1b[?6h\\x1b[3;1H"`,
    // ⒡ 스크롤백이 쌓인 뒤 화면 지우기(2J) → 짧은 화면 · 커서 2행 · 아래 안내 줄(판독이 스크롤백 기준선 baseY 를 더해야 맞는 줄을 읽는다)
    f: `${fill} + "\\x1b[2J\\x1b[Hshort 1\\r\\nshort 2\\r\\n\\r\\n  footer" + "\\x1b[2;1H"`,
    // 대조군(조건 하나만 바꿈): a0 = ⒜ 에서 커서 되올림(\x1b[3A) 만 뺌 · b0 = ⒝ 에서 커서 중간 이동(\x1b[12;5H) 만 뺌
    a0: `${fill} + "╭──────────────╮\\r\\n│ ❯ 입력       │\\r\\n╰──────────────╯\\r\\n  ? for shortcuts\\r\\n  ctx 12% · opus"`,
    b0: `${fill} + "\\x1b[?1049h\\x1b[H\\x1b[2J" + Array.from({ length: 30 }, (_, i) => "tui " + i).join("\\r\\n")`,
    d: `"\\x1b[?1049h\\x1b[H\\x1b[2J" + Array.from({ length: 30 }, (_, i) => "tui " + i).join("\\r\\n") + "\\x1b[?1049l"`,
  };
  const ROWS = `[...${PANE("worker")}.querySelector(".xterm-rows").children].map(d => d.textContent.replace(/\\u00a0/g, " ").trimEnd())`;
  for (const w of [1280, 800]) {
    await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: 820, deviceScaleFactor: 1, mobile: false });
    for (const st of ["a", "b", "b2", "b3", "b4", "c", "d", "e", "f", "a0", "b0"]) {
      await load("two");
      await ev(`window.__shimEmit("out-2", ${enc}(${STATES[st]}))`); await Bun.sleep(300);
      await ev(`window.__shimExit(2, false)`); await Bun.sleep(700);
      const rows = (await ev(ROWS)) as string[];
      const at = rows.findIndex((r) => r.includes("[surface exited]"));
      const below = at < 0 ? [] : rows.slice(at + 1).filter((r) => r.trim() !== "");
      await shot(`c17${st}-${w}.png`);
      let top = "";
      if (st === "a") { await ev(`${PANE("worker")}.querySelector(".xterm-viewport").scrollTop = 0`); await Bun.sleep(400); top = ((await ev(ROWS)) as string[]).slice(0, 8).find((r) => r.startsWith("fill ")) ?? ""; }
      // 덮어쓰기 0 = 종료 전 화면 글자가 한 줄도 사라지지 않음(⒜ 입력 상자 아래 테두리 · ⒝ tui 0~29 전부)
      const must = st.startsWith("a") ? ["╰──────────────╯", "? for shortcuts", "ctx 12% · opus"] : st === "b2" ? Array.from({ length: 43 }, (_, i) => `tui ${60 - 43 + i}`) : st === "b3" ? Array.from({ length: 43 }, (_, i) => `tui ${i}`) : st === "b4" ? Array.from({ length: 10 }, (_, i) => `tui ${i}`) : st.startsWith("b") ? Array.from({ length: 30 }, (_, i) => `tui ${i}`) : st === "e" ? ["STATUS LINE"] : st === "f" ? ["short 1", "short 2", "footer"] : [];
      const lost = must.filter((m) => !rows.some((r) => r.trim() === m.trim()));
      let gap = 0; for (let y = at - 1; y >= 0 && rows[y].trim() === ""; y--) gap++;
      const ok = at >= 0 && gap <= 1 && below.length === 0 && rows[at].trim() === "[surface exited]" && lost.length === 0 && (st !== "a" || top.startsWith("fill 0"));
      check(`c17${st}@${w} 종료 배너 = 내용 맨 아래(붙음) · 덮어쓰기 0${st === "a" ? " · 스크롤백 보존" : ""}`, ok, JSON.stringify({ rows: rows.length, bannerRow: at, gap, bannerLine: at >= 0 ? rows[at] : null, below: below.slice(0, 4), belowN: below.length, lost, ...(st === "a" ? { top } : {}) }));
    }
  }
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
}

// (v116-integ-3 병합) 1091 restart-toast 의 c17·c17x·c17w — 1088 exited-banner 도 「c17」 을 썼다(두 가지가 같은 번호를 따로 씀).
//   두 판정 이름은 겹치지 않는다(1088 = c17a@1280 처럼 폭 붙음 · 1091 = c17a…c17x 폭 없음) → 블록 열쇠 「c17」 를 둘이 같이 쓴다.
//   순서 = 1088 먼저(자기 가지처럼 c16 바로 뒤 · 기본 UA) → 1091(맥 UA 를 세우고 되돌리지 않음 · 자기 load 로 새로 시작) → c18.
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
  // (15:4x 부하 load 28 에서 400ms 고정 대기로 쏜 이벤트가 리스너 등록 전에 유실 → 거짓 적색 1회) — 리스너 등록을 기다려 쏘고,
  //   그때 복원이 아직 판번을 기다리는 중이었는지(지연 6초 안)를 함께 단언해 공허 통과를 막는다.
  await ev(`sessionStorage.setItem("__shimAppVersionDelayMs", "6000")`);
  const t0 = Date.now();
  await cdp("Page.reload", {});
  for (let i = 0; i < 100 && !(await ev(`!!window.__shimHasListener && window.__shimHasListener("update-restart-required")`)); i++) await Bun.sleep(50);
  const emittedAt = Date.now() - t0;
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.8", reason: "app_replaced" })`);
  await Bun.sleep(Math.max(0, 6000 - emittedAt) + 1500);
  const l1 = await ev(`({ tip: document.getElementById("btn-update").title, ...${X} })`);
  await ev(`sessionStorage.removeItem("__shimAppVersionDelayMs")`);
  check("c17l 복원 대기 중 새 교체 완료(1.1.8) → 대기 판번 = 1.1.8 유지(복원 1.1.7 이 덮지 않음)", emittedAt < 5000 && l1.label === "다시 켜기" && /1\.1\.8/.test(l1.tip) && !/1\.1\.7/.test(l1.tip), JSON.stringify({ emittedAt, ...l1 }));
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
  // r. (master 판정 ⑵ · 곁 ①) 설치(다운로드·교체) 진행 중 이중 설치 — ⑴ 진행 중 헤더 재클릭 ⑵ 첫 확인 전 두 번 눌러 쌓인 확인 창 둘 다 「설치」
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }`);
  await ev(`window.__shimInstallDelayMs = 4000; document.getElementById("btn-update").click()`); await Bun.sleep(600);
  await ev(`document.querySelector(".modal-yes")?.click()`); await Bun.sleep(300);
  await ev(`document.getElementById("btn-update").click()`); await Bun.sleep(600);
  const r1 = await ev(`({ busyToast: [...document.querySelectorAll("#toasts .toast .toast-name")].some(t => t.textContent === "새 앱 받는 중"), ...${X} })`);
  if (r1.modal) { await ev(`document.querySelector(".modal-yes")?.click()`); await Bun.sleep(300); } // 기준선: 두 번째 설치 확인 창 → 승낙
  const r2 = await ev(X);
  await Bun.sleep(4000);
  await load("two", "", `window.__shimUpdate = { version: "1.1.7", notes: "" }`);
  await ev(`window.__shimInstallDelayMs = 4000; window.__shimCheckDelayMs = 400; const b = document.getElementById("btn-update"); b.click(); b.click();`); await Bun.sleep(1000);
  const r3n = await ev(`document.querySelectorAll(".modal-overlay").length`);
  await ev(`(() => { for (let i = 0; i < 3; i++) document.querySelector(".modal-overlay .modal-yes")?.click(); })()`); await Bun.sleep(300);
  await ev(`document.querySelector(".modal-overlay .modal-yes")?.click()`); await Bun.sleep(300);
  const r3 = await ev(X);
  check("c17r 설치 진행 중 이중 설치 0 — 진행 중 재클릭 = 확인 창 0·안내 1 · 쌓인 확인 창 둘 다 「설치」 = install_update 1", r1.modal === null && r1.busyToast && r2.installs === 1 && r3.installs === 1, JSON.stringify({ r1, r2, modalsBefore: r3n, r3 }));
  await Bun.sleep(4000);
  // q. 좁은 창 — 단추 글자가 「업데이트」(4자)보다 긴 「다시 켜기」(5자)가 돼도 상단바 넘침·줄바꿈 0 · 단추가 화면 안
  await cdp("Emulation.setDeviceMetricsOverride", { width: 800, height: 820, deviceScaleFactor: 1, mobile: false });
  await load("two", "");
  const Q = `(() => { const bar = document.getElementById("topbar"); const b = document.getElementById("btn-update"); const c = document.getElementById("btn-close"); const r = b.getBoundingClientRect();
    return { label: (b.firstChild?.nodeValue ?? "").trim(), barOverflow: bar.scrollWidth - bar.clientWidth, barH: Math.round(bar.getBoundingClientRect().height), scrollX: getComputedStyle(bar).overflowX, h: Math.round(r.height), hRef: Math.round(c.getBoundingClientRect().height), inView: r.left >= 0 && r.right <= window.innerWidth, pageOverflow: document.documentElement.scrollWidth - window.innerWidth,
      reach: (() => { const keep = bar.scrollLeft; b.scrollIntoView({ block: "nearest", inline: "nearest" }); const q = b.getBoundingClientRect(); const ok = q.left >= 0 && q.right <= window.innerWidth && document.documentElement.scrollWidth - window.innerWidth <= 0; bar.scrollLeft = keep; return ok; })() }; })()`;
  const q0 = await ev(Q);
  await ev(`window.__shimEmit("update-restart-required", { version: "1.1.7", reason: "app_replaced" })`); await Bun.sleep(300);
  const q1 = await ev(Q);
  await shot("c17q-w800-restart.png");
  // 상단바 설계(style.css #topbar · D4 #2) = 한 줄 고정 · 좁으면 접지 않고 가로로 밀어 본다(끝 단추까지 누를 수 있다).
  //   800폭은 수리 전부터 넘친다(기준 +50px) — 「다시 켜기」는 글자 하나만큼 더 민다(증가분은 기록만 · 판정 = 설계 계약).
  //   (첫 판 단언 「넘침 증가 0」은 이 설계와 어긋나 교정했다 — 14:5x 실측 +4px.)
  //   ★(v116-recut-newsplit · 박사님 09-25 23:2x) 상단 + New · Split → · Split ↓ 되살림으로 800폭 넘침 50 → 284px — 「업데이트」·
  //   「다시 켜기」 단추가 스크롤 전 화면 밖이 된다(1.1.5 800폭 = 넘침 216px · 업데이트 보임). 종전 단언 「스크롤 없이 화면 안(inView)」 →
  //   설계 계약 「상단바를 밀면 닿는다(reach)」 로 되돌림 · inView 값은 기록에 남긴다(📌 master 결정 사안 · HANDOFF §26).
  console.log(`     c17q 상단바 가로 넘침: 평소 ${q0.barOverflow}px → 다시 켜기 ${q1.barOverflow}px (증가 ${q1.barOverflow - q0.barOverflow}px)`);
  check("c17q w800 「다시 켜기」 = 단추 한 줄(높이 = 이웃 단추) · 상단바 높이 불변(줄바꿈 0) · 가로 스크롤 유지 · 상단바를 밀면 단추 화면 안 · 페이지 가로 넘침 0", q1.label === "다시 켜기" && q1.h === q1.hRef && q1.barH === q0.barH && q1.scrollX === "auto" && q1.reach && q1.pageOverflow <= 0, JSON.stringify({ q0, q1 }));
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

if (ONLY.includes("c18")) {
  // (v116-exited-banner 정밀 디버깅 경계) 모두 「⒜ 입력 상자 + 커서 되올림」 끝 화면을 기본으로 경계 조건 하나씩 더한다.
  //   g 스크롤백 가득(6000줄 > scrollback 5000) · h 종료 직전 대량 출력(200청크 × 약 10KB, 종료와 같은 틱) · i 필터 carry(끝에 미완 `ESC[?100`)
  //   j 창 크기 바뀐 직후 종료(fit 60ms 디바운스 전) · k 사용자가 위로 스크롤해 둔 채 종료(바닥으로 내려 판독) · l 마지막 열 줄넘김 대기(열 수만큼 X)
  //   n 아주 좁은 창(420폭) · m 종료 이벤트 2회(보이는 배너 1개)
  const enc = `((s) => btoa(String.fromCharCode(...new TextEncoder().encode(s))))`;
  const FOOT = `"╭──────────────╮\\r\\n│ ❯ 입력       │\\r\\n╰──────────────╯\\r\\n  ? for shortcuts\\r\\n  ctx 12% · opus" + "\\x1b[3A\\x1b[5G"`;
  const ROWS = `[...${PANE("worker")}.querySelector(".xterm-rows").children].map(d => d.textContent.replace(/\\u00a0/g, " ").trimEnd())`;
  const emitLines = (n: number, per = 500) => `(() => { for (let k = 0; k < ${n}; k += ${per}) window.__shimEmit("out-2", btoa(Array.from({ length: Math.min(${per}, ${n} - k) }, (_, i) => "L" + (k + i) + " " + "x".repeat(20)).join("\\r\\n") + "\\r\\n")); })()`;
  const judge = async (name: string, extra: (rows: string[]) => Record<string, unknown> = () => ({}), bannersExpected = 1) => {
    const rows = (await ev(ROWS)) as string[];
    const at = rows.findIndex((r) => r.includes("[surface exited]"));
    const n = rows.filter((r) => r.includes("[surface exited]")).length;
    const below = at < 0 ? [] : rows.slice(at + 1).filter((r) => r.trim() !== "");
    const lost = ["╰──────────────╯", "? for shortcuts", "ctx 12% · opus"].filter((m) => !rows.some((r) => r.trim() === m));
    const garbage = rows.filter((r) => /\?100|\[\?|\x1b/.test(r));
    const x = extra(rows);
    const ok = at >= 0 && n === bannersExpected && below.length === 0 && lost.length === 0 && garbage.length === 0 && Object.values(x).every((v) => v !== false);
    await shot(`c18${name}.png`);
    check(`c18${name} 경계 — 배너 맨 아래 · ${bannersExpected}회 · 덮어쓰기 0 · 잔여 글자 0`, ok, JSON.stringify({ at, n, below: below.slice(0, 3), lost, garbage: garbage.slice(0, 2), ...x }));
  };
  const exitWorker = `window.__shimExit(2, false)`;
  // g 스크롤백 가득
  await load("two");
  await ev(emitLines(6000)); await ev(`window.__shimEmit("out-2", ${enc}(${FOOT}))`); await Bun.sleep(600);
  await ev(exitWorker); await Bun.sleep(800);
  await judge("g-scrollback-full");
  // h 종료 직전 대량 출력 — 출력과 종료를 같은 평가(같은 틱)에서
  await load("two");
  await ev(`${emitLines(40000, 400)}; window.__shimEmit("out-2", ${enc}(${FOOT})); ${exitWorker}`); await Bun.sleep(4000);
  await judge("h-burst-then-exit");
  // i 필터 carry — 스트림 끝이 미완 DECSET 후보
  await load("two");
  await ev(`window.__shimEmit("out-2", ${enc}(${FOOT} + "\\x1b[?100"))`); await Bun.sleep(300);
  await ev(exitWorker); await Bun.sleep(800);
  await judge("i-carry-flush");
  // j 창 크기 바뀐 직후 종료
  await load("two");
  await ev(emitLines(120)); await ev(`window.__shimEmit("out-2", ${enc}(${FOOT}))`); await Bun.sleep(300);
  await cdp("Emulation.setDeviceMetricsOverride", { width: 900, height: 600, deviceScaleFactor: 1, mobile: false });
  await ev(exitWorker); await Bun.sleep(1200);
  await judge("j-resize-then-exit");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
  // k 위로 스크롤해 둔 채 종료 → 바닥으로 내려 판독
  await load("two");
  await ev(emitLines(300)); await ev(`window.__shimEmit("out-2", ${enc}(${FOOT}))`); await Bun.sleep(300);
  await ev(`${PANE("worker")}.querySelector(".xterm-viewport").scrollTop = 0`); await Bun.sleep(300);
  await ev(exitWorker); await Bun.sleep(800);
  const topAfter = ((await ev(ROWS)) as string[])[0];
  await ev(`(() => { const v = ${PANE("worker")}.querySelector(".xterm-viewport"); v.scrollTop = v.scrollHeight; })()`); await Bun.sleep(400);
  await judge("k-scrolled-up", () => ({ topAfter }));
  // l 마지막 열 줄넘김 대기 — 열 수만큼 X 를 쓴 뒤 커서 되올림 없이(대기 상태) 종료
  await load("two");
  const cols = await ev(`(window.__shimCalls.filter(c => c.cmd === "resize_surface" && c.args.surfaceId === 2).at(-1)?.args.cols ?? 120)`);
  await ev(`window.__shimEmit("out-2", ${enc}(${FOOT} + "\\x1b[3B\\r\\n" + "X".repeat(${cols})))`); await Bun.sleep(300);
  await ev(exitWorker); await Bun.sleep(800);
  await judge("l-pending-wrap", (rows) => ({ cols, xLineIntact: rows.some((r) => r === "X".repeat(Number(cols))) }));
  // n 아주 좁은 창 — 열이 10 안팎이라 모든 줄이 접힌다 → 행 단위가 아니라 공백 뺀 이어 붙인 글로 판독
  await cdp("Emulation.setDeviceMetricsOverride", { width: 420, height: 820, deviceScaleFactor: 1, mobile: false });
  await load("two");
  await ev(`window.__shimEmit("out-2", ${enc}(${FOOT}))`); await Bun.sleep(300);
  await ev(exitWorker); await Bun.sleep(800);
  {
    const joined = ((await ev(ROWS)) as string[]).join("").replace(/\s+/g, "");
    const keep = ["╰──────────────╯", "?forshortcuts", "ctx12%·opus"].filter((m) => !joined.includes(m));
    await shot("c18n-narrow-420.png");
    check("c18n-narrow-420 경계 — 모든 줄이 접히는 좁은 창: 배너가 글 끝 · 1회 · 덮어쓰기 0", joined.endsWith("[surfaceexited]") && joined.split("[surfaceexited]").length === 2 && keep.length === 0, JSON.stringify({ tail: joined.slice(-60), lost: keep }));
  }
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
  // m 종료 이벤트 2회(실경로에서는 스트림당 1회 — Rust 가 1회만 보냄 · 방어 관측) — 이 모양(짧은 화면 · 같은 틱)에서는 두 콜백이
  //   같은 화면을 읽어 같은 자리에 같은 글을 쓴다 ⇒ 보이는 배너 1개. ⚠조건부(opus 2R): 대상이 맨 아래 근처(스크롤 발생)거나 두 번째가
  //   첫 배너 해석 뒤에 오면 2개가 **내용 아래에** 잇달아 선다. 합격 = 이 모양에서 1개 · 내용 아래.
  await load("two");
  await ev(`window.__shimEmit("out-2", ${enc}(${FOOT}))`); await Bun.sleep(300);
  await ev(`${exitWorker}; window.__shimEmit("exit-2", null)`); await Bun.sleep(800);
  await judge("m-exit-twice");
}

// (v116-integ-3 병합 ③) 1102 auto-equalize 의 c18 — 1088 exited-banner 도 「c18」 을 썼다(두 가지가 같은 번호를 따로 씀 · c17 과 같은 처리).
//   판정 이름: 1088 = c18g-scrollback-full·c18h-burst-then-exit·c18i-carry-flush…c18n-narrow-420(꼬리 붙음) · 1102 = c18a…c18i(공백 뒤 설명)
//   → 앞머리가 겹치는 이름(c18g·c18h·c18i)은 판정 줄 전문으로 가른다. 순서 = 1088 먼저 → 1102(자기 load 로 새로 시작 · 창 크기 스스로 복원).
if (ONLY.includes("c18")) {
  // 좌석별 화면 몫(가로·세로 = #root 대비) — divider 1px · 창 머리 때문에 ±0.01 허용.
  const G = `(() => { const r = document.getElementById("root").getBoundingClientRect(); const o = {}; document.querySelectorAll("#root .pane[data-sid]").forEach(p => { const b = p.getBoundingClientRect(); o[p.dataset.sid] = { w: +(b.width / r.width).toFixed(4), h: +(b.height / r.height).toFixed(4) }; }); return { o, col: document.querySelectorAll("#root .split.col").length }; })()`;
  const near = (a: number, b: number, t = 0.012) => Math.abs(a - b) <= t;
  const even = (o: any, ids: number[]) => ids.every((i) => o[i] && near(o[i].w, o[ids[0]].w));
  const ids = (o: any) => Object.keys(o).map(Number).sort((a, b) => a - b);
  const tick = () => Bun.sleep(3800);
  const view = (x: any) => JSON.stringify(Object.fromEntries(Object.entries(x.o).map(([k, v]: any) => [k, `${v.w}×${v.h}`])));
  // (박사님 결정 09-25 14:5x · master#73a7390d) 좌열 기본 폭 = 창의 25% · 노트북이면 글자 90칸 · 상한 50%. 기대값 D 는 이 창(1280)에서
  //   실제로 선 좌열 폭이고, 그 D 가 규칙에 맞는지는 master 창의 실제 터미널 열 수(shim resize_surface)로 따로 잰다.
  const mcols = async () => (await ev(`(window.__shimCalls.filter(c => c.cmd === "resize_surface" && c.args.surfaceId === 1).at(-1)?.args.cols ?? 0)`)) as number;
  // (master#94526717) 실제 열 ≥ 90 — 상한 50%에 걸린 좁은 창만 예외(그 창은 90칸을 못 채운다) · 90칸 몫이면 90~91칸(반올림 나머지 한 칸 이내).
  const defRule = (w: number, cols: number) => (near(w, 0.25) && cols >= 90) || (near(w, 0.5) && cols <= 92) || (w > 0.25 + 0.012 && w < 0.5 - 0.012 && cols >= 90 && cols <= 91);
  await load("hq5");
  const D = ((await ev(G)) as any).o[1].w as number;
  const Dcols = await mcols();
  check("c18D 1280폭 기본 좌열 폭 D = 규칙(25% · 90칸 · 상한 50%)에 맞음 — master 창 실제 열 수로 대조", defRule(D, Dcols), `D=${D} cols=${Dcols}`);

  // a — 본부+워커1 → 워커 입양(종전 R1: 새 워커 0.50 · master 0.20 · cso 0.05)
  await load("three");
  const a0 = await ev(G);
  await ev(`window.__shimAddSeat(4, "worker", "/Users/user/jarvis/w2")`); await tick();
  const a1 = await ev(G);
  await shot("c18a-adopt.png");
  check("c18a 본부+워커1 → 워커 입양: 워커 2칸 같은 폭 · 좌열 기본 폭 D 그대로(워커 수와 무관) · master:cso 세로 4:1 유지",
    near(a0.o[1].w, D) && even(a1.o, [3, 4]) && near(a1.o[1].w, D) && near(a1.o[1].h / a1.o[2].h, a0.o[1].h / a0.o[2].h, 0.05) && a1.o[1].h > a1.o[2].h * 3,
    `before ${view(a0)} → after ${view(a1)}`);

  // b — 외부 닫힘(가운데 워커) → 남은 워커 같은 폭
  await load("hq5");
  const b0 = await ev(G);
  await ev(`window.__shimExit(4, true)`); await Bun.sleep(1500);
  const b1 = await ev(G);
  check("c18b 외부 닫힘(가운데 워커 4) → 남은 3·5 같은 폭 · 좌열 D 유지 · 칸 수 5→4",
    ids(b0.o).length === 5 && even(b0.o, [3, 4, 5]) && JSON.stringify(ids(b1.o)) === "[1,2,3,5]" && even(b1.o, [3, 5]) && near(b1.o[1].w, D),
    `before ${view(b0)} → after ${view(b1)}`);

  // c — ⌘W(확인 → 닫기) 경로
  await load("hq5");
  await ev(`document.querySelector('#root .pane[data-sid="3"]').dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
  await ev(key("w")); await Bun.sleep(250);
  await ev(`document.querySelector(".modal-yes")?.click()`); await Bun.sleep(500);
  const c1 = await ev(G);
  check("c18c ⌘W 로 워커 3 닫기 → 남은 4·5 같은 폭 · 좌열 D", JSON.stringify(ids(c1.o)) === "[1,2,4,5]" && even(c1.o, [4, 5]) && near(c1.o[1].w, D), view(c1));

  // d — 창 머리 × (두 번 눌러 닫기)
  await load("hq5");
  await ev(`(() => { const x = document.querySelector('#root .pane[data-sid="5"] .pane-close'); x.click(); x.click(); })()`); await Bun.sleep(500);
  const d1 = await ev(G);
  check("c18d 창 머리 × 로 워커 5 닫기 → 남은 3·4 같은 폭 · 좌열 D", JSON.stringify(ids(d1.o)) === "[1,2,3,4]" && even(d1.o, [3, 4]) && near(d1.o[1].w, D), view(d1));

  // e — 새 창(전문가 칸 「창 만들기 → 오른쪽」) = 종전 새 칸 0.50
  await load("hq5", `localStorage.setItem("cys-expert-mode", "1")`);
  const eOrd0 = await ev(`[...document.querySelectorAll("#root .pane[data-sid]")].map(p => +p.dataset.sid)`);
  await ev(`document.querySelector('#root .pane[data-sid="4"]').dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
  const eOrd1 = await ev(`[...document.querySelectorAll("#root .pane[data-sid]")].map(p => +p.dataset.sid)`);
  // (앞 칸이 남긴 저장 배치를 이어받으므로 시작 순서는 칸마다 다르다 — 기대 순서는 분할 전 순서에서 만든다.)
  void eOrd0;
  await ev(`[...document.querySelectorAll("#ws-expert button")].find(x => x.textContent.includes("창 만들기")).click()`);
  await ev(`[...document.querySelectorAll("#ctx-menu .ctx-item")][0]?.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }))`);
  await Bun.sleep(700);
  const e1 = await ev(G);
  const eNew = ids(e1.o).filter((i) => i >= 100);
  const eOrder = await ev(`[...document.querySelectorAll("#root .pane[data-sid]")].map(p => +p.dataset.sid)`);
  await shot("c18e-new-pane.png");
  check("c18e 창 만들기 → 새 창이 워커와 같은 폭 · 분할 대상(4) 바로 오른쪽 · 좌열 기본 폭 D 유지",
    eNew.length === 1 && even(e1.o, [3, 4, eNew[0], 5]) && near(e1.o[1].w, D) &&
      JSON.stringify(eOrder) === JSON.stringify((eOrd1 as number[]).flatMap((x) => (x === 4 ? [4, eNew[0]] : [x]))),
    `${view(e1)} before=${JSON.stringify(eOrd1)} order=${JSON.stringify(eOrder)}`);

  // f — 사람이 끈 좌열 0.40 · 위아래 0.65 는 열기·닫기를 지나도 그대로(D1 = C)
  const saved = { workspaces: [{ id: 1, name: "", tree: { type: "split", dir: "row", ratio: 0.4, a: { type: "split", dir: "col", ratio: 0.65, a: { type: "pane", sid: 1 }, b: { type: "pane", sid: 2 } }, b: { type: "pane", sid: 3 } } }], groups: [], active: 0, counter: 2, groupCounter: 1 };
  await load("three", `localStorage.setItem("cys-layout-v2", ${JSON.stringify(JSON.stringify(saved))})`);
  const f0 = await ev(G);
  await ev(`window.__shimAddSeat(4, "worker", "/Users/user/jarvis/w2")`); await tick();
  const f1 = await ev(G);
  await ev(`window.__shimExit(3, true)`); await Bun.sleep(1500);
  const f2 = await ev(G);
  check("c18f 사람이 끈 좌열 0.40 · 위아래 0.65 → 입양 뒤·닫기 뒤 그대로 · 워커 같은 폭",
    near(f0.o[1].w, 0.4) && near(f1.o[1].w, 0.4) && near(f2.o[1].w, 0.4) && even(f1.o, [3, 4]) && near(f1.o[1].h / (f1.o[1].h + f1.o[2].h), 0.65, 0.02) && near(f2.o[1].h / (f2.o[1].h + f2.o[2].h), 0.65, 0.02) && JSON.stringify(ids(f2.o)) === "[1,2,4]",
    `${view(f0)} → ${view(f1)} → ${view(f2)}`);

  // g — 본부 없는 기기(우리 개발 기기 모양): 전부 한 줄 균등 · 세로 분할 0
  await load("w3");
  const g0 = await ev(G);
  await ev(`window.__shimAddSeat(6, "worker", "/Users/user/jarvis/w4")`); await tick();
  const g1 = await ev(G);
  await ev(`window.__shimExit(4, true)`); await Bun.sleep(1500);
  const g2 = await ev(G);
  await shot("c18g-workers-only.png");
  check("c18g 워커만 3 → 입양 4칸 1/4 → 가운데 닫기 3칸 1/3 · 세로 분할 0",
    even(g0.o, [3, 4, 5]) && near(g0.o[3].w, 1 / 3) && even(g1.o, [3, 4, 5, 6]) && near(g1.o[3].w, 1 / 4) && even(g2.o, [3, 5, 6]) && near(g2.o[3].w, 1 / 3) && g0.col + g1.col + g2.col === 0,
    `${view(g0)} → ${view(g1)} → ${view(g2)}`);

  // i — (v2 · 박사님 결정 09-25 14:1x · master#88533ed8 로 변경 · v1 은 「세로 분할 0」을 단언했다)
  //   팔레트 「분할」 검색 → 가로·세로 분할 둘 다 · ⌘⇧D(워커 4) → 새 창이 4 바로 아래 · 같은 기둥 · 기둥 폭·좌열 몫 불변
  await load("hq5");
  const i0 = await ev(G);
  await ev(`window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true, cancelable: true }))`); await Bun.sleep(400);
  await ev(`(() => { const i = document.querySelector(".palette-input"); i.value = "분할"; i.dispatchEvent(new Event("input", { bubbles: true })); })()`); await Bun.sleep(300);
  const pal = await ev(`[...document.querySelectorAll(".palette-item .pi-title")].map(x => x.textContent)`);
  await shot("c18i-palette.png");
  await ev(`window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }))`); await Bun.sleep(200);
  await ev(`document.querySelector('#root .pane[data-sid="4"]').dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
  await ev(`window.dispatchEvent(new KeyboardEvent("keydown", { key: "D", metaKey: true, shiftKey: true, bubbles: true, cancelable: true }))`); await Bun.sleep(700);
  const i1 = await ev(G);
  const iNew = ids(i1.o).filter((x) => x >= 100);
  await shot("c18i-cmd-shift-d.png");
  check("c18i 팔레트 「분할」 → 가로·세로 분할 둘 다 · ⌘⇧D(워커 4) → 새 창이 4 아래 반 · 같은 기둥 폭 · 기둥 3개 폭 불변 · 좌열 D · 4:1",
    Array.isArray(pal) && pal.includes("가로 분할") && pal.includes("세로 분할") && iNew.length === 1 && i1.col === 2 &&
      near(i1.o[iNew[0]].w, i1.o[4].w) && near(i1.o[4].h, 0.5, 0.02) && near(i1.o[iNew[0]].h, 0.5, 0.02) &&
      even(i1.o, [3, 4, 5]) && near(i1.o[4].w, i0.o[4].w) && near(i1.o[1].w, D) && i1.o[1].h > i1.o[2].h * 3,
    `palette=${JSON.stringify(pal)} ${view(i0)} → ${view(i1)} col=${i1.col}`);

  // v — (v2) 사람이 세로로 나눈 기둥(4 위 · 새 창 아래)이 입양·닫기를 지나도 그대로 · 좌열 4:1 · 기둥끼리만 균등 · 팔레트 세로 분할 실행
  await ev(`window.__shimAddSeat(6, "worker", "/Users/user/jarvis/w4")`); await tick();
  const v1 = await ev(G);
  await ev(`window.__shimExit(3, true)`); await Bun.sleep(1500);
  const v2 = await ev(G);
  await ev(`document.querySelector('#root .pane[data-sid="5"]').dispatchEvent(new MouseEvent("mousedown", { bubbles: true }))`);
  await ev(`window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true, cancelable: true }))`); await Bun.sleep(400);
  await ev(`(() => { const i = document.querySelector(".palette-input"); i.value = "세로 분할"; i.dispatchEvent(new Event("input", { bubbles: true })); })()`); await Bun.sleep(300);
  await ev(`[...document.querySelectorAll(".palette-item")].find(r => r.querySelector(".pi-title").textContent === "세로 분할").dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }))`); await Bun.sleep(700);
  const v3 = await ev(G);
  const vNew = ids(v3.o).filter((x) => x >= 100 && x !== iNew[0]);
  await ev(`window.__shimExit(${iNew[0]}, true)`); await Bun.sleep(1500);
  const v4 = await ev(G);
  await shot("c18v-vertical-kept.png");
  const pil = (o: any, a: number, b: number) => near(o[a].w, o[b].w) && near(o[a].h, 0.5, 0.02) && near(o[b].h, 0.5, 0.02);
  const hq = (o: any, share: number) => near(o[1].w, share) && near(o[1].h / (o[1].h + o[2].h), 0.8, 0.02);
  check("c18v 사람 세로 기둥(4/새 창) → 입양(6) 뒤 그대로 · 기둥 4개 균등 → 워커 3 닫기 뒤 그대로 · 3기둥 균등 → 팔레트 세로 분할(5) → 5 아래 · 폭 불변 → 새 창 닫기 → 4 가 기둥 전체 · 좌열 4:1 내내",
    pil(v1.o, 4, iNew[0]) && even(v1.o, [3, 4, 5, 6]) && near(v1.o[3].w, (1 - D) / 4) && hq(v1.o, D) && v1.col === 2 &&
      JSON.stringify(ids(v2.o)) === JSON.stringify([1, 2, 4, 5, 6, iNew[0]].sort((a, b) => a - b)) && pil(v2.o, 4, iNew[0]) && even(v2.o, [4, 5, 6]) && hq(v2.o, D) && v2.col === 2 &&
      vNew.length === 1 && pil(v3.o, 5, vNew[0]) && pil(v3.o, 4, iNew[0]) && even(v3.o, [4, 5, 6]) && near(v3.o[5].w, v2.o[5].w) && hq(v3.o, D) && v3.col === 3 &&
      near(v4.o[4].h, 1, 0.02) && pil(v4.o, 5, vNew[0]) && even(v4.o, [4, 5, 6]) && hq(v4.o, D) && v4.col === 2,
    `${view(v1)} col=${v1.col} → ${view(v2)} col=${v2.col} → ${view(v3)} col=${v3.col} → ${view(v4)} col=${v4.col}`);

  // h — (박사님 결정 14:5x · master#73a7390d) 창 폭별 기본 좌열 폭: 넓은 모니터 3440 = 25% · 1920·1280 = 90칸 또는 상한 · 800 = 상한 50%
  const hw: Record<number, number> = {};
  for (const width of [3440, 1920, 800]) {
    await cdp("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: false });
    await load("hq5");
    await ev(`window.__shimAddSeat(6, "worker", "/Users/user/jarvis/w4")`); await tick();
    const h1 = await ev(G);
    const hc = await mcols();
    hw[width] = h1.o[1].w;
    if (width === 800) await shot("c18h-w800.png");
    if (width === 3440) await shot("c18h-w3440.png");
    check(`c18h ${width}폭 · 본부+워커 4 → 워커 같은 폭 · 좌열 기본 폭 규칙(25% · 실제 열 ≥ 90 · 상한 50%)`,
      even(h1.o, [3, 4, 5, 6]) && defRule(h1.o[1].w, hc) && (width !== 3440 || near(h1.o[1].w, 0.25)) && (width !== 800 || near(h1.o[1].w, 0.5)) && (width !== 1920 || hc >= 90), `${view(h1)} cols=${hc}`);
  }
  // w — 창 크기가 바뀌면 기본 폭 사용자(표지)는 다시 잰다(3440 → 800 → 3440) · 사람이 끈 0.40 은 그대로
  await cdp("Emulation.setDeviceMetricsOverride", { width: 3440, height: 900, deviceScaleFactor: 1, mobile: false });
  await load("hq5");
  const w0 = await ev(G);
  await cdp("Emulation.setDeviceMetricsOverride", { width: 800, height: 900, deviceScaleFactor: 1, mobile: false }); await Bun.sleep(900);
  const w1 = await ev(G);
  await cdp("Emulation.setDeviceMetricsOverride", { width: 3440, height: 900, deviceScaleFactor: 1, mobile: false }); await Bun.sleep(900);
  const w2 = await ev(G);
  const human = { workspaces: [{ id: 1, name: "", tree: { type: "split", dir: "row", ratio: 0.4, a: { type: "split", dir: "col", ratio: 0.65, a: { type: "pane", sid: 1 }, b: { type: "pane", sid: 2 } }, b: { type: "pane", sid: 3 } } }], groups: [], active: 0, counter: 2, groupCounter: 1 };
  await load("three", `localStorage.setItem("cys-layout-v2", ${JSON.stringify(JSON.stringify(human))})`);
  await cdp("Emulation.setDeviceMetricsOverride", { width: 800, height: 900, deviceScaleFactor: 1, mobile: false }); await Bun.sleep(900);
  const w3 = await ev(G);
  check("c18w 창 크기 변경: 기본 폭 3440(25%) → 800(50%) → 3440(25%) 다시 잼 · 사람이 끈 0.40 은 800 에서도 그대로",
    near(w0.o[1].w, 0.25) && near(w1.o[1].w, 0.5) && near(w2.o[1].w, 0.25) && near(w3.o[1].w, 0.4) && even(w1.o, [3, 4, 5]),
    `${view(w0)} → ${view(w1)} → ${view(w2)} · human ${view(w3)}`);
  // o — 1.1.5 이하 옛 기본 폭 1/3 저장 배치(표지 없음) → 다음 입양 때 새 기본 폭으로(master#73a7390d) · 위아래 0.65 는 그대로
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
  const old13 = { workspaces: [{ id: 1, name: "", tree: { type: "split", dir: "row", ratio: 1 / 3, a: { type: "split", dir: "col", ratio: 0.65, a: { type: "pane", sid: 1 }, b: { type: "pane", sid: 2 } }, b: { type: "pane", sid: 3 } } }], groups: [], active: 0, counter: 2, groupCounter: 1 };
  // 1.1.5 에서 올라온 사용자 = 옛 배치는 있고 이동 플래그는 없다(같은 헤드리스 프로필의 앞 장면이 플래그를 세웠으므로 지운다).
  await load("three", `localStorage.setItem("cys-layout-v2", ${JSON.stringify(JSON.stringify(old13))}); localStorage.removeItem("cys-left-default-migrated")`);
  const o0 = await ev(G);
  await ev(`window.__shimAddSeat(4, "worker", "/Users/user/jarvis/w2")`); await tick();
  const o1 = await ev(G);
  check("c18o 옛 기본 폭 1/3(1.1.5 저장) → 입양 뒤 새 기본 폭 D · master:cso 0.65 그대로",
    near(o0.o[1].w, 1 / 3) && near(o1.o[1].w, D) && near(o1.o[1].h / (o1.o[1].h + o1.o[2].h), 0.65, 0.02) && even(o1.o, [3, 4]),
    `${view(o0)} → ${view(o1)}`);
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
}

if (logs.length) console.log("page exceptions:\n  " + logs.slice(0, 5).join("\n  "));
console.log(fails.length ? `FAIL (${fails.length}): ${fails.join(" · ")}` : "ALL PASS");
cleanup();
process.exit(fails.length ? 1 : 0);
