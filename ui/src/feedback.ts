// 사이드바 「피드백」 창의 순수 로직(TICKET=cys-feedback-menu · 2026-09-15). DOM 배선은 main.ts 가 한다.
// 전송·보관함·재시도는 Rust(src-tauri/src/feedback.rs)가 맡는다 — 서버 칸 이름은 그쪽 한 곳에만 있다.

// 고지 정본 = 도움 서버 FEEDBACK_NOTICE_TEXT(박사님 확정 2026-09-15 18:1x · 726 제안문 그대로 · 보존 90일).
// 문안·기간이 바뀌면 서버 상수와 **이 한 줄**을 같은 날 바꾼다(feedback.test.ts 가 글자 그대로 대조한다).
export const FEEDBACK_NOTICE_TEXT =
  "보내 주신 제목·내용과 사진·영상은 자비스 설치와 사용을 고치는 데만 씁니다. 제목·내용 속 이메일·집 폴더 경로·토큰은 저장하기 전에 지우고, 연락처 칸(적지 않아도 됩니다)은 답을 드리려고 받은 그대로 둡니다. 앱이나 설치 도우미에서 보내면 설치 번호와 판본도 함께 갑니다. 사진·영상은 지울 수 없어 운영팀만 보며, 모두 받은 날로부터 90일 뒤 저절로 지워집니다.";

// 한도 = 서버 HELP-API §11-2·11-3 바이트 값 그대로(딱 그 크기는 받는다). Rust feedback.rs 에도 같은 값 —
// 시험 limits_match_ui_module 이 대조한다.
export const TITLE_MAX = 120;
export const BODY_MAX = 5000;
export const CONTACT_MAX = 200;
export const PHOTO_MAX_BYTES = 5_242_880;
export const PHOTO_MAX_COUNT = 5;
export const VIDEO_MAX_BYTES = 95_000_000;
export const VIDEO_MAX_COUNT = 1;

// 서버는 앞 바이트로 형식을 판별한다(사진 jpeg·png·webp·heic / 영상 mp4·mov·webm) — 창도 같은 목록만 고르게 한다.
export const PHOTO_EXTS = ["jpg", "jpeg", "png", "webp", "heic", "heif"];
export const VIDEO_EXTS = ["mp4", "m4v", "mov", "webm"];
export const ACCEPT_ATTR = [...PHOTO_EXTS, ...VIDEO_EXTS].map((e) => "." + e).join(",");

export type Kind = "photo" | "video";
export interface Attached {
  kind: Kind;
  file: string; // 보관함 안 저장 이름(photo-1.png 등)
  name: string; // 사용자가 고른 원래 이름(화면 캡처는 「화면 캡처」)
  bytes: number;
}

/** 글자 수는 코드 포인트로 센다(서버·Rust 와 같은 단위 — 한글·이모지를 UTF-16 길이로 세면 어긋난다). */
export function charCount(s: string): number {
  return Array.from(s).length;
}

/** 확장자 기준 판별 — HEIC 는 WebView 가 MIME 을 비워 주는 일이 잦아 MIME 을 믿지 않는다. */
export function attachmentKind(name: string): Kind | null {
  const m = /\.([A-Za-z0-9]+)$/.exec(name);
  const ext = m ? m[1].toLowerCase() : "";
  if (PHOTO_EXTS.includes(ext)) return "photo";
  if (VIDEO_EXTS.includes(ext)) return "video";
  return null;
}

/** 입력 글 검사 — 보내기 전에 창이 먼저 막는다. 빈 배열 = 통과. */
export function validateText(title: string, body: string, contact: string): string[] {
  const errs: string[] = [];
  const t = title.trim();
  const b = body.trim();
  if (!t) errs.push("제목을 적어 주세요.");
  else if (charCount(t) > TITLE_MAX) errs.push(`제목은 ${TITLE_MAX}자까지입니다.`);
  if (!b) errs.push("내용을 적어 주세요.");
  else if (charCount(b) > BODY_MAX) errs.push(`내용은 ${BODY_MAX}자까지입니다.`);
  if (charCount(contact.trim()) > CONTACT_MAX) errs.push(`연락처는 ${CONTACT_MAX}자까지입니다.`);
  return errs;
}

/** 첨부 한 건을 더할 수 있는지(화면 캡처도 사진 5장 안에서 센다). null = 가능, 글 = 막는 이유. */
export function attachBlockReason(existing: Attached[], kind: Kind, bytes: number): string | null {
  const count = existing.filter((a) => a.kind === kind).length;
  if (bytes <= 0) return "빈 파일은 붙일 수 없습니다.";
  if (kind === "photo") {
    if (count >= PHOTO_MAX_COUNT) return `사진은 ${PHOTO_MAX_COUNT}장까지입니다(화면 캡처 포함).`;
    if (bytes > PHOTO_MAX_BYTES) return "사진 한 장은 5MB까지입니다.";
  } else {
    if (count >= VIDEO_MAX_COUNT) return `영상은 ${VIDEO_MAX_COUNT}개까지입니다.`;
    if (bytes > VIDEO_MAX_BYTES) return "영상은 95MB까지입니다.";
  }
  return null;
}

export function formatBytes(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}MB`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}KB`;
  return `${n}B`;
}

const ERROR_TEXT: Record<string, string> = {
  invalid_title: "제목을 확인해 주세요.",
  invalid_body: "내용을 확인해 주세요.",
  invalid_contact: "연락처를 확인해 주세요.",
  too_large: "보내는 글이 너무 깁니다.",
  file_cap: "첨부 수가 한도를 넘었습니다.",
  file_too_large: "첨부 파일이 한도보다 큽니다.",
  unsupported_type: "보낼 수 없는 파일 형식입니다.",
  storage_full: "지금은 첨부를 더 받을 수 없습니다.",
  upload_window_closed: "올릴 수 있는 시간이 지났습니다.",
};

export function errorText(code: string): string {
  const key = code.split(" ").pop() ?? code;
  return ERROR_TEXT[key] ?? "보내지 못했습니다.";
}

export interface SubmitResult {
  state: "sent" | "queued" | "rejected";
  id?: string;
  error?: string;
  dropped?: { name: string; error: string }[];
}

/** 보내기 결과를 사용자 글로. ok=false 면 창을 닫지 않고 고쳐 다시 보내게 한다. */
export function resultMessage(r: SubmitResult): { ok: boolean; text: string } {
  if (r.state === "sent") {
    const dropped = r.dropped ?? [];
    const tail = dropped.length
      ? `\n다만 첨부 ${dropped.length}건은 보내지 못했습니다: ` +
        dropped.map((d) => `${d.name}(${errorText(d.error)})`).join(", ")
      : "";
    return { ok: true, text: `피드백을 보냈습니다. 고맙습니다.${r.id ? ` (번호 ${r.id})` : ""}${tail}` };
  }
  if (r.state === "queued") {
    return {
      ok: true,
      text: "지금은 보내지 못해 이 컴퓨터에 두었습니다. 연결되면 앱이 자동으로 다시 보냅니다.",
    };
  }
  return { ok: false, text: errorText(r.error ?? "") };
}
