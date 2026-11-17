// (cysr-ui-slice4) 확인 대기 장부 시험 — 공통층(ChatCore + ConfirmBook) · 대역 데몬(invoke 기록기) · 가짜 시계.
// 판정 단위 = 「허락 집행 = confirm_reply 호출 수」(데몬 feed.reply · 처리 직전 재확인에 걸리면 0).
import { describe, it, expect } from "bun:test";
import { ChatCore, type Deps } from "./core";
import { DECISION_LOG_KEY, masterOf } from "./confirm";
import { ALLOW_AT_WORK_MSG, boundOf, CONFIRM_STALL_MS, RECORDED_ONLY_MSG, type FeedApproval } from "./judge/confirms";

const body = (cmd: string) => `Do you want to proceed?\n— 명령 원문:\n${cmd}\n— 읽기 전용 판정(기계 추정 · 근거 아님): 쓰기·삭제 가능`;
const A = (uuid: string, text: string) => ({ uuid, parent: null, role: "assistant", text, ts: null });

function harness(o: { prior?: Array<Record<string, unknown>>; chunk?: number } = {}) {
  const calls: Array<{ cmd: string; args?: Record<string, unknown> }> = [];
  const mem = new Map<string, string>();
  let now = 10_000_000;
  const listeners: Array<(ev: unknown) => void> = [];
  let listenCalls = 0;
  const st = {
    master: { surface_id: 5, role: "master", exited: false, agent_alive: true as boolean | null, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false, idle_secs: 1 },
    feed: [] as Array<Record<string, unknown>>,
    feedFail: false,
    file: [...(o.prior ?? [])] as Array<Record<string, unknown>>,
    session: "sess-0001",
    chunk: o.chunk ?? 1000,
    reply: null as null | ((args: Record<string, unknown>) => void),
    /** 데몬 feed.reply 결과(기본 = 창을 실제로 누름) */
    replyResult: null as null | Record<string, unknown>,
    /** org.status 응답을 바꿔 끼움(꼴 깨짐 재현) */
    orgOverride: undefined as unknown,
    beforeRecheck: null as null | (() => void),
  };
  const deps: Deps = {
    invoke: async (cmd, args) => {
      calls.push({ cmd, args });
      if (cmd === "org_status") return st.orgOverride !== undefined ? st.orgOverride : { surfaces: [st.master] };
      if (cmd === "feed_list") {
        if (st.feedFail) throw new Error("down");
        return { items: st.feed.map((x) => ({ ...x })) };
      }
      if (cmd === "confirm_reply") {
        st.reply?.(args ?? {});
        const a = args as { requestId: string; decision: string };
        st.feed = st.feed.filter((x) => x.request_id !== a.requestId);
        return st.replyResult ?? { request_id: a.requestId, decision: a.decision, actuated: a.decision === "allow" ? "return" : "esc" };
      }
      if (cmd === "chat_send") return { outcome: "written", result: { sent: true } };
      if (cmd === "chat_transcript") {
        const a = args as { afterOffset: number; fromEnd: boolean };
        if (a.fromEnd) return { status: "ok", session_id: st.session, next_offset: st.file.length, size: st.file.length, records: [] };
        const end = Math.min(st.file.length, a.afterOffset + st.chunk);
        // 대역 파일 = 레코드 배열 · 위치 = 줄 번호(viewcore.rs 의 줄 시작 바이트 `at` 과 같은 뜻)
        return { status: "ok", session_id: st.session, next_offset: end, size: st.file.length, records: st.file.slice(a.afterOffset, end).map((r, i) => ({ ...r, at: a.afterOffset + i })) };
      }
      throw new Error(`unexpected ${cmd}`);
    },
    now: () => now,
    setTimeout: () => 0,
    clearTimeout: () => {},
    store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v), remove: (k) => void mem.delete(k) },
    working: (r) => r.working === true,
    defaultSlug: async () => "hq-slug-0001",
    listenDaemon: (fn) => {
      listenCalls++;
      listeners.push(fn);
      return () => {
        const i = listeners.indexOf(fn);
        if (i >= 0) listeners.splice(i, 1);
      };
    },
  };
  const flush = async () => {
    for (let i = 0; i < 30; i++) await Promise.resolve();
  };
  const core = new ChatCore(deps);
  /** 앱 꼴 사건 — 앱 전달기는 본부 사건에도 본부 slug 를 붙인다(검증 F1) */
  const emit = (name: string, payload: Record<string, unknown>, surface_id: number | null = 5, socket_slug: string | undefined = "hq-slug-0001") => {
    for (const f of [...listeners]) f({ name, payload, surface_id, socket_slug });
  };
  const replies = () => calls.filter((c) => c.cmd === "confirm_reply");
  /** 대화 화면을 엶 + 3초 고리 n번 */
  const open = async (polls = 1) => {
    core.attach();
    await flush();
    for (let i = 0; i < polls; i++) {
      await core.poll();
      await flush();
    }
  };
  /** 도우미 허락 항목 — 기본 = 데몬 지문 표지가 있는 판(앞날 데몬 · 직접 허락 길 시험) · 지금 데몬 = `{ screen_fingerprint: undefined }` */
  const helper = (o: Partial<Record<string, unknown>> = {}) => ({ request_id: "r1", kind: "approval", status: "pending", surface_id: 7, created_at: now / 1000 - 10, daemon_issued: true, body: body("rm -rf build"), screen_fingerprint: "fp-1", ...o });
  return { calls, mem, st, core, emit, replies, open, flush, helper, listenersCount: () => listeners.length, listenCalls: () => listenCalls, setNow: (n: number) => (now = n), getNow: () => now };
}

