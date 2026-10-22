// 상담소·아고라 메뉴 **배선** 회귀 핀(TICKET=cysr-119-t4-app) — 소스를 데이터로 읽어 계약을 단언한다
// (wswiring·feedbackwiring 관례: 런타임 코드 0줄 · DOM/Tauri 불요).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { AGORA_COPY, AUTO_COPY, COUNSEL_COPY, REPORT_NOTICE } from "./counsel";

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

// ★(cysr-menu-top-row · 박사님 2026-10-21 「상담소, 아고라 메뉴 위치가 왼쪽 메뉴바면 애매하다. 상단 피드백과 함께 배치하자.
//   순서는 피드백 상담소 아고라 순을 제안한다.」) 종전 기대값 = 사이드바 줄(#ws-counsel-row)이 목록(#ws-tabs) 아래 · 사용량 패널 위.
//   지금 = 상단바에서 피드백 바로 뒤 상담소 → 아고라 → 정렬 · 사이드바 0(한 곳에만).
describe("상담소 메뉴 자리·라벨", () => {
  const top = html.slice(html.indexOf('<header id="topbar">'), html.indexOf("</header>"));
  it("상단바 단추 순서 = 피드백 · 상담소 · 아고라 · 정렬(맨 앞 넷)", () => {
    const ids = [...top.matchAll(/<button\b[^>]*?\bid="([^"]+)"/g)].map((m) => m[1]);
    expect(ids.slice(0, 4)).toEqual(["btn-feedback", "btn-counsel", "btn-agora", "btn-equalize"]);
  });
  it("사이드바(왼쪽 메뉴바)에는 상담소·아고라 0 · 옛 줄(#ws-counsel-row) 0 · 각 id 는 문서에 한 번", () => {
    const nav = html.slice(html.indexOf('<nav id="wsbar">'), html.indexOf("</nav>"));
    expect(nav.length).toBeGreaterThan(0);
    for (const s of ['id="btn-counsel"', 'id="btn-agora"', 'id="counsel-badge"', 'id="ws-counsel-row"', ">상담소", ">아고라<"]) expect(nav.includes(s)).toBe(false);
    for (const s of ['id="btn-counsel"', 'id="btn-agora"', 'id="counsel-badge"']) expect(html.split(s).length - 1).toBe(1);
    expect(html.includes("ws-counsel-row")).toBe(false);
  });
  it("단추 글자·툴팁 = counsel.ts 문구 정본과 같다", () => {
    expect(html).toContain(`<button id="btn-counsel" title="${COUNSEL_COPY.tooltip}">${COUNSEL_COPY.label} <span id="counsel-badge" class="badge" hidden>0</span></button>`);
  });
  it("공개 문구는 제품명 cysr 만 쓴다(단독 cys 낱말 0) · 위협 표현 0", () => {
    const all = [...Object.values(COUNSEL_COPY), ...Object.values(AGORA_COPY)].join("\n");
    expect(/\bcys\b/.test(all)).toBe(false);
    for (const bad of ["경고", "위험", "금지", "차단", "삭제됩니다", "책임"]) expect(all.includes(bad)).toBe(false);
  });
  it("옛 사이드바 줄 CSS 0 · 상단 두 단추에 자기 크기 규칙 0(글자·여백·높이 = 상단 단추 공통 #topbar button)", () => {
    const code = css.replace(/\/\*[\s\S]*?\*\//g, "");
    expect(code.includes("#ws-counsel-row")).toBe(false);
    expect(/#btn-(counsel|agora)\b/.test(code)).toBe(false);
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
    expect(html).toContain(`</span></button><button id="btn-agora" title="${AGORA_COPY.tooltip}">${AGORA_COPY.label}</button>`);
  });
  it("단추는 Rust open_agora_window 만 부른다(UI 가 주소를 열지 않는다)", () => {
    expect(main).toContain('void invoke("open_agora_window").catch(');
    expect(main.includes('open_url", { url: "https://agora')).toBe(false);
  });
});

// ★(1.1.10 · TICKET=cysr-1110-counsel-off) 안내문이 가리키는 「상담소 끄기」 단추가 앱에 없었고, 안내문도 기기 화면에 한 번도
//   안 떴다(Fable 적대 검토 2건 · cysr-1110.md ① · fleet-report F1·F2). 단추 = 상담소 창 · 안내 = 첫 전송 전 1회 창.
describe("상담소 끄기/켜기 · 첫 안내", () => {
  const pack = read("../../cysjavis-pack/bin/javis_counsel.py");
  const panel = fnBody(main, "function openCounselPanel(");
  const toggle = fnBody(main, "async function loadCounselAuto(");
  const notice = fnBody(main, "async function maybeShowReportNotice(");
  it("안내문 = 팩 HELP_NOTICE 와 글자 그대로(박사님 승인 문구 · 변경 금지) · 단추 이름이 안내문 속 이름과 같다", () => {
    const m = pack.match(/HELP_NOTICE = \("([^"]*)"\s*\n\s*"([^"]*)"\)/);
    expect(m).not.toBeNull();
    expect(REPORT_NOTICE).toBe(m![1] + m![2]);
    expect(REPORT_NOTICE).toContain(`‘${AUTO_COPY.turnOff}’`);
    expect(AUTO_COPY.turnOff).toBe("상담소 끄기");
  });
  it("공개 문구 규칙(cysr · 위협 표현 0)", () => {
    const all = Object.values(AUTO_COPY).join("\n");
    expect(/\bcys\b/.test(all + REPORT_NOTICE)).toBe(false);
    for (const bad of ["경고", "위험", "금지", "차단", "삭제됩니다", "책임"]) expect(all.includes(bad)).toBe(false);
  });
  it("상담소 창에 켜짐/꺼짐 줄과 단추 — 단추는 Rust counsel_auto_set 하나로만 바꾼다(앱이 설정 파일을 직접 쓰지 않는다)", () => {
    expect(panel).toContain('<p class="counsel-auto"><span class="counsel-auto-state"></span><button class="counsel-auto-toggle"></button></p>');
    expect(panel).toContain("void loadCounselAuto(ov);");
    expect(toggle).toContain('invoke("counsel_auto_status")');
    expect(toggle).toContain('invoke("counsel_auto_set", { on: next })');
    expect(toggle).toContain("state.textContent = autoLine(st.auto);");
  });
  it("첫 안내 = 팩이 원할 때만(needs_notice) · 문구 그대로 · 「상담소 끄기」 단추 · 끈 게 확인된 뒤에만 「봤음」 표식", () => {
    expect(notice).toContain('parseAutoStatus(await invoke("counsel_auto_status"))');
    expect(notice).toContain("if (!st.needsNotice) return;");
    expect(notice).toContain("confirmModal(AUTO_COPY.noticeTitle, REPORT_NOTICE, AUTO_COPY.turnOff, AUTO_COPY.ok)");
    const off = notice.indexOf('invoke("counsel_auto_set", { on: false })');
    const seen = notice.indexOf('invoke("counsel_notice_seen")');
    expect(off).toBeGreaterThan(0);
    expect(seen).toBeGreaterThan(off);
    expect(notice).toContain("parseAutoStatus(res).auto !== false");
  });
  it("앱이 뜬 뒤 곧 한 번 + 그 뒤 주기 확인(팩이 판 중간에 새로 깔려도 다음 확인 때 뜬다)", () => {
    expect(main).toContain("setTimeout(() => void maybeShowReportNotice(), REPORT_NOTICE_FIRST_MS);");
    expect(main).toContain("setInterval(() => void maybeShowReportNotice(), REPORT_NOTICE_POLL_MS);");
  });
});
