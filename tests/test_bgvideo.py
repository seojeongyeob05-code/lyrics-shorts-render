import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest

from shorts import cli, lrc
from shorts.bgvideo import BackgroundVideo, is_video
from shorts.frame import FrameRenderer, Style, darken_mask

HAVE_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg 없음")
class BackgroundVideoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.video = os.path.join(cls.dir, "bg.mp4")
        # 앞 1초 빨강, 뒤 1초 파랑(가로로 긴 영상 → 세로 화면에 꽉 채워 잘림)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=red:s=160x90:d=1:r=30",
                        "-f", "lavfi", "-i", "color=blue:s=160x90:d=1:r=30", "-filter_complex",
                        "concat=n=2:v=1", "-pix_fmt", "yuv420p", cls.video], check=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir)

    def color(self, img):
        r, g, b = img.getpixel((img.width // 2, img.height // 2))
        return "red" if r > 150 and b < 100 else "blue" if b > 150 and r < 100 else (r, g, b)

    def test_plays_loops_and_seeks_back(self):
        v = BackgroundVideo(self.video, (90, 160))
        self.addCleanup(v.close)
        self.assertEqual(v.frame_at(0.3).size, (90, 160))
        self.assertEqual(self.color(v.frame_at(0.3)), "red")
        self.assertEqual(self.color(v.frame_at(1.5)), "blue")
        self.assertEqual(self.color(v.frame_at(2.4)), "red")  # 2초 영상이 반복
        self.assertEqual(self.color(v.frame_at(1.6)), "blue")  # 뒤로 가도 맞는 자리
        self.assertIs(v.frame_at(1.6), v.frame_at(1.61))  # 같은 프레임 번호면 다시 안 읽음

    def test_darken_mask_applied(self):
        mask = darken_mask(Style(width=90, height=160, bg_dim=0.5), (90, 160))
        v = BackgroundVideo(self.video, (90, 160), darken=mask)
        self.addCleanup(v.close)
        r, _, _ = v.frame_at(0.2).getpixel((45, 80))
        self.assertTrue(100 < r < 150)

    def test_renderer_draws_lyrics_over_video(self):
        style = Style(width=90, height=160, font_size=16, fade=0, text_color=(0, 255, 0),
                      show_info=False, progress_height=4, progress_bottom=20)
        ly = lrc.parse("[00:00.00]WWW", duration=3)
        with FrameRenderer(style, bg_video=self.video) as a, FrameRenderer(style, bg_video=self.video) as b:
            red, blue = a.render(ly, 0.5), a.render(ly, 1.5)
            self.assertNotEqual(red.getpixel((5, 5)), blue.getpixel((5, 5)))
            self.assertIn((0, 255, 0), {c for _, c in red.getcolors(10**5)})
            for t in [0.2, 1.2, 2.2]:
                self.assertEqual(a.render_bytes(ly, t, t / 3), b.render(ly, t, t / 3).tobytes())

    def test_cli_render_with_video_background(self):
        lrc_path = os.path.join(self.dir, "s.lrc")
        with open(lrc_path, "w") as f:
            f.write("[00:00.50]hello\n[00:01.50]world\n")
        out = os.path.join(self.dir, "o.mp4")
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(["render", lrc_path, "--bg", self.video, "--duration", "2", "--preview", "-o", out])
            cli.main(["frame", lrc_path, "--bg", self.video, "--at", "1.6", "-o", out + ".png"])
        self.assertGreater(os.path.getsize(out), 0)
        self.assertTrue(os.path.exists(out + ".png"))

    def test_missing_file(self):
        with self.assertRaises(ValueError):
            BackgroundVideo(os.path.join(self.dir, "nope.mp4"), (10, 10))


class HelpersTest(unittest.TestCase):
    def test_is_video(self):
        self.assertTrue(is_video("a/B.MP4"))
        self.assertTrue(is_video("x.webm"))
        self.assertFalse(is_video("bg.jpg"))
        self.assertFalse(is_video(None))

    def test_darken_mask(self):
        self.assertIsNone(darken_mask(Style(), (10, 10)))
        m = darken_mask(Style(bg_dim=0.2, bg_shade=0.8), (10, 100))
        self.assertAlmostEqual(m.getpixel((0, 30)), 51, delta=2)  # 가운데 위쪽은 dim만
        self.assertAlmostEqual(m.getpixel((0, 99)), 214, delta=2)  # 아래 끝: 1-(1-0.2)(1-0.8) = 0.84


if __name__ == "__main__":
    unittest.main()
