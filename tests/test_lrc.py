import unittest

from shorts import lrc

SAMPLE = """\
[ti:테스트 곡]
[ar:아무개]
[00:01.00]첫 번째 줄
[00:03.50]두 번째 줄
[00:05.00][00:09.00]후렴
[00:07.00]
"""


class ParseTest(unittest.TestCase):
    def test_meta(self):
        ly = lrc.parse(SAMPLE)
        self.assertEqual(ly.meta["ti"], "테스트 곡")
        self.assertEqual(ly.meta["ar"], "아무개")

    def test_lines_sorted_with_repeats(self):
        ly = lrc.parse(SAMPLE, duration=12)
        self.assertEqual(
            [(ln.start, ln.text) for ln in ly.lines],
            [(1.0, "첫 번째 줄"), (3.5, "두 번째 줄"), (5.0, "후렴"), (9.0, "후렴")],
        )

    def test_end_times(self):
        ly = lrc.parse(SAMPLE, duration=12)
        # 빈 줄(7초)이 후렴을 끝낸다. 마지막 줄은 곡 끝까지.
        self.assertEqual([ln.end for ln in ly.lines], [3.5, 5.0, 7.0, 12])

    def test_max_line_caps_long_gaps(self):
        ly = lrc.parse("[00:00.00]a\n[00:30.00]b", max_line=5)
        self.assertEqual(ly.lines[0].end, 5)
        self.assertEqual(ly.lines[1].end, 35)

    def test_fraction_precision(self):
        ly = lrc.parse("[01:02.5]a\n[01:02.25]b\n[01:02.125]c")
        self.assertEqual([ln.start for ln in ly.lines], [62.125, 62.25, 62.5])

    def test_offset(self):
        ly = lrc.parse("[offset:+500]\n[00:02.00]a")
        self.assertEqual(ly.lines[0].start, 1.5)


class QueryTest(unittest.TestCase):
    def setUp(self):
        self.ly = lrc.parse(SAMPLE, duration=12)

    def test_line_at(self):
        self.assertIsNone(self.ly.line_at(0.5))
        self.assertEqual(self.ly.line_at(1.0).text, "첫 번째 줄")
        self.assertEqual(self.ly.line_at(4.0).text, "두 번째 줄")
        self.assertIsNone(self.ly.line_at(8.0))  # 빈 줄 구간
        self.assertEqual(self.ly.line_at(11.9).text, "후렴")
        self.assertIsNone(self.ly.line_at(12.0))

    def test_clip(self):
        c = self.ly.clip(4.0, 10.0)
        self.assertEqual(
            [(ln.start, ln.end, ln.text) for ln in c.lines],
            [(0.0, 1.0, "두 번째 줄"), (1.0, 3.0, "후렴"), (5.0, 6.0, "후렴")],
        )


if __name__ == "__main__":
    unittest.main()
