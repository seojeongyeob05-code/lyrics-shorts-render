"""긴 곡 렌더 속도·메모리 측정.

    python3 tools/bench.py [--seconds 210] [--keep 폴더]

가짜 곡(합성음 + 노래방/일반 줄이 섞인 LRC + 사진 배경·앨범 아트)을 만들어
가벼운 설정과 무거운 설정(사진 줌 + 노래방 + 음악 막대 + 앨범 아트)으로 전체를 렌더하고
걸린 시간, 실시간 대비 배속, 최대 메모리를 표로 보여준다.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import resource
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

WORDS = "오늘 밤 하늘 아래 작은 노래 하나 너에게 닿기를 바라며 천천히 불러 볼게".split()


def make_song(folder: str, seconds: float) -> dict:
    rnd = random.Random(7)
    lines, t = [], 1.0
    while t < seconds - 4:
        n = rnd.randint(3, 7)
        words = [rnd.choice(WORDS) for _ in range(n)]
        if len(lines) % 2:  # 줄마다 번갈아 노래방/일반
            step = 2.6 / n
            body = " ".join(f"<{fmt(t + k * step)}>{w}" for k, w in enumerate(words))
        else:
            body = " ".join(words)
        lines.append(f"[{fmt(t)}]{body}")
        t += 3.2 + rnd.random() * 1.2
    with open(os.path.join(folder, "song.lrc"), "w", encoding="utf-8") as f:
        f.write("[ti:벤치마크]\n[ar:합성음]\n" + "\n".join(lines) + "\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"aevalsrc='0.3*sin(2*PI*(110+55*floor(t*2))*t)+0.2*sin(2*PI*(660+110*floor(t*3))*t)"
                    f"+0.05*random(0)':d={seconds}", "-c:a", "aac", os.path.join(folder, "song.m4a")],
                   check=True)
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1600, 1200), (30, 60, 110))
    d = ImageDraw.Draw(img)
    for _ in range(80):
        x, y, r = rnd.randint(0, 1600), rnd.randint(0, 1200), rnd.randint(30, 150)
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(rnd.randint(60, 240) for _ in range(3)))
    img.save(os.path.join(folder, "bg.jpg"))
    img.crop((200, 100, 800, 700)).save(os.path.join(folder, "cover.jpg"))
    return {"lines": len(lines)}


def fmt(sec: float) -> str:
    return f"{int(sec // 60):02}:{sec % 60:05.2f}"


def run(folder: str, name: str, extra: list[str]) -> dict:
    out = os.path.join(folder, f"{name}.mp4")
    # 렌더하는 파이썬 프로세스가 끝날 때 자기 최대 메모리를 알려주게 한다(ffmpeg는 따로)
    probe = ("import resource, sys; from shorts import cli; cli.main(sys.argv[1:]); "
             "print('RSS', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, file=sys.stderr)")
    cmd = [sys.executable, "-c", probe, "render", os.path.join(folder, "song.lrc"),
           "--audio", os.path.join(folder, "song.m4a"), "-o", out] + extra
    t0 = time.perf_counter()
    done = subprocess.run(cmd, check=True, cwd=ROOT, stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, text=True)
    elapsed = time.perf_counter() - t0
    py_kb = next(int(l.split()[1]) for l in done.stderr.splitlines() if l.startswith("RSS "))
    return {"name": name, "seconds": elapsed, "py_mb": py_kb / 1024,
            "size_mb": os.path.getsize(out) / 1e6}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=210)
    ap.add_argument("--keep", help="만든 파일을 남길 폴더")
    args = ap.parse_args()
    folder = args.keep or tempfile.mkdtemp(prefix="shorts-bench-")
    os.makedirs(folder, exist_ok=True)
    info = make_song(folder, args.seconds)
    heavy_style = os.path.join(folder, "heavy.json")
    with open(heavy_style, "w") as f:
        json.dump({"extends": "photo", "visualizer": True, "transition": "slide"}, f)
    rows = [
        run(folder, "light", []),
        run(folder, "heavy", ["--style", heavy_style, "--bg", os.path.join(folder, "bg.jpg"),
                              "--cover", os.path.join(folder, "cover.jpg")]),
        run(folder, "preview", ["--preview"]),
    ]
    print(f"곡 {args.seconds:.0f}초, 가사 {info['lines']}줄, CPU {os.cpu_count()}개")
    ffmpeg_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
    print(f"{'설정':8} {'걸린 시간':>9} {'배속':>6} {'파이썬 메모리':>12} {'파일':>8}")
    for r in rows:
        print(f"{r['name']:8} {r['seconds']:8.1f}s {args.seconds / r['seconds']:5.1f}x "
              f"{r['py_mb']:10.0f}MB {r['size_mb']:6.1f}MB")
    print(f"(자식 프로세스 최대 메모리 {ffmpeg_mb:.0f}MB — 대부분 ffmpeg의 x264 인코딩 버퍼)")
    if not args.keep:
        shutil.rmtree(folder)


if __name__ == "__main__":
    main()
