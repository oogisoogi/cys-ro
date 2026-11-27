// (cysr-ui-slice1) 보낸 말 단계 판정 — 순수(P2-DESIGN §5-2 · 조각 1 = 사람 말 최소판: 붙잡음·전달 확인 중·전달됨·답하는 중·답함·못 보냄·확인 중·오래 걸려요).
//
// 「전달됨」 = 결속 세션 기록에 **보낸 뒤** · 보낸 글과 **전문 일치**하는 user 레코드(아직 다른 말에 짝지어지지 않은 첫 것)가 나왔을 때만.
// 「답함」 = 그 user 레코드의 uuid 를 부모로 잇는 사슬 위 assistant 글 + 마스터 활동 쉼. 근거가 없으면 칠하지 않는다(「모름」 = 확인 중).
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지(시각은 인자).

import { appendStepsTo, stepsOf, type ProgDropped, type ProgStep } from "./progress";

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
/** (조각 3 고침 · 검증 지적 A · 실측) 진짜 Claude Code(2.1.32x) 기록은 붙여넣은 사람 글을 이 꼴로 감싸 남기는 일이 있다 —
 *  `\n\n<pasted_content id="N">\n` + 글 + `\n</pasted_content id="N">\n`(id = 영숫자 · 여는·닫는 id 같음 · 이 기기 실측 `3943`·`3f02`).
 *  감싼 **속 글이 보낸 글과 글자 하나까지 같을 때만** 전문 일치로 본다(감싼 밖에 다른 글 = 불일치 = 모름 유지).
 *  ⚠실측(이 좌석 기록 1건): 속 글 안의 `<pasted_content`·`</pasted_content` 는 `<\pasted_content`·`<\/pasted_content` 로 바뀌어 남는다 —
 *  그런 글은 속 글이 원문과 달라 모름으로 남는다(되돌려 맞추지 않음 · 보수 쪽). */
export const PASTE_WRAP = /^\n\n<pasted_content id="([0-9A-Za-z]{1,32})">\n([\s\S]*)\n<\/pasted_content id="\1">\n$/;
/** M8(세션 레코드에 uuid/parentUuid 가 있는가) — **측정 대기**. 없으면 답을 그 말에 묶지 않는다(「답함」 0 · 말풍선은 「마스터」 일반 줄로). */
export const M8_UUID_CHAIN: "unmeasured" | "present" | "absent" = "unmeasured";
/** (조각 3) 원자 제출 요청이 이만큼 응답 없이 걸려 있으면 「보내는 중」 → 「확인 중」(§5-2 「근거 3초 넘게 없음」 · PRD M2 3초). 응답이 오면 그 응답으로 바뀐다. */
export const SENDING_SILENT_MS = 3_000;
/** (조각 3) 데몬 `input.refused_at_write`(쓰기 직전 재판정 · 제출 키를 쓰지 않음)를 보낸 말에 잇는 창.
 *  ⚠출처(검토 지적 1 · 코드 확인): 기준판 3a012bf4 에서는 이 사건을 `surface.send_key` 거부 모드(handlers.rs approval_write_guard)만 낸다 —
 *  대화 화면 원자 제출(Inject guard:None · handlers.rs:3779~3785)은 내지 않는다. 데몬 고침 integ/1116-backlog e4499d72 의
 *  `approval_enter_guard` 가 **원자 제출 Enter 직전 거부에 같은 이름·같은 칸**으로 낸다(통합 빌드에서 이 짝짓기가 뜻을 가짐).
 *  ★1.1.16(S3-1): 원자 제출 거부 사건에는 데몬이 요청 번호(`request_id`)를 싣는다 → 번호로만 짝짓는다(applyRefusedById) · 이 창 규칙은 **번호 없는 사건**
 *  (send_key 거부 모드 · 옛 데몬)에만 남는다 — 그때는 다른 호출자의 사건이 붙을 수 있어 단계는 「확인 중」(모름)만 · 세션 기록이 오면 전달됨으로 고쳐짐 · 다시 보내기 0.
 *  그 사건에는 요청 번호가 없다 → 같은 좌석 · 보낸 지 이 시간 안 · 아직 증거 없는 **가장 최근** 말 하나만(쓰기는 한 번에 1건이라 겹치지 않음).
 *  창 = 원자 제출 최대 0.84초(0.5 M1) + 사건 전달 여유. 설계 목표값. */
export const REFUSED_AT_WRITE_WINDOW_MS = 5_000;
/** 사건 시각(데몬 timestamp)이 보낸 시각보다 이만큼 앞서도 같은 쓰기로 본다(같은 기계 · 시각 찍는 자리 차이). */
export const REFUSED_AT_WRITE_SKEW_MS = 1_000;

export type Step = "held" | "sending" | "injected" | "accepted" | "delivered" | "replying" | "replied" | "failed" | "checking" | "slow" | "queued_hold";

