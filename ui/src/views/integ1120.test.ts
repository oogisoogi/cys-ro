// (TICKET=cysr-1116-integ-1120) 통합 의미 충돌 시험 — s2 「데몬 사건 단일 입구(core.ingest)」 × s79 조각 7 「skill.run_finished 결과 카드」.
//   s2 가 views/index.ts 에서 listenDaemon·defaultSlug 배선을 걷어 사건이 ingest 로만 들어온다 → 결과 장부(ResultBook)도 ingest 에서 받아야 한다.
//   s79 의 뜻(구독은 붙어 있는 동안만 = 대화 화면 · 작업 화면 살핌) 그대로: 붙기 전 사건은 결과 장부에 안 간다.
//   대역 = 앱 배선 꼴(views/index.ts 와 같이 listenDaemon·defaultSlug 없음).
import { describe, expect, it } from "bun:test";
import { ChatCore, type Deps } from "./core";
import { visibleResults } from "./judge/results";

function appShapedCore() {
  const mem = new Map<string, string>();
  const deps: Deps = {
    invoke: async (cmd) => {
      if (cmd === "home_dir_path") return "/Users/user";
      if (cmd === "chat_transcript") return { status: "ok", session_id: "s", next_offset: 0, size: 0, records: [] };
      if (cmd === "org_status") return { surfaces: [] };
      if (cmd === "feed_list") return { items: [] };
      if (cmd === "list_dir") return [];
      return null;
    },
    now: () => 10_000_000,
    setTimeout: () => 0,
    clearTimeout: () => {},
    store: { get: (k) => mem.get(k) ?? null, set: (k, v) => void mem.set(k, v), remove: (k) => void mem.delete(k) },
    working: () => false,
  };
  return new ChatCore(deps);
}
const flush = async () => {
  for (let i = 0; i < 30; i++) await Promise.resolve();
};
const ev = (slug: string) => ({ name: "skill.run_finished", socket_slug: slug, payload: { run_id: "r1", status: "done", artifact_dir: "/Users/user/runs/r1" } });

describe("(integ-1120) s2 ingest × s79 결과 카드", () => {
  it("앱 배선 꼴(listenDaemon 없음): 대화 화면이 붙은 뒤 ingest 로 온 본부 skill.run_finished = 결과 카드", async () => {
    const core = appShapedCore();
    core.attach();
    await flush();
    core.ingest(ev("hq-1"), "hq-1");
    expect(visibleResults(core.results.items).map((r) => [r.path, r.source])).toEqual([["/Users/user/runs/r1", "skill"]]);
  });
  it("붙기 전(대화 화면을 한 번도 안 켬) 사건 = 결과 장부에 안 감(s79 구독 수명 그대로) · 부서 slug = 버림", async () => {
    const core = appShapedCore();
    core.ingest(ev("hq-1"), "hq-1");
    core.attach();
    await flush();
    expect(core.results.items.length).toBe(0);
    core.ingest(ev("dept-x"), "hq-1");
    expect(core.results.items.length).toBe(0);
  });
});
