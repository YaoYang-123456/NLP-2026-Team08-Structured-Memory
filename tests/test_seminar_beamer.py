"""Offline regression test for the final seminar's Beamer generator."""
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DECK = Path("reports/seminar-20261022")
SCRIPT = DECK / "tools/make_pdf_tex.py"
PREAMBLE = Path("reports/homework/slides/preamble.tex")


def tiny_png():
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload +
                struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff")) +
            chunk(b"IEND", b""))


class SeminarBeamerTests(unittest.TestCase):
    def test_fresh_directory_and_non_ascii_math_and_team_table(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / DECK
            (target / "tools").mkdir(parents=True)
            (root / PREAMBLE).parent.mkdir(parents=True)
            shutil.copy2(REPO / SCRIPT, root / SCRIPT)
            shutil.copy2(REPO / PREAMBLE, root / PREAMBLE)

            slides = [
                {"kind": "cover", "title": "占位页", "source": "来源 #1",
                 "speech": "", "lines": ["占位内容"]}
                for _ in range(11)
            ]
            slides[5] = {
                "kind": "cases", "title": "时间案例", "source": "来源 #6",
                "speech": "", "columns": [
                    {"heading": "记录日期 ≠ 事件年份", "body": ["去年"]},
                    {"heading": "观察", "body": ["原话"]}
                ]
            }
            slides[7] = {
                "kind": "team", "title": "团队分工", "source": "项目 #8",
                "speech": "", "rows": [
                    ["任务 / 账号", "实际贡献", "当前比例"],
                    ["B · YaoYang-123456", "原始检索、MetaMem 阅读", "待全组确认"],
                    ["D · lanshuheng9-oss", "跨事件综合、问答", "待全组确认"]
                ]
            }
            slides[10]["lines"] = ["原始裁判 ≠ AI 复核 ≠ 成员人工验收"]
            (target / "seminar-content.json").write_text(
                json.dumps({"title": "测试", "slides": slides}, ensure_ascii=False),
                encoding="utf-8"
            )

            out = root / "fresh" / "nested-output"
            (out / "preview").mkdir(parents=True)
            (out / "preview/slide-01.png").write_bytes(tiny_png())
            completed = subprocess.run(
                [sys.executable, str(root / SCRIPT), str(out)],
                cwd=root, capture_output=True, text=True
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            generated = (out / "source/beamer/main.tex").read_text(encoding="utf-8")
            committed = (target / "final-candidate.tex").read_text(encoding="utf-8")
            self.assertTrue((out / "source/beamer/preamble.tex").is_file())
            self.assertTrue((out / "第8队-研讨候选-20261020.pdf").is_file())
            self.assertIn(r"p{43mm}Yp{22mm}", generated)
            self.assertIn(r"\[0.3mm]", generated)
            self.assertEqual(generated.count(r"$\ne$"), 3)
            self.assertIn(r"\input{../homework/slides/preamble}", committed)
            self.assertEqual(committed.count(r"$\ne$"), 3)


if __name__ == "__main__":
    unittest.main()
