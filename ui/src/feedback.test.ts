import { describe, expect, test } from "bun:test";
import {
  ACCEPT_ATTR,
  attachBlockReason,
  attachmentKind,
  charCount,
  errorText,
  FEEDBACK_NOTICE_TEXT,
  PHOTO_MAX_BYTES,
  resultMessage,
  validateText,
  VIDEO_MAX_BYTES,
  type Attached,
} from "./feedback";

// 고지 정본(박사님 확정 2026-09-15 18:1x · 도움 서버 FEEDBACK_NOTICE_TEXT) — 구현 상수와 **따로** 적는다.
// 같은 상수를 import 해 비교하면 상수를 고쳐도 시험이 따라와 초록이 된다(대조가 아니다).
const NOTICE_CANON =
  "보내 주신 제목·내용과 사진·영상은 자비스 설치와 사용을 고치는 데만 씁니다. 제목·내용 속 이메일·집 폴더 경로·토큰은 저장하기 전에 지우고, 연락처 칸(적지 않아도 됩니다)은 답을 드리려고 받은 그대로 둡니다. 앱이나 설치 도우미에서 보내면 설치 번호와 판본도 함께 갑니다. 사진·영상은 지울 수 없어 운영팀만 보며, 모두 받은 날로부터 90일 뒤 저절로 지워집니다.";

const photo = (i: number): Attached => ({ kind: "photo", file: `photo-${i}.png`, name: `${i}.png`, bytes: 10 });

describe("고지 문안", () => {
  test("서버 정본과 글자 그대로 같다", () => {
    expect(FEEDBACK_NOTICE_TEXT).toBe(NOTICE_CANON);
  });
  test("보존 기간 90일을 말한다", () => {
    expect(FEEDBACK_NOTICE_TEXT).toContain("90일");
  });
});

describe("charCount — 코드 포인트 단위", () => {
  test("이모지 한 개는 한 글자", () => {
    expect(charCount("😀")).toBe(1);
    expect("😀".length).toBe(2);
  });
});

describe("validateText", () => {
  test("빈 제목·빈 내용을 막는다", () => {
    expect(validateText(" ", "내용", "")).toEqual(["제목을 적어 주세요."]);
    expect(validateText("제목", "\n", "")).toEqual(["내용을 적어 주세요."]);
  });
  test("길이 경계 — 120자 통과 · 121자 막음(한글도 한 글자)", () => {
    expect(validateText("가".repeat(120), "b", "")).toEqual([]);
    expect(validateText("가".repeat(121), "b", "")).toEqual(["제목은 120자까지입니다."]);
    expect(validateText("t", "b".repeat(5001), "")).toEqual(["내용은 5000자까지입니다."]);
    expect(validateText("t", "b", "c".repeat(201))).toEqual(["연락처는 200자까지입니다."]);
  });
  test("연락처는 비워도 된다", () => {
    expect(validateText("t", "b", "")).toEqual([]);
  });
});

describe("attachmentKind", () => {
  test("확장자로 사진·영상을 가르고 대소문자를 무시한다", () => {
    expect(attachmentKind("IMG_0001.HEIC")).toBe("photo");
    expect(attachmentKind("화면 기록.mov")).toBe("video");
    expect(attachmentKind("a.webm")).toBe("video");
  });
  test("서버가 못 받는 형식은 null", () => {
    expect(attachmentKind("문서.pdf")).toBeNull();
    expect(attachmentKind("확장자없음")).toBeNull();
    expect(attachmentKind("a.gif")).toBeNull();
  });
  test("파일 고르기 창 목록은 판별 목록과 같다", () => {
    for (const ext of ACCEPT_ATTR.split(",")) expect(attachmentKind("x" + ext)).not.toBeNull();
  });
});

describe("attachBlockReason", () => {
  test("화면 캡처를 포함해 사진 5장에서 막는다", () => {
    const four = [1, 2, 3, 4].map(photo);
    expect(attachBlockReason(four, "photo", 10)).toBeNull();
    expect(attachBlockReason([...four, photo(5)], "photo", 10)).toContain("5장");
  });
  test("크기 경계 — 사진 5MB · 영상 95MB", () => {
    expect(attachBlockReason([], "photo", PHOTO_MAX_BYTES)).toBeNull();
    expect(attachBlockReason([], "photo", PHOTO_MAX_BYTES + 1)).not.toBeNull();
    expect(attachBlockReason([], "video", VIDEO_MAX_BYTES)).toBeNull();
    expect(attachBlockReason([], "video", VIDEO_MAX_BYTES + 1)).not.toBeNull();
  });
  test("영상은 1개 · 사진 수와 따로 센다", () => {
    const withVideo: Attached[] = [{ kind: "video", file: "video-1.mp4", name: "v.mp4", bytes: 9 }];
    expect(attachBlockReason(withVideo, "video", 9)).toContain("1개");
    expect(attachBlockReason(withVideo, "photo", 9)).toBeNull();
  });
  test("빈 파일은 막는다", () => {
    expect(attachBlockReason([], "photo", 0)).not.toBeNull();
  });
});

describe("resultMessage", () => {
  test("보냄 = 창을 닫고 번호를 알린다", () => {
    const m = resultMessage({ state: "sent", id: "fb_1", dropped: [] });
    expect(m.ok).toBe(true);
    expect(m.text).toContain("fb_1");
  });
  test("보냄이어도 빠진 첨부는 숨기지 않는다", () => {
    const m = resultMessage({ state: "sent", id: "x", dropped: [{ name: "v.mp4", error: "file_too_large" }] });
    expect(m.text).toContain("v.mp4");
    expect(m.text).toContain("첨부 1건");
  });
  test("보관 = 자동으로 다시 보낸다고 말한다", () => {
    const m = resultMessage({ state: "queued", error: "network" });
    expect(m.ok).toBe(true);
    expect(m.text).toContain("다시 보냅니다");
  });
  test("거절 = 창을 닫지 않는다(고쳐 다시 보냄)", () => {
    const m = resultMessage({ state: "rejected", error: "invalid_title" });
    expect(m.ok).toBe(false);
    expect(m.text).toBe("제목을 확인해 주세요.");
  });
  test("상태 번호가 붙은 오류 글도 코드로 읽는다", () => {
    expect(errorText("413 file_too_large")).toBe("첨부 파일이 한도보다 큽니다.");
    expect(errorText("모름")).toBe("보내지 못했습니다.");
  });
});
