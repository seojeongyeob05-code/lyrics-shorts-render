"""타임라인 + 시뮬레이션 -> 프레임 데이터 -> mp4. make_short / analyze_voice 공용."""
import multiprocessing as mp
import os
import subprocess
import sys
import time
import wave

import numpy as np

from vocalsim.muscles import fold_params, D1
from render import analysis, frame as fr
from render.timeline import PARAMS

FPS = 30
SLOW_HZ = 1.0  # 슬로모션에서 초당 보여줄 진동 횟수

_R = None  # 워커 공유용 (fork)


def write_wav(path, audio, fs):
    pcm = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes(pcm.tobytes())


def clean_audio(raw):
    """직류 제거 + 보통 발성 크기 기준 정규화, 큰 소리는 부드럽게 눌러 줌."""
    raw = raw - np.convolve(raw, np.ones(441) / 441, mode="same")
    env = np.sqrt(np.convolve(raw ** 2, np.ones(2205) / 2205, mode="same"))
    voiced = env[env > env.max() * 0.05]
    ref = np.median(voiced) if len(voiced) else env.max() + 1e-9
    return raw, 0.95 * np.tanh(raw / ref * 0.16 / 0.95)


def build_data(tl, ctrl, sim, base, title, tag, shown=None, shown_f0=None, db_offset=None):
    """프레임별 상태 목록 + 스펙트로그램.

    shown: 화면/소리에 쓸 오디오 (없으면 합성음). 녹음을 보여줄 때는 녹음을 넣고,
           성대/폐 그림은 그 녹음에 맞춘 합성(sim)으로 그린다.
    shown_f0: (t, f0) 배열. 음높이 표시를 녹음 분석값으로 할 때.
    """
    fs, block = sim["fs"], sim["block"]
    raw = sim["audio"]
    show = raw if shown is None else shown
    lung = analysis.lung_volume(sim["u"], ctrl.ps, fs, block)
    n_frames = int(tl.duration * FPS)
    frames = []
    for fi in range(n_frames):
        t = fi / FPS
        n = min(int(t * fs), len(raw) - 1)
        b = min(n // block, len(ctrl.ct) - 1)
        c = {p: tl.value(p, t) for p in PARAMS}
        f0_sim = analysis.f0_at(sim["x1"], fs, n)
        if shown_f0 is not None:
            ft, ff = shown_f0
            k = int(np.clip(np.searchsorted(ft, t), 0, len(ff) - 1))
            f0 = float(ff[k]) if ff[k] > 0 else None
        else:
            f0 = f0_sim
        ns = min(int(t * fs), len(show) - 1)
        db = analysis.level_db(show, fs, ns)
        if db is not None and db_offset is not None:
            db += db_offset
        # 슬로모션 성대 위치: 지금 직전 한 주기 안에서 위상만 천천히 진행
        if f0_sim:
            P = fs / f0_sim
            ph = (t * SLOW_HZ) % 1.0
            k = int(np.clip(n - P + ph * P, 0, len(raw) - 1))
            fx1, fx2, slow = float(sim["x1"][k]), float(sim["x2"][k]), f0_sim / SLOW_HZ
        else:
            fx1, fx2, slow = float(sim["x1"][n]), float(sim["x2"][n]), 0
        w = int(0.025 * fs)
        tr = sim["u"][max(0, n - w): n + 1][::4]
        fp = fold_params(c["ct"], c["ta"], c["lca"], max(c["ps"], 0.1), base)
        frames.append({
            "t": t, "seg": tl.segment_at(t), "caption": tl.caption_at(t),
            "ctrl": c, "diam": tl.diameter(t), "f0": f0, "db": db,
            "lung": float(lung[b]), "u": float(sim["u"][max(0, n - 600): n + 1].mean()),
            "utrace": tr, "fx1": fx1, "fx2": fx2, "slow": slow,
            "a0": float(sim["a0"][b]), "l": float(sim["l"][b]),
            "thick": fp.d1 / D1,
        })
    spec_h = (fr.H - fr.SPEC_IMG_TOP) * fr.S
    pxs = 216 * fr.S  # 5초 = 화면 폭
    spec = analysis.spectrogram(show, fs, pxs, spec_h)
    return {"frames": frames, "spec": spec, "spec_pxs": pxs, "title": title, "tag": tag}


def _render(fi):
    return _R.frame(fi).tobytes()


def render_video(data, wav, out, jobs=None):
    global _R
    _R = fr.Renderer(data)
    n = len(data["frames"])
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{fr.W}x{fr.H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
           "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with mp.get_context("fork").Pool(jobs or os.cpu_count()) as pool:
        for i, buf in enumerate(pool.imap(_render, range(n), chunksize=4)):
            proc.stdin.write(buf)
            if i % 150 == 0:
                print(f"\r{i}/{n} 프레임 ({time.time() - t0:.0f}s)", end="", file=sys.stderr, flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\n완료: {out} ({time.time() - t0:.0f}s)", file=sys.stderr)


def save_stills(data, stem, times):
    r = fr.Renderer(data)
    paths = []
    for s in times:
        fi = min(int(float(s) * FPS), len(data["frames"]) - 1)
        p = f"{stem}_{float(s):05.1f}s.png"
        r.frame(fi).save(p)
        paths.append(p)
    return paths


def still_video(img_path, seconds, out):
    """정지 이미지 + 무음 -> mp4 (다른 조각과 이어 붙이기 위해 같은 형식)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", img_path,
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(seconds),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
           "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)


def concat_videos(parts, out):
    inputs = []
    for p in parts:
        inputs += ["-i", p]
    fc = "".join(f"[{i}:v][{i}:a]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=1[v][a]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
