// 조각 4 바깥 증거 — 실제 데몬(격리 HOME) 대상 ConfirmBook.decide 1회 + 같은 판 재클릭(TICKET=cysr-ui-slice4-1118).
// 화면 대신 ConfirmBook 을 그대로 쓴다(그리기 = 신뢰 클릭 판정은 e2e 몫). invoke 대역 = 데몬 소켓 원문 RPC(Tauri feed_reply 와 같은 operator_token 첨부).
// 쓰는 법: CYS_SOCKET=<격리 소켓> bun run real_daemon_drive.ts
import { connect } from "node:net";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { ConfirmBook } from "../../../../../ui/src/views/confirm";
import { boundOf } from "../../../../../ui/src/views/judge/confirms";

const sock = process.env.CYS_SOCKET as string;
const tok = readFileSync(join(dirname(sock), "operator.token"), "utf8").trim();
let n = 0;
const rpcLog: unknown[] = [];
function rpc(method: string, params: Record<string, unknown>): Promise<Record<string, unknown>> {
  return new Promise((res, rej) => {
    const c = connect(sock);
    let buf = "";
    const req = JSON.stringify({ id: ++n, method, params });
    c.on("connect", () => c.write(req + "\n"));
    c.on("data", (d) => {
      buf += d.toString("utf8");
      const i = buf.indexOf("\n");
      if (i >= 0) {
        const line = buf.slice(0, i);
        rpcLog.push({ method, req: method === "feed.reply" ? req.replace(tok, "<operator.token>") : req, resp_bytes: Buffer.byteLength(line), resp: line });
        c.end();
        try {
          res(JSON.parse(line));
        } catch (e) {
          rej(e);
        }
      }
    });
    c.on("error", rej);
  });
}
const calls: string[] = [];
const invoke = async (cmd: string, a: Record<string, unknown> = {}): Promise<unknown> => {
  calls.push(cmd);
  if (cmd === "feed_list") {
    const r = await rpc("feed.list", { status: a.status ?? null });
    if (r.ok !== true) throw new Error(String((r.error as { code?: string })?.code));
    return r.result;
  }
  if (cmd === "org_status") {
    const r = await rpc("org.status", {});
    if (r.ok !== true) throw new Error("org");
    return r.result;
  }
  if (cmd === "feed_reply") {
    const r = await rpc("feed.reply", { request_id: a.requestId, decision: a.decision, operator_token: tok });
    if (r.ok !== true) throw `${(r.error as { code?: string })?.code}: ${(r.error as { message?: string })?.message}`;
    return null;
  }
  throw new Error(cmd);
};
const mem = new Map<string, string>();
const book = new ConfirmBook({ invoke, now: () => Date.now(), store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v) } }, () => {});
const feed = await invoke("feed_list", { status: "pending" });
const org = await invoke("org_status");
book.observe(feed, org, null); // 격리 데몬 = 마스터 좌석 없음(멈춤 갈래 no_master)
const band = book.band();
console.log("BAND", JSON.stringify(band.items.map((x) => ({ kind: x.kind, stall: x.kind === "helper" ? x.stall : null, cmd: x.kind !== "ask" ? x.a.command : null }))));
const it = band.items.find((x) => x.kind === "helper");
if (!it || it.kind !== "helper") {
  console.log("NO_ITEM");
  process.exit(2);
}
const bound = boundOf(it.a);
const c0 = calls.length;
await book.decide(bound, "allow");
console.log("FIRST", JSON.stringify({ notice: book.notice, calls: calls.slice(c0), decision: book.decisions.at(-1) }));
const c1 = calls.length;
await book.decide(bound, "allow"); // 같은 판 재클릭 — 이미 처리됨
console.log("SECOND", JSON.stringify({ notice: book.notice, calls: calls.slice(c1), feed_reply_calls: calls.slice(c1).filter((x) => x === "feed_reply").length, decision: book.decisions.at(-1) }));
console.log("RPCLOG", JSON.stringify(rpcLog));
