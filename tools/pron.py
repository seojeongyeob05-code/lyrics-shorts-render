"""일본어 가사의 한글 발음 만들기 / 내가 쓴 발음의 오타 의심 자리 찾기.

    pip install pykakasi
    python3 tools/pron.py 가사.txt                  # 줄마다 한글 발음 출력(-o 파일로 저장)
    python3 tools/pron.py 가사.txt --check 발음.txt  # 쓴 발음과 대조해 다른 자리 알려주기

사전 읽기가 틀리거나(失っ 등) 노래에서 다르게 읽는 경우도 있어서, 알려주는 자리는 '확인해 볼 곳'이다.
조사(は→와, へ→에)·부호·띄어쓰기 차이와 영어 단어는 따지지 않는다.
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from shorts.pron import check_lines, japanese_to_hangul  # noqa: E402


def read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8-sig") as f:
        return [line.strip() for line in f if line.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lyrics", help="일본어 가사(한 줄에 한 줄, 빈 줄 무시)")
    ap.add_argument("--check", help="대조할 한글 발음 파일(줄 수가 같아야 함)")
    ap.add_argument("-o", "--out", help="만든 발음을 저장할 파일")
    args = ap.parse_args(argv)
    lines = read_lines(args.lyrics)
    try:
        if args.check:
            prons = read_lines(args.check)
            if len(prons) != len(lines):
                print(f"줄 수가 달라요: 가사 {len(lines)}줄, 발음 {len(prons)}줄", file=sys.stderr)
                return 2
            report = check_lines(lines, prons)
            for n, auto, given, diffs in report:
                parts = ", ".join(f"'{a or '(없음)'}' ↔ '{b or '(없음)'}'" for a, b in diffs)
                print(f"{n}번째 줄  {lines[n - 1]}\n  자동: {auto}\n  쓴것: {given}\n  다른 곳: {parts}\n")
            print(f"{len(lines)}줄 중 {len(report)}줄 확인 필요" if report else f"{len(lines)}줄 모두 일치")
            return 0
        prons = [japanese_to_hangul(line) for line in lines]
    except ImportError as e:
        print(e, file=sys.stderr)
        return 2
    text = "\n".join(prons) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(args.out)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
