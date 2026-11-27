// (TICKET=cysr-1118-ui ①) 대화 화면 진행 줄 — 순수(박사님 11-22 10:1x 「대화 모드가 … 기다리는데 답답함」 · 10:2x 「요즘 LLM 처럼 생각 과정 · 실제 과정은 선택」).
//
// 기본 = 접힌 한 줄(「파일 읽는 중 · core.ts · 12초」) · 누르면 「과정 보기」 = 실제 단계 목록(읽은 파일 · 실행한 명령 · 찾은 말 · 중간 글 · 시각).
// 재료 = 결속 세션 기록의 마스터 레코드(viewcore.rs parse_transcript_chunk 의 tools · thinking · text) — 메모리에만 둔다(화면 저장소 0 = NFR-S3).
// 생각 내용(thinking 글)은 세션 기록에 빈 칸으로 저장돼 보여 줄 수 없다(11-22 실측 10/10) → 「생각하는 중」 표지만.
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지(시각은 인자).

import { stepLabel, UNSURE_LABEL, viewStep, type Msg, type Rec, type Step } from "./msgstep";

export interface ProgStep {
  kind: "tool" | "text" | "think";
  /** 진행형 한 줄(「파일 읽는 중」) */
  label: string;
  /** 단서(파일 이름 · 명령 설명 · 찾는 말 · 글 앞부분) — 없으면 null */
  hint: string | null;
  /** 기록 시각(ms) · 없으면 null */
  at: number | null;
  /** (TICKET=cysr-1119-s4 · F34) 도구 원 이름(도구 단계만) — 분류는 이 이름으로(표시 글 `label` 을 읽지 않는다) */
  tool?: string;
}

/** 한 말에 들고 있는 단계 상한(넘으면 오래된 것부터 버림 · 버린 수는 분류별로 `Msg.stepsDropped` 에 — F25 · `appendStepsTo`). */
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

/** (TICKET=cysr-1119-s4 · F34) 과정 요약 분류 — 도구 이름 표. text = 글 단계(셈에만 넣고 요약 글에는 안 보임 · [master#70cce152] ⓐ). */
export type ProgClass = "read" | "find" | "cmd" | "edit" | "agent" | "web" | "plan" | "think" | "text" | "other";
/** 버린 단계 수(분류별 · F25). */
export type ProgDropped = Partial<Record<ProgClass, number>>;

/** 도구 이름 → 분류(DESIGN §3-2 F34 · PowerShell·MultiEdit = [master#70cce152] ⓑ) · 표 밖 = 「그 밖」. */
const TOOL_CLASS: Record<string, ProgClass> = {
  Read: "read",
  Glob: "find",
  Grep: "find",
  Bash: "cmd",
  PowerShell: "cmd",
  Edit: "edit",
  MultiEdit: "edit",
  Write: "edit",
  NotebookEdit: "edit",
  Task: "agent",
  Agent: "agent",
  WebSearch: "web",
  WebFetch: "web",
  TodoWrite: "plan",
};

/** 요약에 보이는 순서(같은 수면 이 순서) · 이름. 글(text)은 없음 = 요약 글에 안 보임. */
const CLASS_SHOWN: ReadonlyArray<[ProgClass, string]> = [
  ["read", "읽기"],
  ["find", "찾기"],
  ["cmd", "명령"],
  ["edit", "고침"],
  ["agent", "도우미"],
  ["web", "웹 찾기"],
  ["plan", "계획"],
  ["think", "생각"],
  ["other", "그 밖"],
];
/** 요약에 보이는 분류 최대 수(T-U4). */
export const SUMMARY_MAX = 3;
/** 경과를 붙이는 문턱(ms · V4c) — 이보다 짧으면 단계 글만. */
export const ELAPSED_MIN_MS = 3_000;

/** 단계 하나 → 분류(순수 · 표시 글 무관). */
export function stepClass(s: ProgStep): ProgClass {
  if (s.kind === "think") return "think";
  if (s.kind === "text") return "text";
  return (s.tool !== undefined && TOOL_CLASS[s.tool]) || "other";
}

/** 분류별 셈 = 남은 단계 + 버린 수(순수). 합 = 지금까지 이 말에 이어진 단계 수 전부. */
export function classCounts(steps: readonly ProgStep[], dropped?: ProgDropped): ProgDropped {
  const out: ProgDropped = { ...(dropped ?? {}) };
  for (const s of steps) {
    const c = stepClass(s);
    out[c] = (out[c] ?? 0) + 1;
  }
  return out;
}

