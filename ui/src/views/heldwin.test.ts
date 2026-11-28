// (TICKET=cysr-chat-held-win) 윈 대화 화면 「붙잡아 둠 · 마스터 상태 확인이 늦어져서」 재현·회귀 시험.
// 모형(src-tauri/src/main.rs RPC_POOL 그대로): 앱의 데몬 RPC 는 소켓당 **연결 1개를 직렬로** 나눠 쓴다 → invoke 는 앞 호출이 끝난 뒤 시작한다.
// 윈 = chat_transcript 가 결속 파일을 못 연다(viewcore.rs open_bound = unsupported_platform) → {status:"unknown"} · 고치기 전에는 그 전에 데몬 RPC 2개(surface.list·org.status)를 같은 연결로 불렀다.
// ★1.1.17(cysr-1118-ui ①-4): 윈도 open_bound 를 구현해 새 판 윈은 맥 꼴(ok)이다 — 이 「win」 모형은 결속 기록을 못 여는 좌석(1.1.16 윈 · 링크 거부·세션 미등록)의 회귀 시험으로 남긴다.
// 판정 단위 = chat_send 호출 수(원자 제출 1 = 쓰기 1).
import { describe, it, expect } from "bun:test";
import { ChatCore, needsClick, OBS_MAX_MS, POLL_MS, STATUS_SLOW, type Deps } from "./core";
import { CHAT_QUIET_SECS, CHAT_STATUS_FRESH_SECS, chatWorking } from "./judge/gate";
import { nodeWorking, STATUS_FRESH_SECS } from "../appearance";

type Mode = "mac" | "win";

function sim(o: { mode: Mode; lat: (cmd: string) => number; winInnerRpcs?: number; serial?: boolean; master?: Record<string, unknown>; working?: (r: Record<string, unknown>) => boolean; chatWorking?: (r: Record<string, unknown>) => boolean; busyPasteOk?: boolean }) {
  const calls: string[] = [];
  const mem = new Map<string, string>();
  let now = 1_000_000;
  let hn = 0;
  const timers: Array<{ at: number; fn: () => void; h: number }> = [];
  let busyUntil = 0; // 연결 1개 직렬(풀)
  let sends = 0;
  const st = {
    master: o.master ?? { surface_id: 492, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false },
    hang: new Set<string>(),
  };
  const setT = (fn: () => void, ms: number) => {
    const h = ++hn;
    timers.push({ at: now + ms, fn, h });
    return h;
  };
  const answer = (cmd: string, args?: Record<string, unknown>): unknown => {
    if (cmd === "org_status") return { surfaces: [st.master] };
    if (cmd === "feed_list") return { items: [] };
    if (cmd === "chat_send") {
      sends++;
      return { outcome: "written", result: { sent: true } };
    }
    if (cmd === "chat_transcript") {
      if (o.mode === "win") return { status: "unknown", why: "unsupported_platform" };
      const a = args as { fromEnd: boolean };
      return a.fromEnd ? { status: "ok", session_id: "s1", next_offset: 0, size: 0, records: [] } : { status: "ok", session_id: "s1", next_offset: 0, size: 0, records: [] };
    }
    return null; // 메뉴바·결과 장부 등 다른 조회 — 연결은 똑같이 차지한다
  };
  const deps: Deps = {
    invoke: (cmd, args) => {
      calls.push(cmd);
      if (st.hang.has(cmd)) return new Promise<unknown>(() => {});
      // 윈 chat_transcript 는 그 안에서 데몬 RPC 를 더 부른다(고치기 전 surface.list·org.status = 2) — 같은 연결을 그만큼 더 쓴다.
      const inner = cmd === "chat_transcript" && o.mode === "win" ? (o.winInnerRpcs ?? 2) : 0;
      const cost = o.lat(cmd) * (1 + inner);
      // serial(기본) = 연결 1개 직렬(풀) · false = 호출마다 따로 걸림(웹뷰→Tauri 다리 자체가 느린 경우)
      if (o.serial === false) return new Promise((res) => setT(() => res(answer(cmd, args)), cost));
      const start = Math.max(now, busyUntil);
      busyUntil = start + cost;
      return new Promise((res) => setT(() => res(answer(cmd, args)), busyUntil - now));
    },
    now: () => now,
    setTimeout: setT,
    clearTimeout: (h) => {
      const i = timers.findIndex((t) => t.h === h);
      if (i >= 0) timers.splice(i, 1);
    },
    store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v), remove: (k) => void mem.delete(k) },
    working: o.working ?? ((r) => r.working === true),
    busyPasteOk: o.busyPasteOk,
    chatWorking: o.chatWorking,
  };
  const flush = async () => {
    for (let i = 0; i < 30; i++) await Promise.resolve();
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
  let polling = false;
  const startPolling = () => {
    if (polling) return;
    polling = true;
    const tick = () => {
      void core.poll();
      setT(tick, POLL_MS);
    };
    setT(tick, POLL_MS);
  };
  return { core, deps, st, calls, advance, flush, startPolling, sends: () => sends };
}

