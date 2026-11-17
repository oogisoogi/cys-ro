// (cysr-ui-slice4) 확인 대기 판정 시험 — 순수. P2-DESIGN §5-4 · §2-7 · PRD FR-C1~C6.
import { describe, it, expect } from "bun:test";
import {
  allowReady,
  approvalsOf,
  bandLabel,
  bandOf,
  boundOf,
  CMD_MAX_CHARS,
  CMD_MAX_LINES,
  CONFIRM_STALL_MEASURED,
  CONFIRM_STALL_MS,
  itemStall,
  markersOf,
  masterSilenced,
  openQuestions,
  parseApprovalBody,
  recheck,
  replyErrorMsg,
  resolveKey,
  type StallInput,
} from "./confirms";
import type { Rec } from "./msgstep";

const A = (text: string, uuid = "a1", extra: Partial<Rec> = {}): Rec => ({ uuid, parent: null, role: "assistant", text, ts: null, ...extra });
const body = (cmd: string, ro = "쓰기·삭제 가능") => `Do you want to proceed?\n— 명령 원문:\n${cmd}\n— 읽기 전용 판정(기계 추정 · 근거 아님): ${ro}`;
const feedItem = (o: Partial<Record<string, unknown>> = {}) => ({ request_id: "r1", kind: "approval", status: "pending", surface_id: 7, created_at: 1000, body: body("rm -rf build"), ...o });
const stall = (o: Partial<StallInput> = {}): StallInput => ({ now: 1_000_000, masterSid: 5, masterAlive: true, masterIdleSecs: 1, deadman: null, stalledIds: new Set(), ...o });

describe("마스터 물음 표식 — 줄머리 정확 일치만(§5-4)", () => {
  it("⟪확인 요청: …⟫ 한 줄 = 물음 1 · 뒤 공백은 봐줌", () => {
    expect(markersOf(A("앞 말\n⟪확인 요청: 배포할까요?⟫  \n뒷 말"))).toEqual([{ kind: "ask", text: "배포할까요?", uuid: "a1" }]);
  });
  it("줄 중간·들여쓰기·끝 표시 없음·빈 물음 = 0(꾸미지 않음)", () => {
    for (const t of ["예: ⟪확인 요청: 배포할까요?⟫", " ⟪확인 요청: 배포할까요?⟫", "⟪확인 요청: 배포할까요?", "⟪확인 요청:  ⟫", "⟪확인요청: 붙임⟫", "📌 결정 필요: 배포할까요?"]) expect(markersOf(A(t))).toEqual([]);
  });
  it("사람(user) 글 · 곁가지 · 코드 울타리 안 = 0", () => {
    expect(markersOf({ ...A("⟪확인 요청: 사람이 친 표식⟫"), role: "user" })).toEqual([]);
    expect(markersOf(A("⟪확인 요청: 곁가지⟫", "a1", { sidechain: true }))).toEqual([]);
    expect(markersOf(A("표식 꼴은 이렇게:\n```\n⟪확인 요청: 예시⟫\n```\n끝"))).toEqual([]);
  });
  it("해결 표식 = 앞 20자 열쇠", () => {
    expect(markersOf(A("⟪확인 해결: 가나다라마바사아자차카타파하가나다라마바사아자⟫"))).toEqual([{ kind: "resolve", key: "가나다라마바사아자차카타파하가나다라마바", uuid: "a1" }]);
    expect(resolveKey("🙂".repeat(25))).toBe("🙂".repeat(20)); // 코드 포인트 단위
  });
});

describe("열린 물음 다시 놀기(FR-C3 — 해결 표식이 올 때만 닫힘)", () => {
  const ask = (text: string) => ({ kind: "ask" as const, text, uuid: null });
  const res = (t: string) => ({ kind: "resolve" as const, key: resolveKey(t), uuid: null });
  it("물음 → 해결(앞 20자) = 닫힘 · 해결이 전문이어도 앞 20자로 대조", () => {
    const q = "이번 주 배포를 금요일 오후로 미뤄도 될까요? 고객 공지가 필요해요";
    expect(openQuestions([ask(q)]).map((x) => x.text)).toEqual([q]);
    expect(openQuestions([ask(q), res(q.slice(0, 20))])).toEqual([]);
    expect(openQuestions([ask(q), res(q)])).toEqual([]);
  });
  it("해결 하나 = 가장 오래된 하나만 · 모르는 해결은 무시 · 같은 물음 다시 묻기 = 1건", () => {
    const p = "가나다라마바사아자차카타파하가나다라마바";
    const o = openQuestions([ask(`${p} 첫째`), ask(`${p} 둘째`), res(p), res("없는 물음")]);
    expect(o.map((x) => x.text)).toEqual([`${p} 둘째`]);
    expect(openQuestions([ask("같은 물음"), ask("같은 물음")]).length).toBe(1);
  });
  it("해결 앞에 온 물음만 닫힌다(순서)", () => {
    expect(openQuestions([res("뒤에 올 물음"), ask("뒤에 올 물음")]).length).toBe(1);
  });
});

