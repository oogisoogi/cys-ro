// (cysr-1116-s6) 왼쪽 메뉴바 판정 시험 — P2-DESIGN §11 조각 6 수용 기준(FR-P1·P2·L1·L3 · 개정 E1·E2 · §5-4 빠른 답).
import { describe, expect, it } from "bun:test";
import { buildSeatRows, seatInputOf, seatDot } from "../../seatrows";
import { effectiveGroup, parseSeatGroups, uniqueKeys } from "../../seatgroup";
import {
  addMarkers,
  agoText,
  DEPT_REPLY_NO,
  DEPT_REPLY_YES,
  FORMING_MAX_MS,
  formingMarkersOf,
  quickReplyOf,
  QUIET_SECS,
  railModel,
  TEAM_REPLY_NO,
  TEAM_REPLY_YES,
  teamSummary,
  type RailInput,
} from "./rail";

const NOW = 1_700_000_000_000;
const working = (r: Record<string, unknown>) => r.working_flag === true;

function seat(id: number, cwd: string, extra: Record<string, unknown> = {}): Record<string, unknown> {
  return { surface_id: id, display_no: id, role: `worker-${id}`, title: `${id} · Opus · w`, cwd, exited: false, group: null, group_set: false, ...extra };
}
function org(id: number, o: { task?: string; state?: string; age?: number; idle?: number; working?: boolean } = {}): Record<string, unknown> {
  return { surface_id: id, idle_secs: o.idle ?? 5, working_flag: o.working ?? false, status: o.task === undefined && o.state === undefined ? null : { state: o.state ?? "working", task: o.task ?? null, age_secs: o.age ?? 5 } };
}
function input(surfaces: Record<string, unknown>[], orgs: Record<string, unknown>[], p: Partial<RailInput> = {}): RailInput {
  return { surfaces, org: { surfaces: orgs }, approvalSeats: [], seatGroupsRaw: null, depts: { depts: {} }, markers: [], nowMs: NOW, working, ...p };
}

describe("팀 = 작업 화면 묶음 탭과 같은 모델(개정 E1 · bun 대조)", () => {
  const surfaces = [
    seat(1, "/w/proj/site"),
    seat(2, "/w/proj/site"),
    seat(3, "C:\\work\\home"),
    seat(4, "/w/proj/other", { group: "홍보팀", group_set: true }), // 마스터가 seat-group 으로 옮김
    seat(5, "/w/proj/other"), // 앱 기록으로 옮김
    { surface_id: 9, role: "master", cwd: "/w/proj", exited: false },
    { surface_id: 10, role: "cso", cwd: "/w/proj", exited: false },
  ];
  const groupsRaw = JSON.stringify({ "#role:worker-5": "홍보팀" });
  const orgs = [org(1, { task: "사이트 고치기" }), org(2, { task: "사이트 고치기" }), org(3, { task: "집 정리" }), org(4, { task: "행사 안내" }), org(5, { task: "보도자료" })];
  const m = railModel(input(surfaces, orgs, { seatGroupsRaw: groupsRaw }));

  it("팀 이름·좌석 = main.ts refreshSeatRows 와 같은 길(seatInputOf + effectiveGroup + buildSeatRows)로 만든 묶음과 같다", () => {
    const list = surfaces;
    const uniq = uniqueKeys(null, list);
    const sg = parseSeatGroups(groupsRaw);
    const inputs = list.map((s) => {
      const inp = seatInputOf(s.surface_id as number, s, seatDot("waiting", false, false), undefined, false);
      inp.group = effectiveGroup(sg, null, s, uniq);
      return inp;
    });
    const work = buildSeatRows(inputs);
    const workTeams = work.groups.map((g) => ({ team: g.label, n: g.rows.length }));
    const chatTeams = m.blocks.map((b) => ({ team: b.team, n: b.cards.reduce((a, c) => a + c.helpers, 0) }));
    expect(chatTeams).toEqual(workTeams);
    expect(chatTeams.map((t) => t.team)).toEqual(["site", "home", "홍보팀"]);
  });
  it("같은 팀 같은 일감 = 카드 하나 · 도우미 수(FR-P1)", () => {
    const site = m.blocks.find((b) => b.team === "site")!;
    expect(site.cards).toHaveLength(1);
    expect([site.cards[0].title, site.cards[0].helpers]).toEqual(["사이트 고치기", 2]); // toMatchObject 대신(bun-env.d.ts 최소 matcher 계약)
    expect(m.taskCount).toBe(4);
  });
  it("(검증 i7) ceo 좌석 = 고정(팀·카드 아님) — 작업 화면 묶음과 같은 판정", () => {
    const m2 = railModel(input([seat(1, "/w/proj/site"), { ...seat(2, "/w/proj/hq"), role: "ceo" }], [org(1, { task: "가" }), org(2, { task: "본부 일" })]));
    expect(m2.blocks.map((b) => b.team)).toEqual([null]);
    expect(m2.blocks[0].cards.map((c) => c.title)).toEqual(["가"]);
  });
  it("마스터·운영 좌석은 맡긴 일 카드가 아니다", () => {
    expect(m.blocks.flatMap((b) => b.cards).some((c) => c.title.includes("master"))).toBe(false);
  });
});

