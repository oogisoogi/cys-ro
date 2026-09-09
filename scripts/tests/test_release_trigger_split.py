"""방아쇠 분리 계약의 밀폐 unittest — 「태그는 꼬리표, 발행은 버튼」 (2026-09-09 신설).

★무엇을 지키는가 (TICKET=cys-release-first-publish · 박사님 09:05 승인)
  발행은 이 저장소에서 유일하게 **비가역**인 동작이다. 그 동작에 이르는 길이 하나뿐이고,
  그 길에 승인 게이트가 서 있어야 한다. 이 파일은 그 배선을 **문자열·구조 층위에서** 못박는다.
    ① `release.yml`(태그 push) 은 **발행하지 않는다** — draft 까지만.
    ② 발행은 `release-publish.yml` 의 workflow_dispatch 하나뿐이고,
    ③ 그 입력 `dry_run` 의 **기본값은 true** 다(손이 미끄러져도 발행되지 않는다).
    ④ 승격 step 은 `dry_run == false` 인 잡에만 있고, 그 잡에는 environment 승인이 걸린다.

★왜 소스 계약 검사인가
  이 배선은 워크플로 파일에만 존재한다 — 돌려 보려면 태그를 자르고 발행해야 하는데, 그건
  정확히 우리가 사고 없이 하고 싶은 그 일이다. 그래서 실행 대신 **원문을 읽어** 못박는다
  (test_release_postprocess_gate.py 의 `MainWiringContractTests` 관례와 동형).

★뮤턴트 계약 — 아래를 저지르면 이 파일이 빨개진다:
  · release.yml 에 `--draft=false` 나 `--latest` 를 넣는다(= 태그 push 로 공개 발행) → test_01·02
  · `releaseDraft: true` 를 false 로 뒤집는다                                      → test_00
  · dry_run 기본값을 false 로 바꾼다                                                → test_11
  · publish 잡의 `dry_run == false` 가드를 지운다                                   → test_12
  · publish 잡의 environment 승인을 뗀다                                            → test_13
  · 검증 전용 잡에 승격 명령을 심는다                                               → test_14
  (「REQUIRED_ASSETS 에서 .sig 제거」 뮤턴트는 이 파일이 아니라
   test_release_verify.py 의 test_26/test_26b 가 잡는다 — 그쪽이 실물 판정 지점이다.)

사용: python3 scripts/tests/test_release_trigger_split.py
"""

import io
import os
import unittest

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_WF = os.path.join(_HERE, "..", "..", ".github", "workflows")
_RELEASE = os.path.join(_WF, "release.yml")
_PUBLISH = os.path.join(_WF, "release-publish.yml")


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _code(path):
    """주석 줄을 걷어낸 원문 — 「무엇이 실행되는가」만 남긴다.

    ★왜 필요한가: `release.yml` 은 자기 이력을 주석으로 적어 둔다. 그중 한 줄이
      「종전 '--latest --draft=false' 강제 공개를 **제거**」다. 주석까지 세면 그 기록을 지워야
      테스트가 초록이 되는데, 그건 정확히 반대 방향의 압력이다 — 왜 지금 모양인지를 적어 둔
      문장을 테스트가 밀어내면 안 된다. 그래서 검사 대상에서 주석을 뺀다.
    """
    return "\n".join(ln for ln in _read(path).splitlines()
                      if not ln.lstrip().startswith("#"))


def _load(path):
    return yaml.safe_load(_read(path))


class TagLaneNeverPublishes(unittest.TestCase):
    """① 태그 push 레인은 자산을 만들 뿐, 공개하지 않는다."""

    def setUp(self):
        self.src = _code(_RELEASE)          # 주석 제외 — 이력 기록이 검사에 걸리지 않게

    def test_00_release_draft_is_true(self):
        self.assertIn("releaseDraft: true", self.src,
                      "태그 레인이 draft 로 만들지 않는다 — 태그 push 가 곧 공개 발행이 된다")
        self.assertNotIn("releaseDraft: false", self.src)

    def test_01_no_draft_false_promotion_in_tag_lane(self):
        """`--draft=false` 는 승격 명령이다. 태그 레인에 있으면 방아쇠가 붙어 있는 것이다."""
        self.assertNotIn("--draft=false", self.src,
                         "release.yml 에 승격 명령이 있다 — 태그 push 가 공개 발행을 일으킨다")

    def test_02_no_latest_marking_in_tag_lane(self):
        """`--latest` 는 업데이터가 보는 자리를 옮긴다 — 승인 없이 일어나면 안 된다."""
        self.assertNotIn("--latest", self.src,
                         "release.yml 이 latest 마킹을 한다 — 승인 밖에서 배포 표면이 바뀐다")

    def test_03_tag_trigger_still_exists(self):
        """분리는 '태그가 빌드를 돌리는 것'까지 없애는 게 아니다(과교정 방지)."""
        on = _load(_RELEASE)[True]
        self.assertIn("push", on, "태그 트리거가 통째로 사라졌다 — 자산이 만들어지지 않는다")
        self.assertEqual(on["push"]["tags"], ["v*"])


