// headerlabels.test.ts — 상단바 판번 상시 표시(ⓐ)·데몬 재기동 뒤 pid 라벨 갱신(ⓑ) 회귀(TICKET=cysr-ui-polish-101).
//
// ⓐ 실기: 판번은 데몬≠앱 스큐 박스에서만 보였다 — 평시엔 어디에도 없어 참가자 지원이 막혔다.
// ⓑ 실기(22:40): 데몬을 죽여 스케줄러가 재기동(pid 4116→10132)한 뒤에도 헤더가 옛 pid 를 보였다.
//    라벨은 시작 1회만 쓰였고, 이벤트 스트림 재수립이 UI 에 아무 신호도 주지 않았다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { appVersionLabel, appVersionTitle, daemonInfoLabel } from "./headerlabels";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const rs = readFileSync(new URL("../../src-tauri/src/main.rs", import.meta.url), "utf8");

function fnBody(src: string, head: string, end = "\n}\n"): string {
  const s = src.indexOf(head);
  expect(s).toBeGreaterThan(-1);
  return src.slice(s, src.indexOf(end, s));
}

describe("ⓐ 앱 판번 상시 표시", () => {
  it("라벨·툴팁 문구", () => {
    expect(appVersionLabel("1.0.1")).toBe("v1.0.1");
    expect(appVersionLabel("")).toBe("");
    expect(appVersionTitle("1.0.1", "abc123")).toBe("cysr 앱 판번 v1.0.1 · build abc123");
    expect(appVersionTitle("1.0.1", "")).toContain("build unknown");
  });

  it("브랜드 바로 옆에 판번 칸이 있고, 스큐 박스는 그대로다", () => {
    expect(html).toMatch(/<span id="brand">cysr<\/span>\s*<span id="app-ver"/);
    expect(main).toContain('verSkewBadge.className = "ver-skew-badge"');
  });

  it("start() 가 데몬 대기 전에 판번·build_id 를 채운다", () => {
    const body = fnBody(main, "async function start() {");
    const fill = body.indexOf('getElementById("app-ver")');
    expect(fill).toBeGreaterThan(-1);
    expect(fill).toBeLessThan(body.indexOf('listen("daemon-ready"'));
    const block = body.slice(fill, body.indexOf("})();", fill));
    expect(block).toContain('invoke("app_version")');
    expect(block).toContain('invoke("app_build_id")');
    expect(block).toContain("el.textContent = appVersionLabel(ver)");
    expect(block).toContain("el.title = appVersionTitle(ver, buildId)");
  });

  it("app_build_id 커맨드가 정의·등록돼 있다", () => {
    expect(rs).toContain("fn app_build_id() -> String {");
    expect(rs).toMatch(/app_version,\s*\n\s*app_build_id,/);
  });
});

describe("ⓑ 데몬 재기동 뒤 라벨 갱신", () => {
  it("라벨 문구", () => {
    expect(daemonInfoLabel({ daemon_pid: 10132, socket_path: "/s" })).toBe("daemon pid=10132 sock=/s");
  });

  it("forwarder 가 재수립에서만 daemon-reconnected 를 낸다(첫 연결 제외)", () => {
    const body = fnBody(rs, "fn spawn_event_forwarder(");
    const emit = body.indexOf('app.emit("daemon-reconnected"');
    expect(emit).toBeGreaterThan(body.indexOf("connected = true;"));
    expect(body.slice(body.lastIndexOf("if ever_connected {", emit), emit)).toContain("if ever_connected {");
    expect(body).toMatch(/if connected \{\s*\n\s*ever_connected = true;/);
    expect(body).toContain("let mut ever_connected = false;");
  });

  it("UI 가 재연결마다 daemon_status 를 다시 물어 첫 텍스트 노드만 바꾼다(스큐 배지 보존)", () => {
    const ls = main.indexOf('listen("daemon-reconnected", () => {');
    expect(ls).toBeGreaterThan(-1);
    const handler = main.slice(ls, main.indexOf("});", ls));
    expect(handler).toContain("void refreshDaemonInfo(info);");
    expect(handler).toContain("void checkVersionSkew();");
    const body = fnBody(main, "async function refreshDaemonInfo(");
    expect(body).toContain('invoke("daemon_status")');
    expect(body).toContain("daemonInfoLabel(st)");
    expect(body).toContain("first.textContent = text");
    expect(body).not.toContain("info.textContent");
  });

  it("시작 라벨도 같은 문구 함수를 쓴다(두 벌 드리프트 차단)", () => {
    expect(main).toContain("info.textContent = daemonInfoLabel(status);");
    expect(main).not.toContain("`daemon pid=${");
  });
});
