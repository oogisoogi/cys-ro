// (cysr-1116-s5 · TICKET=cysr-1116-s5-1119) 마스터 멈춤·깨우기·다시 켜기 판정 — 순수(P2-DESIGN §6 · §11 조각 5 행).
//
// 축(데몬 `master.deadman.payload.axis` · governance.rs DeadmanAxis::as_str) 6개 + 「마스터 자리 빔(vacant)」 + 관문 보류(§6-3) + 조용함(§6-1).
// 길(§6-2 표):
//   surface_gone · surface_exited            → start_master
//   agent_dead · seat_vacant_no_meta · shell_proc_dead → start_master → 거절이면 seat_not_claimable ∧ 사람 입력 사유 아님일 때만 65초 1회 자동
//   agent_never_started                       → 옛 좌석 사람 입력 0 확인 → close_surface_if_quiet(데몬 조건부 닫기) → start_master (사람 입력 있으면 닫지 않고 안내)
//   vacant(회수 뒤 · 앱 새로 켬)              → start_master → 성공 뒤 옛 빈 셸 정리(Empty ∧ 사람 입력 0)
//   거절 사유 = 사람 입력                      → 자동 재시도 0 · 「마스터 창에 방금 누가 글을 쓰고 있어 기다리고 있어요」
// 성공(F4 · V-N2) = 목록의 role=master ∧ !exited 좌석 id 가 다시 켜기 전과 다름 ∧ 그 좌석 에이전트 살아 있음 ∧ 관문 없음.
// 규칙: document·window·localStorage·__TAURI__·Date.now·setTimeout 금지(시각은 인자).

import type { MasterRow } from "./gate";
import { HUMAN_QUIET_SECS } from "./gate";

export type DeadAxis = "surface_gone" | "surface_exited" | "shell_proc_dead" | "agent_dead" | "seat_vacant_no_meta" | "agent_never_started";
export const DEAD_AXES: readonly DeadAxis[] = ["surface_gone", "surface_exited", "shell_proc_dead", "agent_dead", "seat_vacant_no_meta", "agent_never_started"];

export function deadAxisOf(v: unknown): DeadAxis | null {
  return typeof v === "string" && (DEAD_AXES as readonly string[]).includes(v) ? (v as DeadAxis) : null;
}

/** 깨움 말(설계 §6-1 원문). 기계 문안 = 데몬 큐 · 원장 기록 · 임무 아님. */
export const WAKE_TEXT = "[깨우기] 사용자가 대화 화면에서 깨웠어요. 남은 확인할 것을 이어서 봐 주세요.";
/** 같은 깨움을 다시 보내지 않는 창(설계 §6-1 · 데몬 같은 문구 300초 억제 선례). */
export const WAKE_DEDUPE_MS = 300_000;
/** 깨운 뒤 이만큼 활동 변화가 없으면 실패 안내(+「마스터 다시 켜기」 함께 · §6-1). */
export const WAKE_TIMEOUT_MS = 120_000;
/** 거절 뒤 자동 1회까지(데몬 60초 역할 회수 + 틱 여유 · §6-2 표 「65초 1회」). */
export const RETRY_DELAY_MS = 65_000;
/** 다시 켜기 성공 판정을 기다리는 상한(설계 목표값 · 측정 대기) — 넘으면 「다시 켜지 못했어요」. */
export const RESTART_TIMEOUT_MS = 120_000;
export const RESTART_TIMEOUT_MEASURED = false;
/** 데몬 deadman(agent_never_started)을 못 받았을 때 행 증거(등록 있음 ∧ 본 적 없음 ∧ 좌석 Empty)가 이만큼 이어지면 「아직 시작하지 못했어요」(설계 목표값). */
export const NEVER_STARTED_MS = 90_000;
/** 다시 켜기 뒤 boot-degraded 를 이 다시 켜기 것으로 보는 창(설계 목표값). */
export const BOOT_DEGRADED_WINDOW_MS = 300_000;

