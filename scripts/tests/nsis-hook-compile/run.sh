#!/usr/bin/env bash
# nsis-hook compile harness runner.
#
#   bash scripts/tests/nsis-hook-compile/run.sh   -> exit 0 = the real hook compiles AND
#                                                    every compile-time guard still fires
#
# What it does (works on macOS/Linux with POSIX makensis, and on Windows CI):
#   1. copies src-tauri/nsis-hooks.nsh byte-identically into build/ (the hook resolves its
#      sidecar sources via ${__FILEDIR__}\binaries\..., so the copy gets its own binaries/)
#   2. generates fake PE32+ executables WITH a real VS_VERSIONINFO resource
#      (make_versioned_pe.py) so the hook's `!getdllversion /packed` oracle runs for real
#   3. compiles harness.nsi with warnings-as-errors (-WX), mirroring the template's
#      include order and macro insertion (an uninserted macro body is never compiled)
#   4. ★negative controls (R2 round-2): re-compiles against poisoned inputs and DEMANDS
#      failure with the exact NSIS-CONTRACT §5 token. A green positive compile alone cannot
#      notice the guards being deleted from the hook (measured: an E1 mutation stripping all
#      four !error guards still exited 0) — only a red negative can.
#        N1 sidecar without VERSIONINFO      -> must fail: 'refusing to build a blind oracle'
#        N2 sidecar stamped 0.0.0.0          -> must fail: 'version resource regression'
#        N3 sidecar missing at compile time  -> must fail: 'sidecar source not found at compile time'
#        N4 the three §5 tokens exist verbatim in the REAL hook — protects the grep belts
#           in release.yml / windows-build.yml (their semantics: token in build log = fail;
#           if the hook's wording drifts, those belts go silently blind)
#        N5 CONTRACT §6 taskkill census on the REAL hook — 9 kills inside
#           NSIS_HOOK_PREUNINSTALL / 10 in the whole file; the single one outside must be
#           the GUI-only '/F /IM cys-app.exe' with no '/T' (owner anchor ④: no path may
#           kill every pane's agent — the deleted v0.14.27 kill fallback class)
#        N6 checklist anchor pins — every hook anchor cited by
#           docs/WINDOWS-UPGRADE-ATOMICITY-CHECKLIST.md exists in the hook, and raw ':NNN'
#           hook line-number citations are refused (they rotted twice — R2/R3)
#
# Env overrides:
#   MAKENSIS            makensis binary (default: makensis on PATH)
#   CYS_HARNESS_VERSION version stamped into the fake PEs (default 0.14.28.0)
#   PYTHON              python interpreter (default: python3)
set -euo pipefail
cd "$(dirname "$0")"

MAKENSIS="${MAKENSIS:-makensis}"
PYTHON="${PYTHON:-python3}"
VER="${CYS_HARNESS_VERSION:-0.14.28.0}"
HOOK="../../../src-tauri/nsis-hooks.nsh"

command -v "$MAKENSIS" >/dev/null 2>&1 || { echo "FAIL: makensis not found (set MAKENSIS=...)" >&2; exit 2; }
[ -f "$HOOK" ] || { echo "FAIL: hook not found at $HOOK" >&2; exit 2; }

rm -rf build
mkdir -p build/binaries build/nsis
cp "$HOOK" build/nsis-hooks.nsh
cmp -s "$HOOK" build/nsis-hooks.nsh || { echo "FAIL: hook copy not byte-identical" >&2; exit 2; }
# helper scripts the hook ships with compile-time `File` from ${CYS_HOOK_DIR}\nsis\ (1.1.11)
SAMEBYTES="../../../src-tauri/nsis/cys-samebytes.ps1"
PRUNE="../../../src-tauri/nsis/cys-runtime-prune.ps1"
cp "$SAMEBYTES" build/nsis/cys-samebytes.ps1
cp "$PRUNE" build/nsis/cys-runtime-prune.ps1

