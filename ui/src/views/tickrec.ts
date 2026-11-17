// 3초 고리 특성 기록기 — TICKET=cysr-ui-slice0-1117 · 설계 P2-DESIGN §2-1 ㉠ 「시험 ① 특성 기록 먼저(조각 0)」.
//
// ★무엇을 하나: refreshPaneTitles(main.ts · 3초 고리) 한 틱의 **입력**(작업공간 트리 · 소켓별 좌석 목록 · 유령 카운터 ·
//   스윕 무장 · 자리표 장부)과 **결과**(입양 · 유령 퇴거 · 옛 자리 쓸기 · 자리표 회수 · 새 부서 탭 · 다시 그리기)를
//   링 200칸에 모은다. 조각 2(고리 분리)가 이 기록을 `decideTick` 에 다시 넣어 「같은 입력 → 같은 판정」을 대조한다.
//
// ★동작 변화 0 계약(이 파일 + main.ts 배선이 함께 지킨다):
//   ① 기본 = 꺼짐. 스위치는 localStorage `cys-tickrec` === "1" **하나뿐**(expertmode.ts 와 같은 규칙 — 다른 값은 전부 꺼짐).
//   ② 꺼짐이면 `tickRecFromSwitch` 가 null 을 돌려주고, main.ts 의 모든 배선은 `tickRec?.메서드(...)` 꼴이다 —
//      선택적 호출은 대상이 null 이면 **인자 식조차 평가하지 않는다**(ECMAScript 단락 평가). 그래서 꺼짐 상태의 고리는
//      종전과 같은 식만 같은 순서로 평가한다(정적 핀 = tickrec.test.ts · 실행 대조 = ui/e2e/tickrec_gate.py).
//   ③ 켜짐이어도 고리 쪽 부작용 0: 기록기는 데몬·Tauri·DOM·localStorage 에 쓰지 않는다(메모리 링 + window 진단 손잡이뿐).
//      기록기 안의 예외는 전부 여기서 삼킨다 — 기록 실패가 틱을 멈추면 안 된다.
//
// ★개인정보 0: 제목·작업 폴더·소켓 경로·유령 카운터 키(소켓 경로 포함)는 **길이 + 소금 친 해시**로만 남긴다.
//   소금은 기록기마다 새로 뽑고 덤프에 싣지 않는다(같은 덤프 안에서는 같은 값 = 같은 해시라 재생 대조는 되고,
//   사전 대입으로 경로를 되찾을 수는 없게). 역할 이름은 제품 어휘(master·cso·worker-2 등) 꼴일 때만 그대로, 아니면 해시.
//   대화 원문은 이 고리의 입력에 없다(좌석 목록에는 화면 글자가 오지 않는다).
//
// ★크기 상한: 링 200칸(넘치면 가장 오래된 칸부터 버림 = 회전) · 한 칸에 작업공간 64 · 소켓 32 · 소켓당 좌석 128 · 오류 16 —
//   넘친 칸은 `trunc` 로 표시한다. 덤프 크기 상한(설계 목표값) = TICKREC_MAX_DUMP_BYTES.

/** localStorage 키 — 이 키가 "1" 일 때만 켜진다. */
export const TICKREC_KEY = "cys-tickrec";
/** 링 칸 수(설계 §2-1 「링 200칸」). */
export const TICKREC_RING = 200;
/** 덤프 크기 상한(설계 목표값 · 좌석 12개 장면 실측으로 확정 — tickrec_gate.py 가 잰다). */
export const TICKREC_MAX_DUMP_BYTES = 2 * 1024 * 1024;
export const TICKREC_SCHEMA = "cys-tickrec/1";

const CAP_WS = 64;
const CAP_SOCK = 32;
const CAP_SURF = 128;
const CAP_ERR = 16;
const CAP_LIST = 256; // 번호 목록(트리 sid · 퇴거 · 쓸기 등) 한 칸 상한

/** 저장된 원시 문자열 → 켜짐 여부("1" 만 참). */
export function tickRecOn(raw: string | null | undefined): boolean {
  return raw === "1";
}

/** cyrb53(공개 영역 53비트 문자열 해시) — 암호 해시가 아니다. 목적 = 같은 덤프 안의 동일성 표시 + 원문 비노출(소금과 함께). */
export function hash53(s: string, seed = 0): string {
  let h1 = 0xdeadbeef ^ seed;
  let h2 = 0x41c6ce57 ^ seed;
  for (let i = 0; i < s.length; i++) {
    const ch = s.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16).padStart(14, "0");
}

const ROLE_WORD = /^[a-z][a-z0-9-]{0,31}$/;

