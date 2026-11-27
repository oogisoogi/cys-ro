// (TICKET=cysr-1121-ui-kfix2) 통합 codex 3R REVISE(cysr-1121-integ-K-r3-codex.json) 남은 major 4건 — 재현 시험(고치기 전 붉음 · 고친 뒤 초록).
//   ① readSettled 가 「파일 끝까지 읽음」만으로 온전 확인을 인정 — 시작점 다시 잡기(none→ok · reset · rebind)·skipped_bytes 로 건너뛴 구간의 남의 차례를 못 보고 10분 넘은 말을 자동 제출.
//   ② 쓰였는지 모르는(unsure) 말이 내부 단계 delivered → 같은 말 겹침 판정이 미해결로 안 셈 → 같은 글 다시 쓰기.
//   ②′ 「확인 못 함」이 진행 줄·흡수 안내·같은 글 전달 안내엔 안 나옴(거짓 안심).
//   신규 — 10분 넘은 말의 기록 확인이 끝나지 않으면 writing 을 쥔 채 멈춰 뒤 말이 전부 줄 섬.
// 새 이름(viewStep·absorbedNote·AGED_READ_MAX_MS)은 이름공간으로 읽는다 — 고치기 전에도 파일이 읽혀 시험마다 붉음이 따로 보이게.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import * as C from "./core";
import * as MS from "./judge/msgstep";
import * as PG from "./judge/progress";
import type { Deps } from "./core";
import type { Msg, Rec } from "./judge/msgstep";

const { ChatCore, HELD_MAX_AGE_MS, STALE, DUP, dupPending, sameTextDelivered } = C;
const { applyRecords, STEP_LABEL, UNSURE_LABEL, ABSORBED_NOTE, WITH_NEXT_NOTE } = MS;
const AGED_READ_MAX_MS = (C as unknown as { AGED_READ_MAX_MS?: number }).AGED_READ_MAX_MS ?? 3_000;
const viewStep = (m: Msg): string => (MS as unknown as { viewStep?: (m: Msg) => string }).viewStep?.(m) ?? m.step;
const absorbedNote = (m: Msg): string | null =>
  (MS as unknown as { absorbedNote?: (m: Msg) => string | null }).absorbedNote?.(m) ?? (m.withNext ? WITH_NEXT_NOTE : m.absorbed ? ABSORBED_NOTE : null);
const iso = (ms: number) => new Date(ms).toISOString();
const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const tick = () => new Promise<void>((r) => setTimeout(r, 0));
const ticks = async (n = 20) => {
  for (let i = 0; i < n; i++) await tick();
};

/** 데몬 흉내(kfix1121 harness + 기록 없음 · 건너뜀 · 끝나지 않는 읽기 · 시각 상한 타이머) */
function harness(o: { approvals?: number[]; outcomes?: string[]; none?: boolean ; agedAutoSend?: boolean } = {}) {
  const calls: Array<{ cmd: string; args?: Record<string, unknown> }> = [];
  const mem = new Map<string, string>();
  const outs = [...(o.outcomes ?? [])];
  let now = 5_000_000;
  let seq = 3;
  let hid = 0;
  const timers = new Map<number, { fn: () => void; ms: number }>();
  const st = { approvals: o.approvals ?? [], sid: 5, file: [] as Array<Record<string, unknown>>, none: o.none ?? false, skipNext: false, hang: false, orgHook: null as null | (() => Promise<void>) };
  const stamp = () => `1795:${seq}`;
  const row = () => ({ surface_id: st.sid, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false, human_input_stamp: stamp() });
  const deps: Deps = {
    agedAutoSend: o.agedAutoSend, // (1.1.21 B안) 생략 = 끔
    invoke: async (cmd, args) => {
      calls.push({ cmd, args });
      if (cmd === "org_status") {
        if (st.orgHook) {
          const f = st.orgHook;
          st.orgHook = null;
          await f(); // 재조회가 걸린 사이에 일어나는 일(시험이 정함)
        }
        return { surfaces: [row()] };
      }
      if (cmd === "feed_list") return { items: st.approvals.map((sid) => ({ kind: "approval", status: "pending", surface_id: sid })) };
      if (cmd === "chat_send") {
        const oc = outs.shift() ?? "written";
        if (oc === "held" || oc === "failed") return { outcome: oc, code: oc === "failed" ? "send_failed" : "approval_open" };
        seq += 1;
        return { outcome: oc, result: { sent: true, human_input_stamp: stamp() } };
      }
      if (cmd === "chat_transcript") {
        const a = (args ?? {}) as { afterOffset?: number; fromEnd?: boolean };
        if (st.none) return { status: "none" };
        if (a.fromEnd) return { status: "ok", session_id: "s-k", next_offset: st.file.length, size: st.file.length, records: [] };
        if (st.hang) return new Promise(() => {}); // 끝나지 않는 기록 RPC
        if (st.skipNext) {
          st.skipNext = false; // 2 MiB 넘는 줄을 건너뛰었다(그 줄 = 남의 차례일 수 있음)
          return { status: "ok", session_id: "s-k", next_offset: st.file.length, size: st.file.length, records: [], skipped_bytes: 4096 };
        }
        return { status: "ok", session_id: "s-k", next_offset: st.file.length, size: st.file.length, records: st.file.slice(a.afterOffset ?? 0) };
      }
      return null;
    },
    now: () => now,
    setTimeout: (fn: () => void, ms: number) => {
      const id = ++hid;
      timers.set(id, { fn, ms });
      return id;
    },
    clearTimeout: (id: unknown) => void timers.delete(id as number),
    store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v), remove: (k) => void mem.delete(k) },
    working: (r) => r.working === true,
  } as Deps;
  const core = new ChatCore(deps);
  core.attach();
  return {
    core,
    st,
    writes: () => calls.filter((c) => c.cmd === "chat_send"),
    setNow: (t: number) => void (now = t),
    getNow: () => now,
    /** 이 길이(ms)로 건 타이머만 지금 터뜨린다(다른 상한 타이머는 그대로). */
    fire: (ms: number) => {
      for (const [id, t] of [...timers]) if (t.ms === ms) {
        timers.delete(id);
        t.fn();
      }
    },
  };
}

