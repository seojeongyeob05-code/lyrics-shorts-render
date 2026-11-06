"""LRC 가사 파일 파서.

지원 형식:
    [ti:제목] [ar:가수] 같은 메타 태그
    [00:12.34]가사          (분:초.소수)
    [00:12.34][01:02.00]후렴 (한 줄에 여러 타임스탬프)
    [offset:+200]           (밀리초, 양수면 가사가 앞당겨짐)
    [00:12.00]<00:12.00>단어 <00:12.60>단위 <00:13.10>타이밍 <00:14.00>
                            (Enhanced LRC: 노래방식 하이라이트용 글자 진행 시각)
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field

_TIME_TAG = re.compile(r"\[(\d+):(\d{1,2})(?:[.:](\d{1,3}))?\]")
_META_TAG = re.compile(r"^\[([a-zA-Z]+):(.*)\]$")
_WORD_TAG = re.compile(r"<(\d+):(\d{1,2})(?:[.:](\d{1,3}))?>")


@dataclass(frozen=True)
class LyricLine:
    start: float  # 초
    end: float  # 초 (다음 줄 시작 또는 곡 끝)
    text: str
    # 노래방식 진행 지점: (시각, 그 시각까지 불린 글자 수). 비어 있으면 줄 단위 가사.
    marks: tuple[tuple[float, int], ...] = ()

    def sung_chars(self, t: float) -> float:
        """시각 t까지 불린 글자 수(소수 = 글자 안에서의 진행). marks가 없으면 줄 전체."""
        if not self.marks:
            return float(len(self.text))
        pts = list(self.marks)
        if pts[-1][1] < len(self.text):
            pts.append((self.end, len(self.text)))
        if t <= pts[0][0]:
            return float(pts[0][1]) if t == pts[0][0] else 0.0
        for (t0, c0), (t1, c1) in zip(pts, pts[1:]):
            if t < t1:
                return c0 + (c1 - c0) * (t - t0) / (t1 - t0) if t1 > t0 else float(c1)
        return float(pts[-1][1])


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
                marks = tuple((mt - start, c) for mt, c in ln.marks)
                out.append(LyricLine(s - start, e - start, ln.text, marks))
        return Lyrics(out, dict(self.meta))


def _split_words(body: str) -> tuple[str, list[tuple[float, int]]]:
    """'<t>가 <t>나' → ('가 나', [(t, 0), (t, 2)]). 공백은 한 칸으로 줄인다."""
    text = ""
    marks = []
    pos = 0
    for m in _WORD_TAG.finditer(body):
        text += body[pos:m.start()]
        pos = m.end()
        norm = " ".join(text.split())
        # 태그 앞이 공백이면 다음 단어는 공백 뒤에서 시작한다
        offset = len(norm) + (1 if norm and text[-1:].isspace() else 0)
        marks.append((_parse_time(m), offset))
    text = " ".join((text + body[pos:]).split())
    return text, [(t, min(c, len(text))) for t, c in marks]


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
        text, marks = _split_words(body)
        if text and end > start:
            marks = tuple((max(0.0, mt - offset), c) for mt, c in marks)
            lines.append(LyricLine(start, end, text, marks))
    return Lyrics(lines, meta)


def load(path: str, duration: float | None = None, max_line: float = 8.0) -> Lyrics:
    with open(path, encoding="utf-8-sig") as f:
        return parse(f.read(), duration=duration, max_line=max_line)
