import unittest

from PIL import Image

from shorts import lrc
from shorts.frame import FrameRenderer, Style, cover_fit, make_background

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


class KaraokeTest(unittest.TestCase):
    def setUp(self):
        self.style = Style(width=400, height=300, font_size=32, next_font_size=18, fade=0,
                           bg_color=(0, 0, 0), text_color=(255, 255, 255),
                           unsung_color=(0, 0, 255), next_color=(255, 200, 0))
        self.r = FrameRenderer(self.style)
        self.ly = lrc.parse("[00:01.00]<00:01.00>AAAA <00:02.00>BBBB<00:03.00>", duration=5)

    def _cols(self, img, color):
        """color에 가까운 픽셀이 있는 x 집합."""
        px = img.load()
        return {x for x in range(img.width) for y in range(img.height)
                if all(abs(a - b) <= 40 for a, b in zip(px[x, y], color))}

    def test_fills_left_to_right(self):
        start = self.r.render(self.ly, 1.0)
        half = self.r.render(self.ly, 2.0)
        end = self.r.render(self.ly, 3.5)
        self.assertFalse(self._cols(start, (255, 255, 255)))
        sung, unsung = self._cols(half, (255, 255, 255)), self._cols(half, (0, 0, 255))
        self.assertTrue(sung and unsung)
        self.assertLess(max(sung), min(unsung))  # 왼쪽은 부른 색, 오른쪽은 안 부른 색
        self.assertFalse(self._cols(end, (0, 0, 255)))

    def test_wrapped_rows_fill_in_order(self):
        style = Style(**{**self.style.__dict__, "width": 160})
        r = FrameRenderer(style)
        img = r.render(self.ly, 1.9)  # 첫 단어(첫 글줄)는 거의 다, 둘째 글줄은 아직
        px = img.load()
        rows_sung = {y for y in range(img.height) for x in range(img.width) if px[x, y] == (255, 255, 255)}
        rows_unsung = {y for y in range(img.height) for x in range(img.width) if px[x, y] == (0, 0, 255)}
        self.assertTrue(rows_sung and rows_unsung)
        self.assertLess(min(rows_sung), max(rows_unsung))
        self.assertGreater(max(rows_unsung), max(rows_sung))

    def test_plain_lines_unchanged(self):
        plain = lrc.parse("[00:01.00]AAAA BBBB", duration=5)
        img = self.r.render(plain, 1.5)
        self.assertTrue(self._cols(img, (255, 255, 255)))
        self.assertFalse(self._cols(img, (0, 0, 255)))


class BackgroundTest(unittest.TestCase):
    SMALL = dict(width=60, height=100)

    def test_gradient_runs_top_to_bottom(self):
        bg = make_background(Style(**self.SMALL, bg_color=(0, 0, 0), bg_gradient=(200, 100, 0)))
        self.assertEqual(bg.getpixel((30, 0)), (0, 0, 0))
        self.assertEqual(bg.getpixel((30, 99)), (200, 100, 0))
        mid = bg.getpixel((30, 50))
        self.assertTrue(90 < mid[0] < 110 and 45 < mid[1] < 55)
        self.assertEqual(bg.getpixel((0, 50)), bg.getpixel((59, 50)))  # 가로로는 같은 색

    def test_dim_darkens(self):
        bg = make_background(Style(**self.SMALL, bg_color=(200, 200, 200), bg_dim=0.5))
        self.assertEqual(bg.getpixel((0, 0)), (100, 100, 100))

    def test_blur_softens_image_edges(self):
        img = Image.new("RGB", (60, 100), (0, 0, 0))
        img.paste((255, 255, 255), (30, 0, 60, 100))
        sharp = make_background(Style(**self.SMALL), img)
        soft = make_background(Style(**self.SMALL, bg_blur=6), img)
        self.assertEqual(sharp.getpixel((28, 50)), (0, 0, 0))
        self.assertTrue(0 < soft.getpixel((28, 50))[0] < 255)

    def test_stroke_draws_outline_color(self):
        ly = lrc.parse("[00:00.00]HELLO", duration=2)
        base = dict(width=200, height=120, font_size=40, fade=0, bg_color=(0, 0, 255),
                    text_color=(255, 255, 255), stroke_color=(255, 0, 0))
        plain = FrameRenderer(Style(**base)).render(ly, 1)
        outlined = FrameRenderer(Style(**base, stroke_width=3)).render(ly, 1)
        self.assertNotIn((255, 0, 0), _colors(plain))
        self.assertIn((255, 0, 0), _colors(outlined))


