import unittest

from shorts import lrc
from shorts.align import align_lines, to_lrc


def words_from(text_times):
    return [{"start": t, "end": t + 0.4, "word": w} for w, t in text_times]


class AlignTest(unittest.TestCase):
    def test_lines_get_start_and_word_marks(self):
        lines = ["今日は晴れ", "明日は雨"]
        words = words_from([("今日", 1.0), ("は", 1.4), ("晴れ", 1.8), ("明日", 5.0), ("は", 5.4), ("雨", 5.8)])
        a = align_lines(lines, words)
        self.assertEqual((a[0].start, a[1].start), (1.0, 5.0))
        self.assertEqual(a[0].marks, [(1.0, 0), (1.4, 2), (1.8, 3)])

    def test_recognition_mistakes_and_katakana_are_tolerated(self):
        # 인식이 "モノ"를 "もの"로, "簡単"을 "肩"으로 틀려도 맞는 글자로 자리를 잡는다
        lines = ["必死なモノさ", "簡単にでない"]
        words = words_from([("必死な", 2.0), ("もの", 2.6), ("さ", 3.0), ("肩に", 6.0), ("出ない", 6.5)])
        a = align_lines(lines, words)
        self.assertEqual(a[0].start, 2.0)
        self.assertAlmostEqual(a[1].start, 6.0 - 0.2 * 1, places=2)  # 첫 글자 못 맞춤 → 조금 앞으로

    def test_missing_line_is_placed_between_neighbours(self):
        lines = ["ああああ", "ぜんぜんちがう", "いいいい"]
        words = words_from([("ああああ", 1.0), ("いいいい", 9.0)])
        a = align_lines(lines, words)
        self.assertTrue(a[0].end < a[1].start < a[2].start)
        self.assertEqual(a[1].marks, [])

    def test_to_lrc_round_trip_with_subs_and_gap(self):
        lines = ["今日は晴れ", "明日は雨"]
        words = words_from([("今日", 1.0), ("は", 1.4), ("晴れ", 1.8), ("明日", 9.0), ("は", 9.4), ("雨", 9.8)])
        text = to_lrc(align_lines(lines, words), subs=[["쿄우와 하레", "오늘은 맑음"], ["아시타와 아메", "내일은 비"]],
                      meta={"ti": "T"})
        ly = lrc.parse(text, duration=12)
        self.assertEqual(ly.meta["ti"], "T")
        self.assertEqual([ln.text for ln in ly.lines], lines)
        self.assertEqual(ly.lines[0].subs, ("쿄우와 하레", "오늘은 맑음"))
        self.assertEqual(ly.lines[0].marks[1], (1.4, 2))
        self.assertLess(ly.lines[0].end, 9.0)  # 다음 줄까지 멀면 빈 줄로 끝냄


if __name__ == "__main__":
    unittest.main()
