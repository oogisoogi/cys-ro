"""C84 산출물 스킬 + 사용자 로컬 스킬 프로필 배선 · 설명 예산 · 발동 문구 겹침 (TICKET=asset-skills-for-seats).

격리: HOME·CLAUDE_CONFIG_DIR·CYS_PACK_DIR·CYS_LOCAL_DIR 전부 임시 폴더. 실제 프로필·팩 무접촉.
"""
import importlib.util
import inspect
import os
import re
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_PACK = os.path.normpath(os.path.join(HERE, "..", ".."))
spec = importlib.util.spec_from_file_location("javis_preflight", os.path.join(HERE, "..", "javis_preflight.py"))
pf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pf)

ENV_KEYS = ("HOME", "CLAUDE_CONFIG_DIR", "CYS_ACCOUNT_DIR", "CYS_PACK_DIR", "JAVIS_PACK_DIR",
            "AITERM_PACK_DIR", "CYS_LOCAL_DIR", "JAVIS_LOCAL_DIR", "AITERM_LOCAL_DIR")

# ── 설명 예산 상한(문자 · 1,536자 잘림 적용 · 좌석 네이티브 목록에 거는 우리 스킬 중 목록에 실리는 것) ──
# 실측(2026-11-06 · Claude Code 2.1.318 · opus-5-5 · claude -p --debug-file): 「Skill listing over budget:
# 84 skills, 30348 chars > 30000 budget」 — 좌석 전체 예산 = 30,000자이고 claude.ai 동기·플러그인 스킬과 나눠 쓴다.
# Claude Code 는 스킬 설명 합계를 컨텍스트의 1%(skillListingBudgetFraction 0.01)로 자르고, 넘치면 덜 부른
# 스킬부터 설명을 지운다(code.claude.com/docs/en/skills). 이 상한은 「우리가 거는 몫」의 천장이다 — 넘으면
# 새 스킬을 넣기 전에 설명을 줄이거나 목록에서 빼야 한다(팩 전부 링크 금지 · master caafbb4a).
LINKED_DESC_CAP = 16000
NEW_ASSET_DESC_MAX = 150   # 「무엇+언제」 2문장(1.1.12 skill-fold 와 같은 문체)
NEW_ASSET_SKILLS = ["motion-graphics-prompt", "video-report-deck", "ppt-design-system",
                    "ppt-styles", "portrait-cutout"]
OVERLAP_MAX = 0.5   # 두 설명의 낱말 겹침(Jaccard) 상한 — 같은 일을 두 스킬이 주장하면 실패


def _desc(skill_md):
    t = open(skill_md, encoding="utf-8").read()
    m = re.match(r"---\r?\n(.*?)\r?\n---", t, re.S)
    if not m:
        return ""
    d = re.search(r"^description:\s*(.*?)(?=^[\w-]+:|\Z)", m.group(1), re.S | re.M)
    if not d:
        return ""
    v = d.group(1).strip()
    if v[:1] in "|>":
        v = v[1:].strip()
    return v.strip("\"'")


def _listed(skill_md):
    """목록에 실리는가 — `disable-model-invocation: true` 는 목록 밖(사용자 /호출 전용 · 공식 문서)."""
    t = open(skill_md, encoding="utf-8").read()
    m = re.match(r"---\r?\n(.*?)\r?\n---", t, re.S)
    return not (m and re.search(r"^disable-model-invocation:\s*true\s*$", m.group(1), re.M))


def _words(s):
    return {w for w in re.findall(r"[0-9A-Za-z가-힣][0-9A-Za-z가-힣.+-]*", s.lower()) if len(w) >= 2}


