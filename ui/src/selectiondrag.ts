// 터미널 선택 끌기의 「뗌(mouseup) 유실」 방어 — 창 하나에 한 번 건다(최상위 부수효과 0 · 창·끝내기는 인자로 받는다).
//
// ★왜 있는가(TICKET=cysr-stuck-selection-drag · 박사님 영상 2026-10-28 22:53 「클릭 없이 커서만 움직였는데
// 선택 블록이 커서를 따라 늘어난다 · 예전부터 계속 있었다」):
//   xterm 5.5.0 SelectionService 는 mousedown 때 document 에 mousemove·mouseup 처리기를 붙이고 **mouseup 이 와야만**
//   뗀다. _handleMouseMove 는 event.buttons 를 보지 않는다 → 웹뷰가 mouseup 한 번을 못 받으면(창 밖에서 뗌·앱 전환 등)
//   단추를 뗀 뒤의 모든 커서 이동이 선택 끝점을 옮긴다(영상 증상). 그 상태에서 새로 누르면 xterm 이 끌기 스크롤 타이머를
//   덮어써 옛 타이머가 고아로 남는다(SelectionService._addMouseDownListeners).
//   재현 = ui/e2e/selection_drag_gate.py B 칸(같은 판 순수 xterm 대조군 · 실제 앱 번들 둘 다 재현 · 정상 뗌이면 둘 다 0).
//
// 고치는 법: 터미널 위에서 누른 뒤 「단추가 떼어진 채 움직임」·「창 초점 잃음」·「뗌 없이 새 누름」 중 하나를 보면 mouseup 을
// 놓친 것으로 보고, 마지막으로 눌린 채 있던 자리에서 뗌을 대신 보낸다(release). 선택은 지우지 않는다 — 뗀 것처럼 끝난다.
// 상단바 끌기(main.ts showTopbarEditor)의 `!(e.buttons & 1)` 취소와 같은 판단이다.

type Listen = {
  addEventListener(type: string, fn: (e: any) => void, opts?: boolean | AddEventListenerOptions): void;
  removeEventListener(type: string, fn: (e: any) => void, opts?: boolean | EventListenerOptions): void;
};

export interface SelectionDragGuardDeps {
  /** 처리기를 붙일 창(capture 로 듣는다 — xterm 의 document 처리기보다 먼저 판단한다). */
  win: Listen;
  /** 누른 곳이 터미널(xterm) 안인가. */
  isTerminal: (target: unknown) => boolean;
  /** 놓친 뗌을 대신 보낸다(main.ts = document 에 합성 mouseup). 좌표는 마지막으로 눌린 채 있던 자리. */
  release: (at: { clientX: number; clientY: number }) => void;
}

/** 방어를 건다. 돌려주는 함수로 뗀다(시험용). */
export function armSelectionDragGuard(deps: SelectionDragGuardDeps): () => void {
  let pressed: { clientX: number; clientY: number } | null = null;
  // 대신 떼기 — 표지를 먼저 지운다(합성 mouseup 이 아래 onUp 을 다시 지나도 되돌아오지 않게).
  const lost = () => {
    const at = pressed;
    pressed = null;
    if (at) deps.release(at);
  };
  const onDown = (e: MouseEvent) => {
    if (pressed) lost(); // 뗌 없이 새 누름 = 앞 누름의 mouseup 을 놓쳤다 → xterm 이 새 누름을 받기 전에 끝낸다
    if (e.button === 0 && deps.isTerminal(e.target)) pressed = { clientX: e.clientX, clientY: e.clientY };
  };
  const onMove = (e: MouseEvent) => {
    if (!pressed) return;
    if (!(e.buttons & 1)) return lost(); // 단추가 떼어진 채 움직인다 = mouseup 을 놓쳤다
    pressed = { clientX: e.clientX, clientY: e.clientY };
  };
  const onUp = () => {
    pressed = null;
  };
  // 창 밖에서 뗐으면 mouseup 이 안 올 수 있다 — 창이 초점을 잃으면 끝낸다(요소 blur 는 창까지 오르지 않는다).
  const onBlur = (e: Event) => {
    if (e.target === deps.win) lost();
  };
  deps.win.addEventListener("mousedown", onDown, true);
  deps.win.addEventListener("mousemove", onMove, true);
  deps.win.addEventListener("mouseup", onUp, true);
  deps.win.addEventListener("blur", onBlur);
  return () => {
    deps.win.removeEventListener("mousedown", onDown, true);
    deps.win.removeEventListener("mousemove", onMove, true);
    deps.win.removeEventListener("mouseup", onUp, true);
    deps.win.removeEventListener("blur", onBlur);
  };
}
