"""tools/lrc-sync.html(브라우저 싱크 도구)을 실제 Chromium으로 돌려 본다.

node와 playwright가 없는 환경에서는 건너뛴다.
"""
import json
import os
import shutil
import subprocess
import unittest

from shorts import lrc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "tools", "lrc-sync.html")
SCRIPT = os.path.join(ROOT, "tests", "lrc_sync_check.js")


def _run():
    if not shutil.which("node"):
        return None
    has_pw = subprocess.run(["node", "-e", "require('playwright')"], capture_output=True)
    if has_pw.returncode != 0:
        return None
    out = subprocess.run(["node", SCRIPT, HTML], capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise AssertionError(f"브라우저 테스트 실패:\n{out.stderr}")
    return json.loads(out.stdout)


class SyncToolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = _run()
        if cls.r is None:
            raise unittest.SkipTest("node + playwright 없음")

    def test_no_page_errors_and_fits_phone(self):
        self.assertEqual(self.r["errors"], [])
        self.assertFalse(self.r["overflowX"])

    def test_time_format(self):
        self.assertEqual(self.r["format"][:4], ["00:00.00", "00:01.23", "01:00.00", "01:01.50"])
        self.assertEqual(self.r["format"][5], "00:00.00")  # 음수는 0으로

    def test_taps_make_lrc_our_parser_reads(self):
        self.assertEqual(self.r["tapLabel"], "다음 줄 시작 (1/3)")  # 빈 줄·공백은 무시
        ly = lrc.parse(self.r["afterTaps"], duration=12)
        # 0.15초 반응 지연 보정, '쉼'은 앞 줄을 끝냄
        self.assertEqual([(ln.start, ln.end, ln.text) for ln in ly.lines],
                         [(1.0, 3.5, "첫 줄"), (3.5, 6.0, "둘째 줄"), (8.0, 12, "셋째 줄")])
        self.assertTrue(self.r["tapDisabled"])
        self.assertFalse(self.r["extraTap"])

    def test_undo_reload_and_edit(self):
        self.assertEqual(self.r["afterUndo"], "[00:01.00]첫 줄\n[00:03.50]둘째 줄\n")
        self.assertEqual(self.r["afterReload"], self.r["afterUndo"])
        self.assertEqual(self.r["afterEdit"], "[00:01.00]첫 줄\n")

    def test_word_mode_makes_karaoke_lrc(self):
        w = self.r["word"]
        self.assertEqual(w["label"], "다음: Hello")
        self.assertEqual(w["full"], "[00:01.00]<00:01.00>Hello <00:01.50>big <00:02.00>world\n"
                                    "[00:04.00]<00:04.00>next <00:04.50>line\n")
        self.assertEqual(w["cursorWords"], 0)  # 다 찍으면 다음 단어 표시 없음
        ly = lrc.parse(w["full"], duration=6)
        self.assertEqual(ly.lines[0].text, "Hello big world")
        self.assertEqual(ly.lines[0].marks, ((1.0, 0), (1.5, 6), (2.0, 10)))
        self.assertEqual(ly.lines[1].marks, ((4.0, 0), (4.5, 5)))
        self.assertEqual(w["afterUndo"], "[00:01.00]<00:01.00>Hello <00:01.50>big <00:02.00>world\n"
                                         "[00:04.00]next line\n")
        self.assertFalse(w["lineModeTap"])  # 줄 모드: 둘째 줄 다음은 없음

    def test_preview_follows_taps(self):
        before, mid, after_last_word, second, done = self.r["preview"]
        self.assertEqual((before["cur"], before["all"], before["next"]), (None, "", "Hello big world"))
        # 1.75초: big(1.5초, 6번째 글자)~world(2.0초, 10번째) 사이 절반 → 8글자까지 밝게
        self.assertEqual((mid["cur"], mid["sung"], mid["lit"]), (0, 8, "Hello bi"))
        self.assertEqual(mid["next"], "next line")
        # 마지막 단어는 다음 줄(4.0초)까지 이어진다: 3.0초면 world의 절반
        self.assertEqual(after_last_word["sung"], 12.5)
        self.assertEqual((second["cur"], second["next"]), (1, ""))
        self.assertEqual(done["cur"], None)  # 마지막 줄도 최대 8초 뒤엔 사라짐

    def test_mode_saved_and_legacy_taps_read(self):
        self.assertEqual(self.r["modeAfterReload"], "word")
        self.assertEqual(self.r["legacy"], "[00:01.00]a\n[00:02.00]\n")

    def test_keyboard(self):
        self.assertEqual(self.r["afterKey"], "[00:00.00]첫 줄\n")
        self.assertEqual(self.r["afterKeyUndo"].strip(), "")


if __name__ == "__main__":
    unittest.main()
