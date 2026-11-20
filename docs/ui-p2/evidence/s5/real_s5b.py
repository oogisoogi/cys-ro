#!/usr/bin/env python3
"""조각 5 후임 실물(격리 HOME cysd · 가짜 claude) — master#565d7c18 §8-3 launch-agent 멱등 재사용 + P1 조건부 닫기. 박사님 데몬·좌석 무접촉."""
import json, os, socket, subprocess, sys, time, threading, signal
W=str(__import__('pathlib').Path(__file__).resolve().parents[4])
R='/private/tmp/claude-501/s5e'
CYS=f'{W}/target/debug/cys'
subprocess.run(['rm','-rf',R]); os.makedirs(f'{R}/h/.cys/update',exist_ok=True); os.makedirs(f'{R}/bin'); os.makedirs(f'{R}/wk')
subprocess.run(['cc','-O0','-o',f'{R}/bin/claude',f'{W}/tests/fixtures/fake_claude.c'],check=True)
SOCK=f'{R}/s.sock'
env={'HOME':f'{R}/h','CYS_SOCKET':SOCK,'AITERM_SOCKET':SOCK,'XDG_STATE_HOME':f'{R}/h/st','CYS_UPDATE_STATE_DIR':f'{R}/h/.cys/update',
     'PATH':f'{R}/bin:{W}/target/debug:/usr/bin:/bin:/usr/sbin:/sbin','TMPDIR':f'{R}/t','LANG':'en_US.UTF-8'}
os.makedirs(env['TMPDIR'])
out=[]; ident={}
def say(*a):
    s=' '.join(str(x) for x in a); print(s,flush=True); out.append(s)
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
def cys(*a,timeout=150):
    return subprocess.run([CYS,*a],env=env,capture_output=True,text=True,timeout=timeout,stdin=subprocess.DEVNULL)
def rows(): return rpc('org.status')['result']['surfaces']
def row(sid): return next((x for x in rows() if x['surface_id']==sid),None)
def wait(pred,secs,what):
    t=time.time()
    while time.time()-t<secs:
        v=pred()
        if v: return v
        time.sleep(0.5)
    say('시간 초과:',what); return None
def screen(sid):
    r=rpc('surface.read_text',{'surface_id':sid})
    return (r.get('result') or {}).get('text','')
def kill_agent(sid):
    spid=next(x for x in rpc('surface.list')['result']['surfaces'] if x['surface_id']==sid)['pid']
    kids=subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True).stdout.split('\n')
    t=[int(l.split()[0]) for l in kids if l.strip() and int(l.split()[1])==spid and l.split()[2].endswith('claude')]
    for p in t: os.kill(p,signal.SIGKILL)
    return spid,t
