"""일본어 가사 → 한글 발음, 그리고 사람이 쓴 발음과 대조해 오타 의심 자리 찾기.

    카베니모타레테 ← かべにもたれて
    っ → 앞 글자 받침 ㅅ(잇쇼), ん → 받침 ㄴ(신쥬쿠), 장음 ー는 생략(와루도)

한자 읽기는 pykakasi(선택 설치: pip install pykakasi)로 히라가나로 바꾼 뒤 변환한다. 사전 읽기가
틀릴 수 있어서(예: 失っ) 자동으로 고치지 않고 다른 자리만 알려준다.
"""

from __future__ import annotations

import difflib

# 가나(히라가나) → 한글. 두 글자 조합(きゃ 등)을 먼저 본다.
_PAIRS = {}
for kana, kor in {
    "きゃ": "캬", "きゅ": "큐", "きょ": "쿄", "ぎゃ": "갸", "ぎゅ": "규", "ぎょ": "교",
    "しゃ": "샤", "しゅ": "슈", "しぇ": "셰", "しょ": "쇼", "じゃ": "쟈", "じゅ": "쥬", "じぇ": "제", "じょ": "죠",
    "ちゃ": "챠", "ちゅ": "츄", "ちぇ": "체", "ちょ": "쵸", "にゃ": "냐", "にゅ": "뉴", "にょ": "뇨",
    "ひゃ": "햐", "ひゅ": "휴", "ひょ": "효", "びゃ": "뱌", "びゅ": "뷰", "びょ": "뵤",
    "ぴゃ": "퍄", "ぴゅ": "퓨", "ぴょ": "표", "みゃ": "먀", "みゅ": "뮤", "みょ": "묘",
    "りゃ": "랴", "りゅ": "류", "りょ": "료", "ふぁ": "파", "ふぃ": "피", "ふぇ": "페", "ふぉ": "포",
    "てぃ": "티", "でぃ": "디", "とぅ": "투", "うぃ": "위", "うぇ": "웨", "うぉ": "워",
}.items():
    _PAIRS[kana] = kor
_SINGLE = dict(zip(
    "あいうえおかきくけこがぎぐげごさしすせそざじずぜぞたちつてとだぢづでどなにぬねの"
    "はひふへほばびぶべぼぱぴぷぺぽまみむめもやゆよらりるれろわをゔぁぃぅぇぉゃゅょゎ",
    ["아", "이", "우", "에", "오", "카", "키", "쿠", "케", "코", "가", "기", "구", "게", "고",
     "사", "시", "스", "세", "소", "자", "지", "즈", "제", "조", "타", "치", "츠", "테", "토",
     "다", "지", "즈", "데", "도", "나", "니", "누", "네", "노", "하", "히", "후", "헤", "호",
     "바", "비", "부", "베", "보", "파", "피", "푸", "페", "포", "마", "미", "무", "메", "모",
     "야", "유", "요", "라", "리", "루", "레", "로", "와", "오", "부", "아", "이", "우", "에", "오",
     "야", "유", "요", "와"]))
_FINAL_S, _FINAL_N = 19, 4  # 받침 ㅅ, ㄴ (한글 조합 종성 번호)


def _add_final(syllable: str, final: int) -> str | None:
    """받침 없는 한글 음절에 받침을 붙인다. 붙일 수 없으면 None."""
    code = ord(syllable) - 0xAC00
    if not (0 <= code < 11172) or code % 28:
        return None
    return chr(0xAC00 + code + final)


def _to_hiragana(text: str) -> str:
    return "".join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in text)


def kana_to_hangul(text: str) -> str:
    """가나(히라가나·가타카나) → 한글 발음. 가나가 아닌 글자(영문·한자·부호)는 그대로 둔다."""
    text = _to_hiragana(text)
    out: list[str] = []
    i = 0
    while i < len(text):
        two, one = text[i:i + 2], text[i]
        if two in _PAIRS:
            out.append(_PAIRS[two])
            i += 2
            continue
        if one in ("っ", "ん"):
            final = _FINAL_S if one == "っ" else _FINAL_N
            merged = _add_final(out[-1], final) if out and len(out[-1]) == 1 else None
            if merged:
                out[-1] = merged
            elif one == "ん":
                out.append("ㄴ")  # 맨 앞의 ん 등
            i += 1
            continue
        if one == "ー":  # 장음은 적지 않는다(와루도)
            i += 1
            continue
        out.append(_SINGLE.get(one, one))
        i += 1
    return "".join(out)


def japanese_to_hangul(text: str) -> str:
    """일본어(한자 포함) → 한글 발음. 조사 は·へ·を는 와·에·오로."""
    try:
        import pykakasi
    except ImportError as e:
        raise ImportError("한자 읽기에 pykakasi가 필요합니다: pip install pykakasi") from e
    parts = []
    for item in pykakasi.kakasi().convert(text):
        hira = item["hira"]
        if item["orig"] == "は" or hira == "は" and parts:
            hira = "わ"
        elif item["orig"] in ("へ", "を"):
            hira = {"へ": "え", "を": "お"}[item["orig"]]
        parts.append(kana_to_hangul(hira))
    return "".join(parts)


# 조사처럼 표기와 발음이 다른 자리: 서로 바뀌어 있어도 오타로 치지 않는다
_SAME = {frozenset({"하", "와"}), frozenset({"헤", "에"})}


def compare(expected: str, given: str) -> list[tuple[str, str]]:
    """대조해 다른 부분 [(자동 발음 쪽, 쓴 발음 쪽), ...]."""
    # 글자만 비교(띄어쓰기·부호·괄호는 빼고)
    a = "".join(c for c in expected if c.isalnum())
    b = "".join(c for c in given if c.isalnum())
    diffs = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        x, y = a[i1:i2], b[j1:j2]
        if len(x) == len(y) and all(c1 == c2 or frozenset({c1, c2}) in _SAME for c1, c2 in zip(x, y)):
            continue
        if any(c.isascii() and c.isalpha() for c in x):
            continue  # 영문 단어(World 등)는 읽는 법이 제각각이라 비교하지 않음
        diffs.append((x, y))
    return diffs


def check_lines(originals: list[str], prons: list[str], to_hangul=japanese_to_hangul):
    """줄마다 [(줄 번호, 자동 발음, 쓴 발음, 다른 부분)] — 다른 부분이 있는 줄만."""
    report = []
    for n, (orig, pron) in enumerate(zip(originals, prons), 1):
        auto = to_hangul(orig)
        diffs = compare(auto, pron)
        if diffs:
            report.append((n, auto, pron, diffs))
    return report
