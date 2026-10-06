// updateresult.ts 순수 로직 + main.ts 배선 핀(1.1.8 U4 · 설계 AUTO-UPDATE-118 §3-12 · 📌18).
//
// 지키는 계약:
//   ① 응답 모양을 믿지 않는다 — 토스트 id 는 두 값만 · result_id 형식 · 문자열에 제어문자(줄바꿈은 본문 1곳만 허용)가 있으면 통째로 버린다.
//   ② 순서: 백엔드 ①②(표시 전 기록) → ③ stickyToast(textContent) → ④ update_result_notice_done. ③ 이 ④ 보다 앞이다.
//   ③ 좌석 0 고정 안내 — textContent 로만 · 닫기 단추 없음 · 조회 실패면 상태를 건드리지 않는다.
//   ④ 앱에 갱신을 결정·집행하는 호출이 없다(설계 §5-1 — 사용자가 누르는 갱신 단추 0).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { parseResultNotice, seatsBlockedText, UPDATE_RESULT_TOAST_ID, UPDATE_ROLLBACK_FAILED_TOAST_ID } from "./updateresult";

const ok = { toast_id: "update-result", result_id: "r-1", title: "자비스 새 판", body: "자비스가 새 판으로 바뀌었어요. 하던 일은 그대로 이어집니다." };

describe("parseResultNotice — 응답 모양 의심", () => {
  it("정상 응답 → 알림 1건(필드 이름을 화면 쪽 이름으로)", () => {
    expect(parseResultNotice(ok)).toEqual({ toastId: UPDATE_RESULT_TOAST_ID, resultId: "r-1", title: ok.title, body: ok.body });
    expect(parseResultNotice({ ...ok, toast_id: "update-rollback-failed" })?.toastId).toBe(UPDATE_ROLLBACK_FAILED_TOAST_ID);
  });
  it("모르는 토스트 id 는 버린다 — 남의 토스트(진행·경보)를 덮지 않게", () => {
    for (const id of ["restore", "bundle-damaged", "purge-fail-x", "update-not-installed", "", 1, null, undefined]) {
      expect({ id, n: parseResultNotice({ ...ok, toast_id: id }) }).toEqual({ id, n: null });
    }
  });
  it("모양이 틀리면 null(무음)", () => {
    for (const v of [null, undefined, 0, "x", [], {}]) expect(parseResultNotice(v)).toBe(null);
    for (const rid of ["", "a b", "a/b", "x".repeat(65), 7, null]) expect({ rid, n: parseResultNotice({ ...ok, result_id: rid }) }).toEqual({ rid, n: null });
    expect(parseResultNotice({ ...ok, result_id: "x".repeat(64) })?.resultId).toBe("x".repeat(64));
    for (const t of ["", 3, null]) expect(parseResultNotice({ ...ok, title: t })).toBe(null);
  });
  it("제어문자·줄 나눔·방향 바꿈 글자는 통째로 거부 — 본문의 줄바꿈(릴리스 노트 둘째 줄)만 허용", () => {
    expect(parseResultNotice({ ...ok, body: "첫 줄\n달라진 점: 둘째 줄" })?.body).toBe("첫 줄\n달라진 점: 둘째 줄");
    expect(parseResultNotice({ ...ok, title: "제목\n둘째" })).toBe(null);
    for (const bad of ["a\rb", "a\u0000b", "a\u001b[31mb", "a\u007fb", "a\u0085b", "a b", "a b", "a‮b", "a⁦b", "a‏b", "a؜b", "a\tb"]) {
      expect({ bad, n: parseResultNotice({ ...ok, body: bad }) }).toEqual({ bad, n: null });
      expect({ bad, s: seatsBlockedText(bad) }).toEqual({ bad, s: null });
    }
    expect(parseResultNotice({ ...ok, body: "가".repeat(601) })).toBe(null);
  });
});

