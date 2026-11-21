// (cysr-ui-slice4) 확인 대기 판정 시험 — 순수. P2-DESIGN §5-4 · §2-7 · PRD FR-C1~C6.
import { describe, it, expect } from "bun:test";
import {
  actuatedOf,
  ALLOW_AT_WORK_MSG,
  allowReady,
  approvalsOf,
  bandLabel,
  bandOf,
  boundOf,
  canAllowDirect,
  CMD_MAX_CHARS,
  CMD_MAX_LINES,
  CONFIRM_STALL_MEASURED,
  CONFIRM_STALL_MS,
  ABSENT_GRACE_MS,
  DEADMAN_MAX_AGE_MS,
  deadmanRevived,
  FINGERPRINT_MISMATCH_CODE,
  itemStall,
  markersOf,
  masterSilenced,
  openQuestions,
  parseApprovalBody,
  recheck,
  replyErrorMsg,
  resolveKey,
  resolves,
  versionKey,
  type Bound,
  type StallInput,
} from "./confirms";
import type { Rec } from "./msgstep";

const A = (text: string, uuid = "a1", extra: Partial<Rec> = {}): Rec => ({ uuid, parent: null, role: "assistant", text, ts: null, ...extra });
const body = (cmd: string, ro = "쓰기·삭제 가능") => `Do you want to proceed?\n— 명령 원문:\n${cmd}\n— 읽기 전용 판정(기계 추정 · 근거 아님): ${ro}`;
const feedItem = (o: Partial<Record<string, unknown>> = {}) => ({ request_id: "r1", kind: "approval", status: "pending", surface_id: 7, created_at: 1000, daemon_issued: true, body: body("rm -rf build"), ...o });
/** 데몬 지문 표지가 있는 판(지문 대조를 지원하는 앞날의 데몬 · 지금 데몬엔 없음) */
const fpItem = (o: Partial<Record<string, unknown>> = {}) => feedItem({ screen_fingerprint: "fp-1", ...o });
const stall = (o: Partial<StallInput> = {}): StallInput => ({ now: 1_000_000, masterSid: 5, masterAlive: true, masterIdleSecs: 1, deadman: null, absentSince: 0, stalledIds: new Set(), ...o });