/** 좌석 목록 한 줄 중 기록기가 읽는 칸(main.ts 의 list_surfaces 행과 같은 이름 · 전부 선택). */
export interface TickRecSurface {
  surface_id: number;
  title?: string | null;
  role?: string | null;
  live_cwd?: string | null;
  exited?: boolean;
  display_no?: number | null;
  line_count?: number | null;
  size?: { rows?: unknown; cols?: unknown } | null;
  cwd_blocked?: unknown;
}

export interface TickRecWorkspace {
  id: number;
  socket?: string;
  pending: boolean;
  deleting: boolean;
  sids: number[];
}

/** 자리표 회수 판정 입력(placeholderclose.ts PlaceholderInput 과 같은 칸 · role 은 해시 규칙 적용). */
export interface TickRecPlaceholderIn {
  isOwnPlaceholder: boolean;
  touched: boolean;
  role: string | null;
  lineCount: number | null;
  isWindows: boolean;
  formationArrived: boolean;
  exited: boolean;
}

export interface TickRecCounters {
  ticks: number; // begin 까지 온 틱(= 소비자가 실제로 돈 틱)
  skippedNotStarted: number; // 복원 전이라 바로 돌아간 틱
  skippedBusy: number; // 앞 틱이 아직 돌아 바로 돌아간 틱(겹침 방지 가드)
  sockSkip: number; // 목록을 받지 못해 건너뛴 소켓(틱×소켓)
  adopt: number;
  adoptAbort: number;
  evict: number;
  sweep: number;
  placeholderJudged: number;
  placeholderClose: number;
  placeholderClosed: number;
  deptOpened: number;
  render: number;
  err: number;
  dropped: number; // 링이 넘쳐 버린 칸
  recorderFault: number; // 기록기 자신의 예외(삼킴)
}

type Json = null | boolean | number | string | Json[] | { [k: string]: Json };

interface Entry {
  seq: number;
  now: number;
  ws: Json[];
  wsTrunc: boolean;
  ghostIn: Json[];
  sweepArmed: boolean;
  placeholders: number[];
  touched: number[];
  socks: Json[];
  ghost: Json[];
  sweep: Json[];
  adopt: Json[];
  adoptAbort: Json[];
  ph: { sock: string; sid: number; in: Json; close: boolean; closed: boolean | null }[];
  wsAfterDepts: number | null;
  render: Json;
  ghostOut: Json[] | null;
  sweepArmedAfter: boolean | null;
  notices: number | null;
  err: string[];
  done: boolean;
}

export interface TickRecorder {
  /** 틱 머리 가드 셈 — 복원 전(!started)이면 skippedNotStarted · 앞 틱이 도는 중(refreshing)이면 skippedBusy · 둘 다 아니면 셈 없음(begin 이 센다). */
  gate(started: boolean, refreshing: boolean): void;
  begin(
    now: number,
    ws: readonly TickRecWorkspace[],
    ghostStrike: ReadonlyMap<string, number>,
    sweepArmed: boolean,
    placeholders: ReadonlySet<number>,
    touched: ReadonlySet<number>,
  ): void;
  deptsDone(wsCount: number): void;
  sock(sock: string, value: unknown, adoptedHere: (sid: number) => boolean): void;
  ghost(sock: string, treeSids: readonly number[], evict: readonly number[]): void;
  sweep(sock: string, here: boolean, scope: readonly number[]): void;
  sweepSid(sock: string, sid: number): void;
  adopt(sock: string, sid: number, role: string | null): void;
  adoptAbort(sock: string, sid: number, noHome: boolean): void;
  placeholderIn(sock: string, sid: number, input: TickRecPlaceholderIn): void;
  placeholderClose(sock: string, sid: number): void;
  placeholderClosed(sock: string, sid: number): void;
  render(adopted: boolean, layoutChanged: boolean): void;
  error(at: string): void;
  end(ghostStrike: ReadonlyMap<string, number>, sweepArmed: boolean): void;
  notices(n: number): void;
  counters(): TickRecCounters;
  dump(): { schema: string; ring: number; counters: TickRecCounters; entries: Json[] };
  dumpJson(): string;
  clear(): void;
}

function zeroCounters(): TickRecCounters {
  return {
    ticks: 0, skippedNotStarted: 0, skippedBusy: 0, sockSkip: 0, adopt: 0, adoptAbort: 0, evict: 0, sweep: 0,
    placeholderJudged: 0, placeholderClose: 0, placeholderClosed: 0, deptOpened: 0, render: 0, err: 0, dropped: 0, recorderFault: 0,
  };
}

const capList = (xs: readonly number[]): number[] => xs.slice(0, CAP_LIST).map((x) => (typeof x === "number" ? x : -1));

