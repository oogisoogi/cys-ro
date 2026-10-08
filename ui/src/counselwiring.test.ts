// 상담소·아고라 메뉴 **배선** 회귀 핀(TICKET=cysr-119-t4-app) — 소스를 데이터로 읽어 계약을 단언한다
// (wswiring·feedbackwiring 관례: 런타임 코드 0줄 · DOM/Tauri 불요).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { AGORA_COPY, COUNSEL_COPY } from "./counsel";

const read = (rel: string): string => readFileSync(new URL(rel, import.meta.url), "utf-8");
const main = read("./main.ts");
const html = read("../index.html");
const css = read("./style.css");
const counselSrc = read("./counsel.ts");

/** `function name(` 부터 짝이 맞는 닫는 중괄호까지. */
function fnBody(src: string, header: string): string {
  const at = src.indexOf(header);
  if (at < 0) throw new Error(`없음: ${header}`);
  let depth = 0;
  for (let i = src.indexOf("{", at); i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) return src.slice(at, i + 1);
  }
  throw new Error(`닫힘 없음: ${header}`);
}

describe("상담소 메뉴 자리·라벨", () => {
  it("사이드바 줄은 목록(#ws-tabs) 아래 · 사용량 패널(#ws-usage) 위에 있다", () => {
    const tabs = html.indexOf('<div id="ws-tabs">');
    const row = html.indexOf('<div id="ws-counsel-row">');
    const usage = html.indexOf('<div id="ws-usage"');
    expect(tabs).toBeGreaterThan(0);
    expect(row).toBeGreaterThan(tabs);
    expect(usage).toBeGreaterThan(row);
  });
  it("단추 글자·툴팁 = counsel.ts 문구 정본과 같다", () => {
    expect(html).toContain(`<button id="btn-counsel" title="${COUNSEL_COPY.tooltip}">${COUNSEL_COPY.label} <span id="counsel-badge" class="badge" hidden>0</span></button>`);
  });
  it("공개 문구는 제품명 cysr 만 쓴다(단독 cys 낱말 0) · 위협 표현 0", () => {
    const all = [...Object.values(COUNSEL_COPY), ...Object.values(AGORA_COPY)].join("\n");
    expect(/\bcys\b/.test(all)).toBe(false);
    for (const bad of ["경고", "위험", "금지", "차단", "삭제됩니다", "책임"]) expect(all.includes(bad)).toBe(false);
  });
  it("메뉴 줄 CSS 는 목록이 남는 공간을 갖게 flex:none 이다", () => {
    expect(css).toMatch(/#ws-counsel-row \{\s*flex: none;/);
  });
});

describe("상담소 창 — 남의 글자는 textContent 로만", () => {
  const panel = fnBody(main, "function openCounselPanel(");
  const item = fnBody(main, "function counselItemEl(");
  const post = fnBody(main, "function counselPostEl(");
  const load = fnBody(main, "async function loadCounselList(");
  it("틀(innerHTML)은 openCounselPanel 한 곳 · 고정 문자열뿐(보간 0)", () => {
    const tpl = panel.slice(panel.indexOf("ov.innerHTML ="), panel.indexOf(";", panel.indexOf("ov.innerHTML =")));
    expect(tpl.includes("${")).toBe(false);
    for (const f of [item, post, load]) expect(f.includes("innerHTML")).toBe(false);
    expect(counselSrc.includes("innerHTML =")).toBe(false);
  });
  it("글쓴이·본문·시각은 textContent 로 넣는다", () => {
    expect(item).toContain("who.textContent = it.from;");
    expect(item).toContain("text.textContent = it.text;");
    expect(item).toContain("when.textContent = fmtWhen(it.ts);");
  });
  it("글 목록은 Rust counsel_room_list 하나에서만 온다(앱이 릴레이 주소를 부르지 않는다)", () => {
    expect(load).toContain('invoke("counsel_room_list")');
    expect(main.includes("agora.godmeyou.kr/rooms")).toBe(false);
    expect(/fetch\(\s*["'`]https:\/\/agora/.test(main)).toBe(false);
  });
  it("단추 배선", () => {
    expect(main).toContain('document.getElementById("btn-counsel")!.addEventListener("click", () => openCounselPanel());');
  });
});

describe("상담소 뱃지 배선(§11 — 읽기만 · 판독 = parseUnread)", () => {
  const poll = fnBody(main, "async function pollCounselUnread(");
  const render = fnBody(main, "function renderCounselBadge(");
  it("unread.json 은 Rust counsel_unread 로 읽고 상태 전이는 stepUnread 하나(판정 끝난 수정 시각만 기억)", () => {
    expect(poll).toContain('invoke("counsel_unread")');
    expect(poll).toContain("const next = stepUnread(counselUnreadCache, res);");
    expect(poll).toContain("if (next === counselUnreadCache) return;");
  });
  it("숫자는 textContent 로 · 0 이면 숨김", () => {
    expect(render).toContain("b.hidden = t === null;");
    expect(render).toContain("b.textContent = t ?? \"0\";");
  });
  it("주기 = UNREAD_POLL_MS(45초 · §11 30~60초 안)", () => {
    expect(main).toContain("setInterval(() => void pollCounselUnread(), UNREAD_POLL_MS);");
  });
  it("앱은 읽음 처리를 하지 않는다(master 판정 Q1) — ack·read 쓰기 명령 0", () => {
    expect(/invoke\("counsel_(ack|seen|mark|read)/.test(main)).toBe(false);
    expect(main.includes("mail_ack")).toBe(false);
  });
});

describe("아고라 메뉴 배선", () => {
  it("단추 글자·툴팁 = AGORA_COPY · 상담소 단추 바로 뒤", () => {
    expect(html).toContain(`</button><button id="btn-agora" title="${AGORA_COPY.tooltip}">${AGORA_COPY.label}</button></div>`);
  });
  it("단추는 Rust open_agora_window 만 부른다(UI 가 주소를 열지 않는다)", () => {
    expect(main).toContain('void invoke("open_agora_window").catch(');
    expect(main.includes('open_url", { url: "https://agora')).toBe(false);
  });
});
