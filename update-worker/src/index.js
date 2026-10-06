// update-worker — `jarvis.godmeyou.kr/update/*` 전용 읽기 워커(1.1.8 U3 2판 · master 결정 ① [master#8db3b908]).
//
// 왜 따로 있나: 사이트 워커(jarvis-site · 정적 자산 = 사이트 전체)로 봉투를 게시하면 갱신 게시 = 사이트 전체 배포가 된다
//   (codex 1R #9 · HANDOFF-U3 §3 ①). 이 워커는 R2 버킷만 읽는다 — 쓰기 0 · 비밀 0 · 게시 = master 로컬 publish-site.py --r2.
//
// 저장 배치(scripts/update/store.py · publish-site.py 와 같은 키):
//   obj/<sha256>                         불변 객체(본문·서명 바이트)
//   ptr/<공개 경로>                       {json, sig, json_sha256, sig_sha256, …} — 본문·서명 쌍을 한 번에 가리키는 포인터
// 공개 경로(설계 AUTO-UPDATE-118 §4-4 홉 「피드·폐기문·본문 보관소」 · 그 밖 = 404):
//   /update/<cysr|agora-client>/<stable|next>.json(.minisig)        봉투        Cache-Control: no-store
//   /update/revocations.json(.minisig)                              폐기문      Cache-Control: no-store
//   /update/<cysr|agora-client>/releases/<seq>.json(.minisig)       보관소      immutable(한 번 게시하면 바뀌지 않음)
// 무결성: 객체 바이트의 sha256 = 포인터 값이어야 내보낸다(다르면 502 — 조용히 다른 바이트를 주지 않는다).

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
    const ptrObj = await env.UPDATE_BUCKET.get("ptr" + rel);
    if (!ptrObj) return plain(404, "not found");
    let ptr;
    try {
      ptr = JSON.parse(await ptrObj.text());
    } catch {
      return plain(502, "bad pointer");
    }
    const key = isSig ? ptr.sig : ptr.json;
    const want = isSig ? ptr.sig_sha256 : ptr.json_sha256;
    if (typeof key !== "string" || !/^obj\/[0-9a-f]{64}$/.test(key) || key !== "obj/" + want) return plain(502, "bad pointer");
    const obj = await env.UPDATE_BUCKET.get(key);
    if (!obj) return plain(502, "object missing");
    const body = await obj.arrayBuffer();
    if ((await sha256hex(body)) !== want) return plain(502, "object digest mismatch");
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