const label = (h: ReturnType<typeof harness>) => {
  const b = h.core.confirm.band();
  return { known: b.known, n: b.items.length, kinds: b.items.map((x) => x.kind) };
};

describe("마스터 물음 — 표식 판독(§5-4 · FR-C1·C3)", () => {
  it("표식 없는 마스터 = 띠 0(꾸미지 않음) · 앞 기록 다 훑으면 「안다」", async () => {
    const h = harness({ prior: [A("a1", "📌 결정 필요: 배포할까요?"), A("a2", "그냥 답")] });
    await h.open(2);
    expect(label(h)).toEqual({ known: true, n: 0, kinds: [] });
  });
  it("대화 화면을 열기 전 물음도 앞 기록 훑기로 뜬다 · 훑는 동안은 「모름」(살펴보는 중)", async () => {
    const prior = Array.from({ length: 5 }, (_, i) => A(`p${i}`, i === 1 ? "⟪확인 요청: 배포할까요?⟫" : `말 ${i}`));
    const h = harness({ prior, chunk: 2 });
    h.core.attach();
    await h.flush();
    await h.core.poll(); // 첫 고리: 마스터를 앎 → 시작점 + 첫 토막
    await h.flush();
    expect(label(h).known).toBe(false);
    for (let i = 0; i < 4; i++) {
      await h.core.poll();
      await h.flush();
    }
    expect(label(h)).toEqual({ known: true, n: 1, kinds: ["ask"] });
    expect(h.core.confirm.questionsSoFar()[0].text).toBe("배포할까요?");
  });
  it("열린 뒤 온 물음 → 1 · 해결 표식 → 0 · 사람이 친 표식 꼴(user) = 0", async () => {
    const h = harness();
    await h.open(2);
    h.st.file.push(A("a1", "⟪확인 요청: 금요일 배포를 미뤄도 될까요?⟫"));
    h.st.file.push({ uuid: "u1", parent: null, role: "user", text: "⟪확인 요청: 사람이 친 글⟫", ts: null });
    await h.core.readTranscript();
    expect(label(h)).toEqual({ known: true, n: 1, kinds: ["ask"] });
    h.st.file.push(A("a2", "알겠어요.\n⟪확인 해결: 금요일 배포를 미뤄도 될까요?⟫"));
    await h.core.readTranscript();
    expect(label(h)).toEqual({ known: true, n: 0, kinds: [] });
  });
  it("보낸 말이 없어도 마스터가 쉬게 된 틱에 세션을 읽어 스스로 낸 물음이 뜬다(새 주기 조회 0)", async () => {
    const h = harness();
    await h.open(3);
    const reads = () => h.calls.filter((c) => c.cmd === "chat_transcript" && (c.args as { fromEnd: boolean }).fromEnd === false).length;
    const r0 = reads();
    await h.core.poll(); // 같은 활동(쉼) — 읽기 0
    await h.flush();
    expect(reads()).toBe(r0);
    h.st.master.working = true;
    await h.core.poll(); // 일함 — 기다리는 말 없음 → 읽기 0
    await h.flush();
    expect(reads()).toBe(r0);
    h.st.file.push(A("a9", "⟪확인 요청: 스스로 묻는 물음⟫"));
    h.st.master.working = false;
    await h.core.poll(); // 쉬게 됨 → 1회
    await h.flush();
    expect(reads()).toBe(r0 + 1);
    expect(label(h)).toEqual({ known: true, n: 1, kinds: ["ask"] });
  });
  it("앞 훑기가 뒤 기록까지 읽어도 순서가 뒤집히지 않는다(물음은 앞 · 해결은 뒤)", async () => {
    const h = harness({ prior: [A("p0", "⟪확인 요청: 순서 시험 물음⟫")], chunk: 1000 });
    h.core.attach();
    await h.flush();
    await h.core.poll(); // 마스터를 앎 → 시작점 = 1(앞 훑기는 다음 고리부터)
    await h.flush();
    h.st.file.push(A("t1", "⟪확인 해결: 순서 시험 물음⟫"));
    await h.core.readTranscript(); // 뒤 읽기가 해결을 먼저 받음
    h.st.file.push(A("t2", "다시 여쭐게요.\n⟪확인 요청: 순서 시험 물음⟫")); // 해결 뒤 다시 물음(뒤 읽기는 아직)
    await h.core.poll(); // 앞 훑기 — p0·t1·t2 를 한 토막에 읽음: t1(뒤 읽기가 받은 것)에서 멈춰야 t2 가 해결 뒤에 논다
    await h.flush();
    await h.core.readTranscript();
    expect(label(h)).toEqual({ known: true, n: 1, kinds: ["ask"] });
  });
  it("(codex 1R 탐침) uuid 없는 레코드도 앞 훑기·뒤 읽기가 두 번 세지 않는다", async () => {
    const N = (text: string, ts: string) => ({ uuid: null, parent: null, role: "assistant", text, ts });
    const h = harness({ prior: [N("⟪확인 요청: 무uuid 물음⟫", "2026-11-18T00:00:00Z")] });
    h.core.attach();
    await h.flush();
    await h.core.poll(); // 시작점 = 1
    await h.flush();
    h.st.file.push(N("⟪확인 해결: 무uuid 물음⟫", "2026-11-18T00:00:05Z"));
    await h.core.readTranscript(); // 뒤 읽기 = 해결
    await h.core.poll(); // 앞 훑기 = 물음 + (해결 = 뒤 기록에서 멈춤)
    await h.flush();
    expect(label(h)).toEqual({ known: true, n: 0, kinds: [] });
  });
  it("결속 세션이 바뀌면 표식 처음부터(옛 물음을 새 대화에 남기지 않음)", async () => {
    const h = harness({ prior: [A("p0", "⟪확인 요청: 옛 세션 물음⟫")] });
    await h.open(3);
    expect(label(h).n).toBe(1);
    h.st.session = "sess-0002";
    h.st.file = [A("n0", "새 세션")];
    await h.core.readTranscript();
    await h.core.poll();
    await h.flush();
    expect(label(h)).toEqual({ known: true, n: 0, kinds: [] });
  });
  it("★물음이 열려 있어도 보낸 말은 원문 그대로(「어느 물음의 답」 붙이기 0 · FR-C3)", async () => {
    const h = harness({ prior: [A("p0", "⟪확인 요청: 배포할까요?⟫")] });
    await h.open(3);
    await h.core.send("네 해 주세요");
    const w = h.calls.filter((c) => c.cmd === "chat_send");
    expect(w.length).toBe(1);
    expect(w[0].args?.text).toBe("네 해 주세요");
    expect(label(h).n).toBe(1); // 화면이 닫지 않는다 — 마스터의 해결 표식만 닫음
  });
});

