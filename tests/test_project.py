import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image

from shorts import cli, project

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "examples", "demo", "demo.json")
HAVE_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


class LoadProjectTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        with open(os.path.join(self.dir, "a.lrc"), "w") as f:
            f.write("[00:01.00]a\n")

    def write(self, data):
        path = os.path.join(self.dir, "song.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
        return path

    def test_paths_and_times(self):
        p = project.load_project(self.write({
            "lyrics": "a.lrc", "out": "out/x.mp4", "start": "0:45, 1:30", "duration": 20,
            "title": "T", "style": "neon", "fps": 24}))
        self.assertEqual(p["lyrics"], os.path.join(self.dir, "a.lrc"))
        self.assertEqual(p["out"], os.path.join(self.dir, "out", "x.mp4"))
        self.assertEqual((p["start"], p["duration"]), ([45, 90], [20.0]))
        self.assertEqual((p["title"], p["style"], p["fps"]), ("T", "neon", 24))
        self.assertEqual(p["_stem"], os.path.join(self.dir, "song"))
        self.assertEqual(project.load_project(self.write({"lyrics": "a.lrc", "start": ["0:10", 30]}))["start"],
                         [10, 30])

    def test_style_file_next_to_project(self):
        with open(os.path.join(self.dir, "mine.json"), "w") as f:
            f.write("{}")
        p = project.load_project(self.write({"lyrics": "a.lrc", "style": "mine.json"}))
        self.assertEqual(p["style"], os.path.join(self.dir, "mine.json"))

    def test_errors(self):
        cases = [
            ({"audio": "x.mp3"}, "lyrics"),
            ({"lyrics": "nope.lrc"}, "파일이 없습니다"),
            ({"lyrics": "a.lrc", "lyric": "a.lrc"}, "알 수 없는 항목 lyric"),
            ({"lyrics": "a.lrc", "start": "soon"}, "시간은"),
            ({"lyrics": "a.lrc", "fps": 0}, "fps"),
            ({"lyrics": "a.lrc", "style": 3}, "style"),
            ("[1]", "객체"),
            ("{oops", "JSON"),
        ]
        for data, needle in cases:
            with self.subTest(data=data):
                with self.assertRaises(ValueError) as cm:
                    project.load_project(self.write(data))
                self.assertIn(needle, str(cm.exception))


class ResolveArgsTest(unittest.TestCase):
    def parse(self, *argv):
        return cli.resolve_args(cli.build_parser().parse_args(list(argv)))

    def test_project_fills_and_cli_overrides(self):
        a = self.parse("render", DEMO, "--duration", "3")
        self.assertEqual(a.lrc, os.path.join(ROOT, "examples", "demo", "demo.lrc"))
        self.assertEqual(a.start, [0, 6])
        self.assertEqual(a.duration, [3])  # 명령줄이 우선
        self.assertEqual(a.fps, 30)  # 기본값
        self.assertEqual(a.stem, os.path.join(ROOT, "examples", "demo", "demo"))
        self.assertIsInstance(a.style, dict)

    def test_plain_lrc_gets_defaults(self):
        a = self.parse("render", "x.lrc")
        self.assertEqual((a.style, a.start, a.fps, a.stem), ("default", [0.0], 30, "x"))

    def test_bad_project_is_readable_error(self):
        with self.assertRaises(SystemExit) as cm:
            self.parse("render", os.path.join(ROOT, "missing.json"))
        self.assertIn("곡 설정 파일", str(cm.exception))


class DemoProjectTest(unittest.TestCase):
    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg 없음")
    def test_preview_names_sit_next_to_final(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        proj = os.path.join(d, "song.json")
        shutil.copy(os.path.join(ROOT, "examples", "demo", "demo.lrc"), os.path.join(d, "demo.lrc"))
        with open(DEMO) as f, open(proj, "w") as g:
            g.write(f.read())
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(["render", proj, "--preview", "--fps", "5", "--duration", "1"])
        self.assertEqual(sorted(n for n in os.listdir(d) if n.endswith(".mp4")),
                         ["song-1.preview.mp4", "song-2.preview.mp4"])

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)

    def test_frame_uses_inline_style(self):
        out = os.path.join(self.dir, "f.png")
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(["frame", DEMO, "--at", "1", "-o", out])
        img = Image.open(out)
        self.assertEqual(img.size, (1080, 1920))
        self.assertEqual(img.getpixel((0, 0)), (0x2A, 0x1B, 0x4A))  # sunset 그라데이션 위쪽 색

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg 없음")
    def test_render_segments_from_project(self):
        base = os.path.join(self.dir, "demo.mp4")
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(["render", DEMO, "--preview", "--fps", "5", "-o", base])
        for k in (1, 2):
            self.assertTrue(os.path.getsize(os.path.join(self.dir, f"demo-{k}.mp4")) > 0)


if __name__ == "__main__":
    unittest.main()
