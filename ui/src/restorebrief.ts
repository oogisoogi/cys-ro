// 복원 브리핑 카드(1단계) — 순수 모듈. DOM·Tauri 0줄(유닛 테스트가 이 파일을 그대로 부른다).
//
// 박사님 채택(2026-09-17 22:3x) 1단계 계약:
//   · 작업기억 파일(SESSION_STATE.md)의 고정 3절(완료 / 진행 중 / 결정 필요) + 복원 결과 + 기록 시각을
//     **프로그램이** 조립한다 — 모델 호출 0(토큰 0).
//   · 마스터 자리 1곳에만 띄운다. ★묻지 않는다(박사님 최상위 원칙 2026-09-21: 「중간에 사용자에게 묻는
//     단계를 모두 삭제하면 좋다」) — 카드는 **알림 1장**이고 버튼은 [닫기] 하나다. 종전의
//     「이어서 진행할까요?」 버튼(누르면 마스터에 한 줄 주입)은 제거했다. 이어서 할지 말지는 마스터가
//     **임무 게이트**(오너 임무 대장)로 판정한다 — 사람에게 되묻지 않고, 사용자의 클릭이 자율 착수
//     권한을 여는 경로도 없앴다(그 경로가 09-21 실기에서 임무 0 함대를 폭주시킨 방아쇠다).
//   · 복원 직후 컨텍스트가 60%를 넘은 자리는 **권유 한 줄**만 얹는다(자동 순환 집행 0 — 알림이지 질문이 아니다).
//   · 문구는 처음 쓰는 사람이 읽는다 — 내부 용어(파일명·역할 코드명·surface·phoenix 등)를 화면에 내지 않는다.
// 2단계(예 뒤 마스터 상세 브리핑)와 저장 훅의 3절 서식 검사는 이 모듈 범위 밖이다.

export interface BriefSections {
  done: string[];
  doing: string[];
  decide: string[];
}

/** 절 하나에서 보여 줄 최대 줄 수 · 한 줄 최대 글자 수(카드가 화면을 덮지 않게). */
export const BRIEF_MAX_ITEMS = 5;
export const BRIEF_MAX_CHARS = 80;

