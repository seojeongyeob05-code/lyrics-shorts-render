"""프레임 렌더러: 시각 t의 가사 화면 한 장을 Pillow 이미지로 그린다.

배경 위에 현재 줄(밝게)과 다음 줄(흐리게)을 세로 가운데 근처에 놓는다.
줄이 바뀔 때는 짧게 페이드 아웃→인 하고, 원하면 하단에 진행 바를 그린다.
단어별 타이밍이 있는 줄은 부른 글자만큼 왼쪽부터 밝게 채운다(노래방식).

구조: 가사는 투명 배경(RGBA) 레이어에 그려 캐시하고, 매 프레임 배경 위에 얹는다.
배경이 고정이고 화면이 그대로면 합성 결과도 캐시해서 다시 쓴다.
"""

from __future__ import annotations

import math
from bisect import bisect_right
import dataclasses
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter

from .lrc import Lyrics
from .text import load_font, wrap

Color = tuple[int, int, int]

# 줌 배경을 새로 계산하는 초당 횟수. 1080x1920 배경 확대 한 번에 ~20ms가 들어
# 매 프레임 하면 느리다. 기본 줌(24초 주기 8%)에서 가장자리가 초당 6px 정도 움직이므로
# 15번이면 한 번에 0.4px — 눈으로 구분되지 않는다.
ZOOM_UPDATES_PER_SEC = 15


@dataclass
class Style:
    width: int = 1080
    height: int = 1920
    bg_color: Color = (16, 16, 24)  # 배경 이미지가 없을 때 배경색(그라데이션이면 위쪽 색)
    bg_gradient: Color | None = None  # 아래쪽 색. 주면 bg_color → bg_gradient 세로 그라데이션
    bg_blur: float = 0  # 배경 이미지 흐림 반경(px). 가사가 잘 읽히게
    bg_dim: float = 0  # 배경을 검게 덮는 정도(0~1)
    bg_zoom: float = 0  # 배경을 천천히 확대했다 돌아오는 정도(0.08 = 최대 8%). 0이면 고정
    bg_zoom_period: float = 20  # 확대 → 원래 크기로 돌아오는 한 주기(초)
    bg_pan: float = 0  # 확대될 때 가로로 흘러가는 정도(-1 왼쪽 ~ 1 오른쪽)
    text_color: Color = (255, 255, 255)
    next_color: Color = (150, 150, 165)
    show_next: bool = True  # 현재 줄 아래에 다음 줄을 미리 보여줄지
    unsung_color: Color = (105, 105, 120)  # 노래방식 줄에서 아직 안 부른 글자
    stroke_width: int = 0  # 글자 테두리 두께(px). 사진 배경 위에서 읽기 좋게
    stroke_color: Color = (0, 0, 0)
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
    show_info: bool = True  # 곡 정보(LRC [ti:] 제목, [ar:] 가수)를 화면 위쪽에 표시
    info_y: float = 0.14  # 곡 정보 블록의 세로 가운데(0=위, 1=아래)
    title_size: int = 54
    artist_size: int = 38
    title_color: Color = (255, 255, 255)
    artist_color: Color = (170, 170, 185)
    cover_size: int = 420  # 앨범 아트 한 변(px). FrameRenderer(cover=...)를 줬을 때만 그림
    cover_y: float = 0.31  # 앨범 아트의 세로 가운데
    cover_shape: str = "rounded"  # rounded(둥근 사각) / circle(원) / square
    cover_radius: float = 0.08  # rounded일 때 모서리 반지름(한 변 대비)
    cover_shadow: float = 0.5  # 아래 그림자 진하기(0이면 없음)

    def scaled(self, k: float) -> Style:
        """픽셀 단위 값을 k배 한 Style(빠른 미리보기용 저해상도). 크기는 짝수로 맞춘다."""
        def px(v: int) -> int:
            return max(1, round(v * k)) if v else 0

        def even(v: int) -> int:
            return max(2, round(v * k / 2) * 2)  # H.264(yuv420p)는 가로세로가 짝수여야 한다

        return dataclasses.replace(
            self, width=even(self.width), height=even(self.height),
            font_size=px(self.font_size), next_font_size=px(self.next_font_size),
            line_gap=px(self.line_gap), stroke_width=px(self.stroke_width),
            title_size=px(self.title_size), artist_size=px(self.artist_size),
            cover_size=px(self.cover_size),
            progress_height=px(self.progress_height), progress_bottom=px(self.progress_bottom),
            bg_blur=self.bg_blur * k)


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


