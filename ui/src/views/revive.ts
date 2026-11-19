// (cysr-1116-s5 · TICKET=cysr-1116-s5-1119) 마스터 멈춤·깨우기·다시 켜기 장부 — P2-DESIGN §6 · §11 조각 5 행.
//
// 판정은 judge/revive.ts(순수) · 이 장부는 사실을 모으고(사건·3초 조회·앱 저장소) 행동(깨움 말·다시 켜기)을 한 번씩만 한다.
//   깨우기  = chat_send{kind:auto}(데몬 큐 · 기계 표지 · 임무 아님) 1건 · 5분 거름 · 사람 보내기 뒤 30초 묶임이면 그 뒤에 · 120초 안에 깨어나지 않으면 실패 안내
//   다시 켜기 = 축별 길(§6-2) · 누름 1 → start_master ≤ 1 · 거절 자동 재시도 = seat_not_claimable ∧ 사람 입력 사유 아님일 때 65초 1회뿐
//             · 복원 중(restore-progress) 잠금 · 성공 = 마스터 좌석 id 바뀜 ∧ 에이전트 생존 ∧ 관문 없음 · boot-degraded 안내 · 옛 빈 셸 정리
// ★다시 켜기는 기존 좌석의 입력줄에 아무것도 쓰지 않는다(send 0) — 새 좌석의 기동 줄은 CLI(launch-agent)가 새 좌석에만 넣는다.
// 데몬·저장소·시계는 deps 로만(시험 대역).

import type { Store } from "./core";
import { masterRowOf, type MasterRow } from "./judge/gate";
import {
  BOOT_DEGRADED_WINDOW_MS,
  deadAxisOf,
  denialNext,
  GATE_WORK_HINT,
  leftoverShell,
  neverStartedEvidence,
  restartPlan,
  restartSucceeded,
  RESTART_TIMEOUT_MS,
  RETRY_DELAY_MS,
  reviveBand,
  reviveSituation,
  startOutcome,
  WAKE_DEDUPE_MS,
  WAKE_TEXT,
  WAKE_TIMEOUT_MS,
  wokeUp,
  type DeadAxis,
  type Denial,
  type ReviveBand,
  type RevivePhase,
  type ReviveSit,
} from "./judge/revive";

/** 이 기기에서 cysr 마스터 좌석을 본 적 있음 — 값 = 마지막으로 본 마스터 좌석 번호(옛 빈 셸 정리에 씀 · V-C4 ⓐ). */
export const SEEN_KEY = "cys-master-seen";
/** role.released{master}·master.deadman 을 받은 기록(V-C4 ⓑ) — 살아 있는 마스터를 다시 보면 지운다. */
export const GONE_KEY = "cys-master-gone";
/** 거절 사건을 기다리는 짧은 창(start_master 가 끝난 뒤 · 사건이 늦게 올 수 있다 · 설계 목표값). */
export const DENIAL_EVENT_WAIT_MS = 1_500;

export interface ReviveDeps {
  invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown>;
  now(): number;
  setTimeout(fn: () => void, ms: number): unknown;
  clearTimeout(h: unknown): void;
  store: Store;
  working(row: Record<string, unknown>): boolean;
  /** 기계 문안 추적(조각 3 trackAuto) */
  trackAuto(entryId: string, seat: number): void;
  /** 사람 보내기 뒤 데몬 큐 묶임 남은 ms(조각 3 R3) */
  holdRemainingMs(): number;
  /** 다른 화면으로(작업 화면에서 보기) */
  goView?(id: string): void;
  /** 작업 화면에서 그 좌석 창에 포커스(관문 답하기) */
  focusSeat?(sid: number): void;
  /** 작업 화면 위 안내 띠(관문) — null = 닫기 */
  workHint?(text: string | null): void;
  /** 도움 요청 창(기존 피드백 창) */
  openHelp?(): void;
  /** 바뀜 알림(다시 그리기) */
  changed(): void;
  /** 빨리 다시 조회(성공 신호 보조) */
  pollSoon?(): void;
}

