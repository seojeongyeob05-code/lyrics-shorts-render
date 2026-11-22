"""음원을 프레임마다의 주파수 막대 높이(0~1)로 바꾼다.

ffmpeg로 모노 PCM을 읽고, 프레임마다 FFT를 해서 저음~고음을 로그 간격 막대로 묶는다.
"""

from __future__ import annotations

import subprocess

import numpy as np

SAMPLE_RATE = 22050
WINDOW = 2048  # FFT 창 크기(약 93ms)
LOW_HZ, HIGH_HZ = 50.0, 8000.0
RANGE_DB = 45.0  # 가장 큰 소리에서 이만큼 아래까지를 0~1로 보여준다
CHUNK = 256  # 한 번에 FFT할 프레임 수(메모리 상한)


def read_pcm(path: str, start: float, duration: float, ffmpeg: str = "ffmpeg") -> np.ndarray:
    """[start, start+duration) 구간을 22050Hz 모노 float32로."""
    out = subprocess.run(
        [ffmpeg, "-v", "error", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", path,
         "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"],
        capture_output=True)
    if out.returncode != 0:
        raise RuntimeError(f"음원을 읽지 못했습니다: {path}\n{out.stderr.decode(errors='replace').strip()}")
    return np.frombuffer(out.stdout, dtype=np.float32)


def band_edges(bands: int) -> np.ndarray:
    """LOW_HZ~HIGH_HZ를 로그 간격으로 나눈 bands+1개의 경계(FFT 칸 번호)."""
    hz = np.geomspace(LOW_HZ, HIGH_HZ, bands + 1)
    bins = np.round(hz * WINDOW / SAMPLE_RATE).astype(int)
    # 저음 쪽은 칸이 좁아 같은 번호가 겹치므로 최소 한 칸씩 벌린다
    for i in range(1, len(bins)):
        bins[i] = max(bins[i], bins[i - 1] + 1)
    return bins


def levels_from_pcm(pcm: np.ndarray, n_frames: int, fps: float, bands: int = 32,
                    decay: float = 0.85) -> np.ndarray:
    """(n_frames, bands) 막대 높이. 올라갈 땐 바로, 내려갈 땐 프레임마다 decay배로 천천히."""
    hop = SAMPLE_RATE / fps
    padded = np.concatenate([np.zeros(WINDOW // 2, np.float32), pcm,
                             np.zeros(WINDOW, np.float32)])
    starts = (np.arange(n_frames) * hop).astype(int)
    edges = band_edges(bands)
    window = np.hanning(WINDOW).astype(np.float32)
    energy = np.zeros((n_frames, bands))
    # 프레임마다 2048칸 창을 한꺼번에 만들면 3분 반 곡에서 수백 MB가 되므로 나눠서 계산
    for c in range(0, n_frames, CHUNK):
        idx = starts[c:c + CHUNK]
        frames = padded[idx[:, None] + np.arange(WINDOW)] * window
        mag = np.abs(np.fft.rfft(frames, axis=1))
        energy[c:c + len(idx)] = np.stack(
            [mag[:, a:b].mean(axis=1) for a, b in zip(edges[:-1], edges[1:])], axis=1)
    db = 20 * np.log10(energy + 1e-9)
    loud = db[db > -150]
    ref = np.percentile(loud, 98) if loud.size else 0.0
    raw = np.clip((db - (ref - RANGE_DB)) / RANGE_DB, 0.0, 1.0)

    decay = decay ** (30.0 / fps)  # fps가 달라도 같은 속도로 내려가게
    out = np.empty_like(raw)
    prev = np.zeros(bands)
    for k in range(n_frames):
        prev = np.maximum(raw[k], prev * decay)
        out[k] = prev
    return out


def load_levels(path: str, start: float, duration: float, fps: float, bands: int = 32,
                ffmpeg: str = "ffmpeg") -> np.ndarray:
    n_frames = round(duration * fps)
    return levels_from_pcm(read_pcm(path, start, duration, ffmpeg), n_frames, fps, bands)
