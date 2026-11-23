import unittest

import numpy as np

from PIL import Image

from shorts import lrc
from shorts.frame import FrameRenderer, Style, cover_fit, make_background, make_cover_layer

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


def _ink_points(img):
    """배경(검정)이 아닌 픽셀 (y, x) 목록."""
    px = img.load()
    return [(y, x) for y in range(img.height) for x in range(img.width) if px[x, y] != (0, 0, 0)]


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

    def test_progress_bar_stays_on_screen(self):
        # 화면보다 progress_bottom이 크면 맨 위에 붙는다(바이트 경로도 같은 자리)
        style = Style(width=60, height=100, progress_bottom=500, progress_height=4, fade=0)
        ly = lrc.parse("[00:00.00]a", duration=2)
        img = FrameRenderer(style).render(ly, 1, progress=1.0)
        self.assertEqual(img.getpixel((30, 1)), style.progress_color)
        self.assertEqual(FrameRenderer(style).render_bytes(ly, 1, 1.0), img.tobytes())

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

    def test_blurred_zoom_uses_half_size_source_without_visible_change(self):
        photo = Image.effect_noise((300, 500), 60).convert("RGB")
        base = dict(width=150, height=250, bg_zoom=0.1, bg_zoom_period=4)
        fast = FrameRenderer(Style(**base, bg_blur=10), photo)
        self.assertEqual(fast._zoom_k, 0.5)
        sharp = FrameRenderer(Style(**base, bg_blur=2), photo)
        self.assertEqual(sharp._zoom_k, 1.0)  # 선명한 배경은 원래 크기로
        exact = FrameRenderer(Style(**base, bg_blur=10), photo)
        exact._zoom_src = exact._bg  # 비교용: 절반 크기 지름길을 끈 것
        for t in (0.3, 1.7):
            a = np.asarray(fast.background_at(t), int)
            b = np.asarray(exact.background_at(t), int)
            self.assertLessEqual(np.abs(a - b).max(), 3)

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


class SongInfoTest(unittest.TestCase):
    BASE = dict(width=200, height=400, font_size=20, next_font_size=14, title_size=18,
                artist_size=14, fade=0.4, bg_color=(0, 0, 0), text_color=(255, 255, 255),
                next_color=(255, 200, 0), title_color=(0, 255, 0), artist_color=(0, 0, 255))
    LRC = "[ti:Song]\n[ar:Band]\n[00:01.00]one\n[00:03.00]two"

    def rows(self, img, color):
        return _rows_with(img, color, tol=60)

    def test_title_above_artist_near_top(self):
        img = FrameRenderer(Style(**self.BASE)).render(lrc.parse(self.LRC, duration=5), 2)
        title, artist = self.rows(img, (0, 255, 0)), self.rows(img, (0, 0, 255))
        self.assertTrue(title and artist)
        self.assertLess(max(title), min(artist))
        self.assertLess(max(artist), 400 * 0.3)

    def test_info_does_not_fade_with_lyrics(self):
        r = FrameRenderer(Style(**self.BASE))
        ly = lrc.parse(self.LRC, duration=5)
        steady, mid_fade = r.render(ly, 2), r.render(ly, 3.2)  # 3.2초 = 줄 바뀌는 페이드 한가운데
        box = (0, 0, 200, int(400 * 0.3))
        self.assertEqual(steady.crop(box).tobytes(), mid_fade.crop(box).tobytes())

    def test_hidden_when_missing_or_disabled(self):
        plain = lrc.parse("[00:01.00]one", duration=5)
        img = FrameRenderer(Style(**self.BASE)).render(plain, 2)
        self.assertFalse(self.rows(img, (0, 255, 0)))
        off = FrameRenderer(Style(**self.BASE, show_info=False)).render(lrc.parse(self.LRC, duration=5), 2)
        self.assertFalse(self.rows(off, (0, 255, 0)))

    def test_render_bytes_matches_with_info(self):
        ly = lrc.parse(self.LRC, duration=5)
        a, b = FrameRenderer(Style(**self.BASE)), FrameRenderer(Style(**self.BASE))
        for t in [0.5, 1.1, 2.0, 3.1, 4.0]:
            self.assertEqual(a.render_bytes(ly, t, t / 5), b.render(ly, t, t / 5).tobytes())


