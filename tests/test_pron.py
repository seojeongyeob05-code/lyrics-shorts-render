import contextlib
import importlib.util
import io
import os
import shutil
import tempfile
import unittest

from shorts import pron

try:
    import pykakasi  # noqa: F401
    HAVE_KAKASI = True
except ImportError:
    HAVE_KAKASI = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class KanaTest(unittest.TestCase):
    def test_basic_and_combos(self):
        cases = {
            "かべにもたれて": "카베니모타레테",
            "きょう": "쿄우",
            "しんじゅく": "신쥬쿠",
            "いっしょ": "잇쇼",  # っ → 받침 ㅅ
            "がっこう": "갓코우",
            "ちゃん": "챤",  # ん → 받침 ㄴ
            "ワールド": "와루도",  # 가타카나, 장음 생략
            "Abc": "Abc",  # 가나가 아니면 그대로
        }
        for kana, kor in cases.items():
            with self.subTest(kana=kana):
                self.assertEqual(pron.kana_to_hangul(kana), kor)

    def test_leading_n_and_double_small_tsu(self):
        self.assertEqual(pron.kana_to_hangul("ん"), "ㄴ")
        self.assertEqual(pron.kana_to_hangul("あっ"), "앗")


class CompareTest(unittest.TestCase):
    def test_typo_found(self):
        self.assertEqual(pron.compare("코타에난테데나이", "코타에난테다나이"), [("데", "다")])

    def test_spacing_punctuation_particles_ignored(self):
        self.assertEqual(pron.compare("쿄우하 하레", "쿄우와하레!"), [])
        self.assertEqual(pron.compare("갓코우헤", "갓코우에…"), [])

    def test_latin_skipped(self):
        self.assertEqual(pron.compare("코노World데", "코노와루도데"), [])

    def test_check_lines_reports_only_differing_lines(self):
        rep = pron.check_lines(["きょうは", "はれ"], ["쿄우와", "하래"], to_hangul=pron.kana_to_hangul)
        self.assertEqual([(n, d) for n, _, _, d in rep], [(2, [("레", "래")])])


@unittest.skipUnless(HAVE_KAKASI, "pykakasi 없음")
class KanjiTest(unittest.TestCase):
    def test_kanji_and_particles(self):
        self.assertEqual(pron.japanese_to_hangul("学校へ行く"), "갓코우에이쿠")
        self.assertEqual(pron.japanese_to_hangul("本を読む"), "혼오요무")

    def test_tool_check_and_generate(self):
        spec = importlib.util.spec_from_file_location("pron_tool", os.path.join(ROOT, "tools", "pron.py"))
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        ja, ko = os.path.join(d, "ja.txt"), os.path.join(d, "ko.txt")
        with open(ja, "w") as f:
            f.write("本を読む\n\n学校へ行く\n")
        with open(ko, "w") as f:
            f.write("혼오요무\n갓코우에이코\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tool.main([ja, "--check", ko]), 0)
        self.assertIn("2번째 줄", out.getvalue())
        self.assertIn("'쿠' ↔ '코'", out.getvalue())
        self.assertIn("2줄 중 1줄 확인 필요", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            tool.main([ja])
        self.assertEqual(out.getvalue(), "혼오요무\n갓코우에이쿠\n")


if __name__ == "__main__":
    unittest.main()