describe("도우미 허락 — 평소 「마스터가 확인하는 중」(FR-C6) · 멈춤 때만 직접(FR-C5)", () => {
  it("평소 = 직접 단추 없음 · 억지로 불러도 재확인에서 멈춤 아님 → 호출 0", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    await h.open(2);
    const it0 = h.core.confirm.band().items[0];
    expect(it0.kind === "helper" && it0.stall).toBeNull();
    await h.core.confirm.decide(boundOf(it0.kind === "helper" ? it0.a : (null as unknown as FeedApproval)), "allow");
    expect(h.replies().length).toBe(0);
    expect(h.core.confirm.notice).toContain("마스터가 다시 확인");
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("not_stalled");
  });
  it("master.deadman → 직접 허락 1회(번호·allow) · 결과 안내 · 누른 기록(명령 원문 0자)", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    h.st.master.idle_secs = 120;
    await h.open(2);
    h.emit("master.deadman", { role: "master", axis: "agent_dead", reason: "agent process dead" });
    const it0 = h.core.confirm.band().items[0];
    expect(it0.kind === "helper" && it0.stall).toBe("deadman");
    await h.core.confirm.decide(boundOf((it0 as { a: FeedApproval }).a), "allow");
    expect(h.replies().map((c) => c.args)).toEqual([{ requestId: "r1", decision: "allow", screenFingerprint: "fp-1" }]);
    expect(h.core.confirm.notice).toContain("허락했어요");
    const log = h.mem.get(DECISION_LOG_KEY) ?? "";
    expect(JSON.parse(log).items).toEqual([{ request_id: "r1", decision: "allow", at: h.getNow(), outcome: "replied" }]);
    expect(log.includes("rm -rf")).toBe(false);
    expect(label(h).n).toBe(0); // 처리 뒤 바로 다시 받음
  });
  it("부서 데몬 사건·다른 역할 deadman = 무시", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    h.st.master.idle_secs = 120;
    await h.open(2);
    h.core.confirm.onEvent({ name: "master.deadman", payload: { role: "master" }, surface_id: 5, socket_slug: "dept-1" });
    h.emit("master.deadman", { role: "cso" });
    const it0 = h.core.confirm.band().items[0];
    expect(it0.kind === "helper" && it0.stall).toBeNull();
  });
  it("approval.stalled(그 요청) → 직접 · 다른 요청 번호 = 아님", async () => {
    const h = harness();
    h.st.feed = [h.helper(), h.helper({ request_id: "r2" })];
    await h.open(2);
    h.emit("approval.stalled", { request_id: "r2", age_secs: 300 }, 7);
    const st = h.core.confirm.band().items.map((x) => (x.kind === "helper" ? x.stall : "?"));
    expect(st).toEqual([null, "stalled_event"]);
  });
  it("생긴 지 5분 ∧ 마스터 소식 5분 없음 → 직접(사건 없이도)", async () => {
    const h = harness();
    h.st.feed = [h.helper({ created_at: (h.getNow() - CONFIRM_STALL_MS) / 1000 })];
    h.st.master.idle_secs = 300;
    await h.open(2);
    const it0 = h.core.confirm.band().items[0];
    expect(it0.kind === "helper" && it0.stall).toBe("quiet");
  });
  it("마스터가 꺼짐(agent_alive false) → 직접 · 마스터 좌석 자신의 승인 = 마스터 창(직접 단추 없음)", async () => {
    const h = harness();
    h.st.feed = [h.helper(), h.helper({ request_id: "rm", surface_id: 5 })];
    h.st.master.agent_alive = false;
    await h.open(2);
    // (검증 F5) 꺼짐을 처음 본 뒤 30초 유예 — 그동안은 「마스터가 확인하는 중」
    expect(h.core.confirm.band().items.map((x) => (x.kind === "helper" ? x.stall : "-"))).toEqual([null, "-"]);
    h.setNow(h.getNow() + 30_000);
    expect(h.core.confirm.band().items.map((x) => [x.kind, x.kind === "helper" ? x.stall : null])).toEqual([
      ["helper", "master_off"],
      ["master_screen", null],
    ]);
  });
});

