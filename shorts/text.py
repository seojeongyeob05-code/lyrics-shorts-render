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


# 줄 첫머리에 오면 어색한 글자(작은 가나·장음·닫는 괄호·문장부호)와 줄 끝에 오면 어색한 여는 괄호
_NO_START = set("っゃゅょぁぃぅぇぉゎッャュョァィゥェォヮヵヶーゝゞ、。，．・：；？！?!…‥」』）)】〉》")
_NO_END = set("「『（(【〈《")


def wrap(text: str, font: ImageFont.FreeTypeFont, max_width: float,
         balance: bool = True) -> list[str]:
    """max_width(px)를 넘지 않게 줄을 나눈다.

    단어(공백) 단위로 채우고, 한 단어가 폭보다 길면(띄어쓰기 없는 일본어·중국어 등) 글자 단위로
    자른다. balance면 줄 수는 그대로 두고 줄 길이를 고르게 맞춘다(앞줄만 꽉 차고 끝줄에 한두 글자
    남는 것을 막음).
    """
    if balance and any(_char_class(c) in ("hira", "kata", "kanji") for c in text):
        return _cjk_wrap(" ".join(text.split()), font, max_width)
    rows = _greedy(text, font, max_width)
    if not balance or len(rows) < 2:
        return rows
    # 같은 줄 수가 나오는 가장 좁은 폭을 찾는다
    lo, hi = max(font.getlength(r) for r in rows) / len(rows), max_width
    for _ in range(12):
        mid = (lo + hi) / 2
        if len(_greedy(text, font, mid)) <= len(rows):
            hi = mid
        else:
            lo = mid
    return _nicer_breaks(text, _greedy(text, font, hi), font, max_width)


def _char_class(c: str) -> str:
    o = ord(c)
    if 0x3040 <= o <= 0x309F:
        return "hira"
    if 0x30A0 <= o <= 0x30FF:
        return "kata"
    if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
        return "kanji"
    if c.isascii() and c.isalnum():
        return "latin"
    return "other"


def _good_break(a: str, b: str) -> bool:
    """a|b에서 끊기 좋은가: 글자 종류(히라가나·가타카나·한자·영문)가 바뀌는 자리."""
    return (a and b and b[0] not in _NO_START and a[-1] not in _NO_END
            and _char_class(a[-1]) != _char_class(b[0]))


def _nicer_breaks(text: str, rows: list[str], font, max_width: float) -> list[str]:
    """띄어쓰기 없이 단어 중간에서 끊긴 자리를 앞뒤 3글자 안의 '글자 종류가 바뀌는 자리'로 옮긴다
    (예: 失っちゃいけな|いモノ → 失っちゃいけない|モノ). 폭을 넘거나 좋은 자리가 없으면 그대로."""
    rows = list(rows)
    pos = 0
    for i in range(len(rows) - 1):
        pos = text.index(rows[i], pos) + len(rows[i])
        a, b = rows[i], rows[i + 1]
        if text[pos:pos + 1].isspace() or _good_break(a, b):
            continue  # 띄어쓰기에서 끊겼거나 이미 좋은 자리
        joined = a + b
        for d in (1, -1, 2, -2, 3, -3):
            k = len(a) + d
            na, nb = joined[:k], joined[k:]
            if (0 < k < len(joined) and _good_break(na, nb)
                    and font.getlength(na) <= max_width and font.getlength(nb) <= max_width):
                rows[i], rows[i + 1] = na, nb
                pos += d
                break
    return rows


def _cjk_wrap(text: str, font, max_width: float) -> list[str]:
    """일본어·중국어처럼 띄어쓰기가 적은 글: 아무 글자 사이에서나 끊을 수 있으니, 줄 길이가 고르게
    되는 자리 근처(±4글자)에서 띄어쓰기 > 글자 종류가 바뀌는 자리 > 그 밖 순으로 고른다."""
    width = font.getlength
    if not text or width(text) <= max_width:
        return [text] if text else []
    n = 2
    while n <= len(text):
        cuts, prev = [], 0
        for k in range(1, n):
            goal = width(text) * k / n
            target = next((i for i in range(prev + 1, len(text)) if width(text[:i]) >= goal),
                          len(text) - 1)
            best, best_score = None, None
            for i in range(max(prev + 1, target - 4), min(len(text), target + 5)):
                a, b = text[:i].rstrip(), text[i:].lstrip()
                if not a or not b or b[0] in _NO_START or a[-1] in _NO_END:
                    continue
                score = -abs(i - target) * 0.6
                if text[i - 1] == " " or text[i] == " ":
                    score += 4
                elif a[-1] in "」』）)】":  # 닫는 괄호 바로 뒤
                    score += 3
                elif _char_class(a[-1]) != _char_class(b[0]):
                    score += 2
                if best_score is None or score > best_score:
                    best, best_score = i, score
            cuts.append(best if best is not None else target)
            prev = cuts[-1]
        rows = [text[a:b].strip() for a, b in zip([0] + cuts, cuts + [len(text)])]
        rows = [r for r in rows if r]
        if all(width(r) <= max_width for r in rows):
            return rows
        n += 1
    return _greedy(text, font, max_width)


def _greedy(text: str, font: ImageFont.FreeTypeFont, max_width: float) -> list[str]:
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
            # 금칙: 다음 줄이 작은 가나·부호로 시작하거나 이 줄이 여는 괄호로 끝나면 한 글자 당김
            while n > 1 and (word[n] in _NO_START or word[n - 1] in _NO_END):
                n -= 1
            lines.append(word[:n])
            word = word[n:]
        cur = word
    if cur:
        lines.append(cur)
    return lines
