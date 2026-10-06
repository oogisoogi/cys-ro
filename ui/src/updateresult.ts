// ui/src/updateresult.ts — 자동 갱신 결과 알림의 응답 해석(순수 도우미 · 1.1.8 U4 · 설계 AUTO-UPDATE-118 §3-12 · 📌18).
//
// 1.1.8 부터 앱에는 「업데이트」 단추·배지·확인 창이 없다(§5-1 — 사용자가 누르는 갱신 단추 0). 갱신은 데몬이 쉬는 시간에 알아서 하고,
// 앱은 그 **결과**를 다음 창에서 토스트 1개로 알리기만 한다. 판정·장부 기록(①② 표시 전 기록 · ④ 닫기)은 백엔드
// (`src-tauri/src/updnotice.rs`)가 하고, 이 모듈은 백엔드 응답의 모양을 의심해 화면에 올릴 값만 골라낸다.
// ★응답은 신뢰하지 않는다 — 토스트 id 는 아래 두 값만 받고(다른 id 로 남의 토스트를 덮지 않게), 문자열은 제어문자가 있으면 통째로 버린다.
//   렌더는 main.ts 가 stickyToast(textContent) 로만 한다(HTML 삽입 없음).
//
// ★이 모듈의 불변식(updateresult.test.ts 가 핀으로 고정 — starvednotice.ts 와 같다):
//   · 최상위 부수효과 0 — 선언(export/const/function/interface/type)만. main.js 는 번들 하나라 여기서 평가 중 예외가 나면 앱 전체가 백지가 된다.

/** 결과 알림 토스트 id(성공·롤백·설치판 폐기) — 기본 수명. 값은 updnotice.rs 의 TOAST_ID_RESULT 와 같다. */
export const UPDATE_RESULT_TOAST_ID = "update-result";
/** 롤백 실패 토스트 id — 안내용 수명(10분)·만료 배너(toastttl.ts 정확 일치 목록). 값은 updnotice.rs 의 TOAST_ID_ROLLBACK_FAILED 와 같다. */
export const UPDATE_ROLLBACK_FAILED_TOAST_ID = "update-rollback-failed";

/** 화면에 올릴 결과 알림 한 건. */
export interface ResultNotice {
  toastId: string;
  resultId: string;
  title: string;
  body: string;
}

const MAX_TEXT = 600;

/** 제어문자(줄바꿈 제외)·줄/문단 나눔·방향 바꿈 글자가 있으면 거짓. 본문의 줄바꿈 1개(릴리스 노트 둘째 줄)는 허용한다. */
function cleanText(v: unknown, allowNewline: boolean): string | null {
  if (typeof v !== "string" || v.length === 0 || v.length > MAX_TEXT) return null;
  for (let i = 0; i < v.length; i++) {
    const c = v.charCodeAt(i);
    if (c === 10 && allowNewline) continue;
    if (c < 32 || (c >= 127 && c <= 159)) return null;
    if (c === 0x2028 || c === 0x2029 || c === 0x200e || c === 0x200f || c === 0x061c) return null;
    if ((c >= 0x202a && c <= 0x202e) || (c >= 0x2066 && c <= 0x2069)) return null;
  }
  return v;
}

/** `update_result_notice` 응답 → 알림 1건(모양이 틀리면 null = 아무것도 띄우지 않는다). */
export function parseResultNotice(v: unknown): ResultNotice | null {
  if (typeof v !== "object" || v === null) return null;
  const o = v as Record<string, unknown>;
  const toastId = o.toast_id;
  if (toastId !== UPDATE_RESULT_TOAST_ID && toastId !== UPDATE_ROLLBACK_FAILED_TOAST_ID) return null;
  const resultId = typeof o.result_id === "string" && /^[A-Za-z0-9._:-]{1,64}$/.test(o.result_id) ? o.result_id : null;
  const title = cleanText(o.title, false);
  const body = cleanText(o.body, true);
  if (resultId === null || title === null || body === null) return null;
  return { toastId, resultId, title, body };
}

/** `update_seats_blocked_notice` 응답 → 창 고정 안내 문구(📌18) 또는 null(안내 없음). */
export function seatsBlockedText(v: unknown): string | null {
  return cleanText(v, false);
}
