// (cysr-1116-s6 · TICKET=cysr-1116-s6-1119) 왼쪽 메뉴바 장부 — 공통층 한 부분(대화 화면이 켜져 있을 때만 돈다). P2-DESIGN §11 조각 6 · §5-1.
//
// 받는 것(이미 있는 길만 · 데몬 무변경):
//  · 좌석 목록 = Tauri `list_surfaces`(본부 · 작업 화면 3초 고리와 같은 명령) — core 의 3초 조회 뒤 1회 · 시간 상한 · 실패면 직전 값.
//    ★쓰기 직전 재조회(fetchFresh)에는 넣지 않는다 — 사람 말 쓰기 길의 시간 예산(OBS_MAX_MS)을 건드리지 않게.
//  · 자기보고·출력 시각·승인 대기 = core 가 3초마다 받는 org.status · feed 원문을 그대로(새 조회 0).
//  · 부서 등록부 = Tauri `list_depts`(파일 읽기) — 10번째 조회마다(30초) · 처음 1회.
//  · 사람이 옮긴 묶음 = 앱 기록 cys-seat-group(작업 화면이 주인 · 여기서는 읽기만).
//  · 「팀 만드는 중」·「부서로 올리는 중」 = 결속 세션 기록의 마스터 답 표식(core 가 읽은 레코드를 그대로) + 묶음 사건 surface.group.changed.
//  · 부서 가이드 본 적 있음 = 앱 기록 cys-dept-guide-seen(§16-5 ②).
// 판정은 judge/rail.ts(순수) · 그리기는 chat/rail.ts.

import { addMarkers, formingMarkersOf, railModel, type Marker, type RailModel } from "./judge/rail";
import type { Rec } from "./judge/msgstep";
import { cleanGroupName, SEAT_GROUP_KEY } from "../seatgroup";

export const DEPT_GUIDE_KEY = "cys-dept-guide-seen";
/** 좌석 목록 왕복 상한(설계 목표값 · core OBS_MAX_MS 와 같은 값). */
export const LIST_MAX_MS = 500;
/** 부서 등록부를 다시 읽는 조회 간격(3초 × 10 = 30초 · 설계 목표값). */
export const DEPTS_EVERY = 10;
const MARKERS_MAX = 20;

export interface RailDeps {
  invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown>;
  now(): number;
  setTimeout(fn: () => void, ms: number): unknown;
  clearTimeout(h: unknown): void;
  store: { get(k: string): string | null; set(k: string, v: string): void };
  working(row: Record<string, unknown>): boolean;
}

export class RailBook {
  private surfaces: Record<string, unknown>[] | undefined = undefined;
  private org: unknown = undefined;
  private approvals: number[] | null = null;
  private depts: unknown = undefined;
  private markers: Marker[] = [];
  private ticks = 0;
  private busy = false;
  private hqSlug: string | null = null;
  private m: RailModel;
  /** 가이드를 지금 펼쳐 보이는가 — first = 처음 부서(「알겠어요」 단추) · again = 「부서 안내」로 다시 보기 */
  guide: "first" | "again" | null = null;

  constructor(
    private readonly d: RailDeps,
    private readonly changed: () => void,
  ) {
    this.m = this.compute();
  }

  get model(): RailModel {
    return this.m;
  }

  setHqSlug(s: string | null): void {
    this.hqSlug = s;
  }

  /** core 의 3초 조회 직후(대화 화면이 켜져 있을 때만 불린다). org·feed = 그 조회 원문 · approvals = feed 에서 고른 승인 대기 좌석. */
  async refresh(org: unknown, approvals: number[] | null): Promise<void> {
    if (org !== undefined) this.org = org;
    if (approvals !== null) this.approvals = approvals;
    if (this.busy) {
      this.recompute();
      return;
    }
    this.busy = true;
    try {
      const wantDepts = this.ticks % DEPTS_EVERY === 0;
      this.ticks++;
      const [list, depts] = await Promise.all([this.bounded(this.d.invoke("list_surfaces", { socket: null })), wantDepts ? this.d.invoke("list_depts").catch(() => undefined) : Promise.resolve(undefined)]);
      const rows = (list as { surfaces?: unknown } | undefined)?.surfaces;
      if (Array.isArray(rows)) this.surfaces = rows.filter((r): r is Record<string, unknown> => !!r && typeof r === "object");
      if (depts !== undefined) this.depts = depts;
    } finally {
      this.busy = false;
    }
    this.recompute();
  }

