#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_trash_old_marking.py — S8 D-1 핀: reap 의 휴지통 블록은 **지우지 않고 표시만** 한다.

밀폐 하네스: `HOME` 과 `CYS_DEPTS_JSON` 을 임시 디렉터리로 덮어 실 휴지통
(`~/.local/state/cys-trash`)·실 레지스트리·실 소켓을 통째로 격리한다. 실 데몬을 부르지 않고
실 격리분을 건드리지 않는다 — 재현은 시험 자리에서만(부서 다섯 원칙 ⑤).

  ① 양성 — TTL 초과 격리분: 블록이 TRASH-OLD 로 알리고 **엔트리는 그대로 남는다**(종전 코드는
     여기서 `rm -rf` 했다). 세어 둔 값은 `TRASH-OLD=1`.
  ★한계: `cys-dept reap` 명령 자체는 이 좌석에서 돌릴 수 없다(역할 게이트가 데몬 권위 역할로
     거부한다 — 실측). 그래서 ①②는 **제품 파일에서 떼어 온 그 블록의 실제 바이트**를 격리 실행한
     결과다. 명령 전체의 통합 동작은 CSO 좌석이나 CI 에서 확인할 **미실행 출하 게이트**다.
  ② 음성 — TTL 미만 격리분: TRASH-OLD 0건, 엔트리 그대로.
  ③ 핀 — 스크립트에 `rm -rf "$_td"` 도 `TRASH-EXPIRE` 토큰도 없다.
  ④ 무접촉 — 알린 뒤에도 격리분 **안의 파일 목록·내용이 바뀌지 않는다**(표식 파일을 남기지 않는다:
     그 쓰기는 미리보기와 명령 사이에 내용 집합을 바꿔 오너의 명령을 헛되게 거부시킨다).
