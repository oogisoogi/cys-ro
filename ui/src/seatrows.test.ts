// seatrows.ts 순수 판정 회귀 시험 (bun test · 신규 의존성 0) — TICKET=cysr-tabs-sidebar-impl 조각 1a.
//
// 못박는 것: 상태 판정표(작업 중·대기·막힘·모름·끝남) · 모름을 작업 중으로 칠하지 않음 ·
//   「확인」 꼬리표는 자기보고 waiting/done 일 때만 · 막힘이면 「승인 창」 · 폴더 이름 자르기(맥 `/` · 윈 `\`) ·
//   고정 좌석(master·cso)은 묶음 밖 · 묶음 순서 = 처음 나타난 순 · 줄 순서 = 머리 번호 순.
import { expect, test } from "bun:test";
import {
  approvalSeatKeys,
  seatApprovalItems,
  buildSeatRows,
  folderKey,
  seatName,
  seatState,
  seatTag,
  showGroupHeaders,
  SEAT_STATE_LABEL,
  type SeatInput,
} from "./seatrows";

const base = (o: Partial<SeatInput>): SeatInput => ({
  sid: 1,
  displayNo: null,
  role: "worker",
  title: "",
  cwd: "/Users/u/axdev/eduscan",
  exited: false,
  dot: "working",
  approvalPending: false,
  statusState: null,
  task: null,
  ctxPct: null,
  ctxSrc: "none",
  ...o,
});

test("판정표 — 데몬 활동 점 → 좌석 상태", () => {
  expect(seatState(base({ dot: "working" }))).toBe("working");
  expect(seatState(base({ dot: "waiting" }))).toBe("idle");
  expect(seatState(base({ dot: "input" }))).toBe("blocked");
  expect(seatState(base({ dot: "unknown" }))).toBe("unknown");
  expect(seatState(base({ dot: "stale" }))).toBe("unknown");
  expect(seatState(base({ dot: null }))).toBe("unknown");
});

test("모름은 작업 중으로 칠하지 않는다 — 관측이 없거나 낡으면 unknown", () => {
  for (const dot of ["unknown", "stale", null] as const) {
    expect(seatState(base({ dot }))).not.toBe("working");
  }
});

test("승인 피드가 대기 중이면 화면 점이 무엇이든 막힘(agy·grok 은 화면 문법이 없어 피드만 잡는다)", () => {
  expect(seatState(base({ dot: "unknown", approvalPending: true }))).toBe("blocked");
  expect(seatState(base({ dot: "working", approvalPending: true }))).toBe("blocked");
});

test("끝난 좌석은 다른 신호보다 먼저 끝남", () => {
  expect(seatState(base({ exited: true, dot: "working", approvalPending: true }))).toBe("exited");
});

test("상태 이름 — waiting 은 「대기」(확인 대기 아님)", () => {
  expect(SEAT_STATE_LABEL.idle).toBe("대기");
  expect(SEAT_STATE_LABEL.working).toBe("작업 중");
  expect(SEAT_STATE_LABEL.blocked).toBe("막힘");
  expect(SEAT_STATE_LABEL.unknown).toBe("모름");
  expect(Object.values(SEAT_STATE_LABEL)).not.toContain("확인 대기");
});

test("꼬리표 — 막힘 = 승인 창 · 「확인」 은 자기보고 waiting/done 일 때만", () => {
  expect(seatTag(base({ approvalPending: true }), "blocked")).toBe("승인 창");
  expect(seatTag(base({ statusState: "waiting" }), "idle")).toBe("확인");
  expect(seatTag(base({ statusState: "done" }), "idle")).toBe("확인");
  // 화면이 대기여도 자기보고가 없으면 꼬리표 없음(막 띄운 빈 좌석)
  expect(seatTag(base({ statusState: null }), "idle")).toBeNull();
  expect(seatTag(base({ statusState: "working" }), "idle")).toBeNull();
  expect(seatTag(base({ statusState: "blocked" }), "working")).toBeNull();
  // 화면이 일하는 중이면 waiting 신고는 낡은 것 — 꼬리표 없음
  expect(seatTag(base({ statusState: "waiting" }), "working")).toBeNull();
  expect(seatTag(base({ statusState: "done" }), "unknown")).toBe("확인");
  // 끝난 좌석엔 꼬리표를 달지 않는다
  expect(seatTag(base({ statusState: "done" }), "exited")).toBeNull();
});

