// (TICKET=cysr-1119-s2 · DESIGN §3-2 F36 · §3-3 F38 · §3-4 K18) 대화 화면 IPC 인자·되돌리기 값·사람 쓰기 길 바이트 검사.
//   F36 = `chat_transcript` 호출은 셋 모두 `ChatCore.transcriptArgs` 한 함수를 거친다(원천 검사 + compat 켠 상태 IPC 바이트 = 1.1.18).
//   F38 = 되돌리기 값은 환경 변수 몫 하나(`Deps.compat1118`) — 저장 키 `cys-chat-compat-1118` 은 두지 않는다.
//   K18 = 대화 화면 보내기가 데몬에 싣는 칸(`viewcore.rs` `human_send_params` · `chat_send` 사람 갈래)과 데몬 처리기·writer 두 파일 = 838f24421 그대로.
import { describe, it, expect } from "bun:test";
import { readFileSync, readdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { ChatCore, type Deps } from "./core";

const SRC = new URL("../", import.meta.url); // ui/src/
const REPO = new URL("../../../", import.meta.url); // 저장소 뿌리

/** ui/src 아래 시험 밖 .ts 전부(열거는 기계에 — 손 목록은 빠뜨린다 · 시험 대역 views/testkit.ts 제외 = 아래 시험이 「시험 파일만 import」 를 못박음). */
function prodTs(): string[] {
  const out: string[] = [];
  const walk = (rel: string) => {
    for (const e of readdirSync(new URL(rel, SRC), { withFileTypes: true })) {
      if (e.isDirectory()) {
        if (e.name !== "node_modules") walk(`${rel}${e.name}/`);
      } else if (e.name.endsWith(".ts") && !e.name.endsWith(".test.ts") && !e.name.endsWith(".d.ts") && e.name !== "testkit.ts" && e.name !== "verify_s3_world.ts") out.push(`${rel}${e.name}`); // testkit = 시험 대역(시험 파일만 import) · verify_s3_world = S3 독립 검증 재현 대역(같은 꼴 · 병합 S3 검증 고침)
    }
  };
  walk("");
  return out.sort();
}
const read = (rel: string) => readFileSync(new URL(rel, SRC), "utf-8");

describe("F36 — chat_transcript 인자 한 함수(transcriptArgs)", () => {
  it("원천 검사: 시험 밖 `invoke(\"chat_transcript\"` = 셋(core 둘 · confirm 하나) · 전부 transcriptArgs 경유", () => {
    const hits: Array<{ file: string; line: string }> = [];
    for (const f of prodTs()) {
      for (const line of read(f).split("\n")) {
        if (line.includes('"chat_transcript"') && line.includes("invoke(")) hits.push({ file: f, line: line.trim() });
      }
    }
    expect(hits.map((h) => h.file)).toEqual(["views/confirm.ts", "views/core.ts", "views/core.ts"]);
    for (const h of hits) expect(h.line).toMatch(/invoke\("chat_transcript", this\.(d\.)?transcriptArgs\(/);
  });
  it("원천 검사: afterOffset·fromEnd 칸을 적은 줄은 transcriptArgs 줄뿐 · 인자 객체 글자 = core.ts 정의 한 곳", () => {
    const stray: string[] = [];
    const lit: string[] = [];
    for (const f of prodTs()) {
      read(f)
        .split("\n")
        .forEach((line, i) => {
          if (/^\s*(\/\/|\*|\/\*\*)/.test(line)) return; // 주석 줄
          // (병합 S3 · CH-C) 다른 명령 `chat_transcript_tail`(쥔 핸들 이어 읽기 · Rust 인자 surface_id·after_offset 둘뿐 · RPC 0)의 인자 줄은 이 계약 밖
          if (/\b(afterOffset|fromEnd)\b/.test(line) && !line.includes("transcriptArgs") && !line.includes('invoke("chat_transcript_tail"')) stray.push(`${f}:${i + 1}`);
          if (line.includes("{ socket: null, surfaceId, afterOffset, fromEnd }")) lit.push(f);
        });
    }
    expect(stray).toEqual([]);
    expect(lit).toEqual(["views/core.ts"]);
  });

  // compat 켠/끈 상태에서 세 호출(시작점 · 이어 읽기 · 앞 기록 훑기)의 IPC 인자 JSON 바이트 = 1.1.18 꼴.
  const OLD = (surfaceId: number, afterOffset: number, fromEnd: boolean) => JSON.stringify({ socket: null, surfaceId, afterOffset, fromEnd });
  for (const compat of [true, false]) {
    it(`compat ${compat ? "켬" : "끔"} — 세 호출의 IPC 인자 바이트 = 1.1.18`, async () => {
      const calls: string[] = [];
      let file = 0;
      const mem = new Map<string, string>();
      const deps: Deps = {
        invoke: async (cmd, args) => {
          if (cmd === "org_status") return { surfaces: [{ surface_id: 5, role: "master", exited: false, agent_alive: true, pending_input_bytes: 0, pending_input_human_bytes: 0, input_paste_open: false, gate_pending: null, human_idle_secs: null, working: false }] };
          if (cmd === "feed_list") return { items: [] };
          if (cmd === "chat_transcript") {
            calls.push(JSON.stringify(args));
            const a = args as { fromEnd: boolean };
            file += 3;
            return { status: "ok", session_id: "s", next_offset: a.fromEnd ? 7 : 7 + file, size: 7 + file, records: [] };
          }
          return null;
        },
        now: () => 1_000_000,
        setTimeout: () => 0,
        clearTimeout: () => {},
        store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v), remove: (k) => void mem.delete(k) },
        working: () => false,
        compat1118: () => compat,
      };
      const c = new ChatCore(deps);
      expect(c.compat1118).toBe(compat);
      c.attach();
      await c.poll();
      for (let i = 0; i < 20; i++) await Promise.resolve();
      await c.readTranscript(); // 시작점(fromEnd) — attach 가 이미 잡았으면 이어 읽기
      await c.readTranscript(); // 이어 읽기
      await c.poll(); // 앞 기록 훑기(confirm.scanStep)
      for (let i = 0; i < 20; i++) await Promise.resolve();
      expect(calls).toContain(OLD(5, 0, true)); // core initOffset(시작점)
      expect(calls).toContain(OLD(5, 7, false)); // core readTranscript(시작점 뒤 이어 읽기)
      expect(calls).toContain(OLD(5, 0, false)); // confirm.scanStep(앞 기록 훑기 · 0 부터)
      for (const s of calls) {
        const a = JSON.parse(s) as { surfaceId: number; afterOffset: number; fromEnd: boolean };
        expect(s).toBe(OLD(a.surfaceId, a.afterOffset, a.fromEnd)); // 칸·순서·값 꼴 = 1.1.18(compat 칸 없음)
      }
      c.detach();
    });
  }
  it("transcriptArgs 출력 = 1.1.18 객체 그대로(compat 칸 0)", () => {
    const c = new ChatCore({
      invoke: async () => null,
      now: () => 0,
      setTimeout: () => 0,
      clearTimeout: () => {},
      store: { get: () => null, set: () => {}, remove: () => {} },
      working: () => false,
      compat1118: () => true,
    });
    expect(JSON.stringify(c.transcriptArgs(9, 42, false))).toBe('{"socket":null,"surfaceId":9,"afterOffset":42,"fromEnd":false}');
    expect(JSON.stringify(c.transcriptArgs(9, 0, true))).toBe('{"socket":null,"surfaceId":9,"afterOffset":0,"fromEnd":true}');
  });
  it("views/testkit.ts 는 시험 파일만 import(운영 코드 0 — 위 열거에서 빼는 근거)", () => {
    expect(prodTs().filter((f) => /from "\.\/testkit"|from "\.\.\/testkit"|from "\.\/views\/testkit"/.test(read(f)))).toEqual([]);
  });
});

describe("F38 — 되돌리기 값 하나(환경 변수 몫) · 저장 키 없음", () => {
  const base = (extra: Partial<Deps>, mem = new Map<string, string>()): Deps => ({
    invoke: async () => null,
    now: () => 0,
    setTimeout: () => 0,
    clearTimeout: () => {},
    store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v), remove: (k) => void mem.delete(k) },
    working: () => false,
    ...extra,
  });
  it("Deps 없음 = 끔 · 던짐 = 끔 · true = 켬 · true 아닌 값 = 끔", () => {
    expect(new ChatCore(base({})).compat1118).toBe(false);
    expect(
      new ChatCore(
        base({
          compat1118: () => {
            throw new Error("env");
          },
        }),
      ).compat1118,
    ).toBe(false);
    expect(new ChatCore(base({ compat1118: () => true })).compat1118).toBe(true);
    expect(new ChatCore(base({ compat1118: () => "1" as unknown as boolean })).compat1118).toBe(false);
  });
  it("저장소에 `cys-chat-compat-1118` 을 넣어도 끔(저장소를 읽지 않음)", () => {
    const mem = new Map([["cys-chat-compat-1118", "1"]]);
    expect(new ChatCore(base({}, mem)).compat1118).toBe(false);
  });
  it("원천 검사: 저장 키 글자 `cys-chat-compat-1118` = ui/src 시험 밖 0", () => {
    const hit = prodTs().filter((f) => read(f).includes("cys-chat-compat-1118"));
    expect(hit).toEqual([]);
  });
});

