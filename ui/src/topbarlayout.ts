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
// ★(1.1.15 · tabs-sidebar 1e · 박사님 11-11 09:4x 「콘트롤 센터는 권고대로 하겠다」) Control Center 는 고정에서 풀고 기본 끔으로 옮겼다 —
//   승인 대기 배지·좌석 상태는 왼쪽 막대 상황판이 넘겨받았고, 여는 길 = 「화면 설정」 「컨트롤 센터 열기」 + 말. 켜면 지금 그대로다.
export const TOPBAR_PINNED: readonly string[] = ["btn-theme"];

// 기본으로 꺼 두는 단추(처음 쓰는 사람·저장이 없거나 깨진 경우) — 박사님 확정 2026-10-12 09:1x 「최적안대로 한다」(A안 5개):
// + New · Split → · Split ↓ · 창 닫기 · 완전 초기화. 켜진 채 남는 것 = 피드백 · 상담소 · 아고라(cysr-menu-top-row 2026-10-21 사이드바에서 옮김) ·
// 정렬 · 파일 · Control Center · ↻ 재시작 · 화면 설정. (1.1.19: 정렬·파일 = 아래 두 상수 · 박사님 11-24 결정)
// ⛔이 집합을 바꾸는 것은 박사님 결정 사항이다. 윈에서는 터미널에 초점이 있을 때 단축키를 xterm 이 먹으므로, 창 만들기 세 단추의
//   보이는 길은 「화면 설정 → 상단 단추」 토글 하나다(index.html v116-recut-newsplit 주석) — 그 길(토글·「화면 설정」 고정)을 먼저 없애지 마라.
// ★(cysr-1119-s10b · DESIGN §2-3 · §8-3 MD-T7 · §8-4 MD-T4 · 박사님 11-24 09:4x 「결제하고 권고대로 한다.」) 정렬·파일 두 단추는 빌드 상수
//   **값**으로 갈린다(두 안 모두 동작 · 바꾸려면 상수 한 줄). 정렬: keep = 1.1.18 그대로 · dim = 켬 + 흐린 글자 · fold = 기본 끔(⌘K 「패널 균등화」 그대로).
//   파일: on = 1.1.18 그대로 · off = 기본 끔 + 순서를 저장한 기기도 한 번만 끔(FILES_BTN_OFF_ONCE_KEY · 다시 켜면 유지).
export type SortButtonMode = "keep" | "dim" | "fold";
export type FilesButtonDefault = "on" | "off";
export const SORT_BUTTON_MODE: SortButtonMode = "fold";
export const FILES_BUTTON_DEFAULT: FilesButtonDefault = "off";
const TOPBAR_DEFAULT_OFF_BASE: readonly string[] = ["btn-new", "btn-split-h", "btn-split-v", "btn-close", "btn-factory-reset", "btn-cc"];
export function topbarDefaultOff(sort: SortButtonMode, files: FilesButtonDefault): string[] {
  return [...TOPBAR_DEFAULT_OFF_BASE, ...(sort === "fold" ? ["btn-equalize"] : []), ...(files === "off" ? ["btn-files"] : [])];
}
export const TOPBAR_DEFAULT_OFF: readonly string[] = topbarDefaultOff(SORT_BUTTON_MODE, FILES_BUTTON_DEFAULT);
// (MD-T9) ↻ 재시작 = 마지막 밸브라 남기되 무게만 낮춘다(흐린 글자 · 확인 창 그대로) · 정렬은 dim 일 때만 흐림.
export function topbarDimIds(sort: SortButtonMode): string[] {
  return [...(sort === "dim" ? ["btn-equalize"] : []), "btn-restart-daemon"];
}

// (1e) 저장된 배치가 있는 사람(1.1.14 이하에서 순서를 고친 사람)에게도 Control Center 를 한 번 끈다 — 표지 열쇠로 1회만.
//   그 뒤 사람이 다시 켜면 그대로 둔다(표지가 있으니 다시 끄지 않는다).
export const CC_BTN_OFF_ONCE_KEY = "cys-cc-btn-off-115";
export function ccButtonOffOnce(items: readonly TopbarItem[], done: boolean): { items: TopbarItem[]; changed: boolean } {
  if (done || !items.some((it) => it.id === "btn-cc" && it.on)) return { items: items.map((it) => ({ ...it })), changed: false };
  return { items: items.map((it) => (it.id === "btn-cc" ? { id: it.id, on: false } : { ...it })), changed: true };
}

// (MD-T7) 파일 단추 한 번만 끄기 — CC 1e 와 같은 꼴(표지 1회 · 그 뒤 사람이 켜면 그대로). on 이면 언제나 무변경.
export const FILES_BTN_OFF_ONCE_KEY = "cys-files-btn-off-119";
export function filesButtonOffOnce(items: readonly TopbarItem[], done: boolean, mode: FilesButtonDefault = FILES_BUTTON_DEFAULT): { items: TopbarItem[]; changed: boolean } {
  if (mode !== "off" || done || !items.some((it) => it.id === "btn-files" && it.on)) return { items: items.map((it) => ({ ...it })), changed: false };
  return { items: items.map((it) => (it.id === "btn-files" ? { id: it.id, on: false } : { ...it })), changed: true };
}

export const isTopbarPinned = (id: string): boolean => TOPBAR_PINNED.includes(id);

// 기본 배치 — 순서 = index.html 의 단추 순서(domIds), 켬끔 = TOPBAR_DEFAULT_OFF 만 끔.
export function defaultTopbarLayout(domIds: readonly string[], off: readonly string[] = TOPBAR_DEFAULT_OFF): TopbarItem[] {
  return domIds.map((id) => ({ id, on: isTopbarPinned(id) || !off.includes(id) }));
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
