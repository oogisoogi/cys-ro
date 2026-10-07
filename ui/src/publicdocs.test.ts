// 공개 문서 현행성 게이트(1.1.8 U4 2판 · codex 1R ④ · master#f69113b1).
//
// 1.1.8 부터 앱에는 「업데이트」 단추·배지·인앱 설치가 없다(설계 AUTO-UPDATE-118 §5-1) — 새 판은 데몬이 쉬는 시간에 받고(자동 갱신)
// 앱은 결과 1줄만 알린다. 공개 문서(README 한/영 · USER-MANUAL · 다운로드 페이지 · 설치 상세 · 아키텍처)는 **현행만** 적는다: 지운 단추·명령·노브를
// 지금 기능처럼 안내하면 사용자가 없는 단추를 찾는다. 옛 경로 서술을 「버전 기록」 으로 남기는 것도 하지 않는다(문서 = 현행).
import { describe, it, expect } from "bun:test";
import { existsSync, readFileSync } from "node:fs";

// 4판(Fable 3R MAJOR-1 · MINOR-1 · master#741101b5): 화이트리스트가 아니라 **README(한/영)가 링크하는 모든 .md 를 자동 수집**한다 —
// 새 공개 문서가 README 에 링크되면 그대로 검사 대상이 된다(2판 4종 → 3판 6종 → 손으로 넓히다 SECURITY.md 를 놓친 꼴 재발 방지).
// 다운로드 페이지(docs/index.html)는 README 가 .md 로 링크하지 않으므로 명시로 더한다.
// 6판(codex 최종 MINOR-1 · master#43ab7cee): 수집기가 인라인 `[x](y)` 단순형만 봤다 → 폴더 링크 `docs/`(그 안 README.md) ·
// 참조식 `[x][d]` + `[d]: y` · HTML `<a href>` · 제목 달린 링크 `[x](y "t")` · 괄호 든 파일명 · `<y>` 꺾쇠형까지 모은다(아래 시험이 반례 5종을 잰다).
const ROOT = new URL("../../", import.meta.url);
/** 문서 하나의 링크 대상 중 저장소 안 .md 를 모은다(순수 — `exists` 로 폴더 README 판정). 반환 = 저장소 뿌리 기준 경로. */
export const collectMdLinks = (text: string, exists: (rootRel: string) => boolean): string[] => {
  const raw: string[] = [];
  // 인라인: ](대상 "제목"?) — 대상 = <꺾쇠> 또는 공백 없는 문자열(괄호 한 겹 허용)
  for (const m of text.matchAll(/\]\(\s*(<[^>\n]+>|(?:[^()\s]|\([^()\s]*\))+)(?:\s+(?:"[^"]*"|'[^']*'|\([^)]*\)))?\s*\)/g)) raw.push(m[1]);
  // 참조 정의: [이름]: 대상 "제목"?
  for (const m of text.matchAll(/^ {0,3}\[[^\]\n]+\]:\s*(<[^>\n]+>|\S+)/gm)) raw.push(m[1]);
  // HTML 앵커
  for (const m of text.matchAll(/<a\s[^>]*?href\s*=\s*["']([^"']+)["']/gi)) raw.push(m[1]);
  const out = new Set<string>();
  for (let t of raw) {
    t = t.replace(/^<|>$/g, "").split("#")[0].split("?")[0];
    if (!t || /^[a-z][a-z0-9+.-]*:/i.test(t) || t.startsWith("//")) continue;
    try {
      t = decodeURI(t);
    } catch {
      continue;
    }
    const rel = new URL(t.replace(/ /g, "%20"), ROOT).href.slice(ROOT.href.length).replace(/%20/g, " "); // URL 해석 = ./ · ../ 정규화
    if (rel.endsWith(".md")) out.add(rel);
    else if (rel === "" || rel.endsWith("/") || !/\.[A-Za-z0-9]+$/.test(rel)) {
      const idx = `${rel.replace(/\/?$/, rel === "" ? "" : "/")}README.md`;
      if (exists(idx)) out.add(idx);
    }
  }
  return [...out];
};
const linkedDocs = (): string[] => {
  const out = new Set<string>(["README.md", "README.en.md"]);
  for (const r of ["README.md", "README.en.md"]) {
    for (const p of collectMdLinks(readFileSync(new URL(r, ROOT), "utf-8"), (q) => existsSync(new URL(q, ROOT)))) out.add(p);
  }
  return [...out].sort();
};
const DOCS = [...linkedDocs().map((p) => `../../${p}`), "../../docs/index.html"];
const read = (rel: string): string => readFileSync(new URL(rel, import.meta.url), "utf-8");

/** 실 릴리스 자산 정규식 4개 — 정본 = docs/index.html 의 동적 조회 정규식(v1.1.7 실 자산명 각 1건 일치 실측 · 아래 시험이 페이지 소스에 같은 정규식이 있음을 단언).
 *  순서 = 다운로드 버튼 dl-mac-arm · dl-mac-x64 · dl-win · dl-win-zip. */
const ASSET_RES = [/^cysr-macos-arm64-v[0-9.]+\.zip$/, /^cysr-macos-x64-v[0-9.]+\.zip$/, /^cysr_[0-9.]+_x64-setup\.exe$/, /^cysr_[0-9.]+_x64-setup\.zip$/];
const DL_IDS = ["dl-mac-arm", "dl-mac-x64", "dl-win", "dl-win-zip"];

/** 7판(codex 재서명 MAJOR-1 · master#1f4bc905): 실 배포 꼴 = 자체서명 ZIP(cysr.app 하나) · 윈 cysr_<판>_x64-setup.exe · 공증 주장 0 · 설치 도우미 0
 *  (근거 = scripts/release-verify.py MAC_ASSETS 주석 · scripts/build-macos-local.sh 자체서명·ditto zip). 공개 문서 전건에서 아래가 0 이어야 한다. */
const STALE_INSTALL = [
  { name: ".dmg", re: /\.dmg\b/gi },
  { name: "DMG", re: /\bDMG\b/g },
  { name: "cys_<판>(옛 윈 이름)", re: /\bcys_(?:[0-9]|<)/g },
  { name: "공증", re: /공증/g },
  { name: "notariz", re: /notariz/gi },
  { name: "Install cys.app", re: /Install cys\.app/g },
  { name: "도우미", re: /도우미/g },
  // publish-docs-118(master#d93a6088 브리프 §2-4): www 만이 아니라 원작자 홈페이지·연락처 주소 전부(cysinsight.com · cysinsight@…)
  { name: "cysinsight(원작자 홈페이지·연락처)", re: /cysinsight/gi },
];

/** 지운 것들의 이름 — 앱 명령 · 환경 노브 · 기록 파일 · 단추/배지 id · 앱의 옛 서명 경로. */
const GONE = [
  "check_update",
  "install_update",
  "check_pack_update",
  "install_pack_update",
  "restart_after_update",
  "update_attempt_report",
  "smart_app_control",
  "update_checked_launch_enabled",
  "autotest_patch_install",
  "CYS_UPDATE_VERIFY",
  "CYS_UPDATE_CHECKED_LAUNCH",
  "CYS_AUTOTEST_PATCH_INSTALL",
  "CYS_UPDATE_MANIFEST_URL",
  ".update-attempt.json",
  "btn-update",
  "update-badge",
  "Tauri updater",
];

// ⑨ 공식 명칭 게이트(publish-docs-118 · master#c33d2ec7 → 2판 #0885ae7a ③ · codex 1R MAJOR 5·6 / agy 1R MAJOR 3·4).
// 박사님 10-07 「우리 자비스 공식명칭은 cysr이다. 이 외 다른 명칭은 쓰지 않는다. 모든 문서를 통일한다.」
//  ① 대상 = **명시 매니페스트**(발행 표면) — README 링크 수집에 기대지 않는다(링크 밖 dist-win·1.x 노트·앱 화면이 빠졌던 구멍). README 가 새 문서를
//     링크하면 아래 「매니페스트 ⊇ README 링크」 시험이 붉어져 등재를 강제한다.
//  ② 크레딧 = **파일별 정확한 문장만** 허용(줄 통째 예외 금지 — 같은 줄 다른 자리의 오변환을 놓쳤다) · 등재된 문장이 실제로 없으면 붉다(묵은 허용 금지).
//  ③ 홑따옴표 꼴 = **승인 토큰만** 코드 꼴로 친다(화면 문자열이 파일 이름 'cys' 를 그대로 옮긴 자리 · 파일 패턴).
export const NAME_MANIFEST = [
  "README.md", "README.en.md", "SECURITY.md", "CONTRIBUTING.md", "NOTICE.md", "USER-MANUAL.md", "ARCHITECTURE-AND-PHILOSOPHY.md",
  "docs/INSTALL.md", "docs/INSTALL-Windows-KR.md", "docs/GUIDE-clean-reset-KR.md", "docs/GUIDE-empty-surface-KR.md",
  "docs/GUIDE-fullauto-cycle-KR.md", "docs/GUIDE-policy-json-KR.md", "docs/RELEASE.md", "dist-win/README.md",
  "docs/RELEASE_NOTES_1.0.0.md", "docs/RELEASE_NOTES_1.0.1.md", "docs/RELEASE_NOTES_1.0.2.md", "docs/index.html", "ui/index.html",
];
const CREDIT_KO_RN = "cys 터미널의 원작자는 CYSJavis(GitHub: idoforgod)입니다. 이 배포본은 원작자의 허락을 받아 oogisoogi가 원작(MIT)을 바탕으로 빌드·서명·배포하는 파생판입니다. 원작 저장소: https://github.com/idoforgod/cys-terminal";
const CREDIT_README = "cysr 는 cys 터미널(github.com/idoforgod/cys-terminal)에서 출발했습니다.";
export const NAME_CREDITS: Record<string, string[]> = {
  "README.md": [CREDIT_README],
  "README.en.md": ["cysr started from the cys terminal (github.com/idoforgod/cys-terminal).", CREDIT_README],
  "NOTICE.md": ["cys-terminal is licensed under the MIT License (see `LICENSE`).", "cysr is a derivative of cys-terminal (Copyright (c) 2026 CYSJavis); see LICENSE."],
  "docs/RELEASE_NOTES_1.0.0.md": [CREDIT_KO_RN],
  "docs/RELEASE_NOTES_1.0.1.md": [CREDIT_KO_RN],
  "docs/RELEASE_NOTES_1.0.2.md": [CREDIT_KO_RN],
  // 앱 화면 출발지 표기 = 박사님 09-27 「도의상 cys가 출발지였다는 내용만 표시」(brandbadge.test · test_default_fleet_formation ⓕ 5자리 결박) — README 문장 그대로 + 짧은 꼬리표
  "ui/index.html": [`title="${CREDIT_README}">cys 터미널에서 출발`],
};
export const NAME_QUOTED_OK = ["'cys'", "'cys-dept-*'"];
/** 순수 판정 — 크레딧(정확한 문장)을 지운 뒤 CYSJavis 개수 · 코드 꼴 밖 낱말 cys 가 있는 줄 · 등재됐지만 없는 크레딧. */
export const nameViolations = (text: string, isHtml: boolean, credits: string[]) => {
  let t = text;
  if (isHtml) {
    const keepNl = (m: string) => m.replace(/[^\n]/g, "");
    t = t.replace(/<!--[\s\S]*?-->/g, keepNl).replace(/<(script|style)\b[\s\S]*?<\/\1>/gi, keepNl).replace(/<code>[\s\S]*?<\/code>/gi, keepNl); // <code> = HTML 의 코드 꼴
  }
  const unusedCredits = credits.filter((c) => !t.includes(c));
  for (const c of credits) t = t.split(c).join("");
  if (isHtml) {
    // 태그는 지우되 사람이 보는 속성 값(title·alt·aria-label·placeholder·content)은 남긴다(툴팁도 화면 문자열이다)
    t = t.replace(/<[^>]*>/g, (tag) => [...tag.matchAll(/\b(?:title|alt|aria-label|placeholder|content)\s*=\s*"([^"]*)"/gi)].map((m) => ` ${m[1]} `).join(""));
  }
  const cysjavis = (t.match(/CYSJavis/g) ?? []).length;
  const lines: number[] = [];
  let fence = false;
  t.split("\n").forEach((line, i) => {
    if (/^\s*(?:>\s*)*(```|~~~)/.test(line)) {
      fence = !fence;
      return;
    }
    if (fence) return;
    let prose = line.replace(/``[^`]*``|`[^`\n]*`/g, "");
    for (const q of NAME_QUOTED_OK) prose = prose.split(q).join("");
    prose = prose.replace(/\]\([^)]*\)/g, "](").replace(/https?:\/\/\S+/g, "");
    if (!isHtml) prose = prose.replace(/<[^>\n]*>/g, "");
    if (/\bcys\b/.test(prose)) lines.push(i + 1);
  });
  return { cysjavis, lines, unusedCredits };
};

describe("공개 문서(README 링크 전부 + 다운로드 페이지) — 현행만(1.1.8 U4)", () => {
  it("수집이 공허하지 않다 — 알려진 공개 문서가 다 들어 있고 각 파일이 실재·비어 있지 않다", () => {
    for (const must of ["SECURITY.md", "docs/INSTALL.md", "ARCHITECTURE-AND-PHILOSOPHY.md", "USER-MANUAL.md", "docs/INSTALL-Windows-KR.md", "docs/GUIDE-clean-reset-KR.md"]) {
      expect({ must, 있음: DOCS.includes(`../../${must}`) }).toEqual({ must, 있음: true });
    }
    // 파일별 하한(SECURITY.md 는 1,000자 미만이 정상이라 일괄 1,000자 하한을 쓰지 않는다) — 읽기 실패(없는 링크)도 여기서 적색.
    for (const d of DOCS) expect({ d, 길이: read(d).length > 300 }).toEqual({ d, 길이: true });
  });
  it("「업데이트」·「Update」 낱말 0 — 없는 단추 이름이자 1.1.8 의 말은 「새 판 · 갱신 · 자동 갱신」", () => {
    for (const d of DOCS) {
      const s = read(d);
      expect({ d, 업데이트: s.split("업데이트").length - 1, Update: s.split("Update").length - 1 }).toEqual({ d, 업데이트: 0, Update: 0 });
    }
  });
  it("지운 앱 명령·환경 노브·기록 파일·단추 id·앱 쪽 옛 서명 경로 이름 0", () => {
    for (const d of DOCS) {
      const s = read(d);
      expect({ d, 남은: GONE.filter((g) => s.includes(g)) }).toEqual({ d, 남은: [] });
    }
  });
  it("도움말 1줄(설계 §5-4)이 한국어 문서 셋에 그대로 있다", () => {
    const line = "새 판은 자비스가 쉬는 시간에 알아서 받아 둡니다(어댑터가 꽂혀 있거나 배터리가 절반 넘게 남았을 때).";
    for (const d of ["../../README.md", "../../USER-MANUAL.md"]) expect({ d, 있음: read(d).includes(line) }).toEqual({ d, 있음: true });
    expect(read("../../docs/index.html").includes(line)).toBe(true);
    expect(read("../../README.en.md").includes("cysr updates itself while it is idle (plugged in, or battery above half).")).toBe(true);
  });
  it("수집기 반례 5종(codex 최종 MINOR-1) — 폴더 링크·참조식·HTML·제목 달린 링크·괄호 든 파일명 · 꺾쇠형 · 외부/앵커 제외", () => {
    const md = [
      "[폴더](docs/evidence/)",
      "[참조][d]",
      "[d]: SECURITY.md \"제목\"",
      '<a href="NOTICE.md">공지</a>',
      '[제목 달린](CONTRIBUTING.md "기여 안내")',
      "[괄호](docs/notes(1).md)",
      "[꺾쇠](<docs/a b.md>)",
      "[외부](https://example.com/x.md) [앵커](#설치) [그림](docs/x.png)",
    ].join("\n");
    const got = collectMdLinks(md, (q) => q === "docs/evidence/README.md").sort();
    expect(got).toEqual(["CONTRIBUTING.md", "NOTICE.md", "SECURITY.md", "docs/a b.md", "docs/evidence/README.md", "docs/notes(1).md"]);
  });
  it("다운로드 페이지 = 우리 저장소(oogisoogi/cys-ro) 최신 릴리스 — 벤더(idoforgod · cys-terminal) 주소 0(codex 최종 MAJOR-1)", () => {
    const s = read("../../docs/index.html");
    const R = "https://github.com/oogisoogi/cys-ro/releases/download/";
    for (const id of ["dl-mac-arm", "dl-mac-x64", "dl-win", "dl-win-zip"]) {
      const href = s.match(new RegExp(`id="${id}"\\s+href="([^"]+)"`))?.[1] ?? "";
      expect({ id, 우리_릴리스: href.startsWith(R) }).toEqual({ id, 우리_릴리스: true });
    }
    expect(s.includes('fetch("https://api.github.com/repos/oogisoogi/cys-ro/releases/latest")')).toBe(true);
    expect({ 벤더: (s.match(/idoforgod|cys-terminal/gi) ?? []).length }).toEqual({ 벤더: 0 });
  });
  it("README(한/영) 설치 절 자산명 = 실 릴리스 자산 정규식(다운로드 페이지와 같은 4개 · master#315fae4c)", () => {
    const page = read("../../docs/index.html");
    for (const re of ASSET_RES) expect({ re: re.source, 페이지에_있음: page.includes(`asset(${re.toString()})`) }).toEqual({ re: re.source, 페이지에_있음: true });
    for (const d of ["../../README.md", "../../README.en.md"]) {
      const names = [...read(d).matchAll(/`(cysr?[-_][^`\s]*\.(?:dmg|zip|exe))`/g)].map((m) => m[1]);
      const asReal = (n: string) => n.replace(/<[^>]+>/g, "1.1.7");
      expect({ d, 틀린_자산명: names.filter((n) => !ASSET_RES.some((re) => re.test(asReal(n)))) }).toEqual({ d, 틀린_자산명: [] });
      // 공허 방지 — 맥 두 종·윈 설치기가 다 적혀 있다
      for (const re of ASSET_RES.slice(0, 3)) expect({ d, re: re.source, 있음: names.some((n) => re.test(asReal(n))) }).toEqual({ d, re: re.source, 있음: true });
    }
  });
  it("설치 안내 = 실 배포 꼴 — DMG·옛 윈 이름·공증·설치 도우미·원작자 내려받기 자리 0(공개 문서 전건 · codex 재서명 MAJOR-1)", () => {
    for (const d of DOCS) {
      const s = read(d);
      const hits = STALE_INSTALL.map(({ name, re }) => ({ name, n: (s.match(re) ?? []).length })).filter((h) => h.n > 0);
      expect({ d, 남은: hits }).toEqual({ d, 남은: [] });
    }
  });
  // publish-docs-118(master#d93a6088 브리프 §2-1·§2-4): 1.0.1 부터 앱 이름 = cysr.app(zip 최상위 · 설치 자리 /Applications/cysr.app).
  // 옛 이름 cys.app 은 「옛 자리 정리」 문맥에서만 — 같은 줄에 옛/old/legacy 표기가 있거나 cysr.app 과 나란히 적힌 줄만 허용한다.
  it("앱 이름 = cysr.app — 옛 이름 cys.app 은 옛 자리 문맥(같은 줄 옛·old·legacy 또는 cysr.app 병기)에서만(공개 문서 전건)", () => {
    for (const d of DOCS) {
      const bad = read(d)
        .split("\n")
        .map((line, i) => ({ line: i + 1, text: line }))
        .filter(({ text }) => /(^|[^a-z])cys\.app/.test(text) && !/cysr\.app|옛|\bold\b|legacy/i.test(text))
        .map(({ line }) => line);
      expect({ d, 현행_뜻_cys_app_줄: bad }).toEqual({ d, 현행_뜻_cys_app_줄: [] });
    }
  });
  it("원작자 저장소(idoforgod/cys-terminal) 주소 = 출처 표기 줄에서만 — 받기·복제 안내 0(공개 문서 전건)", () => {
    for (const d of DOCS) {
      const bad = read(d)
        .split("\n")
        .map((line, i) => ({ line: i + 1, text: line }))
        .filter(({ text }) => /idoforgod\/cys-terminal/i.test(text) && !/출발|started from/i.test(text))
        .map(({ line }) => line);
      expect({ d, 원작자_주소_줄: bad }).toEqual({ d, 원작자_주소_줄: [] });
    }
  });
  it("공식 명칭 = cysr — 매니페스트 전건: 「CYSJavis」 0 · 코드 꼴 밖 낱말 cys 0 · 크레딧은 파일별 정확한 문장만(⑨ 2판)", () => {
    for (const f of NAME_MANIFEST) {
      const v = nameViolations(read(`../../${f}`), f.endsWith(".html"), NAME_CREDITS[f] ?? []);
      expect({ f, ...v }).toEqual({ f, cysjavis: 0, lines: [], unusedCredits: [] });
    }
  });
  it("공식 명칭 매니페스트 ⊇ README 링크 공개 문서 · 전부 실재(새 공개 문서는 등재해야 초록)", () => {
    for (const d of DOCS) {
      const rel = d.replace(/^\.\.\/\.\.\//, "");
      expect({ rel, 등재: NAME_MANIFEST.includes(rel) }).toEqual({ rel, 등재: true });
    }
    for (const f of NAME_MANIFEST) expect({ f, 있음: existsSync(new URL(`../../${f}`, import.meta.url)) }).toEqual({ f, 있음: true });
  });
  it("공식 명칭 판정기 반례(codex 1R) — 홑따옴표로 감싼 제품명 · 「출발」 낱말이 든 줄의 다른 자리 · 크레딧 뒤 덧붙임은 적색", () => {
    expect(nameViolations("제품 이름은 'cys' 가 아니라 'cysr' 입니다 — 제품 이름은 'cys 터미널' 입니다", false, []).lines).toEqual([1]);
    expect(nameViolations("이 제품은 cys에서 출발하지만 공식 이름도 cys입니다", false, []).lines).toEqual([1]);
    expect(nameViolations(`${CREDIT_README} 그리고 cys 를 쓰세요`, false, [CREDIT_README]).lines).toEqual([1]);
    expect(nameViolations(CREDIT_README, false, [CREDIT_README])).toEqual({ cysjavis: 0, lines: [], unusedCredits: [] });
    expect(nameViolations("CYSJavis 팩", false, []).cysjavis).toBe(1);
    expect(nameViolations('<button title="cys launch-agent 로도">x</button>', true, []).lines).toEqual([1]);
    expect(nameViolations("<div>산출물 (<code>~/.cys/x</code>)</div>", true, []).lines).toEqual([]);
    expect(nameViolations("<div>산출물 (~/.cys/x)</div>", true, []).lines).toEqual([1]);
    expect(nameViolations("> ```bash\n> cys status\n> ```", false, []).lines).toEqual([]);
    expect(nameViolations("문장만", false, [CREDIT_README]).unusedCredits).toEqual([CREDIT_README]);
  });
  it("다운로드 버튼 폴백 = 표시 판의 실 자산(태그·파일명·판 결속 · codex 재서명 MINOR-1)", () => {
    const s = read("../../docs/index.html");
    const ver = s.match(/<b id="ver">(v[0-9]+(?:\.[0-9]+)+)<\/b>/)?.[1] ?? "";
    expect({ 표시_판: /^v[0-9]+(\.[0-9]+)+$/.test(ver) }).toEqual({ 표시_판: true });
    // 기대 이름 = 표시 판으로 직접 구성(완전 일치 · codex 재서명 2 MINOR — 부분문자열 판 대조는 v1.1.70 · v1.1.7. 를 통과시켰다)
    const v = ver.slice(1);
    const EXPECTED = [`cysr-macos-arm64-v${v}.zip`, `cysr-macos-x64-v${v}.zip`, `cysr_${v}_x64-setup.exe`, `cysr_${v}_x64-setup.zip`];
    DL_IDS.forEach((id, i) => {
      const href = s.match(new RegExp(`id="${id}"\\s+href="([^"]+)"`))?.[1] ?? "";
      const m = href.match(/^https:\/\/github\.com\/oogisoogi\/cys-ro\/releases\/download\/([^/]+)\/([^/]+)$/);
      const tag = m?.[1] ?? "";
      const file = m?.[2] ?? "";
      expect({ id, 태그_일치: tag === ver, 파일_정규식: ASSET_RES[i].test(file), 파일_완전_일치: file === EXPECTED[i] }).toEqual({
        id,
        태그_일치: true,
        파일_정규식: true,
        파일_완전_일치: true,
      });
    });
  });
});
