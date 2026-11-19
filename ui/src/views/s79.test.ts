// (cysr-1116-s79 · TICKET=cysr-1116-s79-1119) 조각 7 결과 받기 · 조각 9 작업 화면 띠 · S4-7(F7 사람이 물음 내림 · F10 바뀌어 온 항목) — 순수 판정 + 장부 대역.
import { describe, expect, it } from "bun:test";
import { readFileSync } from "node:fs";
import {
  addCandidates,
  baseName,
  candidatesOf,
  kindOf,
  launchesProgram,
  OPEN_REFUSED_EXT,
  OPEN_ALLOWED_EXT,
  openAllowedName,
  listErrorIsMissing,
  missingPrefix,
  normPath,
  parentOf,
  PATHS_PER_REPLY_MAX,
  pathsInText,
  persistable,
  presenceIn,
  restoreResults,
  resultsLabel,
  RESULTS_MAX,
  revisePrefix,
  skillCandidateOf,
  visibleResults,
  withPrefix,
  type Result,
} from "./judge/results";
import { MSG_EXEC, MSG_MISSING, MSG_NETWORK, MSG_OUTSIDE, MSG_UNKNOWN, ResultBook, RESULTS_KEY } from "./results";
import { pickWorkBand, WORK_ANSWER_HELPER, WORK_ANSWER_MASTER, WORK_DRAFT_TEXT } from "./judge/workband";
import { bandOf, dismissKey, openQuestions, swapBlocked, SWAP_GUARD_MS, withoutDismissed, type Band, type FeedApproval, type StallInput } from "./judge/confirms";
import { ConfirmBook } from "./confirm";
import type { Rec } from "./judge/msgstep";
import { Sim } from "./testkit";

const H = "/Users/user";
const rec = (text: string, extra: Partial<Rec> = {}): Rec => ({ uuid: "u1", parent: null, role: "assistant", text, ts: null, ...extra });