/** 화면이 이 판정에 넘기는 사실(전부 공통층이 모은 값). */
export interface ReviveFacts {
  /** 살아 있는 role=master 행(masterRowOf) · undefined = 조회 실패 · null = 없음 */
  master: MasterRow | null | undefined;
  /** 이 기기에서 cysr 마스터 좌석을 본 적 있음(앱 저장소 cys-master-seen · V-C4 ⓐ) */
  seenBefore: boolean;
  /** role.released{master}·master.deadman 을 받은 기록(앱 저장소 · V-C4 ⓑ) */
  goneMark: boolean;
  /** 마지막 master.deadman(본부 데몬 · role master) */
  dead: { sid: number; axis: DeadAxis } | null;
  /** 행 증거(등록 있음 ∧ 본 적 없음 ∧ 좌석 Empty)가 처음 보인 시각 · 끊기면 null */
  neverSince: number | null;
  /** 지금 마스터 좌석이 이 기기에서 살아 있는 마스터로 본 바로 그 좌석인가(번호 + 생성 시각) — 등록 없는 빈 좌석 꺼짐의 근거 */
  seenSame?: boolean;
  /** 마지막 master.idle(본부 · role master) — 새 출력이 있으면 공통층이 지운다 */
  idle: { sid: number; at: number } | null;
  /** (BA1 · 1.1.19) 마스터가 멈춘 까닭(한도 · 로그인) — 장부가 pickStall 로 고른 하나 · 없음 = null(1.1.18 동작) */
  stall?: Stall;
  now: number;
}

// ---------- (BA1 · TICKET=cysr-1119-s8) 멈춘 까닭 — 한도 · 로그인(DESIGN §7 BA1 · 카드 BORROW §3-1 A1) ----------

/** 되돌리기 = false → login·limited 갈래 없음(1.1.18 조용함 띠 그대로). */
export const LIMIT_LOGIN_BANDS = true;
/** 로그인 룰 = 데몬 auth 인터록 룰 그대로(state.rs AUTH_INTERLOCK_RULES · 원천 검사 시험). */
export const AUTH_RULES: readonly string[] = ["not_logged_in", "auth_401", "token_expired", "login_required"];
/** 사건 근거 창 = 데몬 AUTH_INTERLOCK_WINDOW_SECS(300초)와 같은 값. */
export const STALL_EVENT_MS = 300_000;
/** 한도 수치가 이보다 낡았으면(또는 나이 모름) 한도 판정 안 함 = usagebar USAGE_STALE_SECS(30분 · 거짓 띠 0). */
export const LIMIT_STALE_SECS = 1800;

export type Stall = { why: "limit"; resetsAt: number | null } | { why: "login"; rule: string } | null;

/** 좌석 행 `usage`(accounts.rs seat_usage_wire) → 한도 읽기(순수 · 시각 ms). limited = 100% 이상 창이 있고 리셋 전(리셋 = 그 창들 중 가장 늦은 것 · 모름 = null)
 *  · fresh = 신선한 수치가 있으나 한도 아님 · none = 수치 없음·낡음·나이 모름(판정 안 함). */
export type LimitRead = { state: "limited"; resetsAt: number | null } | { state: "fresh" } | { state: "none" };
export function usageLimit(usage: unknown, nowMs: number): LimitRead {
  const u = usage as { rate?: unknown; rate_age_secs?: unknown } | null | undefined;
  const age = u?.rate_age_secs;
  if (!u || !Array.isArray(u.rate) || typeof age !== "number" || !Number.isFinite(age) || age > LIMIT_STALE_SECS) return { state: "none" };
  let hit = false;
  let any = false;
  let resetsAt: number | null = null;
  let unknownReset = false;
  for (const w of u.rate as unknown[]) {
    const r = w as { used_pct?: unknown; resets_at?: unknown } | null;
    if (!r || typeof r.used_pct !== "number" || !Number.isFinite(r.used_pct)) continue;
    const at = typeof r.resets_at === "number" && Number.isFinite(r.resets_at) ? r.resets_at * 1000 : null;
    if (at !== null && at <= nowMs) continue; // 이미 리셋된 창 = 지금 값이 아니다
    any = true;
    if (r.used_pct < 100) continue;
    hit = true;
    if (at === null) unknownReset = true;
    else if (resetsAt === null || at > resetsAt) resetsAt = at;
  }
  if (hit) return { state: "limited", resetsAt: unknownReset ? null : resetsAt };
  return any ? { state: "fresh" } : { state: "none" };
}