const HEADS: [keyof BriefSections, RegExp][] = [
  ["done", /^#{1,6}\s*(?:[^\p{L}\p{N}\s]+\s*)?완료/u],
  ["doing", /^#{1,6}\s*(?:[^\p{L}\p{N}\s]+\s*)?진행\s*중/u],
  ["decide", /^#{1,6}\s*(?:[^\p{L}\p{N}\s]+\s*)?결정\s*필요/u],
];

/** 마크다운 꾸밈을 걷고 길이를 자른다(굵게·코드·링크 표기는 초보자에게 잡음이다). */
export function plainLine(s: string): string {
  let t = s
    .replace(/^\s*(?:[-*+]|\d+[.)])\s+/, "")
    .replace(/^\[[ xX]\]\s*/, "")
    .replace(/\*\*|__|`/g, "")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[\[([^\]]*)\]\]/g, "$1")
    .trim();
  if ([...t].length > BRIEF_MAX_CHARS) t = [...t].slice(0, BRIEF_MAX_CHARS - 1).join("") + "…";
  return t;
}

/** 고정 3절을 뽑는다. 절 제목이 없으면 그 절은 빈 배열(지어내지 않는다). */
export function parseBriefSections(text: string): BriefSections {
  const out: BriefSections = { done: [], doing: [], decide: [] };
  let cur: keyof BriefSections | null = null;
  for (const raw of text.split(/\r?\n/)) {
    if (/^#{1,6}\s/.test(raw)) {
      const hit = HEADS.find(([, re]) => re.test(raw));
      cur = hit ? hit[0] : null;
      continue;
    }
    if (!cur) continue;
    if (!/^\s*(?:[-*+]|\d+[.)])\s+\S/.test(raw)) continue; // 목록 줄만(설명 문단은 카드에 싣지 않는다)
    if (/^\s{2,}/.test(raw)) continue; // 하위 항목은 뺀다(한눈 요지)
    if (out[cur].length >= BRIEF_MAX_ITEMS) continue;
    const line = plainLine(raw);
    if (line) out[cur].push(line);
  }
  return out;
}

/** 기록 시각 — 파일 안에 적힌 가장 늦은 「YYYY-MM-DD HH:MM」(없으면 날짜만, 그것도 없으면 null). */
export function recordedAt(text: string): string | null {
  const full = [...text.matchAll(/(20\d{2}-\d{2}-\d{2})[T ](\d{2}:\d{2})/g)].map((m) => `${m[1]} ${m[2]}`);
  if (full.length) return full.sort().at(-1) ?? null;
  const d = [...text.matchAll(/(20\d{2}-\d{2}-\d{2})/g)].map((m) => m[1]);
  return d.length ? (d.sort().at(-1) ?? null) : null;
}

/** 작업기억 파일 후보 경로 — 마스터 작업 폴더에서 위로 올라가되 홈 폴더를 넘지 않는다. */
export function stateCandidates(cwd: string | null | undefined, home: string): string[] {
  if (!cwd) return [];
  const sep = cwd.includes("\\") && !cwd.includes("/") ? "\\" : "/";
  const norm = (p: string) => p.replace(/[\\/]+$/, "");
  const h = norm(home);
  let d = norm(cwd);
  const out: string[] = [];
  for (let i = 0; i < 8 && d; i++) {
    out.push(`${d}${sep}_round${sep}SESSION_STATE.md`);
    if (d === h || d.length <= h.length) break;
    const cut = d.lastIndexOf(sep);
    if (cut <= 0) break;
    d = d.slice(0, cut);
  }
  return out;
}

/** 역할 코드명 → 처음 쓰는 사람이 읽는 이름. 모르는 역할은 「도우미」로 뭉친다(코드명을 내지 않는다). */
export function friendlyRole(role: string): string {
  if (role === "master") return "총괄";
  if (role === "cso") return "운영 관리";
  if (role.startsWith("worker")) return "작업";
  if (role.startsWith("reviewer")) return "검토";
  return "도우미";
}

/** 복원 직후 「순환을 권해요」를 얹는 문턱(%) — 워커 규율(60% 매듭)과 같은 수다. */
export const CYCLE_ADVICE_PCT = 60;

/**
 * 컨텍스트가 문턱을 넘은 자리에 붙일 권유 줄. **권유일 뿐 집행하지 않는다**(자동 순환 0).
 * `ctxPct=null`(아직 못 잰 자리)은 넘었다고 말하지 않는다 — 모르는 것을 단정하지 않는다.
 */
export function cycleAdviceLines(seats: { role: string; ctxPct: number | null }[]): string[] {
  const hot = seats.filter((s) => typeof s.ctxPct === "number" && (s.ctxPct as number) >= CYCLE_ADVICE_PCT);
  if (!hot.length) return [];
  const names = [...new Set(hot.map((s) => friendlyRole(s.role)))].join(" · ");
  return [`${names} 창은 기억한 내용이 ${CYCLE_ADVICE_PCT}%를 넘었어요. 한 번 정리(순환)를 권해요.`];
}

export interface BriefCard {
  title: string;
  lines: { head: string; items: string[] }[];
  foot: string;
  closeLabel: string;
}

/**
 * 카드 내용을 조립한다. `sections=null` = 작업기억 파일을 못 찾았다(지어내지 않고 그렇다고 말한다).
 * `restoredRoles` = 지금 살아 있는 역할 자리 · `waitingRoles` = 자리는 있는데 아직 켜지지 않은 역할.
 */
export function buildBriefCard(input: {
  sections: BriefSections | null;
  recordedAt: string | null;
  restoredRoles: string[];
  waitingRoles: string[];
  /** 자리별 컨텍스트 사용률(모르면 null) — 60%+ 자리에 순환 권유 한 줄을 얹는다(집행 0). */
  seatCtx?: { role: string; ctxPct: number | null }[];
}): BriefCard {
  const uniq = (xs: string[]) => [...new Set(xs.map(friendlyRole))];
  const back = uniq(input.restoredRoles);
  const wait = uniq(input.waitingRoles).filter((r) => !back.includes(r));
  const lines: BriefCard["lines"] = [];
  lines.push({
    head: "다시 켜진 창",
    items: [
      back.length ? `${back.join(" · ")} 창이 다시 켜졌습니다.` : "다시 켜진 창이 아직 없습니다.",
      ...(wait.length ? [`${wait.join(" · ")} 창은 아직 켜지는 중입니다. 잠시 뒤 저절로 붙습니다.`] : []),
      ...cycleAdviceLines(input.seatCtx ?? []),
    ],
  });
  if (input.sections) {
    const s = input.sections;
    const none = "적힌 것이 없습니다.";
    lines.push({ head: "끝난 일", items: s.done.length ? s.done : [none] });
    lines.push({ head: "하던 일", items: s.doing.length ? s.doing : [none] });
    lines.push({ head: "정하셔야 할 일", items: s.decide.length ? s.decide : [none] });
  } else {
    lines.push({ head: "지난 작업 기록", items: ["정리된 작업 기록을 찾지 못했습니다."] });
  }
  const foot = input.recordedAt
    ? `이 기록은 ${input.recordedAt} 기준입니다. 그 뒤에 한 일은 빠져 있을 수 있습니다.`
    : "기록한 시각을 알 수 없습니다. 최근 일이 빠져 있을 수 있습니다.";
  return {
    // ★질문이 아니라 알림이다 — 물음표를 쓰지 않는다(묻는 단계 삭제 원칙).
    title: "다시 켜졌어요 — 하던 일을 복원했어요",
    lines,
    foot,
    closeLabel: "닫기",
  };
}

/** 화면에 내면 안 되는 내부 용어(테스트가 카드 전문에 대해 0건을 단언한다). */
export const INTERNAL_TERMS = [
  "SESSION_STATE", "surface", "phoenix", "master", "cso", "worker", "reviewer",
  "pane", "socket", "daemon", "데몬", "소켓", "세션", "jsonl", "_round",
];