describe("조각 7 — 답 속 경로(홈 아래만)", () => {
  it("홈 아래 절대 경로 · ~/ 펼침 · 끝 문장 부호·괄호·백틱 깎음 · 나온 순서", () => {
    const t = "다 만들었어요: /Users/user/교회/행사안내.html. 그리고 `~/교회/주보.pdf`(인쇄용)도 있어요.";
    expect(pathsInText(t, H)).toEqual(["/Users/user/교회/행사안내.html", "/Users/user/교회/주보.pdf"]);
  });
  it("홈 밖 · 홈 자신 · 숨은 폴더 · .. 마디 = 0", () => {
    const t = `/etc/hosts /Users/user /Users/user/.cys/pack/x.md /Users/user/a/../b.txt ${H}chi/x.txt /tmp/a.html`; // 홈 이웃 이름(userchi)은 실행 시 조립(개인 경로 검사 오탐 방지)
    expect(pathsInText(t, H)).toEqual([]);
  });
  it("코드 울타리 안 줄 = 0(명령 예시) · 울타리 밖은 받음", () => {
    const t = "```bash\nopen /Users/user/교회/a.html\n```\n결과: /Users/user/교회/b.html";
    expect(pathsInText(t, H)).toEqual(["/Users/user/교회/b.html"]);
  });
  it("확장자 바로 뒤 한글 조사·어미는 깎음 · 확장자 없는 폴더 이름은 그대로", () => {
    expect(pathsInText("파일은 /Users/user/교회/행사안내.html에 있고 /Users/user/교회/주보.pdf를 고쳤어요", H)).toEqual(["/Users/user/교회/행사안내.html", "/Users/user/교회/주보.pdf"]);
    expect(pathsInText("폴더 /Users/user/교회자료 를 보세요", H)).toEqual(["/Users/user/교회자료"]);
  });
  it("「열기」가 곧 실행인 꾸러미(.app 등) = 막음 · 문서·그림·폴더는 아님", () => {
    for (const n of ["Evil.app", "x.APP", "a.pkg", "b.mpkg", "run.command", "p.prefPane", "w.workflow"]) expect(`${n}:${launchesProgram(n)}`).toBe(`${n}:true`);
    // (codex 2R blocking · master#c48208b6 ②) URL·바로가기·스크립트 유형 — 양 OS 공통 · 대소문자 무시
    for (const n of ["a.webloc", "a.URL", "a.inetloc", "a.lnk", "a.sh", "a.tool", "a.terminal", "a.scpt", "a.applescript", "a.ps1", "a.bat", "a.cmd", "a.vbs", "a.js", "a.jse", "a.wsf", "a.hta", "a.reg", "a.msi", "a.scr", "a.Exe"])
      expect(`${n}:${launchesProgram(n)}`).toBe(`${n}:true`);
    for (const n of ["a.html", "주보.pdf", "out", "app", "a.application.md"]) expect(`${n}:${launchesProgram(n)}`).toBe(`${n}:false`);
  });
  it("띄어쓰기 있는 경로(codex 1R major): 백틱 안 통째 · 맨글은 확장자까지 이은 것도 후보", () => {
    expect(pathsInText("보고서는 `/Users/user/Report Final.pdf` 예요", H)).toEqual(["/Users/user/Report Final.pdf"]);
    // (codex 2R major · master#c48208b6 ④) 이은 전체 경로만 — 끊긴 앞 토막(/Users/user/Report) 단독 후보 금지
    expect(pathsInText("보고서는 /Users/user/Report Final.pdf 예요", H)).toEqual(["/Users/user/Report Final.pdf"]);
    expect(pathsInText("보고서는 /Users/user/Report Final Draft v2.pdf 예요", H)).toEqual(["/Users/user/Report Final Draft v2.pdf"]); // 낱말 3개까지 이음
    expect(pathsInText("보고서는 /Users/user/a b c d e.pdf 예요", H)).toEqual([]); // 4개 넘게 = 놓침(알려진 한계 · 앞 토막도 안 냄)
    expect(pathsInText("결과 /Users/user/교회 폴더를 보세요", H)).toEqual(["/Users/user/교회"]); // 이어도 확장자가 안 나오면 그대로
    expect(pathsInText("`ls -la` 와 `/etc/a b.txt`", H)).toEqual([]);
  });
  it("실재 대조 = 유니코드 정규화 무시(NFD 이름) · 맥·윈 대소문자 무시(codex 1R minor)", () => {
    const nfd = "주보.pdf".normalize("NFD");
    expect(presenceIn([{ name: nfd, is_dir: false }], "주보.pdf")?.exists).toBe(true);
    expect(presenceIn([{ name: "Report.PDF", is_dir: false }], "report.pdf")?.exists).toBe(false);
    expect(presenceIn([{ name: "Report.PDF", is_dir: false }], "report.pdf", true)?.exists).toBe(true);
  });
  it("열기 거절 확장자 = Rust viewcore OPEN_REFUSED_EXT 와 같은 목록(한 정의 · codex 2R)", () => {
    const rs = readFileSync(new URL("../../../src-tauri/src/viewcore.rs", import.meta.url), "utf8");
    const m = /pub\(crate\) const OPEN_REFUSED_EXT: &\[&str\] = &\[([\s\S]*?)\];/.exec(rs);
    expect(m).not.toBeNull();
    const rust = [...(m?.[1] ?? "").matchAll(/"([^"]+)"/g)].map((x) => x[1]);
    expect(rust.length).toBeGreaterThan(40);
    expect(rust).toEqual([...OPEN_REFUSED_EXT]);
    for (const e of rust) expect(e).toBe(e.toLowerCase());
  });
  it("열기 허용 목록 = Rust viewcore OPEN_ALLOWED_EXT 와 같은 목록(한 정의 · 독립 검증 V1·V2)", () => {
    const rs = readFileSync(new URL("../../../src-tauri/src/viewcore.rs", import.meta.url), "utf8");
    const m = /pub\(crate\) const OPEN_ALLOWED_EXT: &\[&str\] = &\[([\s\S]*?)\];/.exec(rs);
    expect(m).not.toBeNull();
    expect([...(m?.[1] ?? "").matchAll(/"([^"]+)"/g)].map((x) => x[1])).toEqual([...OPEN_ALLOWED_EXT]);
    for (const e of OPEN_ALLOWED_EXT) expect(OPEN_REFUSED_EXT.includes(e)).toBe(false); // 두 목록이 겹치지 않음
    // 화면 쪽 미리 거르기: 허용 = 문서·그림·페이지·폴더 · 거절 = 위치 파일·윈 목록 밖·실행형 · 확장자 없고 폴더 여부 모름 = Tauri 에 맡김
    for (const [n, d, want] of [["a.html", false, true], ["주보.PDF", null, true], ["out", true, true], ["X.app", true, false], ["p.fileloc", false, false], ["a.appref-ms", null, false], ["a.chm", false, false], ["a.py", false, false], ["주보 최종", null, true], ["주보 최종", false, false]] as const)
      expect(`${n}/${d}:${openAllowedName(n, d)}`).toBe(`${n}/${d}:${want}`);
  });
  it("URL·낱말 한가운데 슬래시 = 0", () => {
    expect(pathsInText("https://example.invalid/Users/user/a.html 와 and/or", H)).toEqual([]);
  });
  it("같은 경로는 한 번 · 상한", () => {
    const many = Array.from({ length: 9 }, (_, i) => `/Users/user/r/${i}.md`).join(" ");
    expect(pathsInText(`${many} /Users/user/r/0.md`, H).length).toBe(PATHS_PER_REPLY_MAX);
    expect(pathsInText("/Users/user/a.md /Users/user/a.md/", H)).toEqual(["/Users/user/a.md"]);
  });
  it("윈도우 홈: \\ · / 둘 다 · 대소문자 무시 · 구분자는 홈의 것으로", () => {
    const W = "C:\\Users\\user";
    expect(pathsInText("결과 c:\\users\\user\\Docs\\a.html 와 C:/Users/user/b.pdf", W)).toEqual(["C:\\Users\\user\\Docs\\a.html", "C:\\Users\\user\\b.pdf"]);
    expect(normPath(`${W}chi\\a.txt`, W)).toBeNull();
    expect(normPath("~\\x\\y.md", W)).toBe("C:\\Users\\user\\x\\y.md");
  });
  it("user·곁가지·글 없는 레코드 = 후보 0 · assistant = 후보(uuid 실림)", () => {
    expect(candidatesOf(rec("/Users/user/a.html", { role: "user" }), H)).toEqual([]);
    expect(candidatesOf(rec("/Users/user/a.html", { sidechain: true }), H)).toEqual([]);
    expect(candidatesOf(rec("", { text: null }), H)).toEqual([]);
    expect(candidatesOf(rec("/Users/user/a.html", { uuid: "m9" }), H)).toEqual([{ path: "/Users/user/a.html", source: "reply", uuid: "m9", runId: null }]);
  });
  it("이름·부모·종류", () => {
    expect(baseName("/Users/user/a/b.html")).toBe("b.html");
    expect(parentOf("/Users/user/a/b.html")).toBe("/Users/user/a");
    expect(parentOf("C:\\Users\\user\\b.pdf")).toBe("C:\\Users\\user");
    expect(kindOf("b.html", null)).toBe("page");
    expect(kindOf("b.PDF", false)).toBe("doc");
    expect(kindOf("b.png", null)).toBe("image");
    expect(kindOf("out", true)).toBe("folder");
    expect(kindOf("out", null)).toBe("folder");
    expect(kindOf("run.bin", false)).toBe("file");
  });
});

describe("조각 7 — 스킬 산출 폴더(skill.run_finished)", () => {
  it("done + 홈 아래 폴더만", () => {
    expect(skillCandidateOf({ run_id: "r1", status: "done", artifact_dir: "/Users/user/cys-skill-runs/r1" }, H)).toEqual({ path: "/Users/user/cys-skill-runs/r1", source: "skill", uuid: null, runId: "r1" });
    expect(skillCandidateOf({ run_id: "r1", status: "failed", artifact_dir: "/Users/user/x" }, H)).toBeNull();
    expect(skillCandidateOf({ run_id: "r1", status: "done", artifact_dir: null }, H)).toBeNull();
    expect(skillCandidateOf({ run_id: "r1", status: "done", artifact_dir: "/var/tmp/x" }, H)).toBeNull();
    expect(skillCandidateOf(null, H)).toBeNull();
  });
});

describe("조각 7 — 목록 · 보임 · 새 결과 · 저장(원문 0자)", () => {
  const c = (path: string, source: "skill" | "reply" = "reply") => ({ path, source, uuid: source === "reply" ? "u" : null, runId: source === "skill" ? "r" : null });
  it("같은 경로 한 카드 · 스킬 출처로 올림 · 최근 것부터 · 상한", () => {
    let l = addCandidates([], [c("/Users/user/a")], 1);
    l = addCandidates(l, [c("/Users/user/a", "skill"), c("/Users/user/b")], 2);
    expect(l.map((r) => [r.path, r.source])).toEqual([
      ["/Users/user/b", "reply"],
      ["/Users/user/a", "skill"],
    ]);
    let big: Result[] = [];
    for (let i = 0; i < RESULTS_MAX + 5; i++) big = addCandidates(big, [c(`/Users/user/${i}`)], i);
    expect(big.length).toBe(RESULTS_MAX);
    expect(big[0].path).toBe(`/Users/user/${RESULTS_MAX + 4}`);
  });
  it("답 속 경로 = 실재 확정만 보임 · 스킬 = 늘 · 「새 결과」 수", () => {
    const l = addCandidates([], [c("/Users/user/a"), c("/Users/user/s", "skill")], 1);
    expect(visibleResults(l).map((r) => r.path)).toEqual(["/Users/user/s"]);
    const l2 = l.map((r) => (r.path === "/Users/user/a" ? { ...r, exists: true } : r));
    expect(visibleResults(l2).length).toBe(2);
    expect(resultsLabel(l2)).toEqual({ text: "결과 2 · 새 결과 2", count: 2, fresh: 2 });
    expect(resultsLabel(l2.map((r) => ({ ...r, seen: true })))).toEqual({ text: "결과 2", count: 2, fresh: 0 });
    // 설명으로만 쓴 경로(없음 확정 · 본 적 없음) = 카드 0
    expect(visibleResults(l.map((r) => ({ ...r, exists: false }))).map((r) => r.path)).toEqual(["/Users/user/s"]);
  });
  it("저장 = 경로·출처·시각·봤음만 · 실재는 다시 확인(null) · 설명으로 쓴 경로는 저장 0 · 깨진 꼴 버림", () => {
    const l = addCandidates([], [c("/Users/user/a"), c("/Users/user/s", "skill"), c("/Users/user/no")], 7).map((r) => (r.path === "/Users/user/a" ? { ...r, exists: true, seen: true } : r));
    const raw = persistable(l);
    expect(raw).not.toContain("/Users/user/no");
    const back = restoreResults(raw);
    expect(back.map((r) => [r.path, r.source, r.seen, r.exists])).toEqual([
      ["/Users/user/s", "skill", false, null],
      ["/Users/user/a", "reply", true, null],
    ]);
    expect(restoreResults("{bad")).toEqual([]);
    expect(restoreResults(JSON.stringify({ v: 2, items: [] }))).toEqual([]);
    expect(restoreResults(JSON.stringify({ v: 1, items: [{ path: 3 }, { path: "/Users/user/z", source: "x", at: 1, seen: false }] }))).toEqual([]);
  });
  it("고쳐 달라고 하기 = 앞글 + 쓰던 글 그대로(지우지 않음) · 두 번 눌러도 한 번", () => {
    const r = addCandidates([], [c("/Users/user/교회/a.html")], 1)[0];
    const p = revisePrefix(r);
    expect(p).toContain("/Users/user/교회/a.html");
    expect(withPrefix("", p)).toBe(p);
    expect(withPrefix("날짜 글씨 키워 줘", p)).toBe(`${p}날짜 글씨 키워 줘`);
    expect(withPrefix(withPrefix("x", p), p)).toBe(`${p}x`);
    expect(missingPrefix(r)).toContain("찾을 수 없어요");
  });
  it("부모 목록 → 실재 · 꼴 깨짐 = 모름 · 없음 오류만 「없음」", () => {
    expect(presenceIn([{ name: "a.html", is_dir: false }], "a.html")).toEqual({ exists: true, isDir: false });
    expect(presenceIn([{ name: "b" }], "a.html")).toEqual({ exists: false, isDir: null });
    expect(presenceIn([{ name: 1 }], "a.html")).toBeNull();
    expect(presenceIn(null, "a")).toBeNull();
    expect(presenceIn([{ name: "A.HTML", is_dir: false }], "a.html", true)?.exists).toBe(true);
    expect(listErrorIsMissing("No such file or directory (os error 2)")).toBe(true);
    expect(listErrorIsMissing("Permission denied (os error 13)")).toBe(false);
  });
});

// ── 장부(대역 invoke) ──
function fakeFs(files: Record<string, Array<{ name: string; is_dir: boolean }>>) {
  const calls: Array<[string, Record<string, unknown> | undefined]> = [];
  const mem = new Map<string, string>();
  let now = 1_000;
  const state = { openErr: null as string | null, homeFails: false };
  const invoke = async (cmd: string, a?: Record<string, unknown>) => {
    calls.push([cmd, a]);
    if (cmd === "home_dir_path") {
      if (state.homeFails) throw new Error("x");
      return H;
    }
    if (cmd === "list_dir") {
      const l = files[String(a?.path)];
      if (!l) throw new Error("No such file or directory (os error 2)");
      return l;
    }
    if (cmd === "result_open") {
      // 대역 = 우리 Tauri result_open(정규 경로 가둠은 cargo 시험 몫) — 열기·폴더 보기를 옛 이름으로 적어 둔다
      calls.push([a?.reveal ? "reveal_path" : "open_path", { path: a?.path }]);
      if (state.openErr) throw new Error(state.openErr);
      return null;
    }
    throw new Error(`unexpected ${cmd}`);
  };
  let changes = 0;
  const book = new ResultBook({ invoke, now: () => now++, store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v) } }, () => changes++);
  return { book, calls, mem, state, files, changes: () => changes };
}
const flush = () => new Promise((r) => setTimeout(r, 0));

