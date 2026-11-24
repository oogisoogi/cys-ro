// topbarlayout.test.ts — 상단 단추 켬끔·순서의 순수 계산(저장·복원·손상 폴백·새 단추·고정 2·▲▼ 경계·끌어 놓기) · TICKET=cysr-1110-screen-settings.
//
// 박사님 2026-10-12 원문: 「메뉴 목록을 보여주고 켜기/끄기 버튼을 두는 것이다. 순서로 마음대로 조정할 수 있도록 드래그드롭하든지
// 켜기/끄지 버튼 옆에 끌어옮기기 아이콘을 넣든지」 · 09:1x 「최적안대로 한다.」(기본 끔 = + New · Split → · Split ↓ · 창 닫기 · 완전 초기화).
// 화면 동작(토글 즉시 반영 · 실제 마우스 끌기 · 새로 고침 뒤 유지)은 docs/screen-settings-evidence-2026-10-12/screen-settings-headless.ts 가
// 실번들로 잰다. 여기는 그 화면이 부르는 계산을 잰다. 단추 목록은 index.html 에서 읽는다(시험이 자기 목록을 따로 들고 있지 않게).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import {
  TOPBAR_LAYOUT_KEY, TOPBAR_LAYOUT_VERSION, TOPBAR_PINNED, TOPBAR_DEFAULT_OFF, type TopbarItem,
  SORT_BUTTON_MODE, FILES_BUTTON_DEFAULT, FILES_BTN_OFF_ONCE_KEY, topbarDefaultOff, filesButtonOffOnce, topbarDimIds,
  isTopbarPinned, defaultTopbarLayout, parseTopbarLayout, serializeTopbarLayout,
  setTopbarItemOn, moveTopbarItem, canMoveTopbarItem, dropTopbarItem, visibleTopbarIds,
} from "./topbarlayout";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const top = html.slice(html.indexOf('<header id="topbar">'), html.indexOf("</header>"));
// main.ts 의 TOPBAR_DOM_IDS 와 같은 뜻 — #topbar 의 id 달린 단추, html 순서
const DOM = [...top.matchAll(/<button\b[^>]*?\bid="([^"]+)"/g)].map((m) => m[1]);
const label = (id: string) => new RegExp(`<button\\b[^>]*\\bid="${id}"[^>]*>([^<]*)`).exec(top)![1].trim();
const ids = (xs: readonly TopbarItem[]) => xs.map((x) => x.id);
const save = (items: unknown, version: unknown = 1) => JSON.stringify({ version, items });

describe("기본값 — 박사님 확정 A안(끔 5 · 보이는 8 = 종전 6 + 상단으로 옮긴 상담소·아고라)", () => {
  it("대상 = 상단바 단추 13개 · 기본 순서 = index.html 순서(피드백 · 상담소 · 아고라 · 정렬 …)", () => {
    // (cysr-1119-s10b MD-T9) ↻ 재시작 = 맨 오른쪽(화면 설정 뒤) — html 순서 = 기본 순서.
    // (1.1.19 · cysr-1119-s10b AG4·AG5) 상담소·아고라 = html 에서 빠짐 → 11개.
    expect(DOM).toEqual(["btn-feedback", "btn-equalize", "btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-files", "btn-cc", "btn-factory-reset", "btn-theme", "btn-restart-daemon"]);
    expect(ids(defaultTopbarLayout(DOM))).toEqual(DOM);
  });

  it("처음 보이는 단추 = 피드백 · 화면 설정 · ↻ 재시작(1.1.19: 상담소·아고라 삭제 · 정렬 fold · 파일 off = 박사님 11-24)", () => {
    expect(SORT_BUTTON_MODE).toBe("fold");
    expect(FILES_BUTTON_DEFAULT).toBe("off");
    expect(visibleTopbarIds(defaultTopbarLayout(DOM)).map(label)).toEqual(["피드백", "화면 설정", "↻ 재시작"]); // + 화면 전환 2 = 첫 화면 5(DESIGN §2-1 fold)
  });

  it("처음 꺼진 단추 = 정렬 · + New · Split → · Split ↓ · 창 닫기 · 파일 · Control Center · 완전 초기화(html 에 요소는 그대로 있다)", () => {
    const off = defaultTopbarLayout(DOM).filter((x) => !x.on).map((x) => x.id);
    expect(off.map(label)).toEqual(["정렬", "+ New", "Split →", "Split ↓", "창 닫기", "파일", "Control Center", "완전 초기화"]);
    expect([...TOPBAR_DEFAULT_OFF].sort()).toEqual([...off].sort());
    for (const id of TOPBAR_DEFAULT_OFF) expect(html.split(`id="${id}"`).length - 1).toBe(1);
  });

  it("고정 1 = 화면 설정(1.1.15 1e: Control Center 고정 해제) — 기본 끔 목록에 들 수 없다", () => {
    expect(TOPBAR_PINNED.map(label)).toEqual(["화면 설정"]);
    for (const id of TOPBAR_PINNED) {
      expect(DOM).toContain(id);
      expect(TOPBAR_DEFAULT_OFF).not.toContain(id);
      expect(isTopbarPinned(id)).toBe(true);
    }
    expect(isTopbarPinned("btn-feedback")).toBe(false);
  });

  it("저장 키·판 = cys-topbar-layout · version 1", () => {
    expect(TOPBAR_LAYOUT_KEY).toBe("cys-topbar-layout");
    expect(TOPBAR_LAYOUT_VERSION).toBe(1);
  });
});

