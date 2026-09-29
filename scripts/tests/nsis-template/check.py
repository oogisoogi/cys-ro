#!/usr/bin/env python3
"""nsis-template check (cysr 1.1.7 E3·E2 · TICKET=cysr-117-impl-brand · master#bd7a4a80 조건 ①).

우리 NSIS 템플릿 사본(src-tauri/nsis/installer.nsi)이 Tauri CLI 원문(src-tauri/nsis/tauri-cli-<핀>-installer.nsi)과
**우리가 적은 차이만큼만** 다른지, 그리고 그 차이가 뜻하는 동작(E3 자동 진행 · E2 제거 등록값 /P)이 제자리에 있는지
정적으로 잰다. 실행 증거는 windows-build.yml T8 이 진다(이것은 표류 가드).

  python3 scripts/tests/nsis-template/check.py   → exit 0 = 전부 통과 · 1 = 실패 목록 출력

잡는 것:
  P1 원문 사본의 sha256 = 핀(원문을 손대면 적색) · P2 원문 파일 이름의 판번 = 워크플로·빌드 스크립트의 TAURI_CLI_VERSION 핀 전부
     (CLI 를 올리면 적색 → 새 원문을 받아 사본 교체 + 아래 차이를 다시 얹는다) · P3 tauri.windows.conf.json 이 우리 사본을 쓴다
  P4 원문 대비 **삭제·교체 0 · 삽입 줄 = EXPECTED_INSERTS 그대로**(차이만 우리 쪽에)
  S1~S7(+S3b) 동작 단언(아래) · N1~N5 음성 대조: 핵심 줄을 지운 변이가 반드시 적색이어야 한다(안 잡는 가드는 가드가 아니다).
"""
import difflib
import hashlib
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PIN_VER = "2.11.4"
PRISTINE = os.path.join(REPO, "src-tauri", "nsis", "tauri-cli-%s-installer.nsi" % PIN_VER)
PRISTINE_SHA256 = "20f4ecc730defb71f1342eaeaec4021df13be3d843abba0effe88ea5835fa079"  # tag tauri-cli-v2.11.4 원문
OURS = os.path.join(REPO, "src-tauri", "nsis", "installer.nsi")
HOOK = os.path.join(REPO, "src-tauri", "nsis-hooks.nsh")
WINCONF = os.path.join(REPO, "src-tauri", "tauri.windows.conf.json")
CLI_PIN_FILES = [".github/workflows/windows-build.yml", ".github/workflows/release.yml",
                 "scripts/build-macos-local.sh", "scripts/build-macos-signed.sh"]
M = "; (cysr 1.1.7 E3)"

