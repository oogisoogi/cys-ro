// 경보 알림 문구 — 순수(v116-ui-close-r2 · D4 #8).
// 승인·유휴·사망 알림과 맥 시스템 알림이 `surface:N`·역할 코드(master·worker-13)·내부 지침 문구를 그대로 실었다.
// 여기서는 **표현만** 사람 말로 바꾼다 — 무엇이 일어났는지(사실)·경보의 세기(❌·🚨·⚠ 머리)는 그대로다.
//   · 창 이름 = 「N번 <역할 이름> 창」 — 창 머리 제목 「N · 특성」의 번호와 대조된다(D4 #12).
//   · 역할 이름 = friendlyRole(복원 카드와 같은 풀이).
//   · 사용자가 할 일은 한 문장으로 맨 끝에. 확인할 수 없는 약속(「자동으로 다시 켭니다」 등)은 적지 않는다.
import { friendlyRole } from "./restorebrief";

/** raw = 진단용 원문(있으면 알림의 접힌 「자세히」 안쪽 · D4 #14 도우미) — 본문에는 싣지 않는다. */
export type AlertCopy = { title: string; body: string; raw?: string };

/** 이벤트 surface_id 우선, 없으면 surface_ref(「surface:N」)에서 번호. 못 읽으면 null. */
export function seatNo(sid: unknown, surfaceRef: unknown): number | null {
  const n = Number(sid);
  if (sid != null && sid !== "" && Number.isInteger(n) && n >= 0) return n;
  const m = /^surface:(\d+)$/.exec(String(surfaceRef ?? ""));
  return m ? Number(m[1]) : null;
}

/**
 * (v116-num) 알림의 번호 = 창 머리 제목과 같은 **보이는 번호**(1~999 순환). `lookup` 은 내부 번호 → 데몬이 준 display_no.
 *   · lookup 이 undefined(옛 데몬 · 목록에서 아직 못 본 창) → 내부 번호 그대로(종전 동작).
 *   · lookup 이 null(보이는 번호 없음 「—」) → null(번호 없이 「작업 창」).
 */
export function visibleNo(internal: number | null, lookup: (sid: number) => number | null | undefined): number | null {
  if (internal == null) return null;
  const d = lookup(internal);
  return d === undefined ? internal : d;
}

/**
 * 「3번 작업 창」 · 역할 없으면 「3번 창」 · 번호 없으면 「작업 창」/「한 창」.
 * (Fable MINOR-3) 부서 데몬의 이벤트면 부서 이름을 앞에 — 본부와 부서는 창 번호가 겹칠 수 있다.
 */
export function seatName(no: number | null, role: unknown, dept?: unknown): string {
  const d = typeof dept === "string" && dept.trim() ? `${dept.trim()} ` : "";
  const r = typeof role === "string" && role.trim() ? `${friendlyRole(role.trim())} ` : "";
  if (no != null) return `${d}${no}번 ${r}창`;
  return r || d ? `${d}${r}창` : "한 창";
}

/** 초 → 「40초」·「5분」·「2시간 10분」. */
export function durText(secs: unknown): string {
  const s = Math.max(0, Math.floor(Number(secs) || 0));
  if (s < 60) return `${s}초`;
  if (s < 3600) return `${Math.floor(s / 60)}분`;
  const m = Math.floor((s % 3600) / 60);
  return `${Math.floor(s / 3600)}시간${m ? ` ${m}분` : ""}`;
}

const clip = (v: unknown, n: number) => String(v ?? "").slice(0, n);
const CHECK = "그 창을 눌러 상태를 확인해 주세요.";

export function approvalRequestCopy(no: number | null, p: Record<string, unknown>): AlertCopy {
  const ex = clip(p.excerpt, 100).trim();
  return {
    title: "⚠ 승인 대기",
    body: `${seatName(no, p.role, p.dept)}이 실행 허락을 기다립니다${ex ? ` — 「${ex}」` : ""}. 그 창을 눌러 확인할 수 있습니다.`,
  };
}

/** 사람 확인이 필요한 승인(방치 · 대신 처리할 자리 없음). 화면은 승인 목록을 연다(main.ts openFeed). */
export function approvalStalledCopy(no: number | null, p: Record<string, unknown>): AlertCopy {
  const who = no != null ? `${seatName(no, p.role, p.dept)}의 ` : "";
  const t = clip(p.title, 80).trim();
  const age = Math.floor(Number(p.age_secs) || 0);
  const what = age > 0 ? `${who}요청이 ${durText(age)} 넘게 처리되지 않았습니다` : `${who}요청은 사람 확인이 필요합니다`;
  return {
    title: "⚠ 승인 방치 — 사람 확인 필요",
    body: `${what}${t ? ` — 「${t}」` : ""}. 열린 승인 목록에서 허락할지 골라 주세요.`,
  };
}

/** 데몬 action 칸(내부 지침 문구)은 싣지 않는다 — 사실(몇 %·기준 몇 %)만 사람 말로. */
export function contextThresholdCopy(no: number | null, p: Record<string, unknown>): AlertCopy {
  return {
    title: `🔋 대화 기억 ${p.context_pct}%`,
    body: `${seatName(no, p.role, p.dept)}의 대화 기억이 기준 ${p.threshold}%를 넘었습니다. 한 번 정리할 때가 됐습니다.`,
  };
}

