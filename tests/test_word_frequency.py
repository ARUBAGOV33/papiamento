"""Tests for tools/word_frequency.py. They use made-up rows and token lists,
so they need neither PyMuPDF nor the PDFs.

Run from the repo root: python3 -m unittest discover -s tests -v
"""

import importlib.util
import io
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "word_frequency.py"
_spec = importlib.util.spec_from_file_location("word_frequency", str(TOOL))
wf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wf)  # type: ignore[union-attr]


def word(id_, lemma, alt="", en=""):
    return {"id": id_, "lemma": lemma, "alt": alt, "en": en, "nl": "", "es": "", "status": "draft"}


class TestWordFrequency(unittest.TestCase):
    def test_tokenize_keeps_enye_and_apostrophes(self):
        self.assertEqual(wf.tokenize("Mañan, cumpr'e Bo’e!"), ["mañan", "cumpr'e", "bo'e"])

    def test_alt_forms_and_phrases_count(self):
        words = [word("pap-1", "cuater", alt="cuatro"), word("pap-2", "a base di")]
        tokens = wf.tokenize("cuater cuatro a base di cuater")
        rows = dict((r["id"], r) for r in wf.score_rows(words, tokens, []))
        self.assertEqual(rows["pap-1"]["pdf_count"], 3)
        self.assertEqual(rows["pap-2"]["pdf_count"], 1)

    def test_sentences_blend_in_once_they_exist(self):
        words = [word("pap-1", "awa"), word("pap-2", "cas")]
        pdf = wf.tokenize("awa awa awa cas")            # awa 750000, cas 250000 per million
        sentences = wf.tokenize("cas cas cas cas")      # cas 1000000 per million
        rows = wf.score_rows(words, pdf, sentences)
        self.assertEqual([r["lemma"] for r in rows], ["cas", "awa"])
        self.assertEqual(rows[0]["score"], 625000.0)     # (250000 + 1000000) / 2
        self.assertEqual(rows[1]["score"], 375000.0)     # (750000 + 0) / 2
        alone = wf.score_rows(words, pdf, [])
        self.assertEqual([r["lemma"] for r in alone], ["awa", "cas"])

    def test_order_is_deterministic_and_marks_translations(self):
        words = [word("pap-2", "b"), word("pap-1", "a", en="a"), word("pap-3", "c")]
        rows = wf.score_rows(words, [], [])
        self.assertEqual([r["id"] for r in rows], ["pap-1", "pap-2", "pap-3"])
        self.assertEqual(rows[0]["translated"], "yes")
        out = io.StringIO()
        wf.write(rows, out)
        self.assertEqual(out.getvalue().splitlines()[0], "\t".join(wf.COLUMNS))
        self.assertEqual(out.getvalue().splitlines()[1], "pap-1\ta\t0\t0\t0.00\tyes")

    def test_excluded_pdfs_are_the_word_lists(self):
        pdfs = [sid for sid, _ in wf.shareable_pdfs(str(TOOL.parent.parent))]
        self.assertNotIn("AB2018", pdfs)
        self.assertNotIn("VOC2009", pdfs)
        self.assertIn("MOR2010", pdfs)


if __name__ == "__main__":
    unittest.main()
