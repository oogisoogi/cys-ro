// 선택 끌기 mouseup 유실 방어 핀 — 단추를 뗀 뒤의 커서 이동이 터미널 선택을 늘리지 않게 하는 판단.
//
// ★왜 필요한가(TICKET=cysr-stuck-selection-drag · 박사님 영상 2026-10-28): xterm 5.5.0 SelectionService 는 mouseup 이
// 와야만 끌기를 끝내고 mousemove 에서 단추 상태를 보지 않는다 → 웹뷰가 mouseup 을 놓치면 클릭 없이 커서만 움직여도 선택이
// 커서를 따라 늘어난다. 실제 엔진 재현·수리 확인 = ui/e2e/selection_drag_gate.py(WebKit·Chromium).
import { describe, it, expect } from "bun:test";
import { armSelectionDragGuard } from "./selectiondrag";

type Fn = (e: any) => void;

/** 붙은 처리기를 기억하는 가짜 창 + 대신 뗀 기록. */
function rig() {
  const handlers = new Map<string, Fn>();
  const win = {
    addEventListener: (type: string, fn: Fn) => void handlers.set(type, fn),
    removeEventListener: (type: string) => void handlers.delete(type),
  };
  const released: { clientX: number; clientY: number }[] = [];
  const off = armSelectionDragGuard({
    win,
    isTerminal: (t) => t === "term",
    release: (at) => released.push(at),
  });
  const fire = (type: string, e: any = {}) => handlers.get(type)?.(e);
  return { win, handlers, released, off, fire };
}

const down = (target: unknown, x = 10, y = 10, button = 0) => ({ target, button, clientX: x, clientY: y });
const move = (x: number, y: number, buttons: number) => ({ clientX: x, clientY: y, buttons });

describe("armSelectionDragGuard — 놓친 뗌을 대신 보낸다", () => {
  it("정상 끌기(누름 → 눌린 채 이동 → 뗌 → 이동)에는 끼어들지 않는다", () => {
    const r = rig();
    r.fire("mousedown", down("term"));
    r.fire("mousemove", move(20, 40, 1));
    r.fire("mouseup");
    r.fire("mousemove", move(30, 90, 0));
    expect(r.released).toEqual([]);
  });

  it("뗌을 놓친 채 단추 없이 움직이면 — 마지막으로 눌린 채 있던 자리에서 한 번 뗀다", () => {
    const r = rig();
    r.fire("mousedown", down("term", 10, 10));
    r.fire("mousemove", move(20, 40, 1));
    r.fire("mousemove", move(30, 90, 0)); // 뗌 유실 뒤 첫 이동
    r.fire("mousemove", move(40, 120, 0));
    expect(r.released).toEqual([{ clientX: 20, clientY: 40 }]);
  });

  it("뗌을 놓친 채 다시 누르면 — 새 누름을 받기 전에 앞 끌기를 끝낸다(xterm 고아 타이머 방지)", () => {
    const r = rig();
    r.fire("mousedown", down("term", 10, 10));
    r.fire("mousedown", down("term", 50, 50));
    expect(r.released).toEqual([{ clientX: 10, clientY: 10 }]);
    r.fire("mousemove", move(60, 60, 0)); // 두 번째 누름도 뗌 유실 → 그 자리에서 끝
    expect(r.released).toEqual([{ clientX: 10, clientY: 10 }, { clientX: 50, clientY: 50 }]);
  });

  it("창이 초점을 잃으면 끝낸다 · 요소 blur(대상이 창이 아님)는 무시", () => {
    const r = rig();
    r.fire("mousedown", down("term", 5, 6));
    r.fire("blur", { target: "textarea" });
    expect(r.released).toEqual([]);
    r.fire("blur", { target: r.win });
    expect(r.released).toEqual([{ clientX: 5, clientY: 6 }]);
    r.fire("blur", { target: r.win }); // 이미 끝남 — 두 번 떼지 않는다
    expect(r.released.length).toBe(1);
  });

  it("터미널 밖 누름·오른쪽 단추 누름은 지켜보지 않는다(다른 끌기 처리기는 각자 처리)", () => {
    const r = rig();
    r.fire("mousedown", down("sidebar"));
    r.fire("mousemove", move(1, 1, 0));
    r.fire("mousedown", down("term", 1, 1, 2));
    r.fire("mousemove", move(2, 2, 0));
    r.fire("blur", { target: r.win });
    expect(r.released).toEqual([]);
  });

  it("대신 뗀 뒤 그 합성 mouseup 이 다시 지나가도 되풀이하지 않는다", () => {
    const handlers = new Map<string, Fn>();
    const win = {
      addEventListener: (type: string, fn: Fn) => void handlers.set(type, fn),
      removeEventListener: () => {},
    };
    let n = 0;
    armSelectionDragGuard({
      win,
      isTerminal: () => true,
      release: () => {
        n++;
        handlers.get("mouseup")?.({}); // main.ts 는 document 에 합성 mouseup 을 보낸다 → 창 capture 를 다시 지난다
      },
    });
    handlers.get("mousedown")?.(down("term"));
    handlers.get("mousemove")?.(move(3, 3, 0));
    handlers.get("mousemove")?.(move(4, 4, 0));
    expect(n).toBe(1);
  });

  it("떼어 내면 처리기 4개가 모두 빠진다", () => {
    const r = rig();
    expect([...r.handlers.keys()].sort()).toEqual(["blur", "mousedown", "mousemove", "mouseup"]);
    r.off();
    expect(r.handlers.size).toBe(0);
  });
});
