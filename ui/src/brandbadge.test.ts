// brandbadge.test.ts — cysr 표시명 핀 + Control Center 헤더 경보 배지 제거 회귀(TICKET=cysr-brand-version).
//
// ⓐ 표시명: 창 제목·문서 제목·좌상단 이름·CC 아래쪽 안내가 「cysr」다. 개명은 **표시명만**이다 —
//    (당시) 원작자 표기 줄과 명령어 이름(cys)은 바꾸지 않는다(master 설계 결정 2026-09-15).
//    ⇒ 1.1.7 에서 둘 다 바뀌었다: 표기 = 출발지 한 줄(⑱) · 명령어 정본 = cysr · cys 는 별칭(E1).
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
    expect(conf.app.windows[0].title).toBe("cysr");
    expect(html).toContain("<title>cysr</title>");
    // ⑨(publish-docs-118 2판 · 박사님 10-07 「공식명칭은 cysr · 이 외 다른 명칭은 쓰지 않는다」): 「CYSJavis Terminal」 꼬리 삭제
    expect(html).not.toContain("CYSJavis Terminal");
    expect(conf.app.windows[0].title).not.toContain("CYSJavis");
    expect(html).toContain('<span id="brand">cysr</span>');
  });

  it("Control Center 아래쪽 안내가 cysr 로 시작한다", () => {
    expect(main).toContain("`cysr Control Center · v${");
    expect(main).not.toContain("`cys Control Center · v${");
  });

  // ★판정 이력(되돌림 방지): 2026-09-15 master 설계 결정은 「표시명만 · productName 은 cys 유지
  //   (제자리 업데이트 연속성)」이었다. 2026-09-16 00:4x 박사님 지시 「설치되는 앱 이름도 cysr」로
  //   productName 은 cysr 가 됐다(TICKET=cysr-product-rename · master 결정 A). 연속성은 이제
  //   productName 이 아니라 NSIS 훅이 진다 — 설치 폴더를 %LOCALAPPDATA%\cys 에 고정하고 옛 이름의
  //   제어판 키·바로가기만 정리한다(src-tauri/nsis-hooks.nsh ⓪-b · 컴파일 하네스 N8).
  //   identifier(업데이터·서명 연속성)는 여전히 그대로다. 명령어는 1.1.7 E1 에서 정본 cysr · 실행파일 cys 는 별칭.
  it("productName 은 cysr · 식별자는 그대로다(제자리 업데이트 연속성)", () => {
    expect(conf.productName).toBe("cysr");
    expect(conf.productName).not.toBe("cys");
    expect(conf.identifier).toBe("com.cysjavis.terminal");
  });

  // (1.1.8 · 박사님 10-08 12:5x 「깃허브에만 원작자를 밝히고 cysr 앱에서는 삭제한다」) 1.1.7 ⑱ 의 앱 안 출발지 한 줄(#ws-credit)을 지운다.
  //   깃허브 쪽 표기(README 출발지 절 · 릴리스 본문 · NOTICE.md · LICENSE)는 그대로 = test_default_fleet_formation.py ⓕ.
  it("앱 화면에 출발지·원작자 표기 없음", () => {
    for (const s of ["ws-credit", "에서 출발", "출발했습니다", "idoforgod", "cys-terminal", "원작자", "파생판", "Original author"]) {
      expect(html).not.toContain(s);
    }
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

  it("승인 대기 배지·경보 스트립 스타일은 남아 있다 · (1.1.8 U4 · 설계 §5-2) 업데이트 배지·단추는 없다", () => {
    expect(html).toContain('id="cc-pending-badge"');
    expect(html).not.toContain('id="update-badge"');
    expect(html).not.toContain('id="btn-update"');
    expect(css).toContain(".cc-alerts {");
  });
});