SIDE_CYS=build/binaries/cys-x86_64-pc-windows-msvc.exe
SIDE_CYSD=build/binaries/cysd-x86_64-pc-windows-msvc.exe
"$PYTHON" make_versioned_pe.py --version "$VER" --out "$SIDE_CYS"
"$PYTHON" make_versioned_pe.py --version "$VER" --out "$SIDE_CYSD"
"$PYTHON" make_versioned_pe.py --version "$VER" --out build/binaries/cys-app.exe

# ── positive: the real hook must compile ──────────────────────────────────────
# -WX: any makensis warning fails the harness (the real build treats hook warnings as
# failures too — see IMPL-SPEC W5-2). -INPUTCHARSET UTF8 mirrors the tauri bundler.
"$MAKENSIS" -V2 -WX -INPUTCHARSET UTF8 harness.nsi
[ -f build/harness-setup.exe ] || { echo "FAIL: harness-setup.exe not produced" >&2; exit 2; }

# ── negative controls: each poisoned input must fail with the CONTRACT §5 token ──
# The token strings are the frozen NSIS-CONTRACT.md §5 '컴파일 실패 문자열' — verbatim,
# no invention. A negative that exits 0, or fails WITHOUT its token, is a guard regression.
expect_fail_with() { # $1=token  $2=label
  local token="$1" label="$2" out rc
  set +e
  out=$("$MAKENSIS" -V2 -WX -INPUTCHARSET UTF8 harness.nsi 2>&1)
  rc=$?
  set -e
  if [ "$rc" -eq 0 ]; then
    echo "FAIL[$label]: poisoned input COMPILED (exit 0) — the compile-time guard is gone" >&2
    exit 1
  fi
  if ! printf '%s' "$out" | grep -qF "$token"; then
    echo "FAIL[$label]: compile failed but WITHOUT the contract token '$token' — wording drift disables the CI grep belts" >&2
    printf '%s\n' "$out" | tail -20 >&2
    exit 1
  fi
  echo "nsis-hook-compile: $label OK (refused with '$token')"
}

# N1 — versionless PE sidecar: POSIX makensis defines EMPTY values instead of erroring
# (measured), so only the hook's own empty-guard stands between this and a blind oracle.
"$PYTHON" make_versioned_pe.py --version "$VER" --no-version --pad 70000 --out "$SIDE_CYSD"
expect_fail_with 'refusing to build a blind oracle' 'N1 versionless sidecar'
"$PYTHON" make_versioned_pe.py --version "$VER" --out "$SIDE_CYSD"

# N2 — 0.0.0.0 stamp: a readable-but-zero VERSIONINFO is an oracle that matches nothing real.
"$PYTHON" make_versioned_pe.py --version 0.0.0.0 --out "$SIDE_CYS"
expect_fail_with 'version resource regression' 'N2 zero-stamped sidecar'
"$PYTHON" make_versioned_pe.py --version "$VER" --out "$SIDE_CYS"

# N3 — missing sidecar: the /FileExists+!error pair must refuse before !getdllversion runs.
rm -f "$SIDE_CYS"
expect_fail_with 'sidecar source not found at compile time' 'N3 missing sidecar'
"$PYTHON" make_versioned_pe.py --version "$VER" --out "$SIDE_CYS"

# N4 — token presence in the REAL hook (not the copy): the release.yml / windows-build.yml
# build-log belts grep for these exact strings; wording drift silently disables them.
for tok in 'refusing to build a blind oracle' \
           'sidecar source not found at compile time' \
           'version resource regression'; do
  grep -qF "$tok" "$HOOK" || {
    echo "FAIL[N4]: contract token '$tok' not found verbatim in $HOOK — CI grep belts are blind" >&2
    exit 1
  }
done
echo "nsis-hook-compile: N4 OK (all 3 CONTRACT §5 tokens verbatim in the hook)"