/** 대화 화면을 켜고 첫 조회가 돌 때까지. */
async function ready(s: ReturnType<typeof sim>): Promise<void> {
  s.core.attach();
  s.startPolling();
  await s.advance(POLL_MS + 5_000);
}

describe("대조군 — 같은 지연에서 맥은 보내고 윈은 붙잡던 길(원인 재현)", () => {
  for (const [mode, inner] of [["mac", 0], ["win", 2], ["win", 0]] as const) {
    it(`${mode}(윈 chat_transcript 안쪽 RPC ${inner}): invoke 180ms(직렬) — 첫 보내기가 그 자리에서 쓰인다 · 쓰기 전 invoke = feed_list·org_status 2개뿐`, async () => {
      const s = sim({ mode, lat: () => 180, winInnerRpcs: inner });
      await ready(s);
      const before = s.calls.length;
      void s.core.submit("cysr 이번 업데이트에 대해 설명해줘");
      await s.advance(1_500);
      const path = s.calls.slice(before);
      const upto = path.indexOf("chat_send");
      expect([mode, s.sends()]).toEqual([mode, 1]);
      expect([mode, path.slice(0, upto)]).toEqual([mode, ["feed_list", "org_status"]]);
      expect(s.core.state.msgs[0].step).not.toBe("held");
    });
  }
  it("win: 3초 조회 고리가 결속 기록 없음(none)을 안 뒤에는 시작점 조회를 매 틱 다시 부르지 않는다(30초에 1회 이하)", async () => {
    const s = sim({ mode: "win", lat: () => 20 });
    await ready(s);
    const before = s.calls.filter((c) => c === "chat_transcript").length;
    await s.advance(60_000);
    const after = s.calls.filter((c) => c === "chat_transcript").length;
    expect(after - before).toBeLessThan(3);
  });
});

