// drainverify.ts 순수 함수 회귀 테스트 (bun test — 신규 의존성 0).
//
// [F5] drain_verify 폴백 사유 분기: 구버전 미지원과 크래시/하드캡을 구분해 UI가 정직한 문구를 고르게 한다.
// 거동(plain drain 폴백)은 양쪽 동일하고 분류·문구만 다르다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import {
  classifyDrainVerifyFallback,
  drainVerifyFallbackToast,
  drainVerifyNotice,
  mergeRetry,
  restoringRetryKeys,
} from "./drainverify";

describe("classifyDrainVerifyFallback — drain_verify 폴백 사유 분기", () => {
  it("구버전 미지원(unsupported 접두) → 'unsupported'", () => {
    expect(
      classifyDrainVerifyFallback("unsupported: cys drain --verify 미지원(구버전 바이너리) (stderr: ...)"),
    ).toBe("unsupported");
  });
  it("크래시/하드캡(verify_failed 접두) → 'verify_failed'", () => {
    expect(
      classifyDrainVerifyFallback("verify_failed: drain --verify 실행 실패(exit=Some(3)...) (stderr: )"),
    ).toBe("verify_failed");
  });
  it("알 수 없는 에러 → null(폴백 아님·상위 rethrow)", () => {
    expect(classifyDrainVerifyFallback("some other tauri error")).toBeNull();
  });
});

describe("drainVerifyFallbackToast — 사유별 정직 문구", () => {
  it("미지원은 '미지원' 문구, '무손실' 표현 없음", () => {
    const t = drainVerifyFallbackToast("unsupported");
    expect(t.title).toContain("미지원");
    expect(t.body).toContain("기존 방식");
    expect(t.body).not.toContain("무손실");
  });
  it("검증 실패는 '실패·점검 권고' 문구, 미지원과 구별", () => {
    const t = drainVerifyFallbackToast("verify_failed");
    expect(t.title).toContain("실패");
    expect(t.body).toContain("점검");
    expect(t.body).not.toContain("무손실");
    // 두 문구가 실제로 다른지(정직성 교정의 핵심)
    expect(t.body).not.toBe(drainVerifyFallbackToast("unsupported").body);
  });
});

describe("drainVerifyNotice — 확인 창 폐기 후의 사후 알림 1줄", () => {
  const node = (role: string, outcome: string) => ({ role, surface: "surface:9", outcome });
  it("전원 마커 확인이면 알림이 없다(조용한 성공)", () => {
    expect(
      drainVerifyNotice({ all_saved: true, total: 3, summary: { saved: 3 }, nodes: [node("master", "saved")] }),
    ).toBeNull();
  });
  it("미확인 자리가 있으면 '대화는 복원했다'를 함께 말한다(묻지 않는다)", () => {
    const n = drainVerifyNotice({
      all_saved: false,
      total: 3,
      summary: { saved: 1 },
      nodes: [node("master", "saved"), node("worker", "timeout"), node("cso", "delivery_failed")],
      max_wait_secs: 40,
    });
    expect(n).not.toBeNull();
    expect(n!.body).toContain("자리 2개");
    expect(n!.body).toContain("복원");
    expect(n!.body).toContain("최대 40초");
    // ★확인 창을 없앴으므로 질문 문구가 남아 있으면 안 된다(회귀 가드).
    expect(n!.body).not.toContain("하시겠습니까");
    expect(n!.title).not.toContain("하시겠습니까");
    // 자리별 사유가 사람 말로 붙는다.
    expect(n!.body).toContain("마커 미확인(시간초과)");
    expect(n!.body).toContain("입력 미제출 실측");
  });
  it("all_saved=false 인데 나열할 노드가 없으면(0노드) 알리지 않는다", () => {
    expect(drainVerifyNotice({ all_saved: false, total: 0, summary: { saved: 0 }, nodes: [] })).toBeNull();
  });
});

// ★[V111-F4] 확인 창 폐기의 **소스 가드** — 순수 함수로는 「모달을 안 띄운다」를 못 잰다(모달은 main.ts
// 흐름에 있다). 그래서 재시작 흐름 함수 본문에 확인 모달 호출이 없다는 것을 직접 단언한다.
// (함수 본문으로 범위를 좁힌다 — 파일 전체 grep 이면 다른 흐름의 정당한 모달에 걸려 공허해진다.)
// ★[V111-F5] 진입 확인 모달 폐기의 전용 축(master 판정 2026-09-21) — 「↻ 한 번 = 드레인 → 재시작」.
// 위 describe 와 축을 나눠 둔다: 저장 미확인 창(뒤)과 진입 확인 창(앞)은 **다른 순간에 묻는** 다른 결함이라
// 한 시험에 묶으면 하나가 되살아나도 다른 하나의 적색에 묻힌다.
describe("manualRestartAllDaemons — 진입 확인 모달이 없다(1클릭 즉시 집행)", () => {
  it("단추 진입부터 drain_verify 호출까지 사용자에게 묻는 단계가 0이다", async () => {
    const src = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
    const i = src.indexOf("async function manualRestartAllDaemons()");
    const j = src.indexOf('invoke("drain_verify"', i);
    expect(i).toBeGreaterThan(-1);
    expect(j).toBeGreaterThan(i);
    const head = src
      .slice(i, j)
      .split("\n")
      .filter((l: string) => !l.trim().startsWith("//"))
      .join("\n");
    expect(head).not.toContain("confirmModal");
    expect(head).not.toContain("if (!ok) return");
    // 대신 진행 상황을 알리는 sticky 토스트가 있어야 한다(묻지 않되 조용하지도 않다).
    expect(head).toContain("stickyToast");
  });
});