# 원문 대비 삽입 줄 전부(순서 그대로) — 이 목록 밖의 차이는 적색.
EXPECTED_INSERTS = [
    M + " 인자 없이 실행된 사람용 설치(/P·/S 아님) = 확인 화면 없이 passive 처럼 자동 진행하고 끝나면 앱을 켠다.",
    ";   박사님 09-25 「손이 안 가게」 · master#bd7a4a80 E3=A. 원문 = tauri-cli-2.11.4-installer.nsi · 차이 = 이 표식 줄들뿐.",
    "Var AutoGui",
    "  " + M + " 낮은 판으로 덮어쓰기(다운그레이드)는 사람이 봐야 한다 — 자동 진행을 끄고 원래 화면 흐름으로",
    "  ${If} $AutoGui = 1",
    "  ${AndIf} $R0 = -1",
    "    StrCpy $AutoGui 0",
    "  ${EndIf}",
    "",
    "  " + M + " 재설치 선택 화면을 띄우지 않는다",
    "  ${OrIf} $AutoGui = 1",
    "    Goto reinst_done",           # ← difflib 는 이 블록을 원문의 같은 줄들과 한 칸 어긋나게 맞춘다(결정론 · 뜻은 같음)
    "  ${EndIf}",
    "",
    "  " + M + " 자동 진행 = 먼저 제거하지 않고 제자리 덮어 설치(설치기 /S 길과 같은 길 — 훅이 켜진 앱·데몬 위 덮어 설치를 맡는다)",
    "  ${If} $AutoGui = 1",
    "  ${EndIf}",
    "",
    "  " + M + " 사람이 그냥 실행(/P 아님 · /S 아님) → 자동 진행",
    "  ${If} $PassiveMode <> 1",
    "  ${AndIfNot} ${Silent}",
    "    StrCpy $AutoGui 1",
    "  " + M + " 진행 화면 자동 닫힘",
    "  ${OrIf} $AutoGui = 1",
    "  " + M + " 마침 화면의 「앱 실행」(기본 켜짐)을 대신한다",
    "  ${If} $AutoGui = 1",
    '    nsis_tauri_utils::RunAsUser "$INSTDIR\\${MAINBINARYNAME}.exe" ""',
    "  ${EndIf}",
    "  " + M + " 환영·설치 폴더·마침 화면 건너뜀",
    "  ${IfThen} $AutoGui = 1  ${|} Abort ${|}",
]


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def func_body(text, name):
    m = re.search(r"^Function %s\n(.*?)^FunctionEnd" % re.escape(name), text, re.S | re.M)
    return m.group(1) if m else None


def macro_body(text, name):
    m = re.search(r"^!macro %s\b[^\n]*\n(.*?)^!macroend" % re.escape(name), text, re.S | re.M)
    return m.group(1) if m else None


