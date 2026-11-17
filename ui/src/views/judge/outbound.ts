// (cysr-ui-slice1) 보내기 전 글 다듬기 — 순수(P2-DESIGN §2-5 composeOutbound · F12 순서).
//
// ① 살균 = pastesafe 규칙(C0·DEL·C1 → 공백 · 탭·줄바꿈 유지 · ESC 도 지워져 울타리 표지 위조 불가) — CR/CRLF 는 먼저 LF 로
// ② 앞 공백 제거(뒤 공백·뒤 빈 줄도 제거 — 세션 기록 전문 대조를 같은 글로 하려고)
// ③ 비면 막음 ④ 맨 앞 `/`·`!` 면 막음(Claude Code 명령·셸 실행) ⑤ 둘째 줄 이하 맨 앞 `/` = U21 측정 대기 → 보수 기본값 = 막음.
// 데몬도 clear_first 본문을 같은 규칙(paste_fence::sanitize_owned)으로 한 번 더 살균한다 — 여기서 먼저 하는 까닭은
// 화면이 「무엇을 보냈는지」를 바이트로 알아야 세션 기록과 전문 대조(§5-2 「틀림 0」)를 할 수 있어서다.

import { sanitizePaste } from "../../pastesafe";

/** U21(둘째 줄 이하 맨 앞 `/` 가 명령으로 실행되는가) — **측정 대기**(조각 0.5 M6 은 보내는 쪽 바이트만 · 받는 쪽은 진짜 Claude 필요).
 *  값이 오면 이 상수만 바꾼다: true = 울타리 안이라 명령 아님(보냄) · false = 못 믿음(막음 · 지금 기본값). */
export const U21_LATER_LINE_SLASH_SAFE: boolean = false;

export type Outbound =
  | { ok: true; text: string }
  | { ok: false; code: "empty" | "leading_command" | "later_line_slash"; msg: string };

export function composeOutbound(raw: string, laterSlashSafe: boolean = U21_LATER_LINE_SLASH_SAFE): Outbound {
  const unixed = raw.replace(/\r\n?/g, "\n");
  const clean = sanitizePaste(unixed).replace(/^\s+/, "").replace(/\s+$/, "");
  if (clean.length === 0) return { ok: false, code: "empty", msg: "보낼 말을 적어 주세요." };
  if (clean[0] === "/" || clean[0] === "!")
    return { ok: false, code: "leading_command", msg: "「/」나 「!」로 시작하는 말은 명령이라 대화 화면에서 보내지 않아요. 작업 화면의 마스터 창에서 쳐 주세요." };
  if (!laterSlashSafe && clean.split("\n").slice(1).some((l) => l.replace(/^[ \t]+/, "").startsWith("/")))
    return { ok: false, code: "later_line_slash", msg: "둘째 줄부터 「/」로 시작하는 줄이 있으면 아직 보내지 않아요(안전 확인 중). 그 줄 앞에 글자를 하나 넣어 주세요." };
  return { ok: true, text: clean };
}