describe("조각 7 — 장부(대역)", () => {
  it("홈을 알기 전 읽은 답은 모아 두었다가 판정 · 실재 확인 뒤에만 보임 · 열기 = open_path 1 · 새 결과 풀림", async () => {
    const t = fakeFs({ "/Users/user/교회": [{ name: "a.html", is_dir: false }] });
    t.book.onTail([rec("다 됐어요 /Users/user/교회/a.html 그리고 /Users/user/교회/없음.pdf", { uuid: "m1" })]);
    expect(t.book.items.length).toBe(0);
    await t.book.start();
    await flush();
    await t.book.tick();
    const vis = visibleResults(t.book.items);
    expect(vis.map((r) => [r.path, r.exists, r.seen])).toEqual([["/Users/user/교회/a.html", true, false]]);
    expect(t.book.items.find((r) => r.name === "없음.pdf")?.exists).toBe(false);
    await t.book.act("/Users/user/교회/a.html", "open");
    expect(t.calls.filter((c) => c[0] === "open_path")).toEqual([["open_path", { path: "/Users/user/교회/a.html" }]]);
    expect(t.book.items.find((r) => r.name === "a.html")?.seen).toBe(true);
    const saved = t.mem.get(RESULTS_KEY) ?? "";
    expect(saved).toContain("a.html");
    expect(saved).not.toContain("다 됐어요"); // 말 원문 0자
    expect(saved).not.toContain("없음.pdf"); // 설명으로만 나온 경로 저장 0
  });
  it("누르기 직전 파일이 사라짐 → open 호출 0 + 「찾을 수 없어요」 · 모름 → 호출 0", async () => {
    const t = fakeFs({ "/Users/user/교회": [{ name: "a.html", is_dir: false }] });
    await t.book.start();
    t.book.onTail([rec("/Users/user/교회/a.html")]);
    await t.book.tick();
    t.files["/Users/user/교회"] = [];
    await t.book.act("/Users/user/교회/a.html", "reveal");
    expect(t.calls.some((c) => c[0] === "reveal_path")).toBe(false);
    expect(t.book.notice).toBe(MSG_MISSING);
    expect(t.book.items[0].exists).toBe(false);
    expect(visibleResults(t.book.items).length).toBe(0); // 본 적 없는 답 속 경로 = 카드에서 빠짐
    t.files["/Users/user/교회"] = [{ name: 3 } as unknown as { name: string; is_dir: boolean }];
    await t.book.act("/Users/user/교회/a.html", "open");
    expect(t.book.notice).toBe(MSG_UNKNOWN);
    expect(t.calls.some((c) => c[0] === "open_path")).toBe(false);
  });
  it("실행형 파일 = Tauri 거절(executable_confirm) → force 로 다시 부르지 않음 + 폴더 보기 안내", async () => {
    const t = fakeFs({ "/Users/user/x": [{ name: "run.txt", is_dir: false }] });
    await t.book.start();
    t.book.onTail([rec("/Users/user/x/run.txt")]);
    await t.book.tick();
    t.state.openErr = "executable_confirm";
    await t.book.act("/Users/user/x/run.txt", "open");
    const opens = t.calls.filter((c) => c[0] === "open_path");
    expect(opens.length).toBe(1);
    expect(opens[0][1]).toEqual({ path: "/Users/user/x/run.txt" }); // force 칸 없음
    expect(t.book.notice).toBe(MSG_EXEC);
    expect(t.book.items[0].seen).toBe(false);
  });
  it("마스터 글 속 .app 꾸러미 = 열기 호출 0 + 안내 · 폴더 보기는 됨", async () => {
    const t = fakeFs({ "/Users/user/Downloads": [{ name: "Evil.app", is_dir: true }] });
    await t.book.start();
    t.book.onTail([rec("받은 앱: /Users/user/Downloads/Evil.app")]);
    await t.book.tick();
    await t.book.act("/Users/user/Downloads/Evil.app", "open");
    expect(t.calls.some((c) => c[0] === "open_path")).toBe(false);
    expect(t.book.notice).toBe(MSG_EXEC);
    await t.book.act("/Users/user/Downloads/Evil.app", "reveal");
    expect(t.calls.filter((c) => c[0] === "reveal_path").length).toBe(1);
  });
  it("Tauri 가 홈 밖·숨은 폴더로 이어짐을 거절(outside_home·hidden_path) → 안내 · 새 결과 그대로", async () => {
    const t = fakeFs({ "/Users/user": [{ name: "Report.pdf", is_dir: false }] });
    await t.book.start();
    t.book.onTail([rec("/Users/user/Report.pdf")]);
    await t.book.tick();
    t.state.openErr = "outside_home";
    await t.book.act("/Users/user/Report.pdf", "open");
    expect(t.book.notice).toBe(MSG_OUTSIDE);
    t.state.openErr = "network_path"; // (codex 2R · master#c48208b6 ③) 윈도 UNC
    await t.book.act("/Users/user/Report.pdf", "open");
    expect(t.book.notice).toBe(MSG_NETWORK);
    expect(t.book.items[0].seen).toBe(false);
  });
  it("(독립 검증 V4) 작업 화면 살핌 중(paused) = list_dir 0 · 후보는 모아 두었다가 대화 화면에서 확인", async () => {
    const t = fakeFs({ "/Users/user/교회": [{ name: "a.html", is_dir: false }] });
    await t.book.start();
    t.book.paused = true;
    t.book.onTail([rec("/Users/user/교회/a.html")]);
    await t.book.tick();
    await flush();
    expect(t.calls.filter((c) => c[0] === "list_dir").length).toBe(0);
    t.book.paused = false;
    await t.book.tick();
    expect(t.calls.filter((c) => c[0] === "list_dir").length).toBe(1);
    expect(visibleResults(t.book.items).length).toBe(1);
  });
  it("skill.run_finished — 본부 slug 만 · 부서 slug·slug 모름 = 버림 · 확인 전에도 카드(확인 중)", async () => {
    const t = fakeFs({ "/Users/user/runs": [{ name: "r1", is_dir: true }] });
    await t.book.start();
    const ev = (slug: string | null) => ({ name: "skill.run_finished", socket_slug: slug, payload: { run_id: "r1", status: "done", artifact_dir: "/Users/user/runs/r1" } });
    t.book.onEvent(ev("base"));
    expect(t.book.items.length).toBe(0); // slug 모름
    t.book.setHqSlug("base");
    t.book.onEvent(ev("dept-x"));
    expect(t.book.items.length).toBe(0);
    t.book.onEvent({ ...ev("base"), name: "skill.run_started" });
    expect(t.book.items.length).toBe(0);
    t.book.onEvent(ev("base"));
    expect(visibleResults(t.book.items).map((r) => [r.path, r.source])).toEqual([["/Users/user/runs/r1", "skill"]]);
    await flush();
    await t.book.tick();
    expect(t.book.items[0].exists).toBe(true);
  });
  it("홈 조회 실패 → 다음 켜짐에 다시(모은 답 잃지 않음) · 다시 켜면 저장된 결과 복원", async () => {
    const t = fakeFs({ "/Users/user": [{ name: "a.md", is_dir: false }] });
    t.state.homeFails = true;
    t.book.onTail([rec("/Users/user/a.md")]);
    await t.book.start();
    expect(t.book.items.length).toBe(0);
    t.state.homeFails = false;
    await t.book.start();
    await flush();
    await t.book.tick();
    expect(visibleResults(t.book.items).length).toBe(1);
    const again = new ResultBook({ invoke: async () => H, now: () => 1, store: { get: (k) => t.mem.get(k) ?? null, set: () => {} } }, () => {});
    expect(again.items.map((r) => [r.path, r.exists])).toEqual([["/Users/user/a.md", null]]);
  });
});

