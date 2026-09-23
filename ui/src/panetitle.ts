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

/** 머리에 보일 제목. sid 를 모르면(생성 직후) 종전처럼 받은 제목·경로를 그대로. */
export function paneTitleText(
  sid: number | null,
  title: string | null | undefined,
  liveCwd: string | null | undefined,
  exited: boolean,
): string {
  let t: string;
  if (!isAutoTitle(title)) t = title as string;
  else if (sid == null) t = liveCwd || "…";
  else t = liveCwd ? `${sid}${SEP}${cwdBase(liveCwd)}` : String(sid);
  return exited ? EXITED_TITLE_PREFIX + t : t;
}

/**
 * 이름 변경 확정 때 데몬에 보낼 제목. 빈 이름 = 기본으로 되돌리기다.
 *   · 편집 전 데몬 제목이 이 번호로 시작하면(역할 창의 「번호 · 특성」) 그것을 되돌려 보낸다 —
 *     ""를 저장하면 데몬은 다시 짓지 않아(initial_title 은 만들 때 1회) 번호·특성이 영구히 사라졌다.
 *   · 그 밖(역할 없는 창·이미 사람 이름)은 ""(자동 제목 = 「번호 · 폴더 이름」).
 */
export function renameCommitTitle(typed: string, before: string | null | undefined, sid: number): string {
  const t = typed.trim();
  if (t) return t;
  return before && before.startsWith(`${sid}${SEP}`) ? before : "";
}