"""
import os, subprocess, sys, tempfile, time, hashlib, json

HERE = os.path.dirname(os.path.abspath(__file__))
DEPT = os.path.join(HERE, "..", "cys-dept")
FAIL = []


def check(cond, msg):
    if not cond:
        FAIL.append(msg)
        print("  FAIL:", msg)
    else:
        print("  ok  :", msg)


def tree_fingerprint(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for f in sorted(filenames):
            p = os.path.join(dirpath, f)
            with open(p, "rb") as fh:
                out.append((os.path.relpath(p, root), hashlib.sha256(fh.read()).hexdigest()))
    return sorted(out)


def extract_block():
    """★제품 파일에서 휴지통 블록의 **실제 바이트**를 떼어 온다(손으로 베낀 사본이 아니다).

    `cys-dept reap` 자체는 이 좌석에서 실행할 수 없다 — 역할 게이트가 데몬 권위 역할(worker-2)로
    거부한다("단일소유 강제: 부서 lifecycle mutation은 CSO/GUI 전용"). 그래서 기능 확인은 그 명령을
    돌리는 것이 아니라 **그 명령의 그 블록을 떼어 격리 실행**하는 것이다. 이 시험이 증명하는 것은
    "이 블록이 지우지 않고 알린다"이고, "reap 전체가 그렇다"가 아니다(한계 명시).
    """
    src = open(DEPT, encoding="utf-8").read().splitlines()
    start = next(i for i, l in enumerate(src) if "★S8 D-1" in l)
    end = next(i for i, l in enumerate(src[start:], start) if l.strip() == "fi")
    return "\n".join(src[start:end + 1])


BLOCK = extract_block()


def run_reap(home, dry, win=None):
    """떼어 온 블록만 격리 실행한다(제품의 바이트 그대로 · 변수만 주입).

    win = None → 이 기계의 실제 `uname`(맥·리눅스). win = (build_info 출력 | None, rc) → 가짜 `uname`(MINGW64_NT)과
    가짜 `cys build-info --json`(CYS_BIN)을 주입해 윈도우 분기를 돌린다(★cysr 1.1.10 · master#4e61b71e Q1=B).
    """
    trash = os.path.join(home, ".local", "state", "cys-trash")
    prelude = ""
    env = dict(os.environ)
    if win is not None:
        out, rc = win
        fake = os.path.join(home, "fake-cys")
        with open(fake, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n[ \"$1\" = build-info ] || exit 9\n%s\nexit %d\n" % (
                "printf '%s\\n' " + json.dumps(out) if out is not None else ":", rc))
        os.chmod(fake, 0o755)
        env["CYS_BIN"] = fake
        prelude = "uname(){ echo MINGW64_NT-10.0-19045; }\n"
    script = "set -u\n%sTRASH_ROOT=%s\ndry=%d\n%s\necho \"[cys-dept] reap 완료(dry=$dry): TRASH-OLD=$nt TRASH-EXPIRE=$ne\"\n" % (
        prelude, json.dumps(trash), 1 if dry else 0, BLOCK)
    env.update(HOME=home, CYS_TRASH_TTL_DAYS="14")
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, timeout=120)
    return r.returncode, r.stdout + r.stderr


def mk_entry(trash, name, age_days):
    d = os.path.join(trash, name)
    os.makedirs(os.path.join(d, "state"), exist_ok=True)
    with open(os.path.join(d, "state", "transcripts.db"), "w", encoding="utf-8") as f:
        f.write("sole copy of a department's conversation memory")
    old = time.time() - age_days * 86400
    for p in (os.path.join(d, "state", "transcripts.db"), os.path.join(d, "state"), d):
        os.utime(p, (old, old))
    return d


def case(age_days, expect_marked):
    with tempfile.TemporaryDirectory(prefix="cys-s8-d1-") as home:
        trash = os.path.join(home, ".local", "state", "cys-trash")
        os.makedirs(trash)
        with open(os.path.join(home, "depts.json"), "w", encoding="utf-8") as f:
            json.dump({"depts": {}}, f)
        name = "dept-9-%d" % int(time.time())
        d = mk_entry(trash, name, age_days)
        before = tree_fingerprint(d)
        for dry in (True, False):
            rc, out = run_reap(home, dry)
            tag = "dry" if dry else "real"
            marked = ("TRASH-OLD %s" % d) in out
            check(marked == expect_marked,
                  "[%s · %sd] TRASH-OLD 알림 %s" % (tag, age_days, "있음" if expect_marked else "없음"))
            check("TRASH-OLD=%d" % (1 if expect_marked else 0) in out,
                  "[%s · %sd] 요약 줄 TRASH-OLD=%d" % (tag, age_days, 1 if expect_marked else 0))
            check(("TRASH-EXPIRE %s" % d) not in out and "TRASH-EXPIRE=0" in out,
                  "[%s · %sd] 정리(TRASH-EXPIRE) 0건 — 맥·리눅스는 언제나 S8" % (tag, age_days))
            check(os.path.isdir(d), "[%s · %sd] ★엔트리가 그대로 있다(지워지지 않았다)" % (tag, age_days))
        check(tree_fingerprint(d) == before,
              "[%sd] ★격리분 안의 내용이 한 바이트도 바뀌지 않았다(표식 파일 없음)" % age_days)


print("== ① 양성: TTL(14d) 초과 30일 격리분 ==")
case(30, True)
print("== ② 음성: 3일 격리분 ==")
case(3, False)
def win_case(build_info, rc, expect_reclaim, label):
    """★cysr 1.1.10 윈도우 예외: 윈도우 ∧ 앱 휴지통 삭제 꺼짐(build-info 에 `"trash_delete_supported":true` 없음)이면
    1.1.9 처럼 TTL 초과분을 정리한다 · 켜진 빌드면 S8(표시만). 3일 격리분은 어느 쪽이든 그대로다."""
    with tempfile.TemporaryDirectory(prefix="cys-1110-win-") as home:
        trash = os.path.join(home, ".local", "state", "cys-trash")
        os.makedirs(trash)
        old_d = mk_entry(trash, "dept-9-%d" % int(time.time()), 30)
        young = mk_entry(trash, "dept-8-%d" % int(time.time()), 3)
        rc_, out = run_reap(home, True, (build_info, rc))
        check(os.path.isdir(old_d), "[win %s · dry] dry 는 아무 것도 지우지 않는다" % label)
        check(("TRASH-EXPIRE %s" % old_d in out) == expect_reclaim, "[win %s · dry] TRASH-EXPIRE 알림 %s" % (label, expect_reclaim))
        rc_, out = run_reap(home, False, (build_info, rc))
        if expect_reclaim:
            check(not os.path.exists(old_d), "[win %s] ★30일 격리분이 정리됐다(1.1.9 동작)" % label)
            check("TRASH-EXPIRE=1" in out and "TRASH-OLD=0" in out, "[win %s] 요약 TRASH-EXPIRE=1 · TRASH-OLD=0" % label)
        else:
            check(os.path.isdir(old_d), "[win %s] ★30일 격리분이 그대로다(S8 — 앱에서 지운다)" % label)
            check("TRASH-OLD=1" in out and "TRASH-EXPIRE=0" in out, "[win %s] 요약 TRASH-OLD=1 · TRASH-EXPIRE=0" % label)
        check(os.path.isdir(young), "[win %s] 3일 격리분은 그대로다(TTL 미만)" % label)


print("== ⑤ 윈도우 · 삭제 꺼진 빌드(칸 false) → 1.1.9 처럼 정리 ==")
win_case('{"target":"windows-x64","trash_delete_supported":false,"version":"1.1.10"}', 0, True, "false")
print("== ⑥ 윈도우 · 칸 없는 옛 바이너리(1.1.9) → 정리 ==")
win_case('{"target":"windows-x64","version":"1.1.9"}', 0, True, "칸 없음")
print("== ⑦ 윈도우 · build-info 실패(1.1.8 이전·바이너리 없음) → 정리 ==")
win_case(None, 2, True, "실패")
print("== ⑧ 윈도우 · 삭제 켜진 빌드(trash_win_validated) → S8 표시만 ==")
win_case('{"target":"windows-x64","trash_delete_supported":true,"version":"1.1.11"}', 0, False, "true")

print("== ③ 핀: 파괴는 윈도우 예외 갈래 한 자리뿐 ==")
src = open(DEPT, encoding="utf-8").read()
check(src.count('rm -rf "$_td"') == 1, '스크립트의 rm -rf "$_td" 는 정확히 한 자리다')
_lines = BLOCK.splitlines()
_rm = next((i for i, l in enumerate(_lines) if 'rm -rf "$_td"' in l), None)
check(_rm is not None and any('if [ "$_trash_reclaim" = 1 ]' in l for l in _lines[max(0, _rm - 3):_rm]),
      'rm -rf "$_td" 는 `_trash_reclaim = 1`(윈도우 ∧ 삭제 꺼짐) 갈래 안에만 있다')
check(src.count('_trash_reclaim=1') == 1 and '*\'"trash_delete_supported":true\'*) _trash_reclaim=0' in src,
      "정리 갈래는 build-info 의 trash_delete_supported:true 가 **없을 때만** 켜진다")
check("TRASH-OLD" in src, "스크립트에 TRASH-OLD 가 있다")
check("delete from Control Center > Trash" in src, "안내 문구가 있다(누가 아니라 이 도구가 무엇을 하는지)")
print()
if FAIL:
    print("FAILED %d건" % len(FAIL))
    for f in FAIL:
        print(" -", f)
    sys.exit(1)
print("PASS — 휴지통 블록은 맥·리눅스·삭제 켜진 윈도우에서 표시만 하고, 삭제 꺼진 윈도우에서만 1.1.9 처럼 정리한다(reap 명령 전체는 미실행 게이트)")
