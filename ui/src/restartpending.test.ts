// restartpending.test.ts — 맥 교체 완료 뒤 「다시 켜기」 대기 · TICKET=v116-restart-toast.
// 행동 핀 = 순수 함수(판번 짝 무효화 · 단추 동작 · 문구 규칙). 구조 핀 = main.ts·main.rs 소스(DOM·Tauri 에 묶여
// 직접 못 부르는 배선 — updatebutton.test.ts 와 같은 방식). 새 시험에 toMatch 금지(tsc 계약) → re.test.
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import {
  RESTART_PENDING_KEY,
  UPDATE_BUTTON_LABEL,
  RESTART_BUTTON_LABEL,
  encodeRestartPending,
  decodeRestartPending,
  updateButtonAction,
  restartReadyToast,
  restartPendingTitle,
} from "./restartpending";

const MAIN = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const HTML = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const RUST = readFileSync(new URL("../../src-tauri/src/main.rs", import.meta.url), "utf8");

function fnBody(src: string, header: string): string {
  const at = src.indexOf(header);
  expect(at).toBeGreaterThan(-1); // 계측 타당성 — 대상 함수를 찾았는가
  const open = src.indexOf("{", at);
  let depth = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) return src.slice(open + 1, i);
  }
  throw new Error("함수 끝을 못 찾았다");
}

describe("대기 판정 — 판번 짝으로 저절로 풀린다", () => {
  test("옛 앱이 그대로 돌면(⌘R) 대기 판번을 돌려준다", () => {
    expect(decodeRestartPending(encodeRestartPending("1.1.7", "1.1.6"), "1.1.6")).toBe("1.1.7");
  });
  test("새 판으로 켜졌으면(지금 판번 == 대기 판번) 무효", () => {
    expect(decodeRestartPending(encodeRestartPending("1.1.7", "1.1.6"), "1.1.7")).toBeNull();
  });
  test("저장 때 판번과 지금 판번이 다르면(다른 프로세스) 무효 — 대기 판번과 무관하게", () => {
    expect(decodeRestartPending(encodeRestartPending("1.1.8", "1.1.6"), "1.1.7")).toBeNull();
  });
  test("검증할 수 없으면 무효 — 판번 모름 · 값 없음 · 깨진 값 · 모양 틀림 · 빈 옛 판번", () => {
    const ok = encodeRestartPending("1.1.7", "1.1.6");
    expect(decodeRestartPending(ok, null)).toBeNull();
    expect(decodeRestartPending(ok, "")).toBeNull();
    expect(decodeRestartPending(null, "1.1.6")).toBeNull();
    expect(decodeRestartPending("", "1.1.6")).toBeNull();
    expect(decodeRestartPending("{not json", "1.1.6")).toBeNull();
    expect(decodeRestartPending("null", "1.1.6")).toBeNull();
    expect(decodeRestartPending('"1.1.7"', "1.1.6")).toBeNull();
    expect(decodeRestartPending(JSON.stringify({ version: 117, appVersion: "1.1.6" }), "1.1.6")).toBeNull();
    expect(decodeRestartPending(JSON.stringify({ version: "1.1.7" }), "1.1.6")).toBeNull();
    expect(decodeRestartPending(encodeRestartPending("1.1.7", ""), "1.1.6")).toBeNull();
  });
  test("칸 이름에 판 번호가 붙어 있다(모양이 바뀌면 옛 값이 섞이지 않게)", () => {
    expect(/-v\d+$/.test(RESTART_PENDING_KEY)).toBe(true);
  });
});

describe("헤더 단추 — 대기면 다시 켜기, 아니면 새로 확인", () => {
  test("동작 판정", () => {
    expect(updateButtonAction(null)).toBe("check");
    expect(updateButtonAction("1.1.7")).toBe("restart");
    expect(updateButtonAction("")).toBe("restart"); // 판번 없는 이벤트여도 교체는 끝났다
  });
  test("onUpdateButton = 대기 판정 뒤 restartAfterUpdate, 그 밖은 checkForUpdate(false) · 확인 캐시로 경로를 고르지 않는다", () => {
    const body = fnBody(MAIN, "async function onUpdateButton()");
    expect(body).toContain('updateButtonAction(restartPendingVersion) === "restart"');
    expect(body).toContain("restartAfterUpdate(restartPendingVersion!)");
    expect(body).toContain("checkForUpdate(false)");
    expect(body.includes("install_update")).toBe(false);
  });
  test("checkForUpdate 는 첫 줄에서 복원을 기다리고 대기면 확인 없이 끝난다(시작·주기·포커스 확인 공통)", () => {
    const body = fnBody(MAIN, "async function checkForUpdate(silent: boolean)");
    const guard = body.indexOf("if (restartPendingVersion !== null) {");
    expect(body.indexOf("await restoreRestartPending();")).toBeGreaterThan(-1);
    expect(guard).toBeGreaterThan(body.indexOf("await restoreRestartPending();"));
    expect(guard).toBeLessThan(body.indexOf('invoke("check_update")'));
    expect(body.slice(guard, body.indexOf("}", guard))).toContain("return;");
  });
  test("설치 확인 창을 누른 사이 교체가 끝났으면 install_update 대신 다시 켜기", () => {
    const body = fnBody(MAIN, "async function promptBinaryPatch()");
    const g = body.indexOf("if (restartPendingVersion !== null) return restartAfterUpdate(restartPendingVersion);");
    expect(g).toBeGreaterThan(-1);
    expect(g).toBeLessThan(body.indexOf('invoke("install_update"'));
  });
  test("단추 글자: 평소 = index.html 의 「업데이트」 그대로 · 대기 = 「다시 켜기」(데몬 「↻ 재시작」과 다른 이름)", () => {
    expect(/<button id="btn-update"[^>]*>업데이트 <span id="update-badge"/.test(HTML)).toBe(true);
    expect(UPDATE_BUTTON_LABEL).toBe("업데이트");
    expect(RESTART_BUTTON_LABEL).toBe("다시 켜기");
    expect(RESTART_BUTTON_LABEL.includes("재시작")).toBe(false);
    expect(fnBody(MAIN, "function paintRestartPending()")).toContain("btn.firstChild.nodeValue = `${RESTART_BUTTON_LABEL} `");
  });
});

