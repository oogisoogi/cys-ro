// (cysr-ui-slice3) 시험 전용 대역 — 가짜 데몬(원자 제출 · 승인 창 거부 · 쓰기 직전 거부 사건 · 사람 입력 시각) + 가짜 Claude(결속 세션 기록 · uuid 사슬 · 답)
// + 가짜 시계·타이머. 시험 파일(slice3.test.ts · msgharness.test.ts)만 부른다 — 제품 번들에 들어가지 않는다(입구 index.ts 가 import 하지 않음).
//
// 「진실」을 따로 적는다: 쓰기마다 바이트가 실제로 들어갔는가 · 세션 기록에 그 말의 user 레코드가 생겼는가 · 답이 붙었는가.
// 화면 단계(core 상태)와 이 진실을 대조하는 것이 M3(틀림 0) · 보낸 말이 늘 단계와 함께 보이는가가 M2(행방 불명 0)다.

import { ChatCore, type Deps } from "./core";

export type SendKind = "written" | "uncertain_written" | "uncertain_lost" | "failed" | "hang_written" | "hang_lost" | "refuse_at_write";

export interface WriteTruth {
  at: number;
  msgId: string | null;
  text: string;
  /** 바이트가 입력줄에 들어갔는가(Ctrl-U·울타리·본문) */
  bytesIn: boolean;
  /** Enter 까지 들어가 Claude 가 받았는가(= 세션 기록이 생길 수 있음) */
  submitted: boolean;
  /** 데몬이 승인 창으로 거부(바이트 0) */
  refused: boolean;
  /** 화면에 돌려준 결과 */
  outcome: string;
}

export interface SimOpts {
  /** 다음 chat_send 를 어떻게 처리할지(호출 순번 n · 글) — 없으면 늘 written */
  plan?: (n: number, text: string) => SendKind;
  /** 바이트가 Enter 까지 들어간 뒤 user 레코드가 생기기까지(ms) · null = 기록이 생기지 않음(U20 접힌 꼴 등) */
  recordDelay?: (n: number) => number | null;
  /** user 레코드 뒤 답(assistant)까지(ms) · null = 답 없음 */
  replyDelay?: (n: number) => number | null;
  /** 걸린 요청이 응답하기까지(ms) */
  hangMs?: number;
  /** M8: 세션 레코드에 uuid 가 없는 꼴 */
  noUuid?: boolean;
  slug?: string;
  /** (조각 3 고침 · 검증 지적 A · 실측 꼴) 이 쓰기의 user 레코드를 `<pasted_content id=…>` 로 감싸 남김 */
  wrapPaste?: (n: number) => boolean;
  /** (조각 3 고침 · 검증 지적 B · 실측 꼴) user 레코드와 답 사이에 끼는 다른 종류 레코드 수(attachment 등 = 글 없는 고리 role:"link") */
  linksBetween?: number;
}

export class Sim {
  now = 1_000_000;
  private timers: Array<{ at: number; fn: () => void; h: number }> = [];
  private hn = 0;
  readonly mem = new Map<string, string>();
  readonly calls: Array<{ cmd: string; args?: Record<string, unknown>; at: number }> = [];
  readonly seat = { surface_id: 5, role: "master", exited: false, agent_alive: true as boolean, gate_pending: null as unknown, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, working: false };
  lastHumanAt: number | null = null;
  /** 좌석 마지막 출력 시각(org.status idle_secs 의 근거) — 기록·답이 생길 때 출력이 있다고 둔다 */
  lastOutputAt: number | null = null;
  approvals: number[] = [];
  /** 데몬 쓰기 직전 판정이 보는 승인 창(가로줄 아래 꼬리) */
  screen = false;
  file: Array<Record<string, unknown>> = [];
  session = "sess-s3";
  readonly writes: WriteTruth[] = [];
  /** user 레코드 uuid → 그 레코드를 만든 쓰기 번호 */
  readonly recordOf = new Map<string, number>();
  /** 쓰기 번호 → user 레코드 uuid / 답 uuid */
  readonly recorded = new Map<number, string>();
  readonly replied = new Map<number, string>();
  private handler: ((e: { payload: unknown }) => void) | null = null;
  listens = 0;
  unlistens = 0;
  private n = 0;
  private lastUuid: string | null = "root";
  core: ChatCore;
  readonly deps: Deps;

