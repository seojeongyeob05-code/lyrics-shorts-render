"""명령줄 진입점.

    python -m shorts render song.lrc --audio song.mp3 --bg bg.jpg --start 0:45 --duration 30
    python -m shorts frame song.lrc --at 0:50 -o preview.png
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

from PIL import Image

from . import lrc
from .frame import FrameRenderer
from .styles import PRESET_DIR, list_presets, load_style
from .video import VideoOptions, render_video

_TIME = re.compile(r"^(?:(\d+):)?(\d+(?:\.\d+)?)$")


def parse_time(text: str) -> float:
    """'45', '0:45', '1:02.5' 같은 표기를 초로."""
    m = _TIME.match(text.strip())
    if not m:
        raise argparse.ArgumentTypeError(f"시간 형식이 아닙니다: {text!r} (예: 45, 0:45, 1:02.5)")
    minutes, seconds = m.group(1), float(m.group(2))
    if minutes is not None and seconds >= 60:
        raise argparse.ArgumentTypeError(f"초는 60 미만이어야 합니다: {text!r}")
    return int(minutes or 0) * 60 + seconds


def probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"음원 길이를 읽지 못했습니다: {path}\n{out.stderr.strip()}")
    return float(out.stdout)


def _apply_info(args, lyrics: lrc.Lyrics) -> lrc.Lyrics:
    """--title/--artist로 LRC의 곡 정보를 덮어쓴다."""
    if args.title is not None:
        lyrics.meta["ti"] = args.title
    if args.artist is not None:
        lyrics.meta["ar"] = args.artist
    return lyrics


def _renderer(args) -> FrameRenderer:
    try:
        style = load_style(args.style)
    except ValueError as e:
        raise SystemExit(str(e)) from None
    if args.font:
        style.font_path = args.font
    if getattr(args, "preview", False):
        style = style.scaled(0.5)
    bg = Image.open(args.bg) if args.bg else None
    cover = Image.open(args.cover) if args.cover else None
    return FrameRenderer(style, background=bg, cover=cover)


class ProgressPrinter:
    """'렌더 중 42% · 남은 시간 약 3초'를 한 줄에 덮어쓰며 보여준다(0.3초마다)."""

    def __init__(self, stream, clock=time.perf_counter):
        self.stream, self.clock = stream, clock
        self.start = clock()
        self.last = -1.0

    def __call__(self, done: int, total: int) -> None:
        now = self.clock()
        if done < total and now - self.last < 0.3:
            return
        self.last = now
        elapsed = now - self.start
        eta = elapsed / done * (total - done) if done else 0
        self.stream.write(f"\r렌더 중 {done * 100 // total:3d}% · 남은 시간 약 {eta:.0f}초   ")
        self.stream.flush()

    def done(self) -> None:
        self.stream.write("\r" + " " * 40 + "\r")
        self.stream.flush()


def cmd_render(args) -> None:
    song_len = probe_duration(args.audio) if args.audio else None
    lyrics = _apply_info(args, lrc.load(args.lrc, duration=song_len))
    if not lyrics.lines:
        raise SystemExit(f"가사 줄이 없습니다: {args.lrc}")

    end_of_song = song_len if song_len is not None else lyrics.lines[-1].end
    if args.start >= end_of_song:
        raise SystemExit(f"--start({args.start:g}s)가 곡 길이({end_of_song:g}s)를 넘습니다")
    duration = args.duration or end_of_song - args.start
    duration = min(duration, end_of_song - args.start)

    clip = lyrics.clip(args.start, args.start + duration)
    out = args.out or os.path.splitext(args.lrc)[0] + ".mp4"
    if args.preview:
        opts = VideoOptions(fps=min(args.fps, 15), preset="ultrafast", crf=28)
        if not args.out:
            out = os.path.splitext(args.lrc)[0] + ".preview.mp4"
    else:
        opts = VideoOptions(fps=args.fps)
    t0 = time.perf_counter()
    progress = ProgressPrinter(sys.stderr) if sys.stderr.isatty() else None
    drawn = render_video(clip, out, duration, _renderer(args), opts,
                         audio=args.audio, audio_start=args.start, on_progress=progress)
    if progress:
        progress.done()
    print(f"{out}  ({duration:.1f}s, 그린 프레임 {drawn}장, {time.perf_counter() - t0:.1f}s 소요)")


def cmd_frame(args) -> None:
    lyrics = _apply_info(args, lrc.load(args.lrc))
    out = args.out or os.path.splitext(args.lrc)[0] + ".png"
    _renderer(args).render(lyrics, args.at).save(out)
    print(out)


def cmd_styles(args) -> None:
    for name in list_presets():
        with open(os.path.join(PRESET_DIR, f"{name}.json"), encoding="utf-8") as f:
            desc = json.load(f).get("description", "")
        print(f"{name:10} {desc}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m shorts", description="가사 쇼츠 렌더러")
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("lrc", help="LRC 가사 파일")
    common.add_argument("-o", "--out", help="출력 파일 (기본: 가사 파일 이름)")
    common.add_argument("--bg", help="배경 이미지")
    common.add_argument("--cover", help="앨범 아트 이미지 (모양·크기·위치는 스타일의 cover_*)")
    common.add_argument("--font", help="폰트 파일 (기본: 스타일 설정 또는 한글 폰트 자동 탐색)")
    common.add_argument("--title", help="화면 위쪽 곡 제목 (기본: LRC [ti:], 빈 문자열이면 숨김)")
    common.add_argument("--artist", help="곡 제목 아래 가수 (기본: LRC [ar:], 빈 문자열이면 숨김)")
    common.add_argument("--style", default="default",
                        help="스타일 프리셋 이름 또는 JSON 파일 (목록: python -m shorts styles)")

    r = sub.add_parser("render", parents=[common], help="mp4 영상 만들기")
    r.add_argument("--audio", help="음원 파일")
    r.add_argument("--start", type=parse_time, default=0.0, help="시작 지점 (예: 0:45)")
    r.add_argument("--duration", type=parse_time, help="길이 (기본: 곡 끝까지)")
    r.add_argument("--fps", type=int, default=30)
    r.add_argument("--preview", action="store_true",
                   help="빠른 미리보기: 절반 해상도·15fps, 기본 출력 이름 *.preview.mp4")
    r.set_defaults(func=cmd_render)

    f = sub.add_parser("frame", parents=[common], help="한 장면 PNG 미리보기")
    f.add_argument("--at", type=parse_time, default=0.0, help="미리볼 시각 (예: 0:50)")
    f.set_defaults(func=cmd_frame)

    sub.add_parser("styles", help="내장 스타일 프리셋 목록").set_defaults(func=cmd_styles)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
