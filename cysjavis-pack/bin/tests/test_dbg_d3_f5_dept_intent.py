#!/usr/bin/env python3
"""dbg-D3 F5 검출 시험 — 「교육부 만들어 줘」 같은 부서 이름 꼴 요청에 부서 절차 안내가 붙는가(훅 종단).

결함(2026-09-23 실측 · fd356c06): 셸 선거름(`hooks/dept-chat-inject.sh` `*부서*|*팀*`)과 파이썬 판정
(`javis_dept_request._INTENT=(부서|팀)`) 둘 다 「부서」「팀」 낱말만 봐서, 설계 문서 §1 예시 「설교준비부 만들어 줘」와
「교육부 만들어 줘」·「홍보과 만들어 줘」에 안내가 0자였다(「교육 부서 만들어 줘」는 702자).

재는 법 = **훅을 실제로 태운다**(셸 거름 + 파이썬 판정 두 층을 한 번에): 임시 HOME · CYS_ROLE=master ·
열린 제안 없음(.hook-wake 부재) · 프롬프트마다 새 요청 폴더(세션 반복 억제 회피). 안내 = stdout 에
`dept-by-chat` 이 든 훅 JSON.
  POS(안내 필수) = 설계 §1 예시 전건 + 「~부 만들어 줘」「~팀」「부서」「과」 형태
  NEG(안내 금지) = 코딩 대화의 흔한 일반어(전부·결과·일부·효과 …)
측정 선단언: 대조 문장 「교육 부서 만들어 줘」(현행도 통과하던 꼴)에 안내가 붙지 않으면 측정 실패(rc 2).
사용: `python3 <this> [--root <cysjavis-pack 을 담은 트리>]` · 0 초록 · 1 적색 · 2 측정 실패.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_PACK = os.path.dirname(os.path.dirname(HERE))

CONTROL = "교육 부서 만들어 줘"
POS = ["설교준비부 만들어 줘", "교육부 만들어 줘", "교육부를 만들어 주세요", "홍보팀 꾸려줘",
       "새가족팀 하나 새로 만들어 주세요", "행정과 만들어 줘", "홍보과 하나 만들자", "교육부 닫아 줘",
       "교육부를 없애 줘", "부서 만들어 줘", "부서 어떻게 됐어", "찬양팀을 만들어 줘", CONTROL]
NEG = ["전부 지워 줘", "결과 정리해 줘", "테스트 결과 만들어 줘", "일부만 만들어", "이 파일 내부 정리해",
       "효과 만들어 줘", "부탁해요", "코드 리뷰 해 줘", "README 만들어 줘"]


def make_pack(root):
    """repo 팩을 심링크로 복제하고 대상 트리의 두 파일(훅·도구)만 실물로 덮는다."""
    td = tempfile.mkdtemp()
    pack = os.path.join(td, "pack")
    os.makedirs(os.path.join(pack, "bin"))
    os.makedirs(os.path.join(pack, "hooks"))
    for sub in ("bin", "hooks"):
        for n in os.listdir(os.path.join(REPO_PACK, sub)):
            os.symlink(os.path.join(REPO_PACK, sub, n), os.path.join(pack, sub, n))
    for rel in ("bin/javis_dept_request.py", "hooks/dept-chat-inject.sh"):
        src = os.path.join(root, "cysjavis-pack", rel)
        dst = os.path.join(pack, rel)
        os.unlink(dst)
        shutil.copy(src, dst)
    return td, pack


def guide_len(pack, home, prompt, n):
    rq = os.path.join(home, "rq-%d" % n)
    env = {"HOME": home, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
           "CYS_ROLE": "master", "CYS_SURFACE_ID": "1", "CYS_DEPT_REQUESTS": rq, "CYS_PACK_DIR": pack,
           "PYTHONDONTWRITEBYTECODE": "1"}
    stdin = json.dumps({"prompt": prompt, "session_id": "s-%d" % n}, ensure_ascii=False)
    p = subprocess.run(["sh", os.path.join(pack, "hooks", "dept-chat-inject.sh")], input=stdin, env=env,
                       capture_output=True, text=True, timeout=30)
    return p.stdout if "dept-by-chat" in p.stdout else ""


def main(argv):
    root = os.path.dirname(REPO_PACK)
    if len(argv) >= 2 and argv[0] == "--root":
        root = argv[1]
    td, pack = make_pack(root)
    home = os.path.join(td, "home")
    os.makedirs(home)
    try:
        if not guide_len(pack, home, CONTROL, 0):
            print("MEASURE-FAIL: 대조 문장 %r 에도 안내가 없다 — 훅 하네스가 대상에 안 닿았다" % CONTROL)
            return 2
        miss = [t for i, t in enumerate(POS, 1) if not guide_len(pack, home, t, i)]
        extra = [t for i, t in enumerate(NEG, 100) if guide_len(pack, home, t, i)]
        print("POS %d · 안내 누락 %d | NEG %d · 잘못 붙음 %d" % (len(POS), len(miss), len(NEG), len(extra)))
        for t in miss:
            print("  누락: %r" % t)
        for t in extra:
            print("  오부착: %r" % t)
        if miss or extra:
            print("FAIL(F5 재현)" if miss else "FAIL(과부착)")
            return 1
        print("PASS: 부서 이름 꼴 요청 전건 안내 · 일반어 0")
        return 0
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
