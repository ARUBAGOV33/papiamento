"""Tests for tools/add_prompts.py.

Run from the repo root: python3 -m unittest discover -s tests -v
"""

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "add_prompts.py"
_spec = importlib.util.spec_from_file_location("add_prompts", str(TOOL))
ap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ap)  # type: ignore[union-attr]

HEADER = "id\tlang\ttext\ttopic\torigin\torigin_ref\tauthor\tbatch\tlicence\tstatus\treviewed_by\tnotes\n"


class TestAddPrompts(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.root))
        for folder in ("corpus/parallel", "eval/parallel"):
            (self.root / folder).mkdir(parents=True)
            (self.root / folder / "prompts.tsv").write_text(HEADER, encoding="utf-8")

    def batch(self, lines):
        path = self.root / "batch.txt"
        path.write_text("# comment\n" + "\n".join(lines) + "\n", encoding="utf-8")
        return str(path)

    def rows(self, folder):
        return [l.split("\t") for l in (self.root / folder / "prompts.tsv").read_text(encoding="utf-8").splitlines()[1:]]

    def test_hold_out_is_fixed_by_the_id(self):
        self.assertEqual(ap.held_out("prm-000004"), ap.held_out("prm-000004"))
        share = sum(ap.held_out("prm-%06d" % n) for n in range(1, 2001)) / 2000.0
        self.assertTrue(0.12 < share < 0.18, share)

    def test_rules(self):
        self.assertEqual(ap.problems("Where is the bus stop?"), [])
        self.assertTrue(ap.problems("Meet me at 7."))                 # digit
        self.assertTrue(ap.problems("Turn on the TV."))               # abbreviation
        self.assertTrue(ap.problems("We (all) went home."))           # brackets
        self.assertTrue(ap.problems(" ".join(["word"] * 15) + "."))   # too long

    def test_adds_in_order_and_splits(self):
        lines = ["en|home|Sentence number %s is here." % w for w in
                 ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")]
        ap.main([self.batch(lines), "--batch", "prompts-1", "--author", "machine", "--root", str(self.root)])
        corpus, held = self.rows("corpus/parallel"), self.rows("eval/parallel")
        ids = sorted(r[0] for r in corpus + held)
        self.assertEqual(ids, ["prm-%06d" % n for n in range(1, 11)])
        self.assertTrue(all(ap.held_out(r[0]) for r in held))
        self.assertFalse(any(ap.held_out(r[0]) for r in corpus))
        self.assertEqual(corpus[0][6:9], ["machine", "prompts-1", "CC0-1.0"])

    def test_refuses_repeats_and_writes_nothing(self):
        ap.main([self.batch(["es|home|Apaga la luz."]), "--batch", "prompts-1", "--author", "machine", "--root", str(self.root)])
        before = (self.root / "corpus/parallel/prompts.tsv").read_text(encoding="utf-8") + \
            (self.root / "eval/parallel/prompts.tsv").read_text(encoding="utf-8")
        with self.assertRaises(SystemExit):
            ap.main([self.batch(["es|home|Apaga la luz.", "en|home|A new one here."]),
                     "--batch", "prompts-2", "--author", "machine", "--root", str(self.root)])
        after = (self.root / "corpus/parallel/prompts.tsv").read_text(encoding="utf-8") + \
            (self.root / "eval/parallel/prompts.tsv").read_text(encoding="utf-8")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
