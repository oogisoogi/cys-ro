// (TICKET=verify-1119-s3 · 재실행) 고침 3c894f8d0 이 새로 연 길이 있는가 — 같은 파일을 526cf0609(고침 전)과 3c894f8d0(고침 뒤)에 돌려 출력을 견준다.
// verify_s3.test.ts 의 대역을 그대로 옮긴 작은 판(파일 없음·되돌리기 켬만 씀).
import { describe, it, expect } from "bun:test";
import { ChatCore, type Deps } from "./core";

function mini(o: { compat?: boolean } = {}) {
  const calls: Array<{ cmd: string; args?: Record<string, unknown>; at: number }> = [];
  let now = 5_000_000;
  const t0 = now;
  const timers: Array<{ at: number; fn: () => void; h: number }> = [];
  let hn = 0;
  const st = {
    master: { surface_id: 5, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false, registered_session_id: "sess-0001-aaaa" } as Record<string, unknown>,
    file: [] as Array<Record<string, unknown>>,
    session: "sess-0001-aaaa",
    noFile: false,
    watchGen: 0,
  };
  const deps: Deps = {
    invoke: async (cmd, args) => {
      calls.push({ cmd, args, at: now - t0 });
      if (cmd === "org_status") return { surfaces: [st.master] };
      if (cmd === "feed_list") return { items: [] };
      if (cmd === "chat_send") return { outcome: "written", result: { sent: true } };
      if (cmd === "chat_transcript") {
        const a = args as { afterOffset: number; fromEnd: boolean };
        if (st.noFile) return { status: "unknown", why: "no_file", session_id: st.session };
        if (a.fromEnd) return { status: "ok", session_id: st.session, next_offset: st.file.length, size: st.file.length, records: [] };
        return { status: "ok", session_id: st.session, next_offset: st.file.length, size: st.file.length, records: st.file.slice(a.afterOffset), reset: a.afterOffset > st.file.length };
      }
      if (cmd === "chat_transcript_watch") {
        const a = args as { sessionId: string };
        if (st.noFile) return { status: "unknown", why: "no_file", session_id: st.session };
        if (a.sessionId !== st.session) return { status: "unknown", why: "session_mismatch" };
        return { status: "ok", session_id: st.session, size: st.file.length, gen: ++st.watchGen };
      }
      if (cmd === "chat_transcript_unwatch") return { status: "ok", was: true };
      if (cmd === "chat_transcript_tail") {
        const a = args as { afterOffset: number };
        return { status: "ok", session_id: st.session, gen: st.watchGen, from_offset: a.afterOffset, to_offset: st.file.length, next_offset: st.file.length, size: st.file.length, records: st.file.slice(a.afterOffset), reset: false, more: false };
      }
      throw new Error(`unexpected ${cmd}`);
    },
    listenApp: async () => () => {},
    now: () => now,
    setTimeout: (fn, ms) => {
      const h = ++hn;
      timers.push({ at: now + ms, fn, h });
      return h;
    },
    clearTimeout: (h) => {
      const i = timers.findIndex((t) => t.h === h);
      if (i >= 0) timers.splice(i, 1);
    },
    store: { get: () => null, set: () => {}, remove: () => {} },
    working: (r) => r.working === true,
  };
  if (o.compat !== undefined) (deps as Deps & { compat1118?: () => boolean }).compat1118 = () => o.compat as boolean;
  const flush = async () => {
    for (let i = 0; i < 60; i++) await Promise.resolve();
  };
  const advance = async (ms: number) => {
    const until = now + ms;
    for (;;) {
      timers.sort((a, b) => a.at - b.at);
      const t = timers[0];
      if (!t || t.at > until) break;
      timers.shift();
      now = t.at;
      t.fn();
      await flush();
    }
    now = until;
    await flush();
  };
  const core = new ChatCore(deps);
  const seen: string[] = [];
  (core.confirm as unknown as { onTail(r: Array<{ uuid?: string }>): void }).onTail = (r) => void seen.push(...r.map((x) => String(x.uuid)));
  const tick3 = async () => {
    for (let i = 0; i < 2; i++) {
      await advance(1000);
      core.pollTick();
      await advance(5);
    }
    await advance(990);
    await core.poll();
    await advance(5);
  };
  const n = (cmd: string) => calls.filter((c) => c.cmd === cmd).length;
  return { core, st, calls, seen, tick3, advance, flush, n };
}