describe("독립 검증(2160) 지적 고정", () => {
  const N = (text: string, ts: string | null = null) => ({ uuid: null, parent: null, role: "assistant", text, ts });
  it("F1 — 본부 slug 가 붙은 사건 = 받음 · 다른 slug = 버림 · 본부 slug 를 아직 모르면 버림", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    h.st.master.idle_secs = 120;
    await h.open(2);
    h.emit("master.deadman", { role: "master" }, 5, "dept-slug-9");
    expect((h.core.confirm.band().items[0] as { stall: unknown }).stall).toBeNull();
    h.core.confirm.setHqSlug(null);
    h.emit("master.deadman", { role: "master" });
    expect((h.core.confirm.band().items[0] as { stall: unknown }).stall).toBeNull();
    h.core.confirm.setHqSlug("hq-slug-0001");
    h.emit("master.deadman", { role: "master" });
    expect((h.core.confirm.band().items[0] as { stall: unknown }).stall).toBe("deadman");
  });
  it("F2 ⓐ — 풀림을 한 번 보면 deadman 을 지운다(그 뒤 마스터 상태 모름이 와도 멈춤 아님 · 클릭 호출 0)", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    h.st.master.idle_secs = 120;
    await h.open(2);
    h.emit("master.deadman", { role: "master" });
    h.setNow(h.getNow() + 10_000);
    h.st.master.idle_secs = 1; // 사건 뒤 출력 = 풀림
    await h.core.poll();
    await h.flush();
    const it0 = h.core.confirm.band().items[0] as { a: FeedApproval; stall: unknown };
    expect(it0.stall).toBeNull();
    h.core.confirm.observe({ items: h.st.feed }, undefined, undefined); // 마스터 상태 모름
    expect((h.core.confirm.band().items[0] as { stall: unknown }).stall).toBeNull();
    // 걸쇠: 같은 좌석이 이어서 보이되 생존이 모름(null)으로 바뀌어도(풀림 다시 계산 = 거짓) 이미 지운 deadman 은 되살아나지 않는다
    h.st.master.agent_alive = null;
    await h.core.poll();
    await h.flush();
    expect((h.core.confirm.band().items[0] as { stall: unknown }).stall).toBeNull();
  });
  it("F2 ⓑ · codex 1R major 1 — 생존 모름(agent_alive null) 관측만으로는 deadman 근거 아님(단추 0 · 호출 0)", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    h.st.master.agent_alive = null;
    h.st.master.idle_secs = 120;
    await h.open(2);
    h.emit("master.deadman", { role: "master" });
    const it0 = h.core.confirm.band().items[0] as { a: FeedApproval; stall: unknown };
    expect(it0.stall).toBeNull();
    await h.core.confirm.decide(boundOf(it0.a), "allow");
    expect(h.replies().length).toBe(0);
  });
  it("codex 1R major 1 재현 — deadman 뒤 같은 마스터가 출력 재개(생존 null · idle 0) = 풀림(걸쇠) · 뒤에 생존 확정이 와도 되살아나지 않음 · 호출 0", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    h.st.master.idle_secs = 120;
    await h.open(2);
    h.emit("master.deadman", { role: "master" });
    expect((h.core.confirm.band().items[0] as { stall: unknown }).stall).toBe("deadman");
    h.setNow(h.getNow() + 10_000);
    h.st.master.agent_alive = null; // 생존 모름
    h.st.master.idle_secs = 0; // 사건 뒤 새 출력
    await h.core.poll();
    await h.flush();
    expect((h.core.confirm.band().items[0] as { stall: unknown }).stall).toBeNull();
    // 걸쇠: 생존 확정 · 오래 조용해져도(새 deadman 없음) 지운 deadman 은 되살아나지 않는다
    h.st.master.agent_alive = true;
    h.st.master.idle_secs = 200;
    await h.core.poll();
    await h.flush();
    const it0 = h.core.confirm.band().items[0] as { a: FeedApproval; stall: unknown };
    expect(it0.stall).toBeNull();
    await h.core.confirm.decide(boundOf(it0.a), "allow");
    expect(h.replies().length).toBe(0);
  });
  it("F3 — 못 나아가는 토막(아직 끝나지 않은 긴 줄) = 「다 훑음」 확정 안 함 · 건너뛴 긴 줄 = 물음은 보이되 모름", async () => {
    const h = harness({ prior: [A("p0", "⟪확인 요청: 긴 줄 앞 물음⟫"), A("p1", "x")], chunk: 1 });
    let stuck = true;
    const inv = h.core["d"].invoke;
    (h.core["d"] as { invoke: typeof inv }).invoke = async (cmd, args) => {
      if (cmd === "chat_transcript" && !(args as { fromEnd: boolean }).fromEnd && (args as { afterOffset: number }).afterOffset === 1) {
        if (stuck) return { status: "ok", session_id: h.st.session, next_offset: 1, size: 2, records: [] };
        return { status: "ok", session_id: h.st.session, next_offset: 2, size: 2, records: [], skipped_bytes: 3_000_000 };
      }
      return inv(cmd, args);
    };
    (h.core.confirm as unknown as { d: { invoke: typeof inv } }).d.invoke = h.core["d"].invoke;
    await h.open(4);
    expect(label(h).known).toBe(false); // 못 나아감 — 모름 유지
    stuck = false;
    await h.open(2);
    expect(label(h)).toEqual({ known: false, n: 1, kinds: ["ask"] }); // 다 훑었으나 긴 줄을 건너뜀 → 물음 1 · 모름
  });
  it("F6 — 처리 직전 org.status 왕복이 500ms 넘으면 호출 0", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    h.st.master.idle_secs = 120;
    await h.open(2);
    h.emit("master.deadman", { role: "master" });
    const it0 = h.core.confirm.band().items[0] as { a: FeedApproval };
    const inv = h.core["d"].invoke;
    (h.core.confirm as unknown as { d: { invoke: typeof inv } }).d.invoke = async (cmd, args) => {
      if (cmd === "org_status") h.setNow(h.getNow() + 501);
      return inv(cmd, args);
    };
    await h.core.confirm.decide(boundOf(it0.a), "allow");
    expect(h.replies().length).toBe(0);
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("org_unknown");
  });
  it("F9 — uuid·시각 없는 레코드: 묻고 → 해결 → 같은 글로 다시 물음 = 열림 1", async () => {
    const h = harness();
    await h.open(3);
    h.st.file.push(N("⟪확인 요청: 무신원 물음⟫"), N("⟪확인 해결: 무신원 물음⟫"), N("⟪확인 요청: 무신원 물음⟫"));
    await h.core.readTranscript();
    expect(label(h)).toEqual({ known: true, n: 1, kinds: ["ask"] });
  });
  it("V17 — 끝을 넘는 토막의 앞 기록 물음(uuid·시각 없음)을 잃지 않는다(위치로 가름 = 1)", async () => {
    const h = harness({ prior: [N("⟪확인 요청: 앞 기록 무신원 물음⟫")] });
    h.core.attach();
    await h.flush();
    await h.core.poll(); // 시작점 = 1
    await h.flush();
    h.st.file.push(N("다른 말"));
    await h.core.readTranscript(); // 뒤 읽기 = 다른 말
    await h.core.poll(); // 앞 훑기(끝을 넘는 토막): 물음 → 다른 말(뒤 기록)에서 멈춤
    await h.flush();
    expect(label(h)).toEqual({ known: true, n: 1, kinds: ["ask"] });
  });
  it("V18 — 앞 훑기는 끝 너머 레코드를 가져가지 않는다 · 뒤 읽기가 한 번만 센다(해결 한 번 = 물음 하나)", async () => {
    const p = "가나다라마바사아자차카타파하가나다라마바";
    const h = harness({ prior: [A("p0", `⟪확인 요청: ${p} 첫째⟫`), A("p1", `⟪확인 요청: ${p} 둘째⟫`)] });
    h.core.attach();
    await h.flush();
    await h.core.readTranscript(); // 마스터 모름 — 아무것도 안 함
    await h.core.poll(); // 시작점 = 2 · (이 틱의 앞 훑기는 시작점 전이라 건너뜀)
    await h.flush();
    h.st.file.push(A("t1", `⟪확인 해결: ${p}⟫`));
    await h.core.poll(); // 앞 훑기: p0·p1 · t1(위치 2 = 끝) 에서 멈춤
    await h.flush();
    await h.core.readTranscript(); // 뒤 읽기: t1 한 번
    expect(h.core.confirm.questionsSoFar().map((q) => q.text)).toEqual([`${p} 둘째`]);
  });
});

