// update-worker — `jarvis.godmeyou.kr/update/*` 전용 읽기 워커(1.1.8 U3 2판 · master 결정 ① [master#8db3b908]).
//
// 왜 따로 있나: 사이트 워커(jarvis-site · 정적 자산 = 사이트 전체)로 봉투를 게시하면 갱신 게시 = 사이트 전체 배포가 된다
//   (codex 1R #9 · HANDOFF-U3 §3 ①). 이 워커는 R2 버킷만 읽는다 — 쓰기 0 · 비밀 0 · 게시 = master 로컬 publish-site.py --r2.
//
// 저장 배치(scripts/update/store.py · publish-site.py 와 같은 키):
//   obj/<sha256>                         불변 객체(본문·서명 바이트)
//   ptr/update/<c>/<ch>.json · ptr/update/revocations.json   {json, sig, json_sha256, sig_sha256, …} — 쌍을 한 번에 가리키는 포인터
//   ptr/update/<c>/releases/_gen          보관소 세대 포인터 {max_seq, seqs: {"<seq>": 포인터}}(3판 · 포인터+색인 한 객체 · CAS 한 번)
// 공개 경로(설계 AUTO-UPDATE-118 §4-4 홉 「피드·폐기문·본문 보관소」 · 그 밖 = 404):
//   /update/<cysr|agora-client>/<stable|next>.json(.minisig)        봉투        Cache-Control: no-store
//   /update/revocations.json(.minisig)                              폐기문      Cache-Control: no-store
//   /update/<cysr|agora-client>/releases/<seq>.json(.minisig)       보관소      immutable(한 번 게시하면 바뀌지 않음)
// 무결성: 포인터가 가리키는 **두 객체 모두**(본문·서명)의 sha256 = 포인터 값이어야 어느 쪽이든 내보낸다 — 하나라도 다르면
//   둘 다 502(codex 2R · 쌍의 한쪽만 나가는 일 0 · 조용히 다른 바이트를 주지 않는다).

const ROUTES = [
  { re: /^\/update\/(cysr|agora-client)\/(stable|next)\.json(\.minisig)?$/, cache: "no-store" },
  { re: /^\/update\/revocations\.json(\.minisig)?$/, cache: "no-store" },
  { re: /^\/update\/(cysr|agora-client)\/releases\/[0-9]+\.json(\.minisig)?$/, cache: "public, max-age=31536000, immutable" },
];

const BASE_HEADERS = { "X-Content-Type-Options": "nosniff", "X-Cys-Update-Worker": "1" };

function plain(status, text) {
  return new Response(text + "\n", {
    status,
    headers: { ...BASE_HEADERS, "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" },
  });
}

async function sha256hex(buf) {
  const d = await crypto.subtle.digest("SHA-256", buf);
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "HEAD") return plain(405, "method not allowed");
    // 원문 경로에서 인코딩된 구분자·점 조각을 먼저 거부(정규화 전 · §4-4 「%2F 등 인코딩된 구분자 거부」).
    const raw = request.url.slice(request.url.indexOf("/", request.url.indexOf("//") + 2)).split("?")[0];
    if (raw.includes("%") || raw.includes("//") || /\/\.\.?(\/|$)/.test(raw)) return plain(404, "not found");
    const path = new URL(request.url).pathname;
    const route = ROUTES.find((r) => r.re.test(path));
    if (!route) return plain(404, "not found");
    const isSig = path.endsWith(".minisig");
    const rel = isSig ? path.slice(0, -".minisig".length) : path;
    const arch = rel.match(/^\/update\/([a-z-]+)\/releases\/([0-9]+)\.json$/);
    const ptrObj = await env.UPDATE_BUCKET.get(arch ? `ptr/update/${arch[1]}/releases/_gen` : "ptr" + rel);
    if (!ptrObj) return plain(404, "not found");
    let ptr;
    try {
      ptr = JSON.parse(await ptrObj.text());
      if (ptr && ptr.tombstone === true) ptr = null; // 묘비 = 없음(4판 · 삭제 대신 조건부 PUT)
      else if (arch) ptr = Object.hasOwn(ptr.seqs || {}, arch[2]) ? ptr.seqs[arch[2]] : null;
    } catch {
      return plain(502, "bad pointer");
    }
    if (!ptr) return plain(404, "not found");
    const pair = {};
    for (const [k, h] of [["json", "json_sha256"], ["sig", "sig_sha256"]]) {
      const key = ptr[k], want = ptr[h];
      if (typeof key !== "string" || typeof want !== "string" || !/^[0-9a-f]{64}$/.test(want) || key !== "obj/" + want)
        return plain(502, "bad pointer");
      const obj = await env.UPDATE_BUCKET.get(key);
      if (!obj) return plain(502, "object missing");
      const buf = await obj.arrayBuffer();
      if ((await sha256hex(buf)) !== want) return plain(502, "object digest mismatch");
      pair[k] = buf;
    }
    const body = isSig ? pair.sig : pair.json;
    const want = isSig ? ptr.sig_sha256 : ptr.json_sha256;
    const headers = {
      ...BASE_HEADERS,
      "Content-Type": isSig ? "text/plain; charset=utf-8" : "application/json",
      "Cache-Control": route.cache,
      ETag: '"' + want + '"',
      "Content-Length": String(body.byteLength),
    };
    return new Response(request.method === "HEAD" ? null : body, { status: 200, headers });
  },
};