describe("seatsBlockedText — 📌18 고정 안내", () => {
  it("문자열이면 그대로 · null·빈 값·문자열 아님·줄바꿈 = 안내 없음", () => {
    const t = "자비스가 잠깐 쉬고 있어요. 처음 설치할 때 쓴 링크 한 줄을 다시 붙여 넣으시면 바로 다시 쓸 수 있어요.";
    expect(seatsBlockedText(t)).toBe(t);
    for (const v of [null, undefined, "", 1, {}, "a\nb"]) expect(seatsBlockedText(v)).toBe(null);
  });
});

const MAIN = readFileSync(new URL("./main.ts", import.meta.url), "utf-8");
const CODE = MAIN.split("\n")
  .map((l) => (l.trimStart().startsWith("//") ? "" : l.replace(/\s\/\/.*$/, "")))
  .join("\n");
function fnBody(name: string): string {
  const a = CODE.search(new RegExp(`(async )?function ${name}\\(`));
  expect(a).toBeGreaterThanOrEqual(0);
  const b = CODE.indexOf("\n}\n", a);
  expect(b).toBeGreaterThan(a);
  return CODE.slice(a, b);
}

describe("main.ts 배선 — 순서 ①②→③→④ · 고정 안내", () => {
  it("결과 알림: 백엔드 판정(①② 표시 전 기록) → 형식 의심 → ③ stickyToast → ④ done 순서", () => {
    const b = fnBody("pullUpdateResultNotice");
    const take = b.indexOf('invoke("update_result_notice")');
    const parse = b.indexOf("parseResultNotice(");
    const show = b.indexOf("stickyToast(n.toastId, ");
    const done = b.indexOf('invoke("update_result_notice_done", { resultId: n.resultId })');
    expect([take, parse, show, done].every((i) => i >= 0)).toBe(true);
    expect(take < show && parse < show && show < done).toBe(true);
    expect(b).toContain("if (n === null) return;");
    // ④ 를 부르는 곳은 이 함수 한 곳뿐(③ 없이 닫는 경로 0)
    expect(CODE.split('invoke("update_result_notice_done"').length - 1).toBe(1);
    expect(CODE.split('invoke("update_result_notice")').length - 1).toBe(1);
  });
  it("결과 알림은 기동 때 1회만 부른다(창 하나에 토스트 1개) · 고정 안내는 기동·포커스·다시 보일 때", () => {
    expect(CODE.split("void pullUpdateResultNotice();").length - 1).toBe(1);
    expect(CODE.split("void refreshSeatsBlockedNote()").length - 1).toBe(3);
  });
  it("고정 안내: textContent 로만 · innerHTML 0 · 닫기 단추 만들지 않음 · 조회 실패면 손대지 않음", () => {
    const b = fnBody("refreshSeatsBlockedNote");
    expect(b).toContain('getElementById("update-hold-note")');
    expect(b).toContain("el.textContent = text ?? \"\";");
    expect(b).toContain("el.hidden = text === null;");
    expect(b).not.toContain("innerHTML");
    expect(b).not.toContain("createElement");
    const catchAt = b.indexOf("} catch {");
    expect(b.slice(catchAt, catchAt + 40)).toContain("return;");
  });
  it("★앱에 갱신을 결정·집행하는 호출이 없다 — 옛 명령 이름 0(설계 §5-1·§5-2)", () => {
    for (const cmd of ["check_update", "install_update", "check_pack_update", "install_pack_update", "restart_after_update", "update_attempt_report", "smart_app_control", "update_checked_launch_enabled", "autotest_patch_install"]) {
      expect({ cmd, 있음: CODE.includes(`invoke("${cmd}"`) }).toEqual({ cmd, 있음: false });
    }
    for (const ev of ["update-progress", "update-restart-required", "pack-progress", "pack-updated", "pack-uptodate", "update-warning"]) {
      expect({ ev, 있음: CODE.includes(`listen("${ev}"`) }).toEqual({ ev, 있음: false });
    }
    // 남기는 것(설계 §5-1 「남긴다」): update-error 듣개
    expect(CODE.includes('listen("update-error"')).toBe(true);
  });
});
