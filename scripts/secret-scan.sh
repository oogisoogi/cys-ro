#!/usr/bin/env bash
# secret-scan.sh — PUBLIC repo 발행 전 시크릿/개인정보 fail-closed 게이트 (오너 2026-06-14).
# '전부 올리기'를 안전하게 유지하는 가드레일. 제네릭화 회귀(개인경로·계정·프로필·토큰·이메일)를 차단한다.
# deny-by-default: 의심 패턴이 하나라도 걸리면 비-0으로 차단한다(통과 입증 책임은 산출물에 있다).
#
# 사용:
#   scripts/secret-scan.sh             # staged 파일 스캔 (pre-commit 용)
#   scripts/secret-scan.sh --all       # 추적 파일 전수 스캔 (sync-pack가 호출)
#   scripts/secret-scan.sh <path>...   # 지정 파일 스캔
#   pre-commit 설치: ln -sf ../../scripts/secret-scan.sh .git/hooks/pre-commit
#
# 한계(정직): 정적 패턴 매칭이다 — 난독화된 시크릿·신종 토큰 형식·이미지 내 텍스트는 못 잡는다.
#            이는 회귀 방지 1차선이지 완전한 비밀유출 방어가 아니다(근본 한계 명문화).
# exit 0=clean / 1=발견(차단) / 2=인자·환경 오류.
#
# ★2026-09-20 배치화(TICKET=v110-secret-scan · release run 35508900699 윈 레그 사고):
#   종전은 **파일마다** grep·sed 를 약 14개 spawn 하는 루프였다(추적 1045파일 → 실측 17,426 spawn).
#   macOS 는 17초로 견뎠지만 Windows Git bash 는 fork 에뮬레이션이라 프로세스 생성이 수십 배
#   비싸 상시 게이트 검체 H-SECRET-1 의 300초 상한을 넘겨 태그 레인이 죽었다
#   (1.0.2 는 같은 검체가 286초 = 여유 5% 미만이었다 — 파일 994→1045 증가가 문턱을 넘겼다).
#   ⇒ **규칙별 배치 스캔**으로 바꿨다: 파일 루프를 없애고 규칙 1건당 grep 을 청크 단위로만 부른다.
#   ⚠ 출력 계약은 **바이트 단위로 불변**이다 — `TYPE\tfile:line:내용` · 파일순→규칙순→줄번호순 ·
#     exit 0/1/2 · 마지막 줄 `✓ secret-scan: clean (mode=..., N 파일)`(N = 인자 전수 계수).
#     H-SECRET-1 이 그 문장을 정규식으로 파싱한다(계약을 바꾸면 게이트가 눈이 먼다).
#   ⚠ 패턴·필터 정규식은 **전부 grep 이 그대로 평가**한다(awk 로 옮기지 않았다). awk 의 동적
#     정규식은 `\\` 처리가 구현마다 갈려 macOS(bwk awk)와 Windows(gawk)에서 다르게 판정될 수
#     있고, 이 티켓의 사고가 바로 '로컬에서 못 재는 Windows 차이'다. awk 는 **구조 작업만** 한다.
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "git repo 아님"; exit 2; }

mode="${1:-staged}"
files=()
case "$mode" in
  --all)      while IFS= read -r f; do files+=("$f"); done < <(git ls-files) ;;
  --staged|staged|"") while IFS= read -r f; do files+=("$f"); done \
                  < <(git diff --cached --name-only --diff-filter=ACM) ;;
  *)          files=("$@") ;;
esac
[ "${#files[@]}" -gt 0 ] || { echo "✓ secret-scan: 스캔 대상 없음"; exit 0; }

