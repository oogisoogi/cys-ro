// (TICKET=cysr-1118-ui ①) 대화 화면 진행 줄 — 해소 판정 「가짜 세션 기록에 tool_use 3건 → 진행 줄 3번 바뀜 · 경과 초 증가」.
// 대조군 = 도구 칸이 없는 옛 파서 꼴(toolsField:false) — 같은 기록에서 진행 줄이 도구마다 바뀌지 않는다(고치기 전 동작).
import { describe, expect, it } from "bun:test";
import { Sim } from "./testkit";
import { appendSteps, elapsedLabel, liveMsg, PROG_MAX, progressLine, stepsOf, toolLabel, type ProgStep } from "./judge/progress";
import { applyRecords, type Msg, type Rec } from "./judge/msgstep";

async function ready(sim: Sim): Promise<void> {
  sim.core.attach();
  await sim.flush();
  await sim.core.poll();
  await sim.flush();
}

const TOOLS = [
  { name: "Read", hint: "core.ts" },
  { name: "Grep", hint: "open_bound" },
  { name: "Bash", hint: "시험 돌리기" },
];

/** 1초마다 진행 줄을 찍는다(화면의 1초 시계와 같은 박자). */
async function trace(sim: Sim, ms: number): Promise<string[]> {
  const out: string[] = [];
  for (let t = 0; t < ms; t += 1_000) {
    await sim.advance(1_000);
    const m = liveMsg(sim.core.state.msgs) ?? sim.core.state.msgs[0];
    const p = m ? progressLine(m, sim.now, liveMsg(sim.core.state.msgs) === m) : null;
    out.push(p ? p.text : "");
  }
  return out;
}
const head = (line: string) => line.replace(/ · \d+(분 \d+)?초$/, "");
const secs = (line: string) => {
  const m = / · (?:(\d+)분 )?(\d+)초$/.exec(line);
  return m ? Number(m[1] ?? 0) * 60 + Number(m[2]) : null;
};
function changes(lines: string[]): string[] {
  const hs: string[] = [];
  for (const l of lines.map(head)) if (l && hs[hs.length - 1] !== l) hs.push(l);
  return hs;
}

describe("진행 줄 — 가짜 세션 기록(tool_use 3건)", () => {
  it("도구마다 진행 줄이 바뀐다(3번) · 경과 초가 늘어난다 · 답 뒤엔 접힌 「과정 N단계」", async () => {
    const sim = new Sim({ recordDelay: () => 100, replyDelay: () => 12_500, toolSteps: TOOLS, toolGapMs: 3_000 }); // 조회 3초 박자마다 도구 1건(한 창에 둘이면 머리줄은 뒤 것만 · 목록엔 둘 다)
    await ready(sim);
    sim.startPolling();
    sim.core.submit("이번 업데이트 설명해줘");
    const lines = await trace(sim, 12_000);
    const hs = changes(lines);
    const toolHeads = hs.filter((h) => /읽는 중|찾는 중|실행 중/.test(h));
    expect(toolHeads).toEqual(["파일 읽는 중 · core.ts", "찾는 중 · open_bound", "명령 실행 중 · 시험 돌리기"]);
    const ss = lines.map(secs).filter((x): x is number => x !== null);
    expect(ss.length).toBeGreaterThanOrEqual(11);
    for (let i = 1; i < ss.length; i++) expect(ss[i]).toBeGreaterThan(ss[i - 1]); // 경과 초 증가(1초마다)
    await sim.advance(12_000); // 답 + 쉼 → 답함
    const m = sim.core.state.msgs[0];
    expect(m.step).toBe("replied");
    expect(liveMsg(sim.core.state.msgs)).toBeNull();
    expect(progressLine(m, sim.now, false)?.text).toBe("과정 4단계"); // 도구 3 + 답 글 1
    expect((m.steps ?? []).map((s) => s.kind)).toEqual(["tool", "tool", "tool", "text"]);
    // NFR-S3: 화면 저장소에 단계·단서가 남지 않는다
    for (const v of sim.mem.values()) expect(v.includes("core.ts") || v.includes("open_bound")).toBe(false);
  });

  it("대조군(옛 파서 꼴 = tools 칸 없음): 같은 기록에서 진행 줄이 도구마다 바뀌지 않는다", async () => {
    const sim = new Sim({ recordDelay: () => 100, replyDelay: () => 12_500, toolSteps: TOOLS, toolGapMs: 3_000, toolsField: false });
    await ready(sim);
    sim.startPolling();
    sim.core.submit("이번 업데이트 설명해줘");
    const hs = changes(await trace(sim, 12_000));
    expect(hs.filter((h) => /읽는 중|찾는 중|실행 중/.test(h))).toEqual([]);
  });

  it("세션 기록을 못 읽는 자리(윈 옛 판 · unknown)에서도 단계 이름 + 경과는 나온다", async () => {
    const sim = new Sim({ recordDelay: () => 100, replyDelay: () => 20_000 });
    const orig = (sim.deps.invoke as (c: string, a?: Record<string, unknown>) => Promise<unknown>).bind(sim.deps);
    sim.deps.invoke = async (cmd, a) => (cmd === "chat_transcript" ? { status: "unknown", why: "unsupported_platform" } : orig(cmd, a));
    await ready(sim);
    sim.startPolling();
    sim.core.submit("안녕");
    const lines = await trace(sim, 5_000);
    const last = lines[lines.length - 1];
    expect(head(last)).toMatch(/^(전달 확인 중|확인 중)$/);
    expect(secs(last)).toBeGreaterThanOrEqual(4);
  });
});

