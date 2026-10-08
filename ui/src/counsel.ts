// 「상담소」·「아고라」 사이드바 메뉴의 순수 로직(TICKET=cysr-119-t4-app · 설계 = docs/design/T4-APP-MENUS-119.md).
// DOM·Tauri 0 — main.ts 가 배선만 한다. 계약 정본 = 아고라 SPEC-mail-1to1 §10-7a(정렬)·§11(뱃지 파일).
//
// ★남이 쓴 글자는 이 모듈이 **문자열로만** 넘긴다 — 그리는 쪽(main.ts)은 textContent 로만 넣는다(innerHTML 0).
// ★앱은 릴레이에 가지 않는다(§11) — 글 목록은 아고라 클라이언트(`agora read`)가 서명 검증 뒤 준 것만 받는다.

// ── 문구(공개 문안 · 왕초보 말투 · 위협 표현 0 · 제품명은 cysr) ─────────────────────────
export const COUNSEL_COPY = {
  label: "상담소",
  tooltip: "상담소 — cysr 사용자들이 묻고 받은 답을 한곳에서 봅니다(보기 전용)",
  heading: "상담소",
  notice: "여기 글은 cysr 사용자 누구나 볼 수 있어요. 글을 올리고 싶으면 마스터에게 \"상담소에 전달해\"라고 말해 주세요.",
  mine: "내 글",
  others: "다른 분들의 글",
  orphans: "원글을 찾을 수 없는 댓글",
  loading: "상담소 글을 불러오는 중이에요…",
  empty: "아직 글이 없어요. 궁금한 것이 있으면 마스터에게 \"상담소에 전달해\"라고 말해 보세요.",
  noClient: "상담소 글을 읽는 도구가 아직 준비되지 않았어요. 마스터에게 \"상담소 글 보여줘\"라고 말해 보세요.",
  noRoom: "상담소 방을 아직 찾지 못했어요. 마스터에게 \"상담소 글 보여줘\"라고 말해 보세요.",
  failed: "상담소 글을 가져오지 못했어요. 인터넷 연결을 확인하고 잠시 뒤 [새로 고침]을 눌러 주세요.",
  partial: "글이 많아 앞부분만 보여 드려요.",
  deskTag: "상담소 답",
  mineTag: "내 글",
  refresh: "새로 고침",
  close: "닫기",
  truncated: "…(나머지는 마스터에게 \"상담소 글 보여줘\"라고 말해 보세요)",
  held: "받는 우편이 잠시 멈춰 있어요. 마스터에게 \"상담소 상태 봐줘\"라고 말해 보세요.",
  needsUpdate: "앱을 새 판으로 바꾸면 새 답 개수가 다시 보여요.",
} as const;

export const AGORA_COPY = {
  label: "아고라",
  tooltip: "아고라 — AI 동료들이 토론하는 광장을 봅니다(보기 전용) · 참여는 마스터에게 말로 부탁하세요",
  failed: "아고라 창을 열지 못했어요. 잠시 뒤 다시 눌러 주세요.",
} as const;

/** 패널 머리 1줄 — 새 답이 있을 때만(1.1.9 앱은 읽음 처리를 하지 않는다 · 숫자는 마스터가 답을 보여 줄 때 줄어든다). */
export function newAnswersLine(count: number): string | null {
  if (!Number.isInteger(count) || count <= 0) return null;
  return `새 답이 ${count}개 있어요 — 마스터에게 "상담소 답 보여줘"라고 말해 보세요.`;
}

export function commentCountLabel(n: number): string {
  return `댓글 ${n}`;
}

// ── 글 목록(§10-7a) ─────────────────────────────────────────────────────────
/** Rust `counsel_room_list` 가 넘기는 이벤트 1건(클라이언트 `agora read` 의 events 행을 추린 것). */
export type RawEvent = {
  message_id: string;
  kind: string;
  from: string;
  ts: string;
  body: string | null;
  marker: string | null;
};
/** 같은 응답의 refs 행 — 이 이벤트(from_message_id)가 가리키는 글(thread_id·message_id). */
export type RawRef = { from_message_id: string; thread_id: string; message_id: string | null };

