import json
import os
import shutil
import subprocess
import tempfile
import unittest

from shorts import lrc
from shorts.frame import FrameRenderer, Style
from shorts.video import VideoOptions, build_ffmpeg_cmd, render_video

LYRICS = lrc.parse("[00:00.50]one\n[00:01.20]two\n[00:01.80]three", duration=2.5)
HAVE_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,nb_frames:format=duration", "-of", "json", path],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out)


class CommandTest(unittest.TestCase):
    def test_without_audio(self):
        cmd = build_ffmpeg_cmd("o.mp4", (1080, 1920), 3, VideoOptions(fps=24))
        self.assertIn("1080x1920", cmd)
        self.assertEqual(cmd[cmd.index("-r") + 1], "24")
        self.assertNotIn("-map", cmd)
        self.assertEqual(cmd[-1], "o.mp4")

    def test_with_audio_seeks_and_maps(self):
        cmd = build_ffmpeg_cmd("o.mp4", (10, 10), 30, VideoOptions(), "song.mp3", 45.5)
        i = cmd.index("song.mp3")
        self.assertEqual(cmd[i - 5:i], ["-ss", "45.500", "-t", "30.000", "-i"])
        self.assertIn("1:a", cmd)


class StateKeyTest(unittest.TestCase):
    def test_key_changes_only_when_lines_change(self):
        r = FrameRenderer(Style(width=64, height=64))
        keys = [r.state_key(LYRICS, t / 10) for t in range(25)]
        self.assertEqual(len(set(keys)), 4)  # 시작 전, one, two, three


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg 없음")
class RenderVideoTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.renderer = FrameRenderer(Style(width=180, height=320, font_size=20, next_font_size=14))

    def test_video_only(self):
        out = os.path.join(self.dir, "v.mp4")
        drawn = render_video(LYRICS, out, 2.0, self.renderer, VideoOptions(fps=10))
        self.assertEqual(drawn, 4)  # 20프레임 중 실제로 그린 건 화면이 바뀔 때뿐
        info = probe(out)
        (v,) = info["streams"]
        self.assertEqual((v["codec_type"], v["width"], v["height"]), ("video", 180, 320))
        self.assertEqual(int(v["nb_frames"]), 20)

    def test_with_audio_segment(self):
        audio = os.path.join(self.dir, "tone.m4a")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=5", "-c:a", "aac", audio], check=True)
        out = os.path.join(self.dir, "va.mp4")
        render_video(LYRICS, out, 1.5, self.renderer, VideoOptions(fps=10),
                     audio=audio, audio_start=2.0)
        info = probe(out)
        self.assertEqual(sorted(s["codec_type"] for s in info["streams"]), ["audio", "video"])
        self.assertAlmostEqual(float(info["format"]["duration"]), 1.5, delta=0.1)

    def test_progress_callback(self):
        seen = []
        render_video(LYRICS, os.path.join(self.dir, "p.mp4"), 1.0, self.renderer,
                     VideoOptions(fps=10), on_progress=lambda d, n: seen.append((d, n)))
        self.assertEqual(seen, [(k, 10) for k in range(1, 11)])

    def test_ffmpeg_error_is_reported(self):
        with self.assertRaises(RuntimeError) as cm:
            render_video(LYRICS, os.path.join(self.dir, "x.mp4"), 1.0, self.renderer,
                         VideoOptions(fps=10), audio=os.path.join(self.dir, "missing.mp3"))
        self.assertIn("ffmpeg", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