# 스캔 제외(노이즈·바이너리·잠금파일): 시크릿이 살지 않고 오탐만 만드는 파일들
# 스캐너 자신과 형제 스캐너(scan-pack-secrets.sh)는 제외 — 둘 다 자기 패턴/정책 정의에 /Users/cys·
# 토큰 형식·개인 핸들(ysfuture)이 리터럴로 들어 자기-오탐을 만든다(린터 관례)
skip_re='\.(lock|png|jpe?g|gif|ico|svg|woff2?|ttf|wasm|pdf|zip|dmg|msi|exe)$|(^|/)Cargo\.lock$|(^|/)LICENSE$|(^|/)secret-scan\.sh$|(^|/)scan-pack-secrets\.sh$'
# 더미 username(제네릭화된 테스트 픽스처) — 그 외 /Users/<name>은 개인경로로 차단.
# ★이름 목록은 **한 벌**이다(`dummy_names`). POSIX 판과 Windows 판이 각자 목록을 들면
#   한쪽만 늘어나 같은 이름이 한 OS 에서만 통과하는 비대칭이 생긴다.
dummy_names='user|x|youruser|USERNAME|runner|home'
dummy_user_re='/Users/('"$dummy_names"')(/|"|$)'
# Windows 홈의 더미 판 — `C:\Users\x\…`·`C:\Users\x>`. 경계는 '이름 문자가 아닌 것'으로 본다
# (뒤에 `\`·`>`·공백·따옴표 등 무엇이 오든 이름 자체가 더미면 통과).
win_dummy_user_re='[A-Za-z]:\\+Users\\+('"$dummy_names"')([^A-Za-z0-9._-]|$)'
# 이메일 허용(공개 연락처가 의도적으로 박힌 배포 문서만 — SECURITY.md 취약점 신고 연락처 포함)
email_allow_re='^(README\.md|README\.en\.md|SECURITY\.md)$'
email_fp_re='example\.(com|org|net)|noreply|@types/|@google/|@tauri|@scope|user@host|you@'
# 개인 계정 핸들 denylist(맨몸) — /Users·.claude- 접두 없이 계정키·설정값으로 박힌 개인 핸들도 차단한다.
# 넓은 패턴 대신 '알려진 개인 핸들'만 명시 등재해 제네릭 영어단어 오탐을 배제한다(deny-by-default 유지).
# ysfuture = 오너 개인 alias·이메일 prefix. 부분일치라 'claude-ysfuture'·'ysfuture@…'도 함께 걸린다.
# cys-macbook = 오너 macOS/Windows 기계 계정명(2026-08-24 실측 누출 3파일 22곳). 경로 접두 없이
#   pane 제목 꼬리(`cso-claude · cys-macbook`)·프롬프트 검체로도 박혀 있어 규칙 1·1′만으로는 안 걸린다.
# ★브랜드 `cysinsight` 는 여기 넣지 않는다 — LICENSE·README·홈페이지 URL 에 실린 공개 식별자다.
handle_deny_re='ysfuture|cys-macbook'

# 규칙 패턴 — 종전 루프 안에 인라인돼 있던 것을 변수로만 옮겼다(문자열 불변).
# 1) 개인 절대경로 (/Users/<실명>) — 더미 제외
rule1_re='/Users/[A-Za-z0-9._-]+'
# 1') 개인 절대경로 Windows 판 (`C:\Users\<실명>`) — 규칙 1의 역슬래시 거울. 더미 제외.
#     사각이었다: 규칙 1의 `/Users/` 는 정슬래시 전용이라 `C:\Users\<실명>` 을 **한 건도** 못 봤다
#     (2026-08-24 실측 — 오너 계정명이 Windows 경로 형태로 문서·검체에 살아 있었다).
#     이름 첫 글자를 영숫자로 못박아 문서의 생략 표기(`C:\Users\...`)를 오탐하지 않는다.
rule2_re='[A-Za-z]:\\+Users\\+[A-Za-z0-9][A-Za-z0-9._-]*'
# 2) 개인 프로필/홈 디렉터리명 (제네릭화 대상) — ★구분자 무관(`/Users/cys`·`C:\Users\cys` 둘 다).
#    종전 `/Users/cys` 는 정슬래시 전용이라 Windows 표기의 같은 계정을 통과시켰다(사각 ②).
rule3_re='\.claude-(ysfuture|cysinsight|cysfuturist)|[/\\]Users[/\\]+cys'
# 3) 이메일 (허용 문서·오탐 제외)
rule4_re='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(com|net|org|io|dev)'
# 4) 자격증명/토큰/개인키. 일반 keyword 규칙은 *따옴표 친 리터럴 값*만(>=12자) 매칭한다 —
#    'api_key = resolve_api_key()' 같은 함수호출·변수참조(따옴표 없음) 오탐을 배제한다.
rule5_re='sk-ant-[A-Za-z0-9]|sk-[A-Za-z0-9]{20}|ghp_[A-Za-z0-9]{10}|github_pat_[A-Za-z0-9]|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9]|-----BEGIN [A-Z ]*PRIVATE KEY-----|(password|passwd|secret|api[_-]?key|access[_-]?token)["'"'"' ]*[:=][ ]*["'"'"'][A-Za-z0-9/+=_-]{12,}'
# 5) 개인 계정 핸들(맨몸 denylist) — 접두(/Users·.claude-) 없이 계정키로 박혀도 차단(규칙2 보강)
rule6_re="$handle_deny_re"

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
findings="$tmp/findings"

