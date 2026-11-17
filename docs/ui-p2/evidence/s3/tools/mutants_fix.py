# 조각 3 고침(TICKET=cysr-ui-slice3-fix-1118) 뮤턴트 — 앞 좌석 41종(mutants.py 그대로) + 검증 지적 A~F·H · 시험 구멍 O11·O13·O14 새 조건.
# 실행: python3 docs/ui-p2/evidence/s3/tools/mutants_fix.py   (시험 = judge·core·slice3·msgharness·slice3fix)
import re, subprocess, pathlib
ui = pathlib.Path(__file__).resolve().parents[5] / "ui"
TESTS = ["src/views/judge/judge.test.ts", "src/views/core.test.ts", "src/views/slice3.test.ts", "src/views/msgharness.test.ts", "src/views/slice3fix.test.ts"]

def run():
    r = subprocess.run(["bun", "test", *TESTS], cwd=ui, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    m = re.search(r"(\d+) fail", r.stdout + r.stderr)
    return int(m.group(1)) if m else -1

F = {
    "msgstep": ui / "src/views/judge/msgstep.ts",
    "autostep": ui / "src/views/judge/autostep.ts",
    "core": ui / "src/views/core.ts",
    "outbound": ui / "src/views/judge/outbound.ts",
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
    # ---- (고침) 검증 시험 구멍 D ----
    ("core", "O11 겹침 판정에서 보내는 중 제외", 'new Set<Step>(["sending", "injected", "checking", "slow", "queued_hold"])', 'new Set<Step>(["injected", "checking", "slow", "queued_hold"])'),
    ("core", "O14 「이 말 보내기」가 클릭 대상 아닌 말에도(needsClick 검사 제거)", "    if (!needsClick(m)) return;\n", ""),
    ("core", "O13 다시 보내기의 쓰는 중 검사 제거", "    if (!m || !canRetry(m) || this.writing) return;", "    if (!m || !canRetry(m)) return;"),
    # ---- A 감싼 붙여넣기 ----
    ("msgstep", "A 감싼 꼴을 전문 일치로 안 봄", "if (normRecordText(r.text) === m.text || wrappedIs(r.text, m.text)) return true;", "if (normRecordText(r.text) === m.text) return true;"),
    ("msgstep", "A 속 글을 다듬어 비교(글자 하나까지 아님)", "return w !== null && w[2] === text;", "return w !== null && normRecordText(w[2]) === text;"),
    ("msgstep", "A 여닫는 id 같음 검사 제거", '<\\/pasted_content id="\\1">', '<\\/pasted_content id="[0-9A-Za-z]{1,32}">'),
    ("msgstep", "A 앞 고정(^) 제거 = 감싼 밖 앞글 허용", 'PASTE_WRAP = /^\\n\\n<pasted', 'PASTE_WRAP = /\\n\\n<pasted'),
    ("msgstep", "A 글 조각의 감싼 꼴 제외", "normRecordText(p) === m.text || wrappedIs(p, m.text));", "normRecordText(p) === m.text);"),
    # ---- B 고리 · 시각순 ----
    ("msgstep", "B 안 묶인 답에 기록 시각 안 붙임", "stray.push(Number.isNaN(at) ? { uuid: r.uuid, text: r.text } : { uuid: r.uuid, text: r.text, at });", "stray.push({ uuid: r.uuid, text: r.text });"),
    ("core", "B 시각 없는 답에 읽은 시각 안 붙임", ".map((x) => (x.at === undefined ? { ...x, at: readAt } : x));", ";"),
    ("core", "B 안 묶인 답을 사람 말 뒤에 몰아 그림(logOrder 끼우기 제거)", "    while (k < timed.length && (timed[k].at as number) < t) out.push({ kind: \"stray\", r: timed[k++] });\n", ""),
    # ---- C 보내는 중 짝 · 소비 안 함 ----
    ("msgstep", "C 짝 후보에서 보내는 중 제외", 'new Set<Step>(["sending", "injected", "checking", "slow"])', 'new Set<Step>(["injected", "checking", "slow"])'),
    ("msgstep", "C 짝 없는 사람 레코드도 소비", "    const pendingHuman = r.role === \"user\" && r.text !== null;", "    const pendingHuman = false;"),
    ("msgstep", "C 짝 없는 사람 레코드를 다시 대어 볼 목록에 안 넣음", "        unmatched.push(r);\n", ""),
    ("msgstep", "C 다시 대기: 단계 검사 제거", "      if (!AWAITING.has(m.step) || m.userUuid ||", "      if (m.userUuid ||"),
    ("msgstep", "C 다시 대기: 가장 먼저 보낸 말 대신 처음 찾은 말", "      if (hit < 0 || (out[hit].sentAt as number) > m.sentAt) hit = i;", "      if (hit < 0) hit = i;"),
    ("msgstep", "C 다시 대기: 시각 검사 제거", " || !recordAfter(r, m.sentAt) || !userRecordMatches(m, r)) continue;", " || !userRecordMatches(m, r)) continue;"),
    ("core", "C 말 단계가 바뀔 때 다시 대기 안 함", "    if (this.pendingUser.length) {", "    if (false) {"),
    # ---- E / ! 막기 ----
    ("outbound", "E 서식 글자(Cf) 안 뗌", "\\s\\p{Cf}\\p{Mn}", "\\s\\p{Mn}"),
    ("outbound", "E 결합 글자(Mn) 안 뗌", "\\p{Cf}\\p{Mn}\\p{Zs}", "\\p{Cf}\\p{Zs}"),
    ("outbound", "E 채움 글자(U+3164 등) 안 뗌", "\\u115F\\u1160\\u3164\\uFFA0\\u2800]", "]"),
    ("outbound", "E NEL·세로 탭·폼 피드를 줄 나눔으로 안 봄", 'unixed.replace(CHECK_BREAK_BEFORE_SANITIZE, "\\n")', "unixed"),
    ("outbound", "E U+2028/U+2029 를 줄 나눔으로 안 봄", "const CHECK_LINES = /[\\n\\u2028\\u2029]/;", "const CHECK_LINES = /\\n/;"),
    ("outbound", "E 둘째 줄은 옛 규칙(공백·탭만 떼고 /)", "  if (!laterSlashSafe && lines.slice(1).some(leadsCommand))", "  if (!laterSlashSafe && lines.slice(1).some((l) => l.replace(/^[ \\t]+/, \"\").startsWith(\"/\")))"),
    # ---- F 시간 상한 ----
    ("core", "F 재조회 시간 상한 제거", "    const r = await this.bounded(this.fetchFresh());", "    const r = await this.fetchFresh();"),
    ("core", "F 시간 상한 넘김을 붙잡지 않음(문턱 코드로만)", "      if (fresh.timedOut) {", "      if (false) {"),
    ("core", "F 쓰기 직전 시작점 잡기 시간 상한 제거", "        const init = await this.bounded(this.initOffset());", "        const init = await this.initOffset();"),
    ("core", "F 조회 고리는 상한 없이", "      const fresh = await this.freshBounded(); // (조각 3 고침", "      const fresh = await this.fetchFresh(); // (조각 3 고침"),
    # ---- H 거둠 ----
    ("core", "H 같은 글 전달됨이어도 다시 보내기 허용", "    if (sameTextDelivered(this.s.msgs, m.text, m.id)) {", "    if (false) {"),
    ("core", "H 자기 자신도 셈", "  return msgs.some((m) => m.id !== exceptId && m.text === text && (m.step === \"delivered\"", "  return msgs.some((m) => m.text === text && (m.step === \"delivered\""),
    # ---- codex 1R(e8ddaf65 BLOCK) 고침 ----
    ("msgstep", "codex① 본 시각 뒤에 보낸 말에도 짝(보내기 전 레코드가 근거)", " || m.sentAt > p.seenAt", ""),
    ("core", "codex② 늦은 시작점 조회도 offset 을 바꿈(세대 검사 제거)", "      if (gen !== this.initGen) return; // (codex 1R major)", "      // (gen 검사 제거) // (codex 1R major)"),
    ("core", "codex③ 안 묶인 답 시각 정렬 제거", ".sort((a, b) => (a.at as number) - (b.at as number)); // (codex 1R minor)", "; // (codex 1R minor)"),
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
