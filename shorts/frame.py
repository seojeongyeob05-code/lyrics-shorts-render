"""프레임 렌더러: 시각 t의 가사 화면 한 장을 Pillow 이미지로 그린다.

배경 위에 현재 줄(밝게)과 다음 줄(흐리게)을 세로 가운데 근처에 놓는다.
줄이 바뀔 때는 짧게 페이드 아웃→인 하고, 원하면 하단에 진행 바를 그린다.
"""

from __future__ import annotations

from bisect import bisect_right
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
    fade: float = 0.24  # 화면이 바뀔 때 페이드 아웃→인 전체 시간(초). 0이면 끔
    progress_bar: bool = True  # render(..., progress=)를 받으면 하단 진행 바를 그림
    progress_color: Color = (255, 255, 255)
    progress_track: Color = (70, 70, 84)
    progress_height: int = 8
    progress_width: float = 0.7  # 화면 폭 대비
    progress_bottom: int = 160  # 화면 아래 끝에서 띄울 거리(px)


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
        self._cache: dict[tuple[int | None, int | None], Image.Image] = {}
        self._cache_owner: Lyrics | None = None
        self._bounds: list[float] = []
        self.layers_drawn = 0  # 실제로 새로 그린 가사 화면 수(성능 확인용)

    def render(self, lyrics: Lyrics, t: float, progress: float | None = None) -> Image.Image:
        """시각 t의 화면. progress(0~1)를 주면 진행 바도 그린다."""
        s = self.style
        cur = self._layer(lyrics, self.state_key(lyrics, t))
        tc = self._last_change(lyrics, t)
        if s.fade > 0 and tc is not None and t - tc < s.fade:
            # 같은 자리에 글자가 겹쳐 보이지 않도록 앞 절반은 이전 화면이 배경으로
            # 사라지고, 뒤 절반은 배경에서 새 화면이 나타난다.
            a = (t - tc) / s.fade
            if a < 0.5:
                prev = self._layer(lyrics, self.state_key(lyrics, tc - 1e-6))
                img = Image.blend(prev, self._bg, a * 2)
            else:
                img = Image.blend(self._bg, cur, a * 2 - 1)
        else:
            img = cur.copy()
        if progress is not None and s.progress_bar:
            self._draw_progress(img, progress)
        return img

    def state_key(self, lyrics: Lyrics, t: float) -> tuple[int | None, int | None]:
        """화면의 가사 내용을 결정하는 값: (현재 줄, 다음 줄) 인덱스."""
        i = lyrics.index_at(t)
        return i, self._next_index(lyrics, t, i)

    def _use(self, lyrics: Lyrics) -> None:
        """다른 가사가 들어오면 캐시를 비운다."""
        if self._cache_owner is not lyrics:
            self._cache.clear()
            self._cache_owner = lyrics
            self._bounds = sorted({x for ln in lyrics.lines for x in (ln.start, ln.end)})

    def _layer(self, lyrics: Lyrics, key: tuple[int | None, int | None]) -> Image.Image:
        """페이드·진행 바 없이 가사만 그린 화면. 같은 키는 다시 그리지 않는다."""
        self._use(lyrics)
        if key not in self._cache:
            if len(self._cache) >= 8:
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = self._draw_lyrics(lyrics, *key)
            self.layers_drawn += 1
        return self._cache[key]

    def _last_change(self, lyrics: Lyrics, t: float) -> float | None:
        """t 이전에 화면 내용이 마지막으로 바뀐 시각(줄 시작/끝)."""
        self._use(lyrics)
        k = bisect_right(self._bounds, t) - 1
        return self._bounds[k] if k >= 0 else None

    def _draw_lyrics(self, lyrics: Lyrics, i: int | None, nxt: int | None) -> Image.Image:
        s = self.style
        img = self._bg.copy()
        draw = ImageDraw.Draw(img)
        cy = s.height * s.center_y
        max_w = s.width * s.max_text_width

        # 현재 줄 블록은 cy에 가운데 맞춤, 다음 줄 블록은 그 아래에 붙인다.
        bottom = cy + s.font_size / 2
        if i is not None:
            rows = wrap(lyrics.lines[i].text, self._font, max_w)
            step = s.font_size * s.line_spacing
            top = cy - step * (len(rows) - 1) / 2
            self._draw_rows(draw, rows, top, step, self._font, s.text_color)
            bottom = top + step * (len(rows) - 1) + s.font_size / 2
        if nxt is not None:
            rows = wrap(lyrics.lines[nxt].text, self._next_font, max_w)
            step = s.next_font_size * s.line_spacing
            top = bottom + s.line_gap + s.next_font_size / 2
            self._draw_rows(draw, rows, top, step, self._next_font, s.next_color)
        return img

    def _draw_progress(self, img: Image.Image, progress: float) -> None:
        s = self.style
        w = round(s.width * s.progress_width)
        x0 = (s.width - w) // 2
        y1 = s.height - s.progress_bottom
        y0 = y1 - s.progress_height
        draw = ImageDraw.Draw(img)
        draw.rectangle((x0, y0, x0 + w - 1, y1 - 1), fill=s.progress_track)
        filled = round(w * min(1.0, max(0.0, progress)))
        if filled:
            draw.rectangle((x0, y0, x0 + filled - 1, y1 - 1), fill=s.progress_color)

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