export interface ReviveView {
  sit: ReviveSit;
  phase: RevivePhase;
  band: ReviveBand | null;
  restoring: boolean;
}

export class ReviveBook {
  private master: MasterRow | null | undefined = undefined;
  private org: unknown = undefined;
  private dead: { sid: number; axis: DeadAxis } | null = null;
  private idle: { sid: number; at: number } | null = null;
  private neverSince: number | null = null;
  private phase: RevivePhase = { kind: "rest" };
  private restoring = false;
  /** 누름 잠금(진행 중 = 다른 누름 무시 · 클릭 1 → 호출 ≤ 1) */
  private busy = false;
  private lastWakeAt: number | null = null;
  private wakeTimer: unknown = null;
  private phaseTimer: unknown = null;
  /** 이 다시 켜기 한 차례에서 자동 재시도를 이미 썼는가 */
  private autoUsed = false;
  private lastDenial: { at: number; ev: Denial } | null = null;
  private lastRestartAt: number | null = null;
  /** 다시 켜기 직전의 옛 마스터 좌석(vacant 면 저장소의 마지막 번호) — 성공 뒤 빈 셸 정리 대상 */
  private oldSid: number | null = null;
  /** 시험 계수 */
  readonly counts = { start: 0, close: 0, wake: 0, autoRetry: 0 };

  constructor(private readonly d: ReviveDeps) {}

  // ---------- 사실 ----------

  private storeGet(k: string): string | null {
    try {
      return this.d.store.get(k);
    } catch {
      return null;
    }
  }
  private storeSet(k: string, v: string | null): void {
    try {
      if (v === null) this.d.store.remove(k);
      else this.d.store.set(k, v);
    } catch {
      /* 저장소 불가 = 이 기기 기억 없이(새 설치처럼) */
    }
  }

  /** 3초 조회 1회분(core.applyFresh) — 마스터 행 · org 원문. */
  observe(master: MasterRow | null | undefined, org: unknown): void {
    const now = this.d.now();
    this.master = master;
    if (org !== undefined) this.org = org;
    if (master && master.agent_alive === true) {
      // 살아 있는 cysr 마스터를 봄 — 「본 적 있음」(번호) 기록 · 놓아짐 기록 지움 · 그 좌석의 낡은 deadman 지움
      if (this.storeGet(SEEN_KEY) !== String(master.surface_id)) this.storeSet(SEEN_KEY, String(master.surface_id));
      if (this.storeGet(GONE_KEY) !== null) this.storeSet(GONE_KEY, null);
      if (this.dead && this.dead.sid === master.surface_id) this.dead = null;
    }
    this.neverSince = neverStartedEvidence(master) ? (this.neverSince ?? now) : null;
    // 조용함 사건 뒤 새 출력·일 시작 = 풀림
    if (this.idle && master && this.idle.sid === master.surface_id && wokeUp(master, this.idle.at, now)) this.idle = null;
    // 깨우는 중 → 깨어남
    if (this.phase.kind === "waking" && wokeUp(master, this.phase.at, now)) this.setPhase({ kind: "rest" });
    // 다시 켜는 중 → 성공 판정
    if (this.phase.kind === "restarting" && restartSucceeded(this.phase.before, master)) this.onRestartOk(master as MasterRow);
    // 사람 입력 때문에 기다리던 것 · 쓰다 만 글 — 사정이 풀렸으면(꺼짐 아님) 띠를 거둔다
    if ((this.phase.kind === "hold_human" || this.phase.kind === "draft_block" || this.phase.kind === "restartfail" || this.phase.kind === "wakefail") && this.situation().kind === "ok")
      this.setPhase({ kind: "rest" });
    // 다시 그리기는 부른 쪽(core.applyFresh → set)이 한다
  }

