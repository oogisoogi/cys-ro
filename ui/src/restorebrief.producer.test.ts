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
      expect(s[k].length <= BRIEF_MAX_ITEMS).toBe(true);
      for (const l of s[k]) {
        expect([...l].length <= BRIEF_MAX_CHARS).toBe(true);
        expect(l.endsWith("…")).toBe(false); // 예시가 잘리면 마스터도 잘리는 줄을 쓴다
      }
    }
    expect(/^20\d{2}-\d{2}-\d{2} \d{2}:\d{2}$/.test(recordedAt(example) ?? "")).toBe(true);
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
    expect(guide === undefined).toBe(false);
    expect(/완료/.test(guide ?? "") && /진행\s*중/.test(guide ?? "")).toBe(true);
  });
});

// ★(판정 B · master#88e8cb7b) 카드 기록 시각 = 3절을 쓴 시각. 종전 규칙(파일 전체 최댓값)은 마스터가 기계용 절에만
//   새 시각을 적으면(오너 지시 대장 한 줄 등) 낡은 3절에 새 시각을 붙였다 — 거짓 신선도.
describe("판정 B — 기록 시각은 3절 안의 `기록 YYYY-MM-DD HH:MM` 줄이 먼저", () => {
  const STALE = [
    "# SESSION_STATE.md",
    "## 완료",
    "- 로그인 화면 오류를 고쳤습니다",
    "## 진행 중",
    "- 결제 화면을 만들고 있습니다",
    "## 결정 필요",
    "- 새 버전을 오늘 내보낼지 정해 주세요",
    "기록 2026-09-24 10:00",
    "",
    "## 오너 지시 대장",
    "| 시각 | 지시 | 상태 |",
    "|---|---|---|",
    "| 2026-09-24 15:00 | 배포 준비 | 진행 |",
  ].join("\n");
  it("★재현: 기계용 절에만 더 늦은 시각이 있어도 카드 시각은 3절의 기록 줄(10:00)", () => {
    expect(recordedAt(STALE)).toBe("2026-09-24 10:00");
    expect(recordedAt(STALE, "2026-09-24 16:00")).toBe("2026-09-24 10:00");
  });
  it("기록 줄이 없으면 종전 규칙(파일 전체 최댓값) 그대로", () => {
    const noRec = STALE.replace("기록 2026-09-24 10:00", "");
    expect(recordedAt(noRec)).toBe("2026-09-24 15:00");
  });
  it("3절 밖(기계용 절 아래)의 「기록 …」 줄은 기록 줄로 치지 않는다", () => {
    const outside = STALE.replace("기록 2026-09-24 10:00", "") + "\n## 커밋 체인\n기록 2026-09-24 09:00";
    expect(recordedAt(outside)).toBe("2026-09-24 15:00");
  });
  it("기록 줄이 지금보다 늦으면(예정·오기) 믿지 않고 종전 규칙으로", () => {
    const future = STALE.replace("기록 2026-09-24 10:00", "기록 2026-10-01 09:00");
    expect(recordedAt(future, "2026-09-24 16:00")).toBe("2026-09-24 15:00");
  });
  it("「기록:」·T 구분자도 기록 줄이다(지침 예시와 같은 뜻의 흔한 변형)", () => {
    expect(recordedAt(STALE.replace("기록 2026-09-24 10:00", "기록: 2026-09-24T10:00"))).toBe("2026-09-24 10:00");
  });
  it("카드 고르기도 같은 시각으로 — 낡은 정본(기록 10:00 · 대장 15:00)보다 12:00 에 3절을 쓴 쪽이 이긴다", () => {
    const cwd = "## 진행 중\n- 드레인 저장분\n기록 2026-09-24 12:00";
    expect(pickBriefText([{ path: "c", text: STALE }, { path: "d", text: cwd }], "2026-09-24 16:00")).toBe(cwd);
  });
  it("지침 예시 블록의 기록 줄이 이 규칙으로 읽힌다(생산자↔소비자 계약)", () => {
    const ex = fencedBlocks(section9(MASTER)).find((b) => hasBriefSections(b)) ?? "";
    const m = ex.match(/^기록 (20\d{2}-\d{2}-\d{2} \d{2}:\d{2})$/m);
    expect(m).not.toBeNull();
    expect(recordedAt(writtenPerDirective(ex) + "\n| 2099-01-01 00:00 | x | y |", "2098-12-31 00:00")).toBe(m?.[1] ?? "");
  });
});

