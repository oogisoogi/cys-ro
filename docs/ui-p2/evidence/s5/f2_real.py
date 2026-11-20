#!/usr/bin/env python3
"""F2 실물: 죽은 마스터 좌석에 사람 초안 → phoenix restore --include-master 직접 실행 → 옛 좌석 닫힘·초안 보존 대조. 인자 = 작업트리 · 격리 폴더 · 대기초"""
import json, os, socket, subprocess, sys, time, signal
W=sys.argv[1]; R=sys.argv[2]; WAIT=float(sys.argv[3]) if len(sys.argv)>3 else 31
CYS=f'{W}/target/debug/cys'
subprocess.run(['rm','-rf',R]); [os.makedirs(f'{R}/{d}',exist_ok=True) for d in ('h/.cys/update','bin','wk','t')]
subprocess.run(['cc','-O0','-o',f'{R}/bin/claude',f'{W}/tests/fixtures/fake_claude.c'],check=True)
SOCK=f'{R}/s.sock'
env={'HOME':f'{R}/h','CYS_SOCKET':SOCK,'AITERM_SOCKET':SOCK,'XDG_STATE_HOME':f'{R}/h/st','CYS_UPDATE_STATE_DIR':f'{R}/h/.cys/update',
     'PATH':f'{R}/bin:{W}/target/debug:/usr/bin:/bin:/usr/sbin:/sbin','TMPDIR':f'{R}/t','LANG':'en_US.UTF-8','PHOENIX_CYS':CYS}
def rpc(method,params=None):
    c=socket.socket(socket.AF_UNIX); c.settimeout(20); c.connect(SOCK)
    c.sendall((json.dumps({'id':1,'method':method,'params':params or {}})+'\n').encode()); buf=b''
    while not buf.endswith(b'\n'):
        d=c.recv(65536)
        if not d: break
        buf+=d
    c.close(); return json.loads(buf)
def cys(*a): return subprocess.run([CYS,*a],env=env,capture_output=True,text=True,timeout=200,stdin=subprocess.DEVNULL)
def rows(): return rpc('org.status')['result']['surfaces']
def row(sid): return next((x for x in rows() if x['surface_id']==sid),None)
K=('surface_id','role','agent_alive','seat','exited','pending_input_human_bytes','human_idle_secs')
ident={}
try:
    t0=time.time()
    while cys('list').returncode!=0:
        if time.time()-t0>60: print('no daemon'); sys.exit(2)
        time.sleep(1)
    time.sleep(2); ident=rpc('system.identify')['result']
    assert os.path.realpath(ident.get('socket') or SOCK)==os.path.realpath(SOCK)
    o=cys('launch-agent','--role','master','--agent','claude','--cwd',f'{R}/wk'); print('launch rc',o.returncode,o.stdout.strip())
    sid=1
    for _ in range(80):
        r=row(sid)
        if r and r.get('agent_alive') is True: break
        time.sleep(0.5)
    spid=next(x for x in rpc('surface.list')['result']['surfaces'] if x['surface_id']==sid)['pid']
    for l in subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True).stdout.split('\n'):
        if l.strip() and int(l.split()[1])==spid and l.split()[2].endswith('claude'): os.kill(int(l.split()[0]),signal.SIGKILL)
    for _ in range(120):
        r=row(sid)
        if r and r.get('agent_alive') is False: break
        time.sleep(0.5)
    print('dead',{k:r.get(k) for k in K})
    print('draft',rpc('surface.send_text',{'surface_id':sid,'text':'echo OWNER-DRAFT-한글','human':True,'quiet':True}).get('result'))
    time.sleep(WAIT)
    b=row(sid); print('before phoenix',{k:b.get(k) for k in K}, 'rows',[x['surface_id'] for x in rows() if not x.get('exited')])
    ph=subprocess.run(['python3',f'{W}/cysjavis-pack/bin/javis_phoenix.py','restore','--include-master'],env=env,capture_output=True,text=True,timeout=400,stdin=subprocess.DEVNULL)
    lines=[l for l in (ph.stdout+ph.stderr).splitlines() if any(w in l for w in ('F2','fresh 강등','빈 좌석','좌석 내 재연결','보류','"phoenix_restore"','"completeness"'))]
    print('phoenix rc',ph.returncode); [print('  ',l[:220]) for l in lines[:14]]
    time.sleep(3)
    a=row(sid)
    print('after old seat',{k:a.get(k) for k in K} if a else 'GONE(닫힘)')
    print('after rows',[(x['surface_id'],x.get('role'),x.get('agent_alive')) for x in rows() if not x.get('exited')])
    print('VERDICT old_seat_kept=%s draft_same=%s' % (a is not None and not a.get('exited'), bool(a) and a.get('pending_input_human_bytes')==b.get('pending_input_human_bytes')))
finally:
    try: os.kill(int(ident.get('daemon_pid')),signal.SIGTERM)
    except Exception as e: print('kill fail',e)
