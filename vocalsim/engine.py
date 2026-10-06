"""발성 물리엔진: 2질량 성대 모델 + Kelly-Lochbaum 도파관 성도.

숨(성문하압) -> 성대 진동(2질량 + 충돌) -> 성문 공기 흐름(베르누이) + 난류 잡음
-> 성도 44 구간 반사 -> 입술 방사 -> 소리
"""
import math
import numpy as np
from numba import njit

from .muscles import fold_params
from . import tract

FS = 44100
OVERSAMPLE = 4
BLOCK = 32  # 제어 파라미터 갱신 단위 (샘플)

# 블록 파라미터 열 순서
_COLS = ("m1", "m2", "k1", "k2", "kc", "r1", "r2", "d1", "d2", "l", "a0", "ps")


@njit(cache=True)
def _simulate(P, D, block, fs, os, seed):
    nblocks = P.shape[0]
    total = nblocks * block
    n_sec = D.shape[1]
    audio = np.zeros(total)
    x1_out = np.zeros(total, dtype=np.float32)
    x2_out = np.zeros(total, dtype=np.float32)
    u_out = np.zeros(total, dtype=np.float32)

    rho = 0.00114
    mu = 1.86e-4
    re_crit = 1200.0
    noise_gain = 1.5e-6
    glot_refl = 0.75
    lip_refl = -0.85
    fade = 0.999
    gin = 1.0 / 300.0

    np.random.seed(seed)
    dt = 1.0 / (fs * os)
    x1 = 0.0
    v1 = 0.0
    x2 = 0.0
    v2 = 0.0

    R = np.zeros(n_sec)
    L = np.zeros(n_sec)
    jr = np.zeros(n_sec + 1)
    jl = np.zeros(n_sec + 1)
    refl = np.zeros(n_sec)
    lip_prev = 0.0
    # 잡음용 대역 필터 상태
    nh_prev_in = 0.0
    nh = 0.0
    nl = 0.0
    hp_a = math.exp(-2 * math.pi * 400.0 / fs)
    lp_a = math.exp(-2 * math.pi * 4500.0 / fs)

    for b in range(nblocks):
        m1 = P[b, 0]
        m2 = P[b, 1]
        k1 = P[b, 2]
        k2 = P[b, 3]
        kc = P[b, 4]
        r1 = P[b, 5]
        r2 = P[b, 6]
        d1 = P[b, 7]
        d2 = P[b, 8]
        l = P[b, 9]
        a0 = P[b, 10]
        ps = P[b, 11]
        h1 = 3.0 * k1
        h2 = 3.0 * k2
        rc1 = 2.0 * 1.0 * math.sqrt(m1 * k1)
        rc2 = 2.0 * 1.0 * math.sqrt(m2 * k2)
        vel = math.sqrt(2.0 * max(ps, 0.0) / rho)
        for i in range(1, n_sec):
            A0 = D[b, i - 1] * D[b, i - 1]
            A1 = D[b, i] * D[b, i]
            refl[i] = (A0 - A1) / (A0 + A1)

        for j in range(block):
            n = b * block + j
            usum = 0.0
            # 미세한 기류 요동: 대칭 평형점에서 진동이 시작되게 함
            kick = 0.01 * ps * l * d1 * np.random.standard_normal()
            for s in range(os):
                a1 = a0 + 2.0 * l * x1
                a2 = a0 + 2.0 * l * x2
                amin = min(a1, a2)
                if a1 > 0.0 and amin > 0.0:
                    F1 = ps * l * d1 * (1.0 - (amin / a1) ** 2)
                else:
                    # 성문이 닫혀 있으면 아래쪽 압력이 그대로 밀어 올림
                    F1 = ps * l * d1
                F1 += kick
                f1 = F1 - r1 * v1 - k1 * x1 - kc * (x1 - x2)
                f2 = -r2 * v2 - k2 * x2 - kc * (x2 - x1)
                if a1 < 0.0:
                    f1 -= h1 * a1 / (2.0 * l) + rc1 * v1
                if a2 < 0.0:
                    f2 -= h2 * a2 / (2.0 * l) + rc2 * v2
                v1 += dt * f1 / m1
                v2 += dt * f2 / m2
                x1 += dt * v1
                x2 += dt * v2
                usum += vel * max(amin, 0.0)
            U = usum / os

            # 난류 잡음 (레이놀즈 수 기준)
            re = rho * U / (mu * l)
            w = np.random.standard_normal()
            nh = hp_a * (nh + w - nh_prev_in)
            nh_prev_in = w
            nl = lp_a * nl + (1.0 - lp_a) * nh
            noise = 0.0
            if re > re_crit:
                noise = noise_gain * (re * re - re_crit * re_crit) * nl

            g = (U + noise) * gin
            lip = 0.0
            for _ in range(2):
                jr[0] = L[0] * glot_refl + g
                jl[n_sec] = R[n_sec - 1] * lip_refl
                for i in range(1, n_sec):
                    wv = refl[i] * (R[i - 1] + L[i])
                    jr[i] = R[i - 1] - wv
                    jl[i] = L[i] + wv
                for i in range(n_sec):
                    R[i] = jr[i] * fade
                    L[i] = jl[i + 1] * fade
                lip += R[n_sec - 1]
            lip *= 0.5
            audio[n] = lip - lip_prev  # 입술 방사 (미분)
            lip_prev = lip
            x1_out[n] = x1
            x2_out[n] = x2
            u_out[n] = U
    return audio, x1_out, x2_out, u_out


class Controls:
    """블록 단위 제어값 배열 (ct, ta, lca, ps, vib, vowel 지름)."""

    def __init__(self, ct, ta, lca, ps, diam, vib=None):
        self.ct = np.asarray(ct, float)
        self.ta = np.asarray(ta, float)
        self.lca = np.asarray(lca, float)
        self.ps = np.asarray(ps, float)
        self.diam = np.asarray(diam, float)
        self.vib = np.zeros_like(self.ct) if vib is None else np.asarray(vib, float)


def synthesize(ctrl, base=1.6, seed=1, fs=FS):
    """ctrl: Controls (블록 길이 BLOCK). 반환: dict(audio, x1, x2, u, a0, l, fs)"""
    nb = len(ctrl.ct)
    P = np.zeros((nb, len(_COLS)))
    rng = np.random.default_rng(seed)
    # 자연스러운 미세 흔들림 (1/f 비슷한 느린 잡음)
    slow = rng.standard_normal(nb)
    k = max(1, int(0.08 * fs / BLOCK))
    slow = np.convolve(slow, np.ones(k) / k, mode="same") * 0.02
    t = np.arange(nb) * BLOCK / fs
    vib = ctrl.vib * np.sin(2 * math.pi * 5.5 * t)
    for b in range(nb):
        fp = fold_params(ctrl.ct[b], ctrl.ta[b], ctrl.lca[b], ctrl.ps[b], base)
        q = 2.0 ** ((vib[b] + slow[b]) / 12.0)
        P[b] = (fp.m1 / q, fp.m2 / q, fp.k1 * q, fp.k2 * q, fp.kc * q, fp.r1, fp.r2,
                fp.d1, fp.d2, fp.l, fp.a0, fp.ps)
    audio, x1, x2, u = _simulate(P, ctrl.diam, BLOCK, fs, OVERSAMPLE, seed)
    return {"audio": audio, "x1": x1, "x2": x2, "u": u,
            "a0": P[:, 10], "l": P[:, 9], "fs": fs, "block": BLOCK}


def default_diam(nb, vowel="a"):
    return np.tile(tract.diameter(vowel), (nb, 1))
