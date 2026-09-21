import { describe, it, expect } from "bun:test";
import {
  unsubmittedSurfaces,
  parseBriefSections,
  recordedAt,
  stateCandidates,
  buildBriefCard,
  friendlyRole,
  plainLine,
  INTERNAL_TERMS,
  BRIEF_MAX_ITEMS,
  cycleAdviceLines,
  CYCLE_ADVICE_PCT,
} from "./restorebrief";

const SAMPLE = `# SESSION_STATE
갱신 2026-09-18 09:10
## ✅ 완료
- **로그인 화면** 고치기 끝
- [x] 시험 전부 통과
  - 하위 항목은 빠진다
## 진행 중
- 결제 화면 만드는 중 \`pay.ts\`
설명 문단은 싣지 않는다
## 📌 결정 필요
- [[배포 날짜]] 정하기
## 기타
- 이 절은 무시된다
2026-09-18T10:42 마지막 저장
`;

describe("parseBriefSections — 고정 3절만 뽑는다", () => {
  it("세 절의 목록 줄만, 꾸밈을 걷어서", () => {
    const s = parseBriefSections(SAMPLE);
    expect(s.done).toEqual(["로그인 화면 고치기 끝", "시험 전부 통과"]);
    expect(s.doing).toEqual(["결제 화면 만드는 중 pay.ts"]);
    expect(s.decide).toEqual(["배포 날짜 정하기"]);
  });
  it("다른 절(기타)의 항목은 섞이지 않는다", () => {
    const s = parseBriefSections(SAMPLE);
    expect([...s.done, ...s.doing, ...s.decide].some((l) => l.includes("무시"))).toBe(false);
  });
  it("절 제목이 없으면 빈 배열이다(지어내지 않는다)", () => {
    expect(parseBriefSections("# 아무거나\n- 항목")).toEqual({ done: [], doing: [], decide: [] });
  });
  it("절마다 최대 개수까지만", () => {
    const many = "## 완료\n" + Array.from({ length: 9 }, (_, i) => `- 항목${i}`).join("\n");
    expect(parseBriefSections(many).done.length).toBe(BRIEF_MAX_ITEMS);
  });
  it("긴 줄은 말줄임으로 자른다", () => {
    expect([...plainLine("- " + "가".repeat(200))].length).toBeLessThan(81);
  });
});

describe("recordedAt — 기록 시각", () => {
  it("가장 늦은 날짜+시각", () => expect(recordedAt(SAMPLE)).toBe("2026-09-18 10:42"));
  it("시각이 없으면 날짜만", () => expect(recordedAt("2026-09-01 과 2026-09-03")).toBe("2026-09-03"));
  it("아무것도 없으면 null", () => expect(recordedAt("없음")).toBeNull());
});

describe("stateCandidates — 위로 올라가되 홈을 넘지 않는다", () => {
  it("맥 경로", () => {
    expect(stateCandidates("/srv/home/a/proj/sub", "/srv/home/a")).toEqual([
      "/srv/home/a/proj/sub/_round/SESSION_STATE.md",
      "/srv/home/a/proj/_round/SESSION_STATE.md",
      "/srv/home/a/_round/SESSION_STATE.md",
    ]);
  });
  it("윈도우 경로", () => {
    expect(stateCandidates("D:\\work\\a\\proj", "D:\\work\\a")).toEqual([
      "D:\\work\\a\\proj\\_round\\SESSION_STATE.md",
      "D:\\work\\a\\_round\\SESSION_STATE.md",
    ]);
  });
  it("작업 폴더를 모르면 후보 0", () => expect(stateCandidates(null, "/srv/home/a")).toEqual([]));
});

