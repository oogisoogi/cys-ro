# VM 안 전용: python3 rpc.py <method> '<params json>' — 계획서 부록 R
import json, os, socket, sys, time
sock = os.environ.get("CYS_SOCKET") or os.path.expanduser("~/.local/state/cys/cys.sock")
tok_path = os.path.join(os.path.dirname(sock), "operator.token")
params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
if params.pop("_human_tokens", False):
    t = open(tok_path).read().strip()
    params["operator_token"] = t; params["owner_token"] = t
s = socket.socket(socket.AF_UNIX); s.connect(sock)
t0 = time.monotonic()
s.sendall((json.dumps({"id": 1, "method": sys.argv[1], "params": params}) + "\n").encode())
line = s.makefile().readline()
print(json.dumps({"rtt_ms": round((time.monotonic() - t0) * 1000, 2), "mono_send": round(t0, 6), "resp": json.loads(line)}, ensure_ascii=False))