/** 까닭 하나 고르기(순수) — 로그인 > 한도(로그인은 리셋으로 안 풀림) · 한도 1차 근거 = 수치 · rate_limited 사건은 수치가 없을 때만(리셋 모름). */
export function pickStall(login: { rule: string; at: number } | null, limit: LimitRead, rateLimitedAt: number | null, now: number): Stall {
  if (login && now - login.at < STALL_EVENT_MS) return { why: "login", rule: login.rule };
  if (limit.state === "limited") return { why: "limit", resetsAt: limit.resetsAt };
  if (limit.state === "none" && rateLimitedAt !== null && now - rateLimitedAt < STALL_EVENT_MS) return { why: "limit", resetsAt: null };
  return null;
}

const DAY = ["일", "월", "화", "수", "목", "금", "토"];
/** 리셋 시각(기기 현지) — 24시간 안 = 「HH:MM」 · 넘으면 「요일 HH:MM」(오늘로 오독 방지 · master#9d622f54 판단 1 승인). */
export function resetClock(atMs: number, nowMs: number): string {
  const t = new Date(atMs);
  const hm = `${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}`;
  return atMs - nowMs > 86_400_000 ? `${DAY[t.getDay()]} ${hm}` : hm;
}

/** 꺼짐 갈래(화면 글이 다르다). */
export type Down = "gone" | "agent" | "never" | "vacant";

export type ReviveSit =
  | { kind: "unknown" }
  | { kind: "none" } // 새 설치 · 마스터 준비 중(§9-3 — 「마스터 좌석 없음」만으로 꺼짐이라 하지 않음)
  | { kind: "ok" }
  | { kind: "gate"; sid: number } // §6-3
  | { kind: "idle"; sid: number } // §6-1
  | { kind: "login"; sid: number; rule: string } // (BA1) 다시 로그인 필요
  | { kind: "limited"; sid: number; resetsAt: number | null } // (BA1) 사용 한도 · 리셋 ms(모름 = null)
  | { kind: "down"; down: Down; axis: DeadAxis | "vacant"; sid: number | null };

/** 행이 「등록 에이전트를 한 번도 못 봤고 좌석이 비어 있다」인가(agent_never_started 의 행 증거 · 데몬 진리표 meta ∧ !agent_seen ∧ Empty). */
export function neverStartedEvidence(m: MasterRow | null | undefined): boolean {
  return !!m && typeof m.agent === "string" && m.agent_seen === false && m.seat === "empty";
}

/** 행이 「등록(meta) 없는 좌석이 비어 있다」인가(seat_vacant_no_meta 의 행 증거 · 옛 데몬 = 칸 없음 → 아님). */
export function vacantNoMetaEvidence(m: MasterRow | null | undefined): boolean {
  return !!m && m.agent === null && m.seat === "empty" && m.agent_alive === null;
}

/** 빈 좌석 증거(어느 쪽이든) — 공통층이 「처음 보인 시각」을 든다. */
export function emptySeatEvidence(m: MasterRow | null | undefined): boolean {
  return neverStartedEvidence(m) || vacantNoMetaEvidence(m);
}