class CoverTest(unittest.TestCase):
    BASE = dict(width=200, height=400, cover_size=100, cover_y=0.3, cover_shadow=0,
                bg_color=(0, 0, 0), fade=0.4, font_size=20)

    def setUp(self):
        self.art = Image.new("RGB", (300, 200), (255, 0, 0))  # 가로로 긴 그림도 정사각형으로

    def test_square_is_centered_at_cover_y(self):
        layer = make_cover_layer(Style(**self.BASE, cover_shape="square"), self.art)
        self.assertEqual(layer.getbbox(), (50, 70, 150, 170))  # 가로 가운데, 세로 0.3*400=120 중심
        self.assertEqual(layer.getpixel((100, 120)), (255, 0, 0, 255))

    def test_shapes_cut_corners(self):
        corner = (52, 72)
        circle = make_cover_layer(Style(**self.BASE, cover_shape="circle"), self.art)
        rounded = make_cover_layer(Style(**self.BASE, cover_shape="rounded", cover_radius=0.2), self.art)
        self.assertEqual(circle.getpixel(corner)[3], 0)
        self.assertEqual(rounded.getpixel(corner)[3], 0)
        self.assertEqual(rounded.getpixel((100, 72))[3], 255)  # 위 변 가운데는 남는다
        edge = circle.getpixel((100 + round(50 * 0.7071), 120 + round(50 * 0.7071)))[3]
        self.assertTrue(0 < edge < 255)  # 원 가장자리는 부드럽게(안티앨리어싱)

    def test_shadow_below(self):
        layer = make_cover_layer(Style(**{**self.BASE, "cover_shadow": 0.8}, cover_shape="square"), self.art)
        r, g, b, a = layer.getpixel((100, 172))  # 그림 바로 아래
        self.assertGreater(a, 0)
        self.assertEqual((r, g, b), (0, 0, 0))

    def test_bad_shape(self):
        with self.assertRaises(ValueError):
            make_cover_layer(Style(**self.BASE, cover_shape="star"), self.art)

    def test_cover_stays_through_fade_and_with_info(self):
        ly = lrc.parse("[ti:T]\n[00:01.00]one\n[00:03.00]two", duration=5)
        style = Style(**self.BASE, cover_shape="square")
        r = FrameRenderer(style, cover=self.art)
        steady, fading = r.render(ly, 2), r.render(ly, 3.2)
        self.assertEqual(steady.getpixel((100, 120)), (255, 0, 0))
        self.assertEqual(fading.getpixel((100, 120)), (255, 0, 0))
        self.assertEqual(r.render_bytes(ly, 3.2, 0.5), FrameRenderer(style, cover=self.art).render(ly, 3.2, 0.5).tobytes())
        # 곡 정보가 없어도 앨범 아트는 나온다
        plain = lrc.parse("[00:01.00]one", duration=5)
        self.assertEqual(FrameRenderer(style, cover=self.art).render(plain, 2).getpixel((100, 120)), (255, 0, 0))


class ScaledStyleTest(unittest.TestCase):
    def test_halves_pixel_values_and_keeps_ratios(self):
        s = Style(stroke_width=3, bg_blur=22).scaled(0.5)
        self.assertEqual((s.width, s.height), (540, 960))
        self.assertEqual((s.font_size, s.next_font_size, s.line_gap), (36, 26, 24))
        self.assertEqual((s.stroke_width, s.progress_height, s.progress_bottom), (2, 4, 210))
        self.assertEqual(s.bg_blur, 11)
        self.assertEqual((s.center_y, s.max_text_width, s.fade), (0.5, 0.68, 0.24))

    def test_sizes_stay_even_and_zero_stays_zero(self):
        s = Style(width=1081, height=1919, stroke_width=0).scaled(0.5)
        self.assertEqual((s.width % 2, s.height % 2), (0, 0))
        self.assertEqual(s.stroke_width, 0)


