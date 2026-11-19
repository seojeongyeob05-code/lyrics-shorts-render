import os
import shutil
import subprocess
import tempfile
import unittest

import numpy as np

from shorts import audio

HAVE_FFMPEG = shutil.which("ffmpeg") is not None
SR = audio.SAMPLE_RATE


def tone(hz, seconds):
    t = np.arange(int(SR * seconds)) / SR
    return (0.5 * np.sin(2 * np.pi * hz * t)).astype(np.float32)


class LevelsTest(unittest.TestCase):
    def test_shape_and_range(self):
        lv = audio.levels_from_pcm(tone(440, 1), 30, 30, bands=16)
        self.assertEqual(lv.shape, (30, 16))
        self.assertTrue(((lv >= 0) & (lv <= 1)).all())

    def test_pitch_moves_peak_band(self):
        low = audio.levels_from_pcm(tone(200, 1), 30, 30, bands=24)[15]
        high = audio.levels_from_pcm(tone(4000, 1), 30, 30, bands=24)[15]
        self.assertLess(low.argmax(), high.argmax())
        self.assertAlmostEqual(low.max(), 1.0, places=3)

    def test_silence_after_sound_decays(self):
        pcm = np.concatenate([tone(440, 1), np.zeros(SR * 2, np.float32)])
        lv = audio.levels_from_pcm(pcm, 90, 30, bands=16)
        peak = lv[15].argmax()
        self.assertGreater(lv[35, peak], 0.1)  # 끝나자마자 0으로 뚝 떨어지지 않고
        self.assertLess(lv[35, peak], lv[29, peak])  # 서서히 내려가서
        self.assertLess(lv[-1].max(), 0.01)  # 결국 바닥

    def test_decay_speed_same_across_fps(self):
        pcm = np.concatenate([tone(440, 1), np.zeros(SR, np.float32)])
        a = audio.levels_from_pcm(pcm, 60, 30, bands=8)
        b = audio.levels_from_pcm(pcm, 120, 60, bands=8)
        band = a[15].argmax()
        self.assertAlmostEqual(a[40, band], b[80, band], delta=0.05)  # 같은 1.33초 시점

    def test_band_edges_strictly_increase(self):
        e = audio.band_edges(48)
        self.assertEqual(len(e), 49)
        self.assertTrue((np.diff(e) > 0).all())

    def test_all_silent_is_zero(self):
        self.assertEqual(audio.levels_from_pcm(np.zeros(SR, np.float32), 10, 30, 8).max(), 0)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg 없음")
class LoadLevelsTest(unittest.TestCase):
    def test_reads_segment_from_file(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        path = os.path.join(d, "t.m4a")
        # 앞 1초 무음, 그다음 1초 소리
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                        "aevalsrc=if(gte(t\\,1)\\,0.5*sin(2*PI*440*t)\\,0):d=2", "-c:a", "aac", path],
                       check=True)
        lv = audio.load_levels(path, start=0.5, duration=1.0, fps=20, bands=8)
        self.assertEqual(lv.shape, (20, 8))
        self.assertLess(lv[2].max(), 0.1)  # 0.6초: 조용
        self.assertGreater(lv[15].max(), 0.9)  # 1.25초: 소리

    def test_missing_file(self):
        with self.assertRaises(RuntimeError):
            audio.load_levels("/nope.mp3", 0, 1, 10)


if __name__ == "__main__":
    unittest.main()
