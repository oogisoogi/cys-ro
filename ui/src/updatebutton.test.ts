import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { updatePlan } from "./updateplan";

// ★TICKET=cysr-console-flicker-r2 ⓔ — 「배지는 떴는데 누르면 최신」 회귀 핀.
// 배지를 만든 판정과 클릭이 따르는 판정이 **같은 한 번의 확인**이어야 한다. 종전 디스패처는 이전 확인의
// 캐시로 경로를 골라 두 판정이 서로 다른 시점의 값이었다. main.ts 는 DOM·Tauri 에 묶여 직접 못 부르므로
// 디스패처 본문을 **소스로** 못박고(구조 핀), 「없음」→배지 "0" 은 순수 함수로 잰다(행동 핀).
// (파일 읽기·단언 형태는 tsconfig.check.json 의 types:[] 계약에 맞춘다 — brandbadge.test.ts 와 같은 방식.)

const MAIN = readFileSync(new URL("./main.ts", import.meta.url), "utf8");

function fnBody(src: string, header: string): string {
  const at = src.indexOf(header);
  expect(at).toBeGreaterThan(-1); // 계측 타당성 — 대상 함수를 찾았는가(못 찾으면 아래 단언이 공허)
  const open = src.indexOf("{", at);
  let depth = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) return src.slice(open + 1, i);
  }
  throw new Error("함수 끝을 못 찾았다");
}

describe("Update 버튼 — 배지와 클릭이 같은 판정을 쓴다", () => {
  test("클릭은 매번 새로 확인한다(캐시로 경로를 고르지 않는다)", () => {
    const body = fnBody(MAIN, "async function onUpdateButton()");
    expect(body).toContain("checkForUpdate(false)");
    for (const stale of ["updateAvailable", "packUpdateAvailable", "promptBinaryPatch", "promptPackInstall"]) {
      expect(body).not.toContain(stale);
    }
  });

  test("버튼 클릭 배선이 그 디스패처를 부른다", () => {
    const wired = /getElementById\("btn-update"\)!\.addEventListener\("click", \(\) => onUpdateButton\(\)\)/;
    expect(wired.test(MAIN)).toBe(true);
  });

  test("같은 판·같은 build_id(백엔드 check_update=null) + 팩 없음 → 배지 '0'(없음 뒤 갱신값)", () => {
    // 백엔드: same_version_verdict(같은 판·같은 build_id)=Skip → check_update 가 null 을 준다
    //   (src-tauri main.rs 시험 same_version_verdict_updates_only_on_a_different_build_id ②).
    const p = updatePlan({ binVersion: null, packVersion: null, binaryTooOld: false, binCheckFailed: false, packCheckFailed: false });
    expect(p.kind).toBe("none");
    expect(p.badge).toBe("0");
  });

  test("「없음」 판정이면 checkForUpdate 가 배지 텍스트를 판정값으로 덮어쓴다(낡은 배지 잔존 금지)", () => {
    const body = fnBody(MAIN, "async function checkForUpdate(silent: boolean)");
    expect(body).toContain("badge.textContent = plan.badge;");
    expect(body).toContain('if (plan.kind !== "unknown")');
  });
});
