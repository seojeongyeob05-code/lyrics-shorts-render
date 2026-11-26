"""내장 스타일을 한 장면씩 그려 한 장에 모은 미리보기(README용).

    python3 tools/gallery.py [-o docs/gallery.jpg] [--font 폰트.ttf]

예시 곡(examples/demo)의 노래방 줄이 반쯤 불린 순간을, 스타일마다 같은 가짜 배경 사진·앨범 아트로
그린다(배경 사진을 쓰는 스타일만 사진을 씀). 스타일을 추가하면 이 스크립트를 다시 돌리면 된다.
"""

from __future__ import annotations

import argparse
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from shorts import lrc  # noqa: E402
from shorts.frame import FrameRenderer  # noqa: E402
from shorts.styles import list_presets, load_style  # noqa: E402
from shorts.text import load_font  # noqa: E402

DEMO = os.path.join(ROOT, "examples", "demo", "demo.lrc")
PHOTO_STYLES = {"photo", "modern"}  # 배경 사진·앨범 아트와 함께 쓰라고 만든 스타일


def sample_photo(seed: int = 5, size: tuple[int, int] = (1200, 2000)) -> Image.Image:
    """밤하늘 보케 느낌의 가짜 사진(저작권 걱정 없는 그림)."""
    rnd = random.Random(seed)
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(size[1]):
        a = y / size[1]
        d.line((0, y, size[0], y), fill=(int(20 + 60 * a), int(30 + 70 * a), int(70 + 90 * (1 - a))))
    for _ in range(50):
        x, y, r = rnd.randint(0, size[0]), rnd.randint(0, size[1]), rnd.randint(40, 220)
        c = rnd.choice([(255, 170, 120), (120, 180, 255), (255, 220, 160), (170, 140, 255)])
        blob = Image.new("L", size, 0)
        ImageDraw.Draw(blob).ellipse((x - r, y - r, x + r, y + r), fill=rnd.randint(40, 110))
        img = Image.composite(Image.new("RGB", size, c), img, blob)
    return img.filter(ImageFilter.GaussianBlur(6))


def make_gallery(names: list[str], at: float = 1.6, font: str | None = None,
                 thumb: tuple[int, int] = (270, 480), cols: int = 4) -> Image.Image:
    lyrics = lrc.load(DEMO)
    photo = sample_photo()
    cover = photo.crop((300, 500, 900, 1100))
    label_h = 44
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb[0], rows * (thumb[1] + label_h)), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)
    label_font = load_font(font, 24)
    for k, name in enumerate(names):
        style = load_style(name)
        if font:
            style.font_path = font
        use_photo = name in PHOTO_STYLES
        renderer = FrameRenderer(style, background=photo if use_photo else None,
                                 cover=cover if use_photo else None)
        frame = renderer.render(lyrics, at, progress=0.35)
        x, y = (k % cols) * thumb[0], (k // cols) * (thumb[1] + label_h)
        sheet.paste(frame.resize(thumb, Image.LANCZOS), (x, y + label_h))
        draw.text((x + thumb[0] / 2, y + label_h / 2), name, font=label_font,
                  fill=(235, 235, 240), anchor="mm")
    return sheet


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "docs", "gallery.jpg"))
    ap.add_argument("--font", help="모든 스타일에 쓸 폰트(없으면 자동 탐색)")
    ap.add_argument("--at", type=float, default=1.6, help="그릴 시각(초)")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    make_gallery(list_presets(), args.at, args.font).save(args.out, quality=88)
    print(args.out)


if __name__ == "__main__":
    main()