describe("저장 → 복원", () => {
  it("저장 형식 = {version:1, items:[{id,on}]} · items 순서 = 화면 순서 · 다른 필드는 싣지 않는다", () => {
    const items = [{ id: "btn-theme", on: true, extra: 1 } as TopbarItem, { id: "btn-new", on: false }];
    expect(serializeTopbarLayout(items)).toBe('{"version":1,"items":[{"id":"btn-theme","on":true},{"id":"btn-new","on":false}]}');
  });

  it("저장한 것을 다시 읽으면 같은 배치(순서·켬끔 그대로)", () => {
    let l = defaultTopbarLayout(DOM);
    l = setTopbarItemOn(l, "btn-new", true);
    l = setTopbarItemOn(l, "btn-feedback", false);
    l = moveTopbarItem(l, "btn-theme", -1);
    l = dropTopbarItem(l, "btn-restart-daemon", "btn-feedback", false);
    expect(parseTopbarLayout(serializeTopbarLayout(l), DOM)).toEqual(l);
    expect(parseTopbarLayout(serializeTopbarLayout(defaultTopbarLayout(DOM)), DOM)).toEqual(defaultTopbarLayout(DOM));
  });

  it("저장 없음(null·빈 글자) = 기본값", () => {
    for (const raw of [null, undefined, ""]) expect(parseTopbarLayout(raw, DOM)).toEqual(defaultTopbarLayout(DOM));
  });
});

describe("손상·구판 저장 = 기본값(앱이 죽거나 단추가 통째로 사라지지 않는다)", () => {
  const allOn = DOM.map((id) => ({ id, on: true }));
  const bad: [string, string][] = [
    ["JSON 아님", "{{{not json"],
    ["숫자", "42"],
    ["null 글자", "null"],
    ["배열만(판 표시 없음)", JSON.stringify(allOn)],
    ["구판 version 0", save(allOn, 0)],
    ["다음 판 version 2", save(allOn, 2)],
    ["version 이 글자", save(allOn, "1")],
    ["items 없음", JSON.stringify({ version: 1 })],
    ["items 가 객체", save({ a: 1 })],
    ["항목이 글자", save(["btn-new"])],
    ["항목에 null", save([null])],
    ["on 이 글자", save([{ id: "btn-new", on: "yes" }])],
    ["id 가 숫자", save([{ id: 3, on: true }])],
    ["on 없음", save([{ id: "btn-new" }])],
    ["빈 목록", save([])],
    ["아는 단추가 하나도 없음", save([{ id: "btn-gone", on: true }])],
  ];
  for (const [name, raw] of bad) {
    it(name, () => expect(parseTopbarLayout(raw, DOM)).toEqual(defaultTopbarLayout(DOM)));
  }
  it("손상 폴백에서도 기본 끔은 꺼진 채다(전부 켬으로 새지 않는다 · 1.1.15 1e: Control Center 포함)", () => {
    expect(visibleTopbarIds(parseTopbarLayout("{{{", DOM)).length).toBe(DOM.length - TOPBAR_DEFAULT_OFF.length);
  });
});

