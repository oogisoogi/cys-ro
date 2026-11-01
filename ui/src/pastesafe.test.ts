// pastesafe.ts 회귀 테스트 (bun test — 신규 의존성 0).
//
// 공격 바이트는 격리 재현에서 쓴 것 그대로다(TICKET=cysr-ghsa-check). 정상 글은 한 글자도 바뀌면 안 된다.
import { describe, it, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { sanitizePaste } from "./pastesafe";

describe("sanitizePaste — 공격 바이트 무력화", () => {
  it("닫는 표지 탈출: ESC[201~ 뒤 글자가 키 입력이 되지 않는다", () => {
    const out = sanitizePaste("x\x1b[201~\x15touch /tmp/pwn\r");
    expect(out).toBe("x [201~ touch /tmp/pwn\r");
    expect(out).not.toContain("\x1b");
  });
  it("여는 표지도 무력화", () => {
    expect(sanitizePaste("a\x1b[200~b")).toBe("a [200~b");
  });
  it("8비트 C1 표지(U+009B)도 무력화", () => {
    expect(sanitizePaste("x\u009b201~y\u009b200~z")).toBe("x 201~y 200~z");
  });
  it("^C 끼워 넣기", () => {
    expect(sanitizePaste("abc\x03touch /tmp/pwn\r")).toBe("abc touch /tmp/pwn\r");
  });
  it("^D·DEL·NUL·BS", () => {
    expect(sanitizePaste("a\x04b\x7fc\x00d\x08e")).toBe("a b c d e");
  });
});

describe("sanitizePaste — 정상 글 불변", () => {
  const same = [
    "",
    "안녕하세요 박사님",
    "한글 첫줄\n둘째 줄\n셋째 줄",
    "윈도우 줄바꿈\r\n둘째\r\n",
    "탭\t구분\t값",
    "if (a) {\n\treturn 1;\n}\n",
    "이모지 🙂👍🏽 가족 👨‍👩‍👧‍👦",
    "조합형 한글 한",
    "일본語 中文 العربية",
    "기호 ~ [201~ [200~ $( ) ` ' \" \\ %",
    " ­​﻿", // C1 바로 위·서식 문자는 범위 밖이다
  ];
  for (const s of same) {
    it(JSON.stringify(s), () => {
      expect(sanitizePaste(s)).toBe(s);
    });
  }
});

describe("sanitizePaste — 글자 전수", () => {
  it("U+0000~U+02FF 는 위험 집합만 공백이 되고 나머지는 그대로다", () => {
    const keep = (c: number) => c === 0x09 || c === 0x0a || c === 0x0d || (c >= 0x20 && c < 0x7f) || c >= 0xa0;
    for (let c = 0; c < 0x300; c++) {
      const ch = String.fromCharCode(c);
      expect(sanitizePaste(`a${ch}b`)).toBe(keep(c) ? `a${ch}b` : "a b");
    }
  });
  it("멱등", () => {
    const once = sanitizePaste("x\x1b[201~\u009b\x03y");
    expect(sanitizePaste(once)).toBe(once);
  });
  it("여러 번 나와도 전부 바뀐다(g 플래그)", () => {
    expect(sanitizePaste("\x1b\x1b\x03\x03")).toBe("    ");
  });
});

describe("배선 핀 — 사람 붙여넣기는 살균을 지난다", () => {
  const src = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  it("클립보드 글은 sanitizePaste 를 거쳐 term.paste 로 간다", () => {
    expect(src).toContain("term.paste(sanitizePaste(text));");
    expect(src).not.toContain("term.paste(text);");
  });
  it("term.paste 입구는 둘뿐이다(글 + 앱이 저장한 이미지 경로)", () => {
    expect(src.match(/term\.paste\(/g)?.length).toBe(3); // 주석 1 + 호출 2
  });
});
