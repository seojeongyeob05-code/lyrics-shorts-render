"""정답을 아는 합성 목소리로 발성 분석이 습관을 맞히는지 확인.

python3 -m pytest tests/  또는  python3 tests/test_analysis.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tests.make_test_voices import main as make_voices  # noqa: E402
from voiceanalysis.analyze import analyze  # noqa: E402
from voiceanalysis.inverse import Inverter  # noqa: E402

EXPECT = {
    "healthy": set(),
    "breathy": {"breathy"},
    "pushing": {"pushing"},
    "pressed": {"pressed"},
}


def test_ground_truth():
    d = tempfile.mkdtemp()
    make_voices(d)
    inv = Inverter()
    for name, want in EXPECT.items():
        res = analyze(os.path.join(d, f"{name}.wav"), inv)
        got = [i["id"] for i in res["issues"]]
        if want:
            assert got and got[0] in want, (name, got)
        else:
            assert not got, (name, got)


if __name__ == "__main__":
    test_ground_truth()
    print("ok")