# ── 대상 목록 확정 ────────────────────────────────────────────────────────────
# 종전 루프의 `[ -f "$f" ] || continue` 는 셸 내장이라 그대로 두고(프로세스 0),
# `printf | grep -qE "$skip_re"` 는 **목록 전체에 대한 grep 1회**로 접는다.
# ★필터를 bash `[[ =~ ]]` 로 옮기지 않은 이유: 정규식 엔진이 grep 과 갈릴 수 있다(위 헤더 ⚠).
for f in "${files[@]}"; do
  if [ -f "$f" ]; then printf '%s\n' "$f"; fi
done > "$tmp/exists"
grep -vE -e "$skip_re" "$tmp/exists" > "$tmp/flist" || true
# 규칙 3(이메일)만 파일 단위 허용목록이 있다 — 종전의 per-file `grep -qE "$email_allow_re"` 와 동치.
grep -vE -e "$email_allow_re" "$tmp/flist" > "$tmp/flist_email" || true

scan_files=(); n_scan=0
while IFS= read -r f; do scan_files+=("$f"); n_scan=$((n_scan+1)); done < "$tmp/flist"
mail_files=(); n_mail=0
while IFS= read -r f; do mail_files+=("$f"); n_mail=$((n_mail+1)); done < "$tmp/flist_email"

# ── 규칙별 배치 스캔 ──────────────────────────────────────────────────────────
# 청크 상한: Windows CreateProcess 명령줄 32,767자 제약 때문에 전량을 한 번에 넘기지 않는다.
CHUNK=100
for r in 1 2 3 4 5 6; do : > "$tmp/raw$r"; done

batch_grep() {  # $1=출력파일 $2=패턴 $3..=대상 파일
  local out="$1" pat="$2"; shift 2
  local args=("$@") i=0 n=$#
  while [ "$i" -lt "$n" ]; do
    grep -HnE -e "$pat" -- "${args[@]:i:CHUNK}" >> "$out" 2>/dev/null || true
    i=$((i+CHUNK))
  done
}

if [ "$n_scan" -gt 0 ]; then
  batch_grep "$tmp/raw1" "$rule1_re" "${scan_files[@]}"
  batch_grep "$tmp/raw2" "$rule2_re" "${scan_files[@]}"
  batch_grep "$tmp/raw3" "$rule3_re" "${scan_files[@]}"
  batch_grep "$tmp/raw5" "$rule5_re" "${scan_files[@]}"
  batch_grep "$tmp/raw6" "$rule6_re" "${scan_files[@]}"
fi
if [ "$n_mail" -gt 0 ]; then
  batch_grep "$tmp/raw4" "$rule4_re" "${mail_files[@]}"
fi

# ── 정렬 키 부여 + 필터 대상 분리 (awk = 구조 작업만) ────────────────────────
# grep -H 의 출력은 `file:line:내용` 이라 종전 `sed "s|^|TYPE\t$f:|"` 의 결과와 같은 꼴이다.
# 여기서는 ⑴파일의 원래 순번 ⑵규칙 번호 ⑶줄번호 를 정렬 키로 붙이고,
# 필터(-v)가 있는 규칙 1·1′·3 은 **내용만** 추려 별도 스트림으로 내보낸다.
# ★파일명을 필터에 노출하지 않는 이유: 종전 필터는 `N:내용` 만 봤다. `docs/@types/x.md` 같은
#   경로가 있으면 `grep -vEi "$email_fp_re"` 가 그 파일의 발견을 통째로 지워 **완화**가 된다.
#   레코드 id 접두(`\001<n>\001`)는 숫자·제어문자뿐이라 세 필터 정규식 중 어느 것도 시작할 수 없다
#   (dummy=`/` 필요 · win-dummy=`[A-Za-z]` 필요 · email-fp=문자/`@` 필요).
awk -v FL="$tmp/flist" \
    -v CS1="$tmp/cs1" -v CS2="$tmp/cs2" -v CS4="$tmp/cs4" \
    -v META="$tmp/meta" -v KEEP="$tmp/keep" '
function emit(fi, r, ln, line, content,    dest) {
  # 필터(-v)가 붙는 규칙 1·1′·3 만 내용 스트림으로 우회시키고, 나머지는 바로 확정한다.
  if (r==1 || r==2 || r==4) {
    gid++
    dest = (r==1 ? CS1 : (r==2 ? CS2 : CS4))
    printf "\001%d\001%s\n", gid, content > dest
    printf "%d\t%d\t%d\t%d\t%s\t%s\n", gid, fi, r, ln, T[r], line > META
  } else {
    printf "%d\t%d\t%d\t%s\t%s\n", fi, r, ln, T[r], line > KEEP
  }
}
BEGIN{ T[1]="PATH"; T[2]="WIN-PATH"; T[3]="PROFILE"; T[4]="EMAIL"; T[5]="SECRET"; T[6]="HANDLE"
       gid=0; maxlen=0; bad=0 }