# N5 — CONTRACT §6 taskkill census (the machine form of owner anchor ④). Outside the
# NSIS_HOOK_PREUNINSTALL macro there must be EXACTLY one taskkill — PREINSTALL's GUI-only
# '/F /IM cys-app.exe' — and no '/T' tree-kill on any line outside that macro (the GUI
# spawns cysd as a plain child: one stray tree-kill = every pane's agent dies. v0.14.27's
# CYS_SWAP_IN_PLACE kill fallback is the regression class this lane pins out).
# Contract and lane move in the same commit or not at all (NSIS-CONTRACT §6).
n5_anchors=$(grep -c 'NSIS_HOOK_PREUNINSTALL' "$HOOK" || true)
if [ "$n5_anchors" -ne 1 ]; then
  echo "FAIL[N5]: 'NSIS_HOOK_PREUNINSTALL' appears $n5_anchors times in the hook (want exactly 1) — the census window below is ambiguous; re-derive CONTRACT §6 before touching kills" >&2
  exit 1
fi
n5_total=$(grep -c 'taskkill' "$HOOK" || true)
n5_inside=$(awk '/NSIS_HOOK_PREUNINSTALL/,/!macroend/' "$HOOK" | grep -c 'taskkill' || true)
if [ "$n5_total" -ne 10 ] || [ "$n5_inside" -ne 9 ]; then
  echo "FAIL[N5]: taskkill census drifted — file total=$n5_total (contract: 10), inside PREUNINSTALL=$n5_inside (contract: 9)" >&2
  exit 1
fi
n5_outside=$(awk '/NSIS_HOOK_PREUNINSTALL/,/!macroend/{next} {print}' "$HOOK" | grep 'taskkill' || true)
if ! printf '%s' "$n5_outside" | grep -qF '/F /IM cys-app.exe'; then
  echo "FAIL[N5]: the single taskkill outside PREUNINSTALL is not the GUI-only '/F /IM cys-app.exe':" >&2
  printf '%s\n' "$n5_outside" >&2
  exit 1
fi
if printf '%s' "$n5_outside" | grep -q '/T'; then
  echo "FAIL[N5]: tree-kill (/T) outside PREUNINSTALL — the every-pane-dies class (owner anchor ④):" >&2
  printf '%s\n' "$n5_outside" >&2
  exit 1
fi
echo "nsis-hook-compile: N5 OK (taskkill census 9 inside PREUNINSTALL / 10 total; the 1 outside is GUI-only, no /T)"

# N7 — (cysr-alias · 2026-09-16) command alias pin. POSTINSTALL must copy the verified cys.exe
# to cysr.exe on the success branch (after cys_post_ok — never before the gates), and
# PREUNINSTALL must delete it (the uninstaller does not track hook-created files).
n7_post=$(awk '/^cys_post_ok:/,/!macroend/' "$HOOK" | grep -c 'CopyFiles /SILENT "\$INSTDIR\\cys.exe" "\$INSTDIR\\cysr.exe"' || true)
n7_early=$(awk '/NSIS_HOOK_POSTINSTALL/,/^cys_post_ok:/' "$HOOK" | grep -c 'cysr.exe' || true)
n7_un=$(awk '/NSIS_HOOK_PREUNINSTALL/,/!macroend/' "$HOOK" | grep -c 'Delete "\$INSTDIR\\cysr.exe"' || true)
if [ "$n7_post" != "1" ] || [ "$n7_early" != "0" ] || [ "$n7_un" != "1" ]; then
  echo "FAIL[N7]: cysr alias drifted — copy after cys_post_ok=$n7_post (want 1) · mentions before cys_post_ok=$n7_early (want 0) · uninstall delete=$n7_un (want 1)" >&2
  exit 1
fi
echo "nsis-hook-compile: N7 OK (cysr.exe copied only on the success branch; removed on uninstall)"

