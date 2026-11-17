"""곡 설정 파일: 한 곡을 렌더하는 데 필요한 것을 JSON 하나에 적어 둔다.

    {
      "lyrics": "노래.lrc",
      "audio": "노래.mp3",
      "bg": "배경.jpg",
      "cover": "앨범.jpg",
      "style": "photo",                     (프리셋 이름, 스타일 파일, 또는 {...} 직접)
      "title": "제목", "artist": "가수",
      "start": ["0:45", "1:30"],            ("0:45,1:30" 이나 45 도 됨)
      "duration": 20,
      "fps": 30,
      "out": "출력/노래.mp4"
    }

파일 경로는 이 JSON 파일이 있는 폴더 기준. 명령줄 옵션이 있으면 그게 우선.
"""

from __future__ import annotations

import argparse
import json
import os
import re

PATH_KEYS = ("lyrics", "audio", "bg", "cover", "font", "out")
TEXT_KEYS = ("title", "artist")
KEYS = PATH_KEYS + TEXT_KEYS + ("style", "start", "duration", "fps", "preview")


_TIME = re.compile(r"^(?:(\d+):)?(\d+(?:\.\d+)?)$")


def parse_time(text: str) -> float:
    """'45', '0:45', '1:02.5' 같은 표기를 초로."""
    m = _TIME.match(text.strip())
    if not m:
        raise argparse.ArgumentTypeError(f"시간 형식이 아닙니다: {text!r} (예: 45, 0:45, 1:02.5)")
    minutes, seconds = m.group(1), float(m.group(2))
    if minutes is not None and seconds >= 60:
        raise argparse.ArgumentTypeError(f"초는 60 미만이어야 합니다: {text!r}")
    return int(minutes or 0) * 60 + seconds


def parse_times(text: str) -> list[float]:
    """'0:45,1:30' 처럼 쉼표로 나눈 여러 시간."""
    parts = [p for p in text.split(",") if p.strip()]
    if not parts:
        raise argparse.ArgumentTypeError(f"시간이 없습니다: {text!r}")
    return [parse_time(p) for p in parts]


def _times(key: str, value) -> list[float]:
    try:
        if isinstance(value, bool):
            raise ValueError
        if isinstance(value, (int, float)):
            return [float(value)]
        if isinstance(value, str):
            return parse_times(value)
        if isinstance(value, list) and value:
            return [float(v) if isinstance(v, (int, float)) and not isinstance(v, bool)
                    else parse_time(str(v)) for v in value]
    except Exception:
        pass
    raise ValueError(f"{key}: 시간은 45, \"0:45\", \"0:45,1:30\", [\"0:45\", 90] 같은 형식이어야 합니다 "
                     f"(받은 값: {value!r})")


def load_project(path: str) -> dict:
    """곡 설정 파일을 읽어 검사하고, 경로는 절대 경로로, 시간은 초 목록으로 바꾼다."""
    path = os.path.abspath(path)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: JSON 형식 오류 ({e})") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path}: 최상위는 {{...}} 객체여야 합니다")
    unknown = sorted(set(data) - set(KEYS))
    if unknown:
        raise ValueError(f"{path}: 알 수 없는 항목 {', '.join(unknown)} (쓸 수 있는 항목: {', '.join(KEYS)})")
    if "lyrics" not in data:
        raise ValueError(f"{path}: \"lyrics\"(LRC 가사 파일)가 필요합니다")

    base = os.path.dirname(path)
    out: dict = {"_base": base, "_stem": os.path.splitext(path)[0]}
    for key, value in data.items():
        if key in PATH_KEYS or key in TEXT_KEYS:
            if not isinstance(value, str):
                raise ValueError(f"{key}: 문자열이어야 합니다 (받은 값: {value!r})")
            out[key] = os.path.join(base, os.path.expanduser(value)) if key in PATH_KEYS else value
        elif key in ("start", "duration"):
            out[key] = _times(key, value)
        elif key == "fps":
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"fps: 양의 정수여야 합니다 (받은 값: {value!r})")
            out[key] = value
        elif key == "preview":
            if not isinstance(value, bool):
                raise ValueError(f"preview: true/false 여야 합니다 (받은 값: {value!r})")
            out[key] = value
        elif key == "style":
            if isinstance(value, str):
                local = os.path.join(base, value)
                out[key] = local if os.path.isfile(local) else value  # 파일이 아니면 프리셋 이름
            elif isinstance(value, dict):
                out[key] = value
            else:
                raise ValueError(f"style: 프리셋 이름, 파일 경로, 또는 {{...}} 이어야 합니다 (받은 값: {value!r})")
    for key in ("lyrics", "audio", "bg", "cover", "font"):
        if key in out and not os.path.isfile(out[key]):
            raise ValueError(f"{key}: 파일이 없습니다: {out[key]}")
    return out