  constructor(readonly o: SimOpts = {}) {
    const self = this;
    this.deps = {
      invoke: async (cmd, args) => self.invoke(cmd, args ?? {}),
      now: () => self.now,
      setTimeout: (fn, ms) => self.later(ms, fn),
      clearTimeout: (h) => {
        const i = self.timers.findIndex((t) => t.h === h);
        if (i >= 0) self.timers.splice(i, 1);
      },
      store: { get: (k) => self.mem.get(k) ?? null, set: (k, v) => void self.mem.set(k, v), remove: (k) => void self.mem.delete(k) },
      working: (r) => r.working === true,
      listen: async (name, h) => {
        if (name === "daemon-event") {
          self.handler = h;
          self.listens++;
        }
        return () => {
          if (self.handler === h) self.handler = null;
          self.unlistens++;
        };
      },
    };
    this.core = new ChatCore(this.deps);
  }

  later(ms: number, fn: () => void): number {
    const h = ++this.hn;
    this.timers.push({ at: this.now + ms, fn, h });
    return h;
  }

  /** 데몬 사건 방송(기본 데몬 = slug 일치). */
  emit(name: string, surface_id: number | null, payload: Record<string, unknown>, seq?: number, slug?: string, timestampSecs?: number): void {
    this.handler?.({ payload: { name, surface_id, payload, seq: seq ?? null, socket_slug: slug ?? this.o.slug ?? "default-slug", timestamp: timestampSecs ?? this.now / 1000 } });
  }
  /** 마스터가 이 말과 무관한 일을 함(깨움·도우미 보고 등) — 「답하는 중」 오칠 시험용 */
  workOther(ms: number): void {
    this.workStart();
    this.later(ms, () => this.workEnd());
  }
  /** 좌석 활동 = 진행 중인 일감 수 > 0(답 작업·무관한 일이 겹쳐도 하나가 끝났다고 쉼이 되지 않게) */
  private jobs = 0;
  private workStart(): void {
    this.jobs++;
    this.seat.working = true;
  }
  private workEnd(): void {
    this.jobs = Math.max(0, this.jobs - 1);
    if (this.jobs === 0) {
      this.seat.working = false;
      this.idleSince = this.now;
    }
  }
  /** 마지막으로 일을 멈춘 시각(하네스: 「답하는 중」인데 오래 쉼 = 틀림) */
  idleSince = 0;

  private human_idle(): number | null {
    return this.lastHumanAt === null ? null : Math.floor((this.now - this.lastHumanAt) / 1000);
  }

  private async invoke(cmd: string, a: Record<string, unknown>): Promise<unknown> {
    this.calls.push({ cmd, args: a, at: this.now });
    if (cmd === "default_socket_slug") return this.o.slug ?? "default-slug";
    if (cmd === "org_status") return { surfaces: [{ ...this.seat, human_idle_secs: this.human_idle(), idle_secs: this.lastOutputAt === null ? null : Math.floor((this.now - this.lastOutputAt) / 1000) }] };
    if (cmd === "feed_list") return { items: this.approvals.map((sid) => ({ kind: "approval", status: "pending", surface_id: sid })) };
    if (cmd === "chat_transcript") {
      if (a.fromEnd) return { status: "ok", session_id: this.session, next_offset: this.file.length, size: this.file.length, records: [] };
      return { status: "ok", session_id: this.session, next_offset: this.file.length, size: this.file.length, records: this.file.slice(a.afterOffset as number) };
    }
    if (cmd === "chat_send") return this.chatSend(String(a.text));
    throw new Error(`unexpected ${cmd}`);
  }

  private chatSend(text: string): Promise<unknown> {
    const n = this.n++;
    const sending = this.core.state.msgs.filter((m) => m.step === "sending" && m.text === text);
    const w: WriteTruth = { at: this.now, msgId: sending.length === 1 ? sending[0].id : null, text, bytesIn: false, submitted: false, refused: false, outcome: "" };
    this.writes.push(w);
    const wi = this.writes.length - 1;
    if (this.screen) {
      this.lastHumanAt = this.now; // 데몬 승인 창 거부도 사람 입력 시각을 찍는다(VERIFY 지적 7)
      w.refused = true;
      w.outcome = "held";
      return Promise.resolve({ outcome: "held", code: "approval_screen" });
    }
    const kind = this.o.plan ? this.o.plan(n, text) : "written";
    if (kind !== "failed") this.lastHumanAt = this.now; // 사람 표지 쓰기는 사람 입력 시각을 찍는다(handlers.rs:7633) · 쓰기 전 확정 거부는 찍지 않는다고 둠〔대역 가정〕
    const lands = kind === "written" || kind === "uncertain_written" || kind === "hang_written" || kind === "refuse_at_write";
    if (lands) {
      w.bytesIn = true;
      if (kind === "refuse_at_write") {
        // Enter 직전 재판정에서 창 → 제출 키 0 · 본문은 입력줄에 남음 · 미제출 계수 ≥ 1 · 사건 1건(≈0.5초 뒤)
        // ⚠이 꼴은 **통합 빌드**(데몬 고침 integ/1116-backlog e4499d72 approval_enter_guard)의 원자 제출 거부를 본뜬 것이다 — 기준판 3a012bf4 의
        //   원자 제출은 Enter 직전 재판정이 없어 이 사건을 내지 않는다(검토 지적 1 · handlers.rs:3779~3785).
        this.later(500, () => {
          this.seat.pending_input_bytes = Math.max(this.seat.pending_input_bytes, 1);
          this.emit("input.refused_at_write", this.seat.surface_id, { reason: "approval_screen" });
        });
      } else {
        this.later(768, () => this.submitted(wi, n));
      }
    }
    const resp = kind === "written" || kind === "hang_written" || kind === "refuse_at_write" ? { outcome: "written", result: { sent: true } } : kind === "failed" ? { outcome: "failed", code: "not_found" } : { outcome: "uncertain", code: "transport_uncertain" };
    w.outcome = resp.outcome;
    if (kind === "hang_written" || kind === "hang_lost") {
      return new Promise((res) => this.later(this.o.hangMs ?? 6_000, () => res(resp)));
    }
    return Promise.resolve(resp);
  }

