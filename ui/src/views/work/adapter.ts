// (cysr-ui-slice1) 작업 화면 어댑터 — 지금 main.ts 화면(#body-row)을 등록 화면 꼴로 **얇게** 감싼다(P2-DESIGN §4-5).
//
// mount = 보이게 · unmount = 숨김(부수지 않음 — 좌석 런타임·xterm·출력 흐름·3초 고리 그대로). 작업 화면만은 「숨김 = 내리기」의 예외다.
// ⚠ #body-row 는 CSS 가 display:flex 라 [hidden] 이 먹지 않는다(index.html 의 #ws-expert 와 같은 함정) → style.display 로 숨긴다.
// (s79 조각 9) extra = 작업 화면이 켜져 있는 동안만 붙는 덧붙임(확인 띠·초안 알림 띠) — 붙이고 떼는 함수만 받는다(작업 화면 본체 무변경).
// (cysr-1116-s2 · §2-3 ㉢) hooks.shown = 보이게 한 **뒤**(미룬 좌석 런타임 만들기 · 크기 맞춤이 보이는 칸을 재게) · hooks.hidden = 숨긴 뒤(이제부터 입양 = 모형만).
// (cysr-1116-integ-1120 통합) 두 갈래 인자를 한 객체로 받는다 — shown/hidden(s2) 과 mount(s79) 는 서로 독립 · 순서 = 보이게 → shown → mount / 떼기 → 숨김 → hidden.

import type { ViewContext, ViewInstance, ViewModule } from "../contract";

export interface WorkExtra<S, A> {
  /** 작업 화면이 켜질 때 — 떼는 함수를 돌려준다 */
  mount(ctx: ViewContext<S, A>): () => void;
}

export interface WorkHooks {
  shown?(): void;
  hidden?(): void;
}

export function workView<S, A>(bodyRow: HTMLElement, viewHost: HTMLElement, hooks: WorkHooks & Partial<WorkExtra<S, A>> = {}): ViewModule<S, A> {
  return {
    mount(_host: HTMLElement, ctx: ViewContext<S, A>): ViewInstance {
      bodyRow.style.display = "";
      viewHost.hidden = true;
      hooks.shown?.();
      let off: (() => void) | null = null;
      try {
        off = hooks.mount ? hooks.mount(ctx) : null;
      } catch {
        off = null; // 덧붙임이 깨져도 작업 화면은 그대로 뜬다
      }
      return {
        unmount() {
          try {
            off?.();
          } catch {
            /* 떼기 실패도 작업 화면 숨김을 막지 않는다 */
          }
          bodyRow.style.display = "none";
          viewHost.hidden = false;
          hooks.hidden?.();
        },
      };
    },
  };
}