class C84WiringTest(unittest.TestCase):
    def setUp(self):
        self.saved = {k: os.environ.get(k) for k in ENV_KEYS}
        self.root = tempfile.mkdtemp(prefix="c84-")
        self.home = os.path.join(self.root, "home")
        self.pack = os.path.join(self.home, ".cys", "pack")
        self.prof = os.path.join(self.home, ".cys", "claude")
        self.local = os.path.join(self.home, ".cys", "local")
        for s in pf.OUTPUT_SKILLS:
            self._mk(os.path.join(self.pack, "skills", s))
        self._mk(os.path.join(self.pack, "skills", "hwp-shadow"))
        self._mk(os.path.join(self.local, "skills", "my-own"))
        self._mk(os.path.join(self.local, "skills", "hwp-shadow"))       # 팩 동명
        os.makedirs(os.path.join(self.local, "skills", "no-skill-md"))  # SKILL.md 없음 = 스킬 아님
        os.makedirs(self.prof)
        open(os.path.join(self.prof, "settings.json"), "w").write("{}\n")
        for k in ENV_KEYS:
            os.environ.pop(k, None)
        os.environ.update({"HOME": self.home, "CLAUDE_CONFIG_DIR": self.prof,
                           "CYS_ACCOUNT_DIR": self.prof, "CYS_PACK_DIR": self.pack})
        # 임시 폴더 팩은 발견 규약의 격리 가드(temp-pack 누수 차단)가 등록 대상을 0 으로 만든다 —
        # 발견 규약 자체는 C26/C27/C29 시험의 몫이므로 여기서는 대상 프로필을 고정한다.
        self._disc = pf.discover_skill_profiles
        pf.discover_skill_profiles = lambda: [self.prof]

    def tearDown(self):
        pf.discover_skill_profiles = self._disc
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.root, ignore_errors=True)

    @staticmethod
    def _mk(d):
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: %s\ndescription: x\n---\n" % os.path.basename(d))

    def _run(self, fix=True):
        p = pf.Preflight(fix=fix, skips=[], mode="fix" if fix else "check")
        p.c84_output_skills()
        return p.results[-1]

    def _target(self, name):
        p = os.path.join(self.prof, "skills", name)
        return os.path.realpath(p) if os.path.islink(p) else None

    def test_links_output_and_local_then_idempotent(self):
        r = self._run()
        self.assertEqual(r["status"], pf.FIXED, r)
        for s in pf.OUTPUT_SKILLS:
            self.assertEqual(self._target(s), os.path.realpath(os.path.join(self.pack, "skills", s)))
        self.assertEqual(self._target("my-own"), os.path.realpath(os.path.join(self.local, "skills", "my-own")))
        self.assertIsNone(self._target("hwp-shadow"), "팩 동명 로컬은 링크하지 않는다(팩 우선)")
        self.assertIsNone(self._target("no-skill-md"))
        self.assertIn("팩 동명 로컬 1건", r["detail"])
        self.assertEqual(self._run()["status"], pf.PASS, "두 번째는 할 일 없음")

    def test_check_mode_reports_without_writing(self):
        r = self._run(fix=False)
        self.assertEqual(r["status"], pf.WARN)
        self.assertFalse(os.path.exists(os.path.join(self.prof, "skills")))

    def test_removed_local_skill_link_is_pruned_and_realdir_untouched(self):
        self._run()
        real = os.path.join(self.prof, "skills", "user-real-dir")
        os.makedirs(real)
        other = os.path.join(self.prof, "skills", "elsewhere")
        os.symlink(os.path.join(self.root, "nowhere"), other)   # 우리 대상이 아닌 끊긴 링크
        shutil.rmtree(os.path.join(self.local, "skills", "my-own"))
        r = self._run()
        self.assertEqual(r["status"], pf.FIXED, r)
        self.assertFalse(os.path.lexists(os.path.join(self.prof, "skills", "my-own")), "끊긴 로컬 링크 정리")
        self.assertTrue(os.path.isdir(real), "실디렉토리 불가침")
        self.assertTrue(os.path.islink(other), "다른 대상 링크 불가침")

    def test_user_realdir_with_output_name_is_not_overwritten(self):
        real = os.path.join(self.prof, "skills", "ppt-styles")
        os.makedirs(real)
        self._run()
        self.assertFalse(os.path.islink(real))

    def test_same_name_user_link_is_kept_and_idempotent(self):
        """codex 1R major: want 에 든 이름이라도 남의 대상 링크는 갈아 끼우지 않는다."""
        sk = os.path.join(self.prof, "skills")
        os.makedirs(sk)
        mine = os.path.join(self.root, "user-own-ppt")
        os.makedirs(mine)
        os.symlink(mine, os.path.join(sk, "ppt-styles"))
        r = self._run()
        self.assertEqual(os.path.realpath(os.path.join(sk, "ppt-styles")), os.path.realpath(mine))
        self.assertIn("사용자 링크 1건 보존", r["detail"])
        self.assertEqual(self._run()["status"], pf.PASS, "보존한 링크 때문에 매번 FIXED 가 나면 안 된다")

    def test_relative_and_escaping_links(self):
        """codex 1R minor: 상대 링크도 우리 오버레이면 정리 · `..` 로 밖을 가리키면 우리 것 아님."""
        self._run()
        sk = os.path.join(self.prof, "skills")
        local_skills = os.path.join(self.local, "skills")
        rel_ours = os.path.relpath(os.path.join(local_skills, "gone-skill"), sk)
        os.symlink(rel_ours, os.path.join(sk, "gone-skill"))                 # 끊긴 상대 링크(우리 것)
        esc = os.path.join(local_skills, "..", "..", "..", "elsewhere-skill")  # 오버레이 밖으로 탈출
        os.symlink(esc, os.path.join(sk, "escaped"))
        self._run()
        self.assertFalse(os.path.lexists(os.path.join(sk, "gone-skill")), "끊긴 상대 로컬 링크 정리")
        self.assertTrue(os.path.islink(os.path.join(sk, "escaped")), "탈출 경로는 우리 링크가 아니다")
        self.assertFalse(pf._link_target_under(os.path.join(sk, "escaped"), local_skills))

    def test_local_dir_env_override(self):
        alt = os.path.join(self.root, "alt-local")
        self._mk(os.path.join(alt, "skills", "alt-skill"))
        os.environ["CYS_LOCAL_DIR"] = alt
        self._run()
        self.assertEqual(self._target("alt-skill"), os.path.realpath(os.path.join(alt, "skills", "alt-skill")))


