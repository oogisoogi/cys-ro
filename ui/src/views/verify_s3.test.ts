// (TICKET=verify-1119-s3 · 독립 검증 좌석 · 기록만) S3 「기록 박자」 반례 재현 시험.
// 스냅샷(526cf0609)의 ui/src/views/ 로 복사해 `bun test src/views/verify_s3.test.ts` 로 돈다. 작업트리에는 두지 않는다.
// 읽는 법: 각 시험은 「바라는 동작」을 단언한다 — 붉음 = 반례 재현. 같은 장면을 되돌리기 켬(= 1.1.18 읽기 길)으로도 돌려
//   대역 장면 자체가 맞는지(1.1.18 길에서는 바라는 동작이 나오는지) 먼저 단언한다(그 단언이 붉으면 내 장면이 틀린 것).
import { describe, it, expect } from "bun:test";
import { ChatCore, type Deps } from "./core";

function vh(o: { compat?: boolean; listenMs?: number; daemonListen?: boolean } = {}) {
  const calls: Array<{ cmd: string; args?: Record<string, unknown>; at: number }> = [];
  let now = 5_000_000;
  const timers: Array<{ at: number; fn: () => void; h: number }> = [];
  let hn = 0;
  const st = {
    master: { surface_id: 5, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false, registered_session_id: "sess-0001-aaaa" } as Record<string, unknown>,
    /** org.status 에 마스터 행이 없다(목록은 옴) */
    masterGone: false,
    file: [] as Array<Record<string, unknown>>,
    session: "sess-0001-aaaa",
    /** 결속된 세션의 jsonl 이 아직 없다(SessionStart 훅이 먼저 등록 · 파일은 첫 입력 때 생김 — cysd handlers.rs:12328 주석) */
    noFile: false,
    watchGen: 0,
    /** tail 이 계속 던진다(Rust tail_on 의 Err — try_clone·metadata·seek·read 실패) */
    tailThrows: false,
  };
  const app = new Map<string, Array<(e: { payload: unknown }) => void>>();
  const later = <T>(ms: number, v: () => T): Promise<T> => (ms <= 0 ? Promise.resolve(v()) : new Promise((res) => timers.push({ at: now + ms, fn: () => res(v()), h: ++hn })));
  const deps: Deps = {
    invoke: async (cmd, args) => {
      calls.push({ cmd, args, at: now });
      if (cmd === "org_status") return { surfaces: st.masterGone ? [] : [st.master] };
      if (cmd === "feed_list") return { items: [] };
      if (cmd === "default_socket_slug") return "slug";
      if (cmd === "chat_send") return { outcome: "written", result: { sent: true } };
      if (cmd === "chat_transcript") {
        const a = args as { afterOffset: number; fromEnd: boolean };
        if (st.noFile) return { status: "unknown", why: "no_file", session_id: st.session };
        if (a.fromEnd) return { status: "ok", session_id: st.session, next_offset: st.file.length, size: st.file.length, records: [] };
        if (a.afterOffset > st.file.length) return { status: "ok", session_id: st.session, next_offset: st.file.length, size: st.file.length, records: st.file.slice(0), reset: true };
        return { status: "ok", session_id: st.session, next_offset: st.file.length, size: st.file.length, records: st.file.slice(a.afterOffset) };
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
        if (st.tailThrows) throw new Error("Bad file descriptor (os error 9)");
        return { status: "ok", session_id: st.session, gen: st.watchGen, from_offset: a.afterOffset, to_offset: st.file.length, next_offset: st.file.length, size: st.file.length, records: st.file.slice(a.afterOffset), reset: false, more: false };
      }
      throw new Error(`unexpected ${cmd}`);
    },
    listenApp: (name, handler) =>
      later(o.listenMs ?? 0, () => {
        const hs = app.get(name) ?? [];
        hs.push(handler);
        app.set(name, hs);
        return () => app.set(name, (app.get(name) ?? []).filter((h) => h !== handler));
      }),
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
  if (o.daemonListen) (deps as Deps & { listen?: unknown }).listen = (_n: string, _h: unknown) => later(o.listenMs ?? 0, () => () => {});
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
  const emit = (payload: Record<string, unknown>) => {
    for (const h of app.get("chat-transcript-changed") ?? []) h({ payload });
  };
  const core = new ChatCore(deps);
  const seenUuids: string[] = [];
  (core.confirm as unknown as { onTail(r: Array<{ uuid?: string }>): void }).onTail = (r) => void seenUuids.push(...r.map((x) => String(x.uuid)));
  const rec = (i: number) => ({ uuid: `u${i}`, parent: null, role: "assistant", text: `답 ${i}`, ts: null });
  const n = (cmd: string) => calls.filter((c) => c.cmd === cmd).length;
  /** 3초 조회 한 번 + 그 사이 1초 틱 둘(앱의 1초 시계 흉내) */
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
  return { core, st, calls, n, flush, advance, emit, rec, seen: () => seenUuids, app, tick3, getNow: () => now };
}

async function watched(h: ReturnType<typeof vh>) {
  h.core.attach();
  await h.flush();
  await h.core.poll();
  await h.advance(10);
}

describe("verify-1119-s3 — 독립 검증 재현", () => {
  // ---------- A ----------
  // /clear(또는 마스터 다시 켜짐): SessionStart 훅이 새 세션을 **먼저** 등록한다 → org.status 의 registered_session_id 가 바뀐 순간
  // 새 jsonl 은 아직 없다(첫 입력 때 생김). 1.1.18 = offset 을 쥔 채 3초마다·보낸 뒤 +1/+3/+7초에 다시 물어 파일이 생기면 따라붙는다.
  async function sceneA(compat: boolean) {
    const h = vh({ compat });
    await watched(h);
    const watchedOk = h.n("chat_transcript_watch");
    h.st.session = "sess-0002-bbbb";
    h.st.master.registered_session_id = "sess-0002-bbbb";
    h.st.file = [];
    h.st.noFile = true; // 새 세션 jsonl 은 아직 없음
    await h.tick3(); // 3초 조회가 결속 바뀜을 본다
    h.core.submit("안녕"); // 사람이 대화 화면에서 말을 보냄
    await h.advance(10);
    const sends = h.n("chat_send");
    h.st.noFile = false; // 첫 입력으로 jsonl 이 생김
    h.st.file.push({ uuid: "user-1", parent: null, role: "user", text: "안녕", ts: null });
    h.st.master.working = true;
    await h.tick3();
    h.st.file.push(h.rec(1)); // 답이 쓰임(보낸 지 약 6초)
    h.st.master.working = false;
    await h.tick3();
    const at9s = [...h.seen()];
    for (let i = 0; i < 12; i++) await h.tick3(); // 그 뒤 36초 더(30초 문이 풀린 뒤까지)
    return { watchedOk, sends, at9s, final: [...h.seen()], step: h.core.state.msgs[0]?.step, fromEnd: h.calls.filter((c) => c.cmd === "chat_transcript" && (c.args as { fromEnd: boolean }).fromEnd).length };
  }

  it("A · /clear 직후 새 jsonl 이 아직 없을 때 — 그 뒤 쓰인 답이 화면에 온다(1.1.18 길에서는 옴)", async () => {
    const old = await sceneA(true);
    const neu = await sceneA(false);
    console.log("[A] 1.1.18 길(되돌리기 켬):", JSON.stringify(old));
    console.log("[A] 1.1.19 길(watch)      :", JSON.stringify(neu));
    expect(old.sends).toBe(1);
    expect(old.final).toContain("u1"); // 장면 검증: 1.1.18 길에서는 답이 온다
    expect(neu.watchedOk).toBe(1);
    expect(neu.sends).toBe(1);
    expect(neu.final).toContain("u1"); // ★붉음 = 반례(답이 끝내 안 옴)
  });

  // ---------- A0(대조 · 정보) ----------
  // 앱을 처음 켰을 때부터 결속 jsonl 이 없는 좌석(막 켠 마스터) — 이 길은 1.1.18 에도 있는 「기록 없음 30초 문」(core.ts:1175-1181)이다.
  // A 가 S3 로 새로 생긴 것인지(= 여기서는 두 길이 같고 A 에서만 갈리는지) 가르려고 둔다.
  async function sceneA0(compat: boolean) {
    const h = vh({ compat });
    h.st.noFile = true;
    await watched(h);
    await h.tick3();
    h.core.submit("안녕");
    await h.advance(10);
    h.st.noFile = false;
    h.st.file.push({ uuid: "user-1", parent: null, role: "user", text: "안녕", ts: null });
    h.st.master.working = true;
    await h.tick3();
    h.st.file.push(h.rec(1));
    h.st.master.working = false;
    for (let i = 0; i < 14; i++) await h.tick3();
    return { sends: h.n("chat_send"), final: [...h.seen()] };
  }

  it("A0 · (대조) 처음부터 jsonl 이 없던 좌석 — 두 길의 결과가 같다(이 길의 유실은 1.1.18 에도 있음 = S3 회귀 아님)", async () => {
    const old = await sceneA0(true);
    const neu = await sceneA0(false);
    console.log("[A0] 1.1.18 길:", JSON.stringify(old), "· 1.1.19 길:", JSON.stringify(neu));
    // (만든 좌석 옮김 · 고침2 · [master#f03515c6] N2 판정) 되돌리기 켬 = 1.1.18 과 같은 동작(이 결함 그대로 · 알고 받는 단점) · 끔 = V1 고침으로 첫 말·답을 받음.
    //   옛 단언 「두 길이 같다」 는 고침 전 「둘 다 잃음」 을 보이던 대조였다.
    expect(old.final).toEqual([]);
    expect(neu.final).toEqual(["user-1", "u1"]);
  });

  // ---------- B ----------
  // org.status 목록에 마스터 행이 한 번 없다(목록은 옴 = null · 모름(undefined) 아님) → 같은 세션으로 돌아옴.
  async function sceneB(compat: boolean) {
    const h = vh({ compat });
    await watched(h);
    h.st.masterGone = true;
    await h.tick3(); // 마스터 행 없음을 본 조회
    h.st.file.push(h.rec(1), h.rec(2)); // 그 사이 마스터가 쓴 것(같은 세션 · 같은 파일)
    h.st.masterGone = false;
    await h.tick3(); // 마스터 행이 돌아옴(결속 id 그대로)
    h.st.master.working = true;
    await h.tick3();
    h.st.master.working = false;
    await h.tick3(); // 1.1.18 길의 읽기 계기(활동 바뀜)
    await h.tick3();
    return { final: [...h.seen()], unwatch: h.n("chat_transcript_unwatch"), watch: h.n("chat_transcript_watch"), fromEnd: h.calls.filter((c) => c.cmd === "chat_transcript" && (c.args as { fromEnd: boolean }).fromEnd).length };
  }

  it("B · 마스터 행이 한 번 빠졌다 같은 세션으로 돌아옴 — 그 사이 덧붙은 레코드를 건너뛰지 않는다(1.1.18 길에서는 읽음)", async () => {
    const old = await sceneB(true);
    const neu = await sceneB(false);
    console.log("[B] 1.1.18 길:", JSON.stringify(old));
    console.log("[B] 1.1.19 길:", JSON.stringify(neu));
    expect(old.final).toEqual(["u1", "u2"]); // 장면 검증
    expect(neu.final).toEqual(["u1", "u2"]); // ★붉음 = 반례(결속이 안 바뀌었는데 끝에서 다시 시작 → 건너뜀)
  });

  // ---------- C ----------
  // tail 이 계속 던진다(쥔 핸들 읽기 실패). 1.1.18 길(경로로 다시 열기)은 멀쩡하다.
  it("C · tail 이 계속 던질 때 — 1.1.18 읽기 길로 내려가 읽는다(watch 를 쥔 채 멈추지 않음)", async () => {
    const h = vh();
    await watched(h);
    h.st.tailThrows = true;
    h.st.file.push(h.rec(1));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 1, reset: false });
    await h.advance(10);
    for (let i = 0; i < 20; i++) {
      h.st.master.working = i % 2 === 0;
      await h.tick3();
    }
    const tails = h.n("chat_transcript_tail");
    const plain = h.calls.filter((c) => c.cmd === "chat_transcript" && !(c.args as { fromEnd: boolean }).fromEnd).length;
    console.log(`[C] 60초 동안: tail 시도 ${tails}회 · 1.1.18 명령 읽기 ${plain}회 · 받은 레코드 ${JSON.stringify(h.seen())}`);
    expect(h.seen()).toContain("u1"); // ★붉음 = 반례(60초 동안 0 · 1.1.18 명령은 한 번도 안 부름)
  });

  // ---------- E ----------
  // 첫 보내기(시작점을 아직 모름): initOffset ok → ensureWatch 가 데몬 RPC 2개짜리 명령을 보내기 길의 둘째 재조회 **앞에** 낸다.
  it("E · 첫 보내기 길 — 시작점 조회와 둘째 재조회(feed_list) 사이에 다른 데몬 조회 명령이 끼지 않는다", async () => {
    const h = vh();
    h.core.attach();
    await h.flush(); // 3초 조회 전(마스터 모름) — 시작점 미정
    const mark = h.calls.length;
    h.core.submit("안녕");
    await h.advance(10);
    const seq = h.calls.slice(mark).map((c) => (c.cmd === "chat_transcript" ? `chat_transcript(fromEnd=${(c.args as { fromEnd: boolean }).fromEnd})` : c.cmd));
    console.log("[E] 보내기 길 호출 순서:", seq.join(" → "));
    const iInit = seq.indexOf("chat_transcript(fromEnd=true)");
    const iSend = seq.indexOf("chat_send");
    expect(iInit).toBeGreaterThanOrEqual(0);
    expect(iSend).toBeGreaterThan(iInit);
    expect(seq.slice(iInit + 1, iSend)).toEqual(["feed_list", "org_status"]); // ★붉음 = chat_transcript_watch 가 그 사이에 낌
  });

  // ---------- F ----------
  // 앱 사건 구독 셋을 차례로 거는 도중(첫째만 등록) 작업 화면 살핌으로 넘어가면(listenGen 바뀜) 남은 둘은 풀리고,
  // unlistenApp.length 가 1 이라 다음 startAppListening 은 바로 돌아간다 → chat-transcript-changed 구독이 영영 없다.
  it("F · 구독을 거는 도중 화면이 바뀌어도 대화 화면으로 돌아오면 기록 사건 구독이 있다", async () => {
    const h = vh({ listenMs: 5, daemonListen: true });
    h.core.attach();
    await h.advance(7); // 첫 앱 사건(boot-degraded) 등록 · 둘째 대기 · 데몬 사건 구독은 대기 중
    const mid = { boot: (h.app.get("boot-degraded") ?? []).length, changed: (h.app.get("chat-transcript-changed") ?? []).length };
    h.core.watchStart(); // 대화 → 작업(새 화면 먼저)
    h.core.detach();
    await h.advance(50);
    h.core.attach(); // 작업 → 대화
    h.core.watchStop();
    await h.advance(50);
    await h.core.poll();
    await h.advance(50);
    const subs = (h.app.get("chat-transcript-changed") ?? []).length;
    h.st.file.push(h.rec(1));
    h.emit({ surface_id: 5, session_id: "sess-0001-aaaa", gen: h.st.watchGen, size: 1, reset: false });
    await h.advance(10);
    console.log(`[F] 도중 등록 ${JSON.stringify(mid)} · 돌아온 뒤 기록 사건 구독 ${subs}개 · watch ${h.n("chat_transcript_watch")}회 · 받은 레코드 ${JSON.stringify(h.seen())}`);
    expect(subs).toBe(1); // ★붉음 = 구독 0(watch 는 걸렸는데 사건을 못 받음)
  });

  // ---------- CH-E(반례 찾기 · 초록이면 「못 찾음」) ----------
  it("CH-E · 되돌리기 켬 = 붙임·살핌·돌아옴·결속 바뀜·reset 사건·뗌 전 과정에서 새 명령(watch·unwatch·tail) 0", async () => {
    const h = vh({ compat: true });
    await watched(h);
    h.core.watchStart();
    h.core.detach();
    await h.tick3();
    h.core.attach();
    h.core.watchStop();
    await h.tick3();
    h.st.session = "sess-0002-bbbb";
    h.st.master.registered_session_id = "sess-0002-bbbb";
    h.st.file = [h.rec(1)];
    await h.tick3();
    h.emit({ surface_id: 5, session_id: "sess-0002-bbbb", gen: 1, size: 1, reset: true });
    h.emit({ surface_id: 5, session_id: "sess-0002-bbbb", gen: 1, size: 2, reset: false });
    h.core.submit("안녕");
    await h.tick3();
    h.st.masterGone = true;
    await h.tick3();
    h.st.masterGone = false;
    await h.tick3();
    h.core.detach();
    await h.advance(50);
    const neu = h.n("chat_transcript_watch") + h.n("chat_transcript_unwatch") + h.n("chat_transcript_tail");
    console.log(`[CH-E] 새 명령 수 = ${neu} · chat_transcript ${h.n("chat_transcript")}회`);
    expect(neu).toBe(0);
  });
});
