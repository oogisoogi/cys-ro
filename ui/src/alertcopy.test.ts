// alertcopy.test.ts — 경보 알림 문구(D4 #8) · TICKET=v116-ui-close-r2.
// 계약: ①코드 원문 0(surface:N · 역할 코드 · 내부 지침 문구) ②세기 머리(❌·🚨·⚠·🔋·💤) 유지 ③사실(번호·%·시간·사유) 유지
//       ④사용자 행동 한 문장 ⑤사망 알림엔 안심 문장.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import {
  seatNo, seatName, durText, approvalRequestCopy, approvalStalledCopy, contextThresholdCopy, paneIdleCopy,
  masterIdleCopy, agentExitedCopy, deadmanCopy, roleTakeoverCopy, seatFolderDeniedCopy, type AlertCopy,
} from "./alertcopy";

const CODE = /surface:\d|\bmaster\b|\bworker(-\d+)?\b|\bcso\b|\breviewer\b|MASTER_DIRECTIVE|cycle-agent|deadman|\d+s\b/;
const all: [string, AlertCopy][] = [
  ["req", approvalRequestCopy(3, { role: "worker-13", surface_ref: "surface:3", excerpt: "Do you want to proceed?" })],
  ["stall", approvalStalledCopy(3, { title: "배포 승인", age_secs: 400, surface_ref: "surface:3" })],
  ["stall0", approvalStalledCopy(null, { title: "사람 전용", age_secs: 0, reason: "human_only" })],
  ["ctx", contextThresholdCopy(2, { role: "cso", context_pct: 83, threshold: 60, action: "cycle-agent(저장→검증→clear→복원) 집행 대상 — MASTER_DIRECTIVE §컨텍스트 사이클" })],
  ["idle", paneIdleCopy(5, { idle_seconds: 900 })],
  ["midle", masterIdleCopy(1, "master", { idle_secs: 320, threshold_secs: 300 })],
  ["exit", agentExitedCopy(4, { role: "worker-2", agent: "claude" })],
  ["dead", deadmanCopy(1, { role: "master", axis: "agent_dead", reason: "agent process dead" })],
  ["take", roleTakeoverCopy(7, { role: "master" })],
  ["folder", seatFolderDeniedCopy(9, { role: "worker", cwd: "/Users/u/Documents/x" }, "문서")],
];

describe("D4 #8 ① 코드 원문 0 · ④ 행동 한 문장", () => {
  for (const [k, c] of all)
    it(k, () => {
      expect(CODE.test(c.title + " " + c.body)).toBe(false);
      expect(/주세요\.$|있습니다\.$|맡습니다\.$|재시작하세요\.$|둡니다\.$/.test(c.body)).toBe(true);
    });
});

