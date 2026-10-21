// 상단 단추(#topbar) 켬끔·순서의 순수 계산 — 저장 형식·기본값·손상 폴백·순서 이동.
// TICKET=cysr-1110-screen-settings · 박사님 2026-10-12 「메뉴 목록을 보여주고 켜기/끄기 버튼을 두는 것이다. 순서로 마음대로 조정할 수 있도록」.
//
// main.ts 의 화면 설정 팝오버(② 상단 단추 구획)와 시작 시 복원이 이 함수들에 배선만 한다
// (DOM·localStorage 는 호출측). 순수 함수라 저장·복원·손상·새 단추·경계를 결정론으로 잰다(topbarlayout.test.ts).
//
// ★숨김 = 보이는 것만 치운다. 단추 요소·누름 처리기·단축키(⌘T·⌘D·⌘W)·팔레트·창 머리 × 는 그대로다
//   (main.ts 는 hidden 속성만 바꾼다 — 요소를 지우지 않는다).

export const TOPBAR_LAYOUT_KEY = "cys-topbar-layout";
export const TOPBAR_LAYOUT_VERSION = 1;

// 저장 형식(version 1): {"version":1,"items":[{"id":"btn-feedback","on":true}, …]} — items 의 순서가 곧 화면 순서.
export interface TopbarItem {
  id: string;
  on: boolean;
}

// 고정 단추 — 끌 수 없다(순서만 바꾼다). 「화면 설정」을 끄면 다시 켤 길이 사라지고,
// 「Control Center」 는 승인 대기 배지·전문가 모드의 입구라 숨기면 승인 요청을 못 본다.
export const TOPBAR_PINNED: readonly string[] = ["btn-theme", "btn-cc"];

// 기본으로 꺼 두는 단추(처음 쓰는 사람·저장이 없거나 깨진 경우) — 박사님 확정 2026-10-12 09:1x 「최적안대로 한다」(A안 5개):
// + New · Split → · Split ↓ · 창 닫기 · 완전 초기화. 켜진 채 남는 것 = 피드백 · 상담소 · 아고라(cysr-menu-top-row 2026-10-21 사이드바에서 옮김) ·
// 정렬 · 파일 · Control Center · ↻ 재시작 · 화면 설정.
// ⛔이 집합을 바꾸는 것은 박사님 결정 사항이다. 윈에서는 터미널에 초점이 있을 때 단축키를 xterm 이 먹으므로, 창 만들기 세 단추의
//   보이는 길은 「화면 설정 → 상단 단추」 토글 하나다(index.html v116-recut-newsplit 주석) — 그 길(토글·「화면 설정」 고정)을 먼저 없애지 마라.
export const TOPBAR_DEFAULT_OFF: readonly string[] = ["btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-factory-reset"];

export const isTopbarPinned = (id: string): boolean => TOPBAR_PINNED.includes(id);

// 기본 배치 — 순서 = index.html 의 단추 순서(domIds), 켬끔 = TOPBAR_DEFAULT_OFF 만 끔.
export function defaultTopbarLayout(domIds: readonly string[]): TopbarItem[] {
  return domIds.map((id) => ({ id, on: isTopbarPinned(id) || !TOPBAR_DEFAULT_OFF.includes(id) }));
}

