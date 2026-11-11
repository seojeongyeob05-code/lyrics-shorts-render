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

    def test_keyboard(self):
        self.assertEqual(self.r["afterKey"], "[00:00.00]첫 줄\n")
        self.assertEqual(self.r["afterKeyUndo"].strip(), "")


if __name__ == "__main__":
    unittest.main()