/** 지금 마스터 사정 하나(순수). 조건마다 한 줄 = 뮤턴트 시험 단위. */
export function reviveSituation(f: ReviveFacts): ReviveSit {
  const m = f.master;
  if (m === undefined) return { kind: "unknown" };
  if (m === null) {
    // 살아 있는 마스터 좌석이 없다 — 창이 닫힘(gone/exited 사건) 또는 자리 빔(본 적 있음·놓아짐 기록). 새 설치 = 준비 중.
    if (f.dead && (f.dead.axis === "surface_gone" || f.dead.axis === "surface_exited")) return { kind: "down", down: "gone", axis: f.dead.axis, sid: f.dead.sid };
    if (f.seenBefore || f.goneMark) return { kind: "down", down: "vacant", axis: "vacant", sid: null };
    return { kind: "none" };
  }
  if (m.gate_pending !== null && m.gate_pending !== undefined) return { kind: "gate", sid: m.surface_id };
  const sid = m.surface_id;
  // 이 좌석의 deadman — 그 뒤 에이전트가 살아 보이면(되살아남) 낡은 사건이다. 창이 살아 있는데 gone/exited 사건 = 낡음.
  const d = f.dead && f.dead.sid === sid && m.agent_alive !== true ? f.dead.axis : null;
  if (d === "agent_never_started") return { kind: "down", down: "never", axis: d, sid };
  if (d === "agent_dead" || d === "seat_vacant_no_meta" || d === "shell_proc_dead") return { kind: "down", down: "agent", axis: d, sid };
  if (m.agent_alive === false) return { kind: "down", down: "agent", axis: "agent_dead", sid };
  const sustained = f.neverSince !== null && f.now - f.neverSince >= NEVER_STARTED_MS;
  if (neverStartedEvidence(m) && sustained) return { kind: "down", down: "never", axis: "agent_never_started", sid };
  // (codex 1R major) 등록 없는 마스터 좌석이 빈 셸로 이어짐 + 이 기기에서 마스터를 본 적 있음 = 사건(seat_vacant_no_meta)을 못 받은 앱 새로 켬도 꺼짐으로
  //   (codex 2R minor) 근거 = 바로 이 좌석을 살아 있는 마스터로 본 적 있음 — 다른 좌석·옛 데몬 표식만으로는 「준비 중」(거짓 꺼짐 띠 0)
  if (vacantNoMetaEvidence(m) && sustained && f.seenSame === true) return { kind: "down", down: "agent", axis: "seat_vacant_no_meta", sid };
  // (BA1) 꺼짐·관문 다음 · 조용함 앞 — 로그인 > 한도
  if (LIMIT_LOGIN_BANDS && f.stall?.why === "login") return { kind: "login", sid, rule: f.stall.rule };
  if (LIMIT_LOGIN_BANDS && f.stall?.why === "limit") return { kind: "limited", sid, resetsAt: f.stall.resetsAt };
  if (f.idle && f.idle.sid === sid && m.agent_alive === true) return { kind: "idle", sid };
  return { kind: "ok" };
}

/** 다시 켜기 누름 → 무엇을 할지(순수). `old` = 쓰기 직전 다시 받은 그 좌석 행(never 갈래만 씀). */
export type RestartPlan = { kind: "start" } | { kind: "close_then_start"; sid: number } | { kind: "draft_block"; sid: number } | { kind: "none" };

export function restartPlan(sit: ReviveSit, old: MasterRow | null | undefined): RestartPlan {
  if (sit.kind !== "down") return { kind: "none" };
  // (실물 실측 · real-daemon.txt ⑤) 같은 role+agent+cwd 기동 120초 안(CREATE_IDEM_TTL_SECS)이면 launch-agent 가 **같은 좌석을 멱등 재사용**해
  //   그 셸에 기동 줄을 clear_first 없이 친다 — 옛 마스터 창에 사람 초안이 있으면 그 뒤에 붙는다. 그래서 모든 축에서 초안이 있으면 켜지 않는다.
  // (codex 1R blocking 1 · 완화) 30초 안 사람 입력도 막는다 — 다시 받은 행과 닫기 사이(같은 누름 안 · 수 ms)에 사람이 새로 치기 시작하는 창을 좁힌다.
  //   남는 창은 닫기 쪽에서 닫는다(master#565d7c18 P1) — 닫기 = 데몬 조건부 닫기(close_surface_if_quiet)가 같은 조건을 닫기와 같은 잠금 안에서 다시 판정.
  const draft = (r: MasterRow) =>
    r.pending_input_human_bytes !== 0 || r.input_paste_open !== false || r.human_idle_secs === undefined || (r.human_idle_secs !== null && r.human_idle_secs < HUMAN_QUIET_SECS);
  if (sit.down !== "never") return old && sit.sid !== null && old.surface_id === sit.sid && draft(old) ? { kind: "draft_block", sid: sit.sid } : { kind: "start" };
  // never_started 는 회수도 승계도 안 된다(§6-2 ②) — 옛 좌석을 닫아야 보유자가 사라진다. 닫기 = 사람 입력 없는 빈 셸일 때만(기계 판단 4-3).
  if (!old || sit.sid === null || old.surface_id !== sit.sid) return { kind: "none" }; // 다시 받은 행이 그 좌석이 아니면 아무것도 안 함
  if (draft(old)) return { kind: "draft_block", sid: sit.sid };
  return { kind: "close_then_start", sid: sit.sid };
}

/** role.claim_denied 사건 칸(handlers.rs surface.create · 전부 의심). */
export interface Denial {
  seat_blocked?: unknown;
  takeover_cancelled?: unknown;
  seat_human_recent?: unknown;
}

