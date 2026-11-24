// (TICKET=verify-1119-s3 · 재실행 2) 고침 2회 b0e8b72ee — ⑴ 파일이 늦게 생기는 장면에서 첫 답이 언제 오는가 ⑵ 되돌리기 켬의 호출 자취(1.1.18 코드 838f24421 과 글자 대조용).
// 같은 파일을 여러 커밋에 돌린다(838f24421 에는 compat1118·watch 가 없다 = 그 자체가 1.1.18).
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
    masterGone: false,
    file: [] as Array<Record<string, unknown>>,
    session: "sess-0001-aaaa",
    noFile: false,
    watchGen: 0,
  };
  const deps: Deps = {
    invoke: async (cmd, args) => {
      calls.push({ cmd, args, at: now - t0 });
      if (cmd === "org_status") return { surfaces: st.masterGone ? [] : [st.master] };
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
  const seen: Array<{ u: string; at: number }> = [];
  (core.confirm as unknown as { onTail(r: Array<{ uuid?: string }>): void }).onTail = (r) => void seen.push(...r.map((x) => ({ u: String(x.uuid), at: now - t0 })));
  /** 초 단위 시간표: 매초 그 초의 일을 하고 1초 흐른 뒤 앱 1초 시계(pollTick — 3초마다 스스로 온전한 조회)를 부른다. */
  const run = async (secs: number, plan: Record<number, () => void>) => {
    for (let s = 0; s < secs; s++) {
      plan[s]?.();
      await flush();
      await advance(1000);
      core.pollTick();
      await flush();
    }
  };
  const start = async () => {
    core.attach();
    await flush();
    await core.poll();
    await advance(10);
  };
  const n = (cmd: string) => calls.filter((c) => c.cmd === cmd).length;
  const rec = (i: number) => ({ uuid: `u${i}`, parent: null, role: "assistant", text: `답 ${i}`, ts: null });
  const user = (t: string) => ({ uuid: `user-${t}`, parent: null, role: "user", text: t, ts: null });
  const trace = () => calls.map((c) => `${(c.at / 1000).toFixed(2)} ${c.cmd} ${JSON.stringify(c.args ?? null)}`);
  return { core, st, calls, seen, run, start, advance, flush, n, rec, user, trace };
}

type Path = "끔" | "켬";
const firstAt = (h: ReturnType<typeof mini>, u: string) => {
  const x = h.seen.find((s) => s.u === u);
  return x ? `${(x.at / 1000).toFixed(0)}s` : "안 옴";
};

// ---------- ⑴ 파일이 늦게 생기는 장면 ----------
// 처음부터 결속 세션은 있고 jsonl 은 없는 좌석(막 켠 마스터). 시각은 대화 화면을 켠 때부터의 초.
async function late(compat: boolean, scene: "send+9" | "send+40" | "nosend" | "clear-nosend") {
  const h = mini({ compat });
  const appear = (text: string) => {
    h.st.noFile = false;
    h.st.file.push(h.user(text));
    h.st.master.working = true;
  };
  const answer = () => {
    h.st.file.push(h.rec(1));
    h.st.master.working = false;
  };
  let fileAt = 0;
  if (scene === "clear-nosend") {
    // watch 가 걸려 있던 좌석 → /clear(새 세션 등록 · 파일 없음) → 데몬이 넣은 복원 지시로 파일이 생김(대화 화면에서 보낸 말 없음)
    await h.start();
    fileAt = 8;
    await h.run(180, {
      2: () => {
        h.st.session = "sess-0002-bbbb";
        h.st.master.registered_session_id = "sess-0002-bbbb";
        h.st.file = [];
        h.st.noFile = true;
      },
      8: () => appear("복원 지시"),
      20: answer,
      150: () => void h.core.submit("다음 말"),
    });
  } else {
    h.st.noFile = true;
    await h.start();
    const sendAt = 10;
    fileAt = scene === "send+9" ? sendAt + 9 : scene === "send+40" ? sendAt + 40 : 20;
    const plan: Record<number, () => void> = { [fileAt]: () => appear("안녕"), [fileAt + 6]: answer, 150: () => void h.core.submit("다음 말") };
    if (scene !== "nosend") plan[sendAt] = () => void h.core.submit("안녕");
    await h.run(180, plan);
  }
  const before150 = h.seen.filter((s) => s.at < 150_000).map((s) => s.u);
  return {
    scene,
    fileAt: `${fileAt}s`,
    answerSeenAt: firstAt(h, "u1"),
    seenBefore150: before150,
    final: h.seen.map((s) => s.u),
    rpc150: 2 * h.calls.filter((c) => c.at < 150_000 && (c.cmd === "chat_transcript" || c.cmd === "chat_transcript_watch")).length,
  };
}

describe("verify-1119-s3 재실행 2 — 파일이 늦게 생기는 장면", () => {
  for (const scene of ["send+9", "send+40", "nosend", "clear-nosend"] as const) {
    it(`늦게 생김 · ${scene} — 답(파일 생긴 뒤 6~12초에 쓰임)이 150초 안에 화면에 온다`, async () => {
      const off = await late(false, scene);
      const on = await late(true, scene);
      console.log(`[L ${scene}] 끔(1.1.19): 파일 ${off.fileAt} · 답 본 때 ${off.answerSeenAt} · 150초 전 ${JSON.stringify(off.seenBefore150)} · 끝 ${JSON.stringify(off.final)} · 150초 RPC ${off.rpc150}`);
      console.log(`[L ${scene}] 켬(1.1.18): 파일 ${on.fileAt} · 답 본 때 ${on.answerSeenAt} · 150초 전 ${JSON.stringify(on.seenBefore150)} · 끝 ${JSON.stringify(on.final)} · 150초 RPC ${on.rpc150}`);
      expect(off.seenBefore150).toContain("u1"); // ★붉음 = 다음 말을 보내기 전까지(150초) 답이 화면에 없음
      // (만든 좌석 옮김 · 고침3 · [master#a5f2e240]) 답 보이는 때를 값으로 — 보낸 뒤 늦게 생김 = 보낸 뒤 ≤ 20초(send+9) · 보낸 뒤 60초 안 = 생긴 뒤 ≤ 20초(send+40) · 보내지 않은 채 = 생긴 뒤 ≤ 31초
      const sec = (x: string) => (x.endsWith("s") ? Number(x.slice(0, -1)) : Infinity);
      const seen = sec(off.answerSeenAt);
      const file = sec(off.fileAt);
      if (scene === "send+9") expect(seen - 10 <= 20).toBe(true);
      else if (scene === "send+40") expect(seen - file <= 20).toBe(true);
      else expect(seen - file <= 31).toBe(true);
    });
  }
});

// ---------- ⑵ 되돌리기 켬 자취(커밋끼리 글자 대조) ----------
async function compatTrace(name: string): Promise<string[]> {
  const h = mini({ compat: true });
  const tag = (lines: string[], extra: string) => [...lines.map((l) => `[TRACE ${name}] ${l}`), `[TRACE ${name}] == ${extra}`];
  const fin = () => `seen=${JSON.stringify(h.seen.map((s) => `${s.u}@${(s.at / 1000).toFixed(0)}`))} steps=${JSON.stringify(h.core.state.msgs.map((m) => m.step))}`;
  if (name === "N2-결속바뀜") {
    await h.start();
    await h.run(18, {
      1: () => {
        h.st.session = "sess-0002-bbbb";
        h.st.master.registered_session_id = "sess-0002-bbbb";
        h.st.file = [h.rec(1)];
      },
      5: () => void h.st.file.push(h.rec(2)),
      8: () => void (h.st.master.working = true),
      11: () => void (h.st.master.working = false),
    });
  } else if (name === "A-clear-파일없음-보냄") {
    await h.start();
    await h.run(60, {
      1: () => {
        h.st.session = "sess-0002-bbbb";
        h.st.master.registered_session_id = "sess-0002-bbbb";
        h.st.file = [];
        h.st.noFile = true;
      },
      4: () => void h.core.submit("안녕"),
      5: () => {
        h.st.noFile = false;
        h.st.file.push(h.user("안녕"));
        h.st.master.working = true;
      },
      10: () => {
        h.st.file.push(h.rec(1));
        h.st.master.working = false;
      },
    });
  } else if (name === "A0-처음부터없음-보냄") {
    h.st.noFile = true;
    await h.start();
    await h.run(60, {
      3: () => void h.core.submit("안녕"),
      4: () => {
        h.st.noFile = false;
        h.st.file.push(h.user("안녕"));
        h.st.master.working = true;
      },
      9: () => {
        h.st.file.push(h.rec(1));
        h.st.master.working = false;
      },
    });
  } else if (name === "B-마스터행빠짐") {
    await h.start();
    await h.run(24, {
      1: () => void (h.st.masterGone = true),
      4: () => void h.st.file.push(h.rec(1), h.rec(2)),
      5: () => void (h.st.masterGone = false),
      9: () => void (h.st.master.working = true),
      13: () => void (h.st.master.working = false),
    });
  } else if (name === "보통-보냄-답-작업화면왕복") {
    await h.start();
    await h.run(40, {
      2: () => void h.core.submit("안녕"),
      3: () => {
        h.st.file.push(h.user("안녕"));
        h.st.master.working = true;
      },
      8: () => {
        h.st.file.push(h.rec(1));
        h.st.master.working = false;
      },
      12: () => {
        h.core.watchStart();
        h.core.detach();
      },
      15: () => {
        h.st.file.push(h.rec(2));
        h.st.master.working = true;
      },
      19: () => void (h.st.master.working = false),
      22: () => {
        h.core.attach();
        h.core.watchStop();
      },
      25: () => void h.core.submit("둘째"),
      26: () => {
        h.st.file.push(h.user("둘째"), h.rec(3));
      },
    });
  } else if (name === "늦게생김-보낸뒤9초") {
    h.st.noFile = true;
    await h.start();
    await h.run(90, {
      10: () => void h.core.submit("안녕"),
      19: () => {
        h.st.noFile = false;
        h.st.file.push(h.user("안녕"));
        h.st.master.working = true;
      },
      25: () => {
        h.st.file.push(h.rec(1));
        h.st.master.working = false;
      },
    });
  }
  return tag(h.trace(), fin());
}

describe("verify-1119-s3 재실행 2 — 되돌리기 켬 자취", () => {
  it("되돌리기 켬 · 장면 6개의 호출 자취를 찍는다(커밋끼리 diff) · 새 명령 0", async () => {
    let newCmds = 0;
    for (const name of ["N2-결속바뀜", "A-clear-파일없음-보냄", "A0-처음부터없음-보냄", "B-마스터행빠짐", "보통-보냄-답-작업화면왕복", "늦게생김-보낸뒤9초"]) {
      const lines = await compatTrace(name);
      newCmds += lines.filter((l) => /chat_transcript_(watch|unwatch|tail)/.test(l)).length;
      console.log(lines.join("\n"));
    }
    expect(newCmds).toBe(0);
  });
});
