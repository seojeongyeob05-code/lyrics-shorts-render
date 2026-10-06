#!/usr/bin/env python3
"""가상 성대 · 발성 물리엔진 쇼츠 만들기.

사용법:
  python3 make_short.py scenarios/default.json -o out/short.mp4
  python3 make_short.py scenarios/default.json --stills 3,20,45   # 특정 시점 PNG 만 확인
"""
import argparse
import math
import multiprocessing as mp
import os
import subprocess
import sys
import time
import wave

import numpy as np

from vocalsim import engine
from vocalsim.muscles import fold_params, D1
from render import analysis, frame as fr
from render.timeline import Timeline, load, PARAMS

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


def prepare(sc_path, limit=None):
    sc = load(sc_path)
    tl = Timeline(sc)
    if limit:
        tl.duration = min(tl.duration, limit)
    voice = sc.get("voice", {})
    base = float(voice.get("base", 1.6))
    t0 = time.time()
    ctrl = tl.controls()
    sim = engine.synthesize(ctrl, base=base, seed=int(voice.get("seed", 1)))
    fs, block = sim["fs"], sim["block"]
    print(f"합성 {tl.duration:.1f}s ({time.time() - t0:.1f}s 걸림)")

    raw = sim["audio"]
    # 직류/저역 제거 + 부드러운 시작
    raw = raw - np.convolve(raw, np.ones(441) / 441, mode="same")
    # 보통 발성 크기를 기준으로 맞추고, 큰 소리는 부드럽게 눌러 줌
    env = np.sqrt(np.convolve(raw ** 2, np.ones(2205) / 2205, mode="same"))
    voiced = env[env > env.max() * 0.05]
    ref = np.median(voiced) if len(voiced) else env.max() + 1e-9
    audio = 0.95 * np.tanh(raw / ref * 0.16 / 0.95)

    lung = analysis.lung_volume(sim["u"], ctrl.ps, fs, block)
    n_frames = int(tl.duration * FPS)
    frames = []
    for fi in range(n_frames):
        t = fi / FPS
        n = min(int(t * fs), len(raw) - 1)
        b = min(n // block, len(ctrl.ct) - 1)
        c = {p: tl.value(p, t) for p in PARAMS}
        f0 = analysis.f0_at(sim["x1"], fs, n)
        db = analysis.level_db(raw, fs, n)
        # 슬로모션 성대 위치: 지금 직전 한 주기 안에서 위상만 천천히 진행
        if f0:
            P = fs / f0
            ph = (t * SLOW_HZ) % 1.0
            k = int(n - P + ph * P)
            k = max(0, min(len(raw) - 1, k))
            fx1, fx2, slow = float(sim["x1"][k]), float(sim["x2"][k]), f0 / SLOW_HZ
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
    spec = analysis.spectrogram(raw, fs, pxs, spec_h)
    data = {"frames": frames, "spec": spec, "spec_pxs": pxs,
            "title": sc.get("title", "가상 성대 · 발성 물리엔진"),
            "tag": sc.get("tag", "모델 소리(합성)")}
    return data, audio, fs


def _render(fi):
    return _R.frame(fi).tobytes()


def main():
    global _R
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("-o", "--out", default="out/short.mp4")
    ap.add_argument("--stills", help="쉼표로 구분한 초 단위 시점. PNG 만 저장")
    ap.add_argument("--limit", type=float, help="앞에서부터 이 길이(초)만 렌더")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    data, audio, fs = prepare(args.scenario, args.limit)
    _R = fr.Renderer(data)
    stem = os.path.splitext(args.out)[0]
    wav = stem + ".wav"
    write_wav(wav, audio, fs)

    if args.stills:
        for s in args.stills.split(","):
            fi = min(int(float(s) * FPS), len(data["frames"]) - 1)
            p = f"{stem}_{float(s):05.1f}s.png"
            _R.frame(fi).save(p)
            print("저장:", p)
        return

    n = len(data["frames"])
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{fr.W}x{fr.H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with mp.get_context("fork").Pool(args.jobs) as pool:
        for i, buf in enumerate(pool.imap(_render, range(n), chunksize=4)):
            proc.stdin.write(buf)
            if i % 150 == 0:
                el = time.time() - t0
                print(f"\r{i}/{n} 프레임 ({el:.0f}s)", end="", file=sys.stderr, flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\n완료: {args.out} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
