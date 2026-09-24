// 창 닫기 보호 — 산 창을 상단 「Close」·⌘W·팔레트 「패널 닫기」로 닫을 때 확인 1회를 띄울지의 **판정부**
// (TICKET=v116-ui-close · 박사님 09-23 「exited 페인 닫다가 실수로 작업 중 페인을 닫았다」 · D4 #7).
//
// ★왜 순수 모듈인가: 「exited 창은 묻지 않고, 산 창은 묻는다」는 화면을 열어 봐야 아는 사실이 아니라
//   판정 한 줄이다. main.ts 안에 두면 그 한 줄을 기계가 잴 수 없고, 조건이 조용히 뒤집혀도(모든 창을
//   묻지 않게 되거나 exited 창까지 묻게 되거나) 아무 시험도 빨개지지 않는다.
//
// ★정책·문안을 여기 한 곳에 모은 이유: 확인 창의 모양은 박사님 결정 A-1(PLAN-1.1.6 §5)의 답이
//   규격이다. 답이 오기 전엔 권고안 A(산 창만 확인 1회 · exited 창은 즉시)로 구현하고, 답이 B(모든 창
//   확인)로 오면 `CLOSE_CONFIRM_POLICY` 한 줄만 바꾼다. 문안도 이 파일만 고치면 된다.
//
// ★창 머리 × 는 이 판정을 쓰지 않는다 — × 는 이미 「두 번 눌러야 닫힘」이고 브리프가 무변경을 요구한다.

/** 확인 정책. "live-only" = 산 창만 묻는다(권고 A) · "all" = exited 창까지 모두 묻는다(B). */
export type CloseConfirmPolicy = "live-only" | "all";
export const CLOSE_CONFIRM_POLICY: CloseConfirmPolicy = "live-only";

/**
 * 확인 창 문안 — 공개 문구 규율(왕초보 말투 · 위협 표현 0 · 내부 용어 0).
 * `{name}` 자리에 화면에 보이는 창 이름이 들어간다(어느 창을 닫는지 사람이 알아야 고를 수 있다).
 */
export const CLOSE_CONFIRM_TEXT = {
  title: "이 창을 닫을까요?",
  body: "「{name}」 창은 아직 켜져 있어요.\n닫으면 이 창에서 하던 일이 멈춰요.",
  yes: "닫기",
  no: "취소",
} as const;

/** 확인 창 본문에 싣는 창 이름의 최대 글자 수(긴 경로 제목이 창을 밀어내지 않게). */
export const CLOSE_NAME_MAX = 40;

/**
 * 이 창을 닫기 전에 물어야 하는가.
 *
 * `exited` = 데몬이 이 창의 셸이 끝났다고 **확정**했는가. `true` 일 때만 묻지 않는다.
 * `false`(살아 있음)와 `null`(모름 — 아직 목록을 못 받은 창 등)은 둘 다 **묻는다**: 모르는 창을
 * 묻지 않고 닫으면 실패 방향이 「작업 중인 창이 사라진다」이고, 묻고 닫으면 실패 방향이 「한 번 더
 * 누른다」다. 안전한 쪽으로 틀린다.
 */
export function needsCloseConfirm(policy: CloseConfirmPolicy, exited: boolean | null): boolean {
  if (policy === "all") return true;
  return exited !== true;
}

/** 확인 창 본문 — 창 이름을 넣고 길면 자른다. 이름이 비면 「이 창」으로 말한다. */
export function closeConfirmBody(name: string | null | undefined): string {
  let n = (name ?? "").trim();
  if (!n) return CLOSE_CONFIRM_TEXT.body.replace("「{name}」 창은", "이 창은");
  if ([...n].length > CLOSE_NAME_MAX) n = [...n].slice(0, CLOSE_NAME_MAX - 1).join("") + "…";
  return CLOSE_CONFIRM_TEXT.body.replace("{name}", n);
}
