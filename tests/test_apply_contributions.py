"""Tests for tools/apply_contributions.py on a mini repo (tests/fixtures/valid
plus the real _meta/) and a made-up snapshot of the tool's database. No
network. The only Papiamento here is copied from rule tests in the repo.

Run from the repo root: python3 -m unittest discover -s tests -v
"""

import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


sync = load("apply_contributions", REPO / "tools" / "apply_contributions.py")
validate = load("validate_for_sync_tests", REPO / "tools" / "validate.py")

PROMPT_HEADER = "id\tlang\ttext\ttopic\torigin\torigin_ref\tauthor\tbatch\tlicence\tstatus\treviewed_by\tnotes\n"
SENTENCE_1 = "mi kier bay"                                            # rules.jsonl, RULE_GRA_MODAL_TA_001
SENTENCE_2 = "Mañan nos docente mester asisti na un conferencia."     # same rule's tests


def profile(pid, handle, role="contributor", github=None, credit=True, name=""):
    return {"id": pid, "handle": handle, "credit_name": name, "credit": credit, "role": role, "github": github,
            "occupation": "teacher", "consent_version": "tool-2026-10", "created_at": "2026-10-20T12:00:00+00:00"}


def snapshot():
    return {
        "profiles": [
            profile("v", "victorgomesrt-rgb", "maintainer", "victorgomesrt-rgb", name="Victor"),
            profile("a", "teacher-a", name="Teacher A"),
            profile("b", "teacher-b", credit=False, name="Teacher B"),
            profile("c", "board-c", "board", None, name="Board C"),
        ],
        "decisions": [
            {"id": 1, "kind": "review", "word_ref": "pap-000002", "translation_id": None, "board_id": "v", "outcome": "reviewed",
             "value": {"en": {"value": "water", "from": "machine"}, "nl": {"value": "water;drinkwater", "from": ["a", "b"]},
                       "es": {"value": "agua", "from": "machine"}}, "exported_in": None},
            {"id": 2, "kind": "review", "word_ref": "pap-000001", "translation_id": None, "board_id": "v", "outcome": "reviewed",
             "value": {"en": {"value": "you", "from": "machine"}}, "exported_in": None},
            {"id": 3, "kind": "translate", "word_ref": "pap-000003", "translation_id": None, "board_id": "c", "outcome": "reviewed",
             "value": {"en": {"value": "house; home", "from": ["a"]}, "nl": {"value": "huis", "from": ["b"]},
                       "es": {"value": "casa", "from": "board"}}, "exported_in": None},
            {"id": 4, "kind": "review", "word_ref": "pap-000015", "translation_id": None, "board_id": "v", "outcome": "disputed",
             "value": None, "exported_in": None},
            {"id": 5, "kind": "sentence", "word_ref": None, "translation_id": 11, "board_id": "v", "outcome": "reviewed",
             "value": {"text": SENTENCE_1, "translation_id": 11, "from": "a"}, "exported_in": None},
            {"id": 6, "kind": "sentence", "word_ref": None, "translation_id": 12, "board_id": "v", "outcome": "reviewed",
             "value": {"text": SENTENCE_2, "translation_id": 13, "from": "a"}, "exported_in": None},
            {"id": 7, "kind": "sentence", "word_ref": None, "translation_id": 14, "board_id": "v", "outcome": "reviewed",
             "value": {"text": "educación", "translation_id": 14, "from": "b"}, "exported_in": None},
            {"id": 8, "kind": "translate", "word_ref": "pap-000004", "translation_id": None, "board_id": "v", "outcome": "reviewed",
             "value": {"en": {"value": "drawer", "from": ["a"]}}, "exported_in": None},
            {"id": 9, "kind": "review", "word_ref": "pap-000002", "translation_id": None, "board_id": "v", "outcome": "reviewed",
             "value": {}, "exported_in": "https://github.com/ARUBAGOV33/papiamento/pull/1"},
        ],
        "translations": [
            {"id": 11, "prompt_ref": "prm-000001", "person_id": "a", "text": SENTENCE_1, "flags_kept": [{"id": "RULE_ORT_014"}, "barbarismo:bar-0001"], "fix_of": None},
            {"id": 12, "prompt_ref": "prm-000004", "person_id": "b", "text": "Manan nos docente mester asisti", "flags_kept": [], "fix_of": None},
            {"id": 13, "prompt_ref": "prm-000004", "person_id": "a", "text": SENTENCE_2, "flags_kept": [], "fix_of": 12},
            {"id": 14, "prompt_ref": "prm-000001", "person_id": "b", "text": "educación", "flags_kept": [], "fix_of": None},
        ],
        "ratings": [
            {"id": 21, "translation_id": 11, "person_id": "b", "verdict": "good"},
            {"id": 22, "translation_id": 12, "person_id": "a", "verdict": "fix"},
        ],
    }


