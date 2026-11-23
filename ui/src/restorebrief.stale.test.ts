// (TICKET=cysr-1118u-chat ④ · master 판정 A) 윈 1.1.17 관찰: 「다시 켜졌어요」 카드가 옛 기록(11-22 11:04)을 보임.
// 고르기 계약(pickBriefText · 판정 B 후속 — 기록 줄 있는 파일 먼저 · 3절 없는 파일은 고르지 않음)은 **그대로** 두고,
// 고른 요약보다 늦은 손길이 **다른 후보 파일**에 있으면 요약 앞에 알림 한 줄(「이 요약은 <시각> 기준이라 그 뒤 일은 빠졌을 수 있어요.」).
// 대조군 = 기점(9c46ff6d0): briefNewerElsewhere·staleBriefLine 없음 → 이 파일 붉음.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { briefNewerElsewhere, buildBriefCard, INTERNAL_TERMS, parseBriefSections, pickBriefText, recordedAt, staleBriefLine } from "./restorebrief";

const NOW = "2026-11-23 06:10";
// 재시작 저장(마스터 작업 폴더 _round) — 3절 + 기록 줄 · 11-22 11:04
const DRAIN = "# S\n## 완료\n- 옛 일 마침\n## 진행 중\n- 옛 일 하는 중\n## 결정 필요\n기록 2026-11-22 11:04\n";
// 정본 — 그 뒤로 마스터가 계속 고침(3절 기록 줄 없음 · 기계용 절 11-23 05:40)
const CANON_NO_REC = "# S\n## 완료\n- 새 일 마침\n## 진행 중\n- 새 일\n## 결정 필요\n\n## 오너 지시 대장\n| 2026-11-23 05:40 | 1.1.17 설치 | 끝 |";
// 정본 — 3절 없음(설치 골격처럼) · 기계용 절 11-23 05:40
const CANON_NO_HEADS = "# S\n## 현재 위치\n- 1.1.17 설치 끝 2026-11-23 05:40\n## 다음 액션 큐\n";

function card(found: { path: string; text: string }[]) {
  const text = pickBriefText(found, NOW);
  return {
    text,
    card: buildBriefCard({
      sections: text === null ? null : parseBriefSections(text),
      recordedAt: text === null ? null : recordedAt(text, NOW),
      restoredRoles: ["master"],
      waitingRoles: [],
      newerElsewhere: briefNewerElsewhere(found, text, NOW),
    }),
  };
}
const note = (c: ReturnType<typeof buildBriefCard>) => c.lines.find((l) => l.head === "알려 드려요")?.items ?? [];

describe("④ 나옴 — 고른 요약보다 다른 파일이 더 늦다", () => {
  it("정본(3절 기록 줄 없음 · 05:40) vs 재시작 저장(기록 11-22 11:04): 계약대로 재시작 저장을 고르고 + 알림 한 줄", () => {
    const { text, card: c } = card([{ path: "canon", text: CANON_NO_REC }, { path: "cwd", text: DRAIN }]);
    expect(text).toBe(DRAIN); // 고르기 계약 그대로(판정 B 후속 「반대 방향」)
    expect(note(c)).toEqual(["이 요약은 2026-11-22 11:04 기준이라 그 뒤 일은 빠졌을 수 있어요."]);
    const order = c.lines.map((l) => l.head);
    expect(order.indexOf("알려 드려요")).toBe(order.indexOf("끝난 일") - 1); // 요약 바로 앞
  });
  it("정본에 3절이 없어도(설치 골격 꼴) 더 늦은 손길이면 알림", () => {
    const { text, card: c } = card([{ path: "canon", text: CANON_NO_HEADS }, { path: "cwd", text: DRAIN }]);
    expect(text).toBe(DRAIN);
    expect(note(c).length).toBe(1);
  });
});

describe("④ 안 나옴", () => {
  it("후보가 하나뿐", () => {
    expect(note(card([{ path: "cwd", text: DRAIN }]).card)).toEqual([]);
  });
  it("다른 파일이 더 이르다(고른 요약이 가장 새것)", () => {
    const older = "# S\n## 현재 위치\n- 2026-11-21 09:00 상태\n";
    expect(note(card([{ path: "canon", text: older }, { path: "cwd", text: DRAIN }]).card)).toEqual([]);
  });
  it("다른 파일의 늦은 시각이 「지금 이후」(예정)면 손길로 치지 않는다", () => {
    const planned = "# S\n## 다음 액션 큐\n- 2026-11-24 09:00 점검 예정\n";
    expect(note(card([{ path: "canon", text: planned }, { path: "cwd", text: DRAIN }]).card)).toEqual([]);
  });
  it("고른 요약이 없으면(3절 있는 파일 0) 알림도 없다 · 고른 요약의 시각을 모르면 말하지 않는다", () => {
    expect(note(card([{ path: "canon", text: CANON_NO_HEADS }]).card)).toEqual([]);
    expect(briefNewerElsewhere([{ path: "a", text: "## 완료\n- x" }, { path: "b", text: CANON_NO_HEADS }], "## 완료\n- x", NOW)).toBe(false);
  });
});