class SlideTest(unittest.TestCase):
    BASE = dict(width=200, height=400, font_size=30, next_font_size=20, line_gap=20, fade=0.5,
                transition="slide", bg_color=(0, 0, 0), text_color=(255, 255, 255),
                next_color=(255, 255, 255), progress_bar=False)
    LRC = "[00:01.00]AAA\n[00:03.00]BBB\n[00:05.00]CCC"

    def test_layers_move_up_and_crossfade(self):
        r = FrameRenderer(Style(**self.BASE))
        d = 45
        steps = [r._transition("prev", "cur", a, d) for a in (0.0, 0.3, 0.7, 1.0)]
        prev_dy = [p[0][2] for p in steps]
        cur_dy = [p[1][2] for p in steps]
        self.assertEqual((prev_dy[0], cur_dy[0]), (0, d))  # 새 줄은 다음 줄 자리에서 시작
        self.assertEqual((prev_dy[-1], cur_dy[-1]), (-d, 0))  # 끝나면 제자리, 이전 줄은 한 줄 위
        self.assertTrue(all(a > b for a, b in zip(cur_dy, cur_dy[1:])))  # 계속 올라간다
        self.assertTrue(all(c - p == d for p, c in zip(prev_dy, cur_dy)))  # 항상 한 줄 간격
        self.assertEqual([(p[0][1], p[1][1]) for p in (steps[0], steps[-1])], [(1, 0), (0, 1)])
        self.assertEqual(steps[2][0][1], 0)  # 이전 화면은 절반쯤에서 이미 사라짐

    def test_slide_distance_follows_layout(self):
        # 두 줄로 감기는 긴 가사 다음에는 다음 줄 자리가 더 아래 → 더 멀리서 올라온다
        r = FrameRenderer(Style(**{**self.BASE, "max_text_width": 0.5}))
        ly = lrc.parse("[00:01.00]A\n[00:03.00]B\n[00:05.00]WWWWWWWWWW\n[00:07.00]C", duration=9)
        short = r._slide_distance(ly, r.state_key(ly, 2), r.state_key(ly, 3.5))
        long_ = r._slide_distance(ly, r.state_key(ly, 6), r.state_key(ly, 7.5))
        self.assertEqual(short, 30 // 2 + 20 + 20 // 2)
        self.assertGreater(long_, short)

    def test_mid_slide_shows_both_lines(self):
        r = FrameRenderer(Style(**self.BASE))
        ly = lrc.parse(self.LRC, duration=7)
        mid, settled = r.render(ly, 3.03), r.render(ly, 3.9)  # 막 시작: 이전 줄이 아직 보임
        top = lambda img: min(y for y, _ in _ink_points(img))
        self.assertLess(top(mid), top(settled))  # 밀려 올라가는 이전 줄이 위에 보인다

    def test_ends_exactly_like_static_frame(self):
        slide = FrameRenderer(Style(**self.BASE))
        still = FrameRenderer(Style(**{**self.BASE, "fade": 0}))
        ly = lrc.parse(self.LRC, duration=7)
        self.assertEqual(slide.render(ly, 3.6).tobytes(), still.render(ly, 3.6).tobytes())

    def test_old_text_leaves_upward_and_offscreen_is_safe(self):
        # 위로 밀려나는 레이어가 화면 위로 넘어가도 오류 없이 잘린다
        style = Style(**{**self.BASE, "center_y": 0.02})
        img = FrameRenderer(style).render(lrc.parse(self.LRC, duration=7), 3.2)
        self.assertEqual(img.size, (200, 400))

    def test_render_bytes_matches(self):
        style = Style(**{**self.BASE, "progress_bar": True})
        ly = lrc.parse(self.LRC, duration=7)
        a, b = FrameRenderer(style), FrameRenderer(style)
        for t in [0.5, 1.1, 1.6, 3.02, 3.3, 4.0]:
            self.assertEqual(a.render_bytes(ly, t, t / 7), b.render(ly, t, t / 7).tobytes())

    def test_bbox_is_computed_once_per_layer(self):
        r = FrameRenderer(Style(**self.BASE))
        ly = lrc.parse(self.LRC, duration=7)
        r.render(ly, 1.5)
        layer = r._text_layer(ly, r.state_key(ly, 1.5), 1.5)
        self.assertEqual(layer._shorts_bbox, layer.getbbox())
        layer._shorts_bbox = (0, 0, 1, 1)  # 저장된 값을 다시 쓰는지 확인
        from shorts.frame import _bbox
        self.assertEqual(_bbox(layer), (0, 0, 1, 1))

    def test_unknown_transition(self):
        with self.assertRaises(ValueError):
            FrameRenderer(Style(transition="spin"))


class RevealTest(unittest.TestCase):
    BASE = dict(width=300, height=300, font_size=30, next_font_size=20, fade=0, reveal="typewriter",
                reveal_cps=10, bg_color=(0, 0, 0), text_color=(255, 255, 255),
                next_color=(255, 0, 0), unsung_color=(0, 0, 255), progress_bar=False)
    LRC = "[00:01.00]ABCDEFGH\n[00:05.00]NEXT"

    def white_xs(self, img):
        return [x for y, x in _ink_points(img) if img.getpixel((x, y))[1] > 200]

    def test_revealed_chars_timing(self):
        r = FrameRenderer(Style(**self.BASE))
        line = lrc.parse(self.LRC, duration=9).lines[0]  # 8글자, 4초
        self.assertEqual(r.revealed_chars(line, 1.0), 0)
        self.assertAlmostEqual(r.revealed_chars(line, 1.35), 3.5)  # 초당 10글자
        self.assertEqual(r.revealed_chars(line, 3.0), 8)
        short = lrc.parse("[00:00.00]ABCDEFGHIJ\n[00:01.00]X", duration=3).lines[0]
        self.assertAlmostEqual(r.revealed_chars(short, 0.3), 5)  # 1초 줄 → 0.6초 안에 10글자

    def test_letters_appear_left_to_right(self):
        r = FrameRenderer(Style(**self.BASE))
        ly = lrc.parse(self.LRC, duration=9)
        start, part, full = r.render(ly, 1.0), r.render(ly, 1.4), r.render(ly, 3)
        self.assertEqual(self.white_xs(start), [])
        self.assertIn((255, 0, 0), _colors(start))  # 다음 줄은 처음부터 제자리에
        self.assertTrue(self.white_xs(part))
        self.assertLess(max(self.white_xs(part)), max(self.white_xs(full)) - 30)
        still = FrameRenderer(Style(**{**self.BASE, "reveal": "none"}))
        self.assertEqual(full.tobytes(), still.render(ly, 3).tobytes())

    def test_works_with_karaoke_and_fast_path(self):
        style = Style(**{**self.BASE, "progress_bar": True})
        ly = lrc.parse("[00:01.00]<00:01.00>AB <00:01.20>CD <00:01.40>EF\n[00:04.00]G", duration=6)
        a, b = FrameRenderer(style), FrameRenderer(style)
        mid = b.render(ly, 1.25)
        self.assertIn((255, 255, 255), _colors(mid))  # 부른 글자
        for t in [1.0, 1.15, 1.3, 1.9, 3.0]:
            self.assertEqual(a.render_bytes(ly, t, t / 6), b.render(ly, t, t / 6).tobytes())

    def test_stroke_is_hidden_too(self):
        style = Style(**{**self.BASE, "stroke_width": 3, "stroke_color": (0, 255, 0), "show_next": False})
        img = FrameRenderer(style).render(lrc.parse(self.LRC, duration=9), 1.0)
        self.assertNotIn((0, 255, 0), _colors(img))

    def test_unknown_reveal(self):
        with self.assertRaises(ValueError):
            FrameRenderer(Style(reveal="spin"))


class VisualizerTest(unittest.TestCase):
    BASE = dict(width=200, height=400, font_size=16, next_font_size=12, fade=0,
                visualizer=True, viz_height=50, viz_bottom=100, viz_width=0.8, viz_gap=0.5,
                bg_color=(0, 0, 0), viz_color=(0, 255, 0), progress_bar=False)

    def test_bar_heights_follow_levels(self):
        r = FrameRenderer(Style(**self.BASE))
        img = r.render(lrc.Lyrics([]), 0, levels=[0.0, 1.0, 0.5, 0.0])
        x0, y0, w, h = r._viz_geometry()
        self.assertEqual((x0, y0, w, h), (20, 250, 160, 50))
        heights = []
        for i in range(4):
            x = round(x0 + (i + 0.5) * w / 4)
            heights.append(sum(img.getpixel((x, y)) == (0, 255, 0) for y in range(y0, y0 + h)))
        self.assertEqual(heights, [2, 50, 25, 2])  # 소리가 없어도 바닥 2px

    def test_off_or_no_levels_draws_nothing(self):
        r = FrameRenderer(Style(**{**self.BASE, "visualizer": False}))
        self.assertEqual(_colors(r.render(lrc.Lyrics([]), 0, levels=[1.0] * 4)), {(0, 0, 0)})
        r = FrameRenderer(Style(**self.BASE))
        self.assertEqual(_colors(r.render(lrc.Lyrics([]), 0)), {(0, 0, 0)})

    def test_render_bytes_matches_with_bars_and_progress(self):
        style = Style(**{**self.BASE, "progress_bar": True, "fade": 0.2})
        ly = lrc.parse("[00:01.00]a\n[00:02.00]<00:02.00>b <00:02.50>c", duration=4)
        a, b = FrameRenderer(style), FrameRenderer(style)
        rng = np.random.default_rng(0)
        for t in [0.5, 1.05, 1.5, 2.2, 3.5]:  # 정지 화면·페이드·노래방 진행을 모두 지난다
            lv = rng.random(8)
            self.assertEqual(a.render_bytes(ly, t, t / 4, lv), b.render(ly, t, t / 4, lv).tobytes())

    def test_content_box_reported(self):
        r = FrameRenderer(Style(**self.BASE))
        names = [n for n, _ in r.content_boxes(lrc.Lyrics([]), 0)]
        self.assertIn("음악 막대", names)


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
