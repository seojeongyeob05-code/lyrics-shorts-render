"""시나리오(JSON) -> 블록 단위 근육 제어값 + 구간/자막 정보."""
import json
import math
import numpy as np

from vocalsim import engine, tract
from vocalsim.muscles import NEUTRAL

PARAMS = ("ct", "ta", "lca", "ps", "vib")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _smooth(u):
    return 0.5 - 0.5 * math.cos(math.pi * u)


def _interp(points, t):
    """points: [(time, value)] 정렬됨. 코사인 보간."""
    if t <= points[0][0]:
        return points[0][1]
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if t <= t1:
            if t1 <= t0:
                return v1
            return v0 + (v1 - v0) * _smooth((t - t0) / (t1 - t0))
    return points[-1][1]


class Timeline:
    def __init__(self, sc):
        self.sc = sc
        self.segments = []
        start = {**NEUTRAL, "ps": 0.0, "vib": 0.0, "vowel": sc.get("voice", {}).get("vowel", "a")}
        tracks = {p: [(0.0, start[p])] for p in PARAMS}
        vowels = [(0.0, start["vowel"])]
        t = 0.0
        for seg in sc["segments"]:
            dur = float(seg["dur"])
            for key in seg.get("keys", []):
                kt, vals = key
                at = t + float(kt)
                for p in PARAMS:
                    if p in vals:
                        tracks[p].append((at, float(vals[p])))
                if "vowel" in vals:
                    vowels.append((at, vals["vowel"]))
            caps = seg.get("captions", [])
            if "caption" in seg:
                caps = [[0, dur, seg["caption"]]]
            self.segments.append({
                "start": t, "end": t + dur,
                "focus": seg.get("focus"),
                "title": seg.get("title"),
                "sub": seg.get("sub"),
                "captions": [(t + float(a), t + float(b), txt) for a, b, txt in caps],
            })
            t += dur
        self.duration = t
        for p in PARAMS:
            tracks[p].sort(key=lambda x: x[0])
        self.tracks = tracks
        self.vowels = vowels

    def value(self, p, t):
        return _interp(self.tracks[p], t)

    def diameter(self, t):
        """모음 전환은 0.25초에 걸쳐 지름을 섞는다."""
        cur = tract.diameter(self.vowels[0][1])
        for at, v in self.vowels[1:]:
            if t < at:
                break
            nxt = tract.diameter(v)
            u = min(1.0, (t - at) / 0.25)
            cur = cur + (nxt - cur) * _smooth(u)
        return cur

    def controls(self, fs=engine.FS, block=engine.BLOCK):
        nb = int(math.ceil(self.duration * fs / block))
        tb = np.arange(nb) * block / fs
        vals = {p: np.array([self.value(p, x) for x in tb]) for p in PARAMS}
        cache = {}
        diam = np.zeros((nb, tract.N))
        for b, x in enumerate(tb):
            k = round(x, 2)
            if k not in cache:
                cache[k] = self.diameter(x)
            diam[b] = cache[k]
        return engine.Controls(vals["ct"], vals["ta"], vals["lca"], vals["ps"], diam, vals["vib"])

    def segment_at(self, t):
        for s in self.segments:
            if s["start"] <= t < s["end"]:
                return s
        return self.segments[-1]

    def caption_at(self, t):
        for s in self.segments:
            for a, b, txt in s["captions"]:
                if a <= t < b:
                    return txt, a, b
        return None
