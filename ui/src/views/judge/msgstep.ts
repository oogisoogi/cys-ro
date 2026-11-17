// (cysr-ui-slice1) 보낸 말 단계 판정 — 순수(P2-DESIGN §5-2 · 조각 1 = 사람 말 최소판: 붙잡음·전달 확인 중·전달됨·답하는 중·답함·못 보냄·확인 중·오래 걸려요).
//
// 「전달됨」 = 결속 세션 기록에 **보낸 뒤** · 보낸 글과 **전문 일치**하는 user 레코드(아직 다른 말에 짝지어지지 않은 첫 것)가 나왔을 때만.
// 「답함」 = 그 user 레코드의 uuid 를 부모로 잇는 사슬 위 assistant 글 + 마스터 활동 쉼. 근거가 없으면 칠하지 않는다(「모름」 = 확인 중).
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지(시각은 인자).

/** 「전달 확인 중」·「확인 중」이 이 시간 넘게 근거 없으면 「확인이 오래 걸려요」(설계 목표값 120초 · §5-1). */
export const SLOW_MS = 120_000;
/** 세션 기록 시각과 보낸 시각의 허용 차(같은 기계 시계 · 기록이 보낸 시각보다 조금 앞서 찍힐 수 있음). */
export const TS_SKEW_MS = 5_000;
/** 원자 제출이 좌석에 머무는 시간 — 0.5 M1 실측 Ctrl-U→Enter 728.1 / 767.9 / 835.2 ms(최소/중앙/최대 · 5회). 설계의 400ms 가 아니다.
 *  세션 기록 첫 조회는 이 뒤에 해야 의미가 있다(아래 READ_AFTER_MS 첫 값 ≥ 이 값). */
export const ATOMIC_SUBMIT_MS = { min: 728, median: 768, max: 836 } as const;
/** 보낸 뒤 세션 기록을 읽는 시각(설계 §5-2 「+1·+3·+7초 · 상한 3」). */
export const READ_AFTER_MS: readonly number[] = [1_000, 3_000, 7_000];
/** U20(긴 붙여넣기가 세션 기록에 「[Pasted text …]」로 접히는가) — **측정 대기**(0.5 M7ⓐ 보류).
 *  지금 = 전문 일치만(접힌 꼴이면 짝이 안 되어 「전달 확인 중 → 오래 걸려요」로 남는다 · 틀린 「전달됨」 0).
 *  값이 오면 `userRecordMatches` 의 이 갈래만 바꾼다. */
export const U20_PASTE_RECORD_FORM: "unmeasured" | "verbatim" | "collapsed" = "unmeasured";
/** M8(세션 레코드에 uuid/parentUuid 가 있는가) — **측정 대기**. 없으면 답을 그 말에 묶지 않는다(「답함」 0 · 말풍선은 「마스터」 일반 줄로). */
export const M8_UUID_CHAIN: "unmeasured" | "present" | "absent" = "unmeasured";
/** (조각 3) 원자 제출 요청이 이만큼 응답 없이 걸려 있으면 「보내는 중」 → 「확인 중」(§5-2 「근거 3초 넘게 없음」 · PRD M2 3초). 응답이 오면 그 응답으로 바뀐다. */
export const SENDING_SILENT_MS = 3_000;
/** (조각 3) 데몬 `input.refused_at_write`(쓰기 직전 재판정 · 제출 키를 쓰지 않음 · handlers.rs approval_write_guard)를 보낸 말에 잇는 창.
 *  그 사건에는 요청 번호가 없다 → 같은 좌석 · 보낸 지 이 시간 안 · 아직 증거 없는 **가장 최근** 말 하나만(쓰기는 한 번에 1건이라 겹치지 않음).
 *  창 = 원자 제출 최대 0.84초(0.5 M1) + 사건 전달 여유. 설계 목표값. */
export const REFUSED_AT_WRITE_WINDOW_MS = 5_000;

export type Step = "held" | "sending" | "injected" | "delivered" | "replying" | "replied" | "failed" | "checking" | "slow" | "queued_hold";

export const STEP_LABEL: Record<Step, string> = {
  held: "붙잡아 둠",
  sending: "보내는 중",
  injected: "전달 확인 중",
  delivered: "전달됨",
  replying: "답하는 중",
  replied: "답함",
  failed: "못 보냄",
  checking: "확인 중",
  slow: "확인이 오래 걸려요",
  queued_hold: "차례 기다림(업데이트 뒤 전달)",
};

export interface Reply {
  uuid: string | null;
  text: string;
}

