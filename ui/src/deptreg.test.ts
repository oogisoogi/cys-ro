// deptreg.ts 회귀 — 판독 실패가 「부서 0」 과 구분되는지(TICKET=cysr-117-impl-lead ①).
import { describe, expect, test } from "bun:test";
import { deptRegistryUnreadableNote, readDeptRegistry } from "./deptreg";

describe("readDeptRegistry", () => {
  test("정상 목록", async () => {
    const r = await readDeptRegistry(async () => ({ depts: { a: { socket: "/s" } } }));
    expect(r).toEqual({ depts: { a: { socket: "/s" } }, unreadable: null });
  });
  test("부서 0 = 못 읽음 아님", async () => {
    expect(await readDeptRegistry(async () => ({ depts: {} }))).toEqual({ depts: {}, unreadable: null });
    expect(await readDeptRegistry(async () => ({}))).toEqual({ depts: {}, unreadable: null });
  });
  test("invoke 실패 = 못 읽음(이유 보존)", async () => {
    const r = await readDeptRegistry(async () => {
      throw "부서 목록 읽기 실패: Permission denied";
    });
    expect(r.depts).toEqual({});
    expect(r.unreadable).toContain("Permission denied");
  });
  test("형식 불일치 = 못 읽음", async () => {
    for (const bad of [{ depts: ["a"] }, { depts: "a" }]) {
      expect((await readDeptRegistry(async () => bad)).unreadable).not.toBeNull();
    }
  });
  test("안내 문구에 이유가 실린다", () => {
    expect(deptRegistryUnreadableNote("X")).toContain("(X)");
  });
});
