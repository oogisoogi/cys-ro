// ★④(1.1.7 · 원작자 C-06 restartplan.ts 의 우리 판 최소 단위) GUI 재기동 주입의 재시도 판단(순수 · DOM 무접촉).
//
// 데몬 초안 게이트(④)는 기계 본문 Text 를 **미제출 입력이 조금이라도 있는 줄**에서 거부한다
// (`[draft_gate:pending_input]`). 재기동 대상 좌석에는 죽은 에이전트가 남긴 **기계 잔여**만 있는 경우가
// 흔하고, 그 좌석에서 [재기동]이 막히면 안 된다. 그래서 그 거부 한 가지에만 `clear_first`(Ctrl-U 선정리 +
// 본문 + CR 원자)로 1회 재시도한다. 데몬 ClearFirst 팔이 **사람 초안**을 다시 검사하므로(human_draft 거부)
// 사람이 쓰던 글은 지워지지 않는다. clear_first 본문에는 개행을 붙이지 않는다 — 데몬이 CR 을 보낸다.
// 그 밖의 거부(사람 초안·화면 점유·타이핑 가드·ACL …)는 재시도하지 않고 원문을 그대로 보인다.

export type RestartRetry = { data: string; clearFirst: true };

export function restartRetryPlan(cmd: string, err: unknown): RestartRetry | null {
  const text = err instanceof Error ? err.message : typeof err === "string" ? err : String(err ?? "");
  return text.includes("[draft_gate:pending_input]") ? { data: cmd, clearFirst: true } : null;
}
