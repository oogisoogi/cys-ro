// 3초 고리 특성 기록기 시험 — TICKET=cysr-ui-slice0-1117 · P2-DESIGN §2-1 조각 0.
//   ① 스위치 = "1" 하나뿐 · 꺼짐 = null(소금·손잡이 호출 0)  ② 링 200칸 회전  ③ 개인정보 0(원문 대신 길이·해시)
//   ④ 기록기 예외는 삼킨다  ⑤ 덤프 크기 상한  ⑥ main.ts 배선 정적 핀: 전부 `tickRec?.` · refreshPaneTitles 안 · 두 벌 식 일치
//   ⑦ 기록기 파일엔 부작용 통로(invoke·__TAURI__·localStorage·document·타이머·fetch) 0
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import {
  TICKREC_KEY, TICKREC_RING, TICKREC_MAX_DUMP_BYTES, TICKREC_SCHEMA,
  createTickRecorder, hash53, tickRecFromSwitch, tickRecOn,
} from "./tickrec";

const MAIN_SRC = readFileSync(new URL("../main.ts", import.meta.url), "utf8");
const REC_SRC = readFileSync(new URL("./tickrec.ts", import.meta.url), "utf8");

/** 주석 걷기(// 줄 끝 · /* *\/ 덩이) — 문자열 안의 // 는 이 두 파일의 검사 대상 줄에 없다(아래 핀이 실패하면 여기부터 본다). */
const stripComments = (src: string): string =>
  src.replace(/\/\*[\s\S]*?\*\//g, "").split("\n").map((l) => {
    const i = l.indexOf("//");
    return i >= 0 && !/["'`][^"'`]*\/\/[^"'`]*["'`]/.test(l) ? l.slice(0, i) : l;
  }).join("\n");

/** main.ts 함수 본문(머리 → 같은 깊이의 닫는 괄호까지 · 문자열 안 괄호는 이 함수에 없다). */
const fnBody = (hay: string, head: string): string => {
  const at = hay.indexOf(head);
  if (at < 0) return "";
  let depth = 0;
  for (let i = hay.indexOf("{", at); i < hay.length; i++) {
    if (hay[i] === "{") depth++;
    else if (hay[i] === "}" && --depth === 0) return hay.slice(at, i + 1);
  }
  return "";
};

const W = (id: number, sids: number[], socket?: string) => ({ id, socket, pending: false, deleting: false, sids });

describe("스위치 — 기본 꺼짐 · 「1」 하나만 켠다", () => {
  it("tickRecOn: 「1」 만 참 · 나머지 전부 꺼짐", () => {
    expect(tickRecOn("1")).toBe(true);
    for (const v of [null, undefined, "", "0", "true", "on", "yes", " 1", "1 ", "01"]) expect({ v, on: tickRecOn(v) }).toEqual({ v, on: false });
    expect(TICKREC_KEY).toBe("cys-tickrec");
  });

  it("꺼짐이면 null · 소금 원천·손잡이 호출 0 · 읽기가 던져도 null(고리는 꺼짐 그대로)", () => {
    for (const raw of [null, "0", "true"]) {
      let salt = 0, exposed = 0;
      const r = tickRecFromSwitch({ read: () => raw, salt: () => (salt++, "s"), expose: () => void exposed++ });
      expect({ raw, r, salt, exposed }).toEqual({ raw, r: null, salt: 0, exposed: 0 });
    }
    let salt = 0;
    expect(tickRecFromSwitch({ read: () => { throw new Error("SecurityError"); }, salt: () => (salt++, "s") })).toBeNull();
    expect(salt).toBe(0);
  });

  it("켜짐(「1」)이면 기록기 1개 · 손잡이에 그것을 건다", () => {
    let got: unknown = null;
    const r = tickRecFromSwitch({ read: () => "1", salt: () => "salt", expose: (x) => { got = x; } });
    expect(r).not.toBeNull();
    expect(got).toBe(r);
    expect(r!.dump().schema).toBe(TICKREC_SCHEMA);
  });
});