def semantic(ours, hook):
    """S1~S7 — 동작 단언. 실패 문장 목록을 돌려준다(빈 목록 = 통과)."""
    bad = []
    oninit = func_body(ours, ".onInit") or ""
    # S1 AutoGui 는 /P 도 /S 도 아닐 때만 켜진다(설치기 /S · 업데이터 /P 경로 무변경)
    if not re.search(r"\$\{If\} \$PassiveMode <> 1\n\s*\$\{AndIfNot\} \$\{Silent\}\n\s*StrCpy \$AutoGui 1", oninit):
        bad.append("S1 .onInit: AutoGui = (/P 아님 ∧ /S 아님) 조건이 없다")
    if oninit.find("StrCpy $AutoGui 1") < oninit.find('${GetOptions} $CMDLINE "/P" $PassiveMode'):
        bad.append("S1 .onInit: AutoGui 판정이 /P 해석보다 앞선다")
    # S2 환영·폴더·마침 화면 = SkipIfPassive 가 AutoGui 에서도 건너뛴다(화면 3개가 이 함수를 PRE 로 쓴다)
    sk = func_body(ours, "SkipIfPassive") or ""
    if "${IfThen} $AutoGui = 1  ${|} Abort ${|}" not in sk:
        bad.append("S2 SkipIfPassive: AutoGui 건너뜀 없음")
    for page in ("MUI_PAGE_WELCOME", "MUI_PAGE_DIRECTORY", "MUI_PAGE_FINISH"):
        i = ours.find("!insertmacro %s" % page)
        pre = ours.rfind("!define MUI_PAGE_CUSTOMFUNCTION_PRE", 0, i)
        if i < 0 or pre < 0 or "SkipIfPassive" not in ours[pre:i].split("\n")[0]:
            bad.append("S2 %s 앞 PRE 가 SkipIfPassive 가 아니다" % page)
    # S3 재설치 선택 화면 = AutoGui 면 띄우지 않고 떠나기 함수로, 떠나기에서는 먼저 제거 없이 제자리 덮어 설치
    pr = func_body(ours, "PageReinstall") or ""
    if not re.search(r"\$\{If\} \$PassiveMode = 1\n(\s*;[^\n]*\n)?\s*\$\{OrIf\} \$AutoGui = 1\n\s*Call PageLeaveReinstall", pr):
        bad.append("S3 PageReinstall: AutoGui 에서 화면을 건너뛰지 않는다")
    # S3b 다운그레이드(판 비교 $R0 = -1)는 자동 진행을 끄고 원래 화면으로 — 화면 건너뜀 판정보다 앞
    idg = pr.find("${If} $AutoGui = 1\n  ${AndIf} $R0 = -1\n    StrCpy $AutoGui 0")
    isk = pr.find("${OrIf} $AutoGui = 1")
    icmp = pr.find("nsis_tauri_utils::SemverCompare")
    if not (0 <= icmp < idg < isk):
        bad.append("S3b PageReinstall: 다운그레이드 때 자동 진행 끄기가 판 비교 뒤·화면 건너뜀 앞에 없다")
    pl = func_body(ours, "PageLeaveReinstall") or ""
    iw, ia, iu = pl.find("$WixMode = 1"), pl.find("${If} $AutoGui = 1\n    Goto reinst_done"), pl.find("reinst_uninstall:")
    if not (0 <= iw < ia < iu):
        bad.append("S3 PageLeaveReinstall: AutoGui → reinst_done 이 Wix 판정 뒤·선택 판정 앞에 없다")
    # S4 「먼저 제거」 경로(/P 같은 판) 보존 — 등록값 뒤에 /P·_?= 를 덧붙여 부른다(등록값의 /P 와 겹쳐도 무해)
    if '${IfThen} $PassiveMode = 1 ${|} StrCpy $R1 "$R1 /P" ${|}' not in pl or 'StrCpy $R1 "$R1 _?=$4"' not in pl:
        bad.append("S4 먼저 제거 경로의 /P·_?= 덧붙임이 사라졌다")
    # S5 진행 화면 자동 닫힘 + 끝나면 앱 실행
    if not re.search(r"\$\{If\} \$PassiveMode = 1\n(\s*;[^\n]*\n)?\s*\$\{OrIf\} \$AutoGui = 1\n\s*SetAutoClose true", ours):
        bad.append("S5 SetAutoClose: AutoGui 자동 닫힘 없음")
    ok = func_body(ours, ".onInstSuccess") or ""
    if not re.search(r'\$\{If\} \$AutoGui = 1\n\s*nsis_tauri_utils::RunAsUser "\$INSTDIR\\\$\{MAINBINARYNAME\}\.exe" ""', ok):
        bad.append("S5 .onInstSuccess: AutoGui 앱 실행 없음")
    # S6 E2 — 훅 POSTINSTALL 이 등록값을 /P 로 덮고, 그 훅은 템플릿의 등록값 쓰기 **뒤**에 삽입된다
    post = macro_body(hook, "NSIS_HOOK_POSTINSTALL") or ""
    if 'WriteRegStr SHCTX "${UNINSTKEY}" "UninstallString" "$\\"$INSTDIR\\uninstall.exe$\\" /P"' not in post:
        bad.append("S6 훅 POSTINSTALL: UninstallString /P 쓰기 없음")
    iw2 = ours.find('WriteRegStr SHCTX "${UNINSTKEY}" "UninstallString"')
    ih = ours.find("!insertmacro NSIS_HOOK_POSTINSTALL")
    if not (0 <= iw2 < ih):
        bad.append("S6 템플릿: 등록값 쓰기가 POSTINSTALL 훅 삽입보다 앞이 아니다(훅의 /P 가 덮여 사라진다)")
    # S7 제거기는 /P 를 읽어 확인 화면을 건너뛰고 자동 닫힘 · 「앱 데이터 삭제」는 그 칸이 켜졌을 때만
    un = func_body(ours, "un.onInit") or ""
    if '${GetOptions} $CMDLINE "/P" $PassiveMode' not in un or "${IfThen} $PassiveMode = 1  ${|} Abort ${|}" not in (func_body(ours, "un.SkipIfPassive") or ""):
        bad.append("S7 제거기: /P 해석·확인 화면 건너뜀 없음")
    if "${If} $DeleteAppDataCheckboxState = 1" not in ours:
        bad.append("S7 제거기: 앱 데이터 삭제가 칸 상태에 묶여 있지 않다(자동 보관 근거 소실)")
    return bad


