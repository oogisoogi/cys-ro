#!/usr/bin/env python3
"""dbg-D3 F4 검출 시험 — 부서 카드 뒤 사람 답 분류기(`javis_dept_request.classify_answer`)의 오분류 0.

결함(2026-09-23 실측 · fd356c06): 「취소하지 말고 진행해」·「안 할 이유 없죠, 만들어요」(동의) → "no" → confirm 이
제안을 버리고 「「아니요」라고 하셔서 만들지 않았습니다」를 말한다. 「진행 상황 알려줘」·「예산은 얼마나 들어」·
「그러면 이름을 교육지원부로 해 줘」(질문·수정) → "yes".

계약(master#d90faae7): 표본 ≥20 · 오분류 0 · 애매하면 "other"(= confirm 이 「직접 「네」」로 되묻는다).
오분류 정의 = 기대가 yes 인데 no/other 가 아닌 반대 판정(yes↔no) 또는 기대 other 인데 yes/no.
  · 동의가 other 로 떨어지는 것은 「되묻기」라 허용하지 않는다 — 명백한 동의 표본(아래 YES)은 yes 여야 한다.
  · 이중부정·양쪽 뜻 문장은 기대값을 other 로 둔다(판정 대신 되묻기가 계약).
사용: `python3 <this> [--bin <javis_dept_request.py 가 있는 폴더>]` · 0 초록 · 1 적색 · 2 측정 실패.
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BIN = os.path.dirname(HERE)

YES = ["네", "네!", "예", "응", "넵", "ㅇㅇ", "ok", "OK", "좋아요", "네 좋아요", "네 만들어 주세요",
       "그렇게 해 주세요", "알겠어요", "부탁해요", "네 부탁드립니다", "진행해", "진행해 주세요",
       "이대로 만들어 줘", "좋습니다 진행하세요", "그래요", "네, 그대로 만들어 주세요.", "닫아 주세요"]
NO = ["아니요", "아뇨", "아니", "싫어요", "취소", "취소해 주세요", "그만", "안 할래요", "그냥 안 할래요",
      "하지 마세요", "만들지 마", "필요 없어요", "됐어요", "아니 괜찮아요", "no"]
OTHER = ["취소하지 말고 진행해", "안 할 이유 없죠, 만들어요", "진행 상황 알려줘", "예산은 얼마나 들어",
         "그러면 이름을 교육지원부로 해 줘", "네 근데 이름은 바꿔 줘", "네?", "왜요?", "잠깐만요",
         "교육부 말고 홍보부로", "괜찮아요", "음...", "부서 어떻게 됐어", ""]


def load(bin_dir):
    sys.dont_write_bytecode = True
    os.environ["HOME"] = tempfile.mkdtemp()
    spec = importlib.util.spec_from_file_location("jdr_f4", os.path.join(bin_dir, "javis_dept_request.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main(argv):
    bin_dir = DEFAULT_BIN
    if len(argv) >= 2 and argv[0] == "--bin":
        bin_dir = argv[1]
    try:
        m = load(bin_dir)
        f = m.classify_answer
    except Exception as e:
        print("MEASURE-FAIL: 분류기 적재 실패 %s: %s" % (type(e).__name__, e))
        return 2
    table = [(t, "yes") for t in YES] + [(t, "no") for t in NO] + [(t, "other") for t in OTHER]
    if len(table) < 20:
        print("MEASURE-FAIL: 표본 %d < 20" % len(table))
        return 2
    bad = []
    for t, want in table:
        got = f(t)
        if got != want:
            bad.append((t, want, got))
    print("표본 %d(yes %d · no %d · other %d) · 불일치 %d" % (len(table), len(YES), len(NO), len(OTHER), len(bad)))
    for t, want, got in bad:
        sev = "★반대 판정" if {want, got} == {"yes", "no"} else ("오판정" if want == "other" else "되묻기 강등")
        print("  %-28r 기대=%-5s 실제=%-5s %s" % (t, want, got, sev))
    if bad:
        print("FAIL(F4 재현)")
        return 1
    print("PASS: 오분류 0")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
