"""Tests for tools/validate.py (the gauntlet).

Fixture layout: tests/fixtures/valid/ is a complete mini repo that passes.
Every other tests/fixtures/<case>/ holds only the files that differ from
valid/; build_repo() copies valid/, overlays the case, and adds a copy of the
real _meta/ so fixtures are always checked against the live schemas.
Byte-level cases (CRLF, NFD, bad UTF-8) and PDFs are written by the tests
themselves so editors and git cannot silently "fix" them.

Run from the repo root: python3 -m unittest discover -s tests -v
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
VALIDATOR = REPO / "tools" / "validate.py"

_spec = importlib.util.spec_from_file_location("validate", str(VALIDATOR))
validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate)  # type: ignore[union-attr]

WORDS_A = "lexicon/words/A/words.tsv"
NUMBERS = "lexicon/numbers/cardinals.tsv"
SOURCES = "sources/sources.tsv"


class GauntletCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def build_repo(self, case=None):
        root = Path(self._tmp.name) / "repo"
        shutil.copytree(str(FIXTURES / "valid"), str(root))
        shutil.copytree(str(REPO / "_meta"), str(root / "_meta"))
        if case is not None:
            shutil.copytree(str(FIXTURES / case), str(root), dirs_exist_ok=True)
        return root

    def run_gauntlet(self, root, strict=False):
        return validate.run(root, strict=strict)

    def check(self, case):
        return self.run_gauntlet(self.build_repo(case))

    def findings(self, ctx, gate=None, severity=None, path=None, contains=None):
        out = []
        for f in ctx.findings:
            if gate is not None and f.gate != gate:
                continue
            if severity is not None and f.severity != severity:
                continue
            if path is not None and f.path != path:
                continue
            if contains is not None and contains not in f.message:
                continue
            out.append(f)
        return out

    def assertFinding(self, ctx, gate, severity, path=None, contains=None, line=None):
        hits = self.findings(ctx, gate, severity, path, contains)
        if line is not None:
            hits = [f for f in hits if f.line == line]
        if not hits:
            self.fail("expected [%s] %s%s%s; got:\n%s" % (
                gate, severity, " at %s" % path if path else "",
                " containing %r" % contains if contains else "",
                dump(ctx)))
        return hits

    def assertNoFinding(self, ctx, gate=None, severity=None, path=None, contains=None):
        hits = self.findings(ctx, gate, severity, path, contains)
        if hits:
            self.fail("unexpected findings:\n%s" % "\n".join(fmt(f) for f in hits))


def fmt(f):
    return "%s [%s] %s %s" % (f.location(), f.gate, f.severity, f.message)


def dump(ctx):
    return "\n".join(fmt(f) for f in ctx.findings) or "(no findings)"


def rewrite(path, fn):
    text = path.read_bytes().decode("utf-8")
    path.write_bytes(fn(text))


# ---------------------------------------------------------------------------

class TestValidRepo(GauntletCase):
    def test_valid_repo_has_no_findings(self):
        ctx = self.check(None)
        self.assertEqual(ctx.findings, [], dump(ctx))
        self.assertTrue(validate.is_ok(ctx))
        self.assertEqual(len(ctx.files), 5)  # A, C, numbers, sources, known-facts
        self.assertGreaterEqual(ctx.facts_checked, 1)  # fact-0009: 7 -> shete

    def test_cli_exit_zero_and_json_shape(self):
        root = self.build_repo()
        proc = subprocess.run([sys.executable, str(VALIDATOR), "--root", str(root), "--json"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stdout.decode() + proc.stderr.decode())
        report = json.loads(proc.stdout.decode("utf-8"))
        self.assertTrue(report["ok"])
        self.assertEqual(sorted(report["gates"]), validate.GATES)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["files_checked"], 5)
        self.assertGreater(report["rows_checked"], 5)

    def test_cli_human_output_and_exit_one(self):
        root = self.build_repo("bad_enum")
        proc = subprocess.run([sys.executable, str(VALIDATOR), "--root", str(root)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8")
        self.assertEqual(proc.returncode, 1, out)
        self.assertIn("%s:3: [G2] ERROR status: 'approved'" % WORDS_A, out)
        self.assertIn("RESULT: FAIL", out)


class TestG0SourceTrace(GauntletCase):
    def test_reviewed_without_page(self):
        ctx = self.check("reviewed_without_page")
        self.assertFinding(ctx, "G0", "error", WORDS_A, "source and page", line=3)

    def test_untraced_is_warning(self):
        ctx = self.check("untraced")
        self.assertFinding(ctx, "G0", "warning", WORDS_A, "untraced", line=3)
        self.assertTrue(validate.is_ok(ctx), dump(ctx))

    def test_strict_turns_warnings_into_errors(self):
        ctx = self.run_gauntlet(self.build_repo("untraced"), strict=True)
        self.assertFinding(ctx, "G0", "error", WORDS_A, "untraced")
        self.assertFalse(validate.is_ok(ctx))

    def test_unknown_source(self):
        ctx = self.check("unknown_source")
        self.assertFinding(ctx, "G0", "error", WORDS_A, "XYZ2020", line=3)

    def test_missing_sources_tsv_warns_once(self):
        root = self.build_repo("unknown_source")
        (root / SOURCES).unlink()
        ctx = self.run_gauntlet(root)
        hits = self.assertFinding(ctx, "G0", "warning", SOURCES, "not found")
        self.assertEqual(len(hits), 1)
        self.assertNoFinding(ctx, "G0", "error")

    def test_missing_card(self):
        ctx = self.check("missing_card")
        self.assertFinding(ctx, "G0", "error", SOURCES, "card sources/cards/NOPE2000.md")

    def test_permission_without_ref(self):
        ctx = self.check("permission_without_ref")
        self.assertFinding(ctx, "G0", "error", SOURCES, "permission_ref", line=3)

    def test_pdf_without_sources_row(self):
        root = self.build_repo()
        (root / "sources/pdf").mkdir(parents=True)
        (root / "sources/pdf/XYZ2020.pdf").write_bytes(b"%PDF-1.4 fixture\n")
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G0", "error", "sources/pdf/XYZ2020.pdf", "not referenced")

    def _with_ab_pdf(self, tier):
        root = self.build_repo()
        pdf_dir = root / "sources/pdf"
        pdf_dir.mkdir(parents=True)
        (pdf_dir / "AB2018.pdf").write_bytes(b"%PDF-1.4 fixture\n")
        (pdf_dir / "SHA256SUMS").write_text("0000  AB2018.pdf\n", encoding="utf-8")
        (pdf_dir / "README.md").write_text("PDFs\n", encoding="utf-8")
        rewrite(root / SOURCES, lambda t: t.replace(
            "\tpublic-domain\t\t\t2\t", "\t%s\t\tsources/pdf/AB2018.pdf\t2\t" % tier).encode("utf-8"))
        return self.run_gauntlet(root)

    def test_shareable_pdf_passes_and_other_files_ignored(self):
        ctx = self._with_ab_pdf("public-domain")
        self.assertEqual(ctx.findings, [], dump(ctx))

    def test_pdf_with_restricted_source(self):
        ctx = self._with_ab_pdf("restricted")
        self.assertFinding(ctx, "G0", "error", SOURCES, "not shareable", line=2)

    def test_pdf_path_missing_on_disk(self):
        root = self.build_repo()
        rewrite(root / SOURCES, lambda t: t.replace(
            "\t\t\t2\t", "\t\tsources/pdf/AB2018.pdf\t2\t").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G0", "error", SOURCES, "does not exist")


class TestG1Format(GauntletCase):
    def test_non_nfc(self):
        root = self.build_repo()
        nfd = unicodedata.normalize("NFD", "tú")
        rewrite(root / WORDS_A, lambda t: t.replace("tú", nfd).encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G1", "error", WORDS_A, "NFC", line=2)

    def test_crlf(self):
        root = self.build_repo()
        rewrite(root / WORDS_A, lambda t: t.replace("\n", "\r\n").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        hits = self.assertFinding(ctx, "G1", "error", WORDS_A, "carriage return", line=1)
        self.assertEqual(len(hits), 1)
        self.assertNoFinding(ctx, "G2")  # rows still parse after the report

    def test_missing_final_newline(self):
        root = self.build_repo()
        rewrite(root / WORDS_A, lambda t: t.rstrip("\n").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G1", "error", WORDS_A, "final newline", line=3)

    def test_not_utf8(self):
        root = self.build_repo()
        rewrite(root / WORDS_A, lambda t: t.encode("latin-1"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G1", "error", WORDS_A, "UTF-8", line=2)

    def test_blank_line(self):
        ctx = self.check("blank_line")
        self.assertFinding(ctx, "G1", "error", WORDS_A, "blank line", line=3)

    def test_wrong_header_skips_rows(self):
        ctx = self.check("wrong_header")
        self.assertFinding(ctx, "G1", "error", NUMBERS, "header", line=1)
        self.assertNoFinding(ctx, "G2", path=NUMBERS)

    def test_wrong_column_count(self):
        ctx = self.check("wrong_column_count")
        self.assertFinding(ctx, "G1", "error", NUMBERS, "has 11 cells, header has 13", line=2)

    def test_trailing_space(self):
        ctx = self.check("trailing_space")
        self.assertFinding(ctx, "G1", "error", WORDS_A, "whitespace", line=3)

    def test_double_space(self):
        ctx = self.check("double_space")
        self.assertFinding(ctx, "G1", "error", WORDS_A, "double space", line=3)

    def test_curly_apostrophe(self):
        ctx = self.check("curly_apostrophe")
        self.assertFinding(ctx, "G1", "error", WORDS_A, "curly apostrophe", line=3)

    def test_quoted_cell_is_warning(self):
        ctx = self.check("quoted_cell")
        self.assertFinding(ctx, "G1", "warning", WORDS_A, "double quotes", line=3)
        self.assertTrue(validate.is_ok(ctx), dump(ctx))

    def test_unsorted_rows(self):
        ctx = self.check("unsorted_rows")
        hits = self.assertFinding(ctx, "G1", "error", WORDS_A, "not sorted", line=3)
        self.assertEqual(len(hits), 1)


class TestG2Schema(GauntletCase):
    def test_bad_enum(self):
        ctx = self.check("bad_enum")
        self.assertFinding(ctx, "G2", "error", WORDS_A, "'approved' is not one of", line=3)

    def test_bad_id_pattern(self):
        ctx = self.check("bad_id_pattern")
        self.assertFinding(ctx, "G2", "error", WORDS_A, "'pap-12' does not match", line=3)

    def test_reviewed_without_reviewer(self):
        ctx = self.check("reviewed_without_reviewer")
        self.assertFinding(ctx, "G2", "error", WORDS_A, "reviewed_by is empty", line=3)

    def test_required_and_unique_within_file(self):
        root = self.build_repo()
        rewrite(root / WORDS_A, lambda t: t.replace("pap-000002\tawa", "pap-000001\t").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", WORDS_A, "lemma is required", line=3)
        self.assertFinding(ctx, "G2", "error", WORDS_A, "duplicate value 'pap-000001'", line=3)
        self.assertNoFinding(ctx, "G4", contains="pap-000001")  # same file: G2 only


class TestG3Orthography(GauntletCase):
    def test_accented_word(self):
        ctx = self.check("accented_word")
        self.assertFinding(ctx, "G3", "error", "lexicon/words/E/words.tsv", "educación", line=2)

    def test_allowlisted_loan_passes(self):
        ctx = self.check("allowlisted_loan")
        self.assertEqual(ctx.findings, [], dump(ctx))

    def test_curacao_marker_warns_except_ab(self):
        ctx = self.check("curacao_marker")
        hits = self.assertFinding(ctx, "G3", "warning", WORDS_A, "atenshon", line=3)
        self.assertIn("-shon", hits[0].message)
        self.assertNoFinding(ctx, "G3", contains="cashon")  # AB2018-sourced
        self.assertTrue(validate.is_ok(ctx), dump(ctx))

    def test_curacao_k_and_function_words(self):
        root = self.build_repo("curacao_marker")
        rewrite(root / WORDS_A, lambda t: t.replace("atenshon", "akuza").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G3", "warning", WORDS_A, "k before a/o/u")

    def test_wrong_letter_folder(self):
        ctx = self.check("wrong_letter_folder")
        self.assertFinding(ctx, "G3", "error", WORDS_A, "belongs in letter folder B", line=4)

    def test_enye_goes_in_n(self):
        root = self.build_repo()
        folder = root / "lexicon/words/N"
        folder.mkdir()
        header = (root / WORDS_A).read_text(encoding="utf-8").split("\n")[0]
        (folder / "words.tsv").write_text(
            header + "\npap-000020\tñapa\t\ts.\t\textra\t\t\tdraft\t\tAB2018\t30\t\n",
            encoding="utf-8")
        ctx = self.run_gauntlet(root)
        self.assertEqual(ctx.findings, [], dump(ctx))


class TestG4Integrity(GauntletCase):
    def test_duplicate_id_across_files(self):
        ctx = self.check("duplicate_id_across_files")
        self.assertFinding(ctx, "G4", "error", "lexicon/words/C/words.tsv",
                           "id 'pap-000001' is already used at %s:2" % WORDS_A)

    def test_duplicate_lemma_pos_tag_across_files(self):
        ctx = self.check("duplicate_lemma_across_files")
        self.assertFinding(ctx, "G4", "error", "lexicon/words/W/words.tsv",
                           "lemma+pos+tag awa|s.| duplicates %s:3" % WORDS_A)

    def test_lexicon_refs_warn(self):
        ctx = self.check("lexicon_ref")
        path = "lexicon/variants/curacao-aruba.tsv"
        self.assertFinding(ctx, "G4", "warning", path, "'come'", line=3)
        self.assertNoFinding(ctx, "G4", contains="'cas'")
        self.assertNoFinding(ctx, severity="error")

    def test_lexicon_refs_skipped_without_words(self):
        root = self.build_repo("lexicon_ref")
        shutil.rmtree(str(root / "lexicon/words"))
        ctx = self.run_gauntlet(root)
        self.assertNoFinding(ctx, "G4")


class TestG5KnownFacts(GauntletCase):
    def test_number_fact_violation(self):
        ctx = self.check("known_fact_23")
        hits = self.assertFinding(ctx, "G5", "error", NUMBERS, "fact-0005", line=3)
        self.assertIn("typo", hits[0].message)  # the ruling's notes are quoted

    def test_hopi_fact_violation(self):
        ctx = self.check("known_fact_hopi")
        path = "lexicon/words/H/words.tsv"
        self.assertFinding(ctx, "G5", "error", path, "fact-0001", line=2)  # contains 'a lot'
        self.assertFinding(ctx, "G5", "error", path, "fact-0002", line=2)  # not-contains 'Hopi'

    def test_fact_pending_when_row_absent(self):
        ctx = self.check(None)
        self.assertNoFinding(ctx, "G5")
        self.assertGreater(ctx.facts_pending, 0)
        self.assertEqual(ctx.facts_checked + ctx.facts_pending, ctx.facts_total)

    def test_g5_checks_is_extensible(self):
        def extra(ctx):
            ctx.add("G5", "error", "rules/x.tsv", 1, "rule test failed")
        validate.G5_CHECKS.append(extra)
        try:
            ctx = self.check(None)
        finally:
            validate.G5_CHECKS.remove(extra)
        self.assertFinding(ctx, "G5", "error", "rules/x.tsv", "rule test failed")


class TestRobustness(GauntletCase):
    def test_garbage_does_not_crash(self):
        root = self.build_repo()
        (root / WORDS_A).write_bytes(b"\xff\xfe\x00garbage")
        (root / NUMBERS).write_bytes(b"")
        (root / "_meta/schema/numbers.schema.json").write_text("{not json", encoding="utf-8")
        ctx = self.run_gauntlet(root)
        self.assertFalse(validate.is_ok(ctx))
        self.assertNoFinding(ctx, contains="internal error")

    def test_real_repo_does_not_crash(self):
        proc = subprocess.run([sys.executable, str(VALIDATOR), "--root", str(REPO)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout.decode("utf-8")
        print("\n--- validator on real repo ---\n" + out)
        self.assertIn(proc.returncode, (0, 1), proc.stderr.decode("utf-8"))
        self.assertIn("RESULT:", out)
        self.assertNotIn("internal error", out)


if __name__ == "__main__":
    unittest.main()
