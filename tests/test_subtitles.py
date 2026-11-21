import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image

from shorts import cli, lrc, subtitles
from shorts.frame import Style

LRC = ("[ti:곡]\n[00:00.50]첫 줄\n[00:02.00]<00:02.50>노래 <00:03.00>{방}<00:03.50>\n"
       "[01:02.25]마지막\n")


def has_libass():
    if not shutil.which("ffmpeg"):
        return False
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return " ass " in out


class SrtTest(unittest.TestCase):
    def test_blocks(self):
        srt = subtitles.to_srt(lrc.parse(LRC, duration=65))
        blocks = srt.strip().split("\n\n")
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0], "1\n00:00:00,500 --> 00:00:02,000\n첫 줄")
        self.assertEqual(blocks[1].splitlines()[2], "노래 {방}")  # 태그는 빠지고 글자만
        self.assertEqual(blocks[2].splitlines()[1], "00:01:02,250 --> 00:01:05,000")

    def test_hours(self):
        self.assertEqual(subtitles._srt_time(3723.004), "01:02:03,004")


class AssTest(unittest.TestCase):
    def test_time_and_color(self):
        self.assertEqual(subtitles._ass_time(62.256), "0:01:02.26")
        self.assertEqual(subtitles._ass_color((0x11, 0x22, 0x33)), "&H00332211")

    def test_karaoke_tags(self):
        line = lrc.parse(LRC, duration=65).lines[1]
        # 줄은 2.0초에 뜨고 첫 단어는 2.5초 → 0.5초 쉼, 이어서 단어마다 \kf, 중괄호는 바꿔 씀
        self.assertEqual(subtitles.karaoke_text(line), "{\\k50}{\\kf50}노래 {\\kf50}(방)")

    def test_last_word_runs_to_line_end_without_closing_tag(self):
        line = lrc.parse("[00:01.00]<00:01.00>a <00:02.00>b", duration=4).lines[0]
        self.assertEqual(subtitles.karaoke_text(line), "{\\kf100}a {\\kf200}b")

    def test_document(self):
        ass = subtitles.to_ass(lrc.parse(LRC, duration=65), Style(text_color=(255, 0, 0)), "Test Font")
        self.assertIn("PlayResX: 1080", ass)
        self.assertIn("Title: 곡", ass)
        self.assertIn("Style: Default,Test Font,72,&H000000FF,", ass)
        dialogues = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
        self.assertEqual(len(dialogues), 3)
        self.assertTrue(dialogues[0].startswith("Dialogue: 0,0:00:00.50,0:00:02.00,Default,"))
        self.assertTrue(dialogues[0].endswith(",첫 줄"))

    @unittest.skipUnless(has_libass(), "libass 없는 ffmpeg")
    def test_libass_draws_it_near_center(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        ass = os.path.join(d, "s.ass")
        with open(ass, "w", encoding="utf-8") as f:
            f.write(subtitles.to_ass(lrc.parse("[00:00.00]WWWW", duration=2)))
        png = os.path.join(d, "f.png")
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1",
                        "-vf", f"ass={ass}", "-frames:v", "1", png], check=True)
        img = Image.open(png).convert("L")
        ys = [y for y in range(0, 1920, 4) if img.crop((0, y, 1080, y + 1)).getextrema()[1] > 128]
        self.assertTrue(ys)
        self.assertAlmostEqual((min(ys) + max(ys)) / 2, 960, delta=80)  # center_y 0.5 근처


class ExportCliTest(unittest.TestCase):
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

    def read(self, name):
        with open(os.path.join(self.dir, name), encoding="utf-8") as f:
            return f.read()

    def test_default_srt_next_to_lyrics(self):
        self.assertIn("song.srt", self.run_cli("export", self.lrc))
        self.assertTrue(self.read("song.srt").startswith("1\n00:00:00,500"))

    def test_segments_shift_to_zero(self):
        self.run_cli("export", self.lrc, "--start", "0,2", "--duration", "2,1.2")
        first, second = self.read("song-1.srt"), self.read("song-2.srt")
        self.assertIn("첫 줄", first)
        self.assertNotIn("노래", first)
        self.assertTrue(second.startswith("1\n00:00:00,000 --> 00:00:01,200\n노래 {방}"))

    def test_ass_with_style_and_title(self):
        self.run_cli("export", self.lrc, "--format", "ass", "--style", "neon", "--title", "새 제목")
        ass = self.read("song.ass")
        self.assertIn("Title: 새 제목", ass)
        self.assertIn(",80,&H00D84FFF,", ass)  # neon: 글자 80px, #FF4FD8


if __name__ == "__main__":
    unittest.main()
