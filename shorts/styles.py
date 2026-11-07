"""스타일 프리셋: JSON 파일로 Style 값을 바꿔 끼운다.

    {"text_color": "#FFE066", "font_size": 80, "center_y": 0.62}

- 색은 "#RRGGBB" 또는 [r, g, b]
- font_path가 상대 경로면 JSON 파일 위치 기준
- 적지 않은 값은 Style 기본값
- "extends": "neon" 으로 다른 프리셋을 이어받을 수 있다
"""

from __future__ import annotations

import dataclasses
import json
import os
import typing

from .frame import Style

PRESET_DIR = os.path.join(os.path.dirname(__file__), "presets")
_FIELDS = {f.name: f for f in dataclasses.fields(Style)}
_HINTS = typing.get_type_hints(Style)


def list_presets() -> list[str]:
    return sorted(n[:-5] for n in os.listdir(PRESET_DIR) if n.endswith(".json"))


def _resolve(name_or_path: str) -> str:
    if os.path.isfile(name_or_path):
        return name_or_path
    path = os.path.join(PRESET_DIR, f"{name_or_path}.json")
    if os.path.isfile(path):
        return path
    raise ValueError(f"스타일을 찾을 수 없습니다: {name_or_path!r} "
                     f"(내장 프리셋: {', '.join(list_presets())} 또는 JSON 파일 경로)")


def _color(key: str, value) -> tuple[int, int, int]:
    if isinstance(value, str) and len(value) == 7 and value.startswith("#"):
        try:
            return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
        except ValueError:
            pass
    elif (isinstance(value, list) and len(value) == 3
          and all(isinstance(c, int) and 0 <= c <= 255 for c in value)):
        return tuple(value)
    raise ValueError(f"{key}: 색은 \"#RRGGBB\" 또는 [r, g, b] 형식이어야 합니다 (받은 값: {value!r})")


def _convert(key: str, value, base_dir: str):
    hint = _HINTS[key]
    if key.endswith("_color") or key == "progress_track":
        return _color(key, value)
    if key == "font_path":
        if value is None:
            return None
        return os.path.normpath(os.path.join(base_dir, os.path.expanduser(value)))
    if hint is bool:
        if not isinstance(value, bool):
            raise ValueError(f"{key}: true/false 여야 합니다 (받은 값: {value!r})")
        return value
    if hint is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key}: 정수여야 합니다 (받은 값: {value!r})")
        return value
    if hint is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key}: 숫자여야 합니다 (받은 값: {value!r})")
        return float(value)
    return value


def load_style(name_or_path: str, _seen: tuple[str, ...] = ()) -> Style:
    """내장 프리셋 이름이나 JSON 파일 경로로 Style을 만든다."""
    path = os.path.abspath(_resolve(name_or_path))
    if path in _seen:
        raise ValueError(f"extends가 순환합니다: {' → '.join(_seen + (path,))}")
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}: JSON 형식 오류 ({e})") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path}: 최상위는 {{...}} 객체여야 합니다")

    base = load_style(data.pop("extends"), _seen + (path,)) if "extends" in data else Style()
    data.pop("description", None)
    unknown = sorted(set(data) - set(_FIELDS))
    if unknown:
        raise ValueError(f"{path}: 알 수 없는 항목 {', '.join(unknown)} "
                         f"(쓸 수 있는 항목: {', '.join(_FIELDS)})")
    base_dir = os.path.dirname(path)
    return dataclasses.replace(base, **{k: _convert(k, v, base_dir) for k, v in data.items()})
