"""LRC 가사 파일 파서.

지원 형식:
    [ti:제목] [ar:가수] 같은 메타 태그
    [00:12.34]가사          (분:초.소수)
    [00:12.34][01:02.00]후렴 (한 줄에 여러 타임스탬프)
    [offset:+200]           (밀리초, 양수면 가사가 앞당겨짐)
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field

_TIME_TAG = re.compile(r"\[(\d+):(\d{1,2})(?:[.:](\d{1,3}))?\]")
_META_TAG = re.compile(r"^\[([a-zA-Z]+):(.*)\]$")


@dataclass(frozen=True)
class LyricLine:
    start: float  # 초
    end: float  # 초 (다음 줄 시작 또는 곡 끝)
    text: str


@dataclass
class Lyrics:
    lines: list[LyricLine]
    meta: dict[str, str] = field(default_factory=dict)

    def index_at(self, t: float) -> int | None:
        """시각 t에 표시 중인 줄의 인덱스. 없으면 None."""
        i = bisect_right([ln.start for ln in self.lines], t) - 1
        if i < 0 or t >= self.lines[i].end:
            return None
        return i

    def line_at(self, t: float) -> LyricLine | None:
        i = self.index_at(t)
        return None if i is None else self.lines[i]

    def clip(self, start: float, end: float) -> Lyrics:
        """[start, end) 구간만 남기고 시각을 0 기준으로 옮긴다."""
        out = []
        for ln in self.lines:
            s, e = max(ln.start, start), min(ln.end, end)
            if s < e:
                out.append(LyricLine(s - start, e - start, ln.text))
        return Lyrics(out, dict(self.meta))


def _parse_time(m: re.Match) -> float:
    minutes, seconds, frac = m.group(1), m.group(2), m.group(3) or "0"
    return int(minutes) * 60 + int(seconds) + int(frac) / 10 ** len(frac)


def parse(text: str, duration: float | None = None, max_line: float = 8.0) -> Lyrics:
    """LRC 문자열을 파싱한다.

    duration: 곡 길이(초). 마지막 줄의 끝 시각으로 쓴다.
    max_line: 다음 줄이 너무 멀 때 한 줄을 띄워 둘 최대 시간(초).
    """
    meta: dict[str, str] = {}
    stamped: list[tuple[float, str]] = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        times = []
        pos = 0
        while m := _TIME_TAG.match(line, pos):
            times.append(_parse_time(m))
            pos = m.end()
        if times:
            body = line[pos:].strip()
            stamped.extend((t, body) for t in times)
        elif m := _META_TAG.match(line):
            meta[m.group(1).lower()] = m.group(2).strip()

    offset = float(meta.get("offset", "0") or 0) / 1000
    stamped.sort(key=lambda x: x[0])

    lines = []
    for i, (t, body) in enumerate(stamped):
        start = max(0.0, t - offset)
        if i + 1 < len(stamped):
            nxt = max(0.0, stamped[i + 1][0] - offset)
        else:
            nxt = duration if duration is not None else start + max_line
        end = min(nxt, start + max_line)
        # 빈 가사 줄은 "여기서 앞 줄이 끝난다"는 표시로만 쓴다.
        if body and end > start:
            lines.append(LyricLine(start, end, body))
    return Lyrics(lines, meta)


def load(path: str, duration: float | None = None, max_line: float = 8.0) -> Lyrics:
    with open(path, encoding="utf-8-sig") as f:
        return parse(f.read(), duration=duration, max_line=max_line)