describe("codex 1R(02:51 · e62e1fb0) 지적 고정", () => {
  const N = (text: string, ts: string | null = null) => ({ uuid: null, parent: null, role: "assistant", text, ts });
  const stalledH = async (o: Partial<Record<string, unknown>> = {}) => {
    const h = harness();
    h.st.feed = [h.helper(o)];
    h.st.master.idle_secs = 120;
    await h.open(2);
    h.emit("master.deadman", { role: "master" });
    const it0 = h.core.confirm.band().items[0] as { a: FeedApproval; stall: unknown };
    return { h, it0 };
  };
  it("blocking — 지금 데몬(지문 표지 없음): 멈춤이어도 허락 = 호출 0(재조회도 0) + 작업 화면 안내 · 거절 = 1회(지문 null)", async () => {
    const { h, it0 } = await stalledH({ screen_fingerprint: undefined });
    expect(it0.stall).toBe("deadman");
    expect(it0.a.fingerprint).toBeNull();
    const n0 = h.calls.length;
    await h.core.confirm.decide(boundOf(it0.a), "allow");
    expect(h.calls.length).toBe(n0); // feed·org 다시 받기도 하지 않음
    expect(h.core.confirm.notice).toBe(ALLOW_AT_WORK_MSG);
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("no_fingerprint");
    await h.core.confirm.decide(boundOf(it0.a), "deny");
    expect(h.replies().map((c) => c.args)).toEqual([{ requestId: "r1", decision: "deny", screenFingerprint: null }]);
  });
  it("blocking — 펼친 뒤 지문이 바뀜(같은 번호·시각·본문 · 다른 창) = 호출 0", async () => {
    const { h, it0 } = await stalledH();
    h.st.feed = [{ ...h.st.feed[0], screen_fingerprint: "fp-2" }];
    await h.core.confirm.decide(boundOf(it0.a), "allow");
    expect(h.replies().length).toBe(0);
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("changed");
  });
  it("major 3 — 본부 slug 를 알 때 slug 없음·null·빈 글 사건 = 버림(approval.stalled · deadman)", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    h.st.master.idle_secs = 120;
    await h.open(2);
    for (const slug of [undefined, null, ""]) {
      for (const f of [(e: unknown) => h.core.confirm.onEvent(e)]) {
        f({ name: "approval.stalled", payload: { request_id: "r1" }, surface_id: 7, ...(slug === undefined ? {} : { socket_slug: slug }) });
        f({ name: "master.deadman", payload: { role: "master" }, surface_id: 5, ...(slug === undefined ? {} : { socket_slug: slug }) });
      }
    }
    const it0 = h.core.confirm.band().items[0] as { a: FeedApproval; stall: unknown };
    expect(it0.stall).toBeNull();
    await h.core.confirm.decide(boundOf(it0.a), "allow");
    expect(h.replies().length).toBe(0);
  });
  it("major 4 — 처리 직전 org 응답 꼴 깨짐({surfaces:null}) = 호출 0 · 마스터 좌석 모르는 동안 직접 단추 0", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    await h.open(2);
    h.emit("approval.stalled", { request_id: "r1" }, 7);
    const it0 = h.core.confirm.band().items[0] as { a: FeedApproval; stall: unknown };
    expect(it0.stall).toBe("stalled_event");
    h.st.orgOverride = { surfaces: null };
    await h.core.confirm.decide(boundOf(it0.a), "allow");
    expect(h.replies().length).toBe(0);
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("org_unknown");
    // 꼴 깨진 org 를 본 뒤(마스터 상태 모름) 띠의 그 항목 = 직접 단추 0(「마스터가 확인하는 중」)
    expect((h.core.confirm.band().items[0] as { stall: unknown }).stall).toBeNull();
  });
  it("2R major — 살아 있는 마스터 행의 좌석 번호가 깨짐(\"7\") = 마스터 없음이 아니라 모름 · 처리 직전 = 호출 0 · 주기 관측 = 직접 단추 0", async () => {
    expect(masterOf({ surfaces: [{ role: "master", surface_id: "7", exited: false, agent_alive: true }] })).toBeUndefined();
    expect(masterOf({ surfaces: [{ role: "master", surface_id: 5, exited: false, agent_alive: true }, { role: "master", surface_id: null, exited: false }] })).toBeUndefined();
    expect(masterOf({ surfaces: [{ role: "master", surface_id: "7", exited: true }] })).toBeNull(); // 끝난 행은 고르지 않음 = 마스터 없음
    expect(masterOf({ surfaces: [] })).toBeNull();
    const h = harness();
    h.st.feed = [h.helper({ screen_fingerprint: undefined })];
    await h.open(2);
    h.emit("approval.stalled", { request_id: "r1" }, 7);
    const it0 = h.core.confirm.band().items[0] as { a: FeedApproval; stall: unknown };
    expect(it0.stall).toBe("stalled_event");
    h.st.orgOverride = { surfaces: [{ ...h.st.master, surface_id: "7" }] }; // 마스터가 7 로 옮겼는데 번호 칸이 깨짐
    await h.core.confirm.decide(boundOf(it0.a), "deny");
    expect(h.replies().length).toBe(0);
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("org_unknown");
    h.core.confirm.observe({ items: h.st.feed }, h.st.orgOverride, { surface_id: 5, agent_alive: true }); // core 가 다른 행을 골라 넘겨도
    expect((h.core.confirm.band().items[0] as { stall: unknown }).stall).toBeNull();
  });
  it("major 5 — 데몬이 기록만 해소(actuated null) = 「했어요」 아님 · 작업 화면 확인 안내 · 기록 outcome recorded_only", async () => {
    for (const dec of ["allow", "deny"] as const) {
      const { h, it0 } = await stalledH();
      h.st.replyResult = { request_id: "r1", decision: dec, actuated: null };
      await h.core.confirm.decide(boundOf(it0.a), dec);
      expect(h.replies().length).toBe(1);
      expect(h.core.confirm.notice).toBe(RECORDED_ONLY_MSG);
      expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("recorded_only");
    }
    const { h, it0 } = await stalledH();
    h.st.replyResult = { request_id: "r1", decision: "deny" }; // actuated 칸 없음 = 기록만
    await h.core.confirm.decide(boundOf(it0.a), "deny");
    expect(h.core.confirm.notice).toBe(RECORDED_ONLY_MSG);
  });
  it("minor — 앞 기록 「물음 X → 물음 Q(uuid·시각 없음) → 해결 X」 · 뒤 기록에 같은 Q 가 먼저 와도 해결 X 를 놓치지 않는다", async () => {
    const h = harness({ prior: [A("x", "⟪확인 요청: X 물음⟫"), N("⟪확인 요청: Q 물음⟫"), A("rx", "⟪확인 해결: X 물음⟫")] });
    h.core.attach();
    await h.flush();
    await h.core.poll(); // 시작점 = 3
    await h.flush();
    h.st.file.push(N("⟪확인 요청: Q 물음⟫"));
    await h.core.readTranscript(); // 뒤 읽기가 Q 를 먼저 받음
    await h.core.poll(); // 앞 훑기(끝을 넘는 토막)
    await h.flush();
    expect(label(h)).toEqual({ known: true, n: 1, kinds: ["ask"] });
    expect(h.core.confirm.questionsSoFar().map((q) => q.text)).toEqual(["Q 물음"]);
  });
  it("minor — 끝을 넘는 토막에 위치 모르는 레코드 = 「다 훑음」 확정 안 함(모름 유지)", async () => {
    const h = harness({ prior: [A("p0", "⟪확인 요청: 위치 시험⟫")] });
    const inv = h.core["d"].invoke;
    const noAt: typeof inv = async (cmd, args) => {
      const r = (await inv(cmd, args)) as { records?: Array<Record<string, unknown>> } | null;
      if (cmd === "chat_transcript" && r?.records) r.records = r.records.map(({ at: _at, ...x }) => x);
      return r;
    };
    (h.core.confirm as unknown as { d: { invoke: typeof inv } }).d.invoke = noAt;
    h.core.attach();
    await h.flush();
    await h.core.poll(); // 시작점 = 1
    await h.flush();
    h.st.file.push(A("t1", "뒤 말"));
    await h.core.readTranscript();
    for (let i = 0; i < 3; i++) {
      await h.core.poll();
      await h.flush();
    }
    expect(label(h).known).toBe(false);
  });
});

