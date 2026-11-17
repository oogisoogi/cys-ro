// restartconfirm.test.ts — 「↻ 재시작」 단추 진입 확인 1회 복원 · TICKET=cysr-restart-confirm-1118.
// 박사님 11-18 「한 번 더 묻자」(실수로 눌러 일하던 자리가 끊긴 뒤). 09-21 에 없앴던 진입 확인 모달을 **이 단추만** 되돌린다.
// 함수 본문을 main.ts 에서 **그대로** 떼어 실행한다(deptprogresswiring.test.ts 의 load 와 같은 방식) — 소스 모양이 아니라 행동을 잰다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";

declare const Bun: { Transpiler: new (o: { loader: "ts" }) => { transformSync(code: string): string } };

const SRC = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const IDX_HTML = readFileSync(new URL("../index.html", import.meta.url), "utf8");

function fnText(name: string): string {
  const a = SRC.indexOf(`async function ${name}(`);
  expect({ 함수: name, 존재: a > -1 }).toEqual({ 함수: name, 존재: true });
  return SRC.slice(a, SRC.indexOf("\n}\n", a) + 2);
}
function constText(name: string): string {
  const a = SRC.indexOf(`const ${name} = `);
  expect({ 상수: name, 존재: a > -1 }).toEqual({ 상수: name, 존재: true });
  return SRC.slice(a, SRC.indexOf("\n", SRC.indexOf("} as const;", a)));
}

type Call = { fn: string; args: unknown[] };

function setup(answer: boolean | "never", opts: { blockedAfterModal?: boolean } = {}) {
  const calls: Call[] = [];
  const rec = (fn: string, ret?: unknown) => (...args: unknown[]) => {
    calls.push({ fn, args });
    return ret;
  };
  let blockedCalls = 0;
  let modalOpen = false;
  const tr = new Bun.Transpiler({ loader: "ts" });
  const deps: Record<string, unknown> = {
    daemonActionBlocked: () => {
      blockedCalls++;
      // 두 번째 호출(모달 뒤)에서만 막힌다 — 모달이 떠 있는 동안 다른 교대가 시작된 장면.
      return opts.blockedAfterModal === true && blockedCalls >= 2;
    },
    confirmModal: (...args: unknown[]) => {
      calls.push({ fn: "confirmModal", args });
      modalOpen = true;
      return answer === "never" ? new Promise<boolean>(() => {}) : Promise.resolve(answer);
    },
    stickyToast: rec("stickyToast"),
    dismissToast: rec("dismissToast"),
    toast: rec("toast"),
    invoke: async (cmd: string, a?: unknown) => {
      calls.push({ fn: "invoke", args: [cmd, a] });
      return { nodes: [], pending_loss_warning: [] };
    },
    classifyDrainVerifyFallback: () => null,
    drainVerifyFallbackToast: () => ({ title: "", body: "" }),
    restoringRetryKeys: () => [],
    mergeRetry: (v: unknown) => v,
    DRAIN_RESTORING_RETRY_MS: 0,
    restartAllDaemons: async (skip: boolean) => {
      calls.push({ fn: "restartAllDaemons", args: [skip] });
      return { failedDepts: [], deptRestoreFailed: false, restoreNotes: [] };
    },
    restartResultToast: rec("restartResultToast"),
    drainVerifyNotice: () => null,
    restartContinuityToast: rec("restartContinuityToast"),
  };
  const keys = Object.keys(deps);
  const code = `${tr.transformSync(constText("RESTART_CONFIRM_TEXT"))}\nlet rotatingDaemon = false;\n${tr.transformSync(fnText("manualRestartAllDaemons"))}\nreturn { manualRestartAllDaemons, rotating: () => rotatingDaemon };`;
  const fns = new Function(...keys, code)(...keys.map((k) => deps[k])) as { manualRestartAllDaemons: () => Promise<void>; rotating: () => boolean };
  return { fns, calls, isModalOpen: () => modalOpen };
}

