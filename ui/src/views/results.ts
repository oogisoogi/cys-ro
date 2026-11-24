// (cysr-1116-s79 · TICKET=cysr-1116-s79-1119) 결과 받기 장부 — 공통층 한 부분(대화 화면이 켜져 있을 때만 돈다 · ConfirmBook 과 같은 수명). P2-DESIGN §11 조각 7.
//
// 받는 것(데몬 무변경 · 새 Tauri 명령 = result_open 하나):
//  · 마스터 답 속 경로 = core 가 읽은 결속 세션 레코드(조각 1 chat_transcript · 시작 오프셋 뒤만) → judge/results.candidatesOf
//  · 스킬 산출 폴더 = daemon-event `skill.run_finished`(본부 slug 일 때만 · ConfirmBook 과 같은 규칙)
//  · 홈 = Tauri `home_dir_path`(대화 화면이 켜질 때 1회) · 실재 = Tauri `list_dir(부모)`(§5-1 「실재 확인은 Tauri 기존 list_dir」 · 작업 화면 살핌 중 = 0)
// 행동(누르기 → 실재 재확인 await 뒤 화면 재판정 = 작업 화면 살핌 중이면 0 · codex 3R ②): 열기·폴더 보기 = 우리 Tauri 명령 `result_open`(viewcore.rs — 정규 경로 가둠 · 열기 = 허용 목록 종류의 보통 파일·꾸러미 아닌 폴더만 · 가명 거절 ·
//       그 밖 `executable_confirm` → **force 로 다시 부르지 않음** · 폴더 보기로 안내) · 둘 다 누르기 직전 실재를 다시 확인(없으면 호출 0 + 「파일을 찾을 수 없어요」).
// 저장 = 앱 저장소 `cys-chat-results`(경로·출처·시각·봤음 · 말 원문 0자 · 최근 50).
// (1.1.19 OB-O4) 치우기·모두 치우기 = 목록에서만 숨김(저장 + 다시 그리기 · invoke 0 = 파일 무변경) · 없어진 지 7일 = 틱에서 자동 숨김 · 숨긴 카드 = 실재 확인 0.

import type { Rec } from "./judge/msgstep";
import {
  addCandidates,
  candidatesOf,
  expireMissing,
  hideAll,
  hideResult,
  openAllowedName,
  listErrorIsMissing,
  parentOf,
  persistable,
  presenceIn,
  restoreResults,
  skillCandidateOf,
  withPresence,
  type Candidate,
  type Result,
} from "./judge/results";

export const RESULTS_KEY = "cys-chat-results";
/** 한 번의 poll 에서 실재를 확인하는 결과 수(list_dir 호출 상한 · 3초마다). */
export const CHECK_PER_TICK = 3;

export interface ResultDeps {
  invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown>;
  now(): number;
  store: { get(k: string): string | null; set(k: string, v: string): void };
  /** (s79 · codex 3R ②) 지금 대화 화면인가 — core 의 한 도우미(onChatScreen · deliver 와 같은 판정) · 없으면 늘 대화 화면(시험·단독). */
  onChat?(): boolean;
}

export const MSG_MISSING = "파일을 찾을 수 없어요 — 「마스터에게 물어보기」로 어디 있는지 물어볼 수 있어요.";
export const MSG_EXEC = "이 파일은 열면 프로그램이 실행될 수 있어 열지 않았어요 — 「폴더 보기」로 확인해 주세요.";
export const MSG_UNKNOWN = "파일이 있는지 확인하지 못했어요 — 잠시 뒤 다시 눌러 주세요.";
export const MSG_NETWORK = "이 결과는 네트워크 폴더에 있어 열지 않았어요 — 「폴더 보기」나 작업 화면에서 확인해 주세요.";
export const MSG_WORK_VIEW = "작업 화면으로 옮겨서 열지 않았어요 — 대화 화면에서 다시 눌러 주세요.";
export const MSG_OUTSIDE = "이 결과는 홈 폴더 밖(또는 숨은 폴더)으로 이어져 있어 열지 않았어요 — 마스터에게 물어봐 주세요.";

export class ResultBook {
  private list: Result[];
  private home: string | null = null;
  private homeAsked = false;
  /** 홈을 알기 전에 읽은 답 레코드(홈을 알면 그때 판정) */
  private early: Rec[] = [];
  private earlySkill: unknown[] = [];
  private hqSlug: string | null = null;
  private checking = new Set<string>();
  private acting = false;
  /** 마지막 행동 결과(결과 칸 아래 1줄) */
  notice: string | null = null;
  /** (s79 · 독립 검증 V4) 작업 화면 살핌 중 — 실재 확인(list_dir) 0 · 후보는 모아 두었다가 대화 화면에서 확인 */
  paused = false;