describe("새 단추·없어진 단추·중복", () => {
  // ★(cysr-menu-top-row 2026-10-21) 종전 기대값 = 「켠 채 맨 끝」. 지금 = 켠 채 **html 바로 앞 단추의 뒤** — 1.1.9 에서 순서를 저장한
  //   사람에게 상담소·아고라가 맨 오른쪽(화면 설정 뒤)이 아니라 피드백 바로 뒤에 서야 박사님 순서(피드백 · 상담소 · 아고라)가 된다.
  it("저장에 없는 단추(나중에 생긴 단추) = 켠 채 html 바로 앞 단추의 뒤 — 기본 끔 목록에 든 id 라도 켠다", () => {
    const saved = save(DOM.filter((id) => id !== "btn-files" && id !== "btn-new").map((id) => ({ id, on: false })));
    const l = parseTopbarLayout(saved, DOM);
    expect(ids(l)).toEqual(DOM); // 저장 순서가 html 순서였으니 빈 자리에 그대로 돌아간다
    expect(l.filter((x) => x.id === "btn-new" || x.id === "btn-files").every((x) => x.on)).toBe(true);
    expect(ids(l).length).toBe(DOM.length);
  });

  // ★(1.1.19 · cysr-1119-s10b AG4·AG5) 상담소·아고라 단추가 html 에서 빠졌다 — 1.1.10~1.1.18 에서 순서를 저장한 기기(두 id 가 저장에 있음)도
  //   두 단추가 보이지 않는다(파서가 화면에 없는 id 를 버린다) · 나머지 저장 순서·켬끔은 그대로. (옛 시험 「1.1.9 저장 → 상담소·아고라 피드백 뒤」 둘은 대상 없음 → 지움)
  it("저장 배치에 btn-counsel·btn-agora 가 있어도(1.1.18 이하 저장) 보이지 않는다 · 나머지 순서·켬끔 그대로", () => {
    expect(DOM.includes("btn-counsel") || DOM.includes("btn-agora")).toBe(false);
    const OLD = ["btn-feedback", "btn-counsel", "btn-agora", ...DOM.filter((id) => id !== "btn-feedback")];
    const custom = [...OLD].reverse().map((id) => ({ id, on: id !== "btn-files" }));
    const l = parseTopbarLayout(save(custom), DOM);
    expect(ids(l)).toEqual(custom.map((x) => x.id).filter((id) => DOM.includes(id)));
    expect(visibleTopbarIds(l).some((id) => id === "btn-counsel" || id === "btn-agora")).toBe(false);
    expect(l.find((x) => x.id === "btn-files")!.on).toBe(false);
    expect(l.length).toBe(DOM.length);
  });

  it("미래 단추 id 가 html 에 생기면 옛 저장을 읽어도 그 단추가 보인다", () => {
    const future = [...DOM, "btn-future"];
    const l = parseTopbarLayout(serializeTopbarLayout(defaultTopbarLayout(DOM)), future);
    expect(l.at(-1)).toEqual({ id: "btn-future", on: true });
    expect(defaultTopbarLayout(future).at(-1)).toEqual({ id: "btn-future", on: true }); // 저장이 없어도 켬
  });

  it("저장에는 있는데 화면에 없는 id = 버린다 · 같은 id 두 번 = 앞의 것만", () => {
    const l = parseTopbarLayout(save([{ id: "btn-gone", on: true }, { id: "btn-new", on: true }, { id: "btn-new", on: false }]), DOM);
    expect(ids(l)).not.toContain("btn-gone");
    expect(l.filter((x) => x.id === "btn-new")).toEqual([{ id: "btn-new", on: true }]);
    // (cysr-menu-top-row) 종전 기대값 = l[0] 이 btn-new. 지금 = 저장에 없는 단추가 html 바로 앞 단추 뒤에 끼므로 피드백(html 맨 앞)이 맨 앞 ·
    //   btn-new 는 html 앞 단추(정렬) 뒤.
    expect(l[0]).toEqual({ id: "btn-feedback", on: true });
    expect(ids(l).indexOf("btn-new")).toBe(ids(l).indexOf("btn-equalize") + 1);
    expect([...ids(l)].sort()).toEqual([...DOM].sort());
  });
});

