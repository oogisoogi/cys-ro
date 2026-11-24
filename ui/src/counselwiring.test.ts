// 「자동 보고」 배선 회귀 핀 — 소스를 데이터로 읽어 계약을 단언한다(wswiring·feedbackwiring 관례: 런타임 코드 0줄 · DOM/Tauri 불요).
// ★(1.1.19 · TICKET=cysr-1119-s10b · DESIGN §8-3 AG4·AG5·AG5n) 「상담소」 창·45초 배지·「아고라」 단추·30분 반복 확인은 화면에서 뺐다 —
//   남은 것 = 화면 설정 「자동 보고」 한 줄 · 첫 안내 창 · 안내 확인 계기(D-11) · 안내문 끝 문장(§8-3-1 정본).
//   옛 핀(상담소 창 textContent · 글 목록 counsel_room_list · 배지 counsel_unread · 아고라 open_agora_window)은 「없음」 단언으로 바꿨다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { AUTO_COPY, REPORT_NOTICE } from "./counsel";

const read = (rel: string): string => readFileSync(new URL(rel, import.meta.url), "utf-8");
const main = read("./main.ts");
const html = read("../index.html");
const css = read("./style.css");
const counselSrc = read("./counsel.ts");
const topbar = read("./topbarlayout.ts");
const tauriMain = read("../../src-tauri/src/main.rs");
const counselRs = read("../../src-tauri/src/counsel.rs");

/** 주석 줄(// · /* · *)을 걷은 코드 — 설명문 속 옛 낱말이 「없음」 단언을 속이지 않게(거꾸로도). */
const code = (s: string): string =>
  s
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n")
    .filter((l) => !/^\s*(\/\/|\*|<!--)/.test(l))
    .map((l) => l.replace(/\s\/\/.*$/, ""))
    .join("\n");
const htmlCode = html.replace(/<!--[\s\S]*?-->/g, "");

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

const NOTICE_TAIL = "끄려면 화면 설정 → ‘자동 보고’를 끄세요.";

