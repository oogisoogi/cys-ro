// (TICKET=cysr-1119-s4) 1.1.19 과정 요약 — CH-D(progressSummary · 진행 줄 머리) · F25(상한 자를 때 분류별 버린 수) · F34(분류 = 도구 이름 표) · V4(18px) · V4c(경과 3초 문턱).
// 정본 = review/1119-DESIGN.md §3-2 F25·F34 · §6 V4·V4c · review/P3-CHAT-1119-DESIGN.v4.md §3-5 D · T-U4 · 판정 [master#70cce152](글 단계 = 셈만 · 요약 글에서 숨김 · PowerShell→명령 · MultiEdit→고침).
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { appendStepsTo, classCounts, PROG_MAX, progressLine, progressSummary, stepClass, stepsOf, type ProgClass, type ProgStep } from "./judge/progress";
import type { Msg, Rec } from "./judge/msgstep";
import { liveMsg } from "./judge/progress";
import { Sim } from "./testkit";

const rec = (o: Partial<Rec>): Rec => ({ uuid: "a", parent: "u", role: "assistant", text: null, ts: "2026-11-23T01:02:03.000Z", ...o });
const tool = (name: string): ProgStep[] => stepsOf(rec({ tools: [{ name, hint: null }] }));
const sum = (c: Partial<Record<ProgClass, number>>) => Object.values(c).reduce((a, b) => a + (b ?? 0), 0);
const msg = (o: Partial<Msg>): Msg => ({ id: "m", text: "안녕", createdAt: 0, sentAt: 0, step: "replied", thread: [], replies: [], ...o });

/** 실기록 9구간 — 2026-11-24 이 기기 Claude Code 세션 기록(jsonl)에서 사람 말 하나 뒤 마스터 레코드들을 채록.
 *  레코드마다 [도구 이름들, 글 있음(1/0), 생각 조각(1/0)] 만 담았다(본문·단서 0 · mcp 도구 이름 = mcp__srv__tool 로 가림). */
