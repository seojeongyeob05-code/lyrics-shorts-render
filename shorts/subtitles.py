"""가사를 다른 편집기·유튜브에서 쓰는 자막 파일로 내보낸다.

- SRT: 줄마다 시작·끝 시각과 글자. 거의 모든 곳에서 읽힌다.
- ASS: 화면 크기·글꼴·색·위치까지 담고, 단어 타이밍이 있는 줄은 노래방 효과(\\kf)로.
"""

from __future__ import annotations

from .frame import Style
from .lrc import Lyrics, LyricLine


def _srt_time(sec: float) -> str:
    ms = max(0, round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def to_srt(lyrics: Lyrics) -> str:
    blocks = [f"{n}\n{_srt_time(ln.start)} --> {_srt_time(ln.end)}\n{ln.text}\n"
              for n, ln in enumerate(lyrics.lines, 1)]
    return "\n".join(blocks)


def _ass_time(sec: float) -> str:
    cs = max(0, round(sec * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def _ass_color(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"&H00{b:02X}{g:02X}{r:02X}"  # ASS는 알파·파랑·초록·빨강 순서


def _ass_escape(text: str) -> str:
    # 중괄호는 ASS에서 효과 태그, 역슬래시는 줄바꿈 등 특수 문자
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def karaoke_text(line: LyricLine) -> str:
    """단어 타이밍을 ASS \\kf(왼쪽부터 채우기) 태그로. 타이밍이 없으면 글자 그대로."""
    if not line.marks:
        return _ass_escape(line.text)
    pts = list(line.marks)
    if pts[-1][1] < len(line.text):
        pts.append((line.end, len(line.text)))
    parts = []
    if pts[0][0] > line.start:  # 줄은 떴지만 첫 단어 전까지 쉬는 시간
        parts.append(f"{{\\k{round((pts[0][0] - line.start) * 100)}}}")
    prefix = line.text[:pts[0][1]]
    if prefix:
        parts.append(_ass_escape(prefix))
    for (t0, c0), (t1, c1) in zip(pts, pts[1:]):
        parts.append(f"{{\\kf{max(0, round((t1 - t0) * 100))}}}{_ass_escape(line.text[c0:c1])}")
    return "".join(parts)


def to_ass(lyrics: Lyrics, style: Style | None = None, font_name: str = "Noto Sans CJK KR") -> str:
    """현재 줄을 화면 가운데(center_y)에 두는 ASS 자막. 노래방 줄은 unsung → text 색으로 채움."""
    s = style or Style()
    margin_v = round(s.height * (1 - s.center_y) - s.font_size / 2)  # 아래 정렬 기준 여백
    margin_h = round(s.width * (1 - s.max_text_width) / 2)
    title = lyrics.meta.get("ti", "")
    head = [
        "[Script Info]",
        f"Title: {title}" if title else "Title: lyrics",
        "ScriptType: v4.00+",
        f"PlayResX: {s.width}",
        f"PlayResY: {s.height}",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # PrimaryColour = 부른 글자, SecondaryColour = 아직 안 부른 글자(\kf가 채우는 색)
        f"Style: Default,{font_name},{s.font_size},{_ass_color(s.text_color)},"
        f"{_ass_color(s.unsung_color)},{_ass_color(s.stroke_color)},&H80000000,"
        f"0,0,0,0,100,100,0,0,1,{s.stroke_width},0,2,{margin_h},{margin_h},{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    events = [f"Dialogue: 0,{_ass_time(ln.start)},{_ass_time(ln.end)},Default,,0,0,0,,"
              f"{karaoke_text(ln)}" for ln in lyrics.lines]
    return "\n".join(head + events) + "\n"