class PublishLaneIsTheOnlyTrigger(unittest.TestCase):
    """②③④ 발행 레인 — 입구 하나 · 기본 dry-run · 승인 게이트."""

    def setUp(self):
        self.src = _read(_PUBLISH)
        self.doc = _load(_PUBLISH)
        self.jobs = self.doc["jobs"]
        self.inputs = self.doc[True]["workflow_dispatch"]["inputs"]

    def test_10_dispatch_only(self):
        """발행 레인은 사람이 누를 때만 돈다 — push·schedule 로 도는 순간 버튼이 아니다."""
        self.assertEqual(list(self.doc[True]), ["workflow_dispatch"])

    def test_11_dry_run_defaults_to_true(self):
        """★기본값이 요점이다. 입력을 비운 채 실행해도 발행되지 않아야 한다."""
        dry = self.inputs["dry_run"]
        self.assertEqual(dry["type"], "boolean")
        self.assertIs(dry["default"], True,
                      "dry_run 기본값이 true 가 아니다 — 실수 한 번이 곧 발행이다")

    def test_12_publish_job_is_gated_on_dry_run_false(self):
        cond = self.jobs["publish"]["if"]
        self.assertIn("inputs.dry_run == false", cond,
                      "publish 잡에 dry_run 가드가 없다: %r" % cond)
        self.assertIn("inputs.confirm == 'PUBLISH'", cond)

    def test_13_publish_job_keeps_owner_approval(self):
        self.assertEqual(self.jobs["publish"].get("environment"), "release-production",
                         "발행 잡에서 오너 승인 게이트가 사라졌다")

    def test_14_verify_job_publishes_nothing(self):
        """검증 잡은 승인 없이 도는 잡이다 — 거기 승격 명령이 있으면 게이트가 무의미해진다."""
        verify_steps = yaml.safe_dump(self.jobs["verify"], allow_unicode=True)
        for forbidden in ("--draft=false", "--latest", "gh release edit"):
            self.assertNotIn(forbidden, verify_steps,
                             "검증 전용 잡에 %r 가 있다 — 승인 밖에서 발행이 가능해진다" % forbidden)
        self.assertNotIn("environment", self.jobs["verify"],
                         "검증 잡에 승인 게이트가 붙었다 — dry-run 마다 사람을 깨운다")

    def test_15_promotion_lives_only_in_the_publish_job(self):
        publish_steps = yaml.safe_dump(self.jobs["publish"], allow_unicode=True)
        self.assertIn("gh release edit", publish_steps,
                      "발행 잡에 승격 명령이 없다 — 이 레인은 아무것도 발행하지 못한다")
        self.assertIn("--draft=false", publish_steps)
        # ★본체(앱) 발행 레인에서 승격 명령을 가진 워크플로는 이 하나뿐이어야 한다.
        #   ⚠`pack-release.yml` 은 **알려진 별도 레인**이다 — `pack-v*` 태그 push 가 팩 전용
        #     릴리스를 `--latest --draft=false` 로 곧장 공개한다(승인 게이트 없음).
        #     이번 티켓의 분리 대상은 본체 릴리스이므로 그 레인은 손대지 않았고, 대신 여기
        #     **이름으로 등재**해 둔다. 새 자동 발행 경로가 하나라도 늘면 이 테스트가 빨개진다.
        #     (팩 레인 자체의 승인 게이트 여부는 별건 — master 에 보고됨 2026-09-09.)
        KNOWN_OTHER_LANES = {"pack-release.yml"}
        owners = []
        for name in sorted(os.listdir(_WF)):
            if not name.endswith((".yml", ".yaml")):
                continue
            if "--draft=false" in _code(os.path.join(_WF, name)):
                owners.append(name)
        self.assertEqual(sorted(set(owners) - KNOWN_OTHER_LANES), ["release-publish.yml"],
                         "본체 발행 레인 밖에 승격 명령이 생겼다: %s" % owners)
        self.assertEqual(sorted(set(owners) & KNOWN_OTHER_LANES), ["pack-release.yml"],
                         "등재된 별도 레인이 사라졌거나 이름이 바뀌었다 — 등재를 갱신하라: %s" % owners)

    def test_16_publish_needs_verify(self):
        """발행 잡은 검증 잡 뒤에 선다 — 승인 창을 열기 전에 기계가 먼저 본다."""
        self.assertIn("verify", self.jobs["publish"].get("needs", []))

    def test_17_publish_reverifies_on_its_own(self):
        """★TOCTOU 계약 — 발행 잡은 verify 의 결과를 믿지 않고 자기 손으로 다시 받아 검증한다.

        승인 대기 동안 draft 가 바뀔 수 있다. 그래서 다운로드·검증·승격이 **한 잡 안에서
        연속**이어야 한다(이 워크플로 머리말의 `environment:` 절 참조).
        """
        publish_steps = yaml.safe_dump(self.jobs["publish"], allow_unicode=True)
        self.assertIn("gh release download", publish_steps,
                      "발행 잡이 자산을 다시 받지 않는다 — 승인 대기 중 바뀐 draft 를 발행한다")
        self.assertIn("release-verify.py", publish_steps,
                      "발행 잡이 자기 손으로 검증하지 않는다")


if __name__ == "__main__":
    unittest.main(verbosity=2)
