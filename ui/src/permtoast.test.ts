// permtoast.test.ts — TCC 폴더 접근 토스트 브랜드명 회귀(TICKET=v110-misc B3).
//
// 실기: perm-warning 토스트 본문이 "cys를 허용한 뒤"로 앱 명칭 개칭(cysr) 전 문구를 그대로
// 남기고 있었다(ui/src/main.ts). 개칭 뒤에도 옛 문구가 조용히 재발하지 않게 핀으로 고정한다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { PRIVACY_APP_NAME, permWarningToast } from "./folderaccess";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");

describe("TCC 폴더 접근 토스트", () => {
  it("옛 명칭 'cys를 허용한 뒤' 가 없다", () => {
    expect(main).not.toContain("cys를 허용한 뒤");
  });

  // (1.1.8 병합 X8 합성) 리스너 문구는 원작자 folderaccess.permWarningToast 로 옮겨 갔다 — 앱 이름은 PRIVACY_APP_NAME
  // 한 곳(우리 브랜드 오버레이 "cysr"). 단언 목적(토스트 본문이 개칭 뒤 이름 cysr 을 말한다)은 그 출처에서 핀한다.
  it("perm-warning 리스너가 'cysr' 을 허용 대상으로 말한다(permWarningToast · PRIVACY_APP_NAME)", () => {
    const idx = main.indexOf('listen("perm-warning"');
    expect(idx).toBeGreaterThan(-1);
    const block = main.slice(idx, main.indexOf("});", idx));
    expect(block).toContain("showPermWarning(e.payload)");
    const sp = main.indexOf("const showPermWarning = (payload: unknown): void => {");
    expect(sp).toBeGreaterThan(-1);
    expect(main.slice(sp, main.indexOf("\n  };\n", sp))).toContain("permWarningToast(((payload ?? {}) as { folder?: unknown }).folder)");
    expect(PRIVACY_APP_NAME).toBe("cysr");
    for (const folder of ["Desktop", "Documents", "Elsewhere"]) {
      const t = permWarningToast(folder);
      expect(t?.detail).toContain("「cysr」");
      expect(t?.detail).not.toContain("「cys」");
    }
  });
});

// ★v116-app-firstrun(A-3): 새 설치 첫 실행의 폴더 권한 창 — 안내가 먼저, 권한 창은 그 뒤(순서 보장).
describe("첫 실행 폴더 권한 안내(A-3)", () => {
  const start = main.indexOf('invoke("folder_access_guide_needed")');
  const block = main.slice(start, main.indexOf("})();", start));

  it("첫 실행 판정은 백엔드 명령 하나에서 온다(UI 가 따로 재지 않는다)", () => {
    expect(start).toBeGreaterThan(-1);
    expect(block).toContain("if (!guide) return;");
  });

  it("안내 토스트가 권한 창 요청보다 먼저다", () => {
    const guide = block.indexOf('stickyToast(\n      "perm-guide"');
    const request = block.indexOf('invoke("request_folder_access")');
    expect(guide).toBeGreaterThan(-1);
    expect(request).toBeGreaterThan(guide);
    // 그려질 틈(프레임 + 지연)이 둘 사이에 있다
    const wait = block.indexOf("requestAnimationFrame");
    expect(wait).toBeGreaterThan(guide);
    expect(request).toBeGreaterThan(wait);
  });

  it("안내는 사람 말로 [허용]을 부탁하고, 거절해도 앱이 켜져 있음과 바꾸는 곳을 말한다", () => {
    expect(block).toContain("허용을 눌러 주세요");
    expect(block).toContain("거절해도 앱은 계속 켜져 있고");
    expect(block).toContain("파일 및 폴더");
  });

  it("공개 안내 말투 — 안내 본문에 괄호·대괄호가 없다", () => {
    const from = block.indexOf('"📁');
    const body = block.slice(from, block.indexOf("\n    );", from));
    expect(body).toContain("허용을 눌러 주세요");
    expect(/[()\[\]（）]/.test(body)).toBe(false);
  });

  it("권한 창 자체의 설명(Info.plist)이 같은 말을 한다 — 두 폴더 키 · 「~해 주세요」 · 괄호 없음", () => {
    const plist = readFileSync(new URL("../../src-tauri/Info.plist", import.meta.url), "utf8");
    for (const key of ["NSDesktopFolderUsageDescription", "NSDocumentsFolderUsageDescription"]) {
      const m = plist.match(new RegExp(`<key>${key}</key>\\s*<string>([^<]*)</string>`));
      expect(m).not.toBeNull();
      expect(m![1]).toContain("허용을 눌러 주세요");
      expect(/[()\[\]]/.test(m![1])).toBe(false);
    }
  });

  it("권한 창이 끝나면(성공·실패 무관) 안내를 내린다", () => {
    expect(/finally \{\s*dismissToast\("perm-guide"\);/.test(block)).toBe(true);
  });

  it("판정·대기의 정확한 형태(opus 1R 생존 후보: === true 반전 · await 삭제 · 지연 0)", () => {
    expect(main.slice(start - 40, start + 60)).toContain('guide = (await invoke("folder_access_guide_needed")) === true;');
    expect(block).toContain("await new Promise<void>((r) => requestAnimationFrame(() => setTimeout(r, 1500)));");
    expect(block).toContain('await invoke("request_folder_access");');
  });

  it("perm-warning 리스너가 먼저 등록된 뒤에 요청한다(거절 원인 문장이 유실되지 않게)", () => {
    expect(main.indexOf('listen("perm-warning"')).toBeLessThan(start);
  });

  it("권한 창 대기로 뒤따르는 리스너 등록을 막지 않는다(await 없이 띄움)", () => {
    const head = main.lastIndexOf("void (async () => {", start);
    expect(head).toBeGreaterThan(main.indexOf('listen("perm-warning"'));
    expect(start - head).toBeLessThan(200);
  });
});