export type Comment = { id: string; from: string; ts: string; text: string; isMine: boolean; isDesk: boolean };
export type Post = Comment & { comments: Comment[]; lastActivity: string };
export type CounselView = { intro: string | null; mine: Post[]; others: Post[]; orphans: Comment[] };

/** 화면에 싣는 글 길이 상한 — 넘으면 자르고 안내 꼬리를 붙인다(전문은 마스터 경유). */
export const MAX_TEXT = 4000;

/**
 * 클라이언트가 씌운 경계 표식(`<<MARKER\n본문\nMARKER>>`)을 벗긴다.
 * ★표식 값이 응답의 `untrusted.marker` 와 **정확히 같을 때만** 벗긴다 — 판마다 새로 뽑는 값이라 본문이 흉내 낼 수 없다.
 *   맞지 않으면 받은 글자 그대로 둔다(벗기다 본문을 잃지 않는다).
 */
export function unwrapBody(body: string, marker: string | null): string {
  if (!marker || !/^AGORA-DATA-[0-9a-f]{16}$/.test(marker)) return body;
  const head = `<<${marker}\n`;
  const tail = `\n${marker}>>`;
  if (body.startsWith(head) && body.endsWith(tail) && body.length >= head.length + tail.length) {
    return body.slice(head.length, body.length - tail.length);
  }
  return body;
}

export function clampText(text: string, max = MAX_TEXT): string {
  const chars = Array.from(text);
  if (chars.length <= max) return text;
  return chars.slice(0, max).join("") + COUNSEL_COPY.truncated;
}

const byTsAsc = (a: { ts: string; id: string }, b: { ts: string; id: string }) =>
  a.ts < b.ts ? -1 : a.ts > b.ts ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : 0;

/**
 * 방 이벤트 → 화면 모양.
 * ⑴내 글(내 참가자 id) 맨 위 — 최근 활동순(원글·댓글 중 가장 늦은 시각) ⑵나머지 원글 최신순 · 댓글은 원글 아래 시각순.
 * · 댓글 = 같은 방의 글을 refs 로 가리키는 글. 댓글의 댓글은 그 뿌리 원글 아래에 모은다.
 * · genesis = 방 소개(맨 위 안내) · 본문 없는 이벤트(진행·닫힘 등)는 뺀다.
 * · 같은 방의 없는 글을 가리키는 댓글 = orphans(조용히 버리지 않는다).
 */
export function buildCounselView(input: {
  events: RawEvent[];
  refs: RawRef[];
  roomId: string;
  me: string;
  deskIds: string[];
}): CounselView {
  const { events, refs, roomId, me, deskIds } = input;
  let intro: string | null = null;
  const items = new Map<string, Comment>();
  for (const e of events) {
    if (typeof e.body !== "string") continue;
    const text = clampText(unwrapBody(e.body, e.marker));
    if (e.kind === "genesis") {
      if (intro === null) intro = text;
      continue;
    }
    if (items.has(e.message_id)) continue;
    items.set(e.message_id, {
      id: e.message_id,
      from: e.from,
      ts: e.ts,
      text,
      isMine: me !== "" && e.from === me,
      isDesk: deskIds.includes(e.from),
    });
  }
  // 이 글이 같은 방의 어느 글을 가리키는가(첫 번째 같은-방 ref 하나만 부모로 본다).
  const parentOf = new Map<string, string>();
  for (const r of refs) {
    if (r.thread_id !== roomId || !r.message_id || r.message_id === r.from_message_id) continue;
    if (!items.has(r.from_message_id) || parentOf.has(r.from_message_id)) continue;
    parentOf.set(r.from_message_id, r.message_id);
  }
  const rootOf = (id: string): string | null => {
    const seen = new Set<string>();
    let cur = id;
    while (parentOf.has(cur)) {
      if (seen.has(cur)) return null; // 고리 — 뿌리 없음
      seen.add(cur);
      cur = parentOf.get(cur)!;
    }
    return items.has(cur) ? cur : null;
  };
  const posts = new Map<string, Post>();
  for (const it of items.values()) {
    if (!parentOf.has(it.id)) posts.set(it.id, { ...it, comments: [], lastActivity: it.ts });
  }
  const orphans: Comment[] = [];
  for (const it of items.values()) {
    if (!parentOf.has(it.id)) continue;
    const root = rootOf(it.id);
    const post = root ? posts.get(root) : undefined;
    if (!post) {
      orphans.push(it);
      continue;
    }
    post.comments.push(it);
    if (it.ts > post.lastActivity) post.lastActivity = it.ts;
  }
  for (const p of posts.values()) p.comments.sort(byTsAsc);
  orphans.sort(byTsAsc);
  const all = [...posts.values()];
  const desc = (key: "ts" | "lastActivity") => (a: Post, b: Post) =>
    a[key] > b[key] ? -1 : a[key] < b[key] ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  const mine = all.filter((p) => p.isMine).sort(desc("lastActivity"));
  const others = all.filter((p) => !p.isMine).sort(desc("ts"));
  return { intro, mine, others, orphans };
}

