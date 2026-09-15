// brandbadge.test.ts — cysr 표시명 핀 + Control Center 헤더 경보 배지 제거 회귀(TICKET=cysr-brand-version).
//
// ⓐ 표시명: 창 제목·문서 제목·좌상단 이름·CC 아래쪽 안내가 「cysr」다. 개명은 **표시명만**이다 —
//    원작자 표기 줄과 명령어 이름(cys)은 바꾸지 않는다(master 설계 결정 2026-09-15).
// ⓔ 경보 배지: 헤더의 ⚠N 개수 배지는 경보가 몇 개든 **요소 자체가 없다**(박사님 결정 2026-09-15).
//    경보 목록은 Control Center 안 Live 스트립(#cc-alerts)으로만 보인다 — 그 스트립과 승인 대기·
//    Update 배지는 그대로여야 한다(과잉 삭제 방지 축).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const css = readFileSync(new URL("./style.css", import.meta.url), "utf8");
const conf = JSON.parse(readFileSync(new URL("../../src-tauri/tauri.conf.json", import.meta.url), "utf8"));

describe("ⓐ 표시명 cysr", () => {
  it("창 제목·문서 제목·좌상단 이름이 cysr 다", () => {
    expect(conf.app.windows[0].title).toBe("cysr — CYSJavis Terminal");
    expect(html).toContain("<title>cysr — CYSJavis Terminal</title>");
    expect(html).toContain('<span id="brand">cysr</span>');
  });

  it("Control Center 아래쪽 안내가 cysr 로 시작한다", () => {
    expect(main).toContain("`cysr Control Center · v${");
    expect(main).not.toContain("`cys Control Center · v${");
  });

  it("식별자·실행파일 이름은 그대로다(제자리 업데이트 연속성)", () => {
    expect(conf.productName).toBe("cys");
    expect(conf.identifier).toBe("com.cysjavis.terminal");
  });

  it("원작자 표기 줄은 손대지 않았다", () => {
    expect(html).toContain('원작 CYSJavis(idoforgod) · MIT · 파생판 배포 oogisoogi</div>');
  });
});

describe("ⓔ Control Center 헤더 경보 배지 제거", () => {
  it("헤더 배지 요소·스타일·갱신 코드가 어디에도 없다", () => {
    expect(html).not.toContain("cc-alertbadge");
    expect(main).not.toContain("cc-alertbadge");
    expect(main).not.toContain("cc-alert-badge");
    expect(css).not.toContain(".cc-alert-badge");
  });

  it("경보가 여러 개여도 렌더 함수는 스트립만 채운다", () => {
    const start = main.indexOf("function renderAlerts(");
    expect(start).toBeGreaterThan(-1);
    const body = main.slice(start, main.indexOf("\n}\n", start));
    expect(body).toContain('getElementById("cc-alerts")');
    expect(body).not.toContain("badge");
    expect(body).not.toContain(".length}");
  });

  it("승인 대기 배지·Update 배지·경보 스트립 스타일은 남아 있다", () => {
    expect(html).toContain('id="cc-pending-badge"');
    expect(html).toContain('id="update-badge"');
    expect(css).toContain(".cc-alerts {");
  });
});