/** 기록기 하나를 만든다. salt = 해시 소금(덤프에 싣지 않음) · ring = 칸 수(시험용 · 기본 200). */
export function createTickRecorder(opts: { salt: string; ring?: number }): TickRecorder {
  const ring = Math.max(1, Math.floor(opts.ring ?? TICKREC_RING));
  const salt = String(opts.salt);
  const entries: Entry[] = [];
  let c = zeroCounters();
  let seq = 0;
  let cur: Entry | null = null;

  const h = (s: string | null | undefined): string | null => (s == null ? null : hash53(salt + "\u0000" + s));
  const sockId = (s: string | undefined | null): string => (s == null || s === "" ? "~" : (h(s) as string)); // "~" = 기본 데몬
  const roleId = (r: string | null | undefined): string | null => (r == null ? null : ROLE_WORD.test(r) ? r : `#${h(r)}`);
  const strikes = (m: ReadonlyMap<string, number>): Json[] => {
    const out: Json[] = [];
    for (const [k, v] of m) {
      if (out.length >= CAP_SURF) break;
      const at = k.lastIndexOf("#"); // paneKey = `${socket}#${sid}` — 소켓 부분만 해시
      out.push([at >= 0 ? `${sockId(k.slice(0, at))}#${k.slice(at + 1)}` : (h(k) as string), typeof v === "number" ? v : -1]);
    }
    return out;
  };
  // 기록기 예외는 여기서 끝난다 — 고리로 새지 않는다.
  const safe = <A extends unknown[]>(fn: (...a: A) => void) => (...a: A): void => {
    try {
      fn(...a);
    } catch {
      c.recorderFault++;
    }
  };

  const rec: TickRecorder = {
    gate: safe((started, refreshing) => {
      if (!started) c.skippedNotStarted++;
      else if (refreshing) c.skippedBusy++;
    }),
    begin: safe((now, ws, ghostStrike, sweepArmed, placeholders, touched) => {
      if (cur && !cur.done) cur.err.push("unfinished"); // 앞 틱이 end 에 닿지 못했다(던짐 등) — 그 칸에 표시만
      c.ticks++;
      cur = {
        seq: ++seq, now, wsTrunc: ws.length > CAP_WS,
        ws: ws.slice(0, CAP_WS).map((w) => ({ id: w.id, sock: sockId(w.socket), pending: !!w.pending, deleting: !!w.deleting, sids: capList(w.sids) })),
        ghostIn: strikes(ghostStrike), sweepArmed: !!sweepArmed,
        placeholders: capList([...placeholders]), touched: capList([...touched]),
        socks: [], ghost: [], sweep: [], adopt: [], adoptAbort: [], ph: [],
        wsAfterDepts: null, render: null, ghostOut: null, sweepArmedAfter: null, notices: null, err: [], done: false,
      };
      entries.push(cur);
      while (entries.length > ring) {
        entries.shift();
        c.dropped++;
      }
    }),
    deptsDone: safe((wsCount) => {
      if (!cur) return;
      cur.wsAfterDepts = wsCount;
      const before = cur.ws.length + (cur.ws.length === 0 ? 1 : 0); // 빈 화면이면 고리가 먼저 빈 탭 1개를 만든다
      if (!cur.wsTrunc && wsCount > before) c.deptOpened += wsCount - before;
    }),
    sock: safe((sock, value, adoptedHere) => {
      if (!cur) return;
      const rows = (value as { surfaces?: unknown } | null | undefined)?.surfaces;
      if (!Array.isArray(rows)) {
        c.sockSkip++;
        if (cur.socks.length < CAP_SOCK) cur.socks.push({ sock: sockId(sock), got: false });
        return;
      }
      if (cur.socks.length >= CAP_SOCK) return;
      const surf = (rows as TickRecSurface[]).slice(0, CAP_SURF).map((s) => {
        const rows_ = s.size && typeof s.size === "object" ? (s.size as { rows?: unknown }).rows : undefined;
        const cols_ = s.size && typeof s.size === "object" ? (s.size as { cols?: unknown }).cols : undefined;
        return {
          sid: s.surface_id,
          role: roleId(s.role ?? null),
          ex: !!s.exited,
          no: typeof s.display_no === "number" ? s.display_no : s.display_no === null ? null : "absent",
          lc: typeof s.line_count === "number" ? s.line_count : null,
          tl: typeof s.title === "string" ? s.title.length : null,
          th: typeof s.title === "string" ? h(s.title) : null,
          cl: typeof s.live_cwd === "string" ? s.live_cwd.length : null,
          ch: typeof s.live_cwd === "string" ? h(s.live_cwd) : null,
          sz: typeof rows_ === "number" && typeof cols_ === "number" ? [rows_, cols_] : null,
          cb: s.cwd_blocked != null && s.cwd_blocked !== false,
          pane: !!adoptedHere(s.surface_id),
        } as Json;
      });
      cur.socks.push({ sock: sockId(sock), got: true, n: rows.length, trunc: rows.length > CAP_SURF, surf });
    }),
    ghost: safe((sock, treeSids, evict) => {
      if (!cur) return;
      c.evict += evict.length;
      cur.ghost.push({ sock: sockId(sock), tree: capList(treeSids), evict: capList(evict) });
    }),
    sweep: safe((sock, here, scope) => {
      if (!cur) return;
      cur.sweep.push({ sock: sockId(sock), here: !!here, scope: capList(scope), targets: [] });
    }),
    sweepSid: safe((sock, sid) => {
      if (!cur) return;
      c.sweep++;
      const id = sockId(sock);
      const row = [...cur.sweep].reverse().find((x) => (x as { sock: string }).sock === id) as { targets: number[] } | undefined;
      if (row && row.targets.length < CAP_LIST) row.targets.push(sid);
    }),
    adopt: safe((sock, sid, role) => {
      if (!cur) return;
      c.adopt++;
      if (cur.adopt.length < CAP_LIST) cur.adopt.push({ sock: sockId(sock), sid, role: roleId(role) });
    }),
    adoptAbort: safe((sock, sid, noHome) => {
      if (!cur) return;
      c.adoptAbort++;
      if (cur.adoptAbort.length < CAP_LIST) cur.adoptAbort.push({ sock: sockId(sock), sid, noHome: !!noHome });
    }),
    placeholderIn: safe((sock, sid, input) => {
      if (!cur) return;
      c.placeholderJudged++;
      if (cur.ph.length >= CAP_LIST) return;
      cur.ph.push({
        sock: sockId(sock), sid, close: false, closed: null,
        in: {
          own: !!input.isOwnPlaceholder, touched: !!input.touched, role: roleId(input.role), lc: typeof input.lineCount === "number" ? input.lineCount : null,
          win: !!input.isWindows, arrived: !!input.formationArrived, ex: !!input.exited,
        },
      });
    }),
    placeholderClose: safe((sock, sid) => {
      if (!cur) return;
      c.placeholderClose++;
      const id = sockId(sock);
      const p = [...cur.ph].reverse().find((x) => x.sock === id && x.sid === sid);
      if (p) p.close = true;
    }),
    placeholderClosed: safe((sock, sid) => {
      if (!cur) return;
      c.placeholderClosed++;
      const id = sockId(sock);
      const p = [...cur.ph].reverse().find((x) => x.sock === id && x.sid === sid);
      if (p) p.closed = true;
    }),
    render: safe((adopted, layoutChanged) => {
      if (!cur) return;
      c.render++;
      cur.render = { adopted: !!adopted, layoutChanged: !!layoutChanged };
    }),
    error: safe((at) => {
      c.err++;
      if (cur && cur.err.length < CAP_ERR) cur.err.push(ROLE_WORD.test(at) ? at : "other");
    }),
    end: safe((ghostStrike, sweepArmed) => {
      if (!cur) return;
      cur.ghostOut = strikes(ghostStrike);
      cur.sweepArmedAfter = !!sweepArmed;
      cur.done = true;
    }),
    notices: safe((n) => {
      if (!cur) return;
      cur.notices = typeof n === "number" ? n : null;
    }),
    counters: () => ({ ...c }),
    dump: () => ({ schema: TICKREC_SCHEMA, ring, counters: { ...c }, entries: entries.map((e) => JSON.parse(JSON.stringify(e)) as Json) }),
    dumpJson: () => JSON.stringify(rec.dump()),
    clear: () => {
      entries.length = 0;
      c = zeroCounters();
      cur = null;
    },
  };
  return rec;
}

