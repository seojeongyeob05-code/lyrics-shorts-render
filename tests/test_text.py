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