class TestApplyContributions(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        self.root = Path(tmp) / "repo"
        shutil.copytree(str(FIXTURES / "valid"), str(self.root))
        shutil.copytree(str(REPO / "_meta"), str(self.root / "_meta"), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("known-facts.tsv"))
        # prm-000001 stays in the corpus; prm-000004 is held out (its id hashes below 15).
        (self.root / "corpus/parallel/prompts.tsv").write_text(
            PROMPT_HEADER + "prm-000001\ten\tWhere is the bus stop?\tgetting around\twritten\t\tmachine\tprompts-1\tCC0-1.0\tdraft\t\t\n",
            encoding="utf-8")
        (self.root / "eval/parallel/prompts.tsv").write_text(
            PROMPT_HEADER + "prm-000004\ten\tWho left the lights on?\thome\twritten\t\tmachine\tprompts-1\tCC0-1.0\tdraft\t\t\n",
            encoding="utf-8")
        # pap-000003 has no translation yet, as a "translate" item would.
        words_c = self.root / "lexicon/words/C/words.tsv"
        words_c.write_text(words_c.read_text(encoding="utf-8").replace(
            "pap-000003\tcas\t\ts.\t\thouse\thuis\tcasa\tmachine\tdraft", "pap-000003\tcas\t\ts.\t\t\t\t\t\tdraft"),
            encoding="utf-8")
        (self.root / "snapshot.json").write_text(json.dumps(snapshot()), encoding="utf-8")

    def apply(self, *extra):
        out = io.StringIO()
        with redirect_stdout(out):
            sync.main(["apply", "--snapshot", str(self.root / "snapshot.json"), "--date", "2026-10-20",
                       "--root", str(self.root), "--summary", str(self.root / "pr.md"), "--ids", str(self.root / "ids.json")] + list(extra))
        return out.getvalue()

    def rows(self, rel):
        lines = (self.root / rel).read_text(encoding="utf-8").splitlines()
        header = lines[0].split("\t")
        return dict((l.split("\t")[0], dict(zip(header, l.split("\t")))) for l in lines[1:])

    def test_writes_decisions_and_the_repo_still_validates(self):
        self.apply()
        awa = self.rows("lexicon/words/A/words.tsv")["pap-000002"]
        self.assertEqual((awa["en"], awa["nl"], awa["es"]), ("water", "water; drinkwater", "agua"))
        self.assertEqual(awa["translated_by"], "teacher-a; teacher-b; machine")
        self.assertEqual((awa["status"], awa["reviewed_by"]), ("reviewed", "victorgomesrt-rgb"))
        self.assertIn("EN, ES confirmed as machine draft, NL corrected", awa["notes"])

        cas = self.rows("lexicon/words/C/words.tsv")["pap-000003"]
        self.assertEqual((cas["en"], cas["nl"], cas["es"]), ("house; home", "huis", "casa"))
        self.assertEqual(cas["translated_by"], "teacher-a; teacher-b; board-c")
        self.assertEqual((cas["status"], cas["reviewed_by"]), ("draft", ""))  # board-c has no GitHub username
        self.assertIn("no GitHub username", cas["notes"])

        hopi = self.rows("lexicon/words/H/words.tsv")["pap-000015"]
        self.assertEqual((hopi["status"], hopi["en"]), ("disputed", "a lot"))

        corpus = list(self.rows("corpus/parallel/pairs.tsv").values())
        self.assertEqual(len(corpus), 1)
        self.assertEqual((corpus[0]["prompt_id"], corpus[0]["pap"], corpus[0]["translated_by"], corpus[0]["checked_by"]),
                         ("prm-000001", SENTENCE_1, "teacher-a", "teacher-b"))
        self.assertEqual((corpus[0]["status"], corpus[0]["reviewed_by"], corpus[0]["batch"], corpus[0]["licence"]),
                         ("reviewed", "victorgomesrt-rgb", "contrib-2026-10-20", "CC0-1.0"))
        self.assertEqual(corpus[0]["flags_kept"], "RULE_ORT_014; bar-0001")
        held = list(self.rows("eval/parallel/pairs.tsv").values())
        self.assertEqual((held[0]["prompt_id"], held[0]["pap"], held[0]["translated_by"]), ("prm-000004", SENTENCE_2, "teacher-a"))
        self.assertEqual(held[0]["checked_by"], "")   # the only rater asked for a fix

        people = self.rows("_meta/contributors.tsv")
        self.assertEqual(people["teacher-a"]["credit_name"], "Teacher A")
        self.assertEqual(people["teacher-b"]["credit_name"], "")          # did not agree to be named
        self.assertEqual((people["board-c"]["role"], people["board-c"]["github"]), ("board", ""))
        self.assertEqual(people["teacher-a"]["consent"], "tool-2026-10")
        self.assertEqual(sorted(people), sorted(set(people)))             # no duplicate handles
        self.assertNotIn("email", "".join((self.root / "_meta/contributors.tsv").read_text(encoding="utf-8").split("\n")[0]))

        self.assertEqual(json.loads((self.root / "ids.json").read_text()), [1, 3, 4, 5, 6])
        ctx = validate.run(self.root)
        errors = [f for f in ctx.findings if f.severity == "error"]
        self.assertEqual(errors, [], "\n".join("%s:%s %s" % (f.path, f.line, f.message) for f in errors))

    def test_skips_what_it_cannot_write_safely(self):
        out = self.apply()
        self.assertIn("skipped decision 2: pap-000001 abo is already reviewed", out)
        self.assertIn("skipped decision 7", out)
        self.assertIn("'educación'", out)
        self.assertIn("skipped decision 8: pap-000004 cashon has a translation in the repo by now", out)
        body = (self.root / "pr.md").read_text(encoding="utf-8")
        self.assertIn("Approval needed from:** @victorgomesrt-rgb", body)
        self.assertIn("Not exported (3)", body)
        abo = self.rows("lexicon/words/A/words.tsv")["pap-000001"]
        self.assertEqual(abo["notes"], "")   # untouched

    def test_dry_run_writes_nothing(self):
        before = dict((p, p.read_bytes()) for p in self.root.rglob("*.tsv"))
        out = self.apply("--dry-run")
        self.assertIn("would write 5 decision(s)", out)
        self.assertEqual(before, dict((p, p.read_bytes()) for p in self.root.rglob("*.tsv")))

    def test_running_twice_adds_no_duplicate_pair(self):
        self.apply()
        self.apply()
        self.assertEqual(len(self.rows("corpus/parallel/pairs.tsv")), 1)

    def test_handle_taken_by_someone_else_is_refused(self):
        snap = snapshot()
        snap["profiles"][1]["handle"] = "arubagov33"   # teacher A's handle clashes with the repo owner
        (self.root / "snapshot.json").write_text(json.dumps(snap), encoding="utf-8")
        out = self.apply()
        self.assertIn("handle 'arubagov33' belongs to GitHub user ARUBAGOV33", out)
        self.assertNotIn("teacher-a", (self.root / "_meta/contributors.tsv").read_text(encoding="utf-8"))
        self.assertEqual(self.rows("lexicon/words/C/words.tsv")["pap-000003"]["en"], "")

    def test_mark_exported_needs_a_pull_request_url(self):
        ids = self.root / "ids.json"
        ids.write_text("[1]", encoding="utf-8")
        with self.assertRaises(SystemExit):
            sync.main(["mark-exported", "--ids", str(ids), "--pr-url", "not-a-url"])


if __name__ == "__main__":
    unittest.main()
