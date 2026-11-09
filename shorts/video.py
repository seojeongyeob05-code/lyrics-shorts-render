"""프레임을 ffmpeg 파이프로 흘려 mp4를 만든다(음원이 있으면 함께 넣는다)."""

from __future__ import annotations

import queue
import subprocess
import threading
from dataclasses import dataclass

from .frame import FrameRenderer
from .lrc import Lyrics


@dataclass
class VideoOptions:
    fps: int = 30
    crf: int = 20  # 낮을수록 화질↑ 용량↑
    preset: str = "veryfast"
    audio_bitrate: str = "192k"
    ffmpeg: str = "ffmpeg"


def build_ffmpeg_cmd(out_path: str, size: tuple[int, int], duration: float,
                     opts: VideoOptions, audio: str | None = None,
                     audio_start: float = 0.0) -> list[str]:
    w, h = size
    cmd = [opts.ffmpeg, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(opts.fps), "-i", "-"]
    if audio:
        cmd += ["-ss", f"{audio_start:.3f}", "-t", f"{duration:.3f}", "-i", audio,
                "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", opts.audio_bitrate]
    cmd += ["-c:v", "libx264", "-preset", opts.preset, "-crf", str(opts.crf),
            "-pix_fmt", "yuv420p", "-t", f"{duration:.3f}",
            "-movflags", "+faststart", out_path]
    return cmd


def render_video(lyrics: Lyrics, out_path: str, duration: float,
                 renderer: FrameRenderer | None = None, opts: VideoOptions | None = None,
                 audio: str | None = None, audio_start: float = 0.0) -> int:
    """[0, duration)초를 렌더링해 out_path에 저장한다. 실제로 그린 프레임 수를 돌려준다.

    audio_start: 음원의 몇 초 지점부터 영상 0초에 맞출지(구간 렌더용).
    """
    renderer = renderer or FrameRenderer()
    opts = opts or VideoOptions()
    s = renderer.style
    cmd = build_ffmpeg_cmd(out_path, (s.width, s.height), duration, opts, audio, audio_start)
    n_frames = round(duration * opts.fps)
    drawn_before = renderer.layers_drawn
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        # 파이프 쓰기는 별도 스레드에서 한다. 쓰기는 ffmpeg가 인코딩하는 동안 막히는데,
        # 그동안 메인 스레드는 다음 프레임을 그릴 수 있다.
        frames: queue.Queue[bytes | None] = queue.Queue(maxsize=8)
        broken = threading.Event()

        def writer() -> None:
            while (data := frames.get()) is not None:
                if broken.is_set():
                    continue  # ffmpeg가 죽었으면 남은 프레임은 버린다
                try:
                    proc.stdin.write(data)
                except BrokenPipeError:
                    broken.set()
            try:
                proc.stdin.close()
            except BrokenPipeError:
                pass

        th = threading.Thread(target=writer, daemon=True)
        th.start()
        try:
            for k in range(n_frames):
                if broken.is_set():
                    break
                t = k / opts.fps
                # 가사 화면은 renderer가 캐시하므로 줄이 바뀔 때만 새로 그린다.
                frames.put(renderer.render_bytes(lyrics, t, progress=t / duration))
        finally:
            frames.put(None)
            th.join()
        err = proc.stderr.read().decode(errors="replace")
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg 실패 (code {proc.returncode}):\n{err.strip()}")
    return renderer.layers_drawn - drawn_before
