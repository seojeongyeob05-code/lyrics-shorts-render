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
        self.assertEqual(set(img.getdata()), {self.style.bg_color})

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
        self.assertEqual(set(img.getdata()), {(200, 30, 30)})


if __name__ == "__main__":
    unittest.main()