describe("판 묶기 · 처리 직전 재확인(FR-C5b)", () => {
  const stalled = async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    h.st.master.idle_secs = 120;
    await h.open(2);
    h.emit("master.deadman", { role: "master" });
    const it0 = h.core.confirm.band().items[0] as { a: FeedApproval };
    return { h, bound: boundOf(it0.a) };
  };
  it("이미 처리된 요청(목록에서 빠짐) = 호출 0 + 「이미 처리됐거나 바뀐 요청이에요」", async () => {
    const { h, bound } = await stalled();
    h.st.feed = [];
    await h.core.confirm.decide(bound, "allow");
    expect(h.replies().length).toBe(0);
    expect(h.core.confirm.notice).toBe("이미 처리됐거나 바뀐 요청이에요.");
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("gone");
  });
  it("★펼친 뒤 판이 바뀜(같은 번호 · 다른 명령) = 호출 0", async () => {
    const { h, bound } = await stalled();
    h.st.feed = [h.helper({ body: body("rm -rf ~") })];
    await h.core.confirm.decide(bound, "allow");
    expect(h.replies().length).toBe(0);
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("changed");
  });
  it("같은 번호 · 다른 시각(다시 뜬 창) = 호출 0", async () => {
    const { h, bound } = await stalled();
    h.st.feed = [h.helper({ created_at: bound.created_at + 5 })];
    await h.core.confirm.decide(bound, "deny");
    expect(h.replies().length).toBe(0);
  });
  it("재확인 조회 실패 = 호출 0(모름은 쓰지 않는 쪽)", async () => {
    const { h, bound } = await stalled();
    h.st.feedFail = true;
    await h.core.confirm.decide(bound, "allow");
    expect(h.replies().length).toBe(0);
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("unknown");
  });
  it("마스터가 그사이 다시 출력(멈춤 풀림) = 호출 0", async () => {
    const { h, bound } = await stalled();
    h.setNow(h.getNow() + 5_000);
    h.st.master.idle_secs = 0;
    await h.core.confirm.decide(bound, "allow");
    expect(h.replies().length).toBe(0);
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("not_stalled");
  });
  it("(codex 1R 탐침) 처리 직전 그 요청이 지금 마스터 좌석의 것이면 approval.stalled 가 있어도 호출 0", async () => {
    const h = harness();
    h.st.feed = [h.helper()];
    await h.open(2);
    h.emit("approval.stalled", { request_id: "r1" }, 7);
    const it0 = h.core.confirm.band().items[0] as { a: FeedApproval; stall: string };
    expect(it0.stall).toBe("stalled_event");
    h.st.master.surface_id = 7; // 마스터가 그 좌석으로
    await h.core.confirm.decide(boundOf(it0.a), "allow");
    expect(h.replies().length).toBe(0);
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("not_stalled");
  });
  it("데몬이 「already resolved」로 거절 = 안내(다시 시도 0)", async () => {
    const { h, bound } = await stalled();
    h.st.reply = () => {
      throw new Error("invalid_params: item already resolved");
    };
    await h.core.confirm.decide(bound, "allow");
    expect(h.replies().length).toBe(1);
    expect(h.core.confirm.notice).toBe("이미 처리됐거나 바뀐 요청이에요.");
    expect(h.core.confirm.decisions.at(-1)?.outcome).toBe("invalid_params");
  });
  it("연타(처리 중 두 번째 누름) = 호출 1", async () => {
    const { h, bound } = await stalled();
    await Promise.all([h.core.confirm.decide(bound, "allow"), h.core.confirm.decide(bound, "allow")]);
    expect(h.replies().length).toBe(1);
  });
});

describe("구독 수명 — 대화 화면이 켜져 있을 때만(작업 화면 동작 변화 0)", () => {
  it("만들기만 하면 구독·조회 0 · 켜면 1 · 내리면 0 · 내린 뒤 사건은 못 받음", async () => {
    const h = harness();
    expect(h.listenCalls()).toBe(0);
    expect(h.calls.length).toBe(0);
    h.core.attach();
    expect(h.listenersCount()).toBe(1);
    h.core.attach();
    expect(h.listenCalls()).toBe(1);
    h.core.detach();
    expect(h.listenersCount()).toBe(0);
  });
});
