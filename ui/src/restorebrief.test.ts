import { describe, it, expect } from "bun:test";
import {
  parseBriefSections,
  recordedAt,
  stateCandidates,
  buildBriefCard,
  friendlyRole,
  plainLine,
  INTERNAL_TERMS,
  BRIEF_MAX_ITEMS,
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