describe("팀 머리 = 묶음 2개 이상일 때만(FR-L1 · 탭 줄과 같은 판정)", () => {
  it("묶음 1개 = 머리 없음(왕초보 화면 그대로)", () => {
    const m = railModel(input([seat(1, "/a/site"), seat(2, "/a/site")], [org(1, { task: "가" }), org(2, { task: "나" })]));
    expect(m.blocks).toHaveLength(1);
    expect(m.blocks[0].team).toBeNull();
    expect(m.taskCount).toBe(2);
  });
  it("묶음 2개 = 팀 머리 + 요약", () => {
    const m = railModel(input([seat(1, "/a/site"), seat(2, "/a/home")], [org(1, { task: "가", working: true }), org(2, { task: "나" })], { approvalSeats: [2] }));
    expect(m.blocks.map((b) => [b.team, b.summary])).toEqual([
      ["site", "● 일하는 중 1"],
      ["home", "▲ 확인 필요 1"],
    ]);
  });
  it("부서는 팀으로 세지 않는다(개정 E2) — 부서 등록부는 따로 부서 줄", () => {
    const m = railModel(input([seat(1, "/a/site")], [org(1, { task: "가" })], { depts: { depts: { "dept-1": { display_name: "홍보부" }, "dept-2": {} } } }));
    expect(m.blocks[0].team).toBeNull();
    expect(m.depts).toEqual([
      { name: "dept-2", title: "dept-2" },
      { name: "dept-1", title: "홍보부" },
    ]);
  });
});

describe("카드 상태(FR-P2 · 모름은 칠하지 않음)", () => {
  const one = (o: Parameters<typeof org>[1], appr = false, orgRow = true) => railModel(input([seat(1, "/a/s")], orgRow ? [org(1, o)] : [], { approvalSeats: appr ? [1] : [] })).blocks[0].cards[0];
  it("일하는 중 · 기다림 · 확인 필요", () => {
    expect(one({ task: "가", working: true }).status).toBe("run");
    expect(one({ task: "가" }).status).toBe("wait");
    expect(one({ task: "가", working: true }, true).status).toBe("need");
  });
  it("10분 넘게 소식 없음 = 조용함(일하는 중이어도)", () => {
    expect(one({ task: "가", working: true, idle: QUIET_SECS + 1, age: QUIET_SECS + 1 }).status).toBe("quiet");
    expect(one({ task: "가", working: true, idle: QUIET_SECS, age: QUIET_SECS + 50 }).status).toBe("run"); // 출력이 10분 안 = 소식 있음
    expect(one({ task: "가", working: true, idle: QUIET_SECS + 50, age: 30 }).status).toBe("run"); // 자기보고가 10분 안 = 소식 있음
  });
  it("자기보고·출력 시각 모름 = 「이 일의 소식을 못 받고 있어요」", () => {
    expect(one({}, false, false).status).toBe("unknown");
  });
  it("마지막 소식 시각 = 출력과 자기보고 중 가까운 쪽", () => {
    expect(one({ task: "가", idle: 400, age: 90 }).newsSecs).toBe(90);
    expect(agoText(90)).toBe("1분 전");
    expect(agoText(30)).toBe("방금");
    expect(agoText(7300)).toBe("2시간 전");
  });
  it("좌석 목록을 아직 못 받음 = 불러오는 중", () => {
    expect(railModel(input([], [], { surfaces: undefined })).loading).toBe(true);
  });
  it("요약 = 모두 조용하면 조용함", () => {
    expect(teamSummary([{ key: "a", title: "a", status: "quiet", newsSecs: 700, helpers: 1 }])).toBe("○ 조용함");
  });
});

