// (TICKET=cysr-1116-cc-autoopen-1120) Control Center 가 저절로 열리는 경로 — 「열림/안 열림」을 경로마다 고정한다.
// 원칙(박사님 11-20): 사람이 누르지 않았는데 CC 가 열리는 것은 approval.stalled(승인 방치 · 데몬 판정)뿐 · 그 밖은 토스트·배지만.
//   ① 원인 표(ccopen.ts) — 원인마다 열림/알림만
//   ② openFeed 실물(main.ts 에서 꺼내 돌린다) — feed.grace 는 패널·탭 0 · approval.stalled·사람 원인은 연다
//   ③ 유예 스케줄러 전 구간(probefail 실물 + main.ts 배선 그대로) — 30초/90초 뒤 pending 이어도 CC 0
//   ④ 배선 전수 — main.ts 의 모든 열기 호출은 원인 표의 원인을 싣는다 · 원인 표의 모든 원인은 배선돼 있다(새 자동 경로가 표 없이 못 들어온다)
//   ⑤ 관측 — 열린 순간·막은 순간마다 로그 1줄(ccOpenLogLine) · setCcOpen 이 그것을 부른다
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { CC_OPEN_CAUSES, ccOpenVerdict, ccOpenIsAuto, ccOpenLogLine } from "./ccopen";
import { makeFeedSwitchScheduler } from "./probefail";

const SRC = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const LINES = SRC.split("\n");

function extractFn(name: string): string {
  const re = new RegExp(`^(async )?function ${name}\\(`);
  const starts = LINES.map((l, i) => (re.test(l) ? i : -1)).filter((i) => i >= 0);
  if (starts.length !== 1) throw new Error(`function ${name}: ${starts.length} declarations`);
  const end = LINES.findIndex((l, i) => i > starts[0] && l === "}");
  if (end < 0) throw new Error(`function ${name}: no closing brace`);
  return LINES.slice(starts[0], end + 1).join("\n");
}

// toastaxis.test.ts 와 같은 모양(타입 검사가 bun 전역 타입 없이 통과하게).
const transpiler = new (globalThis as unknown as { Bun: { Transpiler: new (o: { loader: string }) => { transformSync(s: string): string } } }).Bun.Transpiler({ loader: "ts" });

