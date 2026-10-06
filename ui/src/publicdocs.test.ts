// 공개 문서 현행성 게이트(1.1.8 U4 2판 · codex 1R ④ · master#f69113b1).
//
// 1.1.8 부터 앱에는 「업데이트」 단추·배지·인앱 설치가 없다(설계 AUTO-UPDATE-118 §5-1) — 새 판은 데몬이 쉬는 시간에 받고(자동 갱신)
// 앱은 결과 1줄만 알린다. 공개 문서(README 한/영 · USER-MANUAL · 다운로드 페이지 · 설치 상세 · 아키텍처)는 **현행만** 적는다: 지운 단추·명령·노브를
// 지금 기능처럼 안내하면 사용자가 없는 단추를 찾는다. 옛 경로 서술을 「버전 기록」 으로 남기는 것도 하지 않는다(문서 = 현행).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

// 4판(Fable 3R MAJOR-1 · MINOR-1 · master#741101b5): 화이트리스트가 아니라 **README(한/영)가 링크하는 모든 .md 를 자동 수집**한다 —
// 새 공개 문서가 README 에 링크되면 그대로 검사 대상이 된다(2판 4종 → 3판 6종 → 손으로 넓히다 SECURITY.md 를 놓친 꼴 재발 방지).
// 다운로드 페이지(docs/index.html)는 README 가 .md 로 링크하지 않으므로 명시로 더한다.
const ROOT = new URL("../../", import.meta.url);
const linkedDocs = (): string[] => {
  const out = new Set<string>(["README.md", "README.en.md"]);
  for (const r of ["README.md", "README.en.md"]) {
    for (const m of readFileSync(new URL(r, ROOT), "utf-8").matchAll(/\]\(([^)\s]+)\)/g)) {
      const p = m[1].split("#")[0];
      if (!p || /^[a-z]+:/i.test(p) || !p.endsWith(".md")) continue;
      out.add(new URL(p, ROOT).href.slice(ROOT.href.length)); // URL 해석 = ./ · ../ 정규화
    }
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
});