  constructor(
    private readonly d: ResultDeps,
    private readonly changed: () => void,
  ) {
    let raw: string | null = null;
    try {
      raw = d.store.get(RESULTS_KEY);
    } catch {
      raw = null;
    }
    this.list = restoreResults(raw);
  }

  /** 지금 목록(최근 것부터 · 숨은 후보 포함 — 그리기는 judge/results.visibleResults 로 거른다). */
  get items(): readonly Result[] {
    return this.list;
  }

  /** (OB-O4) 「치우기」 — 목록에서만 숨김(파일 명령 0). */
  hide(id: string): void {
    const next = hideResult(this.list, id);
    if (next.every((r, i) => r === this.list[i])) return;
    this.list = next;
    this.save();
    this.changed();
  }

  /** (OB-O4) 「모두 치우기」(화면이 확인 1회를 받은 뒤 부름) — 보이는 카드 전부 숨김(파일 명령 0). */
  hideAll(): void {
    const next = hideAll(this.list);
    if (next.every((r, i) => r === this.list[i])) return;
    this.list = next;
    this.save();
    this.changed();
  }

  get busy(): boolean {
    return this.acting;
  }

  /** 대화 화면이 켜질 때 core 가 부른다 — 홈 1회. */
  async start(): Promise<void> {
    if (this.home !== null || this.homeAsked) return;
    this.homeAsked = true;
    const h = await this.d.invoke("home_dir_path").catch(() => null);
    if (typeof h !== "string" || !h) {
      this.homeAsked = false; // 다음 켜짐에 다시
      return;
    }
    this.home = h;
    const recs = this.early;
    const sk = this.earlySkill;
    this.early = [];
    this.earlySkill = [];
    this.onTail(recs);
    for (const p of sk) this.addSkill(p);
  }

  setHqSlug(slug: string | null): void {
    this.hqSlug = slug;
  }

  /** core 가 시작 오프셋 뒤를 읽은 레코드. */
  onTail(recs: readonly Rec[]): void {
    if (this.home === null) {
      this.early.push(...recs.filter((r) => r.role === "assistant"));
      return;
    }
    const cands: Candidate[] = [];
    for (const r of recs) cands.push(...candidatesOf(r, this.home));
    this.add(cands);
  }

  /** daemon-event 하나(대화 화면이 켜져 있을 때) — 본부 slug 의 skill.run_finished 만. */
  onEvent(ev: unknown): void {
    const e = (ev ?? {}) as { name?: unknown; payload?: unknown; socket_slug?: unknown };
    if (e.name !== "skill.run_finished") return;
    if (this.hqSlug === null || typeof e.socket_slug !== "string" || e.socket_slug !== this.hqSlug) return; // 부서 데몬 사건 = 버림(ConfirmBook 과 같은 규칙)
    if (this.home === null) {
      this.earlySkill.push(e.payload);
      return;
    }
    this.addSkill(e.payload);
  }

  private addSkill(payload: unknown): void {
    if (this.home === null) return;
    const c = skillCandidateOf(payload, this.home);
    if (c) this.add([c]);
  }

  private add(cands: readonly Candidate[]): void {
    if (!cands.length) return;
    const next = addCandidates(this.list, cands, this.d.now());
    if (next.length === this.list.length && next.every((r, i) => r === this.list[i])) return;
    this.list = next;
    this.save();
    this.changed();
    void this.tick();
  }

  private patch(id: string, p: Partial<Result>): void {
    const i = this.list.findIndex((r) => r.id === id);
    if (i < 0) return;
    this.list = this.list.map((r, j) => (j === i ? { ...r, ...p } : r));
    this.save();
    this.changed();
  }

  private save(): void {
    try {
      this.d.store.set(RESULTS_KEY, persistable(this.list));
    } catch {
      /* 저장 실패는 화면을 막지 않는다(메모리 목록은 그대로) */
    }
  }

