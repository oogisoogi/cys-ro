// (TICKET=cysr-1119-s5 · V6) 대화 목록 스크롤 판정 — 순수. DESIGN §6 V6 · VISUAL §4 카드 V6.
//
// 맨 아래에 붙어 있음 = 바닥까지 48px 안(오르카 `native-chat-autoscroll.ts` 48px · 1.1.18 은 4px).
// 붙어 있으면: 새 마스터 답이 보이는 칸보다 길면 **그 답 첫 줄이 칸 위쪽**에 오게(ChatGPT 2024-11-22 릴리스 노트) · 짧으면 맨 아래.
// 붙어 있지 않으면: 위치를 지키고 새 답 수만 센다(「↓ 새 답 N · 맨 아래로」 단추).
// 셈 = 그리기 횟수가 아니라 마스터 답 열쇠 집합의 차(기록 박자 C 가 그리기를 늘려도 같은 값).
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지(views 정적 핀).

/** 바닥 붙음 문턱(px). */
export const STICK_PX = 48;
/** 긴 새 답의 첫 줄을 칸 위에서 띄우는 여백(px · 합격 = 위 24px 안). */
export const TOP_GAP_PX = 12;

export interface ScrollGeom {
  scrollTop: number;
  clientHeight: number;
  scrollHeight: number;
}

/** 바닥까지 threshold 안이면 붙어 있음. */
export function stickToBottom(g: ScrollGeom, threshold: number = STICK_PX): boolean {
  return g.scrollTop + g.clientHeight >= g.scrollHeight - threshold;
}

/** 이번 그리기에서 처음 본 답 열쇠(나온 순서 그대로). seen = 앞에서 본 열쇠. */
export function newKeys(seen: ReadonlySet<string>, keys: readonly string[]): string[] {
  return keys.filter((k) => !seen.has(k));
}

/**
 * 다시 그린 뒤 둘 스크롤 위치.
 * stuck = 그리기 전 바닥에 붙어 있었나 · prevTop = 그리기 전 scrollTop · first = 새 답 중 첫 것의 칸 안 위치(top = 목록 맨 위에서 · height) · 없으면 null.
 */
export function placeAfterPaint(stuck: boolean, prevTop: number, after: ScrollGeom, first: { top: number; height: number } | null): number {
  const bottom = Math.max(0, after.scrollHeight - after.clientHeight);
  if (!stuck) return Math.min(prevTop, bottom); // 위를 읽는 중 = 위치 불변
  if (first && first.height > after.clientHeight) return Math.min(bottom, Math.max(0, first.top - TOP_GAP_PX)); // 긴 새 답 = 첫 줄이 위
  return bottom;
}

/** 단추 글(새 문구 · master 확인 대상). n ≤ 0 = 단추 숨김(null). */
export function jumpLabel(n: number): string | null {
  return n > 0 ? `↓ 새 답 ${n} · 맨 아래로` : null;
}
