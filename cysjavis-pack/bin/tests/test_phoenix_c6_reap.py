#!/usr/bin/env python3
"""S5 Darwin C6/roster/create/reap integration: exact binaries, one isolated daemon.
Agent spawn/readiness are inert fixtures; C6, roster, create and queue lifecycle are real.
No old harness lifecycle, installed binary fallback, AI launch or live endpoint.
"""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
CYS, CYSD = [REPO / ('target/debug/' + n) for n in ('cys', 'cysd')]
GRACE = 20
# ★(1.1.18 · TICKET=cysr-1118u-debug) surface.create 만 상한 20초 + 같은 idempotency_key 1회 재시도. 깜빡이 서명(11-06~ · 29잡 중 4) =
#   첫 create 가 6초 안에 답하지 못함(PTY 자식은 떴음) · 같은 커밋 재실행 녹 · 로컬 p50 ≈0.2초. 판정은 그대로다.
#   ⚠데몬 idem 캐시는 create 가 **끝날 때** 기록된다(handlers.rs create_idem) — 첫 요청이 아직 도는 중에 같은 키로 다시 부르면 좌석이
#   하나 더 생긴다(실측: 첫 create 를 0.05초에 끊으면 역할 없는 좌석 2개). 그래서 상한을 넘기면 그 첫 요청이 만든 새 좌석을 기다려
#   채택한다(상한 20초 · 전체 시한 안). 다시 부르지 않는다: 40초 뒤에도 첫 요청이 끝났다는 증거가 없어 재요청이 또 중복을 만들 수 있다
#   (codex 1R major) — 안 나타나면 유계 실패. 채택은 manifest create_retries 에 남는다(가려진 지연이 증거에 보이게). 다른 RPC 상한은 6초 그대로.
CREATE_TIMEOUT = 20
DEADLINE = 'S5 body or cleanup deadline'  # SIGALRM 전체 시한의 TimeoutError 문안 — 소켓 타임아웃과 가른다


# Reuse the S7-tested kernel sec+usec identity reader; no harness lifecycle calls.
_hspec = importlib.util.spec_from_file_location('s5_process_identity', REPO/'cysjavis-pack/bin/javis_phoenix_harness.py')
H = importlib.util.module_from_spec(_hspec); _hspec.loader.exec_module(H)


def processes():
    r = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid='], capture_output=True, text=True, check=True, timeout=3)
    return {int(p[0]): int(p[1]) for line in r.stdout.splitlines() if len(p := line.split()) == 2}


def same_process(pid, identity):
    info = H._process_info(pid)
    return info is not None and info[0] == identity


