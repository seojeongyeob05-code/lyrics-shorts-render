"""1080x1920 프레임 그리기. 내부적으로 2배 크기로 그린 뒤 축소(안티앨리어싱)."""
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vocalsim import tract

W, H = 1080, 1920
S = 2  # 슈퍼샘플링 배율
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")

# 영역
HEADER = (0, 300)
ANAT = (300, 1010)
MID = (1010, 1450)
SPEC = (1450, 1920)
SPEC_IMG_TOP = 1482

# 색
C_HEAD_BG = (23, 19, 15)
C_GOLD = (201, 164, 106)
C_TRACK = (58, 51, 44)
C_TEXT = (245, 242, 236)
C_SUB = (169, 162, 154)
C_BODY = (236, 232, 226)
C_SKIN = (246, 236, 226)
C_SKIN_LINE = (214, 196, 182)
C_BONE = (239, 228, 198)
C_BONE_LINE = (205, 188, 152)
C_TUBE = (244, 186, 186)
C_WALL = (190, 62, 66)
C_TONGUE = (214, 108, 112)
C_CART = (204, 218, 232)
C_CARD = (255, 255, 255)
C_INK = (52, 46, 42)
C_INK2 = (120, 112, 104)
C_GLOTTIS = (74, 128, 206)

MUSCLES = [
    ("ct", "윤상갑상근", "성대를 길게"),
    ("ta", "갑상피열근", "성대를 두껍게"),
    ("lca", "외측윤상피열근", "성대를 붙임"),
    ("ps", "폐압", "숨이 미는 힘"),
]
PS_MAX = 30.0
NEUTRAL_UI = {"ct": 0.3, "ta": 0.3, "lca": 0.5, "ps": 9.0}

# 성도 중심선 (성문 -> 입술), 전역 좌표
TUBE_PATH = [(480, 905), (480, 800), (478, 720), (462, 665), (420, 630),
             (330, 618), (240, 622), (172, 630)]
TUBE_PX_PER_D = 19.0

HEAD = [(205, 300), (178, 380), (168, 432), (118, 520), (124, 545), (160, 562),
        (148, 600), (150, 628), (147, 657), (172, 690), (176, 742), (214, 778),
        (330, 792), (388, 832), (406, 905), (396, 1010), (690, 1010), (682, 860),
        (705, 700), (762, 560), (792, 420), (772, 300)]


def _font(weight, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"Pretendard-{weight}.otf"), int(size * S))


class Fonts:
    def __init__(self):
        self.cache = {}

    def __call__(self, weight, size):
        k = (weight, size)
        if k not in self.cache:
            self.cache[k] = _font(weight, size)
        return self.cache[k]


