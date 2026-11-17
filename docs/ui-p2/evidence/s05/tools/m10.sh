P=/Applications/cysr.app/Contents/Resources/runtime/python/bin/python3
R() { $P ~/rpc.py "$@"; }
now() { $P -c 'import time;print(round(time.time(),3))'; }
last_fence_t() { grep " 1b5b323030" ~/got-t.log | tail -1 | awk '{print $1}'; }
mono() { $P - <<'PY'
import ctypes,ctypes.util
# CLOCK_MONOTONIC(6) — 대역 기록기와 같은 시계
libc=ctypes.CDLL(ctypes.util.find_library("c"))
class TS(ctypes.Structure): _fields_=[("s",ctypes.c_long),("ns",ctypes.c_long)]
t=TS(); libc.clock_gettime(6, ctypes.byref(t)); print("%d.%06d"%(t.s,t.ns//1000))
PY
}
enq() { R surface.send_text "{\"surface_id\":3,\"text\":\"$1\",\"queued\":true,\"machine_origin\":true,\"from\":\"chat-auto\"}" | cut -c1-220; }
wait_new() { local before=$1; for i in $(seq 1 90); do n=$(grep -c " 1b5b323030" ~/got-t.log); [ "$n" -gt "$before" ] && break; sleep 1; done; }
cat ~/clear.bin > /dev/ttys001; sleep 40
echo "== 대조(사람 보내기 없음): 큐 1건"; B=$(grep -c " 1b5b323030" ~/got-t.log); T0=$(mono); enq "대조 큐"; wait_new $B; echo "T0=$T0 fence=$(last_fence_t)"
sleep 40
echo "== R3: 원자 사람 보내기 직후 큐 1건"; B=$(grep -c " 1b5b323030" ~/got-t.log)
R surface.send_text '{"surface_id":3,"text":"사람 말","human":true,"quiet":true,"queued":false,"clear_first":true,"machine_origin":false,"refuse_on_approval":true,"_human_tokens":true}' | cut -c60-140
T0=$(mono); enq "묶임 큐"; B=$((B+1)); wait_new $B; echo "T0=$T0 fence=$(last_fence_t)"
R surface.list '{}' | $P -c 'import sys,json;d=json.load(sys.stdin)["resp"]["result"]["surfaces"];s=[x for x in d if x["surface_id"]==3][0];print({k:v for k,v in s.items() if "human" in k or "queue" in k})' | cut -c1-300