describe("고정 2 — 끌 수 없다(순서만)", () => {
  it("토글로 끌 수 없다 · 다른 단추는 꺼진다", () => {
    let l = defaultTopbarLayout(DOM);
    for (const id of TOPBAR_PINNED) l = setTopbarItemOn(l, id, false);
    expect(l).toEqual(defaultTopbarLayout(DOM));
    expect(setTopbarItemOn(l, "btn-feedback", false).find((x) => x.id === "btn-feedback")!.on).toBe(false);
  });

  it("저장값이 끔이어도 켬으로 읽는다(손으로 고친 저장 · 옛 판 저장)", () => {
    const l = parseTopbarLayout(save(DOM.map((id) => ({ id, on: false }))), DOM);
    expect(visibleTopbarIds(l).sort()).toEqual([...TOPBAR_PINNED].sort());
  });

  it("순서는 바뀐다(▲▼ · 끌어 놓기)", () => {
    const l = defaultTopbarLayout(DOM);
    expect(ids(moveTopbarItem(l, "btn-restart-daemon", -1)).slice(-2)).toEqual(["btn-restart-daemon", "btn-theme"]); // (1.1.19 MD-T9) 재시작 = 맨 끝
    expect(ids(dropTopbarItem(l, "btn-cc", "btn-feedback", true))[0]).toBe("btn-cc");
  });
});

describe("토글", () => {
  it("끔 → 켬 → 끔 · 그 단추만 바뀐다 · 원본 배열·항목을 고치지 않는다", () => {
    const l = defaultTopbarLayout(DOM);
    const snap = JSON.stringify(l);
    const on = setTopbarItemOn(l, "btn-new", true);
    expect(on.find((x) => x.id === "btn-new")!.on).toBe(true);
    expect(on.filter((x, i) => x.on !== l[i].on).map((x) => x.id)).toEqual(["btn-new"]);
    expect(setTopbarItemOn(on, "btn-new", false)).toEqual(l);
    expect(JSON.stringify(l)).toBe(snap);
    expect(on).not.toBe(l);
  });

  it("없는 id = 무변경", () => expect(setTopbarItemOn(defaultTopbarLayout(DOM), "btn-nope", false)).toEqual(defaultTopbarLayout(DOM)));
});

describe("▲▼ — 한 칸 · 경계", () => {
  const l = defaultTopbarLayout(DOM);
  it("▼ = 다음 단추와 자리 바꿈 · ▲ 로 되돌아옴", () => {
    const d = moveTopbarItem(l, "btn-feedback", 1);
    expect(ids(d).slice(0, 2)).toEqual([DOM[1], "btn-feedback"]); // 다음 단추 = DOM[1](1.1.10 = 상담소)
    expect(moveTopbarItem(d, "btn-feedback", -1)).toEqual(l);
  });

  it("맨 위의 ▲ · 맨 아래의 ▼ · 없는 id = 무변경(새 배열)", () => {
    expect(moveTopbarItem(l, DOM[0], -1)).toEqual(l);
    expect(moveTopbarItem(l, DOM.at(-1)!, 1)).toEqual(l);
    expect(moveTopbarItem(l, "btn-nope", 1)).toEqual(l);
    expect(moveTopbarItem(l, DOM[0], -1)).not.toBe(l);
  });

  it("누를 수 있는지 = 맨 위는 ▲ 불가 · 맨 아래는 ▼ 불가 · 가운데는 둘 다", () => {
    expect([canMoveTopbarItem(l, DOM[0], -1), canMoveTopbarItem(l, DOM[0], 1)]).toEqual([false, true]);
    expect([canMoveTopbarItem(l, DOM.at(-1)!, -1), canMoveTopbarItem(l, DOM.at(-1)!, 1)]).toEqual([true, false]);
    for (const id of DOM.slice(1, -1)) expect([canMoveTopbarItem(l, id, -1), canMoveTopbarItem(l, id, 1)]).toEqual([true, true]);
    expect(canMoveTopbarItem(l, "btn-nope", 1)).toBe(false);
  });

  it("켬끔은 따라간다(꺼진 단추를 옮겨도 꺼진 채)", () => {
    const d = moveTopbarItem(l, "btn-new", -1);
    expect(d.find((x) => x.id === "btn-new")!.on).toBe(false);
    expect(visibleTopbarIds(d).length).toBe(DOM.length - TOPBAR_DEFAULT_OFF.length); // 1.1.15 1e: Control Center 기본 끔 · 1.1.19 정렬·파일 상수
  });
});

