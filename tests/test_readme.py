"""README에 적힌 명령·설정 예시가 실제 코드와 맞는지(문서가 낡지 않았는지) 확인한다."""
import json
import os
import re
import shlex
import unittest

from shorts import cli, lrc, project, styles

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
    README = f.read()
BLOCKS = re.findall(r"```(\w*)\n(.*?)```", README, re.S)


def shorts_commands():
    """README의 `python3 -m shorts ...` 명령(코드 블록 + 표의 인라인 코드)."""
    found = []
    for _, body in BLOCKS:
        found += [l for l in body.splitlines() if l.startswith("python3 -m shorts")]
    found += re.findall(r"`(python3 -m shorts [^`]+)`", README)
    cmds = []
    for line in found:
        line = line.split("  #")[0].strip()
        argv = shlex.split(line)[3:]
        if "--help" not in argv:
            cmds.append(argv)
    return cmds


class ReadmeTest(unittest.TestCase):
    def test_every_command_parses(self):
        cmds = shorts_commands()
        self.assertGreater(len(cmds), 10)
        for argv in cmds:
            with self.subTest(cmd=" ".join(argv)):
                cli.build_parser().parse_args(argv)  # 없는 옵션이면 SystemExit

    def test_json_examples_are_valid(self):
        examples = [json.loads(body) for kind, body in BLOCKS if kind == "json"]
        self.assertTrue(examples)
        for data in examples:
            with self.subTest(data=data):
                if "lyrics" in data:  # 곡 설정 파일
                    self.assertLessEqual(set(data), set(project.KEYS))
                else:  # 스타일
                    styles.style_from_dict(data, ROOT)

    def test_lrc_example_parses_with_karaoke_line(self):
        body = next(b for _, b in BLOCKS if b.startswith("[ti:"))
        ly = lrc.parse(body)
        self.assertEqual(ly.meta["ti"], "곡 제목")
        self.assertEqual(len(ly.lines), 2)
        self.assertTrue(ly.lines[1].marks)

    def test_style_table_lists_every_preset(self):
        for name in styles.list_presets():
            self.assertIn(f"| `{name}` |", README)

    def test_project_keys_documented(self):
        line = next(l for l in README.splitlines() if l.startswith("- 쓸 수 있는 항목:"))
        self.assertEqual(set(line.split("`")[1].split()), set(project.KEYS))


if __name__ == "__main__":
    unittest.main()
