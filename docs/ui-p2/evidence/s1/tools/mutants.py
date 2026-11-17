# 조각 1 뮤턴트 — 소스를 하나씩 바꿔 bun 시험이 붉어지는지(매번 원복 · 마지막 줄 「원복 확인: True True True」). 실행: python3 docs/ui-p2/evidence/s1/tools/mutants.py
import re, subprocess, pathlib, sys
ui = pathlib.Path(__file__).resolve().parents[5] / "ui"
gate = ui/"src/views/judge/gate.ts"
src = gate.read_text()
body = src[src.index("export function sendGate"):src.index("export function masterRowOf")]
lines = [l for l in body.split("\n") if "return verdict(" in l]
res = []
def run():
    r = subprocess.run(["bun","test","src/views/judge/judge.test.ts","src/views/core.test.ts"],cwd=ui,capture_output=True,text=True)
    m = re.search(r"(\d+) fail", r.stdout+r.stderr)
    return int(m.group(1)) if m else -1
for l in lines:
    gate.write_text(src.replace(l, "  // MUTANT " + l.strip(), 1))
    try:
        res.append((l.strip()[:90], run()))
    finally:
        gate.write_text(src)
core = ui/"src/views/core.ts"
csrc = core.read_text()
muts = [
  ("core: 관측 유효시간 검사 제거", "const stale = this.d.now() - t0 > OBS_MAX_MS;", "const stale = false;"),
  ("core: 세션 소비 집합 대신 빈 집합", "applyRecords(this.s.msgs, recs, this.consumed)", "applyRecords(this.s.msgs, recs, new Set())"),
  ("core: 복원 말 내부 id 대신 저장소 id", "msgs.push({ id: `r${msgs.length + 1}`, text: x.text", "msgs.push({ id: String((it as { id?: unknown }).id), text: x.text"),
  ("core: 복원 말 자동 제출 허용(RESTORED 거름 제거)", "m.step === \"held\" && m.code !== RESTORED && (m.notBefore", "m.step === \"held\" && (m.notBefore"),
  ("core: 보내는 중 영속 실패해도 씀", "notBefore: undefined })) {", "notBefore: undefined }) && false) {"),
  ("core: reset 무시", "        if (r.reset === true) {", "        if (false) {"),
  ("core: 문턱 거부 분기 제거", "      if (!g.ok) {\n", "      if (false) {\n"),
  ("core: 쓰기 직전 재조회 대신 들고 있던 값", "      let fresh = await this.fetchFresh(); // ★쓰기 직전 재조회 1회(3초 목록을 믿지 않음)\n", "      let fresh = { master: this.s.master, approvals: [] as number[] };\n"),
  ("core: 불명도 다시 보내기 허용(uncertain→failed)", 'const step = stepFromOutcome(r.outcome);', 'const step = r.outcome === "uncertain" ? "failed" : stepFromOutcome(r.outcome);'),
]
for name, a, b in muts:
    assert csrc.count(a)==1, name
    core.write_text(csrc.replace(a,b,1))
    try:
        res.append((name, run()))
    finally:
        core.write_text(csrc)
vc = pathlib.Path(__file__).resolve().parents[5] / "src-tauri/src/viewcore.rs"
vsrc = vc.read_text()
a='        "refuse_on_approval": true,\n'
assert vsrc.count(a)==1
vc.write_text(vsrc.replace(a,'        "refuse_on_approval": false,\n',1))
try:
    r = subprocess.run(["bun","test","src/views/registry.test.ts"],cwd=ui,capture_output=True,text=True)
    m = re.search(r"(\d+) fail", r.stdout+r.stderr); res.append(("viewcore.rs: refuse_on_approval false (bun 정적 핀)", int(m.group(1)) if m else -1))
finally:
    vc.write_text(vsrc)
for n,f in res: print(f"{'RED ' if f>0 else 'GREEN!'} fail={f}  {n}")
print("원복 확인:", gate.read_text()==src, core.read_text()==csrc, vc.read_text()==vsrc)