export interface Msg {
  id: string;
  /** composeOutbound 를 거친 글(데몬에 보낸 바이트와 같은 글) */
  text: string;
  createdAt: number;
  /** 원자 제출 요청 시각(ms) · 아직 안 보냈으면 null */
  sentAt: number | null;
  step: Step;
  /** 붙잡음·실패 까닭(문턱 코드·데몬 오류 코드) */
  code?: string;
  note?: string;
  userUuid?: string | null;
  /** 이 말에서 이어진 레코드 uuid 들(부모 사슬) */
  thread: string[];
  replies: Reply[];
  /** 붙잡은 말을 이 시각(ms) 전에는 다시 문턱에 걸지 않음(데몬 거부 뒤 쉼) */
  notBefore?: number;
  /** 다시 보내기를 이미 썼는가(확정 실패 때 1회만 · NFR-R1) */
  retried?: boolean;
  /** (조각 3) 원자 제출을 보낸 마스터 좌석 번호 — 좌석에 걸린 데몬 사건(쓰기 직전 거부)을 이 말에 잇는 데 씀 */
  seat?: number;
}

export interface Rec {
  uuid: string | null;
  parent: string | null;
  role: "user" | "assistant";
  text: string | null;
  parts?: string[] | null;
  ts: string | null;
  sidechain?: boolean;
}

/** 데몬 결과(viewcore.rs classify_send) → 단계. */
export function stepFromOutcome(outcome: unknown): Step {
  switch (outcome) {
    case "written":
      return "injected";
    case "held":
      return "held";
    case "queued_hold":
      return "queued_hold";
    case "failed":
      return "failed";
    default:
      return "checking"; // uncertain·모르는 꼴 = 확인 중(다시 보내기 금지)
  }
}

const AWAITING: ReadonlySet<Step> = new Set<Step>(["injected", "checking", "slow"]);

export function normRecordText(t: string): string {
  return t.replace(/\r\n?/g, "\n").replace(/^\s+/, "").replace(/\s+$/, "");
}

/** user 레코드가 이 말인가 — 지금은 전문 일치만(U20 측정 대기). 조각이 여럿이면 조각 하나가 같아도 된다(훅이 덧붙인 글 조각). */
export function userRecordMatches(m: Msg, r: Rec): boolean {
  if (r.role !== "user" || r.text === null || r.sidechain) return false;
  if (normRecordText(r.text) === m.text) return true;
  return Array.isArray(r.parts) && r.parts.some((p) => normRecordText(p) === m.text);
}

function recordAfter(r: Rec, sentAt: number): boolean {
  if (r.ts === null) return true; // 시각 칸이 없으면 오프셋 순서(보낸 뒤 읽은 새 바이트)만 믿는다
  const t = Date.parse(r.ts);
  return Number.isNaN(t) ? true : t >= sentAt - TS_SKEW_MS;
}

export interface ApplyResult {
  msgs: Msg[];
  /** 이번에 근거로 쓴(또는 본) 레코드 uuid — 호출자가 세션별 소비 집합에 더한다 */
  consumed: string[];
  /** 어느 말에도 묶이지 않은 마스터 글(uuid 사슬이 없을 때 등) — 「마스터」 일반 말풍선 */
  stray: Reply[];
}

/** 새로 읽은 레코드들을 말 목록에 반영(순수 · 입력 불변 · 레코드 순서대로). */
export function applyRecords(msgs: readonly Msg[], recs: readonly Rec[], consumed: ReadonlySet<string> = new Set()): ApplyResult {
  const out = msgs.map((m) => ({ ...m, thread: [...m.thread], replies: [...m.replies] }));
  const stray: Reply[] = [];
  // 한 레코드는 한 번만 근거가 된다(codex 1R major — 다시 읽은 기록으로 같은 uuid 를 두 말에 배정하던 길): 이미 짝지은 user·이미 이은 사슬 레코드는 건너뜀.
  const seen = new Set<string>(consumed);
  const used: string[] = [];
  for (const m of out) {
    if (m.userUuid) seen.add(m.userUuid);
    for (const u of m.thread) seen.add(u);
  }
  for (const r of recs) {
    if (r.sidechain) continue;
    if (r.uuid !== null && seen.has(r.uuid)) continue;
    if (r.uuid !== null) {
      seen.add(r.uuid);
      used.push(r.uuid);
    }
    if (r.role === "user") {
      const cand = out
        .filter((m) => AWAITING.has(m.step) && !m.userUuid && m.sentAt !== null && recordAfter(r, m.sentAt))
        .sort((a, b) => (a.sentAt as number) - (b.sentAt as number))
        .find((m) => userRecordMatches(m, r));
      if (cand) {
        cand.userUuid = r.uuid;
        cand.step = "delivered";
        cand.thread = r.uuid ? [r.uuid] : [];
        continue;
      }
      // 글 있는 user 레코드 = 새 사람 차례 → 옛 말들의 사슬을 닫는다(부모가 옛 답이어도 이어 붙이지 않음).
      if (r.text !== null) {
        for (const m of out) if (r.parent && m.thread.includes(r.parent)) m.thread = [];
        continue;
      }
    }
    const owner = r.parent ? out.find((m) => m.thread.includes(r.parent as string)) : undefined;
    if (owner) {
      if (r.uuid) owner.thread.push(r.uuid);
      if (r.role === "assistant" && r.text !== null) {
        owner.replies.push({ uuid: r.uuid, text: r.text });
        if (owner.step === "delivered") owner.step = "replying";
      }
    } else if (r.role === "assistant" && r.text !== null) {
      stray.push({ uuid: r.uuid, text: r.text });
    }
  }
  return { msgs: out, stray, consumed: used };
}

