import importlib.util
import os
import unittest

from PIL import Image

from shorts.styles import list_presets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("gallery", os.path.join(ROOT, "tools", "gallery.py"))
gallery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gallery)


class GalleryTest(unittest.TestCase):
    def test_tiles_and_labels(self):
        sheet = gallery.make_gallery(["default", "minimal", "neon"], thumb=(54, 96), cols=2)
        self.assertEqual(sheet.size, (2 * 54, 2 * (96 + 44)))
        # minimal(흰 배경)은 두 번째 칸, 이름표 아래
        self.assertGreater(sheet.getpixel((54 + 27, 44 + 48))[0], 200)
        # 마지막 줄의 빈 칸은 바탕색 그대로
        self.assertEqual(sheet.getpixel((54 + 27, 140 + 44 + 48)), (18, 18, 22))

    def test_committed_gallery_covers_every_preset(self):
        path = os.path.join(ROOT, "docs", "gallery.jpg")
        rows = (len(list_presets()) + 3) // 4
        with Image.open(path) as img:
            self.assertEqual(img.size, (4 * 270, rows * (480 + 44)),
                             "스타일이 바뀌었으면 python3 tools/gallery.py 로 다시 만드세요")

    def test_readme_shows_gallery(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            self.assertIn("](docs/gallery.jpg)", f.read())


if __name__ == "__main__":
    unittest.main()