# N6 — checklist anchors are real. docs/WINDOWS-UPGRADE-ATOMICITY-CHECKLIST.md cites the
# hook by ANCHOR (macro/label/function names — raw line numbers rotted twice, R2/R3):
# every cited anchor must exist verbatim in the hook, and raw hook line-number citations
# must not come back. Renaming a hook anchor without updating the checklist reddens here.
CHECKLIST="../../../docs/WINDOWS-UPGRADE-ATOMICITY-CHECKLIST.md"
if [ -f "$CHECKLIST" ]; then
  n6_missing=0
  for a in $(grep -oE 'CYS_[A-Z][A-Z_]+|cys_[a-z0-9]+_[a-z0-9]+|\.onInstFailed|\.onUserAbort|NSIS_HOOK_[A-Z]+' "$CHECKLIST" | sort -u); do
    if ! grep -qF "$a" "$HOOK"; then
      echo "FAIL[N6]: checklist cites hook anchor '$a' which does not exist in the hook — renamed/deleted anchor; update the checklist in the same commit" >&2
      n6_missing=1
    fi
  done
  [ "$n6_missing" -eq 0 ] || exit 1
  if grep -nE '(훅|hook)[^:0-9]{0,12}:[0-9]{2,3}' "$CHECKLIST" >&2; then
    echo "FAIL[N6]: raw hook line-number citation in the checklist (lines above) — cite anchors, not line numbers (they rot on every hook edit)" >&2
    exit 1
  fi
  echo "nsis-hook-compile: N6 OK (all checklist hook anchors exist; no raw line citations)"
else
  echo "FAIL[N6]: checklist not found at $CHECKLIST" >&2
  exit 1
fi

# N8 — (cysr-product-rename · 2026-09-16) rename migration pins. The install dir must be
# pinned back to the daemon state dir BEFORE the unlock sweep and the placement touch
# $INSTDIR; the legacy-name cleanup must run after the desktop shortcut call, remove only
# registry keys/shortcuts (never the folder = state dir), and delete exactly 2 keys.
n8_pin_line=$(grep -n '^cys_pre_dir_kept:' "$HOOK" | head -1 | cut -d: -f1)
n8_sweep_line=$(grep -n 'unlock-sweep.ps1" w' "$HOOK" | head -1 | cut -d: -f1)
# the hook is CRLF (.gitattributes) — strip CR so line-anchored patterns can match
n8_mig=$(awk '/Call CreateOrUpdateDesktopShortcut/,/^cys_post_legacy_done:/' "$HOOK" | tr -d '\r')
n8_rm=$(printf '%s\n' "$n8_mig" | grep -cE 'RMDir|Delete "\$INSTDIR' || true)
n8_keys=$(printf '%s\n' "$n8_mig" | grep -c 'DeleteRegKey' || true)
n8_legacy=$(grep -c '!define CYS_LEGACY_PRODUCT "cys"' "$HOOK" || true)
n8_pre=$(awk '/^cys_pre_single:/,/^cys_pre_dir_kept:/' "$HOOK" | tr -d '\r')
n8_pinbody=$(printf '%s\n' "$n8_pre" | grep -cE '^  StrCmp \$INSTDIR "\$LOCALAPPDATA\\\$\{PRODUCTNAME\}" 0 cys_pre_dir_kept$|^  StrCpy \$INSTDIR \$R0$|^  SetOutPath \$INSTDIR$' || true)
n8_guards=$(printf '%s\n' "$n8_mig" | grep -cE '^  StrCmp \$R0 "\$INSTDIR" ' || true)
# N8-b — (2026-09-16 · T7 R2) the stray new-name folder sweep. The template runs
# `SetOutPath $INSTDIR` (installer.nsi:639) BEFORE this hook, so it CREATES
# $LOCALAPPDATA\<productName> before the pin can redirect; the pin block removes that
# leftover. Three things must hold and none of them is visible to the model (the pin
# block is out of its scope), so they are pinned statically here:
#   · exactly one RMDir in the pre block, and it names the template default
#   · it is NEVER recursive — `RMDir /r` there would delete a real installation
#     someone had put in that folder, which is the whole point of the empty-only cap
#   · it is skipped when the pin target IS that folder (StrCmp … cys_pre_dir_pinned 0)
n8_rmdir=$(printf '%s\n' "$n8_pre" | grep -cE '^  RMDir "\$LOCALAPPDATA\\\$\{PRODUCTNAME\}"$' || true)
n8_rmdir_rec=$(printf '%s\n' "$n8_pre" | grep -cE '^[[:space:]]*RMDir[[:space:]]+/[rR]' || true)
n8_rmdir_guard=$(printf '%s\n' "$n8_pre" | grep -cE '^  StrCmp \$INSTDIR "\$LOCALAPPDATA\\\$\{PRODUCTNAME\}" cys_pre_dir_pinned 0$' || true)
if [ -z "$n8_pin_line" ] || [ -z "$n8_sweep_line" ] || [ "$n8_pin_line" -ge "$n8_sweep_line" ] \
   || [ "$n8_rm" != "0" ] || [ "$n8_keys" != "2" ] || [ "$n8_legacy" != "1" ] \
   || [ "$n8_pinbody" != "3" ] || [ "$n8_guards" != "2" ] \
   || [ "$n8_rmdir" != "1" ] || [ "$n8_rmdir_rec" != "0" ] || [ "$n8_rmdir_guard" != "1" ]; then
  echo "FAIL[N8]: rename migration drifted — pin line=$n8_pin_line (must be < sweep line=$n8_sweep_line) · folder deletes in migration=$n8_rm (want 0) · DeleteRegKey=$n8_keys (want 2) · legacy define=$n8_legacy (want 1) · pin body lines=$n8_pinbody (want 3) · ownership guards=$n8_guards (want 2) · stray-folder RMDir=$n8_rmdir (want 1) · recursive RMDir=$n8_rmdir_rec (want 0) · its skip guard=$n8_rmdir_guard (want 1)" >&2
  exit 1
