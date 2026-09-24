// exitbanner.test.ts — 좌석 종료 배너 위치·쓰기 순서 · TICKET=v116-exited-banner.
//
// 실기 맥락: 박사님 09-24 「[surface exited] 가 맨 아래가 아니라 중간에 나온다」. 헤드리스 c17 재현 —
// 커서가 입력 상자·대체 화면 TUI 중간에 있는 채 끝나면 배너가 그 아래 내용 위에 덮어써졌다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { bannerRow, exitedBannerSeq, writeExitedBanner, EXITED_BANNER, type ExitTerm } from "./exitbanner";

const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
const view = (lines: string[], cursorY: number) => ({ rows: lines.length, cursorY, line: (y: number) => lines[y] ?? "" });
const count = (s: string, sub: string) => s.split(sub).length - 1;

// 가짜 터미널 — 쓰기는 기록만 하고 콜백은 drain() 때 부른다(xterm 의 「해석 뒤 콜백」 흉내).
// 화면은 baseY 뒤에 있다(스크롤백이 쌓인 주 화면 — 판독이 baseY 를 더해야 맞는 줄을 읽는다).
function fake(lines: string[], cursorY: number, baseY = 100) {
  const log: string[] = [];
  const pending: (() => void)[] = [];
  const st = { lines, cursorY };
  const term: ExitTerm = {
    rows: lines.length,
    buffer: {
      active: {
        baseY,
        get cursorY() { return st.cursorY; },
        getLine: (y: number) => { const i = y - baseY; return i >= 0 && i < st.lines.length ? { translateToString: () => st.lines[i] } : undefined; },
      },
    },
    write(data, cb) { log.push(typeof data === "string" ? data : `<bytes:${new TextDecoder().decode(data)}>`); if (cb) pending.push(cb); },
  };
  const drain = () => { while (pending.length) pending.shift()!(); };
  return { term, log, drain, st };
}
const filter = (rest: string, reset = "<reset>") => ({ flush: () => new TextEncoder().encode(rest), reset: () => reset });

describe("v116-exited-banner 배너 줄 판정(bannerRow)", () => {
  it("커서가 중간 · 아래에 내용이 남음 → 마지막 내용 줄 뒤(⒜ 입력 상자 · ⒝ 대체 화면 TUI)", () => {
    const lines = ["fill", "╭──╮", "│ ❯ │", "╰──╯", "  ? for shortcuts", "  ctx 12%", "", ""];
    expect(bannerRow(view(lines, 2))).toBe(5);
  });
  it("커서 아래가 비었음 → 커서 줄 그대로(종전 자리 · 멀쩡한 화면 무변)", () => {
    expect(bannerRow(view(["a", "b", "$ ", "", ""], 2))).toBe(2);
  });
  it("내용이 마지막 행까지 있음 → 마지막 행(줄바꿈이 한 줄 올려 배너 자리를 만든다)", () => {
    expect(bannerRow(view(["a", "b", "c", "d"], 1))).toBe(3);
  });
  it("공백뿐인 줄은 내용이 아니다 · 커서 위 내용은 보지 않는다", () => {
    expect(bannerRow(view(["top", "   ", "\t", "  "], 0))).toBe(0);
  });
  it("커서가 마지막 행 → 마지막 행", () => {
    expect(bannerRow(view(["a", "b", "c"], 2))).toBe(2);
  });
});

describe("v116-exited-banner 배너 문자열", () => {
  it("스크롤 영역 해제 → 절대 이동(1-기준) → 배너 1회 · 대체 화면 해제(1049l) 없음", () => {
    const s = exitedBannerSeq(view(["a", "b", "c", "d", ""], 1));
    expect(s).toBe(`\x1b[r\x1b[4;1H${EXITED_BANNER}`);
    expect(count(s, "[surface exited]")).toBe(1);
    expect(s.includes("1049")).toBe(false);
  });
});

describe("v116-exited-banner 쓰기 순서(writeExitedBanner)", () => {
  it("①잔여 방류 ②정합기 reset ③배너 — 배너는 앞 쓰기가 해석된 뒤(콜백)에만", () => {
    const f = fake(["x", "y", "z", "", ""], 0);
    writeExitedBanner(f.term, filter("\x1b[?10"));
    expect(f.log).toEqual(["<bytes:\x1b[?10>", "<reset>"]); // 콜백 전 = 배너 없음
    f.drain();
    expect(f.log.length).toBe(3);
    expect(f.log[2].endsWith(EXITED_BANNER)).toBe(true);
  });
  it("판독은 콜백 시점 화면 — 대기열의 출력이 해석되며 바뀐 화면을 본다", () => {
    const f = fake(["", "", "", "", ""], 0);
    writeExitedBanner(f.term, filter(""));
    f.st.lines = ["a", "b", "c", "d", ""]; // 대기열에 있던 출력이 해석된 뒤의 화면
    f.st.cursorY = 1;
    f.drain();
    expect(f.log.at(-1)).toBe(`\x1b[r\x1b[4;1H${EXITED_BANNER}`);
  });
  it("잔여가 없으면 빈 쓰기 0 · 판독은 baseY 기준(스크롤백 뒤 화면)", () => {
    const f = fake(["a", "", "b", ""], 0, 4990);
    writeExitedBanner(f.term, filter(""));
    f.drain();
    expect(f.log[0]).toBe("<reset>");
    expect(f.log[1]).toBe(`\x1b[r\x1b[3;1H${EXITED_BANNER}`);
  });
  it("판독 실패(창 파괴 등) → 종전 배너로 강등 · 배너 정확히 1회 · done 호출", () => {
    const f = fake(["a", "b"], 0);
    (f.term.buffer.active as any).getLine = () => { throw new Error("disposed"); };
    let done = 0;
    writeExitedBanner(f.term, filter(""), () => { done++; });
    f.drain();
    expect(f.log.filter((l) => l.includes("[surface exited]")).length).toBe(1);
    expect(f.log.at(-1)).toBe(EXITED_BANNER);
    expect(done).toBe(1);
  });
  it("done(snapToBottom)은 배너 쓰기의 콜백으로 넘어간다", () => {
    const f = fake(["a", ""], 0);
    let done = 0;
    writeExitedBanner(f.term, filter(""), () => { done++; });
    expect(done).toBe(0);
    f.drain();
    expect(done).toBe(1);
  });
});

describe("v116-exited-banner 배선(main.ts)", () => {
  it("exited 리스너가 writeExitedBanner 로 쓴다 · 커서 자리 직접 배너 쓰기 0", () => {
    const i = main.indexOf("listen(ev.exited_event");
    const body = main.slice(i, main.indexOf("});", i));
    expect(body.includes("writeExitedBanner(term, trackFilter, snapToBottom)")).toBe(true);
    expect(main.includes('"\\r\\n\\x1b[31m[surface exited]')).toBe(false);
  });
});