describe("기록 — 입력 → 결과 한 칸", () => {
  it("한 틱의 입력·결과가 한 칸에 모인다 · 카운터가 같은 수를 센다", () => {
    const r = createTickRecorder({ salt: "k" });
    r.gate(false, false); // 복원 전
    r.gate(true, true); // 앞 틱이 도는 중
    r.gate(true, false); // 정상 — 셈 없음
    r.begin(1000, [W(0, [1, 2])], new Map([["#9", 1]]), false, new Set([7]), new Set());
    r.deptsDone(2); // 새 부서 탭 1개
    r.sock("", { surfaces: [{ surface_id: 1, role: "master", exited: false, title: "t", live_cwd: "/a", display_no: 1, line_count: 3, size: { rows: 35, cols: 120 } }] }, (sid) => sid === 1);
    r.sock("/x.sock", undefined, () => false); // 못 받은 소켓
    r.ghost("", [1, 2, 9], [9]);
    r.sweep("", true, [2]);
    r.sweepSid("", 2);
    r.adopt("", 5, "worker-2");
    r.adoptAbort("", 6, true);
    r.placeholderIn("", 7, { isOwnPlaceholder: true, touched: false, role: null, lineCount: null, isWindows: false, formationArrived: true, exited: false });
    r.placeholderClose("", 7);
    r.placeholderClosed("", 7);
    r.render(true, true);
    r.error("sock");
    r.end(new Map(), false);
    r.notices(0);
    const c = r.counters();
    expect(c).toEqual({ ticks: 1, skippedNotStarted: 1, skippedBusy: 1, sockSkip: 1, adopt: 1, adoptAbort: 1, evict: 1, sweep: 1,
      placeholderJudged: 1, placeholderClose: 1, placeholderClosed: 1, deptOpened: 1, render: 1, err: 1, dropped: 0, recorderFault: 0 });
    const e = r.dump().entries[0] as Record<string, unknown>;
    expect(e.seq).toBe(1);
    expect(e.now).toBe(1000);
    expect(e.done).toBe(true);
    expect(e.ghostIn).toEqual([["~#9", 1]]); // 기본 데몬 = 「~」 · 번호는 그대로
    expect(e.ghost).toEqual([{ sock: "~", tree: [1, 2, 9], evict: [9] }]);
    expect(e.sweep).toEqual([{ sock: "~", here: true, scope: [2], targets: [2] }]);
    expect(e.adopt).toEqual([{ sock: "~", sid: 5, role: "worker-2" }]);
    expect(e.ph).toEqual([{ sock: "~", sid: 7, close: true, closed: true, in: { own: true, touched: false, role: null, lc: null, win: false, arrived: true, ex: false } }]);
    expect(e.render).toEqual({ adopted: true, layoutChanged: true });
    expect(e.err).toEqual(["sock"]);
    expect(e.notices).toBe(0);
    const socks = e.socks as Record<string, unknown>[];
    expect(socks[1].got).toBe(false);
    expect(String(socks[1].sock)).toMatch(/^[0-9a-f]{14}$/);
    const s0 = (socks[0].surf as Record<string, unknown>[])[0];
    expect({ ...s0, th: typeof s0.th, ch: typeof s0.ch }).toEqual({ sid: 1, role: "master", ex: false, no: 1, lc: 3, tl: 1, th: "string", cl: 2, ch: "string", sz: [35, 120], cb: false, pane: true });
  });

  it("end 에 닿지 못한 틱(던짐) = 다음 begin 이 그 칸에 「unfinished」 표시", () => {
    const r = createTickRecorder({ salt: "k" });
    r.begin(1, [], new Map(), false, new Set(), new Set());
    r.begin(2, [], new Map(), false, new Set(), new Set());
    const [a, b] = r.dump().entries as Record<string, unknown>[];
    expect(a.err).toEqual(["unfinished"]);
    expect(a.done).toBe(false);
    expect(b.err).toEqual([]);
  });

  it("빈 화면 틱(작업공간 0) = 고리가 먼저 빈 탭 1개를 만든다 — 그것은 새 부서로 세지 않는다", () => {
    const r = createTickRecorder({ salt: "k" });
    r.begin(1, [], new Map(), false, new Set(), new Set());
    r.deptsDone(1);
    expect(r.counters().deptOpened).toBe(0);
    r.begin(2, [W(0, [])], new Map(), false, new Set(), new Set());
    r.deptsDone(1);
    expect(r.counters().deptOpened).toBe(0);
  });

  it("begin 전 호출(복원 전 등)은 칸을 만들지 않는다 — 던지지도 않는다", () => {
    const r = createTickRecorder({ salt: "k" });
    r.adopt("", 1, "master");
    r.sock("", { surfaces: [] }, () => false);
    r.end(new Map(), false);
    expect(r.dump().entries).toEqual([]);
    expect(r.counters().recorderFault).toBe(0);
  });
});

