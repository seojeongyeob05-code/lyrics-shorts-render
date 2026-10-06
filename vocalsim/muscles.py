"""근육 활성도 -> 2질량 성대 모델 파라미터.

Titze & Story (2002) 의 근육 규칙을 단순화해서 Ishizaka-Flanagan 2질량 모델에 매핑한다.
단위는 CGS (g, cm, s, dyn).

입력
  ct  : 윤상갑상근 (cricothyroid)          0..1  성대를 길게 -> 음높이 상승
  ta  : 갑상피열근 (thyroarytenoid)        0..1  성대를 두껍게 -> 굵은 소리, 접촉 시간 증가
  lca : 외측윤상피열근 (lateral cricoarytenoid) 0..1  성대를 붙임 -> 바람 섞임 감소
  ps  : 폐압 (subglottal pressure, cmH2O)        숨이 미는 힘 -> 크기
"""
from dataclasses import dataclass
import math

CMH2O = 980.665  # dyn/cm^2

# Ishizaka & Flanagan (1972) 기준값
M1, M2 = 0.125, 0.025
K1, K2, KC = 80000.0, 8000.0, 25000.0
D1, D2 = 0.25, 0.05
L0 = 1.4
ZETA1, ZETA2 = 0.1, 0.6

NEUTRAL = {"ct": 0.3, "ta": 0.3, "lca": 0.5, "ps": 9.0}


@dataclass
class FoldParams:
    m1: float
    m2: float
    k1: float
    k2: float
    kc: float
    r1: float
    r2: float
    d1: float
    d2: float
    l: float
    a0: float      # 휴지기 성문 면적 (cm^2), 음수면 눌린 상태
    ps: float      # 성문하압 (dyn/cm^2)
    strain: float  # 성대 늘어난 비율


def strain(ct, ta, lca):
    """Titze-Story 신장 규칙: e = G(R*a_ct - a_ta) - H*a_lca"""
    return 0.2 * (3.0 * ct - ta) - 0.2 * lca


def fold_params(ct, ta, lca, ps_cmh2o, base=1.6):
    """base: 목소리 기본 높이 배율 (1.0 = 남성 ~150Hz, 1.6 = 여성 ~230Hz)"""
    e = strain(ct, ta, lca)
    # 장력 계수 Q: 길게 늘이면(e) 지수적으로, TA 수축은 몸체 장력으로 약간 상승
    q = base * 0.85 * math.exp(1.7 * e) * (1.0 + 0.45 * ta)
    # 폐압이 높으면 성대가 더 팽팽해져 음이 약간 오름 (~1%/cmH2O)
    q *= 1.0 + 0.01 * max(min(ps_cmh2o, 40.0) - 9.0, -9.0)
    # 두께: TA 는 접촉면(d)을 두껍게, 신장은 얇게. 질량은 덜 늘어남
    th = (1.0 + 2.5 * ta) / (1.0 + e)
    tm = (1.0 + 0.5 * ta) / (1.0 + e)
    l = L0 * (1.0 + e)
    m1 = M1 * tm / q
    m2 = M2 * tm / q
    k1 = K1 * tm * q
    k2 = K2 * tm * q
    kc = KC * tm * q
    r1 = 2 * ZETA1 * math.sqrt(m1 * k1)
    r2 = 2 * ZETA2 * math.sqrt(m2 * k2)
    # 내전: LCA 가 클수록 성문 간격 감소
    xi0 = 0.04 * (0.85 - lca)
    a0 = 2.0 * l * xi0
    return FoldParams(m1, m2, k1, k2, kc, r1, r2, D1 * th, D2 * th, l, a0,
                      ps_cmh2o * CMH2O, e)
