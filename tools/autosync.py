"""음원 + 가사 텍스트 → 타이밍이 맞춰진 LRC (자동).

    pip install faster-whisper
    python3 tools/autosync.py 노래.mp3 가사.txt --sub 발음.txt --sub 뜻.txt -o 노래.lrc

음성 인식(faster-whisper)으로 단어마다 불리는 시각을 얻고, 가사 텍스트와 글자 단위로 맞대어
줄 시작 시각과 노래방용 단어 시각을 정한다(shorts/align.py). 인식이 틀린 글자는 무시하므로
가사 텍스트만 정확하면 된다. --sub 파일은 가사와 줄 수가 같아야 하고, 같은 시각의 보조 줄로 들어간다.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from shorts.align import align_lines, to_lrc  # noqa: E402


def read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8-sig") as f:
        return [line.strip() for line in f if line.strip()]


def transcribe(path: str, model_name: str, language: str) -> list[dict]:
    import numpy as np
    from faster_whisper import WhisperModel

    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000",
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(np.frombuffer(pcm, np.float32), language=language,
                                   word_timestamps=True, vad_filter=False, beam_size=5,
                                   condition_on_previous_text=False)
    return [{"start": w.start, "end": w.end, "word": w.word} for seg in segments for w in seg.words]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("lyrics", help="가사 텍스트(한 줄에 한 줄, 빈 줄 무시)")
    ap.add_argument("--sub", action="append", default=[], help="보조 줄 파일(발음·번역). 여러 번 가능")
    ap.add_argument("--language", default="ja", help="노래 언어 코드(ja, ko, en ...)")
    ap.add_argument("--model", default="medium", help="whisper 모델(small은 빠르고 덜 정확)")
    ap.add_argument("--title")
    ap.add_argument("--artist")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    lines = read_lines(args.lyrics)
    subs_files = [read_lines(p) for p in args.sub]
    for path, sub in zip(args.sub, subs_files):
        if len(sub) != len(lines):
            raise SystemExit(f"{path}: {len(sub)}줄 — 가사({len(lines)}줄)와 줄 수가 달라요")
    aligned = align_lines(lines, transcribe(args.audio, args.model, args.language))
    missing = [i + 1 for i, ln in enumerate(aligned) if not ln.marks]
    meta = {k: v for k, v in (("ti", args.title), ("ar", args.artist)) if v}
    subs = [list(group) for group in zip(*subs_files)] if subs_files else None
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(to_lrc(aligned, subs=subs, meta=meta))
    print(f"{args.out}  ({len(lines)}줄" + (f", 인식 못 해 앞뒤로 추정한 줄: {missing}" if missing else "") + ")")


if __name__ == "__main__":
    main()
