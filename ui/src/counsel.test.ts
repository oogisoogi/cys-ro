// counsel.ts 순수 로직 시험 — 「자동 보고」 상태 판독·문구(1.1.10 cysr-1110-counsel-off → 1.1.19 · cysr-1119-s10b AG4·AG5).
// ★(1.1.19) 상담소 창·글 목록·배지의 순수 로직(buildCounselView·parseUnread·stepUnread·badgeText …)과 그 시험은 화면과 함께 뺐다.
import { describe, it, expect } from "bun:test";
import { AUTO_COPY, REPORT_NOTICE, autoLine, autoNotice, autoToggle, parseAutoStatus } from "./counsel";

describe("자동 보고 켜기/끄기 상태 판독(TICKET=cysr-1110-counsel-off · 1.1.19 이름 = 자동 보고)", () => {
  it("auto 가 참/거짓일 때만 안다 · 안내는 켜짐이고 팩이 원할 때만", () => {
    expect(parseAutoStatus({ auto: true, notice_seen: false, needs_notice: true })).toEqual({ auto: true, needsNotice: true });
    expect(parseAutoStatus({ auto: false, needs_notice: true })).toEqual({ auto: false, needsNotice: false });
    for (const bad of [null, undefined, "x", { error: "no-python" }, { auto: "true" }]) {
      expect(parseAutoStatus(bad)).toEqual({ auto: null, needsNotice: false });
    }
  });
  it("모를 때 단추 = 끄기(안전 쪽) · 줄 문구", () => {
    expect(autoToggle(true)).toEqual({ label: AUTO_COPY.turnOff, next: false });
    expect(autoToggle(null)).toEqual({ label: AUTO_COPY.turnOff, next: false });
    expect(autoToggle(false)).toEqual({ label: AUTO_COPY.turnOn, next: true });
    expect([autoLine(true), autoLine(false), autoLine(null)]).toEqual([AUTO_COPY.on, AUTO_COPY.off, AUTO_COPY.unknown]);
  });
  it("단추 아래 안내문 — 꺼짐만 「다시 켜려면」 · 켜짐·모름 = 승인 문구 그대로(cysr-1110-visual 눈 검수)", () => {
    // (cysr-1119-s10b AG5n · D-03) 다시 켜는 자리 = 화면 설정 「자동 보고」 한 줄(상담소 창 없음).
    expect(autoNotice(false)).toBe("지금은 보내지 않습니다. 다시 켜려면 화면 설정 \u2192 \u2018자동 보고\u2019를 켜세요.");
    expect(autoNotice(true)).toBe(REPORT_NOTICE);
    expect(autoNotice(null)).toBe(REPORT_NOTICE);
  });
});
