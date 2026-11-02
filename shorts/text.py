"""글꼴 찾기와 줄바꿈."""

from __future__ import annotations

import os
import shutil
import subprocess

from PIL import ImageFont

FONT_ENV = "SHORTS_FONT"

# fc-list가 없을 때 살펴볼 흔한 한글 폰트 위치
_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
]


# 자막용으로 보기 좋은 순서. 목록에 없는 폰트(unifont 같은 비트맵 폰트 포함)는 뒤로.
_PREFERRED = ["nanum", "notosanscjk", "notosanskr", "sourcehansans", "malgun",
              "applesdgothic", "wqy-zenhei"]


def _rank(path: str) -> tuple[int, bool, str]:
    name = os.path.basename(path).lower().replace(" ", "")
    pref = next((i for i, key in enumerate(_PREFERRED) if key in name), len(_PREFERRED))
    # 같은 계열이면 굵은 글꼴이 쇼츠 자막에 더 잘 읽힌다
    return pref, "bold" not in name, path


def find_korean_font() -> str | None:
    """한글을 그릴 수 있는 폰트 파일 경로. 환경변수 SHORTS_FONT가 우선."""
    env = os.environ.get(FONT_ENV)
    if env:
        if not os.path.isfile(env):
            raise FileNotFoundError(f"{FONT_ENV}={env} 파일이 없습니다")
        return env
    if shutil.which("fc-list"):
        out = subprocess.run(["fc-list", ":lang=ko", "file"],
                             capture_output=True, text=True).stdout
        files = [line.strip().rstrip(":") for line in out.splitlines() if line.strip()]
        if files:
            return min(files, key=_rank)
    return next((p for p in _CANDIDATES if os.path.isfile(p)), None)


def load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    """path가 없으면 한글 폰트를 찾아보고, 그래도 없으면 Pillow 기본 폰트."""
    path = path or find_korean_font()
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def wrap(text: str, font: ImageFont.FreeTypeFont, max_width: float) -> list[str]:
    """max_width(px)를 넘지 않게 줄을 나눈다.

    단어(공백) 단위로 채우고, 한 단어가 폭보다 길면 글자 단위로 자른다.
    """
    width = font.getlength
    lines: list[str] = []
    cur = ""
    for word in text.split():
        cand = f"{cur} {word}" if cur else word
        if width(cand) <= max_width:
            cur = cand
            continue
        if cur:
            lines.append(cur)
            cur = ""
        while width(word) > max_width:
            n = 1
            while n < len(word) and width(word[:n + 1]) <= max_width:
                n += 1
            lines.append(word[:n])
            word = word[n:]
        cur = word
    if cur:
        lines.append(cur)
    return lines