/**
 * 스위치를 읽어 켜졌을 때만 기록기를 만든다 — 꺼짐(기본) = null(main.ts 의 `tickRec?.` 배선이 전부 무평가가 된다).
 * read = 스위치 원시 값 읽기(main.ts 가 localStorage 를 넘김 · 던지면 꺼짐) · salt = 소금 원천 · expose = 진단 손잡이 걸기.
 */
export function tickRecFromSwitch(deps: {
  read: () => string | null;
  salt: () => string;
  expose?: (r: TickRecorder) => void;
}): TickRecorder | null {
  let raw: string | null = null;
  try {
    raw = deps.read();
  } catch {
    return null;
  }
  if (!tickRecOn(raw)) return null;
  try {
    const r = createTickRecorder({ salt: deps.salt() });
    deps.expose?.(r);
    return r;
  } catch {
    return null;
  }
}

/** 소금 원천(웹뷰 · 켜졌을 때만 부른다). crypto 가 없으면 시각+난수로 떨어진다(진단 기록용 소금 — 비밀 아님). */
export function defaultTickRecSalt(): string {
  try {
    const a = new Uint32Array(4);
    globalThis.crypto.getRandomValues(a);
    return [...a].map((x) => x.toString(16)).join("");
  } catch {
    return `${Date.now()}-${Math.random()}`;
  }
}
