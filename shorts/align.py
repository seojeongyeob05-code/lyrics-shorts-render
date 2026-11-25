"""알고 있는 가사를 음성 인식 결과(단어마다 시각)에 맞춰 줄·단어 시각을 찾는다.

인식 결과는 틀린 글자가 섞여도 괜찮다. 가사와 인식 글자를 글자 단위로 맞대어(difflib)
일치하는 글자의 시각만 쓰고, 나머지는 앞뒤에서 채운다.

    words = [{"start": 1.2, "end": 1.6, "word": "壁に"}, ...]   # faster-whisper word_timestamps
    lines = align_lines(["壁にもたれて一晩中", ...], words)
"""

from __future__ import annotations

import difflib
import unicodedata
from dataclasses import dataclass


def _norm_char(c: str) -> str:
    """비교용 글자: 가타카나→히라가나, 전각→반각, 소문자. 비교에서 뺄 글자면 ''."""
    c = unicodedata.normalize("NFKC", c).lower()
    if not c or not (c.isalnum()):
        return ""
    o = ord(c)
    if 0x30A1 <= o <= 0x30F6:  # 가타카나 → 히라가나
        c = chr(o - 0x60)
    return c


def _norm(text: str) -> tuple[str, list[int]]:
    """정규화한 글자열과, 그 글자들이 원래 text의 몇 번째 글자였는지."""
    out, idx = [], []
    for i, ch in enumerate(text):
        n = _norm_char(ch)
        for c in n:
            out.append(c)
            idx.append(i)
    return "".join(out), idx


@dataclass
class AlignedLine:
    text: str
    start: float | None  # 못 찾았으면 None
    end: float | None
    marks: list[tuple[float, int]]  # (시각, text 안 글자 위치) — 인식 단어가 시작하는 자리


def align_lines(lines: list[str], words: list[dict]) -> list[AlignedLine]:
    # 인식 결과를 글자마다 시각이 붙은 줄로 펼친다(단어 안에서는 균등하게 나눔)
    rec_chars, rec_times, rec_word_start = [], [], []
    for w in words:
        norm, _ = _norm(w["word"])
        n = len(norm)
        for k, c in enumerate(norm):
            rec_chars.append(c)
            rec_times.append(w["start"] + (w["end"] - w["start"]) * k / max(n, 1))
            rec_word_start.append(k == 0)
    lyric_chars, owner, pos = [], [], []
    for li, line in enumerate(lines):
        norm, idx = _norm(line)
        lyric_chars.extend(norm)
        owner.extend([li] * len(norm))
        pos.extend(idx)

    matcher = difflib.SequenceMatcher(None, lyric_chars, rec_chars, autojunk=False)
    time_of: dict[int, float] = {}  # 가사 글자 번호 → 시각
    word_start: set[int] = set()
    for a, b, size in matcher.get_matching_blocks():
        for k in range(size):
            time_of[a + k] = rec_times[b + k]
            if rec_word_start[b + k] or k == 0:
                word_start.add(a + k)

    result = []
    for li, line in enumerate(lines):
        chars = [i for i, o in enumerate(owner) if o == li]
        hit = [i for i in chars if i in time_of]
        if not hit:
            result.append(AlignedLine(line, None, None, []))
            continue
        # 줄 첫 글자가 안 맞았으면 맞은 첫 글자 시각에서 글자당 0.2초씩 앞으로
        first = hit[0]
        start = time_of[first] - 0.2 * (chars.index(first))
        marks, last_t = [], -1.0
        for i in hit:
            t = time_of[i]
            if i in word_start and t > last_t + 0.05:
                marks.append((round(t, 2), pos[i]))
                last_t = t
        if marks and marks[0][1] != 0:
            marks.insert(0, (round(max(0.0, start), 2), 0))
        end = time_of[hit[-1]] + 0.4
        result.append(AlignedLine(line, round(max(0.0, start), 2), round(end, 2), marks))
    _fill_missing(result)
    return result


def _fill_missing(lines: list[AlignedLine]) -> None:
    """못 찾은 줄은 앞뒤 찾은 줄 사이에 고르게 끼워 넣고, 시작이 거꾸로 가지 않게 다듬는다."""
    known = [i for i, ln in enumerate(lines) if ln.start is not None]
    if not known:
        return
    for i, ln in enumerate(lines):
        if ln.start is not None:
            continue
        prev = max((k for k in known if k < i), default=None)
        nxt = min((k for k in known if k > i), default=None)
        if prev is None:
            ln.start = max(0.0, lines[nxt].start - 3.0 * (nxt - i))
        elif nxt is None:
            ln.start = lines[prev].end + 3.0 * (i - prev - 1)
        else:
            span = lines[nxt].start - lines[prev].end
            ln.start = lines[prev].end + span * (i - prev) / (nxt - prev)
        ln.start = round(ln.start, 2)
        ln.end = round(ln.start + 2.5, 2)
    for a, b in zip(lines, lines[1:]):
        if b.start <= a.start:
            b.start = round(a.start + 0.5, 2)
            b.marks = [m for m in b.marks if m[0] >= b.start]


def to_lrc(lines: list[AlignedLine], subs: list[list[str]] | None = None,
           meta: dict[str, str] | None = None, gap: float = 1.5, karaoke: bool = True) -> str:
    """정렬 결과 → LRC. subs[i]는 i번째 줄 아래에 같이 보일 줄들(발음·번역 등, 같은 시각으로 씀).
    다음 줄까지 gap초 넘게 비면 빈 줄로 앞 줄을 끝낸다."""
    def fmt(t: float) -> str:
        cs = max(0, round(t * 100))
        return f"{cs // 6000:02}:{cs // 100 % 60:02}.{cs % 100:02}"

    out = [f"[{k}:{v}]" for k, v in (meta or {}).items()]
    for i, ln in enumerate(lines):
        if karaoke and len(ln.marks) > 1:
            pieces, cuts = [], [p for _, p in ln.marks] + [len(ln.text)]
            for (t, p), q in zip(ln.marks, cuts[1:]):
                pieces.append(f"<{fmt(t)}>{ln.text[p:q]}")
            body = "".join(pieces) + f"<{fmt(ln.end)}>"
        else:
            body = ln.text
        out.append(f"[{fmt(ln.start)}]{body}")
        for sub in (subs[i] if subs else []):
            out.append(f"[{fmt(ln.start)}]{sub}")
        nxt = lines[i + 1].start if i + 1 < len(lines) else None
        if nxt is None or nxt - ln.end > gap:
            out.append(f"[{fmt(ln.end)}]")
    return "\n".join(out) + "\n"
