// (cysr-1116-s79 · TICKET=cysr-1116-s79-1119) 결과 받기 판정 — 순수. P2-DESIGN §11 조각 7 · §5-1 「결과물」 행 · PRD FR-P3 · FR-P4 · S5.
//
// 결과물을 알아내는 출처 둘(§5-1 · U14 닫힘):
//  ① 스킬 실행 산출 폴더 — 데몬 사건 `skill.run_finished {run_id, status, artifact_dir}`(skillrun.rs · status "done" 이고 폴더가 있을 때만).
//     구조화된 유일한 출처라 실재 확인 전에도 카드를 보인다(확인 중 · 없으면 「파일을 찾을 수 없어요」).
//  ② 마스터 답 속 절대 경로 — **홈 아래만**(허용 경로 · NFR-S2) · 숨은 폴더(`.` 로 시작하는 마디) 안 경로 · `..` 마디 · 코드 울타리 안 줄 = 0.
//     답 글은 경로를 설명·인용으로도 쓰므로 **실재가 확인된 것만** 카드가 된다(없는 경로를 「찾을 수 없어요」로 칠하지 않음 · 소음 0).
// 「새 결과」(FR-P4) = 사람이 열기·폴더 보기를 누르기 전까지 유지.
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지(시각은 인자 · views 정적 핀).

import type { Rec } from "./msgstep";

/** 결과 목록 상한(최근 것부터) — 앱 저장소 보관 한도와 같음. */
export const RESULTS_MAX = 50;
/** 한 답에서 받는 경로 상한(긴 목록을 붙인 답이 카드를 쏟지 않게). */
export const PATHS_PER_REPLY_MAX = 5;

export type ResultSource = "skill" | "reply";
export type ResultKind = "folder" | "page" | "doc" | "image" | "file";

export const KIND_LABEL: Record<ResultKind, string> = {
  folder: "폴더",
  page: "웹 페이지",
  doc: "문서",
  image: "그림",
  file: "파일",
};

export interface Result {
  /** 열쇠 = 정규화한 경로(같은 경로는 한 카드) */
  id: string;
  path: string;
  name: string;
  source: ResultSource;
  /** 처음 본 시각(ms) */
  at: number;
  /** 그 경로를 말한 마스터 답 레코드(대화 안 카드 자리) · 스킬 결과 = null */
  uuid: string | null;
  runId: string | null;
  /** 사람이 열기·폴더 보기를 눌렀는가(FR-P4 — false 면 「새 결과」) */
  seen: boolean;
  /** 실재 · null = 아직 모름(확인 중) */
  exists: boolean | null;
  /** 폴더인가 · null = 모름 */
  isDir: boolean | null;
}

/** 경로 구분자 — 홈이 `C:\…` 꼴이면 `\` 와 `/` 둘 다 받는다(윈도우 · NFR-P1). */
function seps(home: string): RegExp {
  return /^[A-Za-z]:[\\/]/.test(home) ? /[\\/]/ : /\//;
}

