"""Tests for tools/build_pages.py: the progress chart and the README block.

Run from the repo root: python3 -m unittest discover -s tests -v
"""

import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("build_pages", str(REPO / "tools" / "build_pages.py"))
build_pages = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_pages)  # type: ignore[union-attr]

WORDS = {"words": 200, "en": 50, "nl": 40, "es": 0, "reviewed": 10}


def audit(id_, date, table, n, errors, auditor="test-user"):
    return {"id": id_, "date": date, "table": table, "sample_size": str(n), "errors": str(errors),
            "method": "test", "auditor": auditor, "notes": ""}


def repo_stats(audits=()):
    rs = build_pages.repo_stats(dict(WORDS))
    rs["machine"], rs["flaggable"] = 3, 4
    rs["audits"] = build_pages.latest_audits(list(audits))
    return rs


class ProgressTest(unittest.TestCase):
    def stats(self):
        return repo_stats()

    def test_chart_is_valid_svg_in_both_themes(self):
        for theme in build_pages.THEMES:
            with self.subTest(theme=theme):
                svg = build_pages.progress_svg(repo_stats(), theme)
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

    def test_sentence_rows(self):
        rs = self.stats()
        rs["sentences"] = {"prompts": 300, "prompts_reviewed": 7, "held_out": 45, "translated": 12, "pairs": 20, "pairs_reviewed": 5}
        block = build_pages.readme_block(rs)
        self.assertIn("| [Sentence prompts](corpus/parallel/) (English and Spanish; 45 held out for tests) | 300 | 7 |", block)
        self.assertIn("| Aruban Papiamento sentence translations | 20 | 5 |", block)
        svg = build_pages.progress_svg(rs, "light")
        self.assertIn("SENTENCES", svg)
        self.assertIn("12 of 300", svg)
        rs["sentences"] = {"prompts": 0, "held_out": 0, "translated": 0, "pairs": 0, "pairs_reviewed": 0}
        self.assertNotIn("Sentence prompts", build_pages.readme_block(rs))
        self.assertNotIn("SENTENCES", build_pages.progress_svg(rs, "light"))

    def test_front_matter_matches_the_gauntlet(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rule-ort-test-001.md"
            path.write_text('---\nid: RULE_ORT_TEST_001\nstatus: "reviewed"\nseverity: error  # comment\n---\n',
                            encoding="utf-8")
            meta = build_pages.front_matter(str(path))
        self.assertEqual(meta["status"], "reviewed")
        self.assertEqual(meta["severity"], "error")

    def test_still_empty_line(self):
        rs = self.stats()
        rs["empty"] = []
        self.assertNotIn("Still empty", build_pages.readme_block(rs))
        rs["empty"] = ["names"]
        self.assertIn("Still empty: names.", build_pages.readme_block(rs))
        rs["empty"] = ["names", "public holidays", "the corpus"]
        self.assertIn("Still empty: names, public holidays and the corpus.", build_pages.readme_block(rs))

    def test_closed_classes_are_counted(self):
        # The closed word classes count as one of the other tables: a row in
        # the README table, part of the chart's "Rows reviewed" bar, and no
        # longer "still empty" once lexicon/closed-classes/ has rows.
        rs = self.stats()
        other = dict((key, (label, n, reviewed)) for key, label, n, reviewed in rs["other"])
        self.assertIn("closed-classes", other)
        label, n, reviewed = other["closed-classes"]
        self.assertEqual(n, len(build_pages.table_rows("closed-classes")))
        self.assertGreater(n, 0)
        self.assertNotIn("closed word classes", rs["empty"])
        self.assertIn("| %s | %s | %s | not audited yet |" % (label, build_pages.fmt(n), build_pages.fmt(reviewed)),
                      build_pages.readme_block(rs))
        svg = build_pages.progress_svg(rs, "light")
        total = sum(count for _, _, count, _ in rs["other"])
        self.assertIn("of %s" % build_pages.fmt(total), svg.split(">Rows reviewed<", 1)[1])



class RegistryTest(unittest.TestCase):
    def test_tables_are_read_through_the_registry(self):
        # The counts use the registry's globs, so a glob typo (which the
        # gauntlet reports) cannot leave the README showing an old count.
        with open(build_pages.REGISTRY, encoding="utf-8") as f:
            registry = json.load(f)
        self.assertGreater(len(build_pages.table_rows("loanwords")), 0)
        for entry in registry["tables"]:
            if entry["name"] == "loanwords":
                entry["glob"] = "lexicon/loanword/*.tsv"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            saved = build_pages.REGISTRY
            build_pages.REGISTRY = str(path)
            try:
                self.assertEqual(build_pages.table_rows("loanwords"), [])
                with self.assertRaises(SystemExit):
                    build_pages.table_rows("no-such-table")
            finally:
                build_pages.REGISTRY = saved


class QualityTest(unittest.TestCase):
    AUDITS = [
        audit("aud-0001", "2026-01-01", "words", 200, 9),
        audit("aud-0002", "2026-02-01", "words", 200, 0),
        audit("aud-0003", "2026-02-01", "translations", 60, 2, auditor="machine"),
    ]

    def test_wilson_interval(self):
        low, high = build_pages.wilson(2, 60)
        self.assertAlmostEqual(low, 0.0092, places=4)
        self.assertAlmostEqual(high, 0.1136, places=4)
        self.assertEqual(build_pages.wilson(0, 200)[0], 0.0)
        self.assertAlmostEqual(build_pages.wilson(0, 200)[1], 0.0188, places=4)
        self.assertEqual(build_pages.wilson(30, 30)[1], 1.0)

    def test_latest_audit_per_table(self):
        latest = build_pages.latest_audits(self.AUDITS + [
            audit("aud-0004", "2026-02-01", "numbers", 30, 1),
            audit("aud-0005", "2026-02-01", "numbers", 30, 2),  # same day: the higher id wins
            audit("aud-0006", "2026-03-01", "grammar", 5, 6),  # errors > sample_size: skipped
            audit("aud-0007", "2026-03-01", "grammar", 0, 0),  # empty sample: skipped
            audit("aud-0008", "2026-03-01", "calendar", "x", 0),  # not a number: skipped
        ])
        self.assertEqual(sorted(latest), ["numbers", "translations", "words"])
        self.assertEqual(latest["words"]["id"], "aud-0002")
        self.assertEqual(latest["numbers"]["id"], "aud-0005")

    def test_readme_without_audits(self):
        rs = repo_stats()
        block = build_pages.readme_block(rs)
        self.assertIn("| Table | Rows | Reviewed by the board | Measured error rate |", block)
        self.assertIn("| 200 | 10 | not audited yet |", block)
        # Words, the other tables, grammar rules and machine rules
        sentence_rows = 2 if rs.get("sentences", {}).get("prompts") else 0
        self.assertEqual(block.count("not audited yet"), 1 + len(build_pages.OTHER_TABLES) + 2 + sentence_rows)
        self.assertIn("_meta/audits.tsv", block)
        self.assertNotIn("Measured error rate in the latest", block)  # alt text

    def test_readme_error_rate(self):
        block = build_pages.readme_block(repo_stats(self.AUDITS))
        self.assertIn("| 200 | 10 | 0% (0 of 200)<br><sub>95% CI 0\u20131.9%, checked on 2026-02-01</sub>"
                      "<br>Translations: 3.3% (2 of 60)<br><sub>95% CI 0.9\u201311.4%, checked by machine on "
                      "2026-02-01</sub> |", block)
        self.assertIn("Words 0% (0 of 200); Word translations 3.3% (2 of 60).", block)  # alt text
        self.assertIn('"Checked by machine" means', block)
        self.assertNotIn('"Checked by machine" means', build_pages.readme_block(repo_stats(self.AUDITS[:2])))

    def test_quality_section_only_once_audited(self):
        for theme in build_pages.THEMES:
            with self.subTest(theme=theme):
                self.assertNotIn("QUALITY", build_pages.progress_svg(repo_stats(), theme))
                svg = build_pages.progress_svg(repo_stats(self.AUDITS), theme)
                ET.fromstring(svg)
                self.assertIn(">QUALITY<", svg)
                self.assertIn("2 of 60 wrong", svg)
                self.assertIn(">3.3%<", svg)
                self.assertIn(">25%<", svg)
                self.assertNotIn(">Numbers<", svg)  # only audited tables get a row

    def test_quality_scale_fits_the_widest_range(self):
        svg = build_pages.progress_svg(repo_stats([audit("aud-0001", "2026-01-01", "numbers", 30, 9)]), "light")
        self.assertIn(">50%<", svg)  # 9 of 30: the range reaches 47.9%
        svg = build_pages.progress_svg(repo_stats([audit("aud-0001", "2026-01-01", "numbers", 3, 3)]), "light")
        self.assertIn(">100%<", svg)

    def test_output_is_deterministic(self):
        rs = repo_stats(self.AUDITS)
        self.assertEqual(build_pages.progress_svg(rs, "dark"), build_pages.progress_svg(rs, "dark"))
        self.assertEqual(build_pages.readme_block(rs), build_pages.readme_block(rs))

    def test_milestones_line(self):
        rows = [{"id": "P0", "title": "Foundation", "status": "done"},
                {"id": "P1", "title": "Clean data", "status": "in-progress"},
                {"id": "P3", "title": "Products", "status": "not-started"}]
        self.assertEqual(build_pages.milestones_line(rows),
                         "Milestones: **P0 Foundation** \u2705 done \u00b7 **P1 Clean data** \U0001f7e1 in progress"
                         " \u00b7 **P3 Products** \u2b1c not started. [What is left](_meta/milestones.tsv)")
        self.assertIsNone(build_pages.milestones_line([]))
        rs = repo_stats()
        rs["milestones"] = rows
        block = build_pages.readme_block(rs)
        self.assertLess(block.index("Milestones:"), block.index("<picture>"))
        rs["milestones"] = []
        self.assertNotIn("Milestones:", build_pages.readme_block(rs))

    def test_milestone_statuses_match_the_schema(self):
        with open(str(REPO / "_meta" / "schema" / "milestones.schema.json"), encoding="utf-8") as f:
            fields = dict((fs["name"], fs) for fs in json.load(f)["fields"])
        self.assertEqual(sorted(fields["status"]["constraints"]["enum"]), sorted(build_pages.MILESTONE_STATUS))

    def test_audit_tables_match_the_schema(self):
        with open(str(REPO / "_meta" / "schema" / "audits.schema.json"), encoding="utf-8") as f:
            fields = dict((fs["name"], fs) for fs in json.load(f)["fields"])
        self.assertEqual(fields["table"]["constraints"]["enum"], [k for k, _ in build_pages.AUDIT_TABLES])
        for key, _ in build_pages.OTHER_TABLES:
            self.assertIn(key, fields["table"]["constraints"]["enum"])


if __name__ == "__main__":
    unittest.main()
