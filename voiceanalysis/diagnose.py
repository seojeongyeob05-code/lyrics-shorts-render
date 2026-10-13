"""추정한 근육 값 + 음향 특징 -> 발성 문제 진단과 교정값.

의학적 진단이 아니라 물리 모델에 비춰 본 발성 습관 추정이다.
"""
import math
import numpy as np

from . import features as F

MUSCLE_NAME = {"ct": "윤상갑상근", "ta": "갑상피열근", "lca": "외측윤상피열근", "ps": "폐압"}
MUSCLE_ROLE = {"ct": "성대를 길게", "ta": "성대를 두껍게", "lca": "성대를 붙임", "ps": "숨이 미는 힘"}

ISSUES = {
    "breathy": {
        "title": "성대 사이로 바람이 새요",
        "muscle": "lca",
        "why": "성대를 가운데로 모으는 외측윤상피열근이 약하게 쓰여서, 진동하는 동안에도 성대 뒤쪽 틈으로 숨이 빠져나가요. "
               "소리로 바뀌지 못한 숨이 쉰 듯한 바람 소리가 되고, 숨도 빨리 떨어져요.",
        "fix": "성대를 조금 더 붙이기 (외측윤상피열근 ↑)",
        "drill": "'음~' 허밍으로 시작해서 입만 열어 '아'로 바꾸기. 또는 아주 가볍게 '앗' 하고 짧게 끊어 내기를 10번. 성대가 붙는 감각을 먼저 찾아요.",
        "caption": "여기서 성대 사이로 바람이 새요",
    },
    "pressed": {
        "title": "성대를 너무 세게 눌러요",
        "muscle": "lca",
        "why": "성대를 모으는 힘(외측윤상피열근)과 두껍게 하는 힘(갑상피열근)이 과해서, 성대가 서로 꽉 눌린 채 떨려요. "
               "소리가 딱딱하고 목이 쉽게 피곤해져요.",
        "fix": "누르는 힘 풀기 (외측윤상피열근·갑상피열근 ↓, 폐압 조금 ↓)",
        "drill": "한숨 쉬듯 'ha~' 로 부드럽게 시작하기. 빨대를 물고 '우~' 소리로 음계 오르내리기(빨대 발성)로 누르는 습관을 풀어요.",
        "caption": "여기서 성대를 꽉 누르고 있어요",
    },
    "pushing": {
        "title": "고음을 숨으로 밀어 올려요",
        "muscle": "ps",
        "why": "음이 올라갈수록 폐압(숨이 미는 힘)이 같이 크게 올라가요. 음높이는 윤상갑상근이 성대를 늘여서 만들어야 하는데, "
               "숨으로 밀어 올리면 소리만 커지고 목에 힘이 들어가요.",
        "fix": "숨 세기는 고정, 음높이는 성대 늘이기로 (폐압 ↓, 윤상갑상근 ↑)",
        "drill": "작은 소리로 '우~' 사이렌을 낮은 음에서 높은 음까지. 소리 크기를 일정하게 둔 채 음만 올리는 연습을 해요.",
        "caption": "음이 올라가면서 숨으로 밀고 있어요",
    },
    "heavy_high": {
        "title": "고음에서도 성대를 두껍게 끌고 가요",
        "muscle": "ta",
        "why": "높은 음에서도 갑상피열근(성대를 두껍게)을 계속 강하게 써서, 늘이는 근육(윤상갑상근)과 서로 당기고 있어요. "
               "고음이 무겁고, 음이 뒤집히거나 목이 조이기 쉬워요.",
        "fix": "올라갈수록 성대를 얇고 가볍게 (갑상피열근 ↓)",
        "drill": "'응(ng)' 소리로 사이렌을 하며 고음으로 갈수록 소리를 가볍게 줄여요. 큰 소리 대신 작은 소리로 고음을 먼저 익혀요.",
        "caption": "고음인데 성대를 두껍게 끌고 있어요",
    },
    "unstable": {
        "title": "음이 흔들려요",
        "muscle": "ps",
        "why": "한 음을 유지하는 동안 음높이가 불규칙하게 흔들려요. 숨이 일정하게 나가지 않거나 근육끼리 균형이 안 맞을 때 생겨요.",
        "fix": "숨을 일정하게, 음은 고정 (폐압 안정)",
        "drill": "튜너를 보면서 편한 음 하나를 5초간 일정하게 유지하기. 크기를 바꾸지 말고 바늘이 가운데 머물게 해요.",
        "caption": "여기서 음이 흔들려요",
    },
    "fading": {
        "title": "프레이즈 끝에서 힘이 빠져요",
        "muscle": "ps",
        "why": "한 숨으로 부르는 구간의 끝에서 소리가 크게 작아져요. 폐압이 끝까지 유지되지 않고 먼저 무너져요.",
        "fix": "프레이즈 끝까지 폐압 유지",
        "drill": "'스~' 소리를 20초간 같은 세기로 내쉬기. 노래할 때도 마지막 음까지 같은 세기를 유지해 봐요.",
        "caption": "프레이즈 끝에서 숨이 무너져요",
    },
}
ORDER = ["pushing", "heavy_high", "pressed", "breathy", "fading", "unstable"]