  private submitted(wi: number, n: number): void {
    const w = this.writes[wi];
    w.submitted = true;
    const rd = this.o.recordDelay ? this.o.recordDelay(n) : 200;
    if (rd === null) return;
    this.later(rd, () => {
      const uuid = this.o.noUuid ? null : `u${wi}`;
      const text = this.o.wrapPaste?.(n) ? `\n\n<pasted_content id="${(0x3f00 + wi).toString(16)}">\n${w.text}\n</pasted_content id="${(0x3f00 + wi).toString(16)}">\n` : w.text;
      this.file.push({ uuid, parent: this.o.noUuid ? null : this.lastUuid, role: "user", text, ts: new Date(this.now).toISOString() });
      this.lastOutputAt = this.now;
      let tail = uuid;
      if (uuid) {
        this.recordOf.set(uuid, wi);
        this.lastUuid = uuid;
        for (let k = 0; k < (this.o.linksBetween ?? 0); k++) {
          const lu = `l${wi}-${k}`;
          this.file.push({ uuid: lu, parent: tail, role: "link", text: null, parts: null, ts: null, sidechain: false });
          tail = lu;
          this.lastUuid = lu;
        }
      }
      this.recorded.set(wi, uuid ?? `nouuid-${wi}`);
      const rp = this.o.replyDelay ? this.o.replyDelay(n) : 1_500;
      if (rp === null) return; // 답이 없으면 일하지도 않는 것으로 둔다
      this.workStart();
      this.later(rp, () => {
        const au = this.o.noUuid ? null : `a${wi}`;
        this.file.push({ uuid: au, parent: tail, role: "assistant", text: `답 ${wi}`, ts: new Date(this.now).toISOString() });
        this.lastOutputAt = this.now;
        if (au) this.lastUuid = au;
        this.replied.set(wi, au ?? `nouuid-a${wi}`);
        this.workEnd();
      });
    });
  }

  /** 마이크로태스크를 끝까지 비운다(매크로태스크 경계 2번 — 사슬 깊이와 무관). 시계는 움직이지 않는다. */
  async flush(): Promise<void> {
    const imm = (globalThis as unknown as { setImmediate(f: () => void): void }).setImmediate;
    for (let i = 0; i < 2; i++) await new Promise<void>((r) => imm(r));
  }

  async advance(ms: number, each?: () => void): Promise<void> {
    const until = this.now + ms;
    await this.flush(); // 지금 시각에 걸려 있던 사슬을 먼저 끝까지(시각을 옮기기 전에)
    for (;;) {
      this.timers.sort((a, b) => a.at - b.at || a.h - b.h);
      const t = this.timers[0];
      if (!t || t.at > until) break;
      this.timers.shift();
      this.now = t.at;
      t.fn();
      await this.flush();
      each?.();
    }
    this.now = until;
    await this.flush();
    each?.();
  }

  /** 대화 화면처럼 3초마다 poll 을 건다(ctx.timers.every 대역). */
  startPolling(ms = 3_000): void {
    const tick = () => {
      void this.core.poll();
      this.later(ms, tick);
    };
    this.later(ms, tick);
  }

  /** chat_send 수 = 쓰기 수(거부 포함 · 바이트 0 인 거부도 요청 1건). */
  sends(): number {
    return this.calls.filter((c) => c.cmd === "chat_send").length;
  }
}
