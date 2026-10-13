"""정답을 아는 테스트 녹음 만들기: 물리엔진으로 습관별 목소리를 합성.

python3 tests/make_test_voices.py out/testvoices
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vocalsim import engine  # noqa: E402
from render.timeline import Timeline  # noqa: E402
from render.pipeline import write_wav, clean_audio  # noqa: E402

CT = [0.15, 0.3, 0.45, 0.6, 0.75, 0.85, 0.7, 0.5, 0.3, 0.15]


def melody(style):
    keys = [[0.0, {"ps": 0, "ct": CT[0], "ta": 0.35, "lca": 0.55, "vib": 0.0}]]
    t = 0.3
    for i, ct in enumerate(CT):
        hi = (ct - 0.15) / 0.7
        p = {"ct": ct, "ta": 0.35, "lca": 0.55, "ps": 9.0}
        if style == "breathy":
            p["lca"] = 0.12
        if style == "pushing":
            p["ps"] = 8 + 16 * hi
            p["ta"] = 0.35 + 0.6 * hi
        if style == "pressed":
            p["lca"] = 0.95
            p["ta"] = 0.85
            p["ps"] = 17
        if i == 5:  # 숨 쉬기
            keys.append([t - 0.05, {"ps": 0}])
            t += 0.4
        keys.append([t, {**p, "ps": 0 if i in (0, 5) else p["ps"]}] if i in (0, 5) else [t, p])
        keys.append([t + 0.12, p])
        keys.append([t + 0.62, p])
        t += 0.7
    keys.append([t, {"ps": 0}])
    return {"voice": {"base": 1.3, "seed": 11}, "segments": [{"dur": t + 0.4, "keys": keys}]}


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    for style in ("healthy", "breathy", "pushing", "pressed"):
        tl = Timeline(melody(style))
        sim = engine.synthesize(tl.controls(), base=1.3, seed=11)
        _, audio = clean_audio(sim["audio"])
        p = os.path.join(outdir, f"{style}.wav")
        write_wav(p, audio, sim["fs"])
        print("저장:", p)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out/testvoices")
