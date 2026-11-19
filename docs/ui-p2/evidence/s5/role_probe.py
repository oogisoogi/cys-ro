#!/usr/bin/env python3
"""대조: 멱등 재반환 다시 기동 뒤 그 좌석 role — 사람 입력 0. 인자 = 작업트리 · 격리 폴더."""
import json, os, socket, subprocess, sys, time, signal
W=sys.argv[1]; R=sys.argv[2]
CYS=f'{W}/target/debug/cys'
subprocess.run(['rm','-rf',R]); os.makedirs(f'{R}/h/.cys/update',exist_ok=True); os.makedirs(f'{R}/bin'); os.makedirs(f'{R}/wk'); os.makedirs(f'{R}/t')
subprocess.run(['cc','-O0','-o',f'{R}/bin/claude',f'{W}/tests/fixtures/fake_claude.c'],check=True)
SOCK=f'{R}/s.sock'
env={'HOME':f'{R}/h','CYS_SOCKET':SOCK,'AITERM_SOCKET':SOCK,'XDG_STATE_HOME':f'{R}/h/st','CYS_UPDATE_STATE_DIR':f'{R}/h/.cys/update',
     'PATH':f'{R}/bin:{W}/target/debug:/usr/bin:/bin:/usr/sbin:/sbin','TMPDIR':f'{R}/t','LANG':'en_US.UTF-8'}
def rpc(method,params=None):
    c=socket.socket(socket.AF_UNIX); c.settimeout(20); c.connect(SOCK)
    c.sendall((json.dumps({'id':1,'method':method,'params':params or {}})+'\n').encode()); buf=b''
    while not buf.endswith(b'\n'):
        d=c.recv(65536)
        if not d: break
        buf+=d
    c.close(); return json.loads(buf)
def cys(*a): return subprocess.run([CYS,*a],env=env,capture_output=True,text=True,timeout=150,stdin=subprocess.DEVNULL)
def row(sid): return next((x for x in rpc('org.status')['result']['surfaces'] if x['surface_id']==sid),None)
ident={}
try:
    t0=time.time()
    while cys('list').returncode!=0:
        if time.time()-t0>60: print('no daemon'); sys.exit(2)
        time.sleep(1)
    time.sleep(2); ident=rpc('system.identify')['result']
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
    print('dead', {k:r.get(k) for k in ('role','released_role','agent_alive','seat')}, round(time.time()-t0,1))
    time.sleep(float(sys.argv[3]) if len(sys.argv)>3 else 0)
    r=row(sid); print('before relaunch', {k:r.get(k) for k in ('role','released_role','agent_alive','seat')}, round(time.time()-t0,1))
    o=cys('launch-agent','--role','master','--agent','claude','--cwd',f'{R}/wk'); print('relaunch rc',o.returncode,o.stdout.strip(),'reuse-msg' , 'created' in o.stderr, round(time.time()-t0,1))
    for _ in range(80):
        r=row(sid)
        if r and r.get('agent_alive') is True: break
        time.sleep(0.5)
    time.sleep(5); r=row(sid)
    print('after', {k:r.get(k) for k in ('surface_id','role','released_role','agent_alive','seat')}, 'masters', [x['surface_id'] for x in rpc('org.status')['result']['surfaces'] if x.get('role')=='master' and not x.get('exited')])
finally:
    try: os.kill(int(ident.get('daemon_pid')),signal.SIGTERM)
    except Exception as e: print('kill fail',e)
