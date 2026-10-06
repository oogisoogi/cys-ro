#!/bin/bash
# u2-smoke.sh — 1.1.8 U2 실 바이너리 격리 종단 시험(설계 §7-2 격리 env · 실 ~/.cys·실 설치본·실 LaunchAgents 쓰기 0).
#   ① cysd 부팅 가드: 비종결 저널(S7) + 잠금 없음 → rc 75(좌석·상태 파일 생성 0) · 같은 저널 + 살아 있는 잠금 → 가드 통과
#   ② 저널 두 슬롯 손상 + 재구성 불가 → `self-update --recover` rc 2 · state.json seats_blocked · 부팅 가드 유지
#   ③ `self-update --verify-payload` 매니페스트 없음 → rc 3
#   ④ `self-update --auto --spawn` → 러너 사본·복구기 plist(격리 폴더)·install_id 생성 · 러너가 떠서(피드 file:// 부재 = 미도달) 끝남
#   ⑤ `rotate --stop-only --skip-drain`: 다른 소유자가 잠금을 쥐면 rc 26(txn_busy) · 잠금 없으면 0
# 사용: scripts/tests/u2-smoke.sh   (cargo build --bin cys --bin cysd 뒤 · target/debug 바이너리를 쓴다) · exit 0 = 전건 OK
set -u
ROOT=$(git rev-parse --show-toplevel) || exit 2
CYS=$ROOT/target/debug/cys
CYSD=$ROOT/target/debug/cysd
[ -x "$CYS" ] && [ -x "$CYSD" ] || { echo "u2-smoke: 판정 불가 — target/debug/cys·cysd 없음" >&2; exit 2; }
SB=$(mktemp -d /tmp/u2s.XXXXXX)
UPD=$SB/update
mkdir -p "$SB/home" "$UPD"
chmod 700 "$UPD"
iso() {
  env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME="$SB/home" TMPDIR="$SB" LANG=ko_KR.UTF-8 \
    CYS_SOCKET="$SB/s.sock" CYS_STATE_DIR="$SB/state" CYS_PACK_DIR="$SB/home/.cys/pack" CYS_ROOT="$SB/home/.cys" \
    CYS_NO_AUTOSTART=1 CYS_UPDATE_STATE_DIR="$UPD" CYS_UPDATE_LAUNCHAGENTS_DIR="$SB/agents" \
    CYS_UPDATE_FEED_URL="file://$SB/nofeed" CYS_UPDATE_NO_JITTER=1 CYS_UPDATE_APP_PATH="$SB/Applications/cysr.app" \
    AGORA_CONFIG_DIR="$SB/agora" "$@"
}
fail=0
ok() { printf 'OK   %s\n' "$1"; }
bad() { printf 'BAD  %s\n' "$1"; fail=1; }
# 저널 쓰기(시험 전용 · lib 의 정본 직렬화를 거치게 python 이 아니라 시험 바이너리를 쓰지 않는다 — crc 가 있어 손으로 못 쓴다 →
#  러너 상태기계가 남긴 저널을 재현하려면 lib 함수가 필요하므로 여기서는 rust 시험이 만든 표본 대신 「손상」·「비종결」 두 가지만 만든다)
mkjournal() { # $1 = 상태 이름 — crc 는 lib 와 같은 식(정규 직렬화 sha256)이 필요하므로 cys 의 숨은 시험 동사 대신 python 으로 같은 직렬화를 만든다
  python3 - "$UPD" "$1" <<'PY'
import json,hashlib,sys,os
d,st=sys.argv[1],sys.argv[2]
j={"txn_id":"0123456789abcdef0123456789abcdef","epoch":1,"generation":1,"state":st,"release_seq":0,"from_release_seq":0,"target":"","stage_path":"","stage_tree_sha256":"","snapshot_dir":"","snapshot_manifest_sha256":"","prev_installer":None,"prev_bundle":None,"payload_manifest_sha256":"","hold_ingested_upto":0,"boot_id":0,"mono_at_write":0,"wall_at_write":0,"attempt":0,"crc":""}
j["crc"]=hashlib.sha256(json.dumps(j,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
open(os.path.join(d,"journal.json"),"w").write(json.dumps(j,indent=2,ensure_ascii=False))
PY
}
# ① 부팅 가드
mkjournal S7_STOPPED
iso "$CYSD" >"$SB/cysd1.log" 2>&1 & p=$!
for _ in $(seq 1 50); do kill -0 $p 2>/dev/null || break; sleep 0.1; done
if kill -0 $p 2>/dev/null; then kill $p; bad "① 부팅 가드 — cysd 가 5초 안에 안 끝남"; else wait $p; rc=$?
  if [ $rc -eq 75 ] && grep -q '갱신 복구 대기' "$SB/cysd1.log" && [ ! -e "$SB/state/cys.lock" ] && [ ! -e "$SB/s.sock" ]; then ok "① 부팅 가드 rc 75 · 상태 파일 0"; else bad "① 부팅 가드 rc=$rc $(head -c 200 "$SB/cysd1.log")"; fi
fi
python3 - "$UPD" <<'PY' &
import fcntl,os,sys,time,json,subprocess
d=sys.argv[1]
fd=os.open(os.path.join(d,"txn.lock"),os.O_RDWR|os.O_CREAT,0o600); os.fchmod(fd,0o600); fcntl.flock(fd,fcntl.LOCK_EX); open(os.path.join(d,".held"),"w").close()
# ★2판 C3: 소유자 기록 없이 잠금만 = 저널 소유자 아님 → 가드 유지 · 그 뒤 저널 토큰·러너 계보·pid 시작 시각이 맞는 기록을 쓴다
while not os.path.exists(os.path.join(d,".go")): time.sleep(0.05)
lstart=subprocess.check_output(["ps","-p",str(os.getpid()),"-o","lstart="],env={"LC_ALL":"C","PATH":"/bin:/usr/bin"}).decode().strip()
st=int(time.mktime(time.strptime(lstart,"%a %b %d %H:%M:%S %Y")))
o={"owner":"runner","pid":os.getpid(),"txn_id":"0123456789abcdef0123456789abcdef","epoch":1,"started_at":0,"boot_id":0,"start_time":st,"released":False}
p=os.path.join(d,"txn.owner.json"); open(p,"w").write(json.dumps(o)); os.chmod(p,0o600)
open(os.path.join(d,".owned"),"w").close(); time.sleep(8)
PY
lp=$!
for _ in $(seq 1 30); do [ -e "$UPD/.held" ] && break; sleep 0.1; done
iso "$CYSD" >"$SB/cysd2.log" 2>&1; rc=$?
[ $rc -eq 75 ] && ok "① 잠금만 쥠(저널 소유자 기록 없음) = 가드 유지 rc 75(★2판 C3)" || bad "① 소유자 아닌 잠금에 가드 열림 rc=$rc"
touch "$UPD/.go"
for _ in $(seq 1 30); do [ -e "$UPD/.owned" ] && break; sleep 0.1; done
iso "$CYSD" >"$SB/cysd3.log" 2>&1 & p=$!
sleep 2
if kill -0 $p 2>/dev/null; then ok "① 저널 토큰·러너 계보·pid 시작 시각 일치 = 가드 통과(데몬 기동)"; kill $p; wait $p 2>/dev/null; else bad "① 잠금 쥔 러너가 있는데 막힘 $(head -c 200 "$SB/cysd3.log")"; fi
# ⑤ rotate 잠금 경합(잠금 쥔 채)
iso "$CYS" rotate --stop-only --skip-drain >"$SB/rot1.log" 2>&1; rc=$?
[ $rc -eq 26 ] && ok "⑤ rotate --stop-only · 남의 잠금 = rc 26" || bad "⑤ rotate 경합 rc=$rc $(tail -c 200 "$SB/rot1.log")"
wait $lp 2>/dev/null; rm -f "$UPD/.held" "$UPD/.go" "$UPD/.owned"
iso "$CYS" rotate --stop-only --skip-drain >"$SB/rot2.log" 2>&1; rc=$?
[ $rc -eq 0 ] && ok "⑤ rotate --stop-only · 잠금 없음·데몬 없음 = 0" || bad "⑤ rotate 단독 rc=$rc $(tail -c 300 "$SB/rot2.log")"
# ② 손상 저널 → 복구기
echo '{broken' >"$UPD/journal.json"; echo '{broken' >"$UPD/journal.prev.json"
iso "$CYS" self-update --recover --json >"$SB/rec.log" 2>&1; rc=$?
if [ $rc -eq 2 ] && grep -q '"journal_unrecoverable"' "$UPD/state.json" 2>/dev/null; then ok "② 손상 저널 + 재구성 불가 = rc 2 · seats_blocked"; else bad "② rc=$rc $(cat "$SB/rec.log" | head -c 300)"; fi
iso "$CYSD" >"$SB/cysd3.log" 2>&1; rc=$?
[ $rc -eq 75 ] && ok "② 재구성 실패 뒤 부팅 가드 유지(rc 75)" || bad "② 부팅 가드 rc=$rc"
rm -f "$UPD"/journal*.json
# ③ verify-payload
iso "$CYS" self-update --verify-payload --json >"$SB/vp.log" 2>&1; rc=$?
[ $rc -eq 3 ] && ok "③ --verify-payload 매니페스트 없음 = rc 3" || bad "③ rc=$rc"
# ④ auto spawn
iso "$CYS" self-update --auto --spawn --json >"$SB/auto.log" 2>&1; rc=$?
if [ $rc -eq 0 ] && grep -q '"spawned":true' "$SB/auto.log" && [ -x "$UPD/runner/cys" ] && [ -s "$UPD/install_id" ] \
   && grep -q 'self-update' "$SB/agents/com.cysjavis.cysr-update-recover.plist" && cmp -s "$UPD/runner/cys" "$CYS"; then
  ok "④ --auto --spawn: 러너 사본(=cys 바이트)·install_id·복구기 plist(격리) · 즉시 반환"
else bad "④ rc=$rc $(head -c 300 "$SB/auto.log") $(ls "$UPD")"; fi
gone=1; for _ in $(seq 1 60); do pgrep -f "$UPD/runner/cys self-update --run" >/dev/null || { gone=0; break; }; sleep 0.5; done
[ $gone -eq 0 ] && ok "④ 러너 끝남(피드 미도달 = 조용히 끝 · 30초 안)" || bad "④ 러너가 30초 뒤에도 남음"
[ -e "$HOME/Library/LaunchAgents/com.cysjavis.cysr-update-recover.plist" ] && bad "실 LaunchAgents 에 plist 생김(격리 위반)" || ok "격리: 실 LaunchAgents 무접촉"
rm -rf "$SB"
exit $fail