// 저장 문자열 → 배치. domIds = 지금 화면(index.html)에 실제로 있는 단추 id(그 순서).
//   · 없음·JSON 아님·version ≠ 1·items 가 배열 아님·항목 모양이 틀림·아는 단추가 하나도 없음 = 기본값(손상·구판).
//   · 저장에는 있는데 화면에 없는 id(없어진 단추) = 버린다. 같은 id 두 번 = 앞의 것만.
//   · 화면에는 있는데 저장에 없는 id(나중에 생긴 단추) = **켠 채**, html 에서 **바로 앞 단추의 뒤**에 끼운다(맨 앞 단추면 맨 앞) —
//     새 단추가 조용히 숨지 않게 · 정한 자리 그대로 서게(cysr-menu-top-row 2026-10-21: 1.1.9 에서 순서를 저장한 사람에게도
//     상담소·아고라가 피드백 바로 뒤에 선다 — 종전 「끝에」 면 화면 설정 뒤 맨 오른쪽에 떨어졌다).
//   · 고정 단추는 저장값이 끔이어도 켬으로 읽는다.
export function parseTopbarLayout(raw: string | null | undefined, domIds: readonly string[]): TopbarItem[] {
  if (!raw) return defaultTopbarLayout(domIds);
  let v: unknown;
  try {
    v = JSON.parse(raw);
  } catch {
    return defaultTopbarLayout(domIds);
  }
  if (!v || typeof v !== "object" || Array.isArray(v)) return defaultTopbarLayout(domIds);
  const o = v as { version?: unknown; items?: unknown };
  if (o.version !== TOPBAR_LAYOUT_VERSION || !Array.isArray(o.items)) return defaultTopbarLayout(domIds);
  const out: TopbarItem[] = [];
  const seen = new Set<string>();
  for (const e of o.items as unknown[]) {
    if (!e || typeof e !== "object") return defaultTopbarLayout(domIds);
    const { id, on } = e as { id?: unknown; on?: unknown };
    if (typeof id !== "string" || typeof on !== "boolean") return defaultTopbarLayout(domIds);
    if (seen.has(id) || !domIds.includes(id)) continue;
    seen.add(id);
    out.push({ id, on: on || isTopbarPinned(id) });
  }
  if (!out.length) return defaultTopbarLayout(domIds);
  domIds.forEach((id, i) => {
    if (seen.has(id)) return;
    // 앞 단추는 이미 out 에 있다(저장에 있었거나 이 고리에서 먼저 끼웠다) — html 순서대로 돌기 때문이다.
    const at = i === 0 ? 0 : out.findIndex((it) => it.id === domIds[i - 1]) + 1;
    out.splice(at, 0, { id, on: true });
    seen.add(id);
  });
  return out;
}

export function serializeTopbarLayout(items: readonly TopbarItem[]): string {
  return JSON.stringify({ version: TOPBAR_LAYOUT_VERSION, items: items.map(({ id, on }) => ({ id, on })) });
}

// 켬끔 — 고정 단추는 끌 수 없다(무변경). 없는 id = 무변경. 언제나 새 배열.
export function setTopbarItemOn(items: readonly TopbarItem[], id: string, on: boolean): TopbarItem[] {
  return items.map((it) => (it.id === id ? { id, on: on || isTopbarPinned(id) } : { ...it }));
}

// ▲(-1)·▼(+1) 한 칸 이동 — 맨 위의 ▲·맨 아래의 ▼·없는 id = 무변경. 언제나 새 배열.
export function moveTopbarItem(items: readonly TopbarItem[], id: string, delta: -1 | 1): TopbarItem[] {
  const arr = items.map((it) => ({ ...it }));
  const i = arr.findIndex((it) => it.id === id);
  const j = i + delta;
  if (i < 0 || j < 0 || j >= arr.length) return arr;
  [arr[i], arr[j]] = [arr[j], arr[i]];
  return arr;
}
export function canMoveTopbarItem(items: readonly TopbarItem[], id: string, delta: -1 | 1): boolean {
  const i = items.findIndex((it) => it.id === id);
  return i >= 0 && i + delta >= 0 && i + delta < items.length;
}

// 끌어 놓기 — src 를 anchor 의 앞(before=true)/뒤에 놓는다. 자기 위·없는 id = 무변경. 언제나 새 배열.
export function dropTopbarItem(items: readonly TopbarItem[], srcId: string, anchorId: string, before: boolean): TopbarItem[] {
  const arr = items.map((it) => ({ ...it }));
  const si = arr.findIndex((it) => it.id === srcId);
  if (si < 0 || srcId === anchorId || !arr.some((it) => it.id === anchorId)) return arr;
  const [src] = arr.splice(si, 1);
  const ai = arr.findIndex((it) => it.id === anchorId);
  arr.splice(before ? ai : ai + 1, 0, src);
  return arr;
}

// 보이는 단추 id(화면 순서).
export const visibleTopbarIds = (items: readonly TopbarItem[]): string[] => items.filter((it) => it.on).map((it) => it.id);