const ORIG = "그 파일 지워 줘";
const foreignUser = (h: ReturnType<typeof harness>) => ({ uuid: "f1", parent: null, role: "user", text: "RC 로 친 다른 지시", ts: iso(h.getNow() + 1_000) });
async function aged(h: ReturnType<typeof harness>) {
  h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
  h.st.approvals = [];
  await h.core.poll();
}

describe("① 10분 넘은 말 — 건너뛴 기록 구간이 있으면 온전 확인 아님(클릭)", () => {
  it("기록 없음(none) 동안 붙잡음 → 파일이 생기며 시작점이 끝으로 잡혀 남의 차례를 건너뜀 → 클릭", async () => {
    const h = harness({ approvals: [5], none: true });
    await h.core.poll();
    await h.core.send(ORIG);
    expect(h.writes()).toHaveLength(0);
    h.st.none = false;
    h.st.file.push(foreignUser(h)); // 시작점(파일 끝) 앞에 있어 영영 안 읽힘
    await aged(h);
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("붙잡은 뒤 reset(파일 바뀜) → 끝에서 다시 시작 = 그 사이 남의 차례 건너뜀 → 클릭", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.setNow(h.getNow() + 1_000); // 받아들인 뒤(실제 순서)
    h.st.file.push(foreignUser(h));
    await h.core.readTranscript("reset");
    await aged(h);
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("붙잡은 뒤 rebind(결속 바뀜) → 끝에서 다시 시작 → 클릭", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.setNow(h.getNow() + 1_000); // 받아들인 뒤(실제 순서)
    h.st.file.push(foreignUser(h));
    await h.core.readTranscript("rebind");
    await aged(h);
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("붙잡은 뒤 읽기가 큰 줄을 건너뜀(skipped_bytes) → 클릭", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.setNow(h.getNow() + 1_000); // 받아들인 뒤(실제 순서)
    h.st.file.push(foreignUser(h));
    h.st.skipNext = true;
    await h.core.readTranscript("event");
    await aged(h);
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("기록 확인(readSettled)은 통과했으나 쓰기 직전 재조회 사이에 reset → 쓰기 직전에 다시 재서 클릭", async () => {
    const h = harness({ agedAutoSend: true,  approvals: [5] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    let n = 0;
    const arm = () => {
      h.st.orgHook = async () => {
        if (++n < 2) return arm(); // 첫 재조회 = poll · 둘째 = deliver 의 쓰기 직전 재조회(readSettled 뒤)
        h.st.file.push(foreignUser(h));
        await h.core.readTranscript("reset");
      };
    };
    arm();
    await h.core.poll();
    expect(n).toBeGreaterThanOrEqual(2);
    expect(h.writes()).toHaveLength(0);
    expect(h.core.state.msgs[0].code).toBe(STALE);
  });
  it("대조군 — reset 이 말을 받아들이기 **전**이고 그 뒤 빠짐없이 읽힘 → 10분 넘어도 자동(표지)", async () => {
    const h = harness({ agedAutoSend: true,  approvals: [5] });
    await h.core.poll();
    await h.core.readTranscript("reset");
    h.setNow(h.getNow() + 10_000);
    await h.core.send(ORIG);
    await aged(h);
    expect(h.writes().map((c) => c.args?.text)).toEqual([`(10분 전에 쓰신 말) ${ORIG}`]);
  });
});

describe("신규 — 10분 넘은 말의 기록 확인이 끝나지 않음 → 그 말만 클릭 · 뒤 말은 막히지 않음", () => {
  it("기록 RPC 가 끝나지 않음 → 상한 뒤 클릭 대기 · 뒤에 친 말은 바로 나감", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    h.st.hang = true;
    void h.core.poll();
    await ticks();
    h.fire(AGED_READ_MAX_MS);
    await ticks();
    expect(h.core.state.msgs[0].code).toBe(STALE);
    expect(h.writes()).toHaveLength(0);
    void h.core.send("다른 말");
    await ticks();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["다른 말"]);
  });
  it("앞서 시작한 읽기가 끝나지 않음(겹친 읽기) → 상한 뒤 클릭 대기 · 뒤 말 나감", async () => {
    const h = harness({ approvals: [5] });
    await h.core.poll();
    await h.core.send(ORIG);
    h.st.hang = true;
    void h.core.readTranscript("event"); // 끝나지 않는 읽기가 잠금을 쥠
    await ticks();
    h.setNow(h.getNow() + HELD_MAX_AGE_MS + 1);
    h.st.approvals = [];
    void h.core.poll();
    await ticks();
    h.fire(AGED_READ_MAX_MS);
    await ticks();
    expect(h.core.state.msgs[0].code).toBe(STALE);
    void h.core.send("다른 말");
    await ticks();
    expect(h.writes().map((c) => c.args?.text)).toEqual(["다른 말"]);
  });
});

describe("② 확인 못 함 = 같은 말 겹침에서도 미해결(같은 글 두 번 쓰기 0)", () => {
  const T = "배포 멈춰";
  const unsureDelivered = (o: Partial<Msg> = {}): Msg => ({ id: "m1", text: T, createdAt: 1_000, sentAt: 1_000, step: "delivered", userUuid: "u1", thread: ["u1"], replies: [], unsure: true, note: MS.UNSURE_NOTE, ...o } as Msg);
  it("순수: 확인 못 함(delivered·replying·replied·accepted) = dupPending 참 · sameTextDelivered 거짓", () => {
    for (const step of ["delivered", "replying", "replied", "accepted"] as const) {
      const m = unsureDelivered({ step });
      expect(dupPending([m], T)).toBe(true);
      expect(sameTextDelivered([m], T)).toBe(false);
      expect(viewStep(m)).toBe("unsure");
    }
  });
  it("화면 길: 불명 제출 → 다른 길 같은 글 user → 같은 글 다시 침 → 쓰기 1회뿐(DUP 붙잡음) · 「한 번 더 보내기」도 막힘", async () => {
    const h = harness({ outcomes: ["uncertain"] });
    await h.core.poll();
    await h.core.send(T);
    h.st.file.push({ uuid: "u9", parent: null, role: "user", text: T, ts: iso(h.getNow() + 500) });
    await h.core.readTranscript("event");
    expect((h.core.state.msgs[0] as Msg).unsure).toBe(true);
    await h.core.send(T);
    expect(h.writes()).toHaveLength(1);
    const dup = h.core.state.msgs[1];
    expect(dup.code).toBe(DUP);
    expect(dup.note).toBe((C as unknown as { DUP_UNSURE_NOTE?: string }).DUP_UNSURE_NOTE); // 「앞 말이 끝나면」 약속 0(확인 못 함은 저절로 안 끝남)
    await h.core.confirmHeld(dup.id);
    expect(h.writes()).toHaveLength(1);
    expect(h.core.state.notice).toBe((C as unknown as { DUP_UNSURE_NOTICE?: string }).DUP_UNSURE_NOTICE);
  });
  it("겹친 말을 만든 뒤 앞 말이 「확인 못 함」이 됨 → 보이는 안내도 확인 못 함 문구(「앞 말이 끝나면」 약속 0) · 화면 배선 = shownNote", async () => {
    const shown = (C as unknown as { shownNote?: (a: readonly Msg[], m: Msg) => string | undefined }).shownNote ?? ((_a: readonly Msg[], m: Msg) => m.note);
    const h = harness({ outcomes: ["uncertain"] });
    await h.core.poll();
    await h.core.send(T);
    await h.core.send(T); // 앞 말 = 아직 확인 중(unsure 아님) → 겹침 안내는 「앞 말이 끝나면」
    const dupId = h.core.state.msgs[1].id;
    expect(h.core.state.msgs[1].code).toBe(DUP);
    h.st.file.push({ uuid: "u9", parent: null, role: "user", text: T, ts: iso(h.getNow() + 500) });
    await h.core.readTranscript("event");
    const msgs = h.core.state.msgs;
    expect(viewStep(msgs[0])).toBe("unsure");
    expect(shown(msgs, msgs.find((x) => x.id === dupId) as Msg)).toBe((C as unknown as { DUP_UNSURE_NOTE?: string }).DUP_UNSURE_NOTE);
    const CHAT = strip(readFileSync(new URL("./chat/index.ts", import.meta.url), "utf8"));
    expect(CHAT).toContain("const note = shownNote(s.msgs, m);");
  });
  it("대조군 — 데몬이 썼다고 답한(written) 말 뒤 같은 글 = 새 말로 나감(겹침 아님)", async () => {
    const h = harness();
    await h.core.poll();
    await h.core.send(T);
    h.st.file.push({ uuid: "u9", parent: null, role: "user", text: T, ts: iso(h.getNow() + 500) });
    await h.core.readTranscript("event");
    await h.core.send(T);
    expect(h.writes()).toHaveLength(2);
  });
});

describe("②′ 확인 못 함 = 진행 줄·흡수 안내·말풍선 꼴까지 같은 이름(거짓 안심 0)", () => {
  const base = (o: Partial<Msg>): Msg => ({ id: "m1", text: "x", createdAt: 1_000, sentAt: 1_000, step: "accepted", thread: [], replies: [], unsure: true, ...o } as Msg);
  it("받아 둠(accepted)+확인 못 함 → 진행 줄 = 「확인 못 함」 · 「받아 둠」 이름 0", () => {
    const p = PG.progressLine(base({}), 20_000, true);
    expect(p?.text.startsWith(UNSURE_LABEL)).toBe(true);
    expect(p?.text).not.toContain(STEP_LABEL.accepted);
  });
  it("전달됨(delivered)+확인 못 함 · 단계 0 → 진행 줄 = 「확인 못 함」 · 「전달됨」 0", () => {
    const p = PG.progressLine(base({ step: "delivered" }), 20_000, true);
    expect(p?.text.startsWith(UNSURE_LABEL)).toBe(true);
    expect(p?.text).not.toContain(STEP_LABEL.delivered);
  });
  it("답하는 중+확인 못 함 + 단계 있음 → 진행 줄 머리에 「확인 못 함」", () => {
    const steps = [{ kind: "tool", label: "파일 읽음", hint: null, at: 5_000 }] as unknown as NonNullable<Msg["steps"]>;
    for (const summary of [true, false]) {
      const p = PG.progressLine(base({ step: "replying", steps }), 20_000, true, { summary });
      expect(p?.text.startsWith(UNSURE_LABEL)).toBe(true);
    }
  });
  it("대조군 — 확인된 말(unsure 없음)은 종전 그대로", () => {
    expect(PG.progressLine(base({ unsure: undefined }), 20_000, true)?.text.startsWith(STEP_LABEL.accepted)).toBe(true);
  });
  it("흡수·함께 읽힘 안내 — 확인 못 함이면 「받아 읽었어요」 단정 0 · 확인된 말은 종전 문구", () => {
    const a = absorbedNote(base({ step: "delivered", absorbed: true }));
    const w = absorbedNote(base({ step: "delivered", absorbed: true, withNext: "m2" }));
    for (const n of [a, w]) {
      expect(n).not.toBeNull();
      expect(n).not.toBe(ABSORBED_NOTE);
      expect(n).not.toBe(WITH_NEXT_NOTE);
      expect(n as string).toContain("확인할 수 없");
    }
    expect(absorbedNote(base({ step: "delivered", absorbed: true, unsure: undefined }))).toBe(ABSORBED_NOTE);
    expect(absorbedNote(base({ step: "delivered", absorbed: true, withNext: "m2", unsure: undefined }))).toBe(WITH_NEXT_NOTE);
  });
  it("화면 배선 — 말풍선 꼴·data-step·흡수 안내 = viewStep·absorbedNote 한 곳", () => {
    const CHAT = strip(readFileSync(new URL("./chat/index.ts", import.meta.url), "utf8"));
    expect(CHAT).toContain("cv-msg cv-me step-${viewStep(m)}");
    expect(CHAT).toContain("meta.dataset.step = viewStep(m)");
    expect(CHAT).toContain("absorbedNote(m)");
    expect(CHAT).not.toContain("ABSORBED_NOTE");
  });
});