// ★(실증 · ⓔ 효과 실측 run B 15:2x) 새 세션(startup)은 §9 원문이 아니라 CORE 요지만 본다. 요지에 기록 줄·5줄·80자가
//   없자 실제 클로드가 `기록` 줄 없이 3절을 썼다 → 판정 B 의 거짓 신선도 방어가 새 세션에서만 빠졌다.
describe("CORE 요지(새 세션이 보는 유일한 문안)도 3절 서식의 핵심을 말한다", () => {
  for (const f of ["MASTER_CORE.md", "CEO_CORE.md"]) {
    const line = read(`../../cysjavis-pack/directives/${f}`).split("\n").find((l) => l.startsWith("- 영속(§9):")) ?? "";
    it(`${f} §9 요지: 3절 제목 · 기록 줄 · 5줄 · 80자`, () => {
      for (const h of ["## 완료", "## 진행 중", "## 결정 필요"]) expect(line.includes(h)).toBe(true);
      expect(line.includes("기록 YYYY-MM-DD HH:MM")).toBe(true);
      expect(/5줄/.test(line) && /80자/.test(line)).toBe(true);
    });
  }
});

// ★(Opus 적대 1R 발견 1 · P2 · 재현 입력 그대로) 판정 B 뒤 두 파일을 서로 다른 잣대로 쟀다 — 기록 줄 있는 파일은 3절을
//   쓴 시각, 없는 파일은 파일 전체 최댓값(거짓 신선도 그 값). 그래서 옛 3절 파일이 대장 한 줄 덕에 이겼다.
//   규칙: 3절 시각을 아는 파일(유효한 기록 줄)이 먼저 · 그 안에서 늦은 것 · 둘 다 모르면 종전 규칙.
describe("판정 B 후속 — 파일 고르기는 같은 잣대로(기록 줄 있는 파일 먼저)", () => {
  const NOW = "2026-09-24 16:00";
  const CANON = "# S\n## 완료\n- 새 것: 로그인 오류 수정\n## 진행 중\n- 새 것: 결제 화면\n## 결정 필요\n기록 2026-09-24 10:00\n\n## 오너 지시 대장\n| 2026-09-24 15:00 | 배포 준비 | 진행 |";
  const CWD_OLD = "# S\n## 완료\n- 옛 것\n## 진행 중\n- 옛 것\n## 결정 필요\n\n## 오너 지시 대장\n| 2026-09-24 09:00 | 옛 지시 | 완료 |\n| 2026-09-24 12:00 | 옛 지시 2 | 완료 |";
  it("★재현: 기록 줄 있는 정본(3절 10:00 · 대장 15:00) vs 기록 줄 없는 cwd(대장 12:00) → 정본", () => {
    expect(pickBriefText([{ path: "c", text: CANON }, { path: "d", text: CWD_OLD }], NOW)).toBe(CANON);
    expect(pickBriefText([{ path: "d", text: CWD_OLD }, { path: "c", text: CANON }], NOW)).toBe(CANON); // 순서 무관
  });
  it("반대 방향: 기록 줄 없는 정본(대장 15:00) vs 기록 줄 있는 cwd(12:00) → cwd(3절 시각을 아는 쪽)", () => {
    const canonNoRec = CANON.replace("기록 2026-09-24 10:00", "");
    const cwdRec = "## 진행 중\n- 드레인 저장분\n기록 2026-09-24 12:00";
    expect(pickBriefText([{ path: "c", text: canonNoRec }, { path: "d", text: cwdRec }], NOW)).toBe(cwdRec);
  });
  it("미래 기록 줄은 모르는 것으로 친다(기록 줄 없는 파일과 같은 줄에 선다)", () => {
    // 미래 기록 줄 파일은 「모름」 줄에서 종전 규칙 11:00 · CWD_OLD 는 같은 줄에서 12:00 → CWD_OLD(미래 줄을 「안다」로 치면 거꾸로 된다)
    const futureRec = "## 완료\n- 미래 줄\n기록 2026-10-01 09:00\n| 2026-09-24 11:00 |";
    expect(pickBriefText([{ path: "c", text: futureRec }, { path: "d", text: CWD_OLD }], NOW)).toBe(CWD_OLD);
  });
});