describe("ⓐ 관측 기반 상한 — 느린 RPC(600~1500ms)에서도 붙잡힘 → 전달 · 두 번 0", () => {
  for (const mode of ["mac", "win"] as const) {
    for (const lat of [600, 1_000, 1_500]) {
      it(`${mode} · invoke ${lat}ms(호출마다): 결국 쓰기 1 · 그 뒤 60초 동안 더 쓰지 않음`, async () => {
        const s = sim({ mode, lat: () => lat, serial: false });
        await ready(s);
        void s.core.submit("느린 기계에서 보낸 말");
        await s.advance(30_000);
        expect([mode, lat, s.sends()]).toEqual([mode, lat, 1]);
        await s.advance(60_000);
        expect([mode, lat, s.sends()]).toEqual([mode, lat, 1]);
        expect(s.core.state.msgs).toHaveLength(1);
        expect(s.core.state.msgs[0].step).not.toBe("held");
      });
    }
  }
  it("빠른 기계(5ms)는 상한이 바닥(OBS_MAX_MS)에 머문다 — 멈춘 org_status 는 그대로 바닥 시간에 붙잡힘(쓰기 0)", async () => {
    const s = sim({ mode: "mac", lat: () => 5 });
    await ready(s);
    s.st.hang.add("org_status");
    void s.core.submit("말");
    await s.advance(2 * OBS_MAX_MS + 20);
    expect(s.core.state.msgs[0].step).toBe("held");
    expect(s.sends()).toBe(0);
  });
  it("천장 — 2.5초씩 걸리는 조회는 관측 기반이어도 쓰기 근거가 못 된다(쓰기 0 · 붙잡음)", async () => {
    const s = sim({ mode: "mac", lat: () => 2_500, serial: false });
    await ready(s);
    void s.core.submit("말");
    await s.advance(40_000);
    expect(s.sends()).toBe(0);
    expect(s.core.state.msgs[0].step).toBe("held");
  });
});

describe("ⓑ 같은 까닭(상태 확인 늦음) 3회 연속 = 자동 전송 멈춤 + 안내 · 사람 클릭 1회로만", () => {
  it("org_status 가 계속 멈춤 → 3회째 붙잡힘에서 클릭 대기(작업 화면 직접 입력 안내) · 풀려도 자동으로 안 나감 · 클릭 = 쓰기 1", async () => {
    const s = sim({ mode: "win", lat: () => 5 });
    await ready(s);
    s.st.hang.add("org_status");
    void s.core.submit("멈춘 동안 보낸 말");
    await s.advance(20_000);
    const m = s.core.state.msgs[0];
    expect(m.step).toBe("held");
    expect(m.code).toBe(STATUS_SLOW);
    expect(needsClick(m)).toBe(true);
    expect(m.note).toMatch(/작업 화면/);
    s.st.hang.delete("org_status");
    await s.advance(60_000);
    expect(s.sends()).toBe(0); // 사람이 작업 화면에 직접 쳤을 수 있다 — 자동으로 또 보내지 않는다
    void s.core.confirmHeld(s.core.state.msgs[0].id); // 가짜 시계 — 기다리지 않고 시계를 민다
    await s.advance(2_000);
    expect(s.sends()).toBe(1);
    await s.advance(30_000);
    expect(s.sends()).toBe(1);
  });
  it("한두 번 늦었다가 풀리면 그대로 자동 전송(클릭 불요) · 쓰기 1", async () => {
    const s = sim({ mode: "win", lat: () => 5 });
    await ready(s);
    s.st.hang.add("org_status");
    void s.core.submit("잠깐 늦은 말");
    await s.advance(OBS_MAX_MS * 2 + 50); // 1회 붙잡힘
    expect(s.core.state.msgs[0].step).toBe("held");
    s.st.hang.delete("org_status");
    await s.advance(10_000);
    expect(s.sends()).toBe(1);
  });
});

describe("붙잡힌 까닭이 바뀌면 안내도 지금 까닭으로", () => {
  it("상태 확인 늦음으로 붙잡힌 뒤 마스터가 답하는 중 → 안내 = 답하는 중(옛 「상태 확인이 늦어져서」를 남기지 않음) · 쓰기 0 · 끝나면 쓰기 1", async () => {
    const s = sim({ mode: "win", lat: () => 5, busyPasteOk: false }); // (K-3) 「답하는 중」 붙잡음 = 되돌리기 판 동작
    await ready(s);
    s.st.hang.add("org_status");
    void s.core.submit("말");
    await s.advance(OBS_MAX_MS * 2 + 50);
    expect(s.core.state.msgs[0].note).toMatch(/상태 확인이 늦어져서/);
    s.st.hang.delete("org_status");
    (s.st.master as Record<string, unknown>).working = true;
    await s.advance(POLL_MS * 2);
    expect(s.sends()).toBe(0);
    expect(s.core.state.msgs[0].step).toBe("held");
    expect(s.core.state.msgs[0].note).not.toMatch(/상태 확인이 늦어져서/);
    expect(s.core.state.msgs[0].code).toBe("busy");
    (s.st.master as Record<string, unknown>).working = false;
    await s.advance(POLL_MS * 2);
    expect(s.sends()).toBe(1);
  });
});

