"""녹음 특징 -> 근육 값 역추정.

1) 물리엔진으로 근육 값 격자(ct·ta·lca·ps)를 전부 합성해서 같은 특징을 잰 '역추정 표'를 만든다.
2) 녹음의 음(note)마다, 그 음높이를 낼 수 있는 조합 중 특징이 가장 비슷한 것을 찾는다.
3) 음높이는 성대 장력 식을 거꾸로 풀어 ct 로 바꾼다 (ta·lca·ps 가 정해지면 ct 는 음높이로 결정).
"""
import itertools
import math
import multiprocessing as mp
import os

import numpy as np

from vocalsim import engine
from vocalsim.muscles import NEUTRAL
from . import features as F

TABLE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "inverse_table.npz")
GRID = {
    "ct": [0.0, 0.25, 0.5, 0.75, 1.0],
    "ta": [0.0, 0.25, 0.5, 0.75, 1.0],
    "lca": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    "ps": [4.0, 6.0, 9.0, 13.0, 18.0, 25.0],
    "base": [0.8, 1.2, 1.7, 2.3],
}
FEATS = ("f0", "db", "hnr", "h1h2", "cpp", "tilt")
# 특징별 허용 오차 (거리 계산 시 나누는 값)
SCALE = {"hnr": 4.0, "h1h2": 3.0, "cpp": 3.0, "tilt": 4.0, "dbrel": 5.0}
SIM_DUR = 0.45
CT_MAX = 1.4  # 재합성에서 음역 끝을 맞추기 위해 1 을 조금 넘겨도 허용 (표시는 1 로 자름)


def q_factor(ct, ta, lca, ps, base=1.0):
    """muscles.fold_params 와 같은 장력 계수 (음높이에 비례)."""
    e = 0.2 * (3.0 * ct - ta) - 0.2 * lca
    q = base * 0.85 * math.exp(1.7 * e) * (1.0 + 0.45 * ta)
    return q * (1.0 + 0.01 * max(min(ps, 40.0) - 9.0, -9.0))


def _f0_feats(ct, ta, lca, ps):
    return np.array([1.0, ct, ta, lca, ps, ct * ct, ta * ct, math.sqrt(max(ps, 0.0))])


def f0_model(ct, ta, lca, ps, base, coef):
    """장력 계수 q 에 표로 보정한 항을 곱한 음높이 예측 (Hz)."""
    return q_factor(ct, ta, lca, ps, base) * math.exp(float(_f0_feats(ct, ta, lca, ps) @ coef))


def ct_for_f0(f0, ta, lca, ps, base, coef):
    """f0 를 내는 ct 를 이분법으로 찾음 (ct 에 대해 단조 증가). (ct, 범위 안인지)"""
    lo, hi = 0.0, CT_MAX
    if f0 <= f0_model(lo, ta, lca, ps, base, coef):
        return 0.0, f0 >= f0_model(lo, ta, lca, ps, base, coef) * 0.97
    if f0 >= f0_model(hi, ta, lca, ps, base, coef):
        return hi, False
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if f0_model(mid, ta, lca, ps, base, coef) < f0:
            lo = mid
        else:
            hi = mid
    ct = 0.5 * (lo + hi)
    return ct, ct <= 1.0


def _sim_one(p):
    ct, ta, lca, ps, base = p
    nb = int(SIM_DUR * engine.FS / engine.BLOCK)
    c = engine.Controls([ct] * nb, [ta] * nb, [lca] * nb, [ps] * nb, engine.default_diam(nb))
    a = engine.synthesize(c, base=base, seed=3)["audio"][int(0.15 * engine.FS):]
    s = F.summarize(F.frame_features(a))
    if s is None:
        return [np.nan] * len(FEATS)
    return [s[k] for k in FEATS]


def build_table(path=TABLE_PATH, jobs=None):
    params = list(itertools.product(GRID["ct"], GRID["ta"], GRID["lca"], GRID["ps"], GRID["base"]))
    with mp.get_context("fork").Pool(jobs or os.cpu_count()) as pool:
        feats = pool.map(_sim_one, params, chunksize=8)
    P = np.array(params, float)
    X = np.array(feats, float)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    np.savez_compressed(path, params=P, feats=X, names=np.array(FEATS))
    return P, X


