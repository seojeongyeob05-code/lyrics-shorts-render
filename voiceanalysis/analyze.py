"""녹음 한 개를 분석: 특징 -> 근육 역추정 -> 진단 -> 원래/교정 근육 궤적 -> 재합성."""
import math
import numpy as np

from vocalsim import engine, tract
from render import analysis as ra
from render.timeline import PARAMS
from . import features as F
from .inverse import Inverter, ct_for_f0, CT_MAX
from .diagnose import diagnose, correct, overall_score, note_name, ISSUES

MAX_SECONDS = 60.0
BREATH_GAP = 0.12   # 이보다 긴 무성 구간은 숨 쉼으로 처리 (폐압 0)
PHRASE_GAP = 0.25


def _phrases(feat):
    v = feat["f0"] > 0
    out = []
    i, n = 0, len(v)
    gap = int(PHRASE_GAP / F.HOP)
    while i < n:
        if not v[i]:
            i += 1
            continue
        j = i
        last = i
        while j < n and (v[j] or j - last <= gap):
            if v[j]:
                last = j
            j += 1
        out.append({"i0": i, "i1": last + 1, "t0": i * F.HOP, "t1": (last + 1) * F.HOP,
                    "dur": (last + 1 - i) * F.HOP})
        i = last + 1
    return out


class Tracks:
    """10 ms 간격 근육 궤적. render.timeline.Timeline 과 같은 인터페이스 (그리기용)."""

    def __init__(self, t, vals, segments, vowel="a", vib=None):
        self.t = t
        self.vals = vals
        self.vals["vib"] = np.zeros_like(t) if vib is None else vib
        self.duration = float(t[-1]) if len(t) else 0.0
        self.segments = segments
        self.diam = tract.diameter(vowel)

    def value(self, p, t):
        return float(np.interp(t, self.t, self.vals[p]))

    def diameter(self, t):
        return self.diam

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

    def controls(self, fs=engine.FS, block=engine.BLOCK):
        nb = int(math.ceil(self.duration * fs / block))
        tb = np.arange(nb) * block / fs
        v = {p: np.interp(tb, self.t, self.vals[p]) for p in PARAMS}
        diam = np.tile(self.diam, (nb, 1))
        return engine.Controls(v["ct"], v["ta"], v["lca"], v["ps"], diam, v["vib"])


