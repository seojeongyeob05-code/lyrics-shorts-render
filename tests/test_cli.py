import argparse
import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image

from shorts import cli

HAVE_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")
LRC = "[00:01.00]하나\n[00:03.00]둘\n[00:05.00]셋\n[00:07.00]넷\n"


class ProgressPrinterTest(unittest.TestCase):
    def test_throttles_and_estimates_remaining(self):
        now = [0.0]
        buf = io.StringIO()
        p = cli.ProgressPrinter(buf, clock=lambda: now[0])
        now[0] = 1.0
        p(25, 100)  # 1초에 25% → 남은 75%는 약 3초
        now[0] = 1.1
        p(30, 100)  # 0.3초 안 지나서 건너뜀
        now[0] = 4.0
        p(100, 100)  # 마지막은 항상
        lines = [x for x in buf.getvalue().split("\r") if x]
        self.assertEqual(len(lines), 2)
        self.assertIn(" 25%", lines[0])
        self.assertIn("약 3초", lines[0])
        self.assertIn("100%", lines[1])


class ParseTimeTest(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(cli.parse_time("45"), 45)
        self.assertEqual(cli.parse_time("0:45"), 45)
        self.assertEqual(cli.parse_time("1:02.5"), 62.5)
        self.assertEqual(cli.parse_time(" 2:00 "), 120)

    def test_rejects_bad_input(self):
        for bad in ["", "abc", "1:2:3", "1:75", "-3"]:
            with self.assertRaises(argparse.ArgumentTypeError, msg=bad):
                cli.parse_time(bad)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.lrc = os.path.join(self.dir, "song.lrc")
        with open(self.lrc, "w", encoding="utf-8") as f:
            f.write(LRC)

    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(list(argv))
        return buf.getvalue()

    def test_frame_preview_default_name_and_background(self):
        bg = os.path.join(self.dir, "bg.png")
        Image.new("RGB", (50, 50), (10, 120, 200)).save(bg)
        out = self.run_cli("frame", self.lrc, "--at", "0:00.5", "--bg", bg)
        png = os.path.join(self.dir, "song.png")
        self.assertIn(png, out)
        img = Image.open(png)
        self.assertEqual(img.size, (1080, 1920))
        self.assertEqual(img.getpixel((5, 5)), (10, 120, 200))

    def test_style_option_and_list(self):
        out = self.run_cli("frame", self.lrc, "--at", "0:00.5", "--style", "minimal", "-o",
                           os.path.join(self.dir, "m.png"))
        img = Image.open(out.strip())
        self.assertEqual(img.getpixel((5, 5)), (250, 250, 247))
        self.assertIn("neon", self.run_cli("styles"))
        with self.assertRaises(SystemExit) as cm:
            self.run_cli("frame", self.lrc, "--style", "nope")
        self.assertIn("스타일을 찾을 수 없습니다", str(cm.exception))

    def test_title_and_artist_options(self):
        from shorts.cli import _apply_info, build_parser
        from shorts import lrc as lrc_mod
        ly = lrc_mod.parse("[ti:원래 제목]\n[ar:원래 가수]\n[00:01.00]a")
        args = build_parser().parse_args(["frame", self.lrc, "--title", "새 제목", "--artist", ""])
        _apply_info(args, ly)
        self.assertEqual((ly.meta["ti"], ly.meta["ar"]), ("새 제목", ""))
        args = build_parser().parse_args(["frame", self.lrc])
        ly2 = lrc_mod.parse("[ti:그대로]\n[00:01.00]a")
        self.assertEqual(_apply_info(args, ly2).meta["ti"], "그대로")

    def test_start_after_song_end_is_an_error(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_cli("render", self.lrc, "--start", "1:00")
        self.assertIn("곡 길이", str(cm.exception))

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg 없음")
    def test_render_segment_with_audio(self):
        audio = os.path.join(self.dir, "a.m4a")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
                        "sine=duration=9", "-c:a", "aac", audio], check=True)
        out = os.path.join(self.dir, "clip.mp4")
        msg = self.run_cli("render", self.lrc, "--audio", audio, "--start", "2.5",
                           "--duration", "3", "--fps", "10", "-o", out)
        self.assertIn("clip.mp4", msg)
        info = json.loads(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
             "-of", "json", out], capture_output=True, text=True, check=True).stdout)
        self.assertAlmostEqual(float(info["format"]["duration"]), 3, delta=0.1)
        self.assertEqual(len(info["streams"]), 2)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg 없음")
    def test_preview_is_half_size_and_15fps(self):
        msg = self.run_cli("render", self.lrc, "--duration", "2", "--preview")
        out = os.path.join(self.dir, "song.preview.mp4")
        self.assertIn(out, msg)
        info = json.loads(subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
             "stream=width,height,r_frame_rate", "-of", "json", out],
            capture_output=True, text=True, check=True).stdout)["streams"][0]
        self.assertEqual((info["width"], info["height"], info["r_frame_rate"]), (540, 960, "15/1"))

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg 없음")
    def test_duration_is_capped_at_song_end(self):
        # 음원 없이: 마지막 줄 끝(7초 + 최대 8초 = 15초)까지만
        msg = self.run_cli("render", self.lrc, "--start", "10", "--duration", "30", "--fps", "5")
        self.assertIn("(5.0s", msg)


if __name__ == "__main__":
    unittest.main()
