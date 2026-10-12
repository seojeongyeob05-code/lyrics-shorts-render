#!/usr/bin/env python3
"""가상 성대 · 발성 물리엔진 쇼츠 만들기 (시나리오 JSON -> mp4).

사용법:
  python3 make_short.py scenarios/default.json -o out/short.mp4
  python3 make_short.py scenarios/default.json --stills 3,20,45   # 특정 시점 PNG 만 확인
"""
import argparse
import os
import time

from vocalsim import engine
from render import pipeline
from render.timeline import Timeline, load


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
    print(f"합성 {tl.duration:.1f}s ({time.time() - t0:.1f}s 걸림)")
    sim["audio"], audio = pipeline.clean_audio(sim["audio"])
    data = pipeline.build_data(tl, ctrl, sim, base,
                               sc.get("title", "가상 성대 · 발성 물리엔진"),
                               sc.get("tag", "모델 소리(합성)"))
    return data, audio, sim["fs"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("-o", "--out", default="out/short.mp4")
    ap.add_argument("--stills", help="쉼표로 구분한 초 단위 시점. PNG 만 저장")
    ap.add_argument("--limit", type=float, help="앞에서부터 이 길이(초)만 렌더")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    data, audio, fs = prepare(args.scenario, args.limit)
    stem = os.path.splitext(args.out)[0]
    wav = stem + ".wav"
    pipeline.write_wav(wav, audio, fs)

    if args.stills:
        for p in pipeline.save_stills(data, stem, args.stills.split(",")):
            print("저장:", p)
        return
    pipeline.render_video(data, wav, args.out, args.jobs)


if __name__ == "__main__":
    main()
