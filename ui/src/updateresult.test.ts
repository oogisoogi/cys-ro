// updateresult.ts 순수 로직 + main.ts 배선 핀(1.1.8 U4 · 설계 AUTO-UPDATE-118 §3-12 · 📌18).
//
// 지키는 계약:
//   ① 응답 모양을 믿지 않는다 — 토스트 id 는 두 값만 · result_id 형식 · 문자열에 제어문자(줄바꿈은 본문 1곳만 허용)가 있으면 통째로 버린다.
//   ② 순서: 백엔드 ①②(표시 전 기록) → ③ stickyToast(textContent) → ④ update_result_notice_done. ③ 이 ④ 보다 앞이다.
//   ③ 좌석 0 고정 안내 — textContent 로만 · 닫기 단추 없음 · 조회 실패면 상태를 건드리지 않는다.
//   ④ 앱에 갱신을 결정·집행하는 호출이 없다(설계 §5-1 — 사용자가 누르는 갱신 단추 0).
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { latestOnly, parseResultNotice, seatsBlockedText, SEATS_NOTE_POLL_MS, UPDATE_RESULT_TOAST_ID, UPDATE_ROLLBACK_FAILED_TOAST_ID } from "./updateresult";

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
  it("제어문자·줄바꿈·줄 나눔·방향 바꿈 글자는 통째로 거부 — 알림은 한 줄(설계 §6-1 · 2판 codex 1R ⑥)", () => {
    expect(parseResultNotice({ ...ok, body: "첫 문장. 달라진 점: 같은 줄" })?.body).toBe("첫 문장. 달라진 점: 같은 줄");
    expect(parseResultNotice({ ...ok, body: "첫 줄\n달라진 점: 둘째 줄" })).toBe(null);
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
    expect(CODE.split("void refreshSeatsBlockedNote()").length - 1).toBe(4); // 기동 · 포커스 · 저율 폴링 · 다시 보일 때
  });
  it("고정 안내: textContent 로만 · innerHTML 0 · 닫기 단추 만들지 않음 · 조회는 latestOnly 경유(실패 = 손대지 않음 · 역순 응답 폐기)", () => {
    const b = fnBody("applySeatsBlockedNote");
    expect(b).toContain('getElementById("update-hold-note")');
    expect(b).toContain("el.textContent = text ?? \"\";");
    expect(b).toContain("el.hidden = text === null;");
    expect(b).not.toContain("innerHTML");
    expect(b).not.toContain("createElement");
    expect(CODE).toContain('const refreshSeatsBlockedNote = latestOnly(() => invoke("update_seats_blocked_notice"), applySeatsBlockedNote);');
  });
  it("(2판 · codex 1R ②) 포커스·보임이 그대로여도 저율 폴링으로 다시 잰다 — 간격 ≥30초(비용 0 에 가깝게)", () => {
    expect(CODE).toContain("setInterval(() => void refreshSeatsBlockedNote(), SEATS_NOTE_POLL_MS);");
    expect(SEATS_NOTE_POLL_MS).toBeGreaterThanOrEqual(30_000);
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

describe("latestOnly — 겹친 조회의 역순 응답 폐기 · 포커스 유지 중 자동 소거(2판 · codex 1R ②)", () => {
  type Deferred = { promise: Promise<unknown>; resolve: (v: unknown) => void; reject: (e: unknown) => void };
  const deferred = (): Deferred => {
    let resolve!: (v: unknown) => void;
    let reject!: (e: unknown) => void;
    const promise = new Promise<unknown>((a, b) => {
      resolve = a;
      reject = b;
    });
    return { promise, resolve, reject };
  };
  const BLOCKED = "자비스가 잠깐 쉬고 있어요. 처음 설치할 때 쓴 링크 한 줄을 다시 붙여 넣으시면 바로 다시 쓸 수 있어요.";

  it("옛 조회(차단됨)가 새 조회(풀림)보다 늦게 끝나도 안내를 되살리지 않는다", async () => {
    const calls: Deferred[] = [];
    const shown: (string | null)[] = [];
    const refresh = latestOnly(() => {
      const d = deferred();
      calls.push(d);
      return d.promise;
    }, (v) => shown.push(seatsBlockedText(v)));
    const old = refresh();
    const fresh = refresh();
    calls[1].resolve(null); // 새 조회 = 풀림
    await fresh;
    calls[0].resolve(BLOCKED); // 옛 조회 = 차단됨(늦게 도착)
    await old;
    expect(shown).toEqual([null]);
  });

  it("조회가 던지면 아무것도 바꾸지 않는다(일시 실패로 안내를 지우지도 만들지도 않음)", async () => {
    const shown: unknown[] = [];
    await latestOnly(() => Promise.reject(new Error("x")), (v) => shown.push(v))();
    expect(shown).toEqual([]);
  });

  it("★포커스 유지 중 복구 — 이벤트 없이 폴링 틱만으로 차단 → 풀림이 화면에 반영된다", async () => {
    let backend: unknown = BLOCKED;
    const note = { text: "", hidden: true };
    const refresh = latestOnly(() => Promise.resolve(backend), (v) => {
      const t = seatsBlockedText(v);
      note.text = t ?? "";
      note.hidden = t === null;
    });
    await refresh(); // 기동
    expect(note).toEqual({ text: BLOCKED, hidden: false });
    backend = null; // 창은 그대로(포커스·보임 이벤트 없음) · 러너가 seats_blocked 를 지움
    await refresh(); // 저율 폴링 한 틱
    expect(note).toEqual({ text: "", hidden: true });
  });
});
