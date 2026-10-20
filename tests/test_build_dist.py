"""Tests for tools/build_dist.py (the release build).

These build the real repository into a temporary folder and check the result
against the TSV files, so a release can never ship a table that lost rows,
a dataset card with an unfilled placeholder, or a manifest that does not match
its files.

Run from the repo root: python3 -m unittest discover -s tests -v
"""

import glob
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("build_dist", str(REPO / "tools" / "build_dist.py"))
build_dist = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_dist)  # type: ignore[union-attr]


def tsv_rows(pattern):
    n = 0
    for path in glob.glob(str(REPO / pattern)):
        with open(path, encoding="utf-8") as f:
            n += sum(1 for line in f.read().split("\n")[1:] if line)
    return n


class BuildDistTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._tmp.name) / "dist"
        cls.counts, cls.stats = build_dist.build(str(cls.out), "9.8.7", "example/papiamento")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def jsonl(self, name):
        with open(self.out / name, encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    def test_out_refuses_a_folder_it_did_not_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "notes.txt"
            keep.write_text("not a release", encoding="utf-8")
            result = subprocess.run([sys.executable, str(REPO / "tools" / "build_dist.py"), "--out", tmp],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to delete", result.stderr)
            self.assertTrue(keep.exists())

    def test_every_table_keeps_all_rows(self):
        with open(REPO / "_meta" / "schema" / "registry.json", encoding="utf-8") as f:
            globs = dict((t["name"], t["glob"]) for t in json.load(f)["tables"])
        for name, table in build_dist.TABLES:
            with self.subTest(table=name):
                rows = self.jsonl(name + ".jsonl")
                self.assertEqual(len(rows), tsv_rows(globs[table]))
                self.assertEqual(len(rows), self.counts[name])

    def test_grammar_and_rules_complete(self):
        self.assertEqual(len(self.jsonl("grammar.jsonl")), len(glob.glob(str(REPO / "grammar" / "*" / "rule-*.md"))))
        with open(REPO / "rules" / "rules.jsonl", encoding="utf-8") as f:
            n_rules = sum(1 for line in f if line.strip())
        rules = self.jsonl("rules.jsonl")
        self.assertEqual(len(rules), n_rules)
        for r in rules:
            self.assertTrue(r["severity"], r["rule_id"])
            self.assertTrue(r["source"], r["rule_id"])
        with open(self.out / "rule_pack.json", encoding="utf-8") as f:
            pack = json.load(f)
        self.assertEqual(pack["version"], "9.8.7")
        self.assertEqual(len(pack["rules"]), n_rules)
        self.assertEqual(len(pack["barbarismos"]), self.counts["barbarismos"])
        self.assertEqual(len(pack["variants"]), self.counts["variants"])

    def test_multi_value_cells_become_lists(self):
        words = self.jsonl("words.jsonl")
        for field in ("alt", "en", "nl", "es", "translated_by", "reviewed_by"):
            self.assertTrue(all(isinstance(r[field], list) for r in words), field)
        self.assertTrue(all(isinstance(r["notes"], str) for r in words))
        hopi = [r for r in words if r["lemma"] == "hopi"]
        self.assertTrue(hopi and "a lot" in hopi[0]["en"])
        self.assertTrue(all(isinstance(r["features"], list) for r in self.jsonl("closed_classes.jsonl")))
        self.assertTrue(all(isinstance(r["related"], list) for r in self.jsonl("names.jsonl")))
        # prose with "; " in meta tables stays a string
        self.assertTrue(all(isinstance(r["method"], str) for r in self.jsonl("audits.jsonl")))
        self.assertTrue(all(isinstance(r["left"], str) for r in self.jsonl("milestones.jsonl")))

    def test_dataset_card(self):
        card = (self.out / "README.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\{\{[A-Z_]+\}\}", card))
        self.assertIn("Version 9.8.7.", card)
        self.assertIn('load_dataset("example/papiamento"', card)
        front = card.split("---\n")[1]
        # data_files is either a file name or a list of splits with paths
        configs = re.findall(r"config_name: (\S+)\n\s+data_files:(?: (\S+)|\n\s+- split: \S+\n\s+path: (\S+))", front)
        self.assertEqual(sorted(c for c, _, _ in configs), sorted(self.counts))
        for name, data_file, split_path in configs:
            self.assertTrue((self.out / (data_file or split_path)).is_file(), name)
        # held-out prompts are a test split, never train
        self.assertRegex(front, r"config_name: eval_prompts\n\s+data_files:\n\s+- split: test\n\s+path: eval_prompts.jsonl")
        self.assertIn("CC0", card)

    def test_manifest_matches_files(self):
        with open(self.out / "manifest.json", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest["version"], "9.8.7")
        listed = set(manifest["files"])
        self.assertEqual(listed, set(os.listdir(self.out)) - {"manifest.json"})
        for name, info in manifest["files"].items():
            data = (self.out / name).read_bytes()
            self.assertEqual(info["sha256"], hashlib.sha256(data).hexdigest(), name)
            self.assertEqual(info["bytes"], len(data), name)

    def test_build_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            build_dist.build(tmp, "9.8.7", "example/papiamento")
            for name in os.listdir(self.out):
                self.assertEqual((self.out / name).read_bytes(), (Path(tmp) / name).read_bytes(), name)


class EmptyTableTest(unittest.TestCase):
    def test_empty_tables(self):
        data = {"words": [{"id": "pap-000001"}], "names": [], "loanwords": [], "rules": []}
        self.assertEqual(build_dist.empty_tables(data, {"names"}), ["loanwords", "rules"])

    def test_build_refuses_a_table_with_no_rows(self):
        # A glob typo used to ship loanwords.jsonl with 0 rows, exit 0.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            for name in ("_meta", "lexicon", "sources/sources.tsv", "sources/errata.tsv", "grammar", "rules", "CHANGELOG.md"):
                src, dst = REPO / name, root / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                (shutil.copytree if src.is_dir() else shutil.copy)(str(src), str(dst))
            registry = root / "_meta" / "schema" / "registry.json"
            registry.write_text(registry.read_text(encoding="utf-8").replace(
                "lexicon/loanwords/*.tsv", "lexicon/loanword/*.tsv"), encoding="utf-8")
            out = Path(tmp) / "dist"
            saved = build_dist.ROOT
            build_dist.ROOT = str(root)
            try:
                with self.assertRaises(SystemExit) as cm:
                    build_dist.build(str(out), "9.8.7")
            finally:
                build_dist.ROOT = saved
            self.assertIn("no rows for loanwords", str(cm.exception))
            self.assertFalse(out.exists())  # nothing half-written


class ReleaseMetadataTest(unittest.TestCase):
    def test_citation_version_has_changelog_section(self):
        version = build_dist.citation_version()
        if version is None:
            self.skipTest("CITATION.cff has no version yet")
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertTrue(build_dist.changelog_section(version), "CHANGELOG.md has no section for " + version)
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("[%s]: https://github.com/ARUBAGOV33/papiamento/releases/tag/v%s" % (version, version), changelog)

    def test_zenodo_metadata(self):
        with open(REPO / ".zenodo.json", encoding="utf-8") as f:
            zenodo = json.load(f)
        self.assertEqual(zenodo["upload_type"], "dataset")
        self.assertEqual(zenodo["license"], "cc-by-4.0")
        self.assertTrue(zenodo["creators"])


if __name__ == "__main__":
    unittest.main()