def _smooth(x, k):
    if k <= 1:
        return x
    pad = np.pad(x, k // 2, mode="edge")
    return np.convolve(pad, np.ones(k) / k, mode="valid")[:len(x)]


def build_tracks(feat, notes, which, base, inv, f0_target=None):
    """notes[i][which] 의 (ta, lca, ps) 를 이어 붙이고, ct 는 매 프레임 음높이에서 역산."""
    n = len(feat["f0"])
    f0 = feat["f0"] if f0_target is None else f0_target
    out = {k: np.zeros(n) for k in ("ct", "ta", "lca", "ps")}
    owner = -np.ones(n, int)
    for i, nt in enumerate(notes):
        owner[nt["i0"]:nt["i1"]] = i
    # 같은 phrase 안 짧은 무성 구간은 이웃 음 값 유지
    last = None
    gap = 0
    for k in range(n):
        if owner[k] >= 0:
            last = owner[k]
            gap = 0
        else:
            gap += 1
            if last is not None and f0[k] > 0:
                owner[k] = last
    for k in range(n):
        if owner[k] >= 0:
            p = notes[owner[k]][which]
            out["ta"][k], out["lca"][k], out["ps"][k] = p["ta"], p["lca"], p["ps"]
    # 무성 구간: 짧으면 앞뒤 값으로 메우고 (자음), 길면 숨 쉼 (폐압 0)
    voiced = owner >= 0
    idx = np.where(voiced)[0]
    if len(idx) == 0:
        return out
    for key in ("ta", "lca"):
        out[key] = np.interp(np.arange(n), idx, out[key][idx])
    ps = np.interp(np.arange(n), idx, out["ps"][idx])
    run = 0
    breath = np.zeros(n, bool)
    k = 0
    while k < n:
        if voiced[k]:
            k += 1
            continue
        j = k
        while j < n and not voiced[j]:
            j += 1
        if (j - k) * F.HOP > BREATH_GAP or k == 0 or j == n:
            breath[k:j] = True
        k = j
    ps[breath] = 0.0
    out["ps"] = _smooth(ps, 5)
    # ct: 음높이에서 역산 (무성 구간은 이웃 값)
    ct = np.zeros(n)
    have = np.zeros(n, bool)
    for k in range(n):
        if f0[k] > 0 and voiced[k]:
            ct[k] = ct_for_f0(f0[k], out["ta"][k], out["lca"][k], max(out["ps"][k], 3.0), base, inv.coef)[0]
            have[k] = True
    hk = np.where(have)[0]
    if len(hk):
        ct = np.interp(np.arange(n), hk, ct[hk])
    out["ct"] = _smooth(ct, 3)
    return out


def synth_tracks(t, tr, base, f0_target, inv, iters=2, seed=5):
    """궤적으로 합성하고, 실제로 나온 음높이와 목표 음높이 차이만큼 ct 를 고쳐 다시 합성."""
    tr = {k: v.copy() for k, v in tr.items()}
    for it in range(iters + 1):
        tl = Tracks(t, dict(tr), [{"start": 0, "end": 1e9, "captions": []}])
        ctrl = tl.controls()
        sim = engine.synthesize(ctrl, base=base, seed=seed)
        if it == iters:
            return sim, ctrl, tr
        fs = sim["fs"]
        meas = np.array([ra.f0_at(sim["x1"], fs, min(int(x * fs), len(sim["x1"]) - 1)) or 0.0 for x in t])
        ok = (meas > 0) & (f0_target > 0)
        err = np.zeros_like(t)
        err[ok] = np.log(f0_target[ok] / meas[ok])
        err = _smooth(np.clip(err, -0.5, 0.5), 7)
        slope = 1.02 + inv.coef[1] + 2 * inv.coef[5] * tr["ct"] + inv.coef[6] * tr["ta"]
        tr["ct"] = np.clip(tr["ct"] + np.where(f0_target > 0, err / np.maximum(slope, 0.5), 0), 0, CT_MAX)


def analyze(path, inv=None, max_seconds=MAX_SECONDS):
    inv = inv or Inverter()
    x = F.load_audio(path)[: int(max_seconds * F.FS)]
    feat = F.frame_features(x)
    v = feat["f0"] > 0
    if v.sum() < 30:
        raise ValueError("목소리(유성음)를 거의 찾지 못했어요. 조용한 곳에서 노래나 '아~' 소리를 녹음해 주세요.")
    note_idx = F.notes(feat)
    base = inv.estimate_base(float(np.median(feat["f0"][v])), float(np.percentile(feat["f0"][v], 2)))
    db_med = float(np.median(feat["db"][v]))
    notes = []
    for i0, i1 in note_idx:
        m = np.zeros(len(feat["f0"]), bool)
        m[i0:i1] = True
        s = F.summarize(feat, m)
        if s is None:
            continue
        fit = inv.fit_note(s, base, s["db"] - db_med)
        notes.append({"i0": i0, "i1": i1, "t0": i0 * F.HOP, "t1": i1 * F.HOP, "dur": (i1 - i0) * F.HOP,
                      **s, "fit": fit})
    phrases = _phrases(feat)
    issues, flags = diagnose(notes, phrases, feat)
    ids = {it["id"] for it in issues}
    ps_med = float(np.median([n["fit"]["ps"] for n in notes]))
    for n, fl in zip(notes, flags):
        n["flags"] = sorted(fl)
        local = set(fl) | (ids & {"pushing"})
        if "breathy" in ids and n["fit"]["lca"] < 0.4:
            local.add("breathy")
        n["fixed"] = correct(n["fit"], local, ps_med) if local else dict(n["fit"])
    # 프레이즈 끝 힘 빠짐: 교정에서는 프레이즈 앞부분 폐압 유지
    if "fading" in ids:
        for p in phrases:
            inside = [n for n in notes if n["t0"] >= p["t0"] - 1e-6 and n["t1"] <= p["t1"] + 1e-6]
            if len(inside) >= 2:
                keep = float(np.median([n["fixed"]["ps"] for n in inside[: max(1, len(inside) // 2)]]))
                for n in inside[len(inside) // 2:]:
                    n["fixed"]["ps"] = max(n["fixed"]["ps"], keep * 0.95)
    # 교정 음높이: 흔들림이 문제면 비브라토 아닌 흔들림만 매끄럽게
    f0_fix = feat["f0"].copy()
    if "unstable" in ids:
        for n in notes:
            if not n.get("vibrato"):
                seg = f0_fix[n["i0"]:n["i1"]]
                ok = seg > 0
                if ok.sum() > 5:
                    c = 1200 * np.log2(seg[ok] / np.median(seg[ok]))
                    c = _smooth(c, 15)
                    seg[ok] = np.median(seg[ok]) * 2 ** (c / 1200)
    t = feat["t"]
    tr_fit = build_tracks(feat, notes, "fit", base, inv)
    tr_fix = build_tracks(feat, notes, "fixed", base, inv, f0_target=f0_fix)
    v = f0_fix > 0
    st = 12 * np.log2(feat["f0"][v] / 440) + 69
    lo_hz = 440 * 2 ** ((np.percentile(st, 5) - 69) / 12)
    hi_hz = 440 * 2 ** ((np.percentile(st, 95) - 69) / 12)
    avg = {k: float(np.average([n["fit"][k] for n in notes], weights=[n["dur"] for n in notes]))
           for k in ("ct", "ta", "lca", "ps")}
    avg_fix = {k: float(np.average([n["fixed"][k] for n in notes], weights=[n["dur"] for n in notes]))
               for k in ("ct", "ta", "lca", "ps")}
    return {
        "path": path, "audio": x, "feat": feat, "notes": notes, "phrases": phrases,
        "issues": issues, "score": overall_score(issues), "base": base,
        "range": (note_name(lo_hz), note_name(hi_hz)), "median_note": note_name(float(np.median(feat["f0"][v]))),
        "avg": avg, "avg_fixed": avg_fix, "t": t, "tracks_fit": tr_fit, "tracks_fixed": tr_fix,
        "f0_fixed": f0_fix, "inv": inv,
    }


def report_dict(res):
    return {
        "file": res["path"],
        "score": res["score"],
        "range": res["range"],
        "median_note": res["median_note"],
        "voice_base": round(res["base"], 3),
        "muscles_estimated": {k: round(v, 3) for k, v in res["avg"].items()},
        "muscles_corrected": {k: round(v, 3) for k, v in res["avg_fixed"].items()},
        "issues": [{k: it[k] for k in ("id", "title", "severity", "evidence", "why", "fix", "drill", "muscle")}
                   for it in res["issues"]],
        "notes": [{"t0": round(n["t0"], 2), "t1": round(n["t1"], 2), "note": note_name(n["f0"]),
                   "f0": round(n["f0"], 1), "hnr": round(n["hnr"], 1), "h1h2": round(n["h1h2"], 1),
                   "cpp": round(n["cpp"], 1), "tilt": round(n["tilt"], 1),
                   "fit": {k: round(v, 3) for k, v in n["fit"].items() if k in ("ct", "ta", "lca", "ps")},
                   "fixed": {k: round(v, 3) for k, v in n["fixed"].items() if k in ("ct", "ta", "lca", "ps")},
                   "flags": n["flags"]} for n in res["notes"]],
    }


def report_markdown(res):
    from .diagnose import MUSCLE_NAME, MUSCLE_ROLE
    L = [f"# 발성 분석 결과 — 균형 점수 {res['score']}점", ""]
    L.append(f"- 음역: {res['range'][0]} ~ {res['range'][1]} (중심 {res['median_note']})")
    L.append("- 추정 근육 사용 (0~1, 폐압은 cmH₂O) → 교정값")
    for k in ("ct", "ta", "lca", "ps"):
        a, b = res["avg"][k], res["avg_fixed"][k]
        fmt = "{:.0f}" if k == "ps" else "{:.2f}"
        L.append(f"  - {MUSCLE_NAME[k]} ({MUSCLE_ROLE[k]}): {fmt.format(a)} → {fmt.format(b)}")
    L.append("")
    if not res["issues"]:
        L.append("## 큰 문제 없이 균형 잡힌 발성이에요")
        L.append("지금처럼 숨·성대·공명이 고르게 쓰이고 있어요. 음역 끝에서도 같은 균형을 유지하는 연습을 이어가 보세요.")
    for i, it in enumerate(res["issues"], 1):
        L += [f"## {i}. {it['title']}", "",
              f"- 근거: {it['evidence']}",
              f"- 몸에서 일어나는 일: {it['why']}",
              f"- 고치는 방향: {it['fix']}",
              f"- 연습: {it['drill']}", ""]
    L += ["---", "물리 모델로 추정한 발성 습관이며 의학적 진단이 아니에요. "
          "목의 통증이나 쉰 목소리가 2주 넘게 이어지면 이비인후과 진료를 받아 주세요."]
    return "\n".join(L)
