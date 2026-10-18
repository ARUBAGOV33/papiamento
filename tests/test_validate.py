"""Tests for tools/validate.py (the gauntlet).

Fixture layout: tests/fixtures/valid/ is a complete mini repo that passes.
Every other tests/fixtures/<case>/ holds only the files that differ from
valid/; build_repo() copies valid/, overlays the case, and adds a copy of the
real _meta/ so fixtures are always checked against the live schemas. The live
known facts are the exception: they name rows the mini repo does not have, so
valid/_meta/known-facts.tsv holds a few facts that match its rows.
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
        root = Path(tempfile.mkdtemp(dir=self._tmp.name)) / "repo"
        shutil.copytree(str(FIXTURES / "valid"), str(root))
        shutil.copytree(str(REPO / "_meta"), str(root / "_meta"), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("known-facts.tsv"))
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
        # A, C, H, numbers, calendar, barbarismos, variants, loanwords, errata,
        # sources, known-facts, audits, milestones, contributors, and the
        # parallel prompts and pairs in corpus/ and eval/: every registry
        # table has a file.
        self.assertEqual(len(ctx.files), 18)
        self.assertEqual(ctx.facts_checked, ctx.facts_total)  # e.g. fact-0009: 7 -> shete
        self.assertEqual(ctx.facts_pending_ids, [])

    def test_cli_exit_zero_and_json_shape(self):
        root = self.build_repo()
        proc = subprocess.run([sys.executable, str(VALIDATOR), "--root", str(root), "--json"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stdout.decode() + proc.stderr.decode())
        report = json.loads(proc.stdout.decode("utf-8"))
        self.assertTrue(report["ok"])
        self.assertEqual(sorted(report["gates"]), validate.GATES)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["files_checked"], 18)
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

    def test_row_without_source_is_untraced(self):
        root = self.build_repo()
        rewrite(root / WORDS_A, lambda t: t.replace("\tdraft\t\tAB2018\t12\t", "\tdraft\t\t\t12\t").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G0", "warning", WORDS_A, "untraced: no source for page 12", line=3)
        self.assertTrue(validate.is_ok(ctx), dump(ctx))  # draft rows may wait for a source

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

    def test_pdf_outside_pdf_dir(self):
        root = self.build_repo()
        for rel in ("sources/cards/AB2018.pdf", "corpus/raw/scan.PDF"):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(b"%PDF-1.4 fixture\n")
        # Local tool folders (here a nested worktree) are not part of the repo.
        nested = root / ".claude/worktrees/x/sources/pdf/NOPE.pdf"
        nested.parent.mkdir(parents=True)
        nested.write_bytes(b"%PDF-1.4 fixture\n")
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G0", "error", "sources/cards/AB2018.pdf", "PDF outside sources/pdf/")
        self.assertFinding(ctx, "G0", "error", "corpus/raw/scan.PDF", "PDF outside sources/pdf/")
        self.assertNoFinding(ctx, contains="NOPE")

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
    def test_glob_matching_no_file_is_an_error(self):
        root = self.build_repo()
        rewrite(root / "_meta/schema/registry.json",
                lambda t: t.replace("lexicon/loanwords/*.tsv", "lexicon/loanword/*.tsv").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G1", "error", validate.REGISTRY_PATH,
                           "table loanwords: glob 'lexicon/loanword/*.tsv' matches no file")

    def test_optional_table_may_have_no_file(self):
        root = self.build_repo()
        (root / "lexicon/loanwords/loanwords.tsv").unlink()
        registry = json.loads((root / validate.REGISTRY_PATH).read_text(encoding="utf-8"))
        for entry in registry["tables"]:
            if entry["name"] == "loanwords":
                entry["optional"] = True
            if entry["name"] == "variants":
                entry["optional"] = "yes"
        (root / validate.REGISTRY_PATH).write_text(json.dumps(registry), encoding="utf-8")
        ctx = self.run_gauntlet(root)
        self.assertNoFinding(ctx, "G1")
        hits = self.assertFinding(ctx, "G2", "error", validate.REGISTRY_PATH, "optional must be true or false")
        self.assertEqual(len(hits), 1)

    def test_missing_known_facts_and_rules_are_errors(self):
        root = self.build_repo()
        (root / "_meta/known-facts.tsv").unlink()
        (root / validate.RULES_PATH).unlink()
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G1", "error", validate.REGISTRY_PATH, "table known-facts")
        self.assertFinding(ctx, "G1", "error", validate.RULES_PATH, "file not found")

    def test_hidden_characters_in_cells(self):
        root = self.build_repo()
        rewrite(root / WORDS_A, lambda t: t.replace("\twater\twater\tagua\t",
                                                    "\twater\u2028second line\twa\u00a0ter\tag\u200bua\u0007\t").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G1", "error", WORDS_A, "en: hidden or line-breaking character(s) U+2028 LINE SEPARATOR", line=3)
        self.assertFinding(ctx, "G1", "error", WORDS_A, "nl: hidden or line-breaking character(s) U+00A0 NO-BREAK SPACE", line=3)
        self.assertFinding(ctx, "G1", "error", WORDS_A, "es: hidden or line-breaking character(s) U+0007, U+200B ZERO WIDTH SPACE", line=3)

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

    def test_machine_is_not_a_reviewer(self):
        root = self.build_repo()
        rewrite(root / WORDS_A, lambda t: t.replace("reviewed\tvictorgomesrt-rgb", "reviewed\tmachine").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", WORDS_A, "reviewed_by must name people, not machine", line=2)

    def test_required_and_unique_within_file(self):
        root = self.build_repo()
        rewrite(root / WORDS_A, lambda t: t.replace("pap-000002\tawa", "pap-000001\t").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", WORDS_A, "lemma is required", line=3)
        self.assertFinding(ctx, "G2", "error", WORDS_A, "duplicate value 'pap-000001'", line=3)
        self.assertNoFinding(ctx, "G4", contains="pap-000001")  # same file: G2 only

    def test_audit_errors_at_most_sample_size(self):
        ctx = self.check("audit_errors_exceed_sample")
        self.assertFinding(ctx, "G2", "error", "_meta/audits.tsv",
                           "errors (7) is greater than sample_size (5)", line=3)
        self.assertEqual(len(self.findings(ctx, path="_meta/audits.tsv")), 1, dump(ctx))

    def test_at_most_must_name_two_fields(self):
        root = self.build_repo()
        rel = "_meta/schema/audits.schema.json"
        schema = json.loads((root / rel).read_text(encoding="utf-8"))
        schema["x-papiamento"]["at_most"] = [["errors", "no_such_field"]]
        (root / rel).write_text(json.dumps(schema), encoding="utf-8")
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", rel, "at_most")
        self.assertNoFinding(ctx, contains="internal error")


    def test_unknown_contributor_handle(self):
        root = self.build_repo()
        rewrite(root / WORDS_A, lambda t: t.replace("\tmachine\t", "\tnew-person\t", 1).encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G4", "error", WORDS_A, "translated_by: 'new-person' is not a handle in _meta/contributors.tsv")

    def test_contributor_matches_github_name_in_any_case(self):
        root = self.build_repo()
        rewrite(root / WORDS_A, lambda t: t.replace("reviewed\tvictorgomesrt-rgb", "reviewed\tVictorgomesrt-RGB").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertNoFinding(ctx, "G4", contains="contributors.tsv")

    def write_parallel(self, root, folder, prompt_ids, pair_prompt_ids):
        prompts_header = (root / folder / "prompts.tsv").read_text(encoding="utf-8")
        pairs_header = (root / folder / "pairs.tsv").read_text(encoding="utf-8")
        prompts = "".join("%s\ten\tPrompt %s.\thome\twritten\t\tmachine\tprompts-1\tCC0-1.0\tdraft\t\t\n"
                          % (pid, n) for n, pid in enumerate(prompt_ids))
        pairs = "".join("par-%06d\t%s\tmi kier bay\tvictorgomesrt-rgb\t\t\t\tcontrib-2026-11-01\tCC0-1.0\tdraft\t\t\n"
                        % (n + 1, pid) for n, pid in enumerate(pair_prompt_ids))
        (root / folder / "prompts.tsv").write_text(prompts_header + prompts, encoding="utf-8")
        (root / folder / "pairs.tsv").write_text(pairs_header + pairs, encoding="utf-8")

    def test_parallel_pairs_pass(self):
        root = self.build_repo()
        self.write_parallel(root, "corpus/parallel", ["prm-000001"], ["prm-000001"])
        ctx = self.run_gauntlet(root)
        self.assertEqual([f for f in ctx.findings if "parallel" in f.path], [], dump(ctx))

    def test_pair_must_use_a_prompt_in_its_own_folder(self):
        # A corpus/ pair on a held-out eval/ prompt would leak the test set.
        root = self.build_repo()
        self.write_parallel(root, "eval/parallel", ["prm-000002"], [])
        self.write_parallel(root, "corpus/parallel", ["prm-000001"], ["prm-000002"])
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G4", "error", "corpus/parallel/pairs.tsv",
                           "prompt_id: 'prm-000002' is not an id in corpus/parallel/prompts.tsv", line=2)

    def test_pairs_never_translated_by_machine(self):
        root = self.build_repo()
        self.write_parallel(root, "corpus/parallel", ["prm-000001"], ["prm-000001"])
        rewrite(root / "corpus/parallel/pairs.tsv", lambda t: t.replace("victorgomesrt-rgb", "machine").encode("utf-8"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", "corpus/parallel/pairs.tsv", "translated_by")

    def test_folder_refs_must_name_a_tsv_file(self):
        root = self.build_repo()
        rel = "_meta/schema/parallel-pairs.schema.json"
        schema = json.loads((root / rel).read_text(encoding="utf-8"))
        schema["x-papiamento"]["folder_refs"] = {"prompt_id": "../prompts.tsv"}
        (root / rel).write_text(json.dumps(schema), encoding="utf-8")
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", rel, "folder_refs")

    def test_schema_typos_are_reported(self):
        root = self.build_repo()
        rel = "_meta/schema/lexicon-words.schema.json"
        schema = json.loads((root / rel).read_text(encoding="utf-8"))
        schema["x-papiamento"]["aruban_text"] = ["lema", "alt "]
        schema["x-papiamento"]["letter_folder"] = "lema"
        schema["x-papiamento"]["sort_bye"] = ["lemma"]
        schema["fields"][1]["constraints"]["maxLength"] = 40
        schema["fields"][2]["constraint"] = {"required": True}
        schema["x-papiamiento"] = {}
        (root / rel).write_text(json.dumps(schema), encoding="utf-8")
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", rel, "x-papiamento aruban_text must be a list of field names")
        self.assertFinding(ctx, "G2", "error", rel, "x-papiamento letter_folder must be a field name")
        self.assertFinding(ctx, "G2", "error", rel, "unknown x-papiamento key 'sort_bye'")
        self.assertFinding(ctx, "G2", "error", rel, "field lemma: constraint(s) maxLength are not checked")
        self.assertFinding(ctx, "G2", "error", rel, "field alt: unknown key(s) constraint")
        self.assertFinding(ctx, "G2", "error", rel, "unknown schema key(s) x-papiamiento")
        self.assertNoFinding(ctx, contains="internal error")


class TestTranslatedBy(GauntletCase):
    def test_translation_needs_translated_by(self):
        root = self.build_repo()
        path = root / WORDS_A
        lines = path.read_text(encoding="utf-8").split("\n")
        header = lines[0].split("\t")
        col = header.index("translated_by")
        for i, line in enumerate(lines[1:], 1):
            cells = line.split("\t")
            if len(cells) == len(header) and cells[header.index("en")]:
                cells[col] = ""
                lines[i] = "\t".join(cells)
                line_no = i + 1
                break
        path.write_text("\n".join(lines), encoding="utf-8")
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", WORDS_A,
                           "translated_by is required when en", line=line_no)


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
            header + "\npap-000020\tñapa\t\ts.\t\textra\t\t\tmachine\tdraft\t\tAB2018\t30\t\n",
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

    def test_rule_refs_must_name_a_grammar_file(self):
        root = self.build_repo()
        grammar = root / "grammar/orthography/rule-ort-test-001.md"
        grammar.parent.mkdir(parents=True)
        grammar.write_text(TestGrammarFiles.GOOD, encoding="utf-8")
        path = root / "lexicon/barbarismos/barbarismos.tsv"
        path.write_text(path.read_text(encoding="utf-8") + "".join(
            "bar-000%d\t%s\t%s\tes\tSpanish word.\t%s\tdraft\t\tAB2018\t12\t\n" % row for row in [
                (1, "agua", "awa", "RULE_LEX_AGUA_001"),    # row-level id: no grammar file needed
                (2, "casa", "cas", "RULE_ORT_TEST_001"),    # a grammar file has this id
                (3, "usted", "bo", "RULE_PRN_USTED_001"),   # no grammar file
            ]), encoding="utf-8")
        ctx = self.run_gauntlet(root)
        rel = "lexicon/barbarismos/barbarismos.tsv"
        hits = self.assertFinding(ctx, "G4", "warning", rel, "'RULE_PRN_USTED_001' is not the id of a grammar file", line=4)
        self.assertEqual(len(self.findings(ctx, "G4", path=rel)), 1, dump(ctx))
        self.assertTrue(validate.is_ok(ctx), dump(ctx))

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

    def test_fact_matching_no_row_warns(self):
        # A where that matches nothing is a typo, or a fact recorded before its row.
        root = self.build_repo()
        (root / "lexicon/words/H/words.tsv").unlink()
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G5", "warning", "_meta/known-facts.tsv",
                           "fact-0001: no row of words matches lemma=hopi", line=2)
        self.assertTrue(validate.is_ok(ctx), dump(ctx))
        self.assertEqual(ctx.facts_pending_ids, ["fact-0001", "fact-0002"])
        self.assertEqual(ctx.facts_checked + ctx.facts_pending, ctx.facts_total)
        self.assertIn("2 pending (fact-0001, fact-0002)", validate.report_text(ctx))

    def test_fact_pending_when_cell_empty(self):
        # An empty translation means "not known yet": the hopi fact waits.
        ctx = self.check("known_fact_empty")
        self.assertNoFinding(ctx, "G5")
        self.assertEqual(ctx.facts_pending_ids, ["fact-0001", "fact-0002"])
        self.assertEqual(ctx.facts_checked + ctx.facts_pending, ctx.facts_total)

    def test_id_fact_cannot_be_switched_off(self):
        # fact-0901 rules on row pap-000003 (like an errata correction).
        for change, state in (("\thouse\t", "has an empty en"), ("\tdraft\t", "is deprecated")):
            with self.subTest(state=state):
                root = self.build_repo()
                path = root / "lexicon/words/C/words.tsv"
                rewrite(path, lambda t: t.replace(
                    change, "\t\t" if change == "\thouse\t" else "\tdeprecated\t", 1).encode("utf-8"))
                ctx = self.run_gauntlet(root)
                self.assertFinding(ctx, "G5", "error", "_meta/known-facts.tsv",
                                   "fact-0901: the row id=pap-000003 %s" % state)

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



class TestGrammarFiles(GauntletCase):
    GOOD = (
        "---\nid: RULE_ORT_TEST_001\ntitle: Test rule\nstatus: draft\nsource: AB2018\n"
        "page: \"38\"\nseverity: error\nreviewed_by: \"\"\n---\n\n## Rule\n\nA rule.\n")

    def write(self, root, rel, text):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return rel

    def test_valid_grammar_file_passes(self):
        root = self.build_repo()
        self.write(root, "grammar/orthography/rule-ort-test-001.md", self.GOOD)
        ctx = self.run_gauntlet(root)
        self.assertEqual(ctx.findings, [], dump(ctx))
        self.assertEqual(ctx.grammar_checked, 1)

    def test_grammar_missing_field_and_unknown_source(self):
        root = self.build_repo()
        rel = self.write(root, "grammar/orthography/rule-ort-test-001.md",
                         self.GOOD.replace("severity: error\n", "").replace("AB2018", "XYZ2020"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", rel, "severity is required")
        self.assertFinding(ctx, "G0", "error", rel, "'XYZ2020' is not in sources")

    def test_grammar_file_name_must_match_id(self):
        root = self.build_repo()
        rel = self.write(root, "grammar/orthography/wrong-name.md", self.GOOD)
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", rel, "file name must be rule-ort-test-001.md")

    def test_grammar_bad_topic_and_missing_rule_section(self):
        root = self.build_repo()
        bad = self.write(root, "grammar/misc/rule-ort-test-001.md", self.GOOD)
        nosec = self.write(root, "grammar/syntax/rule-ort-test-002.md",
                           self.GOOD.replace("RULE_ORT_TEST_001", "RULE_ORT_TEST_002").replace("## Rule", "## Something"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", bad, "grammar files go in grammar/<topic>/")
        self.assertFinding(ctx, "G2", "error", nosec, "missing a '## Rule' section")


    def test_rule_heading_must_be_exact_and_not_empty(self):
        root = self.build_repo()
        plural = self.write(root, "grammar/orthography/rule-ort-test-001.md", self.GOOD.replace("## Rule\n", "## Rules\n"))
        empty = self.write(root, "grammar/orthography/rule-ort-test-002.md",
                           self.GOOD.replace("RULE_ORT_TEST_001", "RULE_ORT_TEST_002").replace("A rule.\n", "## Source\n\nAB 2018.\n"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", plural, "missing a '## Rule' section")
        self.assertFinding(ctx, "G2", "error", empty, "the '## Rule' section is empty")

    def test_grammar_reviewer_must_be_a_person(self):
        root = self.build_repo()
        rel = self.write(root, "grammar/orthography/rule-ort-test-001.md",
                         self.GOOD.replace("status: draft", "status: reviewed").replace('reviewed_by: ""', "reviewed_by: machine"))
        ctx = self.run_gauntlet(root)
        self.assertFinding(ctx, "G2", "error", rel, "reviewed_by must name people, not machine")


class TestMachineRules(GauntletCase):
    GRAMMAR = (
        "---\nid: RULE_ORT_TEST_001\ntitle: Days in lowercase\nstatus: draft\nsource: AB2018\n"
        "page: \"32\"\nseverity: error\nreviewed_by: \"\"\n---\n\n## Rule\n\nDays are lowercase.\n\n"
        "## Correct\n\n- dialuna\n- Mi ta bay dialuna.\n\n## Incorrect\n\n- Dialuna → dialuna\n")
    B = "(?<![A-Za-zÀ-ÿñÑ'])"
    E = "(?![A-Za-zÀ-ÿñÑ'])"

    def repo(self, rule, grammar=None):
        root = self.build_repo()
        g = root / "grammar/orthography/rule-ort-test-001.md"
        g.parent.mkdir(parents=True, exist_ok=True)
        g.write_text(grammar or self.GRAMMAR, encoding="utf-8")
        r = root / "rules/rules.jsonl"
        r.parent.mkdir(parents=True, exist_ok=True)
        r.write_text(json.dumps(rule, ensure_ascii=False) + "\n", encoding="utf-8")
        return root

    def rule(self, **kw):
        base = {"rule_id": "RULE_ORT_TEST_001", "pattern": self.B + "Dialuna" + self.E,
                "message": "Days are written in lowercase.", "replacement": "dialuna",
                "tests": {"match": ["Dialuna"], "no_match": ["dialuna", "Mi ta bay dialuna."],
                          "fix": [{"text": "Dialuna", "expect": "dialuna"}]}}
        base.update(kw)
        return base

    def test_valid_rule_passes(self):
        ctx = self.run_gauntlet(self.repo(self.rule()))
        self.assertEqual([f for f in ctx.findings if f.gate in ("G0", "G2", "G5")], [], dump(ctx))
        self.assertEqual(ctx.rules_checked, 1)

    def test_test_must_be_printed_in_grammar_file(self):
        r = self.rule(tests={"match": ["Dialuna", "DIALUNA"], "no_match": []})
        ctx = self.run_gauntlet(self.repo(r))
        self.assertFinding(ctx, "G0", "error", "rules/rules.jsonl", "'DIALUNA' is not printed")

    def test_rule_must_catch_and_not_overflag(self):
        r = self.rule(pattern=self.B + "dialuna" + self.E, replacement=None,
                      tests={"match": ["Dialuna"], "no_match": ["dialuna"]})
        ctx = self.run_gauntlet(self.repo(r))
        self.assertFinding(ctx, "G5", "error", "rules/rules.jsonl", "does not catch 'Dialuna'")
        self.assertFinding(ctx, "G5", "error", "rules/rules.jsonl", "wrongly flags the correct example 'dialuna'")

    def test_non_portable_pattern_and_info_rule(self):
        r = self.rule(pattern=r"\bDialuna\b")
        ctx = self.run_gauntlet(self.repo(r, self.GRAMMAR.replace("severity: error", "severity: info")))
        self.assertFinding(ctx, "G2", "error", "rules/rules.jsonl", "behaves differently in JavaScript")
        self.assertFinding(ctx, "G2", "error", "rules/rules.jsonl", "is an info rule")

    def test_bad_replacement_is_reported_not_a_crash(self):
        r = self.rule(replacement="$10", tests={"match": ["Dialuna"], "no_match": ["dialuna"],
                                                 "fix": [{"text": "Dialuna", "expect": "dialuna"}]})
        ctx = self.run_gauntlet(self.repo(r))
        self.assertFinding(ctx, "G2", "error", "rules/rules.jsonl", "cannot be applied")
        self.assertNoFinding(ctx, contains="internal error")
        self.assertEqual(ctx.rules_checked, 1)

    def test_rule_must_not_flag_its_own_correct_examples(self):
        # Before, only examples listed as no_match tests were checked.
        r = self.rule(flags="i", tests={"match": ["Dialuna"], "no_match": []})
        ctx = self.run_gauntlet(self.repo(r))
        rel = "grammar/orthography/rule-ort-test-001.md"
        self.assertFinding(ctx, "G5", "error", "rules/rules.jsonl", "flags the correct example 'dialuna' in %s" % rel)
        self.assertFinding(ctx, "G5", "error", "rules/rules.jsonl", "flags the correct example 'Mi ta bay dialuna.'")

    def test_correct_hits_in_other_files_are_errors_unless_allowed(self):
        other = ("---\nid: RULE_ORT_TEST_002\ntitle: Other\nstatus: draft\nsource: AB2018\npage: \"33\"\n"
                 "severity: error\n---\n\n## Rule\n\nA rule.\n\n## Correct\n\n- Dialuna ta bon.\n")
        for allow, expect_error in (([], True), (["Dialuna ta bon."], False)):
            with self.subTest(allow=allow):
                root = self.repo(self.rule(allow_correct_hits=allow))
                (root / "grammar/orthography/rule-ort-test-002.md").write_text(other, encoding="utf-8")
                ctx = self.run_gauntlet(root)
                hits = self.findings(ctx, "G5", "error", contains="'Dialuna ta bon.' in grammar/orthography/rule-ort-test-002.md")
                self.assertEqual(bool(hits), expect_error, dump(ctx))
                self.assertNoFinding(ctx, "G2")

    def test_allow_correct_hits_must_be_used(self):
        ctx = self.run_gauntlet(self.repo(self.rule(allow_correct_hits=["dialuna", "nada"])))
        self.assertFinding(ctx, "G2", "error", "rules/rules.jsonl", "allow_correct_hits 'dialuna' is not a correct example this rule flags")
        self.assertFinding(ctx, "G2", "error", "rules/rules.jsonl", "allow_correct_hits 'nada'")
        ctx = self.run_gauntlet(self.repo(self.rule(allow_correct_hits="dialuna")))
        self.assertFinding(ctx, "G2", "error", "rules/rules.jsonl", "allow_correct_hits must be a list")

    def test_derived_test_needs_printed_basis(self):
        r = self.rule(tests={"match": [], "no_match": ["dialuna"]},
                      derived=[{"text": "Dialuna", "from": "diamars", "change": "capitalised", "expect": "match"}])
        ctx = self.run_gauntlet(self.repo(r))
        self.assertFinding(ctx, "G0", "error", "rules/rules.jsonl", "based on 'diamars'")


if __name__ == "__main__":
    unittest.main()