describe("④ 문구·배선", () => {
  it("내부 용어 0 · 물음표 0", () => {
    const l = staleBriefLine("2026-11-22 11:04");
    for (const t of INTERNAL_TERMS) expect(`${t}:${l.toLowerCase().includes(t.toLowerCase())}`).toBe(`${t}:false`);
    expect(l).not.toContain("?");
  });
  it("main.ts 카드가 고른 found·text·now 로 briefNewerElsewhere 를 넘긴다", () => {
    const src = readFileSync(new URL("./main.ts", import.meta.url), "utf-8");
    const f = src.slice(src.indexOf("async function showRestoreBrief()"));
    const body = f.slice(0, f.indexOf("document.getElementById(\"restore-brief\")?.remove();"));
    expect(body).toContain("newerElsewhere: briefNewerElsewhere(found, text, now),");
  });
});

// (④ 재검 · master#bcc58fe0 윈 실측) 정본 하나 = 맨 위 「## 완료 / ## 진행 중 / 기록 …」 뒤에 「## [날짜 DRAIN-VERIFY …]」 절이 최신순으로 여럿(그 안에도 3절 제목).
// 윈 정본(~\.cys\pack\round\SESSION_STATE.md) 머리 줄(1·3·7·9·11·19·26행) 모양 그대로 · 작업 폴더 _round = 3절 없음(후보 탈락).
describe("④ 재검 — 한 파일 안: 맨 위 3절만 · 아래 날짜 절에 새 손길이면 알림", () => {
  const win = (top: string) =>
    [
      "# SESSION_STATE — example-project (master)",
      "",
      "## 완료",
      "- 실기 확인을 마쳤어요",
      "",
      "## 진행 중",
      "- 다음 지시를 기다려요",
      `기록 ${top}`,
      "",
      "## [2026-11-23 05:38 DRAIN-VERIFY · 1.1.17 후보 설치(F) 중 재시작] 설치 중",
      "## 완료",
      "- F 설치 시작",
      "## 진행 중",
      "- F 설치",
      "기록 2026-11-23 05:38",
      "",
      "## [2026-11-22 11:04 DRAIN-VERIFY · 재시작 대기] 복원 뒤 대기 중",
      "## 완료",
      "- 옛 11-22 일",
      "## 진행 중",
      "- 재시작 대기",
      "기록 2026-11-22 11:04",
    ].join("\n");
  const cwdNoHeads = "# S\n- 재시작 저장 메모 2026-11-23 05:38\n";
  it("관찰 시점(05:56 · 맨 위 기록 줄이 아직 11-22 11:04): 카드 = 맨 위 3절만 · 시각 11-22 11:04 · 아래 05:38 절 때문에 알림 한 줄", () => {
    const now = "2026-11-23 05:56";
    const found = [
      { path: "canon", text: win("2026-11-22 11:04") },
      { path: "cwd", text: cwdNoHeads },
    ];
    const text = pickBriefText(found, now);
    expect(text).toBe(found[0].text);
    const s = parseBriefSections(text as string);
    expect(s.done).toEqual(["실기 확인을 마쳤어요"]); // 종전 = 「F 설치 시작」「옛 11-22 일」까지 섞임
    expect(s.doing).toEqual(["다음 지시를 기다려요"]);
    expect(recordedAt(text as string, now)).toBe("2026-11-22 11:04"); // 종전 = 아래 절 기록 줄(05:38)을 3절 기록으로 잘못 씀
    expect(briefNewerElsewhere(found, text, now)).toBe(true);
  });
  it("06:01 맨 위 3절을 새로 씀: 맨 위 3절 · 시각 06:01 · 알림 없음", () => {
    const now = "2026-11-23 06:10";
    const found = [{ path: "canon", text: win("2026-11-23 06:01") }];
    const text = pickBriefText(found, now) as string;
    expect(parseBriefSections(text).done).toEqual(["실기 확인을 마쳤어요"]);
    expect(recordedAt(text, now)).toBe("2026-11-23 06:01");
    expect(briefNewerElsewhere(found, text, now)).toBe(false);
  });
  it("같은 파일의 기계용 절(오너 지시 대장)만 늦어도 알림 — 고르기·카드 시각은 그대로(판정 B 계약)", () => {
    const f = "## 완료\n- a\n기록 2026-09-24 10:00\n\n## 오너 지시 대장\n| 2026-09-24 15:00 | 배포 준비 | 진행 |";
    expect(recordedAt(f, "2026-09-24 16:00")).toBe("2026-09-24 10:00");
    expect(briefNewerElsewhere([{ path: "c", text: f }], f, "2026-09-24 16:00")).toBe(true);
  });
});