describe("buildBriefCard — 초보자 문구 · 내부 용어 0", () => {
  const card = buildBriefCard({
    sections: parseBriefSections(SAMPLE),
    recordedAt: "2026-09-18 10:42",
    restoredRoles: ["master", "cso", "worker-2"],
    waitingRoles: ["reviewer-codex", "master"],
  });
  const all = JSON.stringify(card);
  it("★내부 용어가 한 글자도 없다", () => {
    for (const t of INTERNAL_TERMS) expect(all.toLowerCase().includes(t.toLowerCase())).toBe(false);
  });
  it("역할은 쉬운 이름으로, 살아난 역할은 '켜지는 중'에 다시 안 나온다", () => {
    expect(card.lines[0].items[0]).toBe("총괄 · 운영 관리 · 작업 창이 다시 켜졌습니다.");
    expect(card.lines[0].items[1]).toBe("검토 창은 아직 켜지는 중입니다. 잠시 뒤 저절로 붙습니다.");
  });
  it("기록 시각을 밝히고, 그 뒤 일이 빠질 수 있다고 말한다", () => {
    expect(card.foot.includes("2026-09-18 10:42")).toBe(true);
  });
  it("작업 기록이 없으면 없다고 말한다", () => {
    const c = buildBriefCard({ sections: null, recordedAt: null, restoredRoles: [], waitingRoles: [] });
    expect(JSON.stringify(c).includes("찾지 못했습니다")).toBe(true);
    expect(c.foot.includes("알 수 없습니다")).toBe(true);
  });
  it("모르는 역할 코드명을 화면에 내지 않는다", () => expect(friendlyRole("ceo-x")).toBe("도우미"));
});

// ────────────────────────────────────────────────────────────────────────────
// TICKET=v111-restore — ①묻지 않는다(질문·주입 경로 0) · ④60%+ 순환 권유(집행 0)
// ────────────────────────────────────────────────────────────────────────────
describe("카드는 묻지 않는다 — 질문 버튼·주입 문안이 존재하지 않는다", () => {
  const card = buildBriefCard({
    sections: parseBriefSections(SAMPLE),
    recordedAt: "2026-09-18 10:42",
    restoredRoles: ["master"],
    waitingRoles: [],
  });
  it("★[이어서 진행] 라벨·주입 문안 칸이 카드에 없다(필드 부재)", () => {
    // 필드가 '비어 있다'가 아니라 '없다'를 단언한다 — 빈 문자열로 남기면 소비부가 버튼을 다시 그린다.
    expect(Object.keys(card)).not.toContain("continueLabel");
    expect(Object.keys(card)).not.toContain("continueText");
  });
  it("버튼은 [닫기] 하나다", () => expect(card.closeLabel).toBe("닫기"));
  it("★제목이 질문이 아니다(물음표 0)", () => expect(card.title.includes("?")).toBe(false));
  it("★카드 전문에 '이어서 진행' 문구가 0건이다", () =>
    expect(JSON.stringify(card).includes("이어서 진행")).toBe(false));
});

