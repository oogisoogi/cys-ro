// ★(v116-restore-card-producer · R1a 후반) 복원 카드의 **생산자 계약** — 지침이 시키는 대로 쓴 작업기억
// 파일을 카드가 실제로 채워 보여 주는가.
//
// 카드(restorebrief.ts)는 작업기억 파일의 고정 3절(완료 / 진행 중 / 결정 필요)만 읽는다. 그 3절을 쓰는 것은
// 마스터(LLM)이고, 마스터가 보는 것은 지침(MASTER_DIRECTIVE §9 · 부서 CEO 는 CEO_TEMPLATE)의 **예시 블록**이다.
// 그래서 이 시험은 예시 블록을 지침 파일에서 직접 뽑아 카드 파서에 넣는다 — 지침 문구·절 이름이 바뀌어
// 카드가 조용히 비는 일(생산자 0 = 효과 0 · 09-24 master 판정)을 적색으로 묶는다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import {
  parseBriefSections,
  recordedAt,
  pickBriefText,
  hasBriefSections,
  buildBriefCard,
  INTERNAL_TERMS,
  BRIEF_MAX_ITEMS,
  BRIEF_MAX_CHARS,
} from "./restorebrief";

const read = (rel: string) => readFileSync(new URL(rel, import.meta.url), "utf-8");

/** 지침 §9 절 본문(「## 9.」 제목부터 다음 「## 」 제목 전까지 · 코드 울타리 안 제목은 제목이 아니다 — core_inject 분할과 같은 규칙). */
function section9(directive: string): string {
  const lines = directive.split("\n");
  const a = lines.findIndex((l) => /^## 9\.\s/.test(l));
  if (a < 0) return "";
  let fence = false;
  let b = -1;
  for (let i = a + 1; i < lines.length; i++) {
    if (/^\s*(```|~~~)/.test(lines[i])) fence = !fence;
    else if (!fence && /^#{1,2}\s/.test(lines[i])) {
      b = i;
      break;
    }
  }
  return lines.slice(a, b < 0 ? undefined : b).join("\n");
}

/** §9 안의 코드 울타리 블록들(울타리 줄 제외 · 들여쓰기 그대로 = 마스터가 베껴 쓰는 모양 그대로). */
function fencedBlocks(sec: string): string[] {
  const out: string[] = [];
  let cur: string[] | null = null;
  for (const l of sec.split("\n")) {
    if (/^\s*(```|~~~)/.test(l)) {
      if (cur) {
        out.push(cur.join("\n"));
        cur = null;
      } else cur = [];
      continue;
    }
    if (cur) cur.push(l);
  }
  return out;
}

const MASTER = read("../../cysjavis-pack/directives/MASTER_DIRECTIVE.md");
const CEO = read("../../cysjavis-pack/directives/CEO_TEMPLATE.md");
const SKELETON = read("../../cysjavis-pack/round/SESSION_STATE.md");

/** 「지침대로 쓴 파일」 — 설치 골격의 제목 줄 바로 아래에 예시 블록을 넣는다(지침: 제목 바로 아래). */
function writtenPerDirective(example: string): string {
  const [title, ...rest] = SKELETON.split("\n");
  return [title, example, ...rest].join("\n");
}

describe("v116 R1a 생산자 — 지침 §9 의 3절 예시 블록이 카드를 채운다", () => {
  const blocks = fencedBlocks(section9(MASTER));
  const example = blocks.find((b) => hasBriefSections(b)) ?? "";

  it("§9 에 3절 예시 블록이 정확히 1개 있다(울타리 안 — 절 분할·해시를 흔들지 않게)", () => {
    expect(blocks.filter((b) => hasBriefSections(b)).length).toBe(1);
  });
  it("예시 블록을 그대로 파서에 넣으면 3절이 모두 채워진다", () => {
    const s = parseBriefSections(example);
    expect(s.done.length).toBeGreaterThan(0);
    expect(s.doing.length).toBeGreaterThan(0);
    expect(s.decide.length).toBeGreaterThan(0);
    for (const k of ["done", "doing", "decide"] as const) {
      expect(s[k].length).toBeLessThanOrEqual(BRIEF_MAX_ITEMS);
      for (const l of s[k]) {
        expect([...l].length).toBeLessThanOrEqual(BRIEF_MAX_CHARS);
        expect(l.endsWith("…")).toBe(false); // 예시가 잘리면 마스터도 잘리는 줄을 쓴다
      }
    }
    expect(recordedAt(example)).toMatch(/^20\d{2}-\d{2}-\d{2} \d{2}:\d{2}$/);
  });
  it("지침대로 쓴 파일(골격 제목 아래 + 기계용 절 그대로) → 카드가 고르고, 예시의 줄만 싣는다", () => {
    const file = writtenPerDirective(example);
    expect(pickBriefText([{ path: "canon", text: file }])).toBe(file);
    const s = parseBriefSections(file);
    expect(s).toEqual(parseBriefSections(example)); // 아래 기계용 절(현재 위치 · 다음 액션 큐 …)이 새지 않는다
    const card = buildBriefCard({ sections: s, recordedAt: recordedAt(file), restoredRoles: ["master"], waitingRoles: [] });
    expect(card.title).toBe("다시 켜졌어요 — 하던 일을 복원했어요");
    const all = JSON.stringify(card);
    expect(all.includes("적힌 것이 없습니다")).toBe(false);
    for (const t of INTERNAL_TERMS) expect(all.toLowerCase().includes(t.toLowerCase())).toBe(false);
  });
  it("부서 CEO 지침(CEO_TEMPLATE)도 같은 예시 블록을 싣는다(재합성 누락 차단)", () => {
    expect(fencedBlocks(section9(CEO)).find((b) => hasBriefSections(b))).toBe(example);
  });
  it("★S2 불변식: 설치 골격은 3절 제목 줄 0 · 서식 안내는 주석으로만 — 새 설치 첫 카드는 「다시 켜졌어요」", () => {
    expect(hasBriefSections(SKELETON)).toBe(false);
    const guide = [...SKELETON.matchAll(/<!--([\s\S]*?)-->/g)].map((m) => m[1]).find((c) => /결정\s*필요/.test(c));
    expect(guide).toBeDefined();
    expect(/완료/.test(guide ?? "") && /진행\s*중/.test(guide ?? "")).toBe(true);
  });
});
