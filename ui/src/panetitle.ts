// 창(pane) 머리 제목 — 순수 판정(v116-ui-close-r2 · D4 #12).
// 오너 규칙 「번호 + 특성」: 박사님이 master 가 부르는 「285 셸」을 화면과 대조할 수 있어야 한다.
//   · 역할 창 = 데몬이 지은 「번호 · 특성」(panetitle.rs initial_title) — 그대로 쓴다.
//   · 역할 없는 창(사람이 연 셸) = 데몬이 제목을 짓지 않는다 → 「번호 · 폴더 이름」. 종전엔 전체 경로를 제목으로 써
//     좁은 창에서 끝(가장 중요한 폴더 이름)이 잘렸다. 전체 경로는 툴팁으로 옮긴다.
//   · 끝난 창 표지는 **앞머리**다 — 꼬리에 붙이면 말줄임이 표지부터 자른다.

/** 끝난 창 제목 앞머리(D4 #13 문구 · D4 #12 위치). 시험·헤드리스가 이 상수 하나를 본다. */
export const EXITED_TITLE_PREFIX = "(끝남) ";
/** 데몬 제목 칸 구분자(panetitle.rs SEP 와 같은 글자). */
const SEP = " · ";

/** 데몬 기본 자동 제목(「surface N」·빈 문자열) = 우리가 대신 짓는다. */
export const isAutoTitle = (t: string | null | undefined): boolean => !t || /^surface \d+$/.test(t);

/** 경로의 마지막 폴더 이름(맥 `/` · 윈 `\` 모두). 끝 구분자는 무시 · 뿌리만 남으면 원문. */
export function cwdBase(cwd: string): string {
  const parts = cwd.split(/[\\/]+/).filter((p) => p !== "");
  return parts.length ? parts[parts.length - 1] : cwd;
}

/**
 * (v116-num) 제목에 쓰는 번호 = **보이는 번호**(데몬 surface.list 의 display_no · 1~999 순환).
 *   · undefined = 필드가 없는 옛 데몬(1.1.6 이전) → 종전대로 내부 번호.
 *   · null = 보이는 번호 없음 → 「—」(데몬 panetitle.rs 와 같은 글자).
 * 기계 경로(닫기·입력·배달)는 여전히 내부 번호(sid)만 쓴다 — 이것은 사람 눈의 이름표다.
 */
export const NO_DISPLAY_NO = "—";
export function titleNo(sid: number, displayNo?: number | null): string {
  if (displayNo === undefined) return String(sid);
  return displayNo === null ? NO_DISPLAY_NO : String(displayNo);
}

/** 머리에 보일 제목. sid 를 모르면(생성 직후) 종전처럼 받은 제목·경로를 그대로. */
export function paneTitleText(
  sid: number | null,
  title: string | null | undefined,
  liveCwd: string | null | undefined,
  exited: boolean,
  displayNo?: number | null,
): string {
  let t: string;
  if (!isAutoTitle(title)) t = title as string;
  else if (sid == null) t = liveCwd || "…";
  else {
    const no = titleNo(sid, displayNo);
    t = liveCwd ? `${no}${SEP}${cwdBase(liveCwd)}` : no;
  }
  return exited ? EXITED_TITLE_PREFIX + t : t;
}

/** 앞머리 「(끝남) 」를 뗀 제목 — 이름 변경 입력칸에는 표시용 앞머리가 섞여 있다(opus 결함 2). */
export function stripExited(t: string): string {
  return t.startsWith(EXITED_TITLE_PREFIX) ? t.slice(EXITED_TITLE_PREFIX.length) : t;
}

/**
 * 역할 창의 규칙 제목(데몬 initial_title 「번호 · 특성」)인가 — 되돌리기 재료로 기억할 값. 역할 없는 창은 null
 * (그 창의 기본은 경로를 따라가는 자동 제목이라 고정 제목으로 되돌리면 안 된다 — opus 결함 1).
 */
export function ruleTitleOf(
  sid: number,
  role: string | null | undefined,
  title: string | null | undefined,
  displayNo?: number | null,
): string | null {
  return role && title && title.startsWith(`${titleNo(sid, displayNo)}${SEP}`) ? title : null;
}

/**
 * 이름 변경 확정 때 데몬에 보낼 제목. null = 보내지 않는다.
 *   · 바뀐 것이 없으면 보내지 않는다 — 그냥 눌렀다 떼기만 해도 보이던 자동 제목이 고정 제목으로 굳던 것(opus 결함 1).
 *   · 빈 이름 = 기본으로 되돌리기: 역할 창은 기억해 둔 규칙 제목(「번호 · 특성」 · 데몬은 다시 짓지 않는다),
 *     역할 없는 창은 ""(자동 제목 = 「번호 · 폴더 이름」). 사람 이름을 거쳐 비워도 규칙 제목으로 돌아온다(opus 결함 3).
 *   · 「(끝남) 」 앞머리는 떼고 비교·저장한다(opus 결함 2).
 */
export function renameCommitTitle(typed: string, shownBefore: string, ruleTitle: string | null): string | null {
  const t = stripExited(typed).trim();
  if (t === stripExited(shownBefore).trim()) return null;
  if (t) return t;
  return ruleTitle ?? "";
}