  /** 데몬 사건(본부 데몬 것만 · 공통층이 소켓 이름으로 거른 뒤). */
  onEvent(raw: unknown): void {
    const e = raw as { name?: unknown; surface_id?: unknown; payload?: unknown } | null;
    if (!e || typeof e.name !== "string") return;
    const p = (e.payload && typeof e.payload === "object" ? e.payload : {}) as Record<string, unknown>;
    const role = typeof p.role === "string" ? p.role : null;
    const sid = typeof e.surface_id === "number" && Number.isSafeInteger(e.surface_id) ? e.surface_id : null;
    switch (e.name) {
      case "master.deadman": {
        if ((role ?? "master") !== "master" || sid === null) return;
        const axis = deadAxisOf(p.axis);
        if (!axis) return;
        this.dead = { sid, axis };
        this.storeSet(GONE_KEY, "1");
        break;
      }
      case "role.released":
        if (role !== "master") return;
        this.storeSet(GONE_KEY, "1");
        break;
      case "master.idle":
        if ((role ?? "master") !== "master" || sid === null) return;
        this.idle = { sid, at: this.d.now() };
        break;
      case "role.claim_denied":
        if (role !== "master" || p.path !== "surface.create") return;
        this.lastDenial = { at: this.d.now(), ev: { seat_blocked: p.seat_blocked, takeover_cancelled: p.takeover_cancelled, seat_human_recent: p.seat_human_recent } };
        return; // 그리기 변화 없음(다시 켜기 결과 판단이 읽는다)
      case "role.takeover":
      case "role.claimed":
        if (role !== "master") return;
        this.d.pollSoon?.(); // 빨리 알아채는 보조 — 성공 판정은 조회 행으로만
        return;
      default:
        return;
    }
    this.d.changed();
  }

  /** Tauri 앱 사건(boot-degraded · restore-progress). */
  onAppEvent(name: string, payload: unknown): void {
    if (name === "restore-progress") {
      const ph = (payload as { phase?: unknown } | null)?.phase;
      if (ph === "start") this.restoring = true;
      else if (ph === "done" || ph === "error") this.restoring = false;
      else return;
      this.d.changed();
      return;
    }
    if (name === "boot-degraded") {
      const now = this.d.now();
      if (this.lastRestartAt === null || now - this.lastRestartAt > BOOT_DEGRADED_WINDOW_MS) return; // 이 화면이 다시 켠 것이 아니면 작업 화면 알림 몫
      this.setPhase({ kind: "boot_degraded" });
    }
  }

  situation(): ReviveSit {
    return reviveSituation({
      master: this.master,
      seenBefore: this.storeGet(SEEN_KEY) !== null,
      goneMark: this.storeGet(GONE_KEY) !== null,
      dead: this.dead,
      neverSince: this.neverSince,
      idle: this.idle,
      now: this.d.now(),
    });
  }

  view(): ReviveView {
    const sit = this.situation();
    return { sit, phase: this.phase, band: reviveBand(sit, this.phase, this.restoring, this.d.now()), restoring: this.restoring };
  }

  private setPhase(p: RevivePhase, timeoutMs?: number, onTimeout?: () => void): void {
    if (this.phaseTimer !== null) {
      this.d.clearTimeout(this.phaseTimer);
      this.phaseTimer = null;
    }
    this.phase = p;
    if (timeoutMs !== undefined && onTimeout) {
      this.phaseTimer = this.d.setTimeout(() => {
        this.phaseTimer = null;
        onTimeout();
      }, timeoutMs);
    }
    this.d.changed();
  }

  // ---------- 깨우기 ----------

  /** 「마스터 깨우기」(신뢰 클릭 뒤). 5분 안에 이미 깨웠으면 아무것도 안 함. */
  async wake(): Promise<void> {
    if (this.busy || this.phase.kind === "waking" || this.phase.kind === "wake_wait") return;
    const now = this.d.now();
    if (this.lastWakeAt !== null && now - this.lastWakeAt < WAKE_DEDUPE_MS) {
      // 이미 깨운 지 5분이 안 됨 — 다시 보내지 않고 기다림 표시(남은 시간 동안 120초 실패 판정은 이미 돌았다)
      this.setPhase({ kind: "waking", at: this.lastWakeAt }, Math.max(0, this.lastWakeAt + WAKE_TIMEOUT_MS - now), () => this.wakeTimedOut());
      return;
    }
    const hold = this.d.holdRemainingMs();
    this.lastWakeAt = now; // 누른 순간부터 거름(기다리는 동안 다시 눌러도 1건)
    if (hold > 0) {
      // R3: 사람 보내기 뒤 데몬이 큐를 30초 묶는다 — 그 뒤에 보낸다(지금 넣으면 묶인 채 「차례 기다림」만 길어짐 · 같은 1건)
      this.setPhase({ kind: "wake_wait", until: now + hold }, hold, () => void this.sendWake());
      return;
    }
    await this.sendWake();
  }