class ZoomTest(unittest.TestCase):
    def setUp(self):
        # 왼쪽 3칸만 빨강, 나머지 파랑인 배경
        self.img = Image.new("RGB", (100, 200), (0, 0, 255))
        self.img.paste((255, 0, 0), (0, 0, 3, 200))
        self.base = dict(width=100, height=200, bg_zoom=0.2, bg_zoom_period=10, fade=0)

    def test_no_zoom_keeps_one_background(self):
        r = FrameRenderer(Style(width=100, height=200), self.img)
        self.assertIs(r.background_at(0), r.background_at(5))
        self.assertEqual(r.background_at(0).size, (100, 200))

    def test_zooms_in_and_back(self):
        r = FrameRenderer(Style(**self.base), self.img)
        self.assertEqual(r._bg.size, (120, 240))  # 확대해도 선명하게 크게 만들어 둠
        start, peak, back = r.background_at(0), r.background_at(5), r.background_at(10)
        self.assertEqual(start.size, (100, 200))
        self.assertGreater(start.getpixel((0, 100))[0], 200)  # 처음엔 그림 전체(빨간 띠 보임)
        self.assertLess(peak.getpixel((0, 100))[0], 30)  # 최대 확대에선 가장자리가 잘림
        self.assertEqual(start.tobytes(), back.tobytes())  # 한 주기 뒤 제자리

    def test_pan_moves_toward_side(self):
        r = FrameRenderer(Style(**self.base, bg_pan=-1), self.img)
        self.assertGreater(r.background_at(5).getpixel((0, 100))[0], 200)  # 왼쪽으로 흘러 띠가 보임

    def test_updates_are_throttled(self):
        r = FrameRenderer(Style(**self.base), self.img)
        self.assertIs(r.background_at(1.0), r.background_at(1.0 + 1 / 60))
        self.assertIsNot(r.background_at(1.0), r.background_at(1.2))

    def test_lyrics_drawn_over_moving_background(self):
        ly = lrc.parse("[00:00.00]HELLO", duration=10)
        style = Style(**self.base, font_size=20, text_color=(0, 255, 0))
        r = FrameRenderer(style, self.img)
        a, b = r.render(ly, 0), r.render(ly, 5)
        self.assertIn((0, 255, 0), _colors(a))
        self.assertNotEqual(a.tobytes(), b.tobytes())


class RenderBytesTest(unittest.TestCase):
    """render_bytes()는 render().tobytes()와 바이트 단위로 같아야 한다."""

    LRC = ("[00:00.50]plain line\n"
           "[00:02.00]<00:02.00>sing <00:02.60>along<00:03.20>\n"
           "[00:04.00]last")

    def check(self, style, times, progress=True):
        ly = lrc.parse(self.LRC, duration=6)
        fast, slow = FrameRenderer(style), FrameRenderer(style)
        for t in times:
            p = t / 6 if progress else None
            with self.subTest(t=t):
                self.assertEqual(fast.render_bytes(ly, t, p), slow.render(ly, t, p).tobytes())

    def test_matches_render_everywhere(self):
        style = Style(width=90, height=160, font_size=14, next_font_size=10, fade=0.2,
                      progress_height=4, progress_bottom=10)
        times = [k / 20 for k in range(0, 120)]  # 페이드·노래방·정지 구간을 모두 지난다
        self.check(style, times)
        self.check(style, times, progress=False)

    def test_matches_render_with_zoom(self):
        style = Style(width=90, height=160, font_size=14, next_font_size=10, bg_zoom=0.1,
                      bg_zoom_period=3, progress_height=4, progress_bottom=10)
        self.check(style, [k / 10 for k in range(0, 60)])

    def test_without_progress_bar_or_fade(self):
        style = Style(width=90, height=160, font_size=14, next_font_size=10, fade=0,
                      progress_bar=False)
        self.check(style, [0.1, 1.0, 2.3, 3.5, 4.5])

    def test_static_screen_bytes_are_reused(self):
        ly = lrc.parse(self.LRC, duration=6)
        r = FrameRenderer(Style(width=90, height=160, font_size=14, next_font_size=10))
        a = r.render_bytes(ly, 1.0)
        self.assertIs(r.render_bytes(ly, 1.5), a)  # 진행 바 없으면 같은 객체 그대로


if __name__ == "__main__":
    unittest.main()
