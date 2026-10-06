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

/** 제어문자·줄/문단 나눔·방향 바꿈 글자가 있으면 null(allowNewline 이 참일 때만 줄바꿈 허용 — 지금 호출부는 전부 거짓 = 한 줄). */
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
  const body = cleanText(o.body, false); // 알림 1줄(설계 §6-1 · 2판 codex 1R ⑥ — 노트도 같은 줄에 붙는다)
  if (resultId === null || title === null || body === null) return null;
  return { toastId, resultId, title, body };
}

/** 📌18 고정 안내 재조회 간격 — 창이 열린 채(포커스·보임 유지) 러너가 `seats_blocked` 를 지워도 안내가 사라지게 하는 저율 폴링(codex 1R ②).
 *  조회 1번 = 상태 폴더 파일 하나 읽기라 CPU·토큰 비용은 0 에 가깝다. 30초 이상이어야 한다(시험이 하한을 잰다). */
export const SEATS_NOTE_POLL_MS = 60_000;

/** 겹친 조회의 **역순 응답을 버린다** — 가장 나중에 시작한 조회의 결과만 `apply` 한다(세대 번호). 조회가 던지면 아무것도 바꾸지 않는다.
 *  예: 「차단됨」을 묻는 느린 옛 조회가 「풀림」을 받은 새 조회보다 늦게 끝나도 안내를 되살리지 않는다(codex 1R ②). */
export function latestOnly<T>(fetch: () => Promise<T>, apply: (v: T) => void): () => Promise<void> {
  let gen = 0;
  return async () => {
    const mine = ++gen;
    let v: T;
    try {
      v = await fetch();
    } catch {
      return;
    }
    if (mine !== gen) return;
    apply(v);
  };
}

/** `update_seats_blocked_notice` 응답 → 창 고정 안내 문구(📌18) 또는 null(안내 없음). */
export function seatsBlockedText(v: unknown): string | null {
  return cleanText(v, false);
}