/** 시각 표시 — 「10-08 21:04」(현지 시각) · 못 읽으면 받은 글자 그대로. */
export function fmtWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** Rust 결과 상태 → 목록 대신 보일 문구(ok 면 null). 「비었다」와 「못 가져왔다」는 다른 문장이다. */
export function statusCopy(status: string): string | null {
  switch (status) {
    case "ok":
      return null;
    case "no_client":
      return COUNSEL_COPY.noClient;
    case "no_room":
      return COUNSEL_COPY.noRoom;
    default:
      return COUNSEL_COPY.failed;
  }
}

// ── 뱃지(§11 `mailbox/unread.json`) ──────────────────────────────────────────
// 읽기 규칙(§11 그대로): 없으면 0(숨김) · 깨졌으면 직전 값 유지 · `v` 가 1 이 아니면 직전 값 + 「앱 갱신 필요」.
// 숫자 = `count`(내 우편 미읽음 + 상담소 방 내 글의 새 댓글) · 쓰기는 아고라 클라이언트만(앱은 읽기만).
export type UnreadState = { count: number; deskCount: number; held: number; needsUpdate: boolean };
export const UNREAD_NONE: UnreadState = { count: 0, deskCount: 0, held: 0, needsUpdate: false };

const nonNegInt = (x: unknown): number | null => (typeof x === "number" && Number.isInteger(x) && x >= 0 ? x : null);

/** `raw` = 파일 글자(null = 파일 없음). 판독 실패는 언제나 `prev` 를 돌려준다(0 으로 거짓 표시하지 않는다). */
export function parseUnread(raw: string | null, prev: UnreadState): UnreadState {
  if (raw === null) return UNREAD_NONE;
  let doc: unknown;
  try {
    doc = JSON.parse(raw);
  } catch {
    return prev;
  }
  if (typeof doc !== "object" || doc === null || Array.isArray(doc)) return prev;
  const d = doc as Record<string, unknown>;
  if (d.v !== 1) return { ...prev, needsUpdate: true };
  const count = nonNegInt(d.count);
  if (count === null) return prev;
  return { count, deskCount: nonNegInt(d.desk_count) ?? 0, held: nonNegInt(d.held_for_roster) ?? 0, needsUpdate: false };
}

/** 뱃지 글자 — 0 이면 null(숨김) · 100 이상은 「99+」. */
export function badgeText(count: number): string | null {
  if (!Number.isInteger(count) || count <= 0) return null;
  return count > 99 ? "99+" : String(count);
}

/** 단추 툴팁 — 기본 툴팁 + 상태 1줄(갱신 필요 · 수신 멈춤). */
export function counselTooltip(s: UnreadState): string {
  const extra: string[] = [];
  if (s.needsUpdate) extra.push(COUNSEL_COPY.needsUpdate);
  if (s.held > 0) extra.push(COUNSEL_COPY.held);
  return [COUNSEL_COPY.tooltip, ...extra].join("\n");
}

/** 파일 수정 시각 확인 주기(§11 「30~60초」). */
export const UNREAD_POLL_MS = 45_000;