describe("manualRestartAllDaemons — 저장 미확인 확인 창이 없다", () => {
  it("재시작 흐름 본문에 확인 모달이 하나도 없다(1클릭 = 즉시 집행)", async () => {
    const src = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
    const i = src.indexOf("async function manualRestartAllDaemons()");
    expect(i).toBeGreaterThan(-1);
    // ★주석을 걷어낸 **선언문만** 본다 — 이 가드가 자기 설명 주석(「"그래도 재시작"에 아니오를…」)에
    //   스스로 걸렸다. 가드는 코드에 묻고 산문에 묻지 않는다.
    const raw = src.slice(i, src.indexOf("\n}\n", i));
    const body = raw
      .split("\n")
      .filter((l: string) => !l.trim().startsWith("//"))
      .join("\n");
    expect(body).not.toContain("일부 노드 저장 미확인");
    expect(body).not.toContain("그래도 재시작");
    // 대신 사후 알림을 부른다(빼면 사용자는 아무것도 못 듣는다).
    expect(body).toContain("drainVerifyNotice");
    // ★[V111-F5] 진입 확인 모달도 없앴다(master 판정 2026-09-21) — 이 흐름에는 **어떤 확인 모달도 없다**.
    //   ↻ 한 번이 곧 드레인→재시작이고, 사용자는 중간에 아무것도 고르지 않는다.
    expect(body).not.toContain("confirmModal");
  });
});

describe("v113-restore B3 — 복원 중 건너뛴 자리만 재저장", () => {
  const n = (dept: string, surface: string, outcome: string) => ({ role: "worker", dept, surface, outcome });
  it("건너뛴 자리만 키로 뽑는다 · dept 없는 구 코어 결과는 뺀다", () => {
    const keys = restoringRetryKeys([
      n("main", "surface:1", "saved"),
      n("main", "surface:2", "skipped_restoring"),
      { role: "cso", surface: "surface:3", outcome: "skipped_restoring" },
    ]);
    expect(keys).toEqual(["main/surface:2"]);
  });
  it("재시도 결과가 그 자리만 덮고 요약·all_saved 를 다시 센다", () => {
    const first = {
      all_saved: false,
      total: 3,
      summary: { saved: 1, timeout: 0, skipped_restoring: 2 },
      nodes: [n("main", "surface:1", "saved"), n("main", "surface:2", "skipped_restoring"), n("hr", "surface:2", "skipped_restoring")],
    };
    const merged = mergeRetry(first, { nodes: [n("main", "surface:2", "saved"), n("hr", "surface:2", "saved")] });
    expect(merged.summary.saved).toBe(3);
    expect(merged.summary.skipped_restoring).toBe(0);
    expect(merged.all_saved).toBe(true);
    const partial = mergeRetry(first, { nodes: [n("main", "surface:2", "saved")] });
    expect(partial.all_saved).toBe(false);
    expect(partial.nodes[2].outcome).toBe("skipped_restoring"); // 다른 부서의 같은 번호는 섞이지 않는다
  });
});

describe("v113-restore B3 배선 — ↻ 흐름이 건너뛴 자리만 재저장한 뒤 재시작한다", () => {
  it("재시도 호출이 재시작보다 앞이고 only 키를 싣는다", () => {
    const src = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
    const f = src.indexOf("async function manualRestartAllDaemons(");
    const body = src.slice(f, src.indexOf("\n}\n", f));
    const keys = body.indexOf("restoringRetryKeys(verify.nodes)");
    const again = body.indexOf('invoke("drain_verify", { timeout: 20, only: retryKeys })');
    const merge = body.indexOf("verify = mergeRetry(verify, again)");
    const restart = body.indexOf("await restartAllDaemons(true)");
    expect(keys).toBeGreaterThan(-1);
    expect(again).toBeGreaterThan(keys);
    expect(merge).toBeGreaterThan(again);
    expect(restart).toBeGreaterThan(merge);
  });
});
