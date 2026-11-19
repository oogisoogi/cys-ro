#!/usr/bin/env python3
"""조각 5 실물(격리 HOME cysd · 가짜 claude · 좌석 죽이기) — 박사님 데몬·좌석 무접촉. 출력 = 증거 글."""
import json, os, socket, subprocess, sys, time, threading, signal
W=str(__import__('pathlib').Path(__file__).resolve().parents[4])
R='/private/tmp/claude-501/s5d'
CYS=f'{W}/target/debug/cys'
subprocess.run(['rm','-rf',R]); os.makedirs(f'{R}/h/.cys/update',exist_ok=True); os.makedirs(f'{R}/bin'); os.makedirs(f'{R}/wk')
subprocess.run(['cc','-O0','-o',f'{R}/bin/claude',f'{W}/tests/fixtures/fake_claude.c'],check=True)
SOCK=f'{R}/s.sock'
env={'HOME':f'{R}/h','CYS_SOCKET':SOCK,'AITERM_SOCKET':SOCK,'XDG_STATE_HOME':f'{R}/h/st','CYS_UPDATE_STATE_DIR':f'{R}/h/.cys/update',
     'PATH':f'{R}/bin:{W}/target/debug:/usr/bin:/bin:/usr/sbin:/sbin','TMPDIR':f'{R}/t','LANG':'en_US.UTF-8'}
os.makedirs(env['TMPDIR'])
out=[]
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
def cys(*a,timeout=120):
    return subprocess.run([CYS,*a],env=env,capture_output=True,text=True,timeout=timeout,stdin=subprocess.DEVNULL)
t0=time.time()
while cys('list').returncode!=0:
    if time.time()-t0>60: say('데몬 안 뜸'); sys.exit(2)
    time.sleep(1)
time.sleep(2)
ident=rpc('system.identify')['result']; say('데몬 pid',ident.get('daemon_pid'),'· 소켓',SOCK)
# 사건 받기(뒤에서)
evs=[]
ep=subprocess.Popen([CYS,'events'],env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
def rd():
    for l in ep.stdout:
        try: evs.append(json.loads(l))
        except Exception: pass
threading.Thread(target=rd,daemon=True).start()
def rows():
    return rpc('org.status')['result']['surfaces']
def by_role(r): return [x for x in rows() if x.get('role')==r and not x.get('exited')]
def counts():
    rs=[x for x in rows() if not x.get('exited')]
    return {k:sum(1 for x in rs if x.get('role')==k) for k in ('master','cso','worker',None)}
for role in ('master','cso','worker'):
    o=cys('launch-agent','--role',role,'--agent','claude','--cwd',f'{R}/wk')
    say(f'launch-agent {role} rc={o.returncode} stdout={o.stdout.strip()[-40:]}')
def wait(pred,secs,what):
    t=time.time()
    while time.time()-t<secs:
        v=pred()
        if v: return v
        time.sleep(0.5)
    say('시간 초과:',what); return None
m=wait(lambda: next((x for x in by_role('master') if x.get('agent_alive') is True),None),40,'마스터 생존')
say('① 마스터 행 가산 칸:',{k:m.get(k) for k in ('surface_id','agent','agent_alive','agent_seen','seat','human_input_stamp','human_idle_secs')})
sid=m['surface_id']
# ② 사람 원자 제출(대화 화면과 같은 꼴) → 응답 차례 = 행 차례
p={'surface_id':sid,'text':'안녕','quiet':True,'human':True,'queued':False,'clear_first':True,'refuse_on_approval':True,'machine_origin':False}
r=rpc('surface.send_text',p); say('② 원자 제출 응답:',json.dumps(r.get('result') or r.get('error'),ensure_ascii=False))
m2=next(x for x in by_role('master')); say('   행 human_input_stamp =',m2.get('human_input_stamp'),'· human_idle_secs =',m2.get('human_idle_secs'))
before=counts(); say('③ 좌석 수(다시 켜기 전):',before)
# ④ 좌석 죽이기 — 마스터 좌석 셸의 자식(가짜 claude) pid 만 골라 끔(이름 일치 종료 아님)
spid=next(x for x in rpc('surface.list')['result']['surfaces'] if x['surface_id']==sid)['pid']
kids=subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True).stdout.split('\n')
targets=[int(l.split()[0]) for l in kids if l.strip() and int(l.split()[1])==spid and l.split()[2].endswith('claude')]
say('④ 좌석 죽이기: 셸 pid',spid,'→ 가짜 claude pid',targets)
for t in targets: os.kill(t,signal.SIGKILL)
dead=wait(lambda: next((x for x in by_role('master') if x['surface_id']==sid and x.get('agent_alive') is False),None),60,'agent_alive false')
say('   행:',{k:dead.get(k) for k in ('agent_alive','agent_seen','seat')} if dead else None)
dm=wait(lambda: [e for e in evs if e.get('name')=='master.deadman'],120,'master.deadman')
say('   master.deadman:',json.dumps([{k:e['payload'].get(k) for k in ('axis','reason')} for e in (dm or [])],ensure_ascii=False))
# ⑤ 다시 켜기 = start_master 와 같은 명령(cys launch-agent --role master) — 사람 입력 없음
pend0=next(x for x in rows() if x['surface_id']==sid).get('pending_input_bytes')
o=cys('launch-agent','--role','master','--agent','claude','--cwd',f'{R}/wk')
say(f'⑤ launch-agent master(다시 켜기) rc={o.returncode} stdout={o.stdout.strip()[-30:]} stderr끝={o.stderr.strip()[-160:]!r}')
nm=wait(lambda: next((x for x in by_role('master') if x.get('agent_alive') is True),None),40,'마스터 다시 생존(같은 좌석 포함)')
say('   다시 켠 마스터:',{k:nm.get(k) for k in ('surface_id','agent_alive','gate_pending','created_at')},'· 같은 좌석 =',nm and nm['surface_id']==sid if nm else None,'· 옛 좌석 행:',{k:v for k,v in next((x for x in rows() if x['surface_id']==sid),{}).items() if k in ('role','exited','seat','pending_input_bytes','pending_input_human_bytes')})
after=counts(); say('   좌석 수(뒤):',after,'· CSO·워커 같음 =',before['cso']==after['cso'] and before['worker']==after['worker'],'· 마스터 1 =',after['master']==1)
say('   role.takeover:',sum(1 for e in evs if e.get('name')=='role.takeover'),'· role.claim_denied:',sum(1 for e in evs if e.get('name')=='role.claim_denied'))
# ⑥ 사람 입력 사유 거절: 새 마스터 에이전트 죽이고, 그 창에 사람 자판 1글자 → 다시 켜기 → claim_denied + seat_human_recent
sid2=nm['surface_id']
spid2=next(x for x in rpc('surface.list')['result']['surfaces'] if x['surface_id']==sid2)['pid']
kids=subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True).stdout.split('\n')
for l in kids:
    if l.strip() and int(l.split()[1])==spid2 and l.split()[2].endswith('claude'): os.kill(int(l.split()[0]),signal.SIGKILL)
