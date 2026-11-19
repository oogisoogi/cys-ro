import subprocess, sys, os
P='/Users/oogisoogi/axdev/.wt/cys-1116-s5/ui/src/views/revive.ts'
orig=open(P).read()
muts={
 'M1 never 닫기를 무조건 close_surface 로': ('invoke("close_surface_if_quiet", { socket: null, surfaceId: seat.sid, expectedCreatedAt: seat.created_at })','invoke("close_surface", { socket: null, surfaceId: seat.sid })'),
 'M2 데몬 거절을 실패로만(쓰다 만 글 안내 끔)': ('if (msg.includes("close_refused") && !msg.includes("created_at_mismatch"))','if (false)'),
 'M3 생성 시각 안 보냄(0)': ('surfaceId: seat.sid, expectedCreatedAt: seat.created_at','surfaceId: seat.sid, expectedCreatedAt: 0'),
 'M4 신원 모름이어도 닫음': ('if (seat === null) {\n          this.setPhase','if (false) {\n          this.setPhase'),
}
env=dict(os.environ, PATH=os.path.expanduser('~/.bun/bin')+':'+os.environ['PATH'])
try:
  for k,(a,b) in muts.items():
    assert orig.count(a)>=1,k
    open(P,'w').write(orig.replace(a,b,1))
    r=subprocess.run(['bun','test','./src/views/revive.test.ts'],cwd='/Users/oogisoogi/axdev/.wt/cys-1116-s5/ui',capture_output=True,text=True,env=env)
    out=r.stdout+r.stderr
    fails=[l for l in out.splitlines() if l.startswith('(fail)')]
    print(k,'rc',r.returncode,'fails',len(fails)); [print('   ',f[:150]) for f in fails[:3]]
finally:
  open(P,'w').write(orig)
