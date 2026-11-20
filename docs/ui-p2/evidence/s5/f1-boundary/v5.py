#!/usr/bin/env python3
"""s5 독립 검증 실물 — 격리 HOME cysd(검증 트리 빌드) · 가짜 claude. 실사용 데몬 접촉 0(소켓 단언)."""
import json, os, socket, subprocess, sys, time, threading, signal, argparse
ap=argparse.ArgumentParser()
ap.add_argument('--tag',required=True); ap.add_argument('--grace',type=float,default=None)
ap.add_argument('--offset',type=float,default=0.0, help='사망 관측 뒤 다시 기동까지 초')
ap.add_argument('--mode',default='reuse',choices=['reuse','ttl','concurrent','control','draft','draftonly'])
ap.add_argument('--at_create',type=float,default=None,help='생성 뒤 이 초에 다시 기동(ttl 모드)')
a=ap.parse_args()
W=os.environ.get('V5_W') or str(__import__('pathlib').Path(__file__).resolve().parents[4])
R=f'/private/tmp/claude-501/w5-{a.tag}'
CYS=f'{W}/target/debug/cys'
REAL_SOCKS={os.path.expanduser('~/.cys/cys.sock')}
subprocess.run(['rm','-rf',R]); [os.makedirs(f'{R}/{d}',exist_ok=True) for d in ('h/.cys/update','bin','wk','wk2','wk3','t')]
subprocess.run(['cc','-O0','-o',f'{R}/bin/claude',f'{W}/tests/fixtures/fake_claude.c'],check=True)
SOCK=f'{R}/s.sock'
env={'HOME':f'{R}/h','CYS_SOCKET':SOCK,'AITERM_SOCKET':SOCK,'XDG_STATE_HOME':f'{R}/h/st','CYS_UPDATE_STATE_DIR':f'{R}/h/.cys/update',
     'PATH':f'{R}/bin:{W}/target/debug:/usr/bin:/bin:/usr/sbin:/sbin','TMPDIR':f'{R}/t','LANG':'en_US.UTF-8'}
if a.grace is not None: env['CYS_ROLE_RELEASE_GRACE_SECS']=str(a.grace)
out={'tag':a.tag,'mode':a.mode,'grace':a.grace,'offset':a.offset,'at_create':a.at_create,'log':[]}
ident={}
def say(*x): s=' '.join(str(v) for v in x); out['log'].append(f'{time.strftime("%T")} {s}'); print(a.tag,s,flush=True)
def rpc(method,params=None,rid=[0]):
    rid[0]+=1
    c=socket.socket(socket.AF_UNIX); c.settimeout(20); c.connect(SOCK)
    c.sendall((json.dumps({'id':rid[0],'method':method,'params':params or {}})+'\n').encode())
    buf=b''
    while not buf.endswith(b'\n'):
        d=c.recv(65536)
        if not d: break
        buf+=d
    c.close(); return json.loads(buf)
def assert_iso():
    i=rpc('system.identify')['result']
    s=i.get('socket') or i.get('socket_path') or ''
    if (s and os.path.realpath(s)!=os.path.realpath(SOCK)) or os.path.realpath(SOCK) in {os.path.realpath(x) for x in REAL_SOCKS}:
        say('소켓 단언 실패',s); sys.exit(9)
    return i
def cys(*x,timeout=150):
    assert_iso()
    return subprocess.run([CYS,*x],env=env,capture_output=True,text=True,timeout=timeout,stdin=subprocess.DEVNULL)
def rows(): return rpc('org.status')['result']['surfaces']
def row(sid): return next((x for x in rows() if x['surface_id']==sid),None)
def masters(): return [ (x['surface_id'],x.get('agent_alive')) for x in rows() if x.get('role')=='master' and not x.get('exited')]
def roles_map():
    r=rpc('surface.list')['result']['surfaces']; return [(x['surface_id'],x.get('role')) for x in r]
def wait(pred,secs,what):
    t=time.time()
    while time.time()-t<secs:
        v=pred()
        if v: return v
        time.sleep(0.2)
    say('시간 초과:',what); return None
def kill_agent(sid):
    spid=next(x for x in rpc('surface.list')['result']['surfaces'] if x['surface_id']==sid)['pid']
    ps=subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True).stdout.split('\n')
    t=[int(l.split()[0]) for l in ps if l.strip() and int(l.split()[1])==spid and l.split()[2].endswith('claude')]
    for p in t: os.kill(p,signal.SIGKILL)
    return t
