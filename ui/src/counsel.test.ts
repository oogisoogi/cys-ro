// counsel.ts 순수 로직 시험(TICKET=cysr-119-t4-app) — 정렬(§10-7a)·댓글 트리·표식 벗기기·상담소 답 판별·문구.
import { describe, it, expect } from "bun:test";
import {
  COUNSEL_COPY,
  MAX_TEXT,
  UNREAD_NONE,
  badgeText,
  buildCounselView,
  clampText,
  counselTooltip,
  fmtWhen,
  newAnswersLine,
  parseUnread,
  stepUnread,
  UNREAD_CACHE0,
  statusCopy,
  unwrapBody,
  type RawEvent,
  type RawRef,
} from "./counsel";

const ROOM = "2a3c1932d7eccf316cc4a0b312e558c7";
const MK = "AGORA-DATA-0123456789abcdef";
const wrap = (t: string) => `<<${MK}\n${t}\n${MK}>>`;
const ev = (id: string, from: string, ts: string, body: string | null = `글 ${id}`, kind = "post"): RawEvent => ({
  message_id: id,
  kind,
  from,
  ts,
  body: body === null ? null : wrap(body),
  marker: MK,
});
const ref = (from: string, to: string, thread = ROOM): RawRef => ({ from_message_id: from, thread_id: thread, message_id: to });

describe("unwrapBody — 응답의 표식과 정확히 같을 때만 벗긴다", () => {
  it("정상 표식 → 본문만", () => {
    expect(unwrapBody(wrap("안녕\n둘째 줄"), MK)).toBe("안녕\n둘째 줄");
  });
  it("표식이 다르면(본문이 흉내 낸 경우) 그대로 둔다", () => {
    const fake = `<<AGORA-DATA-ffffffffffffffff\nx\nAGORA-DATA-ffffffffffffffff>>`;
    expect(unwrapBody(fake, MK)).toBe(fake);
  });
  it("표식 없음·꼴 밖 표식 → 그대로", () => {
    expect(unwrapBody("raw", null)).toBe("raw");
    expect(unwrapBody(wrap("x"), "AGORA-DATA-xyz")).toBe(wrap("x"));
  });
  it("표식 길이·꼴 가정 0 — 32자 hex·다른 접두도 응답 값과 정확히 같으면 벗긴다(codex 1R BLOCK 5)", () => {
    const m32 = "AGORA-DATA-" + "a".repeat(32);
    expect(unwrapBody(`<<${m32}\nhi\n${m32}>>`, m32)).toBe("hi");
    expect(unwrapBody(`<<X9\nhi\nX9>>`, "X9")).toBe("hi");
  });
  it("빈·여러 줄·너무 긴 표식은 벗기지 않는다", () => {
    expect(unwrapBody("<<\nhi\n>>", "")).toBe("<<\nhi\n>>");
    const nl = "A\nB";
    expect(unwrapBody(`<<${nl}\nhi\n${nl}>>`, nl)).toBe(`<<${nl}\nhi\n${nl}>>`);
    const long = "M".repeat(257);
    expect(unwrapBody(`<<${long}\nhi\n${long}>>`, long)).toBe(`<<${long}\nhi\n${long}>>`);
  });
  it("본문 안에 닫는 표식 흉내가 있어도 바깥 경계만 벗긴다", () => {
    const inner = `앞\n${MK}>>\n<<${MK}\n뒤`;
    expect(unwrapBody(wrap(inner), MK)).toBe(inner);
  });
});