def load_table(path=TABLE_PATH):
    if not os.path.exists(path):
        print("역추정 표가 없어 새로 만듭니다 (1~2분)...")
        return build_table(path)
    d = np.load(path)
    return d["params"], d["feats"]


class Inverter:
    def __init__(self, path=TABLE_PATH):
        P, X = load_table(path)
        ok = ~np.isnan(X).any(axis=1) & (X[:, 0] > 0)
        self.P, self.X = P[ok], X[ok]
        fi = {k: i for i, k in enumerate(FEATS)}
        self.fi = fi
        # 음높이 보정식: log(f0 / q) 를 근육 값의 간단한 함수로 회귀
        q = np.array([q_factor(*p) for p in self.P])
        A = np.array([_f0_feats(*p[:4]) for p in self.P])
        self.coef, *_ = np.linalg.lstsq(A, np.log(self.X[:, fi["f0"]] / q), rcond=None)
        # 같은 base 의 중립 발성 크기를 기준으로 한 상대 dB
        self.dbrel = np.zeros(len(self.P))
        for bv in np.unique(self.P[:, 4]):
            m = self.P[:, 4] == bv
            d = np.linalg.norm((self.P[m, :4] - [NEUTRAL["ct"], NEUTRAL["ta"], NEUTRAL["lca"], NEUTRAL["ps"]]) /
                               [0.25, 0.25, 0.2, 4.0], axis=1)
            ref = float(np.median(self.X[m][np.argsort(d)[:6], fi["db"]]))
            self.dbrel[m] = self.X[m, fi["db"]] - ref

    def estimate_base(self, median_f0, low_f0=None):
        """사람마다 다른 기본 성대 길이/질량을 'base' 하나로: 그 사람의 중간 음높이가 중립 근육값에서 나오도록.
        단, 가장 낮은 음도 ct >= 0 으로 낼 수 있게 상한을 둔다 (교정값 범위까지 고려)."""
        f = f0_model(NEUTRAL["ct"], NEUTRAL["ta"], NEUTRAL["lca"], NEUTRAL["ps"], 1.0, self.coef)
        b = median_f0 / f
        if low_f0:
            top = max(f0_model(0.0, ta, lca, ps, 1.0, self.coef)
                      for ta in (0.0, 0.5, 1.0) for lca in (0.4, 0.6, 0.8) for ps in (5.0, 10.0, 15.0, 20.0))
            b = min(b, 0.97 * low_f0 / top)
        return float(np.clip(b, 0.45, 2.6))

    def fit_note(self, s, base, db_rel):
        """s: 음 하나의 특징 요약. db_rel: 그 사람 평균 대비 크기 (dB).

        표에서 이 음높이 근처(±1반음 정도)에서 소리 특징이 가장 비슷한 조합을 찾고,
        그 조합의 ta·lca·ps 를 이 사람의 성대(base)에 적용해 ct 를 음높이로 역산한다.
        """
        fi = self.fi
        X = self.X
        d2 = (12 * np.log2(X[:, fi["f0"]] / s["f0"]) / 1.0) ** 2
        for k in ("hnr", "h1h2", "cpp", "tilt"):
            d2 += ((X[:, fi[k]] - s[k]) / SCALE[k]) ** 2
        d2 += ((self.dbrel - db_rel) / SCALE["dbrel"]) ** 2
        idx = np.argsort(d2)[:10]
        w = np.exp(-(d2[idx] - d2[idx[0]]) / 2)
        w /= w.sum()
        ta, lca, ps = (self.P[idx, 1:4] * w[:, None]).sum(axis=0)
        ct, in_range = ct_for_f0(s["f0"], ta, lca, ps, base, self.coef)
        return {"ct": min(ct, 1.0), "ta": float(ta), "lca": float(lca), "ps": float(ps),
                "fit_err": float(math.sqrt(d2[idx[0]] / 6)), "in_range": in_range}
