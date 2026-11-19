import subprocess, os, sys
ROOT=str(__import__('pathlib').Path(__file__).resolve().parents[4])
J='ui/src/views/judge/revive.ts'; B='ui/src/views/revive.ts'; G='ui/src/views/judge/gate.ts'
M=[
 ('R1 걸쇠 OR 복귀', B, 'return this.d.restoring ? this.d.restoring() === true : this.restoring;', 'return this.restoring || this.d.restoring?.() === true;'),
 ('R2 증거 종류 바뀌어도 이어 셈', B, 'kind !== null && kind === this.emptyKind ? (this.neverSince ?? now)', 'kind !== null ? (this.neverSince ?? now)'),
 ('R3 같은 좌석 신원 무시', J, 'sustained && f.seenSame === true)', 'sustained && (f.seenBefore || f.goneMark))'),
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