/** main.ts bootViews 와 같은 앱 공통 판정(appearance.nodeWorking) — 자기 신고 신선(≤120초)이면 그 state · 아니면 출력 60초 안 = 일하는 중. */
const appWorking = (n: Record<string, unknown>): boolean => nodeWorking(n.status as Parameters<typeof nodeWorking>[0], n.idle_secs as number | null | undefined, n.exited === true);

describe("대화 화면 「답하는 중」 — 자기 신고(status) 없는 마스터는 출력 10초 정적이면 쉬는 중(앱 공통 60초 대신)", () => {
  it("문턱 값은 appearance 와 맞물린다(신선 120초 동일)", () => {
    expect(CHAT_STATUS_FRESH_SECS).toBe(STATUS_FRESH_SECS);
    expect(CHAT_QUIET_SECS).toBeLessThan(60);
  });
  it("순수 판정: status 없음 = idle_secs 로(≤10 일함 · >10 쉼) · status 신선 = 앱 판정 그대로 · status 낡음 = idle_secs 로 · 끝난 좌석 = 쉼 · idle 모름 = 앱 판정", () => {
    const row = (o: Record<string, unknown>) => ({ surface_id: 1, role: "master", ...o });
    expect(chatWorking(row({ idle_secs: 0 }), appWorking)).toBe(true);
    expect(chatWorking(row({ idle_secs: 10 }), appWorking)).toBe(true);
    expect(chatWorking(row({ idle_secs: 11 }), appWorking)).toBe(false);
    expect(appWorking(row({ idle_secs: 11 }))).toBe(true); // 고치기 전 판정 = 60초까지 「답하는 중」
    expect(chatWorking(row({ idle_secs: 999, status: { state: "working", age_secs: 30 } }), appWorking)).toBe(true);
    expect(chatWorking(row({ idle_secs: 0, status: { state: "idle", age_secs: 30 } }), appWorking)).toBe(false);
    expect(chatWorking(row({ idle_secs: 30, status: { state: "working", age_secs: 376 } }), appWorking)).toBe(false);
    expect(chatWorking(row({ idle_secs: 0, exited: true }), appWorking)).toBe(false);
    expect(chatWorking(row({ idle_secs: null }), appWorking)).toBe(appWorking(row({ idle_secs: null })));
  });
  it("통합(윈 좌석 492 꼴 · status 없음): 답을 마치고 출력 20초 정적 → 바로 씀(고치기 전 = 60초까지 「답하는 중」 붙잡힘) · 출력 중(0초)엔 붙잡음", async () => {
    const master: Record<string, unknown> = { surface_id: 492, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, idle_secs: 0, status: null };
    const s = sim({ mode: "win", lat: () => 5, master, working: appWorking, chatWorking: (r) => chatWorking(r, appWorking), busyPasteOk: false }); // index.ts bootViews 배선 그대로 · (K-3) 붙잡음 판정 = 되돌리기 판 동작
    await ready(s);
    void s.core.submit("출력 중에 보낸 말");
    await s.advance(1_000);
    expect(s.sends()).toBe(0);
    expect(s.core.state.msgs[0].code).toBe("busy");
    master.idle_secs = 20; // 답을 마침 · 20초 정적
    await s.advance(POLL_MS * 2);
    expect(s.sends()).toBe(1);
    expect(s.core.state.health).toBe("ready");
  });
});
