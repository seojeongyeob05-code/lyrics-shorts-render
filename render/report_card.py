"""발성 분석 결과 카드 (1080x1920 PNG). 영상 첫 화면이자 따로 공유할 수 있는 이미지."""
from PIL import Image

from render.frame import Canvas, Fonts, W, H, S, C_HEAD_BG, C_GOLD, C_TEXT, C_SUB, C_TRACK, wrap
from voiceanalysis.diagnose import MUSCLE_NAME, MUSCLE_ROLE

RECOMMEND = {"ta": (0.2, 0.55), "lca": (0.45, 0.7), "ps": (6.0, 14.0)}
C_GOOD = (120, 190, 140)
C_WARN = (232, 132, 96)
C_CARD = (38, 32, 27)


def _score_color(s):
    return C_GOOD if s >= 85 else (C_GOLD if s >= 65 else C_WARN)


def render_card(res, path):
    fonts = Fonts()
    img = Image.new("RGB", (W * S, H * S), C_HEAD_BG)
    c = Canvas(img, fonts)
    c.text(48, 70, "발성 분석", 30, C_GOLD, "Bold")
    c.text(48, 112, "가상 성대 물리엔진으로 거꾸로 계산한 결과", 24, C_SUB)
    sc = res["score"]
    c.text(48, 168, "균형 점수", 34, C_TEXT, "Bold")
    c.text(1032, 140, f"{sc}", 110, _score_color(sc), "Bold", anchor="ra")
    c.rect(48, 290, 1032, 302, fill=C_TRACK, r=6)
    c.rect(48, 290, 48 + 984 * sc / 100, 302, fill=_score_color(sc), r=6)
    c.text(48, 324, f"음역 {res['range'][0]} ~ {res['range'][1]}  ·  중심 {res['median_note']}", 26, C_SUB)

    # 근육 사용 추정
    y = 392
    c.rect(32, y, 1048, y + 430, fill=C_CARD, r=22)
    c.text(56, y + 24, "근육 사용 추정  →  교정값", 28, C_TEXT, "Bold")
    c.text(1024, y + 30, "■ 권장 범위", 20, C_GOOD, anchor="ra")
    for i, k in enumerate(("ct", "ta", "lca", "ps")):
        yy = y + 92 + i * 84
        c.text(56, yy, MUSCLE_NAME[k], 26, C_TEXT, "Bold")
        c.text(56, yy + 34, MUSCLE_ROLE[k], 20, C_SUB)
        x0, x1 = 330, 1010
        vmax = 30.0 if k == "ps" else 1.0
        c.rect(x0, yy + 20, x1, yy + 30, fill=C_TRACK, r=5)
        if k in RECOMMEND:
            a, b = RECOMMEND[k]
            c.rect(x0 + (x1 - x0) * a / vmax, yy + 16, x0 + (x1 - x0) * b / vmax, yy + 34, fill=(60, 96, 72), r=6)
        va = min(1, res["avg"][k] / vmax)
        vb = min(1, res["avg_fixed"][k] / vmax)
        xa, xb = x0 + (x1 - x0) * va, x0 + (x1 - x0) * vb
        if abs(xb - xa) > 8:
            c.line([(xa, yy + 25), (xb, yy + 25)], fill=C_GOLD, width=4)
            c.poly([(xb, yy + 25), (xb - 12 * (1 if xb > xa else -1), yy + 17), (xb - 12 * (1 if xb > xa else -1), yy + 33)],
                   fill=C_GOLD)
        c.ellipse(xa, yy + 25, 11, 11, fill=C_TEXT)
        fmt = "{:.0f}" if k == "ps" else "{:.2f}"
        lab = fmt.format(res["avg"][k])
        if abs(xb - xa) > 8:
            lab += " → " + fmt.format(res["avg_fixed"][k])
        c.text(x0, yy + 42, lab, 20, C_SUB)

    # 문제점
    y = 850
    issues = res["issues"][:3]
    if not issues:
        c.rect(32, y, 1048, y + 260, fill=C_CARD, r=22)
        c.text(56, y + 32, "균형 잡힌 발성이에요", 40, C_GOOD, "Bold")
        for j, ln in enumerate(wrap(c, "숨·성대·공명이 고르게 쓰이고 있어요. 음역 끝에서도 같은 균형을 유지하는 연습을 이어가 보세요.", 26, 940)):
            c.text(56, y + 104 + j * 40, ln, 26, C_TEXT)
    for i, it in enumerate(issues):
        lines_e = wrap(c, it["evidence"], 21, 950)
        lines_d = wrap(c, "연습 · " + it["drill"], 22, 950)
        h = 150 + 32 * len(lines_e) + 34 * len(lines_d)
        c.rect(32, y, 1048, y + h, fill=C_CARD, r=22)
        c.text(56, y + 24, f"{i + 1}", 40, C_WARN, "Bold")
        c.text(104, y + 28, it["title"], 34, C_TEXT, "Bold")
        yy = y + 84
        for ln in lines_e:
            c.text(56, yy, ln, 21, C_SUB)
            yy += 32
        c.text(56, yy + 4, "→ " + it["fix"], 24, C_GOLD, "Bold")
        yy += 46
        for ln in lines_d:
            c.text(56, yy, ln, 22, C_TEXT)
            yy += 34
        y += h + 18
        if y > 1760:
            break
    c.text(W / 2, 1868, "물리 모델로 추정한 발성 습관이며 의학적 진단이 아니에요", 19, C_SUB, anchor="ma")
    img.reduce(S).save(path)
    return path