  private async sendWake(): Promise<void> {
    const m = this.master;
    if (!m || m.agent_alive !== true) {
      this.setPhase({ kind: "wakefail" });
      return;
    }
    this.busy = true;
    const at = this.d.now();
    this.lastWakeAt = at;
    this.setPhase({ kind: "waking", at }, WAKE_TIMEOUT_MS, () => this.wakeTimedOut());
    this.counts.wake++;
    try {
      const r = (await this.d.invoke("chat_send", { socket: null, surfaceId: m.surface_id, text: WAKE_TEXT, kind: "auto" })) as { outcome?: unknown; queue_entry_id?: unknown } | null;
      if (r?.outcome === "queued" && typeof r.queue_entry_id === "string") this.d.trackAuto(r.queue_entry_id, m.surface_id);
      else if (r?.outcome === "failed") this.setPhase({ kind: "wakefail" }); // 큐에 안 들어감 = 깨움 말 0 → 바로 다음 길(다시 켜기)
      // uncertain = 들어갔을 수 있음 → 다시 보내지 않고 120초 판정을 기다린다
    } catch {
      /* 다리 실패 = 모름 → 120초 판정 */
    } finally {
      this.busy = false;
    }
  }

  private wakeTimedOut(): void {
    if (this.phase.kind === "waking") this.setPhase({ kind: "wakefail" });
  }

  // ---------- 다시 켜기 ----------

  /** 「마스터 다시 켜기」(신뢰 클릭 뒤 · 또는 거절 뒤 자동 1회). */
  async restart(auto = false): Promise<void> {
    if (this.busy) return; // 연타 = 호출 0
    if (this.restoring) {
      // 복원 중 = 호출 0(phoenix·두 번 생성 경합 F5). 자동 1회가 이때 걸리면 기다림 띠에 갇히지 않게 실패 안내로.
      if (auto && this.phase.kind === "retry_wait") this.setPhase({ kind: "restartfail", why: "직원 복귀(복원) 중이라 저절로 켜지 않았어요" });
      return;
    }
    if (this.phase.kind === "restarting" || (this.phase.kind === "retry_wait" && !auto)) return;
    this.busy = true;
    try {
      if (!auto) this.autoUsed = false; // 사람이 새로 누른 다시 켜기 = 새 차례
      // 누른 뒤 다시 받는다(3초 목록을 믿지 않음) — 판정·옛 좌석 행 모두 이 값으로
      const org = await this.d.invoke("org_status", { socket: null }).catch(() => undefined);
      if (org !== undefined) this.observe(masterRowOf(org, this.d.working), org);
      const sit = this.situation();
      const fromWakeFail = this.phase.kind === "wakefail"; // 깨우기 실패 뒤 다시 켜기 = 살아 있는 좌석 위로 start_master(승계·거절은 데몬 판정)
      if (sit.kind !== "down" && !fromWakeFail) {
        this.setPhase({ kind: "rest" });
        return; // 이미 살아남(다른 길로 켜짐) — 아무것도 안 함
      }
      const before = this.master ? this.master.surface_id : null;
      this.oldSid = before ?? this.lastSeenSid();
      const plan = sit.kind === "down" ? restartPlan(sit, this.master) : ({ kind: "start" } as const);
      if (plan.kind === "none") return;
      if (plan.kind === "draft_block") {
        this.setPhase({ kind: "draft_block", sid: plan.sid });
        return;
      }
      if (plan.kind === "close_then_start") {
        this.counts.close++;
        try {
          await this.d.invoke("close_surface", { socket: null, surfaceId: plan.sid });
        } catch (e) {
          this.setPhase({ kind: "restartfail", why: `옛 마스터 창을 닫지 못했어요: ${String(e).slice(0, 120)}` });
          return;
        }
      }
      this.lastRestartAt = this.d.now();
      this.setPhase({ kind: "restarting", at: this.lastRestartAt, before: plan.kind === "close_then_start" ? plan.sid : before }, RESTART_TIMEOUT_MS, () => {
        if (this.phase.kind === "restarting") this.setPhase({ kind: "restartfail", why: "시간 안에 마스터가 켜지지 않았어요" });
      });
      this.counts.start++;
      const t0 = this.d.now();
      let err: unknown = undefined;
      try {
        await this.d.invoke("start_master");
      } catch (e) {
        err = e === undefined ? "start_master failed" : e;
      }
      const out = startOutcome(err);
      if (out === "ok") {
        this.d.pollSoon?.();
        return; // 성공 판정은 조회 행으로(observe)
      }
      if (out === "gate_pending") {
        this.setPhase({ kind: "rest" }); // 관문 띠는 행의 gate_pending 이 그린다(§6-3)
        this.d.pollSoon?.();
        return;
      }
      if (out === "failed") {
        this.setPhase({ kind: "restartfail", why: String(err).slice(0, 160) });
        return;
      }
      // 거절 — 그 다시 켜기의 사건(role.claim_denied)을 짧게 기다려 까닭을 본다
      const ev = await this.awaitDenial(t0);
      const next = denialNext(ev, this.autoUsed);
      if (next === "hold_human") this.setPhase({ kind: "hold_human" });
      else if (next === "retry") {
        this.autoUsed = true;
        this.setPhase({ kind: "retry_wait", at: this.d.now() }, RETRY_DELAY_MS, () => {
          this.counts.autoRetry++;
          void this.restart(true);
        });
      } else this.setPhase({ kind: "restartfail", why: "마스터 자리가 아직 비지 않았어요" });
    } finally {
      this.busy = false;
    }
  }

