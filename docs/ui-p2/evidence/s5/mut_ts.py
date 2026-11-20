import subprocess, os, sys
ROOT=str(__import__('pathlib').Path(__file__).resolve().parents[4])
J='ui/src/views/judge/revive.ts'; B='ui/src/views/revive.ts'; G='ui/src/views/judge/gate.ts'
M=[
 ('M1 never 갈래 지움', J, 'if (d === "agent_never_started") return', 'if (false) return'),
 ('M2 never 사람 입력 무시', J, 'if (old.pending_input_human_bytes !== 0 || old.input_paste_open !== false) return', 'if (false) return'),
 ('M3 거절 사람 사유 무시', J, 'const human = ev.seat_human_recent === true ||', 'const human = false &&'),
 ('M4 자동 재시도 상한 무시', J, 'if (ev.seat_blocked === "seat_not_claimable" && !autoUsed) return "retry";', 'if (ev.seat_blocked === "seat_not_claimable") return "retry";'),
 ('M5 연타 잠금 지움', B, 'if (this.busy) return; // 연타', 'if (false) return; // 연타'),
 ('M6 복원 중 잠금 지움', B, '    if (this.restoring) {\n      // 복원 중', '    if (false) {\n      // 복원 중'),
 ('M7 성공 = 좌석 id 무시', J, 'return !!m && m.surface_id !== beforeSid && m.agent_alive === true', 'return !!m && m.agent_alive === true'),
 ('M8 빈 셸 정리 사람 입력 무시', J, '  if (r.pending_input_human_bytes !== 0 || r.input_paste_open !== false) return null;\n', ''),
 ('M9 짝짓기 늘 참', G, 'return typeof own === "number" && own > 0 &&', 'return true ||'),
 ('M10 깨움 5분 거름 지움', B, 'if (this.lastWakeAt !== null && now - this.lastWakeAt < WAKE_DEDUPE_MS) {', 'if (false) {'),
 ('M11 vacant 본 적 있음 무시', J, 'if (f.seenBefore || f.goneMark) return', 'if (f.goneMark) return'),
 ('M12 관문 오류 = 실패로', J, 'if (s.includes("첫기동 관문")) return "gate_pending";', ''),
 ('M13 사람 클릭 = 새 차례 지움', B, 'if (!auto) this.autoUsed = false;', ''),
 ('M14 R3 묶임 무시', B, 'if (hold > 0) {', 'if (false) {'),
 ('M15 boot-degraded 창 무시', B, 'if (this.lastRestartAt === null || now - this.lastRestartAt > BOOT_DEGRADED_WINDOW_MS) return;', ''),
]
env=dict(os.environ); env['PATH']=os.path.expanduser('~/.bun/bin')+':'+env['PATH']
res=[]
for name,f,a,b in M:
    p=os.path.join(ROOT,f); s=open(p).read()
    if s.count(a)!=1: res.append((name,'NOMATCH',s.count(a))); continue
    open(p,'w').write(s.replace(a,b))
    try:
        r=subprocess.run(['bun','test','src/views/revive.test.ts'],cwd=ROOT+'/ui',env=env,capture_output=True,text=True,timeout=120)
        out=r.stdout+r.stderr
        fails=[l for l in out.splitlines() if l.startswith('(fail)')]
        res.append((name,'RED' if r.returncode!=0 else 'GREEN(생존)',len(fails), fails[:2]))
    finally:
        open(p,'w').write(s)
for x in res: print(x)