FILENAME==FL { idx[$0]=FNR; if (length($0)>maxlen) maxlen=length($0); next }
{
  r = substr(FILENAME, length(FILENAME)) + 0
  # 파일명 해석: 알려진 파일 목록에 들어 있는 **가장 긴** 접두를 고른다(경로에 콜론이 있어도 안전).
  best=""; bestpos=0; start=1
  while (1) {
    p = index(substr($0, start), ":")
    if (p == 0) break
    pos = start + p - 1
    if (pos-1 > maxlen) break
    cand = substr($0, 1, pos-1)
    if (cand in idx) { best=cand; bestpos=pos }
    start = pos + 1
  }
  if (bestpos > 0) { rest = substr($0, bestpos+1); q = index(rest, ":") } else { q = 0 }
  if (bestpos > 0 && q > 0) { emit(idx[best], r, substr(rest,1,q-1)+0, $0, substr(rest,q+1)); next }
  # grep 의 **메시지 줄**(`Binary file <경로> matches` 등)은 `파일:줄:` 꼴이 아니다.
  # 종전은 파일마다 grep 을 따로 불러 그 줄도 `sed "s|^|TYPE\t$f:|"` 로 그대로 붙였다 —
  # 같은 결과를 내려면 줄 안에 들어 있는 **알려진 파일명**으로 귀속한다(줄번호 0 = 규칙 머리).
  # ★영어 문구를 파싱하지 않는다(로캘·grep 판본마다 다르다) — 파일명 포함 여부만 본다.
  hit = best
  if (hit == "") { for (k in idx) if (index($0, k) > 0 && length(k) > length(hit)) hit = k }
  if (hit == "") { printf "secret-scan: grep 출력 해석 실패(내부 오류): %s\n", $0 > "/dev/stderr"; bad=1; next }
  emit(idx[hit], r, 0, (bestpos > 0 ? $0 : hit ":" $0), $0)
}
END{ exit (bad ? 3 : 0) }
' "$tmp/flist" "$tmp/raw1" "$tmp/raw2" "$tmp/raw3" "$tmp/raw4" "$tmp/raw5" "$tmp/raw6" \
  || { echo "✗ secret-scan: 내부 오류로 판정 불가 — fail-closed"; exit 2; }
for x in cs1 cs2 cs4 meta keep; do [ -f "$tmp/$x" ] || : > "$tmp/$x"; done

# ── 필터 적용(종전과 같은 grep·같은 정규식·같은 플래그) ──────────────────────
grep -vE  -e "$dummy_user_re"     "$tmp/cs1" > "$tmp/k1" || true
grep -vE  -e "$win_dummy_user_re" "$tmp/cs2" > "$tmp/k2" || true
grep -vEi -e "$email_fp_re"       "$tmp/cs4" > "$tmp/k4" || true

# ── 살아남은 레코드를 되붙이고 파일순→규칙순→줄번호순으로 정렬 ──────────────
awk -v META="$tmp/meta" '
FILENAME==META { p=index($0,"\t"); m[substr($0,1,p-1)] = substr($0,p+1); next }
{ p2 = index(substr($0,2), "\001"); g = substr($0, 2, p2-1); if (g in m) print m[g] }
' "$tmp/meta" "$tmp/k1" "$tmp/k2" "$tmp/k4" >> "$tmp/keep"
LC_ALL=C sort -t"$(printf '\t')" -k1,1n -k2,2n -k3,3n "$tmp/keep" | cut -f4- > "$findings"

n=$(wc -l < "$findings" | tr -d ' ')
if [ "$n" -gt 0 ]; then
  echo "✗ secret-scan: $n 건 발견 — PUBLIC 발행 차단(fail-closed):"
  sed -E 's/([A-Za-z0-9/+_-]{20,})/***REDACTED***/g' "$findings" | head -40
  [ "$n" -gt 40 ] && echo "  …(외 $((n-40))건)"
  echo "→ 개인경로/프로필은 환경변수·더미값으로, 시크릿은 제거 후 재시도하라."
  exit 1
fi
echo "✓ secret-scan: clean (mode=$mode, ${#files[@]} 파일)"
exit 0