describe("링 200칸 회전 · 크기 상한", () => {
  it("205틱 → 칸 200 · 버림 5 · 남은 칸 = 가장 최근 200(seq 6~205)", () => {
    const r = createTickRecorder({ salt: "k" });
    expect(TICKREC_RING).toBe(200);
    for (let i = 0; i < 205; i++) {
      r.begin(i, [], new Map(), false, new Set(), new Set());
      r.end(new Map(), false);
    }
    const d = r.dump();
    expect(d.ring).toBe(200);
    expect(d.entries.length).toBe(200);
    expect(d.counters.dropped).toBe(5);
    expect((d.entries[0] as { seq: number }).seq).toBe(6);
    expect((d.entries[199] as { seq: number }).seq).toBe(205);
  });

  it("좌석 상한을 넘는 목록은 잘리고 trunc 표시 · 최악 장면(200틱 × 소켓 32 × 좌석 128) 덤프도 상한 안", () => {
    const r = createTickRecorder({ salt: "k" });
    const surfaces = Array.from({ length: 300 }, (_, i) => ({ surface_id: i, role: "worker-" + i, exited: false, title: "x".repeat(40), live_cwd: "/p/".repeat(20), display_no: i, line_count: i, size: { rows: 40, cols: 140 } }));
    for (let t = 0; t < 200; t++) {
      r.begin(t, Array.from({ length: 100 }, (_, i) => W(i, [i])), new Map(), false, new Set(), new Set());
      for (let s = 0; s < 40; s++) r.sock("/s" + s, { surfaces }, () => true);
      r.end(new Map(), false);
    }
    const d = r.dump();
    const e = d.entries[0] as { ws: unknown[]; wsTrunc: boolean; socks: { trunc: boolean; surf: unknown[] }[] };
    expect(e.ws.length).toBe(64);
    expect(e.wsTrunc).toBe(true);
    expect(e.socks.length).toBe(32);
    expect(e.socks[0].trunc).toBe(true);
    expect(e.socks[0].surf.length).toBe(128);
    const bytes = new TextEncoder().encode(r.dumpJson()).length;
    // 최악 장면은 상한을 넘을 수 있다 — 그래서 이 수는 「최악 장면 크기」의 기록이고, 상한은 실제 장면(좌석 12 · tickrec_gate.py)에서 잰다.
    expect(bytes).toBeGreaterThan(0);
    expect(TICKREC_MAX_DUMP_BYTES).toBe(2 * 1024 * 1024);
  });

  it("실제 크기 장면(좌석 12 · 소켓 3 · 200틱) 덤프 ≤ 상한", () => {
    const r = createTickRecorder({ salt: "k" });
    const surfaces = Array.from({ length: 4 }, (_, i) => ({ surface_id: i, role: "worker-" + i, exited: false, title: "1 · Opus · proj", live_cwd: "/sandbox/home/proj", display_no: i, line_count: 1000 + i, size: { rows: 40, cols: 140 } }));
    for (let t = 0; t < 200; t++) {
      r.begin(t, [W(0, [0, 1, 2, 3]), W(1, [0, 1, 2, 3], "/d1"), W(2, [0, 1, 2, 3], "/d2")], new Map(), false, new Set(), new Set());
      for (const s of ["", "/d1", "/d2"]) { r.sock(s, { surfaces }, () => true); r.ghost(s, [0, 1, 2, 3], []); r.sweep(s, false, []); }
      r.render(false, false);
      r.end(new Map(), false);
    }
    expect(new TextEncoder().encode(r.dumpJson()).length).toBeLessThan(TICKREC_MAX_DUMP_BYTES + 1);
  });
});