describe("D4 #8 ② 세기 머리 · ③ 사실 유지", () => {
  it("승인 대기 = ⚠ · 창 번호·역할 이름·발췌", () => {
    const c = all[0][1];
    expect(c.title.startsWith("⚠")).toBe(true);
    expect(c.body.startsWith("3번 작업 창이")).toBe(true);
    expect(c.body.includes("Do you want to proceed?")).toBe(true);
  });
  it("승인 방치 = 경과 시간 · 제목 · 경과 0(대신 처리할 자리 없음)은 「사람 확인 필요」", () => {
    expect(all[1][1].body.includes("6분 넘게")).toBe(true);
    expect(all[1][1].body.includes("배포 승인")).toBe(true);
    expect(all[2][1].body.startsWith("요청은 사람 확인이 필요합니다")).toBe(true);
    expect(all[1][1].title.includes("사람 확인 필요")).toBe(true);
  });
  it("대화 기억 = 몇 % · 기준 몇 %(내부 action 문구는 버림)", () => {
    expect(all[3][1].title).toBe("🔋 대화 기억 83%");
    expect(all[3][1].body.includes("2번 운영 관리 창의 대화 기억이 기준 60%를")).toBe(true);
  });
  it("유휴 = 💤 · 시간", () => {
    expect(all[4][1].body.startsWith("5번 창에서 15분 동안")).toBe(true);
    expect(all[5][1].title).toBe("💤 총괄 창이 조용합니다");
    expect(all[5][1].body.includes("5분 동안")).toBe(true);
    expect(all[5][1].body.includes("알림 기준은 5분입니다")).toBe(true); // agy 3R MAJOR — 기준 시간 보존
    expect(masterIdleCopy(1, "master", { idle_secs: 320 }).body.includes("알림 기준")).toBe(false);
  });
  it("⑤ 사망 = ❌ 유지 · 무엇이 멈췄나 + 안심 문장(창·폴더 그대로) + 행동", () => {
    const c = all[6][1];
    expect(c.title.startsWith("❌")).toBe(true);
    expect(c.body.includes("4번 작업 창의 AI가 종료됐습니다")).toBe(true);
    expect(c.body.includes("창과 작업 폴더는 그대로 남아 있습니다")).toBe(true);
  });
  it("deadman = 🚨 · 축별 사람 말 · 모르는 축은 데몬 사유 원문(사실 보존)", () => {
    expect(all[7][1].title).toBe("🚨 총괄 창 응답 없음");
    expect(all[7][1].body.includes("창의 AI가 꺼졌습니다")).toBe(true);
    expect(deadmanCopy(1, { role: "master", axis: "new_axis", reason: "brand new reason" }).body.includes("brand new reason")).toBe(true);
    for (const ax of ["surface_gone", "surface_exited", "shell_proc_dead", "agent_dead", "seat_vacant_no_meta", "agent_never_started"])
      expect(deadmanCopy(1, { axis: ax, reason: "RAW" }).body.includes("RAW")).toBe(false);
  });
  it("자리 이동 · 폴더 권한", () => {
    expect(all[8][1].title).toBe("ℹ 총괄 자리가 다른 창으로 옮겨졌습니다");
    expect(all[8][1].body.startsWith("7번 창이 비어")).toBe(true);
    expect(all[9][1].body.includes("/Users/u/Documents/x 폴더를")).toBe(true);
    expect(all[9][1].body.includes("「문서 폴더」")).toBe(true);
  });
});

describe("D4 #8 도우미", () => {
  it("seatNo — surface_id 우선 · 없으면 surface_ref", () => {
    expect(seatNo(3, "surface:9")).toBe(3);
    expect(seatNo(undefined, "surface:9")).toBe(9);
    expect(seatNo(null, null)).toBe(null);
  });
  it("seatName · durText", () => {
    expect(seatName(3, "reviewer-codex")).toBe("3번 검토 창");
    expect(seatName(3, null)).toBe("3번 창");
    expect(seatName(null, null)).toBe("한 창");
    expect(durText(45)).toBe("45초");
    expect(durText(3700)).toBe("1시간 1분");
    expect(durText(7200)).toBe("2시간");
  });
});

describe("D4 #8 배선 — 경보 처리부가 원문을 조립하지 않는다", () => {
  const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  const ev = main.slice(main.indexOf("function onDaemonEvent("), main.indexOf('if (name === "status.changed" || name === "task.changed")'));
  it("대상 9종이 문구 모듈을 쓴다", () => {
    for (const f of ["approvalRequestCopy(", "approvalStalledCopy(", "contextThresholdCopy(", "roleTakeoverCopy(", "seatFolderDeniedCopy(", "paneIdleCopy(", "masterIdleCopy(", "agentExitedCopy(", "deadmanCopy("])
      expect(ev.includes(f)).toBe(true);
  });
  it("surface:${…} · payload.action · 「에이전트 사망」·「master 유휴」 원문 조립 0", () => {
    expect(ev.includes("surface:${")).toBe(false);
    expect(ev.includes("payload.action")).toBe(false);
    expect(ev.includes("에이전트 사망")).toBe(false);
    expect(ev.includes("master 유휴")).toBe(false);
  });
});