describe("대기 상태의 출처 — 맥 교체 완료 이벤트 하나뿐(윈에선 생기지 않는다)", () => {
  test("restartPendingVersion 에 값을 넣는 곳 = markRestartPending · 복원 두 곳뿐 · markRestartPending 호출 = 교체 완료 리스너 하나", () => {
    const assigns = MAIN.split("\n").filter((l) => /restartPendingVersion\s*=[^=]/.test(l) && !/^\s*(\/\/|\*)/.test(l));
    expect(MAIN).toContain("let restartPendingVersion: string | null = null;"); // 선언(초기값 = 대기 없음)
    expect(assigns.map((l) => l.trim())).toEqual([
      "restartPendingVersion = version;",
      "if (restartPendingVersion === null) restartPendingVersion = v;",
    ]);
    const calls = [...MAIN.matchAll(/markRestartPending\(/g)].length;
    expect(calls).toBe(2); // 정의 1 + 호출 1
    const at = MAIN.indexOf('await listen("update-restart-required"');
    expect(at).toBeGreaterThan(-1);
    expect(MAIN.slice(at, MAIN.indexOf("});", at))).toContain("markRestartPending(version);");
  });
  test("백엔드가 update-restart-required 를 내는 곳 = 맥 install_update_darwin 안 한 곳뿐", () => {
    const hits = [...RUST.matchAll(/"update-restart-required"/g)].map((m) => m.index!);
    expect(hits.length).toBe(1);
    const fn = RUST.lastIndexOf("async fn install_update_darwin(", hits[0]);
    expect(fn).toBeGreaterThan(-1);
    expect(RUST.slice(fn, hits[0]).includes("\nasync fn ")).toBe(false); // 사이에 다른 함수 머리 0
    expect(RUST.slice(fn, hits[0]).includes("\nfn ")).toBe(false);
  });
});

describe("다시 켜기 재진입 차단(4군 ①)", () => {
  test("플래그를 첫 await 전에 세우고 finally 에서 푼다 · 진행 중이면 호출 없이 끝", () => {
    // 주석 줄을 뺀 코드만 본다(주석의 「첫 await 전에」 같은 낱말이 계측을 속이지 않게)
    const body = fnBody(MAIN, "async function restartAfterUpdate(version: string)").split("\n").filter((l) => !/^\s*\/\//.test(l)).join("\n");
    const check = body.indexOf("if (restartingAfterUpdate) {");
    const set = body.indexOf("restartingAfterUpdate = true;");
    const firstAwait = body.indexOf("await ");
    expect(check).toBeGreaterThan(-1);
    expect(set).toBeGreaterThan(check);
    expect(set).toBeLessThan(firstAwait);
    expect(body.slice(check, set).includes("invoke(")).toBe(false);
    expect(/finally\s*\{\s*restartingAfterUpdate = false;/.test(body)).toBe(true);
  });
  test("재시작 경로는 종전 restart_after_update 그대로(새 재시작 경로 0 · 4군 ③)", () => {
    const once = fnBody(MAIN, "async function restartAfterUpdateOnce(version: string)");
    expect(once).toContain('invoke("restart_after_update", { force: false })');
    expect(once).toContain('invoke("restart_after_update", { force: true })');
    expect([...MAIN.matchAll(/invoke\("restart_after_update"/g)].length).toBe(2);
  });
});

describe("문구 — 공개 문구 규칙(새로 생기거나 바뀐 문자열만)", () => {
  const t = restartReadyToast("1.1.7");
  const texts = [t.name, t.detail, restartPendingTitle("1.1.7"), restartReadyToast("").detail, restartPendingTitle("")];
  test("괄호 0 · 판번 앞 v 0 · 전문 용어 0 · 「판」 0", () => {
    for (const s of texts) {
      expect(/[()（）]/.test(s)).toBe(false);
      expect(/\bv\d/.test(s)).toBe(false);
      expect(/drain|데몬|세션|판번|새 판|재시작|sticky|토스트/.test(s)).toBe(false);
    }
  });
  test("안내자 말투 · 행동은 문장마다 하나 · 단추 이름으로 가리킨다", () => {
    expect(t.detail.endsWith("눌러 주세요.")).toBe(true);
    expect(t.detail).toContain(`「${RESTART_BUTTON_LABEL}」 단추`);
    expect(t.detail).toContain("새 앱 1.1.7 설치가 끝났습니다.");
    expect(t.detail.split(". ").length).toBe(3);
    expect(restartReadyToast("").detail.startsWith("새 앱 설치가 끝났습니다.")).toBe(true); // 판번 없는 이벤트
  });
  test("알림은 사라진다 — 수명 규칙(오너 정책) 무변경 · upd-restart 는 지속형 기본 60초", () => {
    const ttl = readFileSync(new URL("./toastttl.ts", import.meta.url), "utf8");
    expect(ttl.includes('"upd-restart"')).toBe(false);
    expect(ttl).toContain("export const STICKY_TTL_MS = 60_000;");
  });
});
