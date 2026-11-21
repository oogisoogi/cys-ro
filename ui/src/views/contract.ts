// (cysr-ui-slice1 · TICKET=cysr-ui-slice1-1117) 화면 등록 계약 — 타입만. 설계 = P2-DESIGN §4-1·§4-2.
//
// 새 화면은 ViewDescriptor 하나를 registry 목록에 넣는 것으로 꽂힌다. 화면은 데몬·파일·localStorage 를 직접 만지지 않고
// ctx.act(행동)와 ctx.subscribe(상태)만 쓴다(FR-X1). 전환 단추는 화면이 그리지 않는다 — registry 가 #view-switch 에 하나 그린다.

export interface MinimumContract {
  /** 확인 대기 수를 보이는 요소의 선택자(최소 계약 FR-X3) */
  confirms: string;
  /** 마지막 보낸 말 단계 */
  lastSendStep: string;
  /** 마스터 상태 */
  masterHealth: string;
  /** 오류 수 */
  errors: string;
  /** 화면 바꾸기 = 공통 자리(registry 가 그림) */
  switcher: "shared";
}

export type Avail = { ok: true } | { ok: false; why: string };

export interface ViewInstance {
  /** 내리기 — 자기가 만든 DOM·리스너 해제(구독·타이머는 registry 가 강제 해제) */
  unmount(): void;
  /** 화면만의 보기 상태(스크롤 등) — JSON 가능 값 */
  snapshot?(): unknown;
  restore?(s: unknown): void;
}

export interface ViewContext<S, A> {
  subscribe(fn: (s: S) => void): () => void;
  act: A;
  timers: { every(ms: number, fn: () => void): void };
}

export interface ViewModule<S, A> {
  mount(host: HTMLElement, ctx: ViewContext<S, A>): ViewInstance;
}

export interface ViewDescriptor<S, A> {
  /** "chat" | "work" | … — 저장 값 · 바꾸지 않음 */
  id: string;
  /** 단추 글 */
  label: string;
  order: number;
  minimum: MinimumContract;
  /** 이 기기에서 쓸 수 있나(긍정 신호가 있을 때만 불가 — §9-3) */
  available(): Promise<Avail>;
  load(): Promise<ViewModule<S, A>>;
  /** 작업 화면처럼 #view-host 밖에 사는 화면 = true(숨김 = 내리기 · 부수지 않음 §4-5) */
  outsideHost?: boolean;
}