class C84PlacementTest(unittest.TestCase):
    def test_in_wire_seat_and_before_c62(self):
        ws = inspect.getsource(pf.wire_seat)
        self.assertIn("pf.c84_output_skills", ws, "좌석 기동 직전 배선(--wire-seat)이 C84 를 타야 한다")
        run = inspect.getsource(pf.Preflight.run)
        self.assertIn("self.c84_output_skills,", run)
        self.assertLess(run.index("self.c84_output_skills,"), run.index("self.c62_pack_heal_ledger,"))


class OutputSkillBudgetTest(unittest.TestCase):
    """저장소 팩 실물 기준 — 목록 실재 · 새 스킬 설명 길이 · 거는 몫 합계 · 겹침."""

    def _md(self, s):
        return os.path.join(REPO_PACK, "skills", s, "SKILL.md")

    def linked_set(self):
        return pf.VIDEO_SKILLS + pf.APPBUILD_SKILLS + pf.HARNESS_SKILLS + pf.OUTPUT_SKILLS

    def test_output_skills_exist_in_repo_pack(self):
        missing = [s for s in pf.OUTPUT_SKILLS if not os.path.isfile(self._md(s))]
        self.assertEqual(missing, [])

    def test_no_duplicate_across_link_lists(self):
        allv = self.linked_set()
        self.assertEqual(len(allv), len(set(allv)), "같은 스킬이 두 목록에 있다")

    def test_new_asset_descriptions_short(self):
        for s in NEW_ASSET_SKILLS:
            d = _desc(self._md(s))
            self.assertTrue(d, "%s description 없음" % s)
            self.assertLessEqual(len(d), NEW_ASSET_DESC_MAX, "%s description %d자" % (s, len(d)))

    def test_linked_description_budget(self):
        total = sum(min(len(_desc(self._md(s))), 1536) for s in self.linked_set()
                    if os.path.isfile(self._md(s)) and _listed(self._md(s)))
        self.assertLessEqual(total, LINKED_DESC_CAP,
                             "좌석에 거는 우리 스킬 설명 합계 %d자 > 상한 %d" % (total, LINKED_DESC_CAP))

    def test_description_overlap(self):
        names = [s for s in self.linked_set() if os.path.isfile(self._md(s)) and _listed(self._md(s))]
        words = {s: _words(_desc(self._md(s))) for s in names}
        bad = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if not words[a] or not words[b]:
                    continue
                j = len(words[a] & words[b]) / len(words[a] | words[b])
                if j > OVERLAP_MAX:
                    bad.append("%s ↔ %s %.2f" % (a, b, j))
        self.assertEqual(bad, [], "발동 문구가 겹치는 스킬 쌍")


if __name__ == "__main__":
    unittest.main()