export const STEP_LABEL: Record<Step, string> = {
  // (TICKET=cysr-1121-ui K-1 · 11-27 사용자 「붙잡아둠 … 제가 인지 하지 못하는 건가요?」) 「붙잡아 둠」은 문제가 난 것처럼 읽혔다 —
  //   자동으로 나갈 말 = 「보낼 차례 기다림」(사람 손 필요 없음) · 눌러야 나갈 말은 화면이 HELD_CLICK_LABEL 로 따로 적는다(core.needsClick).
  held: "보낼 차례 기다림",
  sending: "보내는 중",
  injected: "전달 확인 중",
  // (K-3 · U25 실측) 마스터가 바쁠 때 넘긴 말을 Claude Code 가 받아 뒀다(세션 기록 queue-operation enqueue) — 하던 일 경계에서 읽는다.
  accepted: "마스터가 받아 둠",
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
  /** (조각 3 고침 · 검증 지적 B) 어느 말에도 안 묶인 답의 시각(ms · 기록 시각 · 없으면 읽은 시각) — 화면이 시각순으로 끼워 그림 */
  at?: number;
}

export interface Msg {
  id: string;
  /** composeOutbound 를 거친 글(사람이 쓴 원문 · 데몬에 보낸 바이트와 같은 글 — ★(K R1) 10분 표지를 붙여 보낸 시도는 그 바이트가 sentText) */
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
  /** ★1.1.16(TICKET=cysr-1116-debt-d-1119 · S3-1): 원자 제출 응답의 데몬 요청 번호(`result.request_id`) — 쓰기 직전 거부 사건을 번호로 짝짓는다 */
  requestId?: string;
  /** (조각 3) 원자 제출을 보낸 마스터 좌석 번호 — 좌석에 걸린 데몬 사건(쓰기 직전 거부)을 이 말에 잇는 데 씀 */
  seat?: number;
  /** (TICKET=cysr-1121-ui K-2) 이 말을 받아들일 때 본 마스터 좌석·사람 입력 표지("" = 그때 입력 없음) — 10분이 지나도 이 뒤로 다른 길 사람 입력이 없으면 자동으로 보낸다.
   *  없음(그때 마스터 상태를 몰랐음 · 옛 저장본) = 종전대로 10분 뒤 사람 클릭. */
  heldSeat?: number;
  heldStamp?: string;
  /** (TICKET=cysr-1121-ui K R1) 이번 시도에 실제로 보낸 글(10분 넘은 말 = 「(N분 전에 쓰신 말) 」 + 원문 · 그 밖 = 원문) — 세션 기록 짝짓기에만 씀.
   *  `text`(원문)는 끝까지 바꾸지 않는다: 같은 말 겹침·붙잡음 저장·다시 보내기·「이 말 보내기」는 원문으로 판단 · 붙잡음으로 돌아가면 지운다(다음 시도가 원문에서 표지를 새로 만듦 · 겹침 0). */
  sentText?: string;
  /** (TICKET=cysr-1121-ui K R1) 하던 일 중간에 받아 읽힌 말(세션 기록 `attachment.queued_command` 로 짝지음) — 답에 하던 일 이야기가 섞일 수 있다. */
  absorbed?: boolean;
  /** (TICKET=cysr-1121-ui K R1) 같은 경계에서 뒤 말과 함께 받아 읽혔다(뒤 말 id) — ★(kfix ③) 그 뒤 마스터 글은 어느 말에도 붙이지 않는다(일반 「마스터」 줄). */
  withNext?: string;
  /** (TICKET=cysr-1121-ui-kfix ②) 이번 시도의 원자 제출에 데몬이 「썼음」(written)이라고 답했다 — 세션 기록의 같은 글을 이 말의 것으로 확정할 근거. 붙잡음으로 돌아가면 지운다. */
  wrote?: boolean;
  /** (kfix ②) 같은 글 기록을 이 말에 붙였지만 이 화면 제출이 쓰였는지 모른다(불명·응답 전) — 다른 길로 들어온 같은 글일 수 있어 「전달됨/받아 둠」으로 부르지 않는다.
   *  뒤이어 written 응답이 오면 지운다(confirmWritten). 답은 그대로 붙인다(그 글에 대한 답인 것은 사실). */
  unsure?: boolean;
  /** (kfix ④) 이 말과 같은 글이 마스터 쪽 대기에 들어간 것을 봤다(queue-operation enqueue) — 단계가 바뀌어도(오래 걸려요 등) 대기에서 빠짐(remove)을 이 말에 잇는 근거. */
  queuedSeen?: boolean;
  /** (TICKET=cysr-chat-held-win · ⓑ) 상태 확인 늦음으로 연달아 붙잡힌 횟수 — 상태가 한 번 제때 확인되면 지움 */
  slowHolds?: number;
  /** (TICKET=cysr-1118-ui ①) 이 말에 이어진 마스터 과정(도구·중간 글·생각 표지) — 진행 줄·「과정 보기」 재료 · 메모리만(화면 저장소 0 = NFR-S3) */
  steps?: ProgStep[];
  /** (TICKET=cysr-1119-s4 · F25) 단계 상한(PROG_MAX)으로 앞에서 버린 단계의 분류별 수 — 과정 요약 셈 = 남은 단계 + 이것 */
  stepsDropped?: ProgDropped;
  /** (TICKET=cysr-1118u-chat ③) 이 말의 턴이 끝났다 — 세션 기록에 이 말 사슬 뒤로 **다른 글 있는 user 레코드**(중계·작업 화면 직접 입력·알림 등 새 차례)가 왔다.
   *  이 뒤로는 마스터 활동으로 「답하는 중」을 다시 칠하지 않는다(그 활동은 새 차례의 일이다) · 진행 줄도 달지 않는다. */
  turnClosed?: boolean;
  /** (TICKET=cysr-1118u-chat ③) 사슬에 마지막으로 이은 레코드 종류(고리 제외) — "result" = 도구 결과(user · 글 없음) 뒤 = 아직 턴 안.
   *  도구 결과 바로 뒤의 글 있는 user 레코드(그림 안내 · 스킬 본문 · 중단 표지 — 실측 표본 107건)는 새 차례가 아니라 같은 턴의 고리다. */
  tail?: "assistant" | "result";
}