/** 거절 뒤 다음 걸음(순수). 사건 없음 = 까닭 모름 → 자동 재시도 0(실패 안내 + 다시 누를 수 있음). */
export function denialNext(ev: Denial | null, autoUsed: boolean): "hold_human" | "retry" | "fail" {
  if (!ev) return "fail";
  const human = ev.seat_human_recent === true || (typeof ev.takeover_cancelled === "string" && ev.takeover_cancelled.includes("사람 입력"));
  if (human) return "hold_human";
  if (ev.seat_blocked === "seat_not_claimable" && !autoUsed) return "retry";
  return "fail";
}

/** start_master 결과(Tauri 명령 · 성공 = resolve · 실패 = 오류 글) → 갈래(순수). 글 근거 = main.rs start_master 의 관문 문구 · cys CLI 오류 꼴 `claim_denied: …`. */
export function startOutcome(err: unknown): "ok" | "gate_pending" | "denied" | "failed" {
  if (err === undefined) return "ok";
  const s = String(err);
  if (s.includes("첫기동 관문")) return "gate_pending";
  if (s.includes("claim_denied")) return "denied";
  return "failed";
}

/** 다시 켜기 성공(순수) — 에이전트 살아 있음 ∧ 관문 없음 ∧ (목록 마스터 좌석 id 가 전과 다름 ∨ 같은 좌석이 다시 켜기 전엔 살아 있지 않았음).
 *  (실물 실측 ⑤) launch-agent 의 120초 멱등 재사용이면 같은 좌석에서 되살아난다 — id 만 보면 거짓 실패. 같은 좌석은 전에 생존(true)이 아니었을 때만
 *  (깨우기 실패 뒤 살아 있는 좌석 위로 누른 경우 = 전에도 생존 → 같은 좌석 생존은 성공 아님). 고장 난 빈 셸 = agent_alive true 아님. */
export function restartSucceeded(beforeSid: number | null, m: MasterRow | null | undefined, beforeAlive = false): boolean {
  if (!m || m.agent_alive !== true || (m.gate_pending !== null && m.gate_pending !== undefined)) return false;
  return m.surface_id !== beforeSid || !beforeAlive;
}

/** 성공 뒤 정리할 옛 빈 셸(순수) — 옛 좌석이 살아 있고 · 역할 없고(회수됨) · 등록 에이전트 좌석이었고 · 좌석 Empty · 사람 입력 0 · 최근 사람 입력 없음일 때만 그 번호. */
/** 좌석 한 번의 신원 — 번호 + 데몬이 매긴 생성 시각(데몬이 다시 켜져 번호가 재사용돼도 생성 시각이 다르다 · codex 1R blocking 2). */
export interface SeatId {
  sid: number;
  created_at: number;
}

export function seatIdOf(org: unknown, sid: number): SeatId | null {
  const rows = (org as { surfaces?: unknown } | null)?.surfaces;
  if (!Array.isArray(rows)) return null;
  const r = rows.find((x) => !!x && typeof x === "object" && (x as { surface_id?: unknown }).surface_id === sid) as { created_at?: unknown } | undefined;
  return r && typeof r.created_at === "number" && Number.isFinite(r.created_at) ? { sid, created_at: r.created_at } : null;
}

export function leftoverShell(org: unknown, old: SeatId | null, newSid: number): number | null {
  if (old === null || old.sid === newSid) return null;
  const oldSid = old.sid;
  const rows = (org as { surfaces?: unknown } | null)?.surfaces;
  if (!Array.isArray(rows)) return null;
  const r = rows.find((x) => !!x && typeof x === "object" && (x as { surface_id?: unknown }).surface_id === oldSid) as Record<string, unknown> | undefined;
  if (!r) return null;
  if (r.created_at !== old.created_at) return null; // 같은 번호의 다른 좌석(데몬 다시 켜짐) = 닫지 않음
  if (r.exited === true) return null; // 이미 끝난 좌석은 데몬 회수 몫
  if (r.role !== null && r.role !== undefined) return null; // 아직 역할이 있으면 빈 셸이 아니다
  // 등록 에이전트 좌석(meta)이었던 것만 — 데몬이 다시 켜지면 좌석 번호가 다시 쓰여, 저장소의 옛 번호가 사용자가 연 맨 셸을 가리킬 수 있다(그 셸은 meta 없음).
  if (typeof r.agent !== "string" || r.agent === "") return null;
  if (r.seat !== "empty") return null;
  if (r.pending_input_human_bytes !== 0 || r.input_paste_open !== false) return null;
  const hi = r.human_idle_secs;
  if (hi !== null && !(typeof hi === "number" && hi >= HUMAN_QUIET_SECS)) return null;
  return oldSid;
}

