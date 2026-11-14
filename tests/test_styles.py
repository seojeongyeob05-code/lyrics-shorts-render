import json
import os
import shutil
import tempfile
import unittest

from shorts import lrc, styles
from shorts.frame import FrameRenderer, Style


class StylesTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)

    def write(self, name, data):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
        return path

    def test_all_builtin_presets_load(self):
        names = styles.list_presets()
        self.assertIn("default", names)
        for name in names:
            with self.subTest(name=name):
                self.assertIsInstance(styles.load_style(name), Style)
        self.assertEqual(styles.load_style("default"), Style())

    def test_values_are_converted(self):
        path = self.write("s.json", {"text_color": "#FFE066", "next_color": [1, 2, 3],
                                     "font_size": 80, "center_y": 1, "progress_bar": False,
                                     "font_path": "fonts/a.ttf"})
        s = styles.load_style(path)
        self.assertEqual(s.text_color, (255, 224, 102))
        self.assertEqual(s.next_color, (1, 2, 3))
        self.assertEqual((s.font_size, s.center_y, s.progress_bar), (80, 1.0, False))
        self.assertEqual(s.font_path, os.path.join(self.dir, "fonts", "a.ttf"))
        self.assertEqual(s.bg_color, Style().bg_color)  # 안 적은 값은 기본값

    def test_gradient_value(self):
        self.assertEqual(styles.load_style(self.write("g.json", {"bg_gradient": "#102030"})).bg_gradient,
                         (16, 32, 48))
        self.assertIsNone(styles.load_style(self.write("n.json", {"bg_gradient": None})).bg_gradient)

    def test_extends(self):
        path = self.write("child.json", {"extends": "neon", "font_size": 90})
        s = styles.load_style(path)
        self.assertEqual(s.font_size, 90)
        self.assertEqual(s.text_color, styles.load_style("neon").text_color)

    def test_errors_are_readable(self):
        cases = {
            "unknown.json": ({"text_colour": "#FFFFFF"}, "text_colour"),
            "badcolor.json": ({"text_color": "white"}, "#RRGGBB"),
            "badint.json": ({"font_size": "big"}, "정수"),
            "badbool.json": ({"progress_bar": "no"}, "true/false"),
            "broken.json": ("{not json", "JSON"),
            "list.json": ([1, 2], "객체"),
            "shape.json": ({"cover_shape": "star"}, "rounded"),
        }
        for name, (data, needle) in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as cm:
                    styles.load_style(self.write(name, data))
                self.assertIn(needle, str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            styles.load_style("no-such-preset")
        self.assertIn("neon", str(cm.exception))  # 쓸 수 있는 이름을 알려준다

    def test_extends_cycle(self):
        a = self.write("a.json", {"extends": os.path.join(self.dir, "b.json")})
        self.write("b.json", {"extends": a})
        with self.assertRaises(ValueError) as cm:
            styles.load_style(a)
        self.assertIn("순환", str(cm.exception))


class ShowNextTest(unittest.TestCase):
    def test_hides_upcoming_line(self):
        ly = lrc.parse("[00:00.00]a\n[00:02.00]b", duration=4)
        base = dict(width=120, height=200, font_size=20, next_font_size=14, fade=0,
                    bg_color=(0, 0, 0), next_color=(255, 0, 0))
        shown = FrameRenderer(Style(**base)).render(ly, 1)
        hidden = FrameRenderer(Style(**base, show_next=False)).render(ly, 1)
        red = lambda img: any(c[0] > 200 and c[1] < 50 for _, c in img.getcolors(10**5))
        self.assertTrue(red(shown))
        self.assertFalse(red(hidden))


if __name__ == "__main__":
    unittest.main()
