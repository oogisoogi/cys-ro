// (cysr-1119-s16 · TICKET=cysr-1119-s16) OB-O4 결과 카드 정리 — DESIGN §11-4 합격 = 숨김 · 7일 · 모두 치우기 · 파일 삭제 0.
// 「치우기」 = 목록에서만 숨김(파일 무변경) · 파일이 없어진 카드 = 없음을 처음 본 뒤 7일이면 자동 숨김 · 「모두 치우기」 = 보이는 카드 전부(확인 1회는 화면 몫).
import { describe, expect, it } from "bun:test";
import {
  addCandidates,
  expireMissing,
  hideAll,
  hideResult,
  MISSING_HIDE_MS,
  persistable,
  restoreResults,
  resultsLabel,
  visibleResults,
  withPresence,
  type Result,
} from "./judge/results";
import { ResultBook, RESULTS_KEY } from "./results";

const H = "/Users/user";
const DAY = 24 * 3600 * 1000;

function seeded(n = 2): Result[] {
  let list: Result[] = [];
  for (let i = 0; i < n; i++) list = addCandidates(list, [{ path: `${H}/교회/r${i}.pdf`, source: "reply", uuid: `m${i}`, runId: null }], 1000 + i);
  return list.map((r) => ({ ...r, exists: true, isDir: false }));
}

describe("OB-O4 — 순수 판정", () => {
  it("새 카드 = 숨김 아님 · 없어진 시각 없음", () => {
    const [r] = addCandidates([], [{ path: `${H}/a.html`, source: "reply", uuid: "m", runId: null }], 5);
    expect([r.hidden, r.missingAt]).toEqual([false, null]);
  });
  it("치우기 = 그 카드만 숨김 · 보이는 셈에서 빠짐 · 같은 경로를 다시 말해도 숨김 그대로", () => {
    const list = seeded(2);
    const id = list[0].id;
    const after = hideResult(list, id);
    expect(visibleResults(after).map((r) => r.id)).toEqual([list[1].id]);
    expect(resultsLabel(after).count).toBe(1);
    const again = addCandidates(after, [{ path: id, source: "reply", uuid: "m9", runId: null }], 9999);
    expect(again.find((r) => r.id === id)?.hidden).toBe(true);
    expect(visibleResults(again).length).toBe(1);
  });
  it("모두 치우기 = 보이는 카드 전부 숨김 · 아직 확인 중(안 보이는) 후보는 건드리지 않음", () => {
    let list = seeded(3);
    list = addCandidates(list, [{ path: `${H}/아직.pdf`, source: "reply", uuid: "mx", runId: null }], 2000); // exists null = 안 보임
    const after = hideAll(list);
    expect(visibleResults(after)).toEqual([]);
    expect(after.find((r) => r.name === "아직.pdf")?.hidden).toBe(false);
    expect(after.filter((r) => r.hidden).length).toBe(3);
  });
  it("없어짐을 처음 본 시각 기록 · 다시 있으면 지움 · 계속 없으면 처음 시각 유지", () => {
    const [r] = seeded(1);
    const gone = withPresence(r, false, null, 100);
    expect(gone.missingAt).toBe(100);
    expect(withPresence(gone, false, null, 500).missingAt).toBe(100);
    expect(withPresence(gone, true, false, 600).missingAt).toBe(null);
  });
  it("7일 — 6일 23시간 = 보임 · 7일 = 숨김 · 파일이 있는 카드·모름(재확인 전) = 시각이 있어도 숨기지 않음", () => {
    const [r] = seeded(1);
    const gone = withPresence(r, false, null, 0);
    expect(MISSING_HIDE_MS).toBe(7 * DAY);
    expect(expireMissing([gone], 7 * DAY - 3600 * 1000)[0].hidden).toBe(false);
    expect(expireMissing([gone], 7 * DAY)[0].hidden).toBe(true);
    expect(expireMissing([{ ...gone, exists: null }], 30 * DAY)[0].hidden).toBe(false);
    expect(expireMissing([{ ...gone, exists: true }], 30 * DAY)[0].hidden).toBe(false);
    const same = [withPresence(r, true, false, 0)];
    expect(expireMissing(same, 30 * DAY)).toBe(same); // 바뀐 것 없으면 같은 목록(다시 저장·다시 그리기 0)
  });
  it("저장 왕복 — 숨김·없어진 시각 보존 · 숨긴 답 경로는 재확인 전에도 저장(다시 말해도 되살아나지 않게) · 옛 꼴(두 칸 없음) = 숨김 아님", () => {
    const list = hideResult(seeded(2), `${H}/교회/r0.pdf`).map((x) => ({ ...x, exists: null as boolean | null, missingAt: x.name === "r1.pdf" ? 77 : null }));
    const back = restoreResults(persistable(list));
    // r1 = 봤음 아님·실재 모름·숨김 아님 → 저장 대상 밖(1.1.18 규칙 그대로) · r0 = 숨김 → 저장
    expect(back.map((r) => [r.name, r.hidden, r.missingAt])).toEqual([["r0.pdf", true, null]]);
    const kept = restoreResults(persistable(list.map((x) => ({ ...x, seen: true }))));
    expect(kept.map((r) => [r.name, r.hidden, r.missingAt])).toEqual([
      ["r1.pdf", false, 77],
      ["r0.pdf", true, null],
    ]);
    const old = restoreResults(JSON.stringify({ v: 1, items: [{ path: `${H}/a.pdf`, source: "reply", at: 1, uuid: null, runId: null, seen: true }] }));
    expect([old[0].hidden, old[0].missingAt]).toEqual([false, null]);
  });
});

