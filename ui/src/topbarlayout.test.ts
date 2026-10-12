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

describe("기본값 — 박사님 확정 A안(끔 5 · 보이는 6)", () => {
  it("대상 = 상단바 단추 11개 · 기본 순서 = index.html 순서", () => {
    expect(DOM).toEqual(["btn-feedback", "btn-equalize", "btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-files", "btn-cc", "btn-restart-daemon", "btn-factory-reset", "btn-theme"]);
    expect(ids(defaultTopbarLayout(DOM))).toEqual(DOM);
  });

  it("처음 보이는 단추 = 피드백 · 정렬 · 파일 · Control Center · ↻ 재시작 · 화면 설정", () => {
    expect(visibleTopbarIds(defaultTopbarLayout(DOM)).map(label)).toEqual(["피드백", "정렬", "파일", "Control Center", "↻ 재시작", "화면 설정"]);
  });

  it("처음 꺼진 단추 = + New · Split → · Split ↓ · 창 닫기 · 완전 초기화(html 에 요소는 그대로 있다)", () => {
    const off = defaultTopbarLayout(DOM).filter((x) => !x.on).map((x) => x.id);
    expect(off.map(label)).toEqual(["+ New", "Split →", "Split ↓", "창 닫기", "완전 초기화"]);
    expect([...TOPBAR_DEFAULT_OFF].sort()).toEqual([...off].sort());
    for (const id of TOPBAR_DEFAULT_OFF) expect(html.split(`id="${id}"`).length - 1).toBe(1);
  });

  it("고정 2 = 화면 설정 · Control Center — 기본 끔 목록에 들 수 없다", () => {
    expect(TOPBAR_PINNED.map(label)).toEqual(["화면 설정", "Control Center"]);
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
  it("손상 폴백에서도 끔 5 는 꺼진 채다(전부 켬으로 새지 않는다)", () => {
    expect(visibleTopbarIds(parseTopbarLayout("{{{", DOM)).length).toBe(6);
  });
});

describe("새 단추·없어진 단추·중복", () => {
  it("저장에 없는 단추(나중에 생긴 단추) = 켠 채 맨 끝 — 기본 끔 목록에 든 id 라도 켠다", () => {
    const saved = save(DOM.filter((id) => id !== "btn-files" && id !== "btn-new").map((id) => ({ id, on: false })));
    const l = parseTopbarLayout(saved, DOM);
    expect(ids(l).slice(-2)).toEqual(["btn-new", "btn-files"]); // 끝에 · html 순서대로
    expect(l.slice(-2).every((x) => x.on)).toBe(true);
    expect(ids(l).length).toBe(DOM.length);
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
    expect(l[0]).toEqual({ id: "btn-new", on: true });
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
    expect(ids(moveTopbarItem(l, "btn-theme", -1)).slice(-2)).toEqual(["btn-theme", "btn-factory-reset"]);
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
    expect(ids(d).slice(0, 2)).toEqual(["btn-equalize", "btn-feedback"]);
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
    expect(visibleTopbarIds(d).length).toBe(6);
  });
});

describe("끌어 놓기 결과 = 순서", () => {
  const l = defaultTopbarLayout(DOM);
  it("다른 줄의 앞·뒤에 놓는다(아래 → 위 · 위 → 아래)", () => {
    expect(ids(dropTopbarItem(l, "btn-restart-daemon", "btn-feedback", false)).slice(0, 3)).toEqual(["btn-feedback", "btn-restart-daemon", "btn-equalize"]);
    expect(ids(dropTopbarItem(l, "btn-restart-daemon", "btn-feedback", true)).slice(0, 2)).toEqual(["btn-restart-daemon", "btn-feedback"]);
    expect(ids(dropTopbarItem(l, "btn-feedback", "btn-theme", false)).at(-1)).toBe("btn-feedback");
    expect(ids(dropTopbarItem(l, "btn-feedback", "btn-theme", true)).slice(-2)).toEqual(["btn-feedback", "btn-theme"]);
  });

  it("제자리(바로 뒤 줄의 앞 · 바로 앞 줄의 뒤)·자기 위·없는 id = 순서 그대로", () => {
    expect(dropTopbarItem(l, "btn-feedback", "btn-equalize", true)).toEqual(l);
    expect(dropTopbarItem(l, "btn-equalize", "btn-feedback", false)).toEqual(l);
    expect(dropTopbarItem(l, "btn-feedback", "btn-feedback", true)).toEqual(l);
    expect(dropTopbarItem(l, "btn-nope", "btn-feedback", true)).toEqual(l);
    expect(dropTopbarItem(l, "btn-feedback", "btn-nope", true)).toEqual(l);
  });

  it("어떤 조합으로 옮겨도 단추가 늘거나 줄거나 켬끔이 바뀌지 않는다(11×11×2 전수 + ▲▼ 잇기)", () => {
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