describe("끌어 놓기 결과 = 순서", () => {
  const l = defaultTopbarLayout(DOM);
  it("다른 줄의 앞·뒤에 놓는다(아래 → 위 · 위 → 아래)", () => {
    expect(ids(dropTopbarItem(l, "btn-restart-daemon", "btn-feedback", false)).slice(0, 3)).toEqual(["btn-feedback", "btn-restart-daemon", DOM[1]]);
    expect(ids(dropTopbarItem(l, "btn-restart-daemon", "btn-feedback", true)).slice(0, 2)).toEqual(["btn-restart-daemon", "btn-feedback"]);
    // (1.1.19 MD-T9) 맨 끝 단추 = ↻ 재시작(html 순서) — 끝 단추를 html 에서 읽는다.
    expect(ids(dropTopbarItem(l, "btn-feedback", DOM.at(-1)!, false)).at(-1)).toBe("btn-feedback");
    expect(ids(dropTopbarItem(l, "btn-feedback", DOM.at(-1)!, true)).slice(-2)).toEqual(["btn-feedback", DOM.at(-1)!]);
  });

  it("제자리(바로 뒤 줄의 앞 · 바로 앞 줄의 뒤)·자기 위·없는 id = 순서 그대로", () => {
    expect(dropTopbarItem(l, "btn-feedback", DOM[1], true)).toEqual(l);
    expect(dropTopbarItem(l, DOM[1], "btn-feedback", false)).toEqual(l);
    expect(dropTopbarItem(l, "btn-feedback", "btn-feedback", true)).toEqual(l);
    expect(dropTopbarItem(l, "btn-nope", "btn-feedback", true)).toEqual(l);
    expect(dropTopbarItem(l, "btn-feedback", "btn-nope", true)).toEqual(l);
  });

  it("어떤 조합으로 옮겨도 단추가 늘거나 줄거나 켬끔이 바뀌지 않는다(13×13×2 전수 + ▲▼ 잇기)", () => {
    const onOf = (xs: TopbarItem[]) => Object.fromEntries(xs.map((x) => [x.id, x.on]));
    for (const s of DOM) for (const a of DOM) for (const before of [true, false]) {
      const r = dropTopbarItem(l, s, a, before);
      expect([...ids(r)].sort()).toEqual([...DOM].sort());
      expect(onOf(r)).toEqual(onOf(l));
      if (s !== a) {
        const si = ids(r).indexOf(s), ai = ids(r).indexOf(a);
        expect(si - ai).toBe(before ? -1 : 1); // 놓은 자리 = 그 줄의 바로 앞·뒤
      }
    }
    let m = l;
    for (let i = 0; i < 40; i++) m = moveTopbarItem(m, DOM[(i * 7) % DOM.length], i % 3 ? 1 : -1);
    expect([...ids(m)].sort()).toEqual([...DOM].sort());
    expect(onOf(m)).toEqual(onOf(l));
  });
});

describe("(1e) Control Center 단추 — 저장 배치에도 한 번만 끈다", async () => {
  const { ccButtonOffOnce } = await import("./topbarlayout");
  it("켜져 있고 표지 없음 = 끄고 changed · 표지 있음 = 그대로(사람이 다시 켠 것 존중) · 이미 끔 = 그대로", () => {
    const on = DOM.map((id) => ({ id, on: true }));
    const r = ccButtonOffOnce(on, false);
    expect(r.changed).toBe(true);
    expect(r.items.find((x) => x.id === "btn-cc")!.on).toBe(false);
    expect(r.items.filter((x) => !x.on).map((x) => x.id)).toEqual(["btn-cc"]);
    expect(ccButtonOffOnce(on, true).changed).toBe(false);
    expect(ccButtonOffOnce(r.items, false).changed).toBe(false);
  });
});

