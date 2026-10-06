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
    // 정본 = docs/index.html 의 동적 조회 정규식(v1.1.7 실 자산명 각 1건 일치 실측) — 여기 사본이 페이지 소스에 그대로 있어야 한다.
    const ASSET_RES = [/^cysr-macos-arm64-v[0-9.]+\.zip$/, /^cysr-macos-x64-v[0-9.]+\.zip$/, /^cysr_[0-9.]+_x64-setup\.exe$/, /^cysr_[0-9.]+_x64-setup\.zip$/];
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
});