def _semitones(f):
    return 12 * np.log2(np.asarray(f) / 440.0) + 69


def note_name(f0):
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    m = int(round(float(_semitones(f0))))
    return f"{names[m % 12]}{m // 12 - 1}"


def _pitch_stability(f0, hop=F.HOP):
    """음 하나의 흔들림 (cent, 비브라토 제외 여부)."""
    c = 1200 * np.log2(f0 / np.median(f0))
    k = max(3, int(0.12 / hop) | 1)
    pad = np.pad(c, k // 2, mode="edge")
    smooth = np.convolve(pad, np.ones(k) / k, mode="valid")
    res = c - smooth[:len(c)]
    n = len(res)
    if n < 16:
        return float(np.std(res)), False
    sp = np.abs(np.fft.rfft(res * np.hanning(n))) ** 2
    fr = np.fft.rfftfreq(n, hop)
    band = (fr >= 4.0) & (fr <= 7.5)
    vib = sp[band].sum() / (sp[1:].sum() + 1e-12) > 0.5 and 15 < np.std(res) * 1.41 < 130
    return float(np.std(res)), bool(vib)


def diagnose(notes, phrases, feat):
    """notes: [{t0,t1,dur,f0,feat...,fit{ct,ta,lca,ps}}]. 반환: (issues, per-note flags)"""
    dur = np.array([n["dur"] for n in notes])
    total = dur.sum()
    P = {k: np.array([n["fit"][k] for n in notes]) for k in ("ct", "ta", "lca", "ps")}
    st = _semitones([n["f0"] for n in notes])
    db = np.array([n["db"] for n in notes])
    flags = [set() for _ in notes]
    found = {}

    # 바람 샘
    m = P["lca"] < 0.3
    if dur[m].sum() / total >= 0.25:
        found["breathy"] = {"severity": float(dur[m].sum() / total),
                            "evidence": f"바람 섞인 음 {100 * dur[m].sum() / total:.0f}% · "
                                        f"성대 모음 추정 {np.average(P['lca'], weights=dur):.2f} (권장 0.45~0.7)"}
        for i in np.where(m)[0]:
            flags[i].add("breathy")
    # 눌림
    m = (P["lca"] > 0.75) | ((P["ta"] > 0.75) & (P["ps"] > 15))
    if dur[m].sum() / total >= 0.25:
        found["pressed"] = {"severity": float(dur[m].sum() / total),
                            "evidence": f"눌린 음 {100 * dur[m].sum() / total:.0f}% · "
                                        f"성대 모음 추정 {np.average(P['lca'], weights=dur):.2f}"}
        for i in np.where(m)[0]:
            flags[i].add("pressed")
    # 고음 밀어붙이기 / 고음 두꺼운 성대
    if len(notes) >= 4 and st.max() - st.min() >= 4:
        a_ps = np.polyfit(st, P["ps"], 1, w=np.sqrt(dur))[0]
        a_db = np.polyfit(st, db, 1, w=np.sqrt(dur))[0]
        hi = st >= np.percentile(st, 75)
        if a_ps > 0.85 and P["ps"][hi].mean() >= 15:
            sev = float(np.clip(max(a_ps / 1.5, a_db / 2.5), 0.2, 1.0))
            found["pushing"] = {"severity": sev,
                                "evidence": f"반음 올라갈 때마다 폐압 +{a_ps:.1f} cmH₂O, 크기 +{a_db:.1f} dB · "
                                            f"고음 폐압 {P['ps'][hi].mean():.0f} cmH₂O"}
            for i in np.where(hi & (P["ps"] > np.median(P["ps"])))[0]:
                flags[i].add("pushing")
        high = st >= max(np.percentile(st, 75), np.median(st) + 4)
        if high.any() and P["ta"][high].mean() > 0.6:
            found["heavy_high"] = {"severity": float(np.clip((P["ta"][high].mean() - 0.5) * 2, 0.2, 1.0)),
                                   "evidence": f"고음({note_name(440 * 2 ** ((st[high].mean() - 69) / 12))} 근처)에서 "
                                               f"갑상피열근 추정 {P['ta'][high].mean():.2f} (권장 0.5 이하)"}
            for i in np.where(high & (P["ta"] > 0.6))[0]:
                flags[i].add("heavy_high")
    # 음 흔들림 (0.4초 이상 음만)
    devs = []
    for i, n in enumerate(notes):
        if n["dur"] >= 0.4:
            f = feat["f0"][n["i0"]:n["i1"]]
            f = f[f > 0]
            if len(f) > 10:
                s, vib = _pitch_stability(f)
                n["vibrato"] = vib
                if not vib:
                    devs.append((i, s))
    if devs:
        med = float(np.median([s for _, s in devs]))
        if med > 18:
            found["unstable"] = {"severity": float(np.clip((med - 12) / 30, 0.2, 1.0)),
                                 "evidence": f"긴 음 유지할 때 흔들림 ±{med:.0f} cent (좋음: ±12 이하)"}
            for i, s in devs:
                if s > 18:
                    flags[i].add("unstable")
    # 프레이즈 끝 힘 빠짐
    drops = []
    for p in phrases:
        if p["dur"] >= 1.0:
            # 마지막 0.2초(자연스러운 소리 끝맺음)는 빼고 비교
            tail = int(0.25 / F.HOP)
            d = feat["db"][p["i0"]:p["i1"] - tail]
            v = feat["f0"][p["i0"]:p["i1"] - tail] > 0
            d, f = d[v], feat["f0"][p["i0"]:p["i1"] - tail][v]
            if len(d) > 20:
                n = len(d)
                # 멜로디가 내려가서 작아진 것은 빼고 (끝 음이 3반음 이상 낮으면 비교 안 함)
                st_drop = 12 * np.log2(np.median(f[:n // 2]) / np.median(f[int(n * 0.75):]))
                if st_drop <= 3:
                    drops.append((p, float(np.median(d[int(n * 0.75):]) - np.median(d[:n // 2]))))
    if drops:
        bad = [p for p, x in drops if x < -6]
        if len(bad) / len(drops) >= 0.4:
            found["fading"] = {"severity": float(np.clip(len(bad) / len(drops), 0.2, 1.0)),
                               "evidence": f"프레이즈 {len(drops)}개 중 {len(bad)}개가 끝에서 "
                                           f"평균 {-np.median([x for p, x in drops if x < -6]):.0f} dB 작아짐"}
            for p in bad:
                for i, n in enumerate(notes):
                    if n["t0"] >= p["t0"] + 0.75 * p["dur"] and n["t1"] <= p["t1"] + 0.01:
                        flags[i].add("fading")

    issues = []
    for k in ORDER:
        if k in found:
            issues.append({"id": k, **ISSUES[k], **found[k]})
    issues.sort(key=lambda x: -x["severity"])
    return issues, flags


def correct(fit, issues_ids, ps_med, ct_hint=None):
    """음 하나의 추정 근육 값 -> 교정 근육 값 (음높이는 나중에 ct 로 다시 맞춤)."""
    c = dict(fit)
    if "breathy" in issues_ids:
        c["lca"] = max(c["lca"], 0.55)
    if "pressed" in issues_ids:
        c["lca"] = min(c["lca"], 0.7)
        c["ta"] = min(c["ta"], 0.55)
        c["ps"] = min(c["ps"], 13.0)
    if "pushing" in issues_ids:
        c["ps"] = min(15.0, ps_med + 0.3 * (c["ps"] - ps_med))
    if "heavy_high" in issues_ids:
        ct = fit["ct"] if ct_hint is None else ct_hint
        if ct > 0.45:
            c["ta"] = min(c["ta"], max(0.15, 0.5 - 0.6 * (ct - 0.45)))
    # 공통 안전 범위: 극단값은 권장 범위 쪽으로
    c["lca"] = float(np.clip(c["lca"], 0.4, 0.8))
    c["ps"] = float(np.clip(c["ps"], 5.0, 20.0))
    return c


def overall_score(issues):
    s = 100.0
    w = {"pushing": 22, "heavy_high": 18, "pressed": 20, "breathy": 18, "fading": 12, "unstable": 12}
    for it in issues:
        s -= w[it["id"]] * (0.5 + 0.5 * it["severity"])
    return int(round(max(30.0, s)))