fi
echo "nsis-hook-compile: N8 OK (install dir pinned before sweep; stray new-name folder swept non-recursively behind its guard; legacy cleanup deletes 2 keys + shortcuts, never the state folder)"

# N9 — (1.1.11 · cysr-1111-installer) content oracle pins. VERSIONINFO is not identity: a
# same-version rebuild (1.1.10.0 == 1.1.10.0, other bytes) held by a running CLI/daemon is
# skipped silently by the template's `SetOverwrite try` File, and the old ① version
# short-circuit then reported exit 0 over the stale bytes (2026-10-22 kit B field run).
#   · CYS_PLACE consumes the version verdict ($R2 "fresh") only AFTER its `.new` extraction, and
#     the first such use is the step 4-b gate (no version short-circuit)
#   · step 4-b runs cys-samebytes.ps1 on canonical vs `.new` and only exit "0" skips placement
#   · POSTINSTALL ships the helper (File from nsis\) BEFORE the first CYS_PLACE
#   · the helper is pure ASCII (Windows PowerShell 5.1 reads a BOM-less script as ANSI)
n9_place=$(awk '/^!macro CYS_PLACE /,/^!macroend/' "$HOOK" | tr -d '\r')
n9_ex=$(printf '%s\n' "$n9_place" | grep -n 'File "/oname=\$INSTDIR\\\${BIN}.new.exe"' | head -1 | cut -d: -f1 || true)
n9_done=$(printf '%s\n' "$n9_place" | grep -n 'StrCmp \$R2 "fresh"' | head -1 || true)
n9_first_gate=$(printf '%s' "$n9_done" | grep -cE ':  StrCmp \$R2 "fresh" 0 cys_pl_vacate_\$\{TAG\}$' || true)
n9_done=$(printf '%s' "$n9_done" | cut -d: -f1)
n9_call=$(printf '%s\n' "$n9_place" | grep -c "nsExec::Exec 'powershell -NoProfile -ExecutionPolicy Bypass -File \"\$PLUGINSDIR\\\\cys-samebytes.ps1\" \"\$INSTDIR\\\\\${BIN}.exe\" \"\$INSTDIR\\\\\${BIN}.new.exe\"'" || true)
n9_gate=$(printf '%s\n' "$n9_place" | grep -cE '^  StrCmp \$8 "0" 0 cys_pl_differ_\$\{TAG\}$' || true)
n9_post=$(awk '/^!macro NSIS_HOOK_POSTINSTALL/,/^!macroend/' "$HOOK" | tr -d '\r')
n9_ship=$(printf '%s\n' "$n9_post" | grep -n 'File "/oname=\$PLUGINSDIR\\cys-samebytes.ps1" "\${CYS_HOOK_DIR}\\nsis\\cys-samebytes.ps1"' | head -1 | cut -d: -f1 || true)
n9_first=$(printf '%s\n' "$n9_post" | grep -n '!insertmacro CYS_PLACE' | head -1 | cut -d: -f1 || true)
n9_nonascii=$(LC_ALL=C grep -c '[^[:print:][:space:]]' "$SAMEBYTES" || true)
if [ -z "$n9_ex" ] || [ -z "$n9_done" ] || [ "$n9_done" -le "$n9_ex" ] || [ "$n9_call" != "1" ] \
   || [ "$n9_first_gate" != "1" ] || [ "$n9_gate" != "1" ] || [ -z "$n9_ship" ] || [ -z "$n9_first" ] || [ "$n9_ship" -ge "$n9_first" ] \
   || [ "$n9_nonascii" != "0" ]; then
  echo "FAIL[N9]: content oracle drifted — .new extract line=$n9_ex · first use of the version verdict=$n9_done (must be after extract) and be the 4-b gate=$n9_first_gate (want 1) · samebytes call=$n9_call (want 1) · exit-0 gate=$n9_gate (want 1) · helper shipped at=$n9_ship (must be < first CYS_PLACE=$n9_first) · non-ASCII lines in helper=$n9_nonascii (want 0)" >&2
  exit 1