// ── 조각 9 작업 화면 띠 ──
const appr = (o: Partial<FeedApproval> = {}): FeedApproval => ({ request_id: "r1", surface_id: 2, created_at: 1, body: "b", excerpt: "b", command: "", readonly: null, truncated: false, screen: true, fingerprint: null, ...o });
const stall = (o: Partial<StallInput> = {}): StallInput => ({ now: 10_000, masterSid: 1, masterAlive: true, masterIdleSecs: 0, deadman: null, absentSince: null, stalledIds: new Set(), ...o });

describe("조각 9 — 작업 화면 띠(FR-C7 · 띠 하나)", () => {
  const q = openQuestions([{ kind: "ask", text: "금요일 배포 미룰까요?", uuid: "a1" }]);
  it("확인 띠가 먼저 · 마스터 물음 = 「마스터 창에서 답하기」 → 마스터 좌석", () => {
    const b = pickWorkBand(bandOf(q, [], stall()), "쓰던 말", 1);
    expect(b?.kind).toBe("confirm");
    expect(b?.kind === "confirm" && [b.text, b.action, b.seat]).toEqual(["확인이 필요해요 1 — 마스터가 물어요: 금요일 배포 미룰까요?", WORK_ANSWER_MASTER, 1]);
  });
  it("마스터 창 승인 = 마스터 좌석 · 도우미 허락 = 그 도우미 좌석(「도우미 창에서 답하기」)", () => {
    const m = pickWorkBand(bandOf([], [appr({ surface_id: 1 })], stall()), "", 1);
    expect(m?.kind === "confirm" && [m.item.kind, m.seat, m.action]).toEqual(["master_screen", 1, WORK_ANSWER_MASTER]);
    const h = pickWorkBand(bandOf([], [appr({ surface_id: 7 })], stall()), "", 1);
    expect(h?.kind === "confirm" && [h.item.kind, h.seat, h.action]).toEqual(["helper", 7, WORK_ANSWER_HELPER]);
  });
  it("확인 0 + 초안 = 초안 띠 · 공백 초안 = 0 · 모름 + 0건 = 띠 0(「없음」·「살펴보는 중」 어느 쪽으로도 안 칠함)", () => {
    expect(pickWorkBand(bandOf([], [], stall()), "어린이 합창도", 1)).toEqual({ kind: "draft", text: WORK_DRAFT_TEXT, action: "대화 화면에서 이어 쓰기" });
    expect(pickWorkBand(bandOf([], [], stall()), "  \n", 1)).toBeNull();
    const unknown: Band = bandOf(null, null, stall({ masterSid: undefined }));
    expect(unknown.known).toBe(false);
    expect(pickWorkBand(unknown, "", 1)).toBeNull();
    expect(pickWorkBand(null, "", null)).toBeNull();
  });
  it("모름이어도 항목이 있으면 「더 살펴보는 중」 덧붙여 보임", () => {
    const b = pickWorkBand(bandOf(null, [appr({ surface_id: 7 })], stall()), "", 1);
    expect(b?.kind === "confirm" && b.text).toBe("확인이 필요해요 1 · 더 살펴보는 중 — 도우미가 허락을 기다려요.");
  });
});