/** (K-1) 사람이 눌러야만 나가는 붙잡은 말의 단계 이름 — 「아직 안 보냈다」가 첫 마디(11-26 윈 제보 「보냈다고 여김」). */
export const HELD_CLICK_LABEL = "아직 안 보냄";
/** (K-3) 받아 둔 말의 안내 — 작업 화면에서 바쁠 때 친 말과 같은 길(마스터가 하던 일의 다음 경계에서 읽음). */
export const ACCEPTED_NOTE = "마스터가 받아 뒀어요 — 하던 일을 잠깐 멈출 때 읽어요(작업 화면에서 바쁠 때 친 말과 같아요).";
/** (TICKET=cysr-1121-ui K R1) 받아 둔 말이 마스터 쪽 대기에서 흡수가 아닌 까닭으로 빠졌다(사람이 Claude Code 에서 대기 말을 거둠 등 · 까닭 꼴 미실측) — 확인 불가 · 다시 보내기 0.
 *  ★(kfix ④) 종결 상태다: 「오래 걸려요」로 넘어가지 않고 · 같은 글 새 말을 막지 않는다(사람이 다시 치면 새 말로 나감 · 저절로 다시 보내기는 0). */
export const QUEUE_REMOVED = "queue_removed";
export const QUEUE_REMOVED_LABEL = "대기에서 빠짐";
export const QUEUE_REMOVED_NOTE = "마스터 쪽 대기에서 빠졌어요 — 마스터가 이 말을 읽지 않았을 수 있어요. 필요하면 다시 보내 주세요(저절로 다시 보내지 않아요).";
/** (TICKET=cysr-1121-ui K R1) 하던 일 중간에 받아 읽힌 말(U25-B 실측: 앞 일의 「DONE」과 이 말 확인이 한 답에 섞임).
 *  ★(kfix ③) 그 뒤 마스터 글은 이 말의 답으로 붙이지 않는다 — 앞 일 이야기와 섞인 글이라 일반 「마스터」 줄로(답함 판정 0). */
export const ABSORBED_NOTE = "하던 일 중간에 받아 읽었어요 — 그 뒤 마스터 글은 하던 일 이야기와 섞여 있어 아래 「마스터」 줄로 따로 보여요";
/** (TICKET=cysr-1121-ui K R1) 같은 경계에서 뒤 말과 함께 받아 읽힌 앞 말(U25-D 실측: 말 1·말 2 확인이 한 답). */
export const WITH_NEXT_NOTE = "다음 말과 함께 받아 읽었어요 — 그 뒤 마스터 글은 아래 「마스터」 줄로 따로 보여요";
/** (kfix ②) 같은 글이 마스터 기록에 보이지만 이 화면 제출이 쓰였는지 모름 — 「전달됨」 대신 이 단계 이름·안내. */
export const UNSURE_LABEL = "확인 못 함";
export const UNSURE_NOTE = "마스터 기록에 같은 글이 보여요 — 이 화면에서 보낸 말이 전해진 것인지는 확인할 수 없어요(다른 길로 같은 글이 들어왔을 수 있어요 · 다시 보내지 않아요).";

/** (kfix ②·④) 말 한 건의 단계 이름 — 화면은 STEP_LABEL[m.step] 대신 이것을 쓴다. */
export function stepLabel(m: Msg): string {
  if (m.step === "checking" && m.code === QUEUE_REMOVED) return QUEUE_REMOVED_LABEL;
  if (m.unsure && (m.step === "accepted" || EVIDENCED.has(m.step))) return UNSURE_LABEL;
  return STEP_LABEL[m.step];
}

/** (kfix ②) 원자 제출 응답이 written 일 때 그 말에 합칠 것(순수) — 「썼음」 표지 + 출처 불명 표지 풀기(같은 글 기록이 이 말의 것이라는 근거가 왔다). */
export function confirmWritten(m: Msg): Partial<Msg> {
  return m.unsure ? { wrote: true, unsure: undefined, note: m.note === UNSURE_NOTE ? undefined : m.note } : { wrote: true };
}

/** (kfix ②) 같은 글 기록을 이 말에 붙일 때의 출처 표지 — 데몬이 썼다고 답한 시도만 확정 · 그 밖(응답 전·불명) = 확인 못 함. */
function sureness(m: Msg, note: string | undefined): Pick<Msg, "unsure" | "note"> {
  return m.wrote === true ? { unsure: undefined, note } : { unsure: true, note: UNSURE_NOTE };
}

