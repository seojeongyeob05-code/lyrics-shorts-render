import contextlib
import io
import os
import shutil
import tempfile
import unittest

from PIL import Image

from shorts import cli, guide, lrc
from shorts.frame import FrameRenderer, Style

LONG = lrc.parse("[00:01.00]WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW", duration=5)


class GuideTest(unittest.TestCase):
    def test_zone_boxes_scale_with_screen(self):
        zones = dict(guide.zone_boxes(1080, 1920))
        self.assertEqual(zones["위쪽 메뉴"], (0, 0, 1080, 144))
        self.assertEqual(dict(guide.zone_boxes(540, 960))["오른쪽 버튼"], (459, 403, 540, 960))

    def test_overlaps(self):
        self.assertTrue(guide.overlaps((0, 0, 10, 10), (5, 5, 20, 20)))
        self.assertFalse(guide.overlaps((0, 0, 10, 10), (10, 0, 20, 10)))  # 맞닿기만 하면 안 겹침

    def test_defaults_stay_clear_of_app_ui(self):
        r = FrameRenderer(Style(font_size=72))
        self.assertEqual(guide.find_overlaps(r, LONG, [1.5]), [])

    def test_wide_text_and_low_bar_are_reported(self):
        r = FrameRenderer(Style(max_text_width=0.98, progress_bottom=100))
        found = {(c, z) for c, z, _ in guide.find_overlaps(r, LONG, [0.5, 1.5, 2.5])}
        self.assertIn(("가사", "오른쪽 버튼"), found)
        self.assertIn(("진행 바", "아래쪽 제목·설명"), found)
        r = FrameRenderer(Style(max_text_width=0.98, show_next=False))
        times = {c: t for c, _, t in guide.find_overlaps(r, LONG, [0.5, 1.5, 2.5])}
        self.assertEqual(times["가사"], 1.5)  # 처음 걸린 시각(줄 시작 전엔 화면이 비어 있음)

    def test_draw_guide_tints_zones_only(self):
        img = Image.new("RGB", (1080, 1920), (0, 0, 0))
        out = guide.draw_guide(img)
        self.assertEqual(out.size, img.size)
        self.assertGreater(out.getpixel((540, 100))[0], 20)  # 위쪽 메뉴: 붉게
        self.assertEqual(out.getpixel((540, 960)), (0, 0, 0))  # 가운데: 그대로


class GuideCliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.lrc = os.path.join(self.dir, "s.lrc")
        with open(self.lrc, "w") as f:
            f.write("[00:01.00]WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW\n")
        self.style = os.path.join(self.dir, "wide.json")
        with open(self.style, "w") as f:
            f.write('{"max_text_width": 0.98}')

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            cli.main(list(argv))
        return out.getvalue(), err.getvalue()

    def test_frame_guide_and_warning(self):
        png = os.path.join(self.dir, "g.png")
        _, err = self.run_cli("frame", self.lrc, "--at", "1.5", "--guide", "--style", self.style, "-o", png)
        self.assertIn("'오른쪽 버튼'", err)
        self.assertGreater(Image.open(png).getpixel((540, 100))[0], 20)

    def test_no_warning_with_defaults(self):
        _, err = self.run_cli("frame", self.lrc, "--at", "1.5", "-o", os.path.join(self.dir, "d.png"))
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