  private awaitDenial(since: number): Promise<Denial | null> {
    const fresh = () => (this.lastDenial && this.lastDenial.at >= since ? this.lastDenial.ev : null);
    const got = fresh();
    if (got) return Promise.resolve(got);
    return new Promise((res) => {
      this.d.setTimeout(() => res(fresh()), DENIAL_EVENT_WAIT_MS);
    });
  }

  private lastSeenSid(): number | null {
    const v = Number(this.storeGet(SEEN_KEY));
    return Number.isSafeInteger(v) && v > 0 ? v : null;
  }

  private onRestartOk(m: MasterRow): void {
    this.setPhase({ kind: "rest" });
    // vacant·never 정리: 옛 좌석이 역할 없는 빈 셸 ∧ 사람 입력 0 이면 닫는다(빈 셸 누적 방지 · F3·V-M5) — 아니면 그대로 둔다.
    const old = leftoverShell(this.org, this.oldSid, m.surface_id);
    this.oldSid = null;
    if (old !== null) {
      this.counts.close++;
      void this.d.invoke("close_surface", { socket: null, surfaceId: old }).catch(() => {});
    }
  }

  // ---------- 단추 ----------

  help(): void {
    this.d.openHelp?.();
  }

  toWork(): void {
    this.d.goView?.("work");
  }

  /** 관문 띠 「작업 화면에서 답하기」 — 전환 + 마스터 창 포커스 + 작업 화면 위 안내. */
  answerGate(): void {
    const sit = this.situation();
    if (sit.kind !== "gate") return;
    this.d.workHint?.(null);
    this.d.goView?.("work");
    this.d.focusSeat?.(sit.sid);
    this.d.workHint?.(GATE_WORK_HINT);
  }

  /** 띠를 닫음(restartfail·boot_degraded 확인). */
  dismiss(): void {
    if (this.phase.kind === "restartfail" || this.phase.kind === "boot_degraded" || this.phase.kind === "wakefail") this.setPhase({ kind: "rest" });
  }

  /** 대화 화면이 내려감 — 예약을 거두지 않는다(자동 재시도·실패 판정은 화면과 무관하게 한 번) */
}