describe("verify-1119-s3 재실행 — 고침이 새로 연 길", () => {
  // N1: 결속 세션은 있는데 기록 파일이 **끝내 안 생기는** 좌석(막 켜 놓고 쉬는 마스터 · 슬러그가 안 맞는 좌석).
  //     고침 전 = 「기록 없음 30초 문」 + watch 못 걸면 30초 물러남 → 데몬 조회(명령당 RPC 2)가 30초에 한 번꼴.
  it("N1 · 파일이 끝내 없는 좌석 60초 — 데몬 RPC 2개짜리 명령(chat_transcript·chat_transcript_watch)을 3초마다 쌓지 않는다", async () => {
    const h = mini();
    h.st.noFile = true;
    h.core.attach();
    await h.flush();
    await h.core.poll();
    await h.advance(10);
    for (let i = 0; i < 20; i++) {
      if (i === 3 || i === 10) h.core.submit(`말 ${i}`);
      h.st.master.working = i % 4 === 1;
      await h.tick3();
    }
    const w = h.n("chat_transcript_watch");
    const t = h.n("chat_transcript");
    console.log(`[N1] 60초: chat_transcript_watch ${w}회 · chat_transcript ${t}회 = 데몬 RPC ${2 * (w + t)}개 · chat_send ${h.n("chat_send")}회`);
    expect(2 * (w + t) <= 16).toBe(true); // (고침3 · [master#a5f2e240]) 상한 = 60초 데몬 RPC 16 — 파일을 기다리는 동안 10초·30초 박자로 스스로 다시 묻는 몫을 더함(1.1.18 = 6) // (만든 좌석 옮김 · 타입 게이트: Matchers 형에 toBeLessThanOrEqual 없음 — 뜻 같음) // 30초 문·물러남이 살아 있으면 60초에 몇 번뿐
  });

  // N2: 되돌리기 켬(= 1.1.18 꼴이어야 함)에서 결속이 바뀔 때 chat_transcript 를 언제·어떤 인자로 부르는가.
  it("N2 · 되돌리기 켬 — 결속 바뀜 뒤 시작점 조회(fromEnd)의 시각·횟수(고침 전후를 견줄 값)", async () => {
    const h = mini({ compat: true });
    h.core.attach();
    await h.flush();
    await h.core.poll();
    await h.advance(10);
    const mark = h.calls.length;
    h.st.session = "sess-0002-bbbb";
    h.st.master.registered_session_id = "sess-0002-bbbb";
    h.st.file = [{ uuid: "n1", parent: null, role: "assistant", text: "새 세션 첫 줄", ts: null }];
    await h.tick3(); // 결속 바뀜을 본 조회(활동 바뀜 없음 = 1.1.18 에는 읽기 계기 없음)
    h.st.file.push({ uuid: "n2", parent: null, role: "assistant", text: "둘째 줄", ts: null });
    await h.tick3();
    h.st.master.working = true;
    await h.tick3();
    h.st.master.working = false;
    await h.tick3(); // 1.1.18 의 읽기 계기(활동 바뀜)
    await h.tick3();
    const tr = h.calls.slice(mark).filter((c) => c.cmd === "chat_transcript").map((c) => `${(c.at / 1000).toFixed(1)}s:${(c.args as { fromEnd: boolean }).fromEnd ? "fromEnd" : `after=${(c.args as { afterOffset: number }).afterOffset}`}`);
    console.log(`[N2] 되돌리기 켬 · chat_transcript 호출: ${tr.join(" , ")} · 받은 레코드 ${JSON.stringify(h.seen)} · 새 명령 ${h.n("chat_transcript_watch") + h.n("chat_transcript_unwatch") + h.n("chat_transcript_tail")}`);
    expect(h.n("chat_transcript_watch") + h.n("chat_transcript_unwatch") + h.n("chat_transcript_tail")).toBe(0);
    // (만든 좌석 옮김 · 고침2 · [master#f03515c6] N2) 명령 수가 아니라 시각·시작점 값으로 1.1.18 과 같음 — 기대값 = 같은 장면을 1.1.18 코드(838f24421 ui/src)에 돌려 잰 값
    expect(tr).toEqual(["12.0s:after=0", "12.0s:fromEnd", "15.0s:after=0"]);
    expect(h.seen).toEqual([]);
  });
});
