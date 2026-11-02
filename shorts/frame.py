"""프레임 렌더러: 시각 t의 가사 화면 한 장을 Pillow 이미지로 그린다.

배경 위에 현재 줄(밝게)과 다음 줄(흐리게)을 세로 가운데 근처에 놓는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw

from .lrc import Lyrics
from .text import load_font, wrap

Color = tuple[int, int, int]


@dataclass
class Style:
    width: int = 1080
    height: int = 1920
    bg_color: Color = (16, 16, 24)
    text_color: Color = (255, 255, 255)
    next_color: Color = (150, 150, 165)
    font_path: str | None = None  # None이면 한글 폰트 자동 탐색(text.find_korean_font)
    font_size: int = 72
    next_font_size: int = 52
    line_gap: int = 48  # 현재 줄과 다음 줄 사이 간격(px)
    line_spacing: float = 1.25  # 한 가사가 여러 줄로 나뉠 때 줄 높이(글자 크기 배수)
    max_text_width: float = 0.86  # 화면 폭 대비 최대 글줄 폭
    center_y: float = 0.5  # 현재 줄의 세로 위치(0=위, 1=아래)


def cover_fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """비율을 유지하며 size를 꽉 채우도록 키운 뒤 가운데를 잘라낸다."""
    w, h = size
    scale = max(w / img.width, h / img.height)
    resized = img.resize(
        (max(w, round(img.width * scale)), max(h, round(img.height * scale))),
        Image.LANCZOS,
    )
    left = (resized.width - w) // 2
    top = (resized.height - h) // 2
    return resized.crop((left, top, left + w, top + h))


class FrameRenderer:
    def __init__(self, style: Style | None = None, background: Image.Image | None = None):
        self.style = s = style or Style()
        size = (s.width, s.height)
        if background is None:
            self._bg = Image.new("RGB", size, s.bg_color)
        else:
            self._bg = cover_fit(background.convert("RGB"), size)
        self._font = load_font(s.font_path, s.font_size)
        self._next_font = load_font(s.font_path, s.next_font_size)

    def render(self, lyrics: Lyrics, t: float) -> Image.Image:
        s = self.style
        img = self._bg.copy()
        draw = ImageDraw.Draw(img)
        cy = s.height * s.center_y
        max_w = s.width * s.max_text_width

        # 현재 줄 블록은 cy에 가운데 맞춤, 다음 줄 블록은 그 아래에 붙인다.
        bottom = cy + s.font_size / 2
        i = lyrics.index_at(t)
        if i is not None:
            rows = wrap(lyrics.lines[i].text, self._font, max_w)
            step = s.font_size * s.line_spacing
            top = cy - step * (len(rows) - 1) / 2
            self._draw_rows(draw, rows, top, step, self._font, s.text_color)
            bottom = top + step * (len(rows) - 1) + s.font_size / 2
        nxt = self._next_index(lyrics, t, i)
        if nxt is not None:
            rows = wrap(lyrics.lines[nxt].text, self._next_font, max_w)
            step = s.next_font_size * s.line_spacing
            top = bottom + s.line_gap + s.next_font_size / 2
            self._draw_rows(draw, rows, top, step, self._next_font, s.next_color)
        return img

    def _draw_rows(self, draw, rows, top, step, font, color):
        cx = self.style.width / 2
        for k, row in enumerate(rows):
            draw.text((cx, top + step * k), row, font=font, fill=color, anchor="mm")

    @staticmethod
    def _next_index(lyrics: Lyrics, t: float, current: int | None) -> int | None:
        """현재 줄 다음에 올 줄. 쉬는 구간이면 곧 나올 줄을 미리 보여준다."""
        if current is not None:
            j = current + 1
        else:
            j = next((k for k, ln in enumerate(lyrics.lines) if ln.start > t), None)
        if j is None or j >= len(lyrics.lines):
            return None
        return j