function fakeBook(files: Record<string, { name: string; is_dir: boolean }[]>, t0 = 0) {
  const calls: string[] = [];
  const mem = new Map<string, string>();
  let now = t0;
  const invoke = async (cmd: string, a?: Record<string, unknown>) => {
    calls.push(cmd);
    if (cmd === "home_dir_path") return H;
    if (cmd === "list_dir") {
      const p = String(a?.path);
      if (p in files) return files[p];
      throw new Error("No such file or directory (os error 2)");
    }
    if (cmd === "result_open") return null;
    throw new Error(`unexpected ${cmd}`);
  };
  let changes = 0;
  const book = new ResultBook({ invoke, now: () => now, store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v) } }, () => changes++);
  return { book, calls, mem, files, setNow: (v: number) => void (now = v), changes: () => changes };
}
const rec = (text: string, uuid: string) => ({ uuid, parent: null, role: "assistant" as const, text, ts: null });
const flush = () => new Promise((r) => setTimeout(r, 0));

describe("OB-O4 — 장부(대역) · 파일 삭제 0", () => {
  it("치우기·모두 치우기 = invoke 호출 0(파일 명령 0) · 저장소에 숨김 반영 · 다시 켜도 숨김", async () => {
    const t = fakeBook({ [`${H}/교회`]: [{ name: "a.html", is_dir: false }, { name: "b.pdf", is_dir: false }, { name: "c.png", is_dir: false }] });
    await t.book.start();
    t.book.onTail([rec(`됐어요 ${H}/교회/a.html ${H}/교회/b.pdf ${H}/교회/c.png`, "m1")]);
    await flush();
    await t.book.tick();
    expect(visibleResults(t.book.items).length).toBe(3);
    const before = t.calls.length;
    const ch = t.changes();
    t.book.hide(`${H}/교회/a.html`);
    expect(t.changes()).toBe(ch + 1);
    expect(visibleResults(t.book.items).length).toBe(2);
    t.book.hideAll();
    expect(visibleResults(t.book.items).length).toBe(0);
    expect(t.calls.slice(before)).toEqual([]); // 파일 명령(result_open·삭제 류) 0 · list_dir 도 0
    const again = new ResultBook({ invoke: async () => H, now: () => 1, store: { get: (k) => t.mem.get(k) ?? null, set: () => {} } }, () => {});
    expect(again.items.length).toBe(3);
    expect(again.items.every((r) => r.hidden)).toBe(true);
    expect(JSON.parse(t.mem.get(RESULTS_KEY) ?? "{}").items.length).toBe(3);
  });
  it("숨긴 카드는 실재 확인(list_dir)을 하지 않음", async () => {
    const t = fakeBook({ [`${H}/교회`]: [{ name: "a.html", is_dir: false }] });
    await t.book.start();
    t.book.onTail([rec(`${H}/교회/a.html`, "m1")]);
    await flush();
    await t.book.tick();
    t.book.hide(`${H}/교회/a.html`);
    // 다시 켬 = 실재 모름(null) → 숨김이면 확인 0
    const again = fakeBook(t.files);
    for (const [k, v] of t.mem) again.mem.set(k, v);
    const b2 = new ResultBook({ invoke: async (c, a) => (again.calls.push(c), c === "home_dir_path" ? H : t.files[String(a?.path)]), now: () => 1, store: { get: (k) => again.mem.get(k) ?? null, set: (k, v) => void again.mem.set(k, v) } }, () => {});
    await b2.start();
    await b2.tick();
    expect(again.calls.filter((c) => c === "list_dir")).toEqual([]);
  });
  it("파일이 없어지면 그 시각을 적고 7일 뒤 틱에서 자동 숨김 · 그 전엔 「찾을 수 없어요」 카드로 보임 · 파일 무변경", async () => {
    const t = fakeBook({ [`${H}/교회`]: [{ name: "a.html", is_dir: false }] }, 1000);
    await t.book.start();
    t.book.onTail([rec(`${H}/교회/a.html`, "m1")]);
    await flush();
    await t.book.tick();
    const id = `${H}/교회/a.html`;
    await t.book.act(id, "open"); // 봤음(seen) 만들기
    t.files[`${H}/교회`] = [];
    await t.book.check(id);
    const r = t.book.items.find((x) => x.id === id)!;
    expect([r.exists, r.missingAt, r.seen]).toEqual([false, 1000, true]);
    expect(visibleResults(t.book.items).map((x) => x.id)).toEqual([id]);
    t.setNow(1000 + 7 * DAY - 1);
    await t.book.tick();
    expect(t.book.items.find((x) => x.id === id)?.hidden).toBe(false);
    t.setNow(1000 + 7 * DAY);
    const n0 = t.calls.filter((c) => c !== "list_dir" && c !== "home_dir_path" && c !== "result_open").length;
    await t.book.tick();
    expect(t.book.items.find((x) => x.id === id)?.hidden).toBe(true);
    expect(t.calls.filter((c) => c !== "list_dir" && c !== "home_dir_path" && c !== "result_open").length).toBe(n0);
  });
});