def _resample_path(path, n):
    pts = np.array(path, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    ss = np.linspace(0, cum[-1], n)
    xs = np.interp(ss, cum, pts[:, 0])
    ys = np.interp(ss, cum, pts[:, 1])
    p = np.stack([xs, ys], 1)
    # 법선
    t = np.gradient(p, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    nrm = np.stack([-t[:, 1], t[:, 0]], 1)
    return p, nrm


def _lerp(c0, c1, u):
    u = max(0.0, min(1.0, u))
    return tuple(int(a + (b - a) * u) for a, b in zip(c0, c1))


class Canvas:
    """1x 좌표로 그리면 S배로 변환."""

    def __init__(self, img, fonts):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.f = fonts

    @staticmethod
    def _p(pts):
        return [(x * S, y * S) for x, y in pts]

    def poly(self, pts, fill=None, outline=None, width=1):
        self.d.polygon(self._p(pts), fill=fill, outline=None)
        if outline is not None:
            self.d.line(self._p(list(pts) + [pts[0]]), fill=outline, width=int(width * S), joint="curve")

    def line(self, pts, fill, width=1):
        self.d.line(self._p(pts), fill=fill, width=int(width * S), joint="curve")

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=1, r=0):
        box = (x0 * S, y0 * S, x1 * S, y1 * S)
        if r:
            self.d.rounded_rectangle(box, radius=r * S, fill=fill, outline=outline, width=int(width * S))
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=int(width * S))

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=1):
        self.d.ellipse(((cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S),
                       fill=fill, outline=outline, width=int(width * S))

    def text(self, x, y, s, size, fill, weight="Medium", anchor="la"):
        self.d.text((x * S, y * S), s, font=self.f(weight, size), fill=fill, anchor=anchor)

    def textlen(self, s, size, weight="Medium"):
        return self.f(weight, size).getlength(s) / S


class Renderer:
    def __init__(self, data):
        """data: make_short 에서 준비한 dict (timeline, sim, per-frame 측정값, spec)."""
        self.data = data
        self.fonts = Fonts()
        self.static = self._static()

    # ---------- 정적 배경 ----------
    def _static(self):
        img = Image.new("RGB", (W * S, H * S), C_BODY)
        c = Canvas(img, self.fonts)
        c.rect(0, HEADER[0], W, HEADER[1], fill=C_HEAD_BG)
        # 해부 패널 배경 (아래로 갈수록 조금 어둡게)
        for i, y in enumerate(range(ANAT[0], ANAT[1], 10)):
            c.rect(0, y, W, y + 10, fill=_lerp((242, 239, 234), (226, 222, 216), i / 71))
        # 머리 윤곽
        c.poly(HEAD, fill=C_SKIN, outline=C_SKIN_LINE, width=2)
        # 두개골 바닥 + 척추
        c.poly([(560, 560), (700, 540), (740, 600), (610, 640)], fill=C_BONE, outline=C_BONE_LINE, width=2)
        for i, y in enumerate(range(650, 1010, 42)):
            c.rect(560, y, 640, y + 32, fill=C_BONE, outline=C_BONE_LINE, width=2, r=8)
            c.rect(640, y + 6, 680, y + 24, fill=C_BONE, outline=C_BONE_LINE, width=2, r=6)
        # 경구개
        c.line([(430, 606), (330, 597), (232, 603)], fill=C_BONE_LINE, width=7)
        c.line([(430, 606), (330, 597), (232, 603)], fill=C_BONE, width=4)
        # 오른쪽 관 도식 카드
        c.rect(742, 330, 1062, 985, fill=C_CARD, r=18)
        c.text(762, 348, "성도 단면 — 성문 → 입술", 22, C_INK, "Bold")
        c.text(762, 378, "폭 = 그 위치 관의 굵기", 18, C_INK2)
        # 아래 해부 정보 박스
        c.rect(20, 862, 380, 996, fill=C_CARD, r=14)
        c.text(36, 874, "숨 — 폐 상태", 20, C_INK2)
        # 중간 패널
        c.rect(16, MID[0] + 12, 536, MID[1] - 12, fill=(30, 21, 19), r=16)
        c.rect(548, MID[0] + 12, 1064, MID[1] - 12, fill=C_CARD, r=16)
        c.text(34, MID[0] + 26, "성대 진동 (슬로모션)", 22, C_TEXT, "Bold")
        c.text(568, MID[0] + 26, "숨 · 근육 활성", 22, C_INK, "Bold")
        # 스펙트로그램 영역
        c.rect(0, SPEC[0], W, H, fill=(6, 4, 18))
        c.text(20, SPEC[0] + 6, "스펙트로그램", 20, (170, 170, 200))
        c.text(1060, SPEC[0] + 6, "0 – 5 kHz", 18, (130, 130, 160), anchor="ra")
        return img

    # ---------- 프레임 ----------
    def frame(self, fi):
        d = self.data
        st = d["frames"][fi]
        img = self.static.copy()
        c = Canvas(img, self.fonts)
        self._header(c, st)
        self._anatomy(c, st)
        self._column(c, st)
        self._folds(c, st)
        self._lungs(c, st)
        self._spec(img, st)
        self._caption(img, c, st)
        return img.reduce(S)

    def _header(self, c, st):
        seg = st["seg"]
        f0, db = st["f0"], st["db"]
        focus = seg["focus"]
        if focus:
            c.text(40, 28, seg["title"] or "", 60, C_TEXT, "Bold")
            c.text(42, 104, seg["sub"] or "", 28, C_SUB)
            v = st["ctrl"][focus]
            nv = NEUTRAL_UI[focus]
            if focus == "ps":
                v, nv = v / PS_MAX, nv / PS_MAX
            x0, x1, y = 40, 1040, 160
            c.rect(x0, y, x1, y + 22, fill=C_TRACK, r=11)
            c.rect(x0, y, x0 + max(22, (x1 - x0) * min(1, v)), y + 22, fill=C_GOLD, r=11)
            tx = x0 + (x1 - x0) * nv
            c.rect(tx - 2, y - 8, tx + 2, y + 30, fill=C_TEXT)
            c.text(tx, y + 36, "정상", 22, C_SUB, anchor="ma")
        else:
            c.text(40, 40, d_title(self.data), 50, C_TEXT, "Bold")
            c.text(1040, 56, self.data["tag"], 26, C_SUB, anchor="ra")
            c.text(42, 122, "숨 → 성대 → 목구멍과 입 → 소리", 28, C_SUB)
        c.text(40, 228, "음높이 " + (f"{f0:.0f} Hz" if f0 else "—"), 42, C_TEXT, "Bold")
        c.text(1040, 228, "크기 " + (f"{db:.0f} dB" if db else "—"), 42, C_TEXT, "Bold", anchor="ra")

    def _tube_geom(self, diam):
        p, nrm = _resample_path(TUBE_PATH, tract.N + 1)
        # 구간 경계에서의 반지름 (양 옆 구간 평균)
        dd = np.concatenate([[diam[0]], (diam[:-1] + diam[1:]) / 2, [diam[-1]]])
        r = dd * TUBE_PX_PER_D / 2
        left = p + nrm * r[:, None]
        right = p - nrm * r[:, None]
        return p, left, right

    def _anatomy(self, c, st):
        diam = st["diam"]
        p, left, right = self._tube_geom(diam)
        # 혀: 관의 아래/앞쪽 벽과 턱 사이
        lower = right if np.mean(right[20:40, 1]) > np.mean(left[20:40, 1]) else left
        upper = left if lower is right else right
        tongue = [tuple(q) for q in lower[8:41]] + [(190, 735), (300, 780), (380, 830), (420, 860)]
        c.poly(tongue, fill=C_TONGUE)
        # 인두 뒤 벽 근육
        back = [tuple(q) for q in upper[0:20]]
        c.poly(back + [(560, 640), (560, 905)], fill=(206, 96, 100))
        # 관 내부
        c.poly([tuple(q) for q in left] + [tuple(q) for q in right[::-1]], fill=C_TUBE)
        c.line([tuple(q) for q in left], fill=C_WALL, width=4)
        c.line([tuple(q) for q in right], fill=C_WALL, width=4)
        # 성문 표시
        c.line([tuple(left[0]), tuple(right[0])], fill=C_GLOTTIS, width=7)
        # 기류 입자
        if st["u"] > 20:
            n = len(p) - 1
            speed = 0.25 + st["u"] / 900.0
            for k in range(10):
                s = (st["t"] * speed + k / 10.0) % 1.0
                i = s * n
                i0 = int(i)
                fr = i - i0
                x, y = p[i0] * (1 - fr) + p[min(i0 + 1, n)] * fr
                rr = 3 + 3 * min(1, st["u"] / 400)
                c.ellipse(x, y, rr, rr, fill=(255, 255, 255))
        # 후두: 갑상연골, 윤상연골, 윤상갑상근
        ct = st["ctrl"]["ct"]
        c.poly([(410, 855), (462, 848), (468, 936), (420, 932)], fill=C_CART, outline=(150, 170, 195), width=2)
        c.poly([(426, 948), (500, 950), (500, 978), (432, 975)], fill=C_CART, outline=(150, 170, 195), width=2)
        ctc = _lerp((236, 196, 196), (205, 30, 36), ct * 1.2)
        c.poly([(414, 918), (444, 928), (452, 962), (426, 958)], fill=ctc)
        focus = st["seg"]["focus"]
        hl = C_WALL if focus == "ct" else C_INK2
        c.line([(430, 945), (390, 900)], fill=hl, width=2)
        c.text(386, 892, "윤상갑상근", 18, hl, "Bold" if focus == "ct" else "Medium", anchor="rb")
        c.text(300, 700, "혀", 22, (255, 240, 240), "Bold", anchor="mm")
        c.text(520, 760, "인두", 18, C_INK2)
        c.text(470, 868, "후두", 18, C_INK2, anchor="ra")
        # 숨 정보
        c.text(36, 904, f"폐 부피 {st['lung'] * 100:.0f} %VC", 22, C_INK, "Bold")
        c.text(36, 934, f"폐압 {st['ctrl']['ps']:.1f} cmH₂O", 22, C_INK, "Bold")
        now = "들숨 (숨 채우는 중)" if st["ctrl"]["ps"] < 1 else "날숨 (소리 내는 중)"
        c.text(36, 964, "지금: " + now, 20, C_INK2)

    def _column(self, c, st):
        diam = st["diam"]
        top, bot, cx = 420, 940, 845
        h = (bot - top) / tract.N
        for i in range(tract.N):
            y1 = bot - i * h
            y0 = y1 - h
            w = diam[i] * 26
            col = _lerp((236, 150, 150), (200, 80, 84), i / tract.N)
            c.rect(cx - w, y0 + 0.5, cx + w, y1 - 0.5, fill=col)
        c.rect(cx - 30, bot - 4, cx + 30, bot + 4, fill=C_GLOTTIS)
        for idx, name in tract.SECTION_NAMES:
            y = bot - (idx + 0.5) * h
            c.line([(cx + 52, y), (cx + 66, y)], fill=C_INK2, width=2)
            c.text(cx + 72, y, name, 18, C_INK, anchor="lm")
        c.text(cx, bot + 14, "성문", 18, C_GLOTTIS, "Bold", anchor="ma")

    def _folds(self, c, st):
        y0 = MID[0]
        x1, x2, a0, l = st["fx1"], st["fx2"], st["a0"], st["l"]
        xi0 = a0 / (2 * l)
        e1, e2 = xi0 + x1, xi0 + x2  # 아래/위 가장자리 반폭 (cm)
        emin = max(0.0, min(e1, e2))
        c.text(520, y0 + 30, f"실제보다 {st['slow']:.0f}배 느리게" if st["slow"] else "멈춤", 18, C_SUB, anchor="ra")
        # 위에서 본 모습 (후두경 시점): V 자로 모인 두 성대, 앞쪽 끝은 붙어 있음
        cx, ty, by = 175, y0 + 86, y0 + 296
        c.rect(cx - 128, ty - 14, cx + 128, by + 18, fill=(112, 36, 40), r=70)
        sc = 380.0
        n = 24
        post = max(0.0, xi0) * sc * 1.2
        vib = max(0.0, emin - max(xi0, 0.0)) * sc * 1.4
        closed = emin <= 0
        med_l, med_r, lat_l, lat_r, fal_l, fal_r = [], [], [], [], [], []
        for k in range(n + 1):
            u = k / n
            y = ty + (by - ty) * u
            hw = 0.0 if closed else min(52, post * u + vib * math.sin(math.pi * u))
            lat = 10 + 64 * u
            med_l.append((cx - hw, y))
            med_r.append((cx + hw, y))
            lat_l.append((cx - lat, y))
            lat_r.append((cx + lat, y))
            fal_l.append((cx - lat - 26, y))
            fal_r.append((cx + lat + 26, y))
        # 가성대 (위쪽 주름)
        c.poly(lat_l + fal_l[::-1], fill=(196, 96, 100))
        c.poly(lat_r + fal_r[::-1], fill=(196, 96, 100))
        # 진성대 (흰빛 점막)
        c.poly(lat_l + med_l[::-1], fill=(242, 224, 216))
        c.poly(lat_r + med_r[::-1], fill=(242, 224, 216))
        if not closed:
            c.poly(med_l + med_r[::-1], fill=(8, 4, 4))
        # 피열연골
        for sgn in (-1, 1):
            c.ellipse(cx + sgn * 46, by + 6, 30, 18, fill=(214, 140, 140))
        c.text(cx, ty - 30, "앞 · 위에서 본 성문", 16, C_SUB, anchor="ma")
        # 단면 (2질량)
        lx, rx, mx = 330, 520, 425
        cy0, cy1 = y0 + 100, y0 + 320
        c.text(mx, y0 + 70, "앞에서 자른 단면", 16, C_SUB, anchor="ma")
        sc2 = 450.0
        th = min(2.6, st["thick"])
        upy = y0 + 170
        midy = upy + 14 * th
        lowy = midy + 30 * th
        for sgn in (-1, 1):
            wall = lx if sgn < 0 else rx
            p_up = mx + sgn * max(1.0, min(48, e2 * sc2))
            p_lo = mx + sgn * max(1.0, min(48, e1 * sc2))
            c.poly([(wall, cy0), (wall, cy1), (p_lo, lowy + 20), (p_lo, midy), (p_up, upy), (wall, upy - 40)],
                   fill=(222, 120, 124), outline=(160, 60, 64), width=2)
            c.line([(p_up, upy), (p_lo, midy)], fill=(250, 220, 214), width=4)
        if st["u"] > 20 and emin > 0:
            a = min(1.0, st["u"] / 500)
            col = _lerp((40, 60, 90), (120, 180, 255), a)
            c.line([(mx, cy1 + 5), (mx, upy - 30)], fill=col, width=3)
            c.poly([(mx - 8, upy - 26), (mx + 8, upy - 26), (mx, upy - 42)], fill=col)
        c.text(lx + 4, cy0 - 4, "위", 14, C_SUB, anchor="lb")
        # 성문 기류 파형 (실시간 25ms)
        tr = st["utrace"]
        gx0, gx1, gy0, gy1 = 34, 518, y0 + 372, y0 + 418
        c.text(34, y0 + 344, "성문 기류 (25 ms)", 16, C_SUB)
        if tr is not None and len(tr) > 2:
            m = max(400.0, float(np.max(tr)))
            pts = [(gx0 + (gx1 - gx0) * k / (len(tr) - 1), gy1 - (gy1 - gy0) * v / m) for k, v in enumerate(tr)]
            c.line(pts, fill=C_GOLD, width=2)

    def _lungs(self, c, st):
        y0 = MID[0]
        vol = st["lung"]
        cx, cy = 690, y0 + 165
        s = 0.72 + 0.4 * vol
        c.line([(cx, y0 + 62), (cx, cy - 55)], fill=(200, 160, 160), width=10)
        for sgn in (-1, 1):
            pts = []
            for k in range(25):
                a = math.pi * k / 24
                rx, ry = 55 * s, 85 * s
                x = cx + sgn * (14 + rx + rx * math.cos(a) * (-1 if sgn > 0 else 1))
                y = cy + 10 - ry * math.sin(a) * 0.9
                pts.append((x, y))
            base = cy + 10 + 40 * s
            pts = pts + [(pts[-1][0], base), (pts[0][0], base)]
            c.poly(pts, fill=(240, 168, 170), outline=(196, 96, 100), width=2)
        # 횡격막: 폐 바로 아래 돔. 숨을 내쉴수록 돔이 올라감
        base = cy + 10 + 40 * s
        dome = 14 + 26 * (1 - vol)
        dy = base + 6 + dome
        arc = [(cx - 150 + 300 * k / 20, base + 6 + dome * (1 - math.sin(math.pi * k / 20))) for k in range(21)]
        c.line(arc, fill=(170, 80, 80), width=5)
        c.text(cx, dy + 10, "횡격막", 14, C_INK2, anchor="ma")
        # 폐압 게이지
        gx, gt, gb = 880, y0 + 70, y0 + 255
        c.rect(gx, gt, gx + 16, gb, fill=(232, 228, 222), r=8)
        v = min(1.0, st["ctrl"]["ps"] / PS_MAX)
        c.rect(gx, gb - (gb - gt) * v, gx + 16, gb, fill=C_GOLD if st["seg"]["focus"] == "ps" else (150, 160, 180), r=8)
        c.text(gx + 26, gt, "폐압", 16, C_INK2)
        c.text(gx + 26, gt + 22, f"{st['ctrl']['ps']:.0f}", 26, C_INK, "Bold")
        c.text(gx + 26, gt + 54, "cmH₂O", 14, C_INK2)
        c.text(gx + 26, gb - 40, "폐", 16, C_INK2)
        c.text(gx + 26, gb - 20, f"{vol * 100:.0f}%", 20, C_INK, "Bold")
        # 근육 막대
        focus = st["seg"]["focus"]
        by = y0 + 286
        for i, (k, name, _) in enumerate(MUSCLES):
            y = by + i * 34
            v = st["ctrl"][k] / (PS_MAX if k == "ps" else 1.0)
            on = focus == k
            c.text(568, y + 2, name, 18, C_INK if on else C_INK2, "Bold" if on else "Medium")
            bx0, bx1 = 730, 1040
            c.rect(bx0, y + 6, bx1, y + 18, fill=(232, 228, 222), r=6)
            c.rect(bx0, y + 6, bx0 + max(12, (bx1 - bx0) * min(1, v)), y + 18,
                   fill=C_GOLD if on else (164, 172, 190), r=6)

    def _spec(self, img, st):
        spec = self.data["spec"]  # (h, w, 3) 2배 해상도
        pxs = self.data["spec_pxs"]
        win_w = W * S
        right = int(st["t"] * pxs)
        left = right - win_w
        h = spec.shape[0]
        crop = np.zeros((h, win_w, 3), np.uint8)
        crop[:] = (6, 4, 18)
        a, b = max(0, left), min(spec.shape[1], right)
        if b > a:
            crop[:, a - left: b - left] = spec[:, a:b]
        img.paste(Image.fromarray(crop), (0, SPEC_IMG_TOP * S))

    def _caption(self, img, c, st):
        cap = st["caption"]
        if not cap:
            return
        txt, a, b = cap
        lines = wrap(c, txt, 44, 940)
        lh = 62
        total = lh * len(lines)
        cy = 1700
        top = cy - total // 2 - 22
        bot = cy + total // 2 + 22
        # 반투명 띠
        box = (0, top * S, W * S, bot * S)
        region = img.crop(box)
        shade = Image.new("RGB", region.size, (8, 8, 26))
        img.paste(Image.blend(region, shade, 0.62), box[:2])
        for i, ln in enumerate(lines):
            c.text(W / 2, top + 22 + i * lh + lh / 2, ln, 44, (255, 255, 255), "Bold", anchor="mm")


def d_title(data):
    return data["title"]


def wrap(c, text, size, maxw):
    out = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            t = (cur + " " + w).strip()
            if c.textlen(t, size, "Bold") <= maxw:
                cur = t
            else:
                if cur:
                    out.append(cur)
                cur = w
        if cur:
            out.append(cur)
    return out
