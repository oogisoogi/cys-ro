# 조각 3 뮤턴트 — 단계 판정 조건을 하나씩 빼거나 바꿔 bun 시험이 붉어지는지(매번 원복 · 마지막 줄 「원복 확인」).
# 실행: python3 docs/ui-p2/evidence/s3/tools/mutants.py   (시험 = judge·core·slice3·msgharness)
import re, subprocess, pathlib
ui = pathlib.Path(__file__).resolve().parents[5] / "ui"
TESTS = ["src/views/judge/judge.test.ts", "src/views/core.test.ts", "src/views/slice3.test.ts", "src/views/msgharness.test.ts"]

def run():
    r = subprocess.run(["bun", "test", *TESTS], cwd=ui, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    m = re.search(r"(\d+) fail", r.stdout + r.stderr)
    return int(m.group(1)) if m else -1

F = {
    "msgstep": ui / "src/views/judge/msgstep.ts",
    "autostep": ui / "src/views/judge/autostep.ts",
    "core": ui / "src/views/core.ts",
}
orig = {k: p.read_text() for k, p in F.items()}
M = [
    ("msgstep", "답하는 중 = 전달 뒤 일함 줄 제거", '    if (m.step === "delivered" && masterWorking === true && m === newest) return { ...m, step: "replying" as Step };\n', ""),
    ("msgstep", "답하는 중을 가장 최근 전달 말에 한정하지 않음(검토 지적 2)", 'masterWorking === true && m === newest)', 'masterWorking === true)'),
    ("msgstep", "답 글 없이 쉬어도 답하는 중 유지(검토 지적 2)", '    if (m.step === "replying" && m.replies.length === 0 && (masterWorking === false || m !== newest)) return { ...m, step: "delivered" as Step };', ''),
    ("msgstep", "전달됨이 돼도 옛 확인 중 안내 유지(검토 지적 4)", "        cand.code = undefined; // (조각 3 · 검토 지적 4)", "        // cand.code = undefined; // (조각 3 · 검토 지적 4)"),
    ("msgstep", "쓰기 직전 거부: 시각 차 허용(1초) 제거", "now - m.sentAt < -REFUSED_AT_WRITE_SKEW_MS ||", "now - m.sentAt < 0 ||"),
    ("msgstep", "무응답 3초 → 확인 중 줄 제거", '    if (m.step === "sending" && m.sentAt !== null && now - m.sentAt >= SENDING_SILENT_MS)', '    if (false)'),
    ("msgstep", "무응답 판정에 보낸 시각 없는 말도(sentAt 검사 제거)", 'm.step === "sending" && m.sentAt !== null && now - m.sentAt >= SENDING_SILENT_MS', 'm.step === "sending" && now - (m.sentAt ?? 0) >= SENDING_SILENT_MS'),
    ("msgstep", "늦은 응답이 근거 단계를 되돌림(EVIDENCED 비확정 유지 제거)", "  if (EVIDENCED.has(cur.step) && !definite) return {};\n", ""),
    ("msgstep", "확정 응답이 짝을 풀지 않음", "  if (EVIDENCED.has(cur.step) && definite) return { step: outcomeStep, userUuid: null, thread: [], replies: [] };\n", ""),
    ("msgstep", "쓰기 직전 거부 표지가 늦은 written 에 지워짐", '  if (cur.step === "checking" && cur.code === "refused_at_write" && !definite) return {};', ""),
    ("msgstep", "쓰기 직전 거부: 좌석 검사 제거", "    if (m.seat !== seat || m.sentAt === null) continue;", "    if (m.sentAt === null) continue;"),
    ("core", "쓰기 직전 거부 사건 시각 = 받은 시각(timestamp 무시 · 검토 지적 5)", "      if (typeof ts !== \"number\" || !Number.isFinite(ts)) return;\n      const next = applyRefusedAtWrite(this.s.msgs, e.surface_id, Math.round(ts * 1000));", "      const next = applyRefusedAtWrite(this.s.msgs, e.surface_id, this.d.now());"),
    ("core", "조회 사이 새 출력 틱 읽기 제거(seed 370)", "((prevWorking !== null && prevWorking !== this.lastWorking) || outputSincePoll)", "(prevWorking !== null && prevWorking !== this.lastWorking)"),
    ("core", "새 출력 판정을 늘 참으로(출력 없는 틱도 읽음 · 4군 ①)", "const outputSincePoll = this.lastPollAt !== null && typeof idle === \"number\" && idle * 1000 < pollAt - this.lastPollAt;", "const outputSincePoll = true;"),
    ("core", "읽는 중 온 읽기 계기를 버림(readAgain 제거)", "      this.readAgain = true; //", "      // this.readAgain = true; //"),
    ("msgstep", "쓰기 직전 거부: 창(5초) 검사 제거", " || now - m.sentAt > REFUSED_AT_WRITE_WINDOW_MS) continue;", ") continue;"),
    ("msgstep", "쓰기 직전 거부: 가장 최근 대신 가장 오래된 말", "    if (pick < 0 || (msgs[pick].sentAt as number) <= m.sentAt) pick = i;", "    if (pick < 0) pick = i;"),
    ("msgstep", "쓰기 직전 거부: 이미 전달된 말도(단계 검사 제거)", '    if (m.step !== "sending" && m.step !== "injected" && m.step !== "checking") continue;', '    if (m.step === "held") continue;'),
    ("autostep", "delivered: 묶음(merged_ids) 무시", 'return p.queue_entry_id === id || ids(p.merged_ids).includes(id) ? { step: "delivered" } : null;', 'return p.queue_entry_id === id ? { step: "delivered" } : null;'),
    ("autostep", "inject_aborted: disposed 를 다시 시도로", '      if (ids(p.disposed_ids).includes(id)) return { step: "failed", why: typeof p.why === "string" ? p.why : "disposed" };\n', ""),
    ("autostep", "inject_aborted: 재시도 중을 실패로", 'return ids(p.merged_ids).includes(id) || p.queue_entry_id === id ? { step: "retrying" } : null;', 'return ids(p.merged_ids).includes(id) || p.queue_entry_id === id ? { step: "failed" } : null;'),
    ("autostep", "write_held 무시", 'return ids(p.entry_ids).includes(id) ? { step: "partial", why: typeof p.reason === "string" ? p.reason : undefined } : null;', "return null;"),
    ("autostep", "write_released 를 못 보냄으로 단정(검토 지적 6)", '{ step: "unknown", why: "released_composer_empty" }', '{ step: "failed", why: "released_composer_empty" }'),
    ("autostep", "dropped 무시", 'return ids(p.queue_entry_ids).includes(id) ? { step: "failed", why: typeof p.reason === "string" ? p.reason : "dropped" } : null;', "return null;"),
    ("autostep", "expired 무시", 'return p.queue_entry_id === id ? { step: "expired", why: "expired" } : null;', "return null;"),
    ("autostep", "expired 를 끝난 실패로(되살림 불가 · 검토 지적 3)", '{ step: "expired", why: "expired" }', '{ step: "failed", why: "expired" }'),
    ("autostep", "parked 를 실패로", 'return ids(p.queue_entry_ids).includes(id) ? { step: "parked" } : null;', 'return ids(p.queue_entry_ids).includes(id) ? { step: "failed" } : null;'),
    ("autostep", "rehomed 무시", '    case "queue.rehomed":\n      return ids(p.queue_entry_ids).includes(id) ? { step: "queued" } : null;', '    case "queue.rehomed":\n      return null;'),
    ("autostep", "revived 무시", '    case "queue.revived":\n      return p.queue_entry_id === id ? { step: "queued" } : null;', '    case "queue.revived":\n      return null;'),
    ("autostep", "starved: 좌석 검사 제거", 'return ev.surfaceId === a.seat && (a.step === "queued" || a.step === "retrying") ? { step: "slow" } : null;', 'return a.step === "queued" || a.step === "retrying" ? { step: "slow" } : null;'),
    ("autostep", "끝난 항목도 바뀜(FINAL 검사 제거)", "    if (FINAL.has(a.step)) return a;\n", ""),
    ("autostep", "거꾸로 온 옛 사건도 반영(seq 검사 제거)", "    if (ev.seq !== null && ev.seq <= a.lastSeq) return a;\n", ""),
    ("core", "같은 말 겹침 막기 제거(accept)", "    if (dupPending(this.s.msgs, text)) {", "    if (false) {"),
    ("core", "겹친 말 「한 번 더」 클릭이 앞 말 확인 중에도 나감", "    if (m.code === DUP && dupPending(this.s.msgs, m.text, m.id)) {", "    if (false) {"),
    ("core", "다시 보내기가 겹침을 안 봄(하네스 seed 131)", "    if (dupPending(this.s.msgs, m.text, m.id)) {\n      // (조각 3", "    if (false) {\n      // (조각 3"),
    ("core", "겹침 판정에서 확인 중 제외", 'new Set<Step>(["sending", "injected", "checking", "slow", "queued_hold"])', 'new Set<Step>(["sending", "injected", "slow", "queued_hold"])'),
    ("core", "겹침 판정에서 자동으로 나갈 붙잡음 제외", "(UNRESOLVED.has(m.step) || autoHeld(m))", "UNRESOLVED.has(m.step)"),
    ("core", "겹친 말을 사람 클릭 없이 자동 제출(needsClick 에서 DUP 제거)", "m.code === RESTORED || m.code === STALE || m.code === DUP", "m.code === RESTORED || m.code === STALE"),
    ("core", "부서 데몬 사건도 받음(소켓 검사 제거)", "    if (this.defaultSlug === null || e.socket_slug !== this.defaultSlug) return;\n", ""),
    ("core", "무응답 3초 타이머 제거", "      const silent = this.d.setTimeout(() => {", "      const silent = ((_f: () => void) => 0)(() => {"),
    ("core", "늦은 응답 합치기 대신 응답 그대로", "      const merged = cur ? mergeOutcome(cur, step) : {};", "      const merged: Partial<Msg> = { step };"),
]
res = []
for key, name, a, b in M:
    src = orig[key]
    assert src.count(a) == 1, (name, src.count(a))
    F[key].write_text(src.replace(a, b, 1))
    try:
        res.append((name, run()))
    finally:
        F[key].write_text(src)
for n, f in res:
    print(f"{'RED ' if f > 0 else 'GREEN!'} fail={f}  {n}")
print("붉음:", sum(1 for _, f in res if f > 0), "/", len(res))
print("원복 확인:", *[F[k].read_text() == orig[k] for k in F])