// ★(agy 2R 발견 1·2 · Opus 적대 1R 기록만 2a·2b 와 같은 자리 — 두 검토자 · 재현 입력 그대로)
//   ⑴ 기록 줄을 목록으로 쓰면(`- 기록 …`) 기록 줄로 못 읽고 카드 항목으로 샜다 ⑵ 기록 줄이 여럿이면 첫 줄(옛 시각)이 이겼다.
describe("판정 B 후속 2 — 기록 줄의 흔한 변형", () => {
  const NOW = "2026-09-24 16:00";
  it("★⑴ `- 기록 …` 도 기록 줄이다(파일 고르기 · 시각) — 그리고 카드 항목으로 새지 않는다", () => {
    const NEW_CANON = "## 완료\n- 새 작업\n- 기록 2026-09-24 15:40\n| 2026-09-24 09:00 |";
    const OLD_CWD = "## 완료\n- 옛 작업\n기록 2026-09-24 10:00";
    expect(pickBriefText([{ path: "c", text: NEW_CANON }, { path: "d", text: OLD_CWD }], NOW)).toBe(NEW_CANON);
    expect(recordedAt(NEW_CANON, NOW)).toBe("2026-09-24 15:40");
    expect(parseBriefSections("## 결정 필요\n- c\n- 기록 2026-09-24 14:30\n").decide).toEqual(["c"]);
  });
  it("★⑵ 기록 줄이 여럿이면 가장 늦은 유효한 줄(지금보다 늦은 줄은 뺀다)", () => {
    const FRESH = "## 완료\n- 옛 작업\n기록 2026-09-24 10:00\n## 결정 필요\n- 새 작업\n기록 2026-09-24 15:40";
    const OLD_CWD = "## 완료\n- 다른 작업\n기록 2026-09-24 11:00";
    expect(pickBriefText([{ path: "c", text: FRESH }, { path: "d", text: OLD_CWD }], NOW)).toBe(FRESH);
    expect(recordedAt(FRESH, NOW)).toBe("2026-09-24 15:40");
    expect(recordedAt(FRESH + "\n기록 2026-10-01 09:00", NOW)).toBe("2026-09-24 15:40");
    // 순서가 아니라 시각이다 — 늦은 줄이 먼저 오고 옛 줄이 뒤에 남아도 늦은 줄
    expect(recordedAt("## 결정 필요\n- a\n기록 2026-09-24 15:40\n## 완료\n- b\n기록 2026-09-24 10:00", NOW)).toBe("2026-09-24 15:40");
  });
  it("「기록」으로 시작하지만 시각이 없는 보통 항목은 그대로 항목이다", () => {
    expect(parseBriefSections("## 완료\n- 기록 화면을 고쳤습니다\n").done).toEqual(["기록 화면을 고쳤습니다"]);
  });
});

// ★(agy 3R 발견 1·2·3 · 재현 입력 그대로) 기록 줄 판정이 목록 판정과 엇갈렸다 —
//   ⑴ 시각 뒤에 말이 이어지는 진짜 할 일(`- 기록 … 14:30 에 배포 완료`)을 기록 줄로 삼켰다 ⑵ 1칸 들여쓴 `- 기록 …`(카드는 목록으로
//   셈)을 기록 줄로 못 읽고 항목으로 흘렸다 ⑶ 번호 목록(`1. 기록 …`)도 같다.
describe("판정 B 후속 3 — 기록 줄 판정 = 줄 전체가 기록 시각뿐 · 목록 판정과 같은 표지", () => {
  it("★⑴ 시각 뒤에 말이 이어지면 기록 줄이 아니라 할 일이다", () => {
    const f = "## 완료\n- 기록 2026-09-24 14:30 에 배포 완료\n| 2026-09-24 09:00 |";
    expect(parseBriefSections(f).done).toEqual(["기록 2026-09-24 14:30 에 배포 완료"]);
    expect(recordedAt(f)).toBe("2026-09-24 14:30"); // 기록 줄이 없으니 종전 규칙(파일 최댓값) — 우연히 같은 값
    expect(pickBriefText([{ path: "c", text: f }, { path: "d", text: "## 완료\n- x\n기록 2026-09-24 10:00" }])).toBe(
      "## 완료\n- x\n기록 2026-09-24 10:00",
    ); // 기록 줄 없는 쪽은 「모름」 줄
  });
  it("★⑵ 1칸 들여쓴 `- 기록 …` 도 기록 줄(카드가 목록으로 세는 들여쓰기와 같게)", () => {
    const f = "## 완료\n - 기록 2026-09-24 14:30\n| 2026-09-24 15:00 |";
    expect(parseBriefSections(f).done).toEqual([]);
    expect(recordedAt(f)).toBe("2026-09-24 14:30");
  });
  it("★⑶ 번호 목록 `1. 기록 …` · `1) 기록 …` 도 기록 줄", () => {
    for (const mark of ["1.", "1)"]) {
      const f = `## 결정 필요\n- 정해 주세요\n${mark} 기록 2026-09-24 14:30\n| 2026-09-24 15:00 |`;
      expect(parseBriefSections(f).decide).toEqual(["정해 주세요"]);
      expect(recordedAt(f)).toBe("2026-09-24 14:30");
    }
  });
  it("초·꼬리 공백은 기록 줄 그대로(지침 `date` 출력과 흔한 변형)", () => {
    expect(recordedAt("## 완료\n- a\n기록 2026-09-24 14:30:59  \n| 2026-09-24 15:00 |")).toBe("2026-09-24 14:30");
  });
});
