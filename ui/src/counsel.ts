// 「자동 보고」(1.1.10 · TICKET=cysr-1110-counsel-off → 1.1.19 · cysr-1119-s10b AG4·AG5)의 순수 로직 — DOM·Tauri 0 · main.ts 가 배선만 한다.
// ★(1.1.19) 「상담소」 창·글 목록·45초 배지·「아고라」 단추의 순수 로직(COUNSEL_COPY·AGORA_COPY·buildCounselView·parseUnread …)은 화면과 함께 뺐다.
//   남은 것 = 개인정보 안내문(REPORT_NOTICE · 팩 HELP_NOTICE 와 같은 바이트) · 켜기/끄기 글(AUTO_COPY) · 상태 판독 넷.

// ── 「상담소 끄기/켜기」·첫 안내(1.1.10 · TICKET=cysr-1110-counsel-off) ─────────────────────
/** 첫 안내 문구 — 박사님 승인 문구(2026-10-22)를 실제로 보내는 칸에 맞춰 고친 글(2026-11-12 「7번 권고대로」 · TICKET=cysr-counsel-notice).
 *  팩 `javis_counsel.py` HELP_NOTICE 와 글자 그대로 같다(시험이 대조) · 보내는 칸 ↔ 이 글의 말 = 팩 HELP_SENT_FIELDS(시험이 대조). */
export const REPORT_NOTICE =
  "cysr는 문제를 빨리 찾아 고치기 위해 하루 한 번 기기 상태(판 번호·운영체제·좌석 수와 종류·부서 수·cysr를 켜 둔 시간)와 " +
  "오류 기록(횟수·종류·생긴 시각·점검 결과와 항목 이름)을 개발팀에 보냅니다. " +
  "기기를 구분하는 무작위 번호가 함께 갑니다(사람 이름·파일·대화 내용은 보내지 않습니다). " +
  "끄려면 화면 설정 → ‘자동 보고’를 끄세요.";

// ★(cysr-1119-s10b AG5n · DESIGN §8-3-1 · D-03) 1.1.19 = 「상담소」 단추가 없어지고 「자동 보고」 켜기/끄기가 화면 설정 한 줄로 옮겨 갔다 —
//   안내문 끝 문장·창 제목·두 단추 이름·꺼짐 안내를 그 자리 이름에 맞췄다(팩 NOTICE_VERSION 3 → 판 2 를 본 미가입 기기에 한 번 더 뜬다).
export const AUTO_COPY = {
  noticeTitle: "자동 보고 안내",
  ok: "확인",
  turnOff: "자동 보고 끄기",
  turnOn: "자동 보고 켜기",
  on: "자동 보고: 켜짐",
  off: "자동 보고: 꺼짐",
  unknown: "자동 보고 상태를 확인하지 못했어요.",
  busy: "바꾸는 중이에요…",
  notTurnedOn: "지금은 켜지 못했어요. 잠시 뒤 다시 눌러 주세요.",
  offNotice: "지금은 보내지 않습니다. 다시 켜려면 화면 설정 → ‘자동 보고’를 켜세요.",
} as const;

/** Rust `counsel_auto_status`·`counsel_auto_set` 결과 판독 — auto 가 참/거짓이 아니면 모름(null). 안내 = 켜짐이고 팩이 원할 때만. */
export type AutoStatus = { auto: boolean | null; needsNotice: boolean };
export function parseAutoStatus(res: unknown): AutoStatus {
  const r = (res && typeof res === "object" ? res : {}) as Record<string, unknown>;
  const auto = typeof r.auto === "boolean" ? r.auto : null;
  return { auto, needsNotice: auto === true && r.needs_notice === true };
}

export function autoLine(auto: boolean | null): string {
  return auto === true ? AUTO_COPY.on : auto === false ? AUTO_COPY.off : AUTO_COPY.unknown;
}

/** 단추 아래 안내문 — 꺼짐일 때만 「다시 켜려면」(master#5a04ba60 · cysr-1110-visual 눈 검수) · 켜짐·모름 = 승인 문구 그대로. */
export function autoNotice(auto: boolean | null): string {
  return auto === false ? AUTO_COPY.offNotice : REPORT_NOTICE;
}

/** 단추 = 지금 상태의 반대 · 모를 때는 끄기(보내지 않는 쪽). */
export function autoToggle(auto: boolean | null): { label: string; next: boolean } {
  return auto === false ? { label: AUTO_COPY.turnOn, next: true } : { label: AUTO_COPY.turnOff, next: false };
}
