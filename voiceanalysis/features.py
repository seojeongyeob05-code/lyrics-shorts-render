"""녹음 -> 프레임별 음향 특징.

모든 특징은 같은 함수로 합성음에도 계산해서(역추정 표), 녹음과 모델을 같은 잣대로 비교한다.

특징 (10 ms 간격)
  f0     기본주파수 (Hz, 무성음이면 0)
  db     프레임 크기 (dBFS, 녹음 기기마다 다르므로 상대값으로만 사용)
  hnr    배음 대 잡음비 (dB). 낮을수록 바람 섞임/거침
  h1h2   1·2배음 크기 차 (dB). 클수록 성대가 덜 닫힘(바람), 작을수록 눌림
  cpp    켑스트럼 피크 돌출도 (dB). 주기성이 뚜렷할수록 큼
  tilt   0–1 kHz 대비 1–5 kHz 에너지 (dB). 클수록 밝고 강하게 부딪히는 소리
"""
import subprocess
import numpy as np

FS = 44100
HOP = 0.010
WIN = 0.046
FMIN, FMAX = 70.0, 1100.0


def load_audio(path, fs=FS):
    """ffmpeg 로 어떤 형식이든 모노 float 로 읽기."""
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(fs), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)


def _yin(frame, fs, fmin=FMIN, fmax=FMAX, thresh=0.15):
    """YIN 기본주파수. (f0, 비주기성) 반환."""
    n = len(frame)
    tau_max = min(int(fs / fmin), n // 2)
    tau_min = int(fs / fmax)
    x = frame - frame.mean()
    # 차이 함수 (FFT 자기상관 이용)
    f = np.fft.rfft(x, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:tau_max + 1]
    cs = np.concatenate([[0], np.cumsum(x ** 2)])
    e0 = cs[n - np.arange(tau_max + 1)] - cs[0]
    e1 = cs[n] - cs[np.arange(tau_max + 1)]
    d = e0 + e1 - 2 * ac
    d[0] = 0
    cm = np.ones_like(d)
    run = np.cumsum(d[1:])
    cm[1:] = d[1:] * np.arange(1, tau_max + 1) / np.maximum(run, 1e-12)
    rng = cm[tau_min:tau_max]
    # 임계값 아래 첫 골짜기. 없으면 전역 최솟값에 가까운 첫 골짜기 (배음 아래로 떨어지는 옥타브 오류 방지)
    below = np.where(rng < max(thresh, rng.min() + 0.08))[0]
    if len(below):
        i = below[0]
        while i + 1 < len(rng) and rng[i + 1] < rng[i]:
            i += 1
    else:
        i = int(np.argmin(rng))
    tau = i + tau_min
    ap = float(cm[tau])
    # 포물선 보간
    if 1 <= tau < tau_max - 1:
        a, b, c = cm[tau - 1], cm[tau], cm[tau + 1]
        den = a - 2 * b + c
        if abs(den) > 1e-12:
            tau = tau + 0.5 * (a - c) / den
    return fs / tau, ap


def _harm_amp(spec_db, freqs, f, width):
    m = (freqs > f - width) & (freqs < f + width)
    return spec_db[m].max() if m.any() else -120.0


def _cpp(frame, fs, f0):
    n = 4096
    w = np.hanning(len(frame))
    sp = 20 * np.log10(np.abs(np.fft.rfft(frame * w, n)) + 1e-9)
    ceps = np.fft.irfft(sp)
    q = np.arange(len(ceps)) / fs
    lo, hi = 1 / FMAX, 1 / FMIN
    m = (q >= lo) & (q <= hi)
    qq, cc = q[m], ceps[m]
    k = np.argmax(cc)
    # 회귀선 대비 돌출도
    a, b = np.polyfit(qq, cc, 1)
    return float(cc[k] - (a * qq[k] + b)) * 10


def frame_features(x, fs=FS):
    hop = int(HOP * fs)
    win = int(WIN * fs)
    nfr = max(0, (len(x) - win) // hop)
    out = {k: np.zeros(nfr) for k in ("f0", "db", "hnr", "h1h2", "cpp", "tilt", "ap")}
    out["t"] = (np.arange(nfr) * hop + win / 2) / fs
    if nfr == 0:
        return out
    frames = np.lib.stride_tricks.sliding_window_view(x, win)[::hop][:nfr]
    rms = np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-9
    db = 20 * np.log10(rms)
    out["db"] = db
    floor = np.percentile(db, 95) - 35
    hw = np.hanning(win)
    nfft = 8192
    freqs = np.fft.rfftfreq(nfft, 1 / fs)
    for i in range(nfr):
        fr = frames[i]
        if db[i] < floor:
            continue
        f0, ap = _yin(fr, fs)
        out["ap"][i] = ap
        if ap > 0.35:
            continue
        out["f0"][i] = f0
        r = max(1e-4, min(0.9999, 1 - ap))
        out["hnr"][i] = 10 * np.log10(r / (1 - r))
        sp = 20 * np.log10(np.abs(np.fft.rfft(fr * hw, nfft)) + 1e-9)
        out["h1h2"][i] = _harm_amp(sp, freqs, f0, f0 * 0.2) - _harm_amp(sp, freqs, 2 * f0, f0 * 0.2)
        p = 10 ** (sp / 10)
        lo = p[(freqs > 50) & (freqs < 1000)].sum()
        hi = p[(freqs >= 1000) & (freqs < 5000)].sum()
        out["tilt"][i] = 10 * np.log10(hi / lo + 1e-12)
        out["cpp"][i] = _cpp(fr, fs, f0)
    # 고립된 유성 프레임 제거 + 옥타브 튐 보정
    v = out["f0"] > 0
    for i in range(1, nfr - 1):
        if v[i] and not v[i - 1] and not v[i + 1]:
            out["f0"][i] = 0
    f = out["f0"]
    for i in range(2, nfr):
        if f[i] > 0 and f[i - 1] > 0:
            r = f[i] / f[i - 1]
            if 1.8 < r < 2.2:
                f[i] /= 2
            elif 0.45 < r < 0.55:
                f[i] *= 2
    return out


def summarize(feat, mask=None):
    """유성 프레임의 중앙값 요약."""
    v = feat["f0"] > 0
    if mask is not None:
        v &= mask
    if v.sum() == 0:
        return None
    return {k: float(np.median(feat[k][v])) for k in ("f0", "db", "hnr", "h1h2", "cpp", "tilt")}


def notes(feat, min_dur=0.15, jump_semitones=1.2):
    """연속된 유성 구간을 음(note) 단위로 나눔. [(시작 idx, 끝 idx)]"""
    f = feat["f0"]
    v = f > 0
    out = []
    i, n = 0, len(f)
    min_len = int(min_dur / HOP)
    while i < n:
        if not v[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and v[j + 1]:
            j += 1
        # 큰 음정 점프에서 다시 자름 (짧은 중앙값으로 비교)
        seg_start = i
        k = i + 1
        while k <= j:
            a = np.median(f[max(seg_start, k - 5):k])
            b = np.median(f[k:min(j + 1, k + 5)])
            if abs(12 * np.log2(b / a)) > jump_semitones and k - seg_start >= min_len:
                out.append((seg_start, k))
                seg_start = k
                k += 5
            else:
                k += 1
        if j + 1 - seg_start >= min_len:
            out.append((seg_start, j + 1))
        i = j + 1
    return out
