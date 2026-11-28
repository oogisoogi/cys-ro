#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_idempotency_win_boot_fleet.py — preflight C53(javis_idempotency --self-test)이 **윈 꼴**에서
`cys daemon boot-fleet`(읽기 전용) 때문에 거짓 FAIL 하지 않는가(1.1.21 · TICKET=cysr-1121-pack · TODO 79).

★왜: 윈 1.1.20 실기(11-26 · 604 판정)에서 C53 거짓 FAIL 이 남았다. 원인 둘 중 하나(PATH 에 cys 없음)는 1.1.20 에서
  고쳤고(test_idempotency_no_cys_on_path), 남은 하나 = MUTATE_VERBS 의 `daemon` 통째 분류. 윈에서만
  cmd_check→boot_fleet()→_boot_fleet_query_daemon(javis_orchestra.py:266)이 `cys daemon boot-fleet` 을 subprocess 로
  부르고(unix = 소켓 직접), spy 가 그것을 mutate 로 세어 「관찰 단계에서 mutate 호출」 RED 가 됐다.
  고침 = OBSERVE_SUBVERBS 의 ("daemon","boot-fleet") 쌍 + cmd_check 화이트리스트의 `daemon`(서브동사는 boot-fleet 로 핀).
★윈 대역: javis_orchestra 모듈의 `os` 만 name="nt" 로 바꾼다(_OsNtShape) — 전역 os.name 은 그대로라 맥·리눅스 CI 에서 돈다.
★되돌리면 붉음(2026-11-27 실측 · 변이 4): ① 쌍 삭제 ② 화이트리스트 `daemon` 삭제 ③ 대역 name 을 "posix" 로
  ④ boot_fleet 캐시 비우기 삭제 — 넷 다 rc≠0.
★공허 방지: 윈 꼴 실행에서 `cys daemon boot-fleet` 호출이 spy 에 실제로 찍혔는지 센다(0 이면 윈 길을 안 탄 것).
★좁힘 확인: `daemon` 의 다른 서브동사(install·uninstall·start·stop·status·dept-status·서브동사 없음·미지)는 관찰 경로를 못 지난다.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.dont_write_bytecode = True

import javis_idempotency as idem  # noqa: E402


def main():
    fails = []

    # 1) 분류 — 이 쌍만 관찰, daemon 의 나머지는 mutate 그대로(좁힘).
    if idem.classify_cys_verb(["cys", "daemon", "boot-fleet"]) != "observe":
        fails.append("cys daemon boot-fleet 가 observe 가 아님")
    if not idem.is_observe_only(["C:\\opt\\cys\\bin\\cys.exe", "daemon", "boot-fleet"]):
        fails.append("윈 경로 cys.exe daemon boot-fleet 가 관찰 경로를 못 지남")
    if not idem.is_observe_only(["cys", "--socket", "/x", "daemon", "boot-fleet"]):
        fails.append("전역 옵션 뒤 daemon boot-fleet 가 관찰 경로를 못 지남")
    for argv in (["cys", "daemon", "install"], ["cys", "daemon", "uninstall"], ["cys", "daemon", "start"],
                 ["cys", "daemon", "stop"], ["cys", "daemon", "status"], ["cys", "daemon", "dept-status", "dept-1"],
                 ["cys", "daemon"], ["cys", "daemon", "no-such-sub"], ["cys", "daemon", "install", "boot-fleet"]):
        if idem.is_observe_only(argv):
            fails.append("%s 가 관찰 경로를 지남(좁힘 깨짐)" % " ".join(argv[1:]))
    if idem.OBSERVE_SUBVERBS & idem.MUTATE_SUBVERBS:
        fails.append("서브동사 분류 충돌")

    # 2) 맥·리눅스 꼴은 종전 그대로(소켓 길 · daemon 호출 0). ★먼저 돈다 — 소켓 길이 boot_fleet 캐시를 채우므로
    #    뒤의 윈 꼴이 캐시 비우기 없이는 subprocess 를 안 부른다(self-test 순서와 같음 · 변이 ④를 잡는 자리).
    try:
        n_unix = idem._spy_cmd_check(win_shape=False)
        if n_unix and os.name != "nt":     # 진짜 윈 호스트에서는 대역 없이도 윈 길이라 0 이 아니다(정상)
            fails.append("유닉스 꼴에서 cys daemon 이 subprocess 로 불림(%d회) — 소켓 직접 길이 바뀜" % n_unix)
    except AssertionError as e:
        fails.append("유닉스 꼴 cmd_check RED: %s" % e)

    # 3) 윈 꼴 cmd_check — 실제로 boot-fleet 길을 타고(공허 방지) 관찰 계약을 지키는가.
    try:
        n = idem._spy_cmd_check(win_shape=True)
        if not n:
            fails.append("윈 꼴 cmd_check 가 cys daemon boot-fleet 을 부르지 않음(대역 공허)")
    except AssertionError as e:
        fails.append("윈 꼴 cmd_check RED: %s" % e)

    if fails:
        print("FAIL: " + " | ".join(fails))
        return 1
    print("PASS: 윈 꼴 C53 — daemon boot-fleet %d회 관찰 · 관찰 계약 유지 · daemon 다른 서브동사 9꼴 거부" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