fi
echo "nsis-hook-compile: N9 OK (no version short-circuit before extraction; samebytes gate on exit 0 only; helper shipped before placement; helper ASCII)"

# N10 — the helper's exit-code contract, run for real (pwsh). 0 same · 1 different (same size
# and different size) · 2 undecidable (missing file / no args). The hook reads only "0".
PWSH="${PWSH:-pwsh}"
command -v "$PWSH" >/dev/null 2>&1 || { echo "FAIL[N10]: pwsh not found (set PWSH=...) — the helper contract is unmeasured, which is not a pass" >&2; exit 1; }
N10=build/n10
mkdir -p "$N10"
printf 'MZ-same-bytes-0123456789' > "$N10/a.exe"
cp "$N10/a.exe" "$N10/b.exe"
printf 'MZ-same-bytes-0123456780' > "$N10/c.exe"
printf 'MZ-longer-by-some-bytes-0123456789' > "$N10/d.exe"
n10() { set +e; "$PWSH" -NoProfile -File "$SAMEBYTES" "$@" >/dev/null 2>&1; local rc=$?; set -e; echo "$rc"; }
n10_same=$(n10 "$N10/a.exe" "$N10/b.exe")
n10_diff=$(n10 "$N10/a.exe" "$N10/c.exe")
n10_size=$(n10 "$N10/a.exe" "$N10/d.exe")
n10_miss=$(n10 "$N10/a.exe" "$N10/missing.exe")
n10_none=$(n10)
if [ "$n10_same" != "0" ] || [ "$n10_diff" != "1" ] || [ "$n10_size" != "1" ] || [ "$n10_miss" != "2" ] || [ "$n10_none" != "2" ]; then
  echo "FAIL[N10]: cys-samebytes.ps1 exit contract broken — same=$n10_same (want 0) · diff=$n10_diff (want 1) · size=$n10_size (want 1) · missing=$n10_miss (want 2) · no-args=$n10_none (want 2)" >&2
  exit 1
fi
echo "nsis-hook-compile: N10 OK (cys-samebytes.ps1: same=0 diff=1 size=1 missing=2 no-args=2)"