// ---------- K18 — 사람 쓰기 길 바이트 동일(838f24421) ----------
const rs = (rel: string) => readFileSync(new URL(rel, REPO), "utf-8").replace(/\r\n/g, "\n");
/** `start` 로 시작하는 줄부터 같은 들여쓰기의 닫는 `}` 줄까지(그 줄 포함). */
function block(src: string, start: string): string {
  const lines = src.split("\n");
  const i = lines.findIndex((l) => l.startsWith(start));
  expect(i).toBeGreaterThanOrEqual(0);
  const indent = (lines[i].match(/^\s*/) as RegExpMatchArray)[0];
  const j = lines.findIndex((l, k) => k > i && l === `${indent}}`);
  expect(j).toBeGreaterThan(i);
  return lines.slice(i, j + 1).join("\n");
}

describe("K18 — 사람 쓰기 길 바이트 동일(838f24421)", () => {
  // 838f24421 `src-tauri/src/viewcore.rs:55-71` 글자 그대로.
  const HUMAN_SEND_PARAMS_1118 = [
    "pub(crate) fn human_send_params(surface_id: u64, text: &str, tok: Option<&str>) -> Value {",
    "    let mut p = json!({",
    '        "surface_id": surface_id,',
    '        "text": text,',
    '        "quiet": true,',
    '        "human": true,',
    '        "queued": false,',
    '        "clear_first": true,',
    '        "refuse_on_approval": true,',
    '        "machine_origin": false,',
    "    });",
    "    if let Some(t) = tok {",
    '        p["owner_token"] = json!(t);',
    '        p["operator_token"] = json!(t);',
    "    }",
    "    p",
    "}",
  ].join("\n");
  // 838f24421 `src-tauri/src/viewcore.rs:164-168` — `chat_send` 사람 갈래(칸 함수 · 소켓 · RPC 이름 · 분류).
  const CHAT_SEND_HUMAN_ARM_1118 = [
    '        "human" => {',
    "            let tok = read_operator_token_for(&sock);",
    "            let params = human_send_params(surface_id, &text, tok.as_deref());",
    '            Ok(classify_send(rpc_full_classified(&sock, "surface.send_text", params).await))',
    "        }",
  ].join("\n");

  it("human_send_params_1118 — `human_send_params` 본문 · `chat_send` 사람 갈래 = 838f24421 글자 그대로", () => {
    const v = rs("src-tauri/src/viewcore.rs");
    expect(block(v, "pub(crate) fn human_send_params(")).toBe(HUMAN_SEND_PARAMS_1118);
    const send = block(v, "pub async fn chat_send(");
    expect(send.startsWith("pub async fn chat_send(socket: Option<String>, surface_id: u64, text: String, kind: String) -> Result<Value, String> {\n    let sock = resolve_socket(&socket);\n    match kind.as_str() {\n")).toBe(true);
    expect(block(send, '        "human" => {')).toBe(CHAT_SEND_HUMAN_ARM_1118);
    // 화면 쪽 사람 말 IPC 칸(core → chat_send) = 1.1.18 꼴 `{socket:null, surfaceId, text, kind:"human"}`.
    expect(read("views/core.ts")).toContain('this.d.invoke("chat_send", { socket: null, surfaceId: m.surface_id, text: msg.text, kind: "human" })');
  });

  // 838f24421 의 두 데몬 파일 sha256(줄 끝 LF · `git show 838f24421:<경로> | shasum -a 256`). 1.1.19 에서 두 파일을 만지는 조각 0(PLAN §3).
  //   이 핀이 붉으면 = 사람 쓰기 길(처리기·writer)이 바뀐 것 — 1.1.19 범위 밖(DESIGN §3-4 K18 · 정밀 검증 2R′ C). 1.1.20 에서 바꿀 때 이 핀을 함께 고친다.
  const DAEMON_1118: Record<string, string> = {
    "src/bin/cysd/handlers.rs": "054415fcf36832b3853e02f0efca98d91f4a6e6600cab422cf060ed88cc4722b",
    "src/bin/cysd/state.rs": "2197b79b44a1708f9dfd0ca9fe7a36948fc0046510d7205841cf3a5e3997e996",
  };
  it("k18_daemon_files_1118 — 데몬 `handlers.rs`·`state.rs` = 838f24421 바이트(diff 0)", () => {
    for (const [p, want] of Object.entries(DAEMON_1118)) {
      const bytes = new TextEncoder().encode(rs(p));
      expect(`${p} ${createHash("sha256").update(bytes).digest("hex")}`).toBe(`${p} ${want}`);
    }
  });
});
