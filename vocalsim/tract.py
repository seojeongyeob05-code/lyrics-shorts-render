"""성도(목구멍 + 입) 단면 지름 함수. Pink Trombone (Neil Thapen) 의 혀 모델을 따른다.

44 개 구간, 0 = 성문 바로 위, 43 = 입술.
"""
import math
import numpy as np

N = 44
BLADE_START, TIP_START, LIP_START = 10, 32, 39

# (혀 위치, 혀 지름, 입술 지름)
VOWELS = {
    "a": (12.9, 2.43, 1.5),   # 아
    "e": (19.4, 2.70, 1.3),   # 에
    "i": (26.5, 2.30, 1.1),   # 이
    "o": (14.5, 2.80, 0.55),  # 오
    "u": (22.5, 2.10, 0.35),  # 우
}

SECTION_NAMES = [
    (0, "성문 위"), (3, "후두전정"), (7, "하인두"), (13, "구인두"),
    (24, "구강"), (39, "입술"),
]


def rest_diameter():
    d = np.zeros(N)
    for i in range(N):
        if i < 7 * N / 44 - 0.5:
            d[i] = 0.6
        elif i < 12 * N / 44:
            d[i] = 1.1
        else:
            d[i] = 1.5
    return d


def diameter(vowel="a"):
    tongue_index, tongue_d, lip_d = VOWELS[vowel]
    d = rest_diameter()
    for i in range(BLADE_START, LIP_START):
        t = 1.1 * math.pi * (tongue_index - i) / (TIP_START - BLADE_START)
        fixed = 2 + (tongue_d - 2) / 1.5
        curve = (1.5 - fixed + 1.7) * math.cos(t)
        if i == BLADE_START - 2 or i == LIP_START - 1:
            curve *= 0.8
        if i == BLADE_START or i == LIP_START - 2:
            curve *= 0.94
        d[i] = 1.5 - curve
    for i in range(LIP_START, N):
        d[i] = lip_d
    return np.maximum(d, 0.05)