  /** 실재 확인 하나 — true/false/null(모름). 결과를 목록에 반영. */
  async check(id: string): Promise<boolean | null> {
    const r = this.list.find((x) => x.id === id);
    if (!r || this.checking.has(id)) return r?.exists ?? null;
    this.checking.add(id);
    try {
      let v: { exists: boolean; isDir: boolean | null } | null;
      try {
        const listing = await this.d.invoke("list_dir", { path: parentOf(r.path) });
        v = presenceIn(listing, r.name, /^[A-Za-z]:[\\/]/.test(r.path) || r.path.startsWith("/Users/")); // 윈도·맥 = 대소문자 무시
      } catch (e) {
        v = listErrorIsMissing(e instanceof Error ? e.message : String(e)) ? { exists: false, isDir: null } : null;
      }
      if (v === null) return null;
      const cur = this.list.find((x) => x.id === id);
      if (cur && (cur.exists !== v.exists || (v.isDir !== null && cur.isDir !== v.isDir) || (cur.missingAt !== null) === v.exists)) {
        const w = withPresence(cur, v.exists, v.isDir, this.d.now()); // (OB-O4) 없음을 처음 본 시각
        this.patch(id, { exists: w.exists, isDir: w.isDir, missingAt: w.missingAt });
      }
      return v.exists;
    } finally {
      this.checking.delete(id);
    }
  }

  /** poll 마다 — 아직 모르는 결과의 실재를 최대 CHECK_PER_TICK 개 확인(오래된 것 아닌 최근 것부터). */
  async tick(): Promise<void> {
    if (this.home === null || this.paused) return;
    const kept = expireMissing(this.list, this.d.now()); // (OB-O4) 없어진 지 7일 = 숨김
    if (kept !== this.list) {
      this.list = [...kept];
      this.save();
      this.changed();
    }
    const todo = this.list.filter((r) => r.exists === null && !r.hidden && !this.checking.has(r.id)).slice(0, CHECK_PER_TICK); // 숨긴 카드 = 확인 0
    await Promise.all(todo.map((r) => this.check(r.id)));
  }

  /** 열기·폴더 보기(신뢰 클릭에서만 불림) — 누르기 직전 실재 확인 · 없으면 호출 0. 진행 중이면 무시(클릭 1 → 호출 ≤ 1). */
  async act(id: string, how: "open" | "reveal"): Promise<void> {
    if (this.acting) return;
    const r = this.list.find((x) => x.id === id);
    if (!r) return;
    this.acting = true;
    this.notice = null;
    this.changed();
    try {
      const ex = await this.check(id);
      // (s79 · codex 3R ②) list_dir 를 기다리는 사이 작업 화면으로 옮겼으면 OS 에 넘기지 않는다(result_open 0) — deliver 와 같은 한 도우미로 다시 판정
      if (this.paused || !(this.d.onChat?.() ?? true)) {
        this.notice = MSG_WORK_VIEW;
        return;
      }
      if (ex === false) {
        this.notice = MSG_MISSING;
        return;
      }
      if (ex === null) {
        this.notice = MSG_UNKNOWN;
        return;
      }
      if (how === "open" && !openAllowedName(r.name, r.isDir)) {
        // 앱 꾸러미(.app 등)는 폴더라 Tauri 실행형 검사(파일만)를 지나간다 — 마스터 글에서 온 경로로 프로그램을 띄우지 않는다(폴더 보기만)
        this.notice = MSG_EXEC;
        return;
      }
      try {
        // 우리 Tauri 명령 result_open(viewcore.rs) — 정규 경로(링크 풂)가 정규 홈 아래인지 다시 가두고 · 실행 꾸러미 거절 · 그 뒤 기존 open_path/reveal_path(force 없음).
        //   실행형은 Tauri 가 거절하고, 우리는 force 로 다시 묻지 않는다(쉬운 화면에서 실행 0 · codex 1R blocking = 홈 안 링크 → 홈 밖 .app)
        await this.d.invoke("result_open", { path: r.path, reveal: how === "reveal" });
        this.patch(id, { seen: true });
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.includes("executable_confirm")) this.notice = MSG_EXEC;
        else if (msg.includes("network_path")) this.notice = MSG_NETWORK;
        else if (msg.includes("outside_home") || msg.includes("hidden_path")) this.notice = MSG_OUTSIDE;
        else if (/not a local path/.test(msg)) {
          this.patch(id, { exists: false, missingAt: r.missingAt ?? this.d.now() });
          this.notice = MSG_MISSING;
        } else this.notice = `열지 못했어요 — 작업 화면에서 확인해 주세요.`;
      }
    } finally {
      this.acting = false;
      this.changed();
    }
  }
}