/** 경로 정규화 — 끝 구분자 깎기 · `~/…` 는 홈으로 · 윈도우는 구분자를 홈의 것으로. 홈 아래가 아니거나 허용 밖이면 null. */
export function normPath(raw: string, home: string): string | null {
  if (!home || !raw) return null;
  const win = /^[A-Za-z]:[\\/]/.test(home);
  const sep = win ? "\\" : "/";
  let p = raw;
  if (p === "~" || p.startsWith("~/") || (win && p.startsWith("~\\"))) p = home + p.slice(1);
  if (win) p = p.replace(/\//g, "\\");
  const h = home.replace(/[\\/]+$/, "");
  const cmp = (s: string) => (win ? s.toLowerCase() : s); // 윈도우 경로는 대소문자를 가리지 않는다
  p = p.replace(/[\\/]+$/, "");
  if (!cmp(p).startsWith(cmp(h) + sep)) return null; // 홈 자신·홈 밖 = 0(허용 경로 = 홈 아래 · §5-1)
  const rest = p.slice(h.length + 1).split(seps(home));
  if (rest.some((seg) => seg === "" || seg === "." || seg === ".." || seg.startsWith("."))) return null; // 빈 마디·되돌아가기·숨은 폴더 = 0
  return h + sep + rest.join(sep);
}

/** 경로의 마지막 이름. */
export function baseName(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts[parts.length - 1] ?? path;
}

/** 부모 폴더. */
export function parentOf(path: string): string {
  const i = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  return i <= 0 ? path : path.slice(0, i);
}

const PAGE = new Set(["html", "htm"]);
const DOC = new Set(["pdf", "doc", "docx", "hwp", "hwpx", "ppt", "pptx", "xls", "xlsx", "csv", "md", "txt", "rtf", "odt"]);
const IMAGE = new Set(["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "heic"]);

/** 결과 종류(이름의 확장자 · 폴더 여부). */
export function kindOf(name: string, isDir: boolean | null): ResultKind {
  if (isDir === true) return "folder";
  const m = /\.([A-Za-z0-9]{1,8})$/.exec(name);
  const ext = m ? m[1].toLowerCase() : "";
  if (PAGE.has(ext)) return "page";
  if (DOC.has(ext)) return "doc";
  if (IMAGE.has(ext)) return "image";
  return isDir === false || ext ? "file" : "folder";
}

// 경로 후보 — 홈 꼴로 시작하는 토막(공백·따옴표·괄호·백틱·꺾쇠에서 끊음). 경로 안 띄어쓰기는 받지 않는다(어디서 끝나는지 글만으로 못 가림 · 📌).
const STOP = "\\s`'\"<>()\\[\\]{}「」『』《》“”‘’|*";
const CAND = new RegExp(`(?:~[\\\\/]|[A-Za-z]:[\\\\/]|/)[^${STOP}]+`, "g");
/** 끝에 붙은 문장 부호(경로 일부가 아님) */
const TAIL = /[.,;:!?。、，：；…~]+$/;
/** 확장자 바로 뒤에 붙은 한글 조사·어미(「…/a.html에」·「…/주보.pdf를」) — 확장자가 앞에 있을 때만 깎는다(폴더 이름 「교회에」는 못 가림 · 그대로 둠) */
const HANGUL_TAIL = /^(.*\.[A-Za-z0-9]{1,8})[가-힣]+$/;

/** 「열기」가 곧 프로그램 실행인 꾸러미(맥 .app 등은 폴더라 Tauri open_path 의 실행형 파일 검사를 지나간다) — 열기 대신 폴더 보기만. 이름만 본다(폴더 여부 모름이어도 막음). */
const LAUNCH_BUNDLE = /\.(app|appex|prefpane|action|workflow|saver|qlgenerator|plugin|bundle|kext|xpc|framework|mpkg|pkg|command|tool|terminal)$/i;
export function launchesProgram(name: string): boolean {
  return LAUNCH_BUNDLE.test(name);
}

/** 마스터 답 글 → 홈 아래 경로들(나온 순서 · 겹침 0 · 상한 PATHS_PER_REPLY_MAX). 코드 울타리 안 줄 = 0(명령 예시). */
export function pathsInText(text: string, home: string): string[] {
  const out: string[] = [];
  let fence: { ch: string; n: number } | null = null;
  for (const raw of text.replace(/\r\n?/g, "\n").split("\n")) {
    const f = /^\s*(`{3,}|~{3,})/.exec(raw);
    if (f) {
      const ch = f[1][0];
      const n = f[1].length;
      if (fence === null) fence = { ch, n };
      else if (fence.ch === ch && n >= fence.n && raw.trim() === f[1].trim()) fence = null;
      continue;
    }
    if (fence) continue;
    for (const m of raw.matchAll(CAND)) {
      const at = m.index ?? 0;
      const prev = at > 0 ? raw[at - 1] : "";
      if (prev && /[A-Za-z0-9_.\-:/\\~]/.test(prev)) continue; // 낱말·URL 한가운데(https://… 의 // 등)
      const cut = m[0].replace(TAIL, "");
      const p = normPath(HANGUL_TAIL.exec(cut)?.[1] ?? cut, home);
      if (p && !out.includes(p)) out.push(p);
      if (out.length >= PATHS_PER_REPLY_MAX) return out;
    }
  }
  return out;
}

export interface Candidate {
  path: string;
  source: ResultSource;
  uuid: string | null;
  runId: string | null;
}

/** 마스터 답 레코드 → 결과 후보(user·곁가지·글 없는 레코드 = 0). */
export function candidatesOf(r: Rec, home: string): Candidate[] {
  if (r.role !== "assistant" || r.sidechain || typeof r.text !== "string") return [];
  return pathsInText(r.text, home).map((path) => ({ path, source: "reply" as const, uuid: r.uuid, runId: null }));
}

/** skill.run_finished 사건 본문 → 후보(완료 ∧ 폴더 글이 있을 때만 · 홈 아래만). */
export function skillCandidateOf(payload: unknown, home: string): Candidate | null {
  const p = (payload ?? {}) as { run_id?: unknown; status?: unknown; artifact_dir?: unknown };
  if (p.status !== "done" || typeof p.artifact_dir !== "string" || !p.artifact_dir) return null;
  const path = normPath(p.artifact_dir, home);
  if (!path) return null;
  return { path, source: "skill", uuid: null, runId: typeof p.run_id === "string" ? p.run_id : null };
}

/** 후보를 목록에 더함 — 같은 경로는 한 카드(먼저 본 것 유지 · 스킬 출처가 오면 출처를 스킬로 올림) · 최근 것부터 상한. */
export function addCandidates(list: readonly Result[], cands: readonly Candidate[], now: number): Result[] {
  let out = [...list];
  for (const c of cands) {
    const i = out.findIndex((r) => r.id === c.path);
    if (i >= 0) {
      if (c.source === "skill" && out[i].source !== "skill") out[i] = { ...out[i], source: "skill", runId: c.runId };
      continue;
    }
    out.unshift({ id: c.path, path: c.path, name: baseName(c.path), source: c.source, at: now, uuid: c.uuid, runId: c.runId, seen: false, exists: null, isDir: c.source === "skill" ? true : null });
  }
  if (out.length > RESULTS_MAX) out = out.slice(0, RESULTS_MAX);
  return out;
}

/** 부모 폴더 목록(Tauri list_dir 응답) → 그 이름의 실재·폴더 여부 · 꼴이 틀리면 null(모름). */
export function presenceIn(listing: unknown, name: string, caseless = false): { exists: boolean; isDir: boolean | null } | null {
  if (!Array.isArray(listing)) return null;
  const eq = (a: string) => (caseless ? a.toLowerCase() === name.toLowerCase() : a === name);
  for (const e of listing) {
    const x = e as { name?: unknown; is_dir?: unknown } | null;
    if (!x || typeof x.name !== "string") return null;
    if (eq(x.name)) return { exists: true, isDir: typeof x.is_dir === "boolean" ? x.is_dir : null };
  }
  return { exists: false, isDir: null };
}

/** list_dir 실패 글 → 「없음 확정」인가(파일·폴더 없음 오류만 · 권한·그 밖 = 모름). */
export function listErrorIsMissing(err: string): boolean {
  return /No such file or directory|os error 2\b|os error 3\b|cannot find the (file|path)/i.test(err);
}

/** 화면에 보일 결과 — 스킬 결과 = 늘 · 답 속 경로 = 실재 확정만(답이 설명으로 쓴 경로는 카드 0). */
export function visibleResults(list: readonly Result[]): Result[] {
  return list.filter((r) => r.source === "skill" || r.exists === true || (r.seen && r.exists === false));
}

/** 「결과 N」 머리(보이는 수) · 새 결과 수. */
export function resultsLabel(list: readonly Result[]): { text: string; count: number; fresh: number } {
  const v = visibleResults(list);
  const fresh = v.filter((r) => !r.seen).length;
  return { text: fresh > 0 ? `결과 ${v.length} · 새 결과 ${fresh}` : `결과 ${v.length}`, count: v.length, fresh };
}

/** 「고쳐 달라고 하기」 — 입력칸 앞에 넣을 글(그 결과를 가리키는 말 · 보낼 글은 사람이 보는 그대로 · FR-C3 원문 그대로). */
export function revisePrefix(r: Result): string {
  return `이 결과를 고쳐 주세요 — ${r.path}\n고칠 점: `;
}

/** 「마스터에게 물어보기」(파일을 찾을 수 없음) — 입력칸 앞에 넣을 글. */
export function missingPrefix(r: Result): string {
  return `이 결과 파일을 찾을 수 없어요 — ${r.path}\n어디에 있는지 알려 주세요.`;
}

/** 입력칸에 앞글을 넣는다 — 쓰던 글은 지우지 않고 뒤에 둔다(VERIFY-P2 V-F3). 이미 같은 앞글로 시작하면 그대로. */
export function withPrefix(draft: string, prefix: string): string {
  if (draft.startsWith(prefix)) return draft;
  return draft.trim() ? `${prefix}${draft}` : prefix;
}

/** 저장 꼴(앱 저장소 · 결과 경로·출처·시각·봤음만 — 말 원문 0자) → 목록. 꼴이 틀린 항목은 버림. */
export function restoreResults(raw: string | null): Result[] {
  if (!raw) return [];
  let j: unknown;
  try {
    j = JSON.parse(raw);
  } catch {
    return [];
  }
  const items = (j as { v?: unknown; items?: unknown } | null)?.v === 1 ? (j as { items: unknown }).items : null;
  if (!Array.isArray(items)) return [];
  const out: Result[] = [];
  for (const it of items) {
    const x = it as Record<string, unknown> | null;
    if (!x || typeof x.path !== "string" || (x.source !== "skill" && x.source !== "reply") || typeof x.at !== "number" || typeof x.seen !== "boolean") continue;
    if (out.some((r) => r.id === x.path)) continue;
    out.push({ id: x.path, path: x.path, name: baseName(x.path), source: x.source, at: x.at, uuid: typeof x.uuid === "string" ? x.uuid : null, runId: typeof x.runId === "string" ? x.runId : null, seen: x.seen, exists: null, isDir: x.source === "skill" ? true : null });
    if (out.length >= RESULTS_MAX) break;
  }
  return out;
}

/** 저장할 꼴(실재는 저장하지 않음 — 다시 켜면 다시 확인). 답 속 경로는 실재가 확정된 적 있는 것만(설명으로 쓴 경로를 남기지 않음). */
export function persistable(list: readonly Result[]): string {
  const items = list
    .filter((r) => r.source === "skill" || r.exists === true || r.seen)
    .map((r) => ({ path: r.path, source: r.source, at: r.at, uuid: r.uuid, runId: r.runId, seen: r.seen }));
  return JSON.stringify({ v: 1, items });
}