describe("buildCounselView — 정렬(내 글 맨 위 최근 활동순 → 나머지 최신순)", () => {
  const me = "jarvis-me00000001";
  const events: RawEvent[] = [
    ev("g", "jarvis-chair1", "2026-10-05T13:14:43Z", "방 소개", "genesis"),
    ev("a", "jarvis-other01", "2026-10-08T10:00:00Z"),
    ev("b", me, "2026-10-08T09:00:00Z"),
    ev("c", "jarvis-other02", "2026-10-08T12:00:00Z"),
    ev("d", me, "2026-10-08T11:00:00Z"),
    ev("b1", "jarvis-counsel", "2026-10-09T06:10:00Z"), // b 의 댓글 — b 의 최근 활동을 끌어올린다
    ev("b2", "jarvis-other01", "2026-10-09T06:30:00Z"), // b1 의 댓글 → 뿌리 b 아래
    ev("x", "jarvis-other03", "2026-10-08T13:00:00Z", null, "advance"), // 본문 없음 → 뺀다
    ev("o", "jarvis-other03", "2026-10-08T14:00:00Z"), // 없는 글을 가리킴 → orphans
  ];
  const refs: RawRef[] = [ref("b1", "b"), ref("b2", "b1"), ref("o", "zz"), ref("a", "elsewhere", "f".repeat(32))];
  const v = buildCounselView({ events, refs, roomId: ROOM, me, deskIds: ["jarvis-counsel"] });

  it("genesis = 방 소개 1줄 · 본문 없는 이벤트는 목록에서 빠진다", () => {
    expect(v.intro).toBe("방 소개");
    const ids = [...v.mine, ...v.others].map((p) => p.id);
    expect(ids.includes("g")).toBe(false);
    expect(ids.includes("x")).toBe(false);
  });
  it("내 글은 최근 활동순(댓글 시각 포함)", () => {
    expect(v.mine.map((p) => p.id)).toEqual(["b", "d"]);
    expect(v.mine[0].lastActivity).toBe("2026-10-09T06:30:00Z");
    expect(v.mine.every((p) => p.isMine)).toBe(true);
  });
  it("나머지는 원글 시각 최신순 · 다른 방을 가리키는 글은 원글로 남는다", () => {
    expect(v.others.map((p) => p.id)).toEqual(["c", "a"]);
  });
  it("댓글의 댓글도 뿌리 원글 아래 시각순", () => {
    expect(v.mine[0].comments.map((c) => c.id)).toEqual(["b1", "b2"]);
  });
  it("상담소 답 = 검증된 상담소 id 만", () => {
    expect(v.mine[0].comments[0].isDesk).toBe(true);
    expect(v.mine[0].comments[1].isDesk).toBe(false);
  });
  it("원글을 찾을 수 없는 댓글은 버리지 않고 따로 모은다", () => {
    expect(v.orphans.map((c) => c.id)).toEqual(["o"]);
  });
  it("me 가 비면 「내 글」 0 · 같은 시각은 id 순으로 안정", () => {
    const w = buildCounselView({
      events: [ev("p2", "jarvis-a1", "2026-10-08T10:00:00Z"), ev("p1", "jarvis-a2", "2026-10-08T10:00:00Z")],
      refs: [],
      roomId: ROOM,
      me: "",
      deskIds: [],
    });
    expect(w.mine).toEqual([]);
    expect(w.others.map((p) => p.id)).toEqual(["p1", "p2"]);
  });
  it("refs 고리(서로 가리킴)는 원글 없음으로 orphans", () => {
    const w = buildCounselView({
      events: [ev("p", "jarvis-a1", "2026-10-08T10:00:00Z"), ev("q", "jarvis-a1", "2026-10-08T10:01:00Z")],
      refs: [ref("p", "q"), ref("q", "p")],
      roomId: ROOM,
      me: "",
      deskIds: [],
    });
    expect(w.others).toEqual([]);
    expect(w.orphans.map((c) => c.id)).toEqual(["p", "q"]);
  });
  it("같은 message_id 가 두 번 오면 한 번만", () => {
    const w = buildCounselView({
      events: [ev("p", "jarvis-a1", "2026-10-08T10:00:00Z"), ev("p", "jarvis-a1", "2026-10-08T10:00:00Z")],
      refs: [],
      roomId: ROOM,
      me: "",
      deskIds: [],
    });
    expect(w.others.length).toBe(1);
  });
  it("빈 방(genesis 만) = 글 0 · 소개만", () => {
    const w = buildCounselView({ events: [events[0]], refs: [], roomId: ROOM, me, deskIds: [] });
    expect(w.mine.length + w.others.length + w.orphans.length).toBe(0);
    expect(w.intro).toBe("방 소개");
  });
});

describe("문구·표시", () => {
  it("긴 글은 상한에서 자르고 안내 꼬리", () => {
    const long = "가".repeat(MAX_TEXT + 5);
    const c = clampText(long);
    expect(c.startsWith("가".repeat(MAX_TEXT))).toBe(true);
    expect(c.endsWith(COUNSEL_COPY.truncated)).toBe(true);
    expect(clampText("짧다")).toBe("짧다");
  });
  it("새 답 줄 — 1 이상일 때만", () => {
    expect(newAnswersLine(0)).toBeNull();
    expect(newAnswersLine(-1)).toBeNull();
    expect(newAnswersLine(2)).toBe('새 답이 2개 있어요 — 마스터에게 "상담소 답 보여줘"라고 말해 보세요.');
  });
  it("상태 문구 — 비었다 ≠ 못 가져왔다", () => {
    expect(statusCopy("ok")).toBeNull();
    expect(statusCopy("no_client")).toBe(COUNSEL_COPY.noClient);
    expect(statusCopy("no_room")).toBe(COUNSEL_COPY.noRoom);
    expect(statusCopy("error")).toBe(COUNSEL_COPY.failed);
    expect(statusCopy("뭔지모름")).toBe(COUNSEL_COPY.failed);
    expect(COUNSEL_COPY.failed).not.toBe(COUNSEL_COPY.empty);
  });
  it("시각 = MM-DD HH:MM · 못 읽으면 원문", () => {
    expect(fmtWhen("2026-10-08T12:04:00Z")).toMatch(/^\d{2}-\d{2} \d{2}:\d{2}$/);
    expect(fmtWhen("엉뚱")).toBe("엉뚱");
  });
});


