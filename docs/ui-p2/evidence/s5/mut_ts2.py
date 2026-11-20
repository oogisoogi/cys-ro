import subprocess, os, sys
ROOT=str(__import__('pathlib').Path(__file__).resolve().parents[4])
J='ui/src/views/judge/revive.ts'; B='ui/src/views/revive.ts'; G='ui/src/views/judge/gate.ts'
M=[
 ('N1 gate_wait 잠금 지움', B, 'this.phase.kind === "gate_wait" || (this.phase.kind', '(this.phase.kind'),
 ('N2 생성 시각 대조 지움', J, '  if (r.created_at !== old.created_at) return null;', ''),
 ('N3 30초 사람 입력 막기 지움', J, ' || r.human_idle_secs === undefined || (r.human_idle_secs !== null && r.human_idle_secs < HUMAN_QUIET_SECS);', ';'),
 ('N4 등록 없는 빈 좌석 판정 지움', J, 'if (vacantNoMetaEvidence(m) && sustained', 'if (false && sustained'),
 ('N5 깨움 시각 저장 지움', B, '    this.storeSet(WAKE_AT_KEY, String(at));', ''),
 ('N6 초 버림 보정 지움', J, '(m.idle_secs + 1) * 1000 < now - wakeAt', 'm.idle_secs * 1000 < now - wakeAt'),
 ('N7 같은 좌석 되살림 성공 지움', J, 'return m.surface_id !== beforeSid || !beforeAlive;', 'return m.surface_id !== beforeSid;'),
 ('N8 앱 수명 복원 값 무시', B, 'return this.restoring || this.d.restoring?.() === true;', 'return this.restoring;'),
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
