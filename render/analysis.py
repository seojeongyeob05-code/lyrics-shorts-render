"""시뮬레이션 결과 -> 프레임별 측정값 (음높이, 크기, 폐 부피) + 스펙트로그램."""
import numpy as np

VC = 4500.0          # 폐활량 (cm^3)
LUNG_START = 0.80    # 시작 폐 부피 (VC 비율)
LUNG_MIN = 0.20
INHALE_RATE = 4.0    # 들숨 시 초당 회복 비율
DB_REF_OFFSET = 108.0  # 합성 RMS -> 표시용 dB 보정 (중립 발성 ~80 dB)


def f0_at(x1, fs, n, win=0.045):
    """n 위치 주변의 성대 변위 영점 교차로 기본주파수 추정. 진동 없으면 None."""
    h = int(win * fs / 2)
    seg = x1[max(0, n - h): n + h].astype(float)
    if len(seg) < 64 or seg.std() < 2e-3:
        return None
    seg = seg - seg.mean()
    up = np.where((seg[:-1] < 0) & (seg[1:] >= 0))[0]
    if len(up) < 3:
        return None
    # 선형 보간된 교차 시점
    frac = seg[up] / (seg[up] - seg[up + 1])
    ts = up + frac
    periods = np.diff(ts)
    med = np.median(periods)
    good = periods[np.abs(periods - med) < 0.3 * med]
    if len(good) == 0:
        return None
    return fs / good.mean()


def level_db(audio, fs, n, win=0.06):
    h = int(win * fs / 2)
    seg = audio[max(0, n - h): n + h]
    if len(seg) == 0:
        return None
    rms = np.sqrt(np.mean(seg ** 2))
    if rms < 1e-6:
        return None
    db = 20 * np.log10(rms) + DB_REF_OFFSET
    return db if db > 40 else None


def lung_volume(u, ps_blocks, fs, block):
    """블록마다 흐름(U)만큼 폐 부피 감소, 폐압 ~0 이면 들숨으로 회복."""
    nb = len(ps_blocks)
    ub = u[: nb * block].reshape(nb, block).mean(axis=1)
    dt = block / fs
    vol = np.zeros(nb)
    v = LUNG_START
    for b in range(nb):
        if ps_blocks[b] < 1.0:
            v = min(LUNG_START, v + INHALE_RATE * dt * (LUNG_START - v + 0.05))
        else:
            v = max(LUNG_MIN, v - ub[b] * dt / VC)
        vol[b] = v
    return vol


MAGMA = np.array([
    (0.00, (0, 0, 4)), (0.13, (28, 16, 68)), (0.25, (79, 18, 123)),
    (0.38, (129, 37, 129)), (0.50, (181, 54, 122)), (0.63, (229, 80, 100)),
    (0.75, (251, 135, 97)), (0.88, (254, 194, 135)), (1.00, (252, 253, 191)),
], dtype=object)


def _colormap(v):
    xs = np.array([p for p, _ in MAGMA], float)
    cs = np.array([c for _, c in MAGMA], float)
    out = np.empty(v.shape + (3,), np.uint8)
    for ch in range(3):
        out[..., ch] = np.interp(v, xs, cs[:, ch]).astype(np.uint8)
    return out


def spectrogram(audio, fs, px_per_sec, height, fmax=5000.0, n_fft=2048, dyn=60.0):
    """(height, width, 3) uint8 이미지. 위쪽이 높은 주파수."""
    hop = fs / px_per_sec
    width = int(len(audio) / hop)
    win = np.hanning(n_fft)
    pad = np.concatenate([np.zeros(n_fft // 2), audio, np.zeros(n_fft)])
    idx = (np.arange(width) * hop).astype(int)
    nbin = int(fmax / (fs / n_fft))
    spec = np.empty((width, nbin))
    for c in range(0, width, 1024):
        frames = np.stack([pad[i:i + n_fft] * win for i in idx[c:c + 1024]])
        spec[c:c + len(frames)] = (np.abs(np.fft.rfft(frames, axis=1)) ** 2)[:, :nbin]
    db = 10 * np.log10(spec + 1e-12)
    top = np.percentile(db, 99.7)
    v = np.clip((db - (top - dyn)) / dyn, 0, 1)
    # 세로 리샘플
    ys = np.linspace(0, nbin - 1, height)
    v = np.stack([np.interp(ys, np.arange(nbin), col) for col in v], axis=1)
    v = v[::-1]
    return _colormap(v)
