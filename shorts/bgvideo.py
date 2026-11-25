"""배경 영상: 짧은 영상을 화면에 꽉 채워 반복 재생한다.

ffmpeg로 프레임을 하나씩 읽어 오므로(전체를 메모리에 올리지 않음) 긴 영상도 괜찮다.
흐림은 ffmpeg에서, 어둡게(bg_dim)·아래쪽 그라데이션(bg_shade)은 미리 만든 마스크로 입힌다.
"""

from __future__ import annotations

import subprocess

from PIL import Image

VIDEO_EXTS = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".gif")
FPS = 30  # 배경을 읽는 속도. 렌더 fps와 달라도 시각으로 맞춘다


def is_video(path: str | None) -> bool:
    return bool(path) and path.lower().endswith(VIDEO_EXTS)


def probe_duration(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    try:
        return float(out.stdout)
    except ValueError:
        raise ValueError(f"배경 영상을 읽지 못했습니다: {path}\n{out.stderr.strip()}") from None


class BackgroundVideo:
    def __init__(self, path: str, size: tuple[int, int], blur: float = 0,
                 darken: Image.Image | None = None, ffmpeg: str = "ffmpeg"):
        """darken: 화면 크기 L 마스크(0~255). 검게 덮을 정도."""
        self.path, self.size, self.blur, self.darken, self.ffmpeg = path, size, blur, darken, ffmpeg
        self.duration = probe_duration(path)
        self._proc: subprocess.Popen | None = None
        self._index = -1  # 마지막으로 읽은 프레임 번호(곡 시각 기준)
        self._frame: Image.Image | None = None
        self._black = Image.new("RGB", size, (0, 0, 0))

    def frame_at(self, t: float) -> Image.Image:
        """곡 시각 t의 배경. 돌려받은 이미지를 고치지 말 것."""
        want = max(0, int(t * FPS))
        if self._frame is not None and want == self._index:
            return self._frame
        # 뒤로 가거나 2초 넘게 건너뛰면 그 자리부터 다시 연다(앞으로 조금은 읽고 버린다)
        if self._proc is None or want < self._index or want - self._index > 2 * FPS:
            self._open(want)
        w, h = self.size
        raw = b""
        while self._index < want:
            raw = self._proc.stdout.read(w * h * 3)
            if len(raw) < w * h * 3:  # 혹시 끝나면 처음부터
                self._open(want)
                continue
            self._index += 1
        frame = Image.frombytes("RGB", self.size, raw)
        if self.darken is not None:
            frame = Image.composite(self._black, frame, self.darken)
        self._frame = frame
        return frame

    def _open(self, index: int) -> None:
        self.close()
        w, h = self.size
        start = (index / FPS) % self.duration if self.duration > 0 else 0
        vf = [f"scale={w}:{h}:force_original_aspect_ratio=increase", f"crop={w}:{h}", f"fps={FPS}"]
        if self.blur > 0:
            vf.append(f"gblur=sigma={self.blur / 2:.2f}")  # Pillow 반경 ≈ 2σ
        self._proc = subprocess.Popen(
            [self.ffmpeg, "-v", "error", "-stream_loop", "-1", "-ss", f"{start:.3f}", "-i", self.path,
             "-an", "-vf", ",".join(vf), "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._index = index - 1

    def close(self) -> None:
        if self._proc is not None:
            self._proc.kill()
            self._proc.stdout.close()
            self._proc.wait()
            self._proc = None