def make_background(s: Style, image: Image.Image | None = None) -> Image.Image:
    """Style에 맞춘 배경 한 장: 이미지(꽉 채움) 또는 단색/그라데이션, 그 위에 흐림·어둡게.

    bg_zoom이 있으면 확대해도 흐려지지 않게 (1 + bg_zoom)배 크기로 만든다.
    """
    k = 1 + max(0.0, s.bg_zoom)
    size = (round(s.width * k), round(s.height * k))
    if image is not None:
        bg = cover_fit(image.convert("RGB"), size)
    elif s.bg_gradient is not None:
        # 1px 폭 세로 띠를 만든 뒤 늘린다
        strip = Image.new("RGB", (1, size[1]))
        top, bottom = s.bg_color, s.bg_gradient
        for y in range(size[1]):
            a = y / max(1, size[1] - 1)
            strip.putpixel((0, y), tuple(round(c0 + (c1 - c0) * a) for c0, c1 in zip(top, bottom)))
        bg = strip.resize(size, Image.NEAREST)
    else:
        bg = Image.new("RGB", size, s.bg_color)
    if s.bg_blur > 0:
        bg = bg.filter(ImageFilter.GaussianBlur(s.bg_blur * k))
    if s.bg_dim > 0:
        bg = Image.blend(bg, Image.new("RGB", size, (0, 0, 0)), min(1.0, s.bg_dim))
    return bg


COVER_SHAPES = ("rounded", "circle", "square")


def make_cover_layer(s: Style, cover: Image.Image) -> Image.Image:
    """앨범 아트를 모양대로 오려 그림자와 함께 cover_y에 놓은 전체 화면 크기 RGBA 레이어."""
    if s.cover_shape not in COVER_SHAPES:
        raise ValueError(f"cover_shape는 {', '.join(COVER_SHAPES)} 중 하나여야 합니다: {s.cover_shape!r}")
    size = s.cover_size
    art = cover_fit(cover.convert("RGB"), (size, size))
    # 가장자리가 계단지지 않게 4배로 그린 마스크를 줄여 쓴다
    big = Image.new("L", (size * 4, size * 4), 0)
    d = ImageDraw.Draw(big)
    if s.cover_shape == "circle":
        d.ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    elif s.cover_shape == "rounded":
        d.rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1),
                            radius=round(size * 4 * s.cover_radius), fill=255)
    else:
        d.rectangle((0, 0, size * 4, size * 4), fill=255)
    mask = big.resize((size, size), Image.LANCZOS)

    x, y = (s.width - size) // 2, round(s.height * s.cover_y - size / 2)
    layer = Image.new("RGBA", (s.width, s.height), (0, 0, 0, 0))
    if s.cover_shadow > 0:
        shadow = Image.new("L", (s.width, s.height), 0)
        shadow.paste(mask, (x, y + round(size * 0.04)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.06))
        layer.putalpha(shadow.point(lambda v: round(v * min(1.0, s.cover_shadow))))
    layer.paste(art, (x, y), mask)
    return layer