/** (kfix ④) 대기에서 빠진(종결) 말 — 같은 글 기록 짝 후보는 맨 뒤(새로 보낸 같은 글 말이 먼저). */
function removedLast(a: Msg, b: Msg): number {
  return Number(a.code === QUEUE_REMOVED) - Number(b.code === QUEUE_REMOVED) || (a.sentAt as number) - (b.sentAt as number);
}

export interface Rec {
  uuid: string | null;
  parent: string | null;
  /** (조각 3 고침 · 검증 지적 B) "link" = user·assistant 밖 종류(attachment·system 등) — 글 0자 · uuid·부모만(사슬을 잇는 고리 · NFR-S3)
   *  (K-3) "queued" = 마스터가 바쁠 때 받아 둔 말(queue-operation enqueue · uuid 없음 · 원문) — 사슬 밖 · 「받아 둠」 증거로만
   *  (K R1) "queue_removed" = 받아 둔 말이 흡수(absorbed_mid_turn) 아닌 까닭으로 대기에서 빠짐(queue-operation remove 등 · uuid 없음 · 원문) — 사슬 밖 */
  role: "user" | "assistant" | "link" | "queued" | "queue_removed";
  text: string | null;
  parts?: string[] | null;
  ts: string | null;
  sidechain?: boolean;
  /** (조각 4 · codex 1R minor) 그 줄이 시작하는 파일 바이트 위치(viewcore.rs read_transcript_from) — 앞 훑기·뒤 읽기 겹침을 위치로 가른다 */
  at?: number;
  /** (TICKET=cysr-1118-ui ①) 마스터 레코드의 도구 호출(이름 + 짧은 단서 · viewcore.rs tool_steps) · 없으면 null */
  tools?: { name: string; hint: string | null }[] | null;
  /** (TICKET=cysr-1118-ui ①) 생각 조각(내용은 빈 칸)이 있었는가 */
  thinking?: boolean;
  /** (TICKET=cysr-1121-ui K R1) user 레코드가 `attachment.queued_command`(하던 일 중간 흡수)에서 왔다 */
  queued?: boolean;
  /** (TICKET=cysr-1121-ui K R1) queue_removed 의 까닭(Claude Code `reason` · 없으면 null) */
  reason?: string | null;
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

// (조각 3 고침 · 검증 지적 C) 「보내는 중」(보낸 시각 있음 · 응답이 아직 안 옴)도 짝 후보 — 응답이 걸린 사이 읽힌 자기 레코드를 놓치지 않게.
const AWAITING: ReadonlySet<Step> = new Set<Step>(["sending", "injected", "accepted", "checking", "slow"]); // (K-3) 받아 둔 말도 흡수·턴 끝 user 레코드를 기다린다

export function normRecordText(t: string): string {
  return t.replace(/\r\n?/g, "\n").replace(/^\s+/, "").replace(/\s+$/, "");
}

/** 레코드 글 하나가 보낸 글인가(순수): 감싼 꼴(PASTE_WRAP)로 읽히면 **속 글 비교만**(글자 하나까지 · 정규화 없음) · 아니면 정규화 전문 비교.
 *  (codex 2R blocking) 감싼 꼴을 일반 정규화 비교로도 통과시키면, 보낸 글이 감싼 꼴 자체일 때 속 글이 달라도 일치가 되던 길을 막는다. */
function recordTextIs(raw: string, text: string): boolean {
  const w = PASTE_WRAP.exec(raw);
  return w !== null ? w[2] === text : normRecordText(raw) === text;
}

/** (TICKET=cysr-1121-ui K R1) 세션 기록과 대조할 글 = 이번 시도에 실제로 보낸 글(없으면 원문). */
function wireText(m: Msg): string {
  return m.sentText ?? m.text;
}

/** user 레코드가 이 말인가 — 전문 일치 · 또는 감싼 꼴의 속 글 전문 일치(검증 지적 A). 조각이 여럿이면 조각 하나가 같아도 된다(훅이 덧붙인 글 조각).
 *  (K R1) 대조 글 = 이번 시도에 보낸 글(sentText ?? text). */
export function userRecordMatches(m: Msg, r: Rec): boolean {
  if (r.role !== "user" || r.text === null || r.sidechain) return false;
  const t = wireText(m);
  if (recordTextIs(r.text, t)) return true;
  return Array.isArray(r.parts) && r.parts.some((p) => recordTextIs(p, t));
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
  /** (조각 3 고침 · 검증 지적 C) 짝을 못 찾은 글 있는 user 레코드 — 「본 것」으로 소비하지 않는다(뒤에 그 말이 짝 후보가 되면 rematchPending 으로 다시) */
  unmatched: Rec[];
  /** (TICKET=cysr-1121-ui-kfix ①) 이 화면 말과 짝 안 된 대기 들어감(queue-operation enqueue) — 다른 길 사람 입력 근거(10분 넘은 말 자동 금지 · 아직 흡수 전이라 unmatched 에 안 잡힘). */
  foreignQueued: Rec[];
}

/** 새로 읽은 레코드들을 말 목록에 반영(순수 · 입력 불변 · 레코드 순서대로).
 *  ⚠(TICKET=cysr-1121-ui K R1 · 알려진 한계) 짝짓기 근거는 글·시각뿐이다 — 다른 길(작업 화면·RC·다른 기기)로 같은 시각대에 같은 글이 들어오면 이 화면의 말로 짝지을 수 있다(1.1.18 부터의 user 레코드 짝짓기 한계 · 출처 구별 정보 없음). */
export function applyRecords(msgs: readonly Msg[], recs: readonly Rec[], consumed: ReadonlySet<string> = new Set()): ApplyResult {
  const out = msgs.map((m) => ({ ...m, thread: [...m.thread], replies: [...m.replies] }));
  const stray: Reply[] = [];
  const unmatched: Rec[] = [];
  const foreignQueued: Rec[] = [];
  // 한 레코드는 한 번만 근거가 된다(codex 1R major — 다시 읽은 기록으로 같은 uuid 를 두 말에 배정하던 길): 이미 짝지은 user·이미 이은 사슬 레코드는 건너뜀.
  const seen = new Set<string>(consumed);
  const used: string[] = [];
  for (const m of out) {
    if (m.userUuid) seen.add(m.userUuid);
    for (const u of m.thread) seen.add(u);
  }
  for (const r of recs) {
    if (r.sidechain) continue;
    if (r.role === "queued") {
      // (K-3) 받아 둠 증거 — 아직 짝 없는(보낸 뒤) 같은 글 말 가장 오래된 하나를 「마스터가 받아 둠」으로. 사슬·소비·턴 닫기에 쓰지 않는다(uuid 없음).
      const q = out
        .filter((m) => (m.step === "sending" || m.step === "injected" || m.step === "checking" || m.step === "slow") && m.code !== QUEUE_REMOVED && !m.queuedSeen && !m.userUuid && m.sentAt !== null && r.text !== null && recordAfter(r, m.sentAt))
        .sort((a, b) => (a.sentAt as number) - (b.sentAt as number))
        .find((m) => recordTextIs(r.text as string, wireText(m)));
      if (q) {
        q.step = "accepted";
        q.code = undefined;
        q.queuedSeen = true; // (kfix ④) 단계가 「오래 걸려요」로 바뀌어도 대기에서 빠짐을 이 말에 잇는다
        Object.assign(q, sureness(q, ACCEPTED_NOTE)); // (kfix ②) 쓰였는지 모르는 시도 = 「받아 둠」 아님(확인 못 함)
      } else if (r.text !== null) foreignQueued.push(r); // (kfix ①) 남의 대기 들어감 = 다른 길 사람 입력
      continue;
    }
    if (r.role === "queue_removed") {
      // (TICKET=cysr-1121-ui K R1) 받아 둔 말이 흡수가 아닌 까닭으로 대기에서 빠졌다(사람이 거둠 등 · 까닭 꼴 모름 포함) — 「받아 둠」을 사실로 두지 않고 확인 불가로.
      //   다시 보내기 0(바이트는 이미 넘어갔다) · 뒤에 같은 글 user 레코드가 오면 checking 도 짝 후보라 「전달됨」으로 고쳐진다.
      //   ★(kfix ④) 「받아 둠」 단계만이 아니라 대기에 들어간 것을 본 말(queuedSeen)이면 단계 무관(오래 걸려요·확인 중 · 응답 전 포함) — 단계는 늦은 응답·시간으로 바뀌지만 대기 생명주기는 그대로다.
      const q = out
        .filter((m) => m.queuedSeen === true && m.code !== QUEUE_REMOVED && !m.userUuid && !EVIDENCED.has(m.step) && m.step !== "held" && m.step !== "failed" && m.sentAt !== null && r.text !== null && recordAfter(r, m.sentAt))
        .sort((a, b) => (a.sentAt as number) - (b.sentAt as number))
        .find((m) => recordTextIs(r.text as string, wireText(m)));
      if (q) {
        q.step = "checking";
        q.code = QUEUE_REMOVED;
        q.note = QUEUE_REMOVED_NOTE;
        q.unsure = undefined;
      }
      continue;
    }
    if (r.uuid !== null && seen.has(r.uuid)) continue;
    // 짝 없는 사람 글은 소비하지 않는다(아래에서 짝을 찾았을 때만 seen·used 에 넣음 · 검증 지적 C)
    const pendingHuman = r.role === "user" && r.text !== null;
    if (r.uuid !== null && !pendingHuman) {
      seen.add(r.uuid);
      used.push(r.uuid);
    }
    if (r.role === "user") {
      const cand = out
        .filter((m) => AWAITING.has(m.step) && !m.userUuid && m.sentAt !== null && recordAfter(r, m.sentAt))
        .sort(removedLast)
        .find((m) => userRecordMatches(m, r));
      if (cand) {
        if (r.uuid !== null) {
          seen.add(r.uuid);
          used.push(r.uuid);
        }
        if (r.queued === true) {
          // (TICKET=cysr-1121-ui K R1) 하던 일 중간 흡수 — 같은 경계에서 앞서 흡수된 말(아직 답 글 없음)의 사슬에 이어 붙었으면 두 말이 한 답을 받는다(U25-D).
          //   답은 뒤 말에 붙으므로 앞 말엔 「다음 말과 함께」 표지만(귀속 규칙은 그대로).
          const prev = r.parent ? out.find((m) => m !== cand && m.absorbed === true && m.replies.length === 0 && m.thread.includes(r.parent as string)) : undefined;
          if (prev) prev.withNext = cand.id;
        }
        cand.absorbed = r.queued === true ? true : undefined;
        cand.withNext = undefined;
        cand.userUuid = r.uuid;
        cand.step = "delivered";
        cand.code = undefined; // (조각 3 · 검토 지적 4) 근거가 왔으니 옛 「확인 중」 까닭·안내를 지운다
        Object.assign(cand, sureness(cand, undefined)); // (kfix ②) 쓰였는지 모르는 시도 = 「전달됨」 아님(확인 못 함 · 답은 붙임)
        cand.thread = r.uuid ? [r.uuid] : [];
        cand.tail = undefined;
        cand.turnClosed = undefined; // (codex 1R major) 새 결속 = 새 턴 — 앞 결속의 턴 끝 표지를 이월하지 않는다
        continue;
      }
      // 글 있는 user 레코드 = 새 사람 차례 → 옛 말들의 사슬을 닫는다(부모가 옛 답이어도 이어 붙이지 않음).
      if (r.text !== null) {
        // (TICKET=cysr-1118u-chat ③) 단 도구 결과 바로 뒤에 온 것은 턴 안의 덧붙임(isMeta 그림 안내·스킬 본문·중단 표지)이다 — 새 차례로 닫지 않고 고리로 잇는다.
        //   (새 차례 = 앞 턴 끝(assistant) 뒤에 오는 사람 말·중계(peer)·알림·예약 — 실측 표본: 턴 시작 user 레코드의 가장 가까운 앞 레코드 = assistant end_turn·stop_sequence)
        const mid = r.parent ? out.find((m) => m.tail === "result" && m.thread.includes(r.parent as string)) : undefined;
        if (mid) {
          if (r.uuid !== null) {
            seen.add(r.uuid);
            used.push(r.uuid);
            mid.thread.push(r.uuid);
          }
          mid.tail = undefined; // 덧붙임 바로 뒤의 글 있는 user(예: 중단 표지 뒤 새로 친 말)는 새 차례로 닫힌다
          continue;
        }
        for (const m of out)
          if (r.parent && m.thread.includes(r.parent)) {
            m.thread = [];
            // (TICKET=cysr-1118u-chat ③) 윈 1.1.17 관찰: 중계(RC 다리 · origin.kind "peer" · isMeta user 레코드)로 시작한 턴의 진행 줄이 앞 사람 말 밑에 「답하는 중」으로 붙음.
            //   사슬은 여기서 닫혔지만 이 말의 단계는 그대로라 settleSteps 가 마스터 활동(새 차례의 일)으로 다시 「답하는 중」을 칠했다 → 턴 끝을 단계에 남긴다.
            if (EVIDENCED.has(m.step)) {
              m.turnClosed = true;
              if (m.step === "replying") m.step = m.replies.length > 0 ? "replied" : "delivered";
            }
          }
        unmatched.push(r);
        continue;
      }
    }
    const owner = r.parent ? out.find((m) => m.thread.includes(r.parent as string)) : undefined;
    if (owner) {
      if (r.uuid) owner.thread.push(r.uuid);
      if (r.role === "assistant") owner.tail = "assistant";
      else if (r.role === "user") owner.tail = "result"; // (TICKET=cysr-1118u-chat ③) 글 없는 user = 도구 결과
      if (r.role === "assistant") appendStepsTo(owner, stepsOf(r)); // (TICKET=cysr-1118-ui ①) 진행 줄 재료 · (cysr-1119-s4 F25) 버린 수 보존
      if (r.role === "assistant" && r.text !== null) {
        if (owner.absorbed) {
          // (TICKET=cysr-1121-ui-kfix ③) 하던 일 중간에 받아 읽힌 말 뒤의 글 = 앞 일 출력과 이 말(들) 확인이 섞인 한 답(U25-B·D 실측) —
          //   이 말의 답으로 붙이지 않고 「답함」도 칠하지 않는다(일반 「마스터」 줄 · 시각순). 사슬은 계속 이어 턴 끝·진행 줄 판정은 그대로.
          const at = r.ts === null ? NaN : Date.parse(r.ts);
          stray.push(Number.isNaN(at) ? { uuid: r.uuid, text: r.text } : { uuid: r.uuid, text: r.text, at });
        } else {
          owner.replies.push({ uuid: r.uuid, text: r.text });
          if (owner.step === "delivered") owner.step = "replying";
        }
      }
    } else if (r.role === "assistant" && r.text !== null) {
      const at = r.ts === null ? NaN : Date.parse(r.ts);
      stray.push(Number.isNaN(at) ? { uuid: r.uuid, text: r.text } : { uuid: r.uuid, text: r.text, at });
    }
  }
  return { msgs: out, stray, consumed: used, unmatched, foreignQueued };
}

/** (조각 3 고침 · 검증 지적 C) 앞서 짝을 못 찾은 사람 레코드를 지금 말 목록에 다시 대어 본다(순수 · 짝만 · 사슬 닫기는 안 함).
 *  짝을 찾은 레코드는 pool 에서 빠진다(한 레코드 = 한 말).
 *  ★(codex 1R·2R blocking) 레코드를 **본 시각(seenAt)보다 앞서 이미 보낸** 말에만 짝짓는다(같은 밀리초 = 선후 모름 → 짝 안 함 · 모름) — 보내기 전에 읽은 레코드(다른 길·시각 없는 레코드 포함)가
 *  뒤에 보낸 같은 글 말의 「전달됨」 근거가 되지 않게(쓰기 직전 patchMsg 때 붙어 쓰기가 불명이어도 남던 길 · I2). */
export interface PendingRec {
  r: Rec;
  seenAt: number;
}
export function rematchPending(msgs: readonly Msg[], pool: readonly PendingRec[]): { msgs: Msg[]; pool: PendingRec[]; changed: boolean } {
  let changed = false;
  const out = [...msgs];
  const left: PendingRec[] = [];
  for (const p of pool) {
    const r = p.r;
    let hit = -1;
    for (let i = 0; i < out.length; i++) {
      const m = out[i];
      if (!AWAITING.has(m.step) || m.userUuid || m.sentAt === null || m.sentAt >= p.seenAt || !recordAfter(r, m.sentAt) || !userRecordMatches(m, r)) continue;
      if (hit < 0 || removedLast(m, out[hit]) < 0) hit = i; // (kfix ④) 대기에서 빠진 말은 맨 뒤 후보
    }
    if (hit < 0) {
      left.push(p);
      continue;
    }
    out[hit] = { ...out[hit], userUuid: r.uuid, step: "delivered", code: undefined, ...sureness(out[hit], undefined), thread: r.uuid ? [r.uuid] : [], tail: undefined, turnClosed: undefined, absorbed: r.queued === true ? true : undefined, withNext: undefined }; // (TICKET=cysr-1118u-chat ③ · codex 1R major) 새 결속 = 턴 끝 표지 이월 0 · (kfix ②) 출처 표지
    changed = true;
  }
  return { msgs: out, pool: left, changed };
}

/** 시간·활동에 따른 단계 갱신(순수): 답이 붙은 말은 마스터가 쉬면 「답함」 · 전달된 뒤 마스터가 일하면 「답하는 중」(조각 3) ·
 *  응답 없는 보내기 3초 → 「확인 중」(조각 3) · 근거 없는 대기 120초 → 「오래 걸려요」.
 *  masterWorking = null(모름 · 이 값이 그 기록보다 옛 관측일 수 있음)이면 활동으로는 아무것도 칠하지 않는다. */
export function settleSteps(msgs: readonly Msg[], now: number, masterWorking: boolean | null): Msg[] {
  // 활동으로 「답하는 중」을 칠할 수 있는 말 = 전달된 말 가운데 **가장 최근 하나**뿐(앞 말들은 뒤 말이 덮음 · 검토 지적 2).
  let newest: Msg | null = null;
  for (const m of msgs) if ((m.step === "delivered" || m.step === "replying" || m.step === "replied") && m.sentAt !== null && (newest === null || (newest.sentAt as number) <= m.sentAt)) newest = m;
  return msgs.map((m) => {
    if (m.turnClosed && (m.step === "replying" || m.step === "delivered")) return m.replies.length > 0 ? { ...m, step: "replied" as Step } : m.step === "replying" ? { ...m, step: "delivered" as Step } : m; // (TICKET=cysr-1118u-chat ③) 턴이 끝난 말 = 활동으로 칠하지 않음
    if ((m.step === "replying" || m.step === "delivered") && m.replies.length > 0 && masterWorking === false) return { ...m, step: "replied" as Step };
    if (m.step === "replying" && m.replies.length === 0 && (masterWorking === false || m !== newest)) return { ...m, step: "delivered" as Step }; // 답 글 없이 쉼 · 더 새 말이 있음 = 「전달됨」으로(답하는 중이 굳지 않게)
    if (m.step === "delivered" && masterWorking === true && m === newest) return { ...m, step: "replying" as Step };
    if (m.step === "sending" && m.sentAt !== null && now - m.sentAt >= SENDING_SILENT_MS) return { ...m, step: "checking" as Step, code: "no_answer_yet", note: "보낸 요청의 답을 기다리는 중이에요 — 다시 보내지 않아요." };
    if ((m.step === "injected" || m.step === "checking") && m.code !== QUEUE_REMOVED && m.sentAt !== null && now - m.sentAt >= SLOW_MS) return { ...m, step: "slow" as Step }; // (kfix ④) 대기에서 빠짐 = 종결(오래 걸려요 아님)
    // (K-3) 받아 둔 말 = 마스터가 일하는 동안은 오래 걸려도 정상(하던 일 경계에서 읽음) · 마스터가 쉬는데도 120초 넘게 안 읽혔을 때만 「오래 걸려요」
    if (m.step === "accepted" && m.sentAt !== null && masterWorking === false && now - m.sentAt >= SLOW_MS) return { ...m, step: "slow" as Step };
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
  if ((cur.step === "accepted" || cur.queuedSeen === true) && !definite) return {}; // (K-3) 「받아 둠」 근거가 늦게 온 written·불명 응답보다 정확하다 · (kfix ④) 받아 둔 뒤 「오래 걸려요」가 된 말도
  if (cur.step === "accepted" && definite) return { step: outcomeStep, unsure: undefined, queuedSeen: undefined }; // (kfix) 바이트 0 확정 = 그 대기 말은 이 화면 것이 아니었다
  if (cur.step === "checking" && cur.code === "refused_at_write" && !definite) return {}; // 쓰기 직전 거부 사건이 응답보다 먼저 왔음 — 그 근거가 「썼음」보다 정확하다
  if (cur.code === QUEUE_REMOVED && !definite) return {};
  if (cur.code === QUEUE_REMOVED && definite) return { step: outcomeStep, unsure: undefined, queuedSeen: undefined }; // (kfix ④) 대기에서 빠짐을 본 뒤 온 늦은 written·불명 응답이 그 안내를 덮지 않는다(확정 = 바이트 0 은 그대로 이김)
  if (EVIDENCED.has(cur.step) && definite) return { step: outcomeStep, userUuid: null, thread: [], replies: [], steps: undefined, stepsDropped: undefined, tail: undefined, turnClosed: undefined, absorbed: undefined, withNext: undefined, unsure: undefined, queuedSeen: undefined }; // (codex 1R major) 결속을 풀면 턴 끝 표지도 푼다
  return { step: outcomeStep };
}

/** (조각 3) 데몬 `input.refused_at_write`(좌석 = seat · 받은 시각 now) → 그 좌석에 방금 쓴 말 하나를 「확인 중」으로(순수).
 *  본문은 입력줄에 남았고 제출 키만 안 들어갔다 → 다시 보내기 0(사람이 작업 화면에서 Enter·지우기) · 뒤 말은 문턱 `draft` 가 붙잡는다(데몬이 미제출 계수를 되돌림). */
export function applyRefusedAtWrite(msgs: readonly Msg[], seat: number, now: number): Msg[] {
  let pick = -1;
  for (let i = 0; i < msgs.length; i++) {
    const m = msgs[i];
    if (m.seat !== seat || m.sentAt === null) continue;
    if (m.step !== "sending" && m.step !== "injected" && m.step !== "checking") continue; // 전달됨 이상(근거 있음)·붙잡음은 제외
    if (now - m.sentAt < -REFUSED_AT_WRITE_SKEW_MS || now - m.sentAt > REFUSED_AT_WRITE_WINDOW_MS) continue;
    if (pick < 0 || (msgs[pick].sentAt as number) <= m.sentAt) pick = i;
  }
  if (pick < 0) return [...msgs];
  return msgs.map((m, i) =>
    i === pick ? { ...m, step: "checking" as Step, code: "refused_at_write", note: REFUSED_AT_WRITE_NOTE } : m,
  );
}

const REFUSED_AT_WRITE_NOTE = "마스터 창에 확인할 것이 떠서 이 말의 제출이 멈췄을 수 있어요 — 작업 화면에서 마스터 창을 살펴봐 주세요. 확인 창이 떠 있으면 그 창부터 답해 주세요(이 말은 다시 보내지 않아요).";

/** ★1.1.16(TICKET=cysr-1116-debt-d-1119 · S3-1) 데몬 `input.refused_at_write` 에 요청 번호가 실렸을 때(원자 제출 Enter 직전 거부 ·
 *  handlers.rs approval_enter_guard) → **그 번호의 말 하나만** 「확인 중」으로(순수). 좌석·5초 창 짝짓기는 번호 없는 사건(send_key 거부 모드)에만 남는다.
 *  돌려주는 것 = [새 목록, 짝 찾음] — 짝이 없으면(응답보다 사건이 먼저 옴) 부르는 쪽이 번호를 잠시 기억해 응답이 오면 다시 부른다. */
export function applyRefusedById(msgs: readonly Msg[], requestId: string): [Msg[], boolean] {
  const i = msgs.findIndex((m) => m.requestId === requestId);
  if (i < 0) return [[...msgs], false];
  const m = msgs[i];
  if (m.step !== "sending" && m.step !== "injected" && m.step !== "checking") return [[...msgs], true]; // 전달됨 이상(근거 있음)·붙잡음 = 그대로
  return [msgs.map((x, j) => (j === i ? { ...x, step: "checking" as Step, code: "refused_at_write", note: REFUSED_AT_WRITE_NOTE } : x)), true];
}

/** 다시 보내기 단추를 둘 수 있는가 — 확정 실패 + 아직 다시 보낸 적 없음만(불명·재시도 중·붙잡음 = 0 · 같은 말 두 번 방지). */
export function canRetry(m: Msg): boolean {
  return m.step === "failed" && !m.retried;
}
