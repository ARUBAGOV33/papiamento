"""Tests for tools/build_pages.py: the progress chart and the README block.

Run from the repo root: python3 -m unittest discover -s tests -v
"""

import importlib.util
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("build_pages", str(REPO / "tools" / "build_pages.py"))
build_pages = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_pages)  # type: ignore[union-attr]

WORDS = {"words": 200, "en": 50, "nl": 40, "es": 0, "reviewed": 10}


class ProgressTest(unittest.TestCase):
    def stats(self):
        rs = build_pages.repo_stats(dict(WORDS))
        rs["machine"], rs["flaggable"] = 3, 4
        return rs

    def test_chart_is_valid_svg_in_both_themes(self):
        for theme in build_pages.THEMES:
            with self.subTest(theme=theme):
                svg = build_pages.progress_svg(self.stats(), theme)
                root = ET.fromstring(svg)
                self.assertTrue(root.tag.endswith("svg"))
                self.assertIn("50 of 200", svg)
                self.assertIn("3/4", svg)

    def test_empty_bar_has_no_fill(self):
        svg = build_pages.progress_svg(self.stats(), "light")
        # Spanish is 0 of 200: a track but no coloured bar on that row.
        row = svg.split(">With Spanish<", 1)[1].split(">Reviewed by the board<", 1)[0]
        self.assertEqual(row.count("<rect"), 1)

    def test_readme_block(self):
        block = build_pages.readme_block(self.stats())
        self.assertTrue(block.startswith(build_pages.REPO_START))
        self.assertTrue(block.endswith(build_pages.REPO_END))
        self.assertIn("progress-dark.svg", block)
        self.assertIn("| 200 | 10 |", block)
        self.assertIn("25% with English", block)

    def test_repository_pages_are_up_to_date(self):
        result = subprocess.run([sys.executable, str(REPO / "tools" / "build_pages.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