function stripComments(code: string): string {
  return code
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n")
    .map((l) => l.replace(/(^|[^:"'`])\/\/.*$/, "$1"))
    .join("\n");
}

/** main.ts 의 openFeed 실물을 가짜 세계에서 돌린다 — setCcOpen·setCcTab·logCcOpen 은 기록만 · 원인 판정은 실물(ccOpenVerdict). */
function openFeedSandbox(ccOpen = false) {
  const calls = { setCcOpen: [] as unknown[][], setCcTab: [] as unknown[][], logCcOpen: [] as unknown[][] };
  const world: Record<string, unknown> = {
    ccOpen,
    ccOpenVerdict,
    setCcOpen: (...a: unknown[]) => { calls.setCcOpen.push(a); world.ccOpen = a[0]; },
    setCcTab: (...a: unknown[]) => { calls.setCcTab.push(a); },
    logCcOpen: (...a: unknown[]) => { calls.logCcOpen.push(a); },
  };
  const js = transpiler.transformSync(extractFn("openFeed"));
  const openFeed = new Function("__w", `with(__w){ ${js}; return openFeed; }`)(world) as (cause: string) => void;
  return { openFeed, calls, world };
}

describe("① 원인 표 — 저절로 여는 것은 approval.stalled 뿐", () => {
  test("열림/알림만 표", () => {
    expect(CC_OPEN_CAUSES).toEqual({
      "user.button": "open",
      "user.theme_pop": "open",
      "user.palette": "open",
      "user.board_approvals": "open",
      "approval.stalled": "open",
      "ui.open_panel": "open",
      "feed.grace": "notify",
    });
  });
  test("데몬 이벤트 출처(사람 입력 아님)로 여는 원인 = approval.stalled 와 말로 열기(ui.open_panel) 둘뿐", () => {
    const autoOpen = Object.keys(CC_OPEN_CAUSES).filter((c) => ccOpenIsAuto(c) && ccOpenVerdict(c) === "open");
    expect(autoOpen.sort()).toEqual(["approval.stalled", "ui.open_panel"]);
  });
  test("feed 유예 만료 = 알림만 · 표에 없는 원인 = 알림만(fail-closed)", () => {
    expect(ccOpenVerdict("feed.grace")).toBe("notify");
    expect(ccOpenVerdict("watchdog.proc_count_high")).toBe("notify");
    expect(ccOpenVerdict("unknown")).toBe("notify");
    expect(ccOpenVerdict("toString")).toBe("notify"); // 프로토타입 이름이 표를 뚫지 못한다
  });
});

describe("② openFeed 실물 — 경로별 열림/안 열림", () => {
  test("feed.grace(30초/90초 유예 만료) → 패널 안 열림 · 탭 안 바뀜 · 막은 줄 1개", () => {
    const sb = openFeedSandbox(false);
    sb.openFeed("feed.grace");
    expect(sb.calls.setCcOpen).toEqual([]);
    expect(sb.calls.setCcTab).toEqual([]);
    expect(sb.calls.logCcOpen).toEqual([[false, "feed.grace", false]]);
  });
  test("feed.grace 는 이미 열린 CC 의 탭도 빼앗지 않는다", () => {
    const sb = openFeedSandbox(true);
    sb.openFeed("feed.grace");
    expect(sb.calls.setCcTab).toEqual([]);
  });
  test("approval.stalled → 열림 + 승인 Feed 탭", () => {
    const sb = openFeedSandbox(false);
    sb.openFeed("approval.stalled");
    expect(sb.calls.setCcOpen).toEqual([[true, "approval.stalled"]]);
    expect(sb.calls.setCcTab).toEqual([["feed"]]);
  });
  test("사람이 누른 것(상태판 「승인 요청 N」 · 팔레트) → 열림", () => {
    for (const c of ["user.board_approvals", "user.palette"]) {
      const sb = openFeedSandbox(false);
      sb.openFeed(c);
      expect([c, sb.calls.setCcOpen]).toEqual([c, [[true, c]]]);
    }
  });
  test("이미 열려 있으면 다시 열지 않고 탭만", () => {
    const sb = openFeedSandbox(true);
    sb.openFeed("approval.stalled");
    expect(sb.calls.setCcOpen).toEqual([]);
    expect(sb.calls.setCcTab).toEqual([["feed"]]);
  });
});

describe("③ 유예 스케줄러 전 구간 — pending 이 남아도 CC 는 안 열린다", () => {
  async function run(autoRoute: boolean, feed: unknown) {
    const sb = openFeedSandbox(false);
    const timers: (() => Promise<void>)[] = [];
    const schedule = makeFeedSwitchScheduler({
      setTimer: (fn) => { timers.push(fn); },
      feedList: () => (feed instanceof Error ? Promise.reject(feed) : Promise.resolve(feed)),
      ceoActive: () => Promise.resolve(false),
      open: () => sb.openFeed("feed.grace"), // main.ts 배선 그대로(아래 ④ 가 소스에서 핀)
    });
    schedule("r1", autoRoute);
    for (let i = 0; i < 20 && timers.length; i++) await timers.shift()!();
    return sb;
  }
  test("30초 유예(--wait) 뒤 pending → 열림 0 · 막은 줄 1", async () => {
    const sb = await run(false, { items: [{ request_id: "r1", status: "pending" }] });
    expect(sb.calls.setCcOpen.length).toBe(0);
    expect(sb.calls.logCcOpen).toEqual([[false, "feed.grace", false]]);
  });
  test("90초 유예(auto_route) 뒤 pending → 열림 0", async () => {
    const sb = await run(true, { items: [{ request_id: "r1", status: "pending" }] });
    expect(sb.calls.setCcOpen.length).toBe(0);
  });
  test("조회 2회 실패(종전 「보여 주는 쪽으로 실패」) → 열림 0", async () => {
    const sb = await run(false, new Error("daemon down"));
    expect(sb.calls.setCcOpen.length).toBe(0);
  });
  test("결재됨 → 아무것도 안 함(로그도 0)", async () => {
    const sb = await run(false, { items: [{ request_id: "r1", status: "resolved" }] });
    expect([sb.calls.setCcOpen.length, sb.calls.logCcOpen.length]).toEqual([0, 0]);
  });
});

describe("④ 배선 전수 — main.ts 의 모든 열기 호출은 원인 표를 지난다", () => {
  const code = stripComments(SRC);
  const causes = new Set(Object.keys(CC_OPEN_CAUSES));
  test("openFeed( 호출은 전부 원인 문자열을 싣는다 · 원인 없는 호출 0", () => {
    const calls = [...code.matchAll(/(?<![A-Za-z0-9_.])openFeed\(([^)]*)\)/g)].map((m) => m[1].trim());
    const uses = calls.filter((a) => a !== "cause: CcOpenCause"); // 정의
    expect(uses.length).toBeGreaterThan(0);
    for (const a of uses) expect([a, /^"[a-z_.]+"$/.test(a) && causes.has(a.slice(1, -1))]).toEqual([a, true]);
  });
  test("setCcOpen( 여는 호출(false 아님)은 전부 원인을 싣는다 — openFeed 안의 위임 하나만 변수", () => {
    const calls = [...code.matchAll(/(?<![A-Za-z0-9_.])setCcOpen\(([^)]*)\)/g)].map((m) => m[1].trim());
    const opening = calls.filter((a) => a !== "false" && a !== "open: boolean, cause?: CcOpenCause");
    expect(opening.length).toBeGreaterThan(0);
    for (const a of opening) {
      const m = a.match(/^(true|!ccOpen), (.+)$/);
      expect([a, !!m]).toEqual([a, true]);
      const c = m![2];
      expect([a, c === "cause" || (/^"[a-z_.]+"$/.test(c) && causes.has(c.slice(1, -1)))]).toEqual([a, true]);
    }
    expect(opening.filter((a) => a.endsWith(", cause"))).toEqual(["true, cause"]); // 변수 원인 = openFeed 위임 하나
    expect(extractFn("openFeed")).toContain("if (!ccOpen) setCcOpen(true, cause);");
  });
  test("원인 표의 원인은 전부 main.ts 에 배선돼 있다(죽은 원인 0) · 표 밖 원인 0", () => {
    const used = new Set([...code.matchAll(/(?:openFeed\(|setCcOpen\((?:true|!ccOpen), )"([a-z_.]+)"\)/g)].map((m) => m[1]));
    expect([...used].sort()).toEqual([...causes].sort());
  });
  test("자리별 원인 — 데몬 이벤트 두 곳 · 스케줄러 · 사람 단추", () => {
    const ev = stripComments(extractFn("onDaemonEvent"));
    const st = ev.slice(ev.indexOf('name === "approval.stalled"'), ev.indexOf('name === "context.threshold"'));
    expect(st).toContain('openFeed("approval.stalled");');
    expect(ev).toContain('if (payload.panel === "control-center") setCcOpen(true, "ui.open_panel");');
    expect(code).toMatch(/^\s*open: \(\) => openFeed\("feed\.grace"\),/m);
    expect(code).toContain('document.getElementById("btn-cc")!.addEventListener("click", () => setCcOpen(!ccOpen, "user.button"));');
    // 그 밖의 데몬 이벤트(경보·워치독·건강·피드 생성 등) 분기는 CC 를 열지 않는다 — onDaemonEvent 안의 여는 호출은 위 둘뿐
    const opens = [...ev.matchAll(/(?<![A-Za-z0-9_.])(openFeed\("[^"]+"\)|setCcOpen\((?:true|!ccOpen)[^)]*\))/g)].map((m) => m[1]);
    expect(opens).toEqual(['setCcOpen(true, "ui.open_panel")', 'openFeed("approval.stalled")']);
  });
});

describe("⑤ 관측 — CC 가 열린 순간·막은 순간마다 원인 1줄", () => {
  const at = new Date(2026, 10, 20, 7, 33, 5, 9);
  test("닫힘→열림 = 1줄(auto/user · opened · cause)", () => {
    expect(ccOpenLogLine({ wasOpen: false, cause: "approval.stalled", opened: true }, at)).toMatch(
      /^2026-11-20T07:33:05\.009[+-]\d{4} cc-open auto opened cause=approval\.stalled$/,
    );
    expect(ccOpenLogLine({ wasOpen: false, cause: "user.button", opened: true }, at)).toContain(" cc-open user opened cause=user.button");
  });
  test("이미 열려 있었다 = 전이 아님 → 줄 없음 · 막은 것은 열려 있어도 1줄", () => {
    expect(ccOpenLogLine({ wasOpen: true, cause: "user.button", opened: true }, at)).toBeNull();
    expect(ccOpenLogLine({ wasOpen: true, cause: "feed.grace", opened: false }, at)).toContain(" cc-open auto suppressed cause=feed.grace");
  });
  test("한 원인 = 한 줄(개행·공백 접기 · 길이 상한)", () => {
    const l = ccOpenLogLine({ wasOpen: false, cause: "x\ny", opened: true, detail: "a b\nc" + "z".repeat(300) }, at)!;
    expect(l.includes("\n")).toBe(false);
    expect(l).toContain("cause=x_y detail=a_b_c");
    expect(l.length).toBeLessThan(300);
  });
  test("setCcOpen 은 여는 순간 원인 줄을 남긴다(상태 바꾸기 전 · 원인 없으면 unknown) · 로그 경로 = log_cc_open", () => {
    const body = stripComments(extractFn("setCcOpen"));
    const i = body.indexOf('if (open) logCcOpen(ccOpen, cause ?? "unknown", true);');
    expect(i).toBeGreaterThan(0);
    expect(i).toBeLessThan(body.indexOf("ccOpen = open;"));
    expect(stripComments(extractFn("logCcOpen"))).toContain('void invoke("log_cc_open", { line }).catch(() => {});');
  });
});