# N11 — (1.1.11 · cysr-1111-installer) stale dist-info prune. The installer extracts runtime\ over
# the old tree file by file, so a bundled package whose version changed leaves its old
# <name>-<ver>.dist-info behind = runtime-seal "added" (2026-10-22: pip-26.2.2.dist-info, FAIL 32).
#   static: POSTINSTALL ships cys-runtime-prune.ps1 and runs it ONLY on the success branch
#           (after cys_post_ok), with the install root; the helper is pure ASCII
#   e2e:    a real manifest (javis_runtime_seal.py emit) + residue → seal FAILs (the field state);
#           after the real helper runs under pwsh → seal PASSES; a user's own dist-info, package
#           code, a symlinked stale dist-info (and its target) all survive; no manifest → no-op
n11_post=$(awk '/^!macro NSIS_HOOK_POSTINSTALL/,/^!macroend/' "$HOOK" | tr -d '\r')
n11_ok=$(printf '%s\n' "$n11_post" | grep -n '^cys_post_ok:' | head -1 | cut -d: -f1 || true)
n11_ship=$(printf '%s\n' "$n11_post" | grep -n 'File "/oname=\$PLUGINSDIR\\cys-runtime-prune.ps1" "\${CYS_HOOK_DIR}\\nsis\\cys-runtime-prune.ps1"' | head -1 | cut -d: -f1 || true)
n11_call=$(printf '%s\n' "$n11_post" | grep -n "nsExec::ExecToLog 'powershell -NoProfile -ExecutionPolicy Bypass -File \"\$PLUGINSDIR\\\\cys-runtime-prune.ps1\" \"\$INSTDIR\"'" || true)
n11_calls=$(printf '%s\n' "$n11_call" | grep -c . || true)
n11_call=$(printf '%s\n' "$n11_call" | head -1 | cut -d: -f1)
n11_nonascii=$(LC_ALL=C grep -c '[^[:print:][:space:]]' "$PRUNE" || true)
if [ -z "$n11_ok" ] || [ -z "$n11_ship" ] || [ -z "$n11_call" ] || [ "$n11_calls" != "1" ] \
   || [ "$n11_ship" -le "$n11_ok" ] || [ "$n11_call" -le "$n11_ship" ] || [ "$n11_nonascii" != "0" ]; then
  echo "FAIL[N11]: runtime prune wiring drifted — cys_post_ok line=$n11_ok · helper shipped at=$n11_ship · called at=$n11_call (calls=$n11_calls, want 1; order must be cys_post_ok < ship < call) · non-ASCII lines in helper=$n11_nonascii (want 0)" >&2
  exit 1
