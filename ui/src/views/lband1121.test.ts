// (TICKET=cysr-1121-ui L) 확인 띠 좁히기 — 🗣박사님 11-26 「"확인이 필요해요" 창은 일반 사용자들은 무엇인지 모른다. 괜히 무엇을 해야 하나 긴장하게 된다.」
//   → master 권고 「좁히기(없애지 않음)」 ✅박사님 「권고안대로」 · ㉡ 은 적대 1R 뒤 master 결정(11:0x) = 단순안(시한·깨움 없음 · 「안 누르셔도 돼요 · 하지 않고 기다려요」).
//   설계 = workers/cysr-1121-ui/L-DESIGN.md · 검토 = review/L-codex-r1.json.
// 대조군 = fafe3eee1(v1.1.20): bandNeed·ASK_WAIT_NOTE 없음 · 머리 = 「확인이 필요해요 N」 · 차례 = 물음 먼저 → 아래 붉음.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import { ASK_WAIT_NOTE, bandLabel, bandNeed, bandOf, type Band, type BandItem, type FeedApproval, type StallInput } from "./judge/confirms";
import { pickWorkBand } from "./judge/workband";

const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
const appr = (o: Partial<FeedApproval> = {}): FeedApproval => ({ request_id: "r1", surface_id: 9, created_at: 100, body: "b", screen: true, fingerprint: "f", excerpt: "", command: "", readonly: null, ...o }) as FeedApproval;
const ask = (id: string): BandItem => ({ kind: "ask", key: id, q: { id, text: `물음 ${id}`, uuid: null } });
const helper = (stall: "deadman" | null, id = "h"): BandItem => ({ kind: "helper", key: id, a: appr({ request_id: id }), stall } as BandItem);
const screen = (id = "s"): BandItem => ({ kind: "master_screen", key: id, a: appr({ request_id: id, surface_id: 5 }) });
const band = (items: BandItem[], known = true): Band => ({ known, items });

describe("L ㉢ 갈래 — 사람이 무엇을 해야 하나", () => {
  it("마스터 창 승인·멈춤으로 열린 도우미 허락 = 직접 답하실 것 · 표식 = 마스터 물음 · 평소 도우미 허락 = 마스터가 확인하는 중", () => {
    expect(bandNeed(screen())).toBe("act");
    expect(bandNeed(helper("deadman"))).toBe("act");
    expect(bandNeed(ask("q1"))).toBe("ask");
    expect(bandNeed(helper(null))).toBe("watch");
  });
  it("머리 글 — 갈래별 수 · 0 인 갈래는 뺌 · 다 못 훑었으면 「더 살펴보는 중」 · 0건 확정 = 숨김", () => {
    expect(bandLabel(band([]))).toBeNull();
    expect(bandLabel(band([], false))).toBe("확인할 것 살펴보는 중");
    expect(bandLabel(band([ask("q1")]))).toBe("마스터 물음 1");
    expect(bandLabel(band([helper(null), helper(null, "h2")]))).toBe("마스터가 확인하는 중 2");
    expect(bandLabel(band([screen(), ask("q1"), helper(null)]))).toBe("직접 답하실 것 1 · 마스터 물음 1 · 마스터가 확인하는 중 1");
    expect(bandLabel(band([helper(null)], false))).toBe("마스터가 확인하는 중 1 · 더 살펴보는 중");
    expect(bandLabel(band([screen()]))).toBe("직접 답하실 것 1");
  });
  it("차례 — 직접 답하실 것 → 마스터 물음 → 확인하는 중(같은 갈래는 종전 차례)", () => {
    const st: StallInput = { now: 1_000_000, masterSid: 5, masterAlive: true, masterIdleSecs: 1, deadman: null, absentSince: 0, stalledIds: new Set() } as StallInput;
    const b = bandOf([{ id: "q1", text: "물음", uuid: null }], [appr({ request_id: "h1", surface_id: 9 }), appr({ request_id: "m1", surface_id: 5 })], st);
    expect(b.items.map((x) => x.kind)).toEqual(["master_screen", "ask", "helper"]);
  });
  it("작업 화면 띠도 같은 머리 글(두 화면이 다르게 말하지 않음)", () => {
    const b = band([ask("q1")]);
    const w = pickWorkBand(b, "", 5);
    expect(w?.kind === "confirm" && w.text.startsWith(`${bandLabel(b)} — 마스터가 물어요:`)).toBe(true);
    const WB = strip(readFileSync(new URL("./judge/workband.ts", import.meta.url), "utf8"));
    expect(WB).not.toContain("확인이 필요해요");
  });
});

describe("L ㉡ 단순안 — 안 눌러도 되는 까닭을 띠에 적음(시한·자동 결정 없음)", () => {
  it("물음 항목에 한 줄 · 위협 낱말 없음", () => {
    expect(ASK_WAIT_NOTE).toBe("안 누르셔도 돼요 · 답을 주실 때까지 마스터는 이 일을 하지 않고 기다려요.");
    for (const w of ["분 뒤", "자동", "경고", "위험", "지금 바로"]) expect(ASK_WAIT_NOTE).not.toContain(w);
    const BAND = strip(readFileSync(new URL("./chat/band.ts", import.meta.url), "utf8"));
    expect(BAND).toMatch(/if \(it\.kind === "ask"\) \{\s*box\.append\(el\("div", "cvb-text", `마스터가 물어요: \$\{it\.q\.text\}`\)\);\s*box\.append\(el\("div", "cvb-wait", ASK_WAIT_NOTE\)\);/);
  });
  it("확인하는 중만 있으면 머리를 차분한 색으로(data-calm) · 그 밖은 주의 색", () => {
    const BAND = strip(readFileSync(new URL("./chat/band.ts", import.meta.url), "utf8"));
    expect(BAND).toContain('head.dataset.calm = String(b.known && b.items.length > 0 && b.items.every((x) => bandNeed(x) === "watch"));');
    const CSS = readFileSync(new URL("./views.css", import.meta.url), "utf8");
    expect(CSS).toContain('.cvb-head[data-calm="true"] { color: var(--cv-sub); }');
    expect(CSS).toContain(".cvb-wait {");
  });
});

describe("L ㉠ 지침 — 물음을 사용자만 정할 세 가지로 좁힘", () => {
  const MD = readFileSync(new URL("../../../cysjavis-pack/directives/MASTER_DIRECTIVE.md", import.meta.url), "utf8");
  const CEO = readFileSync(new URL("../../../cysjavis-pack/directives/CEO_TEMPLATE.md", import.meta.url), "utf8");
  const LINE = "- `⟪확인 요청: <한 줄 물음>⟫` — 돈·되돌릴 수 없는 바깥 일(공개·발송·삭제)·사용자 손(암호·2단계·기기)일 때만 — 그 밖은 마스터가 정해 알리고, 답이 없으면 하지 않고 기다린다.";
  it("MASTER·CEO 틀 모두 새 줄 · 옛 「사람의 결정·확인이 필요할 때」 0", () => {
    expect(MD).toContain(LINE);
    expect(CEO).toContain(LINE);
    expect(MD).not.toContain("사람의 결정·확인이 필요할 때");
    expect(CEO).not.toContain("사람의 결정·확인이 필요할 때");
  });
  it("해결 표식 규칙(앞 20자 · 띄어쓰기 그대로)은 뜻 그대로 남음", () => {
    expect(MD).toContain("- `⟪확인 해결: <같은 물음 앞 20자(띄어쓰기도 그대로)>⟫` — 그 물음이 끝났을 때(안 내면 띠가 남는다).");
  });
});
