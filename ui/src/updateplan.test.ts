import { describe, expect, test } from "bun:test";
import { updatePlan } from "./updateplan";

const base = { binCheckFailed: false, packCheckFailed: false, binaryTooOld: false };

describe("updatePlan — 옵션 2 분기 판정(문자열 핀 = 회귀 0 증명)", () => {
  test("★신설: 본체+팩 동시 + 호환 → 팩 무중단을 가리지 않는다", () => {
    const p = updatePlan({ ...base, binVersion: "0.12.57", packVersion: "0.12.58" });
    expect(p.kind).toBe("pack-and-binary");
    expect(p.badge).toBe("↻");
    // (r2 · D4 #14) 팩 → 자비스 구성 · 본체 → 앱 · 패치 설치 → 설치 · 무중단 → 재시작 없이(뜻 동일 · 분기 불변)
    expect(p.title).toBe("새 자비스 구성 0.12.58 은 재시작 없이 적용 · 새 앱 0.12.57 도 설치 가능");
    expect(p.toastMsg).toContain("재시작 없이 적용됩니다");
    expect(p.toastMsg).toContain("같은 단추로 설치"); // T5 개정(오너 2026-07-15) — 앱 인앱 설치 안내
  });

  test("본체+팩 동시 + 비호환 → 종전대로 본체 필요(가림이 정당한 케이스)", () => {
    const p = updatePlan({ ...base, binVersion: "0.12.57", packVersion: "0.12.58", binaryTooOld: true });
    // binVersion 존재가 우선 — 본체 안내(팩은 어차피 min_binary 미달).
    expect(p.kind).toBe("binary");
  });

  test("본체만 → 패치 설치 문구(T5 개정 — 오너 2026-07-15)", () => {
    const p = updatePlan({ ...base, binVersion: "0.12.57", packVersion: null });
    expect(p.kind).toBe("binary");
    expect(p.badge).toBe("!");
    expect(p.title).toBe("새 앱 0.12.57 — 상단 「업데이트」로 설치");
    expect(p.toastMsg).toBe("새 앱 0.12.57 이 나왔습니다. 상단 「업데이트」를 누르면 설치하고, 다시 켜지면 하던 창이 돌아옵니다.");
  });

  test("팩만 + 호환 → 종전 무중단 문구 그대로(회귀 0)", () => {
    const p = updatePlan({ ...base, binVersion: null, packVersion: "0.12.58" });
    expect(p.kind).toBe("pack");
    expect(p.badge).toBe("↻");
    expect(p.title).toBe("새 자비스 구성 0.12.58 — 재시작 없이 적용");
    expect(p.toastMsg).toBe("새 자비스 구성 0.12.58 이 있습니다. 상단 「업데이트」를 누르면 재시작 없이 적용됩니다.");
  });

  test("팩만 + 비호환 → 종전 본체 필요 문구 그대로(회귀 0)", () => {
    const p = updatePlan({ ...base, binVersion: null, packVersion: "0.12.58", binaryTooOld: true });
    expect(p.kind).toBe("binary-required");
    expect(p.badge).toBe("!");
    expect(p.title).toBe("새 자비스 구성 0.12.58 — 앱을 먼저 새 판으로 받아 주세요");
    expect(p.toastMsg).toBe(
      "새 자비스 구성 0.12.58 은 더 새로운 앱이 있어야 적용됩니다. 설치 사이트에서 앱을 먼저 받아 주세요: https://jarvis-install.godmeyou.kr",
    );
    // ★r3 S3 — URL 바로 뒤에 괄호·문자가 붙으면 링크 파서가 그것까지 주소로 먹는다. 뒤는 공백이나 끝이어야 한다.
    expect(p.toastMsg).toMatch(/https:\/\/jarvis-install\.godmeyou\.kr(\s|$)/);
    // ★안내 링크는 문장과 **독립으로** 판정한다(r2 · codex·agy 1R) — scheme 이 빠지면 링크로 인식되지 않는다.
    const link = p.toastMsg.match(/https?:\/\/[^\s)]+/);
    expect(link).not.toBeNull();
    const u = new URL(link![0]);
    expect(u.protocol).toBe("https:");
    expect(u.host).toBe("jarvis-install.godmeyou.kr");
    expect(p.title).not.toContain("홈페이지");
    expect(p.toastMsg).not.toContain("홈페이지");
  });

  test("업데이트 없음 + 양쪽 체크 성공 → '0' 배지(종전)", () => {
    const p = updatePlan({ ...base, binVersion: null, packVersion: null });
    expect(p.kind).toBe("none");
    expect(p.badge).toBe("0");
    expect(p.ok).toBe(true);
    expect(p.title).toBe("최신 버전 — 대기 중인 업데이트 없음");
  });

  test("업데이트 없음 + 체크 실패 → unknown = 배지 유지(fail-safe 종전)", () => {
    for (const f of [
      { binCheckFailed: true, packCheckFailed: false },
      { binCheckFailed: false, packCheckFailed: true },
      { binCheckFailed: true, packCheckFailed: true },
    ]) {
      const p = updatePlan({ ...base, ...f, binVersion: null, packVersion: null });
      expect(p.kind).toBe("unknown");
      expect(p.badge).toBe("");
    }
  });

  test("체크 실패여도 보존 상태가 있으면 그 상태로 판정(fail-safe 보존 종전)", () => {
    const p = updatePlan({ ...base, binCheckFailed: true, binVersion: "0.12.57", packVersion: null });
    expect(p.kind).toBe("binary");
  });
});