  /** core 가 읽은 결속 세션 레코드(뒤 기록) — 「만드는 중」 표식을 모은다. */
  onTail(recs: readonly Rec[]): void {
    const found = recs.flatMap((r) => formingMarkersOf(r));
    if (!found.length) return;
    this.markers = addMarkers(this.markers, found, this.d.now()).slice(-MARKERS_MAX);
    this.recompute();
  }

  /** daemon-event — 본부 데몬의 묶음 사건만(부서 데몬은 좌석 번호가 겹친다). 목록 칸을 바로 고쳐 쓰고 다시 판정(다음 3초 목록이 같은 값을 싣는다). */
  onEvent(raw: unknown): void {
    const e = raw as { name?: unknown; socket_slug?: unknown; surface_id?: unknown; payload?: unknown; group?: unknown } | null;
    if (!e || e.name !== "surface.group.changed") return;
    if (this.hqSlug === null || e.socket_slug !== this.hqSlug) return;
    const p = (e.payload && typeof e.payload === "object" ? e.payload : e) as { surface_id?: unknown; group?: unknown };
    const sid = typeof p.surface_id === "number" ? p.surface_id : typeof e.surface_id === "number" ? e.surface_id : null;
    if (sid === null || !this.surfaces) return;
    const row = this.surfaces.find((r) => r.surface_id === sid);
    if (!row) return;
    row.group = cleanGroupName(p.group);
    row.group_set = true;
    this.recompute();
  }

  /** 처음 부서가 생겼고 가이드를 본 적 없으면 펼친다(§16-6 · 한 번). */
  private maybeFirstGuide(): void {
    if (this.guide !== null || this.m.depts.length === 0) return;
    let seen: string | null = null;
    try {
      seen = this.d.store.get(DEPT_GUIDE_KEY);
    } catch {
      seen = null;
    }
    if (seen === null) this.guide = "first";
  }

  /** 「알겠어요」 — 본 적 있음 기록 · 접음. */
  ackGuide(): void {
    try {
      this.d.store.set(DEPT_GUIDE_KEY, JSON.stringify({ v: 1, at: this.d.now() }));
    } catch {
      /* 저장 못 해도 접는다(다음 실행에 한 번 더 보일 뿐) */
    }
    this.guide = null;
    this.changed();
  }

  /** 「부서 안내」 — 저장소와 무관하게 늘 열림 · 다시 누르면 접음. */
  toggleGuide(): void {
    this.guide = this.guide === null ? "again" : null;
    this.changed();
  }

  private compute(): RailModel {
    let raw: string | null = null;
    try {
      raw = this.d.store.get(SEAT_GROUP_KEY);
    } catch {
      raw = null;
    }
    return railModel({ surfaces: this.surfaces, org: this.org, approvalSeats: this.approvals, seatGroupsRaw: raw, depts: this.depts, markers: this.markers, nowMs: this.d.now(), working: this.d.working });
  }

  private recompute(): void {
    this.m = this.compute();
    this.maybeFirstGuide();
    this.changed();
  }

  private bounded(p: Promise<unknown>): Promise<unknown> {
    return new Promise((res) => {
      let done = false;
      const h = this.d.setTimeout(() => {
        if (done) return;
        done = true;
        res(undefined);
      }, LIST_MAX_MS);
      p.then(
        (v) => {
          if (done) return;
          done = true;
          this.d.clearTimeout(h);
          res(v);
        },
        () => {
          if (done) return;
          done = true;
          this.d.clearTimeout(h);
          res(undefined);
        },
      );
    });
  }
}