describe("승인 feed 본문 → 펼침 자료(FR-C5a — 까닭은 지어내지 않음)", () => {
  it("데몬 본문 꼴 → excerpt · 명령 원문 · 기계 추정", () => {
    expect(parseApprovalBody(body("rm -rf build\nls"))).toEqual({ excerpt: "Do you want to proceed?", command: "rm -rf build\nls", readonly: "쓰기·삭제 가능" });
    expect(parseApprovalBody("excerpt 만")).toEqual({ excerpt: "excerpt 만", command: "", readonly: null });
  });
  it("pending approval 만 · 번호·좌석·시각 온전한 것만 · 오래된 것부터 · 꼴 틀림 = null(모름)", () => {
    const got = approvalsOf({ items: [feedItem({ request_id: "r2", created_at: 2000 }), feedItem(), feedItem({ request_id: "x", kind: "question" }), feedItem({ request_id: "y", status: "resolved" }), feedItem({ request_id: "" }), feedItem({ request_id: "z", surface_id: "7" })] });
    expect(got?.map((a) => a.request_id)).toEqual(["r1", "r2"]);
    expect(approvalsOf(null)).toBeNull();
    expect(approvalsOf({ nope: 1 })).toBeNull();
    expect(approvalsOf({ items: [] })).toEqual([]);
  });
  it("데몬 자름 한도(12행·600자)에 닿으면 잘림 표시", () => {
    const lines = Array.from({ length: CMD_MAX_LINES }, (_, i) => `l${i}`).join("\n");
    expect(approvalsOf({ items: [feedItem({ body: body(lines) })] })?.[0].truncated).toBe(true);
    expect(approvalsOf({ items: [feedItem({ body: body("x".repeat(CMD_MAX_CHARS)) })] })?.[0].truncated).toBe(true);
    expect(approvalsOf({ items: [feedItem()] })?.[0].truncated).toBe(false);
  });
});

describe("마스터 멈춤 판정(FR-C5 · 직접 단추는 이때만)", () => {
  const a = approvalsOf({ items: [feedItem({ created_at: 1000 })] })![0];
  it("5분 = 설계 목표값 · 측정 대기 표지", () => {
    expect(CONFIRM_STALL_MS).toBe(300_000);
    expect(CONFIRM_STALL_MEASURED).toBe(false);
  });
  it("모름(마스터 행 없음)·살아 있음·소식 있음 = 멈춤 아님", () => {
    expect(itemStall(stall({ masterSid: undefined, masterAlive: null, masterIdleSecs: null }), a)).toBeNull();
    expect(itemStall(stall(), a)).toBeNull();
  });
  it("마스터 좌석 없음 · 꺼짐 확정 = 멈춤", () => {
    expect(masterSilenced(stall({ masterSid: null }))).toBe("no_master");
    expect(masterSilenced(stall({ masterAlive: false }))).toBe("master_off");
    expect(masterSilenced(stall({ masterAlive: null }))).toBeNull(); // 모름은 멈춤 아님
  });
  it("master.deadman = 멈춤 · 같은 마스터가 그 뒤 출력했거나 새 마스터가 서면 풀림", () => {
    const d = { at: 1_000_000 - 60_000, sid: 5 };
    expect(masterSilenced(stall({ deadman: d, masterIdleSecs: 120 }))).toBe("deadman");
    expect(masterSilenced(stall({ deadman: d, masterIdleSecs: 10 }))).toBeNull();
    expect(masterSilenced(stall({ deadman: d, masterSid: 9, masterIdleSecs: 999 }))).toBeNull();
    expect(masterSilenced(stall({ deadman: d, masterSid: undefined, masterAlive: null, masterIdleSecs: null }))).toBe("deadman");
  });
  it("그 요청의 approval.stalled = 멈춤", () => {
    expect(itemStall(stall({ stalledIds: new Set(["r1"]) }), a)).toBe("stalled_event");
    expect(itemStall(stall({ stalledIds: new Set(["r9"]) }), a)).toBeNull();
  });
  it("생긴 지 5분 ∧ 마스터 소식 5분 없음 = 멈춤 · 둘 중 하나라도 모자라면 아님", () => {
    const born = (1_000_000 - CONFIRM_STALL_MS) / 1000;
    const b = { ...a, created_at: born };
    expect(itemStall(stall({ masterIdleSecs: 300 }), b)).toBe("quiet");
    expect(itemStall(stall({ masterIdleSecs: 299 }), b)).toBeNull();
    expect(itemStall(stall({ masterIdleSecs: 300 }), { ...b, created_at: born + 1 })).toBeNull();
    expect(itemStall(stall({ masterIdleSecs: null }), b)).toBeNull();
  });
});