/** 시간·활동에 따른 단계 갱신(순수): 답이 붙은 말은 마스터가 쉬면 「답함」 · 전달된 뒤 마스터가 일하면 「답하는 중」(조각 3) ·
 *  응답 없는 보내기 3초 → 「확인 중」(조각 3) · 근거 없는 대기 120초 → 「오래 걸려요」.
 *  masterWorking = null(모름 · 이 값이 그 기록보다 옛 관측일 수 있음)이면 활동으로는 아무것도 칠하지 않는다. */
export function settleSteps(msgs: readonly Msg[], now: number, masterWorking: boolean | null): Msg[] {
  return msgs.map((m) => {
    if ((m.step === "replying" || m.step === "delivered") && m.replies.length > 0 && masterWorking === false) return { ...m, step: "replied" as Step };
    if (m.step === "delivered" && masterWorking === true) return { ...m, step: "replying" as Step };
    if (m.step === "sending" && m.sentAt !== null && now - m.sentAt >= SENDING_SILENT_MS) return { ...m, step: "checking" as Step, code: "no_answer_yet", note: "보낸 요청의 답을 기다리는 중이에요 — 다시 보내지 않아요." };
    if ((m.step === "injected" || m.step === "checking") && m.sentAt !== null && now - m.sentAt >= SLOW_MS) return { ...m, step: "slow" as Step };
    return m;
  });
}

/** (조각 3) 근거(결속 세션 기록)로 칠한 단계 — 뒤늦게 온 원자 제출 응답(written·불명)이 이것을 「전달 확인 중」으로 되돌리지 않는다. */
const EVIDENCED: ReadonlySet<Step> = new Set<Step>(["delivered", "replying", "replied"]);

/** (조각 3) 원자 제출 응답을 지금 단계에 합친다(순수). 확정(바이트 0 = 붙잡음·정비 보류·못 보냄)은 늘 이긴다 —
 *  그때 세션 기록에서 짝지은 user 레코드는 이 말의 것이 아니었다(같은 글이 다른 길로 들어옴)이므로 짝을 푼다. written·불명은 근거 단계를 되돌리지 않는다. */
export function mergeOutcome(cur: Msg, outcomeStep: Step): Partial<Msg> {
  const definite = outcomeStep === "held" || outcomeStep === "failed" || outcomeStep === "queued_hold";
  if (EVIDENCED.has(cur.step) && !definite) return {};
  if (cur.step === "checking" && cur.code === "refused_at_write" && !definite) return {}; // 쓰기 직전 거부 사건이 응답보다 먼저 왔음 — 그 근거가 「썼음」보다 정확하다
  if (EVIDENCED.has(cur.step) && definite) return { step: outcomeStep, userUuid: null, thread: [], replies: [] };
  return { step: outcomeStep };
}

/** (조각 3) 데몬 `input.refused_at_write`(좌석 = seat · 받은 시각 now) → 그 좌석에 방금 쓴 말 하나를 「확인 중」으로(순수).
 *  본문은 입력줄에 남았고 제출 키만 안 들어갔다 → 다시 보내기 0(사람이 작업 화면에서 Enter·지우기) · 뒤 말은 문턱 `draft` 가 붙잡는다(데몬이 미제출 계수를 되돌림). */
export function applyRefusedAtWrite(msgs: readonly Msg[], seat: number, now: number): Msg[] {
  let pick = -1;
  for (let i = 0; i < msgs.length; i++) {
    const m = msgs[i];
    if (m.seat !== seat || m.sentAt === null || m.userUuid) continue;
    if (m.step !== "sending" && m.step !== "injected" && m.step !== "checking") continue;
    if (now - m.sentAt < 0 || now - m.sentAt > REFUSED_AT_WRITE_WINDOW_MS) continue;
    if (pick < 0 || (msgs[pick].sentAt as number) <= m.sentAt) pick = i;
  }
  if (pick < 0) return [...msgs];
  return msgs.map((m, i) =>
    i === pick ? { ...m, step: "checking" as Step, code: "refused_at_write", note: "마스터 창에 확인할 것이 떠서 보낸 말이 입력줄에 남았을 수 있어요 — 작업 화면에서 확인한 뒤 Enter 를 누르거나 지워 주세요(다시 보내지 않아요)." } : m,
  );
}

/** 다시 보내기 단추를 둘 수 있는가 — 확정 실패 + 아직 다시 보낸 적 없음만(불명·재시도 중·붙잡음 = 0 · 같은 말 두 번 방지). */
export function canRetry(m: Msg): boolean {
  return m.step === "failed" && !m.retried;
}