describe("AG4 · AG5 — 상담소·아고라 화면 0(단추·창·배지·명령)", () => {
  it("상단바·사이드바에 상담소·아고라 단추·배지 0 · CSS 규칙 0", () => {
    for (const id of ["btn-counsel", "btn-agora", "counsel-badge", "ws-counsel-row"]) expect({ id, 있음: htmlCode.includes(id) }).toEqual({ id, 있음: false });
    const c = css.replace(/\/\*[\s\S]*?\*\//g, "");
    expect(/#btn-(counsel|agora)\b/.test(c)).toBe(false);
  });
  it("main.ts 에 상담소 창·배지·아고라 배선 0(원천 grep · 주석 제외)", () => {
    const m = code(main);
    for (const bad of ["btn-counsel", "btn-agora", "openCounselPanel", "pollCounselUnread", "counsel_room_list", "counsel_unread", "open_agora_window", "AGORA_COPY", "COUNSEL_COPY", "UNREAD_POLL_MS", "REPORT_NOTICE_POLL_MS"])
      expect({ bad, 있음: m.includes(bad) }).toEqual({ bad, 있음: false });
  });
  it("45초·30분 반복 타이머 0 — 안내 확인을 setInterval 로 돌리지 않는다", () => {
    const m = code(main);
    expect(/setInterval\([^;]{0,80}(maybeShowReportNotice|pollCounsel)/.test(m)).toBe(false);
  });
  it("D-13 — Rust 명령 counsel_room_list·counsel_unread·open_agora_window 가 이름표(generate_handler!)와 counsel.rs 에서 사라졌다", () => {
    for (const n of ["counsel_room_list", "counsel_unread", "open_agora_window"]) {
      expect({ n, 이름표: code(tauriMain).includes(`counsel::${n}`) }).toEqual({ n, 이름표: false });
      expect({ n, 정의: counselRs.includes(`fn ${n}(`) }).toEqual({ n, 정의: false });
    }
    // 남는 명령 셋 = 자동 보고 상태·켜기/끄기·안내 봤음
    for (const n of ["counsel_auto_status", "counsel_auto_set", "counsel_notice_seen"]) expect(tauriMain).toContain(`counsel::${n},`);
  });
  it("저장 배치에 상담소·아고라 id 가 남은 기기도 단추가 보이지 않는다 — 단추 목록은 html 에서 읽고, 상단 단추 파서는 없는 id 를 버린다", () => {
    expect(main).toContain('const TOPBAR_DOM_IDS: readonly string[] = [...topbarEl.querySelectorAll<HTMLButtonElement>(":scope > button[id]")].map((b) => b.id);');
    expect(topbar).toContain("if (seen.has(id) || !domIds.includes(id)) continue;");
  });
});

describe("AG5 — 「자동 보고」 켜기/끄기 = 화면 설정 한 줄", () => {
  const row = fnBody(main, "function screenSettingsAutoRow(");
  const load = fnBody(main, "async function loadReportAutoRow(");
  it("자리 = S9 틀의 screenSettingsAutoRow(전문가 구획 앞 최상위 한 줄) · 줄을 만들 때 상태를 1회 읽는다(화면 설정 열 때만)", () => {
    expect(row).toContain('row.className = "theme-pop-row sp-auto-row";');
    expect(row).toContain("void loadReportAutoRow(row, state, btn);");
    expect(row.includes("return null;")).toBe(false);
    expect(main).toContain("pop.append(look.sec, bar.sec, ...(autoRow ? [autoRow] : []), expert.sec, all.sec);");
  });
  it("상태 = counsel_auto_status · 바꾸기 = counsel_auto_set 하나(앱이 설정 파일을 직접 쓰지 않는다 · 1.1.18 set_auto 그대로)", () => {
    expect(load).toContain('res = next === undefined ? await invoke("counsel_auto_status") : await invoke("counsel_auto_set", { on: next });');
    expect(load).toContain("state.textContent = autoLine(st.auto);");
    expect(load).toContain("const t = autoToggle(st.auto);");
    expect(load).toContain("btn.onclick = () => void loadReportAutoRow(row, state, btn, t.next);");
    expect(/localStorage|writeFile|config\.json/.test(load)).toBe(false);
  });
  it("켜기 실패 = 1.1.18 글 notTurnedOn · 안내문(개인정보) = 줄 툴팁(꺼짐이면 「다시 켜려면」)", () => {
    expect(load).toContain('if (next === true && st.auto !== true) state.textContent += " " + AUTO_COPY.notTurnedOn;');
    expect(load).toContain("row.title = autoNotice(st.auto);");
    expect(AUTO_COPY.notTurnedOn).toBe("지금은 켜지 못했어요. 잠시 뒤 다시 눌러 주세요.");
  });
});

describe("AG5 · D-11 — 첫 안내 창과 안내 확인 계기(반복 타이머 0)", () => {
  const notice = fnBody(main, "async function maybeShowReportNotice(");
  const load = fnBody(main, "async function loadReportAutoRow(");
  it("첫 안내 = 팩이 원할 때만(needs_notice) · 문구 그대로 · 「자동 보고 끄기」 · 끈 게 확인된 뒤에만 「봤음」 표식", () => {
    expect(notice).toContain('st = parseAutoStatus(await invoke("counsel_auto_status"));');
    expect(notice).toContain("if (!st.needsNotice) return;");
    expect(notice).toContain("confirmModal(AUTO_COPY.noticeTitle, REPORT_NOTICE, AUTO_COPY.turnOff, AUTO_COPY.ok)");
    const off = notice.indexOf('invoke("counsel_auto_set", { on: false })');
    const seen = notice.indexOf('invoke("counsel_notice_seen")');
    expect(off).toBeGreaterThan(0);
    expect(seen).toBeGreaterThan(off);
    expect(notice).toContain("parseAutoStatus(res).auto !== false");
  });
  it("계기 ① 앱이 뜬 뒤 5초 1회(D-04 · 지우지 않음)", () => {
    expect(main).toContain("const REPORT_NOTICE_FIRST_MS = 5_000;");
    expect(main).toContain("setTimeout(() => void maybeShowReportNotice(), REPORT_NOTICE_FIRST_MS);");
  });
  it("계기 ② 화면 설정을 열 때 — 자동 보고 줄이 읽은 상태를 그대로 넘긴다(두 번 묻지 않음)", () => {
    expect(load).toContain("if (next === undefined) void maybeShowReportNotice(st);");
  });
  it("계기 ③ 대화 화면·작업 화면 첫 진입마다 1회 — 화면마다 실행당 한 번(집합) · 대화 = #view-host 가 처음 보일 때 · 작업 = onWorkShown", () => {
    const entry = fnBody(main, "function noteViewEntryForReportNotice(");
    expect(entry).toContain("if (reportNoticeViewsSeen.has(view)) return;");
    expect(entry).toContain("void maybeShowReportNotice();");
    expect(main).toContain('noteViewEntryForReportNotice("chat");');
    // (TICKET=cysr-1119-integ1 · S10b×S12 풀이) 작업 화면 진입 = S12 보기 칸 닫기 먼저 + S10b 안내 계기 — 두 조각 한 줄
    expect(main).toContain('onWorkShown: () => { closePeek("leave"); retryFailedRuntimes(); render(); noteViewEntryForReportNotice("work"); },');
    expect(main).toContain('mo.observe(viewHost, { attributes: true, attributeFilter: ["hidden"] });');
  });
});

describe("AG5n — 안내문 끝 문장 정본(DESIGN §8-3-1) · 단추 이름 = 자동 보고", () => {
  const pack = read("../../cysjavis-pack/bin/javis_counsel.py");
  it("안내문 = 팩 HELP_NOTICE 와 글자 그대로 · 끝 문장 = 정본 바이트", () => {
    const m = pack.match(/HELP_NOTICE = \(((?:\s*"[^"]*")+)\s*\)/);
    expect(m).not.toBeNull();
    const parts = [...m![1].matchAll(/"([^"]*)"/g)].map((x) => x[1]);
    expect(parts.length).toBeGreaterThan(1);
    expect(REPORT_NOTICE).toBe(parts.join(""));
    // (cysr-1119-s10b AG5n) 끝 문장 = DESIGN §8-3-1 정본 문자열 바이트 그대로(팩 HELP_NOTICE·모듈 설명과 같은 바이트 = 팩 시험) · 단추 이름 = 자동 보고.
    expect(REPORT_NOTICE.endsWith(NOTICE_TAIL)).toBe(true);
    expect(REPORT_NOTICE.includes("상담소")).toBe(false);
    expect([AUTO_COPY.noticeTitle, AUTO_COPY.turnOff, AUTO_COPY.turnOn]).toEqual(["자동 보고 안내", "자동 보고 끄기", "자동 보고 켜기"]);
    expect(AUTO_COPY.offNotice).toBe("지금은 보내지 않습니다. 다시 켜려면 화면 설정 → ‘자동 보고’를 켜세요.");
  });
  it("원천 grep — 화면 글(counsel.ts 문자열·index.html 보이는 글)에 「상담소」 0 · 주석·옛 판 이행 설명은 제외(주석을 걷고 잰다)", () => {
    const strs = [...code(counselSrc).matchAll(/"([^"]*)"/g)].map((x) => x[1]).join("\n");
    expect(strs.includes("상담소")).toBe(false);
    expect(htmlCode.includes("상담소")).toBe(false);
  });
  it("공개 문구 규칙(cysr · 위협 표현 0)", () => {
    const all = Object.values(AUTO_COPY).join("\n");
    expect(/\bcys\b/.test(all + REPORT_NOTICE)).toBe(false);
    for (const bad of ["경고", "위험", "금지", "차단", "삭제됩니다", "책임"]) expect(all.includes(bad)).toBe(false);
  });
});