/** 깨움이 들었는가(순수) — 깨운 뒤 마스터가 일을 시작했거나(working) 새 출력이 있었다(idle_secs 가 깨운 뒤 경과보다 작음). */
export function wokeUp(m: MasterRow | null | undefined, wakeAt: number, now: number): boolean {
  if (!m) return false;
  if (m.working) return true;
  // idle_secs 는 초 아래를 버린 값 — 1초를 더해 「깨운 뒤 새 출력」만 인정(깨우기 직전 1초 안 옛 출력을 새 출력으로 보지 않음 · codex 1R minor)
  return typeof m.idle_secs === "number" && (m.idle_secs + 1) * 1000 < now - wakeAt;
}

// ---------- 띠(그리기 재료 · 순수) ----------

/** 진행 중인 행동의 상태(공통층 장부가 든다). */
export type RevivePhase =
  | { kind: "rest" }
  | { kind: "wake_wait"; until: number } // 사람 보내기 뒤 30초 묶임 동안 기다렸다 보냄
  | { kind: "waking"; at: number }
  | { kind: "wakefail" }
  | { kind: "restarting"; at: number; before: number | null; beforeAlive: boolean }
  | { kind: "retry_wait"; at: number }
  | { kind: "hold_human" }
  | { kind: "draft_block"; sid: number }
  | { kind: "restartfail"; why: string }
  | { kind: "boot_degraded" }
  | { kind: "gate_wait"; at: number }; // start_master 가 관문 보류로 끝남 — 관문 좌석이 목록에 보일 때까지 다시 켜기 잠금(codex 1R major)

export type BandBtn = "wake" | "restart" | "help" | "work" | "gate_answer";

export interface ReviveBand {
  key: string;
  tone: "err" | "wait";
  title: string;
  body: string;
  buttons: BandBtn[];
  /** 잠긴 단추(누를 수 없음 · 「…중」) */
  locked?: BandBtn;
  lockLabel?: string;
}

const WHY: Record<Down, string> = {
  gone: "마스터 창이 닫혀 있어요.",
  agent: "마스터 프로그램이 멈췄어요.",
  never: "마스터가 아직 시작하지 못했어요.",
  vacant: "마스터가 멈춰 있어요.",
};