const REAL: Array<Array<[string[], number, number]>> = [
  [[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Artifact"],0,0],[[],1,0],[["Artifact"],0,0],[[],0,1],[["mcp__srv__tool"],0,0],[["Read"],0,0],[[],0,1],[["mcp__srv__tool"],0,0],[[],1,0],[["mcp__srv__tool"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["mcp__srv__tool"],0,0],[[],1,0],[["Monitor"],0,0],[["mcp__srv__tool"],0,0],[[],0,1],[["Bash"],0,0],[["ListAgents"],0,0],[[],0,1],[["Read"],0,0],[["ToolSearch"],0,0],[["SendMessage"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["ToolSearch"],0,0],[["SendUserFile"],0,0],[["Bash"],0,0],[[],1,0]],
  [[[],0,1],[["Bash"],0,0],[["Read"],0,0],[["Read"],0,0],[[],0,1],[["Read"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["ToolSearch"],0,0],[[],0,1],[[],1,0],[["CronList"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Monitor"],0,0],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Agent"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],1,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[[],1,0]],
  [[[],0,1],[["Bash"],0,0],[["Read"],0,0],[["Read"],0,0],[[],0,1],[["Read"],0,0],[[],0,1],[["Bash"],0,0],[["ToolSearch"],0,0],[[],0,1],[["CronList"],0,0],[["Bash"],0,0],[[],0,1],[[],0,1],[["Bash"],0,0],[["Read"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[[],1,0],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],1,0],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["ToolSearch"],0,0],[["TaskStop"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Monitor"],0,0],[[],1,0]],
  [[[],0,1],[["Bash"],0,0],[[],0,1],[["ToolSearch"],0,0],[["Bash"],0,0],[[],0,1],[["CronCreate"],0,0],[["CronCreate"],0,0],[["CronCreate"],0,0],[["CronCreate"],0,0],[["CronCreate"],0,0],[["Monitor"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],1,0],[["Agent"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Agent"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[[],1,0],[["Bash"],0,0],[["SendMessage"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],1,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[[],1,0]],
  [[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Read"],0,0],[[],0,1],[["Edit"],0,0],[["Edit"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Read"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["ToolSearch"],0,0],[["SendUserFile"],0,0],[[],1,0]],
  [[["Read"],0,0],[[],0,1],[[],1,0],[["Bash"],0,0],[[],0,1],[[],0,1],[["ToolSearch"],0,0],[["TaskStop"],0,0],[["Bash"],0,0],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Edit"],0,0],[[],0,1],[["Bash"],0,0],[[],1,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],1,0],[["Bash"],0,0],[[],1,0],[["Bash"],0,0],[[],0,1],[[],1,0],[["Bash"],0,0],[["Bash"],0,0],[[],1,0]],
  [[[],0,1],[["Bash"],0,0],[["Read"],0,0],[["Read"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["ListAgents"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["ToolSearch"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[[],1,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[[],1,0],[["Write"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],1,0],[["Bash"],0,0],[[],1,0],[["Bash"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[[],1,0]],
  [[[],0,1],[["Bash"],0,0],[["ToolSearch"],0,0],[["mcp__srv__tool"],0,0],[[],0,1],[["mcp__srv__tool"],0,0],[["Bash"],0,0],[["Read"],0,0]],
  [[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[["Read"],0,0],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],0,1],[["Bash"],0,0],[[],1,0],[["Bash"],0,0],[["ToolSearch"],0,0],[["Monitor"],0,0],[["Bash"],0,0],[[],1,0]],
];
const realRecs = (seg: Array<[string[], number, number]>): Rec[] =>
  seg.map(([tools, text, think], i) => rec({ uuid: `r${i}`, text: text ? "글" : null, thinking: think === 1, tools: tools.map((name) => ({ name, hint: null })) }));

describe("F34 분류 = 도구 이름 표(TOOL_CLASS) · 표시 문구와 무관", () => {
  it("표의 도구 전부 · 생각 · 글 · 모르는 도구 · mcp 도구가 칸 안(그 밖 포함)", () => {
    const want: Array<[string, ProgClass]> = [
      ["Read", "read"], ["Glob", "find"], ["Grep", "find"], ["Bash", "cmd"], ["PowerShell", "cmd"],
      ["Edit", "edit"], ["MultiEdit", "edit"], ["Write", "edit"], ["NotebookEdit", "edit"], ["Task", "agent"], ["Agent", "agent"],
      ["WebSearch", "web"], ["WebFetch", "web"], ["TodoWrite", "plan"], ["mcp__claude-in-chrome__navigate", "other"], ["Monitor", "other"],
    ];
    for (const [name, cls] of want) expect([name, stepClass(tool(name)[0])]).toEqual([name, cls]);
    expect(tool("Write")[0].tool).toBe("Write"); // 원 이름 칸
    expect(stepClass(stepsOf(rec({ thinking: true }))[0])).toBe("think");
    expect(stepClass(stepsOf(rec({ text: "답" }))[0])).toBe("text");
  });
  it("표시 문구 뮤턴트에 계수 불변 — 단계의 label 을 전부 바꿔도 분류 셈이 같다", () => {
    for (const seg of REAL) {
      const steps = realRecs(seg).flatMap(stepsOf);
      const relabeled = steps.map((s, i) => ({ ...s, label: `바뀐 문구 ${i}` }));
      expect(classCounts(relabeled)).toEqual(classCounts(steps));
    }
  });
});

describe("T-U4 progressSummary — 실기록 9구간", () => {
  it("분류 수 합 = 단계 목록 수 100% · 0 숨김 · 최대 3 · 많은 순 · 글 단계는 셈에만(요약 글 0)", () => {
    expect(REAL.length).toBe(9);
    for (const seg of REAL) {
      const steps = realRecs(seg).flatMap(stepsOf);
      expect(steps.length).toBeGreaterThan(0);
      const c = classCounts(steps);
      expect(sum(c)).toBe(steps.length); // 100%
      const s = progressSummary(steps);
      const parts = s === "" ? [] : s.split(" · ");
      expect(parts.length <= 3).toBe(true);
      const ns = parts.map((p) => Number(/ (\d+)번$/.exec(p)?.[1] ?? NaN));
      for (const n of ns) expect(n).toBeGreaterThan(0); // 0 숨김
      for (let i = 1; i < ns.length; i++) expect(ns[i] <= ns[i - 1]).toBe(true); // 많은 순
      expect(s.includes("글")).toBe(false); // [master#70cce152] ⓐ
    }
  });
  it("글자 그대로: 읽기 3 · 찾기 2 · 명령 2 · 고침 1 → 최대 3(같은 수 = 표 순서) · 「N번」", () => {
    const steps = [...tool("Read"), ...tool("Grep"), ...tool("Read"), ...tool("Bash"), ...tool("Glob"), ...tool("Edit"), ...tool("Bash"), ...tool("Read"), ...stepsOf(rec({ text: "답" }))];
    expect(progressSummary(steps)).toBe("읽기 3번 · 찾기 2번 · 명령 2번");
    expect(progressSummary([...tool("WebFetch"), ...tool("TodoWrite"), ...tool("Agent"), ...tool("Monitor")])).toBe("도우미 1번 · 웹 찾기 1번 · 계획 1번");
    expect(progressSummary(stepsOf(rec({ thinking: true })))).toBe("생각 1번");
    expect(progressSummary(stepsOf(rec({ text: "답만" })))).toBe("");
    expect(progressSummary([])).toBe("");
  });
});

describe("F25 상한 자를 때 분류별 버린 수 보존", () => {
  it("단계 250 → 남은 200 + 버린 수 · 분류 합 = 250 · 분류마다 입력과 같음", () => {
    const owner: { steps?: ProgStep[]; stepsDropped?: Partial<Record<ProgClass, number>> } = {};
    const input: ProgStep[] = [];
    for (let i = 0; i < 250; i++) {
      const add = i % 5 === 0 ? stepsOf(rec({ text: `글 ${i}` })) : tool(["Read", "Grep", "Bash", "Edit"][i % 4]);
      input.push(...add);
      appendStepsTo(owner, add);
    }
    expect(owner.steps?.length).toBe(PROG_MAX);
    expect(sum(owner.stepsDropped ?? {})).toBe(250 - PROG_MAX);
    expect(sum(classCounts(owner.steps ?? [], owner.stepsDropped))).toBe(250);
    expect(classCounts(owner.steps ?? [], owner.stepsDropped)).toEqual(classCounts(input));
    expect(owner.steps?.[0]).toBe(input[50]); // 버린 것 = 앞 50
  });
  it("요약 = 남은 단계 + 버린 수(버린 읽기도 셈)", () => {
    const owner: { steps?: ProgStep[]; stepsDropped?: Partial<Record<ProgClass, number>> } = {};
    for (let i = 0; i < 150; i++) appendStepsTo(owner, tool("Read"));
    for (let i = 0; i < 100; i++) appendStepsTo(owner, tool("Bash"));
    expect(progressSummary(owner.steps ?? [], owner.stepsDropped)).toBe("읽기 150번 · 명령 100번");
    expect(progressSummary(owner.steps ?? [])).toBe("읽기 100번 · 명령 100번"); // 대조: 버린 수를 안 넣으면 틀린 셈(읽기 50 빠짐)
  });
});

describe("CH-D 진행 줄 머리 · V4c 경과 3초 문턱", () => {
  const at = (ms: number) => new Date(ms).toISOString();
  const stepsAt = (ms: number, ...names: string[]) => names.flatMap((n) => stepsOf(rec({ ts: at(ms), tools: [{ name: n, hint: "x" }] })));
  it("끝난 말 = 「요약 · 걸린 시간」(마지막 단계 시각 − 보낸 시각) · 요약이 비면 경과만", () => {
    const steps = [...stepsAt(10_000, "Read", "Read", "Read", "Grep", "Grep", "Bash", "Bash"), ...stepsAt(80_000, "Edit")];
    expect(progressLine(msg({ steps }), 999_999, false)).toEqual({ text: "읽기 3번 · 찾기 2번 · 명령 2번 · 1분 20초", live: false });
    const textOnly = stepsOf(rec({ ts: at(12_000), text: "답" }));
    expect(progressLine(msg({ steps: textOnly }), 999_999, false)?.text).toBe("12초");
  });
  it("끝난 말 · 걸린 시간 모름/3초 미만 · 요약 빔 = 「과정 보기」(펼침 단추가 남게) · 단계 0 = 없음", () => {
    expect(progressLine(msg({ steps: stepsOf(rec({ ts: at(2_000), text: "답" })) }), 9_999, false)?.text).toBe("과정 보기");
    expect(progressLine(msg({ steps: stepsOf(rec({ ts: null, text: "답" })) }), 9_999, false)?.text).toBe("과정 보기");
    expect(progressLine(msg({ steps: stepsAt(2_000, "Read") }), 9_999, false)?.text).toBe("읽기 1번");
    expect(progressLine(msg({ steps: [] }), 9_999, false)).toBeNull();
  });
  it("답하는 중 = 「요약 · 경과 · 지금: <단계>」(P3 U3 꼴) · 도구 0 = 1.1.18 꼴(단계 · 단서 · 경과)", () => {
    const live = msg({ step: "replying", steps: stepsAt(1_000, "Read", "Read", "Bash") });
    expect(progressLine(live, 130_000, true)).toEqual({ text: "읽기 2번 · 명령 1번 · 2분 10초 · 지금: 명령 실행 중", live: true });
    const textLive = msg({ step: "replying", steps: stepsOf(rec({ ts: at(1_000), text: "안녕하세요 박사님" })) });
    expect(progressLine(textLive, 12_000, true)?.text).toBe("답 쓰는 중 · 안녕하세요 박사님 · 12초");
    expect(progressLine(msg({ step: "injected", steps: undefined }), 12_000, true)?.text).toBe("전달 확인 중 · 12초");
  });
  it("V4c — 2.9초 = 단계 글만 · 3.0초 = 「· 3초」(요약 줄도 같음)", () => {
    expect(progressLine(msg({ step: "injected" }), 2_900, true)?.text).toBe("전달 확인 중");
    expect(progressLine(msg({ step: "injected" }), 3_000, true)?.text).toBe("전달 확인 중 · 3초");
    const live = msg({ step: "replying", steps: stepsAt(500, "Read") });
    expect(progressLine(live, 2_999, true)?.text).toBe("읽기 1번 · 지금: 파일 읽는 중");
    expect(progressLine(live, 3_000, true)?.text).toBe("읽기 1번 · 3초 · 지금: 파일 읽는 중");
  });
  it("되돌리기 연결점 summary:false = 1.1.18 머리(「과정 N단계」 · 단계 · 단서 · 경과)", () => {
    const steps = [...stepsAt(1_000, "Read", "Bash"), ...stepsOf(rec({ ts: at(5_000), text: "답" }))];
    expect(progressLine(msg({ steps }), 99_000, false, { summary: false })?.text).toBe("과정 3단계");
    expect(progressLine(msg({ step: "replying", steps: stepsAt(1_000, "Bash") }), 12_000, true, { summary: false })?.text).toBe("명령 실행 중 · x · 12초");
  });
});

describe("V4 진행 줄 글자 18px", () => {
  it("views.css .cv-prog = font-size 18px(.86em 17.2px 아님) · 진행 줄 안쪽 규칙에 더 작은 글자 0", () => {
    const css = readFileSync(new URL("./views.css", import.meta.url), "utf8");
    const rule = /\.cv-prog \{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(rule).toContain("font-size: 18px;");
    // 진행 줄 안쪽(.cv-prog-* · .cv-steps · .cv-stepi-*) 규칙은 글자를 따로 정하지 않는다(= 18px 를 물려받음)
    const inner = [...css.matchAll(/^(\.cv-prog[\w.-]*|\.cv-steps|\.cv-stepi[\w-]*)[^{\n]*\{([^}]*)\}/gm)].filter((m) => m[1] !== ".cv-prog");
    expect(inner.length).toBeGreaterThan(5);
    expect(inner.filter((m) => /font-size/.test(m[2])).map((m) => m[1])).toEqual([]);
  });
});

describe("CH-D 실제 ChatCore 위(가짜 세션 기록 · 1초 박자)", () => {
  it("답하는 중 줄이 요약 꼴로 바뀐다 · 처음 2초는 경과 없음 · 끝난 뒤 요약 + 걸린 시간", async () => {
    const sim = new Sim({ recordDelay: () => 100, replyDelay: () => 12_500, toolSteps: [{ name: "Read", hint: "core.ts" }, { name: "Grep", hint: "x" }, { name: "Bash", hint: "시험" }], toolGapMs: 3_000 });
    sim.core.attach();
    await sim.flush();
    await sim.core.poll();
    await sim.flush();
    sim.startPolling();
    sim.core.submit("설명해줘");
    const lines: string[] = [];
    for (let t = 0; t < 12_000; t += 1_000) {
      await sim.advance(1_000);
      const m = liveMsg(sim.core.state.msgs);
      lines.push(m ? (progressLine(m, sim.now, true)?.text ?? "") : "");
    }
    expect(lines[0]).not.toMatch(/초/); // 1초 = V4c
    expect(lines.some((l) => /^읽기 1번 · \d+초 · 지금: 파일 읽는 중$/.test(l))).toBe(true);
    expect(lines.some((l) => /^읽기 1번 · 찾기 1번 · 명령 1번 · \d+초 · 지금: 명령 실행 중$/.test(l))).toBe(true);
    await sim.advance(12_000);
    const m = sim.core.state.msgs[0];
    expect(m.step).toBe("replied");
    expect(progressLine(m, sim.now, false)?.text).toMatch(/^읽기 1번 · 찾기 1번 · 명령 1번 · \d+초$/);
  });
});

// (TICKET=cysr-1119-integ1 · S4 HANDOFF ⑴ × S2 CH-E) 되돌리기 연결점 — 화면의 진행 줄 두 곳(prog · 1초 시계)이 ChatCore.compat1118 한 값을 넘긴다.
describe("integ1 S4×S2 되돌리기 연결", () => {
  const src = readFileSync(new URL("./chat/index.ts", import.meta.url), "utf8").replace(/\r\n/g, "\n");
  it("progressLine 호출 = 두 곳 · 둘 다 { summary: !act.compat1118 }", () => {
    const calls = src.split("\n").filter((l) => l.includes("progressLine(") && !l.trim().startsWith("import"));
    expect(calls.length).toBe(2);
    for (const l of calls) expect(l).toContain("{ summary: !act.compat1118 })");
  });
  it("compat 켬 = 요약 숨김 · 끔 = 요약 있음(같은 말)", () => {
    const m = msg({ step: "replied", steps: [...tool("Bash"), ...tool("Read")], repliedAt: 9_000 } as Partial<Msg>);
    const on = progressLine(m, 10_000, false, { summary: !true });
    const off = progressLine(m, 10_000, false, { summary: !false });
    expect(on?.text ?? "").not.toBe(off?.text ?? "");
  });
});