def main():
    if sys.platform != 'darwin':
        print('SKIP: Darwin-only S5 fixture; Windows native remains unrun')
        return 0
    assert CYS.is_file() and CYSD.is_file(), 'S5 requires exact built worktree binaries'
    base = REPO / 'target/u-tmp'
    base.mkdir(parents=True, exist_ok=True)  # a fresh CI runner has no target/u-tmp (release run 39747056302)
    base = base.resolve()
    with tempfile.TemporaryDirectory(prefix='s5n-', dir=base) as temp:
        root = Path(temp).resolve()
        endpoint = root / 'd.sock'
        assert root.parent == base and len(os.fsencode(endpoint)) < 100
        for name in ('home', 'pack', 'ledger', 'tmp'):
            (root / name).mkdir()
        env = {'HOME':str(root/'home'), 'TMPDIR':str(root/'tmp'), 'PATH':'/usr/bin:/bin:/usr/sbin:/sbin',
               'CYS_SOCKET':str(endpoint), 'CYS_STATE_DIR':str(root/'ledger'), 'CYS_PACK_DIR':str(root/'pack'),
               'CYS_SHELL':'/bin/sh', 'CYS_NO_AUTORESTORE':'1', 'CYS_REAP_EXITED':'1',
               'CYS_REAP_EXITED_GRACE_SECS':str(GRACE), 'CYS_REAP_EXITED_NONROLE_GRACE_SECS':str(GRACE),
               'PHOENIX_CYS':str(CYS), 'PHOENIX_SPAWN_RETRIES':'0', 'PYTHONDONTWRITEBYTECODE':'1'}
        owned, cleanup_errors = {}, []
        daemon, ready = None, False
        def capture(roots=()):
            parents = processes()
            todo = list(roots) + [pid for pid, identity in owned.items() if same_process(pid, identity)]
            seen = set()
            while todo:
                pid = todo.pop()
                if pid in seen: continue
                seen.add(pid)
                info = H._process_info(pid)
                if info is None:
                    assert pid in owned, 'new owned root vanished before identity capture'
                    continue
                if pid in owned and owned[pid] != info[0]: continue
                owned[pid] = info[0]
                for child, parent in parents.items():
                    if parent != pid or child in seen: continue
                    now, child_info = H._process_info(pid), H._process_info(child)
                    assert now == info, 'owned parent incarnation changed during capture'
                    if child_info is None: continue
                    assert child_info[1] == pid, 'descendant parent changed during capture'
                    if child in owned: assert owned[child] == child_info[0], 'owned descendant reused'
                    owned[child] = child_info[0]
                    todo.append(child)
        def rpc(method, params=None, timeout=6):
            assert endpoint.parent == root
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect(str(endpoint))
                s.sendall((json.dumps({'id':'s5-native','method':method,'params':params or {}})+'\n').encode())
                with s.makefile('rb') as stream:
                    reply = json.loads(stream.readline(2_000_000))
            assert reply.get('ok'), 'isolated RPC failed: %s %s' % (method, reply.get('error'))
            return reply['result']
        def events(*names):
            # events.stream replays the ring from after_seq; read what is there and stop at the first quiet gap.
            assert endpoint.parent == root
            lines, tail = [], b''
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                s.connect(str(endpoint))
                s.sendall((json.dumps({'id':'s5-events','method':'events.stream','params':{'after_seq':0,'names':list(names),'categories':[]}})+'\n').encode())
                try:
                    while chunk := s.recv(65536):
                        tail += chunk
                except TimeoutError:
                    pass
            for line in tail.split(b'\n'):
                with contextlib.suppress(ValueError):
                    if isinstance(row := json.loads(line), dict) and row.get('name') in names: lines.append(row)
            return lines
        def until(fn, seconds=8):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                try:
                    if value := fn(): return value
                except (OSError, ValueError): pass
                time.sleep(0.05)
            raise AssertionError('S5 bounded observation timed out')
        def surfaces(): return rpc('surface.list')['surfaces']
        def seat_runs(sid, argv):
            # TICKET=cysr-1116-leasee2e-1121: 좌석이 로그인 셸 프로필을 다 돌고 명령(argv 완전 일치)을 띄웠고 데몬 seat 캐시도 그것을 본다.
            #   자손 0 인 프로필 단계의 좌석은 seat=empty 로 읽혀 phoenix 가 「빈 좌석 = 부활 대상」으로 센다(설계) — 운영 경로는 spawn 뒤
            #   stage_ready(에이전트 기동 확인)가 run_restore 안에서 그 단계를 기다리지만 이 고정장치는 stage_ready 를 대역으로 바꿨다.
            row = next((s for s in surfaces() if s['surface_id'] == sid), None)
            if not row or row.get('seat') != 'occupied': return False
            ps = subprocess.run(['/bin/ps', '-axo', 'ppid=,command='], capture_output=True, text=True, check=True, timeout=3)
            return any(len(f := line.split(None, 1)) == 2 and f[0] == str(row['pid']) and f[1].strip() == argv for line in ps.stdout.splitlines())
        def record_surface(sid):
            capture([next(s for s in surfaces() if s['surface_id'] == sid)['pid']])
        create_retries = []
        def create(role, command):
            params = {'role':role,'cmd':command,'cwd':str(root),'idempotency_key':'s5-native-create-%s' % (role or 'live')}
            before = {s['surface_id'] for s in surfaces()}
            started = time.monotonic()
            try:
                sid = rpc('surface.create', params, CREATE_TIMEOUT)['surface_id']
            except TimeoutError as exc:
                if exc.args == (DEADLINE,):
                    raise  # the 90s body deadline (SIGALRM), not this request's socket timeout
                late = {'role':role,'timed_out_after_secs':round(time.monotonic()-started,3)}
                create_retries.append(late)
                manifest['create_retries'] = create_retries
                # The daemon records the key only when a create finishes, so a second create while the first is still in
                # flight makes a second seat (measured). Adopt the seat the late first create made; never re-send.
                # until() swallows OSError (TimeoutError included), so the body deadline is re-checked right after it.
                found = None
                with contextlib.suppress(AssertionError):
                    found = until(lambda: next((s['surface_id'] for s in surfaces() if s['surface_id'] not in before
                                                and (s.get('role') or None) == role), None),
                                  min(CREATE_TIMEOUT, max(0.0, body_deadline - time.monotonic())))
                if time.monotonic() >= body_deadline:
                    raise TimeoutError(DEADLINE)
                late['adopted_late_first'] = found is not None
                assert found is not None, 'S5 create: no reply in %ss and no seat in %ss more (not re-sent)' % (CREATE_TIMEOUT, CREATE_TIMEOUT)
                sid = found
            record_surface(sid)
            return sid
        def cli(*args):
            return subprocess.run([str(CYS),'--socket',str(endpoint),*args], env=env, cwd=root,
                                  capture_output=True, text=True, timeout=12)
        manifest = {'result':'failed','body_deadline_secs':90,'cleanup_deadline_secs':45,'owned_residuals':'unmeasured','grace_secs':GRACE,'endpoint':str(endpoint),'state_root':str(root),
                    'binary_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (CYS,CYSD)}}
        def save_evidence():
            manifest['owned_original_identities'] = [{'pid':pid,'start_identity':list(identity)} for pid,identity in sorted(owned.items())]
            artifact = os.environ.get('S5_NATIVE_EVIDENCE')
            if artifact:
                out = Path(artifact); out.mkdir(parents=True,exist_ok=True)
                body = (root/'daemon.log').read_text(errors='replace') if (root/'daemon.log').exists() else ''
                if (root/'operator.token').exists():
                    token = (root/'operator.token').read_text().strip()
                    if token: body = body.replace(token, '[REDACTED]')
                (out/'daemon.log').write_text(body)
                (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        def timeout(*args): raise TimeoutError(DEADLINE)
        prior = signal.signal(signal.SIGALRM, timeout)
        body_deadline = time.monotonic() + 90
        signal.alarm(90)
        try:
            with open(root/'daemon.log','wb') as log:
                daemon = subprocess.Popen([str(CYSD)], env=env, cwd=root, stdout=log, stderr=log, start_new_session=True)
            capture([daemon.pid])
            until(lambda: rpc('system.ping'), 30)
            ready = True
            rpc('system.pause', {'reason':'isolated S5 fixture; preserve queue without injection'})
            live = create(None, 'sleep 120; :')
            old = create('worker-s5-native', 'sleep 2; :')
            rpc('surface.send_text', {'surface_id':old,'text':'S5 retained native work','queued':True})
            queue_id = next(e['id'] for e in rpc('queue.list',{'full':True})['entries'] if e.get('text') == 'S5 retained native work')
            with mock.patch.dict(os.environ, env, clear=True):
                spec = importlib.util.spec_from_file_location('phoenix_s5_native',REPO/'cysjavis-pack/bin/javis_phoenix.py')
                p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
                p.CYS = str(CYS)
                p.observe_and_persist_roster(str(endpoint))
                until(lambda: any(s['surface_id'] == old and s['exited'] for s in surfaces()))
                exited_observed = time.monotonic()
                # Fork D7(2): an exiting role seat parks its queue on the role name and the next claim inherits it
                # (upstream Q7 moves it to restored_queue). Parking follows the exited flag, so spawn must wait for it.
                until(lambda: any(queue_id in e['payload'].get('queue_entry_ids', []) and e['payload'].get('role') == 'worker-s5-native'
                                  for e in events('queue.parked')))
                spawn_ids = []
                def spawn(sock, role, observed, **kwargs):
                    assert sock == str(endpoint) and role == 'worker-s5-native'
                    r = cli('new-surface','--role',role,'--cmd','sleep 120; :','--cwd',str(root))
                    assert r.returncode == 0, r.stderr
                    ref = re.search(r'surface:\d+', r.stdout).group(0)
                    sid = int(ref.split(':')[1]); spawn_ids.append(sid); record_surface(sid)
                    return ref, 'owned inert replacement; no real agent'
                with contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.object(p,'spawn_surrogate',spawn))
                    for name in ('stage_ready','stage_reinject','stage_g2_ack'):
                        stack.enter_context(mock.patch.object(p,name,lambda *a:(True,'fixture-only')))
                    stack.enter_context(mock.patch.object(p,'stage_observe_session',lambda *a,**k:(None,'no real agent session')))
                    first = p.run_restore(str(endpoint),ticket='s5-first',stub=True,no_breaker=True,print_result=False)
                    manifest['first_deferred_after_exit_observation_secs'] = round(time.monotonic()-exited_observed,3)
                    assert any(e['surface'] == 'surface:%d' % old for e in first['c6_reap_deferred']), 'S5 fresh deferred must be observed'
                    assert 'surface:%d' % old not in first['c6_reaped']
                    assert first['target_roles'] == ['worker-s5-native'] and len(spawn_ids) == 1
                    new = spawn_ids[0]
                    # 두 번째 복원은 대체 좌석이 앉은 뒤에 — CI 러너(C8 run 44850374411)는 그 좌석이 아직 프로필 단계(seat=empty)일 때
                    #   두 번째 run_restore 가 돌아 역할을 다시 대상으로 잡았다(S5 duplicate restore · 로컬 느린 .profile 로 재현).
                    until(lambda: seat_runs(new, 'sleep 120'), 20)
                    second = p.run_restore(str(endpoint),ticket='s5-second',stub=True,no_breaker=True,print_result=False)
                    assert second['target_roles'] == [] and spawn_ids == [new], 'S5 duplicate restore'
                until(lambda: any(e['id'] == queue_id and e.get('surface_id') == new and not e.get('restored') for e in rpc('queue.list')['entries']))
                assert any(queue_id in e['payload'].get('queue_entry_ids', []) and e['payload'].get('to_surface') == new
                           for e in events('queue.inherited')), 'S5 queue must be inherited by the replacement'
                assert any(s['surface_id'] == live and not s['exited'] for s in surfaces()), 'S5 live control lost'
                assert rpc('system.resolve_role',{'role':'worker-s5-native'})['surface_id'] == new
                # Only this fixture waits; restore does not wait through grace.
                deadline = exited_observed + GRACE + 0.25
                while time.monotonic() < deadline: time.sleep(min(0.1,deadline-time.monotonic()))
                due = cli('reap-due','surface:%d' % old)
                assert due.returncode == 0, due.stderr
                outcome = json.loads(due.stdout)
                assert outcome['surface_id'] == old and outcome['outcome'] in ('reaped','gone'), outcome
                assert all(s['surface_id'] != old for s in surfaces())
                assert rpc('system.resolve_role',{'role':'worker-s5-native'})['surface_id'] == new
                entries = [e for e in rpc('queue.list')['entries'] if e['id'] == queue_id]
                assert len(entries) == 1 and entries[0]['surface_id'] == new
                assert not json.loads((root/'topology.json').read_text()).get('tombstones')
                manifest.update(old=old,replacement=new,queue_id=queue_id,spawn_count=len(spawn_ids),later_due=outcome,
                                assertions='deferred, once-restored, once-rehomed, mapping, live control, no tombstones')
        except BaseException as exc:
            manifest['failure_type'] = type(exc).__name__
            raise
        finally:
            signal.alarm(0)
            cleanup_started = time.monotonic()
            try:
                signal.alarm(45)
                if daemon is not None:
                    capture()
                    if ready:
                        try:
                            token = (root/'operator.token').read_text().strip()
                            for row in surfaces(): rpc('surface.close',{'surface_id':row['surface_id'],'owner_token':token})
                            assert surfaces() == []
                        except Exception as exc: cleanup_errors.append(type(exc).__name__)
                    for pid, identity in owned.items():
                        if pid != daemon.pid and same_process(pid, identity):
                            try: os.kill(pid, signal.SIGKILL)
                            except ProcessLookupError: pass
                    if daemon.poll() is None:
                        daemon.terminate()
                        try: daemon.wait(timeout=5)
                        except subprocess.TimeoutExpired: daemon.kill(); daemon.wait(timeout=5)
                    until(lambda: all(not same_process(pid, identity) for pid,identity in owned.items()),5)
                    manifest['owned_residuals'] = 0
                    manifest['daemon_ready'] = ready
                    assert not cleanup_errors, 'graceful cleanup failed: '+repr(cleanup_errors)
                manifest['result'] = 'passed' if 'assertions' in manifest and 'failure_type' not in manifest else 'failed'
            except BaseException as exc:
                manifest['cleanup_failure_type'] = type(exc).__name__
                raise
            finally:
                signal.alarm(0); signal.signal(signal.SIGALRM, prior)
                manifest['cleanup_errors'] = cleanup_errors
                manifest['cleanup_elapsed_secs'] = round(time.monotonic()-cleanup_started,3)
                save_evidence()  # Runs even if body, capture, close, wait, or residual proof failed.
                print(json.dumps(manifest,sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