describe("cycleAdviceLines — 60%+ 자리에 권유 한 줄(집행 0)", () => {
  it("문턱은 워커 규율과 같은 60이다", () => expect(CYCLE_ADVICE_PCT).toBe(60));
  it("문턱 미만이면 한 줄도 얹지 않는다", () =>
    expect(cycleAdviceLines([{ role: "master", ctxPct: 59 }])).toEqual([]));
  it("★경계값(정확히 60)은 권유한다", () =>
    expect(cycleAdviceLines([{ role: "master", ctxPct: 60 }]).length).toBe(1));
  it("못 잰 자리(null)는 넘었다고 말하지 않는다", () =>
    expect(cycleAdviceLines([{ role: "master", ctxPct: null }])).toEqual([]));
  it("★숫자가 아닌 값이 오면(데몬 JSON 문자열) 넘었다고 말하지 않는다", () => {
    // 이 줄이 없으면 `typeof === "number"` 가드를 지워도 스위트가 초록이다(등가 뮤턴트로 보인다)
    // — null 만으로는 JS 의 `null >= 60 === false` 가 가드를 대신해 주기 때문이다.
    // 실제 재료는 데몬 JSON(usage.ctx_pct)이라 타입이 문자열로 올 수 있고, 그때
    // `"97" >= 60` 은 **참**이 되어 못 잰 값이 권유가 된다.
    const dirty = [{ role: "master", ctxPct: "97" as unknown as number }];
    expect(cycleAdviceLines(dirty)).toEqual([]);
  });
  it("넘은 자리만 쉬운 이름으로 모아 한 줄", () => {
    const l = cycleAdviceLines([
      { role: "master", ctxPct: 97 },
      { role: "cso", ctxPct: 72 },
      { role: "worker-2", ctxPct: 12 },
    ]);
    expect(l).toEqual(["총괄 · 운영 관리 창은 기억한 내용이 60%를 넘었어요. 한 번 정리(순환)를 권해요."]);
  });
  it("★권유일 뿐 집행이 아니다 — 문구에 명령·질문이 없다", () => {
    const [line] = cycleAdviceLines([{ role: "master", ctxPct: 80 }]);
    expect(line.includes("?")).toBe(false);
    expect(line.includes("권해요")).toBe(true);
  });
  it("카드에 실리고 내부 용어는 0건이다", () => {
    const c = buildBriefCard({
      sections: null,
      recordedAt: null,
      restoredRoles: ["master", "worker-2"],
      waitingRoles: [],
      seatCtx: [
        { role: "master", ctxPct: 97 },
        { role: "worker-2", ctxPct: 3 },
      ],
    });
    const all = JSON.stringify(c);
    expect(all.includes("한 번 정리(순환)를 권해요")).toBe(true);
    for (const t of INTERNAL_TERMS) expect(all.toLowerCase().includes(t.toLowerCase())).toBe(false);
  });
  it("seatCtx 미지정(구 호출부)이면 권유 줄이 없다 — 추가는 순수 additive", () => {
    const c = buildBriefCard({ sections: null, recordedAt: null, restoredRoles: ["master"], waitingRoles: [] });
    expect(JSON.stringify(c).includes("순환")).toBe(false);
  });
});

describe("v112-restore ① 미제출 자리 정직 표기", () => {
  const now = 10_000;
  const rec = (ts: number, surface: number, state: string) => JSON.stringify({ ts, surface, state, resubmitted: true });
  it("자리마다 가장 늦은 기록만 본다 — 뒤에 제출됐으면 미제출이 아니다", () => {
    const log = [rec(now - 30, 47, "not_submitted"), rec(now - 10, 47, "submitted"), rec(now - 5, 46, "not_submitted")].join("\n");
    expect(unsubmittedSurfaces(log, now)).toEqual([46]);
  });
  it("입력창 미실측으로 보내지 않은 자리(held_input_not_ready)도 미전달로 센다", () => {
    expect(unsubmittedSurfaces(rec(now - 3, 9, "held_input_not_ready"), now)).toEqual([9]);
  });
  it("창 밖 기록·못 잰 기록·깨진 줄은 미제출로 말하지 않는다", () => {
    const log = [rec(now - 5000, 47, "not_submitted"), rec(now - 5, 48, "unmeasured"), "{깨짐", ""].join("\n");
    expect(unsubmittedSurfaces(log, now)).toEqual([]);
  });
  it("카드에 미제출 한 줄이 붙고 내부 용어는 0건", () => {
    const c = buildBriefCard({ sections: null, recordedAt: null, restoredRoles: ["worker"], waitingRoles: [], unsubmittedRoles: ["worker"] });
    const all = JSON.stringify(c);
    expect(all.includes("전송되지 않음")).toBe(true);
    for (const t of INTERNAL_TERMS) expect(all.includes(t)).toBe(false);
  });
  it("미제출 자리가 없으면 그 줄도 없다", () => {
    const c = buildBriefCard({ sections: null, recordedAt: null, restoredRoles: ["worker"], waitingRoles: [], unsubmittedRoles: [] });
    expect(JSON.stringify(c).includes("전송되지 않음")).toBe(false);
  });
});