/** 띠 하나(순수) — 없으면 null. 진행 중 행동이 사정보다 앞선다(누른 결과를 먼저 보임). `restoring` = 복원 중 잠금. */
export function reviveBand(sit: ReviveSit, ph: RevivePhase, restoring: boolean, now: number): ReviveBand | null {
  switch (ph.kind) {
    case "restarting":
      return { key: "restarting", tone: "err", title: "마스터를 다시 켜는 중이에요.", body: "30초쯤 걸려요.", buttons: ["restart"], locked: "restart", lockLabel: "켜는 중…" };
    case "retry_wait":
      return { key: "retry_wait", tone: "err", title: "꺼진 마스터 자리를 정리하는 중이에요.", body: "1분 뒤 저절로 한 번 더 켜 볼게요.", buttons: ["help"] };
    case "hold_human":
      return { key: "hold_human", tone: "err", title: "마스터 창에 방금 누가 글을 쓰고 있어 기다리고 있어요.", body: "쓰던 글을 지우지 않으려고 멈췄어요. 그 창을 다 쓰신 뒤 다시 눌러 주세요.", buttons: ["restart", "work"] };
    case "draft_block":
      return { key: "draft_block", tone: "err", title: "그 창에 쓰다 만 글이 있어요.", body: "쓰던 글을 지우지 않으려고 마스터 창을 닫지 않았어요. 작업 화면에서 그 글을 보내거나 지운 뒤 다시 눌러 주세요.", buttons: ["work", "restart"] };
    case "restartfail":
      return { key: "restartfail", tone: "err", title: "마스터를 다시 켜지 못했어요.", body: ph.why ? `운영팀에 도움을 요청할 수 있어요. (${ph.why})` : "운영팀에 도움을 요청할 수 있어요.", buttons: ["help", "restart"] };
    case "gate_wait":
      if (sit.kind === "gate") break; // 관문 좌석이 보이면 관문 띠
      return { key: "gate_wait", tone: "wait", title: "마스터가 처음 켜지며 확인을 기다려요.", body: "마스터 창이 목록에 나타나는 중이에요.", buttons: ["restart"], locked: "restart", lockLabel: "기다리는 중…" };
    case "boot_degraded":
      return { key: "boot_degraded", tone: "wait", title: "마스터는 켜졌지만 팀 준비가 덜 됐어요.", body: "작업 화면에서 도우미 창들을 확인해 주세요.", buttons: ["work"] };
    case "wake_wait": {
      const secs = Math.max(1, Math.ceil((ph.until - now) / 1000));
      return { key: "wake_wait", tone: "err", title: "마스터를 깨울게요.", body: `방금 보낸 말 뒤라 약 ${secs}초 뒤에 깨우는 말을 보내요.`, buttons: ["wake"], locked: "wake", lockLabel: "깨우는 중…" };
    }
    case "waking":
      return { key: "waking", tone: "err", title: "마스터를 깨우는 중이에요.", body: "깨우는 말 1건을 보냈어요.", buttons: ["wake"], locked: "wake", lockLabel: "깨우는 중…" };
    case "wakefail":
      return { key: "wakefail", tone: "err", title: "마스터가 깨어나지 않았어요.", body: "다시 켜 보거나 운영팀에 도움을 요청할 수 있어요.", buttons: ["restart", "help"], ...(restoring ? { locked: "restart" as const, lockLabel: "복원하는 중이에요" } : {}) };
    case "rest":
      break;
  }
  if (sit.kind === "gate") return { key: "gate", tone: "wait", title: "마스터가 처음 켜지며 확인을 기다려요.", body: "작업 화면의 마스터 창에서 답해 주세요.", buttons: ["gate_answer"] };
  if (sit.kind === "login" || sit.kind === "limited") return stallBand(sit, now);
  if (sit.kind === "idle") return { key: "idle", tone: "err", title: "마스터가 한동안 조용해요.", body: "보낸 말은 깨어나면 차례대로 전달돼요.", buttons: ["wake"] };
  if (sit.kind === "down") {
    const b: ReviveBand = { key: `down_${sit.down}`, tone: "err", title: WHY[sit.down], body: "다시 켜면 하던 일을 이어서 해요.", buttons: ["restart"] };
    if (restoring) return { ...b, body: "직원 복귀(복원)가 끝나면 다시 켤 수 있어요.", locked: "restart", lockLabel: "복원하는 중이에요" };
    return b;
  }
  return null;
}

/** (BA1) 까닭 띠 글 표 — 열쇠 = 기계 값(sit.kind)만 · 한국어 글로 가르지 않는다(F02 원칙). 한도 띠 = 단추 0(깨우기 헛손 없음). */
export const STALL_TEXT = {
  limited: { title: "마스터가 사용 한도에 닿아 쉬고 있어요.", at: (hm: string) => `${hm} 쯤 다시 움직여요. 보낸 말은 그때 차례대로 전달돼요.`, unknown: "한도가 풀리면 다시 움직여요." },
  login: { title: "마스터가 다시 로그인해야 해요.", body: "작업 화면의 마스터 창에서 /login 을 입력해 주세요." },
} as const;

function stallBand(sit: { kind: "login"; sid: number; rule: string } | { kind: "limited"; sid: number; resetsAt: number | null }, now: number): ReviveBand {
  if (sit.kind === "login") return { key: "login", tone: "err", title: STALL_TEXT.login.title, body: STALL_TEXT.login.body, buttons: ["work"] };
  const body = sit.resetsAt === null ? STALL_TEXT.limited.unknown : STALL_TEXT.limited.at(resetClock(sit.resetsAt, now));
  return { key: "limited", tone: "wait", title: STALL_TEXT.limited.title, body, buttons: [] };
}

/** 작업 화면 관문 안내(§6-3 · 앱 문구 근거 main.rs start_master 관문 처방). */
export const GATE_WORK_HINT = "마스터 창에서 답해 주세요. 아래 방향키를 한 번 누른 뒤 Enter — 「Yes, I trust this folder」·「Yes, I accept」를 고르세요. 「No, exit」에서는 Enter 를 누르지 마세요.";
