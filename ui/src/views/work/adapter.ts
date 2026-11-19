// (cysr-ui-slice1) 작업 화면 어댑터 — 지금 main.ts 화면(#body-row)을 등록 화면 꼴로 **얇게** 감싼다(P2-DESIGN §4-5).
//
// mount = 보이게 · unmount = 숨김(부수지 않음 — 좌석 런타임·xterm·출력 흐름·3초 고리 그대로). 작업 화면만은 「숨김 = 내리기」의 예외다.
// ⚠ #body-row 는 CSS 가 display:flex 라 [hidden] 이 먹지 않는다(index.html 의 #ws-expert 와 같은 함정) → style.display 로 숨긴다.
// (cysr-1116-s2 · §2-3 ㉢) hooks.shown = 보이게 한 **뒤**(미룬 좌석 런타임 만들기 · 크기 맞춤이 보이는 칸을 재게) · hooks.hidden = 숨긴 뒤(이제부터 입양 = 모형만).

import type { ViewInstance, ViewModule } from "../contract";

export interface WorkHooks {
  shown?(): void;
  hidden?(): void;
}

export function workView<S, A>(bodyRow: HTMLElement, viewHost: HTMLElement, hooks: WorkHooks = {}): ViewModule<S, A> {
  return {
    mount(): ViewInstance {
      bodyRow.style.display = "";
      viewHost.hidden = true;
      hooks.shown?.();
      return {
        unmount() {
          bodyRow.style.display = "none";
          viewHost.hidden = false;
          hooks.hidden?.();
        },
      };
    },
  };
}
