// (TICKET=cysr-1118-ui ①) 대화 화면 진행 줄 — 순수(박사님 11-22 10:1x 「대화 모드가 … 기다리는데 답답함」 · 10:2x 「요즘 LLM 처럼 생각 과정 · 실제 과정은 선택」).
//
// 기본 = 접힌 한 줄(「파일 읽는 중 · core.ts · 12초」) · 누르면 「과정 보기」 = 실제 단계 목록(읽은 파일 · 실행한 명령 · 찾은 말 · 중간 글 · 시각).
// 재료 = 결속 세션 기록의 마스터 레코드(viewcore.rs parse_transcript_chunk 의 tools · thinking · text) — 메모리에만 둔다(화면 저장소 0 = NFR-S3).
// 생각 내용(thinking 글)은 세션 기록에 빈 칸으로 저장돼 보여 줄 수 없다(11-22 실측 10/10) → 「생각하는 중」 표지만.
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지(시각은 인자).

import { STEP_LABEL, type Msg, type Rec, type Step } from "./msgstep";

export interface ProgStep {
  kind: "tool" | "text" | "think";
  /** 진행형 한 줄(「파일 읽는 중」) */
  label: string;
  /** 단서(파일 이름 · 명령 설명 · 찾는 말 · 글 앞부분) — 없으면 null */
  hint: string | null;
  /** 기록 시각(ms) · 없으면 null */
  at: number | null;
}

/** 한 말에 들고 있는 단계 상한(넘으면 오래된 것부터 버림 · 센 수는 dropped 로). */
export const PROG_MAX = 200;
/** 중간 글 단서 글자 수. */
export const TEXT_HINT_MAX = 40;

const TOOL_LABEL: Record<string, string> = {
  Read: "파일 읽는 중",
  Edit: "파일 고치는 중",
  MultiEdit: "파일 고치는 중",
  NotebookEdit: "파일 고치는 중",
  Write: "파일 쓰는 중",
  Bash: "명령 실행 중",
  PowerShell: "명령 실행 중",
  Grep: "찾는 중",
  Glob: "파일 찾는 중",
  WebSearch: "웹 검색 중",
  WebFetch: "웹 읽는 중",
  Task: "도우미에게 맡기는 중",
  Agent: "도우미에게 맡기는 중",
  TodoWrite: "할 일 정리 중",
};

/** 도구 이름 → 진행형 한 줄(모르는 도구 = 「도구 쓰는 중 · <이름>」 · mcp__서버__이름 = 마지막 이름). */
export function toolLabel(name: string): string {
  const known = TOOL_LABEL[name];
  if (known) return known;
  const short = name.startsWith("mcp__") ? name.split("__").filter(Boolean).pop() ?? name : name;
  return `도구 쓰는 중 · ${short}`;
}

function tsOf(r: Rec): number | null {
  if (r.ts === null) return null;
  const t = Date.parse(r.ts);
  return Number.isNaN(t) ? null : t;
}

function clip(s: string, n: number): string {
  const one = s.replace(/\s+/g, " ").trim();
  const cs = Array.from(one);
  return cs.length > n ? `${cs.slice(0, n).join("")}…` : one;
}

/** 마스터 레코드 하나 → 단계들(순수). 도구 호출이 있으면 그것들 · 글이 있으면 「답 쓰는 중」 · 둘 다 없고 생각 조각만 있으면 「생각하는 중」. */
export function stepsOf(r: Rec): ProgStep[] {
  if (r.role !== "assistant" || r.sidechain) return [];
  const at = tsOf(r);
  const out: ProgStep[] = [];
  if (r.text !== null && r.text.trim() !== "") out.push({ kind: "text", label: "답 쓰는 중", hint: clip(r.text, TEXT_HINT_MAX), at });
  for (const t of Array.isArray(r.tools) ? r.tools : []) {
    if (!t || typeof t.name !== "string") continue;
    out.push({ kind: "tool", label: toolLabel(t.name), hint: typeof t.hint === "string" && t.hint !== "" ? t.hint : null, at });
  }
  if (out.length === 0 && r.thinking === true) out.push({ kind: "think", label: "생각하는 중", hint: null, at });
  return out;
}

/** 단계 잇기(순수 · 새 배열) — 상한을 넘으면 앞에서 버린다. */
export function appendSteps(prev: readonly ProgStep[] | undefined, add: readonly ProgStep[]): ProgStep[] | undefined {
  if (add.length === 0) return prev ? [...prev] : prev;
  const all = [...(prev ?? []), ...add];
  return all.length > PROG_MAX ? all.slice(all.length - PROG_MAX) : all;
}

/** 진행 줄을 다는 단계(아직 답을 기다리는 말). */
const LIVE: ReadonlySet<Step> = new Set<Step>(["injected", "checking", "slow", "delivered", "replying"]);

/** 진행 줄을 달 말 = 보낸 시각이 있고 아직 답을 기다리는 말 가운데 가장 최근 하나(앞 말들은 뒤 말이 덮음 — settleSteps 와 같은 규칙). */
export function liveMsg(msgs: readonly Msg[]): Msg | null {
  let best: Msg | null = null;
  for (const m of msgs) if (LIVE.has(m.step) && m.sentAt !== null && (best === null || (best.sentAt as number) <= m.sentAt)) best = m;
  return best;
}

/** 경과(ms) → 「12초」 · 「1분 5초」 · 「1시간 2분」(음수 = 0초). */
export function elapsedLabel(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s}초`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}분 ${s % 60}초`;
  return `${Math.floor(m / 60)}시간 ${m % 60}분`;
}

/** 접힌 한 줄(순수) — 답을 기다리는 말: 「<지금 단계> · <단서> · <경과>」 · 끝난 말: 단계가 있으면 「과정 N단계」 · 없으면 null.
 *  지금 단계 = 마지막 단계(답하는 중일 때만 · 전달 확인 전엔 그 말의 단계 이름) · 세션 기록을 못 읽는 자리(윈 옛 판 등)에서도 단계 이름 + 경과는 나온다. */
export function progressLine(m: Msg, now: number, live: boolean): { text: string; live: boolean } | null {
  const steps = m.steps ?? [];
  if (!live || m.sentAt === null) return steps.length ? { text: `과정 ${steps.length}단계`, live: false } : null;
  const last = steps[steps.length - 1];
  const head = (m.step === "replying" || m.step === "delivered") && last ? (last.hint ? `${last.label} · ${last.hint}` : last.label) : STEP_LABEL[m.step];
  return { text: `${head} · ${elapsedLabel(now - m.sentAt)}`, live: true };
}

/** 펼친 목록 한 줄의 시각(이 기기 시간대 HH:MM:SS) · 없으면 빈 글. */
export function stepTime(at: number | null): string {
  if (at === null) return "";
  const t = new Date(at);
  return [t.getHours(), t.getMinutes(), t.getSeconds()].map((n) => String(n).padStart(2, "0")).join(":");
}