test("폴더 이름 — 마지막 이름 · 맥/윈 구분자 · 끝 구분자 · 빈 값", () => {
  expect(folderKey("/Users/u/axdev/eduscan")).toBe("eduscan");
  expect(folderKey("/Users/u/axdev/eduscan/")).toBe("eduscan");
  expect(folderKey("C:\\Users\\u\\work\\lms")).toBe("lms");
  expect(folderKey("C:\\Users\\u\\work\\lms\\")).toBe("lms");
  expect(folderKey("/")).toBe("");
  expect(folderKey("")).toBe("");
  expect(folderKey(null)).toBe("");
});

test("일감 이름 — 자기보고 task 첫 줄 우선 · 없으면 제목의 마지막 조각", () => {
  expect(seatName(base({ task: "홈 화면 수정\n세부", title: "931 · Opus · site" }))).toBe("홈 화면 수정");
  expect(seatName(base({ task: "  ", title: "931 · Opus · site" }))).toBe("site");
  expect(seatName(base({ task: null, title: "eduscan" }))).toBe("eduscan");
  const long = "가".repeat(80);
  expect(seatName(base({ task: long })).length <= 40).toBe(true);
});

test("고정 좌석(master·cso 계열)은 묶음 밖 · master 가 cso 위", () => {
  const m = buildSeatRows([
    base({ sid: 5, role: "cso", displayNo: 2 }),
    base({ sid: 3, role: "worker", displayNo: 7 }),
    base({ sid: 4, role: "master", displayNo: 1 }),
  ]);
  expect(m.fixed.map((r) => r.sid)).toEqual([4, 5]);
  expect(m.groups.flatMap((g) => g.rows.map((r) => r.sid))).toEqual([3]);
});

test("묶음 = 생성 폴더 마지막 이름 · 묶음 순서 = 처음 나타난 순 · 줄 순서 = 머리 번호 순", () => {
  const m = buildSeatRows([
    base({ sid: 20, displayNo: 935, cwd: "/w/lms" }),
    base({ sid: 11, displayNo: 931, cwd: "/w/site" }),
    base({ sid: 12, displayNo: 934, cwd: "/w/lms" }),
    base({ sid: 13, displayNo: 932, cwd: "/w/site" }),
  ]);
  expect(m.groups.map((g) => g.key)).toEqual(["site", "lms"]);
  expect(m.groups[0].rows.map((r) => r.no)).toEqual(["931", "932"]);
  expect(m.groups[1].rows.map((r) => r.no)).toEqual(["934", "935"]);
});

test("명시 묶음(사람이 옮긴 값)이 폴더보다 먼저", () => {
  const m = buildSeatRows([
    base({ sid: 1, displayNo: 1, cwd: "/w/site", group: "LMS" }),
    base({ sid: 2, displayNo: 2, cwd: "/w/site" }),
  ]);
  expect(m.groups.map((g) => [g.key, g.rows.map((r) => r.sid)])).toEqual([
    ["LMS", [1]],
    ["site", [2]],
  ]);
});

test("머리 번호가 없으면 내부 id 로 적고 정렬도 그 값", () => {
  const m = buildSeatRows([base({ sid: 9, displayNo: null })]);
  expect(m.groups[0].rows[0].no).toBe("9");
});

test("폴더를 모르는 좌석은 「폴더 없음」 묶음", () => {
  const m = buildSeatRows([base({ sid: 1, cwd: null })]);
  expect(m.groups[0].key).toBe("");
  expect(m.groups[0].label).toBe("폴더 없음");
});

test("묶음 머리는 묶음이 2개 이상일 때만(왕초보 = 지금 화면과 같게)", () => {
  expect(showGroupHeaders(buildSeatRows([]))).toBe(false);
  expect(showGroupHeaders(buildSeatRows([base({ sid: 1, role: "master" })]))).toBe(false);
  expect(showGroupHeaders(buildSeatRows([base({ sid: 1 }), base({ sid: 2 })]))).toBe(false);
  expect(
    showGroupHeaders(buildSeatRows([base({ sid: 1, cwd: "/a" }), base({ sid: 2, cwd: "/b" })])),
  ).toBe(true);
});

test("CTX 는 pickCtx 결과를 그대로 싣는다(결측 = null · 0 으로 접지 않음)", () => {
  const m = buildSeatRows([base({ sid: 1, ctxPct: null, ctxSrc: "none" }), base({ sid: 2, ctxPct: 0, ctxSrc: "measured" })]);
  const rows = m.groups[0].rows;
  expect(rows[0].ctxPct).toBeNull();
  expect(rows[1].ctxPct).toBe(0);
});

test("이름 보고자 줄 — 번호 대신 이름 · named 표식", () => {
  const m = buildSeatRows([base({ sid: -1, role: "master", label: "master", dot: null })]);
  expect(m.fixed[0].no).toBe("master");
  expect(m.fixed[0].named).toBe(true);
  expect(m.fixed[0].state).toBe("unknown");
});