class FrameRenderer:
    def __init__(self, style: Style | None = None, background: Image.Image | None = None,
                 cover: Image.Image | None = None):
        self.style = s = style or Style()
        self._cover = make_cover_layer(s, cover) if cover is not None else None
        self._bg = make_background(s, background)
        self._font = load_font(s.font_path, s.font_size)
        self._next_font = load_font(s.font_path, s.next_font_size)
        self._title_font = load_font(s.font_path, s.title_size)
        self._artist_font = load_font(s.font_path, s.artist_size)
        # 앨범 아트 + 곡 정보 레이어(RGBA). 가사와 따로, 페이드 없이 얹는다
        self._overlay: Image.Image | None = self._cover
        self._cache: dict[tuple, Image.Image] = {}  # 가사 레이어(RGBA)
        self._cache_owner: Lyrics | None = None
        self._bounds: list[float] = []
        self._static: tuple[Image.Image, Image.Image] | None = None  # (레이어, 배경과 합성)
        self._zoomed: tuple[float, Image.Image] | None = None  # 마지막으로 계산한 줌 배경
        self._bytes_of: Image.Image | None = None  # render_bytes가 바이트로 바꿔 둔 화면
        self._bytes = b""
        self.layers_drawn = 0  # 실제로 새로 그린 가사 레이어 수(성능 확인용)

    def render(self, lyrics: Lyrics, t: float, progress: float | None = None) -> Image.Image:
        """시각 t의 화면. progress(0~1)를 주면 진행 바도 그린다."""
        img, shared = self._frame(lyrics, t)
        if shared:
            img = img.copy()  # 캐시된 화면 위에 진행 바를 그리지 않도록
        if progress is not None and self.style.progress_bar:
            self._draw_progress(img, progress)
        return img

    def render_bytes(self, lyrics: Lyrics, t: float, progress: float | None = None) -> bytes:
        """render(...).tobytes()와 같은 결과. 영상 인코딩용 빠른 경로.

        화면이 그대로인 구간(페이드·노래방 진행·배경 줌 없음)은 화면 바이트를 한 번만
        만들어 두고 진행 바 줄만 덮어쓴다. 1080x1920 한 장을 바이트로 바꾸는 데 4~5ms가
        들어서 대부분의 프레임에서 이 비용을 없앤다.
        """
        s = self.style
        img, shared = self._frame(lyrics, t)
        draw_bar = progress is not None and s.progress_bar
        if not shared:
            if draw_bar:
                self._draw_progress(img, progress)
            return img.tobytes()
        if self._bytes_of is not img:
            self._bytes_of, self._bytes = img, img.tobytes()
        if not draw_bar:
            return self._bytes
        buf = bytearray(self._bytes)
        x0, y0, w, h, filled = self._progress_geometry(progress)
        track, bar = bytes(s.progress_track) * w, bytes(s.progress_color) * filled
        for y in range(y0, y0 + h):
            off = (y * s.width + x0) * 3
            buf[off:off + 3 * w] = track
            buf[off:off + 3 * filled] = bar
        return bytes(buf)

    def background_at(self, t: float) -> Image.Image:
        """시각 t의 배경(돌려받은 이미지를 고치지 말 것)."""
        s = self.style
        if s.bg_zoom <= 0:
            return self._bg
        t = round(t * ZOOM_UPDATES_PER_SEC) / ZOOM_UPDATES_PER_SEC
        if self._zoomed is not None and self._zoomed[0] == t:
            return self._zoomed[1]
        # 0 → 1 → 0으로 부드럽게 오가는 위상: 확대했다가 원래 크기로 돌아온다
        phase = 0.5 - 0.5 * math.cos(2 * math.pi * t / s.bg_zoom_period)
        scale = 1 + s.bg_zoom * phase
        bw, bh = self._bg.size
        w, h = bw / scale, bh / scale
        cx = bw / 2 + max(-1.0, min(1.0, s.bg_pan)) * (bw - w) / 2
        cy = bh / 2
        bg = self._bg.resize((s.width, s.height), Image.BILINEAR,
                             box=(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
        self._zoomed = (t, bg)
        return bg

    def state_key(self, lyrics: Lyrics, t: float) -> tuple[int | None, int | None]:
        """화면의 가사 내용을 결정하는 값: (현재 줄, 다음 줄) 인덱스."""
        i = lyrics.index_at(t)
        return i, (self._next_index(lyrics, t, i) if self.style.show_next else None)

    def _frame(self, lyrics: Lyrics, t: float) -> tuple[Image.Image, bool]:
        """진행 바를 뺀 시각 t의 화면과, 그 이미지가 캐시와 공유되는지(고치면 안 되는지)."""
        s = self.style
        layer = self._text_layer(lyrics, self.state_key(lyrics, t), t)
        alpha = 1.0
        tc = self._last_change(lyrics, t)
        if s.fade > 0 and tc is not None and t - tc < s.fade:
            # 같은 자리에 글자가 겹쳐 보이지 않도록 앞 절반은 이전 가사가 사라지고,
            # 뒤 절반은 새 가사가 나타난다.
            a = (t - tc) / s.fade
            if a < 0.5:
                layer = self._text_layer(lyrics, self.state_key(lyrics, tc - 1e-6), tc - 1e-6)
                alpha = 1 - a * 2
            else:
                alpha = a * 2 - 1
        if alpha == 1.0 and s.bg_zoom <= 0 and self._is_cached(layer):
            if self._static is None or self._static[0] is not layer:
                self._static = (layer, self._composite(self._bg, layer, 1.0))
            return self._static[1], True
        return self._composite(self.background_at(t), layer, alpha), False

    def _composite(self, bg: Image.Image, layer: Image.Image, alpha: float) -> Image.Image:
        """배경 위에 가사 레이어를 alpha(0~1) 불투명도로, 앨범 아트·곡 정보는 그대로 얹은 새 이미지."""
        out = bg.copy()
        self._paste(out, layer, alpha)
        if self._overlay is not None:
            self._paste(out, self._overlay, 1.0)
        return out

    @staticmethod
    def _paste(out: Image.Image, layer: Image.Image, alpha: float) -> None:
        bbox = layer.getbbox()  # 글자가 있는 영역만 합성
        if bbox and alpha > 0:
            part = layer.crop(bbox)
            mask = part.getchannel("A")
            if alpha < 1:
                mask = mask.point(lambda v: round(v * alpha))
            out.paste(part, bbox[:2], mask)

    def _draw_info(self, meta: dict[str, str]) -> Image.Image | None:
        """곡 제목(굵게)과 가수를 info_y 근처에 가운데 정렬로 그린 레이어. 둘 다 없으면 None."""
        s = self.style
        blocks = [(text, font, size, color) for text, font, size, color in (
            (meta.get("ti", "").strip(), self._title_font, s.title_size, s.title_color),
            (meta.get("ar", "").strip(), self._artist_font, s.artist_size, s.artist_color),
        ) if text]
        if not s.show_info or not blocks:
            return None
        rows = [(row, font, size, color)
                for text, font, size, color in blocks
                for row in wrap(text, font, s.width * s.max_text_width)]
        heights = [size * s.line_spacing for _, _, size, _ in rows]
        y = s.height * s.info_y - sum(heights) / 2
        img = Image.new("RGBA", (s.width, s.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for (row, font, size, color), h in zip(rows, heights):
            draw.text((s.width / 2, y + h / 2), row, font=font, fill=color, anchor="mm",
                      stroke_width=s.stroke_width, stroke_fill=s.stroke_color)
            y += h
        return img

    def _use(self, lyrics: Lyrics) -> None:
        """다른 가사가 들어오면 캐시를 비운다."""
        if self._cache_owner is not lyrics:
            self._cache.clear()
            self._static = None
            self._cache_owner = lyrics
            info = self._draw_info(lyrics.meta)
            if self._cover is not None and info is not None:
                self._overlay = Image.alpha_composite(self._cover, info)
            else:
                self._overlay = info if info is not None else self._cover
            self._bounds = sorted({x for ln in lyrics.lines for x in (ln.start, ln.end)})

    def _text_layer(self, lyrics: Lyrics, key: tuple[int | None, int | None],
                    t: float) -> Image.Image:
        """시각 t에 보일 가사 레이어(RGBA, 투명 배경). 돌려받은 이미지를 고치지 말 것."""
        i = key[0]
        if i is None or not lyrics.lines[i].marks:
            return self._layer(lyrics, key, color=self.style.text_color)
        # 노래방식: 안 부른 색 레이어와 부른 색 레이어를 진행 정도만큼 섞는다
        unsung = self._layer(lyrics, key, color=self.style.unsung_color)
        sung = self._layer(lyrics, key, color=self.style.text_color)
        line = lyrics.lines[i]
        done = line.sung_chars(t)
        if done >= len(line.text):
            return sung
        rows = self._current_rows(line.text)
        h = self.style.font_size * 0.75
        # 글자가 있는 띠만 합성한다(전체 화면을 섞으면 느리다)
        band = (0, max(0, int(rows[0][3] - h)), unsung.width,
                min(unsung.height, int(rows[-1][3] + h) + 1))
        mask = Image.new("L", (band[2], band[3] - band[1]), 0)
        draw = ImageDraw.Draw(mask)
        for row, offset, x0, y in rows:
            n = min(max(done - offset, 0.0), len(row))
            if n <= 0:
                break
            whole = int(n)
            px = self._font.getlength(row[:whole])
            if whole < len(row):
                px += (n - whole) * self._font.getlength(row[whole])
            draw.rectangle((0, y - h - band[1], x0 + px, y + h - band[1]), fill=255)
        img = unsung.copy()
        img.paste(sung.crop(band), band[:2], mask)
        return img

    def _is_cached(self, img: Image.Image) -> bool:
        return any(img is v for v in self._cache.values())

    def _layer(self, lyrics: Lyrics, key: tuple[int | None, int | None],
               color: Color) -> Image.Image:
        """현재 줄을 color로 그린 가사 레이어. 같은 키는 다시 그리지 않는다."""
        self._use(lyrics)
        ck = (key, color)
        if ck not in self._cache:
            if len(self._cache) >= 8:
                self._cache.pop(next(iter(self._cache)))
            self._cache[ck] = self._draw_lyrics(lyrics, *key, color)
            self.layers_drawn += 1
        return self._cache[ck]

    def _current_rows(self, text: str) -> list[tuple[str, int, float, float]]:
        """현재 줄을 줄바꿈한 결과: (글줄, text 안 시작 위치, 왼쪽 x, 가운데 y)."""
        s = self.style
        rows = wrap(text, self._font, s.width * s.max_text_width)
        step = s.font_size * s.line_spacing
        top = s.height * s.center_y - step * (len(rows) - 1) / 2
        out = []
        offset = 0
        for k, row in enumerate(rows):
            offset = text.index(row, offset)
            out.append((row, offset, (s.width - self._font.getlength(row)) / 2, top + step * k))
            offset += len(row)
        return out

    def _last_change(self, lyrics: Lyrics, t: float) -> float | None:
        """t 이전에 화면 내용이 마지막으로 바뀐 시각(줄 시작/끝)."""
        self._use(lyrics)
        k = bisect_right(self._bounds, t) - 1
        return self._bounds[k] if k >= 0 else None

    def _draw_lyrics(self, lyrics: Lyrics, i: int | None, nxt: int | None,
                     color: Color) -> Image.Image:
        s = self.style
        img = Image.new("RGBA", (s.width, s.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        stroke = {"stroke_width": s.stroke_width, "stroke_fill": s.stroke_color}

        # 현재 줄 블록은 center_y에 가운데 맞춤, 다음 줄 블록은 그 아래에 붙인다.
        bottom = s.height * s.center_y + s.font_size / 2
        if i is not None:
            rows = self._current_rows(lyrics.lines[i].text)
            for row, _, _, y in rows:
                draw.text((s.width / 2, y), row, font=self._font, fill=color, anchor="mm",
                          **stroke)
            bottom = rows[-1][3] + s.font_size / 2
        if nxt is not None:
            rows = wrap(lyrics.lines[nxt].text, self._next_font, s.width * s.max_text_width)
            step = s.next_font_size * s.line_spacing
            top = bottom + s.line_gap + s.next_font_size / 2
            for k, row in enumerate(rows):
                draw.text((s.width / 2, top + step * k), row, font=self._next_font,
                          fill=s.next_color, anchor="mm", **stroke)
        return img

    def _progress_geometry(self, progress: float) -> tuple[int, int, int, int, int]:
        """진행 바의 (왼쪽 x, 위 y, 폭, 높이, 채운 폭)."""
        s = self.style
        w = round(s.width * s.progress_width)
        filled = round(w * min(1.0, max(0.0, progress)))
        return (s.width - w) // 2, s.height - s.progress_bottom - s.progress_height, \
            w, s.progress_height, filled

    def _draw_progress(self, img: Image.Image, progress: float) -> None:
        s = self.style
        x0, y0, w, h, filled = self._progress_geometry(progress)
        draw = ImageDraw.Draw(img)
        draw.rectangle((x0, y0, x0 + w - 1, y0 + h - 1), fill=s.progress_track)
        if filled:
            draw.rectangle((x0, y0, x0 + filled - 1, y0 + h - 1), fill=s.progress_color)

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
