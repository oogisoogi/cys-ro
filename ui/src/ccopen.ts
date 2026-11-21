// (TICKET=cysr-1116-cc-autoopen-1120) Control Center 를 **여는 원인**의 단일 정의처 — 순수 판정자(main.ts 는 배선만 한다).
//
// 박사님 원칙(11-20): 「콘트롤 센터를 볼 일도, 그곳에서 처리할 일도 없다. 긴급할 경우를 제외하고는 보게 할 일이 없게」.
//   = 승인 UX 의 「알림과 포커스 강탈의 분리」. 사람이 누르지 않았는데 CC 가 저절로 열리는 것은
//     **사람이 꼭 봐야 하는 긴급**(approval.stalled — 데몬이 승인 방치 5분을 판정한 신호)일 때뿐이다.
//   그 밖의 데몬 출처 계기는 토스트·배지로만 알리고 화면을 빼앗지 않는다.
//
// 원인 표(이 표에 없는 원인으로 CC 를 열 수 없다 — ccopen.test.ts 가 main.ts 의 모든 열기 호출을 이 표와 대조한다):
//   user.*            사람이 누른 것(상단 단추·화면 설정·팔레트·사이드바 「승인 요청 N」) → 연다
//   approval.stalled  승인 방치 5분(사람 개입 필요 · 데몬 판정) → 저절로 연다(유일한 자동 열기)
//   ui.open_panel     `cys open-control-center` = 말로 열기(사람 CLI 또는 master 좌석만 · 데몬 게이트) → 연다(명시 요청)
//   feed.grace        `feed.item.created` 뒤 30초/90초 유예가 지나도 pending → **열지 않는다**(알림만 · 로그 1줄)
//     근거: 그 항목(`cys feed push --wait`)의 결재자는 master 다(워커 지침 §7) — 박사님은 결재자가 아니다.
//           30초 미결은 긴급이 아니라 master 가 아직 안 본 것이고, 생성 토스트·승인 대기 배지가 이미 알린다.
//           사람 소환은 데몬 판정(approval.stalled · 5분)의 몫이다.

export const CC_OPEN_CAUSES = {
  "user.button": "open", // 상단 「Control Center」 단추(btn-cc)
  "user.theme_pop": "open", // 화면 설정 팝오버의 「컨트롤 센터 열기」
  "user.palette": "open", // 커맨드 팔레트 「Control Center 토글」·「승인 Feed 탭 열기」
  "user.board_approvals": "open", // 사이드바 상태판의 「승인 요청 N」 단추
  "approval.stalled": "open", // 데몬 승인 방치 판정 — 유일한 자동 열기
  "ui.open_panel": "open", // `cys open-control-center`(말로 열기 · 데몬 호출자 게이트)
  "feed.grace": "notify", // feed 유예 만료 — 포커스 강탈 0
} as const satisfies Record<string, "open" | "notify">;

export type CcOpenCause = keyof typeof CC_OPEN_CAUSES;
export type CcOpenVerdict = "open" | "notify";

/** 이 원인이 CC 를 열어도 되는가. 표에 없는 값(타입 밖 문자열)은 열지 않는다(fail-closed — 모르는 계기가 화면을 빼앗지 않게). */
export function ccOpenVerdict(cause: string): CcOpenVerdict {
  return Object.prototype.hasOwnProperty.call(CC_OPEN_CAUSES, cause) ? CC_OPEN_CAUSES[cause as CcOpenCause] : "notify";
}

/** 저절로(사람 입력 없이) 연 원인인가 — 로그 줄의 머리표에 쓴다. */
export function ccOpenIsAuto(cause: string): boolean {
  return !cause.startsWith("user.");
}

/**
 * 앱 로그 한 줄(관측 장치) — CC 가 열린 순간(닫힘→열림 전이)과 열기를 막은 순간마다 한 줄.
 * 다음에 또 「저절로 떴다」 하면 이 줄의 원인 칸이 답한다. 열려 있던 것을 다시 여는 것은 전이가 아니라 null.
 * 형식: `<로컬 ISO 시각> cc-open <auto|user> <opened|suppressed> cause=<원인>[ detail=<부가>]`
 */
export function ccOpenLogLine(
  o: { wasOpen: boolean; cause: string; opened: boolean; detail?: string },
  now: Date,
): string | null {
  if (o.opened && o.wasOpen) return null; // 이미 열려 있었다 — 전이 아님
  const p = (x: number, n = 2) => String(x).padStart(n, "0");
  const off = -now.getTimezoneOffset();
  const tz = `${off >= 0 ? "+" : "-"}${p(Math.floor(Math.abs(off) / 60))}${p(Math.abs(off) % 60)}`;
  const ts = `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}T${p(now.getHours())}:${p(now.getMinutes())}:${p(now.getSeconds())}.${p(now.getMilliseconds(), 3)}${tz}`;
  const clean = (s: string) => s.replace(/[\r\n\t ]+/g, "_").slice(0, 120);
  const detail = o.detail ? ` detail=${clean(o.detail)}` : "";
  return `${ts} cc-open ${ccOpenIsAuto(o.cause) ? "auto" : "user"} ${o.opened ? "opened" : "suppressed"} cause=${clean(o.cause)}${detail}`;
}
