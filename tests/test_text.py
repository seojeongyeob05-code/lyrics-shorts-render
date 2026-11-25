import os
import unittest
from unittest import mock

from PIL import ImageFont

from shorts import text


class WrapTest(unittest.TestCase):
    def setUp(self):
        self.font = ImageFont.load_default(20)

    def test_short_text_stays_one_line(self):
        self.assertEqual(text.wrap("hello world", self.font, 1000), ["hello world"])

    def test_wraps_on_spaces_within_width(self):
        rows = text.wrap("one two three four five six seven", self.font, 120)
        self.assertGreater(len(rows), 1)
        self.assertEqual(" ".join(rows), "one two three four five six seven")
        for r in rows:
            self.assertLessEqual(self.font.getlength(r), 120)

    def test_long_word_is_split_by_characters(self):
        word = "abcdefghijklmnopqrstuvwxyz"
        rows = text.wrap(word, self.font, 60)
        self.assertEqual("".join(rows), word)
        for r in rows:
            self.assertLessEqual(self.font.getlength(r), 60)

    def test_collapses_extra_spaces_and_empty(self):
        self.assertEqual(text.wrap("  a   b  ", self.font, 1000), ["a b"])
        self.assertEqual(text.wrap("", self.font, 1000), [])


class BalancedWrapTest(unittest.TestCase):
    def setUp(self):
        path = text.find_korean_font()
        if path is None:
            self.skipTest("이 환경에 CJK 폰트 없음")
        self.font = ImageFont.truetype(path, 40)

    def test_latin_rows_are_evened_out(self):
        font = ImageFont.load_default(20)
        words = "aaaa bbbb cccc dddd eeee f"
        greedy = text.wrap(words, font, font.getlength("aaaa bbbb cccc dddd eeee"), balance=False)
        even = text.wrap(words, font, font.getlength("aaaa bbbb cccc dddd eeee"))
        self.assertEqual(greedy[-1], "f")  # 욕심껏 채우면 끝줄에 한 글자
        self.assertEqual(len(even), len(greedy))
        self.assertGreater(len(even[-1]), 1)

    def test_japanese_breaks_at_script_change_not_mid_word(self):
        w = self.font.getlength("失っちゃいけないモノはな") * 0.95
        self.assertEqual(text.wrap("失っちゃいけないモノはなに?", self.font, w),
                         ["失っちゃいけない", "モノはなに?"])

    def test_japanese_prefers_space_and_never_starts_with_small_kana(self):
        w = self.font.getlength("でも 答えなんて出ないま")
        rows = text.wrap("でも 答えなんて出ないままさ", self.font, w)
        self.assertEqual(rows, ["でも 答えなんて", "出ないままさ"])
        for t in ["ちょっとまってちょっとまってちょっと", "いっしょにいたいっていったっけ"]:
            for row in text.wrap(t, self.font, self.font.getlength(t) * 0.6)[1:]:
                self.assertNotIn(row[0], "っゃゅょー")

    def test_closing_bracket_break(self):
        t = "「もうこれ以上はない」と言いながら"
        rows = text.wrap(t, self.font, self.font.getlength(t) * 0.7)
        self.assertEqual(rows[0], "「もうこれ以上はない」")


class FindFontTest(unittest.TestCase):
    def test_env_var_wins(self):
        with mock.patch.dict(os.environ, {text.FONT_ENV: __file__}):
            self.assertEqual(text.find_korean_font(), __file__)

    def test_env_var_missing_file_raises(self):
        with mock.patch.dict(os.environ, {text.FONT_ENV: "/nope/font.ttf"}):
            with self.assertRaises(FileNotFoundError):
                text.find_korean_font()

    def test_prefers_known_fonts_and_bold(self):
        files = ["/f/unifont.otf", "/f/wqy-zenhei.ttc", "/f/NanumGothic.ttf", "/f/NanumGothicBold.ttf"]
        self.assertEqual(min(files, key=text._rank), "/f/NanumGothicBold.ttf")
        self.assertEqual(min(files[:2], key=text._rank), "/f/wqy-zenhei.ttc")

    def test_found_font_renders_hangul(self):
        path = text.find_korean_font()
        if path is None:
            self.skipTest("이 환경에 한글 폰트 없음")
        font = ImageFont.truetype(path, 40)
        # 글리프가 없으면 '가'와 '나'가 똑같은 빈 상자(tofu)로 그려진다
        self.assertNotEqual(bytes(font.getmask("가")), bytes(font.getmask("나")))


if __name__ == "__main__":
    unittest.main()
