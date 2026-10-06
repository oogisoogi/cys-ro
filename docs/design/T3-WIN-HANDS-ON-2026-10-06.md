# T3 상담소 자동 전달 — 윈 실기 지시 초안 (TICKET=agora-t3-pack-collector · 발송 = master)

> 받는 이 = 윈 노트북 master. 목적 = 1.1.8 팩의 수집기가 윈에서 **사람 손 0 · 화면 0** 으로 신호·일일·주간 세 통을 맥과 같은 바이트로 다루는지 실기 확인.
> 라이브 발신 = **시험 참가자 키만**(이 PC 의 실제 참가자 설정 폴더 사용 금지) · 막히면 그 단계 출력 원문을 붙여 회신.
> 줄 표기 `$CFG` = 시험 설정 폴더(아래 0 에서 정한다). PowerShell 이 아니라 **cys 좌석의 bash(동봉 Git bash)** 에서 친다.

## 0. 준비(시험 설정 폴더 격리)
```bash
export AGORA_CONFIG_DIR="$HOME/.config/agora-test-win118"   # 실제 ~/.config/agora 와 분리
export CFG="$AGORA_CONFIG_DIR"
cys --version; head -1 "${CYS_PACK_DIR:-$HOME/.cys/pack}/.pack-version"          # 기대: 1.1.8 · 1.1.8
ls "${CYS_PACK_DIR:-$HOME/.cys/pack}/install/"                                    # 기대: agora-client-0.1.14.zip.b64 · agora-client.pin
grep -n '"agora-counsel"' "${CYS_PACK_DIR:-$HOME/.cys/pack}/schedule.json"        # 기대: 1줄(every_minutes 30 · base_only true)
```

## 1. 클라이언트 첫 설치(동봉본 · 사람 손 0)
```bash
python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_counsel.py" ensure-client
cat "$CFG/lib/.pin"; cat "${CYS_PACK_DIR:-$HOME/.cys/pack}/install/agora-client.pin"   # 기대: 두 줄이 같다
python3 "$CFG/lib/bin/agora" --version 2>/dev/null || python3 "$CFG/lib/bin/agora" whoami --dir "$CFG" | head -5
tail -3 "$CFG/counsel/tick.log"
```
- 다시 한 번 `ensure-client` → `tick.log` 에 「무접촉」 줄(같은 핀) · `$CFG/lib` 수정 시각 불변.

## 2. 시험 참가자 가입(라이브 쓰기 = 등록 1)
```bash
A="python3 $CFG/lib/bin/agora"
$A keygen jarvis-test-win118 --dir "$CFG" 2>/dev/null || $A keygen jarvis-test-win118
export AGORA_SIGNING_KEY="$CFG/id_ed25519"
$A register --relay https://agora.godmeyou.kr --unattended
$A sync-roster --yes
grep -c '^jarvis-counsel ' "$CFG/allowed_signers"     # 기대: 1(핀 데스크 키가 명부에 있어야 기계 통 승인 예외가 선다)
```

## 3. 신호 1줄 유발 → 줄끝 LF 바이트 대조
```bash
CYS_ROLE=worker python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_counsel.py" signal --source worker --op hook.session-start --error-code hook.rc1
python3 - <<'EOF'
import os
p = os.path.join(os.environ["CFG"], "counsel", "signals.jsonl")
b = open(p, "rb").read()
print("bytes", len(b), "CRLF" if b"\r\n" in b else "LF only", "BOM" if b.startswith(b"\xef\xbb\xbf") else "no BOM")
print(b.decode("utf-8").splitlines()[-1])
EOF
```
기대: `LF only · no BOM` · 마지막 줄 `{"error_code":"hook.rc1","op":"hook.session-start","os":"windows-…","source":"worker","ts":"…Z","version":"1.1.8"}`.

## 4. 한 판(=일정이 30분마다 부르는 것과 같은 명령) — 신호 1통 + 일일 1통
```bash
python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_counsel.py" tick
cat "$CFG/counsel/facts.json"                      # 일일 칸 재료(좌석·doctor·오류 계수·부서·가동 시간)
tail -1 "$CFG/counsel/counsel.log"                 # 기대: signal.result=sent · daily.result=sent · weekly.result=empty(이 PC 는 직전 주기 원장 0)
wc -c "$CFG/counsel/signals.jsonl" "$CFG/counsel/signals-sent.jsonl"   # 기대: 모은 파일 0 바이트 · 보낸 원장 = 3 의 줄과 같은 바이트
python3 -c "import json,os;s=json.load(open(os.path.join(os.environ['CFG'],'counsel','state.json')));print({k:s.get(k) for k in ('signal_day','daily_day','daily_ok_at','weekly_skipped','weekly')})"
```
- 같은 명령을 바로 한 번 더 → counsel.log 마지막 줄 `done_today` 둘(같은 날 재발신 0).
- 3 에서 쓴 줄 원문과 `signals-sent.jsonl` 마지막 줄을 `cmp` 로 대조 — 한 바이트도 달라지면 안 된다(주간 근거 id = 줄 원문 해시).

## 5. 주간 빈 보고 생략 → 일일 `weekly_skipped`
- 4 의 counsel.log 에 `weekly.result=empty` 와 그 `cycle`(예 `2026-W40`)이 있고, 같은 판 일일 통의 칸 목록(`daily.칸`)에 `weekly_skipped` 가 있어야 한다.
- 데스크 쪽 확인 = master(데스크 `mail sync` 뒤 inbox 에 이 참가자 일일 1통 · `weekly_skipped` = 그 주기).

## 6. 끄기 확인(그 키만 · 모은 줄 삭제 · whoami 셋째 칸)
```bash
CYS_ROLE=worker python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_counsel.py" signal --source worker --op hook.session-start --error-code hook.rc1
$A counsel off --dir "$CFG"
wc -c "$CFG/counsel/signals.jsonl"                                  # 기대: 0
$A whoami --dir "$CFG" | grep autosend_counsel                      # 기대: "상담소 자동 전달: 꺼짐"
CYS_ROLE=worker python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_counsel.py" signal --source worker --op hook.session-start --error-code hook.rc1
wc -c "$CFG/counsel/signals.jsonl"                                  # 기대: 0(꺼진 동안은 쓰지도 않는다)
python3 "${CYS_PACK_DIR:-$HOME/.cys/pack}/bin/javis_counsel.py" tick; tail -1 "$CFG/counsel/counsel.log"   # 기대: result=off
$A counsel on --dir "$CFG"
```

## 7. 일정 실발화(30분 · 사람 손 0)
- 6 뒤 그대로 두고 다음 날 06:00 KST 이후 첫 30분 안에 `counsel.log` 에 새 줄이 생겼는지(= cysd 일정이 부름) 회신. 잠든 PC 는 깬 직후 1회.
- `cys schedule list | grep agora-counsel` 출력 1줄 첨부.

## 8. 회신 서식
단계별 PASS/FAIL 한 줄 + FAIL 단계 출력 원문 · `signals.jsonl`/`signals-sent.jsonl` 바이트 수 · counsel.log 마지막 3줄 · 윈 판(`cmd /c ver`).