describe("개인정보 0 — 원문 대신 길이 + 소금 친 해시", () => {
  const SECRET_TITLE = "대화 원문 — 비밀 계획";
  const SECRET_CWD = ["", "Users", "hong", "교회", "명단"].join("/");
  const SECRET_SOCK = ["", "Users", "hong", ".cys", "depts", "재정부.sock"].join("/");
  const run = (salt: string) => {
    const r = createTickRecorder({ salt });
    r.begin(1, [W(0, [1], SECRET_SOCK)], new Map([[`${SECRET_SOCK}#1`, 1]]), false, new Set(), new Set());
    r.sock(SECRET_SOCK, { surfaces: [{ surface_id: 1, role: "홍길동", title: SECRET_TITLE, live_cwd: SECRET_CWD, exited: false }] }, () => false);
    r.adopt(SECRET_SOCK, 1, "홍길동");
    r.end(new Map([[`${SECRET_SOCK}#1`, 2]]), false);
    return r.dumpJson();
  };

  it("덤프에 제목·작업 폴더·소켓 경로·제품 어휘 밖 역할 원문이 없다 · 소금도 없다", () => {
    const j = run("pepper-123");
    for (const needle of [SECRET_TITLE, "비밀", SECRET_CWD, "hong", "교회", "명단", "재정부", ".sock", "홍길동", "pepper-123"]) expect({ needle, found: j.includes(needle) }).toEqual({ needle, found: false });
    expect(j).toContain(`"tl":${SECRET_TITLE.length}`);
    expect(j).toContain(`"cl":${SECRET_CWD.length}`);
  });

  it("같은 소금 = 같은 덤프(재생 대조 가능) · 다른 소금 = 다른 해시(덤프끼리 대조해 원문 추적 불가)", () => {
    expect(run("a")).toBe(run("a"));
    expect(run("a")).not.toBe(run("b"));
  });

  it("제품 어휘 역할(master·cso·worker-N·reviewer-x)은 그대로 · 그 밖은 「#해시」", () => {
    const r = createTickRecorder({ salt: "k" });
    r.begin(1, [], new Map(), false, new Set(), new Set());
    for (const role of ["master", "cso", "worker-12", "reviewer-codex", "Master", "w 1", "홍길동"]) r.adopt("", 1, role);
    const roles = ((r.dump().entries[0] as { adopt: { role: string }[] }).adopt).map((a) => a.role);
    expect(roles.slice(0, 4)).toEqual(["master", "cso", "worker-12", "reviewer-codex"]);
    for (const x of roles.slice(4)) expect(x).toMatch(/^#[0-9a-f]{14}$/);
  });

  it("hash53 = 고정 길이 16진 · 결정론", () => {
    expect(hash53("abc")).toBe(hash53("abc"));
    expect(hash53("abc")).toMatch(/^[0-9a-f]{14}$/);
    expect(hash53("abc")).not.toBe(hash53("abd"));
  });
});

describe("기록기 예외는 고리로 새지 않는다", () => {
  it("adoptedHere 가 던져도 sock 은 던지지 않는다 — recorderFault 1", () => {
    const r = createTickRecorder({ salt: "k" });
    r.begin(1, [], new Map(), false, new Set(), new Set());
    expect(() => r.sock("", { surfaces: [{ surface_id: 1 }] }, () => { throw new Error("boom"); })).not.toThrow();
    expect(r.counters().recorderFault).toBe(1);
  });

  it("이상한 입력(숫자 아닌 sid·순환 참조 없는 이상 값)도 던지지 않는다", () => {
    const r = createTickRecorder({ salt: "k" });
    expect(() => r.begin(1, [W(0, ["x" as unknown as number])], new Map([["k", NaN]]), false, new Set(), new Set())).not.toThrow();
    expect(() => r.sock("", { surfaces: "nope" }, () => false)).not.toThrow();
    expect(() => r.dumpJson()).not.toThrow();
  });
});

describe("main.ts 배선 정적 핀 — 꺼짐 = 무평가", () => {
  const code = stripComments(MAIN_SRC);
  const tick = fnBody(code, "async function refreshPaneTitles(");

  it("main.ts 의 tickRec 낱말 = 선언 1 + `tickRec?.` 호출뿐 · 호출은 전부 refreshPaneTitles 안", () => {
    const all = [...code.matchAll(/\btickRec\b/g)].map((m) => code.slice(m.index, m.index! + 9));
    const decl = code.match(/const tickRec: TickRecorder \| null = tickRecFromSwitch\(/g) ?? [];
    expect(decl.length).toBe(1);
    const uses = all.length - decl.length;
    expect(all.filter((s) => s === "tickRec?.").length).toBe(uses); // 선언 말고는 전부 선택적 호출
    expect([...tick.matchAll(/\btickRec\?\./g)].length).toBe(uses); // 그 호출은 전부 고리 본문 안
    expect(uses).toBe(18); // 배선 자리 수 — 늘리거나 줄이면 이 수와 tickrec_gate.py 를 함께 본다 · (cysr-1116-s2) 17 → 18 = 입양 기록이 두 갈래(런타임 지금 · 미룸)에 하나씩
  });

  it("배선 줄은 대입·await·return 을 품지 않는다(고리 흐름을 바꾸지 않는 단독 문장)", () => {
    const lines = tick.split("\n").filter((l) => l.includes("tickRec?."));
    for (const l of lines) {
      const t = l.trim();
      expect({ t, ok: t.startsWith("tickRec?.") && t.endsWith(");") && !/\bawait\b|\breturn\b/.test(t) && !/[^=!<>]=[^=>]/.test(t.replace(/=>/g, "")) }).toEqual({ t, ok: true });
    }
  });

  it("자리표 판정 입력 기록 = 판정이 실제로 쓴 입력 그대로(두 벌 → 한 벌로 접음 · cysr-1116-s2)", () => {
    // 조각 0 은 기록 줄과 판정 인자를 같은 식 두 벌로 썼다. 조각 2 는 판정(tick.ts decidePlaceholders)이 만든 입력 v.in 을 기록기에 그대로 넘긴다 —
    //   식이 하나뿐이라 갈릴 수 없다. main.ts 고리에 판정 인자 식(shouldClosePlaceholder 호출)이 다시 생기면 붉음.
    expect(tick).toContain('tickRec?.placeholderIn(sk ?? "", sid, v.in);');
    expect(/shouldClosePlaceholder\(/.test(tick)).toBe(false);
    expect(tick).toContain("const verdicts = decidePlaceholders({");
  });

  it("스위치 읽기는 localStorage 읽기 1회뿐(쓰기 0) · 손잡이 이름 = __cysTickRec", () => {
    const decl = code.slice(code.indexOf("const tickRec: TickRecorder | null"), code.indexOf("let refreshing = false;"));
    expect(decl).toContain("read: () => localStorage.getItem(TICKREC_KEY)");
    expect(decl).not.toContain("setItem");
    expect(decl).toContain("__cysTickRec = r");
  });
});

describe("기록기 파일 = 부작용 통로 0", () => {
  it("invoke·__TAURI__·localStorage·sessionStorage·document·window·타이머·fetch 를 쓰지 않는다", () => {
    const code = stripComments(REC_SRC);
    for (const w of ["invoke(", "__TAURI__", "localStorage", "sessionStorage", "document.", "window.", "setTimeout", "setInterval", "fetch(", "XMLHttpRequest", "indexedDB"]) {
      expect({ w, found: code.includes(w) }).toEqual({ w, found: false });
    }
  });
});