describe("띠(FR-C1·C1a·C6)", () => {
  const approvals = approvalsOf({ items: [feedItem(), feedItem({ request_id: "rm", surface_id: 5, created_at: 900 })] })!;
  it("모르면 「확인할 것 살펴보는 중」 · 0건 확정이면 숨김 · 아는 N", () => {
    expect(bandLabel(bandOf(null, [], stall()))).toBe("확인할 것 살펴보는 중");
    expect(bandLabel(bandOf([], null, stall()))).toBe("확인할 것 살펴보는 중");
    expect(bandLabel(bandOf([], [], stall({ masterSid: undefined })))).toBe("확인할 것 살펴보는 중");
    expect(bandLabel(bandOf([], [], stall()))).toBeNull();
    expect(bandLabel(bandOf(null, approvals, stall()))).toBe("확인이 필요해요 2 · 더 살펴보는 중");
    expect(bandLabel(bandOf([{ id: "q1", text: "물음", uuid: null }], approvals, stall()))).toBe("확인이 필요해요 3");
  });
  it("마스터 물음 먼저 · 마스터 좌석 승인 = 마스터 창(직접 단추 없음) · 도우미 = 평소 멈춤 아님", () => {
    const b = bandOf([{ id: "q1", text: "물음", uuid: null }], approvals, stall());
    expect(b.items.map((x) => x.kind)).toEqual(["ask", "master_screen", "helper"]);
    const h = b.items[2];
    expect(h.kind === "helper" && h.stall).toBeNull();
  });
});

describe("직접 허락 준비(FR-C5a 펼침) · 처리 직전 재확인(FR-C5b 판 묶기)", () => {
  const a = approvalsOf({ items: [feedItem()] })![0];
  const helper = (st: "deadman" | null) => ({ kind: "helper" as const, key: "k", a, stall: st });
  it("멈춤 아님 = 허락·거절 모두 안 됨", () => {
    expect(allowReady(helper(null), true, "allow").ok).toBe(false);
    expect(allowReady(helper(null), true, "deny").ok).toBe(false);
    expect(allowReady({ kind: "ask", key: "q", q: { id: "q", text: "x", uuid: null } }, true, "allow").ok).toBe(false);
  });
  it("멈춤 · 펼치기 전 허락 = 흐림 안내 · 펼친 뒤 = 됨 · 거절은 펼침 없이 됨", () => {
    const r = allowReady(helper("deadman"), false, "allow");
    expect(r.ok === false && r.msg).toContain("무엇을 보기");
    expect(allowReady(helper("deadman"), true, "allow").ok).toBe(true);
    expect(allowReady(helper("deadman"), false, "deny").ok).toBe(true);
  });
  const st = () => "deadman" as const;
  const b = boundOf(a);
  it("같은 번호·시각·본문·좌석 ∧ 지금도 멈춤 = 통과", () => {
    expect(recheck(b, [a], st).ok).toBe(true);
  });
  it("모름 · 이미 처리(목록에 없음) · 판 바뀜(본문·시각·좌석) · 멈춤 풀림 = 호출 0 + 안내", () => {
    const code = (r: ReturnType<typeof recheck>) => (r.ok ? "ok" : r.code);
    expect(code(recheck(b, null, st))).toBe("unknown");
    expect(code(recheck(b, [], st))).toBe("gone");
    expect(code(recheck(b, [{ ...a, body: body("rm -rf /") }], st))).toBe("changed");
    expect(code(recheck(b, [{ ...a, created_at: a.created_at + 1 }], st))).toBe("changed");
    expect(code(recheck(b, [{ ...a, surface_id: 8 }], st))).toBe("changed");
    expect(code(recheck(b, [a], () => null))).toBe("not_stalled");
    const g = recheck(b, [], st);
    expect(g.ok === false && g.msg).toBe("이미 처리됐거나 바뀐 요청이에요.");
  });
  it("feed_reply 실패 글 → 사람 글", () => {
    expect(replyErrorMsg("invalid_params: item already resolved")).toBe("이미 처리됐거나 바뀐 요청이에요.");
    expect(replyErrorMsg("approval_screen_gone: x")).toContain("이미 사라졌어요");
    expect(replyErrorMsg("approval_actuation_refused: x")).toContain("누르지 않았어요");
    expect(replyErrorMsg("self_approval_denied: x")).toContain("self_approval_denied");
  });
});