describe("조각 9 — 공통층: 대화 화면을 안 켰으면 작업 화면 띠도 조회 0 · 살피는 중엔 보내지 않음", () => {
  it("(codex 1R major) 앞 말 전달 중 작업 화면으로 → 그 전달이 끝나도 뒤 붙잡은 말은 안 나감(pump) → 대화 화면 돌아오면 나감", async () => {
    const sim = new Sim({ plan: () => "hang_written", hangMs: 5_000 });
    sim.core.attach();
    await sim.flush();
    await sim.core.poll();
    await sim.flush();
    sim.core.submit("첫 말");
    await sim.advance(100);
    sim.core.submit("둘째 말");
    await sim.advance(100);
    expect(sim.sends()).toBe(1); // 첫 말 쓰는 중 — 둘째는 차례 기다림
    expect(sim.core.watchStart()).toBe(true);
    sim.core.detach();
    sim.startPolling(); // 작업 화면 띠도 3초마다 poll
    await sim.advance(60_000); // 첫 말 응답 도착 → deliver 끝 → pump · 그 뒤 poll 20회
    expect(sim.sends()).toBe(1); // ★살피는 중 = 둘째 말 쓰기 0(pump·poll 어느 길로도)
    sim.core.attach();
    sim.core.watchStop();
    await sim.advance(60_000);
    expect(sim.sends()).toBe(2); // 대화 화면으로 돌아오면 나감
  });
  it("(독립 검증 V3) deliver 가 쓰기 직전 재조회를 기다리는 사이 작업 화면으로 → chat_send 0 · 붙잡음(work_view) → 대화 화면 돌아오면 1", async () => {
    const sim = new Sim();
    sim.approvals = [5];
    sim.core.attach();
    await sim.flush();
    await sim.core.poll();
    await sim.flush();
    sim.core.submit("재조회 중 옮김");
    await sim.advance(100);
    expect(sim.core.state.msgs[0].step).toBe("held");
    sim.approvals = [];
    const inv = sim.deps.invoke;
    let orgs = 0;
    sim.deps.invoke = async (cmd, a) => {
      const r = await inv(cmd, a);
      if (cmd === "org_status" && ++orgs === 2) {
        sim.core.watchStart(); // poll 의 org(1) 다음 = deliver 의 쓰기 직전 재조회(2) — 그 응답이 오기 전에 사람이 작업 화면을 누름
        sim.core.detach();
      }
      return r;
    };
    await sim.core.poll();
    await sim.advance(100);
    expect(orgs).toBeGreaterThanOrEqual(2);
    expect(sim.sends()).toBe(0);
    expect(sim.core.state.msgs[0].code).toBe("work_view");
    sim.deps.invoke = inv;
    sim.core.attach();
    sim.core.watchStop();
    sim.startPolling();
    await sim.advance(40_000);
    expect(sim.sends()).toBe(1);
  });
  it("대화 화면 켠 적 없음 → watchStart = false · invoke 0", async () => {
    const sim = new Sim();
    expect(sim.core.warm).toBe(false);
    expect(sim.core.watchStart()).toBe(false);
    await sim.flush();
    expect(sim.calls.length).toBe(0);
  });
  it("대화 화면에서 붙잡힌 말 → 작업 화면으로 → 문턱이 열려도 쓰기 0 → 대화 화면 돌아오면 1건", async () => {
    const sim = new Sim();
    sim.approvals = [5]; // 마스터 좌석 승인 창 → 문턱 닫힘 = 붙잡음
    sim.core.attach();
    await sim.flush();
    await sim.core.poll();
    await sim.flush();
    sim.core.submit("작업 화면 가기 전에 보낸 말");
    await sim.advance(100);
    expect(sim.core.state.msgs[0].step).toBe("held");
    expect(sim.sends()).toBe(0);
    // registry 순서 그대로: 새 화면(작업)을 먼저 띄우고 → 옛 화면(대화)을 내린다
    expect(sim.core.watchStart()).toBe(true); // 작업 화면 띠가 살핌
    sim.core.detach(); // 대화 화면 내림 — 살피는 중이면 구독·세션 읽기를 끄지 않는다
    sim.approvals = [];
    await sim.advance(20_000);
    for (let i = 0; i < 5; i++) {
      await sim.core.poll();
      await sim.advance(3_000);
    }
    expect(sim.sends()).toBe(0); // ★살피는 중엔 붙잡은 말을 보내지 않음(사람이 마스터 창에 칠 수 있음)
    expect(sim.calls.some((c) => c.cmd === "org_status")).toBe(true); // 띠 자료는 계속 받음
    // ★작업 화면에 있는 동안 마스터가 새로 물음 → 세션 읽기가 살아 있어 띠 자료에 들어온다(대화 화면 내림이 구독을 끄지 않음)
    sim.file.push({ uuid: "ask-w", parent: null, role: "assistant", text: "⟪확인 요청: 작업 화면에서 본 물음⟫", ts: null });
    await sim.core.readTranscript();
    await sim.advance(100);
    const qs = sim.core.confirm.band().items.filter((i) => i.kind === "ask");
    expect(qs.length).toBe(1);
    sim.core.attach(); // 대화 화면 다시(registry = 새 화면을 먼저 띄운 뒤 옛 화면을 내림)
    sim.core.watchStop();
    await sim.core.poll();
    await sim.advance(100);
    expect(sim.sends()).toBe(1);
  });
});