describe("진행 줄 순수부", () => {
  const rec = (o: Partial<Rec>): Rec => ({ uuid: "a", parent: "u", role: "assistant", text: null, ts: "2026-11-23T01:02:03.000Z", ...o });
  it("레코드 → 단계: 글 = 답 쓰는 중(앞 40자) · 도구 = 진행형 · 생각만 = 생각하는 중 · user·sidechain = 없음", () => {
    expect(stepsOf(rec({ text: "가".repeat(50) }))[0]).toEqual({ kind: "text", label: "답 쓰는 중", hint: `${"가".repeat(40)}…`, at: Date.parse("2026-11-23T01:02:03.000Z") });
    expect(stepsOf(rec({ tools: [{ name: "Edit", hint: "a.rs" }, { name: "mcp__claude-in-chrome__navigate", hint: null }] })).map((s) => [s.label, s.hint])).toEqual([
      ["파일 고치는 중", "a.rs"],
      ["도구 쓰는 중 · navigate", null],
    ]);
    expect(stepsOf(rec({ thinking: true }))).toEqual([{ kind: "think", label: "생각하는 중", hint: null, at: Date.parse("2026-11-23T01:02:03.000Z") }]);
    expect(stepsOf(rec({ thinking: true, tools: [{ name: "Read", hint: "x" }] })).map((s) => s.kind)).toEqual(["tool"]);
    expect(stepsOf(rec({ role: "user", text: "사람" }))).toEqual([]);
    expect(stepsOf(rec({ sidechain: true, tools: [{ name: "Read", hint: "x" }] }))).toEqual([]);
    expect(toolLabel("Agent")).toBe("도우미에게 맡기는 중");
  });
  it("경과 표기 · 단계 상한 · 답이 다른 말로 넘어가면(확정 실패) 단계도 지움", () => {
    expect([elapsedLabel(-5), elapsedLabel(12_900), elapsedLabel(65_000), elapsedLabel(3_725_000)]).toEqual(["0초", "12초", "1분 5초", "1시간 2분"]);
    const many: ProgStep[] = Array.from({ length: PROG_MAX + 5 }, (_, i) => ({ kind: "tool", label: "x", hint: String(i), at: null }));
    const kept = appendSteps(undefined, many) as ProgStep[];
    expect(kept.length).toBe(PROG_MAX);
    expect(kept[0].hint).toBe("5");
  });
  it("applyRecords = 그 말의 사슬 위 마스터 레코드만 단계로(다른 사슬·사람 글은 안 붙음)", () => {
    const m: Msg = { id: "m1", text: "안녕", createdAt: 0, sentAt: 0, step: "injected", thread: [], replies: [] };
    const recs: Rec[] = [
      { uuid: "u1", parent: null, role: "user", text: "안녕", ts: null },
      { uuid: "a1", parent: "u1", role: "assistant", text: null, ts: null, tools: [{ name: "Read", hint: "x.ts" }] },
      { uuid: "z1", parent: "other", role: "assistant", text: null, ts: null, tools: [{ name: "Bash", hint: "남의 일" }] },
      { uuid: "a2", parent: "a1", role: "assistant", text: "답", ts: null },
    ];
    const r = applyRecords([m], recs);
    expect((r.msgs[0].steps ?? []).map((s) => s.hint)).toEqual(["x.ts", "답"]);
  });
});
