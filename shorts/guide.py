"""쇼츠 앱 UI가 화면을 덮는 자리.

유튜브 쇼츠·릴스·틱톡 모두 위쪽 메뉴, 오른쪽 버튼 줄(좋아요·댓글·공유), 아래쪽
제목·채널·설명이 영상 위에 겹친다. 위치는 기기·앱 버전마다 조금씩 달라서
여기 값은 1080x1920 기준으로 넉넉하게 잡은 대략적인 영역이다.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from .text import load_font

# (이름, (왼쪽, 위, 오른쪽, 아래)) — 화면 크기 대비 비율
ZONES: list[tuple[str, tuple[float, float, float, float]]] = [
    ("위쪽 메뉴", (0.0, 0.0, 1.0, 0.075)),
    ("오른쪽 버튼", (0.85, 0.42, 1.0, 1.0)),
    ("아래쪽 제목·설명", (0.0, 0.80, 0.85, 1.0)),
]

Box = tuple[int, int, int, int]


def zone_boxes(width: int, height: int) -> list[tuple[str, Box]]:
    return [(name, (round(x0 * width), round(y0 * height), round(x1 * width), round(y1 * height)))
            for name, (x0, y0, x1, y1) in ZONES]


def overlaps(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def find_overlaps(renderer, lyrics, times) -> list[tuple[str, str, float]]:
    """times 중 렌더한 내용이 가림 영역에 걸리는 경우: [(내용, 영역, 처음 걸린 시각), ...]."""
    s = renderer.style
    zones = zone_boxes(s.width, s.height)
    found: dict[tuple[str, str], float] = {}
    for t in times:
        for content, box in renderer.content_boxes(lyrics, t):
            for zone, zbox in zones:
                if overlaps(box, zbox):
                    found.setdefault((content, zone), t)
    return [(c, z, t) for (c, z), t in found.items()]


def draw_guide(img: Image.Image) -> Image.Image:
    """가림 영역을 반투명 빨강으로 덮고 이름을 적은 새 이미지."""
    out = img.convert("RGBA")
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for name, box in zone_boxes(*out.size):
        draw.rectangle(box, fill=(255, 40, 60, 80), outline=(255, 40, 60, 200), width=3)
        # 좁은 영역(오른쪽 버튼 줄)에도 이름이 들어가게 글자 크기를 줄인다
        size = max(12, out.width // 36)
        font = load_font(None, size)
        while size > 10 and font.getlength(name) > box[2] - box[0] - 16:
            size -= 2
            font = load_font(None, size)
        draw.text((box[0] + 8, box[1] + 10), name, font=font, fill=(255, 255, 255, 230),
                  stroke_width=2, stroke_fill=(0, 0, 0, 200))
    return Image.alpha_composite(out, layer).convert("RGB")
