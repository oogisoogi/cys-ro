// TICKET=cys-117-exitedpane-b1 — 본부(기본) 데몬 종료 소식이 창 제거까지 닿는가 + F4(타 부서 같은 번호) 보호.
import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { eventSock } from "./evsock";

const DEFAULT_SLUG = "00000000000000aa";
const DEPT_SLUG = "00000000000000bb";
const DEPT_SOCK = "/tmp/cys-dept-x.sock";
const dept = new Map([[DEPT_SLUG, DEPT_SOCK]]);

describe("eventSock — 종료 소식의 출처 판정", () => {
  test("본부(기본) 데몬 식별표 → 본부 작업공간(socket undefined)으로 처리한다", () => {
    expect(eventSock(DEFAULT_SLUG, dept, DEFAULT_SLUG)).toEqual({ ok: true, socket: undefined });
  });

  test("부서 데몬 식별표 → 그 부서 소켓(회귀 0)", () => {
    expect(eventSock(DEPT_SLUG, dept, DEFAULT_SLUG)).toEqual({ ok: true, socket: DEPT_SOCK });
  });

  test("식별표 없음 → 기본 데몬(하위호환)", () => {
    expect(eventSock(undefined, dept, DEFAULT_SLUG)).toEqual({ ok: true, socket: undefined });
    expect(eventSock("", dept, DEFAULT_SLUG)).toEqual({ ok: true, socket: undefined });
  });

  test("F4 보호: 알 수 없는 식별표(아직 등록 전 타 부서)는 본부로 폴백하지 않는다", () => {
    expect(eventSock("00000000000000cc", dept, DEFAULT_SLUG)).toEqual({ ok: false });
  });

  test("F4 보호: 기본 식별표를 아직 모르면(null) 어떤 식별표도 본부로 보지 않는다", () => {
    expect(eventSock(DEFAULT_SLUG, dept, null)).toEqual({ ok: false });
    expect(eventSock("00000000000000cc", new Map(), null)).toEqual({ ok: false });
  });

  test("부서 식별표가 기본 식별표 판정보다 먼저다(부서 표 우선 · 기존 동작 보존)", () => {
    const m = new Map([[DEFAULT_SLUG, DEPT_SOCK]]);
    expect(eventSock(DEFAULT_SLUG, m, DEFAULT_SLUG)).toEqual({ ok: true, socket: DEPT_SOCK });
  });
});

// main.ts 처리기는 화면을 띄워야 돌므로 배선을 소스로 고정한다(다른 모듈 시험의 관례).
describe("main.ts 배선 — 종료 소식 처리기가 판정부를 쓰고 기본 식별표를 백엔드에서 받는다", () => {
  const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  const at = main.indexOf('name === "surface.exited" || name === "surface.closed" || name === "surface.reaped"');
  const branch = main.slice(at, main.indexOf("\n  }\n}", at));

  test("처리기가 eventSock(… defaultSocketSlug) 로 판정하고 그 결과로 removeDeadPane 을 부른다", () => {
    expect(at).toBeGreaterThan(0);
    expect(branch.includes("eventSock(event.socket_slug, socketForSlug, defaultSocketSlug)")).toBe(true);
    expect(branch.includes("if (!src.ok) return;")).toBe(true);
    expect(branch.includes("removeDeadPane(Number(sid), src.socket)")).toBe(true);
  });

  test("기본 식별표는 백엔드 명령 default_socket_slug 로 받는다", () => {
    expect(main.includes('invoke("default_socket_slug")')).toBe(true);
  });
});