K=('surface_id','role','released_role','agent_alive','seat','pending_input_bytes','pending_input_human_bytes','input_paste_open','human_idle_secs','created_at')
try:
    t0=time.time()
    while cys('list').returncode!=0:
        if time.time()-t0>60: say('데몬 안 뜸'); sys.exit(2)
        time.sleep(1)
    time.sleep(2)
    ident=rpc('system.identify')['result']; say('데몬 pid',ident.get('daemon_pid'),'· 소켓',SOCK)
    evs=[]
    ep=subprocess.Popen([CYS,'events'],env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    def rd():
        for l in ep.stdout:
            try: evs.append(json.loads(l))
            except Exception: pass
    threading.Thread(target=rd,daemon=True).start()
    T0=time.time()
    o=cys('launch-agent','--role','master','--agent','claude','--cwd',f'{R}/wk')
    say(f'① launch-agent master rc={o.returncode} stdout={o.stdout.strip()[-20:]}')
    m=wait(lambda: next((x for x in rows() if x.get('role')=='master' and x.get('agent_alive') is True),None),40,'마스터 생존')
    sid=m['surface_id']; say('   마스터 행:',{k:m.get(k) for k in K})
    spid,t=kill_agent(sid); say('② 에이전트 죽이기: 셸',spid,'→ 가짜 claude',t)
    d=wait(lambda: (lambda r: r if r and r.get('agent_alive') is False else None)(row(sid)),60,'agent_alive false')
    say('   행:',{k:d.get(k) for k in K} if d else None, '· 경과', round(time.time()-T0,1),'s')
    # ③ 사람 초안(엔터 없음) — 30초 안 다시 기동은 데몬이 먼저 막는다(seat_human_recent) · 30초 뒤(초안은 그대로)는 승계 → 멱등 재반환 → 이번 고침이 막는다
    r=rpc('surface.send_text',{'surface_id':sid,'text':'echo DRAFT-OWNER','human':True,'quiet':True}); say('③ 사람 초안 응답:',json.dumps(r.get('result') or r.get('error'),ensure_ascii=False)[:120])
    o=cys('launch-agent','--role','master','--agent','claude','--cwd',f'{R}/wk')
    say(f'   30초 안 다시 기동 rc={o.returncode} · stderr 끝={o.stderr.strip()[-120:]!r}')
    say('   … 사람 입력 뒤 31초(초안은 줄에 남음)'); time.sleep(31)
    b=row(sid); scr0=screen(sid)
    say('   전 행:',{k:b.get(k) for k in K},'· 생성 뒤',round(time.time()-T0,1),'s')
    o=cys('launch-agent','--role','master','--agent','claude','--cwd',f'{R}/wk')
    a=row(sid); scr1=screen(sid)
    say(f'   다시 기동 rc={o.returncode} stdout={o.stdout.strip()[-20:]!r}')
    say('   stderr 끝:',repr(o.stderr.strip()[-300:]))
    say('   뒤 행:',{k:a.get(k) for k in K} if a else None)
    say('   같은 좌석 남음 =',a is not None and not a.get('exited'),'· 입력줄 바이트 같음 =',a and a.get('pending_input_bytes')==b.get('pending_input_bytes'),'· 화면 같음 =',scr0==scr1,'· 화면 끝 줄 =',repr([l for l in scr1.splitlines() if l.strip()][-1:]))
    # ④ 사람이 초안을 지움(사람 C-u = send_text \x15) → 31초 뒤 다시 기동 = 멱등 재반환 → C-u(권위) 로 비운 뒤 침 → 같은 좌석 되살아남
    r=rpc('surface.send_text',{'surface_id':sid,'text':'\x15','human':True,'quiet':True}); say('④ 사람 C-u 응답:',json.dumps(r.get('result') or r.get('error'),ensure_ascii=False)[:100])
    say('   … 31초'); time.sleep(31)
    b=row(sid); say('   전 행:',{k:b.get(k) for k in K},'· 생성 뒤',round(time.time()-T0,1),'s')
    o=cys('launch-agent','--role','master','--agent','claude','--cwd',f'{R}/wk')
    say(f'   다시 기동 rc={o.returncode} stdout={o.stdout.strip()[-20:]!r}')
    say('   stderr 끝:',repr(o.stderr.strip()[-200:]))
    n=wait(lambda: (lambda r: r if r and r.get('agent_alive') is True else None)(row(sid)),40,'같은 좌석 되살아남')
    say('   뒤 행:',{k:n.get(k) for k in K} if n else {k:row(sid).get(k) for k in K})
    time.sleep(5)
    say('   5초 뒤 좌석 수(마스터):',sum(1 for x in rows() if x.get('role')=='master' and not x.get('exited')),'· 행',{k:row(sid).get(k) for k in K},'· 사건 role.claim_denied',[e['payload'].get('seat_human_recent') for e in evs if e.get('name')=='role.claim_denied'])
    say('   role·seat 사건:',json.dumps([(e.get('name'),{k:e.get('payload',{}).get(k) for k in ('role','surface_id','from','to','reason','holder','new_surface','old_surface','cause')}) for e in evs if any(w in (e.get('name') or '') for w in ('role.','takeover','seat.','restore','released'))],ensure_ascii=False)[:1500])
    # ⑤ P1 조건부 닫기 실물 — 사람 초안이 있는 좌석 · 생성 시각 다름 = 닫지 않음 / 빈 줄 · 조용함 = 닫음
    w=cys('launch-agent','--role','worker','--agent','claude','--cwd',f'{R}/wk')
    wk=wait(lambda: next((x for x in rows() if x.get('role')=='worker' and x.get('agent_alive') is True),None),40,'워커 생존')
    ws=wk['surface_id']
    q=lambda at: rpc('surface.close',{'surface_id':ws,'if_quiet':True,'expected_created_at':at})
    r=q(wk['created_at']+5); say('⑤ 조건부 닫기 · 생성 시각 다름:',json.dumps(r.get('error'),ensure_ascii=False)[:140])
    rpc('surface.send_text',{'surface_id':ws,'text':'half','human':True,'quiet':True})
    r=q(wk['created_at']); say('   사람 초안:',json.dumps(r.get('error'),ensure_ascii=False)[:140],'· 좌석 남음 =',row(ws) is not None)
    rpc('surface.send_text',{'surface_id':ws,'text':'\x15','human':True,'quiet':True})
    r=q(wk['created_at']); say('   비운 직후(30초 안 사람 입력):',json.dumps(r.get('error'),ensure_ascii=False)[:140])
    say('   … 31초 조용히')
    time.sleep(31)
    r=q(wk['created_at']); say('   조용함:',json.dumps(r.get('result') or r.get('error'),ensure_ascii=False)[:140],'· 좌석 없음 =',row(ws) is None)
    say('   사건 surface.close_if_quiet_denied:',[e['payload'].get('reason') for e in evs if e.get('name')=='surface.close_if_quiet_denied'])
    ep.terminate()
finally:
    open(f'{W}/docs/ui-p2/evidence/s5/real-daemon-s5b.txt','w').write('# 조각 5 후임 실물 — 격리 HOME cysd(이 작업트리 빌드) · 가짜 claude · '+time.strftime('%Y-%m-%d %H:%M')+'\n'+'\n'.join(out)+'\n')
    try: os.kill(int(ident.get('daemon_pid')),signal.SIGTERM)
    except Exception as e: print('데몬 종료 실패',e)
