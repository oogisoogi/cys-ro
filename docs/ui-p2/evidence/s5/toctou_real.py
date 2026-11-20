#!/usr/bin/env python3
"""①실물: 스냅샷 뒤 사람 입력 → 조건부 회수 거절 / 새 표지 = 닫힘 · phoenix 무초안 빈 좌석 = 조건부 회수 성공. 인자 = 작업트리 · 격리 폴더"""
import json, os, socket, subprocess, sys, time, signal
W=sys.argv[1]; R=sys.argv[2]
CYS=f'{W}/target/debug/cys'
subprocess.run(['rm','-rf',R]); [os.makedirs(f'{R}/{d}',exist_ok=True) for d in ('h/.cys/update','bin','wk','wk2','t')]
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
def row(sid): return next((x for x in rpc('org.status')['result']['surfaces'] if x['surface_id']==sid),None)
def kill_agent(sid):
    spid=next(x for x in rpc('surface.list')['result']['surfaces'] if x['surface_id']==sid)['pid']
    for l in subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True).stdout.split('\n'):
        if l.strip() and int(l.split()[1])==spid and l.split()[2].endswith('claude'): os.kill(int(l.split()[0]),signal.SIGKILL)
ident={}
try:
    t0=time.time()
    while cys('list').returncode!=0:
        if time.time()-t0>60: sys.exit(2)
        time.sleep(1)
    time.sleep(2); ident=rpc('system.identify')['result']
    o=cys('launch-agent','--role','worker','--agent','claude','--cwd',f'{R}/wk'); print('worker',o.returncode,o.stdout.strip())
    ws=int(o.stdout.strip().split(':')[-1])
    time.sleep(3); snap=row(ws); print('snapshot', {k:snap.get(k) for k in ('created_at','human_input_stamp','pending_input_human_bytes','human_idle_secs')})
    rpc('surface.send_text',{'surface_id':ws,'text':'x','human':True,'quiet':True}); rpc('surface.send_text',{'surface_id':ws,'text':'\x15','human':True,'quiet':True})
    print('사람 입력(x + C-u) 뒤 31초'); time.sleep(31)
    now=row(ws); print('now', {k:now.get(k) for k in ('human_input_stamp','pending_input_human_bytes','human_idle_secs')})
    a=cys('close-surface',f'surface:{ws}','--reap','--if-quiet',repr(snap['created_at']),'--if-quiet-stamp',snap.get('human_input_stamp') or '')
    print('① 스냅샷 표지로 조건부 회수 rc',a.returncode,'stderr',a.stderr.strip()[-160:],'· 좌석 남음',row(ws) is not None)
    b=cys('close-surface',f'surface:{ws}','--reap','--if-quiet',repr(snap['created_at']),'--if-quiet-stamp',now.get('human_input_stamp') or '')
    print('   지금 표지로 조건부 회수 rc',b.returncode,b.stdout.strip()[-60:],'· 좌석 없음',row(ws) is None)
    c=cys('close-surface','surface:999','--reap'); print('   칸 없는 호출(종전) 없는 좌석 rc',c.returncode,c.stderr.strip()[-80:])
    # phoenix: 무초안 빈 마스터 좌석 → 조건부 회수 성공 → fresh
    o=cys('launch-agent','--role','master','--agent','claude','--cwd',f'{R}/wk2'); ms=int(o.stdout.strip().split(':')[-1]); print('master',o.returncode,ms)
    time.sleep(3); kill_agent(ms)
    for _ in range(120):
        r=row(ms)
        if r and r.get('agent_alive') is False: break
        time.sleep(0.5)
    ph=subprocess.run(['python3',f'{W}/cysjavis-pack/bin/javis_phoenix.py','restore','--include-master'],env=env,capture_output=True,text=True,timeout=400,stdin=subprocess.DEVNULL)
    lines=[l for l in (ph.stdout+ph.stderr).splitlines() if any(w in l for w in ('F2','fresh 강등','"phoenix_restore"','"completeness"'))]
    print('phoenix rc',ph.returncode); [print('  ',l[:200]) for l in lines[:6]]
    ms_rows=[(x['surface_id'],x.get('role'),x.get('agent_alive')) for x in rpc('org.status')['result']['surfaces'] if not x.get('exited')]
    print('   옛 마스터 좌석',ms,'남음' if row(ms) else '회수됨','· 좌석',ms_rows)
    jp=f'{R}/h/.cys'
    for root,_,fs in os.walk(R):
        for f in fs:
            if f.startswith('journal') and f.endswith('.json'):
                t=open(os.path.join(root,f)).read()
                print('   journal empty_seat_reaped' , 'empty_seat_reaped' in t, '· held', 'empty_seat_reap_held_human_input' in t)
finally:
    try: os.kill(int(ident.get('daemon_pid')),signal.SIGTERM)
    except Exception as e: print('kill fail',e)