// ── (cysr-1119-s10b) MD-T4 정렬 · MD-T7 파일 · MD-T9 재시작 — 값으로 갈리는 빌드 상수(DESIGN §2-3 · §8-3 · §8-4) ──
describe("MD-T4·T7 — 기본 끔 목록은 두 상수에서 계산한다(값마다 동작)", () => {
  const BASE = ["btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-factory-reset", "btn-cc"];
  it("keep·dim = 정렬 켬 · fold = 정렬 끔 / on = 파일 켬 · off = 파일 끔(그 밖 기본 끔 6 은 그대로)", () => {
    for (const sort of ["keep", "dim", "fold"] as const)
      for (const files of ["on", "off"] as const) {
        const off = topbarDefaultOff(sort, files);
        expect([...off].sort()).toEqual([...BASE, ...(sort === "fold" ? ["btn-equalize"] : []), ...(files === "off" ? ["btn-files"] : [])].sort());
      }
    expect([...TOPBAR_DEFAULT_OFF].sort()).toEqual([...topbarDefaultOff(SORT_BUTTON_MODE, FILES_BUTTON_DEFAULT)].sort());
  });
  it("on·keep = 1.1.18 과 같은 배치(상담소·아고라 빼고 · 재시작 자리만 맨 끝)", () => {
    const l = defaultTopbarLayout(DOM, topbarDefaultOff("keep", "on"));
    expect(visibleTopbarIds(l).map(label)).toEqual(["피드백", "정렬", "파일", "화면 설정", "↻ 재시작"]);
  });
  it("흐린 글자 = 재시작 늘 · 정렬은 dim 일 때만", () => {
    expect(topbarDimIds("keep")).toEqual(["btn-restart-daemon"]);
    expect(topbarDimIds("fold")).toEqual(["btn-restart-daemon"]);
    expect([...topbarDimIds("dim")].sort()).toEqual(["btn-equalize", "btn-restart-daemon"]);
  });
});

describe("MD-T7 — 파일 단추: 저장 배치에도 한 번만 끈다(off) · on 이면 손대지 않는다", () => {
  it("표지 열쇠 = cys-files-btn-off-119", () => expect(FILES_BTN_OFF_ONCE_KEY).toBe("cys-files-btn-off-119"));
  it("off: 켜져 있고 표지 없음 = 끄고 changed · 표지 있음 = 그대로(다시 켜면 유지) · 이미 끔 = 그대로 · 파일 말고는 안 바뀜", () => {
    const on = DOM.map((id) => ({ id, on: true }));
    const r = filesButtonOffOnce(on, false, "off");
    expect(r.changed).toBe(true);
    expect(r.items.filter((x) => !x.on).map((x) => x.id)).toEqual(["btn-files"]);
    expect(filesButtonOffOnce(on, true, "off").changed).toBe(false);
    expect(filesButtonOffOnce(r.items, false, "off").changed).toBe(false);
  });
  it("on: 어떤 저장이어도 바꾸지 않는다", () => {
    const on = DOM.map((id) => ({ id, on: true }));
    expect(filesButtonOffOnce(on, false, "on")).toEqual({ items: on, changed: false });
  });
});

describe("MD-T4·T7·T9 배선(main.ts) — 표지 1회 끄기 · 흐린 글자", () => {
  const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  it("파일 단추 표지 = 시작 때 한 번 · 저장이 있을 때만 저장 배치를 고친다(CC 1e 와 같은 꼴)", () => {
    expect(main).toContain("filesButtonOffOnce(topbarLayout, localStorage.getItem(FILES_BTN_OFF_ONCE_KEY) === \"1\")");
    expect(main).toContain("localStorage.setItem(FILES_BTN_OFF_ONCE_KEY, \"1\");");
  });
  it("흐린 글자 = topbarDimIds(SORT_BUTTON_MODE) 의 단추에 tb-dim(확인 창·처리기 무변경)", () => {
    expect(main).toContain("for (const id of topbarDimIds(SORT_BUTTON_MODE)) topbarBtn(id)?.classList.add(\"tb-dim\");");
    const css = readFileSync(new URL("./views/views.css", import.meta.url), "utf8");
    expect(css).toContain("#topbar > button.tb-dim");
  });
});