describe("마스터 물음 표식 — 줄머리 정확 일치만(§5-4)", () => {
  it("⟪확인 요청: …⟫ 한 줄 = 물음 1 · 뒤 공백은 봐줌", () => {
    expect(markersOf(A("앞 말\n⟪확인 요청: 배포할까요?⟫  \n뒷 말"))).toEqual([{ kind: "ask", text: "배포할까요?", uuid: "a1" }]);
  });
  it("줄 중간·들여쓰기·끝 표시 없음·빈 물음 = 0(꾸미지 않음)", () => {
    for (const t of ["예: ⟪확인 요청: 배포할까요?⟫", " ⟪확인 요청: 배포할까요?⟫", "⟪확인 요청: 배포할까요?", "⟪확인 요청:  ⟫", "⟪확인요청: 붙임⟫", "📌 결정 필요: 배포할까요?"]) expect(markersOf(A(t))).toEqual([]);
  });
  it("(검증 F8) ~~~ 울타리 · 들여쓴 ``` · ```` 안의 ``` 예시 = 0 · 울타리 닫힌 뒤 표식 = 1", () => {
    expect(markersOf(A("~~~\n⟪확인 요청: 물결 울타리⟫\n~~~"))).toEqual([]);
    expect(markersOf(A("1. 예:\n   ```\n⟪확인 요청: 들여쓴 울타리⟫\n   ```"))).toEqual([]);
    expect(markersOf(A("````md\n```\n⟪확인 요청: 네 개 울타리 안⟫\n```\n````"))).toEqual([]);
    expect(markersOf(A("```\n예시\n```\n⟪확인 요청: 진짜 물음⟫")).map((e) => e.kind)).toEqual(["ask"]);
  });
  it("사람(user) 글 · 곁가지 · 코드 울타리 안 = 0", () => {
    expect(markersOf({ ...A("⟪확인 요청: 사람이 친 표식⟫"), role: "user" })).toEqual([]);
    expect(markersOf(A("⟪확인 요청: 곁가지⟫", "a1", { sidechain: true }))).toEqual([]);
    expect(markersOf(A("표식 꼴은 이렇게:\n```\n⟪확인 요청: 예시⟫\n```\n끝"))).toEqual([]);
  });
  it("해결 표식 = 실린 글 전부(대조는 resolves)", () => {
    expect(markersOf(A("⟪확인 해결: 가나다라마바사아자차카타파하가나다라마바사아자⟫"))).toEqual([{ kind: "resolve", key: "가나다라마바사아자차카타파하가나다라마바사아자", uuid: "a1" }]);
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
  it("(codex 1R 탐침) 앞 20자만 같고 뒷말이 다른 해결 · 20자보다 짧은 해결 = 안 닫힘 · 짧은 물음은 전체로", () => {
    const p = "12345678901234567890";
    expect(openQuestions([ask(`${p}실제 질문`), { kind: "resolve", key: `${p}틀린 뒷말`, uuid: null }]).length).toBe(1);
    expect(openQuestions([ask(`${p}실제 질문`), { kind: "resolve", key: "1234567890", uuid: null }]).length).toBe(1);
    expect(openQuestions([ask(`${p}실제 질문`), { kind: "resolve", key: `${p}실제`, uuid: null }]).length).toBe(0);
    expect(openQuestions([ask("배포할까요?"), { kind: "resolve", key: "배포할까요?", uuid: null }]).length).toBe(0);
    expect(openQuestions([ask("배포할까요?"), { kind: "resolve", key: "배포", uuid: null }]).length).toBe(1);
  });
  it("(검증 F4 · codex 1R major 6) 20번째 글자가 띄어쓰기여도 표식 판독이 깎지 않아 「앞 20자」 그대로 닫힘", () => {
    const q = "이번 금요일 배포를 다음 주 월요일 오후로 미뤄도 될까요?";
    const k20 = Array.from(q).slice(0, 20).join("");
    expect(k20.endsWith(" ")).toBe(true); // 이 견본의 20번째 글자 = 띄어쓰기
    const ev = markersOf(A(`⟪확인 해결: ${k20}⟫`));
    expect(ev).toEqual([{ kind: "resolve", key: k20, uuid: "a1" }]); // 20번째 공백 보존
    expect(openQuestions([ask(q), ...ev]).length).toBe(0);
    expect(openQuestions([ask(q), { kind: "resolve", key: "이번 금요일 배포를 다음 주", uuid: null }]).length).toBe(1);
  });
  it("(codex 2R minor) 물음 글도 깎지 않음 — 20번째 글자가 끝 공백인 물음 · 앞 공백 물음의 원문 앞 20자 해결이 닫음", () => {
    const q = "abcdefghijklmnopqrs ";
    const ev = markersOf(A(`⟪확인 요청: ${q}⟫`));
    expect(ev).toEqual([{ kind: "ask", text: q, uuid: "a1" }]);
    expect(openQuestions([...ev, ...markersOf(A(`⟪확인 해결: ${resolveKey(q)}⟫`, "a2"))]).length).toBe(0);
    const lead = markersOf(A("⟪확인 요청:  앞 공백 물음⟫"));
    expect(openQuestions([...lead, ...markersOf(A("⟪확인 해결:  앞 공백 물음⟫", "a3"))]).length).toBe(0);
    expect(markersOf(A("⟪확인 요청:   ⟫"))).toEqual([]); // 빈 물음은 여전히 0
  });
  it("(codex 1R major 6) 대조 = 원문 코드 포인트 그대로 — 공백 수가 다른 해결은 닫지 않고 · 띄어쓰기 두 칸 물음의 정확한 앞 20자는 닫음", () => {
    // ① 거짓 해결: 물음 「…t  X」(두 칸) 를 「…t X」(한 칸) 해결이 닫으면 안 된다
    expect(resolves("abcdefghijklmnopqrst  X", "abcdefghijklmnopqrst X")).toBe(false);
    expect(openQuestions([ask("abcdefghijklmnopqrst  X"), ...markersOf(A("⟪확인 해결: abcdefghijklmnopqrst X⟫"))]).length).toBe(1);
    // ② 정상 해결 누락: 물음 안 두 칸 공백 — resolveKey 가 만든 정확한 앞 20자는 닫아야 한다
    const q = "abcdefghij  klmnopqrstuvw";
    expect(resolves(q, resolveKey(q))).toBe(true);
    expect(openQuestions([ask(q), ...markersOf(A(`⟪확인 해결: ${resolveKey(q)}⟫`))]).length).toBe(0);
    // ③ 공백을 하나로 줄인 해결은 안 닫힘
    expect(resolves(q, "abcdefghij klmnopqrst")).toBe(false);
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
  it("pending approval 만 · 오래된 것부터 · 꼴 틀림 = null(모름)", () => {
    const got = approvalsOf({ items: [feedItem({ request_id: "r2", created_at: 2000 }), feedItem(), feedItem({ request_id: "x", kind: "question" }), feedItem({ request_id: "y", status: "resolved" })] });
    expect(got?.map((a) => a.request_id)).toEqual(["r1", "r2"]);
    expect(approvalsOf(null)).toBeNull();
    expect(approvalsOf({ nope: 1 })).toBeNull();
    expect(approvalsOf({ items: [] })).toEqual([]);
    // (codex 1R 탐침 · 검증 V14) 대기 중 승인이 꼴이 깨졌으면(번호·좌석·시각 칸 어느 것이든) 0건이 아니라 모름
    expect(approvalsOf({ items: [feedItem(), feedItem({ request_id: "z", surface_id: null })] })).toBeNull();
    expect(approvalsOf({ items: [feedItem(), feedItem({ request_id: 7 })] })).toBeNull();
    expect(approvalsOf({ items: [feedItem(), feedItem({ request_id: "t", created_at: "x" })] })).toBeNull();
  });
  it("(검증 F0) 데몬이 화면에서 감지한 창(daemon_issued · 없으면 번호 접두 daemon-)만 screen · 좌석이 올린 approval 은 직접 단추 0", () => {
    const [a, b, c, d] = approvalsOf({ items: [feedItem({ request_id: "r1" }), feedItem({ request_id: "req-1", daemon_issued: false }), feedItem({ request_id: "daemon-9", daemon_issued: undefined }), feedItem({ request_id: "req-2", daemon_issued: undefined })] })!;
    expect([a.screen, b.screen, c.screen, d.screen]).toEqual([true, false, true, false]);
    const st = stall({ masterSid: null });
    expect(itemStall(st, a)).toBe("no_master");
    expect(itemStall(st, b)).toBeNull();
    expect(itemStall(stall({ stalledIds: new Set(["req-1"]) }), b)).toBeNull();
  });
  it("(codex 1R blocking) 데몬 지문 표지 = feed 항목 screen_fingerprint(비어 있지 않은 글)만 · 지금 데몬(칸 없음) = null → 직접 허락 0", () => {
    const [a, b, c, d] = approvalsOf({ items: [feedItem({ request_id: "r1" }), fpItem({ request_id: "r2" }), feedItem({ request_id: "r3", screen_fingerprint: "" }), feedItem({ request_id: "r4", screen_fingerprint: 7 })] })!;
    expect([a.fingerprint, b.fingerprint, c.fingerprint, d.fingerprint]).toEqual([null, "fp-1", null, null]);
    expect([a, b, c, d].map(canAllowDirect)).toEqual([false, true, false, false]);
    expect(canAllowDirect({ ...b, screen: false })).toBe(false); // 좌석이 올린 approval 은 지문이 있어도 아님
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
    // (codex 1R major 4) 마스터 좌석을 모르는 동안은 그 요청의 approval.stalled ·5분 규칙이 있어도 직접 단추 0
    const old = { ...a, created_at: (1_000_000 - CONFIRM_STALL_MS) / 1000 };
    expect(itemStall(stall({ masterSid: undefined, masterAlive: null, masterIdleSecs: 999, stalledIds: new Set(["r1"]) }), old)).toBeNull();
    expect(itemStall(stall(), a)).toBeNull();
  });
  it("(검증 F5) 좌석 없음·꺼짐 확정은 30초 이어져야 멈춤(다시 켜는 사이 단추 0)", () => {
    expect(ABSENT_GRACE_MS).toBe(30_000);
    expect(masterSilenced(stall({ masterSid: null, absentSince: 1_000_000 - 29_999 }))).toBeNull();
    expect(masterSilenced(stall({ masterSid: null, absentSince: 1_000_000 - 30_000 }))).toBe("no_master");
    expect(masterSilenced(stall({ masterAlive: false, absentSince: null }))).toBeNull();
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
    // (검증 F2 ⓐ) 마스터 상태 모름이면 deadman 을 멈춤 근거로 안 씀
    expect(masterSilenced(stall({ deadman: d, masterSid: undefined, masterAlive: null, masterIdleSecs: null }))).toBeNull();
    // (뮤턴트 「F2 마스터 모름이어도 deadman 근거」 생존 막음) 좌석 모름이면 생존 칸이 무엇이든 deadman 근거 아님 — masterSilenced 자체 계약
    expect(masterSilenced(stall({ deadman: d, masterSid: undefined, masterAlive: true, masterIdleSecs: 120 }))).toBeNull();
    // (codex 1R major 1) 생존 모름(null)이어도 사건 뒤 새 출력 = 풀림 · 생존 모름 관측만으로는 deadman 근거 아님 · 꺼짐 확정(false)은 풀림 아님
    expect(deadmanRevived(stall({ deadman: d, masterAlive: null, masterIdleSecs: 0 }))).toBe(true);
    expect(deadmanRevived(stall({ deadman: d, masterAlive: null, masterIdleSecs: 120 }))).toBe(false);
    expect(deadmanRevived(stall({ deadman: d, masterAlive: true, masterIdleSecs: 10 }))).toBe(true);
    expect(deadmanRevived(stall({ deadman: d, masterAlive: false, masterIdleSecs: 0 }))).toBe(false);
    expect(masterSilenced(stall({ deadman: d, masterAlive: null, masterIdleSecs: 120 }))).toBeNull();
    expect(masterSilenced(stall({ deadman: d, masterAlive: false, masterIdleSecs: 0, absentSince: null }))).toBe("deadman");
    // (검증 F2) 나이 상한 300초 — 데몬은 아직 죽어 있으면 300초마다 다시 알린다
    expect(masterSilenced(stall({ deadman: { at: 1_000_000 - DEADMAN_MAX_AGE_MS - 1, sid: 5 }, masterIdleSecs: 999 }))).toBeNull();
    expect(masterSilenced(stall({ deadman: { at: 1_000_000 - DEADMAN_MAX_AGE_MS, sid: 5 }, masterIdleSecs: 999 }))).toBe("deadman");
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
  const a = approvalsOf({ items: [fpItem()] })![0];
  const now0 = approvalsOf({ items: [feedItem()] })![0]; // 지금 데몬(지문 표지 없음)
  const helper = (st: "deadman" | null, x = a) => ({ kind: "helper" as const, key: "k", a: x, stall: st });
  it("(codex 1R blocking) 지문 표지 없는 판 = 펼쳐도 허락 0(작업 화면 안내) · 거절은 됨", () => {
    const r = allowReady(helper("deadman", now0), true, "allow");
    expect(r.ok === false && r.msg).toBe(ALLOW_AT_WORK_MSG);
    expect(ALLOW_AT_WORK_MSG).toBe("마스터가 멈췄어요. 허락은 작업 화면의 그 도우미 창에서 직접 눌러 주세요.");
    expect(allowReady(helper("deadman", now0), false, "deny").ok).toBe(true);
  });
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
    expect(code(recheck(b, [{ ...a, fingerprint: "fp-2" }], st))).toBe("changed"); // 지문이 바뀜(같은 번호 · 다른 창)
    expect(code(recheck(b, [{ ...a, fingerprint: null }], st))).toBe("changed"); // 지문 표지가 사라짐
    expect(code(recheck(b, [a], () => null))).toBe("not_stalled");
    const g = recheck(b, [], st);
    expect(g.ok === false && g.msg).toBe("이미 처리됐거나 바뀐 요청이에요.");
  });
  it("(codex 1R major 2) 판 열쇠 = Bound 칸 전부(번호·시각·본문·좌석·지문) — 어느 하나만 바뀌어도 다른 열쇠(펼침 해제)", () => {
    const fields = Object.keys(b) as Array<keyof Bound>;
    expect(fields.sort()).toEqual(["body", "created_at", "fingerprint", "request_id", "surface_id"]);
    const alt: Record<keyof Bound, unknown> = { request_id: "r9", created_at: a.created_at + 1, body: body("ls"), surface_id: a.surface_id + 1, fingerprint: "fp-9" };
    for (const f of fields) expect(versionKey({ ...a, [f]: alt[f] })).not.toBe(versionKey(a));
    expect(versionKey({ ...a })).toBe(versionKey(a));
  });
  it("(codex 1R major 5) 데몬 결과 actuated — 글일 때만 실제로 눌림 · null·없음 = 기록만", () => {
    expect(actuatedOf({ actuated: "return" })).toBe("return");
    expect(actuatedOf({ actuated: null })).toBeNull();
    expect(actuatedOf({ request_id: "r1" })).toBeNull();
    expect(actuatedOf(null)).toBeNull();
    expect(actuatedOf({ actuated: "" })).toBeNull();
  });
  it("feed_reply 실패 글 → 사람 글", () => {
    expect(replyErrorMsg(`${FINGERPRINT_MISMATCH_CODE}: x`)).toContain("달라져 누르지 않았어요");
    expect(replyErrorMsg("invalid_params: item already resolved")).toBe("이미 처리됐거나 바뀐 요청이에요.");
    expect(replyErrorMsg("approval_screen_gone: x")).toContain("이미 사라졌어요");
    expect(replyErrorMsg("approval_actuation_refused: x")).toContain("누르지 않았어요");
    expect(replyErrorMsg("self_approval_denied: x")).toContain("self_approval_denied");
  });
});