def la(cwd): return cys('launch-agent','--role','master','--agent','claude','--cwd',cwd)
try:
    # 데몬 기동(격리) — 첫 호출이 자동 기동
    subprocess.run([CYS,'list'],env=env,capture_output=True,timeout=60)
    wait(lambda: os.path.exists(SOCK),240,'소켓')
    time.sleep(1.5)
    ident=assert_iso(); say('데몬 pid',ident.get('daemon_pid'),'sock',SOCK)
    evs=[]
    ep=subprocess.Popen([CYS,'events'],env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    threading.Thread(target=lambda:[evs.append(dict(json.loads(l),_t=time.time())) for l in ep.stdout if l.startswith('{')],daemon=True).start()
    T0=time.time()
    o=la(f'{R}/wk'); say('① 1차 기동 rc',o.returncode,o.stdout.strip()[-12:])
    m=wait(lambda: next((x for x in rows() if x.get('role')=='master' and x.get('agent_alive') is True),None),40,'마스터 생존')
    A=m['surface_id']; Tc=time.time()
    say('A=',A,'생성 뒤',round(Tc-T0,1))
    if a.mode=='ttl':
        time.sleep(2)
    k=kill_agent(A); say('② kill',k)
    d=wait(lambda: (lambda r: r if r and r.get('agent_alive') is False else None)(row(A)),40,'agent_alive false'); Td=time.time()
    say('   사망 관측 · 생성 뒤',round(Td-T0,1))
    if a.mode=='ttl':
        rem=a.at_create-(time.time()-T0)
        if rem>0: time.sleep(rem)
    else:
        rem=a.offset-(time.time()-Td)
        if rem>0: time.sleep(rem)
    say('③ 다시 기동 직전 · 사망 뒤',round(time.time()-Td,2),'· 생성 뒤',round(time.time()-T0,1),'· row role',row(A).get('role'),'· masters',masters())
    if a.mode=='draftonly':
        r=rpc('surface.send_text',{'surface_id':A,'text':'echo OWNER-DRAFT-한글','human':True,'quiet':True}); say('   사람 초안(다시 기동 없음)',json.dumps(r.get('result') or r.get('error'),ensure_ascii=False))
    if a.mode=='draft':
        r=rpc('surface.send_text',{'surface_id':A,'text':'echo OWNER-DRAFT-한글','human':True,'quiet':True}); say('   사람 초안',json.dumps(r.get('result') or r.get('error'),ensure_ascii=False))
        o=la(f'{R}/wk'); say('   즉시 다시 기동 rc',o.returncode,repr(o.stderr.strip()[-110:]))
        time.sleep(31)
        b=row(A); s0=rpc('surface.read_text',{'surface_id':A})['result'].get('text','')
        o=la(f'{R}/wk'); s1=rpc('surface.read_text',{'surface_id':A})['result'].get('text',''); c=row(A)
        say('   31초 뒤 다시 기동 rc',o.returncode,'stdout',o.stdout.strip()[-12:],repr(o.stderr.strip()[-200:]))
        out['draft']={'rc':o.returncode,'pending_before':(b['pending_input_bytes'],b['pending_input_human_bytes']),'pending_after':(c['pending_input_bytes'],c['pending_input_human_bytes']),'screen_same':s0==s1,'last_line':[l for l in s1.splitlines() if l.strip()][-1:]}
        say('   초안 보존',out['draft'])
    if a.mode in ('reuse','ttl'):
        o=la(f'{R}/wk'); say('   rc',o.returncode,'stdout',o.stdout.strip()[-12:],'stderr끝',repr(o.stderr.strip()[-160:]))
    elif a.mode=='concurrent':
        res={}
        th=[threading.Thread(target=lambda c=c: res.__setitem__(c,la(f'{R}/{c}'))) for c in ('wk','wk2')]
        [t.start() for t in th]; [t.join() for t in th]
        for c,o in res.items(): say('  ',c,'rc',o.returncode,o.stdout.strip()[-12:],repr(o.stderr.strip()[-120:]))
    elif a.mode=='control':
        res={}
        th=[threading.Thread(target=lambda c=c: res.__setitem__(c,la(f'{R}/{c}'))) for c in ('wk2','wk3')]
        [t.start() for t in th]; [t.join() for t in th]
        for c,o in res.items(): say('  ',c,'rc',o.returncode,o.stdout.strip()[-12:],repr(o.stderr.strip()[-120:]))
    T3=time.time(); say('   다시 기동 반환 · 사망 뒤',round(T3-Td,2))
    g=a.grace if a.grace is not None else 60
    settle=max(15, g+10) if a.mode not in ("draft","draftonly") else 150
    time.sleep(settle)
    ms=masters(); out['masters_after']=ms
    out['roles']=roles_map()
    out['role_events']=[(round(e['_t']-Td,2),e.get('name'),e.get('surface_id'),(e.get('payload') or {}).get('role'),(e.get('payload') or {}).get('path') or (e.get('payload') or {}).get('reason')) for e in evs if (e.get('name') or '').startswith('role.')]
    say('④',round(settle),'초 뒤 masters(role=master ∧ !exited)',ms,'· surface.list role',out['roles'])
    say('   role 사건',out['role_events'])
    out['all_events']=[(round(e['_t']-Td,2),e.get('name'),e.get('surface_id'),json.dumps(e.get('payload'),ensure_ascii=False)[:300]) for e in evs]
    out['verdict']='ONE' if len(ms)==1 else ('ZERO' if not ms else 'TWO+')
    say('판정',out['verdict'])
    ep.terminate()
finally:
    try: os.kill(int(ident.get('daemon_pid')),signal.SIGTERM)
    except Exception as e: print('데몬 종료 실패',e)
    json.dump(out,open(os.path.join(os.environ.get('V5_OUT',R),f'res-{a.tag}.json'),'w'),ensure_ascii=False,indent=1)