export function paneIdleCopy(no: number | null, p: Record<string, unknown>): AlertCopy {
  return {
    title: "💤 조용한 창",
    body: `${seatName(no, p.role, p.dept)}에서 ${durText(p.idle_seconds)} 동안 새 출력이 없습니다. 멈춘 것 같으면 ${CHECK}`,
  };
}

export function masterIdleCopy(no: number | null, role: string, p: Record<string, unknown>): AlertCopy {
  return {
    title: `💤 ${friendlyRole(role)} 창이 조용합니다`,
    body:
      `${seatName(no, role, p.dept)}에서 ${durText(p.idle_secs)} 동안 새 출력이 없습니다` +
      // (agy 3R MAJOR 수용) 종전 문구의 기준 시간(threshold_secs)을 잃지 않는다 — 사실 보존.
      (p.threshold_secs != null ? `. 알림 기준은 ${durText(p.threshold_secs)}입니다` : "") +
      `. 기다리는 중일 수 있으니 오래 이어지면 ${CHECK}`,
  };
}

/** AI(클로드 등)가 끝나고 창의 명령줄만 남았다(데몬 governance check_agent_death · 1회). */
export function agentExitedCopy(no: number | null, p: Record<string, unknown>): AlertCopy {
  return {
    title: "❌ AI가 꺼졌습니다", // (Fable MAJOR-3) 「멈춤」은 💤 유휴 문구와 겹친다 — 본문 「종료」와 같은 뜻으로
    body: `${seatName(no, p.role, p.dept)}의 AI가 종료됐습니다. 창과 작업 폴더는 그대로 남아 있습니다. ${CHECK}`,
  };
}

/** deadman 축(governance DeadmanAxis::as_str) → 사람 말. 모르는 축은 데몬 사유 원문을 그대로 싣는다(사실 보존). */
const DEADMAN_AXIS: Record<string, string> = {
  surface_gone: "창이 사라졌습니다",
  surface_exited: "창이 끝났습니다",
  shell_proc_dead: "창의 명령줄이 꺼졌습니다",
  agent_dead: "창의 AI가 꺼졌습니다",
  seat_vacant_no_meta: "창에 AI가 없습니다",
  agent_never_started: "창의 AI가 시작되지 않았습니다",
};
/** (Fable MAJOR-1) 창 자체가 없어진 축 — 「그 창을 눌러」는 누를 곳이 없다. ↻ 재시작 = 엔진을 다시 켜고 창을 자동 복원(index.html 툴팁). */
const DEADMAN_NO_WINDOW = new Set(["surface_gone", "surface_exited"]);
export function deadmanCopy(no: number | null, p: Record<string, unknown>): AlertCopy {
  const role = typeof p.role === "string" && p.role ? p.role : "master";
  const axis = String(p.axis ?? "");
  // (Fable MINOR-5) 모르는 축은 사람 말로 닫고, 데몬 사유 원문은 「자세히」 안쪽으로(역할 코드 재유출 차단 · 진단 보존).
  const why = DEADMAN_AXIS[axis] ?? "응답이 없습니다";
  const act = DEADMAN_NO_WINDOW.has(axis) ? "상단 「↻ 재시작」을 누르면 창을 다시 세웁니다." : CHECK;
  return {
    title: `🚨 ${friendlyRole(role)} 창 응답 없음`,
    body: `${seatName(no, role, p.dept)} — ${why}. ${act}`,
    raw: p.reason ? String(p.reason) : undefined,
  };
}

export function roleTakeoverCopy(prevNo: number | null, p: Record<string, unknown>): AlertCopy {
  const name = typeof p.role === "string" && p.role ? friendlyRole(p.role) : "도우미";
  // (agy 4R MINOR 수용) 부서 이벤트면 부서 이름 접두 — 다른 경보와 같은 seatName.
  const prev = prevNo != null ? seatName(prevNo, null, p.dept) : "옛 창";
  return {
    title: `ℹ ${name} 자리가 다른 창으로 옮겨졌습니다`,
    // ★(v116-integ · master#24673176) 꼬리 문장 묶음은 데몬 화면 고지(cysd handlers.rs seat_takeover_notice)와
    //   **같은 말**이어야 한다 — cysd 시험 v115_seat_takeover_notice_is_screen_output_not_shell_input 이 이 파일을 핀한다.
    body: `${prev}이 비어 있어 이 역할을 새 창으로 옮겨 붙였습니다. 옛 창은 곧 정리됩니다. 전할 말이 남아 있으면 그대로 둡니다.`,
  };
}

export function seatFolderDeniedCopy(no: number | null, p: Record<string, unknown>, folderName: string): AlertCopy {
  const cwd = String(p.cwd ?? "").trim();
  return {
    title: "⚠ 부서 폴더 접근 권한이 꺼져 있습니다",
    body: `${seatName(no, p.role, p.dept)}이 ${cwd ? `${cwd} ` : "작업 "}폴더를 열지 못해 AI가 시작되지 않았습니다. 시스템 설정 → 개인정보 보호 및 보안 → 파일 및 폴더 → cysr 에서 「${folderName} 폴더」를 켠 뒤 앱을 재시작하세요.`,
  };
}