def main():
    fails = []
    pristine, ours, hook = read(PRISTINE), read(OURS), read(HOOK)
    # P1
    h = hashlib.sha256(pristine.encode("utf-8")).hexdigest()
    if h != PRISTINE_SHA256:
        fails.append("P1 원문 사본 sha256 불일치: %s" % h)
    # P2
    for rel in CLI_PIN_FILES:
        vals = set(re.findall(r"TAURI_CLI_VERSION(?::\s*'|=\"\$\{TAURI_CLI_VERSION:-)([0-9.]+)", read(os.path.join(REPO, rel))))
        if vals != {PIN_VER}:
            fails.append("P2 %s 의 TAURI_CLI_VERSION 핀 %s ≠ 템플릿 원문 판 %s — 새 원문을 받아 사본을 다시 만들어라" % (rel, sorted(vals), PIN_VER))
    # P3
    nsis = json.loads(read(WINCONF))["bundle"]["windows"]["nsis"]
    if nsis.get("template") != "nsis/installer.nsi" or not os.path.isfile(os.path.join(REPO, "src-tauri", nsis.get("template", ""))):
        fails.append("P3 tauri.windows.conf.json 이 우리 템플릿 사본을 쓰지 않는다: %r" % nsis.get("template"))
    # P4
    a, b = pristine.split("\n"), ours.split("\n")
    ins = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ("delete", "replace"):
            fails.append("P4 원문 줄 삭제·교체 %d~%d: %r" % (i1 + 1, i2, a[i1:i2][:2]))
        if tag in ("insert", "replace"):
            ins += b[j1:j2]
    if ins != EXPECTED_INSERTS:
        extra = [x for x in ins if x not in EXPECTED_INSERTS][:3]
        miss = [x for x in EXPECTED_INSERTS if x not in ins][:3]
        fails.append("P4 삽입 줄이 목록과 다르다 — 목록 밖 %r · 빠짐 %r" % (extra, miss))
    fails += semantic(ours, hook)
    # 음성 대조 — 핵심 줄 하나를 지운 변이가 반드시 적색
    negs = [
        ("N1 AutoGui 켜기 제거", ours.replace("    StrCpy $AutoGui 1\n", ""), hook),
        ("N2 SkipIfPassive 의 AutoGui 건너뜀 제거", ours.replace("  ${IfThen} $AutoGui = 1  ${|} Abort ${|}\n", ""), hook),
        ("N3 재설치 AutoGui → 덮어 설치 제거", ours.replace("  ${If} $AutoGui = 1\n    Goto reinst_done\n  ${EndIf}\n", ""), hook),
        ("N4 훅 /P 제거", ours, hook.replace('uninstall.exe$\\" /P"', 'uninstall.exe$\\""')),
        ("N5 다운그레이드 자동 진행 끄기 제거", ours.replace("  ${AndIf} $R0 = -1\n    StrCpy $AutoGui 0\n", ""), hook),
    ]
    for name, o2, h2 in negs:
        if (o2, h2) == (ours, hook):
            fails.append("%s: 변이가 적용되지 않았다(측정 불능)" % name)
        elif not semantic(o2, h2):
            fails.append("%s: 변이가 초록 — 단언이 죽었다" % name)
    if fails:
        print("nsis-template: FAIL")
        for f in fails:
            print("  - " + f)
        return 1
    print("nsis-template: OK (원문 %s sha 핀 · CLI 핀 %d곳 · 삽입 %d줄 = 목록 · 동작 단언 S1~S7 · 음성 대조 N1~N5 적색)"
          % (PIN_VER, len(CLI_PIN_FILES), len(EXPECTED_INSERTS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
