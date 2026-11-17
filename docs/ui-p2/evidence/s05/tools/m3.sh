P=/Applications/cysr.app/Contents/Resources/runtime/python/bin/python3
R() { $P ~/rpc.py "$@"; }
pend() { R surface.list '{}' | $P -c 'import sys,json;d=json.load(sys.stdin)["resp"]["result"]["surfaces"];s=[x for x in d if x["surface_id"]==3][0];print("pib=",s.get("pending_input_bytes"),"pihb=",s.get("pending_input_human_bytes"),"lhi=",s.get("last_human_input_age_secs", s.get("last_human_input")))'; }
atomic() { R surface.send_text "{\"surface_id\":3,\"text\":\"$1\",\"human\":true,\"quiet\":true,\"queued\":false,\"clear_first\":true,\"machine_origin\":false,\"refuse_on_approval\":true,\"_human_tokens\":true}" | $P -c 'import sys,json;r=json.load(sys.stdin)["resp"];print("atomic ok=",r.get("ok"),(r.get("error") or {}).get("code"),str((r.get("error") or {}).get("message",""))[:140])'; }
chunks() { tail -n +$(($1+1)) ~/got-t.log | awk '{print $2":"substr($3,1,12)}' | tr '\n' ' '; echo; }
cat ~/clear.bin > /dev/ttys001; sleep 1
echo "== ⓐ 사람 초안(사람 표지 · Enter 없음)"; N=$(wc -l < ~/got-t.log)
R surface.send_text '{"surface_id":3,"text":"사람초안","human":true,"quiet":true,"_human_tokens":true}' | cut -c1-160; sleep 1; pend
atomic "ⓐ 원자"; sleep 2; pend; chunks $N
sleep 32
echo "== ⓑ 기계 잔여(사람 표지 없음 · Enter 없음)"; N=$(wc -l < ~/got-t.log)
R surface.send_text '{"surface_id":3,"text":"기계잔여","quiet":true}' | cut -c1-160; sleep 1; pend
atomic "ⓑ 원자"; sleep 2; pend; chunks $N
sleep 32
echo "== ⓒ 방금 사람 키(사람 표지 send_key · 1초 뒤)"; N=$(wc -l < ~/got-t.log)
R surface.send_key '{"surface_id":3,"key":"End","human":true,"_human_tokens":true}' | cut -c1-160; sleep 1; pend
atomic "ⓒ 원자"; sleep 2; pend; chunks $N