/** (CH-D) 과정 요약 한 줄 — 0 아닌 분류 최대 3개 「읽기 3번 · 찾기 2번 · 명령 2번」(많은 순 · 같으면 표 순서 · 호출 수라 「N번」) · 보일 것 없으면 빈 글. */
export function progressSummary(steps: readonly ProgStep[], dropped?: ProgDropped): string {
  const c = classCounts(steps, dropped);
  return CLASS_SHOWN.map(([k, name], i) => ({ name, n: c[k] ?? 0, i }))
    .filter((x) => x.n > 0)
    .sort((a, b) => b.n - a.n || a.i - b.i)
    .slice(0, SUMMARY_MAX)
    .map((x) => `${x.name} ${x.n}번`)
    .join(" · ");
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
    out.push({ kind: "tool", label: toolLabel(t.name), hint: typeof t.hint === "string" && t.hint !== "" ? t.hint : null, at, tool: t.name });
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

/** (TICKET=cysr-1119-s4 · F25) 말에 단계 잇기 — 상한을 넘어 앞에서 버리는 단계는 분류별 수를 `stepsDropped` 에 더한다(요약 셈이 잘린 목록에서 나오지 않게). */
export function appendStepsTo(owner: { steps?: ProgStep[]; stepsDropped?: ProgDropped }, add: readonly ProgStep[]): void {
  const prev = owner.steps ?? [];
  const cut = prev.length + add.length - PROG_MAX;
  if (cut > 0) owner.stepsDropped = classCounts([...prev, ...add].slice(0, cut), owner.stepsDropped);
  owner.steps = appendSteps(owner.steps, add);
}

/** 진행 줄을 다는 단계(아직 답을 기다리는 말). */
const LIVE: ReadonlySet<Step> = new Set<Step>(["injected", "accepted", "checking", "slow", "delivered", "replying"]);

/** 진행 줄을 달 말 = **보낸 시각이 가장 늦은 말**이 아직 답을 기다리면 그 말 · 아니면 없음(앞 말들은 뒤 말이 덮음).
 *  ★codex 1R major: 기다리는 말만 먼저 걸러 고르면, 새 말이 「답함」이 된 뒤 옛 미응답 말이 다시 살아나 옛 단계·시계가 재개됐다 — 최신성 경계를 먼저 잡는다. */
export function liveMsg(msgs: readonly Msg[]): Msg | null {
  let newest: Msg | null = null;
  for (const m of msgs) if (m.sentAt !== null && (newest === null || (newest.sentAt as number) <= m.sentAt)) newest = m;
  return newest && LIVE.has(newest.step) && !newest.turnClosed ? newest : null; // (TICKET=cysr-1118u-chat ③) 턴이 끝난 말(뒤에 중계 등 새 차례) = 진행 줄을 살려 달지 않음
}

/** 경과(ms) → 「12초」 · 「1분 5초」 · 「1시간 2분」(음수 = 0초). */
export function elapsedLabel(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s}초`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}분 ${s % 60}초`;
  return `${Math.floor(m / 60)}시간 ${m % 60}분`;
}

/** 경과 글 — 3초 미만(V4c)·모름 = null. */
function elapsedOrNull(ms: number | null): string | null {
  return ms === null || Number.isNaN(ms) || ms < ELAPSED_MIN_MS ? null : elapsedLabel(ms);
}

/** 접힌 한 줄(순수).
 *  (TICKET=cysr-1119-s4 · CH-D) 요약 켬(기본):
 *   · 답을 기다리는 말 = 도구·생각 단계가 있으면 「<요약> · <경과> · 지금: <지금 단계>」(P3 v4 U3 꼴) · 없으면 「<지금 단계> · <단서> · <경과>」(1.1.18 꼴)
 *   · 끝난 말 = 「<요약> · <걸린 시간>」(걸린 시간 = 마지막 단계 시각 − 보낸 시각) · 요약이 비면 걸린 시간만 · 둘 다 없으면 「과정 보기」(펼침 단추 자리) · 단계 0 = null
 *   · 경과·걸린 시간은 3초 미만이면 안 붙임(V4c)
 *  요약 끔(`summary:false` = 되돌리기 연결점 · S2 의 CH-E 가 병합 때 꽂음) = 1.1.18 머리(끝난 말 「과정 N단계」). 경과 3초 문턱(V4c)은 둘 다(판으로 되돌림).
 *  지금 단계 = 마지막 단계(답하는 중일 때만 · 전달 확인 전엔 그 말의 단계 이름) · 세션 기록을 못 읽는 자리(윈 옛 판 등)에서도 단계 이름 + 경과는 나온다. */
export function progressLine(m: Msg, now: number, live: boolean, opts: { summary?: boolean } = {}): { text: string; live: boolean } | null {
  const steps = m.steps ?? [];
  const useSummary = opts.summary !== false;
  const summary = useSummary ? progressSummary(steps, m.stepsDropped) : "";
  if (!live || m.sentAt === null) {
    if (steps.length === 0) return null;
    if (!useSummary) return { text: `과정 ${steps.length}단계`, live: false };
    const lastAt = steps[steps.length - 1].at;
    const took = elapsedOrNull(lastAt === null || m.sentAt === null ? null : lastAt - m.sentAt);
    const text = [summary, took].filter((x): x is string => !!x).join(" · ");
    return { text: text || "과정 보기", live: false };
  }
  const last = steps[steps.length - 1];
  const answering = (m.step === "replying" || m.step === "delivered") && last;
  const elapsed = elapsedOrNull(now - m.sentAt);
  // (TICKET=cysr-1121-ui-kfix2 ②′) 쓰였는지 모르는 말 = 진행 줄 첫 마디도 「확인 못 함」(말풍선 이름과 같은 값 · 「받아 둠」·「전달됨」 단정 0) — 과정 단계는 그 글에 대한 마스터 일이라 그대로 잇는다.
  const unsure = viewStep(m) === "unsure" ? UNSURE_LABEL : null;
  if (answering && summary) return { text: [unsure, summary, elapsed, `지금: ${last.label}`].filter((x): x is string => !!x).join(" · "), live: true };
  const head = answering ? [unsure, last.label, last.hint].filter((x): x is string => !!x).join(" · ") : stepLabel(m);
  return { text: elapsed ? `${head} · ${elapsed}` : head, live: true };
}

/** 펼친 목록 한 줄의 시각(이 기기 시간대 HH:MM:SS) · 없으면 빈 글. */
export function stepTime(at: number | null): string {
  if (at === null) return "";
  const t = new Date(at);
  return [t.getHours(), t.getMinutes(), t.getSeconds()].map((n) => String(n).padStart(2, "0")).join(":");
}