// ── S4-7 ──
describe("S4-7 · F7 — 사람이 물음을 띠에서 내림(마스터에게 보냄 0)", () => {
  it("(codex 2R minor) 같은 글로 다시 물으면 대화 자리(uuid)는 가장 최근 물음으로 · 번호는 그대로", () => {
    const qs = openQuestions([
      { kind: "ask", text: "A?", uuid: "old" },
      { kind: "ask", text: "A?", uuid: "new" },
      { kind: "ask", text: "A?", uuid: null }, // uuid 없는 다시 물음은 자리를 지우지 않음
    ]);
    expect(qs.map((q) => [q.id, q.uuid, q.last])).toEqual([["q1", "new", 3]]);
  });
  it("withoutDismissed = 번호 + 글 열쇠 · 같은 번호 다른 글은 그대로", () => {
    const qs = openQuestions([
      { kind: "ask", text: "A?", uuid: null },
      { kind: "ask", text: "B?", uuid: null },
    ]);
    expect(withoutDismissed(qs, new Map([[dismissKey(qs[0]), qs[0].last ?? 0]])).map((q) => q.text)).toEqual(["B?"]);
    expect(withoutDismissed(qs, new Map([[dismissKey({ ...qs[0], text: "다른 글" }), 99]])).length).toBe(2);
    // (codex 1R major) 내린 뒤 해결 없이 같은 글로 다시 물음 → 다시 보임
    const again = openQuestions([
      { kind: "ask", text: "A?", uuid: null },
      { kind: "ask", text: "B?", uuid: null },
      { kind: "ask", text: "A?", uuid: null },
    ]);
    expect(withoutDismissed(again, new Map([[dismissKey(qs[0]), qs[0].last ?? 0]])).map((q) => q.text)).toEqual(["A?", "B?"]);
  });
  it("ConfirmBook.dismiss → 띠에서 빠짐 · 기록(번호·dismiss · 글 0자) · invoke 0 · 세션 바뀌면 비움", async () => {
    const mem = new Map<string, string>();
    const calls: string[] = [];
    const b = new ConfirmBook({ invoke: async (c) => (calls.push(c), null), now: () => 5, store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v) } }, () => {});
    b.startSession("s1", 1, 0);
    b.onTail([rec("⟪확인 요청: 비밀 물음 글⟫", { uuid: "q" })]);
    b.observe({ items: [] }, { surfaces: [{ surface_id: 1, role: "master", agent_alive: true }] }, { surface_id: 1, agent_alive: true });
    const before = b.band();
    expect(before.items.map((i) => i.kind)).toEqual(["ask"]);
    const it0 = before.items[0];
    if (it0.kind !== "ask") throw new Error("ask");
    b.dismiss(it0.q);
    b.dismiss(it0.q); // 두 번 = 한 번
    expect(b.band().items.length).toBe(0);
    expect(b.band().known).toBe(true);
    expect(calls).toEqual([]);
    const log = mem.get("cys-chat-decisions") ?? "";
    expect(JSON.parse(log).items).toEqual([{ request_id: "q1", decision: "dismiss", at: 5, outcome: "dismissed" }]);
    expect(log).not.toContain("비밀 물음 글");
    // 해결 없이 같은 글로 다시 물음 → 다시 띠에(codex 1R major)
    b.onTail([rec("⟪확인 요청: 비밀 물음 글⟫")]);
    expect(b.band().items.length).toBe(1);
    // 해결 뒤 다시 묻기(새 표식 = 새 번호) → 띠에
    b.onTail([rec("⟪확인 해결: 비밀 물음 글⟫"), rec("⟪확인 요청: 비밀 물음 글⟫")]);
    expect(b.band().items.length).toBe(1);
    b.resetSession();
    b.startSession("s2", 1, 0);
    b.onTail([rec("⟪확인 요청: 비밀 물음 글⟫")]);
    expect(b.band().items.length).toBe(1); // 새 세션 = 내림 기록 비움(번호가 다시 매겨짐)
  });
});

describe("S4-7 · F10 — 저절로 바뀌어 온 항목엔 잠깐 누름을 받지 않음", () => {
  it("온 지 SWAP_GUARD_MS 안 = 막음 · 지나면 · 다른 열쇠 · 없음 = 통과", () => {
    const a = { key: "k2", at: 1_000 };
    expect(swapBlocked(a, "k2", 1_000)).toBe(true);
    expect(swapBlocked(a, "k2", 1_000 + SWAP_GUARD_MS - 1)).toBe(true);
    expect(swapBlocked(a, "k2", 1_000 + SWAP_GUARD_MS)).toBe(false);
    expect(swapBlocked(a, "k1", 1_000)).toBe(false);
    expect(swapBlocked(null, "k2", 1_000)).toBe(false);
  });
});