test("승인 피드 → 좌석 열쇠 — 본부(dept null) = undefined 소켓 · 부서 = 소켓 경로 · 대기 approval 만", () => {
  const keys = approvalSeatKeys({
    sockets: [
      { socket: "/s/base.sock", dept: null, ok: true, items: [
        { kind: "approval", status: "pending", surface_id: 7 },
        { kind: "approval", status: "resolved", surface_id: 8 },
        { kind: "note", status: "pending", surface_id: 9 },
        { kind: "approval", status: "pending", surface_id: null },
      ] },
      { socket: "/s/dept-a.sock", dept: "a", ok: true, items: [{ kind: "approval", status: "pending", surface_id: 3 }] },
      { socket: 5, dept: "bad", ok: true, items: [{ kind: "approval", status: "pending", surface_id: 4 }] },
    ],
  });
  expect([...keys].sort()).toEqual(["/s/dept-a.sock#3", "undefined#7"]);
  expect(approvalSeatKeys(null).size).toBe(0);
  expect(approvalSeatKeys({ sockets: "x" }).size).toBe(0);
});

test("surface.list 원행 → 입력 — 생성 폴더(cwd) 사용 · live_cwd 무시 · 끝난 좌석 CTX 판정 불가 · 원행 없음 = 모름", async () => {
  const { seatInputOf } = await import("./seatrows");
  const i = seatInputOf(5, { display_no: 931, role: "worker", title: "931 · Opus · site", cwd: "/w/site", live_cwd: "/w/other", exited: false, usage: { ctx_pct: 38 } }, "working", { state: "waiting", task: "홈 화면 수정" }, false);
  expect([i.displayNo, i.cwd, i.ctxPct, i.ctxSrc, i.statusState, i.task, i.dot]).toEqual([931, "/w/site", 38, "measured", "waiting", "홈 화면 수정", "working"]);
  const ex = seatInputOf(6, { exited: true, usage: { ctx_pct: 50 } }, "working", undefined, false);
  expect([ex.exited, ex.ctxPct, ex.ctxSrc]).toEqual([true, null, "stale"]);
  const none = seatInputOf(7, undefined, "working", undefined, false);
  expect([none.dot, seatState(none)]).toEqual([null, "unknown"]);
});

test("이름 보고자 입력 — 이름 줄 · 활동 모름 · CTX 결측은 결측", async () => {
  const { namedSeatInputs } = await import("./seatrows");
  const xs = namedSeatInputs([{ name: "master", ctxPct: 52 }, { name: "cso", ctxPct: null }]);
  const m = buildSeatRows(xs);
  expect(m.fixed.map((r) => [r.no, r.state, r.ctxPct, r.named])).toEqual([["master", "unknown", 52, true], ["cso", "unknown", null, true]]);
});

test("화면 활동 점 — 관측 우선 · 관측이 모름일 때만 자기보고 판정(nodeWorking) 작업 중이면 작업 중 · 신호 없음 = 모름", async () => {
  const { seatDot } = await import("./seatrows");
  expect(seatDot("waiting", true)).toBe("waiting");
  expect(seatDot("input", true)).toBe("input");
  expect(seatDot("stale", true)).toBe("stale");
  expect(seatDot("unknown", true)).toBe("working");
  expect(seatDot("unknown", false)).toBe("unknown");
  // 승인 피드 대기 = 입력 대기(관측이 무엇이든)
  expect(seatDot("working", false, true)).toBe("input");
  expect(seatDot("unknown", true, true)).toBe("input");
});

test("(master#ec9c8b30 ③) 좌석에 걸린 승인 요청 수(항목 단위) — 상황판 「승인 요청」 = 전체 − 이것 · 좌석 없음·좌석 줄 밖·승인 아님은 빼고 · 형식 오류 = 0", () => {
  const all = { sockets: [
    { socket: "/b.sock", dept: null, ok: true, items: [
      { kind: "approval", status: "pending", surface_id: 6 },
      { kind: "approval", status: "pending", surface_id: 6 },
      { kind: "approval", status: "pending", surface_id: null },
      { kind: "approval", status: "pending", surface_id: 99 },
      { kind: "notice", status: "pending", surface_id: 6 },
    ] },
    { socket: "/d.sock", dept: "lms", ok: true, items: [{ kind: "approval", status: "pending", surface_id: 21 }] },
  ] };
  expect(seatApprovalItems(all, new Set(["undefined#6", "/d.sock#21"]))).toBe(3);
  expect(seatApprovalItems(all, new Set())).toBe(0);
  expect(seatApprovalItems(null, new Set(["undefined#6"]))).toBe(0);
});
