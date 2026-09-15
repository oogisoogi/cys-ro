#!/usr/bin/env python3
"""javis_orient_log.py — E2 Phase A: 오리엔테이션 실패 계측 (설계 DESIGN_LAZYCODEX_DISTILLATION §E2).

목적: 폴더별 컨텍스트(E2)는 '계측 선행, 조건부 파일럿'이다. 파일럿에 앞서 위임 오리엔테이션
실패(엉뚱한 대상·컨텍스트 결핍·재탐색)를 결정론으로 계측해 Phase B 진입 게이트(실패율 ≥기준치)의
근거 데이터를 쌓는다. EVENT_CONTRACT 무접촉(신규 이벤트 타입 신설 회피).

기록 규율(R4 · producer≠evaluator): master는 반려 발생 '사실'만 트리거하고, kind 분류·기록은
독립 분류주체(Agent 독립 인스턴스 또는 codex)가 수행한다. 이 규율은 도구가 아니라 운영 규율이므로
도구는 --by(분류 주체)를 필수 인자로 강제만 한다(master 단독 기록의 무효화는 운영에서 판정).

저장: $JAVIS_ROOT/_round/orientation_log.jsonl (append-only · O_APPEND · 수정·삭제 금지 = 감사 원장).
레코드: {"ts","task","kind","by","note"}.

exit codes: 0 ok · 2 usage
stdlib만 사용. 네트워크 0.
"""
import argparse
import json
import os
import sys
import time


# Windows: 콘솔 없는 부모(cysd·pythonw 브리지·GUI) 아래에서 출력을 캡처하는 콘솔 자식(cys.exe·powershell·cmd)을
# 숨김 없이 낳으면 자식마다 새 콘솔 창이 뜬다(TICKET=cysr-console-flicker-r2). 캡처하는 subprocess 호출에
# **NOWIN 을 전개한다(출력을 터미널로 흘리는 호출은 제외 — 창을 숨기면 그 출력이 사라진다). 타 OS 무동작.
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}

ROOT = os.environ.get("JAVIS_ROOT") or os.getcwd()  # 개인경로 하드코딩 금지(pack scan gate)

KINDS = ["wrong-target", "missing-context", "re-explore"]  # 오리엔테이션 실패 유형
EXIT_OK, EXIT_USAGE = 0, 2


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _log_path():
    return os.path.join(ROOT, "_round", "orientation_log.jsonl")


