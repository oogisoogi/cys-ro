// 시험 하네스(1.1.8 U3 2판): publish-site.py --fs 가 쓴 저장소 폴더를 가짜 R2 로 삼아 워커를 그대로 부른다.
//   사용: node fs-harness.mjs <저장소 루트> <요청 JSON 배열: [{"method":"GET","url":"https://…"}]>
//   출력: JSON 배열 [{status, headers, sha256, size}] — 시험(scripts/tests/test_update_publish.py)이 판정한다.
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import worker from "../src/index.js";

const [root, reqJson] = process.argv.slice(2);
const bucket = {
  async get(key) {
    if (key.includes("..")) throw new Error("key escapes root: " + key);
    try {
      const buf = await readFile(path.join(root, key));
      return { text: async () => buf.toString("utf8"), arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) };
    } catch (e) {
      if (e.code === "ENOENT") return null;
      throw e;
    }
  },
};
const out = [];
for (const r of JSON.parse(reqJson)) {
  const res = await worker.fetch(new Request(r.url, { method: r.method || "GET" }), { UPDATE_BUCKET: bucket });
  const body = Buffer.from(await res.arrayBuffer());
  out.push({
    status: res.status,
    headers: Object.fromEntries(res.headers.entries()),
    sha256: createHash("sha256").update(body).digest("hex"),
    size: body.length,
  });
}
process.stdout.write(JSON.stringify(out));
