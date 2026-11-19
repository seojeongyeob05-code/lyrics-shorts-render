"""명령줄 진입점.

    python -m shorts render song.lrc --audio song.mp3 --bg bg.jpg --start 0:45 --duration 30
    python -m shorts frame song.lrc --at 0:50 -o preview.png
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

from PIL import Image

from . import audio, guide, lrc
from .frame import FrameRenderer
from .project import load_project, parse_time, parse_times
from .styles import PRESET_DIR, list_presets, load_style, style_from_dict
from .video import VideoOptions, render_video

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
        if isinstance(args.style, dict):  # 곡 설정 파일에 직접 적은 스타일
            style = style_from_dict(args.style, args.project_dir, "곡 설정 파일의 style")
        else:
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


def segment_paths(base: str, n: int) -> list[str]:
    """구간이 여러 개면 base 이름 뒤에 -1, -2 ...를 붙인다."""
    if n == 1:
        return [base]
    root, ext = os.path.splitext(base)
    return [f"{root}-{k}{ext}" for k in range(1, n + 1)]


def cmd_render(args) -> None:
    song_len = probe_duration(args.audio) if args.audio else None
    lyrics = _apply_info(args, lrc.load(args.lrc, duration=song_len))
    if not lyrics.lines:
        raise SystemExit(f"가사 줄이 없습니다: {args.lrc}")

    end_of_song = song_len if song_len is not None else lyrics.lines[-1].end
    starts = args.start
    durations = args.duration or [None]
    if len(durations) == 1:
        durations = durations * len(starts)
    elif len(durations) != len(starts):
        raise SystemExit(f"--duration은 1개이거나 --start 개수({len(starts)})와 같아야 합니다")
    segments = []
    for start, duration in zip(starts, durations):  # 렌더 전에 모든 구간을 먼저 확인
        if start >= end_of_song:
            raise SystemExit(f"--start({start:g}s)가 곡 길이({end_of_song:g}s)를 넘습니다")
        segments.append((start, min(duration or end_of_song - start, end_of_song - start)))

    if args.preview:
        opts = VideoOptions(fps=min(args.fps, 15), preset="ultrafast", crf=28)
        base = args.out or args.stem + ".preview.mp4"
    else:
        opts = VideoOptions(fps=args.fps)
        base = args.out or args.stem + ".mp4"
    renderer = _renderer(args)
    if renderer.style.visualizer and not args.audio:
        print("주의: 스타일에 visualizer가 켜져 있지만 --audio가 없어서 음악 막대를 그리지 않아요",
              file=sys.stderr)
    for (start, duration), out in zip(segments, segment_paths(base, len(segments))):
        clip = lyrics.clip(start, start + duration)
        drawn_before = renderer.layers_drawn  # 아래 겹침 검사도 가사를 미리 그려 캐시한다
        # 줄마다 한 번씩(페이드가 끝난 뒤) 가림 영역에 걸리는지 확인
        warn_overlaps(renderer, clip, [0.0] + [ln.start + 0.3 for ln in clip.lines], offset=start)
        t0 = time.perf_counter()
        progress = ProgressPrinter(sys.stderr) if sys.stderr.isatty() else None
        levels = None
        if renderer.style.visualizer and args.audio:
            levels = audio.load_levels(args.audio, start, duration, opts.fps,
                                       renderer.style.viz_bands)
        render_video(clip, out, duration, renderer, opts, audio=args.audio,
                     audio_start=start, on_progress=progress, levels=levels)
        drawn = renderer.layers_drawn - drawn_before
        if progress:
            progress.done()
        print(f"{out}  ({duration:.1f}s, 그린 프레임 {drawn}장, {time.perf_counter() - t0:.1f}s 소요)")


def warn_overlaps(renderer, lyrics, times, offset: float = 0.0) -> None:
    """쇼츠 앱 UI에 가려질 내용이 있으면 stderr에 알린다."""
    for content, zone, t in guide.find_overlaps(renderer, lyrics, times):
        print(f"주의: {content}이(가) 쇼츠 앱의 '{zone}' 자리에 걸려요 "
              f"({format_time(t + offset)}) — frame --guide로 확인", file=sys.stderr)


def format_time(sec: float) -> str:
    return f"{int(sec // 60)}:{sec % 60:04.1f}"


def cmd_frame(args) -> None:
    lyrics = _apply_info(args, lrc.load(args.lrc))
    out = args.out or args.stem + ".png"
    renderer = _renderer(args)
    img = renderer.render(lyrics, args.at, progress=args.at / max(lyrics.lines[-1].end, 1e-6)
                          if lyrics.lines else None)
    if args.guide:
        img = guide.draw_guide(img)
    img.save(out)
    print(out)
    warn_overlaps(renderer, lyrics, [args.at])


def cmd_styles(args) -> None:
    for name in list_presets():
        with open(os.path.join(PRESET_DIR, f"{name}.json"), encoding="utf-8") as f:
            desc = json.load(f).get("description", "")
        print(f"{name:10} {desc}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m shorts", description="가사 쇼츠 렌더러")
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("lrc", help="LRC 가사 파일, 또는 곡 설정 파일(.json)")
    common.add_argument("-o", "--out", help="출력 파일 (기본: 가사·설정 파일 이름)")
    common.add_argument("--bg", help="배경 이미지")
    common.add_argument("--cover", help="앨범 아트 이미지 (모양·크기·위치는 스타일의 cover_*)")
    common.add_argument("--font", help="폰트 파일 (기본: 스타일 설정 또는 한글 폰트 자동 탐색)")
    common.add_argument("--title", help="화면 위쪽 곡 제목 (기본: LRC [ti:], 빈 문자열이면 숨김)")
    common.add_argument("--artist", help="곡 제목 아래 가수 (기본: LRC [ar:], 빈 문자열이면 숨김)")
    common.add_argument("--style",
                        help="스타일 프리셋 이름 또는 JSON 파일 (목록: python -m shorts styles)")

    r = sub.add_parser("render", parents=[common], help="mp4 영상 만들기")
    r.add_argument("--audio", help="음원 파일")
    r.add_argument("--start", type=parse_times,
                   help="시작 지점 (예: 0:45). 쉼표로 여러 개 주면 구간마다 영상 하나씩: 0:45,1:30")
    r.add_argument("--duration", type=parse_times,
                   help="길이 (기본: 곡 끝까지). 하나면 모든 구간 공통, 여러 개면 구간마다: 20,15")
    r.add_argument("--fps", type=int)
    r.add_argument("--preview", action="store_true",
                   help="빠른 미리보기: 절반 해상도·15fps, 기본 출력 이름 *.preview.mp4")
    r.set_defaults(func=cmd_render)

    f = sub.add_parser("frame", parents=[common], help="한 장면 PNG 미리보기")
    f.add_argument("--at", type=parse_time, default=0.0, help="미리볼 시각 (예: 0:50)")
    f.add_argument("--guide", action="store_true",
                   help="쇼츠 앱 UI(메뉴·버튼·제목)가 덮는 자리를 반투명 빨강으로 표시")
    f.set_defaults(func=cmd_frame)

    sub.add_parser("styles", help="내장 스타일 프리셋 목록").set_defaults(func=cmd_styles)
    return p


_DEFAULTS = {"style": "default", "start": [0.0], "fps": 30}


def resolve_args(args) -> argparse.Namespace:
    """곡 설정 파일(.json)이면 그 값으로 빈 옵션을 채우고, 남은 옵션엔 기본값을 넣는다."""
    args.project_dir = os.getcwd()
    if args.lrc.lower().endswith(".json"):
        try:
            project = load_project(args.lrc)
        except (OSError, ValueError) as e:
            raise SystemExit(f"곡 설정 파일을 읽지 못했습니다: {e}") from None
        args.project_dir, args.stem = project.pop("_base"), project.pop("_stem")
        args.lrc = project.pop("lyrics")
        for key, value in project.items():
            if hasattr(args, key) and getattr(args, key) in (None, False):  # 명령줄 옵션이 우선
                setattr(args, key, value)
    else:
        args.stem = os.path.splitext(args.lrc)[0]
    for key, value in _DEFAULTS.items():
        if getattr(args, key, "-") is None:
            setattr(args, key, value)
    return args


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if hasattr(args, "lrc"):
        args = resolve_args(args)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