def _append_jsonl(path, rec):
    """append-only(O_APPEND) JSONL 1줄 기록 — 감사 원장(수정·삭제 금지)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def _read_records(path):
    """손상 줄 관대 파싱(check_manifest 관례) — 감사 원장은 일부 손상에도 통계가 서야 한다."""
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def cmd_add(a):
    rec = {"ts": _now(), "task": a.task, "kind": a.kind, "by": a.by, "note": a.note or ""}
    _append_jsonl(_log_path(), rec)
    print(json.dumps(rec, ensure_ascii=False))
    return EXIT_OK


def compute_stats(records, total=None):
    """순수 함수(self-test 밀폐 핀) — 오리엔테이션 실패 계측 통계.
    by_kind: 유형별 건수 · by_kind_ratio: 유형별 비율(전체 실패 대비) ·
    failure_rate: total(위임 총건) 주어질 때만 실패/위임 (Phase B 게이트 근거).
    ★어태커 결함2 가드: total은 양수이고 실패건 이상이어야 한다 — 위반 시 ValueError(호출부 exit 2)."""
    n = len(records)
    by_kind = {k: 0 for k in KINDS}
    unknown = 0
    for r in records:
        k = r.get("kind")
        if k in by_kind:
            by_kind[k] += 1
        else:
            unknown += 1
    stats = {
        "total_failures": n,
        "by_kind": by_kind,
        "by_kind_ratio": {k: (by_kind[k] / n if n else 0.0) for k in KINDS},
    }
    if unknown:
        stats["unknown_kind"] = unknown
    if total is not None:
        if total <= 0:
            raise ValueError("--total은 양수여야 한다(위임 총건 > 0): %r" % total)
        if total < n:
            raise ValueError("--total(%d) < 기록된 실패건(%d) — 위임 총건이 실패건보다 작을 수 없다"
                             % (total, n))
        stats["delegations_total"] = total
        stats["failure_rate"] = n / total
    return stats


def cmd_stats(a):
    try:
        stats = compute_stats(_read_records(_log_path()), total=a.total)
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return EXIT_USAGE
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    return EXIT_OK


def cmd_self_test(args):
    """밀폐 자기검증(tmpdir + JAVIS_ROOT 주입 — 실장부 오염 금지). add append·--by 필수·
    kind 검증·stats 비율·failure_rate·빈 로그 경계."""
    import subprocess
    import tempfile

    self_path = os.path.abspath(__file__)

    def run(root, argv):
        env = dict(os.environ)
        env["JAVIS_ROOT"] = root
        r = subprocess.run([sys.executable, self_path] + argv,
                           capture_output=True, text=True, env=env, **NOWIN)
        return r.returncode, r.stdout, r.stderr

    try:
        # 순수 함수 배터리(subprocess 없이 결정론 핀)
        assert compute_stats([]) == {
            "total_failures": 0, "by_kind": {k: 0 for k in KINDS},
            "by_kind_ratio": {k: 0.0 for k in KINDS}}, "빈 입력 통계 오류"
        recs = [{"kind": "wrong-target"}, {"kind": "wrong-target"}, {"kind": "re-explore"}]
        s = compute_stats(recs, total=20)
        assert s["total_failures"] == 3 and s["by_kind"]["wrong-target"] == 2, "건수 집계 오류: %s" % s
        assert abs(s["by_kind_ratio"]["wrong-target"] - 2 / 3) < 1e-9, "비율 산출 오류: %s" % s
        assert abs(s["failure_rate"] - 3 / 20) < 1e-9, "failure_rate 산출 오류: %s" % s
        assert compute_stats([{"kind": "bogus"}])["unknown_kind"] == 1, "미지 kind 미집계"
        # ★어태커 결함2 가드(순수): total<=0·total<실패건 → ValueError
        for bad in (0, -5):
            try:
                compute_stats(recs, total=bad)
                assert False, "total=%r가 ValueError를 안 냄" % bad
            except ValueError:
                pass
        try:
            compute_stats(recs, total=2)  # 실패 3건 > total 2
            assert False, "total<실패건이 ValueError를 안 냄"
        except ValueError:
            pass
        assert compute_stats(recs, total=3)["failure_rate"] == 1.0, "total==실패건 경계(1.0) 오류"

        with tempfile.TemporaryDirectory(prefix="javis-orient-") as root:
            # add: append 누적(O_APPEND)
            rc, _, e = run(root, ["add", "--task", "T1", "--kind", "wrong-target",
                                  "--by", "codex", "--note", "엉뚱한 폴더"])
            assert rc == EXIT_OK, "add 실패: %s" % e
            rc, _, e = run(root, ["add", "--task", "T2", "--kind", "missing-context", "--by", "agy"])
            assert rc == EXIT_OK, "add(2) 실패: %s" % e
            recs2 = _read_records(os.path.join(root, "_round", "orientation_log.jsonl"))
            assert len(recs2) == 2, "append 누적 실패: %s" % recs2
            assert recs2[0]["by"] == "codex" and recs2[1]["kind"] == "missing-context", "레코드 내용 오류"

            # --by 필수: 누락 시 argparse 거부(exit 2)
            rc, _, _ = run(root, ["add", "--task", "T3", "--kind", "re-explore"])
            assert rc == EXIT_USAGE, "--by 누락이 2를 안 냄: %s" % rc

            # kind 검증: 미허용 kind → exit 2(choices)
            rc, _, _ = run(root, ["add", "--task", "T4", "--kind", "bogus", "--by", "codex"])
            assert rc == EXIT_USAGE, "미허용 kind가 2를 안 냄: %s" % rc

            # stats: 실제 CLI 경로로 집계(총 2건 — bogus/누락은 append되지 않음)
            rc, out, e = run(root, ["stats", "--total", "20"])
            assert rc == EXIT_OK, "stats 실패: %s" % e
            js = json.loads(out)
            assert js["total_failures"] == 2 and js["failure_rate"] == 2 / 20, "stats CLI 집계 오류: %s" % js

            # ★어태커 결함2 CLI 가드: --total 0 → exit 2, --total 1(실패 2건 미만) → exit 2
            rc, _, err = run(root, ["stats", "--total", "0"])
            assert rc == EXIT_USAGE and "양수" in err, "--total 0 미거부: rc=%s err=%s" % (rc, err)
            rc, _, err = run(root, ["stats", "--total", "1"])
            assert rc == EXIT_USAGE and "실패건" in err, "--total<실패건 미거부: rc=%s err=%s" % (rc, err)

            # 빈 로그 경계: 새 root에서 stats는 total 0(무크래시)
            with tempfile.TemporaryDirectory(prefix="javis-orient-empty-") as root2:
                rc, out, e = run(root2, ["stats"])
                assert rc == EXIT_OK and json.loads(out)["total_failures"] == 0, "빈 로그 stats 오류: %s" % e
    except AssertionError as ex:
        print("javis_orient_log self-test FAIL: %s" % ex, file=sys.stderr)
        return 1
    print("javis_orient_log self-test OK (add append·--by 필수·kind 검증·stats 비율·"
          "failure_rate·--total 가드(0·<실패건)·빈 로그 경계 · 밀폐 tmpdir+JAVIS_ROOT)")
    return EXIT_OK


def main(argv=None):
    # preflight 호환: `--self-test`는 subcommand 없이도 동작해야 한다(orchestra 관례 준용·가로채기).
    if "--self-test" in (sys.argv if argv is None else argv):
        return cmd_self_test(None)
    p = argparse.ArgumentParser(description="오리엔테이션 실패 계측 (E2 Phase A)")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("add", help="오리엔테이션 실패 1건 기록")
    c.add_argument("--task", required=True, help="반려된 위임 태스크 id")
    c.add_argument("--kind", required=True, choices=KINDS, help="실패 유형")
    c.add_argument("--by", required=True,
                   help="분류 주체(R4 — 독립 리뷰어: codex/agy/agent 인스턴스 · master 단독 기록 무효)")
    c.add_argument("--note", default=None, help="자유 메모(폴더·상황 맥락 등)")
    c.set_defaults(fn=cmd_add)

    c = sub.add_parser("stats", help="계측 통계·비율 산출")
    c.add_argument("--total", type=int, default=None,
                   help="위임 총건(주면 failure_rate 산출 — Phase B 게이트 근거)")
    c.set_defaults(fn=cmd_stats)

    sub.add_parser("self-test", help="밀폐 자기검증(tmpdir + JAVIS_ROOT 주입)"
                   ).set_defaults(fn=cmd_self_test)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