describe("「팀 만드는 중」(FR-L3 · §5-1 개정 E1)", () => {
  const rec = (text: string, role: "assistant" | "user" = "assistant") => ({ uuid: "u1", parent: null, role, text, ts: null });
  it("마스터 답 줄머리 정확 일치만 · 울타리 안·사람 말 = 0", () => {
    expect(formingMarkersOf(rec("좋아요.\n⟪팀 만드는 중: 홍보팀⟫\n"))).toEqual([{ kind: "team", name: "홍보팀" }]);
    expect(formingMarkersOf(rec("```\n⟪팀 만드는 중: 홍보팀⟫\n```"))).toEqual([]);
    expect(formingMarkersOf(rec("예: ⟪팀 만드는 중: 홍보팀⟫"))).toEqual([]);
    expect(formingMarkersOf(rec("⟪팀 만드는 중: 홍보팀⟫", "user"))).toEqual([]);
    expect(formingMarkersOf(rec("⟪부서로 올리는 중: 홍보팀⟫"))).toEqual([{ kind: "promote", name: "홍보팀" }]);
  });
  it("표식 → 만드는 중 카드 · 그 이름 묶음이 생기면 내림(만드는 중 → 진행)", () => {
    const marks = addMarkers([], [{ kind: "team", name: "홍보팀" }], NOW);
    const before = railModel(input([seat(1, "/a/site")], [org(1, { task: "가" })], { markers: marks }));
    expect(before.forming).toEqual([{ kind: "team", name: "홍보팀", line: "팀 만드는 중이에요" }]);
    expect(before.taskCount).toBe(1); // 만드는 중 카드는 맡긴 일 수에 넣지 않는다
    const after = railModel(input([seat(1, "/a/site"), seat(2, "/a/site", { group: "홍보팀", group_set: true })], [org(1, { task: "가" }), org(2, { task: "나" })], { markers: marks }));
    expect(after.forming).toEqual([]);
    expect(after.blocks.map((b) => b.team)).toEqual(["site", "홍보팀"]);
  });
  it("상한 넘게 묶음이 안 생기면 내림 · 같은 표식 두 번 = 카드 하나", () => {
    const marks = addMarkers(addMarkers([], [{ kind: "team", name: "가팀" }], NOW - FORMING_MAX_MS - 1), [{ kind: "team", name: "나팀" }], NOW);
    const twice = addMarkers(marks, [{ kind: "team", name: "나팀" }], NOW);
    expect(railModel(input([], [], { markers: twice })).forming.map((f) => f.name)).toEqual(["나팀"]);
  });
  it("부서로 올리는 중 → 부서 등록부에 그 이름이 생기면 부서 줄로", () => {
    const marks = addMarkers([], [{ kind: "promote", name: "홍보팀" }], NOW);
    expect(railModel(input([], [], { markers: marks })).forming.map((f) => f.kind)).toEqual(["promote"]);
    const done = railModel(input([], [], { markers: marks, depts: { depts: { "dept-3": { display_name: "홍보팀" } } } }));
    expect(done.forming).toEqual([]);
    expect(done.depts.map((d) => d.title)).toEqual(["홍보팀"]);
  });
});

describe("빠른 답(§5-4 D7 · §16-5 ①)", () => {
  it("⟪팀 제안⟫ = 팀 · ⟪부서 제안: 팀⟫ = 부서 · 울타리 안·줄 중간 = 없음", () => {
    expect(quickReplyOf("나눠 맡길까요?\n⟪팀 제안⟫")).toEqual({ kind: "team" });
    expect(quickReplyOf("올릴까요?\n⟪부서 제안: 홍보팀⟫")).toEqual({ kind: "dept", team: "홍보팀" });
    expect(quickReplyOf("```\n⟪팀 제안⟫\n```")).toBeNull();
    expect(quickReplyOf("예: ⟪팀 제안⟫ 이렇게")).toBeNull();
    expect(quickReplyOf("그냥 답")).toBeNull();
  });
  it("단추 글 = 설계 원문 그대로", () => {
    expect([TEAM_REPLY_YES, TEAM_REPLY_NO, DEPT_REPLY_YES, DEPT_REPLY_NO]).toEqual(["네, 팀으로 나눠 주세요", "아니요, 지금처럼 해 주세요", "네, 부서로 올려 주세요", "지금은 아니요"]);
  });
});