fi
SEAL="../../../cysjavis-pack/bin/javis_runtime_seal.py"
N11=build/n11
SP=runtime/python/Lib/site-packages
mk() { mkdir -p "$(dirname "$1")"; printf '%s' "$2" > "$1"; }
rm -rf "$N11"
mk "$N11/inst/$SP/pip-26.2.1.dist-info/METADATA" 'Name: pip 26.2.1'
mk "$N11/inst/$SP/pip-26.2.1.dist-info/RECORD" 'pip/__init__.py'
mk "$N11/inst/$SP/pip/__init__.py" '__version__ = "26.2.1"'
mk "$N11/inst/$SP/Setuptools-80.0.dist-info/METADATA" 'Name: setuptools'
# (cysr-1111-adv-fixes #4) a shipped dist-info whose (non-normalized) name itself holds '-'
mk "$N11/inst/$SP/python-dateutil-2.9.0.dist-info/METADATA" 'Name: python-dateutil'
mk "$N11/inst/runtime/git/etc/profile" 'export X=1'
"$PYTHON" "$SEAL" emit --root "$N11/inst/runtime" --out "$N11/inst/runtime-manifest.json" >/dev/null
# the field residue: the previous kit's pip dist-info + a case/separator variant of a shipped name
mk "$N11/inst/$SP/pip-26.2.2.dist-info/METADATA" 'Name: pip 26.2.2'
mk "$N11/inst/$SP/pip-26.2.2.dist-info/licenses/LICENSE.txt" 'MIT'
mk "$N11/inst/$SP/setuptools-79.0.dist-info/RECORD" 'x'
mk "$N11/inst/$SP/python-dateutil-2.8.2.dist-info/RECORD" 'x'
n11_seal() { set +e; "$PYTHON" "$SEAL" verify --root "$N11/inst/runtime" --manifest "$N11/inst/runtime-manifest.json" >/dev/null 2>&1; local rc=$?; set -e; echo "$rc"; }
n11_before=$(n11_seal)
# negatives the prune must leave alone (each is reported by the seal, never silently deleted)
mkdir -p "$N11/inst2"; cp -R "$N11/inst/." "$N11/inst2/"
mk "$N11/inst2/$SP/userpkg-1.0.dist-info/METADATA" 'Name: userpkg'
# a user's dist-info sharing only the first '-' segment with a shipped name: key = name before the LAST '-'
mk "$N11/inst2/$SP/python-jose-3.3.0.dist-info/METADATA" 'Name: python-jose'
mk "$N11/inst2/$SP/pip/_new_module.py" 'x = 1'
mk "$N11/outside/keep/LICENSE" 'outside'
ln -s "$(cd "$N11/outside" && pwd)/keep" "$N11/inst2/$SP/pip-26.2.0.dist-info"
mkdir -p "$N11/inst2/$SP/pip-25.0.dist-info"; ln -s "$(cd "$N11/outside" && pwd)/keep" "$N11/inst2/$SP/pip-25.0.dist-info/inner"
mkdir -p "$N11/inst3"; cp -R "$N11/inst/." "$N11/inst3/"; rm -f "$N11/inst3/runtime-manifest.json"
"$PWSH" -NoProfile -File "$PRUNE" "$N11/inst"  > "$N11/out1.log" 2>&1 || true
"$PWSH" -NoProfile -File "$PRUNE" "$N11/inst2" > "$N11/out2.log" 2>&1 || true
"$PWSH" -NoProfile -File "$PRUNE" "$N11/inst3" > "$N11/out3.log" 2>&1 || true
n11_after=$(n11_seal)
n11_bad=""
[ "$n11_before" = "1" ] || n11_bad="$n11_bad residue-not-seen-by-seal(rc=$n11_before)"
[ "$n11_after" = "0" ] || n11_bad="$n11_bad seal-still-fails-after-prune(rc=$n11_after)"
[ ! -e "$N11/inst/$SP/pip-26.2.1.dist-info/METADATA" ] && n11_bad="$n11_bad shipped-dist-info-removed"
[ -e "$N11/inst/$SP/pip/__init__.py" ] || n11_bad="$n11_bad package-code-removed"
[ -e "$N11/inst2/$SP/userpkg-1.0.dist-info/METADATA" ] || n11_bad="$n11_bad user-dist-info-removed"
[ -e "$N11/inst2/$SP/python-jose-3.3.0.dist-info/METADATA" ] || n11_bad="$n11_bad user-dist-info-with-dash-in-name-removed"
[ -e "$N11/inst/$SP/python-dateutil-2.9.0.dist-info/METADATA" ] || n11_bad="$n11_bad shipped-dash-name-dist-info-removed"
[ -e "$N11/inst2/$SP/pip/_new_module.py" ] || n11_bad="$n11_bad package-code-file-removed"
[ -L "$N11/inst2/$SP/pip-26.2.0.dist-info" ] || n11_bad="$n11_bad symlinked-dist-info-removed"
[ -e "$N11/inst2/$SP/pip-25.0.dist-info/inner" ] || n11_bad="$n11_bad dist-info-holding-a-link-removed"
[ -e "$N11/outside/keep/LICENSE" ] || n11_bad="$n11_bad link-target-deleted"
[ -e "$N11/inst2/$SP/pip-26.2.2.dist-info" ] && n11_bad="$n11_bad inst2-residue-kept"
[ -e "$N11/inst3/$SP/pip-26.2.2.dist-info/METADATA" ] || n11_bad="$n11_bad pruned-without-manifest"
grep -q '^cys-runtime-prune: skipped (no runtime-manifest.json' "$N11/out3.log" || n11_bad="$n11_bad no-manifest-not-a-deliberate-skip"
grep -q 'cys-runtime-prune: stale-dist-info removed=3 failed=0' "$N11/out1.log" || n11_bad="$n11_bad summary-line($(tail -1 "$N11/out1.log"))"
if [ -n "$n11_bad" ]; then
  echo "FAIL[N11]: stale dist-info prune contract broken:$n11_bad" >&2
  exit 1
fi
echo "nsis-hook-compile: N11 OK (prune wired after cys_post_ok; seal FAIL with residue → PASS after prune; user dist-info · package code · links kept; no manifest = no-op)"

# ── re-verify the positive with restored inputs (negatives must leave no residue) ──
"$MAKENSIS" -V2 -WX -INPUTCHARSET UTF8 harness.nsi >/dev/null
echo "nsis-hook-compile: OK (hook compiled, macros inserted, getdllversion oracle exercised, 3 negative controls + token, census and anchor pins verified)"