wait(lambda: next((x for x in by_role('master') if x['surface_id']==sid2 and x.get('agent_alive') is False),None),60,'둘째 agent_alive false')
r=rpc('surface.send_text',{'surface_id':sid2,'text':'x','human':True,'quiet':True}); say('⑥ 사람 자판 1글자 응답:',json.dumps(r.get('result'),ensure_ascii=False))
nd=len([e for e in evs if e.get('name')=='role.claim_denied'])
o=cys('launch-agent','--role','master','--agent','claude','--cwd',f'{R}/wk')
say(f'   다시 켜기 rc={o.returncode} stderr끝={o.stderr.strip()[-200:]!r}')
time.sleep(1.5)
cd=[e for e in evs if e.get('name')=='role.claim_denied'][nd:]
say('   role.claim_denied:',json.dumps([{k:e['payload'].get(k) for k in ('seat_blocked','seat_human_recent','takeover_cancelled','path')} for e in cd],ensure_ascii=False))
say('   좌석 수:',counts())
# ⑦ S1-10: 빈 셸(에이전트 죽은 좌석)에 원자 제출 → no_agent · 사람 입력 시각 그대로(되돌림)
row=next(x for x in rows() if x['surface_id']==sid2); seq0=row.get('human_input_stamp')
r=rpc('surface.send_text',{**p,'surface_id':sid2})
row=next(x for x in rows() if x['surface_id']==sid2)
say('⑦ 빈 셸 원자 제출:',json.dumps(r.get('error') or r.get('result'),ensure_ascii=False)[:160],'· 표지 전/후',seq0,row.get('human_input_stamp'))
ep.terminate()
open(f'{W}/docs/ui-p2/evidence/s5/real-daemon.txt','w').write('# 조각 5 실물 — 격리 HOME cysd(이 작업트리 빌드) · 가짜 claude(tests/fixtures/fake_claude.c) · 좌석 죽이기 · '+time.strftime('%Y-%m-%d %H:%M')+'\n'+'\n'.join(out)+'\n')
# 정리: 이 격리 데몬만(pid 지정)
try: os.kill(int(ident.get('daemon_pid')),signal.SIGTERM)
except Exception as e: say('데몬 종료 실패',e)
