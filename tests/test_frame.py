import unittest

from PIL import Image

from shorts import lrc
from shorts.frame import FrameRenderer, Style, cover_fit

LYRICS = lrc.parse("[00:01.00]first line\n[00:03.00]second line\n[00:06.00]third", duration=8)


def _rows_with(img, color, tol=10):
    """color에 가까운 픽셀이 있는 행(y) 집합."""
    px = img.load()
    rows = set()
    for y in range(img.height):
        for x in range(0, img.width, 2):
            if all(abs(a - b) <= tol for a, b in zip(px[x, y], color)):
                rows.add(y)
                break
    return rows


def _ink(img):
    """배경(검정)이 아닌 픽셀 좌표 집합."""
    px = img.load()
    return {(x, y) for y in range(img.height) for x in range(img.width) if px[x, y] != (0, 0, 0)}


def _colors(img):
    return {c for _, c in img.getcolors(img.width * img.height)}


class CoverFitTest(unittest.TestCase):
    def test_wide_image_fills_and_crops_center(self):
        src = Image.new("RGB", (400, 100), (255, 0, 0))
        src.paste((0, 0, 255), (175, 0, 225, 100))  # 가운데 파란 띠
        out = cover_fit(src, (90, 160))
        self.assertEqual(out.size, (90, 160))
        self.assertEqual(out.getpixel((45, 80)), (0, 0, 255))

    def test_small_image_is_upscaled(self):
        out = cover_fit(Image.new("RGB", (10, 10), (1, 2, 3)), (108, 192))
        self.assertEqual(out.size, (108, 192))
        self.assertEqual(out.getpixel((0, 0)), (1, 2, 3))


class RenderTest(unittest.TestCase):
    def setUp(self):
        # 테스트를 빠르게 하려고 작은 캔버스
        # 안티앨리어싱 가장자리가 다른 줄 색으로 오인되지 않게 색을 뚜렷이 구분
        self.style = Style(width=270, height=480, font_size=24, next_font_size=18, line_gap=12,
                           bg_color=(0, 0, 0), text_color=(255, 255, 255), next_color=(255, 200, 0))
        self.r = FrameRenderer(self.style)

    def test_size_and_background_when_no_text(self):
        img = self.r.render(lyrics=lrc.Lyrics([]), t=0)
        self.assertEqual(img.size, (270, 480))
        self.assertEqual(_colors(img), {self.style.bg_color})

    def test_current_line_is_above_next_line(self):
        img = self.r.render(LYRICS, 1.5)
        cur = _rows_with(img, self.style.text_color)
        nxt = _rows_with(img, self.style.next_color)
        self.assertTrue(cur and nxt)
        self.assertLess(max(cur), min(nxt))
        self.assertAlmostEqual((min(cur) + max(cur)) / 2, 240, delta=6)  # 세로 가운데

    def test_gap_before_first_line_shows_upcoming_line_only(self):
        img = self.r.render(LYRICS, 0.2)
        self.assertFalse(_rows_with(img, self.style.text_color))
        self.assertTrue(_rows_with(img, self.style.next_color))

    def test_last_line_has_no_next(self):
        img = self.r.render(LYRICS, 7)
        self.assertTrue(_rows_with(img, self.style.text_color))
        self.assertFalse(_rows_with(img, self.style.next_color))

    def test_background_image_is_used_and_not_mutated(self):
        bg = Image.new("RGB", (100, 100), (200, 30, 30))
        r = FrameRenderer(self.style, background=bg)
        r.render(LYRICS, 1.5)
        img = r.render(lrc.Lyrics([]), 0)
        self.assertEqual(_colors(img), {(200, 30, 30)})


class EffectsTest(unittest.TestCase):
    def setUp(self):
        self.style = Style(width=270, height=480, font_size=24, next_font_size=18, line_gap=12,
                           bg_color=(0, 0, 0), text_color=(255, 255, 255),
                           next_color=(255, 200, 0), fade=0.4)

    def _brightest(self, img):
        return max(max(c) for _, c in img.getcolors(img.width * img.height))

    def test_fade_out_then_in_without_overlap(self):
        r = FrameRenderer(self.style)
        # 3.0초에 first → second. 페이드 0.4초: 0.1초 뒤엔 이전 화면이 흐려지는 중,
        # 0.2초엔 배경만, 0.3초엔 새 화면이 나타나는 중, 0.4초 뒤엔 완전히 새 화면.
        before = r.render(LYRICS, 2.9)
        out = r.render(LYRICS, 3.1)
        blank = r.render(LYRICS, 3.2)
        into = r.render(LYRICS, 3.3)
        done = r.render(LYRICS, 3.5)
        self.assertEqual(self._brightest(before), 255)
        self.assertLess(self._brightest(out), 255)
        self.assertEqual(_colors(blank), {self.style.bg_color})
        self.assertLess(self._brightest(into), 255)
        self.assertEqual(self._brightest(done), 255)
        # 사라지는 중엔 이전 화면, 나타나는 중엔 새 화면과 같은 자리에 글자가 있다
        self.assertLessEqual(_ink(out), _ink(before))
        self.assertLessEqual(_ink(into), _ink(done))
        self.assertNotEqual(_ink(before), _ink(done))

    def test_fade_off_matches_plain_frame(self):
        plain = FrameRenderer(Style(**{**self.style.__dict__, "fade": 0}))
        self.assertEqual(plain.render(LYRICS, 1.1).tobytes(),
                         FrameRenderer(self.style).render(LYRICS, 1.5).tobytes())

    def test_progress_bar(self):
        r = FrameRenderer(self.style)
        img = r.render(LYRICS, 0.2, progress=0.5)
        s = self.style
        y = s.height - s.progress_bottom - s.progress_height // 2
        w = round(s.width * s.progress_width)
        x0 = (s.width - w) // 2
        self.assertEqual(img.getpixel((x0 + 2, y)), s.progress_color)
        self.assertEqual(img.getpixel((x0 + w - 3, y)), s.progress_track)
        self.assertEqual(img.getpixel((x0 - 3, y)), s.bg_color)
        # 진행 바가 캐시된 화면에 남지 않아야 한다
        self.assertEqual(r.render(LYRICS, 0.2).getpixel((x0 + 2, y)), s.bg_color)

    def test_layers_are_cached(self):
        r = FrameRenderer(self.style)
        for k in range(80):
            r.render(LYRICS, k / 10)
        self.assertEqual(r.layers_drawn, 4)  # 시작 전, first, second, third


if __name__ == "__main__":
    unittest.main()
