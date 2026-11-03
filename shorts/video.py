"""프레임을 ffmpeg 파이프로 흘려 mp4를 만든다(음원이 있으면 함께 넣는다)."""

from __future__ import annotations

import subprocess
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
    drawn = 0
    last_key = None
    last_bytes = b""
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        try:
            for k in range(n_frames):
                t = k / opts.fps
                # 화면에 보이는 줄이 그대로면 직전 프레임을 재사용한다.
                key = renderer.state_key(lyrics, t)
                if key != last_key:
                    last_bytes = renderer.render(lyrics, t).tobytes()
                    last_key = key
                    drawn += 1
                proc.stdin.write(last_bytes)
            proc.stdin.close()
        except BrokenPipeError:
            pass  # ffmpeg가 먼저 죽었다. 아래에서 에러 메시지를 보여준다.
        err = proc.stderr.read().decode(errors="replace")
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg 실패 (code {proc.returncode}):\n{err.strip()}")
    return drawn