describe("parseUnread — §11 읽기 규칙", () => {
  const prev = { count: 3, deskCount: 1, held: 0, needsUpdate: false };
  const doc = (o: Record<string, unknown>) => JSON.stringify({ v: 1, updated_at: "2026-10-09T00:00:00.000Z", count: 2, desk_count: 1, mail_unread: 1, desk_post_replies: 1, held_for_roster: 0, threads: [], ...o });
  it("정상 → 그 값 · 판정 끝", () => {
    expect(parseUnread(doc({}), prev)).toEqual({ state: { count: 2, deskCount: 1, held: 0, needsUpdate: false }, settled: true });
  });
  it("파일 없음 → 0(숨김) · 판정 끝", () => {
    expect(parseUnread(null, prev)).toEqual({ state: UNREAD_NONE, settled: true });
  });
  it("깨진 JSON·반쯤 쓴 파일·배열 → 직전 값 · 판정 안 끝남(다음에 다시 읽는다)", () => {
    for (const raw of ["{", doc({}).slice(0, 20), "[]", "null", ""]) expect(parseUnread(raw, prev)).toEqual({ state: prev, settled: false });
  });
  it("v ≠ 1 → 직전 값 + 갱신 필요 · 판정 끝", () => {
    expect(parseUnread(doc({ v: 2 }), prev)).toEqual({ state: { ...prev, needsUpdate: true }, settled: true });
    expect(parseUnread(doc({ v: "1" }), prev).state.needsUpdate).toBe(true);
  });
  it("count 형식 밖 → 직전 값 · 판정 안 끝남", () => {
    for (const c of [-1, 1.5, "2"]) expect(parseUnread(doc({ count: c }), prev)).toEqual({ state: prev, settled: false });
  });
  it("수신 보류 칸", () => {
    expect(parseUnread(doc({ held_for_roster: 4 }), prev).state.held).toBe(4);
  });
  it("실측 파일 모양(2026-10-09 이 맥 · 전부 0)", () => {
    const real = '{\n "count": 0,\n "desk_count": 0,\n "desk_post_replies": 0,\n "held_for_roster": 0,\n "mail_unread": 0,\n "threads": [],\n "updated_at": "2026-10-05T13:16:12.945Z",\n "v": 1\n}\n';
    expect(parseUnread(real, prev).state).toEqual(UNREAD_NONE);
  });
});

describe("stepUnread — 부분 쓰기 뒤 같은 밀리초에 완성돼도 다시 읽는다(codex 1R BLOCK 4)", () => {
  const full = JSON.stringify({ v: 1, count: 5, desk_count: 2, held_for_roster: 0 });
  it("깨진 글자의 수정 시각은 기억하지 않는다 → 같은 시각의 완성본을 다음 폴링에서 읽는다", () => {
    const c1 = stepUnread(UNREAD_CACHE0, { exists: true, mtime_ms: 1000, text: full.slice(0, 7) });
    expect(c1.mtime).toBe(-1);
    expect(c1.state).toEqual(UNREAD_NONE);
    const c2 = stepUnread(c1, { exists: true, mtime_ms: 1000, text: full });
    expect(c2.state.count).toBe(5);
    expect(c2.mtime).toBe(1000);
    // 판정이 끝난 뒤 같은 시각 = 다시 판독하지 않는다(같은 객체).
    expect(stepUnread(c2, { exists: true, mtime_ms: 1000, text: "{" })).toBe(c2);
  });
  it("읽기 실패(text null·명령 실패) = 재시도 · 파일 사라짐 = 숨김", () => {
    const c = stepUnread(UNREAD_CACHE0, { exists: true, mtime_ms: 9, text: full });
    const failed = stepUnread(c, { exists: true, mtime_ms: 10, text: null });
    expect(failed.mtime).toBe(9);
    expect(failed.state.count).toBe(5);
    expect(stepUnread(failed, { exists: false }).state).toEqual(UNREAD_NONE);
    expect(stepUnread(failed, null).state).toEqual(UNREAD_NONE);
  });
});

describe("뱃지 글자·툴팁", () => {
  it("0 숨김 · 1 · 99 · 100 → 99+", () => {
    expect(badgeText(0)).toBeNull();
    expect(badgeText(1)).toBe("1");
    expect(badgeText(99)).toBe("99");
    expect(badgeText(120)).toBe("99+");
  });
  it("툴팁 = 기본 + 상태줄", () => {
    expect(counselTooltip(UNREAD_NONE)).toBe(COUNSEL_COPY.tooltip);
    expect(counselTooltip({ ...UNREAD_NONE, needsUpdate: true, held: 1 })).toBe(
      [COUNSEL_COPY.tooltip, COUNSEL_COPY.needsUpdate, COUNSEL_COPY.held].join("\n"),
    );
  });
});
