#!/usr/bin/env python3
"""녹음 파일 -> 발성 분석 (리포트 + 교정 소리 + 쇼츠 영상).

사용법:
  python3 analyze_voice.py 내녹음.m4a                 # out/analysis/<파일이름>/ 에 결과 저장
  python3 analyze_voice.py 내녹음.m4a --no-video      # 리포트와 소리만 빠르게

결과물
  report.md / report.json   진단 내용
  card.png                  결과 카드 (영상 첫 화면)
  fitted.wav                내 녹음을 물리엔진으로 다시 계산한 소리
  corrected.wav             같은 음정을 교정한 근육 값으로 낸 소리
  analysis.mp4              결과 카드 → 내 소리 → 고친 소리 (9:16)
"""
import argparse
import json
import os
import sys
import time

import numpy as np

from render import pipeline
from render.report_card import render_card
from voiceanalysis import features as F
from voiceanalysis.analyze import analyze, report_dict, report_markdown, synth_tracks, Tracks
from voiceanalysis.diagnose import ISSUES, MUSCLE_NAME, MUSCLE_ROLE, ORDER

VIDEO_SECONDS = 25.0
CARD_SECONDS = 6.0
RECOMMEND_UI = {"ct": 0.4, "ta": 0.4, "lca": 0.58, "ps": 10.0}


def _cut(res, seconds):
    """영상용: 앞 seconds 초만 쓰도록 궤적/오디오 자르기."""
    n = int(np.searchsorted(res["t"], seconds))
    t = res["t"][:n]
    fit = {k: v[:n] for k, v in res["tracks_fit"].items()}
    fix = {k: v[:n] for k, v in res["tracks_fixed"].items()}
    return t, fit, fix, res["feat"]["f0"][:n], res["f0_fixed"][:n]


def _captions(res, seconds, kind):
    """문제가 있던 음 위치에 자막. kind: 'mine' | 'fixed'"""
    caps = []
    for n in res["notes"]:
        if n["t0"] >= seconds or not n["flags"]:
            continue
        fl = sorted(n["flags"], key=ORDER.index)[0]
        it = ISSUES[fl]
        txt = it["caption"] if kind == "mine" else f"{it['fix'].split(' (')[0]} → 이렇게 들려요"
        t1 = min(n["t1"], seconds)
        if caps and caps[-1][2] == txt and n["t0"] - caps[-1][1] < 0.6:
            caps[-1][1] = t1
        else:
            caps.append([n["t0"], t1, txt])
    # 너무 짧은 자막은 최소 1.6초 보이게
    out = []
    for a, b, txt in caps:
        b = max(b, a + 1.6)
        if out and a < out[-1][1]:
            a = out[-1][1]
        if b - a >= 0.8:
            out.append([a, b, txt])
    if not out or out[0][0] > 2.2:
        first = "내 녹음을 물리엔진으로 거꾸로 계산했어요" if kind == "mine" else "같은 음정, 근육만 고쳐서 다시 낸 소리예요"
        out.insert(0, [0.0, 2.2 if not out else min(2.2, out[0][0]), first])
    return [(a, b, t) for a, b, t in out]


def render_part(res, kind, t, tr, f0_show, seconds, out_mp4, jobs):
    top = res["issues"][0] if res["issues"] else None
    focus = top["muscle"] if top else "ct"
    if kind == "mine":
        seg = {"start": 0.0, "end": 1e9, "focus": focus,
               "title": "내 소리 · " + MUSCLE_NAME[focus],
               "sub": f"{MUSCLE_ROLE[focus]} · 녹음에서 거꾸로 계산한 값",
               "tick": RECOMMEND_UI[focus], "tick_label": "권장",
               "captions": _captions(res, seconds, "mine")}
    else:
        seg = {"start": 0.0, "end": 1e9, "focus": focus,
               "title": "고친 소리 · " + MUSCLE_NAME[focus],
               "sub": (top["fix"] if top else "지금 균형 그대로") ,
               "tick": res["avg"][focus], "tick_label": "내 소리",
               "captions": _captions(res, seconds, "fixed")}
    inv = res["inv"]
    if kind == "mine":
        sim, ctrl, tr2 = synth_tracks(t, tr, res["base"], f0_show, inv, iters=0)
    else:
        sim, ctrl, tr2 = synth_tracks(t, tr, res["base"], f0_show, inv, iters=2)
    tl = Tracks(t, dict(tr2), [seg])
    raw, clean = pipeline.clean_audio(sim["audio"])
    sim["audio"] = raw
    fs = sim["fs"]
    if kind == "mine":
        user = res["audio"][: int(seconds * fs)]
        uraw, shown = pipeline.clean_audio(user)
        n = min(len(shown), int(tl.duration * fs))
        shown = shown[:n]
        data = pipeline.build_data(tl, ctrl, sim, res["base"], "내 소리", "녹음", shown=uraw[:n],
                                   shown_f0=(res["t"], res["feat"]["f0"]))
        audio = shown
    else:
        data = pipeline.build_data(tl, ctrl, sim, res["base"], "고친 소리", "모델 소리(합성)")
        audio = clean
    wav = out_mp4[:-4] + ".wav"
    pipeline.write_wav(wav, audio, fs)
    pipeline.render_video(data, wav, out_mp4, jobs)
    return audio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("-o", "--outdir")
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--seconds", type=float, default=VIDEO_SECONDS, help="영상에 쓸 녹음 앞부분 길이")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()

    name = os.path.splitext(os.path.basename(args.audio))[0]
    outdir = args.outdir or os.path.join("out", "analysis", name)
    os.makedirs(outdir, exist_ok=True)
    t0 = time.time()
    try:
        res = analyze(args.audio)
    except ValueError as e:
        print(e)
        sys.exit(1)
    print(f"분석 완료 ({time.time() - t0:.1f}s) — 균형 점수 {res['score']}, 문제 {len(res['issues'])}개")
    md = report_markdown(res)
    with open(os.path.join(outdir, "report.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(outdir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report_dict(res), f, ensure_ascii=False, indent=2)
    card = render_card(res, os.path.join(outdir, "card.png"))
    print(md)

    # 전체 길이 재합성 (소리 파일)
    full_t = res["t"]
    for kind, key, f0 in (("fitted", "tracks_fit", res["feat"]["f0"]), ("corrected", "tracks_fixed", res["f0_fixed"])):
        sim, _, _ = synth_tracks(full_t, res[key], res["base"], f0, res["inv"], iters=2 if kind == "corrected" else 0)
        _, a = pipeline.clean_audio(sim["audio"])
        pipeline.write_wav(os.path.join(outdir, f"{kind}.wav"), a, sim["fs"])
    if args.no_video:
        return

    secs = min(args.seconds, float(res["t"][-1]))
    t, fit, fix, f0_user, f0_fix = _cut(res, secs)
    parts = [os.path.join(outdir, "_part0.mp4"), os.path.join(outdir, "_part1.mp4"), os.path.join(outdir, "_part2.mp4")]
    pipeline.still_video(card, CARD_SECONDS, parts[0])
    render_part(res, "mine", t, fit, f0_user, secs, parts[1], args.jobs)
    render_part(res, "fixed", t, fix, f0_fix, secs, parts[2], args.jobs)
    out = os.path.join(outdir, "analysis.mp4")
    pipeline.concat_videos(parts, out)
    for p in parts:
        for q in (p, p[:-4] + ".wav"):
            if os.path.exists(q):
                os.remove(q)
    print(f"\n완료: {outdir}/ (영상 analysis.mp4, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
