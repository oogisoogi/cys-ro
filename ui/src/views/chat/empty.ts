// (TICKET=cysr-1119-s5 · CV-EX3 = 시각 카드 V10) 대화 화면 빈 상태 — 제목 · 안내 · 예시 단추 3(P2 S0 꼴 · DESIGN §4-2).
//
// 예시 글 = P2-mock `app.js:7-13` 그대로. 누르면 입력칸에 그 글을 넣기만 한다(보내지 않음 · 데몬 호출 0).
// 쓰던 글이 있으면 덮지도 앞에 넣지도 않는다(그대로 두고 예시 무시). 글은 textContent 만.

/** 예시 3줄(P2-mock 글 그대로). */
export const CHAT_EXAMPLES: readonly string[] = ["교회 추수감사 행사 안내 페이지 만들어 줘", "이번 주 주보 PDF 정리해 줘", "다음 달 교사 모임 일정을 표로 만들어 줘"];
export const EMPTY_TITLE = "마스터에게 맡길 일을 적어 주세요";
export const EMPTY_GUIDE = "이렇게 말해 보세요(누르면 입력칸에 들어가요)";

interface DraftInput {
  value: string;
  focus(): void;
  setSelectionRange(a: number, b: number): void;
}

/** 예시 넣기 — 입력칸이 비었을 때만(공백뿐도 빈 것) · 넣었으면 true. 보내지 않는다(setDraft = 초안 기억만). */
export function applyExample(input: DraftInput, act: { setDraft(t: string): void }, ex: string): boolean {
  if (input.value.trim() !== "") return false;
  input.value = ex;
  act.setDraft(ex);
  input.focus();
  input.setSelectionRange(ex.length, ex.length);
  return true;
}

/** 빈 상태 목록 칸(li.cv-empty) — onPick(예시 글) 은 그리기 쪽이 applyExample 로 잇는다. */
export function createEmpty(onPick: (ex: string) => void): HTMLLIElement {
  const li = document.createElement("li");
  li.className = "cv-empty";
  const h = document.createElement("div");
  h.className = "cv-empty-title";
  h.textContent = EMPTY_TITLE;
  const g = document.createElement("div");
  g.className = "cv-empty-guide";
  g.textContent = EMPTY_GUIDE;
  const box = document.createElement("div");
  box.className = "cv-ex";
  for (const ex of CHAT_EXAMPLES) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cv-ex-btn";
    b.textContent = ex;
    b.addEventListener("click", () => onPick(ex));
    box.append(b);
  }
  li.append(h, g, box);
  return li;
}