describe("↻ 재시작 단추 — 진입 확인 1회", () => {
  it("취소 → 아무 호출도 하지 않는다(invoke 0 · 재시작 0 · 토스트 0 · 교대 표지 안 잡음)", async () => {
    const { fns, calls } = setup(false);
    await fns.manualRestartAllDaemons();
    expect(calls.map((c) => c.fn)).toEqual(["confirmModal"]);
    expect(fns.rotating()).toBe(false);
  });

  it("「다시 시작」 → 기존 흐름 그대로(드레인 검증 → 재시작 skipDrain=true → 결과 알림) · 끝나면 표지 해제", async () => {
    const { fns, calls } = setup(true);
    await fns.manualRestartAllDaemons();
    const names = calls.map((c) => c.fn);
    expect(names[0]).toBe("confirmModal");
    expect(calls.filter((c) => c.fn === "invoke").map((c) => c.args[0])).toEqual(["drain_verify"]);
    expect(calls.find((c) => c.fn === "restartAllDaemons")?.args).toEqual([true]);
    expect(names.indexOf("confirmModal")).toBeLessThan(names.indexOf("invoke"));
    expect(names).toContain("restartResultToast");
    expect(fns.rotating()).toBe(false);
  });

  it("문구 = 박사님이 정한 그대로 · 거절 쪽이 「취소」(confirmModal 의 기본 초점이 거절 단추)", async () => {
    const { fns, calls } = setup(false);
    await fns.manualRestartAllDaemons();
    expect(calls[0].args).toEqual([
      "데몬을 다시 시작할까요?",
      "일하던 자리들이 잠깐 멈췄다가 대화 기억과 함께 다시 켜집니다.",
      "다시 시작",
      "취소",
    ]);
    // 기본 초점 = 취소 · Esc·바깥 클릭 = 취소 는 confirmModal 한 곳이 보증한다 — 그 줄이 그대로 있는지 못박는다.
    const f = SRC.slice(SRC.indexOf("function confirmModal("));
    const modal = f.slice(0, f.indexOf("\n}\n"));
    expect(modal).toContain('(ov.querySelector(".modal-no") as HTMLElement).focus();');
    expect(modal).toContain('if (e.key !== "Escape") return;');
    expect(modal).toContain("if (e.target === ov) done(false);");
  });

  it("답이 오기 전(모달이 떠 있는 동안)에는 아무것도 시작하지 않는다 · 교대 표지도 안 잡아 다른 길을 막지 않는다", async () => {
    const { fns, calls } = setup("never");
    void fns.manualRestartAllDaemons();
    await Promise.resolve();
    expect(calls.map((c) => c.fn)).toEqual(["confirmModal"]);
    expect(fns.rotating()).toBe(false);
  });

  it("모달이 떠 있는 사이 다른 교대·purge 가 시작됐으면 「다시 시작」 을 눌러도 집행하지 않는다(TOCTOU)", async () => {
    const { fns, calls } = setup(true, { blockedAfterModal: true });
    await fns.manualRestartAllDaemons();
    expect(calls.map((c) => c.fn)).toEqual(["confirmModal"]);
    expect(fns.rotating()).toBe(false);
  });

  it("우회 길 0 — 이 함수를 부르는 곳은 단추 클릭 한 곳뿐(팔레트·단축키·타이머 없음)", () => {
    const callers = [...SRC.matchAll(/manualRestartAllDaemons\(\)/g)].length;
    // 선언 1 + 클릭 배선 1
    expect(callers).toBe(2);
    expect(SRC).toContain('document.getElementById("btn-restart-daemon")!.addEventListener("click", () => void manualRestartAllDaemons());');
    expect(IDX_HTML.match(/btn-restart-daemon/g)?.length).toBe(1);
    // 단추를 프로그램으로 누르는 길(.click()) 도 없다
    expect(SRC).not.toMatch(/btn-restart-daemon[^\n]*\.click\(\)/);
  });
});
